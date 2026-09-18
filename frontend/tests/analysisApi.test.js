import { describe, expect, it, vi } from "vitest";

import { getAnalysis, getAnalysisHistory, getMarketOpportunities } from "../src/api/analysisApi";

describe("analysis API client", () => {
  it("requests analysis for the requested symbol and returns the response", async () => {
    const analysis = {
      symbol: "EGAL",
      technical_score: 1,
      fundamental_score: 2,
      stock_quality: 3,
      entry_quality: 1,
      opportunity: "buy",
    };

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue(analysis),
    });

    await expect(getAnalysis("EGAL")).resolves.toEqual(analysis);
    expect(globalThis.fetch).toHaveBeenCalledWith(
      "/api/v1/analysis/EGAL",
    );
  });

  it("throws an error containing the HTTP status when the API fails", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
    });

    await expect(getAnalysis("EGAL")).rejects.toMatchObject({
      status: 404,
    });
  });
});


it("requests the market opportunity endpoint", async () => {
  globalThis.fetch = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({ opportunities: [], missing_symbols: [] }),
  });

  await getMarketOpportunities(["egal", "ieec"]);

  expect(global.fetch).toHaveBeenCalledWith(
    "/api/v1/opportunities?symbols=egal%2Cieec",
  );
});


describe("analysis history API client", () => {
  it("requests historical analysis with optional inclusive date bounds", async () => {
    const history = { symbol: "EGAL", items: [] };

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue(history),
    });

    await expect(
      getAnalysisHistory("EGAL", "2026-09-16", "2026-09-18"),
    ).resolves.toEqual(history);

    expect(globalThis.fetch).toHaveBeenCalledWith(
      "/api/v1/history/EGAL?from_date=2026-09-16&to_date=2026-09-18",
    );
  });
});
