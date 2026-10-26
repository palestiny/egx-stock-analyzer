function formatTimestamp(value) {
  if (!value) return "Publication time unavailable";
  const timestamp = Date.parse(value);
  return Number.isFinite(timestamp) ? new Date(timestamp).toLocaleString() : "Publication time unavailable";
}

function safeExternalUrl(value) {
  if (typeof value !== "string" || !value.trim()) return null;
  try {
    const url = new URL(value);
    return url.protocol === "https:" || url.protocol === "http:" ? url.toString() : null;
  } catch {
    return null;
  }
}

function NewsEvent({ event }) {
  const href = safeExternalUrl(event.source_url);
  return (
    <li className="news-event" key={event.event_id}>
      <div className="detail-row">
        <span>
          {href ? (
            <a href={href} target="_blank" rel="noopener noreferrer">{event.title}</a>
          ) : event.title}
        </span>
        <strong>{String(event.category || "other").replaceAll("_", " ")}</strong>
      </div>
      <p className="muted">
        {event.source_name || "Unknown source"} · Published: {formatTimestamp(event.published_at)} · First seen: {formatTimestamp(event.first_seen_at)}
      </p>
      <p className="muted">
        Matched: {(event.matched_symbols || []).join(", ") || "Unconfirmed"} · Entity-match confidence: {event.entity_match_confidence ?? "—"}
      </p>
    </li>
  );
}

export function NewsEventsPanel({ data, loading, error }) {
  const events = data?.events ?? [];

  return (
    <section className="panel news-events-panel" aria-label="company and market news">
      <p className="eyebrow">NEWS & DISCLOSURES</p>
      <h3>Relevant news and disclosures</h3>
      {data?.as_of && <p className="muted">Evidence cutoff: {formatTimestamp(data.as_of)}</p>}
      {loading && <p role="status" className="muted">Loading news and disclosures...</p>}
      {error && <p role="alert" className="error-message">{error.message || "News and disclosures are unavailable."}</p>}
      {!loading && !error && data && events.length === 0 && (
        <p className="muted">No qualifying news events were found for this symbol at the selected cutoff. This does not prove that no relevant news exists.</p>
      )}
      {!loading && !error && events.length > 0 && (
        <ul className="news-event-list">
          {events.map((event) => <NewsEvent event={event} key={event.event_id} />)}
        </ul>
      )}
      <p className="muted indicator-note">
        News matching and categories are heuristic evidence. Open the original source before acting; publication time and first-seen time are shown separately to preserve point-in-time context.
      </p>
    </section>
  );
}
