import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import App from "../src/App";
import { getAlert, getAnalysisComparison, getAnalysisHistory, getMarketOpportunities, getReport, getSnapshotPerformance } from "../src/api/analysisApi";

vi.mock("../src/api/analysisApi", () => ({
  getAlert: vi.fn(),
  getAnalysisHistory: vi.fn(),
  getAnalysisComparison: vi.fn(),
  getSnapshotPerformance: vi.fn(),
  getMarketOpportunities: vi.fn(),
  getReport: vi.fn(),
}));

const report = {
  symbol: "EGAL",
  analysis_date: "2026-09-18",
  current_price: 350.5,
  technical_score: 72,
  fundamental_score: 68,
  stock_quality: 70,
  entry_quality: 65,
  opportunity: "watch",
  nearest_support: 340.0,
  nearest_resistance: 365.0,
  trend: "uptrend",
  momentum: "positive",
  volume: "normal",
  profitability: "strong",
  liquidity: "adequate",
  growth: "positive",
  fundamental_period_end: "2026-06-30",
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
    expect(screen.getByText("350.5")).toBeInTheDocument();
    expect(screen.getByText("BUY")).toBeInTheDocument();
  });

  it("loads and renders historical analysis snapshots", async () => {
    getReport.mockResolvedValue(report);
    getAlert.mockResolvedValue({ classification: "BUY", stock_quality_score: 85, entry_quality_score: 80 });
    getAnalysisHistory.mockResolvedValue({
      symbol: "EGAL",
      items: [
        {
          snapshot_id: "snapshot-2",
          report: {
            ...report,
            analysis_date: "2026-09-18",
            opportunity: "buy",
            stock_quality: 72,
            entry_quality: 66,
            current_price: 350.5,
          },
        },
        {
          snapshot_id: "snapshot-1",
          report: {
            ...report,
            analysis_date: "2026-09-16",
            opportunity: "watch",
            stock_quality: 68,
            entry_quality: 61,
            current_price: 344.0,
          },
        },
      ],
    });

    render(<App />);
    fireEvent.change(screen.getByLabelText("Stock Symbol"), { target: { value: "egal" } });
    fireEvent.click(screen.getByRole("button", { name: "Load Analysis" }));

    expect(await screen.findByText("Stock 72")).toBeInTheDocument();
    expect(screen.getAllByText("2026-09-18").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("2026-09-16").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Stock 72")).toBeInTheDocument();
    expect(screen.getByText("Entry 61")).toBeInTheDocument();
    expect(getAnalysisHistory).toHaveBeenCalledWith("EGAL");
  });

  it("loads and renders historical price performance for a selected comparison", async () => {
    getReport.mockResolvedValue(report);
    getAlert.mockResolvedValue({ classification: "BUY", stock_quality_score: 85, entry_quality_score: 80 });
    getAnalysisHistory.mockResolvedValue({
      symbol: "EGAL",
      items: [
        { snapshot_id: "snapshot-2", report: { ...report, analysis_date: "2026-09-18", current_price: 125 } },
        { snapshot_id: "snapshot-1", report: { ...report, analysis_date: "2026-09-16", current_price: 100 } },
      ],
    });
    getAnalysisComparison.mockResolvedValue({
      symbol: "EGAL",
      deltas: {
        technical_score: 1,
        fundamental_score: 1,
        stock_quality: 2,
        entry_quality: 1,
        current_price: 25,
        nearest_support: null,
        nearest_resistance: null,
      },
      classification_changed: false,
    });
    getSnapshotPerformance.mockResolvedValue({
      symbol: "EGAL",
      metrics: { price_change: 25, price_change_percent: 25 },
    });

    render(<App />);
    fireEvent.change(screen.getByLabelText("Stock Symbol"), { target: { value: "EGAL" } });
    fireEvent.click(screen.getByRole("button", { name: "Load Analysis" }));

    expect(await screen.findByText("Stock 70")).toBeInTheDocument();

    const selects = screen.getAllByRole("combobox");
    fireEvent.change(selects[0], { target: { value: "snapshot-1" } });
    fireEvent.change(selects[1], { target: { value: "snapshot-2" } });
    fireEvent.click(screen.getByRole("button", { name: "Compare" }));

    expect(await screen.findByText("25", { selector: "strong" })).toBeInTheDocument();
    expect(getSnapshotPerformance).toHaveBeenCalledWith("EGAL", "snapshot-1", "snapshot-2");
  });

  it("shows a historical-analysis error without hiding the latest report", async () => {
    getReport.mockResolvedValue(report);
    getAlert.mockResolvedValue({ classification: "BUY", stock_quality_score: 85, entry_quality_score: 80 });
    getAnalysisHistory.mockRejectedValue(new Error("Analysis history request failed"));

    render(<App />);
    fireEvent.change(screen.getByLabelText("Stock Symbol"), { target: { value: "EGAL" } });
    fireEvent.click(screen.getByRole("button", { name: "Load Analysis" }));

    expect(await screen.findByRole("heading", { name: "EGAL" })).toBeInTheDocument();
    expect(screen.getByText("Analysis history request failed")).toBeInTheDocument();
  });

  it("loads and renders the market opportunity view", async () => {
    getMarketOpportunities.mockResolvedValue({
      opportunities: [
        {
          symbol: "EGAL",
          classification: "buy",
          stock_quality: 6,
          entry_quality: 2,
          technical_score: 4,
          fundamental_score: 2,
        },
      ],
      missing_symbols: ["IEEC"],
    });

    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "Load Opportunities" }));

    const symbol = await screen.findByText("EGAL");
    const row = symbol.closest(".detail-row");
    expect(row).not.toBeNull();
    expect(row).toHaveTextContent("buy");
    expect(row).toHaveTextContent("Stock 6");
    expect(row).toHaveTextContent("Entry 2");
    expect(row).toHaveTextContent("Technical 4");
    expect(row).toHaveTextContent("Fundamental 2");
    expect(screen.getByText("Missing stored results: IEEC")).toBeInTheDocument();
    expect(getMarketOpportunities).toHaveBeenCalledWith(["EGAL", "IEEC", "COMI"]);
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
