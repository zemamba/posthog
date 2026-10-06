"""Waits that a source can leave before they end.

A source that sleeps between retries, or until a rate limit resets, does not yield an item and does
not reach a safe point. The pipeline acts on a worker shutdown only at those two places, so the
sleep holds the worker for its whole length, and a retry loop repeats that for hours.

`interruptible_sleep` replaces `time.sleep` in a retry or rate-limit wait. The wait time is the
same. The differences are:

- When the worker starts to shut down, the wait reaches a safe point, if the caller declared with
  `safe_point_during_waits` that the wait is one. A resumable run then hands off at once.
- When the pipeline no longer reads the source, the wait raises `SourceAbandonedError`, so the
  thread of the source ends and stops its requests.

Outside an import the function is `time.sleep`.
"""

import time
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar

from products.warehouse_sources.backend.temporal.data_imports.pipelines.core.abandonable_iterate import (
    SourceAbandonedError,
)
from products.warehouse_sources.backend.temporal.data_imports.sources.common.progress import RETRY_WAIT, note_progress
from products.warehouse_sources.backend.temporal.data_imports.sources.common.safe_point import reach_safe_point


class SourceWaitSignals:
    """What the pipeline tells the waits of one source."""

    def __init__(self) -> None:
        self._shutdown = threading.Event()
        self._abandoned = threading.Event()

    def notify_shutdown(self) -> None:
        self._shutdown.set()

    def notify_abandoned(self) -> None:
        self._abandoned.set()
        # A wait that has not seen the shutdown yet waits on this event.
        self._shutdown.set()

    @property
    def is_abandoned(self) -> bool:
        return self._abandoned.is_set()

    def sleep(self, seconds: float, safe_point: Callable[[], None] | None) -> None:
        deadline = time.monotonic() + seconds
        if self._shutdown.wait(max(seconds, 0.0)):
            self._raise_if_abandoned()
            if safe_point is not None:
                safe_point()
            # The shutdown event stays set, so the rest of the wait can end early only when the
            # pipeline abandons the source.
            self._abandoned.wait(max(deadline - time.monotonic(), 0.0))
            self._raise_if_abandoned()

    def _raise_if_abandoned(self) -> None:
        if self._abandoned.is_set():
            raise SourceAbandonedError("The pipeline no longer reads this source, so its wait ends")


_active_signals: ContextVar[SourceWaitSignals | None] = ContextVar("warehouse_source_wait_signals", default=None)
_wait_safe_point: ContextVar[Callable[[], None] | None] = ContextVar("warehouse_source_wait_safe_point", default=None)


@contextmanager
def activate_wait_signals(signals: SourceWaitSignals) -> Iterator[None]:
    """Install `signals` for code that runs in this context, including source threads started in it."""
    token = _active_signals.set(signals)
    try:
        yield
    finally:
        _active_signals.reset(token)


@contextmanager
def safe_point_during_waits(safe_point: Callable[[], None] = reach_safe_point) -> Iterator[None]:
    """Declare that a wait inside this block is a safe point.

    Use it only around a call whose retry waits meet the rule for a safe point: every row the
    staged cursor covers was already yielded, and the source holds none of them in a local buffer.
    Do not keep the block open across a `yield`.
    """
    token = _wait_safe_point.set(safe_point)
    try:
        yield
    finally:
        _wait_safe_point.reset(token)


def interruptible_sleep(seconds: float) -> None:
    signals = _active_signals.get()
    if signals is None:
        time.sleep(seconds)
        return
    # A wait is a decision of the source, so the thread is not blocked in a call.
    note_progress(RETRY_WAIT)
    signals.sleep(seconds, _wait_safe_point.get())
