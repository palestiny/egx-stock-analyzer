from app.application.analysis.run_store import InMemoryAnalysisRunStore
from app.domain.analysis_run import AnalysisRun


def test_analysis_run_store_round_trip():
    store = InMemoryAnalysisRunStore()
    run = AnalysisRun.create()

    store.save(run)

    assert store.get(run.id) == run


def test_analysis_run_store_returns_none_for_unknown_run():
    store = InMemoryAnalysisRunStore()

    assert store.get(AnalysisRun.create().id) is None
