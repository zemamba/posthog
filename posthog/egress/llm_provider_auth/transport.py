"""Recorded transport for the calls that check a user's own LLM provider API key.

The credential belongs to the user's account at the provider, and PostHog sends one request when the
user saves a key. No PostHog process shares a budget for these calls, so they are recorded but not gated.
"""

from typing import Any, Literal

import requests

from posthog.egress.llm_provider_auth.observability import llm_provider_auth_egress
from posthog.egress.transport.transport import RecordedEgressClient

ANTHROPIC_MODELS_URL = "https://api.anthropic.com/v1/models"
ANTHROPIC_API_VERSION = "2023-06-01"
OPENAI_MODELS_URL = "https://api.openai.com/v1/models"


class LLMProviderAuthClient(RecordedEgressClient):
    observability = llm_provider_auth_egress

    def _standard_headers(self) -> dict[str, str]:
        return {"Accept": "application/json"}


_llm_provider_auth_client = LLMProviderAuthClient()


def llm_provider_auth_request(
    method: str,
    url: str,
    *,
    provider: Literal["anthropic", "openai"],
    source: str,
    endpoint: str,
    headers: dict[str, str],
    timeout: float | tuple[float, float] | None = None,
    session: requests.Session | None = None,
    **kwargs: Any,
) -> requests.Response:
    # The scope is the provider name. A scope built from the key would put a secret on a metric label.
    return _llm_provider_auth_client.request(
        method,
        url,
        source=source,
        scope=provider,
        endpoint=endpoint,
        headers=headers,
        timeout=timeout,
        session=session,
        **kwargs,
    )
