function formatTimestamp(value) {
  if (!value) return "Publication time unknown";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "Publication time invalid";
  return parsed.toLocaleString();
}

export function NewsEventsPanel({ result, loading, error }) {
  const events = result?.events ?? [];

  return (
    <section className="panel" aria-label="news events">
      <p className="eyebrow">NEWS & DISCLOSURES</p>
      <h3>Related news events</h3>
      <p className="muted">
        Source metadata and timestamps are shown as supplied by the configured feed.
        Keyword and symbol matching are heuristic, not verified financial interpretation.
      </p>

      {loading && <p role="status" className="muted">Loading related news...</p>}
      {error && (
        <p role="alert" className="state-card error">
          {error.status === 503
            ? "News ingestion is not configured or the news store is unavailable."
            : error.status === 401 || error.status === 403
              ? "Sign in with an authorized account to view news events."
              : error.message}
        </p>
      )}

      {!loading && !error && result && events.length === 0 && (
        <p className="muted">
          No related events met the current matching and confidence filters.
          This does not prove that no relevant news exists.
        </p>
      )}

      {!loading && !error && events.length > 0 && (
        <ul className="news-event-list">
          {events.map((event) => (
            <li key={event.event_id} className="news-event">
              <div className="news-event-heading">
                {event.source_url ? (
                  <a href={event.source_url} target="_blank" rel="noreferrer">
                    {event.title || "Untitled news event"}
                  </a>
                ) : (
                  <strong>{event.title || "Untitled news event"}</strong>
                )}
              </div>
              <div className="detail-row">
                <span>Source</span>
                <strong>{event.source_name || "Unknown source"} · {event.source_type || "other"}</strong>
              </div>
              <div className="detail-row">
                <span>Category</span>
                <strong>{event.category || "uncategorized"}</strong>
              </div>
              <div className="detail-row">
                <span>Published</span>
                <strong>{formatTimestamp(event.published_at)}</strong>
              </div>
              <div className="detail-row">
                <span>Retrieved</span>
                <strong>{formatTimestamp(event.retrieved_at)}</strong>
              </div>
              {event.published_at == null && (
                <p className="muted">
                  No reliable publication timestamp: do not use this event as historical point-in-time evidence.
                </p>
              )}
              <div className="detail-row">
                <span>Symbol-match confidence</span>
                <strong>{event.entity_match_confidence ?? "Unknown"}</strong>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
