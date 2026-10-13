"""The Ancient World pack: eight memorable moments and marvels of the ancient world, drawn with the
same supersampled Canvas as art.py and art_scenes.py (a tile's colour family comes from the dominant
object under it, its tone from the shading).

Gentle: the Lascaux cave paintings, the pyramids of Giza, Stonehenge at midsummer sunrise.
Challenge: Tutankhamun's golden mask, a black-figure amphora for the first Olympic Games, the Great Wall.
Master: the Terracotta Army, the Colosseum.
"""
import math
import random

import numpy as np
from scipy import ndimage

from art import Canvas, LAPIS, SAFFRON, FERN, EMBER, UMBER, PEARL, encode, leaf
from art_scenes import ALL, ellipse, rect, tube, frame, cloud, smooth_noise, chevron


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def tiles(c):
    """Integer tile coordinates of every pixel (for crisp tile-aligned grids, bricks and keys)."""
    return np.floor(c.X).astype(int), np.floor(c.Y).astype(int)


def outline(mask, width_px=7):
    """The rim of a mask, about width_px/8 tiles thick."""
    return mask & ~ndimage.binary_erosion(mask, iterations=width_px)


BIG_HAND = ["...#....", ".#.#.#..", ".#.#.#.#", ".#.#.#.#", ".#######", "########", "#######.", ".######.",
            "..####.."]
SMALL_HAND = ["..#.#..", "#.#.#.#", "#.#.#.#", "#######", "#######", ".#####.", "..###.."]


def hand_stencil(c, ox, oy, sprite):
    """A negative hand stencil: a halo of sprayed red ochre with the pale hand (a tile sprite whose top-left
    tile is (ox, oy)) left bare."""
    X, Y = c.X, c.Y
    tx, ty = tiles(c)
    h, w = len(sprite), len(sprite[0])
    hx, hy = ox + w / 2, oy + h / 2
    rad = max(w, h) / 2 + 1.6
    c.paint(c.circle(hx, hy, rad), EMBER, np.clip(1.05 - 0.75 * np.hypot(X - hx, Y - hy) / rad, 0.2, 1), 1.1)
    hand = np.zeros_like(X, bool)
    for j, row in enumerate(sprite):
        for i, ch in enumerate(row):
            if ch == "#":
                hand |= (tx == ox + i) & (ty == oy + j)
    c.paint(hand, PEARL, 0.1, 1.8)


# ---------------------------------------------------------------------------
# Gentle
# ---------------------------------------------------------------------------

def lascaux():
    """Lascaux, c. 17,000 BC: a great black aurochs, a red horse and a stag on a lumpy cave wall."""
    c = Canvas(48, 36)
    X, Y = c.X, c.Y
    n, n2 = smooth_noise(c, 17, 0.45), smooth_noise(c, 5, 1.1)
    # the lumpy limestone wall: pale bosses, warm ochre stains, a brown shadowed rim
    c.paint(ALL(c), PEARL, np.clip(0.45 + 0.5 * n + 0.12 * n2, 0.1, 1.0))
    for (ex, ey, rx, ry) in ((21, 31, 10, 3.8), (2.5, 14, 4, 8), (45, 16, 4, 6), (28, 3.5, 11, 3.2)):
        c.paint(ellipse(c, ex, ey, rx, ry) & (n2 > -0.35), SAFFRON, np.clip(0.05 + 0.3 * (n + 0.5), 0, 0.6))
    rim = np.minimum.reduce([X, 48 - X, Y * 1.4, (36 - Y) * 1.4])
    c.paint(rim < 1.9 + 1.2 * n2 + 0.6 * n, UMBER, np.clip(0.15 + 0.2 * n2, 0, 0.4))
    # the aurochs (facing left), drawn in local units and mapped onto the wall
    s = 0.8
    P = lambda x, y: (3.8 + (x - 7) * s, 2.6 + (y - 3.4) * s)
    E = lambda x, y, rx, ry, a=0.0: ellipse(c, *P(x, y), rx * s, ry * s, a)
    T = lambda pts, w0, w1: tube(c, [P(*p) for p in pts], w0 * s, w1 * s)
    body = E(27, 13.4, 10.2, 4.5) | E(19.5, 11.4, 5.4, 5.2) | E(35.3, 12.8, 4.6, 4.5)
    neck = c.poly_mask([P(18.5, 7.0), P(11.8, 9.2), P(10.8, 14.6), P(17, 17.2)])
    head = E(10.2, 12.4, 3.3, 2.2, 0.6)
    legs = (T([(17.5, 15), (16.9, 18.5), (16.5, 21.6)], 2.4, 1.5) | T([(21.2, 15.5), (21.8, 18.5), (22.1, 21.6)], 2.4, 1.5)
            | T([(33.2, 15.5), (33.6, 18.5), (33.8, 21.6)], 2.4, 1.5) | T([(37.8, 14.8), (39.2, 18), (39.0, 21.4)], 2.4, 1.5))
    horns = T([(11.8, 10.2), (9.8, 7.5), (10.4, 4.6), (12.4, 3.4)], 1.4, 0.9) | T([(13.2, 9.5), (13.7, 6.4), (15.9, 4.5)], 1.4, 0.9)
    tail = T([(39.8, 10.4), (40.8, 13), (41.0, 17.4)], 1.1, 0.9)
    bull = body | neck | head | legs
    c.paint(bull, UMBER, np.clip(0.45 + 0.08 * n2, 0, 1), 1.3)
    c.paint(outline(bull, 8) | head | legs | horns | tail | (neck & (X < P(15, 0)[0])), UMBER, 0.95, 1.4)
    # the red horse (facing right) with a black mane, tail and hooves
    horse = ellipse(c, 20.5, 27.6, 7.0, 3.5) | c.poly_mask([(24.7, 26.0), (27.9, 22.2), (30.1, 23.2), (27.7, 28.6)])
    horse |= ellipse(c, 30.9, 24.3, 2.5, 1.35, 0.75)
    hlegs = (tube(c, [(16.1, 29), (15.6, 33)], 1.6, 1.1) | tube(c, [(18.7, 30), (19.1, 33.3)], 1.6, 1.1)
             | tube(c, [(23.7, 30), (24.5, 33.2)], 1.6, 1.1) | tube(c, [(26.1, 29), (27.5, 32.8)], 1.6, 1.1))
    c.paint(horse | hlegs, EMBER, np.clip(0.3 + 0.3 * (Y - 24) / 7, 0, 1), 1.3)
    c.paint(tube(c, [(24.5, 24.9), (27.5, 21.6), (29.3, 21.9)], 1.5, 1.1), UMBER, 0.95, 1.5)
    c.paint(tube(c, [(13.9, 26.3), (12.1, 28.8), (11.7, 32.2)], 1.8, 1.0), UMBER, 0.95, 1.5)
    c.paint(hlegs & (Y > 31.6), UMBER, 0.95, 1.5)
    # the stag (facing left) with branching antlers
    deer = ellipse(c, 41.0, 20.6, 4.3, 2.2, 0.05) | c.poly_mask([(38.1, 20.0), (35.9, 16.0), (37.4, 15.3), (39.9, 19.1)])
    deer |= ellipse(c, 35.3, 16.3, 1.9, 1.0, -0.35)
    for (a, b) in (((38.4, 22), (38.0, 26.4)), ((39.8, 22.4), (40.1, 26.6)), ((43.2, 22.2), (43.7, 26.4)), ((44.4, 21.4), (45.2, 25.6))):
        deer |= tube(c, [a, b], 1.3, 0.9)
    c.paint(deer, EMBER, 0.6, 1.3)
    for pts in ([(36.4, 15.4), (35.5, 12.4), (36.7, 9.0), (39.0, 7.2)], [(37.1, 15.2), (38.8, 12.6), (41.8, 10.8)],
                [(35.7, 12.9), (33.6, 11.5)], [(36.2, 10.2), (34.4, 8.3)], [(38.4, 13.0), (39.0, 10.4)], [(40.2, 11.8), (41.0, 9.2)]):
        c.paint(c.line_mask(pts, 1.0), UMBER, 0.95, 1.6)
    # hand stencils
    hand_stencil(c, 2, 24, BIG_HAND)
    hand_stencil(c, 39, 28, SMALL_HAND)
    frame(c)
    return encode(c.to_tiles())


def pyramids():
    """The Great Pyramid of Giza, c. 2560 BC: three pyramids at sunset, palms and the Nile in front."""
    c = Canvas(42, 40)
    X, Y = c.X, c.Y
    ty = np.floor(Y).astype(int)
    # evening sky in horizontal bands; the low sun sits in the notch between the two great pyramids
    c.paint(ALL(c), LAPIS, np.clip(0.75 - 0.5 * Y / 8, 0.15, 1))
    c.paint(Y > 7.5 + 0.8 * np.sin(X * 0.3), EMBER, np.clip(0.75 - 0.75 * (Y - 7.5) / 14, 0, 1))
    c.paint(c.circle(21.0, 11.4, 4.0), EMBER, 0.0, 1.1)
    c.paint(c.circle(21.0, 11.4, 2.6), PEARL, 0.0, 1.3)
    # far dunes
    c.paint(Y > 24.5 + 0.7 * np.sin(X * 0.22 + 0.8), SAFFRON, 0.8)

    def pyramid(ax, ay, x0, x1, by, rx, lit, shadow):
        course = (ty % 2) * 0.14  # stepped courses: alternate tones row by row
        left = c.poly_mask([(ax, ay), (x0, by), (rx, by)])
        right = c.poly_mask([(ax, ay), (rx, by), (x1, by)])
        c.paint(left, SAFFRON, np.clip(lit + course + 0.008 * (Y - ay), 0, 1), 1.1)
        c.paint(right, UMBER, np.clip(shadow + course, 0, 1), 1.1)
        return left, right
    pyramid(5.5, 19.4, -1.5, 12.5, 25.6, 7.4, 0.25, 0.2)                     # Menkaure
    l2, r2 = pyramid(15.0, 11.0, 2.5, 28, 26.2, 18.2, 0.1, 0.25)              # Khafre, with its casing cap
    c.paint((l2 | r2) & (Y < 13.6), PEARL, np.where(l2, 0.05, 0.6), 1.2)
    l1, r1 = pyramid(30.5, 3.6, 14.5, 46.5, 31.4, 34.5, 0.0, 0.1)             # Khufu
    cap = (l1 | r1) & (Y < 8.0)
    c.paint(cap, PEARL, np.where(l1, 0.0, 0.5) + (ty % 2) * 0.12, 1.3)       # bright stepped capstone
    # the pyramid's long shadow on the sand, near dunes
    c.paint(Y > 30.8 + 0.8 * np.sin(X * 0.3 + 2.0), SAFFRON, np.clip(0.8 + 0.12 * np.sin(X * 1.1 + Y * 2), 0, 1))
    # the green bank and the Nile
    c.paint(Y > 33.2 + 0.4 * np.sin(X * 0.5), FERN, np.clip(0.45 + 0.2 * np.sin(X * 1.7), 0, 1))
    nile = Y > 35.6 + 0.3 * np.sin(X * 0.4)
    c.paint(nile, LAPIS, np.clip(0.4 + 0.12 * (Y - 35.6) + 0.12 * np.sin(Y * 3 + X * 0.5), 0, 1))
    c.paint(nile & (np.abs(X - 21.0) < 3) & (np.sin(Y * 3.2 + X * 0.8) > 0.55), PEARL, 0.1, 1.2)
    # palms on the bank
    for (px, py, tx_, ty_, lean) in ((3.5, 35, 5.0, 18.5, 1), (10.5, 35, 9.6, 22.5, -1), (38.5, 35.5, 37, 20.5, -1)):
        c.paint(tube(c, [(px, py), (px + (tx_ - px) * 0.3 + lean * 0.8, (py + ty_) / 2), (tx_, ty_)], 1.3, 0.9), UMBER,
                np.clip(0.45 + 0.3 * (np.sin(Y * 3.2) > 0.3), 0, 1), 1.2)
        for k in range(7):
            a = math.pi * (1.05 + 0.9 * k / 6)
            ln = 5.4 - 1.2 * abs(k - 3) / 3
            leaf(c, tx_, ty_, tx_ + math.cos(a) * ln, ty_ + math.sin(a) * ln * 0.75 + 1.6 * abs(math.cos(a)), 1.7, 0.18)
        c.paint(c.circle(tx_ + 0.4, ty_ + 1.0, 0.75), EMBER, 0.55, 1.5)
    frame(c)
    return encode(c.to_tiles())


def stonehenge():
    """Stonehenge at midsummer sunrise, c. 2500 BC: the ring seen from slightly above, trilithons and single
    stones round a grassy circle, the sun low between two uprights, long shadows running towards us."""
    c = Canvas(48, 36)
    X, Y = c.X, c.Y
    hz, sx, sy = 13.0, 24.0, 11.2
    ecx, ecy, erx, ery = 24.0, 22.0, 17.0, 8.6            # the ring's footprint (an ellipse on the ground)
    # sunrise sky glowing round the sun, a low line of far hills, the grassy plain
    d = np.hypot(X - sx, (Y - sy) * 1.5)
    c.paint(ALL(c), LAPIS, np.clip(0.2 + 0.7 * (d - 12) / 12, 0.15, 1))
    c.paint(d < 12.5, EMBER, np.clip(0.05 + 0.5 * (d - 6.5) / 6, 0, 1))
    c.paint(d < 7.0, SAFFRON, np.clip(0.02 + 0.4 * d / 7.0, 0, 1))
    c.paint(c.circle(sx, sy, 2.0), PEARL, 0.0, 1.4)
    c.paint(Y > hz - 0.6 + 0.5 * np.sin(X * 0.35), FERN, 0.85)
    c.paint(Y > hz + 0.6, FERN, np.clip(0.3 + 0.012 * (Y - hz) * np.abs(X - sx), 0, 0.7))
    # stones round the ellipse (angle in degrees, 0 = right, 90 = nearest); trilithon pairs share a lintel
    singles = (180, 0, 152, 28)
    pairs = ((258, 282), (214, 236), (304, 326), (104, 126), (54, 76))
    pos = lambda a: (ecx + erx * math.cos(math.radians(a)), ecy + ery * math.sin(math.radians(a)))
    size = lambda a: 0.75 + 0.4 * (math.sin(math.radians(a)) + 1) / 2
    # long shadows first, pointing away from the sun across the grass
    for a in list(singles) + [x for p in pairs for x in p]:
        bx, by = pos(a)
        n = math.hypot(bx - sx, by - sy)
        ln = 8.0 + 5.0 * math.sin(math.radians(a))
        c.paint(c.line_mask([(bx, by), (bx + (bx - sx) / n * ln, by + (by - sy) / n * ln)], 2.0 * size(a)) & (Y > hz + 0.6),
                FERN, 1.0, 1.05)

    def upright(a, extra=0.0):
        """A grey standing stone, lit along the top, its side away from the sun in brown shadow."""
        bx, by = pos(a)
        s = size(a)
        w, h = 2.5 * s, 8.0 * s + extra
        m = c.poly_mask([(bx - w / 2, by), (bx - w / 2, by - h + 0.6), (bx - w / 2 + 0.6, by - h), (bx + w / 2 - 0.5, by - h),
                         (bx + w / 2, by - h + 0.7), (bx + w / 2, by)])
        c.paint(m, PEARL, 0.95, 1.3)
        c.paint(m & (Y < by - h + 1.0), PEARL, 0.35, 1.32)
        side = 1 if bx > sx else -1
        c.paint(m & ((X - bx) * side > w / 2 - 1.0 * s) & (Y > by - h + 1.0), UMBER, 0.05, 1.35)
        return bx, by - h
    order = sorted([(a, None) for a in singles] + [(p[0], p) for p in pairs], key=lambda t: math.sin(math.radians(t[0])))
    for a, pair in order:
        if pair is None:
            upright(a)
            continue
        extra = 1.2 if pair == (258, 282) else 0.0
        (x0, t0), (x1, t1) = upright(pair[0], extra), upright(pair[1], extra)
        s = size(pair[0])
        lint = c.poly_mask([(min(x0, x1) - 1.5 * s, max(t0, t1) + 0.2), (min(x0, x1) - 1.4 * s, min(t0, t1) - 1.6 * s),
                            (max(x0, x1) + 1.4 * s, min(t0, t1) - 1.6 * s), (max(x0, x1) + 1.5 * s, max(t0, t1) + 0.2)])
        c.paint(lint, PEARL, np.clip(0.7 + 0.12 * (Y - min(t0, t1)), 0, 1), 1.36)
    # a fallen stone lying in the grass at the front
    c.paint(ellipse(c, 29.5, 33.0, 3.6, 1.0, 0.06), PEARL, 0.9, 1.3)
    frame(c)
    return encode(c.to_tiles())


# ---------------------------------------------------------------------------
# Challenge
# ---------------------------------------------------------------------------

def golden_mask():
    """Tutankhamun's golden mask (c. 1323 BC, found in 1922), front-on in the dark of the tomb."""
    c = Canvas(38, 46)
    X, Y = c.X, c.Y
    cx = 19.0
    dx = X - cx
    c.paint(ALL(c), UMBER, np.clip(0.85 + 0.12 * smooth_noise(c, 3, 0.5), 0, 1))
    # broad collar over the shoulders: gold rings between bands of lapis, carnelian and turquoise beads
    r = np.hypot(dx / 1.28, Y - 27.5)
    ang = np.arctan2(dx, Y - 27.5)
    collar = (r < 19.6) & (Y > 29.0)
    c.paint(collar, SAFFRON, np.clip(0.1 + 0.02 * r, 0, 1))
    for (r0, r1, fam, tone, nseg) in ((8.2, 10.2, LAPIS, 0.85, 0), (11.2, 13.2, EMBER, 0.55, 0), (14.2, 16.4, LAPIS, 0.3, 0)):
        ring = collar & (r >= r0) & (r < r1)
        if nseg:
            ring &= np.abs(((ang * nseg / math.pi) % 1.0) - 0.5) < 0.34
        c.paint(ring, fam, tone, 1.2)
    drops = collar & (r >= 17.3) & (np.abs(((ang * 17 / math.pi) % 1.0) - 0.5) > 0.5 * (r - 17.3) / 2.3 - 0.1)
    c.paint(collar & (r >= 17.3) & ~drops, UMBER, 0.9, 1.1)
    # nemes headdress: rounded crown and two lappets, striped gold and deep blue, with a dark rim
    crown = ellipse(c, cx, 15.0, 12.8, 12.5) & (Y < 20)
    flare = c.poly_mask([(cx - 12.8, 14), (cx - 16.0, 24), (cx - 15.6, 35.5), (cx + 15.6, 35.5), (cx + 16.0, 24), (cx + 12.8, 14)])
    nemes = crown | flare
    s = Y - 0.05 * np.minimum(dx * dx, 110)
    stripe = (np.floor((s - 0.2) / 2.3).astype(int) % 2) == 0
    c.paint(nemes, SAFFRON, np.clip(0.1 + 0.3 * np.abs(dx) / 13, 0, 1))
    c.paint(nemes & stripe, LAPIS, 0.85, 1.1)
    c.paint(outline(nemes, 5) & (Y > 15), UMBER, 0.95, 1.15)
    # the face, framed by a blue edge, and the ears
    face = ellipse(c, cx, 20.5, 7.4, 9.6)
    c.paint(ellipse(c, cx, 20.3, 8.1, 10.3) & (Y > 10.5), LAPIS, 0.9, 1.2)
    for side in (-1, 1):
        c.paint(ellipse(c, cx + side * 8.6, 21.5, 1.7, 2.8), SAFFRON, 0.4, 1.3)
        c.paint(c.circle(cx + side * 8.7, 23.3, 0.55), UMBER, 0.95, 1.5)
    c.paint(face, SAFFRON, np.clip(0.02 + 0.35 * np.hypot(dx / 7.4, (Y - 19) / 9.6) ** 2, 0, 1), 1.3)
    c.paint(rect(c, cx - 7.6, 10.4, cx + 7.6, 12.2) & ellipse(c, cx, 20.3, 8.2, 10.6), SAFFRON, 0.35, 1.35)
    # eyes: lapis brows and kohl, white eyes, dark pupils; nose and lips
    for side in (-1, 1):
        ex, ey = cx + side * 3.4, 18.6
        c.paint(c.line_mask([(ex - side * 2.2, 16.3), (ex, 15.5), (ex + side * 2.6, 16.0)], 0.75), LAPIS, 0.9, 1.6)
        c.paint(ellipse(c, ex, ey, 2.9, 1.55) | c.line_mask([(ex + side * 2.2, ey + 0.2), (ex + side * 4.6, ey + 0.3)], 0.7),
                LAPIS, 0.9, 1.6)
        c.paint(ellipse(c, ex, ey, 2.35, 1.05), PEARL, 0.05, 1.75)
        c.paint(c.circle(ex, ey, 0.8), UMBER, 1.0, 1.85)
    c.paint(ellipse(c, cx, 23.2, 1.3, 0.6), SAFFRON, 0.65, 1.5)
    c.paint(ellipse(c, cx, 26.4, 2.1, 0.55), EMBER, 0.55, 1.5)
    # vulture and cobra on the brow
    c.paint(c.circle(cx - 1.4, 9.8, 1.15) | c.poly_mask([(cx - 2.4, 10.1), (cx - 3.4, 11.2), (cx - 2.1, 11.0)]), SAFFRON, 0.45, 1.8)
    c.paint(c.circle(cx - 1.6, 9.6, 0.35), UMBER, 1.0, 1.9)
    c.paint(ellipse(c, cx + 1.4, 9.4, 1.15, 1.9), LAPIS, 0.55, 1.8)
    c.paint(ellipse(c, cx + 1.4, 9.7, 0.45, 1.1), EMBER, 0.4, 1.9)
    # the braided beard, in its own shadow
    beard = rect(c, cx - 1.8, 29.4, cx + 1.8, 37.0) | ellipse(c, cx, 36.8, 2.0, 1.2)
    c.paint((rect(c, cx - 2.5, 29.4, cx + 2.5, 37.4) | ellipse(c, cx, 37.1, 2.7, 1.8)) & ~face, UMBER, 0.95, 1.3)
    c.paint(beard, SAFFRON, 0.2, 1.4)
    c.paint(beard & (((Y - np.abs(dx) * 0.8) % 2.0) < 1.0), LAPIS, 0.8, 1.5)
    frame(c)
    return encode(c.to_tiles())


def olympia():
    """The first Olympic Games, 776 BC: a black-figure amphora with a band of running athletes, olive
    sprigs (the victor's prize) in the corners."""
    c = Canvas(38, 46)
    X, Y = c.X, c.Y
    tx, ty = tiles(c)
    cx = 19.0
    dx = X - cx
    # a plain blue ground, lighter behind the vase, a pale shelf and two olive sprigs
    c.paint(ALL(c), LAPIS, np.clip(0.45 + 0.4 * np.hypot(dx / 20, (Y - 22) / 24) ** 1.5, 0, 1))
    c.paint(Y > 43.2, PEARL, np.clip(0.15 + 0.1 * (Y - 43), 0, 1))
    for side in (-1, 1):
        for stem in ([(cx + side * 18.5, 16.0), (cx + side * 17.2, 10.0), (cx + side * 14.5, 5.0), (cx + side * 10.5, 2.2)],
                     [(cx + side * 18.4, 27.0), (cx + side * 17.3, 33.5), (cx + side * 14.8, 38.8), (cx + side * 11.0, 42.4)]):
            c.paint(c.line_mask(stem, 0.6), UMBER, 0.6, 1.2)
            for k, t in enumerate(np.linspace(0.08, 0.92, 7)):
                i = min(int(t * 3), 2)
                f = t * 3 - i
                px, py = stem[i][0] + (stem[i + 1][0] - stem[i][0]) * f, stem[i][1] + (stem[i + 1][1] - stem[i][1]) * f
                a = math.atan2(stem[i + 1][1] - stem[i][1], stem[i + 1][0] - stem[i][0]) + (0.8 if k % 2 else -0.8)
                c.paint(ellipse(c, px + math.cos(a) * 1.4, py + math.sin(a) * 1.4, 1.7, 0.7, a), FERN, 0.3 + 0.1 * (k % 3), 1.3)
    # the amphora's profile: clay body, black lip, lower body and foot, two handles
    ys = [1.6, 3.4, 4.0, 8.0, 10.6, 12.6, 15.0, 19.0, 23.0, 28.0, 33.0, 37.0, 39.4, 40.4, 42.0, 43.2]
    hw = [6.0, 6.0, 4.3, 3.9, 4.3, 8.4, 12.0, 13.6, 13.8, 12.8, 10.2, 7.0, 4.2, 3.8, 6.0, 6.0]
    half = np.interp(Y, ys, hw)
    vase = (Y >= 1.6) & (Y <= 43.2) & (np.abs(dx) <= half)
    c.paint(vase, EMBER, np.clip(0.2 + 0.35 * (np.abs(dx) / np.maximum(half, 1)) ** 2, 0, 1))
    for side in (-1, 1):
        c.paint(tube(c, [(cx + side * 3.8, 5.4), (cx + side * 9.0, 5.0), (cx + side * 10.6, 8.0), (cx + side * 10.9, 13.2)],
                     1.8, 1.8) & ~vase, UMBER, 0.9, 1.2)
    c.paint(vase & ((Y < 4.0) | (Y > 37.0)), UMBER, np.clip(0.8 + 0.2 * np.abs(dx) / np.maximum(half, 1), 0, 1))
    # a palmette on the neck and tongues on the shoulder
    for k in range(5):
        a = -math.pi / 2 + (k - 2) * 0.5
        tip = (cx + math.cos(a) * 3.9, 10.2 + math.sin(a) * 4.1)
        c.paint((c.line_mask([(cx, 10.2), tip], 0.8) | c.circle(*tip, 0.75)) & vase, UMBER, 0.9, 1.3)
    c.paint(ellipse(c, cx, 10.2, 1.5, 0.8), UMBER, 0.9, 1.3)
    ang = np.arctan2(dx, Y - 4)
    c.paint(vase & (Y > 12.0) & (Y < 14.6) & (np.abs(((ang * 11 / math.pi) % 1.0) - 0.5) < 0.24), UMBER, 0.9, 1.2)
    # the key (meander) band below the runners: tile-aligned square spirals
    unit = ["#####", "....#", "###.#", "#...#", "#####"]
    u, v = (tx - 4) % 6, ty - 31
    key = np.zeros_like(vase)
    for j, row in enumerate(unit):
        for i, ch in enumerate(row):
            if ch == "#":
                key |= (v == j) & (u == i)
    c.paint(vase & key, UMBER, 0.9, 1.2)
    # two runners, big black figures in the sprint pose, heading right
    for (hx, hy) in ((cx - 7.2, 24.8), (cx + 6.2, 24.8)):
        fig = c.circle(hx + 2.6, hy - 7.6, 1.7) | ellipse(c, hx + 1.0, hy - 2.9, 1.7, 3.3, 0.3)
        fig |= tube(c, [(hx + 1.9, hy - 5.0), (hx + 4.3, hy - 3.4), (hx + 5.4, hy - 5.6)], 1.6, 1.3)
        fig |= tube(c, [(hx + 0.6, hy - 4.8), (hx - 1.9, hy - 3.2), (hx - 3.8, hy - 4.8)], 1.6, 1.3)
        fig |= tube(c, [(hx + 0.3, hy), (hx + 3.8, hy + 1.0)], 2.4, 1.8) | tube(c, [(hx + 3.8, hy + 1.0), (hx + 3.2, hy + 5.0)], 1.7, 1.3)
        fig |= c.line_mask([(hx + 3.2, hy + 5.0), (hx + 4.6, hy + 5.3)], 1.0)
        fig |= tube(c, [(hx, hy), (hx - 1.6, hy + 3.4)], 2.4, 1.8) | tube(c, [(hx - 1.6, hy + 3.4), (hx - 4.6, hy + 2.3)], 1.7, 1.3)
        c.paint(fig & vase, UMBER, 0.95, 1.5)
    frame(c)
    return encode(c.to_tiles())


def great_wall():
    """The Great Wall of China: the wall climbs from the foreground to a watchtower on the crest, turns and
    runs back along a far ridge, with misty mountains behind."""
    c = Canvas(44, 40)
    X, Y = c.X, c.Y
    tx, ty = tiles(c)
    # pale sky, a far range sinking into mist, and a nearer blue range
    c.paint(ALL(c), LAPIS, 0.05)
    c.paint(Y > 3.2 + 1.6 * np.sin(X * 0.3 + 0.5) + 0.7 * np.sin(X * 0.8 + 0.5), LAPIS, 0.3)
    c.paint(Y > 5.6 + 0.8 * np.sin(X * 0.5), PEARL, np.clip(0.05 + 0.05 * (Y - 5.6), 0, 0.25))
    c.paint(Y > 7.4 + 2.0 * np.sin(X * 0.22 + 2.2) + 0.8 * np.sin(X * 0.6 + 2.2), LAPIS, np.clip(0.5 + 0.03 * (Y - 7), 0, 1))
    # far ridge (carrying the far run of the wall) and the near hill (carrying the near run)
    far_top = lambda x: np.interp(x, [-1, 9, 20, 31], [9.0, 11.0, 13.4, 17.5])
    far_h = lambda x: np.interp(x, [-1, 31], [1.4, 2.6])
    near_top = lambda x: np.interp(x, [-1, 15, 31, 45], [33.5, 26.0, 17.5, 24.5])
    near_h = lambda x: np.interp(x, [-1, 15, 31, 45], [5.2, 4.4, 3.6, 4.2])
    c.paint(Y > np.interp(X, [-1, 9, 20, 31, 38, 45], [10.2, 12.4, 15.2, 19.8, 17.4, 15.8]), FERN, np.clip(0.8 + 0.1 * np.sin(X * 1.3 + Y), 0, 1))
    c.paint(Y > near_top(X) + near_h(X) - 0.4, FERN, np.clip(0.3 + 0.12 * np.sin(X * 0.9 + Y * 1.4) + 0.01 * (Y - 20), 0, 1))
    # autumn trees dotted over the slopes
    r = random.Random(21)
    for _ in range(90):
        x, y = r.uniform(1, 43), r.uniform(12, 39)
        top = near_top(x) + near_h(x) + 1.2 if y > near_top(x) else np.interp(x, [-1, 9, 20, 31, 38, 45], [10.2, 12.4, 15.2, 19.8, 17.4, 15.8]) + 1.2
        if y > top and not (near_top(x) - 2.5 < y < near_top(x) + near_h(x) + 1.2):
            fam = (EMBER, SAFFRON, EMBER, FERN)[r.randrange(4)]
            c.paint(c.circle(x, y, r.uniform(1.0, 1.45)), fam, r.uniform(0.2, 0.7) if fam != FERN else 0.95, 1.1)

    def run(x0, x1, top, h):
        """A run of wall between x0 and x1: brick face, bright walkway, crenellated parapet, dark footing."""
        t, hh = top(X), h(X)
        span = (X >= x0) & (X < x1)
        face = span & (Y >= t) & (Y < t + hh)
        c.paint(face, PEARL, np.clip(0.45 + 0.3 * ((ty % 2) == 1) + 0.25 * (((tx + (ty // 2) * 2) % 4) == 0), 0, 1), 1.2)
        c.paint(face & (Y < t + 0.9), PEARL, 0.02, 1.25)
        c.paint(span & (Y >= t - 1.3 * hh / 4.4) & (Y < t) & (tx % 2 == 0), PEARL, 0.3, 1.3)
        c.paint(span & (Y >= t + hh - 0.7) & (Y < t + hh + 0.1), UMBER, 0.6, 1.25)

    def tower(x, y, s):
        """A square watchtower standing on the wall at (x, y): brick courses, arched windows, battlements."""
        body = rect(c, x - 2.6 * s, y - 5.2 * s, x + 2.6 * s, y + 3.6 * s)
        c.paint(body, PEARL, np.clip(0.3 + 0.2 * (X > x), 0, 1), 1.3)
        c.paint(body & (((ty % 2) == 1) | (((tx + (ty // 2) * 2) % 4) == 0)) & (s > 0.8), UMBER, 0.45, 1.35)
        c.paint(rect(c, x - 2.9 * s, y - 6.6 * s, x + 2.9 * s, y - 5.2 * s) & (tx % 2 == 0), PEARL, 0.25, 1.35)
        c.paint(rect(c, x - 2.9 * s, y - 5.4 * s, x + 2.9 * s, y - 4.6 * s), PEARL, 0.1, 1.36)
        for wx in (x - 1.2 * s, x + 1.2 * s):
            c.paint(rect(c, wx - 0.6 * s, y - 3.0 * s, wx + 0.6 * s, y - 0.4 * s) | c.circle(wx, y - 3.0 * s, 0.6 * s),
                    UMBER, 0.95, 1.5)
    run(-1, 31, far_top, far_h)
    tower(9, 11.0, 0.55)
    run(-1, 45, near_top, near_h)
    tower(31, 17.5, 0.9)
    tower(15, 26.0, 1.2)
    frame(c)
    return encode(c.to_tiles())


# ---------------------------------------------------------------------------
# Master
# ---------------------------------------------------------------------------

def terracotta():
    """The Terracotta Army, c. 210 BC: three rows of clay warriors in the pit, each row standing in front of
    an earth wall, the pit floor below; grey-brown clay with small traces of their old paint."""
    c = Canvas(44, 40)
    X, Y = c.X, c.Y
    tx, ty = tiles(c)
    # dark shadowed trenches behind the rows
    c.paint(ALL(c), UMBER, 0.95)

    def earth(y0, y1):
        """A band of rammed earth seen from the front: a lit top edge and darker layers below."""
        m = (Y >= y0 + 0.4 * np.sin(X * 0.9)) & (Y < y1)
        c.paint(m, SAFFRON, np.clip(0.88 + 0.12 * (((ty - int(y0)) % 2) == 1), 0, 1), 1.1)
        c.paint(m & (Y < y0 + 1.0 + 0.4 * np.sin(X * 0.9)), SAFFRON, 0.55, 1.15)
    earth(0, 2.2)

    def warrior(x, hy, s, paint):
        # legs and shoes, a painted hem, grey clay robe and arms with painted cuffs, a brown armour vest with
        # rivet dots, a red scarf, a round pale head with its topknot
        for side in (-1, 1):
            c.paint(rect(c, x + side * 1.05 * s - 0.7 * s, hy + 8.4 * s, x + side * 1.05 * s + 0.7 * s, hy + 10.1 * s),
                    PEARL, 0.8, 1.2)
            c.paint(ellipse(c, x + side * 1.2 * s, hy + 10.2 * s, 1.0 * s, 0.5 * s), UMBER, 0.6, 1.25)
        body = ellipse(c, x, hy + 3.4 * s, 3.1 * s, 1.4 * s) | rect(c, x - 2.6 * s, hy + 3.4 * s, x + 2.6 * s, hy + 7.4 * s)
        c.paint(body, PEARL, np.clip(0.6 + 0.3 * np.abs(X - x) / (2.4 * s), 0, 1), 1.2)
        for side in (-1, 1):
            c.paint(tube(c, [(x + side * 2.6 * s, hy + 3.5 * s), (x + side * 3.0 * s, hy + 7.4 * s)], 1.5 * s, 1.3 * s), PEARL, 0.75, 1.25)
            c.paint(ellipse(c, x + side * 2.95 * s, hy + 6.5 * s, 0.8 * s, 0.75 * s), paint, 0.45, 1.3)
            c.paint(c.circle(x + side * 3.0 * s, hy + 7.9 * s, 0.75 * s), PEARL, 0.3, 1.3)
        c.paint(c.poly_mask([(x - 2.3 * s, hy + 7.2 * s), (x + 2.3 * s, hy + 7.2 * s), (x + 2.6 * s, hy + 8.6 * s),
                             (x - 2.6 * s, hy + 8.6 * s)]), paint, 0.45, 1.3)
        vest = rect(c, x - 1.4 * s, hy + 3.1 * s, x + 1.4 * s, hy + 6.9 * s)
        c.paint(vest, UMBER, 0.2, 1.35)
        rivets = ((tx % 2) == 0) & ((ty % 2) == 1) & (np.abs(X - x) < 1.1 * s) & (Y > hy + 3.5 * s) & (Y < hy + 6.7 * s)
        c.paint(vest & rivets, PEARL, 0.35, 1.4)
        c.paint(ellipse(c, x, hy + 2.3 * s, 1.5 * s, 0.7 * s), EMBER, 0.45, 1.4)
        c.paint(c.circle(x, hy, 1.9 * s), PEARL, 0.6, 1.4)
        c.paint((c.circle(x, hy, 1.9 * s) & (Y < hy - 1.0 * s)) | c.circle(x + 0.7 * s, hy - 2.1 * s, 0.95 * s), UMBER, 0.3, 1.5)
        for side in (-1, 1):   # one dark tile per eye
            c.paint((tx == int(x + side * 0.75 * s)) & (ty == int(hy + 0.2 * s)), UMBER, 0.9, 1.7)
    # three rows, back to front; each row's legs are hidden by the earth wall in front of it
    paints = (LAPIS, FERN, SAFFRON, LAPIS, FERN, EMBER, FERN, LAPIS)
    rows = ((4.5, 0.85, 6.9, 3.4, 10.8), (15.3, 0.92, 7.5, 0.0, 22.3), (27.0, 1.0, 8.2, 4.1, 37.7))
    for k, (hy, s, step, off, wall) in enumerate(rows):
        xs = np.arange(22 - off - step * 3, 46, step)
        for i, x in enumerate(xs):
            warrior(x, hy, s, paints[(i * 3 + k) % len(paints)])
        earth(wall, wall + 2.1 if k < 2 else 40)
    for x0 in (0, 42.4):   # the side walls of the pit
        c.paint(rect(c, x0, 0, x0 + 1.6, 40), SAFFRON, 0.95, 1.3)
    frame(c)
    return encode(c.to_tiles())


def colosseum():
    """The Colosseum, AD 80: the curved outer wall with three tiers of arches and the attic storey, broken
    away on the right where the brick inner ring shows."""
    c = Canvas(46, 40)
    X, Y = c.X, c.Y
    cx, R, D, eye = 15.0, 60.0, 45.0, 40.0
    # map each screen column to an angle round the drum; v is the height on the wall seen square-on
    th = np.linspace(-0.6, 1.2, 3000)
    theta = np.interp(X, cx + R * np.sin(th) * D / (D + R * (1 - np.cos(th))), th)
    f = D / (D + R * (1 - np.cos(theta)))
    v = eye + (Y - eye) / f
    sarc = R * theta
    # sky and a cloud
    c.paint(ALL(c), LAPIS, np.clip(0.5 - 0.4 * Y / 16, 0.05, 1))
    cloud(c, [(35, 4.5, 1.6), (37.5, 3.6, 2.1), (40, 4.7, 1.5)])
    # where the outer wall has fallen (right), in steps of broken blocks, the lower inner ring shows
    step = ((np.floor(v / 1.7) * 37) % 5 - 2) * 0.7
    edge_s = np.where(v < 19.5, 20.0, np.where(v < 28.0, 25.5, 99.0)) + step
    broken = sarc > edge_s
    inner = broken & (v > 17.0) & (v < 36.5)
    c.paint(inner, PEARL, np.clip(0.55 + 0.15 * ((np.floor(v / 1.2) % 2) == 0), 0, 1))
    ia = (sarc / 4.2) % 1.0
    iarch = inner & (np.abs(ia - 0.5) < 0.26) & (((v - 17.0) % 6.0) > 2.2)
    c.paint(iarch, UMBER, 0.95, 1.2)
    c.paint(iarch & (v < 22.5), LAPIS, 0.2, 1.25)
    # the outer wall: travertine cornices and spandrels, warm half-columns, arches showing shadow, the brick
    # of the inner corridors, or the sky where the vaults behind have gone
    wall = ~broken & (v > 4.5) & (v < 36.5)
    c.paint(wall, PEARL, np.clip(0.1 + 0.3 * theta + 0.12 * ((np.floor(v / 1.2) % 2) == 0), 0, 1))
    a = (sarc / 5.4 + 0.5) % 1.0
    bay = np.floor(sarc / 5.4 + 0.5).astype(int)
    for k, (top, bot) in enumerate(((28.0, 36.5), (19.5, 28.0), (11.0, 19.5))):
        tier = wall & (v > top + 1.3) & (v < bot)
        c.paint(tier & (np.abs(a - 0.5) > 0.37), SAFFRON, np.clip(0.55 + 0.3 * theta, 0, 1), 1.2)
        spring = bot - 4.6
        arch = tier & (np.abs(a - 0.5) < 0.25) & ((v > spring) | ((((a - 0.5) * 5.4) ** 2 + (v - spring) ** 2) < 1.35 ** 2))
        c.paint(arch, UMBER, 0.95, 1.2)
        lit = arch & (v > spring + 0.6)
        if k == 0:
            c.paint(lit & ((bay % 3) == 1), EMBER, 0.6, 1.25)
        elif k == 1:
            c.paint(lit & (((bay % 3) == 2) | (sarc > 17)), LAPIS, 0.2, 1.3)
            c.paint(lit & ((bay % 3) == 0) & (sarc <= 17), EMBER, 0.6, 1.25)
        else:
            c.paint(lit, LAPIS, 0.15, 1.3)
    # the attic: pilasters and small square windows in every other bay
    attic = wall & (v < 11.0)
    c.paint(attic & (np.abs(a - 0.5) > 0.4), SAFFRON, np.clip(0.45 + 0.3 * theta, 0, 1), 1.2)
    c.paint(attic & (np.abs(a - 0.5) < 0.17) & (np.abs(v - 7.9) < 1.0), UMBER, 0.9, 1.3)
    # the broken edge: a jagged brick buttress, and plants growing on the ruin
    c.paint(~broken & (sarc > edge_s - 1.8) & (v > 4.5) & (v < 36.5), EMBER, 0.8, 1.35)
    r = random.Random(80)
    for _ in range(12):
        tv, x0, x1 = r.choice(((4.6, 1, 31), (11.0, 1, 31), (19.5, 1, 35), (28.0, 1, 44)))
        px = r.uniform(x0, x1)
        py = eye + (tv - eye) * np.interp(px, X[0], f[0])
        c.paint(ellipse(c, px, py, 1.1, 0.7), FERN, 0.45, 1.45)
    # the lawn in front with a pale path and bushes
    ground = v >= 36.5
    c.paint(ground, FERN, np.clip(0.35 + 0.2 * np.sin(X * 1.3), 0, 1))
    c.paint(ground & (np.abs(X - 20 - (Y - 37) * 2.5) < 2.2 + (Y - 37) * 0.6), PEARL, 0.35, 1.1)
    for bx in (3, 8.5, 27, 33, 40):
        c.paint(ellipse(c, bx, 37.2, 1.8, 1.3), FERN, 0.9, 1.3)
    frame(c)
    return encode(c.to_tiles())


SCENES = {
    "lascaux": lascaux, "pyramids": pyramids, "stonehenge": stonehenge, "goldenmask": golden_mask,
    "olympia": olympia, "greatwall": great_wall, "terracotta": terracotta, "colosseum": colosseum,
}
