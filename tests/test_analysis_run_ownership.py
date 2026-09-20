from datetime import date
from uuid import UUID, uuid4
from unittest.mock import Mock

import pytest

from app.application.analysis.get_analysis_run import AnalysisRunNotFoundError, GetAnalysisRun
from app.application.analysis.list_analysis_runs import ListAnalysisRuns
from app.application.analysis.result_store import InMemoryAnalysisResultStore
from app.application.analysis.run_market_analysis import RunMarketAnalysis
from app.application.analysis.run_store import InMemoryAnalysisRunStore
from app.application.security.identity import AuthenticatedIdentity
from app.application.stocks.catalog import InMemoryStockCatalog
from app.domain.analysis_run import AnalysisRun
from app.domain.execution import ExecutionState
from app.domain.stocks.stock import Stock


AS_OF = date(2026, 9, 20)


def test_market_run_persists_user_owner():
    user_id = uuid4()
    stock = Stock.create("EGAL", "Egypt Aluminum")
    runner = RunMarketAnalysis(
        InMemoryStockCatalog([stock]),
        Mock(),
    )

    result = runner.execute(["EGAL"], AS_OF, owner_user_id=user_id)

    run = runner._analysis_run_store.get(result.analysis_run_id)
    assert run is not None
    assert run.owner_user_id == user_id


def test_user_can_read_own_run():
    user_id = uuid4()
    run = AnalysisRun.create(owner_user_id=user_id).with_state(ExecutionState.COMPLETED)
    store = InMemoryAnalysisRunStore()
    store.save(run)

    capability = GetAnalysisRun(store, InMemoryAnalysisResultStore())

    view = capability.execute(run.id, identity=AuthenticatedIdentity.user(user_id))

    assert view.run_id == run.id


def test_user_cannot_read_another_users_run():
    owner_id = uuid4()
    other_id = uuid4()
    run = AnalysisRun.create(owner_user_id=owner_id).with_state(ExecutionState.COMPLETED)
    store = InMemoryAnalysisRunStore()
    store.save(run)

    capability = GetAnalysisRun(store, InMemoryAnalysisResultStore())

    with pytest.raises(AnalysisRunNotFoundError):
        capability.execute(run.id, identity=AuthenticatedIdentity.user(other_id))


def test_operator_can_read_user_owned_run():
    run = AnalysisRun.create(owner_user_id=uuid4()).with_state(ExecutionState.COMPLETED)
    store = InMemoryAnalysisRunStore()
    store.save(run)

    view = GetAnalysisRun(
        store,
        InMemoryAnalysisResultStore(),
    ).execute(run.id, identity=AuthenticatedIdentity.operator())

    assert view.run_id == run.id


def test_user_list_is_scoped_to_owned_runs():
    owner_id = uuid4()
    other_id = uuid4()
    own = AnalysisRun.create(owner_user_id=owner_id)
    other = AnalysisRun.create(owner_user_id=other_id)
    global_run = AnalysisRun.create()
    store = InMemoryAnalysisRunStore()
    for run in (own, other, global_run):
        store.save(run)

    view = ListAnalysisRuns(store).execute(
        identity=AuthenticatedIdentity.user(owner_id),
    )

    assert [item.run_id for item in view.items] == [own.id]


def test_operator_list_includes_user_and_global_runs():
    own = AnalysisRun.create(owner_user_id=uuid4())
    global_run = AnalysisRun.create()
    store = InMemoryAnalysisRunStore()
    store.save(own)
    store.save(global_run)

    view = ListAnalysisRuns(store).execute(identity=AuthenticatedIdentity.operator())

    assert {item.run_id for item in view.items} == {own.id, global_run.id}


def test_legacy_global_run_is_not_visible_to_regular_user():
    run = AnalysisRun.create()
    store = InMemoryAnalysisRunStore()
    store.save(run)

    view = ListAnalysisRuns(store).execute(
        identity=AuthenticatedIdentity.user(uuid4()),
    )

    assert view.items == ()
