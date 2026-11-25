#!/usr/bin/env python3
"""Render the news-image-20261125 entry: a one-page vector infographic.

Deterministic: same input files -> same bytes out. No network, no clock,
no randomness. Reads stories.json + land-110m.geojson (Natural Earth,
public domain) next to this file, writes entry.png (1024x1024, PNG).
"""
import json
import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 1024, 1024

NAVY = (13, 34, 64)
RED = (178, 34, 34)
DARKRED = (140, 22, 22)
INK = (22, 22, 22)
GRAY = (96, 96, 96)
LIGHT = (238, 242, 245)
MAP_LAND = (203, 211, 219)
MAP_LINE = (158, 167, 176)
MAP_SEA = (235, 241, 247)
WHITE = (255, 255, 255)
SKY = (24, 52, 96)

F_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
F_R = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


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


def draw_art_tower(d, x, y, w, h):
    d.rectangle([x, y, x + w, y + h], fill=(28, 58, 104))
    d.rectangle([x, y + h - 26, x + w, y + h], fill=(16, 32, 60))
    # skyline
    import random
    rnd = random.Random(7)
    bx = x + 4
    while bx < x + w - 20:
        bw = rnd.randint(14, 30)
        bh = rnd.randint(18, 52)
        d.rectangle([bx, y + h - 26 - bh, bx + bw, y + h - 26],
                    fill=(10, 22, 44))
        bx += bw + 4
    # main twisted tower (KAFD style): tapered, diagonal ribs
    cx = x + w // 2
    top_y, bot_y = y + 8, y + h - 26
    d.polygon([(cx - 13, top_y), (cx + 13, top_y),
               (cx + 24, bot_y), (cx - 24, bot_y)], fill=(214, 219, 226))
    for i in range(6):
        yy = top_y + 10 + i * 12
        d.line([(cx - 16, yy), (cx + 16, yy + 6)], fill=(140, 148, 158), width=2)
    # impact burst at tower top
    bx0, by0 = cx + 22, top_y + 6
    for ang in range(0, 360, 45):
        import math
        r1, r2 = 5, 13
        a = math.radians(ang)
        d.line([(bx0, by0), (bx0 + r2 * math.cos(a), by0 + r2 * math.sin(a))],
               fill=(255, 176, 32), width=3)
    d.ellipse([bx0 - 5, by0 - 5, bx0 + 5, by0 + 5], fill=(255, 120, 20))
    # windows
    for wy in range(top_y + 18, bot_y - 6, 10):
        d.point([(cx - 6, wy), (cx + 6, wy)], fill=(255, 220, 120))


def draw_art_treaty(d, x, y, w, h):
    d.rectangle([x, y, x + w, y + h], fill=(216, 231, 240))
    d.rectangle([x, y + h - 18, x + w, y + h], fill=(120, 170, 120))
    # two flags on poles
    for fx, col in ((x + 34, (0, 40, 110)), (x + w - 74, (0, 90, 60))):
        d.line([(fx, y + 14), (fx, y + h - 18)], fill=(60, 60, 60), width=2)
        d.rectangle([fx, y + 14, fx + 40, y + 40], fill=col)
        for sx in range(4):
            d.ellipse([fx + 6 + sx * 9, y + 20, fx + 10 + sx * 9, y + 24],
                      fill=(255, 255, 255))
    # treaty document
    dx, dy = x + w // 2 - 46, y + 26
    d.rectangle([dx, dy, dx + 92, dy + 58], fill=WHITE,
                outline=(120, 120, 120))
    for i in range(4):
        d.line([(dx + 10, dy + 12 + i * 11), (dx + 82, dy + 12 + i * 11)],
               fill=(150, 150, 150), width=2)
    d.ellipse([dx + 66, dy + 44, dx + 84, dy + 62], fill=RED,
              outline=(120, 0, 0))


def draw_art_rocket(d, x, y, w, h):
    import math
    d.rectangle([x, y, x + w, y + h], fill=(12, 22, 44))
    rnd = __import__("random").Random(11)
    for _ in range(26):
        sx = x + rnd.randint(4, w - 4)
        sy = y + rnd.randint(4, h - 30)
        d.ellipse([sx, sy, sx + 2, sy + 2], fill=(255, 255, 255))
    cx = x + w // 2
    # smoke
    for i, (ox, oy, r) in enumerate(((-26, 78, 12), (26, 82, 14), (0, 88, 16))):
        d.ellipse([cx + ox - r, y + oy - r, cx + ox + r, y + oy + r],
                  fill=(190, 195, 200))
    # flame
    d.polygon([(cx - 9, y + 66), (cx + 9, y + 66), (cx, y + 96)],
              fill=(255, 140, 20))
    d.polygon([(cx - 5, y + 66), (cx + 5, y + 66), (cx, y + 84)],
              fill=(255, 220, 60))
    # rocket body
    d.rectangle([cx - 11, y + 14, cx + 11, y + 66], fill=(235, 238, 242))
    d.polygon([(cx - 11, y + 14), (cx + 11, y + 14), (cx, y - 2)],
              fill=(200, 40, 40))
    d.polygon([(cx - 11, y + 52), (cx - 24, y + 70), (cx - 11, y + 66)],
              fill=(200, 40, 40))
    d.polygon([(cx + 11, y + 52), (cx + 24, y + 70), (cx + 11, y + 66)],
              fill=(200, 40, 40))
    d.ellipse([cx - 5, y + 26, cx + 5, y + 36], fill=(120, 190, 230),
              outline=(60, 60, 60))
    d.rectangle([x, y + h - 8, x + w, y + h], fill=(40, 44, 50))


ART = {"tower": draw_art_tower, "treaty": draw_art_treaty,
       "rocket": draw_art_rocket}


def load_land():
    with open(os.path.join(HERE, "land-110m.geojson")) as f:
        gj = json.load(f)
    polys = []
    for feat in gj["features"]:
        geom = feat["geometry"]
        geoms = geom["coordinates"] if geom["type"] == "MultiPolygon" \
            else [geom["coordinates"]]
        for poly in geoms:
            for ring in poly:
                # split at antimeridian jumps
                cur = [ring[0]]
                for a, b in zip(ring, ring[1:]):
                    if abs(b[0] - a[0]) > 180:
                        polys.append(cur)
                        cur = [b]
                    else:
                        cur.append(b)
                polys.append(cur)
    return polys


def main():
    with open(os.path.join(HERE, "stories.json")) as f:
        data = json.load(f)
    main_stories = data["main"]
    medium = data["medium"]
    also = data["also"]
    all_stories = main_stories + medium + also

    # region counts, in the 1st-place header style
    order = ["EUROPE", "MIDDLE EAST", "ASIA", "AFRICA", "AMERICAS",
             "OCEANIA", "GLOBAL"]
    counts = {r: 0 for r in order}
    for s in all_stories:
        counts[s["region"]] = counts.get(s["region"], 0) + 1
    count_str = " · ".join(f"{r} {counts[r]}" for r in order
                           if counts[r] > 0)

    img = Image.new("RGB", (W, H), WHITE)
    d = ImageDraw.Draw(img)

    # ---- masthead ----
    d.rectangle([0, 0, W, 58], fill=NAVY)
    d.text((16, 6), data["masthead"], font=font(F_B, 28), fill=WHITE)
    date_txt = data["date"].upper()
    dw = d.textlength(date_txt, font=font(F_B, 15))
    d.text((W - 16 - dw, 12), date_txt, font=font(F_B, 15), fill=(255, 200, 60))
    sub = (f"{len(all_stories)} STORIES, ALL FROM {data['date'].upper()}  ·  "
           + count_str)
    d.text((16, 40), sub, font=font(F_B, 12), fill=(190, 205, 225))

    # ---- ticker ----
    d.rectangle([0, 58, W, 94], fill=DARKRED)
    tick = "   •   ".join(data["ticker"])
    tlines = wrap(d, tick, font(F_B, 13), W - 32)
    ty = 58 + (36 - len(tlines) * 15) // 2
    for ln in tlines:
        lw = d.textlength(ln, font=font(F_B, 13))
        d.text(((W - lw) // 2, ty), ln, font=font(F_B, 13), fill=WHITE)
        ty += 15

    y = 102
    # ---- main stories ----
    col_w, gap = 320, 16
    for i, s in enumerate(main_stories):
        x = 16 + i * (col_w + gap)
        ART[s["art"]](d, x, y, col_w, 100)
        d.ellipse([x + 6, y + 6, x + 30, y + 30], fill=RED)
        num = str(s["n"])
        nw = d.textlength(num, font=font(F_B, 14))
        d.text((x + 18 - nw / 2, y + 10), num, font=font(F_B, 14),
               fill=WHITE)
        yy = y + 112
        hl = wrap(d, s["headline"], font(F_B, 18), col_w)
        yy = draw_lines(d, hl, x, yy, font(F_B, 18), INK, 22)
        yy += 4
        body = wrap(d, s["body"], font(F_R, 12), col_w)
        yy = draw_lines(d, body, x, yy, font(F_R, 12), (40, 40, 40), 15)
        yy += 4
        d.text((x, yy), s["source"], font=font(F_B, 10), fill=GRAY)
    y += 256

    # ---- medium stories ----
    y += 6
    d.text((16, y), "THE DAY'S OTHER BIG STORIES", font=font(F_B, 13),
           fill=NAVY)
    y += 18
    mcol_w = 488
    for s in medium:
        _hw = d.textlength(f"{s['place']} — {s['headline']}",
                           font=font(F_B, 12))
        assert _hw <= 460, f"medium headline too wide: {s['n']} {_hw:.0f}px"
        _bl = wrap(d, s['body'], font(F_R, 11), mcol_w - 28)
        assert len(_bl) <= 2, f"medium body wraps to {len(_bl)} lines: {s['n']}"
    for i, s in enumerate(medium):
        col = i % 2
        row = i // 2
        x = 16 + col * (mcol_w + 16)
        ry = y + row * 52
        d.ellipse([x, ry + 2, x + 20, ry + 22], fill=RED)
        num = str(s["n"])
        nw = d.textlength(num, font=font(F_B, 11))
        d.text((x + 10 - nw / 2, ry + 5), num, font=font(F_B, 11),
               fill=WHITE)
        tx = x + 28
        head = f"{s['place']} — {s['headline']}"
        d.text((tx, ry), head, font=font(F_B, 12), fill=INK)
        bl = wrap(d, s["body"], font(F_R, 11), mcol_w - 28)
        draw_lines(d, bl[:2], tx, ry + 16, font(F_R, 11), (40, 40, 40), 13)
        d.text((tx, ry + 40), s["source"], font=font(F_B, 9), fill=GRAY)
    y += 4 * 52 + 4

    # ---- map + by the numbers ----
    y += 4
    d.text((16, y), "WHERE THE NEWS IS", font=font(F_B, 12), fill=NAVY)
    d.text((652, y), "BY THE NUMBERS", font=font(F_B, 12), fill=NAVY)
    y += 16
    map_x, map_w, map_h = 16, 620, 108
    d.rectangle([map_x, y, map_x + map_w, y + map_h], fill=MAP_SEA)
    polys = load_land()
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
    nudge = {1: (8, -4), 4: (-8, 6), 11: (-6, -4)}
    for s in main_stories + medium:
        px = map_x + (s["lon"] + 180) / 360.0 * map_w
        py = y + (78 - s["lat"]) / 138.0 * map_h
        dx, dy = nudge.get(s["n"], (0, 0))
        px, py = px + dx, py + dy
        d.ellipse([px - 7, py - 7, px + 7, py + 7], fill=RED,
                  outline=WHITE, width=2)
        num = str(s["n"])
        nw = d.textlength(num, font=font(F_B, 9))
        d.text((px - nw / 2, py - 5), num, font=font(F_B, 9), fill=WHITE)
    # numbers panel
    nx, nw_ = 652, 356
    d.rectangle([nx, y, nx + nw_, y + map_h], fill=LIGHT)
    stats = [("11", "hurt in Riyadh tower strike"),
             ("€1.78tn", "EU budget on the table"),
             ("$743m", "Naver's logistics bet"),
             ("200 yrs", "Mackenzie jail term"),
             ("72", "orangutans rescued"),
             ("−5.54%", "KOSPI's Wednesday fall")]
    for i, (big, small) in enumerate(stats):
        col, row = i % 2, i // 2
        sx = nx + 12 + col * 172
        sy = y + 8 + row * 38
        d.text((sx, sy), big, font=font(F_B, 16), fill=RED)
        d.text((sx, sy + 20), small, font=font(F_R, 10), fill=(50, 50, 50))
    y += map_h + 8

    # ---- also list ----
    d.text((16, y), "ALSO ON WEDNESDAY 25 NOVEMBER", font=font(F_B, 13),
           fill=NAVY)
    y += 20
    acol_w = 320
    for i, s in enumerate(also):
        col, row = i % 3, i // 3
        x = 16 + col * (acol_w + 16)
        ry = y + row * 24
        head = f"{s['n']} · {s['place']} — "
        hw = d.textlength(head, font=font(F_B, 10))
        d.text((x, ry), head, font=font(F_B, 10), fill=NAVY)
        full = f"{s['text']} ({s['source']})"
        first = wrap(d, full, font(F_R, 10), acol_w - hw)
        d.text((x + hw, ry), first[0], font=font(F_R, 10), fill=INK)
        rest = " ".join(first[1:])
        if rest:
            second = wrap(d, rest, font(F_R, 10), acol_w)
            d.text((x, ry + 12), second[0], font=font(F_R, 10), fill=INK)
    y += 8 * 24 + 6

    # ---- footer: date check ----
    d.rectangle([0, y, W, H], fill=NAVY)
    fy = y + 8
    d.text((16, fy), "DATE CHECK — ", font=font(F_B, 11), fill=(255, 200, 60))
    dw = d.textlength("DATE CHECK — ", font=font(F_B, 11))
    decl = wrap(d, data["datecheck"], font(F_R, 11), W - 32 - dw)
    ly = fy
    for ln in decl:
        d.text((16 + dw, ly), ln, font=font(F_R, 11), fill=WHITE)
        ly += 13
    fy = ly + 2
    left = "LEFT OUT: " + "  •  ".join(data["excluded"])
    ll = wrap(d, left, font(F_R, 10), W - 32)
    for ln in ll:
        d.text((16, fy), ln, font=font(F_R, 10), fill=(190, 205, 225))
        fy += 12
    print(f"final y={fy} (canvas {H})")
    assert fy <= H, f"overflow: {fy} > {H}"

    out = os.path.join(HERE, "entry.png")
    img.save(out, format="PNG")
    print(f"wrote {out} {os.path.getsize(out)} bytes")


if __name__ == "__main__":
    main()
