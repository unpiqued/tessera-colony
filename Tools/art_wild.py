"""Wild Wonders: eight natural wonders of the world, drawn with the same supersampled Canvas as art.py.

Gentle (big calm regions): northern lights, Grand Canyon, Victoria Falls, Antarctic iceberg.
Challenge (busier): an erupting volcano, a rainforest canopy with a toucan and a macaw.
Master (every colour in many small islands): a coral reef, a bamboo forest with a giant panda.
"""
import math
import random

import numpy as np

from art import Canvas, LAPIS, SAFFRON, FERN, EMBER, UMBER, PEARL, encode, smoothstep
from art_scenes import ALL, ellipse, rect, tube, frame, sky, cloud, smooth_noise


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def voronoi(c, seeds):
    """Distance to the nearest and second-nearest seed, and the index of the nearest seed."""
    d1 = np.full(c.X.shape, 1e9)
    d2 = np.full(c.X.shape, 1e9)
    idx = np.zeros(c.X.shape, int)
    for i, (sx, sy) in enumerate(seeds):
        d = np.hypot(c.X - sx, c.Y - sy)
        closer = d < d1
        d2 = np.where(closer, d1, np.minimum(d2, d))
        idx = np.where(closer, i, idx)
        d1 = np.where(closer, d, d1)
    return d1, d2, idx


def jitter_grid(seed, x0, x1, y0, y1, step, amp):
    r = random.Random(seed)
    return [(gx + r.uniform(-amp, amp), gy + r.uniform(-amp, amp))
            for gy in np.arange(y0, y1, step) for gx in np.arange(x0, x1, step)]


def blade(c, bx, by, tx, ty, width, shade, fam=FERN, prio=1.0, bend=0.0, rib=True, edge=False):
    """A lance-shaped leaf from base to tip: the two halves in neighbouring tones, a pale midrib, a dark edge."""
    L = math.hypot(tx - bx, ty - by)
    dx, dy = (tx - bx) / L, (ty - by) / L
    s = (c.X - bx) * dx + (c.Y - by) * dy
    u = s / L
    t = -(c.X - bx) * dy + (c.Y - by) * dx - bend * L * 4 * u * (1 - u)
    half = width / 2 * np.sqrt(np.clip(np.sin(np.pi * np.clip(u, 0, 1)), 0, 1))
    m = (u >= 0) & (u <= 1) & (np.abs(t) <= half)
    c.paint(m, fam, np.clip(shade + 0.14 * np.sign(t) + 0.5 * (edge & (np.abs(t) > half - 0.9)), 0, 1), prio)
    if rib:
        c.paint(m & (np.abs(t) < 0.3) & (u < 0.85), fam, max(0.0, shade - 0.4), prio + 0.05)
    return m


def fish(c, x, y, L, facing, fam, shade, tail_fam=None, bars=(), bar_fam=PEARL, bar_w=0.28, prio=1.5):
    """A small fish: oval body, fan tail, dark eye; `bars` are positions along the body (-1 tail .. 1 head)."""
    h = L * 0.62
    body = ellipse(c, x, y, L / 2, h / 2)
    bx = x - facing * L * 0.3
    tail = c.poly_mask([(bx, y), (bx - facing * L * 0.5, y - h * 0.5), (bx - facing * L * 0.5, y + h * 0.5)])
    c.paint(tail, fam if tail_fam is None else tail_fam, shade, prio)
    c.paint(body, fam, shade, prio)
    along = (c.X - x) * facing / (L / 2)
    for b in bars:
        c.paint(body & (np.abs(along - b) < bar_w), bar_fam, 0.1 if bar_fam == PEARL else 0.9, prio + 0.1)
    c.paint(c.circle(x + facing * L * 0.28, y - h * 0.08, 0.42), UMBER, 1.0, prio + 0.6)
    return body | tail


def penguin(c, x, feet, h, face, chick=False):
    """An emperor penguin standing on `feet`: pear-shaped, dark back, flippers and head, white front, gold
    neck patches (face -1/1 = profile to the left/right, 0 = facing us). A chick is grey with a white face."""
    body = ellipse(c, x, feet - h * 0.33, h * 0.24, h * 0.33) | \
        ellipse(c, x + face * h * 0.03, feet - h * 0.62, h * 0.17, h * 0.2)
    head = c.circle(x + face * h * 0.05, feet - h * 0.84, h * 0.12)
    if chick:
        c.paint(body | head, PEARL, 0.75, 1.6)
        c.paint(head, UMBER, 0.9, 1.65)
        c.paint(ellipse(c, x, feet - h * 0.8, h * 0.1, h * 0.07), PEARL, 0.0, 1.7)
        return
    c.paint(body | head, UMBER, 0.95, 1.6)
    front = ellipse(c, x + face * h * 0.1, feet - h * 0.33, h * (0.15 if face else 0.17), h * 0.33) | \
        ellipse(c, x + face * h * 0.1, feet - h * 0.6, h * (0.08 if face else 0.1), h * 0.15)
    c.paint(front & body, PEARL, 0.05, 1.7)
    for side in ((-1, 1) if face == 0 else (face,)):
        c.paint(ellipse(c, x + side * h * 0.1 + face * h * 0.03, feet - h * 0.72, h * 0.06, h * 0.08), SAFFRON, 0.15, 1.9)
    if face:
        c.paint(c.poly_mask([(x + face * h * 0.15, feet - h * 0.88), (x + face * h * 0.33, feet - h * 0.8),
                             (x + face * h * 0.15, feet - h * 0.8)]), EMBER, 0.45, 1.9)
    c.paint(ellipse(c, x, feet, h * 0.14, h * 0.05), UMBER, 0.9, 1.7)


# ---------------------------------------------------------------------------
# gentle
# ---------------------------------------------------------------------------

def aurora():
    """Northern lights: a green and a blue curtain over snowy spruces and a frozen lake."""
    c = Canvas(40, 44)
    X, Y = c.X, c.Y
    tx = np.floor(X).astype(int)
    horizon = 30.5
    # deep night sky with a few tile-sized stars
    c.paint(ALL(c), LAPIS, np.clip(1.0 - 0.35 * smoothstep(22, 31, Y), 0, 1))
    r = random.Random(17)
    for _ in range(22):
        sx, sy = r.randrange(2, 38), r.randrange(1, 28)
        c.paint(rect(c, sx, sy, sx + 1, sy + 1), PEARL, 0.0, 1.8)

    def curtain(Yv, hem, height, x0, x1, seed):
        """Folds two tiles wide rising from a bright hem, each to its own height, split apart near the top."""
        ray = tx // 3
        rnd = (np.sin(ray * 12.9898 + seed) * 43758.5453) % 1.0
        env = np.clip(np.minimum(X - x0, x1 - X) / 6.0, 0, 1)
        h = height * (0.4 + 0.6 * rnd) * env
        t = (hem - Yv) / np.maximum(h, 0.1)
        m = (Yv <= hem) & (t <= 1) & (h > 0.8) & ~(((tx % 3) == 2) & (t > 0.35))
        return m, np.clip(t, 0, 1)

    # a faint blue curtain far behind, then the main curtain: green low down, turning blue as the rays fade
    mb, tb = curtain(Y, 7.5 + 1.5 * np.sin(X * 0.3), 5.5, -2, 20, 3.0)
    c.paint(mb, LAPIS, np.clip(0.3 + 0.4 * tb, 0, 1), 1.1)
    hem_g = 17.0 + 4.5 * np.sin(X * 0.17 - 0.3)
    mg, tg = curtain(Y, hem_g, 14.0, -2, 44, 7.0)
    c.paint(mg & (tg < 0.72), FERN, np.clip(0.75 * tg * (tg > 0.12) + 0.25 * ((tx % 3) == 1) * (tg > 0.3), 0, 1), 1.15)
    c.paint(mg & (tg >= 0.72), LAPIS, np.clip(-0.5 + 1.2 * tg, 0, 1), 1.15)
    # far snowy hills, the frozen lake with a green sheen below them
    c.paint((Y > horizon - 2.6 - 1.6 * np.sin(X * 0.2 + 0.2) - 0.5 * np.sin(X * 0.7)) & (Y < horizon), PEARL, 0.6)
    lake = Y >= horizon
    c.paint(lake, LAPIS, np.clip(0.1 + 0.6 * (Y - horizon) / 6, 0, 1))
    rnd = (np.sin((tx // 3) * 12.9898 + 7.0) * 43758.5453) % 1.0
    c.paint(lake & (Y >= horizon + 1.0) & (Y < horizon + 2.5 + 2.5 * rnd), FERN,
            np.clip(0.0 + 0.6 * (Y - horizon - 1) / 4 + 0.25 * ((tx % 3) == 2), 0, 1), 1.1)
    c.paint(Y > 37.0 + 1.0 * np.sin(X * 0.3 + 1.0), PEARL, np.clip(0.05 + 0.3 * smoothstep(37, 44, Y), 0, 1))

    def spruce(x, base, height, width, tier_snow=True):
        """A triangle with a sawtooth edge of drooping tiers; snow on the moonlit side of each tier."""
        top = base - height
        k = np.floor((Y - top - 1.0) / 4.2)
        t = (Y - top - 1.0) / 4.2 - k
        hw = width * np.clip((Y - top) / height, 0, 1) * (0.62 + 0.38 * t)
        tree = (np.abs(X - x) <= hw + 0.3) & (Y >= top) & (Y < base)
        c.paint(tree | rect(c, x - 0.7, base - 1, x + 0.7, base + 1), UMBER, 0.95, 1.2)
        snow = tree & (x - X > hw - 1.6 + 1.2 * t) & (t < 0.8) & tier_snow | (tree & (Y < top + 2.2))
        c.paint(snow, PEARL, 0.1, 1.25)

    for (x, base, hgt, w, ts) in ((10.5, 40.0, 16, 3.4, False), (5.0, 42.0, 31, 5.5, True), (29.5, 39.5, 13, 3.0, False),
                                  (35.0, 42.0, 34, 6.0, True)):
        spruce(x, base, hgt, w, ts)
    frame(c)
    return encode(c.to_tiles())


def canyon():
    """Grand Canyon: rock spurs receding in depth, each striped with the same beds, a river far below."""
    c = Canvas(48, 36)
    X, Y = c.X, c.Y
    sky(c, 0.45, 0.02, horizon=8)
    cloud(c, [(21, 2.6, 1.2), (23.5, 1.9, 1.7), (26, 2.7, 1.1)])
    # the beds from the rim down: pale cap rock, red slope, a gold ledge, the thick red wall, dark base
    beds = [(SAFFRON, 0.02, 1.0), (EMBER, 0.05, 1.2), (SAFFRON, 0.45, 0.7), (EMBER, 0.55, 2.0), (UMBER, 0.1, 99)]
    bounds = np.cumsum([b[2] for b in beds])

    def rock(poly, top, scale, near, n_beds=5):
        """A spur of rock: beds scaled by nearness, deeper tones up close; far spurs lose the gold ledge."""
        m = c.poly_mask(poly)
        k = np.clip(np.searchsorted(bounds, (Y - top) / scale, side='right'), 0, n_beds - 1)
        for i, (fam, sh, _) in enumerate(beds[:n_beds]):
            fam = EMBER if (i == 2 and near < 0.3) else fam
            c.paint(m & (k == i), fam, np.clip(sh + 0.35 * near + 0.05 * np.sin(X * 0.9) + 0.03 * (Y - top) * (i == 4), 0, 1))

    # inner gorge with the green river winding through it
    c.paint(c.poly_mask([(8, 36), (19, 20), (31, 19), (42, 36)]), UMBER, 0.85)
    river = tube(c, [(29, 19.5), (26.5, 22.5), (23, 25), (25.5, 28.5), (22.5, 32), (20, 37)], 1.2, 3.6)
    c.paint(river, LAPIS, np.clip(0.25 + 0.25 * np.sin(Y * 1.3 + X * 0.5), 0, 1), 1.1)
    # hazy far rim with a mesa and a butte, then spurs alternating from each side, nearer and deeper-toned
    rock([(0, 7.2), (48, 6.6), (48, 16), (0, 16)], 6.6, 1.2, 0.0, 2)
    rock([(5, 7.2), (6.5, 4.4), (15.5, 4.4), (17, 7.2)], 4.4, 1.2, 0.0, 2)
    rock([(36, 6.8), (37.2, 2.6), (40.8, 2.6), (42, 6.8)], 2.6, 1.2, 0.0, 2)
    rock([(48, 9.5), (33, 9.5), (29, 12), (24.5, 17.5), (48, 19)], 9.5, 1.1, 0.1)
    rock([(0, 11), (14, 11), (18, 13.5), (26, 20.5), (0, 22)], 11.0, 1.3, 0.2)
    rock([(27, 21.5), (28.5, 16.5), (30, 14.5), (34, 14.5), (35.5, 16.5), (37, 21.5)], 14.5, 1.1, 0.25)
    rock([(48, 16.5), (40, 16.5), (36.5, 20), (31, 27), (48, 29)], 16.5, 1.6, 0.35)
    rock([(0, 18), (9, 18), (13, 21), (19.5, 30), (21, 36), (0, 36)], 18.0, 2.1, 0.5)
    rock([(48, 25.5), (40, 25.5), (35, 30.5), (32.5, 36), (48, 36)], 25.5, 2.4, 0.6)
    # a few junipers on the nearest rims
    for (jx, jy) in ((3, 17.4), (6.5, 17.6), (44, 25.0), (41.5, 25.2)):
        c.paint(ellipse(c, jx, jy, 1.4, 1.0), FERN, 0.75, 1.3)
    frame(c)
    return encode(c.to_tiles())


def victoria_falls():
    """Victoria Falls seen across its gorge: a white curtain receding to the right, spray, a rainbow, rainforest."""
    c = Canvas(40, 46)
    X, Y = c.X, c.Y
    lip = 9.0 + 0.2 * X            # top edge of the falls
    foot = 35.0 - 0.2 * X          # where the water drops into the spray
    sky(c, 0.5, 0.05, horizon=16)
    n = smooth_noise(c, 4, 0.9)
    # spray rising high above the lip ("the smoke that thunders")
    cloud(c, [(6, 5.0, 2.2), (9, 3.4, 2.8), (12, 5.2, 2.0)])
    cloud(c, [(26, 8.0, 1.8), (28.5, 6.6, 2.4), (31, 8.2, 1.7)])
    # far rim: rainforest crowns above the lip, the river sliding over it
    c.paint((Y > lip - 3.8 + 1.2 * np.abs(np.sin(X * 0.55)) + 0.5 * np.sin(X * 1.7)) & (Y < lip), FERN,
            np.clip(0.6 + 0.3 * n, 0, 1))
    c.paint((Y >= lip - 0.9) & (Y < lip + 0.4), LAPIS, 0.3, 1.1)
    # the curtain: white water in wavy streaks, some tinted blue, with two dark rock buttresses
    wx = X + 0.6 * np.sin(Y * 0.5 + X * 0.3)
    streak = (wx % 2.6) / 2.6
    fall = (Y >= lip + 0.4) & (Y < foot + 3)
    c.paint(fall, PEARL, np.clip(0.05 + 0.6 * (streak > 0.55) + 0.2 * np.clip((Y - lip) / 20, 0, 1), 0, 1))
    c.paint(fall & ((wx % 7.8) < 1.0) & (Y < lip + 12), LAPIS, 0.05, 1.05)
    for (x0, w, ln) in ((12.0, 2.4, 10.0), (28.5, 1.8, 7.0)):
        d = Y - lip
        rock = (np.abs(X - x0 - 0.1 * d) < w * (1.0 - d / ln) + 0.4 * np.sin(Y * 2.3 + x0)) & fall & (d < ln)
        c.paint(rock, UMBER, np.clip(0.45 + 0.4 * (X > x0 + 0.1 * d), 0, 1), 1.1)
    # the dark river in the gorge and the spray billowing up along the foot of the falls
    c.paint(Y >= foot + 3, LAPIS, 0.95)
    spray = np.zeros_like(X, bool)
    for k, sx in enumerate(np.arange(-1, 43, 4.0)):
        spray |= c.circle(sx, 35.0 - 0.2 * sx - 0.8 - 1.4 * (k % 2), 3.4 + 0.8 * (k % 3))
    c.paint(spray, PEARL, np.clip(0.0 + 0.04 * (Y - foot + 4), 0, 0.3), 1.05)
    # a rainbow arching through the spray
    rr = np.hypot(X - 17, Y - 46)
    for k, fam in enumerate((EMBER, SAFFRON, FERN, LAPIS)):
        band = (rr < 22 - 1.15 * k) & (rr >= 22 - 1.15 * (k + 1))
        c.paint(band, fam, 0.3 if fam in (EMBER, LAPIS) else 0.15, 1.3)
    # the near rim: rainforest crowns, thicker to the right where the gorge swings towards us
    near = (Y > 43.5) | ((Y > 41) & (X > 20)) | ((Y > 37) & (X > 33))
    for (tx, ty, tr) in ((1, 42, 4.0), (7, 41.5, 3.6), (13, 42.5, 3.4), (19, 40.8, 3.8), (25.5, 39.2, 4.0),
                         (31.5, 36.5, 4.4), (37.5, 34.0, 4.6), (35, 40, 4.2), (41, 38.5, 3.5)):
        near |= c.circle(tx, ty, tr)
    c.paint(near, FERN, np.clip(0.35 + 0.35 * n + 0.02 * (Y - 34), 0, 1), 1.1)
    frame(c)
    return encode(c.to_tiles())


def iceberg():
    """An Antarctic iceberg, its hidden bulk below the waterline, emperor penguins on a floe and under water."""
    c = Canvas(42, 42)
    X, Y = c.X, c.Y
    sea = 17.0
    c.paint(ALL(c), LAPIS, np.clip(0.4 - 0.3 * Y / sea, 0, 1))
    c.paint((Y > sea - 1.1) & (Y < sea), PEARL, 0.4, 1.1)                  # far ice shelf
    c.paint(Y >= sea, LAPIS, np.clip(0.65 + 0.45 * (Y - sea) / 14, 0, 1))
    c.paint((Y >= sea) & (Y < sea + 0.9), LAPIS, 0.4, 1.05)
    # above water: a jagged berg, sunlit faces white, shadowed faces grey
    c.paint(c.poly_mask([(2.5, 17.2), (5, 12), (8, 9), (10.5, 10.5), (14.5, 1.8), (17.5, 5.5), (20.5, 4.5),
                         (23.5, 6.5), (26, 11.5), (28, 17.2)]), PEARL, 0.0, 1.2)
    for pts, sh in (([(14.5, 1.8), (17.5, 5.5), (17, 10), (16, 17.2), (13, 17.2), (15.3, 9)], 0.65),
                    ([(20.5, 4.5), (23.5, 6.5), (26, 11.5), (28, 17.2), (22, 17.2), (22, 10)], 0.7),
                    ([(17.5, 5.5), (20.5, 4.5), (22, 10), (22, 17.2), (16, 17.2), (17, 10)], 0.35),
                    ([(8, 9), (10.5, 10.5), (9.5, 17.2), (7.5, 17.2), (9, 12)], 0.6)):
        c.paint(c.poly_mask(pts), PEARL, sh, 1.25)
    # below water: the far bigger hidden bulk, cut into facets, white near the surface, pale blue deeper
    rim = [(2.5, 17), (1, 23), (2.5, 30), (7.5, 35.5), (15.5, 38.5), (24.5, 37), (31, 31), (32.5, 24), (28.5, 17)]
    ctr = (16, 26)
    depth = np.clip((Y - sea) / 20, 0, 1)
    for i in range(len(rim)):
        face = c.poly_mask([ctr, rim[i], rim[(i + 1) % len(rim)]])
        if i in (0, 7):
            c.paint(face, PEARL, 0.25 if i == 0 else 0.5, 1.15)
        else:
            c.paint(face, LAPIS, np.clip(0.0 + 0.2 * (i % 2) + 0.35 * depth, 0, 1), 1.15)
    # the floe with a pair of emperors and their chick
    c.paint(c.poly_mask([(29, 17.4), (30.5, 15.6), (41.5, 15.4), (42, 17.4), (41, 19), (30, 19.2)]), PEARL,
            np.clip(0.05 + 0.4 * (Y > 17.3), 0, 1), 1.3)
    penguin(c, 31.8, 16.0, 10.5, 1)
    penguin(c, 38.3, 16.0, 11.0, 0)
    penguin(c, 35.0, 16.6, 4.8, 0, chick=True)
    # two more flying through the water, trailing bubbles
    for (px, py, d) in ((37, 26.5, -1), (37.5, 34.5, 1)):
        c.paint(ellipse(c, px, py, 3.2, 1.2, 0.3 * d), UMBER, 0.95, 1.6)
        c.paint(ellipse(c, px + 0.2 * d, py + 0.55, 2.4, 0.65, 0.3 * d), PEARL, 0.1, 1.7)
        c.paint(c.circle(px + 3.0 * d, py + 0.9 * d, 0.9), UMBER, 0.95, 1.65)
        for k in range(3):
            c.paint(c.circle(px - d * (4.4 + 1.6 * k), py - 1.0 * d - 0.9 * k, 0.55), PEARL, 0.05, 1.7)
    frame(c)
    return encode(c.to_tiles())


# ---------------------------------------------------------------------------
# challenge
# ---------------------------------------------------------------------------

def volcano():
    """An erupting cinder cone at dusk: lava rivers, an ash plume, flying bombs, a cooling lava field."""
    c = Canvas(40, 46)
    X, Y = c.X, c.Y
    # dusk: deep blue above, an orange glow low on the horizon behind the cone
    c.paint(ALL(c), LAPIS, np.clip(1.0 - 0.3 * Y / 28, 0, 1))
    c.paint(Y > 27.5 + 1.0 * np.sin(X * 0.5 + 1), EMBER, np.clip(0.3 - 0.05 * (Y - 27), 0, 1))
    # ash plume: billows rising from the crater and bending away to the right, lit red from below
    r = random.Random(21)
    plume = np.zeros_like(X, bool)
    for k in range(16):
        t = k / 15
        px, py = 20 + 9 * t ** 2 + 1.5 * math.sin(k * 1.9), 14.5 - 14 * t + r.uniform(-0.5, 0.5)
        plume |= c.circle(px, py, 3.0 + 5.0 * t)
    n = smooth_noise(c, 6, 0.7)
    c.paint(plume, PEARL, np.clip(0.6 + 0.4 * n + 0.02 * (X - 20), 0, 1), 1.05)
    c.paint(plume & (n < -0.2), UMBER, np.clip(0.1 + 0.3 * (-n), 0, 1), 1.05)
    # the cone with dark gullies
    cone = c.poly_mask([(-1, 38), (5, 32), (15.5, 16), (24.5, 16), (35, 31), (41, 36), (41, 40), (-1, 40)])
    gully = np.sin(np.arctan2(X - 20, Y - 10) * 22) > 0.35
    c.paint(cone, UMBER, np.clip(0.75 + 0.25 * gully - 0.1 * (X < 20), 0, 1))
    c.paint(ellipse(c, 20, 16.2, 4.6, 1.2), EMBER, 0.2, 1.3)
    # lava fountain and flying bombs
    for a in np.linspace(-0.55, 0.55, 5):
        c.paint(c.line_mask([(20, 16), (20 + 6 * math.sin(a), 16 - 6 * math.cos(a))], 1.0), SAFFRON, 0.15, 1.3)
    for (bx, by, vx) in ((11, 8, -1), (29, 9.5, 1), (7.5, 14, -1), (33, 5.5, 1), (15, 4, -1), (25.5, 3.5, 1)):
        c.paint(c.line_mask([(bx, by), (bx - vx * 1.6, by + 1.4)], 0.6), EMBER, 0.4, 1.5)
        c.paint(c.circle(bx, by, 0.85), SAFFRON, 0.1, 1.7)
    # lava rivers winding down the flanks, a bright core in each
    for pts, w in (([(17, 17), (15, 22), (16, 27), (12.5, 32), (10, 38.5)], 2.6),
                   ([(23, 17), (25, 22), (23.5, 28), (27, 33), (28, 39)], 2.8),
                   ([(21, 17.5), (20, 23), (18.5, 28)], 1.8)):
        c.paint(tube(c, pts, w * 0.7, w), EMBER, 0.35, 1.4)
        c.paint(tube(c, pts, w * 0.25, w * 0.35), SAFFRON, 0.2, 1.5)
    # the cooling lava field: dark crusted slabs split by glowing cracks
    field = Y > 37.5 + 0.8 * np.sin(X * 0.4)
    d1, d2, idx = voronoi(c, jitter_grid(12, 0, 42, 36, 48, 3.2, 1.1))
    crack = (d2 - d1) < 0.55
    c.paint(field, UMBER, np.clip(0.7 + 0.25 * np.sin(idx * 1.7), 0, 1))
    c.paint(field & crack, EMBER, np.clip(0.25 + 0.03 * (Y - 38), 0, 1), 1.2)
    c.paint(field & crack & (np.sin(idx * 3.1) > 0.5), SAFFRON, 0.2, 1.25)
    frame(c)
    return encode(c.to_tiles())


def rainforest():
    """A rainforest canopy: leaves of every shape, hanging vines, a toucan and a scarlet macaw on branches."""
    c = Canvas(42, 46)
    X, Y = c.X, c.Y
    # sky glimpsed through the canopy above, deep shadow below
    c.paint(ALL(c), LAPIS, np.clip(0.2 + 0.4 * Y / 24, 0, 1))
    c.paint(Y > 25 + 2 * np.sin(X * 0.3), UMBER, 0.95)
    # back layer: fans of big dark-edged leaves reaching in from every side
    fans = [(-3, 34, (-0.8, -0.2, 0.35), 16), (45, 46, (-2.9, -2.35, -1.85), 16), (45, 20, (3.4, 2.9, 2.5), 15),
            (20, 50, (-2.0, -1.45, -0.95), 14), (12, -4, (0.6, 1.2, 1.8), 15), (34, -4, (1.4, 2.0, 2.6), 13)]
    for i, (fx, fy, angs, ln) in enumerate(fans):
        for j, a in enumerate(angs):
            blade(c, fx, fy, fx + ln * math.cos(a), fy + ln * math.sin(a), ln * 0.36, 0.45 + 0.12 * ((i + j) % 3),
                  bend=0.08 * (1 if j % 2 else -1), edge=True)
    # hanging lianas with little leaves
    for vx in (4.5, 20.5, 38.5):
        pts = [(vx + 1.0 * math.sin(k * 0.8), k * 2.5 - 1) for k in range(16)]
        c.paint(c.line_mask(pts, 1.0), UMBER, 0.4, 1.3)
        for k in range(2, 15, 3):
            s = 1 if k % 2 else -1
            blade(c, pts[k][0], pts[k][1], pts[k][0] + s * 2.6, pts[k][1] + 1.4, 1.6, 0.15, prio=1.35, rib=False)
    # front layer: a split monstera, a torn banana leaf, palm fronds and heart leaves
    mon = ellipse(c, 8.5, 38.5, 9.0, 7.5, -0.3)
    c.paint(mon, FERN, np.clip(0.25 + 0.2 * (X - 8.5 > (Y - 38.5) * 0.3), 0, 1), 1.2)
    for a in np.linspace(-2.7, 0.3, 6):
        cut = c.line_mask([(8.5 + 3.4 * math.cos(a), 38.5 + 3.0 * math.sin(a)), (8.5 + 10 * math.cos(a), 38.5 + 8.5 * math.sin(a))], 1.3)
        c.paint(cut & mon, UMBER, 0.95, 1.4)
    c.paint(c.line_mask([(8.5, 38.5), (0, 46)], 0.9) & mon, FERN, 0.05, 1.25)
    banana = blade(c, 43.5, 10, 26.5, 1.5, 9.0, 0.3, prio=1.15, bend=0.1)
    for k in range(4):
        tear = c.line_mask([(40 - 3.6 * k, 1 + 1.7 * k), (37.5 - 3.6 * k, -2 + 1.7 * k)], 0.8)
        c.paint(tear & banana, LAPIS, 0.3, 1.2)
    for (hx, hy, sz) in ((30.5, 21, 1.35), (38.5, 38, 1.0), (19.5, 35.5, 1.45)):
        heart = c.circle(hx - 1.6 * sz, hy, 2.8 * sz) | c.circle(hx + 1.6 * sz, hy, 2.8 * sz) | \
            c.poly_mask([(hx - 4.2 * sz, hy + 1.0), (hx + 4.2 * sz, hy + 1.0), (hx, hy + 6.5 * sz)])
        c.paint(heart, FERN, np.clip(0.2 + 0.2 * (X > hx), 0, 1), 1.15)
        c.paint(heart & (np.abs(X - hx) < 0.35), FERN, 0.0, 1.2)
    for k in range(6):
        a = 0.35 + 0.22 * k
        blade(c, -1 + 1.4 * k, -1 + 0.3 * k, -1 + 1.4 * k + 6 * math.cos(a), 5 + 6 * math.sin(a) * 0.8, 2.0,
              0.35 + 0.1 * (k % 2), prio=1.15, rib=False)
    # branches
    c.paint(tube(c, [(-1, 21.5), (10, 23.0), (19, 23.5)], 2.8, 1.8), UMBER, np.clip(0.55 + 0.3 * np.sin(X * 1.5), 0, 1), 1.3)
    c.paint(tube(c, [(43, 30.5), (33, 31.5), (22, 34.5)], 2.8, 1.8), UMBER, np.clip(0.55 + 0.3 * np.sin(X * 1.5), 0, 1), 1.3)
    # the toucan: black body and tail, white bib, blue eye, huge gold bill with a red tip
    c.paint(ellipse(c, 11, 16.5, 3.1, 5.2, 0.12) | tube(c, [(10.5, 20.5), (9.8, 27)], 2.8, 2.0) | c.circle(12.4, 11.2, 2.5),
            UMBER, 0.95, 1.6)
    c.paint(ellipse(c, 13.0, 14.2, 1.9, 1.8), PEARL, 0.05, 1.7)
    c.paint(c.circle(13.2, 10.6, 0.75), LAPIS, 0.1, 1.9)
    bill = c.poly_mask([(14.2, 9.2), (17.5, 8.7), (21, 9.6), (22.8, 11.3), (19.5, 11.6), (14.4, 12.7)])
    c.paint(bill, SAFFRON, np.clip(0.2 + 0.2 * (Y - 9) / 3, 0, 1), 1.8)
    c.paint(bill & (X > 19.8), EMBER, 0.35, 1.85)
    # the scarlet macaw: red body and head, white face, gold and blue wing, a long tail hanging below the branch
    c.paint(tube(c, [(31, 31), (32.3, 38), (33.2, 45.5)], 2.6, 1.2), EMBER, 0.4, 1.55)
    c.paint(tube(c, [(32.2, 33), (33.6, 40.5)], 1.2, 0.8), LAPIS, 0.9, 1.6)
    c.paint(ellipse(c, 30.5, 25.5, 3.4, 5.4, -0.15) | c.circle(29.3, 19.8, 2.7), EMBER, 0.35, 1.6)
    wing = ellipse(c, 31.8, 26.5, 2.4, 5.0, -0.2)
    c.paint(wing, SAFFRON, 0.2, 1.65)
    c.paint(wing & (Y > 26.2), LAPIS, 0.85, 1.7)
    c.paint(ellipse(c, 28.4, 20.0, 1.5, 1.3), PEARL, 0.05, 1.7)
    c.paint(c.circle(28.5, 19.8, 0.55), UMBER, 1.0, 1.9)
    c.paint(c.poly_mask([(27.0, 19.3), (25.0, 20.4), (25.3, 22.6), (26.6, 23.1), (27.4, 21.6)]), PEARL, 0.45, 1.85)
    c.paint(c.poly_mask([(26.6, 22.0), (27.6, 21.8), (27.4, 23.2), (26.4, 23.4)]), UMBER, 0.9, 1.9)
    # a hanging heliconia and a few blooms
    for k in range(5):
        hy, s = 2.5 + 2.2 * k, (1 if k % 2 else -1)
        c.paint(c.poly_mask([(24.5, hy), (24.5 + s * 2.8, hy + 0.9), (24.5, hy + 2.1)]), EMBER, 0.3, 1.5)
        c.paint(c.circle(24.5 + s * 2.3, hy + 0.9, 0.6), SAFFRON, 0.1, 1.55)
    c.paint(c.line_mask([(24.5, 0), (24.5, 13.5)], 0.6), FERN, 0.6, 1.45)
    for (fx, fy, fam) in ((3.5, 28.5, EMBER), (26.5, 43, SAFFRON), (40, 30, PEARL), (13.5, 31, EMBER), (36, 13, PEARL)):
        for k in range(5):
            a = k * 2 * math.pi / 5
            c.paint(c.circle(fx + 1.0 * math.cos(a), fy + 1.0 * math.sin(a), 0.75), fam, 0.2, 1.5)
        c.paint(c.circle(fx, fy, 0.5), SAFFRON if fam != SAFFRON else EMBER, 0.3, 1.6)
    frame(c)
    return encode(c.to_tiles())


# ---------------------------------------------------------------------------
# master
# ---------------------------------------------------------------------------

def reef():
    """A sea turtle gliding over a coral garden: a red branching coral, a brain coral, a table coral, an
    anemone with clownfish, and schools of small fish swimming in tidy rows through open blue water."""
    c = Canvas(42, 46)
    X, Y = c.X, c.Y
    tx, ty = np.floor(X).astype(int), np.floor(Y).astype(int)
    c.paint(ALL(c), LAPIS, np.clip(0.15 + 0.6 * Y / 44, 0, 1))
    c.paint((np.sin((X - 0.5 * Y) * 0.5) > 0.85) & (Y < 24), LAPIS, 0.0, 1.0)      # sunlight shafts
    # pale coral sand with shadowed ripples
    sand = Y > 38.8 + 0.8 * np.sin(X * 0.35)
    c.paint(sand, PEARL, 0.2)
    c.paint(sand & (((Y + 0.6 * np.sin(X * 0.9)) % 2.0) < 0.55) & (Y > 39.8), UMBER, 0.05, 1.1)
    # a red branching coral, its tips pale with polyps
    rng = random.Random(8)

    def branch(x, y, ang, ln, w, depth):
        x1, y1 = x + math.cos(ang) * ln, y + math.sin(ang) * ln
        c.paint(tube(c, [(x, y), (x1, y1)], w, w * 0.8), EMBER, 0.45, 1.25)
        if depth:
            for da in (-0.55, 0.5):
                branch(x1, y1, ang + da + rng.uniform(-0.1, 0.1), ln * 0.75, w * 0.8, depth - 1)
        else:
            c.paint(c.circle(x1, y1, 0.8), EMBER, 0.0, 1.35)
    branch(8, 45, -1.57, 5.5, 2.4, 3)
    # a round brain coral with meandering grooves
    brain = ellipse(c, 19.5, 41.0, 7.0, 5.4)
    grooves = ((tx + np.round(1.4 * np.sin(ty * 1.1 + tx * 0.3)).astype(int)) % 3) == 0
    c.paint(brain, SAFFRON, np.clip(0.2 + 0.4 * (Y - 35.6) / 9, 0, 1), 1.2)
    c.paint(brain & grooves & (Y > 36.4), UMBER, 0.45, 1.25)
    # a flat table coral on a short stalk, polyps dotted along its rim
    c.paint(rect(c, 35.5, 32, 37.5, 45), UMBER, 0.55, 1.2)
    plate = ellipse(c, 36.5, 31.8, 6.3, 1.9)
    c.paint(plate, PEARL, np.clip(0.15 + 0.5 * (Y > 31.9), 0, 1), 1.25)
    c.paint(plate & (ty == 30) & (tx % 2 == 1), FERN, 0.1, 1.3)
    # an anemone and its clownfish
    ax, ay = 29, 42.5
    for a in np.linspace(-2.8, -0.35, 7):
        tip = (ax + 3.3 * math.cos(a), ay + 3.6 * math.sin(a))
        c.paint(c.line_mask([(ax, ay), tip], 1.0), FERN, 0.2, 1.3)
        c.paint(c.circle(*tip, 0.6), PEARL, 0.0, 1.35)
    c.paint(ellipse(c, ax, ay + 0.8, 2.8, 1.4), FERN, 0.75, 1.3)
    # the sea turtle, heading up and to the right: plated green shell, golden head and flippers swept back
    ang = -0.25
    ca, sa = math.cos(ang), math.sin(ang)

    def at(u, v):
        return (19.0 + u * ca - v * sa, 13.5 + u * sa + v * ca)
    for side in (-1, 1):
        c.paint(ellipse(c, *at(1.0, side * 6.5), 5.2, 1.7, ang - side * 0.8), SAFFRON, 0.45, 1.3)
        c.paint(ellipse(c, *at(-6.6, side * 3.4), 2.4, 1.1, ang - side * 0.55), SAFFRON, 0.45, 1.3)
    c.paint(ellipse(c, *at(8.3, 0), 2.5, 1.9, ang), SAFFRON, 0.35, 1.3)
    c.paint(c.circle(*at(9.2, -0.8), 0.5), UMBER, 1.0, 1.6)
    shell = ellipse(c, *at(0, 0), 7.8, 5.8, ang)
    scutes = [at(u, v) for u in (-3.5, 0, 3.5) for v in (-3.2, 0, 3.2)]
    d1, d2, idx = voronoi(c, scutes)
    c.paint(shell, FERN, np.clip(0.3 + 0.3 * (idx % 2) + 0.08 * d1, 0, 1), 1.45)
    c.paint(shell & ((d2 - d1) < 0.55), UMBER, 0.35, 1.5)
    c.paint(shell & ~ellipse(c, *at(0, 0), 6.9, 4.9, ang), FERN, 1.0, 1.5)

    # schools of small fish in tidy rows, drawn tile by tile (T tail, B body, S stripe, E eye; facing right)
    small = ["T.BBB.", "TTBBEB", "T.BBB."]
    banded = ["T.SBS.", "TTSBSE", "T.SBS."]
    disc = ["...BB..", "T.BBBB.", "TTBBBEB", "T.BBBB.", "...BB.."]

    def school(rows, spots, flip, body, tail=None, stripe=(PEARL, 0.05)):
        pal = {"B": body, "T": tail or body, "S": stripe, "E": (UMBER, 1.0)}
        for (x0, y0) in spots:
            for j, row in enumerate(rows):
                for i, ch in enumerate(row):
                    if ch != ".":
                        col = x0 + (len(row) - 1 - i if flip else i)
                        c.paint(rect(c, col, y0 + j, col + 1, y0 + j + 1), *pal[ch], 1.7)
    school(disc, [(26, 1), (33, 1), (33, 6)], True, (SAFFRON, 0.1))                       # yellow tangs
    school(small, [(2, 2), (4, 6), (2, 10), (4, 14), (2, 18)], False, (EMBER, 0.05))       # orange anthias
    school(banded, [(27, 14), (34, 14), (30, 18), (27, 22), (34, 22)], True, (PEARL, 0.05), stripe=(UMBER, 0.9))
    school(small, [(2, 24), (9, 24), (16, 24)], False, (FERN, 0.1))                        # green chromis
    school(small, [(11, 1), (18, 1)], False, (FERN, 0.1))
    school(disc, [(27, 25), (34, 25)], True, (LAPIS, 1.0), tail=(SAFFRON, 0.2))             # blue tangs
    school(small, [(13, 27), (20, 27), (13, 31), (20, 31)], False, (PEARL, 0.15), tail=(LAPIS, 0.3))  # silversides
    school(banded, [(23, 34)], False, (EMBER, 0.3))                                        # clownfish
    school(banded, [(29, 35)], True, (EMBER, 0.3))
    frame(c)
    return encode(c.to_tiles())


def bamboo():
    """A bamboo grove: ringed green, golden and pale stems, leaf sprays, and a panda eating in the middle."""
    c = Canvas(42, 46)
    X, Y = c.X, c.Y
    tx, ty = np.floor(X).astype(int), np.floor(Y).astype(int)
    r = random.Random(52)
    # misty light between the stems, faint stems far behind
    c.paint(ALL(c), LAPIS, np.clip(0.02 + 0.25 * Y / 40, 0, 1))
    for x0 in (2, 8, 16, 25, 33, 39):
        c.paint(rect(c, x0, -1, x0 + 1, 41) & ((ty + x0) % 7 != 0), LAPIS, 0.55)
    # the forest floor: soil, fallen leaves, sunlit spots, bamboo shoots
    ground = Y > 39.5 + 0.7 * np.sin(X * 0.5)
    c.paint(ground, UMBER, np.clip(0.5 + 0.2 * np.sin(X * 1.3 + Y), 0, 1))
    for k in range(40):
        gx, gy = r.uniform(0, 42), r.uniform(40.5, 46)
        c.paint(ellipse(c, gx, gy, 1.6, 0.75, r.uniform(-0.5, 0.5)) & ground, SAFFRON if k % 4 == 0 else EMBER,
                r.uniform(0.2, 0.6), 1.3)
    for (sx, h) in ((4.5, 7), (37.0, 6), (10.0, 5), (31.5, 4.5)):
        shoot = c.poly_mask([(sx - 1.8, 42), (sx + 1.8, 42), (sx, 42 - h)])
        c.paint(shoot, EMBER, 0.6, 1.4)
        c.paint(shoot & ((ty % 3) == 0), UMBER, 0.7, 1.45)
    # stems: (x0, width, family, ring family, node phase), ringed every eighth row
    stems = [(0, 2, FERN, UMBER, 1), (3, 3, SAFFRON, FERN, 3), (8, 2, FERN, FERN, 6), (11, 3, PEARL, UMBER, 4),
             (26, 3, SAFFRON, FERN, 1), (30, 2, FERN, FERN, 5), (34, 3, PEARL, UMBER, 2), (38.5, 3, FERN, UMBER, 7),
             (16, 2, FERN, FERN, 3), (22, 2, FERN, UMBER, 0)]
    for i, (x0, w, fam, ring, ph) in enumerate(stems):
        s = rect(c, x0, -1, x0 + w, 41)
        c.paint(s, fam, np.clip(0.02 + 0.45 * (X - x0) / w, 0, 1), 1.2)
        c.paint(s & ((ty + ph) % 8 == 0), ring, 0.85 if ring == UMBER else (1.0 if ring == fam else 0.7), 1.3)
        # leaf sprays hanging from the upper nodes of every other stem
        for j, ny in enumerate(range(8 - ph % 8, 20, 8)):
            if (i + j) % 2:
                continue
            side = 1 if (i // 2 + j) % 2 else -1
            bx = x0 + (w if side > 0 else 0)
            for k in range(4):
                a = 0.2 + 0.32 * k
                blade(c, bx, ny, bx + side * 5.2 * math.cos(a), ny + 5.2 * math.sin(a), 1.5,
                      0.7 + 0.1 * (k % 3), prio=1.35, rib=False)
    # dappled sunlight on the floor
    for (sx, sy) in ((6, 42.5), (14, 44.5), (29, 43), (35, 45), (40, 42)):
        c.paint(ellipse(c, sx, sy, 1.4, 0.7), SAFFRON, 0.0, 1.4)
    # the panda: sitting in the middle of the grove
    px = 21.0
    body = ellipse(c, px, 33.5, 7.8, 8.2)
    c.paint(body, PEARL, np.clip(0.05 + 0.3 * np.abs(X - px) / 8, 0, 1), 1.5)
    for side in (-1, 1):
        c.paint(ellipse(c, px + side * 5.3, 40.2, 3.4, 2.6), UMBER, 0.95, 1.6)
        c.paint(ellipse(c, px + side * 5.6, 40.6, 1.5, 1.1), UMBER, 0.55, 1.65)
    # one arm raised to the mouth holding a stalk upright, the other resting on the belly
    c.paint(c.line_mask([(px - 5.0, 37), (px - 6.2, 9)], 1.4), FERN, 0.3, 1.8)
    c.paint(c.line_mask([(px - 5.0, 37), (px - 6.2, 9)], 1.4) & (ty % 5 == 0), FERN, 0.9, 1.85)
    for (a, ln) in ((-2.5, 5.0), (-1.9, 4.5), (-0.6, 4.5), (-0.1, 4.0)):
        blade(c, px - 6.2, 10.5, px - 6.2 + ln * math.cos(a), 10.5 + ln * math.sin(a), 1.6, 0.1, prio=1.85, rib=False)
    c.paint(tube(c, [(px - 7.0, 29.5), (px - 7.5, 26.5), (px - 5.4, 24.5)], 3.2, 2.8), UMBER, 0.95, 1.9)
    c.paint(tube(c, [(px + 7.0, 29.0), (px + 5.5, 32.5), (px + 2.0, 34.0)], 3.2, 2.6), UMBER, 0.95, 1.7)
    head = ellipse(c, px, 21.0, 5.6, 4.9)
    for side in (-1, 1):
        c.paint(c.circle(px + side * 4.4, 16.7, 2.0), UMBER, 0.95, 1.6)
    c.paint(head, PEARL, np.clip(0.02 + 0.2 * np.hypot(X - px, Y - 21) / 5, 0, 1), 1.6)
    for side in (-1, 1):
        c.paint(ellipse(c, px + side * 2.2, 20.5, 1.3, 1.9, side * 0.5), UMBER, 0.95, 1.8)
        c.paint(c.circle(px + side * 2.0, 20.1, 0.45), PEARL, 0.0, 2.0)
    c.paint(ellipse(c, px, 23.3, 1.0, 0.7), UMBER, 1.0, 1.9)
    frame(c)
    return encode(c.to_tiles())


SCENES = {
    "aurora": aurora, "canyon": canyon, "falls": victoria_falls, "iceberg": iceberg,
    "volcano": volcano, "rainforest": rainforest, "reef": reef, "bamboo": bamboo,
}
