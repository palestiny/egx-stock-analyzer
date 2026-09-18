async function parseError(response, operation) {
  const error = new Error(operation + " failed with status " + response.status);
  error.status = response.status;
  throw error;
}

async function getJson(url, operation, options) {
  const response = options === undefined
    ? await fetch(url)
    : await fetch(url, options);

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
