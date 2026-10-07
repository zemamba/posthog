"""Profiles: named sets of run defaults."""

from __future__ import annotations

import dataclasses
from collections.abc import Mapping
from typing import Any, Final
from uuid import UUID

from django.db import IntegrityError, transaction
from django.db.models import QuerySet
from django.db.models.functions import Lower
from django.utils import timezone

from ..facade.contracts import CallerIdentity, InvalidInput, ProfileCreateInput, ProfileDTO, ProfileNotFound
from ..facade.enums import InferenceMode, PrMode, SizeName
from ..models import CloudAgentProfile, TeamCloudAgentsConfig
from .analytics import capture_event
from .config_resolution import validate_max_duration_minutes
from .webhooks.endpoints import validate_webhook_url

PROFILE_UPDATE_FIELDS: Final = frozenset(
    {
        "name",
        "description",
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
        "tags",
        "webhook_url",
    }
)
_ENUM_FIELDS: Final = frozenset({"size", "inference", "pr_mode"})


def to_profile_dto(profile: CloudAgentProfile) -> ProfileDTO:
    return ProfileDTO(
        id=profile.id,
        name=profile.name,
        description=profile.description,
        repository=profile.repository,
        branch=profile.branch,
        model=profile.model,
        size=SizeName(profile.size) if profile.size else None,
        inference=InferenceMode(profile.inference) if profile.inference else None,
        instructions=profile.instructions,
        create_pr=profile.create_pr,
        pr_mode=PrMode(profile.pr_mode) if profile.pr_mode else None,
        max_duration_minutes=profile.max_duration_minutes,
        max_cost_usd=profile.max_cost_usd,
        tags=list(profile.tags or []),
        webhook_url=profile.webhook_url,
        created_by_id=profile.created_by_id,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


def _active(team_id: int) -> QuerySet[CloudAgentProfile]:
    return CloudAgentProfile.objects.for_team(team_id).filter(deleted=False)


def _get_profile(team_id: int, profile_id: UUID) -> CloudAgentProfile:
    profile = _active(team_id).filter(id=profile_id).first()
    if profile is None:
        raise ProfileNotFound()
    return profile


def _name_taken_error() -> InvalidInput:
    return InvalidInput("A profile with this name already exists. Use a different name.", attr="name")


def _validate_values(values: Mapping[str, Any], *, team_id: int, exclude_id: UUID | None = None) -> None:
    name = values.get("name")
    if "name" in values:
        if not name or not name.strip():
            raise InvalidInput("Give the profile a name.", attr="name")
        duplicates = _active(team_id).filter(name__iexact=name.strip())
        if exclude_id is not None:
            duplicates = duplicates.exclude(id=exclude_id)
        if duplicates.exists():
            raise _name_taken_error()
    if values.get("max_duration_minutes") is not None:
        validate_max_duration_minutes(values["max_duration_minutes"])
    if values.get("webhook_url"):
        validate_webhook_url(values["webhook_url"])


def _column_values(values: Mapping[str, Any]) -> dict[str, Any]:
    columns: dict[str, Any] = {}
    for field, value in values.items():
        if field == "name":
            columns[field] = value.strip()
        elif field in _ENUM_FIELDS and value is not None:
            columns[field] = value.value if hasattr(value, "value") else value
        elif field == "tags":
            columns[field] = list(value or [])
        else:
            columns[field] = value
    return columns


def list_profiles(team_id: int) -> list[ProfileDTO]:
    return [to_profile_dto(profile) for profile in _active(team_id).order_by(Lower("name"), "id")]


def get_profile(team_id: int, profile_id: UUID) -> ProfileDTO:
    return to_profile_dto(_get_profile(team_id, profile_id))


def get_profile_by_ref(team_id: int, ref: str) -> ProfileDTO:
    """Find a profile by its id or, when `ref` is not an id, by its name without regard to case."""
    try:
        profile_id: UUID | None = UUID(ref)
    except ValueError:
        profile_id = None
    if profile_id is not None:
        return to_profile_dto(_get_profile(team_id, profile_id))
    profile = _active(team_id).filter(name__iexact=ref.strip()).first()
    if profile is None:
        raise ProfileNotFound()
    return to_profile_dto(profile)


def create_profile(team_id: int, data: ProfileCreateInput, caller: CallerIdentity) -> ProfileDTO:
    values = dataclasses.asdict(data)
    _validate_values(values, team_id=team_id)
    try:
        # The unique constraint decides when two requests create the same name at the same time.
        with transaction.atomic():
            profile = CloudAgentProfile.objects.for_team(team_id).create(
                team_id=team_id, created_by_id=caller.user_id, **_column_values(values)
            )
    except IntegrityError:
        raise _name_taken_error() from None
    capture_event("cloud_agents_profile_created", caller, team_id, {"profile_id": str(profile.id)})
    return to_profile_dto(profile)


def update_profile(team_id: int, profile_id: UUID, changes: Mapping[str, Any], caller: CallerIdentity) -> ProfileDTO:
    """Apply `changes`, a mapping of field name to new value. A None value clears a default."""
    unknown = set(changes) - PROFILE_UPDATE_FIELDS
    if unknown:
        raise InvalidInput(f"These fields cannot be changed: {', '.join(sorted(unknown))}.")
    profile = _get_profile(team_id, profile_id)
    _validate_values(changes, team_id=team_id, exclude_id=profile.id)
    columns = _column_values(changes)
    for field, value in columns.items():
        setattr(profile, field, value)
    if columns:
        try:
            with transaction.atomic():
                profile.save(update_fields=[*columns, "updated_at"])
        except IntegrityError:
            raise _name_taken_error() from None
    capture_event(
        "cloud_agents_profile_updated",
        caller,
        team_id,
        {"profile_id": str(profile.id), "changed_fields": sorted(columns)},
    )
    return to_profile_dto(profile)


def delete_profile(team_id: int, profile_id: UUID, caller: CallerIdentity) -> None:
    """Soft delete. The row stays so that runs keep their profile, and the name becomes free."""
    profile = _get_profile(team_id, profile_id)
    profile.deleted = True
    profile.deleted_at = timezone.now()
    with transaction.atomic():
        profile.save(update_fields=["deleted", "deleted_at", "updated_at"])
        # SET_NULL applies to a hard delete only, so clear the project default here.
        TeamCloudAgentsConfig.objects.for_team(team_id).filter(default_profile_id=profile.id).update(
            default_profile=None
        )
    capture_event("cloud_agents_profile_deleted", caller, team_id, {"profile_id": str(profile.id)})
