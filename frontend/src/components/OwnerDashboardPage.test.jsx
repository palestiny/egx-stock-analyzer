import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { OwnerDashboardPage } from "./OwnerDashboardPage";

const overview = {
  as_of: "2026-10-26T12:00:00+00:00",
  availability: {
    session_reports: false,
    payment_reconciliation: false,
  },
  counts: {
    linked_telegram_accounts: 4,
    news_events: 12,
    subscriptions_by_status: { ACTIVE: 3 },
    unconsumed_unexpired_link_challenges: 1,
    telegram_outbox_by_status: { PENDING: 2, DELIVERED: 5 },
    telegram_deliveries_by_status: { DELIVERED: 5, FAILED: 1, SUPPRESSED: 2 },
    oldest_pending_outbox_created_at: "2026-10-26T10:00:00+00:00",
  },
  integrations: {
    telegram_transport_configured: true,
    news_source_configured: false,
  },
  limitations: ["Session reports are not configured."],
};

describe("OwnerDashboardPage", () => {
  it("shows aggregate operational status and explicitly marks missing features", async () => {
    const getOverview = vi.fn().mockResolvedValue(overview);
    render(
      <OwnerDashboardPage
        getOverview={getOverview}
        publishOpportunity={vi.fn()}
        dispatchOpportunities={vi.fn()}
        onBack={vi.fn()}
      />,
    );

    expect(await screen.findByText("Owner Dashboard")).toBeInTheDocument();
    expect(screen.getByText("4")).toBeInTheDocument();
    expect(screen.getByText("12")).toBeInTheDocument();
    expect(screen.getAllByText("Not implemented/configured")).toHaveLength(2);
    expect(screen.getByText("News source configured")).toBeInTheDocument();
  });

  it("queues a symbol opportunity and refreshes the overview", async () => {
    const getOverview = vi.fn().mockResolvedValue(overview);
    const publishOpportunity = vi.fn().mockResolvedValue({
      event_id: "event-123",
      queued_new_event: true,
    });
    render(
      <OwnerDashboardPage
        getOverview={getOverview}
        publishOpportunity={publishOpportunity}
        dispatchOpportunities={vi.fn()}
        onBack={vi.fn()}
      />,
    );

    fireEvent.change(await screen.findByLabelText("Symbol to publish from the latest dated analysis"), {
      target: { value: "egal" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Publish opportunity" }));

    expect(await screen.findByText(/event-123 queued/)).toBeInTheDocument();
    expect(publishOpportunity).toHaveBeenCalledWith("EGAL");
    await waitFor(() => expect(getOverview).toHaveBeenCalledTimes(2));
  });

  it("dispatches the queued alert batch and displays recipient outcomes", async () => {
    const dispatchOpportunities = vi.fn().mockResolvedValue({
      events_processed: 2,
      events_suppressed_no_recipients: 0,
      events_suppressed_no_eligible_recipients: 1,
      recipients_delivered: 3,
      recipients_suppressed: 1,
      recipients_failed: 0,
    });
    render(
      <OwnerDashboardPage
        getOverview={vi.fn().mockResolvedValue(overview)}
        publishOpportunity={vi.fn()}
        dispatchOpportunities={dispatchOpportunities}
        onBack={vi.fn()}
      />,
    );

    fireEvent.click(await screen.findByRole("button", { name: "Dispatch queued Telegram alerts" }));

    expect(await screen.findByText("Events processed")).toBeInTheDocument();
    expect(dispatchOpportunities).toHaveBeenCalledWith(100);
    const dispatchResult = screen.getByLabelText("dispatch result");
    expect(dispatchResult).toHaveTextContent("3");
    expect(dispatchResult).toHaveTextContent("Events suppressed (no linked recipients)");
    expect(dispatchResult).toHaveTextContent("Events suppressed (no eligible recipients)");
    expect(dispatchResult).toHaveTextContent("1");
  });


  it("generates and displays an explicitly provisional point-in-time report snapshot", async () => {
    const report = {
      session_date: "2026-10-26",
      generated_at: "2026-10-27T05:00:00+00:00",
      exchange_timezone: "Africa/Cairo",
      methodology_version: "session-opportunity-ledger-v1",
      total_count: 1,
      unresolved_count: 1,
      resolved_proxy_count: 0,
      status_counts: { ACTIVE: 1, TRIGGERED: 0 },
      opportunities: [{
        signal_id: "signal-1",
        symbol: "EGAL",
        publication_time: "2026-10-26T11:00:00+00:00",
        original_entry_lower: "350",
        original_entry_upper: "355",
        original_invalidation: "342",
        original_targets: [{ label: "T1", price: "370" }],
        current_status: "ACTIVE",
        current_evidence: ["daily close above resistance"],
        market_proxy_outcome: null,
        market_proxy_return: null,
        market_proxy_r: null,
        outcome_observed_at: null,
      }],
      created: true,
    };
    const generateSessionReport = vi.fn().mockResolvedValue(report);
    render(
      <OwnerDashboardPage
        getOverview={vi.fn().mockResolvedValue(overview)}
        publishOpportunity={vi.fn()}
        dispatchOpportunities={vi.fn()}
        generateSessionReport={generateSessionReport}
        getSessionReport={vi.fn()}
        onBack={vi.fn()}
      />,
    );

    fireEvent.change(await screen.findByLabelText("EGX session date"), {
      target: { value: "2026-10-26" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Generate snapshot" }));

    expect(await screen.findByText("A new immutable snapshot was saved.")).toBeInTheDocument();
    expect(generateSessionReport).toHaveBeenCalledWith("2026-10-26");
    expect(screen.getByText(/manual snapshot, not a finalized-session certification/)).toBeInTheDocument();
    expect(screen.getByText("EGAL")).toBeInTheDocument();
    expect(screen.getByText("350 – 355")).toBeInTheDocument();
    expect(screen.getByText("daily close above resistance")).toBeInTheDocument();
    expect(screen.getAllByText("Unresolved").length).toBeGreaterThan(0);
  });

  it("shows a clear empty state when no saved session snapshot exists", async () => {
    const getSessionReport = vi.fn().mockRejectedValue({ status: 404, message: "not found" });
    render(
      <OwnerDashboardPage
        getOverview={vi.fn().mockResolvedValue(overview)}
        publishOpportunity={vi.fn()}
        dispatchOpportunities={vi.fn()}
        generateSessionReport={vi.fn()}
        getSessionReport={getSessionReport}
        onBack={vi.fn()}
      />,
    );

    fireEvent.change(await screen.findByLabelText("EGX session date"), {
      target: { value: "2026-10-26" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Load saved snapshot" }));

    expect(await screen.findByText("No saved report snapshot exists for this session date yet.")).toBeInTheDocument();
    expect(getSessionReport).toHaveBeenCalledWith("2026-10-26");
  });
});
