import { useState } from "react";

const PAGE_SIZE = 50;
const STATE_OPTIONS = [
  "created",
  "running",
  "completed",
  "completed_with_errors",
  "failed",
  "interrupted",
];

export function ScheduledWorkflowHistoryPanel({ execution, getHistory }) {
  const [history, setHistory] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [fromState, setFromState] = useState("");
  const [toState, setToState] = useState("");

  async function handleLoad(options = {}) {
    setLoading(true);
    setError(null);

    try {
      setHistory(await getHistory(execution.id, options));
    } catch (requestError) {
      setHistory(null);
      setError(requestError);
    } finally {
      setLoading(false);
    }
  }

  function getFilterOptions() {
    return {
      pageSize: PAGE_SIZE,
      ...(fromState ? { fromState } : {}),
      ...(toState ? { toState } : {}),
    };
  }

  async function handleLoadMore() {
    if (!history?.next_cursor) {
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const nextPage = await getHistory(execution.id, {
        ...getFilterOptions(),
        cursor: history.next_cursor,
      });
      setHistory((current) => ({
        ...nextPage,
        history: [...(current?.history ?? []), ...nextPage.history],
      }));
    } catch (requestError) {
      setError(requestError);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="workflow-history">
      <div className="workflow-history-filters">
        <label>
          From state
          <select
            aria-label="From state"
            value={fromState}
            onChange={(event) => setFromState(event.target.value)}
          >
            <option value="">Any</option>
            {STATE_OPTIONS.map((state) => (
              <option key={state} value={state}>{state}</option>
            ))}
          </select>
        </label>
        <label>
          To state
          <select
            aria-label="To state"
            value={toState}
            onChange={(event) => setToState(event.target.value)}
          >
            <option value="">Any</option>
            {STATE_OPTIONS.map((state) => (
              <option key={state} value={state}>{state}</option>
            ))}
          </select>
        </label>
      </div>

      <button
        type="button"
        onClick={() => handleLoad(getFilterOptions())}
        disabled={loading}
      >
        {loading ? "Loading history..." : "History"}
      </button>

      {error?.status === 404 && (
        <p className="state-card error" role="alert">
          Workflow execution history was not found.
        </p>
      )}

      {error && error.status !== 404 && (
        <p className="state-card error" role="alert">
          Workflow execution history could not be loaded.
        </p>
      )}

      {history && history.history.length === 0 && (
        <p className="muted">No lifecycle history is available.</p>
      )}

      {history && history.history.length > 0 && (
        <>
          <div className="history-list" aria-label="workflow lifecycle history">
            {history.history.map((item) => (
              <div className="history-row" key={item.sequence}>
                <strong>{item.to_state}</strong>
                <span>
                  {item.from_state ?? "—"} → {item.to_state}
                </span>
                <span>{item.reason ?? "No reason recorded"}</span>
                <span>{new Date(item.occurred_at).toLocaleString()}</span>
              </div>
            ))}
          </div>

          {history.has_more && (
            <button type="button" onClick={handleLoadMore} disabled={loading}>
              {loading ? "Loading..." : "Load more"}
            </button>
          )}
        </>
      )}
    </div>
  );
}
