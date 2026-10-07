from typing import Any

from posthog.test.base import BaseTest
from unittest.mock import patch

from django.test import SimpleTestCase

from parameterized import parameterized

from posthog.models.user import User
from posthog.models.user_integration import UserIntegration

from products.tasks.backend.facade import inference
from products.tasks.backend.logic.services.inference_resolution import (
    InvalidInferenceState,
    issue_run_inference_credential,
    validated_inference_state,
)

MODULE = "products.tasks.backend.logic.services.inference_resolution"

OWN_KEY_CLAUDE = {"claude_model_access": "own-key"}
OWN_KEY_CODEX = {"codex_model_access": "own-key"}
SUBSCRIPTION_CLAUDE = {"claude_model_access": "own-subscription", "claude_subscription_source": "server"}
SUBSCRIPTION_CODEX = {"codex_model_access": "own-subscription"}


class TestResolveInference(BaseTest):
    def _store(self, user: User, kind: str) -> None:
        if kind == "codex":
            UserIntegration.objects.create(
                user=user, kind="codex", integration_id="acct", config={"status": "connected"}
            )
            return
        UserIntegration.objects.create(
            user=user, kind=kind, integration_id=kind, config={}, sensitive_config={"secret": f"sk-fake-{kind}"}
        )

    def _resolve(
        self, *, adapter: str, requested: str, stored: tuple[str, ...], flags: bool, user: User | None
    ) -> inference.InferenceDecision:
        for kind in stored:
            self._store(self.user, kind)
        with (
            patch(f"{MODULE}.claude_subscription_storage_enabled", return_value=flags),
            patch(f"{MODULE}.posthoganalytics.feature_enabled", return_value=flags),
        ):
            return inference.resolve_inference(
                user_id=user.id if user else None,
                team_id=self.team.id,
                runtime_adapter=adapter,
                requested=requested,  # type: ignore[arg-type]
            )

    @parameterized.expand(
        [
            # name, adapter, requested, stored, flags, mode, credential_kind, state updates
            (
                "auto_prefers_the_key",
                "claude",
                "auto",
                ("anthropic_api_key", "claude_subscription"),
                True,
                "own_key",
                "anthropic_api_key",
                OWN_KEY_CLAUDE,
            ),
            (
                "auto_uses_the_subscription",
                "claude",
                "auto",
                ("claude_subscription",),
                True,
                "own_subscription",
                "claude_subscription",
                SUBSCRIPTION_CLAUDE,
            ),
            (
                "auto_ignores_a_subscription_with_the_flag_off",
                "claude",
                "auto",
                ("claude_subscription",),
                False,
                "posthog",
                None,
                {},
            ),
            ("auto_with_nothing_stored", "claude", "auto", (), True, "posthog", None, {}),
            (
                "auto_ignores_the_key_of_the_other_provider",
                "claude",
                "auto",
                ("openai_api_key", "codex"),
                True,
                "posthog",
                None,
                {},
            ),
            (
                "auto_codex_prefers_the_key",
                "codex",
                "auto",
                ("openai_api_key", "codex"),
                True,
                "own_key",
                "openai_api_key",
                OWN_KEY_CODEX,
            ),
            (
                "auto_codex_uses_the_chatgpt_account",
                "codex",
                "auto",
                ("codex",),
                True,
                "own_subscription",
                "codex",
                SUBSCRIPTION_CODEX,
            ),
            (
                "auto_codex_ignores_the_account_with_the_flag_off",
                "codex",
                "auto",
                ("codex",),
                False,
                "posthog",
                None,
                {},
            ),
            (
                "explicit_key",
                "claude",
                "own_key",
                ("anthropic_api_key",),
                False,
                "own_key",
                "anthropic_api_key",
                OWN_KEY_CLAUDE,
            ),
            (
                "explicit_codex_key",
                "codex",
                "own_key",
                ("openai_api_key",),
                False,
                "own_key",
                "openai_api_key",
                OWN_KEY_CODEX,
            ),
            (
                "explicit_subscription_over_a_stored_key",
                "claude",
                "own_subscription",
                ("anthropic_api_key", "claude_subscription"),
                True,
                "own_subscription",
                "claude_subscription",
                SUBSCRIPTION_CLAUDE,
            ),
            (
                "explicit_codex_subscription",
                "codex",
                "own_subscription",
                ("codex",),
                True,
                "own_subscription",
                "codex",
                SUBSCRIPTION_CODEX,
            ),
            (
                "explicit_posthog_over_a_stored_key",
                "claude",
                "posthog",
                ("anthropic_api_key",),
                True,
                "posthog",
                None,
                {},
            ),
        ]
    )
    def test_resolves_the_mode_and_the_state_to_stamp(
        self,
        _name: str,
        adapter: str,
        requested: str,
        stored: tuple[str, ...],
        flags: bool,
        mode: str,
        credential_kind: str | None,
        updates: dict[str, Any],
    ) -> None:
        decision = self._resolve(adapter=adapter, requested=requested, stored=stored, flags=flags, user=self.user)

        assert decision.mode == mode
        assert decision.adapter == adapter
        assert decision.credential_kind == credential_kind
        assert decision.owner_user_id == (None if mode == "posthog" else self.user.id)
        assert dict(decision.run_state_updates) == updates
        assert decision.resolved_from_auto is (requested == "auto")
        assert "sk-fake" not in repr(decision)
        assert inference.inference_billing_for_state({"runtime_adapter": adapter, **updates}) == mode

    @parameterized.expand(
        [
            (
                "key_not_stored",
                "claude",
                "own_key",
                ("openai_api_key", "claude_subscription"),
                True,
                True,
                "credential_missing",
            ),
            (
                "codex_key_not_stored",
                "codex",
                "own_key",
                ("anthropic_api_key", "codex"),
                True,
                True,
                "credential_missing",
            ),
            (
                "subscription_not_stored",
                "claude",
                "own_subscription",
                ("anthropic_api_key",),
                True,
                True,
                "credential_missing",
            ),
            (
                "subscription_flag_off",
                "claude",
                "own_subscription",
                ("claude_subscription",),
                False,
                True,
                "not_available",
            ),
            (
                "chatgpt_account_not_connected",
                "codex",
                "own_subscription",
                ("openai_api_key",),
                True,
                True,
                "credential_missing",
            ),
            ("chatgpt_flag_off", "codex", "own_subscription", ("codex",), False, True, "not_available"),
            ("key_without_a_user", "claude", "own_key", ("anthropic_api_key",), True, False, "no_user"),
            (
                "subscription_without_a_user",
                "claude",
                "own_subscription",
                ("claude_subscription",),
                True,
                False,
                "no_user",
            ),
        ]
    )
    def test_an_explicit_mode_that_cannot_be_used_is_refused(
        self, _name: str, adapter: str, requested: str, stored: tuple[str, ...], flags: bool, with_user: bool, code: str
    ) -> None:
        with self.assertRaises(inference.InferenceUnavailable) as raised:
            self._resolve(
                adapter=adapter, requested=requested, stored=stored, flags=flags, user=self.user if with_user else None
            )

        assert raised.exception.code == code
        assert raised.exception.detail
        assert "sk-fake" not in raised.exception.detail

    @parameterized.expand([("no_user", False), ("user_of_another_organization", True)])
    def test_auto_without_a_team_member_uses_posthog(self, _name: str, outsider: bool) -> None:
        user = None
        if outsider:
            user = User.objects.create_user(email="outsider@example.com", password=None, first_name="Outsider")
            self._store(user, "anthropic_api_key")

        decision = self._resolve(adapter="claude", requested="auto", stored=(), flags=True, user=user)

        assert (decision.mode, dict(decision.run_state_updates), decision.resolved_from_auto) == ("posthog", {}, True)

    @parameterized.expand(
        [
            ("the_selected_key", OWN_KEY_CLAUDE, "anthropic_api_key", True, "sk-fake-anthropic_api_key"),
            (
                "the_stored_subscription",
                SUBSCRIPTION_CLAUDE,
                "claude_subscription",
                True,
                "sk-fake-claude_subscription",
            ),
            ("another_kind_than_the_run_selected", OWN_KEY_CLAUDE, "claude_subscription", True, None),
            ("a_gateway_run", {}, "anthropic_api_key", True, None),
            (
                "a_relayed_subscription_run",
                {"claude_model_access": "own-subscription"},
                "claude_subscription",
                True,
                None,
            ),
            ("a_subscription_with_the_flag_off", SUBSCRIPTION_CLAUDE, "claude_subscription", False, "missing"),
        ]
    )
    def test_a_run_gets_only_the_credential_its_state_selects(
        self, _name: str, state: dict[str, Any], credential: str, flag: bool, expected: str | None
    ) -> None:
        self._store(self.user, "anthropic_api_key")
        self._store(self.user, "claude_subscription")
        run_state = {**state, "claude_subscription_user_id": self.user.id}

        with patch(f"{MODULE}.claude_subscription_storage_enabled", return_value=flag):
            if expected == "missing":
                with self.assertRaises(inference.InferenceCredentialMissing):
                    issue_run_inference_credential(run_state, team_id=self.team.id, credential=credential)  # type: ignore[arg-type]
                return
            grant = issue_run_inference_credential(run_state, team_id=self.team.id, credential=credential)  # type: ignore[arg-type]

        assert (grant.secret if grant else None) == expected
        if grant is not None:
            assert grant.secret not in repr(grant)

    def test_a_run_never_gets_the_credential_of_a_user_who_is_not_its_owner(self) -> None:
        other = User.objects.create_and_join(self.organization, "other@example.com", "password")
        self._store(self.user, "anthropic_api_key")

        with self.assertRaises(inference.InferenceCredentialMissing):
            issue_run_inference_credential(
                {**OWN_KEY_CLAUDE, "claude_subscription_user_id": other.id},
                team_id=self.team.id,
                credential="anthropic_api_key",
            )


class TestValidatedInferenceState(SimpleTestCase):
    @parameterized.expand(
        [
            ("none", None, "posthog-gateway", "posthog-gateway", "relay"),
            ("posthog", {}, "posthog-gateway", "posthog-gateway", "relay"),
            ("own_key", OWN_KEY_CLAUDE, "own-key", "posthog-gateway", "relay"),
            ("stored_subscription", SUBSCRIPTION_CLAUDE, "own-subscription", "posthog-gateway", "server"),
            ("codex", SUBSCRIPTION_CODEX, "posthog-gateway", "own-subscription", "relay"),
        ]
    )
    def test_every_inference_key_gets_a_value(
        self, _name: str, updates: dict[str, Any] | None, claude: str, codex: str, source: str
    ) -> None:
        assert validated_inference_state(updates) == {
            "claude_model_access": claude,
            "codex_model_access": codex,
            "claude_subscription_source": source,
        }

    @parameterized.expand(
        [
            ("owner_key", {"claude_subscription_user_id": 1}),
            ("unrelated_key", {"sandbox_size": "16x64"}),
            ("unknown_access", {"claude_model_access": "free"}),
            ("unknown_source", {"claude_subscription_source": "desktop"}),
        ]
    )
    def test_other_keys_and_unknown_values_are_refused(self, _name: str, updates: dict[str, Any]) -> None:
        with self.assertRaises(InvalidInferenceState):
            validated_inference_state(updates)
