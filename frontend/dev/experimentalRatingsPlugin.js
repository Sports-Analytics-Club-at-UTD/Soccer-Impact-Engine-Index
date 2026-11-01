// Node-only Vite middleware. Never imported by client code; never installed for build/preview.
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { fileURLToPath } from "node:url";
const run = promisify(execFile);
const repo = fileURLToPath(new URL("../../", import.meta.url));
export const EXPERIMENTAL_ENDPOINT = "/__local_experimental/five-attributes";
const loopback = (v) => ["127.0.0.1", "::1", "::ffff:127.0.0.1"].includes(v);
const localHost = (v) => typeof v === "string" && /^(?:localhost|127\.0\.0\.1|\[::1\])(?::\d+)?$/.test(v);

export async function loadFrozenExperimentalData() {
  const { stdout } = await run("python", ["-B", "-m", "scripts.provisional_ovr"], {
    cwd: repo, windowsHide: true, timeout: 45000, maxBuffer: 24 * 1024 * 1024,
  });
  const data = JSON.parse(stdout);
  if (data.classification !== "local_experimental" || data.local_only !== true || data.publication_authorized !== false || data.production_ready !== false) {
    throw Error("Local adapter returned an invalid experimental boundary");
  }
  return data;
}

export function experimentalMiddleware({ load = loadFrozenExperimentalData, log = () => {} } = {}) {
  return async (req, res, next) => {
    if (req.url?.split("?")[0] !== EXPERIMENTAL_ENDPOINT) return next();
    const fail = (status, message) => {
      res.statusCode = status; res.setHeader("Content-Type", "application/json");
      res.setHeader("Cache-Control", "no-store"); res.setHeader("X-Content-Type-Options", "nosniff");
      res.end(JSON.stringify({ error: message }));
    };
    const host = req.headers.host, origin = req.headers.origin;
    if (!loopback(req.socket.remoteAddress) || !localHost(host) ||
        (origin !== undefined && origin !== `http://${host}` && origin !== `https://${host}`) ||
        req.headers["sec-fetch-site"] === "cross-site") return fail(403, "Local same-origin development access only");
    if (req.method !== "GET") return fail(405, "GET only");
    if (req.url !== EXPERIMENTAL_ENDPOINT) return fail(400, "No file paths or query parameters are accepted");
    try {
      const data = await load();
      res.statusCode = 200; res.setHeader("Content-Type", "application/json; charset=utf-8");
      res.setHeader("Cache-Control", "no-store"); res.setHeader("X-Content-Type-Options", "nosniff");
      res.setHeader("Cross-Origin-Resource-Policy", "same-origin");
      res.end(JSON.stringify(data));
    } catch (error) {
      log(`Local experimental adapter failed: ${error.message}`);
      fail(500, "Frozen experimental data failed validation. No fallback was loaded.");
    }
  };
}

export default function localExperimentalRatings() {
  return {
    name: "local-experimental-five-attributes", apply: "serve",
    configResolved(config) {
      if (config.command === "serve" && ![undefined, false, "localhost", "127.0.0.1", "::1"].includes(config.server.host)) {
        throw Error("Experimental development preview must bind to loopback only");
      }
    },
    configureServer(server) {
      server.middlewares.use(experimentalMiddleware({ log: (message) => server.config.logger.error(message) }));
    },
    // Intentionally no configurePreviewServer, build hook or static export.
  };
}
