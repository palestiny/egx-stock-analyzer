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

  it("renders a successful analysis result", async () => {
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
    expect(fetchMock).toHaveBeenCalledWith("/api/v1/analysis/EGAL");
  });

  it("shows a loading state while the request is pending", async () => {
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

    expect(screen.getByText(/loading/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /analyze/i })).toBeDisabled();
    expect(fetchMock).toHaveBeenCalledWith("/api/v1/analysis/EGAL");

    resolveRequest({
      ok: true,
      json: async () => analysis,
    });

    await waitFor(() => {
      expect(screen.queryByText(/loading/i)).not.toBeInTheDocument();
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
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: false,
      status: 404,
    });

    render(<App />);
    fireEvent.change(screen.getByLabelText(/stock symbol/i), {
      target: { value: "EGAL" },
    });
    fireEvent.click(screen.getByRole("button", { name: /analyze/i }));

    expect(await screen.findByText(/analysis result not found/i)).toBeInTheDocument();
  });
});
