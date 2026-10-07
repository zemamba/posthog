"""Facade for the tasks behind the Cloud Agents public API.

The Cloud Agents product authorizes its own callers, then creates, resumes and reads its
tasks through this boundary. Every function here is scoped to the reserved ``cloud_agents``
origin and to the team.

The run-scoped functions of the general facade also work for these tasks:
``signal_task_run_user_message``, ``read_task_run_history`` and ``get_task_run_detail`` in
``facade/api.py``, and ``cancel_task_run`` in ``facade/cancellation.py``. They look a run up by
run id, task id and team id and do no visibility check, so an internal task is not hidden from
them. They also do no origin check: resolve the run with ``get_cloud_agent_task_run`` first.
"""

from products.tasks.backend.facade.contracts import CloudAgentTaskDTO
from products.tasks.backend.logic.services.cloud_agent_tasks import (
    CloudAgentRunNotResumable,
    CloudAgentTaskError,
    CloudAgentTaskInvalid,
    CloudAgentTaskNotFound,
    CloudAgentTaskOriginKeyConflict,
    TaskRunEnd,
    classify_task_run_end,
    count_active_cloud_agent_runs,
    create_cloud_agent_task,
    get_cloud_agent_task_run,
    list_cloud_agent_task_run_ids,
    resume_cloud_agent_task,
)

__all__ = [
    "CloudAgentRunNotResumable",
    "CloudAgentTaskDTO",
    "CloudAgentTaskError",
    "CloudAgentTaskInvalid",
    "CloudAgentTaskNotFound",
    "CloudAgentTaskOriginKeyConflict",
    "TaskRunEnd",
    "classify_task_run_end",
    "count_active_cloud_agent_runs",
    "create_cloud_agent_task",
    "get_cloud_agent_task_run",
    "list_cloud_agent_task_run_ids",
    "resume_cloud_agent_task",
]
