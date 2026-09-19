import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ScheduledWorkflowHistoryPanel } from "./ScheduledWorkflowHistoryPanel";

describe("ScheduledWorkflowHistoryPanel", () => {
  it("loads and renders persisted lifecycle history", async () => {
    const getHistory = vi.fn().mockResolvedValue({
      execution_id: "execution-1",
      occurrence_id: "occ-45",
      history: [
        {
          sequence: 1,
          from_state: null,
          to_state: "created",
          occurred_at: "2026-09-19T10:00:00Z",
          reason: null,
        },
        {
          sequence: 2,
          from_state: "created",
          to_state: "running",
          occurred_at: "2026-09-19T10:01:00Z",
          reason: "started",
        },
      ],
      has_more: false,
      next_cursor: null,
    });

    render(
      <ScheduledWorkflowHistoryPanel
        execution={{ id: "execution-1" }}
        getHistory={getHistory}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "History" }));

    await waitFor(() => {
      expect(screen.getByText("started")).toBeInTheDocument();
    });
    expect(screen.getByText("created → running")).toBeInTheDocument();
    expect(getHistory).toHaveBeenCalledWith("execution-1", { pageSize: 50 });
  });

  it("renders an empty-history state", async () => {
    const getHistory = vi.fn().mockResolvedValue({
      execution_id: "execution-1",
      occurrence_id: "occ-45",
      history: [],
      has_more: false,
      next_cursor: null,
    });

    render(
      <ScheduledWorkflowHistoryPanel
        execution={{ id: "execution-1" }}
        getHistory={getHistory}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "History" }));

    await waitFor(() => {
      expect(
        screen.getByText("No lifecycle history is available."),
      ).toBeInTheDocument();
    });
  });

  it("renders a not-found error", async () => {
    const error = Object.assign(new Error("not found"), { status: 404 });
    const getHistory = vi.fn().mockRejectedValue(error);

    render(
      <ScheduledWorkflowHistoryPanel
        execution={{ id: "execution-1" }}
        getHistory={getHistory}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "History" }));

    await waitFor(() => {
      expect(
        screen.getByText("Workflow execution history was not found."),
      ).toBeInTheDocument();
    });
  });

  it("loads the next page and appends history", async () => {
    const getHistory = vi.fn()
      .mockResolvedValueOnce({
        execution_id: "execution-1",
        occurrence_id: "occ-45",
        history: [
          {
            sequence: 1,
            from_state: null,
            to_state: "created",
            occurred_at: "2026-09-19T10:00:00Z",
            reason: null,
          },
        ],
        has_more: true,
        next_cursor: "MQ",
      })
      .mockResolvedValueOnce({
        execution_id: "execution-1",
        occurrence_id: "occ-45",
        history: [
          {
            sequence: 2,
            from_state: "created",
            to_state: "running",
            occurred_at: "2026-09-19T10:01:00Z",
            reason: "started",
          },
        ],
        has_more: false,
        next_cursor: null,
      });

    render(
      <ScheduledWorkflowHistoryPanel
        execution={{ id: "execution-1" }}
        getHistory={getHistory}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "History" }));
    await waitFor(() => {
      expect(screen.getByText("created → running")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "Load more" }));

    await waitFor(() => {
      expect(screen.getByText("created → running")).toBeInTheDocument();
    });
    expect(getHistory).toHaveBeenLastCalledWith("execution-1", {
      pageSize: 50,
      cursor: "MQ",
    });
    expect(screen.queryByRole("button", { name: "Load more" })).not.toBeInTheDocument();
  });


  it("passes selected state filters and keeps them for pagination", async () => {
    const getHistory = vi.fn()
      .mockResolvedValueOnce({
        execution_id: "execution-1",
        occurrence_id: "occ-45",
        history: [
          {
            sequence: 3,
            from_state: "running",
            to_state: "completed",
            occurred_at: "2026-09-19T10:02:00Z",
            reason: "finished",
          },
        ],
        has_more: true,
        next_cursor: "eyJzZXF1ZW5jZSI6M30",
      })
      .mockResolvedValueOnce({
        execution_id: "execution-1",
        occurrence_id: "occ-45",
        history: [],
        has_more: false,
        next_cursor: null,
      });

    render(
      <ScheduledWorkflowHistoryPanel
        execution={{ id: "execution-1" }}
        getHistory={getHistory}
      />,
    );

    fireEvent.change(screen.getByRole("combobox", { name: "From state" }), {
      target: { value: "running" },
    });
    fireEvent.change(screen.getByRole("combobox", { name: "To state" }), {
      target: { value: "completed" },
    });
    fireEvent.click(screen.getByRole("button", { name: "History" }));

    await waitFor(() => {
      expect(screen.getByText("running → completed")).toBeInTheDocument();
    });
    expect(getHistory).toHaveBeenCalledWith("execution-1", {
      pageSize: 50,
      fromState: "running",
      toState: "completed",
    });

    fireEvent.click(screen.getByRole("button", { name: "Load more" }));

    await waitFor(() => {
      expect(screen.getByText("No lifecycle history is available.")).toBeInTheDocument();
    });
    expect(getHistory).toHaveBeenLastCalledWith("execution-1", {
      pageSize: 50,
      cursor: "eyJzZXF1ZW5jZSI6M30",
      fromState: "running",
      toState: "completed",
    });
  });

});
