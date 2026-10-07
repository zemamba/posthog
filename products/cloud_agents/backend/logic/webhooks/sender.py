"""Send one signed webhook request to a customer URL.

The URL never reaches an error, a log line or a metric label. A failure names a status code or an
exception class only, because the text of a `requests` error holds the whole URL.
"""

from __future__ import annotations

import time
from typing import Final

import requests

from posthog.dataclasses import frozen
from posthog.security.pinned_requests import SSRFBlockedError, pinned_session

from ...facade.enums import WebhookEvent
from .signing import SIGNATURE_VERSION, sign

CONNECT_TIMEOUT_SECONDS: Final = 3.0
READ_TIMEOUT_SECONDS: Final = 5.0
USER_AGENT: Final = "PostHog-CloudAgents-Webhooks/1"


@frozen
class SendResult:
    """`status_code` is None when no response arrived. `error_class` then names the exception class."""

    status_code: int | None
    error_class: str | None
    # Seconds from a `Retry-After` response header, when the receiver sent one.
    retry_after: int | None = None
    # The URL points to an address PostHog does not send to. A retry cannot succeed.
    blocked: bool = False


def _parse_retry_after(value: str | None) -> int | None:
    if value is None or not value.strip().isdigit():
        return None
    return int(value.strip())


def post_signed(url: str, secret: str, event_id: str, event_type: WebhookEvent, body: bytes) -> SendResult:
    timestamp = int(time.time())
    headers = {
        "Content-Type": "application/json",
        "User-Agent": USER_AGENT,
        "X-PostHog-Webhook-Id": event_id,
        "X-PostHog-Webhook-Timestamp": str(timestamp),
        "X-PostHog-Webhook-Signature": f"{SIGNATURE_VERSION}={sign(secret, timestamp, body)}",
        "X-PostHog-Webhook-Event": WebhookEvent(event_type).value,
    }
    try:
        # The customer owns this URL, so the call has no posthog/egress domain. The caller honors
        # 429 and Retry-After. `pinned_session` validates the URL and connects to the IPs that it
        # validated, which closes the window where DNS changes between the check and the connection.
        with pinned_session(url) as session:
            request = session.prepare_request(requests.Request("POST", url, data=body, headers=headers))
            settings = session.merge_environment_settings(request.url, {}, True, None, None)
            # The adapter and not `session.send`, with `stream=True` and no read. The session reads
            # the whole body of a redirect to find its target, so a receiver that answers 3xx with
            # an unbounded body would fill the memory of the worker. The adapter follows nothing.
            response = session.get_adapter(request.url or url).send(
                request,
                stream=True,
                timeout=(CONNECT_TIMEOUT_SECONDS, READ_TIMEOUT_SECONDS),
                verify=True if settings["verify"] is None else settings["verify"],
                cert=settings["cert"],
                proxies=settings["proxies"],
            )
            status_code = response.status_code
            retry_after = _parse_retry_after(response.headers.get("Retry-After"))
            response.close()
    except SSRFBlockedError:
        return SendResult(status_code=None, error_class=SSRFBlockedError.__name__, blocked=True)
    except requests.RequestException as error:
        return SendResult(status_code=None, error_class=type(error).__name__)
    return SendResult(status_code=status_code, error_class=None, retry_after=retry_after)
