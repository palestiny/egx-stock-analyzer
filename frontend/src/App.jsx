import { useState } from "react";

import { getAlert, getReport } from "./api/analysisApi";

function App() {
  const [symbol, setSymbol] = useState("");
  const [report, setReport] = useState(null);
  const [alert, setAlert] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  async function handleAnalyze() {
    const normalizedSymbol = symbol.trim().toUpperCase();

    if (!normalizedSymbol) {
      return;
    }

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
    <main>
      <h1>EGX Stock Analyzer</h1>

      <label htmlFor="stock-symbol">Stock Symbol</label>
      <input
        id="stock-symbol"
        name="stock-symbol"
        type="text"
        value={symbol}
        onChange={(event) => setSymbol(event.target.value)}
        placeholder="e.g. EGAL"
      />

      <button type="button" onClick={handleAnalyze} disabled={loading}>
        {loading ? "Loading..." : "Load Analysis"}
      </button>

      {loading && <p>Loading latest analysis...</p>}

      {error?.status === 404 && <p>No stored analysis report was found.</p>}
      {error && error.status !== 404 && <p>{error.message}</p>}

      {report && (
        <section aria-label="analysis result">
          <h2>{report.symbol}</h2>
          <p>Analysis date: {report.analysis_date}</p>
          <p>Current price: {report.current_price ?? "—"}</p>
          <p>Technical Score: {report.technical_score}</p>
          <p>Fundamental Score: {report.fundamental_score}</p>
          <p>Stock Quality: {report.stock_quality}</p>
          <p>Entry Quality: {report.entry_quality}</p>
          <p>Opportunity: {report.opportunity}</p>
          <p>Support: {report.nearest_support ?? "—"}</p>
          <p>Resistance: {report.nearest_resistance ?? "—"}</p>
          <p>Trend: {report.trend}</p>
          <p>Momentum: {report.momentum}</p>
          <p>Volume: {report.volume}</p>
          <p>Profitability: {report.profitability}</p>
          <p>Liquidity: {report.liquidity}</p>
          <p>Growth: {report.growth}</p>
        </section>
      )}

      {report && (
        <section aria-label="alert result">
          <h2>Alert</h2>
          {alert ? (
            <>
              <p>Classification: {alert.classification}</p>
              <p>Stock Quality: {alert.stock_quality_score}</p>
              <p>Entry Quality: {alert.entry_quality_score}</p>
            </>
          ) : (
            <p>No alert candidate for the latest analysis.</p>
          )}
        </section>
      )}
    </main>
  );
}

export default App;
