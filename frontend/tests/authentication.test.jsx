import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import App from "../src/App";
import { getCurrentIdentity } from "../src/api/analysisApi";
import { clearSessionToken } from "../src/auth/session";

vi.mock("../src/api/analysisApi", () => ({
  getAlert: vi.fn(),
  getAnalysisComparison: vi.fn(),
  getAnalysisHistory: vi.fn(),
  getCurrentIdentity: vi.fn(),
  getMarketOpportunities: vi.fn(),
  getReport: vi.fn(),
  getScheduledWorkflowExecutions: vi.fn(),
  getSnapshotPerformance: vi.fn(),
  recoverScheduledWorkflowExecution: vi.fn(),
  getUserAuditHistory: vi.fn(),
}));

describe("Frontend authentication", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    clearSessionToken();
  });

  it("renders login when no session token exists", () => {
    render(<App />);
    expect(screen.getByRole("heading", { name: "Sign in" })).toBeInTheDocument();
    expect(screen.getByLabelText("Access token")).toBeInTheDocument();
  });

  it("authenticates with the entered bearer credential", async () => {
    getCurrentIdentity.mockResolvedValue({
      subject: "user-1",
      user_id: "00000000-0000-0000-0000-000000000002",
      status: "active",
    });

    render(<App />);
    fireEvent.change(screen.getByLabelText("Access token"), {
      target: { value: "secret-token" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));

    await waitFor(() =>
      expect(screen.getByLabelText("Stock Symbol")).toBeInTheDocument(),
    );
    expect(getCurrentIdentity).toHaveBeenCalledTimes(1);
    expect(window.sessionStorage.getItem("egx-stock-analyzer.session-token")).toBe("secret-token");
  });

  it("returns to login and clears the session when authentication fails", async () => {
    const error = new Error("Authentication request failed");
    error.status = 401;
    getCurrentIdentity.mockRejectedValue(error);

    render(<App />);
    fireEvent.change(screen.getByLabelText("Access token"), {
      target: { value: "wrong-token" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));

    await waitFor(() =>
      expect(screen.getByRole("heading", { name: "Sign in" })).toBeInTheDocument(),
    );
    expect(window.sessionStorage.getItem("egx-stock-analyzer.session-token")).toBeNull();
  });

  it("logs out by clearing the session", async () => {
    window.sessionStorage.setItem("egx-stock-analyzer.session-token", "test-token");
    getCurrentIdentity.mockResolvedValue({
      subject: "user-1",
      user_id: "00000000-0000-0000-0000-000000000002",
      status: "active",
    });

    render(<App />);
    await waitFor(() =>
      expect(screen.getByLabelText("Stock Symbol")).toBeInTheDocument(),
    );

    fireEvent.click(screen.getByRole("button", { name: "Log out" }));

    expect(window.sessionStorage.getItem("egx-stock-analyzer.session-token")).toBeNull();
    expect(screen.getByRole("heading", { name: "Sign in" })).toBeInTheDocument();
  });
});
