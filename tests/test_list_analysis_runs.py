from datetime import datetime, timezone
from uuid import UUID

from app.application.analysis.list_analysis_runs import (
    InvalidAnalysisRunListQueryError,
    ListAnalysisRuns,
)
from app.application.analysis.run_store import InMemoryAnalysisRunStore
from app.domain.analysis_run import AnalysisRun
from app.domain.execution import ExecutionState


def make_run(created_at: datetime, state: ExecutionState) -> AnalysisRun:
    return AnalysisRun(
        id=UUID(created_at.strftime("%Y%m%d%H%M%S%f")[:32].ljust(32, "0")),
        created_at=created_at,
        state=state,
    )


def test_lists_runs_in_deterministic_descending_order():
    store = InMemoryAnalysisRunStore()
    older = make_run(datetime(2026, 9, 20, 8, tzinfo=timezone.utc), ExecutionState.COMPLETED)
    newer = make_run(datetime(2026, 9, 20, 9, tzinfo=timezone.utc), ExecutionState.FAILED)
    store.save(older)
    store.save(newer)

    view = ListAnalysisRuns(store).execute()

    assert [item.run_id for item in view.items] == [newer.id, older.id]
    assert view.next_cursor is None


def test_state_filter_is_applied_before_pagination():
    store = InMemoryAnalysisRunStore()
    completed_old = make_run(datetime(2026, 9, 20, 8, tzinfo=timezone.utc), ExecutionState.COMPLETED)
    failed_new = make_run(datetime(2026, 9, 20, 9, tzinfo=timezone.utc), ExecutionState.FAILED)
    completed_new = make_run(datetime(2026, 9, 20, 10, tzinfo=timezone.utc), ExecutionState.COMPLETED)
    for run in [completed_old, failed_new, completed_new]:
        store.save(run)

    view = ListAnalysisRuns(store).execute(
        state=ExecutionState.COMPLETED,
        page_size=1,
    )
    next_view = ListAnalysisRuns(store).execute(
        state=ExecutionState.COMPLETED,
        page_size=1,
        cursor=view.next_cursor,
    )

    assert [item.run_id for item in view.items] == [completed_new.id]
    assert [item.run_id for item in next_view.items] == [completed_old.id]


def test_empty_query_returns_empty_collection():
    view = ListAnalysisRuns(InMemoryAnalysisRunStore()).execute()

    assert view.items == ()
    assert view.next_cursor is None


def test_cursor_is_opaque_and_bound_to_filter_and_page_size():
    store = InMemoryAnalysisRunStore()
    first = make_run(datetime(2026, 9, 20, 10, tzinfo=timezone.utc), ExecutionState.COMPLETED)
    second = make_run(datetime(2026, 9, 20, 9, tzinfo=timezone.utc), ExecutionState.COMPLETED)
    store.save(first)
    store.save(second)

    capability = ListAnalysisRuns(store)
    view = capability.execute(state=ExecutionState.COMPLETED, page_size=1)

    assert view.next_cursor is not None
    assert "2026" not in view.next_cursor

    try:
        capability.execute(state=ExecutionState.FAILED, page_size=1, cursor=view.next_cursor)
    except InvalidAnalysisRunListQueryError:
        pass
    else:
        raise AssertionError("Expected filter-bound cursor rejection")

    try:
        capability.execute(state=ExecutionState.COMPLETED, page_size=2, cursor=view.next_cursor)
    except InvalidAnalysisRunListQueryError:
        pass
    else:
        raise AssertionError("Expected page-size-bound cursor rejection")


def test_malformed_cursor_is_rejected():
    store = InMemoryAnalysisRunStore()
    run = make_run(datetime(2026, 9, 20, 10, tzinfo=timezone.utc), ExecutionState.COMPLETED)
    store.save(run)

    try:
        ListAnalysisRuns(store).execute(cursor="invalid")
    except InvalidAnalysisRunListQueryError:
        pass
    else:
        raise AssertionError("Expected malformed cursor rejection")


def test_page_size_is_bounded():
    capability = ListAnalysisRuns(InMemoryAnalysisRunStore())

    for value in [0, 101]:
        try:
            capability.execute(page_size=value)
        except InvalidAnalysisRunListQueryError:
            continue
        raise AssertionError("Expected page-size validation")
