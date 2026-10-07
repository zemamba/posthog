"""Merge the settings of one call, its profile and the project into the configuration a run uses."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Final

from posthog.dataclasses import frozen

from ..facade.contracts import (
    InvalidInput,
    ProfileDTO,
    RepositoryRequired,
    ResolvedRunConfig,
    RunCreateInput,
    TeamSettingsDTO,
)
from ..facade.enums import InferenceMode, PrMode, SizeName

MIN_DURATION_MINUTES: Final = 5
MAX_DURATION_MINUTES: Final = 240


@frozen
class ProductDefaults:
    size: SizeName = SizeName.S_4X16
    inference: InferenceMode = InferenceMode.AUTO
    create_pr: bool = True
    pr_mode: PrMode = PrMode.DRAFT
    max_duration_minutes: int = 60
    # The run step selects a model when no level sets one.
    model: str | None = None
    max_cost_usd: Decimal | None = None


PRODUCT_DEFAULTS: Final = ProductDefaults()


def _first_set(field: str, *sources: object | None) -> Any:
    for source in sources:
        value = getattr(source, field, None) if source is not None else None
        if value is not None:
            return value
    return None


def _merge_tags(*tag_lists: list[str] | None) -> list[str]:
    merged: dict[str, None] = {}
    for tags in tag_lists:
        for tag in tags or []:
            merged.setdefault(tag)
    return list(merged)


def _join_instructions(*blocks: str | None) -> str | None:
    kept = [block.strip() for block in blocks if block and block.strip()]
    return "\n\n".join(kept) if kept else None


def validate_max_duration_minutes(value: int) -> None:
    if not MIN_DURATION_MINUTES <= value <= MAX_DURATION_MINUTES:
        raise InvalidInput(
            f"The maximum duration must be from {MIN_DURATION_MINUTES} to {MAX_DURATION_MINUTES} minutes.",
            attr="max_duration_minutes",
        )


def resolve_run_config(call: RunCreateInput, profile: ProfileDTO | None, team: TeamSettingsDTO) -> ResolvedRunConfig:
    """Take each field from the first level that sets it: call, profile, project, product default."""
    repository = _first_set("repository", call, profile, team)
    if not repository:
        raise RepositoryRequired()

    max_duration_minutes = _first_set("max_duration_minutes", call, profile, team, PRODUCT_DEFAULTS)
    validate_max_duration_minutes(max_duration_minutes)

    return ResolvedRunConfig(
        repository=repository,
        branch=_first_set("branch", call, profile, team),
        model=_first_set("model", call, profile, team, PRODUCT_DEFAULTS),
        size=SizeName(_first_set("size", call, profile, team, PRODUCT_DEFAULTS)),
        inference=InferenceMode(_first_set("inference", call, profile, team, PRODUCT_DEFAULTS)),
        # Broad guidance comes first, so the more specific level has the last word.
        instructions=_join_instructions(
            team.instructions, profile.instructions if profile else None, call.instructions
        ),
        create_pr=_first_set("create_pr", call, profile, team, PRODUCT_DEFAULTS),
        pr_mode=PrMode(_first_set("pr_mode", call, profile, team, PRODUCT_DEFAULTS)),
        max_duration_minutes=max_duration_minutes,
        max_cost_usd=_first_set("max_cost_usd", call, profile, team, PRODUCT_DEFAULTS),
        tags=_merge_tags(profile.tags if profile else None, call.tags),
        profile_id=profile.id if profile else None,
    )


def render_prompt(config: ResolvedRunConfig, prompt: str) -> str:
    """Put the instructions block above the prompt. Without instructions, return the prompt unchanged."""
    if not config.instructions:
        return prompt
    return f"<instructions>\n{config.instructions}\n</instructions>\n\n{prompt}"
