import test from "node:test";
import assert from "node:assert/strict";
import { runCli, shouldSkipE2e } from "./setup.js";

/** Extract array entries from CLI JSON output. */
function extractEntries(raw: unknown): unknown[] {
  if (Array.isArray(raw)) return raw;
  if (raw && typeof raw === "object") {
    const obj = raw as Record<string, unknown>;
    for (const key of ["entries", "data", "datas", "records"]) {
      if (Array.isArray(obj[key])) return obj[key] as unknown[];
    }
  }
  return [];
}

/** Find a KN that has object types. */
async function findKnWithOTs(): Promise<string | null> {
  const { code, stdout } = await runCli(["bkn", "list", "--limit", "20"]);
  if (code !== 0) return null;
  const kns = extractEntries(JSON.parse(stdout)) as Array<{ id?: string }>;
  for (const kn of kns) {
    if (!kn.id) continue;
    const { code: otCode, stdout: otOut } = await runCli(["bkn", "object-type", "list", kn.id]);
    if (otCode !== 0) continue;
    const ots = extractEntries(JSON.parse(otOut));
    if (ots.length > 0) return kn.id;
  }
  return null;
}

test("e2e: object-type list returns array", { skip: shouldSkipE2e() }, async () => {
  const knId = await findKnWithOTs();
  if (!knId) { test.skip("no KN with object types"); return; }
  const { code, stdout } = await runCli(["bkn", "object-type", "list", knId]);
  assert.equal(code, 0);
  const entries = extractEntries(JSON.parse(stdout));
  assert.ok(entries.length > 0, "should have at least 1 object type");
});

test("e2e: object-type get returns single OT", { skip: shouldSkipE2e() }, async () => {
  const knId = await findKnWithOTs();
  if (!knId) { test.skip("no KN with object types"); return; }
  const { code: listCode, stdout: listOut } = await runCli(["bkn", "object-type", "list", knId]);
  if (listCode !== 0) { test.skip("object-type list failed"); return; }
  const entries = extractEntries(JSON.parse(listOut)) as Array<{ id?: string }>;
  const otId = entries[0]?.id;
  if (!otId) { test.skip("no object types"); return; }
  const { code, stdout } = await runCli(["bkn", "object-type", "get", knId, otId]);
  assert.equal(code, 0);
  const raw = JSON.parse(stdout) as Record<string, unknown>;
  const ot = Array.isArray(raw.entries) ? (raw.entries[0] as Record<string, unknown>) : raw;
  assert.ok(ot.id !== undefined || ot.name !== undefined);
});

test("e2e: relation-type list returns array", { skip: shouldSkipE2e() }, async () => {
  const knId = await findKnWithOTs();
  if (!knId) { test.skip("no KN available"); return; }
  const { code, stdout } = await runCli(["bkn", "relation-type", "list", knId]);
  assert.equal(code, 0);
  const parsed = JSON.parse(stdout) as unknown;
  assert.ok(Array.isArray(parsed) || typeof parsed === "object");
});

test("e2e: relation-type get returns single RT", { skip: shouldSkipE2e() }, async () => {
  const knId = await findKnWithOTs();
  if (!knId) { test.skip("no KN available"); return; }
  const { code: listCode, stdout: listOut } = await runCli(["bkn", "relation-type", "list", knId]);
  if (listCode !== 0) { test.skip("relation-type list failed"); return; }
  const entries = extractEntries(JSON.parse(listOut)) as Array<{ id?: string }>;
  const rtId = entries[0]?.id;
  if (!rtId) { test.skip("no relation types"); return; }
  const { code, stdout } = await runCli(["bkn", "relation-type", "get", knId, rtId]);
  assert.equal(code, 0);
  const raw = JSON.parse(stdout) as Record<string, unknown>;
  const rt = Array.isArray(raw.entries) ? (raw.entries[0] as Record<string, unknown>) : raw;
  assert.ok(rt.id !== undefined || rt.name !== undefined);
});
