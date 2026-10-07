from datetime import UTC, datetime

import time_machine
from posthog.test.base import BaseTest
from unittest.mock import patch

from django.db import connection
from django.test import SimpleTestCase

import requests
from parameterized import parameterized

from posthog.models.integration.inference_credentials import (
    INFERENCE_CREDENTIAL_PROVIDERS,
    INFERENCE_CREDENTIAL_TYPES,
    InferenceCredentialError,
    InferenceCredentialKind,
    InferenceCredentialStore,
    InferenceCredentialUnverified,
    InvalidInferenceCredential,
    claude_subscription_storage_enabled,
    validate_secret_format,
)
from posthog.models.user import User
from posthog.models.user_integration import UserIntegration

FROZEN_NOW = datetime(2026, 3, 1, 12, 0, tzinfo=UTC)

ANTHROPIC_KEY = "sk-ant-api03-not-a-real-key-0001"
OPENAI_KEY = "sk-proj-not-a-real-key-000000002"
CLAUDE_TOKEN = "sk-ant-oat01-not-a-real-token-0003"

VALID_SECRETS = {
    InferenceCredentialKind.ANTHROPIC_API_KEY: ANTHROPIC_KEY,
    InferenceCredentialKind.OPENAI_API_KEY: OPENAI_KEY,
    InferenceCredentialKind.CLAUDE_SUBSCRIPTION: CLAUDE_TOKEN,
}


def _provider_response(status_code: int) -> requests.Response:
    response = requests.Response()
    response.status_code = status_code
    response._content = b"{}"
    return response


class TestValidateSecretFormat(SimpleTestCase):
    @parameterized.expand([(kind.value, kind) for kind in InferenceCredentialKind])
    def test_accepts_the_secret_of_its_own_kind(self, _name: str, kind: InferenceCredentialKind) -> None:
        validate_secret_format(kind, VALID_SECRETS[kind])

    @parameterized.expand(
        [
            ("subscription_token_as_anthropic_key", InferenceCredentialKind.ANTHROPIC_API_KEY, CLAUDE_TOKEN),
            ("openai_key_as_anthropic_key", InferenceCredentialKind.ANTHROPIC_API_KEY, OPENAI_KEY),
            ("anthropic_key_as_subscription", InferenceCredentialKind.CLAUDE_SUBSCRIPTION, ANTHROPIC_KEY),
            ("openai_key_as_subscription", InferenceCredentialKind.CLAUDE_SUBSCRIPTION, OPENAI_KEY),
            ("anthropic_key_as_openai_key", InferenceCredentialKind.OPENAI_API_KEY, ANTHROPIC_KEY),
            ("subscription_token_as_openai_key", InferenceCredentialKind.OPENAI_API_KEY, CLAUDE_TOKEN),
            ("no_prefix", InferenceCredentialKind.OPENAI_API_KEY, "not-a-real-key-000000000004"),
            ("too_short", InferenceCredentialKind.OPENAI_API_KEY, "sk-short"),
            ("inner_whitespace", InferenceCredentialKind.OPENAI_API_KEY, "sk-proj-not-a-real key-000000005"),
        ]
    )
    def test_rejects_a_secret_of_the_wrong_shape_without_echoing_it(
        self, _name: str, kind: InferenceCredentialKind, secret: str
    ) -> None:
        with self.assertRaises(InvalidInferenceCredential) as raised:
            validate_secret_format(kind, secret)

        assert secret not in str(raised.exception)

    def test_every_kind_has_a_provider_and_a_credential_type(self) -> None:
        assert set(INFERENCE_CREDENTIAL_PROVIDERS) == set(InferenceCredentialKind)
        assert set(INFERENCE_CREDENTIAL_TYPES) == set(InferenceCredentialKind)


class TestInferenceCredentialStore(BaseTest):
    def _connect(self, kind: InferenceCredentialKind, secret: str | None = None, *, user: User | None = None) -> None:
        with patch("requests.request", return_value=_provider_response(200)):
            InferenceCredentialStore.connect((user or self.user).id, kind, secret or VALID_SECRETS[kind])

    def _raw_sensitive_config(self, kind: InferenceCredentialKind) -> str:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT sensitive_config::text FROM posthog_user_integration WHERE user_id = %s AND kind = %s",
                [self.user.id, kind.value],
            )
            return cursor.fetchone()[0]

    @parameterized.expand(
        [
            (
                "anthropic",
                InferenceCredentialKind.ANTHROPIC_API_KEY,
                "https://api.anthropic.com/v1/models",
                "x-api-key",
            ),
            ("openai", InferenceCredentialKind.OPENAI_API_KEY, "https://api.openai.com/v1/models", "Authorization"),
        ]
    )
    @time_machine.travel(FROZEN_NOW, tick=False)
    def test_connect_checks_an_api_key_with_its_provider_and_stores_it_encrypted(
        self, _name: str, kind: InferenceCredentialKind, url: str, header: str
    ) -> None:
        secret = VALID_SECRETS[kind]
        with patch("requests.request", return_value=_provider_response(200)) as request:
            summary = InferenceCredentialStore.connect(self.user.id, kind, f"  {secret}\n")

        assert request.call_args.args == ("GET", url)
        assert request.call_args.kwargs["headers"][header].endswith(secret)
        assert request.call_args.kwargs["timeout"] is not None
        assert summary.kind == kind
        assert summary.provider == INFERENCE_CREDENTIAL_PROVIDERS[kind]
        assert summary.credential_type == "api_key"
        assert summary.key_suffix == secret[-4:]
        assert summary.created_at == FROZEN_NOW
        assert summary.last_used_at is None
        assert secret not in repr(summary)

        row = UserIntegration.objects.get(user=self.user, kind=kind.value)
        assert row.sensitive_config == {"secret": secret}
        assert secret not in row.integration_id
        assert secret not in str(row.config)
        assert secret not in self._raw_sensitive_config(kind)
        assert InferenceCredentialStore.has(self.user.id, kind)

    def test_connect_replaces_the_credential_of_the_same_kind_and_keeps_the_other_kinds(self) -> None:
        self._connect(InferenceCredentialKind.OPENAI_API_KEY)
        self._connect(InferenceCredentialKind.ANTHROPIC_API_KEY, "sk-ant-api03-not-a-real-key-first")
        InferenceCredentialStore.resolve_secret(self.user.id, InferenceCredentialKind.ANTHROPIC_API_KEY)

        self._connect(InferenceCredentialKind.ANTHROPIC_API_KEY, "sk-ant-api03-not-a-real-key-second")

        summaries = {summary.kind: summary for summary in InferenceCredentialStore.list_for_user(self.user.id)}
        assert set(summaries) == {InferenceCredentialKind.ANTHROPIC_API_KEY, InferenceCredentialKind.OPENAI_API_KEY}
        assert summaries[InferenceCredentialKind.ANTHROPIC_API_KEY].key_suffix == "cond"
        assert summaries[InferenceCredentialKind.ANTHROPIC_API_KEY].last_used_at is None
        assert UserIntegration.objects.filter(user=self.user, kind="anthropic_api_key").count() == 1
        assert (
            InferenceCredentialStore.resolve_secret(self.user.id, InferenceCredentialKind.ANTHROPIC_API_KEY)
            == "sk-ant-api03-not-a-real-key-second"
        )

    @parameterized.expand(
        [
            ("unauthorized", _provider_response(401), InvalidInferenceCredential),
            ("forbidden", _provider_response(403), InvalidInferenceCredential),
            ("rate_limited", _provider_response(429), InferenceCredentialUnverified),
            ("server_error", _provider_response(503), InferenceCredentialUnverified),
            ("connection_error", requests.ConnectionError("refused"), InferenceCredentialUnverified),
            ("timeout", requests.Timeout("slow"), InferenceCredentialUnverified),
        ]
    )
    def test_connect_stores_nothing_when_the_provider_does_not_confirm_the_key(
        self, _name: str, outcome: requests.Response | Exception, expected: type[InferenceCredentialError]
    ) -> None:
        self._connect(InferenceCredentialKind.ANTHROPIC_API_KEY, "sk-ant-api03-not-a-real-key-first")

        with patch("requests.request", side_effect=[outcome]), self.assertRaises(expected) as raised:
            InferenceCredentialStore.connect(self.user.id, InferenceCredentialKind.ANTHROPIC_API_KEY, ANTHROPIC_KEY)

        assert ANTHROPIC_KEY not in str(raised.exception)
        assert raised.exception.__context__ is None
        assert (
            InferenceCredentialStore.resolve_secret(self.user.id, InferenceCredentialKind.ANTHROPIC_API_KEY)
            == "sk-ant-api03-not-a-real-key-first"
        )

    def test_connect_stores_a_subscription_token_without_a_provider_call(self) -> None:
        with patch("requests.request") as request:
            summary = InferenceCredentialStore.connect(
                self.user.id, InferenceCredentialKind.CLAUDE_SUBSCRIPTION, CLAUDE_TOKEN
            )

        request.assert_not_called()
        assert summary.provider == "anthropic"
        assert summary.credential_type == "subscription"
        assert CLAUDE_TOKEN not in self._raw_sensitive_config(InferenceCredentialKind.CLAUDE_SUBSCRIPTION)

    def test_connect_rejects_a_wrong_format_before_any_provider_call(self) -> None:
        with patch("requests.request") as request, self.assertRaises(InvalidInferenceCredential):
            InferenceCredentialStore.connect(self.user.id, InferenceCredentialKind.OPENAI_API_KEY, ANTHROPIC_KEY)

        request.assert_not_called()
        assert not InferenceCredentialStore.has(self.user.id, InferenceCredentialKind.OPENAI_API_KEY)

    def test_resolve_secret_returns_the_secret_and_records_the_use(self) -> None:
        with time_machine.travel(FROZEN_NOW, tick=False):
            self._connect(InferenceCredentialKind.OPENAI_API_KEY)
        used_at = datetime(2026, 3, 2, 9, 30, tzinfo=UTC)

        with time_machine.travel(used_at, tick=False):
            secret = InferenceCredentialStore.resolve_secret(self.user.id, InferenceCredentialKind.OPENAI_API_KEY)

        assert secret == OPENAI_KEY
        [summary] = InferenceCredentialStore.list_for_user(self.user.id)
        assert summary.last_used_at == used_at
        assert summary.created_at == FROZEN_NOW
        assert InferenceCredentialStore.resolve_secret(self.user.id, InferenceCredentialKind.ANTHROPIC_API_KEY) is None

    def test_one_user_cannot_reach_the_credentials_of_another_user(self) -> None:
        other = User.objects.create_and_join(self.organization, "other@example.com", None)
        self._connect(InferenceCredentialKind.OPENAI_API_KEY)
        self._connect(InferenceCredentialKind.OPENAI_API_KEY, "sk-proj-not-a-real-key-of-other", user=other)

        assert [summary.key_suffix for summary in InferenceCredentialStore.list_for_user(other.id)] == ["ther"]
        assert InferenceCredentialStore.disconnect(other.id, InferenceCredentialKind.OPENAI_API_KEY) is True
        assert InferenceCredentialStore.disconnect(other.id, InferenceCredentialKind.OPENAI_API_KEY) is False
        assert InferenceCredentialStore.resolve_secret(other.id, InferenceCredentialKind.OPENAI_API_KEY) is None
        assert InferenceCredentialStore.resolve_secret(self.user.id, InferenceCredentialKind.OPENAI_API_KEY) == (
            OPENAI_KEY
        )

    @parameterized.expand(
        [
            ("enabled", True, None, True),
            ("disabled", False, None, False),
            ("no_answer", None, None, False),
            ("check_failed", None, RuntimeError("down"), False),
        ]
    )
    def test_subscription_storage_flag_is_scoped_to_the_organization_and_fails_closed(
        self, _name: str, flag_value: bool | None, error: Exception | None, expected: bool
    ) -> None:
        with patch(
            "posthog.models.integration.inference_credentials.posthoganalytics.feature_enabled",
            return_value=flag_value,
            side_effect=error,
        ) as feature_enabled:
            assert claude_subscription_storage_enabled(self.user) is expected

        assert feature_enabled.call_args.args[0] == "cloud-agents-claude-subscription-storage"
        assert feature_enabled.call_args.kwargs["groups"] == {"organization": str(self.organization.id)}
