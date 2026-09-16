import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import App from "../src/App";
import { getAnalysis } from "../src/api/analysisApi";

vi.mock("../src/api/analysisApi", () => ({
  getAnalysis: vi.fn(),
}));

const analysis = {
  symbol: "EGAL",
  technical_score: 1,
  fundamental_score: 2,
  stock_quality: 3,
  entry_quality: 1,
  opportunity: "buy",
};

describe("Dashboard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the analysis symbol input and action", () => {
    render(<App />);

    expect(screen.getByLabelText(/stock symbol/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /analyze/i })).toBeInTheDocument();
  });

  it("renders a successful analysis result", async () => {
    getAnalysis.mockResolvedValue(analysis);
    const user = userEvent.setup();

    render(<App />);
    await user.type(screen.getByLabelText(/stock symbol/i), "EGAL");
    await user.click(screen.getByRole("button", { name: /analyze/i }));

    expect(await screen.findByText("EGAL")).toBeInTheDocument();
    expect(screen.getByText("Technical Score")).toBeInTheDocument();
    expect(screen.getByText("1")).toBeInTheDocument();
    expect(screen.getByText("Fundamental Score")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
    expect(screen.getByText("Stock Quality")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
    expect(screen.getByText("Entry Quality")).toBeInTheDocument();
    expect(screen.getByText("Opportunity")).toBeInTheDocument();
    expect(screen.getByText("buy")).toBeInTheDocument();
  });

  it("shows a loading state while the request is pending", async () => {
    let resolveRequest;
    getAnalysis.mockReturnValue(new Promise((resolve) => {
      resolveRequest = resolve;
    }));
    const user = userEvent.setup();

    render(<App />);
    await user.type(screen.getByLabelText(/stock symbol/i), "EGAL");
    await user.click(screen.getByRole("button", { name: /analyze/i }));

    expect(screen.getByText(/loading/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /analyze/i })).toBeDisabled();

    resolveRequest(analysis);
    await waitFor(() => {
      expect(screen.queryByText(/loading/i)).not.toBeInTheDocument();
    });
  });

  it("shows an API error", async () => {
    getAnalysis.mockRejectedValue(new Error("Network error"));
    const user = userEvent.setup();

    render(<App />);
    await user.type(screen.getByLabelText(/stock symbol/i), "EGAL");
    await user.click(screen.getByRole("button", { name: /analyze/i }));

    expect(await screen.findByText("Network error")).toBeInTheDocument();
  });

  it("shows a not-found message for a 404 result", async () => {
    const error = new Error("Analysis request failed with status 404");
    error.status = 404;
    getAnalysis.mockRejectedValue(error);
    const user = userEvent.setup();

    render(<App />);
    await user.type(screen.getByLabelText(/stock symbol/i), "EGAL");
    await user.click(screen.getByRole("button", { name: /analyze/i }));

    expect(await screen.findByText(/analysis result not found/i)).toBeInTheDocument();
  });
});
