/**
 * Pre-test script: ensures a valid token exists for the e2e platform.
 *
 * Run once before `node --test` so that every test-file process inherits
 * a valid ~/.kweaver/ token without each process racing to refresh.
 *
 * Priority:
 * 1. ensureValidToken() — uses refresh_token if available
 * 2. playwrightLogin()  — OAuth2 + headless browser (produces refresh_token)
 */

import { readFileSync, existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { homedir } from "node:os";
import { fileURLToPath } from "node:url";
import { setCurrentPlatform } from "../../src/config/store.js";
import { ensureValidToken, normalizeBaseUrl, playwrightLogin } from "../../src/auth/oauth.js";

function findRepoRoot(): string | null {
  let dir = dirname(fileURLToPath(import.meta.url));
  for (let i = 0; i < 10; i += 1) {
    if (existsSync(join(dir, ".git"))) return dir;
    const parent = dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }
  return null;
}

function loadEnvFile(path: string): void {
  if (!existsSync(path)) return;
  const content = readFileSync(path, "utf-8");
  for (const line of content.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const withoutExport = trimmed.replace(/^export\s+/, "");
    const eqIdx = withoutExport.indexOf("=");
    if (eqIdx < 0) continue;
    const key = withoutExport.slice(0, eqIdx).trim();
    let value = withoutExport.slice(eqIdx + 1).trim();
    value = value.replace(/^["']|["']$/g, "");
    if (!(key in process.env)) {
      process.env[key] = value;
    }
  }
}

const REPO_ROOT = findRepoRoot();
if (REPO_ROOT) loadEnvFile(join(REPO_ROOT, ".env.e2e"));
loadEnvFile(join(homedir(), ".env.secrets"));

const baseUrl = process.env.KWEAVER_BASE_URL;
if (!baseUrl) {
  console.log("[e2e] KWEAVER_BASE_URL not set, skipping token refresh");
  process.exit(0);
}

const base = normalizeBaseUrl(baseUrl);
setCurrentPlatform(base);

// Try refresh_token first
try {
  const token = await ensureValidToken();
  console.log(`[e2e] Token valid for ${base} (expires ${token.expiresAt ?? "unknown"})`);
  process.exit(0);
} catch {
  // fall through
}

// Fallback: Playwright headless login
const username = process.env.KWEAVER_USERNAME;
const password = process.env.KWEAVER_PASSWORD;
if (!username || !password) {
  console.error("[e2e] Token expired and no KWEAVER_USERNAME/KWEAVER_PASSWORD for auto-login");
  process.exit(1);
}

try {
  const token = await playwrightLogin(base, { username, password });
  console.log(`[e2e] Playwright login OK for ${base} (expires ${token.expiresAt ?? "unknown"})`);
} catch (err) {
  console.error(`[e2e] Auto-login failed: ${err instanceof Error ? err.message : err}`);
  process.exit(1);
}
