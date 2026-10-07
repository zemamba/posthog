"""
Celery tasks for the lifecycle of a run.

Async entrypoints. Keep task functions thin: the work is in logic/.
"""

from __future__ import annotations

from typing import Final
from uuid import UUID

import structlog
from celery import shared_task

from posthog.models.scoping import with_team_scope
from posthog.scoping_audit import skip_team_scope_audit

# Module imports, not names: logic/sync.py starts these tasks, so each side reads the other at call time.
from ..logic import (
    cost as cost_logic,
    sweeps as sweeps_logic,
    sync as sync_logic,
)

logger = structlog.get_logger(__name__)

# The ledger settles when the sandbox session closes and the last model usage arrives. The delays
# add up to 30 minutes. After that the reconciler asks again on its own schedule.
FINALIZE_RETRY_DELAYS_SECONDS: Final = (30, 60, 120, 240, 480, 870)


@shared_task(ignore_result=True, max_retries=0)
@with_team_scope()
def sync_cloud_agent_run(team_id: int, task_run_id: str) -> None:
    sync_logic.apply_task_run_update(team_id, UUID(task_run_id))


@shared_task(ignore_result=True, max_retries=0)
@with_team_scope()
def finalize_run_cost(team_id: int, run_id: str, attempt: int = 0, retry: bool = True) -> None:
    if cost_logic.refresh_run_cost(team_id, UUID(run_id)):
        return
    if retry and attempt < len(FINALIZE_RETRY_DELAYS_SECONDS):
        # A new task and not `self.retry`, so a failed attempt never counts against a Celery retry limit.
        finalize_run_cost.apply_async(
            args=[team_id, run_id], kwargs={"attempt": attempt + 1}, countdown=FINALIZE_RETRY_DELAYS_SECONDS[attempt]
        )


@shared_task(ignore_result=True)
@skip_team_scope_audit  # The reconciler finds stale runs in all projects, then updates each in its own scope.
def reconcile_cloud_agent_runs() -> None:
    logger.info("cloud_agents_runs_reconciled", seen=sync_logic.reconcile_runs())


@shared_task(ignore_result=True)
@skip_team_scope_audit  # The sweep starts from the projects that Tasks reports, then reads each in its own scope.
def stop_cloud_agent_runs_over_quota() -> None:
    logger.info("cloud_agents_quota_sweep_done", cancelled=sweeps_logic.stop_runs_over_quota())
