"""Geometry & Illusions pack: mathematical figures, fractals and optical illusions, drawn with the
same supersampled Canvas as art.py.

Gentle: the impossible tribar (44 x 40), the golden spiral over Fibonacci squares (48 x 34), the
Mandelbrot set (46 x 40).
Challenge: the Sierpinski triangle (48 x 40), a Hilbert curve (41 x 41), the cafe wall illusion (46 x 43).
Master: a Celtic knotwork panel (44 x 44), a ten-fold girih star pattern (44 x 44).
All figures are plain mathematics or traditional ornament (no Escher, no lettering).
"""
import math

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

from art import Canvas, LAPIS, SAFFRON, FERN, EMBER, UMBER, PEARL, encode
from art_scenes import ALL, rect, frame

T1, T2, T3 = 1 / 3, 2 / 3, 1.0   # exact tones: flat areas come out without dither speckle


def tiles_of(c):
    """Tile-aligned coordinates (column, row) for crisp grid patterns."""
    return np.floor(c.X).astype(int), np.floor(c.Y).astype(int)


# ---------------------------------------------------------------------------
# Gentle
# ---------------------------------------------------------------------------

def impossible_triangle():
    """The Penrose tribar: three square bars along the x, y and z axes, seen so that (1,1,1) points at
    the viewer. Painted as boxes (only the faces turned toward us) in the order second half of the
    x bar, y bar, z bar, first half of the x bar -- which closes the impossible corner. Each face
    direction gets its own colour, so every bar shows two of the three shades."""
    W, H = 44, 40
    c = Canvas(W, H)
    X, Y = c.X, c.Y
    tx, ty = tiles_of(c)
    # calm background: a blue field, lighter round the figure, on isometric dot paper
    c.paint(ALL(c), LAPIS, np.where(np.hypot(tx + 0.5 - W / 2, (ty + 0.5 - H / 2) * 1.1) < 17.5, T1, T2))
    sp = 7.0
    for j in range(-1, 8):
        for i in range(-1, 9):
            gx = int(round(i * sp + (j % 2) * sp / 2 + 1.5))
            gy = int(round(j * sp * math.sqrt(3) / 2 + 2.5))
            c.paint((tx >= gx - 1) & (tx <= gx) & (ty >= gy - 1) & (ty <= gy), PEARL, 0.0, 1.1)
    # projection: x -> right, y -> up-left, z -> down-left (they sum to zero, so (1,1,1) is the view axis)
    L, w = 10.0, 1.95
    ex, ey, ez = (1.0, 0.0), (-0.5, -math.sqrt(3) / 2), (-0.5, math.sqrt(3) / 2)
    xbar2 = ((L / 2, L), (0, w), (0, w))
    ybar = ((L - w, L), (0, L), (0, w))
    zbar = ((L - w, L), (L - w, L), (0, L))
    xbar1 = ((0, L / 2), (0, w), (0, w))

    def flat(x, y, z):
        return (x * ex[0] + y * ey[0] + z * ez[0], x * ex[1] + y * ey[1] + z * ez[1])
    corners = [flat(x, y, z) for b in (xbar2, ybar, zbar, xbar1) for x in b[0] for y in b[1] for z in b[2]]
    x0, x1 = min(p[0] for p in corners), max(p[0] for p in corners)
    y0, y1 = min(p[1] for p in corners), max(p[1] for p in corners)
    s = min((W - 9) / (x1 - x0), (H - 8) / (y1 - y0))
    ox, oy = W / 2 - s * (x0 + x1) / 2, H / 2 + 0.3 - s * (y0 + y1) / 2

    def face(axis, box):
        (x0, x1), (y0, y1), (z0, z1) = box
        if axis == 0:
            q = [(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)]
        elif axis == 1:
            q = [(x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)]
        else:
            q = [(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
        return c.poly_mask([(ox + s * flat(*p)[0], oy + s * flat(*p)[1]) for p in q])

    # one colour per face direction: light gold, mid red, dark brown
    looks = {0: (EMBER, T1), 1: (SAFFRON, 0.0), 2: (UMBER, T2)}

    def box(b, axes):
        for a in axes:
            c.paint(face(a, b), looks[a][0], looks[a][1], 1.2)
    # the bars, each drawn over the one before (second half of x, y, z, then the first half of x on top)
    box(xbar2, (1, 2, 0))
    box(ybar, (0, 2, 1))
    box(zbar, (0, 1, 2))
    box(xbar1, (1, 2))            # no end face at the cut: it would show the trick
    frame(c)
    return encode(c.to_tiles())


def golden_spiral():
    """Fibonacci squares 1, 1, 2, 3, 5, 8, 13 laid round each other into a 21 x 13 golden rectangle,
    every one its own colour and outlined in dark brown, with the bold red quarter-circle spiral drawn
    corner to corner through all of them. Two tiles per unit, so the smallest squares are 2 x 2 and
    every outline falls exactly on a tile row or column."""
    W, H = 48, 34
    c = Canvas(W, H)
    X, Y = c.X, c.Y
    c.paint(ALL(c), PEARL, T1)                            # pale paper round the rectangle
    # lay the squares: each new one goes on the next side of the growing rectangle (right, down, left, up)
    sizes = [1, 1, 2, 3, 5, 8, 13]
    sq = [(0, 0, 1)]
    bx0, by0, bx1, by1 = 0, 0, 1, 1
    for k, f in enumerate(sizes[1:]):
        side = k % 4
        x, y = [(bx1, by0), (bx0, by1), (bx0 - f, by1 - f), (bx1 - f, by0 - f)][side]
        sq.append((x, y, f))
        bx0, by0, bx1, by1 = min(bx0, x), min(by0, y), max(bx1, x + f), max(by1, y + f)

    # the spiral: in each square a quarter circle centred on one corner, joined end to end, turning one way
    def chain(k, start):
        if k == len(sq):
            return []
        x, y, f = sq[k]
        corners = [(x, y), (x + f, y), (x + f, y + f), (x, y + f)]
        for ci, (cx, cy) in enumerate(corners):
            for a, b in ((1, 3), (3, 1)):
                p0, p1 = corners[(ci + a) % 4], corners[(ci + b) % 4]
                a0 = math.atan2(p0[1] - cy, p0[0] - cx)
                turn = (math.atan2(p1[1] - cy, p1[0] - cx) - a0 + math.pi) % (2 * math.pi) - math.pi
                if (start is None or p0 == start) and turn > 0:
                    rest = chain(k + 1, p1)
                    if rest is not None:
                        return [(cx, cy, f, a0, turn)] + rest
        return None
    arcs = chain(0, None)
    # turn it on its side (21 wide, 13 tall) and centre it; unit corners land on tile centres
    sq = [(y, x, f) for (x, y, f) in sq]
    arcs = [(cy, cx, f, math.pi / 2 - a0, -turn) for (cx, cy, f, a0, turn) in arcs]
    bx0, by0, bx1, by1 = by0, bx0, by1, bx1
    u = 2.0
    offx = (W - u * (bx1 - bx0)) / 2 - u * bx0 - 0.5
    offy = (H - u * (by1 - by0)) / 2 - u * by0 - 0.5
    # the squares, small to large; inside the arc a paler tone of the square's colour
    looks = [(LAPIS, 0.0, 0.0), (FERN, 0.0, 0.0), (SAFFRON, T2, T3), (PEARL, 0.0, T1), (FERN, T1, T2),
             (LAPIS, T1, T2), (SAFFRON, 0.0, T1)]
    for (x, y, f), (fam, t_in, t_out), (ax, ay, _, _, _) in zip(sq, looks, arcs):
        m = rect(c, offx + u * x, offy + u * y, offx + u * (x + f), offy + u * (y + f))
        inside = np.hypot(X - offx - u * ax, Y - offy - u * ay) < u * f
        c.paint(m, fam, t_out)
        c.paint(m & inside, fam, t_in)
    # thin dark outlines round every square, then the bold spiral over them in one unbroken curl
    for (x, y, f) in sq:
        x0, y0, x1, y1 = offx + u * x, offy + u * y, offx + u * (x + f), offy + u * (y + f)
        ring = rect(c, x0 - 0.5, y0 - 0.5, x1 + 0.5, y1 + 0.5) & ~rect(c, x0 + 0.5, y0 + 0.5, x1 - 0.5, y1 - 0.5)
        c.paint(ring, UMBER, T2, 1.4)
    line = np.zeros_like(X, bool)
    for (ax, ay, f, a0, turn) in arcs:
        pts = [(offx + u * (ax + f * math.cos(a0 + turn * t / 24)), offy + u * (ay + f * math.sin(a0 + turn * t / 24)))
               for t in range(25)]
        line |= c.line_mask(pts, 1.5)
    c.paint(line, EMBER, T3, 1.6)
    frame(c)
    return encode(c.to_tiles())


def mandelbrot():
    """The Mandelbrot set by escape time: the dark cardioid-and-bulbs body, ringed by smooth colour bands
    (deep blue far out, through white and gold to red at the edge of the set)."""
    W, H = 46, 40
    c = Canvas(W, H)
    X, Y = c.X, c.Y
    # the view: real part -2.04 .. 0.68, imaginary part -1.18 .. 1.18, so the whole set fits with
    # its tail pointing left and the top and bottom bulbs just short of the frame
    cxv, scale = -0.68, 2.72 / W
    cc = cxv + (X - W / 2) * scale + 1j * (Y - H / 2) * scale
    # iterate z -> z^2 + c on every pixel; record when (and how smoothly) each point escapes
    z = np.zeros_like(cc)
    mu = np.full(X.shape, -1.0)
    alive = np.ones(X.shape, bool)
    for n in range(200):
        z[alive] = z[alive] ** 2 + cc[alive]
        esc = alive & (np.abs(z) > 4.0)
        mu[esc] = n + 1 - np.log(np.log(np.abs(z[esc]))) / math.log(2)     # smooth escape time
        alive &= ~esc
    # colour bands by escape time, from deep blue far out to red at the edge of the set
    bands = [(-1e9, LAPIS, T3), (2.4, LAPIS, T2), (3.3, LAPIS, T1), (4.3, PEARL, 0.0), (5.6, SAFFRON, 0.0),
             (7.2, SAFFRON, T1), (9.5, EMBER, T1)]
    for lo, fam, tone in bands:
        c.paint(mu >= lo, fam, tone)
    c.paint(mu < 0, UMBER, T3)                       # the set itself
    frame(c)
    return encode(c.to_tiles())


# ---------------------------------------------------------------------------
# Challenge
# ---------------------------------------------------------------------------

def sierpinski():
    """The Sierpinski triangle to depth four: 27 solid triangles, each showing its own fourth-level hole
    as a paler inverted triangle, and the holes of the three larger levels in white. A solid's colour
    is set by its corner within its parent (so touching solids always differ), its tone by its corner
    of the big triangle. Solids are drawn a shade oversize so neighbouring holes never touch. The
    triangle stands on the bottom edge and pokes into the top one, splitting the blue ground in two."""
    W, H = 48, 40
    c = Canvas(W, H)
    c.paint(ALL(c), LAPIS, T3)
    S = (H - 0.7) / (math.sqrt(3) / 2)
    A, B = (W / 2 - S / 2, H - 1.0), (W / 2 + S / 2, H - 1.0)
    C = (W / 2, H - 1.0 - S * math.sqrt(3) / 2)

    def mid(p, q):
        return ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2)

    def grow(tri, d):
        """Push each vertex of a triangle d tiles further from its centre."""
        gx, gy = sum(p[0] for p in tri) / 3, sum(p[1] for p in tri) / 3
        out = []
        for (x, y) in tri:
            r = math.hypot(x - gx, y - gy)
            out.append((gx + (x - gx) * (r + d) / r, gy + (y - gy) * (r + d) / r))
        return out
    # the whole triangle is paper; the three levels of holes are left showing it
    c.paint(c.poly_mask([A, B, C]), PEARL, 0.0)
    c.paint(c.poly_mask([mid(A, B), mid(B, C), mid(C, A)]), PEARL, T1, 1.1)
    solids = [((A, B, C), ())]
    for level in range(3):
        nxt = []
        for (p, q, r), addr in solids:
            ab, bc, ca = mid(p, q), mid(q, r), mid(r, p)
            nxt += [((p, ab, ca), addr + (0,)), ((ab, q, bc), addr + (1,)), ((ca, bc, r), addr + (2,))]
        solids = nxt
    fams = [EMBER, FERN, SAFFRON]
    for (p, q, r), addr in solids:
        fam = fams[addr[2]]
        tone = [T1, T2, T2][addr[0]] if fam != SAFFRON else [0.0, T1, T1][addr[0]]
        c.paint(c.poly_mask(grow((p, q, r), 0.6)), fam, tone, 1.3)
        c.paint(c.poly_mask([mid(p, q), mid(q, r), mid(r, p)]), fam, max(0.0, tone - T1) if tone > 0 else 0.0, 1.3)
    frame(c)
    return encode(c.to_tiles())


def hilbert_points(order):
    """Grid points of the Hilbert curve of the given order, in path order (x right, y up)."""
    n = 2 ** order
    pts = []
    for d in range(n * n):
        x = y = 0
        t, s = d, 1
        while s < n:
            rx = 1 & (t // 2)
            ry = 1 & (t ^ rx)
            if ry == 0:
                if rx == 1:
                    x, y = s - 1 - x, s - 1 - y
                x, y = y, x
            x, y = x + s * rx, y + s * ry
            t //= 4
            s *= 2
        pts.append((x, y))
    return pts


def hilbert():
    """The Hilbert curve of order four: 256 grid points joined into one path, drawn one tile wide on a
    dark ground with a one-tile gap, in a pale mat. The colour runs red, gold, green, blue round and
    round along its length (a new colour every 16 path tiles), a shade deeper in each quarter of the
    curve, and the mat cuts the dark ground into separate fingers."""
    W = H = 41
    c = Canvas(W, H)
    tx, ty = tiles_of(c)
    order, run = 4, 16
    n = 2 ** order
    span = 2 * n - 1
    x0, y0 = (W - span) // 2, (H - span) // 2
    c.paint(ALL(c), PEARL, T1)
    ring = np.maximum(np.abs(tx - (x0 + span // 2)), np.abs(ty - (y0 + span // 2))) == span // 2 + 2
    c.paint(ring, LAPIS, T3)                                         # a thin line round the mat's window
    c.paint((tx >= x0) & (tx < x0 + span) & (ty >= y0) & (ty < y0 + span), UMBER, T3)
    pts = [(x0 + 2 * px, y0 + 2 * (n - 1 - py)) for (px, py) in hilbert_points(order)]
    # walk the path tile by tile, numbering the tiles
    walk = np.full((H, W), -1)
    k = 0
    for (ax, ay), (bx, by) in zip(pts[:-1], pts[1:]):
        for (x, y) in ((ax, ay), ((ax + bx) // 2, (ay + by) // 2)):
            walk[y, x] = k
            k += 1
    walk[pts[-1][1], pts[-1][0]] = k
    idx = walk[ty, tx]
    cycle = [EMBER, SAFFRON, FERN, LAPIS]
    quarter_tone = [0.0, T1, T1, T2]
    for q in range(4):
        for j, fam in enumerate(cycle):
            m = (idx >= 0) & ((idx // run) % 4 == j) & (idx * 4 // (k + 1) == q)
            c.paint(m, fam, quarter_tone[q] if fam != SAFFRON else quarter_tone[q] * 0.5)
    frame(c)
    return encode(c.to_tiles())


def cafe_wall():
    """The cafe wall illusion: rows of alternating dark and light bricks, each row shifted half a brick
    against the next, between thin mid-grey mortar lines -- the mortar lines seem to slope. The light
    bricks take a different pale colour on each row; a mortar margin keeps the bricks off the frame."""
    W, H = 46, 43
    c = Canvas(W, H)
    tx, ty = tiles_of(c)
    # tile-aligned so every brick and mortar line is crisp: bricks 8 x 4 tiles, mortar one tile thick
    # (thin against the brick height, as the illusion needs)
    lb, bh = 8, 4                                   # brick length and height in tiles
    # eight courses of bricks, each over a one-tile mortar line, inside a one-tile mortar margin
    row = (ty - 2) // (bh + 1)
    mortar = ((ty - 2) % (bh + 1)) == bh
    wall = (tx >= 2) & (tx < W - 2) & (ty >= 2) & (ty < H - 2)
    # every other course is shifted by half a brick; dark and light bricks alternate along a course
    brick = (tx - 2 + (row % 2) * lb // 2) // lb
    is_dark = (brick % 2) == 0
    c.paint(ALL(c), PEARL, T3)                      # the mid-grey mortar
    light = [SAFFRON, LAPIS, FERN]                  # pale bricks: a different colour on each course
    for k, fam in enumerate(light):
        c.paint(wall & ~mortar & ~is_dark & (row % 3 == k), fam, 0.0)
    c.paint(wall & ~mortar & is_dark, UMBER, T3)    # dark bricks
    frame(c)
    return encode(c.to_tiles())


# ---------------------------------------------------------------------------
# Master
# ---------------------------------------------------------------------------

def knot_strands(nx, ny, breaks):
    """Trace the closed strands of a knotwork grid. Crossing points are the grid points (i, j) with
    i + j odd; strands run diagonally from one to the next and turn back at the panel edge and at
    'breaks' ({(i, j): 'h' or 'v'}, a wall at that point). Returns, per strand, its points in order
    as (point, is_crossing, direction)."""
    def turn(p):
        return p[0] in (0, nx) or p[1] in (0, ny) or p in breaks
    used, strands = set(), []
    for p0 in [(i, j) for i in range(1, nx) for j in range(1, ny) if (i + j) % 2 and (i, j) not in breaks]:
        for d0 in ((1, 1), (1, -1)):
            if (p0, d0[0] * d0[1]) in used:
                continue
            path, p, d = [], p0, d0
            while turn(p) or (p, d[0] * d[1]) not in used:
                if not turn(p):
                    used.add((p, d[0] * d[1]))
                path.append((p, not turn(p), d))
                q = (p[0] + d[0], p[1] + d[1])
                dx, dy = d
                if q in breaks:
                    dx, dy = (-dx, dy) if breaks[q] == 'v' else (dx, -dy)
                else:
                    dx = -dx if q[0] in (0, nx) else dx
                    dy = -dy if q[1] in (0, ny) else dy
                p, d = q, (dx, dy)
            strands.append(path)
    return strands


def knot_curve(path, steps=8):
    """A closed smooth curve through a strand: straight through crossings, and a Bezier with the turn
    points as control points wherever the strand bounces off an edge or a break."""
    k0 = next(k for k, e in enumerate(path) if e[1])
    path = path[k0:] + path[:k0]
    out, k, n = [], 0, len(path)
    while k < n:
        ctrl, m = [path[k][0]], k + 1
        while not path[m % n][1]:
            ctrl.append(path[m % n][0])
            m += 1
        ctrl.append(path[m % n][0])
        for t in np.linspace(0, 1, steps * (len(ctrl) - 1), endpoint=False):
            pts = list(ctrl)
            while len(pts) > 1:
                pts = [((1 - t) * a[0] + t * b[0], (1 - t) * a[1] + t * b[1]) for a, b in zip(pts[:-1], pts[1:])]
            out.append(pts[0])
        k = m
    return out + [out[0]]


def celtic_knot():
    """A knotwork panel: four corner knots, each one strand, bound together by a red strand that loops
    through all of them round an open centre. Bands go alternately over and under at every crossing
    (the under band darkens where it dives); dark ground shows between; a gold border set with
    coloured jewels."""
    W = H = 44
    c = Canvas(W, H)
    n, u, w = 8, 4.65, 3.45
    # walls that turn the strands back: a ring round the centre and a gap at the middle of each side
    breaks = {(4, 1): 'v', (4, 7): 'v', (1, 4): 'h', (7, 4): 'h', (4, 3): 'h', (4, 5): 'h', (3, 4): 'v', (5, 4): 'v'}
    ox, oy = (W - n * u) / 2, (H - n * u) / 2

    def P(p):
        return (ox + p[0] * u, oy + p[1] * u)
    c.paint(ALL(c), UMBER, T3)
    strands = knot_strands(n, n, breaks)
    # the strand that reaches every quarter is red; each corner knot takes its own colour
    fam = {}
    for k, st in enumerate(strands):
        xs, ys = [q[0][0] for q in st], [q[0][1] for q in st]
        if max(xs) - min(xs) > n * 0.6 and max(ys) - min(ys) > n * 0.6:
            fam[k] = EMBER
        else:
            fam[k] = [[SAFFRON, LAPIS], [FERN, PEARL]][int(np.mean(ys) > n / 2)][int(np.mean(xs) > n / 2)]
    look = {FERN: T1, EMBER: T1, SAFFRON: 0.0, LAPIS: T1, PEARL: 0.0}
    for k, st in enumerate(strands):
        c.paint(c.line_mask([P(q) for q in knot_curve(st)], w), fam[k], look[fam[k]], 1.2)

    def bar(p, d, half_len, half_w):
        (px, py), (dx, dy) = P(p), (d[0] / math.sqrt(2), d[1] / math.sqrt(2))
        return c.poly_mask([(px + dx * half_len - dy * half_w, py + dy * half_len + dx * half_w),
                            (px + dx * half_len + dy * half_w, py + dy * half_len - dx * half_w),
                            (px - dx * half_len + dy * half_w, py - dy * half_len - dx * half_w),
                            (px - dx * half_len - dy * half_w, py - dy * half_len + dx * half_w)])
    # at every crossing: the under band darkens as it dives, the over band passes on top
    for k, st in enumerate(strands):
        for (p, cross, d) in st:
            if cross and (p[0] % 2 == 0) == (d[0] * d[1] > 0):
                c.paint(bar(p, d, w / 2 + 1.4, w / 2), fam[k], look[fam[k]] + T1, 1.3)
    for k, st in enumerate(strands):
        for (p, cross, d) in st:
            if cross and (p[0] % 2 == 0) != (d[0] * d[1] > 0):
                c.paint(bar(p, d, w / 2 + 0.6, w / 2 + 0.05), fam[k], look[fam[k]], 1.4)
    # border: a gold band set with coloured jewels that cut it into short lengths
    tx, ty = tiles_of(c)
    ring = np.minimum.reduce([tx, W - 1 - tx, ty, H - 1 - ty])
    band = (ring >= 1) & (ring <= 2)
    horiz = np.minimum(ty, H - 1 - ty) <= np.minimum(tx, W - 1 - tx)
    pos = np.where(horiz, tx, ty) - (W // 2 - 1)
    side = np.where(horiz, np.where(ty < H / 2, 0, 2), np.where(tx < W / 2, 3, 1))
    c.paint(band, SAFFRON, T1)
    jewel = band & ((pos % 7) < 2)
    corner = band & (np.minimum(tx, W - 1 - tx) <= 2) & (np.minimum(ty, H - 1 - ty) <= 2)
    jfam = [EMBER, LAPIS, FERN, PEARL]
    for k, f in enumerate(jfam):
        c.paint(jewel & ~corner & ((pos // 7 + side) % 4 == k), f, T1 if f != PEARL else 0.0, 1.3)
    c.paint(corner, EMBER, T2, 1.3)
    frame(c)
    return encode(c.to_tiles())


D18, D36 = math.radians(18), math.radians(36)
GR_R = 1 / (2 * math.sin(D18))                 # decagon circumradius (edge 1)
GR_H = 2 * math.sin(D36)                       # elongated hexagon height
GR_A = GR_H / 2 + 1 / (2 * math.tan(D18))      # decagon centre to hexagon centre


def girih_tiles(x0, x1, y0, y1):
    """A periodic girih tiling with edge 1: regular decagons on the lattice (0, 2A) and 2A(cos18, sin18),
    an elongated hexagon between each pair of neighbouring decagons, and four bow ties per cell
    filling the rest (their places were found by fitting bow ties into the 72-degree gaps)."""
    v1, v2 = (0.0, 2 * GR_A), (2 * GR_A * math.cos(D18), 2 * GR_A * math.sin(D18))
    c36, c18, s18 = math.cos(D36), math.cos(D18), math.sin(D18)
    hexagon = [(-0.5 - c36, 0), (-0.5, -GR_H / 2), (0.5, -GR_H / 2), (0.5 + c36, 0), (0.5, GR_H / 2), (-0.5, GR_H / 2)]
    bowtie = [(-c18, -0.5), (0, -0.5 + s18), (c18, -0.5), (c18, 0.5), (0, 0.5 - s18), (-c18, 0.5)]

    def place(shape, cx, cy, ang):
        ca, sa = math.cos(ang), math.sin(ang)
        return [(cx + x * ca - y * sa, cy + x * sa + y * ca) for x, y in shape]
    out = []
    for m in range(-12, 13):
        for n in range(-12, 13):
            cx, cy = m * v1[0] + n * v2[0], m * v1[1] + n * v2[1]
            if not (x0 - 6 < cx < x1 + 6 and y0 - 6 < cy < y1 + 6):
                continue
            out.append(("decagon", [(cx + GR_R * math.cos(k * D36), cy + GR_R * math.sin(k * D36)) for k in range(10)]))
            for deg in (90, 18):
                t = math.radians(deg)
                out.append(("hexagon", place(hexagon, cx + GR_A * math.cos(t), cy + GR_A * math.sin(t), t + math.pi / 2)))
            qx, qy = cx + GR_R * c36 + s18 / 2, cy + 1 / (2 * math.tan(D18)) + c18 / 2
            for (dx, dy) in ((0, 0), (0, GR_H), (GR_H * c18, GR_H * s18), (GR_H * c18, GR_H + GR_H * s18)):
                out.append(("bowtie", place(bowtie, qx + dx, qy + dy, 3 * D18)))
    return out


def _inside(poly, x, y, eps=1e-7):
    inside = False
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        if abs((x2 - x1) * (y - y1) - (y2 - y1) * (x - x1)) < eps and \
                min(x1, x2) - eps <= x <= max(x1, x2) + eps and min(y1, y2) - eps <= y <= max(y1, y2) + eps:
            return True
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


def hankin(poly, contact=D36):
    """Girih strapwork for one tile (Hankin's polygons-in-contact): from every edge midpoint two rays
    leave at `contact` either side of the inward normal; rays are paired off nearest-first where they
    meet inside the tile. Returns the line segments."""
    n = len(poly)
    turn = sum(poly[i][0] * poly[(i + 1) % n][1] - poly[(i + 1) % n][0] * poly[i][1] for i in range(n))
    rays = []
    for i in range(n):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % n]
        ln = math.hypot(x2 - x1, y2 - y1)
        nx, ny = -(y2 - y1) / ln * math.copysign(1, turn), (x2 - x1) / ln * math.copysign(1, turn)
        for sgn in (1, -1):
            ca, sa = math.cos(sgn * contact), math.sin(sgn * contact)
            rays.append((i, ((x1 + x2) / 2, (y1 + y2) / 2), (nx * ca - ny * sa, nx * sa + ny * ca)))
    meets = []
    for p in range(len(rays)):
        for q in range(p + 1, len(rays)):
            (i, (ax, ay), (adx, ady)), (j, (bx, by), (bdx, bdy)) = rays[p], rays[q]
            det = -adx * bdy + ady * bdx
            if i == j:
                continue
            if abs(det) < 1e-9:                    # collinear rays running at each other
                ex, ey = bx - ax, by - ay
                if abs(ex * ady - ey * adx) < 1e-6 and ex * adx + ey * ady > 0 and adx * bdx + ady * bdy < 0:
                    meets.append((math.hypot(ex, ey), p, q, ((ax + bx) / 2, (ay + by) / 2)))
                continue
            s = (-(bx - ax) * bdy + (by - ay) * bdx) / det
            t = (adx * (by - ay) - ady * (bx - ax)) / det
            if s > 1e-6 and t > 1e-6 and _inside(poly, ax + s * adx, ay + s * ady):
                meets.append((s + t, p, q, (ax + s * adx, ay + s * ady)))
    used, segs = set(), []
    for _, p, q, X in sorted(meets):
        if p not in used and q not in used:
            used |= {p, q}
            segs += [(rays[p][1], X), (rays[q][1], X)]
    return segs


def girih_star():
    """A ten-fold girih pattern: the strapwork of a periodic girih tiling (decagons, elongated hexagons
    and bow ties; Hankin's construction with the straps leaving each edge midpoint at 28 degrees to
    the normal), drawn as white straps at a scale where one star fills the middle. The ten-pointed
    gold star with its red heart sits in a decagon, ringed by petals alternately green and red; deep
    blue barrels, dark diamonds (bow-tie pairs) and little gold chips fill the rest."""
    W = H = 44
    c = Canvas(W, H)
    e, sw = 8.0, 1.05                               # tiles per girih edge, strap width in tiles
    ss, pad = 8, 10                                 # pixels per tile, margin tiles
    cx0, cy0 = W / 2, H / 2                         # a star in the middle
    tiles = girih_tiles(-(W / 2 + pad) / e, (W / 2 + pad) / e, -(H / 2 + pad) / e, (H / 2 + pad) / e)
    segs = [sg for _, poly in tiles for sg in hankin(poly, math.radians(28))]
    size = ((W + 2 * pad) * ss, (H + 2 * pad) * ss)

    def to_px(p):                                  # girih units (y up) -> padded pixels
        return ((pad + cx0 + p[0] * e) * ss, (pad + cy0 - p[1] * e) * ss)

    def strap_mask(width):
        img = Image.new("L", size, 0)
        d = ImageDraw.Draw(img)
        for p, q in segs:
            d.line([to_px(p), to_px(q)], fill=255, width=max(1, int(round(width * ss))))
        return np.array(img) > 0

    def crop(a):
        return a[pad * ss:(pad + H) * ss, pad * ss:(pad + W) * ss]
    # classify the faces of the strap net (with hairline straps) by their full area in girih units
    lab, n = ndimage.label(~strap_mask(0.15))
    area = np.bincount(lab.ravel()) / (e * ss) ** 2
    lab = crop(lab)
    kind = np.select([area[lab] > 3, area[lab] > 0.8, area[lab] > 0.5, area[lab] > 0.25], [4, 3, 2, 1], 0)
    # petals take green or red by their place round the nearest star, so the star wears a two-colour halo
    rows, cols = np.nonzero(np.ones(lab.shape, bool))
    flat = lab.ravel()
    cnt = np.bincount(flat, minlength=lab.max() + 1)
    my = np.bincount(flat, weights=rows / ss, minlength=lab.max() + 1) / np.maximum(cnt, 1)
    mx = np.bincount(flat, weights=cols / ss, minlength=lab.max() + 1) / np.maximum(cnt, 1)
    centres = [(cx0 + sum(p[0] for p in poly) / 10 * e, cy0 - sum(p[1] for p in poly) / 10 * e)
               for _, poly in tiles if len(poly) == 10]
    side = np.zeros(len(cnt), int)
    for k in range(len(cnt)):
        sx, sy = min(centres, key=lambda q: (q[0] - mx[k]) ** 2 + (q[1] - my[k]) ** 2)
        side[k] = int(math.floor((math.atan2(my[k] - sy, mx[k] - sx) + math.pi / 2) / D36)) % 2
    alt = side[lab] == 1
    c.paint(ALL(c), SAFFRON, T2)                                     # tiny triangles: gold chips
    c.paint(kind == 1, UMBER, T2)                                    # small diamonds
    c.paint((kind == 2) & alt, FERN, T1)                             # petals
    c.paint((kind == 2) & ~alt, EMBER, T1)
    c.paint(kind == 3, LAPIS, T3)                                    # barrels
    c.paint(kind == 4, SAFFRON, T1)                                  # ten-pointed stars
    # a small red rosette in the heart of every star
    for (hx, hy) in centres:
        ang = np.arctan2(c.Y - hy, c.X - hx)
        heart = np.hypot(c.X - hx, c.Y - hy) < (0.33 + 0.12 * np.abs(np.cos(5 * (ang - math.pi / 2)))) * e
        c.paint(heart & (kind == 4), EMBER, T2, 1.2)
    c.paint(crop(strap_mask(sw)), PEARL, 0.0, 1.15)                 # the white strapwork on top
    frame(c)
    return encode(c.to_tiles())


SCENES = {
    "triangle": impossible_triangle,
    "spiral": golden_spiral,
    "mandelbrot": mandelbrot,
    "sierpinski": sierpinski,
    "hilbert": hilbert,
    "cafewall": cafe_wall,
    "knot": celtic_knot,
    "girih": girih_star,
}
