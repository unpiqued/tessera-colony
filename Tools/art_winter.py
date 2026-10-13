"""Winter pack: eight warm, wintry pictures drawn with the supersampled Canvas of art.py (a tile's colour
family comes from the dominant object under it, its tone from the shading). All designs are original.

Gentle: a snowman in the garden, a cardinal in the snow, the sledding hill, mittens & cocoa.
Challenge: one of Wilson Bentley's snow crystals (from 1885) in a gilt frame; the skating pond after
Currier & Ives (1862).
Master (busy, every colour in many islands): a snow globe with a little village, a frosted window.
"""
import math
import random

import numpy as np

from art import Canvas, LAPIS, SAFFRON, FERN, EMBER, UMBER, PEARL, encode
from art_scenes import ALL, ellipse, rect, tube, frame, smooth_noise
from art_tales import bezier, tiles, sprite


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------

def fir(c, x, base, h, w, shade=0.8, snow=True, prio=1.2):
    """A fir: a short trunk and three stacked tiers with snow on their tips (snow='tiers': also a drift of
    snow along the lower edge of each tier; snow=False: none)."""
    c.paint(rect(c, x - 0.6, base - h * 0.2, x + 0.6, base), UMBER, 0.8, prio)
    for k in range(3):
        y1 = base - h * 0.14 - k * h * 0.25
        hw = w / 2 * (1 - k * 0.24)
        tri = c.poly_mask([(x - hw, y1), (x + hw, y1), (x, y1 - h * 0.45)])
        c.paint(tri, FERN, np.clip(shade + 0.08 * (c.X - x) / max(hw, 0.1), 0, 1), prio)
        if snow == 'tiers':
            c.paint(tri & (c.Y > y1 - h * 0.075) & (np.sin(c.X * 2.2 + k) > -0.6), PEARL, 0.1, prio + 0.05)
        if snow:
            c.paint(tri & (c.Y < y1 - h * 0.37), PEARL, 0.05, prio + 0.05)


def snowfall(c, rng, n, ok, shade=0.0, prio=1.35, x0=1, x1=None, y0=1, y1=None):
    """n single-tile snowflakes at random tiles whose centre passes ok(x, y)."""
    x1 = x1 or c.w - 1
    y1 = y1 or c.h - 1
    done = 0
    for _ in range(n * 20):
        x, y = rng.randrange(x0, x1), rng.randrange(y0, y1)
        if ok(x + 0.5, y + 0.5):
            c.paint(rect(c, x, y, x + 1, y + 1), PEARL, shade, prio)
            done += 1
            if done == n:
                break


# children sitting on sleds, seen from the side facing right (w pompom, h hat, b ribbed brim, f face, e eye,
# s scarf, c coat, a arm, m mitten, t trousers, o boots); RIDER has legs stretched forward, BACKRIDER sits
# behind another child, TOT is a small one on a sled of their own
RIDER = ["..ww......", ".hhhh.....", "hhhhhh....", "bbbbbbb...", ".ffeff....", ".ffffff...", "..ssss....",
         ".cccccc...", "cccccaaam.", "cccccc....", "cccccttt..", ".....tttoo"]
BACKRIDER = RIDER[:9] + ["cccccc....", "cccccc...."]
TOT = [".ww.....", "hhhh....", "bbbbb...", "ffef....", ".fff....", "cccca...", "ccccam..", "cccctt..", "....ttoo"]


def kid(c, x0, y0, rows, coat, hat, scarf=None, prio=1.7):
    """Paint one of the child sprites with its top-left tile at (x0, y0); the scarf defaults to the coat."""
    pal = {'w': (PEARL, 0.05), 'h': (hat, 0.35), 'b': (hat, 0.8), 'f': (EMBER, 0.0), 'e': (UMBER, 1.0),
           's': (scarf, 0.4) if scarf is not None else (coat, 0.55), 'c': (coat, 0.4), 'a': (coat, 0.75), 'm': (hat, 0.5),
           't': (UMBER, 0.5), 'o': (UMBER, 0.95)}
    sprite(c, x0, y0, rows, pal, prio)


# ---------------------------------------------------------------------------
# gentle
# ---------------------------------------------------------------------------

def snowman():
    """A three-ball snowman waving his stick arms in a snowy garden at dusk: red knit hat, green scarf with
    a red stripe, carrot nose, coal eyes and buttons; firs and a rail fence behind, snow falling."""
    c = Canvas(40, 46)
    X, Y = c.X, c.Y
    rng = random.Random(11)
    c.paint(ALL(c), LAPIS, np.clip(0.95 - 0.55 * Y / 30, 0, 1))
    # snowy firs at the far edge of the garden, clear of the arms
    for (px, h, w) in ((3.5, 12, 7.5), (8.8, 8.5, 5.5), (35.5, 12.5, 7.5), (30.5, 8, 5)):
        fir(c, px, 30.0, h, w, snow=False)
    # the rail fence with snow on the posts
    for fx in np.arange(1.6, 40, 4.4):
        c.paint(rect(c, fx - 0.6, 26.6, fx + 0.6, 33.0), UMBER, 0.35, 1.25)
        c.paint(ellipse(c, fx, 26.6, 0.9, 0.6), PEARL, 0.05, 1.3)
    c.paint(rect(c, 0, 28.0, 40, 29.0) | rect(c, 0, 30.8, 40, 31.8), UMBER, 0.45, 1.2)
    # the snowy garden, blue in the dusk, with lit drift crests
    ground = Y > 31.5 + 0.8 * np.sin(X * 0.3 + 1.0)
    c.paint(ground, LAPIS, np.clip(0.05 + 0.25 * (Y - 31) / 14, 0, 1))
    c.paint(ellipse(c, 26.5, 42.6, 9.5, 1.9), LAPIS, 0.55, 1.15)
    # three balls of snow, lit from the upper left
    for (bx, by, br) in ((20, 36.3, 6.8), (20, 26.2, 5.0), (20, 17.4, 4.0)):
        ball = c.circle(bx, by, br)
        lit = np.clip(((X - bx) * 0.55 + (Y - by) * 0.85) / br, 0, 1)
        c.paint(ball, PEARL, np.clip(0.0 + 0.62 * lit ** 1.5, 0, 1), 1.3)
        c.paint(ball & ~c.circle(bx - 0.5, by - 0.6, br - 0.4) & (Y > by), PEARL, 0.85, 1.32)
    # stick arms raised in a wave, with twig fingers
    for pts in ([(15.4, 24.0), (10.2, 18.6), (8.2, 14.2)], [(10.2, 18.6), (6.8, 18.2)],
                [(24.6, 24.0), (29.8, 19.0), (32.4, 15.2)], [(29.8, 19.0), (33.4, 19.0)]):
        c.paint(c.line_mask(pts, 0.8), UMBER, 0.85, 1.6)
    # coal buttons, eyes and mouth; the carrot nose
    for (px, py) in ((20, 25.0), (20, 27.8), (20, 33.0)):
        c.paint(c.circle(px, py, 0.72), UMBER, 0.95, 1.7)
    for ex in (18.3, 21.7):
        c.paint(c.circle(ex, 16.3, 0.75), UMBER, 1.0, 1.8)
    for (mx, my) in ((18.2, 19.5), (20.0, 20.1), (21.8, 19.5)):
        c.paint(c.circle(mx, my, 0.45), UMBER, 0.9, 1.8)
    c.paint(c.poly_mask([(19.6, 17.1), (19.6, 18.7), (25.6, 18.3)]), EMBER, 0.45, 1.8)
    # green scarf: a wrap round the neck and an end with a red stripe hanging down the front
    wrap = ellipse(c, 20, 21.9, 5.4, 1.7)
    tail = c.poly_mask([(20.4, 22.0), (23.8, 22.0), (25.6, 31.0), (22.2, 31.3)])
    c.paint(wrap | tail, FERN, np.clip(0.35 + 0.25 * (X - 15) / 10, 0, 1), 1.6)
    c.paint(tail & (np.abs(Y - 27.4) < 0.8), EMBER, 0.45, 1.65)
    # red knit hat: tall round dome with a white stripe, ribbed cuff, white pompom
    dome = ellipse(c, 20, 13.6, 4.6, 5.4) & (Y < 13.6)
    c.paint(dome, EMBER, np.clip(0.3 + 0.3 * (X - 16) / 8, 0, 1), 1.6)
    c.paint(dome & (np.abs(Y - 10.6) < 0.6), PEARL, 0.1, 1.65)
    c.paint(rect(c, 15.0, 12.8, 25.0, 15.2), EMBER, np.where((X % 1.0) < 0.5, 0.65, 0.9), 1.7)
    c.paint(c.circle(20, 7.6, 1.7), PEARL, 0.05, 1.7)
    # falling snow
    snowfall(c, rng, 50, lambda x, y: y < 31 and math.hypot(x - 20, (y - 22) * 0.6) > 8.0
             and not (5 < x < 35 and 12 < y < 25))
    snowfall(c, rng, 10, lambda x, y: 5 < x < 35 and 12 < y < 25 and math.hypot(x - 20, (y - 20) * 0.7) > 7.5)
    frame(c)
    return encode(c.to_tiles())


def cardinal():
    """A bright red cardinal perched on a snow-laden spruce bough against a soft grey-blue winter sky."""
    c = Canvas(44, 42)
    X, Y = c.X, c.Y
    c.paint(ALL(c), LAPIS, np.clip(0.42 - 0.32 * (X + 0.6 * Y) / 64 + 0.12 * smooth_noise(c, 2, 0.25), 0, 1))
    # big soft out-of-focus snowflakes and a few small ones falling
    for (bx, by, br) in ((6, 6, 2.4), (32, 15, 1.6), (4, 21, 1.6), (40, 33, 2.2), (25, 3, 1.3)):
        c.paint(c.circle(bx, by, br), PEARL, np.clip(0.4 * np.hypot(X - bx, Y - by) / br, 0, 1), 1.05)
    snowfall(c, random.Random(8), 14, lambda x, y: (y < 20 and x > 26) or (x < 10 and 10 < y < 30) or (y > 36 and x > 12))

    def bough(path, length, w_twig, cap_w, seed):
        """A spruce twig with needles fanning forward on both sides and a lumpy cap of snow on top."""
        dense = [(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t) for (a, b) in zip(path[:-1], path[1:])
                 for t in np.linspace(0, 1, int(math.hypot(b[0] - a[0], b[1] - a[1]) * 1.6))]
        needles = np.zeros_like(X, bool)
        for i, (px, py) in enumerate(dense):
            ang = math.atan2(path[-1][1] - path[0][1], path[-1][0] - path[0][0])
            for side in (-1, 1):
                a = ang + side * 1.0 + 0.2 * math.sin(i * 1.7)
                needles |= c.line_mask([(px, py), (px + length * math.cos(a), py + length * math.sin(a))], 0.6)
        c.paint(needles, FERN, np.clip(0.62 + 0.3 * np.sin(X * 1.7 + Y * 2.3), 0, 1), 1.2)
        c.paint(tube(c, path, w_twig, w_twig * 0.6), UMBER, 0.75, 1.3)
        cap = tube(c, [(px, py - cap_w * 0.62) for (px, py) in path], cap_w, cap_w * 0.7)
        cap &= smooth_noise(c, seed, 1.1) > -0.5
        c.paint(cap, PEARL, np.clip(0.02 + 0.1 * smooth_noise(c, seed + 1, 0.6), 0, 0.4), 1.35)

    bough([(-1, 37.0), (12, 33.6), (26, 29.8), (45, 25.0)], 3.4, 1.5, 3.0, 9)
    bough([(36, 26.6), (43, 32.5)], 2.6, 0.8, 2.0, 12)
    bough([(45, 6.5), (37, 9.0), (30, 9.6)], 2.8, 0.9, 2.2, 14)
    # the cardinal (feet at fx, fy, scale s): body, neck, head with its pointed crest, all bright red
    fx, fy, s = 21.0, 29.0, 1.12
    P = lambda u, v: (fx + u * s, fy + v * s)
    body = ellipse(c, *P(0.5, -6.4), 6.2 * s, 5.0 * s, -0.55)
    head = c.circle(*P(-4.7, -13.4), 3.7 * s) | tube(c, [P(-4.0, -12.5), P(-1.0, -9.0)], 5.0 * s, 6.0 * s)
    crest = c.poly_mask([P(-7.3, -15.8), P(-1.6, -21.6), P(-1.1, -13.6)])
    bird = body | head | crest
    c.paint(bird, EMBER, np.clip(0.28 + 0.3 * ((X - fx + 9) * 0.4 + (Y - fy + 21) * 0.6) / 15, 0, 1), 1.5)
    wing = ellipse(c, *P(2.6, -6.4), 5.4 * s, 2.9 * s, -0.65)
    c.paint(wing, EMBER, 0.78, 1.55)
    for k in range(3):
        quill = c.line_mask([P(-0.4 + k * 1.6, -5.2 + k * 1.3), P(4.2 + k * 1.4, -8.6 + k * 1.4)], 0.42)
        c.paint(quill & wing, EMBER, 1.0, 1.6)
    # the long tail, hanging down in front of the bough
    tail = c.poly_mask([P(3.6, -4.6), P(6.4, -6.4), P(14.6, 5.0), P(12.0, 7.6), P(9.6, 6.6)])
    c.paint(tail, EMBER, np.clip(0.62 + 0.02 * (Y - fy), 0, 1), 1.6)
    c.paint(c.line_mask([P(5.4, -4.6), P(12.0, 6.0)], 0.45) & tail, EMBER, 1.0, 1.65)
    # black mask, orange cone beak, eye; feet gripping the bough
    c.paint(c.poly_mask([P(-9.5, -13.6), P(-6.3, -15.2), P(-3.9, -13.8), P(-4.3, -10.2), P(-7.5, -10.0), P(-9.3, -11.4)]),
            UMBER, 0.95, 1.7)
    c.paint(c.poly_mask([P(-8.1, -14.6), P(-8.1, -11.0), P(-12.2, -12.5)]), SAFFRON, 0.75, 1.8)
    c.paint(c.circle(*P(-5.3, -13.7), 0.55), PEARL, 0.1, 1.85)
    for du in (-1.0, 1.2):
        c.paint(c.line_mask([P(du, -2.0), P(du - 0.3, 0.6)], 0.5), UMBER, 0.85, 1.6)
    frame(c)
    return encode(c.to_tiles())


def sledding():
    """A long snowy hill falls diagonally across the picture: three children ride a wooden toboggan down
    the middle, a small one on a red sled sets off from the crest and another reaches the run-out; firs on
    the slope, a far snowy plain and a pale sun beyond."""
    c = Canvas(48, 36)
    X, Y = c.X, c.Y
    c.paint(ALL(c), LAPIS, np.clip(0.42 - 0.4 * Y / 26, 0, 1))
    c.paint(c.circle(41, 6.0, 2.6), SAFFRON, 0.05, 1.2)
    # the far snowy plain
    c.paint(Y > 23.5 + 0.8 * np.sin(X * 0.5), PEARL, 0.45)
    # the big hill: steep at the top left, flattening towards the right
    surf = lambda x: 7.0 + 24.0 * x / 48.0 + 3.0 * np.sin(np.pi * np.clip(x, 0, 48) / 48.0)
    hill = Y > surf(X)
    c.paint(hill, PEARL, np.clip(0.02 + 0.03 * (Y - surf(X)), 0, 0.5))
    # snowy firs on the crest and on the near slope
    for (px, base, h, w) in ((2.0, 10.0, 9, 5.0), (4.0, 35.5, 13, 7.5), (11.2, 36.0, 9, 6.0)):
        fir(c, px, base, h, w, snow=False)

    def board(x0, x1, fam, w, curl=2.0):
        """A sled deck along the slope from x0 to x1, its front curling up."""
        y0, y1 = float(surf(x0)) - 0.3, float(surf(x1)) - 0.3
        pts = [(x0, y0), (x1, y1)] + bezier((x1, y1), (x1 + 1.4 * curl, y1 + 0.3), (x1 + 1.1 * curl, y1 - 1.6 * curl), 8)
        c.paint(c.line_mask(pts, w), fam, 0.55, 1.6)

    # a small child on a red sled near the top
    board(5.5, 11.5, EMBER, 1.1, 1.2)
    kid(c, 6, int(round(float(surf(8)))) - 10, TOT, SAFFRON, EMBER)
    # three children on the wooden toboggan, each holding on to the one in front
    board(14.0, 35.0, UMBER, 1.5, 1.8)
    for (x0, rows, coat, hat, scarf) in ((15, BACKRIDER, FERN, EMBER, None), (21, BACKRIDER, SAFFRON, FERN, None),
                                          (27, RIDER, EMBER, SAFFRON, PEARL)):
        kid(c, x0, int(round(float(surf(x0 + 3)))) - 12, rows, coat, hat, scarf)
    # one more reaching the run-out on a red sled
    board(39.0, 45.0, EMBER, 1.1, 1.2)
    kid(c, 39, int(round(float(surf(41)))) - 10, TOT, LAPIS, EMBER)
    frame(c)
    return encode(c.to_tiles())


def cocoa():
    """A close-up still life: a red mug of cocoa heaped with marshmallows, steam curling up against the
    snowy night window, beside a pair of patterned knitted mittens on the wooden table."""
    c = Canvas(46, 40)
    X, Y = c.X, c.Y
    rng = random.Random(3)
    # lamplit striped wallpaper and the night window behind the mug
    c.paint(ALL(c), SAFFRON, np.where(np.floor(X / 2.0) % 2 == 0, 0.0, 0.34))
    win = rect(c, 1, 1, 24.5, 17.5)
    c.paint(win, LAPIS, np.clip(0.98 - 0.3 * Y / 18, 0, 1))
    snowfall(c, rng, 18, lambda x, y: 2 < x < 24 and 1 < y < 17 and not (4.5 < x < 20.5), shade=0.0)
    c.paint(win & ~rect(c, 1.8, 1.8, 23.7, 16.7), UMBER, 0.55, 1.2)
    c.paint(rect(c, 12.3, 1, 13.1, 17.5) | rect(c, 1, 8.8, 24.5, 9.6), UMBER, 0.55, 1.2)
    c.paint(rect(c, 0.5, 16.6, 25.3, 18.6), PEARL, 0.2, 1.25)
    # the wooden table: planks with dark seams
    table = Y > 19.5
    plank = np.floor((Y - 19.5) / 3.6).astype(int)
    c.paint(table, UMBER, np.clip(0.3 + 0.12 * (plank % 2) + 0.12 * np.sin(X * 0.7 + plank * 2.0 + np.sin(Y * 1.3)), 0, 1))
    c.paint(table & (((Y - 19.5) % 3.6) < 0.45), UMBER, 0.95, 1.1)
    # steam curling up from the mug
    for (sx, ph, top) in ((8.6, 0.0, 2.5), (12.6, 2.2, 1.5), (16.6, 4.0, 3.0)):
        pts = [(sx + 1.3 * math.sin(t * 0.8 + ph), 9.0 - t) for t in np.linspace(0, 9.0 - top, 24)]
        c.paint(c.line_mask(pts, 1.0), PEARL, 0.15, 1.3)
    # the mug: red cylinder, white band, handle on the left, dark cocoa and a heap of marshmallows
    cx, top, bot, rx = 12.6, 12.5, 31.5, 7.2
    body = rect(c, cx - rx, top, cx + rx, bot) | ellipse(c, cx, bot, rx, 1.8)
    handle = ellipse(c, cx - rx, 22.5, 3.8, 4.8) & ~ellipse(c, cx - rx, 22.5, 2.1, 3.1) & (X < cx - rx + 0.5)
    cyl = np.clip(0.3 + 0.55 * ((X - cx + 2.5) / rx) ** 2, 0, 1)
    c.paint(handle, EMBER, 0.7, 1.4)
    c.paint(body, EMBER, cyl, 1.4)
    c.paint(body & (Y > 21.5) & (Y < 24.5), PEARL, np.clip(cyl * 0.6, 0, 1), 1.45)
    c.paint(ellipse(c, cx, top, rx, 3.0), EMBER, 0.1, 1.5)
    c.paint(ellipse(c, cx, top + 0.2, rx - 1.0, 2.2), UMBER, 0.9, 1.55)
    for (mx, my) in ((10.4, 12.0), (12.9, 11.0), (15.2, 11.9), (11.8, 13.1), (14.2, 13.2), (12.8, 9.8)):
        c.paint(ellipse(c, mx, my, 1.4, 1.1), PEARL, np.clip(0.05 + 0.3 * (Y - my + 1) / 2.2, 0, 1), 1.6)
    # a pair of knitted mittens: blue, white zigzag band and dots, ribbed red cuffs, thumbs outward
    for (mx, my, ang, side) in ((29.4, 27.2, -0.12, -1), (39.3, 26.8, 0.12, 1)):
        ca, sa = math.cos(ang), math.sin(ang)
        u = (X - mx) * ca + (Y - my) * sa
        v = -(X - mx) * sa + (Y - my) * ca
        hand = ((np.abs(u) < 3.3) & (v > -3.4) & (v < 4.4)) | (((u / 3.3) ** 2 + ((v + 3.4) / 3.6) ** 2) <= 1)
        tu, tv = u - side * 3.3, v - 0.4
        thumb = ((tu * 0.9 - side * tv * 0.43) / 1.35) ** 2 + ((tv * 0.9 + side * tu * 0.43) / 2.8) ** 2 <= 1
        cuff = (np.abs(u) < 3.6) & (v >= 4.4) & (v < 8.4)
        mit = hand | thumb
        c.paint(mit, LAPIS, np.clip(0.42 + 0.12 * u / 3.3, 0, 1), 1.4)
        zig = hand & (np.abs(v - 1.0 - 1.0 * np.abs(((u + 10) % 2.6) - 1.3)) < 0.55)
        c.paint(zig, PEARL, 0.1, 1.5)
        dots = hand & (np.abs(v + 2.9) < 0.65) & ((np.floor((u + 10.5) / 1.3) % 2) == 0) & (np.abs(u) < 2.6)
        c.paint(dots, PEARL, 0.1, 1.5)
        c.paint(cuff, EMBER, np.where(((u + 10) % 1.3) < 0.65, 0.4, 0.7), 1.45)
        c.paint(cuff & (np.abs(v - 6.4) < 0.5), PEARL, 0.15, 1.5)
    frame(c)
    return encode(c.to_tiles())


# ---------------------------------------------------------------------------
# challenge
# ---------------------------------------------------------------------------

def hexagon(c, cx, cy, r, rot=0.0):
    """A regular hexagon of circumradius r with a corner pointing along angle rot."""
    m = np.ones_like(c.X, bool)
    for k in range(3):
        a = rot + math.pi / 6 + k * math.pi / 3
        m &= np.abs((c.X - cx) * math.cos(a) + (c.Y - cy) * math.sin(a)) <= r * math.cos(math.pi / 6)
    return m


def dendrite(c, cx, cy, R, w, rot=-math.pi / 2, spacing=3.2, start=5.0, w_branch=None):
    """A six-fold dendritic snow crystal of radius R: six main arms, each with fern-like side branches at 60
    degrees that are longest a third of the way out (they never cross the neighbouring arm's branches)."""
    m = np.zeros_like(c.X, bool)
    for k in range(6):
        a = rot + k * math.pi / 3
        ux, uy = math.cos(a), math.sin(a)
        m |= c.line_mask([(cx, cy), (cx + R * ux, cy + R * uy)], w)
        d = start
        while d < R - 1.0:
            L = min(0.75 * d, 0.58 * (R - d))
            bx, by = cx + d * ux, cy + d * uy
            for side in (-1, 1):
                b = a + side * math.pi / 3
                m |= c.line_mask([(bx, by), (bx + L * math.cos(b), by + L * math.sin(b))], w_branch or w * 0.72)
            d += spacing
    return m


# small crystals for the plate's lower row (x crystal, o blue core)
SMALL = [["x.x.x", ".xxx.", "xxoxx", ".xxx.", "x.x.x"],
         [".xxx.", "xx.xx", "x.o.x", "xx.xx", ".xxx."],
         ["..x..", "x.x.x", ".xox.", "x.x.x", "..x.."],
         ["x.x.x", ".x.x.", "xxoxx", ".x.x.", "x.x.x"],
         [".x.x.", "xxxxx", ".xox.", "xxxxx", ".x.x."],
         ["..x..", ".x.x.", "xxoxx", ".x.x.", "..x.."]]


def snowflake():
    """After Wilson Bentley's snow-crystal photographs (from 1885), set out like one of his plates: a great
    six-armed dendrite, white on a deep blue ground in a gilt mount, its arms reaching the corners of a
    gilt hexagon, and below it a row of six small crystals on black in coloured slide mounts."""
    c = Canvas(44, 44)
    X, Y = c.X, c.Y
    tx, ty = tiles(c)
    cx, cy = 22.0, 18.5
    r = np.hypot(X - cx, Y - cy)
    # the big slide: gilt mount, red velvet corners, the hexagon with a deep blue ground
    c.paint(ALL(c), SAFFRON, 0.4)
    c.paint(rect(c, 2, 2, 42, 35), EMBER, np.clip(0.8 + 0.15 * smooth_noise(c, 3, 0.6), 0, 1), 1.1)
    c.paint(hexagon(c, cx, cy, 17.6, -math.pi / 2), SAFFRON, 0.3, 1.2)
    c.paint(hexagon(c, cx, cy, 16.3, -math.pi / 2), LAPIS, 1.0, 1.3)
    # the great crystal: arms with side branches, a hexagonal centre plate with a ring
    crystal = dendrite(c, cx, cy, 16.6, 1.7, w_branch=1.15) | hexagon(c, cx, cy, 4.2, -math.pi / 2)
    c.paint(crystal & hexagon(c, cx, cy, 16.8, -math.pi / 2), PEARL, np.clip(0.0 + 0.2 * (r / 16) ** 2, 0, 1), 1.5)
    ring = hexagon(c, cx, cy, 3.1, -math.pi / 2) & ~hexagon(c, cx, cy, 1.9, -math.pi / 2)
    c.paint(ring, LAPIS, 0.35, 1.6)
    # the row of small slides: coloured mounts, black grounds, a different small crystal in each
    mounts = [EMBER, FERN, LAPIS, EMBER, FERN, LAPIS]
    for k in range(6):
        x0 = 1 + 7 * k
        c.paint(rect(c, x0, 36, x0 + 7, 43), mounts[k], 0.6, 1.3)
        c.paint(rect(c, x0 + 1, 37, x0 + 6, 42), UMBER, 1.0, 1.35)
        sprite(c, x0 + 1, 37, SMALL[k], {'x': (PEARL, 0.05), 'o': (LAPIS, 0.3)}, 1.6)
    frame(c)
    return encode(c.to_tiles())


# skaters and onlookers, tiny (h hat or bonnet, f face, c coat or jacket, s skirt)
FAR_GENT, FAR_LADY = [".h.", ".f.", "ccc", "c.c"], [".h.", ".f.", "ccc", "sss"]
MID_GENT = [".h.", ".f.", "ccc", "ccc", ".c.", "c.c"]
MID_LADY = [".h.", ".f.", "ccc", "sss", "sss", "sss"]
NEAR_GENT = [".hh.", ".hh.", ".ff.", "cccc", ".cc.", ".cc.", ".c.c"]
NEAR_LADY = [".hh.", ".ff.", "cccc", ".ss.", "ssss", "ssss", "ssss"]


def skating():
    """After Currier & Ives, "Central Park, Winter: The Skating Pond" (1862): crowds of small skaters on the
    frozen pond under a pale yellow winter sky, a stone bridge arching across the far end, the skating
    house with the red ball up on its flagpole, bare trees and onlookers on the snowy near bank."""
    c = Canvas(48, 36)
    X, Y = c.X, c.Y
    rng = random.Random(1862)
    # pale winter sky, yellow towards the horizon
    c.paint(ALL(c), LAPIS, np.where(Y < 2.5, 0.34, 0.0))
    c.paint(Y > 4.5, SAFFRON, np.where(Y < 7.0, 0.0, 0.34))
    # the far shore: bare woods, dark evergreens, the skating house with its flagpole and red ball
    c.paint(Y > 10.0 + 0.5 * np.sin(X * 0.7) + 0.5 * np.sin(X * 1.9), UMBER, 0.3)
    for (ex, top) in ((17.0, 6.5), (20.0, 7.5), (23.0, 6.0)):
        c.paint(c.poly_mask([(ex - 2.2, 13.0), (ex + 2.2, 13.0), (ex, top)]), FERN, 0.85, 1.1)
    c.paint(rect(c, 9.0, 8.6, 16.0, 12.8), PEARL, 0.3, 1.15)
    c.paint(c.poly_mask([(8.0, 8.8), (17.0, 8.8), (12.5, 5.6)]), EMBER, 0.65, 1.2)
    for wx in (10.5, 12.5, 14.5):
        c.paint(rect(c, wx - 0.5, 9.8, wx + 0.5, 11.4), UMBER, 0.85, 1.25)
    c.paint(c.line_mask([(12.5, 5.6), (12.5, 1.8)], 0.45), UMBER, 0.9, 1.3)
    c.paint(c.circle(12.5, 2.0, 1.0), EMBER, 0.55, 1.35)
    # the frozen pond
    ice = Y > 12.8
    c.paint(ice, LAPIS, np.where(Y < 21.0, 0.0, 0.34))
    # the humped stone bridge across the far end: dark railing, arch with its shadow and reflection
    bx = 36.0
    deck = 7.6 + 0.016 * (X - bx) ** 2
    span = (Y > deck) & (Y < 13.4) & (np.abs(X - bx) < 12.5)
    hole = ellipse(c, bx, 13.4, 6.4, 3.6) & (Y < 13.4)
    c.paint(span, PEARL, np.clip(0.1 + 0.2 * (Y - 8) / 6, 0, 1), 1.2)
    c.paint(span & ellipse(c, bx, 13.4, 7.6, 4.8) & (Y > deck + 1.4), PEARL, 0.7, 1.22)
    c.paint(hole, LAPIS, 0.67, 1.25)
    c.paint(ellipse(c, bx, 13.4, 6.4, 2.0) & (Y >= 13.4) & ice, LAPIS, 0.34, 1.15)
    c.paint((np.abs(Y - deck + 0.2) < 0.45) & (np.abs(X - bx) < 12.5), UMBER, 0.7, 1.3)
    # the snowy near bank
    bank = Y > 29.0 + 0.9 * np.sin(X * 0.25 + 0.6)
    c.paint(bank, PEARL, np.clip(0.05 + 0.03 * (Y - 29), 0, 0.4))
    # bare trees: a great one on the left, a smaller one on the right
    def branch(x, y, ang, length, w, depth):
        x1, y1 = x + math.cos(ang) * length, y + math.sin(ang) * length
        c.paint(tube(c, [(x, y), (x1, y1)], w, w * 0.75), UMBER, 0.8, 1.3)
        if depth > 0:
            for da in (-0.45, 0.4):
                branch(x1, y1, ang + da + rng.uniform(-0.1, 0.1), length * 0.62, max(0.8, w * 0.65), depth - 1)
    c.paint(tube(c, [(3.5, 36), (4.0, 24), (4.0, 15)], 3.0, 2.0), UMBER, 0.85, 1.3)
    for ang in (-1.75, -1.25, -0.6):
        branch(4.0, 15.5, ang, 6.5, 1.5, 1)
    c.paint(tube(c, [(45.0, 36), (45.2, 25)], 1.8, 1.2), UMBER, 0.85, 1.3)
    for ang in (-2.0, -1.2):
        branch(45.2, 25.5, ang, 4.5, 1.0, 0)
    # skaters: small far off, bigger nearer (gentlemen in dark or red coats, ladies in coloured skirts)
    skirts = [EMBER, FERN, LAPIS, EMBER, FERN, SAFFRON, EMBER, FERN]
    spots = [(15, 13, 0), (21, 14, 0), (28, 15, 0), (43, 15, 0),
             (8, 17, 1), (18, 18, 1), (37, 18, 1), (43, 21, 1),
             (12, 20, 2), (24, 21, 2), (31, 20, 2)]
    for i, (sx, sy, size) in enumerate(spots):
        lady = i % 2 == 1
        rows = [[FAR_GENT, FAR_LADY], [MID_GENT, MID_LADY], [NEAR_GENT, NEAR_LADY]][size][lady]
        coat = (EMBER, 0.95) if i % 4 == 2 else (UMBER, 0.95 if not lady else 0.7)
        pal = {'h': (UMBER, 0.95), 'f': (EMBER, 0.0), 'c': coat, 's': (skirts[i % len(skirts)], 0.6)}
        sprite(c, sx, sy, rows, pal, 1.6)
    # onlookers on the bank
    for i, ox in enumerate((10, 15, 21, 29, 35, 40)):
        lady = i % 2 == 0
        oy = int(round(27.6 + 0.9 * math.sin(ox * 0.25 + 0.6)))
        pal = {'h': (UMBER, 0.95), 'f': (EMBER, 0.0), 'c': (UMBER, 0.8), 's': ([EMBER, FERN, EMBER][i % 3], 0.6)}
        sprite(c, ox, oy, MID_LADY if lady else MID_GENT, pal, 1.6)
    frame(c)
    return encode(c.to_tiles())


# ---------------------------------------------------------------------------
# master
# ---------------------------------------------------------------------------

class Clip:
    """A view of a canvas whose paint() only reaches inside `mask` (for drawing inside the snow globe)."""

    def __init__(self, c, mask):
        self.c, self.mask = c, mask

    def paint(self, m, family, shade, prio=1.0):
        self.c.paint(m & self.mask, family, shade, prio)

    def __getattr__(self, name):
        return getattr(self.c, name)


def house(c, x0, x1, base, wall_h, roof_h, wall, roof, wins, prio=1.4):
    """A small snowy house: walls, a pitched roof with a cap of snow, a door and lit square windows."""
    X, Y = c.X, c.Y
    xm = (x0 + x1) / 2
    c.paint(rect(c, x0, base - wall_h, x1, base), wall[0], wall[1], prio)
    top = base - wall_h
    r = c.poly_mask([(x0 - 0.7, top + 0.2), (x1 + 0.7, top + 0.2), (xm, top - roof_h)])
    c.paint(r, roof[0], roof[1], prio + 0.05)
    c.paint(r & (Y < top - roof_h * 0.45), PEARL, 0.05, prio + 0.1)
    c.paint(rect(c, xm - 0.6, base - 2.0, xm + 0.6, base), UMBER, 0.9, prio + 0.15)
    for (wx, wy) in wins:
        c.paint(rect(c, wx, wy, wx + 1.0, wy + 1.0), SAFFRON, 0.05, prio + 0.2)


def snowglobe():
    """A glass snow globe on a turned wooden base, standing on a white mantel against red-and-gold
    wallpaper: inside, snow falls on a tiny village at night, houses with lit windows round a little square
    with a lit tree and two lamp posts, snowy hills and a crescent moon behind."""
    c = Canvas(40, 46)
    X, Y = c.X, c.Y
    rng = random.Random(7)
    # wallpaper: red diamonds in a gold lattice, white rosettes at the crossings, a dot in every diamond
    c.paint(ALL(c), EMBER, 0.8)
    lat = (((X + Y) % 8.0) < 1.3) | (((X - Y) % 8.0) < 1.3)
    c.paint(lat, SAFFRON, 0.45, 1.1)
    for i in range(-6, 12):
        for j in range(-6, 12):
            a, b = 0.65 + 8 * i, 0.65 + 8 * j
            px, py = (a + b) / 2, (a - b) / 2
            if -1 < px < 41 and -1 < py < 47:
                c.paint(c.circle(px, py, 1.05), PEARL, 0.15, 1.15)
            a, b = 4.65 + 8 * i, 4.65 + 8 * j
            px, py = (a + b) / 2, (a - b) / 2
            if -1 < px < 41 and -1 < py < 47:
                c.paint(c.circle(px, py, 1.3), FERN if (i + j) % 2 else LAPIS, 0.55, 1.15)
    # the white mantel shelf
    shelf = Y > 41.0
    c.paint(shelf, PEARL, np.clip(0.15 + 0.12 * (Y - 41), 0, 1), 1.2)
    c.paint(rect(c, 0, 42.6, 40, 43.4), PEARL, 0.9, 1.25)
    # the globe: glass rim, night sky inside
    gx, gy, R = 20.0, 18.5, 14.2
    glass = c.circle(gx, gy, R)
    inside = c.circle(gx, gy, R - 0.9)
    c.paint(c.circle(gx, gy, R + 0.8), UMBER, 0.85, 1.28)
    c.paint(glass, LAPIS, 0.2, 1.3)
    c.paint(inside, LAPIS, 1.0, 1.35)
    # a tiny village (everything clipped to the glass): moon, snowy hills with firs, houses round a square
    sub = Clip(c, inside)
    sub.paint(c.circle(27.0, 9.5, 2.5) & ~c.circle(28.5, 8.6, 2.0), PEARL, 0.1, 1.4)
    sub.paint(Y > 18.5 + 1.8 * np.sin(X * 0.45 + 1.0), PEARL, 0.45, 1.36)
    for (fx, fy) in ((8.5, 19.2), (11.0, 18.4), (30.5, 19.0), (33.0, 19.8)):
        sub.paint(c.poly_mask([(fx - 1.3, fy + 1.2), (fx + 1.3, fy + 1.2), (fx, fy - 2.6)]), FERN, 0.85, 1.38)
    sub.paint(Y > 24.0, PEARL, np.clip(0.02 + 0.04 * (Y - 24), 0, 0.4), 1.4)
    house(sub, 8.4, 13.6, 24.2, 4.4, 3.0, (EMBER, 0.55), (UMBER, 0.7), [(9.4, 21.0), (11.6, 21.0)])
    house(sub, 13.6, 17.0, 24.2, 6.4, 2.6, (PEARL, 0.75), (FERN, 0.75), [(14.8, 18.6)])
    house(sub, 23.0, 26.4, 24.2, 6.4, 2.6, (SAFFRON, 0.75), (EMBER, 0.75), [(24.2, 18.6)])
    house(sub, 26.4, 31.6, 24.2, 4.4, 3.0, (PEARL, 0.7), (LAPIS, 0.55), [(27.4, 21.0), (29.6, 21.0)])
    # the tree in the square, with coloured lights and a star; two lamp posts
    for k, (w, y1) in enumerate(((4.4, 29.6), (3.5, 26.0), (2.5, 22.6))):
        sub.paint(c.poly_mask([(gx - w, y1), (gx + w, y1), (gx, y1 - 4.8)]), FERN, 0.55 + 0.1 * k, 1.5)
    sub.paint(rect(c, gx - 0.6, 29.4, gx + 0.6, 31.0), UMBER, 0.85, 1.5)
    lights = [(18.2, 28.2, EMBER), (21.8, 28.4, SAFFRON), (20.0, 26.6, LAPIS), (16.9, 29.0, SAFFRON), (23.1, 29.0, EMBER),
              (18.8, 24.6, SAFFRON), (21.4, 23.8, EMBER), (19.8, 21.2, LAPIS), (17.6, 25.4, PEARL), (22.4, 25.4, PEARL)]
    for (lx, ly, fam) in lights:
        sub.paint(c.circle(lx, ly, 0.6), fam, 0.15 if fam == LAPIS else 0.1, 1.6)
    star = c.poly_mask([(gx - 1.3, 17.6), (gx + 1.3, 17.6), (gx, 15.4)]) \
        | c.poly_mask([(gx - 1.3, 16.2), (gx + 1.3, 16.2), (gx, 18.4)])
    sub.paint(star, SAFFRON, 0.1, 1.65)
    for lx in (11.0, 29.0):
        sub.paint(rect(c, lx - 0.35, 24.5, lx + 0.35, 30.0), UMBER, 0.9, 1.5)
        sub.paint(c.circle(lx, 24.2, 0.85), SAFFRON, 0.05, 1.55)
    # falling snow inside the glass, and a white highlight on the glass
    snowfall(c, rng, 30, lambda x, y: math.hypot(x - gx, y - gy) < R - 1.6 and y < 17
             and math.hypot(x - 27.0, y - 9.5) > 2.6, prio=1.62)
    ang = np.arctan2(Y - gy, X - gx)
    hl = c.circle(gx, gy, R - 0.9) & ~c.circle(gx, gy, R - 1.9) & (ang > -2.6) & (ang < -2.0)
    c.paint(hl, PEARL, 0.0, 1.66)
    # the turned wooden base with a gold band and a sprig of holly
    base = c.poly_mask([(11.5, 30.6), (28.5, 30.6), (31.0, 41.0), (9.0, 41.0)]) | ellipse(c, gx, 30.6, 8.5, 1.2)
    c.paint(base, UMBER, np.clip(0.35 + 0.4 * np.abs(X - gx) / 11 + 0.1 * np.sin(X * 2.2), 0, 1), 1.7)
    c.paint(base & (Y > 32.6) & (Y < 34.0), SAFFRON, np.clip(0.2 + 0.4 * np.abs(X - gx) / 11, 0, 1), 1.75)
    c.paint(base & (Y > 39.4), UMBER, 0.95, 1.75)
    for (lx, ly, ang) in ((17.6, 36.6, 0.35), (22.4, 36.6, -0.35)):
        c.paint(ellipse(c, lx, ly, 2.2, 1.0, ang), FERN, 0.45, 1.8)
    for (bx, by) in ((19.3, 36.1), (20.7, 36.1), (20.0, 37.2)):
        c.paint(c.circle(bx, by, 0.6), EMBER, 0.45, 1.85)
    frame(c)
    return encode(c.to_tiles())


def frost_fern(c, x, y, ang, length, barb=2.2, bend=0.25, depth=1):
    """A feathery frost fern growing from (x, y) along ang: a curving stem with barbs on both sides every
    2.5 tiles, shortening towards the tip, and (depth > 0) two side ferns; returns its mask."""
    n = max(3, int(length / 0.6))
    pts = [(x, y)]
    for i in range(1, n + 1):
        a = ang + bend * i / n
        pts.append((pts[-1][0] + math.cos(a) * length / n, pts[-1][1] + math.sin(a) * length / n))
    m = c.line_mask(pts, 0.7)
    step = max(1, int(round(2.5 / (length / n))))
    for i in range(step, n, step):
        t = i / n
        a = ang + bend * t
        bl = barb * (1 - t) + 0.6
        px, py = pts[i]
        for side in (-1, 1):
            b = a + side * 0.75
            m |= c.line_mask([(px, py), (px + bl * math.cos(b), py + bl * math.sin(b))], 0.6)
    if depth > 0:
        for (t, side) in ((0.3, 1), (0.55, -1)):
            px, py = pts[int(t * n)]
            m |= frost_fern(c, px, py, ang + bend * t + side * 0.8, length * 0.45, barb * 0.6, -side * 0.2, depth - 1)
    return m


def frostwindow():
    """A window on a winter night seen from outside: four panes grown over with feathery frost ferns,
    through them the warm glow of a candle on the inner sill, a cat curled beside it and green curtains;
    a brick wall, icicles under the stone lintel, snow on the sill and a window box of evergreens."""
    c = Canvas(40, 46)
    X, Y = c.X, c.Y
    tx, ty = tiles(c)
    # brick wall: courses of two-row bricks between grey mortar rows, dark staggered joints
    course = ty // 3
    joint = ((tx + (course % 2) * 2) % 5) == 0
    c.paint(ALL(c), EMBER, np.clip(0.6 + 0.3 * (((tx + (course % 2) * 2) // 5 * 7 + course * 3) % 4) / 3, 0, 1))
    c.paint(ty % 3 == 2, PEARL, 0.7, 1.05)
    c.paint(joint & (ty % 3 != 2), UMBER, 0.85, 1.05)
    # behind the glass: the warm glow of the room, green curtains drawn to the sides
    gx0, gy0, gx1, gy1 = 7.2, 8.8, 32.8, 37.0
    gl = rect(c, gx0, gy0, gx1, gy1)
    d = np.hypot(X - 13.5, (Y - 31.0) * 1.2)
    c.paint(gl, SAFFRON, np.clip(d / 22.0, 0, 1), 1.1)
    c.paint(gl & (d > 23.0), EMBER, 0.55, 1.12)
    for xe in (gx0, gx1):
        half = np.interp(Y, [gy0, 27, 30, gy1], [5.6, 2.8, 2.8, 4.0])
        drape = gl & (np.abs(X - xe) < half)
        c.paint(drape, FERN, np.clip(0.55 + 0.3 * np.sin(X * 2.4), 0, 1), 1.15)
        c.paint(drape & (np.abs(Y - 28.5) < 0.7), SAFFRON, 0.7, 1.2)
    # the candle in its brass holder, its flame; a cat curled on the inner sill
    c.paint(rect(c, 12.6, 29.0, 14.4, 35.4), EMBER, 0.35, 1.5)
    c.paint(ellipse(c, 13.5, 35.8, 2.6, 0.9) | rect(c, 12.4, 35.0, 14.6, 36.4), UMBER, 0.6, 1.55)
    c.paint(ellipse(c, 13.5, 27.0, 1.0, 1.9), SAFFRON, 0.0, 1.55)
    c.paint(c.circle(13.5, 27.6, 0.55), PEARL, 0.0, 1.6)
    ears = c.poly_mask([(23.0, 31.6), (23.2, 29.4), (24.6, 30.8)]) | c.poly_mask([(24.8, 30.7), (26.0, 29.4), (26.2, 31.6)])
    cat = ellipse(c, 27.0, 34.8, 3.4, 2.1) | c.circle(24.6, 32.4, 1.8) | ears \
        | tube(c, [(30.2, 35.6), (31.4, 33.8), (30.8, 32.2)], 1.0, 0.8)
    c.paint(cat, UMBER, 0.95, 1.5)
    # frost on every pane: a pale blue icy haze round the edges and white feathery fronds
    mx, my = 20.0, 22.9
    panes = [(gx0, gy0, mx, my), (mx, gy0, gx1, my), (gx0, my, mx, gy1), (mx, my, gx1, gy1)]
    rng = random.Random(14)
    clear = c.circle(13.5, 31.0, 5.0) | (cat & (Y > 30.5))
    for k, (x0, y0, x1, y1) in enumerate(panes):
        pane = rect(c, x0, y0, x1, y1)
        # a pale blue icy haze round the pane's edges, the glow showing through in the middle
        u, v = (X - (x0 + x1) / 2) / ((x1 - x0) / 2), (Y - (y0 + y1) / 2) / ((y1 - y0) / 2)
        haze = pane & (np.maximum(np.abs(u), np.abs(v)) + 0.1 * np.sin(X * 1.7 + Y * 2.3) > 0.78) & ~clear
        c.paint(haze, LAPIS, 0.05, 1.6)
        ferns = np.zeros_like(X, bool)
        # tall fronds growing up from the bottom edge, smaller ones down from the top corners
        for (fx, ln) in ((x0 + 2.6, rng.uniform(8.5, 10.5)), (x1 - 2.6, rng.uniform(8.5, 10.5)), ((x0 + x1) / 2, 5.0)):
            ferns |= frost_fern(c, fx, y1, -math.pi / 2 + rng.uniform(-0.25, 0.25), ln, 2.2, rng.choice((-0.25, 0.25)), 0)
        for (qx, sgn) in ((x0, 1), (x1, -1)):
            ferns |= frost_fern(c, qx, y0, math.pi / 2 - sgn * 0.75, 5.5, 1.8, sgn * 0.3, 0)
        c.paint(ferns & pane & ~clear, PEARL, 0.0, 1.65)
    # the window frame with its cross of mullions
    wood = (rect(c, 6.0, 7.6, 34.0, 38.2) & ~gl) | rect(c, 19.4, gy0, 20.6, gy1) | rect(c, gx0, 22.3, gx1, 23.5)
    c.paint(wood, UMBER, 0.55, 1.75)
    # stone lintel with icicles, stone sill heaped with snow
    c.paint(rect(c, 4.5, 5.0, 35.5, 7.6), PEARL, 0.45, 1.8)
    for k, ix in enumerate(np.arange(6.5, 34.0, 2.6)):
        ln = 1.8 + 1.4 * ((k * 5) % 3)
        c.paint(c.poly_mask([(ix - 0.7, 7.4), (ix + 0.7, 7.4), (ix, 7.4 + ln)]), LAPIS, 0.15, 1.85)
    c.paint(rect(c, 4.5, 38.2, 35.5, 40.8), PEARL, 0.5, 1.8)
    heap = ellipse(c, 20.0, 38.4, 16.0, 1.3) | ellipse(c, 10.0, 37.9, 5.0, 1.0) | ellipse(c, 30.0, 38.0, 5.0, 0.9)
    c.paint(heap, PEARL, 0.0, 1.85)
    # a window box of snowy evergreen sprigs and red berries under the sill
    for k, sx in enumerate(np.arange(9.0, 32.0, 2.9)):
        sprig = c.poly_mask([(sx - 1.7, 42.0), (sx + 1.7, 42.0), (sx + 0.2 * (k % 2), 38.6 + 0.5 * (k % 3))])
        c.paint(sprig, FERN, 0.6 + 0.2 * (k % 2), 1.9)
    for (bx, by) in ((12.0, 41.0), (20.6, 40.8), (26.2, 41.1)):
        c.paint(c.circle(bx, by, 0.65), EMBER, 0.35, 1.95)
    c.paint(rect(c, 7.0, 41.6, 33.0, 44.8), UMBER, 0.45, 1.95)
    c.paint(rect(c, 7.0, 41.6, 33.0, 42.4), UMBER, 0.75, 1.96)
    frame(c)
    return encode(c.to_tiles())


SCENES = {
    "snowman": snowman, "cardinal": cardinal, "sledding": sledding, "cocoa": cocoa,
    "snowflake": snowflake, "skating": skating, "snowglobe": snowglobe, "frostwindow": frostwindow,
}
