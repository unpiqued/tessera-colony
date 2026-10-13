"""Sixteen original pictures for the Garden and Master packs — every one a different subject, drawn
with the same supersampled Canvas as art.py (a tile's colour family comes from the dominant object
under it, its tone from the shading).

Garden (40 x 44): hot-air balloon, lighthouse, toadstools, tulip bed, sailboat, honeycomb & bees,
owl, desert cacti.
Master (42 x 46), deliberately busy so that one colour sits in many separate places (stripes,
patches, bricks, windows, leaves, suckers): tiger, giraffe, autumn tree, castle, viaduct train,
city skyline, chameleon, octopus.
"""
import math
import random

import numpy as np

from art import Canvas, LAPIS, SAFFRON, FERN, EMBER, UMBER, PEARL, encode, leaf, smoothstep

GW, GH = 40, 44
MW, MH = 42, 46


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def ALL(c):
    return np.ones_like(c.X, bool)


def ellipse(c, cx, cy, rx, ry, ang=0.0):
    ca, sa = math.cos(ang), math.sin(ang)
    dx, dy = c.X - cx, c.Y - cy
    u = (dx * ca + dy * sa) / rx
    v = (-dx * sa + dy * ca) / ry
    return u * u + v * v <= 1.0


def rect(c, x0, y0, x1, y1):
    return (c.X >= x0) & (c.X < x1) & (c.Y >= y0) & (c.Y < y1)


def tube(c, pts, w0, w1):
    """A stroke along `pts` whose width goes from w0 to w1 (union of discs, densely sampled)."""
    m = np.zeros_like(c.X, bool)
    dense = []
    for (x0, y0), (x1, y1) in zip(pts[:-1], pts[1:]):
        n = max(2, int(math.hypot(x1 - x0, y1 - y0) * 3))
        for k in range(n):
            t = k / n
            dense.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t))
    dense.append(pts[-1])
    for i, (x, y) in enumerate(dense):
        w = w0 + (w1 - w0) * i / max(1, len(dense) - 1)
        m |= c.circle(x, y, w / 2)
    return m


def frame(c, fam=UMBER, shade=0.75):
    d = np.minimum.reduce([c.X, c.w - c.X, c.Y, c.h - c.Y])
    c.paint(d < 1, fam, shade, 1.2)


def sky(c, top=0.72, bottom=0.18, horizon=None):
    h = horizon or c.h
    c.paint(ALL(c), LAPIS, np.clip(top - (top - bottom) * c.Y / h, 0, 1))


def cloud(c, parts, shade_top=0.05):
    m = np.zeros_like(c.X, bool)
    for (a, b, r) in parts:
        m |= c.circle(a, b, r)
    base = max(b for _, b, _ in parts) + 0.6
    m &= c.Y <= base
    top = min(b - r for a, b, r in parts)
    c.paint(m, PEARL, np.clip(shade_top + 0.6 * (c.Y - top) / max(0.1, base - top), 0, 1), 1.1)


def smooth_noise(c, seed, freq=0.35):
    r = random.Random(seed)
    n = np.zeros_like(c.X)
    for _ in range(5):
        a, b, p = r.uniform(-1, 1), r.uniform(-1, 1), r.uniform(0, 6.28)
        n += np.sin((a * c.X + b * c.Y) * freq * r.uniform(0.6, 1.6) + p)
    return n / 5.0


def chevron(c, x, y, s=1.0):
    return c.line_mask([(x - 1.2 * s, y - 0.6 * s), (x, y), (x + 1.2 * s, y - 0.6 * s)], 0.35 * s)


# ---------------------------------------------------------------------------
# Garden
# ---------------------------------------------------------------------------

def hot_air_balloon():
    c = Canvas(GW, GH)
    X, Y = c.X, c.Y
    sky(c, 0.78, 0.12)
    cloud(c, [(6, 9, 2.2), (9, 8, 2.8), (12, 9.4, 2.0)])
    cloud(c, [(31, 27, 1.8), (34, 26, 2.4), (36.5, 27.4, 1.6)])
    # rolling hills with fields
    far = Y > 33.5 + 2.5 * np.sin(X * 0.23 + 1.0)
    c.paint(far, FERN, np.clip(0.18 + 0.08 * np.sin(X * 1.1), 0, 1))
    near = Y > 37.5 + 1.8 * np.sin(X * 0.31 + 3.2)
    rows = 0.5 + 0.5 * np.sin((X * 0.9 + Y * 2.2))
    c.paint(near, FERN, np.clip(0.45 + 0.35 * (rows > 0.6), 0, 1))
    field = near & (X > 22) & (X < 33) & (Y > 39.5)
    c.paint(field, SAFFRON, np.clip(0.35 + 0.3 * (rows > 0.5), 0, 1))
    for tx in (5.0, 9.0, 35.5):
        ty = 34.2 + 2.5 * math.sin(tx * 0.23 + 1.0)
        c.paint(rect(c, tx - 0.35, ty - 0.2, tx + 0.35, ty + 1.8), UMBER, 0.8, 1.3)
        c.paint(c.circle(tx, ty - 1.2, 1.5), FERN, 0.85, 1.2)
    # the envelope: a sphere with a tapering skirt, eight gores
    cx, cy, R = 20.0, 14.0, 10.6
    skirt = c.poly_mask([(cx - R * 0.9, cy + R * 0.42), (cx - 2.9, cy + R + 4.4), (cx + 2.9, cy + R + 4.4),
                         (cx + R * 0.9, cy + R * 0.42)])
    env = c.circle(cx, cy, R) | skirt
    hw = np.where(Y <= cy, np.sqrt(np.clip(R * R - (Y - cy) ** 2, 0.01, None)),
                  np.interp(Y, [cy, cy + R * 0.42, cy + R + 4.4], [R, R * 0.9, 2.9]))
    t = np.clip((X - cx) / np.maximum(hw, 0.1), -1, 1)
    gore = np.floor((np.arcsin(t) + math.pi / 2) / (math.pi / 8)).astype(int)
    shade = np.clip(0.18 + 0.55 * np.abs(t) ** 1.6 + 0.12 * (Y - cy) / R, 0, 1)
    c.paint(env & (gore % 2 == 0), EMBER, shade)
    c.paint(env & (gore % 2 == 1), SAFFRON, shade)
    band = env & (np.abs(Y - (cy + 4.2)) < 1.1)
    c.paint(band, LAPIS, np.clip(0.55 + 0.3 * np.abs(t), 0, 1), 1.2)
    c.paint(band & (np.abs((X - cx) % 3.0 - 1.5) < 0.55), PEARL, 0.1, 1.3)
    crown = env & (Y < cy - R + 2.4)
    c.paint(crown, UMBER, 0.55, 1.2)
    # ropes and basket
    for (x0, x1) in ((cx - 2.7, cx - 2.0), (cx + 2.7, cx + 2.0), (cx - 0.9, cx - 0.7), (cx + 0.9, cx + 0.7)):
        c.paint(c.line_mask([(x0, cy + R + 4.4), (x1, 30.4)], 0.3), UMBER, 0.95, 1.6)
    basket = rect(c, cx - 2.6, 30.2, cx + 2.6, 34.0)
    weave = 0.5 + 0.5 * np.sin(X * 3.1) * np.sin(Y * 3.1)
    c.paint(basket, UMBER, np.clip(0.35 + 0.35 * weave, 0, 1), 1.3)
    c.paint(rect(c, cx - 2.9, 30.0, cx + 2.9, 30.8), UMBER, 0.9, 1.4)
    # two birds
    for (bx, by) in ((33, 7), (35.5, 9.5)):
        c.paint(chevron(c, bx, by, 0.9), UMBER, 0.9, 1.6)
    frame(c)
    return encode(c.to_tiles())


def lighthouse():
    c = Canvas(GW, GH)
    X, Y = c.X, c.Y
    sky(c, 0.62, 0.08, horizon=30)
    cloud(c, [(29, 6, 1.8), (32, 5, 2.4), (35, 6.2, 1.7)])
    cloud(c, [(4, 16, 1.4), (6.5, 15.2, 1.9), (9, 16.3, 1.3)])
    # beams of light (behind the tower)
    for side in (-1, 1):
        beam = c.poly_mask([(20, 8.6), (20 + side * 22, 3.5), (20 + side * 22, 12.5)])
        c.paint(beam, SAFFRON, np.clip(0.05 + 0.03 * np.abs(X - 20), 0, 0.5), 0.9)
    # sea with wave crests
    sea = Y >= 29.5
    c.paint(sea, LAPIS, np.clip(0.5 + 0.4 * (Y - 29.5) / 14.5, 0, 1))
    crest = sea & (np.sin(X * 0.9 + np.sin(Y * 1.3) * 1.5 + Y * 1.9) > 0.9) & (Y > 30.5)
    c.paint(crest, PEARL, 0.25, 1.2)
    # rocks and grass
    rock = c.poly_mask([(6, 44), (8, 36), (12, 33.5), (17, 32.5), (26, 33), (30, 35.5), (33, 44)])
    n = smooth_noise(c, 5, 0.9)
    c.paint(rock, UMBER, np.clip(0.55 + 0.3 * n + 0.02 * (Y - 33), 0, 1))
    grass = rock & (Y < 35.2) & (Y > 32.3)
    c.paint(grass, FERN, np.clip(0.4 + 0.3 * n, 0, 1), 1.2)
    c.paint(c.poly_mask([(33, 44), (34.5, 40), (37.5, 39.2), (40, 41), (40, 44)]), UMBER, 0.7)
    # the tower: a tapering cylinder with red and white bands
    base_y, top_y = 34.5, 12.2
    half = np.interp(Y, [top_y, base_y], [2.6, 4.6])
    tower = (Y >= top_y) & (Y < base_y) & (np.abs(X - 20) <= half)
    tpos = (X - 20) / np.maximum(half, 0.1)
    cyl = np.clip(0.15 + 0.5 * np.abs(tpos + 0.25) ** 1.5, 0, 1)
    bands = np.floor((Y - top_y) / 4.4).astype(int) % 2
    c.paint(tower & (bands == 0), EMBER, cyl)
    c.paint(tower & (bands == 1), PEARL, np.clip(cyl * 0.7, 0, 1))
    for wy in (18.5, 27.0):
        c.paint(ellipse(c, 20, wy, 0.7, 1.1), UMBER, 0.9, 1.6)
    door = (np.abs(X - 20) < 1.2) & (Y > 31.3) & (Y < base_y) | c.circle(20, 31.3, 1.2)
    c.paint(door & (Y < base_y), UMBER, 0.85, 1.6)
    # gallery, lantern and roof
    c.paint(rect(c, 16.2, 11.0, 23.8, 12.4), UMBER, 0.85, 1.4)
    c.paint(rect(c, 17.8, 7.6, 22.2, 11.0), SAFFRON, np.clip(0.02 + 0.1 * np.abs(X - 20), 0, 1), 1.3)
    c.paint(rect(c, 19.75, 7.6, 20.25, 11.0), UMBER, 0.9, 1.5)
    roof = c.poly_mask([(17.2, 7.8), (22.8, 7.8), (20, 4.6)])
    c.paint(roof, EMBER, 0.8, 1.3)
    c.paint(c.circle(20, 4.4, 0.6), UMBER, 0.9, 1.5)
    # gulls
    for (bx, by) in ((8, 8), (11, 11), (30, 18)):
        c.paint(chevron(c, bx, by, 0.9), UMBER, 0.85, 1.6)
    frame(c)
    return encode(c.to_tiles())


def toadstools():
    c = Canvas(GW, GH)
    X, Y = c.X, c.Y
    sky(c, 0.35, 0.05, horizon=20)
    # forest canopy and trunks
    canopy = np.zeros_like(X, bool)
    r = random.Random(3)
    for _ in range(26):
        canopy |= c.circle(r.uniform(-2, 42), r.uniform(-2, 9), r.uniform(2.5, 4.5))
    n = smooth_noise(c, 9, 0.8)
    c.paint(canopy, FERN, np.clip(0.55 + 0.25 * n, 0, 1))
    for (tx, w) in ((4, 3.2), (13.5, 2.4), (25, 3.6), (35, 2.6)):
        trunk = (np.abs(X - tx) < w / 2) & (Y > 3) & (Y < 32)
        bark = 0.5 + 0.5 * np.sin(X * 4.0 + np.sin(Y * 0.8) * 2)
        c.paint(trunk, UMBER, np.clip(0.45 + 0.35 * bark, 0, 1))
    # far undergrowth and the forest floor
    under = Y > 25 + 1.5 * np.sin(X * 0.5)
    c.paint(under, FERN, np.clip(0.75 + 0.15 * n, 0, 1))
    floor = Y > 33 + 0.8 * np.sin(X * 0.35 + 1)
    c.paint(floor, UMBER, np.clip(0.3 + 0.25 * n + 0.01 * (Y - 33), 0, 1))
    moss = floor & (smooth_noise(c, 21, 1.4) > 0.35)
    c.paint(moss, FERN, 0.45, 1.1)
    # grass tufts
    for gx in range(1, 40, 3):
        base = 34.5 + (gx * 7) % 5 * 0.6
        for dx in (-0.7, 0.0, 0.7):
            c.paint(c.line_mask([(gx + dx, base + 1.5), (gx + dx * 2.2, base - 1.2)], 0.35), FERN, 0.3, 1.3)
    # three toadstools: red caps with white spots, white stems, gills
    for (cx, cy, rx, ry, stem_w, stem_bot, spots) in ((14, 24, 8.5, 5.5, 4.2, 37.5, 9), (29, 29.5, 5.8, 3.8, 2.8, 39.5, 6),
                                                         (35.5, 35.5, 3.2, 2.2, 1.6, 41.0, 3)):
        stem = rect(c, cx - stem_w / 2, cy, cx + stem_w / 2, stem_bot) | ellipse(c, cx, stem_bot, stem_w * 0.7, 0.8)
        c.paint(stem, PEARL, np.clip(0.1 + 0.35 * np.abs(X - cx) / stem_w, 0, 1), 1.2)
        ring = rect(c, cx - stem_w / 2 - 0.4, cy + (stem_bot - cy) * 0.35, cx + stem_w / 2 + 0.4, cy + (stem_bot - cy) * 0.35 + 0.8)
        c.paint(ring, PEARL, 0.35, 1.3)
        cap = ellipse(c, cx, cy, rx, ry) & (Y <= cy + 0.3)
        c.paint(cap, EMBER, np.clip(0.25 + 0.5 * ((Y - (cy - ry)) / ry) + 0.2 * np.abs(X - cx) / rx, 0, 1))
        gills = ellipse(c, cx, cy + 0.2, rx * 0.95, 1.0) & (Y > cy + 0.2)
        c.paint(gills, PEARL, 0.55, 1.2)
        rs = random.Random(int(cx * 10))
        for _ in range(spots):
            a = rs.uniform(math.pi * 1.05, math.pi * 1.95)
            rr = rs.uniform(0.3, 0.8)
            sx, sy = cx + math.cos(a) * rx * rr, cy + math.sin(a) * ry * rr
            c.paint(c.circle(sx, sy, rs.uniform(0.55, 1.0) * rx / 8) & cap, PEARL, 0.08, 1.6)
    # a few yellow flowers
    for (fx, fy) in ((4, 38), (8, 41), (22, 40.5), (38, 39)):
        for k in range(5):
            a = k * 2 * math.pi / 5
            c.paint(c.circle(fx + 0.8 * math.cos(a), fy + 0.8 * math.sin(a), 0.5), SAFFRON, 0.2, 1.4)
        c.paint(c.circle(fx, fy, 0.4), UMBER, 0.8, 1.5)
    frame(c)
    return encode(c.to_tiles())


def tulip_bed():
    c = Canvas(GW, GH)
    X, Y = c.X, c.Y
    sky(c, 0.7, 0.15, horizon=20)
    c.paint(c.circle(32, 7, 3.2), SAFFRON, np.clip(0.1 + 0.08 * np.hypot(X - 32, Y - 7), 0, 1), 1.2)
    cloud(c, [(7, 7, 2.0), (10, 6, 2.6), (13, 7.3, 1.8)])
    field = Y > 17 + 1.2 * np.sin(X * 0.3)
    c.paint(field, FERN, np.clip(0.15 + 0.4 * (Y - 17) / 20, 0, 1))
    soil = Y > 36.5 + 0.6 * np.sin(X * 0.5)
    furrow = 0.5 + 0.5 * np.sin(Y * 2.6 + np.sin(X * 0.4))
    c.paint(soil, UMBER, np.clip(0.35 + 0.35 * furrow, 0, 1))
    cols = [EMBER, SAFFRON, PEARL, EMBER, LAPIS, SAFFRON, EMBER]
    xs = [4.8, 10.2, 15.6, 21.0, 26.4, 31.8, 37.0]
    tops = [19.5, 16.5, 20.5, 15.5, 19.0, 17.0, 20.0]
    for i, (x, top, fam) in enumerate(zip(xs, tops, cols)):
        # stem and leaves
        c.paint(c.line_mask([(x, top + 4), (x + 0.4 * math.sin(i), 38)], 0.7), FERN, 0.8, 1.2)
        side = 1 if i % 2 == 0 else -1
        leaf(c, x, 36.5, x + side * 3.2, 27 + (i % 3), 2.4, bend=0.1 * side)
        # the cup: a round body with three pointed petals on top
        body = ellipse(c, x, top + 2.2, 2.3, 2.6)
        crown = c.poly_mask([(x - 2.3, top + 2.0), (x - 1.9, top - 0.9), (x - 0.8, top + 0.6), (x, top - 1.3),
                             (x + 0.8, top + 0.6), (x + 1.9, top - 0.9), (x + 2.3, top + 2.0)])
        cup = body | crown
        sh = np.clip(0.3 + 0.35 * np.abs(X - x) / 2.3 + 0.12 * (Y - top) / 4, 0, 1)
        if fam == PEARL:
            sh = sh * 0.6
        c.paint(cup, fam, sh, 1.1)
        c.paint(cup & (np.abs(X - x) < 0.25) & (Y > top + 0.4), fam, np.clip(sh + 0.3, 0, 1), 1.2)
    frame(c)
    return encode(c.to_tiles())


def sailboat():
    c = Canvas(GW, GH)
    X, Y = c.X, c.Y
    horizon = 25.0
    c.paint(ALL(c), LAPIS, np.clip(0.8 - 0.6 * Y / horizon, 0, 1))
    glow = (Y > 12) & (Y < horizon)
    c.paint(glow, SAFFRON, np.clip(0.75 - 0.6 * (Y - 12) / (horizon - 12), 0, 1))
    sun = c.circle(27, horizon, 5.0) & (Y < horizon)
    c.paint(sun, EMBER, np.clip(0.1 + 0.05 * np.hypot(X - 27, Y - horizon), 0, 1), 1.3)
    island = (Y < horizon) & (Y > horizon - 3.2 + 2.2 * ((X / 11.0) - 0.5) ** 2 * 4) & (X < 11)
    c.paint(island, FERN, 0.85, 1.2)
    sea = Y >= horizon
    rip = 0.5 + 0.5 * np.sin(Y * 3.0 + np.sin(X * 0.6) * 1.2)
    c.paint(sea, LAPIS, np.clip(0.45 + 0.3 * (Y - horizon) / 19 + 0.2 * (rip - 0.5), 0, 1))
    refl = sea & (np.abs(X - 27) < 3.8 - 0.1 * (Y - horizon)) & (rip > 0.6)
    c.paint(refl, SAFFRON, 0.3, 1.2)
    # boat
    hull = c.poly_mask([(7.5, 31.2), (26.5, 31.2), (23.2, 35.4), (10.6, 35.4)])
    c.paint(hull, UMBER, np.clip(0.55 + 0.08 * (Y - 31), 0, 1), 1.2)
    c.paint(hull & (Y < 32.1), PEARL, 0.3, 1.4)
    c.paint(c.line_mask([(17, 8.5), (17, 31.3)], 0.55), UMBER, 0.9, 1.6)
    main = c.poly_mask([(17.5, 9.5), (17.5, 29.6), (27.5, 29.6)])
    c.paint(main, PEARL, np.clip(0.05 + 0.04 * (X - 17.5) + 0.01 * (Y - 9), 0, 1), 1.2)
    jib = c.poly_mask([(16.5, 11.5), (16.5, 29.6), (8.5, 29.6)])
    c.paint(jib, EMBER, np.clip(0.3 + 0.04 * (16.5 - X), 0, 1), 1.2)
    c.paint(c.poly_mask([(17.3, 8.4), (17.3, 10.0), (20.0, 9.2)]), SAFFRON, 0.3, 1.5)
    # boom and a wake
    c.paint(c.line_mask([(17, 29.8), (27.5, 29.8)], 0.45), UMBER, 0.9, 1.5)
    wake = sea & (np.abs(Y - 36.2 - 0.05 * (X - 10)) < 0.35) & (X > 3) & (X < 24)
    c.paint(wake, PEARL, 0.35, 1.3)
    for (bx, by) in ((6, 6), (9, 8.5), (33, 9)):
        c.paint(chevron(c, bx, by, 0.9), UMBER, 0.9, 1.6)
    frame(c)
    return encode(c.to_tiles())


def honeycomb():
    c = Canvas(GW, GH)
    X, Y = c.X, c.Y
    # pointy-top hexagon grid
    s = 3.7
    q = (math.sqrt(3) / 3 * X - Y / 3) / s
    r_ = (2 / 3 * Y) / s
    cube_x, cube_z = q, r_
    cube_y = -cube_x - cube_z
    rx, ry, rz = np.round(cube_x), np.round(cube_y), np.round(cube_z)
    dx, dy, dz = np.abs(rx - cube_x), np.abs(ry - cube_y), np.abs(rz - cube_z)
    fix_x = (dx > dy) & (dx > dz)
    fix_y = ~fix_x & (dy > dz)
    rx = np.where(fix_x, -ry - rz, rx)
    ry = np.where(fix_y, -rx - rz, ry)
    rz = np.where(~fix_x & ~fix_y, -rx - ry, rz)
    hcx = s * math.sqrt(3) * (rx + rz / 2)
    hcy = s * 1.5 * rz
    d = np.maximum.reduce([np.abs(X - hcx) * 2 / math.sqrt(3), np.abs((X - hcx) / math.sqrt(3) + (Y - hcy)),
                           np.abs(-(X - hcx) / math.sqrt(3) + (Y - hcy))]) / s
    cell_id = (rx * 73856093 + rz * 19349663).astype(np.int64)
    kind = cell_id % 6
    wall = d > 0.84
    shade = np.clip(0.1 + 0.6 * d, 0, 1)
    c.paint(ALL(c), SAFFRON, shade)
    c.paint(~wall & (kind == 0), SAFFRON, np.clip(0.7 + 0.25 * d, 0, 1))
    c.paint(~wall & (kind == 1), UMBER, np.clip(0.45 + 0.3 * d, 0, 1))
    c.paint(wall, UMBER, 0.75, 1.15)
    # meadow at the bottom with blue flowers
    meadow = Y > 34.5 + 1.2 * np.sin(X * 0.45)
    c.paint(meadow, FERN, np.clip(0.3 + 0.3 * (0.5 + 0.5 * np.sin(X * 2.3 + Y)), 0, 1), 1.0)
    for (fx, fy) in ((4, 38), (10, 40.5), (16, 37.5), (25, 40), (31, 37.8), (36.5, 40.5)):
        for k in range(5):
            a = k * 2 * math.pi / 5 + fx
            c.paint(c.circle(fx + 0.9 * math.cos(a), fy + 0.9 * math.sin(a), 0.6), LAPIS, 0.25, 1.4)
        c.paint(c.circle(fx, fy, 0.45), SAFFRON, 0.1, 1.5)
    # four bees
    for (bx, by, ang, sc) in ((11, 10, 0.25, 1.35), (29, 15, -0.35, 1.2), (17, 26, 0.1, 1.3)):
        ca, sa = math.cos(ang), math.sin(ang)
        # wings first (pale, behind), then a round striped body and a dark head
        for side in (-1, 1):
            wx, wy = bx - 0.8 * sc * ca - side * 2.4 * sc * sa, by - 0.8 * sc * sa + side * 2.4 * sc * ca
            c.paint(ellipse(c, wx, wy, 2.2 * sc, 1.3 * sc, ang + side * 0.5), PEARL, 0.1, 2.0)
        body = ellipse(c, bx, by, 2.9 * sc, 2.0 * sc, ang)
        along = (X - bx) * ca + (Y - by) * sa
        stripes = (np.abs(along + 0.9 * sc) < 0.55 * sc) | (np.abs(along - 0.9 * sc) < 0.55 * sc)
        c.paint(body, SAFFRON, 0.02, 2.1)
        c.paint(body & stripes, UMBER, 0.95, 2.2)
        c.paint(c.circle(bx + 3.3 * sc * ca, by + 3.3 * sc * sa, 1.3 * sc), UMBER, 0.95, 2.3)
        c.paint(c.line_mask([(bx - 2.8 * sc * ca, by - 2.8 * sc * sa), (bx - 3.9 * sc * ca, by - 3.9 * sc * sa)], 0.5), UMBER, 0.95, 2.3)
    frame(c)
    return encode(c.to_tiles())


def owl():
    c = Canvas(GW, GH)
    X, Y = c.X, c.Y
    sky(c, 0.55, 0.1)
    r = random.Random(12)
    for (ox, oy) in ((3, 4), (37, 6), (2, 20), (38, 22)):
        for _ in range(7):
            lx, ly = ox + r.uniform(-4, 4), oy + r.uniform(-4, 4)
            a = r.uniform(0, math.pi)
            m = ellipse(c, lx, ly, 2.4, 1.1, a)
            c.paint(m, FERN, np.clip(0.3 + 0.5 * r.random(), 0, 1), 1.1)
    # branch
    br = tube(c, [(-1, 36.5), (12, 35.0), (26, 34.0), (41, 31.5)], 3.2, 2.2)
    c.paint(br, UMBER, np.clip(0.5 + 0.3 * np.sin(X * 1.7 + Y * 0.4), 0, 1), 1.2)
    twig = tube(c, [(30, 33.3), (34, 29), (35.5, 26.5)], 1.2, 0.6)
    c.paint(twig, UMBER, 0.6, 1.2)
    leaf(c, 35.5, 26.5, 38.8, 22.0, 2.6, bend=0.1)
    # the owl
    cx = 20.0
    body = ellipse(c, cx, 24.5, 8.6, 10.4)
    c.paint(body, UMBER, np.clip(0.45 + 0.3 * np.abs(X - cx) / 8.6, 0, 1))
    for side in (-1, 1):
        tuft = c.poly_mask([(cx + side * 3.5, 15.5), (cx + side * 7.8, 10.5), (cx + side * 7.2, 17.0)])
        c.paint(tuft, UMBER, 0.7, 1.1)
        wing = ellipse(c, cx + side * 7.0, 26.5, 2.8, 7.2, side * 0.18)
        c.paint(wing, UMBER, 0.8, 1.2)
        feathers = wing & (np.sin(Y * 2.2) > 0.6)
        c.paint(feathers, UMBER, 0.95, 1.3)
    belly = ellipse(c, cx, 28.0, 5.4, 6.6)
    c.paint(belly, PEARL, 0.25, 1.2)
    for yy in np.arange(23.5, 33.6, 2.0):
        for xx in np.arange(cx - 4 + (yy % 4) * 0.5, cx + 4.2, 2.1):
            c.paint(chevron(c, xx, yy, 0.55) & belly, UMBER, 0.6, 1.4)
    # face: two pale discs, yellow eyes, dark pupils, a beak
    for side in (-1, 1):
        ex = cx + side * 3.6
        c.paint(c.circle(ex, 18.8, 3.5), PEARL, np.clip(0.1 + 0.08 * np.hypot(X - ex, Y - 18.8), 0, 1), 1.3)
        c.paint(c.circle(ex, 18.8, 2.2), SAFFRON, 0.25, 1.5)
        c.paint(c.circle(ex, 18.8, 1.15), UMBER, 1.0, 1.7)
        c.paint(c.circle(ex - 0.45, 18.3, 0.35), PEARL, 0.0, 1.9)
    beak = c.poly_mask([(cx - 1.0, 20.5), (cx + 1.0, 20.5), (cx, 23.2)])
    c.paint(beak, SAFFRON, 0.6, 1.6)
    for side in (-1, 1):
        for k in (-1, 0, 1):
            c.paint(c.line_mask([(cx + side * 3 + k * 0.7, 34.2), (cx + side * 3 + k * 1.0, 35.6)], 0.45), SAFFRON, 0.55, 1.8)
    frame(c)
    return encode(c.to_tiles())


def desert_cacti():
    c = Canvas(GW, GH)
    X, Y = c.X, c.Y
    sky(c, 0.6, 0.02, horizon=24)
    # a mesa with red strata
    mesa = c.poly_mask([(15, 24), (18, 13.5), (33, 13.5), (36.5, 24)])
    strata = np.floor((Y - 13.5) / 2.0).astype(int) % 3
    c.paint(mesa, UMBER, np.clip(0.35 + 0.02 * (Y - 13.5), 0, 1))
    c.paint(mesa & (strata == 1), EMBER, np.clip(0.45 + 0.1 * np.sin(X), 0, 1), 1.1)
    butte = c.poly_mask([(1, 24), (2.5, 18.5), (8, 18.5), (10, 24)])
    c.paint(butte, UMBER, 0.55)
    # dunes
    for k, (base, amp, freq, ph, tone) in enumerate(((23.5, 1.0, 0.25, 0.5, 0.15), (29, 2.0, 0.18, 2.0, 0.3),
                                                      (35.5, 2.4, 0.22, 4.0, 0.45), (40.5, 1.4, 0.3, 1.0, 0.6))):
        dune = Y > base + amp * np.sin(X * freq + ph)
        c.paint(dune, SAFFRON, np.clip(tone + 0.1 * np.sin(X * 0.9 + Y), 0, 1))
    # saguaros: trunk with ribs and arms
    def saguaro(x, top, bottom, w, arms):
        m = rect(c, x - w / 2, top, x + w / 2, bottom) | c.circle(x, top, w / 2)
        for (side, ay, reach, up) in arms:
            ax = x + side * (w / 2 + reach)
            m |= c.line_mask([(x, ay), (ax, ay)], w * 0.72)
            m |= c.line_mask([(ax, ay), (ax, ay - up)], w * 0.72) | c.circle(ax, ay - up, w * 0.36)
        ribs = np.sin(X * 6.0) > 0.55
        c.paint(m, FERN, np.clip(0.35 + 0.2 * (X - x) / w, 0, 1))
        c.paint(m & ribs, FERN, 0.85, 1.1)
        return m
    saguaro(11, 15.5, 38.5, 3.2, [(-1, 27, 2.2, 5.5), (1, 24, 2.4, 6.5)])
    saguaro(29, 20.5, 37.5, 2.6, [(1, 29.5, 1.8, 4.5)])
    # prickly pear with fruit
    for (px, py, rx, ry, a) in ((20.5, 38.5, 2.4, 1.6, 0.2), (22.5, 35.5, 1.9, 1.3, -0.4), (18.8, 35.8, 1.7, 1.2, 0.5)):
        pad = ellipse(c, px, py, rx, ry, a)
        c.paint(pad, FERN, 0.55, 1.1)
    for (fx, fy) in ((22.9, 34.1), (18.1, 34.6), (21.7, 36.8), (11, 14.6), (29, 19.7)):
        c.paint(c.circle(fx, fy, 0.6), EMBER, 0.3, 1.6)
    for (rx_, ry_, s_) in ((4.5, 40, 1.6), (35, 39, 1.9), (26.5, 41.5, 1.1)):
        c.paint(ellipse(c, rx_, ry_, s_ * 1.3, s_ * 0.8), UMBER, 0.6, 1.2)
    for (fx, fy) in ((6.5, 36.5), (33, 35.5), (15.5, 41)):
        c.paint(c.circle(fx, fy, 0.55), PEARL, 0.1, 1.5)
    frame(c)
    return encode(c.to_tiles())


# ---------------------------------------------------------------------------
# Master
# ---------------------------------------------------------------------------

def tiger():
    c = Canvas(MW, MH)
    X, Y = c.X, c.Y
    sky(c, 0.5, 0.2)
    r = random.Random(4)
    for _ in range(60):
        lx, ly = r.uniform(-2, 44), r.uniform(-2, 48)
        c.paint(ellipse(c, lx, ly, r.uniform(2.0, 3.6), r.uniform(0.8, 1.4), r.uniform(0, math.pi)),
                FERN, np.clip(0.25 + 0.6 * r.random(), 0, 1), 1.0)
    cx, cy = 21.0, 25.0
    for side in (-1, 1):
        ear = c.circle(cx + side * 11.5, 11.5, 4.3)
        c.paint(ear, EMBER, 0.55, 1.1)
        c.paint(c.circle(cx + side * 11.5, 11.8, 2.4), PEARL, 0.3, 1.2)
        c.paint(ear & ~c.circle(cx + side * 11.5, 11.8, 3.3), UMBER, 0.85, 1.25)
    head = ellipse(c, cx, cy, 15.5, 14.5)
    c.paint(head, EMBER, np.clip(0.25 + 0.45 * np.hypot((X - cx) / 15.5, (Y - cy) / 14.5), 0, 1), 1.1)
    # white cheeks, muzzle, brows and chin
    for side in (-1, 1):
        c.paint(ellipse(c, cx + side * 8.5, cy + 6.5, 5.2, 4.2, side * 0.3), PEARL, 0.25, 1.2)
        c.paint(ellipse(c, cx + side * 5.8, 18.0, 3.0, 1.3, -side * 0.25), PEARL, 0.15, 1.3)
    c.paint(ellipse(c, cx, cy + 7.5, 6.0, 5.0), PEARL, 0.1, 1.3)
    c.paint(ellipse(c, cx, cy + 12.2, 4.0, 2.2), PEARL, 0.3, 1.3)
    # stripes: forehead, temples, cheeks and jaw
    stripes = []
    # the forehead "bars" and the curved stripes above each brow
    for k, (yy, half) in enumerate(((11.6, 2.4), (13.4, 1.9), (15.2, 1.3))):
        stripes.append(([(cx - half, yy + 0.3), (cx, yy), (cx + half, yy + 0.3)], 0.8))
    for side in (-1, 1):
        stripes.append(([(cx + side * 3.8, 11.2), (cx + side * 5.2, 12.8), (cx + side * 5.0, 14.6)], 0.9))
    for side in (-1, 1):
        for k, yy in enumerate((16.5, 20.0, 23.5, 27.0, 30.5)):
            x0 = cx + side * (15.5 - 0.9 * abs(yy - cy) * 0.35)
            stripes.append(([(x0, yy), (x0 - side * 3.2, yy + 0.8), (x0 - side * 5.0, yy + 0.1)], 1.2 if k % 2 else 0.9))
        stripes.append(([(cx + side * 9.5, 12.6), (cx + side * 7.5, 15.0), (cx + side * 8.2, 16.6)], 1.0))
        stripes.append(([(cx + side * 12.5, 33.0), (cx + side * 9.8, 34.5), (cx + side * 8.0, 34.0)], 1.0))
    for pts, w in stripes:
        c.paint(c.line_mask(pts, w) & head, UMBER, 0.9, 1.6)
    # eyes
    for side in (-1, 1):
        ex, ey = cx + side * 5.8, 21.0
        eye = ellipse(c, ex, ey, 2.4, 1.4, -side * 0.2)
        c.paint(ellipse(c, ex, ey, 3.0, 1.9, -side * 0.2), UMBER, 0.95, 1.7)
        c.paint(eye, FERN, 0.2, 1.8)
        c.paint(ellipse(c, ex, ey, 0.45, 1.25), UMBER, 1.0, 2.0)
        c.paint(c.circle(ex - 0.7, ey - 0.5, 0.3), PEARL, 0.0, 2.1)
    nose = c.poly_mask([(cx - 2.4, cy + 3.2), (cx + 2.4, cy + 3.2), (cx, cy + 6.2)])
    c.paint(nose, EMBER, 0.15, 1.8)
    c.paint(c.line_mask([(cx, cy + 6.0), (cx, cy + 7.8)], 0.45), UMBER, 0.9, 1.9)
    c.paint(c.line_mask([(cx - 3.2, cy + 9.0), (cx, cy + 7.8), (cx + 3.2, cy + 9.0)], 0.45), UMBER, 0.9, 1.9)
    for side in (-1, 1):
        for (wx, wy) in ((3.0, 7.2), (4.2, 8.0), (3.0, 8.8)):
            c.paint(c.circle(cx + side * wx, cy + wy, 0.28), UMBER, 0.8, 1.9)
    frame(c)
    return encode(c.to_tiles())


def giraffe():
    """A close-up: the giraffe's patched body and neck fill most of the frame."""
    c = Canvas(MW, MH)
    X, Y = c.X, c.Y
    sky(c, 0.6, 0.1, horizon=20)
    cloud(c, [(30, 5, 1.8), (33, 4, 2.4), (36, 5.3, 1.7)])
    grass = Y > 18 + 1.0 * np.sin(X * 0.3)
    blades = 0.5 + 0.5 * np.sin(X * 2.4 + np.sin(Y * 1.1) * 1.5)
    c.paint(grass, SAFFRON, np.clip(0.2 + 0.4 * blades + 0.01 * (Y - 18), 0, 1))
    tufts = grass & (np.sin(X * 1.3 + Y * 0.9) > 0.8) & (np.sin(Y * 2.1) > 0.2)
    c.paint(tufts, FERN, 0.5, 1.1)
    # a small acacia on the horizon
    c.paint(tube(c, [(36, 20), (36.4, 15), (35, 12)], 1.0, 0.6), UMBER, 0.8, 1.1)
    c.paint(ellipse(c, 35.5, 11.3, 5.0, 1.6), FERN, 0.6, 1.1)
    # body (running off the right edge), two legs, and a long neck up to the head at the top left
    body = ellipse(c, 33, 31, 14, 8.5)
    legs = (tube(c, [(26, 36), (25.5, 42), (25.2, 47)], 3.0, 2.2) | tube(c, [(33, 37), (33.5, 42), (33.8, 47)], 3.0, 2.2))
    neck = c.poly_mask([(16.5, 29), (27, 25), (15.5, 9.5), (10.5, 11.5)])
    head = ellipse(c, 10.0, 8.2, 5.4, 3.2, -0.5) | ellipse(c, 5.2, 11.3, 2.6, 2.1, -0.5)
    tail = tube(c, [(41.8, 27), (41.5, 34)], 0.8, 0.8)
    coat = body | legs | neck | head
    # irregular patches (Voronoi) separated by pale lines
    r = random.Random(7)
    seeds = []
    for gy in np.arange(-1, 50, 3.3):
        for gx in np.arange(-1, 46, 3.3):
            seeds.append((gx + r.uniform(-1.0, 1.0), gy + r.uniform(-1.0, 1.0)))
    d1 = np.full(X.shape, 99.0)
    d2 = np.full(X.shape, 99.0)
    for (sx, sy) in seeds:
        d = np.hypot(X - sx, Y - sy)
        d2 = np.minimum(d2, np.maximum(d1, d))
        d1 = np.minimum(d1, d)
    lines = (d2 - d1) < 0.6
    tone = 0.45 + 0.35 * d1 / 2.2
    c.paint(coat, EMBER, np.clip(tone, 0, 1))
    c.paint(coat & lines, PEARL, 0.25, 1.2)
    c.paint(legs & (Y > 44.5), UMBER, 0.9, 1.4)
    c.paint(tail, UMBER, 0.8, 1.3)
    c.paint(ellipse(c, 41.6, 35, 0.9, 1.6), UMBER, 0.95, 1.4)
    # mane along the back of the neck, face details, ossicones
    c.paint(c.line_mask([(27.5, 24.5), (16.2, 9.3)], 1.2), UMBER, 0.85, 1.4)
    c.paint(ellipse(c, 5.0, 11.6, 2.1, 1.6, -0.5), PEARL, 0.3, 1.5)
    c.paint(c.circle(4.4, 11.2, 0.35), UMBER, 0.95, 1.7)
    c.paint(c.circle(10.6, 7.1, 0.75), UMBER, 1.0, 1.8)
    c.paint(ellipse(c, 15.2, 5.6, 1.9, 0.8, 0.6), EMBER, 0.55, 1.6)
    for (ox, oy) in ((11.5, 3.9), (13.6, 4.4)):
        c.paint(c.line_mask([(ox, oy + 1.2), (ox + 0.5, oy - 1.5)], 0.6), UMBER, 0.8, 1.7)
        c.paint(c.circle(ox + 0.5, oy - 1.7, 0.6), UMBER, 1.0, 1.8)
    frame(c)
    return encode(c.to_tiles())


def autumn_tree():
    c = Canvas(MW, MH)
    X, Y = c.X, c.Y
    sky(c, 0.6, 0.1, horizon=34)
    c.paint(Y > 32 + 1.5 * np.sin(X * 0.25), FERN, 0.7)
    grass = Y > 36 + 0.8 * np.sin(X * 0.3 + 2)
    c.paint(grass, FERN, np.clip(0.3 + 0.2 * np.sin(X * 2.1 + Y * 0.7), 0, 1))
    # trunk and branches
    trunk = c.poly_mask([(17.5, 41), (24.5, 41), (22.5, 26), (19.5, 26)])
    c.paint(trunk, UMBER, np.clip(0.45 + 0.3 * np.sin(Y * 1.4 + X * 0.3) * 0.5 + 0.25 * (X - 21) / 3.5, 0, 1))
    r = random.Random(11)

    def branch(x, y, ang, length, w, depth):
        x1, y1 = x + math.cos(ang) * length, y + math.sin(ang) * length
        c.paint(tube(c, [(x, y), (x1, y1)], w, w * 0.65), UMBER, 0.7, 1.1)
        if depth > 0:
            for da in (-0.45, 0.4):
                branch(x1, y1, ang + da + r.uniform(-0.15, 0.15), length * 0.68, w * 0.62, depth - 1)
    for ang in (-2.2, -1.75, -1.3, -0.95):
        branch(21, 27, ang, 7.5, 2.0, 2)
    # a canopy of hundreds of separate leaves in four colours, sky showing between them
    fams = [EMBER, EMBER, SAFFRON, SAFFRON, FERN, UMBER]
    for _ in range(430):
        a = r.uniform(0, 2 * math.pi)
        rr = math.sqrt(r.random())
        lx, ly = 21 + math.cos(a) * rr * 18.0, 16 + math.sin(a) * rr * 12.5
        fam = fams[r.randrange(len(fams))]
        m = ellipse(c, lx, ly, r.uniform(0.9, 1.6), r.uniform(0.55, 0.9), r.uniform(0, math.pi))
        c.paint(m, fam, np.clip(r.uniform(0.15, 0.7), 0, 1), 1.3)
    # fallen leaves on the grass
    for _ in range(40):
        lx, ly = r.uniform(2, 40), r.uniform(38, 44.5)
        c.paint(ellipse(c, lx, ly, 0.9, 0.5, r.uniform(0, math.pi)), fams[r.randrange(4)], r.uniform(0.2, 0.6), 1.4)
    frame(c)
    return encode(c.to_tiles())


def castle():
    c = Canvas(MW, MH)
    X, Y = c.X, c.Y
    sky(c, 0.65, 0.12, horizon=30)
    cloud(c, [(6, 6, 1.8), (8.5, 5, 2.3), (11, 6.2, 1.6)])
    cloud(c, [(33, 4, 1.5), (35.5, 3.2, 2.0), (38, 4.4, 1.4)])
    c.paint(Y > 29 + 1.5 * np.sin(X * 0.3 + 1), FERN, 0.55)
    bank = Y > 36.5
    c.paint(bank, FERN, np.clip(0.3 + 0.2 * np.sin(X * 2.0), 0, 1))
    moat = Y > 40.5
    c.paint(moat, LAPIS, np.clip(0.5 + 0.3 * (0.5 + 0.5 * np.sin(Y * 3 + np.sin(X * 0.5) * 2)), 0, 1))

    def stone(m, stagger=0):
        """Brickwork: courses of two stone rows and a mortar row, with staggered vertical joints."""
        rowi = np.floor(Y).astype(int)
        course = rowi // 3
        mortar_row = (rowi % 3) == 2
        col = np.floor(X).astype(int) + stagger
        joint = ((col % 5) == (course % 2) * 2) & ~mortar_row
        blockshade = 0.08 + 0.3 * (((col // 5) * 5 + course * 3) % 4) / 3
        c.paint(m, PEARL, np.clip(blockshade, 0, 1))
        c.paint(m & (mortar_row | joint), UMBER, 0.35, 1.4)

    def merlons(x0, x1, top):
        w = 1.6
        teeth = ((X - x0) / w).astype(int) % 2 == 0
        return (X >= x0) & (X < x1) & (Y >= top - 1.6) & (Y < top) & teeth

    wall = rect(c, 6, 22, 36, 40.5) | merlons(6, 36, 22)
    keep = rect(c, 14.5, 12, 27.5, 40.5) | merlons(14.5, 27.5, 12)
    left = rect(c, 2.5, 15, 10.5, 40.5)
    right = rect(c, 31.5, 15, 39.5, 40.5)
    for m in (wall, keep):
        stone(m)
    for m, st in ((left, 1), (right, 3)):
        stone(m, st)
    # conical roofs with flags
    for (tx, top) in ((6.5, 15.0), (35.5, 15.0)):
        roof = c.poly_mask([(tx - 4.8, top + 0.3), (tx + 4.8, top + 0.3), (tx, top - 7.5)])
        c.paint(roof, EMBER, np.clip(0.35 + 0.1 * (X - tx), 0, 1), 1.2)
        c.paint(c.line_mask([(tx, top - 7.5), (tx, top - 10.5)], 0.35), UMBER, 0.9, 1.5)
        c.paint(c.poly_mask([(tx, top - 10.6), (tx + 2.6, top - 9.8), (tx, top - 9.0)]), SAFFRON, 0.3, 1.6)
    c.paint(c.line_mask([(21, 10.5), (21, 5.5)], 0.35), UMBER, 0.9, 1.5)
    c.paint(c.poly_mask([(21, 5.4), (24.2, 6.3), (21, 7.2)]), LAPIS, 0.35, 1.6)
    # windows (arched slits), banners, gate and drawbridge
    for (wx, wy) in ((6.5, 20), (6.5, 27), (35.5, 20), (35.5, 27), (18, 16.5), (24, 16.5), (18, 23), (24, 23)):
        c.paint(rect(c, wx - 0.6, wy, wx + 0.6, wy + 2.4) | c.circle(wx, wy, 0.6), UMBER, 0.95, 1.8)
    for bx in (16.2, 25.8):
        ban = c.poly_mask([(bx - 1.1, 26), (bx + 1.1, 26), (bx + 1.1, 31.5), (bx, 30.5), (bx - 1.1, 31.5)])
        c.paint(ban, LAPIS, 0.45, 1.8)
        c.paint(c.circle(bx, 28.0, 0.55) & ban, SAFFRON, 0.2, 1.9)
    gate = rect(c, 18, 33, 24, 40.5) | c.circle(21, 33, 3.0)
    c.paint(gate & (Y < 40.5), UMBER, 0.9, 1.8)
    grid = gate & (Y < 40.5) & ((((X - 18) % 1.5) < 0.35) | (((Y - 30) % 1.5) < 0.35))
    c.paint(grid, SAFFRON, 0.75, 1.9)
    bridge = c.poly_mask([(18, 40.5), (24, 40.5), (25.2, 45.5), (16.8, 45.5)])
    c.paint(bridge, UMBER, np.clip(0.4 + 0.3 * ((Y % 1.2) < 0.3), 0, 1), 1.7)
    frame(c)
    return encode(c.to_tiles())


def viaduct_train():
    c = Canvas(MW, MH)
    X, Y = c.X, c.Y
    sky(c, 0.62, 0.1, horizon=24)
    # mountains with snow
    mtn = Y > 16 + 5.5 * np.abs(((X + 4) / 13.0) % 2 - 1)
    c.paint(mtn, LAPIS, np.clip(0.75 - 0.02 * (Y - 12), 0, 1))
    snow = mtn & (Y < 18.8 + 5.5 * np.abs(((X + 4) / 13.0) % 2 - 1) - 3.2 + 0.4 * np.sin(X * 3))
    c.paint(snow, PEARL, 0.12, 1.1)
    # valley slopes and a river
    slope = Y > 24 + 0.12 * (X - 21) ** 2 * 0.05 + 2 * np.sin(X * 0.2)
    c.paint(slope, FERN, np.clip(0.35 + 0.25 * np.sin(X * 1.3 + Y * 0.8), 0, 1))
    river = (Y > 40) & (np.abs(X - 21 - 3 * np.sin(Y * 0.5)) < 4 + (Y - 40) * 0.8)
    c.paint(river, LAPIS, np.clip(0.4 + 0.25 * np.sin(Y * 3), 0, 1), 1.1)
    r = random.Random(5)
    for _ in range(14):
        tx, ty = r.choice([r.uniform(1, 11), r.uniform(31, 41)]), r.uniform(30, 43)
        pine = c.poly_mask([(tx - 1.4, ty + 1.2), (tx + 1.4, ty + 1.2), (tx, ty - 3.0)])
        c.paint(pine, FERN, 0.85, 1.2)
    # the viaduct: sandstone with round arches (you see the valley through them)
    deck_top, deck_bot = 22.0, 25.0
    struct = rect(c, 0, deck_top, MW, 42)
    arches = np.zeros_like(X, bool)
    for ax in np.arange(3.5, 42, 7.0):
        arches |= (c.circle(ax, 31.0, 2.7) | rect(c, ax - 2.7, 31.0, ax + 2.7, 42.0))
    piers = struct & ~arches & (Y >= deck_bot)
    deck = rect(c, 0, deck_top, MW, deck_bot)
    stone_rows = np.floor(Y / 1.5).astype(int)
    fx = ((X + (stone_rows % 2) * 1.2) / 2.4) % 1.0
    block = 0.2 + 0.35 * ((np.floor((X + (stone_rows % 2) * 1.2) / 2.4).astype(int) + stone_rows) % 3) / 2
    c.paint(piers | deck, SAFFRON, np.clip(block, 0, 1))
    c.paint((piers | deck) & ((fx < 0.12) | ((Y / 1.5) % 1.0 < 0.15)), UMBER, 0.45, 1.5)
    c.paint(rect(c, 0, deck_top - 0.6, MW, deck_top), UMBER, 0.9, 1.4)
    # the train: engine, tender and two carriages
    wheel_y = deck_top - 1.3
    engine = rect(c, 27, deck_top - 6.2, 38.5, deck_top - 1.2)
    boiler = ellipse(c, 33.5, deck_top - 4.0, 5.2, 2.2)
    c.paint(engine | boiler, EMBER, np.clip(0.35 + 0.1 * (Y - (deck_top - 6)), 0, 1), 1.3)
    c.paint(rect(c, 27, deck_top - 9.0, 31, deck_top - 5.8), EMBER, 0.6, 1.3)
    c.paint(rect(c, 27.8, deck_top - 8.2, 30.2, deck_top - 6.6), PEARL, 0.15, 1.5)
    c.paint(rect(c, 26.6, deck_top - 9.8, 31.4, deck_top - 8.9), UMBER, 0.9, 1.5)
    c.paint(rect(c, 35.5, deck_top - 9.0, 37.0, deck_top - 5.8), UMBER, 0.95, 1.5)
    c.paint(c.poly_mask([(38.5, deck_top - 1.2), (41.5, deck_top - 0.6), (38.5, deck_top - 3.0)]), UMBER, 0.8, 1.5)
    for k, (x0, x1, fam) in enumerate(((14.5, 25.5, LAPIS), (2.0, 13.0, FERN))):
        car = rect(c, x0, deck_top - 6.8, x1, deck_top - 1.2)
        c.paint(car, fam, 0.45, 1.3)
        c.paint(rect(c, x0 - 0.3, deck_top - 7.6, x1 + 0.3, deck_top - 6.8), UMBER, 0.85, 1.4)
        for wx in np.arange(x0 + 1.2, x1 - 1.0, 2.4):
            c.paint(rect(c, wx, deck_top - 5.8, wx + 1.4, deck_top - 3.8), PEARL, 0.15, 1.5)
    for wx in (4.5, 10.5, 17.0, 23.0, 29.5, 33.0, 36.5):
        c.paint(c.circle(wx, wheel_y, 1.3), UMBER, 0.95, 1.6)
        c.paint(c.circle(wx, wheel_y, 0.4), PEARL, 0.3, 1.7)
    # smoke puffs drifting back over the carriages
    for (sx, sy, sr) in ((36.3, 10.5, 1.8), (33.5, 8.2, 2.3), (29.5, 6.5, 2.7), (24.5, 5.2, 2.9), (19, 4.6, 2.6)):
        c.paint(c.circle(sx, sy, sr), PEARL, np.clip(0.1 + 0.05 * (36 - sx) / 3, 0, 0.6), 1.2)
    frame(c)
    return encode(c.to_tiles())


def city_skyline():
    """Dusk over a dense city. Every tower's face is a grid: floor slabs every third row and mullions
    every two or three columns split it into small panels, each with one lit, dark or curtained window
    (like the castle's brickwork, this puts each colour in many separate places)."""
    c = Canvas(MW, MH)
    X, Y = c.X, c.Y
    horizon = 42.0
    c.paint(ALL(c), LAPIS, np.clip(0.95 - 0.5 * Y / 14, 0, 1))
    c.paint((Y > 8) & (Y < horizon), EMBER, np.clip(0.75 - 0.5 * (Y - 8) / 8, 0, 1))
    c.paint((Y > 12) & (Y < horizon), SAFFRON, np.clip(0.55 - 0.4 * (Y - 12) / 6, 0, 1))
    r = random.Random(23)
    for _ in range(7):
        c.paint(c.circle(r.uniform(2, 40), r.uniform(1.5, 4.5), 0.3), PEARL, 0.0, 1.4)
    c.paint(c.circle(35, 4.5, 1.9) & ~c.circle(36.1, 3.8, 1.6), PEARL, 0.1, 1.3)   # crescent moon
    tx = np.floor(X).astype(int)
    ty = np.floor(Y).astype(int)
    # (x0, x1, top, facade family, slab family, bay width, floor phase)
    back = [(0, 5, 8, LAPIS, UMBER, 3, 0), (5, 10, 5, PEARL, UMBER, 2, 1), (10, 14, 10, EMBER, UMBER, 3, 2),
            (14, 19, 4, FERN, UMBER, 3, 0), (19, 23, 9, PEARL, LAPIS, 2, 1), (23, 28, 6, EMBER, UMBER, 3, 2),
            (28, 32, 3, LAPIS, PEARL, 2, 0), (32, 37, 9, PEARL, UMBER, 3, 1), (37, 42, 6, FERN, UMBER, 2, 2)]
    front = [(0, 6, 22, EMBER, UMBER, 3, 1), (6, 11, 18, PEARL, LAPIS, 2, 0), (11, 17, 25, LAPIS, UMBER, 3, 2),
             (17, 22, 20, UMBER, PEARL, 2, 1), (22, 27, 17, FERN, UMBER, 3, 0), (27, 32, 24, PEARL, EMBER, 2, 2),
             (32, 37, 19, EMBER, UMBER, 3, 1), (37, 42, 23, LAPIS, PEARL, 2, 0)]
    for layer, specs in enumerate((back, front)):
        pr = 1.0 + 0.2 * layer
        for i, (x0, x1, top, fam, slab, bay, ph) in enumerate(specs):
            b = rect(c, x0, top, x1, horizon)
            c.paint(b, fam, np.clip(0.45 + 0.1 * layer + 0.12 * (X - x0) / (x1 - x0), 0, 1), pr)
            # roof parapet, floor slabs every third row and mullions every `bay` columns
            floor_row = ((ty - top - ph) % 3) == 0
            mull = ((tx - x0) % bay) == 0
            grid = b & (floor_row | mull | (ty == top))
            c.paint(grid, slab, 0.85 if slab == UMBER else 0.3, pr + 0.05)
            # one window per panel: lit, curtained or dark
            win = b & ~floor_row & ~mull & (ty > top) & (((ty - top - ph) % 3) == 1) & (((tx - x0) % bay) == 1)
            k = (tx * 7 + ty * 13 + i * 5 + layer * 3) % 6
            c.paint(win & (k < 3), SAFFRON, 0.1, pr + 0.1)
            c.paint(win & (k == 3), EMBER if fam != EMBER else LAPIS, 0.2, pr + 0.1)
            c.paint(win & (k >= 4), UMBER if fam != UMBER and slab != UMBER else FERN, 0.95, pr + 0.1)
    # roof details: a spire, an antenna with a red light, a water tank
    c.paint(c.line_mask([(30.1, 3.2), (30.1, 0.6)], 0.4), PEARL, 0.4, 1.3)
    c.paint(c.line_mask([(16.5, 4), (16.5, 2.0)], 0.4), UMBER, 0.9, 1.4)
    c.paint(c.circle(16.5, 2.0, 0.5), EMBER, 0.2, 1.6)
    c.paint(rect(c, 24.5, 3.0, 26.5, 6.0), UMBER, 0.6, 1.4)
    # the river with window reflections
    water = Y >= horizon
    c.paint(water, LAPIS, np.clip(0.6 + 0.3 * (Y - horizon) / 3, 0, 1))
    c.paint(water & ((tx % 3) == 1) & ((ty % 2) == 0), SAFFRON, 0.4, 1.2)
    frame(c)
    return encode(c.to_tiles())


def chameleon():
    c = Canvas(MW, MH)
    X, Y = c.X, c.Y
    sky(c, 0.45, 0.08)
    r = random.Random(31)
    # hibiscus flowers and a few leaves, kept clear of the chameleon
    for (fx, fy, fr) in ((6, 7, 2.8), (36, 6, 2.4), (21, 4.5, 1.8)):
        for k in range(5):
            a = k * 2 * math.pi / 5 + fx
            c.paint(c.circle(fx + fr * 0.62 * math.cos(a), fy + fr * 0.62 * math.sin(a), fr * 0.55), EMBER, 0.3, 1.2)
        c.paint(c.circle(fx, fy, fr * 0.3), SAFFRON, 0.15, 1.3)
    for (lx, ly, a) in ((38, 42.5, 2.4), (33, 44.5, 0.2), (40, 12, 1.2), (22, 43.5, 0.1)):
        c.paint(ellipse(c, lx, ly, 3.2, 1.3, a), FERN, 0.8, 1.0)
    # branch
    c.paint(tube(c, [(-1, 36.5), (14, 34.0), (30, 33.0), (43, 30.5)], 3.0, 2.2), UMBER,
            np.clip(0.5 + 0.3 * np.sin(X * 1.9), 0, 1), 1.2)
    # body: a thick arched spine
    spine = [(9, 27.5), (13, 23.0), (19, 20.5), (25, 21.0), (29.5, 23.0)]
    body = tube(c, spine, 7.0, 9.0)
    # a tail that curls round below the branch
    tail_pts = [(9, 27.5), (7.0, 31.5)]
    for i in range(24):
        t = i / 23
        a = math.pi * 1.05 + t * 1.8 * math.pi
        rad = 5.2 - 3.4 * t
        tail_pts.append((8.2 + math.cos(a) * rad, 40.0 + math.sin(a) * rad * 0.9))
    tail = tube(c, tail_pts, 3.6, 1.0)
    head = c.poly_mask([(28.5, 16.0), (33.5, 18.0), (39.8, 24.2), (37.0, 28.8), (29.0, 29.2)])
    cham = body | tail | head
    c.paint(cham, FERN, np.clip(0.12 + 0.4 * (Y - 16) / 13, 0, 1), 1.3)
    # skin: wide diagonal yellow bands, blue spots, a pale belly line and a spiky crest
    bands = cham & ~head & (np.sin((X * 0.8 + Y * 0.45)) > 0.55)
    c.paint(bands, SAFFRON, 0.2, 1.4)
    spots = np.zeros_like(X, bool)
    for _ in range(22):
        sx, sy = r.uniform(11, 29), r.uniform(18, 27)
        spots |= c.circle(sx, sy, r.uniform(0.5, 0.8))
    c.paint(spots & body & ~bands, LAPIS, 0.35, 1.5)
    belly = tube(c, [(11, 29.0), (16, 25.6), (22, 25.1), (28, 26.4)], 1.0, 1.0) & body
    c.paint(belly, PEARL, 0.25, 1.5)
    for kx in np.arange(12, 29, 1.7):
        ky = 16.5 + 0.03 * (kx - 20) ** 2
        c.paint(c.poly_mask([(kx - 0.6, ky + 1.4), (kx, ky - 0.4), (kx + 0.6, ky + 1.4)]), FERN, 0.9, 1.45)
    c.paint(head & (Y < 19.5 + 0.2 * (X - 29)), FERN, 0.75, 1.4)
    # legs gripping the branch
    for (lx, ly) in ((12.5, 27), (16.5, 27.5), (24.5, 27.5), (28.5, 28)):
        c.paint(tube(c, [(lx, ly), (lx + 0.9, ly + 3.4), (lx + 0.3, ly + 6.2)], 1.8, 1.2), FERN, 0.55, 1.45)
        c.paint(c.circle(lx + 0.3, ly + 6.3, 0.8), FERN, 0.7, 1.5)
    # the eye turret and the mouth
    c.paint(c.circle(33.2, 22.6, 2.4), FERN, 0.05, 1.6)
    c.paint(c.circle(33.5, 22.6, 1.0), UMBER, 1.0, 1.8)
    c.paint(c.circle(33.1, 22.1, 0.35), PEARL, 0.0, 1.9)
    c.paint(c.line_mask([(33.5, 26.8), (38.5, 25.6)], 0.4), UMBER, 0.9, 1.7)
    frame(c)
    return encode(c.to_tiles())


def octopus():
    c = Canvas(MW, MH)
    X, Y = c.X, c.Y
    c.paint(ALL(c), LAPIS, np.clip(0.3 + 0.6 * Y / MH, 0, 1))
    rays = (np.sin(X * 0.5 + Y * 0.18) > 0.8) & (Y < 26)
    c.paint(rays, LAPIS, 0.12, 1.0)
    # sand, rocks, seaweed and pale coral
    sand = Y > 39 + 1.2 * np.sin(X * 0.35)
    c.paint(sand, SAFFRON, np.clip(0.2 + 0.25 * (0.5 + 0.5 * np.sin(X * 2.2 + Y * 1.1)), 0, 1))
    for (rx_, ry_, s_) in ((6, 41.5, 3.0), (35.5, 42, 3.4), (24, 43.5, 1.8)):
        c.paint(ellipse(c, rx_, ry_, s_, s_ * 0.6), UMBER, np.clip(0.5 + 0.3 * (Y - ry_) / s_, 0, 1), 1.1)
    for sx in (2.5, 11, 30, 39.5):
        pts = [(sx + 1.2 * math.sin(t * 1.3), 42 - t * 2.4) for t in range(9)]
        c.paint(c.line_mask(pts, 0.9), FERN, 0.55, 1.2)
    for (cx_, cy_) in ((16, 40), (32, 39)):
        for ang in (-1.2, -0.6, 0.0, 0.6):
            x1, y1 = cx_ + math.sin(ang) * 4.0, cy_ - math.cos(ang) * 4.0
            c.paint(c.line_mask([(cx_, cy_ + 1), (x1, y1)], 0.8), PEARL, 0.3, 1.2)
            c.paint(c.circle(x1, y1, 0.6), PEARL, 0.2, 1.3)
    # bubbles
    r = random.Random(8)
    for _ in range(16):
        bx, by, br = r.uniform(3, 39), r.uniform(2, 30), r.uniform(0.35, 0.8)
        c.paint(c.circle(bx, by, br), PEARL, 0.1, 1.4)
    # eight arms curling out from under the mantle, each with a row of pale suckers
    cx, cy = 21.0, 16.0
    for k in range(8):
        # fan the arms out across the lower half, the outer ones reaching sideways, tips curling
        base_a = math.pi * (-0.08 + 1.16 * k / 7)
        sgn = -1 if k < 4 else 1
        pts = []
        for i in range(24):
            t = i / 23
            a = base_a + sgn * (0.25 * t + 1.5 * max(0.0, t - 0.6) ** 1.5 * 2.2)
            rad = 5.5 + 16.0 * t
            pts.append((cx + math.cos(a) * rad * 1.1, cy + 5.0 + math.sin(a) * rad * 0.9))
        arm = tube(c, pts, 3.0, 0.8)
        c.paint(arm, EMBER, np.clip(0.35 + 0.25 * math.sin(k), 0, 1), 1.4)
        for i in range(3, 22, 2):
            (x0, y0), (x1, y1) = pts[i], pts[i + 1]
            nx, ny = -(y1 - y0), (x1 - x0)
            ln = math.hypot(nx, ny) or 1.0
            side = 1 if k < 4 else -1
            wid = (3.0 + (0.8 - 3.0) * i / 23) * 0.3
            c.paint(c.circle(x0 + side * nx / ln * wid, y0 + side * ny / ln * wid, max(0.3, wid * 0.8)) & arm,
                    PEARL, 0.25, 1.6)
    mantle = ellipse(c, cx, cy, 7.2, 8.6) & (Y < cy + 7.5)
    c.paint(mantle, EMBER, np.clip(0.2 + 0.45 * np.hypot((X - cx) / 7.2, (Y - cy + 3) / 8.6), 0, 1), 1.5)
    for (sx, sy) in ((18.5, 11), (23.5, 10.5), (21, 13.5), (17.5, 15), (24.5, 14.5)):
        c.paint(c.circle(sx, sy, 0.6) & mantle, EMBER, 0.85, 1.6)
    for side in (-1, 1):
        ex, ey = cx + side * 3.4, cy + 4.2
        c.paint(ellipse(c, ex, ey, 1.8, 1.4), PEARL, 0.15, 1.7)
        c.paint(ellipse(c, ex, ey, 1.2, 0.45), UMBER, 1.0, 1.9)
    frame(c)
    return encode(c.to_tiles())


SCENES = {
    "balloon": hot_air_balloon, "lighthouse": lighthouse, "toadstools": toadstools, "tulips": tulip_bed,
    "sailboat": sailboat, "honeycomb": honeycomb, "owl": owl, "desert": desert_cacti,
    "tiger": tiger, "giraffe": giraffe, "autumn": autumn_tree, "castle": castle,
    "viaduct": viaduct_train, "skyline": city_skyline, "chameleon": chameleon, "octopus": octopus,
}
