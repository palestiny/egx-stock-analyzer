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
    expect(screen.getByText("Not implemented/configured")).toBeInTheDocument();
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
    expect(screen.getByText("3")).toBeInTheDocument();
    expect(screen.getByText("0")).toBeInTheDocument();
  });
});
