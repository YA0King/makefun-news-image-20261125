#!/usr/bin/env python3
"""Render v2 of the news-image-20261125 entry: a broadsheet front page.

Rebuilt by studying the winning entries (gentle-koala-36 11-24, regian
11-23, wu-san / noble-koala / malapetakasatu / illyash22 11-25):
cream paper, Didone serif masthead, italic ticker, 6-number strip,
UTC timeline, 3 illustrated hero scenes, 4x2 medium grid, world map
with region-coloured pins, dense ALSO list, DATE CHECK footer with
borderline adjudication and a confidence legend.

Same stories.json as v1 (35 stories, 25 Nov 2026) - only the rendering
changed. Deterministic: same input files -> same bytes out. No network,
no clock, no randomness (seeded PRNG only). Reads stories.json +
land-110m.geojson from its own directory, writes entry.png (1024x1024).
"""
import json
import math
import os
import random

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(HERE, "..", "repo")
W, H = 1024, 1024

# ---- palette (sampled from the winning pages) ----
PAPER = (246, 241, 231)
PAPER2 = (251, 248, 240)
INK = (18, 18, 18)
RED = (168, 30, 30)
DARKRED = (140, 22, 22)
GRAY = (96, 96, 94)
RULE = (70, 70, 70)
LIGHT_RULE = (190, 182, 165)
MAP_SEA = (214, 228, 238)
MAP_LAND = (233, 224, 196)
MAP_LINE = (178, 168, 138)
WHITE = (255, 255, 255)
GOLD = (255, 200, 60)

REGION_COLORS = {
    "EUROPE": (31, 78, 156),
    "MIDDLE EAST": (176, 42, 42),
    "ASIA": (122, 79, 163),
    "AFRICA": (194, 94, 0),
    "AMERICAS": (46, 125, 50),
    "OCEANIA": (14, 122, 107),
    "GLOBAL": (90, 90, 90),
}

# ---- fonts ----
NOTO = "/usr/share/fonts/truetype/noto"
LIB = "/usr/share/fonts/truetype/liberation"
F_DISP_BLK = os.path.join(NOTO, "NotoSerifDisplay-Black.ttf")
F_DISP_B = os.path.join(NOTO, "NotoSerifDisplay-Bold.ttf")
F_DISP_I = os.path.join(NOTO, "NotoSerifDisplay-Italic.ttf")
F_SERIF = os.path.join(NOTO, "NotoSerif-Regular.ttf")
F_SERIF_B = os.path.join(NOTO, "NotoSerif-Bold.ttf")
F_SANS_B = os.path.join(LIB, "LiberationSans-Bold.ttf")
F_SANS = os.path.join(LIB, "LiberationSans-Regular.ttf")


def font(path, size):
    return ImageFont.truetype(path, size)


def wrap(draw, text, fnt, max_w):
    """Greedy word wrap by pixel width. Returns list of lines."""
    words = text.split()
    lines, cur = [], ""
    for w_ in words:
        trial = (cur + " " + w_).strip()
        if draw.textlength(trial, font=fnt) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w_
    if cur:
        lines.append(cur)
    return lines


def draw_lines(draw, lines, x, y, fnt, fill, lh):
    for ln in lines:
        draw.text((x, y), ln, font=fnt, fill=fill)
        y += lh
    return y


def trunc_lines(lines, max_lines, max_w, draw, fnt):
    """Keep at most max_lines lines, ellipsis on the last if cut."""
    if len(lines) <= max_lines:
        return lines
    out = lines[:max_lines]
    last = out[-1]
    while last and draw.textlength(last + " …", font=fnt) > max_w:
        last = last.rsplit(" ", 1)[0] if " " in last else last[:-1]
    out[-1] = (last + " …").strip()
    return out


def status_badge(s):
    """Confidence badge derived honestly from the source list:
    2+ named outlets -> CONFIRMED, 1 outlet -> REPORTED."""
    n = len([p for p in s["source"].split("·") if p.strip()])
    return ("CONFIRMED", (14, 122, 107)) if n >= 2 else ("REPORTED", (194, 94, 0))


# ---------------------------------------------------------------- scenes
def night_sky(d, x, y, w, h, seed, glow_y=None):
    """Dark blue night sky, seeded stars, optional orange horizon glow."""
    bands = [(13, 27, 51), (18, 38, 68), (26, 52, 88), (40, 68, 104)]
    for i in range(h):
        t = i / max(h - 1, 1)
        c0 = bands[min(int(t * 3), 2)]
        c1 = bands[min(int(t * 3) + 1, 3)]
        f = t * 3 - int(t * 3)
        d.line([(x, y + i), (x + w, y + i)],
               fill=tuple(int(c0[k] + (c1[k] - c0[k]) * f) for k in range(3)))
    if glow_y is not None:
        for r in range(26, 0, -2):
            d.ellipse([x + w // 2 - r * 3, glow_y - r,
                       x + w // 2 + r * 3, glow_y + r],
                      fill=(176, 84, 30))
    rnd = random.Random(seed)
    for _ in range(26):
        sx = x + rnd.randint(3, w - 3)
        sy = y + rnd.randint(3, h - 24)
        r = rnd.choice([1, 1, 2])
        d.ellipse([sx, sy, sx + r, sy + r], fill=(255, 255, 255))


def draw_scene_riyadh(d, x, y, w, h):
    """Night: PIF tower hit, fire burst halfway up, skyline silhouette."""
    night_sky(d, x, y, w, h, seed=7, glow_y=y + h - 20)
    # skyline silhouette
    rnd = random.Random(11)
    bx = x + 4
    while bx < x + w - 18:
        bw = rnd.randint(16, 30)
        bh = rnd.randint(20, 46)
        d.rectangle([bx, y + h - 18 - bh, bx + bw, y + h - 18],
                    fill=(10, 22, 44))
        for wy in range(y + h - 16 - bh + 4, y + h - 20, 9):
            if rnd.random() < 0.5:
                d.point([(bx + 4, wy), (bx + bw - 5, wy)],
                        fill=(255, 210, 110))
        bx += bw + 4
    # PIF tower: tapered, pale, diagonal ribs
    cx = x + w // 2
    top_y, bot_y = y + 10, y + h - 18
    d.polygon([(cx - 12, top_y), (cx + 12, top_y),
               (cx + 22, bot_y), (cx - 22, bot_y)], fill=(216, 221, 228))
    for i in range(7):
        yy = top_y + 8 + i * 11
        d.line([(cx - 14, yy), (cx + 14, yy + 5)], fill=(140, 148, 158),
               width=2)
    for wy in range(top_y + 20, bot_y - 6, 10):
        d.point([(cx - 6, wy), (cx + 6, wy)], fill=(255, 220, 120))
    # impact burst halfway up the tower
    bx0, by0 = cx + 20, top_y + 52
    for r, col in ((16, (255, 120, 20)), (11, (255, 176, 32)),
                   (6, (255, 230, 120))):
        d.ellipse([bx0 - r, by0 - r, bx0 + r, by0 + r], fill=col)
    for ang in range(0, 360, 30):
        a = math.radians(ang)
        d.line([(bx0, by0),
                (bx0 + 22 * math.cos(a), by0 + 22 * math.sin(a))],
               fill=(255, 176, 32), width=2)
    # drone dots approaching
    for dx, dy in ((-52, -14), (-38, -22), (-24, -10)):
        d.ellipse([cx + dx - 2, top_y + 30 + dy, cx + dx + 2, top_y + 30 + dy],
                  fill=(255, 255, 255))
    d.rectangle([x, y + h - 18, x + w, y + h], fill=(16, 32, 60))


def draw_scene_solomons(d, x, y, w, h, polys):
    """Pacific mini-map: SE Australia + Solomons, dashed Canberra-Honiara
    route, NO FOREIGN BASES callout. Land from Natural Earth polygons.
    Drawn on a temp layer so polygons clip cleanly at the panel edge."""
    layer = Image.new("RGB", (w, h), (206, 224, 234))
    dl = ImageDraw.Draw(layer)
    lon0, lon1, lat0, lat1 = 140.0, 166.0, -40.0, -4.0

    def proj(lon, lat):
        px = (lon - lon0) / (lon1 - lon0) * w
        py = (lat1 - lat) / (lat1 - lat0) * h
        return px, py

    for ring in polys:
        pts = [proj(lon, lat) for lon, lat in ring]
        if len(pts) >= 3:
            dl.polygon(pts, fill=(232, 222, 192), outline=(170, 160, 130))
    d._image.paste(layer, (x, y))
    # route Canberra -> Honiara (dashed)
    c0 = (x + proj(149.13, -35.28)[0], y + proj(149.13, -35.28)[1])
    c1 = (x + proj(159.97, -9.65)[0], y + proj(159.97, -9.65)[1])
    steps = 24
    for i in range(steps):
        if i % 2:
            continue
        t0, t1 = i / steps, (i + 1) / steps
        d.line([(c0[0] + (c1[0] - c0[0]) * t0, c0[1] + (c1[1] - c0[1]) * t0),
                (c0[0] + (c1[0] - c0[0]) * t1, c0[1] + (c1[1] - c0[1]) * t1)],
               fill=(176, 42, 42), width=2)
    for (lon, lat, label, lx, ly) in (
            (149.13, -35.28, "CANBERRA", 10, -4),
            (159.97, -9.65, "HONIARA", -58, -4)):
        px, py = x + proj(lon, lat)[0], y + proj(lon, lat)[1]
        d.ellipse([px - 5, py - 5, px + 5, py + 5], fill=RED, outline=WHITE,
                  width=2)
        d.text((px + lx, py + ly), label, font=font(F_SANS_B, 9), fill=INK)
    # callout
    cx0, cy0 = x + w - 138, y + h - 30
    d.rectangle([cx0, cy0, cx0 + 130, cy0 + 22], fill=WHITE,
                outline=RED, width=2)
    d.text((cx0 + 7, cy0 + 5), "NO FOREIGN BASES", font=font(F_SANS_B, 10),
           fill=RED)


def draw_scene_shenzhou(d, x, y, w, h):
    """Night launch: rocket on pad, flame, smoke, 00:18 UTC badge."""
    night_sky(d, x, y, w, h, seed=23, glow_y=y + h - 16)
    cx = x + w // 2
    # launch pad + tower
    d.rectangle([x, y + h - 14, x + w, y + h], fill=(24, 28, 34))
    d.rectangle([cx - 34, y + int(h * 0.26), cx - 28, y + h - 14],
                fill=(90, 96, 104))
    d.rectangle([cx + 28, y + int(h * 0.38), cx + 34, y + h - 14],
                fill=(90, 96, 104))
    # smoke
    for ox, oy, r in ((-26, 0.84, 13), (26, 0.88, 15), (0, 0.92, 17)):
        oy = y + int(h * oy)
        d.ellipse([cx + ox - r, oy - r, cx + ox + r, oy + r],
                  fill=(190, 195, 200))
    # flame + rocket body (fractions of h so the scene scales)
    body_top = y + int(h * 0.24)
    body_bot = y + int(h * 0.72)
    d.polygon([(cx - 9, body_bot), (cx + 9, body_bot), (cx, y + h - 2)],
              fill=(255, 140, 20))
    d.polygon([(cx - 5, body_bot), (cx + 5, body_bot), (cx, y + h - 12)],
              fill=(255, 220, 60))
    d.rectangle([cx - 11, body_top, cx + 11, body_bot],
                fill=(235, 238, 242))
    d.polygon([(cx - 11, body_top), (cx + 11, body_top), (cx, y + 10)],
              fill=(200, 40, 40))
    d.polygon([(cx - 11, body_bot - 14), (cx - 25, body_bot + 2),
               (cx - 11, body_bot)], fill=(200, 40, 40))
    d.polygon([(cx + 11, body_bot - 14), (cx + 25, body_bot + 2),
               (cx + 11, body_bot)], fill=(200, 40, 40))
    d.ellipse([cx - 5, body_top + 12, cx + 5, body_top + 22],
              fill=(120, 190, 230), outline=(60, 60, 60))
    # 00:18 UTC badge
    bx0, by0 = x + w - 86, y + 8
    d.rectangle([bx0, by0, bx0 + 78, by0 + 18], fill=(10, 22, 44))
    d.text((bx0 + 7, by0 + 3), "00:18 UTC", font=font(F_SANS_B, 11),
           fill=WHITE)


# ---------------------------------------------------------------- icons
def icon_ship(d, x, y, s, col):
    d.polygon([(x, y + s * 0.55), (x + s, y + s * 0.55),
               (x + s * 0.85, y + s * 0.85), (x + s * 0.15, y + s * 0.85)],
              fill=col)
    d.rectangle([x + s * 0.2, y + s * 0.15, x + s * 0.45, y + s * 0.55],
                fill=col)
    d.rectangle([x + s * 0.55, y + s * 0.3, x + s * 0.8, y + s * 0.55],
                fill=col)


def icon_flame(d, x, y, s, col):
    d.polygon([(x + s * 0.5, y), (x + s * 0.85, y + s * 0.55),
               (x + s * 0.65, y + s * 0.55), (x + s * 0.8, y + s * 0.85),
               (x + s * 0.2, y + s * 0.85), (x + s * 0.35, y + s * 0.55),
               (x + s * 0.15, y + s * 0.55)], fill=col)
    d.ellipse([x + s * 0.35, y + s * 0.6, x + s * 0.65, y + s * 0.9],
              fill=(255, 200, 60))


def icon_chart_down(d, x, y, s, col):
    d.line([(x, y + s * 0.85), (x + s, y + s * 0.85)], fill=col, width=2)
    d.line([(x, y + s * 0.85), (x, y + s * 0.1)], fill=col, width=2)
    d.line([(x + s * 0.1, y + s * 0.25), (x + s * 0.4, y + s * 0.45),
            (x + s * 0.6, y + s * 0.35), (x + s * 0.9, y + s * 0.75)],
           fill=RED, width=3)


def icon_doc(d, x, y, s, col):
    d.rectangle([x + s * 0.15, y, x + s * 0.85, y + s], fill=WHITE,
                outline=col, width=2)
    for i in range(3):
        d.line([(x + s * 0.28, y + s * (0.25 + i * 0.2)),
                (x + s * 0.72, y + s * (0.25 + i * 0.2))], fill=col, width=2)
    d.ellipse([x + s * 0.58, y + s * 0.68, x + s * 0.82, y + s * 0.92],
              fill=RED)


def icon_gavel(d, x, y, s, col):
    d.line([(x + s * 0.15, y + s * 0.85), (x + s * 0.85, y + s * 0.15)],
           fill=col, width=4)
    d.rectangle([x + s * 0.55, y, x + s * 0.95, y + s * 0.3], fill=col)
    d.line([(x + s * 0.1, y + s * 0.9), (x + s * 0.6, y + s * 0.9)],
           fill=col, width=3)


def icon_flag(d, x, y, s, col):
    d.line([(x + s * 0.2, y), (x + s * 0.2, y + s)], fill=col, width=2)
    d.polygon([(x + s * 0.2, y), (x + s * 0.9, y + s * 0.2),
               (x + s * 0.2, y + s * 0.45)], fill=col)


def icon_train(d, x, y, s, col):
    d.rounded_rectangle([x, y, x + s, y + s], radius=4, fill=col)
    d.rectangle([x + s * 0.15, y + s * 0.15, x + s * 0.4, y + s * 0.4],
                fill=WHITE)
    d.rectangle([x + s * 0.6, y + s * 0.15, x + s * 0.85, y + s * 0.4],
                fill=WHITE)
    d.line([(x + s * 0.15, y + s * 0.65), (x + s * 0.85, y + s * 0.65)],
           fill=WHITE, width=2)


def icon_burst(d, x, y, s, col):
    cx, cy = x + s / 2, y + s / 2
    for ang in range(0, 360, 30):
        a = math.radians(ang)
        d.line([(cx, cy), (cx + s * 0.48 * math.cos(a),
                           cy + s * 0.48 * math.sin(a))], fill=col, width=2)
    d.ellipse([cx - s * 0.2, cy - s * 0.2, cx + s * 0.2, cy + s * 0.2],
              fill=(255, 176, 32))


ICONS = {"ship": icon_ship, "flame": icon_flame, "chart": icon_chart_down,
         "doc": icon_doc, "gavel": icon_gavel, "flag": icon_flag,
         "train": icon_train, "burst": icon_burst}


def load_land():
    with open(os.path.join(REPO, "land-110m.geojson")) as f:
        gj = json.load(f)
    polys = []
    for feat in gj["features"]:
        geom = feat["geometry"]
        geoms = geom["coordinates"] if geom["type"] == "MultiPolygon" \
            else [geom["coordinates"]]
        for poly in geoms:
            for ring in poly:
                cur = [ring[0]]
                for a, b in zip(ring, ring[1:]):
                    if abs(b[0] - a[0]) > 180:
                        polys.append(cur)
                        cur = [b]
                    else:
                        cur.append(b)
                polys.append(cur)
    return polys

# ---------------------------------------------------------------- layout
MEDIUM_META = {
    4: ("ship", "PORT", "HIT", "WAR"),
    5: ("train", "DEAL", "STRIKE OFF", "LABOUR"),
    6: ("flag", "70+", "BOATS SUNK", "SECURITY"),
    7: ("doc", "SECRETS", "FOR SALE", "ESPIONAGE"),
    8: ("chart", "-5.86%", "NVIDIA", "MARKETS"),
    9: ("flag", "€45bn", "UKRAINE LOAN", "BUDGET"),
    10: ("ship", "2", "SHIPS HIT", "WAR"),
    11: ("flame", "4", "KILLED", "WAR"),
}

HERO_TOPIC = {1: "STRIKE", 2: "TREATY", 3: "SPACE"}

# pin nudges (story n -> dx, dy) to unclump the map
PIN_NUDGE = {1: (14, -8), 4: (-14, 8), 7: (-13, 9), 8: (13, -9),
             10: (-6, 8), 11: (8, -10)}

# timeline: only times verified against named outlets (see report)
TIMELINE = [
    ("00:18", "Shenzhou-24 lifts off"),
    ("02:20", "Kospi -5.54% at 11:20 Seoul"),
]

NUMBERS = [
    ("11", "hurt in Riyadh tower strike"),
    ("€45bn", "Ukraine loan on the table"),
    ("74,746", "Gaza death toll, WAFA says"),
    ("200 yrs", "Mackenzie jail term"),
    ("72", "orangutans rescued"),
    ("-5.54%", "KOSPI's Wednesday fall"),
]

DATECHECK = (
    "Every story here happened or was first reported on Wed 25 Nov 2026, "
    "as the named outlets reported it. Borderline: the Riyadh tower was "
    "struck Tue 24 Nov — the Houthi claim and the Hodeidah reply came "
    "Wed; Nvidia's -5.86% was Tuesday's US session."
)

# ticker in proper case (same three lead stories as the mains)
TICKER = ("Houthis hit Riyadh tower — 11 hurt  ◆  Solomons sign pact: "
          "no foreign bases  ◆  Shenzhou-24 lifts off with first Pakistani")


def main():
    with open(os.path.join(REPO, "stories.json")) as f:
        data = json.load(f)
    main_stories = data["main"]
    medium = data["medium"]
    also = data["also"]
    all_stories = main_stories + medium + also

    order = ["EUROPE", "MIDDLE EAST", "ASIA", "AFRICA", "AMERICAS",
             "OCEANIA", "GLOBAL"]
    counts = {r: 0 for r in order}
    for s in all_stories:
        counts[s["region"]] = counts.get(s["region"], 0) + 1
    count_str = " · ".join(f"{r} {counts[r]}" for r in order
                           if counts[r] > 0)

    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W - 1, H - 1], outline=INK, width=2)
    MX = 16
    CW = W - 2 * MX

    # ---- top line ----
    y = 10
    f_top = font(F_SANS_B, 11)
    d.text((MX, y), "THE WORLD ON ONE PAGE", font=f_top, fill=INK)
    c = "DAY 329 OF 2026"
    d.text(((W - d.textlength(c, font=f_top)) / 2, y), c, font=f_top,
           fill=RED)
    r = "EVERY STORY DATED WEDNESDAY 25 NOV"
    d.text((W - MX - d.textlength(r, font=f_top), y), r, font=f_top,
           fill=INK)
    y += 17
    d.line([(MX, y), (W - MX, y)], fill=INK, width=2)
    y += 5

    # ---- masthead ----
    size = 60
    while size > 40:
        f_mast = font(F_DISP_BLK, size)
        tw = d.textlength("Wednesday 25 November 2026", font=f_mast)
        if tw <= CW:
            break
        size -= 2
    bb = d.textbbox((0, 0), "Wednesday 25 November 2026", font=f_mast)
    d.text(((W - tw) / 2, y - bb[1]), "Wednesday 25 November 2026",
           font=f_mast, fill=INK)
    y += (bb[3] - bb[1]) + 6
    d.line([(MX, y), (W - MX, y)], fill=INK, width=1)
    y += 5

    # ---- sub-line ----
    sub = f"35 STORIES, ALL FROM WEDNESDAY 25 NOV  ·  {count_str}"
    f_sub = font(F_SANS_B, 12)
    sw = d.textlength(sub, font=f_sub)
    d.text(((W - sw) / 2, y), sub, font=f_sub, fill=INK)
    y += 16
    d.line([(MX, y), (W - MX, y)], fill=INK, width=1)
    y += 4

    # ---- ticker (italic serif; diamonds drawn as vector shapes:
    # the Display italic has no U+25C6 glyph)
    f_tick = font(F_DISP_I, 16)
    parts = TICKER.split("  ◆  ")
    tw = sum(d.textlength(p, font=f_tick) for p in parts) + \
        28 * (len(parts) - 1)
    tx = (W - tw) / 2
    for i, p in enumerate(parts):
        d.text((tx, y), p, font=f_tick, fill=INK)
        tx += d.textlength(p, font=f_tick)
        if i < len(parts) - 1:
            cx0, cy0 = tx + 14, y + 10
            d.polygon([(cx0, cy0 - 6), (cx0 + 6, cy0),
                       (cx0, cy0 + 6), (cx0 - 6, cy0)], fill=RED)
            tx += 28
    y += 20
    d.line([(MX, y), (W - MX, y)], fill=INK, width=1)
    y += 4

    # ---- numbers strip: 6 cells ----
    cell_w = CW / 6
    f_num = font(F_DISP_B, 26)
    f_cap = font(F_SANS, 9)
    for i, (big, small) in enumerate(NUMBERS):
        cx = MX + i * cell_w
        if i > 0:
            d.line([(cx - 4, y + 2), (cx - 4, y + 40)], fill=LIGHT_RULE,
                   width=1)
        d.text((cx, y + 8), big, font=f_num, fill=INK)
        bw = d.textlength(big, font=f_num)
        cap = wrap(d, small, f_cap, cell_w - bw - 14)
        draw_lines(d, cap[:2], cx + bw + 6, y + 10, f_cap, GRAY, 11)
    y += 42
    d.line([(MX, y), (W - MX, y)], fill=INK, width=1)
    y += 3

    # ---- UTC timeline strip (verified times only) ----
    f_tl = font(F_SANS_B, 10)
    d.rectangle([MX, y, MX + 62, y + 16], fill=RED)
    d.text((MX + 6, y + 3), "WED UTC", font=f_tl, fill=WHITE)
    tx = MX + 70
    for t, label in TIMELINE:
        d.text((tx, y + 3), t, font=f_tl, fill=RED)
        tx += d.textlength(t, font=f_tl) + 4
        d.text((tx, y + 3), label, font=f_tl, fill=INK)
        tx += d.textlength(label, font=f_tl) + 12
        d.text((tx, y + 3), "|", font=f_tl, fill=LIGHT_RULE)
        tx += 12
    d.text((tx, y + 3), "WIRES READ UP TO 08:30 UTC", font=f_tl, fill=GRAY)
    y += 18
    d.line([(MX, y), (W - MX, y)], fill=INK, width=1)
    y += 6

    # ---- heroes ----
    polys = load_land()
    col_w, gap = 320, 16
    art_h = 92
    hero_bottom = y
    for i, s in enumerate(main_stories):
        x = MX + i * (col_w + gap)
        col = REGION_COLORS[s["region"]]
        if s["art"] == "tower":
            draw_scene_riyadh(d, x, y, col_w, art_h)
        elif s["art"] == "treaty":
            draw_scene_solomons(d, x, y, col_w, art_h, polys)
        else:
            draw_scene_shenzhou(d, x, y, col_w, art_h)
        d.rectangle([x, y, x + col_w, y + art_h], outline=INK, width=1)
        yy = y + art_h + 6
        # kicker chip + number + place
        kick = f"{s['region']} · {HERO_TOPIC[s['n']]}"
        f_kick = font(F_SANS_B, 10)
        kw = d.textlength(kick, font=f_kick) + 12
        d.rectangle([x, yy, x + kw, yy + 16], fill=col)
        d.text((x + 6, yy + 3), kick, font=f_kick, fill=WHITE)
        bx = x + kw + 6
        d.ellipse([bx, yy, bx + 16, yy + 16], fill=INK)
        num = str(s["n"])
        nw = d.textlength(num, font=font(F_SANS_B, 10))
        d.text((bx + 8 - nw / 2, yy + 3), num, font=font(F_SANS_B, 10),
               fill=WHITE)
        d.text((bx + 22, yy + 2), s["place"], font=font(F_SANS_B, 11),
               fill=INK)
        yy += 22
        # headline (serif display, max 3 lines)
        f_hl = font(F_DISP_B, 23)
        hl = wrap(d, s["headline"], f_hl, col_w)
        assert len(hl) <= 3, f"hero headline {len(hl)} lines: {s['n']}"
        yy = draw_lines(d, hl, x, yy, f_hl, INK, 25)
        yy += 3
        # body (serif, max 2 lines, truncated - winners run ~2 lines)
        f_body = font(F_SERIF, 11)
        bl = wrap(d, s["body"], f_body, col_w)
        bl = trunc_lines(bl, 2, col_w, d, f_body)
        yy = draw_lines(d, bl, x, yy, f_body, (40, 40, 40), 14)
        yy += 4
        # source + status badge
        badge, bcol = status_badge(s)
        f_src = font(F_SANS_B, 9)
        d.text((x, yy), s["source"], font=f_src, fill=GRAY)
        bw = d.textlength(badge, font=f_src)
        d.rectangle([x + col_w - bw - 10, yy - 1,
                     x + col_w, yy + 12], fill=bcol)
        d.text((x + col_w - bw - 5, yy + 1), badge, font=f_src, fill=WHITE)
        yy += 12
        hero_bottom = max(hero_bottom, yy)
    y = hero_bottom + 8

    # ---- medium grid: 4 cols x 2 rows ----
    d.text((MX, y), "THE DAY IN EIGHT", font=font(F_SANS_B, 12), fill=INK)
    d.text((W - MX - d.textlength("EVERY PICTURE DATED, EVERY STORY SOURCED",
                                  font=font(F_SANS_B, 10)), y + 1),
           "EVERY PICTURE DATED, EVERY STORY SOURCED",
           font=font(F_SANS_B, 10), fill=GRAY)
    y += 16
    mcol_w, mgap = 238, 13
    cell_h = 96
    for i, s in enumerate(medium):
        col_i, row_i = i % 4, i // 4
        x = MX + col_i * (mcol_w + mgap)
        ry = y + row_i * cell_h
        col = REGION_COLORS[s["region"]]
        d.line([(x, ry), (x + mcol_w, ry)], fill=col, width=3)
        icon, big, cap, topic = MEDIUM_META[s["n"]]
        # left stat column
        ICONS[icon](d, x + 2, ry + 10, 22, col)
        f_big = font(F_SANS_B, 13)
        bl2 = wrap(d, big, f_big, 54)
        draw_lines(d, bl2[:1], x, ry + 36, f_big, INK, 15)
        f_cap = font(F_SANS, 8)
        cl = wrap(d, cap, f_cap, 54)
        draw_lines(d, cl[:2], x, ry + 52, f_cap, GRAY, 10)
        # right column
        tx = x + 60
        f_mk = font(F_SANS_B, 10)
        d.ellipse([tx, ry + 8, tx + 14, ry + 22], fill=INK)
        num = str(s["n"])
        nw = d.textlength(num, font=font(F_SANS_B, 9))
        d.text((tx + 7 - nw / 2, ry + 10), num, font=font(F_SANS_B, 9),
               fill=WHITE)
        d.text((tx + 18, ry + 9),
               f"{s['place']} · {topic}", font=f_mk, fill=col)
        # headline: 13px, fall back to 12 if it wraps to 3 lines
        f_mh = font(F_SANS_B, 13)
        hl = wrap(d, s["headline"], f_mh, mcol_w - 60)
        if len(hl) > 2:
            f_mh = font(F_SANS_B, 12)
            hl = wrap(d, s["headline"], f_mh, mcol_w - 60)
        assert len(hl) <= 2, f"medium headline {len(hl)} lines: {s['n']}"
        yy = draw_lines(d, hl[:2], tx, ry + 26, f_mh, INK, 16)
        f_mb = font(F_SANS, 10)
        bl = wrap(d, s["body"], f_mb, mcol_w - 60)
        bl = trunc_lines(bl, 2, mcol_w - 60, d, f_mb)
        yy = draw_lines(d, bl, tx, yy + 2, f_mb, (40, 40, 40), 12)
        d.text((tx, ry + 86), s["source"], font=font(F_SANS_B, 8),
               fill=GRAY)
    y += 2 * cell_h + 6

    # ---- map + legend ----
    d.rectangle([MX, y, MX + 168, y + 17], fill=INK)
    d.text((MX + 8, y + 3), "WHERE IT HAPPENED", font=font(F_SANS_B, 11),
           fill=WHITE)
    d.text((MX + 178, y + 3), "pins carry the story numbers",
           font=font(F_DISP_I, 11), fill=GRAY)
    y += 20
    map_x, map_w, map_h = MX, 600, 100
    d.rectangle([map_x, y, map_x + map_w, y + map_h], fill=MAP_SEA)
    for ring in polys:
        pts = []
        for lon, lat in ring:
            if lat < -60:
                continue
            px = map_x + (lon + 180) / 360.0 * map_w
            py = y + (78 - lat) / 138.0 * map_h
            pts.append((px, py))
        if len(pts) >= 3:
            d.polygon(pts, fill=MAP_LAND, outline=MAP_LINE)
    for s in main_stories + medium:
        px = map_x + (s["lon"] + 180) / 360.0 * map_w
        py = y + (78 - s["lat"]) / 138.0 * map_h
        dx, dy = PIN_NUDGE.get(s["n"], (0, 0))
        px, py = px + dx, py + dy
        col = REGION_COLORS[s["region"]]
        d.ellipse([px - 8, py - 8, px + 8, py + 8], fill=col,
                  outline=WHITE, width=2)
        num = str(s["n"])
        nw = d.textlength(num, font=font(F_SANS_B, 9))
        d.text((px - nw / 2, py - 5), num, font=font(F_SANS_B, 9),
               fill=WHITE)
    # legend box right of map
    lx, lw = map_x + map_w + 16, CW - map_w - 16
    d.rectangle([lx, y, lx + lw, y + map_h], fill=PAPER2,
                outline=LIGHT_RULE, width=1)
    ly = y + 8
    d.text((lx + 10, ly), "HOW TO READ THIS PAGE", font=font(F_SANS_B, 10),
           fill=INK)
    ly += 16
    regs = [(r, counts[r]) for r in order if counts[r] > 0]
    for j, (r, c) in enumerate(regs):
        ex = lx + 10 + (j % 2) * 180
        ey = ly + (j // 2) * 14
        d.rectangle([ex, ey + 2, ex + 9, ey + 11],
                    fill=REGION_COLORS[r])
        d.text((ex + 13, ey), f"{r} {c}", font=font(F_SANS, 10), fill=INK)
    ly += ((len(regs) + 1) // 2) * 14 + 4
    d.line([(lx + 10, ly), (lx + lw - 10, ly)], fill=LIGHT_RULE, width=1)
    ly += 5
    d.text((lx + 10, ly), "CONFIRMED = 2+ outlets  ·  REPORTED = one wire",
           font=font(F_SANS, 9), fill=GRAY)
    ly += 13
    d.text((lx + 10, ly), "Maps and drawings are original vector art.",
           font=font(F_DISP_I, 10), fill=GRAY)
    y += map_h + 8

    # ---- ALSO list: 3 cols x 8 rows ----
    d.text((MX, y), "ALSO ON WEDNESDAY 25 NOVEMBER",
           font=font(F_SANS_B, 13), fill=INK)
    y += 18
    acol_w = 320
    f_an = font(F_SANS_B, 10)
    f_at = font(F_SANS, 10)
    for i, s in enumerate(also):
        col_i, row_i = i % 3, i // 3
        x = MX + col_i * (acol_w + 16)
        ry = y + row_i * 14
        # one visual line per story (winners' ALSO rows are single lines):
        # bold "n · PLACE — " + regular text, truncated with ellipsis
        head = f"{s['n']} · {s['place']} — "
        hw = d.textlength(head, font=f_an)
        d.text((x, ry), head, font=f_an, fill=(31, 58, 95))
        lines = wrap(d, s["text"], f_at, acol_w - hw)
        first = lines[0] if lines else ""
        if len(lines) > 1:
            while first and d.textlength(first + " …", font=f_at) > \
                    acol_w - hw:
                first = first.rsplit(" ", 1)[0] if " " in first \
                    else first[:-1]
            first = (first + " …").strip()
        d.text((x + hw, ry), first, font=f_at, fill=INK)
    y += 8 * 14 + 4

    # ---- footer: DATE CHECK ----
    d.line([(MX, y), (W - MX, y)], fill=INK, width=2)
    y += 6
    f_dc = font(F_SANS_B, 11)
    d.text((MX, y), "DATE CHECK  ", font=f_dc, fill=RED)
    dw = d.textlength("DATE CHECK  ", font=f_dc)
    f_dct = font(F_SERIF, 10)
    decl = wrap(d, DATECHECK, f_dct, CW - dw)
    yy = y
    for ln in decl:
        d.text((MX + dw, yy), ln, font=f_dct, fill=INK)
        yy += 12
    y = yy + 2
    left = "LEFT OUT:  " + "  •  ".join(data["excluded"])
    f_lo = font(F_SANS, 10)
    ll = wrap(d, left, f_lo, CW)
    for ln in ll:
        d.text((MX, y), ln, font=f_lo, fill=GRAY)
        y += 12
    y += 2
    f_src2 = font(F_SANS, 9)
    srcs = ("Sources: SCMP · Gulf News · AFP · FMT · Japan Times · "
            "Al Jazeera · Korea Times · SBS · NYT · EU Insider · "
            "BD Global Times")
    sl = wrap(d, srcs, f_src2, CW)
    for ln in sl:
        d.text((MX, y), ln, font=f_src2, fill=GRAY)
        y += 11
    foot = ("DRAWN BY AN AI AGENT FOR MAKE.FUN  ·  WEDNESDAY 25 NOVEMBER "
            "2026  ·  ONE PAGE, ONE DAY")
    fw = d.textlength(foot, font=font(F_SANS, 8))
    d.text(((W - fw) / 2, y + 2), foot, font=font(F_SANS, 8), fill=GRAY)
    y += 12
    print(f"final y={y} (canvas {H})")
    assert y <= H, f"overflow: {y} > {H}"

    out = os.path.join(HERE, "entry.png")
    img.save(out, format="PNG")
    print(f"wrote {out} {os.path.getsize(out)} bytes")


if __name__ == "__main__":
    main()
