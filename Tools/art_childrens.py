"""Children's Classics pack: eight iconic scenes from public-domain children's books, drawn from the
books themselves (not any film or cartoon version) with the supersampled Canvas of art.py.

Gentle: the yellow brick road to the Emerald City (Baum), messing about in boats (Grahame), the
red-flag warning (Nesbit), the door in the ivy (Burnett).
Challenge: the Mad Tea-Party (Carroll), Mowgli at the Council Rock (Kipling).
Master (busy, every colour in many islands): the chessboard country (Carroll), inside the Terrible
Dogfish (Collodi).
"""
import math
import random

import numpy as np

from scipy import ndimage

from art import Canvas, LAPIS, SAFFRON, FERN, EMBER, UMBER, PEARL, SS, encode, leaf
from art_scenes import ALL, ellipse, rect, tube, frame, sky, cloud, smooth_noise


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------

def lerp_path(pts, y):
    """Interpolate (x, half-width) along a path given as [(y, x, half_width), ...] sorted by y."""
    ys = [p[0] for p in pts]
    return np.interp(y, ys, [p[1] for p in pts]), np.interp(y, ys, [p[2] for p in pts])


# ---------------------------------------------------------------------------
# Gentle
# ---------------------------------------------------------------------------

def yellowbrick():
    """Baum, The Wonderful Wizard of Oz (1900): the road of yellow brick winds through meadows and the
    great field of poppies to the green spires of the Emerald City."""
    c = Canvas(44, 42)
    X, Y = c.X, c.Y
    hz = 16.0
    sky(c, 0.72, 0.05, horizon=hz)
    cloud(c, [(5, 5.5, 1.6), (7.5, 4.6, 2.1), (10, 5.6, 1.5)])
    cloud(c, [(38, 9, 1.3), (40.2, 8.3, 1.7)])
    # distant blue hills either side of the city
    c.paint(Y > hz - 2.5 + 1.5 * np.sin(X * 0.35 + 0.5), LAPIS, 0.62)
    # the Emerald City: a green wall with towers and tall spires, lit green windows, gold finials
    gate_x = 26.0
    c.paint(rect(c, 15.5, 12.5, 36.5, hz + 0.4), FERN, 2 / 3)
    c.paint(rect(c, 15.5, 11.5, 36.5, 12.5) & (np.floor(X).astype(int) % 2 == 0), FERN, 2 / 3)
    for (x, top, w) in ((16.8, 10.0, 0.9), (19.6, 7.5, 1.1), (22.6, 9.0, 1.0), (26.0, 4.5, 1.6), (29.4, 8.0, 1.0),
                        (32.4, 6.0, 1.1), (35.2, 10.0, 0.9)):
        shaft = rect(c, x - w, top, x + w, hz)
        c.paint(shaft, FERN, np.where(X < x, 0.0, 1 / 3), 1.1)
        tip = top - 3.2 - 1.8 * w
        c.paint(c.poly_mask([(x - w - 0.5, top + 0.3), (x + w + 0.5, top + 0.3), (x, tip)]), FERN, 1.0, 1.2)
        c.paint(c.circle(x, tip, 0.5), SAFFRON, 0.0, 1.6)
        for wy in np.arange(top + 1.2, hz - 1.5, 2.2):
            c.paint(rect(c, x - 0.45, wy, x + 0.45, wy + 1.0), FERN, 1.0, 1.3)
    c.paint(rect(c, gate_x - 1.1, hz - 2.4, gate_x + 1.1, hz + 0.4) | c.circle(gate_x, hz - 2.4, 1.1), FERN, 1.0, 1.4)
    # the great poppy field: a red band before the city that sweeps down the left side
    n = smooth_noise(c, 4, 1.3)
    poppies = (Y > hz) & ((Y < 20.5 + 0.6 * np.sin(X * 0.4)) | (Y < 37 - 0.55 * X))
    c.paint(poppies, EMBER, np.where(n > 0.1, 2 / 3, 1 / 3))
    # green meadows with round trees
    meadow = (Y > hz) & ~poppies
    c.paint(meadow, FERN, np.where(smooth_noise(c, 9, 0.9) > 0.2, 2 / 3, 1 / 3))
    for (tx, ty, tr) in ((38.5, 22.5, 2.3), (35.5, 23.5, 1.7), (41.5, 28.5, 1.8)):
        c.paint(c.circle(tx, ty, tr), FERN, 1.0, 1.1)
        c.paint(rect(c, tx - 0.4, ty + tr - 0.3, tx + 0.4, ty + tr + 1.2), UMBER, 0.7, 1.3)
    # the road of yellow brick, in perspective: staggered courses grow towards the viewer
    path = [(hz - 0.2, gate_x, 0.6), (18.0, 24.0, 1.0), (20.5, 21.0, 1.7), (23.5, 19.6, 2.6), (27.0, 22.0, 3.6),
            (31.0, 27.0, 5.0), (35.5, 28.4, 6.6), (42.5, 24.0, 9.8)]
    cx, hw = lerp_path(path, Y)
    road = (Y > hz - 0.2) & (np.abs(X - cx) <= hw)
    u = (X - cx) / np.maximum(hw, 0.1)
    row = 300.0 / (Y - hz + 3.0)
    ri = np.floor(row).astype(int)
    col = np.floor(u * 2.6 + 0.5 * (ri % 2)).astype(int)
    c.paint(road, SAFFRON, ((ri + col) % 2) * (1 / 3) + (((ri * 5 + col * 3) % 7) == 0) * (1 / 3))
    c.paint(road & (np.abs(u) > 0.9), SAFFRON, 1.0, 1.1)
    # leafy tufts among the poppies, big poppies in the near meadow, small ones scattered
    for (lx, ly) in ((4, 22), (11, 19.5), (16.5, 24.5), (6.5, 29), (31, 18.5), (39, 19)):
        c.paint(ellipse(c, lx, ly, 1.3, 0.7, 0.4) | ellipse(c, lx + 1.0, ly - 0.2, 1.1, 0.6, -0.5), FERN, 2 / 3, 1.3)
    for (fx, fy, fr) in ((3.8, 37.8, 1.6), (8.2, 39.6, 1.5), (12.0, 37.0, 1.3)):
        c.paint(c.line_mask([(fx, fy), (fx + 0.3, 41)], 0.5), FERN, 1.0, 1.3)
        c.paint(c.circle(fx, fy, fr), EMBER, np.where(Y < fy, 1 / 3, 2 / 3), 1.4)
        c.paint(c.circle(fx, fy, 0.55), UMBER, 1.0, 1.7)
    for (fx, fy, fr) in ((30, 41, 0.9), (37.5, 39.5, 1.0), (41.5, 35, 0.8), (34.5, 31, 0.8), (40, 25.5, 0.7)):
        c.paint(c.circle(fx, fy, fr), EMBER, 0.4, 1.4)
    frame(c)
    return encode(c.to_tiles())


def riverbank():
    """Grahame, The Wind in the Willows (1908): messing about in boats. The Water Rat rows his little
    blue-and-white boat down the willow-lined river, the Mole in the stern, the luncheon-basket between."""
    c = Canvas(48, 36)
    X, Y = c.X, c.Y
    sky(c, 0.5, 0.05, horizon=9)
    # the far bank: meadow and a line of trees
    far = Y > 8.0 + 0.06 * X
    c.paint(far, FERN, 1 / 3)
    for (tx, ty, r) in ((18, 7.5, 2.4), (22, 7.0, 3.0), (26.5, 7.8, 2.2), (35, 8.0, 2.6), (39, 7.5, 2.0)):
        c.paint(c.circle(tx, ty, r) & (Y < ty + 1.5), FERN, 1.0, 1.1)
    # the river, with ripples
    water = Y > 11.5 + 0.08 * X + 0.4 * np.sin(X * 0.4)
    rip = np.sin(X * 0.9 + 3 * np.sin(Y * 1.7)) > 0.75
    c.paint(water, LAPIS, np.where(rip & (np.floor(Y).astype(int) % 3 == 0), 2 / 3, np.where(Y < 20, 0.0, 1 / 3)))
    # the near bank with reeds and bulrushes
    bank = Y > 29.5 + 0.9 * np.sin(X * 0.25 + 1.0) - 0.04 * X
    c.paint(bank, FERN, np.where(smooth_noise(c, 3, 1.0) > 0.0, 1 / 3, 2 / 3))
    for rx in list(np.arange(9.5, 19, 1.1)) + list(np.arange(37.5, 47, 1.0)):
        top = 22.5 + 2.5 * math.sin(rx * 1.7)
        c.paint(c.line_mask([(rx, 33), (rx + 0.6 * math.sin(rx), top)], 0.45), FERN, 1.0, 1.3)
    for (bx, by) in ((11.5, 23.5), (15.0, 22.8), (40.5, 23.0), (44.0, 24.2)):
        c.paint(ellipse(c, bx, by, 0.55, 1.3), UMBER, 0.8, 1.6)
    for (px, py) in ((25, 28.8), (29, 30.0)):
        c.paint(ellipse(c, px, py, 1.7, 0.7) & ~ellipse(c, px + 1.2, py - 0.3, 0.6, 0.5), FERN, 2 / 3, 1.3)
    # the willow on the left: trunk, crown and long drooping fronds over the water
    c.paint(tube(c, [(3.5, 34), (4.0, 24), (5.5, 14), (8.5, 6)], 3.2, 1.6), UMBER, 0.7, 1.2)
    crown = ellipse(c, 9, 2.5, 13.5, 6.5)
    c.paint(crown, FERN, np.where(np.sin(X * 1.7 + Y * 0.6) > 0.3, 1 / 3, 0.0), 1.1)
    for k, fx in enumerate(np.arange(0.5, 22, 1.25)):
        length = 9 + 7 * abs(math.sin(k * 1.3)) - 0.25 * fx
        c.paint(c.line_mask([(fx, 4), (fx + 0.3, 6 + length * 0.5), (fx + 0.9, 6 + length)], 0.55), FERN,
                (k % 3) / 3, 1.25)
    # the boat: blue outside, white within, and its reflection
    c.paint(ellipse(c, 26.5, 25.6, 11.0, 1.5), LAPIS, 2 / 3, 1.1)
    hull = c.poly_mask([(14.0, 18.8), (16.5, 20.4), (35.5, 20.2), (38.0, 18.6), (34.5, 24.4), (18.5, 24.6)])
    c.paint(hull, LAPIS, 1.0, 1.3)
    c.paint(hull & (Y < 20.9), PEARL, 0.2, 1.4)
    # the luncheon-basket
    c.paint(rect(c, 24.0, 16.4, 28.4, 19.8), SAFFRON, np.where((np.floor(X * 1.6) + np.floor(Y * 1.6)) % 2 == 0, 1 / 3, 2 / 3), 1.5)
    c.paint(rect(c, 23.8, 15.8, 28.6, 16.8), SAFFRON, 1.0, 1.6)
    c.paint(c.line_mask([(24.8, 16.0), (25.5, 14.4), (26.9, 14.4), (27.6, 16.0)], 0.45), UMBER, 0.8, 1.6)
    # the Water Rat at the oars (brown fur, pale front, round ear, facing left)
    rat = ellipse(c, 20.6, 16.4, 2.6, 3.6) | c.circle(19.2, 11.6, 2.1)
    rat |= c.poly_mask([(18.0, 10.6), (15.0, 12.2), (18.0, 13.4)])
    c.paint(rat, UMBER, 0.0, 1.5)
    c.paint(c.circle(20.4, 9.5, 0.9), UMBER, 2 / 3, 1.6)
    c.paint(c.circle(18.3, 11.3, 0.45), UMBER, 1.0, 1.8)
    c.paint(c.circle(15.2, 12.2, 0.45), UMBER, 1.0, 1.8)
    c.paint(ellipse(c, 19.6, 17.0, 1.3, 2.4), PEARL, 0.4, 1.5)
    c.paint(c.line_mask([(23.0, 16.8), (12.5, 25.5)], 0.5), UMBER, 2 / 3, 1.7)
    c.paint(ellipse(c, 12.0, 26.0, 1.8, 0.8, -0.6), UMBER, 2 / 3, 1.6)
    # the Mole in the stern (black velvet, pink snout and paws, facing right)
    mole = ellipse(c, 31.4, 16.8, 2.5, 3.2) | ellipse(c, 32.4, 12.8, 2.0, 1.7)
    c.paint(mole, UMBER, 1.0, 1.5)
    c.paint(c.poly_mask([(34.0, 12.0), (36.6, 13.2), (34.2, 14.2)]), EMBER, 0.0, 1.7)
    for (hx, hy) in ((34.0, 16.8), (29.2, 18.4)):
        c.paint(ellipse(c, hx, hy, 0.9, 0.7), EMBER, 0.0, 1.7)
    frame(c)
    return encode(c.to_tiles())


def railwaychildren():
    """Nesbit, The Railway Children (1906): a landslip has buried the line; looking up the cutting past
    the fallen earth, the three children wave their red flannel flags at the oncoming train."""
    c = Canvas(48, 36)
    X, Y = c.X, c.Y
    vx, vy = 21.0, 13.0
    sky(c, 0.62, 0.08, horizon=vy)
    # the cutting: grassy banks rising either side, trees along the top, the line between
    ground = Y > vy
    c.paint(ground, FERN, np.where(np.sin(X * 1.3 + Y * 0.7) > 0.4, 1 / 3, 0.0))
    n = smooth_noise(c, 6, 1.0)
    for sgn in (-1, 1):
        wall = (sgn * (X - vx) > 4.5 + (vy - Y) * 0.55) & (sgn * (X - vx) > 4.5 + (Y - vy) * 1.6)
        c.paint(wall, FERN, np.where(n * sgn > 0.05, 1.0, 2 / 3), 1.0)
    for (tx, ty, r) in ((3, 1.5, 3.2), (8, 0.8, 2.6), (12.5, 2.5, 2.2), (35.5, 2.2, 2.2), (40, 1.0, 2.8), (45.5, 2.0, 3.2)):
        c.paint(c.circle(tx, ty, r), FERN, 1 / 3, 1.1)
    # the line: grey ballast, sleepers and two rails converging on the bend
    d = Y - vy
    across = (X - vx) / np.maximum(d * 0.62, 0.05)
    bed = ground & (np.abs(across) < 1.0)
    c.paint(bed, PEARL, 2 / 3)
    sleepers = bed & (np.abs(across) < 0.78) & (((45.0 / (d + 2.0)) % 1.0) < 0.4) & (d > 6.5)
    c.paint(sleepers, UMBER, 1 / 3, 1.2)
    for side in (-0.5, 0.5):
        c.paint(ground & (np.abs(across - side) < 0.035 + 0.25 / np.maximum(d, 1)), UMBER, 1.0, 1.5)
    # the engine coming round the bend, seen three-quarter on: black smokebox front, blue boiler with
    # a brass band and dome, chimney, cab with a lit window, big wheels
    boiler = c.poly_mask([(vx, 9.0), (vx + 12.0, 9.6), (vx + 12.0, 15.2), (vx, 17.0)])
    c.paint(boiler, LAPIS, np.where(Y < 11.5, 2 / 3, 1.0), 1.3)
    c.paint(boiler & (np.abs(X - vx - 6.5) < 0.5), SAFFRON, 1 / 3, 1.4)
    c.paint(rect(c, vx + 9.5, 6.0, vx + 14.5, 15.6), LAPIS, 1.0, 1.35)
    c.paint(rect(c, vx + 10.6, 7.4, vx + 12.6, 9.8), LAPIS, 0.0, 1.5)
    c.paint(ellipse(c, vx + 4.6, 9.4, 1.3, 1.4) & (Y < 9.9), SAFFRON, 2 / 3, 1.6)
    c.paint(c.poly_mask([(vx, 15.5), (vx + 14.5, 14.6), (vx + 14.5, 16.4), (vx, 18.2)]), UMBER, 1.0, 1.3)
    for (wx, wy, r) in ((vx + 3.6, 17.2, 1.7), (vx + 7.6, 16.6, 1.6)):
        c.paint(c.circle(wx, wy, r), UMBER, 1.0, 1.5)
        c.paint(c.circle(wx, wy, 0.5), UMBER, 0.0, 1.6)
    c.paint(c.circle(vx, 13.0, 3.9), UMBER, 1.0, 1.45)
    c.paint(c.circle(vx, 13.0, 2.6) & ~c.circle(vx, 13.0, 1.9), UMBER, 1 / 3, 1.5)
    c.paint(rect(c, vx - 1.1, 5.4, vx + 1.1, 9.4), UMBER, 1.0, 1.5)
    c.paint(rect(c, vx - 1.6, 5.0, vx + 1.6, 6.0), SAFFRON, 2 / 3, 1.6)
    c.paint(rect(c, vx - 4.4, 16.6, vx + 4.0, 18.8), UMBER, 1.0, 1.5)
    # a great plume of steam filling the gap between the trees
    for (px, py, r) in ((vx + 0.5, 3.4, 2.4), (vx - 3.0, 4.0, 2.6), (vx + 4.0, 3.6, 3.0), (vx + 8.5, 3.6, 3.2),
                        (vx + 12.5, 3.0, 2.8), (vx - 6.5, 3.0, 2.4), (vx + 2.0, 0.6, 2.4), (vx + 7.0, 0.4, 2.4),
                        (vx + 7.4, 7.6, 1.9)):
        c.paint(c.circle(px, py, r), PEARL, np.where(Y < py - 0.5, 0.0, 1 / 3), 1.2)
    # the landslip in the foreground: a heap of earth and stones with a fallen tree lying across it
    slip = Y > 28.0 + 0.08 * X + 0.6 * np.sin(X * 0.9) - 1.5 * np.exp(-((X - 3) / 5) ** 2)
    c.paint(slip, UMBER, np.where(smooth_noise(c, 8, 1.3) > 0.0, 0.0, 1 / 3), 1.1)
    c.paint(tube(c, [(36, 33.8), (26, 32.2), (20, 31.0)], 1.7, 1.2), UMBER, 1.0, 1.4)
    c.paint(c.circle(17.0, 30.6, 2.8) | c.circle(14.0, 31.8, 2.2) | c.circle(18.5, 33.0, 1.8), FERN, np.where(Y < 30, 1 / 3, 1.0), 1.3)
    c.paint(c.line_mask([(36, 33.8), (38.5, 31.8)], 0.5) | c.line_mask([(36, 33.8), (38.0, 35.8)], 0.5), UMBER, 1.0, 1.4)
    # the three children, seen from behind, waving red flags over their heads
    for (fx, fy, s, dress) in ((8.0, 29.5, 1.15, PEARL), (33.5, 29.6, 1.1, LAPIS), (41.0, 26.8, 0.95, PEARL)):
        body = c.poly_mask([(fx - 1.8 * s, fy - 0.8 * s), (fx + 1.8 * s, fy - 0.8 * s), (fx + 1.1 * s, fy - 5.4 * s),
                            (fx - 1.1 * s, fy - 5.4 * s)])
        c.paint(body, dress, 1 / 3 if dress == LAPIS else 0.0, 1.5)
        for lx in (-0.7, 0.7):
            c.paint(c.line_mask([(fx + lx * s, fy - 1.0 * s), (fx + lx * s, fy + 0.6)], 0.65 * s), UMBER, 1.0, 1.6)
        c.paint(c.circle(fx, fy - 6.6 * s, 1.45 * s), UMBER, 1 / 3, 1.7)
        for side in (-1, 1):
            hand = (fx + side * 2.6 * s, fy - 8.4 * s)
            c.paint(c.line_mask([(fx + side * 0.9 * s, fy - 5.0 * s), hand], 0.65 * s), EMBER, 0.0, 1.6)
            flag = c.poly_mask([(hand[0] - 0.2 * side, hand[1] + 0.4), (hand[0] + side * 3.0 * s, hand[1] - 1.0 * s),
                                (hand[0] + side * 3.4 * s, hand[1] + 1.6 * s), (hand[0] + 0.2 * side, hand[1] + 2.2 * s)])
            c.paint(flag, EMBER, 2 / 3, 1.7)
    frame(c)
    return encode(c.to_tiles())


def secretgarden():
    """Burnett, The Secret Garden (1911): the little door hidden under the ivy of the high garden wall
    stands half open on roses and spring flowers; the robin watches from the wall, the old key below."""
    c = Canvas(36, 46)
    X, Y = c.X, c.Y
    tx, ty = np.floor(X).astype(int), np.floor(Y).astype(int)
    sky(c, 0.55, 0.05, horizon=10)
    # the high brick wall with a stone coping (bricks shown by tone only, so the wall stays one region)
    wall_top = 9.0
    wall = (Y >= wall_top) & (Y < 38)
    brick = (((tx + ty % 2) // 2) * 7 + ty * 13) % 5
    c.paint(wall, EMBER, np.where(brick == 0, 1.0, np.where(brick < 3, 2 / 3, 1 / 3)))
    c.paint(rect(c, -1, wall_top - 1.2, 37, wall_top + 0.6), PEARL, 2 / 3, 1.2)
    # thick ivy hanging in long tongues from the top of the wall and climbing its sides
    hang = 1.2 + 6.0 * np.abs(np.sin(X * 0.33 + 0.3)) ** 4 + 1.5 * np.sin(X * 1.3) ** 2 + 5.0 * np.exp(-((X - 18) / 2.6) ** 2)
    ivy = wall & ((Y - wall_top < hang) | (X < 2.5 + 3.0 * np.sin(Y * 0.3) ** 4) | (X > 33.5 - 3.0 * np.sin(Y * 0.27 + 1) ** 4))
    ivy |= rect(c, -1, wall_top - 1.4, 37, wall_top + 0.6) & (np.sin(X * 0.9) > -0.2)
    leaves = (np.sin(X * 2.2 + np.sin(Y * 1.9) * 2.0) > 0.0)
    c.paint(ivy, FERN, np.where(leaves, 2 / 3, 1.0), 1.1)
    c.paint(ivy & (np.sin(X * 3.1 + Y * 2.7) > 0.8), FERN, 1 / 3, 1.15)
    # the doorway, half open on the garden: blue sky, trees, roses, daffodils, a green lawn
    dx0, dx1, dtop, dbot = 12.5, 23.5, 25.0, 38.0
    dcx, dr = (dx0 + dx1) / 2, (dx1 - dx0) / 2
    door = rect(c, dx0, dtop, dx1, dbot) | (c.circle(dcx, dtop, dr) & (Y < dtop))
    c.paint(rect(c, dx0 - 1.0, dtop, dx1 + 1.0, dbot) | (c.circle(dcx, dtop, dr + 1.0) & (Y < dtop)), PEARL, 2 / 3, 1.2)
    c.paint(door, LAPIS, 0.0, 1.3)
    c.paint(door & (Y > 25 + 1.2 * np.sin(X * 1.3)), FERN, 1.0, 1.3)
    c.paint(door & (Y > 33.5), FERN, 1 / 3, 1.35)
    for (rx, ry, fam, sh) in ((15.5, 28.0, EMBER, 1 / 3), (18.0, 30.0, PEARL, 0.0), (21.5, 27.5, EMBER, 1 / 3),
                              (20.0, 31.5, EMBER, 2 / 3), (16.5, 31.5, PEARL, 0.0)):
        c.paint(c.circle(rx, ry, 1.2) & door, fam, sh, 1.45)
    for (fx, fy) in ((15.5, 35.5), (18.0, 36.6), (20.5, 35.2), (22.5, 36.8)):
        c.paint(c.circle(fx, fy, 0.75) & door, SAFFRON, 0.0, 1.5)
    # the door itself, swung inward against the left jamb: planks and an iron ring
    leaf_m = c.poly_mask([(dx0, dtop - 2.0), (dx0 + 3.6, dtop - 0.6), (dx0 + 3.6, dbot - 0.6), (dx0, dbot)])
    leaf_m |= door & (X < dx0 + 3.6) & (Y < dtop)
    c.paint(leaf_m & door, UMBER, np.where((tx % 2) == 0, 1 / 3, 2 / 3), 1.5)
    c.paint(c.circle(dx0 + 2.6, 31.5, 0.7), UMBER, 1.0, 1.7)
    # the curtain of ivy pulled aside at the right of the door
    c.paint(c.poly_mask([(dx1 - 0.5, 19.5), (dx1 + 2.5, 19.0), (dx1 + 3.0, 33.0), (dx1 + 0.8, 30.5)]), FERN, 2 / 3, 1.4)
    # the gravel path and the grass at the foot of the wall
    ground = Y >= 38
    c.paint(ground, FERN, np.where(np.sin(X * 2.1 + Y) > 0.2, 1 / 3, 2 / 3))
    path = ground & (np.abs(X - dcx) < 5.5 + (Y - 38) * 0.9)
    c.paint(path, PEARL, np.where(np.sin(X * 2.7) * np.sin(Y * 2.9) > 0.3, 2 / 3, 1 / 3))
    # the old key lying on the path
    c.paint(c.circle(11.5, 42.2, 1.9) & ~c.circle(11.5, 42.2, 0.8), SAFFRON, 1.0, 1.8)
    c.paint(c.line_mask([(13.2, 42.2), (22.0, 42.2)], 1.0), SAFFRON, 1.0, 1.8)
    c.paint(rect(c, 19.4, 42.2, 20.6, 44.4) | rect(c, 21.0, 42.2, 22.2, 43.8), SAFFRON, 1.0, 1.8)
    # the robin on the wall coping, against the sky
    rbx, rby = 25.5, 5.4
    c.paint(ellipse(c, rbx, rby, 2.8, 2.1, -0.2) | c.circle(rbx + 2.4, rby - 1.6, 1.5), UMBER, 1 / 3, 1.6)
    c.paint(c.poly_mask([(rbx - 2.2, rby - 0.2), (rbx - 5.0, rby - 1.8), (rbx - 4.4, rby + 0.8)]), UMBER, 2 / 3, 1.6)
    c.paint(ellipse(c, rbx + 2.0, rby + 0.3, 1.4, 1.6), EMBER, 1 / 3, 1.7)
    c.paint(c.circle(rbx + 2.8, rby - 1.9, 0.4), UMBER, 1.0, 1.9)
    c.paint(c.poly_mask([(rbx + 3.6, rby - 2.0), (rbx + 5.0, rby - 1.4), (rbx + 3.6, rby - 1.0)]), UMBER, 1.0, 1.8)
    for lx in (rbx - 0.4, rbx + 0.8):
        c.paint(c.line_mask([(lx, rby + 1.8), (lx, wall_top - 1.2)], 0.4), UMBER, 1.0, 1.7)
    frame(c)
    return encode(c.to_tiles())


# ---------------------------------------------------------------------------
# Challenge
# ---------------------------------------------------------------------------

def teapot(c, x, y, s, fam, shade=1 / 3, prio=1.6):
    """A round teapot standing on (x, y) (bottom centre), spout to the left, handle to the right."""
    X, Y = c.X, c.Y
    body = ellipse(c, x, y - 1.4 * s, 2.0 * s, 1.5 * s) & (Y < y)
    spout = c.line_mask([(x - 1.6 * s, y - 1.2 * s), (x - 3.0 * s, y - 2.6 * s)], 0.6 * s)
    handle = c.circle(x + 2.0 * s, y - 1.5 * s, 0.9 * s) & ~c.circle(x + 2.0 * s, y - 1.5 * s, 0.35 * s)
    lid = ellipse(c, x, y - 3.0 * s, 1.1 * s, 0.4 * s) | c.circle(x, y - 3.4 * s, 0.4 * s)
    c.paint(body | spout | handle | lid, fam, np.where(X < x - 0.5 * s, shade, min(1.0, shade + 1 / 3)), prio)
    return body


def teacup(c, x, y, fam, shade=1 / 3, prio=1.6):
    """A teacup on its saucer standing on (x, y)."""
    cup = c.poly_mask([(x - 0.9, y - 1.6), (x + 0.9, y - 1.6), (x + 0.6, y - 0.4), (x - 0.6, y - 0.4)])
    cup |= c.circle(x + 1.0, y - 1.1, 0.45)
    c.paint(cup, fam, shade, prio)
    c.paint(ellipse(c, x, y - 0.3, 1.4, 0.35), fam, min(1.0, shade + 1 / 3), prio)


def teaparty():
    """Carroll, Alice's Adventures in Wonderland (1865), after Tenniel: the Mad Tea-Party at the long
    table under the tree before the March Hare's house (ear-shaped chimneys, a roof thatched with fur)."""
    c = Canvas(48, 38)
    X, Y = c.X, c.Y
    sky(c, 0.5, 0.05, horizon=22)
    c.paint(Y > 20.5 + 0.5 * np.sin(X * 0.4), FERN, np.where(np.sin(X * 1.7 + Y * 2.1) > 0.3, 2 / 3, 1 / 3))
    # the tree: trunk and a broad crown over the left of the table
    c.paint(tube(c, [(3.0, 36), (2.8, 22), (4.0, 8)], 3.6, 2.4), UMBER, np.where(X < 2.8, 1 / 3, 2 / 3), 1.1)
    crown = c.circle(2, 2, 6.2) | c.circle(9.0, -0.5, 4.6) | c.circle(17.5, -1.5, 3.5) | c.circle(0, 12, 3.2)
    c.paint(crown, FERN, np.where(smooth_noise(c, 5, 1.5) > 0.05, 2 / 3, 1.0), 1.1)
    # the March Hare's house: a roof thatched with fur and two chimneys shaped like ears
    c.paint(rect(c, 31.5, 11.0, 47.5, 22.0), PEARL, np.where(np.floor(X).astype(int) % 5 == 1, 2 / 3, 1 / 3))
    c.paint(rect(c, 33.6, 14.0, 36.0, 17.0), LAPIS, 2 / 3, 1.3)
    fur = c.poly_mask([(29.5, 12.0), (39.0, 6.0), (48.5, 8.0), (48.5, 12.0)])
    c.paint(fur, UMBER, np.where(np.sin(X * 2.6 + Y * 1.2) > 0.2, 0.0, 1 / 3), 1.2)
    for (ex, ang) in ((35.5, -0.3), (44.5, 0.25)):
        c.paint(ellipse(c, ex, 4.6, 1.5, 3.4, ang), UMBER, 0.0, 1.3)
        c.paint(ellipse(c, ex, 4.8, 0.6, 2.4, ang), EMBER, 0.0, 1.35)
    # the long table with its white cloth and wooden legs
    c.paint(rect(c, 3.0, 23.0, 37.0, 24.6), PEARL, 0.0, 1.2)
    c.paint(rect(c, 3.0, 24.6, 37.0, 28.4 + 0.5 * np.sin(X * 1.6)), PEARL, 1 / 3, 1.2)
    for lx in (5.0, 21.0, 35.0):
        c.paint(rect(c, lx - 0.6, 28.0, lx + 0.6, 35.0), UMBER, 2 / 3, 1.3)
    # the March Hare: long ears, light-brown fur, a red coat
    hx = 11.5
    c.paint(ellipse(c, hx, 21.0, 4.0, 3.8), EMBER, 2 / 3, 1.3)
    c.paint(ellipse(c, hx, 15.0, 2.5, 2.8), UMBER, 0.0, 1.4)
    for (ex, ang) in ((hx - 1.2, -0.3), (hx + 1.4, 0.3)):
        c.paint(ellipse(c, ex, 9.0, 1.0, 3.6, ang), UMBER, 0.0, 1.4)
        c.paint(ellipse(c, ex, 9.2, 0.42, 2.6, ang), EMBER, 0.0, 1.45)
    c.paint(c.circle(hx - 1.1, 14.4, 0.45), UMBER, 1.0, 1.7)
    c.paint(ellipse(c, hx + 0.4, 16.9, 1.3, 0.9), PEARL, 0.0, 1.5)
    # the Hatter: tall hat with a band and card, a big bow tie, green coat
    c.paint(ellipse(c, 27.0, 21.2, 4.0, 4.4), FERN, 1.0, 1.3)
    c.paint(c.circle(27.0, 15.4, 2.2), EMBER, 0.0, 1.4)
    hat = c.poly_mask([(24.9, 13.4), (29.1, 13.4), (29.7, 5.0), (24.3, 5.0)])
    c.paint(hat, UMBER, 1.0, 1.5)
    c.paint(ellipse(c, 27.0, 13.2, 3.6, 0.7), UMBER, 1.0, 1.5)
    c.paint(hat & (Y > 10.6) & (Y < 12.0), EMBER, 2 / 3, 1.6)
    c.paint(rect(c, 28.4, 8.2, 30.2, 10.6), PEARL, 0.0, 1.7)
    c.paint(c.poly_mask([(27.0, 18.6), (24.8, 17.6), (24.8, 19.8)]) | c.poly_mask([(27.0, 18.6), (29.2, 17.6), (29.2, 19.8)]),
            SAFFRON, 1 / 3, 1.6)
    for ex in (26.0, 28.0):
        c.paint(c.circle(ex + 0.5, 15.5, 0.45), UMBER, 1.0, 1.9)
    # Alice in a large armchair at the end of the table: blue dress, white pinafore, fair hair
    c.paint(rect(c, 37.0, 11.0, 46.0, 31.0) | c.circle(41.5, 11.5, 4.5), EMBER, 1.0, 1.25)
    c.paint(rect(c, 38.2, 13.2, 44.8, 21.5), SAFFRON, 1 / 3, 1.4)
    c.paint(ellipse(c, 41.5, 23.5, 3.4, 4.6), LAPIS, 1 / 3, 1.45)
    c.paint(rect(c, 37.6, 25.5, 45.4, 30.5), LAPIS, 2 / 3, 1.45)
    c.paint(ellipse(c, 41.5, 23.5, 1.9, 3.8) | rect(c, 39.6, 25.5, 43.4, 30.0), PEARL, 0.0, 1.5)
    c.paint(c.circle(41.5, 16.6, 2.1), EMBER, 0.0, 1.55)
    c.paint(c.circle(41.5, 15.4, 2.1) & (Y < 15.2), SAFFRON, 1 / 3, 1.6)
    for ex in (40.5, 42.5):
        c.paint(c.circle(ex, 16.5, 0.4), UMBER, 1.0, 1.9)
    for lx in (40.4, 42.6):
        c.paint(rect(c, lx - 0.45, 30.0, lx + 0.45, 33.6), PEARL, 1 / 3, 1.5)
        c.paint(ellipse(c, lx, 33.8, 0.9, 0.6), UMBER, 1.0, 1.6)
    # teapots (one with the Dormouse asleep inside) and many cups along the table
    c.paint(c.circle(18.6, 17.4, 1.8) | c.circle(17.2, 15.6, 0.8) | c.circle(20.0, 15.6, 0.8), UMBER, 1 / 3, 1.65)
    c.paint(c.line_mask([(17.6, 17.2), (18.5, 17.6)], 0.35) | c.line_mask([(19.1, 17.6), (20.0, 17.2)], 0.35), UMBER, 1.0, 1.7)
    teapot(c, 18.6, 23.4, 1.3, LAPIS)
    teapot(c, 33.0, 23.4, 1.0, SAFFRON)
    teapot(c, 6.5, 23.4, 0.9, EMBER)
    for (x, fam) in ((10.5, LAPIS), (13.5, SAFFRON), (22.5, EMBER), (25.0, LAPIS), (29.5, EMBER), (36.0, LAPIS)):
        teacup(c, x, 23.6, fam)
    for (x, fam) in ((8.0, SAFFRON), (15.5, EMBER), (31.0, LAPIS)):
        teacup(c, x, 27.0, fam, 2 / 3)
    frame(c)
    return encode(c.to_tiles())


def wolf_from_behind(c, x, y, s, shade=2 / 3, prio=1.4):
    """A grey wolf sitting with its back to us: wide haunches, narrow shoulders, two pointed ears."""
    X, Y = c.X, c.Y
    m = ellipse(c, x, y - 2.0 * s, 2.7 * s, 2.1 * s) | ellipse(c, x, y - 4.8 * s, 1.8 * s, 2.6 * s)
    m |= c.circle(x, y - 7.8 * s, 1.45 * s)
    for sd in (-1, 1):
        m |= c.poly_mask([(x + sd * 0.2 * s, y - 8.6 * s), (x + sd * 1.3 * s, y - 10.9 * s), (x + sd * 1.6 * s, y - 7.8 * s)])
    m |= tube(c, [(x + 2.2 * s, y - 0.5 * s), (x + 3.8 * s, y - 0.3 * s), (x + 4.6 * s, y - 0.9 * s)], 1.0 * s, 0.6 * s)
    c.paint(m, PEARL, np.where(Y > y - 3.2 * s, min(1.0, shade + 1 / 3), shade), prio)
    c.paint(m & (Y < y - 6.4 * s) & (np.abs(X - x) > 0.9 * s), PEARL, max(0.0, shade - 1 / 3), prio + 0.05)
    return m


def wolfpack():
    """Kipling, The Jungle Book (1894): the Council Rock under a full moon. Akela lies at full length on
    the rock, the grey wolves of the Seeonee pack sit in a ring, the man-cub Mowgli stands in the middle."""
    c = Canvas(42, 46)
    X, Y = c.X, c.Y
    c.paint(ALL(c), LAPIS, 1.0)
    mx_, my_, mr = 21.0, 13.0, 8.8
    c.paint(c.circle(mx_, my_, mr + 2.6), LAPIS, 2 / 3)
    for (sx, sy) in ((8.5, 3.5), (33.5, 3.0), (12.0, 8.5), (30.5, 9.0), (6.5, 14.0), (36.0, 15.5)):
        c.paint(c.circle(sx + 0.5, sy + 0.5, 0.5) | rect(c, sx - 0.5, sy, sx + 1.5, sy + 1) | rect(c, sx, sy - 0.5, sx + 1, sy + 1.5),
                PEARL, 0.0, 1.5)
    # the great moon behind the Council Rock
    c.paint(c.circle(mx_, my_, mr), PEARL, np.where(np.hypot(X - mx_ - 1.5, Y - my_ + 1.5) < 6.8, 0.0, 1 / 3), 1.2)
    for (cx_, cy_, cr) in ((18.0, 11.5, 1.6), (24.0, 16.0, 1.2), (17.5, 17.0, 1.0)):
        c.paint(c.circle(cx_, cy_, cr), PEARL, 2 / 3, 1.25)
    # dark jungle crowding in at both sides, with big leaves, flowers and fireflies
    for sgn in (-1, 1):
        edge = sgn * (X - 21) > 11.0 + 3.5 * np.sin(Y * 0.5 + (1 if sgn > 0 else 3)) - 0.15 * np.maximum(Y - 24, 0)
        c.paint(edge, FERN, 1.0)
    for (bx, by, tx, ty, w) in ((-1, 4, 9, 0.5, 4.0), (-1, 13, 8.5, 9.5, 3.8), (-1, 23, 7.5, 19.0, 3.6),
                                (43, 6, 34, 2.5, 4.0), (43, 15, 34.5, 12.5, 3.8), (43, 25, 35.0, 21.0, 3.6)):
        leaf(c, bx, by, tx, ty, w, bend=0.12)
    for (fx, fy) in ((4.5, 29.0), (37.5, 30.5), (2.5, 17.5), (39.5, 9.5), (8.0, 25.0), (34.5, 26.5), (6.0, 6.5),
                     (36.0, 19.5), (10.0, 16.0), (32.5, 6.0), (3.0, 23.0), (39.0, 24.5)):
        for k in range(5):
            a = k * 2 * math.pi / 5
            c.paint(c.circle(fx + 0.95 * math.cos(a), fy + 0.95 * math.sin(a), 0.75), EMBER, 1 / 3, 1.5)
        c.paint(c.circle(fx, fy, 0.5), SAFFRON, 0.0, 1.6)
    # the hilltop, moonlit in the middle of the ring
    ground = Y > 32.0 + 0.8 * np.sin(X * 0.4)
    c.paint(ground, FERN, np.where(ellipse(c, 21.0, 40.0, 13.0, 4.5), 2 / 3, 1.0))
    for (fx, fy) in ((2.5, 39.0), (39.0, 40.0), (15.0, 44.5), (26.5, 44.5), (19.0, 33.5), (37.5, 44.0), (2.5, 44.0),
                     (10.5, 31.5), (31.0, 31.5), (6.0, 2.0), (35.0, 1.5)):
        c.paint(rect(c, fx - 1, fy, fx + 2, fy + 1) | rect(c, fx, fy - 1, fx + 1, fy + 2), SAFFRON, 0.0, 1.6)
    # the Council Rock, a dark mass against the moon, with Akela lying along its top
    rock = c.poly_mask([(8.5, 37.0), (11.0, 28.0), (13.0, 24.0), (29.0, 24.0), (31.0, 28.0), (33.5, 37.0)])
    c.paint(rock, UMBER, np.where(np.sin(X * 0.9 - Y * 0.5) > 0.7, 2 / 3, 1.0), 1.2)
    c.paint(rock & (Y < 25.2), UMBER, 1 / 3, 1.25)
    ak = ellipse(c, 19.5, 22.0, 5.6, 2.0) | ellipse(c, 25.6, 19.6, 2.0, 1.7) | rect(c, 24.5, 21.0, 28.8, 24.0)
    ak |= c.poly_mask([(26.8, 18.6), (29.8, 19.8), (27.0, 21.0)])
    for ex in (24.6, 26.2):
        ak |= c.poly_mask([(ex - 0.8, 18.6), (ex, 16.0), (ex + 0.8, 18.6)])
    ak |= tube(c, [(14.2, 22.4), (12.4, 23.4), (11.6, 24.2)], 1.2, 0.8)
    c.paint(ak, UMBER, 1.0, 1.5)
    c.paint(c.circle(26.4, 19.4, 0.45), SAFFRON, 0.0, 1.8)
    # the wolves sitting in a ring round the rock
    for (wx, wy, ws) in ((12.5, 37.0, 0.9), (29.5, 37.0, 0.9), (5.5, 45.6, 1.3), (35.5, 45.6, 1.3)):
        wolf_from_behind(c, wx, wy, ws, 2 / 3)
    # Mowgli, the man-cub, standing in the middle of the ring, his pebbles at his feet
    mx, my, k = 21.0, 44.0, 1.2
    c.paint(ellipse(c, mx, my - 6.0 * k, 1.6 * k, 2.6 * k) | c.line_mask([(mx - 0.7 * k, my - 4.0 * k), (mx - 1.2 * k, my)], 0.9 * k)
            | c.line_mask([(mx + 0.7 * k, my - 4.0 * k), (mx + 1.2 * k, my)], 0.9 * k), EMBER, 2 / 3, 1.6)
    c.paint(c.line_mask([(mx - 1.3 * k, my - 7.6 * k), (mx - 3.2 * k, my - 4.4 * k)], 0.75 * k)
            | c.line_mask([(mx + 1.3 * k, my - 7.6 * k), (mx + 3.4 * k, my - 10.4 * k)], 0.75 * k), EMBER, 2 / 3, 1.6)
    c.paint(c.circle(mx, my - 10.0 * k, 1.5 * k), EMBER, 1 / 3, 1.7)
    c.paint(c.circle(mx, my - 10.5 * k, 1.55 * k) & (Y < my - 10.4 * k), UMBER, 1.0, 1.75)
    c.paint(rect(c, mx - 1.6 * k, my - 4.6 * k, mx + 1.6 * k, my - 3.0 * k), PEARL, 1 / 3, 1.7)
    for (px, py) in ((15.0, 43.0), (17.0, 45.0), (25.0, 44.5), (26.5, 42.0)):
        c.paint(rect(c, px, py, px + 2, py + 1), PEARL, 1 / 3, 1.6)
    frame(c)
    return encode(c.to_tiles())


# ---------------------------------------------------------------------------
# Master
# ---------------------------------------------------------------------------

def outlined(c, m, fam, shade, prio, ring=0.45, ring_fam=UMBER):
    """Paint mask m with a dark outline ring around it (keeps neighbouring figures apart)."""
    halo = ndimage.binary_dilation(m, iterations=max(1, int(ring * SS)))
    c.paint(halo & ~m, ring_fam, 1.0, prio)
    c.paint(m, fam, shade, prio)


def chess_figure(c, kind, x, y, s, fam, shade):
    """A chess piece standing on (x, y): 'queen' (a figure with a bell skirt, face and crown),
    'castle' (a rook tower) or 'knight' (a horse's head on a base)."""
    X, Y = c.X, c.Y
    base = rect(c, x - 2.4 * s, y - 1.0 * s, x + 2.4 * s, y)
    if kind == 'castle':
        body = base | c.poly_mask([(x - 1.7 * s, y - 1.0 * s), (x + 1.7 * s, y - 1.0 * s), (x + 1.3 * s, y - 6.5 * s),
                                    (x - 1.3 * s, y - 6.5 * s)])
        top = rect(c, x - 2.2 * s, y - 8.6 * s, x + 2.2 * s, y - 6.5 * s)
        notch = (np.floor((X - (x - 2.2 * s)) / (1.47 * s)).astype(int) % 2 == 1) & (Y < y - 7.6 * s)
        m = body | (top & ~notch)
        outlined(c, m, fam, shade, 1.6, 0.7)
        c.paint(rect(c, x - 0.5 * s, y - 5.2 * s, x + 0.5 * s, y - 3.6 * s), UMBER, 1.0, 1.7)
    elif kind == 'knight':
        pts = [(-1.8, -1), (2.0, -1), (2.2, -3.0), (2.5, -5.6), (1.9, -8.2), (0.9, -9.6), (0.5, -11.0), (-0.3, -9.6),
               (-1.6, -8.6), (-3.2, -6.8), (-3.4, -5.6), (-2.5, -4.9), (-1.0, -5.4), (-0.5, -4.4), (-1.6, -2.6)]
        head = c.poly_mask([(x + px * s, y + py * s) for px, py in pts])
        outlined(c, head | base, fam, shade, 1.6, 0.7)
        c.paint(c.circle(x - 0.7 * s, y - 7.7 * s, 0.45 * s), UMBER, 1.0, 1.7)
        c.paint(c.line_mask([(x + 1.3 * s, y - 8.6 * s), (x + 2.2 * s, y - 5.0 * s)], 0.6 * s), fam, min(1.0, shade + 1 / 3), 1.7)
    else:
        skirt = c.poly_mask([(x - 2.8 * s, y), (x + 2.8 * s, y), (x + 1.1 * s, y - 6.2 * s), (x - 1.1 * s, y - 6.2 * s)])
        bodice = c.poly_mask([(x - 1.1 * s, y - 6.2 * s), (x + 1.1 * s, y - 6.2 * s), (x + 1.4 * s, y - 8.0 * s),
                              (x - 1.4 * s, y - 8.0 * s)])
        head = c.circle(x, y - 9.2 * s, 1.25 * s)
        crown = c.poly_mask([(x - 1.3 * s, y - 9.8 * s), (x - 1.5 * s, y - 11.8 * s), (x - 0.6 * s, y - 10.8 * s),
                             (x, y - 12.2 * s), (x + 0.6 * s, y - 10.8 * s), (x + 1.5 * s, y - 11.8 * s), (x + 1.3 * s, y - 9.8 * s)])
        outlined(c, skirt | bodice | head | crown, fam, shade, 1.6, 0.7)
        c.paint(head & (Y > y - 9.8 * s), PEARL, 1 / 3 if fam != PEARL else 0.0, 1.7)
        c.paint(crown, SAFFRON, 1 / 3, 1.7)
        c.paint(c.line_mask([(x - 1.0 * s, y - 7.4 * s), (x - 2.6 * s, y - 5.0 * s)], 0.6 * s)
                | c.line_mask([(x + 1.0 * s, y - 7.4 * s), (x + 2.6 * s, y - 5.0 * s)], 0.6 * s), fam, min(1.0, shade + 1 / 3), 1.65)


def lookingglass():
    """Carroll, Through the Looking-Glass (1871): the country laid out like a great chessboard, little
    brooks running straight across it and green hedges between, with the Red and White Queens, knights
    and castles as tall as people, and Alice setting out across the squares."""
    c = Canvas(44, 44)
    X, Y = c.X, c.Y
    tx, ty = np.floor(X).astype(int), np.floor(Y).astype(int)
    top = 6
    # sky and a line of far hills
    c.paint(ALL(c), LAPIS, np.where(Y < 3, 1 / 3, 0.0))
    c.paint(Y > 3.5 + 1.3 * np.sin(X * 0.45) + 0.6 * np.sin(X * 1.3), FERN, 1.0)
    for (hx, hy) in ((6.5, 3.6), (19.0, 2.8), (31.5, 3.4), (39.5, 2.6)):
        c.paint(c.circle(hx, hy, 1.4), FERN, 2 / 3, 1.1)
    # the board: squares of wheat and meadow, hedges between columns, brooks between rows
    board = ty >= top
    light = ((tx + 2) // 5 + (ty - top) // 4) % 2 == 0
    c.paint(board & light, SAFFRON, np.where(ty % 2 == 0, 1 / 3, 0.0))
    c.paint(board & ~light, FERN, 0.0)
    hedge = board & (tx % 5 == 3)
    c.paint(hedge, FERN, 1.0)
    brook = board & ((ty - top) % 4 == 0)
    c.paint(brook, LAPIS, np.where((tx + ty) % 4 == 0, 0.0, 2 / 3))
    # little bridges where some hedges meet the brooks
    for by in range(top, 44, 4):
        for hx in range(3, 44, 5):
            if (hx // 5 + by // 4) % 2 == 0:
                c.paint(rect(c, hx - 1, by, hx + 2, by + 1), UMBER, 1 / 3, 1.2)
    # the chessmen, as tall as people
    chess_figure(c, 'castle', 39.5, 15.0, 0.95, EMBER, 1 / 3)
    chess_figure(c, 'knight', 7.0, 18.0, 1.05, PEARL, 1 / 3)
    chess_figure(c, 'queen', 31.0, 26.0, 1.35, PEARL, 1 / 3)
    chess_figure(c, 'queen', 11.0, 38.0, 1.45, EMBER, 1 / 3)
    chess_figure(c, 'knight', 36.0, 42.5, 1.05, EMBER, 2 / 3)
    chess_figure(c, 'castle', 21.0, 15.0, 0.85, PEARL, 1 / 3)
    # Alice walking across the squares: fair hair, blue dress, white pinafore
    ax, ay = 22.5, 36.0
    girl = c.poly_mask([(ax - 2.2, ay - 1.0), (ax + 2.2, ay - 1.0), (ax + 0.9, ay - 5.0), (ax - 0.9, ay - 5.0)])
    girl |= c.circle(ax, ay - 6.3, 1.25) | c.line_mask([(ax - 0.6, ay - 1.0), (ax - 0.8, ay)], 0.55)
    girl |= c.line_mask([(ax + 0.6, ay - 1.0), (ax + 1.0, ay)], 0.55)
    outlined(c, girl, LAPIS, 1 / 3, 1.6)
    c.paint(c.poly_mask([(ax - 1.0, ay - 1.4), (ax + 1.0, ay - 1.4), (ax + 0.6, ay - 4.6), (ax - 0.6, ay - 4.6)]), PEARL, 0.0, 1.7)
    c.paint(c.circle(ax, ay - 6.3, 1.25) & (Y > ay - 6.6), EMBER, 0.0, 1.7)
    c.paint((c.circle(ax, ay - 6.5, 1.35) & (Y < ay - 6.6)) | rect(c, ax - 1.4, ay - 6.6, ax - 0.8, ay - 4.6)
            | rect(c, ax + 0.8, ay - 6.6, ax + 1.4, ay - 4.6), SAFFRON, 1 / 3, 1.7)
    frame(c)
    return encode(c.to_tiles())


def fish(c, x, y, s, fam, d=1, shade=1 / 3, prio=1.5):
    """A small fish facing right (d=1) or left (d=-1)."""
    m = ellipse(c, x, y, 1.4 * s, 0.75 * s)
    m |= c.poly_mask([(x - 1.0 * s * d, y), (x - 2.3 * s * d, y - 0.9 * s), (x - 2.3 * s * d, y + 0.9 * s)])
    c.paint(m, fam, shade, prio)
    c.paint(c.circle(x + 0.7 * s * d, y - 0.15 * s, 0.25 * s + 0.1), UMBER, 1.0, prio + 0.1)


def pinocchio():
    """Collodi, The Adventures of Pinocchio (1883): deep inside the Terrible Dogfish, under the arches
    of its ribs, Pinocchio finds old Geppetto at a little table lit by a candle in a green bottle; far
    off, the sleeping monster's open jaws let in the moonlight over the sea."""
    c = Canvas(44, 42)
    X, Y = c.X, c.Y
    tx, ty = np.floor(X).astype(int), np.floor(Y).astype(int)
    vx, vy, fl = 22.0, 17.0, 21.5
    t = np.hypot((X - vx) / 1.3, Y - vy)
    # the vault of the belly: red flesh between great pale ribs, each with a dark shadow behind it
    c.paint(ALL(c), EMBER, np.where(t < 11, 1.0, 2 / 3))
    for k, tk in enumerate((8.8, 13.0, 18.8, 26.5, 36.0)):
        w = 0.6 + 0.07 * tk
        c.paint((t > tk) & (t < tk + w), PEARL, np.where(X < vx, 1 / 3, 2 / 3) if k < 2 else np.where(X < vx, 0.0, 1 / 3), 1.2)
        c.paint((t > tk + w) & (t < tk + w + 0.45 + 0.04 * tk), UMBER, 1.0, 1.1)
        for hx in np.arange(vx - tk * 1.3 + 2.5, vx + tk * 1.3 - 2.0, 6.0 + k):
            hy = vy - math.sqrt(max(0.0, (tk + 0.3) ** 2 - ((hx - vx) / 1.3) ** 2))
            if 1.5 < hy < fl - 4 and abs(hx - vx) > 5:
                c.paint(c.line_mask([(hx, hy + 0.3), (hx + 0.4, hy + 2.0 + 0.3 * k), (hx, hy + 3.2 + 0.4 * k)], 0.8), FERN, 2 / 3, 1.3)
    # the open jaws: a lens of moonlit sky between two rows of great teeth
    half = 3.6 * np.sqrt(np.clip(1 - ((X - vx) / 7.5) ** 2, 0, 1))
    mouth = (np.abs(Y - (vy - 1.0)) < half)
    c.paint(mouth, LAPIS, np.where(Y < vy, 1.0, 2 / 3), 1.3)
    c.paint(c.circle(vx + 2.6, vy - 2.2, 1.2), SAFFRON, 0.0, 1.5)
    for k in range(7):
        x0 = vx - 6.0 + k * 2.0
        h = 3.6 * math.sqrt(max(0.0, 1 - ((x0 - vx) / 7.5) ** 2))
        c.paint(c.poly_mask([(x0 - 0.9, vy - 1 - h - 0.5), (x0 + 0.9, vy - 1 - h - 0.5), (x0, vy - 1 - h + 2.0)]), PEARL, 0.0, 1.6)
        c.paint(c.poly_mask([(x0 - 0.9, vy - 1 + h + 0.5), (x0 + 0.9, vy - 1 + h + 0.5), (x0, vy - 1 + h - 1.6)]), PEARL, 1 / 3, 1.6)
    # sea water washed in across the floor, with the moon's path running from the jaws
    water = Y > fl
    c.paint(water, LAPIS, np.where((np.sin(X * 0.7 + np.floor(Y) * 2.1) > 0.75) & (ty % 2 == 1), 1 / 3, 2 / 3))
    c.paint(water & (np.abs(X - vx - 0.5) < 0.6 + 0.25 * (Y - fl)) & (ty % 2 == 0) & (Y < 31), SAFFRON, 1 / 3, 1.2)
    # the dry bank in the foreground, a few rocks and the wreck of a boat
    bank = ellipse(c, 21.0, 37.0, 15.5, 3.9)
    c.paint(bank, UMBER, np.where(np.sin(X * 0.9 + Y * 1.7) > 0.4, 1 / 3, 0.0), 1.1)
    for (qx, qy, qr) in ((9.0, 37.5, 1.3), (28.0, 38.5, 1.5), (34.0, 36.0, 1.1)):
        c.paint(ellipse(c, qx, qy, qr * 1.6, qr * 0.6), LAPIS, 1 / 3, 1.15)
    for (qx, qy) in ((14.5, 37.5), (31.5, 38.0), (22.5, 38.5), (6.5, 36.5), (19.0, 40.5)):
        c.paint(ellipse(c, qx, qy, 0.9, 0.6), PEARL, 2 / 3, 1.2)
    wreck = c.poly_mask([(1.2, 24.0), (8.0, 28.5), (7.0, 33.5), (2.5, 34.5), (1.2, 32.0)])
    c.paint(wreck, UMBER, np.where(tx % 2 == 0, 2 / 3, 1.0), 1.3)
    c.paint(c.line_mask([(3.5, 29.5), (6.5, 17.0)], 0.8), UMBER, 2 / 3, 1.35)
    for (rx_, ry_, rr) in ((40.0, 33.0, 1.4), (33.5, 25.5, 1.0), (12.0, 24.5, 1.0)):
        c.paint(ellipse(c, rx_, ry_, rr * 1.5, rr), UMBER, 2 / 3, 1.3)
    r = random.Random(29)
    for (fx_, fy_, fam) in ((13.0, 28.0, SAFFRON), (30.0, 29.0, FERN), (38.5, 29.0, PEARL), (8.5, 38.0, SAFFRON),
                            (36.5, 39.5, FERN), (40.0, 24.0, SAFFRON), (5.0, 22.5, PEARL), (27.0, 23.0, FERN),
                            (17.0, 23.5, PEARL), (34.0, 21.5, SAFFRON), (2.8, 40.0, FERN), (40.5, 37.5, PEARL)):
        fish(c, fx_, fy_, 0.85, fam, r.choice((-1, 1)), 1 / 3)
    # the little table, the candle in its green glass bottle and its warm glow
    c.paint(c.circle(21.0, 21.8, 2.0), SAFFRON, 1 / 3, 1.25)
    c.paint(rect(c, 16.0, 28.6, 26.0, 30.0), UMBER, 0.0, 1.5)
    for lx in (17.0, 25.0):
        c.paint(rect(c, lx - 0.5, 30.0, lx + 0.5, 35.0), UMBER, 0.0, 1.5)
    c.paint(ellipse(c, 21.0, 27.0, 1.2, 1.6) | rect(c, 20.5, 24.6, 21.5, 26.0), FERN, 2 / 3, 1.7)
    c.paint(rect(c, 20.55, 22.4, 21.45, 24.6), PEARL, 0.0, 1.75)
    c.paint(ellipse(c, 21.0, 21.6, 0.6, 1.0), SAFFRON, 0.0, 1.8)
    # Geppetto: an old man all white with age, sitting at the table (green coat, white hair and beard)
    gx, gy = 12.5, 22.6
    c.paint(rect(c, gx - 2.0, 31.0, gx + 2.0, 35.5) | rect(c, gx + 1.0, 30.0, gx + 4.0, 31.5), FERN, 1.0, 1.45)
    c.paint(ellipse(c, gx, gy + 5.8, 3.0, 4.0) | c.line_mask([(gx + 1.5, gy + 4.8), (16.8, 28.2)], 1.2), FERN, 2 / 3, 1.5)
    c.paint(c.circle(gx - 0.3, gy, 2.3), PEARL, 1 / 3, 1.55)
    c.paint(ellipse(c, gx + 1.0, gy + 0.2, 1.4, 1.4), EMBER, 0.0, 1.6)
    c.paint(ellipse(c, gx + 0.8, gy + 2.3, 1.7, 1.3), PEARL, 0.0, 1.65)
    c.paint(c.circle(gx + 1.5, gy - 0.1, 0.42), UMBER, 1.0, 1.8)
    # Pinocchio, the wooden puppet (pointed cap, long nose, jointed limbs), running up with arms out
    px_, py_ = 31.0, 36.0
    wood = (c.line_mask([(px_ - 0.6, py_ - 6.0), (px_ - 1.8, py_)], 1.0) | c.line_mask([(px_ + 0.6, py_ - 6.0), (px_ + 2.0, py_)], 1.0)
            | c.line_mask([(px_ - 1.2, py_ - 10.4), (px_ - 4.4, py_ - 12.4)], 0.9) | c.line_mask([(px_ + 1.2, py_ - 10.4), (px_ + 4.2, py_ - 8.0)], 0.9)
            | c.circle(px_, py_ - 13.2, 1.8) | c.line_mask([(px_ - 1.4, py_ - 13.0), (px_ - 5.4, py_ - 12.6)], 0.65))
    c.paint(wood, SAFFRON, 1.0, 1.6)
    suit = c.poly_mask([(px_ - 1.6, py_ - 11.0), (px_ + 1.6, py_ - 11.0), (px_ + 2.0, py_ - 5.6), (px_ - 2.0, py_ - 5.6)])
    c.paint(suit, PEARL, 1 / 3, 1.6)
    c.paint(suit & (c.circle(px_ - 0.6, py_ - 9.4, 0.6) | c.circle(px_ + 0.8, py_ - 7.2, 0.6)), EMBER, 1 / 3, 1.65)
    c.paint(c.poly_mask([(px_ - 1.9, py_ - 14.4), (px_ + 1.9, py_ - 14.4), (px_ + 0.6, py_ - 18.6)]), PEARL, 0.0, 1.65)
    c.paint(c.circle(px_ - 0.8, py_ - 13.6, 0.4), UMBER, 1.0, 1.8)
    frame(c)
    return encode(c.to_tiles())


SCENES = {
    "yellowbrick": yellowbrick, "riverbank": riverbank,
    "railwaychildren": railwaychildren, "secretgarden": secretgarden,
    "teaparty": teaparty, "wolfpack": wolfpack,
    "lookingglass": lookingglass, "pinocchio": pinocchio,
}
