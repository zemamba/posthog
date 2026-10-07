from datetime import UTC, datetime, timedelta
from typing import Any

import time_machine
from posthog.test.base import BaseTest
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

import requests
from parameterized import parameterized

from posthog.models import Team
from posthog.models.utils import uuid7
from posthog.security.pinned_requests import SSRFBlockedError

from products.cloud_agents.backend.facade.enums import WebhookEvent
from products.cloud_agents.backend.logic.webhooks import sender
from products.cloud_agents.backend.logic.webhooks.attempts import (
    RETRY_COUNTDOWNS,
    delete_expired_deliveries,
    serialize_payload,
)
from products.cloud_agents.backend.logic.webhooks.delivery import API_VERSION, enqueue_run_event
from products.cloud_agents.backend.logic.webhooks.endpoints import get_or_create_secret
from products.cloud_agents.backend.logic.webhooks.signing import verify
from products.cloud_agents.backend.models import CloudAgentRun, CloudAgentsWebhookDelivery, CloudAgentsWebhookEndpoint
from products.cloud_agents.backend.tasks.tasks import deliver_webhook

NOW = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
POST_SIGNED = "products.cloud_agents.backend.logic.webhooks.sender.post_signed"
SIX_HOURS = 6 * 60 * 60


def _result(status_code: int | None = None, error_class: str | None = None, **kwargs: Any) -> sender.SendResult:
    return sender.SendResult(status_code=status_code, error_class=error_class, **kwargs)


class TestDeliverWebhook(BaseTest):
    def _delivery(self, **kwargs: Any) -> CloudAgentsWebhookDelivery:
        event_id = uuid7()
        return CloudAgentsWebhookDelivery.objects.create(
            team=self.team,
            url="https://example.com/hook",
            run_id=uuid7(),
            event_type=WebhookEvent.RUN_COMPLETED.value,
            event_id=event_id,
            payload={"id": str(event_id), "type": "run.completed", "data": {"run": {"status": "completed"}}},
            **kwargs,
        )

    @parameterized.expand(
        [
            # name, send result, attempts before, expected status, expected countdown
            ("ok", _result(200), 0, "succeeded", None),
            ("accepted", _result(202), 0, "succeeded", None),
            ("server_error_retries", _result(503), 0, "pending", RETRY_COUNTDOWNS[0]),
            ("bad_gateway_second_retry", _result(502), 1, "pending", RETRY_COUNTDOWNS[1]),
            ("timeout_status_retries", _result(408), 0, "pending", RETRY_COUNTDOWNS[0]),
            ("too_early_retries", _result(425), 0, "pending", RETRY_COUNTDOWNS[0]),
            ("rate_limited_retries", _result(429), 0, "pending", RETRY_COUNTDOWNS[0]),
            ("transport_error_retries", _result(None, "ConnectTimeout"), 0, "pending", RETRY_COUNTDOWNS[0]),
            ("gone_fails", _result(410), 0, "failed", None),
            ("bad_request_fails", _result(400), 0, "failed", None),
            ("redirect_fails", _result(302), 0, "failed", None),
            ("blocked_url_fails", _result(None, "SSRFBlockedError", blocked=True), 0, "failed", None),
            ("last_retry", _result(503), len(RETRY_COUNTDOWNS) - 1, "pending", RETRY_COUNTDOWNS[-1]),
            ("retries_exhausted", _result(503), len(RETRY_COUNTDOWNS), "gave_up", None),
            ("retry_after_extends_wait", _result(429, retry_after=120), 0, "pending", 120),
            ("retry_after_cannot_shorten_wait", _result(429, retry_after=1), 0, "pending", RETRY_COUNTDOWNS[0]),
            ("retry_after_is_capped", _result(503, retry_after=SIX_HOURS * 4), 0, "pending", SIX_HOURS),
        ]
    )
    def test_outcome(
        self, _name: str, result: sender.SendResult, attempts: int, expected_status: str, countdown: int | None
    ) -> None:
        delivery = self._delivery(attempts=attempts)
        with (
            time_machine.travel(NOW, tick=False),
            patch(POST_SIGNED, return_value=result),
            patch.object(deliver_webhook, "apply_async") as apply_async,
        ):
            deliver_webhook(str(delivery.id), self.team.id)

        delivery.refresh_from_db()
        assert delivery.status == expected_status
        assert delivery.attempts == attempts + 1
        assert delivery.last_status_code == result.status_code
        assert delivery.last_error == result.error_class
        assert delivery.delivered_at == (NOW if expected_status == "succeeded" else None)
        if countdown is None:
            assert delivery.next_attempt_at is None
            apply_async.assert_not_called()
        else:
            assert delivery.next_attempt_at == NOW + timedelta(seconds=countdown)
            apply_async.assert_called_once_with(args=[str(delivery.id), self.team.id], countdown=countdown)

    @parameterized.expand([("succeeded",), ("failed",), ("gave_up",)])
    def test_final_delivery_is_not_sent_again(self, status: str) -> None:
        delivery = self._delivery(status=status, attempts=2)
        with patch(POST_SIGNED) as post_signed:
            deliver_webhook(str(delivery.id), self.team.id)
        post_signed.assert_not_called()

    def test_request_is_signed_with_the_team_secret(self) -> None:
        delivery = self._delivery()
        secret, _ = get_or_create_secret(self.team.id)
        with patch(POST_SIGNED, return_value=_result(200)) as post_signed:
            deliver_webhook(str(delivery.id), self.team.id)

        url, used_secret, event_id, event_type, body = post_signed.call_args.args
        assert (url, used_secret, event_id) == (delivery.url, secret, str(delivery.event_id))
        assert event_type == WebhookEvent.RUN_COMPLETED
        assert body == serialize_payload(delivery.payload)

    def test_other_team_cannot_trigger_a_delivery(self) -> None:
        delivery = self._delivery()
        other_team = Team.objects.create(organization=self.organization, name="Other team")
        with patch(POST_SIGNED) as post_signed:
            deliver_webhook(str(delivery.id), other_team.id)
        post_signed.assert_not_called()

    def test_retention_deletes_only_old_deliveries(self) -> None:
        with time_machine.travel(NOW - timedelta(days=31), tick=False):
            old = self._delivery()
        with time_machine.travel(NOW - timedelta(days=29), tick=False):
            recent = self._delivery()
        with time_machine.travel(NOW, tick=False):
            assert delete_expired_deliveries() == 1
        assert not CloudAgentsWebhookDelivery.objects.filter(id=old.id).exists()
        assert CloudAgentsWebhookDelivery.objects.filter(id=recent.id).exists()


class TestPostSigned(SimpleTestCase):
    def _send(self, response: Any = None, error: Exception | None = None) -> tuple[sender.SendResult, MagicMock]:
        session = MagicMock()
        session.prepare_request.side_effect = lambda request: request.prepare()
        session.merge_environment_settings.return_value = {"verify": None, "cert": None, "proxies": {}}
        adapter_send = session.get_adapter.return_value.send
        adapter_send.return_value = response
        adapter_send.side_effect = error
        with (
            time_machine.travel(NOW, tick=False),
            patch("products.cloud_agents.backend.logic.webhooks.sender.pinned_session") as pinned_session,
        ):
            if isinstance(error, SSRFBlockedError):
                pinned_session.side_effect = error
            else:
                pinned_session.return_value.__enter__.return_value = session
            result = sender.post_signed(
                "https://example.com/hook", "whsec_test", "evt-1", WebhookEvent.RUN_FAILED, b'{"a":1}'
            )
        return result, adapter_send

    def test_headers_carry_a_signature_the_receiver_can_verify(self) -> None:
        result, adapter_send = self._send(MagicMock(status_code=204, headers={}))
        request = adapter_send.call_args.args[0]
        headers = request.headers

        assert result == _result(204)
        assert headers["X-PostHog-Webhook-Id"] == "evt-1"
        assert headers["X-PostHog-Webhook-Event"] == "run.failed"
        assert headers["Content-Type"] == "application/json"
        assert headers["User-Agent"] == "PostHog-CloudAgents-Webhooks/1"
        assert headers["X-PostHog-Webhook-Timestamp"] == str(int(NOW.timestamp()))
        assert headers["X-PostHog-Webhook-Signature"].startswith("v1=")
        assert verify(
            "whsec_test", headers["X-PostHog-Webhook-Timestamp"], request.body, headers["X-PostHog-Webhook-Signature"]
        )
        # No redirect is followed and no body is read.
        assert adapter_send.call_args.kwargs["stream"] is True
        assert adapter_send.call_args.kwargs["timeout"] == (3.0, 5.0)

    @parameterized.expand(
        [
            ("retry_after_seconds", {"Retry-After": "30"}, 30),
            ("retry_after_date_is_ignored", {"Retry-After": "Wed, 21 Oct 2026 07:28:00 GMT"}, None),
            ("no_header", {}, None),
        ]
    )
    def test_retry_after_header(self, _name: str, headers: dict[str, str], expected: int | None) -> None:
        result, _ = self._send(MagicMock(status_code=429, headers=headers))
        assert result == _result(429, retry_after=expected)

    @parameterized.expand(
        [
            ("timeout", requests.ConnectTimeout("https://example.com/hook timed out"), "ConnectTimeout", False),
            ("connection", requests.ConnectionError("https://example.com/hook refused"), "ConnectionError", False),
            ("blocked", SSRFBlockedError("Disallowed target IP: 10.0.0.5"), "SSRFBlockedError", True),
        ]
    )
    def test_failure_names_only_the_exception_class(
        self, _name: str, error: Exception, error_class: str, blocked: bool
    ) -> None:
        result, _ = self._send(error=error)
        assert result == _result(None, error_class, blocked=blocked)


class TestEnqueueRunEvent(BaseTest):
    def _endpoint(self, path: str, **kwargs: Any) -> CloudAgentsWebhookEndpoint:
        return CloudAgentsWebhookEndpoint.objects.create(team=self.team, url=f"https://example.com/{path}", **kwargs)

    def _run(self, webhook_url: str | None = None) -> CloudAgentRun:
        return CloudAgentRun.objects.create(
            team=self.team, prompt="Fix the bug", repository="acme/app", webhook_url=webhook_url
        )

    def _enqueue(self, run: CloudAgentRun, event_type: WebhookEvent) -> tuple[list[Any], MagicMock]:
        with patch.object(deliver_webhook, "delay") as delay:
            with self.captureOnCommitCallbacks(execute=True):
                delivery_ids = enqueue_run_event(self.team.id, run.id, event_type, {"id": str(run.id)})
                # Nothing is scheduled before the transaction commits.
                delay.assert_not_called()
        return delivery_ids, delay

    def test_targets_matching_enabled_endpoints_and_the_run_url(self) -> None:
        all_events = self._endpoint("all")
        matching = self._endpoint("matching", event_types=["run.completed", "run.failed"])
        self._endpoint("other-event", event_types=["run.started"])
        self._endpoint("disabled", enabled=False)
        other_team = Team.objects.create(organization=self.organization, name="Other team")
        CloudAgentsWebhookEndpoint.all_teams.create(team=other_team, url="https://example.com/other-team")
        run = self._run(webhook_url="https://example.com/run")

        delivery_ids, delay = self._enqueue(run, WebhookEvent.RUN_COMPLETED)

        deliveries = list(CloudAgentsWebhookDelivery.objects.order_by("created_at", "id"))
        assert [delivery.id for delivery in deliveries] == delivery_ids
        assert {(delivery.endpoint_id, delivery.url) for delivery in deliveries} == {
            (all_events.id, all_events.url),
            (matching.id, matching.url),
            (None, "https://example.com/run"),
        }
        assert sorted(call.args for call in delay.call_args_list) == sorted(
            (str(delivery_id), self.team.id) for delivery_id in delivery_ids
        )

    def test_envelope(self) -> None:
        self._endpoint("a")
        self._endpoint("b")
        run = self._run()
        with time_machine.travel(NOW, tick=False):
            self._enqueue(run, WebhookEvent.RUN_FAILED)

        first, second = CloudAgentsWebhookDelivery.objects.all()
        assert first.event_id == second.event_id
        assert first.payload == {
            "id": str(first.event_id),
            "type": "run.failed",
            "created_at": NOW.isoformat(),
            "api_version": API_VERSION,
            "data": {"run": {"id": str(run.id)}},
        }
        assert (first.run_id, first.event_type, first.status, first.attempts) == (run.id, "run.failed", "pending", 0)

    @parameterized.expand(
        [
            ("no_targets", None, False, 0),
            ("run_url_only", "https://example.com/run", False, 1),
            ("run_url_equal_to_endpoint_is_sent_once", "https://example.com/all", True, 1),
        ]
    )
    def test_run_url(self, _name: str, webhook_url: str | None, with_endpoint: bool, expected: int) -> None:
        if with_endpoint:
            self._endpoint("all")
        delivery_ids, delay = self._enqueue(self._run(webhook_url=webhook_url), WebhookEvent.RUN_STARTED)
        assert len(delivery_ids) == expected
        assert delay.call_count == expected
