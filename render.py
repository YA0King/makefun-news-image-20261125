#!/usr/bin/env python3
"""render.py -- one-page newspaper infographic, 1024x1024 PNG.

v5 edition (25 Nov 2026). Reads stories.json (main 3 + medium 13 + also 21)
plus a Natural Earth land GeoJSON, and draws a broadsheet-style front page
with PIL only. No timestamps are embedded, so two runs on the same input
produce identical bytes.

v6 edition (25 Nov 2026, same day, later wires): main 3 + medium 15 +
also 24 = 42 stories. Changes vs v5:
  - medium grid still 5 columns x 3 rows (15 cards: PCE and GDP promoted
    from the also list); geometry unchanged;
  - also list still three columns, now 8 rows each (24 items);
  - map legend is 3 columns x 6 rows (18 pinned stories: 3 main + 15
    medium); the v5 2-column layout would run off the right edge;
  - the NOT YET line is gone: Iowa and Hera have happened, so the
    stories.json for v6 carries no `notyet` key at all.
  - ALSO pitch is 10px (was 11): with 8 rows the last row ended at
    y=883, and the 888 rule struck through it while the UTC red label
    box clipped its descenders; 10px ends the list clear of both. The
    wires cut-off note moved from the UTC band header (it overlapped
    the 21:00 event label) to the ALSO header row, right-aligned.

v7 edition (26 Nov 2026): main 3 + medium 12 + also 35 = 50 stories.
Changes vs v6:
  - masthead: the big serif date ("Wednesday 25 November 2026",
    48pt Didone) is now the largest text on the page; the title
    "THE WORLD ON ONE PAGE" shrinks to a small eyebrow line with the
    story count and day number (broadsheet nameplate: one dominant
    element, the rest clearly subordinate; nameplate sits between
    double rules; 3-4 type sizes do the ranking, not boxes).
  - medium 15 -> 12, also 24 -> 35; 8 new stories verified 2026-11-26.
  - medium cards gain a right-aligned status word
    (OFFICIAL / CLAIM / REPORTED) and the time_utc in the source
    line; the per-card source name moves to the footer SOURCES line.
  - ALSO rows gain time_utc at the tail where known (9 of 35).
  - footer gains a SOURCES: aggregate line (all outlets, truncated).
  - layout compression to fit 12 ALSO rows: main scene 80 -> 72px,
    WHY IT MATTERS 3 -> 2 lines (why strings shortened in the data),
    map 88 -> 80px, masthead tightened. Warm beige paper kept.
  - numbers band: "500 new hires" swapped for "GBP 2,166 UK energy
    cap, Jan 2027".

v5 changes vs v4 (house style of the 11-19..11-25 leaders):
  - big serif date in the masthead top line (rank1's serif date title);
  - status chips on the main stories: OFFICIAL / CLAIM / REPORTED, with the
    legend in the footer (rank1's status legend);
  - WHY IT MATTERS strip replaces THE DAY IN EIGHT: the eight repeated
    mini-scenes were the most template/AI-looking element on the page;
  - DATE CHECK box gains a NOT YET line (rank1): Iowa detonation and Hera
    images had not happened by the wires cut and are not reported as news;
  - numbers band supports explicit line breaks, so the KOSPI label no
    longer orphans "Jan" on its own line; the band's last figure is the
    corrected PCE 3.8% instead of the Australia CPI 4.9%;
  - a podium scene for speech/apology cards, so fewer medium cards fall
    back to the generic document tile.

Usage:
    python3 render.py [--input stories.json] [--geo land-110m.geojson]
                      [--output entry.png]
"""

import argparse
import json
import math
import os
import re
import sys

from PIL import Image, ImageDraw, ImageFont

W, H = 1024, 1024
PAPER = (246, 241, 231)
INK = (26, 26, 26)
MUTED = (107, 98, 87)
FAINT = (185, 173, 151)
RED = (179, 35, 27)
NAVY = (26, 38, 66)
LAND = (227, 216, 189)
LAND_EDGE = (138, 127, 99)
PANEL = (238, 231, 214)
SKY = (214, 226, 232)
CONFIRMED_TEAL = (0, 120, 110)

FIELD_STRIP_COLORS = {
    # v8.2 (G4): medium-card data strips are coloured by field
    # (sunny-fox's full-width strips): red for violence, navy for
    # statecraft and money, gold for the rest.
    "War": RED, "Disaster": RED, "Crime": RED,
    "Diplomacy": NAVY, "Justice": NAVY, "Politics": NAVY,
    "Security": NAVY, "Markets": NAVY, "Economy": NAVY,
    "Trade": NAVY, "Business": NAVY,
    "Tech": (178, 106, 0), "Science": (178, 106, 0),
    "Space": (178, 106, 0), "Culture": (178, 106, 0),
    "Society": (178, 106, 0), "Rights": (178, 106, 0),
    "Labour": (178, 106, 0), "Energy": (178, 106, 0),
    "Environment": (178, 106, 0),
}

REGION_COLORS = {
    "N. AMERICA": (107, 63, 160),
    "LATIN AMERICA": (196, 84, 32),
    "EUROPE": (46, 107, 52),
    "MIDDLE EAST": (163, 31, 22),
    "N. AFRICA": (178, 106, 0),
    "SUB-SAH. AFRICA": (120, 84, 50),
    "SOUTH ASIA": (180, 50, 110),
    "E. & SE ASIA": (31, 78, 121),
    "OCEANIA": (15, 118, 110),
    "GLOBAL": (58, 58, 96),
}

# Timeline points whose times were disproved by the fact-check pass
# (VERIFICATION.md): the 03:00 interview item was published 24 Nov and the
# 05:56 Senate item sat on 24 Nov. They are dropped from the axis even when
# present in stand-in data; a corrected draft simply will not contain them.
BAD_TIMES = {"03:00", "05:56"}

FONT_DIRS = [
    "/usr/share/fonts/truetype/noto",
    "/usr/share/fonts/truetype/dejavu",
    "/usr/share/fonts/truetype/liberation",
]


def font(names, size):
    for name in names:
        for d in FONT_DIRS:
            p = os.path.join(d, name)
            if os.path.exists(p):
                return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def f_display(size):
    return font(["NotoSerifDisplay-Black.ttf", "DejaVuSerif-Bold.ttf"], size)


def f_serif(size, bold=False, italic=False):
    if bold and italic:
        names = ["NotoSerif-BoldItalic.ttf", "LiberationSerif-BoldItalic.ttf"]
    elif bold:
        names = ["NotoSerif-Bold.ttf", "LiberationSerif-Bold.ttf"]
    elif italic:
        names = ["NotoSerif-Italic.ttf", "LiberationSerif-Italic.ttf"]
    else:
        names = ["NotoSerif-Regular.ttf", "LiberationSerif-Regular.ttf"]
    return font(names, size)


def f_sans(size, bold=False, italic=False):
    if bold and italic:
        names = ["NotoSans-BoldItalic.ttf", "LiberationSans-BoldItalic.ttf"]
    elif bold:
        names = ["NotoSans-Bold.ttf", "LiberationSans-Bold.ttf"]
    elif italic:
        names = ["NotoSans-Italic.ttf", "LiberationSans-Italic.ttf"]
    else:
        names = ["NotoSans-Regular.ttf", "LiberationSans-Regular.ttf"]
    return font(names, size)


def text_w(f, s):
    return f.getbbox(s)[2]


def wrap(draw, s, f, width):
    """Greedy word wrap; returns a list of lines that fit `width`."""
    lines, cur = [], ""
    for word in s.split():
        trial = (cur + " " + word).strip()
        if text_w(f, trial) <= width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def draw_wrapped(draw, x, y, s, f, fill, width, leading=None):
    if leading is None:
        leading = int(f.size * 1.22)
    for line in wrap(draw, s, f, width):
        draw.text((x, y), line, font=f, fill=fill)
        y += leading
    return y


def hline(draw, x0, x1, y, fill=INK, width=1):
    draw.line([(x0, y), (x1, y)], fill=fill, width=width)


def status_chip(draw, x, y, status):
    """OFFICIAL / CLAIM / REPORTED / CONFIRMED status chip.

    OFFICIAL = government data or an official statement.
    CLAIM = one party's claim, not independently confirmed.
    REPORTED = outlet reporting.
    CONFIRMED = official record, or 2+ major outlets agreeing.
    """
    label = (status or "REPORTED").upper()
    f = f_sans(9, bold=True)
    w = text_w(f, label) + 12
    fill = {"OFFICIAL": NAVY, "CLAIM": (178, 106, 0),
            "REPORTED": (46, 107, 52),
            "CONFIRMED": CONFIRMED_TEAL}.get(label, (46, 107, 52))
    draw.rounded_rectangle([x, y, x + w, y + 14], radius=3, fill=fill)
    draw.text((x + 6, y + 2), label, font=f, fill=(255, 255, 255))
    return w


def hhmm_of(t):
    """Normalise a story's time_utc to 'HH:MM' or ''.

    Accepts 'HH:MM' and ISO stamps ('2026-11-25T13:30:00Z'); 'n/a'
    and anything else mean the story carries no usable clock time.
    """
    if not t:
        return ""
    m = re.fullmatch(r"(\d{1,2}):(\d{2})", t)
    if m:
        return f"{int(m.group(1)):02d}:{m.group(2)}"
    m = re.search(r"T(\d{2}):(\d{2})", t)
    if m:
        return f"{m.group(1)}:{m.group(2)}"
    return ""


def is_pinned(story):
    """A story gets a map pin only when it carries real coordinates.
    lat 0 / lon 0 is the null-island sentinel for placeless items
    (e.g. the asteroid story) and is skipped, not plotted in the sea."""
    return ("lat" in story and "lon" in story
            and not (story["lat"] == 0 and story["lon"] == 0))


def kind_of(story):
    """Pick a pictorial kind from the story's own art tag or keywords.

    Keyword matching is word-boundary based: substring matching put the
    wrong picture on several stories ("supermarket" read as a market
    chart, "Metropolitan" read as the Metro, "searched" read as the sea,
    "Wang Fuk Court" read as a courtroom).
    """
    art = (story.get("art") or "").lower()
    if art in ("tower", "treaty", "rocket", "port", "train", "flag",
               "chart", "rise", "gavel", "blast", "smoke", "summit",
               "document", "podium", "shaft", "ship", "market", "shop",
               "bill", "fire", "power"):
        return art
    blob = ((story.get("headline") or "") + " " +
            (story.get("body") or "")).lower()

    def has(*pats):
        return any(re.search(p, blob) for p in pats)

    if has(r"\blaunch(ed|es|ing)?\b", r"\bspace\b", r"\brocket\b",
           r"\borbit\b"):
        return "rocket"
    if has(r"\bmetro\b", r"\bsubway\b", r"\btrain\b", r"\brail\b"):
        return "train"
    if has(r"\bshares?\b", r"\bstocks?\b", r"\bmarket\b", r"\bfalls?\b",
           r"\bslides?\b", r"\bindex\b", r"\bkospi\b", r"\bnvidia\b",
           r"\bwage(s)?\b", r"\bpay\b", r"\braise(s|d)?\b"):
        return "chart"
    if has(r"\bjudge\b", r"\bguilty\b", r"\bplead(ed|s|ing)?\b",
           r"\bverdict\b", r"\bsentenc(e|ed|es|ing)?\b", r"\btrial\b",
           r"\bseize(s|d)?\b", r"\bcustoms\b", r"\barrest(s|ed)?\b"):
        return "gavel"
    if has(r"\bexpel(led|s|ling)?\b", r"\benvoy\b", r"\bdiplomat(ic)?\b",
           r"\bembassy\b"):
        return "flag"
    if has(r"\bport\b", r"\bship\b", r"\bsea\b", r"\bharbour\b",
           r"\bharbor\b"):
        return "port"
    if has(r"\btreaty\b", r"\bpact\b", r"\bsign(ed|s|ing)?\b", r"\bdeal\b",
           r"\bagreement\b"):
        return "treaty"
    if has(r"\bsummit\b", r"\bleaders?\b", r"\bhosts?\b", r"\bpresident\b",
           r"\bprime minister\b"):
        return "summit"
    # Memorials and anniversaries are features, not fresh violence:
    # the Tai Po piece mourns a year-old fire, so it gets the neutral
    # document picture even though its body mentions the dead.
    if has(r"\banniversar(y|ies)\b", r"\bmourn(s|ed|ing)?\b",
           r"\bsurvivors?\b"):
        return "document"
    if has(r"\bdrones?\b"):
        return "smoke"
    if has(r"\bmine(s|rs)?\b", r"\btrapped\b", r"\bflooded\b"):
        return "shaft"
    if has(r"\bstrike\b", r"\battack(ed|s|ing)?\b", r"\bblast\b",
           r"\bbomb\b", r"\bkills?\b", r"\bkilled\b", r"\bhit\b",
           r"\bhits\b"):
        return "blast"
    return "document"


# ---------------------------------------------------------------- scenes
# Each painter fills a (x, y, w, h) box with a flat vector scene.

def _sky(draw, x, y, w, h, top=(198, 214, 224), bot=(232, 228, 210)):
    for i in range(h):
        t = i / max(1, h - 1)
        c = tuple(int(top[j] + (bot[j] - top[j]) * t) for j in range(3))
        draw.line([(x, y + i), (x + w, y + i)], fill=c)


def _building(draw, x, y, w, h, fill=(58, 58, 60)):
    draw.rectangle([x, y, x + w, y + h], fill=fill)
    for wy in range(y + 6, y + h - 6, 10):
        for wx in range(x + 4, x + w - 4, 9):
            draw.rectangle([wx, wy, wx + 4, wy + 5], fill=(240, 220, 130))


def scene_tower(draw, x, y, w, h):
    # Riyadh skyline, sized for the 34px medium tile: every roofline
    # stays inside the tile, and a small intercepted drone with a
    # red burst reads the "four drones intercepted" line.
    _sky(draw, x, y, w, h)
    gy = y + h - 4
    draw.line([(x, gy), (x + w, gy)], fill=(90, 86, 78), width=1)
    _building(draw, x + 3, y + h - 20, 22, 20, fill=(58, 58, 60))
    _building(draw, x + w - 56, y + h - 24, 24, 24, fill=(70, 66, 60))
    _building(draw, x + w - 27, y + h - 16, 22, 16, fill=(58, 58, 60))
    tx = x + w // 2 - 8
    draw.rectangle([tx, y + 5, tx + 16, gy], fill=(38, 38, 40))
    draw.polygon([(tx - 2, y + 5), (tx + 18, y + 5), (tx + 8, y + 1)],
                 fill=(38, 38, 40))
    for wy in range(y + 11, gy - 4, 7):
        draw.rectangle([tx + 3, wy, tx + 13, wy + 3], fill=(240, 220, 130))
    # intercepted drone, upper left sky: dark body, rotor bars, and
    # a red burst where it was hit
    dx, dy = x + 52, y + 7
    draw.ellipse([dx - 3, dy - 2, dx + 3, dy + 2], fill=(30, 30, 32))
    draw.line([(dx - 7, dy - 4), (dx + 7, dy - 4)], fill=(30, 30, 32),
              width=1)
    draw.line([(dx - 7, dy + 4), (dx + 7, dy + 4)], fill=(30, 30, 32),
              width=1)
    bx, by = dx - 14, dy + 4
    for ang in range(0, 360, 45):
        r = 5
        ex = bx + int(r * math.cos(math.radians(ang)))
        ey = by + int(r * math.sin(math.radians(ang)))
        draw.line([(bx, by), (ex, ey)], fill=RED, width=1)
    draw.ellipse([bx - 2, by - 2, bx + 2, by + 2], fill=RED)


def scene_treaty(draw, x, y, w, h):
    # pact document on a table, sized for the 34px tile: the sheet
    # now has a real height (the v8 version degenerated to zero
    # height when the tile shrank to 36px), with a second sheet
    # behind it, a red wax seal and two flags.
    _sky(draw, x, y, w, h, top=(222, 230, 214), bot=(240, 236, 218))
    draw.rectangle([x, y + h - 6, x + w, y + h], fill=(120, 92, 60))
    dw, dh = w // 2, h - 13
    dx, dy = x + w // 2 - dw // 2, y + 3
    draw.rectangle([dx - 3, dy - 1, dx + dw - 3, dy + dh - 1],
                   fill=(226, 226, 220), outline=(150, 150, 148), width=1)
    draw.rectangle([dx, dy, dx + dw, dy + dh], fill=(255, 255, 255),
                   outline=INK, width=1)
    for i in range(3):
        ly = dy + 6 + i * 5
        draw.line([(dx + 6, ly), (dx + dw - 6, ly)], fill=(150, 150, 150),
                  width=1)
    sx, sy = dx + dw - 11, dy + dh - 6
    draw.ellipse([sx - 4, sy - 4, sx + 4, sy + 4], fill=RED,
                 outline=(120, 20, 12))
    draw.polygon([(sx - 3, sy + 3), (sx + 1, sy + 3), (sx - 1, sy + 8)],
                 fill=RED)
    draw.polygon([(sx + 1, sy + 3), (sx + 4, sy + 3), (sx + 3, sy + 8)],
                 fill=RED)
    for fx, fc in ((x + 7, (31, 78, 121)), (x + w - 23, (46, 107, 52))):
        draw.line([(fx + 8, y + 4), (fx + 8, y + h - 6)], fill=INK, width=2)
        draw.ellipse([fx + 6, y + 2, fx + 10, y + 6], fill=(240, 200, 40))
        draw.polygon([(fx + 8, y + 4), (fx + 22, y + 9), (fx + 8, y + 14)],
                     fill=fc)


def scene_rocket(draw, x, y, w, h):
    # rescaled for the 60px main scene: the v8 painter still drew
    # to 72px, so the fins and flame were clipped by the tile edge.
    # A launch gantry fills the wide tile beside the rocket.
    draw.rectangle([x, y, x + w, y + h], fill=(24, 34, 58))
    for sx, sy in ((x + 12, y + 8), (x + w - 16, y + 14),
                   (x + w // 2, y + 6), (x + 20, y + h - 14),
                   (x + w - 26, y + h - 22), (x + w // 4, y + 20),
                   (x + 3 * w // 4, y + 30)):
        draw.ellipse([sx - 2, sy - 2, sx + 2, sy + 2], fill=(255, 255, 255))
    cx = x + w // 2
    gx = cx - 52
    draw.rectangle([gx, y + 8, gx + 8, y + h - 4], fill=(52, 58, 72))
    for ay in (y + 16, y + 28, y + 40):
        draw.line([(gx + 8, ay), (gx + 26, ay)], fill=(90, 96, 110), width=2)
    draw.line([(x, y + h - 4), (x + w, y + h - 4)], fill=(90, 96, 110),
              width=1)
    # v8.2 (G2): a bigger rocket (wider body, wider flame) -- the
    # 60px tile had a lot of empty dark sky around the old one
    draw.polygon([(cx, y + 3), (cx - 13, y + 22), (cx + 13, y + 22)],
                 fill=RED)
    draw.rectangle([cx - 13, y + 22, cx + 13, y + 42], fill=(240, 240, 235))
    draw.ellipse([cx - 5, y + 28, cx + 5, y + 36], fill=(31, 78, 121))
    draw.polygon([(cx - 13, y + 36), (cx - 23, y + 48), (cx - 13, y + 44)],
                 fill=RED)
    draw.polygon([(cx + 13, y + 36), (cx + 23, y + 48), (cx + 13, y + 44)],
                 fill=RED)
    draw.polygon([(cx - 7, y + 42), (cx + 7, y + 42), (cx, y + 57)],
                 fill=(240, 160, 40))
    draw.polygon([(cx - 4, y + 42), (cx + 4, y + 42), (cx, y + 52)],
                 fill=(240, 200, 40))
    draw.ellipse([cx - 20, y + 50, cx - 8, y + 56], fill=(200, 200, 200))
    draw.ellipse([cx + 8, y + 50, cx + 20, y + 56], fill=(180, 180, 180))
    # launch-time chip, top right so it never collides with the
    # red FIRST PAKISTANI banner the main column paints top left
    f_clk = f_sans(9, bold=True)
    clk = "00:18 UTC"
    cw = text_w(f_clk, clk) + 12
    draw.rectangle([x + w - cw - 6, y + 3, x + w - 6, y + 16],
                   outline=(255, 255, 255), width=1)
    draw.text((x + w - cw, y + 5), clk, font=f_clk, fill=(255, 255, 255))


def scene_blast(draw, x, y, w, h):
    # strike on a port, sized for the 34px tile: the burst radius
    # now fits inside the tile (v8 clipped it top and bottom),
    # container stacks at both edges read "port", with smoke and
    # rubble on the ground.
    _sky(draw, x, y, w, h, top=(230, 202, 172), bot=(242, 232, 208))
    gy = y + h - 4
    draw.line([(x, gy), (x + w, gy)], fill=(90, 86, 78), width=1)
    for sx, col in ((x + 4, (163, 31, 22)), (x + 18, (31, 78, 121)),
                    (x + w - 32, (196, 160, 40)), (x + w - 18, (163, 31, 22))):
        draw.rectangle([sx, gy - 12, sx + 12, gy - 6], fill=col,
                       outline=(255, 255, 255), width=1)
        draw.rectangle([sx, gy - 6, sx + 12, gy], fill=col,
                       outline=(255, 255, 255), width=1)
    cx, cy = x + w // 2, y + h // 2 + 1
    for ang in range(0, 360, 30):
        r = 11
        ex = cx + int(r * math.cos(math.radians(ang)))
        ey = cy + int(r * math.sin(math.radians(ang)))
        draw.line([(cx, cy), (ex, ey)], fill=(240, 160, 40), width=2)
    draw.ellipse([cx - 8, cy - 8, cx + 8, cy + 8], fill=(240, 120, 30))
    draw.ellipse([cx - 4, cy - 4, cx + 4, cy + 4], fill=RED)
    for px, py, d in ((x + w // 4, y + 3, 9), (x + 3 * w // 4, y + 5, 8)):
        draw.ellipse([px - d // 2, py, px + d // 2, py + d],
                     fill=(150, 148, 142))
    for rx, ry in ((cx - 16, gy - 2), (cx + 14, gy - 3), (cx + 22, gy - 2)):
        draw.rectangle([rx, ry, rx + 3, ry + 2], fill=(70, 66, 60))


def scene_smoke(draw, x, y, w, h):
    # strike aftermath: rooftops with rising smoke columns, a small
    # flame on the centre roof and rubble at the foot.
    _sky(draw, x, y, w, h, top=(206, 198, 186), bot=(236, 230, 214))
    gy = y + h - 4
    gx = x + w // 2
    draw.line([(x, gy), (x + w, gy)], fill=(90, 86, 78), width=1)
    for bx, bh in ((x + 4, 16), (x + w // 2 - 14, 20), (x + w - 30, 14)):
        _building(draw, bx, gy - bh, 26, bh, fill=(70, 66, 60))
    for px, py, d in ((x + 18, y + 4, 12), (gx, y + 2, 14),
                      (x + w - 18, y + 6, 10), (gx + 24, y + 10, 8)):
        draw.ellipse([px - d // 2, py, px + d // 2, py + d],
                     fill=(150, 148, 142))
    draw.polygon([(gx - 5, gy - 20), (gx, gy - 27), (gx + 5, gy - 20)],
                 fill=(240, 160, 40))
    draw.polygon([(gx - 2, gy - 20), (gx, gy - 25), (gx + 2, gy - 20)],
                 fill=(240, 200, 40))
    for dx2, dy2 in ((x + w // 4, gy - 2), (x + 3 * w // 4, gy - 3)):
        draw.rectangle([dx2, dy2, dx2 + 3, dy2 + 2], fill=(70, 66, 60))


def scene_chart(draw, x, y, w, h):
    # falling bars with a clearly falling red trend line: the v8
    # line dropped less than a pixel over the tile width and read
    # as horizontal, and the bars were only 6px tall.
    draw.rectangle([x, y, x + w, y + h], fill=(238, 236, 228))
    base = y + h - 6
    vals = [0.75, 0.6, 0.68, 0.45, 0.5, 0.28]
    bw = (w - 16) // len(vals)
    for i, v in enumerate(vals):
        bx = x + 8 + i * bw
        bh = int((h - 14) * v)
        draw.rectangle([bx, base - bh, bx + bw - 4, base], fill=(31, 78, 121))
    draw.line([(x + 6, y + 6), (x + w - 6, base - 2)], fill=RED, width=3)
    draw.polygon([(x + w - 16, base - 8), (x + w - 4, base - 2),
                  (x + w - 16, base + 2)], fill=RED)


def scene_rise(draw, x, y, w, h):
    # rising data: ascending bars with a red arrow climbing to the
    # top right, for inflation / GDP growth cards (the v8 falling
    # chart pointed the wrong way for both).
    draw.rectangle([x, y, x + w, y + h], fill=(238, 236, 228))
    base = y + h - 6
    vals = [0.25, 0.38, 0.45, 0.58, 0.68, 0.8]
    bw = (w - 16) // len(vals)
    for i, v in enumerate(vals):
        bx = x + 8 + i * bw
        bh = int((h - 14) * v)
        draw.rectangle([bx, base - bh, bx + bw - 4, base], fill=(31, 78, 121))
    draw.line([(x + 6, base - 2), (x + w - 6, y + 6)], fill=RED, width=3)
    draw.polygon([(x + w - 16, y + 2), (x + w - 4, y + 6),
                  (x + w - 16, y + 10)], fill=RED)


def scene_train(draw, x, y, w, h):
    _sky(draw, x, y, w, h, top=(210, 222, 228), bot=(240, 236, 220))
    draw.rectangle([x, y + h - 10, x + w, y + h], fill=(90, 86, 78))
    draw.rounded_rectangle([x + 8, y + 14, x + w - 8, y + h - 18], radius=8,
                           fill=(31, 78, 121))
    win_w, gap = int(w * 0.22), int(w * 0.08)
    for i in range(3):
        wx = x + int(w * 0.12) + i * (win_w + gap)
        draw.rectangle([wx, y + 24, wx + win_w, y + 40],
                       fill=(214, 226, 232))
    draw.line([(x + 8, y + h - 22), (x + w - 8, y + h - 22)], fill=INK,
              width=2)


def scene_flag(draw, x, y, w, h):
    _sky(draw, x, y, w, h)
    draw.line([(x + w // 2, y + 8), (x + w // 2, y + h - 8)], fill=INK,
              width=2)
    draw.polygon([(x + w // 2, y + 8), (x + w - 10, y + 16),
                  (x + w // 2, y + 24)], fill=RED)
    draw.rectangle([x + 8, y + h - 12, x + w - 8, y + h - 8], fill=(90, 86, 78))


def scene_gavel(draw, x, y, w, h):
    # courtroom gavel, sized for the 34px tile: a large head with
    # end caps and a highlight, a diagonal handle down to the
    # sound block on the bench, and a red seal. The v8 version
    # read as two brown bars.
    draw.rectangle([x, y, x + w, y + h], fill=(238, 236, 228))
    draw.rectangle([x, y + h - 6, x + w, y + h], fill=(120, 92, 60))
    cx = x + w // 2
    draw.rectangle([cx - 50, y + 20, cx - 16, y + 27], fill=(120, 92, 60),
                   outline=(90, 66, 40), width=1)
    draw.line([(cx + 2, y + 12), (cx + 36, y + 26)], fill=(120, 92, 60),
              width=5)
    draw.rectangle([cx - 48, y + 6, cx + 6, y + 16], fill=(90, 66, 40))
    draw.rectangle([cx - 48, y + 6, cx + 6, y + 9], fill=(120, 92, 60))
    draw.rectangle([cx - 52, y + 5, cx - 48, y + 17], fill=(70, 50, 30))
    draw.rectangle([cx + 2, y + 5, cx + 6, y + 17], fill=(70, 50, 30))
    draw.ellipse([x + w - 16, y + 4, x + w - 8, y + 12], fill=RED,
                 outline=(120, 20, 12))


def scene_summit(draw, x, y, w, h):
    _sky(draw, x, y, w, h, top=(222, 228, 220), bot=(240, 236, 218))
    draw.rectangle([x, y + h - 18, x + w, y + h], fill=(120, 92, 60))
    pw = max(10, w // 3 - 6)
    for i in range(3):
        bx = x + 3 + i * (w // 3)
        cx = bx + pw // 2
        draw.ellipse([cx - 6, y + 14, cx + 6, y + 26], fill=(240, 210, 170))
        draw.polygon([(bx, y + h - 18), (cx - 6, y + 26),
                      (cx + 6, y + 26), (bx + pw, y + h - 18)],
                     fill=((31, 78, 121), (46, 107, 52), (107, 63, 160))[i])


def scene_port(draw, x, y, w, h):
    draw.rectangle([x, y, x + w, y + h], fill=(214, 226, 232))
    draw.rectangle([x, y + h // 2 + 6, x + w, y + h], fill=(70, 110, 140))
    draw.polygon([(x + w // 2 - 16, y + h // 2 + 6),
                  (x + w // 2 + 16, y + h // 2 + 6),
                  (x + w // 2, y + 12)], fill=(240, 240, 235))
    draw.line([(x + w // 2, y + 12), (x + w // 2, y + h // 2 + 6)], fill=INK,
              width=2)
    draw.rectangle([x + 8, y + h // 2 + 2, x + w - 8, y + h // 2 + 16],
                   fill=(140, 60, 40))
    for i in range(3):
        draw.rectangle([x + 16 + i * 14, y + h // 2 + 6, x + 24 + i * 14,
                        y + h // 2 + 12], fill=(240, 220, 130))



def scene_shaft(draw, x, y, w, h):
    # earth strata with speckles, a wider lit mine shaft with
    # ladder rungs and a helmet lamp beam, rubble at the foot.
    for i, c in enumerate(((170, 138, 92), (200, 172, 124), (160, 128, 84))):
        draw.rectangle([x, y + i * (h // 3), x + w, y + (i + 1) * (h // 3)],
                       fill=c)
    for sx, sy in ((x + 12, y + 5), (x + 30, y + 16), (x + 48, y + 8),
                   (x + w - 52, y + 6), (x + w - 30, y + 18),
                   (x + w - 12, y + 9), (x + 66, y + 24),
                   (x + w - 66, y + 26)):
        draw.ellipse([sx, sy, sx + 3, sy + 2], fill=(120, 96, 62))
    sx = x + w // 2 - 11
    draw.rectangle([sx, y + 3, sx + 22, y + h - 3], fill=(48, 40, 32))
    for ry in range(y + 10, y + h - 6, 7):
        draw.line([(sx + 3, ry), (sx + 19, ry)], fill=(200, 172, 124),
                  width=2)
    draw.ellipse([x + w // 2 - 4, y + 5, x + w // 2 + 4, y + 13],
                 fill=(240, 200, 60))
    draw.polygon([(x + w // 2 - 3, y + 13), (x + w // 2 + 3, y + 13),
                  (x + w // 2 + 7, y + 24), (x + w // 2 - 7, y + 24)],
                 fill=(250, 226, 140))
    for rx, ry in ((sx - 8, y + h - 6), (sx + 24, y + h - 5),
                   (sx + 30, y + h - 7)):
        draw.polygon([(rx, ry), (rx + 5, ry), (rx + 2, ry - 4)],
                     fill=(90, 72, 48))


def scene_podium(draw, x, y, w, h):
    # a speaker at a lectern: for apologies, reviews and announcements,
    # so those cards stop falling back to the generic document tile
    _sky(draw, x, y, w, h, top=(222, 226, 220), bot=(240, 236, 218))
    cx = x + w // 2
    draw.ellipse([cx - 6, y + 10, cx + 6, y + 22], fill=(240, 210, 170))
    draw.polygon([(cx - 12, y + h - 14), (cx - 6, y + 22),
                  (cx + 6, y + 22), (cx + 12, y + h - 14)],
                 fill=(31, 78, 121))
    draw.rectangle([x + 6, y + h - 22, x + w - 6, y + h - 10],
                   fill=(120, 92, 60))
    draw.line([(cx + 10, y + h - 22), (cx + 18, y + h - 30)], fill=INK,
              width=2)
    draw.ellipse([cx + 16, y + h - 34, cx + 20, y + h - 30], fill=INK)


def scene_document(draw, x, y, w, h):
    draw.rectangle([x, y, x + w, y + h], fill=(238, 236, 228))
    dw, dh = w - 24, h - 16
    dx, dy = x + 12, y + 8
    draw.rectangle([dx, dy, dx + dw, dy + dh], fill=(255, 255, 255),
                   outline=INK, width=1)
    for i in range(4):
        draw.line([(dx + 8, dy + 10 + i * 7), (dx + dw - 8, dy + 10 + i * 7)],
                  fill=(150, 150, 150), width=1)
    draw.ellipse([dx + dw - 18, dy + dh - 16, dx + dw - 6, dy + dh - 4],
                 fill=RED)


def scene_ship(draw, x, y, w, h):
    # container ship at sea, for the tariff story: stacked boxes on a
    # hull under a pale sky; sized for the 60px main scene
    _sky(draw, x, y, w, h, top=(214, 226, 232), bot=(240, 236, 220))
    sea = y + h // 2 + 8
    draw.rectangle([x, sea, x + w, y + h], fill=(70, 110, 140))
    # a small distant ship on the horizon, behind the main hull
    draw.rectangle([x + 22, sea - 10, x + 52, sea - 6], fill=(52, 66, 80))
    draw.rectangle([x + 30, sea - 16, x + 38, sea - 10], fill=(52, 66, 80))
    for i in range(3):
        draw.line([(x + 8 + i * 24, sea + 8), (x + w - 8 - i * 18, sea + 8)],
                  fill=(200, 220, 230), width=1)
    draw.line([(x + 8, sea + 14), (x + w - 8, sea + 14)],
              fill=(200, 220, 230), width=1)
    # hull: a long dark trapezoid
    draw.polygon([(x + 10, sea - 2), (x + w - 10, sea - 2),
                  (x + w - 34, y + h - 6), (x + 34, y + h - 6)],
                 fill=(40, 44, 52))
    # four stacks of containers above the deck, one per tariff rate
    # (Vietnam 35%, India 25%, China 20%, EU 15% -- USTR release):
    # the rate is painted on the top box of each stack, white on the
    # dark boxes and ink on the gold one, so the key numbers sit
    # inside the picture instead of only in the body text.
    rates = [("VN 35%", (163, 31, 22)), ("IN 25%", (31, 78, 121)),
             ("CN 20%", (196, 160, 40)), ("EU 15%", (46, 107, 52))]
    f_rate = f_sans(8, bold=True)
    for s, (rate, col) in enumerate(rates):
        sx = x + w // 2 - 80 + s * 40
        for r in range(2):
            draw.rectangle([sx, sea - 26 + r * 13, sx + 36,
                            sea - 14 + r * 13], fill=col,
                           outline=(255, 255, 255), width=1)
        tw = text_w(f_rate, rate)
        ink = INK if col == (196, 160, 40) else (255, 255, 255)
        draw.text((sx + (36 - tw) // 2, sea - 24), rate, font=f_rate,
                  fill=ink)
    # bridge tower at the stern; its top now sits 1px inside the
    # tile (v8 put it 3px above the tile edge and the frame cut it)
    draw.rectangle([x + w - 52, sea - 36, x + w - 34, sea - 2],
                   fill=(240, 240, 235))
    draw.rectangle([x + w - 52, sea - 36, x + w - 34, sea - 30],
                   fill=(31, 78, 121))


def scene_market(draw, x, y, w, h):
    # dark trading screen with a falling red line: the KOSPI rout
    draw.rectangle([x, y, x + w, y + h], fill=(18, 28, 52))
    for gy in range(y + 8, y + h - 4, 12):
        draw.line([(x + 4, gy), (x + w - 4, gy)], fill=(38, 52, 84), width=1)
    pts = [(x + 10, y + 16), (x + w * 0.3, y + 20), (x + w * 0.5, y + 30),
           (x + w * 0.7, y + 34), (x + w - 12, y + h - 10)]
    draw.line(pts, fill=(240, 60, 40), width=3)
    for px, py in pts:
        draw.ellipse([px - 3, py - 3, px + 3, py + 3], fill=(255, 255, 255))
    # in-scene data labels (verified): the two chip stocks across
    # the top, the close level with the KOSPI label at the bottom
    f_top = f_sans(9, bold=True)
    parts = [("SK HYNIX ", (255, 255, 255)), ("-11.1%", (255, 90, 70)),
             ("    SAMSUNG ", (255, 255, 255)), ("-9.9%", (255, 90, 70))]
    tw = sum(text_w(f_top, t) for t, _ in parts)
    tx = x + w // 2 - tw // 2
    for t, c in parts:
        draw.text((tx, y + 3), t, font=f_top, fill=c)
        tx += text_w(f_top, t)
    f_lab = f_sans(11, bold=True)
    draw.text((x + 10, y + h - 18), "KOSPI -6.2% · 4,697.51",
              font=f_lab, fill=(255, 255, 255))


def scene_shop(draw, x, y, w, h):
    # supermarket front, sized for the 34px tile: striped awning,
    # a glass door with a handle, and two windows with goods on
    # the shelves. The v8 windows were 4px slits with nothing in them.
    draw.rectangle([x, y, x + w, y + h], fill=(232, 226, 206))
    n = 6
    sw = (w - 8) // n
    for i in range(n):
        c = (163, 31, 22) if i % 2 == 0 else (245, 240, 228)
        ax = x + 4 + i * sw
        draw.polygon([(ax, y + 3), (ax + sw, y + 3), (ax + sw, y + 11),
                      (ax, y + 11)], fill=c)
    draw.rectangle([x + 4, y + 11, x + w - 4, y + h - 3], fill=(240, 236, 222),
                   outline=INK, width=1)
    dw = max(16, w // 4)
    door_x0, door_x1 = x + w // 2 - dw // 2, x + w // 2 + dw // 2
    draw.rectangle([door_x0, y + 14, door_x1, y + h - 3],
                   fill=(120, 170, 200), outline=INK, width=1)
    draw.line([(door_x0, y + h // 2 + 4), (door_x1, y + h // 2 + 4)],
              fill=INK, width=1)
    draw.ellipse([door_x1 - 5, y + h // 2 + 1, door_x1 - 2, y + h // 2 + 4],
                 fill=INK)
    for wx0, wx1 in ((x + 8, door_x0 - 5), (door_x1 + 5, x + w - 8)):
        draw.rectangle([wx0, y + 14, wx1, y + h - 6], fill=(180, 210, 225),
                       outline=INK, width=1)
        draw.line([(wx0, y + h - 11), (wx1, y + h - 11)], fill=INK, width=1)
        for j, gc in enumerate(((163, 31, 22), (31, 78, 121),
                                (196, 160, 40))):
            gx2 = wx0 + 4 + j * 11
            draw.rectangle([gx2, y + h - 17, gx2 + 7, y + h - 11], fill=gc)
    draw.line([(x, y + h - 3), (x + w, y + h - 3)], fill=(90, 86, 78),
              width=1)


def scene_bill(draw, x, y, w, h):
    # an energy bill: white paper on a second sheet, red header
    # band, a lightning bolt and a small coin stack. The v8 bolt
    # ran 2px past the tile bottom.
    draw.rectangle([x, y, x + w, y + h], fill=(214, 208, 188))
    px, py, pw, ph = x + 8, y + 4, w - 16, h - 8
    draw.rectangle([px + 4, py + 3, px + pw + 4, py + ph + 3],
                   fill=(200, 194, 172), outline=(150, 142, 122), width=1)
    draw.rectangle([px, py, px + pw, py + ph], fill=(255, 255, 255),
                   outline=INK, width=1)
    draw.rectangle([px, py, px + pw, py + 8], fill=RED)
    for i in range(3):
        draw.line([(px + 26, py + 15 + i * 5),
                   (px + pw - 26, py + 15 + i * 5)], fill=(150, 150, 150),
                  width=1)
    bx = px + pw - 18
    draw.polygon([(bx + 6, py + 11), (bx - 2, py + 22), (bx + 4, py + 22),
                  (bx - 2, py + 29), (bx + 8, py + 17), (bx + 2, py + 17)],
                 fill=(240, 200, 40))
    for i in range(3):
        cx2 = px + 12 + i * 2
        draw.ellipse([cx2 - 4, py + ph - 8 - i * 3, cx2 + 4, py + ph - 2 - i * 3],
                     fill=(240, 200, 40), outline=(178, 140, 20))


def scene_fire(draw, x, y, w, h):
    # a tanker truck in flames on a road, for the Cairo fire
    draw.rectangle([x, y, x + w, y + h], fill=(52, 48, 46))
    for cx, py, d in ((x + w // 4, y + 2, 12), (x + w // 2, y + 6, 10),
                      (x + 3 * w // 4, y + 2, 12)):
        draw.ellipse([cx - d // 2, py, cx + d // 2, py + d],
                     fill=(120, 116, 110))
    cx = x + w // 2
    for ex, ey, er in ((cx - 26, y + 4, 2), (cx - 14, y + 2, 1),
                       (cx + 18, y + 3, 2), (cx + 28, y + 6, 1),
                       (cx + 6, y + 1, 1)):
        draw.ellipse([ex - er, ey - er, ex + er, ey + er],
                     fill=(240, 160, 40))
    # a wider flame, rooted on the tanker
    draw.polygon([(cx - 22, y + h - 12), (cx - 8, y + 4), (cx, y + 14),
                  (cx + 8, y + 2), (cx + 22, y + h - 12)], fill=(240, 120, 30))
    draw.polygon([(cx - 12, y + h - 12), (cx - 4, y + 12), (cx + 2, y + 18),
                  (cx + 10, y + 10), (cx + 12, y + h - 12)], fill=(240, 200, 40))
    draw.polygon([(cx - 6, y + h - 12), (cx - 2, y + 16), (cx + 2, y + 20),
                  (cx + 5, y + 15), (cx + 6, y + h - 12)],
                 fill=(250, 240, 200))
    # tanker: dark cylinder body on wheels, low in the frame
    ty = y + h - 14
    draw.rectangle([x + 10, ty - 8, x + w - 10, ty], fill=(40, 36, 34))
    draw.ellipse([x + 14, ty - 14, x + w - 30, ty - 6], fill=(96, 88, 82))
    draw.line([(x + 16, ty - 12), (x + w - 32, ty - 12)], fill=(150, 142, 134),
              width=1)
    draw.rectangle([x + w - 30, ty - 12, x + w - 12, ty - 6],
                   fill=(70, 64, 60))
    draw.ellipse([x + w - 16, ty - 10, x + w - 12, ty - 6],
                 fill=(250, 240, 180))
    for wx in (x + 24, x + w - 24):
        draw.ellipse([wx - 4, ty - 2, wx + 4, ty + 8], fill=INK)
    draw.rectangle([x, y + h - 6, x + w, y + h], fill=(30, 28, 26))
    for dx2 in range(x + 6, x + w - 6, 18):
        draw.line([(dx2, y + h - 3), (dx2 + 8, y + h - 3)],
                  fill=(220, 220, 210), width=1)


def scene_power(draw, x, y, w, h):
    # two transmission pylons against a dark sky, sagging lines
    # between them, a yellow spark, and a blacked-out city skyline
    # with two lit windows. The v8 spark ran to the tile bottom.
    draw.rectangle([x, y, x + w, y + h], fill=(38, 44, 62))
    for sx, sy in ((x + 10, y + 6), (x + w - 12, y + 10), (x + w // 2, y + 4)):
        draw.ellipse([sx - 1, sy - 1, sx + 1, sy + 1], fill=(255, 255, 255))
    cx = x + w // 2 - 18
    draw.line([(cx - 14, y + h - 6), (cx, y + 6)], fill=(200, 200, 200),
              width=2)
    draw.line([(cx + 14, y + h - 6), (cx, y + 6)], fill=(200, 200, 200),
              width=2)
    draw.line([(cx - 20, y + 12), (cx + 20, y + 12)], fill=(200, 200, 200),
              width=2)
    draw.line([(cx - 14, y + 20), (cx + 14, y + 20)], fill=(200, 200, 200),
              width=1)
    cx2 = x + w - 34
    draw.line([(cx2 - 9, y + h - 6), (cx2, y + 12)], fill=(180, 180, 180),
              width=2)
    draw.line([(cx2 + 9, y + h - 6), (cx2, y + 12)], fill=(180, 180, 180),
              width=2)
    draw.line([(cx2 - 13, y + 17), (cx2 + 13, y + 17)], fill=(180, 180, 180),
              width=1)
    for off in (13, 21):
        pts = []
        for t in range(5):
            fx = cx + 20 + (cx2 - 20 - (cx + 20)) * t / 4
            fy = y + off + int(4 * (1 - (2 * t / 4 - 1) ** 2))
            pts.append((fx, fy))
        draw.line(pts, fill=(160, 160, 160), width=1)
    draw.polygon([(cx + 24, y + 6), (cx + 16, y + 18), (cx + 21, y + 18),
                  (cx + 14, y + 28), (cx + 25, y + 15), (cx + 20, y + 15)],
                 fill=(240, 200, 40))
    for bx, bw, bh in ((x + 6, 18, 8), (x + 30, 14, 11), (x + w - 58, 20, 9),
                       (x + w - 24, 16, 12)):
        draw.rectangle([bx, y + h - 6 - bh, bx + bw, y + h - 6],
                       fill=(16, 18, 26))
    for wx, wy in ((x + 12, y + h - 12), (x + w - 50, y + h - 14)):
        draw.rectangle([wx, wy, wx + 2, wy + 3], fill=(240, 200, 40))
    draw.rectangle([x, y + h - 6, x + w, y + h], fill=(20, 24, 34))


SCENES = {
    "tower": scene_tower, "treaty": scene_treaty, "rocket": scene_rocket,
    "blast": scene_blast, "chart": scene_chart, "rise": scene_rise,
    "train": scene_train,
    "flag": scene_flag, "gavel": scene_gavel, "summit": scene_summit,
    "port": scene_port, "document": scene_document,
    "smoke": scene_smoke, "shaft": scene_shaft, "podium": scene_podium,
    "ship": scene_ship, "market": scene_market, "shop": scene_shop,
    "bill": scene_bill, "fire": scene_fire, "power": scene_power,
}


def draw_scene(img, kind, x, y, w, h):
    """Paint a scene into a tile and paste it, so no painter can draw
    outside its own box and into neighbouring text."""
    tile = Image.new("RGB", (w, h), PANEL)
    td = ImageDraw.Draw(tile)
    td.rectangle([0, 0, w - 1, h - 1], outline=INK, width=1)
    SCENES.get(kind, scene_document)(td, 1, 1, w - 2, h - 2)
    img.paste(tile, (x, y))


def draw_icon(img, kind, x, y, s):
    draw_scene(img, kind, x, y, s, s)


# ---------------------------------------------------------------- map

def project(lon, lat, mx, my, mw, mh):
    px = mx + (lon + 180.0) / 360.0 * mw
    py = my + (85.0 - min(lat, 85.0)) / 145.0 * mh
    return px, py


def draw_map(img, draw, geo, stories, mx, my, mw, mh):
    draw.rectangle([mx, my, mx + mw, my + mh], fill=(233, 227, 208),
                   outline=INK, width=1)
    for feat in geo.get("features", []):
        geom = feat.get("geometry") or {}
        polys = []
        if geom.get("type") == "Polygon":
            polys = [geom.get("coordinates", [])]
        elif geom.get("type") == "MultiPolygon":
            polys = geom.get("coordinates", [])
        for poly in polys:
            for ring in poly:
                pts = []
                for lon, lat in ring:
                    if lat < -58:
                        continue
                    pts.append(project(lon, lat, mx + 2, my + 2, mw - 4, mh - 4))
                if len(pts) > 2:
                    draw.polygon(pts, fill=LAND, outline=LAND_EDGE)
    # dotted land texture (bagarte's halftone map): stamp a dot on a
    # 6px grid wherever the pixel underneath is land
    for gx in range(mx + 4, mx + mw - 4, 6):
        for gy in range(my + 4, my + mh - 4, 6):
            if img.getpixel((gx, gy)) == LAND:
                draw.ellipse([gx - 1, gy - 1, gx + 1, gy + 1],
                             fill=(196, 180, 148))
    placed = []
    for st in stories:
        if not is_pinned(st):
            continue
        bx, by = project(st["lon"], st["lat"], mx + 2, my + 2, mw - 4, mh - 4)
        px, py = bx, by
        # A colliding pin tries radial offsets in turn (right, left,
        # down, up, diagonals, then further out) and takes the first
        # spot clear of every placed pin, so dense clusters (Riyadh /
        # Hodeidah / Gaza / Jerusalem; Jiuquan / Bogor / Kuala Lumpur)
        # fan out instead of stacking on one x offset and hiding each
        # other. Pins are schematic; the legend carries the numbers.
        # v8.1: the threshold is the pin diameter plus a 3px gap, and
        # every candidate is clamped inside the map frame, so no pin
        # can be pushed out of the box and clipped by the frame.
        if any(abs(px - qx) < 25 and abs(py - qy) < 25
               for qx, qy in placed):
            for dx, dy in ((28, 0), (-28, 0), (0, 18), (0, -18),
                           (28, 18), (28, -18), (-28, 18), (-28, -18),
                           (56, 0), (-56, 0), (56, 18), (56, -18),
                           (0, 36), (0, -36), (84, 0), (-84, 0)):
                cx, cy = bx + dx, by + dy
                cx = min(max(cx, mx + 13), mx + mw - 13)
                cy = min(max(cy, my + 13), my + mh - 13)
                if not any(abs(cx - qx) < 25 and abs(cy - qy) < 25
                           for qx, qy in placed):
                    px, py = cx, cy
                    break
            else:
                px, py = bx + 84, by
        px = min(max(px, mx + 13), mx + mw - 13)
        py = min(max(py, my + 13), my + mh - 13)
        placed.append((px, py))
        r = 11
        # pin in the story's region colour (the 11-19..11-23 winners
        # all colour-code their pins by region)
        pcol = REGION_COLORS.get(st.get("region", ""), RED)
        # v8.1: a pin pushed far off its true spot gets a leader
        # line back to a small dot on the true location. On a map
        # only 80px tall, a 25px nudge is ~45 degrees of latitude,
        # so without the dot a displaced pin lands in the wrong sea
        # (v8 put Giza's pin south of Africa and Gaza's in the
        # North Sea); the dot keeps the true spot readable.
        if (px - bx) ** 2 + (py - by) ** 2 > 12 ** 2:
            draw.line([(bx, by), (px, py)], fill=(120, 110, 92), width=1)
            draw.ellipse([bx - 3, by - 3, bx + 3, by + 3], fill=pcol,
                         outline=(255, 255, 255), width=1)
        draw.ellipse([px - r, py - r, px + r, py + r], fill=pcol,
                     outline=(255, 255, 255), width=3)
        f = f_sans(11, bold=True)
        label = str(st["n"])
        tw = text_w(f, label)
        draw.text((px - tw / 2, py - 6), label, font=f, fill=(255, 255, 255))


# ---------------------------------------------------------------- page

def region_counts(stories):
    counts = {}
    for st in stories:
        counts[st.get("region", "")] = counts.get(st.get("region", ""), 0) + 1
    order = ["N. AMERICA", "LATIN AMERICA", "EUROPE", "MIDDLE EAST",
             "N. AFRICA", "SUB-SAH. AFRICA", "SOUTH ASIA", "E. & SE ASIA",
             "OCEANIA", "GLOBAL"]
    return [(r, counts[r]) for r in order if r in counts]


def trunc_line(draw, s, f, width):
    """Shorten `s` with an ellipsis until it fits `width`."""
    if text_w(f, s) <= width:
        return s
    while text_w(f, s + "…") > width and len(s) > 4:
        s = s[:-1]
    return s + "…"


def render(data, geo):
    img = Image.new("RGB", (W, H), PAPER)
    draw = ImageDraw.Draw(img)
    x0, x1 = 20, 1004
    cw = x1 - x0

    draw.rectangle([8, 8, W - 9, H - 9], outline=INK, width=2)

    main = data["main"]
    medium = data["medium"]
    also = data["also"]
    all_stories = main + medium + also
    total = len(all_stories)
    counts = region_counts(all_stories)
    regions = {st.get("region", "") for st in all_stories}
    fields = {st.get("field", "") for st in all_stories}
    field_counts = {}
    for st in all_stories:
        f = st.get("field", "")
        field_counts[f] = field_counts.get(f, 0) + 1
    date_str = data.get("date", "Wednesday 25 November 2026").upper()

    # ---- masthead (v7): one dominant element -- the big serif date
    # (rank1's serif date title, now 48pt Didone, the largest text on
    # the page). The title shrinks to a small eyebrow line; the
    # nameplate sits between double rules (broadsheet convention).
    y = 14
    f_small = f_sans(10, bold=True)
    left = (f"{total} STORIES · {len(regions)} REGIONS · "
            f"{len(fields)} FIELDS")
    draw.text((x0, y), left, font=f_small, fill=INK)
    mid = "THE WORLD IN ONE DAY"
    draw.text((x0 + cw // 2 - text_w(f_small, mid) // 2, y), mid,
              font=f_small, fill=INK)
    right = "DAY 329 OF 2026"
    draw.text((x1 - text_w(f_small, right), y), right, font=f_small, fill=INK)
    # v8.2 (G1): the winners' eyebrow carries the first-reported
    # line; it fits in the gap between the centred title and the
    # right-hand day number (290px in a ~370px gap).
    phrase = "· ALL FIRST REPORTED ON WEDNESDAY 25 NOVEMBER 2026"
    draw.text((x1 - text_w(f_small, right) - 12
               - text_w(f_small, phrase), y), phrase, font=f_small,
              fill=INK)

    f_date = f_display(48)
    date_title = data.get("date", "Wednesday 25 November 2026")
    draw.text((x0 + cw // 2 - text_w(f_date, date_title) // 2, 28),
              date_title, font=f_date, fill=INK)
    hline(draw, x0, x1, 88, width=2)
    hline(draw, x0, x1, 91, width=1)

    # ---- subline: region colour chips, one per region present
    # (11-23 regian's colour system: the same colours reappear on the
    # map pins, the medium icons and the also-list numbers)
    f_chip = f_sans(10, bold=True)
    chip_h = 15
    chip_gap = 6
    chip_ws = [text_w(f_chip, f"{r} {c}") + 14 for r, c in counts]
    tot_cw = sum(chip_ws) + chip_gap * (len(chip_ws) - 1)
    cx = x0 + (cw - tot_cw) // 2
    for (r, c), w in zip(counts, chip_ws):
        col = REGION_COLORS.get(r, INK)
        draw.rectangle([cx, 95, cx + w, 95 + chip_h], fill=col)
        draw.text((cx + 7, 97), f"{r} {c}", font=f_chip,
                  fill=(255, 255, 255))
        cx += w + chip_gap
    # ---- fields breakdown (v8): one line under the chips, fields
    # sorted by count so the reader sees the mix at a glance
    f_field = f_sans(9)
    field_parts = sorted(field_counts.items(), key=lambda kv: (-kv[1], kv[0]))
    field_line = f"{len(fields)} FIELDS — " + " · ".join(
        f"{k.upper()} {c}" for k, c in field_parts)
    if text_w(f_field, field_line) > cw:
        f_field = f_sans(8)
    draw.text((x0 + (cw - text_w(f_field, field_line)) // 2, 114),
              field_line, font=f_field, fill=INK)
    hline(draw, x0, x1, 126, width=1)

    # ---- ticker: italic items joined by hand-drawn red diamonds
    # (the ◆ glyph is missing from the italic serif face, so draw it)
    f_tick = f_serif(13, italic=True)
    items = data.get("ticker", [])
    parts_w = [text_w(f_tick, t) for t in items]
    gap = 22
    total_w = sum(parts_w) + gap * (len(items) - 1)
    tx = x0 + (cw - total_w) // 2
    ty = 131
    for i, t in enumerate(items):
        draw.text((tx, ty), t, font=f_tick, fill=INK)
        tx += parts_w[i]
        if i < len(items) - 1:
            cx, cy = tx + gap // 2, ty + 8
            draw.polygon([(cx, cy - 4), (cx + 4, cy), (cx, cy + 4),
                          (cx - 4, cy)], fill=RED)
            tx += gap
    hline(draw, x0, x1, 150, width=1)

    # ---- six number strips: dark navy band (bagarte's numbers panel),
    # with a red label column on the left
    numbers = data.get("numbers", [])[:6]
    y = 154
    draw.rectangle([x0, y, x1, 198], fill=NAVY)
    label_w = 110
    draw.rectangle([x0, y, x0 + label_w, 198], fill=RED)
    f_nlab2 = f_sans(9, bold=True)
    for j, ln in enumerate(["THE DAY IN", "NUMBERS"]):
        draw.text((x0 + 8, y + 10 + j * 12), ln, font=f_nlab2,
                  fill=(255, 255, 255))
    bw = (cw - label_w) // 6
    f_num = f_display(22)
    f_nlab = f_sans(9)
    for i, (num, label) in enumerate(numbers):
        bx = x0 + label_w + i * bw
        if i:
            draw.line([(bx, y + 4), (bx, y + 42)], fill=(70, 85, 120),
                      width=1)
        draw.text((bx + bw // 2 - text_w(f_num, num) // 2, y), num,
                  font=f_num, fill=(255, 255, 255))
        # a "\n" in a label forces a balanced break (the KOSPI label used
        # to orphan "Jan" on its own line); otherwise wrap greedily
        lab_lines = []
        for part in label.split("\n"):
            lab_lines.extend(wrap(draw, part, f_nlab, bw - 12))
        for j, ln in enumerate(lab_lines):
            draw.text((bx + 6, y + 23 + j * 10), ln, font=f_nlab,
                      fill=(205, 210, 225))
    hline(draw, x0, x1, 198, width=1)

    f_lab = f_sans(11, bold=True)  # section headers + timeline label
    # ---- UTC timeline (v8.2, G3: moved to the top -- the winners
    # put THE DAY IN UTC as a strip right under the numbers band,
    # so the day's time spine is visible on the first screen)
    y = 204
    lab = "THE DAY IN UTC"
    lab_w = text_w(f_lab, lab) + 12
    draw.rectangle([x0, y - 3, x0 + lab_w, y + 11], fill=RED)
    draw.text((x0 + 6, y), lab, font=f_lab, fill=(255, 255, 255))
    ty = y + 18
    draw.line([(x0 + 8, ty), (x1 - 8, ty)], fill=INK, width=2)
    events = []
    seen_times = set()
    for st in all_stories:
        t = st.get("time_utc")
        # Accept both HH:MM and ISO stamps; one dot per clock time, so
        # four stories sharing the 13:30 data release read as one dot.
        # "n/a" means the story carries no usable time and is skipped.
        m = re.fullmatch(r"(\d{1,2}):(\d{2})", t or "")
        if not m:
            m = re.search(r"T(\d{2}):(\d{2})", t or "")
        if not m:
            continue
        hhmm = f"{int(m.group(1)):02d}:{m.group(2)}"
        if hhmm in BAD_TIMES or hhmm in seen_times:
            continue
        seen_times.add(hhmm)
        events.append((hhmm, st))
    events.sort(key=lambda e: e[0])
    f_tt = f_sans(9, bold=True)
    f_te = f_sans(8)
    span_w = x1 - x0 - 40
    placed_x = []
    label_right = x0 + lab_w + 8
    place_right = -1
    for t, st in events:
        hh, mm = map(int, t.split(":"))
        frac = (hh * 60 + mm) / (24 * 60)
        px = x0 + 20 + frac * span_w
        for qx in placed_x:
            if abs(px - qx) < 16:
                px = qx + 16
        placed_x.append(px)
        draw.ellipse([px - 4, ty - 4, px + 4, ty + 4], fill=RED,
                     outline=(255, 255, 255), width=1)
        lx = px - text_w(f_tt, t) // 2
        if lx < label_right + 4:
            lx = label_right + 4
        draw.text((lx, ty - 15), t, font=f_tt, fill=INK)
        label_right = lx + text_w(f_tt, t)
        cap = st.get("place", "")
        cx = px - text_w(f_te, cap) // 2
        if cx < place_right + 4:
            cx = place_right + 4
        draw.text((cx, ty + 7), cap, font=f_te, fill=MUTED)
        place_right = cx + text_w(f_te, cap)
    tl_bottom = ty + 20
    hline(draw, x0, x1, tl_bottom, width=1)


    # ---- three main stories
    y = tl_bottom + 4
    col_w = (cw - 2 * 14) // 3
    main_bottom = y
    for i, st in enumerate(main):
        cx = x0 + i * (col_w + 14)
        col = REGION_COLORS.get(st.get("region", ""), INK)
        f_kick = f_sans(10, bold=True)
        kick = f"{st.get('region', '')} — {st.get('place', '')}"
        draw.text((cx, y), kick, font=f_kick, fill=col)
        # measure the chip first so it right-aligns exactly
        f_chipm = f_sans(9, bold=True)
        cw_chip = text_w(f_chipm, (st.get("status") or "REPORTED").upper()) + 12
        status_chip(draw, cx + col_w - cw_chip, y - 1,
                    st.get("status", "REPORTED"))
        f_head = f_serif(17, bold=True)
        hy = y + 18
        for ln in wrap(draw, st["headline"], f_head, col_w)[:2]:
            draw.text((cx, hy), ln, font=f_head, fill=INK)
            hy += 19
        sy = y + 58
        draw_scene(img, kind_of(st), cx, sy, col_w, 60)
        # data banner inside the scene (regian / superskie): the key
        # fact, taken from the story's own text, never invented
        banner = st.get("banner")
        if banner:
            f_ban = f_sans(9, bold=True)
            bw = text_w(f_ban, banner) + 12
            draw.rectangle([cx + 6, sy + 6, cx + 6 + bw, sy + 22], fill=RED)
            draw.text((cx + 12, sy + 9), banner, font=f_ban,
                      fill=(255, 255, 255))
        f_body = f_serif(11)
        by = sy + 68
        blines = wrap(draw, st["body"], f_body, col_w)
        shown = blines[:3]
        if len(blines) > 3:
            shown[-1] = shown[-1].rstrip() + " …"
        for ln in shown:
            draw.text((cx, by), ln, font=f_body, fill=INK)
            by += 13
        # v8: WHY IT MATTERS moves into the column (the strip is gone):
        # one red label + one serif line, in the story's own words
        f_whyh = f_sans(8, bold=True)
        f_why = f_serif(10)
        why_label = "WHY IT MATTERS "
        why_text = trunc_line(draw, st.get("why", ""), f_why,
                              col_w - text_w(f_whyh, why_label))
        draw.text((cx, by + 1), why_label, font=f_whyh, fill=RED)
        draw.text((cx + text_w(f_whyh, why_label), by + 1), why_text,
                  font=f_why, fill=INK)
        by += 14
        f_src = f_sans(9)
        draw.text((cx, by + 1), "Source: " + st.get("source", ""),
                  font=f_src, fill=MUTED)
        main_bottom = max(main_bottom, by + 12)
    hline(draw, x0, x1, main_bottom + 6, width=1)

    # ---- medium grid (v8.2): 6 columns x 2 rows of scene cards --
    # a scene on top, a full-width field-coloured data strip, a
    # 2-line title, a 1-line body and a status line with a solid
    # status chip (sunny-fox's card pattern)
    y = main_bottom + 10
    draw.text((x0, y), "MORE OF THE DAY", font=f_lab, fill=INK)
    n_label = f"{len(medium)} STORIES"
    draw.text((x1 - text_w(f_lab, n_label), y), n_label, font=f_lab,
              fill=MUTED)
    gy = y + 16
    ncols = 6
    cell_w = (cw - (ncols - 1) * 8) // ncols
    cell_h = 100
    scene_h = 36
    nrows = 2
    for idx, st in enumerate(medium):
        r, c = divmod(idx, ncols)
        cx = x0 + c * (cell_w + 8)
        cy = gy + r * (cell_h + 6)
        draw_scene(img, kind_of(st), cx, cy, cell_w, scene_h)
        # v8.2 (G4): the data chip becomes a full-width coloured
        # strip under the scene, coloured by field; the region
        # colour survives in the status line below, which carries
        # the story number and place.
        col = REGION_COLORS.get(st.get("region", ""), INK)
        strip_h = 0
        chip = st.get("chip")
        if chip:
            strip_h = 12
            draw.rectangle([cx, cy + scene_h, cx + cell_w,
                            cy + scene_h + strip_h],
                           fill=FIELD_STRIP_COLORS.get(
                               st.get("field", ""), NAVY))
            f_chip2 = f_sans(9, bold=True)
            draw.text((cx + 6, cy + scene_h + 2), chip, font=f_chip2,
                      fill=(255, 255, 255))
        f_mh = f_serif(11, bold=True)
        hlines = wrap(draw, st["headline"], f_mh, cell_w)
        shown = hlines[:2]
        if len(hlines) > 2:
            shown[-1] = trunc_line(draw, shown[-1].rstrip(), f_mh, cell_w)
        my = cy + scene_h + strip_h + 3
        for ln in shown:
            draw.text((cx, my), ln, font=f_mh, fill=INK)
            my += 13
        f_mb = f_serif(10)
        body1 = wrap(draw, st["body"], f_mb, cell_w)
        if body1:
            draw.text((cx, my), trunc_line(draw, body1[0], f_mb, cell_w),
                      font=f_mb, fill=INK)
        # status word right-aligned in its colour + the time in the
        # prefix (H6/H12). The per-card source name moves to the footer
        # SOURCES line; the prefix drops the time first if prefix +
        # status would overflow the card.
        f_ms = f_sans(8)
        f_msb = f_sans(8, bold=True)
        status = (st.get("status") or "REPORTED").upper()
        scol = {"OFFICIAL": NAVY, "CLAIM": (178, 106, 0),
                "REPORTED": (46, 107, 52),
                "CONFIRMED": CONFIRMED_TEAL}.get(status, (46, 107, 52))
        chip_w = text_w(f_msb, status) + 10
        t = hhmm_of(st.get("time_utc"))
        prefix = f"{st['n']} · {st.get('place', '')}"
        if t and text_w(f_msb, prefix + f" · {t}") + chip_w <= cell_w - 4:
            prefix += f" · {t}"
        if text_w(f_msb, prefix) + chip_w > cell_w - 4:
            prefix = trunc_line(draw, prefix, f_msb, cell_w - 4 - chip_w)
        sy2 = cy + cell_h - 13
        draw.text((cx, sy2), prefix, font=f_msb, fill=col)
        draw.rounded_rectangle([cx + cell_w - chip_w, sy2 - 1,
                                cx + cell_w, sy2 + 12], radius=3,
                               fill=scol)
        draw.text((cx + cell_w - chip_w + 5, sy2 + 1), status,
                  font=f_msb, fill=(255, 255, 255))
    hline(draw, x0, x1, gy + cell_h + 3, fill=FAINT)
    grid_bottom = gy + nrows * (cell_h + 6) - 6
    hline(draw, x0, x1, grid_bottom + 6, width=1)

    # ---- map + legend (v8: WHY strip deleted, why lives in main)
    y = grid_bottom + 10
    draw.text((x0, y), "WHERE IT HAPPENED — PINS CARRY THE STORY NUMBERS",
              font=f_lab, fill=INK)
    draw.text((x1 - text_w(f_lab, "MAP: NATURAL EARTH 110M"), y),
              "MAP: NATURAL EARTH 110M", font=f_lab, fill=MUTED)
    my = y + 16
    mh = 74
    map_w = 660
    pinned = [st for st in main + medium if is_pinned(st)]
    draw_map(img, draw, geo, pinned, x0, my, map_w, mh)
    lx = x0 + map_w + 14
    f_leg = f_sans(9)
    # 15 pinned stories (3 main + 12 medium) in 3 columns x 5 rows
    per_col = (len(pinned) + 2) // 3
    for i, st in enumerate(pinned):
        col, row = divmod(i, per_col)
        entry = f"{st['n']}  {st.get('place', '')}"
        lx0 = lx + col * 103
        dot = REGION_COLORS.get(st.get("region", ""), INK)
        draw.rectangle([lx0, my + 3 + row * 11, lx0 + 7, my + 10 + row * 11],
                       fill=dot)
        draw.text((lx0 + 10, my + 1 + row * 11),
                  trunc_line(draw, entry, f_leg, 96),
                  font=f_leg, fill=INK)
    map_bottom = my + mh
    hline(draw, x0, x1, map_bottom + 6, width=1)

    # ---- also list, three columns, grouped by field count in the header
    y = map_bottom + 10
    n_fields = len({st.get("field", "") for st in also})
    draw.text((x0, y),
              f"ALSO ON {date_str} — {len(also)} STORIES, {n_fields} FIELDS",
              font=f_lab, fill=INK)
    # wires cut-off note lives on the ALSO header row now: the UTC band
    # header row is too crowded (its right end collides with the 21:00
    # event label), and the ALSO header's right half is empty.
    wires = data.get("wires_read", "")
    if wires:
        draw.text((x1 - text_w(f_lab, wires), y), wires,
                  font=f_lab, fill=MUTED)
    ay = y + 16
    acol_w = (cw - 2 * 12) // 3
    f_al = f_sans(9)
    f_alb = f_sans(9, bold=True)
    f_alt = f_sans(8)
    f_als = f_sans(8, bold=True)
    per_col = (len(also) + 2) // 3
    for ci in range(3):
        ax = x0 + ci * (acol_w + 12)
        for j, st in enumerate(also[ci * per_col:(ci + 1) * per_col]):
            ncol = REGION_COLORS.get(st.get("region", ""), INK)
            num = f"{st['n']}  "
            # v7 (H12): time_utc at the tail of the row where known;
            # v8: a status letter (O/R/C) at the very tail, like the
            # winners' lists. The text is truncated to leave room.
            t = hhmm_of(st.get("time_utc"))
            ttxt = f" {t}" if t else ""
            tw_t = text_w(f_alt, ttxt) if t else 0
            slet = {"OFFICIAL": "O", "REPORTED": "R",
                    "CLAIM": "C", "CONFIRMED": "\u2713"}.get(
                        (st.get("status") or "").upper(), "")
            sw = text_w(f_als, f" {slet}") if slet else 0
            scol = {"OFFICIAL": NAVY, "CLAIM": (178, 106, 0),
                    "REPORTED": (46, 107, 52),
                    "CONFIRMED": CONFIRMED_TEAL}.get(
                        (st.get("status") or "").upper(), (46, 107, 52))
            rest = trunc_line(
                draw, f"{st.get('place', '')} — {st['text']}", f_al,
                acol_w - text_w(f_alb, num) - tw_t - sw - 4)
            ry = ay + j * 10
            draw.text((ax, ry), num, font=f_alb, fill=ncol)
            draw.text((ax + text_w(f_alb, num), ry), rest,
                      font=f_al, fill=INK)
            if t:
                draw.text((ax + acol_w - tw_t - sw, ry), ttxt,
                          font=f_alt, fill=MUTED)
            if slet:
                draw.text((ax + acol_w - sw, ry), f" {slet}",
                          font=f_als, fill=scol)
    also_bottom = ay + (per_col - 1) * 10 + 10
    hline(draw, x0, x1, also_bottom + 6, width=1)

    # ---- footer: date check in a red-outlined box, how to read, left out
    y = also_bottom + 12
    f_fh = f_sans(10, bold=True)
    f_fb = f_serif(10)
    dc = data.get("datecheck", "")
    tx = x0 + 92
    fy = y
    for ln in wrap(draw, dc, f_fb, x1 - tx)[:3]:
        draw.text((tx, fy), ln, font=f_fb, fill=INK)
        fy += 11
    # NOT YET line (rank1): scheduled items that had not happened by the
    # wires cut are named here, not reported as news
    ny = data.get("notyet", "")
    if ny:
        f_ny = f_sans(10, bold=True)
        head = "NOT YET: "
        rest = ny[len(head):] if ny.startswith(head) else ny
        draw.text((tx, fy), head, font=f_ny, fill=RED)
        draw.text((tx + text_w(f_ny, head), fy), rest, font=f_fb, fill=INK)
        fy += 11
    draw.rectangle([x0, y - 5, x1, fy + 2], outline=RED, width=1)
    draw.rectangle([x0, y - 5, x0 + 90, y + 11], fill=RED)
    draw.text((x0 + 5, y - 2), "DATE CHECK", font=f_fh,
              fill=(255, 255, 255))
    f_hr = f_sans(9)
    howto = ("HOW TO READ: numbers match the map pins. OFFICIAL = government "
             "data · CLAIM = one party's claim, unconfirmed · REPORTED = "
             "outlet reporting · CONFIRMED = official record or 2+ major "
             "outlets. DATE CHECK rules on dates.")
    draw.text((x0, fy + 4), trunc_line(draw, howto, f_hr, cw),
              font=f_hr, fill=INK)
    # v7 (H7): aggregate Sources line -- every outlet behind the 50
    # stories, in story order, truncated to the page width.
    seen = []
    for st in all_stories:
        s = st.get("source", "")
        if s and s not in seen:
            seen.append(s)
    # v8.1: sources wrap onto full lines, split only at " · "
    # boundaries, instead of truncating mid-name (v8 cut the line
    # at "AUSTRALIAN BUR…", losing half the outlets).
    f_fs = f_sans(8)
    src_lines = []
    cur = "SOURCES: "
    for s in seen:
        add = s if cur == "SOURCES: " else " · " + s
        if text_w(f_fs, cur + add) <= cw:
            cur += add
        else:
            src_lines.append(cur)
            cur = s
    src_lines.append(cur)
    for i, ln in enumerate(src_lines):
        draw.text((x0, fy + 13 + i * 9), ln, font=f_fs, fill=MUTED)
    y = fy + 13 + len(src_lines) * 9
    f_ff = f_sans(8)
    # v8.1: the full status legend already sits in HOW TO READ
    # above; here only the O/R/C letter key is needed, which frees
    # room for the LEFT OUT line (v8 cut it at "guilty p…").
    legend = "O = OFFICIAL · R = REPORTED · C = CLAIM · ✓ = CONFIRMED"
    legend_w = text_w(f_ff, legend)
    left = "; ".join(data.get("excluded", [])[:5])
    if len(data.get("excluded", [])) > 5:
        left += "; …"
    left = "LEFT OUT: " + left
    max_left = x1 - legend_w - 16 - x0
    if text_w(f_ff, left) > max_left:
        while text_w(f_ff, left + "…") > max_left and len(left) > 6:
            left = left[:-1]
        left += "…"
    draw.text((x0, y), left, font=f_ff, fill=MUTED)
    draw.text((x1 - legend_w, y), legend, font=f_ff, fill=MUTED)

    if y + 10 > H - 8:
        raise SystemExit("layout overflow: footer past page edge")
    return img


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=None)
    ap.add_argument("--geo", default=None)
    ap.add_argument("--output", default=None)
    args = ap.parse_args(argv)

    here = os.path.dirname(os.path.abspath(__file__))
    src = args.input or os.path.join(here, "stories.json")
    geo_local = os.path.join(here, "land-110m.geojson")
    geo_fallback = os.path.expanduser(
        "~/workspace/makefun/news-image-20261125-v3/repo/land-110m.geojson")
    geo_path = args.geo or (geo_local if os.path.exists(geo_local)
                            else geo_fallback)
    out = args.output or os.path.join(here, "entry.png")

    with open(src, encoding="utf-8") as fh:
        data = json.load(fh)
    with open(geo_path, encoding="utf-8") as fh:
        geo = json.load(fh)

    img = render(data, geo)
    assert img.size == (W, H), img.size
    img.save(out)
    print(f"wrote {out} from {src}  size={img.size}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
