import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import App from "../src/App";
import { getAlert, getAnalysisComparison, getAnalysisHistory, getCurrentIdentity, getMarketBreadthStress, getMarketOpportunities, getReport, getStockRegime, getTechnicalScanner, getScheduledWorkflowExecutions, getSnapshotPerformance, recoverScheduledWorkflowExecution } from "../src/api/analysisApi";
import { clearSessionToken, setSessionToken } from "../src/auth/session";

vi.mock("../src/api/analysisApi", () => ({
  getAlert: vi.fn(),
  getCurrentIdentity: vi.fn(),
  getAnalysisHistory: vi.fn(),
  getAnalysisRun: vi.fn(),
  getAnalysisComparison: vi.fn(),
  getSnapshotPerformance: vi.fn(),
  getMarketBreadthStress: vi.fn(),
  getMarketOpportunities: vi.fn(),
  getStockRegime: vi.fn(),
  getReport: vi.fn(),
  getTechnicalScanner: vi.fn(),
  getScheduledWorkflowExecutions: vi.fn(),
  getScheduledWorkflowExecutionHistory: vi.fn(),
  recoverScheduledWorkflowExecution: vi.fn(),
  getUserAuditHistory: vi.fn(),
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
    clearSessionToken();
    setSessionToken("test-token");
    getCurrentIdentity.mockResolvedValue({
      subject: "operator",
      user_id: "00000000-0000-0000-0000-000000000001",
      status: "active",
    });
  });

  async function renderAuthenticatedApp() {
    render(<App />);
    await waitFor(() =>
      expect(screen.getByLabelText("Stock Symbol")).toBeInTheDocument(),
    );
  }

  it("renders the analysis symbol input and action", async () => {
    await renderAuthenticatedApp();
    expect(screen.getByLabelText("Stock Symbol")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Load Analysis" })).toBeInTheDocument();
  });

  it("loads and renders the latest report and alert", async () => {
    getReport.mockResolvedValue(report);
    getAlert.mockResolvedValue({ classification: "BUY", stock_quality_score: 85, entry_quality_score: 80 });

    await renderAuthenticatedApp();
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

    await renderAuthenticatedApp();
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

    await renderAuthenticatedApp();
    fireEvent.change(screen.getByLabelText("Stock Symbol"), { target: { value: "EGAL" } });
    fireEvent.click(screen.getByRole("button", { name: "Load Analysis" }));

    expect(await screen.findByRole("heading", { name: "EGAL" })).toBeInTheDocument();

    const beforeSelect = screen.getByLabelText("Before");
    const afterSelect = screen.getByLabelText("After");
    fireEvent.change(beforeSelect, { target: { value: "snapshot-1" } });
    fireEvent.change(afterSelect, { target: { value: "snapshot-2" } });
    fireEvent.click(screen.getByRole("button", { name: "Compare" }));

    const performancePanel = await screen.findByLabelText("historical performance");
    expect(performancePanel).toHaveTextContent("Price Change");
    expect(performancePanel).toHaveTextContent("25");
    expect(getSnapshotPerformance).toHaveBeenCalledWith("EGAL", "snapshot-1", "snapshot-2");
  });

  it("shows a historical-analysis error without hiding the latest report", async () => {
    getReport.mockResolvedValue(report);
    getAlert.mockResolvedValue({ classification: "BUY", stock_quality_score: 85, entry_quality_score: 80 });
    getAnalysisHistory.mockRejectedValue(new Error("Analysis history request failed"));

    await renderAuthenticatedApp();
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

    await renderAuthenticatedApp();
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


  it("loads trend and risk diagnostics for an opportunity without changing its ranking", async () => {
    getMarketOpportunities.mockResolvedValue({
      opportunities: [{
        symbol: "EGAL",
        classification: "buy",
        stock_quality: 6,
        entry_quality: 2,
        technical_score: 4,
        fundamental_score: 2,
      }],
      missing_symbols: [],
    });
    getStockRegime.mockResolvedValue({
      symbol: "EGAL",
      trend: "uptrend",
      volatility: "medium",
      latest_close: 375,
      sma_20: 370,
      sma_50: 355,
      annualized_realized_volatility: 0.28,
      drawdown_from_observed_peak: -0.06,
      valid_observation_count: 90,
      latest_observation_date: "2026-10-19",
      is_trading_signal: false,
    });

    await renderAuthenticatedApp();
    fireEvent.click(screen.getByRole("button", { name: "Load Opportunities" }));
    const row = (await screen.findByText("EGAL")).closest(".detail-row");
    fireEvent.click(within(row).getByRole("button", { name: "Load trend & risk" }));

    await waitFor(() => expect(getStockRegime).toHaveBeenCalledWith("EGAL"));
    expect(await within(row).findByText(/Trend: uptrend · Risk: medium/)).toBeInTheDocument();
    expect(row).toHaveTextContent("Realized volatility: 28.00%");
    expect(row).toHaveTextContent("Data through 2026-10-19");
    expect(row).toHaveTextContent("Diagnostic only, not a trading signal.");
    expect(row).toHaveTextContent("Stock 6");
  });

  it("renders market breadth stress with coverage and missing data context", async () => {
    getMarketBreadthStress.mockResolvedValue({
      requested_symbols: 3,
      analyzed_symbols: 2,
      missing_symbols: ["COMI"],
      coverage_percent: "66.67",
      uptrend_count: 1,
      downtrend_count: 1,
      positive_momentum_count: 1,
      negative_momentum_count: 1,
      above_average_volume_count: 1,
      negative_momentum_with_above_average_volume_count: 1,
      stress_components: {
        downtrend: { count: 1, share_percent: "50.00", weight_points: "25.00" },
        negative_momentum: { count: 1, share_percent: "50.00", weight_points: "20.00" },
        negative_momentum_with_above_average_volume: { count: 1, share_percent: "50.00", weight_points: "5.00" },
      },
      analysis_date_status: "PARTIAL",
      latest_analysis_date: "2026-10-27",
      undated_symbols: ["IEEC"],
      bullish_breadth_percent: "50.00",
      bearish_pressure_percent: "50.00",
      stress_score: 50,
      stress_level: "elevated",
      data_status: "LATEST_SAVED_ANALYSIS_SNAPSHOT",
      methodology: "Heuristic based on saved trends and momentum.",
      is_trading_signal: false,
    });

    await renderAuthenticatedApp();
    fireEvent.change(screen.getByLabelText("Market breadth symbols"), { target: { value: "egal,ieec,comi" } });
    fireEvent.click(screen.getByRole("button", { name: "Calculate Market Pulse" }));

    const panel = await screen.findByLabelText("market breadth and stress pulse");
    expect(panel).toHaveTextContent("50 / elevated");
    expect(panel).toHaveTextContent("66.67%");
    expect(panel).toHaveTextContent("Missing saved analyses: COMI");
    expect(panel).toHaveTextContent("LATEST_SAVED_ANALYSIS_SNAPSHOT");
    expect(panel).toHaveTextContent("Snapshot date status");
    expect(panel).toHaveTextContent("PARTIAL");
    expect(panel).toHaveTextContent("Latest saved analysis date");
    expect(panel).toHaveTextContent("2026-10-27");
    expect(panel).toHaveTextContent("Saved analyses with unknown dates: IEEC");
    expect(panel).toHaveTextContent("Downtrend");
    expect(panel).toHaveTextContent("25.00 pts");
    expect(panel).toHaveTextContent("Negative momentum + above-average volume");
    expect(getMarketBreadthStress).toHaveBeenCalledWith(["EGAL", "IEEC", "COMI"]);
  });

  it("loads and renders the pre-breakout momentum-volume watchlist", async () => {
    getTechnicalScanner.mockResolvedValue({
      scanner_id: "pre-breakout-momentum-volume",
      evaluated_symbols: 2,
      data_status: "HISTORICAL_ANALYSIS_RESULT",
      matches: [{
        symbol: "COMI",
        score: 82,
        criteria: ["uptrend", "positive_momentum", "above_average_volume", "volume_expansion", "near_resistance"],
        momentum_percent: 4.2,
        volume_ratio: 1.8,
        resistance_price: 100,
        distance_to_resistance_percent: -4,
      }],
    });

    await renderAuthenticatedApp();
    fireEvent.change(screen.getByLabelText("Pre-breakout symbols"), { target: { value: "comi, egal" } });
    fireEvent.click(screen.getByRole("button", { name: "Scan Pre-breakout" }));

    const panel = await screen.findByRole("region", { name: "pre-breakout momentum volume watchlist" });
    expect(panel).toHaveTextContent("COMI");
    expect(panel).toHaveTextContent("Momentum 4.20%");
    expect(panel).toHaveTextContent("Volume 1.80×");
    expect(panel).toHaveTextContent("Resistance 100");
    expect(panel).toHaveTextContent("Distance -4.00%");
    expect(getTechnicalScanner).toHaveBeenCalledWith(["COMI", "EGAL"], "pre-breakout-momentum-volume");
    expect(panel).toHaveTextContent("Watchlist only, not a buy signal.");
  });

  it("loads and renders scheduled workflow executions in API order", async () => {
    getScheduledWorkflowExecutions.mockResolvedValue({
      items: [
        {
          id: "workflow-2",
          occurrence_id: "occ-2",
          state: "completed",
          created_at: "2026-09-19T10:00:00Z",
          updated_at: "2026-09-19T10:01:00Z",
          analysis_state: "completed",
          delivery_state: "completed",
        },
        {
          id: "workflow-1",
          occurrence_id: "occ-1",
          state: "interrupted",
          created_at: "2026-09-18T10:00:00Z",
          updated_at: "2026-09-18T10:02:00Z",
          analysis_state: "completed",
          delivery_state: "failed",
        },
      ],
    });

    await renderAuthenticatedApp();
    fireEvent.click(screen.getByRole("button", { name: "Load Workflows" }));

    const firstOccurrence = await screen.findByText(/occ-2/);
    const rows = screen.getAllByText(/occ-/).map((item) => item.textContent);
    expect(rows[0]).toContain("occ-2");
    expect(firstOccurrence).toBeInTheDocument();
    expect(screen.getAllByText("interrupted").length).toBeGreaterThan(0);
    expect(getScheduledWorkflowExecutions).toHaveBeenCalledWith(undefined);
  });

  it("passes the submitted occurrence filter to the workflow API", async () => {
    getScheduledWorkflowExecutions.mockResolvedValue({ items: [] });

    await renderAuthenticatedApp();
    fireEvent.change(screen.getByLabelText("Occurrence ID"), { target: { value: "occ-42" } });
    fireEvent.click(screen.getByRole("button", { name: "Load Workflows" }));

    await waitFor(() => expect(getScheduledWorkflowExecutions).toHaveBeenCalledWith("occ-42"));
    expect(screen.getByText("No scheduled workflow executions were found.")).toBeInTheDocument();
  });

  it("shows the workflow visibility unavailable state for HTTP 503", async () => {
    getScheduledWorkflowExecutions.mockRejectedValue(
      Object.assign(new Error("Scheduled workflow executions request failed with status 503"), { status: 503 }),
    );

    await renderAuthenticatedApp();
    fireEvent.click(screen.getByRole("button", { name: "Load Workflows" }));

    expect(await screen.findByText("Scheduled workflow visibility is not configured.")).toBeInTheDocument();
  });

  it("shows a loading state while the report request is pending", async () => {
    let resolveReport;
    getReport.mockReturnValue(new Promise((resolve) => { resolveReport = resolve; }));

    await renderAuthenticatedApp();
    fireEvent.change(screen.getByLabelText("Stock Symbol"), { target: { value: "EGAL" } });
    fireEvent.click(screen.getByRole("button", { name: "Load Analysis" }));

    expect(screen.getByText("Loading latest analysis...")).toBeInTheDocument();
    expect(within(screen.getByLabelText("Stock Symbol").closest("form")).getByRole("button", { name: "Loading..." })).toBeDisabled();

    resolveReport(report);
    await waitFor(() => expect(screen.getByRole("heading", { name: "EGAL" })).toBeInTheDocument());
  });

  it("treats an alert 404 as no alert candidate", async () => {
    getReport.mockResolvedValue(report);
    getAlert.mockRejectedValue(Object.assign(new Error("not found"), { status: 404 }));

    await renderAuthenticatedApp();
    fireEvent.change(screen.getByLabelText("Stock Symbol"), { target: { value: "EGAL" } });
    fireEvent.click(screen.getByRole("button", { name: "Load Analysis" }));

    expect(await screen.findByText("No alert candidate for the latest analysis.")).toBeInTheDocument();
  });

  it("shows a not-found message when the report is unavailable", async () => {
    getReport.mockRejectedValue(Object.assign(new Error("Report request failed with status 404"), { status: 404 }));

    await renderAuthenticatedApp();
    fireEvent.change(screen.getByLabelText("Stock Symbol"), { target: { value: "UNKNOWN" } });
    fireEvent.click(screen.getByRole("button", { name: "Load Analysis" }));

    expect(await screen.findByText("No stored analysis report was found.")).toBeInTheDocument();
  });


  it("shows Recover only for interrupted workflows and updates the row from recovery response", async () => {
    getScheduledWorkflowExecutions.mockResolvedValue({
      items: [
        {
          id: "workflow-completed",
          occurrence_id: "occ-completed",
          state: "completed",
          created_at: "2026-09-19T10:00:00Z",
          updated_at: "2026-09-19T10:01:00Z",
          analysis_state: "completed",
          delivery_state: "completed",
        },
        {
          id: "workflow-interrupted",
          occurrence_id: "occ-interrupted",
          state: "interrupted",
          created_at: "2026-09-18T10:00:00Z",
          updated_at: "2026-09-18T10:02:00Z",
          analysis_state: "completed",
          delivery_state: "failed",
        },
      ],
    });
    recoverScheduledWorkflowExecution.mockResolvedValue({
      id: "workflow-interrupted",
      occurrence_id: "occ-interrupted",
      state: "completed",
      created_at: "2026-09-18T10:00:00Z",
      updated_at: "2026-09-19T11:00:00Z",
      analysis_state: "completed",
      delivery_state: "completed",
    });

    await renderAuthenticatedApp();
    fireEvent.click(screen.getByRole("button", { name: "Load Workflows" }));

    const recover = await screen.findByRole("button", { name: "Recover" });
    expect(recover).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Recover" })).toHaveLength(1);

    fireEvent.click(recover);

    await waitFor(() => {
      expect(recoverScheduledWorkflowExecution).toHaveBeenCalledWith("workflow-interrupted");
    });
    const workflowRows = screen.getAllByText(/occ-/).map((item) => item.closest(".detail-row"));
    expect(workflowRows[1]).toHaveTextContent("completed");
    expect(screen.queryByRole("button", { name: "Recover" })).not.toBeInTheDocument();
  });

  it("shows an explicit recovery error for a non-recoverable workflow", async () => {
    getScheduledWorkflowExecutions.mockResolvedValue({
      items: [{
        id: "workflow-interrupted",
        occurrence_id: "occ-interrupted",
        state: "interrupted",
        created_at: "2026-09-18T10:00:00Z",
        updated_at: "2026-09-18T10:02:00Z",
        analysis_state: "completed",
        delivery_state: "failed",
      }],
    });
    recoverScheduledWorkflowExecution.mockRejectedValue(
      Object.assign(new Error("conflict"), { status: 409 }),
    );

    await renderAuthenticatedApp();
    fireEvent.click(screen.getByRole("button", { name: "Load Workflows" }));
    fireEvent.click(await screen.findByRole("button", { name: "Recover" }));

    expect(await screen.findByText("Workflow execution is no longer recoverable.")).toBeInTheDocument();
  });

});
