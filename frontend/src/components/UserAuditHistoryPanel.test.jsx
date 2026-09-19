import { render, screen, waitFor } from "@testing-library/react";
import { expect, it, vi } from "vitest";

import { UserAuditHistoryPanel } from "./UserAuditHistoryPanel";

it("loads and renders redacted personal audit history", async () => {
  const getUserAuditHistory = vi.fn().mockResolvedValue({
    items: [
      {
        audit_id: 1,
        actor: "operator",
        target: "self",
        action: "credential_rotated_by_operator",
        occurred_at: "2026-09-19T12:00:00+00:00",
        outcome: "success",
      },
    ],
    total_count: 1,
    offset: 0,
    page_size: 50,
    has_more: false,
  });

  render(<UserAuditHistoryPanel getUserAuditHistory={getUserAuditHistory} />);

  await waitFor(() => {
    expect(screen.getByText("credential_rotated_by_operator")).toBeInTheDocument();
  });

  expect(screen.getByText(/success.*operator/)).toBeInTheDocument();
  expect(getUserAuditHistory).toHaveBeenCalledWith({
    action: undefined,
    outcome: undefined,
    offset: 0,
  });
});

it("renders empty state", async () => {
  const getUserAuditHistory = vi.fn().mockResolvedValue({
    items: [],
    total_count: 0,
    offset: 0,
    page_size: 50,
    has_more: false,
  });

  render(<UserAuditHistoryPanel getUserAuditHistory={getUserAuditHistory} />);

  await waitFor(() => {
    expect(screen.getByText("No security events were found.")).toBeInTheDocument();
  });
});
