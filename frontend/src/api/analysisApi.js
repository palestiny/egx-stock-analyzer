export async function getAnalysis(symbol) {
  const response = await fetch(`/api/v1/analysis/${symbol}`);

  if (!response.ok) {
    const error = new Error(`Analysis request failed with status ${response.status}`);
    error.status = response.status;
    throw error;
  }

  return response.json();
}
