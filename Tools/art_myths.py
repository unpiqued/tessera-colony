"""Myths & Legends: eight tile pictures of iconic scenes from myths, epics and legends, drawn with the
supersampled Canvas of art.py (a tile's colour family comes from the dominant object under it, its tone
from the shading). Own compositions throughout: no film or modern designs, no lettering, simple figures,
nothing violent.

Gentle: the Sirens (Odyssey), the Trojan horse (Aeneid), the sword in the stone (Malory), the celestial
rose (Dante's Paradiso, after Dore's engraving).  Challenge: the Monkey King on his cloud (Journey to the
West), Ali Baba's cave (Arabian Nights).  Master: the dragon on its hoard (Beowulf), moon-viewing at the
palace (the Tale of Genji, after the 12th-century scroll).
"""
import math
import random

import numpy as np
from scipy import ndimage

from art import Canvas, LAPIS, SAFFRON, FERN, EMBER, UMBER, PEARL, encode
from art_scenes import ALL, ellipse, rect, tube, frame, smooth_noise


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def tiles(c):
    """Integer tile coordinates of every supersampled pixel (for crisp tile-aligned patterns)."""
    return np.floor(c.X).astype(int), np.floor(c.Y).astype(int)


def snap(v):
    """Round a shade to an exact tone (0, 1/3, 2/3, 1) so a gradient becomes crisp bands without dither."""
    return np.round(np.clip(v, 0, 1) * 3) / 3


def spiral(cx, cy, r0, r1, turns, a0, sense=1, sy=1.0, n=60):
    """Points of a spiral whose radius goes from r0 to r1 over `turns` turns."""
    pts = []
    for i in range(n):
        t = i / (n - 1)
        a = a0 + sense * t * turns * 2 * math.pi
        r = r0 + (r1 - r0) * t
        pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r * sy))
    return pts


def outlined(c, mask, fam, shade, prio=1.3, width=0.6, line=UMBER):
    """Paint `mask` with a dark contour `width` tiles thick round it (so overlapping parts stay apart)."""
    ring = ndimage.binary_dilation(mask, iterations=max(1, int(round(width * 8)))) & ~mask
    c.paint(ring, line, 1.0, prio + 0.05)
    c.paint(mask, fam, shade, prio)


def robed(c, x, foot, h, w=1.0):
    """A simple robed figure: (head mask, body mask) with the feet at (x, foot)."""
    hr = 0.16 * h * w
    head = c.circle(x, foot - h + hr, hr)
    body = c.poly_mask([(x - 0.17 * h * w, foot - h + 2 * hr), (x + 0.17 * h * w, foot - h + 2 * hr),
                        (x + 0.27 * h * w, foot), (x - 0.27 * h * w, foot)])
    return head, body


# ---------------------------------------------------------------------------
# gentle
# ---------------------------------------------------------------------------

def siren(c, x, y, s=1.0):
    """A Siren: a bird with a woman's head and raised golden wings, perched with its feet at (x, y)."""
    for side in (-1, 1):
        wing = c.poly_mask([(x + side * 0.3 * s, y - 3.0 * s), (x + side * 2.9 * s, y - 5.6 * s),
                            (x + side * 2.3 * s, y - 2.9 * s), (x + side * 0.7 * s, y - 1.4 * s)])
        c.paint(wing, SAFFRON, 1 / 3, 1.6)
    body = ellipse(c, x, y - 1.8 * s, 1.05 * s, 1.6 * s) | c.poly_mask([(x - 0.5 * s, y - 1.0 * s),
                                                                     (x + 1.9 * s, y + 0.1 * s), (x + 0.6 * s, y - 0.4 * s)])
    c.paint(body, EMBER, 2 / 3, 1.7)
    c.paint(c.circle(x, y - 4.0 * s, 0.85 * s), PEARL, 0.0, 1.8)


def sirens():
    """Homer's Odyssey: Odysseus bound to the mast as his black ship rows past the Sirens' rocks."""
    c = Canvas(48, 36)
    X, Y = c.X, c.Y
    hz = 14.0
    # a pale dawn sky over the wine-dark sea with long pale swell lines
    c.paint(ALL(c), PEARL, snap(0.4 - 0.45 * Y / hz))
    sea = Y >= hz
    swell = np.sin(Y * 1.5 + np.sin(X * 0.28 + Y * 0.2) * 1.8) > 0.85
    c.paint(sea, LAPIS, snap(0.6 + 0.4 * (Y - hz) / 18 - 0.34 * swell))
    # the Sirens' crags on the right, foam at their feet
    n = smooth_noise(c, 4, 0.8)
    rock = c.poly_mask([(32.5, 36), (33.4, 30), (34.2, 26.5), (34.6, 22.5), (35.2, 20.0), (38.6, 19.8), (39.6, 15.6),
                        (41.0, 11.4), (44.8, 11.2), (46.0, 14.0), (48, 14.6), (48, 36)])
    c.paint(rock, UMBER, snap(0.42 + 0.3 * n + 0.02 * (Y - 10)))
    c.paint(rock & (np.sin(X * 0.9 - Y * 1.3) > 0.8), UMBER, 1.0, 1.05)
    foam = (ellipse(c, 33.2, 28.4, 1.8, 0.7) | ellipse(c, 32.0, 33.6, 2.0, 0.8) | ellipse(c, 34.0, 23.2, 1.3, 0.6)) & ~rock
    c.paint(foam, PEARL, 0.0, 1.2)
    for (sx, sy, s) in ((42.9, 11.3, 1.45), (37.0, 20.0, 1.2), (43.6, 27.0, 1.15)):
        siren(c, sx, sy, s)
    # the black ship: long low hull, ram at the bow (right), stern curling up and over on the left
    hull = c.poly_mask([(4.5, 20.4), (26.5, 20.4), (28.6, 17.4), (29.8, 17.8), (28.4, 21.6), (31.8, 23.4),
                        (28.5, 24.5), (6.5, 24.5)])
    stern = tube(c, [(6.0, 22.5), (3.4, 19.8), (2.8, 16.6), (4.0, 14.0), (6.2, 13.6), (7.0, 14.8)], 2.0, 1.0)
    c.paint(hull | stern, UMBER, 1.0, 1.3)
    c.paint(hull & (Y > 21.2) & (Y < 22.4) & (X < 28.0), EMBER, 1 / 3, 1.4)
    c.paint(c.circle(28.4, 22.8, 0.75), PEARL, 0.0, 1.8)
    # oars dipping into the sea (only below the hull)
    for ox in (9.0, 12.5, 20.0, 23.5):
        c.paint(c.line_mask([(ox, 23.0), (ox - 3.0, 28.4)], 0.55) & ~hull, SAFFRON, 2 / 3, 1.5)
        c.paint(ellipse(c, ox - 3.2, 28.8, 0.45, 0.9, 0.5), SAFFRON, 2 / 3, 1.5)
    # mast, yard and the big square sail bellying in the wind
    c.paint(c.line_mask([(14.0, 1.4), (14.0, 20.5)], 0.75), UMBER, 1.0, 1.4)
    c.paint(c.line_mask([(3.0, 3.4), (25.0, 3.4)], 0.75), UMBER, 1.0, 1.5)
    foot = 12.6 + 0.8 * (1 - ((X - 14) / 10.5) ** 2)
    sail = (np.abs(X - 14) < 10.0 + 0.5 * np.sin((Y - 3.6) / 9.5 * math.pi)) & (Y > 3.8) & (Y < foot)
    brail = ((np.floor(X).astype(int) - 14) % 3 == 0)
    c.paint(sail, SAFFRON, np.where(brail, 1.0, 1 / 3), 1.2)
    # Odysseus, bound to the mast (pale chiton, ropes across it)
    head, body = robed(c, 14.0, 20.5, 6.4, 0.9)
    c.paint(body, PEARL, 0.0, 1.7)
    c.paint(head, EMBER, 0.0, 1.8)
    for ry in (16.6, 18.4):
        c.paint(c.line_mask([(12.6, ry), (15.4, ry + 0.3)], 0.42) & body, UMBER, 1.0, 1.8)
    frame(c)
    return encode(c.to_tiles())


def trojanhorse():
    """Virgil's Aeneid: the great wooden horse on its wheeled platform before the gate of Troy at evening."""
    c = Canvas(40, 44)
    X, Y = c.X, c.Y
    wall_top, ground = 15.0, 33.0
    # evening sky and a low sun
    c.paint(ALL(c), EMBER, snap(0.75 - 0.8 * Y / wall_top))
    c.paint(c.circle(27.0, 12.0, 3.4), SAFFRON, 0.0, 1.1)
    # the walls of Troy: pale stone in courses, two towers, a gate under the horse's belly
    tx, ty = tiles(c)
    course = (((tx + ((ty // 2) % 2) * 2) // 4 + ty // 2) % 2) / 3
    walls = rect(c, 0, wall_top, 40, ground) | rect(c, 0, 7.5, 8, ground) | rect(c, 32, 7.5, 40, ground)
    walls |= (rect(c, 0, wall_top - 1.4, 40, wall_top) & (((X - 0.4) % 2.4) < 1.2))
    walls |= (rect(c, 0, 6.0, 8, 7.5) | rect(c, 32, 6.0, 40, 7.5)) & (((X - 0.4) % 2.4) < 1.2)
    c.paint(walls, PEARL, course + (Y > 25) / 3)
    for (wx, wy) in ((3.5, 11), (36.5, 11), (3.5, 19), (36.5, 19)):
        c.paint(rect(c, wx - 0.6, wy, wx + 0.6, wy + 2.6) | c.circle(wx, wy, 0.6), UMBER, 1.0, 1.6)
    gate = rect(c, 16.5, 26.0, 23.5, ground) | c.circle(20.0, 26.0, 3.5)
    c.paint(gate & (Y < ground), UMBER, 1.0, 1.4)
    # the plain before the walls, the horse's long evening shadow on it
    plain = Y >= ground
    c.paint(plain, SAFFRON, snap(0.2 + 0.45 * (Y - ground) / 11))
    c.paint(plain & ellipse(c, 27.0, 40.8, 14.0, 2.0), SAFFRON, 1.0, 1.05)
    # the horse (facing left): planked barrel body, neck, head, ears, legs, tail
    body = ellipse(c, 21.0, 22.0, 11.0, 5.0)
    neck = c.poly_mask([(9.5, 21.5), (11.8, 17.5), (9.2, 9.0), (12.8, 6.4), (17.5, 13.5), (18.5, 18.5)])
    head = c.poly_mask([(3.6, 12.6), (4.2, 10.8), (8.6, 6.0), (11.2, 5.2), (13.2, 7.6), (11.4, 10.6),
                        (6.8, 13.8), (4.4, 14.0)]) | c.poly_mask([(7.5, 13.4), (11.4, 10.4), (11.6, 14.6)])
    ears = c.poly_mask([(10.0, 6.0), (10.6, 2.8), (12.2, 6.0)])
    legs = np.zeros_like(X, bool)
    for lx in (11.8, 15.2, 26.2, 29.6):
        legs |= rect(c, lx - 1.1, 24.0, lx + 1.1, 36.6)
    tail = tube(c, [(31.6, 19.5), (33.6, 22.5), (34.4, 27.5), (33.8, 31.0)], 2.2, 1.0)
    horse = body | neck | head | ears | legs | tail
    plank = ((ty // 2) % 2) / 3
    c.paint(horse, UMBER, plank + (X > 29.5) / 3, 1.2)
    c.paint(tail | ears | c.line_mask([(12.4, 6.0), (17.8, 15.0)], 1.1), UMBER, 1.0, 1.3)
    c.paint(c.circle(9.4, 8.6, 0.6), UMBER, 1.0, 1.7)
    c.paint(legs & (Y > 35.0), UMBER, 2 / 3, 1.3)
    c.paint(rect(c, 19.0, 20.0, 23.5, 24.0) & ~rect(c, 19.6, 20.6, 22.9, 23.4), UMBER, 1.0, 1.4)
    # wheeled platform
    c.paint(rect(c, 8.0, 36.4, 33.5, 38.0), UMBER, 1.0, 1.4)
    for wx in (10.5, 16.5, 25.0, 31.0):
        c.paint(c.circle(wx, 39.2, 1.7), UMBER, 1.0, 1.5)
        c.paint(c.circle(wx, 39.2, 0.6), SAFFRON, 1 / 3, 1.6)
    frame(c)
    return encode(c.to_tiles())


def swordstone():
    """Malory's Le Morte d'Arthur: a young figure on the stone reaching for the sword in the anvil, in a
    beam of light, with the dark wood and a chapel behind."""
    c = Canvas(36, 46)
    X, Y = c.X, c.Y
    tx, ty = tiles(c)
    # the dark wood: deep green canopy with lighter masses, two trunks
    n = smooth_noise(c, 6, 0.55)
    c.paint(ALL(c), FERN, np.where(n > 0.15, 2 / 3, 1.0))
    for (x0, w) in ((32.2, 3.4), (0.6, 2.4)):
        c.paint(rect(c, x0 - w / 2, 0, x0 + w / 2, 34), UMBER, np.where((tx % 2) == 0, 2 / 3, 1.0))
    # the chapel on the left: grey stone, red roof, bell gable, dark door and lancet window
    c.paint(rect(c, 1.5, 16.6, 10.0, 33.5), PEARL, 2 / 3)
    c.paint(c.poly_mask([(0.6, 17.2), (5.75, 10.6), (10.9, 17.2)]), EMBER, 2 / 3, 1.2)
    c.paint(rect(c, 4.65, 7.4, 6.85, 11.2) | c.poly_mask([(4.45, 7.6), (5.75, 5.8), (7.05, 7.6)]), PEARL, 2 / 3, 1.2)
    c.paint(rect(c, 5.25, 8.4, 6.25, 10.2), UMBER, 1.0, 1.5)
    c.paint(rect(c, 4.65, 27.8, 6.85, 33.5) | c.circle(5.75, 27.8, 1.1), UMBER, 1.0, 1.5)
    c.paint(rect(c, 5.25, 19.4, 6.25, 22.8) | c.circle(5.75, 19.4, 0.5), UMBER, 1.0, 1.5)
    # the grassy clearing
    c.paint(Y > 33.0 + 0.6 * np.sin(X * 0.4), FERN, np.where(Y > 41.5, 1 / 3, 2 / 3))
    # the beam of light falling on the sword
    beam = c.poly_mask([(14.0, 0), (22.0, 0), (25.5, 30.0), (10.5, 30.0)])
    half = 4.0 + 3.5 * Y / 30
    c.paint(beam, PEARL, np.where(np.abs(X - 18) < half * 0.55, 0.0, 1 / 3), 1.0)
    # the stone block (lit top, shaded front with joints) and the anvil on it
    c.paint(c.poly_mask([(10.4, 29.6), (27.0, 29.6), (28.4, 32.0), (9.0, 32.0)]), PEARL, 2 / 3, 1.1)
    front = rect(c, 9.0, 32.0, 28.4, 41.5)
    joint = ((ty - 32) % 3 == 2) | (((tx + 3 * ((ty - 32) // 3)) % 7) == 0)
    c.paint(front, PEARL, np.where(joint, 1.0, 2 / 3), 1.1)
    anvil = rect(c, 11.5, 25.2, 24.5, 27.0) | c.poly_mask([(11.5, 25.2), (9.4, 25.5), (11.5, 27.0)])
    anvil |= rect(c, 14.6, 27.0, 21.4, 28.8) | rect(c, 13.0, 28.8, 23.0, 30.4)
    c.paint(anvil, UMBER, 1.0, 1.4)
    # the sword: steel blade, golden cross-guard and pommel, red leather grip
    c.paint(rect(c, 16.6, 15.6, 19.4, 25.4), LAPIS, np.where(X < 18.0, 0.0, 1 / 3), 1.6)
    guard = rect(c, 12.4, 14.0, 23.6, 15.6) | c.circle(12.4, 14.8, 0.95) | c.circle(23.6, 14.8, 0.95)
    c.paint(guard, SAFFRON, 1 / 3, 1.7)
    c.paint(rect(c, 17.0, 9.2, 19.0, 14.0), EMBER, np.where(ty % 2 == 0, 1.0, 2 / 3), 1.7)
    c.paint(c.circle(18.0, 8.4, 1.4), SAFFRON, 1 / 3, 1.8)
    # the young figure on the stone, reaching up for the grip
    legs = c.line_mask([(24.8, 23.5), (24.2, 29.8)], 1.3) | c.line_mask([(26.6, 23.5), (27.4, 29.8)], 1.3)
    c.paint(legs, LAPIS, 2 / 3, 1.6)
    tunic = c.poly_mask([(23.9, 15.6), (27.3, 15.6), (28.2, 24.2), (23.2, 24.2)])
    c.paint(tunic, EMBER, 2 / 3, 1.6)
    c.paint(rect(c, 23.6, 20.0, 27.8, 20.9), UMBER, 1.0, 1.65)
    c.paint(c.line_mask([(24.2, 16.4), (21.6, 13.4), (19.4, 11.2)], 1.3), EMBER, 2 / 3, 1.65)
    c.paint(c.line_mask([(27.2, 16.4), (28.4, 20.4), (28.2, 22.6)], 1.2), EMBER, 2 / 3, 1.6)
    c.paint(c.circle(19.2, 11.0, 0.8) | c.circle(28.2, 23.0, 0.7), EMBER, 0.0, 1.7)
    c.paint(c.circle(25.6, 13.8, 1.6), EMBER, 0.0, 1.7)
    c.paint(c.circle(25.6, 13.8, 1.6) & ((Y < 13.2) | (X > 26.4)), SAFFRON, 2 / 3, 1.75)
    frame(c)
    return encode(c.to_tiles())


def celestialrose():
    """Dante's Paradiso (after Dore's 1868 engraving): the white-and-gold rose of light seen at a slant,
    tier on tier of round petals filled with tiny souls, rays streaming round it; Dante and Beatrice
    look up from a cloud below."""
    c = Canvas(42, 42)
    X, Y = c.X, c.Y
    tx, ty = tiles(c)
    cx, cy, sq = 21.0, 17.0, 0.74
    dx, dy = X - cx, (Y - cy) / sq
    rho = np.hypot(dx, dy)
    ang = np.arctan2(dy, dx)
    # deep blue heaven with crisp rays
    c.paint(ALL(c), LAPIS, np.where(np.sin(ang * 12) > 0.45, 2 / 3, 1.0))
    # the rose: five tiers of round petals, white and gold in turn, painted from the outside in
    souls = ((tx + 2 * ty) % 4 == 0) & (ty % 2 == 0)
    for k, (R, fam) in enumerate(((20.0, PEARL), (16.4, SAFFRON), (12.9, PEARL), (9.6, SAFFRON), (6.6, PEARL))):
        npet = int(round(2 * math.pi * R / 3.6))
        tier = rho < R - 1.6
        for i in range(npet):
            a = 2 * math.pi * (i + 0.5 * (k % 2)) / npet
            tier |= np.hypot(dx - math.cos(a) * (R - 1.6), dy - math.sin(a) * (R - 1.6)) < 1.75
        base = 1 / 3 if fam == PEARL else 2 / 3
        c.paint(tier, fam, np.where(souls, base - 1 / 3, base))
    # sparks of light in the blue around the rose
    for (sx, sy) in ((3.5, 4.0), (38.5, 3.5), (37.5, 37.0), (24.5, 38.5), (3.0, 27.5), (39.0, 26.0), (30.5, 34.0)):
        c.paint(c.line_mask([(sx - 1.1, sy), (sx + 1.1, sy)], 0.6) | c.line_mask([(sx, sy - 1.1), (sx, sy + 1.1)], 0.6),
                PEARL, 0.0, 1.5)
    # the heart of light
    c.paint(rho < 3.9, SAFFRON, 0.0, 1.2)
    c.paint(rho < 2.2, PEARL, 0.0, 1.3)
    # a cloud below, Dante (red, hooded) and Beatrice (white, golden hair) looking up
    cl = np.zeros_like(X, bool)
    for (a, b, r) in ((3.5, 40.0, 3.2), (8.5, 38.6, 3.4), (14.0, 39.2, 3.0), (18.6, 40.6, 2.4)):
        cl |= c.circle(a, b, r)
    c.paint(cl & (Y > 36.6), LAPIS, np.where(Y < 38.6, 0.0, 1 / 3), 1.1)
    h1, b1 = robed(c, 8.6, 38.4, 8.4)
    c.paint(b1, EMBER, 2 / 3, 1.6)
    c.paint(h1, UMBER, 1 / 3, 1.65)
    h2, b2 = robed(c, 13.0, 38.4, 8.8)
    c.paint(b2, PEARL, 0.0, 1.6)
    c.paint(c.line_mask([(13.9, 33.0), (16.2, 28.8)], 0.85), PEARL, 0.0, 1.6)
    c.paint(h2, SAFFRON, 1 / 3, 1.7)
    frame(c)
    return encode(c.to_tiles())


# ---------------------------------------------------------------------------
# challenge
# ---------------------------------------------------------------------------

def scroll_cloud(c, cx, cy, s, flip=1, prio=1.2):
    """A curling auspicious cloud: a cluster of round lobes with spiral grooves."""
    m = c.circle(cx, cy, 1.9 * s) | c.circle(cx + flip * 2.3 * s, cy + 0.5 * s, 1.5 * s) | \
        c.circle(cx - flip * 2.1 * s, cy + 0.7 * s, 1.3 * s) | ellipse(c, cx, cy + 1.3 * s, 4.0 * s, 0.9 * s)
    c.paint(m, PEARL, 0.0, prio)
    for (ax, ay, r) in ((cx, cy - 0.1 * s, 1.2 * s), (cx + flip * 2.4 * s, cy + 0.6 * s, 0.8 * s)):
        c.paint(c.line_mask(spiral(ax, ay, 0.15 * s, r, 1.1, 0, flip, n=30), 0.36 * max(s, 1.2)) & m,
                LAPIS, 1 / 3, prio + 0.1)
    return m


def monkeyking():
    """Journey to the West: Sun Wukong riding his somersault cloud above the peaks, golden headband on his
    brow, shading his eyes towards the sun, the golden staff held across his body."""
    c = Canvas(42, 46)
    X, Y = c.X, c.Y
    tx, ty = tiles(c)
    c.paint(ALL(c), LAPIS, snap(0.4 - 0.4 * Y / 24))
    # the sun with a ring of short rays
    sx, sy = 34.5, 8.0
    ang = np.arctan2(Y - sy, X - sx)
    rr = np.hypot(X - sx, Y - sy)
    c.paint((rr < 6.6) & (np.sin(ang * 12) > 0.25) & (rr > 4.6), SAFFRON, 1 / 3, 1.1)
    c.paint(rr < 4.4, EMBER, np.where(rr < 2.6, 0.0, 1 / 3), 1.2)
    # karst peaks: tapering pinnacles lit from the left, green behind and blue in front, mist between
    def peaks(spec, fam, lit, shade, avoid=None):
        for (px, top, w) in spec:
            m = (np.abs(X - px) < w * (0.55 + 0.06 * (Y - top))) & (Y > top + 1.6 * (X - px) ** 2 / w)
            if avoid is not None:
                m &= ~avoid
            c.paint(m, fam, np.where(X < px - 0.3, lit, shade))
            c.paint(m & (Y < top + 1.6), FERN, 0.0, 1.1)
    peaks([(3, 24, 3.0), (10.5, 28, 2.6), (27, 26, 3.0), (33.5, 21.5, 3.4), (40.5, 26, 2.6)], FERN, 2 / 3, 1.0)
    mist = (Y > 35.0 + 0.8 * np.sin(X * 0.45)) & (Y < 37.6 + 0.8 * np.sin(X * 0.45))
    c.paint(mist, PEARL, 1 / 3, 1.05)
    peaks([(2.5, 36, 3.0), (14, 39.5, 2.6), (25.5, 38.5, 3.0), (37, 33.5, 3.6)], LAPIS, 2 / 3, 1.0, mist)
    # small clouds and a pair of cranes in the sky
    scroll_cloud(c, 6.0, 5.5, 1.0, 1)
    scroll_cloud(c, 36.5, 24.5, 0.85, -1)
    scroll_cloud(c, 4.5, 17.5, 0.9, 1)
    for (bx, by) in ((25.0, 4.5), (28.5, 2.8)):
        c.paint(c.line_mask([(bx - 1.6, by - 0.6), (bx, by + 0.3), (bx + 1.6, by - 0.6)], 0.5), PEARL, 0.0, 1.5)
    # the somersault cloud with its streaming tail
    tail = tube(c, [(16, 35.5), (10, 38.5), (5, 38.0), (2, 35.5)], 3.6, 1.2)
    c.paint(tail, PEARL, 0.0, 1.25)
    c.paint(tail & (np.abs(Y - 37.4 + 0.25 * (X - 10)) < 0.4) & (X < 14), LAPIS, 1 / 3, 1.3)
    scroll_cloud(c, 20.0, 33.0, 2.0, 1, 1.3)
    scroll_cloud(c, 11.5, 35.5, 1.2, -1, 1.3)
    # the Monkey King: tail, legs and boots, tiger-skin kilt, red tunic with a gold belt
    x0 = 19.0
    c.paint(tube(c, [(x0 - 2.0, 24.0), (x0 - 6.6, 26.8), (x0 - 9.6, 24.4), (x0 - 8.4, 21.6)], 1.1, 0.8),
            UMBER, 1 / 3, 1.5)
    for (pts) in ([(x0 - 1.2, 24.0), (x0 - 3.2, 27.4), (x0 - 3.4, 31.0)], [(x0 + 1.2, 24.0), (x0 + 3.4, 27.0),
                                                                            (x0 + 4.0, 30.6)]):
        c.paint(tube(c, pts, 2.2, 1.9), EMBER, 1.0, 1.5)
        c.paint(c.circle(pts[-1][0] + 0.5, pts[-1][1] + 0.3, 1.2), UMBER, 1.0, 1.55)
    kilt = c.poly_mask([(x0 - 2.6, 20.2), (x0 + 2.6, 20.2), (x0 + 3.8, 25.0), (x0 - 3.8, 25.0)])
    c.paint(kilt, SAFFRON, 1 / 3, 1.5)
    c.paint(kilt & ((tx + ty // 2) % 3 == 0), UMBER, 1.0, 1.55)
    torso = c.poly_mask([(x0 - 3.0, 14.6), (x0 + 3.0, 14.6), (x0 + 2.4, 20.6), (x0 - 2.4, 20.6)])
    c.paint(torso, EMBER, 2 / 3, 1.5)
    c.paint(rect(c, x0 - 2.6, 19.4, x0 + 2.6, 20.6), SAFFRON, 2 / 3, 1.55)
    # the golden staff, held across the body, red-banded at both ends
    staff = c.line_mask([(0.0, 22.7), (42.0, 16.3)], 1.1)
    c.paint(staff, SAFFRON, 1 / 3, 1.7)
    c.paint(staff & ((X < 4.0) | (X > 37.6)), EMBER, 2 / 3, 1.75)
    # arms: the left hand grips the staff, the right hand shades the eyes
    c.paint(c.line_mask([(x0 - 2.6, 15.6), (x0 - 4.2, 18.4), (x0 - 4.0, 19.8)], 1.5), EMBER, 2 / 3, 1.75)
    c.paint(c.circle(x0 - 4.0, 20.2, 0.95), UMBER, 1 / 3, 1.8)
    c.paint(c.line_mask([(x0 + 2.6, 15.4), (x0 + 5.4, 13.2), (x0 + 3.4, 10.0)], 1.5), EMBER, 2 / 3, 1.75)
    c.paint(ellipse(c, x0 + 2.6, 9.6, 1.4, 0.75, 0.3), UMBER, 1 / 3, 1.85)
    # the head: brown fur, pale face, dark eyes, golden headband
    c.paint(c.circle(x0, 11.0, 3.1) | c.circle(x0 - 3.0, 11.6, 1.0), UMBER, 1 / 3, 1.7)
    c.paint(ellipse(c, x0 + 0.6, 12.0, 2.1, 2.2), EMBER, 0.0, 1.75)
    c.paint(c.circle(x0, 11.0, 3.2) & (np.abs(Y - 9.4) < 0.6), SAFFRON, 0.0, 1.8)
    for ex in (x0 - 0.2, x0 + 1.6):
        c.paint(c.circle(ex, 11.4, 0.4), UMBER, 1.0, 1.85)
    frame(c)
    return encode(c.to_tiles())


def jar(c, x, base, s, fam=EMBER):
    """A big storage jar standing at (x, base), lit from the left, with a deeper band round its shoulder."""
    body = ellipse(c, x, base - 3.0 * s, 2.7 * s, 3.0 * s)
    body |= rect(c, x - 0.9 * s, base - 6.8 * s, x + 0.9 * s, base - 4.5 * s)
    body |= rect(c, x - 1.6 * s, base - 7.6 * s, x + 1.6 * s, base - 6.6 * s)
    c.paint(body, fam, np.where(c.X < x - 0.7 * s, 1 / 3, 2 / 3), 1.3)
    c.paint(body & (np.abs(c.Y - base + 4.4 * s) < 0.5), fam, 1.0, 1.35)
    return body


def alibaba():
    """One Thousand and One Nights: 'Open Sesame!' - Ali Baba in the bright rock doorway of the robbers'
    cave, the stone door swung in, heaps of gold, jars, chests, jewels and lamps below him."""
    c = Canvas(44, 42)
    X, Y = c.X, c.Y
    tx, ty = tiles(c)
    sill = 21.0
    # the cave wall: big dark rock blocks
    n = smooth_noise(c, 11, 0.7)
    c.paint(ALL(c), UMBER, np.where(n > 0.1, 2 / 3, 1.0))
    # the doorway: daylight sky and dunes outside, a pale rim, the stone door swung inwards
    door = rect(c, 17.0, 8.0, 27.0, sill) | ellipse(c, 22.0, 8.0, 5.0, 4.8)
    rim = rect(c, 15.6, 8.0, 28.4, sill) | ellipse(c, 22.0, 8.0, 6.4, 6.2)
    c.paint(rim, UMBER, 0.0, 1.1)
    c.paint(door, LAPIS, np.where(Y < 9.0, 0.0, 1 / 3), 1.2)
    c.paint(door & (Y > 16.5 + 0.5 * np.sin(X * 0.8)), SAFFRON, 0.0, 1.2)
    c.paint(c.poly_mask([(28.4, 4.0), (33.0, 6.5), (33.0, 24.0), (28.4, 21.0)]), PEARL, 2 / 3, 1.2)
    c.paint(c.poly_mask([(33.0, 6.5), (34.2, 6.0), (34.2, 23.6), (33.0, 24.0)]), PEARL, 1.0, 1.2)
    # steps down from the sill into the cave
    for k in range(3):
        y0 = sill + 2.0 * k
        c.paint(rect(c, 16.0 - 1.5 * k, y0, 28.0 + 1.5 * k, y0 + 2.0), PEARL, np.where(Y < y0 + 0.9, 1 / 3, 2 / 3), 1.1)
    # a patterned carpet hanging on the left wall
    rug = rect(c, 1.5, 4.0, 12.5, 20.0)
    c.paint(rug, LAPIS, 2 / 3, 1.2)
    c.paint(rect(c, 2.6, 5.1, 11.4, 18.9), EMBER, 2 / 3, 1.25)
    c.paint(c.poly_mask([(7.0, 7.0), (10.2, 12.0), (7.0, 17.0), (3.8, 12.0)]), SAFFRON, 1 / 3, 1.3)
    c.paint(c.poly_mask([(7.0, 9.6), (8.5, 12.0), (7.0, 14.4), (5.5, 12.0)]), LAPIS, 2 / 3, 1.35)
    for (mx, my) in ((4.0, 6.8), (10.0, 6.8), (4.0, 17.2), (10.0, 17.2)):
        c.paint(rect(c, mx - 0.6, my - 0.6, mx + 0.6, my + 0.6), SAFFRON, 1 / 3, 1.35)
    c.paint(rect(c, 1.5, 20.0, 12.5, 21.0) & (np.floor(X).astype(int) % 2 == 0), PEARL, 1 / 3, 1.3)
    # Ali Baba in the doorway, arms raised in wonder
    head, body = robed(c, 22.0, sill, 9.6)
    c.paint(body, EMBER, 2 / 3, 1.6)
    c.paint(c.line_mask([(20.8, 15.4), (18.8, 12.2)], 0.9) | c.line_mask([(23.2, 15.4), (25.2, 12.2)], 0.9),
            EMBER, 2 / 3, 1.6)
    c.paint(rect(c, 20.6, 16.8, 23.4, 17.6), SAFFRON, 2 / 3, 1.65)
    c.paint(head, EMBER, 0.0, 1.7)
    c.paint(ellipse(c, 22.0, 12.1, 1.8, 1.0), PEARL, 0.0, 1.8)
    # hanging lamps on chains
    for (lx, ly) in ((14.2, 4.0), (38.5, 9.0)):
        c.paint(c.line_mask([(lx, 0), (lx, ly - 1.2)], 0.35), SAFFRON, 1.0, 1.4)
        c.paint(ellipse(c, lx, ly, 1.9, 1.1) | c.poly_mask([(lx - 1.0, ly), (lx + 1.0, ly), (lx, ly + 2.4)]),
                SAFFRON, 1 / 3, 1.5)
        c.paint(ellipse(c, lx, ly - 2.0, 0.6, 1.0), EMBER, 0.0, 1.6)
    # two banded chests stacked on the right
    for (x0, y0, x1, y1) in ((32.0, 21.5, 42.5, 28.5), (34.0, 15.0, 42.0, 21.5)):
        c.paint(rect(c, x0, y0 + 1.6, x1, y1) | ellipse(c, (x0 + x1) / 2, y0 + 1.6, (x1 - x0) / 2, 1.6), EMBER, 1.0, 1.3)
        c.paint(rect(c, x0, y0 + 1.6, x1, y1) & ((np.abs(X - x0 - 1.4) < 0.6) | (np.abs(X - x1 + 1.4) < 0.6) |
                                                 (np.abs(Y - y0 - 2.0) < 0.5)), SAFFRON, 1.0, 1.35)
        c.paint(rect(c, (x0 + x1) / 2 - 0.8, y0 + 2.6, (x0 + x1) / 2 + 0.8, y0 + 4.2), PEARL, 0.0, 1.4)
    # heaps of gold coins across the floor (rows of coins as tone bands), low in front of the steps
    heap = (Y > 26.0 + 5.0 * np.cos((X - 22) / 44 * math.pi) ** 2 + 0.8 * np.sin(X * 0.7)) & (Y > 26.5)
    c.paint(heap, SAFFRON, np.where((ty + (tx // 2) % 2) % 2 == 0, 1 / 3, 2 / 3))
    # jewels (cut stones with a bright facet) and three big jars on the heaps
    for k, (gx, gy) in enumerate(((3, 33), (8, 37), (14, 34.5), (30, 34.5), (36, 37), (40.5, 32.5), (4, 39.5),
                                  (24.5, 38.5), (19, 38.5), (34, 30.5), (13, 39.0))):
        fam = (LAPIS, FERN, EMBER)[k % 3]
        c.paint(c.poly_mask([(gx - 1.5, gy), (gx, gy - 1.5), (gx + 1.5, gy), (gx, gy + 1.5)]), fam, 2 / 3, 1.6)
        c.paint(c.poly_mask([(gx - 1.0, gy - 0.1), (gx - 0.1, gy - 1.0), (gx - 0.1, gy - 0.1)]), fam, 0.0, 1.65)
    for (jx, base, s, fam) in ((4.2, 31.0, 1.15, EMBER), (10.8, 31.5, 1.0, EMBER), (15.0, 31.5, 0.7, PEARL)):
        jar(c, jx, base, s, fam)
    for (gx, gy) in ((29.0, 30.5), (12.0, 33.5)):
        cup = c.poly_mask([(gx - 1.6, gy - 3), (gx + 1.6, gy - 3), (gx + 0.4, gy - 1.2), (gx - 0.4, gy - 1.2)])
        cup |= rect(c, gx - 0.35, gy - 1.3, gx + 0.35, gy - 0.4) | rect(c, gx - 1.2, gy - 0.5, gx + 1.2, gy + 0.2)
        c.paint(cup, PEARL, 1 / 3, 1.55)
    crown = c.poly_mask([(19.0, 31.0), (19.0, 27.6), (20.5, 29.4), (22.0, 27.0), (23.5, 29.4), (25.0, 27.6), (25.0, 31.0)])
    c.paint(crown, SAFFRON, 0.0, 1.5)
    c.paint(c.circle(22.0, 29.9, 0.7), EMBER, 1 / 3, 1.6)
    frame(c)
    return encode(c.to_tiles())


# ---------------------------------------------------------------------------
# master
# ---------------------------------------------------------------------------

def dragonhoard():
    """Beowulf: the dragon asleep on its hoard of coins, cups, gems and helmets deep in a cave - seen side on,
    wing half raised, neck arched down so the head rests on the gold, a wisp of smoke at its nostril."""
    c = Canvas(44, 42)
    X, Y = c.X, c.Y
    tx, ty = tiles(c)
    r = random.Random(29)
    # cave wall: dark rock, pale stalactites, blue crystal clusters
    c.paint(ALL(c), UMBER, np.where(smooth_noise(c, 13, 0.8) > 0.2, 2 / 3, 1.0))
    for (x0, w, ln) in ((3, 5, 5), (8, 3, 3), (13, 5, 7), (19, 3, 4), (24, 5, 4), (29, 3, 5), (34, 5, 6), (39, 3, 3)):
        half = np.floor((w - 1) / 2 * (1 - (ty - 1) / ln) + 0.5)
        c.paint((ty <= ln) & (np.abs(tx - x0) <= half), PEARL, np.where(tx < x0, 0.0, 1 / 3), 1.2)
    for (gx, gy, s) in ((3.5, 13.0, 1.1), (40.5, 15.5, 1.1), (6.0, 20.5, 0.8)):
        for a in (-0.55, 0.0, 0.55):
            tipx, tipy = gx + 3.0 * s * math.sin(a), gy - 3.0 * s * math.cos(a)
            c.paint(c.line_mask([(gx, gy + 1.0), (tipx, tipy)], 1.2 * s), LAPIS, np.where(X < gx, 0.0, 1 / 3), 1.3)
    # the hoard: a mound of overlapping gold coins, most with a dark rim
    mound = Y > 25.0 + 0.008 * (X - 24) ** 2 + 0.5 * np.sin(X * 0.8)
    c.paint(mound, SAFFRON, 1.0)
    for k in range(300):
        cx_, cy_ = r.uniform(-1, 45), r.uniform(23, 43)
        c.paint(c.circle(cx_, cy_, 1.45) & mound, UMBER if k % 4 else SAFFRON, 1.0, 1.0)
        c.paint(c.circle(cx_, cy_, 1.15) & mound, SAFFRON, r.choice((0.0, 1 / 3, 1 / 3)), 1.05)
    # treasures on the hoard: helmets, cups, a round shield, gems
    for (hx, hy) in ((40.0, 36.5), (27.5, 39.5), (13.0, 31.0)):
        c.paint(ellipse(c, hx, hy, 2.3, 2.1) & (Y < hy + 0.5), PEARL, np.where(X < hx, 0.0, 1 / 3), 1.5)
        c.paint(rect(c, hx - 2.5, hy + 0.3, hx + 2.5, hy + 1.1) | rect(c, hx - 0.35, hy - 0.4, hx + 0.35, hy + 2.4),
                PEARL, 2 / 3, 1.55)
    for (gx, gy) in ((3.5, 38.5), (33.5, 37.0), (19.5, 41.8)):
        cup = c.poly_mask([(gx - 1.7, gy - 3.4), (gx + 1.7, gy - 3.4), (gx + 0.4, gy - 1.3), (gx - 0.4, gy - 1.3)])
        cup |= rect(c, gx - 0.35, gy - 1.4, gx + 0.35, gy - 0.4) | rect(c, gx - 1.2, gy - 0.6, gx + 1.2, gy)
        c.paint(cup, PEARL, 1 / 3, 1.55)
        c.paint(c.circle(gx, gy - 2.6, 0.5), EMBER, 1 / 3, 1.6)
    c.paint(c.circle(11.0, 38.5, 2.7), LAPIS, 2 / 3, 1.5)
    c.paint(c.circle(11.0, 38.5, 0.9), SAFFRON, 0.0, 1.55)
    for k, (gx, gy) in enumerate(((7.0, 33.5), (24.0, 35.5), (36.5, 40.5), (16.5, 37.0), (42.0, 31.5), (31.0, 41.0),
                                  (22.0, 31.5), (6.0, 41.0), (2.5, 31.0), (28.5, 34.0), (16.0, 32.5), (39.0, 41.0))):
        fam = (EMBER, FERN, LAPIS)[k % 3]
        c.paint(c.poly_mask([(gx - 1.4, gy), (gx, gy - 1.4), (gx + 1.4, gy), (gx, gy + 1.4)]), fam, 1 / 3, 1.6)
    # the dragon, back to front: raised wing, tail, legs, body with its arched neck, spines, head
    tips = [(15.0, 5.0), (23.0, 1.2), (32.0, 2.0), (39.5, 8.5)]
    wing = c.poly_mask([(25.0, 18.0), tips[0], (21.8, 10.5), tips[1], (27.6, 9.5), tips[2], (34.2, 11.5), tips[3],
                        (35.5, 18.0)])
    outlined(c, wing, EMBER, np.where(Y < 9, 1 / 3, 2 / 3), 1.3)
    for tip in tips:
        c.paint(c.line_mask([(27.5, 17.0), tip], 0.8), UMBER, 1.0, 1.4)
    tail = tube(c, [(37.5, 21.0), (41.0, 20.5), (42.6, 25.5), (40.5, 30.5), (36.6, 32.4)], 4.2, 1.5)
    outlined(c, tail, FERN, 1 / 3, 1.35)
    c.paint(c.poly_mask([(37.4, 30.8), (33.0, 32.6), (37.4, 34.4)]), EMBER, 1 / 3, 1.45)
    legs = tube(c, [(35.5, 24.0), (34.5, 28.0), (31.0, 29.8)], 3.6, 2.6) | tube(c, [(23.5, 23.0), (23.0, 27.5),
                                                                                   (20.2, 29.6)], 3.2, 2.4)
    outlined(c, legs, FERN, 1 / 3, 1.36)
    for (fx, fy) in ((19.8, 29.6), (30.6, 29.8)):
        for d in (-0.8, 0.0, 0.8):
            c.paint(c.line_mask([(fx + 0.4, fy + d * 0.5), (fx - 1.2, fy + d * 0.8 + 0.3)], 0.5), PEARL, 0.0, 1.6)
    body = ellipse(c, 29.5, 21.0, 9.0, 5.0) | c.circle(35.5, 22.5, 4.0)
    neck = tube(c, [(22.0, 19.5), (18.0, 13.0), (13.0, 11.8), (9.6, 15.2), (8.2, 20.5)], 4.6, 3.4)
    outlined(c, body | neck, FERN, np.where(Y < 19.0, 2 / 3, 1 / 3), 1.4)
    c.paint(ellipse(c, 29.0, 25.0, 7.0, 1.3) & body, PEARL, 1 / 3, 1.45)
    for (x0, y0, x1, y1) in ((10.4, 12.8, 8.4, 9.4), (14.6, 10.2, 14.0, 6.6), (19.4, 11.6, 21.4, 8.2),
                             (25.0, 16.2, 26.0, 13.0), (36.0, 18.0, 38.6, 15.0)):
        c.paint(c.poly_mask([(x0 - 1.2, y0 + 0.6), (x1, y1), (x0 + 1.2, y0 + 0.8)]), EMBER, 1 / 3, 1.45)
    # the head resting on the gold: long snout, swept-back horns, shut eye, a wisp of smoke
    head = ellipse(c, 8.6, 23.6, 3.2, 2.7) | c.poly_mask([(1.2, 24.6), (2.8, 22.8), (7.0, 21.6), (8.4, 26.2),
                                                         (1.6, 26.8)])
    outlined(c, head, FERN, 1 / 3, 1.5)
    c.paint(head & (Y > 25.4), FERN, 0.0, 1.55)
    for (hx, hy, tipx, tipy) in ((9.6, 21.2, 12.6, 17.6), (11.0, 22.2, 14.4, 20.4)):
        c.paint(c.poly_mask([(hx - 0.7, hy + 0.3), (tipx, tipy), (hx + 0.8, hy + 0.7)]), PEARL, 1 / 3, 1.6)
    c.paint(c.line_mask([(6.8, 23.2), (9.2, 23.4)], 0.5), UMBER, 1.0, 1.7)
    c.paint(c.circle(2.4, 24.2, 0.45), UMBER, 1.0, 1.7)
    for (sx_, sy_, sr) in ((2.2, 20.4, 0.8), (3.4, 18.4, 1.0), (2.6, 16.2, 0.9)):
        c.paint(c.circle(sx_, sy_, sr), PEARL, 0.0, 1.45)
    frame(c)
    return encode(c.to_tiles())


SLANT = 0.9   # the Genji pavilion is drawn in oblique projection: beams run down-right with dx/dy = SLANT


def oblique(pts):
    """Convert (u, y) points (u measured across the slanting beams) to canvas (x, y)."""
    return [(u + SLANT * y, y) for (u, y) in pts]


def lady(c, u, y, robes, s=1.0):
    """A Heian court lady seen from above, head at (u, y) in pavilion coordinates: her robes spread on the
    floor in broad coloured bands (outermost first), long black hair streaming down her back, a pale face."""
    pts = [(-1.8, 0.4), (1.9, 0.4), (4.4, 2.6), (6.2, 6.4), (5.4, 9.0), (0.0, 9.6), (-5.0, 9.0), (-6.2, 6.6),
           (-4.4, 2.6)]
    robe = c.poly_mask(oblique([(u + px * s, y + py * s) for (px, py) in pts]))
    for k, fam in enumerate(robes):
        c.paint(robe, fam, 0.0 if fam == PEARL else 1 / 3, 1.45 + 0.02 * k)
        robe = ndimage.binary_erosion(robe, iterations=int(round(1.15 * s * 8)))
    hair = oblique([(u + 0.2 * s, y + 0.4 * s), (u - 1.4 * s, y + 3.0 * s), (u - 2.8 * s, y + 5.8 * s),
                    (u - 3.8 * s, y + 8.2 * s)])
    c.paint(tube(c, hair, 2.1 * s, 1.2 * s), UMBER, 1.0, 1.6)
    hx, hy = oblique([(u + 0.5 * s, y - 0.3 * s)])[0]
    c.paint(c.circle(hx, hy, 1.3 * s), PEARL, 0.0, 1.65)


def folding_screen(c, x0, y0, panels, pw, ph):
    """A folding screen standing upright: zig-zag gold panels in dark frames, painted across with green hills
    above a blue stream."""
    X, Y = c.X, c.Y
    inner = np.zeros_like(X, bool)
    for p in range(panels):
        z = 0.6 * (p % 2)
        xa, xb = x0 + p * pw, x0 + (p + 1) * pw
        c.paint(rect(c, xa, y0 + z, xb, y0 + z + ph), UMBER, 1.0, 1.5)
        m = rect(c, xa + 0.4, y0 + z + 0.5, xb - 0.4, y0 + z + ph - 0.5)
        c.paint(m, SAFFRON, 0.0 if p % 2 else 1 / 3, 1.55)
        inner |= m
    wave = y0 + ph * 0.66 - 0.7 * np.sin((X - x0) * 0.6)
    c.paint(inner & (Y > wave), LAPIS, np.where(Y > wave + 1.0, 2 / 3, 1 / 3), 1.6)
    hills = Y > y0 + ph * 0.22 + 1.8 * np.abs(np.sin((X - x0) * 0.35))
    c.paint(inner & hills & (Y < wave - 0.7), FERN, 2 / 3, 1.6)


def genji():
    """The Tale of Genji (after the 12th-century scroll): moon-viewing at the palace. A pavilion seen from
    above at a slant with its roof 'blown off': tatami rooms between dark beams, a painted folding screen,
    two court ladies in great layered robes; gold mist across two corners, the full moon in the night sky,
    a garden pond with a red arched bridge."""
    c = Canvas(42, 44)
    X, Y = c.X, c.Y
    tx, ty = tiles(c)
    u = X - SLANT * Y
    # the garden (lower left) and the night sky with the full moon (upper right)
    c.paint(ALL(c), FERN, np.where((tx + 2 * ty) % 5 == 0, 1.0, 2 / 3))
    c.paint(u > 16.6, LAPIS, 1.0)
    c.paint(c.circle(33.0, 6.8, 3.7), PEARL, 0.0, 1.3)
    pond = ellipse(c, 9.0, 38.6, 7.4, 3.6, -0.2)
    c.paint(pond, LAPIS, np.where((ty % 2 == 0) & ((tx + ty) % 4 == 0), 1 / 3, 2 / 3))
    c.paint(c.line_mask([(1.5, 41.0), (5.0, 37.6), (9.5, 36.4), (14.0, 37.2), (17.0, 39.8)], 1.3), EMBER, 1 / 3, 1.5)
    for bx in (4.0, 7.5, 11.5, 15.0):
        c.paint(c.line_mask([(bx, 38.2), (bx, 40.8)], 0.55), EMBER, 2 / 3, 1.5)
    for (rx_, ry_, s_) in ((19.5, 42.0, 1.2), (2.5, 31.5, 1.1)):
        c.paint(ellipse(c, rx_, ry_, 1.6 * s_, 1.1 * s_), PEARL, np.where(Y < ry_, 1 / 3, 2 / 3), 1.3)
    for k, (fx, fy) in enumerate(((2.0, 21.5), (5.0, 26.5), (1.8, 26.0), (10.5, 32.0), (16.0, 35.0), (6.0, 32.0),
                                  (13.0, 34.0))):
        c.paint(c.circle(fx, fy, 0.8) | c.circle(fx + 1.1, fy - 0.6, 0.65), (EMBER, SAFFRON, PEARL)[k % 3], 1 / 3, 1.4)
    # the pavilion: a pale veranda with a red rail on the garden side, a red rail on the far side
    c.paint((u > -11.2) & (u <= -9.0), PEARL, 1 / 3)
    c.paint(((u > -12.1) & (u <= -11.2)) | ((u > 15.8) & (u <= 16.6)), EMBER, 1 / 3, 1.35)
    # three rooms floored with tatami: pale mats in a grid of dark borders, between heavy beams
    floor = (u > -9.0) & (u < 15.0)
    c.paint(floor, FERN, 0.0)
    c.paint(floor & (((u + 9.0) % 4.8 < 0.85) | ((Y % 15.0) % 3.75 < 0.6)), UMBER, 1 / 3, 1.1)
    beams = ((u > -9.8) & (u <= -8.6)) | ((u > 14.4) & (u <= 15.8)) | (floor & ((np.abs(Y - 15.0) < 0.75) |
                                                                              (np.abs(Y - 30.0) < 0.75)))
    c.paint(beams, UMBER, 1.0, 1.3)
    # a painted folding screen in the upper room, a court lady in each of the lower rooms
    folding_screen(c, 3.2, 5.8, 5, 3.4, 7.4)
    lady(c, 3.4, 16.6, (EMBER, SAFFRON, LAPIS, PEARL), 1.3)
    lady(c, 1.0, 31.4, (LAPIS, PEARL, EMBER, SAFFRON), 1.15)
    # golden mist crossing the top-left and bottom-right corners, flecked with gold dust
    gold = np.zeros_like(X, bool)
    for (x0, x1, y0, h) in ((-2, 17, 2.0, 3.6), (-2, 1.5, 6.4, 2.4), (19, 45, 41.8, 3.8), (38, 45, 37.8, 2.4)):
        gold |= ((X > x0) & (X < x1) & (np.abs(Y - y0) < h / 2 + 0.4 * np.sin(X * 0.9))) | \
            c.circle(x0 + 0.1, y0, h / 2) | c.circle(x1 - 0.1, y0, h / 2)
    c.paint(gold, SAFFRON, np.where((tx * 3 + ty * 2) % 7 == 0, 2 / 3, 0.0), 1.8)
    frame(c)
    return encode(c.to_tiles())


SCENES = {
    "sirens": sirens, "trojanhorse": trojanhorse, "swordstone": swordstone, "celestialrose": celestialrose,
    "monkeyking": monkeyking, "alibaba": alibaba, "dragonhoard": dragonhoard, "genji": genji,
}
