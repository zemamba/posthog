"""Celery beat schedules for cloud_agents.

Not auto-collected: posthog/tasks/scheduled.py imports these constants through the facade
(facade/tasks.py) and registers them in `setup_periodic_tasks`.
"""

from celery.schedules import crontab

# Once a day, at a quiet hour.
DELETE_OLD_WEBHOOK_DELIVERIES_CRONTAB = crontab(hour="4", minute="20")

# A lost webhook retry task is repaired by this persisted-schedule sweep.
RETRY_DUE_WEBHOOK_DELIVERIES_CRONTAB = crontab(minute="*/5")
# A run that the status signal of Tasks did not reach is repaired within this time.
RECONCILE_RUNS_CRONTAB = crontab(minute="*/5")
# A project over its usage limit loses its active billed runs within this time.
STOP_RUNS_OVER_QUOTA_CRONTAB = crontab(minute="*/5")
