"""Celery beat schedules for cloud_agents.

Not auto-collected: posthog/tasks/scheduled.py imports these constants through the facade
(facade/tasks.py) and registers them in `setup_periodic_tasks`.
"""

from celery.schedules import crontab

# Once a day, at a quiet hour.
DELETE_OLD_WEBHOOK_DELIVERIES_CRONTAB = crontab(hour="4", minute="20")
