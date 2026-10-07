"""Webhook endpoints and the per-project signing secret."""

from __future__ import annotations

import urllib.parse as urlparse
from collections.abc import Mapping
from typing import Any, Final
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from posthog.security.url_validation import validate_external_url

from ...facade.contracts import (
    CallerIdentity,
    InvalidWebhookUrl,
    TooManyWebhookEndpoints,
    WebhookEndpointCreateInput,
    WebhookEndpointDTO,
    WebhookEndpointNotFound,
)
from ...facade.enums import WebhookEvent
from ...models import CloudAgentsWebhookEndpoint, TeamCloudAgentsConfig
from ..analytics import capture_event
from ..team_config import lock_team_config
from .signing import generate_secret

MAX_ENDPOINTS_PER_TEAM: Final = 5
ENDPOINT_UPDATE_FIELDS: Final = frozenset({"url", "enabled", "event_types"})


def validate_webhook_url(url: str) -> None:
    """Raise `InvalidWebhookUrl` unless `url` is an HTTPS address that PostHog can send to."""
    try:
        scheme = urlparse.urlparse(url).scheme
    except ValueError:
        raise InvalidWebhookUrl() from None
    if scheme != "https":
        raise InvalidWebhookUrl("The webhook URL must start with https://.")
    try:
        validate_external_url(url)
    except ValueError:
        # The reason can name an internal address, so the caller gets the generic message.
        raise InvalidWebhookUrl() from None


def to_endpoint_dto(endpoint: CloudAgentsWebhookEndpoint) -> WebhookEndpointDTO:
    return WebhookEndpointDTO(
        id=endpoint.id,
        url=endpoint.url,
        enabled=endpoint.enabled,
        event_types=[WebhookEvent(event_type) for event_type in endpoint.event_types],
        created_by_id=endpoint.created_by_id,
        created_at=endpoint.created_at,
        updated_at=endpoint.updated_at,
    )


def _get_endpoint(team_id: int, endpoint_id: UUID) -> CloudAgentsWebhookEndpoint:
    endpoint = CloudAgentsWebhookEndpoint.objects.for_team(team_id).filter(id=endpoint_id).first()
    if endpoint is None:
        raise WebhookEndpointNotFound()
    return endpoint


def list_endpoints(team_id: int) -> list[WebhookEndpointDTO]:
    endpoints = CloudAgentsWebhookEndpoint.objects.for_team(team_id).order_by("created_at", "id")
    return [to_endpoint_dto(endpoint) for endpoint in endpoints]


def get_endpoint(team_id: int, endpoint_id: UUID) -> WebhookEndpointDTO:
    return to_endpoint_dto(_get_endpoint(team_id, endpoint_id))


def create_endpoint(team_id: int, data: WebhookEndpointCreateInput, caller: CallerIdentity) -> WebhookEndpointDTO:
    validate_webhook_url(data.url)
    with transaction.atomic():
        # The lock makes the count check exact when two requests create an endpoint at the same time.
        lock_team_config(team_id)
        if CloudAgentsWebhookEndpoint.objects.for_team(team_id).count() >= MAX_ENDPOINTS_PER_TEAM:
            raise TooManyWebhookEndpoints(limit=MAX_ENDPOINTS_PER_TEAM)
        endpoint = CloudAgentsWebhookEndpoint.objects.for_team(team_id).create(
            team_id=team_id,
            url=data.url,
            enabled=data.enabled,
            event_types=[event_type.value for event_type in data.event_types],
            created_by_id=caller.user_id,
        )
    capture_event(
        "cloud_agents_webhook_endpoint_created",
        caller,
        team_id,
        {"endpoint_id": str(endpoint.id), "event_types": endpoint.event_types},
    )
    return to_endpoint_dto(endpoint)


def update_endpoint(team_id: int, endpoint_id: UUID, changes: Mapping[str, Any]) -> WebhookEndpointDTO:
    """Apply `changes`, a mapping of field name to new value. Only the fields in `ENDPOINT_UPDATE_FIELDS` change."""
    endpoint = _get_endpoint(team_id, endpoint_id)
    update_fields: list[str] = []
    if "url" in changes:
        validate_webhook_url(changes["url"])
        endpoint.url = changes["url"]
        update_fields.append("url")
    if "enabled" in changes:
        endpoint.enabled = changes["enabled"]
        update_fields.append("enabled")
    if "event_types" in changes:
        endpoint.event_types = [WebhookEvent(event_type).value for event_type in changes["event_types"]]
        update_fields.append("event_types")
    if update_fields:
        endpoint.save(update_fields=[*update_fields, "updated_at"])
    return to_endpoint_dto(endpoint)


def delete_endpoint(team_id: int, endpoint_id: UUID, caller: CallerIdentity) -> None:
    endpoint = _get_endpoint(team_id, endpoint_id)
    endpoint.delete()
    capture_event("cloud_agents_webhook_endpoint_deleted", caller, team_id, {"endpoint_id": str(endpoint_id)})


def get_or_create_secret(team_id: int) -> tuple[str, bool]:
    """Return `(secret, created)`. `created` is True when this call made the secret."""
    with transaction.atomic():
        config = lock_team_config(team_id)
        if config.webhook_secret:
            return config.webhook_secret, False
        return _write_new_secret(config), True


def rotate_secret(team_id: int) -> str:
    """Replace the secret. Deliveries sent after this call use the new secret."""
    with transaction.atomic():
        config = lock_team_config(team_id)
        return _write_new_secret(config)


def _write_new_secret(config: TeamCloudAgentsConfig) -> str:
    secret = generate_secret()
    config.webhook_secret = secret
    config.webhook_secret_created_at = timezone.now()
    config.save(update_fields=["webhook_secret", "webhook_secret_created_at", "updated_at"])
    return secret
