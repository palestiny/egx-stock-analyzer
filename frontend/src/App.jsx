import { useState } from "react";

import { getAnalysis } from "./api/analysisApi";

function App() {
  const [symbol, setSymbol] = useState("");
  const [analysis, setAnalysis] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  async function handleAnalyze() {
    const normalizedSymbol = symbol.trim().toUpperCase();

    if (!normalizedSymbol) {
      return;
    }

    setLoading(true);
    setAnalysis(null);
    setError(null);

    try {
      const result = await getAnalysis(normalizedSymbol);
      setAnalysis(result);
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
        Analyze
      </button>

      {loading && <p>Loading analysis...</p>}

      {error?.status === 404 && <p>Analysis result not found.</p>}
      {error && error.status !== 404 && <p>{error.message}</p>}

      {analysis && (
        <section aria-label="analysis result">
          <h2>{analysis.symbol}</h2>

          <article>
            <h3>Technical Score</h3>
            <p>{analysis.technical_score}</p>
          </article>

          <article>
            <h3>Fundamental Score</h3>
            <p>{analysis.fundamental_score}</p>
          </article>

          <article>
            <h3>Stock Quality</h3>
            <p>{analysis.stock_quality}</p>
          </article>

          <article>
            <h3>Entry Quality</h3>
            <p>{analysis.entry_quality}</p>
          </article>

          <article>
            <h3>Opportunity</h3>
            <p>{analysis.opportunity}</p>
          </article>
        </section>
      )}
    </main>
  );
}

export default App;
