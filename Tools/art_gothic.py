"""Gothic & Mystery pack: eight iconic scenes from Gothic and mystery classics (all public domain), drawn
with the supersampled Canvas of art.py (a tile's colour family comes from the dominant object under it,
its tone from the shading). Spooky but family-friendly; book scenes only, no film designs, no lettering.

Gentle: Poe's raven, the Headless Horseman, the Hound of the Baskervilles, the bells of Notre-Dame.
Challenge: Castle Dracula, the Arctic pursuit from Frankenstein.
Master (busy, every colour in many islands): Wells's Martian tripods, the Paris Opera's chandelier.
"""
import math
import random

import numpy as np
from scipy import ndimage

from art import Canvas, LAPIS, SAFFRON, FERN, EMBER, UMBER, PEARL, SS, encode, smoothstep
from art_scenes import ALL, ellipse, rect, tube, frame, sky, cloud, smooth_noise


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def grow(mask, r):
    """The mask grown by r tiles (for glows and outlines round a silhouette)."""
    rp = max(1, int(round(r * SS)))
    yy, xx = np.mgrid[-rp:rp + 1, -rp:rp + 1]
    return ndimage.binary_dilation(mask, structure=(xx * xx + yy * yy) <= rp * rp)


def sprite(c, x0, y0, rows, fam, shade, prio=1.7):
    """Paint a tile-exact pixel sprite ('#' = filled) with its top-left tile at (x0, y0)."""
    m = np.zeros_like(c.X, bool)
    for j, row in enumerate(rows):
        for i, ch in enumerate(row):
            if ch == '#':
                m |= rect(c, x0 + i, y0 + j, x0 + i + 1, y0 + j + 1)
    c.paint(m, fam, shade, prio)


BAT = ["#.....#", "##.#.##", ".#####.", "...#..."]   # a pixel bat, wings raised
HORSE = ["..#........", ".###.......", "##.##......", "...##......", "...#######.", "...########",
         "...#.#..#.#", "..#..#..#..#"]   # a pixel horse trotting to the left
GIANT = ["....##...", "....##...", "..#####..", ".########", "##.####..", "#..####..", "...####..", "...####..",
         "...####..", "..##..##."]   # a tall figure in a long coat, cloak flying behind, one arm out to the reins
DOG = ["....##", "#.####", ".####.", ".#..#."]   # a sledge dog running to the right


# ---------------------------------------------------------------------------
# Gentle
# ---------------------------------------------------------------------------

def raven():
    """Poe's chamber at midnight: the black raven on the pale bust of Pallas just above the chamber door,
    a velvet armchair at the left, an oil lamp on a little table at the right, red curtains at the corners."""
    c = Canvas(36, 46)
    X, Y = c.X, c.Y
    # deep-blue wall, lit up round the lamp
    lamp = np.hypot(X - 30.5, (Y - 27.0) * 0.9)
    c.paint(ALL(c), LAPIS, np.clip(1.0 - 0.6 * np.exp(-(lamp / 8.5) ** 2), 0, 1))
    # floorboards, a red rug and the raven's shadow "floating on the floor"
    c.paint(Y >= 40.5, UMBER, np.where(np.sin(Y * 3.2) > 0.6, 1.0, 0.67))
    c.paint(ellipse(c, 17.5, 43.8, 15.5, 2.6), EMBER, np.where(ellipse(c, 17.5, 43.8, 13.8, 1.7), 0.67, 0.33))
    for fx in (1.6, 33.4):
        c.paint(rect(c, fx - 0.6, 42.4, fx + 0.6, 45.2), SAFFRON, 0.33, 1.25)
    shadow = ellipse(c, 14.0, 43.5, 4.2, 0.9) | c.poly_mask([(10.5, 43.4), (6.5, 42.6), (7.0, 44.2)])
    c.paint(shadow, UMBER, 1.0, 1.3)
    # curtains swept to the corners, with gold tie-backs
    folds = np.where(np.sin(X * 1.7 + Y * 0.25) > 0.2, 0.67, 0.33)
    for side in (-1, 1):
        ox = 18 + side * 17
        cur = c.poly_mask([(ox, 1), (ox - side * 8.5, 1), (ox - side * 6.0, 6.5), (ox - side * 3.5, 12.5),
                           (ox - side * 2.6, 19.5), (ox, 22)])
        c.paint(cur, EMBER, folds)
        c.paint(ellipse(c, ox - side * 3.0, 14.5, 1.4, 0.8), SAFFRON, 0.33, 1.5)
    # the chamber door: a stone frame, a panelled door and a brass knob
    c.paint(rect(c, 10, 23, 26, 40.5), PEARL, 0.67, 1.1)
    c.paint(rect(c, 11.4, 24.4, 24.6, 40.5), UMBER, 0.33, 1.1)
    for (x0, y0, x1, y1) in ((12.6, 25.6, 17.4, 31.6), (18.6, 25.6, 23.4, 31.6), (12.6, 33.2, 17.4, 39.6), (18.6, 33.2, 23.4, 39.6)):
        c.paint(rect(c, x0, y0, x1, y1), UMBER, 0.67, 1.15)
    c.paint(c.circle(22.6, 32.4, 0.65), SAFFRON, 0.33, 1.8)
    c.paint(rect(c, 8.5, 21.4, 27.5, 23.2), PEARL, 0.4, 1.2)                  # the lintel shelf
    # the bust of Pallas in profile (facing left): plinth, draped shoulders, neck, head, crested helmet
    lit = np.where(X > 18.4, 0.0, 0.33)
    bust = (rect(c, 14.6, 20.2, 21.4, 21.5) | rect(c, 15.8, 19.0, 20.2, 20.3)
            | (ellipse(c, 18, 18.4, 5.8, 2.6) & (Y < 19.1)) | rect(c, 16.8, 14.6, 19.4, 17)
            | c.circle(18.2, 13.6, 2.5) | c.poly_mask([(15.9, 13.0), (14.7, 14.6), (16.0, 14.8)])
            | (ellipse(c, 18.6, 12.6, 3.0, 2.4) & (Y < 13.2)))
    c.paint(bust, PEARL, lit, 1.3)
    c.paint(c.poly_mask([(15.0, 12.4), (19.0, 12.4), (19.0, 13.4), (15.2, 13.2)]), PEARL, 0.67, 1.35)  # helmet brow
    c.paint(c.line_mask([(15.0, 17.6), (18.0, 19.0), (21.0, 17.4)], 0.6), PEARL, 0.67, 1.35)          # drapery fold
    # the raven: body, long tail, head with a heavy beak, gripping feet, one gleaming eye
    rv = (ellipse(c, 17.8, 6.8, 4.6, 2.6, -0.32) | c.poly_mask([(14.6, 7.2), (10.0, 12.2), (12.4, 12.6), (16.6, 9.0)])
          | c.circle(22.4, 3.7, 1.9) | c.poly_mask([(23.6, 2.7), (27.6, 4.4), (23.8, 5.2)])
          | c.circle(21.2, 5.2, 1.6)
          | c.line_mask([(17.6, 8.4), (17.4, 10.4)], 0.6) | c.line_mask([(19.6, 8.2), (19.8, 10.4)], 0.6))
    c.paint(rv, UMBER, 1.0, 1.6)
    c.paint(ellipse(c, 16.8, 7.0, 3.0, 1.3, -0.32), UMBER, 0.67, 1.65)       # folded wing sheen
    c.paint(c.circle(22.8, 3.3, 0.55), SAFFRON, 0.0, 2.0)
    # the velvet armchair at the left, side-on: tall buttoned back, rolled arm, wooden legs
    c.paint(rect(c, 1.0, 26.5, 4.4, 37.4) | c.circle(2.7, 26.5, 1.7), EMBER, 0.67, 1.1)
    for by in (28.0, 30.5):
        c.paint(c.circle(2.7, by, 0.5), EMBER, 1.0, 1.2)
    c.paint(rect(c, 1.0, 33.0, 10.6, 37.4), EMBER, 0.67, 1.12)
    c.paint(rect(c, 1.0, 31.2, 10.0, 33.0) | c.circle(10.0, 32.1, 1.3), EMBER, 0.33, 1.15)
    c.paint(c.circle(10.0, 32.1, 0.55), EMBER, 1.0, 1.3)
    c.paint(rect(c, 1.0, 37.4, 10.6, 38.6), UMBER, 0.67, 1.2)
    c.paint(rect(c, 1.4, 38.6, 2.6, 40.8) | rect(c, 9.2, 38.6, 10.4, 40.8), UMBER, 1.0, 1.3)
    # the oil lamp on a small round table, and a book of forgotten lore
    c.paint(ellipse(c, 30.5, 34.2, 4.2, 0.9) | rect(c, 29.9, 34.2, 31.1, 40.5) | ellipse(c, 30.5, 40.3, 2.4, 0.6),
            UMBER, 0.67, 1.2)
    c.paint(c.poly_mask([(28.4, 33.5), (32.6, 33.5), (31.6, 30.6), (29.4, 30.6)]) | ellipse(c, 30.5, 30.2, 2.2, 1.3),
            SAFFRON, 0.67, 1.3)
    c.paint(rect(c, 29.6, 23.8, 31.4, 29.0) | ellipse(c, 30.5, 26.8, 1.5, 1.8), PEARL, 0.0, 1.3)
    c.paint(ellipse(c, 30.5, 26.4, 0.55, 1.1), SAFFRON, 0.0, 1.8)
    c.paint(rect(c, 25.8, 32.9, 28.4, 33.6), PEARL, 0.33, 1.4)
    frame(c)
    return encode(c.to_tiles())


def horseman():
    """Sleepy Hollow by moonlight: the Headless Horseman galloping across the wooden bridge, his cloak
    streaming against the full moon and the glowing jack-o'-lantern held high; a bare tree at the left and
    the white church on its hill."""
    c = Canvas(48, 36)
    X, Y = c.X, c.Y
    sky(c, 0.98, 0.62, horizon=29)
    c.paint(c.circle(16.0, 10.5, 8.6), PEARL, np.where(smooth_noise(c, 3, 0.9) > 0.35, 0.33, 0.0), 1.1)
    # the hill with the church: white tower and spire, a long nave with arched windows
    c.paint(Y > 20.5 + 0.07 * (X - 45) ** 2, FERN, 0.9)
    c.paint(rect(c, 39.6, 17.0, 46.6, 21.5), PEARL, 0.33, 1.2)
    c.paint(c.poly_mask([(39.6, 17.2), (46.6, 17.2), (45.8, 15.2), (40.0, 15.2)]), PEARL, 0.67, 1.2)
    c.paint(rect(c, 36.8, 10.6, 39.8, 21.5) | c.poly_mask([(36.4, 10.8), (40.2, 10.8), (38.3, 4.6)]), PEARL, 0.0, 1.25)
    for wx in (41.6, 43.6, 45.4):
        c.paint(rect(c, wx - 0.5, 18.2, wx + 0.5, 20.2) | c.circle(wx, 18.2, 0.5), UMBER, 0.67, 1.6)
    c.paint(rect(c, 37.8, 13.0, 38.8, 15.0), UMBER, 0.67, 1.6)
    # the bridge railing (behind the horse), the creek with the moon's reflection, banks, piles and deck
    c.paint(rect(c, 0, 25.6, 48, 26.7), UMBER, 0.67, 1.2)
    for px in (4.5, 17.5, 30.5, 43.5):
        c.paint(rect(c, px - 0.55, 25.6, px + 0.55, 29.6), UMBER, 0.67, 1.2)
    c.paint(Y >= 31.3, LAPIS, np.where(np.sin(Y * 2.5 + np.sin(X * 0.7)) > 0, 0.67, 0.33))
    c.paint((Y >= 31.3) & (np.abs(X - 16.0 - 0.8 * np.sin(Y * 2.2)) < 2.2 - 0.25 * (Y - 31)), PEARL, 0.33, 1.15)
    c.paint(c.poly_mask([(0, 30), (7, 31), (4, 36), (0, 36)]) | c.poly_mask([(48, 30), (41, 31), (44, 36), (48, 36)]), FERN, 1.0)
    for px in (9.0, 37.5):
        c.paint(rect(c, px - 0.7, 31, px + 0.7, 36), UMBER, 0.67, 1.2)
    c.paint(rect(c, 0, 29.5, 48, 31.4), UMBER, np.where((X % 1.6) < 0.4, 0.67, 0.33), 1.2)
    # the bare tree reaching in from the left
    tree = (tube(c, [(3.4, 36), (3.7, 27), (4.2, 18), (5.6, 10.5)], 3.2, 1.5) | tube(c, [(4.2, 19), (7.0, 16.6), (8.6, 15.8)], 1.4, 0.8)
            | tube(c, [(5.4, 11), (8.0, 7.2), (10.2, 5.6)], 1.2, 0.7) | tube(c, [(4.8, 14.5), (2.0, 9), (1.8, 4.5)], 1.3, 0.8)
            | tube(c, [(5.6, 11), (5.4, 5.5), (6.4, 2.0)], 1.0, 0.7) | tube(c, [(3.8, 25), (1.2, 22.0)], 1.1, 0.8))
    c.paint(tree, UMBER, 1.0, 1.3)
    # the black horse in a flying gallop, facing right: haunch, barrel, chest, neck stretched forward,
    # ears pricked, forelegs reaching, hind legs thrown back, tail streaming
    horse = (ellipse(c, 15.4, 19.0, 3.6, 3.5) | ellipse(c, 21.0, 19.4, 6.4, 3.4, -0.04) | ellipse(c, 26.0, 18.8, 3.2, 3.4)
             | tube(c, [(26.2, 18.0), (28.8, 14.6), (30.4, 12.4)], 5.0, 3.0) | tube(c, [(30.2, 12.2), (34.0, 14.4)], 3.0, 1.8)
             | c.poly_mask([(29.4, 11.8), (29.8, 9.6), (31.0, 11.4)])
             | tube(c, [(26.6, 21.0), (30.0, 22.8), (33.6, 22.2)], 1.6, 1.0) | tube(c, [(25.4, 21.6), (27.8, 24.4), (31.0, 25.6)], 1.6, 1.0)
             | tube(c, [(15.0, 21.0), (11.6, 23.4), (8.0, 23.8)], 1.9, 1.0) | tube(c, [(16.6, 21.6), (14.0, 24.6), (10.8, 26.0)], 1.9, 1.0)
             | tube(c, [(12.8, 17.2), (9.6, 16.2), (6.8, 17.2), (4.8, 16.4)], 2.2, 0.8))
    c.paint(horse, UMBER, 1.0, 1.5)
    c.paint(c.circle(31.4, 12.6, 0.45), EMBER, 0.33, 1.6)                       # a red eye
    # the headless rider: cloak streaming back with its red lining, dark coat, a leg in the stirrup,
    # shoulders and collar with no head, one arm holding the glowing jack-o'-lantern high
    c.paint(c.poly_mask([(20.0, 10.4), (14.0, 8.6), (9.4, 11.2), (12.2, 12.4), (9.0, 15.0), (15.4, 15.4), (19.6, 15.6)]), EMBER, 1.0, 1.4)
    rider = (tube(c, [(20.4, 16.6), (21.2, 11.4)], 3.2, 3.4) | ellipse(c, 21.2, 11.0, 2.3, 1.0)
             | tube(c, [(20.8, 16.8), (23.0, 19.0), (22.4, 21.6)], 1.6, 1.2) )
    c.paint(rider, UMBER, 0.33, 1.55)
    c.paint(rect(c, 20.4, 9.6, 22.0, 10.6), EMBER, 0.67, 1.6)                   # the empty collar
    c.paint(c.circle(26.5, 4.5, 3.9), LAPIS, 0.33, 1.3)                          # glow on the sky
    c.paint(ellipse(c, 26.5, 4.5, 3.0, 2.6), EMBER, 0.33, 1.7)
    c.paint(rect(c, 25, 3, 26, 4) | rect(c, 27, 3, 28, 4) | rect(c, 25, 5, 28, 6), SAFFRON, 0.0, 1.9)  # carved face
    c.paint(rect(c, 26.0, 1.2, 27.0, 2.2), FERN, 0.67, 1.8)
    c.paint(tube(c, [(22.2, 11.2), (24.0, 9.0), (25.2, 7.2)], 1.9, 1.7), UMBER, 0.33, 1.85)   # the arm raised
    frame(c)
    return encode(c.to_tiles())


def hound():
    """The Grimpen moor at night: the huge hound bounding along a ridge with fire bursting from its open
    jaws and its outline flickering with flame, a granite tor under the full moon, mist over the mire, and
    the lit windows of Baskerville Hall far off."""
    c = Canvas(48, 36)
    X, Y = c.X, c.Y
    sky(c, 0.98, 0.6, horizon=24)
    c.paint(c.circle(8.5, 7.0, 6.3), LAPIS, 0.33, 1.0)
    c.paint(c.circle(8.5, 7.0, 4.9), PEARL, np.where(smooth_noise(c, 8, 1.1) > 0.4, 0.33, 0.0), 1.2)
    # far moor with the long dark hall among trees, then the near moor with mire pools
    c.paint(Y > 22.5 + 0.7 * np.sin(X * 0.22 + 1), LAPIS, 0.8)
    c.paint(ellipse(c, 47.0, 21.0, 2.0, 2.4), FERN, 1.0, 1.2)
    hall = rect(c, 37, 20, 46, 24) | rect(c, 40, 16, 43, 20) | c.poly_mask([(39.6, 16.2), (43.4, 16.2), (41.5, 13.6)])
    c.paint(hall, UMBER, 1.0, 1.3)
    for (wx, wy) in ((38, 21), (44, 21), (41, 17), (41, 21)):
        c.paint(rect(c, wx, wy, wx + 1, wy + 1 + (wx == 41 and wy == 21)), SAFFRON, 0.0, 1.8)
    near = Y > 25 + 0.8 * np.sin(X * 0.3)
    c.paint(near, UMBER, np.where(smooth_noise(c, 4, 0.7) > 0.1, 0.33, 0.67))
    for (px, py, rx, ry) in ((35, 33.0, 6.0, 1.2), (44.5, 29.4, 3.4, 0.9)):
        c.paint(ellipse(c, px, py, rx, ry), LAPIS, 0.33, 1.1)
    # a bank of mist lying along the foot of the ridge
    c.paint((np.abs(Y - 26.4 - 0.8 * np.sin(X * 0.25)) < 1.0) & (X > 30), PEARL, 0.0, 1.05)
    # the ridge in the foreground and the granite tor
    top = 23.0 + 13 * smoothstep(27, 42, X) + 0.4 * np.sin(X * 0.8)
    c.paint(Y > top, UMBER, np.where(np.sin(X * 1.3 + Y) > 0.5, 0.67, 1.0))
    for (x0, y0, x1, y1, sh) in ((1.4, 18.6, 7.2, 23.4, 0.67), (2.4, 15.4, 8.6, 18.8, 0.33),
                                 (3.6, 12.8, 7.6, 15.6, 0.67), (6.8, 19.6, 11.0, 23.4, 0.33)):
        c.paint(rect(c, x0 + 0.15, y0 + 0.15, x1 - 0.15, y1 - 0.15), PEARL, sh, 1.15)
    # the hound in mid-bound, facing right: deep chest, tucked waist, haunch, head thrust forward with the
    # jaws wide open, ears flattened, forelegs reaching, hind legs thrown back, tail streaming
    hd = (ellipse(c, 24.8, 15.0, 4.0, 4.0) | ellipse(c, 20.4, 14.6, 5.0, 3.0, -0.06) | ellipse(c, 16.6, 14.2, 3.4, 3.3)
          | tube(c, [(26.4, 13.6), (29.4, 11.8)], 5.0, 4.0) | ellipse(c, 31.0, 11.4, 3.0, 2.6)
          | tube(c, [(32.0, 10.8), (36.0, 11.4)], 2.4, 2.0) | tube(c, [(31.6, 13.2), (35.2, 14.8)], 1.8, 1.4)
          | c.poly_mask([(29.6, 9.4), (27.2, 9.6), (28.6, 12.4)])
          | tube(c, [(26.4, 17.6), (29.0, 20.0), (32.2, 20.6)], 2.4, 1.6) | tube(c, [(24.8, 18.4), (25.8, 21.2), (27.8, 23.0)], 2.4, 1.6)
          | tube(c, [(15.4, 16.4), (12.6, 19.0), (9.6, 19.8)], 2.6, 1.6) | tube(c, [(17.0, 16.8), (15.6, 20.2), (13.4, 22.8)], 2.6, 1.6)
          | tube(c, [(13.4, 12.8), (10.6, 11.6), (8.4, 12.2)], 1.9, 1.0))
    c.paint(grow(hd, 1.0) & ~hd, SAFFRON, 0.0, 1.45)
    c.paint(hd, UMBER, 1.0, 1.5)
    c.paint(ellipse(c, 27.4, 12.4, 1.3, 2.4, 0.3), UMBER, 0.67, 1.55)                 # the hackles
    c.paint(c.circle(31.6, 10.4, 0.7), SAFFRON, 0.0, 2.0)                             # burning eye
    c.paint(c.poly_mask([(32.2, 12.4), (37.6, 12.0), (39.0, 13.8), (36.6, 15.8), (33.0, 13.8)]), EMBER, 0.33, 1.9)  # fire
    c.paint(c.poly_mask([(33.0, 12.6), (37.0, 12.6), (35.0, 14.0)]), SAFFRON, 0.0, 1.95)
    frame(c)
    return encode(c.to_tiles())


def notredame():
    """Notre-Dame at dusk: the twin towers with chimeras on their corners, the open colonnade between them,
    the rose window, the gallery of kings and three deep portals; in the open belfry the great bell swings
    with the little bell-ringer clinging to it."""
    c = Canvas(38, 46)
    X, Y = c.X, c.Y
    tx = np.floor(X).astype(int)
    # dusk sky: deep blue above, paling towards the gallery
    c.paint(ALL(c), LAPIS, np.clip(1.0 - Y / 19, 0, 1))
    # the stone facade: two towers on a broad front; buttresses and string courses in darker stone
    front = rect(c, 1.5, 7.5, 13.5, 46) | rect(c, 24.5, 7.5, 36.5, 46) | rect(c, 1.5, 20.5, 36.5, 46)
    c.paint(front, PEARL, 0.33)
    for bx in (1.5, 12.5, 24.5, 35.5):
        c.paint(rect(c, bx, 7.5, bx + 1.0, 46), PEARL, 0.67, 1.05)
    for (y0, y1) in ((20.5, 21.5), (30.0, 33.0)):
        c.paint(rect(c, 1.5, y0, 36.5, y1), PEARL, 0.67, 1.1)
    # the gallery of kings: statues in a row of niches
    c.paint(rect(c, 2.5, 30.6, 35.5, 32.6) & ((tx % 2) == 1), PEARL, 1.0, 1.15)
    # tower parapets; a horned, winged chimera crouches on each outer corner, peering out over the city
    for x0 in (1.5, 24.5):
        c.paint(rect(c, x0, 6.5, x0 + 12, 7.6), PEARL, 0.67, 1.1)
    for (gx, f) in ((3.4, -1), (34.6, 1)):
        g = (ellipse(c, gx, 4.6, 1.5, 2.0) | ellipse(c, gx + f * 1.5, 3.2, 1.2, 0.9, f * 0.3)
             | c.poly_mask([(gx + f * 1.0, 2.6), (gx + f * 0.9, 0.9), (gx + f * 1.6, 2.4)])
             | c.poly_mask([(gx - f * 0.6, 3.6), (gx - f * 2.4, 1.2), (gx - f * 1.6, 4.4)]))
        c.paint(g, UMBER, 1.0, 1.6)
    # the open gallery between the towers: a row of slender columns standing against the pale sky
    c.paint(rect(c, 13.5, 15.0, 24.5, 20.5) & ((tx % 2) == 1), PEARL, 0.33, 1.2)
    c.paint(rect(c, 13.5, 19.6, 24.5, 20.5), PEARL, 0.67, 1.2)
    # the left belfry: two tall lancets
    for lx in (5.0, 10.0):
        c.paint(rect(c, lx - 1.3, 10.5, lx + 1.3, 18.5) | c.circle(lx, 10.5, 1.3), UMBER, 1.0, 1.3)
    # the right belfry thrown open: a dark arch, the beam, the great bell swinging on its yoke and the
    # little bell-ringer clinging to its shoulder
    arch = rect(c, 26.4, 11.0, 34.6, 19.4) | (ellipse(c, 30.5, 11.0, 4.1, 3.4) & (Y < 11.2))
    c.paint(arch, UMBER, 1.0, 1.3)
    c.paint(rect(c, 26.0, 9.2, 35.0, 10.2) & arch, UMBER, 0.33, 1.35)            # the beam
    ang = -0.32
    ca, sa = math.cos(ang), math.sin(ang)
    u = (X - 30.4) * ca + (Y - 10.4) * sa
    v = -(X - 30.4) * sa + (Y - 10.4) * ca
    prof = np.interp(v, [0.6, 1.4, 4.0, 5.6, 6.6, 7.2], [1.2, 1.9, 2.1, 2.6, 3.3, 3.3])   # shoulder, waist, flared lip
    bell = (v > 0.6) & (v < 7.2) & (np.abs(u) < prof)
    c.paint(bell, SAFFRON, np.where(u > 0.6, 0.67, 0.33), 1.6)
    c.paint(bell & (v > 6.2), SAFFRON, 1.0, 1.65)
    c.paint((np.abs(u) < 0.8) & (v > 7.2) & (v < 8.4), UMBER, 0.33, 1.65)         # the clapper
    rider = (c.circle(29.0, 9.6, 0.9) | ellipse(c, 28.0, 11.4, 1.1, 1.5, 0.4)
             | c.line_mask([(28.6, 10.6), (30.2, 11.6)], 0.7) | c.line_mask([(27.6, 12.6), (28.8, 13.4)], 0.7))
    c.paint(rider, EMBER, 0.33, 1.8)
    # the rose window with its radiating petals, and twin lancets in each tower
    rc = np.hypot(X - 19, Y - 25.3)
    ra = np.arctan2(Y - 25.3, X - 19)
    c.paint(rc < 5.6, PEARL, 1.0, 1.2)
    c.paint(rc < 4.8, LAPIS, np.where(np.cos(ra * 8) > 0.3, 0.33, 0.67), 1.3)
    c.paint((rc < 4.8) & (rc > 2.6) & (np.cos(ra * 8) > 0.8), PEARL, 0.67, 1.32)   # tracery
    c.paint((rc < 3.0) & (rc > 1.6), EMBER, 0.33, 1.35)
    c.paint(c.circle(19, 25.3, 1.4), SAFFRON, 0.0, 1.5)
    for lx in (5.0, 10.0, 28.0, 33.0):
        c.paint(rect(c, lx - 1.1, 23.0, lx + 1.1, 28.5) | c.circle(lx, 23.0, 1.1), UMBER, 1.0, 1.3)
    # three deep pointed portals: dark stone archivolts, a pale tympanum, dark doors split by a pier
    for (px, hw) in ((7.0, 3.6), (19.0, 4.3), (31.0, 3.6)):
        spring = 39.0
        arc = rect(c, px - hw, spring, px + hw, 45.0) | (c.circle(px - 0.4 * hw, spring, 1.4 * hw)
                                                       & c.circle(px + 0.4 * hw, spring, 1.4 * hw) & (Y < spring))
        inner = rect(c, px - hw + 1.1, spring, px + hw - 1.1, 45.0) | (c.circle(px - 0.4 * hw, spring, 1.4 * hw - 1.1)
                                                                     & c.circle(px + 0.4 * hw, spring, 1.4 * hw - 1.1) & (Y < spring))
        c.paint(arc, UMBER, 0.33, 1.15)
        c.paint(inner, PEARL, 0.33, 1.2)
        c.paint(inner & (Y > spring + 0.2), UMBER, 1.0, 1.25)
        c.paint(rect(c, px - 0.5, spring + 0.2, px + 0.5, 45.0), PEARL, 0.67, 1.3)
    c.paint(Y > 45.0, PEARL, 0.67)
    frame(c)
    return encode(c.to_tiles())


# ---------------------------------------------------------------------------
# Challenge
# ---------------------------------------------------------------------------

def dracula():
    """Castle Dracula at night: a black silhouette of slender towers and battlements with a few lit windows,
    high on a tall rocky crag against a huge moon and a deep sky; bats over the moon, a dark pine wood below
    and the calèche with its two lanterns on the winding road through the mist."""
    c = Canvas(40, 46)
    X, Y = c.X, c.Y
    tx = np.floor(X).astype(int)
    sky(c, 1.0, 0.7, horizon=40)
    c.paint(c.circle(20.5, 11.5, 11.6), LAPIS, 0.33, 1.0)                     # the moon's halo
    c.paint(c.circle(20.5, 11.5, 10.4), PEARL, np.where(smooth_noise(c, 5, 0.6) > 0.4, 0.33, 0.0), 1.1)
    for (sx, sy) in ((3, 3), (36, 3), (2, 21), (37, 24)):
        c.paint(rect(c, sx, sy, sx + 1, sy + 1), PEARL, 0.0, 1.5)
    # the crag: a tall cliff of grey columns, shadowed on the right, pinched below the walls
    crag = c.poly_mask([(7.6, 22.6), (34.4, 22.6), (33.2, 25.5), (31.0, 28), (31.8, 31), (35.0, 35.5),
                        (5.0, 35.5), (8.5, 31), (9.6, 28), (8.6, 25.5)])
    col = np.floor((X + 0.4 * np.sin(Y * 0.5)) / 1.7).astype(int)
    c.paint(crag, PEARL, np.where(col % 3 == 0, 0.67, 1.0))
    c.paint(crag & (X > 25.5 + 2.0 * np.sin(Y * 0.45)) & (Y > 24.2), UMBER, np.where(col % 2 == 0, 0.33, 0.0), 1.05)
    for pts in ([(12.4, 24.4), (13.2, 29), (12.0, 33)], [(18.6, 24.4), (19.4, 30)]):
        c.paint(c.line_mask(pts, 0.9) & crag, UMBER, 0.67, 1.2)
    # the castle: battlemented curtain wall, square towers, a spire and a turret, sharp against the moon
    merl = (tx % 2) == 0
    castle = (rect(c, 7, 19, 34, 23) | (rect(c, 7, 18, 34, 19) & merl)                    # curtain wall
              | rect(c, 7, 11, 11, 23) | (rect(c, 7, 10, 11, 11) & ~merl)                  # left tower
              | rect(c, 14, 5, 18, 23) | (rect(c, 14, 4, 18, 5) & merl)                    # the keep
              | rect(c, 21, 12, 23, 23) | c.poly_mask([(19.9, 12.4), (24.1, 12.4), (22.0, 5.0)])  # spire tower
              | rect(c, 26, 8, 30, 23) | (rect(c, 26, 7, 30, 8) & merl)                    # right tower
              | rect(c, 32, 15, 34, 23) | c.poly_mask([(30.9, 15.4), (35.1, 15.4), (33.0, 10.0)]))  # turret
    c.paint(castle, UMBER, 1.0, 1.4)
    for (wx, wy) in ((15, 7), (16, 12), (8, 13), (28, 11), (21, 15), (11, 20), (25, 20)):
        c.paint(rect(c, wx, wy, wx + 1, wy + 3), SAFFRON, 0.0, 1.7)
    # bats streaming out over the moon and the sky (tile-exact pixel bats)
    for (bx, by) in ((2, 6), (7, 2), (23, 2), (31, 4)):
        sprite(c, bx, by, BAT, UMBER, 1.0)
    # the dark pine wood below the crag, then moonlit mist lying along the valley
    tops = 31.6 + 2.4 * np.abs(((X + 0.6) / 1.5) % 2 - 1)
    c.paint(Y > tops, FERN, np.where(np.floor((X + 0.6) / 3.0) % 2 == 0, 1.0, 0.8))
    c.paint(Y > 36.4 + 0.6 * np.sin(X * 0.45), LAPIS, 0.0, 1.05)
    for (px, h) in ((35.0, 6.0), (37.6, 7.6)):
        c.paint(c.poly_mask([(px - 2.0, 42.6), (px + 2.0, 42.6), (px, 42.6 - h)]), FERN, 1.0, 1.3)
    # the road winding out of the wood and along the valley
    c.paint(c.line_mask([(14.0, 35.6), (8.0, 38.2), (16.0, 41.2)], 1.6) | (Y > 41.6 + 0.5 * np.sin(X * 0.3)),
            PEARL, np.where(Y > 44.6, 0.67, 0.33), 1.2)
    # the calèche: a black coach with a lit window, the driver high on his box and two lanterns,
    # drawn by two black horses (tile-exact sprites)
    coach = ((rect(c, 24.6, 36.4, 31.8, 40.0) | ellipse(c, 28.2, 39.6, 3.6, 1.6) | (ellipse(c, 28.2, 36.6, 3.6, 1.0) & (Y < 36.6)))
             | c.circle(23.4, 34.4, 0.75) | rect(c, 22.6, 35.0, 24.6, 38.0) | rect(c, 21.8, 37.6, 24.6, 38.4))
    c.paint(coach, UMBER, 1.0, 1.6)
    c.paint(rect(c, 27, 37, 29, 39), SAFFRON, 0.33, 1.7)
    c.paint(c.circle(25.4, 42.3, 1.3) | c.circle(30.4, 42.0, 1.6), UMBER, 0.67, 1.65)     # wheels
    for (lx, ly) in ((22.0, 39.4), (32.8, 37.6)):
        c.paint(rect(c, lx - 0.65, ly - 1.0, lx + 0.65, ly + 1.0), SAFFRON, 0.0, 1.8)
    for hx in (12, 2):
        sprite(c, hx, 36, HORSE, UMBER, 1.0)
    frame(c)
    return encode(c.to_tiles())


def arctic():
    """The Arctic chase from Frankenstein: Walton's ship locked in pack ice under the aurora; far off,
    against a great iceberg, a dog sledge carries a gigantic figure away across the ice."""
    c = Canvas(48, 36)
    X, Y = c.X, c.Y
    tx, ty = np.floor(X).astype(int), np.floor(Y).astype(int)
    hz = 16.0
    sky(c, 1.0, 0.67, horizon=hz)
    # aurora: two green curtains with red upper fringes sweeping across the sky
    for (y0, a, ph, depth, x0, x1) in ((6.0, 2.6, 0.2, 4.6, -1, 31), (2.4, 1.4, 2.4, 3.6, 24, 49)):
        top = y0 + a * np.sin(X * 0.19 + ph)
        band = (Y > top) & (Y < top + depth) & (X > x0) & (X < x1)
        c.paint(band, FERN, np.where(Y > top + depth * 0.55, 0.0, 0.33), 1.1)
        c.paint(band & (Y < top + 1.0), EMBER, 0.0, 1.15)
    for (sx, sy) in ((3, 2), (10, 3), (17, 2), (21, 12), (45, 6), (6, 14), (40, 11)):
        c.paint(rect(c, sx, sy, sx + 1, sy + 1), PEARL, 0.0, 1.6)
    # the great iceberg behind the sledge, and a lower one far off to the right
    for pts in ([(23, hz + 0.5), (25.5, 10.0), (28.5, 9.0), (31.0, 5.0), (34.5, 6.5), (36.5, 9.0), (39.5, 10.5), (41.0, hz + 0.5)],
                [(41.5, hz + 0.5), (43.0, 12.6), (47.5, 12.0), (47.5, hz + 0.5)]):
        m = c.poly_mask(pts)
        c.paint(m, PEARL, 0.0, 1.1)
        c.paint(m & (X > pts[3][0] + 1.0) & (Y > pts[3][1] + 0.35 * (X - pts[3][0])), LAPIS, 0.0, 1.15)
    # the pack ice: big floes, some split by dark open leads (tile-crisp), the rest by pressure ridges
    r = random.Random(31)
    seeds = []
    for k, (yy, step) in enumerate(((17.5, 7.0), (21.0, 8.0), (25.5, 9.0), (31.0, 10.0), (36.0, 11.0))):
        for xx in np.arange(-3 + (k % 2) * step / 2, 52, step):
            seeds.append((xx + r.uniform(-1, 1) * step / 4, yy + r.uniform(-0.5, 0.5)))
    XC, YC = tx + 0.5, ty + 0.5
    d1, d2 = np.full(X.shape, 1e9), np.full(X.shape, 1e9)
    i1, i2 = np.zeros(X.shape, int), np.zeros(X.shape, int)
    for i, (sx, sy) in enumerate(seeds):
        d = np.hypot(XC - sx, (YC - sy) * 2.0)
        closer = d < d1
        second = ~closer & (d < d2)
        d2, i2 = np.where(closer, d1, np.where(second, d, d2)), np.where(closer, i1, np.where(second, i, i2))
        i1, d1 = np.where(closer, i, i1), np.where(closer, d, d1)
    ice = Y >= hz
    c.paint(ice, PEARL, np.where(i1 % 3 == 0, 0.33, 0.0))
    c.paint(ice & (Y < hz + 1.0), LAPIS, 0.0, 1.05)
    edge = ice & ((d2 - d1) < 1.0) & (Y > hz + 1.0)
    c.paint(edge, PEARL, 0.67, 1.15)
    c.paint(edge & (((i1 * 7 + i2 * 7) % 3) == 0), LAPIS, 1.0, 1.2)
    # Walton's ship heeled in the ice: hull, three masts with furled sails, bowsprit, stern lights
    hull = c.poly_mask([(1.8, 19.4), (22.5, 18.2), (20.6, 25.0), (5.0, 25.4)])
    c.paint(grow(hull, 1.2) & (Y > 22.5), PEARL, 0.33, 1.25)
    c.paint(hull, UMBER, np.where(Y > 22.0, 1.0, 0.67), 1.3)
    c.paint(c.line_mask([(1.9, 19.8), (22.4, 18.6)], 0.9), PEARL, 0.0, 1.4)
    for wx in (3, 5):
        c.paint(rect(c, wx, 21, wx + 1, 22), SAFFRON, 0.0, 1.7)
    c.paint(c.line_mask([(22, 18.6), (24.4, 17.0)], 0.8), UMBER, 0.67, 1.4)
    for (mx, mtop, yards) in ((6.5, 3.5, (7.0, 12.0)), (12.5, 1.6, (5.0, 10.0, 15.0)), (18.5, 4.5, (8.5, 13.5))):
        c.paint(c.line_mask([(mx, 19.5), (mx + 0.06 * (19.5 - mtop), mtop)], 1.0), UMBER, 1.0, 1.4)
        for k, yy in enumerate(yards):
            xm = mx + 0.06 * (19.5 - yy)
            c.paint(ellipse(c, xm, yy, 3.9 - 0.4 * k, 0.8), PEARL, 0.33, 1.45)
    # the sledge far out on the floes: a gigantic cloaked figure standing on the runners, one arm out to
    # the reins, a pair of dogs running ahead (tile-exact sprites)
    c.paint(rect(c, 25.2, 22.0, 34.4, 22.9) | c.line_mask([(34.2, 22.4), (35.2, 21.2)], 0.7), UMBER, 0.67, 1.6)
    sprite(c, 26, 12, GIANT, UMBER, 1.0)
    for dx in (35, 40):
        sprite(c, dx, 19, DOG, UMBER, 0.33)
    frame(c)
    return encode(c.to_tiles())


# ---------------------------------------------------------------------------
# Master
# ---------------------------------------------------------------------------

def tripods():
    """The War of the Worlds: Martian fighting-machines striding over the hedged fields of Surrey on long
    jointed legs, a steam train fleeing along its embankment, cottages, the red weed spreading along the river."""
    c = Canvas(44, 42)
    X, Y = c.X, c.Y
    tx, ty = np.floor(X).astype(int), np.floor(Y).astype(int)
    XC, YC = tx + 0.5, ty + 0.5
    hz = 17
    # smoky sky: grey smoke clouds drifting over a pale glow low down
    c.paint(Y < hz, LAPIS, np.clip(0.8 - 0.8 * Y / hz, 0, 1))
    c.paint((Y > 13.5) & (Y < hz), SAFFRON, 0.0)
    for (sx, sy, k) in ((4, 4.0, 1.0), (29, 2.8, 1.1), (41, 7.0, 0.8), (30, 12.4, 0.7), (6, 13.0, 0.7)):
        cloud(c, [(sx - 2.6 * k, sy + 0.6, 1.8 * k), (sx, sy, 2.5 * k), (sx + 2.6 * k, sy + 0.7, 1.7 * k)], 0.6)
    # hedged fields in perspective: hedge rows, hedges converging on the horizon, many crops
    rows = np.array([hz, 19, 21, 24, 27, 31, 36, 43])
    ri = np.clip(np.searchsorted(rows, YC) - 1, 0, 6)
    u = (XC - 22) / ((YC - 9) * 0.42) + ri * 0.37
    col = np.floor(u).astype(int)
    kind = (col * 7 + ri * 5) % 6
    ground = Y >= hz
    c.paint(ground, FERN, 0.0)
    c.paint(ground & (kind == 2), SAFFRON, np.where(ri % 2 == 0, 0.0, 0.33))
    c.paint(ground & (kind == 4), SAFFRON, 0.67)
    c.paint(ground & (kind == 5), FERN, 0.33)
    hedge = ground & (np.isin(ty, rows[1:-1]) | (np.abs((u % 1.0) - 0.5) > 0.5 - 0.5 / ((YC - 9) * 0.42)))
    c.paint(hedge & (ty > hz), FERN, 0.67, 1.2)
    # the river, the red weed choking its banks and creeping into the fields
    rx = 34 + 3.0 * np.sin(YC * 0.3) + (YC - hz) * 0.15
    river = ground & (np.abs(XC - rx) < 0.5 + 0.06 * (YC - hz))
    weed = ground & ~river & (np.abs(XC - rx) < 1.6 + 0.12 * (YC - hz)) & (smooth_noise(c, 6, 0.9) > -0.2)
    c.paint(weed, EMBER, np.where((tx + ty) % 3 == 0, 0.67, 0.33), 1.2)
    c.paint(river, LAPIS, 0.33, 1.25)
    for (wx, wy, wr) in ((25, 34, 1.6), (41, 40, 1.8), (21, 39, 1.3)):
        c.paint(c.circle(wx, wy, wr), EMBER, 0.33, 1.2)
    # cottages: white walls, red roofs, dark doors
    for (hx, hy) in ((6, 22), (20, 21), (2, 34), (11, 39), (39, 27), (28, 31), (41, 21)):
        c.paint(rect(c, hx, hy - 2, hx + 3, hy), PEARL, 0.0, 1.5)
        c.paint(rect(c, hx - 1, hy - 3, hx + 4, hy - 2) | rect(c, hx, hy - 4, hx + 3, hy - 3), EMBER, 0.67, 1.55)
        c.paint(rect(c, hx + 1, hy - 1, hx + 2, hy), UMBER, 1.0, 1.6)
    # the steam train on its embankment, smoke trailing back
    c.paint(rect(c, 0, 32, 27, 33), PEARL, 1.0, 1.4)
    c.paint(rect(c, 18, 27, 21, 32) | rect(c, 17.6, 26.4, 21.4, 27.2) | rect(c, 21, 29, 26, 32) | rect(c, 24, 27, 25, 29),
            LAPIS, 1.0, 1.5)                                                      # cab, boiler and chimney
    for x0 in (3, 11):
        c.paint(rect(c, x0, 29, x0 + 7, 32), EMBER, 1.0, 1.5)
        c.paint(rect(c, x0 + 1, 30, x0 + 6, 31) & ((tx % 2) == 0), SAFFRON, 0.0, 1.55)
    c.paint(rect(c, 19, 28, 20, 29), PEARL, 0.0, 1.55)                          # cab window
    for wx in (5.0, 8.0, 13.0, 16.0, 19.5, 22.5, 25.0):
        c.paint(c.circle(wx, 32.0, 0.75), UMBER, 1.0, 1.6)                        # wheels
    for (sx, sy, sr) in ((23.6, 25.0, 1.3), (21.4, 23.2, 1.6), (17.6, 22.4, 1.9), (13.4, 22.6, 1.7)):
        c.paint(c.circle(sx, sy, sr), PEARL, 0.33, 1.3)
    # the fighting-machines: a domed hood with a metal rim and a green glare, a carriage beneath, three
    # long legs kinking outward at the knees; steel tentacles dangling from the biggest
    for (hx, hy, s, fam, legs) in ((15.0, 7.0, 1.0, UMBER, (((6.5, 17.0), (2.5, 39.0)), ((24.5, 17.5), (29.5, 37.0)), ((18.0, 25.0), (14.0, 41.0)))),
                                   (36.5, 9.5, 0.62, UMBER, (((31.5, 15.5), (30.5, 30.0)), ((41.5, 15.0), (42.0, 29.0)), ((38.0, 20.5), (36.5, 32.0)))),
                                   (26.5, 12.6, 0.42, UMBER, (((24.0, 16.0), (23.0, 22.0)), ((29.0, 16.0), (30.0, 21.5)), ((27.0, 18.0), (26.6, 23.0))))):
        hub = (hx, hy + 4.2 * s)
        for (knee, foot) in legs:
            c.paint(tube(c, [hub, knee, foot], 1.4 * s + 0.3, 0.8 * s + 0.4), fam, 1.0, 1.6)
            c.paint(c.circle(knee[0], knee[1], 0.9 * s + 0.35), fam, 0.67, 1.65)
            c.paint(ellipse(c, foot[0], foot[1], 1.2 * s + 0.4, 0.5 * s + 0.25), fam, 1.0, 1.65)
        if s > 0.9:
            for pts in ([(hx - 1.5, hy + 5.0), (hx - 4.0, hy + 8.5), (hx - 2.5, hy + 11.5), (hx - 4.5, hy + 13.5)],
                        [(hx + 1.5, hy + 5.0), (hx + 3.0, hy + 9.0), (hx + 1.5, hy + 12.0)]):
                c.paint(tube(c, pts, 0.9, 0.6), PEARL, 0.67, 1.6)
        dome = ellipse(c, hx, hy + 0.8 * s, 4.6 * s, 4.6 * s) & (Y < hy + 2.4 * s)
        hood = dome | ellipse(c, hx, hy + 2.4 * s, 4.2 * s, 1.0 * s) | ellipse(c, hx, hy + 3.8 * s, 2.6 * s, 1.3 * s)
        c.paint(hood, fam, np.where(Y < hy - 1.6 * s, 0.67, 1.0), 1.7)
        c.paint(dome & (np.abs(Y - hy - 1.4 * s) < 0.35 * s + 0.25), PEARL if fam == UMBER else UMBER, 0.67, 1.75)
        c.paint(ellipse(c, hx + 2.0 * s, hy - 0.2 * s, 1.2 * s + 0.2, 0.8 * s + 0.2), FERN, 0.0, 1.85)
    frame(c)
    return encode(c.to_tiles())


def chandelier():
    """The Paris Opera seen from the stage: the painted ceiling ringed with gold and laurel, four tiers of
    red-and-gold boxes sweeping round the horseshoe with tiny spectators, the audience in the stalls and
    the footlights below, and the great crystal chandelier blazing in the centre."""
    c = Canvas(44, 44)
    X, Y = c.X, c.Y
    tx, ty = np.floor(X).astype(int), np.floor(Y).astype(int)
    XC, YC = tx + 0.5, ty + 0.5
    lift = 0.017 * (XC - 22) ** 2                     # the horseshoe: tiers sweep up towards the sides
    row = np.floor(YC + lift).astype(int)             # tile row in the "unbent" auditorium
    th = np.arcsin(np.clip((XC - 22) / 25.0, -1, 1))  # angle round the horseshoe
    # the painted ceiling: robed muses on a blue sky, panels divided by gold ribs
    c.paint(ALL(c), LAPIS, 0.67)
    ray = np.arctan2(XC - 22, YC + 4) / 0.42 + 0.5
    sec, fr = np.floor(ray).astype(int), ray % 1.0
    ceil = row < 8
    c.paint(ceil & (smooth_noise(c, 3, 0.8) > 0.3), LAPIS, 0.33, 1.02)
    figs = ceil & (row >= 2) & (row <= 6) & (np.abs(fr - 0.5) < 0.17)
    for k, (fam, sh) in enumerate(((EMBER, 0.33), (FERN, 0.33), (PEARL, 0.0), (FERN, 0.67))):
        c.paint(figs & (sec % 4 == k), fam, np.where(row <= 3, 0.0, sh), 1.1)
    c.paint(ceil & (np.abs(fr - 0.5) > 0.44), SAFFRON, 0.67, 1.15)
    c.paint(row == 8, SAFFRON, 0.33, 1.2)                                       # gold cornice ring
    c.paint(row == 9, FERN, np.where((tx % 3) == 1, 0.33, 0.67), 1.2)          # laurel garland
    # four tiers: the gold balcony front, then a red band of boxes, each box a dark opening with a pale
    # spectator's face over coloured shoulders, red pilasters between
    for k in range(4):
        d = row - (10 + 7 * k)
        band = (d >= 0) & (d < 7)
        u = th / 0.2 + 0.5 * k
        b, f = np.floor(u).astype(int), u % 1.0
        c.paint(band & (d == 0), SAFFRON, 0.0, 1.2)
        c.paint(band & (d == 1), SAFFRON, 0.67, 1.2)
        c.paint(band & (d >= 2), EMBER, np.where(d == 2, 0.67, 1.0), 1.2)
        box = band & (d >= 3) & (d <= 5) & (f > 0.25)
        c.paint(box, UMBER, 1.0, 1.22)
        face = box & (d == 4) & (np.abs(f - 0.62) < 0.08) & ((b + k) % 4 != 3)
        c.paint(face, PEARL, 0.0, 1.3)
        for j, fam in enumerate((LAPIS, FERN, SAFFRON)):
            c.paint(box & (d == 5) & (np.abs(f - 0.62) < 0.2) & ((b + k) % 4 != 3) & ((b + 2 * k) % 3 == j), fam, 0.67, 1.28)
    # the stalls: red velvet seats and rows of the audience; the gold rail of the orchestra pit; the stage
    # edge with its footlights
    st = row >= 38
    c.paint(st, EMBER, np.where(ty % 3 == 0, 0.67, 1.0), 1.2)
    sr, who = ty % 3, (tx + ty // 3) % 3 == 1
    c.paint(st & (sr == 1) & who, PEARL, 0.0, 1.3)                               # faces
    for j, fam in enumerate((LAPIS, FERN, UMBER, FERN)):                         # coats and gowns
        c.paint(st & (sr == 2) & who & ((tx // 3 + ty // 3) % 4 == j), fam, 0.33, 1.28)
    c.paint(Y >= 41, UMBER, 1.0, 1.3)
    c.paint(rect(c, 0, 40.4, 44, 41.2), SAFFRON, 0.33, 1.35)
    c.paint(Y >= 42.5, UMBER, 0.33, 1.35)
    c.paint((Y >= 41.4) & (Y < 42.5) & ((tx % 3) == 1), SAFFRON, 0.0, 1.4)
    # the chandelier, tile by tile (half-width per row, mirrored about the centre): chain and crown, a bell
    # of crystal on gold ribs, the great ring whose arms reach out with candles standing on them and
    # crystal drops hanging below, the bowl, a second ring of lights, the basket and the pendant drop
    m = np.abs(XC - 22) - 0.5                                                    # 0, 1, 2 ... from the centre
    half = dict(enumerate([1, 1, 1, 2, 3, 4, 5, 6, 7, 8, 9, 9, 9, 9, 8, 7, 6, 5, 5, 4, 3, 2, 1, 1]))
    hw = np.vectorize(lambda r: half.get(r, -1))(ty)
    body = (m < hw) & (ty < 24)
    arm = (ty == 11) & (m < 15)
    candle = np.isin(ty, (9, 10)) & np.isin(m, (10, 12, 14))
    drop = np.isin(ty, (12, 13)) & np.isin(m, (9, 11, 13)) & ~((ty == 13) & (m == 13))
    inside = body | arm | candle | drop
    c.paint(grow(inside, 0.9) & ~inside & (ty >= 3), UMBER, 1.0, 1.55)
    c.paint(inside, PEARL, np.where((m + ty) % 2 == 0, 0.0, 0.33), 1.6)          # crystal
    c.paint(body & (m % 3 == 1) & (ty >= 6) & (ty <= 9), SAFFRON, 0.67, 1.62)   # gold ribs of the bell
    c.paint(inside & np.isin(ty, (0, 1, 2, 5, 11, 18, 21)), SAFFRON, 0.67, 1.62)  # chain, crown, rings, arms
    c.paint(inside & np.isin(ty, (3, 12)) & ~drop, SAFFRON, 0.33, 1.62)
    c.paint(body & np.isin(ty, (4, 10, 17)), SAFFRON, np.where(m % 2 == 0, 0.0, 0.67), 1.65)  # lights
    c.paint(candle & (ty == 9), SAFFRON, 0.0, 1.66)                              # flames on the arms
    c.paint((candle & (ty == 10)) | drop, PEARL, 0.0, 1.66)                     # candles and drops
    c.paint(body & (ty >= 13) & (ty <= 16) & (m % 2 == 1), PEARL, 0.0, 1.64)    # strings of crystal
    c.paint(body & (ty >= 13) & (ty <= 16) & (m % 2 == 0) & ((m // 2 + ty) % 2 == 0), SAFFRON, 0.0, 1.64)
    frame(c)
    return encode(c.to_tiles())


SCENES = {
    "raven": raven, "horseman": horseman, "hound": hound, "notredame": notredame,
    "dracula": dracula, "arctic": arctic, "tripods": tripods, "chandelier": chandelier,
}
