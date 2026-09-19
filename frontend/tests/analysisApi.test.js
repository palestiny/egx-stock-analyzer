import { beforeEach, describe, expect, it, vi } from "vitest";

import { getAnalysis, getAnalysisHistory, getMarketOpportunities, getScheduledWorkflowExecutions, recoverScheduledWorkflowExecution } from "../src/api/analysisApi";
import { clearSessionToken, setSessionToken } from "../src/auth/session";

describe("analysis API client", () => {
  beforeEach(() => {
    clearSessionToken();
  });
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


it("requests an explicit historical comparison by snapshot UUID", async () => {
  const comparison = { symbol: "EGAL", deltas: { stock_quality: 3 } };

  globalThis.fetch = vi.fn().mockResolvedValue({
    ok: true,
    json: vi.fn().mockResolvedValue(comparison),
  });

  const { getAnalysisComparison } = await import("../src/api/analysisApi");
  await expect(
    getAnalysisComparison("EGAL", "before-id", "after-id"),
  ).resolves.toEqual(comparison);

  expect(globalThis.fetch).toHaveBeenCalledWith(
    "/api/v1/comparisons/EGAL?before=before-id&after=after-id",
  );
});


it("requests historical performance by snapshot UUID", async () => {
  const performance = { symbol: "EGAL", metrics: { price_change: 25, price_change_percent: 25 } };

  globalThis.fetch = vi.fn().mockResolvedValue({
    ok: true,
    json: vi.fn().mockResolvedValue(performance),
  });

  const { getSnapshotPerformance } = await import("../src/api/analysisApi");
  await expect(
    getSnapshotPerformance("EGAL", "before-id", "after-id"),
  ).resolves.toEqual(performance);

  expect(globalThis.fetch).toHaveBeenCalledWith(
    "/api/v1/performance/EGAL?before=before-id&after=after-id",
  );
});


it("requests scheduled workflow executions with an optional occurrence filter", async () => {
  const executions = { items: [] };

  globalThis.fetch = vi.fn().mockResolvedValue({
    ok: true,
    json: vi.fn().mockResolvedValue(executions),
  });

  await expect(getScheduledWorkflowExecutions("occ-42")).resolves.toEqual(executions);

  expect(globalThis.fetch).toHaveBeenCalledWith(
    "/api/v1/workflows/executions?occurrence_id=occ-42",
  );
});


it("requests scheduled workflow recovery with POST", async () => {
  const execution = { id: "workflow-1", occurrence_id: "occ-1", state: "completed" };

  globalThis.fetch = vi.fn().mockResolvedValue({
    ok: true,
    json: vi.fn().mockResolvedValue(execution),
  });

  await expect(recoverScheduledWorkflowExecution("workflow-1")).resolves.toEqual(execution);

  expect(globalThis.fetch).toHaveBeenCalledWith(
    "/api/v1/workflows/executions/workflow-1/recover",
    { method: "POST" },
  );
});


it("adds the current session token as a bearer authorization header", async () => {
  setSessionToken("session-token");
  globalThis.fetch = vi.fn().mockResolvedValue({
    ok: true,
    json: vi.fn().mockResolvedValue({ subject: "user-1" }),
  });

  const { getCurrentIdentity } = await import("../src/api/analysisApi");
  await expect(getCurrentIdentity()).resolves.toEqual({ subject: "user-1" });

  expect(globalThis.fetch).toHaveBeenCalledWith(
    "/api/v1/auth/me",
    { headers: { Authorization: "Bearer session-token" } },
  );
});

it("clears the session and emits auth expiry on HTTP 401", async () => {
  setSessionToken("expired-token");
  globalThis.fetch = vi.fn().mockResolvedValue({
    ok: false,
    status: 401,
  });
  const dispatchSpy = vi.spyOn(window, "dispatchEvent");

  const { getCurrentIdentity } = await import("../src/api/analysisApi");
  await expect(getCurrentIdentity()).rejects.toMatchObject({ status: 401 });

  expect(window.sessionStorage.getItem("egx-stock-analyzer.session-token")).toBeNull();
  expect(dispatchSpy).toHaveBeenCalled();
});


describe("getManagementAudit", () => {
  it("builds bounded audit query parameters", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ items: [], total_count: 0, offset: 0, page_size: 50, has_more: false }),
    });

    const { getManagementAudit } = await import("../src/api/analysisApi");
    await getManagementAudit({
      actorUserId: "actor-id",
      targetUserId: "target-id",
      action: "user_created",
      outcome: "success",
      pageSize: 50,
      offset: 100,
    });

    expect(global.fetch).toHaveBeenCalledWith(
      "/api/v1/management/audit?actor_user_id=actor-id&target_user_id=target-id&action=user_created&outcome=success&page_size=50&offset=100",
    );
  });
});
