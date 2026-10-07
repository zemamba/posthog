"""Read `CloudAgentRun` rows and turn them into the public shape of a run."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from django.db.models import QuerySet

from products.tasks.backend.facade.pricing import cloud_agents_hourly_price_usd

from ..facade.contracts import (
    AgentSessionDTO,
    ResolvedRunConfig,
    RunCostDTO,
    RunDTO,
    RunNotFound,
    RunResultDTO,
    SizeSpec,
)
from ..facade.enums import (
    BillingMode,
    CallerKind,
    CloudAgentRunStatus,
    InferenceBilling,
    SizeName,
    StopReason,
    size_shape,
)
from ..models import CloudAgentRun


def run_rows(team_id: int) -> QuerySet[CloudAgentRun]:
    return CloudAgentRun.objects.for_team(team_id).select_related("created_by", "profile")


def get_run_row(team_id: int, run_id: UUID) -> CloudAgentRun:
    run = run_rows(team_id).filter(id=run_id).first()
    if run is None:
        raise RunNotFound()
    return run


def size_spec(size: SizeName) -> SizeSpec:
    shape = size_shape(size)
    return SizeSpec.from_name(size, price_per_hour_usd=cloud_agents_hourly_price_usd(shape.vcpu, shape.memory_gib))


def _parse_time(value: object) -> datetime | None:
    return datetime.fromisoformat(value) if isinstance(value, str) and value else None


def _format_time(value: datetime | None) -> str | None:
    # The same text that the REST API writes for a time, so a webhook receiver can share a parser.
    return value.isoformat().replace("+00:00", "Z") if value is not None else None


def session_entry(
    *,
    index: int,
    task_run_id: UUID,
    status: CloudAgentRunStatus,
    started_at: datetime | None,
    ended_at: datetime | None,
) -> dict[str, Any]:
    """One item of `CloudAgentRun.agent_sessions`."""
    return {
        "index": index,
        "task_run_id": str(task_run_id),
        "status": status.value,
        "started_at": _format_time(started_at),
        "ended_at": _format_time(ended_at),
    }


def _to_session_dto(entry: dict[str, Any]) -> AgentSessionDTO:
    return AgentSessionDTO(
        index=entry["index"],
        task_run_id=UUID(entry["task_run_id"]),
        status=CloudAgentRunStatus(entry["status"]),
        started_at=_parse_time(entry.get("started_at")),
        ended_at=_parse_time(entry.get("ended_at")),
    )


def to_cost_dto(run: CloudAgentRun) -> RunCostDTO:
    total_usd = None if run.compute_usd is None else run.compute_usd + (run.inference_usd or Decimal(0))
    return RunCostDTO(
        compute_usd=run.compute_usd,
        inference_usd=run.inference_usd,
        total_usd=total_usd,
        vcpu_seconds=run.vcpu_seconds,
        gib_seconds=run.gib_seconds,
        billing_mode=BillingMode(run.billing_mode),
        inference_billing=InferenceBilling(run.inference_billing) if run.inference_billing else None,
        final=run.cost_final,
    )


def to_run_dto(run: CloudAgentRun) -> RunDTO:
    config = ResolvedRunConfig.from_json(run.config)
    # A soft-deleted profile keeps its row, so the run still names the profile it used.
    profile = run.profile
    created_by = run.created_by
    return RunDTO(
        id=run.id,
        status=CloudAgentRunStatus(run.status),
        stop_reason=StopReason(run.stop_reason) if run.stop_reason else None,
        error=run.error,
        created_at=run.created_at,
        updated_at=run.updated_at,
        started_at=run.started_at,
        completed_at=run.completed_at,
        prompt=run.prompt,
        repository=run.repository,
        branch=run.branch,
        profile_id=profile.id if profile is not None else None,
        profile_name=profile.name if profile is not None else None,
        config=config,
        size=size_spec(config.size),
        result=RunResultDTO(pr_url=run.pr_url, pr_urls=list(run.pr_urls or []), summary=run.summary),
        cost=to_cost_dto(run),
        agent_sessions=[_to_session_dto(entry) for entry in run.agent_sessions or []],
        tags=list(run.tags or []),
        metadata=dict(run.metadata or {}),
        created_by_id=created_by.id if created_by is not None else None,
        created_by_email=created_by.email if created_by is not None else None,
        caller_kind=CallerKind(run.caller_kind),
    )


def _decimal(value: Decimal | None) -> str | None:
    return None if value is None else str(value)


def format_price(value: Decimal) -> str:
    """A price without trailing zeros, for example `0.368`."""
    return format(value.normalize(), "f")


def run_payload(run: RunDTO) -> dict[str, Any]:
    """The JSON shape of a run in a webhook event. It is the same shape that the REST API returns."""
    return {
        "id": str(run.id),
        "status": run.status.value,
        "stop_reason": run.stop_reason.value if run.stop_reason else None,
        "error": run.error,
        "created_at": _format_time(run.created_at),
        "started_at": _format_time(run.started_at),
        "completed_at": _format_time(run.completed_at),
        "updated_at": _format_time(run.updated_at),
        "prompt": run.prompt,
        "repository": run.repository,
        "branch": run.branch,
        "profile": {"id": str(run.profile_id), "name": run.profile_name} if run.profile_id else None,
        "config": {
            "model": run.config.model,
            "size": {
                "name": run.size.name.value,
                "vcpu": run.size.vcpu,
                "memory_gib": run.size.memory_gib,
                "price_per_hour_usd": format_price(run.size.price_per_hour_usd),
            },
            "inference": run.config.inference.value,
            "create_pr": run.config.create_pr,
            "pr_mode": run.config.pr_mode.value,
            "max_duration_minutes": run.config.max_duration_minutes,
            "max_cost_usd": _decimal(run.config.max_cost_usd),
            "instructions_applied": bool(run.config.instructions),
        },
        "result": {"pr_url": run.result.pr_url, "pr_urls": run.result.pr_urls, "summary": run.result.summary},
        "cost": {
            "compute_usd": _decimal(run.cost.compute_usd),
            "inference_usd": _decimal(run.cost.inference_usd),
            "total_usd": _decimal(run.cost.total_usd),
            "vcpu_seconds": _decimal(run.cost.vcpu_seconds),
            "gib_seconds": _decimal(run.cost.gib_seconds),
            "billing_mode": run.cost.billing_mode.value,
            "inference_billing": run.cost.inference_billing.value if run.cost.inference_billing else None,
            "final": run.cost.final,
        },
        "agent_sessions": [
            {
                "index": session.index,
                "status": session.status.value,
                "started_at": _format_time(session.started_at),
                "ended_at": _format_time(session.ended_at),
            }
            for session in run.agent_sessions
        ],
        "tags": run.tags,
        "metadata": run.metadata,
        "created_by": {"id": run.created_by_id, "email": run.created_by_email} if run.created_by_id else None,
        "caller": run.caller_kind.value,
    }
