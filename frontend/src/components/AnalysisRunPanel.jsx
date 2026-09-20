import { useEffect, useState } from "react";

export function AnalysisRunPanel({ getAnalysisRun, initialRunId = "" }) {
  const [runId, setRunId] = useState(initialRunId);
  const [loadedRunId, setLoadedRunId] = useState(null);
  const [view, setView] = useState(null);
  const [cursor, setCursor] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  async function loadRunById(normalizedRunId, nextCursor = null) {
    setLoading(true);
    setError(null);
    try {
      const result = await getAnalysisRun(normalizedRunId, {
        pageSize: 50,
        cursor: nextCursor,
      });
      setView(result);
      setLoadedRunId(normalizedRunId);
      setCursor(nextCursor);
    } catch (requestError) {
      setView(null);
      setLoadedRunId(null);
      setCursor(null);
      setError(requestError);
    } finally {
      setLoading(false);
    }
  }

  async function loadRun(event, nextCursor = null) {
    event?.preventDefault();
    const normalizedRunId = runId.trim();
    if (!normalizedRunId) {
      return;
    }
    await loadRunById(normalizedRunId, nextCursor);
  }

  useEffect(() => {
    if (initialRunId) {
      setRunId(initialRunId);
      loadRunById(initialRunId);
    }
  }, [initialRunId]);

  async function loadRunForLoadedRun(nextCursor) {
    if (!loadedRunId) {
      return;
    }
    await loadRunById(loadedRunId, nextCursor);
  }

  return (
    <section className="panel" aria-label="analysis run history">
      <div>
        <p className="eyebrow">ANALYSIS RUNS</p>
        <h3>Analysis run detail</h3>
        <p className="muted">
          Inspect one durable market-wide analysis run and its correlated successful snapshots.
        </p>
      </div>

      <form className="symbol-form" onSubmit={(event) => loadRun(event)}>
        <label className="sr-only" htmlFor="analysis-run-id">
          Analysis run ID
        </label>
        <input
          id="analysis-run-id"
          name="analysis-run-id"
          type="text"
          value={runId}
          onChange={(event) => setRunId(event.target.value)}
          placeholder="AnalysisRunId"
          autoComplete="off"
        />
        <button type="submit" disabled={loading}>
          {loading ? "Loading..." : "Load Run"}
        </button>
      </form>

      {error && (
        <p className="state-card error" role="alert">
          {error.status === 404 ? "Analysis run was not found." : error.message}
        </p>
      )}

      {view && (
        <>
          <div className="detail-row">
            <strong>{view.state}</strong>
            <span>{view.run_id} · Created {new Date(view.created_at).toLocaleString()}</span>
          </div>

          {view.outcomes_available && view.outcomes.length > 0 && (
            <section aria-label="analysis run outcomes">
              <p className="eyebrow">OUTCOMES</p>
              <div className="opportunity-list">
                {view.outcomes.map((outcome) => (
                  <div className="detail-row" key={outcome.symbol}>
                    <strong>{outcome.symbol}</strong>
                    <span>
                      {outcome.state}
                      {outcome.failure_code ? ` · ${outcome.failure_code}` : ""}
                      {outcome.failure_detail ? ` · ${outcome.failure_detail}` : ""}
                    </span>
                  </div>
                ))}
              </div>
            </section>
          )}

          {view.outcomes_available && view.outcomes.length === 0 && (
            <p className="muted">This run completed without requested symbols.</p>
          )}

          {!view.outcomes_available && (
            <p className="muted">Per-symbol outcomes are unavailable for this legacy run.</p>
          )}

          {view.snapshots.length === 0 && (
            <p className="muted">This run has no successful snapshots.</p>
          )}

          {view.snapshots.length > 0 && (
            <div className="opportunity-list">
              {view.snapshots.map((snapshot) => (
                <div className="detail-row" key={snapshot.snapshot_id}>
                  <strong>{snapshot.symbol}</strong>
                  <span>{snapshot.analysis_date ?? "No analysis date"} · {snapshot.snapshot_id}</span>
                </div>
              ))}
            </div>
          )}

          {view.next_cursor && (
            <button type="button" onClick={() => loadRunForLoadedRun(view.next_cursor)} disabled={loading}>
              {loading ? "Loading..." : "Next snapshots"}
            </button>
          )}

          {cursor && (
            <button type="button" onClick={() => loadRunForLoadedRun(null)} disabled={loading}>
              First page
            </button>
          )}
        </>
      )}
    </section>
  );
}
