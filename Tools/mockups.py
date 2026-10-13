"""Renders the design mockups. The board, ants, chambers and tunnels come from the real reference
engine (engine.py) at a chosen moment of the designed solution; the surrounding UI is drawn to
match the SwiftUI layout. Every image is stamped MOCKUP: these are not screenshots of the app.

Usage: python3 mockups.py <levels_report.json> <out_dir> [photo_json]
"""
import json
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont, ImageFilter

from engine import Board, Game, Scheduler, STEP, PICKUP, SLOT
from render import render_board, soil_block, tile_block, PAL, hash32, MARGIN_T, MARGIN_L
from palette import FAMILIES, hex_to_rgb
from ant_gait import draw_ant

S = 2  # pixels per point
LOAM = (28, 21, 17); LOAM_R = (39, 29, 23); PANEL = (47, 36, 28); EDGE = (74, 58, 44)
SAND = (233, 220, 195); SAND_DIM = (184, 169, 143); BRASS = (217, 164, 65); DANGER = (224, 86, 58); OK = (140, 197, 106)

FONT_DIR = "/usr/share/fonts/truetype/google-fonts/"


def font(kind, size):
    size = int(size * S)
    names = {"sym": "DejaVuSans-Bold.ttf", "serif": "Lora-Variable.ttf", "serif_b": "Lora-Variable.ttf", "sans": "Poppins-Medium.ttf",
             "sans_b": "Poppins-SemiBold.ttf", "sans_bb": "Poppins-Bold.ttf"}
    for cand in (names[kind], "Poppins-Regular.ttf", "DejaVuSans.ttf"):
        for d in (FONT_DIR, "/usr/share/fonts/truetype/dejavu/"):
            p = os.path.join(d, cand)
            if os.path.exists(p):
                try:
                    return ImageFont.truetype(p, size)
                except OSError:
                    pass
    return ImageFont.load_default()


def P(v):
    return int(round(v * S))


def rrect(d, box, r, fill=None, outline=None, width=1):
    x0, y0, x1, y1 = box
    d.rounded_rectangle([P(x0), P(y0), P(x1), P(y1)], radius=P(r), fill=fill, outline=outline, width=P(width) if outline else 0)


def text(d, xy, s, f, fill=SAND, anchor="la"):
    d.text((P(xy[0]), P(xy[1])), s, font=f, fill=fill, anchor=anchor)


def mockup_stamp(img, label):
    d = ImageDraw.Draw(img, 'RGBA')
    f = font("sans_bb", 15)
    w = d.textlength("MOCKUP — " + label + " — not a screenshot of the running app", font=f)
    x = img.width - w - P(24); y = img.height - P(40)
    d.rounded_rectangle([x - P(12), y - P(8), img.width - P(12), y + P(26)], radius=P(10), fill=(200, 40, 60, 235))
    d.text((x, y), "MOCKUP — " + label + " — not a screenshot of the running app", font=f, fill=(255, 255, 255))


# ---------------------------------------------------------------------------
# engine state helpers
# ---------------------------------------------------------------------------

def curve(board, path, tile, u):
    L = len(path)
    def node(k):
        if k < L:
            c = path[k]
            return (c % board.C + 0.5, c // board.C + 0.5)
        s = path[-1]
        sx, sy = s % board.C + 0.5, s // board.C + 0.5
        tx, ty = tile % board.C + 0.5, tile // board.C + 0.5
        return (sx + (tx - sx) * 0.22, sy + (ty - sy) * 0.22)
    u = max(0.0, min(float(L), u))
    mid = lambda a, b: ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    if u <= 0.5:
        p0, p1 = node(0), node(1); m = mid(p0, p1); t = u / 0.5
        return (p0[0] + (m[0] - p0[0]) * t, p0[1] + (m[1] - p0[1]) * t, p1[0] - p0[0], p1[1] - p0[1])
    if u >= L - 0.5:
        a, b = node(L - 1), node(L); m = mid(a, b); t = (u - (L - 0.5)) / 0.5
        return (m[0] + (b[0] - m[0]) * t, m[1] + (b[1] - m[1]) * t, b[0] - a[0], b[1] - a[1])
    j = int(math.floor(u + 0.5)); tau = u - (j - 0.5)
    pp, pj, pn = node(j - 1), node(j), node(j + 1)
    a, c = mid(pp, pj), mid(pj, pn); o = 1 - tau
    x = o * o * a[0] + 2 * o * tau * pj[0] + tau * tau * c[0]
    y = o * o * a[1] + 2 * o * tau * pj[1] + tau * tau * c[1]
    dx = 2 * o * (pj[0] - a[0]) + 2 * tau * (c[0] - pj[0]); dy = 2 * o * (pj[1] - a[1]) + 2 * tau * (c[1] - pj[1])
    return x, y, dx, dy


def lane_of(trip):
    """Outbound lane (about +-1); carriers come home in the middle (mirrors AntGeometry)."""
    return trip.lane


CARRIER_LANE = -0.15


def apply_lane(x, y, dx, dy, off):
    l = math.hypot(dx, dy)
    if l < 1e-6:
        return x, y
    return x - dy / l * off, y + dx / l * off


def outbound_u(trip, elapsed):
    e = elapsed
    for at, dur in trip.pauses:
        reach = at * STEP
        if e < reach:
            return e / STEP, None
        if e < reach + dur:
            return at, e - reach
        e -= dur
    return e / STEP, None


def pose(board, trip, t):
    if t < trip.depart or t >= trip.home:
        return None
    path = trip.route
    L = len(path)
    lane = lane_of(trip)
    if t < trip.arrive:
        u, paused = outbound_u(trip, t - trip.depart)
        u = min(u, L)
        x, y, dx, dy = curve(board, path, trip.claim.tile, u)
        x, y = apply_lane(x, y, dx, dy, lane * 0.2 * min(1.0, 0.4 + 0.6 * min(u, L - u)))
        h = math.atan2(dy, dx)
        if paused is not None:
            h += 0.4 * math.sin(paused / 0.8 * 2 * math.pi) * min(1.0, paused / 0.2)
        return dict(x=x, y=y, h=h, dist=u, carrying=False, lift=0, scale=(0.3 + 0.7 * u) if u < 1 else 1,
                    moving=paused is None)
    if t < trip.pickup_end:
        p = (t - trip.arrive) / PICKUP
        x, y, dx, dy = curve(board, path, trip.claim.tile, L)
        turn = 0 if p < 0.5 else (p - 0.5) / 0.5
        out_lane = lane * (1 - turn) + lane * CARRIER_LANE * turn
        x, y = apply_lane(x, y, dx, dy, out_lane * 0.2 * 0.4)
        return dict(x=x, y=y, h=math.atan2(dy, dx) + math.pi * turn, dist=L + turn * 0.9, carrying=p >= 0.5,
                    lift=min(1, p / 0.5), scale=1, moving=p >= 0.5)
    u = L - (t - trip.pickup_end) / STEP
    x, y, dx, dy = curve(board, path, trip.claim.tile, u)
    x, y = apply_lane(x, y, dx, dy, lane * CARRIER_LANE * 0.2 * min(1.0, 0.4 + 0.6 * min(max(0, u), L - u)))
    return dict(x=x, y=y, h=math.atan2(-dy, -dx), dist=L + 0.9 + (L - u), carrying=True, lift=1,
                scale=(0.3 + 0.7 * max(0, u)) if u < 1 else 1, moving=True)


def state_at(lv, n_moves, gap, t_after, capacity=None):
    """Follow the designed solution in game time under the slot rule (send only into an open
    slot), making the first n_moves; then look t_after seconds later."""
    board = Board(lv["rows"])
    tunnels = [[tuple(x) for x in t] for t in lv["tunnels"]]
    cap = capacity or lv["classic"]
    g = Game(board, tunnels, cap)
    sch = Scheduler(board, "natural")
    now = 0.0
    for m, q in enumerate(lv["solution"][:n_moves]):
        while True:
            ids = {c.uid for c in g.state.chambers}
            busy = sch.busy_teams(now) - ids
            if len(g.state.chambers) + len(busy) < cap or not busy:
                break
            now = min(sch.slot_free_time(u) for u in busy) + 1e-6
        ev = g.dispatch(q)
        sch.schedule(ev, m, now)
        now += gap
    t = now + t_after
    return board, g, sch, t


def slot_items(g, sch, t):
    """Mirror of GameController.refreshSlots (positions in order of arrival)."""
    busy = {}
    fam = {}
    for tr in sch.trips:
        if tr.pickup_end > t:
            busy[tr.claim.team] = busy.get(tr.claim.team, 0) + 1
            fam[tr.claim.team] = tr.claim.family
    items = []
    ids = set()
    for c in g.state.chambers:
        ids.add(c.uid)
        items.append(("held" if c.held else "waiting", c.family, c.remaining + busy.get(c.uid, 0)))
    for u in sorted(busy):
        if u not in ids:
            items.append(("working", fam[u], busy[u]))
    items.sort(key=lambda it: {"working": 0, "waiting": 1, "held": 2}[it[0]])
    while len(items) < g.state.capacity:
        items.append(("open", None, 0))
    return items


def board_image(lv, board, sch, t, cs, palette=None, hill=True):
    rows = lv["rows"]
    cleared = set()
    for tr in sch.trips:
        if tr.arrive <= t:
            i = tr.claim.tile
            cleared.add((i % board.C - MARGIN_L, i // board.C - MARGIN_T))
    im = render_board(rows, cs, cleared=cleared, palette=palette, hill=hill).convert("RGB")
    d = ImageDraw.Draw(im, 'RGBA')
    for tr in sch.trips:
        if tr.arrive > t:
            i = tr.claim.tile; x, y = i % board.C, i // board.C
            d.rectangle([x * cs, y * cs, (x + 1) * cs - 1, (y + 1) * cs - 1], fill=(255, 255, 255, 64))
    pal = PAL if palette is None else [[hex_to_rgb(c) for c in fam] for fam in palette]
    ants = []
    for tr in sch.trips:
        p = pose(board, tr, t)
        if p:
            f = board.family[tr.claim.tile]; tone = board.tone[tr.claim.tile]
            ants.append((p, pal[f][tone], tr))
    for p, col, tr in ants:
        if not p["carrying"] and p["lift"] > 0:
            i = tr.claim.tile; fx, fy = i % board.C + 0.5, i // board.C + 0.5
            jx, jy = p["x"] + math.cos(p["h"]) * 0.72, p["y"] + math.sin(p["h"]) * 0.72
            e = p["lift"]; x, y = fx + (jx - fx) * e, fy + (jy - fy) * e; h = (0.9 - 0.4 * e) * cs / 2
            d.rounded_rectangle([x * cs - h, y * cs - h, x * cs + h, y * cs + h], radius=h * 0.3, fill=col + (255,), outline=(0, 0, 0, 115))
        draw_ant(im, p["x"], p["y"], p["h"], p["dist"], col, cs, carrying=col if p["carrying"] else None, scale=p["scale"])
    return im, len(ants)


# ---------------------------------------------------------------------------
# UI pieces
# ---------------------------------------------------------------------------

def swatch(size, fam, tile, pal=None, radius=16):
    w, h = size
    pal = pal or PAL
    im = Image.new("RGBA", (P(w), P(h)), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    tp = P(tile)
    d.rectangle([0, 0, P(w), P(h)], fill=pal[fam][2])
    for yy in range(0, P(h), tp):
        for xx in range(0, P(w), tp):
            hv = hash32(xx // tp + fam * 97, (yy // tp) * 31 + fam) % 10
            tone = 0 if hv < 3 else (1 if hv < 7 else (2 if hv < 9 else 3))
            d.rounded_rectangle([xx, yy, xx + tp - S, yy + tp - S], radius=S * 2, fill=pal[fam][tone], outline=(30, 22, 17))
    # top light / bottom shade
    grad = Image.new("RGBA", im.size, (0, 0, 0, 0)); gd = ImageDraw.Draw(grad)
    for yy in range(im.height):
        t = yy / im.height
        a = int(56 * (1 - t * 2)) if t < 0.5 else int(56 * (t * 2 - 1))
        gd.line([(0, yy), (im.width, yy)], fill=(255, 255, 255, a) if t < 0.5 else (0, 0, 0, a))
    im = Image.alpha_composite(im, grad)
    mask = Image.new("L", im.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, im.width - 1, im.height - 1], radius=P(radius), fill=255)
    out = Image.new("RGBA", im.size, (0, 0, 0, 0)); out.paste(im, (0, 0), mask)
    return out


def luminance(c):
    def lin(v):
        v /= 255
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * lin(c[0]) + 0.7152 * lin(c[1]) + 0.0722 * lin(c[2])


def team_card(img, box, fam, need, pal=None, highlighted=False, dimmed=False):
    x0, y0, x1, y1 = box
    pal = pal or PAL
    sw = swatch((x1 - x0, y1 - y0), fam, max(10, (y1 - y0) / 7), pal)
    if dimmed:
        sw.putalpha(sw.getchannel("A").point(lambda a: int(a * 0.45)))
    img.alpha_composite(sw, (P(x0), P(y0)))
    d = ImageDraw.Draw(img, 'RGBA')
    rrect(d, box, 16, outline=BRASS if highlighted else (0, 0, 0, 110), width=4 if highlighted else 1)
    ink = (36, 23, 15) if luminance(pal[fam][1]) > 0.42 else (255, 255, 255)
    f = font("sans_bb", (y1 - y0) * 0.34)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    sh = (255, 255, 255, 90) if ink[0] < 100 else (0, 0, 0, 120)
    d.text((P(cx), P(cy) + S * 2), str(need), font=f, fill=sh, anchor="mm")
    d.text((P(cx), P(cy)), str(need), font=f, fill=ink, anchor="mm")


def pod(img, box, fam=None, n=None, pal=None, jammed=False):
    d = ImageDraw.Draw(img, 'RGBA')
    if fam is None:
        rrect(d, box, 14, fill=LOAM_R)
        x0, y0, x1, y1 = box
        # dashed outline
        for i in range(0, int((x1 - x0) * 2 + (y1 - y0) * 2), 9):
            pass
        rrect(d, box, 14, outline=EDGE, width=1.5)
        return
    team_card(img, box, fam, n, pal)
    if jammed:
        rrect(ImageDraw.Draw(img, 'RGBA'), box, 14, outline=DANGER, width=3)


def return_badge(d, cx, cy, size=18):
    """The brass one-tap "return" mark on a waiting team."""
    r = size / 2
    d.ellipse([P(cx - r), P(cy - r), P(cx + r), P(cy + r)], fill=BRASS, outline=(0, 0, 0, 90), width=P(1))
    text(d, (cx, cy + 0.5), "\u21b6", font("sym", size * 0.62), (42, 28, 18), "mm")


def exit_button(d, cx, cy):
    """The round X in the top-left corner of the game screen."""
    d.ellipse([P(cx - 22), P(cy - 22), P(cx + 22), P(cy + 22)], fill=PANEL + (235,), outline=EDGE, width=P(1.5))
    text(d, (cx, cy + 1), "\u2715", font("sym", 17), SAND, "mm")


def panel_frame(d, box):
    rrect(d, box, 20, fill=PANEL, outline=EDGE, width=1)


def pill(d, box, label, prominent, f=None):
    f = f or font("sans_b", 14)
    rrect(d, box, (box[3] - box[1]) / 2, fill=BRASS if prominent else LOAM_R, outline=None if prominent else EDGE, width=1)
    text(d, ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2), label, f, (42, 28, 18) if prominent else SAND, "mm")


def slider(d, x0, y, x1, frac, label):
    text(d, (x0, y - 22), "ANT SPEED", font("sans_bb", 12), SAND_DIM)
    text(d, (x1 - 60, y - 22), label, font("sans_bb", 13), SAND, "ra")
    text(d, (x1, y - 22), "1×", font("sans_bb", 12), BRASS, "ra")
    tx0, tx1 = x0 + 28, x1 - 28
    d.rounded_rectangle([P(tx0), P(y + 12), P(tx1), P(y + 17)], radius=P(3), fill=(90, 74, 58))
    kx = tx0 + (tx1 - tx0) * frac
    d.rounded_rectangle([P(tx0), P(y + 12), P(kx), P(y + 17)], radius=P(3), fill=BRASS)
    d.ellipse([P(kx - 13), P(y + 1), P(kx + 13), P(y + 27)], fill=(245, 240, 230), outline=(0, 0, 0, 60))
    # tortoise/hare glyphs drawn as simple labels
    text(d, (x0, y + 14), "0.1×", font("sans", 10), SAND_DIM, "lm")
    text(d, (x1, y + 14), "16×", font("sans", 10), SAND_DIM, "rm")


def tool_button(d, box, label):
    rrect(d, box, 14, fill=LOAM_R, outline=EDGE, width=1)
    text(d, ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2), label, font("sans_b", 15), SAND, "mm")


def mini(board, rows, shown_tiles, pal=None, scale=2):
    pal = pal or PAL
    h, w = len(rows), len(rows[0])
    im = Image.new("RGB", (w, h), (42, 32, 25))
    px = im.load()
    for y in range(h):
        for x in range(w):
            ch = rows[y][x]
            if ch == '.':
                continue
            i = (y + MARGIN_T) * board.C + x + MARGIN_L
            if i in shown_tiles:
                f, t = divmod(ord(ch) - 97, 4)
                px[x, y] = pal[f][t]
    return im.resize((w * scale * S, h * scale * S), Image.NEAREST)


# ---------------------------------------------------------------------------
# screens
# ---------------------------------------------------------------------------

def game_screen_landscape(lv, n_moves, t_after, label, jam=False, out=None, highlight_q=None, speed_frac=0.454, speed_label="1.0×",
                          event_text=None, ground=None):
    W, H = 1180, 820
    img = Image.new("RGBA", (P(W), P(H)), LOAM + (255,))
    d = ImageDraw.Draw(img, 'RGBA')
    board, g, sch, t = state_at(lv, n_moves, 3.0, t_after)
    if jam:
        # a genuine mistake sequence: after the ants finish, keep sending teams that can't finish
        t = max(tr.pickup_end for tr in sch.trips) + 1.0
        for _ in range(10):
            if g.deadlocked():
                break
            bad = [q for q in range(len(g.tunnels)) if g.can_dispatch(q) and not g.scout(q)["fits"]]
            good = [q for q in range(len(g.tunnels)) if g.can_dispatch(q)]
            if not good:
                break
            q = (bad or good)[0]
            ev = g.dispatch(q); sch.schedule(ev, len(g.moves) - 1, t)
            t = max([t] + [tr.pickup_end for tr in sch.trips]) + 1.0
    panel_w = 446
    availW, availH = W - panel_w - 48, H - 32
    cell = min(availW / board.C, availH / board.R)
    cell = math.floor(cell * 2) / 2
    cs = P(cell)
    bim, nants = board_image(lv, board, sch, t, cs)
    bx = 16 + (availW - board.C * cell) / 2
    by = 16 + (availH - board.R * cell) / 2
    mask = Image.new("L", bim.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, bim.width - 1, bim.height - 1], radius=P(12), fill=255)
    img.paste(bim, (P(bx), P(by)), mask)
    rrect(d, (bx, by, bx + board.C * cell, by + board.R * cell), 12, outline=DANGER if jam else EDGE, width=3 if jam else 1)
    exit_button(d, 36, 36)
    # panel
    px0 = W - panel_w - 16; py0 = 16
    panel_frame(d, (px0, py0, W - 16, H - 16))
    x = px0 + 16; y = py0 + 16; x1 = W - 32
    text(d, (x, y), "Sunflower & Monarch", font("serif", 24), SAND)
    assists = sum(1 for m in g.moves if m >= 100)
    text(d, (x, y + 34), "Classic · %d moves" % sum(1 for m in g.moves if m < 100) + (" · %d assists" % assists if assists else ""), font("sans", 13), SAND_DIM)
    d.ellipse([P(x1 - 36), P(y), P(x1), P(y + 36)], fill=SAND)
    text(d, (x1 - 18, y + 18), "···", font("sans_bb", 13), PANEL, "mm")
    y += 62
    delivered = sum(1 for tr in sch.trips if tr.home <= t)
    d.rounded_rectangle([P(x), P(y), P(x1), P(y + 5)], radius=P(3), fill=(80, 64, 50))
    d.rounded_rectangle([P(x), P(y), P(x + (x1 - x) * delivered / board.tile_count), P(y + 5)], radius=P(3), fill=BRASS)
    text(d, (x, y + 12), "%d of %d tiles home · %d unclaimed" % (delivered, board.tile_count, board.tile_count - g.state.cleared), font("sans", 12), SAND_DIM)
    y += 40
    items = slot_items(g, sch, t)
    n_open = sum(1 for it in items if it[0] == "open")
    if event_text:
        d.rounded_rectangle([P(x), P(y), P(x + 4), P(y + 34)], radius=P(2), fill=BRASS)
        lines = event_text.split("\n")
        for k, ln in enumerate(lines[:2]):
            text(d, (x + 12, y + k * 17), ln, font("sans", 12), SAND)
        y += 44
    text(d, (x, y), "SLOTS", font("sans_bb", 12), DANGER if jam else SAND_DIM)
    text(d, (x + 52, y), "%d of %d open" % (n_open, len(items)), font("sans_bb", 12), OK if n_open else BRASS)
    text(d, (x1, y), "?", font("sans_bb", 14), SAND_DIM, "ra")
    y += 22
    pw = 58
    cx = x
    for kind, f, n in items:
        box = (cx, y, cx + pw, y + pw)
        if kind == "open":
            pod(img, box)
            d = ImageDraw.Draw(img, 'RGBA')
            text(d, (cx + pw / 2, y + pw / 2), "Open", font("sans_bb", 12), OK, "mm")
        else:
            pod(img, box, f, n)
            d = ImageDraw.Draw(img, 'RGBA')
            col = {"working": SAND, "waiting": BRASS, "held": SAND_DIM}[kind]
            text(d, (cx + pw / 2, y + pw + 4), kind.capitalize(), font("sans_bb", 11), col, "ma")
            if kind == "waiting":
                return_badge(d, cx + pw - 3, y + 3, 18)
        cx += pw + 8
    rrect(d, (cx, y, cx + pw, y + pw), 14, outline=BRASS, width=1.5)
    text(d, (cx + pw / 2, y + pw / 2 - 8), "+", font("sans_bb", 20), BRASS, "mm")
    text(d, (cx + pw / 2, y + pw / 2 + 14), "Slot", font("sans_bb", 11), BRASS, "mm")
    y += pw + 24
    if n_open == 0 and not jam:
        text(d, (x, y - 4), "All slots busy — next one opens in about 9 s. Teams can't be sent until then.", font("sans", 11), BRASS)
        y += 16
    # tunnels
    text(d, (x, y), "TUNNELS", font("sans_bb", 12), SAND_DIM)
    text(d, (x + 70, y + 1), "Tap to send into an open slot · each tap sends the next team", font("sans", 11), SAND_DIM)
    y += 20
    nq = len(g.tunnels); colw = (x1 - x - 10 * (nq - 1)) / nq
    for q in range(nq):
        cx0 = x + q * (colw + 10)
        left = len(g.tunnels[q]) - g.state.heads[q] + len(g.state.returned[q])
        text(d, (cx0 + colw / 2, y), "TUNNEL %d · %d left" % (q + 1, left), font("sans_bb", 11), SAND_DIM, "ma")
        fr = g.front(g.state, q)
        if fr:
            team_card(img, (cx0, y + 20, cx0 + colw, y + 118), fr[0], fr[1], highlighted=(highlight_q == q), dimmed=(n_open == 0))
            h = g.state.heads[q]
            nxt = g.tunnels[q][h + 1:h + 4]
            for k, (f, n) in enumerate(nxt):
                cb = (cx0, y + 126 + k * 30, cx0 + colw, y + 152 + k * 30)
                team_card(img, cb, f, n)
            d = ImageDraw.Draw(img, 'RGBA')
            more = left - 1 - len(nxt)
            if more > 0:
                text(d, (cx0 + colw / 2, y + 220), "+%d more" % more, font("sans_bb", 12), BRASS, "ma")
    d = ImageDraw.Draw(img, 'RGBA')
    y += 244
    if highlight_q is not None and not jam:
        rrect(d, (x, y, x1, y + 58), 14, fill=LOAM_R, outline=BRASS, width=1)
        text(d, (x + 14, y + 10), "Hint: send the team in tunnel %d (glowing)." % (highlight_q + 1), font("sans", 13), SAND)
        pill(d, (x1 - 150, y + 28, x1 - 80, y + 52), "Do it", True, font("sans_b", 12))
        pill(d, (x1 - 70, y + 28, x1 - 12, y + 52), "OK", False, font("sans_b", 12))
        y += 68
    tool_button(d, (x, y, (x + x1) / 2 - 5, y + 44), "Undo")
    tool_button(d, ((x + x1) / 2 + 5, y, x1, y + 44), "Hint")
    y += 78
    slider(d, x, y, x1, speed_frac, speed_label)
    y += 48
    shown = {tr.claim.tile for tr in sch.trips if tr.home <= t}
    m = mini(board, lv["rows"], shown, scale=1)
    m = m.resize((int(m.width * 140 / m.height * S / S), P(140)), Image.NEAREST) if False else m
    mh = min(P(H - 32) - P(y) - P(8), P(150))
    if mh > P(60):
        m = m.resize((int(m.width * mh / m.height), int(mh)), Image.NEAREST)
        img.paste(m, (P(x), P(y)))
        d.rectangle([P(x), P(y), P(x) + m.width, P(y) + m.height], outline=(168, 119, 42), width=P(2))
        text(d, (x + m.width / S + 12, y + 4), "NEST GALLERY", font("sans_bb", 12), BRASS)
        tx = x + m.width / S + 12
        text(d, (tx, y + 24), "Every tile carried home is", font("sans", 13), SAND_DIM)
        text(d, (tx, y + 42), "re-laid down here, in place.", font("sans", 13), SAND_DIM)
    return img, g, sch, t, (bx, by, cell), nants


def jam_overlay(img, g):
    W, H = img.width / S, img.height / S
    ov = Image.new("RGBA", img.size, (0, 0, 0, 115))
    img.alpha_composite(ov)
    d = ImageDraw.Draw(img, 'RGBA')
    cw, ch = 440, 470
    x0, y0 = (W - cw) / 2 - 150, (H - ch) / 2
    rrect(d, (x0, y0, x0 + cw, y0 + ch), 22, fill=PANEL, outline=DANGER, width=2)
    text(d, (x0 + cw / 2, y0 + 26), "\u26a0", font("sym", 30), DANGER, "ma")
    text(d, (x0 + cw / 2, y0 + 66), "The colony is blocked", font("serif", 26), SAND, "ma")
    text(d, (x0 + cw / 2, y0 + 108), "Every one of the %d slots holds a team waiting" % g.state.capacity, font("sans", 14), SAND_DIM, "ma")
    text(d, (x0 + cw / 2, y0 + 128), "for tiles it can't reach yet, so no team can be sent.", font("sans", 14), SAND_DIM, "ma")
    yy = y0 + 160
    pill(d, (x0 + 24, yy, x0 + cw - 24, yy + 44), "Undo the last move", True); yy += 54
    pill(d, (x0 + 24, yy, x0 + cw - 24, yy + 44), "Add a slot", False); yy += 60
    text(d, (x0 + 24, yy), "Or open a slot — tap a waiting team to return it to its tunnel:", font("sans", 13), SAND_DIM); yy += 26
    for i, tm in enumerate(g.state.chambers):
        pod(img, (x0 + 24 + i * 62, yy, x0 + 78 + i * 62, yy + 54), tm.family, tm.remaining)
    d = ImageDraw.Draw(img, 'RGBA')
    yy += 72
    pill(d, (x0 + cw / 2 - 190, yy, x0 + cw / 2 - 70, yy + 44), "Hint", False)
    pill(d, (x0 + cw / 2 - 60, yy, x0 + cw / 2 + 60, yy + 44), "Restart", False)
    pill(d, (x0 + cw / 2 + 70, yy, x0 + cw / 2 + 190, yy + 44), "Home", False)


RATING_WORDS = ["Relaxed", "Steady", "Tricky", "Hard", "Fiendish"]
RATING_COLS = [OK, (156, 196, 90), BRASS, (224, 128, 58), DANGER]


def level_rating(lv, diff_index):
    from generate_levels import rating
    return rating(lv["careless"][diff_index], lv["greedy"][diff_index])


def rating_dots(d, x, y, level, size=9):
    for k in range(5):
        col = RATING_COLS[level - 1] if k < level else EDGE
        d.ellipse([P(x + k * (size + 3)), P(y), P(x + k * (size + 3) + size), P(y + size)], fill=col)


def level_thumb(rows, pal=None, h=100):
    board = Board(rows)
    allt = {i for i in range(board.N) if board.family[i] >= 0}
    m = mini(board, rows, allt, pal, scale=1)
    w = m.width * h / m.height
    return m.resize((P(w), P(h)), Image.NEAREST), w


def versus_screen(lv, layout, stop_at=60.0):
    """Two-player mockup from a real reference-model match (versus.py) at game time `stop_at`."""
    import random as _r
    import versus as V
    from render import draw_hill
    tunnels = [[tuple(x) for x in t] for t in lv["tunnels"]]
    m = V.VMatch(lv["rows"], tunnels, lv["classic"], layout, "reach3", "any", "upkeep")
    keep = {}
    V.play_timed(m, _r.Random(4), stop_at=stop_at, keep=keep)
    scheds, t = keep["schedulers"], keep["t"]
    W, H = 1180, 820
    img = Image.new("RGBA", (P(W), P(H)), LOAM + (255,))
    d = ImageDraw.Draw(img, 'RGBA')
    PCOL = [(63, 182, 200), (240, 138, 93)]
    text(d, (20, 16), "\u2715", font("sym", 18), SAND_DIM)
    text(d, (52, 18), "%s · %s · Reach 3 · Any colour · Slot upkeep · Classic" % (lv["title"], "Race" if layout == "race" else "Shared board"),
         font("sans", 12), SAND_DIM)
    rrect(d, (W - 300, 22, W - 90, 28), 3, fill=EDGE)
    rrect(d, (W - 300, 22, W - 220, 28), 3, fill=BRASS)
    text(d, (W - 60, 16), "2.0×", font("sans_bb", 12), SAND)

    def board_img(i, cs):
        board = m.boards[i].board
        im, _ = board_image(lv, board, scheds[i], t, cs, hill=(layout == "race"))
        if layout == "shared":
            for p, h in enumerate(V.shared_holes(board)):
                draw_hill(im, board.C, board.R, cs, (h % board.C, h // board.C))
            dd = ImageDraw.Draw(im, 'RGBA')
            for p, h in enumerate(V.shared_holes(board)):
                cx, cy = (h % board.C + 0.5) * cs, (h // board.C + 0.5) * cs
                dd.ellipse([cx - 1.4 * cs, cy - 0.9 * cs, cx + 1.4 * cs, cy + 0.9 * cs], outline=PCOL[p] + (255,), width=3)
            # player rings under ants: redraw ants' rings lightly
            for tr in scheds[i].trips:
                ps = pose(board, tr, t)
                if ps:
                    owner = tr.claim.team // V.PLAYER_BASE
                    r = cs * 0.62
                    dd.ellipse([ps["x"] * cs - r, ps["y"] * cs - r, ps["x"] * cs + r, ps["y"] * cs + r], outline=PCOL[owner] + (230,), width=2)
        return im

    def controls(p, x0, y0, x1):
        dd = ImageDraw.Draw(img, 'RGBA')
        pl = m.players[p]
        dd.ellipse([P(x0), P(y0 + 4), P(x0 + 12), P(y0 + 16)], fill=PCOL[p])
        text(dd, (x0 + 18, y0), "Player %d" % (p + 1), font("serif", 17), SAND)
        home = sum(1 for tr in scheds[m.bidx(p)].trips if tr.home <= t and tr.claim.team // V.PLAYER_BASE == p)
        home += sum(1 for c in range(m.boards[m.bidx(p)].board.N) if m.boards[m.bidx(p)].owner[c] == p) - \
            sum(1 for tr in scheds[m.bidx(p)].trips if tr.claim.team // V.PLAYER_BASE == p)
        pen = m.penalties(p)
        score = home - pen
        text(dd, (x1 - 30, y0 - 2), "%d" % round(score), font("sans_bb", 24), PCOL[p], "ra")
        text(dd, (x1, y0 + 8), "pts", font("sans", 11), SAND_DIM, "ra")
        text(dd, (x0, y0 + 24), "%d tiles home · −%d penalties" % (home, round(pen)), font("sans", 10), SAND_DIM)
        y = y0 + 44
        waiting = m.waiting(p)
        working = sorted({tr.claim.team for tr in scheds[m.bidx(p)].trips if tr.pickup_end > t and tr.claim.team // V.PLAYER_BASE == p}
                         - {w.uid for w in waiting})
        occ = len(waiting) + len(working)
        text(dd, (x0, y + 12), "%d of %d open" % (max(0, pl.capacity - occ), pl.capacity), font("sans_bb", 10), BRASS if occ >= pl.capacity else OK)
        px = x0 + 62
        for uid in working:
            fam = next(tr.claim.family for tr in scheds[m.bidx(p)].trips if tr.claim.team == uid)
            left = sum(1 for tr in scheds[m.bidx(p)].trips if tr.claim.team == uid and tr.pickup_end > t)
            pod(img, (px, y, px + 38, y + 38), fam, left); px += 43
        for w in waiting:
            pod(img, (px, y, px + 38, y + 38), w.family, w.remaining)
            dd = ImageDraw.Draw(img, 'RGBA')
            rrect(dd, (px, y, px + 38, y + 38), 12, outline=BRASS, width=2)
            return_badge(dd, px + 36, y + 2, 15); px += 43
        dd = ImageDraw.Draw(img, 'RGBA')
        for _ in range(max(0, pl.capacity - occ)):
            rrect(dd, (px, y, px + 38, y + 38), 12, fill=LOAM_R, outline=EDGE, width=1); px += 43
        rrect(dd, (px, y, px + 38, y + 38), 12, outline=BRASS, width=1.5)
        text(dd, (px + 19, y + 12), "+", font("sans_bb", 13), BRASS, "mm")
        text(dd, (px + 19, y + 27), "−25", font("sans_bb", 9), BRASS, "mm")
        y += 48
        nq = len(pl.queues)
        colw = (x1 - x0 - 6 * (nq - 1)) / nq
        for q in range(nq):
            cx0 = x0 + q * (colw + 6)
            yy = y
            for dpt, team in enumerate(pl.queues[q][:7]):
                if dpt < 3:
                    hh = 54 if dpt == 0 else 42
                    ok = m.check(p, q, dpt)[0] and occ < pl.capacity
                    team_card(img, (cx0, yy, cx0 + colw, yy + hh), team.family, team.remaining, dimmed=not ok)
                    dd = ImageDraw.Draw(img, 'RGBA')
                    if dpt > 0:
                        rrect(dd, (cx0 + colw - 30, yy + 3, cx0 + colw - 3, yy + 17), 7, fill=(0, 0, 0, 140))
                        text(dd, (cx0 + colw - 16, yy + 10), "−%d" % (3 * dpt), font("sans_bb", 9), (255, 255, 255), "mm")
                    yy += hh + 4
                else:
                    team_card(img, (cx0, yy, cx0 + colw, yy + 20), team.family, team.remaining)
                    yy += 24
            dd = ImageDraw.Draw(img, 'RGBA')
            if len(pl.queues[q]) > 7:
                text(dd, (cx0 + colw / 2, yy), "+%d" % (len(pl.queues[q]) - 7), font("sans_bb", 10), SAND_DIM, "ma")

    if layout == "race":
        colw = (W - 30) / 2
        for p in (0, 1):
            x0 = 10 + p * (colw + 10)
            dd = ImageDraw.Draw(img, 'RGBA')
            rrect(dd, (x0, 44, x0 + colw, H - 10), 18, fill=PANEL, outline=PCOL[p] + (180,), width=2)
            board = m.boards[p].board
            cs = min((colw - 20) / board.C, 380 / board.R)
            bim = board_img(p, max(4, int(round(P(cs)))))
            bx = x0 + (colw - board.C * cs) / 2
            img.paste(bim.resize((P(board.C * cs), P(board.R * cs))), (P(bx), P(52)))
            controls(p, x0 + 12, 52 + board.R * cs + 10, x0 + colw - 12)
    else:
        side = 330
        board = m.boards[0].board
        cs = min((W - 2 * side - 40) / board.C, (H - 60) / board.R)
        bim = board_img(0, max(4, int(round(P(cs)))))
        bx = (W - board.C * cs) / 2
        img.paste(bim.resize((P(board.C * cs), P(board.R * cs))), (P(bx), P(48)))
        for p, x0 in ((0, 10), (1, W - side - 10)):
            dd = ImageDraw.Draw(img, 'RGBA')
            rrect(dd, (x0, 44, x0 + side, H - 10), 18, fill=PANEL, outline=PCOL[p] + (180,), width=2)
            controls(p, x0 + 12, 56, x0 + side - 12)
    return img


PACK_ORDER = [("main", "MOSAICS"), ("garden", "GARDEN"), ("challenge", "CHALLENGE"), ("master", "MASTER")]
MOCK_DONE = {"firstDig", "nestingRings"}          # the mockup player has finished these


def mock_state(lv):
    key = lv["key"]
    if key in MOCK_DONE:
        return "done"
    lock = {"peacockFan": "Koi Pond", "nightMarket": "Peacock Fan"}
    if key in lock:
        return "locked:" + lock[key]
    return "open"


def person_icon(d, x, y, col, s_=1.0):
    d.ellipse([P(x + 6 * s_), P(y), P(x + 16 * s_), P(y + 10 * s_)], fill=col)
    d.rounded_rectangle([P(x + 2 * s_), P(y + 12 * s_), P(x + 20 * s_), P(y + 26 * s_)], radius=P(7 * s_), fill=col)


def trophy_icon(d, x, y, col):
    d.rounded_rectangle([P(x + 3), P(y), P(x + 21), P(y + 13)], radius=P(5), fill=col)
    d.rectangle([P(x + 10), P(y + 12), P(x + 14), P(y + 20)], fill=col)
    d.rounded_rectangle([P(x + 5), P(y + 20), P(x + 19), P(y + 25)], radius=P(2), fill=col)
    d.arc([P(x - 3), P(y + 1), P(x + 8), P(y + 11)], 90, 270, fill=col, width=P(2.5))
    d.arc([P(x + 16), P(y + 1), P(x + 27), P(y + 11)], 270, 90, fill=col, width=P(2.5))


def home_top(img, d, W, x, difficulty_index, filt):
    """Header, the two big buttons and the filter bar (mirrors HomeView)."""
    text(d, (x, 26), "Tessera Colony", font("serif", 40), SAND)
    text(d, (x, 80), "Send the colony out. Carry the mosaic home, one tile at a time.", font("sans", 15), SAND_DIM)
    text(d, (W - x - 64, 44), "?", font("sans_bb", 22), SAND_DIM, "mm")
    d.ellipse([P(W - x - 76), P(32), P(W - x - 52), P(56)], outline=SAND_DIM, width=P(2))
    text(d, (W - x - 18, 44), "\u2699", font("sym", 24), SAND_DIM, "mm")
    # big buttons
    y0, y1 = 112, 196
    half = (W - 2 * x - 14) / 2
    rrect(d, (x, y0, x + half, y1), 20, fill=BRASS)
    person_icon(d, x + 20, y0 + 28, (42, 28, 18)); person_icon(d, x + 34, y0 + 30, (42, 28, 18), 0.9)
    text(d, (x + 72, y0 + 18), "Two players", font("serif", 23), (42, 28, 18))
    text(d, (x + 72, y0 + 52), "Race or share a board on one iPad", font("sans", 13), (70, 50, 30))
    text(d, (x + half - 22, (y0 + y1) / 2), "\u203a", font("sans_bb", 26), (42, 28, 18), "mm")
    bx = x + half + 14
    rrect(d, (bx, y0, bx + half, y1), 20, fill=PANEL, outline=BRASS + (160,), width=1.5)
    trophy_icon(d, bx + 22, y0 + 30, SAND)
    text(d, (bx + 72, y0 + 18), "High scores", font("serif", 23), SAND)
    text(d, (bx + 72, y0 + 52), "Best scores and names per mosaic", font("sans", 13), SAND_DIM)
    text(d, (bx + half - 22, (y0 + y1) / 2), "\u203a", font("sans_bb", 26), SAND, "mm")
    # filter bar
    fy = 212
    rrect(d, (x, fy, W - x, fy + 124), 18, fill=PANEL, outline=EDGE)
    text(d, (x + 16, fy + 20), "DIFFICULTY", font("sans_bb", 12), BRASS)
    sx0, sw_ = x + 124, 420
    rrect(d, (sx0, fy + 12, sx0 + sw_, fy + 44), 9, fill=LOAM_R)
    for i, name in enumerate(["Gentle", "Classic", "Expert"]):
        c0 = sx0 + i * sw_ / 3
        if i == difficulty_index:
            rrect(d, (c0 + 3, fy + 15, c0 + sw_ / 3 - 3, fy + 41), 7, fill=(90, 74, 58))
        text(d, (c0 + sw_ / 6, fy + 28), name, font("sans_b", 13), SAND, "mm")
    text(d, (x + 16, fy + 64), "SHOW", font("sans_bb", 12), BRASS)
    cx = x + 124
    dots = {"All": None, "Easy": OK, "Medium": BRASS, "Hard": (224, 128, 58), "Fiendish": DANGER}
    for name, col in dots.items():
        w = 26 + len(name) * 8.5 + (16 if col else 0)
        on = name == filt
        rrect(d, (cx, fy + 54, cx + w, fy + 90), 18, fill=BRASS if on else LOAM_R, outline=None if on else EDGE)
        tx = cx + 14
        if col:
            d.ellipse([P(tx), P(fy + 68), P(tx + 9), P(fy + 77)], fill=col); tx += 15
        text(d, (tx, fy + 63), name, font("sans_bb", 13), (42, 28, 18) if on else SAND)
        cx += w + 8
    return fy + 124


def home_card(img, d_, levels, key, state, cx, cy, cw, ch, th, diff_index):
    d = d_[0]
    rrect(d, (cx, cy, cx + cw, cy + ch), 16, fill=PANEL, outline=EDGE)
    tm, tw = level_thumb(levels[key]["rows"], h=th)
    if tw > cw - 20:
        tm = tm.resize((P(cw - 20), P(th * (cw - 20) / tw)), Image.NEAREST); tw = cw - 20
    if state.startswith("locked"):
        g_ = tm.convert("L").convert("RGB")
        tm = Image.blend(g_, Image.new("RGB", g_.size, (40, 32, 26)), 0.45)
    img.paste(tm, (P(cx + (cw - tw) / 2), P(cy + 10)))
    dd = ImageDraw.Draw(img, 'RGBA')
    d_[0] = dd
    if state.startswith("locked"):
        text(dd, (cx + cw / 2, cy + 10 + th / 2), "LOCKED", font("sans_bb", 13), SAND, "mm")
    yy = cy + th + 18
    title = levels[key]["title"]
    text(dd, (cx + 10, yy), title if len(title) < 19 else title[:17] + "…", font("serif", 15), SAND)
    tiles = sum(1 for r in levels[key]["rows"] for c in r if c != ".")
    text(dd, (cx + 10, yy + 22), "%d tiles · %d teams" % (tiles, sum(len(t) for t in levels[key]["tunnels"])), font("sans", 10.5), SAND_DIM)
    r = level_rating(levels[key], diff_index)
    dn = ["Gentle", "Classic", "Expert"][diff_index]
    text(dd, (cx + 10, yy + 39), dn + ":", font("sans", 10.5), SAND_DIM)
    wx = cx + 16 + 6.2 * len(dn)
    text(dd, (wx, yy + 39), RATING_WORDS[r - 1], font("sans_bb", 10.5), RATING_COLS[r - 1])
    rating_dots(dd, wx + 7 * len(RATING_WORDS[r - 1]) + 4, yy + 42, r, size=7)
    by = yy + 60
    if state == "done":
        text(dd, (cx + 10, by - 2), "\u2713 Completed", font("sym", 10.5), OK)
        pill(dd, (cx + 10, by + 14, cx + 108, by + 38), "Play again…", False, font("sans_b", 10.5))
    elif state == "open":
        pill(dd, (cx + 10, by + 6, cx + 80, by + 34), "Play…", True, font("sans_b", 11.5))
    else:
        text(dd, (cx + 10, by + 4), "Finish %s" % state.split(":")[1], font("sans_bb", 10.5), BRASS)
        text(dd, (cx + 10, by + 19), "to unlock", font("sans_bb", 10.5), BRASS)


def home_screen(levels_report, photo, out, difficulty_index=1, filt="All", H=1200):
    """Home (mockup): the top buttons, the filter, then each pack's mosaics that pass the filter."""
    W = 1180
    img = Image.new("RGBA", (P(W), P(H)), LOAM + (255,))
    d = ImageDraw.Draw(img, 'RGBA')
    x = 50
    levels = {l["key"]: l for l in levels_report["levels"]}
    y = home_top(img, d, W, x, difficulty_index, filt)
    ranges = {"All": (1, 5), "Easy": (1, 2), "Medium": (3, 3), "Hard": (4, 4), "Fiendish": (5, 5)}
    lo, hi = ranges[filt]
    shown_total = sum(1 for l in levels_report["levels"] if lo <= level_rating(l, difficulty_index) <= hi)
    dn = ["Gentle", "Classic", "Expert"][difficulty_index]
    note = ("New games start on %s; cards show how hard each mosaic is on %s. %d mosaics." % (dn, dn, len(levels))
            if filt == "All" else "Showing %d of %d mosaics rated %s on %s." % (shown_total, len(levels), filt, dn))
    text(d, (x + 16, y - 26), note, font("sans", 11.5), SAND_DIM)
    y += 18
    if filt == "All":
        rrect(d, (x, y, W - x, y + 70), 20, fill=PANEL, outline=BRASS, width=1.5)
        tm, tw = level_thumb(levels["koiPond"]["rows"], h=54)
        img.paste(tm, (P(x + 14), P(y + 8)))
        d = ImageDraw.Draw(img, 'RGBA')
        text(d, (x + 30 + tw, y + 10), "NEXT UP", font("sans_bb", 12), BRASS)
        text(d, (x + 30 + tw, y + 26), "Koi Pond", font("serif", 22), SAND)
        pill(d, (W - x - 130, y + 16, W - x - 16, y + 54), "Play…", True)
        y += 88
    cols = 5
    cw = (W - 2 * x - (cols - 1) * 12) / cols
    d_ = [d]
    blurbs = {"main": "Finish a mosaic to unlock the next · Sunflower & Monarch is open from the start",
              "garden": "Eight new pictures, the gentlest pack (most Relaxed or Steady on Classic) · unlocked by First Dig",
              "challenge": "Interlocking layers — one-step play fails on Classic and Expert · unlocked by First Dig",
              "master": "Eight busy pictures, the hardest: one-step play fails on Classic and Expert (6 of 8 on Gentle too) · unlocked by any Challenge mosaic"}
    for pack, title in PACK_ORDER:
        keys = [l["key"] for l in levels_report["levels"] if l.get("pack", "main") == pack
                and lo <= level_rating(l, difficulty_index) <= hi]
        if not keys:
            continue
        if y + 60 > H - 60:
            break
        dd = d_[0]
        total = sum(1 for l in levels_report["levels"] if l.get("pack", "main") == pack)
        done = sum(1 for l in levels_report["levels"] if l.get("pack", "main") == pack and l["key"] in MOCK_DONE)
        text(dd, (x, y), title, font("sans_bb", 13), DANGER if pack in ("challenge", "master") else BRASS)
        text(dd, (x + 12 + 10 * len(title), y + 1), "%d of %d finished · %s" % (done, total, blurbs[pack]), font("sans", 11), SAND_DIM)
        y += 22
        for i, key in enumerate(keys):
            r_, c_ = divmod(i, cols)
            cy = y + r_ * 256
            if cy + 244 > H - 50:
                dd = d_[0]
                text(dd, (x, cy + 4), "… scroll for %d more" % (len(keys) - i), font("sans_bb", 12), SAND_DIM)
                y = H
                break
            home_card(img, d_, levels, key, mock_state(levels[key]), x + c_ * (cw + 12), cy, cw, 244, 118, difficulty_index)
        else:
            y += ((len(keys) - 1) // cols + 1) * 256 + 12
            continue
        break
    return img


# ---------------------------------------------------------------------------
# Home: the collection (themes, pack shelves, found / explored / mastered)
# ---------------------------------------------------------------------------

COLL_THEMES = [("First Mosaics", ["main"]), ("Seasons", ["halloween", "winter"]),
               ("Nature", ["garden", "wild", "naturalist"]), ("Art", ["gallery", "worldart", "crafts"]),
               ("Literature", ["epics", "tales", "childrens", "stage", "adventure", "gothic", "novels"]),
               ("History", ["ancient", "voyages", "modern", "inventions"]), ("Sky & Science", ["cosmos", "space", "geometry"]),
               ("Tests of Skill", ["challenge", "master"])]
# seasonal packs and the dates they are in season (mirrors LevelCatalog.seasons)
COLL_SEASONS = {"halloween": ((9, 20), (11, 7)), "winter": ((12, 1), (2, 28))}


def in_season(pack, month, day):
    if pack not in COLL_SEASONS:
        return False
    (fm, fd), (tm_, td) = COLL_SEASONS[pack]
    md, a, b = month * 100 + day, fm * 100 + fd, tm_ * 100 + td
    return a <= md <= b if a <= b else (md >= a or md <= b)
COLL_TITLES = {"main": "MOSAICS", "garden": "GARDEN", "wild": "WILD WONDERS", "gallery": "GALLERY", "worldart": "WORLD ART",
               "ancient": "ANCIENT WORLD", "voyages": "VOYAGES", "modern": "MODERN MOMENTS", "cosmos": "SKY & SCIENCE",
               "challenge": "CHALLENGE", "master": "MASTER", "epics": "EPICS & LEGENDS", "tales": "FAIRY TALES & FABLES",
               "childrens": "CHILDREN'S CLASSICS", "stage": "SHAKESPEARE", "adventure": "ADVENTURE CLASSICS",
               "gothic": "GOTHIC & MYSTERY", "novels": "GREAT NOVELS", "naturalist": "NATURAL HISTORY", "crafts": "WORLD CRAFT",
               "geometry": "GEOMETRY & ILLUSIONS", "space": "PROBES & TELESCOPES", "inventions": "INVENTIONS & FIRSTS",
               "halloween": "HALLOWEEN", "winter": "WINTER"}
COLL_BLURBS = {
    "main": "Finish a mosaic to unlock the next. Sunflower & Monarch is open from the start.",
    "garden": "Eight gentle pictures, from a hot-air balloon to a desert bloom. Opens after First Dig.",
    "wild": "Natural wonders, from the Northern Lights to a coral reef. Gentlest to hardest. Opens after First Dig.",
    "gallery": "Famous paintings as mosaics — Monet, Vermeer, Leonardo, Munch, Van Gogh, Seurat, Klimt. Opens after First Dig.",
    "worldart": "Hokusai, Hiroshige, a Ming vase, Kandinsky, the Sun Stone, Ravenna, Alhambra, Mondrian. Opens after any Gallery mosaic.",
    "ancient": "Lascaux to the Colosseum. Gentlest to hardest. Opens after First Dig.",
    "voyages": "Wayfinders to the South Pole. Opens after any Ancient World mosaic.",
    "modern": "The first flight to the Berlin Wall. Opens after any Voyages mosaic.",
    "cosmos": "An eclipse to the periodic table. Opens after any Wild Wonders mosaic.",
    "challenge": "Interlocking layers — one-step play fails on Classic and Expert. Opens after First Dig.",
    "master": "The hardest mosaics. Opens after any Challenge mosaic.",
    "epics": "The Sirens, the Trojan Horse, the sword in the stone, Ali Baba's cave… Gentlest to hardest. Opens after First Dig.",
    "tales": "Red Riding Hood, Jack's beanstalk, the gingerbread house… Gentlest to hardest. Opens after First Dig.",
    "childrens": "The yellow brick road, the Mad Tea-Party, Pinocchio… Opens after any Fairy Tales mosaic.",
    "stage": "The balcony, Yorick, Macbeth's witches, the Globe… Opens after any Epics & Legends mosaic.",
    "adventure": "Crusoe's footprint, the white whale, the treasure map… Opens after any Children's Classics mosaic.",
    "gothic": "The Raven, the Headless Horseman, Castle Dracula… Opens after any Adventure Classics mosaic.",
    "novels": "Gatsby's green light, Miss Havisham, the Netherfield ball… Opens after any Shakespeare mosaic.",
    "naturalist": "Audubon's flamingo, Haeckel's jellyfish, a beetle drawer… Opens after any Garden mosaic.",
    "crafts": "A Talavera plate, Delft tiles, a tartan, a Persian carpet… Opens after any World Art mosaic.",
    "geometry": "The impossible triangle, the Mandelbrot set, a Celtic knot… Opens after any Challenge mosaic.",
    "space": "Earthrise, Pluto's heart, the Hubble Deep Field… Opens after any Sky & Science mosaic.",
    "inventions": "The penny-farthing, the light bulb, Babbage's engine… Opens after any Modern Moments mosaic.",
    "halloween": "Seasonal (late Sept – early Nov): a jack-o'-lantern, a black cat, a spider's web… Opens after First Dig.",
    "winter": "Seasonal (Dec – Feb): a snowman, Bentley's snowflake, a snow globe… Opens after First Dig."}
# the mockup player: stars (1 Gentle .. 3 Expert) and most harder options used on Expert
MOCK_PROGRESS = {"firstDig": (2, 0), "koiPond": (1, 0), "gardenBalloon": (3, 2), "gardenLighthouse": (2, 0),
                 "gardenToadstools": (1, 0), "wildAurora": (1, 0), "gallerySunrise": (3, 0), "galleryLilyPond": (1, 0),
                 "nestingRings": (1, 0), "ancientLascaux": (2, 0), "talesRedRidingHood": (2, 0), "epicsTrojanHorse": (1, 0),
                 "halloJackOLantern": (2, 0)}
MOCK_SAVES = {"galleryPearl": 14}


def coll_packs(levels_report):
    packs = {}
    for l in levels_report["levels"]:
        packs.setdefault(l.get("pack", "main"), []).append(l)
    return packs


def coll_rule(pack, packs):
    first = (["firstDig"], "First Dig")
    rules = {"garden": first, "wild": first, "gallery": first, "ancient": first, "challenge": first,
             "epics": first, "tales": first, "halloween": first, "winter": first,
             "naturalist": ([l["key"] for l in packs.get("garden", [])], "any Garden mosaic"),
             "crafts": ([l["key"] for l in packs.get("worldart", [])], "any World Art mosaic"),
             "space": ([l["key"] for l in packs.get("cosmos", [])], "any Sky & Science mosaic"),
             "geometry": ([l["key"] for l in packs.get("challenge", [])], "any Challenge mosaic"),
             "inventions": ([l["key"] for l in packs.get("modern", [])], "any Modern Moments mosaic"),
             "childrens": ([l["key"] for l in packs.get("tales", [])], "any Fairy Tales mosaic"),
             "adventure": ([l["key"] for l in packs.get("childrens", [])], "any Children's Classics mosaic"),
             "stage": ([l["key"] for l in packs.get("epics", [])], "any Epics & Legends mosaic"),
             "gothic": ([l["key"] for l in packs.get("adventure", [])], "any Adventure Classics mosaic"),
             "novels": ([l["key"] for l in packs.get("stage", [])], "any Shakespeare mosaic"),
             "worldart": ([l["key"] for l in packs.get("gallery", [])], "any Gallery mosaic"),
             "voyages": ([l["key"] for l in packs.get("ancient", [])], "any Ancient World mosaic"),
             "modern": ([l["key"] for l in packs.get("voyages", [])], "any Voyages mosaic"),
             "cosmos": ([l["key"] for l in packs.get("wild", [])], "any Wild Wonders mosaic"),
             "master": ([l["key"] for l in packs.get("challenge", [])], "any Challenge mosaic")}
    return rules.get(pack)


def coll_status(lv, packs, progress=MOCK_PROGRESS, saves=MOCK_SAVES):
    """Mirrors AppModel.status(of:) in Collection.swift."""
    key, pack = lv["key"], lv.get("pack", "main")
    chain = {"koiPond": ("firstDig", "First Dig"), "peacockFan": ("koiPond", "Koi Pond"), "nightMarket": ("peacockFan", "Peacock Fan")}
    if key in chain and chain[key][0] not in progress:
        return ("locked", chain[key][1])
    if pack != "main":
        keys, label = coll_rule(pack, packs)
        if not any(k in progress for k in keys):
            return ("locked", label)
        order = [l["key"] for l in packs[pack]]
        limit = 3 + sum(1 for k in order if k in progress)
        i = order.index(key)
        if key not in progress and key not in saves and i >= limit:
            return ("hidden", max(1, i - limit + 1))
    if key in progress:
        stars, mods = progress[key]
        return ("mastered", 3) if mods > 0 and stars == 3 else ("explored", stars)
    return ("found", saves.get(key, 0))


def flame_icon(d, x, y, s, col):
    pts = [(x + 0.5 * s, y), (x + 0.85 * s, y + 0.45 * s), (x + 0.95 * s, y + 0.75 * s), (x + 0.5 * s, y + s),
           (x + 0.05 * s, y + 0.75 * s), (x + 0.2 * s, y + 0.4 * s), (x + 0.35 * s, y + 0.55 * s)]
    d.polygon([(P(a), P(b)) for a, b in pts], fill=col)


def star_row(d, x, y, stars, mastered=False, size=12):
    f = font("sym", size)
    for k in range(3):
        text(d, (x + k * (size + 2), y), "★" if k < stars else "☆", f, BRASS if k < stars else EDGE)
    if mastered:
        flame_icon(d, x + 3 * (size + 2) + 1, y + 1, size, DANGER)


def coll_progress(levels, packs, progress=MOCK_PROGRESS):
    total = len(levels); found = explored = stars = mastered = 0; open_ = False
    for l in levels:
        st = coll_status(l, packs, progress)
        if st[0] != "locked":
            open_ = True
        if st[0] in ("found", "explored", "mastered"):
            found += 1
        if st[0] in ("explored", "mastered"):
            explored += 1; stars += st[1]
        if st[0] == "mastered":
            mastered += 1
    return dict(total=total, found=found, explored=explored, stars=stars, mastered=mastered, open=open_)


def coll_card(img, d_, lv, st, cx, cy, diff_index):
    d = d_[0]
    rrect(d, (cx, cy, cx + 150, cy + 170), 10, fill=(42, 32, 25))
    border = {"found": BRASS, "mastered": DANGER, "explored": EDGE}.get(st[0], EDGE)
    if st[0] == "locked":
        text(d, (cx + 75, cy + 70), "\U0001F512" if False else "LOCKED", font("sans_bb", 12), SAND_DIM, "mm")
        text(d, (cx + 75, cy + 94), "Opens after", font("sans_b", 10.5), SAND_DIM, "mm")
        text(d, (cx + 75, cy + 110), st[1] if len(st[1]) < 22 else st[1][:20] + "…", font("sans_b", 10.5), SAND_DIM, "mm")
    elif st[0] == "hidden":
        text(d, (cx + 75, cy + 70), "?", font("serif", 44), SAND_DIM, "mm")
        text(d, (cx + 75, cy + 112), "Finish %d more" % st[1], font("sans_b", 10.5), SAND_DIM, "mm")
        text(d, (cx + 75, cy + 127), "in this pack", font("sans_b", 10.5), SAND_DIM, "mm")
    else:
        tm, tw = level_thumb(lv["rows"], h=158)
        if tw > 138:
            tm = tm.resize((P(138), P(158 * 138 / tw)), Image.NEAREST); th = 158 * 138 / tw; tw = 138
        else:
            th = 158
        img.paste(tm, (P(cx + (150 - tw) / 2), P(cy + (170 - th) / 2)))
        d = ImageDraw.Draw(img, 'RGBA'); d_[0] = d
        if st[0] == "found":
            lab = "IN PROGRESS" if st[1] else "NEW"
            w = 18 + 7.2 * len(lab)
            rrect(d, (cx + 6, cy + 6, cx + 6 + w, cy + 24), 9, fill=SAND if st[1] else BRASS)
            text(d, (cx + 6 + w / 2, cy + 15), lab, font("sans_bb", 9.5), (42, 28, 18), "mm")
        if st[0] == "mastered":
            d.ellipse([P(cx + 6), P(cy + 6), P(cx + 30), P(cy + 30)], fill=LOAM + (220,))
            flame_icon(d, cx + 11, cy + 10, 14, DANGER)
    rrect(d, (cx, cy, cx + 150, cy + 170), 10, outline=border, width=2)
    title = {"locked": "Locked", "hidden": "Undiscovered"}.get(st[0], lv["title"])
    text(d, (cx, cy + 178), title if len(title) < 21 else title[:19] + "…", font("serif", 14.5),
         SAND if st[0] not in ("locked", "hidden") else SAND_DIM)
    if st[0] not in ("locked", "hidden"):
        rating_dots(d, cx, cy + 204, level_rating(lv, diff_index), size=8)
        if st[0] in ("explored", "mastered"):
            star_row(d, cx + 96, cy + 199, st[1], st[0] == "mastered", size=11)


def coll_filter_bar(d, x, y, W, difficulty_index, rating, status, note):
    rrect(d, (x, y, W - x, y + 172), 18, fill=PANEL, outline=EDGE)
    text(d, (x + 16, y + 20), "DIFFICULTY", font("sans_bb", 12), BRASS)
    sx0, sw_ = x + 124, 420
    rrect(d, (sx0, y + 12, sx0 + sw_, y + 44), 9, fill=LOAM_R)
    for i, name in enumerate(["Gentle", "Classic", "Expert"]):
        c0 = sx0 + i * sw_ / 3
        if i == difficulty_index:
            rrect(d, (c0 + 3, y + 15, c0 + sw_ / 3 - 3, y + 41), 7, fill=(90, 74, 58))
        text(d, (c0 + sw_ / 6, y + 28), name, font("sans_b", 13), SAND, "mm")

    def chips(yy, items, on_name):
        cx = x + 124
        for name, col in items:
            w = 26 + len(name) * 8.5 + (16 if col else 0)
            on = name == on_name
            rrect(d, (cx, yy, cx + w, yy + 36), 18, fill=BRASS if on else LOAM_R, outline=None if on else EDGE)
            tx = cx + 14
            if col:
                d.ellipse([P(tx), P(yy + 14), P(tx + 9), P(yy + 23)], fill=col); tx += 15
            text(d, (tx, yy + 9), name, font("sans_bb", 13), (42, 28, 18) if on else SAND)
            cx += w + 8
    text(d, (x + 16, y + 64), "SHOW", font("sans_bb", 12), BRASS)
    chips(y + 54, [("All", None), ("Easy", OK), ("Medium", BRASS), ("Hard", (224, 128, 58)), ("Fiendish", DANGER)], rating)
    text(d, (x + 16, y + 110), "STATUS", font("sans_bb", 12), BRASS)
    chips(y + 100, [("All", None), ("To explore", None), ("Explored", None), ("Go harder", None), ("Mastered", None)], status)
    text(d, (x + 16, y + 148), note, font("sans", 11.5), SAND_DIM)
    return y + 172


def collection_home(levels_report, difficulty_index=1, rating="All", status="All", H=2200, next_key="galleryPearl",
                    only_themes=None, season_day=(10, 3)):
    """Home (mockup) with the collection: summary, theme chips, filters, then themes of pack shelves."""
    W = 1180
    img = Image.new("RGBA", (P(W), P(H)), LOAM + (255,))
    d = ImageDraw.Draw(img, 'RGBA')
    x = 50
    levels = {l["key"]: l for l in levels_report["levels"]}
    packs = coll_packs(levels_report)
    # header and the two big buttons (home_top draws the old filter bar too: cover it)
    home_top(img, d, W, x, difficulty_index, rating)
    d.rectangle([P(0), P(206), P(W), P(345)], fill=LOAM)
    y = 212
    # next up
    rrect(d, (x, y, W - x, y + 76), 20, fill=PANEL, outline=BRASS, width=1.5)
    tm, tw = level_thumb(levels[next_key]["rows"], h=60)
    img.paste(tm, (P(x + 14), P(y + 8)))
    d = ImageDraw.Draw(img, 'RGBA')
    text(d, (x + 30 + tw, y + 12), "NEXT UP", font("sans_bb", 12), BRASS)
    text(d, (x + 30 + tw, y + 28), levels[next_key]["title"], font("serif", 22), SAND)
    pill(d, (W - x - 140, y + 19, W - x - 16, y + 57), "Resume…" if next_key in MOCK_SAVES else "Play…", True)
    y += 94
    # the collection card
    allp = coll_progress(levels_report["levels"], packs)
    chips_ = []
    cx, row = x + 16, 0
    for title, pids in COLL_THEMES:
        tp = coll_progress([l for p in pids for l in packs.get(p, [])], packs)
        lab = "%s %d/%d" % (title, tp["explored"], tp["total"])
        w = 30 + 7.4 * len(lab)
        if cx + w > W - x - 16:
            cx, row = x + 16, row + 1
        chips_.append((cx, row, w, lab, tp["open"]))
        cx += w + 8
    card_h = 150 + 36 * row
    rrect(d, (x, y, W - x, y + card_h), 18, fill=PANEL, outline=EDGE)
    text(d, (x + 16, y + 14), "YOUR COLLECTION", font("sans_bb", 13), BRASS)
    text(d, (W - x - 16, y + 16), "★ Gentle · ★★ Classic · ★★★ Expert · flame = Expert with a harder option",
         font("sym", 10.5), SAND_DIM, "ra")
    figs = [("%d" % allp["found"], "of %d found" % allp["total"]), ("%d" % allp["explored"], "explored"),
            ("%d" % allp["stars"], "of %d stars" % (3 * allp["total"])), ("%d" % allp["mastered"], "mastered")]
    fw = (W - 2 * x - 32) / 4
    for i, (v, cap) in enumerate(figs):
        fx = x + 16 + i * fw
        text(d, (fx, y + 40), v, font("sans_bb", 22), SAND)
        text(d, (fx, y + 72), cap, font("sans", 12), SAND_DIM)
    bar_w = W - 2 * x - 32
    rrect(d, (x + 16, y + 96, x + 16 + bar_w, y + 102), 3, fill=LOAM_R)
    rrect(d, (x + 16, y + 96, x + 16 + bar_w * allp["stars"] / (3 * allp["total"]), y + 102), 3, fill=BRASS)
    for cx, row, w, lab, open_ in chips_:
        yy = y + 112 + 36 * row
        rrect(d, (cx, yy, cx + w, yy + 28), 14, fill=LOAM_R, outline=BRASS + (150,) if open_ else EDGE)
        text(d, (cx + 14, yy + 6), lab, font("sans_b", 12), SAND)
    y += card_h + 18
    # filters
    shown = [l for l in levels_report["levels"] if coll_status(l, packs)[0] not in ("locked", "hidden")]
    lo, hi = {"All": (1, 5), "Easy": (1, 2), "Medium": (3, 3), "Hard": (4, 4), "Fiendish": (5, 5)}[rating]

    def passes(l):
        st = coll_status(l, packs)
        if st[0] in ("locked", "hidden"):
            return rating == "All" and status == "All"
        if not (lo <= level_rating(l, difficulty_index) <= hi):
            return False
        return {"All": True, "To explore": st[0] == "found", "Explored": st[0] in ("explored", "mastered"),
                "Go harder": st[0] == "explored", "Mastered": st[0] == "mastered"}[status]
    dn = ["Gentle", "Classic", "Expert"][difficulty_index]
    filtering = rating != "All" or status != "All"
    n_shown = sum(1 for l in shown if passes(l))
    note = ("Showing %d of %d mosaics (only ones you have found)." % (n_shown, len(levels)) if filtering else
            "New games start on %s; the dots on each card show how hard it is on %s. %d mosaics." % (dn, dn, len(levels)))
    y = coll_filter_bar(d, x, y, W, difficulty_index, rating, status, note) + 22
    d_ = [d]
    for title, pids in COLL_THEMES:
        if only_themes and title not in only_themes:
            continue
        tl = [l for p in pids for l in packs.get(p, [])]
        if not any(passes(l) for l in tl):
            continue
        if y + 80 > H - 60:
            break
        d = d_[0]
        tp = coll_progress(tl, packs)
        text(d, (x, y), title, font("serif", 26), SAND)
        text(d, (W - x, y + 10), "%d of %d explored · %d ★" % (tp["explored"], tp["total"], tp["stars"]), font("sym", 12), SAND_DIM, "ra")
        y += 46
        for pid in pids:
            ls = [l for l in packs.get(pid, []) if passes(l)]
            if not ls:
                continue
            if y + 290 > H - 50:
                text(d_[0], (x, y), "… scroll for more", font("sans_bb", 12), SAND_DIM)
                y = H
                break
            d = d_[0]
            pp = coll_progress(packs[pid], packs)
            t = COLL_TITLES[pid]
            text(d, (x, y), t, font("sans_bb", 13), DANGER if pid in ("challenge", "master") else BRASS)
            badge = 0
            if in_season(pid, *season_day):
                bx = x + 14 + 9.6 * len(t)
                rrect(d, (bx, y - 2, bx + 78, y + 17), 9, fill=BRASS)
                text(d, (bx + 39, y + 7.5), "IN SEASON", font("sans_bb", 9.5), (42, 28, 18), "mm")
                badge = 88
            if not pp["open"]:
                line = "Opens after %s" % coll_rule(pid, packs)[1]
            else:
                line = "%d of %d found · %d explored · %d of %d ★" % (pp["found"], pp["total"], pp["explored"], pp["stars"], 3 * pp["total"])
                if pp["mastered"]:
                    line += " · %d mastered" % pp["mastered"]
            text(d, (x + 14 + 9.6 * len(t) + badge, y + 1), line, font("sym", 11), SAND_DIM)
            rrect(d, (x, y + 24, x + 320, y + 28), 2, fill=LOAM_R)
            if pp["explored"]:
                rrect(d, (x, y + 24, x + 320 * pp["explored"] / pp["total"], y + 28), 2, fill=BRASS)
            text(d, (x, y + 36), COLL_BLURBS[pid], font("sans", 11.5), SAND_DIM)
            cy = y + 62
            for i, l in enumerate(ls):
                cx = x + i * 164
                if cx > W - 20:
                    break
                coll_card(img, d_, l, coll_status(l, packs), cx, cy, difficulty_index)
            # the shelf scrolls sideways: fade the right edge
            fade = Image.new("RGBA", (P(60), P(230)), (0, 0, 0, 0))
            for k in range(P(60)):
                ImageDraw.Draw(fade).line([(k, 0), (k, P(230))], fill=LOAM + (int(255 * k / P(60)),))
            img.alpha_composite(fade, (P(W - 60), P(cy - 4)))
            d_[0] = ImageDraw.Draw(img, 'RGBA')
            y = cy + 238
        else:
            y += 10
            continue
        break
    return img


MODS = [("hiddenQueue", "Hidden queue", 20), ("noScout", "No scouting", 10), ("noHints", "No hints", 10),
        ("limitedUndo", "3 undos", 20), ("noAssists", "No assists", 15), ("noRepeatColour", "No colour twice", 25)]


def start_sheet(levels_report, key="labyrinth", selected=1, mods=("noHints", "limitedUndo")):
    """The start sheet (mockup): difficulty, harder options, this mosaic's high scores; pinned Start."""
    import scoring
    W, H = 1180, 1130
    img = Image.new("RGBA", (P(W), P(H)), (14, 10, 8, 255))
    d = ImageDraw.Draw(img, 'RGBA')
    levels = {l["key"]: l for l in levels_report["levels"]}
    lv = levels[key]
    sx0, sx1, sy0 = 250, 930, 30
    rrect(d, (sx0, sy0, sx1, H - 64), 26, fill=LOAM, outline=EDGE, width=1.5)
    tm, tw = level_thumb(lv["rows"], h=110)
    img.paste(tm, (P(sx0 + 28), P(sy0 + 24)))
    d = ImageDraw.Draw(img, 'RGBA')
    tx = sx0 + 46 + tw
    text(d, (tx, sy0 + 26), lv.get("pack", "main").upper(), font("sans_bb", 12), DANGER)
    text(d, (tx, sy0 + 44), lv["title"], font("serif", 28), SAND)
    text(d, (tx, sy0 + 82), lv["subtitle"], font("sans", 13), SAND_DIM)
    tiles = sum(1 for r in lv["rows"] for c in r if c != ".")
    text(d, (tx, sy0 + 104), "%d tiles · %d teams · %d tunnels" % (tiles, sum(len(t) for t in lv["tunnels"]), len(lv["tunnels"])),
         font("sans", 12), SAND_DIM)
    text(d, (sx1 - 40, sy0 + 40), "\u2715", font("sym", 18), SAND_DIM, "mm")
    y = sy0 + 152
    text(d, (sx0 + 28, y), "CHOOSE A DIFFICULTY", font("sans_bb", 13), BRASS)
    y += 24
    blurbs = ["Extra slots, and each tunnel tells you whether its team can finish now.",
              "The intended challenge. Scout, plan, undo freely.",
              "Only the slots the designed solution needs — little room to wait."]
    expl = ["Almost any order works.", "A little care goes a long way.",
            "Send teams that can finish now and you'll get there.",
            "Sending whatever can finish now isn't enough — think a few moves ahead.",
            "Needs a real plan: scout, count slots, and use undo."]
    for i, (name, slots) in enumerate((("Gentle", lv["gentle"]), ("Classic", lv["classic"]), ("Expert", lv["expert"]))):
        sel = i == selected
        hbox = 126 if sel else 72
        box = (sx0 + 28, y, sx1 - 28, y + hbox)
        rrect(d, box, 16, fill=LOAM_R if sel else PANEL, outline=BRASS if sel else EDGE, width=2.5 if sel else 1)
        cx, cy = sx0 + 56, y + 26
        d.ellipse([P(cx - 11), P(cy - 11), P(cx + 11), P(cy + 11)], outline=BRASS if sel else SAND_DIM, width=P(2))
        if sel:
            d.ellipse([P(cx - 6), P(cy - 6), P(cx + 6), P(cy + 6)], fill=BRASS)
        text(d, (sx0 + 80, y + 12), name, font("serif", 20), SAND)
        text(d, (sx1 - 46, y + 16), "%d slots" % slots, font("sans_bb", 14), BRASS, "ra")
        yy = y + 42
        if sel:
            text(d, (sx0 + 80, yy), blurbs[i], font("sans", 13), SAND_DIM); yy += 24
        r = level_rating(lv, i)
        rating_dots(d, sx0 + 80, yy + 4, r, size=10)
        text(d, (sx0 + 150, yy), RATING_WORDS[r - 1], font("sans_bb", 14), RATING_COLS[r - 1])
        text(d, (sx0 + 160 + 9 * len(RATING_WORDS[r - 1]), yy + 1), "· careless tapping wins %d%%" % round(100 * lv["careless"][i]),
             font("sans", 13), SAND_DIM)
        if sel:
            text(d, (sx0 + 80, yy + 26), expl[r - 1], font("sans", 13), SAND)
        y += hbox + 10
    # harder options
    y += 8
    df = [0.5, 1.0, 1.5][selected]
    mf = scoring.solo_score(100, "classic", mods, 0, 0, 0)["mf"]
    text(d, (sx0 + 28, y), "HARDER OPTIONS", font("sans_bb", 13), BRASS)
    text(d, (sx1 - 28, y - 1), "Score ×%.2f" % (df * mf), font("sans_bb", 14), SAND, "ra")
    y += 26
    colw = (sx1 - sx0 - 56 - 8) / 2
    for i, (mk, title, bonus) in enumerate(MODS):
        r_, c_ = divmod(i, 2)
        bx0 = sx0 + 28 + c_ * (colw + 8); by0 = y + r_ * 52
        on = mk in mods
        rrect(d, (bx0, by0, bx0 + colw, by0 + 44), 12, fill=LOAM_R if on else PANEL, outline=BRASS if on else EDGE, width=2 if on else 1)
        rrect(d, (bx0 + 12, by0 + 13, bx0 + 30, by0 + 31), 4, fill=BRASS if on else None, outline=None if on else SAND_DIM, width=1.5)
        if on:
            text(d, (bx0 + 21, by0 + 22), "\u2713", font("sym", 12), (42, 28, 18), "mm")
        text(d, (bx0 + 42, by0 + 12), title, font("sans_b", 14), SAND)
        text(d, (bx0 + colw - 12, by0 + 14), "+%d%%" % bonus, font("sans_bb", 12), BRASS if on else SAND_DIM, "ra")
    y += 3 * 52 + 4
    text(d, (sx0 + 28, y), "No hints: the hint button is off.  3 undos: only 3 undos for the whole game.", font("sans", 12), SAND_DIM)
    y += 34
    # high scores
    text(d, (sx0 + 28, y), "HIGH SCORES", font("sans_bb", 13), BRASS)
    y += 24
    t_ = sum(1 for r in lv["rows"] for c in r if c != ".")
    rows_ = [("Ana", scoring.solo_score(t_, "expert", ("limitedUndo",), 3, 0, 0)["score"], "Expert + 3 undos", "9:41", ("limitedUndo",)),
             ("Sam", scoring.solo_score(t_, "classic", (), 2, 0, 0)["score"], "Classic", "12:05", ()),
             ("Kai", scoring.solo_score(t_, "gentle", (), 0, 1, 0)["score"], "Gentle", "7:58", ())]
    for i, (nm, sc, how, tm_, ms) in enumerate(rows_):
        yy = y + i * 30
        text(d, (sx0 + 44, yy), "%d" % (i + 1), font("sans_bb", 13), BRASS if i == 0 else SAND_DIM, "ra")
        text(d, (sx0 + 56, yy), nm, font("sans_b", 14), SAND)
        text(d, (sx0 + 110, yy + 2), how, font("sans", 11), SAND_DIM)
        text(d, (sx1 - 120, yy + 1), tm_, font("sans", 12), SAND_DIM, "ra")
        text(d, (sx1 - 36, yy), "{:,}".format(sc), font("sans_bb", 15), SAND, "ra")
    # pinned start button
    d.rectangle([P(sx0 + 1), P(H - 144), P(sx1 - 1), P(H - 66)], fill=LOAM_R)
    d.line([P(sx0 + 1), P(H - 144), P(sx1 - 1), P(H - 144)], fill=EDGE, width=P(1))
    pill(d, (sx0 + 28, H - 128, sx1 - 28, H - 84), "Start on %s · %d harder" % (["Gentle", "Classic", "Expert"][selected], len(mods)), True, font("sans_bb", 16))
    return img


def finish_card(levels_report, key="firstDig", difficulty="expert", mods=("noHints", "limitedUndo"), undos=3, name="Ana"):
    """The finish card with a new high score and the name box (mockup)."""
    import scoring
    W, H = 1180, 920
    lv = next(l for l in levels_report["levels"] if l["key"] == key)
    board = Board(lv["rows"])
    allt = {i for i in range(board.N) if board.family[i] >= 0}
    img = Image.new("RGBA", (P(W), P(H)), LOAM + (255,))
    bg = mini(board, lv["rows"], allt, scale=1)
    bh = H - 40
    bw = bg.width * bh / bg.height
    bg = bg.resize((P(bw), P(bh)), Image.NEAREST)
    img.paste(bg, (P((W - bw) / 2), P(20)))
    img.alpha_composite(Image.new("RGBA", img.size, (0, 0, 0, 130)))
    d = ImageDraw.Draw(img, 'RGBA')
    exit_button(d, 36, 36)
    cw, ch = 480, 736
    x0, y0 = (W - cw) / 2, (H - ch) / 2
    rrect(d, (x0, y0, x0 + cw, y0 + ch), 24, fill=PANEL, outline=BRASS, width=2)
    m = mini(board, lv["rows"], allt, scale=1)
    mh = 120
    m = m.resize((int(m.width * P(mh) / m.height), P(mh)), Image.NEAREST)
    img.paste(m, (int(P(x0 + cw / 2) - m.width / 2), P(y0 + 22)))
    d = ImageDraw.Draw(img, 'RGBA')
    d.rectangle([int(P(x0 + cw / 2) - m.width / 2), P(y0 + 22), int(P(x0 + cw / 2) + m.width / 2), P(y0 + 22 + mh)], outline=BRASS, width=P(3))
    y = y0 + 22 + mh + 14
    text(d, (x0 + cw / 2, y), "Re-laid in the nest", font("serif", 26), SAND, "ma"); y += 40
    mastered = difficulty == "expert" and len(mods) > 0
    star_row(d, x0 + cw / 2 - 40, y - 2, 3 if difficulty == "expert" else 2, mastered, size=18); y += 30
    text(d, (x0 + cw / 2, y), "%s tiles carried home · %s · %d harder options" % ("{:,}".format(board.tile_count), difficulty.title(), len(mods)),
         font("sans", 13), SAND_DIM, "ma"); y += 24
    if mastered:
        flame_icon(d, x0 + cw / 2 - 150, y + 1, 15, BRASS)
        text(d, (x0 + cw / 2 + 10, y), "Mastered — Expert with a harder option!", font("sans_bb", 14), BRASS, "ma")
    y += 30
    stats = [("TIME", "6:12"), ("MOVES", str(len(lv["solution"]))), ("UNDOS", str(undos)), ("HINTS", "0"), ("ASSISTS", "0")]
    for i, (k, v) in enumerate(stats):
        cx = x0 + 60 + i * 90
        text(d, (cx, y), v, font("sans_bb", 20), SAND, "ma")
        text(d, (cx, y + 28), k, font("sans_bb", 10), SAND_DIM, "ma")
    y += 56
    sc = scoring.solo_score(board.tile_count, difficulty, mods, undos, 0, 0)
    rrect(d, (x0 + 20, y, x0 + cw - 20, y + 250), 16, fill=LOAM_R + (200,))
    text(d, (x0 + cw / 2 - 60, y + 22), "SCORE", font("sans_bb", 12), BRASS, "ra")
    text(d, (x0 + cw / 2 - 48, y + 10), "{:,}".format(sc["score"]), font("sans_bb", 28), SAND)
    text(d, (x0 + cw / 2, y + 54), "%s tiles × %g %s × %.2f harder options − %d undos"
         % ("{:,}".format(board.tile_count), sc["df"], difficulty.title(), sc["mf"], sc["undo"]), font("sans", 12), SAND_DIM, "ma")
    trophy_icon(d, x0 + 96, y + 80, BRASS)
    text(d, (x0 + 132, y + 82), "New high score on %s!" % lv["title"], font("sans_bb", 15), BRASS)
    rrect(d, (x0 + 36, y + 120, x0 + cw - 130, y + 164), 12, fill=LOAM_R, outline=BRASS, width=1.5)
    text(d, (x0 + 50, y + 131), name + "|", font("sans_b", 16), SAND)
    pill(d, (x0 + cw - 120, y + 120, x0 + cw - 36, y + 164), "Save", True)
    text(d, (x0 + cw / 2, y + 180), "Previous best: 1,512 by Sam (Expert) — now #2", font("sans", 12), SAND_DIM, "ma")
    text(d, (x0 + cw / 2, y + 204), "Tap the box, type your name, then Save.", font("sans", 12), SAND_DIM, "ma")
    y += 266
    names = {m[0]: m[1] for m in MODS}
    nxt = next((m[0] for m in MODS if m[0] not in mods), None)
    harder = {"gentle": "Try it on Classic", "classic": "Try it on Expert"}.get(difficulty) or ("Expert + " + names[nxt] if nxt else None)
    if harder:
        pill(d, (x0 + cw / 2 - 120, y, x0 + cw / 2 + 120, y + 44), harder, False)
        y += 56
    pill(d, (x0 + 40, y, x0 + 180, y + 44), "Nest gallery", False)
    pill(d, (x0 + 190, y, x0 + 310, y + 44), "Play again", False)
    pill(d, (x0 + 320, y, x0 + cw - 40, y + 44), "Next mosaic", True)
    return img


def portrait_screen(lv, n_moves, t_after):
    W, H = 820, 1180
    img = Image.new("RGBA", (P(W), P(H)), LOAM + (255,))
    d = ImageDraw.Draw(img, 'RGBA')
    board, g, sch, t = state_at(lv, n_moves, 3.0, t_after)
    panel_h = 480
    cell = math.floor(min((W - 24) / board.C, (H - panel_h - 30) / board.R) * 2) / 2
    cs = P(cell)
    bim, _ = board_image(lv, board, sch, t, cs)
    bx = (W - board.C * cell) / 2; by = 12
    img.paste(bim, (P(bx), P(by)))
    rrect(d, (bx, by, bx + board.C * cell, by + board.R * cell), 12, outline=EDGE, width=1)
    exit_button(d, 30, 30)
    # zoom inset (pinch-to-zoom illustration)
    zx, zy, zw = 0, 0, 240
    ants = [(pose(board, tr, t), tr) for tr in sch.trips]
    ants = [(p, tr) for p, tr in ants if p]
    if ants:
        carriers = [a for a in ants if a[0]["carrying"] and a[0]["y"] < board.R - 8] or ants
        def isolation(a):
            return min((math.hypot(a[0]["x"] - b[0]["x"], a[0]["y"] - b[0]["y"]) for b in ants if b is not a), default=9)
        p0 = max(carriers, key=lambda a: min(isolation(a), 2.2) * 10 + a[0]["y"] * 0.01)[0]
        cx, cy = p0["x"], p0["y"]
        big = P(34)
        sub_rows = lv["rows"]
        inset = board_image(lv, board, sch, t, big)[0]
        ix0 = int((cx - 3.5) * big); iy0 = int((cy - 3.5) * big)
        ix0 = max(0, min(inset.width - P(zw), ix0)); iy0 = max(0, min(inset.height - P(zw), iy0))
        crop = inset.crop((ix0, iy0, ix0 + P(zw), iy0 + P(zw)))
        ox, oy = W - zw - 24, by + 16
        img.paste(crop, (P(ox), P(oy)))
        rrect(d, (ox, oy, ox + zw, oy + zw), 8, outline=BRASS, width=3)
        text(d, (ox + zw / 2, oy + zw + 6), "Pinch to zoom: ants crawl, feet plant and lift", font("sans_b", 11), SAND, "ma")
    y = by + board.R * cell + 12
    panel_frame(d, (12, y, W - 12, H - 12))
    x = 26; x1 = W - 26; y += 14
    text(d, (x, y), "Sunflower & Monarch", font("serif", 20), SAND)
    text(d, (x, y + 28), "Classic · %d moves" % len(g.moves), font("sans", 13), SAND_DIM)
    y += 54
    items = slot_items(g, sch, t)
    n_free = sum(1 for it in items if it[0] == "open")
    text(d, (x, y), "SLOTS", font("sans_bb", 12), SAND_DIM)
    text(d, (x + 52, y), "%d of %d open" % (n_free, len(items)), font("sans_bb", 12), OK if n_free else BRASS)
    y += 20
    cxp = x
    for kind, f, n in items:
        box = (cxp, y, cxp + 52, y + 52)
        if kind == "open":
            pod(img, box)
            d = ImageDraw.Draw(img, 'RGBA')
            text(d, (cxp + 26, y + 26), "Open", font("sans_bb", 11), OK, "mm")
        else:
            pod(img, box, f, n)
            d = ImageDraw.Draw(img, 'RGBA')
            text(d, (cxp + 26, y + 56), kind.capitalize(), font("sans_bb", 10),
                 {"working": SAND, "waiting": BRASS, "held": SAND_DIM}[kind], "ma")
            if kind == "waiting":
                return_badge(d, cxp + 49, y + 3, 16)
        cxp += 60
    d = ImageDraw.Draw(img, 'RGBA')
    rrect(d, (cxp, y, cxp + 52, y + 52), 14, outline=BRASS, width=1.5)
    text(d, (cxp + 26, y + 20), "+", font("sans_bb", 18), BRASS, "mm")
    text(d, (cxp + 26, y + 38), "Slot", font("sans_bb", 10), BRASS, "mm")
    y += 76
    nq = len(g.tunnels); colw = (x1 - x - 10 * (nq - 1)) / nq
    n_open = sum(1 for it in items if it[0] == "open")
    for q in range(nq):
        cx0 = x + q * (colw + 10)
        text(d, (cx0 + colw / 2, y), "TUNNEL %d · %d left" % (q + 1, len(g.tunnels[q]) - g.state.heads[q]), font("sans_bb", 11), SAND_DIM, "ma")
        fr = g.front(g.state, q)
        if fr:
            team_card(img, (cx0, y + 20, cx0 + colw, y + 100), fr[0], fr[1], dimmed=(n_open == 0))
            h = g.state.heads[q]
            for k, (f, n) in enumerate(g.tunnels[q][h + 1:h + 4]):
                team_card(img, (cx0, y + 108 + k * 30, cx0 + colw, y + 134 + k * 30), f, n)
    d = ImageDraw.Draw(img, 'RGBA')
    y += 206
    tool_button(d, (x, y, (x + x1) / 2 - 5, y + 50), "Undo")
    tool_button(d, ((x + x1) / 2 + 5, y, x1, y + 50), "Hint")
    y += 84
    slider(d, x, y, x1, 0.25, "0.35×")
    return img


def photo_flow(photo_src_path, photo, out_size=(1180, 820)):
    W, H = out_size
    img = Image.new("RGBA", (P(W), P(H)), LOAM + (255,))
    d = ImageDraw.Draw(img, 'RGBA')
    text(d, (40, 30), "Photo to playable mosaic", font("serif", 30), SAND)
    text(d, (40, 74), "1. Choose a photo    2. The white background becomes open ground    3. Colours become families with shaded tones    4. Teams and tunnels are planned so it can be solved", font("sans", 12), SAND_DIM)
    src = Image.open(photo_src_path).convert("RGB")
    sh = 560; sw = int(src.width * sh / src.height)
    img.paste(src.resize((P(sw), P(sh))), (P(40), P(120)))
    text(d, (40 + sw / 2, 120 + sh + 10), "Your photo", font("sans_b", 13), SAND_DIM, "ma")
    text(d, (40 + sw + 30, 120 + sh / 2), "\u2192", font("sym", 40), BRASS, "mm")
    board = Board(photo["rows"])
    cs = P(7)
    lvlike = {"rows": photo["rows"]}
    tunnels = [[tuple(x) for x in t] for t in photo["tunnels"]]
    g = Game(board, tunnels, photo["chambers"]["classic"])
    sch = Scheduler(board, "natural")
    now = 0.0
    for m, q in enumerate(photo["solution"][:3]):
        ev = g.dispatch(q); sch.schedule(ev, m, now); now += 3.0
    bim, _ = board_image({"rows": photo["rows"]}, board, sch, now + 14, cs, palette=photo["palette"])
    bh = 600; bw = bim.width / S * bh / (bim.height / S)
    bim = bim.resize((P(bw), P(bh)), Image.LANCZOS)
    ox = 40 + sw + 70
    img.paste(bim, (P(ox), P(110)))
    text(d, (ox + bw / 2, 110 + bh + 8), "Playable mosaic: %d tiles in %d colours, %d teams" % (photo["tiles"], len(photo["palette"]), sum(len(t) for t in photo["tunnels"])), font("sans_b", 13), SAND_DIM, "ma")
    # palette strip
    px0 = ox + bw + 30
    text(d, (px0, 120), "COLOUR FAMILIES", font("sans_bb", 12), BRASS)
    pal = [[hex_to_rgb(c) for c in fam] for fam in photo["palette"]]
    for i, fam in enumerate(pal):
        sw_ = swatch((140, 36), i, 12, pal, radius=8)
        img.alpha_composite(sw_, (P(px0), P(146 + i * 50)))
    text(d, (px0, 146 + len(pal) * 50 + 10), "Team pieces are made of", font("sans", 12), SAND_DIM)
    text(d, (px0, 146 + len(pal) * 50 + 28), "the same tones; no symbols.", font("sans", 12), SAND_DIM)
    return img


def main():
    rep = json.load(open(sys.argv[1]))
    out = sys.argv[2]
    photo = json.load(open(sys.argv[3])) if len(sys.argv) > 3 else None
    photo_src = sys.argv[4] if len(sys.argv) > 4 else None
    os.makedirs(out, exist_ok=True)
    lv = next(l for l in rep["levels"] if l["key"] == "sunflower")
    # 1. active play: several teams working, one waiting, the hint glowing
    img, g, sch, t, geo, nants = game_screen_landscape(
        lv, 12, 14.0, "Active play", highlight_q=lv["solution"][12],
        event_text="Tunnel 2: team of 72 sent — every tile is reachable;\nits slot opens when the ants have picked them all up.")
    mockup_stamp(img, "Active play, iPad landscape")
    img.convert("RGB").save(os.path.join(out, "01_active_play_ipad_landscape.png"))
    print("active play ants on board:", nants, "slots:", slot_items(g, sch, t))
    # 2. blocked recovery
    img, g, sch, t, geo, _ = game_screen_landscape(lv, 20, 0.0, "Blocked", jam=True)
    if g.deadlocked():
        jam_overlay(img, g)
    print("blocked:", g.deadlocked(), [(c.family, c.remaining) for c in g.state.chambers])
    mockup_stamp(img, "Recovery when blocked")
    img.convert("RGB").save(os.path.join(out, "02_blocked_recovery.png"))
    # 3. home / collection
    img = home_screen(rep, photo, out)
    mockup_stamp(img, "Home: Two players and High scores at the top, difficulty filter, packs")
    img.convert("RGB").save(os.path.join(out, "03_home_collection.png"))
    img = home_screen(rep, photo, out, difficulty_index=2, filt="Fiendish", H=1000)
    mockup_stamp(img, "Home filtered: Fiendish on Expert")
    img.convert("RGB").save(os.path.join(out, "09_home_filter_fiendish.png"))
    # 3b. start sheet with difficulty selection, harder options and high scores
    img = start_sheet(rep, "labyrinth", 1)
    mockup_stamp(img, "Start card: difficulty, harder options, high scores")
    img.convert("RGB").save(os.path.join(out, "06_difficulty_selection.png"))
    img = finish_card(rep)
    mockup_stamp(img, "Finish: score and a new high score with your name")
    img.convert("RGB").save(os.path.join(out, "10_high_score_entry.png"))
    # 3c. two players
    lvfd = next(l for l in rep["levels"] if l["key"] == "firstDig")
    img = versus_screen(lvfd, "race", 70.0)
    mockup_stamp(img, "Two players: race, split screen")
    img.convert("RGB").save(os.path.join(out, "07_two_player_race.png"))
    img = versus_screen(lvfd, "shared", 70.0)
    mockup_stamp(img, "Two players: shared board")
    img.convert("RGB").save(os.path.join(out, "08_two_player_shared.png"))
    # 4. portrait layout
    img = portrait_screen(lv, 30, 20.0)
    mockup_stamp(img, "iPad portrait layout")
    img.convert("RGB").save(os.path.join(out, "04_ipad_portrait.png"))
    # 5. photo flow
    if photo and photo_src:
        img = photo_flow(photo_src, photo)
        mockup_stamp(img, "Photo-to-puzzle")
        img.convert("RGB").save(os.path.join(out, "05_photo_to_puzzle.png"))


if __name__ == "__main__":
    main()
