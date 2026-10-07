"""
Contract types for cloud_agents.

Frozen dataclasses and typed errors that define what this product exposes.
No Django or DRF imports. The facade takes and returns these types.
"""

from __future__ import annotations

from dataclasses import field
from datetime import datetime
from decimal import Decimal
from typing import Any, ClassVar
from uuid import UUID

from posthog.dataclasses import frozen

from .enums import (
    BillingMode,
    CallerKind,
    InferenceBilling,
    InferenceMode,
    PrMode,
    RunStatus,
    SizeName,
    StopReason,
    WebhookDeliveryStatus,
    WebhookEvent,
    size_shape,
)


@frozen
class CallerIdentity:
    """Who started an operation. `user_id` is None for a caller that is not a person."""

    user_id: int | None
    distinct_id: str | None
    kind: CallerKind
    billable: bool
    product: str | None = None


@frozen
class SizeSpec:
    name: SizeName
    vcpu: int
    memory_gib: int

    @classmethod
    def from_name(cls, name: SizeName) -> SizeSpec:
        vcpu, memory_gib = size_shape(name)
        return cls(name=name, vcpu=vcpu, memory_gib=memory_gib)


@frozen
class RunCreateInput:
    """One request to start a run. `profile` is a profile id or a profile name."""

    prompt: str
    repository: str | None = None
    branch: str | None = None
    profile: str | None = None
    model: str | None = None
    size: SizeName | None = None
    inference: InferenceMode | None = None
    instructions: str | None = None
    create_pr: bool | None = None
    pr_mode: PrMode | None = None
    max_duration_minutes: int | None = None
    max_cost_usd: Decimal | None = None
    tags: list[str] | None = None
    metadata: dict[str, Any] | None = None
    webhook_url: str | None = None
    idempotency_key: str | None = None


@frozen
class ProfileDTO:
    id: UUID
    name: str
    description: str
    repository: str | None
    branch: str | None
    model: str | None
    size: SizeName | None
    inference: InferenceMode | None
    instructions: str | None
    create_pr: bool | None
    pr_mode: PrMode | None
    max_duration_minutes: int | None
    max_cost_usd: Decimal | None
    tags: list[str]
    webhook_url: str | None
    created_by_id: int | None
    created_at: datetime
    updated_at: datetime


@frozen
class ProfileCreateInput:
    name: str
    description: str = ""
    repository: str | None = None
    branch: str | None = None
    model: str | None = None
    size: SizeName | None = None
    inference: InferenceMode | None = None
    instructions: str | None = None
    create_pr: bool | None = None
    pr_mode: PrMode | None = None
    max_duration_minutes: int | None = None
    max_cost_usd: Decimal | None = None
    tags: list[str] = field(default_factory=list)
    webhook_url: str | None = None


@frozen
class TeamSettingsDTO:
    """Project defaults for runs. The limits are the effective values, after any override."""

    repository: str | None
    branch: str | None
    model: str | None
    size: SizeName | None
    inference: InferenceMode | None
    instructions: str | None
    create_pr: bool | None
    pr_mode: PrMode | None
    max_duration_minutes: int | None
    max_cost_usd: Decimal | None
    default_profile_id: UUID | None
    max_concurrent_runs: int
    create_rate_per_hour: int
    webhook_secret_set: bool
    updated_at: datetime | None


@frozen
class ResolvedRunConfig:
    """The configuration a run uses, after the call, the profile, the project and the product defaults are merged."""

    repository: str
    branch: str | None
    model: str | None
    size: SizeName
    inference: InferenceMode
    instructions: str | None
    create_pr: bool
    pr_mode: PrMode
    max_duration_minutes: int
    max_cost_usd: Decimal | None
    tags: list[str]
    webhook_url: str | None
    profile_id: UUID | None

    def to_json(self) -> dict[str, Any]:
        return {
            "repository": self.repository,
            "branch": self.branch,
            "model": self.model,
            "size": self.size.value,
            "inference": self.inference.value,
            "instructions": self.instructions,
            "create_pr": self.create_pr,
            "pr_mode": self.pr_mode.value,
            "max_duration_minutes": self.max_duration_minutes,
            "max_cost_usd": None if self.max_cost_usd is None else str(self.max_cost_usd),
            "tags": list(self.tags),
            "webhook_url": self.webhook_url,
            "profile_id": None if self.profile_id is None else str(self.profile_id),
        }

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> ResolvedRunConfig:
        max_cost_usd = data.get("max_cost_usd")
        profile_id = data.get("profile_id")
        return cls(
            repository=data["repository"],
            branch=data.get("branch"),
            model=data.get("model"),
            size=SizeName(data["size"]),
            inference=InferenceMode(data["inference"]),
            instructions=data.get("instructions"),
            create_pr=data["create_pr"],
            pr_mode=PrMode(data["pr_mode"]),
            max_duration_minutes=data["max_duration_minutes"],
            max_cost_usd=None if max_cost_usd is None else Decimal(str(max_cost_usd)),
            tags=list(data.get("tags") or []),
            webhook_url=data.get("webhook_url"),
            profile_id=None if profile_id is None else UUID(str(profile_id)),
        )


@frozen
class AgentSessionDTO:
    index: int
    task_run_id: UUID
    status: RunStatus
    started_at: datetime | None
    ended_at: datetime | None


@frozen
class RunResultDTO:
    pr_url: str | None
    pr_urls: list[str]
    summary: str | None


@frozen
class RunCostDTO:
    compute_usd: Decimal | None
    inference_usd: Decimal | None
    total_usd: Decimal | None
    vcpu_seconds: Decimal | None
    gib_seconds: Decimal | None
    billing_mode: BillingMode
    inference_billing: InferenceBilling | None
    final: bool


@frozen
class RunDTO:
    id: UUID
    status: RunStatus
    stop_reason: StopReason | None
    error: str | None
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    prompt: str
    repository: str
    branch: str | None
    profile_id: UUID | None
    profile_name: str | None
    config: ResolvedRunConfig
    result: RunResultDTO
    cost: RunCostDTO
    agent_sessions: list[AgentSessionDTO]
    tags: list[str]
    metadata: dict[str, Any]
    created_by_id: int | None
    created_by_email: str | None
    caller_kind: CallerKind


@frozen
class WebhookEndpointDTO:
    id: UUID
    url: str
    enabled: bool
    event_types: list[WebhookEvent]
    created_by_id: int | None
    created_at: datetime
    updated_at: datetime


@frozen
class WebhookEndpointCreateInput:
    url: str
    enabled: bool = True
    event_types: list[WebhookEvent] = field(default_factory=list)


@frozen
class WebhookDeliveryDTO:
    id: UUID
    endpoint_id: UUID | None
    url: str
    run_id: UUID
    event_type: WebhookEvent
    event_id: UUID
    status: WebhookDeliveryStatus
    attempts: int
    last_status_code: int | None
    last_error: str | None
    next_attempt_at: datetime | None
    delivered_at: datetime | None
    created_at: datetime


@frozen
class WebhookSecretDTO:
    """`secret` is set only in the response that creates or rotates it."""

    secret: str | None = field(repr=False)
    created: bool


class CloudAgentsError(Exception):
    """Base class for errors a caller can act on. `message` is safe to show to the caller."""

    code: ClassVar[str] = "cloud_agents_error"
    status_code: ClassVar[int] = 400
    default_message: ClassVar[str] = "The request could not be completed."

    def __init__(self, message: str | None = None) -> None:
        self.message = message or self.default_message
        super().__init__(self.message)


class InvalidInput(CloudAgentsError):
    code = "invalid_input"
    default_message = "The request is not valid."

    def __init__(self, message: str | None = None, *, attr: str | None = None) -> None:
        super().__init__(message)
        self.attr = attr


class RunNotFound(CloudAgentsError):
    code = "run_not_found"
    status_code = 404
    default_message = "This run does not exist in this project."


class ProfileNotFound(CloudAgentsError):
    code = "profile_not_found"
    status_code = 404
    default_message = "This profile does not exist in this project."


class WebhookEndpointNotFound(CloudAgentsError):
    code = "webhook_endpoint_not_found"
    status_code = 404
    default_message = "This webhook endpoint does not exist in this project."


class RepositoryRequired(CloudAgentsError):
    code = "repository_required"
    default_message = "Set a repository on the run, on its profile, or in the project settings."


class IdempotencyKeyReused(CloudAgentsError):
    code = "idempotency_key_reused"
    status_code = 409
    default_message = "This idempotency key was used with a different request. Use a new key."


class RunStopping(CloudAgentsError):
    code = "run_stopping"
    status_code = 409
    default_message = "This run is stopping. Wait until it stops, then try again."


class RunNotResumable(CloudAgentsError):
    code = "run_not_resumable"
    status_code = 409
    default_message = "This run cannot be resumed. Start a new run."


class UsageLimited(CloudAgentsError):
    code = "usage_limited"
    status_code = 429
    default_message = "This project reached its usage limit. Raise the limit in billing settings, then try again."


class ConcurrencyLimited(CloudAgentsError):
    code = "concurrency_limited"
    status_code = 429
    retry_after: ClassVar[int] = 30

    def __init__(self, *, limit: int, active: int) -> None:
        super().__init__(
            f"This project runs {active} agents and the limit is {limit}. Wait until a run stops, then try again."
        )
        self.limit = limit
        self.active = active


class CreateRateLimited(CloudAgentsError):
    code = "create_rate_limited"
    status_code = 429

    def __init__(self, *, retry_after: int) -> None:
        super().__init__(f"This project starts runs too quickly. Try again in {retry_after} seconds.")
        self.retry_after = retry_after


class InvalidWebhookUrl(CloudAgentsError):
    code = "invalid_webhook_url"
    default_message = "The webhook URL must be a public HTTPS address."


class TooManyWebhookEndpoints(CloudAgentsError):
    code = "too_many_webhook_endpoints"

    def __init__(self, *, limit: int) -> None:
        super().__init__(f"A project can have {limit} webhook endpoints. Delete one, then try again.")
        self.limit = limit
