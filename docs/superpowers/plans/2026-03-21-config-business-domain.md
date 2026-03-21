# Per-Platform Business Domain Config Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let users persist a default `businessDomain` per platform so every CLI command uses it automatically instead of hard-coding `bd_public`.

**Architecture:** Store `businessDomain` in a new `config.json` alongside existing per-platform files (`client.json`, `token.json`). Add `loadPlatformConfig` / `savePlatformConfig` to the store module. Introduce a `kweaver config` CLI command for `set-bd` / `show`. Replace all 28 `let businessDomain = "bd_public"` occurrences with a helper that reads from config first. The `KWEAVER_BUSINESS_DOMAIN` env var remains highest priority, then per-platform config, then `"bd_public"` fallback.

**Tech Stack:** TypeScript, Node.js built-in `fs`

---

### Task 1: Store layer — persist businessDomain per platform

**Files:**
- Modify: `packages/typescript/src/config/store.ts`
- Test: `packages/typescript/test/config-store.test.ts`

- [ ] **Step 1: Write the failing test**

```typescript
// In packages/typescript/test/config-store.test.ts
import { describe, it, beforeEach, afterEach } from "node:test";
import { strict as assert } from "node:assert";
import { mkdtempSync, rmSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";
import {
  loadPlatformBusinessDomain,
  savePlatformBusinessDomain,
  resolveBusinessDomain,
} from "../src/config/store.js";

describe("platform config (businessDomain)", () => {
  let origDir: string | undefined;
  let tempDir: string;

  beforeEach(() => {
    origDir = process.env.KWEAVERC_CONFIG_DIR;
    tempDir = mkdtempSync(join(tmpdir(), "kw-cfg-"));
    process.env.KWEAVERC_CONFIG_DIR = tempDir;
  });

  afterEach(() => {
    if (origDir === undefined) delete process.env.KWEAVERC_CONFIG_DIR;
    else process.env.KWEAVERC_CONFIG_DIR = origDir;
    rmSync(tempDir, { recursive: true, force: true });
  });

  it("returns null when no config exists", () => {
    const bd = loadPlatformBusinessDomain("https://example.com");
    assert.equal(bd, null);
  });

  it("saves and loads businessDomain", () => {
    savePlatformBusinessDomain("https://example.com", "my-uuid-bd");
    const bd = loadPlatformBusinessDomain("https://example.com");
    assert.equal(bd, "my-uuid-bd");
  });

  it("resolveBusinessDomain prefers env var", () => {
    savePlatformBusinessDomain("https://example.com", "from-config");
    process.env.KWEAVER_BUSINESS_DOMAIN = "from-env";
    try {
      assert.equal(resolveBusinessDomain("https://example.com"), "from-env");
    } finally {
      delete process.env.KWEAVER_BUSINESS_DOMAIN;
    }
  });

  it("resolveBusinessDomain falls back to config then bd_public", () => {
    // No config → bd_public
    assert.equal(resolveBusinessDomain("https://no-config.com"), "bd_public");
    // With config → config value
    savePlatformBusinessDomain("https://example.com", "uuid-bd");
    assert.equal(resolveBusinessDomain("https://example.com"), "uuid-bd");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/typescript && npx tsx --test test/config-store.test.ts`
Expected: FAIL — `loadPlatformBusinessDomain` and `resolveBusinessDomain` not found

- [ ] **Step 3: Implement store functions**

Add to `packages/typescript/src/config/store.ts`:

```typescript
/** Per-platform config (not auth — general settings). */
export interface PlatformConfig {
  businessDomain?: string;
}

function loadPlatformConfig(baseUrl: string): PlatformConfig | null {
  ensureStoreReady();
  return readJsonFile<PlatformConfig>(getPlatformFile(baseUrl, "config.json"));
}

function savePlatformConfig(baseUrl: string, config: PlatformConfig): void {
  ensureStoreReady();
  ensurePlatformDir(baseUrl);
  writeJsonFile(getPlatformFile(baseUrl, "config.json"), config);
}

export function loadPlatformBusinessDomain(baseUrl: string): string | null {
  return loadPlatformConfig(baseUrl)?.businessDomain ?? null;
}

export function savePlatformBusinessDomain(baseUrl: string, businessDomain: string): void {
  const existing = loadPlatformConfig(baseUrl) ?? {};
  savePlatformConfig(baseUrl, { ...existing, businessDomain });
}

/**
 * Resolve businessDomain: env var > per-platform config > "bd_public".
 * If baseUrl is omitted, uses the current platform.
 */
export function resolveBusinessDomain(baseUrl?: string): string {
  const fromEnv = process.env.KWEAVER_BUSINESS_DOMAIN;
  if (fromEnv) return fromEnv;

  const targetUrl = baseUrl ?? getCurrentPlatform();
  if (targetUrl) {
    const fromConfig = loadPlatformBusinessDomain(targetUrl);
    if (fromConfig) return fromConfig;
  }
  return "bd_public";
}
```

Also export `PlatformConfig` and all three new functions from the module.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/typescript && npx tsx --test test/config-store.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/typescript/src/config/store.ts packages/typescript/test/config-store.test.ts
git commit -m "feat(config): add per-platform businessDomain storage and resolution"
```

---

### Task 2: Add `kweaver config` CLI command

**Files:**
- Create: `packages/typescript/src/commands/config.ts`
- Modify: `packages/typescript/src/cli.ts`
- Test: `packages/typescript/test/config-cmd.test.ts`

- [ ] **Step 1: Write the failing test**

```typescript
// packages/typescript/test/config-cmd.test.ts
import { describe, it, beforeEach, afterEach } from "node:test";
import { strict as assert } from "node:assert";
import { mkdtempSync, rmSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";

// Helper to capture console output from run()
async function runCli(args: string[]): Promise<{ code: number; stdout: string; stderr: string }> {
  const { run } = await import("../src/cli.js");
  const stdout: string[] = [];
  const stderr: string[] = [];
  const origLog = console.log;
  const origErr = console.error;
  console.log = (...a: unknown[]) => stdout.push(a.map(String).join(" "));
  console.error = (...a: unknown[]) => stderr.push(a.map(String).join(" "));
  try {
    const code = await run(args);
    return { code, stdout: stdout.join("\n"), stderr: stderr.join("\n") };
  } finally {
    console.log = origLog;
    console.error = origErr;
  }
}

describe("kweaver config", () => {
  let origDir: string | undefined;
  let tempDir: string;

  beforeEach(() => {
    origDir = process.env.KWEAVERC_CONFIG_DIR;
    tempDir = mkdtempSync(join(tmpdir(), "kw-cfg-"));
    process.env.KWEAVERC_CONFIG_DIR = tempDir;
    // Set up a fake current platform
    const platformsDir = join(tempDir, "platforms", "aHR0cHM6Ly9leGFtcGxlLmNvbQ");
    mkdirSync(platformsDir, { recursive: true });
    writeFileSync(join(platformsDir, "client.json"), JSON.stringify({ baseUrl: "https://example.com", clientId: "x", clientSecret: "s", redirectUri: "http://localhost", logoutRedirectUri: "http://localhost", scope: "openid" }));
    writeFileSync(join(tempDir, "state.json"), JSON.stringify({ currentPlatform: "https://example.com" }));
  });

  afterEach(() => {
    if (origDir === undefined) delete process.env.KWEAVERC_CONFIG_DIR;
    else process.env.KWEAVERC_CONFIG_DIR = origDir;
    rmSync(tempDir, { recursive: true, force: true });
  });

  it("config show prints bd_public by default", async () => {
    const { code, stdout } = await runCli(["config", "show"]);
    assert.equal(code, 0);
    assert.ok(stdout.includes("bd_public"), `expected bd_public in: ${stdout}`);
  });

  it("config set-bd saves and config show reflects it", async () => {
    const r1 = await runCli(["config", "set-bd", "my-uuid"]);
    assert.equal(r1.code, 0);
    const r2 = await runCli(["config", "show"]);
    assert.equal(r2.code, 0);
    assert.ok(r2.stdout.includes("my-uuid"), `expected my-uuid in: ${r2.stdout}`);
  });

  it("config --help shows usage", async () => {
    const { code, stdout } = await runCli(["config", "--help"]);
    assert.equal(code, 0);
    assert.ok(stdout.includes("set-bd"));
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/typescript && npx tsx --test test/config-cmd.test.ts`
Expected: FAIL — `config` is unknown command

- [ ] **Step 3: Implement the config command**

Create `packages/typescript/src/commands/config.ts`:

```typescript
import {
  getCurrentPlatform,
  resolveBusinessDomain,
  savePlatformBusinessDomain,
  loadPlatformBusinessDomain,
} from "../config/store.js";

const HELP = `kweaver config

Subcommands:
  set-bd <value>    Set the default business domain for the current platform
  show              Show current config (platform, business domain)
  --help            Show this message

Examples:
  kweaver config set-bd 54308785-4438-43df-9490-a7fd11df5765
  kweaver config show`;

export async function runConfigCommand(args: string[]): Promise<number> {
  const [sub, ...rest] = args;

  if (!sub || sub === "--help" || sub === "-h" || sub === "help") {
    console.log(HELP);
    return 0;
  }

  if (sub === "show") {
    const platform = getCurrentPlatform();
    if (!platform) {
      console.error("No active platform. Run `kweaver auth login <url>` first.");
      return 1;
    }
    const bd = resolveBusinessDomain(platform);
    const source = process.env.KWEAVER_BUSINESS_DOMAIN
      ? "env"
      : loadPlatformBusinessDomain(platform)
        ? "config"
        : "default";
    console.log(`Platform:        ${platform}`);
    console.log(`Business Domain: ${bd} (${source})`);
    return 0;
  }

  if (sub === "set-bd") {
    const value = rest[0];
    if (!value || value.startsWith("-")) {
      console.error("Usage: kweaver config set-bd <value>");
      return 1;
    }
    const platform = getCurrentPlatform();
    if (!platform) {
      console.error("No active platform. Run `kweaver auth login <url>` first.");
      return 1;
    }
    savePlatformBusinessDomain(platform, value);
    console.log(`Business domain set to: ${value}`);
    return 0;
  }

  console.error(`Unknown config subcommand: ${sub}`);
  console.log(HELP);
  return 1;
}
```

Register in `packages/typescript/src/cli.ts` — add import and route:

```typescript
import { runConfigCommand } from "./commands/config.js";
// ... in run():
if (command === "config") {
  return runConfigCommand(rest);
}
```

Also add to `printHelp()`:
- Usage: `kweaver config [set-bd|show]`
- Commands: `config         Per-platform configuration (business domain)`

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/typescript && npx tsx --test test/config-cmd.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/typescript/src/commands/config.ts packages/typescript/src/cli.ts packages/typescript/test/config-cmd.test.ts
git commit -m "feat(cli): add kweaver config command for per-platform business domain"
```

---

### Task 3: Replace hard-coded `bd_public` defaults with `resolveBusinessDomain()`

**Files:**
- Modify: `packages/typescript/src/commands/bkn.ts` (19 occurrences)
- Modify: `packages/typescript/src/commands/agent.ts` (5 occurrences)
- Modify: `packages/typescript/src/commands/agent-chat.ts` (1 occurrence)
- Modify: `packages/typescript/src/commands/ds.ts` (1 occurrence)
- Modify: `packages/typescript/src/commands/vega.ts` (1 occurrence)
- Modify: `packages/typescript/src/commands/call.ts` (1 occurrence)

**Approach:** In each parse function, change the default from `"bd_public"` to `""`. Then at the end of each parse function (after the arg-parsing loop, before `return`), add a single fallback line. This keeps the change localized to parse functions — no need to find execution points.

- [ ] **Step 1: Add import to each command file**

In every file listed above, add:

```typescript
import { resolveBusinessDomain } from "../config/store.js";
```

- [ ] **Step 2: In each parse function, change default and add resolution before return**

For every parse function that contains `let businessDomain = "bd_public"`, apply this two-line change:

```typescript
// Before:
let businessDomain = "bd_public";
// ... arg-parsing loop ...
return { ..., businessDomain, ... };

// After:
let businessDomain = "";
// ... arg-parsing loop (unchanged — -bd flag sets businessDomain if provided) ...
if (!businessDomain) businessDomain = resolveBusinessDomain();
return { ..., businessDomain, ... };
```

The `resolveBusinessDomain()` call (no args) uses the current platform from `~/.kweaver/state.json`, which is the common case. The resolution line goes right before the `return` statement in each parse function.

For `call.ts` which does not use a separate parse function, apply the same pattern inline — change the default to `""` and add `if (!businessDomain) businessDomain = resolveBusinessDomain();` after the flag-parsing loop.

- [ ] **Step 3: Run existing tests to verify no regressions**

Run: `cd packages/typescript && npm test`
Expected: All existing tests PASS (no config is set in tests, so `resolveBusinessDomain()` returns `"bd_public"` — same behavior as before)

- [ ] **Step 4: Commit**

```bash
git add packages/typescript/src/commands/bkn.ts packages/typescript/src/commands/agent.ts packages/typescript/src/commands/agent-chat.ts packages/typescript/src/commands/ds.ts packages/typescript/src/commands/vega.ts packages/typescript/src/commands/call.ts
git commit -m "feat(cli): use per-platform business domain config as default for all commands"
```

---

### Task 4: Update skill documentation

**Files:**
- Modify: `skills/kweaver/SKILL.md` (or `.claude/skills/kweaver/SKILL.md`)
- Modify: `skills/kweaver/references/bkn.md` (or `.claude/skills/kweaver/references/bkn.md`)

- [ ] **Step 1: Update SKILL.md**

Add `config` to the command group table:

```markdown
| `config` | 平台配置（business domain 等） | — |
```

Update the 注意事项 section — replace:
> **不要自行猜测 business_domain 值**，使用默认值 `bd_public`

with:
> **不要自行猜测 business_domain 值**。首次使用时运行 `kweaver config show` 确认当前 business domain。
> 如果返回 `bd_public (default)` 但命令结果为空，可能需要用 `kweaver config set-bd <uuid>` 设置正确的值（从平台 UI 的请求头中获取 `X-Business-Domain`）。

- [ ] **Step 2: Add config examples to references**

Add a brief section to the relevant reference doc or create `references/config.md`:

```markdown
# 配置命令参考

## 命令

```bash
kweaver config show                    # 显示当前平台配置
kweaver config set-bd <value>          # 设置默认 business domain
```

## 说明

- DIP 产品通常使用 UUID 格式的 business domain（非 `bd_public`）
- 设置后所有命令（bkn、agent、ds、vega、call）自动使用该值
- 可用 `-bd` 标志临时覆盖
- 环境变量 `KWEAVER_BUSINESS_DOMAIN` 优先级最高
```

- [ ] **Step 3: Commit**

```bash
git add skills/kweaver/ .claude/skills/kweaver/
git commit -m "docs(skill): update kweaver skill with config command and business domain guidance"
```

---

### Task 5: Manual verification on live platform

- [ ] **Step 1: Set business domain**

```bash
kweaver config set-bd 54308785-4438-43df-9490-a7fd11df5765
```

- [ ] **Step 2: Verify config show**

```bash
kweaver config show
```
Expected: `Business Domain: 54308785-4438-43df-9490-a7fd11df5765 (config)`

- [ ] **Step 3: Verify bkn list now works without -bd flag**

```bash
kweaver bkn list --pretty
```
Expected: Shows "Demo供应链业务知识网络"

- [ ] **Step 4: Verify -bd flag still overrides**

```bash
kweaver bkn list -bd bd_public --pretty
```
Expected: Returns empty list (different domain)

- [ ] **Step 5: Verify other commands**

```bash
kweaver agent list
kweaver ds list
kweaver vega health
```
Expected: All return data from the correct business domain
