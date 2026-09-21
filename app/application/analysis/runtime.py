from dataclasses import dataclass

from app.application.analysis.get_market_opportunity_ranking import GetMarketOpportunityRanking
from app.application.analysis.automatic_analysis_retention import AutomaticAnalysisRetention
from app.application.analysis.delete_analysis_run import DeleteAnalysisRun
from app.application.analysis.delete_analysis_snapshot import DeleteAnalysisSnapshot
from app.application.analysis.purge_analysis_lifecycle import PurgeAnalysisLifecycle
from app.application.analysis.lifecycle_store import AnalysisLifecycleStore
from app.application.analysis.get_analysis_run import GetAnalysisRun
from app.application.analysis.list_analysis_runs import ListAnalysisRuns
from app.application.reporting.get_analysis_history import GetAnalysisHistory
from app.application.identity.get_management_audit import GetManagementAudit
from app.application.identity.get_user_audit_history import GetUserAuditHistory
from app.application.identity.management_audit import ManagementAuditStore
from app.application.analysis.input_assembler import AnalysisInputAssembler
from app.application.analysis.rank_market_opportunities import RankMarketOpportunities
from app.application.analysis.result_store import AnalysisResultStore
from app.application.analysis.run_configured_market_analysis import RunConfiguredMarketAnalysis
from app.application.reporting.compare_analysis_snapshots import CompareAnalysisSnapshots
from app.application.reporting.change_detection import DetectAnalysisChanges
from app.application.reporting.calculate_snapshot_performance import CalculateSnapshotPerformance
from app.application.analysis.run_market_analysis import RunMarketAnalysis
from app.application.analysis.run_store import AnalysisRunStore
from app.application.analysis.run_stock_analysis import RunStockAnalysis
from app.application.analysis.run_stock_analysis_by_symbol import RunStockAnalysisBySymbol
from app.application.execution.retry import RetryPolicy
from app.application.reporting.get_alert_candidate import GetAlertCandidate
from app.application.reporting.get_analysis_report import GetAnalysisReport
from app.application.stocks.catalog import StockCatalog


@dataclass(frozen=True)
class StockAnalysisRuntime:
    run_by_symbol: RunStockAnalysisBySymbol
    run_market_analysis: RunMarketAnalysis
    run_configured_market_analysis: RunConfiguredMarketAnalysis
    rank_market_opportunities: RankMarketOpportunities
    get_market_opportunity_ranking: GetMarketOpportunityRanking
    get_analysis_run: GetAnalysisRun
    list_analysis_runs: ListAnalysisRuns
    run_stock_analysis: RunStockAnalysis
    get_analysis_report: GetAnalysisReport
    get_analysis_history: GetAnalysisHistory
    compare_analysis_snapshots: CompareAnalysisSnapshots
    detect_analysis_changes: DetectAnalysisChanges
    calculate_snapshot_performance: CalculateSnapshotPerformance
    get_alert_candidate: GetAlertCandidate
    get_management_audit: GetManagementAudit | None
    get_user_audit_history: GetUserAuditHistory | None
    result_store: AnalysisResultStore
    delete_analysis_run: DeleteAnalysisRun | None = None
    delete_analysis_snapshot: DeleteAnalysisSnapshot | None = None
    purge_analysis_lifecycle: PurgeAnalysisLifecycle | None = None
    automatic_analysis_retention: AutomaticAnalysisRetention | None = None


def create_stock_analysis_runtime(
    stock_catalog: StockCatalog,
    input_assembler: AnalysisInputAssembler,
    result_store: AnalysisResultStore,
    retry_policy: RetryPolicy,
    management_audit_store: ManagementAuditStore | None = None,
    analysis_run_store: AnalysisRunStore | None = None,
    lifecycle_store: AnalysisLifecycleStore | None = None,
    automatic_retention_policy=None,
) -> StockAnalysisRuntime:
    run_stock_analysis = RunStockAnalysis(
        input_assembler=input_assembler,
        result_store=result_store,
        retry_policy=retry_policy,
    )
    if analysis_run_store is None:
        from app.application.analysis.run_store import InMemoryAnalysisRunStore

        analysis_run_store = InMemoryAnalysisRunStore()

    run_market_analysis = RunMarketAnalysis(
        stock_catalog=stock_catalog,
        run_stock_analysis=run_stock_analysis,
        analysis_run_store=analysis_run_store,
    )
    run_configured_market_analysis = RunConfiguredMarketAnalysis(
        stock_catalog=stock_catalog,
        run_market_analysis=run_market_analysis,
    )
    rank_market_opportunities = RankMarketOpportunities()
    get_analysis_run = GetAnalysisRun(
        run_store=analysis_run_store,
        result_store=result_store,
    )
    list_analysis_runs = ListAnalysisRuns(analysis_run_store)
    delete_analysis_run = (
        DeleteAnalysisRun(analysis_run_store, lifecycle_store)
        if lifecycle_store is not None
        else None
    )
    delete_analysis_snapshot = (
        DeleteAnalysisSnapshot(result_store, lifecycle_store)
        if lifecycle_store is not None
        else None
    )
    purge_analysis_lifecycle = (
        PurgeAnalysisLifecycle(lifecycle_store)
        if lifecycle_store is not None
        else None
    )
    automatic_analysis_retention = (
        AutomaticAnalysisRetention(lifecycle_store, automatic_retention_policy)
        if lifecycle_store is not None
        else None
    )
    get_market_opportunity_ranking = GetMarketOpportunityRanking(
        result_store=result_store,
        rank_market_opportunities=rank_market_opportunities,
    )
    run_by_symbol = RunStockAnalysisBySymbol(
        stock_catalog=stock_catalog,
        run_stock_analysis=run_stock_analysis,
    )
    get_analysis_history = GetAnalysisHistory(
        stock_catalog=stock_catalog,
        result_store=result_store,
    )
    compare_analysis_snapshots = CompareAnalysisSnapshots(
        stock_catalog=stock_catalog,
        result_store=result_store,
    )
    detect_analysis_changes = DetectAnalysisChanges(compare_analysis_snapshots)
    calculate_snapshot_performance = CalculateSnapshotPerformance(
        stock_catalog=stock_catalog,
        result_store=result_store,
    )
    get_analysis_report = GetAnalysisReport(
        stock_catalog=stock_catalog,
        result_store=result_store,
    )
    get_alert_candidate = GetAlertCandidate(
        stock_catalog=stock_catalog,
        result_store=result_store,
    )
    get_management_audit = (
        GetManagementAudit(management_audit_store)
        if management_audit_store is not None
        else None
    )
    get_user_audit_history = (
        GetUserAuditHistory(management_audit_store)
        if management_audit_store is not None
        else None
    )

    return StockAnalysisRuntime(
        run_by_symbol=run_by_symbol,
        run_market_analysis=run_market_analysis,
        run_configured_market_analysis=run_configured_market_analysis,
        rank_market_opportunities=rank_market_opportunities,
        get_market_opportunity_ranking=get_market_opportunity_ranking,
        get_analysis_run=get_analysis_run,
        list_analysis_runs=list_analysis_runs,
        delete_analysis_run=delete_analysis_run,
        delete_analysis_snapshot=delete_analysis_snapshot,
        purge_analysis_lifecycle=purge_analysis_lifecycle,
        automatic_analysis_retention=automatic_analysis_retention,
        run_stock_analysis=run_stock_analysis,
        get_analysis_report=get_analysis_report,
        get_analysis_history=get_analysis_history,
        compare_analysis_snapshots=compare_analysis_snapshots,
        detect_analysis_changes=detect_analysis_changes,
        calculate_snapshot_performance=calculate_snapshot_performance,
        get_alert_candidate=get_alert_candidate,
        get_management_audit=get_management_audit,
        get_user_audit_history=get_user_audit_history,
        result_store=result_store,
    )
