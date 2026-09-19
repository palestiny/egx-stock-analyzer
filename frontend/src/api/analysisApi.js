import { clearSessionToken, getSessionToken } from "../auth/session";

async function parseError(response, operation) {
  const error = new Error(operation + " failed with status " + response.status);
  error.status = response.status;
  throw error;
}

async function getJson(url, operation, options) {
  const requestOptions = options ? { ...options } : {};
  const sessionToken = getSessionToken();
  if (sessionToken) {
    requestOptions.headers = {
      ...(options?.headers ?? {}),
      Authorization: "Bearer " + sessionToken,
    };
  }

  const response = Object.keys(requestOptions).length === 0
    ? await fetch(url)
    : await fetch(url, requestOptions);

  if (!response.ok) {
    if (response.status === 401) {
      clearSessionToken();
      window.dispatchEvent(new Event("egx:auth-expired"));
    }
    await parseError(response, operation);
  }

  return response.json();
}

export function getAnalysis(symbol) {
  return getJson("/api/v1/analysis/" + encodeURIComponent(symbol), "Analysis request");
}

export function runAnalysis(symbol) {
  return getJson("/api/v1/analysis/" + encodeURIComponent(symbol), "Analysis execution request", {
    method: "POST",
  });
}

export function getReport(symbol) {
  return getJson("/api/v1/reports/" + encodeURIComponent(symbol), "Report request");
}

export function getAlert(symbol) {
  return getJson("/api/v1/alerts/" + encodeURIComponent(symbol), "Alert request");
}

export function getMarketOpportunities(symbols) {
  const query = symbols.join(",");
  return getJson("/api/v1/opportunities?symbols=" + encodeURIComponent(query), "Market opportunities request");
}

export function getAnalysisHistory(symbol, fromDate, toDate) {
  const params = new URLSearchParams();
  if (fromDate) {
    params.set("from_date", fromDate);
  }
  if (toDate) {
    params.set("to_date", toDate);
  }

  const query = params.toString();
  const url = "/api/v1/history/" + encodeURIComponent(symbol) + (query ? "?" + query : "");
  return getJson(url, "Analysis history request");
}


export function getAnalysisComparison(symbol, beforeSnapshotId, afterSnapshotId) {
  const params = new URLSearchParams({
    before: beforeSnapshotId,
    after: afterSnapshotId,
  });
  return getJson(
    "/api/v1/comparisons/" + encodeURIComponent(symbol) + "?" + params.toString(),
    "Analysis comparison request",
  );
}


export function getSnapshotPerformance(symbol, beforeSnapshotId, afterSnapshotId) {
  const params = new URLSearchParams({
    before: beforeSnapshotId,
    after: afterSnapshotId,
  });
  return getJson(
    "/api/v1/performance/" + encodeURIComponent(symbol) + "?" + params.toString(),
    "Historical performance request",
  );
}


export function getScheduledWorkflowExecutions(occurrenceId) {
  const params = new URLSearchParams();
  if (occurrenceId) {
    params.set("occurrence_id", occurrenceId);
  }

  const query = params.toString();
  const url = "/api/v1/workflows/executions" + (query ? "?" + query : "");
  return getJson(url, "Scheduled workflow executions request");
}


export function recoverScheduledWorkflowExecution(executionId) {
  return getJson(
    "/api/v1/workflows/executions/" + encodeURIComponent(executionId) + "/recover",
    "Scheduled workflow recovery request",
    { method: "POST" },
  );
}


export function getScheduledWorkflowExecutionHistory(executionId, options = {}) {
  const params = new URLSearchParams();
  if (options.pageSize != null) {
    params.set("page_size", String(options.pageSize));
  }
  if (options.cursor) {
    params.set("cursor", options.cursor);
  }

  const query = params.toString();
  return getJson(
    "/api/v1/workflows/executions/" +
      encodeURIComponent(executionId) +
      "/history" +
      (query ? "?" + query : ""),
    "Scheduled workflow execution history request",
  );
}


export function getCurrentIdentity() {
  return getJson("/api/v1/auth/me", "Authentication request");
}


export function getUsers() {
  return getJson("/api/v1/users", "User administration request");
}

export function createUser() {
  return getJson("/api/v1/users", "User creation request", { method: "POST" });
}

export function updateUserStatus(userId, status) {
  return getJson(
    "/api/v1/users/" + encodeURIComponent(userId) + "/status?status=" + encodeURIComponent(status),
    "User lifecycle request",
    { method: "PATCH" },
  );
}

export function rotateOwnCredential() {
  return getJson(
    "/api/v1/users/me/credentials/rotate",
    "Credential rotation request",
    { method: "POST" },
  );
}


export function rotateUserCredential(userId) {
  return getJson(
    "/api/v1/users/" + encodeURIComponent(userId) + "/credentials/rotate",
    "User credential rotation request",
    { method: "POST" },
  );
}


export function getManagementAudit(filters = {}) {
  const params = new URLSearchParams();
  if (filters.actorUserId) params.set("actor_user_id", filters.actorUserId);
  if (filters.targetUserId) params.set("target_user_id", filters.targetUserId);
  if (filters.action) params.set("action", filters.action);
  if (filters.outcome) params.set("outcome", filters.outcome);
  if (filters.fromTime) params.set("from_time", new Date(filters.fromTime).toISOString());
  if (filters.toTime) params.set("to_time", new Date(filters.toTime).toISOString());
  params.set("page_size", String(filters.pageSize ?? 50));
  params.set("offset", String(filters.offset ?? 0));

  return getJson(
    "/api/v1/management/audit?" + params.toString(),
    "Management audit request",
  );
}


export function getUserAuditHistory(filters = {}) {
  const params = new URLSearchParams();
  if (filters.action) params.set("action", filters.action);
  if (filters.outcome) params.set("outcome", filters.outcome);
  if (filters.fromTime) params.set("from_time", new Date(filters.fromTime).toISOString());
  if (filters.toTime) params.set("to_time", new Date(filters.toTime).toISOString());
  params.set("page_size", String(filters.pageSize ?? 50));
  params.set("offset", String(filters.offset ?? 0));

  return getJson(
    "/api/v1/users/me/audit?" + params.toString(),
    "User audit history request",
  );
}
