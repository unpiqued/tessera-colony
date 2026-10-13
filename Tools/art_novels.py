"""Great Novels pack: eight iconic scenes from public-domain novels, drawn with the supersampled Canvas
of art.py (a tile's colour family comes from the dominant object under it, its tone from the shading).
Every scene is an original composition from the book's text (no film designs, no book-cover art).

Gentle: Gatsby's green light, Scrooge's Christmas morning, Wuthering Heights in a storm, the comet of 1812.
Challenge: Miss Havisham's room, the bishop's silver candlesticks.
Master (busy, every colour in many islands): the Netherfield ball, Oliver asking for more.
"""
import math
import random

import numpy as np

from art import Canvas, LAPIS, SAFFRON, FERN, EMBER, UMBER, PEARL, encode, smoothstep
from art_scenes import ALL, ellipse, rect, tube, frame, smooth_noise


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------

def tiles(c):
    return np.floor(c.X).astype(int), np.floor(c.Y).astype(int)


def stars(c, rng, n, x0, x1, y0, y1, r=0.45, fam=PEARL, shade=0.05):
    for _ in range(n):
        c.paint(c.circle(rng.uniform(x0, x1), rng.uniform(y0, y1), r), fam, shade, 1.5)


def flame(c, x, y, s=1.0, glow=0.0):
    """A candle flame whose base sits at (x, y): a pale teardrop with an orange heart, optional glow."""
    if glow:
        c.paint(c.circle(x, y - 0.9 * s, glow), SAFFRON, np.clip(0.1 + 0.12 * np.hypot(c.X - x, c.Y - y + 0.9 * s), 0, 0.5), 1.15)
    drop = c.circle(x, y - 0.55 * s, 0.55 * s) | c.poly_mask([(x - 0.5 * s, y - 0.7 * s), (x, y - 2.0 * s), (x + 0.5 * s, y - 0.7 * s)])
    c.paint(drop, SAFFRON, 0.0, 1.8)
    c.paint(c.circle(x, y - 0.5 * s, 0.3 * s), EMBER, 0.2, 1.9)


def onion(c, cx, cy, r):
    """An onion dome centred at (cx, cy): a swelling bulb that tapers to a point above."""
    bulb = ellipse(c, cx, cy, r, r * 0.92)
    tip = c.poly_mask([(cx - r * 0.78, cy - r * 0.55), (cx, cy - r * 2.0), (cx + r * 0.78, cy - r * 0.55)])
    return bulb | tip


def gentleman(c, x, feet, h, coat, coat_shade, legs=PEARL):
    """A Regency gentleman facing us: dark tail coat, white cravat and waistcoat, pale breeches."""
    s = h / 12.0
    X, Y = c.X, c.Y
    c.paint(tube(c, [(x - 0.6 * s, feet - 4.5 * s), (x - 0.75 * s, feet - 0.3 * s)], 0.95 * s, 0.85 * s)
            | tube(c, [(x + 0.6 * s, feet - 4.5 * s), (x + 0.75 * s, feet - 0.3 * s)], 0.95 * s, 0.85 * s), legs, 0.3, 1.5)
    c.paint(ellipse(c, x - 0.9 * s, feet - 0.2 * s, 0.8 * s, 0.4 * s) | ellipse(c, x + 0.9 * s, feet - 0.2 * s, 0.8 * s, 0.4 * s),
            UMBER, 0.95, 1.6)
    body = c.poly_mask([(x - 1.9 * s, feet - 9.3 * s), (x + 1.9 * s, feet - 9.3 * s), (x + 2.1 * s, feet - 4.0 * s),
                        (x + 1.2 * s, feet - 3.0 * s), (x - 1.2 * s, feet - 3.0 * s), (x - 2.1 * s, feet - 4.0 * s)])
    c.paint(body, coat, coat_shade, 1.5)
    c.paint(c.poly_mask([(x - 0.8 * s, feet - 9.4 * s), (x + 0.8 * s, feet - 9.4 * s), (x, feet - 6.0 * s)]), PEARL, 0.05, 1.6)
    c.paint(c.circle(x, feet - 10.6 * s, 1.15 * s), EMBER, 0.05, 1.6)
    c.paint(c.circle(x, feet - 11.0 * s, 1.2 * s) & (Y < feet - 11.1 * s), UMBER, 0.75, 1.7)


def lady(c, x, feet, h, gown, gown_shade, sash=None, hair=0.8):
    """A Regency lady: high-waisted gown falling straight to the floor, short sleeves, hair up in a bun."""
    s = h / 13.0
    gown_m = c.poly_mask([(x - 1.3 * s, feet - 9.6 * s), (x + 1.3 * s, feet - 9.6 * s), (x + 2.6 * s, feet),
                          (x - 2.6 * s, feet)])
    c.paint(gown_m, gown, np.clip(gown_shade + 0.15 * np.abs(c.X - x) / (2.6 * s), 0, 1), 1.5)
    if sash is not None:
        c.paint(gown_m & (np.abs(c.Y - (feet - 8.9 * s)) < 0.5 * s), sash, 0.4, 1.6)
    for side in (-1, 1):
        c.paint(tube(c, [(x + side * 1.4 * s, feet - 9.0 * s), (x + side * 1.9 * s, feet - 6.0 * s)], 0.7 * s, 0.6 * s),
                EMBER, 0.05, 1.55)
    c.paint(c.circle(x, feet - 10.7 * s, 1.05 * s), EMBER, 0.05, 1.6)
    c.paint((c.circle(x, feet - 11.1 * s, 1.1 * s) & (c.Y < feet - 11.1 * s)) | c.circle(x, feet - 12.3 * s, 0.7 * s),
            UMBER, hair, 1.7)


# ---------------------------------------------------------------------------
# gentle
# ---------------------------------------------------------------------------

def greenlight():
    """The Great Gatsby: a lone figure at the foot of his lawn stretches out his arm across the dark bay
    toward the single green light at the end of a dock; his mansion is lit from tower to cellar."""
    c = Canvas(48, 36)
    X, Y = c.X, c.Y
    hz = 12.5
    # night sky and the silver pepper of the stars
    c.paint(ALL(c), LAPIS, np.clip(1.0 - 0.3 * Y / hz, 0, 1))
    stars(c, random.Random(41), 9, 19, 46, 1.5, hz - 3.5)
    # the bay, with long low ripples
    rip = np.sin(Y * 1.9 + np.sin(X * 0.3) * 1.4)
    c.paint(Y >= hz, LAPIS, np.clip(0.5 + 0.3 * (Y - hz) / 22 - 0.22 * (rip > 0.8), 0, 1))
    # the far shore of East Egg: a low dark band of trees
    bumps = np.clip(np.sin(X * 0.8) + 0.6 * np.sin(X * 1.9 + 1.0), 0, None)
    c.paint((X > 15) & (Y > hz - 0.8 - 0.9 * bumps) & (Y < hz + 0.5), UMBER, 0.95, 1.1)
    # Daisy's dock and the green light at its end, glowing and trembling in the water
    lx, ly = 41.0, hz - 2.5
    c.paint(c.circle(lx, ly, 2.8), FERN, np.clip(0.05 + 0.12 * np.hypot(X - lx, Y - ly), 0, 1), 1.3)
    c.paint(rect(c, 37.5, hz + 0.1, 44.5, hz + 0.9), UMBER, 0.85, 1.3)
    c.paint(rect(c, lx - 0.4, ly, lx + 0.4, hz + 0.6), UMBER, 0.9, 1.5)
    c.paint(c.circle(lx, ly, 0.8), PEARL, 0.0, 2.0)
    for k in range(5):
        c.paint(ellipse(c, lx + 0.3 * math.sin(k * 2.0), hz + 2.6 + k * 2.3, 1.3 - 0.12 * k, 0.5), FERN, 0.15 + 0.08 * k, 1.5)
    # the lawn sweeping down from the house to the low sea wall along the bottom
    edge = [(-1, 19.5), (16, 20.0), (22, 25.0), (29, 30.2), (38, 32.6), (49, 33.4)]
    lawn = c.poly_mask(edge + [(49, 37), (-1, 37)])
    stripes = (np.sin((X - (Y - 20) * 1.4) * 0.45) > 0.6)
    c.paint(lawn, FERN, np.clip(0.75 + 0.01 * Y - 0.25 * stripes, 0, 1))
    c.paint(c.line_mask(edge, 0.9), PEARL, 0.65, 1.3)
    # the mansion: mansard roof, a tower on one side, every window lit
    c.paint(rect(c, -1, 6.0, 17.5, 20.2), PEARL, np.clip(0.55 + 0.015 * X, 0, 1))
    c.paint(c.poly_mask([(-1, 6.3), (0.5, 3.4), (15.5, 3.4), (17.8, 6.3)]), UMBER, 0.85, 1.1)
    c.paint(rect(c, 11.0, 0.5, 16.5, 6.0), PEARL, 0.7, 1.1)
    c.paint(c.poly_mask([(10.4, 0.9), (13.75, -3.0), (17.1, 0.9)]), UMBER, 0.85, 1.1)
    for wy in (7.4, 11.2, 15.0):
        for wx in (0.8, 3.9, 7.0, 10.1, 13.2):
            c.paint(rect(c, wx, wy, wx + 1.7, wy + 2.3), SAFFRON, 0.1, 1.5)
    c.paint(rect(c, 12.9, 1.4, 14.6, 3.6), SAFFRON, 0.1, 1.5)
    # the lone figure, a dark silhouette against the water, one arm reaching toward the light
    fx, ft = 30.0, 31.6
    man = (c.circle(fx, ft - 12.7, 1.3)
           | c.poly_mask([(fx - 1.7, ft - 11.1), (fx + 1.7, ft - 11.1), (fx + 1.4, ft - 5.8), (fx - 1.4, ft - 5.8)])
           | tube(c, [(fx - 0.6, ft - 6.2), (fx - 1.5, ft - 0.3)], 1.1, 0.95) | tube(c, [(fx + 0.6, ft - 6.2), (fx + 1.6, ft - 0.3)], 1.1, 0.95)
           | tube(c, [(fx + 1.2, ft - 10.6), (fx + 3.6, ft - 11.6), (fx + 6.4, ft - 13.0)], 1.0, 0.8)
           | tube(c, [(fx - 1.3, ft - 10.6), (fx - 1.9, ft - 6.6)], 0.95, 0.85))
    c.paint(man, UMBER, 1.0, 1.7)
    frame(c)
    return encode(c.to_tiles())


def christmascarol():
    """A Christmas Carol: Scrooge, in nightcap and dressing gown, flings open his window on Christmas
    morning and calls down to a boy in the snowy street; the church bell swings, wreaths hang on the doors."""
    c = Canvas(40, 44)
    X, Y = c.X, c.Y
    tx, ty = tiles(c)
    # bright, cold morning sky
    c.paint(ALL(c), LAPIS, np.clip(0.45 - 0.4 * Y / 24, 0, 1))
    # the church tower down the street, its bell swinging in the belfry
    c.paint(rect(c, 29.5, 6.5, 36.5, 22), PEARL, np.where(X > 34, 0.7, 0.45))
    c.paint(c.poly_mask([(28.8, 6.8), (37.2, 6.8), (33, -3)]), UMBER, 0.75, 1.1)
    c.paint(rect(c, 28.8, 6.0, 37.2, 7.2), PEARL, 0.05, 1.2)
    c.paint(rect(c, 31, 10.5, 35, 16.5) | c.circle(33, 10.5, 2.0), UMBER, 0.95, 1.3)
    c.paint(c.poly_mask([(31.4, 15.4), (32.2, 11.6), (33.4, 10.8), (34.2, 11.8), (34.8, 15.6)]), SAFFRON, 0.3, 1.7)
    # houses across the street: snow-laden roof, a chimney, windows, a green door with a wreath
    c.paint(rect(c, 25, 21, 41, 33), EMBER, np.clip(0.75 + 0.15 * (ty % 2), 0, 1))
    c.paint(rect(c, 26.5, 13.5, 28.5, 19), EMBER, 0.85)
    c.paint(c.poly_mask([(24.5, 21.5), (27.5, 17.0), (41, 17.0), (41, 21.5)]), PEARL, 0.1, 1.1)
    c.paint(rect(c, 32.0, 23.0, 34.6, 27.0), LAPIS, 0.25, 1.3)
    c.paint(rect(c, 36.5, 24.5, 40, 33), FERN, 0.85, 1.3)
    c.paint(c.circle(38.2, 27.5, 1.2) & ~c.circle(38.2, 27.5, 0.5), FERN, 0.35, 1.5)
    # the snowy street
    street = Y > 33 + (X < 25) * 3.5
    c.paint(street, PEARL, np.clip(0.05 + 0.02 * (Y - 33) + 0.3 * (np.abs(np.sin(X * 0.6 + Y * 0.2)) > 0.95), 0, 1))
    # Scrooge's house: dark brick, a white window frame, open casements, a snowy eave
    c.paint(rect(c, -1, -1, 25.5, 36.5), UMBER, np.clip(0.6 + 0.2 * ((ty + (tx // 3) % 2) % 2), 0, 1))
    c.paint(rect(c, -1, -1, 25.5, 2.2), PEARL, 0.05, 1.2)
    c.paint(rect(c, 5.5, 8.6, 21.5, 26), PEARL, 0.3, 1.2)
    c.paint(rect(c, 7, 10, 20, 25.5), UMBER, 1.0, 1.2)
    for pts in ([(1.0, 8.2), (5.4, 9.6), (5.4, 25.2), (1.0, 26.4)], [(21.6, 9.6), (26.0, 8.2), (26.0, 26.4), (21.6, 25.2)]):
        c.paint(c.poly_mask(pts), PEARL, 0.35, 1.25)
        x0, x1 = pts[0][0] + 0.6, pts[1][0] - 0.6
        c.paint(c.poly_mask([(x0, pts[0][1] + 1.4), (x1, pts[1][1] + 1.4), (x1, pts[2][1] - 1.0), (x0, pts[3][1] - 1.0)]),
                LAPIS, np.where(np.abs(Y - 17) < 0.5, 0.75, 0.15), 1.3)
    c.paint(rect(c, 4, 25.2, 23, 27.0), PEARL, 0.05, 1.4)
    # Scrooge leaning out: blue dressing gown over his nightshirt, arms flung wide on the sill, a long nightcap
    sx = 13.0
    c.paint(ellipse(c, sx, 24.5, 5.0, 5.0) & (Y < 25.4), LAPIS, 0.75, 1.4)
    c.paint(c.poly_mask([(sx - 1.8, 19.2), (sx + 1.8, 19.2), (sx + 0.9, 25.4), (sx - 0.9, 25.4)]), PEARL, 0.1, 1.5)
    for side in (-1, 1):
        c.paint(tube(c, [(sx + side * 3.2, 21.2), (sx + side * 6.2, 23.4), (sx + side * 7.6, 24.6)], 2.0, 1.6), LAPIS, 0.7, 1.45)
        c.paint(c.circle(sx + side * 8.4, 24.8, 1.0), EMBER, 0.05, 1.6)
    c.paint(ellipse(c, sx, 16.4, 2.2, 2.6), EMBER, 0.05, 1.5)
    c.paint(c.circle(sx - 0.9, 15.8, 0.38) | c.circle(sx + 0.9, 15.8, 0.38) | ellipse(c, sx, 18.1, 1.0, 0.45), UMBER, 1.0, 1.9)
    cap = c.poly_mask([(sx - 2.6, 15.2), (sx - 1.6, 12.2), (sx + 1.8, 11.8), (sx + 4.0, 13.4), (sx + 7.4, 17.2),
                       (sx + 6.4, 18.0), (sx + 2.8, 14.6), (sx + 2.4, 15.2)])
    c.paint(cap, PEARL, 0.1, 1.6)
    c.paint(rect(c, sx - 2.7, 14.0, sx + 2.6, 14.9), PEARL, 0.4, 1.65)
    c.paint(c.circle(sx + 7.4, 18.4, 0.95), EMBER, 0.35, 1.7)
    # the front door with its wreath
    c.paint(rect(c, 1.5, 28.5, 7.5, 36.5), LAPIS, 0.85, 1.3)
    c.paint(c.circle(4.5, 31.8, 1.8) & ~c.circle(4.5, 31.8, 0.8), FERN, 0.55, 1.5)
    c.paint(c.circle(4.5, 33.6, 0.6), EMBER, 0.3, 1.7)
    # the boy below in the street, one arm pointing up at the window
    bx, bf = 30.5, 42.0
    c.paint(tube(c, [(bx - 0.6, bf - 4.5), (bx - 0.9, bf)], 0.95, 0.9) | tube(c, [(bx + 0.6, bf - 4.5), (bx + 1.0, bf)], 0.95, 0.9), UMBER, 0.9, 1.5)
    c.paint(c.poly_mask([(bx - 1.7, bf - 9.6), (bx + 1.7, bf - 9.6), (bx + 2.1, bf - 4.0), (bx - 2.1, bf - 4.0)]), LAPIS, 0.6, 1.5)
    c.paint(tube(c, [(bx - 1.3, bf - 8.8), (bx - 3.2, bf - 11.2), (bx - 4.4, bf - 13.6)], 1.0, 0.85), LAPIS, 0.6, 1.55)
    c.paint(rect(c, bx - 1.6, bf - 10.2, bx + 1.6, bf - 9.2), SAFFRON, 0.3, 1.6)
    c.paint(c.circle(bx, bf - 11.4, 1.3), EMBER, 0.05, 1.6)
    c.paint(ellipse(c, bx + 0.2, bf - 12.6, 1.7, 0.8), UMBER, 0.8, 1.7)
    frame(c)
    return encode(c.to_tiles())


def wuthering():
    """Wuthering Heights: the stone farmhouse hunched on the crest of the moor in a storm, its stunted
    firs and gaunt thorns all stretching their limbs one way, one window lit against the night."""
    c = Canvas(48, 36)
    X, Y = c.X, c.Y
    # storm sky: dark, with paler torn cloud streaming before the wind and slanting rain
    n = smooth_noise(c, 17, 0.3)
    torn = n + 0.55 * np.sin((X + Y * 1.7) * 0.2) + 0.5 * (1 - X / 48)
    rain = (np.sin((X + Y * 0.45) * 2.3) > 0.86) & (np.sin((Y - X * 0.4) * 0.8) > -0.2)
    c.paint(ALL(c), LAPIS, np.clip(0.98 - 0.55 * smoothstep(0.1, 0.8, torn) - 0.3 * rain, 0, 1))
    # the moor rising to the right: dark grass, brown heather, a dry-stone wall climbing to the house
    crest = 30.5 - 13 * smoothstep(0, 30, X) + 0.8 * np.sin(X * 0.45)
    moor = Y > crest
    combed = np.sin((X * 0.9 - Y * 1.6)) > 0.7
    c.paint(moor, FERN, np.clip(0.97 + 0.05 * smooth_noise(c, 5, 0.6) - 0.17 * combed, 0, 1))
    heath = moor & (smooth_noise(c, 9, 0.4) > 0.15) & (Y > crest + 1.5)
    c.paint(heath, UMBER, np.clip(0.8 - 0.15 * combed, 0, 1))
    c.paint(c.line_mask([(17, 37), (21.5, 28.5), (26.5, 19.5)], 0.9), PEARL, 0.8, 1.2)
    # the house: long, low, stone with big corner quoins; slate roof; smoke torn sideways from the chimneys
    walls = rect(c, 26.5, 11.0, 42.5, 18.8)
    quoin = ((X < 27.7) | (X > 41.3)) & (np.floor(Y / 1.2) % 2 == 0)
    c.paint(walls, PEARL, np.clip(0.6 + 0.2 * quoin + 0.08 * np.sin(X * 2.1) * np.sin(Y * 2.7), 0, 1))
    c.paint(c.poly_mask([(25.6, 11.4), (28.5, 7.4), (40.5, 7.4), (43.4, 11.4)]), UMBER, 0.9, 1.1)
    c.paint(rect(c, 42.5, 13.5, 47.5, 18.8), PEARL, 0.8)
    c.paint(c.poly_mask([(42.0, 13.8), (42.0, 11.5), (47.5, 13.2), (47.5, 14.0)]), UMBER, 0.9, 1.1)
    for chx in (29.6, 39.4):
        c.paint(rect(c, chx - 0.9, 5.2, chx + 0.9, 8.0), PEARL, 0.7, 1.2)
        c.paint(tube(c, [(chx - 0.3, 5.0), (chx - 3.5, 3.6), (chx - 7.5, 3.4)], 1.5, 0.8), PEARL, 0.3, 1.1)
    for wx in (29.0, 32.0, 38.8):
        c.paint(rect(c, wx, 12.8, wx + 1.2, 15.2), UMBER, 0.95, 1.5)
    c.paint(rect(c, 34.4, 14.0, 36.2, 18.8), UMBER, 0.95, 1.5)
    # one lit window, glowing
    c.paint(c.circle(38.2, 13.9, 2.2) & walls, SAFFRON, np.clip(0.2 + 0.2 * np.hypot(X - 38.2, Y - 13.9), 0, 1), 1.3)
    c.paint(rect(c, 37.4, 12.6, 39.0, 15.3), SAFFRON, 0.0, 1.6)
    # stunted firs at the end of the house, slanting hard before the wind
    for (fx, fb, fh, w) in ((21.5, 22.0, 10.0, 2.2), (24.2, 20.0, 8.0, 1.8)):
        c.paint(c.poly_mask([(fx - w, fb), (fx + w, fb), (fx - 3.4, fb - fh)]), FERN, 0.95, 1.2)
        c.paint(c.line_mask([(fx, fb + 1.2), (fx, fb - 0.3)], 0.7), UMBER, 0.9, 1.3)
    # gaunt thorns in the foreground, every limb stretched the same way
    trunk = tube(c, [(13.5, 37), (13.0, 29), (10.5, 23.5), (7.0, 20.0)], 2.8, 1.4)
    limbs = (tube(c, [(10.6, 23.8), (6.0, 22.6), (1.5, 23.0), (-1, 22.0)], 1.3, 0.7)
             | tube(c, [(8.6, 21.6), (5.5, 16.8), (1.5, 14.6), (-1, 14.0)], 1.2, 0.6)
             | tube(c, [(12.3, 26.5), (14.0, 21.5), (12.0, 17.0), (8.0, 14.0), (5.0, 12.5)], 1.2, 0.6)
             | tube(c, [(7.0, 20.0), (3.0, 18.5), (-1, 18.6)], 1.1, 0.6)
             | tube(c, [(20.5, 27.0), (19.8, 22.5), (17.0, 20.0), (14.5, 19.4)], 1.4, 0.7))
    c.paint(trunk | limbs, UMBER, 0.95, 1.4)
    for (bx, by, rx) in ((2.5, 13.6, 2.6), (5.8, 11.8, 2.0), (1.5, 21.8, 2.2), (0.8, 17.9, 1.8), (15.0, 18.8, 2.1)):
        c.paint(ellipse(c, bx, by, rx, rx * 0.55, -0.25), UMBER, 0.8, 1.3)
    frame(c)
    return encode(c.to_tiles())


def comet1812():
    """War and Peace: on a frosty night Pierre stands in a snowy Moscow square and looks up at the great
    comet of 1812, its long tail uplifted above the golden onion domes and the red Kremlin wall."""
    c = Canvas(44, 42)
    X, Y = c.X, c.Y
    tx, ty = tiles(c)
    # frosty night sky with stars
    c.paint(ALL(c), LAPIS, np.clip(0.98 - 0.25 * Y / 26, 0, 1))
    stars(c, random.Random(18), 12, 2, 42, 1.5, 14)
    # the comet: a brilliant head and a long tail lifted up and fanning out
    hx, hy = 29.5, 8.0
    tail = [(hx, hy), (27.8, 4.6), (25.0, 1.2), (21.0, -3.0)]
    c.paint(tube(c, tail, 4.0, 15.0), LAPIS, 0.2, 1.1)
    c.paint(tube(c, tail, 2.8, 10.0), PEARL, np.clip(0.0 + 0.05 * np.hypot(X - hx, Y - hy), 0, 0.65), 1.15)
    c.paint(c.circle(hx, hy, 1.9), SAFFRON, 0.0, 1.6)
    c.paint(c.circle(hx, hy, 1.0), PEARL, 0.0, 1.8)
    # the bell tower of Ivan the Great: tall, white, a golden dome
    c.paint(rect(c, 34.5, 9.0, 40.5, 30) | rect(c, 35.2, 4.5, 39.8, 9.0), PEARL, np.where(X > 38.5, 0.45, 0.15))
    for (wy, wh) in ((11.0, 3.0), (17.5, 3.0), (6.0, 2.0)):
        c.paint(rect(c, 36.6, wy, 38.4, wy + wh), UMBER, 0.9, 1.4)
    c.paint(onion(c, 37.5, 3.6, 2.4), SAFFRON, np.clip(0.15 + 0.25 * (X - 36) / 2, 0, 1), 1.3)
    # the cathedral: white walls, five golden onion domes on tall drums, crosses on top
    c.paint(rect(c, 7, 19, 30, 30), PEARL, 0.2)
    for (dx, dy, dr, drum) in ((18.0, 12.5, 4.0, 4.0), (10.5, 16.8, 2.8, 2.5), (25.5, 16.8, 2.8, 2.5)):
        c.paint(rect(c, dx - dr * 0.62, dy + dr * 0.6, dx + dr * 0.62, dy + dr * 0.6 + drum), PEARL, 0.3, 1.1)
        c.paint(rect(c, dx - 0.4, dy + dr * 0.6 + 0.8, dx + 0.4, dy + dr * 0.6 + drum - 0.5), UMBER, 0.9, 1.4)
        c.paint(onion(c, dx, dy, dr), SAFFRON, np.clip(0.1 + 0.6 * np.clip((X - dx + dr * 0.5) / (dr * 1.6), 0, 1), 0, 1), 1.3)
        c.paint(c.line_mask([(dx, dy - dr * 2.0), (dx, dy - dr * 2.0 - 2.0)], 0.5)
                | c.line_mask([(dx - 0.9, dy - dr * 2.0 - 1.2), (dx + 0.9, dy - dr * 2.0 - 1.2)], 0.45), SAFFRON, 0.2, 1.6)
    for wx in (9.5, 13.5, 22.5, 26.5):
        c.paint(rect(c, wx - 0.6, 22, wx + 0.6, 25.5) | c.circle(wx, 22, 0.6), UMBER, 0.9, 1.4)
    # the red Kremlin wall, its merlons capped with snow, and a tower with a green tent roof
    wall = rect(c, -1, 30.0, 45, 34.5) | (rect(c, -1, 28.1, 45, 30.0) & ((tx % 3) != 2))
    c.paint(wall, EMBER, np.clip(0.55 + 0.15 * (ty % 2), 0, 1), 1.2)
    c.paint(rect(c, -1, 27.9, 45, 28.5) & ((tx % 3) != 2), PEARL, 0.05, 1.3)
    c.paint(rect(c, 0.5, 15, 6.5, 34.5), EMBER, np.clip(0.5 + 0.3 * (X > 4.5), 0, 1), 1.25)
    c.paint(c.poly_mask([(0.0, 15.3), (3.5, 5.0), (7.0, 15.3)]), FERN, np.clip(0.5 + 0.3 * (X > 3.5), 0, 1), 1.25)
    c.paint(c.poly_mask([(0.0, 15.3), (7.0, 15.3), (6.0, 13.8), (1.0, 13.8)]), PEARL, 0.05, 1.3)
    c.paint(c.circle(3.5, 4.6, 0.8), SAFFRON, 0.1, 1.5)
    c.paint(rect(c, 2.8, 19, 4.2, 22), UMBER, 0.9, 1.4)
    # the snowy square with soft drifts and footprints, and Pierre in his fur coat gazing up at the comet
    snow = Y > 34.5 + 0.5 * np.sin(X * 0.5)
    drift = np.sin(X * 0.35 + 1.0) * 1.0 + 37.5
    c.paint(snow, PEARL, np.clip(0.05 + 0.3 * (np.abs(Y - drift) < 0.5) + 0.006 * (Y - 33), 0, 1))
    for k in range(6):
        c.paint(ellipse(c, 11 + k * 3.2, 40.6 - k * 0.1 + (k % 2) * 0.8, 0.6, 0.35), PEARL, 0.75, 1.2)
    px, pf = 33.5, 41.4
    c.paint(c.poly_mask([(px - 2.4, pf - 11.0), (px + 2.4, pf - 11.0), (px + 4.0, pf), (px - 4.0, pf)]), UMBER, 0.6, 1.5)
    c.paint(c.line_mask([(px, pf - 9.5), (px + 0.3, pf - 0.5)], 0.4), UMBER, 0.9, 1.5)
    c.paint(tube(c, [(px - 2.0, pf - 10.0), (px - 3.2, pf - 6.0)], 1.5, 1.3), UMBER, 0.75, 1.55)
    c.paint(ellipse(c, px, pf - 11.0, 3.0, 1.3), PEARL, 0.6, 1.55)
    c.paint(c.circle(px - 0.3, pf - 12.9, 1.55) | c.poly_mask([(px - 1.7, pf - 13.6), (px - 2.9, pf - 14.3), (px - 1.8, pf - 12.4)]), EMBER, 0.05, 1.6)
    c.paint(c.circle(px - 0.9, pf - 13.5, 0.35), UMBER, 1.0, 1.9)
    c.paint(c.poly_mask([(px - 0.8, pf - 14.0), (px + 1.8, pf - 12.8), (px + 2.8, pf - 15.6), (px + 0.2, pf - 16.8)]), UMBER, 0.95, 1.65)
    frame(c)
    return encode(c.to_tiles())


# ---------------------------------------------------------------------------
# challenge
# ---------------------------------------------------------------------------

def havisham():
    """Great Expectations: Miss Havisham's room, the curtains drawn for ever. The long table with the
    rotting wedding cake hung with cobwebs, candelabra, the clock stopped at twenty to nine, and the
    figure in the yellowed wedding dress and long veil, leaning on her crutch-headed stick."""
    c = Canvas(42, 44)
    X, Y = c.X, c.Y
    tx, ty = tiles(c)
    # the dark room, its faded wallpaper in dull green stripes
    c.paint(ALL(c), UMBER, np.clip(0.85 + 0.1 * smooth_noise(c, 6, 0.4), 0, 1))
    c.paint((tx % 6) < 2, FERN, np.clip(0.88 + 0.1 * smooth_noise(c, 8, 0.5), 0, 1), 1.05)
    # the heavy curtains drawn across the window, under a gilded pelmet
    curt = rect(c, -1, 2.5, 11, 38.3) & (X < 11 - 2.0 * smoothstep(22, 38, Y))
    c.paint(curt, EMBER, np.clip(0.65 + 0.3 * (np.sin(X * 1.7) > 0.4), 0, 1), 1.1)
    c.paint(rect(c, -1, 0, 12.5, 3.0) | rect(c, -1, -1, 43, 1.6), SAFFRON, 0.75, 1.2)
    c.paint(rect(c, -1, 3.0, 12.5, 4.0) & (tx % 2 == 0), SAFFRON, 0.45, 1.3)
    # the stopped clock, twenty minutes to nine
    cx, cy = 25.5, 7.5
    c.paint(c.circle(cx, cy, 5.0), SAFFRON, 0.6, 1.3)
    c.paint(c.circle(cx, cy, 3.9), PEARL, 0.1, 1.35)
    for k in range(12):
        a = k * math.pi / 6
        c.paint(c.circle(cx + 3.2 * math.sin(a), cy - 3.2 * math.cos(a), 0.5 if k % 3 == 0 else 0.3), UMBER, 0.9, 1.6)
    for (ang, ln, w) in ((8.67 / 12 * 2 * math.pi, 1.9, 0.8), (40 / 60 * 2 * math.pi, 3.0, 0.55)):
        c.paint(c.line_mask([(cx, cy), (cx + ln * math.sin(ang), cy - ln * math.cos(ang))], w), UMBER, 1.0, 1.7)
    # a great cobweb spun across the corner of the ceiling
    web = np.zeros_like(X, bool)
    spokes = [math.radians(a) for a in (95, 118, 141, 164)]
    for a in spokes:
        web |= c.line_mask([(42.5, -0.5), (42.5 + 11 * math.cos(a), -0.5 + 11 * math.sin(a))], 0.5)
    for rr in (4.6, 8.8):
        web |= c.line_mask([(42.5 + rr * math.cos(a), -0.5 + rr * math.sin(a) + 0.4) for a in spokes], 0.45)
    c.paint(web, PEARL, 0.1, 1.45)
    # the long table: dark legs, a yellowed cloth with a scalloped hem, a floor of old boards
    c.paint(rect(c, -1, 38, 43, 45), UMBER, np.clip(0.55 + 0.3 * (ty % 3 == 0), 0, 1))
    c.paint(rect(c, -1, 37.2, 43, 38.3), SAFFRON, 0.85, 1.2)
    c.paint(rect(c, 3.5, 32, 5.0, 38.5) | rect(c, 30.0, 32, 31.5, 38.5), UMBER, 0.98, 1.3)
    cloth = rect(c, 2, 26.5, 32, 33) & (Y < 33 + 0.9 * np.abs(np.sin((X - 2) * math.pi / 4)))
    c.paint(cloth, PEARL, np.clip(0.7 + 0.15 * np.sin(X * 1.6), 0, 1), 1.1)
    # cobweb threads sagging from the top of the cake to the candelabra
    for (ex, ey) in ((6.0, 15.0), (28.5, 15.0)):
        sag = [(17.6 + (ex - 17.6) * t, 10.6 + (ey - 10.6) * t + 1.6 * math.sin(math.pi * t)) for t in np.linspace(0, 1, 9)]
        c.paint(c.line_mask(sag, 0.55), PEARL, 0.1, 1.45)
    # the wedding cake: three leaning tiers with yellowed piping and black mould
    for (x0, x1, y0, y1) in ((10.5, 24.5, 21.5, 27.0), (12.5, 22.5, 17.0, 21.5), (14.8, 20.6, 13.0, 17.0)):
        c.paint(rect(c, x0, y0, x1, y1), PEARL, np.clip(0.05 + 0.25 * (X - x0) / (x1 - x0), 0, 1), 1.3)
        c.paint(rect(c, x0, y1 - 1.0, x1, y1) & (((tx + ty) % 2) == 0), SAFFRON, 0.35, 1.4)
    c.paint(c.circle(17.6, 11.6, 1.6), PEARL, 0.3, 1.35)
    for (mx, my, mr) in ((13.2, 23.6, 0.8), (21.8, 22.6, 0.8), (16.4, 18.6, 0.7), (19.6, 14.6, 0.6)):
        c.paint(c.circle(mx, my, mr), UMBER, 0.85, 1.5)
    # two candelabra with burning candles
    for cx2 in (6.0, 28.5):
        c.paint(rect(c, cx2 - 0.45, 20.5, cx2 + 0.45, 27.0) | ellipse(c, cx2, 26.8, 1.8, 0.7), SAFFRON, 0.5, 1.5)
        c.paint(c.line_mask([(cx2 - 2.4, 19.4), (cx2 - 2.4, 21.0), (cx2, 21.8), (cx2 + 2.4, 21.0), (cx2 + 2.4, 19.4)], 0.65), SAFFRON, 0.5, 1.5)
        for kx in (-2.4, 0.0, 2.4):
            top = 17.0 if kx else 16.2
            c.paint(rect(c, cx2 + kx - 0.45, top, cx2 + kx + 0.45, 19.8 if kx else 20.6), PEARL, 0.0, 1.55)
            flame(c, cx2 + kx, top, 0.9, glow=1.3)
    # Miss Havisham: long veil behind, white hair crowned with flowers, the old dress to the floor, a stick
    hx = 37.0
    c.paint(c.poly_mask([(hx - 1.0, 10.8), (hx + 1.8, 10.6), (hx + 5.4, 40), (hx + 1.0, 41)]), PEARL, 0.0, 1.3)
    dress = c.poly_mask([(hx - 1.9, 15.6), (hx + 1.9, 15.6), (hx + 1.2, 21.5), (hx + 4.6, 43), (hx - 5.0, 43), (hx - 1.2, 21.5)])
    c.paint(dress, PEARL, np.clip(0.45 + 0.2 * (np.sin(X * 1.4) > 0.3) + 0.0 * Y, 0, 1), 1.4)
    c.paint(dress & (np.abs(Y - 21.6) < 0.5), SAFFRON, 0.4, 1.45)
    c.paint(tube(c, [(hx - 1.6, 16.4), (hx - 3.0, 19.8), (hx - 4.3, 21.8)], 1.1, 0.9), PEARL, 0.3, 1.5)
    c.paint(c.circle(hx - 4.5, 22.0, 0.7), EMBER, 0.05, 1.6)
    c.paint(c.line_mask([(hx - 4.8, 22.2), (hx - 5.6, 43)], 0.65) | c.line_mask([(hx - 5.9, 22.0), (hx - 3.6, 22.0)], 0.6), UMBER, 0.95, 1.65)
    c.paint(ellipse(c, hx, 12.9, 1.5, 1.8), EMBER, 0.05, 1.5)
    c.paint(c.circle(hx - 0.6, 12.6, 0.32) | c.circle(hx + 0.6, 12.6, 0.32), UMBER, 1.0, 1.8)
    c.paint((c.circle(hx, 12.2, 1.85) & (Y < 11.9)) | ellipse(c, hx + 1.4, 13.5, 0.6, 1.4), PEARL, 0.25, 1.6)
    for (fx, fy) in ((hx - 1.4, 10.6), (hx, 10.0), (hx + 1.4, 10.4)):
        c.paint(c.circle(fx, fy, 0.5), SAFFRON, 0.15, 1.7)
    frame(c)
    return encode(c.to_tiles())


def candlesticks():
    """Les Miserables: the bishop's simple room at night: the two tall silver candlesticks burning on
    the mantel, the cupboard where the silver is kept, bread on a plate, the traveller's sack and staff
    by the door, stars in the window."""
    c = Canvas(38, 46)
    X, Y = c.X, c.Y
    tx, ty = tiles(c)
    # night-blue plaster walls under a dark ceiling beam, a floor of red tiles
    c.paint(ALL(c), LAPIS, np.clip(0.8 + 0.12 * smooth_noise(c, 4, 0.3), 0, 1))
    c.paint(rect(c, -1, -1, 39, 2.6), UMBER, np.clip(0.7 + 0.2 * (np.sin(X * 0.9) > 0.5), 0, 1), 1.1)
    floor = Y >= 37
    c.paint(floor, EMBER, np.clip(0.5 + 0.3 * (((tx // 4) + (ty // 3)) % 2), 0, 1))
    c.paint(floor & ((((ty - 37) % 3) == 2) | (((tx + 2 * ((ty - 37) // 3)) % 4) == 0)), PEARL, 0.75, 1.1)
    # the starry window, arched, with a cross of glazing bars
    win = rect(c, 27, 6, 37, 20) | c.circle(32, 6, 5)
    c.paint(win, PEARL, 0.5, 1.1)
    pane = rect(c, 28.2, 6, 35.8, 19.0) | c.circle(32, 6, 3.8)
    c.paint(pane, LAPIS, np.clip(1.0 - 0.015 * Y, 0, 1), 1.15)
    for (sx, sy) in ((30.0, 5.0), (34.0, 9.2), (30.2, 15.4), (34.0, 16.0)):
        c.paint(c.circle(sx, sy, 0.5) | c.line_mask([(sx - 1.0, sy), (sx + 1.0, sy)], 0.4) | c.line_mask([(sx, sy - 1.0), (sx, sy + 1.0)], 0.4), SAFFRON, 0.0, 1.5)
    c.paint(pane & ((np.abs(X - 32) < 0.4) | (np.abs(Y - 11.5) < 0.4)), UMBER, 0.85, 1.55)
    c.paint(rect(c, 26.4, 19.6, 37.6, 21.0), PEARL, 0.35, 1.2)
    # the cupboard where the silver is kept
    c.paint(rect(c, 28.5, 24, 36, 37.5), UMBER, 0.85, 1.1)
    c.paint((rect(c, 29.5, 25.5, 31.8, 36) | rect(c, 32.7, 25.5, 35, 36)), UMBER, 0.45, 1.15)
    # the door, its planks and iron hinges; the sack and the staff leaning beside it
    door = rect(c, 1, 9, 10, 37)
    c.paint(door, FERN, np.clip(0.65 + 0.2 * ((tx % 3) == 0), 0, 1), 1.1)
    for hy in (13, 31):
        c.paint(rect(c, 1, hy, 6.5, hy + 0.9), UMBER, 0.9, 1.3)
    c.paint(c.circle(8.6, 23, 0.6), SAFFRON, 0.5, 1.5)
    c.paint(c.line_mask([(9.6, 37.5), (4.2, 10.5)], 0.85), SAFFRON, 0.65, 1.5)
    sack = ellipse(c, 5.2, 34.2, 3.8, 3.6) | c.poly_mask([(3.6, 31.5), (6.8, 31.5), (6.2, 28.4), (4.4, 28.4)])
    c.paint(sack, PEARL, np.clip(0.55 + 0.25 * (X - 4) / 4, 0, 1), 1.4)
    c.paint(rect(c, 4.0, 29.4, 6.6, 30.2), UMBER, 0.8, 1.5)
    # the fireplace: stone surround, dark hearth, glowing embers, a wooden mantel shelf
    c.paint(rect(c, 12.5, 23, 26.5, 37), PEARL, np.clip(0.55 + 0.2 * ((tx + ty // 2) % 2), 0, 1))
    c.paint(rect(c, 15, 26.5, 24, 37) | c.circle(19.5, 26.5, 4.5) & (Y > 23.5), UMBER, 0.95, 1.2)
    c.paint(ellipse(c, 19.5, 36.0, 3.6, 1.4), EMBER, 0.3, 1.4)
    c.paint(c.circle(18.5, 35.0, 0.7) | c.circle(20.6, 34.8, 0.6), SAFFRON, 0.1, 1.5)
    c.paint(rect(c, 11, 21.6, 28, 23.2), UMBER, 0.85, 1.3)
    c.paint(rect(c, 11.5, 23.2, 27.5, 23.8), UMBER, 0.65, 1.3)
    # the two silver candlesticks: broad foot, knopped stem, drip pan, white candle and flame
    for cx in (15.0, 24.0):
        stem = (np.abs(X - cx) < 0.6 + 0.5 * (np.cos((Y - 12) * 1.3) > 0.6)) & (Y > 11.8) & (Y < 20)
        foot = c.poly_mask([(cx - 0.8, 19.2), (cx + 0.8, 19.2), (cx + 2.2, 21.6), (cx - 2.2, 21.6)])
        pan = ellipse(c, cx, 11.6, 1.8, 0.55)
        silver = stem | foot | pan
        c.paint(silver, PEARL, np.clip(0.2 + 0.55 * (X > cx + 0.2) - 0.2 * (np.abs(X - cx + 0.4) < 0.25), 0, 1), 1.6)
        c.paint(rect(c, cx - 0.55, 7.4, cx + 0.55, 11.2), PEARL, 0.0, 1.6)
        flame(c, cx, 7.4, 1.1, glow=2.6)
    # the table with the plate of bread
    c.paint(rect(c, 14, 41, 38, 43) | rect(c, 15.5, 43, 17, 46) | rect(c, 34, 43, 35.5, 46), UMBER, 0.9, 1.3)
    c.paint(rect(c, 14, 41, 38, 41.8), UMBER, 0.45, 1.35)
    c.paint(ellipse(c, 26, 40.7, 6.0, 1.5), PEARL, 0.1, 1.5)
    c.paint(ellipse(c, 26, 39.1, 4.0, 1.9) & (Y < 40.5), SAFFRON, np.clip(0.4 + 0.2 * (Y - 37) / 3, 0, 1), 1.6)
    c.paint(c.line_mask([(24, 38.1), (24.8, 39.3)], 0.4) | c.line_mask([(26.6, 37.9), (27.4, 39.1)], 0.4), SAFFRON, 0.9, 1.7)
    frame(c)
    return encode(c.to_tiles())


# ---------------------------------------------------------------------------
# master
# ---------------------------------------------------------------------------

def netherfield():
    """Pride and Prejudice: the ball at Netherfield. A musicians' gallery with its balustrade, tall
    windows between green panels, candle chandeliers, and the two lines of the dance on a chequered
    floor: gentlemen in dark (and militia red) coats behind, ladies in pale high-waisted gowns in front."""
    c = Canvas(46, 40)
    X, Y = c.X, c.Y
    tx, ty = tiles(c)
    # green panelled wall with cream pilasters
    c.paint(ALL(c), FERN, np.clip(0.55 + 0.25 * (Y - 8) / 16, 0, 1))
    c.paint((((tx + 2) % 7) == 0) & (Y > 8), PEARL, 0.3, 1.1)
    # tall arched windows with glazing bars and red swags
    for wx in (2.0, 23.0, 44.0):
        win = rect(c, wx - 2.6, 11.5, wx + 2.6, 24) | (c.circle(wx, 11.5, 2.6) & (Y < 11.5))
        c.paint(win, LAPIS, np.clip(0.95 - 0.2 * (Y - 9) / 15, 0, 1), 1.2)
        c.paint(win & ((((tx - int(wx)) % 2) == 0) & ((ty % 3) == 0) | (np.abs(X - wx) < 0.35)), PEARL, 0.25, 1.3)
        c.paint(c.poly_mask([(wx - 3.2, 8.4), (wx + 3.2, 8.4), (wx + 3.2, 9.8), (wx, 11.0), (wx - 3.2, 9.8)]), EMBER, 0.55, 1.4)
    # the musicians' gallery: a dark loft, players and instruments, white balusters, a gilt rail
    c.paint(rect(c, -1, -1, 47, 6.0), LAPIS, 0.98, 1.1)
    for k, mx in enumerate(np.arange(4.0, 45, 7.5)):
        c.paint(c.circle(mx, 2.6, 1.0), EMBER, 0.05, 1.5)
        c.paint(c.circle(mx, 2.2, 1.05) & (Y < 2.0), [UMBER, SAFFRON, PEARL][k % 3], 0.5, 1.6)
        c.paint(ellipse(c, mx + 1.8, 4.2, 1.3, 0.7, 0.5), [EMBER, SAFFRON][k % 2], 0.6, 1.55)
    c.paint(rect(c, -1, 4.6, 47, 5.4), SAFFRON, 0.35, 1.35)
    c.paint(rect(c, -1, 5.4, 47, 7.4) & ((tx % 2) == 0), PEARL, 0.2, 1.3)
    c.paint(rect(c, -1, 5.4, 47, 7.4) & ((tx % 2) == 1), UMBER, 0.9, 1.3)
    c.paint(rect(c, -1, 7.4, 47, 8.2), SAFFRON, 0.55, 1.35)
    # candle chandeliers hanging in front of the wall
    for chx in (12.5, 33.5):
        c.paint(c.line_mask([(chx, 8.2), (chx, 11.5)], 0.45), SAFFRON, 0.75, 1.5)
        c.paint(ellipse(c, chx, 13.4, 4.4, 1.5) & ~ellipse(c, chx, 13.1, 3.3, 0.8), SAFFRON, 0.35, 1.55)
        c.paint(c.circle(chx, 15.0, 0.9) | c.circle(chx, 16.4, 0.6), PEARL, 0.05, 1.6)
        for kx in (-3.6, -1.8, 0.0, 1.8, 3.6):
            c.paint(rect(c, chx + kx - 0.35, 11.7, chx + kx + 0.35, 13.0), PEARL, 0.05, 1.6)
            flame(c, chx + kx, 11.7, 0.8)
    # the chequered floor (in tones of polished wood)
    fl = Y >= 25.5
    c.paint(fl, SAFFRON, np.clip(0.62 + 0.38 * ((((tx + ty) // 2) % 2) == 0), 0, 1))
    # the gentlemen's line behind, the ladies' line in front
    coats = [(UMBER, 0.95), (EMBER, 0.65), (LAPIS, 0.9), (UMBER, 0.85), (FERN, 0.95), (EMBER, 0.65), (LAPIS, 0.85), (UMBER, 0.95)]
    for k, gx in enumerate(np.arange(3.0, 46, 5.7)):
        gentleman(c, gx, 28.8, 12.5, *coats[k])
    gowns = [(PEARL, 0.05, LAPIS), (LAPIS, 0.0, PEARL), (PEARL, 0.1, EMBER), (SAFFRON, 0.0, LAPIS), (EMBER, 0.0, PEARL),
             (PEARL, 0.05, FERN), (FERN, 0.0, PEARL), (PEARL, 0.1, SAFFRON)]
    for k, lx in enumerate(np.arange(5.85, 44, 5.7)):
        g, sh, sash = gowns[k]
        lady(c, lx, 40.6, 13.5, g, sh, sash, hair=[0.8, 0.55, 0.95][k % 3])
    frame(c)
    return encode(c.to_tiles())


def boy(c, x, top, smock, hair, hair_shade):
    """A workhouse boy seen from the front behind a table: cropped hair, face, smock (about 5 tiles tall)."""
    c.paint(c.poly_mask([(x - 1.5, top + 2.2), (x + 1.5, top + 2.2), (x + 1.8, top + 5.4), (x - 1.8, top + 5.4)]), smock[0], smock[1], 1.4)
    c.paint(c.circle(x, top + 1.1, 1.1), EMBER, 0.05, 1.5)
    c.paint(c.circle(x, top + 0.8, 1.15) & (c.Y < top + 0.6), hair, hair_shade, 1.6)


def workhouse():
    """Oliver Twist: the workhouse hall at supper. Brick walls, high arched windows, long tables of boys
    with their bowls, the steaming copper at the end, the master in his apron and cap with the ladle,
    and small Oliver who has stepped out to hold up his bowl and ask for more."""
    c = Canvas(44, 42)
    X, Y = c.X, c.Y
    tx, ty = tiles(c)
    # brick walls: courses of two rows of red-brown brick, dark mortar, staggered joints
    course = ty // 3
    shift = (course % 2) * 3
    joint = ((tx + shift) % 6) == 0
    c.paint(ALL(c), EMBER, np.clip(0.6 + 0.3 * ((((tx + shift) // 6) + course) % 3) / 2 + 0.4 * joint, 0, 1))
    c.paint((ty % 3) == 2, PEARL, 0.8, 1.05)
    # high arched windows with small panes
    for wx in (7.0, 19.0, 31.0):
        win = rect(c, wx - 3.2, 3.5, wx + 3.2, 13) | (c.circle(wx, 3.5, 3.2) & (Y < 3.5))
        c.paint(win, PEARL, 0.4, 1.15)
        pane = win & ~(((tx - int(wx - 3.2)) % 3 == 0) | ((ty % 3) == 0)) & (np.abs(X - wx) < 2.6) & (Y < 12.4)
        c.paint(pane, LAPIS, np.clip(0.15 + 0.04 * Y, 0, 1), 1.2)
    # a green painted dado with vertical boards along the lower wall
    dado = (Y >= 16) & (Y < 33)
    c.paint(dado, FERN, np.clip(0.7 + 0.2 * ((tx % 3) == 1), 0, 1), 1.05)
    c.paint(dado & ((tx % 3) == 0), UMBER, 0.85, 1.1)
    c.paint(rect(c, -1, 15.2, 45, 16.2) | rect(c, -1, 32.2, 45, 33.0), SAFFRON, 0.85, 1.2)
    # flagstone floor
    floor = Y >= 33
    c.paint(floor, PEARL, np.clip(0.6 + 0.2 * (((tx // 4) + (ty // 3)) % 2), 0, 1))
    c.paint(floor & (((tx % 4) == 0) | ((ty % 3) == 0)), UMBER, 0.6, 1.05)
    # the back table and its row of boys
    smocks = [(LAPIS, 0.6), (PEARL, 0.7), (LAPIS, 0.75), (UMBER, 0.45), (PEARL, 0.6)]
    hairs = [(UMBER, 0.85), (SAFFRON, 0.4), (UMBER, 0.6), (EMBER, 0.85), (SAFFRON, 0.7)]
    for k, bx in enumerate(np.arange(2.5, 21, 3.5)):
        boy(c, bx, 18.0, smocks[k % 5], *hairs[(k + 2) % 5])
        c.paint(ellipse(c, bx, 23.2, 1.3, 0.6), PEARL, 0.05, 1.5)
    c.paint(rect(c, -1, 23.6, 21, 25.4), UMBER, 0.55, 1.3)
    # the copper: a great round boiler on a brick hearth, a glowing fire door, steam rising
    c.paint(rect(c, 34, 25, 45, 35), EMBER, np.clip(0.75 + 0.2 * ((ty % 2) == 0), 0, 1), 1.2)
    c.paint(rect(c, 37.3, 29.5, 41.7, 33.5) | c.circle(39.5, 29.5, 2.2), UMBER, 0.95, 1.3)
    c.paint(ellipse(c, 39.5, 32.6, 1.9, 1.0), EMBER, 0.25, 1.4)
    c.paint(ellipse(c, 39.5, 31.9, 0.9, 0.7), SAFFRON, 0.05, 1.45)
    cop = ellipse(c, 39.5, 23.5, 6.0, 4.6) & (Y > 19.5)
    c.paint(cop, SAFFRON, np.clip(0.55 + 0.45 * (X - 35) / 9, 0, 1), 1.3)
    c.paint(cop & (np.abs(Y - 23.0) < 0.45), EMBER, 0.9, 1.4)
    c.paint(ellipse(c, 39.5, 19.6, 6.0, 1.3), UMBER, 0.95, 1.35)
    for (sx, sy, sr) in ((38.5, 16.8, 1.6), (40.5, 14.2, 1.8), (38.6, 11.2, 2.0), (40.2, 8.0, 1.8)):
        c.paint(c.circle(sx, sy, sr), PEARL, 0.1, 1.2)
    # the master: a fat man in a white apron and tall cap, ladle in the copper
    mx = 30.5
    c.paint(ellipse(c, mx, 27.0, 4.4, 7.4), UMBER, 0.75, 1.4)
    c.paint(c.poly_mask([(mx - 2.8, 23.0), (mx + 2.8, 23.0), (mx + 3.6, 34.5), (mx - 3.6, 34.5)]), PEARL, 0.05, 1.45)
    c.paint(tube(c, [(mx - 1.6, 33.5), (mx - 1.8, 38.5)], 1.4, 1.4) | tube(c, [(mx + 1.6, 33.5), (mx + 1.8, 38.5)], 1.4, 1.4), UMBER, 0.9, 1.45)
    c.paint(c.circle(mx, 17.8, 2.0), EMBER, 0.1, 1.5)
    c.paint(c.circle(mx - 0.7, 17.4, 0.3) | c.circle(mx + 0.7, 17.4, 0.3), UMBER, 1.0, 1.8)
    c.paint(rect(c, mx - 2.0, 12.8, mx + 2.0, 16.4) | ellipse(c, mx, 12.8, 2.4, 1.3), PEARL, 0.05, 1.55)
    c.paint(tube(c, [(mx + 3.4, 24.0), (mx + 5.6, 21.6), (mx + 7.0, 20.0)], 1.3, 1.1), UMBER, 0.75, 1.55)
    c.paint(c.line_mask([(mx + 7.0, 19.6), (mx + 7.5, 22.0)], 0.6), PEARL, 0.6, 1.6)
    # Oliver, small, stepping up and holding out his empty bowl in both hands
    ox, of = 21.0, 38.5
    c.paint(tube(c, [(ox - 0.6, of - 4.2), (ox - 0.9, of)], 1.0, 0.9) | tube(c, [(ox + 0.6, of - 4.2), (ox + 0.9, of)], 1.0, 0.9), UMBER, 0.95, 1.5)
    c.paint(c.poly_mask([(ox - 1.6, of - 9.6), (ox + 1.6, of - 9.6), (ox + 2.0, of - 3.8), (ox - 2.0, of - 3.8)]), LAPIS, 0.5, 1.5)
    c.paint(c.circle(ox, of - 11.0, 1.35), EMBER, 0.05, 1.55)
    c.paint(c.circle(ox - 0.1, of - 11.4, 1.4) & (Y < of - 11.6), UMBER, 0.55, 1.6)
    c.paint(tube(c, [(ox + 1.2, of - 8.8), (ox + 2.6, of - 10.2), (ox + 3.6, of - 11.6)], 0.85, 0.75), LAPIS, 0.5, 1.55)
    c.paint(tube(c, [(ox - 1.2, of - 8.8), (ox + 0.6, of - 10.4), (ox + 2.6, of - 11.8)], 0.85, 0.75), LAPIS, 0.6, 1.55)
    c.paint(ellipse(c, ox + 3.6, of - 12.6, 1.8, 0.9) & (Y > of - 13.2), PEARL, 0.0, 1.7)
    c.paint(ellipse(c, ox + 3.6, of - 13.0, 1.6, 0.4), UMBER, 0.6, 1.75)
    # the front table across the left of the hall, its boys and their bowls
    smocks2 = [(PEARL, 0.65), (LAPIS, 0.7), (UMBER, 0.5), (LAPIS, 0.55), (PEARL, 0.75)]
    for k, bx in enumerate(np.arange(2.5, 18, 4.0)):
        boy(c, bx, 28.5, smocks2[k % 5], *hairs[k % 5])
    c.paint(rect(c, -1, 33.5, 17.5, 35.5), UMBER, 0.5, 1.3)
    for bx in np.arange(2.5, 18, 4.0):
        c.paint(ellipse(c, bx, 33.4, 1.4, 0.65), PEARL, 0.05, 1.5)
    c.paint(rect(c, 1.5, 35.5, 2.7, 41) | rect(c, 15.2, 35.5, 16.4, 41), UMBER, 0.9, 1.3)
    frame(c)
    return encode(c.to_tiles())


SCENES = {
    "greenlight": greenlight, "christmascarol": christmascarol, "wuthering": wuthering, "comet1812": comet1812,
    "havisham": havisham, "candlesticks": candlesticks, "netherfield": netherfield, "workhouse": workhouse,
}
