"""Create, resume and read the tasks behind the Cloud Agents public API.

The Cloud Agents product owns its API contract, its limits and its usage ledger. Everything
task-shaped happens here, so that product never touches tasks internals. Each function is
scoped to the reserved ``cloud_agents`` origin: a task of another origin is never found.
"""

from collections.abc import Mapping
from typing import Any, Literal
from uuid import UUID

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import QuerySet

from posthog.dataclasses import frozen
from posthog.models import User
from posthog.models.team.team import Team

from products.tasks.backend.exceptions import COMPUTE_USAGE_LIMIT_ERROR_MESSAGE
from products.tasks.backend.facade import (
    api as tasks_api,
    contracts,
)
from products.tasks.backend.feature_flags import get_model_access_error
from products.tasks.backend.logic.services.model_catalogue import runtime_adapter_for
from products.tasks.backend.logic.services.sandbox_config import (
    SANDBOX_SIZE_SHAPES,
    SANDBOX_SIZE_STATE_KEY,
    SandboxSize,
)
from products.tasks.backend.models import Task, TaskClientProvenance, TaskRun
from products.tasks.backend.temporal.process_task.activities.update_task_run_status import (
    TIMED_OUT_INACTIVITY_STATE_KEY,
    TIMED_OUT_WALL_CLOCK_STATE_KEY,
)
from products.tasks.backend.temporal.process_task.utils import (
    RuntimeAdapter,
    get_default_model_for_runtime_adapter,
    validate_model_selection,
)

ACTIVE_RUN_STATUSES = [TaskRun.Status.NOT_STARTED, TaskRun.Status.QUEUED, TaskRun.Status.IN_PROGRESS]

# The PostHog MCP posture of every Cloud Agents run. An unattended run that an API key
# started must not write to the project.
CLOUD_AGENT_POSTHOG_MCP_SCOPES: Literal["read_only"] = "read_only"

TaskRunEnd = Literal["done", "cancelled", "error", "timeout", "usage_limit"]


class CloudAgentTaskError(Exception):
    """Base for the refusals below. ``attr`` names the request field at fault, if one is."""

    def __init__(self, detail: str, *, attr: str | None = None) -> None:
        self.detail = detail
        self.attr = attr
        super().__init__(detail)


class CloudAgentTaskInvalid(CloudAgentTaskError):
    pass


class CloudAgentTaskNotFound(CloudAgentTaskError):
    pass


class CloudAgentRunNotResumable(CloudAgentTaskError):
    pass


class CloudAgentTaskOriginKeyConflict(CloudAgentTaskError):
    def __init__(self, origin_key: str) -> None:
        self.origin_key = origin_key
        super().__init__(f"Idempotency key {origin_key!r} is already used by another task", attr="origin_key")


def create_cloud_agent_task(
    *,
    team_id: int,
    user_id: int,
    prompt: str,
    title: str,
    repository: str,
    branch: str | None,
    create_pr: bool,
    origin_key: str | None,
    billable: bool,
    sandbox_size: SandboxSize,
    model: str | None,
    runtime_adapter: str | None,
    reasoning_effort: str | None,
    inactivity_timeout_seconds: int | None,
    extra_run_state: Mapping[str, object] | None,
) -> contracts.CloudAgentTaskDTO:
    """Create a Cloud Agents task and start its first run.

    A repeated ``origin_key`` returns the existing task with ``created=False``, before any
    other check, so that a retry succeeds when the first attempt did. Raises
    ``CloudAgentTaskOriginKeyConflict`` when the key belongs to a task of another origin, and
    ``CloudAgentTaskInvalid`` when the model selection is not allowed.

    ``billable`` is carried as the task's client provenance. Each sandbox session that a run of
    the task opens copies it, which is how the usage ledger finds the sessions to bill.

    The sandbox has the fixed shape of ``sandbox_size``, the default size included, so that
    the usage record of each session states the full selected shape.
    """
    replay = _find_replayed_task(team_id, origin_key)
    if replay is not None:
        return replay

    selection = _resolve_model_selection(
        user_id=user_id, model=model, runtime_adapter=runtime_adapter, reasoning_effort=reasoning_effort
    )
    run_state: dict[str, Any] = {
        **(extra_run_state or {}),
        **_sized_run_state(sandbox_size),
        # The boot path reads the override and delivers the prompt one time. A pending user
        # message is delivered at boot and forwarded again for a cold background run.
        "initial_prompt_override": prompt,
    }
    team = Team.objects.get(id=team_id)
    try:
        # One transaction so that a duplicate origin_key rolls back the task, its run and the
        # workflow start, which is deferred to the commit.
        with transaction.atomic():
            task = Task.create_and_run(
                team=team,
                title=title.strip()[:255] or prompt[:255],
                description=prompt,
                origin_product=Task.OriginProduct.CLOUD_AGENTS,
                user_id=user_id,
                repository=repository,
                branch=branch,
                mode="background",
                create_pr=create_pr,
                posthog_mcp_scopes=CLOUD_AGENT_POSTHOG_MCP_SCOPES,
                origin_key=origin_key,
                internal=True,
                client_provenance=TaskClientProvenance.CLOUD_AGENTS if billable else None,
                # An internal task gets no AI run defaults from Tasks, so the selection is pinned here.
                runtime_adapter=selection.runtime_adapter,
                model=selection.model,
                reasoning_effort=reasoning_effort,
                sandbox_resources=SANDBOX_SIZE_SHAPES[sandbox_size],
                inactivity_timeout_seconds=inactivity_timeout_seconds,
                extra_run_state=run_state,
            )
    except IntegrityError:
        if origin_key is None:
            raise
        replay = _find_replayed_task(team_id, origin_key)
        if replay is None:
            raise
        return replay
    return _task_dto(task, created=True)


def resume_cloud_agent_task(
    *,
    team_id: int,
    task_id: UUID,
    user_id: int,
    previous_run_id: UUID,
    message: str,
    sandbox_size: SandboxSize,
    model: str | None,
    reasoning_effort: str | None,
    inactivity_timeout_seconds: int | None,
    extra_run_state: Mapping[str, object] | None,
) -> contracts.TaskRunDTO:
    """Start a successor run that resumes ``previous_run_id`` with ``message`` as its first turn.

    The task lookup is scoped to the origin and the team, not to what ``user_id`` can see in
    Tasks: the Cloud Agents product authorizes its own callers. ``model`` and
    ``reasoning_effort`` left as ``None`` keep the selection of the previous run.

    Raises ``CloudAgentTaskNotFound`` for an unknown task, ``CloudAgentRunNotResumable`` when
    the previous run is unknown, still active or owned by an earlier task owner, and
    ``CloudAgentTaskInvalid`` when the request is refused for another reason.
    """
    task = _cloud_agent_tasks(team_id).filter(id=task_id).first()
    if task is None:
        raise CloudAgentTaskNotFound("Task not found")
    previous_run = task.runs.filter(id=previous_run_id).first()
    if previous_run is None:
        raise CloudAgentRunNotResumable("The previous run does not belong to this task", attr="previous_run_id")
    if not previous_run.is_terminal:
        raise CloudAgentRunNotResumable("The previous run is still active", attr="previous_run_id")

    previous_dispatch = (previous_run.state or {}).get("pending_dispatch")
    previous_create_pr = previous_dispatch.get("create_pr") if isinstance(previous_dispatch, dict) else None
    create_pr = previous_create_pr if isinstance(previous_create_pr, bool) else True

    server_run_state: dict[str, Any] = {
        **(extra_run_state or {}),
        **_sized_run_state(sandbox_size),
        # The same record the first run has, so that a lost workflow start is dispatched again
        # with the same PR and scope settings.
        "pending_dispatch": {
            "create_pr": create_pr,
            "posthog_mcp_scopes": CLOUD_AGENT_POSTHOG_MCP_SCOPES,
            "user_id": user_id,
        },
    }
    if inactivity_timeout_seconds is not None:
        server_run_state["inactivity_timeout_seconds"] = inactivity_timeout_seconds

    result = tasks_api._run_resolved_task(
        task,
        team_id,
        user_id,
        validated_data={
            "mode": "background",
            "resume_from_run_id": previous_run.id,
            "pending_user_message": message,
            "model": model,
            "runtime_adapter": runtime_adapter_for(model) if model else None,
            "reasoning_effort": reasoning_effort,
        },
        server_run_state=server_run_state,
        create_pr=create_pr,
        posthog_mcp_scopes=CLOUD_AGENT_POSTHOG_MCP_SCOPES,
    )
    if result is None:
        raise CloudAgentRunNotResumable(
            "The previous run belongs to an earlier owner of the task", attr="previous_run_id"
        )
    if result.error is not None:
        if result.error.attr is None:
            raise CloudAgentRunNotResumable(result.error.detail, attr="previous_run_id")
        raise CloudAgentTaskInvalid(result.error.detail, attr=result.error.attr)
    run = get_cloud_agent_task_run(team_id=team_id, run_id=result.run_id) if result.run_id else None
    if run is None:
        raise CloudAgentRunNotResumable("The successor run was not created", attr="previous_run_id")
    return run


def classify_task_run_end(run: contracts.TaskRunDTO) -> TaskRunEnd:
    """Why a finished run ended. Raises ``ValueError`` for a run that is still active.

    A completed run is ``done`` even with a timeout marker: the workflow completes an idle
    run whose turn ended, and marks it, when no client ended it first. A failed run with a
    timeout marker stopped in the middle of a turn, so it is ``timeout``.
    """
    if not run.is_terminal:
        raise ValueError(f"Task run {run.id} has not ended (status {run.status})")
    if run.status == TaskRun.Status.CANCELLED:
        return "cancelled"
    if run.status == TaskRun.Status.COMPLETED:
        return "done"
    if (run.error_message or "").startswith(COMPUTE_USAGE_LIMIT_ERROR_MESSAGE):
        return "usage_limit"
    if run.state.get(TIMED_OUT_INACTIVITY_STATE_KEY) or run.state.get(TIMED_OUT_WALL_CLOCK_STATE_KEY):
        return "timeout"
    return "error"


def count_active_cloud_agent_runs(*, team_id: int) -> int:
    """Runs of this origin that have not ended. Soft-deleting a task does not stop its run, so
    the runs of deleted tasks count."""
    return TaskRun.objects.filter(
        team_id=team_id,
        task__team_id=team_id,
        task__origin_product=Task.OriginProduct.CLOUD_AGENTS,
        status__in=ACTIVE_RUN_STATUSES,
    ).count()


def get_cloud_agent_task_run(*, team_id: int, run_id: UUID) -> contracts.TaskRunDTO | None:
    """A run by id, only when it belongs to a Cloud Agents task of this team.

    ``get_task_run`` is scoped to the team at most, so a caller that holds only a run id would
    read the run of any task through it.
    """
    run = (
        TaskRun.objects.select_related("task", "task__created_by")
        .filter(id=run_id, team_id=team_id, task__team_id=team_id, task__origin_product=Task.OriginProduct.CLOUD_AGENTS)
        .first()
    )
    return tasks_api._task_run_to_dto(run) if run is not None else None


def list_cloud_agent_task_run_ids(*, team_id: int, task_id: UUID) -> list[UUID]:
    """Every run of the task, oldest first. Each run after the first resumes the one before it."""
    return list(
        TaskRun.objects.filter(
            team_id=team_id,
            task_id=task_id,
            task__team_id=team_id,
            task__origin_product=Task.OriginProduct.CLOUD_AGENTS,
        )
        .order_by("created_at", "id")
        .values_list("id", flat=True)
    )


def _cloud_agent_tasks(team_id: int) -> QuerySet[Task]:
    return Task.objects.filter(team_id=team_id, origin_product=Task.OriginProduct.CLOUD_AGENTS, deleted=False)


def _sized_run_state(sandbox_size: SandboxSize) -> dict[str, Any]:
    """The run state that pins a run to a fixed sandbox shape.

    The CPU and memory keys are repeated here because a successor run gets no
    ``sandbox_resources`` argument: its state is the only place the shape can come from.
    """
    shape = SANDBOX_SIZE_SHAPES[sandbox_size]
    return {
        SANDBOX_SIZE_STATE_KEY: sandbox_size.value,
        "sandbox_cpu_cores": shape.cpu_cores,
        "sandbox_memory_gb": shape.memory_gb,
        # Request equals limit, so the usage record of the session states the full shape.
        "burstable_sandbox_resources_enabled": False,
        # Gives the agent the `finish` tool, so the sandbox is released when the work is done
        # and not at the inactivity timeout.
        "end_run_when_done": True,
    }


@frozen
class _ModelSelection:
    runtime_adapter: str
    model: str | None


def _resolve_model_selection(
    *, user_id: int, model: str | None, runtime_adapter: str | None, reasoning_effort: str | None
) -> _ModelSelection:
    adapter = runtime_adapter or runtime_adapter_for(model) or RuntimeAdapter.CLAUDE.value
    resolved_model = model or get_default_model_for_runtime_adapter(adapter)
    try:
        validate_model_selection(adapter, resolved_model, reasoning_effort)
    except ValidationError as error:
        raise CloudAgentTaskInvalid("; ".join(error.messages), attr="model") from error
    distinct_id = User.objects.filter(id=user_id).values_list("distinct_id", flat=True).first()
    access_error = get_model_access_error(resolved_model, distinct_id=distinct_id)
    if access_error is not None:
        raise CloudAgentTaskInvalid(access_error, attr="model")
    return _ModelSelection(runtime_adapter=adapter, model=resolved_model)


def _find_replayed_task(team_id: int, origin_key: str | None) -> contracts.CloudAgentTaskDTO | None:
    if origin_key is None:
        return None
    existing = Task.objects.filter(team_id=team_id, origin_key=origin_key).first()
    if existing is None:
        return None
    if existing.origin_product != Task.OriginProduct.CLOUD_AGENTS:
        raise CloudAgentTaskOriginKeyConflict(origin_key)
    return _task_dto(existing, created=False)


def _task_dto(task: Task, *, created: bool) -> contracts.CloudAgentTaskDTO:
    run = task.latest_run
    return contracts.CloudAgentTaskDTO(
        task_id=task.id,
        team_id=task.team_id,
        run=tasks_api._task_run_to_dto(run, task=task) if run is not None else None,
        created=created,
    )
