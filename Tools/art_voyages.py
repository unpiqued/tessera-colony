"""Voyages pack: eight pictures of great voyages and discoveries, drawn with the supersampled Canvas
of art.py (a tile's colour family comes from the dominant object under it, its tone from the shading).

Gentle: Polynesian wayfinders, a Viking longship, a Silk Road caravan, Zheng He's treasure ship.
Challenge: Gutenberg's press, Galileo and Jupiter's moons.
Master (busy, every colour in many islands): Darwin's Galapagos, the race to the South Pole.
"""
import math
import random

import numpy as np

from art import Canvas, LAPIS, SAFFRON, FERN, EMBER, UMBER, PEARL, encode, smoothstep
from art_scenes import ALL, ellipse, rect, tube, frame, sky, cloud, smooth_noise


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------

def sparkle(c, x, y, s=1.0, fam=SAFFRON, shade=0.05, prio=1.6):
    """A four-pointed star (a plus of tiles when centred on a tile centre)."""
    m = (c.circle(x, y, 0.55 * s) | c.line_mask([(x - s, y), (x + s, y)], 0.5 * s)
         | c.line_mask([(x, y - s), (x, y + s)], 0.5 * s))
    c.paint(m, fam, shade, prio)


def bezier(p0, p1, p2, n=16):
    return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
             (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]) for t in np.linspace(0, 1, n)]


def crab_claw(c, apex, left, right, depth, bow=1.2):
    """A Polynesian crab-claw sail: point at the bottom, two curved spars, a deep concave top edge.
    Returns (sail mask, spar polylines)."""
    def spar(tip, sgn):
        mid = ((apex[0] + tip[0]) / 2 + sgn * bow, (apex[1] + tip[1]) / 2)
        return bezier(apex, mid, tip)
    ls, rs = spar(left, -1), spar(right, 1)
    top = bezier(left, ((left[0] + right[0]) / 2, (left[1] + right[1]) / 2 + depth), right)
    return c.poly_mask(ls + top[1:] + rs[::-1][1:]), (ls, rs)


def voronoi(c, seeds):
    """Nearest / second-nearest seed distances and the nearest seed's index."""
    d1 = np.full(c.X.shape, 99.0)
    d2 = np.full(c.X.shape, 99.0)
    idx = np.zeros(c.X.shape, int)
    for i, (sx, sy) in enumerate(seeds):
        d = np.hypot(c.X - sx, c.Y - sy)
        closer = d < d1
        d2 = np.where(closer, d1, np.minimum(d2, d))
        idx = np.where(closer, i, idx)
        d1 = np.where(closer, d, d1)
    return d1, d2, idx


def camel(c, x, y, s, bundles, robe):
    """A laden camel and rider walking left, feet on ground level y (about 12.5*s tiles tall)."""
    by = y - 5.2 * s

    def P(dx, dy):
        return (x + dx * s, by + dy * s)
    body = ellipse(c, *P(0, 0), 3.1 * s, 1.9 * s) | ellipse(c, *P(0.3, -1.6), 2.0 * s, 1.6 * s)
    neck = tube(c, [P(-2.4, -0.3), P(-4.1, 0.1), P(-5.2, -1.4), P(-5.5, -3.0)], 1.7 * s, 1.2 * s)
    head = ellipse(c, *P(-6.2, -3.2), 1.35 * s, 0.8 * s, 0.2)
    legs = np.zeros_like(c.X, bool)
    for (lx, sw) in ((-2.1, -0.9), (-1.2, 0.6), (1.5, -0.7), (2.3, 0.8)):
        legs |= tube(c, [P(lx, 1.0), P(lx + sw * 0.4, 3.0), (x + (lx + sw) * s, y)], 1.05 * s, 0.85 * s)
    tail = tube(c, [P(3.0, -0.4), P(3.6, 1.6)], 0.6 * s, 0.5 * s)
    c.paint(body | neck | head | legs | tail, UMBER, 0.95, 1.4)
    # bright bundles slung behind and in front of the rider
    c.paint(c.poly_mask([P(0.9, -2.2), P(3.6, -1.6), P(3.4, 0.9), P(0.9, 0.9)]), bundles[0], 0.35, 1.6)
    c.paint(rect(c, *P(-2.1, -1.5), *P(-0.6, 0.6)), bundles[1], 0.3, 1.6)
    # the rider: robe, face and turban
    c.paint(ellipse(c, *P(0.1, -3.9), 1.05 * s, 1.6 * s), robe, 0.4, 1.6)
    c.paint(c.circle(*P(0.0, -6.0), 0.8 * s), UMBER, 0.7, 1.7)
    c.paint(ellipse(c, *P(0.1, -6.6), 1.05 * s, 0.6 * s), PEARL, 0.1, 1.75)


FINCH = {  # tile sprites of perched finches facing right (h head, o eye, B beak, b body, w wing, T tail, l leg)
    "thick": [".....hh..", "....hhoB.", "TTbbbbbB.", ".TTwwbb..", "....l...."],
    "thin": [".....hh..", "....hhoBB", "TTbbbbb..", ".TTwwbb..", "....l...."],
    "long": [".....hh..", "....hhoBB", "TTbbbbb.B", ".TTwwbb..", "....l...."],
}


def finch(c, x0, y0, beak, facing=1):
    """A Darwin's finch as a crisp tile sprite whose top-left tile is (x0, y0): a dark bird with a pale
    eye and a beak of the given kind (a thick yellow seed-cracker, a thin or a long grey prober)."""
    beak_col = (SAFFRON, 0.35) if beak == "thick" else (PEARL, 0.55)
    cols = {"h": (UMBER, 0.95), "b": (UMBER, 0.95), "T": (UMBER, 0.95), "l": (UMBER, 0.95), "w": (UMBER, 0.4),
            "o": (PEARL, 0.0), "B": beak_col}
    for j, row in enumerate(FINCH[beak]):
        for i, ch in enumerate(row if facing > 0 else row[::-1]):
            if ch in cols:
                c.paint(rect(c, x0 + i, y0 + j, x0 + i + 1, y0 + j + 1), *cols[ch], 2.0)


def crab(c, x, y, s=1.0):
    """A red Sally Lightfoot crab seen from above."""
    for side in (-1, 1):
        for k in (-0.6, 0.0, 0.6):
            c.paint(c.line_mask([(x + side * 0.9 * s, y + k * s), (x + side * 2.1 * s, y + k * 1.6 * s + 0.4 * s)],
                                0.45 * s), EMBER, 0.6, 1.7)
    c.paint(ellipse(c, x, y, 1.4 * s, 1.0 * s), EMBER, 0.3, 1.8)
    c.paint(c.circle(x - 0.5 * s, y - 0.8 * s, 0.35 * s) | c.circle(x + 0.5 * s, y - 0.8 * s, 0.35 * s), LAPIS, 0.3, 1.9)


def dog(c, x, y, coat, harness, s=1.0):
    """A sled dog in harness pulling to the left: a solid silhouette with pricked ears and a curled
    tail; (x, y) is the middle of its body."""
    def P(dx, dy):
        return (x + dx * s, y + dy * s)
    body = ellipse(c, *P(0, 0), 2.3 * s, 1.15 * s) | tube(c, [P(-1.6, -0.3), P(-2.4, -1.3)], 1.6 * s, 1.4 * s)
    head = c.circle(*P(-2.7, -1.6), 1.0 * s) | ellipse(c, *P(-3.7, -1.2), 0.85 * s, 0.5 * s, 0.2)
    ears = c.poly_mask([P(-3.2, -2.2), P(-2.9, -3.3), P(-2.3, -2.3)])
    legs = np.zeros_like(c.X, bool)
    for (lx, sw) in ((-1.6, -0.5), (-0.9, 0.2), (1.2, -0.4), (1.9, 0.3)):
        legs |= c.line_mask([P(lx, 0.4), P(lx + sw, 2.3)], 0.8 * s)
    tail = tube(c, [P(2.1, -0.4), P(2.9, -1.4), P(2.3, -2.2)], 1.0 * s, 0.8 * s)
    c.paint(body | head | ears | legs | tail, coat, 0.3 if coat == UMBER else 0.85, 1.6)
    c.paint(c.line_mask([P(-1.3, -1.1), P(-1.2, 1.0)], 0.7 * s) | c.line_mask([P(-1.2, -1.0), P(1.6, -1.0)], 0.6 * s),
            harness, 0.35, 1.7)
    c.paint(c.circle(*P(-2.9, -1.8), 0.3 * s), PEARL, 0.0, 1.9)


# ---------------------------------------------------------------------------
# Gentle
# ---------------------------------------------------------------------------

def wayfinders():
    """A double-hulled voyaging canoe with crab-claw sails under the moon and a rising star path."""
    c = Canvas(44, 40)
    X, Y = c.X, c.Y
    hz = 25.0
    # night sky, a little lighter at the horizon; the moon with a soft halo at the top right
    c.paint(ALL(c), LAPIS, np.clip(1.0 - 0.4 * smoothstep(6, hz, Y), 0, 1))
    mx, my = 37.5, 6.5
    c.paint(c.circle(mx, my, 5.8), LAPIS, 0.68, 1.0)
    c.paint(c.circle(mx, my, 3.4), PEARL, np.clip(0.05 + 0.3 * (np.hypot(X - mx - 1.0, Y - my - 0.8) < 1.2), 0, 1), 1.3)
    # the star path: bright stars rising from the horizon in an arc, joined by a faint trail
    path = [(2.5, 21.5), (4.5, 15.5), (6.5, 9.5), (9.5, 4.5), (15.5, 2.5)]
    c.paint(c.line_mask([(1.0, 25.5)] + path + [(21, 1.5)], 0.9), LAPIS, 0.4, 1.1)
    for (sx, sy) in path:
        sparkle(c, sx, sy, 1.1)
    for (sx, sy) in ((26.5, 3.5), (31.5, 16.5), (42.5, 15.5), (22.5, 19.5), (29.5, 1.5)):
        c.paint(c.circle(sx, sy, 0.5), PEARL, 0.05, 1.5)
    # a distant high island under the moon
    h = 5.0 * np.exp(-((X - 38.5) / 2.6) ** 2) + 2.2 * np.exp(-((X - 33) / 2.4) ** 2)
    c.paint((Y <= hz) & (Y > hz - h) & (h > 0.5), FERN, 0.9, 1.1)
    # sea with long swell lines and the moon's glitter path
    sea = Y > hz
    swell = np.sin(np.sqrt(np.clip(Y - hz, 0, None)) * 4.2 + np.sin(X * 0.21) * 1.2)
    c.paint(sea, LAPIS, np.clip(0.85 - 0.45 * (swell > 0.55), 0, 1))
    glint = sea & (np.abs(X - mx + 0.08 * (Y - hz)) < 0.9 + 0.12 * (Y - hz)) & (swell > 0.7)
    c.paint(glint, PEARL, 0.1, 1.2)
    # the two hulls (the far one shows its upswept ends), the lashed deck and a thatched hut
    def hull(x0, x1, top, bot):
        u = (X - (x0 + x1) / 2) / ((x1 - x0) / 2)
        return (np.abs(u) <= 1) & (Y >= top - 3.6 * u ** 6) & (Y <= bot - 5.6 * u ** 4)
    c.paint(hull(12, 42.5, 28.6, 31.0), UMBER, 0.95, 1.2)
    c.paint(rect(c, 12.5, 28.4, 37, 30.8), UMBER, np.clip(0.1 + 0.3 * ((X % 1.8) < 0.5), 0, 1), 1.2)
    hut = c.poly_mask([(20, 28.6), (20, 26), (23.5, 23.2), (27, 26), (27, 28.6)])
    c.paint(hut, SAFFRON, np.clip(0.55 + 0.35 * (Y > 26), 0, 1), 1.3)
    near = hull(4.5, 38, 30.8, 34.4)
    c.paint(near, UMBER, np.clip(0.6 + 0.35 * (Y > 32.2), 0, 1), 1.3)
    # two crab-claw sails on their masts
    for apex, left, right, depth in (((16.5, 29.5), (10, 11.5), (23.5, 6), 5.0),
                                     ((31, 29.5), (26, 9), (37, 14.5), 4.5)):
        sail, spars = crab_claw(c, apex, left, right, depth)
        seams = np.sin(np.arctan2(Y - apex[1], X - apex[0]) * 18) > 0.8
        c.paint(sail, SAFFRON, np.clip(0.18 + 0.25 * seams + 0.012 * (apex[1] - Y), 0, 1), 1.2)
        for sp in spars:
            c.paint(c.line_mask(sp, 0.75), UMBER, 0.9, 1.5)
        c.paint(c.line_mask([apex, (apex[0] + 0.8, apex[1] - 11)], 0.6), UMBER, 0.85, 1.4)
    frame(c)
    return encode(c.to_tiles())


def longship():
    """A Viking longship under a striped square sail, shields on the rail, below a fjord cliff."""
    c = Canvas(46, 38)
    X, Y = c.X, c.Y
    hz = 27.5
    sky(c, 0.42, 0.1, horizon=hz)
    cloud(c, [(30, 5.5, 1.8), (33, 4.5, 2.5), (36.5, 5.8, 1.7)], 0.3)
    # the fjord: a tall cliff on the left, a paler far wall on the right
    n = smooth_noise(c, 3, 0.7)
    cliff = c.poly_mask([(0, 4.5), (3, 3.2), (6.5, 4.0), (9.5, 3.4), (11, 6), (9.5, 9), (12, 12.5), (11, 17),
                         (13.5, 21), (13, 24.5), (15.5, hz + 0.5), (0, hz + 0.5)])
    c.paint(cliff, PEARL, np.clip(0.62 + 0.22 * n + 0.25 * (np.sin(Y * 1.1 + X * 0.3) > 0.7), 0, 1))
    forest = cliff & ~c.poly_mask([(0, 7.0), (3, 5.8), (6.5, 6.8), (10.5, 6.2), (11, 9), (0, 9)]) & (Y < 7.5)
    forest |= (X < 11) & (Y > 1.6 + 0.9 * np.abs(np.sin(X * 1.2))) & (Y < 5)
    c.paint(forest, FERN, np.clip(0.55 + 0.3 * (np.sin(X * 2.4) > 0.3), 0, 1), 1.1)
    far = c.poly_mask([(46, 13), (41, 16), (37, 21), (33, 24.5), (29, hz + 0.5), (46, hz + 0.5)])
    c.paint(far, PEARL, np.clip(0.3 + 0.1 * n, 0, 1))
    # grey-blue sea with long light streaks
    sea = Y > hz
    streak = np.sin(Y * 2.3 + np.sin(X * 0.35) * 1.4) > 0.75
    c.paint(sea, LAPIS, np.clip(0.55 + 0.25 * (Y - hz) / 10 - 0.3 * streak, 0, 1))
    # mast, yard and the big striped sail (billowing: the foot curves down in the middle)
    c.paint(c.line_mask([(23, 1.2), (23, 25)], 0.8), UMBER, 0.9, 1.4)
    foot = 19.5 + 1.6 * (1 - ((X - 23) / 11.5) ** 2)
    sail = (np.abs(X - 23) < 11.5 + 0.4 * np.sin((Y - 3.5) / 17 * math.pi)) & (Y > 3.8) & (Y < foot)
    stripe = np.floor((X - 11.5) / 2.9).astype(int) % 2
    bill = np.clip(0.12 + 0.25 * np.abs(X - 23) / 11.5, 0, 1)
    c.paint(sail & (stripe == 0), EMBER, np.clip(bill + 0.2, 0, 1), 1.2)
    c.paint(sail & (stripe == 1), PEARL, bill, 1.2)
    c.paint(c.line_mask([(10.5, 3.6), (35.5, 3.6)], 0.9), UMBER, 0.85, 1.5)
    # the hull: a long crescent with strakes, a curled stern and the dragon-head prow
    u = (X - 22) / 17
    top, bot = 24.2 - 2.4 * u ** 4, 29.4 - 5.0 * u ** 4
    hull = (np.abs(u) <= 1) & (Y >= top) & (Y <= bot)
    strake = np.floor((Y - top) / 1.25).astype(int) % 2
    c.paint(hull, UMBER, np.clip(0.5 + 0.3 * strake, 0, 1), 1.3)
    c.paint(tube(c, [(5.4, 23.5), (4.0, 19.5), (3.7, 16.2), (4.8, 14.2), (6.5, 14.6), (6.6, 16.4), (5.4, 16.8)],
                 1.9, 1.0), UMBER, 0.75, 1.4)
    c.paint(tube(c, [(38.6, 23.2), (40.2, 19.5), (40.9, 16), (40.2, 13.2)], 2.2, 1.7), UMBER, 0.75, 1.4)
    head = c.poly_mask([(38.8, 13.6), (38.9, 11.4), (40.6, 10.1), (43.6, 10.9), (44.6, 12.2), (42.2, 12.5),
                        (44.3, 13.8), (41.4, 14.4)])
    c.paint(head, UMBER, 0.75, 1.5)
    c.paint(c.poly_mask([(39.2, 11.4), (38.2, 8.6), (40.6, 10.3)]), UMBER, 0.75, 1.5)
    c.paint(c.circle(41.3, 11.4, 0.55), SAFFRON, 0.1, 1.9)
    # round shields along the rail, three colours in turn, each with a dark boss
    cols = (SAFFRON, EMBER, PEARL)
    for k in range(10):
        sx = 9.4 + 2.75 * k
        sy = 24.2 - 2.4 * ((sx - 22) / 17) ** 4 + 0.2
        c.paint(c.circle(sx, sy, 1.35), cols[k % 3], 0.25 if cols[k % 3] != PEARL else 0.1, 1.6)
        c.paint(c.circle(sx, sy, 0.45), UMBER, 0.95, 1.9)
    # oars dipping into the water
    for ox in (13.5, 19, 24.5, 30):
        c.paint(c.line_mask([(ox, 27.5), (ox - 2.2, 32.6)], 0.65) & ~hull, UMBER, 0.8, 1.5)
    frame(c)
    return encode(c.to_tiles())


def silkroad():
    """A Silk Road caravan on a dune ridge at dusk, heading for a walled city (a caravanserai town)
    in front of the low sun."""
    c = Canvas(48, 36)
    X, Y = c.X, c.Y
    # dusk sky: deep blue above, a red glow lower down, the low sun
    c.paint(ALL(c), LAPIS, np.clip(0.9 - 0.45 * Y / 8, 0, 1))
    c.paint(Y > 7.5 + 0.8 * np.sin(X * 0.25), EMBER, np.clip(0.6 - 0.6 * (Y - 7) / 15, 0, 1))
    sx, sy = 7.0, 17.5
    c.paint(c.circle(sx, sy, 4.6), SAFFRON, np.clip(0.02 + 0.2 * (np.hypot(X - sx, Y - sy) > 3.3), 0, 1), 1.1)
    # the far plain and the walled city: towers, a dome, a minaret and a lit gate
    c.paint(Y > 24.8 + 0.4 * np.sin(X * 0.5), EMBER, 0.75, 1.0)
    tx = np.floor(X).astype(int)
    city = rect(c, 1, 22, 11, 25.5) | rect(c, 1, 19.5, 3.5, 25.5) | rect(c, 7.5, 19.5, 10, 25.5)
    city |= (rect(c, 1, 21, 11, 22) & (tx % 2 == 1)) | (ellipse(c, 5.5, 22.2, 2.2, 2.9) & (Y < 22.4))
    city |= (ellipse(c, 8.75, 19.6, 1.25, 1.6) & (Y < 19.8)) | (ellipse(c, 2.25, 19.6, 1.25, 1.6) & (Y < 19.8))
    c.paint(city, UMBER, 0.75, 1.3)
    c.paint(rect(c, 4.5, 23, 6.5, 25.5) | c.circle(5.5, 23, 1.0), SAFFRON, 0.1, 1.5)
    # the ridge the caravan walks on, its sunlit rippled face, the shadowed hollow below

    def ground(x):
        return np.where(x > 12, 24.5 - 0.09 * (x - 12), 24.5 + 0.45 * (12 - x))
    crest = ground(X)
    face = Y > crest
    ripple = np.sin((Y - crest) * 2.2 + X * 0.3) > 0.65
    c.paint(face, SAFFRON, np.clip(0.25 + 0.03 * (Y - crest) + 0.3 * ripple, 0, 1))
    hollow = face & (Y > 38 - 0.3 * X + 0.8 * np.sin(Y * 0.7))
    c.paint(hollow, UMBER, np.clip(0.05 + 0.3 * ripple, 0, 1), 1.0)
    # three laden camels with riders, roped nose to tail
    walkers = ((19.5, (LAPIS, SAFFRON), PEARL), (31.3, (FERN, PEARL), LAPIS), (43.1, (SAFFRON, LAPIS), FERN))
    for (x, bundles, robe) in walkers:
        camel(c, x, float(ground(x)), 1.1, bundles, robe)
    for (x0, x1) in ((19.5, 31.3), (31.3, 43.1)):
        c.paint(c.line_mask([(x0 + 3.8, float(ground(x0)) - 5.6), (x1 - 7.4, float(ground(x1)) - 9.0)], 0.4), UMBER, 0.9, 1.5)
    frame(c)
    return encode(c.to_tiles())


def treasureship():
    """Zheng He's treasure ship at three-quarters: a huge junk with many battened red sails and a
    high stern castle; smaller ships of the fleet on the horizon."""
    c = Canvas(42, 44)
    X, Y = c.X, c.Y
    tx, ty = np.floor(X).astype(int), np.floor(Y).astype(int)
    hz = 25.0
    sky(c, 0.5, 0.08, horizon=hz)
    cloud(c, [(3, 5.5, 1.5), (5.5, 4.6, 2.0), (8, 5.8, 1.4)], 0.1)
    # sea with swell lines and whitecaps
    sea = Y > hz
    dy = np.clip(Y - hz, 0, None)
    swell = np.sin(dy ** 0.8 * 3.0 + np.sin(X * 0.3) * 1.3)
    c.paint(sea, LAPIS, np.clip(0.45 + 0.35 * dy / 19 + 0.2 * (swell > 0.5), 0, 1))
    c.paint(sea & (swell > 0.93) & (np.sin(X * 0.7 + Y) > 0.2) & (Y > hz + 2), PEARL, 0.1, 1.2)
    # two smaller ships of the fleet on the horizon
    for (sx, sc) in ((3.8, 0.75), (8.8, 0.55)):
        c.paint(c.poly_mask([(sx - 3 * sc, hz - 0.9), (sx + 3 * sc, hz - 0.9), (sx + 2.2 * sc, hz + 0.6),
                             (sx - 2.2 * sc, hz + 0.6)]), UMBER, 0.8, 1.3)
        for k in (-1, 1):
            mx = sx + k * 1.3 * sc
            c.paint(rect(c, mx - 1.0 * sc, hz - 6.0 * sc, mx + 1.0 * sc, hz - 1.0 * sc), EMBER, 0.5, 1.3)
    # the sails, aft first so each one forward overlaps the next: fan-topped, battened, outlined
    sails = [(33.5, 11.5, 20.5, 5.5), (27.5, 8, 29.5, 6.5), (21.5, 4.5, 30, 7.5), (14.5, 2.5, 30.5, 8.5), (9.5, 12, 29.5, 6.5)]
    for i, (x0, top, bot, w) in enumerate(sails):
        c.paint(c.line_mask([(x0 - 0.4, bot + 2), (x0 - 0.4, top - 1.8)], 0.8), UMBER, 0.9, 1.4)
        c.paint(c.poly_mask([(x0 - 0.4, top - 1.9), (x0 + 1.9, top - 1.2), (x0 - 0.4, top - 0.5)]), SAFFRON, 0.2, 1.5)
        pts = [(x0, bot), (x0, top + 1.8), (x0 + w * 0.55, top), (x0 + w, top + 0.9), (x0 + w + 1.0, top + (bot - top) * 0.45),
               (x0 + w + 0.5, bot - 1.5), (x0 + w - 0.4, bot)]
        sail = c.poly_mask(pts)
        c.paint(sail, EMBER, np.clip(0.05 + 0.2 * (i % 2) + 0.15 * (X - x0) / w, 0, 1), 1.2)
        for k in range(1, 12):
            yl, yr = top + 1.8 + k * 2.6, top + 0.9 + k * 2.4
            if yl >= bot - 0.8:
                break
            c.paint(sail & c.line_mask([(x0, yl), (x0 + w + 1.2, yr)], 0.9), EMBER, 1.0, 1.3)
        c.paint(c.line_mask(pts + [pts[0]], 0.6), UMBER, 0.85, 1.35)
    # the hull: long and heavy, bow towards us, a gold band and a painted eye
    hull = c.poly_mask([(7.5, 29.5), (10, 31.8), (18, 32.5), (27, 32.0), (31, 30.8), (31.5, 22.5), (40.5, 21.5),
                        (40.5, 26.5), (39.5, 31), (37.5, 35), (31, 37.5), (17, 38.8), (11, 37.5), (8.5, 33.5)])
    c.paint(hull, UMBER, np.clip(0.55 + 0.02 * (Y - 28) + 0.25 * ((Y % 1.6) < 0.35), 0, 1), 1.3)
    c.paint(c.line_mask([(8.0, 30.5), (10.5, 32.6), (18, 33.4), (28, 33.0), (31.5, 32), (39.8, 30.5)], 1.1), SAFFRON, 0.35, 1.5)
    c.paint(ellipse(c, 11.8, 34.8, 1.6, 1.1), PEARL, 0.05, 1.6)
    c.paint(c.circle(12.0, 34.8, 0.6), UMBER, 1.0, 1.8)
    # the stern castle: rows of lit windows, a red railing, the rudder
    castle = rect(c, 31.5, 22.5, 40.5, 30)
    c.paint(castle & (ty % 3 == 1) & (tx % 3 != 0), SAFFRON, 0.2, 1.5)
    c.paint(rect(c, 31, 21.3, 41, 22.5) | (rect(c, 31.5, 19.8, 40.5, 21.3) & (tx % 2 == 0)), EMBER, 0.6, 1.5)
    c.paint(tube(c, [(37.5, 35.5), (39.5, 38.5)], 2.4, 2.0), UMBER, 0.9, 1.3)
    # bow wave
    c.paint(sea & ~hull & c.line_mask([(5, 35.5), (8, 34.2), (11, 38.2), (17, 40)], 1.0), PEARL, 0.15, 1.4)
    frame(c)
    return encode(c.to_tiles())


# ---------------------------------------------------------------------------
# Challenge
# ---------------------------------------------------------------------------

def printingpress():
    """Gutenberg's press: a tall timber frame, the great central screw with its long bar, the platen
    raised above a fresh sheet on the bed; printed pages drying on a line; a case of type."""
    c = Canvas(40, 44)
    X, Y = c.X, c.Y
    tx, ty = np.floor(X).astype(int), np.floor(Y).astype(int)
    # warm plaster wall, green wainscot, terracotta floor
    c.paint(ALL(c), SAFFRON, np.clip(0.1 + 0.12 * smooth_noise(c, 4, 0.5), 0, 1))
    wains = rect(c, 0, 34, 40, 39)
    c.paint(wains, FERN, 0.7)
    c.paint(wains & ((tx % 5 == 0) | (ty == 34)), FERN, 0.95, 1.1)
    c.paint(Y >= 39, EMBER, np.clip(0.35 + 0.35 * ((tx // 4 + ty // 3) % 2) + 0.3 * (tx % 4 == 0), 0, 1))
    # printed pages pegged on a line: a red decorated initial and blocks of text
    c.paint(c.line_mask([(1, 2.4), (39, 2.4)], 0.45), UMBER, 0.9, 1.3)
    for x0 in (2, 11, 20, 29):
        page = rect(c, x0, 3, x0 + 7, 12)
        c.paint(page, PEARL, 0.02, 1.4)
        c.paint(page & (tx > x0) & (tx < x0 + 6) & ((ty == 8) | (ty == 10)), UMBER, 0.9, 1.5)
        c.paint(page & (tx > x0 + 4) & (tx < x0 + 6) & ((ty == 4) | (ty == 6)), UMBER, 0.9, 1.5)
        ini = rect(c, x0 + 1, 4, x0 + 4, 7)
        c.paint(ini, EMBER, 0.4, 1.6)
        c.paint(ini & (tx == x0 + 2) & (ty == 5), SAFFRON, 0.1, 1.7)
        c.paint(rect(c, x0 + 1, 1.8, x0 + 2, 3.6) | rect(c, x0 + 5, 1.8, x0 + 6, 3.6), UMBER, 0.5, 1.5)
    # a small leaded window
    win = rect(c, 29, 14, 38, 21)
    c.paint(win, LAPIS, np.clip(0.15 + 0.07 * (Y - 14), 0, 1))
    c.paint(win & ((tx % 3 == 2) | (ty == 17)) | rect(c, 28, 13, 39, 14) | rect(c, 28, 21, 39, 22), UMBER, 0.7, 1.2)
    # the press frame: two tall posts, the cap and the heavy head beam, a sill on the floor
    grain = 0.5 + 0.5 * np.sin(X * 3.1 + np.sin(Y * 0.7) * 2.0)
    wood = rect(c, 3, 13, 6, 40) | rect(c, 21, 13, 24, 40) | rect(c, 2, 13, 25, 15.5) | rect(c, 2, 17.5, 25, 20.5)
    c.paint(wood, UMBER, np.clip(0.35 + 0.3 * grain, 0, 1), 1.2)
    c.paint(rect(c, 2, 38.5, 25, 40.5), UMBER, 0.9, 1.3)
    # the great screw, and the long bar sticking out sideways to its knob
    screw = rect(c, 10.5, 20.5, 16.5, 27)
    c.paint(screw, PEARL, 0.55, 1.3)
    c.paint(screw & ((tx - ty) % 3 == 0), UMBER, 0.95, 1.4)
    c.paint(c.line_mask([(15.5, 23.6), (33.5, 25.0)], 1.3) | c.circle(34.2, 25.1, 1.4), UMBER, 0.95, 1.5)
    # the platen raised above the bed, where a fresh sheet lies on the forme
    c.paint(rect(c, 7, 27, 20, 29), UMBER, 0.95, 1.4)
    c.paint(rect(c, 7, 30, 20, 31.5), PEARL, 0.0, 1.5)
    c.paint(rect(c, 2, 31.5, 26.5, 33.5) | rect(c, 25, 33.5, 26.5, 38.5), UMBER, 0.75, 1.3)
    # the type case on its stand: small compartments of grey and brass letter blocks
    case = rect(c, 28, 28, 38, 35)
    c.paint(case, UMBER, 0.85, 1.3)
    cell = case & (tx % 3 != 1) & (ty % 3 != 1)
    kind = (tx // 3 + ty // 3) % 3
    c.paint(cell & (kind == 0), PEARL, 0.6, 1.4)
    c.paint(cell & (kind == 1), SAFFRON, 0.65, 1.4)
    c.paint(cell & (kind == 2), PEARL, 0.9, 1.4)
    c.paint(rect(c, 29, 35, 30.5, 39) | rect(c, 35.5, 35, 37, 39), UMBER, 0.8, 1.3)
    frame(c)
    return encode(c.to_tiles())


def galileo():
    """Jupiter and its four moons seen through the eyepiece; the leather telescope, a sketchbook of
    dot diagrams, books, a quill and a candle on the desk around it."""
    c = Canvas(42, 44)
    X, Y = c.X, c.Y
    tx, ty = np.floor(X).astype(int), np.floor(Y).astype(int)
    cx, cy, R = 21.0, 15.5, 13.2
    # the desk: dark wooden planks
    c.paint(ALL(c), UMBER, np.clip(0.55 + 0.1 * np.sin(X * 2.6 + np.sin(Y * 0.3) * 3), 0, 1))
    c.paint((tx % 7 == 3), UMBER, 0.95, 1.05)
    # books stacked at the top left, a quill in an ink pot, a candle in a brass dish
    for i, (x0, x1, fam) in enumerate(((1, 9, EMBER), (1.5, 8, LAPIS), (1, 7.5, FERN))):
        book = rect(c, x0, 1 + 2.2 * i, x1, 3 + 2.2 * i)
        c.paint(book, fam, 0.45, 1.2)
        c.paint(book & ((tx == int(x0) + 1) | (tx == int(x1) - 2)), SAFFRON, 0.3, 1.3)
    c.paint(ellipse(c, 3.5, 11.4, 2.5, 0.7), PEARL, 0.35, 1.2)
    c.paint(ellipse(c, 3.2, 26.5, 2.2, 2.0), LAPIS, 0.8, 1.3)
    c.paint(rect(c, 2.2, 23.6, 4.2, 25.2), LAPIS, 0.9, 1.3)
    c.paint(ellipse(c, 2.8, 18.5, 1.2, 4.6, 0.35), PEARL, 0.1, 1.4)
    c.paint(c.line_mask([(1.6, 15.0), (3.4, 23.8)], 0.45), UMBER, 0.9, 1.5)
    c.paint(rect(c, 36, 8, 39, 16), PEARL, np.clip(0.1 + 0.1 * (X - 36), 0, 1), 1.2)
    c.paint(ellipse(c, 37.5, 16.5, 3.2, 1.0), SAFFRON, 0.65, 1.3)
    c.paint(ellipse(c, 37.5, 5.8, 1.0, 1.9), SAFFRON, 0.05, 1.5)
    c.paint(ellipse(c, 37.5, 6.4, 0.5, 0.9), EMBER, 0.2, 1.6)
    # the eyepiece view: brass ring, night sky, star crosses
    d = np.hypot(X - cx, Y - cy)
    c.paint(d < R + 1.7, SAFFRON, np.clip(0.3 + 0.3 * (Y - cy) / R, 0, 1), 1.2)
    c.paint((d < R + 2.2) & (d > R + 1.6), UMBER, 0.95, 1.2)
    c.paint(d < R, LAPIS, np.clip(0.95 - 0.35 * (np.hypot(X - 20, Y - 15) < 7.5), 0, 1), 1.2)
    for (sx, sy) in ((13.5, 5.5), (29.5, 7.5), (11.5, 23.5), (30.5, 24.5), (24.5, 4.5), (17.5, 26.5)):
        sparkle(c, sx, sy, 1.2, PEARL, 0.15, 1.5)
    # banded Jupiter with the great red spot
    jup = ellipse(c, 20, 15, 5.4, 5.0)
    limb = np.clip(0.35 * np.hypot((X - 20) / 5.4, (Y - 15) / 5.0) ** 3, 0, 1)
    bands = [(-5, SAFFRON, 0.6), (-3.2, EMBER, 0.25), (-1.9, PEARL, 0.05), (-0.5, SAFFRON, 0.2),
             (0.9, EMBER, 0.45), (2.3, PEARL, 0.15), (3.5, SAFFRON, 0.65)]
    for i, (y0, fam, sh) in enumerate(bands):
        y1 = bands[i + 1][0] if i + 1 < len(bands) else 5.1
        c.paint(jup & (Y - 15 >= y0) & (Y - 15 < y1), fam, np.clip(sh + limb, 0, 1), 1.4)
    c.paint(ellipse(c, 22.3, 16.6, 1.4, 0.8), EMBER, 0.85, 1.6)
    # the four moons strung along the equator
    for mx in (9.0, 12.0, 28.0, 31.5):
        c.paint(c.circle(mx, 15.5, 0.95), PEARL, 0.0, 1.9)
    # the telescope: leather tube with gilt bands and brass ends, lying across the lower left
    ax, ay, bx, by = 0.5, 41.5, 17.5, 32.5
    tel = tube(c, [(ax, ay), (bx, by)], 3.0, 4.6)
    c.paint(tel, EMBER, 0.7, 1.4)
    for t in (0.3, 0.55, 0.8):
        px, py = ax + (bx - ax) * t, ay + (by - ay) * t
        c.paint(c.line_mask([(px - 1.3, py - 2.4), (px + 1.3, py + 2.4)], 0.9) & tel, SAFFRON, 0.3, 1.5)
    c.paint(tube(c, [(bx - 0.9, by + 0.5), (bx + 0.6, by - 0.3)], 5.2, 5.2), SAFFRON, 0.5, 1.5)
    c.paint(tube(c, [(0, 42.3), (2.2, 41.1)], 2.4, 2.4), SAFFRON, 0.55, 1.5)
    # the sketchbook: green cover, a pale page with rows of dot diagrams and notes
    c.paint(c.poly_mask([(19.5, 31.2), (41, 30.2), (41, 43), (20.5, 43)]), FERN, 0.75, 1.3)
    page = c.poly_mask([(20.8, 32.2), (41, 31.3), (41, 43), (21.6, 43)])
    c.paint(page, PEARL, np.clip(0.02 + 0.02 * (Y - 32), 0, 1), 1.35)
    for (ry, dots) in ((34.5, (-6, -3, 3, 6)), (37.5, (-4, 3, 6)), (40.5, (-6, -3, 4))):
        c.paint(c.circle(31.5, ry, 1.1) & page, UMBER, 0.85, 1.7)
        for dx in dots:
            sparkle(c, 31.5 + dx, ry, 0.85, UMBER, 0.8, 1.8)
        c.paint(rect(c, 22.5, ry - 0.5, 25.5 - (ry % 2), ry + 0.5) & page, UMBER, 0.5, 1.6)
    for (sx, sy) in ((16.5, 8.5), (27.5, 9.5), (14.5, 21.5), (26.5, 22.5), (21.5, 24.5)):
        sparkle(c, sx, sy, 1.2, SAFFRON, 0.1, 1.5)
    frame(c)
    return encode(c.to_tiles())


# ---------------------------------------------------------------------------
# Master
# ---------------------------------------------------------------------------

def galapagos():
    """Darwin's Galapagos: a giant tortoise with a domed shell of hexagonal scutes on dark lava rock,
    a marine iguana and red crabs on the rocks, finches perched on a prickly-pear cactus, the sea behind."""
    c = Canvas(44, 42)
    X, Y = c.X, c.Y
    tx, ty = np.floor(X).astype(int), np.floor(Y).astype(int)
    r = random.Random(1835)
    # a narrow band of sky and sea with breaking crests, then dry golden grass
    c.paint(ALL(c), LAPIS, np.clip(0.15 + 0.7 * Y / 7, 0, 1))
    c.paint(((tx + (ty // 2) * 3) % 8 < 3) & (ty % 2 == 1) & (Y > 2.5) & (Y < 6) & (X > 22), PEARL, 0.1, 1.2)
    c.paint(Y > 6.6 + 0.5 * np.sin(X * 0.4), SAFFRON, np.clip(0.1 + 0.25 * (np.sin(X * 1.7 + Y * 2.3) > 0.7), 0, 1))
    # dark lava rock across the foreground: orange lichen, grey pits, tide pools
    lava = Y > 30.5 + 1.2 * np.sin(X * 0.35 + 1.0)
    c.paint(lava, UMBER, np.clip(0.85 + 0.2 * (smooth_noise(c, 13, 1.4) > 0.3), 0, 1))
    for _ in range(40):
        px, py = r.uniform(2, 42), r.uniform(32, 40.5)
        c.paint(ellipse(c, px, py, r.uniform(0.9, 1.3), 0.8, r.uniform(0, 3)) & lava,
                (SAFFRON, EMBER, PEARL, PEARL)[r.randrange(4)], r.uniform(0.3, 0.7), 1.2)
    for (px, py, rx) in ((5, 37.5, 2.6), (29.5, 40.3, 2.2), (26, 33.3, 1.6), (32, 33.4, 1.5), (11.5, 40.4, 1.6)):
        c.paint(ellipse(c, px, py, rx, 1.1), LAPIS, 0.45, 1.4)
    # green tufts in the dry grass
    for (gx, gy) in ((22, 9.5), (30, 11), (38, 9.5), (41, 14), (19.5, 15), (24, 12.5), (34.5, 13.5), (16, 29.5)):
        c.paint(c.poly_mask([(gx - 1.3, gy + 0.9), (gx - 0.5, gy - 1.2), (gx, gy + 0.2), (gx + 0.6, gy - 1.3),
                             (gx + 1.3, gy + 0.9)]), FERN, 0.55, 1.3)
    # the prickly-pear cactus: scaly red-brown trunk, spiny green pads, flowers
    trunk = tube(c, [(8.3, 33), (7.9, 25), (9.2, 17)], 3.0, 2.4)
    c.paint(trunk, EMBER, 0.85, 1.3)
    c.paint(trunk & ((tx + ty // 2) % 2 == 0) & (ty % 2 == 0), UMBER, 0.8, 1.35)
    pads = [(10.0, 17.5, 3.8, 2.5, 0.1), (4.6, 13.8, 3.0, 2.0, 0.6), (16.8, 13.8, 3.2, 2.1, -0.6),
            (10.2, 10.3, 2.5, 1.8, 1.5), (3.8, 21.2, 2.4, 1.7, 0.35)]
    for (px, py, rx, ry, a) in pads:
        pad = ellipse(c, px, py, rx, ry, a)
        c.paint(pad, FERN, np.clip(0.3 + 0.45 * np.hypot((X - px) / rx, (Y - py) / ry) ** 2, 0, 1), 1.4)
        c.paint(pad & (tx % 2 == 0) & (ty % 2 == 1) & ellipse(c, px, py, rx - 0.7, ry - 0.6, a), PEARL, 0.25, 1.5)
    for i, (fx, fy) in enumerate(((1.8, 16.2), (13.8, 16.0), (19.8, 15.6), (6.2, 22.8))):
        c.paint(c.circle(fx, fy, 0.95), (SAFFRON, EMBER)[i % 2], 0.1 + 0.2 * (i % 2), 1.6)
    # three finches perched on the pads, each with a different beak
    for (fx, fy, beak, fc) in ((14, 7, "thick", 1), (1, 7, "thin", -1), (7, 3, "long", -1)):
        finch(c, fx, fy, beak, fc)
    # the tortoise: grey neck and head reaching for the cactus, thick scaly pillar legs
    cx, cy, rx, ry = 30.0, 28.5, 12.3, 12.5
    neck = tube(c, [(20, 26.5), (17.2, 25.0), (15.6, 24.3)], 3.8, 3.0) | ellipse(c, 14.0, 23.7, 2.9, 2.0, -0.25)
    legs = tube(c, [(21.5, 27), (21, 34)], 4.4, 4.6) | tube(c, [(38.3, 27), (38.7, 33.8)], 4.0, 4.2)
    c.paint(neck | legs, PEARL, np.clip(0.72 + 0.15 * (X - 11) / 10 + 0.2 * ((ty % 2 == 0) & (Y > 28)), 0, 1), 1.3)
    c.paint(legs & (Y > 29.5) & ((tx + ty) % 3 == 0), UMBER, 0.6, 1.35)
    c.paint(c.circle(13.4, 23.1, 0.65), UMBER, 1.0, 1.8)
    c.paint(c.line_mask([(11.3, 24.5), (14.4, 24.5)], 0.5), UMBER, 0.9, 1.7)
    # the domed shell: hexagonal scutes (dark seam, brown ring, golden centre) and a row of marginals
    shell = ellipse(c, cx, cy, rx, ry) & (Y < cy)
    seeds = [(cx + dx, cy - 8.8) for dx in (-5, 0, 5)]                          # vertebral row along the top
    seeds += [(cx + dx, cy - 4.6) for dx in (-10, -7.5, -2.5, 2.5, 7.5, 10)]     # costal row, staggered
    seeds += [(cx + dx, cy - 1.3) for dx in np.arange(-10.5, 11, 3.0)]           # small marginals at the rim
    d1, d2, idx = voronoi(c, seeds)
    gap = d2 - d1
    c.paint(shell, UMBER, 0.35, 1.3)
    c.paint(shell & (gap > 1.35), SAFFRON, np.clip(0.5 + 0.2 * (Y - cy + ry) / ry, 0, 1), 1.35)
    c.paint(shell & ((gap < 0.75) | ~ellipse(c, cx, cy, rx - 0.8, ry - 0.8)), UMBER, 0.95, 1.4)
    # the marine iguana basking in front: rust red with a dark spiky crest, the tail curving away
    spine = [(x, 37.4 + 0.01 * (x - 34) ** 2) for x in np.arange(36.5, 14, -1.5)]
    ig = tube(c, spine, 3.4, 0.9)
    for (lx, ly, dx) in ((34.5, 38.3, 1.3), (29, 38.4, 1.2), (31, 38.4, -1.0), (24.5, 38.6, -1.2)):
        ig |= c.line_mask([(lx, ly), (lx + dx, ly + 2.0)], 1.0)
    ig |= ellipse(c, 39.0, 36.6, 2.6, 1.7, -0.25)
    c.paint(ig, EMBER, np.clip(0.45 + 0.08 * (Y - 37), 0, 1), 1.5)
    for (kx, ky) in spine[:8]:
        c.paint(c.poly_mask([(kx - 0.7, ky - 0.9), (kx, ky - 2.4), (kx + 0.7, ky - 0.9)]), EMBER, 0.95, 1.6)
    c.paint(ellipse(c, 39.2, 35.8, 1.6, 0.7, -0.25), PEARL, 0.1, 1.6)
    c.paint(c.circle(40.0, 36.5, 0.45), UMBER, 1.0, 1.9)
    # Sally Lightfoot crabs on the rock
    for (kx, ky) in ((13, 36.8), (17, 40.2), (3.8, 33.6)):
        crab(c, kx, ky)
    frame(c)
    return encode(c.to_tiles())


def southpole():
    """The race to the South Pole: a tent flying its flag, sledges of crates, a dog team, sastrugi,
    and a low sun with its halo and sun dogs."""
    c = Canvas(42, 42)
    X, Y = c.X, c.Y
    tx, ty = np.floor(X).astype(int), np.floor(Y).astype(int)
    hz = 16.0
    r = random.Random(1911)
    # pale polar sky with the halo, the parhelic circle, sun dogs and the low sun
    sky(c, 0.6, 0.12, horizon=hz)
    sx, sy = 10.5, 12.5
    ring = np.abs(np.hypot(X - sx, Y - sy) - 7.0) < 0.55
    c.paint(ring & (Y < hz), SAFFRON, 0.05, 1.3)
    c.paint(c.line_mask([(0, sy), (42, sy)], 0.8), PEARL, 0.05, 1.2)
    c.paint(c.line_mask([(sx - 3.5, sy - 7.6), (sx, sy - 6.6), (sx + 3.5, sy - 7.6)], 0.8), SAFFRON, 0.1, 1.3)
    for px in (sx - 7.0, sx + 7.0):
        c.paint(ellipse(c, px, sy, 1.1, 1.4), EMBER, 0.1, 1.6)
    c.paint(c.circle(sx, sy, 1.6), SAFFRON, 0.0, 1.7)
    # snow plain with wind-cut sastrugi: blue shadowed ridges, larger nearer
    c.paint(Y >= hz, PEARL, np.clip(0.08 + 0.2 * smooth_noise(c, 5, 0.6), 0, 1))
    for _ in range(40):
        y = r.uniform(hz + 0.8, 41.5)
        k = (y - hz) / (42 - hz)
        x, L = r.uniform(-2, 42), 2.5 + 5.0 * k
        a = r.uniform(-0.3, -0.05)
        pts = [(x, y), (x + L * 0.5, y + math.sin(a) * L * 0.5 - 0.3), (x + L, y + math.sin(a) * L)]
        c.paint(c.line_mask(pts, 0.8 + 0.5 * k), LAPIS, 0.15, 1.15)
    # the tent: canvas panels with dark seams, a door, guy lines, and the flag on its pole
    tent = c.poly_mask([(23, 28), (30.5, 12.5), (38, 28)])
    c.paint(tent, SAFFRON, np.clip(0.12 + 0.3 * (X > 30.5) + 0.01 * (Y - 12), 0, 1), 1.3)
    for fx in (26.2, 34.8):
        c.paint(c.line_mask([(30.5, 12.5), (fx, 28)], 0.5) & tent, UMBER, 0.6, 1.4)
    c.paint(c.poly_mask([(29.3, 28), (30.6, 22.5), (31.9, 28)]), UMBER, 0.95, 1.5)
    for (gx, gy) in ((20.5, 29.5), (40.5, 29.5)):
        c.paint(c.line_mask([(30.5, 15), (gx, gy)], 0.35), UMBER, 0.8, 1.3)
    c.paint(c.line_mask([(30.5, 13), (30.5, 1.2)], 0.6), UMBER, 0.9, 1.5)
    flag = rect(c, 31, 2, 40, 9)
    c.paint(flag, EMBER, 0.45, 1.6)
    c.paint(flag & (((tx >= 33) & (tx <= 35)) | ((ty >= 4) & (ty <= 6))), PEARL, 0.05, 1.7)
    c.paint(flag & ((tx == 34) | (ty == 5)), LAPIS, 0.55, 1.8)
    # two sledges piled with crates and lashed: one by the tent, one hitched to the team
    for (x0, x1, base, crates) in ((5, 19, 25.5, ((5.5, 10, 3.5, FERN), (10, 14.5, 4.5, EMBER), (14.5, 18.5, 3, LAPIS))),
                                   (25, 40.5, 39, ((25.5, 30, 4.5, EMBER), (30, 34.5, 5.5, FERN), (34.5, 38.5, 4, SAFFRON),
                                                   (38.5, 41, 3.5, FERN)))):
        c.paint(c.line_mask([(x0 - 1.4, base - 1.4), (x0, base + 0.6), (x1, base + 0.6)], 0.8), UMBER, 0.95, 1.5)
        c.paint(rect(c, x0, base - 0.7, x1, base), UMBER, 0.6, 1.4)
        for (a, b, h, fam) in crates:
            box = rect(c, a, base - 0.7 - h, b - 0.4, base - 0.7)
            c.paint(box, fam, 0.35, 1.45)
            c.paint(box & (ty == int(base - 0.7 - h) + 1), PEARL, 0.25, 1.5)
        c.paint(c.line_mask([(x0 + 0.5, base - 5.5), (x1 - 0.5, base - 1.2)], 0.5), UMBER, 0.85, 1.55)
    # the dog team in pairs along the gang line, pulling to the left
    c.paint(c.line_mask([(2, 35.0), (24.5, 37.5)], 0.45), UMBER, 0.9, 1.3)
    for i, (dx, dy) in enumerate(((6.5, 31.3), (7.3, 38.6), (16.5, 32.2), (17.3, 39.3))):
        dog(c, dx, dy, UMBER, FERN if i % 2 else EMBER, 1.2)
    frame(c)
    return encode(c.to_tiles())


SCENES = {
    "wayfinders": wayfinders, "longship": longship, "silkroad": silkroad, "treasureship": treasureship,
    "printingpress": printingpress, "galileo": galileo, "galapagos": galapagos, "southpole": southpole,
}
