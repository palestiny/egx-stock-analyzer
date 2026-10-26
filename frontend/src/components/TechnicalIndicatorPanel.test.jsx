import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { TechnicalIndicatorPanel } from "./TechnicalIndicatorPanel";

const point = {
  timestamp: "2026-10-26T10:00:00+02:00",
  close: "100",
  sma_20: "98",
  ema_20: "99",
  bollinger_upper: "102",
  sma_50: null,
  sma_200: null,
  rsi_14: "62.5",
  macd_histogram: "0.75",
  atr_14: "2.1",
  adx_14: "24",
  candlestick_patterns: ["bullish_engulfing"],
  confirmed_swings: [["high", "101"]],
  fibonacci_direction: "up",
  fibonacci_anchor_indices: [2, 5],
  fibonacci_retracements: [["0.5", "95"]],
  fibonacci_extension_direction: "up",
  fibonacci_extension_anchor_indices: [1, 2, 5],
  fibonacci_extensions: [["1.618", "120"]],
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
    expect(screen.getByText("EMA 20")).toBeTruthy();
    expect(screen.getByText("Bollinger upper")).toBeTruthy();
    expect(screen.getByText("Fibonacci retracement")).toBeTruthy();
    expect(screen.getByText("Fibonacci extension")).toBeTruthy();
    expect(screen.getByText("HIGH 101.00")).toBeTruthy();
    expect(screen.getByText("50.0%")).toBeTruthy();
    expect(screen.getByText("161.8%")).toBeTruthy();
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
