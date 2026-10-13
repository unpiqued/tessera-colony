"""Cosmos pack: wonders of the sky and moments of science, drawn with the supersampled Canvas of
art.py (a tile's colour family comes from the dominant object under it, its tone from the shading).

Gentle: total solar eclipse, Saturn's rings, Halley's Comet over a town (1910), Newton's prism (1666).
Challenge: Franklin's kite in a thunderstorm (1752), a spiral galaxy.
Master (very busy, every colour in many small islands): the DNA double helix (1953) and
Mendeleev's periodic table (1869).
"""
import math
import random

import numpy as np

from art import Canvas, LAPIS, SAFFRON, FERN, EMBER, UMBER, PEARL, encode, smoothstep
from art_scenes import ALL, ellipse, rect, tube, frame, smooth_noise


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def bezier(p0, p1, p2, n=40):
    """Points along a quadratic Bezier curve."""
    return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
             (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]) for t in np.linspace(0, 1, n)]


def tile_stars(c, pts, fam=PEARL, shade=0.05, prio=1.8):
    """Crisp one-tile stars: a small disc centred in each listed tile."""
    for (x, y) in pts:
        c.paint(c.circle(math.floor(x) + 0.5, math.floor(y) + 0.5, 0.55), fam, shade, prio)


def random_stars(c, seed, n, avoid=lambda x, y: False, fam=PEARL):
    r = random.Random(seed)
    pts = []
    while len(pts) < n:
        x, y = r.randrange(1, c.w - 1), r.randrange(1, c.h - 1)
        if not avoid(x + 0.5, y + 0.5) and all(abs(x - a) + abs(y - b) > 2 for a, b in pts):
            pts.append((x, y))
    tile_stars(c, pts, fam)


def person(c, x, base, h, coat, arm=None, hat="bowler"):
    """A small figure in colour: dark legs and hat, a coat, a pale face and hand; `arm` = (dx, dy)
    points one arm from the shoulder. Proportions are for h = 8.5 tiles and scale with h."""
    k = h / 8.5
    top = base - h
    if hat == "bowler":
        c.paint(ellipse(c, x, top + 0.9 * k, 1.0 * k, 0.9 * k) | rect(c, x - 1.5 * k, top + 1.4 * k, x + 1.5 * k, top + 2.0 * k),
                UMBER, 1.0, 1.7)
    elif hat == "wide":
        c.paint(ellipse(c, x, top + 1.0 * k, 0.9 * k, 0.8 * k) | ellipse(c, x, top + 1.7 * k, 2.1 * k, 0.45 * k), UMBER, 0.67, 1.7)
    c.paint(c.circle(x, top + 2.9 * k, 1.0 * k), EMBER, 0.0, 1.6)
    c.paint(rect(c, x - 1.2 * k, base - 2.1 * k, x - 0.3 * k, base) | rect(c, x + 0.3 * k, base - 2.1 * k, x + 1.2 * k, base),
            UMBER, 1.0, 1.6)
    c.paint(c.poly_mask([(x - 1.5 * k, top + 4.0 * k), (x + 1.5 * k, top + 4.0 * k), (x + 1.9 * k, base - 2.0 * k),
                         (x - 1.9 * k, base - 2.0 * k)]), coat, 0.67, 1.6)
    if arm:
        s = 1 if arm[0] > 0 else -1
        hx, hy = x + arm[0], top + 4.4 * k + arm[1]
        c.paint(c.line_mask([(x + s * 1.2 * k, top + 4.5 * k), (hx, hy)], 0.95 * k), coat, 0.67, 1.65)
        c.paint(c.circle(hx, hy, 0.6 * k), EMBER, 0.0, 1.7)


def tile_grid_paint(c, fam, shade, prio=1.0):
    """Paint a per-tile (family, shade) grid exactly onto the canvas (-1 = leave as is)."""
    tx = np.clip(np.floor(c.X).astype(int), 0, c.w - 1)
    ty = np.clip(np.floor(c.Y).astype(int), 0, c.h - 1)
    F, S = fam[ty, tx], shade[ty, tx]
    for f in range(6):
        m = F == f
        if m.any():
            c.paint(m, f, S, prio)


def sprite(c, x0, y0, rows, fam, shade, prio=1.6):
    """Paint a small tile-exact pixel sprite ('#' = filled) with its top-left tile at (x0, y0)."""
    m = np.zeros_like(c.X, bool)
    for j, row in enumerate(rows):
        for i, ch in enumerate(row):
            if ch == '#':
                m |= rect(c, x0 + i, y0 + j, x0 + i + 1, y0 + j + 1)
    c.paint(m, fam, shade, prio)


# pixel silhouettes of eclipse watchers ('#' = filled tile)
WATCHER = ["..###..", "..###..", "...#...", ".#####.", "#######", "#.###.#", "#.###.#", "..###..", "..###..",
           "..#.#..", "..#.#..", "..#.#..", ".##.##."]
POINTER = [".......#", "..###.#.", "..###.#.", "...#.#..", ".#####..", "#.###...", "#.###...", "..###...", "..###...",
           "..#.#...", "..#.#...", "..#.#...", ".##.##.."]
CHILD = [".###.", ".###.", "..#..", "#####", ".###.", ".###.", ".#.#.", ".#.#."]


# ---------------------------------------------------------------------------
# gentle
# ---------------------------------------------------------------------------

def eclipse():
    """Totality: the black moon ringed by a pearly corona with red prominences, a few stars in the
    darkened sky, a sunset glow all round the horizon, and people watching from the hills."""
    c = Canvas(42, 42)
    X, Y = c.X, c.Y
    cx, cy, R = 21.0, 15.0, 5.8
    d = np.hypot(X - cx, Y - cy)
    A = np.arctan2(Y - cy, X - cx)
    # deep blue sky, a shade paler low down, a band of sunset colours all round the horizon
    c.paint(ALL(c), LAPIS, 1.0 - 0.34 * smoothstep(23.5, 24.5, Y))
    c.paint(Y > 27.0 + 0.7 * np.sin(X * 0.25), EMBER, np.clip(1.0 - 0.3 * (Y - 27), 0.33, 1))
    c.paint(Y > 30.5 + 0.5 * np.sin(X * 0.33 + 1), SAFFRON, np.clip(0.12 * (Y - 30.5), 0, 0.4))
    tile_stars(c, [(3, 3), (10, 4), (36, 2), (39, 8), (3, 21), (38, 22), (16, 1), (29, 1), (2, 12), (34, 25)])
    c.paint(c.circle(7.0, 8.0, 0.85), PEARL, 0.0, 2.0)   # Venus
    # the corona: a bright inner ring and uneven streamers, fringed with a pale blue glow
    reach = R * 1.25 + 0 * A
    for a, L, w in ((0.25, 1.5, 0.2), (math.pi + 0.25, 1.35, 0.2), (math.pi - 0.5, 0.7, 0.16), (-0.45, 0.65, 0.15),
                    (-1.95, 0.35, 0.09), (-1.3, 0.3, 0.08), (1.9, 0.4, 0.1), (1.25, 0.3, 0.09), (2.6, 0.3, 0.1)):
        reach = reach + R * L * np.exp(-(np.angle(np.exp(1j * (A - a))) / w) ** 2)
    c.paint(d < reach + 1.5, LAPIS, 0.33)
    c.paint(d < reach, PEARL, np.clip(0.75 * (d - R) / (reach - R), 0, 1), 1.1)
    # red prominences licking out from the limb, then the moon's black disc
    for a, s in ((-2.35, 1.2), (0.55, 0.95), (1.95, 1.05), (-0.85, 0.85)):
        px, py = cx + (R + 0.5) * math.cos(a), cy + (R + 0.5) * math.sin(a)
        c.paint(ellipse(c, px, py, 1.3 * s, 1.1 * s, a + math.pi / 2), EMBER, 0.33, 1.9)
    c.paint(d < R, UMBER, 1.0, 1.6)
    # dark rolling hills and the watchers (two point up at the sun)
    ground = lambda x: 37.0 + 1.3 * np.sin(x * 0.2 + 0.4) + 0.4 * np.sin(x * 0.6)
    c.paint(Y > ground(X), UMBER, 0.95)
    for (x, spr) in ((3, POINTER), (10, WATCHER), (16, CHILD), (24, WATCHER), (31, [r[::-1] for r in POINTER])):
        g = int(math.floor(float(ground(x + len(spr[0]) / 2))))
        sprite(c, x, g - len(spr) + 1, spr, UMBER, 1.0)
    frame(c)
    return encode(c.to_tiles())


def saturn():
    """Saturn tilted in a starfield: a banded cream-and-ochre globe, wide pale rings split by the
    Cassini gap, the rings' shadow on the globe, the globe's shadow on the rings behind, three moons."""
    c = Canvas(46, 38)
    X, Y = c.X, c.Y
    cx, cy, tilt, k = 23.0, 19.0, -0.28, 0.27
    ca, sa = math.cos(tilt), math.sin(tilt)
    u = (X - cx) * ca + (Y - cy) * sa          # along the ring plane
    v = -(X - cx) * sa + (Y - cy) * ca         # across it (positive = the near side)
    re = np.hypot(u, v / k)                    # radius measured in the ring plane
    Rp, ob = 9.0, 0.92
    pr = np.hypot(u / Rp, v / (Rp * ob))
    globe = pr <= 1
    c.paint(ALL(c), LAPIS, 1.0)

    def busy(x, y):
        uu, vv = (x - cx) * ca + (y - cy) * sa, -(x - cx) * sa + (y - cy) * ca
        return math.hypot(uu, vv / k) < 22.5 or math.hypot(uu / Rp, vv / (Rp * ob)) < 1.25 or math.hypot(x - 6.5, y - 31) < 3
    random_stars(c, 5, 28, busy)
    for (sx, sy) in ((4.5, 5.5), (29.5, 34.5), (42.5, 19.5)):                     # a few bright stars
        c.paint(rect(c, sx - 1.5, sy - 0.5, sx + 1.5, sy + 0.5) | rect(c, sx - 0.5, sy - 1.5, sx + 0.5, sy + 1.5),
                PEARL, 0.1, 1.8)
    # the rings: B (bright), the Cassini gap (open sky), A (greyer)
    along = np.abs(u) / 21.0
    ringB = (re >= 11.8) & (re < 16.4)
    ringA = (re >= 17.8) & (re < 21.3)

    def rings(where):
        c.paint(ringB & where, PEARL, np.clip(0.3 * along, 0, 1), 1.2)
        c.paint(ringA & where, PEARL, np.clip(0.6 + 0.3 * along, 0, 1), 1.2)
    rings(ALL(c))
    # the globe's shadow falls across the rings behind it
    c.paint((ringA | ringB) & (v < 0) & (np.hypot((u - 4.5) / Rp, v / (Rp * ob)) < 1.0), LAPIS, 1.0, 1.25)
    # the globe: cream and ochre zones with brown belts, darker towards the limb and the lower right
    lat = v / (Rp * ob)
    limb = 0.3 * pr ** 4 + 0.25 * np.clip((u * 0.7 + v * 0.7) / Rp, 0, 1)
    bands = ((-1.1, -0.68, SAFFRON, 0.7), (-0.68, -0.46, SAFFRON, 0.3), (-0.46, -0.3, UMBER, 0.0),
             (-0.3, 0.02, SAFFRON, 0.0), (0.02, 0.18, UMBER, 0.05), (0.18, 1.1, SAFFRON, 0.35))
    for lo, hi, f, b in bands:
        c.paint(globe & (lat >= lo) & (lat < hi), f, np.clip(b + limb, 0, 1), 1.3)
    # the rings' shadow hugs the near rings where they cross the globe; then the near rings in front
    c.paint(globe & (v > 0) & (re < 11.8) & (re > 9.9), UMBER, 0.95, 1.35)
    rings(v > 0)
    # moons: orange Titan and two small icy ones
    c.paint(c.circle(6.5, 31.0, 1.6), SAFFRON, 0.9, 1.8)
    c.paint(c.circle(40.0, 6.5, 1.05), PEARL, 0.15, 1.8)
    c.paint(c.circle(38.5, 32.5, 0.8), PEARL, 0.05, 1.8)
    frame(c)
    return encode(c.to_tiles())


def halley():
    """Halley's Comet in 1910: a bright head low in the sky, its tail curving away to the top-left,
    over a sleeping town of gables, chimneys and a spire; people on a hill point up at it."""
    c = Canvas(44, 40)
    X, Y = c.X, c.Y
    c.paint(ALL(c), LAPIS, 1.0 - 0.34 * smoothstep(27.5, 28.5, Y))
    tile_stars(c, [(3, 15), (8, 20), (15, 21), (21, 14), (26, 22), (39, 4), (41, 12), (37, 24), (31, 3), (14, 1), (2, 22)])
    # the comet: head low on the right, the tail curving away to the top-left corner in a pale glow
    hx, hy = 32.5, 17.0
    path = bezier((hx, hy), (20.0, 5.0), (-1.5, 2.5), 50)
    c.paint(tube(c, path, 3.0, 10.5), LAPIS, 0.35)
    head_d = np.hypot(X - hx, Y - hy)
    c.paint(tube(c, path, 1.7, 7.0), PEARL, np.clip(0.75 * head_d / 34, 0, 1), 1.1)
    c.paint(c.circle(hx, hy, 2.0), PEARL, 0.0, 1.5)
    c.paint(c.circle(hx, hy, 1.0), SAFFRON, 0.0, 1.7)
    # the sleeping town: steep gables with chimneys, a church spire, a few lit windows
    houses = ((16.5, 21.5, 33.5, 3.6, EMBER), (21.5, 25.0, 34.5, 2.6, UMBER), (29.0, 34.5, 32.0, 3.8, EMBER),
              (34.5, 38.5, 33.5, 2.8, UMBER), (38.5, 43.5, 31.5, 4.0, EMBER))
    for i, (x0, x1, top, rh, rf) in enumerate(houses):
        c.paint(rect(c, x0, top, x1, 40), PEARL, 1.0)
        c.paint(rect(c, x1 - 1.9, top - rh - 0.3, x1 - 0.8, top), UMBER, 0.95, 1.2)      # chimney
        c.paint(c.poly_mask([(x0 - 0.5, top + 0.4), ((x0 + x1) / 2, top - rh), (x1 + 0.5, top + 0.4)]), rf,
                0.9 if rf == EMBER else 0.4, 1.1)
        for j, wx in enumerate(np.arange(x0 + 1.1, x1 - 1.0, 2.2)):
            lit = (i + j) % 3 == 1
            c.paint(rect(c, wx, top + 1.3, wx + 1.0, top + 2.6), SAFFRON if lit else UMBER, 0.05 if lit else 1.0, 1.5)
    c.paint(rect(c, 25.0, 26.5, 29.0, 40), PEARL, 1.0, 1.05)                         # church tower
    c.paint(c.poly_mask([(24.4, 26.8), (27.0, 17.5), (29.6, 26.8)]), UMBER, 0.4, 1.1)
    c.paint(rect(c, 26.4, 28.4, 27.6, 30.6) | c.circle(27.0, 28.4, 0.6), SAFFRON, 0.05, 1.5)
    c.paint(Y > 38.4, FERN, 1.0, 1.1)
    # the hill with three watchers pointing at the comet
    hill_top = lambda x: 31.5 + 0.02 * (x - 6) ** 2 + (0.35 * (x - 15) ** 1.6 if x > 15 else 0)
    hill = Y > np.vectorize(hill_top)(np.clip(X, 0, 25))
    c.paint(hill & (X < 25), FERN, np.clip(0.75 + 0.02 * (Y - 30), 0, 1), 1.2)
    for (x, h, coat, arm, hat) in ((4.2, 8.6, PEARL, (3.4, -3.2), "bowler"), (9.2, 8.2, EMBER, None, "wide"),
                                   (13.4, 5.8, SAFFRON, (2.6, -2.6), None)):
        person(c, x, hill_top(x) + 0.6, h, coat, arm, hat)
    frame(c)
    return encode(c.to_tiles())


def prism():
    """Newton's darkened room (1666): a sunbeam through a hole in the window shutter strikes a glass
    prism held in a brass stand and fans out into a spectrum on the wall; a green cloth on the table,
    a book, and books piled on the floor."""
    c = Canvas(44, 40)
    X, Y = c.X, c.Y
    # dark wall and floorboards
    c.paint(ALL(c), UMBER, 1.0)
    c.paint(Y > 35.0, UMBER, 0.67)
    c.paint((Y > 35.0) & (Y < 36.0), UMBER, 0.33)                                   # skirting board
    c.paint(rect(c, 3.0, 36.8, 41.0, 40.0), EMBER, np.where((Y > 37.4) & (Y < 37.9), 0.5, 1.0), 1.1)   # rug
    # the closed shutter (two leaves of vertical boards) in a stone window, a small hole letting in the sun
    c.paint(rect(c, 1.0, 2.0, 13.0, 28.0), PEARL, 1.0, 1.1)                          # stone window surround
    c.paint(rect(c, 1.0, 27.0, 13.5, 28.0), PEARL, 0.67, 1.15)                       # sill
    c.paint(rect(c, 2.0, 3.0, 12.0, 27.0), UMBER, np.where(((X - 2.0) % 2.5) < 0.5, 0.67, 0.2), 1.15)
    c.paint(rect(c, 6.6, 3.0, 7.4, 27.0), UMBER, 1.0, 1.25)
    c.paint(c.circle(9.5, 12.0, 1.1), SAFFRON, 0.0, 1.9)
    # the white beam slanting down into the prism, and its path through the glass
    c.paint(tube(c, [(9.5, 12.0), (18.3, 16.8)], 1.5, 2.0), PEARL, 0.0, 1.4)
    tri = [(15.8, 12.8), (26.2, 12.8), (21.0, 21.9)]
    c.paint(c.poly_mask(tri), LAPIS, np.clip(0.02 + 0.03 * (Y - 13), 0, 1), 1.3)
    c.paint(c.line_mask([tri[0], tri[1]], 0.6), PEARL, 0.2, 1.35)
    c.paint(tube(c, [(18.3, 16.8), (23.6, 17.2)], 1.5, 1.5), PEARL, 0.05, 1.4)
    # the spectrum: blue bent most, red least; it lands as a bright oblong on the wall
    ox, oy = 23.8, 17.2
    edges = [5.0, 8.8, 12.6, 16.4, 20.2]
    for i, fam in enumerate((LAPIS, FERN, SAFFRON, EMBER)):
        wedge = c.poly_mask([(ox, oy - 0.3), (ox, oy + 0.3), (41.5, edges[i + 1]), (41.5, edges[i])])
        c.paint(wedge, fam, np.where(X > 37.0, 0.0, 0.4), 1.3)
    # the brass stand holding the prism by its lower edge
    c.paint(c.line_mask([(21.0, 21.5), (21.0, 28.5)], 0.9), SAFFRON, 0.9, 1.3)
    c.paint(rect(c, 19.6, 20.8, 22.4, 22.3) | rect(c, 18.3, 27.3, 23.7, 28.5), SAFFRON, 0.8, 1.35)
    # the table under a green cloth with a book on it, a rug, books piled on the floor
    c.paint(rect(c, 7.5, 28.5, 36.5, 32.5), FERN, np.where(Y < 29.5, 0.67, 1.0), 1.2)
    for lx in (9.0, 33.5):
        c.paint(rect(c, lx, 32.5, lx + 1.5, 38.5), UMBER, 0.33, 1.2)
    c.paint(rect(c, 27.0, 25.2, 33.5, 28.5), EMBER, 0.75, 1.3)
    c.paint(rect(c, 27.4, 26.6, 33.1, 27.5), PEARL, 0.2, 1.4)
    for j, (bx0, bx1, fam) in enumerate(((35.5, 41.5, LAPIS), (36.0, 41.0, EMBER), (35.8, 41.2, SAFFRON))):
        c.paint(rect(c, bx0, 37.0 - 1.5 * j, bx1, 38.5 - 1.5 * j), fam, 0.67, 1.3)
    frame(c)
    return encode(c.to_tiles())


# ---------------------------------------------------------------------------
# challenge
# ---------------------------------------------------------------------------

def kite():
    """Franklin's kite (1752): a diamond kite with a tail of bows high in a swirling storm, forks of
    lightning and slanting rain; the string runs down to a key and a figure in a tricorn hat."""
    c = Canvas(40, 46)
    X, Y = c.X, c.Y
    c.paint(ALL(c), LAPIS, 1.0 - 0.34 * smoothstep(33.5, 34.5, Y))
    # grey storm clouds spiralling round an eye up to the left
    ex, ey = 12.0, 10.0
    rr = np.hypot(X - ex, (Y - ey) * 1.25)
    th = np.arctan2(Y - ey, X - ex)
    swirl = np.sin(rr * 0.72 - th * 2.0 + 1.6 * smooth_noise(c, 6, 0.45))
    clouds = (swirl > -0.05) & (Y < 26 + 2.5 * np.sin(X * 0.35)) & (rr > 2.2)
    c.paint(clouds, PEARL, np.clip(1.05 - 0.5 * (swirl + 0.05), 0.5, 1))
    # slanting rain below the clouds
    r = random.Random(14)
    for _ in range(24):
        x, y = r.uniform(2, 38), r.uniform(24, 41)
        c.paint(c.line_mask([(x, y), (x - 1.0, y + 2.4)], 0.7), PEARL, 0.1, 1.25)
    # two forks of lightning with a pale glow
    for bolt in ([(36.0, 15.0), (33.0, 20.5), (35.6, 21.4), (32.0, 27.5), (34.4, 28.2), (31.2, 34.5)],
                 [(3.5, 12.0), (6.4, 16.8), (3.8, 17.8), (6.6, 23.4), (4.4, 24.2), (5.8, 29.0)]):
        c.paint(c.line_mask(bolt, 2.4), LAPIS, 0.0, 1.1)
        c.paint(c.line_mask(bolt, 1.0), SAFFRON, 0.0, 1.9)
    # the kite: a tilted diamond in red and gold quarters with cross sticks and a wire point
    kx, ky, ka = 25.5, 10.0, 0.3

    def K(px, py):
        return (kx + px * math.cos(ka) - py * math.sin(ka), ky + px * math.sin(ka) + py * math.cos(ka))
    top, rgt, bot, lft, mid = K(0, -7.0), K(5.8, 0), K(0, 10.0), K(-5.8, 0), K(0, 0)
    for i, (p, q) in enumerate(((top, rgt), (rgt, bot), (bot, lft), (lft, top))):
        c.paint(c.poly_mask([p, q, mid]), EMBER if i % 2 == 0 else SAFFRON, 0.33 if i % 2 == 0 else 0.15, 1.4)
    c.paint(c.line_mask([top, bot], 0.6) | c.line_mask([lft, rgt], 0.6), UMBER, 0.8, 1.7)
    c.paint(c.line_mask([top, K(0, -9.8)], 0.55), UMBER, 1.0, 1.7)
    # the tail with bows
    tail = [bot, (bot[0] + 1.2, bot[1] + 2.8), (bot[0] - 0.3, bot[1] + 5.6), (bot[0] + 1.4, bot[1] + 8.4),
            (bot[0] + 0.4, bot[1] + 11.2)]
    c.paint(c.line_mask(tail, 0.55), UMBER, 0.8, 1.6)
    for j, (bx, by) in enumerate(tail[1:]):
        bow = c.poly_mask([(bx - 1.9, by - 1.2), (bx - 1.9, by + 1.2), (bx, by)]) | \
            c.poly_mask([(bx + 1.9, by - 1.2), (bx + 1.9, by + 1.2), (bx, by)])
        c.paint(bow, FERN if j % 2 == 0 else EMBER, 0.2, 1.7)
    # the string sagging down past the key to Franklin's hand
    c.paint(c.line_mask(bezier(K(0, 2.0), (21.0, 30.0), (11.8, 35.4), 40), 0.65), UMBER, 0.95, 1.8)
    sprite(c, 13, 31, [".###.", ".#.#.", ".###.", "..#..", "..#..", "..##.", "..#..", "..##."], SAFFRON, 0.67, 2.0)   # key
    # the meadow with a puddle, and the figure in a tricorn hat
    c.paint(Y > 42.6 + 0.5 * np.sin(X * 0.4), FERN, np.clip(0.55 + 0.15 * np.sin(X * 2.0 + Y), 0, 1), 1.1)
    c.paint(ellipse(c, 27.0, 44.0, 4.0, 0.8), LAPIS, 0.33, 1.2)
    fx, base = 8.5, 44.0
    c.paint(c.poly_mask([(fx - 1.6, base - 7.3), (fx + 1.6, base - 7.3), (fx + 2.4, base - 2.2), (fx - 2.4, base - 2.2)]),
            UMBER, 0.67, 1.6)                                                      # coat
    c.paint(rect(c, fx - 1.4, base - 2.3, fx - 0.4, base) | rect(c, fx + 0.4, base - 2.3, fx + 1.4, base), PEARL, 0.33, 1.6)
    c.paint(rect(c, fx - 1.6, base - 0.8, fx - 0.2, base) | rect(c, fx + 0.2, base - 0.8, fx + 1.6, base), UMBER, 1.0, 1.7)
    c.paint(c.line_mask([(fx + 1.2, base - 6.6), (fx + 3.1, base - 8.3)], 1.0), UMBER, 0.67, 1.7)   # raised arm
    c.paint(c.circle(fx + 3.3, base - 8.6, 0.6) | c.circle(fx + 0.2, base - 8.4, 1.1), EMBER, 0.0, 1.8)  # hand, face
    c.paint(c.poly_mask([(fx - 2.0, base - 9.0), (fx + 2.4, base - 9.0), (fx + 0.2, base - 10.8)]), UMBER, 1.0, 1.8)
    frame(c)
    return encode(c.to_tiles())


def galaxy():
    """A spiral galaxy seen almost face-on: a golden core and two arms of pearly star light winding
    out to the edges of the picture, strung with blue and gold clusters and pink nebula knots, brown
    dust lanes along their inner edges, a deep blue sky with stars between them."""
    c = Canvas(44, 44)
    X, Y = c.X, c.Y
    cx, cy, rot, incl = 22.0, 22.0, -0.5, 0.86
    ca, sa = math.cos(rot), math.sin(rot)
    gx = (X - cx) * ca + (Y - cy) * sa
    gy = (-(X - cx) * sa + (Y - cy) * ca) / incl
    r = np.hypot(gx, gy)
    b, r0, Rd = 0.3, 2.4, 12.5
    psi = np.arctan2(gy, gx) - np.log(np.maximum(r, 0.5) / r0) / b    # 0 or pi along an arm crest
    wave, side = np.cos(2 * psi), np.sin(2 * psi)

    def to_img(rr, th):
        px, py = rr * math.cos(th), rr * math.sin(th) * incl
        return cx + px * ca - py * sa, cy + px * sa + py * ca
    # deep sky with stars, a paler glow round the core
    c.paint(ALL(c), LAPIS, 1.0)
    c.paint(r < 9.0, LAPIS, 0.67)
    # the arms: pearly star light, dimming and thinning outwards, running off the edges
    th_arm = 0.3 - 0.2 * np.clip((r - 4) / 8, 0, 1) + 0.25 * np.clip((r - 12) / 14, 0, 1)
    arm = (wave > th_arm) & (r > 3.0)
    c.paint(arm, PEARL, np.where(r < 11, 0.0, 1 / 3))
    in_gap = lambda x, y: bool(arm[int(y * 8), int(x * 8)])
    random_stars(c, 12, 30, lambda x, y: in_gap(x, y) or math.hypot(x - cx, y - cy) < 7)
    # dust lanes along the inner edge of each arm
    dust = (r > 4.5) & (r < 17) & (np.abs(wave - th_arm) < 0.2) & (side > 0)
    c.paint(dust, UMBER, 0.33, 1.2)
    c.paint(dust & (r < 9), EMBER, 1.0, 1.25)
    # star clusters strung along the crests: gold near the core, blue further out, pink knots
    rnd = random.Random(21)
    for k in range(2):
        for i in range(34):
            rr = 5.0 + i * 0.62 + rnd.uniform(-0.3, 0.3)
            th = math.log(rr / r0) / b + k * math.pi + rnd.uniform(-0.2, 0.2)
            x, y = to_img(rr, th)
            if i % 4 == 2:
                fam, sh = EMBER, 0.0
            elif rr < 8:
                fam, sh = SAFFRON, 0.1
            else:
                fam, sh = (LAPIS, 0.0) if i % 2 else (SAFFRON, 0.0)
            c.paint(c.circle(x, y, rnd.uniform(0.75, 1.1)), fam, sh, 1.5)
    # the bright core
    c.paint(r < 5.2, SAFFRON, np.clip(0.05 + 0.08 * r, 0, 1), 1.3)
    c.paint(r < 2.3, PEARL, 0.0, 1.4)
    frame(c)
    return encode(c.to_tiles())


# ---------------------------------------------------------------------------
# master
# ---------------------------------------------------------------------------

def helix():
    """The DNA double helix (1953): two pearly backbone ribbons twisting round each other, joined by
    tile-aligned base-pair rungs in four colours (A-T ember/saffron, G-C fern/lapis), on a near-black
    ground with a faint diamond lattice of atoms, as in a crystal."""
    c = Canvas(38, 48)
    X, Y = c.X, c.Y
    tx, ty = np.floor(X).astype(int), np.floor(Y).astype(int)
    cx, A, P, ph0 = 19.0, 11.5, 26.0, 0.6
    phase = lambda y: 2 * math.pi * y / P + ph0
    env = np.abs(X - cx) < A * np.abs(np.sin(2 * math.pi * Y / P + ph0)) + 2.6
    # background: near-black with a faint diamond lattice, atoms at its nodes
    c.paint(ALL(c), UMBER, 1.0)
    lines = ((tx + ty) % 6 == 0) | ((tx - ty) % 6 == 0)
    c.paint(lines & ~env, LAPIS, 1.0, 1.3)
    c.paint(((tx + ty) % 6 == 0) & ((tx - ty) % 6 == 0) & ~env, PEARL, 0.67, 1.4)
    # base-pair rungs on every other tile row, split at the axis into two complementary bases
    pairs = [(EMBER, SAFFRON), (SAFFRON, EMBER), (FERN, LAPIS), (LAPIS, FERN)]
    rnd = random.Random(1953)
    for row in range(1, 47, 2):
        s = math.sin(phase(row + 0.5))
        xa, xb = cx + A * s, cx - A * s
        if abs(xa - xb) < 4.5:
            continue
        fa, fb = pairs[rnd.randrange(4)]
        c.paint(rect(c, min(xa, xb), row, cx, row + 1), fa, 0.33, 1.4)
        c.paint(rect(c, cx, row, max(xa, xb), row + 1), fb, 0.33, 1.4)
    # the two backbones, sampled along their length and split into back and front runs
    ys = np.linspace(-3, 51, 540)
    back = np.zeros_like(X, bool)
    fronts = []
    for sgn in (1, -1):
        pts = [(cx + sgn * A * math.sin(phase(y)), y) for y in ys]
        z = [sgn * math.cos(phase(y)) for y in ys]
        runs, cur = [], [0]
        for i in range(1, len(ys)):
            if (z[i] > 0) != (z[cur[0]] > 0):
                runs.append(cur)
                cur = []
            cur.append(i)
        runs.append(cur)
        for run in runs:
            seg = [pts[i] for i in run]
            if len(seg) < 2:
                continue
            if z[run[0]] > 0:
                fronts.append(seg)
            else:
                back |= tube(c, seg, 2.2, 2.2)
    c.paint(back, PEARL, 0.8, 1.5)
    for seg in fronts:
        m = tube(c, seg, 2.2, 2.2)
        c.paint(tube(c, seg, 3.8, 3.8) & back & ~m, UMBER, 1.0, 1.6)     # dark gap where it crosses
        c.paint(m, PEARL, 0.0, 1.6)
    frame(c)
    return encode(c.to_tiles())


def periodic():
    """Mendeleev's periodic table (1869) chalked up on a green board: the familiar outline of small
    square cells (tall columns at both ends, the transition block, the two detached rows), each cell
    coloured by its group with a dark border and a dark corner mark; chalk and a duster on the tray."""
    W, H = 48, 36
    c = Canvas(W, H)
    # the board, its wooden chalk tray with a stick of chalk and a duster
    c.paint(ALL(c), FERN, 1.0)
    c.paint(rect(c, 0, 34.0, W, 35.0), UMBER, 0.33, 1.2)
    c.paint(rect(c, 6.0, 33.0, 9.0, 34.0), PEARL, 0.0, 1.6)
    c.paint(rect(c, 41.0, 32.9, 45.0, 34.0), SAFFRON, 0.67, 1.6)
    # the cells: groups 1-18 in periods 1-7, then the two detached rows
    group_fam = {1: EMBER, 2: SAFFRON, 13: FERN, 14: SAFFRON, 15: FERN, 16: PEARL, 17: EMBER, 18: LAPIS}
    for g in range(3, 13):
        group_fam[g] = LAPIS if g % 2 else PEARL
    col_x = {g: 5 + 2 * (g - 1) + (g >= 3) + (g >= 13) for g in range(1, 19)}
    cells = []
    for p in range(1, 8):
        for g in range(1, 19):
            if (p == 1 and g not in (1, 18)) or (p in (2, 3) and 3 <= g <= 12):
                continue
            f = PEARL if (g, p) == (1, 1) else group_fam[g]
            if g == 3 and p >= 6:
                f = EMBER if p == 6 else FERN          # the slots the detached rows belong to
            cells.append((col_x[g], 2 + 3 * (p - 1), f))
    for row, fams in ((27, (EMBER, SAFFRON)), (30, (FERN, LAPIS))):
        for i in range(15):
            cells.append((10 + 2 * i, row, fams[i % 2]))
    occ = np.zeros((H, W), bool)
    grid_f = np.full((H, W), -1, int)
    grid_s = np.zeros((H, W))
    for (x, y, f) in cells:
        occ[y:y + 2, x:x + 2] = True
        grid_f[y:y + 2, x:x + 2] = f
        grid_s[y:y + 2, x:x + 2] = 0.0 if f == PEARL else 1 / 3
        grid_s[y, x] = 1.0                              # the corner mark
    # a dark border round every cell: the ring of tiles next to any cell
    ring = np.zeros((H, W), bool)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            ring |= np.roll(np.roll(occ, dy, 0), dx, 1)
    ring &= ~occ
    grid_f[ring] = UMBER
    grid_s[ring] = 0.8
    tile_grid_paint(c, grid_f, grid_s, 1.5)
    frame(c)
    return encode(c.to_tiles())


SCENES = {
    "eclipse": eclipse, "saturn": saturn, "halley": halley, "prism": prism,
    "kite": kite, "galaxy": galaxy, "helix": helix, "periodic": periodic,
}
