"""
Celery tasks for cloud_agents.

Async entrypoints. Keep task functions thin: the work is in logic/.
"""

from __future__ import annotations

from uuid import UUID

import structlog
from celery import shared_task

from posthog.models.scoping import with_team_scope
from posthog.scoping_audit import skip_team_scope_audit

from ..logic.webhooks.attempts import attempt_delivery, delete_expired_deliveries

logger = structlog.get_logger(__name__)


@shared_task(ignore_result=True, max_retries=0)
@with_team_scope()
def deliver_webhook(delivery_id: str, team_id: int) -> None:
    countdown = attempt_delivery(team_id, UUID(delivery_id))
    if countdown is not None:
        # A new task and not `self.retry`, because the retry state is in the delivery row. A lost
        # task then leaves a row that shows the next attempt time.
        deliver_webhook.apply_async(args=[delivery_id, team_id], countdown=countdown)


@shared_task(ignore_result=True)
@skip_team_scope_audit  # Retention applies to all projects, so the delete has no team scope.
def delete_old_webhook_deliveries() -> None:
    deleted = delete_expired_deliveries()
    logger.info("cloud_agents_webhook_deliveries_deleted", deleted=deleted)
