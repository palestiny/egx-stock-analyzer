from dataclasses import dataclass

from app.application.analysis.get_market_opportunity_ranking import GetMarketOpportunityRanking
from app.application.analysis.input_assembler import AnalysisInputAssembler
from app.application.analysis.rank_market_opportunities import RankMarketOpportunities
from app.application.analysis.result_store import AnalysisResultStore
from app.application.analysis.run_configured_market_analysis import RunConfiguredMarketAnalysis
from app.application.analysis.run_market_analysis import RunMarketAnalysis
from app.application.analysis.run_configured_market_analysis import RunConfiguredMarketAnalysis
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
    run_configured_market_analysis: RunConfiguredMarketAnalysis
    rank_market_opportunities: RankMarketOpportunities
    get_market_opportunity_ranking: GetMarketOpportunityRanking
    run_stock_analysis: RunStockAnalysis
    get_analysis_report: GetAnalysisReport
    get_alert_candidate: GetAlertCandidate
    result_store: AnalysisResultStore


def create_stock_analysis_runtime(
    stock_catalog: StockCatalog,
    input_assembler: AnalysisInputAssembler,
    result_store: AnalysisResultStore,
    retry_policy: RetryPolicy,
) -> StockAnalysisRuntime:
    run_stock_analysis = RunStockAnalysis(
        input_assembler=input_assembler,
        result_store=result_store,
        retry_policy=retry_policy,
    )
    run_market_analysis = RunMarketAnalysis(
        stock_catalog=stock_catalog,
        run_stock_analysis=run_stock_analysis,
    )
    run_configured_market_analysis = RunConfiguredMarketAnalysis(
        stock_catalog=stock_catalog,
        run_market_analysis=run_market_analysis,
        run_configured_market_analysis=run_configured_market_analysis,
    )
    run_configured_market_analysis = RunConfiguredMarketAnalysis(
        stock_catalog=stock_catalog,
        run_market_analysis=run_market_analysis,
        run_configured_market_analysis=run_configured_market_analysis,
    )
    rank_market_opportunities = RankMarketOpportunities()
    get_market_opportunity_ranking = GetMarketOpportunityRanking(
        result_store=result_store,
        rank_market_opportunities=rank_market_opportunities,
    )
    run_by_symbol = RunStockAnalysisBySymbol(
        stock_catalog=stock_catalog,
        run_stock_analysis=run_stock_analysis,
    )
    get_analysis_report = GetAnalysisReport(
        stock_catalog=stock_catalog,
        result_store=result_store,
    )
    get_alert_candidate = GetAlertCandidate(
        stock_catalog=stock_catalog,
        result_store=result_store,
    )

    return StockAnalysisRuntime(
        run_by_symbol=run_by_symbol,
        run_market_analysis=run_market_analysis,
        rank_market_opportunities=rank_market_opportunities,
        get_market_opportunity_ranking=get_market_opportunity_ranking,
        run_stock_analysis=run_stock_analysis,
        get_analysis_report=get_analysis_report,
        get_alert_candidate=get_alert_candidate,
        result_store=result_store,
    )
