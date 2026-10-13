"""Adventure pack: eight iconic scenes from adventure classics (all public domain), drawn with the
supersampled Canvas of art.py (a tile's colour family comes from the dominant object under it, its tone
from the shading). Every picture is an original composition of the book's scene.

Gentle: Crusoe's footprint, Don Quixote's windmills, Huck Finn's raft, Gulliver in Lilliput.
Challenge: the white whale, Verne's underground sea.
Master (busy, every colour in many islands): the Treasure Island map, the Nautilus.
"""
import math
import random

import numpy as np
from scipy import ndimage

from art import Canvas, LAPIS, SAFFRON, FERN, EMBER, UMBER, PEARL, encode, smoothstep
from art_scenes import ALL, ellipse, rect, tube, frame


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------

def frond(c, bx, by, tx, ty, width, shade=0.5, fam=FERN, prio=1.2, droop=0.25):
    """A palm frond: a drooping tapered blade from (bx, by) to (tx, ty) with a darker midrib."""
    mx, my = (bx + tx) / 2, (by + ty) / 2 - droop * math.hypot(tx - bx, ty - by)
    pts = [((1 - t) ** 2 * bx + 2 * (1 - t) * t * mx + t * t * tx,
            (1 - t) ** 2 * by + 2 * (1 - t) * t * my + t * t * ty) for t in np.linspace(0, 1, 14)]
    c.paint(tube(c, pts, width, 0.5), fam, shade, prio)
    c.paint(c.line_mask(pts[:-3], 0.3), fam, min(1.0, shade + 0.35), prio + 0.05)
    return pts


def puff(c, parts, fam=PEARL, top=0.0, under=0.34, prio=1.1):
    """A crisp two-tone cloud: union of circles, lighter on top, a flat shaded base."""
    m = np.zeros_like(c.X, bool)
    for (a, b, r) in parts:
        m |= c.circle(a, b, r)
    base = max(b for _, b, _ in parts) + 0.5
    m &= c.Y <= base
    c.paint(m, fam, np.where(c.Y > base - 1.2, under, top), prio)
    return m


def rot_pts(pts, x, y, s=1.0, ang=0.0, flip=1):
    """Place local points: scale by s, mirror by flip (-1 faces left), rotate by ang, move to (x, y)."""
    ca, sa = math.cos(ang), math.sin(ang)
    return [(x + (flip * px * ca - py * sa) * s, y + (flip * px * sa + py * ca) * s) for px, py in pts]


def steed(c, x, y, s, fam, shade, gallop=True, flip=1, prio=1.4, donkey=False):
    """A horse (or a donkey) facing right (flip=-1: left), barrel centred at (x, y), ~14*s long."""
    P = lambda pts: rot_pts(pts, x, y, s, 0.0, flip)
    m = ellipse(c, x, y, 3.6 * s, (1.8 if donkey else 1.45) * s)
    m |= c.circle(*P([(-2.6, -0.2)])[0], 1.7 * s) | c.circle(*P([(2.6, 0.0)])[0], 1.5 * s)     # rump, chest
    neck = [(2.0, -1.2), (3.9, 0.4), (5.8, -3.4), (4.6, -4.5)] if not donkey else [(2.0, -1.0), (3.9, 0.6), (5.0, -2.6), (3.8, -3.4)]
    m |= c.poly_mask(P(neck))
    hd = [(4.5, -4.7), (5.7, -4.3), (7.7, -2.6), (7.5, -1.7), (6.6, -1.7), (4.8, -3.2)]
    if donkey:
        hd = [(px - 1.0, py + 1.0) for px, py in hd]
    m |= c.poly_mask(P(hd))
    ear = [(4.7, -4.4), (4.9, -5.8), (5.5, -4.5)] if not donkey else [(3.6, -3.4), (3.4, -6.0), (4.4, -3.6)]
    m |= c.poly_mask(P(ear))
    if gallop:
        legs = [[(2.9, 0.8), (4.6, 2.0), (6.2, 2.0)], [(2.3, 1.0), (3.3, 2.7), (2.6, 4.0)],
                [(-3.0, 0.9), (-4.6, 2.6), (-6.4, 3.2)], [(-2.0, 1.0), (-1.9, 2.8), (-2.7, 4.2)]]
    else:
        legs = [[(2.7, 0.8), (2.9, 4.6)], [(1.6, 0.8), (1.7, 4.6)], [(-2.7, 0.8), (-2.9, 4.6)], [(-1.5, 0.8), (-1.4, 4.6)]]
    for leg in legs:
        m |= tube(c, P(leg), 0.85 * s, 0.7 * s)
    c.paint(m, fam, shade, prio)
    tail = P([(-4.1, -0.9), (-5.6, -0.4), (-6.6, 1.0)] if gallop else [(-4.1, -0.6), (-4.6, 1.0), (-4.5, 3.2)])
    c.paint(tube(c, tail, 1.0 * s, 0.6 * s), UMBER, 0.9, prio + 0.05)
    if not donkey:
        c.paint(tube(c, P([(2.6, -1.6), (4.0, -3.2), (4.8, -4.6)]), 0.7 * s, 0.6 * s), UMBER, 0.9, prio + 0.05)  # mane
    eye = (6.0, -3.6) if not donkey else (5.0, -2.6)
    c.paint(c.circle(*P([eye])[0], 0.35 * s), UMBER, 1.0, prio + 0.2)
    return m


def dotted_trail(c, trail, fam=EMBER, shade=0.67):
    """A dotted path of single tiles (every other tile) along a polyline."""
    pts = []
    for (a0, b0), (a1, b1) in zip(trail[:-1], trail[1:]):
        n = max(1, int(math.hypot(a1 - a0, b1 - b0)))
        pts += [(a0 + (a1 - a0) * i / n, b0 + (b1 - b0) * i / n) for i in range(n)]
    for (px, py) in pts[::2]:
        c.paint(rect(c, math.floor(px), math.floor(py), math.floor(px) + 1, math.floor(py) + 1), fam, shade, 1.5)


def compass_rose(c, cx, cy):
    """A chart's compass rose: four long points split dark/pale, four short red diagonals, a ring."""
    c.paint(c.circle(cx, cy, 3.6) & ~c.circle(cx, cy, 2.8), UMBER, 0.34, 1.4)
    for i in range(8):
        a = i * math.pi / 4 - math.pi / 2
        L = 5.6 if i % 2 == 0 else 3.4
        tip = (cx + math.cos(a) * L, cy + math.sin(a) * L)
        for s in (-1, 1):
            side = (cx + math.cos(a + s * 0.62) * 1.5, cy + math.sin(a + s * 0.62) * 1.5)
            fam, sh = ((UMBER, 1.0) if s > 0 else (PEARL, 0.0)) if i % 2 == 0 else (EMBER, 0.34)
            c.paint(c.poly_mask([(cx, cy), side, tip]), fam, sh, 1.55 if i % 2 == 0 else 1.45)
    c.paint(c.circle(cx, cy, 0.8), SAFFRON, 1.0, 1.6)


def ship_doodle(c, sx, sy):
    """A little two-sailed ship as drawn in a chart's margin."""
    c.paint(c.poly_mask([(sx - 2.6, sy + 1.0), (sx + 2.6, sy + 1.0), (sx + 1.8, sy + 2.4), (sx - 1.8, sy + 2.4)]), UMBER, 1.0, 1.5)
    c.paint(c.poly_mask([(sx - 0.2, sy + 0.8), (sx - 0.2, sy - 3.4), (sx - 2.5, sy + 0.8)]), PEARL, 0.34, 1.5)
    c.paint(c.poly_mask([(sx + 0.5, sy + 0.8), (sx + 0.5, sy - 2.6), (sx + 2.4, sy + 0.8)]), PEARL, 0.34, 1.5)
    c.paint(rect(c, sx - 0.2, sy - 4.6, sx + 1.4, sy - 3.6), EMBER, 0.34, 1.6)


def pixel_fish(c, x, y, fam, sh):
    """A 3 x 1 tile fish swimming left: a two-tile body and a forked tail."""
    c.paint(rect(c, x, y, x + 2, y + 1), fam, sh, 1.6)
    c.paint(rect(c, x + 2, y - 0.4, x + 3, y + 1.4) & ~rect(c, x + 2, y + 0.45, x + 3, y + 0.55), fam, 1.0, 1.55)


def coral(c, x, y, h, ang, depth, w, sh):
    """A branching coral tree (recursive forks)."""
    x1, y1 = x + math.sin(ang) * h, y - math.cos(ang) * h
    c.paint(tube(c, [(x, y), (x1, y1)], w, w * 0.8), EMBER, sh, 1.4)
    if depth:
        for da in (-0.6, 0.55):
            coral(c, x1, y1, h * 0.7, ang + da, depth - 1, w * 0.8, sh)


def diver(c, x, foot, lamp=False):
    """A helmet diver walking on the sea floor: suit, air tank, brass helmet with its glass, rising bubbles."""
    c.paint(tube(c, [(x - 0.7, foot - 3.0), (x - 1.6, foot)], 1.3, 1.2) | tube(c, [(x + 0.7, foot - 3.0), (x + 1.4, foot)], 1.3, 1.2),
            UMBER, 0.67, 1.6)                                                                   # legs
    c.paint(rect(c, x - 1.5, foot - 7.5, x + 1.5, foot - 2.6), UMBER, 0.34, 1.6)               # suit
    c.paint(rect(c, x + 1.5, foot - 7.0, x + 2.6, foot - 3.6), PEARL, 0.67, 1.6)               # air tank
    c.paint(tube(c, [(x - 1.2, foot - 6.6), (x - 3.2, foot - 5.0)], 1.0, 0.9), UMBER, 0.34, 1.6)   # arm
    c.paint(c.circle(x, foot - 9.4, 2.1), SAFFRON, 0.67, 1.7)                                 # brass helmet
    c.paint(c.circle(x - 0.7, foot - 9.4, 1.0), LAPIS, 0.0, 1.8)                              # face glass
    if lamp:
        c.paint(c.circle(x - 3.6, foot - 4.8, 0.9), SAFFRON, 0.0, 1.7)
    for i in range(3):
        c.paint(c.circle(x + 0.5 + 0.7 * i, foot - 13.0 - 2.0 * i, 0.55), PEARL, 0.0, 1.5)


def jellyfish(c, x, y):
    """A pale jellyfish bell with a red rim and three trailing tentacles."""
    bell = ellipse(c, x, y, 2.6, 2.0) & (c.Y < y + 0.5)
    c.paint(bell, PEARL, 0.0, 1.5)
    c.paint(bell & (c.Y > y - 0.5), EMBER, 0.34, 1.5)
    for k in (-2, 0, 2):
        c.paint(rect(c, x + k - 0.5, y + 0.5, x + k + 0.5, y + 4.5 - abs(k) * 0.5), EMBER, 0.0, 1.45)


# ---------------------------------------------------------------------------
# Gentle
# ---------------------------------------------------------------------------

def footprint():
    """Robinson Crusoe: the single bare footprint on the beach, seen from above, with Crusoe in
    goatskins under his parasol staring at it; the surf runs diagonally across the top-right corner."""
    c = Canvas(44, 42)
    X, Y = c.X, c.Y
    # sand with soft ripple bands, then the wet sand and the sea across the top-right corner
    s = (44 - X) * 0.62 + Y - 19 + 1.1 * np.sin(X * 0.33 + 0.8)
    c.paint(ALL(c), SAFFRON, 0.34)
    c.paint(np.sin(Y * 0.8 + 2.0 * np.sin(X * 0.21)) > 0.85, SAFFRON, 0.0)
    c.paint(s < 3.2, SAFFRON, 0.67)
    c.paint(s < 0, LAPIS, np.where(s > -4.5, 0.34, np.where(s > -10.0, 0.67, 1.0)))
    # foam: the surf edge and two lines of breaking waves
    c.paint((s < 0) & (s > -1.2), PEARL, 0.0, 1.2)
    for off, ph in ((-5.5, 0.0), (-11.0, 2.0)):
        crest = (np.abs(s - off) < 0.6) & (np.sin(X * 0.4 + ph) > -0.35)
        c.paint(crest, PEARL, 0.2, 1.2)
    # two palms: one leaning in from the top-left corner, a smaller one near the surf
    for (pts, w, crown, fronds) in (
            ([(-2, 30), (0.5, 14), (4.5, 4.0)], 2.2, (4.5, 4.0), ((8.5, 1.5), (6.5, 6.5), (0.5, 7.5), (-4.0, 5.0), (8.0, -3.0))),
            ([(21.0, 14.0), (20.2, 8.5), (18.0, 3.5)], 1.4, (18.0, 3.5), ((-6.0, 2.5), (-3.5, 6.0), (3.5, 5.5), (6.0, 0.5), (-5.0, -2.5)))):
        c.paint(tube(c, pts, w, w * 0.6), UMBER, np.where(np.sin(Y * 2.2) > 0.2, 0.34, 0.67), 1.2)
        for k, (dx, dy) in enumerate(fronds):
            frond(c, crown[0], crown[1], crown[0] + dx, crown[1] + dy, 2.9 if w > 2 else 2.4, 0.4 if k % 2 else 0.67, droop=0.18)
        c.paint(c.circle(crown[0], crown[1], w * 0.5), UMBER, 0.8, 1.3)

    # the footprint (a right foot, toes up): a rim of pushed-up sand, then the hollow, its upper-left wall shaded
    sole = [(21.0, 23.5), (23.0, 21.6), (27.0, 21.3), (30.5, 22.4), (32.6, 24.4), (33.0, 27.5), (32.0, 31.0),
            (31.2, 34.0), (31.0, 37.0), (24.8, 37.0), (25.6, 33.5), (25.4, 31.0), (23.4, 28.5), (21.2, 26.5)]
    hollow = c.poly_mask(sole) | ellipse(c, 27.9, 37.0, 3.2, 3.5)
    for (x, y, rx, ry) in ((22.4, 17.8, 1.8, 2.3), (26.0, 18.3, 1.15, 1.45), (28.8, 19.4, 1.0, 1.25),
                           (31.1, 21.0, 0.9, 1.1), (33.1, 23.1, 0.8, 1.0)):              # five toes
        hollow |= ellipse(c, x, y, rx, ry, 0.3)
    c.paint(ndimage.binary_dilation(hollow, iterations=5), SAFFRON, 0.0, 1.3)
    c.paint(hollow, UMBER, 0.0, 1.5)
    c.paint(hollow & ~np.roll(np.roll(hollow, 7, axis=0), 7, axis=1), UMBER, 0.45, 1.5)
    # Crusoe: goatskin leggings and shaggy coat, bearded face, tall fur cap, a hide parasol
    cx = 11.0
    for lx in (cx - 1.5, cx + 1.4):
        c.paint(tube(c, [(lx, 31.0), (lx + 0.2, 38.0)], 2.1, 1.8), UMBER, 0.34, 1.4)
        c.paint(ellipse(c, lx + 0.8, 38.8, 1.6, 0.8), UMBER, 1.0, 1.5)
    coat = c.poly_mask([(cx - 2.8, 22.0), (cx + 2.8, 22.0), (cx + 4.4, 32.5), (cx - 4.4, 32.5)])
    hem = (Y > 31.0) & (np.abs(((X - cx) % 1.6) - 0.8) * 2 > (Y - 31.0) * 1.2)
    c.paint(coat & ~hem, UMBER, 0.0, 1.3)
    c.paint(coat & (np.abs(Y - 27.0) < 0.5), UMBER, 0.67, 1.35)                    # belt
    c.paint(tube(c, [(cx + 2.4, 23.0), (cx + 5.0, 25.6), (cx + 6.6, 23.4)], 1.6, 1.4), UMBER, 0.0, 1.4)  # arm up
    c.paint(c.circle(cx + 6.9, 22.9, 0.9), EMBER, 0.0, 1.6)
    face = ellipse(c, cx + 0.5, 19.3, 2.0, 2.2) | ellipse(c, cx + 2.5, 19.6, 0.7, 0.6)
    c.paint(face, EMBER, 0.0, 1.5)
    c.paint(ellipse(c, cx + 0.2, 21.4, 2.0, 1.4) & (X < cx + 2.3), UMBER, 1.0, 1.55)  # beard
    c.paint(c.circle(cx + 1.3, 18.8, 0.4), UMBER, 1.0, 1.7)                        # eye
    cap = c.poly_mask([(cx - 2.2, 18.2), (cx + 2.5, 18.2), (cx + 0.9, 14.2), (cx - 1.1, 13.6)])
    c.paint(cap, UMBER, 0.67, 1.5)
    c.paint(tube(c, [(cx - 2.2, 25.5), (cx - 2.4, 11.0)], 0.6, 0.6), UMBER, 1.0, 1.5)
    canopy = ellipse(c, cx - 2.4, 11.8, 6.2, 3.6) & (Y < 11.8 + 0.6)
    spokes = np.sin(np.arctan2(Y - 12.2, X - cx + 2.4) * 8) > 0.3
    c.paint(canopy, EMBER, np.where(spokes, 0.67, 1.0), 1.4)
    fringe = ellipse(c, cx - 2.4, 11.8, 6.4, 1.4) & (Y > 11.8) & ((np.floor(X) % 2) == 0)
    c.paint(fringe, EMBER, 1.0, 1.4)
    # two shells on the sand
    for (sx, sy) in ((38.5, 36.0), (18.5, 33.5)):
        c.paint(ellipse(c, sx, sy, 1.2, 0.9), PEARL, 0.2, 1.5)
    frame(c)
    return encode(c.to_tiles())


def windmills():
    """Don Quixote tilting at windmills: white windmills on the plain of La Mancha, the thin knight on
    Rocinante charging with his lance at the great sails, Sancho on his donkey hanging back."""
    c = Canvas(48, 36)
    X, Y = c.X, c.Y
    c.paint(ALL(c), LAPIS, np.clip(np.floor((23 - Y) / 7.0) / 3.0, 0, 0.67))   # banded sky
    puff(c, [(6, 6.5, 2.0), (9.5, 5.2, 2.8), (13, 6.5, 1.9)])
    # the plain rising to a ridge with a hill on the right, and a dusty track
    ground = 24.0 - 3.5 * smoothstep(17, 27, X) - 1.5 * np.exp(-((X - 41) / 6.0) ** 2) + 0.3 * np.sin(X * 0.8)
    c.paint(Y > ground, SAFFRON, np.where(Y > ground + 3.0, 0.34, 0.0))
    c.paint((np.abs(Y - (33.2 - 0.05 * X)) < 1.0) & (Y > ground), SAFFRON, 0.67, 1.1)

    def windmill(x, base, h, wb, R, ang, sail_w):
        tower = c.poly_mask([(x - wb / 2, base), (x + wb / 2, base), (x + wb * 0.37, base - h), (x - wb * 0.37, base - h)])
        c.paint(tower, PEARL, np.where(X < x + wb * 0.15, 0.0, 0.5), 1.2)
        c.paint(rect(c, x - wb * 0.13, base - h * 0.28, x + wb * 0.13, base) | c.circle(x, base - h * 0.28, wb * 0.13),
                UMBER, 0.9, 1.5)                                                               # door
        c.paint(c.poly_mask([(x - wb * 0.45, base - h + 0.3), (x + wb * 0.45, base - h + 0.3), (x, base - h - wb * 0.42)]),
                UMBER, 0.67, 1.4)                                                              # conical cap
        hx, hy = x, base - h + 0.4
        for k in range(4):
            a = ang + k * math.pi / 2
            ux, uy, nx, ny = math.cos(a), math.sin(a), -math.sin(a), math.cos(a)
            tip = (hx + ux * R, hy + uy * R)
            if sail_w > 0:   # a canvas sail beside the spar, framed in dark wood
                p0 = (hx + ux * R * 0.22, hy + uy * R * 0.22)
                quad = [p0, tip, (tip[0] + nx * sail_w, tip[1] + ny * sail_w), (p0[0] + nx * sail_w, p0[1] + ny * sail_w)]
                c.paint(c.poly_mask(quad), PEARL, 0.0, 1.3)
                c.paint(c.line_mask(quad + [p0], 0.4), UMBER, 0.67, 1.4)
            c.paint(c.line_mask([(hx, hy), tip], max(0.45, R * 0.045)), UMBER, 0.9, 1.45)
        c.paint(c.circle(hx, hy, max(0.55, R * 0.06)), UMBER, 1.0, 1.5)
    windmill(11.0, 24.2, 3.6, 2.4, 3.2, -0.3, 1.4)
    windmill(25.5, 21.0, 5.2, 3.2, 4.2, -0.65, 1.6)
    windmill(41.0, 28.0, 13.5, 8.0, 11.5, -math.pi / 4, 2.7)
    # Sancho Panza on his donkey, hanging back at the left
    steed(c, 4.6, 27.6, 0.6, PEARL, 0.67, gallop=False, donkey=True)
    c.paint(ellipse(c, 4.5, 25.1, 1.4, 1.5), EMBER, 0.34, 1.6)                        # round body
    c.paint(c.circle(4.7, 22.9, 0.85), EMBER, 0.0, 1.65)
    c.paint(ellipse(c, 4.7, 22.2, 1.5, 0.5), SAFFRON, 0.67, 1.7)                       # hat
    # Don Quixote on Rocinante, galloping right with his long lance aimed at the great sail
    steed(c, 16.0, 28.0, 1.15, UMBER, 0.0, gallop=True)
    c.paint(tube(c, [(16.2, 26.6), (17.6, 29.0), (16.8, 31.0)], 1.0, 0.9), LAPIS, 1.0, 1.6)   # leg
    c.paint(tube(c, [(16.0, 26.2), (17.8, 19.8)], 1.7, 1.4), LAPIS, 1.0, 1.6)                 # armoured body
    c.paint(c.circle(18.3, 18.3, 1.1), EMBER, 0.0, 1.7)                                     # face
    c.paint(ellipse(c, 17.9, 17.1, 1.7, 0.8, -0.3), SAFFRON, 0.34, 1.75)                     # basin helmet
    c.paint(c.circle(15.3, 22.6, 1.8), EMBER, 0.67, 1.65)                                   # round shield
    c.paint(c.line_mask([(15.0, 24.2), (32.6, 22.4)], 0.5), UMBER, 1.0, 1.8)                 # lance
    frame(c)
    return encode(c.to_tiles())


def raft():
    """Huckleberry Finn: the log raft drifting down the wide moonlit Mississippi at night, with its little
    wigwam and a lantern, Huck and Jim aboard as dark shapes against the moon's path, and a steamboat's
    lights far off along the bank."""
    c = Canvas(48, 36)
    X, Y = c.X, c.Y
    # night sky, moon and a few stars
    c.paint(ALL(c), LAPIS, 1.0)
    c.paint(c.circle(13.0, 5.0, 3.2), PEARL, np.where(np.hypot(X - 11.8, Y - 4.2) > 2.8, 0.34, 0.0), 1.3)
    for (sx, sy) in ((4, 2), (24, 2), (30, 6), (37, 2), (44, 6), (6, 9), (21, 8)):
        c.paint(c.circle(sx + 0.5, sy + 0.5, 0.45), PEARL, 0.0, 1.5)
    # the far bank: a dark line of cottonwoods
    bank = 12.0 + 1.4 * np.sin(X * 0.55) + 0.8 * np.sin(X * 1.7 + 1) + 0.5 * np.sin(X * 0.21)
    c.paint(Y > bank, FERN, 1.0)
    c.paint(Y > 14.4, UMBER, 1.0)
    # the river and the moon's broken path on it
    water = Y > 15.0
    c.paint(water, LAPIS, 1.0)
    half = 2.4 + 0.45 * (Y - 15)
    path = water & ((np.floor(Y - 15) % 3) != 2) & (np.abs(X - 13.0) < half * (0.6 + 0.4 * np.sin(Y * 1.3) ** 2))
    c.paint(path, PEARL, np.where(Y < 23, 0.0, 0.34), 1.1)
    # the steamboat far off: white decks with rows of lit windows, two stacks with sparks
    c.paint(rect(c, 34.0, 12.8, 44.0, 14.6) | c.poly_mask([(33.0, 14.6), (45.0, 14.6), (43.8, 15.8), (34.0, 15.8)]), PEARL, 0.67, 1.4)
    c.paint(rect(c, 36.0, 11.2, 41.5, 12.8), PEARL, 0.34, 1.4)
    c.paint((rect(c, 34.5, 13.2, 43.5, 14.2) | rect(c, 36.5, 11.6, 41.0, 12.4)) & (np.floor(X) % 2 == 0), SAFFRON, 0.0, 1.5)
    for sx in (37.2, 40.0):
        c.paint(rect(c, sx - 0.45, 7.2, sx + 0.45, 11.2), UMBER, 1.0, 1.5)
    for (px, py) in ((37.6, 5.9), (40.6, 5.1), (39.0, 3.8)):
        c.paint(c.circle(px, py, 0.5), EMBER, 0.0, 1.6)
    c.paint(water & (np.abs(X - 39) < 4.5) & (Y < 19.0) & (np.sin(Y * 4.0) > 0.5) & (np.floor(X) % 2 == 1), SAFFRON, 0.34, 1.2)
    # the raft: a skewed deck of big logs, its near edge darker
    deck = c.poly_mask([(4.0, 28.0), (33.0, 27.0), (37.0, 31.0), (6.5, 32.5)])
    c.paint(deck, UMBER, np.where(np.floor(Y) % 2 == 0, 0.34, 0.0), 1.2)       # one log per tile row
    c.paint(c.poly_mask([(6.5, 32.5), (37.0, 31.0), (37.0, 32.5), (6.5, 34.0)]), UMBER, 0.67, 1.2)
    # the wigwam: a little A-frame shanty with a glowing doorway, and the lantern on its pole
    c.paint(c.poly_mask([(23.0, 29.4), (34.0, 28.8), (31.5, 20.5), (26.5, 20.7)]), UMBER, 0.67, 1.35)
    c.paint(c.poly_mask([(27.0, 29.2), (30.6, 29.0), (28.9, 24.2)]), SAFFRON, 0.0, 1.5)
    c.paint(rect(c, 21.0, 20.5, 21.6, 28.6), UMBER, 1.0, 1.5)
    c.paint(c.circle(21.3, 19.8, 1.15), SAFFRON, 0.0, 1.7)
    c.paint(water & (np.abs(X - 21.6) < 0.9) & (Y > 33.6) & (np.sin(Y * 3.0) > -0.2), SAFFRON, 0.34, 1.3)
    # Jim standing at the long steering sweep, Huck sitting at the edge with his feet over the water
    c.paint(c.line_mask([(9.0, 23.5), (6.4, 29.0), (2.0, 35.0)], 0.6), UMBER, 1.0, 1.5)
    c.paint(c.poly_mask([(10.4, 29.6), (13.4, 29.6), (13.6, 22.4), (12.6, 21.0), (11.2, 21.0), (10.2, 22.4)]), UMBER, 1.0, 1.6)
    c.paint(c.circle(11.9, 19.6, 1.2), UMBER, 1.0, 1.7)
    c.paint(tube(c, [(11.0, 22.4), (8.4, 24.0)], 1.0, 0.9), UMBER, 1.0, 1.6)
    c.paint(c.poly_mask([(15.8, 31.4), (18.2, 31.4), (17.9, 27.2), (16.2, 27.2)]), UMBER, 1.0, 1.6)
    c.paint(tube(c, [(17.8, 31.4), (18.8, 32.2), (19.0, 35.0)], 0.9, 0.8), UMBER, 1.0, 1.6)
    c.paint(c.circle(17.0, 26.0, 1.05), UMBER, 1.0, 1.7)
    c.paint(ellipse(c, 17.0, 25.1, 2.0, 0.6), SAFFRON, 0.67, 1.75)                      # straw hat
    frame(c)
    return encode(c.to_tiles())


def lilliput():
    """Gulliver's Travels: Gulliver lying on his back in the grass, seen from above, tied down by rows of
    thin ropes pegged into the ground, with tiny Lilliputians on his chest, a ladder and a little cart."""
    c = Canvas(48, 38)
    X, Y = c.X, c.Y
    c.paint(ALL(c), FERN, 0.34)
    c.paint(np.abs(np.sin(X * 1.1) * np.sin(Y * 0.9 + X * 0.2)) > 0.93, FERN, 0.67)
    cy = 19.5
    # arms along his sides (blue sleeves, white cuffs, hands)
    for s in (-1, 1):
        c.paint(tube(c, [(16.0, cy + s * 6.2), (23.0, cy + s * 8.4), (29.0, cy + s * 8.6)], 3.6, 3.0), LAPIS, 0.67, 1.2)
        c.paint(ellipse(c, 30.0, cy + s * 8.6, 1.1, 1.7), PEARL, 0.0, 1.3)
        c.paint(ellipse(c, 32.2, cy + s * 8.4, 1.6, 1.4), EMBER, 0.0, 1.3)
    # legs: buff breeches, white stockings, black shoes with gold buckles
    for s in (-1, 1):
        c.paint(tube(c, [(29.0, cy + s * 2.6), (36.0, cy + s * 2.9)], 4.8, 4.0), SAFFRON, 0.67, 1.2)
        c.paint(tube(c, [(36.0, cy + s * 2.9), (42.0, cy + s * 3.1)], 3.4, 2.8), PEARL, 0.34, 1.2)
        c.paint(ellipse(c, 43.8, cy + s * 3.2, 2.0, 1.7), UMBER, 1.0, 1.3)
        c.paint(c.circle(43.5, cy + s * 3.2, 0.6), SAFFRON, 0.0, 1.5)
    # the long blue coat with gold buttons, a white cravat
    coat = c.poly_mask([(14.0, cy - 6.8), (27.0, cy - 5.8), (32.0, cy - 6.2), (32.0, cy + 6.2), (27.0, cy + 5.8), (14.0, cy + 6.8)])
    c.paint(coat, LAPIS, np.where(np.abs(Y - cy) < 3.5, 0.34, 0.67), 1.2)
    for bx in (18.5, 22.5, 26.5):
        c.paint(rect(c, bx - 0.5, cy - 2.0, bx + 0.5, cy - 1.0) | rect(c, bx - 0.5, cy + 1.0, bx + 0.5, cy + 2.0), SAFFRON, 0.0, 1.5)
    c.paint(ellipse(c, 14.2, cy, 1.8, 2.6), PEARL, 0.0, 1.3)
    # the head, top towards the left: hair spread on the grass, a face looking straight up
    c.paint(ellipse(c, 7.5, cy, 6.0, 6.0), UMBER, 0.34, 1.2)
    c.paint(ellipse(c, 9.6, cy, 4.2, 4.2), EMBER, 0.0, 1.3)
    for s in (-1, 1):
        c.paint(rect(c, 8.0, cy + s * 2.0 - 0.5, 9.0, cy + s * 2.0 + 0.5), UMBER, 1.0, 1.6)        # eyes
    c.paint(rect(c, 10.0, cy - 0.5, 11.0, cy + 0.5), EMBER, 0.34, 1.6)                           # nose
    c.paint(rect(c, 12.0, cy - 1.5, 13.0, cy + 1.5), EMBER, 1.0, 1.6)                            # mouth
    # rows of hemp ropes across him, each pegged into the grass on both sides
    for (x, half) in ((4.0, 6.5), (16.5, 10.5), (25.5, 11.0), (35.0, 6.5), (41.0, 6.5)):
        y0, y1 = cy - half - 1.2, cy + half + 1.2
        c.paint(c.line_mask([(x, y0), (x + 0.6, y1)], 0.6), SAFFRON, 0.0, 1.45)
        for (px, py) in ((x, y0), (x + 0.6, y1)):
            c.paint(c.circle(math.floor(px) + 0.5, math.floor(py) + 0.5, 0.6), UMBER, 0.67, 1.5)
    # tiny Lilliputians on his chest and around him, one climbing a ladder, and a little cart
    def tiny(x, y, fam):
        """A 3 x 4 tile stick person: head, arms and body, two legs."""
        x, y = math.floor(x), math.floor(y)
        c.paint(rect(c, x, y, x + 1, y + 1), EMBER, 0.0, 1.85)
        c.paint(rect(c, x - 1, y + 1, x + 2, y + 2) | rect(c, x, y + 2, x + 1, y + 3), fam, 0.67, 1.8)
        c.paint(rect(c, x - 1, y + 3, x, y + 4) | rect(c, x + 1, y + 3, x + 2, y + 4), UMBER, 0.67, 1.8)
    lad = rect(c, 21.0, 28.0, 22.0, 35.0) | rect(c, 24.0, 28.0, 25.0, 35.0)
    for k in (29, 31, 33):
        lad |= rect(c, 21.0, k, 25.0, k + 1)
    c.paint(lad, UMBER, 0.0, 1.7)
    for (x, y) in ((20, 16), (22, 20), (29, 18), (22, 28), (6, 32), (10, 3)):
        tiny(x, y, EMBER if y < 25 else (LAPIS if x < 20 else PEARL))
    c.paint(rect(c, 38.0, 32.0, 43.0, 34.5), UMBER, 0.34, 1.5)
    for wx in (39.0, 42.0):
        c.paint(c.circle(wx, 34.8, 0.8), UMBER, 1.0, 1.6)
    frame(c)
    return encode(c.to_tiles())


# ---------------------------------------------------------------------------
# Challenge
# ---------------------------------------------------------------------------

def whitewhale():
    """Moby-Dick: the great white whale breaching beside a whaleboat full of oarsmen, the Pequod small
    on the horizon, spray flying (no harpoons, no harm)."""
    c = Canvas(44, 42)
    X, Y = c.X, c.Y
    horizon = 16.0
    # stormy sky and grey clouds, the dark sea with broken rows of white crests
    c.paint(ALL(c), LAPIS, np.where(Y < 8, 0.67, 0.34))
    puff(c, [(22, 4.5, 2.0), (25.5, 3.4, 2.7), (29, 4.6, 1.9)], PEARL, 0.67, 1.0)
    puff(c, [(35, 4.0, 1.5), (37.8, 3.0, 2.1), (40.5, 4.1, 1.5)], PEARL, 0.67, 1.0)
    sea = Y >= horizon
    c.paint(sea, LAPIS, np.where(Y < 25, 0.67, 1.0))
    row = np.floor(Y - horizon)
    crests = sea & (row % 4 == 1) & (np.sin(X * 0.55 + row * 2.3) > 0.45)
    c.paint(crests, PEARL, np.where(Y < 26, 0.34, 0.0), 1.15)
    # the Pequod far off on the horizon
    c.paint(c.poly_mask([(32.0, 15.0), (40.0, 15.0), (39.0, 16.5), (33.0, 16.5)]), UMBER, 1.0, 1.5)
    for (mx, top) in ((34.0, 10.0), (36.5, 9.0), (39.0, 10.5)):
        c.paint(rect(c, mx - 0.5, top, mx + 0.5, 15.0), UMBER, 1.0, 1.5)
        c.paint(rect(c, mx - 1.0, top + 1.0, mx + 1.0, top + 2.0) | rect(c, mx - 1.0, top + 2.6, mx + 1.0, top + 4.0), PEARL, 0.0, 1.55)
    # the whale: a huge blunt square head bursting up out of the sea, slanting up to the left
    hx, hy = 12.0, 4.0
    dx, dy = 0.5, 0.866
    nx, ny = -dy, dx
    u = (X - hx) * dx + (Y - hy) * dy
    v = (X - hx) * nx + (Y - hy) * ny
    half = np.where(u < 15, 6.0, 6.0 - 0.12 * (u - 15))
    front = np.clip(1.2 - u, 0, None) / 1.2
    body = (u > 0) & ((np.abs(v) / half) ** 8 + front ** 2 < 1.0)
    waterline = 28.5 + 0.6 * np.sin(X * 0.9)
    whale = body & (Y < waterline)
    c.paint(whale, PEARL, np.where(v > 1.5, 0.0, np.where(v > -3.0, 0.34, 0.67)), 1.3)
    c.paint(whale & (u > 16) & (np.abs((u % 3.2) - 1.6) < 0.4) & (v < 3.5), PEARL, 0.67, 1.35)       # skin folds
    c.paint(whale & (np.abs(v + 1.0 + 0.4 * np.sin(u * 0.9)) < 0.45) & (u > 3) & (u < 12), PEARL, 0.67, 1.35)  # scar
    # the long narrow lower jaw, hanging open, with its row of teeth
    ju0, jv0, ja = 15.5, 5.6, 0.22
    jdx, jdy = dx * math.cos(ja) - nx * math.sin(ja), dy * math.cos(ja) - ny * math.sin(ja)
    jnx, jny = -jdy, jdx
    jx0, jy0 = hx + dx * ju0 + nx * jv0, hy + dy * ju0 + ny * jv0
    ju = -((X - jx0) * jdx + (Y - jy0) * jdy)
    jv = (X - jx0) * jnx + (Y - jy0) * jny
    gap = body & (v > 3.6) & (u > 3.0) & (u < ju0 + 0.5) & ~((ju > 0) & (jv > 0.9))
    c.paint(gap & (Y < waterline), UMBER, 1.0, 1.5)
    jaw = (ju > 0) & (ju < 13.5) & (jv > 0.9) & (jv < 2.6) & (Y < waterline)
    c.paint(jaw, PEARL, 0.0, 1.45)
    for k in range(5):
        tx_, ty_ = jx0 - jdx * (2.5 + 2.2 * k) + jnx * 0.4, jy0 - jdy * (2.5 + 2.2 * k) + jny * 0.4
        c.paint(c.circle(tx_, ty_, 0.55), PEARL, 0.0, 1.7)
    ex, ey = hx + dx * 16.5 + nx * 3.2, hy + dy * 16.5 + ny * 3.2
    c.paint(c.circle(ex, ey, 0.75), UMBER, 1.0, 1.8)
    fx, fy = hx + dx * 21.0 + nx * 6.0, hy + dy * 21.0 + ny * 6.0
    c.paint(ellipse(c, fx - 1.4, fy + 0.8, 2.8, 1.2, -0.6) & (Y < waterline), PEARL, 0.34, 1.4)        # flipper
    # spray: a collar of white water where the whale bursts out, and flying drops
    collar = (np.abs(Y - waterline + 0.3) < 1.5 + 0.9 * np.sin(X * 1.7)) & (X > 9) & (X < 34)
    c.paint(collar, PEARL, 0.0, 1.45)
    r = random.Random(17)
    for _ in range(12):
        a = r.uniform(-3.0, -0.2)
        d = r.uniform(7, 13)
        c.paint(c.circle(22 + math.cos(a) * d * 1.3, 27.5 + math.sin(a) * d * 0.7, r.uniform(0.6, 0.95)), PEARL, 0.0, 1.5)
    # the whaleboat with five oarsmen and a man standing in the bow
    boat = c.poly_mask([(1.5, 34.0), (26.0, 34.0), (23.0, 37.5), (4.5, 37.5)])
    c.paint(boat, UMBER, 0.34, 1.5)
    c.paint(rect(c, 2.0, 34.0, 25.0, 35.0), UMBER, 1.0, 1.55)
    for k, ox in enumerate((5.0, 8.5, 12.0, 15.5, 19.0)):
        c.paint(c.line_mask([(ox + 1.0, 33.0), (ox - 2.2, 38.8)], 0.95), SAFFRON, 0.67, 1.55)
        c.paint(rect(c, ox - 0.5, 31.0, ox + 1.0, 34.0), (EMBER, LAPIS, EMBER)[k % 3], 0.34 if k % 3 != 1 else 0.0, 1.6)
        c.paint(c.circle(ox + 0.25, 30.2, 0.75), EMBER, 0.0, 1.65)
    c.paint(rect(c, 22.0, 29.0, 23.5, 34.0), EMBER, 0.67, 1.6)
    c.paint(c.circle(22.75, 28.1, 0.8), EMBER, 0.0, 1.65)
    c.paint(c.line_mask([(23.2, 30.0), (25.6, 28.0)], 0.55), EMBER, 0.67, 1.6)                       # pointing arm
    frame(c)
    return encode(c.to_tiles())


def undergroundsea():
    """Journey to the Centre of the Earth: the vast cavern of the underground sea, glowing with its strange
    light, stalactites hanging from the rock vault, a forest of giant pale mushrooms on the shore with
    giant ferns, and the explorers' little raft under sail."""
    c = Canvas(48, 36)
    X, Y = c.X, c.Y
    r = random.Random(29)
    c.paint(ALL(c), UMBER, 1.0)
    # the glowing vault: a great arch of light over the sea, brightest towards the horizon
    opening = ((X - 30) / 18.5) ** 2 + ((Y - 21) / 19.0) ** 2 < 1.0
    c.paint(opening, LAPIS, np.where(Y < 8, 0.34, 0.0))
    c.paint(opening & (Y > 13), PEARL, 0.0, 1.05)
    puff(c, [(22, 10.5, 1.6), (25, 9.6, 2.2), (28, 10.6, 1.5)], PEARL, 0.0, 0.34, 1.05)
    puff(c, [(35, 7.0, 1.3), (37.5, 6.2, 1.8), (40, 7.0, 1.2)], PEARL, 0.0, 0.34, 1.05)
    # far cliffs across the sea
    cliffs = (Y > 14.5 + 2.2 * np.abs(np.sin(X * 0.3 + 0.5)) + 0.6 * np.sin(X * 1.3)) & (Y < 18.5)
    c.paint(cliffs & opening, LAPIS, 0.67, 1.1)
    # the sea: banded, with rows of glinting ripples
    sea = (Y >= 18.0) & (X > 8)
    c.paint(sea, LAPIS, np.where(Y < 23, 0.34, 0.67))
    c.paint(sea & (np.floor(Y) % 3 == 1) & (np.sin(X * 0.7 + Y * 1.9) > 0.55), PEARL, 0.0, 1.1)
    # stalactites hanging from the rim of the vault
    for k in range(19):
        sx = 12.8 + k * 1.95 + r.uniform(-0.4, 0.4)
        dxn = (sx - 30) / 18.5
        if abs(dxn) >= 0.97:
            continue
        top = 21 - 19.0 * math.sqrt(1 - dxn * dxn) - 1.0
        ln = r.uniform(3.0, 5.0) + (3.5 if k % 3 == 1 else 0.0)
        w = r.uniform(1.0, 1.4)
        c.paint(c.poly_mask([(sx - w, top), (sx + w, top), (sx + 0.1, top + ln)]), UMBER, 0.67 if k % 2 else 1.0, 1.3)
    # the left shore and the forest of giant mushrooms against the dark rock wall
    shore = (Y > 26.5 + 0.5 * np.sin(X * 0.9)) & (X < 21 - 0.6 * (36 - Y))
    c.paint(shore | (X < 9) & (Y > 26), UMBER, 0.67, 1.1)
    for (mx, my, rx, ry, foot) in ((5.5, 6.0, 5.6, 3.4, 31.5), (12.5, 12.5, 4.4, 2.6, 30.0), (3.0, 17.5, 3.0, 2.0, 33.0),
                                   (17.0, 20.0, 3.0, 1.8, 29.0)):
        sw = max(1.4, rx * 0.36)
        c.paint(rect(c, mx - sw / 2, my, mx + sw / 2, foot) | ellipse(c, mx, foot, sw * 0.9, 0.8), PEARL,
                np.where(X < math.floor(mx) + 0.5, 0.34, 0.67), 1.3)
        c.paint(ellipse(c, mx, my, rx, ry) & (Y < my + 0.3), PEARL, np.where(Y < my - ry * 0.45, 0.0, 0.34), 1.35)
        c.paint(ellipse(c, mx, my + 0.3, rx * 0.92, 1.0) & (Y > my + 0.3), SAFFRON, 0.67, 1.4)
    # giant ferns on the shore in front of the mushrooms
    for (fx, fy, tips) in ((7.5, 35.5, ((1.5, 28.5), (5.5, 26.5), (10.5, 27.0), (14.0, 30.5))),
                           (19.5, 35.5, ((15.5, 31.0), (19.5, 29.0), (24.0, 31.5)))):
        for k, (tx, ty) in enumerate(tips):
            c.paint(tube(c, [(fx, fy), ((fx + tx) / 2, ty - 1.2), (tx, ty)], 1.8, 0.7), FERN, 0.34 if k % 2 else 0.67, 1.35)
    # stalagmites on the right shore
    for (gx, gb, gh, gw) in ((45.0, 36.0, 10.0, 2.4), (41.5, 36.0, 6.0, 1.7)):
        c.paint(c.poly_mask([(gx - gw, gb), (gx + gw, gb), (gx, gb - gh)]), UMBER, 0.67, 1.3)
    # the explorers' raft under a square sail
    c.paint(c.poly_mask([(24.0, 27.5), (37.5, 27.5), (36.5, 29.5), (25.0, 29.5)]), UMBER, 0.34, 1.5)
    c.paint(rect(c, 30.0, 17.5, 31.0, 27.6), UMBER, 1.0, 1.55)
    c.paint(c.poly_mask([(26.5, 19.0), (34.5, 18.5), (34.0, 25.5), (27.0, 25.8)]), EMBER, 0.34, 1.5)
    c.paint(c.poly_mask([(26.5, 19.0), (34.5, 18.5), (34.5, 19.6), (26.5, 20.1)]), UMBER, 0.67, 1.55)
    for (px, fam) in ((26.0, LAPIS), (33.0, SAFFRON), (35.5, PEARL)):
        c.paint(rect(c, px - 0.5, 25.5, px + 0.7, 27.6), fam, 0.67, 1.6)
        c.paint(c.circle(px + 0.1, 24.8, 0.65), EMBER, 0.0, 1.65)
    frame(c)
    return encode(c.to_tiles())


# ---------------------------------------------------------------------------
# Master
# ---------------------------------------------------------------------------

def treasuremap():
    """Treasure Island: Flint's old chart of the island lying on a table - an island of bays and wooded hills
    with dotted trails to the red X, blue shallows and wave marks on the parchment sea, a compass rose,
    little ships and a sea serpent in the margins, a chequered border, and the parrot perched on the
    corner. No writing, only marks."""
    c = Canvas(44, 42)
    X, Y = c.X, c.Y
    tx = np.floor(X).astype(int)
    ty = np.floor(Y).astype(int)
    c.paint(ALL(c), UMBER, 0.67)                                                     # the table
    paper = rect(c, 2, 2, 42, 40) & ~c.poly_mask([(42.5, 33.0), (42.5, 40.5), (35.0, 40.5)])
    c.paint(paper, SAFFRON, 0.0)
    c.paint(c.poly_mask([(42.0, 33.5), (35.5, 40.0), (39.5, 33.5)]), SAFFRON, 0.67, 1.2)   # curled corner
    # a chequered border (dark, pale and red blocks) round the chart
    band = paper & rect(c, 3, 3, 41, 39) & ~rect(c, 4, 4, 40, 38)
    k = ((tx + ty) // 3) % 4
    c.paint(band, PEARL, 0.0, 1.2)
    c.paint(band & (k == 0), UMBER, 1.0, 1.25)
    c.paint(band & (k == 2), EMBER, 0.34, 1.25)
    # the parchment sea with faint grid lines
    sea = rect(c, 4, 4, 40, 38)
    c.paint(sea & rect(c, 5, 5, 39, 37) & (((tx - 4) % 7 == 6) | ((ty - 4) % 7 == 6)), UMBER, 0.0, 1.1)
    # the island, ringed by blue shallows and a dark inked coast, with a small islet off the south-east
    isl = [(22, 6), (25, 5.5), (28, 7), (29.5, 9.5), (28.5, 11.5), (31, 12.5), (33.5, 14), (34, 17), (32, 19.5), (34.5, 22.5),
           (33.5, 25.5), (30.5, 25.5), (28.5, 23.5), (26.5, 25.5), (28.5, 28.5), (28.0, 31.5), (25.5, 33.0), (23, 32.5),
           (22, 29.5), (20.0, 33.0), (16.5, 33.0), (15.5, 30.0), (13.5, 28.0), (10.0, 28.5), (7.0, 27.0), (9.5, 25.0),
           (12.5, 24.0), (11.0, 21.5), (13.5, 19.0), (11.0, 15.5), (13.0, 12.0), (15.5, 11.0), (17.5, 12.0), (19.0, 9.0), (20.5, 7)]
    land = c.poly_mask(isl) | ellipse(c, 32.0, 30.5, 2.0, 1.6)
    shallows = ndimage.binary_dilation(land, iterations=22) & sea
    c.paint(shallows, LAPIS, 0.34, 1.2)
    c.paint(ndimage.binary_dilation(land, iterations=6), UMBER, 1.0, 1.3)            # inked coast
    c.paint(land, SAFFRON, 0.67, 1.3)
    for (wx, wy) in ((6, 6), (12, 6), (34, 6), (6, 16), (37, 11), (6, 22), (38, 27), (17, 36), (5, 28), (37, 33), (30, 5)):
        wave = (rect(c, wx, wy, wx + 1, wy + 1) | rect(c, wx + 1, wy - 1, wx + 2, wy) | rect(c, wx + 2, wy, wx + 3, wy + 1)
                | rect(c, wx + 3, wy - 1, wx + 4, wy))
        c.paint(wave & ~shallows, LAPIS, 0.67, 1.15)
    # hills (shaded mounds) and woods (little clumps of trees)
    for (hx, hy, hw, hh) in ((16.5, 24.0, 4.0, 5.0), (24.0, 9.5, 2.8, 3.4), (29.5, 17.0, 3.0, 3.6), (24.5, 29.5, 2.6, 3.0)):
        hill = c.poly_mask([(hx - hw, hy + hh * 0.4), (hx + hw, hy + hh * 0.4), (hx, hy - hh * 0.6)])
        c.paint(hill, UMBER, np.where(X < hx, 0.34, 0.67), 1.4)
    for (wx, wy) in ((14.5, 13.5), (13.5, 17.5), (12.5, 25.5), (18.5, 29.5), (22.5, 24.5), (31.0, 22.0), (25.5, 18.0),
                     (31.5, 13.5), (9.0, 26.0), (26.5, 13.5), (20.0, 9.5)):
        c.paint((c.circle(wx, wy, 1.05) | c.circle(wx + 1.2, wy + 0.9, 0.9)) & land, FERN, 0.67, 1.35)
    # dotted trails from the anchorages to the red X
    dotted_trail(c, [(27.5, 25.0), (25.0, 22.0), (22.5, 19.5), (20.5, 18.0)])
    dotted_trail(c, [(22.0, 7.5), (21.5, 11.0), (19.5, 14.5)])
    xm = np.zeros_like(X, bool)
    for i in range(6):                                       # a crisp 6 x 6 pixel X with bold strokes
        xm |= rect(c, 15 + i, 13 + i, 16.9 + i, 14 + i) | rect(c, 20.1 - i, 13 + i, 22 - i, 14 + i)
    c.paint(xm & rect(c, 15, 13, 21, 19), EMBER, 0.67, 1.9)
    # a compass rose in the lower left, little ships and a sea serpent in the margins
    compass_rose(c, 10.0, 32.0)
    ship_doodle(c, 9.0, 10.0)
    ship_doodle(c, 37.0, 19.5)
    serp = np.zeros_like(X, bool)                            # a sea serpent: two arched coils and a raised head
    for hx in (24.5, 29.0):
        serp |= ellipse(c, hx, 36.8, 2.0, 2.6) & ~ellipse(c, hx, 37.2, 0.9, 1.6) & (Y < 37.4)
    serp |= tube(c, [(32.0, 37.2), (32.8, 34.0), (34.2, 32.6)], 1.6, 1.4) | ellipse(c, 35.0, 32.6, 1.7, 1.2)
    serp |= tube(c, [(22.5, 37.0), (20.8, 35.8)], 1.3, 0.6)
    c.paint(serp, FERN, 1.0, 1.5)
    c.paint(rect(c, 35.0, 32.0, 36.0, 33.0), PEARL, 0.0, 1.7)                          # eye
    c.paint(rect(c, 37.0, 33.0, 38.0, 34.0), EMBER, 0.67, 1.6)                          # tongue
    # the parrot perched on the top-right corner of the chart, facing left
    px, py = 36.5, 9.5
    c.paint(tube(c, [(px + 1.0, py + 3.5), (px + 2.6, py + 10.0)], 2.0, 1.0), LAPIS, 0.67, 1.6)   # long tail
    c.paint(ellipse(c, px, py, 2.8, 4.2, 0.2), FERN, 0.34, 1.6)                       # body
    c.paint(ellipse(c, px + 1.2, py + 0.6, 1.5, 3.4, 0.2), FERN, 1.0, 1.65)          # wing
    c.paint(ellipse(c, px + 1.7, py + 3.2, 1.0, 1.2, 0.2), EMBER, 0.34, 1.7)          # red wing tip
    c.paint(c.circle(px - 0.8, py - 4.2, 2.2), FERN, 0.0, 1.65)                       # head
    c.paint(c.poly_mask([(px - 2.6, py - 5.2), (px - 4.8, py - 4.2), (px - 4.2, py - 2.2), (px - 2.6, py - 3.0)]), SAFFRON, 1.0, 1.7)  # beak
    c.paint(rect(c, math.floor(px - 1.5), math.floor(py - 5.0), math.floor(px - 0.5), math.floor(py - 4.0)), UMBER, 1.0, 1.8)  # eye
    c.paint(rect(c, px - 1.5, py + 4.0, px + 1.5, py + 5.0), UMBER, 0.0, 1.6)          # feet
    frame(c)
    return encode(c.to_tiles())


def nautilus():
    """Twenty Thousand Leagues Under the Seas: the riveted Nautilus gliding over the undersea forest, its
    round windows glowing, divers in brass helmets walking among kelp and coral below, fish shoals and
    jellyfish all around."""
    c = Canvas(44, 42)
    X, Y = c.X, c.Y
    tx = np.floor(X).astype(int)
    ty = np.floor(Y).astype(int)
    # water darkening with depth, slanting light rays near the top
    c.paint(ALL(c), LAPIS, np.where(Y < 16, 0.34, np.where(Y < 29, 0.67, 1.0)))
    ray = np.sin((X + 0.6 * Y) * 0.42)
    c.paint((Y < 30) & (ray > 0.6), LAPIS, 0.0, 1.0)
    c.paint((Y < 24 - 4 * np.sin(X * 0.13)) & (ray > 0.9), PEARL, 0.34, 1.05)                # sunbeams
    # the seabed: rippled sand and dark rocks
    sand = Y > 37.5 + 0.8 * np.sin(X * 0.4)
    c.paint(sand, SAFFRON, np.where((tx + 2 * ty) % 5 == 0, 0.67, 0.34))
    for (rx_, ry_, s_) in ((12.0, 38.3, 2.4), (31.5, 38.4, 2.0)):
        c.paint(ellipse(c, rx_, ry_, s_, s_ * 0.6), UMBER, 0.67, 1.2)
    for (px_, py_) in ((9.5, 39.0), (23.0, 39.0), (35.5, 39.0), (2.5, 38.5)):               # pebbles
        c.paint(rect(c, px_ - 1.0, py_ - 0.5, px_ + 1.0, py_ + 0.5) | rect(c, px_ - 0.5, py_ - 1.0, px_ + 0.5, py_), UMBER, 1.0, 1.25)
    for gx in (16.0, 25.0, 30.0):                                                           # sea-grass tufts
        for d in (-1, 0, 1):
            c.paint(rect(c, gx + d, 38.0 - (1 - abs(d)) * 1.0, gx + d + 1, 39.5), FERN, 0.67, 1.3)
    # kelp forests on both sides: tall wavy strands with blades
    for k, kx in enumerate((2.0, 10.5, 33.5, 37.5, 41.5)):
        top = 22.0 + (k * 5) % 6
        pts = [(kx + 0.6 * math.sin(t * 0.8 + k * 1.7), t) for t in np.arange(40.5, top, -1.0)]
        c.paint(c.line_mask(pts, 1.2), FERN, 1.0, 1.3)
        for i in range(2, len(pts) - 1, 3):
            s = 1 if (i + k) % 2 else -1
            c.paint(ellipse(c, pts[i][0] + s * 1.0, pts[i][1] - 0.6, 1.0, 0.55, -s * 0.6), FERN, 0.34, 1.3)
    # coral trees in red and orange
    for (cx_, cy_, h, sh) in ((14.0, 39.5, 2.8, 0.34), (22.5, 40.0, 2.6, 0.67), (38.5, 39.0, 3.6, 0.34)):
        coral(c, cx_, cy_, h, 0.0, 2, 1.2, sh)
    # a giant clam holding its pearl, and starfish on the sand
    c.paint(ellipse(c, 6.0, 37.0, 3.4, 2.4) & (Y < 37.0), PEARL, 0.67, 1.45)
    c.paint(ellipse(c, 6.0, 37.0, 3.4, 1.6) & (Y >= 37.0), PEARL, 1.0, 1.45)
    c.paint(ellipse(c, 6.0, 36.9, 2.3, 1.0), UMBER, 1.0, 1.5)
    c.paint(c.circle(6.5, 36.5, 0.95), PEARL, 0.0, 1.7)
    for (sx, sy) in ((29.5, 40.0), (34.5, 38.5)):
        star = c.line_mask([(sx - 1.4, sy), (sx + 1.4, sy)], 0.7) | c.line_mask([(sx, sy - 1.3), (sx, sy + 1.2)], 0.7)
        c.paint(star, EMBER, 0.67, 1.5)
    # the Nautilus: a long spindle of riveted steel plates, a dark band of glowing round windows, a spur
    ncx, ncy, L = 22.0, 9.5, 18.5
    u = (X - ncx) / L
    hh = 5.0 * np.clip(1 - u ** 2, 0, 1) ** 0.5
    hull = (np.abs(Y - ncy) < hh) & (np.abs(u) < 1)
    spur = c.poly_mask([(ncx + L - 2.0, ncy - 1.2), (ncx + L + 1.6, ncy), (ncx + L - 2.0, ncy + 1.2)])
    c.paint(hull | spur, UMBER, np.where(Y < ncy - 3.5, 0.0, np.where(Y < ncy + 1.5, 0.34, 0.67)), 1.3)
    c.paint(hull & ((tx - 4) % 5 == 0) & (np.abs(Y - ncy) > 1.5), UMBER, 1.0, 1.35)            # plate seams
    rivets = hull & ((ty == int(ncy) - 3) | (ty == int(ncy) + 3)) & (tx % 2 == 0)
    c.paint(rivets, PEARL, 0.67, 1.4)                                                        # rows of rivets
    for wx in (-12, -6, 6, 12):                                                               # round portholes
        c.paint(c.circle(ncx + wx + 0.5, ncy + 0.5, 1.75), PEARL, 0.34, 1.5)
        c.paint(c.circle(ncx + wx + 0.5, ncy + 0.5, 1.15), SAFFRON, 0.0, 1.6)
    c.paint(c.circle(ncx + 0.5, ncy + 0.5, 2.6), PEARL, 0.34, 1.5)                            # the great salon window
    c.paint(c.circle(ncx + 0.5, ncy + 0.5, 1.9), SAFFRON, 0.0, 1.6)
    c.paint(c.poly_mask([(ncx - 5, ncy - hh.max() - 0.0), (ncx + 3, ncy - hh.max()), (ncx + 2, ncy - 7.2), (ncx - 4, ncy - 7.2)]), UMBER, 0.67, 1.4)  # platform
    c.paint(rect(c, ncx - 3, ncy - 7, ncx - 1, ncy - 6), SAFFRON, 0.0, 1.6)                  # lantern
    c.paint(c.line_mask([(ncx - L - 0.6, ncy - 2.8), (ncx - L - 0.6, ncy + 2.8)], 1.0) | rect(c, ncx - L - 1.0, ncy - 0.5, ncx - L + 1.5, ncy + 0.5),
            UMBER, 1.0, 1.5)                                                                     # propeller
    # fish shoals in mid-water (and a few near the surface)
    for i in range(8):
        pixel_fish(c, 13 + (i % 4) * 4 + (i // 4) * 2, 19 + (i // 4) * 2 + (i % 2), SAFFRON, 0.0)
    for i in range(6):
        pixel_fish(c, 15 + (i % 3) * 4 + (i // 3) * 2, 25 + (i // 3) * 2, EMBER, 0.34)
    for i in range(4):
        pixel_fish(c, 29 + i * 3.5, 1.5 + (i % 2), EMBER, 0.34)
    # two divers in brass helmets walking along the bottom, one with a lamp; jellyfish drifting
    diver(c, 18.0, 38.0)
    diver(c, 27.0, 38.0, lamp=True)
    for (jx, jy) in ((38.5, 18.0), (5.5, 17.5), (30.5, 28.0)):
        jellyfish(c, jx, jy)
    frame(c)
    return encode(c.to_tiles())


SCENES = {
    "footprint": footprint, "windmills": windmills, "raft": raft, "lilliput": lilliput,
    "whitewhale": whitewhale, "undergroundsea": undergroundsea,
    "treasuremap": treasuremap, "nautilus": nautilus,
}
