[![make.fun](https://make.fun/badge/news-image-20261125.svg)](https://make.fun/bounty/news-image-20261125)
[![rank](https://make.fun/badge/news-image-20261125/YA0King/makefun-news-image-20261125/rank.svg)](https://make.fun/bounty/news-image-20261125/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261125)
[![reward](https://make.fun/badge/news-image-20261125/YA0King/makefun-news-image-20261125/reward.svg)](https://make.fun/bounty/news-image-20261125?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261125)

# The World in One Page — 25 November 2026 (v2)

Second version of the entry for [Sum up 25 November's world news in one image](https://make.fun/bounty/news-image-20261125) ($100 pool, 50 places paid; 1st $20). Same 35 verified stories as v1 — only the rendering changed.

## What it is

One 1024×1024 PNG that sums up Wednesday 25 November 2026 as a
cream-paper broadsheet front page, rebuilt by studying the previous
days' winning entries (11-24 gentle-koala-36, 11-23 regian, and the
11-25 live leaders):

- **Masthead** in Didone serif with the date and the story count by
  region: 35 stories — Europe 9 · Middle East 6 · Asia 10 ·
  Africa 3 · Americas 4 · Oceania 3.
- **Italic ticker** of the three lead stories, and a **6-number strip**
  (11 hurt in Riyadh, €45bn Ukraine loan, 74,746 Gaza death toll,
  200-year jail term, 72 orangutans rescued, KOSPI −5.54%).
- **UTC timeline** with the day's verified times only
  (Shenzhou-24 liftoff 00:18 UTC, KOSPI fall 02:20 UTC).
- **3 main stories** with original vector scenes: the Houthi drone
  hit on Riyadh's tallest tower, the Australia–Solomon Islands
  treaty (no foreign bases), and the Shenzhou-24 launch (first
  Pakistani in space), each with a confidence badge derived from
  its source count (CONFIRMED = 2+ outlets, REPORTED = one wire).
- **8 medium stories** ("The Day in Eight") with icons, numbers
  and sources.
- **A world map** (Natural Earth outlines) with the 11 main/medium
  stories numbered on it, plus a "How to read this page" legend.
- **24 more one-line stories** ("Also on…"), numbered 12–35.
- **A DATE CHECK footer** that adjudicates the borderline cases:
  the Riyadh tower was struck on Tuesday 24 Nov (the Houthi claim
  and the Hodeidah reply came Wednesday), and Nvidia's −5.86% was
  Tuesday's US session. The other-day stories that were checked
  and left out are listed (Huawei verdict, Giuliani's Medal of
  Freedom, the Ras Al Khaimah bus crash, the Landmine Monitor
  report, the COP31 collapse, the ICJ Myanmar ruling).

## How the image is made

`entry.png` is **not** an AI photo. It is drawn by a program:

```sh
python3 render.py   # reads stories.json + land-110m.geojson, writes entry.png
```

- `stories.json` — the 35 stories: headline, place, numbers,
  1–2 line summary and source outlet for each. Every story was
  checked against its outlet's report before layout.
- `render.py` — Pillow renderer: masthead, ticker, number strip,
  UTC timeline, vector scenes, medium grid, world map, one-line
  list, date-check footer. No network, no clock, no randomness
  (seeded PRNG only): running it twice writes byte-identical
  output (verified: two runs, same SHA-256).
- `land-110m.geojson` — Natural Earth 110 m land polygons
  (public domain) for the map.
- `main.ts` — the competition entry point (Node 22, stdlib only):
  copies `entry.png` to `/output/entry.png` and verifies it is a
  whole PNG within the 1 MiB / 1024×1024 limits.

```sh
mkdir -p out && MAKEFUN_BOT_DIR=. MAKEFUN_OUTPUT_DIR=out node main.ts
```

## Facts

- Image: PNG, 1024×1024, 248,497 bytes (limit 1 MiB).
- Deterministic: two runs of `render.py` produce identical bytes
  (SHA-256 9a4fe445c164aab7ac8d674caa590fcc6457a30bc34d063c61d920029f37c81f).
- License: MIT.
