# import-csv Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `kweaver ds import-csv` and `kweaver bkn create-from-csv` CLI commands to import CSV files into a KWeaver datasource via the dataflow API, then optionally build a Knowledge Network.

**Architecture:** New `src/api/dataflow.ts` wraps 4 dataflow endpoints. `ds import-csv` in `src/commands/ds.ts` handles CSV parsing, batching, and DAG construction. `bkn create-from-csv` in `src/commands/bkn.ts` composes import + `create-from-ds`. Skill guide updated.

**Tech Stack:** TypeScript, Node.js 22+, `csv-parse` for CSV parsing, native `fetch` for HTTP.

**Spec:** `docs/superpowers/specs/2026-03-24-import-csv-design.md`

**Reference implementation:** `packages/python/tests/e2e/fixtures/db.py`

---

### Task 1: Add `csv-parse` dependency

**Files:**
- Modify: `packages/typescript/package.json`

- [ ] **Step 1: Install csv-parse**

```bash
cd packages/typescript && npm install csv-parse
```

- [ ] **Step 2: Verify installation**

```bash
node -e "require('csv-parse/sync')"
```

Expected: no error

- [ ] **Step 3: Commit**

```bash
git add packages/typescript/package.json packages/typescript/package-lock.json
git commit -m "deps: add csv-parse for CSV import support"
```

---

### Task 2: Dataflow API client — tests

**Files:**
- Create: `packages/typescript/test/dataflow.test.ts`

- [ ] **Step 1: Write tests for all 4 endpoints + execute convenience method**

```typescript
import test from "node:test";
import assert from "node:assert/strict";
import {
  createDataflow,
  runDataflow,
  pollDataflowResults,
  deleteDataflow,
  executeDataflow,
} from "../src/api/dataflow.js";

const BASE = "https://mock.kweaver.test";
const TOKEN = "test-token";
const BD = "bd_public";

test("createDataflow sends POST and returns id", async () => {
  const orig = globalThis.fetch;
  let captured: { url: string; method: string; body: unknown } | undefined;
  globalThis.fetch = async (input: string | URL | Request, init?: RequestInit) => {
    captured = {
      url: typeof input === "string" ? input : input.toString(),
      method: init?.method ?? "GET",
      body: init?.body ? JSON.parse(init.body as string) : undefined,
    };
    return new Response(JSON.stringify({ id: "dag-123" }), { status: 200 });
  };
  try {
    const result = await createDataflow({
      baseUrl: BASE,
      accessToken: TOKEN,
      businessDomain: BD,
      body: {
        title: "test-dag",
        trigger_config: { operator: "@trigger/manual" },
        steps: [
          { id: "trigger", title: "trigger", operator: "@trigger/manual", parameters: {} },
        ],
      },
    });
    assert.equal(result, "dag-123");
    assert.ok(captured!.url.includes("/api/automation/v1/data-flow/flow"));
    assert.equal(captured!.method, "POST");
  } finally {
    globalThis.fetch = orig;
  }
});

test("runDataflow sends POST with empty body", async () => {
  const orig = globalThis.fetch;
  let capturedBody: unknown;
  globalThis.fetch = async (_input: string | URL | Request, init?: RequestInit) => {
    capturedBody = init?.body ? JSON.parse(init.body as string) : undefined;
    return new Response("", { status: 200 });
  };
  try {
    await runDataflow({ baseUrl: BASE, accessToken: TOKEN, businessDomain: BD, dagId: "dag-123" });
    assert.deepEqual(capturedBody, {});
  } finally {
    globalThis.fetch = orig;
  }
});

test("pollDataflowResults returns success status", async () => {
  const orig = globalThis.fetch;
  globalThis.fetch = async () =>
    new Response(JSON.stringify({ results: [{ status: "success" }] }), { status: 200 });
  try {
    const result = await pollDataflowResults({
      baseUrl: BASE,
      accessToken: TOKEN,
      businessDomain: BD,
      dagId: "dag-123",
      timeout: 5,
      interval: 0.1,
    });
    assert.equal(result.status, "success");
  } finally {
    globalThis.fetch = orig;
  }
});

test("pollDataflowResults returns completed as success", async () => {
  const orig = globalThis.fetch;
  globalThis.fetch = async () =>
    new Response(JSON.stringify({ results: [{ status: "completed" }] }), { status: 200 });
  try {
    const result = await pollDataflowResults({
      baseUrl: BASE,
      accessToken: TOKEN,
      businessDomain: BD,
      dagId: "dag-123",
      timeout: 5,
      interval: 0.1,
    });
    assert.equal(result.status, "completed");
  } finally {
    globalThis.fetch = orig;
  }
});

test("pollDataflowResults throws on failed status", async () => {
  const orig = globalThis.fetch;
  globalThis.fetch = async () =>
    new Response(JSON.stringify({ results: [{ status: "failed", reason: "bad data" }] }), {
      status: 200,
    });
  try {
    await assert.rejects(
      () =>
        pollDataflowResults({
          baseUrl: BASE,
          accessToken: TOKEN,
          businessDomain: BD,
          dagId: "dag-123",
          timeout: 5,
          interval: 0.1,
        }),
      (err: Error) => {
        assert.ok(err.message.includes("bad data"));
        return true;
      },
    );
  } finally {
    globalThis.fetch = orig;
  }
});

test("pollDataflowResults throws on timeout", async () => {
  const orig = globalThis.fetch;
  globalThis.fetch = async () =>
    new Response(JSON.stringify({ results: [] }), { status: 200 });
  try {
    await assert.rejects(
      () =>
        pollDataflowResults({
          baseUrl: BASE,
          accessToken: TOKEN,
          businessDomain: BD,
          dagId: "dag-123",
          timeout: 0.3,
          interval: 0.1,
        }),
      (err: Error) => {
        assert.ok(err.message.includes("timeout") || err.message.includes("did not complete"));
        return true;
      },
    );
  } finally {
    globalThis.fetch = orig;
  }
});

test("deleteDataflow sends DELETE", async () => {
  const orig = globalThis.fetch;
  let capturedMethod = "";
  globalThis.fetch = async (_input: string | URL | Request, init?: RequestInit) => {
    capturedMethod = init?.method ?? "GET";
    return new Response("", { status: 200 });
  };
  try {
    await deleteDataflow({ baseUrl: BASE, accessToken: TOKEN, businessDomain: BD, dagId: "dag-123" });
    assert.equal(capturedMethod, "DELETE");
  } finally {
    globalThis.fetch = orig;
  }
});

test("executeDataflow runs full lifecycle and cleans up", async () => {
  const orig = globalThis.fetch;
  const calls: string[] = [];
  globalThis.fetch = async (input: string | URL | Request, init?: RequestInit) => {
    const url = typeof input === "string" ? input : input.toString();
    const method = init?.method ?? "GET";
    calls.push(`${method} ${url.replace(BASE, "")}`);

    if (method === "POST" && url.includes("/data-flow/flow")) {
      return new Response(JSON.stringify({ id: "dag-456" }), { status: 200 });
    }
    if (method === "POST" && url.includes("/run-instance/")) {
      return new Response("", { status: 200 });
    }
    if (method === "GET" && url.includes("/dag/")) {
      return new Response(JSON.stringify({ results: [{ status: "success" }] }), { status: 200 });
    }
    if (method === "DELETE") {
      return new Response("", { status: 200 });
    }
    return new Response("", { status: 404 });
  };
  try {
    const result = await executeDataflow({
      baseUrl: BASE,
      accessToken: TOKEN,
      businessDomain: BD,
      body: {
        title: "test",
        trigger_config: { operator: "@trigger/manual" },
        steps: [{ id: "trigger", title: "trigger", operator: "@trigger/manual", parameters: {} }],
      },
      timeout: 5,
      pollInterval: 0.1,
    });
    assert.equal(result.status, "success");
    assert.equal(calls.length, 4);
    assert.ok(calls[0].startsWith("POST"));  // create
    assert.ok(calls[1].startsWith("POST"));  // run
    assert.ok(calls[2].startsWith("GET"));   // poll
    assert.ok(calls[3].startsWith("DELETE")); // delete
  } finally {
    globalThis.fetch = orig;
  }
});

test("executeDataflow cleans up DAG even on failure", async () => {
  const orig = globalThis.fetch;
  let deleteCalled = false;
  globalThis.fetch = async (input: string | URL | Request, init?: RequestInit) => {
    const url = typeof input === "string" ? input : input.toString();
    const method = init?.method ?? "GET";

    if (method === "POST" && url.includes("/data-flow/flow")) {
      return new Response(JSON.stringify({ id: "dag-err" }), { status: 200 });
    }
    if (method === "POST" && url.includes("/run-instance/")) {
      return new Response("", { status: 200 });
    }
    if (method === "GET" && url.includes("/dag/")) {
      return new Response(JSON.stringify({ results: [{ status: "failed", reason: "boom" }] }), {
        status: 200,
      });
    }
    if (method === "DELETE") {
      deleteCalled = true;
      return new Response("", { status: 200 });
    }
    return new Response("", { status: 404 });
  };
  try {
    await assert.rejects(() =>
      executeDataflow({
        baseUrl: BASE,
        accessToken: TOKEN,
        businessDomain: BD,
        body: {
          title: "test-fail",
          trigger_config: { operator: "@trigger/manual" },
          steps: [{ id: "trigger", title: "trigger", operator: "@trigger/manual", parameters: {} }],
        },
        timeout: 5,
        pollInterval: 0.1,
      }),
    );
    assert.ok(deleteCalled, "DAG should be deleted even on failure");
  } finally {
    globalThis.fetch = orig;
  }
});
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd packages/typescript && npx tsx --test test/dataflow.test.ts
```

Expected: FAIL — module `../src/api/dataflow.js` not found

- [ ] **Step 3: Commit**

```bash
git add test/dataflow.test.ts
git commit -m "test: add dataflow API client tests (red)"
```

---

### Task 3: Dataflow API client — implementation

**Files:**
- Create: `packages/typescript/src/api/dataflow.ts`

- [ ] **Step 1: Implement dataflow.ts**

```typescript
import { HttpError } from "../utils/http.js";

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

// ── Types ────────────────────────────────────────────────────────────────────

export interface DataflowStep {
  id: string;
  title: string;
  operator: string;
  parameters: Record<string, unknown>;
}

export interface DataflowCreateBody {
  title: string;
  description?: string;
  trigger_config: { operator: string };
  steps: DataflowStep[];
}

export interface DataflowResult {
  status: "success" | "completed" | "failed" | "error";
  reason?: string;
}

// ── Create ───────────────────────────────────────────────────────────────────

export interface CreateDataflowOptions {
  baseUrl: string;
  accessToken: string;
  businessDomain?: string;
  body: DataflowCreateBody;
}

export async function createDataflow(options: CreateDataflowOptions): Promise<string> {
  const { baseUrl, accessToken, businessDomain = "bd_public", body } = options;
  const base = baseUrl.replace(/\/+$/, "");
  const url = `${base}/api/automation/v1/data-flow/flow`;
  const response = await fetch(url, {
    method: "POST",
    headers: { ...buildHeaders(accessToken, businessDomain), "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new HttpError(response.status, response.statusText, await response.text());
  const data = (await response.json()) as Record<string, unknown>;
  const id = data.id ?? data.dag_id;
  if (!id) throw new Error("Dataflow create response missing id");
  return String(id);
}

// ── Run ──────────────────────────────────────────────────────────────────────

export interface RunDataflowOptions {
  baseUrl: string;
  accessToken: string;
  businessDomain?: string;
  dagId: string;
}

export async function runDataflow(options: RunDataflowOptions): Promise<void> {
  const { baseUrl, accessToken, businessDomain = "bd_public", dagId } = options;
  const base = baseUrl.replace(/\/+$/, "");
  const url = `${base}/api/automation/v1/run-instance/${encodeURIComponent(dagId)}`;
  const response = await fetch(url, {
    method: "POST",
    headers: { ...buildHeaders(accessToken, businessDomain), "content-type": "application/json" },
    body: JSON.stringify({}),
  });
  if (!response.ok) throw new HttpError(response.status, response.statusText, await response.text());
}

// ── Poll Results ─────────────────────────────────────────────────────────────

export interface PollDataflowOptions {
  baseUrl: string;
  accessToken: string;
  businessDomain?: string;
  dagId: string;
  timeout?: number;    // seconds, default 900
  interval?: number;   // seconds, default 3
}

export async function pollDataflowResults(options: PollDataflowOptions): Promise<DataflowResult> {
  const {
    baseUrl,
    accessToken,
    businessDomain = "bd_public",
    dagId,
    timeout = 900,
    interval = 3,
  } = options;
  const base = baseUrl.replace(/\/+$/, "");
  const url = `${base}/api/automation/v1/dag/${encodeURIComponent(dagId)}/results`;
  const deadline = Date.now() + timeout * 1000;

  while (Date.now() < deadline) {
    const response = await fetch(url, {
      method: "GET",
      headers: buildHeaders(accessToken, businessDomain),
    });
    if (response.ok) {
      const data = (await response.json()) as { results?: Array<{ status?: string; reason?: string }> };
      const results = data.results ?? [];
      if (results.length > 0) {
        const first = results[0];
        const status = first.status ?? "";
        if (status === "success" || status === "completed") {
          return { status: status as DataflowResult["status"] };
        }
        if (status === "failed" || status === "error") {
          throw new Error(`Dataflow failed: ${first.reason ?? "unknown"}`);
        }
      }
    }
    await new Promise((r) => setTimeout(r, interval * 1000));
  }

  throw new Error(`Dataflow ${dagId} did not complete within ${timeout}s (timeout)`);
}

// ── Delete ───────────────────────────────────────────────────────────────────

export interface DeleteDataflowOptions {
  baseUrl: string;
  accessToken: string;
  businessDomain?: string;
  dagId: string;
}

export async function deleteDataflow(options: DeleteDataflowOptions): Promise<void> {
  const { baseUrl, accessToken, businessDomain = "bd_public", dagId } = options;
  const base = baseUrl.replace(/\/+$/, "");
  const url = `${base}/api/automation/v1/data-flow/flow/${encodeURIComponent(dagId)}`;
  await fetch(url, {
    method: "DELETE",
    headers: buildHeaders(accessToken, businessDomain),
  });
  // best-effort delete, ignore errors
}

// ── Execute (convenience) ────────────────────────────────────────────────────

export interface ExecuteDataflowOptions {
  baseUrl: string;
  accessToken: string;
  businessDomain?: string;
  body: DataflowCreateBody;
  timeout?: number;
  pollInterval?: number;
}

export async function executeDataflow(options: ExecuteDataflowOptions): Promise<DataflowResult> {
  const { baseUrl, accessToken, businessDomain, body, timeout, pollInterval } = options;
  const base = { baseUrl, accessToken, businessDomain };
  const dagId = await createDataflow({ ...base, body });
  try {
    await runDataflow({ ...base, dagId });
    return await pollDataflowResults({ ...base, dagId, timeout, interval: pollInterval });
  } finally {
    await deleteDataflow({ ...base, dagId }).catch(() => {});
  }
}
```

- [ ] **Step 2: Run tests to verify they pass**

```bash
cd packages/typescript && npx tsx --test test/dataflow.test.ts
```

Expected: all 9 tests PASS

- [ ] **Step 3: Commit**

```bash
git add src/api/dataflow.ts
git commit -m "feat: add dataflow API client (create/run/poll/delete/execute)"
```

---

### Task 4: CSV import logic — tests

**Files:**
- Create: `packages/typescript/test/import-csv.test.ts`

Tests cover: CSV parsing, table name generation, batch splitting, field mapping, DAG body construction.

- [ ] **Step 1: Write tests**

```typescript
import test from "node:test";
import assert from "node:assert/strict";
import { writeFileSync, mkdirSync, rmSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";
import {
  parseCsvFile,
  buildTableName,
  splitBatches,
  buildFieldMappings,
  buildDagBody,
} from "../src/commands/import-csv.js";

const TMP = join(tmpdir(), "kweaver-import-csv-test");

test("setup", () => {
  mkdirSync(TMP, { recursive: true });
});

test("parseCsvFile parses valid UTF-8 CSV", async () => {
  const file = join(TMP, "valid.csv");
  writeFileSync(file, "name,age\nAlice,30\nBob,25\n");
  const { headers, rows } = await parseCsvFile(file);
  assert.deepEqual(headers, ["name", "age"]);
  assert.equal(rows.length, 2);
  assert.equal(rows[0].name, "Alice");
  assert.equal(rows[1].age, "25");
});

test("parseCsvFile handles UTF-8 BOM", async () => {
  const file = join(TMP, "bom.csv");
  writeFileSync(file, "\uFEFFcode,value\nA,1\n");
  const { headers } = await parseCsvFile(file);
  assert.deepEqual(headers, ["code", "value"]);
});

test("parseCsvFile converts empty strings to null", async () => {
  const file = join(TMP, "nulls.csv");
  writeFileSync(file, "a,b\n1,\n,2\n");
  const { rows } = await parseCsvFile(file);
  assert.equal(rows[0].b, null);
  assert.equal(rows[1].a, null);
});

test("parseCsvFile throws on invalid CSV (column count mismatch)", async () => {
  const file = join(TMP, "bad.csv");
  writeFileSync(file, "a,b\n1,2,3\n");
  await assert.rejects(() => parseCsvFile(file));
});

test("parseCsvFile returns empty rows for header-only file", async () => {
  const file = join(TMP, "empty.csv");
  writeFileSync(file, "a,b\n");
  const { headers, rows } = await parseCsvFile(file);
  assert.deepEqual(headers, ["a", "b"]);
  assert.equal(rows.length, 0);
});

test("buildTableName strips .csv and adds prefix", () => {
  assert.equal(buildTableName("/path/to/物料.csv", "my_"), "my_物料");
  assert.equal(buildTableName("data.csv", ""), "data");
  assert.equal(buildTableName("/a/b/test.CSV", "pfx_"), "pfx_test");
});

test("splitBatches splits rows correctly", () => {
  const rows = Array.from({ length: 7 }, (_, i) => ({ id: String(i) }));
  const batches = splitBatches(rows, 3);
  assert.equal(batches.length, 3);
  assert.equal(batches[0].length, 3);
  assert.equal(batches[1].length, 3);
  assert.equal(batches[2].length, 1);
});

test("splitBatches returns single batch for small data", () => {
  const rows = [{ a: "1" }];
  const batches = splitBatches(rows, 500);
  assert.equal(batches.length, 1);
});

test("buildFieldMappings creates VARCHAR(512) mappings", () => {
  const mappings = buildFieldMappings(["code", "name"]);
  assert.equal(mappings.length, 2);
  assert.deepEqual(mappings[0], {
    source: { name: "code" },
    target: { name: "code", data_type: "VARCHAR(512)" },
  });
});

test("buildDagBody creates correct DAG structure", () => {
  const dag = buildDagBody({
    datasourceId: "ds-1",
    datasourceType: "mysql",
    tableName: "my_table",
    tableExist: false,
    data: [{ a: "1" }],
    fieldMappings: [{ source: { name: "a" }, target: { name: "a", data_type: "VARCHAR(512)" } }],
  });
  assert.ok(dag.title.includes("import_my_table"));
  assert.equal(dag.trigger_config.operator, "@trigger/manual");
  assert.equal(dag.steps.length, 2);
  assert.equal(dag.steps[0].operator, "@trigger/manual");
  assert.equal(dag.steps[1].operator, "@internal/database/write");
  const params = dag.steps[1].parameters;
  assert.equal(params.datasource_type, "mysql");
  assert.equal(params.datasource_id, "ds-1");
  assert.equal(params.table_name, "my_table");
  assert.equal(params.table_exist, false);
});

test("cleanup", () => {
  rmSync(TMP, { recursive: true, force: true });
});
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd packages/typescript && npx tsx --test test/import-csv.test.ts
```

Expected: FAIL — module not found

- [ ] **Step 3: Commit**

```bash
git add test/import-csv.test.ts
git commit -m "test: add CSV import logic tests (red)"
```

---

### Task 5: CSV import logic — implementation

**Files:**
- Create: `packages/typescript/src/commands/import-csv.ts`

Exported functions for parsing, naming, batching, and DAG construction. Kept separate from `ds.ts` for testability — `ds.ts` will import and call these.

- [ ] **Step 1: Implement import-csv.ts**

```typescript
import { readFile } from "node:fs/promises";
import { basename } from "node:path";
import { parse } from "csv-parse/sync";
import type { DataflowCreateBody } from "../api/dataflow.js";

// ── CSV Parsing ──────────────────────────────────────────────────────────────

export interface CsvData {
  headers: string[];
  rows: Array<Record<string, string | null>>;
}

export async function parseCsvFile(filePath: string): Promise<CsvData> {
  let content = await readFile(filePath, "utf-8");
  // Strip UTF-8 BOM
  if (content.charCodeAt(0) === 0xfeff) {
    content = content.slice(1);
  }

  const records: Array<Record<string, string>> = parse(content, {
    columns: true,
    skip_empty_lines: true,
    trim: true,
  });

  if (records.length === 0) {
    // Parse again just for headers
    const headerOnly: string[][] = parse(content, {
      to: 1,
      skip_empty_lines: true,
      trim: true,
    });
    const headers = headerOnly[0] ?? [];
    return { headers, rows: [] };
  }

  const headers = Object.keys(records[0]);
  const rows = records.map((row) => {
    const cleaned: Record<string, string | null> = {};
    for (const key of headers) {
      const val = row[key];
      cleaned[key] = val === "" || val === undefined ? null : val;
    }
    return cleaned;
  });

  return { headers, rows };
}

// ── Table Name ───────────────────────────────────────────────────────────────

export function buildTableName(filePath: string, prefix: string): string {
  const name = basename(filePath).replace(/\.csv$/i, "");
  return `${prefix}${name}`;
}

// ── Batching ─────────────────────────────────────────────────────────────────

export function splitBatches<T>(rows: T[], batchSize: number): T[][] {
  const batches: T[][] = [];
  for (let i = 0; i < rows.length; i += batchSize) {
    batches.push(rows.slice(i, i + batchSize));
  }
  return batches;
}

// ── Field Mappings ───────────────────────────────────────────────────────────

export interface FieldMapping {
  source: { name: string };
  target: { name: string; data_type: string };
}

export function buildFieldMappings(headers: string[]): FieldMapping[] {
  return headers.map((h) => ({
    source: { name: h },
    target: { name: h, data_type: "VARCHAR(512)" },
  }));
}

// ── DAG Body ─────────────────────────────────────────────────────────────────

export interface DagBodyOptions {
  datasourceId: string;
  datasourceType: string;
  tableName: string;
  tableExist: boolean;
  data: Array<Record<string, string | null>>;
  fieldMappings: FieldMapping[];
}

export function buildDagBody(options: DagBodyOptions): DataflowCreateBody {
  const { datasourceId, datasourceType, tableName, tableExist, data, fieldMappings } = options;
  const tag = Date.now();
  return {
    title: `import_${tableName}_${tag}`,
    description: "CSV import — auto-deleted",
    trigger_config: { operator: "@trigger/manual" },
    steps: [
      {
        id: "trigger",
        title: "trigger",
        operator: "@trigger/manual",
        parameters: {},
      },
      {
        id: "write",
        title: `Write ${tableName}`,
        operator: "@internal/database/write",
        parameters: {
          datasource_type: datasourceType,
          datasource_id: datasourceId,
          table_name: tableName,
          table_exist: tableExist,
          operate_type: "append",
          data,
          sync_model_fields: fieldMappings,
        },
      },
    ],
  };
}
```

- [ ] **Step 2: Run tests to verify they pass**

```bash
cd packages/typescript && npx tsx --test test/import-csv.test.ts
```

Expected: all tests PASS

- [ ] **Step 3: Commit**

```bash
git add src/commands/import-csv.ts
git commit -m "feat: add CSV import logic (parse, batch, DAG construction)"
```

---

### Task 6: `ds import-csv` CLI command

**Files:**
- Modify: `packages/typescript/src/commands/ds.ts`

- [ ] **Step 1: Add import to ds.ts**

At the top of `ds.ts`, after existing imports, add:

```typescript
import { statSync } from "node:fs";
import { glob } from "node:fs/promises";
import { resolve as resolvePath } from "node:path";
import {
  parseCsvFile,
  buildTableName,
  splitBatches,
  buildFieldMappings,
  buildDagBody,
} from "./import-csv.js";
import { executeDataflow } from "../api/dataflow.js";
```

Note: `glob` is from `node:fs/promises` (Node 22+). `statSync` and `resolvePath` are used by `resolveFiles`. `getDatasource` is already imported in `ds.ts` — do NOT re-import it.

- [ ] **Step 2: Add import-csv to dispatch and help text**

In `runDsCommand`, add to the dispatch function (after the `connect` line):

```typescript
if (subcommand === "import-csv") return runDsImportCsvCommand(rest);
```

Update the help string to include:

```
  import-csv <ds-id> --files <glob_or_list> [--table-prefix X] [--batch-size N]
    Import CSV files into datasource tables via dataflow API.
```

- [ ] **Step 3: Add argument parser**

```typescript
function parseImportCsvArgs(args: string[]): {
  datasourceId: string;
  files: string;
  tablePrefix: string;
  batchSize: number;
  businessDomain: string;
} {
  let datasourceId = "";
  let files = "";
  let tablePrefix = "";
  let batchSize = 500;
  let businessDomain = "";

  for (let i = 0; i < args.length; i += 1) {
    const arg = args[i];
    if (arg === "--help" || arg === "-h") throw new Error("help");
    if (arg === "--files" && args[i + 1]) { files = args[++i]; continue; }
    if (arg === "--table-prefix" && args[i + 1]) { tablePrefix = args[++i]; continue; }
    if (arg === "--batch-size" && args[i + 1]) {
      batchSize = parseInt(args[++i], 10);
      if (Number.isNaN(batchSize) || batchSize < 1 || batchSize > 10000) {
        throw new Error("--batch-size must be between 1 and 10000");
      }
      continue;
    }
    if ((arg === "-bd" || arg === "--biz-domain") && args[i + 1]) { businessDomain = args[++i]; continue; }
    if (!arg.startsWith("-") && !datasourceId) { datasourceId = arg; }
  }

  if (!datasourceId || !files) {
    throw new Error("Usage: kweaver ds import-csv <ds-id> --files <glob_or_list> [--table-prefix X] [--batch-size N]");
  }
  if (!businessDomain) businessDomain = resolveBusinessDomain();
  return { datasourceId, files, tablePrefix, batchSize, businessDomain };
}
```

- [ ] **Step 4: Add resolveFiles helper**

```typescript
async function resolveFiles(pattern: string): Promise<string[]> {
  // Comma-separated list or glob
  const parts = pattern.split(",").map((s) => s.trim()).filter(Boolean);
  const result: string[] = [];

  for (const part of parts) {
    if (part.includes("*") || part.includes("?")) {
      // Glob pattern — use Node 22 fs.glob
      for await (const entry of glob(part)) {
        if (entry.endsWith(".csv") || entry.endsWith(".CSV")) {
          result.push(resolvePath(entry));
        }
      }
    } else {
      const abs = resolvePath(part);
      try {
        statSync(abs);
        result.push(abs);
      } catch {
        throw new Error(`File not found: ${part}`);
      }
    }
  }

  if (result.length === 0) {
    throw new Error(`No CSV files matched: ${pattern}`);
  }
  return result;
}
```

- [ ] **Step 5: Add command handler**

```typescript
const IMPORT_CSV_HELP = `kweaver ds import-csv <ds-id> --files <glob_or_list> [options]

Import CSV files into datasource tables via dataflow API.

Options:
  --files <s>          CSV file paths (comma-separated or glob pattern, required)
  --table-prefix <s>   Table name prefix (default: none)
  --batch-size <n>     Rows per batch (default: 500, range: 1-10000)
  -bd, --biz-domain    Business domain (default: bd_public)`;

export interface ImportCsvResult {
  code: number;
  tables: string[];  // successfully imported table names
}

export async function runDsImportCsv(args: string[]): Promise<ImportCsvResult> {
  let options: ReturnType<typeof parseImportCsvArgs>;
  try {
    options = parseImportCsvArgs(args);
  } catch (error) {
    if (error instanceof Error && error.message === "help") {
      console.log(IMPORT_CSV_HELP);
      return 0;
    }
    console.error(error instanceof Error ? error.message : String(error));
    return 1;
  }

  try {
    const token = await ensureValidToken();
    const base = { baseUrl: token.baseUrl, accessToken: token.accessToken, businessDomain: options.businessDomain };

    // Resolve files
    const filePaths = await resolveFiles(options.files);

    // Get datasource type
    const dsBody = await getDatasource({ ...base, id: options.datasourceId });
    const dsParsed = JSON.parse(dsBody) as Record<string, unknown>;
    const datasourceType = String(dsParsed.type ?? dsParsed.ds_type ?? dsParsed.data_type ?? "mysql");

    // Phase 1: Parse and validate ALL CSVs upfront
    const parsed: Array<{ filePath: string; tableName: string; headers: string[]; rows: Array<Record<string, string | null>> }> = [];
    for (const filePath of filePaths) {
      const { headers, rows } = await parseCsvFile(filePath);
      if (headers.length === 0) {
        console.error(`[${filePath}] no headers found, skipping`);
        continue;
      }
      if (rows.length === 0) {
        console.error(`[${filePath}] no data rows, skipping`);
        continue;
      }
      const tableName = buildTableName(filePath, options.tablePrefix);
      parsed.push({ filePath, tableName, headers, rows });
    }

    if (parsed.length === 0) {
      console.error("No valid CSV files to import");
      return { code: 1, tables: [] };
    }

    // Phase 2: Import each file
    const results: Array<{ table: string; rows: number; success: boolean; error?: string }> = [];
    const tTotal = Date.now();

    for (const { tableName, headers, rows } of parsed) {
      const fieldMappings = buildFieldMappings(headers);
      const batches = splitBatches(rows, options.batchSize);
      const tTable = Date.now();
      let tableSuccess = true;

      for (let bIdx = 0; bIdx < batches.length; bIdx++) {
        const batch = batches[bIdx];
        const isFirst = bIdx === 0;
        process.stderr.write(`[${tableName}] batch ${bIdx + 1}/${batches.length} (${batch.length} rows)...`);
        const tBatch = Date.now();

        try {
          const dagBody = buildDagBody({
            datasourceId: options.datasourceId,
            datasourceType,
            tableName,
            tableExist: !isFirst,
            data: batch,
            fieldMappings,
          });
          await executeDataflow({ ...base, body: dagBody });
          console.error(` ${((Date.now() - tBatch) / 1000).toFixed(1)}s`);
        } catch (error) {
          const msg = error instanceof Error ? error.message : String(error);
          console.error(` FAILED: ${msg}`);
          tableSuccess = false;
          results.push({ table: tableName, rows: rows.length, success: false, error: msg });
          break;
        }
      }

      if (tableSuccess) {
        const elapsed = ((Date.now() - tTable) / 1000).toFixed(1);
        console.error(`[${tableName}] done (${rows.length} rows in ${elapsed}s)`);
        results.push({ table: tableName, rows: rows.length, success: true });
      }
    }

    const totalElapsed = ((Date.now() - tTotal) / 1000).toFixed(1);
    const succeeded = results.filter((r) => r.success);
    const failed = results.filter((r) => !r.success);
    const totalRows = succeeded.reduce((sum, r) => sum + r.rows, 0);

    console.error(`\nImport complete: ${succeeded.length} tables, ${totalRows} rows in ${totalElapsed}s`);
    if (failed.length > 0) {
      console.error(`Failed: ${failed.map((r) => r.table).join(", ")}`);
    }

    // Output structured result
    console.log(JSON.stringify({
      tables: results.map((r) => ({ name: r.table, rows: r.rows, success: r.success, error: r.error })),
      summary: { total: results.length, succeeded: succeeded.length, failed: failed.length, total_rows: totalRows },
    }, null, 2));

    const importedTables = succeeded.map((r) => r.table);
    return { code: failed.length > 0 ? 1 : 0, tables: importedTables };
  } catch (error) {
    console.error(formatHttpError(error));
    return { code: 1, tables: [] };
  }
}

// CLI entry point wrapper
export async function runDsImportCsvCommand(args: string[]): Promise<number> {
  const result = await runDsImportCsv(args);
  return result.code;
}
```

- [ ] **Step 6: Run existing tests to verify no regressions**

```bash
cd packages/typescript && npx tsx --test test/dataflow.test.ts test/import-csv.test.ts
```

Expected: all tests PASS

- [ ] **Step 7: Verify CLI help works**

```bash
cd packages/typescript && npx tsx src/cli.ts ds import-csv -h
```

Expected: prints help text

- [ ] **Step 8: Commit**

```bash
git add src/commands/ds.ts src/commands/import-csv.ts
git commit -m "feat: add ds import-csv CLI command"
```

---

### Task 7: `bkn create-from-csv` CLI command

**Files:**
- Modify: `packages/typescript/src/commands/bkn.ts`

- [ ] **Step 1: Add import and dispatch**

At top of `bkn.ts`, add import:

```typescript
import { runDsImportCsv } from "./ds.js";
```

In `runKnCommand` dispatch (around line 833), add:

```typescript
if (subcommand === "create-from-csv") return runKnCreateFromCsvCommand(rest);
```

Update help text to include:

```
  create-from-csv <ds-id> --files <glob> --name X [--table-prefix P] [--build]
```

- [ ] **Step 2: Add argument parser**

```typescript
const KN_CREATE_FROM_CSV_HELP = `kweaver bkn create-from-csv <ds-id> --files <glob> --name X [options]

Import CSV files into datasource, then create a knowledge network.

Options:
  --files <s>          CSV file paths (comma-separated or glob, required)
  --name <s>           Knowledge network name (required)
  --table-prefix <s>   Table name prefix (default: none)
  --batch-size <n>     Rows per batch (default: 500)
  --tables <a,b>       Tables to include in KN (default: all imported)
  --build (default)    Build after creation
  --no-build           Skip build
  --timeout <n>        Build timeout in seconds (default: 300)
  -bd, --biz-domain    Business domain (default: bd_public)`;

function parseKnCreateFromCsvArgs(args: string[]): {
  dsId: string;
  files: string;
  name: string;
  tablePrefix: string;
  batchSize: number;
  tables: string[];
  build: boolean;
  timeout: number;
  businessDomain: string;
} {
  let dsId = "";
  let files = "";
  let name = "";
  let tablePrefix = "";
  let batchSize = 500;
  let tablesStr = "";
  let build = true;
  let timeout = 300;
  let businessDomain = "";

  for (let i = 0; i < args.length; i += 1) {
    const arg = args[i];
    if (arg === "--help" || arg === "-h") throw new Error("help");
    if (arg === "--files" && args[i + 1]) { files = args[++i]; continue; }
    if (arg === "--name" && args[i + 1]) { name = args[++i]; continue; }
    if (arg === "--table-prefix" && args[i + 1]) { tablePrefix = args[++i]; continue; }
    if (arg === "--batch-size" && args[i + 1]) { batchSize = parseInt(args[++i], 10); continue; }
    if (arg === "--tables" && args[i + 1]) { tablesStr = args[++i]; continue; }
    if (arg === "--build") { build = true; continue; }
    if (arg === "--no-build") { build = false; continue; }
    if (arg === "--timeout" && args[i + 1]) {
      timeout = parseInt(args[++i], 10);
      if (Number.isNaN(timeout) || timeout < 1) timeout = 300;
      continue;
    }
    if ((arg === "-bd" || arg === "--biz-domain") && args[i + 1]) { businessDomain = args[++i]; continue; }
    if (!arg.startsWith("-") && !dsId) { dsId = arg; }
  }

  if (!dsId || !files || !name) {
    throw new Error("Usage: kweaver bkn create-from-csv <ds-id> --files <glob> --name X [options]");
  }
  const tables = tablesStr ? tablesStr.split(",").map((s) => s.trim()).filter(Boolean) : [];
  if (!businessDomain) businessDomain = resolveBusinessDomain();
  return { dsId, files, name, tablePrefix, batchSize, tables, build, timeout, businessDomain };
}
```

- [ ] **Step 3: Add command handler**

```typescript
async function runKnCreateFromCsvCommand(args: string[]): Promise<number> {
  let options: ReturnType<typeof parseKnCreateFromCsvArgs>;
  try {
    options = parseKnCreateFromCsvArgs(args);
  } catch (error) {
    if (error instanceof Error && error.message === "help") {
      console.log(KN_CREATE_FROM_CSV_HELP);
      return 0;
    }
    console.error(error instanceof Error ? error.message : String(error));
    return 1;
  }

  // Step 1: Import CSVs
  console.error("Phase 1: Importing CSV files ...");
  const importArgs = [
    options.dsId,
    "--files", options.files,
    ...(options.tablePrefix ? ["--table-prefix", options.tablePrefix] : []),
    "--batch-size", String(options.batchSize),
    "-bd", options.businessDomain,
  ];
  const importResult = await runDsImportCsv(importArgs);
  if (importResult.code !== 0) {
    console.error("CSV import failed, aborting KN creation");
    return importResult.code;
  }

  // Step 2: Create KN from datasource
  // Use user-specified tables, or fall back to the tables just imported
  const tables = options.tables.length > 0 ? options.tables : importResult.tables;
  console.error("\nPhase 2: Creating knowledge network ...");
  const createArgs = [
    options.dsId,
    "--name", options.name,
    ...(tables.length > 0 ? ["--tables", tables.join(",")] : []),
    ...(options.build ? ["--build"] : ["--no-build"]),
    "--timeout", String(options.timeout),
    "-bd", options.businessDomain,
  ];
  return runKnCreateFromDsCommand(createArgs);
}
```

- [ ] **Step 4: Verify CLI help**

```bash
cd packages/typescript && npx tsx src/cli.ts bkn create-from-csv -h
```

Expected: prints help text

- [ ] **Step 5: Commit**

```bash
git add src/commands/bkn.ts
git commit -m "feat: add bkn create-from-csv CLI command"
```

---

### Task 8: Update skill guide

**Files:**
- Modify: `skills/kweaver-core/references/build-kn-from-db.md`
- Modify: `skills/kweaver-core/SKILL.md`

- [ ] **Step 1: Add CSV section to build-kn-from-db.md**

After the "分步路径" section, add:

```markdown
## 从 CSV 文件构建

当数据在本地 CSV 文件中，需要一个 KWeaver 可访问的数据源作为中间存储。

### 快速路径（一条命令）

\`\`\`bash
# datasource_id 来自已有数据源（kweaver ds list）或现场连接
kweaver bkn create-from-csv <datasource_id> --files "*.csv" --name "my-kn"

# 指定表前缀和部分表
kweaver bkn create-from-csv <ds_id> --files "物料.csv,库存.csv" \
  --name "supply-kn" --table-prefix sc_
\`\`\`

### 分步路径

\`\`\`bash
# 1. 导入 CSV 到数据源
kweaver ds import-csv <datasource_id> --files "*.csv" --table-prefix my_

# 2. 从数据源创建 KN
kweaver bkn create-from-ds <datasource_id> --name "my-kn" --build
\`\`\`

### import-csv 参数

| 参数 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `datasource_id` | 是 | — | KWeaver 可访问的数据源 ID |
| `--files` | 是 | — | CSV 文件路径，逗号分隔或 glob |
| `--table-prefix` | 否 | `""` | 表名前缀 |
| `--batch-size` | 否 | 500 | 每批写入行数（1-10000） |
```

- [ ] **Step 2: Update SKILL.md ds command row**

In the 命令组总览 table, update the `ds` row:

```markdown
| `ds` | 数据源管理 | `ds list`, `ds get <id>`, `ds import-csv <id> --files ...` | `references/ds.md` |
```

- [ ] **Step 3: Update SKILL.md 操作指南 table**

Update the guide description:

```markdown
| 从数据库/CSV 构建 KN | 连接数据源 → CSV 导入 → 创建 KN → 构建索引 → 查询验证 → 绑定 Agent | [references/build-kn-from-db.md](references/build-kn-from-db.md) |
```

- [ ] **Step 4: Update references/ds.md**

Add `import-csv` to the commands list and example section.

- [ ] **Step 5: Commit**

```bash
git add skills/kweaver-core/references/build-kn-from-db.md skills/kweaver-core/SKILL.md skills/kweaver-core/references/ds.md
git commit -m "docs: update skill guide with CSV import workflow"
```

---

### Task 9: Run all tests and final verification

**Files:** none (verification only)

- [ ] **Step 1: Run all unit tests**

```bash
cd packages/typescript && npx tsx --test test/dataflow.test.ts test/import-csv.test.ts test/cli.test.ts test/client.test.ts
```

Expected: all PASS

- [ ] **Step 2: Verify CLI commands register correctly**

```bash
cd packages/typescript && npx tsx src/cli.ts ds -h
npx tsx src/cli.ts ds import-csv -h
npx tsx src/cli.ts bkn create-from-csv -h
```

Expected: all print help text with correct usage

- [ ] **Step 3: Verify build compiles**

```bash
cd packages/typescript && npx tsc --noEmit
```

Expected: no type errors

- [ ] **Step 4: Final commit if any fixes needed**

```bash
git add -A && git commit -m "fix: address test/build issues"
```
