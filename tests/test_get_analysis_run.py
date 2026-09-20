from datetime import date
from uuid import uuid4

from app.application.analysis.get_analysis_run import (
    AnalysisRunNotFoundError,
    GetAnalysisRun,
    InvalidAnalysisRunQueryError,
)
from app.application.analysis.result_store import InMemoryAnalysisResultStore
from app.application.analysis.run_store import InMemoryAnalysisRunStore
from app.domain.analysis_run import AnalysisRun
from app.domain.execution import ExecutionState


def make_run(state: ExecutionState) -> AnalysisRun:
    return AnalysisRun.create().with_state(state)


def save_snapshot(store, run_id, symbol, analysis_date):
    store.save(
        symbol,
        object(),
        analysis_date=analysis_date,
        analysis_run_id=run_id,
    )


def test_completed_run_returns_correlated_snapshots_in_symbol_order():
    run_store = InMemoryAnalysisRunStore()
    result_store = InMemoryAnalysisResultStore()
    run = make_run(ExecutionState.COMPLETED)
    run_store.save(run)
    save_snapshot(result_store, run.id, "SVCE", date(2026, 9, 20))
    save_snapshot(result_store, run.id, "EGAL", date(2026, 9, 20))

    view = GetAnalysisRun(run_store, result_store).execute(run.id)

    assert view.run_id == run.id
    assert view.state is ExecutionState.COMPLETED
    assert [item.symbol for item in view.snapshots] == ["EGAL", "SVCE"]


def test_partial_run_returns_only_successful_correlated_snapshots():
    run_store = InMemoryAnalysisRunStore()
    result_store = InMemoryAnalysisResultStore()
    run = make_run(ExecutionState.COMPLETED_WITH_ERRORS)
    run_store.save(run)
    save_snapshot(result_store, run.id, "EGAL", date(2026, 9, 20))

    view = GetAnalysisRun(run_store, result_store).execute(run.id)

    assert view.state is ExecutionState.COMPLETED_WITH_ERRORS
    assert [item.symbol for item in view.snapshots] == ["EGAL"]


def test_all_failed_and_empty_runs_are_readable_without_snapshots():
    run_store = InMemoryAnalysisRunStore()
    result_store = InMemoryAnalysisResultStore()
    failed = make_run(ExecutionState.FAILED)
    empty = make_run(ExecutionState.COMPLETED)
    run_store.save(failed)
    run_store.save(empty)

    failed_view = GetAnalysisRun(run_store, result_store).execute(failed.id)
    empty_view = GetAnalysisRun(run_store, result_store).execute(empty.id)

    assert failed_view.snapshots == ()
    assert empty_view.snapshots == ()


def test_pagination_returns_bounded_pages_and_opaque_cursor():
    run_store = InMemoryAnalysisRunStore()
    result_store = InMemoryAnalysisResultStore()
    run = make_run(ExecutionState.COMPLETED)
    run_store.save(run)
    for symbol in ["EGAL", "IEEC", "SVCE"]:
        save_snapshot(result_store, run.id, symbol, date(2026, 9, 20))

    capability = GetAnalysisRun(run_store, result_store)
    first = capability.execute(run.id, page_size=2)

    assert [item.symbol for item in first.snapshots] == ["EGAL", "IEEC"]
    assert first.next_cursor is not None
    assert "EGAL" not in first.next_cursor
    assert "IEEC" not in first.next_cursor

    second = capability.execute(run.id, page_size=2, cursor=first.next_cursor)

    assert [item.symbol for item in second.snapshots] == ["SVCE"]
    assert second.next_cursor is None


def test_cursor_is_bound_to_run_and_page_size():
    run_store = InMemoryAnalysisRunStore()
    result_store = InMemoryAnalysisResultStore()
    run = make_run(ExecutionState.COMPLETED)
    run_store.save(run)
    save_snapshot(result_store, run.id, "EGAL", date(2026, 9, 20))
    save_snapshot(result_store, run.id, "IEEC", date(2026, 9, 20))

    capability = GetAnalysisRun(run_store, result_store)
    cursor = capability.execute(run.id, page_size=1).next_cursor

    other_run = make_run(ExecutionState.COMPLETED)
    run_store.save(other_run)

    try:
        capability.execute(other_run.id, page_size=1, cursor=cursor)
    except InvalidAnalysisRunQueryError as error:
        assert "cursor" in str(error)
    else:
        raise AssertionError("Expected invalid cursor")

    try:
        capability.execute(run.id, page_size=2, cursor=cursor)
    except InvalidAnalysisRunQueryError as error:
        assert "cursor" in str(error)
    else:
        raise AssertionError("Expected invalid cursor")


def test_missing_run_is_explicit():
    capability = GetAnalysisRun(
        InMemoryAnalysisRunStore(),
        InMemoryAnalysisResultStore(),
    )

    missing_id = uuid4()

    try:
        capability.execute(missing_id)
    except AnalysisRunNotFoundError:
        pass
    else:
        raise AssertionError("Expected AnalysisRunNotFoundError")


def test_page_size_is_bounded():
    run_store = InMemoryAnalysisRunStore()
    result_store = InMemoryAnalysisResultStore()
    run = make_run(ExecutionState.COMPLETED)
    run_store.save(run)

    for invalid in [0, 101]:
        try:
            GetAnalysisRun(run_store, result_store).execute(run.id, page_size=invalid)
        except InvalidAnalysisRunQueryError:
            continue
        raise AssertionError("Expected InvalidAnalysisRunQueryError")
