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
        createSessionReport={vi.fn()}
        getSessionReport={vi.fn()}
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
        createSessionReport={vi.fn()}
        getSessionReport={vi.fn()}
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
      recipients_delivered: 3,
      recipients_suppressed: 1,
      recipients_failed: 0,
    });
    render(
      <OwnerDashboardPage
        getOverview={vi.fn().mockResolvedValue(overview)}
        publishOpportunity={vi.fn()}
        dispatchOpportunities={dispatchOpportunities}
        createSessionReport={vi.fn()}
        getSessionReport={vi.fn()}
        onBack={vi.fn()}
      />,
    );

    fireEvent.click(await screen.findByRole("button", { name: "Dispatch queued Telegram alerts" }));

    expect(await screen.findByText("Events processed")).toBeInTheDocument();
    expect(dispatchOpportunities).toHaveBeenCalledWith(100);
    const dispatchResult = screen.getByLabelText("dispatch result");
    expect(dispatchResult).toHaveTextContent("3");
    expect(dispatchResult).toHaveTextContent("0");
  });

  it("builds and displays a persisted session report with market-proxy outcomes", async () => {
    const createSessionReport = vi.fn().mockResolvedValue({
      session_date: "2026-10-26",
      generated_at: "2026-10-26T15:30:00+03:00",
      methodology_version: "session-ledger-v1",
      total_count: 1,
      resolved_proxy_count: 0,
      unresolved_count: 1,
      opportunities: [{
        signal_id: "signal-1",
        symbol: "EGAL",
        current_status: "ACTIVE",
        original_entry_lower: "100",
        original_entry_upper: "105",
        original_invalidation: "95",
        original_targets: [{ label: "T1", price: "110" }],
        market_proxy_outcome: null,
        market_proxy_return: null,
      }],
    });
    render(
      <OwnerDashboardPage
        getOverview={vi.fn().mockResolvedValue(overview)}
        publishOpportunity={vi.fn()}
        dispatchOpportunities={vi.fn()}
        createSessionReport={createSessionReport}
        getSessionReport={vi.fn()}
        onBack={vi.fn()}
      />,
    );

    fireEvent.change(await screen.findByLabelText("EGX session date"), {
      target: { value: "2026-10-26" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Generate and save report" }));

    expect(await screen.findByText("Session 2026-10-26")).toBeInTheDocument();
    expect(screen.getByText("EGAL")).toBeInTheDocument();
    expect(screen.getByText("T1: 110")).toBeInTheDocument();
    expect(screen.getByText("Unresolved")).toBeInTheDocument();
    expect(createSessionReport).toHaveBeenCalledWith("2026-10-26");
  });

});
