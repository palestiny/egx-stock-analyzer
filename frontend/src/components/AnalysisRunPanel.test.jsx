import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AnalysisRunPanel } from "./AnalysisRunPanel";

describe("AnalysisRunPanel", () => {
  it("loads and renders one analysis run", async () => {
    const getAnalysisRun = vi.fn().mockResolvedValue({
      run_id: "run-1",
      created_at: "2026-09-20T08:00:00Z",
      state: "completed",
      snapshots: [
        {
          snapshot_id: "snapshot-1",
          symbol: "EGAL",
          analysis_date: "2026-09-20",
        },
      ],
      next_cursor: null,
    });

    render(<AnalysisRunPanel getAnalysisRun={getAnalysisRun} />);

    fireEvent.change(screen.getByLabelText("Analysis run ID"), {
      target: { value: "run-1" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Load Run" }));

    expect(await screen.findByText("EGAL")).toBeInTheDocument();
    expect(getAnalysisRun).toHaveBeenCalledWith("run-1", {
      pageSize: 50,
      cursor: null,
    });
  });

  it("loads the next snapshot page using the server cursor", async () => {
    const getAnalysisRun = vi
      .fn()
      .mockResolvedValueOnce({
        run_id: "run-1",
        created_at: "2026-09-20T08:00:00Z",
        state: "completed",
        snapshots: [
          {
            snapshot_id: "snapshot-1",
            symbol: "EGAL",
            analysis_date: "2026-09-20",
          },
        ],
        next_cursor: "opaque-cursor",
      })
      .mockResolvedValueOnce({
        run_id: "run-1",
        created_at: "2026-09-20T08:00:00Z",
        state: "completed",
        snapshots: [
          {
            snapshot_id: "snapshot-2",
            symbol: "SVCE",
            analysis_date: "2026-09-20",
          },
        ],
        next_cursor: null,
      });

    render(<AnalysisRunPanel getAnalysisRun={getAnalysisRun} />);

    fireEvent.change(screen.getByLabelText("Analysis run ID"), {
      target: { value: "run-1" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Load Run" }));

    expect(await screen.findByText("EGAL")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Next snapshots" }));

    await waitFor(() => {
      expect(screen.getByText("SVCE")).toBeInTheDocument();
    });
    expect(getAnalysisRun).toHaveBeenLastCalledWith("run-1", {
      pageSize: 50,
      cursor: "opaque-cursor",
    });
  });

  it("renders not-found errors without changing analytical state", async () => {
    const error = Object.assign(new Error("not found"), { status: 404 });
    const getAnalysisRun = vi.fn().mockRejectedValue(error);

    render(<AnalysisRunPanel getAnalysisRun={getAnalysisRun} />);

    fireEvent.change(screen.getByLabelText("Analysis run ID"), {
      target: { value: "missing" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Load Run" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Analysis run was not found.",
    );
  });
});


  it("renders persisted success and failure outcomes", async () => {
    const getAnalysisRun = vi.fn().mockResolvedValue({
      run_id: "run-2",
      created_at: "2026-09-20T08:00:00Z",
      state: "completed_with_errors",
      outcomes_available: true,
      outcomes: [
        {
          symbol: "EGAL",
          state: "success",
          stock_id: "stock-1",
          failure_code: null,
          failure_detail: null,
        },
        {
          symbol: "UNKNOWN",
          state: "failed",
          stock_id: null,
          failure_code: "UNKNOWN_SYMBOL",
          failure_detail: "UNKNOWN",
        },
      ],
      snapshots: [],
      next_cursor: null,
    });

    render(<AnalysisRunPanel getAnalysisRun={getAnalysisRun} initialRunId="run-2" />);

    expect(await screen.findByText("UNKNOWN")).toBeInTheDocument();
    expect(screen.getByText(/UNKNOWN_SYMBOL/)).toBeInTheDocument();
    expect(screen.getByText("EGAL")).toBeInTheDocument();
  });
