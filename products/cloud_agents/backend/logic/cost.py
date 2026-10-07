"""Copy the cost of a run from the Tasks usage ledger to its `CloudAgentRun` row."""

from __future__ import annotations

from decimal import Decimal
from typing import Final
from uuid import UUID

from django.db import transaction

from products.tasks.backend.facade.billing import get_task_run_billing
from products.tasks.backend.facade.contracts import TaskRunBillingDTO

from ..facade.contracts import RunUsageDTO, SandboxSessionUsageDTO
from ..facade.enums import BillingMode, InferenceBilling
from ..models import CloudAgentRun
from .analytics import capture_event_in_task
from .run_rows import get_run_row, to_cost_dto

_USD_PLACES: Final = Decimal("0.0001")
_SECONDS_PLACES: Final = Decimal("0.001")


def cents_to_usd(cents: int | None) -> Decimal | None:
    return None if cents is None else (Decimal(cents) / 100).quantize(_USD_PLACES)


def apply_billing(run: CloudAgentRun, billing: TaskRunBillingDTO) -> list[str]:
    """Set the cost fields of `run` from `billing`. Returns the names of the fields that it set."""
    inference_billing = InferenceBilling(billing.inference_billing)
    run.compute_usd = cents_to_usd(billing.compute_cost_cents)
    # The customer pays the model provider directly for a run on their own credential, so PostHog has no cost to show.
    run.inference_usd = (
        cents_to_usd(billing.inference_cost_cents) if inference_billing == InferenceBilling.POSTHOG else None
    )
    run.vcpu_seconds = billing.vcpu_seconds.quantize(_SECONDS_PLACES)
    run.gib_seconds = billing.gib_seconds.quantize(_SECONDS_PLACES)
    run.billing_mode = (BillingMode.BILLED if billing.billable else BillingMode.UNBILLED).value
    run.inference_billing = inference_billing.value
    run.cost_final = billing.settled
    return [
        "compute_usd",
        "inference_usd",
        "vcpu_seconds",
        "gib_seconds",
        "billing_mode",
        "inference_billing",
        "cost_final",
    ]


def _completed_event_properties(run: CloudAgentRun) -> dict[str, object]:
    duration_s = (
        int((run.completed_at - run.started_at).total_seconds()) if run.started_at and run.completed_at else None
    )
    return {
        "run_id": str(run.id),
        "status": run.status,
        "stop_reason": run.stop_reason,
        "duration_s": duration_s,
        "size": run.config.get("size"),
        "billing_mode": run.billing_mode,
        "inference_billing": run.inference_billing,
        "compute_usd": float(run.compute_usd) if run.compute_usd is not None else None,
        "inference_usd": float(run.inference_usd) if run.inference_usd is not None else None,
        "caller_kind": run.caller_kind,
        "caller_product": run.caller_product,
    }


def refresh_run_cost(team_id: int, run_id: UUID) -> bool:
    """Read the ledger and store the cost of the run. Returns True when the cost is final.

    Call it from a Celery task: the first call that finds a final cost captures the
    `cloud_agents_run_completed` event with the Celery-safe client.
    """
    with transaction.atomic():
        run = CloudAgentRun.objects.for_team(team_id).select_for_update().filter(id=run_id).first()
        if run is None or run.task_id is None:
            # A run with no task has no ledger rows, so there is nothing to wait for.
            return True
        if run.cost_final:
            return True
        billing = get_task_run_billing(team_id=team_id, task_id=run.task_id)
        run.save(update_fields=[*apply_billing(run, billing), "updated_at"])
        became_final = billing.settled
    if became_final:
        capture_event_in_task(
            "cloud_agents_run_completed", team_id, run.created_by_id, _completed_event_properties(run)
        )
    return became_final


def get_run_usage(team_id: int, run_id: UUID) -> RunUsageDTO:
    """The cost of a run and its sandbox sessions, read from the ledger now."""
    run = get_run_row(team_id, run_id)
    if run.task_id is None:
        return RunUsageDTO(run_id=run.id, cost=to_cost_dto(run), sessions=[])
    billing = get_task_run_billing(team_id=team_id, task_id=run.task_id)
    if not run.cost_final:
        # Shown, not saved: the finalization task stores the cost, so that it captures the completion event one time.
        apply_billing(run, billing)
    return RunUsageDTO(
        run_id=run.id,
        cost=to_cost_dto(run),
        sessions=[
            SandboxSessionUsageDTO(
                vcpu=Decimal(str(session.cpu_cores)),
                memory_gib=Decimal(str(session.memory_gb)),
                started_at=session.started_at,
                ended_at=session.ended_at,
                seconds=session.seconds,
                cost_usd=cents_to_usd(session.cost_cents) or Decimal(0),
                waived=session.waived,
            )
            for session in billing.sessions
        ],
    )
