"""Follow the runs of Tasks that belong to this product.

`AppConfig.ready()` imports this module at Django startup, so it imports the signal seam of
Tasks and nothing else of this product.
"""

from __future__ import annotations

from functools import partial
from typing import Any

from django.db import transaction

from products.tasks.backend.facade.task_run_signals import TaskOriginProduct, connect_task_run_status_changed

DISPATCH_UID = "cloud_agents_follow_task_run_status"


def connect() -> None:
    connect_task_run_status_changed(sync_run_on_task_run_status_change, dispatch_uid=DISPATCH_UID)


def _enqueue_sync(team_id: int, task_run_id: str) -> None:
    # Deferred: the task module loads the run logic and the Tasks facade, which Django startup must not pay for.
    from products.cloud_agents.backend.tasks.run_tasks import sync_cloud_agent_run  # noqa: PLC0415

    sync_cloud_agent_run.delay(team_id, task_run_id)


def sync_run_on_task_run_status_change(sender: Any, task_run: Any, **kwargs: Any) -> None:
    """Queue a sync when a run of this product changes status. Only plain columns of `task_run` are read."""
    if task_run.origin_product != TaskOriginProduct.CLOUD_AGENTS:
        return
    # The writer's transaction is still open. The worker must read the status that it commits.
    transaction.on_commit(partial(_enqueue_sync, task_run.team_id, str(task_run.id)))
