import {
  type TokenConfig,
  getCurrentPlatform,
  loadTokenConfig,
  saveTokenConfig,
  setCurrentPlatform,
} from "../config/store.js";
import { HttpError, NetworkRequestError } from "../utils/http.js";

const TOKEN_TTL_SECONDS = 3600;

export function normalizeBaseUrl(value: string): string {
  return value.replace(/\/+$/, "");
}

export async function playwrightLogin(
  baseUrl: string,
  username: string,
  password: string,
): Promise<TokenConfig> {
  let chromium: typeof import("playwright").chromium;
  try {
    const pw = await import("playwright");
    chromium = pw.chromium;
  } catch {
    throw new Error(
      "Playwright is not installed. Run:\n  npm install playwright && npx playwright install chromium"
    );
  }

  const browser = await chromium.launch({ headless: true });
  try {
    const context = await browser.newContext();
    const page = await context.newPage();

    await page.goto(`${baseUrl}/api/dip-hub/v1/login`, {
      waitUntil: "networkidle",
      timeout: 30_000,
    });

    await page.waitForSelector('input[name="account"]', { timeout: 10_000 });
    await page.fill('input[name="account"]', username);
    await page.fill('input[name="password"]', password);
    await page.click("button.ant-btn-primary");

    let accessToken: string | null = null;
    for (let i = 0; i < 30; i++) {
      await new Promise((r) => setTimeout(r, 1000));

      // Check for login error messages
      const errorEl = await page.$(".ant-message-error, .ant-alert-error");
      if (errorEl) {
        const errorText = await errorEl.textContent();
        throw new Error(`Login failed: ${errorText?.trim() || "unknown error"}`);
      }

      for (const cookie of await context.cookies()) {
        if (cookie.name === "dip.oauth2_token") {
          accessToken = decodeURIComponent(cookie.value);
          break;
        }
      }
      if (accessToken) break;
    }

    if (!accessToken) {
      throw new Error(
        "Login timed out: dip.oauth2_token cookie not received within 30 seconds. " +
        "Check username/password."
      );
    }

    const now = new Date();
    const tokenConfig: TokenConfig = {
      baseUrl,
      accessToken,
      tokenType: "bearer",
      scope: "",
      expiresIn: TOKEN_TTL_SECONDS,
      expiresAt: new Date(now.getTime() + TOKEN_TTL_SECONDS * 1000).toISOString(),
      obtainedAt: now.toISOString(),
    };

    saveTokenConfig(tokenConfig);
    setCurrentPlatform(baseUrl);
    return tokenConfig;
  } finally {
    await browser.close();
  }
}

export async function ensureValidToken(opts?: { forceRefresh?: boolean }): Promise<TokenConfig> {
  const envToken = process.env.KWEAVER_TOKEN;
  const envBaseUrl = process.env.KWEAVER_BASE_URL;
  if (!opts?.forceRefresh && envToken && envBaseUrl) {
    const rawToken = envToken.replace(/^Bearer\s+/i, "");
    return {
      baseUrl: normalizeBaseUrl(envBaseUrl),
      accessToken: rawToken,
      tokenType: "bearer",
      scope: "",
      obtainedAt: new Date().toISOString(),
    };
  }

  const currentPlatform = getCurrentPlatform();
  if (!currentPlatform) {
    throw new Error("No active platform selected. Run `kweaver auth login <platform-url>` first.");
  }

  if (opts?.forceRefresh) {
    throw new Error(
      `Token refresh is not supported. Run \`kweaver auth login ${currentPlatform}\` again.`
    );
  }

  const token = loadTokenConfig(currentPlatform);
  if (!token) {
    throw new Error(
      `No saved token for ${currentPlatform}. Run \`kweaver auth login ${currentPlatform}\` first.`
    );
  }

  if (token.expiresAt) {
    const expiresAtMs = Date.parse(token.expiresAt);
    if (!Number.isNaN(expiresAtMs) && expiresAtMs - 60_000 <= Date.now()) {
      throw new Error(
        `Access token expired. Run \`kweaver auth login ${currentPlatform}\` again.`
      );
    }
  }

  return token;
}

export async function withTokenRetry<T>(
  fn: (token: TokenConfig) => Promise<T>,
): Promise<T> {
  const token = await ensureValidToken();
  try {
    return await fn(token);
  } catch (error) {
    if (error instanceof HttpError && error.status === 401) {
      const platform = token.baseUrl;
      throw new Error(
        `Authentication failed (401). Token may be expired or revoked.\n` +
        `Run \`kweaver auth login ${platform}\` again.`
      );
    }
    throw error;
  }
}

function formatOAuthErrorBody(body: string): string | null {
  let data: { error?: string; error_description?: string };
  try {
    data = JSON.parse(body) as { error?: string; error_description?: string };
  } catch {
    return null;
  }
  if (!data || typeof data.error !== "string") {
    return null;
  }
  const code = data.error;
  const description = typeof data.error_description === "string" ? data.error_description : "";
  const lines: string[] = [`OAuth error: ${code}`];
  if (description) {
    lines.push(description);
  }
  if (code === "invalid_grant") {
    lines.push("");
    lines.push("The refresh token or authorization code is invalid or expired. Run `kweaver auth <platform-url>` again to log in.");
  }
  return lines.join("\n");
}

export function formatHttpError(error: unknown): string {
  if (error instanceof HttpError) {
    const oauthMessage = formatOAuthErrorBody(error.body);
    if (oauthMessage) {
      return `HTTP ${error.status} ${error.statusText}\n\n${oauthMessage}`;
    }
    return `${error.message}\n${error.body}`.trim();
  }

  if (error instanceof NetworkRequestError) {
    return [
      error.message,
      `Method: ${error.method}`,
      `URL: ${error.url}`,
      `Cause: ${error.causeMessage}`,
      `Hint: ${error.hint}`,
    ].join("\n").trim();
  }

  if (error instanceof Error) {
    return error.message;
  }

  return String(error);
}
