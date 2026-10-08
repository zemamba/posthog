from collections import Counter
from collections.abc import Collection, Iterable, Sequence
from datetime import datetime, time, timedelta
from functools import partial
from typing import TYPE_CHECKING
from uuid import UUID

from django.db import transaction
from django.db.models import F

from posthog.dataclasses import frozen

from ..facade.contracts import SuggestionAlreadyDecidedError, SuggestionDraft
from ..facade.enums import (
    WarehouseSuggestionDismissalReason,
    WarehouseSuggestionKind,
    WarehouseSuggestionStatus,
    WarehouseSuggestionSubjectKind,
)
from ..models import WarehouseSuggestion
from .analytics import SuggestionOutcome, report_outcomes
from .candidates.base import CandidateContext
from .candidates.registry import CANDIDATES
from .reads import Subject
from .rules import LifecycleRules
from .suggestions import transition_to, upsert_suggestions

if TYPE_CHECKING:
    from posthog.models.team import Team


@frozen
class LifecycleResult:
    created: int
    reproposed: int
    revived: int
    auto_resolved: int
    expired: int
    surfaced: int
    assets_reconciled: int


OutcomeBatches = Sequence[tuple[SuggestionOutcome, Sequence[WarehouseSuggestion]]]


@frozen
class Reopened:
    reproposed: tuple[WarehouseSuggestion, ...]
    revived: tuple[WarehouseSuggestion, ...]


def apply_run(
    context: CandidateContext, team: "Team", drafts: Sequence[SuggestionDraft], now: datetime, *, surface: bool
) -> LifecycleResult:
    fingerprints = {draft.fingerprint for draft in drafts}
    reopened = _reopen(context, drafts)
    created = _upsert(context.team_id, drafts)
    auto_resolved = _auto_resolve(context, fingerprints)
    expired = _expire(context, fingerprints, now)
    surfaced = _surface(context.team_id, context.rules.lifecycle, now) if surface else []
    assets_reconciled = _reconcile_assets(context)
    outcomes: OutcomeBatches = (
        (SuggestionOutcome.CREATED, created),
        (SuggestionOutcome.REPROPOSED, reopened.reproposed),
        (SuggestionOutcome.REVIVED, reopened.revived),
        (SuggestionOutcome.AUTO_RESOLVED, auto_resolved),
        (SuggestionOutcome.EXPIRED, expired),
        (SuggestionOutcome.SURFACED, surfaced),
    )
    transaction.on_commit(partial(_report_all, outcomes, team))
    return LifecycleResult(
        created=len(created),
        reproposed=len(reopened.reproposed),
        revived=len(reopened.revived),
        auto_resolved=len(auto_resolved),
        expired=len(expired),
        surfaced=len(surfaced),
        assets_reconciled=assets_reconciled,
    )


def _report_all(outcomes: "OutcomeBatches", team: "Team") -> None:
    for outcome, rows in outcomes:
        report_outcomes(outcome, rows, team=team)


def _upsert(team_id: int, drafts: Sequence[SuggestionDraft]) -> list[WarehouseSuggestion]:
    suggestions = WarehouseSuggestion.objects.for_team(team_id)
    fingerprints = {draft.fingerprint for draft in drafts}
    existing = set(suggestions.filter(fingerprint__in=fingerprints).values_list("fingerprint", flat=True))
    upsert_suggestions(team_id, drafts)
    return list(suggestions.filter(fingerprint__in=fingerprints - existing))


REVIVABLE_STATUSES = (WarehouseSuggestionStatus.EXPIRED, WarehouseSuggestionStatus.AUTO_RESOLVED)


def _reopen(context: CandidateContext, drafts: Sequence[SuggestionDraft]) -> Reopened:
    drafts_by_fingerprint = {draft.fingerprint: draft for draft in drafts}
    suggestions = WarehouseSuggestion.objects.for_team(context.team_id)
    closed = suggestions.filter(
        fingerprint__in=drafts_by_fingerprint,
        status__in=[WarehouseSuggestionStatus.DISMISSED, *REVIVABLE_STATUSES],
    )
    reproposed: list[WarehouseSuggestion] = []
    revived: list[WarehouseSuggestion] = []
    for row in closed:
        if row.status in REVIVABLE_STATUSES:
            revived.extend(_moved(row, context.team_id, WarehouseSuggestionStatus.PROPOSED))
        elif _earns_reproposal(row, drafts_by_fingerprint[row.fingerprint], context.rules.lifecycle):
            reproposed.extend(_moved(row, context.team_id, WarehouseSuggestionStatus.PROPOSED))
    reproposed_ids = [row.id for row in reproposed]
    revived_ids = [row.id for row in revived]
    suggestions.filter(id__in=reproposed_ids).update(reproposed_count=F("reproposed_count") + 1)
    suggestions.filter(id__in=[*reproposed_ids, *revived_ids]).update(surfaced_at=None)
    return Reopened(
        reproposed=tuple(suggestions.filter(id__in=reproposed_ids)),
        revived=tuple(suggestions.filter(id__in=revived_ids)),
    )


def _earns_reproposal(row: WarehouseSuggestion, draft: SuggestionDraft, rules: LifecycleRules) -> bool:
    return (
        row.dismissal_reason == WarehouseSuggestionDismissalReason.NOT_NOW
        and row.dismissed_at_score is not None
        and draft.score > row.dismissed_at_score
        and draft.score >= rules.reproposal_score_multiple * row.dismissed_at_score
    )


def _auto_resolve(context: CandidateContext, refreshed_fingerprints: Collection[str]) -> list[WarehouseSuggestion]:
    open_rows = (
        WarehouseSuggestion.objects.for_team(context.team_id)
        .filter(status=WarehouseSuggestionStatus.PROPOSED)
        .exclude(fingerprint__in=refreshed_fingerprints)
    )
    resolved = (
        row for row in open_rows if CANDIDATES[WarehouseSuggestionKind(row.kind)].is_resolved(context, _subject(row))
    )
    return _move_all(resolved, context.team_id, WarehouseSuggestionStatus.AUTO_RESOLVED)


def _expire(
    context: CandidateContext, refreshed_fingerprints: Collection[str], now: datetime
) -> list[WarehouseSuggestion]:
    rules = context.rules.lifecycle
    if context.reads.recent_days_with_data < rules.expire_after_days:
        return []
    stale = (
        WarehouseSuggestion.objects.for_team(context.team_id)
        .filter(
            status=WarehouseSuggestionStatus.PROPOSED, last_seen_at__lt=now - timedelta(days=rules.expire_after_days)
        )
        .exclude(fingerprint__in=refreshed_fingerprints)
    )
    return _move_all(stale, context.team_id, WarehouseSuggestionStatus.EXPIRED)


def _surface(team_id: int, rules: LifecycleRules, now: datetime) -> list[WarehouseSuggestion]:
    suggestions = WarehouseSuggestion.objects.for_team(team_id)
    start_of_day = datetime.combine(now.date(), time.min, tzinfo=now.tzinfo)
    open_kinds = Counter(
        suggestions.filter(status=WarehouseSuggestionStatus.PROPOSED, surfaced_at__isnull=False).values_list(
            "kind", flat=True
        )
    )
    slots = min(
        rules.max_surfaced_per_day - suggestions.filter(surfaced_at__gte=start_of_day).count(),
        rules.max_open - open_kinds.total(),
    )
    if slots <= 0:
        return []
    first_week = not suggestions.filter(
        surfaced_at__lt=start_of_day - timedelta(days=rules.first_week_runs - 1)
    ).exists()
    waiting = sorted(
        suggestions.filter(status=WarehouseSuggestionStatus.PROPOSED, surfaced_at__isnull=True).only(
            "id", "kind", "score"
        ),
        key=lambda row: (first_week and row.kind not in rules.first_week_kinds, -row.score, str(row.id)),
    )
    chosen: list[UUID] = []
    for row in waiting:
        if len(chosen) == slots:
            break
        if open_kinds[row.kind] >= rules.max_open_per_kind:
            continue
        open_kinds[row.kind] += 1
        chosen.append(row.id)
    suggestions.filter(id__in=chosen).update(surfaced_at=now)
    return list(suggestions.filter(id__in=chosen))


def _reconcile_assets(context: CandidateContext) -> int:
    suggestions = WarehouseSuggestion.objects.for_team(context.team_id)
    changed = 0
    for row in suggestions.filter(status=WarehouseSuggestionStatus.ACCEPTED).only(
        "id", "kind", "subject_kind", "subject_id", "asset_outcome"
    ):
        outcome = CANDIDATES[WarehouseSuggestionKind(row.kind)].asset_outcome(context, _subject(row))
        if outcome != row.asset_outcome:
            changed += suggestions.filter(id=row.id).update(asset_outcome=outcome)
    return changed


def _move_all(
    rows: Iterable[WarehouseSuggestion], team_id: int, status: WarehouseSuggestionStatus
) -> list[WarehouseSuggestion]:
    return [moved for row in rows for moved in _moved(row, team_id, status)]


def _moved(row: WarehouseSuggestion, team_id: int, status: WarehouseSuggestionStatus) -> list[WarehouseSuggestion]:
    try:
        return [transition_to(row.id, team_id, status, user_id=None)]
    except SuggestionAlreadyDecidedError:
        return []


def _subject(row: WarehouseSuggestion) -> Subject:
    return Subject(kind=WarehouseSuggestionSubjectKind(row.subject_kind), id=row.subject_id)
