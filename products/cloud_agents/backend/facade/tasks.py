"""Celery tasks and schedules that core registers. See posthog/tasks/scheduled.py."""

from ..tasks.schedules import DELETE_OLD_WEBHOOK_DELIVERIES_CRONTAB
from ..tasks.tasks import delete_old_webhook_deliveries

__all__ = ["DELETE_OLD_WEBHOOK_DELIVERIES_CRONTAB", "delete_old_webhook_deliveries"]
