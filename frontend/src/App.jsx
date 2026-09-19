import { useState } from "react";

import { getAlert, getAnalysisComparison, getAnalysisHistory, getMarketOpportunities, getReport, getScheduledWorkflowExecutions, getSnapshotPerformance, recoverScheduledWorkflowExecution } from "./api/analysisApi";

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

function App() {
  const [symbol, setSymbol] = useState("");
  const [report, setReport] = useState(null);
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
  const [marketSymbols, setMarketSymbols] = useState("EGAL,IEEC,COMI");
  const [marketView, setMarketView] = useState(null);
  const [marketError, setMarketError] = useState(null);
  const [marketLoading, setMarketLoading] = useState(false);
  const [workflowOccurrenceId, setWorkflowOccurrenceId] = useState("");
  const [workflowExecutions, setWorkflowExecutions] = useState(null);
  const [workflowError, setWorkflowError] = useState(null);
  const [workflowLoading, setWorkflowLoading] = useState(false);
  const [recoveringWorkflowId, setRecoveringWorkflowId] = useState(null);
  const [workflowRecoveryErrors, setWorkflowRecoveryErrors] = useState({});

  async function handleAnalyze(event) {
    event.preventDefault();
    const normalizedSymbol = symbol.trim().toUpperCase();

    if (!normalizedSymbol) {
      return;
    }

    setSymbol(normalizedSymbol);
    setLoading(true);
    setReport(null);
    setAlert(null);
    setHistory(null);
    setHistoryError(null);
    setHistoryLoading(true);
    setError(null);

    try {
      const reportResult = await getReport(normalizedSymbol);
      setReport(reportResult);

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
    } finally {
      setLoading(false);
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
    </main>
  );
}

export default App;
