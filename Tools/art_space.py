"""Probes & Telescopes pack: famous views sent home by spacecraft, rovers and space telescopes, each
drawn as an original tile composition with the supersampled Canvas of art.py (a tile's colour family
comes from the dominant object under it, its tone from the shading). No agency marks anywhere.

Gentle: Earthrise (Apollo 8, 1968), Pluto's heart (New Horizons, 2015), Jupiter's Great Red Spot,
a blue sunset on Mars.
Challenge: the Pillars of Creation (Hubble, 1995), a six-wheeled rover on the rocks of Mars.
Master (very busy, every colour in many small islands): the Cosmic Cliffs of Carina (Webb, 2022)
and the Hubble Deep Field (1995).
"""
import math
import random

import numpy as np

from art import Canvas, LAPIS, SAFFRON, FERN, EMBER, UMBER, PEARL, encode
from art_scenes import ALL, ellipse, rect, frame, smooth_noise


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def tiles(c):
    """Integer tile coordinates of every canvas pixel."""
    return np.floor(c.X).astype(int), np.floor(c.Y).astype(int)


def tile_star(c, T, x, y, fam=PEARL, shade=0.0, arm=0, vert=None, diag=0, prio=1.8):
    """A tile-exact star at tile (x, y): the centre tile plus optional horizontal arms (`arm` tiles),
    vertical arms (`vert`, default = arm) and diagonal arms (`diag`) - the telescope's spikes."""
    tx, ty = T
    vert = arm if vert is None else vert
    dx, dy = tx - x, ty - y
    m = (dx == 0) & (dy == 0)
    if arm:
        m |= (dy == 0) & (np.abs(dx) <= arm)
    if vert:
        m |= (dx == 0) & (np.abs(dy) <= vert)
    if diag:
        m |= (np.abs(dx) == np.abs(dy)) & (np.abs(dx) <= diag)
    c.paint(m, fam, shade, prio)


def scatter(seed, n, x0, y0, x1, y1, ok=lambda x, y: True, gap=2):
    """n random tiles in [x0, x1) x [y0, y1), at least `gap` apart (Chebyshev) and allowed by ok()."""
    r = random.Random(seed)
    pts, tries = [], 0
    while len(pts) < n and tries < 20000:
        tries += 1
        x, y = r.randrange(x0, x1), r.randrange(y0, y1)
        if ok(x + 0.5, y + 0.5) and all(max(abs(x - a), abs(y - b)) > gap for a, b in pts):
            pts.append((x, y))
    return pts


def column(c, pts, widths, rough=0.0, seed=0, freq=0.8):
    """A soft column along `pts` whose width follows `widths` (one per point); `rough` roughens its edge
    with smooth noise, for clouds of gas and dust."""
    dense = []
    for (p, q, wa, wb) in zip(pts[:-1], pts[1:], widths[:-1], widths[1:]):
        n = max(2, int(math.hypot(q[0] - p[0], q[1] - p[1]) * 2.5))
        for k in range(n):
            t = k / n
            dense.append((p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t, wa + (wb - wa) * t))
    dense.append((pts[-1][0], pts[-1][1], widths[-1]))
    sd = np.full(c.X.shape, 99.0, np.float32)
    for (x, y, w) in dense:
        sd = np.minimum(sd, np.hypot(c.X - x, c.Y - y) - w / 2)
    if rough:
        sd = sd - rough * smooth_noise(c, seed, freq)
    return sd


def streaks(c, seed, fx, fy):
    """Smooth noise stretched along one axis (fx, fy = frequencies across x and y), for streaky gas and dust."""
    r = random.Random(seed)
    n = np.zeros_like(c.X)
    for _ in range(5):
        a, b, p = r.uniform(-1, 1), r.uniform(-1, 1), r.uniform(0, 6.28)
        n += np.sin(a * c.X * fx + b * c.Y * fy + p)
    return n / 5.0


def heart(c, hx, hy, s, ang=0.0):
    """A heart about 2s tiles wide: two round lobes (the left one larger) over a point, tilted by `ang`;
    returns (mask, u) with u < 0 on the left lobe."""
    u0, v0 = (c.X - hx) / s, (c.Y - hy) / s
    u = u0 * math.cos(ang) + v0 * math.sin(ang)
    v = -u0 * math.sin(ang) + v0 * math.cos(ang)
    lobes = ((u + 0.48) ** 2 + (v + 0.12) ** 2 < 0.6 ** 2) | ((u - 0.5) ** 2 + (v + 0.2) ** 2 < 0.52 ** 2)
    point = (v > -0.15) & (np.abs(u + 0.03) < (1.3 - v) * 0.72)
    return lobes | point, u


# ---------------------------------------------------------------------------
# gentle
# ---------------------------------------------------------------------------

def earthrise():
    """Apollo 8, Christmas Eve 1968: the half-lit blue-and-white Earth rising over the grey, cratered
    horizon of the Moon in black space."""
    c = Canvas(46, 40)
    X, Y = c.X, c.Y
    T = tiles(c)
    c.paint(ALL(c), UMBER, 1.0)                                                 # black space
    ex, ey, er = 17.0, 12.6, 10.9
    horizon = 27.0 + 0.006 * (X - 26) ** 2 - 0.09 * (X - 26) + 0.3 * np.sin(X * 0.8) + 0.2 * np.sin(X * 2.1 + 1)
    for i, (x, y) in enumerate(scatter(68, 18, 1, 1, 45, 22, lambda x, y: math.hypot(x - ex, y - ey) > er + 2)):
        tile_star(c, T, x, y, SAFFRON if i % 3 else PEARL, 0.0 if i % 3 else 0.3, prio=1.5)
    # the Earth: a sphere lit from the upper left; the night side a deep blue shadow
    nx, ny = (X - ex) / er, (Y - ey) / er
    earth = nx * nx + ny * ny < 1
    nz = np.sqrt(np.clip(1 - nx * nx - ny * ny, 0, 1))
    lam = (-0.8 * nx - 0.35 * ny + 0.3 * nz) / math.sqrt(0.8 ** 2 + 0.35 ** 2 + 0.3 ** 2)
    lit = earth & (lam > 0.0)
    c.paint(earth, LAPIS, 1.0, 1.2)
    c.paint(lit, LAPIS, np.clip(0.75 - 0.9 * lam, 0, 0.66), 1.2)
    # a big desert continent with green edges, and swirling white clouds on the day side
    land = lit & (smooth_noise(c, 8, 0.3) + 0.3 * nx - 0.2 * ny > 0.0)
    c.paint(land, SAFFRON, np.clip(1.2 - 0.4 * lam, 0.8, 1), 1.25)
    c.paint(land & (smooth_noise(c, 9, 0.6) > 0.3), FERN, 0.9, 1.3)
    ang = np.arctan2(Y - ey - 4, X - ex + 3)
    swirl = np.sin(ang * 2 + np.hypot(X - ex + 3, Y - ey - 4) * 0.9 + 2.0 * smooth_noise(c, 4, 0.4))
    clouds = lit & ((swirl > 0.6) | (smooth_noise(c, 12, 0.5) > 0.5))
    c.paint(clouds, PEARL, np.clip(0.05 + 0.6 * (1 - lam), 0, 0.66), 1.3)
    # the Moon's grey surface, with craters foreshortened by the low view, lit from the left
    moon = Y > horizon
    n = smooth_noise(c, 3, 0.7)
    c.paint(moon, PEARL, np.clip(0.72 + 0.02 * (Y - 26) + 0.15 * n, 0, 1))
    c.paint(moon & (Y < horizon + 1.0), PEARL, 0.25, 1.1)                              # sunlit far rim
    for (x, y, rx) in ((6, 29.5, 2.6), (24.5, 28.4, 2.0), (33.5, 28.3, 2.4), (43, 29.0, 2.0), (18.0, 32.0, 3.8),
                       (37.0, 33.0, 4.2), (7.0, 37.0, 5.4), (27.5, 37.5, 6.6), (42.5, 37.8, 2.6),
                       (27.5, 31.4, 2.2), (13.0, 28.6, 1.8)):
        ry = rx * (0.32 + 0.025 * (y - 26))
        c.paint(ellipse(c, x, y, rx * 1.22, ry * 1.4) & moon, PEARL, 0.0, 1.3)          # bright raised rim
        bowl = ellipse(c, x, y, rx, ry) & moon
        c.paint(bowl, PEARL, 0.95, 1.35)                                                # grey floor
        c.paint(bowl & ~ellipse(c, x + 0.6 * rx, y + 0.25 * ry, rx, ry), UMBER, 0.9, 1.4)   # shadowed wall
    frame(c)
    return encode(c.to_tiles())


def plutoheart():
    """New Horizons, July 2015: Pluto's tan and peach globe with its great pale heart, the dark
    red-brown 'whale' along the equator, and small grey Charon with its red cap."""
    c = Canvas(42, 42)
    X, Y = c.X, c.Y
    T = tiles(c)
    c.paint(ALL(c), LAPIS, 1.0)                                                 # deep blue space
    px, py, R = 22.5, 22.0, 17.4
    for (x, y) in scatter(15, 16, 1, 1, 41, 41, lambda x, y: math.hypot(x - px, y - py) > R + 1.2
                          and math.hypot(x - 5.5, y - 5.5) > 4.5):
        tile_star(c, T, x, y, PEARL, 0.1, prio=1.5)
    nx, ny = (X - px) / R, (Y - py) / R
    r2 = nx * nx + ny * ny
    disc = r2 < 1
    limb = np.clip(r2 ** 2, 0, 1)
    n1, n2 = smooth_noise(c, 31, 0.5), smooth_noise(c, 5, 0.7)
    lat = ny + 0.12 * n1
    # zones: a grey-beige north polar cap, a peach band, tan-orange middle, brown south
    c.paint(disc, SAFFRON, np.clip(0.75 + 0.3 * limb + 0.1 * n2, 0, 1))
    c.paint(disc & (lat > -0.6) & (lat < -0.16) & (n2 > -0.3), EMBER, np.clip(0.0 + 0.45 * limb, 0, 1), 1.05)
    c.paint(disc & (lat <= -0.6), PEARL, np.clip(0.7 + 0.35 * limb, 0, 1), 1.05)
    c.paint(disc & (lat > 0.5 + 0.15 * n2), UMBER, np.clip(0.05 + 0.4 * limb, 0, 1), 1.05)
    # the dark red-brown 'whale' along the equator, and the dark spots beyond the heart
    whale = (ellipse(c, 13.0, 26.0, 9.5, 3.3, 0.18) | ellipse(c, 6.5, 24.0, 2.8, 4.8, 0.15)) & disc
    whale |= disc & (ellipse(c, 37.0, 28.0, 2.6, 1.5, -0.4) | ellipse(c, 34.5, 31.0, 1.8, 1.2, 0))
    c.paint(whale, UMBER, np.clip(0.75 + 0.3 * limb, 0, 1), 1.1)
    # the heart: the smooth bright left lobe and the greyer right lobe
    hm, u = heart(c, 26.0, 23.5, 6.8, 0.25)
    hm &= disc
    c.paint(hm, PEARL, np.clip(np.where(u < 0.05, 0.0, 0.33) + 0.4 * limb, 0, 1), 1.2)
    # Charon: grey with its red polar cap
    ch = c.circle(5.5, 5.5, 3.2)
    c.paint(ch, PEARL, np.clip(0.55 + 0.1 * (X - 4), 0, 1), 1.3)
    c.paint(ch & (Y < 4.0), EMBER, 0.9, 1.35)
    frame(c)
    return encode(c.to_tiles())


def redspot():
    """Jupiter close up: cream, tan, brown and orange cloud bands flowing around the great oval of the
    Red Spot in its pale collar, white ovals downstream, the planet's edge and little Io in a corner."""
    c = Canvas(48, 36)
    X, Y = c.X, c.Y
    cx, cy, rx, ry = 18.5, 20.5, 9.6, 5.8
    sx, sy = (X - cx) / rx, (Y - cy) / ry
    rho2 = np.maximum(sx * sx + sy * sy, 1.0)
    # streamlines of the flow around the oval, wavy edges, and turbulence in its wake to the left
    wake = np.exp(-((Y - cy + 2) / 5.0) ** 2) * np.clip((cx - 4 - X) / 8.0, 0, 1.2)
    v = (cy + ry * sy * (1 - 1 / rho2) + 0.45 * np.sin(X * 0.42 + 0.3 * Y) + 0.35 * smooth_noise(c, 3, 0.8)
         + 2.6 * wake * smooth_noise(c, 7, 0.75))
    edge = np.hypot(X - 2.0, Y - 52.0)                      # distance from the planet's centre, for the limb
    limb = np.clip((edge - 46.0) / 11.0, 0, 1) ** 2 * 0.45
    bands = ((-99, 2.6, UMBER, 0.2), (2.6, 4.6, SAFFRON, 0.25), (4.6, 9.8, PEARL, 0.1), (9.8, 11.8, SAFFRON, 0.4),
             (11.8, 18.2, EMBER, 0.1), (18.2, 22.8, PEARL, 0.05), (22.8, 27.6, SAFFRON, 0.5), (27.6, 29.8, UMBER, 0.3),
             (29.8, 32.4, PEARL, 0.4), (32.4, 99, UMBER, 0.05))
    for lo, hi, fam, sh in bands:
        m = (v >= lo) & (v < hi)
        c.paint(m, fam, np.clip(sh + 0.3 * (v - lo) / (hi - lo) * (fam != PEARL) + limb, 0, 1))
    # bluish-grey festoons hanging from the brown belt into the bright equatorial zone
    for fx in (3.0, 14.0, 25.0, 34.0):
        c.paint(c.line_mask([(fx, 4.8), (fx + 2.0, 6.8), (fx + 4.5, 8.0), (fx + 6.5, 8.2)], 1.0), LAPIS, 0.55, 1.2)
    # the Great Red Spot: a deep red rim, a brick-red ring and a paler salmon heart
    rr = np.sqrt(sx * sx + sy * sy)
    spot = rr <= 1
    c.paint(spot, EMBER, np.where(rr > 0.82, 0.95, np.where(rr > 0.5, 0.62, 0.3)), 1.3)
    c.paint(spot & (rr < 0.5) & (np.sin(np.arctan2(sy, sx) * 2 + rr * 9) > 0.6), EMBER, 0.6, 1.32)
    # white ovals in the tan belt below it
    for (ox, oy) in ((33.5, 26.0), (42.5, 26.3)):
        c.paint(ellipse(c, ox, oy, 2.4, 1.3), PEARL, 0.0, 1.4)
    # the planet's edge: space in the top-right corner, with little Io
    space = edge > 56.5
    c.paint(space, LAPIS, 1.0, 1.5)
    io = c.circle(43.0, 5.0, 2.4)
    c.paint(io, SAFFRON, np.clip(0.1 + 0.2 * np.hypot(X - 42.3, Y - 4.3), 0, 1), 1.6)
    c.paint(io & (c.circle(43.8, 5.6, 0.6) | c.circle(42.3, 4.6, 0.45)), EMBER, 0.4, 1.65)
    frame(c)
    return encode(c.to_tiles())


def marssunset():
    """A rover's view of sunset on Mars: a small pale sun sinking to a crater rim in a soft blue
    glow, the dusty butterscotch sky darkening to brown above, dark rocky ground in front."""
    c = Canvas(38, 46)
    X, Y = c.X, c.Y
    sx, sy = 16.5, 29.2
    n1, n2 = smooth_noise(c, 2, 0.35), smooth_noise(c, 6, 0.6)
    # dusty sky: brown high up, butterscotch lower, a peach haze along the rim, a round blue glow
    # about the small white sun
    c.paint(ALL(c), UMBER, np.where(Y < 7.0 + 1.5 * n1, 1.0, 0.67))
    for (x, y, L, a) in ((9, 5.5, 5.5, -0.08), (27, 8.0, 6.5, 0.06), (13, 11.0, 4.5, 0.05), (32, 3.6, 3.5, 0.0)):
        c.paint(ellipse(c, x, y, L, 0.75, a) | ellipse(c, x + 0.3 * L, y - 0.6, 0.5 * L, 0.6, a), SAFFRON, 1.0, 1.05)   # dust clouds
    c.paint(Y > 13.5 + 2.0 * n1 + 1.2 * np.sin(X * 0.3), SAFFRON, 1.0)
    c.paint(Y > 25.5 + 1.5 * n2 + 0.8 * np.sin(X * 0.5 + 1), EMBER, np.where(Y > 28.5, 0.0, 0.33))
    r = np.hypot((X - sx) / 1.25, Y - sy) + 0.7 * n2
    c.paint(r < 8.4, LAPIS, np.clip(0.11 * (r - 1.5), 0, 0.72), 1.05)
    c.paint(r < 2.4, PEARL, 0.35, 1.1)
    c.paint(c.circle(sx, sy, 1.3), PEARL, 0.0, 1.6)
    # the far crater rim in silhouette, and the dark slope in front rising to the right
    rim = Y > 31.0 + 0.5 * np.sin(X * 0.4 + 1.4) + 0.3 * np.sin(X * 1.3) - 6.0 * np.exp(-((X - 31) / 3.2) ** 4)
    c.paint(rim, UMBER, 0.67)
    c.paint(Y > 36.0 - 0.2 * X + 0.4 * np.sin(X * 0.9) + 0.6 * n1, UMBER, 1.0)
    # boulders on the slope, brown, their tops rimmed rust-red by the last light
    for (x, y, s) in ((5.5, 42.0, 2.8), (14.0, 39.5, 1.7), (22.5, 43.0, 2.2), (30.0, 38.5, 1.4), (33.5, 43.0, 2.0),
                      (24.5, 36.8, 1.1), (35.5, 35.8, 1.0), (17.5, 37.0, 1.0), (3.5, 37.2, 1.1)):
        rock = ellipse(c, x, y, 1.5 * s, 1.1 * s) & (Y < y + 0.6 * s)
        c.paint(rock, UMBER, 0.33, 1.2)
        c.paint(rock & ~ellipse(c, x + 0.3 * s, y + 0.55 * s, 1.5 * s, 1.1 * s), EMBER, 0.9, 1.25)   # lit crown
    frame(c)
    return encode(c.to_tiles())


# ---------------------------------------------------------------------------
# challenge
# ---------------------------------------------------------------------------

def pillars():
    """Hubble, 1995: the Pillars of Creation - three tall dark columns of dust, their heads glowing
    white and gold, standing in green and blue gas with four-spiked stars scattered through it."""
    c = Canvas(40, 46)
    X, Y = c.X, c.Y
    T = tiles(c)
    n1, n2, n3 = smooth_noise(c, 3, 0.3), smooth_noise(c, 11, 0.55), smooth_noise(c, 19, 0.9)
    # glowing gas: green above, blue-teal lower down and to the right, with clouds of each in the other
    c.paint(ALL(c), FERN, np.clip(0.6 + 0.015 * Y + 0.3 * n2, 0, 1))
    c.paint(X * 0.4 + Y * 0.55 + 6 * n1 > 31, LAPIS, np.clip(0.55 + 0.35 * n2, 0, 1))
    c.paint((n3 > 0.3) & (Y < 34), LAPIS, 0.7, 1.02)
    c.paint((n3 < -0.42) & (X * 0.4 + Y * 0.55 + 6 * n1 > 31), FERN, 0.85, 1.02)
    # three tall columns of dust leaning a little to the right, bulging at their heads
    left = column(c, [(8, 47), (10, 34), (11.5, 22), (13, 11), (14.5, 5.5)], [11, 7.5, 6.5, 6.0, 5.6], 0.9, 21)
    mid = column(c, [(23, 47), (23.5, 37), (22.5, 27.5), (22.2, 21.5)], [9, 6.5, 5.2, 5.2], 0.8, 22)
    right = column(c, [(35.5, 47), (34.5, 40.5), (32.6, 34.5), (31.2, 31.5)], [7.5, 5.5, 4.0, 3.4], 0.6, 23)
    near = np.minimum.reduce([left, mid, right])
    heads = ((left < 3.2 + 1.5 * n2) & (Y < 13)) | ((mid < 2.6 + 1.2 * n2) & (Y < 26)) | ((right < 1.8) & (Y < 34))
    c.paint(heads, SAFFRON, np.clip(0.0 + 0.25 * near, 0, 1), 1.05)                      # golden glow round the heads
    c.paint(~heads & (near < 5.5) & (near > 0) & (Y < 28) & (n2 > -0.1), FERN, 0.3, 1.03)     # green glow beyond it
    for i, (s, tip) in enumerate(((left, 14), (mid, 27), (right, 36))):
        body = s < 0
        lit = body & (np.roll(s, 9, axis=0) > -0.2) & (Y < tip)                        # edge facing the stars above
        c.paint(body, UMBER, np.clip(0.6 + 0.3 * n3 + 0.008 * Y, 0, 1), 1.2)
        c.paint(body & (streaks(c, 40 + i, 1.4, 0.35) > 0.3) & (s < -0.8) & (Y > tip + 2), UMBER, 1.0, 1.25)
        c.paint(body & (s > -0.9) & ~lit, UMBER, 0.2, 1.26)                               # paler fringe
        c.paint(lit, PEARL, 0.3, 1.3)
    c.paint((near < 0) & (Y > 42.6 + 1.6 * n3 + 0.8 * n2), FERN, 0.75, 1.4)                # their feet lost in the gas
    # little evaporating globules off the left pillar's head
    for (x, y) in ((18.2, 4.2), (17.6, 1.9), (18.6, 7.4)):
        c.paint(c.circle(x, y, 0.8), UMBER, 0.6, 1.35)
    # stars: points and four-spiked bright ones
    for i, (x, y) in enumerate(scatter(95, 42, 1, 1, 39, 45, lambda x, y: near[int(y * 8), int(x * 8)] > 0.8)):
        tile_star(c, T, x, y, PEARL if i % 3 else SAFFRON, 0.0, 1 if i % 2 else 0)
    frame(c)
    return encode(c.to_tiles())


def rover():
    """A six-wheeled rover on Mars in three-quarter view - blue solar deck, white body, mast camera
    head and dish antenna on rocker-bogie legs - on red rocks and orange dunes, its tracks behind it."""
    c = Canvas(48, 38)
    X, Y = c.X, c.Y
    T = tiles(c)
    tx, ty = T
    n1 = smooth_noise(c, 4, 0.4)
    # dusty pink sky, brown hills, then red rocky ground with broad rippled orange dunes
    c.paint(ALL(c), EMBER, 0.0)
    c.paint(Y > 9.5 + 1.6 * np.sin(X * 0.2 + 0.5) + 0.6 * np.sin(X * 0.7), UMBER, np.where(Y < 12.0, 0.0, 0.33))
    ground = Y > 13.0 + 0.5 * np.sin(X * 0.3 + 2)
    c.paint(ground, EMBER, np.clip(0.6 + 0.015 * (Y - 13) + 0.2 * n1, 0, 1))
    dunes = ground & ((Y < 16.5 + 1.5 * np.sin(X * 0.25)) | (Y > 35.0 + 1.2 * n1))
    ripple = np.sin(Y * 2.2 + X * 0.35 + 0.8 * np.sin(X * 0.45)) > 0.6
    c.paint(dunes, SAFFRON, np.where(ripple, 0.45, 0.85))
    # rocks, dark brown and red, lit on top
    rnd = random.Random(12)
    for (x, y) in scatter(12, 9, 1, 17, 47, 35, lambda x, y: not (5 < x < 43 and 12 < y < 36) and
                          abs(y - 34.2 + 0.05 * (10.5 - x) ** 2 + 0.1 * (10.5 - x)) > 2.5, gap=3):
        s = 0.6 + 0.05 * (y - 14)
        rock = ellipse(c, x + 0.5, y + 0.5, s * rnd.uniform(1.3, 1.8), s, rnd.uniform(-0.3, 0.3))
        fam = UMBER if rnd.random() < 0.6 else EMBER
        c.paint(rock, fam, 0.0 if fam == UMBER else 0.95, 1.2)
        c.paint(rock & (Y > y + 0.5 + 0.1 * s), UMBER, 0.95, 1.25)
    # its tracks, curving away behind it: two treads of cleat marks
    for (x0, y0, w, k) in ((10.0, 34.2, 1.6, 0.05), (13.5, 31.4, 1.2, 0.025)):
        yy = y0 - k * (x0 - X) ** 2 - 0.1 * (x0 - X)
        c.paint((np.abs(Y - yy) < w / 2) & (X < x0), UMBER, np.where(tx % 2 == 0, 0.67, 0.33), 1.3)
    # shadow, far wheels, rocker-bogie legs, near wheels (dark tyres round grey hubs)
    c.paint(ellipse(c, 24.0, 34.3, 14.0, 1.0), UMBER, 0.9, 1.25)
    for (x, y, r) in ((16.0, 28.6, 2.4), (27.0, 28.6, 2.4), (38.0, 28.6, 2.4)):
        c.paint(c.circle(x, y, r), UMBER, 0.6, 1.5)
        c.paint(c.circle(x, y, r - 0.9), PEARL, 0.9, 1.52)
    for pts in ([(25.0, 23.0), (18.0, 25.5), (12.0, 31.0)], [(18.0, 25.5), (23.5, 31.0)], [(25.0, 23.0), (31.5, 24.5), (35.0, 31.0)]):
        c.paint(c.line_mask(pts, 1.1), PEARL, 0.4, 1.58)
    for (x, y, r) in ((12.0, 31.0, 3.0), (23.5, 31.0, 3.0), (35.0, 31.0, 3.0)):
        c.paint(c.circle(x, y, r), UMBER, 1.0, 1.6)
        c.paint(c.circle(x, y, r - 0.95), PEARL, 0.55, 1.62)
        c.paint(c.circle(x, y, 0.65), UMBER, 0.8, 1.65)
    # the body and the solar deck seen from above: blue cells with dark seams
    c.paint(rect(c, 14.0, 17.5, 34.0, 23.4), PEARL, np.where(X > 31.0, 0.67, 0.1), 1.4)
    c.paint(rect(c, 14.0, 22.4, 34.0, 23.4), PEARL, 0.95, 1.45)
    deck = c.poly_mask([(5.5, 17.6), (40.5, 17.6), (44.5, 12.4), (9.5, 12.4)])
    c.paint(deck, LAPIS, np.clip(0.33 + 0.33 * (ty % 2) + 0.02 * (X - 8), 0, 1), 1.5)
    c.paint(deck & ((((tx + ty) % 5) == 0) | (ty == 15)), UMBER, 0.95, 1.52)
    c.paint(rect(c, 5.5, 17.0, 40.5, 18.0), PEARL, 0.25, 1.55)
    # mast with its camera head, the dish antenna and a thin low-gain mast
    c.paint(c.line_mask([(36.0, 13.5), (36.0, 5.0)], 1.0), PEARL, 0.3, 1.6)
    c.paint(rect(c, 32.0, 2.0, 40.5, 5.6), PEARL, 0.05, 1.65)
    for ex in (37.5, 39.5):
        c.paint(rect(c, ex - 0.5, 3.0, ex + 0.5, 4.6), UMBER, 1.0, 1.7)
    c.paint(c.line_mask([(19.5, 14.0), (19.5, 10.5)], 0.8), PEARL, 0.5, 1.6)
    c.paint(ellipse(c, 19.0, 9.2, 3.3, 2.2, -0.35), PEARL, 0.0, 1.62)
    c.paint(ellipse(c, 19.3, 9.5, 1.3, 0.8, -0.35), PEARL, 0.67, 1.64)
    c.paint(c.line_mask([(13.0, 13.0), (13.0, 5.5)], 0.55), PEARL, 0.6, 1.6)
    frame(c)
    return encode(c.to_tiles())


# ---------------------------------------------------------------------------
# master
# ---------------------------------------------------------------------------

def cliffs():
    """Webb, 2022: the Cosmic Cliffs of Carina - ridge behind ridge of billowing orange and brown gas and
    dust, each with a glowing edge, under a blue sky of pale haze crowded with spiked stars."""
    c = Canvas(46, 40)
    X, Y = c.X, c.Y
    T = tiles(c)
    n1, n2, n3 = smooth_noise(c, 5, 0.5), smooth_noise(c, 17, 1.0), smooth_noise(c, 29, 0.6)
    # blue sky, deeper towards the top, pale haze patches low down
    c.paint(ALL(c), LAPIS, np.clip(1.1 - 0.05 * Y + 0.15 * n1, 0.0, 1))
    c.paint((smooth_noise(c, 61, 0.8) > 0.4) & (Y > 8) & (Y < 21), PEARL, 0.45, 1.02)
    # three ridges, back to front, with scalloped billowy tops: (top line, body, rim, knots)
    back = (16.5 + 2.4 * np.sin(X * 0.2 + 0.6) + 1.2 * np.sin(X * 0.55 + 2.0) - 6.5 * np.exp(-((X - 30) / 2.6) ** 2)
            - 4.5 * np.exp(-((X - 10) / 2.2) ** 2) - 1.3 * np.abs(np.sin(X * 0.62)))
    mid = 25.0 + 2.0 * np.sin(X * 0.27 + 2.5) + 1.0 * np.sin(X * 0.7) - 3.5 * np.exp(-((X - 19) / 2.0) ** 2) - 1.3 * np.abs(np.sin(X * 0.55 + 1))
    front = 32.0 + 1.8 * np.sin(X * 0.3 + 4.0) + 0.9 * np.sin(X * 0.8 + 1) - 1.2 * np.abs(np.sin(X * 0.5 + 2))
    for k, (tl, body, rim, knot) in enumerate(((back, EMBER, SAFFRON, LAPIS), (mid, UMBER, EMBER, SAFFRON),
                                              (front, UMBER, EMBER, EMBER))):
        m = Y > tl + 0.5 * n3
        d = Y - tl
        c.paint(m, body, np.clip((0.25, 0.0, 0.67)[k] + 0.05 * d + 0.2 * n2, 0, 1), 1.0 + 0.02 * k)
        c.paint(m & (n1 + 0.5 * n2 + 0.2 * k > 0.6) & (d > 2.5), knot, (0.4, 0.6, 0.6)[k], 1.03 + 0.02 * k)
        c.paint(m & (d < (3.2, 1.3, 1.1)[k] + 0.9 * n2), rim, np.clip((0.0, 0.33, 0.67)[k] + 0.08 * d, 0, 1), 1.04 + 0.02 * k)
        if k == 0:
            c.paint(m & (d < 1.0 + 0.5 * n2), PEARL, 0.25, 1.05)                         # white-hot edge
    # stars: bright ones with eight spikes, crosses, a few single points
    for i, (x, y) in enumerate(scatter(2022, 74, 1, 1, 45, 39, gap=2)):
        fam = (PEARL, SAFFRON, PEARL, PEARL, PEARL, EMBER)[i % 6]
        in_sky = y + 0.5 < back[int(y * 8 + 4), int(x * 8 + 4)]
        if i < 6:
            tile_star(c, T, x, y, PEARL if i % 2 else SAFFRON, 0.0, arm=1, vert=3, diag=2, prio=1.9)
        elif i < 58 and (in_sky or i % 3) and fam != EMBER:
            tile_star(c, T, x, y, fam, 0.05, arm=1, vert=1, prio=1.8)
        else:
            tile_star(c, T, x, y, fam, 0.05, prio=1.8)
    frame(c)
    return encode(c.to_tiles())


def deepfield():
    """The Hubble Deep Field (1995): a dark patch of sky packed with distant galaxies - golden
    ellipticals, blue and white spirals, an edge-on disc, red smudges - each in a dim glow of reddened or
    bluish light, and a few spiked foreground stars."""
    c = Canvas(44, 44)
    X, Y = c.X, c.Y
    T = tiles(c)
    c.paint(ALL(c), UMBER, 1.0)
    rnd = random.Random(1995)

    def oval(x, y, rx, ry, ang, fam, glow, core=0.0, halo=0.8, prio=1.4):
        """A galaxy seen as a soft oval: a bright core fading outwards inside a dim glow (`glow` family)."""
        q = np.hypot(((X - x) * math.cos(ang) + (Y - y) * math.sin(ang)) / rx,
                     (-(X - x) * math.sin(ang) + (Y - y) * math.cos(ang)) / ry)
        if halo:
            c.paint(q < 1 + halo / min(rx, ry), glow, 1.0, prio - 0.1)
        c.paint(q < 1, fam, np.clip(core + 0.75 * q, 0, 1), prio)

    def spiral(x, y, r, ang, incl, core, arm, glow):
        ca, sa = math.cos(ang), math.sin(ang)
        gx = (X - x) * ca + (Y - y) * sa
        gy = (-(X - x) * sa + (Y - y) * ca) / incl
        rr = np.hypot(gx, gy)
        psi = np.arctan2(gy, gx) - np.log(np.maximum(rr, 0.3) / (0.25 * r)) / 0.32
        c.paint(rr < r * 1.15, glow, 1.0, 1.3)
        c.paint((rr < r) & (np.cos(2 * psi) > 0.0), arm, np.clip(0.0 + 0.6 * rr / r, 0, 1), 1.4)
        c.paint(rr < 0.34 * r, core, 0.0, 1.5)
    # the big ones: a face-on spiral, a tilted spiral, a giant elliptical, an edge-on disc, red and blue irregulars
    spiral(11.0, 11.0, 6.4, 0.4, 0.8, SAFFRON, PEARL, LAPIS)
    spiral(32.5, 31.5, 5.6, -0.6, 0.62, SAFFRON, LAPIS, LAPIS)
    oval(32.0, 10.0, 4.2, 3.0, 0.5, SAFFRON, EMBER, 0.0, 1.0)
    oval(11.5, 33.5, 6.0, 1.3, -0.4, PEARL, LAPIS, 0.1, 0.9)
    oval(11.5, 33.5, 1.8, 1.1, -0.4, SAFFRON, SAFFRON, 0.0, 0.0, 1.45)
    oval(22.0, 22.0, 3.0, 2.0, 1.1, EMBER, EMBER, 0.2, 0.0)
    for (bx, by) in ((21.5, 38.0), (23.2, 39.2), (20.4, 39.6), (22.6, 36.8)):
        oval(bx, by, 1.2, 1.0, 0, LAPIS, LAPIS, 0.0, 0.0)
    big = [(11, 11, 7.4), (32.5, 31.5, 6.5), (32, 10, 5.2), (11.5, 33.5, 6.6), (22, 22, 3.5), (22, 38.5, 3.0)]
    # dozens of small faint ones: red, gold and white smudges
    kinds = [(EMBER, EMBER), (EMBER, EMBER), (SAFFRON, EMBER), (SAFFRON, EMBER), (PEARL, LAPIS), (LAPIS, LAPIS), (PEARL, EMBER)]
    for (x, y) in scatter(7, 100, 1, 1, 43, 43, lambda x, y: min(math.hypot(x - a, y - b) - r for a, b, r in big) > 1.0, gap=2):
        s = rnd.uniform(0.75, 1.5)
        f, g = kinds[rnd.randrange(len(kinds))]
        oval(x + 0.5, y + 0.5, s * rnd.uniform(1.3, 1.9), s, rnd.uniform(0, 3.1), f, g, rnd.uniform(0.0, 0.4),
             0.6 * (f != g) * (s > 0.95))
    # foreground stars with four spikes
    for (x, y) in ((24, 5), (40, 40), (3, 22), (40, 18)):
        tile_star(c, T, x, y, PEARL, 0.0, arm=2, prio=1.9)
    frame(c)
    return encode(c.to_tiles())


SCENES = {
    "earthrise": earthrise, "plutoheart": plutoheart, "redspot": redspot, "marssunset": marssunset,
    "pillars": pillars, "rover": rover, "cliffs": cliffs, "deepfield": deepfield,
}
