from collections.abc import Mapping
from typing import Literal, get_args

from posthog.dataclasses import frozen

ModelAccessMode = Literal["posthog-gateway", "own-subscription", "own-key"]
OwnModelAccessMode = Literal["own-subscription", "own-key"]
SubscriptionAdapter = Literal["claude", "codex"]
ClaudeSubscriptionSource = Literal["relay", "server"]
InferenceBilling = Literal["posthog", "own_key", "own_subscription"]
# The credential a run needs for its model calls. `codex` is the connected ChatGPT account. The
# other three are the kinds of `InferenceCredentialStore`.
RunCredentialKind = Literal["anthropic_api_key", "openai_api_key", "claude_subscription", "codex"]
ServerHeldCredentialKind = Literal["anthropic_api_key", "openai_api_key", "claude_subscription"]

OWN_MODEL_ACCESS_MODES: frozenset[str] = frozenset(get_args(OwnModelAccessMode))
CLAUDE_SUBSCRIPTION_SOURCE_STATE_KEY = "claude_subscription_source"
# The run state keys that select who pays for model use. A server-side caller stamps them. The
# owner key `{adapter}_subscription_user_id` is not in this set, because run creation stamps it.
INFERENCE_STATE_KEYS: frozenset[str] = frozenset(
    {"claude_model_access", "codex_model_access", CLAUDE_SUBSCRIPTION_SOURCE_STATE_KEY}
)

_OWN_KEY_CREDENTIAL_KINDS: dict[SubscriptionAdapter, ServerHeldCredentialKind] = {
    "claude": "anthropic_api_key",
    "codex": "openai_api_key",
}


@frozen
class ModelAccess:
    """Who pays for a run's model use: PostHog, or the owner's plan or API key for one adapter."""

    adapter: SubscriptionAdapter | None = None
    # The user whose plan or API key the run uses. Stored as `{adapter}_subscription_user_id` for
    # both own modes.
    owner_id: int | None = None
    own_mode: OwnModelAccessMode = "own-subscription"
    # Where a Claude plan token comes from: the client that answers the run's credential request,
    # or the token that the server stores for the owner.
    claude_subscription_source: ClaudeSubscriptionSource = "relay"

    @property
    def kind(self) -> ModelAccessMode:
        return "posthog-gateway" if self.adapter is None else self.own_mode

    def access_for(self, adapter: SubscriptionAdapter) -> ModelAccessMode:
        return self.own_mode if adapter == self.adapter else "posthog-gateway"

    @property
    def billing(self) -> InferenceBilling:
        if self.adapter is None:
            return "posthog"
        return "own_key" if self.own_mode == "own-key" else "own_subscription"

    @property
    def credential_kind(self) -> RunCredentialKind | None:
        """The credential that the server must hold for the run. None for a gateway run and for a
        relayed Claude plan token, which the server never holds."""
        if self.adapter is None:
            return None
        if self.own_mode == "own-key":
            return _OWN_KEY_CREDENTIAL_KINDS[self.adapter]
        if self.adapter == "codex":
            return "codex"
        return "claude_subscription" if self.claude_subscription_source == "server" else None

    @property
    def server_held_credential_kind(self) -> ServerHeldCredentialKind | None:
        kind = self.credential_kind
        return None if kind is None or kind == "codex" else kind


class InvalidModelAccess(ValueError):
    pass


def resolve_model_access(state: Mapping[str, object]) -> ModelAccess:
    modes: dict[SubscriptionAdapter, OwnModelAccessMode] = {}
    for candidate in get_args(SubscriptionAdapter):
        value = state.get(f"{candidate}_model_access")
        if value == "own-subscription" or value == "own-key":
            modes[candidate] = value
    if len(modes) > 1:
        if "own-key" in modes.values():
            raise InvalidModelAccess("Select only one of your own model credentials for this run.")
        raise InvalidModelAccess("Select only one subscription for this run.")
    if not modes:
        return ModelAccess()
    adapter, own_mode = next(iter(modes.items()))
    if (state.get("runtime_adapter") or "claude") != adapter:
        credential = "API key" if own_mode == "own-key" else "subscription"
        raise InvalidModelAccess(f"The {adapter} {credential} requires the {adapter} runtime.")
    owner = state.get(f"{adapter}_subscription_user_id")
    server_source = (
        adapter == "claude"
        and own_mode == "own-subscription"
        and state.get(CLAUDE_SUBSCRIPTION_SOURCE_STATE_KEY) == "server"
    )
    return ModelAccess(
        adapter=adapter,
        owner_id=owner if isinstance(owner, int) and not isinstance(owner, bool) else None,
        own_mode=own_mode,
        claude_subscription_source="server" if server_source else "relay",
    )


def inference_billing_for_state(state: Mapping[str, object]) -> InferenceBilling:
    """Who pays for the model use of a run with this state.

    Raises ``InvalidModelAccess`` for a state that no run can have, such as two own credentials.
    """
    return resolve_model_access(state).billing
