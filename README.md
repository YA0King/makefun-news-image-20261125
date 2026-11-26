[![make.fun · news-image-20261125](https://make.fun/badge/news-image-20261125.svg)](https://make.fun/bounty/news-image-20261125?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261125)
[![rank](https://make.fun/badge/news-image-20261125/YA0King/makefun-news-image-20261125/rank.svg)](https://make.fun/bounty/news-image-20261125/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261125)
[![reward](https://make.fun/badge/news-image-20261125/YA0King/makefun-news-image-20261125/reward.svg)](https://make.fun/bounty/news-image-20261125?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261125)

# The World on One Page — 25 November 2026 (v8.2)

One-page newspaper infographic: 50 stories from Wednesday 25 November
2026, drawn as a broadsheet front page (1024 × 1024 PNG).

v8.2 is the current edition: 50 stories, all verified against their
sources on 26 Nov 2026 (see `../VERIFICATION_v8.2.md`). Changes over v7:
numeric labels inside the main scenes, fields 18 → 20, a fourth status
tier `CONFIRMED` (28 of 50 stories), the UTC timeline moved to the top,
and medium cards as full-width field-coloured bands.

## Files

| File | What it is |
|---|---|
| `render.py` | The renderer. Python + Pillow, written from scratch. Reads a stories JSON file and a Natural Earth land GeoJSON, writes `entry.png`. |
| `entry.png` | The rendered page (1024 × 1024). |
| `main.ts` | Entry-image checks: missing-file preflight, PNG signature + IHDR validation, exact 1024 × 1024 size check, SHA-256 verification. |
| `stories.json` | Story data for this edition (main 3 + medium 12 + also 35 = 50 stories). |

## Render

```sh
python3 render.py [--input stories.json] [--geo land-110m.geojson] [--output entry.png]
```

No timestamps are embedded, so two runs on the same input produce
identical bytes. Verified: two consecutive runs give
SHA-256 `b4c0a4c5e9618c62173f0ca9658195fa6454340ae4d4447441e1fb424140e3f7`.

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
  kicker and a status chip (`CONFIRMED` = official record or 2+ major
  outlets, `OFFICIAL` = government data or an official statement,
  `CLAIM` = one party's claim, not independently confirmed,
  `REPORTED` = outlet reporting; the chip says nothing about the date —
  that is the DATE CHECK's job).
- `MORE OF THE DAY`: a 12-story grid with vector icons, plus
  `WHY IT MATTERS`: one line per main story, in the story's own words.
- A real vector world map from Natural Earth 110m data, with numbered
  pins for every story that carries coordinates, and a legend.
- `ALSO ON …` one-line index in three columns (35 stories, 16 fields).
- A UTC timeline (only time points that survived fact-checking are
  plotted) and `WIRES READ UP TO … UTC`.
- Footer: DATE CHECK (with named exclusions and borderline rulings),
  a NOT YET line for scheduled items that had not happened by the wires
  cut (Thanksgiving 26 Nov, German budget vote 27 Nov, UK energy cap
  1 Jan 2027), LEFT OUT, and the
  `CONFIRMED / OFFICIAL / CLAIM / REPORTED` legend.

The page's own wording contains no "DRAWN BY …" line and no other
self-referential credit line.

## Data note

The image in this directory was rendered from `stories.json`
(main 3 + medium 12 + also 35 = 50 stories).

Two things the renderer handles deliberately:

1. Timeline: only real `HH:MM` stamps are plotted. Most stories carry
   `time_utc: "n/a"` and those are skipped; the two disproved v3 times
   (03:00, 05:56) stay excluded via `BAD_TIMES`.
2. Map pins: placeless items carry lat 0, lon 0, which is a null-island
   sentinel, not a location in the Gulf of Guinea — they get no pin and
   no legend entry. The 15 pinned main+medium stories are listed in the
   legend in two columns as number + place.

Icon matching is word-boundary based, so "supermarket" is not read as
a market chart, "Metropolitan" is not read as the Metro, "searched"
is not read as the sea, and the Tai Po anniversary feature gets a
neutral document picture instead of an explosion pictogram.

## License

MIT — see `LICENSE`.
