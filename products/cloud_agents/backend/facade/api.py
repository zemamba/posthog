"""
Facade for cloud_agents.

The ONLY module other products and the presentation layer are allowed to import.
Accept and return the frozen dataclasses in contracts.py. Never return ORM
instances or import DRF.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator, Callable, Mapping, Sequence
from datetime import datetime
from typing import Any
from uuid import UUID

from ..logic import (
    catalog as catalog_logic,
    config_resolution,
    cost as cost_logic,
    limits as limits_logic,
    profiles as profiles_logic,
    runs as runs_logic,
    settings as settings_logic,
    streams as streams_logic,
    usage as usage_logic,
)
from ..logic.analytics import capture_event
from ..logic.webhooks import (
    delivery as delivery_logic,
    endpoints as endpoints_logic,
)
from .contracts import (
    CallerIdentity,
    CatalogDTO,
    EstimateDTO,
    MessageResult,
    ProfileCreateInput,
    ProfileDTO,
    ResolvedRunConfig,
    RunCreateInput,
    RunDTO,
    RunEventsDTO,
    RunEventStream,
    RunListFilters,
    RunUsageDTO,
    TeamSettingsDTO,
    UsageSummaryDTO,
    WebhookDeliveryDTO,
    WebhookEndpointCreateInput,
    WebhookEndpointDTO,
    WebhookSecretDTO,
)
from .enums import SizeName, UsageGroupBy, WebhookEvent

MIN_DURATION_MINUTES = config_resolution.MIN_DURATION_MINUTES
MAX_DURATION_MINUTES = config_resolution.MAX_DURATION_MINUTES
MAX_WEBHOOK_ENDPOINTS = endpoints_logic.MAX_ENDPOINTS_PER_TEAM
WEBHOOK_API_VERSION = delivery_logic.API_VERSION
FEATURE_FLAG_KEY = "cloud-agents"


# --- Run configuration ---


def resolve_run_config(call: RunCreateInput, profile: ProfileDTO | None, team: TeamSettingsDTO) -> ResolvedRunConfig:
    return config_resolution.resolve_run_config(call, profile, team)


def render_prompt(config: ResolvedRunConfig, prompt: str) -> str:
    return config_resolution.render_prompt(config, prompt)


# --- Runs ---


def start_run(
    team_id: int, caller: CallerIdentity, data: RunCreateInput, idempotency_key: str | None = None
) -> tuple[RunDTO, bool]:
    """Start a run. The flag is True when the idempotency key replayed a run that an earlier request started.

    Another product calls this with `CallerIdentity(kind=CallerKind.INTERNAL, billable=False, product=...)`
    to start a run that the project is not billed for.
    """
    return runs_logic.start_run(team_id, caller, data, idempotency_key)


def get_run(team_id: int, run_id: UUID) -> RunDTO:
    return runs_logic.get_run(team_id, run_id)


def list_runs(team_id: int, filters: RunListFilters | None = None) -> Sequence[RunDTO]:
    """The runs of the project, newest first. The result reads only the page that the caller takes a slice of."""
    return runs_logic.list_runs(team_id, filters or RunListFilters())


def send_message(team_id: int, caller: CallerIdentity, run_id: UUID, content: str) -> MessageResult:
    return runs_logic.send_message(team_id, caller, run_id, content)


def cancel_run(team_id: int, caller: CallerIdentity, run_id: UUID) -> tuple[RunDTO, bool]:
    """Ask the run to stop. The flag is False when the run already ended."""
    return runs_logic.cancel_run(team_id, caller, run_id)


def get_run_usage(team_id: int, run_id: UUID) -> RunUsageDTO:
    return cost_logic.get_run_usage(team_id, run_id)


def get_run_events(team_id: int, run_id: UUID) -> RunEventsDTO:
    return runs_logic.get_run_events(team_id, run_id)


def prepare_run_event_stream(
    team_id: int, run_id: UUID, *, last_event_id: str | None, start_latest: bool
) -> RunEventStream:
    """Resolve the run for streaming. It reads the database, so call it on the request thread."""
    return streams_logic.prepare_run_event_stream(
        team_id, run_id, last_event_id=last_event_id, start_latest=start_latest
    )


def run_event_stream(stream: RunEventStream) -> AsyncGenerator[bytes]:
    """The body of the stream response, as Server-Sent Events frames."""
    return streams_logic.run_event_stream(stream)


# --- Catalog and usage ---


def get_catalog(team_id: int) -> CatalogDTO:
    return catalog_logic.get_catalog(team_id)


def estimate_cost(size: SizeName, minutes: int) -> EstimateDTO:
    return catalog_logic.estimate_cost(size, minutes)


def get_usage_summary(
    team_id: int, *, date_from: datetime | None, date_to: datetime | None, group_by: UsageGroupBy
) -> UsageSummaryDTO:
    return usage_logic.get_usage_summary(team_id, date_from=date_from, date_to=date_to, group_by=group_by)


# --- Profiles ---


def list_profiles(team_id: int) -> list[ProfileDTO]:
    return profiles_logic.list_profiles(team_id)


def get_profile(team_id: int, profile_id: UUID) -> ProfileDTO:
    return profiles_logic.get_profile(team_id, profile_id)


def get_profile_by_ref(team_id: int, ref: str) -> ProfileDTO:
    return profiles_logic.get_profile_by_ref(team_id, ref)


def create_profile(team_id: int, data: ProfileCreateInput, caller: CallerIdentity) -> ProfileDTO:
    return profiles_logic.create_profile(team_id, data, caller)


def update_profile(team_id: int, profile_id: UUID, changes: Mapping[str, Any], caller: CallerIdentity) -> ProfileDTO:
    return profiles_logic.update_profile(team_id, profile_id, changes, caller)


def delete_profile(team_id: int, profile_id: UUID, caller: CallerIdentity) -> None:
    profiles_logic.delete_profile(team_id, profile_id, caller)


# --- Project settings ---


def get_team_settings(team_id: int) -> TeamSettingsDTO:
    return settings_logic.get_team_settings(team_id)


def update_team_settings(team_id: int, changes: Mapping[str, Any], caller: CallerIdentity) -> TeamSettingsDTO:
    return settings_logic.update_team_settings(team_id, changes, caller)


# --- Webhooks ---


def list_webhook_endpoints(team_id: int) -> list[WebhookEndpointDTO]:
    return endpoints_logic.list_endpoints(team_id)


def get_webhook_endpoint(team_id: int, endpoint_id: UUID) -> WebhookEndpointDTO:
    return endpoints_logic.get_endpoint(team_id, endpoint_id)


def create_webhook_endpoint(
    team_id: int, data: WebhookEndpointCreateInput, caller: CallerIdentity
) -> WebhookEndpointDTO:
    return endpoints_logic.create_endpoint(team_id, data, caller)


def update_webhook_endpoint(team_id: int, endpoint_id: UUID, changes: Mapping[str, Any]) -> WebhookEndpointDTO:
    return endpoints_logic.update_endpoint(team_id, endpoint_id, changes)


def delete_webhook_endpoint(team_id: int, endpoint_id: UUID, caller: CallerIdentity) -> None:
    endpoints_logic.delete_endpoint(team_id, endpoint_id, caller)


def validate_webhook_url(url: str) -> None:
    endpoints_logic.validate_webhook_url(url)


def get_or_create_webhook_secret(team_id: int) -> WebhookSecretDTO:
    """The secret is in the result only when this call created it. Rotate the secret to read a new one."""
    secret, created = endpoints_logic.get_or_create_secret(team_id)
    return WebhookSecretDTO(secret=secret if created else None, created=created)


def rotate_webhook_secret(team_id: int) -> WebhookSecretDTO:
    return WebhookSecretDTO(secret=endpoints_logic.rotate_secret(team_id), created=True)


def send_test_webhook_event(team_id: int, endpoint_id: UUID, caller: CallerIdentity) -> UUID:
    delivery_id = delivery_logic.send_test_event(team_id, endpoint_id)
    capture_event("cloud_agents_webhook_test_sent", caller, team_id, {"endpoint_id": str(endpoint_id)})
    return delivery_id


def enqueue_run_event(team_id: int, run_id: UUID, event_type: WebhookEvent, payload: dict[str, Any]) -> list[UUID]:
    return delivery_logic.enqueue_run_event(team_id, run_id, event_type, payload)


def list_recent_webhook_deliveries(team_id: int) -> list[WebhookDeliveryDTO]:
    return delivery_logic.list_recent_deliveries(team_id)


# --- Limits ---


def concurrency_guard(team_id: int, count_active: Callable[[], int]) -> None:
    limits_logic.concurrency_guard(team_id, count_active)


def consume_create_rate(team_id: int) -> None:
    limits_logic.consume_create_rate(team_id)


def refund_create_rate(team_id: int) -> None:
    limits_logic.refund_create_rate(team_id)
