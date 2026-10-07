import dataclasses
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from unittest.mock import MagicMock, patch

from posthog.token_bucket import BucketDecision

from products.cloud_agents.backend.facade.contracts import CallerIdentity
from products.cloud_agents.backend.facade.enums import CallerKind
from products.cloud_agents.backend.models import CloudAgentRun
from products.tasks.backend.facade.contracts import CloudAgentTaskDTO, TaskRunBillingDTO, TaskRunDTO
from products.tasks.backend.facade.inference import InferenceDecision

FLAG_KEY = "cloud-agents"


class CloudAgentsFlagMixin:
    _flag_patcher: Any

    def setUp(self) -> None:
        super().setUp()  # type: ignore[misc]
        self.set_cloud_agents_flag(True)

    def tearDown(self) -> None:
        self._flag_patcher.stop()
        super().tearDown()  # type: ignore[misc]

    def set_cloud_agents_flag(self, enabled: bool) -> None:
        if hasattr(self, "_flag_patcher"):
            self._flag_patcher.stop()
        self._flag_patcher = patch("posthoganalytics.feature_enabled")
        mock = self._flag_patcher.start()
        # Only this flag, so the request does not turn on unrelated flags.
        mock.side_effect = lambda flag_name, *args, **kwargs: enabled if flag_name == FLAG_KEY else False

    def base_url(self) -> str:
        return f"/api/projects/{self.team.id}/cloud_agents"  # type: ignore[attr-defined]


def caller_for(user: Any) -> CallerIdentity:
    return CallerIdentity(user_id=user.id, distinct_id=user.distinct_id, kind=CallerKind.API, billable=True)


LOGIC = "products.cloud_agents.backend.logic"
RUN_CONFIG: dict[str, Any] = {
    "repository": "acme/app",
    "branch": None,
    "model": "claude-test-model",
    "runtime_adapter": "claude",
    "size": "4x16",
    "inference": "posthog",
    "inference_requested": "auto",
    "instructions": None,
    "create_pr": True,
    "pr_mode": "draft",
    "max_duration_minutes": 60,
    "max_cost_usd": None,
    "tags": [],
    "webhook_url": None,
    "profile_id": None,
}
TERMINAL_TASK_RUN_STATUSES = ("completed", "failed", "cancelled")


def task_run_dto(
    *,
    team_id: int,
    task_id: UUID | None = None,
    run_id: UUID | None = None,
    status: str = "queued",
    error_message: str | None = None,
    output: dict[str, Any] | None = None,
    state: dict[str, Any] | None = None,
    completed_at: datetime | None = None,
) -> TaskRunDTO:
    return TaskRunDTO(
        id=run_id or uuid4(),
        task_id=task_id or uuid4(),
        team_id=team_id,
        status=status,
        environment="cloud",
        stage=None,
        branch=None,
        error_message=error_message,
        output=output,
        state=state or {},
        completed_at=completed_at,
        is_terminal=status in TERMINAL_TASK_RUN_STATUSES,
        task_origin_product="cloud_agents",
        pr_url=(output or {}).get("pr_url"),
    )


def billing_dto(**overrides: Any) -> TaskRunBillingDTO:
    values: dict[str, Any] = {
        "compute_cost_cents": None,
        "inference_cost_cents": None,
        "vcpu_seconds": Decimal(0),
        "gib_seconds": Decimal(0),
        "billable": True,
        "inference_billing": "posthog",
        "rate_card_version": "2026-10-01",
        "waived": False,
        "settled": False,
        "sessions": (),
    }
    return TaskRunBillingDTO(**{**values, **overrides})


class TasksFacadeFake:
    """Stands in for the Tasks product at its facade. It holds the runs that the tests create and change."""

    def __init__(self, team_id: int) -> None:
        self.team_id = team_id
        self.runs: dict[UUID, TaskRunDTO] = {}
        self.create_calls: list[dict[str, Any]] = []
        self.resume_calls: list[dict[str, Any]] = []
        self.billing = billing_dto()

    def create(self, **kwargs: Any) -> CloudAgentTaskDTO:
        self.create_calls.append(kwargs)
        run = task_run_dto(team_id=kwargs["team_id"])
        self.runs[run.id] = run
        return CloudAgentTaskDTO(task_id=run.task_id, team_id=run.team_id, run=run, created=True)

    def resume(self, **kwargs: Any) -> TaskRunDTO:
        self.resume_calls.append(kwargs)
        run = task_run_dto(team_id=kwargs["team_id"], task_id=kwargs["task_id"])
        self.runs[run.id] = run
        return run

    def get(self, *, team_id: int, run_id: UUID) -> TaskRunDTO | None:
        run = self.runs.get(run_id)
        return run if run is not None and run.team_id == team_id else None

    def count_active(self, *, team_id: int) -> int:
        return sum(1 for run in self.runs.values() if run.team_id == team_id and not run.is_terminal)

    def list_run_ids(self, *, team_id: int, task_id: UUID) -> list[UUID]:
        return [run.id for run in self.runs.values() if run.task_id == task_id and run.team_id == team_id]

    def set_status(self, run_id: UUID | None, status: str, **changes: Any) -> TaskRunDTO:
        assert run_id is not None
        run = self.runs[run_id]
        output = changes.get("output", run.output)
        self.runs[run_id] = dataclasses.replace(
            run,
            status=status,
            is_terminal=status in TERMINAL_TASK_RUN_STATUSES,
            pr_url=(output or {}).get("pr_url"),
            **changes,
        )
        return self.runs[run_id]

    def get_billing(self, *, team_id: int, task_id: UUID) -> TaskRunBillingDTO:
        return self.billing


class TasksFakeMixin:
    """Patches every Tasks facade function that the run logic calls, and the Redis bucket of the create rate."""

    tasks: TasksFacadeFake
    mocks: dict[str, MagicMock]

    def setUp(self) -> None:
        super().setUp()  # type: ignore[misc]
        self.tasks = TasksFacadeFake(self.team.id)  # type: ignore[attr-defined]
        allowed = BucketDecision(allowed=True, remaining=9, limit=10, retry_after=0, reset=0)
        inference = InferenceDecision(
            mode="posthog",
            adapter="claude",
            credential_kind=None,
            owner_user_id=None,
            run_state_updates={},
            resolved_from_auto=True,
        )
        targets: dict[str, Any] = {
            f"{LOGIC}.runs.create_cloud_agent_task": {"side_effect": self.tasks.create},
            f"{LOGIC}.runs.resume_cloud_agent_task": {"side_effect": self.tasks.resume},
            f"{LOGIC}.runs.get_cloud_agent_task_run": {"side_effect": self.tasks.get},
            f"{LOGIC}.sync.get_cloud_agent_task_run": {"side_effect": self.tasks.get},
            f"{LOGIC}.streams.get_cloud_agent_task_run": {"side_effect": self.tasks.get},
            f"{LOGIC}.runs.count_active_cloud_agent_runs": {"side_effect": self.tasks.count_active},
            f"{LOGIC}.runs.list_cloud_agent_task_run_ids": {"side_effect": self.tasks.list_run_ids},
            f"{LOGIC}.runs.get_task_run_billing": {"side_effect": self.tasks.get_billing},
            f"{LOGIC}.cost.get_task_run_billing": {"side_effect": self.tasks.get_billing},
            f"{LOGIC}.runs.resolve_inference": {"return_value": inference},
            f"{LOGIC}.runs.cloud_agents_quota_denial": {"return_value": None},
            f"{LOGIC}.runs.cloud_agents_quota_reset_at": {"return_value": None},
            f"{LOGIC}.runs.signal_task_run_user_message": {"return_value": True},
            f"{LOGIC}.runs.cancel_task_run": {"return_value": ("accepted", None)},
            f"{LOGIC}.runs.read_task_run_history": {"return_value": []},
            f"{LOGIC}.limits.consume": {"return_value": allowed},
            f"{LOGIC}.limits.refund": {},
            f"{LOGIC}.analytics.report_user_action": {},
        }
        self.mocks = {}
        for target, config in targets.items():
            patcher = patch(target, **config)
            self.mocks[target.removeprefix(f"{LOGIC}.")] = patcher.start()
            self.addCleanup(patcher.stop)  # type: ignore[attr-defined]

    def make_run(self, *, team: Any = None, task_status: str = "queued", **overrides: Any) -> CloudAgentRun:
        """A stored run with one agent session, and its Tasks run in the fake."""
        team = team or self.team  # type: ignore[attr-defined]
        task_run = task_run_dto(team_id=team.id, status=task_status)
        self.tasks.runs[task_run.id] = task_run
        values: dict[str, Any] = {
            "team": team,
            "created_by": self.user,  # type: ignore[attr-defined]
            "prompt": "Fix the flaky test",
            "repository": "acme/app",
            "config": RUN_CONFIG,
            "task_id": task_run.task_id,
            "current_task_run_id": task_run.id,
            "agent_sessions": [
                {"index": 1, "task_run_id": str(task_run.id), "status": "queued", "started_at": None, "ended_at": None}
            ],
            "inference_billing": "posthog",
        }
        return CloudAgentRun.all_teams.create(**{**values, **overrides})
