import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import App from "../src/App";
import { getAlert, getAnalysisComparison, getAnalysisHistory, getCurrentIdentity, getMarketOpportunities, getReport, getScheduledWorkflowExecutions, getSnapshotPerformance, recoverScheduledWorkflowExecution } from "../src/api/analysisApi";
import { clearSessionToken, setSessionToken } from "../src/auth/session";

vi.mock("../src/api/analysisApi", () => ({
  getAlert: vi.fn(),
  getCurrentIdentity: vi.fn(),
  getAnalysisHistory: vi.fn(),
  getAnalysisComparison: vi.fn(),
  getSnapshotPerformance: vi.fn(),
  getMarketOpportunities: vi.fn(),
  getReport: vi.fn(),
  getScheduledWorkflowExecutions: vi.fn(),
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
    expect(screen.getByText("interrupted")).toBeInTheDocument();
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
    expect(screen.getByRole("button", { name: "Loading..." })).toBeDisabled();

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
