import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ScheduledWorkflowHistoryPanel } from "./ScheduledWorkflowHistoryPanel";

describe("ScheduledWorkflowHistoryPanel", () => {
  it("loads and renders persisted lifecycle history", async () => {
    const user = userEvent.setup();
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
    });

    render(
      <ScheduledWorkflowHistoryPanel
        execution={{ id: "execution-1" }}
        getHistory={getHistory}
      />,
    );

    await user.click(screen.getByRole("button", { name: "History" }));

    await waitFor(() => {
      expect(screen.getByText("started")).toBeInTheDocument();
    });
    expect(screen.getByText("created → running")).toBeInTheDocument();
    expect(getHistory).toHaveBeenCalledWith("execution-1");
  });

  it("renders an empty-history state", async () => {
    const user = userEvent.setup();
    const getHistory = vi.fn().mockResolvedValue({
      execution_id: "execution-1",
      occurrence_id: "occ-45",
      history: [],
    });

    render(
      <ScheduledWorkflowHistoryPanel
        execution={{ id: "execution-1" }}
        getHistory={getHistory}
      />,
    );

    await user.click(screen.getByRole("button", { name: "History" }));

    await waitFor(() => {
      expect(
        screen.getByText("No lifecycle history is available."),
      ).toBeInTheDocument();
    });
  });

  it("renders a not-found error", async () => {
    const user = userEvent.setup();
    const error = Object.assign(new Error("not found"), { status: 404 });
    const getHistory = vi.fn().mockRejectedValue(error);

    render(
      <ScheduledWorkflowHistoryPanel
        execution={{ id: "execution-1" }}
        getHistory={getHistory}
      />,
    );

    await user.click(screen.getByRole("button", { name: "History" }));

    await waitFor(() => {
      expect(
        screen.getByText("Workflow execution history was not found."),
      ).toBeInTheDocument();
    });
  });
});
