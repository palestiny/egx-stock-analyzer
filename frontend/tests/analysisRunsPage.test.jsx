import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AnalysisRunsPage } from "../src/components/AnalysisRunsPage";

const RUN_A = "00000000-0000-0000-0000-000000000001";
const RUN_B = "00000000-0000-0000-0000-000000000002";

function page(items, nextCursor = null) {
  return { items, has_more: nextCursor !== null, next_cursor: nextCursor };
}

describe("AnalysisRunsPage", () => {
  it("renders the first page and sends the selected server-side state filter", async () => {
    const getAnalysisRuns = vi.fn()
      .mockResolvedValueOnce(page([
        { run_id: RUN_A, created_at: "2026-09-20T10:00:00Z", state: "completed" },
      ]));

    render(<AnalysisRunsPage getAnalysisRuns={getAnalysisRuns} onSelectRun={vi.fn()} onBack={vi.fn()} />);

    expect(await screen.findByText(/00000000-0000-0000-0000-000000000001/)).toBeInTheDocument();
    expect(getAnalysisRuns).toHaveBeenCalledWith({
      state: undefined,
      pageSize: 50,
      cursor: null,
    });

    fireEvent.change(screen.getByLabelText("State"), { target: { value: "failed" } });

    await waitFor(() => expect(getAnalysisRuns).toHaveBeenLastCalledWith({
      state: "failed",
      pageSize: 50,
      cursor: null,
    }));
  });

  it("uses the returned opaque cursor for the next page", async () => {
    const getAnalysisRuns = vi.fn()
      .mockResolvedValueOnce(page([
        { run_id: RUN_A, created_at: "2026-09-20T10:00:00Z", state: "completed" },
      ], "opaque-next"))
      .mockResolvedValueOnce(page([
        { run_id: RUN_B, created_at: "2026-09-19T10:00:00Z", state: "failed" },
      ]));

    render(<AnalysisRunsPage getAnalysisRuns={getAnalysisRuns} onSelectRun={vi.fn()} onBack={vi.fn()} />);

    expect(await screen.findByText(new RegExp(RUN_A))).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Next page" }));

    await waitFor(() => expect(getAnalysisRuns).toHaveBeenLastCalledWith({
      state: undefined,
      pageSize: 50,
      cursor: "opaque-next",
    }));
    expect(await screen.findByText(new RegExp(RUN_B))).toBeInTheDocument();
  });

  it("renders empty and no-more-pages states", async () => {
    const getAnalysisRuns = vi.fn().mockResolvedValue(page([]));

    render(<AnalysisRunsPage getAnalysisRuns={getAnalysisRuns} onSelectRun={vi.fn()} onBack={vi.fn()} />);

    expect(await screen.findByText("No analysis runs matched the selected filter.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Next page" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "First page" })).toBeDisabled();
  });

  it("maps authentication, authorization, and invalid-query errors safely", async () => {
    const getAnalysisRuns = vi.fn().mockRejectedValue({ status: 400 });

    render(<AnalysisRunsPage getAnalysisRuns={getAnalysisRuns} onSelectRun={vi.fn()} onBack={vi.fn()} />);

    expect(await screen.findByText("The run discovery query is invalid.")).toBeInTheDocument();
  });

  it("navigates to the selected run without changing the run metadata", async () => {
    const getAnalysisRuns = vi.fn().mockResolvedValue(page([
      { run_id: RUN_A, created_at: "2026-09-20T10:00:00Z", state: "completed" },
    ]));
    const onSelectRun = vi.fn();

    render(<AnalysisRunsPage getAnalysisRuns={getAnalysisRuns} onSelectRun={onSelectRun} onBack={vi.fn()} />);

    fireEvent.click(await screen.findByRole("button", { name: /completed/i }));
    expect(onSelectRun).toHaveBeenCalledWith(RUN_A);
  });
});
