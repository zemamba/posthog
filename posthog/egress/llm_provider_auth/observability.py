"""LLM provider key check outbound request telemetry.

The key check reads only the status code, so this domain parses no rate-limit header and declares no gauges.
"""

from prometheus_client import Counter

from posthog.egress.observability.observability import EgressMetrics, EgressObservability

llm_provider_auth_egress = EgressObservability(
    EgressMetrics(
        request_counter=Counter(
            "llm_provider_auth_api_requests",
            "Outbound requests that check a user's own LLM provider API key.",
            labelnames=["scope", "method", "endpoint", "status_code", "source"],
        ),
    )
)
