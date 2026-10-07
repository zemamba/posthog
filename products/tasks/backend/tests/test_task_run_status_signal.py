from collections.abc import Callable

from posthog.test.base import BaseTest
from unittest.mock import MagicMock, patch

from parameterized import parameterized

from products.tasks.backend.facade import api as facade
from products.tasks.backend.facade.task_run_signals import connect_task_run_status_changed, task_run_status_changed
from products.tasks.backend.models import Task, TaskRun


def _mark_completed(run: TaskRun) -> None:
    run.mark_completed(notify=False)


def _mark_failed(run: TaskRun) -> None:
    run.mark_failed("boom")


def _facade_update(run: TaskRun) -> None:
    facade.update_task_run(
        run.id, run.task_id, run.team_id, validated_data={"status": TaskRun.Status.CANCELLED}, caller_is_agent=True
    )


def _save_state_only(run: TaskRun) -> None:
    run.state = {"scratch": True}
    run.save(update_fields=["state", "updated_at"])


def _save_unchanged_status(run: TaskRun) -> None:
    run.save()


def _status_set_but_not_written(run: TaskRun) -> None:
    run.status = TaskRun.Status.COMPLETED
    run.save(update_fields=["state", "updated_at"])


def _refresh_then_save(run: TaskRun) -> None:
    TaskRun.objects.filter(id=run.id).update(status=TaskRun.Status.FAILED)
    run.refresh_from_db(fields=["status"])
    run.save(update_fields=["status", "updated_at"])


@patch("products.tasks.backend.models.TaskRun.publish_stream_state_event", MagicMock())
@patch("products.tasks.backend.facade.api.signal_workflow_completion", MagicMock())
class TestTaskRunStatusChanged(BaseTest):
    def _receiver(self) -> MagicMock:
        receiver = MagicMock()
        connect_task_run_status_changed(receiver, dispatch_uid="test_task_run_status_changed")
        self.addCleanup(task_run_status_changed.disconnect, sender=TaskRun, dispatch_uid="test_task_run_status_changed")
        return receiver

    def _task(self) -> Task:
        return Task.objects.create(
            team=self.team,
            title="t",
            description="d",
            origin_product=Task.OriginProduct.USER_CREATED,
            created_by=self.user,
        )

    def _loaded_run(self) -> TaskRun:
        created = TaskRun.objects.create(task=self._task(), team=self.team, status=TaskRun.Status.IN_PROGRESS)
        return TaskRun.objects.get(id=created.id)

    @parameterized.expand(
        [
            ("mark_completed", _mark_completed, TaskRun.Status.COMPLETED),
            ("mark_failed", _mark_failed, TaskRun.Status.FAILED),
            ("facade_update_task_run", _facade_update, TaskRun.Status.CANCELLED),
        ]
    )
    def test_status_change_is_sent_once_with_the_previous_status(
        self, _name: str, change: Callable[[TaskRun], None], expected_status: str
    ) -> None:
        run = self._loaded_run()
        receiver = self._receiver()

        change(run)

        assert receiver.call_count == 1
        assert receiver.call_args.kwargs["task_run"].id == run.id
        assert receiver.call_args.kwargs["task_run"].status == expected_status
        assert receiver.call_args.kwargs["previous_status"] == TaskRun.Status.IN_PROGRESS

    @parameterized.expand(
        [
            ("state_only_save", _save_state_only),
            ("full_save_with_the_same_status", _save_unchanged_status),
            ("status_set_but_left_out_of_update_fields", _status_set_but_not_written),
            ("status_reloaded_before_the_save", _refresh_then_save),
        ]
    )
    def test_save_that_does_not_change_the_stored_status_sends_nothing(
        self, _name: str, change: Callable[[TaskRun], None]
    ) -> None:
        run = self._loaded_run()
        receiver = self._receiver()

        change(run)

        receiver.assert_not_called()

    def test_first_insert_is_sent_with_no_previous_status(self) -> None:
        task = self._task()
        receiver = self._receiver()

        run = TaskRun.objects.create(task=task, team=self.team, status=TaskRun.Status.QUEUED)
        run.status = TaskRun.Status.IN_PROGRESS
        run.save(update_fields=["status", "updated_at"])

        assert [call.kwargs["previous_status"] for call in receiver.call_args_list] == [None, TaskRun.Status.QUEUED]

    def test_a_failing_receiver_does_not_fail_the_save(self) -> None:
        run = self._loaded_run()

        def failing_receiver(**kwargs: object) -> None:
            raise RuntimeError("boom")

        connect_task_run_status_changed(failing_receiver, dispatch_uid="test_task_run_status_changed")
        self.addCleanup(task_run_status_changed.disconnect, sender=TaskRun, dispatch_uid="test_task_run_status_changed")

        run.mark_completed(notify=False)

        assert TaskRun.objects.get(id=run.id).status == TaskRun.Status.COMPLETED
