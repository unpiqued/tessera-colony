"""Inventions & Firsts: eight original tile pictures of famous machines and first moments of
invention, each drawn as the object itself (no people, no likenesses, no makers' marks, no lettering),
with the supersampled Canvas of art.py (a tile's colour family comes from the dominant object under
it, its tone from the shading).

Gentle: penny-farthing, light bulb, candlestick telephone, Leonardo's flying machine.
Challenge: Stephenson's Rocket, the first photograph.  Master: Jacquard loom, Difference Engine.
"""
import math
import random

import numpy as np
from scipy import ndimage

from art import Canvas, LAPIS, SAFFRON, FERN, EMBER, UMBER, PEARL, encode, SS
from art_scenes import ALL, ellipse, rect, tube, frame, sky, cloud, smooth_noise


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def spoked_wheel(c, cx, cy, r, n, tyre_w=1.0, spoke_w=0.6, tyre=(UMBER, 0.9), spoke=(PEARL, 0.35),
                 hub=(PEARL, 0.15), hub_r=1.0, rot=0.0, prio=1.6, fill=None):
    """A wheel seen side-on: n straight spokes, a dark tyre ring and a hub; the background shows
    between the spokes unless the wheel has a `fill` (family, shade) of its own."""
    d = np.hypot(c.X - cx, c.Y - cy)
    if fill:
        c.paint(d <= r, fill[0], fill[1], prio)
    for k in range(n):
        a = rot + 2 * math.pi * k / n
        end = (cx + math.cos(a) * (r - tyre_w * 0.5), cy + math.sin(a) * (r - tyre_w * 0.5))
        c.paint(c.line_mask([(cx, cy), end], spoke_w), spoke[0], spoke[1], prio)
    c.paint((d <= r) & (d >= r - tyre_w), tyre[0], tyre[1], prio + 0.1)
    c.paint(d <= hub_r, hub[0], hub[1], prio + 0.2)


def gear(c, cx, cy, r, teeth, depth=0.8, rot=0.0):
    """Mask of a toothed wheel seen face-on."""
    a = np.arctan2(c.Y - cy, c.X - cx)
    d = np.hypot(c.X - cx, c.Y - cy)
    return d <= np.where(np.cos(teeth * (a - rot)) > 0, r, r - depth)


def tiles(c):
    return np.floor(c.X).astype(int), np.floor(c.Y).astype(int)


# ---------------------------------------------------------------------------
# Gentle
# ---------------------------------------------------------------------------

def pennyfarthing():
    """Penny-farthing (1870s): the high-wheeler side-on on a park path: the huge spoked front wheel,
    the tiny trailing wheel, the red backbone hugging the big wheel up to the saddle and handlebar."""
    c = Canvas(46, 38)
    X, Y = c.X, c.Y
    ground = 32.8
    # summer sky with two clouds, a low line of round park trees, the lawn and a sandy path
    sky(c, 0.45, 0.0, horizon=27)
    cloud(c, [(5, 8, 1.8), (7.8, 7.0, 2.4), (10.6, 8.2, 1.7)])
    cloud(c, [(38.5, 5.0, 1.5), (41, 4.1, 2.0), (43.5, 5.2, 1.4)])
    trees = Y > 27.0
    for (tx, ty, tr) in ((1.5, 24.5, 3.0), (5.5, 23.0, 3.8), (10.5, 24.4, 3.2), (14.2, 25.6, 2.2)):
        trees |= c.circle(tx, ty, tr)
    c.paint(trees, FERN, np.clip(0.8 + 0.1 * smooth_noise(c, 2, 0.9), 0, 1))
    lawn = Y > 28.2 + 0.3 * np.sin(X * 0.35)
    c.paint(lawn, FERN, np.clip(0.32 + 0.1 * np.sin(X * 0.8), 0, 1))
    path = Y > 31.0 + 0.3 * np.sin(X * 0.25 + 1)
    c.paint(path, SAFFRON, np.clip(0.12 + 0.3 * (Y - 31.0) / 7, 0, 1))
    c.paint(ellipse(c, 21, ground + 0.8, 15, 0.9), SAFFRON, 0.85, 1.1)
    # the little trailing wheel and the great front wheel
    fx, fy, R = 30.0, ground - 13.4, 13.4
    rx, ry, r = 10.0, ground - 3.3, 3.3
    spoked_wheel(c, rx, ry, r, 6, tyre_w=0.9, spoke_w=0.5, hub_r=0.6, rot=0.3)
    # (the big wheel's wire spokes are drawn as a dark tone of whatever shows through them)
    spokes = np.zeros_like(X, bool)
    for k in range(16):
        a = 0.2 + 2 * math.pi * k / 16
        spokes |= c.line_mask([(fx + math.cos(a) * 1.5, fy + math.sin(a) * 1.5),
                               (fx + math.cos(a) * (R - 0.6), fy + math.sin(a) * (R - 0.6))], 0.75)
    for fam in (LAPIS, FERN, SAFFRON, PEARL):
        c.paint(spokes & (c.fam == fam), fam, 1.0, 1.8)
    spoked_wheel(c, fx, fy, R, 0, tyre_w=1.15, hub_r=1.2)
    # backbone: from the head over the top of the big wheel, hugging its back, down to the little hub
    head = (29.4, 4.4)
    pts = [head] + [(fx + 14.9 * math.cos(a), fy + 14.9 * math.sin(a)) for a in np.linspace(-1.8, -3.1, 7)]
    pts += [(13.4, 23.8), (rx, ry)]
    c.paint(tube(c, pts, 1.4, 1.0), EMBER, 0.8, 1.8)
    # fork down to the front hub, crank and pedal
    c.paint(tube(c, [head, (fx, fy)], 1.3, 1.0), EMBER, 0.8, 1.8)
    c.paint(c.circle(fx, fy, 1.1), PEARL, 0.3, 2.0)
    c.paint(c.line_mask([(fx, fy), (32.4, 22.0)], 0.7), UMBER, 0.85, 2.0)
    c.paint(rect(c, 31.6, 21.6, 34.0, 22.6), UMBER, 0.95, 2.0)
    # leather saddle on its spring, and the moustache handlebar with grips
    c.paint(ellipse(c, 25.0, 3.5, 2.7, 1.1, -0.1), UMBER, 0.5, 2.1)
    c.paint(rect(c, 24.6, 4.0, 25.6, 5.2), UMBER, 0.9, 2.0)
    c.paint(c.line_mask([(26.9, 3.0), (29.4, 2.3), (32.0, 3.0)], 0.65), UMBER, 0.95, 2.0)
    for gx in (26.6, 32.3):
        c.paint(ellipse(c, gx, 3.4, 0.8, 0.6), UMBER, 0.6, 2.1)
    frame(c)
    return encode(c.to_tiles())


def lightbulb():
    """The incandescent lamp (1879): a big pear-shaped glass globe glowing gold around its looped
    carbon filament, on a screw base in a brass socket, in a dark room lit only by its warm halo."""
    c = Canvas(36, 46)
    X, Y = c.X, c.Y
    cx, gy, R, neck_y, base_y = 18.0, 16.0, 10.2, 29.5, 36.0
    # the glass: a sphere tapering smoothly into the neck
    t = np.clip((Y - (gy + 2.0)) / (neck_y - gy - 2.0), 0, 1)
    hw0 = math.sqrt(R * R - 4.0)
    hw = np.where(Y < gy + 2.0, np.sqrt(np.clip(R * R - (Y - gy) ** 2, 0, None)),
                  4.0 + (hw0 - 4.0) * (np.cos(math.pi * t) + 1) / 2)
    glass = (np.abs(X - cx) <= hw) & (Y >= gy - R) & (Y <= neck_y)
    # warm halo rings following the glass outline, fading into the dark room, crossed by light rays
    dist = ndimage.distance_transform_edt(~glass) / SS
    c.paint(ALL(c), UMBER, np.clip(0.6 + 0.03 * dist, 0, 1))
    c.paint(dist < 6.0, EMBER, np.clip(0.35 + 0.1 * dist, 0, 1))
    for a in (-90, -58, -122, -26, -154, 8, 172):
        ar = math.radians(a)
        p0 = (cx + math.cos(ar) * (R - 1), gy + math.sin(ar) * (R - 1))
        p1 = (cx + math.cos(ar) * (R + 9), gy + math.sin(ar) * (R + 9))
        c.paint(tube(c, [p0, p1], 2.2, 0.7), SAFFRON, 0.45, 1.2)
    c.paint(dist < 2.6, SAFFRON, np.clip(0.55 + 0.15 * dist, 0, 1))
    # the glowing glass, its pale rim and a highlight
    c.paint(glass, SAFFRON, np.clip(0.02 + 0.035 * np.hypot(X - cx, Y - 14), 0, 1))
    inner = ndimage.distance_transform_edt(glass) / SS
    c.paint(glass & (inner < 0.95), PEARL, 0.45, 1.3)
    hl = [(cx + (R - 2.4) * math.cos(a), gy + (R - 2.4) * math.sin(a)) for a in np.linspace(3.5, 4.3, 6)]
    c.paint(c.line_mask(hl, 1.2), PEARL, 0.0, 1.5)
    # the glass stem, lead-in wires and the horseshoe filament
    c.paint(c.poly_mask([(cx - 1.4, neck_y), (cx + 1.4, neck_y), (cx + 0.8, 24.5), (cx - 0.8, 24.5)]), PEARL, 0.2, 1.3)
    for s in (-1, 1):
        c.paint(c.line_mask([(cx + s * 0.6, 24.8), (cx + s * 3.6, 19.5)], 0.5), SAFFRON, 0.95, 1.5)
    fil = [(cx + 3.6 * math.cos(a), 15.0 - 5.6 * math.sin(a)) for a in np.linspace(0, math.pi, 16)]
    fil = [(cx + 3.6, 19.5)] + fil + [(cx - 3.6, 19.5)]
    c.paint(c.line_mask(fil, 1.2), EMBER, 0.38, 2.0)
    # screw base (threads as alternating bands), brass socket on a turned wooden stand
    shell = rect(c, cx - 4.1, neck_y - 0.3, cx + 4.1, base_y)
    ridge = ((Y - neck_y - 0.18 * (X - cx)) % 1.6) < 0.8
    c.paint(shell, PEARL, np.where(ridge, 0.1, 0.75), 1.4)
    c.paint(rect(c, cx - 4.6, base_y, cx + 4.6, base_y + 3.2), SAFFRON, np.clip(0.3 + 0.08 * np.abs(X - cx), 0, 1), 1.4)
    c.paint(rect(c, cx - 4.6, base_y + 1.3, cx + 4.6, base_y + 1.9), SAFFRON, 0.95, 1.5)
    stand = c.poly_mask([(cx - 3.0, base_y + 3.2), (cx + 3.0, base_y + 3.2), (cx + 4.0, 42.5), (cx + 8.5, 43.5),
                         (cx + 8.5, 45.0), (cx - 8.5, 45.0), (cx - 8.5, 43.5), (cx - 4.0, 42.5)])
    c.paint(stand, UMBER, np.clip(0.05 + 0.04 * np.abs(X - cx), 0, 1), 1.3)
    frame(c)
    return encode(c.to_tiles())


def telephone():
    """The candlestick telephone, big and central: the round brass foot, the tall thin black stem, the
    trumpet mouthpiece at the top turned towards us, and the earpiece hanging on its hook at the side
    with a curly red cord, on a green leather desk against a calm blue wall."""
    c = Canvas(38, 46)
    X, Y = c.X, c.Y
    sx = 19.5
    # calm wall, the desk's wooden rim, green leather top and drawer front with brass knobs
    c.paint(ALL(c), LAPIS, 0.33)
    c.paint(Y >= 33.0, UMBER, 0.35)
    c.paint(rect(c, 2, 34.0, 36, 40.0), FERN, np.clip(0.5 + 0.1 * smooth_noise(c, 5, 0.5), 0, 1), 1.1)
    c.paint(Y >= 41.0, UMBER, 0.75)
    for hx in (9.5, 28.5):
        c.paint(rect(c, hx - 1.0, 42.4, hx + 1.0, 43.6), SAFFRON, 0.4, 1.4)
    # a notepad on the desk
    c.paint(c.poly_mask([(28.0, 35.0), (35.0, 34.6), (35.4, 39.2), (28.4, 39.6)]), PEARL, 0.1, 1.3)
    # the round brass foot: a dome on a wide rim
    foot = ellipse(c, sx, 37.4, 7.6, 1.9) | c.poly_mask([(sx - 7.2, 37.4), (sx - 4.0, 33.2), (sx + 4.0, 33.2), (sx + 7.2, 37.4)])
    c.paint(foot, SAFFRON, np.clip(0.15 + 0.08 * np.abs(X - sx) + 0.05 * (Y - 33), 0, 1), 1.5)
    c.paint(foot & (Y > 37.6), SAFFRON, 0.9, 1.55)
    # the tall thin stem with brass collars
    c.paint(rect(c, sx - 1.2, 9.5, sx + 1.2, 33.5), UMBER, np.where(X < sx - 0.2, 0.65, 0.95), 1.6)
    for cy in (10.0, 32.0):
        c.paint(rect(c, sx - 1.8, cy, sx + 1.8, cy + 1.2), SAFFRON, 0.35, 1.7)
    # the transmitter and its trumpet mouthpiece, opening towards us and to the right
    c.paint(c.circle(sx, 7.0, 3.0), UMBER, 0.9, 1.7)
    c.paint(c.poly_mask([(sx + 1.5, 5.4), (sx + 1.5, 8.6), (sx + 7.4, 11.8), (sx + 7.4, 2.2)]), UMBER, 0.75, 1.7)
    c.paint(ellipse(c, sx + 7.6, 7.0, 2.1, 4.9), SAFFRON, 0.3, 1.8)
    c.paint(ellipse(c, sx + 7.8, 7.0, 1.2, 3.6), UMBER, 1.0, 1.9)
    # the brass hook on the left of the stem, and the earpiece hanging in it
    c.paint(c.line_mask([(sx - 1.2, 14.6), (15.2, 14.6), (14.8, 12.8)], 0.9), SAFFRON, 0.4, 1.8)
    ex = 11.6
    cup = ellipse(c, ex, 12.6, 3.6, 1.7) | c.poly_mask([(ex - 3.4, 12.8), (ex + 3.4, 12.8), (ex + 1.4, 16.4), (ex - 1.4, 16.4)])
    body = rect(c, ex - 1.3, 16.0, ex + 1.3, 27.5) | ellipse(c, ex, 27.6, 1.8, 1.1)
    c.paint(cup | body, UMBER, np.where(X < ex - 0.2, 0.65, 0.95), 1.7)
    c.paint(rect(c, ex - 1.7, 16.2, ex + 1.7, 17.3), SAFFRON, 0.35, 1.8)
    # the curly cord: a coil looping down from the earpiece and across to the foot
    path = [(ex, 28.6), (8.8, 31.8), (7.4, 35.4), (9.2, 38.4), (12.6, 38.2)]
    pts = []
    for (ax, ay), (bx, by) in zip(path[:-1], path[1:]):
        L = math.hypot(bx - ax, by - ay)
        nx, ny = -(by - ay) / L, (bx - ax) / L
        for t in np.linspace(0, 1, int(L * 6), endpoint=False):
            ph = (len(pts) / 6.0) * 2 * math.pi / 1.4
            pts.append((ax + (bx - ax) * t + nx * 0.95 * math.sin(ph), ay + (by - ay) * t + ny * 0.95 * math.sin(ph)))
    c.paint(c.line_mask(pts, 0.7), EMBER, 0.5, 1.8)
    frame(c)
    return encode(c.to_tiles())


def flyingmachine():
    """Leonardo's ornithopter (c. 1488) as a notebook study: brown ink on aged paper, the bat-like
    ribbed wings washed in red chalk, the long wooden chassis hung from a shoulder axle with pulleys,
    stirrups below, red-chalk bird studies and lines of abstract ink marks (no real writing)."""
    c = Canvas(48, 36)
    X, Y = c.X, c.Y
    cx = 24.0
    n = smooth_noise(c, 17, 0.6)
    # aged paper, darkening to a tea-coloured band at the edges
    c.paint(ALL(c), PEARL, np.clip(0.3 + 0.2 * n, 0, 1))
    edge = np.minimum.reduce([X, 48 - X, Y, 36 - Y]) + 0.7 * n
    c.paint(edge < 3.0, SAFFRON, np.clip(0.95 - 0.25 * edge, 0, 1))
    # two bat wings: arm spar to the wrist hinge, finger ribs fanning out, scalloped membrane between
    for s in (-1, 1):
        S, Wr = (cx + s * 3.0, 12.0), (cx + s * 11.0, 6.0)
        tips = [(cx + s * 21.5, 4.0), (cx + s * 21.0, 11.5), (cx + s * 17.5, 17.2), (cx + s * 11.5, 20.5),
                (cx + s * 5.0, 19.5)]
        outline = [S, Wr]
        for (ax, ay), (bx, by) in zip(tips[:-1], tips[1:]):
            mx, my = (ax + bx) / 2, (ay + by) / 2
            outline += [(ax, ay), (mx + (Wr[0] - mx) * 0.22, my + (Wr[1] - my) * 0.22)]
        outline += [tips[-1]]
        c.paint(c.poly_mask(outline), EMBER, np.clip(0.05 + 0.12 * n, 0, 1), 1.1)
        c.paint(tube(c, [S, Wr], 1.2, 0.9), UMBER, 0.75, 1.6)
        for tp in tips[:4]:
            c.paint(c.line_mask([Wr, tp], 0.65), UMBER, 0.7, 1.6)
        c.paint(c.line_mask([S, tips[4]], 0.65), UMBER, 0.7, 1.6)
        c.paint(c.circle(Wr[0], Wr[1], 1.0), UMBER, 0.9, 1.7)
    # the chassis: a long open wooden frame with one cross-bar, hung from the shoulder axle; pulleys at
    # the axle ends; a foot bar with two stirrups below
    c.paint(rect(c, cx - 2.3, 11.5, cx + 2.3, 27.0) & ~rect(c, cx - 1.1, 12.7, cx + 1.1, 25.8), UMBER, 0.75, 1.6)
    c.paint(rect(c, cx - 2.3, 18.8, cx + 2.3, 19.8), UMBER, 0.75, 1.6)
    c.paint(c.line_mask([(cx - 4.0, 12.0), (cx + 4.0, 12.0)], 1.0), UMBER, 0.85, 1.6)
    for s in (-1, 1):
        c.paint(c.circle(cx + s * 4.0, 12.0, 1.9) & ~c.circle(cx + s * 4.0, 12.0, 0.9), UMBER, 0.85, 1.7)
        c.paint(c.line_mask([(cx + s * 2.6, 27.0), (cx + s * 2.6, 29.4), (cx + s * 4.4, 29.4), (cx + s * 4.4, 27.0)], 0.6),
                UMBER, 0.75, 1.6)
    c.paint(c.line_mask([(cx - 5.0, 27.0), (cx + 5.0, 27.0)], 0.8), UMBER, 0.8, 1.6)
    # red-chalk bird studies and lines of abstract ink marks
    for (bx, by, bs) in ((8.0, 27.5, 2.8), (13.5, 23.5, 1.8)):
        c.paint(c.line_mask([(bx - 2 * bs, by - 0.4 * bs), (bx - bs, by - 0.9 * bs), (bx, by),
                             (bx + bs, by - 0.9 * bs), (bx + 2 * bs, by - 0.4 * bs)], 0.8), EMBER, 0.8, 1.6)
    for k, ly in enumerate((24.5, 27.5, 30.5)):
        for (a, b) in ((32.5 + k, 37.5), (38.6, 43.5 - k))[:2 - k // 2]:
            pts = [(x, ly + 0.25 * math.sin(x * 2.3)) for x in np.arange(a, b, 0.4)]
            c.paint(c.line_mask(pts, 0.6), UMBER, 0.75, 1.6)
    frame(c)
    return encode(c.to_tiles())


# ---------------------------------------------------------------------------
# Challenge
# ---------------------------------------------------------------------------

def rocket():
    """Stephenson's Rocket (1829), side-on and large: the yellow boiler barrel, the tall white chimney
    at the front, the big spoked driving wheel and the small trailing wheel, the steeply inclined
    cylinder and its rods, the copper firebox, and the little barrel tender, on rails under a plume,
    with the striped spectators' tents of the 1829 trials on the hills."""
    c = Canvas(48, 36)
    X, Y = c.X, c.Y
    tx, ty = tiles(c)
    rail = 32.0
    # sky darkening upwards (so the white chimney and steam stand out), distant hills, a pale meadow
    sky(c, 0.85, 0.15, horizon=14)
    c.paint(Y > 13.8 + 1.0 * np.sin(X * 0.2 + 0.5), FERN, 0.8)
    c.paint(Y > 17.0 + 0.4 * np.sin(X * 0.3), FERN, np.clip(0.12 + 0.1 * smooth_noise(c, 6, 0.8), 0, 1))
    # striped spectators' tents of the Rainhill trials on the hills, each with a pennant
    for (px, w) in ((4.2, 3.0), (41.0, 3.4)):
        tent = c.poly_mask([(px - w, 15.0), (px - w, 12.6), (px, 10.2), (px + w, 12.6), (px + w, 15.0)])
        c.paint(tent, EMBER, 0.35, 1.2)
        c.paint(tent & (((np.floor(X).astype(int) - int(px) + 1) // 2) % 2 == 0), PEARL, 0.1, 1.25)
        c.paint(c.line_mask([(px, 10.2), (px, 8.2)], 0.4), UMBER, 0.9, 1.3)
        c.paint(c.poly_mask([(px, 8.0), (px + 2.0, 8.7), (px, 9.4)]), SAFFRON, 0.2, 1.3)
    # the line: rail on gravel and sleepers
    c.paint(Y > rail, SAFFRON, np.clip(0.55 + 0.2 * smooth_noise(c, 8, 1.3), 0, 1))
    c.paint((ty == 33) & (tx % 3 == 1), UMBER, 0.75, 1.2)
    c.paint(ty == 32, PEARL, 0.55, 1.3)
    # a plume of steam trailing back from the chimney
    for (px, py, pr) in ((13.8, 2.6, 1.6), (17.0, 2.2, 2.2), (21.5, 2.8, 2.6), (26.5, 2.4, 2.7), (32.0, 3.0, 2.5),
                         (37.5, 2.6, 2.2), (42.0, 3.0, 1.7)):
        c.paint(c.circle(px, py, pr), PEARL, np.clip(0.02 + 0.03 * (px - 13), 0, 0.6), 1.2)
    # the little tender: a yellow wagon carrying a hooped water barrel
    c.paint(rect(c, 36.5, 24.2, 46.6, 25.8), SAFFRON, 0.5, 1.4)
    barrel = ellipse(c, 41.6, 20.6, 5.0, 3.8) & (np.abs(X - 41.6) < 4.5)
    c.paint(barrel, UMBER, np.clip(0.1 + 0.1 * np.abs(Y - 19.6), 0, 1), 1.4)
    c.paint(barrel & ((np.abs(X - 39.0) < 0.5) | (np.abs(X - 41.6) < 0.5) | (np.abs(X - 44.2) < 0.5)), UMBER, 0.95, 1.5)
    c.paint(rect(c, 34.0, 23.6, 36.6, 24.4), UMBER, 0.9, 1.5)
    # copper firebox at the back, frame, red buffer beam at the front
    c.paint(rect(c, 29.5, 11.5, 34.5, 25.0) | ellipse(c, 32.0, 11.6, 2.5, 1.6), EMBER,
            np.clip(0.3 + 0.16 * np.abs(X - 31.5), 0, 1), 1.4)
    c.paint(rect(c, 5.0, 18.6, 35.0, 20.0), UMBER, 0.95, 1.5)
    c.paint(rect(c, 3.4, 17.8, 6.4, 21.6), EMBER, 0.45, 1.6)
    # the yellow boiler barrel with black end ring and hoops; the tall white chimney with a dark crown
    boiler = rect(c, 8.0, 11.5, 29.6, 18.6)
    c.paint(boiler, SAFFRON, np.clip(0.0 + 0.09 * np.abs(Y - 13.2), 0, 1), 1.4)
    c.paint(boiler & ((np.abs(X - 16.0) < 0.45) | (np.abs(X - 23.0) < 0.45)), UMBER, 0.95, 1.5)
    c.paint(rect(c, 7.2, 11.0, 9.0, 19.0), UMBER, 0.95, 1.5)
    c.paint(c.poly_mask([(8.8, 11.6), (12.0, 11.6), (11.5, 2.8), (9.3, 2.8)]), PEARL, np.where(X < 10.4, 0.0, 0.35), 1.6)
    c.paint(rect(c, 8.6, 1.4, 12.2, 2.9), UMBER, 0.9, 1.7)
    # driving wheels: the far one just showing behind; the near one with a dark iron tyre, twelve
    # straight dark spokes and a brass hub; then the small trailing and tender wheels
    c.paint(c.circle(17.0, rail - 7.9, 7.2) & ~c.circle(17.0, rail - 7.9, 6.2), UMBER, 0.6, 1.5)
    spoked_wheel(c, 14.6, rail - 7.2, 7.2, 12, 1.25, 0.7, tyre=(UMBER, 0.95), spoke=(UMBER, 0.8),
                 hub=(SAFFRON, 0.4), hub_r=1.3, rot=0.13)
    for (wx, wr, n) in ((31.6, 3.0, 6), (39.0, 2.3, 4), (44.0, 2.3, 4)):
        spoked_wheel(c, wx, rail - wr, wr, n, 0.9, 0.5, tyre=(UMBER, 0.95), spoke=(UMBER, 0.8),
                     hub=(UMBER, 0.95), hub_r=0.6, rot=0.26)
    # the inclined cylinder at the rear, its piston rod, crosshead and connecting rod to the crank pin
    c.paint(tube(c, [(32.0, 11.0), (26.0, 17.6)], 2.6, 2.6), UMBER, 0.85, 1.7)
    c.paint(tube(c, [(32.6, 10.4), (31.4, 11.7)], 3.0, 3.0), SAFFRON, 0.55, 1.75)
    c.paint(c.line_mask([(26.0, 17.6), (23.4, 20.6)], 0.8), PEARL, 0.35, 1.8)
    c.paint(c.line_mask([(23.4, 20.6), (18.4, 27.0)], 0.8), PEARL, 0.25, 1.85)
    c.paint(c.circle(23.4, 20.6, 0.8) | c.circle(18.4, 27.0, 0.75), PEARL, 0.1, 1.9)
    frame(c)
    return encode(c.to_tiles())


def firstphoto():
    """The first photograph (1826): in a darkened upstairs room a wooden box camera with a brass lens
    sits on the stone sill between green casements, aimed out over tiled rooftops, chimneys and a
    dovecote under a pale sky; the chemist's jars and the pewter plate on a shelf below."""
    c = Canvas(42, 44)
    X, Y = c.X, c.Y
    tx, ty = tiles(c)

    def tiled(m, fam=EMBER, lo=0.3):
        """Roof tiles: courses split by dark joints so each course breaks into short runs."""
        c.paint(m, fam, lo + 0.25 * (ty % 2), 1.1)
        c.paint(m & ((ty % 2 == 1) | ((tx + 2 * (ty // 2)) % 4 == 0)), UMBER, 0.7, 1.15)
    # the view: pale sky, a tree, the courtyard wall
    c.paint(ALL(c), LAPIS, np.clip(0.35 - 0.3 * (Y - 3) / 14, 0, 1))
    c.paint(c.circle(9.5, 14.5, 3.6) | c.circle(6.8, 16.8, 3.0) | c.circle(12.8, 16.0, 2.6), FERN,
            np.clip(0.5 + 0.25 * smooth_noise(c, 4, 1.2), 0, 1))
    c.paint(Y > 23.5, PEARL, np.clip(0.15 + 0.03 * (Y - 23.5), 0, 1))
    # a dovecote with a pyramid roof, a long barn with chimneys, a slate-roofed house
    c.paint(rect(c, 10, 13.5, 17, 24), SAFFRON, 0.1, 1.05)
    c.paint(rect(c, 12.5, 16, 14.5, 18), UMBER, 0.9, 1.2)
    tiled(c.poly_mask([(13.5, 6.6), (8.6, 13.8), (18.4, 13.8)]))
    c.paint(rect(c, 17, 19, 31, 24), SAFFRON, 0.3, 1.05)
    tiled(c.poly_mask([(19.5, 14.0), (30.5, 14.0), (32.5, 19.2), (16.5, 19.2)]))
    for (cx_, top) in ((22.5, 10.5), (28.5, 11.5)):
        c.paint(rect(c, cx_ - 1, top, cx_ + 1, 14.5), PEARL, 0.5, 1.3)
        c.paint(rect(c, cx_ - 1.5, top - 1.0, cx_ + 1.5, top), UMBER, 0.85, 1.35)
    c.paint(rect(c, 31, 14.5, 37, 24), PEARL, 0.35, 1.05)
    c.paint(c.poly_mask([(30, 15.2), (34.5, 9.6), (39, 15.2)]), LAPIS, np.where(ty % 2 == 0, 0.8, 0.95), 1.1)
    c.paint(rect(c, 33, 17, 35, 20), UMBER, 0.9, 1.2)
    # the darkened room around the window, the window frame, two open green casements with leaded panes
    win = rect(c, 5, 3, 37, 34)
    c.paint(~win, UMBER, np.clip(0.8 + 0.02 * np.abs(X - 21) / 2, 0, 1))
    c.paint(win & ~rect(c, 6, 4, 36, 34), UMBER, 0.45, 1.3)
    for (a, b) in ((5, 1.2), (37, 40.8)):
        leaf = c.poly_mask([(a, 3), (b, 1.2), (b, 37.5), (a, 34)])
        c.paint(leaf, FERN, 0.8, 1.2)
        lo, hi = (2, 3) if a == 5 else (38, 39)
        c.paint(leaf & (tx >= lo) & (tx <= hi) & (ty % 4 != 0) & (ty >= 3) & (ty <= 34), LAPIS, 0.1, 1.3)
    # the stone sill
    c.paint(rect(c, 3, 33.5, 39, 36), PEARL, np.where(Y < 34.5, 0.0, 0.4), 1.3)
    # below the sill: a shelf with the chemist's jars and the pewter plate with its faint rooftops
    c.paint(rect(c, 3, 41, 39, 42), UMBER, 0.45, 1.2)
    for (jx, w, h, fam) in ((5, 2, 3, LAPIS), (8.5, 3, 2, FERN), (13, 2, 3, EMBER), (16.5, 3, 2, SAFFRON)):
        c.paint(rect(c, jx, 41 - h, jx + w, 41), fam, 0.4, 1.3)
        c.paint(rect(c, jx + w / 2 - 0.5, 40 - h, jx + w / 2 + 0.5, 41 - h), UMBER, 0.4, 1.35)
    plate = rect(c, 26, 36.5, 35, 41)
    c.paint(plate, PEARL, 0.3, 1.2)
    ghost = c.poly_mask([(28, 40), (29.5, 37.6), (31, 40)]) | rect(c, 30.5, 38.8, 34, 40)
    c.paint(plate & ghost, PEARL, 0.85, 1.25)
    # the camera: wooden box with dark edges and brass corners, inner sliding box, brass lens tube
    box = rect(c, 8, 24.5, 23, 33.5)
    c.paint(box, UMBER, np.clip(0.05 + 0.03 * (Y - 24.5), 0, 1), 1.5)
    c.paint(box & ((tx == 8) | (tx == 22) | (ty == 24) | (ty == 32)), UMBER, 0.8, 1.55)
    for (bx, by) in ((8, 24), (22, 24), (8, 32), (22, 32)):
        c.paint((tx == bx) & (ty == by), SAFFRON, 0.3, 1.6)
    c.paint(rect(c, 23, 25.5, 26.5, 32.5), UMBER, 0.4, 1.5)
    c.paint(rect(c, 26.5, 26.5, 30.5, 31.5), SAFFRON, np.where(Y < 28.5, 0.1, 0.6), 1.6)
    c.paint(rect(c, 30.5, 26.0, 31.5, 32.0), UMBER, 0.95, 1.6)
    frame(c)
    return encode(c.to_tiles())


# ---------------------------------------------------------------------------
# Master
# ---------------------------------------------------------------------------

def loom():
    """The Jacquard loom (1804): its chain of punched cards, laced edge to edge, feeding down into the
    card cylinder; coloured warp threads below, and the strip of cloth they weave: a bright rosette
    with leaves and little diamonds on a crimson ground."""
    c = Canvas(40, 46)
    X, Y = c.X, c.Y
    tx, ty = tiles(c)
    r = random.Random(41)
    # workshop wall; the loom's two timber posts with brass bolts, and its top beam
    c.paint(ALL(c), LAPIS, np.clip(0.6 + 0.12 * smooth_noise(c, 3, 0.4), 0, 1))
    grain = 0.5 + 0.5 * np.sin(X * 3.1 + np.sin(Y * 0.7) * 2.0)
    posts = ((tx >= 2) & (tx <= 3)) | ((tx >= 36) & (tx <= 37))
    c.paint(posts & (ty >= 2), UMBER, np.clip(0.35 + 0.3 * grain, 0, 1), 1.1)
    c.paint((ty == 2) & (tx >= 2) & (tx <= 37), UMBER, 0.8, 1.1)
    c.paint(posts & (ty % 6 == 5), SAFFRON, 0.3, 1.2)
    # the card chain: each card four rows with square holes, laced to the next, alternately offset
    for k in range(5):
        y0 = 4 + 5 * k
        x0 = 7 + (1 if k % 2 else -1)
        x1 = x0 + 26
        card = (tx >= x0) & (tx < x1) & (ty >= y0) & (ty < y0 + 4)
        c.paint(card, SAFFRON if k % 2 else PEARL, np.where(ty == y0, 0.05, 0.3), 1.2)
        for hx in range(x0 + 1, x1 - 2, 3):
            if r.random() < 0.6:
                c.paint(card & (tx >= hx) & (tx < hx + 2) & (ty >= y0 + 1) & (ty < y0 + 3), UMBER, 0.95, 1.3)
        if k < 4:
            for lx in (x0 + 2, x0 + 13, x1 - 3):
                c.paint((tx == lx) & (ty == y0 + 4), EMBER, 0.4, 1.3)
    # the card cylinder (a square prism with brass pegs)
    c.paint((ty >= 29) & (ty <= 31) & (tx >= 5) & (tx <= 34), UMBER, 0.85, 1.2)
    c.paint((ty == 30) & (tx >= 6) & (tx <= 33) & (tx % 2 == 0), SAFFRON, 0.3, 1.3)
    # coloured warp threads running down into the cloth
    warp = [FERN, SAFFRON, PEARL, FERN, EMBER, SAFFRON]
    for i, wx in enumerate(range(6, 34, 2)):
        c.paint((tx == wx) & (ty >= 32) & (ty <= 33), warp[i % len(warp)], 0.3, 1.2)
    # the woven cloth: crimson ground, rows of small diamonds, a rosette with leaves in the middle
    cloth = (ty >= 34) & (ty <= 43) & (tx >= 5) & (tx <= 34)
    c.paint(cloth, EMBER, np.where((tx + ty) % 2 == 0, 0.65, 0.85), 1.1)
    cols = [SAFFRON, FERN, LAPIS, FERN]
    for i, dx in enumerate(range(7, 34, 4)):
        if abs(dx - 20) < 6:
            continue
        for j, dy in enumerate((36, 41)):
            dm = cloth & (np.abs(tx - dx) + np.abs(ty - dy) <= 1)
            c.paint(dm, cols[(i + 2 * j) % 4], 0.2, 1.3)
    rcx, rcy = 20, 38.5
    for s in (-1, 1):
        c.paint(cloth & ellipse(c, rcx + 0.5 + s * 5.2, rcy + 0.5, 2.8, 1.5, s * 0.5), FERN, 0.45, 1.3)
    d = np.hypot(X - rcx - 0.5, Y - rcy - 0.5)
    ang = np.arctan2(Y - rcy - 0.5, X - rcx - 0.5)
    c.paint(cloth & (d < 3.8 + 0.9 * np.cos(6 * ang)), SAFFRON, 0.15, 1.4)
    c.paint(cloth & (d < 2.2), PEARL, 0.2, 1.5)
    c.paint(cloth & (d < 1.2), LAPIS, 0.4, 1.6)
    # the cloth beam
    c.paint((ty == 44) & (tx >= 4) & (tx <= 35), UMBER, 0.6, 1.2)
    frame(c)
    return encode(c.to_tiles())


def diffengine():
    """Babbage's Difference Engine (1822 design): columns of stacked brass figure wheels marked with
    abstract digits, steel shafts and bronze carry levers between them, held between iron plates on
    turned steel pillars, gears and a crank on top, on an iron stand over a tiled floor."""
    c = Canvas(44, 42)
    X, Y = c.X, c.Y
    tx, ty = tiles(c)
    r = random.Random(1822)
    # dark blue wall and a green-and-cream tiled floor
    c.paint(ALL(c), LAPIS, np.clip(0.7 + 0.25 * Y / 42, 0, 1))
    floor = ty >= 37
    c.paint(floor, PEARL, 0.2)
    c.paint(floor & (((tx // 2) + (ty // 2)) % 2 == 0), FERN, 0.55, 1.1)
    # the iron stand
    c.paint((ty >= 33) & (ty <= 34) & (tx >= 3) & (tx <= 40), UMBER, 0.75, 1.2)
    for lx in (4, 21, 38):
        c.paint((ty >= 35) & (ty <= 37) & (tx >= lx) & (tx <= lx + 1), UMBER, 0.85, 1.2)
    # iron plates top and bottom, turned steel pillars at the corners
    c.paint((ty >= 7) & (ty <= 8) & (tx >= 3) & (tx <= 40), UMBER, 0.9, 1.2)
    c.paint((ty == 31) & (tx >= 3) & (tx <= 40), UMBER, 0.9, 1.2)
    c.paint((ty == 32) & (tx >= 3) & (tx <= 40), PEARL, 0.5, 1.2)
    for px in (4, 38):
        c.paint((ty >= 9) & (ty <= 30) & (tx >= px) & (tx <= px + 1), PEARL, np.where(ty % 3 == 0, 0.7, 0.15), 1.2)
    # four columns of seven figure wheels each, shafts in the gaps, bronze carry levers between columns
    for col, cx_ in enumerate((9, 16, 23, 30)):
        for k in range(7):
            y0 = 10 + 3 * k
            wheel = (tx >= cx_) & (tx <= cx_ + 4) & (ty >= y0) & (ty <= y0 + 1)
            rnd = np.abs(tx - cx_ - 2) / 2.0
            c.paint(wheel, SAFFRON, np.where(ty == y0, 0.02 + 0.3 * rnd, 0.5 + 0.35 * rnd), 1.3)
            for _ in range(r.choice((1, 2))):
                c.paint(wheel & (tx == cx_ + r.randrange(5)) & (ty == y0 + r.randrange(2)), UMBER, 0.95, 1.4)
            c.paint((tx == cx_ + 2) & (ty == y0 - 1), PEARL, 0.35, 1.3)
            if col < 3 and (k + col) % 2 == 0:
                c.paint((tx >= cx_ + 5) & (tx <= cx_ + 6) & (ty >= y0) & (ty <= y0 + 1), EMBER, 0.5, 1.3)
    # gears and the crank on top
    for (gx, gr, n, fam, rot) in ((10.5, 2.8, 9, SAFFRON, 0.0), (16.6, 2.1, 7, EMBER, 0.3), (22.5, 2.8, 9, SAFFRON, 0.2),
                                  (28.6, 2.1, 7, EMBER, 0.1)):
        c.paint(gear(c, gx, 4.0, gr, n, 0.8, rot), fam, 0.4, 1.4)
        c.paint(c.circle(gx, 4.0, 0.7), UMBER, 0.9, 1.5)
    c.paint(c.line_mask([(28.6, 4.0), (35.5, 2.4)], 0.8), UMBER, 0.9, 1.6)
    c.paint(c.circle(36.2, 2.4, 1.0), PEARL, 0.2, 1.7)
    c.paint(rect(c, 28.1, 4.0, 29.1, 7.0) | rect(c, 10.0, 4.0, 11.0, 7.0) | rect(c, 22.0, 4.0, 23.0, 7.0), PEARL, 0.4, 1.35)
    frame(c)
    return encode(c.to_tiles())


SCENES = {
    "pennyfarthing": pennyfarthing, "lightbulb": lightbulb, "telephone": telephone, "flyingmachine": flyingmachine,
    "rocket": rocket, "firstphoto": firstphoto, "loom": loom, "diffengine": diffengine,
}
