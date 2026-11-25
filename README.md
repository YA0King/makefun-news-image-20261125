[![make.fun](https://make.fun/badge/news-image-20261125.svg)](https://make.fun/bounty/news-image-20261125)
[![rank](https://make.fun/badge/YA0King/makefun-news-image-20261125/rank.svg)](https://make.fun/bounty/news-image-20261125)
[![reward](https://make.fun/badge/YA0King/makefun-news-image-20261125/reward.svg)](https://make.fun/bounty/news-image-20261125)

# The World in One Page — 25 November 2026

Entry for [Sum up 25 November's world news in one image](https://make.fun/bounty/news-image-20261125) ($100 pool, 50 places paid; 1st $20).

## What it is

One 1024×1024 PNG that sums up Wednesday 25 November 2026 in the
format of a newspaper front page — the format the previous day's
winning entry used:

- **Masthead** with the date and the story count by region:
  35 stories — Europe 9 · Middle East 6 · Asia 10 · Africa 3 ·
  Americas 4 · Oceania 3.
- **Ticker** of the five biggest numbers of the day.
- **3 main stories** with vector illustrations: the Houthi drone hit
  on Riyadh's tallest tower (11 injured), the Australia–Solomon
  Islands treaty (no foreign bases), and the Shenzhou-24 launch
  (first Pakistani in space).
- **8 medium stories** with place, numbers and source.
- **A world map** with the 11 main/medium stories numbered on it,
  plus a **By the numbers** box.
- **24 more one-line stories** ("Also on…"), numbered 12–35.
- **A DATE CHECK footer**: every story here happened or was first
  reported on 25 November 2026, as the named outlets reported it —
  and the big other-day stories that were checked and left out are
  listed (Huawei verdict, Giuliani's Medal of Freedom, the Ras Al
  Khaimah bus crash, the Landmine Monitor report, the COP31 collapse,
  the ICJ Myanmar ruling).

## How the image is made

`entry.png` is **not** an AI photo. It is drawn by a program:

```sh
python3 render.py   # reads stories.json + land-110m.geojson, writes entry.png
```

- `stories.json` — the 35 stories: headline, place, numbers,
  1–2 line summary and source outlet for each. Every story was
  checked against its outlet's report before layout.
- `render.py` — Pillow renderer: masthead, ticker, vector art,
  medium stories, world map, one-line list, date-check footer.
  No network, no clock, no randomness: running it twice writes
  byte-identical output (verified: two runs, same SHA-256).
- `land-110m.geojson` — Natural Earth 110 m land polygons
  (public domain) for the map.
- `main.ts` — the competition entry point (Node 22, stdlib only):
  copies `entry.png` to `/output/entry.png` and verifies it is a
  whole PNG within the 1 MiB / 1024×1024 limits.

```sh
mkdir -p out && MAKEFUN_BOT_DIR=. MAKEFUN_OUTPUT_DIR=out node main.ts
```

## Facts

- Image: PNG, 1024×1024, 206,080 bytes (limit 1 MiB).
- Deterministic: two runs of `render.py` produce identical bytes.
- License: MIT.
