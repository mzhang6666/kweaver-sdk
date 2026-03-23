/**
 * Normalize .bkn file bytes to UTF-8 for BKN import (validate / push).
 * Used when --detect-encoding (default) or --source-encoding is active.
 */

import {
  copyFileSync,
  mkdirSync,
  mkdtempSync,
  readdirSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { join, relative, resolve } from "node:path";
import chardet from "chardet";
import iconv from "iconv-lite";

/** Minimum confidence (0–1) for charset detection before failing. */
export const BKN_DETECT_MIN_CONFIDENCE = 0.65;

export interface BknEncodingImportOptions {
  /** When true (default), detect encoding for non-UTF-8 .bkn files. */
  detectEncoding: boolean;
  /** When set, decode all .bkn files with this encoding (overrides detection). */
  sourceEncoding: string | null;
}

/**
 * Parse --no-detect-encoding, --detect-encoding, --source-encoding <name> from argv.
 * Remaining args are returned for positional parsing (directory, etc.).
 */
export function stripBknEncodingCliArgs(args: string[]): {
  rest: string[];
  options: BknEncodingImportOptions;
} {
  let detectEncoding = true;
  let sourceEncoding: string | null = null;
  const rest: string[] = [];

  for (let i = 0; i < args.length; i += 1) {
    const arg = args[i];
    if (arg === "--no-detect-encoding") {
      detectEncoding = false;
      continue;
    }
    if (arg === "--detect-encoding") {
      detectEncoding = true;
      continue;
    }
    if (arg === "--source-encoding") {
      const v = args[i + 1];
      if (!v || v.startsWith("-")) {
        throw new Error("Missing value for --source-encoding (e.g. gb18030)");
      }
      sourceEncoding = v;
      i += 1;
      continue;
    }
    rest.push(arg);
  }

  return {
    rest,
    options: { detectEncoding, sourceEncoding },
  };
}

function isValidUtf8(buf: Buffer): boolean {
  try {
    new TextDecoder("utf-8", { fatal: true }).decode(buf);
    return true;
  } catch {
    return false;
  }
}

function stripUtf8Bom(buf: Buffer): Buffer {
  if (buf.length >= 3 && buf[0] === 0xef && buf[1] === 0xbb && buf[2] === 0xbf) {
    return buf.subarray(3);
  }
  return buf;
}

/**
 * Decode raw .bkn bytes to a UTF-8 Buffer (no BOM).
 */
export function normalizeBknFileBytes(raw: Buffer, options: BknEncodingImportOptions, fileLabel: string): Buffer {
  if (options.sourceEncoding) {
    const enc = options.sourceEncoding.trim().toLowerCase();
    if (enc === "utf-8" || enc === "utf8") {
      const body = stripUtf8Bom(raw);
      if (!isValidUtf8(body)) {
        throw new Error(`Invalid UTF-8 in ${fileLabel} despite --source-encoding utf-8`);
      }
      return Buffer.from(body.toString("utf8"), "utf8");
    }
    if (!iconv.encodingExists(enc)) {
      throw new Error(`Unsupported --source-encoding: ${options.sourceEncoding}`);
    }
    const text = iconv.decode(raw, enc);
    return Buffer.from(text, "utf8");
  }

  if (!options.detectEncoding) {
    const body = stripUtf8Bom(raw);
    if (!isValidUtf8(body)) {
      throw new Error(
        `Invalid UTF-8 in ${fileLabel}. Use --detect-encoding (default) or --source-encoding (e.g. gb18030).`,
      );
    }
    return Buffer.from(body.toString("utf8"), "utf8");
  }

  let work = stripUtf8Bom(raw);
  if (isValidUtf8(work)) {
    return Buffer.from(work.toString("utf8"), "utf8");
  }

  const matches = chardet.analyse(work);
  const best = matches[0];
  if (!best || best.confidence < BKN_DETECT_MIN_CONFIDENCE) {
    throw new Error(
      `Could not detect encoding confidently for ${fileLabel} (best confidence ${best?.confidence ?? 0}). ` +
        `Try --source-encoding gb18030 or save files as UTF-8.`,
    );
  }
  const name = best.name ?? "utf-8";
  if (!iconv.encodingExists(name)) {
    throw new Error(`Detected encoding "${name}" is not supported for ${fileLabel}. Try --source-encoding.`);
  }
  const text = iconv.decode(work, name);
  return Buffer.from(text, "utf8");
}

/**
 * When normalization is needed, copy the tree to a temp dir with .bkn files normalized to UTF-8.
 * Returns the directory to pass to loadNetwork and a cleanup function.
 */
export function prepareBknDirectoryForImport(
  absDir: string,
  options: BknEncodingImportOptions,
): { dir: string; cleanup: () => void } {
  const needWork =
    options.sourceEncoding != null || options.detectEncoding;

  if (!needWork) {
    return { dir: absDir, cleanup: () => {} };
  }

  const root = resolve(absDir);
  const tmpRoot = mkdtempSync(join(tmpdir(), "kweaver-bkn-"));

  function walk(srcDir: string, destDir: string): void {
    mkdirSync(destDir, { recursive: true });
    const entries = readdirSync(srcDir, { withFileTypes: true });
    for (const entry of entries) {
      if (entry.name === "." || entry.name === "..") continue;
      const srcPath = join(srcDir, entry.name);
      const destPath = join(destDir, entry.name);

      if (entry.isDirectory()) {
        walk(srcPath, destPath);
        continue;
      }
      if (!entry.isFile()) continue;

      if (entry.name.endsWith(".bkn")) {
        const raw = readFileSync(srcPath);
        const rel = relative(root, srcPath) || entry.name;
        const out = normalizeBknFileBytes(raw, options, rel);
        writeFileSync(destPath, out);
      } else {
        copyFileSync(srcPath, destPath);
      }
    }
  }

  walk(root, tmpRoot);

  return {
    dir: tmpRoot,
    cleanup: () => {
      try {
        rmSync(tmpRoot, { recursive: true, force: true });
      } catch {
        /* ignore */
      }
    },
  };
}
