import { parseScorecard } from "./scorecardAdapter.js";

export class ScorecardLoadError extends Error {
  constructor(code, message, cause) {
    super(message, { cause });
    this.name = "ScorecardLoadError";
    this.code = code;
  }
}

export function scorecardAssetUrl(baseUrl = "/") {
  if (typeof baseUrl !== "string" || !baseUrl.trim()) throw new Error("A Vite base path is required");
  return `${baseUrl.endsWith("/") ? baseUrl : `${baseUrl}/`}data/scorecard.json`;
}

export async function loadScorecard({ baseUrl = "/", fetchImpl = globalThis.fetch, signal } = {}) {
  const url = scorecardAssetUrl(baseUrl);
  let response;
  try {
    response = await fetchImpl(url, { signal, headers: { Accept: "application/json" } });
  } catch (cause) {
    if (cause?.name === "AbortError") throw cause;
    throw new ScorecardLoadError("network", "Could not load the raw scorecard. Check the connection and asset location.", cause);
  }
  if (!response?.ok) {
    throw new ScorecardLoadError("http", `Raw scorecard request failed (HTTP ${response?.status ?? "unknown"}). No demo data was substituted.`);
  }
  let payload;
  try {
    payload = await response.json();
  } catch (cause) {
    if (cause?.name === "AbortError") throw cause;
    throw new ScorecardLoadError("json", "The raw scorecard response is not valid JSON.", cause);
  }
  try {
    return parseScorecard(payload);
  } catch (cause) {
    throw new ScorecardLoadError("contract", `Raw scorecard validation failed: ${cause.message}`, cause);
  }
}
