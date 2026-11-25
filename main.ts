// news-image-20261125 entry, third version (Node 22, standard library only).
//
// The entry is a program that writes one image summing up the world
// news of Wednesday 25 November 2026 to /output/entry.png.
//
// The image itself is held in this repository as entry.png. It was
// produced by render.py (Python + Pillow, no network, no clock, no
// randomness) from stories.json — 35 news stories, every one verified
// as having happened or first been reported on 25 November 2026, each
// with its source — plus a Natural Earth world outline
// (land-110m.geojson, public domain). This is the v3 rendering: the
// v2 broadsheet pushed further — a full UTC timeline built from five
// verified event times (Shenzhou-24 00:18, KOSPI 02:20, Hodeidah
// 02:22, Trump on Iran 03:00, Nigeria Senate 05:56), 8 medium
// stories each with a drawn mini scene plus a "THE DAY IN EIGHT"
// strip of 8 small scenes, taller hero scenes (92px) and a taller
// map (96px), and a DATE CHECK footer that now lists 9 excluded
// other-day stories (three date errors in v2 were fixed: the
// Ecuador pause, the EU car-sales release and the Mackenzie
// 200-year term were not 25 November news). Re-running render.py
// writes byte-identical output, and this program copies those same
// bytes to the output directory, so the run is deterministic.
//
// Run it the way the grader does:
//   mkdir -p out && MAKEFUN_BOT_DIR=. MAKEFUN_OUTPUT_DIR=out node main.ts

import { copyFileSync, existsSync, mkdirSync, readFileSync, statSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const outDir = process.env.MAKEFUN_OUTPUT_DIR ?? "/output";
mkdirSync(outDir, { recursive: true });

const here = dirname(fileURLToPath(import.meta.url));
const source = join(here, "entry.png");
// Fail fast with a clear message if the entry image is missing from
// the repository, instead of a bare ENOENT from the copy below.
if (!existsSync(source)) {
  throw new Error(`entry image missing from repository: ${source}`);
}
const dest = join(outDir, "entry.png");
copyFileSync(source, dest);

// Verify the written entry: it must exist, be non-empty, and start
// with a PNG or JPEG magic header (the competition judges the file
// by its header).
if (!existsSync(dest)) {
  throw new Error(`entry image missing after copy: ${dest}`);
}
const size = statSync(dest).size;
if (size === 0) {
  throw new Error(`entry image is empty: ${dest}`);
}
const head = readFileSync(dest).subarray(0, 8);
const isPng =
  head[0] === 0x89 && head[1] === 0x50 && head[2] === 0x4e && head[3] === 0x47 &&
  head[4] === 0x0d && head[5] === 0x0a && head[6] === 0x1a && head[7] === 0x0a;
const isJpeg = head[0] === 0xff && head[1] === 0xd8 && head[2] === 0xff;
if (!isPng && !isJpeg) {
  throw new Error(`entry image is neither PNG nor JPEG (bad magic header): ${dest}`);
}

// Integrity: the copied file must be byte-identical to the source
// entry.png in this repository. Compare SHA-256 digests. The crypto
// module is loaded here (top-level await, ESM) so this verification
// stays one self-contained step next to the checks above.
const { createHash } = await import("node:crypto");
const digest = (path) =>
  createHash("sha256").update(readFileSync(path)).digest("hex");
const sourceHash = digest(join(here, "entry.png"));
const destHash = digest(dest);
if (sourceHash !== destHash) {
  throw new Error(
    `entry image hash mismatch after copy: ${dest} is ${destHash}, expected ${sourceHash}`,
  );
}
console.log(`SHA-256 verified: ${destHash}`);

// Enforce the competition's own limits locally: at most 1 MiB and
// 1024 by 1024 pixels. For a PNG the dimensions come from the IHDR
// chunk (width at bytes 16-19, height at bytes 20-23, big-endian).
const MAX_BYTES = 1024 * 1024;
if (size > MAX_BYTES) {
  throw new Error(`entry image is ${size} bytes, over the 1 MiB limit: ${dest}`);
}
if (isPng) {
  const buf = readFileSync(dest);
  // The first chunk of a PNG must be IHDR (bytes 12-15); a file with
  // a valid magic but a corrupt or truncated header would otherwise
  // hand us garbage dimensions.
  if (buf.length < 24 || buf.subarray(12, 16).toString("ascii") !== "IHDR") {
    throw new Error(`entry image is not a well-formed PNG (first chunk is not IHDR): ${dest}`);
  }
  const width = buf.readUInt32BE(16);
  const height = buf.readUInt32BE(20);
  if (width > 1024 || height > 1024) {
    throw new Error(`entry image is ${width}x${height}, over the 1024x1024 limit: ${dest}`);
  }
  // The entry is a single fixed-canvas broadsheet: it must be exactly
  // 1024x1024, not merely within the limit above.
  if (width !== 1024 || height !== 1024) {
    throw new Error(`entry image is ${width}x${height}, expected exactly 1024x1024: ${dest}`);
  }
  console.log(`Wrote ${dest} (${size} bytes, PNG, ${width}x${height})`);
} else {
  console.log(`Wrote ${dest} (${size} bytes, JPEG)`);
}
