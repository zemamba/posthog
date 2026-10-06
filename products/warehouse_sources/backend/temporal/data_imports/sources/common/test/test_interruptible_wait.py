import threading
import contextvars
from collections.abc import Callable
from typing import Any

import pytest
from unittest.mock import MagicMock, patch

from requests import Response

from products.warehouse_sources.backend.temporal.data_imports.pipelines.core.abandonable_iterate import (
    SourceAbandonedError,
)
from products.warehouse_sources.backend.temporal.data_imports.sources.common.interruptible_wait import (
    SourceWaitSignals,
    activate_wait_signals,
    interruptible_sleep,
    safe_point_during_waits,
)
from products.warehouse_sources.backend.temporal.data_imports.sources.common.progress import (
    RETRY_WAIT,
    SAFE_POINT,
    ImportProgress,
    activate_import_progress,
)
from products.warehouse_sources.backend.temporal.data_imports.sources.common.rest_source.paginators import (
    JSONResponseCursorPaginator,
)
from products.warehouse_sources.backend.temporal.data_imports.sources.common.rest_source.rest_client import RESTClient
from products.warehouse_sources.backend.temporal.data_imports.sources.common.safe_point import activate_safe_point

# Long enough that a wait which nothing interrupts fails the test on its join timeout.
LONG_WAIT_SECONDS = 60.0
JOIN_TIMEOUT_SECONDS = 5.0


class _HandOff(Exception):
    pass


def _raise_hand_off() -> None:
    raise _HandOff()


class _SourceThread:
    """Runs `work` the way the pipeline runs a source: on a thread that copied the caller's context."""

    def __init__(self, work: Callable[[], Any]) -> None:
        self.error: BaseException | None = None
        self._work = work
        self._thread = threading.Thread(target=contextvars.copy_context().run, args=(self._run,), daemon=True)
        self._thread.start()

    def _run(self) -> None:
        try:
            self._work()
        except BaseException as error:
            self.error = error

    def ended(self) -> bool:
        self._thread.join(JOIN_TIMEOUT_SECONDS)
        return not self._thread.is_alive()


def test_outside_an_import_the_wait_is_a_plain_sleep() -> None:
    with patch("time.sleep") as sleep:
        interruptible_sleep(12.5)

    sleep.assert_called_once_with(12.5)


@pytest.mark.parametrize(
    "declared_safe_point,expected_error",
    [
        pytest.param(True, _HandOff, id="wait_is_a_safe_point"),
        # Without the declaration the cursor can cover rows the source still holds, so the wait
        # must not hand off. It ends only when the pipeline leaves the source.
        pytest.param(False, SourceAbandonedError, id="wait_is_not_a_safe_point"),
    ],
)
def test_a_wait_hands_off_at_shutdown_only_where_it_is_a_safe_point(
    declared_safe_point: bool, expected_error: type[BaseException]
) -> None:
    signals = SourceWaitSignals()
    progress = ImportProgress()
    waiting = threading.Event()

    def work() -> None:
        waiting.set()
        if declared_safe_point:
            with safe_point_during_waits():
                interruptible_sleep(LONG_WAIT_SECONDS)
        else:
            interruptible_sleep(LONG_WAIT_SECONDS)

    with (
        activate_import_progress(progress),
        activate_wait_signals(signals),
        activate_safe_point(_raise_hand_off, covers_framework_checkpoints=False),
    ):
        source = _SourceThread(work)
    assert waiting.wait(JOIN_TIMEOUT_SECONDS)

    signals.notify_shutdown()
    if not declared_safe_point:
        assert source.error is None
        signals.notify_abandoned()

    assert source.ended()
    assert isinstance(source.error, expected_error)
    # The source chose to wait, so the wait is not a blocked call.
    assert progress.snapshot().kind == (SAFE_POINT if declared_safe_point else RETRY_WAIT)


def _response(status_code: int, body: bytes, headers: dict[str, str] | None = None) -> Response:
    response = Response()
    response.status_code = status_code
    response._content = body
    response.headers.update(headers or {})
    response.url = "https://api.example.com/items"
    return response


_PAGE = _response(200, b'{"data": [{"id": 1}], "next": "cursor-2"}')
_RATE_LIMITED = _response(429, b"{}", {"Retry-After": "60"})


@pytest.mark.parametrize(
    "responses,pages_before_the_wait,expected_error",
    [
        pytest.param([_PAGE, _RATE_LIMITED], 1, _HandOff, id="rate_limited_after_a_page"),
        # The caller can stage a cursor between two `paginate` calls, so the first request of a
        # call is not at a framework safe point.
        pytest.param([_RATE_LIMITED], 0, SourceAbandonedError, id="rate_limited_on_the_first_request"),
    ],
)
def test_a_rest_client_retry_wait_hands_off_at_shutdown_after_a_framework_safe_point(
    responses: list[Response], pages_before_the_wait: int, expected_error: type[BaseException]
) -> None:
    session = MagicMock()
    session.prepare_request.side_effect = lambda request: MagicMock(url=request.url)
    remaining = list(responses)
    in_retry_wait = threading.Event()

    def send(*args: Any, **kwargs: Any) -> Response:
        response = remaining.pop(0)
        if not remaining:
            in_retry_wait.set()
            remaining.append(response)
        return response

    session.send.side_effect = send
    client = RESTClient(base_url="https://api.example.com", session=session)
    signals = SourceWaitSignals()
    pages: list[Any] = []
    shutting_down = threading.Event()

    def hand_off_when_shutting_down() -> None:
        if shutting_down.is_set():
            raise _HandOff()

    def work() -> None:
        paginator = JSONResponseCursorPaginator(cursor_path="next", cursor_param="cursor")
        for page in client.paginate("/items", paginator=paginator, data_selector="data"):
            pages.append(page)

    with (
        activate_wait_signals(signals),
        activate_safe_point(hand_off_when_shutting_down, covers_framework_checkpoints=True),
    ):
        source = _SourceThread(work)
    assert in_retry_wait.wait(JOIN_TIMEOUT_SECONDS)

    shutting_down.set()
    signals.notify_shutdown()
    if expected_error is SourceAbandonedError:
        signals.notify_abandoned()

    assert source.ended()
    assert isinstance(source.error, expected_error)
    assert len(pages) == pages_before_the_wait
