from app.application.security.identity import LEGACY_OPERATOR_USER_ID
from app.application.identity.user_store import UserStore
from app.domain.stocks.stock import Stock
from app.domain.identity.user import User, UserStatus
from app.application.stocks.catalog import InMemoryStockCatalog
from app.infrastructure.config import InfrastructureConfig
from app.infrastructure.runtime import create_infrastructure_runtime
from app.infrastructure.persistence.sqlite_user_store import SQLiteUserStore


class FakeYFinanceModule:
    pass


def test_infrastructure_runtime_composes_shared_sqlite_user_store(tmp_path):
    database_path = tmp_path / "analysis.db"

    runtime = create_infrastructure_runtime(
        stock_catalog=InMemoryStockCatalog(
            [Stock.create("EGAL", "Egypt Aluminum")]
        ),
        yfinance_module=FakeYFinanceModule(),
        config=InfrastructureConfig(
            operator_token="test-token",
            analysis_database_path=str(database_path),
        ),
    )

    assert isinstance(runtime.user_store, SQLiteUserStore)
    assert isinstance(runtime.user_store, UserStore)
    assert runtime.user_store.get(LEGACY_OPERATOR_USER_ID) == User(
        LEGACY_OPERATOR_USER_ID,
        UserStatus.ACTIVE,
    )

    runtime.close()


def test_legacy_operator_identity_materialization_is_idempotent(tmp_path):
    database_path = tmp_path / "analysis.db"
    config = InfrastructureConfig(
        operator_token="test-token",
        analysis_database_path=str(database_path),
    )

    first = create_infrastructure_runtime(
        stock_catalog=InMemoryStockCatalog(
            [Stock.create("EGAL", "Egypt Aluminum")]
        ),
        yfinance_module=FakeYFinanceModule(),
        config=config,
    )
    first.user_store.save(User(LEGACY_OPERATOR_USER_ID, UserStatus.DISABLED))
    first.close()

    second = create_infrastructure_runtime(
        stock_catalog=InMemoryStockCatalog(
            [Stock.create("EGAL", "Egypt Aluminum")]
        ),
        yfinance_module=FakeYFinanceModule(),
        config=config,
    )

    assert second.user_store.get(LEGACY_OPERATOR_USER_ID) == User(
        LEGACY_OPERATOR_USER_ID,
        UserStatus.DISABLED,
    )
    second.close()
