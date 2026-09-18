import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import App from "../src/App";
import { getAlert, getReport } from "../src/api/analysisApi";

vi.mock("../src/api/analysisApi", () => ({
  getAlert: vi.fn(),
  getReport: vi.fn(),
}));

const report = {
  symbol: "EGAL",
  analysis_date: "2026-09-18",
  current_price: "350.5",
  technical_score: 72,
  fundamental_score: 68,
  stock_quality: 70,
  entry_quality: 65,
  opportunity: "watch",
  nearest_support: "340.0",
  nearest_resistance: "365.0",
  trend: "uptrend",
  momentum: "positive",
  volume: "normal",
  profitability: "strong",
  liquidity: "adequate",
  growth: "positive",
};

describe("Dashboard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the analysis symbol input and action", () => {
    render(<App />);
    expect(screen.getByLabelText("Stock Symbol")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Load Analysis" })).toBeInTheDocument();
  });

  it("loads and renders the latest report and alert", async () => {
    getReport.mockResolvedValue(report);
    getAlert.mockResolvedValue({ classification: "BUY", stock_quality_score: 85, entry_quality_score: 80 });

    render(<App />);
    fireEvent.change(screen.getByLabelText("Stock Symbol"), { target: { value: "egal" } });
    fireEvent.click(screen.getByRole("button", { name: "Load Analysis" }));

    await waitFor(() => expect(screen.getByRole("heading", { name: "EGAL" })).toBeInTheDocument());
    expect(getReport).toHaveBeenCalledWith("EGAL");
    expect(getAlert).toHaveBeenCalledWith("EGAL");
    expect(screen.getByText(/Current price:\s*350\.5/)).toBeInTheDocument();
    expect(screen.getByText("BUY")).toBeInTheDocument();
  });

  it("shows a loading state while the report request is pending", async () => {
    let resolveReport;
    getReport.mockReturnValue(new Promise((resolve) => { resolveReport = resolve; }));

    render(<App />);
    fireEvent.change(screen.getByLabelText("Stock Symbol"), { target: { value: "EGAL" } });
    fireEvent.click(screen.getByRole("button", { name: "Load Analysis" }));

    expect(screen.getByText("Loading latest analysis...")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Loading..." })).toBeDisabled();

    resolveReport(report);
    await waitFor(() => expect(screen.getByRole("heading", { name: "EGAL" })).toBeInTheDocument());
  });

  it("treats an alert 404 as no alert candidate", async () => {
    getReport.mockResolvedValue(report);
    getAlert.mockRejectedValue(Object.assign(new Error("not found"), { status: 404 }));

    render(<App />);
    fireEvent.change(screen.getByLabelText("Stock Symbol"), { target: { value: "EGAL" } });
    fireEvent.click(screen.getByRole("button", { name: "Load Analysis" }));

    expect(await screen.findByText("No alert candidate for the latest analysis.")).toBeInTheDocument();
  });

  it("shows a not-found message when the report is unavailable", async () => {
    getReport.mockRejectedValue(Object.assign(new Error("Report request failed with status 404"), { status: 404 }));

    render(<App />);
    fireEvent.change(screen.getByLabelText("Stock Symbol"), { target: { value: "UNKNOWN" } });
    fireEvent.click(screen.getByRole("button", { name: "Load Analysis" }));

    expect(await screen.findByText("No stored analysis report was found.")).toBeInTheDocument();
  });
});