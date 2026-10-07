"""Create webhook deliveries for a run event and schedule them."""

from __future__ import annotations

from datetime import UTC, datetime
from functools import partial
from typing import Any, Final
from uuid import UUID

from django.db import transaction

from posthog.models.utils import uuid7

from ...facade.contracts import WebhookDeliveryDTO
from ...facade.enums import WebhookDeliveryStatus, WebhookEvent
from ...models import CloudAgentRun, CloudAgentsWebhookDelivery, CloudAgentsWebhookEndpoint
from ...tasks.tasks import deliver_webhook
from .endpoints import get_endpoint

API_VERSION: Final = "2026-10-01"
RECENT_DELIVERIES_LIMIT: Final = 50


def build_envelope(event_id: UUID, event_type: WebhookEvent, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(event_id),
        "type": event_type.value,
        "created_at": datetime.now(UTC).isoformat(),
        "api_version": API_VERSION,
        "data": {"run": payload},
    }


def to_delivery_dto(delivery: CloudAgentsWebhookDelivery) -> WebhookDeliveryDTO:
    return WebhookDeliveryDTO(
        id=delivery.id,
        endpoint_id=delivery.endpoint_id,
        url=delivery.url,
        run_id=delivery.run_id,
        event_type=WebhookEvent(delivery.event_type),
        event_id=delivery.event_id,
        status=WebhookDeliveryStatus(delivery.status),
        attempts=delivery.attempts,
        last_status_code=delivery.last_status_code,
        last_error=delivery.last_error,
        next_attempt_at=delivery.next_attempt_at,
        delivered_at=delivery.delivered_at,
        created_at=delivery.created_at,
    )


def _create_and_schedule(
    team_id: int,
    run_id: UUID,
    event_type: WebhookEvent,
    payload: dict[str, Any],
    targets: list[tuple[UUID | None, str]],
) -> list[UUID]:
    if not targets:
        return []
    # One event id for all targets, so a receiver behind two endpoints can drop the duplicate.
    event_id = uuid7()
    envelope = build_envelope(event_id, event_type, payload)
    delivery_ids: list[UUID] = []
    with transaction.atomic():
        for endpoint_id, url in targets:
            delivery = CloudAgentsWebhookDelivery.objects.for_team(team_id).create(
                team_id=team_id,
                endpoint_id=endpoint_id,
                url=url,
                run_id=run_id,
                event_type=event_type.value,
                event_id=event_id,
                payload=envelope,
            )
            delivery_ids.append(delivery.id)
            # After the commit, so the worker never looks for a row that a rollback removed.
            transaction.on_commit(partial(deliver_webhook.delay, str(delivery.id), team_id))
    return delivery_ids


def enqueue_run_event(team_id: int, run_id: UUID, event_type: WebhookEvent, payload: dict[str, Any]) -> list[UUID]:
    """Create one delivery per enabled endpoint that takes this event, plus one for the run's own URL.

    `payload` is the public shape of the run. Returns the ids of the new deliveries.
    """
    targets: list[tuple[UUID | None, str]] = [
        (endpoint.id, endpoint.url)
        for endpoint in CloudAgentsWebhookEndpoint.objects.for_team(team_id).filter(enabled=True).order_by("created_at")
        if not endpoint.event_types or event_type.value in endpoint.event_types
    ]
    run_webhook_url = (
        CloudAgentRun.objects.for_team(team_id).filter(id=run_id).values_list("webhook_url", flat=True).first()
    )
    if run_webhook_url and run_webhook_url not in {url for _, url in targets}:
        targets.append((None, run_webhook_url))
    return _create_and_schedule(team_id, run_id, event_type, payload, targets)


def send_test_event(team_id: int, endpoint_id: UUID) -> UUID:
    """Send a `run.test` event to one endpoint, also when it is disabled or filters event types."""
    endpoint = get_endpoint(team_id, endpoint_id)
    run_id = uuid7()
    payload = {
        "id": str(run_id),
        "status": "completed",
        "stop_reason": "done",
        "prompt": "This is a test event. No run was started.",
    }
    (delivery_id,) = _create_and_schedule(
        team_id, run_id, WebhookEvent.RUN_TEST, payload, [(endpoint.id, endpoint.url)]
    )
    return delivery_id


def list_recent_deliveries(team_id: int, limit: int = RECENT_DELIVERIES_LIMIT) -> list[WebhookDeliveryDTO]:
    deliveries = CloudAgentsWebhookDelivery.objects.for_team(team_id).order_by("-created_at")[:limit]
    return [to_delivery_dto(delivery) for delivery in deliveries]
