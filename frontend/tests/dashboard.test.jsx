import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import App from "../src/App";

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
    vi.restoreAllMocks();
  });

  it("renders the analysis symbol input and action", () => {
    render(<App />);

    expect(screen.getByLabelText(/stock symbol/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /analyze/i })).toBeInTheDocument();
  });

  it("runs analysis and renders a successful result", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue({
        ok: true,
        json: async () => analysis,
      });

    render(<App />);
    fireEvent.change(screen.getByLabelText(/stock symbol/i), {
      target: { value: "egal" },
    });
    fireEvent.click(screen.getByRole("button", { name: /analyze/i }));

    expect(await screen.findByRole("heading", { name: "EGAL" })).toBeInTheDocument();
    expect(screen.getByText("Technical Score")).toBeInTheDocument();
    expect(screen.getByText("Fundamental Score")).toBeInTheDocument();
    expect(screen.getByText("Stock Quality")).toBeInTheDocument();
    expect(screen.getByText("Entry Quality")).toBeInTheDocument();
    expect(screen.getByText("Opportunity")).toBeInTheDocument();
    expect(screen.getByText("buy")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith("/api/v1/analysis/EGAL", {
      method: "POST",
    });
  });

  it("shows a loading state while analysis is running", async () => {
    let resolveRequest;
    const fetchMock = vi.spyOn(globalThis, "fetch").mockReturnValue(
      new Promise((resolve) => {
        resolveRequest = resolve;
      }),
    );

    render(<App />);
    fireEvent.change(screen.getByLabelText(/stock symbol/i), {
      target: { value: "EGAL" },
    });
    fireEvent.click(screen.getByRole("button", { name: /analyze/i }));

    expect(screen.getByText(/running analysis/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /analyze/i })).toBeDisabled();
    expect(fetchMock).toHaveBeenCalledWith("/api/v1/analysis/EGAL", {
      method: "POST",
    });

    resolveRequest({
      ok: true,
      json: async () => analysis,
    });

    await waitFor(() => {
      expect(screen.queryByText(/running analysis/i)).not.toBeInTheDocument();
    });
  });

  it("shows an API error", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("Network error"));

    render(<App />);
    fireEvent.change(screen.getByLabelText(/stock symbol/i), {
      target: { value: "EGAL" },
    });
    fireEvent.click(screen.getByRole("button", { name: /analyze/i }));

    expect(await screen.findByText("Network error")).toBeInTheDocument();
  });

  it("shows a not-found message for a 404 result", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(
      Object.assign(new Error("Analysis execution request failed with status 404"), {
        status: 404,
      }),
    );

    render(<App />);
    fireEvent.change(screen.getByLabelText(/stock symbol/i), {
      target: { value: "EGAL" },
    });
    fireEvent.click(screen.getByRole("button", { name: /analyze/i }));

    expect(await screen.findByText(/stock symbol was not found/i)).toBeInTheDocument();
  });
});
