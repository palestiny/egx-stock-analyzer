import { useState } from "react";

export function ScheduledWorkflowHistoryPanel({ execution, getHistory }) {
  const [history, setHistory] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  async function handleLoad() {
    setLoading(true);
    setError(null);

    try {
      setHistory(await getHistory(execution.id));
    } catch (requestError) {
      setHistory(null);
      setError(requestError);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="workflow-history">
      <button type="button" onClick={handleLoad} disabled={loading}>
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
      )}
    </div>
  );
}
