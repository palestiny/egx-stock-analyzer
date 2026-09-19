async function parseError(response, operation) {
  const error = new Error(operation + " failed with status " + response.status);
  error.status = response.status;
  throw error;
}

async function getJson(url, operation, options) {
  const operatorToken = import.meta.env.VITE_EGX_OPERATOR_TOKEN;
  const requestOptions = options === undefined ? {} : { ...options };

  if (operatorToken) {
    requestOptions.headers = {
      ...(requestOptions.headers || {}),
      Authorization: "Bearer " + operatorToken,
    };
  }

  const response = Object.keys(requestOptions).length === 0
    ? await fetch(url)
    : await fetch(url, requestOptions);

  if (!response.ok) {
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
