"""One attempt to send a stored webhook delivery, and the retry policy.

The Celery task in tasks/tasks.py calls this module. It is separate from delivery.py, which
schedules that task, so that the two do not import each other.
"""

from __future__ import annotations

import json
from datetime import timedelta
from typing import Final
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from ...facade.enums import WebhookDeliveryStatus, WebhookEvent
from ...models import CloudAgentsWebhookDelivery
from . import sender
from .endpoints import get_or_create_secret

# Seconds to wait before retry 1, 2, and so on. A delivery that still fails after the last retry gives up.
RETRY_COUNTDOWNS: Final = (10, 60, 300, 1800, 7200, 21600)
MAX_RETRY_AFTER_SECONDS: Final = 6 * 60 * 60
# 4xx codes that tell the sender to try again. All other 4xx codes are final.
RETRYABLE_CLIENT_STATUS_CODES: Final = frozenset({408, 425, 429})
DELIVERY_RETENTION: Final = timedelta(days=30)
_DELETE_BATCH_SIZE: Final = 5000


def serialize_payload(payload: dict) -> bytes:
    """The exact bytes that are signed and sent. Sorted keys make every attempt send the same body."""
    return json.dumps(payload, separators=(",", ":"), sort_keys=True, ensure_ascii=False).encode()


def _is_retryable(result: sender.SendResult) -> bool:
    if result.blocked:
        return False
    if result.status_code is None:
        return True
    return result.status_code in RETRYABLE_CLIENT_STATUS_CODES or result.status_code >= 500


def attempt_delivery(team_id: int, delivery_id: UUID) -> int | None:
    """Send the delivery once and record the outcome.

    Returns the seconds to wait before the next attempt, or None when the delivery reached a final status.
    """
    with transaction.atomic():
        delivery = (
            CloudAgentsWebhookDelivery.objects.for_team(team_id).select_for_update().filter(id=delivery_id).first()
        )
        if delivery is None or delivery.status != WebhookDeliveryStatus.PENDING.value:
            return None
        if delivery.next_attempt_at is not None and delivery.next_attempt_at > timezone.now():
            return None

        secret, _ = get_or_create_secret(team_id)
        result = sender.post_signed(
            delivery.url,
            secret,
            str(delivery.event_id),
            WebhookEvent(delivery.event_type),
            serialize_payload(delivery.payload),
        )

        now = timezone.now()
        delivery.attempts += 1
        delivery.last_status_code = result.status_code
        delivery.last_error = result.error_class
        delivery.next_attempt_at = None
        countdown: int | None = None

        if result.status_code is not None and 200 <= result.status_code < 300:
            delivery.status = WebhookDeliveryStatus.SUCCEEDED.value
            delivery.delivered_at = now
        elif not _is_retryable(result):
            delivery.status = WebhookDeliveryStatus.FAILED.value
        elif delivery.attempts > len(RETRY_COUNTDOWNS):
            delivery.status = WebhookDeliveryStatus.GAVE_UP.value
        else:
            countdown = RETRY_COUNTDOWNS[delivery.attempts - 1]
            if result.retry_after is not None:
                # The receiver can ask for a longer wait, up to the cap. It cannot shorten the wait.
                countdown = max(countdown, min(result.retry_after, MAX_RETRY_AFTER_SECONDS))
            delivery.next_attempt_at = now + timedelta(seconds=countdown)

        delivery.save(
            update_fields=["status", "attempts", "last_status_code", "last_error", "next_attempt_at", "delivered_at"]
        )
        return countdown


def due_deliveries(limit: int = 500) -> list[tuple[int, UUID]]:
    return list(
        CloudAgentsWebhookDelivery.all_teams.filter(
            status=WebhookDeliveryStatus.PENDING.value,
            next_attempt_at__lte=timezone.now(),
        )
        .order_by("next_attempt_at")
        .values_list("team_id", "id")[:limit]
    )


def delete_expired_deliveries() -> int:
    """Delete deliveries older than the retention period, for all projects. Returns the number deleted."""
    cutoff = timezone.now() - DELIVERY_RETENTION
    deleted_total = 0
    while True:
        batch = list(
            CloudAgentsWebhookDelivery.all_teams.filter(created_at__lt=cutoff).values_list("id", flat=True)[
                :_DELETE_BATCH_SIZE
            ]
        )
        if not batch:
            return deleted_total
        deleted, _ = CloudAgentsWebhookDelivery.all_teams.filter(id__in=batch).delete()
        deleted_total += deleted
