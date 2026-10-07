"""DRF serializers for cloud_agents."""

from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import Any

from rest_framework import serializers

from ..facade.api import MAX_DURATION_MINUTES, MIN_DURATION_MINUTES
from ..facade.enums import InferenceMode, PrMode, SizeName, WebhookDeliveryStatus, WebhookEvent

REPOSITORY_REGEX = r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$"
MAX_TAGS = 20
URL_MAX_LENGTH = 2000


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
            "How the agent pays for model usage. `auto` uses your own key or subscription when one is "
            "connected, and PostHog inference otherwise. Null uses the product default."
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
        help_text="Whether the pull request opens as a draft or ready for review. Null uses the product default.",
    )
    max_duration_minutes = serializers.IntegerField(
        min_value=MIN_DURATION_MINUTES,
        max_value=MAX_DURATION_MINUTES,
        required=False,
        allow_null=True,
        help_text=(
            f"The run stops after this many minutes, from {MIN_DURATION_MINUTES} to {MAX_DURATION_MINUTES}. "
            "Null uses the product default."
        ),
    )
    max_cost_usd = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0.01"),
        required=False,
        allow_null=True,
        help_text="The run stops when its cost reaches this amount in US dollars. Null sets no cost limit.",
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


class SettingsUpdateSerializer(RunDefaultsSerializer):
    default_profile = serializers.UUIDField(
        required=False,
        allow_null=True,
        help_text="ID of the profile that a run uses when it names no profile. Null sets no default profile.",
    )


class SettingsSerializer(RunDefaultsSerializer):
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
