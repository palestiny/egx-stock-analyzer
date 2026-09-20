import { useEffect, useState } from "react";

const STATE_OPTIONS = [
  { value: "", label: "All states" },
  { value: "completed", label: "Completed" },
  { value: "completed_with_errors", label: "Completed with errors" },
  { value: "failed", label: "Failed" },
];

function discoveryErrorMessage(error) {
  if (error?.status === 401) return "Your session has expired. Sign in again.";
  if (error?.status === 403) return "You do not have access to analysis runs.";
  if (error?.status === 400) return "The run discovery query is invalid.";
  return "Analysis run discovery is temporarily unavailable.";
}

export function AnalysisRunsPage({ getAnalysisRuns, onSelectRun, onBack }) {
  const [state, setState] = useState("");
  const [view, setView] = useState(null);
  const [cursor, setCursor] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  async function loadRuns(nextCursor = null) {
    setLoading(true);
    setError(null);

    try {
      const result = await getAnalysisRuns({
        state: state || undefined,
        pageSize: 50,
        cursor: nextCursor,
      });
      setView(result);
      setCursor(nextCursor);
    } catch (requestError) {
      setView(null);
      setCursor(null);
      setError(requestError);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadRuns(null);
  }, [state]);

  return (
    <main className="app-shell">
      <header className="page-header">
        <div>
          <p className="eyebrow">ANALYSIS RUNS</p>
          <h1>Analysis Runs</h1>
          <p className="subtitle">
            Discover persisted market-wide analysis runs and open a run to inspect its snapshots.
          </p>
        </div>
        <div className="symbol-form">
          <button type="button" onClick={onBack}>Back to Dashboard</button>
          <button type="button" onClick={() => loadRuns(null)} disabled={loading}>
            {loading ? "Refreshing..." : "Refresh"}
          </button>
        </div>
      </header>

      <section className="panel" aria-label="analysis run discovery">
        <div className="symbol-form">
          <label htmlFor="analysis-run-state">State</label>
          <select
            id="analysis-run-state"
            value={state}
            onChange={(event) => setState(event.target.value)}
            disabled={loading}
          >
            {STATE_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </select>
        </div>

        {loading && (
          <p className="state-card" role="status">Loading analysis runs...</p>
        )}

        {error && (
          <p className="state-card error" role="alert">{discoveryErrorMessage(error)}</p>
        )}

        {!loading && !error && view && view.items.length === 0 && (
          <p className="muted">No analysis runs matched the selected filter.</p>
        )}

        {!error && view && view.items.length > 0 && (
          <div className="opportunity-list">
            {view.items.map((run) => (
              <button
                className="detail-row"
                type="button"
                key={run.run_id}
                onClick={() => onSelectRun(run.run_id)}
              >
                <strong>{run.state}</strong>
                <span>
                  {run.run_id} · Created {new Date(run.created_at).toLocaleString()}
                </span>
              </button>
            ))}
          </div>
        )}

        {!error && view && (
          <div className="symbol-form">
            <button
              type="button"
              onClick={() => loadRuns(null)}
              disabled={loading || !cursor}
            >
              First page
            </button>
            <button
              type="button"
              onClick={() => loadRuns(view.next_cursor)}
              disabled={loading || !view.next_cursor}
            >
              Next page
            </button>
          </div>
        )}
      </section>
    </main>
  );
}
