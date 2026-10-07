from django.test import SimpleTestCase

from parameterized import parameterized

from products.cloud_agents.backend.facade.enums import CloudAgentRunStatus, StopReason
from products.cloud_agents.backend.logic import status as status_logic

TASK_RUN_ENDS = ["done", "cancelled", "error", "timeout", "usage_limit"]


class TestStatusMapping(SimpleTestCase):
    @parameterized.expand(
        [
            ("not_started", CloudAgentRunStatus.QUEUED),
            ("queued", CloudAgentRunStatus.QUEUED),
            ("in_progress", CloudAgentRunStatus.RUNNING),
            ("completed", CloudAgentRunStatus.COMPLETED),
            ("failed", CloudAgentRunStatus.FAILED),
            ("cancelled", CloudAgentRunStatus.CANCELLED),
        ]
    )
    def test_task_run_status_maps_to_run_status(self, task_run_status: str, expected: CloudAgentRunStatus) -> None:
        assert status_logic.run_status_for(task_run_status) == expected

    def test_unknown_task_run_status_is_an_error(self) -> None:
        with self.assertRaises(ValueError):
            status_logic.run_status_for("paused")

    @parameterized.expand(
        [(status, run_end) for status in ("not_started", "queued", "in_progress") for run_end in [None, *TASK_RUN_ENDS]]
    )
    def test_active_run_has_no_stop_reason(self, task_run_status: str, run_end: str | None) -> None:
        assert status_logic.stop_reason_for(status_logic.run_status_for(task_run_status), run_end) is None

    @parameterized.expand(
        [
            ("completed", "done", StopReason.DONE, False),
            ("cancelled", "cancelled", StopReason.CANCELLED, False),
            ("failed", "error", StopReason.ERROR, True),
            ("failed", "timeout", StopReason.TIMEOUT, True),
            ("failed", "usage_limit", StopReason.USAGE_LIMIT, True),
        ]
    )
    def test_ended_run_has_a_stop_reason_and_a_safe_error(
        self, task_run_status: str, run_end: str, expected: StopReason, has_error: bool
    ) -> None:
        stop_reason = status_logic.stop_reason_for(status_logic.run_status_for(task_run_status), run_end)
        assert stop_reason == expected
        error = status_logic.error_message_for(stop_reason)
        assert (error is not None) is has_error
        # The usage limit text of Tasks names another product. The API text must not.
        assert "Desktop" not in (error or "")

    @parameterized.expand(
        [
            ("queued", "running", True),
            ("running", "queued", False),
            ("running", "completed", True),
            ("completed", "running", False),
            ("failed", "queued", False),
            ("queued", "queued", True),
        ]
    )
    def test_status_moves_forward_only(self, current: str, new: str, expected: bool) -> None:
        assert status_logic.moves_forward(current, new) is expected
