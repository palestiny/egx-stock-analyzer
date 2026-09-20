import { useEffect, useState } from "react";

export function UserAuditHistoryPanel({ getUserAuditHistory }) {
  const [page, setPage] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [action, setAction] = useState("");
  const [outcome, setOutcome] = useState("");

  async function load(nextOffset = 0) {
    setLoading(true);
    setError(null);
    try {
      setPage(
        await getUserAuditHistory({
          action: action || undefined,
          outcome: outcome || undefined,
          offset: nextOffset,
        }),
      );
    } catch (requestError) {
      setPage(null);
      setError(requestError);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load(0);
  }, []);

  return (
    <section className="panel" aria-label="personal audit history">
      <div>
        <p className="eyebrow">SECURITY</p>
        <h3>My security history</h3>
        <p className="muted">
          Read-only activity concerning your account.
        </p>
      </div>

      <form
        className="symbol-form"
        onSubmit={(event) => {
          event.preventDefault();
          load(0);
        }}
      >
        <label>
          Action
          <select value={action} onChange={(event) => setAction(event.target.value)}>
            <option value="">All account events</option>
            <option value="user_created">Account created</option>
            <option value="user_active">Account reactivated</option>
            <option value="user_disabled">Account disabled</option>
            <option value="user_deleted">Account deleted</option>
            <option value="credential_rotated">Credential rotated</option>
            <option value="credential_rotated_by_operator">Credential rotated by operator</option>
          </select>
        </label>
        <label>
          Outcome
          <select value={outcome} onChange={(event) => setOutcome(event.target.value)}>
            <option value="">All outcomes</option>
            <option value="success">Success</option>
            <option value="failed">Failed</option>
          </select>
        </label>
        <button type="submit" disabled={loading}>
          {loading ? "Loading..." : "Refresh"}
        </button>
      </form>

      {error && (
        <p className="state-card error" role="alert">
          {error.status === 401 ? "Authentication required." : error.message}
        </p>
      )}

      {loading && !page && (
        <p className="muted" role="status">Loading security history...</p>
      )}

      {!loading && page && page.items.length === 0 && (
        <p className="muted">No security events were found.</p>
      )}

      {page && page.items.length > 0 && (
        <>
          <div className="opportunity-list">
            {page.items.map((item) => (
              <div className="detail-row" key={item.audit_id}>
                <strong>{item.action}</strong>
                <span>
                  {item.outcome} · {item.actor} · {new Date(item.occurred_at).toLocaleString()}
                </span>
              </div>
            ))}
          </div>
          <div className="symbol-form">
            <button
              type="button"
              disabled={loading || page.offset === 0}
              onClick={() => load(Math.max(0, page.offset - page.page_size))}
            >
              Previous
            </button>
            <span className="muted">
              Showing {page.offset + 1}–{Math.min(page.offset + page.items.length, page.total_count)} of {page.total_count}
            </span>
            <button
              type="button"
              disabled={loading || !page.has_more}
              onClick={() => load(page.offset + page.page_size)}
            >
              Next
            </button>
          </div>
        </>
      )}
    </section>
  );
}
