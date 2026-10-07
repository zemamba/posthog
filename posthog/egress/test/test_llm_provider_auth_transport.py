from unittest.mock import patch

from django.test import SimpleTestCase

import requests
from prometheus_client import REGISTRY

from posthog.egress.llm_provider_auth import ANTHROPIC_MODELS_URL, llm_provider_auth_request

FAKE_KEY = "sk-ant-api03-not-a-real-key-0001"


def _samples() -> list:
    return [
        sample
        for metric in REGISTRY.collect()
        if metric.name.startswith("llm_provider_auth_api")
        for sample in metric.samples
    ]


def _request_count() -> float:
    labels = {"scope": "anthropic", "method": "GET", "endpoint": "v1/models", "status_code": "401", "source": "test"}
    return REGISTRY.get_sample_value("llm_provider_auth_api_requests_total", labels) or 0


class TestLLMProviderAuthTransport(SimpleTestCase):
    def test_request_is_recorded_under_the_provider_scope_without_the_key(self) -> None:
        response = requests.Response()
        response.status_code = 401
        before = _request_count()

        with patch("requests.request", return_value=response) as request:
            llm_provider_auth_request(
                "GET",
                ANTHROPIC_MODELS_URL,
                provider="anthropic",
                source="test",
                endpoint="v1/models",
                headers={"x-api-key": FAKE_KEY},
                timeout=1.0,
            )

        assert request.call_args.kwargs["headers"]["x-api-key"] == FAKE_KEY
        assert request.call_args.kwargs["timeout"] == 1.0
        assert _request_count() == before + 1
        assert not any(FAKE_KEY in value for sample in _samples() for value in sample.labels.values())
