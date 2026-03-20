# Vega TypeScript CLI — Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `kweaver vega` CLI commands covering read-only Vega operations (catalogs, resources, connector-types, health/inspect) using only `/api/vega-backend/v1/` endpoints.

**Architecture:** Two new files (`src/api/vega.ts` for raw fetch, `src/commands/vega.ts` for CLI) plus minor edits to `src/cli.ts`. Follows the existing `ds` command pattern exactly. No resource layer, no new types, no `KWeaverClient` changes.

**Tech Stack:** TypeScript, Node.js `fetch`, existing auth/formatting utilities.

**Spec:** `docs/superpowers/specs/2026-03-21-vega-ts-cli-phase1-design.md`

---

## File Structure

### New Files

| File | Responsibility |
|------|---------------|
| `packages/typescript/src/api/vega.ts` | Raw fetch functions for all Vega endpoints (14 functions), local `buildHeaders()` |
| `packages/typescript/src/commands/vega.ts` | CLI arg parsing, subcommand routing, `inspect`/`stats` composite logic |
| `packages/typescript/test/e2e/vega.test.ts` | E2E tests against live Vega backend |

### Modified Files

| File | Changes |
|------|---------|
| `packages/typescript/src/cli.ts` | Add `vega` case to `run()` router + help text |
| `.claude/skills/kweaver/SKILL.md` | Add `vega` to command group table |
| `.claude/skills/kweaver/references/vega.md` | Trim to Phase 1 commands only |

---

## Task 1: API Layer — Catalog Endpoints

**Files:**
- Create: `packages/typescript/src/api/vega.ts`

- [ ] **Step 1: Create vega.ts with buildHeaders and catalog functions**

```typescript
// packages/typescript/src/api/vega.ts
import { HttpError } from "../utils/http.js";

const VEGA_BASE = "/api/vega-backend/v1";

function buildHeaders(accessToken: string, businessDomain: string): Record<string, string> {
  return {
    accept: "application/json, text/plain, */*",
    "accept-language": "zh-cn",
    authorization: `Bearer ${accessToken}`,
    token: accessToken,
    "x-business-domain": businessDomain,
    "x-language": "zh-cn",
  };
}

// ── Health ────────────────────────────────────────────────────────

export interface VegaHealthOptions {
  baseUrl: string;
  accessToken: string;
  businessDomain?: string;
}

export async function vegaHealth(options: VegaHealthOptions): Promise<string> {
  const { baseUrl, accessToken, businessDomain = "bd_public" } = options;
  const base = baseUrl.replace(/\/+$/, "");
  const response = await fetch(`${base}/health`, {
    method: "GET",
    headers: buildHeaders(accessToken, businessDomain),
  });
  const body = await response.text();
  if (!response.ok) throw new HttpError(response.status, response.statusText, body);
  return body;
}

// ── Catalogs ─────────────────────────────────────────────────────

export interface ListVegaCatalogsOptions {
  baseUrl: string;
  accessToken: string;
  status?: string;
  limit?: number;
  offset?: number;
  businessDomain?: string;
}

export async function listVegaCatalogs(options: ListVegaCatalogsOptions): Promise<string> {
  const { baseUrl, accessToken, status, limit, offset, businessDomain = "bd_public" } = options;
  const base = baseUrl.replace(/\/+$/, "");
  const url = new URL(`${base}${VEGA_BASE}/catalogs`);
  if (status) url.searchParams.set("status", status);
  if (limit !== undefined) url.searchParams.set("limit", String(limit));
  if (offset !== undefined) url.searchParams.set("offset", String(offset));
  const response = await fetch(url.toString(), {
    method: "GET",
    headers: buildHeaders(accessToken, businessDomain),
  });
  const body = await response.text();
  if (!response.ok) throw new HttpError(response.status, response.statusText, body);
  return body;
}

export interface GetVegaCatalogOptions {
  baseUrl: string;
  accessToken: string;
  id: string;
  businessDomain?: string;
}

export async function getVegaCatalog(options: GetVegaCatalogOptions): Promise<string> {
  const { baseUrl, accessToken, id, businessDomain = "bd_public" } = options;
  const base = baseUrl.replace(/\/+$/, "");
  const response = await fetch(`${base}${VEGA_BASE}/catalogs/${encodeURIComponent(id)}`, {
    method: "GET",
    headers: buildHeaders(accessToken, businessDomain),
  });
  const body = await response.text();
  if (!response.ok) throw new HttpError(response.status, response.statusText, body);
  return body;
}

export interface VegaCatalogHealthStatusOptions {
  baseUrl: string;
  accessToken: string;
  ids: string;
  businessDomain?: string;
}

export async function vegaCatalogHealthStatus(options: VegaCatalogHealthStatusOptions): Promise<string> {
  const { baseUrl, accessToken, ids, businessDomain = "bd_public" } = options;
  const base = baseUrl.replace(/\/+$/, "");
  const url = new URL(`${base}${VEGA_BASE}/catalogs/health-status`);
  url.searchParams.set("ids", ids);
  const response = await fetch(url.toString(), {
    method: "GET",
    headers: buildHeaders(accessToken, businessDomain),
  });
  const body = await response.text();
  if (!response.ok) throw new HttpError(response.status, response.statusText, body);
  return body;
}

export interface TestVegaCatalogConnectionOptions {
  baseUrl: string;
  accessToken: string;
  id: string;
  businessDomain?: string;
}

export async function testVegaCatalogConnection(options: TestVegaCatalogConnectionOptions): Promise<string> {
  const { baseUrl, accessToken, id, businessDomain = "bd_public" } = options;
  const base = baseUrl.replace(/\/+$/, "");
  const response = await fetch(`${base}${VEGA_BASE}/catalogs/${encodeURIComponent(id)}/test-connection`, {
    method: "POST",
    headers: buildHeaders(accessToken, businessDomain),
  });
  const body = await response.text();
  if (!response.ok) throw new HttpError(response.status, response.statusText, body);
  return body;
}

export interface DiscoverVegaCatalogOptions {
  baseUrl: string;
  accessToken: string;
  id: string;
  wait?: boolean;
  businessDomain?: string;
}

export async function discoverVegaCatalog(options: DiscoverVegaCatalogOptions): Promise<string> {
  const { baseUrl, accessToken, id, wait, businessDomain = "bd_public" } = options;
  const base = baseUrl.replace(/\/+$/, "");
  const url = new URL(`${base}${VEGA_BASE}/catalogs/${encodeURIComponent(id)}/discover`);
  if (wait) url.searchParams.set("wait", "true");
  const response = await fetch(url.toString(), {
    method: "POST",
    headers: buildHeaders(accessToken, businessDomain),
  });
  const body = await response.text();
  if (!response.ok) throw new HttpError(response.status, response.statusText, body);
  return body;
}

export interface ListVegaCatalogResourcesOptions {
  baseUrl: string;
  accessToken: string;
  id: string;
  category?: string;
  limit?: number;
  offset?: number;
  businessDomain?: string;
}

export async function listVegaCatalogResources(options: ListVegaCatalogResourcesOptions): Promise<string> {
  const { baseUrl, accessToken, id, category, limit, offset, businessDomain = "bd_public" } = options;
  const base = baseUrl.replace(/\/+$/, "");
  const url = new URL(`${base}${VEGA_BASE}/catalogs/${encodeURIComponent(id)}/resources`);
  if (category) url.searchParams.set("category", category);
  if (limit !== undefined) url.searchParams.set("limit", String(limit));
  if (offset !== undefined) url.searchParams.set("offset", String(offset));
  const response = await fetch(url.toString(), {
    method: "GET",
    headers: buildHeaders(accessToken, businessDomain),
  });
  const body = await response.text();
  if (!response.ok) throw new HttpError(response.status, response.statusText, body);
  return body;
}
```

- [ ] **Step 2: Verify it compiles**

Run: `cd packages/typescript && npx tsc --noEmit src/api/vega.ts`
Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add packages/typescript/src/api/vega.ts
git commit -m "feat(vega): add API layer — health + catalog endpoints"
```

---

## Task 2: API Layer — Resource, ConnectorType, DiscoverTask Endpoints

**Files:**
- Modify: `packages/typescript/src/api/vega.ts`

- [ ] **Step 1: Append resource, connector-type, and discover-task functions**

Append to `packages/typescript/src/api/vega.ts`:

```typescript
// ── Resources ────────────────────────────────────────────────────

export interface ListVegaResourcesOptions {
  baseUrl: string;
  accessToken: string;
  catalogId?: string;
  category?: string;
  status?: string;
  limit?: number;
  offset?: number;
  businessDomain?: string;
}

export async function listVegaResources(options: ListVegaResourcesOptions): Promise<string> {
  const { baseUrl, accessToken, catalogId, category, status, limit, offset, businessDomain = "bd_public" } = options;
  const base = baseUrl.replace(/\/+$/, "");
  const url = new URL(`${base}${VEGA_BASE}/resources`);
  if (catalogId) url.searchParams.set("catalog_id", catalogId);
  if (category) url.searchParams.set("category", category);
  if (status) url.searchParams.set("status", status);
  if (limit !== undefined) url.searchParams.set("limit", String(limit));
  if (offset !== undefined) url.searchParams.set("offset", String(offset));
  const response = await fetch(url.toString(), {
    method: "GET",
    headers: buildHeaders(accessToken, businessDomain),
  });
  const body = await response.text();
  if (!response.ok) throw new HttpError(response.status, response.statusText, body);
  return body;
}

export interface GetVegaResourceOptions {
  baseUrl: string;
  accessToken: string;
  id: string;
  businessDomain?: string;
}

export async function getVegaResource(options: GetVegaResourceOptions): Promise<string> {
  const { baseUrl, accessToken, id, businessDomain = "bd_public" } = options;
  const base = baseUrl.replace(/\/+$/, "");
  const response = await fetch(`${base}${VEGA_BASE}/resources/${encodeURIComponent(id)}`, {
    method: "GET",
    headers: buildHeaders(accessToken, businessDomain),
  });
  const body = await response.text();
  if (!response.ok) throw new HttpError(response.status, response.statusText, body);
  return body;
}

export interface QueryVegaResourceDataOptions {
  baseUrl: string;
  accessToken: string;
  id: string;
  body: string;
  businessDomain?: string;
}

export async function queryVegaResourceData(options: QueryVegaResourceDataOptions): Promise<string> {
  const { baseUrl, accessToken, id, body: reqBody, businessDomain = "bd_public" } = options;
  const base = baseUrl.replace(/\/+$/, "");
  const response = await fetch(`${base}${VEGA_BASE}/resources/${encodeURIComponent(id)}/data`, {
    method: "POST",
    headers: {
      ...buildHeaders(accessToken, businessDomain),
      "content-type": "application/json",
    },
    body: reqBody,
  });
  const body = await response.text();
  if (!response.ok) throw new HttpError(response.status, response.statusText, body);
  return body;
}

export interface PreviewVegaResourceOptions {
  baseUrl: string;
  accessToken: string;
  id: string;
  limit?: number;
  businessDomain?: string;
}

export async function previewVegaResource(options: PreviewVegaResourceOptions): Promise<string> {
  const { baseUrl, accessToken, id, limit = 10, businessDomain = "bd_public" } = options;
  const base = baseUrl.replace(/\/+$/, "");
  const url = new URL(`${base}${VEGA_BASE}/resources/${encodeURIComponent(id)}/preview`);
  if (limit !== undefined) url.searchParams.set("limit", String(limit));
  const response = await fetch(url.toString(), {
    method: "GET",
    headers: buildHeaders(accessToken, businessDomain),
  });
  const body = await response.text();
  if (!response.ok) throw new HttpError(response.status, response.statusText, body);
  return body;
}

// ── Connector Types ──────────────────────────────────────────────

export interface ListVegaConnectorTypesOptions {
  baseUrl: string;
  accessToken: string;
  businessDomain?: string;
}

export async function listVegaConnectorTypes(options: ListVegaConnectorTypesOptions): Promise<string> {
  const { baseUrl, accessToken, businessDomain = "bd_public" } = options;
  const base = baseUrl.replace(/\/+$/, "");
  const response = await fetch(`${base}${VEGA_BASE}/connector-types`, {
    method: "GET",
    headers: buildHeaders(accessToken, businessDomain),
  });
  const body = await response.text();
  if (!response.ok) throw new HttpError(response.status, response.statusText, body);
  return body;
}

export interface GetVegaConnectorTypeOptions {
  baseUrl: string;
  accessToken: string;
  type: string;
  businessDomain?: string;
}

export async function getVegaConnectorType(options: GetVegaConnectorTypeOptions): Promise<string> {
  const { baseUrl, accessToken, type, businessDomain = "bd_public" } = options;
  const base = baseUrl.replace(/\/+$/, "");
  const response = await fetch(`${base}${VEGA_BASE}/connector-types/${encodeURIComponent(type)}`, {
    method: "GET",
    headers: buildHeaders(accessToken, businessDomain),
  });
  const body = await response.text();
  if (!response.ok) throw new HttpError(response.status, response.statusText, body);
  return body;
}

// ── Discover Tasks ───────────────────────────────────────────────

export interface ListVegaDiscoverTasksOptions {
  baseUrl: string;
  accessToken: string;
  status?: string;
  limit?: number;
  offset?: number;
  businessDomain?: string;
}

export async function listVegaDiscoverTasks(options: ListVegaDiscoverTasksOptions): Promise<string> {
  const { baseUrl, accessToken, status, limit, offset, businessDomain = "bd_public" } = options;
  const base = baseUrl.replace(/\/+$/, "");
  const url = new URL(`${base}${VEGA_BASE}/discover-tasks`);
  if (status) url.searchParams.set("status", status);
  if (limit !== undefined) url.searchParams.set("limit", String(limit));
  if (offset !== undefined) url.searchParams.set("offset", String(offset));
  const response = await fetch(url.toString(), {
    method: "GET",
    headers: buildHeaders(accessToken, businessDomain),
  });
  const body = await response.text();
  if (!response.ok) throw new HttpError(response.status, response.statusText, body);
  return body;
}
```

- [ ] **Step 2: Verify it compiles**

Run: `cd packages/typescript && npx tsc --noEmit src/api/vega.ts`
Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add packages/typescript/src/api/vega.ts
git commit -m "feat(vega): add API layer — resources, connector-types, discover-tasks"
```

---

## Task 3: Command Layer — Router + Help + Catalog Subcommands

**Files:**
- Create: `packages/typescript/src/commands/vega.ts`

- [ ] **Step 1: Create vega.ts with router and catalog subcommands**

```typescript
// packages/typescript/src/commands/vega.ts
import { ensureValidToken, formatHttpError } from "../auth/oauth.js";
import {
  vegaHealth,
  listVegaCatalogs,
  getVegaCatalog,
  vegaCatalogHealthStatus,
  testVegaCatalogConnection,
  discoverVegaCatalog,
  listVegaCatalogResources,
  listVegaResources,
  getVegaResource,
  queryVegaResourceData,
  previewVegaResource,
  listVegaConnectorTypes,
  getVegaConnectorType,
  listVegaDiscoverTasks,
} from "../api/vega.js";
import { formatCallOutput } from "./call.js";

function printVegaHelp(): void {
  console.log(`kweaver vega

Subcommands:
  health                              Server health check
  stats                               Platform statistics
  inspect [--full]                    Combined health + catalog report

  catalog list [--status X] [--limit N] [--offset N]
  catalog get <id>
  catalog health [<ids>] [--all]
  catalog test-connection <id>
  catalog discover <id> [--wait]
  catalog resources <id> [--category X] [--limit N]

  resource list [--catalog-id X] [--category X] [--status X] [--limit N] [--offset N]
  resource get <id>
  resource data <id> -d '<body>'
  resource preview <id> [--limit N]

  connector-type list
  connector-type get <type>`);
}

export async function runVegaCommand(args: string[]): Promise<number> {
  const [subcommand, ...rest] = args;

  if (!subcommand || subcommand === "--help" || subcommand === "-h") {
    printVegaHelp();
    return 0;
  }

  try {
    if (subcommand === "health") return runVegaHealthCommand(rest);
    if (subcommand === "stats") return runVegaStatsCommand(rest);
    if (subcommand === "inspect") return runVegaInspectCommand(rest);
    if (subcommand === "catalog") return runVegaCatalogCommand(rest);
    if (subcommand === "resource") return runVegaResourceCommand(rest);
    if (subcommand === "connector-type") return runVegaConnectorTypeCommand(rest);

    console.error(`Unknown vega subcommand: ${subcommand}`);
    return 1;
  } catch (error) {
    console.error(formatHttpError(error));
    return 1;
  }
}

// ── Common arg parsing helpers ───────────────────────────────────

interface CommonFlags {
  businessDomain: string;
  pretty: boolean;
}

function parseCommonFlags(args: string[]): CommonFlags {
  let businessDomain = "bd_public";
  let pretty = true;
  for (let i = 0; i < args.length; i += 1) {
    const arg = args[i];
    if ((arg === "-bd" || arg === "--biz-domain") && args[i + 1]) {
      businessDomain = args[++i];
    }
    if (arg === "--pretty") pretty = true;
  }
  return { businessDomain, pretty };
}

// ── Health ────────────────────────────────────────────────────────

async function runVegaHealthCommand(args: string[]): Promise<number> {
  if (args.includes("--help") || args.includes("-h")) {
    console.log("kweaver vega health\n\nShow Vega server health info.");
    return 0;
  }
  const flags = parseCommonFlags(args);
  const token = await ensureValidToken();
  const body = await vegaHealth({
    baseUrl: token.baseUrl,
    accessToken: token.accessToken,
    businessDomain: flags.businessDomain,
  });
  console.log(formatCallOutput(body, flags.pretty));
  return 0;
}

// ── Stats ─────────────────────────────────────────────────────────

async function runVegaStatsCommand(args: string[]): Promise<number> {
  if (args.includes("--help") || args.includes("-h")) {
    console.log("kweaver vega stats\n\nShow platform resource counts.");
    return 0;
  }
  const flags = parseCommonFlags(args);
  const token = await ensureValidToken();
  const base = { baseUrl: token.baseUrl, accessToken: token.accessToken, businessDomain: flags.businessDomain };

  const stats: Record<string, unknown> = {};
  try {
    const catBody = await listVegaCatalogs({ ...base, limit: 100 });
    const parsed = JSON.parse(catBody) as Record<string, unknown>;
    const entries = Array.isArray(parsed) ? parsed : (parsed.entries ?? parsed.data ?? []);
    stats.catalog_count = Array.isArray(entries) ? entries.length : 0;
  } catch {
    stats.catalog_count = "error";
  }

  console.log(formatCallOutput(JSON.stringify(stats), flags.pretty));
  return 0;
}

// ── Inspect ───────────────────────────────────────────────────────

async function runVegaInspectCommand(args: string[]): Promise<number> {
  if (args.includes("--help") || args.includes("-h")) {
    console.log("kweaver vega inspect [--full]\n\nCombined health + catalog + tasks report.");
    return 0;
  }
  const flags = parseCommonFlags(args);
  const token = await ensureValidToken();
  const base = { baseUrl: token.baseUrl, accessToken: token.accessToken, businessDomain: flags.businessDomain };

  const report: Record<string, unknown> = {};

  // Health
  try {
    report.server_info = JSON.parse(await vegaHealth(base));
  } catch (err) {
    console.error(`Warning: health check failed: ${err instanceof Error ? err.message : err}`);
  }

  // Catalogs
  try {
    const catBody = await listVegaCatalogs({ ...base, limit: 100 });
    const parsed = JSON.parse(catBody) as Record<string, unknown>;
    const entries = (Array.isArray(parsed) ? parsed : (parsed.entries ?? parsed.data ?? [])) as Array<Record<string, unknown>>;
    report.catalog_summary = {
      total: entries.length,
      healthy: entries.filter((c) => c.health_status === "healthy").length,
      degraded: entries.filter((c) => c.health_status === "degraded").length,
      unhealthy: entries.filter((c) => c.health_status === "unhealthy").length,
    };
  } catch (err) {
    console.error(`Warning: catalog list failed: ${err instanceof Error ? err.message : err}`);
  }

  // Active discover tasks
  try {
    const taskBody = await listVegaDiscoverTasks({ ...base, status: "running" });
    const parsed = JSON.parse(taskBody) as Record<string, unknown>;
    const entries = Array.isArray(parsed) ? parsed : (parsed.entries ?? parsed.data ?? []);
    report.active_discover_tasks = entries;
  } catch (err) {
    console.error(`Warning: discover tasks failed: ${err instanceof Error ? err.message : err}`);
  }

  console.log(formatCallOutput(JSON.stringify(report), flags.pretty));
  return 0;
}

// ── Catalog ───────────────────────────────────────────────────────

async function runVegaCatalogCommand(args: string[]): Promise<number> {
  const [sub, ...rest] = args;
  if (!sub || sub === "--help" || sub === "-h") {
    console.log(`kweaver vega catalog <subcommand>

Subcommands:
  list [--status X] [--limit N] [--offset N]
  get <id>
  health [<ids>] [--all]
  test-connection <id>
  discover <id> [--wait]
  resources <id> [--category X] [--limit N]`);
    return 0;
  }

  if (sub === "list") return runCatalogList(rest);
  if (sub === "get") return runCatalogGet(rest);
  if (sub === "health") return runCatalogHealth(rest);
  if (sub === "test-connection") return runCatalogTestConnection(rest);
  if (sub === "discover") return runCatalogDiscover(rest);
  if (sub === "resources") return runCatalogResources(rest);

  console.error(`Unknown catalog subcommand: ${sub}`);
  return 1;
}

async function runCatalogList(args: string[]): Promise<number> {
  let status: string | undefined;
  let limit: number | undefined;
  let offset: number | undefined;
  const flags = parseCommonFlags(args);

  for (let i = 0; i < args.length; i += 1) {
    const arg = args[i];
    if (arg === "--help" || arg === "-h") {
      console.log("kweaver vega catalog list [--status X] [--limit N] [--offset N]");
      return 0;
    }
    if (arg === "--status" && args[i + 1]) { status = args[++i]; continue; }
    if (arg === "--limit" && args[i + 1]) { limit = parseInt(args[++i], 10); continue; }
    if (arg === "--offset" && args[i + 1]) { offset = parseInt(args[++i], 10); continue; }
  }

  const token = await ensureValidToken();
  const body = await listVegaCatalogs({
    baseUrl: token.baseUrl, accessToken: token.accessToken,
    status, limit, offset, businessDomain: flags.businessDomain,
  });
  console.log(formatCallOutput(body, flags.pretty));
  return 0;
}

async function runCatalogGet(args: string[]): Promise<number> {
  const id = args.find((a) => !a.startsWith("-"));
  if (!id) { console.error("Usage: kweaver vega catalog get <id>"); return 1; }
  const flags = parseCommonFlags(args);
  const token = await ensureValidToken();
  const body = await getVegaCatalog({
    baseUrl: token.baseUrl, accessToken: token.accessToken,
    id, businessDomain: flags.businessDomain,
  });
  console.log(formatCallOutput(body, flags.pretty));
  return 0;
}

async function runCatalogHealth(args: string[]): Promise<number> {
  const flags = parseCommonFlags(args);
  const all = args.includes("--all");
  const ids = args.filter((a) => !a.startsWith("-"));

  const token = await ensureValidToken();
  const base = { baseUrl: token.baseUrl, accessToken: token.accessToken, businessDomain: flags.businessDomain };

  let idsStr: string;
  if (all) {
    // Fetch all catalog IDs first
    const catBody = await listVegaCatalogs({ ...base, limit: 100 });
    const parsed = JSON.parse(catBody) as Record<string, unknown>;
    const entries = (Array.isArray(parsed) ? parsed : (parsed.entries ?? parsed.data ?? [])) as Array<Record<string, unknown>>;
    idsStr = entries.map((c) => String(c.id ?? "")).filter(Boolean).join(",");
    if (!idsStr) { console.log("No catalogs found."); return 0; }
  } else if (ids.length > 0) {
    idsStr = ids.join(",");
  } else {
    console.error("Usage: kweaver vega catalog health [<ids...>] [--all]");
    return 1;
  }

  const body = await vegaCatalogHealthStatus({ ...base, ids: idsStr });
  console.log(formatCallOutput(body, flags.pretty));
  return 0;
}

async function runCatalogTestConnection(args: string[]): Promise<number> {
  const id = args.find((a) => !a.startsWith("-"));
  if (!id) { console.error("Usage: kweaver vega catalog test-connection <id>"); return 1; }
  const flags = parseCommonFlags(args);
  const token = await ensureValidToken();
  const body = await testVegaCatalogConnection({
    baseUrl: token.baseUrl, accessToken: token.accessToken,
    id, businessDomain: flags.businessDomain,
  });
  console.log(formatCallOutput(body, flags.pretty));
  return 0;
}

async function runCatalogDiscover(args: string[]): Promise<number> {
  const id = args.find((a) => !a.startsWith("-"));
  if (!id) { console.error("Usage: kweaver vega catalog discover <id> [--wait]"); return 1; }
  const wait = args.includes("--wait");
  const flags = parseCommonFlags(args);
  const token = await ensureValidToken();
  const body = await discoverVegaCatalog({
    baseUrl: token.baseUrl, accessToken: token.accessToken,
    id, wait, businessDomain: flags.businessDomain,
  });
  console.log(formatCallOutput(body, flags.pretty));
  return 0;
}

async function runCatalogResources(args: string[]): Promise<number> {
  let id = "";
  let category: string | undefined;
  let limit: number | undefined;
  const flags = parseCommonFlags(args);

  for (let i = 0; i < args.length; i += 1) {
    const arg = args[i];
    if (arg === "--help" || arg === "-h") {
      console.log("kweaver vega catalog resources <id> [--category X] [--limit N]");
      return 0;
    }
    if (arg === "--category" && args[i + 1]) { category = args[++i]; continue; }
    if (arg === "--limit" && args[i + 1]) { limit = parseInt(args[++i], 10); continue; }
    if (!arg.startsWith("-") && !id) { id = arg; continue; }
  }

  if (!id) { console.error("Usage: kweaver vega catalog resources <id> [--category X] [--limit N]"); return 1; }

  const token = await ensureValidToken();
  const body = await listVegaCatalogResources({
    baseUrl: token.baseUrl, accessToken: token.accessToken,
    id, category, limit, businessDomain: flags.businessDomain,
  });
  console.log(formatCallOutput(body, flags.pretty));
  return 0;
}
```

- [ ] **Step 2: Verify it compiles**

Run: `cd packages/typescript && npx tsc --noEmit src/commands/vega.ts`
Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add packages/typescript/src/commands/vega.ts
git commit -m "feat(vega): add command layer — router + catalog subcommands"
```

---

## Task 4: Command Layer — Resource + ConnectorType Subcommands

**Files:**
- Modify: `packages/typescript/src/commands/vega.ts`

- [ ] **Step 1: Append resource and connector-type subcommand handlers**

Append to `packages/typescript/src/commands/vega.ts`:

```typescript
// ── Resource ──────────────────────────────────────────────────────

async function runVegaResourceCommand(args: string[]): Promise<number> {
  const [sub, ...rest] = args;
  if (!sub || sub === "--help" || sub === "-h") {
    console.log(`kweaver vega resource <subcommand>

Subcommands:
  list [--catalog-id X] [--category X] [--status X] [--limit N] [--offset N]
  get <id>
  data <id> -d '<body>'
  preview <id> [--limit N]`);
    return 0;
  }

  if (sub === "list") return runResourceList(rest);
  if (sub === "get") return runResourceGet(rest);
  if (sub === "data") return runResourceData(rest);
  if (sub === "preview") return runResourcePreview(rest);

  console.error(`Unknown resource subcommand: ${sub}`);
  return 1;
}

async function runResourceList(args: string[]): Promise<number> {
  let catalogId: string | undefined;
  let category: string | undefined;
  let status: string | undefined;
  let limit: number | undefined;
  let offset: number | undefined;
  const flags = parseCommonFlags(args);

  for (let i = 0; i < args.length; i += 1) {
    const arg = args[i];
    if (arg === "--help" || arg === "-h") {
      console.log("kweaver vega resource list [--catalog-id X] [--category X] [--status X] [--limit N] [--offset N]");
      return 0;
    }
    if (arg === "--catalog-id" && args[i + 1]) { catalogId = args[++i]; continue; }
    if (arg === "--category" && args[i + 1]) { category = args[++i]; continue; }
    if (arg === "--status" && args[i + 1]) { status = args[++i]; continue; }
    if (arg === "--limit" && args[i + 1]) { limit = parseInt(args[++i], 10); continue; }
    if (arg === "--offset" && args[i + 1]) { offset = parseInt(args[++i], 10); continue; }
  }

  const token = await ensureValidToken();
  const body = await listVegaResources({
    baseUrl: token.baseUrl, accessToken: token.accessToken,
    catalogId, category, status, limit, offset, businessDomain: flags.businessDomain,
  });
  console.log(formatCallOutput(body, flags.pretty));
  return 0;
}

async function runResourceGet(args: string[]): Promise<number> {
  const id = args.find((a) => !a.startsWith("-"));
  if (!id) { console.error("Usage: kweaver vega resource get <id>"); return 1; }
  const flags = parseCommonFlags(args);
  const token = await ensureValidToken();
  const body = await getVegaResource({
    baseUrl: token.baseUrl, accessToken: token.accessToken,
    id, businessDomain: flags.businessDomain,
  });
  console.log(formatCallOutput(body, flags.pretty));
  return 0;
}

async function runResourceData(args: string[]): Promise<number> {
  let id = "";
  let data = "";
  const flags = parseCommonFlags(args);

  for (let i = 0; i < args.length; i += 1) {
    const arg = args[i];
    if (arg === "--help" || arg === "-h") {
      console.log("kweaver vega resource data <id> -d '<body>'");
      return 0;
    }
    if ((arg === "-d" || arg === "--data") && args[i + 1]) { data = args[++i]; continue; }
    if (!arg.startsWith("-") && !id) { id = arg; continue; }
  }

  if (!id || !data) {
    console.error("Usage: kweaver vega resource data <id> -d '<body>'");
    return 1;
  }

  const token = await ensureValidToken();
  const body = await queryVegaResourceData({
    baseUrl: token.baseUrl, accessToken: token.accessToken,
    id, body: data, businessDomain: flags.businessDomain,
  });
  console.log(formatCallOutput(body, flags.pretty));
  return 0;
}

async function runResourcePreview(args: string[]): Promise<number> {
  let id = "";
  let limit: number | undefined;
  const flags = parseCommonFlags(args);

  for (let i = 0; i < args.length; i += 1) {
    const arg = args[i];
    if (arg === "--help" || arg === "-h") {
      console.log("kweaver vega resource preview <id> [--limit N]");
      return 0;
    }
    if (arg === "--limit" && args[i + 1]) { limit = parseInt(args[++i], 10); continue; }
    if (!arg.startsWith("-") && !id) { id = arg; continue; }
  }

  if (!id) { console.error("Usage: kweaver vega resource preview <id> [--limit N]"); return 1; }

  const token = await ensureValidToken();
  const body = await previewVegaResource({
    baseUrl: token.baseUrl, accessToken: token.accessToken,
    id, limit, businessDomain: flags.businessDomain,
  });
  console.log(formatCallOutput(body, flags.pretty));
  return 0;
}

// ── Connector Type ────────────────────────────────────────────────

async function runVegaConnectorTypeCommand(args: string[]): Promise<number> {
  const [sub, ...rest] = args;
  if (!sub || sub === "--help" || sub === "-h") {
    console.log(`kweaver vega connector-type <subcommand>

Subcommands:
  list    List available connector types
  get <type>  Get connector type details`);
    return 0;
  }

  if (sub === "list") return runConnectorTypeList(rest);
  if (sub === "get") return runConnectorTypeGet(rest);

  console.error(`Unknown connector-type subcommand: ${sub}`);
  return 1;
}

async function runConnectorTypeList(args: string[]): Promise<number> {
  if (args.includes("--help") || args.includes("-h")) {
    console.log("kweaver vega connector-type list");
    return 0;
  }
  const flags = parseCommonFlags(args);
  const token = await ensureValidToken();
  const body = await listVegaConnectorTypes({
    baseUrl: token.baseUrl, accessToken: token.accessToken,
    businessDomain: flags.businessDomain,
  });
  console.log(formatCallOutput(body, flags.pretty));
  return 0;
}

async function runConnectorTypeGet(args: string[]): Promise<number> {
  const type = args.find((a) => !a.startsWith("-"));
  if (!type) { console.error("Usage: kweaver vega connector-type get <type>"); return 1; }
  const flags = parseCommonFlags(args);
  const token = await ensureValidToken();
  const body = await getVegaConnectorType({
    baseUrl: token.baseUrl, accessToken: token.accessToken,
    type, businessDomain: flags.businessDomain,
  });
  console.log(formatCallOutput(body, flags.pretty));
  return 0;
}
```

- [ ] **Step 2: Verify it compiles**

Run: `cd packages/typescript && npx tsc --noEmit src/commands/vega.ts`
Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add packages/typescript/src/commands/vega.ts
git commit -m "feat(vega): add resource + connector-type subcommands"
```

---

## Task 5: Wire into CLI Router

**Files:**
- Modify: `packages/typescript/src/cli.ts`

- [ ] **Step 1: Add vega import and route**

In `packages/typescript/src/cli.ts`:

Add import at top:
```typescript
import { runVegaCommand } from "./commands/vega.js";
```

Add route in `run()` function, before the "Unknown command" fallback:
```typescript
  if (command === "vega") {
    return runVegaCommand(rest);
  }
```

Add to `printHelp()` Usage section:
```
  kweaver vega [health|stats|inspect|catalog|resource|connector-type]
```

Add to Commands section:
```
  vega           Vega observability platform (catalogs, resources, connector-types, health)
```

- [ ] **Step 2: Verify CLI help shows vega**

Run: `cd packages/typescript && npx tsx src/cli.ts --help`
Expected: output includes `vega` in both Usage and Commands sections

- [ ] **Step 3: Verify vega subcommand help works**

Run: `cd packages/typescript && npx tsx src/cli.ts vega --help`
Expected: shows vega subcommand list

- [ ] **Step 4: Compile check**

Run: `cd packages/typescript && npx tsc --noEmit`
Expected: no errors across entire project

- [ ] **Step 5: Commit**

```bash
git add packages/typescript/src/cli.ts
git commit -m "feat(vega): wire vega command into CLI router"
```

---

## Task 6: E2E Tests

**Files:**
- Create: `packages/typescript/test/e2e/vega.test.ts`

- [ ] **Step 1: Write e2e tests**

```typescript
// packages/typescript/test/e2e/vega.test.ts
import test from "node:test";
import assert from "node:assert/strict";
import { runCli, shouldSkipE2e } from "./setup.js";

function extractEntries(raw: unknown): unknown[] {
  if (Array.isArray(raw)) return raw;
  if (raw && typeof raw === "object") {
    const obj = raw as Record<string, unknown>;
    for (const key of ["entries", "data", "records"]) {
      if (Array.isArray(obj[key])) return obj[key] as unknown[];
    }
  }
  return [];
}

test("e2e: vega health returns server info", { skip: shouldSkipE2e() }, async () => {
  const { code, stdout } = await runCli(["vega", "health"]);
  assert.equal(code, 0, "vega health should succeed");
  const parsed = JSON.parse(stdout) as Record<string, unknown>;
  assert.ok(parsed.server_name !== undefined || Object.keys(parsed).length > 0, "should return server info");
});

test("e2e: vega catalog list returns array", { skip: shouldSkipE2e() }, async () => {
  const { code, stdout } = await runCli(["vega", "catalog", "list"]);
  assert.equal(code, 0);
  const entries = extractEntries(JSON.parse(stdout));
  assert.ok(entries.length >= 0, "catalog list should return parseable entries");
});

test("e2e: vega connector-type list returns array", { skip: shouldSkipE2e() }, async () => {
  const { code, stdout } = await runCli(["vega", "connector-type", "list"]);
  assert.equal(code, 0);
  const entries = extractEntries(JSON.parse(stdout));
  assert.ok(entries.length >= 0, "connector-type list should return parseable entries");
});

test("e2e: vega inspect returns composite report", { skip: shouldSkipE2e() }, async () => {
  const { code, stdout } = await runCli(["vega", "inspect"]);
  assert.equal(code, 0);
  const report = JSON.parse(stdout) as Record<string, unknown>;
  assert.ok("server_info" in report || "catalog_summary" in report, "inspect should return a report");
});

test("e2e: vega resource list returns array", { skip: shouldSkipE2e() }, async () => {
  const { code, stdout } = await runCli(["vega", "resource", "list"]);
  assert.equal(code, 0);
  const entries = extractEntries(JSON.parse(stdout));
  assert.ok(entries.length >= 0, "resource list should return parseable entries");
});

test("e2e: vega stats returns counts", { skip: shouldSkipE2e() }, async () => {
  const { code, stdout } = await runCli(["vega", "stats"]);
  assert.equal(code, 0);
  const parsed = JSON.parse(stdout) as Record<string, unknown>;
  assert.ok("catalog_count" in parsed, "stats should include catalog_count");
});

test("e2e: vega --help returns help text", async () => {
  const { code, stdout } = await runCli(["vega", "--help"]);
  assert.equal(code, 0);
  assert.ok(stdout.includes("catalog"), "help should mention catalog");
  assert.ok(stdout.includes("resource"), "help should mention resource");
  assert.ok(stdout.includes("connector-type"), "help should mention connector-type");
});
```

- [ ] **Step 2: Run help test (always works, no backend needed)**

Run: `cd packages/typescript && npx tsx --test test/e2e/vega.test.ts --test-name-pattern "help"`
Expected: PASS

- [ ] **Step 3: Run full e2e suite if backend available**

Run: `cd packages/typescript && npx tsx --test test/e2e/vega.test.ts`
Expected: PASS (or skip if no KWEAVER_BASE_URL)

- [ ] **Step 4: Commit**

```bash
git add packages/typescript/test/e2e/vega.test.ts
git commit -m "test(vega): add e2e tests for vega CLI commands"
```

---

## Task 7: Update Skill Files

**Files:**
- Modify: `.claude/skills/kweaver/SKILL.md`
- Modify: `.claude/skills/kweaver/references/vega.md`

- [ ] **Step 1: Add vega to SKILL.md command group table**

In `.claude/skills/kweaver/SKILL.md`, add a row to the command group table:

```
| `vega` | Vega 可观测平台（catalogs、resources、connector-types、health） | `references/vega.md` |
```

- [ ] **Step 2: Update SKILL.md description to match actual capabilities**

Remove or adjust Vega trigger words that reference unimplemented features (指标模型, DSL 查询). Keep: "Catalog", "Vega", "健康检查", "巡检".

- [ ] **Step 3: Rewrite references/vega.md to Phase 1 scope**

Replace the full content of `.claude/skills/kweaver/references/vega.md` with only the implemented commands (remove model, query dsl/promql, trace, task sections that use `mdl-*` paths).

- [ ] **Step 4: Remove orphaned reference files**

Delete `references/action.md` and `references/query.md` (redundant with `bkn.md`).

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/kweaver/
git commit -m "docs(skill): update kweaver skill for vega CLI phase 1"
```

---

## Task 8: Final Regression

- [ ] **Step 1: Full TypeScript compile check**

Run: `cd packages/typescript && npx tsc --noEmit`
Expected: no errors

- [ ] **Step 2: Run existing tests to verify no regressions**

Run: `cd packages/typescript && npx tsx --test test/*.test.ts`
Expected: all existing tests pass

- [ ] **Step 3: Run vega e2e tests**

Run: `cd packages/typescript && npx tsx --test test/e2e/vega.test.ts`
Expected: all pass (or skip gracefully)

- [ ] **Step 4: Manual smoke test**

Run: `cd packages/typescript && npx tsx src/cli.ts vega health`
Verify: returns JSON or clear error if no backend
