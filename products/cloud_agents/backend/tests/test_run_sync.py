from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import time_machine
from posthog.test.base import BaseTest
from unittest.mock import patch

from parameterized import parameterized

from posthog.models import Organization, Team

from products.cloud_agents.backend import receivers
from products.cloud_agents.backend.logic import sweeps, sync
from products.cloud_agents.backend.models import CloudAgentRun, CloudAgentsWebhookDelivery, CloudAgentsWebhookEndpoint
from products.cloud_agents.backend.tasks.run_tasks import (
    FINALIZE_RETRY_DELAYS_SECONDS,
    finalize_run_cost,
    reconcile_cloud_agent_runs,
    stop_cloud_agent_runs_over_quota,
    sync_cloud_agent_run,
)
from products.cloud_agents.backend.tasks.tasks import deliver_webhook
from products.cloud_agents.backend.tests.base import LOGIC, TasksFakeMixin, billing_dto, task_run_dto

NOW = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)
# The text that Tasks stores on a run that the usage limit stopped.
TASKS_USAGE_LIMIT_ERROR = "Your organization reached its PostHog Desktop usage limit."


class RunSyncTestCase(TasksFakeMixin, BaseTest):
    def setUp(self) -> None:
        super().setUp()
        CloudAgentsWebhookEndpoint.objects.create(team=self.team, url="https://example.com/hook")

    def sync(self, run: CloudAgentRun, task_run_id: Any = None) -> tuple[CloudAgentRun, Any]:
        """Run the sync task, commit, and return the stored run and the finalization calls."""
        with (
            patch.object(deliver_webhook, "delay"),
            patch.object(finalize_run_cost, "delay") as finalize,
            self.captureOnCommitCallbacks(execute=True),
        ):
            sync_cloud_agent_run(self.team.id, str(task_run_id or run.current_task_run_id))
        return CloudAgentRun.objects.get(id=run.id), finalize

    def events(self) -> list[str]:
        return list(CloudAgentsWebhookDelivery.objects.order_by("created_at").values_list("event_type", flat=True))


class TestApplyTaskRunUpdate(RunSyncTestCase):
    def test_run_follows_its_tasks_run_and_sends_each_event_one_time(self) -> None:
        run = self.make_run()
        self.tasks.set_status(run.current_task_run_id, "in_progress")
        with time_machine.travel(NOW, tick=False):
            running, finalize = self.sync(run)
            self.sync(run)

        assert (running.status, running.stop_reason, running.started_at) == ("running", None, NOW)
        assert running.agent_sessions[0]["status"] == "running"
        assert self.events() == ["run.started"]
        finalize.assert_not_called()

        self.tasks.set_status(
            run.current_task_run_id,
            "completed",
            output={"pr_url": "https://github.com/acme/app/pull/7"},
            state={"task_summary": " Fixed the test. "},
            completed_at=NOW + timedelta(minutes=5),
        )
        with time_machine.travel(NOW + timedelta(minutes=6), tick=False):
            done, finalize = self.sync(run)
            self.sync(run)

        assert (done.status, done.stop_reason, done.error) == ("completed", "done", None)
        assert done.completed_at == NOW + timedelta(minutes=5)
        assert (done.pr_url, done.pr_urls) == ("https://github.com/acme/app/pull/7", [done.pr_url])
        assert done.summary == "Fixed the test."
        assert done.agent_sessions[0]["ended_at"] == (NOW + timedelta(minutes=5)).isoformat()
        assert self.events() == ["run.started", "run.completed"]
        finalize.assert_called_once_with(self.team.id, str(run.id))
        payload = CloudAgentsWebhookDelivery.objects.get(event_type="run.completed").payload["data"]["run"]
        assert (payload["id"], payload["status"], payload["result"]["pr_url"]) == (
            str(run.id),
            "completed",
            done.pr_url,
        )

    @parameterized.expand(
        [
            ("cancelled", "cancelled", "Stopped by user", {}, "cancelled", "run.cancelled", False),
            ("error", "failed", "Traceback: KeyError at worker.py", {}, "error", "run.failed", True),
            ("timeout", "failed", None, {"timed_out_wall_clock": True}, "timeout", "run.failed", True),
            ("usage_limit", "failed", TASKS_USAGE_LIMIT_ERROR, {}, "usage_limit", "run.failed", True),
        ]
    )
    def test_end_of_a_run(
        self,
        _name: str,
        task_status: str,
        tasks_error: str | None,
        state: dict[str, Any],
        stop_reason: str,
        event: str,
        has_error: bool,
    ) -> None:
        run = self.make_run()
        self.tasks.set_status(run.current_task_run_id, task_status, error_message=tasks_error, state=state)

        stored, finalize = self.sync(run)

        assert (stored.status, stored.stop_reason) == (task_status, stop_reason)
        assert (stored.error is not None) is has_error
        # The text of Tasks can hold an exception or the name of another product. The API never shows it.
        assert tasks_error is None or tasks_error not in (stored.error or "")
        assert "Desktop" not in (stored.error or "")
        # A run that ends before it was seen as running sends no start event.
        assert self.events() == [event]
        finalize.assert_called_once()

    def test_late_read_does_not_move_a_run_back(self) -> None:
        run = self.make_run(status="completed", stop_reason="done", completed_at=NOW)
        self.tasks.set_status(run.current_task_run_id, "in_progress")

        stored, finalize = self.sync(run)

        assert (stored.status, stored.stop_reason) == ("completed", "done")
        assert self.events() == []
        finalize.assert_not_called()

    def test_update_from_an_older_session_does_not_change_the_resumed_run(self) -> None:
        old = task_run_dto(team_id=self.team.id, status="failed", error_message="Sandbox stopped")
        self.tasks.runs[old.id] = old
        run = self.make_run()
        run.agent_sessions = [
            {"index": 1, "task_run_id": str(old.id), "status": "running", "started_at": None, "ended_at": None},
            {**run.agent_sessions[0], "index": 2},
        ]
        run.save()

        stored, finalize = self.sync(run, task_run_id=old.id)

        assert (stored.status, stored.stop_reason, stored.error) == ("queued", None, None)
        assert [session["status"] for session in stored.agent_sessions] == ["failed", "queued"]
        assert self.events() == []
        finalize.assert_not_called()

    def test_unknown_tasks_run_changes_nothing(self) -> None:
        run = self.make_run()
        stored, _ = self.sync(run, task_run_id=uuid4())
        assert stored.updated_at == run.updated_at

    def test_cancellation_by_the_quota_sweep_keeps_its_reason(self) -> None:
        billed = self.make_run(task_status="in_progress", status="running")
        unbilled = self.make_run(task_status="in_progress", status="running", billable=False)
        other_team = Team.objects.create(organization=Organization.objects.create(name="Other"), name="Other team")
        within_limit = self.make_run(team=other_team, task_status="in_progress", status="running")

        def cancel(run_id: Any, *args: Any, **kwargs: Any) -> tuple[str, None]:
            self.tasks.set_status(run_id, "cancelled")
            return "accepted", None

        with (
            patch(f"{LOGIC}.sweeps.list_teams_over_cloud_agents_quota_with_active_runs", return_value=[self.team.id]),
            patch(f"{LOGIC}.sweeps.cancel_task_run", side_effect=cancel) as cancel_task_run,
        ):
            stop_cloud_agent_runs_over_quota()

        assert [call.args[0] for call in cancel_task_run.call_args_list] == [billed.current_task_run_id]
        assert cancel_task_run.call_args.kwargs["reason"] == sweeps.USAGE_LIMIT_CANCEL_REASON
        stored, _ = self.sync(billed)
        assert (stored.status, stored.stop_reason) == ("cancelled", "usage_limit")
        assert "usage limit" in (stored.error or "")
        for untouched in (unbilled, within_limit):
            assert CloudAgentRun.all_teams.get(id=untouched.id).stop_reason is None


class TestReceiver(BaseTest):
    @parameterized.expand([("cloud_agents", True), ("user_created", False), ("", False)])
    def test_only_runs_of_this_product_are_synced(self, origin_product: str, synced: bool) -> None:
        task_run = SimpleNamespace(id=uuid4(), team_id=self.team.id, origin_product=origin_product)
        with (
            patch.object(sync_cloud_agent_run, "delay") as delay,
            self.captureOnCommitCallbacks(execute=True) as callbacks,
        ):
            receivers.sync_run_on_task_run_status_change(sender=None, task_run=task_run, previous_status="queued")
            # Not before the commit: the worker must read the status that the writer commits.
            delay.assert_not_called()

        assert len(callbacks) == (1 if synced else 0)
        if synced:
            delay.assert_called_once_with(self.team.id, str(task_run.id))


class TestCostFinalization(RunSyncTestCase):
    def finalize(self, run: CloudAgentRun, **kwargs: Any) -> tuple[CloudAgentRun, Any, Any]:
        with (
            patch.object(finalize_run_cost, "apply_async") as retry,
            patch(f"{LOGIC}.cost.capture_event_in_task") as capture,
        ):
            finalize_run_cost(self.team.id, str(run.id), **kwargs)
        return CloudAgentRun.objects.get(id=run.id), retry, capture

    def test_settled_cost_is_stored_as_final_and_captured_one_time(self) -> None:
        run = self.make_run(
            task_status="completed",
            status="completed",
            stop_reason="done",
            started_at=NOW,
            completed_at=NOW + timedelta(minutes=10),
        )
        self.tasks.billing = billing_dto(
            compute_cost_cents=6,
            inference_cost_cents=125,
            vcpu_seconds=Decimal("2400.0004"),
            gib_seconds=Decimal("9600"),
            settled=True,
        )
        stored, retry, capture = self.finalize(run)
        _, _, second_capture = self.finalize(run)

        assert (stored.compute_usd, stored.inference_usd) == (Decimal("0.0600"), Decimal("1.2500"))
        assert (stored.vcpu_seconds, stored.gib_seconds) == (Decimal("2400.000"), Decimal("9600.000"))
        assert (stored.billing_mode, stored.inference_billing, stored.cost_final) == ("billed", "posthog", True)
        retry.assert_not_called()
        capture.assert_called_once()
        event, team_id, user_id, properties = capture.call_args.args
        assert (event, team_id, user_id) == ("cloud_agents_run_completed", self.team.id, self.user.id)
        assert properties == {
            "run_id": str(run.id),
            "status": "completed",
            "stop_reason": "done",
            "duration_s": 600,
            "size": "4x16",
            "billing_mode": "billed",
            "inference_billing": "posthog",
            "compute_usd": 0.06,
            "inference_usd": 1.25,
            "caller_kind": "api",
            "caller_product": None,
        }
        second_capture.assert_not_called()

    @parameterized.expand(
        [
            (
                "own_subscription_has_no_inference_cost",
                {"inference_billing": "own_subscription", "inference_cost_cents": 50},
                None,
                "billed",
            ),
            ("unbilled_run", {"billable": False, "inference_cost_cents": 50}, Decimal("0.5000"), "unbilled"),
        ]
    )
    def test_who_pays(
        self, _name: str, billing: dict[str, Any], inference_usd: Decimal | None, billing_mode: str
    ) -> None:
        run = self.make_run(task_status="completed", status="completed")
        self.tasks.billing = billing_dto(compute_cost_cents=10, settled=True, **billing)
        stored, _, _ = self.finalize(run)
        assert (stored.inference_usd, stored.billing_mode) == (inference_usd, billing_mode)

    @parameterized.expand(
        [
            ("first_attempt", {}, FINALIZE_RETRY_DELAYS_SECONDS[0], 1),
            ("last_retry", {"attempt": len(FINALIZE_RETRY_DELAYS_SECONDS) - 1}, FINALIZE_RETRY_DELAYS_SECONDS[-1], 6),
            ("retries_used_up", {"attempt": len(FINALIZE_RETRY_DELAYS_SECONDS)}, None, None),
            ("reconciler_does_not_chain_retries", {"retry": False}, None, None),
        ]
    )
    def test_cost_that_is_not_settled(
        self, _name: str, kwargs: dict[str, Any], countdown: int | None, next_attempt: int | None
    ) -> None:
        run = self.make_run(task_status="completed", status="completed")
        self.tasks.billing = billing_dto(compute_cost_cents=10, settled=False)

        stored, retry, capture = self.finalize(run, **kwargs)

        assert (stored.compute_usd, stored.cost_final) == (Decimal("0.1000"), False)
        capture.assert_not_called()
        if countdown is None:
            retry.assert_not_called()
        else:
            retry.assert_called_once_with(
                args=[self.team.id, str(run.id)], kwargs={"attempt": next_attempt}, countdown=countdown
            )

    def test_retry_delays_cover_thirty_minutes(self) -> None:
        assert sum(FINALIZE_RETRY_DELAYS_SECONDS) == 30 * 60


class TestReconciler(RunSyncTestCase):
    def test_reconciler_repairs_stale_runs_and_asks_for_missing_costs(self) -> None:
        stale_at = NOW - sync.RECONCILE_AFTER - timedelta(seconds=1)
        with time_machine.travel(stale_at, tick=False):
            stale = self.make_run(last_synced_at=stale_at)
            never_synced = self.make_run()
        with time_machine.travel(NOW, tick=False):
            fresh = self.make_run(last_synced_at=NOW)
            cost_pending = self.make_run(task_status="completed", status="completed", completed_at=NOW)
            self.make_run(task_status="completed", status="completed", completed_at=NOW, cost_final=True)
            self.make_run(
                task_status="completed", status="completed", completed_at=NOW - sync.COST_RECONCILE_WINDOW * 2
            )
            for run in (stale, never_synced, fresh):
                self.tasks.set_status(run.current_task_run_id, "in_progress")
            with patch.object(deliver_webhook, "delay"), patch.object(finalize_run_cost, "delay") as finalize:
                reconcile_cloud_agent_runs()

        statuses = {
            run.id: run.status for run in CloudAgentRun.objects.filter(id__in=[stale.id, never_synced.id, fresh.id])
        }
        assert statuses == {stale.id: "running", never_synced.id: "running", fresh.id: "queued"}
        finalize.assert_called_once_with(self.team.id, str(cost_pending.id), retry=False)
