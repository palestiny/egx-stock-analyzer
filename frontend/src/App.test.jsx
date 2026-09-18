import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";

import App from "./App";

vi.mock("./api/analysisApi", () => ({
  getReport: vi.fn(),
  getAlert: vi.fn(),
}));

import { getAlert, getReport } from "./api/analysisApi";

describe("App", () => {
  test("loads and displays report and alert data", async () => {
    getReport.mockResolvedValue({
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
    });
    getAlert.mockResolvedValue({
      classification: "buy",
      stock_quality_score: 85,
      entry_quality_score: 80,
    });

    render(<App />);
    fireEvent.change(screen.getByLabelText("Stock Symbol"), {
      target: { value: "egal" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Load Analysis" }));

    expect(getReport).toHaveBeenCalledWith("EGAL");

    await waitFor(() => {
      expect(screen.getByText("350.5")).toBeInTheDocument();
      expect(screen.getByText("BUY")).toBeInTheDocument();
    });
  });

  test("treats alert 404 as no alert candidate", async () => {
    getReport.mockResolvedValue({
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
    });
    getAlert.mockRejectedValue(Object.assign(new Error("not found"), { status: 404 }));

    render(<App />);
    fireEvent.change(screen.getByLabelText("Stock Symbol"), {
      target: { value: "EGAL" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Load Analysis" }));

    await waitFor(() => {
      expect(screen.getByText("No alert candidate for the latest analysis.")).toBeInTheDocument();
    });
  });

  test("shows a report not-found error", async () => {
    getReport.mockRejectedValue(Object.assign(new Error("not found"), { status: 404 }));

    render(<App />);
    fireEvent.change(screen.getByLabelText("Stock Symbol"), {
      target: { value: "UNKNOWN" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Load Analysis" }));

    await waitFor(() => {
      expect(screen.getByText("No stored analysis report was found.")).toBeInTheDocument();
    });
  });
});
