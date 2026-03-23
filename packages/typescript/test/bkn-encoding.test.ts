import test from "node:test";
import assert from "node:assert/strict";
import iconv from "iconv-lite";
import {
  normalizeBknFileBytes,
  prepareBknDirectoryForImport,
  stripBknEncodingCliArgs,
} from "../src/utils/bkn-encoding.js";

const utf8Sample = Buffer.from("---\ntype: network\nid: x\nname: 测试\n---\n# 标题\n", "utf8");

test("stripBknEncodingCliArgs: defaults detect on, no source", () => {
  const { rest, options } = stripBknEncodingCliArgs(["mydir"]);
  assert.deepEqual(rest, ["mydir"]);
  assert.equal(options.detectEncoding, true);
  assert.equal(options.sourceEncoding, null);
});

test("stripBknEncodingCliArgs: --no-detect-encoding", () => {
  const { options } = stripBknEncodingCliArgs(["--no-detect-encoding", "d"]);
  assert.equal(options.detectEncoding, false);
});

test("stripBknEncodingCliArgs: --source-encoding gb18030", () => {
  const { options } = stripBknEncodingCliArgs(["--source-encoding", "gb18030", "d"]);
  assert.equal(options.sourceEncoding, "gb18030");
});

test("normalizeBknFileBytes: UTF-8 passthrough when detect on", () => {
  const out = normalizeBknFileBytes(utf8Sample, { detectEncoding: true, sourceEncoding: null }, "x.bkn");
  assert.equal(out.toString("utf8"), utf8Sample.toString("utf8"));
});

test("normalizeBknFileBytes: UTF-8 BOM stripped then valid", () => {
  const bom = Buffer.concat([Buffer.from([0xef, 0xbb, 0xbf]), utf8Sample]);
  const out = normalizeBknFileBytes(bom, { detectEncoding: true, sourceEncoding: null }, "x.bkn");
  assert.equal(out.toString("utf8"), utf8Sample.toString("utf8"));
});

test("normalizeBknFileBytes: GB18030 bytes with --source-encoding", () => {
  const gbkBytes = iconv.encode(utf8Sample.toString("utf8"), "gb18030");
  const out = normalizeBknFileBytes(gbkBytes, { detectEncoding: false, sourceEncoding: "gb18030" }, "x.bkn");
  assert.equal(out.toString("utf8"), utf8Sample.toString("utf8"));
});

test("normalizeBknFileBytes: invalid UTF-8 with --no-detect-encoding throws", () => {
  const bad = Buffer.from([0xff, 0xfe, 0xfd]);
  assert.throws(
    () => normalizeBknFileBytes(bad, { detectEncoding: false, sourceEncoding: null }, "x.bkn"),
    /Invalid UTF-8/,
  );
});

test("prepareBknDirectoryForImport: no work when no-detect and no source", () => {
  const { dir, cleanup } = prepareBknDirectoryForImport("/tmp", {
    detectEncoding: false,
    sourceEncoding: null,
  });
  assert.equal(dir, "/tmp");
  cleanup();
});
