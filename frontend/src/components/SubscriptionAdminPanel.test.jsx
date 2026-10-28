import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { SubscriptionAdminPanel } from "./SubscriptionAdminPanel";

describe("SubscriptionAdminPanel", () => {
  it("creates an immutable plan version from validated entitlement JSON", async () => {
    const createPlan = vi.fn().mockResolvedValue({
      plan_id: "telegram-pilot",
      version: 1,
      display_name: "Telegram Pilot",
    });
    render(<SubscriptionAdminPanel createPlan={createPlan} />);

    fireEvent.click(screen.getByRole("button", { name: "Create plan version" }));

    await waitFor(() => expect(createPlan).toHaveBeenCalledWith({
      plan_id: "telegram-pilot",
      version: 1,
      display_name: "Telegram Pilot",
      entitlements: [{ code: "telegram_opportunities", enabled: true, limit: 50 }],
      active: true,
    }));
    expect(await screen.findByText("Latest result: plan")).toBeInTheDocument();
  });

  it("provisions a pending subscription and requires an explicit audited transition", async () => {
    const createSubscription = vi.fn().mockResolvedValue({
      subscription_id: "subscription-123",
      user_id: "7f1ec31e-2c2b-4a2e-a24c-7d2c2f81d912",
      plan_id: "telegram-pilot",
      plan_version: 1,
      status: "PENDING",
    });
    const transitionSubscription = vi.fn().mockResolvedValue({
      subscription_id: "subscription-123",
      user_id: "7f1ec31e-2c2b-4a2e-a24c-7d2c2f81d912",
      plan_id: "telegram-pilot",
      plan_version: 1,
      status: "ACTIVE",
    });
    render(
      <SubscriptionAdminPanel
        createSubscription={createSubscription}
        transitionSubscription={transitionSubscription}
      />,
    );

    fireEvent.change(screen.getByLabelText("User ID"), { target: { value: "7f1ec31e-2c2b-4a2e-a24c-7d2c2f81d912" } });
    fireEvent.change(screen.getByLabelText("Starts at (ISO-8601 with timezone)"), {
      target: { value: "2026-10-28T09:00:00+03:00" },
    });
    fireEvent.change(screen.getByLabelText("Expires at (ISO-8601 with timezone)"), {
      target: { value: "2026-11-28T09:00:00+03:00" },
    });
    fireEvent.change(screen.getByLabelText("Audit reason"), {
      target: { value: "Manual pilot provisioning" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create pending subscription" }));

    await waitFor(() => expect(createSubscription).toHaveBeenCalledWith({
      user_id: "7f1ec31e-2c2b-4a2e-a24c-7d2c2f81d912",
      plan_id: "telegram-pilot",
      plan_version: 1,
      starts_at: "2026-10-28T09:00:00+03:00",
      expires_at: "2026-11-28T09:00:00+03:00",
      reason: "Manual pilot provisioning",
      payment_provider: null,
      payment_reference: null,
    }));
    expect(await screen.findByText("Current status: PENDING")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("New status"), { target: { value: "ACTIVE" } });
    fireEvent.change(screen.getAllByLabelText("Audit reason")[1], {
      target: { value: "Operator verified pilot access" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Record status transition" }));

    await waitFor(() => expect(transitionSubscription).toHaveBeenCalledWith(
      "subscription-123",
      { status: "ACTIVE", reason: "Operator verified pilot access" },
    ));
    expect(await screen.findByText("Current status: ACTIVE")).toBeInTheDocument();
  });

  it("rejects invalid entitlement JSON before sending a request", async () => {
    const createPlan = vi.fn();
    render(<SubscriptionAdminPanel createPlan={createPlan} />);
    fireEvent.change(screen.getByLabelText("Entitlements JSON"), {
      target: { value: "{invalid" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create plan version" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/valid JSON/);
    expect(createPlan).not.toHaveBeenCalled();
  });

  it("does not offer transitions from a terminal subscription status", async () => {
    const getSubscription = vi.fn().mockResolvedValue({
      subscription_id: "subscription-terminal",
      user_id: "user-1",
      plan_id: "telegram-pilot",
      plan_version: 1,
      status: "CANCELLED",
    });
    const transitionSubscription = vi.fn();
    render(
      <SubscriptionAdminPanel
        getSubscription={getSubscription}
        transitionSubscription={transitionSubscription}
      />,
    );

    fireEvent.change(screen.getByLabelText("Subscription ID"), {
      target: { value: "subscription-terminal" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Find by subscription ID" }));

    expect(await screen.findByText(/This is a terminal status; no further transitions are allowed\./)).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Transition subscription status" })).not.toBeInTheDocument();
    expect(transitionSubscription).not.toHaveBeenCalled();
  });


  it("loads and displays persisted subscription audit events", async () => {
    const getSubscription = vi.fn().mockResolvedValue({
      subscription_id: "subscription-audit",
      user_id: "7f1ec31e-2c2b-4a2e-a24c-7d2c2f81d912",
      plan_id: "telegram-pilot",
      plan_version: 1,
      status: "ACTIVE",
    });
    const getSubscriptionEvents = vi.fn().mockResolvedValue({
      subscription_id: "subscription-audit",
      events: [{
        event_id: 1,
        actor: "operator",
        event: "STATUS_TRANSITION",
        reason: "Verified pilot access",
        occurred_at: "2026-10-28T10:00:00+00:00",
        previous_status: "PENDING",
        new_status: "ACTIVE",
      }],
    });
    render(
      <SubscriptionAdminPanel
        getSubscription={getSubscription}
        getSubscriptionEvents={getSubscriptionEvents}
      />,
    );

    fireEvent.change(screen.getByLabelText("Subscription ID"), {
      target: { value: "subscription-audit" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Find by subscription ID" }));
    fireEvent.click(await screen.findByRole("button", { name: "Load audit history" }));

    const auditHistory = await screen.findByLabelText("subscription audit history");
    expect(auditHistory).toHaveTextContent("Verified pilot access");
    expect(getSubscriptionEvents).toHaveBeenCalledWith("subscription-audit");
    expect(auditHistory).toHaveTextContent("PENDING → ACTIVE");
  });

});