from typing import cast

from rest_framework import exceptions, serializers, status
from rest_framework.request import Request
from rest_framework.response import Response

from posthog.event_usage import report_user_action
from posthog.models.integration.inference_credentials import (
    MAX_SECRET_LENGTH,
    InferenceCredentialKind,
    InferenceCredentialStore,
    InferenceCredentialSummary,
    InferenceCredentialType,
    InferenceCredentialUnverified,
    InferenceProvider,
    InvalidInferenceCredential,
    claude_subscription_storage_enabled,
)
from posthog.models.user import User
from posthog.oauth_provenance import is_sandbox_origin_request

INFERENCE_CREDENTIAL_KIND_URL_PATTERN = "|".join(InferenceCredentialKind.values)
INFERENCE_CREDENTIAL_SOURCE = "user_integration_api"


class UserInferenceCredentialConnectRequestSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(
        choices=InferenceCredentialKind.choices,
        help_text=(
            "Which credential to store. `anthropic_api_key` and `openai_api_key` are API keys from the provider "
            "console. `claude_subscription` is the token that `claude setup-token` prints. A user has at most one "
            "credential of each kind, so a new one replaces the stored one."
        ),
    )
    secret = serializers.CharField(
        write_only=True,
        max_length=MAX_SECRET_LENGTH,
        style={"input_type": "password"},
        help_text=(
            "The API key or subscription token. PostHog checks an API key with the provider, then stores the "
            "secret encrypted. No response returns it."
        ),
    )


class UserInferenceCredentialSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(
        choices=InferenceCredentialKind.choices, help_text="The kind of the stored credential."
    )
    provider = serializers.ChoiceField(
        choices=InferenceProvider.choices, help_text="The inference provider that the credential belongs to."
    )
    credential_type = serializers.ChoiceField(
        choices=InferenceCredentialType.choices,
        help_text="`api_key` for a provider API key, `subscription` for a Claude subscription token.",
    )
    key_suffix = serializers.CharField(
        help_text="The last 4 characters of the secret, so the user can tell which credential is stored."
    )
    created_at = serializers.DateTimeField(help_text="When this credential was stored.")
    last_used_at = serializers.DateTimeField(
        allow_null=True, help_text="When a cloud agent run last used this credential. Null when no run has used it."
    )


class UserInferenceCredentialListResponseSerializer(serializers.Serializer):
    results = UserInferenceCredentialSerializer(
        many=True, help_text="The inference credentials the user has stored, at most one of each kind."
    )


class InferenceProviderUnavailable(exceptions.APIException):
    status_code = status.HTTP_502_BAD_GATEWAY
    default_code = "inference_provider_unavailable"


def ensure_not_sandbox_inference_request(request: Request) -> None:
    if is_sandbox_origin_request(request):
        raise exceptions.PermissionDenied("Cloud agent runs cannot read or change stored inference credentials.")


def get_own_user(request: Request, user_uuid: str | None) -> User:
    """The requesting user. Unlike the other personal integrations, staff cannot name another user here."""
    user = cast(User, request.user)
    if user_uuid not in (None, "@me", str(user.uuid)):
        raise exceptions.PermissionDenied("You can only manage your own inference credentials.")
    return user


def serialize_inference_credential(summary: InferenceCredentialSummary) -> dict[str, object]:
    return dict(UserInferenceCredentialSerializer(summary).data)


def list_inference_credentials(user: User) -> Response:
    summaries = InferenceCredentialStore.list_for_user(user.id)
    return Response({"results": [serialize_inference_credential(summary) for summary in summaries]})


def connect_inference_credential(user: User, kind: InferenceCredentialKind, secret: str) -> Response:
    if kind == InferenceCredentialKind.CLAUDE_SUBSCRIPTION and not claude_subscription_storage_enabled(user):
        raise exceptions.PermissionDenied("Storing a Claude subscription token is not available for your organization.")
    try:
        summary = InferenceCredentialStore.connect(user.id, kind, secret, source=INFERENCE_CREDENTIAL_SOURCE)
    except InvalidInferenceCredential as error:
        report_user_action(user, "inference credential connect failed", {"kind": kind.value, "reason": "invalid"})
        raise exceptions.ValidationError({"secret": str(error)})
    except InferenceCredentialUnverified as error:
        report_user_action(user, "inference credential connect failed", {"kind": kind.value, "reason": "unverified"})
        raise InferenceProviderUnavailable(str(error))
    report_user_action(user, "inference credential connected", {"kind": kind.value})
    return Response(serialize_inference_credential(summary), status=status.HTTP_201_CREATED)


def disconnect_inference_credential(user: User, kind: InferenceCredentialKind) -> Response:
    if InferenceCredentialStore.disconnect(user.id, kind):
        report_user_action(user, "inference credential disconnected", {"kind": kind.value})
    return Response(status=status.HTTP_204_NO_CONTENT)
