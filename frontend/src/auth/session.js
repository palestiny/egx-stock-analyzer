const SESSION_KEY = "egx-stock-analyzer.session-token";

export function getSessionToken() {
  return window.sessionStorage.getItem(SESSION_KEY);
}

export function setSessionToken(token) {
  const normalized = token.trim();
  if (!normalized) {
    throw new Error("Authentication token is required");
  }
  window.sessionStorage.setItem(SESSION_KEY, normalized);
}

export function clearSessionToken() {
  window.sessionStorage.removeItem(SESSION_KEY);
}
