import { useState } from "react";

import { getAlert, getReport } from "./api/analysisApi";

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
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

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
    } catch (requestError) {
      setError(requestError);
    } finally {
      setLoading(false);
    }
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
        </>
      )}
    </main>
  );
}

export default App;
