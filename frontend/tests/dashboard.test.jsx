import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import App from "../src/App";

const { mockGetAnalysis } = vi.hoisted(() => ({
  mockGetAnalysis: vi.fn(),
}));

vi.mock("../src/api/analysisApi", () => ({
  getAnalysis: mockGetAnalysis,
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
    mockGetAnalysis.mockResolvedValue(analysis);

    render(<App />);
    fireEvent.change(screen.getByLabelText(/stock symbol/i), {
      target: { value: "EGAL" },
    });
    fireEvent.click(screen.getByRole("button", { name: /analyze/i }));

    expect(await screen.findByRole("heading", { name: "EGAL" })).toBeInTheDocument();
    expect(screen.getByText("Technical Score")).toBeInTheDocument();
    expect(screen.getByText("Fundamental Score")).toBeInTheDocument();
    expect(screen.getByText("Stock Quality")).toBeInTheDocument();
    expect(screen.getByText("Entry Quality")).toBeInTheDocument();
    expect(screen.getByText("Opportunity")).toBeInTheDocument();
    expect(screen.getByText("buy")).toBeInTheDocument();
    expect(mockGetAnalysis).toHaveBeenCalledWith("EGAL");
  });

  it("shows a loading state while the request is pending", async () => {
    let resolveRequest;
    mockGetAnalysis.mockReturnValue(new Promise((resolve) => {
      resolveRequest = resolve;
    }));

    render(<App />);
    fireEvent.change(screen.getByLabelText(/stock symbol/i), {
      target: { value: "EGAL" },
    });
    fireEvent.click(screen.getByRole("button", { name: /analyze/i }));

    expect(screen.getByText(/loading/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /analyze/i })).toBeDisabled();

    resolveRequest(analysis);
    await waitFor(() => {
      expect(screen.queryByText(/loading/i)).not.toBeInTheDocument();
    });
  });

  it("shows an API error", async () => {
    mockGetAnalysis.mockRejectedValue(new Error("Network error"));

    render(<App />);
    fireEvent.change(screen.getByLabelText(/stock symbol/i), {
      target: { value: "EGAL" },
    });
    fireEvent.click(screen.getByRole("button", { name: /analyze/i }));

    expect(await screen.findByText("Network error")).toBeInTheDocument();
  });

  it("shows a not-found message for a 404 result", async () => {
    const error = new Error("Analysis request failed with status 404");
    error.status = 404;
    mockGetAnalysis.mockRejectedValue(error);

    render(<App />);
    fireEvent.change(screen.getByLabelText(/stock symbol/i), {
      target: { value: "EGAL" },
    });
    fireEvent.click(screen.getByRole("button", { name: /analyze/i }));

    expect(await screen.findByText(/analysis result not found/i)).toBeInTheDocument();
  });
});
