"""The live event stream of a run: the stream of its current Tasks run, after one frame with the run facts."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import cast
from uuid import UUID

from products.tasks.backend.facade.cloud_agents import get_cloud_agent_task_run
from products.tasks.backend.facade.streams import (
    TaskRunSseStream,
    format_sse_event,
    prepare_task_run_sse_stream,
    task_run_sse_stream,
)

from ..facade.contracts import RunEventStream, RunNotFound, RunNotReady
from .run_rows import get_run_row, to_run_dto

RUN_EVENT_NAME = "run"


def prepare_run_event_stream(
    team_id: int, run_id: UUID, *, last_event_id: str | None, start_latest: bool
) -> RunEventStream:
    """Resolve the run for streaming. It does the database reads, so call it on the request thread."""
    run = get_run_row(team_id, run_id)
    if run.current_task_run_id is None or run.task_id is None:
        raise RunNotReady()
    # The stream helper has no origin check, so the run is resolved as a Cloud Agents run first.
    if get_cloud_agent_task_run(team_id=team_id, run_id=run.current_task_run_id) is None:
        raise RunNotFound()
    source = prepare_task_run_sse_stream(
        run.current_task_run_id, run.task_id, team_id, last_event_id=last_event_id, start_latest=start_latest
    )
    if source is None:
        raise RunNotFound()
    return RunEventStream(run=to_run_dto(run), source=source)


async def run_event_stream(stream: RunEventStream) -> AsyncGenerator[bytes]:
    """The response body. The first frame tells the client the run and its status when the connection opened."""
    run = stream.run
    yield format_sse_event(
        {
            "id": str(run.id),
            "status": run.status.value,
            "stop_reason": run.stop_reason.value if run.stop_reason else None,
        },
        event_name=RUN_EVENT_NAME,
    )
    async for frame in task_run_sse_stream(cast(TaskRunSseStream, stream.source)):
        yield frame
