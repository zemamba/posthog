from typing import Any
from uuid import uuid4

from posthog.test.base import BaseTest
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from parameterized import parameterized

from posthog.models import Integration
from posthog.models.user import User

from products.tasks.backend.exceptions import COMPUTE_USAGE_LIMIT_ERROR_MESSAGE, ComputeBillingLimitError
from products.tasks.backend.facade import (
    api as facade,
    cloud_agents,
    contracts,
)
from products.tasks.backend.facade.compute import DEFAULT_SANDBOX_SIZE, SandboxSize
from products.tasks.backend.logic.services.sandbox import SandboxConfig
from products.tasks.backend.logic.services.sandbox_usage import open_sandbox_session
from products.tasks.backend.models import SandboxSession, Task, TaskClientProvenance, TaskRun
from products.tasks.backend.temporal.process_task.activities.get_task_processing_context import (
    TaskProcessingContext,
    _is_burstable_sandbox_resources_enabled,
)
from products.tasks.backend.visibility import task_visibility_q


def _run_dto(status: str, *, error_message: str | None = None, state: dict | None = None) -> contracts.TaskRunDTO:
    return contracts.TaskRunDTO(
        id=uuid4(),
        task_id=uuid4(),
        team_id=1,
        status=status,
        environment="cloud",
        stage=None,
        branch=None,
        error_message=error_message,
        output=None,
        state=state or {},
        is_terminal=status in ("completed", "failed", "cancelled"),
    )


class TestClassifyTaskRunEnd(SimpleTestCase):
    @parameterized.expand(
        [
            ("completed", "completed", None, {}, "done"),
            ("completed_after_idle_timeout", "completed", None, {"timed_out_inactivity": True}, "done"),
            ("cancelled", "cancelled", "Stopped by user", {"cancel_requested_at": "now"}, "cancelled"),
            ("cancelled_wins_over_a_timeout_marker", "cancelled", None, {"timed_out_inactivity": True}, "cancelled"),
            ("failed", "failed", "Sandbox stopped; resume to continue", {"sandbox_gone": True}, "error"),
            ("failed_without_a_message", "failed", None, {}, "error"),
            (
                "agent_lost",
                "failed",
                "The agent stopped before finishing its turn",
                {"timed_out_inactivity": True},
                "timeout",
            ),
            ("wall_clock_cap", "failed", None, {"timed_out_wall_clock": True}, "timeout"),
            (
                "usage_limit",
                "failed",
                ComputeBillingLimitError({"team_id": 1}).message,
                {},
                "usage_limit",
            ),
            (
                "organization_deactivated",
                "failed",
                ComputeBillingLimitError({"team_id": 1}, "organization_deactivated").message,
                {},
                "error",
            ),
        ]
    )
    def test_run_end_is_classified(
        self, _name: str, status: str, error_message: str | None, state: dict, expected: str
    ) -> None:
        assert (
            cloud_agents.classify_task_run_end(_run_dto(status, error_message=error_message, state=state)) == expected
        )

    @parameterized.expand([("queued",), ("in_progress",), ("not_started",)])
    def test_active_run_has_no_end(self, status: str) -> None:
        with self.assertRaises(ValueError):
            cloud_agents.classify_task_run_end(_run_dto(status))

    def test_usage_limit_message_is_the_one_the_billing_error_carries(self) -> None:
        assert ComputeBillingLimitError({"team_id": 1}).message == COMPUTE_USAGE_LIMIT_ERROR_MESSAGE


@patch("products.tasks.backend.models.TaskRun.publish_stream_state_event", MagicMock())
@patch("products.tasks.backend.temporal.client.execute_task_processing_workflow", MagicMock())
class TestCloudAgentTasks(BaseTest):
    def setUp(self) -> None:
        super().setUp()
        Integration.objects.create(team=self.team, kind="github", config={})

    def _create(self, **overrides: Any) -> contracts.CloudAgentTaskDTO:
        kwargs: dict[str, Any] = {
            "team_id": self.team.id,
            "user_id": self.user.id,
            "prompt": "Fix the flaky test",
            "title": "Flaky test",
            "repository": "posthog/posthog",
            "branch": None,
            "create_pr": True,
            "origin_key": None,
            "billable": True,
            "sandbox_size": SandboxSize.CPU_8_MEMORY_32,
            "model": None,
            "runtime_adapter": None,
            "reasoning_effort": None,
            "inactivity_timeout_seconds": None,
            "extra_run_state": None,
        }
        kwargs.update(overrides)
        return cloud_agents.create_cloud_agent_task(**kwargs)

    def _resume(self, created: contracts.CloudAgentTaskDTO, **overrides: Any) -> contracts.TaskRunDTO:
        assert created.run is not None
        kwargs: dict[str, Any] = {
            "team_id": self.team.id,
            "task_id": created.task_id,
            "user_id": self.user.id,
            "previous_run_id": created.run.id,
            "message": "Also update the docs",
            "sandbox_size": SandboxSize.CPU_8_MEMORY_32,
            "model": None,
            "reasoning_effort": None,
            "inactivity_timeout_seconds": None,
            "extra_run_state": None,
        }
        kwargs.update(overrides)
        return cloud_agents.resume_cloud_agent_task(**kwargs)

    def _finish(self, run_id: Any, status: str = TaskRun.Status.COMPLETED) -> None:
        TaskRun.objects.filter(id=run_id).update(status=status)

    def _context(self, run: TaskRun) -> TaskProcessingContext:
        return TaskProcessingContext(
            task_id=str(run.task_id),
            run_id=str(run.id),
            team_id=run.team_id,
            team_uuid=str(self.team.uuid),
            organization_id=str(self.team.organization_id),
            github_integration_id=None,
            repository="posthog/posthog",
            distinct_id="user-1",
            state=run.state,
        )

    def test_create_stamps_a_reserved_internal_background_task(self) -> None:
        created = self._create(create_pr=False)

        task = Task.objects.get(id=created.task_id)
        assert created.created is True
        assert created.run is not None
        assert (task.origin_product, task.internal, task.channel_id) == (Task.OriginProduct.CLOUD_AGENTS, True, None)
        assert (created.run.mode, created.run.status) == ("background", TaskRun.Status.QUEUED)
        state = created.run.state
        assert state["initial_prompt_override"] == "Fix the flaky test"
        assert state["end_run_when_done"] is True
        assert state["pending_dispatch"]["posthog_mcp_scopes"] == "read_only"
        assert state["pending_dispatch"]["create_pr"] is False
        assert state["runtime_adapter"] == "claude"
        assert state["model"]

    def test_created_task_is_not_in_the_default_task_list(self) -> None:
        created = self._create()

        listed = Task.objects.filter(team_id=self.team.id, internal=False).filter(task_visibility_q(self.user.id))

        assert created.task_id not in set(listed.values_list("id", flat=True))

    @parameterized.expand(
        [
            ("default_size", DEFAULT_SANDBOX_SIZE, 4.0, 16.0),
            ("small_size", SandboxSize.CPU_1_MEMORY_2, 1.0, 2.0),
            ("large_size", SandboxSize.CPU_16_MEMORY_64, 16.0, 64.0),
        ]
    )
    def test_create_pins_a_fixed_sandbox_of_the_selected_size(
        self, _name: str, size: SandboxSize, cpu_cores: float, memory_gb: float
    ) -> None:
        created = self._create(sandbox_size=size)

        assert created.run is not None
        run = TaskRun.objects.get(id=created.run.id)
        assert run.state["sandbox_size"] == size.value
        assert self._context(run).sandbox_resource_overrides() == {"cpu_cores": cpu_cores, "memory_gb": memory_gb}
        assert _is_burstable_sandbox_resources_enabled(run_id=str(run.id), state=run.state) is False

    @parameterized.expand(
        [
            ("billable", True, TaskClientProvenance.CLOUD_AGENTS),
            ("not_billable", False, None),
        ]
    )
    def test_billable_is_carried_onto_the_sandbox_sessions_of_the_run(
        self, _name: str, billable: bool, expected: TaskClientProvenance | None
    ) -> None:
        created = self._create(billable=billable)
        assert created.run is not None

        open_sandbox_session(run_id=created.run.id, sandbox_id="sb-1", config=SandboxConfig(name="sb"), required=True)

        assert Task.objects.get(id=created.task_id).client_provenance == expected
        session = SandboxSession.objects.for_team(self.team.id).get(sandbox_id="sb-1")
        assert (session.client_provenance, session.origin_product) == (expected, Task.OriginProduct.CLOUD_AGENTS)

    def test_caller_run_state_cannot_replace_the_server_keys(self) -> None:
        created = self._create(
            extra_run_state={
                "cloud_agent_session_id": "session-1",
                "sandbox_size": "1x2",
                "burstable_sandbox_resources_enabled": True,
                "end_run_when_done": False,
            }
        )

        assert created.run is not None
        state = created.run.state
        assert state["cloud_agent_session_id"] == "session-1"
        assert state["sandbox_size"] == "8x32"
        assert state["burstable_sandbox_resources_enabled"] is False
        assert state["end_run_when_done"] is True

    def test_repeated_origin_key_returns_the_first_task(self) -> None:
        first = self._create(origin_key="key-1")
        replay = self._create(origin_key="key-1", prompt="A different prompt", sandbox_size=SandboxSize.CPU_1_MEMORY_2)

        assert replay.created is False
        assert first.run is not None and replay.run is not None
        assert (replay.task_id, replay.run.id) == (first.task_id, first.run.id)
        assert Task.objects.filter(team_id=self.team.id, origin_key="key-1").count() == 1
        assert TaskRun.objects.filter(task_id=first.task_id).count() == 1

    def test_origin_key_of_another_origin_is_a_conflict(self) -> None:
        Task.objects.create(
            team=self.team,
            title="t",
            description="d",
            origin_product=Task.OriginProduct.WORKFLOW,
            origin_key="key-1",
            created_by=self.user,
        )

        with self.assertRaises(cloud_agents.CloudAgentTaskOriginKeyConflict):
            self._create(origin_key="key-1")

    @parameterized.expand(
        [
            ("model_of_another_runtime", {"model": "gpt-5.5", "runtime_adapter": "claude"}),
            ("unknown_runtime", {"runtime_adapter": "not-a-runtime"}),
        ]
    )
    def test_invalid_model_selection_creates_nothing(self, _name: str, overrides: dict[str, Any]) -> None:
        with self.assertRaises(cloud_agents.CloudAgentTaskInvalid):
            self._create(**overrides)

        assert not Task.objects.filter(team_id=self.team.id, origin_product=Task.OriginProduct.CLOUD_AGENTS).exists()

    def test_resume_creates_a_successor_that_keeps_size_scopes_and_provenance(self) -> None:
        created = self._create(create_pr=False, sandbox_size=SandboxSize.CPU_2_MEMORY_4)
        assert created.run is not None
        self._finish(created.run.id)
        other_member = User.objects.create_and_join(self.organization, "other@example.com", "password")

        with patch("products.tasks.backend.facade.api._trigger_task_processing_workflow", return_value=None) as trigger:
            successor = self._resume(
                created,
                user_id=other_member.id,
                sandbox_size=SandboxSize.CPU_8_MEMORY_32,
                inactivity_timeout_seconds=300,
                extra_run_state={"cloud_agent_session_id": "session-1", "burstable_sandbox_resources_enabled": True},
            )

        assert successor.id != created.run.id
        assert successor.task_id == created.task_id
        state = successor.state
        assert state["resume_from_run_id"] == str(created.run.id)
        assert state["pending_user_message"] == "Also update the docs"
        assert state["sandbox_size"] == "8x32"
        assert (state["sandbox_cpu_cores"], state["sandbox_memory_gb"]) == (8.0, 32.0)
        assert state["burstable_sandbox_resources_enabled"] is False
        assert state["end_run_when_done"] is True
        assert state["inactivity_timeout_seconds"] == 300
        assert state["cloud_agent_session_id"] == "session-1"
        assert (state["runtime_adapter"], state["model"]) == (
            created.run.state["runtime_adapter"],
            created.run.state["model"],
        )
        assert trigger.call_args.kwargs["create_pr"] is False
        assert trigger.call_args.kwargs["posthog_mcp_scopes"] == "read_only"
        assert Task.objects.get(id=created.task_id).client_provenance == TaskClientProvenance.CLOUD_AGENTS
        assert cloud_agents.list_cloud_agent_task_run_ids(team_id=self.team.id, task_id=created.task_id) == [
            created.run.id,
            successor.id,
        ]

    def test_resume_of_an_active_run_is_refused(self) -> None:
        created = self._create()

        with self.assertRaises(cloud_agents.CloudAgentRunNotResumable):
            self._resume(created)

        assert TaskRun.objects.filter(task_id=created.task_id).count() == 1

    def test_resume_of_a_run_of_another_task_is_refused(self) -> None:
        created = self._create()
        other = self._create()
        assert created.run is not None and other.run is not None
        self._finish(other.run.id)

        with self.assertRaises(cloud_agents.CloudAgentRunNotResumable):
            self._resume(created, previous_run_id=other.run.id)

    def test_resume_does_not_find_a_task_of_another_origin(self) -> None:
        other = facade.create_and_run_task(
            team=self.team,
            title="t",
            description="d",
            origin_product=facade.TaskOriginProduct.USER_CREATED,
            user_id=self.user.id,
            repository="posthog/posthog",
        )
        assert other.latest_run is not None
        self._finish(other.latest_run.id)

        with self.assertRaises(cloud_agents.CloudAgentTaskNotFound):
            cloud_agents.resume_cloud_agent_task(
                team_id=self.team.id,
                task_id=other.task_id,
                user_id=self.user.id,
                previous_run_id=other.latest_run.id,
                message="m",
                sandbox_size=DEFAULT_SANDBOX_SIZE,
                model=None,
                reasoning_effort=None,
                inactivity_timeout_seconds=None,
                extra_run_state=None,
            )

    def test_active_run_count_and_run_read_are_scoped_to_the_origin(self) -> None:
        first = self._create()
        second = self._create()
        other = facade.create_and_run_task(
            team=self.team,
            title="t",
            description="d",
            origin_product=facade.TaskOriginProduct.USER_CREATED,
            user_id=self.user.id,
            repository="posthog/posthog",
        )
        assert first.run is not None and second.run is not None and other.latest_run is not None

        assert cloud_agents.count_active_cloud_agent_runs(team_id=self.team.id) == 2
        self._finish(second.run.id, TaskRun.Status.FAILED)
        TaskRun.objects.filter(id=first.run.id).update(status=TaskRun.Status.IN_PROGRESS)
        assert cloud_agents.count_active_cloud_agent_runs(team_id=self.team.id) == 1

        found = cloud_agents.get_cloud_agent_task_run(team_id=self.team.id, run_id=first.run.id)
        assert found is not None and found.id == first.run.id
        assert cloud_agents.get_cloud_agent_task_run(team_id=self.team.id, run_id=other.latest_run.id) is None
        assert cloud_agents.get_cloud_agent_task_run(team_id=self.team.id + 1, run_id=first.run.id) is None
        assert cloud_agents.list_cloud_agent_task_run_ids(team_id=self.team.id, task_id=other.task_id) == []

    def test_plain_task_keeps_the_burstable_default_and_names_no_size(self) -> None:
        created = facade.create_and_run_task(
            team=self.team,
            title="t",
            description="d",
            origin_product=facade.TaskOriginProduct.USER_CREATED,
            user_id=self.user.id,
            repository="posthog/posthog",
        )

        assert created.latest_run is not None
        state = created.latest_run.state
        assert "sandbox_size" not in state
        assert "burstable_sandbox_resources_enabled" not in state
        assert "end_run_when_done" not in state
        assert _is_burstable_sandbox_resources_enabled(run_id=str(created.latest_run.id), state=state) is True
        assert Task.objects.get(id=created.task_id).client_provenance is None
