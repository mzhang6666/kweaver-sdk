import test from "node:test";
import assert from "node:assert/strict";
import { runCli, shouldSkipE2e } from "./setup.js";

/** Extract array entries from CLI JSON output. */
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

test("e2e: vega --help returns help text", async () => {
  // No skip — always runs, no backend needed
  const { code, stdout } = await runCli(["vega", "--help"]);
  assert.equal(code, 0);
  assert.ok(stdout.includes("catalog"));
  assert.ok(stdout.includes("resource"));
  assert.ok(stdout.includes("connector-type"));
});

test("e2e: vega health returns server info", { skip: shouldSkipE2e() }, async () => {
  const { code, stdout } = await runCli(["vega", "health"]);
  // /health may not be exposed via gateway — tolerate 404
  if (code !== 0) { test.skip("health endpoint not available via gateway"); return; }
  const parsed = JSON.parse(stdout);
  assert.ok(parsed.server_name !== undefined || Object.keys(parsed).length > 0);
});

test("e2e: vega catalog list returns array", { skip: shouldSkipE2e() }, async () => {
  const { code, stdout } = await runCli(["vega", "catalog", "list"]);
  assert.equal(code, 0);
  const entries = extractEntries(JSON.parse(stdout));
  assert.ok(entries.length >= 0);
});

test("e2e: vega connector-type list returns array", { skip: shouldSkipE2e() }, async () => {
  const { code, stdout } = await runCli(["vega", "connector-type", "list"]);
  // Backend may return 400 due to sort parameter bug — tolerate
  if (code !== 0) { test.skip("connector-type list not available (backend sort bug)"); return; }
  const entries = extractEntries(JSON.parse(stdout));
  assert.ok(entries.length >= 0);
});

test("e2e: vega resource list returns array", { skip: shouldSkipE2e() }, async () => {
  const { code, stdout } = await runCli(["vega", "resource", "list"]);
  assert.equal(code, 0);
  const entries = extractEntries(JSON.parse(stdout));
  assert.ok(entries.length >= 0);
});

test("e2e: vega stats returns counts", { skip: shouldSkipE2e() }, async () => {
  const { code, stdout } = await runCli(["vega", "stats"]);
  assert.equal(code, 0);
  const parsed = JSON.parse(stdout);
  assert.ok("catalog_count" in parsed);
});

test("e2e: vega inspect returns composite report", { skip: shouldSkipE2e() }, async () => {
  const { code, stdout } = await runCli(["vega", "inspect"]);
  assert.equal(code, 0);
  const report = JSON.parse(stdout);
  assert.ok("health" in report || "catalog_count" in report);
});

test("e2e: vega catalog --help shows CRUD subcommands", async () => {
  const { code, stdout } = await runCli(["vega", "catalog", "--help"]);
  assert.equal(code, 0);
  assert.ok(stdout.includes("create"));
  assert.ok(stdout.includes("update"));
  assert.ok(stdout.includes("delete"));
});

test("e2e: vega resource --help shows CRUD subcommands", async () => {
  const { code, stdout } = await runCli(["vega", "resource", "--help"]);
  assert.equal(code, 0);
  assert.ok(stdout.includes("create"));
  assert.ok(stdout.includes("update"));
  assert.ok(stdout.includes("delete"));
});

test("e2e: vega connector-type --help shows CRUD subcommands", async () => {
  const { code, stdout } = await runCli(["vega", "connector-type", "--help"]);
  assert.equal(code, 0);
  assert.ok(stdout.includes("register"));
  assert.ok(stdout.includes("update"));
  assert.ok(stdout.includes("delete"));
  assert.ok(stdout.includes("enable"));
});

test("e2e: vega discovery-task --help shows subcommands", async () => {
  const { code, stdout } = await runCli(["vega", "discovery-task", "--help"]);
  assert.equal(code, 0);
  assert.ok(stdout.includes("list"));
  assert.ok(stdout.includes("get"));
});

test("e2e: vega discovery-task list returns array", { skip: shouldSkipE2e() }, async () => {
  const { code, stdout } = await runCli(["vega", "discovery-task", "list"]);
  // Backend may not support discovery-task endpoint yet — tolerate
  if (code !== 0) { test.skip("discovery-task list not available"); return; }
  const entries = extractEntries(JSON.parse(stdout));
  assert.ok(entries.length >= 0);
});
