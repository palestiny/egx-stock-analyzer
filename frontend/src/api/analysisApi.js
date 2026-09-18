async function parseError(response, operation) {
  const error = new Error(operation + " failed with status " + response.status);
  error.status = response.status;
  throw error;
}

export async function getAnalysis(symbol) {
  const response = await fetch("/api/v1/analysis/" + symbol);

  if (!response.ok) {
    await parseError(response, "Analysis request");
  }

  return response.json();
}

export async function runAnalysis(symbol) {
  const response = await fetch("/api/v1/analysis/" + symbol, {
    method: "POST",
  });

  if (!response.ok) {
    await parseError(response, "Analysis execution request");
  }

  return response.json();
}
