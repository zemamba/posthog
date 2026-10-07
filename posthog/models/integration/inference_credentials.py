"""A user's own inference credentials for cloud agent runs.

A user can store one Anthropic API key, one OpenAI API key, and one Claude subscription token. Each
lives on its own `UserIntegration` row, encrypted in `sensitive_config`. An API key is checked against
the provider before it is stored. Only server and worker code reads a secret back, through
`InferenceCredentialStore.resolve_secret`. No route returns one.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from django.db import connection, transaction
from django.utils import timezone

import requests
import structlog
import posthoganalytics

from posthog.dataclasses import frozen
from posthog.egress.llm_provider_auth import (
    ANTHROPIC_API_VERSION,
    ANTHROPIC_MODELS_URL,
    OPENAI_MODELS_URL,
    llm_provider_auth_request,
)
from posthog.enums import LabeledStrEnum
from posthog.exceptions_capture import capture_exception
from posthog.models.user_integration import UserIntegration

if TYPE_CHECKING:
    from posthog.models.user import User

logger = structlog.get_logger(__name__)

# Provider terms for server-side use of a Claude subscription token are not final, so storage stays off
# for every organization that this flag does not name.
CLAUDE_SUBSCRIPTION_STORAGE_FEATURE_FLAG = "cloud-agents-claude-subscription-storage"

PROVIDER_PROBE_TIMEOUT_SECONDS = (5.0, 10.0)
KEY_SUFFIX_LENGTH = 4
# The suffix is shown to the user, so a shorter secret would have most of its characters on display.
MIN_SECRET_LENGTH = 20
MAX_SECRET_LENGTH = 1024

ANTHROPIC_KEY_PREFIX = "sk-ant-"
CLAUDE_SUBSCRIPTION_TOKEN_PREFIX = "sk-ant-oat"
OPENAI_KEY_PREFIX = "sk-"


class InferenceCredentialKind(LabeledStrEnum):
    ANTHROPIC_API_KEY = "anthropic_api_key", "Anthropic API key"
    OPENAI_API_KEY = "openai_api_key", "OpenAI API key"
    CLAUDE_SUBSCRIPTION = "claude_subscription", "Claude subscription"


class InferenceProvider(LabeledStrEnum):
    ANTHROPIC = "anthropic", "Anthropic"
    OPENAI = "openai", "OpenAI"


class InferenceCredentialType(LabeledStrEnum):
    API_KEY = "api_key", "API key"
    SUBSCRIPTION = "subscription", "Subscription"


INFERENCE_CREDENTIAL_PROVIDERS: dict[InferenceCredentialKind, InferenceProvider] = {
    InferenceCredentialKind.ANTHROPIC_API_KEY: InferenceProvider.ANTHROPIC,
    InferenceCredentialKind.OPENAI_API_KEY: InferenceProvider.OPENAI,
    InferenceCredentialKind.CLAUDE_SUBSCRIPTION: InferenceProvider.ANTHROPIC,
}

INFERENCE_CREDENTIAL_TYPES: dict[InferenceCredentialKind, InferenceCredentialType] = {
    InferenceCredentialKind.ANTHROPIC_API_KEY: InferenceCredentialType.API_KEY,
    InferenceCredentialKind.OPENAI_API_KEY: InferenceCredentialType.API_KEY,
    InferenceCredentialKind.CLAUDE_SUBSCRIPTION: InferenceCredentialType.SUBSCRIPTION,
}


class InferenceCredentialError(Exception):
    """The credential was not stored. The message is safe to show to the user and never holds the secret."""


class InvalidInferenceCredential(InferenceCredentialError):
    """The secret has the wrong format for its kind, or the provider does not accept it."""


class InferenceCredentialUnverified(InferenceCredentialError):
    """The provider did not give a usable answer, so the secret could not be checked."""


@frozen
class InferenceCredentialSummary:
    kind: InferenceCredentialKind
    provider: InferenceProvider
    credential_type: InferenceCredentialType
    key_suffix: str
    created_at: datetime
    last_used_at: datetime | None


def claude_subscription_storage_enabled(user: "User", organization_id: str | int | None = None) -> bool:
    organization_id = str(organization_id or user.current_organization_id)
    try:
        enabled = posthoganalytics.feature_enabled(
            CLAUDE_SUBSCRIPTION_STORAGE_FEATURE_FLAG,
            str(user.distinct_id),
            groups={"organization": organization_id},
            group_properties={"organization": {"id": organization_id}},
            only_evaluate_locally=False,
            send_feature_flag_events=False,
        )
    except Exception as error:
        capture_exception(error)
        return False
    return bool(enabled)


def validate_secret_format(kind: InferenceCredentialKind, secret: str) -> None:
    if not MIN_SECRET_LENGTH <= len(secret) <= MAX_SECRET_LENGTH or any(character.isspace() for character in secret):
        raise InvalidInferenceCredential("This does not look like a valid credential. Check that you copied all of it.")
    match kind:
        case InferenceCredentialKind.ANTHROPIC_API_KEY:
            if secret.startswith(CLAUDE_SUBSCRIPTION_TOKEN_PREFIX):
                raise InvalidInferenceCredential(
                    "This is a Claude subscription token, not an Anthropic API key. "
                    "Add it as a Claude subscription instead."
                )
            if not secret.startswith(ANTHROPIC_KEY_PREFIX):
                raise InvalidInferenceCredential("An Anthropic API key starts with `sk-ant-`.")
        case InferenceCredentialKind.CLAUDE_SUBSCRIPTION:
            if secret.startswith(ANTHROPIC_KEY_PREFIX) and not secret.startswith(CLAUDE_SUBSCRIPTION_TOKEN_PREFIX):
                raise InvalidInferenceCredential(
                    "This is an Anthropic API key, not a Claude subscription token. Add it as an Anthropic API key "
                    "instead, or run `claude setup-token` to get a subscription token."
                )
            if not secret.startswith(CLAUDE_SUBSCRIPTION_TOKEN_PREFIX):
                raise InvalidInferenceCredential(
                    "A Claude subscription token starts with `sk-ant-oat`. Run `claude setup-token` to get one."
                )
        case InferenceCredentialKind.OPENAI_API_KEY:
            if secret.startswith(ANTHROPIC_KEY_PREFIX):
                raise InvalidInferenceCredential("This is an Anthropic credential, not an OpenAI API key.")
            if not secret.startswith(OPENAI_KEY_PREFIX):
                raise InvalidInferenceCredential("An OpenAI API key starts with `sk-`.")


def verify_api_key_with_provider(provider: InferenceProvider, api_key: str, *, source: str) -> None:
    """Ask the provider for its model list with the key. Only the status code is read."""
    provider_name = provider.label
    response: requests.Response | None = None
    try:
        match provider:
            case InferenceProvider.ANTHROPIC:
                response = llm_provider_auth_request(
                    "GET",
                    ANTHROPIC_MODELS_URL,
                    provider="anthropic",
                    source=source,
                    endpoint="v1/models",
                    headers={"x-api-key": api_key, "anthropic-version": ANTHROPIC_API_VERSION},
                    timeout=PROVIDER_PROBE_TIMEOUT_SECONDS,
                    params={"limit": 1},
                    allow_redirects=False,
                )
            case InferenceProvider.OPENAI:
                response = llm_provider_auth_request(
                    "GET",
                    OPENAI_MODELS_URL,
                    provider="openai",
                    source=source,
                    endpoint="v1/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=PROVIDER_PROBE_TIMEOUT_SECONDS,
                    allow_redirects=False,
                )
    except requests.RequestException as error:
        logger.warning("inference_credential_probe_failed", provider=provider.value, error_type=type(error).__name__)
    if response is None:
        # Raised outside the `except` block on purpose. The transport exception holds the prepared
        # request, which holds the key in a header, so it must not travel as the context of this error.
        raise InferenceCredentialUnverified(f"Could not reach {provider_name} to verify the key. Try again.")
    if response.status_code == 401:
        raise InvalidInferenceCredential(f"{provider_name} rejected this API key. Check the key and try again.")
    if response.status_code == 403:
        raise InvalidInferenceCredential(
            f"{provider_name} refused this API key (HTTP 403). Check that the key is active and can list models."
        )
    if not response.ok:
        logger.warning(
            "inference_credential_probe_unexpected_status", provider=provider.value, status_code=response.status_code
        )
        raise InferenceCredentialUnverified(
            f"Could not verify the key because {provider_name} returned HTTP {response.status_code}. Try again."
        )


class InferenceCredentialStore:
    """The `UserIntegration` rows that hold a user's inference credentials: one row per user per kind."""

    @classmethod
    def list_for_user(cls, user_id: int) -> list[InferenceCredentialSummary]:
        rows = UserIntegration.objects.filter(user_id=user_id, kind__in=InferenceCredentialKind.values).order_by("kind")
        return [cls._summary(row) for row in rows]

    @classmethod
    def has(cls, user_id: int, kind: InferenceCredentialKind) -> bool:
        return UserIntegration.objects.filter(user_id=user_id, kind=kind.value).exists()

    @classmethod
    def connect(
        cls, user_id: int, kind: InferenceCredentialKind, secret: str, *, source: str = "inference_credential_store"
    ) -> InferenceCredentialSummary:
        """Check the secret, then store it in place of any credential of the same kind.

        Raises `InvalidInferenceCredential` or `InferenceCredentialUnverified`, and stores nothing then.
        """
        secret = secret.strip()
        validate_secret_format(kind, secret)
        # No provider call for a subscription token: no documented endpoint accepts one for a check.
        if INFERENCE_CREDENTIAL_TYPES[kind] == InferenceCredentialType.API_KEY:
            verify_api_key_with_provider(INFERENCE_CREDENTIAL_PROVIDERS[kind], secret, source=source)

        # The provider call above stays outside this transaction so a slow provider holds no lock.
        with transaction.atomic():
            cls._lock_user(user_id, kind)
            row, _ = UserIntegration.objects.update_or_create(
                user_id=user_id,
                kind=kind.value,
                defaults={
                    "integration_id": kind.value,
                    "config": {
                        "key_suffix": secret[-KEY_SUFFIX_LENGTH:],
                        "connected_at": timezone.now().isoformat(),
                        "last_used_at": None,
                    },
                    "sensitive_config": {"secret": secret},
                },
            )
        return cls._summary(row)

    @classmethod
    def disconnect(cls, user_id: int, kind: InferenceCredentialKind) -> bool:
        deleted, _ = UserIntegration.objects.filter(user_id=user_id, kind=kind.value).delete()
        return deleted > 0

    @classmethod
    def resolve_secret(cls, user_id: int, kind: InferenceCredentialKind) -> str | None:
        """The stored secret, for server and worker code only. Never return the result from an API route."""
        with transaction.atomic():
            row = UserIntegration.objects.select_for_update().filter(user_id=user_id, kind=kind.value).first()
            if row is None:
                return None
            secret = row.sensitive_config.get("secret")
            if not isinstance(secret, str) or not secret:
                return None
            row.config = {**row.config, "last_used_at": timezone.now().isoformat()}
            row.save(update_fields=["config", "updated_at"])
        return secret

    @classmethod
    def _lock_user(cls, user_id: int, kind: InferenceCredentialKind) -> None:
        # Row locks cannot protect the first connection because its record does not exist yet.
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT pg_advisory_xact_lock(%s, hashtext(%s))", [user_id, f"user_integration:{kind.value}"]
            )

    @classmethod
    def _summary(cls, row: UserIntegration) -> InferenceCredentialSummary:
        kind = InferenceCredentialKind(row.kind)
        return InferenceCredentialSummary(
            kind=kind,
            provider=INFERENCE_CREDENTIAL_PROVIDERS[kind],
            credential_type=INFERENCE_CREDENTIAL_TYPES[kind],
            key_suffix=str(row.config.get("key_suffix") or ""),
            created_at=cls._parse_datetime(row.config.get("connected_at")) or row.created_at,
            last_used_at=cls._parse_datetime(row.config.get("last_used_at")),
        )

    @staticmethod
    def _parse_datetime(value: object) -> datetime | None:
        if not isinstance(value, str):
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
