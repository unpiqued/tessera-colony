"""Gallery pack: tile homages of eight famous public-domain paintings, drawn with the same supersampled
Canvas as art.py / art_scenes.py (a tile's colour family comes from the dominant object under it, its
tone from the shading).

Gentle: Monet's Impression, Sunrise and Water Lily Pond, Vermeer's Girl with a Pearl Earring, Leonardo's
Mona Lisa.  Challenge: Munch's The Scream, Van Gogh's The Starry Night.  Master: Seurat's La Grande
Jatte (built from tile-aligned dashes) and Klimt's The Kiss (a mosaic of small islands of every colour).
"""
import math
import random

import numpy as np

from art import Canvas, LAPIS, SAFFRON, FERN, EMBER, UMBER, PEARL, encode
from art_scenes import ALL, ellipse, rect, tube, frame, smooth_noise


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def tiles(c):
    """Integer tile coordinates of every supersampled pixel (for crisp tile-aligned patterns)."""
    return np.floor(c.X).astype(int), np.floor(c.Y).astype(int)


def cell_random(c, seed, cw=1, stagger=0):
    """A fixed random value per tile-aligned cell `cw` tiles wide; each row is shifted by
    `stagger` tiles (brick layout), so cells read as short horizontal dashes."""
    tx, ty = tiles(c)
    r = random.Random(seed)
    table = np.array([[r.random() for _ in range(c.w + 8)] for _ in range(c.h + 2)])
    return table[ty, (tx + (ty * stagger) % max(cw, 1)) // cw]


def spiral(cx, cy, r0, r1, turns, a0, sense=1, sx=1.0, sy=1.0, n=80):
    """Points of a spiral whose radius goes from r0 to r1 over `turns` turns."""
    pts = []
    for i in range(n):
        t = i / (n - 1)
        a = a0 + sense * t * turns * 2 * math.pi
        r = r0 + (r1 - r0) * t
        pts.append((cx + math.cos(a) * r * sx, cy + math.sin(a) * r * sy))
    return pts


def silhouette(c, x, foot, h, hat=0.0, w=1.0, skirt=1.4):
    """A small standing figure: head, body widening to `skirt` * w at the feet; `hat` adds a top hat."""
    m = c.circle(x, foot - h + 0.55 * w, 0.55 * w)
    m |= c.poly_mask([(x - 0.3 * w, foot - h + 1.0 * w), (x + 0.3 * w, foot - h + 1.0 * w),
                      (x + skirt * w / 2, foot), (x - skirt * w / 2, foot)])
    if hat:
        m |= rect(c, x - 0.4 * w, foot - h - hat + 0.3, x + 0.4 * w, foot - h + 0.4)
    return m


# ---------------------------------------------------------------------------
# gentle
# ---------------------------------------------------------------------------

def impression_sunrise():
    """Monet, Impression, Sunrise (1872): a hazy harbour, the small orange sun and its broken
    reflection, dark rowing boats in the foreground."""
    c = Canvas(48, 36)
    X, Y = c.X, c.Y
    n = smooth_noise(c, 3, 0.3)
    # a grey hazy sky, bluer toward the top
    c.paint(ALL(c), PEARL, np.where(n + 0.04 * (Y - 12) > -0.05, 1.0, 0.667))
    c.paint(Y < 5.5 + 2.2 * np.sin(X * 0.13 + 2.2) + 1.5 * n, LAPIS, np.where(n > 0.2, 0.0, 0.333))
    # salmon wisps of cloud lit by the sun, streaming up to the right
    for pts, w in (([(19, 9.0), (26, 7.2), (34, 5.0), (43, 3.8)], 1.5), ([(30, 10.5), (38, 9.2), (46, 9.0)], 1.1),
                   ([(8, 7.5), (15, 6.8)], 1.0)):
        c.paint(c.line_mask(pts, w), EMBER, 0.02, 1.1)
    # the far harbour: cranes, masts and chimneys dissolving in the haze
    far = rect(c, 0, 17.2, 17, 19.5) | rect(c, 30, 17.6, 48, 19.5)
    for (mx, top) in ((2.5, 10.5), (5.5, 12.5), (9, 11.0), (13, 13.5), (34, 12.5), (38, 10.0), (41.5, 13), (45, 11.5)):
        far |= c.line_mask([(mx, top), (mx, 18)], 0.75)
    far |= c.line_mask([(38, 10.2), (43.5, 12.2)], 0.7) | c.line_mask([(9, 11.2), (5, 13.2)], 0.7)
    c.paint(far, LAPIS, 1.0, 1.4)
    # the harbour water with long horizontal ripples and pale glints
    water = Y >= 19.5
    rip = 0.5 + 0.5 * np.sin(Y * 2.6 + np.sin(X * 0.35) * 1.4)
    c.paint(water, LAPIS, np.clip(0.45 + 0.4 * (Y - 19.5) / 16 + 0.3 * (rip - 0.5), 0, 1))
    for (x0, x1, yy) in ((2, 8, 24.5), (36, 43, 22.5), (38, 46, 30.5)):
        c.paint(rect(c, x0, yy, x1, yy + 0.9), PEARL, 0.45, 1.2)
    # the sun and its broken reflection
    sx = 25.5
    c.paint(c.circle(sx, 12.0, 2.05), EMBER, 0.3, 1.8)
    for k, (yy, half, dx) in enumerate(((20.2, 1.4, 0.2), (22.2, 2.0, -0.6), (24.2, 1.5, 0.7), (26.2, 2.5, -0.2),
                                         (28.4, 1.8, 0.9), (30.6, 2.9, -0.5), (33.0, 2.2, 0.5))):
        c.paint(rect(c, sx + dx - half, yy, sx + dx + half, yy + 1.0), EMBER, 0.3 + 0.2 * (k % 2), 1.5)
    # three rowing boats, the nearest with a standing oarsman
    for (bx, by, L, fam, sh) in ((16.5, 28.0, 5.5, UMBER, 0.9), (7.0, 22.8, 3.2, UMBER, 0.8), (33.5, 21.2, 2.4, LAPIS, 1.0)):
        c.paint(ellipse(c, bx, by, L, 0.75 * L / 5.5 + 0.35), fam, sh, 1.6)
        c.paint(c.line_mask([(bx - 0.4 * L, by), (bx - 0.4 * L, by - 1.6 * L / 5.5 - 0.6)], 0.9), fam, sh, 1.6)
    c.paint(c.line_mask([(18.5, 27.8), (18.8, 24.0)], 1.1) | c.circle(18.8, 23.6, 0.7), UMBER, 0.95, 1.7)
    c.paint(c.line_mask([(19, 26), (23.5, 30.2)], 0.5), UMBER, 0.9, 1.6)
    c.paint(ellipse(c, 16.5, 30.1, 5.0, 0.6), LAPIS, 1.0, 1.2)
    frame(c)
    return encode(c.to_tiles())


def water_lily_pond():
    """Monet, The Water Lily Pond (1899): the green arched footbridge across the top third, dense
    willow foliage, and a pond of lily pads with a few pink and white flowers."""
    c = Canvas(42, 42)
    X, Y = c.X, c.Y
    n = smooth_noise(c, 7, 0.45)
    # willows and bamboo in deep greens
    c.paint(ALL(c), FERN, np.where(smooth_noise(c, 8, 1.0) > 0.25, 0.667, 1.0))
    # the pond: blue water holding dark vertical reflections of the trees
    water = Y > 19.8 + 0.8 * np.sin(X * 0.3)
    refl = np.sin(X * 0.8 + np.sin(Y * 0.25) * 1.5) + 0.4 * n
    c.paint(water, LAPIS, np.where(refl > 0.4, 1.0, 0.66))
    # drifts of lily pads, growing toward the viewer, with a few pink and white flowers
    r = random.Random(17)
    for row, yy in enumerate((22.0, 24.8, 28.0, 31.6, 35.6, 40.0)):
        rx = 1.3 + 0.4 * row
        x = r.uniform(-2, 1)
        tilt = r.uniform(-0.12, 0.12)
        while x < 44:
            if r.random() < 0.85:
                py = yy + tilt * (x - 21) + r.uniform(-0.3, 0.3)
                c.paint(ellipse(c, x, py, rx * r.uniform(1.0, 1.4), rx * 0.5), FERN, 0.1 + 0.25 * r.random(), 1.2)
                if r.random() < 0.18:
                    fam = EMBER if r.random() < 0.6 else PEARL
                    c.paint(ellipse(c, x + r.uniform(-0.4, 0.4), py - 0.2, 0.8 + 0.1 * row, 0.62 + 0.06 * row),
                            fam, 0.02, 1.7)
            x += rx * r.uniform(1.5, 2.2)
    # the Japanese footbridge: handrail, balusters and deck on a shallow arch, dark beneath
    arch = 0.014 * (X - 21) ** 2
    rail = np.abs(Y - (7.4 + arch)) < 0.75
    deck = (Y > 11.4 + arch) & (Y < 13.5 + arch)
    posts = (Y > 7.4 + arch) & (Y < 12 + arch) & (np.abs((X + 0.9) % 3.6 - 1.8) < 0.5)
    c.paint((Y > 5.5 + arch) & (Y < 12 + arch), FERN, 1.0, 1.1)
    c.paint((Y >= 13.5 + arch) & (Y < 14.8 + arch), UMBER, 0.9, 1.2)
    c.paint(rail | deck | posts, FERN, np.clip(0.0 + 0.12 * (Y - 6 - arch) / 6, 0, 1), 1.5)
    frame(c)
    return encode(c.to_tiles())


def pearl_earring():
    """Vermeer, Girl with a Pearl Earring (c. 1665): a face turning over the shoulder out of a dark
    ground, the blue and yellow turban, the pearl catching the light."""
    c = Canvas(36, 44)
    X, Y = c.X, c.Y
    c.paint(ALL(c), UMBER, 1.0)
    # ochre jacket (her shoulder, turned away to the left) and the white collar
    jacket = c.poly_mask([(1, 44), (2.5, 38), (7, 33.5), (15, 31.5), (25, 32.5), (31, 36.5), (34, 44)])
    c.paint(jacket, SAFFRON, np.clip(0.7 + 0.25 * (X - 12) / 20 + 0.12 * np.sin(X * 0.7 - Y * 0.5), 0, 1))
    for pts in ([(6, 44), (9, 38.5), (12.5, 35.5)], [(24, 44), (25, 39), (27.5, 35.5)]):
        c.paint(c.line_mask(pts, 1.1) & jacket, UMBER, 0.0, 1.2)
    collar = c.poly_mask([(9.5, 33), (16.5, 31.2), (23.5, 32.5), (22, 35.5), (15.5, 35.2), (10.5, 35.6)])
    c.paint(collar, PEARL, np.clip(0.02 + 0.04 * (X - 10), 0, 1), 1.3)
    # the yellow cloth hanging from the crown down the back of the neck
    cloth = c.poly_mask([(22, 8.5), (27.5, 8.5), (29, 16), (28.5, 27), (27, 31.5), (24.2, 31), (24.5, 22), (23.2, 14)])
    c.paint(cloth, SAFFRON, np.clip(0.05 + 0.3 * (X - 23) / 6 + 0.01 * (Y - 8), 0, 1), 1.1)
    c.paint(c.line_mask([(26, 12), (26.8, 21), (26.2, 29)], 0.7) & cloth, UMBER, 0.0, 1.15)
    # neck (in shadow behind the pearl) and the face, lit from the left
    neck = c.poly_mask([(11.5, 26), (21.5, 22), (23.5, 31.5), (12.5, 32.5)])
    c.paint(neck, EMBER, 0.02, 1.1)
    c.paint(neck & (X > 17.5 - 0.3 * (Y - 26)), UMBER, 0.6, 1.15)
    face = c.poly_mask([(9.6, 15.0), (8.9, 16.8), (9.1, 18.6), (8.6, 20.4), (9.0, 22.4), (9.8, 24.2), (10.6, 26.2),
                        (12.8, 27.6), (15.6, 27.2), (18.6, 25.4), (21.2, 22.4), (21.5, 17.5), (20.5, 13.5)])
    c.paint(face, EMBER, 0.333, 1.2)
    c.paint(face & ellipse(c, 13.6, 19.0, 6.4, 8.0, 0.1), EMBER, 0.0, 1.2)
    # turban: blue over the brow and round the back of the head, the yellow knot on top
    turban = c.poly_mask([(8.8, 16.4), (9.8, 11), (13, 7.5), (18, 6.2), (23, 7.5), (25.5, 11), (25.2, 16.5),
                          (23.5, 21.5), (21.4, 22.2), (21.3, 17), (20.4, 13.6), (15, 13.6), (10.6, 14.8)])
    c.paint(turban, LAPIS, np.clip(0.5 + 0.4 * (X - 10) / 15 - 0.25 * (Y < 10), 0, 1), 1.2)
    c.paint(ellipse(c, 23, 8.2, 4.8, 2.6, 0.3), SAFFRON, 0.15, 1.25)
    c.paint(c.line_mask([(11.2, 12.2), (14.5, 9.4), (18, 8.4)], 0.9), PEARL, 0.333, 1.3)
    # eyes, the shadow beside the nose, lips
    for (ex, ey) in ((11.0, 18.5), (16.0, 18.5)):
        c.paint(rect(c, ex, ey, ex + 1, ey + 1), PEARL, 0.0, 1.8)
        c.paint(rect(c, ex + 1, ey - 0.3, ex + 2.9, ey + 1), UMBER, 1.0, 1.8)
    c.paint(c.line_mask([(13.8, 19.6), (13.6, 22.3), (12.4, 22.9)], 0.55), EMBER, 0.2, 1.5)
    c.paint(ellipse(c, 12.9, 24.9, 1.3, 0.55, -0.1), EMBER, 0.667, 1.7)
    # the pearl: a bright drop in the neck's shadow
    c.paint(c.circle(20.3, 26.0, 1.9), UMBER, 0.9, 1.6)
    c.paint(c.circle(20.3, 26.0, 1.25), PEARL, np.clip(0.02 + 0.3 * np.hypot(X - 19.8, Y - 25.5), 0, 1), 1.9)
    frame(c)
    return encode(c.to_tiles())


def mona_lisa():
    """Leonardo, Mona Lisa (c. 1503): the half-length figure with dark hair and dress and folded
    hands, in front of a hazy winding landscape."""
    c = Canvas(36, 48)
    X, Y = c.X, c.Y
    n = smooth_noise(c, 5, 0.5)
    # hazy sky and blue-grey mountains, the horizon higher on the right
    c.paint(ALL(c), LAPIS, 0.0)
    mtn = Y > 8.0 + 2.2 * np.abs(np.sin(X * 0.45)) - 0.1 * (X - 18) + 0.6 * n
    c.paint(mtn, LAPIS, np.where(n > 0.1, 0.667, 0.333))
    lake = (Y > 12.5 - 0.1 * (X - 18)) & (X > 22) & (Y < 16)
    c.paint(lake, LAPIS, 0.05)
    # olive land and ochre rocks: a winding road on the left, a river and a little bridge on the right
    land = Y > 15.5 - 0.12 * (X - 18) + 1.2 * np.sin(X * 0.6) + (X > 22) * 1.5
    c.paint(land, FERN, np.clip(0.75 + 0.2 * n + 0.01 * Y, 0, 1))
    c.paint(land & (smooth_noise(c, 9, 0.9) > 0.35), UMBER, 0.2, 1.05)
    c.paint(c.line_mask([(1, 26), (6, 24), (3, 21.5), (7.5, 19.5), (5, 17.5)], 1.1), SAFFRON, 0.333, 1.3)
    c.paint(c.line_mask([(35, 27), (30, 24.5), (33, 21.5), (29, 19)], 1.2) & land, LAPIS, 0.25, 1.3)
    c.paint(c.line_mask([(29.5, 23.4), (31, 22.4), (32.8, 23.2)], 0.6), UMBER, 0.6, 1.4)
    # the parapet and the dark loggia below it
    c.paint(Y > 27.5, UMBER, 0.333)
    c.paint(Y > 29, UMBER, 0.667)
    # dark dress and the golden-ochre pleated sleeves: arms at her sides, forearms folded at the bottom
    dress = c.poly_mask([(9.5, 21.5), (26.5, 21.5), (31.5, 29), (35, 48), (1, 48), (4.5, 29)])
    c.paint(dress, UMBER, 1.0, 1.1)
    arm_l = tube(c, [(9, 25), (6.5, 31), (6.5, 36), (10, 39.5), (18, 41)], 6.0, 6.4)
    arm_r = tube(c, [(27, 25), (29.5, 31), (29.5, 35.5), (27, 38.5), (23.5, 39.5)], 6.0, 6.0)
    c.paint(arm_l | arm_r, UMBER, 0.0, 1.2)
    c.paint((arm_l | arm_r) & (np.sin((X - 0.6 * Y) * 1.6) > 0.35), SAFFRON, 1.0, 1.25)
    # skin: face, neck and the wide neckline, then the folded hands
    neckline = (Y < 25.2 - 0.07 * (X - 18) ** 2) & (Y > 18) & (np.abs(X - 18) < 8.5)
    skin = ellipse(c, 17.6, 12.6, 4.0, 5.3) | rect(c, 15.6, 16, 20, 21) | neckline
    c.paint(skin, EMBER, np.where(X > 19.8 + 0.3 * np.abs(Y - 13), 0.333, 0.0), 1.3)
    hands = ellipse(c, 21.8, 39.6, 4.6, 1.9, -0.15) | ellipse(c, 16, 41.4, 3.6, 1.7, 0.25)
    c.paint(hands, EMBER, 0.0, 1.5)
    c.paint(c.line_mask([(18.5, 39.8), (25.8, 38.6)], 0.3) & hands, EMBER, 0.333, 1.6)
    # dark hair falling to the shoulders, parted in the middle; eyes, smile
    hair = (ellipse(c, 17.8, 12.2, 5.4, 6.8) & ~ellipse(c, 17.6, 13.3, 3.9, 5.6)) | \
        c.poly_mask([(12.4, 13), (13.8, 13), (13.4, 21), (11, 23.5)]) | \
        c.poly_mask([(21.6, 13), (23.2, 13), (25, 23.5), (22.2, 21)])
    c.paint(hair & (Y > 5.5), UMBER, 0.9, 1.4)
    for ex in (15.9, 19.6):
        c.paint(ellipse(c, ex, 11.9, 1.0, 0.45), UMBER, 0.85, 1.7)
    c.paint(c.line_mask([(16.2, 15.6), (17.7, 15.9), (19.3, 15.5)], 0.4), EMBER, 0.6, 1.7)
    frame(c)
    return encode(c.to_tiles())


# ---------------------------------------------------------------------------
# challenge
# ---------------------------------------------------------------------------

def the_scream():
    """Munch, The Scream (1893): a banded blood-orange sky, swirling blue fjord, the long diagonal
    railing of the bridge and the pale figure with its hands to its face."""
    c = Canvas(40, 48)
    X, Y = c.X, c.Y
    # sky in wavy bands of red, orange and yellow
    phase = Y + 1.4 * np.sin(X * 0.24 + Y * 0.15) + 0.6 * np.sin(X * 0.6)
    band = np.floor(phase / 2.3).astype(int) % 4
    c.paint(ALL(c), EMBER, 0.35)
    c.paint(band == 1, SAFFRON, 0.45)
    c.paint(band == 2, EMBER, 0.75)
    c.paint(band == 3, SAFFRON, 0.1)
    # the fjord: deep blue with swirling lighter currents, a dark curving shore on the left
    fjord = Y > 17 + 1.5 * np.sin(X * 0.3 + 1)
    swirl = np.sin(np.hypot(X - 26, (Y - 24) * 1.8) * 1.3)
    c.paint(fjord, LAPIS, np.clip(0.8 - 0.4 * (swirl > 0.4), 0, 1))
    shore = fjord & (X < 22 - 0.5 * (Y - 18) + 3 * np.sin(Y * 0.5)) & (Y < 30)
    ring = np.sin(np.hypot(X - 2, (Y - 30) * 1.4) * 1.1) > 0.3
    c.paint(shore, FERN, 0.95)
    c.paint(shore & ring, UMBER, 0.85, 1.05)
    head = fjord & (X > 30) & (Y < 21.5 + 0.3 * (X - 30)) & (Y > 18.5 + 0.05 * (X - 30))
    c.paint(head, FERN, 0.9)
    # the bridge deck receding to the upper left, with planks converging
    top = 22.5 + 0.45 * X
    ang = np.arctan2(Y - 21.5, X + 6)
    deck = Y > top + 2.0 + 0.15 * X
    planks = np.floor(ang * 14).astype(int) % 2
    c.paint(deck, EMBER, 0.8)
    c.paint(deck & (planks == 1), SAFFRON, 0.9, 1.05)
    # the railing: a heavy top rail and a lower rail, thickening toward the viewer
    rail = (Y > top) & (Y < top + 0.9 + 0.06 * X)
    low = (Y > top + 1.4 + 0.1 * X) & (Y < top + 2.0 + 0.15 * X)
    c.paint(rail | low, UMBER, 0.45, 1.4)
    # two figures far along the bridge
    for (fx, h) in ((5.0, 5.4), (8.2, 5.9)):
        foot = 22.5 + 0.45 * fx + 5.6
        c.paint(silhouette(c, fx, foot, h, hat=0.9, w=1.3), UMBER, 0.95, 1.6)
    # the figure: a swaying dark body, arms raised to the face, a pale skull-like head
    body = c.poly_mask([(18, 34.5), (21.6, 34.5), (23.8, 36.5), (23, 41), (25, 48), (13, 48), (15.2, 42), (16, 36.5)])
    c.paint(body, UMBER, 0.95, 1.4)
    for side in (-1, 1):
        c.paint(tube(c, [(19.8 + side * 3.0, 38), (19.8 + side * 4.3, 34.5), (19.8 + side * 3.2, 31.5)], 1.7, 1.4),
                UMBER, 0.95, 1.5)
    skull = ellipse(c, 19.8, 29.8, 2.9, 3.4) | ellipse(c, 19.8, 32.0, 1.9, 2.2)
    c.paint(skull | rect(c, 18.9, 33, 20.7, 35), PEARL, np.clip(0.2 + 0.12 * (X - 18), 0, 1), 1.6)
    for side in (-1, 1):
        c.paint(ellipse(c, 19.8 + side * 3.0, 31.0, 0.85, 1.7), PEARL, 0.55, 1.7)
        c.paint(ellipse(c, 19.8 + side * 1.15, 29.3, 0.6, 0.9), UMBER, 0.9, 1.8)
    c.paint(ellipse(c, 19.8, 32.4, 0.55, 0.95), UMBER, 0.9, 1.8)
    frame(c)
    return encode(c.to_tiles())


def starry_night():
    """Van Gogh, The Starry Night (1889): the swirling sky with its great spirals, haloed stars and
    crescent moon, the flame-like cypress, the village and its spire under rolling hills."""
    c = Canvas(48, 38)
    X, Y = c.X, c.Y
    # sky: deep blue with lighter brush-stroke currents
    flow = np.sin(Y * 1.3 + np.sin(X * 0.3) * 2.0 + X * 0.15)
    c.paint(ALL(c), LAPIS, np.where(flow > 0.45, 0.333, np.where(Y + 0.3 * X < 9, 1.0, 0.667)))
    # the great swirl: two interlocking spirals and a long wave, pale strokes with blue haloes
    strokes = [spiral(20, 12, 5.5, 1.0, 1.25, math.pi * 0.9, 1, 1.2, 0.9),
               spiral(31, 10.5, 3.6, 0.8, 1.1, 0.1, -1, 1.1, 0.9),
               [(1, 17), (6, 15.8), (11, 16.5), (16, 17.5), (22, 17), (27, 15), (33, 14.5), (40, 16), (47, 15)]]
    for pts in strokes:
        c.paint(c.line_mask(pts, 2.6), LAPIS, 0.08, 1.1)
    for pts in strokes:
        c.paint(c.line_mask(pts, 1.1), PEARL, 0.3, 1.3)
    # haloed stars and the crescent moon
    for (sx, sy, r) in ((15.5, 3.2, 1.3), (25.5, 3.0, 1.2), (35.5, 4.5, 1.1), (12.5, 20.5, 1.8), (22.5, 19.8, 1.2),
                        (36.5, 16.5, 1.3), (42.5, 13.0, 1.2), (46, 17.5, 1.0), (4.5, 4.5, 1.1)):
        c.paint(c.circle(sx, sy, r * 1.9), LAPIS, 0.02, 1.4)
        c.paint(c.circle(sx, sy, r * 1.3), PEARL, 0.1, 1.5)
        c.paint(c.circle(sx, sy, max(0.9, r * 0.8)), SAFFRON, 0.15, 1.6)
    c.paint(c.circle(42, 5.5, 4.0), SAFFRON, np.clip(0.02 + 0.03 * np.hypot(X - 42, Y - 5.5), 0, 1), 1.4)
    c.paint(c.circle(42, 5.5, 2.8) & ~c.circle(43.4, 4.5, 2.3), EMBER, 0.2, 1.7)
    # rolling hills with pale ridge lines, the dark village below
    ridge = 24.5 - 0.1 * X + 1.2 * np.sin(X * 0.28 + 1) + 0.5 * np.sin(X * 0.7)
    hills = Y > ridge
    c.paint(hills, LAPIS, 1.0)
    c.paint(hills & (Y < ridge + 1.0), LAPIS, 0.35, 1.05)
    for off in (3.0, 6.2):
        c.paint(hills & (np.abs(Y - ridge - off - 0.6 * np.sin(X * 0.4)) < 0.65), FERN, 0.9, 1.05)
    for (hx, hy) in ((14.8, 32.5), (18.0, 33.8), (21.2, 31.8), (32.6, 32.6), (35.8, 30.8), (39.2, 33.2), (42.6, 31.4)):
        wall = rect(c, hx - 1.5, hy, hx + 1.5, hy + 2.8)
        roof = c.poly_mask([(hx - 1.9, hy + 0.1), (hx + 1.9, hy + 0.1), (hx, hy - 1.5)])
        c.paint(wall, PEARL, 0.8, 1.3)
        c.paint(roof, UMBER, 0.6, 1.3)
        c.paint(rect(c, hx - 0.5, hy + 0.9, hx + 0.5, hy + 1.9), SAFFRON, 0.2, 1.6)
    for (tx, ty, tr) in ((24.5, 31.5, 1.8), (31, 34.5, 1.6), (45.5, 34.8, 1.8), (12.8, 35.5, 1.5)):
        c.paint(ellipse(c, tx, ty, tr, tr * 1.3), FERN, 1.0, 1.25)
    # the church and its tall spire
    c.paint(rect(c, 26, 27.5, 30, 34), PEARL, 0.8, 1.4)
    c.paint(c.poly_mask([(27.1, 27.2), (28.9, 27.2), (28, 16.0)]), UMBER, 0.9, 1.6)
    # the cypress: a dark flame rising from the lower left, with green flame tongues
    ys = np.clip((Y - 1.0) / 37, 0, 1)
    half = 0.5 + 5.6 * ys ** 0.8 * (0.8 + 0.2 * np.sin(Y * 1.2))
    cx = 8.5 + 1.2 * np.sin(Y * 0.3)
    cyp = np.abs(X - cx) < half
    c.paint(cyp, UMBER, 1.0, 1.3)
    tongues = cyp & (np.sin((X - cx) * 1.6 - Y * 0.9) > 0.6) & (np.abs(X - cx) < half - 0.8) & (np.sin(Y * 0.7) > -0.3)
    c.paint(tongues, FERN, 1.0, 1.35)
    frame(c)
    return encode(c.to_tiles())


# ---------------------------------------------------------------------------
# master
# ---------------------------------------------------------------------------

def dashes(c, mask, base, mix, seed, stagger=2):
    """Pointillist fill: 3-tile horizontal dashes in a brick layout; each dash is the `base` (family,
    shade) or, by its share, one of `mix` = [(family, share, shade)]."""
    v = cell_random(c, seed, 3, stagger)
    c.paint(mask, base[0], base[1])
    lo = 0.0
    for fam, share, sh in mix:
        c.paint(mask & (v >= lo) & (v < lo + share), fam, sh)
        lo += share


def grande_jatte():
    """Seurat, A Sunday Afternoon on the Island of La Grande Jatte (1884-86): the whole scene built of
    tile dashes - river with boats, trees, sunlit and shadowed grass - and strollers in silhouette."""
    c = Canvas(48, 36)
    X, Y = c.X, c.Y
    # regions of light and shade, each a weave of dashes of similar value but different hue
    river = (X < 12.5 - 0.35 * Y) & (Y > 2.5)
    trees = (Y < 3.5 + 1.2 * np.sin(X * 0.45)) & ~river
    shade = ((Y > 25 - 0.1 * (X - 24) + 1.2 * np.sin(X * 0.35)) | ((Y > 4) & (Y < 8.5 + 2 * np.sin(X * 0.25))
                                                                    & (X < 30))) & ~river & ~trees
    lawn = ~river & ~trees & ~shade
    dashes(c, river, (LAPIS, 0.333), [(LAPIS, 0.25, 0.0), (PEARL, 0.12, 0.0)], 1)
    dashes(c, trees, (FERN, 1.0), [(UMBER, 0.18, 0.667), (LAPIS, 0.14, 1.0)], 2)
    dashes(c, lawn, (FERN, 0.333), [(SAFFRON, 0.26, 0.0), (FERN, 0.16, 0.0), (EMBER, 0.06, 0.0)], 3)
    dashes(c, shade, (FERN, 0.667), [(FERN, 0.25, 1.0), (LAPIS, 0.1, 0.667), (EMBER, 0.06, 0.667)], 4)
    # thin tree trunks rising into the canopy
    for (tx, w, foot) in ((15.5, 1.1, 13), (21.5, 1.0, 10.5), (29, 1.3, 14.5), (33.5, 1.0, 12)):
        c.paint(rect(c, tx - w / 2, 0, tx + w / 2, foot), UMBER, 1.0, 1.3)
    # on the river: a white sail and a long scull with rowers
    c.paint(c.poly_mask([(6.2, 1.5), (6.2, 7.2), (10.2, 7.2)]), PEARL, 0.0, 1.6)
    c.paint(rect(c, 4.5, 7.2, 10.5, 8.2), UMBER, 1.0, 1.6)
    c.paint(rect(c, 0, 13.4, 7, 14.4) | rect(c, 2, 12, 3, 13.4) | rect(c, 4.8, 12, 5.8, 13.4), EMBER, 0.667, 1.6)
    # the couple on the right: the man in a top hat, the woman (in blue) with bustle and parasol, the monkey
    man = c.poly_mask([(43.8, 12), (46.5, 12), (47.2, 34), (43.8, 34)]) | c.circle(45.2, 10.8, 1.2) | \
        rect(c, 44.2, 6.8, 46.2, 10)
    c.paint(man, UMBER, 1.0, 1.6)
    c.paint(ellipse(c, 44.4, 10.9, 0.8, 1.0), EMBER, 0.0, 1.7)
    c.paint(c.poly_mask([(44, 12.4), (45.6, 12.4), (44.8, 15)]), PEARL, 0.0, 1.7)
    woman = c.poly_mask([(38.2, 12.2), (40.2, 12.2), (40.6, 17.5), (43.2, 19.5), (43.3, 23), (42.6, 34),
                         (35.4, 34), (37.2, 22), (38.1, 17.5)]) | c.circle(39.2, 11.1, 1.15)
    c.paint(woman, LAPIS, 1.0, 1.7)
    c.paint(ellipse(c, 38.4, 11.2, 0.55, 0.75), EMBER, 0.0, 1.8)
    c.paint(ellipse(c, 38.6, 8.6, 4.4, 3.0) & (Y < 8.7), UMBER, 1.0, 1.7)
    c.paint(c.line_mask([(38.6, 8.6), (38.2, 14)], 0.45), UMBER, 1.0, 1.7)
    c.paint(ellipse(c, 33.2, 32.6, 1.6, 1.0) | c.circle(31.7, 31.8, 0.8), UMBER, 1.0, 1.7)
    c.paint(c.line_mask([(35.6, 30), (33.8, 31.8)], 0.35), UMBER, 1.0, 1.7)
    # lower left: the reclining boatman, a seated man in a top hat, a woman with a fan
    c.paint(ellipse(c, 6.2, 31.2, 3.6, 1.4, -0.1) | c.circle(1.9, 30.4, 1.1), EMBER, 0.667, 1.7)
    c.paint(c.line_mask([(9, 31.2), (14, 32.2)], 1.1), UMBER, 1.0, 1.7)
    c.paint(c.poly_mask([(5, 23.5), (7.5, 23.5), (9, 29.8), (4.5, 29.8)]) | c.circle(6.2, 22.3, 1.1) |
            rect(c, 5.3, 18.6, 7.1, 21.6), UMBER, 1.0, 1.7)
    c.paint(c.poly_mask([(12, 23.5), (14.4, 23.5), (16, 30.5), (10.5, 30.5)]) | c.circle(13.2, 22.3, 1.1),
            UMBER, 1.0, 1.7)
    # the woman fishing at the water's edge, the girl in white, a woman with an orange parasol, far strollers
    c.paint(silhouette(c, 12.8, 19, 7, w=1.5, skirt=2.0), EMBER, 1.0, 1.7)
    c.paint(c.line_mask([(13, 14), (7.5, 11)], 0.35), UMBER, 1.0, 1.7)
    c.paint(silhouette(c, 26.5, 25.5, 6.5, w=2.0, skirt=2.0), PEARL, 0.0, 1.8)
    c.paint(silhouette(c, 22.5, 24.5, 8.5, w=1.9, skirt=2.1), UMBER, 1.0, 1.7)
    c.paint(ellipse(c, 22.5, 15.2, 3.2, 1.5) & (Y < 15.3), EMBER, 0.333, 1.8)
    c.paint(c.line_mask([(22.5, 15.2), (22.5, 17)], 0.4), UMBER, 1.0, 1.8)
    for (fx, foot, h, fam) in ((31.5, 15, 4.5, LAPIS), (18.5, 13.5, 4.0, UMBER), (25.5, 13, 4.0, EMBER)):
        c.paint(silhouette(c, fx, foot, h, w=1.3, skirt=2.0), fam, 1.0, 1.7)
    c.paint(ellipse(c, 31.5, 10.2, 2.0, 1.1) & (Y < 10.3), PEARL, 0.0, 1.8)
    frame(c)
    return encode(c.to_tiles())


def the_kiss():
    """Klimt, The Kiss (1907-08): the embracing couple as one golden cloak on a flower meadow - his
    robe of black and white rectangles, her dress of coloured circles - on a gold-flecked ground."""
    c = Canvas(42, 42)
    X, Y = c.X, c.Y
    tx, ty = tiles(c)
    # bronze ground flecked with gold
    c.paint(ALL(c), UMBER, np.where(smooth_noise(c, 3, 0.4) > 0.1, 0.333, 0.0))
    c.paint(cell_random(c, 5, 2, 1) < 0.4, SAFFRON, 1.0)
    # the flower meadow, ending in a cliff edge at the lower right
    meadow = ((Y > 26 + 0.3 * X) & (X < 34.5)) | (Y > 38.5)
    c.paint(meadow, FERN, np.where(smooth_noise(c, 8, 0.8) > 0, 0.667, 1.0))
    fv = cell_random(c, 6, 2, 1)
    fl = meadow & ((tx + ty) % 2 == 0)
    for fam, lo, sh in ((EMBER, 0.0, 0.333), (LAPIS, 0.13, 0.333), (PEARL, 0.26, 0.0), (SAFFRON, 0.36, 0.0)):
        c.paint(fl & (fv >= lo) & (fv < lo + 0.11), fam, sh, 1.2)
    # the golden cloak: his robe (upper left) and her dress (lower right)
    cloak = c.poly_mask([(17, 4.5), (25.5, 4.5), (30, 11), (33, 21), (32.5, 30), (30, 36.5), (15, 37), (11, 28.5),
                         (11, 17), (13.5, 9)])
    c.paint(cloak, SAFFRON, np.where(smooth_noise(c, 4, 1.0) > 0.2, 0.333, 0.0), 1.1)
    his = cloak & (X < 25.5 - 0.3 * (Y - 18))
    col = tx // 3
    row_y = ty + 2 * (col % 2)
    cell = his & ((tx % 3) != 2) & ((row_y % 5) != 4)
    rk = random.Random(21)
    kinds = np.array([[rk.random() for _ in range(16)] for _ in range(12)])
    kind = kinds[row_y // 5, col]
    c.paint(cell & (kind < 0.45), UMBER, 1.0, 1.2)
    c.paint(cell & (kind >= 0.45) & (kind < 0.8), PEARL, 0.0, 1.2)
    c.paint(cell & (kind < 0.2) & ((row_y % 5) == 1) & ((tx % 3) == 0), PEARL, 0.333, 1.25)
    hers = cloak & ~his & (Y > 16)
    r = random.Random(12)
    for _ in range(40):
        cx, cy = r.uniform(21, 34), r.uniform(17, 37)
        fam = [EMBER, LAPIS, FERN, PEARL, LAPIS][r.randrange(5)]
        c.paint(c.circle(cx, cy, 1.3) & hers, fam, 0.333, 1.3)
        c.paint(c.circle(cx, cy, 0.45) & hers, SAFFRON, 0.667, 1.4)
    # his head bent down, crowned with ivy; her face tilted back against his shoulder, flowers in her hair
    c.paint(ellipse(c, 21.5, 7.8, 3.8, 3.1, 0.4), UMBER, 1.0, 1.5)
    for (lx, ly) in ((18.2, 5.8), (20.2, 4.5), (22.8, 4.4), (25.2, 5.8)):
        c.paint(c.circle(lx, ly, 0.85), FERN, 0.333, 1.6)
    c.paint(ellipse(c, 24.8, 10.8, 1.6, 2.2, 0.5), EMBER, 0.0, 1.5)
    c.paint(ellipse(c, 29.4, 14.6, 2.0, 2.6, -0.3), UMBER, 0.333, 1.5)
    c.paint(ellipse(c, 26.4, 15.2, 3.2, 2.1, -0.35), EMBER, 0.0, 1.6)
    c.paint(ellipse(c, 23.6, 17.0, 1.7, 1.1, 0.3), EMBER, 0.333, 1.6)
    c.paint(c.line_mask([(25.4, 14.9), (27.0, 14.2)], 0.8), UMBER, 1.0, 2.0)
    for (hx, hy, fam) in ((31, 12.5, EMBER), (31.8, 15.5, LAPIS), (30.2, 17.8, PEARL)):
        c.paint(c.circle(hx, hy, 0.9), fam, 0.333, 1.6)
    # her feet over the edge, with golden tendrils
    c.paint(ellipse(c, 31.5, 37.5, 1.6, 1.0, 0.6), EMBER, 0.0, 1.6)
    for gx in (29.5, 31.2, 33):
        c.paint(c.line_mask([(gx, 36.5), (gx + 0.5, 41)], 0.6), SAFFRON, 0.0, 1.5)
    frame(c)
    return encode(c.to_tiles())


SCENES = {
    "sunrise": impression_sunrise,
    "lilypond": water_lily_pond,
    "pearl": pearl_earring,
    "monalisa": mona_lisa,
    "scream": the_scream,
    "starrynight": starry_night,
    "grandejatte": grande_jatte,
    "kiss": the_kiss,
}
