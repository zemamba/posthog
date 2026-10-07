from django.test import SimpleTestCase

from parameterized import parameterized

from products.cloud_agents.backend.logic.webhooks.signing import generate_secret, sign, verify

BODY = b'{"id":"evt_1","type":"run.completed"}'
TIMESTAMP = 1767225600


class TestWebhookSigning(SimpleTestCase):
    def test_round_trip(self) -> None:
        secret = generate_secret()
        assert secret.startswith("whsec_")
        signature = sign(secret, TIMESTAMP, BODY)
        assert verify(secret, TIMESTAMP, BODY, signature)
        assert verify(secret, str(TIMESTAMP), BODY, f"v1={signature}")

    @parameterized.expand(
        [
            ("body", {"body": BODY + b" "}),
            ("timestamp", {"timestamp": TIMESTAMP + 1}),
            ("secret", {"secret": "whsec_other"}),
            ("signature", {"signature": "0" * 64}),
        ]
    )
    def test_tamper_fails(self, _name: str, changed: dict) -> None:
        secret = "whsec_test"
        args = {"secret": secret, "timestamp": TIMESTAMP, "body": BODY, "signature": sign(secret, TIMESTAMP, BODY)}
        assert not verify(**{**args, **changed})
