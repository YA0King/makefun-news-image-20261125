// main.ts -- entry-image checks for the one-page newspaper entry.
//
// Usage:
//   npx tsx main.ts [repo-dir] [expected-sha256]
//   node --experimental-strip-types main.ts [repo-dir] [expected-sha256]
//
// Checks, in order:
//   1. entry.png exists in the repository (missing file is a hard error).
//   2. The file is a PNG of exactly 1024 x 1024.
//   3. Its SHA-256 matches the expected hash when one is supplied.
// Exit code 0 means every check passed; anything else prints the
// failing check to stderr and exits non-zero.

import { createHash } from "node:crypto";
import { existsSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";

export const ENTRY_FILE = "entry.png";
export const EXPECTED_WIDTH = 1024;
export const EXPECTED_HEIGHT = 1024;

/**
 * Preflight: fail fast with a precise message when the entry image is
 * absent, before any byte of it is read. This runs ahead of the size and
 * hash checks so a missing file can never be mistaken for a bad render.
 */
export function preflightEntry(repoDir: string): string {
  let dirStat;
  try {
    dirStat = statSync(repoDir);
  } catch {
    throw new Error(`repository directory not found: ${repoDir}`);
  }
  if (!dirStat.isDirectory()) {
    throw new Error(`repository path is not a directory: ${repoDir}`);
  }
  const path = join(repoDir, ENTRY_FILE);
  if (!existsSync(path)) {
    throw new Error("entry image missing from repository");
  }
  const fileStat = statSync(path);
  if (!fileStat.isFile()) {
    throw new Error(`entry image is not a regular file: ${path}`);
  }
  if (fileStat.size === 0) {
    throw new Error(`entry image is empty: ${path}`);
  }
  return path;
}

export interface EntryReport {
  path: string;
  width: number;
  height: number;
  sha256: string;
}

export function sha256Hex(data: Buffer): string {
  return createHash("sha256").update(data).digest("hex");
}

const PNG_SIGNATURE = Buffer.from([
  0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a,
]);

export function readPngSize(data: Buffer): { width: number; height: number } {
  // A PNG header needs at least 24 bytes: 8-byte signature + 4-byte
  // IHDR length + 4-byte chunk type + 8 bytes of width/height. Anything
  // shorter cannot carry dimensions, so reject it before reading.
  if (data.length < 24) {
    throw new Error(
      `entry image too short to be a PNG: ${data.length} bytes (need >= 24)`,
    );
  }
  if (!data.subarray(0, 8).equals(PNG_SIGNATURE)) {
    throw new Error("entry image is not a PNG file (bad signature)");
  }
  // The first chunk after the signature must be IHDR; if some other
  // chunk sits there, offsets 16..23 are not width/height at all.
  if (data.toString("ascii", 12, 16) !== "IHDR") {
    throw new Error(
      `entry image first chunk is not IHDR: ` +
        JSON.stringify(data.toString("ascii", 12, 16)),
    );
  }
  // PNG: 8-byte signature, then the IHDR chunk. Width lives at bytes
  // 16..19 and height at bytes 20..23, both big-endian uint32.
  const width = data.readUInt32BE(16);
  const height = data.readUInt32BE(20);
  return { width, height };
}

export function checkEntry(repoDir: string, expectedSha256?: string): EntryReport {
  const path = preflightEntry(repoDir);
  const data = readFileSync(path);
  const { width, height } = readPngSize(data);
  if (width !== EXPECTED_WIDTH || height !== EXPECTED_HEIGHT) {
    throw new Error(
      `entry image must be ${EXPECTED_WIDTH}x${EXPECTED_HEIGHT}, ` +
        `got ${width}x${height}`,
    );
  }
  const sha256 = sha256Hex(data);
  if (expectedSha256 && sha256 !== expectedSha256.toLowerCase()) {
    throw new Error(
      `entry image SHA-256 mismatch: expected ${expectedSha256}, got ${sha256}`,
    );
  }
  return { path, width, height, sha256 };
}

function main(): number {
  const repoDir = process.argv[2] ?? process.cwd();
  const expected = process.argv[3];
  try {
    const report = checkEntry(repoDir, expected);
    console.log(
      `OK ${report.path} ${report.width}x${report.height} ` +
        `sha256=${report.sha256}`,
    );
    return 0;
  } catch (err) {
    console.error(`FAIL ${(err as Error).message}`);
    return 1;
  }
}

if (import.meta.url === `file://${process.argv[1]}`) {
  process.exit(main());
}
