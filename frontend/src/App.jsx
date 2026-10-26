import { useEffect, useState } from "react";

import { getAlert, getAnalysisRuns, getAnalysisComparison, getAnalysisHistory, getCurrentIdentity, getMarketBreadthStress, getMarketOpportunities, getReport, getStockRegime, getTechnicalScanner, getScheduledWorkflowExecutions, getSnapshotPerformance, recoverScheduledWorkflowExecution, getUsers, createUser, updateUserStatus, rotateOwnCredential, rotateUserCredential, getManagementAudit, getUserAuditHistory, getScheduledWorkflowExecutionHistory, getAnalysisRun, getTechnicalIndicatorHistory, getNewsEvents } from "./api/analysisApi";
import { clearSessionToken, getSessionToken, setSessionToken } from "./auth/session";
import { UserAuditHistoryPanel } from "./components/UserAuditHistoryPanel";
import { AnalysisRunsPage } from "./components/AnalysisRunsPage";
import { ScheduledWorkflowHistoryPanel } from "./components/ScheduledWorkflowHistoryPanel";
import { AnalysisRunPanel } from "./components/AnalysisRunPanel";
import { TechnicalIndicatorPanel } from "./components/TechnicalIndicatorPanel";
import { NewsEventsPanel } from "./components/NewsEventsPanel";

function Metric({ label, value }) {
  return (
    <div className="metric">
      <span className="metric-label">{label}</span>
      <strong>{value ?? "—"}</strong>
    </div>
  );
}

function DetailPanel({ title, items }) {
  return (
    <section className="panel">
      <h3>{title}</h3>
      {items.map(([label, value]) => (
        <div className="detail-row" key={label}>
          <span>{label}</span>
          <strong>{value ?? "—"}</strong>
        </div>
      ))}
    </section>
  );
}

function DashboardApp({ onLogout, identity, onOpenAnalysisRuns }) {
  const [symbol, setSymbol] = useState("");
  const [report, setReport] = useState(null);
  const [indicatorHistory, setIndicatorHistory] = useState(null);
  const [indicatorError, setIndicatorError] = useState(null);
  const [indicatorLoading, setIndicatorLoading] = useState(false);
  const [newsEvents, setNewsEvents] = useState(null);
  const [newsError, setNewsError] = useState(null);
  const [newsLoading, setNewsLoading] = useState(false);
  const [alert, setAlert] = useState(null);
  const [history, setHistory] = useState(null);
  const [historyError, setHistoryError] = useState(null);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [beforeSnapshotId, setBeforeSnapshotId] = useState("");
  const [afterSnapshotId, setAfterSnapshotId] = useState("");
  const [comparison, setComparison] = useState(null);
  const [comparisonError, setComparisonError] = useState(null);
  const [comparisonLoading, setComparisonLoading] = useState(false);
  const [performance, setPerformance] = useState(null);
  const [performanceError, setPerformanceError] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [regime, setRegime] = useState(null);
  const [regimeError, setRegimeError] = useState(null);
  const [regimeLoading, setRegimeLoading] = useState(false);
  const [marketSymbols, setMarketSymbols] = useState("EGAL,IEEC,COMI");
  const [marketView, setMarketView] = useState(null);
  const [marketError, setMarketError] = useState(null);
  const [marketLoading, setMarketLoading] = useState(false);
  const [breadthSymbols, setBreadthSymbols] = useState("EGAL,IEEC,COMI");
  const [breadthView, setBreadthView] = useState(null);
  const [breadthError, setBreadthError] = useState(null);
  const [breadthLoading, setBreadthLoading] = useState(false);
  const [opportunityRegimes, setOpportunityRegimes] = useState({});
  const [opportunityRegimeErrors, setOpportunityRegimeErrors] = useState({});
  const [opportunityRegimeLoading, setOpportunityRegimeLoading] = useState({});
  const [scannerSymbols, setScannerSymbols] = useState("EGAL,IEEC,COMI");
  const [preBreakoutView, setPreBreakoutView] = useState(null);
  const [preBreakoutError, setPreBreakoutError] = useState(null);
  const [preBreakoutLoading, setPreBreakoutLoading] = useState(false);
  const [workflowOccurrenceId, setWorkflowOccurrenceId] = useState("");
  const [workflowExecutions, setWorkflowExecutions] = useState(null);
  const [workflowError, setWorkflowError] = useState(null);
  const [workflowLoading, setWorkflowLoading] = useState(false);
  const [recoveringWorkflowId, setRecoveringWorkflowId] = useState(null);
  const [workflowRecoveryErrors, setWorkflowRecoveryErrors] = useState({});
  const [users, setUsers] = useState(null);
  const [userAdminError, setUserAdminError] = useState(null);
  const [userAdminLoading, setUserAdminLoading] = useState(false);
  const [rotatedCredential, setRotatedCredential] = useState(null);
  const [credentialRotationError, setCredentialRotationError] = useState(null);
  const [auditFilters, setAuditFilters] = useState({ actorUserId: "", targetUserId: "", action: "", outcome: "", fromTime: "", toTime: "" });
  const [auditPage, setAuditPage] = useState(null);
  const [auditError, setAuditError] = useState(null);
  const [auditLoading, setAuditLoading] = useState(false);

  async function handleAnalyze(event) {
    event.preventDefault();
    const normalizedSymbol = symbol.trim().toUpperCase();

    if (!normalizedSymbol) {
      return;
    }

    setSymbol(normalizedSymbol);
    setLoading(true);
    setReport(null);
    setIndicatorHistory(null);
    setIndicatorError(null);
    setIndicatorLoading(true);
    setNewsEvents(null);
    setNewsError(null);
    setNewsLoading(true);
    setAlert(null);
    setHistory(null);
    setHistoryError(null);
    setHistoryLoading(true);
    setError(null);

    try {
      const reportResult = await getReport(normalizedSymbol);
      setReport(reportResult);

      try {
        setIndicatorHistory(await getTechnicalIndicatorHistory(normalizedSymbol));
      } catch (indicatorRequestError) {
        setIndicatorError(indicatorRequestError);
      } finally {
        setIndicatorLoading(false);
      }

      try {
        setNewsEvents(await getNewsEvents(normalizedSymbol));
      } catch (newsRequestError) {
        setNewsError(newsRequestError);
      } finally {
        setNewsLoading(false);
      }

      try {
        setAlert(await getAlert(normalizedSymbol));
      } catch (alertError) {
        if (alertError.status !== 404) {
          throw alertError;
        }
      }

      try {
        setHistory(await getAnalysisHistory(normalizedSymbol));
      } catch (historyRequestError) {
        setHistoryError(historyRequestError);
      } finally {
        setHistoryLoading(false);
      }
    } catch (requestError) {
      setError(requestError);
      setHistoryLoading(false);
      setIndicatorLoading(false);
      setNewsLoading(false);
    } finally {
      setLoading(false);
    }
  }


  async function handleStockRegime(event) {
    event.preventDefault();
    const normalizedSymbol = symbol.trim().toUpperCase();
    if (!normalizedSymbol) {
      setRegimeError(new Error("Enter a stock symbol first."));
      setRegime(null);
      return;
    }

    setRegimeLoading(true);
    setRegimeError(null);
    setRegime(null);
    try {
      setRegime(await getStockRegime(normalizedSymbol));
    } catch (requestError) {
      setRegimeError(requestError);
    } finally {
      setRegimeLoading(false);
    }
  }

  async function handleCompare(event) {
    event.preventDefault();
    if (!beforeSnapshotId || !afterSnapshotId) {
      return;
    }

    setComparisonLoading(true);
    setComparisonError(null);
    setPerformance(null);
    setPerformanceError(null);

    try {
      const [comparisonResult, performanceResult] = await Promise.all([
        getAnalysisComparison(symbol, beforeSnapshotId, afterSnapshotId),
        getSnapshotPerformance(symbol, beforeSnapshotId, afterSnapshotId),
      ]);
      setComparison(comparisonResult);
      setPerformance(performanceResult);
    } catch (requestError) {
      setComparison(null);
      setPerformance(null);
      setComparisonError(requestError);
      setPerformanceError(requestError);
    } finally {
      setComparisonLoading(false);
    }
  }


  async function handleMarketOpportunities(event) {
    event.preventDefault();
    const symbols = marketSymbols
      .split(",")
      .map((value) => value.trim().toUpperCase())
      .filter(Boolean);

    setMarketLoading(true);
    setMarketError(null);

    try {
      setMarketView(await getMarketOpportunities(symbols));
    } catch (requestError) {
      setMarketError(requestError);
      setMarketView(null);
    } finally {
      setMarketLoading(false);
    }
  }


  async function handleMarketBreadthStress(event) {
    event.preventDefault();
    const symbols = breadthSymbols
      .split(",")
      .map((value) => value.trim().toUpperCase())
      .filter(Boolean);
    if (symbols.length === 0) {
      setBreadthError(new Error("Enter at least one stock symbol."));
      setBreadthView(null);
      return;
    }

    setBreadthLoading(true);
    setBreadthError(null);
    try {
      setBreadthView(await getMarketBreadthStress(symbols));
    } catch (requestError) {
      setBreadthError(requestError);
      setBreadthView(null);
    } finally {
      setBreadthLoading(false);
    }
  }

  async function handleOpportunityRegime(rawSymbol) {
    const normalizedSymbol = rawSymbol.trim().toUpperCase();
    if (!normalizedSymbol) return;

    setOpportunityRegimeLoading((current) => ({ ...current, [normalizedSymbol]: true }));
    setOpportunityRegimeErrors((current) => ({ ...current, [normalizedSymbol]: null }));
    try {
      const profile = await getStockRegime(normalizedSymbol);
      setOpportunityRegimes((current) => ({ ...current, [normalizedSymbol]: profile }));
    } catch (requestError) {
      setOpportunityRegimeErrors((current) => ({
        ...current,
        [normalizedSymbol]: requestError,
      }));
    } finally {
      setOpportunityRegimeLoading((current) => ({ ...current, [normalizedSymbol]: false }));
    }
  }

  async function handlePreBreakoutScan(event) {
    event.preventDefault();
    const symbols = scannerSymbols
      .split(",")
      .map((value) => value.trim().toUpperCase())
      .filter(Boolean);
    if (symbols.length === 0) {
      setPreBreakoutView(null);
      setPreBreakoutError(new Error("Enter at least one stock symbol."));
      return;
    }

    setPreBreakoutLoading(true);
    setPreBreakoutError(null);
    try {
      setPreBreakoutView(await getTechnicalScanner(symbols, "pre-breakout-momentum-volume"));
    } catch (requestError) {
      setPreBreakoutView(null);
      setPreBreakoutError(requestError);
    } finally {
      setPreBreakoutLoading(false);
    }
  }


  async function handleWorkflowExecutions(event) {
    event.preventDefault();
    const occurrenceId = workflowOccurrenceId.trim();
    setWorkflowLoading(true);
    setWorkflowError(null);

    try {
      setWorkflowExecutions(await getScheduledWorkflowExecutions(occurrenceId || undefined));
    } catch (requestError) {
      setWorkflowExecutions(null);
      setWorkflowError(requestError);
    } finally {
      setWorkflowLoading(false);
    }
  }


  async function handleWorkflowRecovery(executionId) {
    setRecoveringWorkflowId(executionId);
    setWorkflowRecoveryErrors((current) => ({ ...current, [executionId]: null }));

    try {
      const recovered = await recoverScheduledWorkflowExecution(executionId);
      setWorkflowExecutions((current) => {
        if (!current) {
          return current;
        }
        return {
          ...current,
          items: current.items.map((item) => (
            item.id === executionId ? recovered : item
          )),
        };
      });
    } catch (requestError) {
      setWorkflowRecoveryErrors((current) => ({
        ...current,
        [executionId]: requestError,
      }));
    } finally {
      setRecoveringWorkflowId(null);
    }
  }

  async function handleUserAdministration() {
    setUserAdminLoading(true);
    setUserAdminError(null);
    try {
      setUsers(await getUsers());
    } catch (requestError) {
      setUsers(null);
      setUserAdminError(requestError);
    } finally {
      setUserAdminLoading(false);
    }
  }

  async function handleCreateUser() {
    setUserAdminLoading(true);
    setUserAdminError(null);
    try {
      const created = await createUser();
      setRotatedCredential(created.credential);
      setUsers(await getUsers());
    } catch (requestError) {
      setUserAdminError(requestError);
    } finally {
      setUserAdminLoading(false);
    }
  }

  async function handleUserCredentialRotation(userId) {
    setUserAdminLoading(true);
    setUserAdminError(null);
    try {
      const result = await rotateUserCredential(userId);
      setRotatedCredential(result.credential);
    } catch (requestError) {
      setUserAdminError(requestError);
    } finally {
      setUserAdminLoading(false);
    }
  }

  async function handleUserStatus(userId, status) {
    setUserAdminLoading(true);
    setUserAdminError(null);
    try {
      await updateUserStatus(userId, status);
      setUsers(await getUsers());
    } catch (requestError) {
      setUserAdminError(requestError);
    } finally {
      setUserAdminLoading(false);
    }
  }

  async function handleRotateOwnCredential() {
    setCredentialRotationError(null);
    setRotatedCredential(null);
    try {
      const result = await rotateOwnCredential();
      setRotatedCredential(result.credential);
    } catch (requestError) {
      setCredentialRotationError(requestError);
    }
  }

  async function handleManagementAudit(event, nextOffset = 0) {
    event?.preventDefault();
    setAuditLoading(true);
    setAuditError(null);
    try {
      setAuditPage(await getManagementAudit({ ...auditFilters, offset: nextOffset }));
    } catch (requestError) {
      setAuditPage(null);
      setAuditError(requestError);
    } finally {
      setAuditLoading(false);
    }
  }

  function updateAuditFilter(name, value) {
    setAuditFilters((current) => ({ ...current, [name]: value }));
  }

  function formatWorkflowTimestamp(value) {
    return new Date(value).toLocaleString();
  }

  return (
    <main className="app-shell">
      <header className="page-header">
        <div>
          <p className="eyebrow">EGX STOCK ANALYZER</p>
          <h1>Stock Analysis</h1>
          <p className="subtitle">
            Read the latest stored analysis for an EGX stock.
          </p>
          <button type="button" onClick={onOpenAnalysisRuns}>Analysis Runs</button>
          <button type="button" onClick={onLogout}>Log out</button>
        </div>

        <form className="symbol-form" onSubmit={handleAnalyze}>
          <label className="sr-only" htmlFor="stock-symbol">
            Stock Symbol
          </label>
          <input
            id="stock-symbol"
            name="stock-symbol"
            type="text"
            value={symbol}
            onChange={(event) => setSymbol(event.target.value)}
            placeholder="e.g. EGAL"
            autoComplete="off"
          />
          <button type="submit" disabled={loading}>
            {loading ? "Loading..." : "Load Analysis"}
          </button>
        </form>
      </header>

      {loading && (
        <section className="state-card" role="status">
          Loading latest analysis...
        </section>
      )}

      <section className="panel stock-regime-panel" aria-label="stock regime and risk profile">
        <div>
          <p className="eyebrow">TREND & RISK</p>
          <h3>Stock regime and risk profile</h3>
          <p className="muted">Loads a fresh diagnostic request from the configured market-data provider. It is not a buy/sell signal.</p>
        </div>
        <form className="symbol-form" onSubmit={handleStockRegime}>
          <button type="submit" disabled={regimeLoading || !symbol.trim()}>
            {regimeLoading ? "Loading profile..." : "Load regime & risk"}
          </button>
        </form>
        {regimeError && <p className="state-card error" role="alert">{regimeError.message}</p>}
        {regime && (
          <div className="opportunity-list">
            <div className="detail-row"><strong>{regime.symbol}</strong><span>Trend: {regime.trend} · Volatility: {regime.volatility}</span></div>
            <div className="detail-row"><span>Latest close</span><strong>{regime.latest_close ?? "—"}</strong></div>
            <div className="detail-row"><span>SMA20 / SMA50</span><strong>{regime.sma_20 ?? "—"} / {regime.sma_50 ?? "—"}</strong></div>
            <div className="detail-row"><span>Annualized realized volatility</span><strong>{regime.annualized_realized_volatility == null ? "—" : (regime.annualized_realized_volatility * 100).toFixed(2) + "%"}</strong></div>
            <div className="detail-row"><span>Drawdown from observed peak</span><strong>{regime.drawdown_from_observed_peak == null ? "—" : (regime.drawdown_from_observed_peak * 100).toFixed(2) + "%"}</strong></div>
            <div className="detail-row"><span>Valid / excluded observations</span><strong>{regime.valid_observation_count} / {regime.excluded_observation_count}</strong></div>
            <div className="detail-row"><span>Latest observation</span><strong>{regime.latest_observation_date ?? "—"}</strong></div>
            {regime.reasons?.map((reason) => <p className="muted" key={reason}>{reason}</p>)}
            <p className="muted">Source: {regime.source}. Requested through {regime.requested_to}. Diagnostic only.</p>
          </div>
        )}
      </section>

      {error?.status === 404 && (
        <section className="state-card error" role="alert">
          No stored analysis report was found.
        </section>
      )}

      {error && error.status !== 404 && (
        <section className="state-card error" role="alert">
          {error.message}
        </section>
      )}

      <section className="panel market-opportunities-panel" aria-label="market opportunities">
        <div>
          <p className="eyebrow">MARKET VIEW</p>
          <h3>Market opportunities</h3>
        </div>

        <form className="symbol-form" onSubmit={handleMarketOpportunities}>
          <label className="sr-only" htmlFor="market-symbols">
            Market symbols
          </label>
          <input
            id="market-symbols"
            name="market-symbols"
            type="text"
            value={marketSymbols}
            onChange={(event) => setMarketSymbols(event.target.value)}
            placeholder="EGAL,IEEC,COMI"
            autoComplete="off"
          />
          <button type="submit" disabled={marketLoading}>
            {marketLoading ? "Loading..." : "Load Opportunities"}
          </button>
        </form>

        {marketError && (
          <p className="state-card error" role="alert">
            {marketError.message}
          </p>
        )}

        {marketView && marketView.opportunities.length === 0 && marketView.missing_symbols.length === 0 && (
          <p className="muted">No opportunities in the requested universe.</p>
        )}

        {marketView && marketView.opportunities.length > 0 && (
          <div className="opportunity-list">
            {marketView.opportunities.map((item) => (
              <div className="detail-row" key={item.symbol}>
                <strong>{item.symbol}</strong>
                <span>
                  {item.classification} · Stock {item.stock_quality} · Entry {item.entry_quality}
                  {" "}· Technical {item.technical_score} · Fundamental {item.fundamental_score}
                </span>
                <button
                  type="button"
                  onClick={() => handleOpportunityRegime(item.symbol)}
                  disabled={Boolean(opportunityRegimeLoading[item.symbol])}
                >
                  {opportunityRegimeLoading[item.symbol] ? "Loading risk..." : "Load trend & risk"}
                </button>
                {opportunityRegimeErrors[item.symbol] && (
                  <span className="state-card error" role="alert">
                    {opportunityRegimeErrors[item.symbol].message}
                  </span>
                )}
                {opportunityRegimes[item.symbol] && (
                  <div className="opportunity-regime-summary">
                    <span>
                      Trend: {opportunityRegimes[item.symbol].trend} · Risk: {opportunityRegimes[item.symbol].volatility}
                    </span>
                    <span>
                      Close {opportunityRegimes[item.symbol].latest_close ?? "—"} · SMA20 {opportunityRegimes[item.symbol].sma_20 ?? "—"} · SMA50 {opportunityRegimes[item.symbol].sma_50 ?? "—"}
                    </span>
                    <span>
                      Realized volatility: {opportunityRegimes[item.symbol].annualized_realized_volatility == null
                        ? "—"
                        : (opportunityRegimes[item.symbol].annualized_realized_volatility * 100).toFixed(2) + "%"}
                      {" "}· Drawdown: {opportunityRegimes[item.symbol].drawdown_from_observed_peak == null
                        ? "—"
                        : (opportunityRegimes[item.symbol].drawdown_from_observed_peak * 100).toFixed(2) + "%"}
                    </span>
                    <span className="muted">
                      Data through {opportunityRegimes[item.symbol].latest_observation_date ?? "unknown date"} · {opportunityRegimes[item.symbol].valid_observation_count} valid observations · Diagnostic only, not a trading signal.
                    </span>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {marketView && marketView.missing_symbols.length > 0 && (
          <p className="muted">
            Missing stored results: {marketView.missing_symbols.join(", ")}
          </p>
        )}
      </section>


      <section className="panel market-stress-panel" aria-label="market breadth and stress pulse">
        <div>
          <p className="eyebrow">MARKET HEALTH</p>
          <h3>Market Breadth & Stress Pulse</h3>
          <p className="muted">Uses the latest saved analysis snapshots for the symbols below, not live intraday prices. This heuristic is context, not a crash prediction or trading signal.</p>
        </div>
        <form className="symbol-form" onSubmit={handleMarketBreadthStress}>
          <label className="sr-only" htmlFor="breadth-symbols">Market breadth symbols</label>
          <input
            id="breadth-symbols"
            name="breadth-symbols"
            type="text"
            value={breadthSymbols}
            onChange={(event) => setBreadthSymbols(event.target.value)}
            placeholder="EGAL,IEEC,COMI"
            autoComplete="off"
          />
          <button type="submit" disabled={breadthLoading}>
            {breadthLoading ? "Calculating..." : "Calculate Market Pulse"}
          </button>
        </form>
        {breadthError && <p className="state-card error" role="alert">{breadthError.message}</p>}
        {breadthView && (
          <div className="opportunity-list">
            <div className="detail-row"><span>Stress score / level</span><strong>{breadthView.stress_score ?? "—"} / {breadthView.stress_level}</strong></div>
            <div className="detail-row"><span>Bullish breadth</span><strong>{breadthView.bullish_breadth_percent == null ? "—" : breadthView.bullish_breadth_percent + "%"}</strong></div>
            <div className="detail-row"><span>Bearish pressure</span><strong>{breadthView.bearish_pressure_percent == null ? "—" : breadthView.bearish_pressure_percent + "%"}</strong></div>
            <div className="detail-row"><span>Uptrend / downtrend</span><strong>{breadthView.uptrend_count} / {breadthView.downtrend_count}</strong></div>
            <div className="detail-row"><span>Positive / negative momentum</span><strong>{breadthView.positive_momentum_count} / {breadthView.negative_momentum_count}</strong></div>
            <div className="detail-row"><span>Above-average volume</span><strong>{breadthView.above_average_volume_count}</strong></div>
            <div className="detail-row"><span>Coverage</span><strong>{breadthView.analyzed_symbols}/{breadthView.requested_symbols} ({breadthView.coverage_percent ?? "—"}%)</strong></div>
            {breadthView.missing_symbols?.length > 0 && <p className="muted">Missing saved analyses: {breadthView.missing_symbols.join(", ")}</p>}
            <p className="muted">Data: {breadthView.data_status}. {breadthView.methodology}</p>
          </div>
        )}
      </section>

      <section className="panel" aria-label="pre-breakout momentum volume watchlist">
        <div>
          <p className="eyebrow">EARLY WATCH</p>
          <h3>Pre-breakout Momentum + Volume</h3>
          <p className="muted">Find saved analyses with positive momentum, at least 1.5× relative volume, and price still within 5% below resistance.</p>
        </div>

        <form className="symbol-form" onSubmit={handlePreBreakoutScan}>
          <label className="sr-only" htmlFor="pre-breakout-symbols">Pre-breakout symbols</label>
          <input
            id="pre-breakout-symbols"
            name="pre-breakout-symbols"
            type="text"
            value={scannerSymbols}
            onChange={(event) => setScannerSymbols(event.target.value)}
            placeholder="EGAL,IEEC,COMI"
            autoComplete="off"
          />
          <button type="submit" disabled={preBreakoutLoading}>
            {preBreakoutLoading ? "Scanning..." : "Scan Pre-breakout"}
          </button>
        </form>

        {preBreakoutError && (
          <p className="state-card error" role="alert">{preBreakoutError.message}</p>
        )}
        {preBreakoutView && preBreakoutView.matches.length === 0 && (
          <p className="muted">No matches for the current saved analysis snapshots.</p>
        )}
        {preBreakoutView && preBreakoutView.matches.length > 0 && (
          <div className="opportunity-list">
            {preBreakoutView.matches.map((item) => (
              <div className="detail-row" key={item.symbol}>
                <strong>{item.symbol}</strong>
                <span>
                  Momentum {Number(item.momentum_percent).toFixed(2)}% · Volume {Number(item.volume_ratio).toFixed(2)}×
                  {" "}· Resistance {item.resistance_price}
                  {" "}· Distance {Number(item.distance_to_resistance_percent).toFixed(2)}%
                </span>
                <span className="muted">{item.criteria.join(" · ")}</span>
              </div>
            ))}
          </div>
        )}
        <p className="muted">Watchlist only, not a buy signal. Results use the latest saved analysis and may be stale.</p>
      </section>

      <AnalysisRunPanel getAnalysisRun={getAnalysisRun} />

      <section className="panel workflow-operations-panel" aria-label="scheduled workflows">
        <div>
          <p className="eyebrow">OPERATIONS</p>
          <h3>Scheduled workflows</h3>
          <p className="muted">Read-only visibility into persisted scheduled workflow executions.</p>
        </div>

        <form className="symbol-form" onSubmit={handleWorkflowExecutions}>
          <label className="sr-only" htmlFor="workflow-occurrence-id">
            Occurrence ID
          </label>
          <input
            id="workflow-occurrence-id"
            name="workflow-occurrence-id"
            type="text"
            value={workflowOccurrenceId}
            onChange={(event) => setWorkflowOccurrenceId(event.target.value)}
            placeholder="Optional occurrence ID"
            autoComplete="off"
          />
          <button type="submit" disabled={workflowLoading}>
            {workflowLoading ? "Loading..." : "Load Workflows"}
          </button>
        </form>

        {workflowError?.status === 503 && (
          <p className="state-card error" role="alert">
            Scheduled workflow visibility is not configured.
          </p>
        )}

        {workflowError && workflowError.status !== 503 && (
          <p className="state-card error" role="alert">
            {workflowError.message}
          </p>
        )}

        {workflowExecutions && workflowExecutions.items.length === 0 && (
          <p className="muted">No scheduled workflow executions were found.</p>
        )}

        {workflowExecutions && workflowExecutions.items.length > 0 && (
          <div className="opportunity-list">
            {workflowExecutions.items.map((execution) => (
              <div className="detail-row" key={execution.id}>
                <strong>{execution.state}</strong>
                <span>
                  {execution.occurrence_id}
                  {" · Created "}
                  {formatWorkflowTimestamp(execution.created_at)}
                  {" · Updated "}
                  {formatWorkflowTimestamp(execution.updated_at)}
                  {" · Analysis "}
                  {execution.analysis_state ?? "—"}
                  {" · Delivery "}
                  {execution.delivery_state ?? "—"}
                </span>
                <ScheduledWorkflowHistoryPanel
                  execution={execution}
                  getHistory={getScheduledWorkflowExecutionHistory}
                />

                {execution.state === "interrupted" && (
                  <div>
                    <button
                      type="button"
                      onClick={() => handleWorkflowRecovery(execution.id)}
                      disabled={recoveringWorkflowId === execution.id}
                    >
                      {recoveringWorkflowId === execution.id ? "Recovering..." : "Recover"}
                    </button>
                    {workflowRecoveryErrors[execution.id]?.status === 404 && (
                      <p className="state-card error" role="alert">
                        Workflow execution was not found.
                      </p>
                    )}
                    {workflowRecoveryErrors[execution.id]?.status === 409 && (
                      <p className="state-card error" role="alert">
                        Workflow execution is no longer recoverable.
                      </p>
                    )}
                    {workflowRecoveryErrors[execution.id] &&
                      workflowRecoveryErrors[execution.id].status !== 404 &&
                      workflowRecoveryErrors[execution.id].status !== 409 && (
                        <p className="state-card error" role="alert">
                          Workflow recovery failed.
                        </p>
                      )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="panel" aria-label="account security">
        <div>
          <p className="eyebrow">ACCOUNT</p>
          <h3>Credential security</h3>
          <p className="muted">Rotate your current durable credential. The new credential is shown once.</p>
        </div>
        <button type="button" onClick={handleRotateOwnCredential}>Rotate credential</button>
        {rotatedCredential && (
          <p className="state-card" role="status">New credential: {rotatedCredential}</p>
        )}
        {credentialRotationError && (
          <p className="state-card error" role="alert">{credentialRotationError.message}</p>
        )}
      </section>

      <UserAuditHistoryPanel getUserAuditHistory={getUserAuditHistory} />

      {identity?.subject === "operator" && (
        <section className="panel" aria-label="user administration">
          <div>
            <p className="eyebrow">ADMINISTRATION</p>
            <h3>Users</h3>
            <button type="button" onClick={handleUserAdministration} disabled={userAdminLoading}>
              {userAdminLoading ? "Loading..." : "Load Users"}
            </button>
            <button type="button" onClick={handleCreateUser} disabled={userAdminLoading}>
              Create User
            </button>
          </div>
          {userAdminError && <p className="state-card error" role="alert">{userAdminError.message}</p>}
          {users && users.items.map((user) => (
            <div className="detail-row" key={user.user_id}>
              <strong>{user.user_id}</strong>
              <span>{user.status}</span>
              {user.status === "active" && (
                <button type="button" onClick={() => handleUserStatus(user.user_id, "disabled")} disabled={userAdminLoading}>
                  Disable
                </button>
              )}
              {user.status === "disabled" && (
                <button type="button" onClick={() => handleUserStatus(user.user_id, "active")} disabled={userAdminLoading}>
                  Reactivate
                </button>
              )}
              {user.user_id !== "00000000-0000-0000-0000-000000000001" && user.status !== "deleted" && (
                <>
                  <button type="button" onClick={() => handleUserStatus(user.user_id, "deleted")} disabled={userAdminLoading}>
                    Delete
                  </button>
                  <button type="button" onClick={() => handleUserCredentialRotation(user.user_id)} disabled={userAdminLoading}>
                    Rotate Credential
                  </button>
                </>
              )}
            </div>
          ))}
        </section>
      )}

      {identity?.subject === "operator" && (
        <section className="panel" aria-label="management audit">
          <div>
            <p className="eyebrow">SECURITY OPERATIONS</p>
            <h3>Management audit</h3>
            <p className="muted">Read-only security-management evidence. Audit identity is represented by UUID.</p>
          </div>

          <form className="symbol-form" onSubmit={(event) => handleManagementAudit(event, 0)}>
            <input aria-label="Actor user ID" placeholder="Actor UUID" value={auditFilters.actorUserId} onChange={(event) => updateAuditFilter("actorUserId", event.target.value)} />
            <input aria-label="Target user ID" placeholder="Target UUID" value={auditFilters.targetUserId} onChange={(event) => updateAuditFilter("targetUserId", event.target.value)} />
            <input aria-label="Action" placeholder="Action" value={auditFilters.action} onChange={(event) => updateAuditFilter("action", event.target.value)} />
            <input aria-label="Outcome" placeholder="Outcome" value={auditFilters.outcome} onChange={(event) => updateAuditFilter("outcome", event.target.value)} />
            <input aria-label="From time" type="datetime-local" value={auditFilters.fromTime} onChange={(event) => updateAuditFilter("fromTime", event.target.value)} />
            <input aria-label="To time" type="datetime-local" value={auditFilters.toTime} onChange={(event) => updateAuditFilter("toTime", event.target.value)} />
            <button type="submit" disabled={auditLoading}>{auditLoading ? "Loading..." : "Load Audit"}</button>
          </form>

          {auditError && <p className="state-card error" role="alert">{auditError.message}</p>}
          {auditPage && auditPage.items.length === 0 && <p className="muted">No management audit events were found.</p>}

          {auditPage && auditPage.items.length > 0 && (
            <>
              <div className="opportunity-list">
                {auditPage.items.map((item) => (
                  <div className="detail-row" key={item.audit_id}>
                    <strong>{item.action}</strong>
                    <span>{item.outcome} · {item.actor_user_id} → {item.target_user_id} · {formatWorkflowTimestamp(item.occurred_at)}</span>
                  </div>
                ))}
              </div>
              <div className="symbol-form">
                <button type="button" disabled={auditLoading || auditPage.offset === 0} onClick={() => handleManagementAudit(null, Math.max(0, auditPage.offset - auditPage.page_size))}>Previous</button>
                <span className="muted">Showing {auditPage.offset + 1}–{Math.min(auditPage.offset + auditPage.items.length, auditPage.total_count)} of {auditPage.total_count}</span>
                <button type="button" disabled={auditLoading || !auditPage.has_more} onClick={() => handleManagementAudit(null, auditPage.offset + auditPage.page_size)}>Next</button>
              </div>
            </>
          )}
        </section>
      )}

      {report && (
        <>
          <section className="hero-card" aria-label="analysis result">
            <div>
              <p className="eyebrow">LATEST ANALYSIS</p>
              <h2>{report.symbol}</h2>
              <p className="muted">Analysis date: {report.analysis_date}</p>
            </div>
            <div className="classification">
              <span>Opportunity</span>
              <strong>{report.opportunity}</strong>
            </div>
          </section>

          <section className="metrics-grid" aria-label="analysis scores">
            <Metric label="Technical Score" value={report.technical_score} />
            <Metric label="Fundamental Score" value={report.fundamental_score} />
            <Metric label="Stock Quality" value={report.stock_quality} />
            <Metric label="Entry Quality" value={report.entry_quality} />
          </section>

          <section className="panel-grid">
            <DetailPanel
              title="Price & Levels"
              items={[
                ["Current price", report.current_price],
                ["Nearest support", report.nearest_support],
                ["Nearest resistance", report.nearest_resistance],
              ]}
            />
            <DetailPanel
              title="Technical"
              items={[
                ["Trend", report.trend],
                ["Momentum", report.momentum],
                ["Volume", report.volume],
              ]}
            />
            <DetailPanel
              title="Fundamentals"
              items={[
                ["Profitability", report.profitability],
                ["Liquidity", report.liquidity],
                ["Growth", report.growth],
                ["Period end", report.fundamental_period_end],
              ]}
            />
          </section>

          <TechnicalIndicatorPanel history={indicatorHistory} loading={indicatorLoading} error={indicatorError} />
          <NewsEventsPanel data={newsEvents} loading={newsLoading} error={newsError} />

          <section className="panel alert-panel" aria-label="alert result">
            <div>
              <p className="eyebrow">ALERT</p>
              <h3>Latest alert candidate</h3>
            </div>
            {alert ? (
              <div className="alert-details">
                <Metric label="Classification" value={alert.classification} />
                <Metric label="Stock Quality" value={alert.stock_quality_score} />
                <Metric label="Entry Quality" value={alert.entry_quality_score} />
              </div>
            ) : (
              <p className="muted">No alert candidate for the latest analysis.</p>
            )}
          </section>

          <section className="panel history-panel" aria-label="analysis history">
            <div>
              <p className="eyebrow">HISTORY</p>
              <h3>Historical analysis</h3>
            </div>

            {historyLoading && (
              <p className="muted" role="status">Loading historical analysis...</p>
            )}

            {historyError && (
              <p className="state-card error" role="alert">
                {historyError.message}
              </p>
            )}

            {!historyLoading && !historyError && history && history.items.length === 0 && (
              <p className="muted">No historical analysis snapshots were found.</p>
            )}

            {!historyLoading && !historyError && history && history.items.length > 0 && (
              <>
                <div className="history-list">
                  {history.items.map((item) => (
                    <div className="history-row" key={item.snapshot_id}>
                      <strong>{item.report.analysis_date}</strong>
                      <span>{item.report.opportunity}</span>
                      <span>Stock {item.report.stock_quality}</span>
                      <span>Entry {item.report.entry_quality}</span>
                      <span>Price {item.report.current_price}</span>
                    </div>
                  ))}
                </div>

                {history.items.length >= 2 && (
                  <form className="comparison-form" onSubmit={handleCompare}>
                    <label>
                      Before
                      <select
                        value={beforeSnapshotId}
                        onChange={(event) => setBeforeSnapshotId(event.target.value)}
                      >
                        <option value="">Select snapshot</option>
                        {history.items.map((item) => (
                          <option key={item.snapshot_id} value={item.snapshot_id}>
                            {item.report.analysis_date}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label>
                      After
                      <select
                        value={afterSnapshotId}
                        onChange={(event) => setAfterSnapshotId(event.target.value)}
                      >
                        <option value="">Select snapshot</option>
                        {history.items.map((item) => (
                          <option key={item.snapshot_id} value={item.snapshot_id}>
                            {item.report.analysis_date}
                          </option>
                        ))}
                      </select>
                    </label>
                    <button
                      type="submit"
                      disabled={comparisonLoading || !beforeSnapshotId || !afterSnapshotId}
                    >
                      {comparisonLoading ? "Comparing..." : "Compare"}
                    </button>
                  </form>
                )}
              </>
            )}

            {comparisonError && (
              <p className="state-card error" role="alert">
                {comparisonError.message}
              </p>
            )}

            {comparison && (
              <section className="comparison-panel" aria-label="analysis comparison">
                <p className="eyebrow">COMPARISON</p>
                <h3>{comparison.symbol} before / after</h3>
                <div className="metrics-grid">
                  <Metric label="Technical Δ" value={comparison.deltas.technical_score} />
                  <Metric label="Fundamental Δ" value={comparison.deltas.fundamental_score} />
                  <Metric label="Stock Quality Δ" value={comparison.deltas.stock_quality} />
                  <Metric label="Entry Quality Δ" value={comparison.deltas.entry_quality} />
                  <Metric label="Price Δ" value={comparison.deltas.current_price} />
                  <Metric label="Support Δ" value={comparison.deltas.nearest_support} />
                  <Metric label="Resistance Δ" value={comparison.deltas.nearest_resistance} />
                  <Metric label="Classification Changed" value={comparison.classification_changed ? "Yes" : "No"} />
                </div>
                {performanceError && (
                  <p className="state-card error" role="alert">{performanceError.message}</p>
                )}
                {performance && (
                  <div className="metrics-grid" aria-label="historical performance">
                    <Metric label="Price Change" value={performance.metrics.price_change} />
                    <Metric label="Price Change %" value={performance.metrics.price_change_percent} />
                  </div>
                )}
              </section>
            )}
          </section>
        </>
      )}
      <p className="muted financial-disclaimer" role="note">
        Informational research only — not investment advice or a guarantee of returns. Market data may be delayed or incomplete; verify official sources and assess risk independently.
      </p>
    </main>
  );
}


function LoginScreen({ onAuthenticated }) {
  const [token, setToken] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    const normalizedToken = token.trim();
    if (!normalizedToken) {
      return;
    }

    setLoading(true);
    setError(null);
    try {
      setSessionToken(normalizedToken);
      const identity = await getCurrentIdentity();
      onAuthenticated(identity);
    } catch (requestError) {
      clearSessionToken();
      setError(requestError);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="app-shell">
      <section className="panel" aria-label="login">
        <p className="eyebrow">EGX STOCK ANALYZER</p>
        <h1>Sign in</h1>
        <p className="muted">Enter your configured bearer credential to access the dashboard.</p>
        <form className="symbol-form" onSubmit={handleSubmit}>
          <label htmlFor="access-token">Access token</label>
          <input
            id="access-token"
            name="access-token"
            type="password"
            value={token}
            onChange={(event) => setToken(event.target.value)}
            autoComplete="current-password"
          />
          <button type="submit" disabled={loading || !token.trim()}>
            {loading ? "Signing in..." : "Sign in"}
          </button>
        </form>
        {error && (
          <p className="state-card error" role="alert">
            {error.status === 401 ? "Invalid authentication credential." : error.message}
          </p>
        )}
        <p className="muted financial-disclaimer" role="note">
          Informational research only — not investment advice or a guarantee of returns.
        </p>
      </section>
    </main>
  );
}

function App() {
  const [identity, setIdentity] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [pathname, setPathname] = useState(window.location.pathname);

  function navigate(path) {
    window.history.pushState({}, "", path);
    setPathname(path);
  }

  function logout() {
    clearSessionToken();
    setIdentity(null);
    navigate("/");
  }

  useEffect(() => {
    let active = true;

    async function restoreSession() {
      const token = getSessionToken();
      if (!token) {
        if (active) {
          setAuthLoading(false);
        }
        return;
      }

      try {
        const currentIdentity = await getCurrentIdentity();
        if (active) {
          setIdentity(currentIdentity);
        }
      } catch {
        clearSessionToken();
        if (active) {
          setIdentity(null);
        }
      } finally {
        if (active) {
          setAuthLoading(false);
        }
      }
    }

    restoreSession();

    const handleExpired = () => {
      if (active) {
        setIdentity(null);
      }
    };
    window.addEventListener("egx:auth-expired", handleExpired);

    return () => {
      active = false;
      window.removeEventListener("egx:auth-expired", handleExpired);
    };
  }, []);

  useEffect(() => {
    const handlePopState = () => setPathname(window.location.pathname);
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  if (authLoading) {
    return (
      <main className="app-shell">
        <section className="state-card" role="status">Checking authentication...</section>
      </main>
    );
  }

  if (!identity) {
    return <LoginScreen onAuthenticated={setIdentity} />;
  }

  if (pathname === "/analysis-runs") {
    return (
      <AnalysisRunsPage
        getAnalysisRuns={getAnalysisRuns}
        onSelectRun={(runId) => navigate("/analysis-runs/" + encodeURIComponent(runId))}
        onBack={() => navigate("/")}
      />
    );
  }

  if (pathname.startsWith("/analysis-runs/")) {
    const runId = decodeURIComponent(pathname.slice("/analysis-runs/".length));
    return (
      <main className="app-shell">
        <section className="panel" aria-label="analysis run detail">
          <button type="button" onClick={() => navigate("/analysis-runs")}>Back to Analysis Runs</button>
          <AnalysisRunPanel getAnalysisRun={getAnalysisRun} initialRunId={runId} />
        </section>
      </main>
    );
  }

  return (
    <DashboardApp
      onLogout={logout}
      identity={identity}
      onOpenAnalysisRuns={() => navigate("/analysis-runs")}
    />
  );
}

export default App;
