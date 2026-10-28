import { useEffect, useState } from "react";

function Metric({ label, value }) {
  return (
    <div className="metric">
      <span className="metric-label">{label}</span>
      <strong>{value ?? "—"}</strong>
    </div>
  );
}

function statusCounts(value) {
  if (value == null) return "Not available";
  const entries = Object.entries(value);
  return entries.length ? entries.map(([key, count]) => key + ": " + count).join(" · ") : "0";
}

export function OwnerDashboardPage({
  getOverview,
  publishOpportunity,
  dispatchOpportunities,
  generateSessionReport,
  getSessionReport,
  onBack,
}) {
  const [overview, setOverview] = useState(null);
  const [symbol, setSymbol] = useState("");
  const [publishResult, setPublishResult] = useState(null);
  const [dispatchResult, setDispatchResult] = useState(null);
  const [sessionDate, setSessionDate] = useState("");
  const [sessionReport, setSessionReport] = useState(null);
  const [sessionReportError, setSessionReportError] = useState(null);
  const [sessionReportNotice, setSessionReportNotice] = useState(null);
  const [sessionReportAction, setSessionReportAction] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [dispatching, setDispatching] = useState(false);

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      setOverview(await getOverview());
    } catch (requestError) {
      setError(requestError);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    let active = true;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const result = await getOverview();
        if (active) setOverview(result);
      } catch (requestError) {
        if (active) setError(requestError);
      } finally {
        if (active) setLoading(false);
      }
    }
    load();
    return () => { active = false; };
  }, [getOverview]);

  async function handlePublish(event) {
    event.preventDefault();
    const normalized = symbol.trim().toUpperCase();
    if (!normalized) return;
    setPublishing(true);
    setError(null);
    setPublishResult(null);
    try {
      setPublishResult(await publishOpportunity(normalized));
      setSymbol(normalized);
      await refresh();
    } catch (requestError) {
      setError(requestError);
    } finally {
      setPublishing(false);
    }
  }

  async function handleDispatch() {
    setDispatching(true);
    setError(null);
    setDispatchResult(null);
    try {
      setDispatchResult(await dispatchOpportunities(100));
      await refresh();
    } catch (requestError) {
      setError(requestError);
    } finally {
      setDispatching(false);
    }
  }

  async function handleGenerateSessionReport() {
    if (!sessionDate) return;
    setSessionReportAction("generate");
    setSessionReportError(null);
    setSessionReportNotice(null);
    try {
      const result = await generateSessionReport(sessionDate);
      setSessionReport(result);
      setSessionReportNotice(
        result.created
          ? "A new immutable snapshot was saved."
          : "The matching immutable snapshot already existed.",
      );
      await refresh();
    } catch (requestError) {
      setSessionReportError(requestError.message);
    } finally {
      setSessionReportAction(null);
    }
  }

  async function handleLoadSessionReport() {
    if (!sessionDate) return;
    setSessionReportAction("load");
    setSessionReportError(null);
    setSessionReportNotice(null);
    try {
      setSessionReport(await getSessionReport(sessionDate));
    } catch (requestError) {
      setSessionReport(null);
      setSessionReportError(
        requestError.status === 404
          ? "No saved report snapshot exists for this session date yet."
          : requestError.message,
      );
    } finally {
      setSessionReportAction(null);
    }
  }

  const counts = overview?.counts ?? {};
  const availability = overview?.availability ?? {};
  const integrations = overview?.integrations ?? {};

  return (
    <main className="app-shell">
      <header className="page-header">
        <div>
          <p className="eyebrow">OPERATIONS</p>
          <h1>Owner Dashboard</h1>
          <p className="subtitle">Queue health, subscriber delivery, and operational gaps.</p>
          <button type="button" onClick={onBack}>Back to Analysis</button>
          <button type="button" onClick={refresh} disabled={loading}>
            {loading ? "Refreshing..." : "Refresh"}
          </button>
        </div>
      </header>

      {error && (
        <p className="state-card error" role="alert">
          {error.status === 401 || error.status === 403
            ? "Operator access is required for this dashboard."
            : error.message}
        </p>
      )}

      {overview && (
        <>
          <section className="metrics-grid" aria-label="operational metrics">
            <Metric label="Linked Telegram accounts" value={counts.linked_telegram_accounts ?? "Unavailable"} />
            <Metric label="News events stored" value={counts.news_events ?? "Unavailable"} />
            <Metric label="Saved session reports" value={counts.saved_session_reports ?? "Unavailable"} />
            <Metric label="Active subscriptions" value={counts.subscriptions_by_status?.ACTIVE ?? 0} />
            <Metric label="Unexpired link challenges" value={counts.unconsumed_unexpired_link_challenges ?? "Unavailable"} />
          </section>

          <section className="panel" aria-label="delivery health">
            <h2>Delivery health</h2>
            <div className="detail-row">
              <span>Outbox by status</span>
              <strong>{statusCounts(counts.telegram_outbox_by_status)}</strong>
            </div>
            <div className="detail-row">
              <span>Recipient delivery attempts</span>
              <strong>{statusCounts(counts.telegram_deliveries_by_status)}</strong>
            </div>
            <div className="detail-row">
              <span>Oldest pending event</span>
              <strong>{counts.oldest_pending_outbox_created_at ?? "No pending events"}</strong>
            </div>
            <div className="detail-row">
              <span>Telegram transport configured</span>
              <strong>{integrations.telegram_transport_configured ? "Yes" : "No"}</strong>
            </div>
            <div className="detail-row">
              <span>News source configured</span>
              <strong>{integrations.news_source_configured ? "Yes" : "No"}</strong>
            </div>
          </section>

          <section className="panel" aria-label="opportunity operations">
            <h2>Opportunity operations</h2>
            <form className="symbol-form" onSubmit={handlePublish}>
              <label htmlFor="publish-symbol">Symbol to publish from the latest dated analysis</label>
              <input
                id="publish-symbol"
                value={symbol}
                onChange={(event) => setSymbol(event.target.value.toUpperCase())}
                placeholder="e.g. EGAL"
                autoComplete="off"
              />
              <button type="submit" disabled={publishing || !symbol.trim()}>
                {publishing ? "Queueing..." : "Publish opportunity"}
              </button>
            </form>
            <p className="muted">Publishing queues an immutable event; it does not send a Telegram message immediately.</p>
            {publishResult && (
              <p className="state-card" role="status">
                Event {publishResult.event_id} queued: {publishResult.queued_new_event ? "new event" : "already queued"}.
              </p>
            )}
            <button type="button" onClick={handleDispatch} disabled={dispatching}>
              {dispatching ? "Dispatching..." : "Dispatch queued Telegram alerts"}
            </button>
            {dispatchResult && (
              <div className="metrics-grid" aria-label="dispatch result">
                <Metric label="Events processed" value={dispatchResult.events_processed} />
                <Metric label="Events suppressed (no linked recipients)" value={dispatchResult.events_suppressed_no_recipients ?? 0} />
                <Metric label="Events suppressed (no eligible recipients)" value={dispatchResult.events_suppressed_no_eligible_recipients ?? 0} />
                <Metric label="Delivered" value={dispatchResult.recipients_delivered} />
                <Metric label="Suppressed" value={dispatchResult.recipients_suppressed} />
                <Metric label="Failed" value={dispatchResult.recipients_failed} />
              </div>
            )}
          </section>

          <section className="panel" aria-label="session opportunity reports">
            <h2>Session opportunity report snapshots</h2>
            <p className="muted">
              Generate or read an immutable point-in-time snapshot for a selected session date.
              This is a manual snapshot, not a finalized-session certification, a profitability result,
              or an automatic Telegram report.
            </p>
            <div className="session-report-controls">
              <label htmlFor="session-report-date">EGX session date</label>
              <input
                id="session-report-date"
                type="date"
                value={sessionDate}
                onChange={(event) => setSessionDate(event.target.value)}
                required
              />
              <button
                type="button"
                onClick={handleGenerateSessionReport}
                disabled={!sessionDate || sessionReportAction !== null}
              >
                {sessionReportAction === "generate" ? "Saving snapshot..." : "Generate snapshot"}
              </button>
              <button
                type="button"
                onClick={handleLoadSessionReport}
                disabled={!sessionDate || sessionReportAction !== null}
              >
                {sessionReportAction === "load" ? "Loading snapshot..." : "Load saved snapshot"}
              </button>
            </div>
            {sessionReportError && (
              <p className="state-card error" role="alert">{sessionReportError}</p>
            )}
            {sessionReportNotice && (
              <p className="state-card" role="status">{sessionReportNotice}</p>
            )}
            {sessionReport && (
              <>
                <div className="metrics-grid" aria-label="session report metrics">
                  <Metric label="Session date" value={sessionReport.session_date} />
                  <Metric label="Snapshot generated at" value={sessionReport.generated_at} />
                  <Metric label="Opportunities" value={sessionReport.total_count} />
                  <Metric label="Unresolved" value={sessionReport.unresolved_count} />
                  <Metric label="Resolved market proxies" value={sessionReport.resolved_proxy_count} />
                </div>
                <p className="muted">
                  Methodology: {sessionReport.methodology_version} · Time zone: {sessionReport.exchange_timezone}
                </p>
                <div className="detail-row">
                  <span>Current status counts</span>
                  <strong>{statusCounts(sessionReport.status_counts)}</strong>
                </div>
                {sessionReport.opportunities?.length ? (
                  <div className="table-scroll">
                    <table>
                      <thead>
                        <tr>
                          <th>Symbol</th>
                          <th>Published</th>
                          <th>Original entry zone</th>
                          <th>Invalidation</th>
                          <th>Targets</th>
                          <th>Current status</th>
                          <th>Current evidence</th>
                          <th>Market-proxy outcome</th>
                          <th>Return / R</th>
                          <th>Outcome observed at</th>
                        </tr>
                      </thead>
                      <tbody>
                        {sessionReport.opportunities.map((item) => (
                          <tr key={item.signal_id}>
                            <td>{item.symbol}</td>
                            <td>{item.publication_time}</td>
                            <td>{item.original_entry_lower} – {item.original_entry_upper}</td>
                            <td>{item.original_invalidation}</td>
                            <td>
                              {item.original_targets?.length
                                ? item.original_targets.map((target) => `${target.label}: ${target.price}`).join(" · ")
                                : "—"}
                            </td>
                            <td>{item.current_status}</td>
                            <td>{item.current_evidence?.length ? item.current_evidence.join(" · ") : "—"}</td>
                            <td>{item.market_proxy_outcome ?? "Unresolved"}</td>
                            <td>
                              {item.market_proxy_return ?? "—"} / {item.market_proxy_r ?? "—"}
                            </td>
                            <td>{item.outcome_observed_at ?? "—"}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <p className="muted">This snapshot contains no opportunities for the selected session date.</p>
                )}
              </>
            )}
          </section>

          <section className="panel" aria-label="feature readiness">
            <h2>Feature readiness</h2>
            <div className="detail-row">
              <span>Session report persistence</span>
              <strong>{availability.session_reports ? "Available" : "Not implemented/configured"}</strong>
            </div>
            <div className="detail-row">
              <span>Payment reconciliation</span>
              <strong>{availability.payment_reconciliation ? "Available" : "Not implemented/configured"}</strong>
            </div>
            {(overview.limitations ?? []).map((item) => (
              <p className="muted" key={item}>{item}</p>
            ))}
          </section>
        </>
      )}

      <p className="muted financial-disclaimer" role="note">
        Operational status only. A successful Telegram transport response does not prove that a subscriber read a message, and this dashboard does not imply a validated trading edge.
      </p>
    </main>
  );
}
