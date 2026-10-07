"""Copy the state of a Tasks run to the `CloudAgentRun` row that owns it.

Three triggers call `apply_task_run_update`: the status signal of Tasks, a read of a run whose
row is old, and the periodic reconciler. It is safe to call it any number of times.
"""

from __future__ import annotations

from datetime import timedelta
from functools import partial
from typing import Any, Final
from uuid import UUID

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

import structlog

from products.tasks.backend.facade.api import read_pr_urls
from products.tasks.backend.facade.cloud_agents import classify_task_run_end, get_cloud_agent_task_run
from products.tasks.backend.facade.contracts import TaskRunDTO

# Module imports, not names: the task modules import this module, and this module starts their
# tasks, so each side reads the other at call time.
from ..facade.enums import CloudAgentRunStatus, StopReason, WebhookEvent
from ..models import CloudAgentRun
from ..tasks import run_tasks
from . import status as status_logic
from .run_rows import run_payload, to_run_dto
from .webhooks import delivery as delivery_logic

logger = structlog.get_logger(__name__)

READ_REFRESH_AFTER: Final = timedelta(seconds=5)
RECONCILE_AFTER: Final = timedelta(minutes=2)
RECONCILE_BATCH_SIZE: Final = 500
COST_RECONCILE_WINDOW: Final = timedelta(days=7)
SUMMARY_STATE_KEY: Final = "task_summary"

_TERMINAL_VALUES: Final = [status.value for status in status_logic.TERMINAL_STATUSES]
_TERMINAL_EVENTS: Final = {
    CloudAgentRunStatus.COMPLETED: WebhookEvent.RUN_COMPLETED,
    CloudAgentRunStatus.FAILED: WebhookEvent.RUN_FAILED,
    CloudAgentRunStatus.CANCELLED: WebhookEvent.RUN_CANCELLED,
}


def _update_session(run: CloudAgentRun, task_run: TaskRunDTO, status: CloudAgentRunStatus) -> None:
    now = timezone.now()
    sessions: list[dict[str, Any]] = []
    for entry in run.agent_sessions or []:
        if entry.get("task_run_id") == str(task_run.id):
            entry = {**entry, "status": status.value}
            if status != CloudAgentRunStatus.QUEUED and not entry.get("started_at"):
                entry["started_at"] = now.isoformat()
            if status_logic.is_terminal(status) and not entry.get("ended_at"):
                entry["ended_at"] = (task_run.completed_at or now).isoformat()
        sessions.append(entry)
    run.agent_sessions = sessions


def _stop_reason(run: CloudAgentRun, task_run: TaskRunDTO, status: CloudAgentRunStatus) -> StopReason | None:
    if not status_logic.is_terminal(status):
        return None
    stop_reason = status_logic.stop_reason_for(status, classify_task_run_end(task_run))
    if stop_reason == StopReason.CANCELLED and task_run.state.get("cancel_source") == "cloud_agents_quota_sweep":
        return StopReason.USAGE_LIMIT
    return stop_reason


def _apply_to_current_run(run: CloudAgentRun, task_run: TaskRunDTO) -> None:
    previous_status = CloudAgentRunStatus(run.status)
    new_status = status_logic.run_status_for(task_run.status)
    now = timezone.now()
    run.last_synced_at = now
    if not status_logic.moves_forward(previous_status, new_status):
        run.save(update_fields=["last_synced_at", "updated_at"])
        return

    _update_session(run, task_run, new_status)
    run.status = new_status.value
    stop_reason = _stop_reason(run, task_run, new_status)
    run.stop_reason = stop_reason.value if stop_reason is not None else None
    run.error = status_logic.error_message_for(stop_reason)
    if new_status != CloudAgentRunStatus.QUEUED and run.started_at is None:
        run.started_at = now
    if status_logic.is_terminal(new_status) and run.completed_at is None:
        run.completed_at = task_run.completed_at or now

    # A later agent session can open one more pull request, so the list keeps the earlier ones.
    pr_urls = list(dict.fromkeys([*(run.pr_urls or []), *read_pr_urls(task_run.output)]))
    run.pr_urls = pr_urls
    run.pr_url = task_run.pr_url or run.pr_url or (pr_urls[0] if pr_urls else None)
    summary = task_run.state.get(SUMMARY_STATE_KEY)
    if isinstance(summary, str) and summary.strip():
        run.summary = summary.strip()
    run.save()

    if new_status == previous_status:
        return
    event = WebhookEvent.RUN_STARTED if new_status == CloudAgentRunStatus.RUNNING else _TERMINAL_EVENTS.get(new_status)
    if event is not None:
        # In this transaction, so a status change and its event are stored together or not at all.
        delivery_logic.enqueue_run_event(run.team_id, run.id, event, run_payload(to_run_dto(run)))
    if status_logic.is_terminal(new_status):
        transaction.on_commit(partial(run_tasks.finalize_run_cost.delay, run.team_id, str(run.id)))


def apply_task_run_update(team_id: int, task_run_id: UUID) -> None:
    """Read the Tasks run again and move the cloud agent run that owns it forward."""
    task_run = get_cloud_agent_task_run(team_id=team_id, run_id=task_run_id)
    if task_run is None:
        return
    with transaction.atomic():
        rows = CloudAgentRun.objects.for_team(team_id).select_for_update(of=("self",))
        run = rows.select_related("created_by", "profile").filter(current_task_run_id=task_run_id).first()
        if run is not None:
            _apply_to_current_run(run, task_run)
            return
        # An update for a session that a later message replaced. It must not change the run, which
        # now follows its newer session, so only the entry of the old session changes.
        run = rows.filter(agent_sessions__contains=[{"task_run_id": str(task_run_id)}]).first()
        if run is not None:
            _update_session(run, task_run, status_logic.run_status_for(task_run.status))
            run.save(update_fields=["agent_sessions", "updated_at"])


def needs_read_refresh(run: CloudAgentRun) -> bool:
    if run.current_task_run_id is None or status_logic.is_terminal(run.status):
        return False
    return run.last_synced_at is None or timezone.now() - run.last_synced_at > READ_REFRESH_AFTER


def reconcile_runs() -> int:
    """Repair the rows that the status signal did not reach. Returns how many rows it looked at.

    It covers every project, so the query has no team scope. Each row is then updated in the scope
    of its own team.
    """
    stale_before = timezone.now() - RECONCILE_AFTER
    stale_active = (
        CloudAgentRun.all_teams.exclude(status__in=_TERMINAL_VALUES)
        .filter(current_task_run_id__isnull=False)
        .filter(Q(last_synced_at__lt=stale_before) | Q(last_synced_at__isnull=True, created_at__lt=stale_before))
        .order_by("last_synced_at")
        .values_list("team_id", "current_task_run_id")[:RECONCILE_BATCH_SIZE]
    )
    cost_pending = (
        CloudAgentRun.all_teams.filter(status__in=_TERMINAL_VALUES, cost_final=False, task_id__isnull=False)
        # A cost that is not final after this long will not become final, so the sweep stops asking.
        .filter(completed_at__gte=timezone.now() - COST_RECONCILE_WINDOW)
        .order_by("completed_at")
        .values_list("team_id", "id")[:RECONCILE_BATCH_SIZE]
    )
    seen = 0
    for team_id, task_run_id in list(stale_active):
        if task_run_id is None:
            continue
        seen += 1
        try:
            apply_task_run_update(team_id, task_run_id)
        except Exception:
            logger.exception("cloud_agents_reconcile_run_failed", team_id=team_id, task_run_id=str(task_run_id))
    for team_id, run_id in list(cost_pending):
        seen += 1
        # The next sweep is the retry, so the task does not schedule its own.
        run_tasks.finalize_run_cost.delay(team_id, str(run_id), retry=False)
    return seen
