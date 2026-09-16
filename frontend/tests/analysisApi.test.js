import { describe, expect, it, vi } from "vitest";

import { getAnalysis } from "../src/api/analysisApi";

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
