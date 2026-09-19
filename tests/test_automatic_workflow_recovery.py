from datetime import datetime, timezone
from unittest.mock import Mock
from uuid import uuid4

from app.application.execution.automatic_workflow_recovery import (
    AutomaticWorkflowRecovery,
)
from app.application.execution.scheduled_workflow_execution import (
    ScheduledWorkflowExecution,
)


def make_interrupted(occurrence_id: str):
    created = ScheduledWorkflowExecution.create(
        occurrence_id,
        datetime(2026, 9, 19, 7, 0, tzinfo=timezone.utc),
    )
    return created.start(
        datetime(2026, 9, 19, 7, 1, tzinfo=timezone.utc)
    ).interrupt(
        datetime(2026, 9, 19, 7, 2, tzinfo=timezone.utc)
    )


class FakeStore:
    def __init__(self, executions):
        self.executions = tuple(executions)

    def list_interrupted(self):
        return self.executions


def test_no_interrupted_executions_is_noop():
    recover = Mock()
    result = AutomaticWorkflowRecovery(
        recover,
        FakeStore([]),
    ).execute()

    assert result.attempted == ()
    assert result.recovered == ()
    assert result.failed == ()
    recover.execute.assert_not_called()


def test_recovery_uses_occurrence_date_and_preserves_identity():
    execution = make_interrupted(
        "00000000-0000-0000-0000-000000000001:2026-09-18:08:30:00"
    )
    recover = Mock()

    result = AutomaticWorkflowRecovery(
        recover,
        FakeStore([execution]),
    ).execute()

    assert result.attempted == (execution.id,)
    assert result.recovered == (execution.id,)
    assert result.failed == ()
    recover.execute.assert_called_once_with(
        execution.id,
        execution.created_at.date(),
    )


def test_multiple_recoveries_follow_store_order():
    first = make_interrupted(
        "00000000-0000-0000-0000-000000000001:2026-09-18:08:30:00"
    )
    second = make_interrupted(
        "00000000-0000-0000-0000-000000000002:2026-09-19:08:30:00"
    )
    recover = Mock()

    result = AutomaticWorkflowRecovery(
        recover,
        FakeStore([second, first]),
    ).execute()

    assert result.attempted == (second.id, first.id)
    assert result.recovered == (second.id, first.id)


def test_one_recovery_failure_does_not_block_later_recoveries():
    first = make_interrupted(
        "00000000-0000-0000-0000-000000000001:2026-09-18:08:30:00"
    )
    second = make_interrupted(
        "00000000-0000-0000-0000-000000000002:2026-09-19:08:30:00"
    )
    recover = Mock()
    recover.execute.side_effect = [RuntimeError("recovery failed"), second]

    result = AutomaticWorkflowRecovery(
        recover,
        FakeStore([first, second]),
    ).execute()

    assert result.attempted == (first.id, second.id)
    assert result.recovered == (second.id,)
    assert result.failed == (first.id,)


def test_repeated_startup_does_not_replay_terminal_execution():
    execution = make_interrupted(
        "00000000-0000-0000-0000-000000000001:2026-09-18:08:30:00"
    )
    recover = Mock()
    store = FakeStore([execution])

    first = AutomaticWorkflowRecovery(recover, store).execute()
    second = AutomaticWorkflowRecovery(recover, FakeStore([])).execute()

    assert first.recovered == (execution.id,)
    assert second.attempted == ()


def test_malformed_occurrence_date_isolated_as_failure():
    execution = make_interrupted(
        "00000000-0000-0000-0000-000000000001:not-a-date:08:30:00"
    )
    recover = Mock()

    result = AutomaticWorkflowRecovery(
        recover,
        FakeStore([execution]),
    ).execute()

    assert result.failed == (execution.id,)
    recover.execute.assert_not_called()


def test_each_attempt_is_independent():
    execution = make_interrupted(
        f"{uuid4()}:2026-09-19:08:30:00"
    )
    recover = Mock()

    AutomaticWorkflowRecovery(recover, FakeStore([execution])).execute()

    assert recover.execute.call_count == 1
