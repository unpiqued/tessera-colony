"""Stage pack: eight iconic scenes from Shakespeare, drawn with the supersampled Canvas of art.py (a
tile's colour family comes from the dominant object under it, its tone from the shading).

Gentle: Romeo and Juliet's balcony, Hamlet with Yorick's skull, the Macbeth witches at their cauldron,
the Tempest shipwreck.  Challenge: the Midsummer Night's Dream fairy wood, Cleopatra's barge.
Master (busy, every colour in many islands): the Globe playhouse, the three caskets at Belmont.
"""
import math
import random

import numpy as np

from art import Canvas, LAPIS, SAFFRON, FERN, EMBER, UMBER, PEARL, encode
from art_scenes import ALL, ellipse, rect, tube, frame, smooth_noise


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------

def tiles(c):
    """Integer tile coordinates of every supersampled pixel (for crisp tile-aligned patterns)."""
    return np.floor(c.X).astype(int), np.floor(c.Y).astype(int)


def sparkle(c, x, y, s=1.0, fam=PEARL, shade=0.0, prio=1.6):
    """A four-pointed star (a plus of tiles when centred on a tile centre)."""
    m = (c.circle(x, y, 0.55 * s) | c.line_mask([(x - s, y), (x + s, y)], 0.5 * s)
         | c.line_mask([(x, y - s), (x, y + s)], 0.5 * s))
    c.paint(m, fam, shade, prio)


def xf(pts, ox, oy, ang):
    """Map local points (u right, v UP) around the origin (ox, oy), tilted by `ang` (top leans right
    for ang > 0), to canvas points."""
    ca, sa = math.cos(ang), math.sin(ang)
    return [(ox + u * ca + v * sa, oy + u * sa - v * ca) for u, v in pts]


def bezier(p0, p1, p2, n=16):
    return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
             (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]) for t in np.linspace(0, 1, n)]


def blobs(c, parts):
    m = np.zeros_like(c.X, bool)
    for (a, b, r) in parts:
        m |= c.circle(a, b, r)
    return m


# ---------------------------------------------------------------------------
# gentle
# ---------------------------------------------------------------------------

def balcony():
    """Romeo and Juliet, II.ii: Juliet leans from a moonlit stone balcony on the right, ivy climbing
    the wall; Romeo looks up from the dark garden below; cypresses, a full moon and stars."""
    c = Canvas(38, 46)
    X, Y = c.X, c.Y
    tx, ty = tiles(c)
    # night sky, the moon with a pale halo, stars
    c.paint(ALL(c), LAPIS, 1.0)
    c.paint(c.circle(8.5, 8.5, 5.2), LAPIS, 0.5)
    c.paint(c.circle(8.5, 8.5, 3.5), PEARL, np.clip(0.02 + 0.09 * np.hypot(X - 7.6, Y - 7.6), 0, 0.4), 1.3)
    for (sx, sy, s) in ((16, 4, 1.0), (2, 18, 0.9), (14, 13, 0.8), (17, 20, 0.9)):
        sparkle(c, sx + 0.5, sy + 0.5, s, PEARL, 0.0)
    # two dark cypresses and the garden hedge, a lawn at the bottom
    for (cx, top, w) in ((3.5, 23.0, 2.7), (14.0, 25.5, 2.3)):
        c.paint(ellipse(c, cx, 37.0, w, 37.0 - top), FERN, 1.0, 1.1)
    hedge = Y > 34.0 + 1.1 * np.abs(np.sin(X * 0.45))
    c.paint(hedge, FERN, np.where(np.sin(X * 0.9) + 0.4 * np.sin(Y * 1.3) > 0.6, 0.667, 1.0))
    c.paint(Y > 42.0 + 0.4 * np.sin(X * 0.5), FERN, 0.333)
    for (rx_, ry_) in ((2.5, 37.5), (6.5, 39.5), (17.0, 37.0)):
        c.paint(c.circle(rx_, ry_, 0.9), EMBER, 0.333, 1.5)
    # the house wall: moonlit ashlar, staggered blocks shown by tone only
    wall = X >= 21.0
    row = ty // 2
    blk = ((tx + 2 * (row % 2)) // 4 + row) % 2
    c.paint(wall, PEARL, np.where(X < 22.5, 1.0, np.where(blk == 1, 0.667, 0.333)))
    # the lit doorway with its moulded arch
    arch = rect(c, 24.0, 11.0, 35.5, 21.0) | (c.circle(29.75, 11.0, 5.75) & (Y < 11.0))
    door = rect(c, 25.2, 11.0, 34.3, 21.0) | (c.circle(29.75, 11.0, 4.55) & (Y < 11.0))
    c.paint(arch, PEARL, 0.0, 1.2)
    c.paint(door, SAFFRON, np.clip(0.05 + 0.08 * np.hypot(X - 31, Y - 13), 0, 0.7), 1.2)
    # Juliet leaning out over the rail: dress, hair, face, an arm on the coping
    c.paint(c.poly_mask([(25.4, 15.0), (29.4, 14.8), (31.0, 21.0), (24.8, 21.0)]), EMBER,
            np.clip(0.45 + 0.2 * np.sin(X * 2.5), 0, 1), 1.5)
    c.paint(ellipse(c, 29.0, 15.8, 1.4, 3.2, 0.2) | c.circle(28.0, 12.4, 1.9), UMBER, 0.333, 1.6)
    c.paint(c.circle(26.9, 13.0, 1.45), EMBER, 0.0, 1.7)
    c.paint(tube(c, [(26.0, 16.0), (23.4, 18.8), (21.6, 20.0)], 1.2, 1.0), EMBER, 0.667, 1.7)
    c.paint(c.circle(21.2, 20.0, 0.75), EMBER, 0.0, 1.8)
    # the balcony: coping, balusters with dark gaps, base slab, corbels and its shadow on the wall
    c.paint(rect(c, 21.0, 27.8, 38, 29.6), PEARL, 1.0)
    c.paint(rect(c, 16.5, 22.0, 38, 26.4), UMBER, 1.0, 1.2)
    bal = rect(c, 16.5, 23.0, 38, 26.4) & (((X - 17.0) % 2.4) < 1.3)
    c.paint(bal, PEARL, np.clip(0.1 + 0.2 * np.abs(((X - 17.0) % 2.4) - 0.65), 0, 1), 1.3)
    c.paint(rect(c, 16.0, 20.6, 38, 22.0), PEARL, 0.0, 1.4)
    c.paint(rect(c, 15.6, 26.4, 38, 27.9), PEARL, 0.0, 1.4)
    for kx in (18.0, 26.0, 34.0):
        c.paint(c.poly_mask([(kx - 1.6, 27.9), (kx + 1.6, 27.9), (kx + 0.4, 31.2), (kx - 0.4, 31.2)]), PEARL, 0.333, 1.3)
    # ivy climbing the corner of the wall and hanging from the balcony
    r = random.Random(5)
    paths = [[(22.0, 46), (21.4, 38), (22.2, 31), (21.2, 26)], [(21.5, 20.5), (22.0, 12), (23.2, 4), (22.0, -1)],
             [(17.0, 28.0), (17.5, 31.5), (16.8, 34.0)], [(30.5, 28.0), (30.9, 31.5)], [(37.0, 28), (36.5, 33)]]
    for pts in paths:
        for (x0, y0), (x1, y1) in zip(pts[:-1], pts[1:]):
            for t in np.linspace(0, 1, 7):
                lx, ly = x0 + (x1 - x0) * t + r.uniform(-0.7, 0.7), y0 + (y1 - y0) * t
                c.paint(ellipse(c, lx, ly, r.uniform(0.9, 1.3), r.uniform(0.6, 0.9), r.uniform(0, 3)), FERN,
                        r.uniform(0.3, 0.7), 1.25)
    # Romeo in the garden, looking up with one arm raised: cloak, doublet, hose, head
    c.paint(c.poly_mask([(8.0, 32.8), (9.6, 32.6), (8.4, 42.5), (4.6, 42.2)]), UMBER, 0.333, 1.5)
    c.paint(c.line_mask([(9.6, 38), (8.8, 44.5)], 1.3) | c.line_mask([(10.6, 38), (11.6, 44.5)], 1.3), UMBER, 1.0, 1.5)
    c.paint(c.poly_mask([(8.3, 32.9), (11.9, 32.9), (12.4, 38.4), (7.8, 38.4)]), SAFFRON, 0.333, 1.6)
    c.paint(tube(c, [(11.4, 33.6), (13.4, 31.2), (14.8, 28.8)], 1.2, 1.0), SAFFRON, 0.667, 1.6)
    c.paint(c.circle(15.1, 28.3, 0.7), EMBER, 0.0, 1.8)
    c.paint(c.circle(10.4, 31.2, 1.45), EMBER, 0.0, 1.7)
    c.paint(c.circle(9.9, 30.6, 1.5) & ((X < 10.1) | (Y < 30.3)), UMBER, 1.0, 1.8)
    frame(c)
    return encode(c.to_tiles())


def sprite(c, x0, y0, rows, colours, prio=1.8):
    """Paint a tile-aligned sprite: each character of `rows` names a (family, shade) in `colours`
    (other characters leave the canvas as is); its top-left tile is (x0, y0)."""
    tx, ty = tiles(c)
    for j, row in enumerate(rows):
        for i, ch in enumerate(row):
            if ch in colours:
                fam, sh = colours[ch]
                c.paint((tx == x0 + i) & (ty == y0 + j), fam, sh, prio)


def yorick():
    """Hamlet, V.i: the prince in black holds up Yorick's skull in the churchyard; leaning gravestones,
    a fresh grave, Elsinore castle on its headland under a grey sky."""
    c = Canvas(42, 42)
    X, Y = c.X, c.Y
    n = smooth_noise(c, 4, 0.3)
    # heavy grey sky, a strip of sea, the dark headland and the castle with green copper spires
    c.paint(ALL(c), PEARL, np.where((n > 0.25) & (np.hypot(X - 22, Y - 8) > 6), 0.667, 1.0))
    c.paint(rect(c, 0, 24.5, 30, 28.5), LAPIS, 0.667)
    head = c.poly_mask([(18, 30), (21, 26.5), (24.5, 22.5), (30, 21.5), (42, 21.0), (42, 31), (18, 31)])
    c.paint(head, UMBER, np.where(np.sin(Y * 1.7 + X * 0.25) > 0.75, 1.0, 0.667))
    keep = rect(c, 25.5, 15.5, 40.0, 21.5) | rect(c, 25.0, 11.5, 28.6, 21.5) | rect(c, 36.4, 12.5, 40.2, 21.5)
    keep |= rect(c, 30.4, 8.0, 34.2, 21.5)
    keep |= rect(c, 25.5, 14.6, 40.0, 15.6) & (((X - 25.5) % 1.8) < 0.9)
    c.paint(keep, LAPIS, 1.0, 1.2)
    for (sx, base, top, hw) in ((26.8, 11.6, 7.0, 2.0), (32.3, 8.1, 1.8, 2.2), (38.3, 12.6, 8.0, 2.0)):
        c.paint(c.poly_mask([(sx - hw, base), (sx + hw, base), (sx, top)]), FERN, 0.333, 1.3)
    for (wx, wy) in ((32.3, 11.5), (27.3, 17.0), (35.0, 17.5)):
        c.paint(rect(c, wx - 0.5, wy, wx + 0.5, wy + 1.4), SAFFRON, 0.0, 1.6)
    # the churchyard grass
    c.paint(Y > 30.0 + 0.9 * np.sin(X * 0.22 + 1.0), FERN, np.where(smooth_noise(c, 9, 0.9) > 0.2, 0.667, 0.333))
    # leaning gravestones (a cross in the middle) and a fresh mound with a spade
    for (bx, by, w, h, a, cross) in ((22.5, 34.0, 3.4, 5.6, 0.2, False), (29.5, 33.0, 1.6, 7.4, -0.12, True),
                                     (36.5, 34.0, 3.2, 5.0, 0.24, False)):
        ca, sa = math.cos(a), math.sin(a)
        lx = (X - bx) * ca + (Y - by) * sa
        ly = (X - bx) * sa - (Y - by) * ca
        if cross:
            m = ((np.abs(lx) <= w / 2) & (ly >= 0) & (ly <= h)) | ((np.abs(lx) <= 2.4) & (np.abs(ly - h + 2.2) <= 0.75))
        else:
            m = (((np.abs(lx) <= w / 2) & (ly >= 0) & (ly <= h - w / 2)) | (lx ** 2 + (ly - h + w / 2) ** 2 <= (w / 2) ** 2))
        c.paint(m, PEARL, np.where(lx > 0.3, 1.0, 0.667), 1.3)
    mound = ellipse(c, 30.0, 40.5, 10.5, 3.6)
    c.paint(mound, UMBER, np.where(np.sin(X * 2.3 + Y * 3.1) > 0.3, 0.333, 0.0), 1.1)
    c.paint(c.line_mask([(38.2, 38.0), (39.8, 30.6)], 0.7), UMBER, 1.0, 1.5)
    c.paint(c.poly_mask([(37.3, 37.2), (39.4, 37.6), (38.8, 40.6), (37.0, 40.2)]), PEARL, 0.667, 1.5)
    # Hamlet in black: cloak, doublet, white collar
    c.paint(c.poly_mask([(5.8, 15.8), (13.4, 15.8), (15.8, 42), (1.2, 42)]), UMBER, 1.0, 1.4)
    c.paint(c.poly_mask([(7.4, 16.0), (12.6, 16.0), (13.2, 29.0), (7.0, 29.0)]), UMBER, 0.667, 1.45)
    c.paint(ellipse(c, 9.9, 15.4, 2.7, 1.0), PEARL, 0.0, 1.6)
    # his head in profile, facing the skull
    c.paint(c.circle(10.0, 12.5, 2.3) | c.circle(12.3, 12.9, 0.55), EMBER, 0.0, 1.6)
    c.paint(c.circle(9.3, 11.9, 2.6) & ((X < 9.4) | (Y < 10.9)), UMBER, 0.333, 1.7)
    c.paint(c.circle(11.2, 12.2, 0.4), UMBER, 1.0, 1.9)
    # the raised arm, cuff and hand holding up the skull
    c.paint(tube(c, [(12.5, 17.2), (17.0, 17.6), (21.2, 14.0)], 2.1, 1.6), UMBER, 1.0, 1.6)
    c.paint(c.circle(21.2, 13.9, 0.85), PEARL, 0.0, 1.7)
    c.paint(c.circle(22.5, 12.7, 1.1), EMBER, 0.0, 1.75)
    sprite(c, 19, 5, [".XXXXX.",
                      "XXXXXXX",
                      "XooXooX",
                      "XooXooX",
                      "XXXoXXX",
                      ".XXXXX.",
                      ".XoXoX."], {"X": (PEARL, 0.0), "o": (UMBER, 1.0)})
    frame(c)
    return encode(c.to_tiles())


def hooded(c, x, foot, h, hands):
    """A hooded witch seen from the front, `h` tiles tall: a dark green cloak with a drooping hood, a
    dark hood opening round a pale face with a long nose, and sleeves reaching to each point of `hands`."""
    top, k = foot - h, h / 20.0
    X = c.X
    cloak = c.poly_mask([(x - 1.6 * k, top + 0.2 * k), (x + 0.6 * k, top + 1.0 * k), (x + 2.2 * k, top + 3.5 * k),
                         (x + 2.8 * k, top + 6.5 * k), (x + 3.6 * k, top + 8 * k), (x + 5.2 * k, foot), (x - 5.2 * k, foot),
                         (x - 3.6 * k, top + 8 * k), (x - 2.8 * k, top + 6.5 * k), (x - 2.2 * k, top + 3.5 * k)])
    for (hx, hy) in hands:
        s = 1 if hx > x else -1
        cloak |= tube(c, [(x + s * 2.8 * k, top + 9.0 * k), (hx, hy)], 2.0 * k, 1.4 * k)
    c.paint(cloak, FERN, np.where(X > x + 1.2 * k, 1.0, 0.667), 1.4)
    c.paint(ellipse(c, x, top + 5.4 * k, 1.75 * k, 2.4 * k), UMBER, 1.0, 1.5)
    c.paint(ellipse(c, x, top + 6.0 * k, 1.15 * k, 1.75 * k), EMBER, 0.0, 1.6)
    c.paint(c.poly_mask([(x - 0.4 * k, top + 5.6 * k), (x + 0.4 * k, top + 5.6 * k), (x, top + 7.6 * k)]), EMBER, 0.333, 1.65)
    for (hx, hy) in hands:
        c.paint(c.circle(hx, hy, 0.8 * k), EMBER, 0.0, 1.65)


def witches():
    """Macbeth, IV.i: the three weird sisters round their bubbling cauldron on the blasted heath, a
    twisted bare tree, thunder clouds and a stroke of lightning."""
    c = Canvas(44, 42)
    X, Y = c.X, c.Y
    # storm sky, rolling paler thunder clouds, lightning
    c.paint(ALL(c), LAPIS, np.where(Y < 11, 1.0, 0.667))
    cl = blobs(c, [(4, 2, 4.5), (11, 0, 4.5), (18, 2.5, 3.5), (27, 1, 5), (35, 3, 4), (42, 0.5, 4.5), (14, 6, 2.6),
                   (31, 6.5, 2.8), (40, 6, 3.0)])
    c.paint(cl, LAPIS, np.where(Y > 4.5 + 1.5 * smooth_noise(c, 2, 0.8), 0.333, 0.0), 1.1)
    bolt = [(37.0, 7.5), (34.8, 12.0), (38.0, 12.8), (35.6, 19.5)]
    c.paint(c.line_mask(bolt, 1.0) | c.line_mask([(34.8, 12.0), (32.2, 16.0)], 0.6), SAFFRON, 0.0, 1.6)
    # the heath: far ridge and near ground
    c.paint(Y > 29.0 + 1.2 * np.sin(X * 0.21 + 0.7), UMBER, 0.667)
    c.paint(Y > 33.0 + 0.8 * np.sin(X * 0.3 + 2.0), UMBER, 0.333)
    c.paint((Y > 33.0) & (smooth_noise(c, 5, 0.9) > 0.3), FERN, 0.333, 1.1)
    # the bare twisted tree on the left
    tree = tube(c, [(1.8, 34), (1.4, 27), (2.8, 20), (2.0, 13), (3.6, 6)], 2.6, 1.2)
    for pts, w in (([(2.6, 19), (5.6, 15.0), (8.4, 13.4), (9.6, 9.5)], 1.1), ([(2.2, 13), (0.4, 9.5)], 0.9),
                   ([(3.2, 8), (6.6, 4.5), (7.6, 1.5)], 0.9), ([(5.6, 15.0), (5.2, 10.5)], 0.7)):
        tree |= tube(c, pts, w, 0.5)
    c.paint(tree, UMBER, 1.0, 1.3)
    # the three sisters: one behind the pot with arms raised, two beside it
    hooded(c, 22.0, 30.0, 21.0, [(16.2, 11.5), (27.8, 11.5)])
    hooded(c, 9.5, 41.0, 24.0, [(14.0, 24.2), (5.0, 26.0)])
    hooded(c, 34.5, 41.0, 24.0, [(30.0, 24.2), (40.0, 14.5)])
    # the cauldron on its fire: flames, logs, the black pot, its rim and the bubbling green brew
    for (fx, fy, fr) in ((16.0, 37.5, 2.2), (19.5, 37, 2.8), (24.5, 37, 2.8), (28.0, 37.5, 2.2), (22, 36.5, 2.6)):
        c.paint(c.poly_mask([(fx - fr, fy + 2), (fx, fy - 2 * fr), (fx + fr, fy + 2)]), EMBER, 0.333, 1.5)
        c.paint(c.poly_mask([(fx - fr * 0.5, fy + 2), (fx, fy - fr), (fx + fr * 0.5, fy + 2)]), SAFFRON, 0.0, 1.55)
    c.paint(c.line_mask([(15.0, 39.8), (29.0, 38.4)], 1.4) | c.line_mask([(15.5, 38.4), (28.5, 39.8)], 1.4), UMBER, 0.333, 1.6)
    pot = ellipse(c, 22.0, 29.0, 8.0, 6.8) & (Y > 25.0)
    c.paint(pot, UMBER, np.where(np.hypot(X - 18.5, Y - 27.5) < 2.6, 0.667, 1.0), 1.6)
    c.paint(ellipse(c, 22.0, 25.2, 8.4, 2.0), UMBER, 0.333, 1.65)
    c.paint(ellipse(c, 22.0, 25.0, 6.9, 1.3), FERN, 0.0, 1.7)
    for (bx, by, br) in ((19.0, 24.3, 0.8), (24.6, 24.0, 1.0), (21.8, 23.2, 0.7)):
        c.paint(c.circle(bx, by, br), PEARL, 0.0, 1.75)
    frame(c)
    return encode(c.to_tiles())


def tempest():
    """The Tempest, I.i: a ship heels over in mountainous waves under a lightning-torn sky; Prospero,
    staff raised, conjures the storm from the cliff of his island."""
    c = Canvas(48, 36)
    X, Y = c.X, c.Y
    # storm sky with swirling paler clouds, and lightning on the left
    c.paint(ALL(c), LAPIS, 1.0)
    sw = smooth_noise(c, 6, 0.32) + 0.25 * np.sin(np.hypot(X - 20, Y - 6) * 0.9)
    c.paint((sw > 0.1) & (Y < 22), LAPIS, np.where((sw > 0.42) & (np.hypot(X - 18, Y - 12) > 9), 0.333, 0.667))
    c.paint(c.line_mask([(9.5, -1), (7.0, 4.5), (10.0, 5.5), (6.0, 14.0)], 1.0)
            | c.line_mask([(7.0, 4.5), (3.5, 8.0)], 0.6), SAFFRON, 0.0, 1.6)
    # the far swell with a line of foam
    surf = 18.0 + 2.2 * np.sin(X * 0.42 + 1.0)
    c.paint(Y > surf, LAPIS, np.where(Y > surf + 4, 0.667, 0.333))
    c.paint((Y > surf) & (Y < surf + 1.1), PEARL, 0.333, 1.2)
    # the ship, heeling over: hull with a gilded strake, three masts with bellying sails, a pennant
    ox, oy, a = 18.0, 21.0, 0.3
    hull = c.poly_mask(xf([(-11, 3.5), (-10.2, 0), (-7, -2.4), (7, -2.6), (10.4, 0.4), (11.6, 2.6), (6.5, 2.0),
                           (-6.5, 2.0)], ox, oy, a))
    c.paint(hull, UMBER, 0.667, 1.3)
    c.paint(c.line_mask(xf([(-9.8, 0.6), (10.6, 0.8)], ox, oy, a), 0.6), SAFFRON, 0.333, 1.4)
    for (u, h) in ((-6.2, 13.5), (0.4, 16.0), (6.8, 12.5)):
        c.paint(c.line_mask(xf([(u, 1.5), (u, h)], ox, oy, a), 0.7), UMBER, 1.0, 1.5)
        for (v0, v1, hw) in ((h - 5.6, h - 2.0, 1.7), (3.4, h - 7.0, 2.4)):
            sail = c.poly_mask(xf([(u - hw, v1), (u + hw, v1), (u + hw + 1.0, v0), (u - hw + 1.0, v0)], ox, oy, a))
            c.paint(sail, PEARL, 0.0, 1.4)
    c.paint(c.poly_mask(xf([(0.6, 15.0), (3.8, 15.6), (0.6, 16.4)], ox, oy, a)), EMBER, 0.333, 1.6)
    # the near breaker curling in front of the hull
    near = 26.0 + 3.0 * np.sin(X * 0.26 + 3.4) - 4.0 * np.exp(-((X - 6.0) / 3.0) ** 2)
    c.paint(Y > near, LAPIS, np.where(Y > near + 3.5, 1.0, 0.667), 1.1)
    c.paint((Y > near) & (Y < near + 1.4), PEARL, 0.0, 1.3)
    for (fx, fy) in ((3.5, 21.0), (8.0, 20.5), (5.5, 18.8)):
        c.paint(c.circle(fx, fy, 1.0), PEARL, 0.0, 1.3)
    # Prospero's island: a cliff with a green crown, spray at its foot
    cliff = c.poly_mask([(32.0, 37), (33.5, 26), (35.5, 20), (38.0, 15.5), (41.0, 12.5), (48, 12), (48, 37)])
    c.paint(cliff, UMBER, np.where(np.sin(X * 0.9 + Y * 0.6) > 0.5, 1.0, 0.667), 1.2)
    c.paint(cliff & (Y < 14.3 + 0.2 * (48 - X)) & (X > 37), FERN, 0.333, 1.25)
    for (fx, fy, fr) in ((33.0, 29.0, 1.6), (34.6, 26.6, 1.2), (31.5, 31.5, 1.4)):
        c.paint(c.circle(fx, fy, fr), PEARL, 0.0, 1.4)
    # Prospero: robe, beard, raised arm and staff with a glowing tip
    foot = 12.8
    c.paint(c.poly_mask([(41.4, 4.6), (44.6, 4.6), (46.8, foot), (39.4, foot)]), EMBER, 0.667, 1.6)
    c.paint(c.circle(43.0, 3.8, 1.3), EMBER, 0.0, 1.7)
    c.paint(c.poly_mask([(41.9, 4.4), (44.1, 4.4), (43.0, 7.6)]), PEARL, 0.0, 1.75)
    c.paint(tube(c, [(42.0, 6.0), (40.2, 3.6)], 1.1, 0.9), EMBER, 0.667, 1.65)
    c.paint(c.line_mask([(41.2, 12.2), (39.4, 0.8)], 0.6), UMBER, 1.0, 1.7)
    sparkle(c, 39.5, 1.5, 1.1, SAFFRON, 0.0, 1.8)
    frame(c)
    return encode(c.to_tiles())


# ---------------------------------------------------------------------------
# challenge
# ---------------------------------------------------------------------------

def fairy(c, x, y, s=1.0):
    """A tiny glowing fairy: a pale halo, two pairs of white wings, a golden body and head."""
    c.paint(c.circle(x, y, 2.7 * s), LAPIS, 0.333, 1.2)
    for side in (-1, 1):
        c.paint(ellipse(c, x + side * 1.35 * s, y - 0.6 * s, 1.35 * s, 0.85 * s, -side * 0.5), PEARL, 0.0, 1.5)
        c.paint(ellipse(c, x + side * 1.0 * s, y + 0.8 * s, 0.95 * s, 0.6 * s, side * 0.5), PEARL, 0.0, 1.5)
    c.paint(ellipse(c, x, y + 0.4 * s, 0.55 * s, 1.3 * s) | c.circle(x, y - 1.3 * s, 0.6 * s), SAFFRON, 0.0, 1.7)


def frond(c, base, ctrl, tip, w=1.5, fam=FERN, shade=0.0, prio=1.3):
    """A fern frond: a tapering blade along a curve, its edges notched into leaflets."""
    pts = bezier(base, ctrl, tip, 25)
    left, right = [], []
    for i, (x, y) in enumerate(pts):
        (xa, ya), (xb, yb) = pts[max(0, i - 1)], pts[min(24, i + 1)]
        d = math.hypot(xb - xa, yb - ya) or 1.0
        nx, ny = -(yb - ya) / d, (xb - xa) / d
        t = i / 24
        hw = w * (1 - t) ** 0.7 * (0.45 + 0.55 * abs(math.sin(t * math.pi * 4.5)))
        left.append((x + nx * hw, y + ny * hw))
        right.append((x - nx * hw, y - ny * hw))
    c.paint(c.poly_mask(left + right[::-1]), fam, shade, prio)


def fairywood():
    """A Midsummer Night's Dream, III.i: the moonlit fairy wood; Bottom, with his ass's head, asleep on
    Titania's flower bank; fairies glowing in the air, fireflies, toadstools and ferns between the oaks."""
    c = Canvas(42, 46)
    X, Y = c.X, c.Y
    r = random.Random(17)
    # night sky, the moon with its halo
    c.paint(ALL(c), LAPIS, 1.0)
    c.paint(c.circle(28.0, 9.0, 5.6), LAPIS, 0.667)
    c.paint(c.circle(28.0, 9.0, 3.6), PEARL, 0.0, 1.3)
    # the canopy of the oaks, leaving a window for the moon
    leaves = blobs(c, [(x_, 1.5 + 2.5 * math.sin(x_ * 0.7) ** 2, 3.4) for x_ in (2, 6, 10, 14, 18, 37, 41)]
                   + [(17, 7.5, 2.4), (10, 9.5, 2.6), (36.0, 9.0, 2.6), (39, 13, 2.4), (21.5, 3.0, 2.2), (34.0, 2.5, 2.4)])
    c.paint(leaves, FERN, np.where(smooth_noise(c, 4, 1.4) > 0.2, 0.667, 1.0), 1.1)
    for (sx, sy) in ((21.5, 11.5), (19.5, 25.5), (30.5, 26.5), (31.5, 3.5)):
        c.paint(c.circle(sx, sy, 0.5), PEARL, 0.0, 1.4)
    # the two oak trunks and their boughs
    trunks = c.poly_mask([(0, 46), (0, 0), (4.4, 0), (3.6, 14), (4.0, 28), (7.4, 40), (9.5, 46)])
    trunks |= c.poly_mask([(42, 46), (42, 0), (37.8, 0), (38.6, 15), (38.2, 30), (35.2, 40), (33.0, 46)])
    trunks |= tube(c, [(3.0, 11), (8.0, 7.5), (13.0, 6.5)], 2.4, 1.0) | tube(c, [(38.8, 12), (34.5, 7.0), (31.0, 5.5)], 2.2, 0.9)
    c.paint(trunks, UMBER, np.where(np.sin(Y * 0.8 + 3 * np.sin(X * 0.9)) > 0.4, 1.0, 0.667), 1.2)
    # the glade, leaf litter between the roots, and Titania's flowery bank
    c.paint((Y > 32.0 + 0.6 * np.sin(X * 0.5)) & ~trunks, FERN, 0.333)
    c.paint((Y > 37.0) & ((X < 9.0 + 0.4 * (Y - 37.0)) | (X > 33.0 - 0.4 * (Y - 37.0))), UMBER, 0.333, 1.25)
    bank = ellipse(c, 20.5, 36.5, 14.5, 5.0)
    c.paint(bank, FERN, 0.667, 1.1)
    kinds = [(EMBER, 0.333), (PEARL, 0.0), (SAFFRON, 0.0), (LAPIS, 0.0), (EMBER, 0.0)]
    for i, (fx, fy) in enumerate([(9, 36), (12, 39), (14, 35), (16, 38), (19, 41), (21, 35), (23, 38), (26, 35),
                                  (28, 38), (31, 36), (25, 41), (14, 42), (30, 33), (11, 33), (18, 33)]):
        fam, sh = kinds[i % 5]
        c.paint(c.circle(fx, fy, 0.95), fam, sh, 1.4)
    # Bottom asleep on the bank: legs and boots, russet tunic and sleeve
    for pts in ([(25.5, 29.6), (30.0, 28.6), (33.6, 30.6)], [(25.5, 31.6), (30.0, 32.2), (33.8, 32.6)]):
        c.paint(tube(c, pts, 1.8, 1.5), UMBER, 0.667, 1.5)
        c.paint(ellipse(c, pts[-1][0] + 0.7, pts[-1][1], 1.3, 1.0), UMBER, 1.0, 1.55)
    c.paint(ellipse(c, 22.0, 30.6, 4.8, 2.4), EMBER, 0.333, 1.5)
    c.paint(tube(c, [(19.5, 29.2), (22.4, 31.8), (25.4, 31.4)], 1.3, 1.1), EMBER, 0.667, 1.55)
    # ...his ass's head (a tile sprite): long ears with dark tips, a closed eye, mane, pale muzzle
    c.paint(ellipse(c, 16.4, 29.6, 2.0, 1.9), PEARL, 0.667, 1.5)
    for (gx, gy, fam) in ((17.6, 27.6, EMBER), (18.2, 29.8, SAFFRON), (17.4, 31.8, LAPIS)):
        c.paint(c.circle(gx, gy, 0.8), fam, 0.0, 1.7)
    sprite(c, 6, 18, [".....d..d..",
                      ".....dd.dd.",
                      ".....Gi.Gi.",
                      ".....Gi.Gi.",
                      ".....GG.GG.",
                      "....GGGGGGm",
                      "...GGGGGGGm",
                      "..GGkkGGGGm",
                      ".GGGGGGGGGm",
                      "WWGGGGGGGG.",
                      "WWWWGGGGG..",
                      "nWWWW......",
                      ".WWW......."],
           {"G": (PEARL, 0.667), "W": (PEARL, 0.0), "i": (EMBER, 0.0), "d": (UMBER, 1.0), "m": (UMBER, 1.0),
            "k": (UMBER, 1.0), "n": (UMBER, 1.0)})
    # toadstools and ferns among the roots
    for (mx, my, s) in ((4.5, 42.0, 1.0), (8.0, 44.2, 0.8), (35.0, 43.4, 0.9), (38.0, 41.0, 1.1)):
        c.paint(rect(c, mx - 0.5 * s, my - 0.4, mx + 0.5 * s, my + 1.5 * s), PEARL, 0.0, 1.5)
        c.paint(ellipse(c, mx, my, 1.9 * s, 1.2 * s) & (Y < my + 0.1), EMBER, 0.333, 1.55)
    for (base, ctrl, tip) in (((3.0, 45.5), (2.0, 39.0), (1.5, 34.5)), ((3.5, 45.5), (5.5, 40.5), (9.5, 38.5)),
                              ((39.0, 45.5), (40.0, 39.0), (40.5, 34.5)), ((38.5, 45.5), (36.5, 40.5), (32.5, 38.5))):
        frond(c, base, ctrl, tip)
    # fairies in the air and fireflies
    for (fx, fy, s) in ((10.0, 12.5, 1.0), (21.5, 19.0, 1.0), (33.0, 23.0, 0.95), (27.5, 17.0, 0.85)):
        fairy(c, fx, fy, s)
    for _ in range(16):
        fx, fy = r.randrange(5, 37) + 0.5, r.randrange(11, 27) + 0.5
        if not (5 < fx < 18 and fy > 17):
            c.paint(c.circle(fx, fy, 0.42), SAFFRON, 0.0, 1.45)
    frame(c)
    return encode(c.to_tiles())


def cleopatra():
    """Antony and Cleopatra, II.ii: "The barge she sat in, like a burnish'd throne, burn'd on the
    water": the golden barge with its purple sails and silver oars, the queen enthroned under her
    canopy, the river at sunset with palms on the far bank."""
    c = Canvas(48, 36)
    X, Y = c.X, c.Y
    tx, ty = tiles(c)
    hz = 14.0
    # sunset sky in bands: blue, rose, pale gold at the horizon; the low sun on the left
    wav = 0.6 * np.sin(X * 0.35)
    c.paint(ALL(c), LAPIS, np.where(Y < 3.5 + wav, 0.667, 0.333))
    c.paint(Y > 7.5 + wav, EMBER, 0.0)
    c.paint(Y > 11.0 - wav, SAFFRON, 0.0)
    c.paint(c.circle(3.8, hz, 3.2) & (Y < hz), SAFFRON, 0.667, 1.3)
    # the far bank, a dark line of trees, and two palms on the right
    c.paint(Y > hz - 1.0 + 0.4 * np.sin(X * 0.8) + 0.5 * np.sin(X * 2.1), FERN, 1.0)
    for (bx, h, lean) in ((42.8, 8.5, -0.6), (45.6, 6.5, 0.5)):
        top = (bx + lean, hz - 1 - h)
        c.paint(tube(c, [(bx, hz - 0.5), (bx + lean * 0.4, hz - 1 - h * 0.5), top], 0.9, 0.7), UMBER, 0.667, 1.3)
        for a in (-2.7, -2.1, -1.3, -0.6, 0.1):
            ex, ey = top[0] + 3.2 * math.cos(a), top[1] + 3.2 * math.sin(a) + 1.6
            c.paint(c.line_mask(bezier(top, (top[0] + 2.0 * math.cos(a), top[1] - 1.2), (ex, ey), 8), 0.8), FERN, 1.0, 1.35)
    # the river, with the sun's broken reflection and the barge's gold and purple reflections
    water = Y >= hz
    c.paint(water, LAPIS, np.where(np.sin(Y * 2.4 + np.sin(X * 0.5)) > 0.4, 0.667, 0.333))
    for k, yy in enumerate((15, 18, 21, 24)):
        c.paint(water & (ty == yy) & (np.abs(X - 3.8 - (0.7 if k % 2 else -0.5)) < 1.6 + 0.4 * k), SAFFRON, 0.0, 1.2)
    for (x0, x1, yy, fam) in ((14, 21, 33, SAFFRON), (24, 32, 33, EMBER), (17, 27, 34, SAFFRON)):
        c.paint(water & (ty == yy) & (X >= x0) & (X < x1), fam, 0.667, 1.2)
    # the mast, gilded yards and the purple (deep red and brown) striped sail
    c.paint(c.line_mask([(18.0, 22), (18.0, 3)], 0.75), UMBER, 1.0, 1.4)
    sail = c.poly_mask([(11.2, 4.4), (24.8, 4.4), (24.0, 17.6), (12.0, 17.6)])
    c.paint(sail, EMBER, np.where(X > 18.0, 1.0, 0.667), 1.3)
    c.paint(sail & (ty % 3 == 1), UMBER, 0.667, 1.35)
    c.paint(c.line_mask([(10.4, 3.9), (25.6, 3.9)], 0.7) | c.line_mask([(11.6, 18), (24.4, 18)], 0.6), SAFFRON, 0.667, 1.45)
    # the canopy and burnished throne at the stern, the queen in white with a golden crown
    c.paint(rect(c, 28.6, 13.6, 33.4, 21.5), SAFFRON, 0.0, 1.35)
    for px in (26.8, 35.2):
        c.paint(c.line_mask([(px, 12.4), (px, 21.4)], 0.6), SAFFRON, 0.667, 1.5)
    roof = c.poly_mask([(25.8, 13.2), (36.2, 13.2), (34.8, 10.4), (27.2, 10.4)])
    c.paint(roof, EMBER, 0.333, 1.45)
    c.paint(roof & ((tx // 2) % 2 == 0), PEARL, 0.0, 1.5)
    c.paint(c.circle(31.0, 15.4, 1.5) | rect(c, 29.5, 15.4, 32.5, 17.4), UMBER, 1.0, 1.55)
    c.paint(c.circle(31.0, 15.9, 0.95), EMBER, 0.0, 1.65)
    c.paint(rect(c, 29.6, 13.6, 32.4, 14.6), SAFFRON, 0.333, 1.7)
    c.paint(c.poly_mask([(30.0, 17.3), (32.0, 17.3), (33.0, 21.5), (29.0, 21.5)]), PEARL, 0.0, 1.6)
    # the hull: lotus prow and stern, gilded body, a painted band, silver oars
    hull = c.poly_mask([(7.6, 12.8), (9.0, 13.4), (10.2, 17.2), (11.8, 21.2), (35.6, 21.2), (38.0, 17.6), (39.4, 14.2),
                        (40.8, 13.2), (40.3, 15.6), (39.0, 20.2), (36.4, 24.6), (33.6, 26.4), (14.6, 26.4),
                        (11.8, 25), (9.4, 20.4), (8.2, 15.4)])
    c.paint(hull, SAFFRON, np.where(Y > 24.4, 0.667, 0.333), 1.4)
    c.paint(c.circle(8.0, 12.6, 1.1) | c.circle(40.6, 12.8, 1.1), SAFFRON, 0.0, 1.5)
    c.paint(c.line_mask([(11.0, 21.6), (37.4, 21.6)], 0.6), UMBER, 1.0, 1.5)
    band = hull & (ty == 23) & (tx >= 12) & (tx <= 35)
    c.paint(band & (tx % 3 == 0), EMBER, 0.333, 1.55)
    c.paint(band & (tx % 3 == 1), LAPIS, 0.667, 1.55)
    for i in range(8):
        x0 = 14.5 + 2.7 * i
        c.paint(c.line_mask([(x0, 24.6), (x0 - 2.4, 30.6)], 0.7) | ellipse(c, x0 - 2.6, 31.2, 0.6, 1.1, 0.4), PEARL, 0.0, 1.6)
    frame(c)
    return encode(c.to_tiles())


# ---------------------------------------------------------------------------
# master
# ---------------------------------------------------------------------------

def table(seed, n, choices):
    r = random.Random(seed)
    return [choices[r.randrange(len(choices))] for _ in range(n)]


def people(c, region, cell_w, seed, choices, stagger=1):
    """Fill `region` with a tile-aligned crowd: per cell of `cell_w` x 2 tiles (rows staggered), a pale
    head at the top left and three tiles of hat and clothes in a colour picked from `choices`."""
    tx, ty = tiles(c)
    band = ty // 2
    u = tx + band * stagger
    k = (u // cell_w) * 7 + band * 31
    pos, top = u % cell_w, (ty % 2 == 0)
    picks = table(seed, 997, choices)
    for fam, sh in set(choices):
        sel = np.isin(k % 997, [j for j, cc in enumerate(picks) if cc == (fam, sh)])
        c.paint(region & (pos < 2) & sel, fam, sh, 1.05)
    c.paint(region & (pos == 0) & top, EMBER, 0.0, 1.1)


def gallery_tiers(c, gal, f, posts):
    """The Globe's galleries: three tiers, each a dark rail row over a row of heads and hats and two rows
    of clothes in 2-tile cells; `f` runs from 0 at the top of the band to 1 at the yard."""
    tx, ty = tiles(c)
    tier = np.clip(np.floor(f * 3), 0, 2).astype(int)
    row = np.clip(np.floor((f * 3 - tier) * 4), 0, 3).astype(int)
    clothes = table(7, 997, [(LAPIS, 0.667), (EMBER, 0.667), (FERN, 0.667), (PEARL, 0.333), (SAFFRON, 0.667)])
    k = (tx // 2 + 5 * tier) % 997
    for fam, sh in set(clothes):
        sel = np.isin(k, [j for j, cc in enumerate(clothes) if cc == (fam, sh)])
        c.paint(gal & ((row >= 2) | ((row == 1) & (tx % 2 == 1))) & sel, fam, sh)
    c.paint(gal & (row == 1) & (tx % 2 == 0), EMBER, 0.0)
    c.paint(gal & ((row == 0) | posts), UMBER, 1.0, 1.2)


def globe():
    """The Globe playhouse, 1599: the round timber-framed theatre seen from above, its thatched roof
    ring, three galleries of spectators, the stage under its painted heavens, groundlings in the yard,
    the flag flying over the hut; the Thames beyond and Bankside houses in front."""
    c = Canvas(44, 44)
    X, Y = c.X, c.Y
    tx, ty = tiles(c)
    XC, YC = tx + 0.5, ty + 0.5
    cx, cy = 22.0, 20.0
    RO, RYO, RI, RYI, DROP, WALL = 21.0, 13.0, 17.2, 10.6, 12.0, 8.0
    crowd = [(LAPIS, 0.333), (FERN, 0.667), (SAFFRON, 0.333), (PEARL, 0.0), (EMBER, 0.667), (LAPIS, 0.667), (UMBER, 1.0)]
    # Bankside: grass, the Thames with ripples and two wherries along the top, houses in front
    c.paint(ALL(c), FERN, np.where(smooth_noise(c, 3, 0.8) > 0.2, 0.333, 0.667))
    river = Y < 6.5 + 0.8 * np.sin(X * 0.3)
    c.paint(river, LAPIS, 0.333)
    c.paint(river & ((tx * 3 + ty * 5) % 7 == 0) & (ty % 2 == 1), PEARL, 0.0, 1.2)
    for (bx, by) in ((5.5, 3.0), (36.5, 2.5)):
        c.paint(ellipse(c, bx, by, 2.6, 0.9), UMBER, 0.667, 1.3)
    for (hx, w) in ((0.0, 7.0), (37.0, 7.0)):
        c.paint(rect(c, hx, 36.5, hx + w, 44), PEARL, 0.333, 1.2)
        c.paint(c.poly_mask([(hx - 0.5, 36.6), (hx + w + 0.5, 36.6), (hx + w / 2, 33.5)]), EMBER, 0.667, 1.25)
        c.paint(rect(c, hx + w / 2 - 0.5, 38.0, hx + w / 2 + 0.5, 40.0), UMBER, 1.0, 1.3)
    # the outer wall: whitewashed plaster in a timber frame over a brick plinth
    dxo = np.clip((X - cx) / RO, -1, 1)
    yo = cy + RYO * np.sqrt(1 - dxo ** 2)
    wall = (np.abs(X - cx) < RO) & (Y >= cy) & (Y < yo + WALL)
    q = (Y - yo) / WALL
    c.paint(wall, PEARL, np.where(X > cx + 8, 0.333, 0.0))
    angs = [math.pi / 20 + 2 * math.pi * k / 20 for k in range(20)]
    posts = np.zeros_like(wall)
    for a in angs:
        if math.sin(a) > 0:
            posts |= np.abs(X - (cx + RO * math.cos(a))) < 0.5
    rails = (np.abs(q - 0.42) < 0.06) | (np.abs(q - 0.08) < 0.07)
    c.paint(wall & (posts | rails), UMBER, 0.667, 1.3)
    c.paint(wall & (q > 0.8), EMBER, np.where((tx + ty) % 2 == 0, 0.667, 1.0), 1.3)
    c.paint(wall & (np.abs(X - cx) < 1.6) & (q > 0.5), UMBER, 1.0, 1.4)
    # the thatched roof ring: twenty bays, ridges at the corners
    outer, inner = ellipse(c, cx, cy, RO, RYO), ellipse(c, cx, cy, RI, RYI)
    ring = outer & ~inner
    ang = np.arctan2((Y - cy) / RYO, (X - cx) / RO)
    bay = np.floor((ang - math.pi / 20) / (2 * math.pi / 20)).astype(int)
    c.paint(ring, SAFFRON, np.where(bay % 2 == 0, 0.333, 0.667))
    for a in angs:
        p0 = (cx + RI * math.cos(a), cy + RYI * math.sin(a))
        p1 = (cx + RO * math.cos(a), cy + RYO * math.sin(a))
        c.paint(c.line_mask([p0, p1], 0.55) & ring, UMBER, 0.667, 1.3)
    # the galleries on the far side, split into bays by posts
    floor = ellipse(c, cx, cy + DROP, RI, RYI)
    gal = inner & ~floor
    dxi = np.clip((XC - cx) / RI, -1, 1)
    f = (YC - (cy - RYI * np.sqrt(1 - dxi ** 2))) / DROP
    gposts = np.zeros_like(gal)
    for a in angs:
        if math.sin(a) < 0:
            gposts |= np.abs(X - (cx + RI * math.cos(a))) < 0.5
    gallery_tiers(c, gal, f, gposts)
    # the yard, packed with groundlings
    yard = inner & floor
    c.paint(yard, UMBER, 0.333)
    people(c, yard, 2, 11, crowd[:6], stagger=1)
    # the tiring house behind the stage: a wide curtained middle between two narrow doors
    front = rect(c, 16.5, 9.0, 27.5, 22.0) & gal
    c.paint(front, PEARL, 0.0, 1.3)
    for (x0, x1, fam, sh) in ((18.0, 19.0, UMBER, 0.667), (19.6, 24.4, EMBER, 0.333), (25.0, 26.0, UMBER, 0.667)):
        c.paint(rect(c, x0, 18.0, x1, 22.0) & front, fam, sh, 1.35)
    # the stage: planks, its dark front, two players
    stage = c.poly_mask([(17.0, 21.2), (27.0, 21.2), (28.0, 26.0), (16.0, 26.0)])
    c.paint(stage, SAFFRON, np.where(ty % 2 == 0, 0.667, 1.0), 1.4)
    c.paint(rect(c, 16.0, 26.0, 28.0, 27.4), UMBER, 1.0, 1.4)
    for (px, fam) in ((19.5, LAPIS), (24.5, EMBER)):
        c.paint(rect(c, px - 0.5, 23.0, px + 0.5, 25.0) | rect(c, px - 1.0, 23.4, px + 1.0, 24.6), fam, 0.667, 1.6)
        c.paint(rect(c, px - 0.5, 22.0, px + 0.5, 23.0), EMBER if fam != EMBER else PEARL, 0.0, 1.65)
    # the heavens: two marbled pillars, a pediment painted blue with golden stars, its tiled roof
    for px in (17.0, 27.0):
        c.paint(rect(c, px - 0.5, 17.0, px + 0.5, 26.0), PEARL, 0.333, 1.5)
    c.paint(c.poly_mask([(15.6, 13.2), (22.0, 7.4), (28.4, 13.2), (28.4, 15.0), (22.0, 9.6), (15.6, 15.0)]), EMBER, 0.667, 1.45)
    ped = c.poly_mask([(16.0, 17.0), (28.0, 17.0), (28.0, 15.0), (22.0, 9.8), (16.0, 15.0)])
    c.paint(ped, LAPIS, 1.0, 1.5)
    for (sx, sy) in ((21, 12), (19, 15), (24, 14), (22, 16)):
        c.paint((tx == sx) & (ty == sy), SAFFRON, 0.0, 1.6)
    c.paint(rect(c, 15.6, 16.8, 28.4, 17.8), SAFFRON, 0.333, 1.55)
    # the hut on the roof and the flag
    c.paint(rect(c, 19.0, 3.6, 25.0, 7.8), PEARL, 0.333, 1.4)
    c.paint(c.poly_mask([(18.4, 4.0), (25.6, 4.0), (22.0, 1.8)]), EMBER, 1.0, 1.45)
    c.paint(c.line_mask([(22.0, 2.0), (22.0, 0.4)], 0.5), UMBER, 1.0, 1.5)
    c.paint(c.poly_mask([(22.2, 0.6), (27.0, 0.8), (26.0, 1.9), (27.0, 3.0), (22.2, 2.8)]), EMBER, 0.333, 1.55)
    frame(c)
    return encode(c.to_tiles())


CASKET = ["...XXX...",
          ".XXXXXxx.",
          "XXXXXXXxx",
          "TTTTTTTTT",
          "XXXXLXXxx",
          "XXXXLXXxx",
          "XXXXXXXxx",
          "TTTTTTTTT"]


def casket(c, x0, y0, fam, sh, trim, tsh):
    """A domed casket (tile sprite, 9 x 8): lit body, shaded right side, a trim band, a lock, a plinth."""
    sprite(c, x0, y0, CASKET, {"X": (fam, sh), "x": (fam, min(1.0, sh + 0.333)), "T": (trim, tsh), "L": (trim, tsh)})


def caskets():
    """The Merchant of Venice, III.ii: the choice of the three caskets - gold, silver and lead - on a
    patterned carpet in Portia's marble hall at Belmont: columns, Gothic Venetian windows, a
    chequered marble floor."""
    c = Canvas(42, 44)
    X, Y = c.X, c.Y
    tx, ty = tiles(c)
    # green damask wall with a gold lattice
    c.paint(ALL(c), FERN, 0.667)
    c.paint(((tx + ty) % 4 == 0) | ((tx - ty) % 4 == 0), SAFFRON, 0.333, 1.05)
    c.paint(((tx + ty) % 4 == 2) & ((tx - ty) % 4 == 2), EMBER, 0.333, 1.05)
    # three Venetian Gothic windows: white stone frames, two pointed lights each and a roundel
    for wx in (7.5, 21.0, 34.5):
        def arch(hw, bottom, lift, x0=wx):
            top = c.circle(x0 + hw / 2, 9.0, hw * 1.5 + lift) & c.circle(x0 - hw / 2, 9.0, hw * 1.5 + lift) & (Y < 9.0)
            return top | rect(c, x0 - hw - lift, 9.0, x0 + hw + lift, bottom)
        c.paint(arch(2.9, 20.0, 1.0), PEARL, 0.0, 1.2)
        c.paint(arch(2.9, 19.0, 0.0), PEARL, 0.333, 1.25)
        for side in (-1, 1):
            light = arch(1.0, 19.0, 0.0, wx + side * (1.5 if wx != 21.0 else 1.75)) & (Y > 8.2)
            c.paint(light, LAPIS, np.where(Y < 15, 0.0, 0.333), 1.3)
        c.paint(c.circle(wx, 6.4, 1.1), EMBER, 0.333, 1.35)
    # marble columns with gilded capitals and bases, a cornice and a skirting
    c.paint(rect(c, 0, 0, 42, 2.0), PEARL, 0.333, 1.3)
    c.paint(rect(c, 0, 1.0, 42, 2.0) & (tx % 2 == 0), SAFFRON, 0.333, 1.35)
    for colx in (1.0, 14.25, 27.75, 41.0):
        shaft = rect(c, colx - 1.3, 2.0, colx + 1.3, 22.0)
        c.paint(shaft, PEARL, np.where(tx % 2 == 0, 0.0, 0.333), 1.4)
        c.paint(rect(c, colx - 1.8, 2.0, colx + 1.8, 4.0) | rect(c, colx - 1.8, 20.0, colx + 1.8, 22.0), SAFFRON, 0.333, 1.45)
    c.paint(rect(c, 0, 21.5, 42, 23.0), PEARL, 0.667, 1.3)
    # the chequered floor, its rows widening toward us
    fy = Y >= 23.0
    d = Y + 10.0
    chk = (np.floor((X - 21.0) * 10.0 / d) + np.floor(500.0 / d)).astype(int) % 2
    c.paint(fy, PEARL, 0.0)
    c.paint(fy & (chk == 1), UMBER, 1.0, 1.05)
    # the carpet: a blue border and gold line round a red field with a row of medallions
    c.paint(c.poly_mask([(4.5, 27.6), (37.5, 27.6), (43.0, 45), (-1.0, 45)]), LAPIS, 1.0, 1.2)
    field = c.poly_mask([(5.8, 28.6), (36.2, 28.6), (41.0, 45), (1.0, 45)])
    c.paint(field, EMBER, 0.667, 1.25)
    c.paint(field & ~c.poly_mask([(6.8, 29.6), (35.2, 29.6), (39.8, 45), (2.2, 45)]), SAFFRON, 0.0, 1.27)
    for i, mx in enumerate((4.5, 10.0, 15.5, 21.0, 26.5, 32.0, 37.5)):
        my = 41.0
        dia = (np.abs(X - mx) + np.abs(Y - my) * 1.1) < 2.6
        c.paint(dia & field, SAFFRON if i % 2 == 0 else FERN, 0.333, 1.3)
        c.paint(c.circle(mx, my, 0.7) & field, PEARL, 0.0, 1.35)
    # the three caskets: gold, silver and lead
    casket(c, 6, 31, SAFFRON, 0.0, UMBER, 1.0)
    casket(c, 17, 31, PEARL, 0.0, LAPIS, 0.667)
    casket(c, 28, 31, PEARL, 0.667, UMBER, 0.667)
    frame(c)
    return encode(c.to_tiles())


SCENES = {
    "balcony": balcony,
    "yorick": yorick,
    "witches": witches,
    "tempest": tempest,
    "fairywood": fairywood,
    "cleopatra": cleopatra,
    "globe": globe,
    "caskets": caskets,
}
