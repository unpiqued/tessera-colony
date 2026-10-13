"""Challenge mosaics: pictures built from interlocking layers, so the order in which colours
are cleared really matters (nested rings, an over-under weave, a maze, a stained-glass window).
Each is about 1,700-1,850 tiles. Drawn with the same Canvas as art.py.
"""
import math
import random

import numpy as np

from art import Canvas, LAPIS, SAFFRON, FERN, EMBER, UMBER, PEARL


def frame(c, fam=UMBER, width=1):
    X, Y = c.X, c.Y
    d = np.minimum.reduce([X, c.w - X, Y, c.h - Y])
    c.paint(d < width, fam, 0.75, 1.3)
    return d


def nesting_rings():
    """Concentric squircle rings in four colours, cut by four Umber spokes that lead inward."""
    W, H = 40, 44
    c = Canvas(W, H)
    X, Y = c.X, c.Y
    cx, cy = 20.0, 21.5
    dx, dy = X - cx, Y - cy
    r = (np.abs(dx) ** 3 + np.abs(dy * 0.92) ** 3) ** (1 / 3)
    c.paint(np.ones_like(X, bool), PEARL, np.clip(0.15 + 0.25 * Y / H, 0, 1))
    ring_fams = [EMBER, SAFFRON, FERN, LAPIS]
    band = 2.25
    for k in range(8):
        r0 = 2.6 + k * band
        m = (r >= r0) & (r < r0 + band - 0.35)
        shade = np.clip(0.25 + 0.55 * (r - r0) / band + 0.1 * np.sin(np.arctan2(dy, dx) * 3), 0, 1)
        c.paint(m, ring_fams[k % 4], shade)
    # the jewel in the middle
    c.paint(r < 2.6, SAFFRON, np.clip(0.2 + 0.25 * r, 0, 1), 1.4)
    c.paint(r < 1.2, EMBER, 0.3, 1.6)
    # four diagonal spokes of Umber: an Umber team can tunnel along them toward the centre
    ang = np.arctan2(dy, dx)
    for a in (math.pi / 4, 3 * math.pi / 4, -math.pi / 4, -3 * math.pi / 4):
        da = np.abs(np.angle(np.exp(1j * (ang - a))))
        spoke = (da * np.maximum(r, 0.1) < 0.62) & (r > 4.9) & (r < 19.5)
        c.paint(spoke, UMBER, np.clip(0.5 + 0.02 * r, 0, 1), 1.5)
    d = frame(c, UMBER, 1)
    chk = (d >= 1) & (d < 2)
    c.paint(chk & (((np.floor(X) + np.floor(Y)) % 2) == 0), LAPIS, 0.55, 1.2)
    return c.to_tiles()


def basket_weave():
    """Over-under strips: Ember/Saffron run across, Fern/Pearl run down, Umber shows through the gaps."""
    W, H = 40, 44
    c = Canvas(W, H)
    X, Y = c.X, c.Y
    period = 5.0
    width = 3.2
    fx, fy = np.mod(X - 2.0, period), np.mod(Y - 2.0, period)
    ix, iy = np.floor((X - 2.0) / period), np.floor((Y - 2.0) / period)
    horiz = fy < width
    vert = fx < width
    c.paint(np.ones_like(X, bool), UMBER, np.clip(0.55 + 0.3 * np.sin(X * 0.4) * np.sin(Y * 0.37), 0, 1))
    h_fams = [EMBER, SAFFRON]
    v_fams = [FERN, PEARL]
    hf = np.where(np.mod(iy, 2) == 0, h_fams[0], h_fams[1])
    vf = np.where(np.mod(ix, 2) == 0, v_fams[0], v_fams[1])
    over_h = np.mod(ix + iy, 2) == 0
    # shading: a strip dips (darker) where it goes under
    h_shade = np.clip(0.2 + 0.5 * np.abs(fx - width / 2) / period + 0.25 * (fy / width), 0, 1)
    v_shade = np.clip(0.2 + 0.5 * np.abs(fy - width / 2) / period + 0.25 * (fx / width), 0, 1)
    only_h = horiz & ~vert
    only_v = vert & ~horiz
    cross = horiz & vert
    for fam in h_fams:
        c.paint(only_h & (hf == fam), fam, h_shade)
        c.paint(cross & over_h & (hf == fam), fam, np.clip(h_shade - 0.15, 0, 1), 1.2)
    for fam in v_fams:
        c.paint(only_v & (vf == fam), fam, v_shade)
        c.paint(cross & ~over_h & (vf == fam), fam, np.clip(v_shade - 0.15, 0, 1), 1.2)
    frame(c, LAPIS, 1.5)
    return c.to_tiles()


def labyrinth(seed=7):
    """A maze: Umber walls, and passages painted in colour bands by walking distance from the
    entrance at the bottom, so the deeper you go the more colours you have to clear first."""
    cols, rows, cell = 9, 10, 4
    W, H = cols * cell + 1 + 4, rows * cell + 1 + 4
    c = Canvas(W, H)
    X, Y = c.X, c.Y
    rng = random.Random(seed)
    # recursive backtracker
    open_e = set()
    seen = {(0, 0)}
    stack = [(0, 0)]
    while stack:
        x, y = stack[-1]
        nb = [(x + dx, y + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
              if 0 <= x + dx < cols and 0 <= y + dy < rows and (x + dx, y + dy) not in seen]
        if not nb:
            stack.pop()
            continue
        n = rng.choice(nb)
        open_e.add(frozenset(((x, y), n)))
        seen.add(n)
        stack.append(n)
    # a few extra openings make loops (more than one way in)
    for _ in range(6):
        x, y = rng.randrange(cols - 1), rng.randrange(rows - 1)
        n = (x + 1, y) if rng.random() < 0.5 else (x, y + 1)
        open_e.add(frozenset(((x, y), n)))
    entrance = (cols // 2, rows - 1)
    dist = {entrance: 0}
    q = [entrance]
    while q:
        cur = q.pop(0)
        x, y = cur
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (x + dx, y + dy)
            if n in seen and n not in dist and frozenset((cur, n)) in open_e:
                dist[n] = dist[cur] + 1
                q.append(n)
    band_fams = [SAFFRON, FERN, LAPIS, EMBER, PEARL]
    maxd = max(dist.values())
    c.paint(np.ones_like(X, bool), UMBER, np.clip(0.6 + 0.2 * np.sin(X + Y), 0, 1))    # walls
    ox, oy = 2.0, 2.0
    for (x, y), dd in dist.items():
        fam = band_fams[min(len(band_fams) - 1, dd * len(band_fams) // (maxd + 1))]
        x0, y0 = ox + 1 + x * cell, oy + 1 + y * cell
        room = (X >= x0) & (X < x0 + cell - 1) & (Y >= y0) & (Y < y0 + cell - 1)
        shade = np.clip(0.15 + 0.6 * (dd % 4) / 4 + 0.08 * (Y - y0), 0, 1)
        c.paint(room, fam, shade)
        for dx, dy in ((1, 0), (0, 1)):
            n = (x + dx, y + dy)
            if frozenset(((x, y), n)) in open_e and n in dist:
                if dx:
                    door = (X >= x0 + cell - 1) & (X < x0 + cell) & (Y >= y0) & (Y < y0 + cell - 1)
                else:
                    door = (Y >= y0 + cell - 1) & (Y < y0 + cell) & (X >= x0) & (X < x0 + cell - 1)
                nf = band_fams[min(len(band_fams) - 1, min(dd, dist[n]) * len(band_fams) // (maxd + 1))]
                c.paint(door, nf, 0.4)
    # entrance through the bottom wall and border
    ex0 = ox + 1 + entrance[0] * cell
    gate = (X >= ex0) & (X < ex0 + cell - 1) & (Y >= H - 3)
    c.paint(gate, band_fams[0], 0.3, 1.5)
    d = np.minimum.reduce([X, W - X, Y, H - Y])
    c.paint((d < 2) & ~gate, PEARL, np.clip(0.2 + 0.3 * (d < 1), 0, 1), 1.2)
    return c.to_tiles()


def rose_window():
    """A stained-glass rose: wedges of glass in three rings, held by Umber leading that joins
    everything together, set in a Lapis night with Pearl stars."""
    W, H = 40, 44
    c = Canvas(W, H)
    X, Y = c.X, c.Y
    cx, cy, R = 20.0, 22.0, 18.2
    dx, dy = X - cx, Y - cy
    r = np.hypot(dx, dy)
    ang = np.mod(np.arctan2(dy, dx) + math.pi / 2, 2 * math.pi)
    c.paint(np.ones_like(X, bool), LAPIS, np.clip(0.55 + 0.35 * Y / H, 0, 1))
    rng = random.Random(4)
    for _ in range(26):
        sx, sy = rng.uniform(1.5, W - 1.5), rng.uniform(1.5, H - 1.5)
        if math.hypot(sx - cx, sy - cy) > R + 1.5:
            c.paint(c.circle(sx, sy, 0.55), PEARL, 0.1, 1.8)
    inside = r < R
    rings = [(3.2, 8.0, 8, [SAFFRON, EMBER]), (8.0, 13.0, 12, [LAPIS, FERN, EMBER]),
             (13.0, R, 16, [EMBER, SAFFRON, FERN, LAPIS])]
    for (r0, r1, n, fams) in rings:
        seg = np.floor(ang / (2 * math.pi / n)).astype(int)
        for k in range(n):
            m = inside & (r >= r0) & (r < r1) & (seg == k)
            shade = np.clip(0.2 + 0.6 * (r - r0) / (r1 - r0), 0, 1)
            c.paint(m, fams[k % len(fams)], shade)
    c.paint(r < 3.2, PEARL, np.clip(0.1 + 0.2 * r, 0, 1), 1.3)
    c.paint(r < 1.4, SAFFRON, 0.2, 1.5)
    # leading: ring boundaries and wedge edges
    lead = np.zeros_like(inside)
    for rb in (3.2, 8.0, 13.0, R):
        lead |= np.abs(r - rb) < 0.45
    for (r0, r1, n, _) in rings:
        w = 2 * math.pi / n
        edge = np.abs(np.mod(ang + w / 2, w) - w / 2) * np.maximum(r, 0.1)
        lead |= (edge < 0.4) & (r >= r0) & (r < r1)
    c.paint(lead & (r < R + 0.45), UMBER, 0.8, 1.6)
    frame(c, UMBER, 1)
    return c.to_tiles()


CHALLENGE_ART = {
    "rings": nesting_rings,
    "weave": basket_weave,
    "maze": labyrinth,
    "rose": rose_window,
}
