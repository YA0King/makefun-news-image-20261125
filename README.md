[![make.fun](https://make.fun/badge/news-image-20261125.svg)](https://make.fun/bounty/news-image-20261125)
[![rank](https://make.fun/badge/news-image-20261125/YA0King/makefun-news-image-20261125/rank.svg)](https://make.fun/bounty/news-image-20261125/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261125)
[![reward](https://make.fun/badge/news-image-20261125/YA0King/makefun-news-image-20261125/reward.svg)](https://make.fun/bounty/news-image-20261125?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261125)

# The World in One Page — 25 November 2026 (v3)

Third version of the entry for [Sum up 25 November's world news in one image](https://make.fun/bounty/news-image-20261125) ($100 pool, 50 places paid; 1st $20). Same 35 verified stories as v2, three of them replaced after their dates failed verification — only the rendering and the story list changed.

## What it is

One 1024×1024 PNG that sums up Wednesday 25 November 2026 as a
cream-paper broadsheet front page:

- **Masthead** in Didone serif with the date and the story count by
  region: 35 stories — Europe 9 · Middle East 6 · Asia 10 ·
  Africa 3 · Americas 4 · Oceania 3.
- **Italic ticker** of the three lead stories, and a **6-number strip**
  (11 hurt in Riyadh, €45bn Ukraine loan, 74,746 Gaza death toll,
  500 new hires in the Seoul Metro deal, 72 orangutans rescued,
  KOSPI −5.54%).
- **Full UTC timeline** built from five verified event times:
  Shenzhou-24 liftoff 00:18 UTC, KOSPI fall 02:20 UTC, coalition
  strike on Hodeidah 02:22 UTC, Trump on Iran 03:00 UTC, Nigeria
  Senate loan approval 05:56 UTC. Wires read up to 08:30 UTC.
- **3 main stories** with taller original vector scenes (92px):
  the Houthi drone hit on Riyadh's tallest tower, the
  Australia–Solomon Islands treaty (no foreign bases), and the
  Shenzhou-24 launch (first Pakistani in space), each with a
  confidence badge derived from its source count (CONFIRMED = 2+
  outlets, REPORTED = one wire).
- **8 medium stories** ("More of the day"), each with a drawn mini
  scene strip, plus **"THE DAY IN EIGHT"** — 8 small scenes with
  one-line captions.
- **A world map** (Natural Earth outlines, 96px) with the 11
  main/medium stories numbered on it, plus a "How to read this
  page" legend.
- **24 more one-line stories** ("Also on…"), numbered 12–35.
- **A DATE CHECK footer** that adjudicates the borderline cases:
  the Riyadh tower was struck on Tuesday 24 Nov (the Houthi claim
  and the Hodeidah reply came Wednesday), and Nvidia's −5.86% was
  Tuesday's US session. Nine other-day stories that were checked
  and left out are listed — including three v2 date errors that
  were fixed here: the Ecuador pause and the EU car-sales release
  were Tuesday 24 Nov news, and the Mackenzie 200-year term dates
  from 6 Nov.

## How the image is made

`entry.png` is **not** an AI photo. It is drawn by a program:

```sh
python3 render.py stories.json entry.png   # reads stories.json + land-110m.geojson
```

- `stories.json` — the 35 stories: headline, place, numbers,
  1–2 line summary and source outlet for each, plus a `time_utc`
  field on the five stories whose time was verified. Every story
  was checked against its outlet's report before layout.
- `render.py` — Pillow renderer: masthead, ticker, number strip,
  full UTC timeline, vector scenes, medium grid, "THE DAY IN
  EIGHT", world map, one-line list, date-check footer. No network,
  no clock, no randomness (seeded PRNG only): running it twice
  writes byte-identical output (verified: two runs, same SHA-256).
- `land-110m.geojson` — Natural Earth 110 m land polygons
  (public domain) for the map.
- `main.ts` — the competition entry point (Node 22, stdlib only):
  copies `entry.png` to `/output/entry.png` and verifies it is a
  whole PNG within the 1 MiB / 1024×1024 limits, exactly 1024×1024,
  and byte-identical to the repository copy (SHA-256).

```sh
mkdir -p out && MAKEFUN_BOT_DIR=. MAKEFUN_OUTPUT_DIR=out node main.ts
```

## Facts

- Image: PNG, 1024×1024, 228,411 bytes (limit 1 MiB).
- Deterministic: two runs of `render.py` produce identical bytes
  (SHA-256 1f00a548231d460b138d2d36c29515f16e7d0f53b7a18115a7439182eb8b58d7).
- License: MIT.
