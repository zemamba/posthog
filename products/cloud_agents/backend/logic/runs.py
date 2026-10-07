"""Start, continue, cancel and read cloud agent runs. Each run is one task of the Tasks product."""

from __future__ import annotations

import json
import hashlib
import dataclasses
from collections.abc import Sequence
from typing import Final, cast, overload
from uuid import UUID

from django.db import IntegrityError, transaction
from django.db.models import QuerySet
from django.utils import timezone

from posthog.dataclasses import frozen

from products.tasks.backend.facade.api import read_task_run_history, signal_task_run_user_message
from products.tasks.backend.facade.billing import get_task_run_billing
from products.tasks.backend.facade.cancellation import cancel_task_run
from products.tasks.backend.facade.cloud_agents import (
    CloudAgentRunNotResumable,
    CloudAgentTaskInvalid,
    CloudAgentTaskNotFound,
    count_active_cloud_agent_runs,
    create_cloud_agent_task,
    get_cloud_agent_task_run,
    list_cloud_agent_task_run_ids,
    resume_cloud_agent_task,
)
from products.tasks.backend.facade.compute import SandboxSize
from products.tasks.backend.facade.compute_quota import (
    ComputeBillingLimitExceeded,
    cloud_agents_quota_denial,
    cloud_agents_quota_reset_at,
)
from products.tasks.backend.facade.contracts import TaskRunDTO
from products.tasks.backend.facade.inference import (
    InferenceDecision,
    InferenceRequest,
    InferenceUnavailable,
    resolve_inference,
)
from products.tasks.backend.facade.model_catalogue import runtime_adapter_for
from products.tasks.backend.facade.run_config import RuntimeAdapter, get_default_model_for_runtime_adapter

from ..facade.contracts import (
    CallerIdentity,
    CredentialOwnerRequired,
    IdempotencyKeyReused,
    InvalidInput,
    MessageResult,
    OrganizationDeactivated,
    ProfileDTO,
    ProfileNotFound,
    ResolvedRunConfig,
    RunCancelUnavailable,
    RunCreateInput,
    RunDTO,
    RunEventsDTO,
    RunListFilters,
    RunNotFound,
    RunNotReady,
    RunNotResumable,
    RunStopping,
    TeamSettingsDTO,
    UsageLimited,
)
from ..facade.enums import BillingMode, CloudAgentRunStatus, InferenceMode
from ..models import CloudAgentRun
from . import (
    limits,
    status as status_logic,
    sync,
)
from .analytics import capture_event
from .config_resolution import render_prompt, resolve_run_config
from .cost import apply_billing
from .profiles import get_profile, get_profile_by_ref
from .run_rows import get_run_row, run_rows, session_entry, to_run_dto
from .settings import get_team_settings
from .webhooks.endpoints import validate_webhook_url

INACTIVITY_TIMEOUT_SECONDS: Final = 600
MAX_RETRY_AFTER_SECONDS: Final = 24 * 60 * 60
TITLE_MAX_LENGTH: Final = 120
EVENT_LOG_MAX_BYTES: Final = 16 * 1024 * 1024
RUN_ID_STATE_KEY: Final = "cloud_agents_run_id"
_OWN_CREDENTIAL_MODES: Final = frozenset({InferenceMode.OWN_KEY, InferenceMode.OWN_SUBSCRIPTION})


class _DuplicateIdempotencyKey(Exception):
    pass


@frozen
class _ModelSelection:
    runtime_adapter: str
    model: str | None


class RunList(Sequence[RunDTO]):
    """The runs that match a filter, newest first. It reads only the page that a caller takes a slice of."""

    def __init__(self, rows: QuerySet[CloudAgentRun]) -> None:
        self._rows = rows

    def __len__(self) -> int:
        return self._rows.count()

    @overload
    def __getitem__(self, index: int) -> RunDTO: ...

    @overload
    def __getitem__(self, index: slice) -> list[RunDTO]: ...

    def __getitem__(self, index: int | slice) -> RunDTO | list[RunDTO]:
        if isinstance(index, slice):
            return [to_run_dto(run) for run in self._rows[index]]
        return to_run_dto(self._rows[index])


# --- Start ---


def request_hash(data: RunCreateInput) -> str:
    """The identity of a create request, so a reused idempotency key with a different body is refused."""
    body = dataclasses.asdict(data)
    body.pop("idempotency_key", None)
    return hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()


def _origin_key(team_id: int, idempotency_key: str) -> str:
    return f"ca:{hashlib.sha256(f'{team_id}:{idempotency_key}'.encode()).hexdigest()[:40]}"


def _find_replay(team_id: int, idempotency_key: str, body_hash: str) -> RunDTO | None:
    run = run_rows(team_id).filter(idempotency_key=idempotency_key).first()
    if run is None:
        return None
    if run.request_hash != body_hash:
        raise IdempotencyKeyReused()
    return to_run_dto(run)


def _resolve_profile(team_id: int, ref: str | None, settings: TeamSettingsDTO) -> ProfileDTO | None:
    if ref:
        try:
            return get_profile_by_ref(team_id, ref)
        except ProfileNotFound:
            raise InvalidInput("This profile does not exist in this project.", attr="profile") from None
    if settings.default_profile_id is None:
        return None
    try:
        return get_profile(team_id, settings.default_profile_id)
    except ProfileNotFound:
        return None


def _check_quota(team_id: int, *, billable: bool) -> None:
    """Raise when the project must not start or continue a billed run. An unbilled run has no quota."""
    if not billable:
        return
    denial = cloud_agents_quota_denial(team_id=team_id)
    if denial is None:
        return
    if denial == "organization_deactivated":
        raise OrganizationDeactivated()
    raise UsageLimited(retry_after=_quota_retry_after(team_id))


def _quota_retry_after(team_id: int) -> int | None:
    reset_at = cloud_agents_quota_reset_at(team_id=team_id)
    if reset_at is None:
        return None
    seconds = int((reset_at - timezone.now()).total_seconds())
    return min(max(seconds, 1), MAX_RETRY_AFTER_SECONDS)


def _select_model(model: str | None) -> _ModelSelection:
    """The runtime that drives the model. With no model, PostHog selects the default model of the default runtime."""
    if model is None:
        adapter = RuntimeAdapter.CLAUDE.value
        return _ModelSelection(runtime_adapter=adapter, model=get_default_model_for_runtime_adapter(adapter))
    adapter_for_model = runtime_adapter_for(model)
    if adapter_for_model is None:
        raise InvalidInput("This model is not available. Read the catalog for the models you can use.", attr="model")
    return _ModelSelection(runtime_adapter=adapter_for_model, model=model)


def _resolve_inference(
    team_id: int, caller: CallerIdentity, selection: _ModelSelection, requested: InferenceMode
) -> InferenceDecision:
    try:
        return resolve_inference(
            user_id=caller.user_id,
            team_id=team_id,
            runtime_adapter=selection.runtime_adapter,
            requested=cast(InferenceRequest, requested.value),
        )
    except InferenceUnavailable as error:
        raise InvalidInput(error.detail, attr="inference") from error


def _run_state(run: CloudAgentRun, config: ResolvedRunConfig) -> dict[str, object]:
    return {RUN_ID_STATE_KEY: str(run.id), "max_duration_minutes": config.max_duration_minutes}


def _attach_session(run: CloudAgentRun, task_run: TaskRunDTO) -> None:
    """Make `task_run` the current agent session of `run`. The caller saves the row."""
    session_status = status_logic.run_status_for(task_run.status)
    sessions = list(run.agent_sessions or [])
    sessions.append(
        session_entry(
            index=len(sessions) + 1,
            task_run_id=task_run.id,
            status=session_status,
            started_at=None,
            ended_at=None,
        )
    )
    run.agent_sessions = sessions
    run.task_id = task_run.task_id
    run.current_task_run_id = task_run.id
    run.status = CloudAgentRunStatus.QUEUED.value
    run.stop_reason = None
    run.error = None
    run.completed_at = None
    run.cost_final = False
    run.last_synced_at = timezone.now()


def _create_run(
    team_id: int,
    caller: CallerIdentity,
    user_id: int,
    data: RunCreateInput,
    config: ResolvedRunConfig,
    selection: _ModelSelection,
    decision: InferenceDecision,
    idempotency_key: str | None,
    body_hash: str | None,
) -> CloudAgentRun:
    # One transaction holds the row of this product and the rows of Tasks, and Tasks starts its
    # workflow only after the commit. So a failure at any step leaves no row and no sandbox, and a
    # run never exists on one side only. The concurrency count is exact for the same reason: the
    # lock of the guard is held until the new Tasks run is stored.
    with transaction.atomic():
        limits.concurrency_guard(team_id, lambda: count_active_cloud_agent_runs(team_id=team_id))
        try:
            with transaction.atomic():
                run = CloudAgentRun.objects.for_team(team_id).create(
                    team_id=team_id,
                    created_by_id=user_id,
                    caller_kind=caller.kind.value,
                    caller_product=caller.product,
                    billable=caller.billable,
                    prompt=data.prompt,
                    repository=config.repository,
                    branch=config.branch,
                    profile_id=config.profile_id,
                    tags=config.tags,
                    metadata=dict(data.metadata or {}),
                    idempotency_key=idempotency_key,
                    request_hash=body_hash,
                    webhook_url=config.webhook_url,
                    config={
                        **config.to_json(),
                        "model": selection.model,
                        "runtime_adapter": selection.runtime_adapter,
                        "inference": decision.mode,
                        "inference_requested": config.inference.value,
                    },
                    status=CloudAgentRunStatus.QUEUED.value,
                    billing_mode=(BillingMode.BILLED if caller.billable else BillingMode.UNBILLED).value,
                    inference_billing=decision.mode,
                )
        except IntegrityError:
            if idempotency_key is None:
                raise
            raise _DuplicateIdempotencyKey() from None
        try:
            task = create_cloud_agent_task(
                team_id=team_id,
                user_id=user_id,
                prompt=render_prompt(config, data.prompt),
                title=data.prompt[:TITLE_MAX_LENGTH],
                repository=config.repository,
                branch=config.branch,
                create_pr=config.create_pr,
                origin_key=_origin_key(team_id, idempotency_key) if idempotency_key else None,
                billable=caller.billable,
                sandbox_size=SandboxSize(config.size.value),
                model=selection.model,
                runtime_adapter=selection.runtime_adapter,
                reasoning_effort=None,
                inactivity_timeout_seconds=INACTIVITY_TIMEOUT_SECONDS,
                extra_run_state=_run_state(run, config),
                inference_state=decision.run_state_updates,
            )
        except CloudAgentTaskInvalid as error:
            raise InvalidInput(error.detail, attr=error.attr if error.attr == "model" else None) from error
        if task.run is None:
            raise RuntimeError(f"Tasks returned no run for cloud agent run {run.id}")
        _attach_session(run, task.run)
        run.save()
    return run


def start_run(
    team_id: int, caller: CallerIdentity, data: RunCreateInput, idempotency_key: str | None = None
) -> tuple[RunDTO, bool]:
    """Start a run. The flag is True when the idempotency key replayed a run that an earlier request started."""
    idempotency_key = idempotency_key or data.idempotency_key
    body_hash = request_hash(data) if idempotency_key else None
    if idempotency_key and body_hash:
        # Before every gate, so a retry of a request that succeeded always gets its run back.
        replay = _find_replay(team_id, idempotency_key, body_hash)
        if replay is not None:
            return replay, True
    if caller.user_id is None:
        raise InvalidInput("A run needs a user. Use a personal API key or an OAuth token of a user.")

    settings = get_team_settings(team_id)
    profile = _resolve_profile(team_id, data.profile, settings)
    config = resolve_run_config(data, profile, settings)
    if data.webhook_url:
        validate_webhook_url(data.webhook_url)
    selection = _select_model(config.model)

    _check_quota(team_id, billable=caller.billable)
    limits.consume_create_rate(team_id)
    try:
        decision = _resolve_inference(team_id, caller, selection, config.inference)
        run = _create_run(
            team_id, caller, caller.user_id, data, config, selection, decision, idempotency_key, body_hash
        )
    except _DuplicateIdempotencyKey:
        limits.refund_create_rate(team_id)
        # A concurrent request with the same key stored its run first.
        replay = _find_replay(team_id, idempotency_key or "", body_hash or "")
        if replay is None:
            raise
        return replay, True
    except BaseException:
        # Nothing started, so the request does not count against the create rate.
        limits.refund_create_rate(team_id)
        raise

    capture_event(
        "cloud_agents_run_created",
        caller,
        team_id,
        {
            "run_id": str(run.id),
            "billable": caller.billable,
            "size": config.size.value,
            "inference_requested": config.inference.value,
            "inference_resolved": decision.mode,
            "profile_used": config.profile_id is not None,
            "has_idempotency_key": idempotency_key is not None,
        },
    )
    return to_run_dto(get_run_row(team_id, run.id)), False


# --- Read ---


def _refreshed_row(team_id: int, run_id: UUID) -> CloudAgentRun:
    run = get_run_row(team_id, run_id)
    if run.current_task_run_id is not None and sync.needs_read_refresh(run):
        sync.apply_task_run_update(team_id, run.current_task_run_id)
        run = get_run_row(team_id, run_id)
    return run


def get_run(team_id: int, run_id: UUID) -> RunDTO:
    run = _refreshed_row(team_id, run_id)
    if not run.cost_final and run.task_id is not None:
        # Shown, not saved: the finalization task stores the cost, so it captures the completion event one time.
        apply_billing(run, get_task_run_billing(team_id=team_id, task_id=run.task_id))
    return to_run_dto(run)


def list_runs(team_id: int, filters: RunListFilters) -> RunList:
    rows = run_rows(team_id)
    if filters.status is not None:
        rows = rows.filter(status=filters.status.value)
    if filters.profile_id is not None:
        rows = rows.filter(profile_id=filters.profile_id)
    if filters.repository:
        rows = rows.filter(repository__iexact=filters.repository)
    if filters.tag:
        rows = rows.filter(tags__contains=[filters.tag])
    if filters.created_after is not None:
        rows = rows.filter(created_at__gte=filters.created_after)
    if filters.created_before is not None:
        rows = rows.filter(created_at__lt=filters.created_before)
    # The id breaks a tie between two runs of the same instant, so a page boundary never repeats a run.
    return RunList(rows.order_by("-created_at", "-id"))


def get_run_events(team_id: int, run_id: UUID) -> RunEventsDTO:
    """Every stored event of the run, oldest first, across its agent sessions."""
    run = get_run_row(team_id, run_id)
    if run.task_id is None:
        return RunEventsDTO(events=[], truncated=False)
    task_run_ids = list_cloud_agent_task_run_ids(team_id=team_id, task_id=run.task_id)
    # The history of a session holds the sessions before it. So the newest session gives the full
    # log, and when that is too large, the newest earlier session that fits gives the start of it.
    for position, task_run_id in enumerate(reversed(task_run_ids)):
        events = read_task_run_history(task_run_id, run.task_id, team_id, max_bytes=EVENT_LOG_MAX_BYTES)
        if events is not None:
            return RunEventsDTO(events=events, truncated=position > 0)
    return RunEventsDTO(events=[], truncated=bool(task_run_ids))


# --- Continue ---


def _check_credential_owner(run: CloudAgentRun, caller: CallerIdentity) -> None:
    """A run on a user's own key or subscription spends that user's credential, so only that user continues it."""
    inference = run.config.get("inference")
    if inference in _OWN_CREDENTIAL_MODES and (caller.user_id is None or caller.user_id != run.created_by_id):
        raise CredentialOwnerRequired()


def _send_to_live_session(team_id: int, run: CloudAgentRun, task_run: TaskRunDTO, content: str) -> bool:
    """Give the message to the running agent. False when its workflow already ended."""
    try:
        delivered = signal_task_run_user_message(
            task_run.id,
            task_run.task_id,
            team_id,
            content=content,
            artifact_ids=[],
            # The creator, so Tasks sees the owner of the credential that the run uses.
            actor_user_id=run.created_by_id,
        )
    except ComputeBillingLimitExceeded:
        raise UsageLimited(retry_after=_quota_retry_after(team_id)) from None
    except RuntimeError:
        raise RunStopping() from None
    return bool(delivered)


def _resume(team_id: int, run_id: UUID, user_id: int, previous: TaskRunDTO, content: str) -> CloudAgentRun:
    # One transaction, for the same reasons as in `_create_run`: a resume starts a sandbox.
    with transaction.atomic():
        limits.concurrency_guard(team_id, lambda: count_active_cloud_agent_runs(team_id=team_id))
        run = CloudAgentRun.objects.for_team(team_id).select_for_update().get(id=run_id)
        if run.current_task_run_id != previous.id:
            # Another message resumed the run first. Its session is not ready to take a message yet.
            raise RunNotReady()
        config = ResolvedRunConfig.from_json(run.config)
        try:
            task_run = resume_cloud_agent_task(
                team_id=team_id,
                task_id=previous.task_id,
                user_id=user_id,
                previous_run_id=previous.id,
                message=content,
                # The size and the model are fixed for the life of the run.
                sandbox_size=SandboxSize(config.size.value),
                model=config.model,
                reasoning_effort=None,
                inactivity_timeout_seconds=INACTIVITY_TIMEOUT_SECONDS,
                extra_run_state=_run_state(run, config),
                inference_state=None,
            )
        except (CloudAgentRunNotResumable, CloudAgentTaskNotFound):
            raise RunNotResumable() from None
        except CloudAgentTaskInvalid as error:
            raise InvalidInput(error.detail) from error
        _attach_session(run, task_run)
        run.save()
    return run


def send_message(team_id: int, caller: CallerIdentity, run_id: UUID, content: str) -> MessageResult:
    """Send a follow-up message. A live agent gets it. A run that stopped starts a new agent session with it."""
    run = _refreshed_row(team_id, run_id)
    _check_quota(team_id, billable=run.billable)
    _check_credential_owner(run, caller)
    if run.current_task_run_id is None:
        raise RunNotReady()
    task_run = get_cloud_agent_task_run(team_id=team_id, run_id=run.current_task_run_id)
    if task_run is None:
        raise RunNotFound()

    if not task_run.is_terminal:
        if _send_to_live_session(team_id, run, task_run, content):
            capture_event("cloud_agents_run_followup_sent", caller, team_id, {"run_id": str(run.id), "resumed": False})
            return MessageResult(resumed=False, run=to_run_dto(run))
        task_run = get_cloud_agent_task_run(team_id=team_id, run_id=task_run.id)
        if task_run is None or not task_run.is_terminal:
            # The workflow ended and the run is not stored as ended yet, so it cannot be resumed now.
            raise RunStopping()

    user_id = run.created_by_id or caller.user_id
    if user_id is None:
        raise InvalidInput("A run needs a user. Use a personal API key or an OAuth token of a user.")
    resumed = _resume(team_id, run.id, user_id, task_run, content)
    capture_event("cloud_agents_run_followup_sent", caller, team_id, {"run_id": str(run.id), "resumed": True})
    return MessageResult(resumed=True, run=to_run_dto(get_run_row(team_id, resumed.id)))


# --- Cancel ---


def cancel_run(team_id: int, caller: CallerIdentity, run_id: UUID) -> tuple[RunDTO, bool]:
    """Ask the run to stop. The flag is False when the run already ended, so there was nothing to cancel."""
    run = get_run_row(team_id, run_id)
    if run.current_task_run_id is None or run.task_id is None:
        raise RunNotReady()
    # The generic cancel has no origin check, so the run is resolved as a Cloud Agents run first.
    task_run = get_cloud_agent_task_run(team_id=team_id, run_id=run.current_task_run_id)
    if task_run is None:
        raise RunNotFound()
    outcome, _ = cancel_task_run(
        task_run.id,
        task_run.task_id,
        team_id,
        source="cloud_agents_api",
        requested_by_user_id=caller.user_id,
        requested_by_distinct_id=caller.distinct_id,
    )
    capture_event("cloud_agents_run_cancelled", caller, team_id, {"run_id": str(run.id), "outcome": outcome})
    match outcome:
        case "accepted" | "already_terminal":
            sync.apply_task_run_update(team_id, task_run.id)
            return to_run_dto(get_run_row(team_id, run_id)), outcome == "accepted"
        case "not_found":
            raise RunNotFound()
        case _:
            raise RunCancelUnavailable()
