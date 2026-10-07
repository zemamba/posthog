"""Project settings: the run defaults that apply when a call and its profile set no value."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Final

from ..facade.contracts import CallerIdentity, InvalidInput, TeamSettingsDTO
from ..facade.enums import InferenceMode, PrMode, SizeName
from ..models import CloudAgentProfile, TeamCloudAgentsConfig
from .analytics import capture_event
from .config_resolution import validate_max_duration_minutes
from .limits import DEFAULT_CREATE_RATE_PER_HOUR, DEFAULT_MAX_CONCURRENT_RUNS
from .team_config import get_team_config

# The limits and the webhook secret are not here: staff set the limits, and the secret has its own calls.
SETTINGS_UPDATE_FIELDS: Final = frozenset(
    {
        "repository",
        "branch",
        "model",
        "size",
        "inference",
        "instructions",
        "create_pr",
        "pr_mode",
        "max_duration_minutes",
        "max_cost_usd",
        "default_profile_id",
    }
)
_ENUM_FIELDS: Final = frozenset({"size", "inference", "pr_mode"})


def to_settings_dto(config: TeamCloudAgentsConfig) -> TeamSettingsDTO:
    return TeamSettingsDTO(
        repository=config.repository,
        branch=config.branch,
        model=config.model,
        size=SizeName(config.size) if config.size else None,
        inference=InferenceMode(config.inference) if config.inference else None,
        instructions=config.instructions,
        create_pr=config.create_pr,
        pr_mode=PrMode(config.pr_mode) if config.pr_mode else None,
        max_duration_minutes=config.max_duration_minutes,
        max_cost_usd=config.max_cost_usd,
        default_profile_id=config.default_profile_id,
        max_concurrent_runs=(
            config.max_concurrent_runs if config.max_concurrent_runs is not None else DEFAULT_MAX_CONCURRENT_RUNS
        ),
        create_rate_per_hour=config.create_rate_per_hour or DEFAULT_CREATE_RATE_PER_HOUR,
        webhook_secret_set=bool(config.webhook_secret),
        updated_at=config.updated_at,
    )


def get_team_settings(team_id: int) -> TeamSettingsDTO:
    """Return the settings of the project. The first read creates the row with no defaults set."""
    return to_settings_dto(get_team_config(team_id))


def update_team_settings(team_id: int, changes: Mapping[str, Any], caller: CallerIdentity) -> TeamSettingsDTO:
    """Apply `changes`, a mapping of field name to new value. A None value clears a default."""
    unknown = set(changes) - SETTINGS_UPDATE_FIELDS
    if unknown:
        raise InvalidInput(f"These fields cannot be changed: {', '.join(sorted(unknown))}.")
    if changes.get("max_duration_minutes") is not None:
        validate_max_duration_minutes(changes["max_duration_minutes"])
    default_profile_id = changes.get("default_profile_id")
    if default_profile_id is not None:
        profile_exists = (
            CloudAgentProfile.objects.for_team(team_id).filter(id=default_profile_id, deleted=False).exists()
        )
        if not profile_exists:
            raise InvalidInput("This profile does not exist in this project.", attr="default_profile")

    config = get_team_config(team_id)
    for field, value in changes.items():
        if field in _ENUM_FIELDS and value is not None:
            value = value.value if hasattr(value, "value") else value
        setattr(config, field, value)
    if changes:
        config.save(update_fields=[*changes, "updated_at"])
        # Field names only. The values can hold instructions or a repository name.
        capture_event("cloud_agents_settings_updated", caller, team_id, {"changed_fields": sorted(changes)})
    return to_settings_dto(config)
