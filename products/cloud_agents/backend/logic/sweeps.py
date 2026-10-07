"""Stop the billed runs of a project that is over its usage limit."""

from __future__ import annotations

from typing import Final

import structlog

from products.tasks.backend.facade.cancellation import cancel_task_run
from products.tasks.backend.facade.compute_quota import list_teams_over_cloud_agents_quota_with_active_runs

from ..models import CloudAgentRun
from .status import TERMINAL_STATUSES

logger = structlog.get_logger(__name__)

USAGE_LIMIT_CANCEL_REASON: Final = "Stopped because the project reached its usage limit"


def stop_runs_over_quota() -> int:
    """Cancel the active billed runs of every project that is over its limit. Returns how many it cancelled."""
    cancelled = 0
    for team_id in list_teams_over_cloud_agents_quota_with_active_runs():
        runs = (
            CloudAgentRun.objects.for_team(team_id)
            .filter(billable=True)
            .exclude(status__in=[status.value for status in TERMINAL_STATUSES])
        )
        for run in runs:
            if run.current_task_run_id is None or run.task_id is None:
                continue
            try:
                outcome, _ = cancel_task_run(
                    run.current_task_run_id,
                    run.task_id,
                    team_id,
                    reason=USAGE_LIMIT_CANCEL_REASON,
                    source="cloud_agents_quota_sweep",
                )
            except Exception:
                logger.exception("cloud_agents_quota_sweep_cancel_failed", team_id=team_id, run_id=str(run.id))
                continue
            if outcome != "accepted":
                continue
            cancelled += 1
    return cancelled
