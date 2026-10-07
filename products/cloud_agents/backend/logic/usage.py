"""Usage totals of a project, from the costs stored on its runs."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, Final

from django.db.models import Count, QuerySet, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone

from ..facade.contracts import InvalidInput, UsageBucketDTO, UsageSummaryDTO, UsageTotalsDTO
from ..facade.enums import UsageGroupBy
from ..models import CloudAgentRun

DEFAULT_RANGE: Final = timedelta(days=30)
MAX_RANGE: Final = timedelta(days=366)

_SUMS: Final = {
    "runs": Count("id"),
    "compute": Sum("compute_usd"),
    "inference": Sum("inference_usd"),
    "vcpu": Sum("vcpu_seconds"),
    "gib": Sum("gib_seconds"),
}


def _totals(row: dict[str, Any]) -> UsageTotalsDTO:
    compute_usd = row["compute"] or Decimal(0)
    inference_usd = row["inference"] or Decimal(0)
    return UsageTotalsDTO(
        runs=row["runs"],
        compute_usd=compute_usd,
        inference_usd=inference_usd,
        total_usd=compute_usd + inference_usd,
        vcpu_seconds=row["vcpu"] or Decimal(0),
        gib_seconds=row["gib"] or Decimal(0),
    )


def _buckets(rows: QuerySet[CloudAgentRun], group_by: UsageGroupBy) -> list[UsageBucketDTO]:
    if group_by == UsageGroupBy.DAY:
        by_day = rows.annotate(day=TruncDate("created_at", tzinfo=UTC)).values("day").annotate(**_SUMS)
        return [
            UsageBucketDTO(key=row["day"].isoformat(), label=None, usage=_totals(row)) for row in by_day.order_by("day")
        ]
    by_profile = rows.values("profile_id", "profile__name").annotate(**_SUMS).order_by("profile__name", "profile_id")
    return [
        UsageBucketDTO(
            key=str(row["profile_id"]) if row["profile_id"] else None, label=row["profile__name"], usage=_totals(row)
        )
        for row in by_profile
    ]


def get_usage_summary(
    team_id: int, *, date_from: datetime | None, date_to: datetime | None, group_by: UsageGroupBy
) -> UsageSummaryDTO:
    """Totals and buckets for the runs created from `date_from` up to, and not at, `date_to`."""
    date_to = date_to or timezone.now()
    date_from = date_from or date_to - DEFAULT_RANGE
    if date_from >= date_to:
        raise InvalidInput("The start of the range must be before its end.", attr="date_from")
    if date_to - date_from > MAX_RANGE:
        raise InvalidInput(f"The range must be {MAX_RANGE.days} days or less.", attr="date_from")
    rows = CloudAgentRun.objects.for_team(team_id).filter(created_at__gte=date_from, created_at__lt=date_to)
    return UsageSummaryDTO(
        date_from=date_from,
        date_to=date_to,
        group_by=group_by,
        totals=_totals(rows.aggregate(**_SUMS)),
        buckets=_buckets(rows, group_by),
    )
