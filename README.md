# The World on One Page — 25 November 2026 (v5)

One-page newspaper infographic: 37 stories from Wednesday 25 November
2026, drawn as a broadsheet front page (1024 × 1024 PNG).

v5 is a fact-and-style revision of v4: every story was re-verified against
its source on 26 Nov 2026 (see `../REVERIFICATION_v5.md`). Two v4 items
carried wrong numbers and were fixed (October PCE: 0.3% m/m, 3.8% y/y,
core 3.3%; Q3 GDP: spending +4.2%, exports −5.3%), the Cartagena item was
trimmed to what its cited wire actually says, and the Australia item was
reframed from Tuesday's criticism to Wednesday's passage of the Act.
Nothing was deleted; the count stays 37.

## Files

| File | What it is |
|---|---|
| `render.py` | The renderer. Python + Pillow, written from scratch. Reads a stories JSON file and a Natural Earth land GeoJSON, writes `entry.png`. |
| `entry.png` | The rendered page (1024 × 1024). |
| `main.ts` | Entry-image checks: missing-file preflight, PNG signature + IHDR validation, exact 1024 × 1024 size check, SHA-256 verification. |
| `stories.json` | Story data for this edition (main 3 + medium 13 + also 21 = 37 stories). |

## Render

```sh
python3 render.py [--input stories.json] [--geo land-110m.geojson] [--output entry.png]
```

No timestamps are embedded, so two runs on the same input produce
identical bytes. Verified: two consecutive runs give
SHA-256 `fe247fbccd8219c6a0edf23f69073d368be3137ecb2a55cda7317a8cea2839c3`.

## Check the entry

```sh
node --experimental-strip-types main.ts [repo-dir] [expected-sha256]
```

Exit 0 means all checks passed.

## What the page contains

- Masthead with the date in big serif and per-region counts, computed
  from the data (not hard-coded).
- Italic ticker with hand-drawn red-diamond separators.
- Six number strips, taken from the stories data.
- Three main stories, each with a flat vector scene, a coloured region
  kicker and a status chip (`OFFICIAL` = government data or an official
  statement, `CLAIM` = one party's claim, not independently confirmed,
  `REPORTED` = outlet reporting; the chip says nothing about the date —
  that is the DATE CHECK's job).
- `MORE OF THE DAY`: a 13-story grid with vector icons, plus
  `WHY IT MATTERS`: one line per main story, in the story's own words.
- A real vector world map from Natural Earth 110m data, with numbered
  pins for every story that carries coordinates, and a legend.
- `ALSO ON …` one-line index in three columns (21 stories, 6 fields).
- A UTC timeline (only time points that survived fact-checking are
  plotted) and `WIRES READ UP TO … UTC`.
- Footer: DATE CHECK (with named exclusions and borderline rulings),
  a NOT YET line for scheduled items that had not happened by the wires
  cut (Iowa detonation, Hera images), LEFT OUT, and the
  `OFFICIAL / CLAIM / REPORTED` legend.

The page's own wording contains no "DRAWN BY …" line and no other
self-referential credit line.

## Data note

The image in this directory was rendered from `stories.json`
(main 3 + medium 13 + also 21 = 37 stories).

Two things the renderer handles deliberately:

1. Timeline: only real `HH:MM` stamps are plotted. Most stories carry
   `time_utc: "n/a"` and those are skipped; the two disproved v3 times
   (03:00, 05:56) stay excluded via `BAD_TIMES`.
2. Map pins: placeless items carry lat 0, lon 0, which is a null-island
   sentinel, not a location in the Gulf of Guinea — they get no pin and
   no legend entry. The 16 pinned main+medium stories are listed in the
   legend in two columns as number + place.

Icon matching is word-boundary based, so "supermarket" is not read as
a market chart, "Metropolitan" is not read as the Metro, "searched"
is not read as the sea, and the Tai Po anniversary feature gets a
neutral document picture instead of an explosion pictogram.

## License

MIT — see `LICENSE`.
