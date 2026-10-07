"""Map the status of a Tasks run to the public status of a cloud agent run. Pure, no database."""

from __future__ import annotations

from typing import Final

from ..facade.enums import CloudAgentRunStatus, StopReason

TERMINAL_STATUSES: Final = frozenset(
    {CloudAgentRunStatus.COMPLETED, CloudAgentRunStatus.FAILED, CloudAgentRunStatus.CANCELLED}
)

_STATUS_BY_TASK_RUN_STATUS: Final[dict[str, CloudAgentRunStatus]] = {
    "not_started": CloudAgentRunStatus.QUEUED,
    "queued": CloudAgentRunStatus.QUEUED,
    "in_progress": CloudAgentRunStatus.RUNNING,
    "completed": CloudAgentRunStatus.COMPLETED,
    "failed": CloudAgentRunStatus.FAILED,
    "cancelled": CloudAgentRunStatus.CANCELLED,
}

_STOP_REASON_BY_RUN_END: Final[dict[str, StopReason]] = {
    "done": StopReason.DONE,
    "cancelled": StopReason.CANCELLED,
    "error": StopReason.ERROR,
    "timeout": StopReason.TIMEOUT,
    "usage_limit": StopReason.USAGE_LIMIT,
}

# The error text of a Tasks run is written for the people who operate Tasks. It can hold an
# exception message or the name of another product, so the API shows one of these messages and
# never the Tasks text.
_ERROR_BY_STOP_REASON: Final[dict[StopReason, str]] = {
    StopReason.ERROR: "The run failed. Send a message to try again, or start a new run.",
    StopReason.TIMEOUT: "The run stopped because it reached its time limit. Send a message to continue.",
    StopReason.USAGE_LIMIT: (
        "The run stopped because this project reached its usage limit. "
        "Raise the limit in billing settings, then send a message to continue."
    ),
    StopReason.BUDGET_EXCEEDED: "The run stopped because it reached its cost limit.",
}

_STATUS_ORDER: Final[dict[CloudAgentRunStatus, int]] = {
    CloudAgentRunStatus.QUEUED: 0,
    CloudAgentRunStatus.RUNNING: 1,
    CloudAgentRunStatus.COMPLETED: 2,
    CloudAgentRunStatus.FAILED: 2,
    CloudAgentRunStatus.CANCELLED: 2,
}


def run_status_for(task_run_status: str) -> CloudAgentRunStatus:
    """The public status of a Tasks run status. Raises `ValueError` for a status that Tasks does not have."""
    try:
        return _STATUS_BY_TASK_RUN_STATUS[task_run_status]
    except KeyError:
        raise ValueError(f"Unknown task run status {task_run_status!r}") from None


def stop_reason_for(status: CloudAgentRunStatus, run_end: str | None) -> StopReason | None:
    """Why the run stopped. None while the run is active. `run_end` is the Tasks class of the end."""
    if status not in TERMINAL_STATUSES:
        return None
    if run_end is None:
        raise ValueError("A run that ended needs its end class")
    try:
        return _STOP_REASON_BY_RUN_END[run_end]
    except KeyError:
        raise ValueError(f"Unknown run end {run_end!r}") from None


def error_message_for(stop_reason: StopReason | None) -> str | None:
    """The message the API shows for a stop reason. None for a run that is active, done or cancelled."""
    return _ERROR_BY_STOP_REASON.get(stop_reason) if stop_reason is not None else None


def is_terminal(status: CloudAgentRunStatus | str) -> bool:
    return CloudAgentRunStatus(status) in TERMINAL_STATUSES


def moves_forward(current: CloudAgentRunStatus | str, new: CloudAgentRunStatus | str) -> bool:
    """False when `new` is an earlier stage than `current`, which is what a late read gives."""
    return _STATUS_ORDER[CloudAgentRunStatus(new)] >= _STATUS_ORDER[CloudAgentRunStatus(current)]
