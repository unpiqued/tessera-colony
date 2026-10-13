"""World Art pack: eight tile homages to public-domain art and design from around the world and across
time, drawn with the same supersampled Canvas as art.py.

Gentle: Hokusai's Great Wave (48 x 34), Hiroshige's Sudden Shower (36 x 48), a Ming blue-and-white
vase (36 x 46), Kandinsky's Several Circles (42 x 42).
Challenge: the Aztec Sun Stone (44 x 44), the starry vault of Galla Placidia, Ravenna (42 x 46).
Master: Nasrid zellige tilework of the Alhambra (44 x 44), Mondrian's grid (42 x 42).
"""
import math
import random

import numpy as np

from art import Canvas, LAPIS, SAFFRON, FERN, EMBER, UMBER, PEARL, encode
from art_scenes import ALL, ellipse, rect, tube, frame


T1, T2, T3 = 1 / 3, 2 / 3, 1.0   # exact tones: flat areas come out without dither speckle


def tiles_of(c):
    """Tile-aligned coordinates (column, row) for crisp grid patterns."""
    return np.floor(c.X).astype(int), np.floor(c.Y).astype(int)


# ---------------------------------------------------------------------------
# Gentle
# ---------------------------------------------------------------------------

def great_wave():
    """Hokusai, The Great Wave off Kanagawa (c. 1831): the clawed wave curls over from the left,
    Fuji small and white in the trough, long boats with rowers."""
    c = Canvas(48, 34)
    X, Y = c.X, c.Y
    # cream sky under a grey band of cloud along the top
    c.paint(ALL(c), PEARL, T1)
    c.paint(Y < 5.0 + 0.8 * np.sin(X * 0.4 + 1.0), PEARL, T2)
    c.paint(Y < 2.6 + 0.6 * np.sin(X * 0.3), PEARL, T3)
    # far sea, and Mount Fuji on the horizon: dark blue with a white cap inside its outline
    c.paint(Y > 26.0, LAPIS, T1)
    c.paint(c.poly_mask([(26.2, 26.4), (32.2, 19.8), (34.2, 19.6), (40.4, 26.4)]), LAPIS, T3, 1.2)
    c.paint(c.poly_mask([(30.2, 22.9), (32.6, 20.6), (33.8, 20.5), (36.4, 22.9), (34.6, 22.0), (33.2, 23.1),
                         (31.8, 22.2)]), PEARL, 0.0, 1.6)
    # the swell on the right, its foam crest inset
    swell = Y > 22.0 + 0.1 * (X - 47.5) ** 2
    c.paint(swell, LAPIS, np.where(np.sin(np.hypot(X - 47, Y - 36) * 1.9) > 0.3, T1, T3))
    c.paint(swell & (Y > 23.2 + 0.1 * (X - 47.5) ** 2) & (Y < 24.8 + 0.1 * (X - 47.5) ** 2) & (X > 40),
            PEARL, 0.0, 1.3)
    # the great wave: one curling mass whose lip hangs over the hollow, striped along its curve
    outer = [(-1, 35), (-1, 19), (1.5, 14), (5, 9.5), (9, 6), (14, 3.4), (19, 2.2), (24, 2.2), (28.6, 3.6),
             (32.2, 6.2), (34.6, 9.6), (35.4, 12.8)]
    inner = [(33.6, 11.6), (31.6, 9.6), (28.8, 8.6), (26, 8.8), (23.8, 10.2), (22.4, 12.6), (22.0, 15.4),
             (22.8, 18.6), (24.4, 21.8), (26.6, 25), (28.6, 28.5), (30.2, 32), (31, 35)]
    wave = c.poly_mask(outer + inner)
    c.paint(wave, LAPIS, np.where(np.sin(np.hypot(X - 28, Y - 17) * 1.8) > 0.4, T1, T3))
    # foam: a white band a tile inside the crest, and blue-edged claws hanging from the lip
    crest = tube(c, [(7.6, 10.8), (9.8, 9.0), (14.2, 6.4), (19.2, 5.2), (24.0, 5.2), (28.2, 6.6), (31.4, 9.0),
                     (33.6, 12.0)], 1.6, 1.3)
    c.paint(crest & wave, PEARL, 0.0, 1.3)
    for (sx, sy) in ((24.6, 9.8), (27.2, 8.8), (29.8, 9.2), (32.2, 10.6), (34.4, 12.6)):
        claw = [(sx, sy), (sx + 0.2, sy + 2.2), (sx + 1.3, sy + 3.5)]
        c.paint(tube(c, claw, 3.0, 2.2), LAPIS, T3, 1.3)
        c.paint(tube(c, claw, 1.6, 1.0), PEARL, 0.0, 1.5)
    # the small foreground wave echoing Fuji, with its white cap
    small = c.poly_mask([(7, 35), (12.5, 31.0), (15.5, 28.4), (18.5, 30.6), (24, 35)])
    c.paint(small, LAPIS, T2, 1.1)
    c.paint(small & (Y < 30.8) & (Y > 29.5), PEARL, 0.0, 1.3)
    # three long pale boats with rows of dark rowers
    for (x0, y0, x1, y1) in ((5.5, 29.6, 21.5, 26.2), (22.5, 32.4, 36.5, 31.6), (35.0, 28.6, 46.5, 25.2)):
        c.paint(tube(c, [(x0, y0), (x1, y1)], 1.6, 1.6), SAFFRON, 0.0, 1.5)
        for k in range(1, 7):
            t = k / 7
            c.paint(c.circle(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t - 1.1, 0.6), UMBER, T3, 1.7)
    frame(c)
    return encode(c.to_tiles())


def sudden_shower():
    """Hiroshige, Sudden Shower over Shin-Ohashi Bridge (1857): the wooden bridge crosses diagonally,
    small figures hurry under straw hats and an umbrella, dense rain lines, a dark cloud band at the
    top, the far bank low and faint, a raftsman on the river."""
    c = Canvas(36, 48)
    X, Y = c.X, c.Y
    tx, ty = tiles_of(c)
    c.paint(ALL(c), PEARL, T1)
    # the ink-dark cloud band along the top, billowing at its lower edge
    edge = 6.5 + 1.1 * np.sin(X * 0.45 + 0.8) + 0.7 * np.sin(X * 1.25)
    c.paint(Y < edge, UMBER, T2)
    c.paint(Y < edge - 2.2, UMBER, T3)
    # the far bank (Atake): a low strip of trees and roofs
    c.paint((Y > 16.8 + 0.8 * np.sin(X * 0.9) + 0.5 * np.sin(X * 2.3 + 1) + 0.04 * X) & (Y < 20.0), FERN, T3)
    c.paint(Y >= 20.0, LAPIS, T2)
    # the bridge: deck rising to the right, dark near beam, pilings in the water, a railing behind
    top = 36.5 - 0.3 * X
    c.paint((Y >= top) & (Y < top + 3.8), UMBER, 0.0, 1.2)
    piles = (Y >= top + 5.0) & ((((X - 1.0) % 5.5) < 1.1) | (((X - 3.2) % 5.5) < 0.8))
    c.paint(((Y >= top + 3.8) & (Y < top + 5.0)) | piles, UMBER, T3, 1.2)
    c.paint((np.abs(Y - (top - 1.0)) < 0.4) | ((Y > top - 1.2) & (Y < top) & (((X - 0.5) % 4.0) < 0.6)),
            UMBER, T3, 1.3)
    # rain: long steep lines in two directions, drawn as tone steps only so no colour region is broken
    rain = ((tx - np.floor(ty * 0.17).astype(int)) % 4 == 0) | ((tx + np.floor(ty * 0.06).astype(int)) % 7 == 2)
    for fam, s in ((PEARL, T3), (LAPIS, T3), (UMBER, None), (FERN, T2)):
        m = rain & (c.fam == fam)
        c.paint(m, fam, np.where(c.shade > 0.8, T2, np.where(c.shade < 0.2, T1, T3)) if s is None else s)
    # a log raft with its boatman poling toward the far bank
    c.paint(rect(c, 7.5, 24.2, 19.5, 25.8), UMBER, T2, 1.3)
    c.paint(c.line_mask([(16.2, 18.8), (20.4, 27.0)], 0.5), UMBER, T3, 1.5)
    c.paint(tube(c, [(14.0, 20.8), (14.4, 24.4)], 1.6, 1.8), UMBER, T3, 1.5)
    c.paint(c.poly_mask([(12.0, 21.0), (16.0, 21.0), (14.0, 19.2)]), SAFFRON, T1, 1.6)

    def walker(x, hat, body, lean=0.0):
        feet = 36.5 - 0.3 * x + 3.0
        for side in (-1, 1):
            c.paint(c.line_mask([(x + side * 0.7, feet - 2.0), (x + side * 0.9 + lean, feet)], 0.7), UMBER, T3, 1.6)
        c.paint(c.poly_mask([(x - 1.2 + lean, feet - 6.2), (x + 1.2 + lean, feet - 6.2), (x + 1.9, feet - 1.8),
                             (x - 1.9, feet - 1.8)]), body[0], body[1], 1.7)
        if hat is not None:
            c.paint(c.poly_mask([(x - 2.6 + lean, feet - 5.8), (x + 2.6 + lean, feet - 5.8),
                                 (x + lean, feet - 8.0)]), hat[0], hat[1], 1.8)
    # two figures in straw hats and capes on the left, one alone, two under one umbrella on the right
    walker(4.6, (SAFFRON, T1), (SAFFRON, T3), 0.8)
    walker(10.2, (SAFFRON, T1), (PEARL, T2), 0.8)
    walker(17.6, (SAFFRON, T2), (EMBER, T2), -0.7)
    walker(25.4, None, (PEARL, T1), -0.7)
    walker(29.0, None, (LAPIS, 0.0), -0.7)
    uy = 36.5 - 0.3 * 27.2 - 3.5
    c.paint(ellipse(c, 27.2, uy, 5.0, 2.7) & (Y < uy + 0.2), UMBER, T3, 1.9)
    frame(c)
    return encode(c.to_tiles())


def ming_vase():
    """A Ming blue-and-white porcelain meiping (15th c.): a cobalt lotus scroll round the body, ruyi
    lappets on the shoulder, lotus panels at the foot; on a lacquer-red wall, on a dark wooden stand."""
    c = Canvas(36, 46)
    X, Y = c.X, c.Y
    cx = 18.0
    c.paint(ALL(c), EMBER, T3)
    c.paint(ellipse(c, cx, 23.0, 15.5, 20.5), EMBER, T2)
    # the vase: a meiping profile (half-width by height), glazed white with a soft highlight
    ys = [3.6, 5.6, 6.2, 7.6, 9.6, 12.0, 15.0, 19.0, 24.0, 30.0, 35.5, 39.5, 40.4, 41.6]
    hw = [2.9, 2.9, 2.2, 3.0, 7.0, 10.2, 11.6, 11.9, 11.2, 9.6, 8.0, 7.0, 7.3, 7.3]
    half = np.interp(Y, ys, hw)
    vase = (Y >= 3.6) & (Y < 41.6) & (np.abs(X - cx) <= half)
    t = (X - cx) / np.maximum(half, 0.1)
    c.paint(vase, PEARL, np.where((t > -0.62) & (t < -0.12), 0.0, np.where(np.abs(t) > 0.8, T2, T1)))

    def blue(m, tone=T3, p=1.3):
        c.paint(m & vase, LAPIS, tone, p)
    # rim, the two bands framing the main zone, and the foot band
    blue(Y < 5.6)
    blue(np.abs(Y - 13.6) < 0.6)
    blue(np.abs(Y - 34.2) < 0.6)
    blue(Y > 39.8)
    # shoulder: ruyi (cloud-collar) lappets hanging below the neck
    for k in range(-2, 3):
        lx = cx + k * 3.4
        blue(c.circle(lx, 9.8, 1.4) | c.poly_mask([(lx - 1.35, 10.1), (lx + 1.35, 10.1), (lx, 12.6)]), T2)
    # lower zone: pointed lotus panels standing on the foot band
    for k in range(-2, 3):
        lx = cx + k * 3.1
        blue(c.poly_mask([(lx - 1.1, 40), (lx - 1.1, 37.4), (lx, 35.6), (lx + 1.1, 37.4), (lx + 1.1, 40)]), T2)
    # main zone: a lotus scroll - one wavy vine with leaves, and big blossoms on its crests and troughs
    vine = [(x, 24.0 - 4.2 * math.sin((x - 6.0) * 0.52)) for x in np.arange(5.5, 31.0, 0.5)]
    blue(tube(c, vine, 1.1, 1.1), T3, 1.4)
    for k, bx in enumerate((9.0, 15.0, 21.0, 27.0)):
        by = 24.0 - 4.2 * math.sin((bx - 6.0) * 0.52)
        up = -1 if k % 2 == 0 else 1
        fy = by + up * 1.2
        petals = np.zeros_like(X, bool)
        for a in (-0.9, -0.45, 0.0, 0.45, 0.9):
            petals |= ellipse(c, bx + 2.1 * math.sin(a), fy + up * 2.1 * math.cos(a), 0.95, 1.6, -a * up)
        blue(petals | c.circle(bx, fy, 1.8), T2, 1.5)
        blue(c.circle(bx, fy, 1.0), T3, 1.6)
        # a leaf on the vine between blossoms
        lx = bx + 3.0
        ly = 24.0 - 4.2 * math.sin((lx - 6.0) * 0.52)
        blue(ellipse(c, lx, ly - up * 1.3, 1.5, 0.8, 0.6 * up), T3, 1.5)
    # a carved wooden stand
    stand = rect(c, cx - 8.6, 41.4, cx + 8.6, 42.8)
    stand |= rect(c, cx - 8.8, 42.8, cx - 6.6, 45) | rect(c, cx + 6.6, 42.8, cx + 8.8, 45)
    c.paint(stand, UMBER, T3, 1.3)
    frame(c)
    return encode(c.to_tiles())


def several_circles():
    """Kandinsky, Several Circles (1926): translucent circles of many sizes on a near-black ground;
    where two overlap the colours mix; one big deep-blue circle with a pale halo."""
    c = Canvas(42, 42)
    c.paint(ALL(c), UMBER, T3)
    c.paint(ellipse(c, 25.0, 27.0, 14.0, 10.5, -0.5), UMBER, T2)
    # the big dark-blue circle and its halo
    halo, big = c.circle(16, 16, 12.4), c.circle(16, 16, 10.4)
    c.paint(halo, LAPIS, 0.0)
    c.paint(big, LAPIS, T3)
    # a large yellow circle overlapping it: green where they mix
    yel = c.circle(26.5, 26.5, 7.6)
    c.paint(yel, SAFFRON, T1)
    c.paint(yel & halo, FERN, 0.0)
    c.paint(yel & big, FERN, T2)
    # a blue circle over the yellow's lower right (green again where they overlap)
    blu = c.circle(34.5, 33.5, 5.2)
    c.paint(blu, LAPIS, T1)
    c.paint(blu & yel, FERN, T1)
    # a red circle touching the halo (deeper red in the overlap)
    red = c.circle(7.5, 31.5, 4.6)
    c.paint(red, EMBER, T1)
    c.paint(red & halo, EMBER, T3)
    # smaller circles floating on the ground and inside the big one
    for (x, y, r, fam, s) in ((11.5, 11.0, 3.0, PEARL, 0.0), (21, 11, 2.1, EMBER, T1), (20, 21, 2.1, SAFFRON, 0.0),
                              (34.0, 9.0, 4.2, FERN, T1), (38, 18, 2.1, SAFFRON, T1), (28, 38, 2.1, EMBER, 0.0),
                              (18.0, 35.5, 2.5, PEARL, T2), (5, 4, 2.1, LAPIS, 0.0), (26, 5, 2.1, FERN, T2),
                              (30, 17, 2.1, PEARL, T1), (38, 26, 2.1, EMBER, T2), (12, 38, 2.1, SAFFRON, T2)):
        c.paint(c.circle(x, y, r), fam, s, 1.3)
    frame(c)
    return encode(c.to_tiles())


# ---------------------------------------------------------------------------
# Challenge
# ---------------------------------------------------------------------------

def sun_stone():
    """The Aztec Sun Stone (c. 1502-21): the face at the centre, four Ollin panels, the ring of twenty
    day signs, eight pointed rays and the fire-serpent rim; grey stone with painted accents on a dark
    ground. The carved grooves are drawn last so they form one connected network."""
    c = Canvas(44, 44)
    X, Y = c.X, c.Y
    cx = cy = 22.0
    R = np.hypot(X - cx, Y - cy)
    A = np.arctan2(Y - cy, X - cx)
    c.paint(ALL(c), UMBER, T3)
    stone = R <= 20.7
    c.paint(stone, PEARL, T2)
    # the fire-serpent rim (painted red, scaled)
    c.paint(stone & (R > 18.0), EMBER, np.where(np.sin(A * 20) > 0.2, T2, T3))
    # eight big golden rays pointing at the rim
    for k in range(8):
        dA = np.abs((A - k * math.pi / 4 + math.pi) % (2 * math.pi) - math.pi)
        c.paint((R > 14.0) & (R < 16.9) & (dA * R < 3.1 * (16.9 - R) / 2.9), SAFFRON, T1, 1.3)
    # the twenty day signs, turquoise and pale stone alternating
    pos = A / (2 * math.pi) * 20 + 0.5
    ring = (R > 10.4) & (R < 13.3)
    c.paint(ring & (np.floor(pos) % 2 == 0), FERN, T1, 1.2)
    c.paint(ring & (np.floor(pos) % 2 == 1), PEARL, 0.0, 1.2)
    # the four Ollin panels, each with a painted glyph, and hearts held at the sides
    panels = []
    for (sx, sy, fam) in ((-1, -1, EMBER), (1, -1, LAPIS), (-1, 1, SAFFRON), (1, 1, LAPIS)):
        px, py = cx + sx * 5.0, cy + sy * 5.0
        inside = rect(c, px - 1.5, py - 1.5, px + 1.5, py + 1.5)
        panels.append(rect(c, px - 2.3, py - 2.3, px + 2.3, py + 2.3) & ~inside)
        c.paint(inside, PEARL, 0.0, 1.5)
        c.paint(c.circle(px, py, 1.1), fam, T2, 1.6)
    for sx in (-1, 1):
        c.paint(c.circle(cx + sx * 7.6, cy, 1.5), EMBER, T2, 1.5)
    # the central face: pale, with a gold headband, dark eyes and the red knife tongue
    face = R < 4.2
    c.paint(face, PEARL, 0.0, 1.3)
    c.paint(face & (Y < 19.9), SAFFRON, T1, 1.4)
    for sx in (-1, 1):
        c.paint(c.circle(cx + sx * 1.7, 21.3, 0.75), UMBER, T3, 1.8)
    c.paint(c.poly_mask([(cx - 1.1, 23.2), (cx + 1.1, 23.2), (cx, 26.8)]), EMBER, T2, 1.8)
    # the carved grooves: rings, the day-sign dividers, the panel outlines, and the date box at the
    # top where the serpents' tails meet
    groove = np.zeros_like(stone)
    for r0 in (17.6, 13.7, 10.0, 4.8):
        groove |= np.abs(R - r0) < 0.6
    groove |= (R > 9.8) & (R < 13.9) & ((pos % 1 < 0.1) | (pos % 1 > 0.9))
    date = rect(c, 20.3, 2.9, 23.7, 5.5)
    groove |= rect(c, 19.4, 2.0, 24.6, 6.4) & ~date
    for m in panels:
        groove |= m
    c.paint(groove & stone, UMBER, T1, 1.4)
    c.paint(date, PEARL, T1, 1.5)
    frame(c)
    return encode(c.to_tiles())


def ravenna_vault():
    """The starry vault of the Mausoleum of Galla Placidia, Ravenna (c. 425): a deep-blue dome thick
    with gold and white rosettes in concentric rings round a golden cross, gold stars in the corners,
    bands of red, green and white at the edges. Rosettes and cross are tile-aligned."""
    c = Canvas(42, 46)
    X, Y = c.X, c.Y
    tx, ty = tiles_of(c)
    cx, cy = 21.0, 23.0
    R = np.hypot(X - cx, Y - cy)
    # the corners (pendentives), the border bands and the dome ringed in gold
    c.paint(ALL(c), LAPIS, T2)
    edge = np.minimum.reduce([X, c.w - X, Y, c.h - Y])
    c.paint(edge < 2.0, EMBER, T2)
    c.paint((edge >= 2.0) & (edge < 3.0), FERN, T2)
    c.paint((edge >= 3.0) & (edge < 4.0), PEARL, T1)
    c.paint(R < 17.0, LAPIS, T3)
    c.paint((R >= 15.7) & (R < 17.1), SAFFRON, T2, 1.2)

    def rosette(x, y, big, fam):
        """A rosette on whole tiles: a plus, or (big) a 3x3 block with four tips."""
        i, j = int(math.floor(x)), int(math.floor(y))
        dx, dy = np.abs(tx - i), np.abs(ty - j)
        m = (dx + dy <= 1) if not big else ((np.maximum(dx, dy) <= 1) | ((dx + dy == 2) & ((dx == 0) | (dy == 0))))
        c.paint(m, fam, T1 if fam == SAFFRON else 0.0, 1.5)
    # three concentric rings of small rosettes, gold and white alternating
    for (rr, n, a0) in ((7.8, 10, 0.3), (11.1, 14, 0.0), (14.2, 18, 0.2)):
        for k in range(n):
            a = a0 + k * 2 * math.pi / n
            rosette(cx + rr * math.cos(a), cy + rr * math.sin(a), False, SAFFRON if k % 2 == 0 else PEARL)
    for (x, y) in ((6.5, 7.5), (35.5, 7.5), (6.5, 38.5), (35.5, 38.5)):
        rosette(x, y, True, SAFFRON)
    # the golden Latin cross at the centre
    cross = ((tx >= 20) & (tx <= 21) & (ty >= 17) & (ty <= 30)) | ((ty >= 19) & (ty <= 20) & (tx >= 16) & (tx <= 25))
    c.paint(cross, SAFFRON, T1, 1.6)
    frame(c)
    return encode(c.to_tiles())


# ---------------------------------------------------------------------------
# Master
# ---------------------------------------------------------------------------

def star_sd(u, v, R, r):
    """Signed distance (negative inside) to an 8-point star with tips at radius R and inner corners
    at radius r, for offsets (u, v) from its centre."""
    rho, th = np.hypot(u, v), np.arctan2(v, u)
    phi = np.abs(((th + math.pi / 8) % (math.pi / 4)) - math.pi / 8)
    x, y = rho * np.cos(phi), rho * np.sin(phi)
    ex, ey = r * math.cos(math.pi / 8) - R, r * math.sin(math.pi / 8)
    ln = math.hypot(ex, ey)
    return (x - R) * (ey / ln) - y * (ex / ln)


def alhambra_zellige():
    """Nasrid zellige of the Alhambra (14th c.): large 8-point star rosettes (green and gold points
    round a red or blue octagon holding a gold star and a white heart) on a 22-tile lattice, small red
    stars at the lattice corners, the ground between cut into blue and black wedges by white
    interlacing straps. Evaluated at tile centres, so every edge is crisp."""
    c = Canvas(44, 44)
    tx, ty = tiles_of(c)
    px, py = tx + 0.5, ty + 0.5
    S = 22.0
    # star centres sit on tile corners (11 + 22 i), so every shape and strap is mirror-symmetric
    bi, bj = np.floor(px / S), np.floor(py / S)
    u, v = px - (bi * S + 11), py - (bj * S + 11)             # offset from the big star's centre
    si, sj = np.floor((px + 11) / S), np.floor((py + 11) / S)
    u2, v2 = px - si * S, py - sj * S                         # offset from the small star's centre
    RB, rb = 10.6, 5.4
    big, inner, small = star_sd(u, v, RB, rb), star_sd(u, v, 3.6, 2.0), star_sd(u2, v2, 5.2, 2.9)
    # the ground: eight wedges round each small star, blue and black alternating
    wedge = np.floor((np.arctan2(v2, u2) + math.pi) / (math.pi / 4)).astype(int) % 8
    fam = np.where(wedge % 2 == 0, LAPIS, UMBER)
    tone = np.ones(tx.shape)
    # big stars: eight points round an octagon; axial points green, diagonal points gold
    rho, ang = np.hypot(u, v), np.arctan2(v, u)
    along = rho * np.cos(np.abs(((ang + math.pi / 8) % (math.pi / 4)) - math.pi / 8))   # toward nearest tip
    axial = (np.round(ang / (math.pi / 4)).astype(int) % 2) == 0
    pts = (big <= 0) & (along > rb * math.cos(math.pi / 8) + 0.5)
    fam[pts & axial], tone[pts & axial] = FERN, T2
    fam[pts & ~axial], tone[pts & ~axial] = SAFFRON, T1
    # the octagon (red or blue by star) holding a gold star with a white heart
    par = ((bi + bj) % 2).astype(int)
    octa = (big <= 0) & (along < rb * math.cos(math.pi / 8) - 0.5)
    fam[octa] = np.where(par[octa] == 0, EMBER, LAPIS)
    tone[octa] = T2
    fam[inner <= 0], tone[inner <= 0] = SAFFRON, T1
    fam[np.maximum(np.abs(u), np.abs(v)) <= 1], tone[np.maximum(np.abs(u), np.abs(v)) <= 1] = PEARL, 0.0
    # small stars at the lattice corners: pale red with a gold heart
    fam[small <= 0], tone[small <= 0] = EMBER, T1
    heart = np.maximum(np.abs(u2), np.abs(v2)) <= 1.2
    fam[heart], tone[heart] = SAFFRON, T2
    # white straps: star outlines, the octagon ring, and straight bands between the stars
    strap = ((big > 0) & (big <= 1.0)) | ((small > 0) & (small <= 1.0))
    strap |= (big <= 0) & ~pts & ~octa
    bands = (np.abs(u2) < 0.6) | (np.abs(v2) < 0.6) | (np.abs(np.abs(u2) - np.abs(v2)) < 0.6)
    strap |= bands & (big > 0) & (small > 0)
    fam[strap], tone[strap] = PEARL, 0.0
    for f in range(6):
        c.paint(fam == f, f, tone)
    frame(c)
    return encode(c.to_tiles())


def mondrian_grid():
    """Mondrian, Composition with Large Red Plane, Yellow, Black, Gray and Blue (1921): thick dark lines
    split the canvas into rectangles; a large red plane upper right of centre, and many more, smaller
    cells than the original so red, yellow, blue, grey and white each appear in several places."""
    c = Canvas(42, 42)
    tx, ty = tiles_of(c)
    c.paint(ALL(c), UMBER, T3)
    r = random.Random(1921)
    cells = []

    def split(x0, y0, x1, y1):
        """Cut a cell (tile ranges, lines excluded) by a one-tile line until it is small."""
        w, h = x1 - x0, y1 - y0
        if (w <= 6 and h <= 6) or (w * h < 30 and r.random() < 0.5):
            cells.append((x0, y0, x1, y1))
        elif w >= h:
            s = r.randint(x0 + 2, x1 - 3)
            split(x0, y0, s, y1)
            split(s + 1, y0, x1, y1)
        else:
            s = r.randint(y0 + 2, y1 - 3)
            split(x0, y0, x1, s)
            split(x0, s + 1, x1, y1)
    # the big red plane; the left column, the upper right and the lower band are subdivided
    split(1, 1, 9, 41)
    split(25, 1, 41, 15)
    split(10, 16, 41, 41)
    colours = {"white": (PEARL, 0.0), "grey": (PEARL, T2), "red": (EMBER, T2), "yellow": (SAFFRON, T1),
               "blue": (LAPIS, T3), "black": (UMBER, T3)}
    weights = ["white"] * 6 + ["grey"] * 3 + ["red", "yellow", "yellow", "blue", "blue"]
    chosen = [((10, 1, 24, 15), "red")]
    for cell in cells:
        # no colour twice across one line (neighbours are one tile apart)
        near = [k for (o, k) in chosen
                if o[0] <= cell[2] + 1 and cell[0] <= o[2] + 1 and o[1] <= cell[3] + 1 and cell[1] <= o[3] + 1]
        pick = r.choice(weights)
        while pick not in ("white", "grey") and pick in near:
            pick = r.choice(weights)
        chosen.append((cell, pick))
    chosen[-7] = (chosen[-7][0], "black")    # one small black plane, as in the original
    for (x0, y0, x1, y1), k in chosen:
        fam, s = colours[k]
        c.paint((tx >= x0) & (tx < x1) & (ty >= y0) & (ty < y1), fam, s)
    frame(c)
    return encode(c.to_tiles())


SCENES = {
    "greatwave": great_wave, "shower": sudden_shower, "mingvase": ming_vase, "circles": several_circles,
    "sunstone": sun_stone, "ravenna": ravenna_vault, "alhambra": alhambra_zellige, "mondrian": mondrian_grid,
}
