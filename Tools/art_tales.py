"""Tales pack: eight iconic scenes from fairy tales and fables (Grimm, Perrault, Andersen, Aesop, English
folk tales), drawn with the supersampled Canvas of art.py (a tile's colour family comes from the dominant
object under it, its tone from the shading). All designs are original; nothing follows a film version.

Gentle: Little Red Riding Hood, Jack and the Beanstalk, the Tortoise and the Hare, Rapunzel.
Challenge: the Snow Queen's sleigh, Cinderella at midnight.
Master (busy, every colour in many islands): the gingerbread house, the Princess and the Pea.
"""
import math
import random

import numpy as np
from scipy import ndimage

from art import Canvas, LAPIS, SAFFRON, FERN, EMBER, UMBER, PEARL, encode
from art_scenes import ALL, ellipse, rect, tube, frame, sky, cloud, smooth_noise


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------

def bezier(p0, p1, p2, n=16):
    return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
             (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]) for t in np.linspace(0, 1, n)]


def tiles(c):
    return np.floor(c.X).astype(int), np.floor(c.Y).astype(int)


def halo(mask, px=6):
    """A rim about px/8 tiles wide just outside a mask (for dark outlines)."""
    return ndimage.binary_dilation(mask, iterations=px) & ~mask


def heart_leaf(c, bx, by, ang, s, shade=0.0):
    """A heart-shaped bean leaf s tiles long from its stalk end (bx, by) in direction ang, dark rim and rib."""
    ca, sa = math.cos(ang), math.sin(ang)
    u = (c.X - bx) * ca + (c.Y - by) * sa
    v = -(c.X - bx) * sa + (c.Y - by) * ca
    t = np.clip(u / s, 0, 1)
    half = s * 0.5 * np.sqrt(np.clip(t * 2.2, 0, 1)) * (1 - t) ** 0.7 * 1.25
    m = (u >= 0) & (u <= s) & (np.abs(v) <= half)
    c.paint(m, FERN, shade, 1.35)
    c.paint(m & (np.abs(v) > half - 0.6), FERN, 0.8, 1.36)
    c.paint(m & (np.abs(v) < 0.3) & (u < s * 0.8), FERN, 0.6, 1.37)
    return m


def sprite(c, x0, y0, rows, pal, prio=1.8):
    """Paint a tile-exact pixel sprite: each character of `rows` maps through pal to (family, shade); '.' is
    left alone. The top-left tile is (x0, y0)."""
    tx, ty = tiles(c)
    for j, row in enumerate(rows):
        for i, ch in enumerate(row):
            if ch in pal:
                fam, shade = pal[ch]
                c.paint((tx == x0 + i) & (ty == y0 + j), fam, shade, prio)


# the wolf's head in profile, facing left (D rim, G/g greys, L pale fur, Y eye, E inner ear, R tongue)
WOLF = ["......D......",
        ".....DGD..D..",
        ".....DEGDDGD.",
        "....DGEGGGEGD",
        "....DGGGGGGGG",
        "...DGgGGGGGGG",
        "..DgDYDGGGGGG",
        ".DggggggGGGGG",
        "DDgggggggGGGG",
        "DDDDDDLLgGGGG",
        ".DRRDLLLLgGGG",
        "..DRDDLLLLLGG",
        "...D..DLLLLLG",
        "........DDLLL"]


# Hansel and Gretel seen from the side, facing right (H hair, B braid, F face, h hand, J jacket, D dress,
# A apron, P legs, S shoes)
HANSEL = ["..HHH..", ".HHHHH.", ".HHHFF.", ".HHFFF.", "..FFF..", ".JJJJJ.", "JJJJJJJ", "hJJJJJh", ".JJJJJ.",
          ".PP.PP.", ".PP.PP.", ".PP.PP.", ".SS.SSS"]
GRETEL = ["..HHH..", ".HHHHH.", "BHHHFF.", "BHHFFF.", "B.FFF..", ".DDDDD.", "DDDAAD.", "hDDAADh", "DDDAADD",
          "DDDDDDD", ".PP.PP.", ".SS.SSS"]


# the princess sitting up in bed: crown, golden hair, pale face, pink nightgown
PRINCESS = ["..Y..Y..Y..", "..YYYYYYY..", ".HHHHHHHHH.", ".HHFFFFFHH.", ".HHFFFFFHH.", ".HHHFFFHHH.",
            "HHGGGGGGGHH", "HFGGGGGGGFH", ".GGGGGGGGG."]


def flower(c, x, y, r, fam, shade=0.15, heart=SAFFRON, prio=1.4):
    """A five-petalled flower about 2r + 1 tiles across."""
    for k in range(5):
        a = k * 2 * math.pi / 5 + x
        c.paint(c.circle(x + r * math.cos(a), y + r * math.sin(a), r * 0.62), fam, shade, prio)
    c.paint(c.circle(x, y, r * 0.5), heart, 0.2, prio + 0.1)


def flake(c, x, y, s, fam=PEARL, shade=0.0, prio=1.7):
    """A six-armed snowflake s tiles in radius."""
    m = c.circle(x, y, 0.45 * s)
    for k in range(3):
        a = k * math.pi / 3
        m |= c.line_mask([(x - s * math.cos(a), y - s * math.sin(a)), (x + s * math.cos(a), y + s * math.sin(a))], 0.45)
    c.paint(m, fam, shade, prio)


def swirl(c, cx, cy, r, fam_a, fam_b, arms=3, twist=1.3):
    """A round lollipop with spiral stripes in two colours; returns the disc mask."""
    d = np.hypot(c.X - cx, c.Y - cy)
    disc = d <= r
    band = (np.arctan2(c.Y - cy, c.X - cx) * arms / (2 * math.pi) + d * twist / r * arms) % 1.0 < 0.5
    c.paint(disc & band, fam_a, 0.35, 1.6)
    c.paint(disc & ~band, fam_b, 0.1, 1.6)
    return disc


# ---------------------------------------------------------------------------
# gentle
# ---------------------------------------------------------------------------

def red_riding_hood():
    """The girl in the red cloak walks the forest path with her basket; the wolf peeks out from behind
    a great trunk, his tail showing on the far side."""
    c = Canvas(40, 44)
    X, Y = c.X, c.Y
    n = smooth_noise(c, 41, 0.45)
    # deep green wood with pale dapples of light, a few distant trunks
    c.paint(ALL(c), FERN, np.clip(0.78 + 0.2 * n, 0, 1))
    c.paint((smooth_noise(c, 43, 0.6) > 0.3) & (Y < 30), FERN, 0.15)
    for (tx, w) in ((8.5, 1.4), (12.0, 1.0), (24.5, 1.8)):
        c.paint(rect(c, tx - w / 2, -1, tx + w / 2, 31), UMBER, 0.2)
    # grass, then the winding path (light earth with sunny spots)
    c.paint(Y > 29.5 + 0.8 * np.sin(X * 0.4), FERN, np.clip(0.35 + 0.15 * n, 0, 1))
    t = np.clip((44 - Y) / 15.0, 0, 1)
    path = (Y > 29.5) & (np.abs(X - (17 + 7 * t + 3 * np.sin(t * math.pi))) < 8.0 * (1 - t) + 0.7)
    c.paint(path, UMBER, np.clip(0.05 + 0.1 * n, 0, 1), 1.05)
    c.paint(path & (smooth_noise(c, 47, 1.1) > 0.45), SAFFRON, 0.15, 1.1)
    # the wolf: a grey head peering round the trunk (tile sprite), his tail out the far side
    tail = tube(c, [(34.0, 31.0), (36.6, 29.6), (38.0, 26.6)], 2.8, 1.8)
    c.paint(halo(tail, 6), UMBER, 1.0, 1.5)
    c.paint(tail, PEARL, 0.85, 1.4)
    c.paint(c.circle(38.0, 26.4, 1.0), PEARL, 0.1, 1.45)
    sprite(c, 18, 11, WOLF, {"D": (UMBER, 1.0), "G": (PEARL, 0.95), "g": (PEARL, 0.62), "L": (PEARL, 0.05),
                             "Y": (SAFFRON, 0.2), "E": (EMBER, 0.15), "R": (EMBER, 0.55)})
    # great dark trunks with root flares (the wolf's tree on the right)
    for (tx, w, bot) in ((1.0, 3.6, 36), (32.6, 6.2, 34.0)):
        trunk = (np.abs(X - tx) < w / 2 + np.clip(Y - bot + 3, 0, None) * 0.6) & (Y < bot)
        c.paint(trunk, UMBER, np.clip(0.72 + 0.2 * np.sin(X * 2.2 + np.sin(Y * 0.5)), 0, 1), 1.2)
    # flowers along the path
    for (fx, fy, fam) in ((5, 40, EMBER), (8.5, 34, PEARL), (27.5, 38, PEARL), (33, 41.5, EMBER), (37, 36.5, SAFFRON)):
        flower(c, fx, fy, 0.8, fam, 0.1)
    # the girl: blue skirt, legs, red cloak and hood, face
    cx = 13.5
    c.paint(c.poly_mask([(cx - 3.4, 37.2), (cx + 4.0, 37.2), (cx + 3.4, 39.6), (cx - 2.8, 39.6)]), LAPIS, 0.55, 1.3)
    for lx in (cx - 1.0, cx + 1.4):
        c.paint(rect(c, lx - 0.5, 39.4, lx + 0.5, 41.6) | ellipse(c, lx + 0.4, 41.6, 0.9, 0.55), UMBER, 0.95, 1.5)
    cloak = c.poly_mask([(cx - 2.2, 24.0), (cx + 2.6, 24.0), (cx + 6.0, 37.6), (cx + 1.0, 38.4), (cx - 5.2, 37.8)])
    hood = c.circle(cx + 0.4, 21.6, 3.7)
    c.paint(cloak | hood, EMBER, np.clip(0.6 + 0.25 * (np.sin(X * 1.6 - Y * 0.3) > 0.6), 0, 1), 1.2)
    c.paint(c.circle(cx + 1.5, 22.4, 2.1), PEARL, 0.05, 1.5)
    c.paint(ellipse(c, cx + 1.5, 20.8, 2.0, 0.8), UMBER, 0.55, 1.55)
    c.paint(c.circle(cx + 2.5, 22.2, 0.42), UMBER, 1.0, 1.9)
    # her arm and the basket held out towards the wolf
    c.paint(c.line_mask([(cx + 2.6, 27.0), (cx + 5.6, 30.4)], 1.3), EMBER, 0.85, 1.4)
    c.paint(c.line_mask(bezier((cx + 4.6, 31.0), (cx + 6.8, 26.0), (cx + 9.0, 31.0)), 0.5), UMBER, 0.8, 1.6)
    basket = c.poly_mask([(cx + 3.8, 31.0), (cx + 9.8, 31.0), (cx + 9.0, 34.6), (cx + 4.6, 34.6)])
    c.paint(basket, SAFFRON, np.where((np.floor(X) + np.floor(Y)) % 2 == 0, 0.55, 0.85), 1.5)
    c.paint(ellipse(c, cx + 6.8, 31.0, 3.0, 0.9), PEARL, 0.15, 1.55)
    frame(c)
    return encode(c.to_tiles())


def beanstalk():
    """Jack's beanstalk twists up from the cottage garden through the clouds to the giant's golden castle."""
    c = Canvas(36, 48)
    X, Y = c.X, c.Y
    sky(c, 0.75, 0.1, horizon=44)
    cloud(c, [(4, 30, 1.6), (6.5, 29, 2.1), (9, 30.2, 1.4)])
    cloud(c, [(28, 37, 1.5), (30.5, 36, 2.0), (33, 37.2, 1.4)])
    # the giant's castle: golden walls, three towers with red cones
    gold = np.clip(0.3 + 0.35 * ((X % 6) > 3), 0, 1)
    c.paint(rect(c, 7.5, 8.5, 28.5, 16), SAFFRON, gold)
    c.paint(rect(c, 7.5, 7.3, 28.5, 8.5) & (np.floor(X / 1.5) % 2 == 0), SAFFRON, 0.4)
    for (tx, top, hw) in ((9.0, 6.0, 2.2), (27.0, 6.0, 2.2), (18.0, 4.5, 2.8)):
        c.paint(rect(c, tx - hw, top, tx + hw, 16), SAFFRON, np.clip(0.2 + 0.25 * (X - tx + hw) / hw, 0, 1), 1.1)
        c.paint(c.poly_mask([(tx - hw - 0.8, top + 0.2), (tx + hw + 0.8, top + 0.2), (tx, top - 4.6)]), EMBER, 0.55, 1.2)
        c.paint(rect(c, tx - 0.6, top + 2.0, tx + 0.6, top + 4.2) | c.circle(tx, top + 2.0, 0.6), UMBER, 0.9, 1.6)
    c.paint(rect(c, 16.6, 11.5, 19.4, 16) | c.circle(18, 11.5, 1.4), UMBER, 0.85, 1.5)
    # the cloud bank the castle stands on
    cloud(c, [(0, 16.5, 3.0), (4.5, 15.0, 3.4), (9.5, 16.4, 2.8), (14.0, 15.2, 3.4), (19.5, 16.6, 3.2), (24.5, 15.0, 3.4),
              (29.5, 16.2, 3.0), (34.5, 15.4, 3.2)])
    c.paint(ellipse(c, 18, 18.2, 17, 1.6) & (Y > 17), PEARL, 0.55, 1.1)
    # green hills and the cottage at the foot
    c.paint(Y > 41.5 + 1.2 * np.sin(X * 0.3 + 1), FERN, np.clip(0.3 + 0.1 * np.sin(X * 1.7 + Y), 0, 1))
    c.paint(rect(c, 2.0, 38.5, 11.0, 44.5), PEARL, np.clip(0.15 + 0.06 * (X - 2.0), 0, 1), 1.2)
    c.paint(c.poly_mask([(0.5, 39.0), (12.5, 39.0), (9.0, 34.0), (4.0, 34.0)]), SAFFRON, np.clip(0.55 + 0.1 * np.sin(X * 3), 0, 1), 1.2)
    c.paint(rect(c, 8.6, 31.5, 10.0, 35), UMBER, 0.75, 1.3)
    c.paint(rect(c, 3.5, 40.6, 5.5, 44.5), UMBER, 0.9, 1.5)
    c.paint(rect(c, 7.2, 40.4, 9.6, 42.6), LAPIS, 0.6, 1.5)
    # the stalk: an S-curve of two strands twisting round each other (back halves painted first)
    def spine(u):
        return 19.5 + 5.0 * math.sin(2 * math.pi * 0.9 * u + 0.3), 46.5 - 31.5 * u
    pts = []
    for u in np.linspace(0, 1, 200):
        xc, y = spine(u)
        for k in (0, 1):
            ph = u * 24 + k * math.pi
            pts.append((math.cos(ph), xc + (1.7 - 0.7 * u) * math.sin(ph), y, 3.4 - 1.6 * u))
    pts.sort(key=lambda p: p[0])
    for depth, x, y, w in pts:
        c.paint(c.circle(x, y, w / 2), FERN, 0.98 - 0.45 * max(0, depth), 1.3)
    # huge heart-shaped leaves on alternate sides
    for (u, side, s) in ((0.08, -1, 7.5), (0.25, 1, 8.0), (0.43, -1, 7.4), (0.62, 1, 6.6), (0.78, -1, 6.0), (0.93, 1, 5.0)):
        xc, y = spine(u)
        heart_leaf(c, xc + side * 1.6, y, -math.pi / 2 + side * 1.2, s)
    # Jack climbing on the right of the stalk, reaching up
    jx, jy = 19.8, 27.5
    c.paint(c.line_mask([(jx - 0.4, jy - 2.4), (jx - 1.8, jy - 5.2)], 0.9), EMBER, 0.45, 1.85)
    c.paint(c.circle(jx, jy - 3.6, 1.25), PEARL, 0.1, 1.8)
    c.paint(ellipse(c, jx + 0.2, jy - 4.5, 1.4, 0.8), SAFFRON, 0.3, 1.85)
    c.paint(c.poly_mask([(jx - 1.3, jy - 2.4), (jx + 1.3, jy - 2.4), (jx + 1.5, jy + 1.0), (jx - 1.3, jy + 1.0)]), EMBER, 0.45, 1.8)
    c.paint(rect(c, jx - 1.3, jy + 1.0, jx - 0.2, jy + 3.8) | rect(c, jx + 0.3, jy + 1.0, jx + 1.4, jy + 3.0), LAPIS, 0.8, 1.8)
    frame(c)
    return encode(c.to_tiles())


def tortoise_hare():
    """Aesop: the hare sleeps under the tree by the road while the tortoise plods on to the finishing post."""
    c = Canvas(48, 36)
    X, Y = c.X, c.Y
    sky(c, 0.6, 0.12, horizon=14)
    c.paint(c.circle(40, 5, 2.8), SAFFRON, 0.1, 1.2)
    cloud(c, [(22, 5, 1.6), (24.5, 4.2, 2.1), (27, 5.2, 1.5)])
    # rolling hills: a dark far ridge, then the meadow
    c.paint(Y > 11 + 2.0 * np.sin(X * 0.16 + 0.5), FERN, 0.8)
    c.paint(Y > 16 + 2.2 * np.sin(X * 0.11 + 4.0), FERN, np.clip(0.3 + 0.1 * np.sin(X * 1.3 + Y * 2), 0, 1))
    # the winding road from the far hills, round past the tree and across to the finish on the right
    road = np.zeros_like(X, bool)
    pts = bezier((30, 13), (10, 15), (21, 21.5), 24) + bezier((21, 21.5), (27, 27.5), (48, 28.0), 24)[1:]
    for i, (px, py) in enumerate(pts):
        road |= c.circle(px, py, 0.4 + 3.6 * i / len(pts))
    c.paint(road & (Y > 12.5), PEARL, np.clip(0.5 + 0.12 * np.sin(X * 0.7), 0, 1), 1.1)
    # the shady tree
    c.paint(tube(c, [(4.5, 27), (4.2, 15), (5.5, 9)], 2.8, 1.6), UMBER, 0.85, 1.2)
    canopy = np.zeros_like(X, bool)
    for (a, b, r) in ((1, 8, 4.0), (6, 5, 4.6), (11, 7.5, 4.0), (3, 12, 3.4), (8.5, 11.5, 3.4)):
        canopy |= c.circle(a, b, r)
    c.paint(canopy, FERN, np.clip(0.8 + 0.15 * smooth_noise(c, 3, 1.0), 0, 1), 1.1)
    # the hare asleep in its shade: a brown loaf with long ears raised, eyes shut, white tail and chin
    hx, hy = 12.0, 28.0
    body = ellipse(c, hx, hy, 5.2, 3.2) | ellipse(c, hx - 3.6, hy + 2.4, 2.6, 1.0)
    head = ellipse(c, hx + 5.0, hy - 1.0, 2.7, 2.3, 0.2)
    ears = c.line_mask([(hx + 4.2, hy - 2.6), (hx + 1.2, hy - 9.0)], 1.5) | c.line_mask([(hx + 5.6, hy - 2.8), (hx + 5.0, hy - 9.6)], 1.5)
    hare = body | head | ears
    c.paint(halo(hare, 5), UMBER, 1.0, 1.45)
    c.paint(hare, UMBER, np.clip(0.05 + 0.06 * (Y - hy + 3), 0, 0.35), 1.45)
    c.paint(c.line_mask([(hx + 4.4, hy - 3.6), (hx + 2.1, hy - 8.2)], 0.5) | c.line_mask([(hx + 5.5, hy - 3.8), (hx + 5.1, hy - 8.6)], 0.5), EMBER, 0.05, 1.5)
    c.paint(ellipse(c, hx + 6.0, hy + 0.5, 1.8, 0.9) | ellipse(c, hx + 3.6, hy + 2.6, 2.0, 0.7), PEARL, 0.1, 1.55)
    c.paint(c.circle(hx - 5.2, hy - 0.8, 1.2), PEARL, 0.0, 1.6)
    c.paint(c.line_mask([(hx + 5.0, hy - 1.4), (hx + 6.3, hy - 1.2)], 0.45), UMBER, 1.0, 1.8)
    c.paint(c.circle(hx + 7.6, hy - 0.5, 0.5), EMBER, 0.2, 1.8)
    # the tortoise on the road: domed shell with golden plates, head stretched forward
    tx, ty = 30.5, 27.6
    skin = (tube(c, [(tx + 4.0, ty - 0.6), (tx + 7.0, ty - 1.6)], 1.8, 1.6) | c.circle(tx + 7.6, ty - 1.8, 1.5))
    for (lx, lean) in ((tx - 4.0, -0.6), (tx - 1.6, 0.5), (tx + 1.6, -0.5), (tx + 4.0, 0.6)):
        skin |= c.line_mask([(lx, ty - 0.5), (lx + lean, ty + 2.0)], 1.4)
    c.paint(halo(skin, 4), UMBER, 0.9, 1.35)
    c.paint(skin, FERN, 0.55, 1.4)
    c.paint(c.circle(tx + 8.2, ty - 2.2, 0.4), UMBER, 1.0, 1.9)
    shell = ellipse(c, tx, ty, 6.0, 5.0) & (Y < ty + 0.4)
    c.paint(shell, UMBER, 0.8, 1.4)
    for (px, py, rx, ry) in ((tx, ty - 3.0, 1.7, 1.1), (tx - 3.0, ty - 1.5, 1.4, 1.0), (tx + 3.0, ty - 1.5, 1.4, 1.0),
                             (tx - 1.4, ty - 0.6, 1.0, 0.6), (tx + 1.4, ty - 0.6, 1.0, 0.6)):
        c.paint(ellipse(c, px, py, rx, ry) & shell, SAFFRON, 0.55, 1.5)
    c.paint(rect(c, tx - 6.1, ty - 0.2, tx + 6.1, ty + 0.8), SAFFRON, 0.85, 1.45)
    # the finishing posts with the red ribbon across the road
    for (px, top, bot) in ((41.0, 17.0, 27.5), (45.0, 19.0, 33.5)):
        post = rect(c, px - 1.0, top, px + 1.0, bot)
        c.paint(post, PEARL, 0.0, 1.5)
        c.paint(post & (np.floor(Y) % 3 == 0), EMBER, 0.6, 1.55)
        c.paint(c.poly_mask([(px - 0.1, top - 4.2), (px + 4.4, top - 2.7), (px - 0.1, top - 1.2)]), SAFFRON, 0.2, 1.6)
        c.paint(c.line_mask([(px - 0.5, top), (px - 0.5, top - 4.4)], 0.6), UMBER, 0.9, 1.6)
    c.paint(c.line_mask(bezier((41.0, 21.5), (43.0, 25.5), (45.0, 23.5)), 1.0), EMBER, 0.4, 1.7)
    frame(c)
    return encode(c.to_tiles())


def rapunzel():
    """The doorless tower in the wood: one high window, the golden braid let down to the ground, thorns below."""
    c = Canvas(36, 48)
    X, Y = c.X, c.Y
    sky(c, 0.7, 0.08, horizon=34)
    cloud(c, [(4, 9, 1.6), (6.5, 8, 2.2), (9, 9.3, 1.5)])
    # the dark wood behind: a line of rounded tree tops
    tops = 30 + 2.2 * np.abs(np.sin(X * 0.42)) - 1.2 * np.sin(X * 0.13)
    c.paint(Y > tops, FERN, np.clip(0.72 + 0.15 * np.sin(X * 1.3), 0, 1))
    c.paint(Y > 41.5 + 0.8 * np.sin(X * 0.5), FERN, np.clip(0.3 + 0.12 * np.sin(X * 2.1 + Y), 0, 1))
    # the stone tower (lit from the left), with a ring of corbels and the red cone roof
    cx = 20.5
    half = np.interp(Y, [13, 44], [4.4, 5.2])
    tower = (Y >= 13) & (Y < 44) & (np.abs(X - cx) <= half)
    tx, ty = tiles(c)
    course = ((tx + 2 * (ty // 2)) % 4 == 0) & (ty % 2 == 0)
    cyl = np.clip(0.1 + 0.55 * ((X - cx) / half + 0.4) ** 2 / 2, 0, 0.8)
    c.paint(tower, PEARL, np.clip(cyl + 0.15 * course, 0, 1))
    c.paint(rect(c, cx - 5.4, 12.0, cx + 5.4, 13.6), UMBER, 0.65, 1.3)
    c.paint(c.poly_mask([(cx - 6.6, 12.3), (cx + 6.6, 12.3), (cx, 1.6)]), EMBER, np.clip(0.45 + 0.08 * (X - cx), 0, 1), 1.2)
    c.paint(c.line_mask([(cx, 2.0), (cx, 0.6)], 0.4), UMBER, 0.9, 1.4)
    # the window with Rapunzel leaning out
    win = rect(c, cx - 2.0, 16.0, cx + 2.0, 20.4) | c.circle(cx, 16.0, 2.0)
    c.paint(win, UMBER, 0.95, 1.5)
    c.paint(c.circle(cx, 17.2, 1.7), SAFFRON, 0.2, 1.6)
    c.paint(c.circle(cx, 17.8, 1.15), PEARL, 0.05, 1.7)
    c.paint(rect(c, cx - 2.6, 20.2, cx + 2.6, 21.2), PEARL, 0.4, 1.5)
    # the braid hanging down the wall to the ground, plaited, with a bow, coiled at the foot
    by = np.clip(Y, 20, 44)
    bxc = cx + 0.5 + 0.9 * np.sin((by - 20) * 0.16)
    braid = (Y > 20.0) & (Y < 44.0) & (np.abs(X - bxc) < 1.0)
    c.paint(braid, SAFFRON, np.where((Y - X * 0.6) % 1.6 < 0.8, 0.2, 0.6), 1.7)
    c.paint(ellipse(c, cx + 3.4, 44.2, 3.6, 1.2) & ~ellipse(c, cx + 3.4, 44.2, 1.6, 0.4), SAFFRON, 0.35, 1.6)
    c.paint(ellipse(c, cx + 1.0, 39.0, 1.4, 0.7), LAPIS, 0.5, 1.8)
    # brambles in the foreground: dark thorny stems with leaves and a few roses
    r = random.Random(9)
    for (x0, y0, x1, y1, x2, y2) in ((0, 38, 7, 31, 14, 47), (2, 47, 5, 35, 12, 37), (36, 37, 29, 31, 25, 47), (35, 47, 31, 37, 26, 39)):
        stem = bezier((x0, y0), (x1, y1), (x2, y2), 21)
        c.paint(c.line_mask(stem, 1.1), UMBER, 0.85, 1.4)
        for i in range(2, 19, 2):
            (ax, ay), (bx, by) = stem[i], stem[i + 1]
            ln = math.hypot(bx - ax, by - ay) or 1.0
            nx, ny = -(by - ay) / ln * (-1) ** (i // 2), (bx - ax) / ln * (-1) ** (i // 2)
            c.paint(c.poly_mask([(ax - 0.5 * (bx - ax) / ln, ay - 0.5 * (by - ay) / ln), (ax + 0.5 * (bx - ax) / ln, ay + 0.5 * (by - ay) / ln),
                                 (ax + 1.5 * nx, ay + 1.5 * ny)]), UMBER, 0.95, 1.45)
        for (sx, sy) in stem[3:-3:5]:
            c.paint(ellipse(c, sx + r.uniform(-1, 1), sy + r.uniform(-1.4, 0.4), 1.3, 0.7, r.uniform(0, 3)), FERN, 0.8, 1.35)
    for (fx, fy) in ((5.5, 36.5), (9.5, 41.0), (30.5, 36.0), (27.8, 42.0)):
        c.paint(c.circle(fx, fy, 1.0), EMBER, 0.55, 1.6)
    frame(c)
    return encode(c.to_tiles())


# ---------------------------------------------------------------------------
# challenge
# ---------------------------------------------------------------------------

def snow_queen():
    """Andersen: the Snow Queen's white sleigh flies through the storm, Kay's red sledge tied on behind,
    past her palace of ice spires above the frozen land."""
    c = Canvas(44, 42)
    X, Y = c.X, c.Y
    c.paint(ALL(c), LAPIS, np.clip(1.0 - 0.25 * Y / 32, 0, 1))
    # wind swirls of driven snow and flakes everywhere
    rr = random.Random(5)
    for (sx, sy, r0, a0, turn) in ((34, 7, 7.0, 3.6, 4.4), (15, 30, 8.0, 5.6, 3.4), (22, 4, 6.0, 0.2, 2.6), (3, 3, 5.0, 0.5, 2.0)):
        sp = [(sx + (r0 - 3.5 * t) * math.cos(a0 + turn * t), sy + (r0 - 3.5 * t) * 0.65 * math.sin(a0 + turn * t))
              for t in np.linspace(0, 1, 40)]
        c.paint(c.line_mask(sp, 0.8), PEARL, 0.25, 1.15)
    for _ in range(45):
        fx, fy = rr.uniform(1, 43), rr.uniform(1, 33)
        c.paint(c.circle(math.floor(fx) + 0.5, math.floor(fy) + 0.5, 0.5), PEARL, 0.0, 1.3)
    for _ in range(26):
        fx, fy = math.floor(rr.uniform(2, 42)) + 0.5, math.floor(rr.uniform(2, 32)) + 0.5
        c.paint(c.circle(fx, fy, 0.5) | c.line_mask([(fx - 1, fy), (fx + 1, fy)], 0.5) | c.line_mask([(fx, fy - 1), (fx, fy + 1)], 0.5),
                PEARL, 0.0, 1.35)
    # the ice palace: spires lit white on the left and blue on the right, with dark slit windows
    for (x, top, hw) in ((27.5, 22, 1.6), (30.5, 15, 2.0), (34.0, 9.5, 2.4), (37.5, 13, 2.0), (40.5, 18, 1.8),
                         (32.5, 22, 1.4), (36.0, 21, 1.4), (42.5, 24, 1.2)):
        spire = c.poly_mask([(x - hw, 35), (x - hw, top + hw * 2.4), (x, top), (x + hw, top + hw * 2.4), (x + hw, 35)])
        c.paint(spire, PEARL, np.where(X < x, 0.1, 0.45), 1.2)
        c.paint(ndimage.binary_erosion(spire, iterations=7) & (X >= x - 0.2), LAPIS, 0.15, 1.25)
        for wy in (top + hw * 2.4 + 1.5, top + hw * 2.4 + 6.0):
            c.paint(rect(c, x - 0.5, wy, x + 0.5, wy + 2.5) | c.circle(x, wy, 0.5), LAPIS, 0.95, 1.5)
    # the frozen land: snow drifts striped with blue shadow, snow-laden pines
    land = Y > 33 + 1.0 * np.sin(X * 0.3)
    c.paint(land, PEARL, 0.1, 1.25)
    c.paint(land & (np.sin(Y * 1.6 + np.sin(X * 0.35) * 2.0) > 0.45), LAPIS, 0.3, 1.25)
    for (px, py, s) in ((3.5, 39, 0.9), (8.0, 38, 1.1), (13, 40, 0.8)):
        for k in range(3):
            c.paint(c.poly_mask([(px - 2.6 * s + k * 0.5 * s, py - k * 2.4 * s), (px + 2.6 * s - k * 0.5 * s, py - k * 2.4 * s),
                                 (px, py - (k + 1.5) * 2.4 * s)]), FERN, 0.85, 1.3)
            c.paint(ellipse(c, px, py - (k + 1.0) * 2.4 * s, 1.6 * s - k * 0.3, 0.45), PEARL, 0.05, 1.35)
    # the white sleigh: a swan-neck prow curling high at the front, gold rim, curling gold runner
    body = c.poly_mask([(5.0, 15.5), (7.5, 15.0), (8.5, 18.0), (21.0, 18.0), (25.0, 14.0), (24.4, 10.6), (26.2, 9.6),
                        (28.4, 11.0), (28.0, 15.5), (24.0, 22.8), (8.0, 22.8), (5.0, 20.0)])
    c.paint(body, PEARL, np.clip(0.0 + 0.04 * (Y - 12), 0, 0.4), 1.5)
    c.paint(c.circle(26.5, 11.2, 0.75), SAFFRON, 0.5, 1.6)
    c.paint(c.line_mask([(5.0, 15.5), (7.5, 15.0), (8.5, 18.0), (21.0, 18.0), (25.0, 14.0), (24.4, 10.6), (26.2, 9.6)], 0.7),
            SAFFRON, 0.35, 1.6)
    c.paint(c.line_mask([(6.0, 25.0), (26.5, 25.0)] + bezier((26.5, 25.0), (31.5, 25.0), (30.0, 21.0), 8), 0.7), SAFFRON, 0.45, 1.6)
    for sx in (10, 16, 22):
        c.paint(c.line_mask([(sx, 22.6), (sx, 25.0)], 0.5), SAFFRON, 0.7, 1.55)
    # the Snow Queen standing in it: ice-blue robe and cloak flying back, white face, gold crown of spikes
    cloak = c.poly_mask([(11.0, 9.5), (6.5, 9.0), (2.0, 11.0), (4.0, 12.0), (1.5, 14.0), (8.0, 14.5), (10.5, 12.5)])
    robe = c.poly_mask([(10.0, 18.2), (17.0, 18.2), (15.4, 9.0), (11.4, 9.0)])
    c.paint(cloak | robe, LAPIS, np.where(X < 9, 0.3, 0.05), 1.55)
    c.paint(c.line_mask([(15.0, 11.0), (19.6, 13.4)], 1.1), LAPIS, 0.05, 1.6)
    c.paint(ellipse(c, 13.4, 9.4, 3.2, 1.1), PEARL, 0.2, 1.6)
    c.paint(c.circle(13.4, 6.8, 1.7), PEARL, 0.0, 1.65)
    c.paint(c.poly_mask([(11.4, 5.8), (11.4, 2.6), (12.4, 4.6), (13.4, 1.8), (14.4, 4.6), (15.4, 2.6), (15.4, 5.8)]), SAFFRON, 0.25, 1.7)
    # Kay's little red sledge tied on behind
    c.paint(c.line_mask([(6.0, 21.5), (4.4, 27.4)], 0.4), UMBER, 0.5, 1.5)
    c.paint(rect(c, 0.8, 27.4, 6.4, 29.0), EMBER, 0.55, 1.6)
    c.paint(c.line_mask([(1.0, 29.8), (6.6, 29.8), (7.2, 28.8)], 0.45), UMBER, 0.85, 1.6)
    c.paint(c.circle(3.4, 25.8, 1.0), PEARL, 0.1, 1.7)
    c.paint(ellipse(c, 3.4, 25.1, 1.2, 0.6), EMBER, 0.75, 1.75)
    frame(c)
    return encode(c.to_tiles())


def cinderella():
    """Perrault: midnight strikes on the great palace clock; one glass slipper is left on the grand stair
    and the pumpkin coach waits below."""
    c = Canvas(40, 46)
    X, Y = c.X, c.Y
    tx, ty = tiles(c)
    c.paint(ALL(c), LAPIS, 0.95)
    for (sx, sy, s) in ((2.5, 3.5, 1), (8.5, 2.5, 0), (5.5, 8.5, 1), (31.5, 2.5, 0), (36.5, 6.5, 1), (33.5, 10.5, 0), (10.5, 9.5, 0)):
        star = c.circle(sx, sy, 0.55)
        if s:
            star |= c.line_mask([(sx - 1, sy), (sx + 1, sy)], 0.5) | c.line_mask([(sx, sy - 1), (sx, sy + 1)], 0.5)
        c.paint(star, PEARL if s else SAFFRON, 0.0, 1.6)
    # the palace front: grey stone with a cornice and string course, rows of lit arched windows
    facade = (Y >= 13) & (Y < 31)
    c.paint(facade, PEARL, np.where(ty % 2 == 0, 0.75, 0.55))
    c.paint(rect(c, 0, 12, 40, 13.6) | rect(c, 0, 21.2, 40, 22.2), UMBER, 0.45, 1.1)
    c.paint(rect(c, 0, 10.8, 40, 12) & (tx % 2 == 0), PEARL, 0.3)
    for wx in (3.5, 9.0, 31.0, 36.5):
        for wy in (15.5, 24.5):
            w = rect(c, wx - 1.6, wy, wx + 1.6, wy + 4.5) | c.circle(wx, wy, 1.6)
            c.paint(w, SAFFRON, np.clip(0.05 + 0.1 * (Y - wy), 0, 1), 1.3)
            c.paint(rect(c, wx - 2.0, wy + 4.5, wx + 2.0, wy + 5.3), PEARL, 0.1, 1.3)
    # the clock tower in the middle, the clock at twelve
    c.paint(rect(c, 13, 3.5, 27, 31), PEARL, np.clip(0.3 + 0.03 * np.abs(X - 20), 0, 1), 1.05)
    c.paint(c.poly_mask([(12, 4.0), (28, 4.0), (20, 0.5)]), PEARL, 0.7, 1.1)
    c.paint(c.circle(20, 11.0, 6.0), SAFFRON, 0.45, 1.2)
    c.paint(c.circle(20, 11.0, 5.0), PEARL, 0.0, 1.25)
    for k in range(12):
        a = k * math.pi / 6
        c.paint(c.circle(20 + 4.0 * math.sin(a), 11.0 - 4.0 * math.cos(a), 0.5 if k % 3 else 0.7), UMBER, 0.85, 1.6)
    c.paint(c.line_mask([(20, 11.5), (20, 7.2)], 0.65) | c.line_mask([(20, 11.5), (20, 8.6)], 1.2), UMBER, 1.0, 1.8)
    c.paint(c.circle(20, 11.0, 0.7), SAFFRON, 0.6, 1.9)
    door = rect(c, 16.5, 23.5, 23.5, 31) | c.circle(20, 23.5, 3.5)
    c.paint(door, SAFFRON, np.clip(0.05 + 0.04 * (Y - 20), 0, 1), 1.3)
    c.paint(door & (np.abs(X - 20) < 0.3), UMBER, 0.7, 1.35)
    # the night forecourt, the grand stair with dark risers and a red runner down the middle
    c.paint(Y >= 31, LAPIS, np.where(ty % 2 == 0, 0.72, 0.9))
    t = np.clip((Y - 31) / 15, 0, 1)
    stair = (Y >= 31) & (X > 15.5 - 11 * t) & (X < 24.5 + 2.5 * t)
    edges = np.array([31, 32.4, 34.0, 35.8, 37.8, 40.0, 42.4, 45.0])
    lo = edges[np.clip(np.searchsorted(edges, Y) - 1, 0, 7)]
    c.paint(stair, PEARL, 0.05, 1.1)
    c.paint(stair & (Y - lo < 0.6), UMBER, 0.6, 1.15)
    c.paint(stair & (np.abs(X - (20 - 4.2 * t)) < 1.5 + 1.0 * t), EMBER, np.where(Y - lo < 0.6, 0.85, 0.5), 1.2)
    for (x0, x1) in ((15.5, 4.5), (24.5, 27)):
        c.paint(c.line_mask([(x0, 30.6), (x1, 46)], 1.3), PEARL, 0.45, 1.3)
    # the glass slipper on a step
    shoe = ellipse(c, 13.4, 39.4, 3.0, 1.1) | c.poly_mask([(13.2, 38.6), (16.4, 36.2), (17.2, 36.8), (16.4, 40.2)])
    c.paint(halo(shoe, 4), LAPIS, 0.7, 1.75)
    c.paint(shoe, LAPIS, 0.05, 1.8)
    c.paint(ellipse(c, 12.2, 39.0, 1.3, 0.45), PEARL, 0.0, 1.9)
    c.paint(c.line_mask([(16.6, 37.0), (16.8, 40.8)], 0.55), LAPIS, 0.45, 1.9)
    # a lamp at the foot of the stair, and the pumpkin coach waiting below
    c.paint(rect(c, 2.3, 33, 3.3, 46), UMBER, 0.9, 1.4)
    c.paint(c.circle(2.8, 32.0, 1.4), SAFFRON, 0.05, 1.5)
    coach = ellipse(c, 33.0, 37.0, 6.4, 5.4)
    c.paint(coach, EMBER, np.clip(0.25 + 0.25 * np.abs(X - 33) / 6.4, 0, 1), 1.3)
    for dx in (-4.0, -1.5, 1.5, 4.0):
        c.paint(c.line_mask(bezier((33 + dx * 0.4, 31.8), (33 + dx * 1.25, 37), (33 + dx * 0.4, 42.2)), 0.45) & coach, EMBER, 0.85, 1.4)
    c.paint(rect(c, 31.2, 34.5, 34.8, 38.5) | c.circle(33, 34.5, 1.8), SAFFRON, 0.1, 1.5)
    c.paint(c.line_mask(bezier((31.6, 31.8), (33, 29.8), (34.6, 30.6)), 0.7), FERN, 0.6, 1.6)
    for wx in (28.5, 37.5):
        c.paint(c.circle(wx, 43.0, 2.6) & ~c.circle(wx, 43.0, 1.9), SAFFRON, 0.5, 1.6)
        c.paint(c.line_mask([(wx - 2, 43.0), (wx + 2, 43.0)], 0.45) | c.line_mask([(wx, 41.0), (wx, 45.0)], 0.45), PEARL, 0.4, 1.55)
    frame(c)
    return encode(c.to_tiles())


# ---------------------------------------------------------------------------
# master
# ---------------------------------------------------------------------------

def gingerbread_house():
    """Grimm: Hansel and Gretel come upon the house in the wood, built of gingerbread with icing, candy
    windows and a roof of sweets."""
    c = Canvas(44, 42)
    X, Y = c.X, c.Y
    tx, ty = tiles(c)
    r = random.Random(17)
    # the dark wood: sky through the trees, trunks, leafy masses, grass
    c.paint(ALL(c), LAPIS, np.clip(0.35 + 0.02 * Y, 0, 1))
    for _ in range(40):
        c.paint(c.circle(r.uniform(-2, 46), r.uniform(-2, 24), r.uniform(1.6, 3.2)), FERN, r.uniform(0.6, 0.95), 1.0)
    for x in (1.5, 6.5, 41.5):
        c.paint(rect(c, x - 0.9, 8, x + 0.9, 36), UMBER, 0.9, 1.05)
    bush = np.zeros_like(X, bool)
    for (bx, by, br) in ((-1, 26, 4.5), (4, 23, 4.0), (9, 25, 4.0), (13, 28, 3.5), (2, 31, 4.0), (8, 31, 4.0)):
        bush |= c.circle(bx, by, br)
    c.paint(bush & (Y > 19), FERN, np.clip(0.85 + 0.1 * smooth_noise(c, 8, 1.2), 0, 1), 1.02)
    c.paint(Y > 35.5 + 0.6 * np.sin(X * 0.5), FERN, np.where((tx * 3 + ty * 5) % 7 == 0, 0.15, 0.45))
    # gingerbread walls with a lattice of piped icing and a sweet in every diamond
    walls = rect(c, 12, 21, 40, 37)
    c.paint(walls, UMBER, 0.15)
    c.paint(walls & (((tx + ty) % 5 == 0) | ((tx - ty) % 5 == 0)), PEARL, 0.05, 1.2)
    centre = walls & ((tx + ty) % 5 == 2) & ((tx - ty) % 5 == 2)
    for k, fam in enumerate((EMBER, FERN, SAFFRON, LAPIS)):
        c.paint(centre & ((tx // 5 + ty // 5) % 4 == k), fam, 0.25, 1.25)
    # the roof of sweets: round candies set in gingerbread, iced edges, a striped chimney
    roof = c.poly_mask([(9, 22), (26, 3.5), (43, 22)])
    c.paint(roof, UMBER, 0.35)
    cell_x, cell_y = (tx - 1) // 3, (ty - 1) // 3
    pick = (cell_x * 7 + cell_y * 3 + (cell_x * cell_y) % 4) % 5
    candy = roof & ((tx - 1) % 3 != 2) & ((ty - 1) % 3 != 2)
    for k, fam in enumerate((EMBER, LAPIS, FERN, SAFFRON, PEARL)):
        c.paint(candy & (pick == k), fam, 0.2, 1.2)
    chimney = rect(c, 33, 4, 36, 14)
    c.paint(chimney, EMBER, 0.5, 1.3)
    c.paint(chimney & ((tx + ty) % 2 == 0), PEARL, 0.0, 1.35)
    for side in (-1, 1):
        c.paint(c.line_mask([(26, 3.5), (26 + side * 17.5, 22.3)], 1.6), PEARL, 0.05, 1.5)
        for k in range(1, 9):
            u = k / 9
            c.paint(c.circle(26 + side * 17.5 * u, 3.5 + 18.8 * u + 1.0, 0.6), PEARL, 0.1, 1.5)
    c.paint(rect(c, 10.5, 21.0, 41.5, 22.4), PEARL, 0.1, 1.5)
    # two lollipops planted on the roof
    for (lx, ly, fa, fb) in ((18.0, 12.5, EMBER, PEARL), (26, 9.0, LAPIS, SAFFRON)):
        c.paint(c.line_mask([(lx, ly), (lx, ly + 5)], 0.6), PEARL, 0.2, 1.6)
        swirl(c, lx, ly, 2.4, fa, fb)
    # candy windows and the chocolate door in a candy-cane frame
    for wx in (17.0, 35.0):
        c.paint(rect(c, wx - 3, 24, wx + 3, 31), PEARL, 0.05, 1.3)
        c.paint(rect(c, wx - 2, 25, wx + 2, 30), SAFFRON, 0.2, 1.4)
        c.paint(rect(c, wx - 2, 25, wx + 2, 30) & ((tx == int(wx)) | (ty == 27)), EMBER, 0.5, 1.45)
    door = rect(c, 23, 27, 29, 37) | c.circle(26, 27, 3)
    c.paint(door, EMBER, 0.4, 1.3)
    c.paint(door & ((tx + ty) % 2 == 0), PEARL, 0.0, 1.35)
    inner = rect(c, 24, 28, 28, 37) | c.circle(26, 28, 2)
    c.paint(inner, UMBER, np.where((tx % 2 == 0) ^ (ty % 2 == 0), 0.7, 0.95), 1.4)
    # gumdrops along the foot of the walls, sweets for stepping stones
    for k, gx in enumerate(np.arange(13.5, 40, 2.4)):
        if 22 < gx < 30:
            continue
        c.paint(c.circle(gx, 37.0, 1.1) & (Y < 37.2), (FERN, EMBER, SAFFRON, LAPIS)[k % 4], 0.25, 1.5)
    for k, (px, py) in enumerate(((25.5, 38.6), (22.0, 39.6), (18.0, 40.4))):
        c.paint(ellipse(c, px, py, 1.5, 0.8), (PEARL, SAFFRON, EMBER)[k], 0.1, 1.4)
    # Hansel and Gretel walking up hand in hand (tile sprites)
    kids = {"H": (SAFFRON, 0.35), "B": (SAFFRON, 0.6), "F": (PEARL, 0.05), "h": (PEARL, 0.05), "J": (LAPIS, 0.55),
            "D": (EMBER, 0.55), "A": (PEARL, 0.1), "P": (UMBER, 0.75), "S": (UMBER, 1.0)}
    sprite(c, 1, 28, HANSEL, kids)
    sprite(c, 8, 29, GRETEL, kids)
    frame(c)
    return encode(c.to_tiles())


def princess_pea():
    """Andersen: the princess sits on top of the tall pile of mattresses under a canopy, a ladder against
    the stack and the little pea at the very bottom."""
    c = Canvas(40, 46)
    X, Y = c.X, c.Y
    tx, ty = tiles(c)
    # wallpaper with a sparse gold motif, a checked floor
    c.paint(ALL(c), LAPIS, np.where(tx % 3 == 0, 0.5, 0.3))
    c.paint(((tx % 6 == 1) & (ty % 6 == 2)) | ((tx % 6 == 4) & (ty % 6 == 5)), SAFFRON, 0.3, 1.0)
    floor = Y >= 42
    c.paint(floor, UMBER, 0.2)
    c.paint(floor & ((tx // 2 + ty) % 2 == 0), PEARL, 0.4, 1.05)
    # the bed frame, two posts, a canopy with a fringed valance and curtains tied back
    c.paint(rect(c, 7, 39, 33, 42), UMBER, 0.75, 1.2)
    for px in (7.5, 32.5):
        c.paint(rect(c, px - 0.8, 4, px + 0.8, 44), UMBER, 0.6, 1.3)
    for side in (-1, 1):
        x0 = 20 + side * 20
        curtain = c.poly_mask([(x0, 5), (x0 - side * 7.5, 5), (x0 - side * 2.5, 30), (x0 - side * 3.5, 44), (x0, 44)])
        c.paint(curtain, EMBER, np.where(np.sin(X * 2.0) > 0, 0.55, 0.85), 1.3)
        c.paint(ellipse(c, x0 - side * 3.0, 30.0, 2.2, 0.9), SAFFRON, 0.3, 1.5)
    c.paint(rect(c, 0, 0, 40, 4.0), EMBER, 0.75, 1.3)
    c.paint(rect(c, 0, 4.0, 40, 5.0), SAFFRON, 0.25, 1.4)
    c.paint(rect(c, 0, 5.0, 40, 6.0) & (tx % 3 == 1), SAFFRON, 0.55, 1.4)
    # the pile of mattresses, each a different patterned fabric, rolled ends, slightly askew
    fams = [(EMBER, PEARL), (FERN, SAFFRON), (LAPIS, PEARL), (SAFFRON, EMBER), (PEARL, FERN), (EMBER, SAFFRON),
            (LAPIS, SAFFRON), (FERN, EMBER), (SAFFRON, LAPIS), (PEARL, EMBER), (LAPIS, EMBER), (FERN, PEARL)]
    for i, (fa, fb) in enumerate(fams):
        y1 = 39 - 2 * i
        y0 = y1 - 2
        sx = 1.3 * math.sin(i * 1.9)
        a, b = 10.5 + sx + (i % 3) * 0.4, 29.5 + sx - (i % 2) * 0.6
        body = rect(c, a, y0, b, y1)
        ends = ellipse(c, a, y0 + 1, 1.3, 1.0) | ellipse(c, b, y0 + 1, 1.3, 1.0)
        c.paint(body | ends, fa, 0.35, 1.2)
        c.paint(ends & ~body, fa, 0.8, 1.2)
        kind = i % 5
        if kind == 0:
            pat = tx % 2 == 0                                   # stripes
        elif kind == 1:
            pat = (tx + ty) % 2 == 0                            # checks
        elif kind == 2:
            pat = (tx % 3 == 1) & (ty == y0)                    # dots
        elif kind == 3:
            pat = (tx % 4 == 2) | ((tx % 4 == 0) & (ty == y0))  # flowers
        else:
            pat = (tx // 2) % 2 == 0                            # wide stripes
        c.paint(body & pat & (X > a + 0.5) & (X < b - 0.5), fb, 0.15, 1.25)
    # the pea under the bottom mattress
    c.paint(c.circle(20.5, 39.6, 0.8), FERN, 0.4, 1.9)
    # a ladder leaning on the stack
    for (x0, x1) in ((34.0, 29.5), (36.5, 32.0)):
        c.paint(c.line_mask([(x0, 44), (x1, 14)], 0.6), UMBER, 0.9, 1.6)
    for k in range(1, 14):
        yy = 44 - k * 2.2
        u = (44 - yy) / 30
        c.paint(c.line_mask([(34.0 - 4.5 * u, yy), (36.5 - 4.5 * u, yy)], 0.5), UMBER, 0.9, 1.6)
    # the princess sitting up on top beside her pillow
    c.paint(ellipse(c, 12.5 + 1.3 * math.sin(11 * 1.9), 14.0, 2.6, 1.3), PEARL, 0.05, 1.5)
    sprite(c, 15, 6, PRINCESS, {"Y": (SAFFRON, 0.75), "H": (SAFFRON, 0.3), "F": (PEARL, 0.05), "G": (EMBER, 0.1)})
    frame(c)
    return encode(c.to_tiles())


SCENES = {
    "redridinghood": red_riding_hood,
    "beanstalk": beanstalk,
    "tortoisehare": tortoise_hare,
    "rapunzel": rapunzel,
    "snowqueen": snow_queen,
    "cinderella": cinderella,
    "gingerbread": gingerbread_house,
    "princesspea": princess_pea,
}
