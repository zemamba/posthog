from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import time_machine
from posthog.test.base import APIBaseTest
from unittest.mock import MagicMock, patch

from parameterized import parameterized
from rest_framework import status

from posthog.models import Integration, User
from posthog.models.scoping import team_scope
from posthog.token_bucket import BucketDecision

from products.cloud_agents.backend.facade import api
from products.cloud_agents.backend.facade.contracts import CallerIdentity, RunCreateInput
from products.cloud_agents.backend.facade.enums import BillingMode, CallerKind
from products.cloud_agents.backend.models import CloudAgentProfile, CloudAgentRun, TeamCloudAgentsConfig
from products.cloud_agents.backend.tests.base import (
    LOGIC,
    RUN_CONFIG,
    CloudAgentsFlagMixin,
    TasksFakeMixin,
    billing_dto,
    task_run_dto,
)
from products.tasks.backend.facade.cloud_agents import (
    CloudAgentRunNotResumable,
    CloudAgentTaskInvalid,
    get_cloud_agent_task_run,
)
from products.tasks.backend.facade.compute import SandboxSize
from products.tasks.backend.facade.compute_quota import ComputeBillingLimitExceeded
from products.tasks.backend.facade.contracts import SandboxSessionUsageDTO
from products.tasks.backend.facade.inference import InferenceDecision, InferenceUnavailable

NOW = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)
CREATE_BODY: dict[str, Any] = {"prompt": "Fix the flaky test", "repository": "acme/app"}
OWN_SUBSCRIPTION_DECISION = InferenceDecision(
    mode="own_subscription",
    adapter="claude",
    credential_kind="claude_subscription",
    owner_user_id=1,
    run_state_updates={"claude_model_access": "own-subscription"},
    resolved_from_auto=True,
)


class RunsAPITestCase(TasksFakeMixin, CloudAgentsFlagMixin, APIBaseTest):
    def runs_url(self, suffix: str = "") -> str:
        return f"{self.base_url()}/runs/{suffix}"

    def create(self, body: dict[str, Any] | None = None, **extra: Any) -> Any:
        return self.client.post(self.runs_url(), data=body or CREATE_BODY, format="json", **extra)

    def stored_runs(self) -> list[CloudAgentRun]:
        with team_scope(self.team.id):
            return list(CloudAgentRun.objects.order_by("created_at", "id"))


class TestCreateRun(RunsAPITestCase):
    def test_minimal_create_returns_the_full_run(self) -> None:
        with time_machine.travel(NOW, tick=False):
            response = self.create()

        assert response.status_code == status.HTTP_201_CREATED, response.json()
        (run,) = self.stored_runs()
        assert response.json() == {
            "id": str(run.id),
            "status": "queued",
            "stop_reason": None,
            "error": None,
            "created_at": "2026-10-07T12:00:00Z",
            "started_at": None,
            "completed_at": None,
            "updated_at": "2026-10-07T12:00:00Z",
            "prompt": "Fix the flaky test",
            "repository": "acme/app",
            "branch": None,
            "profile": None,
            "config": {
                "model": run.config["model"],
                "size": {"name": "4x16", "vcpu": 4, "memory_gib": 16, "price_per_hour_usd": "0.368"},
                "inference": "posthog",
                "create_pr": True,
                "pr_mode": "draft",
                "max_duration_minutes": 60,
                "max_cost_usd": None,
                "instructions_applied": False,
            },
            "result": {"pr_url": None, "pr_urls": [], "summary": None},
            "cost": {
                "compute_usd": None,
                "inference_usd": None,
                "total_usd": None,
                "vcpu_seconds": None,
                "gib_seconds": None,
                "billing_mode": "billed",
                "inference_billing": "posthog",
                "final": False,
            },
            "agent_sessions": [{"index": 1, "status": "queued", "started_at": None, "ended_at": None}],
            "tags": [],
            "metadata": {},
            "created_by": {"id": self.user.id, "email": self.user.email},
            "caller": "app",
        }
        (call,) = self.tasks.create_calls
        assert call["origin_key"] is None
        assert call["billable"] is True
        assert call["prompt"] == call["title"] == "Fix the flaky test"
        assert call["sandbox_size"] == SandboxSize("4x16")
        assert call["inactivity_timeout_seconds"] == 600
        assert call["extra_run_state"] == {"cloud_agents_run_id": str(run.id), "max_duration_minutes": 60}
        assert (call["model"], call["runtime_adapter"]) == (run.config["model"], "claude")
        assert run.current_task_run_id in self.tasks.runs

    def test_profile_supplies_the_repository_and_instructions(self) -> None:
        with team_scope(self.team.id):
            profile = CloudAgentProfile.objects.create(
                team=self.team, name="Backend", repository="acme/api", instructions="Run the tests.", tags=["be"]
            )
        response = self.create({"prompt": "Fix it", "profile": "backend", "tags": ["ci"]})

        assert response.status_code == status.HTTP_201_CREATED, response.json()
        body = response.json()
        assert body["repository"] == "acme/api"
        assert body["profile"] == {"id": str(profile.id), "name": "Backend"}
        assert body["tags"] == ["be", "ci"]
        assert body["config"]["instructions_applied"] is True
        assert self.tasks.create_calls[0]["prompt"] == "<instructions>\nRun the tests.\n</instructions>\n\nFix it"

    @parameterized.expand(
        [
            ("no_repository", {"prompt": "Fix it"}, "repository", "repository_required"),
            ("unknown_profile", {**CREATE_BODY, "profile": "nope"}, "profile", "invalid_input"),
            ("empty_prompt", {**CREATE_BODY, "prompt": ""}, "prompt", "blank"),
            ("unknown_model", {**CREATE_BODY, "model": "not-a-model"}, "model", "invalid_input"),
            (
                "too_many_metadata_pairs",
                {**CREATE_BODY, "metadata": {str(index): "v" for index in range(17)}},
                "metadata",
                "invalid_input",
            ),
        ]
    )
    def test_invalid_request_starts_nothing(
        self, _name: str, body: dict[str, Any], attr: str | None, code: str
    ) -> None:
        response = self.create(body)

        assert response.status_code == status.HTTP_400_BAD_REQUEST, response.json()
        assert (response.json()["attr"], response.json()["code"]) == (attr, code)
        assert self.stored_runs() == []
        assert self.tasks.create_calls == []

    def test_idempotency_key_replays_the_run_and_refuses_a_different_body(self) -> None:
        first = self.create(HTTP_IDEMPOTENCY_KEY="key-1")
        replay = self.create(HTTP_IDEMPOTENCY_KEY="key-1")
        different = self.create({**CREATE_BODY, "prompt": "Other task"}, HTTP_IDEMPOTENCY_KEY="key-1")
        other_key = self.create(HTTP_IDEMPOTENCY_KEY="key-2")

        assert first.status_code == status.HTTP_201_CREATED
        assert "Idempotency-Replayed" not in first.headers
        assert (replay.status_code, replay.headers["Idempotency-Replayed"]) == (status.HTTP_200_OK, "true")
        assert replay.json()["id"] == first.json()["id"]
        assert different.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert different.json()["code"] == "idempotency_key_reused"
        assert other_key.status_code == status.HTTP_201_CREATED
        assert len(self.tasks.create_calls) == 2
        assert self.tasks.create_calls[0]["origin_key"].startswith("ca:")
        assert self.tasks.create_calls[0]["origin_key"] != self.tasks.create_calls[1]["origin_key"]

    def test_replay_does_not_pass_the_gates_again(self) -> None:
        first = self.create(HTTP_IDEMPOTENCY_KEY="key-1")
        self.mocks["runs.cloud_agents_quota_denial"].return_value = "quota_exhausted"
        consumed = self.mocks["limits.consume"].call_count

        replay = self.create(HTTP_IDEMPOTENCY_KEY="key-1")

        assert (replay.status_code, replay.json()["id"]) == (status.HTTP_200_OK, first.json()["id"])
        assert self.mocks["limits.consume"].call_count == consumed

    def test_concurrent_request_with_the_same_key_replays_the_stored_run(self) -> None:
        first = self.create(HTTP_IDEMPOTENCY_KEY="key-1")
        with team_scope(self.team.id):
            winner = CloudAgentRun.objects.get(id=first.json()["id"])
            winner.idempotency_key = None
            winner.save()

        def store_the_winner(**kwargs: Any) -> InferenceDecision:
            # The other request stores its run after this request looked for the key and before it inserts.
            CloudAgentRun.all_teams.filter(id=winner.id).update(idempotency_key="key-1")
            return self.mocks["runs.resolve_inference"].return_value

        self.mocks["runs.resolve_inference"].side_effect = store_the_winner
        response = self.create(HTTP_IDEMPOTENCY_KEY="key-1")

        assert (response.status_code, response.json()["id"]) == (status.HTTP_200_OK, first.json()["id"])
        assert len(self.stored_runs()) == 1
        assert len(self.tasks.create_calls) == 1
        self.mocks["limits.refund"].assert_called_once()

    @parameterized.expand([("empty", " "), ("too_long", "k" * 101)])
    def test_invalid_idempotency_key_is_rejected(self, _name: str, key: str) -> None:
        response = self.create(HTTP_IDEMPOTENCY_KEY=key)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["attr"] == "Idempotency-Key"

    @parameterized.expand(
        [
            ("resets_soon", timedelta(hours=1), "3600"),
            ("reset_is_capped_at_a_day", timedelta(days=10), "86400"),
            ("reset_unknown", None, None),
        ]
    )
    def test_quota_denied(self, _name: str, reset_in: timedelta | None, retry_after: str | None) -> None:
        self.mocks["runs.cloud_agents_quota_denial"].return_value = "quota_exhausted"
        self.mocks["runs.cloud_agents_quota_reset_at"].return_value = NOW + reset_in if reset_in else None
        with time_machine.travel(NOW, tick=False):
            response = self.create()

        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert response.json()["code"] == "usage_limited"
        assert response.headers.get("Retry-After") == retry_after
        assert self.tasks.create_calls == []
        self.mocks["limits.consume"].assert_not_called()

    def test_deactivated_organization_is_refused(self) -> None:
        self.mocks["runs.cloud_agents_quota_denial"].return_value = "organization_deactivated"
        response = self.create()
        assert (response.status_code, response.json()["code"]) == (403, "organization_deactivated")

    def test_create_rate_limited(self) -> None:
        self.mocks["limits.consume"].return_value = BucketDecision(
            allowed=False, remaining=0, limit=10, retry_after=42, reset=600
        )
        response = self.create()

        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert (response.json()["code"], response.headers["Retry-After"]) == ("create_rate_limited", "42")
        assert self.tasks.create_calls == []

    def test_concurrency_limit_starts_nothing_and_refunds_the_rate(self) -> None:
        with team_scope(self.team.id):
            TeamCloudAgentsConfig.objects.create(team=self.team, max_concurrent_runs=1)
        assert self.create().status_code == status.HTTP_201_CREATED

        response = self.create()

        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert (response.json()["code"], response.headers["Retry-After"]) == ("concurrency_limited", "30")
        assert len(self.tasks.create_calls) == 1
        assert len(self.stored_runs()) == 1
        self.mocks["limits.refund"].assert_called_once()

    @parameterized.expand(
        [
            (
                "inference_unavailable",
                "runs.resolve_inference",
                InferenceUnavailable("Connect your Claude subscription first.", code="credential_missing"),
                "inference",
            ),
            (
                "tasks_refuses_the_model",
                "runs.create_cloud_agent_task",
                CloudAgentTaskInvalid("This model is not available to you.", attr="model"),
                "model",
            ),
        ]
    )
    def test_refused_start_leaves_no_run_and_refunds_the_rate(
        self, _name: str, target: str, error: Exception, attr: str
    ) -> None:
        self.mocks[target].side_effect = error
        response = self.create({**CREATE_BODY, "inference": "own_subscription"}, HTTP_IDEMPOTENCY_KEY="key-1")

        assert response.status_code == status.HTTP_400_BAD_REQUEST, response.json()
        assert (response.json()["attr"], response.json()["detail"]) == (attr, str(error))
        assert self.stored_runs() == []
        self.mocks["limits.refund"].assert_called_once()

    def test_failed_start_leaves_no_run_so_the_same_key_can_try_again(self) -> None:
        self.mocks["runs.create_cloud_agent_task"].side_effect = RuntimeError("database is down")
        self.client.raise_request_exception = False
        failed = self.create(HTTP_IDEMPOTENCY_KEY="key-1")
        self.mocks["runs.create_cloud_agent_task"].side_effect = self.tasks.create

        retried = self.create(HTTP_IDEMPOTENCY_KEY="key-1")

        assert failed.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert retried.status_code == status.HTTP_201_CREATED
        assert [str(run.id) for run in self.stored_runs()] == [retried.json()["id"]]

    def test_own_subscription_run_reports_who_pays_for_inference(self) -> None:
        self.mocks["runs.resolve_inference"].return_value = OWN_SUBSCRIPTION_DECISION
        body = self.create({**CREATE_BODY, "inference": "auto"}).json()

        assert body["config"]["inference"] == "own_subscription"
        assert body["cost"]["inference_billing"] == "own_subscription"
        assert self.tasks.create_calls[0]["inference_state"] == {"claude_model_access": "own-subscription"}
        assert self.mocks["runs.resolve_inference"].call_args.kwargs["requested"] == "auto"

    def test_internal_caller_is_not_billed_and_skips_the_quota(self) -> None:
        self.mocks["runs.cloud_agents_quota_denial"].return_value = "quota_exhausted"
        caller = CallerIdentity(
            user_id=self.user.id, distinct_id=None, kind=CallerKind.INTERNAL, billable=False, product="signals"
        )
        self.tasks.billing = billing_dto(billable=False)

        run, replayed = api.start_run(self.team.id, caller, RunCreateInput(**CREATE_BODY))

        assert replayed is False
        assert self.tasks.create_calls[0]["billable"] is False
        assert run.cost.billing_mode == BillingMode.UNBILLED
        assert run.caller_kind == CallerKind.INTERNAL
        assert api.get_run(self.team.id, run.id).cost.billing_mode == BillingMode.UNBILLED


@patch("products.tasks.backend.models.TaskRun.publish_stream_state_event", MagicMock())
@patch("products.tasks.backend.temporal.client.execute_task_processing_workflow", MagicMock())
class TestCreateRunWithTasks(CloudAgentsFlagMixin, APIBaseTest):
    def setUp(self) -> None:
        super().setUp()
        Integration.objects.create(team=self.team, kind="github", config={})

    def test_create_starts_a_tasks_run_without_the_desktop_access_gate(self) -> None:
        denied = AssertionError("Cloud Agents must not consult the PostHog Desktop access gate")
        with (
            patch("products.tasks.backend.facade.access.get_desktop_access_decision", side_effect=denied),
            patch("products.tasks.backend.facade.access.code_access_required_response", side_effect=denied),
            patch("products.tasks.backend.facade.access.usage_limit_response", side_effect=denied),
            patch("products.tasks.backend.access.get_desktop_access_decision", side_effect=denied),
            patch(
                f"{LOGIC}.limits.consume",
                return_value=BucketDecision(allowed=True, remaining=9, limit=10, retry_after=0, reset=0),
            ),
            patch("products.cloud_agents.backend.tasks.run_tasks.sync_cloud_agent_run.delay") as sync_delay,
            self.captureOnCommitCallbacks(execute=True),
        ):
            response = self.client.post(f"{self.base_url()}/runs/", data=CREATE_BODY, format="json")

        assert response.status_code == status.HTTP_201_CREATED, response.json()
        with team_scope(self.team.id):
            run = CloudAgentRun.objects.get(id=response.json()["id"])
        assert run.current_task_run_id is not None
        task_run = get_cloud_agent_task_run(team_id=self.team.id, run_id=run.current_task_run_id)
        assert task_run is not None
        assert task_run.state["cloud_agents_run_id"] == str(run.id)
        # The status signal of Tasks reaches this product for its own runs.
        sync_delay.assert_called_with(self.team.id, str(run.current_task_run_id))


class TestReadRuns(RunsAPITestCase):
    def test_list_filters(self) -> None:
        with team_scope(self.team.id):
            profile = CloudAgentProfile.objects.create(team=self.team, name="Backend")
        with time_machine.travel(NOW - timedelta(days=2), tick=False):
            old = self.make_run(repository="acme/api", tags=["ci"], profile=profile)
        with time_machine.travel(NOW, tick=False):
            new = self.make_run(status="completed")
        cases: list[tuple[str, list[CloudAgentRun]]] = [
            ("", [new, old]),
            ("?status=completed", [new]),
            ("?status=queued", [old]),
            (f"?profile_id={profile.id}", [old]),
            ("?repository=ACME/API", [old]),
            ("?repository=api", [old]),
            ("?repository=acme", [new, old]),
            ("?tag=ci", [old]),
            ("?tag=c", []),
            ("?created_after=2026-10-06T00:00:00Z", [new]),
            ("?created_before=2026-10-06T00:00:00Z", [old]),
        ]
        for query, expected in cases:
            body = self.client.get(self.runs_url(query)).json()
            assert [row["id"] for row in body["results"]] == [str(run.id) for run in expected], query
            assert body["count"] == len(expected), query

    def test_list_rejects_an_unknown_status(self) -> None:
        response = self.client.get(self.runs_url("?status=paused"))
        assert (response.status_code, response.json()["attr"]) == (status.HTTP_400_BAD_REQUEST, "status")

    def test_list_pages_do_not_repeat_or_skip_runs_created_at_the_same_instant(self) -> None:
        with time_machine.travel(NOW, tick=False):
            runs = [self.make_run() for _ in range(5)]
        expected = sorted((str(run.id) for run in runs), reverse=True)

        paged: list[str] = []
        for offset in range(0, 6, 2):
            page = self.client.get(self.runs_url(f"?limit=2&offset={offset}")).json()
            assert page["count"] == 5
            paged.extend(row["id"] for row in page["results"])
        assert paged == expected

    def test_retrieve_refreshes_a_stale_active_run_and_shows_the_live_cost(self) -> None:
        with time_machine.travel(NOW, tick=False):
            run = self.make_run(last_synced_at=NOW)
            self.tasks.set_status(run.current_task_run_id, "in_progress")
            self.tasks.billing = billing_dto(compute_cost_cents=12, inference_cost_cents=30)
            fresh = self.client.get(self.runs_url(f"{run.id}/")).json()
        with time_machine.travel(NOW + timedelta(seconds=6), tick=False):
            stale = self.client.get(self.runs_url(f"{run.id}/")).json()

        assert fresh["status"] == "queued"
        assert (stale["status"], stale["started_at"]) == ("running", "2026-10-07T12:00:06Z")
        assert stale["cost"] == {
            "compute_usd": "0.1200",
            "inference_usd": "0.3000",
            "total_usd": "0.4200",
            "vcpu_seconds": "0.000",
            "gib_seconds": "0.000",
            "billing_mode": "billed",
            "inference_billing": "posthog",
            "final": False,
        }

    def test_run_usage_lists_the_sandbox_sessions(self) -> None:
        run = self.make_run()
        self.tasks.billing = billing_dto(
            compute_cost_cents=37,
            inference_cost_cents=None,
            inference_billing="own_subscription",
            vcpu_seconds=Decimal("3600"),
            gib_seconds=Decimal("14400"),
            sessions=(
                SandboxSessionUsageDTO(
                    cpu_cores=4,
                    memory_gb=16,
                    started_at=NOW,
                    ended_at=NOW + timedelta(hours=1),
                    seconds=3600,
                    cost_cents=37,
                    waived=False,
                ),
            ),
        )
        response = self.client.get(self.runs_url(f"{run.id}/usage/"))

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {
            "run_id": str(run.id),
            "cost": {
                "compute_usd": "0.3700",
                "inference_usd": None,
                "total_usd": "0.3700",
                "vcpu_seconds": "3600.000",
                "gib_seconds": "14400.000",
                "billing_mode": "billed",
                "inference_billing": "own_subscription",
                "final": False,
            },
            "sessions": [
                {
                    "vcpu": "4",
                    "memory_gib": "16",
                    "started_at": "2026-10-07T12:00:00Z",
                    "ended_at": "2026-10-07T13:00:00Z",
                    "seconds": 3600,
                    "cost_usd": "0.3700",
                    "waived": False,
                }
            ],
        }

    @parameterized.expand(
        [
            ("newest_session_fits", [None, [{"n": 1}, {"n": 2}]], [{"n": 1}, {"n": 2}], False, 1),
            ("only_the_first_session_fits", [[{"n": 1}], None], [{"n": 1}], True, 2),
            ("nothing_fits", [None, None], [], True, 2),
        ]
    )
    def test_events_as_json(
        self, _name: str, history_by_session: list[Any], events: list[Any], truncated: bool, reads: int
    ) -> None:
        run = self.make_run(task_status="completed")
        second = task_run_dto(team_id=self.team.id, task_id=run.task_id)
        self.tasks.runs[second.id] = second
        history = dict(zip([run.current_task_run_id, second.id], history_by_session))
        self.mocks["runs.read_task_run_history"].side_effect = lambda run_id, *args, **kwargs: history[run_id]

        response = self.client.get(self.runs_url(f"{run.id}/events/"))

        assert response.status_code == status.HTTP_200_OK, response.content
        assert response.json() == {"events": events, "truncated": truncated}
        # The newest session is read first, because its history holds the sessions before it.
        assert self.mocks["runs.read_task_run_history"].call_args_list[0].args[0] == second.id
        assert self.mocks["runs.read_task_run_history"].call_count == reads

    @parameterized.expand(
        [
            ("accept_any", "", "*/*"),
            ("accept_json", "", "application/json"),
            ("format_json", "?format=json", None),
        ]
    )
    def test_events_default_to_json(self, _name: str, query: str, accept: str | None) -> None:
        run = self.make_run(task_status="completed")
        self.mocks["runs.read_task_run_history"].return_value = [{"n": 1}]

        url = self.runs_url(f"{run.id}/events/{query}")
        response = self.client.get(url, HTTP_ACCEPT=accept) if accept is not None else self.client.get(url)

        assert response.status_code == status.HTTP_200_OK, response.content
        assert response["Content-Type"].startswith("application/json")
        assert response.json() == {"events": [{"n": 1}], "truncated": False}

    def test_events_stream_sends_the_run_frame_then_the_tasks_stream(self) -> None:
        run = self.make_run(task_status="in_progress", status="running")
        source = object()

        async def tasks_stream(stream: object) -> Any:
            assert stream is source
            yield b"id: 7\ndata: {}\n\n"

        with (
            patch(f"{LOGIC}.streams.prepare_task_run_sse_stream", return_value=source) as prepare,
            patch(f"{LOGIC}.streams.task_run_sse_stream", tasks_stream),
        ):
            response = self.client.get(
                self.runs_url(f"{run.id}/events/?start=latest"),
                HTTP_ACCEPT="text/event-stream",
                HTTP_LAST_EVENT_ID="6",
            )

            body = b"".join(response.streaming_content)  # type: ignore[attr-defined]

        assert response.status_code == status.HTTP_200_OK
        assert response["Content-Type"].startswith("text/event-stream")
        frames = body.decode().split("\n\n")
        assert frames[0] == (f'event: run\ndata: {{"id": "{run.id}", "status": "running", "stop_reason": null}}')
        assert frames[1] == "id: 7\ndata: {}"
        prepare.assert_called_once_with(
            run.current_task_run_id, run.task_id, self.team.id, last_event_id="6", start_latest=True
        )


class TestSendMessage(RunsAPITestCase):
    def send(self, run: CloudAgentRun, **extra: Any) -> Any:
        return self.client.post(
            self.runs_url(f"{run.id}/messages/"), data={"content": "Also fix the lint"}, format="json", **extra
        )

    def test_live_run_gets_the_message_in_its_session(self) -> None:
        run = self.make_run(task_status="in_progress", status="running")
        response = self.send(run)

        assert response.status_code == status.HTTP_202_ACCEPTED, response.json()
        assert (response.json()["resumed"], response.json()["run"]["id"]) == (False, str(run.id))
        signal = self.mocks["runs.signal_task_run_user_message"]
        signal.assert_called_once_with(
            run.current_task_run_id,
            run.task_id,
            self.team.id,
            content="Also fix the lint",
            artifact_ids=[],
            actor_user_id=self.user.id,
        )
        assert self.tasks.resume_calls == []

    def test_stopped_run_resumes_with_its_stored_size_and_model(self) -> None:
        run = self.make_run(
            task_status="failed",
            status="failed",
            stop_reason="error",
            error="The run failed.",
            completed_at=NOW,
            cost_final=True,
            config={**RUN_CONFIG, "size": "8x32"},
        )
        previous_id = run.current_task_run_id
        response = self.send(run)

        assert response.status_code == status.HTTP_202_ACCEPTED, response.json()
        body = response.json()
        assert body["resumed"] is True
        assert (body["run"]["status"], body["run"]["stop_reason"], body["run"]["error"]) == ("queued", None, None)
        assert (body["run"]["completed_at"], body["run"]["cost"]["final"]) == (None, False)
        assert [session["index"] for session in body["run"]["agent_sessions"]] == [1, 2]
        (call,) = self.tasks.resume_calls
        assert call["previous_run_id"] == previous_id
        assert call["message"] == "Also fix the lint"
        assert (call["sandbox_size"], call["model"]) == (SandboxSize("8x32"), "claude-test-model")
        assert (call["user_id"], call["inference_state"]) == (self.user.id, None)
        self.mocks["runs.signal_task_run_user_message"].assert_not_called()
        with team_scope(self.team.id):
            run.refresh_from_db()
        assert run.current_task_run_id not in (None, previous_id)

    def test_workflow_that_is_gone_resumes_when_the_run_has_ended(self) -> None:
        run = self.make_run(task_status="in_progress", status="running")

        def workflow_gone(run_id: UUID, *args: Any, **kwargs: Any) -> bool:
            self.tasks.set_status(run_id, "completed")
            return False

        self.mocks["runs.signal_task_run_user_message"].side_effect = workflow_gone
        response = self.send(run)
        assert (response.status_code, response.json()["resumed"]) == (status.HTTP_202_ACCEPTED, True)

    @parameterized.expand(
        [
            (
                "stopping",
                "in_progress",
                "runs.signal_task_run_user_message",
                RuntimeError("stopping"),
                409,
                "run_stopping",
            ),
            (
                "workflow_gone_and_not_ended",
                "in_progress",
                "runs.signal_task_run_user_message",
                None,
                409,
                "run_stopping",
            ),
            (
                "usage_limit",
                "in_progress",
                "runs.signal_task_run_user_message",
                ComputeBillingLimitExceeded(),
                429,
                "usage_limited",
            ),
            (
                "not_resumable",
                "completed",
                "runs.resume_cloud_agent_task",
                CloudAgentRunNotResumable("The previous run belongs to an earlier owner"),
                409,
                "run_not_resumable",
            ),
        ]
    )
    def test_message_that_cannot_be_delivered(
        self, _name: str, task_status: str, target: str, error: Exception | None, http_status: int, code: str
    ) -> None:
        run = self.make_run(task_status=task_status)
        if error is None:
            self.mocks[target].side_effect = None
            self.mocks[target].return_value = False
        else:
            self.mocks[target].side_effect = error
        response = self.send(run)
        assert (response.status_code, response.json()["code"]) == (http_status, code)

    def test_quota_denied(self) -> None:
        run = self.make_run(task_status="in_progress")
        self.mocks["runs.cloud_agents_quota_denial"].return_value = "quota_exhausted"
        assert self.send(run).status_code == status.HTTP_429_TOO_MANY_REQUESTS
        self.mocks["runs.signal_task_run_user_message"].assert_not_called()

    @parameterized.expand([("live", "in_progress"), ("stopped", "completed")])
    def test_only_the_subscription_owner_continues_an_own_subscription_run(self, _name: str, task_status: str) -> None:
        owner = User.objects.create_and_join(self.organization, "owner@example.com", None)
        run = self.make_run(
            task_status=task_status, created_by=owner, config={**RUN_CONFIG, "inference": "own_subscription"}
        )

        response = self.send(run)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.json()["code"] == "credential_owner_required"
        assert "subscription of the user who started it" in response.json()["detail"]
        self.mocks["runs.signal_task_run_user_message"].assert_not_called()
        assert self.tasks.resume_calls == []

    def test_another_user_continues_a_posthog_inference_run_as_its_creator(self) -> None:
        owner = User.objects.create_and_join(self.organization, "owner@example.com", None)
        run = self.make_run(task_status="completed", created_by=owner)
        assert self.send(run).status_code == status.HTTP_202_ACCEPTED
        assert self.tasks.resume_calls[0]["user_id"] == owner.id

    def test_resume_counts_against_the_concurrency_limit(self) -> None:
        with team_scope(self.team.id):
            TeamCloudAgentsConfig.objects.create(team=self.team, max_concurrent_runs=1)
        self.make_run(task_status="in_progress")
        stopped = self.make_run(task_status="completed")

        response = self.send(stopped)

        assert (response.status_code, response.json()["code"]) == (429, "concurrency_limited")
        assert self.tasks.resume_calls == []


class TestCancelRun(RunsAPITestCase):
    @parameterized.expand(
        [
            ("accepted", 202),
            ("already_terminal", 200),
            ("unavailable", 503),
            ("not_cloud", 503),
            ("not_found", 404),
        ]
    )
    def test_cancel_outcome(self, outcome: str, http_status: int) -> None:
        run = self.make_run(task_status="completed" if outcome == "already_terminal" else "in_progress")
        self.mocks["runs.cancel_task_run"].return_value = (outcome, None)

        response = self.client.post(self.runs_url(f"{run.id}/cancel/"))

        assert response.status_code == http_status, response.json()
        if http_status == 200:
            assert response.json()["status"] == "completed"
        if http_status == 503:
            assert (response.json()["code"], response.headers["Retry-After"]) == ("cancel_unavailable", "5")
        args, kwargs = self.mocks["runs.cancel_task_run"].call_args
        assert args == (run.current_task_run_id, run.task_id, self.team.id)
        assert kwargs["requested_by_user_id"] == self.user.id

    def test_run_of_another_origin_is_never_cancelled(self) -> None:
        run = self.make_run(current_task_run_id=uuid4())
        assert self.client.post(self.runs_url(f"{run.id}/cancel/")).status_code == status.HTTP_404_NOT_FOUND
        self.mocks["runs.cancel_task_run"].assert_not_called()
