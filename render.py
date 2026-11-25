#!/usr/bin/env python3
"""Render v3 of the news-image entry: the 'extreme' broadsheet.

Built on v2 (cream paper, Didone masthead, ticker, 6-number strip,
UTC timeline, heroes, map, ALSO list, DATE CHECK) and pushed toward
what the 11-25 leaders do:
  - 50 stories: 3 heroes + 13 cards with mini scene strips + 34 ALSO
    one-liners (2 cols x 17 rows), after noble-koala (50 stories).
  - 8 vector scenes: 3 hero scenes + 'THE DAY IN EIGHT' 4x2 small
    scenes, after wu-san (8 drawn scenes).
  - Full UTC timeline built from each story's time_utc field, after
    malapetakasatu (UTC Timeline & Date-Check Audit).
  - DATE CHECK with borderline adjudication + confidence legend,
    after gentle-koala-36 (Hormuz ruling).
  - Real vector world map (Natural Earth polygons) with pins.

Usage: python3 render_v3.py [stories.json] [out.png]
Deterministic: same input files -> same bytes out. No network, no
clock, no randomness (seeded PRNG only). Reads the stories file +
land-110m.geojson, writes a 1024x1024 PNG.
"""
import json
import math
import os
import random
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
GEO = os.path.join(HERE, "..", "repo", "land-110m.geojson")
W, H = 1024, 1024

# ---- palette (sampled from the winning pages) ----
PAPER = (246, 241, 231)
PAPER2 = (251, 248, 240)
INK = (18, 18, 18)
RED = (168, 30, 30)
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
    return ("CONFIRMED", (14, 122, 107)) if n >= 2 else ("REPORTED",
                                                        (194, 94, 0))


def parse_hhmm(t):
    """'HH:MM' -> minutes since midnight, or None."""
    try:
        hh, mm = t.split(":")
        return int(hh) * 60 + int(mm)
    except Exception:
        return None


def parse_day(date_str):
    """'Wednesday 25 November 2026' -> (weekday abbr, day-of-year)."""
    import datetime
    try:
        dt = datetime.datetime.strptime(date_str, "%A %d %B %Y")
        return dt.strftime("%a").upper(), dt.timetuple().tm_yday
    except Exception:
        return "WED", 329
    """'HH:MM' -> minutes since midnight, or None."""
    try:
        hh, mm = t.split(":")
        return int(hh) * 60 + int(mm)
    except Exception:
        return None


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
        # glow radius scaled to the scene height and clamped inside it:
        # a fixed 26px glow spills far outside 18px card strips.
        r_max = max(4, min(26, h // 3))
        gy = min(glow_y, y + h - r_max)
        gy = max(gy, y + r_max)
        for r in range(r_max, 0, -2):
            d.ellipse([x + w // 2 - r * 3, gy - r,
                       x + w // 2 + r * 3, gy + r],
                      fill=(176, 84, 30))
    rnd = random.Random(seed)
    for _ in range(26):
        sx = x + rnd.randint(3, w - 3)
        sy = y + rnd.randint(3, max(4, h - 6))
        r = rnd.choice([1, 1, 2])
        d.ellipse([sx, sy, sx + r, sy + r], fill=(255, 255, 255))

def draw_scene_riyadh(d, x, y, w, h):
    """Night: tower hit, fire burst halfway up, skyline silhouette."""
    night_sky(d, x, y, w, h, seed=7, glow_y=y + h - 20)
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
    bx0, by0 = cx + 20, top_y + 52
    for r, col in ((16, (255, 120, 20)), (11, (255, 176, 32)),
                   (6, (255, 230, 120))):
        d.ellipse([bx0 - r, by0 - r, bx0 + r, by0 + r], fill=col)
    for ang in range(0, 360, 30):
        a = math.radians(ang)
        d.line([(bx0, by0),
                (bx0 + 22 * math.cos(a), by0 + 22 * math.sin(a))],
               fill=(255, 176, 32), width=2)
    for dx, dy in ((-52, -14), (-38, -22), (-24, -10)):
        d.ellipse([cx + dx - 2, top_y + 30 + dy, cx + dx + 2, top_y + 30 + dy],
                  fill=(255, 255, 255))
    d.rectangle([x, y + h - 18, x + w, y + h], fill=(16, 32, 60))


def draw_scene_solomons(d, x, y, w, h, polys):
    """Pacific mini-map: SE Australia + Solomons, dashed route, callout."""
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
    cx0, cy0 = x + w - 138, y + h - 30
    d.rectangle([cx0, cy0, cx0 + 130, cy0 + 22], fill=WHITE,
                outline=RED, width=2)
    d.text((cx0 + 7, cy0 + 5), "NO FOREIGN BASES", font=font(F_SANS_B, 10),
           fill=RED)


def draw_scene_shenzhou(d, x, y, w, h):
    """Night launch: rocket on pad, flame, smoke, 00:18 UTC badge."""
    night_sky(d, x, y, w, h, seed=23, glow_y=y + h - 16)
    cx = x + w // 2
    d.rectangle([x, y + h - 14, x + w, y + h], fill=(24, 28, 34))
    d.rectangle([cx - 34, y + int(h * 0.26), cx - 28, y + h - 14],
                fill=(90, 96, 104))
    d.rectangle([cx + 28, y + int(h * 0.38), cx + 34, y + h - 14],
                fill=(90, 96, 104))
    for ox, oy, r in ((-26, 0.84, 13), (26, 0.88, 15), (0, 0.92, 17)):
        oy = y + int(h * oy)
        d.ellipse([cx + ox - r, oy - r, cx + ox + r, oy + r],
                  fill=(190, 195, 200))
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
    bx0, by0 = x + w - 86, y + 8
    d.rectangle([bx0, by0, bx0 + 78, by0 + 18], fill=(10, 22, 44))
    d.text((bx0 + 7, by0 + 3), "00:18 UTC", font=font(F_SANS_B, 11),
           fill=WHITE)


# ---------------------------------------------------------------- mini scenes
def mini_scene(d, x, y, w, h, kind, seed):
    """Small flat vector scene for card strips and THE DAY IN EIGHT.
    kind picks the motif; everything is seeded so it is deterministic."""
    rnd = random.Random(seed)
    if kind == "fire":
        night_sky(d, x, y, w, h, seed=seed + 1, glow_y=y + h - 6)
        bx = x + w // 2
        for r, col in ((h // 2, (255, 120, 20)), (h // 3, (255, 176, 32)),
                       (h // 5, (255, 230, 120))):
            d.ellipse([bx - r, y + h - r - 4, bx + r, y + h - 4], fill=col)
        d.rectangle([x, y + h - 5, x + w, y + h], fill=(16, 32, 60))
    elif kind == "sea":
        d.rectangle([x, y, x + w, y + h], fill=(206, 224, 234))
        for i in range(3):
            yy = y + h * (0.35 + i * 0.22)
            d.line([(x, yy), (x + w, yy)], fill=(90, 140, 180), width=2)
        sx = x + w // 2
        d.polygon([(sx - w * 0.28, y + h * 0.62), (sx + w * 0.28, y + h * 0.62),
                   (sx + w * 0.2, y + h * 0.85), (sx - w * 0.2, y + h * 0.85)],
                  fill=(40, 60, 90))
        d.rectangle([sx - 4, y + h * 0.2, sx + 14, y + h * 0.62],
                    fill=(40, 60, 90))
    elif kind == "rocket":
        night_sky(d, x, y, w, h, seed=seed + 2, glow_y=y + h - 4)
        cx = x + w // 2
        d.polygon([(cx - 4, y + h * 0.55), (cx + 4, y + h * 0.55),
                   (cx, y + h - 2)], fill=(255, 140, 20))
        d.rectangle([cx - 5, y + h * 0.18, cx + 5, y + h * 0.55],
                    fill=(235, 238, 242))
        d.polygon([(cx - 5, y + h * 0.18), (cx + 5, y + h * 0.18),
                   (cx, y + 2)], fill=(200, 40, 40))
        d.rectangle([x, y + h - 4, x + w, y + h], fill=(24, 28, 34))
    elif kind == "court":
        d.rectangle([x, y, x + w, y + h], fill=(233, 224, 196))
        for i in range(3):
            cx = x + w * (0.22 + i * 0.28)
            d.rectangle([cx - 3, y + h * 0.25, cx + 3, y + h * 0.85],
                        fill=(120, 100, 70))
        d.rectangle([x + w * 0.08, y + h * 0.15, x + w * 0.92, y + h * 0.25],
                    fill=(90, 75, 50))
        d.rectangle([x + w * 0.08, y + h * 0.85, x + w * 0.92, y + h * 0.95],
                    fill=(90, 75, 50))
    elif kind == "deal":
        d.rectangle([x, y, x + w, y + h], fill=(214, 228, 238))
        d.rectangle([x + w * 0.3, y + h * 0.2, x + w * 0.7, y + h * 0.8],
                    fill=WHITE, outline=(31, 78, 156), width=2)
        for i in range(3):
            d.line([(x + w * 0.36, y + h * (0.32 + i * 0.16)),
                    (x + w * 0.64, y + h * (0.32 + i * 0.16))],
                   fill=(31, 78, 156), width=2)
        d.ellipse([x + w * 0.58, y + h * 0.6, x + w * 0.68, y + h * 0.72],
                  fill=RED)
    elif kind == "chart":
        d.rectangle([x, y, x + w, y + h], fill=(251, 248, 240))
        d.line([(x + 4, y + h - 6), (x + w - 4, y + h - 6)], fill=INK, width=2)
        d.line([(x + 4, y + h - 6), (x + 4, y + 4)], fill=INK, width=2)
        pts = [(x + 6 + i * (w - 12) / 4, y + h * (0.3 + 0.14 * i))
               for i in range(5)]
        for a, b in zip(pts, pts[1:]):
            d.line([a, b], fill=RED, width=3)
    elif kind == "flag":
        d.rectangle([x, y, x + w, y + h], fill=(233, 224, 196))
        d.line([(x + w * 0.2, y + 3), (x + w * 0.2, y + h - 3)], fill=INK,
               width=2)
        d.polygon([(x + w * 0.2, y + 3), (x + w * 0.75, y + h * 0.25),
                   (x + w * 0.2, y + h * 0.5)], fill=RED)
        for i in range(6):
            cx = x + w * (0.15 + 0.13 * i)
            d.ellipse([cx - 3, y + h - 9, cx + 3, y + h - 3],
                      fill=(40, 60, 90))
    elif kind == "burst":
        night_sky(d, x, y, w, h, seed=seed + 3)
        cx, cy = x + w // 2, y + h // 2
        for ang in range(0, 360, 30):
            a = math.radians(ang)
            d.line([(cx, cy), (cx + h * 0.45 * math.cos(a),
                               cy + h * 0.45 * math.sin(a))],
                   fill=(255, 176, 32), width=2)
        d.ellipse([cx - 6, cy - 6, cx + 6, cy + 6], fill=(255, 230, 120))
    elif kind == "forest":
        d.rectangle([x, y, x + w, y + h], fill=(206, 224, 200))
        for i in range(5):
            cx = x + w * (0.12 + i * 0.19)
            hh = h * (0.4 + 0.12 * ((i * 7) % 3))
            d.polygon([(cx, y + h - hh), (cx - 7, y + h - 8),
                       (cx + 7, y + h - 8)], fill=(46, 125, 50))
        d.rectangle([x, y + h - 8, x + w, y + h], fill=(90, 75, 50))
    elif kind == "train":
        d.rectangle([x, y, x + w, y + h], fill=(214, 228, 238))
        cx = x + w // 2
        d.rounded_rectangle([cx - w * 0.2, y + h * 0.15, cx + w * 0.2,
                             y + h * 0.9], radius=4, fill=(31, 78, 156))
        d.rectangle([cx - w * 0.13, y + h * 0.25, cx + w * 0.13, y + h * 0.45],
                    fill=WHITE)
        d.line([(x + 4, y + h - 4), (x + w - 4, y + h - 4)], fill=INK, width=2)
    else:  # "city": night skyline
        night_sky(d, x, y, w, h, seed=seed + 4, glow_y=y + h - 4)
        bx = x + 3
        while bx < x + w - 10:
            bw = rnd.randint(8, 16)
            bh = rnd.randint(int(h * 0.3), int(h * 0.7))
            d.rectangle([bx, y + h - 4 - bh, bx + bw, y + h - 4],
                        fill=(10, 22, 44))
            bx += bw + 3
        d.rectangle([x, y + h - 4, x + w, y + h], fill=(16, 32, 60))


def scene_for(story):
    """Pick a mini-scene kind from a story's art field or keywords."""
    art = (story.get("art") or "").lower()
    if art in ("tower", "fire", "sea", "rocket", "court", "deal", "chart",
               "flag", "burst", "forest", "train", "city"):
        return art
    text = ((story.get("headline") or "") + " " +
            (story.get("body") or "") + " " +
            (story.get("text") or "")).lower()
    for kw, kind in (("fire", "fire"), ("burn", "fire"), ("blast", "burst"),
                     ("strike", "burst"), ("ship", "sea"), ("port", "sea"),
                     ("launch", "rocket"), ("space", "rocket"),
                     ("court", "court"), ("trial", "court"),
                     ("deal", "deal"), ("pact", "deal"), ("sign", "deal"),
                     ("stock", "chart"), ("market", "chart"),
                     ("forest", "forest"), ("wildfire", "forest"),
                     ("train", "train"), ("metro", "train"),
                     ("flag", "flag"), ("protest", "flag")):
        if kw in text:
            return kind
    return "city"


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
    with open(GEO) as f:
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
HERO_TOPIC = {1: "STRIKE", 2: "TREATY", 3: "SPACE"}

# pin nudges (story n -> dx, dy) to unclump the map
PIN_NUDGE = {1: (14, -8), 4: (-14, 8), 7: (-13, 9), 8: (13, -9),
             10: (-6, 8), 11: (8, -10)}


def build_timeline(data, all_stories):
    """Full UTC timeline from per-story time_utc fields, sorted.
    Falls back to the data file's explicit 'timeline' list, then to
    nothing (the strip still prints the wires-read cutoff)."""
    events = []
    for s in all_stories:
        t = s.get("time_utc")
        m = parse_hhmm(t) if t else None
        if m is not None:
            label = s.get("headline") or s.get("text") or ""
            events.append((m, t, label))
    events.sort()
    if not events and data.get("timeline"):
        for t, label in data["timeline"]:
            m = parse_hhmm(t)
            if m is not None:
                events.append((m, t, label))
        events.sort()
    return events


def main():
    data_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        HERE, "stories.json")
    out_path = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
        HERE, "entry_v3.png")
    with open(data_path) as f:
        data = json.load(f)
    main_stories = data["main"]
    medium = data["medium"]
    also = data["also"]
    eight = data.get("eight") or medium[:8]
    all_stories = main_stories + medium + also

    order = ["EUROPE", "MIDDLE EAST", "ASIA", "AFRICA", "AMERICAS",
             "OCEANIA", "GLOBAL"]
    counts = {r: 0 for r in order}
    for s in all_stories:
        counts[s["region"]] = counts.get(s["region"], 0) + 1
    count_str = " · ".join(f"{r} {counts[r]}" for r in order
                           if counts[r] > 0)
    n_total = len(all_stories)
    date_str = data.get("date", "")
    # masthead date line: 'Wednesday 25 November 2026'
    mast = date_str
    sub = (f"{n_total} STORIES, ALL FROM {date_str.upper()}  ·  "
           f"{count_str}")
    numbers = data.get("numbers", [
        ("11", "hurt in Riyadh tower strike"),
        ("45bn", "Ukraine loan on the table"),
        ("74,746", "Gaza death toll, WAFA says"),
        ("200 yrs", "Mackenzie jail term"),
        ("72", "orangutans rescued"),
        ("-5.54%", "KOSPI's Wednesday fall"),
    ])
    ticker = data.get("ticker", "")
    if isinstance(ticker, list):
        ticker = "  ◆  ".join(ticker[:3])
    timeline = build_timeline(data, all_stories)
    wires = data.get("wires_read", "")

    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W - 1, H - 1], outline=INK, width=2)
    MX = 14
    CW = W - 2 * MX

    wd_abbr, doy = parse_day(date_str)
    # ---- top line ----
    y = 8
    f_top = font(F_SANS_B, 11)
    d.text((MX, y), "THE WORLD ON ONE PAGE", font=f_top, fill=INK)
    c = f"DAY {doy} OF 2026"
    d.text(((W - d.textlength(c, font=f_top)) / 2, y), c, font=f_top,
           fill=RED)
    r = f"EVERY STORY DATED {date_str.upper()}"
    d.text((W - MX - d.textlength(r, font=f_top), y), r, font=f_top,
           fill=INK)
    y += 14
    d.line([(MX, y), (W - MX, y)], fill=INK, width=2)
    y += 4

    # ---- masthead ----
    size = 52
    while size > 40:
        f_mast = font(F_DISP_BLK, size)
        tw = d.textlength(mast, font=f_mast)
        if tw <= CW:
            break
        size -= 2
    bb = d.textbbox((0, 0), mast, font=f_mast)
    d.text(((W - tw) / 2, y - bb[1]), mast, font=f_mast, fill=INK)
    y += (bb[3] - bb[1]) + 5
    d.line([(MX, y), (W - MX, y)], fill=INK, width=1)
    y += 4

    # ---- sub-line ----
    f_sub = font(F_SANS_B, 12)
    sw = d.textlength(sub, font=f_sub)
    d.text(((W - sw) / 2, y), sub, font=f_sub, fill=INK)
    y += 13
    d.line([(MX, y), (W - MX, y)], fill=INK, width=1)
    y += 3

    # ---- ticker (italic serif; diamonds drawn as vector shapes) ----
    if ticker:
        f_tick = font(F_DISP_I, 15)
        parts = ticker.split("  ◆  ")
        # shrink the longest part until the whole ticker fits the page
        for _ in range(40):
            tw = sum(d.textlength(p, font=f_tick) for p in parts) + \
                26 * (len(parts) - 1)
            if tw <= CW:
                break
            i = max(range(len(parts)),
                    key=lambda j: d.textlength(parts[j], font=f_tick))
            words = parts[i].split()
            if len(words) > 2:
                parts[i] = " ".join(words[:-1]) + " …"
            else:
                parts[i] = parts[i][:max(4, len(parts[i]) - 4)] + " …"
        tw = sum(d.textlength(p, font=f_tick) for p in parts) + \
            26 * (len(parts) - 1)
        tx = (W - tw) / 2
        for i, p in enumerate(parts):
            d.text((tx, y), p, font=f_tick, fill=INK)
            tx += d.textlength(p, font=f_tick)
            if i < len(parts) - 1:
                cx0, cy0 = tx + 13, y + 9
                d.polygon([(cx0, cy0 - 5), (cx0 + 5, cy0),
                           (cx0, cy0 + 5), (cx0 - 5, cy0)], fill=RED)
                tx += 26
        y += 17
        d.line([(MX, y), (W - MX, y)], fill=INK, width=1)
        y += 3

    # ---- numbers strip: 6 cells ----
    cell_w = CW / 6
    f_num = font(F_DISP_B, 22)
    f_cap = font(F_SANS, 9)
    for i, (big, small) in enumerate(numbers[:6]):
        cx = MX + i * cell_w
        if i > 0:
            d.line([(cx - 4, y + 2), (cx - 4, y + 36)], fill=LIGHT_RULE,
                   width=1)
        d.text((cx, y + 6), big, font=f_num, fill=INK)
        bw = d.textlength(big, font=f_num)
        cap = wrap(d, small, f_cap, cell_w - bw - 12)
        draw_lines(d, cap[:2], cx + bw + 5, y + 8, f_cap, GRAY, 11)
    y += 30
    d.line([(MX, y), (W - MX, y)], fill=INK, width=1)
    y += 3

    # ---- UTC timeline strip: full 00:00-24:00 axis, event dots ----
    f_tl = font(F_SANS_B, 10)
    d.rectangle([MX, y, MX + 58, y + 14], fill=RED)
    d.text((MX + 5, y + 2), f"{wd_abbr} UTC", font=f_tl, fill=WHITE)
    axis_x0, axis_x1 = MX + 66, W - MX
    axis_y = y + 10
    d.line([(axis_x0, axis_y), (axis_x1, axis_y)], fill=LIGHT_RULE, width=1)
    for hh in range(0, 25, 4):
        px = axis_x0 + (axis_x1 - axis_x0) * hh / 24.0
        d.line([(px, axis_y - 3), (px, axis_y + 3)], fill=GRAY, width=1)
        lab = f"{hh:02d}:00"
        lw = d.textlength(lab, font=font(F_SANS, 8))
        lx = min(max(px - lw / 2, MX), W - MX - lw)
        d.text((lx, y + 1), lab, font=font(F_SANS, 8), fill=GRAY)
    for m, t, label in timeline:
        px = axis_x0 + (axis_x1 - axis_x0) * m / 1440.0
        d.ellipse([px - 3, axis_y - 3, px + 3, axis_y + 3], fill=RED,
                  outline=WHITE, width=1)
    y += 15
    # event labels under the axis (max 6, earliest first, truncated)
    f_ev = font(F_SANS, 9)
    shown = timeline[:6]
    ex = axis_x0
    for m, t, label in shown:
        if len(label) > 26:
            label = label[:23].rsplit(" ", 1)[0] + " …"
        item = f"{t} {label}"
        iw = d.textlength(item, font=f_ev)
        if ex + iw > axis_x1:
            break
        d.text((ex, y), t, font=font(F_SANS_B, 9), fill=RED)
        ex += d.textlength(t, font=font(F_SANS_B, 9)) + 3
        d.text((ex, y), label, font=f_ev, fill=INK)
        ex += d.textlength(label, font=f_ev) + 10
        d.text((ex, y), "|", font=f_ev, fill=LIGHT_RULE)
        ex += 8
    if wires:
        d.text((axis_x1 - d.textlength(wires, font=f_ev), y), wires,
               font=f_ev, fill=GRAY)
    y += 11
    d.line([(MX, y), (W - MX, y)], fill=INK, width=1)
    y += 5

    # ---- heroes ----
    polys = load_land()
    col_w, gap = 322, 15
    art_h = 92
    hero_bottom = y
    for i, s in enumerate(main_stories):
        x = MX + i * (col_w + gap)
        col = REGION_COLORS[s["region"]]
        art = (s.get("art") or "").lower()
        if art == "tower":
            draw_scene_riyadh(d, x, y, col_w, art_h)
        elif art == "treaty":
            draw_scene_solomons(d, x, y, col_w, art_h, polys)
        elif art == "rocket":
            draw_scene_shenzhou(d, x, y, col_w, art_h)
        else:
            mini_scene(d, x, y, col_w, art_h, scene_for(s), 100 + i)
        d.rectangle([x, y, x + col_w, y + art_h], outline=INK, width=1)
        yy = y + art_h + 4
        kick = f"{s['region']} · {HERO_TOPIC.get(s['n'], 'NEWS')}"
        f_kick = font(F_SANS_B, 10)
        kw = d.textlength(kick, font=f_kick) + 12
        d.rectangle([x, yy, x + kw, yy + 15], fill=col)
        d.text((x + 6, yy + 2), kick, font=f_kick, fill=WHITE)
        bx = x + kw + 5
        d.ellipse([bx, yy, bx + 15, yy + 15], fill=INK)
        num = str(s["n"])
        nw = d.textlength(num, font=font(F_SANS_B, 10))
        d.text((bx + 7 - nw / 2, yy + 2), num, font=font(F_SANS_B, 10),
               fill=WHITE)
        d.text((bx + 20, yy + 1), s["place"], font=font(F_SANS_B, 11),
               fill=INK)
        yy += 20
        f_hl = font(F_DISP_B, 21)
        hl = wrap(d, s["headline"], f_hl, col_w)
        assert len(hl) <= 2, f"hero headline {len(hl)} lines: {s['n']}"
        yy = draw_lines(d, hl, x, yy, f_hl, INK, 21)
        yy += 2
        f_body = font(F_SERIF, 11)
        bl = wrap(d, s["body"], f_body, col_w)
        bl = trunc_lines(bl, 2, col_w, d, f_body)
        yy = draw_lines(d, bl, x, yy, f_body, (40, 40, 40), 12)
        yy += 3
        badge, bcol = status_badge(s)
        f_src = font(F_SANS_B, 9)
        d.text((x, yy), s["source"], font=f_src, fill=GRAY)
        bw = d.textlength(badge, font=f_src)
        d.rectangle([x + col_w - bw - 10, yy - 1,
                     x + col_w, yy + 11], fill=bcol)
        d.text((x + col_w - bw - 5, yy + 1), badge, font=f_src, fill=WHITE)
        yy += 11
        hero_bottom = max(hero_bottom, yy)
    y = hero_bottom + 6

    # ---- map strip: real vector land + pins, legend at right ----
    # (the label chip overlaps the map's top-left corner: no extra row)
    map_h = 96
    map_x, map_w = MX, 640
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
        if "lon" not in s or "lat" not in s:
            continue
        px = map_x + (s["lon"] + 180) / 360.0 * map_w
        py = y + (78 - s["lat"]) / 138.0 * map_h
        dx, dy = PIN_NUDGE.get(s["n"], (0, 0))
        # deterministic declutter: spread any geographic cluster
        dx += ((s["n"] * 13) % 17) - 8
        dy += ((s["n"] * 7) % 13) - 6
        px, py = px + dx, py + dy
        col = REGION_COLORS[s["region"]]
        d.ellipse([px - 6, py - 6, px + 6, py + 6], fill=col,
                  outline=WHITE, width=2)
        num = str(s["n"])
        nw = d.textlength(num, font=font(F_SANS_B, 7))
        d.text((px - nw / 2, py - 4), num, font=font(F_SANS_B, 7),
               fill=WHITE)
    lx, lw = map_x + map_w + 12, CW - map_w - 12
    d.rectangle([lx, y, lx + lw, y + map_h], fill=PAPER2,
                outline=LIGHT_RULE, width=1)
    ly = y + 5
    d.text((lx + 8, ly), "HOW TO READ THIS PAGE", font=font(F_SANS_B, 9),
           fill=INK)
    ly += 13
    regs = [(r, counts[r]) for r in order if counts[r] > 0]
    for j, (r, c) in enumerate(regs):
        ex = lx + 8 + (j % 3) * 112
        ey = ly + (j // 3) * 12
        d.rectangle([ex, ey + 1, ex + 8, ey + 10], fill=REGION_COLORS[r])
        d.text((ex + 11, ey), f"{r} {c}", font=font(F_SANS, 9), fill=INK)
    ly += ((len(regs) + 2) // 3) * 12 + 2
    d.text((lx + 8, ly), "CONFIRMED = 2+ outlets  ·  REPORTED = one wire",
           font=font(F_SANS, 8), fill=GRAY)
    ly += 12
    d.text((lx + 8, ly), "MAP: NATURAL EARTH 110M", font=font(F_SANS, 8),
           fill=GRAY)
    ly += 11
    d.text((lx + 8, ly), "EVERY PIN IS A STORY ON THIS PAGE",
           font=font(F_SANS, 8), fill=GRAY)
    # label chip on top of the map corner (drawn last so it sits above)
    d.rectangle([map_x, y, map_x + 96, y + 14], fill=INK)
    d.text((map_x + 6, y + 2), "WHERE IT HAPPENED",
           font=font(F_SANS_B, 9), fill=WHITE)
    d.text((map_x + 102, y + 2), "pins carry the story numbers",
           font=font(F_DISP_I, 10), fill=INK)
    y += map_h + 5

    # ---- cards: 5 cols x N rows, each with a mini scene strip ----
    d.text((MX, y), "MORE OF THE DAY", font=font(F_SANS_B, 11), fill=INK)
    d.text((W - MX - d.textlength("EVERY PICTURE DATED, EVERY STORY SOURCED",
                                  font=font(F_SANS_B, 9)), y + 1),
           "EVERY PICTURE DATED, EVERY STORY SOURCED",
           font=font(F_SANS_B, 9), fill=GRAY)
    y += 14
    ccol_w, cgap = 192, 8
    card_h = 70
    cols = 5
    for i, s in enumerate(medium):
        col_i, row_i = i % cols, i // cols
        x = MX + col_i * (ccol_w + cgap)
        ry = y + row_i * (card_h + 4)
        col = REGION_COLORS[s["region"]]
        d.line([(x, ry), (x + ccol_w, ry)], fill=col, width=2)
        mini_scene(d, x, ry + 2, ccol_w, 18, scene_for(s), 200 + s["n"])
        d.rectangle([x, ry + 2, x + ccol_w, ry + 20], outline=INK, width=1)
        # number chip on the strip
        d.ellipse([x + 3, ry + 4, x + 16, ry + 17], fill=INK)
        num = str(s["n"])
        nw = d.textlength(num, font=font(F_SANS_B, 9))
        d.text((x + 10 - nw / 2, ry + 5), num, font=font(F_SANS_B, 9),
               fill=WHITE)
        yy = ry + 23
        f_ch = font(F_SANS_B, 11)
        hl = wrap(d, s["headline"], f_ch, ccol_w)
        if len(hl) > 2:
            f_ch = font(F_SANS_B, 10)
            hl = wrap(d, s["headline"], f_ch, ccol_w)
        assert len(hl) <= 2, f"card headline {len(hl)} lines: {s['n']}"
        yy = draw_lines(d, hl[:2], x, yy, f_ch, INK, 12)
        f_cb = font(F_SANS, 10)
        bl = wrap(d, s.get("body", ""), f_cb, ccol_w)
        bl = trunc_lines(bl, 1, ccol_w, d, f_cb)
        if bl:
            yy = draw_lines(d, bl, x, yy + 1, f_cb, (40, 40, 40), 11)
        d.text((x, ry + 60), s["source"], font=font(F_SANS_B, 8),
               fill=GRAY)
    rows = (len(medium) + cols - 1) // cols
    y += rows * (card_h + 4) - 4 + 6

    # ---- THE DAY IN EIGHT: 4 cols x 2 rows of small scenes ----
    d.text((MX, y), "THE DAY IN EIGHT", font=font(F_SANS_B, 12), fill=INK)
    y += 13
    ecol_w, egap = 241, 10
    esc_h = 38
    row_h = esc_h + 15
    for i, s in enumerate(eight[:8]):
        col_i, row_i = i % 4, i // 4
        x = MX + col_i * (ecol_w + egap)
        ry = y + row_i * row_h
        mini_scene(d, x, ry, ecol_w, esc_h, scene_for(s), 300 + s["n"])
        d.rectangle([x, ry, x + ecol_w, ry + esc_h], outline=INK, width=1)
        cap = f"{s['n']} · {s['place']} — " + (s.get("headline") or
                                               s.get("text") or "")
        f_cap = font(F_SANS_B, 10)
        cl = wrap(d, cap, f_cap, ecol_w)
        cl = trunc_lines(cl, 1, ecol_w, d, f_cap)
        draw_lines(d, cl, x, ry + esc_h + 3, f_cap, INK, 11)
    y += 2 * row_h + 6

    # ---- ALSO list: 2 cols x N rows, one line per story ----
    d.text((MX, y), f"ALSO ON {date_str.upper()}",
           font=font(F_SANS_B, 12), fill=INK)
    y += 13
    acol_w = 490
    f_an = font(F_SANS_B, 9)
    f_at = font(F_SANS, 9)
    for i, s in enumerate(also):
        col_i, row_i = i % 2, i // 2
        x = MX + col_i * (acol_w + 16)
        ry = y + row_i * 11
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
    y += ((len(also) + 1) // 2) * 11 + 4

    # ---- footer: DATE CHECK ----
    d.line([(MX, y), (W - MX, y)], fill=INK, width=2)
    y += 5
    f_dc = font(F_SANS_B, 11)
    d.text((MX, y), "DATE CHECK  ", font=f_dc, fill=RED)
    dw = d.textlength("DATE CHECK  ", font=f_dc)
    f_dct = font(F_SERIF, 10)
    decl = wrap(d, data.get("datecheck", ""), f_dct, CW - dw)
    yy = y
    for ln in decl:
        d.text((MX + dw, yy), ln, font=f_dct, fill=INK)
        yy += 11
    y = yy + 1
    left = "LEFT OUT:  " + "  •  ".join(data.get("excluded", []))
    f_lo = font(F_SANS, 9)
    ll = wrap(d, left, f_lo, CW)
    for ln in ll:
        d.text((MX, y), ln, font=f_lo, fill=GRAY)
        y += 10
    y += 1
    seen, srcs = [], []
    for s in all_stories:
        for p in s["source"].split("·"):
            p = p.strip()
            if p and p not in seen:
                seen.append(p)
                srcs.append(p)
    f_src2 = font(F_SANS, 9)
    sl = wrap(d, "Sources: " + " · ".join(srcs), f_src2, CW)
    for ln in sl:
        d.text((MX, y), ln, font=f_src2, fill=GRAY)
        y += 10
    foot = (f"DRAWN BY AN AI AGENT FOR MAKE.FUN  ·  {date_str.upper()}  ·  "
            "ONE PAGE, ONE DAY")
    fw = d.textlength(foot, font=font(F_SANS, 8))
    d.text(((W - fw) / 2, y + 1), foot, font=font(F_SANS, 8), fill=GRAY)
    y += 10
    print(f"final y={y} (canvas {H})  stories={n_total} "
          f"medium={len(medium)} also={len(also)} timeline={len(timeline)}")
    assert y <= H, f"overflow: {y} > {H}"

    img.save(out_path, format="PNG")
    print(f"wrote {out_path} {os.path.getsize(out_path)} bytes")


if __name__ == "__main__":
    main()
