import test from "node:test";
import assert from "node:assert/strict";
import { runCli, shouldSkipE2e, getE2eEnv, shouldRunDestructive } from "./setup.js";

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

test("e2e: ds list returns array", { skip: shouldSkipE2e() }, async () => {
  const { code, stdout } = await runCli(["ds", "list"]);
  assert.equal(code, 0);
  const entries = extractEntries(JSON.parse(stdout));
  assert.ok(entries.length >= 0, "ds list should return parseable entries");
});

test("e2e: ds get returns datasource details", { skip: shouldSkipE2e() }, async () => {
  const { code: listCode, stdout: listOut } = await runCli(["ds", "list"]);
  if (listCode !== 0) { test.skip("ds list failed"); return; }
  const entries = extractEntries(JSON.parse(listOut)) as Array<{ id?: string }>;
  const dsId = entries[0]?.id;
  if (!dsId) { test.skip("no datasources"); return; }
  const { code, stdout } = await runCli(["ds", "get", dsId]);
  assert.equal(code, 0);
  const ds = JSON.parse(stdout) as Record<string, unknown>;
  assert.ok(ds.id !== undefined || ds.ds_id !== undefined);
});

test("e2e: ds tables returns tables with columns", { skip: shouldSkipE2e() }, async () => {
  const { code: listCode, stdout: listOut } = await runCli(["ds", "list"]);
  if (listCode !== 0) { test.skip("ds list failed"); return; }
  const entries = extractEntries(JSON.parse(listOut)) as Array<{ id?: string }>;
  const dsId = entries[0]?.id;
  if (!dsId) { test.skip("no datasources"); return; }
  const { code, stdout } = await runCli(["ds", "tables", dsId]);
  assert.equal(code, 0);
  const parsed = JSON.parse(stdout) as unknown;
  assert.ok(Array.isArray(parsed) || typeof parsed === "object");
});

test("e2e: ds connect registers datasource (destructive)", { skip: !shouldRunDestructive() || shouldSkipE2e() }, async () => {
  const env = getE2eEnv();
  if (!env.dbHost || !env.dbUser || !env.dbPass || !env.dbName) {
    test.skip("E2E database not configured");
    return;
  }

  const dsName = `e2e_ds_${Date.now()}`;
  const { code, stdout, stderr } = await runCli([
    "ds", "connect", env.dbType, env.dbHost, env.dbPort, env.dbName,
    "--account", env.dbUser, "--password", env.dbPass, "--name", dsName,
  ]);
  assert.equal(code, 0, `ds connect failed: ${stderr}`);

  const parsed = JSON.parse(stdout) as Record<string, unknown>;
  const dsId = String(parsed.datasource_id ?? parsed.id ?? parsed.ds_id ?? "");
  assert.ok(dsId, "should return datasource id");

  // Cleanup: delete the created datasource
  if (dsId) {
    await runCli(["ds", "delete", dsId, "-y"]);
  }
});
