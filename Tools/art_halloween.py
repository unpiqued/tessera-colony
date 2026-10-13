"""Halloween pack: eight cosy-spooky seasonal pictures, drawn with the supersampled Canvas of art.py (a
tile's colour family comes from the dominant object under it, its tone from the shading). Family friendly:
pumpkins, cats, smiling ghosts and a creaky house; no gore, no protected characters, no lettering.

Gentle: the jack-o'-lantern, the black cat on the fence, the scarecrow, the friendly ghosts.
Challenge: the haunted house on the hill, the pumpkin patch.
Master (busy, every colour in many islands): the spider's web, trick-or-treat street.
"""
import math
import random

import numpy as np

from art import Canvas, LAPIS, SAFFRON, FERN, EMBER, UMBER, PEARL, SS, encode, leaf
from art_scenes import ALL, ellipse, rect, tube, frame, smooth_noise

T0, T1, T2, T3 = 0.0, 0.33, 0.67, 1.0          # the four flat tones (no dither speckle)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def sprite(c, x0, y0, rows, fam, shade, prio=1.7):
    """Paint a tile-exact pixel sprite ('#' = filled) with its top-left tile at (x0, y0)."""
    m = np.zeros_like(c.X, bool)
    for j, row in enumerate(rows):
        for i, ch in enumerate(row):
            if ch == '#':
                m |= rect(c, x0 + i, y0 + j, x0 + i + 1, y0 + j + 1)
    c.paint(m, fam, shade, prio)


def stars(c, pts):
    for (sx, sy) in pts:
        c.paint(rect(c, sx, sy, sx + 1, sy + 1), PEARL, T0, 1.6)


def pumpkin(c, x, y, rx, ry, fam=EMBER, stem=True, prio=1.3):
    """A small ribbed pumpkin: lighter middle lobe, darker side lobes, a green stem."""
    c.paint(ellipse(c, x, y, rx, ry), fam, T2, prio)
    c.paint(ellipse(c, x, y, rx * 0.45, ry * 0.97), fam, T1, prio + 0.02)
    if rx > 2.2:
        c.paint(ellipse(c, x, y, rx * 0.45, ry * 0.97) & (c.X < x - 0.2) & (c.Y < y - 0.2), fam, T0, prio + 0.03)
    if stem:
        c.paint(rect(c, x - 0.45, y - ry - 0.9, x + 0.55, y - ry + 0.4), FERN, T3, prio + 0.1)


def autumn_leaf(c, lx, ly, a, fam, tone, s=1.0, prio=1.7):
    """A small three-lobed autumn leaf pointing along angle a, with a darker midrib."""
    ca, sa = math.cos(a), math.sin(a)
    m = (ellipse(c, lx, ly, 2.6 * s, 1.7 * s, a)
         | ellipse(c, lx + (0.6 * ca - 1.0 * sa) * s, ly + (1.0 * ca + 0.6 * sa) * s, 1.5 * s, 1.1 * s, a + 1.0)
         | ellipse(c, lx + (0.6 * ca + 1.0 * sa) * s, ly + (0.6 * sa - 1.0 * ca) * s, 1.5 * s, 1.1 * s, a - 1.0))
    c.paint(m, fam, tone, prio)
    rib = c.line_mask([(lx - 2.6 * s * ca, ly - 2.6 * s * sa), (lx + 1.8 * s * ca, ly + 1.8 * s * sa)], 0.4)
    c.paint(rib & m, fam, min(1.0, tone + 0.34), prio + 0.02)


# a bat with spread wings (9 x 5 tiles), a small far-off one (5 x 3) and a bird in flight (9 x 3)
BAT = ["#.......#", "##.#.#.##", ".#######.", "..##.##..", "....#...."]
SMALL_BAT = ["#...#", "##.##", "..#.."]
BIRD = ["##.....##", "..##.##..", "....#...."]


# ---------------------------------------------------------------------------
# Gentle
# ---------------------------------------------------------------------------

def jackolantern():
    """A big carved pumpkin, close up on the porch at night with a little one beside it: five ribbed lobes,
    a curly green stem with a leafy vine, triangle eyes, a triangle nose and a toothy grin glowing yellow
    from the candle inside."""
    c = Canvas(44, 40)
    X, Y = c.X, c.Y
    cx, cy = 19.5, 22.6
    c.paint(ALL(c), LAPIS, T3)
    stars(c, ((40, 3), (13, 2), (41, 15), (16, 6), (40, 25)))
    c.paint(rect(c, 37, 7, 40, 8) | rect(c, 38, 6, 39, 9), PEARL, T0, 1.6)         # a twinkling star
    # the house wall behind at the left: clapboards and a lit window
    tx, ty = np.floor(X).astype(int), np.floor(Y).astype(int)
    c.paint(X < 12.0, UMBER, np.where(ty % 2 == 0, T2, T3), 1.05)
    c.paint(rect(c, 2, 3, 11, 14), PEARL, T1, 1.1)
    c.paint(rect(c, 3, 4, 10, 13) & (tx != 6) & (ty != 8), SAFFRON, np.where(ty < 8, T1, T0), 1.15)
    # porch boards and the warm light the lantern spills on them
    porch = Y > 35.0
    c.paint(porch, UMBER, np.where(ty % 2 == 0, T1, T2), 1.1)
    c.paint(porch & ellipse(c, cx, 37.6, 12.0, 2.2), UMBER, T0, 1.12)
    # the lobes, outer ones first: each lighter down its middle, a dark groove round its edge
    lobes = ((cx - 12.2, 23.6, 5.2, 9.8, T2), (cx + 12.2, 23.6, 5.2, 9.8, T2),
             (cx - 7.0, 23.0, 6.8, 11.2, T1), (cx + 7.0, 23.0, 6.8, 11.2, T1), (cx, 22.6, 7.2, 12.0, T1))
    for (lx, ly, rx, ry, tone) in lobes:
        c.paint(ellipse(c, lx, ly, rx, ry), EMBER, T3, 1.2)
        inner = ellipse(c, lx, ly, rx - 0.9, ry - 0.7)
        c.paint(inner, EMBER, np.where(np.abs(X - lx) < rx * 0.45, tone, min(1.0, tone + 0.34)), 1.2)
    c.paint(ellipse(c, cx - 3.4, 14.8, 1.5, 2.4, 0.3), EMBER, T0, 1.25)       # a gleam on the top
    # the carved face, glowing pale yellow; the cut flesh shows deeper gold along the bottom of the grin
    eyes = (c.poly_mask([(cx - 10.4, 19.8), (cx - 3.2, 19.8), (cx - 6.6, 13.6)])
            | c.poly_mask([(cx + 3.2, 19.8), (cx + 10.4, 19.8), (cx + 6.6, 13.6)]))
    nose = c.poly_mask([(cx - 2.0, 23.0), (cx + 2.0, 23.0), (cx, 20.2)])
    u = (X - cx) / 11.6
    top = 26.0 - 3.4 * u * u
    bot = 23.2 + 7.4 * np.clip(1 - u * u, 0, 1) ** 0.7
    mouth = (np.abs(u) < 1) & (Y > top) & (Y < bot)
    teeth = rect(c, cx - 6.2, 23, cx - 3.4, 27.6) | rect(c, cx + 3.4, 23, cx + 6.2, 27.6) | rect(c, cx - 1.4, 28.6, cx + 1.4, 32)
    c.paint(eyes | nose | (mouth & ~teeth), SAFFRON, T0, 1.5)
    c.paint(mouth & ~teeth & ~np.roll(mouth, -SS, axis=0), SAFFRON, T2, 1.55)
    # a little pumpkin beside it
    c.paint(ellipse(c, 38.0, 32.6, 3.9, 3.0), EMBER, T2, 1.3)
    c.paint(ellipse(c, 38.0, 32.6, 1.8, 2.9), EMBER, T1, 1.32)
    c.paint(tube(c, [(38.0, 30.0), (38.4, 28.4), (39.6, 27.8)], 1.4, 0.9), FERN, T2, 1.35)
    # the curly stem with a leaf, and a vine with a leaf and a curling tendril off to the right
    c.paint(tube(c, [(cx + 0.2, 12.0), (cx + 0.4, 8.6), (cx + 2.0, 6.4), (cx + 4.2, 5.8), (cx + 5.0, 7.2)], 3.4, 1.6),
            FERN, T2, 1.5)
    c.paint(tube(c, [(cx + 2.0, 10.6), (cx + 6.0, 8.0), (cx + 10.0, 7.6), (cx + 13.0, 5.6)], 1.0, 0.8), FERN, T3, 1.45)
    pts = [(cx + 13.0 - math.cos(a) * (2.4 - 0.2 * a), 3.8 + math.sin(a) * (2.4 - 0.2 * a)) for a in np.arange(1.6, 8.0, 0.3)]
    c.paint(tube(c, pts, 0.9, 0.7), FERN, T3, 1.45)
    leaf(c, cx + 7.0, 8.0, cx + 10.6, 2.0, 3.4, bend=-0.2)
    leaf(c, cx - 1.6, 11.4, cx - 10.6, 9.0, 4.0, bend=0.15)
    frame(c)
    return encode(c.to_tiles())


def blackcat():
    """A black cat with its back arched and tail up, standing on a board fence against a huge harvest
    moon; bats flit across the night sky, pumpkins sit in the grass below."""
    c = Canvas(46, 40)
    X, Y = c.X, c.Y
    mx, my, mr = 27.0, 16.0, 12.6
    d = np.hypot(X - mx, Y - my)
    c.paint(ALL(c), LAPIS, np.where(d < mr + 2.4, T2, T3))
    stars(c, ((3, 3), (8, 12), (5, 21), (12, 4), (43, 22), (42, 4), (16, 18)))
    # the harvest moon with soft darker seas
    moon = d < mr
    c.paint(moon, SAFFRON, T0, 1.1)
    c.paint(moon & (smooth_noise(c, 6, 0.55) > 0.32), SAFFRON, T1, 1.12)
    # the fence: a cap rail, boards with dark gaps (sky between), a lower rail, posts
    tx = np.floor(X).astype(int)
    boards = rect(c, 0, 27, 46, 34) & (tx % 4 != 3)
    c.paint(boards, UMBER, np.where(tx % 8 < 4, T1, T2), 1.1)
    c.paint(rect(c, 0, 25.6, 46, 27.2), UMBER, T1, 1.2)
    c.paint(rect(c, 0, 31.0, 46, 32.2), UMBER, T2, 1.2)
    for px in (6.5, 39.5):
        c.paint(rect(c, px - 1.0, 24.6, px + 1.0, 34), UMBER, T2, 1.25)
    # grass and three pumpkins in front of the fence
    grass = Y > 34.0 + 0.6 * np.sin(X * 1.7) - 1.2 * (np.sin(X * 2.9) > 0.75)
    c.paint(grass, FERN, np.where(np.sin(X * 1.1 + Y) > 0.3, T2, T3))
    pumpkin(c, 7.0, 35.6, 3.0, 2.2)
    pumpkin(c, 12.2, 36.6, 2.2, 1.6)
    pumpkin(c, 37.5, 36.0, 2.6, 1.9)
    # the cat, facing left: arched back, stiff legs, head low, ears up, tail raised with a hooked tip
    cat = (tube(c, [(20.4, 22.0), (21.4, 18.0), (24.6, 14.8), (28.4, 15.6), (30.6, 19.0), (30.8, 22.2)], 4.8, 4.4)
           | tube(c, [(20.2, 21.0), (19.2, 25.8)], 1.6, 1.4) | tube(c, [(22.0, 21.0), (22.2, 25.8)], 1.5, 1.4)
           | tube(c, [(30.4, 21.0), (31.6, 25.8)], 1.7, 1.4) | tube(c, [(28.6, 21.0), (28.8, 25.8)], 1.5, 1.4)
           | c.circle(17.8, 17.0, 3.2) | ellipse(c, 15.0, 18.4, 1.8, 1.4)
           | c.poly_mask([(14.8, 16.2), (14.4, 11.0), (17.8, 14.2)]) | c.poly_mask([(17.6, 14.0), (20.0, 10.6), (20.8, 15.6)])
           | tube(c, [(30.6, 18.4), (33.2, 14.8), (33.6, 10.6), (32.2, 7.6), (33.8, 5.6), (35.8, 6.2)], 2.0, 1.4))
    c.paint(cat, UMBER, T3, 1.6)
    c.paint(c.circle(16.5, 16.5, 0.6), FERN, T0, 2.0)                         # a green eye
    # bats
    for (bx, by) in ((3, 6), (10, 9), (21, 5), (38, 9)):
        sprite(c, bx, by, BAT, UMBER, T3)
    frame(c)
    return encode(c.to_tiles())


def scarecrow():
    """A straw-stuffed scarecrow in a golden cornfield under an autumn sky: patched floppy hat, sacking
    face with button eyes and a stitched smile, checked shirt, arms out on the crossbar with straw at
    the cuffs, and two crows perched on the arms."""
    c = Canvas(42, 44)
    X, Y = c.X, c.Y
    tx, ty = np.floor(X).astype(int), np.floor(Y).astype(int)
    cx = 21.0
    c.paint(ALL(c), LAPIS, np.where(Y < 12, T1, T0))
    for (a, b, k) in ((7, 5.5, 1.0), (34, 9.5, 0.8)):
        c.paint(c.circle(a - 2.4 * k, b + 0.6, 1.8 * k) | c.circle(a, b, 2.5 * k) | c.circle(a + 2.5 * k, b + 0.7, 1.7 * k),
                PEARL, T0, 1.1)
    # a dark hedge on the horizon, then the cornfield: stalks, leaves and tassels
    c.paint(Y > 28.0 + 0.9 * np.sin(X * 0.8) + 0.5 * np.sin(X * 2.1), FERN, T3)
    field = Y > 31.0 + 0.8 * np.sin(X * 1.9)
    stalk = (tx % 3 == 0)
    c.paint(field, SAFFRON, np.where(stalk, T3, np.where((tx + ty) % 4 < 2, T1, T2)))
    for k in range(14):
        x0 = 1.5 + k * 3.0
        c.paint(c.line_mask([(x0, 32.4 + (k % 3)), (x0 + 0.4, 29.6 + (k % 2))], 0.7), SAFFRON, T1, 1.1)
    # the post behind
    c.paint(rect(c, cx - 0.8, 26, cx + 0.8, 34), UMBER, T2, 1.0)
    # the shirt: arms out along the crossbar, red check (all one colour family)
    shirt = c.poly_mask([(4.0, 16.4), (38.0, 16.4), (38.4, 21.0), (26.0, 21.6), (25.4, 27.6), (16.6, 27.6),
                         (16.0, 21.6), (3.6, 21.0)])
    check = np.where((tx % 4 == 1) & (ty % 4 == 1), T3, np.where((tx % 4 == 1) | (ty % 4 == 1), T2, T1))
    c.paint(shirt, EMBER, check, 1.2)
    c.paint(rect(c, 29.0, 17.4, 31.6, 20.0), LAPIS, T1, 1.3)                    # a patch on the sleeve
    # straw bursting from the cuffs
    for side in (-1, 1):
        x0 = cx + side * 17.2
        for (dx, dy) in ((2.2, -2.4), (2.8, -0.4), (2.6, 1.8), (1.6, 3.4)):
            c.paint(tube(c, [(x0, 18.8), (x0 + side * dx, 18.8 + dy)], 1.0, 0.6), SAFFRON, T0, 1.3)
    # trousers with a patched knee and a rope belt
    trousers = c.poly_mask([(16.6, 27.4), (25.4, 27.4), (25.8, 36), (21.6, 36), (21.0, 31), (20.4, 36), (16.2, 36)])
    c.paint(trousers, LAPIS, T2, 1.2)
    c.paint(rect(c, 22.4, 31.6, 24.6, 33.6), SAFFRON, T2, 1.3)
    c.paint(rect(c, 16.4, 26.8, 25.6, 27.8), UMBER, T1, 1.3)
    c.paint(field & (Y > 35.0) & (tx % 3 == 0), SAFFRON, T3, 1.4)              # stalks in front
    # the sacking head, rope at the neck, straw hair, face
    c.paint(ellipse(c, cx, 12.4, 4.4, 4.8), PEARL, np.where(X > cx + 2.6, T3, T2), 1.3)
    c.paint(rect(c, cx - 2.2, 16.6, cx + 2.2, 17.4), UMBER, T1, 1.35)
    for (dx, dy) in ((-4.6, 1.8), (-5.2, 0.0), (4.6, 1.8), (5.2, 0.0)):
        c.paint(tube(c, [(cx + dx * 0.7, 10.2), (cx + dx, 10.2 + dy)], 1.0, 0.6), SAFFRON, T0, 1.35)
    for side in (-1, 1):
        c.paint(c.circle(cx + side * 2.0, 12.0, 1.0), UMBER, T3, 1.6)
        c.paint(rect(c, math.floor(cx + side * 2.0) - 1, 11, math.floor(cx + side * 2.0), 12), PEARL, T0, 1.65)
        c.paint(c.circle(cx + side * 3.0, 13.8, 0.75), EMBER, T0, 1.55)
    c.paint(c.poly_mask([(cx - 1.1, 14.2), (cx + 1.1, 14.2), (cx, 12.6)]), EMBER, T1, 1.6)
    c.paint(c.line_mask([(cx - 2.6, 14.6), (cx - 1.4, 15.8), (cx + 1.4, 15.8), (cx + 2.6, 14.6)], 0.5), UMBER, T3, 1.6)
    # the floppy patched hat
    c.paint(ellipse(c, cx, 8.6, 7.6, 1.4), UMBER, T1, 1.4)
    c.paint(c.poly_mask([(cx - 4.2, 8.4), (cx - 3.6, 4.0), (cx - 1.6, 2.6), (cx + 0.4, 3.6), (cx + 2.4, 2.4),
                         (cx + 3.8, 3.8), (cx + 4.2, 8.4)]), UMBER, T2, 1.4)
    c.paint(rect(c, cx - 4.2, 6.8, cx + 4.2, 7.8), EMBER, T2, 1.45)
    c.paint(rect(c, cx + 0.6, 3.8, cx + 3.0, 6.2), LAPIS, T1, 1.5)
    # crows perched on the arms, facing in, and one flying
    for side in (-1, 1):
        bx = cx + side * 12.0
        crow = (ellipse(c, bx, 14.4, 2.4, 1.5, side * 0.35) | c.circle(bx - side * 2.0, 12.8, 1.2)
                | c.poly_mask([(bx + side * 1.6, 14.6), (bx + side * 4.2, 15.8), (bx + side * 3.8, 14.0)]))
        c.paint(crow, UMBER, T3, 1.7)
        c.paint(c.poly_mask([(bx - side * 2.9, 12.4), (bx - side * 4.5, 13.0), (bx - side * 2.9, 13.6)]), SAFFRON, T3, 1.75)
    sprite(c, 30, 3, BIRD, UMBER, T3)
    frame(c)
    return encode(c.to_tiles())


def ghosts():
    """Three smiling sheet ghosts floating over a little graveyard of round-topped headstones at dusk:
    a sunset glow behind the hill, a crescent moon, a bare tree at the side, two pumpkins in the grass."""
    c = Canvas(48, 36)
    X, Y = c.X, c.Y
    c.paint(ALL(c), LAPIS, np.select([Y < 9, Y < 17], [T3, T2], T1))
    c.paint(ellipse(c, 25, 28.5, 31, 8.0), EMBER, T1)                            # the sunset glow
    c.paint(ellipse(c, 25, 28.5, 24, 5.0), SAFFRON, T1)
    c.paint(c.circle(43.0, 5.0, 2.4) & ~c.circle(44.2, 4.1, 2.0), PEARL, T0, 1.4)    # a crescent moon
    stars(c, ((33, 2), (17, 2), (46, 13), (4, 9)))
    # the graveyard hill and its headstones (blank and round-topped)
    hill = Y > 23.0 + 6.0 * ((X - 25) / 25) ** 2 + 0.3 * np.sin(X * 1.3)
    c.paint(hill, FERN, np.where(Y > 31, T3, T2))
    for (x0, top, w, h) in ((7, 27, 5, 6), (17, 24, 5, 7), (28, 24, 6, 7), (38, 27, 5, 6)):
        stone = rect(c, x0, top + 1, x0 + w, top + h) | rect(c, x0 + 1, top, x0 + w - 1, top + 1)
        c.paint(stone, PEARL, np.where(X > x0 + w - 1, T3, T2), 1.3)
        c.paint(rect(c, x0 - 1, top + h, x0 + w + 1, top + h + 1), FERN, T3, 1.35)
    pumpkin(c, 13.4, 32.6, 1.8, 1.3)
    pumpkin(c, 35.0, 32.4, 2.0, 1.4)
    # the bare tree at the left
    tree = (tube(c, [(2.2, 36), (2.8, 26), (3.6, 17), (5.6, 9)], 3.2, 1.2) | tube(c, [(3.4, 20.0), (6.6, 15.6), (6.8, 13.0)], 1.2, 0.7)
            | tube(c, [(4.6, 12.6), (3.4, 6.0), (4.6, 2.0)], 1.0, 0.7) | tube(c, [(5.4, 10.0), (8.2, 6.4), (10.4, 5.6)], 1.0, 0.6))
    c.paint(tree, UMBER, T3, 1.3)
    # the ghosts: a round head, a sheet that widens and sweeps to one side ending in three soft points,
    # little arms raised; big eyes, rosy cheeks and an open smile
    for (gx, top, w, h, sway) in ((13.6, 5.6, 8.2, 13.2, -1.0), (25.0, 2.6, 9.6, 15.4, 0.6), (36.8, 6.4, 8.2, 12.8, 1.1)):
        s = w / 9.6
        hc = top + w / 2
        f = np.clip((Y - hc) / (h - w / 2), 0, 1)
        sx = X - sway * f * f * 3.0
        hw = w / 2 + 1.1 * f
        hem = top + h - 2.4 * np.abs(np.sin(1.5 * math.pi * (sx - gx) / (w / 2 + 1.1)))
        g = c.circle(gx, hc, w / 2) | ((np.abs(sx - gx) < hw) & (Y >= hc) & (Y < hem))
        g |= ellipse(c, gx - w / 2 - 0.6, hc + 2.4, 1.9, 0.9, 0.7) | ellipse(c, gx + w / 2 + 0.6, hc + 2.4, 1.9, 0.9, -0.7)
        c.paint(g, PEARL, np.where(sx - gx > hw * 0.5, T1, T0), 1.5)
        for side in (-1, 1):
            c.paint(ellipse(c, gx + side * 1.6 * s, hc - 0.4, 0.8, 1.25), UMBER, T3, 1.7)
            c.paint(c.circle(gx + side * 2.9 * s, hc + 1.3, 0.7), EMBER, T0, 1.65)
        c.paint(ellipse(c, gx, hc + 1.3, 1.3 * s, 1.6 * s) & (Y > hc + 1.3), UMBER, T3, 1.7)
    frame(c)
    return encode(c.to_tiles())


# ---------------------------------------------------------------------------
# Challenge
# ---------------------------------------------------------------------------

def hauntedhouse():
    """A crooked Victorian house on a hill at dusk: a leaning turret with a witch-hat roof, a sagging
    mansard roof with dormers, white trim, lit windows with shutters (one hanging askew), a porch with
    pumpkins on the steps, a gnarled bare tree, a winding path, and bats against the deep blue sky."""
    c = Canvas(40, 46)
    X, Y = c.X, c.Y
    tx, ty = np.floor(X).astype(int), np.floor(Y).astype(int)
    c.paint(ALL(c), LAPIS, np.select([Y < 14, Y < 27], [T3, T2], T1))
    stars(c, ((15, 2), (30, 3), (2, 18), (20, 7), (13, 10)))
    # the hill, the winding path and pumpkins along it
    c.paint(Y > 32.5 + 0.02 * (X - 20) ** 2, FERN, np.where(Y > 39, T3, T2))
    path = c.line_mask([(21, 35), (23, 38), (17.5, 41), (11.5, 43.5), (9, 47)], 2.4)
    c.paint(path, PEARL, T2, 1.2)
    for (px, py) in ((26.0, 39.4), (13.0, 41.0)):
        pumpkin(c, px, py, 1.6, 1.2, prio=1.5)
    # the house: walls leaning a little to the right, white trim, a sagging mansard roof with dormers
    lean = 0.07 * (34 - Y)
    hx = X - lean
    walls = (hx > 10) & (hx < 31) & (Y > 16.5) & (Y < 34)
    c.paint(walls, UMBER, np.where(ty % 3 == 0, T3, T2), 1.2)
    trim = walls & ((hx < 11) | (hx > 30) | ((Y > 24) & (Y < 25)))
    c.paint(trim, PEARL, T1, 1.25)
    roof = c.poly_mask([(9.6, 17.0), (32.4, 16.6), (30.6, 10.4), (21.0, 11.4), (12.2, 11.0)])
    c.paint(roof, EMBER, np.where(ty % 2 == 0, T3, T2), 1.25)
    c.paint(c.line_mask([(12.2, 10.8), (21.0, 11.2), (30.6, 10.2)], 0.9) | rect(c, 9.4, 16.6, 32.6, 17.4), PEARL, T1, 1.3)
    for (dx, dy) in ((15, 11), (25, 10)):
        c.paint(rect(c, dx - 1, dy, dx + 4, dy + 4) | c.poly_mask([(dx - 1.6, dy + 0.2), (dx + 4.6, dy + 0.2), (dx + 1.5, dy - 2.6)]),
                UMBER, T3, 1.35)
        c.paint(rect(c, dx, dy + 1, dx + 3, dy + 4), SAFFRON, T0, 1.45)
    # windows, lit (one dark), with green shutters; one shutter hangs askew
    for (wx, wy, lit) in ((13, 19, 1), (18, 19, 1), (23, 19, 0), (27, 19, 1), (13, 26, 1), (27, 26, 1)):
        sh = int(round(0.07 * (34 - wy - 2)))
        c.paint(rect(c, wx + sh, wy, wx + sh + 3, wy + 4), SAFFRON if lit else LAPIS, T0 if lit else T3, 1.45)
        if wy < 24:
            c.paint(rect(c, wx + sh, wy + 2, wx + sh + 3, wy + 3), UMBER, T3, 1.46)
        if wy > 24:
            continue
        c.paint(rect(c, wx + sh - 1, wy, wx + sh, wy + 4), FERN, T3, 1.4)
        if wx != 27:
            c.paint(rect(c, wx + sh + 3, wy, wx + sh + 4, wy + 4), FERN, T3, 1.4)
    c.paint(rect(c, 32, 20, 33, 24) | rect(c, 33, 23, 34, 25), FERN, T3, 1.4)
    # the porch with its posts, red door, fanlight and steps
    c.paint(rect(c, 11, 29, 32, 30), PEARL, T1, 1.4)
    for px in (12, 17, 25, 30):
        c.paint(rect(c, px, 30, px + 1, 34), PEARL, T1, 1.45)
    c.paint(rect(c, 19, 30, 23, 34), EMBER, T3, 1.45)
    c.paint(rect(c, 20, 31, 22, 32), SAFFRON, T0, 1.5)
    c.paint(rect(c, 17, 34, 25, 35) | rect(c, 16, 35, 26, 36), PEARL, T2, 1.45)
    for (px, py) in ((15.0, 34.8), (27.0, 34.8)):
        pumpkin(c, px, py, 1.7, 1.3, prio=1.6)
    # the leaning turret with a witch-hat roof, a trim band and lit windows
    tl = 0.09 * (34 - Y)
    turret = (X + tl > 4.5) & (X + tl < 11.5) & (Y > 13) & (Y < 34)
    c.paint(turret, UMBER, np.where(X + tl > 9.5, T3, T2), 1.3)
    c.paint(turret & (Y > 21) & (Y < 22), PEARL, T1, 1.32)
    c.paint(c.poly_mask([(3.0, 14.0), (11.6, 13.2), (4.0, 1.6)]), EMBER, T3, 1.35)
    c.paint(c.line_mask([(4.0, 1.8), (3.6, 0.6)], 0.5), UMBER, T3, 1.4)
    for (wx, wy) in ((6, 15), (5, 25)):
        c.paint(rect(c, wx, wy, wx + 2, wy + 4), SAFFRON, T0, 1.45)
    # the gnarled tree at the right, reaching over the roof
    tree = (tube(c, [(36.6, 41), (36.4, 36), (35.0, 28), (36.0, 20), (34.6, 13)], 2.8, 1.0)
            | tube(c, [(35.6, 22.0), (32.6, 17.6), (29.6, 15.2)], 1.2, 0.6)
            | tube(c, [(35.2, 15.6), (37.6, 10.4), (38.4, 7.0)], 1.0, 0.6) | tube(c, [(34.8, 14.0), (32.0, 8.4), (28.4, 6.4)], 1.0, 0.6)
            | tube(c, [(36.4, 31.0), (38.6, 27.6)], 1.0, 0.6))
    c.paint(tree, UMBER, T3, 1.38)
    sprite(c, 16, 2, BAT, UMBER, T3)
    sprite(c, 7, 4, SMALL_BAT, UMBER, T3)
    frame(c)
    return encode(c.to_tiles())


def pumpkinpatch():
    """A pumpkin patch in perspective: a leafy field full of orange, yellow and white pumpkins growing
    smaller towards the red barn, a dirt lane leading back to it, curling tendrils, a blue wheelbarrow
    with pumpkins in it on the left and a hay bale with a pumpkin on top on the right."""
    c = Canvas(48, 38)
    X, Y = c.X, c.Y
    tx, ty = np.floor(X).astype(int), np.floor(Y).astype(int)
    c.paint(ALL(c), LAPIS, np.where(Y < 4, T1, T0))
    for (a, b, k) in ((8, 3.4, 0.8), (22, 2.6, 0.6)):
        c.paint(c.circle(a - 2.4 * k, b + 0.6, 1.8 * k) | c.circle(a, b, 2.5 * k) | c.circle(a + 2.5 * k, b + 0.7, 1.7 * k),
                PEARL, T0, 1.1)
    # trees and the red barn on the horizon
    c.paint(Y > 7.4 + 1.3 * np.abs(np.sin(X * 0.45)), FERN, T3)
    c.paint(rect(c, 33, 3, 42, 9) | c.poly_mask([(32.0, 3.4), (43.0, 3.4), (37.5, 0.6)]), EMBER, T2, 1.2)
    c.paint(c.poly_mask([(31.6, 3.6), (43.4, 3.6), (37.5, 0.4)]) & ~c.poly_mask([(33.2, 3.7), (41.8, 3.7), (37.5, 1.5)]), PEARL, T1, 1.25)
    c.paint(rect(c, 36, 5, 39, 9), PEARL, T1, 1.25)
    # the leafy field, and a dirt lane running back to the barn
    field = Y > 9.4
    c.paint(field, FERN, np.where(smooth_noise(c, 4, 1.2) > 0.2, T1, T2))
    lane = field & (np.abs(X - (37.5 - (37.5 - 24.0) * (Y - 9.4) / 28.6)) < 0.8 + 0.22 * (Y - 9.4))
    c.paint(lane, UMBER, np.where(ty % 3 == 0, T2, T1), 1.1)
    # rows of pumpkins, small and far to big and near, each with a curling tendril beside it
    r = random.Random(13)
    for k, (ry, rad) in enumerate(((11.6, 1.15), (14.6, 1.5), (18.6, 2.0), (23.8, 2.6), (30.6, 3.3))):
        x = r.uniform(0.5, 2.5) * rad
        while x < 48:
            lx = 37.5 - (37.5 - 24.0) * (ry - 9.4) / 28.6
            if abs(x - lx) > 1.2 + 0.22 * (ry - 9.4) + rad * 1.2:
                fam = (EMBER, EMBER, SAFFRON, EMBER, PEARL, EMBER, SAFFRON, PEARL)[r.randrange(8)]
                pr = rad * r.uniform(0.85, 1.15)
                pts = [(x - pr * 1.4 + math.cos(a) * (0.9 - 0.08 * a) * rad * 0.7, ry + pr * 0.4 + math.sin(a) * (0.9 - 0.08 * a) * rad * 0.7)
                       for a in np.arange(0, 7.5, 0.4)]
                c.paint(c.line_mask(pts, 0.45), FERN, T3, 1.3)
                pumpkin(c, x, ry, pr * 1.25, pr, fam, prio=1.4 + 0.05 * k)
            x += rad * r.uniform(3.4, 4.4)
    # the wheelbarrow with pumpkins, left front
    pumpkin(c, 6.0, 28.6, 2.4, 1.9, prio=1.55)
    pumpkin(c, 10.6, 28.2, 2.7, 2.1, SAFFRON, prio=1.55)
    c.paint(c.line_mask([(12.4, 31.4), (17.8, 29.6)], 0.8) | c.line_mask([(10.8, 34.0), (10.6, 37.0)], 0.8), UMBER, T3, 1.6)
    c.paint(c.poly_mask([(2.0, 29.8), (13.8, 29.8), (12.2, 34.4), (4.8, 34.4)]), LAPIS, T2, 1.6)
    c.paint(rect(c, 2, 30, 14, 31), LAPIS, T1, 1.62)
    c.paint(c.circle(4.2, 35.0, 1.8), UMBER, T3, 1.65)
    c.paint(c.circle(4.2, 35.0, 0.6), PEARL, T1, 1.7)
    # the hay bale with a pumpkin on top, right front
    bale = rect(c, 36, 29, 47, 37)
    c.paint(bale, SAFFRON, np.where(ty % 3 == 0, T2, T1), 1.6)
    c.paint(bale & ((tx == 39) | (tx == 44)), UMBER, T1, 1.62)
    pumpkin(c, 41.6, 26.6, 3.0, 2.4, prio=1.65)
    frame(c)
    return encode(c.to_tiles())


# ---------------------------------------------------------------------------
# Master
# ---------------------------------------------------------------------------

def spiderweb():
    """A big orb web spanning the frame at night: white spokes run out from the hub to the twigs it hangs
    from, the golden capture spiral crosses them ring after ring, beaded with dew; autumn leaves are
    caught in it and a little cartoon spider sits at the hub. The threads cut the night sky and the ivy
    behind into many small pieces."""
    c = Canvas(44, 44)
    X, Y = c.X, c.Y
    hx, hy = 21.0, 19.5
    r = random.Random(5)
    # the garden at night: deep sky, big ivy leaves along the bottom, a twig across the top-left corner
    # and a stem up the right side
    c.paint(ALL(c), LAPIS, T3)
    for (lx, ly, a, s) in ((5, 39, 0.5, 1.2), (13, 42, -0.2, 1.0), (2.5, 31, 1.1, 0.9), (38, 40, -0.6, 1.2),
                           (42, 31.5, 1.3, 0.9), (29, 42.5, 0.15, 1.0), (21, 44, 0.0, 0.9)):
        c.paint(ellipse(c, lx, ly, 4.4 * s, 3.0 * s, a), FERN, T2 if int(lx) % 2 else T3, 1.0)
    c.paint(tube(c, [(-1, 10), (6, 5.4), (13, 2.6), (21, 0.6)], 2.2, 1.2), UMBER, T2, 1.2)
    c.paint(tube(c, [(45, 2), (42.0, 13), (41.4, 25), (42.6, 36)], 1.8, 1.4), UMBER, T2, 1.2)
    # the spokes (white) from the hub out past the frame
    n = 13
    angs = [2 * math.pi * (k + 0.25 + r.uniform(-0.15, 0.15)) / n for k in range(n)]
    def pt(a, rr):
        return (hx + math.cos(a) * rr * 1.05, hy + math.sin(a) * rr)
    for a in angs:
        c.paint(c.line_mask([pt(a, 1.5), pt(a, 40)], 0.8), PEARL, T0, 1.5)
    # the capture spiral: rings of chords between the spokes, sagging a little; at alternate crossings
    # the ring or the spoke lies on top, so both are cut into short pieces; dew drops on some chords
    for j, rr in enumerate((4.2, 8.2, 12.2, 16.2, 20.2, 24.2)):
        pts = [pt(a, rr * (1 + 0.04 * math.sin(k * 2.3 + j))) for k, a in enumerate(angs)]
        for k in range(n):
            p, q = pts[k], pts[(k + 1) % n]
            mid = ((p[0] + q[0]) / 2 + (hx - (p[0] + q[0]) / 2) * 0.05, (p[1] + q[1]) / 2 + (hy - (p[1] + q[1]) / 2) * 0.05)
            c.paint(c.line_mask([p, mid, q], 0.8), SAFFRON, T0, 1.55)
            if (j + k) % 3 == 2 and j > 0:
                c.paint(c.circle(mid[0], mid[1], 0.9), PEARL, T0, 1.65)       # a dew drop
        for k in range(n):
            p = pts[k]
            c.paint(c.circle(p[0], p[1], 0.6), (SAFFRON, PEARL)[(j + k) % 2], T0, 1.6)
    # leaves caught in the web
    for (lx, ly, a, fam, tone) in ((9.0, 12.0, 0.5, EMBER, T1), (33.5, 8.5, -0.6, EMBER, T2), (32.0, 30.5, 1.0, UMBER, T0),
                                   (7.5, 27.5, -0.2, EMBER, T1), (22.0, 34.5, 0.3, EMBER, T2), (37.0, 19.0, 1.4, EMBER, T1),
                                   (25.5, 5.0, 2.6, EMBER, T2), (13.5, 36.5, -0.9, UMBER, T0)):
        autumn_leaf(c, lx, ly, a, fam, tone)
    for (lx, ly, a, fam) in ((15.0, 26.5, 2.2, UMBER), (30.0, 14.0, -0.4, UMBER), (39.0, 27.5, 1.9, EMBER), (3.5, 19.0, 0.2, UMBER)):
        autumn_leaf(c, lx, ly, a, fam, T0 if fam == UMBER else T1, 0.8)
    # the spider at the hub: round body, eight bent legs, big eyes
    for side in (-1, 1):
        for (ex, ey) in ((3.6, -3.0), (4.4, -1.0), (4.4, 1.4), (3.6, 3.6)):
            knee = (hx + side * ex * 0.7, hy + ey - 1.3)
            c.paint(c.line_mask([(hx, hy), knee, (hx + side * ex, hy + ey + 0.4)], 0.7), UMBER, T3, 1.8)
    c.paint(ellipse(c, hx, hy + 0.8, 2.3, 2.6) | c.circle(hx, hy - 1.9, 1.7), UMBER, T3, 1.85)
    c.paint(rect(c, 20, 17, 21, 18) | rect(c, 21, 17, 22, 18), PEARL, T0, 1.9)
    c.paint(rect(c, 20, 19, 22, 20), EMBER, T1, 1.9)
    frame(c)
    return encode(c.to_tiles())


def trickortreat():
    """Trick-or-treat night: a street of four tall house fronts (red brick, white, blue and green) with
    lit sash windows, porch lights and jack-o'-lanterns on the steps, hedges, a streetlamp, and three
    children in costume - a sheet ghost, a cat and a witch - walking along the pavement with pumpkin
    buckets, dark against the lit windows."""
    c = Canvas(48, 40)
    X, Y = c.X, c.Y
    tx, ty = np.floor(X).astype(int), np.floor(Y).astype(int)
    c.paint(ALL(c), LAPIS, T3)
    stars(c, ((2, 2), (12, 1), (20, 3), (30, 1), (40, 2), (46, 5), (35, 5)))
    sprite(c, 8, 5, SMALL_BAT, UMBER, T3)
    # houses: (x0, x1, peak, wall family, wall tone, trim, upper windows, lower window, door)
    houses = ((1, 12, 2, EMBER, T1, UMBER, (2, 7), 7, 2), (12, 24, 4, PEARL, T1, UMBER, (13, 19), 13, 19),
              (24, 36, 1, LAPIS, T0, PEARL, (25, 31), 25, 32), (36, 47, 5, FERN, T0, PEARL, (37, 42), 42, 37))
    for i, (x0, x1, peak, fam, tone, trim, ups, low, dx) in enumerate(houses):
        wall = rect(c, x0, 10, x1, 27)
        if fam == EMBER:                                   # brickwork: courses with staggered joints
            mortar = (ty % 2 == 0) | ((tx + (ty // 2 % 2) * 2) % 4 == 0)
            c.paint(wall, fam, np.where(mortar, T3, tone), 1.1)
        else:                                              # clapboards
            c.paint(wall, fam, np.where(ty % 2 == 0, min(1.0, tone + 0.34), tone), 1.1)
        c.paint(c.poly_mask([(x0 - 0.7, 10.5), (x1 + 0.7, 10.5), ((x0 + x1) / 2, peak)]), UMBER, np.where(ty % 2 == 0, T3, T2), 1.2)
        gx = (x0 + x1) // 2
        c.paint(rect(c, gx - 1, 7, gx + 1, 9), SAFFRON, T1, 1.3)                    # attic window
        # sash windows: trim, two lit panes split by a glazing bar (one window dark)
        tt = T3 if trim == UMBER else T0
        for (wx, wy) in [(u, 12) for u in ups] + [(low, 20)]:
            dark = (i, wx, wy) in ((1, 19, 12), (3, 37, 12))
            c.paint(rect(c, wx, wy, wx + 4, wy + 7), trim, tt, 1.3)
            c.paint(rect(c, wx + 1, wy + 1, wx + 3, wy + 6) & (ty != wy + 3), LAPIS if dark else SAFFRON, T3 if dark else T0, 1.35)
        if fam == PEARL:                                   # green shutters on the white house
            for u in ups:
                c.paint(rect(c, u - 1, 12, u, 19) | rect(c, u + 4, 12, u + 5, 19), FERN, T3, 1.32)
        # the door, a porch light, the steps and a jack-o'-lantern
        c.paint(rect(c, dx, 20, dx + 3, 27), (FERN, EMBER, EMBER, UMBER)[i], T3, 1.35)
        c.paint(rect(c, dx + 1, 18, dx + 2, 19), SAFFRON, T0, 1.4)
        c.paint(rect(c, dx - 1, 27, dx + 4, 28), PEARL, T2, 1.4)
        if i:
            jx = dx - 1.6 if i != 1 else dx + 4.6
            pumpkin(c, jx, 26.6, 1.6, 1.3, prio=1.5)
            c.paint(rect(c, int(jx) - 1, 26, int(jx), 27) | rect(c, int(jx) + 1, 26, int(jx) + 2, 27), SAFFRON, T0, 1.55)
    # front lawns with two hedges, the moonlit pavement, the kerb and the road with its dashed line
    c.paint(Y >= 27, FERN, T3, 1.0)
    for (hx, hw) in ((9.8, 2.6), (45.0, 2.2)):
        c.paint(ellipse(c, hx, 27.6, hw, 2.4) & (Y < 29), FERN, T2, 1.2)
    c.paint(Y >= 29, LAPIS, np.where(tx % 4 == 0, T3, T2), 1.1)
    c.paint(Y >= 33, PEARL, T3, 1.1)
    c.paint(Y >= 34, LAPIS, T3, 1.1)
    c.paint(rect(c, 0, 36, 48, 37) & (tx % 6 < 3), PEARL, T1, 1.15)
    # the streetlamp and its pool of light
    c.paint(ellipse(c, 41.5, 31.2, 4.0, 1.4), PEARL, T0, 1.15)
    c.paint(rect(c, 41, 10, 42, 33), UMBER, T3, 1.6)
    c.paint(rect(c, 40, 7, 43, 10), SAFFRON, T0, 1.65)
    c.paint(rect(c, 39, 6, 44, 7), UMBER, T3, 1.65)
    # the children, each with a pumpkin bucket: a sheet ghost, a cat with ears and a tail, a witch
    gx = 4.0
    c.paint(c.circle(gx, 22.8, 2.6) | (rect(c, gx - 2.6, 22.8, gx + 2.6, 33) & (Y < 32.6 + 0.6 * np.sin(X * 2.6))), PEARL, T0, 1.7)
    c.paint(rect(c, 2, 22, 3, 24) | rect(c, 4, 22, 5, 24), UMBER, T3, 1.8)
    kx = 15.5
    cat = (c.circle(kx, 23.6, 2.1) | c.poly_mask([(kx - 2.3, 23.2), (kx - 2.4, 19.2), (kx - 0.2, 21.6)])
           | c.poly_mask([(kx + 2.3, 23.2), (kx + 2.4, 19.2), (kx + 0.2, 21.6)]) | rect(c, kx - 1.9, 25.6, kx + 1.9, 31)
           | rect(c, kx - 1.9, 31, kx - 0.4, 33) | rect(c, kx + 0.4, 31, kx + 1.9, 33)
           | tube(c, [(kx + 1.6, 30.0), (kx + 4.0, 29.4), (kx + 4.6, 26.6), (kx + 3.6, 25.4)], 0.9, 0.8))
    c.paint(cat, UMBER, T3, 1.7)
    c.paint(ellipse(c, kx, 24.0, 1.3, 1.1), EMBER, T0, 1.75)
    wx = 27.5
    c.paint(c.poly_mask([(wx - 3.0, 33.0), (wx + 3.0, 33.0), (wx + 1.4, 25.4), (wx - 1.4, 25.4)]), UMBER, T3, 1.7)
    c.paint(c.circle(wx, 24.0, 1.6), EMBER, T0, 1.75)
    c.paint(c.poly_mask([(wx - 3.6, 22.8), (wx + 3.6, 22.8), (wx + 3.6, 21.8), (wx + 1.4, 21.8), (wx + 0.4, 15.6),
                         (wx - 1.4, 21.8), (wx - 3.6, 21.8)]), UMBER, T3, 1.8)
    c.paint(rect(c, wx - 1.4, 20.8, wx + 1.4, 21.8), EMBER, T2, 1.85)
    for (bx, by) in ((gx + 4.0, 30.6), (kx - 3.6, 30.6), (wx + 3.8, 30.6)):
        c.paint(c.line_mask([(bx - 1.2, by - 0.8), (bx, by - 2.2), (bx + 1.2, by - 0.8)], 0.4), UMBER, T3, 1.8)
        c.paint(ellipse(c, bx, by, 1.6, 1.3), EMBER, T1, 1.85)
    frame(c)
    return encode(c.to_tiles())


SCENES = {
    "jackolantern": jackolantern, "blackcat": blackcat, "scarecrow": scarecrow, "ghosts": ghosts,
    "hauntedhouse": hauntedhouse, "pumpkinpatch": pumpkinpatch, "spiderweb": spiderweb, "trickortreat": trickortreat,
}
