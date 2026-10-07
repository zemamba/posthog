"""DRF serializers for cloud_agents."""

from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import Any

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from ..facade.api import MAX_DURATION_MINUTES, MIN_DURATION_MINUTES
from ..facade.contracts import RunDTO
from ..facade.enums import (
    BillingMode,
    CallerKind,
    CloudAgentRunStatus,
    InferenceBilling,
    InferenceMode,
    PrMode,
    SizeName,
    StopReason,
    UsageGroupBy,
    WebhookDeliveryStatus,
    WebhookEvent,
)

REPOSITORY_REGEX = r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$"
MAX_TAGS = 20
URL_MAX_LENGTH = 2000
PROMPT_MAX_LENGTH = 64000
MAX_METADATA_PAIRS = 16
METADATA_KEY_MAX_LENGTH = 64
METADATA_VALUE_MAX_LENGTH = 512
IDEMPOTENCY_KEY_MAX_LENGTH = 100
MAX_ESTIMATE_MINUTES = 24 * 60


class LabeledEnumField(serializers.ChoiceField):
    """A choice field that gives the view an enum member and writes the value of the member."""

    def __init__(self, enum_class: Any, **kwargs: Any) -> None:
        self.enum_class = enum_class
        super().__init__(choices=enum_class.choices, **kwargs)

    def to_internal_value(self, data: Any) -> Any:
        return self.enum_class(super().to_internal_value(data))

    def to_representation(self, value: Any) -> Any:
        return super().to_representation(value.value if isinstance(value, Enum) else value)


def _tags_field(**kwargs: Any) -> serializers.ListField:
    return serializers.ListField(
        child=serializers.CharField(max_length=50),
        max_length=MAX_TAGS,
        **kwargs,
    )


class RunDefaultsSerializer(serializers.Serializer):
    """The run defaults that a profile and the project settings share. A null value sets no default."""

    repository = serializers.RegexField(
        REPOSITORY_REGEX,
        max_length=255,
        required=False,
        allow_null=True,
        help_text="Default GitHub repository, in the format `owner/name`. Null sets no default.",
    )
    branch = serializers.CharField(
        max_length=255,
        required=False,
        allow_null=True,
        help_text="Default base branch. Null uses the default branch of the repository.",
    )
    model = serializers.CharField(
        max_length=100,
        required=False,
        allow_null=True,
        help_text="Default model for the agent. Null lets PostHog select the model.",
    )
    size = LabeledEnumField(
        SizeName,
        required=False,
        allow_null=True,
        help_text="Default sandbox size, as `<vCPU>x<memory in GiB>`. Null uses the product default.",
    )
    inference = LabeledEnumField(
        InferenceMode,
        required=False,
        allow_null=True,
        help_text=(
            "How the agent pays for model usage. `auto` uses your own subscription when one is connected "
            "for the runtime, and PostHog inference otherwise. Null uses the product default."
        ),
    )
    instructions = serializers.CharField(
        max_length=20000,
        required=False,
        allow_null=True,
        allow_blank=True,
        help_text=(
            "Instructions that the agent gets before the prompt. Project instructions come first, "
            "then profile instructions, then the instructions of the run."
        ),
    )
    create_pr = serializers.BooleanField(
        required=False,
        allow_null=True,
        help_text="Whether the agent opens a pull request when it finishes. Null uses the product default.",
    )
    pr_mode = LabeledEnumField(
        PrMode,
        required=False,
        allow_null=True,
        help_text=(
            "Whether the pull request opens as a draft or ready for review. Reserved. Not enforced yet. "
            "Null uses the product default."
        ),
    )
    max_duration_minutes = serializers.IntegerField(
        min_value=MIN_DURATION_MINUTES,
        max_value=MAX_DURATION_MINUTES,
        required=False,
        allow_null=True,
        help_text=(
            f"The run time limit in minutes, from {MIN_DURATION_MINUTES} to {MAX_DURATION_MINUTES}. Reserved. Not enforced yet. "
            "Null uses the product default."
        ),
    )
    max_cost_usd = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0.01"),
        required=False,
        allow_null=True,
        help_text="Cost limit of a run in US dollars. Reserved. Not enforced yet. Null sets no cost limit.",
    )


class ProfileWriteFieldsSerializer(RunDefaultsSerializer):
    description = serializers.CharField(
        max_length=2000, required=False, allow_blank=True, help_text="What this profile is for."
    )
    tags = _tags_field(required=False, help_text="Tags added to every run that uses this profile.")
    webhook_url = serializers.URLField(
        max_length=URL_MAX_LENGTH,
        required=False,
        allow_null=True,
        help_text="HTTPS URL that gets the events of every run that uses this profile. Null sends none.",
    )


class ProfileCreateSerializer(ProfileWriteFieldsSerializer):
    name = serializers.CharField(
        max_length=100,
        help_text="Name of the profile. It is unique in the project, without regard to case.",
    )


class ProfileUpdateSerializer(ProfileWriteFieldsSerializer):
    name = serializers.CharField(
        max_length=100,
        required=False,
        help_text="Name of the profile. It is unique in the project, without regard to case.",
    )


class ProfileSerializer(RunDefaultsSerializer):
    id = serializers.UUIDField(help_text="ID of the profile.")
    name = serializers.CharField(help_text="Name of the profile.")
    description = serializers.CharField(allow_blank=True, help_text="What this profile is for.")
    tags = _tags_field(help_text="Tags added to every run that uses this profile.")
    webhook_url = serializers.URLField(
        allow_null=True, help_text="HTTPS URL that gets the events of every run that uses this profile."
    )
    created_by = serializers.IntegerField(
        source="created_by_id", allow_null=True, help_text="ID of the user who created the profile."
    )
    created_at = serializers.DateTimeField(help_text="When the profile was created.")
    updated_at = serializers.DateTimeField(help_text="When the profile was last changed.")


class CloudAgentSettingsUpdateSerializer(RunDefaultsSerializer):
    default_profile = serializers.UUIDField(
        required=False,
        allow_null=True,
        help_text="ID of the profile that a run uses when it names no profile. Null sets no default profile.",
    )


class CloudAgentSettingsSerializer(RunDefaultsSerializer):
    default_profile = serializers.UUIDField(
        source="default_profile_id",
        allow_null=True,
        help_text="ID of the profile that a run uses when it names no profile.",
    )
    max_concurrent_runs = serializers.IntegerField(
        help_text="How many runs the project can have active at the same time."
    )
    create_rate_per_hour = serializers.IntegerField(help_text="How many runs the project can start in one hour.")
    webhook_secret_set = serializers.BooleanField(help_text="Whether the project has a webhook signing secret.")
    updated_at = serializers.DateTimeField(allow_null=True, help_text="When the settings were last changed.")


def _event_types_field(**kwargs: Any) -> serializers.ListField:
    return serializers.ListField(child=LabeledEnumField(WebhookEvent), max_length=len(WebhookEvent), **kwargs)


class WebhookEndpointCreateSerializer(serializers.Serializer):
    url = serializers.URLField(
        max_length=URL_MAX_LENGTH, help_text="HTTPS URL that gets a POST request for each event."
    )
    enabled = serializers.BooleanField(
        required=False, default=True, help_text="Whether PostHog sends events to this endpoint."
    )
    event_types = _event_types_field(
        required=False,
        default=list,
        help_text="The event types to send. An empty list sends all event types.",
    )


class WebhookEndpointUpdateSerializer(serializers.Serializer):
    url = serializers.URLField(
        max_length=URL_MAX_LENGTH, required=False, help_text="HTTPS URL that gets a POST request for each event."
    )
    enabled = serializers.BooleanField(required=False, help_text="Whether PostHog sends events to this endpoint.")
    event_types = _event_types_field(
        required=False, help_text="The event types to send. An empty list sends all event types."
    )


class WebhookEndpointSerializer(serializers.Serializer):
    id = serializers.UUIDField(help_text="ID of the webhook endpoint.")
    url = serializers.URLField(help_text="HTTPS URL that gets a POST request for each event.")
    enabled = serializers.BooleanField(help_text="Whether PostHog sends events to this endpoint.")
    event_types = _event_types_field(help_text="The event types to send. An empty list sends all event types.")
    created_by = serializers.IntegerField(
        source="created_by_id", allow_null=True, help_text="ID of the user who created the endpoint."
    )
    created_at = serializers.DateTimeField(help_text="When the endpoint was created.")
    updated_at = serializers.DateTimeField(help_text="When the endpoint was last changed.")


class WebhookSecretSerializer(serializers.Serializer):
    secret = serializers.CharField(
        allow_null=True,
        help_text=(
            "The signing secret. It is present only in the response that creates or rotates it, so store it "
            "then. Null when the project already has a secret: rotate the secret to get a new one."
        ),
    )
    created = serializers.BooleanField(help_text="Whether this request created the secret.")


class WebhookTestSerializer(serializers.Serializer):
    delivery_id = serializers.UUIDField(help_text="ID of the delivery that carries the test event.")


class WebhookDeliverySerializer(serializers.Serializer):
    id = serializers.UUIDField(help_text="ID of the delivery.")
    endpoint = serializers.UUIDField(
        source="endpoint_id",
        allow_null=True,
        help_text="ID of the webhook endpoint. Null for a delivery to the webhook URL of one run.",
    )
    url = serializers.URLField(help_text="URL that the event was sent to.")
    run_id = serializers.UUIDField(help_text="ID of the run that the event is about.")
    event_type = LabeledEnumField(WebhookEvent, help_text="Type of the event.")
    event_id = serializers.UUIDField(
        help_text="ID of the event. It is the same for every attempt and for every endpoint that gets the event."
    )
    status = LabeledEnumField(
        WebhookDeliveryStatus,
        help_text=(
            "`pending` waits for an attempt, `succeeded` got a 2xx response, `failed` got a response that "
            "a retry cannot fix, and `gave_up` used all its retries."
        ),
    )
    attempts = serializers.IntegerField(help_text="How many times PostHog tried to send the event.")
    last_status_code = serializers.IntegerField(
        allow_null=True, help_text="HTTP status of the last attempt. Null when no response arrived."
    )
    last_error = serializers.CharField(
        allow_null=True, help_text="Kind of connection error of the last attempt. Null when a response arrived."
    )
    next_attempt_at = serializers.DateTimeField(
        allow_null=True, help_text="When the next attempt is due. Null when no attempt is planned."
    )
    delivered_at = serializers.DateTimeField(allow_null=True, help_text="When the receiver accepted the event.")
    created_at = serializers.DateTimeField(help_text="When the delivery was created.")


# --- Runs ---


class CloudAgentRunCreateSerializer(RunDefaultsSerializer):
    prompt = serializers.CharField(
        max_length=PROMPT_MAX_LENGTH,
        help_text="The task for the agent, in plain language.",
    )
    repository = serializers.RegexField(
        REPOSITORY_REGEX,
        max_length=255,
        required=False,
        allow_null=True,
        help_text=(
            "GitHub repository that the agent works in, in the format `owner/name`. Required unless the "
            "profile or the project settings set a default."
        ),
    )
    profile = serializers.CharField(
        max_length=100,
        required=False,
        allow_null=True,
        help_text=(
            "ID or name of the profile whose defaults the run uses. Null uses the default profile of the "
            "project, when one is set."
        ),
    )
    tags = _tags_field(required=False, help_text="Tags for the run. The tags of the profile are added to them.")
    metadata = serializers.DictField(
        child=serializers.CharField(max_length=METADATA_VALUE_MAX_LENGTH, allow_blank=True),
        required=False,
        help_text=(
            f"Your own key and value pairs, stored with the run and returned with it. At most "
            f"{MAX_METADATA_PAIRS} pairs. Keys and values are strings."
        ),
    )
    webhook_url = serializers.URLField(
        max_length=URL_MAX_LENGTH,
        required=False,
        allow_null=True,
        help_text="HTTPS URL that gets the events of this run, in addition to the webhook endpoints of the project.",
    )

    def validate_metadata(self, value: dict[str, str]) -> dict[str, str]:
        if len(value) > MAX_METADATA_PAIRS:
            raise serializers.ValidationError(f"Use at most {MAX_METADATA_PAIRS} metadata pairs.")
        if any(len(key) > METADATA_KEY_MAX_LENGTH for key in value):
            raise serializers.ValidationError(f"A metadata key can have {METADATA_KEY_MAX_LENGTH} characters at most.")
        return value


class CloudAgentRunMessageSerializer(serializers.Serializer):
    content = serializers.CharField(
        max_length=PROMPT_MAX_LENGTH, help_text="The follow-up message for the agent, in plain language."
    )


class CloudAgentRunListQuerySerializer(serializers.Serializer):
    status = LabeledEnumField(CloudAgentRunStatus, required=False, help_text="Return only the runs with this status.")
    profile_id = serializers.UUIDField(required=False, help_text="Return only the runs that used this profile.")
    repository = serializers.RegexField(
        REPOSITORY_REGEX,
        max_length=255,
        required=False,
        help_text="Return only the runs in this repository, in the format `owner/name`.",
    )
    tag = serializers.CharField(max_length=50, required=False, help_text="Return only the runs that have this tag.")
    created_after = serializers.DateTimeField(
        required=False, help_text="Return only the runs created at or after this time, in ISO 8601 format."
    )
    created_before = serializers.DateTimeField(
        required=False, help_text="Return only the runs created before this time, in ISO 8601 format."
    )


class CloudAgentRunProfileRefSerializer(serializers.Serializer):
    id = serializers.UUIDField(source="profile_id", help_text="ID of the profile.")
    name = serializers.CharField(source="profile_name", help_text="Name of the profile.")


class CloudAgentSizeSerializer(serializers.Serializer):
    name = LabeledEnumField(SizeName, help_text="Name of the size, as `<vCPU>x<memory in GiB>`.")
    vcpu = serializers.IntegerField(help_text="Number of vCPUs of the sandbox.")
    memory_gib = serializers.IntegerField(help_text="Memory of the sandbox in GiB.")
    price_per_hour_usd = serializers.DecimalField(
        max_digits=12,
        decimal_places=6,
        normalize_output=True,
        help_text="Compute price of one hour of this size in US dollars, as a decimal string.",
    )


class CloudAgentRunConfigSerializer(serializers.Serializer):
    """Reads a run: the stored configuration is in `config`, and the priced size is on the run."""

    model = serializers.CharField(source="config.model", allow_null=True, help_text="Model that the agent uses.")
    size = CloudAgentSizeSerializer(help_text="Sandbox size of the run. It is fixed for the life of the run.")
    inference = LabeledEnumField(
        InferenceMode,
        source="config.inference",
        help_text=(
            "How the run pays for model usage: `posthog` for PostHog inference, `own_subscription` for the "
            "subscription of the user."
        ),
    )
    create_pr = serializers.BooleanField(
        source="config.create_pr", help_text="Whether the agent opens a pull request when it finishes."
    )
    pr_mode = LabeledEnumField(
        PrMode,
        source="config.pr_mode",
        help_text="Whether the pull request opens as a draft or ready for review. Reserved. Not enforced yet.",
    )
    max_duration_minutes = serializers.IntegerField(
        source="config.max_duration_minutes", help_text="Time limit of the run in minutes."
    )
    max_cost_usd = serializers.DecimalField(
        source="config.max_cost_usd",
        max_digits=10,
        decimal_places=2,
        allow_null=True,
        help_text="Cost limit of the run in US dollars. Reserved. Not enforced yet.",
    )
    instructions_applied = serializers.SerializerMethodField(
        help_text="Whether the agent got instructions from the run, its profile or the project settings."
    )

    @extend_schema_field(serializers.BooleanField())
    def get_instructions_applied(self, run: RunDTO) -> bool:
        return bool(run.config.instructions)


class CloudAgentRunResultSerializer(serializers.Serializer):
    pr_url = serializers.URLField(allow_null=True, help_text="URL of the pull request that the agent opened last.")
    pr_urls = serializers.ListField(
        child=serializers.URLField(), help_text="URLs of all pull requests that the agent opened."
    )
    summary = serializers.CharField(allow_null=True, help_text="Summary of the work, written by the agent.")


def _usd_field(help_text: str, **kwargs: Any) -> serializers.DecimalField:
    return serializers.DecimalField(max_digits=14, decimal_places=4, help_text=help_text, **kwargs)


def _seconds_field(help_text: str, **kwargs: Any) -> serializers.DecimalField:
    return serializers.DecimalField(max_digits=16, decimal_places=3, help_text=help_text, **kwargs)


class CloudAgentRunCostSerializer(serializers.Serializer):
    compute_usd = _usd_field(
        "Compute cost in US dollars, as a decimal string. Null until the first sandbox reports usage.",
        allow_null=True,
    )
    inference_usd = _usd_field(
        "Model usage cost in US dollars, as a decimal string. Null when the run uses your own subscription, "
        "because you pay the model provider directly.",
        allow_null=True,
    )
    total_usd = _usd_field(
        "Sum of the compute cost and the model usage cost, as a decimal string. Null until the compute cost is known.",
        allow_null=True,
    )
    vcpu_seconds = _seconds_field("vCPU seconds that the run used.", allow_null=True)
    gib_seconds = _seconds_field("GiB seconds of memory that the run used.", allow_null=True)
    billing_mode = LabeledEnumField(
        BillingMode, help_text="`billed` when the project pays for the run, `unbilled` when it does not."
    )
    inference_billing = LabeledEnumField(
        InferenceBilling, allow_null=True, help_text="Who pays for the model usage of the run."
    )
    final = serializers.BooleanField(
        help_text="Whether the cost is final. The cost can still change for a short time after the run stops."
    )


class CloudAgentAgentSessionSerializer(serializers.Serializer):
    index = serializers.IntegerField(help_text="Position of the session in the run, from 1.")
    status = LabeledEnumField(CloudAgentRunStatus, help_text="Status of the session.")
    started_at = serializers.DateTimeField(allow_null=True, help_text="When the agent started work in this session.")
    ended_at = serializers.DateTimeField(allow_null=True, help_text="When the session ended.")


class CloudAgentRunCreatedBySerializer(serializers.Serializer):
    id = serializers.IntegerField(source="created_by_id", help_text="ID of the user.")
    email = serializers.CharField(source="created_by_email", allow_null=True, help_text="Email address of the user.")


class CloudAgentRunSerializer(serializers.Serializer):
    id = serializers.UUIDField(help_text="ID of the run.")
    status = LabeledEnumField(
        CloudAgentRunStatus,
        help_text=(
            "`queued` waits for a sandbox, `running` has an agent at work, and `completed`, `failed` and "
            "`cancelled` are final until you send a new message."
        ),
    )
    stop_reason = LabeledEnumField(
        StopReason, allow_null=True, help_text="Why the run stopped. Null while the run is active."
    )
    error = serializers.CharField(
        allow_null=True, help_text="What went wrong and what to do next. Null when the run has no error."
    )
    created_at = serializers.DateTimeField(help_text="When the run was created.")
    started_at = serializers.DateTimeField(allow_null=True, help_text="When the agent first started work.")
    completed_at = serializers.DateTimeField(allow_null=True, help_text="When the run stopped.")
    updated_at = serializers.DateTimeField(help_text="When the run last changed.")
    prompt = serializers.CharField(help_text="The task that the run started with.")
    repository = serializers.CharField(help_text="GitHub repository of the run, in the format `owner/name`.")
    branch = serializers.CharField(
        allow_null=True, help_text="Base branch of the run. Null uses the default branch of the repository."
    )
    profile = serializers.SerializerMethodField(help_text="The profile that the run used. Null when it used none.")
    config = CloudAgentRunConfigSerializer(source="*", help_text="The configuration that the run uses.")
    result = CloudAgentRunResultSerializer(help_text="What the agent produced.")
    cost = CloudAgentRunCostSerializer(help_text="What the run cost.")
    agent_sessions = CloudAgentAgentSessionSerializer(
        many=True,
        help_text="The agent sessions of the run, oldest first. A message to a run that stopped starts a new session.",
    )
    tags = _tags_field(help_text="Tags of the run, including the tags of its profile.")
    metadata = serializers.DictField(
        child=serializers.CharField(allow_blank=True), help_text="Your own key and value pairs."
    )
    created_by = serializers.SerializerMethodField(
        help_text="The user who started the run. Null when the user no longer exists."
    )
    caller = LabeledEnumField(
        CallerKind,
        source="caller_kind",
        help_text="`api` for an API client, `app` for the PostHog app, `internal` for a PostHog product.",
    )

    @extend_schema_field(CloudAgentRunProfileRefSerializer(allow_null=True))
    def get_profile(self, run: RunDTO) -> Any:
        return CloudAgentRunProfileRefSerializer(run).data if run.profile_id is not None else None

    @extend_schema_field(CloudAgentRunCreatedBySerializer(allow_null=True))
    def get_created_by(self, run: RunDTO) -> Any:
        return CloudAgentRunCreatedBySerializer(run).data if run.created_by_id is not None else None


class CloudAgentRunMessageResponseSerializer(serializers.Serializer):
    resumed = serializers.BooleanField(
        help_text=(
            "True when the message started a new agent session, because the run had stopped. False when "
            "the running agent got the message."
        )
    )
    run = CloudAgentRunSerializer(help_text="The run after the message.")


class CloudAgentSandboxSessionUsageSerializer(serializers.Serializer):
    vcpu = serializers.DecimalField(
        max_digits=8, decimal_places=3, normalize_output=True, help_text="Number of vCPUs of the sandbox."
    )
    memory_gib = serializers.DecimalField(
        max_digits=8, decimal_places=3, normalize_output=True, help_text="Memory of the sandbox in GiB."
    )
    started_at = serializers.DateTimeField(help_text="When the sandbox started.")
    ended_at = serializers.DateTimeField(allow_null=True, help_text="When the sandbox stopped. Null while it is up.")
    seconds = serializers.IntegerField(help_text="How many seconds of the sandbox count for the cost.")
    cost_usd = _usd_field("Compute cost of the sandbox in US dollars, as a decimal string.")
    waived = serializers.BooleanField(help_text="Whether PostHog waived the cost of this sandbox.")


class CloudAgentRunUsageSerializer(serializers.Serializer):
    run_id = serializers.UUIDField(help_text="ID of the run.")
    cost = CloudAgentRunCostSerializer(help_text="What the run cost up to now.")
    sessions = CloudAgentSandboxSessionUsageSerializer(many=True, help_text="The sandboxes of the run, oldest first.")


class CloudAgentRunEventsSerializer(serializers.Serializer):
    events = serializers.ListField(
        child=serializers.DictField(),
        help_text=(
            "The stored events of the run, oldest first, across all agent sessions. Each event is one "
            "agent protocol message with the time it was recorded."
        ),
    )
    truncated = serializers.BooleanField(
        help_text=(
            "True when the event log is too large to return in full. The response then has the earliest "
            "agent sessions that fit."
        )
    )


# --- Catalog, estimate and usage ---


class CloudAgentModelSerializer(serializers.Serializer):
    id = serializers.CharField(help_text="ID of the model. Use it as `model` when you start a run.")
    name = serializers.CharField(help_text="Display name of the model.")
    runtime_adapter = serializers.CharField(help_text="The agent runtime that drives the model.")
    is_default = serializers.BooleanField(help_text="Whether a run with no model uses this model.")


class CloudAgentRateCardSerializer(serializers.Serializer):
    vcpu_hour_usd = serializers.DecimalField(
        max_digits=12,
        decimal_places=6,
        normalize_output=True,
        help_text="Price of one vCPU for one hour in US dollars, as a decimal string.",
    )
    memory_gib_hour_usd = serializers.DecimalField(
        max_digits=12,
        decimal_places=6,
        normalize_output=True,
        help_text="Price of one GiB of memory for one hour in US dollars, as a decimal string.",
    )
    version = serializers.CharField(help_text="Version of the price list.")


class CloudAgentLimitsSerializer(serializers.Serializer):
    max_concurrent_runs = serializers.IntegerField(
        help_text="How many runs the project can have active at the same time."
    )
    create_rate_per_hour = serializers.IntegerField(help_text="How many runs the project can start in one hour.")


class CloudAgentCatalogSerializer(serializers.Serializer):
    sizes = CloudAgentSizeSerializer(many=True, help_text="The sandbox sizes that a run can use.")
    models = CloudAgentModelSerializer(many=True, help_text="The models that a run can use.")
    inference_modes = serializers.ListField(
        child=LabeledEnumField(InferenceMode), help_text="The values that `inference` accepts."
    )
    rates = CloudAgentRateCardSerializer(help_text="The compute prices that the size prices come from.")
    limits = CloudAgentLimitsSerializer(help_text="The limits of this project.")


class CloudAgentEstimateQuerySerializer(serializers.Serializer):
    size = LabeledEnumField(SizeName, help_text="Sandbox size to price, as `<vCPU>x<memory in GiB>`.")
    minutes = serializers.IntegerField(
        min_value=1, max_value=MAX_ESTIMATE_MINUTES, help_text="How many minutes the sandbox is up."
    )


class CloudAgentEstimateSerializer(serializers.Serializer):
    size = LabeledEnumField(SizeName, help_text="The sandbox size that was priced.")
    minutes = serializers.IntegerField(help_text="How many minutes the sandbox is up.")
    price_per_hour_usd = serializers.DecimalField(
        max_digits=12,
        decimal_places=6,
        normalize_output=True,
        help_text="Compute price of one hour of this size in US dollars, as a decimal string.",
    )
    estimate_usd = _usd_field(
        "Compute cost for the given minutes in US dollars, as a decimal string. Model usage is not included."
    )


class CloudAgentUsageQuerySerializer(serializers.Serializer):
    date_from = serializers.DateTimeField(
        required=False, help_text="Start of the range, in ISO 8601 format. The default is 30 days before `date_to`."
    )
    date_to = serializers.DateTimeField(
        required=False, help_text="End of the range, not included, in ISO 8601 format. The default is now."
    )
    group_by = LabeledEnumField(
        UsageGroupBy,
        required=False,
        default=UsageGroupBy.DAY,
        help_text="`day` gives one bucket for each UTC day. `profile` gives one bucket for each profile.",
    )


class CloudAgentUsageTotalsSerializer(serializers.Serializer):
    runs = serializers.IntegerField(help_text="Number of runs.")
    compute_usd = _usd_field("Compute cost in US dollars, as a decimal string.")
    inference_usd = _usd_field(
        "Model usage cost in US dollars, as a decimal string. Runs on your own subscription add nothing."
    )
    total_usd = _usd_field("Sum of the compute cost and the model usage cost, as a decimal string.")
    vcpu_seconds = _seconds_field("vCPU seconds used.")
    gib_seconds = _seconds_field("GiB seconds of memory used.")


class CloudAgentUsageBucketSerializer(serializers.Serializer):
    key = serializers.CharField(
        allow_null=True,
        help_text=(
            "The UTC date of the bucket for `group_by=day`. The profile ID for `group_by=profile`, or null "
            "for the runs that used no profile."
        ),
    )
    name = serializers.CharField(
        source="label", allow_null=True, help_text="Name of the profile for `group_by=profile`. Null for other buckets."
    )
    usage = CloudAgentUsageTotalsSerializer(help_text="Usage of the runs in this bucket.")


class CloudAgentUsageSummarySerializer(serializers.Serializer):
    date_from = serializers.DateTimeField(help_text="Start of the range.")
    date_to = serializers.DateTimeField(help_text="End of the range, not included.")
    group_by = LabeledEnumField(UsageGroupBy, help_text="How the buckets are grouped.")
    totals = CloudAgentUsageTotalsSerializer(help_text="Usage of all runs created in the range.")
    buckets = CloudAgentUsageBucketSerializer(many=True, help_text="Usage for each day or for each profile.")
