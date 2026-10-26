import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { TechnicalIndicatorPanel } from "./TechnicalIndicatorPanel";

const point = {
  timestamp: "2026-10-26T10:00:00+02:00",
  close: "100",
  sma_20: "98",
  sma_50: null,
  sma_200: null,
  rsi_14: "62.5",
  macd_histogram: "0.75",
  atr_14: "2.1",
  adx_14: "24",
  candlestick_patterns: ["bullish_engulfing"],
};

describe("TechnicalIndicatorPanel", () => {
  it("renders the price chart and latest indicator evidence", () => {
    render(
      <TechnicalIndicatorPanel
        history={{
          available: true,
          returned_points: 1,
          total_points: 1,
          methodology_version: "technical-indicators-v1",
          points: [point],
        }}
        loading={false}
        error={null}
      />,
    );

    expect(screen.getByRole("img", { name: /closing price with sma/i })).toBeTruthy();
    expect(screen.getByText("62.50")).toBeTruthy();
    expect(screen.getByText("bullish_engulfing")).toBeTruthy();
    expect(screen.getByText(/1 of 1 points/)).toBeTruthy();
  });

  it("explains when saved analysis has no indicator history", () => {
    render(
      <TechnicalIndicatorPanel
        history={{ available: false, points: [], total_points: 0, returned_points: 0 }}
        loading={false}
        error={null}
      />,
    );
    expect(screen.getByText(/predates indicator-history storage/i)).toBeTruthy();
  });

  it("announces loading and errors accessibly", () => {
    const { rerender } = render(
      <TechnicalIndicatorPanel history={null} loading={true} error={null} />,
    );
    expect(screen.getByRole("status")).toBeTruthy();

    rerender(
      <TechnicalIndicatorPanel
        history={null}
        loading={false}
        error={new Error("Provider unavailable")}
      />,
    );
    expect(screen.getByRole("alert").textContent).toContain("Provider unavailable");
  });
});
