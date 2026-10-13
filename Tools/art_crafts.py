"""World Craft pack: eight tile pictures of traditional crafts and patterns from around the world, drawn
respectfully as everyday folk art with the same supersampled Canvas as art.py.

Gentle: a Talavera plate from Puebla (44 x 44), a Polish wycinanki paper cut (46 x 40), three Ukrainian
pysanky eggs (48 x 38), a panel of Delft tiles above a kitchen shelf (41 x 48).
Challenge: a kimono with the asanoha (hemp-leaf) pattern on its stand (42 x 46), an original woven
tartan swatch with a fringe (44 x 44).
Master: an American patchwork quilt of eight-point stars (44 x 44), a Persian medallion carpet (34 x 48).
"""
import math

import numpy as np

from art import Canvas, LAPIS, SAFFRON, FERN, EMBER, UMBER, PEARL, encode
from art_scenes import ALL, ellipse, rect, tube, frame


T1, T2, T3 = 1 / 3, 2 / 3, 1.0   # exact tones: flat areas come out without dither speckle


def tiles_of(c):
    """Tile-aligned coordinates (column, row) for crisp grid patterns."""
    return np.floor(c.X).astype(int), np.floor(c.Y).astype(int)


def petal(c, cx, cy, ang, r0, r1, w, fat=1.7):
    """A radial teardrop from radius r0 to r1 at angle `ang`, widest (w) toward its outer end when
    fat > 1, toward its inner end when fat < 1."""
    dx, dy = math.cos(ang), math.sin(ang)
    u = ((c.X - cx) * dx + (c.Y - cy) * dy - r0) / (r1 - r0)
    p = -(c.X - cx) * dy + (c.Y - cy) * dx
    s = np.clip(u, 0, 1) ** fat
    return (u >= 0) & (u <= 1) & (np.abs(p) <= w * np.sqrt(np.clip(s * (1 - s), 0, None)))


def egg_space(c, cx, cy, rx, ry, ang=0.0):
    """An egg (narrow end up, tilted by `ang`): returns (mask, u, v) with u across (-1..1) and v along
    the long axis (-1 at the narrow top, +1 at the round bottom). Evaluated at tile centres, so every
    band and motif on the shell comes out crisp."""
    ca, sa = math.cos(ang), math.sin(ang)
    dx, dy = np.floor(c.X) + 0.5 - cx, np.floor(c.Y) + 0.5 - cy
    v = (-dx * sa + dy * ca) / ry
    u = (dx * ca + dy * sa) / rx / (1 + 0.16 * v)
    return u * u + v * v <= 1.0, u, v


def star8(u, v, R, r):
    """Mask of an 8-point star (tips at radius R, inner corners at r) in offsets (u, v)."""
    rho, th = np.hypot(u, v), np.arctan2(v, u)
    phi = np.abs(((th + math.pi / 8) % (math.pi / 4)) - math.pi / 8)
    x, y = rho * np.cos(phi), rho * np.sin(phi)
    ex, ey = r * math.cos(math.pi / 8) - R, r * math.sin(math.pi / 8)
    return (x - R) * ey - y * ex <= 0


def grid_canvas(W, H):
    """Tile-grid drawing: returns (xs, ys, fam, tone) arrays of shape (H, W) to fill directly."""
    ys, xs = np.mgrid[0:H, 0:W]
    return xs, ys, np.full((H, W), PEARL), np.zeros((H, W))


def grid_paint(c, fam, tone):
    """Paints tile-grid arrays onto the canvas (every pixel of a tile gets that tile's value)."""
    F = np.repeat(np.repeat(fam, 8, axis=0), 8, axis=1)
    T = np.repeat(np.repeat(tone, 8, axis=0), 8, axis=1)
    for f in range(6):
        c.paint(F == f, f, T)


def edge8(m, diagonal=True):
    """The tiles of a tile-grid mask that touch a tile outside it - also diagonally (a thicker outline
    that stays connected side to side along diagonal edges), or only side to side (a thin one)."""
    inner = m.copy()
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if diagonal or dx == 0 or dy == 0:
                inner &= np.roll(np.roll(m, dy, axis=0), dx, axis=1)
    return m & ~inner


# ---------------------------------------------------------------------------
# Gentle
# ---------------------------------------------------------------------------

def talavera_plate():
    """Talavera poblana (Puebla, Mexico): a round tin-glazed plate with bold raised cobalt petals round a
    yellow-and-orange flower, yellow drops between the petals, small green leaves at the heart and a
    scalloped cobalt rim; lying on a planked wooden table."""
    c = Canvas(44, 44)
    X, Y = c.X, c.Y
    cx, cy = 22.0, 22.0
    R, A = np.hypot(X - cx, Y - cy), np.arctan2(Y - cy, X - cx)
    # the table: broad planks told apart by tone only
    plank = np.floor((X + 3) / 9).astype(int) % 2
    c.paint(ALL(c), UMBER, np.where(plank == 0, T1, T2))
    c.paint(((X + 3) % 9) < 0.5, UMBER, T3)
    # the plate, its shadow and its pale lip
    c.paint(c.circle(cx + 0.9, cy + 1.1, 19.8), UMBER, T3)
    c.paint(R < 19.6, PEARL, T1)
    c.paint(R < 18.4, PEARL, 0.0)
    # scalloped cobalt rim: sixteen arches hanging inward
    inner = 15.8 - 1.2 * np.abs(np.sin(A * 8))
    c.paint((R < 18.0) & (R > inner), LAPIS, T3, 1.2)
    # eight big cobalt petals with a lighter vein
    for k in range(8):
        a = k * math.pi / 4
        c.paint(petal(c, cx, cy, a, 4.6, 12.8, 6.6), LAPIS, T3, 1.3)
        c.paint(petal(c, cx, cy, a, 6.4, 11.6, 2.2), LAPIS, T1, 1.35)
    # yellow drops between the petals, deep orange at their hearts; green leaves at the heart
    for k in range(8):
        a = (k + 0.5) * math.pi / 4
        c.paint(petal(c, cx, cy, a, 8.4, 13.4, 4.6), SAFFRON, T1, 1.3)
        c.paint(petal(c, cx, cy, a, 10.2, 12.8, 2.0), SAFFRON, T3, 1.35)
        c.paint(petal(c, cx, cy, a, 4.0, 8.2, 3.0, 0.8), FERN, T2, 1.3)
    # the central flower
    c.paint(R < 4.8, SAFFRON, T1, 1.4)
    c.paint(R < 4.8 - 1.0 * np.abs(np.sin(A * 4)), SAFFRON, T2, 1.4)
    c.paint(R < 2.3, EMBER, T2, 1.5)
    frame(c)
    return encode(c.to_tiles())


def wycinanki():
    """A Polish folk paper cut (wycinanki, Lowicz style): two roosters face each other across a tree
    of flowers, cut from bright layered paper and pasted on white, standing on a scalloped green
    strip. Mirror-symmetric."""
    c = Canvas(46, 40)
    X, Y = c.X, c.Y
    mx = 23.0
    c.paint(ALL(c), PEARL, 0.0)
    # scalloped green ground strip
    bump = np.sqrt(np.clip(1 - (((X - mx) % 4) / 2 - 1) ** 2, 0, 1))
    c.paint(Y > 34.6 - 1.1 * bump, FERN, T2)
    c.paint(Y > 36.8, FERN, T3)
    # the tree: stem, paired leaves, two tulips on curling branches, a big rosette on top
    c.paint(c.line_mask([(mx, 35.0), (mx, 8.0)], 1.4), FERN, T3, 1.3)
    for s in (-1, 1):
        for ly in (20.5, 25.5, 30.5):
            c.paint(ellipse(c, mx + s * 2.9, ly, 3.0, 1.15, -s * 0.5), FERN, T1, 1.3)
        c.paint(tube(c, [(mx, 18.0), (mx + s * 2.8, 16.5), (mx + s * 4.2, 13.4)], 0.9, 0.8), FERN, T3, 1.3)
        tx, ty = mx + s * 4.4, 11.4
        cup = ellipse(c, tx, ty, 1.9, 1.8) | c.poly_mask([(tx - 1.9, ty), (tx - 1.6, ty - 2.6), (tx - 0.6, ty - 1.2),
                                                          (tx, ty - 2.9), (tx + 0.6, ty - 1.2), (tx + 1.6, ty - 2.6),
                                                          (tx + 1.9, ty)])
        c.paint(cup, LAPIS, T2, 1.4)
        c.paint(ellipse(c, tx, ty + 0.3, 0.8, 1.1), SAFFRON, T1, 1.5)
    for k in range(8):
        a = k * math.pi / 4
        c.paint(c.circle(mx + 3.0 * math.cos(a), 5.6 + 3.0 * math.sin(a), 1.5), EMBER, T2, 1.4)
    c.paint(c.circle(mx, 5.6, 2.4), SAFFRON, T1, 1.5)
    c.paint(c.circle(mx, 5.6, 1.2), LAPIS, T2, 1.6)
    # the roosters (s = -1 left, +1 right), heads toward the tree; d is the distance from the middle
    for s in (-1, 1):
        d = s * (X - mx)

        def P(dx, y):
            return (mx + s * dx, y)
        # the tail: a fan of three feather bands, each cut with a serrated edge
        rr, th = np.hypot(d - 14.8, Y - 20.0), np.arctan2(Y - 20.0, d - 14.8)
        fan = (th > -1.95) & (th < 0.45)
        for (r0, r1, fam) in ((2.2, 4.3, LAPIS), (4.3, 6.3, SAFFRON), (6.3, 8.2, FERN)):
            edge = r1 + 0.35 * np.cos(th * 16)
            c.paint(fan & (rr >= r0) & (rr < edge), fam, np.where(np.sin(th * 16) > 0, T1, T2), 1.2)
        # body, breast, neck and head in red paper
        body = ellipse(c, *P(14.2, 25.6), 5.6, 4.1, -s * 0.3) | c.circle(*P(10.8, 23.6), 3.4)
        body |= c.poly_mask([P(9.6, 22.4), P(8.3, 16.6), P(11.0, 15.6), P(12.8, 21.4)]) | c.circle(*P(9.9, 15.8), 2.0)
        c.paint(body, EMBER, T2, 1.3)
        for k, dx in enumerate((9.0, 10.1, 11.2)):
            c.paint(c.circle(*P(dx, 13.6 - 0.5 * (k == 1)), 0.95), EMBER, T3, 1.4)
        c.paint(c.poly_mask([P(8.2, 15.1), P(8.2, 16.7), P(6.5, 15.9)]), SAFFRON, T2, 1.5)
        c.paint(ellipse(c, *P(9.0, 18.2), 0.75, 1.15), EMBER, T3, 1.5)
        c.paint(c.circle(*P(9.8, 15.5), 0.5), UMBER, T3, 1.8)
        # the wing: blue paper with a yellow layer
        c.paint(ellipse(c, *P(14.8, 25.2), 3.7, 2.5, -s * 0.25), LAPIS, T2, 1.4)
        c.paint(ellipse(c, *P(14.0, 25.0), 2.1, 1.3, -s * 0.25), SAFFRON, T1, 1.5)
        for dx in (12.5, 15.5):
            c.paint(c.line_mask([P(dx, 29.0), P(dx, 34.6)], 0.9), UMBER, T3, 1.4)
            c.paint(c.line_mask([P(dx - 1.2, 34.6), P(dx + 1.2, 34.6)], 0.8), UMBER, T3, 1.4)
    frame(c)
    return encode(c.to_tiles())


def pysanky():
    """Three Ukrainian pysanky standing together on an embroidered linen cloth, each written with a
    different design: a black egg with a red belt carrying the golden 'endless line'; a deep-red egg
    with a big golden eight-point star between black caps; a yellow egg parted by a red and black
    stripe from end to end, with an ear of wheat either side. A paler patch toward the light makes each egg round."""
    c = Canvas(48, 38)
    X, Y = c.X, c.Y
    tx, ty = tiles_of(c)
    # pale-blue wall, white linen with soft shadows and a red cross-stitched band
    c.paint(ALL(c), LAPIS, T1)
    c.paint(Y > 25.0, PEARL, 0.0)
    for (sx, sw) in ((9.2, 6.2), (24.4, 7.0), (39.6, 6.2)):
        c.paint(ellipse(c, sx, 29.2, sw, 1.4), PEARL, T2)
    band = (Y > 32.0) & (Y < 35.0)
    c.paint(band, EMBER, np.where(((tx + ty) % 3) == 0, T3, T2))

    def egg(cx, cy, rx, ry, ang, fam, tone, lit, sheen=0.34):
        m, u, v = egg_space(c, cx, cy, rx, ry, ang)
        c.paint(m, fam, np.where(np.hypot(u + 0.45, v + 0.36) < sheen, lit, tone), 1.1)
        return m, u, v
    # left: black, a red belt carrying the golden endless line
    m, u, v = egg(8.6, 19.6, 6.5, 9.1, -0.2, UMBER, T3, T2, 0.2)
    belt = np.abs(v - 0.05) < 0.27
    c.paint(m & belt, EMBER, T2, 1.3)
    c.paint(m & belt & (np.abs(v - 0.05 - 0.11 * np.sin(u * 7)) < 0.075), SAFFRON, T1, 1.4)
    # centre: deep red, a big golden eight-point star, black caps
    m, u, v = egg(24.0, 17.6, 7.2, 10.2, 0.0, EMBER, T3, T2)
    c.paint(m & (np.abs(v) > 0.78), UMBER, T3, 1.3)
    c.paint(m & star8(u, (v + 0.04) * 1.42, 0.8, 0.36), SAFFRON, T1, 1.4)
    c.paint(m & star8(u, (v + 0.04) * 1.42, 0.3, 0.16), EMBER, T1, 1.45)
    # right: yellow, a red stripe with black edges from end to end, an ear of wheat either side
    m, u, v = egg(39.4, 19.6, 6.5, 9.1, 0.2, SAFFRON, T1, 0.0)
    c.paint(m & (np.abs(u) < 0.36), UMBER, T3, 1.3)
    c.paint(m & (np.abs(u) < 0.2), EMBER, T2, 1.35)
    for side in (-1, 1):
        du, dv = (u - side * 0.69) * 6.5, (v + 0.02) * 9.1          # in tiles, from the ear's middle
        lean = du + side * 0.2 * dv
        c.paint(m & (np.abs(lean) < 0.5) & (dv > 0.6) & (dv < 4.4), FERN, T3, 1.4)
        c.paint(m & ((lean / 1.0) ** 2 + ((dv + 1.5) / 2.7) ** 2 < 1), FERN,
                np.where(np.floor(dv) % 2 == 0, T1, T2), 1.4)
    frame(c)
    return encode(c.to_tiles())


def bitmap(c, rows, x0, y0, fam, tones):
    """Paints a small pixel drawing (one character per tile) with its top-left tile at (x0, y0);
    `tones` maps characters to tones, other characters are left alone."""
    tx, ty = tiles_of(c)
    for j, row in enumerate(rows):
        for i, ch in enumerate(row):
            if ch in tones:
                c.paint((tx == x0 + i) & (ty == y0 + j), fam, tones[ch], 1.5)


DELFT = {
    "windmill": [".##...##.",
                 "..##.##..",
                 "...###...",
                 "..##+##..",
                 ".##+++##.",
                 "...+++...",
                 "..+++++..",
                 "..+++++..",
                 ".-------."],
    "ship": ["....#....",
             "....#+...",
             "....#++..",
             "...+#+++.",
             "..++#++++",
             ".+++#++++",
             "#########",
             ".#######.",
             "..-.-.-.."],
    "tulip": ["..#.#.#..",
              "..#####..",
              "..#####..",
              "...###...",
              "....#....",
              ".++.#.++.",
              "..++#++..",
              "...+#+...",
              "....#...."],
}


def delft_tiles():
    """A panel of nine Dutch Delft tiles in a wooden frame on an ochre kitchen wall: cobalt windmills,
    sailing boats and tulips on white glaze, the tiles told apart by a faint difference in the glaze,
    a small cobalt 'spider' wherever four tiles meet; below, a shelf with a copper kettle and a
    blue-and-white jug."""
    c = Canvas(41, 48)
    X, Y = c.X, c.Y
    tx, ty = tiles_of(c)
    c.paint(ALL(c), SAFFRON, T2)
    # the frame (lit along its top and left) and the nine tiles of 11 x 11
    fr = (tx >= 2) & (tx <= 38) & (ty >= 2) & (ty <= 38)
    c.paint(fr, UMBER, T2)
    c.paint(fr & ((tx == 2) | (ty == 2)), UMBER, T1)
    panel = (tx >= 4) & (tx <= 36) & (ty >= 4) & (ty <= 36)
    c.paint(panel, PEARL, np.where((((tx - 4) // 11 + (ty - 4) // 11) % 2) == 0, 0.0, T1))
    order = [["ship", "tulip", "windmill"], ["tulip", "windmill", "tulip"], ["windmill", "tulip", "ship"]]
    for j in range(3):
        for i in range(3):
            bitmap(c, DELFT[order[j][i]], 5 + 11 * i, 5 + 11 * j, LAPIS, {"#": T3, "+": T2, "-": T1})
    # spiders where four tiles meet: a 2 x 2 knot with four diagonal legs
    for gy in (15, 26):
        for gx in (15, 26):
            knot = (tx >= gx - 1) & (tx <= gx) & (ty >= gy - 1) & (ty <= gy)
            legs = (np.abs(tx - gx + 0.5) == 1.5) & (np.abs(ty - gy + 0.5) == 1.5)
            c.paint(knot | legs, LAPIS, T2, 1.5)
    # the shelf on two brackets
    c.paint((ty >= 45) & (ty <= 46) & (tx >= 1) & (tx <= 39), UMBER, T3)
    for bx in (6, 34):
        c.paint(c.poly_mask([(bx - 0.5, 47.0), (bx + 1.5, 47.0), (bx + 1.5, 47.6), (bx - 0.5, 47.6)]), UMBER, T3)
    # a copper kettle: round body, lid knob, spout and handle
    c.paint(ellipse(c, 12.0, 42.6, 4.2, 2.6) & (Y < 45.0), EMBER, np.where(X < 10.8, T1, T2), 1.3)
    c.paint(ellipse(c, 12.0, 40.2, 2.4, 0.8), EMBER, T3, 1.35)
    c.paint(c.line_mask([(15.6, 42.6), (18.0, 40.4)], 0.9), EMBER, T3, 1.35)
    c.paint(c.line_mask([(9.4, 40.0), (10.0, 38.6), (14.0, 38.6), (14.6, 40.0)], 0.6), UMBER, T3, 1.4)
    # a blue-and-white jug
    jug = ellipse(c, 28.5, 42.4, 2.8, 2.7) | rect(c, 27.0, 39.0, 30.0, 41.0)
    c.paint(jug & (Y < 45.0), PEARL, 0.0, 1.3)
    c.paint(jug & (np.abs(Y - 42.6) < 0.6), LAPIS, T3, 1.35)
    c.paint(jug & (Y < 40.0), LAPIS, T2, 1.35)
    c.paint(c.line_mask([(31.0, 40.0), (32.6, 41.2), (31.2, 43.4)], 0.6), PEARL, T1, 1.3)
    frame(c)
    return encode(c.to_tiles())


# ---------------------------------------------------------------------------
# Challenge
# ---------------------------------------------------------------------------

def asanoha(X, Y, a, h):
    """The asanoha (hemp-leaf) pattern on a triangular lattice (vertical side a, column spacing h; h = a
    makes every line a clean 1:1, 2:1 or 3:2 staircase in tiles). Returns the distance to the leaf
    outlines (from each triangle's centre to its corners) and to the midribs (the lattice lines)."""
    s = X / h
    t = (Y - s * a / 2) / a
    i, j = np.floor(s), np.floor(t)
    up = (s - i) + (t - j) < 1
    corners = [(np.where(up, i, i + 1), j), (np.where(up, i + 1, i), np.where(up, j, j + 1)),
               (np.where(up, i, i + 1), j + 1)]
    pts = [(si * h, si * a / 2 + ti * a) for si, ti in corners]
    gx = sum(p[0] for p in pts) / 3
    gy = sum(p[1] for p in pts) / 3
    d = np.full(X.shape, 99.0)
    for (vx, vy) in pts:
        ex, ey = vx - gx, vy - gy
        k = np.clip(((X - gx) * ex + (Y - gy) * ey) / (ex * ex + ey * ey), 0, 1)
        d = np.minimum(d, np.hypot(X - gx - k * ex, Y - gy - k * ey))
    slant = a * h / math.hypot(h, a / 2)
    rib = np.minimum.reduce([np.abs(s - np.round(s)) * h, np.abs(t - np.round(t)) * slant,
                             np.abs(s + t - np.round(s + t)) * slant])
    return d, rib


def asanoha_kimono():
    """An indigo kimono hung flat on its black lacquered stand (iko), dyed all over with the asanoha
    (hemp-leaf) pattern in white - six-pointed stars of leaves on a triangular lattice - with a white
    collar over a red under-collar and a red obi with gold flowers and a gold cord; behind it a shoji
    screen of cream paper in a light wooden lattice above a wooden kickboard, straw tatami below."""
    c = Canvas(42, 46)
    X, Y = c.X, c.Y
    tx, ty = tiles_of(c)
    # shoji, kickboard, and tatami with a dark green binding
    c.paint(ALL(c), PEARL, T1)
    c.paint(((tx % 7) == 3) | ((ty % 9) == 2), SAFFRON, T3)
    c.paint((ty >= 34) & (ty < 42), SAFFRON, np.where(ty == 34, T2, T3))
    c.paint(Y >= 42.0, SAFFRON, T1)
    c.paint((Y >= 42.0) & (Y < 43.0), FERN, T3)
    # the stand: two posts on feet and a top rail with upturned ends
    for px in (1.8, 40.2):
        c.paint(rect(c, px - 0.8, 6.0, px + 0.8, 44.0), UMBER, T3, 1.2)
        c.paint(rect(c, px - 2.0, 42.8, px + 2.0, 44.0), UMBER, T3, 1.2)
    c.paint(c.poly_mask([(0.0, 4.2), (4, 5.4), (38, 5.4), (42.0, 4.2), (42.0, 6.2), (38, 7.2), (4, 7.2), (0.0, 6.2)]),
            UMBER, T3, 1.2)
    # the kimono: arms along the rail, sleeves hanging free of the body, a long body
    sleeves = rect(c, 3.5, 7.0, 38.5, 16.0) | rect(c, 3.5, 7.0, 11.0, 23.0) | rect(c, 31.0, 7.0, 38.5, 23.0)
    sleeves |= ellipse(c, 6.0, 23.0, 2.5, 2.2) | ellipse(c, 36.0, 23.0, 2.5, 2.2) | rect(c, 6.0, 20, 11.0, 25.2)
    sleeves |= rect(c, 31.0, 20, 36.0, 25.2)
    kim = sleeves | rect(c, 12.5, 6.5, 29.5, 42.0)
    c.paint(kim, LAPIS, T3, 1.1)
    # the asanoha, decided per tile, one tile inside the silhouette, without stray single tiles
    def shift(m, dx, dy):
        return np.roll(np.roll(m, dx * 8, axis=1), dy * 8, axis=0)
    core = kim & shift(kim, 1, 0) & shift(kim, -1, 0) & shift(kim, 0, 1) & shift(kim, 0, -1)
    d, rib = asanoha(np.floor(X) + 0.5 - 21.0, np.floor(Y) + 0.5 - 8.0, 14.0, 14.0)
    pat = core & ((d < 0.5) | (rib < 0.47))
    pat &= shift(pat, 1, 0) | shift(pat, -1, 0) | shift(pat, 0, 1) | shift(pat, 0, -1)
    c.paint(pat, PEARL, 0.0, 1.2)
    # the collar: white neckbands with the red under-kimono showing between them, crossing left over
    # right (the right-hand band runs on top down to the obi)
    c.paint(c.line_mask([(18.5, 6.8), (21.2, 14.6)], 1.1), PEARL, 0.0, 1.3)
    c.paint(c.line_mask([(19.7, 7.2), (21.4, 12.0)], 1.0), EMBER, T2, 1.3)
    c.paint(c.line_mask([(22.5, 7.2), (20.6, 13.2)], 1.0), EMBER, T2, 1.32)
    c.paint(c.line_mask([(23.6, 6.8), (18.7, 23.4)], 1.2), PEARL, 0.0, 1.35)
    c.paint(c.line_mask([(25.0, 6.8), (19.9, 23.4)], 1.4), LAPIS, T2, 1.34)
    # obi: red with gold flower diamonds and a gold cord tied in front
    obi = rect(c, 12.5, 23.5, 29.5, 29.5)
    c.paint(obi, EMBER, T2, 1.4)
    for ox in (15.0, 21.0, 27.0):
        c.paint((np.abs(X - ox) + np.abs(Y - 25.8) * 1.2 < 1.9) & obi, SAFFRON, T1, 1.5)
    c.paint(obi & (np.abs(Y - 28.3) < 0.5), SAFFRON, T2, 1.55)
    c.paint(ellipse(c, 21.0, 28.4, 1.4, 1.0) | c.line_mask([(20.6, 28.6), (19.6, 31.6)], 0.6), SAFFRON, T2, 1.6)
    # red lining showing at the hem
    c.paint(rect(c, 12.5, 41.0, 29.5, 42.0), EMBER, T3, 1.3)
    frame(c)
    return encode(c.to_tiles())


def tartan():
    """An original woven tartan (not any registered sett): green and blue grounds, black lines in
    pairs, a red and a yellow overcheck. Where two colours cross, the brighter overcheck shows over the
    grounds and green shows over blue; the black lines only darken whatever they cross (black on black
    gives small black squares); the 2/2 twill shows as diagonal tone steps where the colours differ.
    A swatch with a knotted fringe at both ends, on white linen."""
    c = Canvas(44, 44)
    tx, ty = tiles_of(c)
    # the sett (colour, threads), repeated across warp (columns) and weft (rows)
    sett = [(EMBER, 2), (FERN, 6), (UMBER, 1), (FERN, 1), (UMBER, 1), (LAPIS, 6), (SAFFRON, 1), (LAPIS, 6),
            (UMBER, 1), (FERN, 1), (UMBER, 1), (FERN, 6)]
    seq = np.array([f for f, n in sett for _ in range(n)])
    wid = np.array([n for f, n in sett for _ in range(n)])
    warp, weft = seq[(tx + 2) % len(seq)], seq[(ty - 2) % len(seq)]
    ww, hw = wid[(tx + 2) % len(seq)], wid[(ty - 2) % len(seq)]
    base = np.array([T2, T1, T1, T2, T3, 0.0])
    rank = np.array([1, 3, 2, 3, 0, 3])[np.stack([warp, weft])]     # blue < green < red, yellow
    fam = np.where(rank[0] > rank[1], warp, np.where(rank[1] > rank[0], weft, np.where(ww <= hw, warp, weft)))
    fam = np.where(warp == UMBER, np.where(weft == UMBER, UMBER, weft), np.where(weft == UMBER, warp, fam))
    twill = ((tx + ty) // 2) % 2 == 0
    tone = base[fam] + np.where(warp == weft, 0.0, np.where(twill, T1, 0.0))
    dark = ((warp == UMBER) | (weft == UMBER)) & (fam != UMBER)
    tone = np.clip(np.where(dark, np.maximum(tone, T2) + T1, tone), 0, 1)
    # the linen, the cloth, and the fringe: warp ends knotted in tassels of three threads
    c.paint(ALL(c), PEARL, T1)
    cloth = rect(c, 2, 6, 42, 38)
    fringe = (rect(c, 2, 2, 42, 6) | rect(c, 2, 38, 42, 42)) & (((tx - 2) % 4) < 3)
    for f in range(6):
        c.paint(cloth & (fam == f), f, tone)
        c.paint(fringe & (warp == f), f, base[f])
    frame(c)
    return encode(c.to_tiles())


# ---------------------------------------------------------------------------
# Master
# ---------------------------------------------------------------------------

def patchwork_quilt():
    """An American patchwork quilt: nine eight-point star blocks, each star pieced from two fabrics
    round a small centre on a light ground, set with red sashing and gold cornerstones inside a
    piano-key border of every colour."""
    c = Canvas(44, 44)
    X, Y = c.X, c.Y
    tx, ty = tiles_of(c)
    fam = np.full(tx.shape, PEARL)
    tone = np.zeros(tx.shape)

    def put(m, f, t):
        fam[m], tone[m] = f, t
    # piano-key border: short bars of every colour
    keys = [EMBER, SAFFRON, LAPIS, FERN, UMBER, PEARL]
    k = ((np.where((ty <= 2) | (ty >= 41), tx, ty)) // 2) % 6
    for i, f in enumerate(keys):
        put(k == i, f, T2 if f != PEARL else T1)
    # sashing and cornerstones
    inner = (tx >= 2) & (tx <= 41) & (ty >= 2) & (ty <= 41)
    lx, ly = (tx - 2) % 13, (ty - 2) % 13
    put(inner & ((lx == 0) | (ly == 0)), EMBER, T3)
    put(inner & (lx == 0) & (ly == 0), SAFFRON, T1)
    # the star blocks (star fabric A, star fabric B, centre, ground)
    blocks = [(LAPIS, SAFFRON, UMBER, PEARL), (FERN, EMBER, SAFFRON, PEARL), (EMBER, LAPIS, SAFFRON, PEARL),
              (UMBER, SAFFRON, EMBER, PEARL), (EMBER, SAFFRON, FERN, LAPIS), (LAPIS, FERN, EMBER, PEARL),
              (FERN, LAPIS, SAFFRON, PEARL), (SAFFRON, EMBER, UMBER, PEARL), (UMBER, EMBER, SAFFRON, PEARL)]
    for b, (fa, fb, fc, fg) in enumerate(blocks):
        bx, by = 3 + 13 * (b % 3), 3 + 13 * (b // 3)
        u, v = X - bx - 6.0, Y - by - 6.0
        blk = (tx >= bx) & (tx < bx + 12) & (ty >= by) & (ty < by + 12)
        put(blk, fg, 0.0 if fg == PEARL else T1)
        # eight diamond points, the two fabrics alternating
        cu, cv = np.floor(u) + 0.5, np.floor(v) + 0.5
        st = blk & star8(cu, cv, 6.2, 2.7)
        sector = np.round(np.arctan2(cv, cu) / (math.pi / 4)).astype(int) % 2
        put(st & (sector == 0), fa, T2)
        put(st & (sector == 1), fb, T2 if fb != SAFFRON else T1)
        put(blk & (np.abs(cu) < 1.2) & (np.abs(cv) < 1.2), fc, T3 if fc != SAFFRON else T2)
    for f in range(6):
        c.paint(fam == f, f, tone)
    frame(c)
    return encode(c.to_tiles())


def persian_carpet():
    """A Persian medallion carpet seen from above, drawn on whole tiles: a deep-red field with small
    blossoms, a navy lobed medallion outlined in gold with a red star and pendants, gold-ringed quarter
    medallions in the corners, a navy main border of red-and-gold rosettes with green leaves between
    gold-and-white and gold-and-green guard stripes, a red outer guard, and a white fringe at both
    ends lying over the floorboards."""
    W, H = 34, 48
    c = Canvas(W, H)
    xs, ys, fam, tone = grid_canvas(W, H)
    xc, yc = xs + 0.5 - 17.0, ys + 0.5 - 24.0                  # offsets from the carpet's centre

    def put(m, f, t):
        fam[m], tone[m] = f, (t if np.isscalar(t) else t[m])
    # floorboards and the fringe threads
    put(np.ones_like(xs, bool), UMBER, np.where((ys % 2) == 0, T2, T1))
    put((((ys >= 1) & (ys <= 3)) | ((ys >= 44) & (ys <= 46))) & (xs >= 1) & (xs <= 32) & ((xs % 2) == 1), PEARL, 0.0)
    rug = (xs >= 1) & (xs <= 32) & (ys >= 4) & (ys <= 43)
    sx, sy = np.minimum(xs - 1, 32 - xs), np.minimum(ys - 4, 43 - ys)     # depth from the sides
    d = np.minimum(sx, sy)
    along = np.where(sy <= sx, xc, yc)
    # outer red guard, gold-and-white stripe, navy main border, gold-and-green stripe
    put(rug & (d == 0), EMBER, T3)
    put(rug & (d == 1), PEARL, 0.0)
    put(rug & (d == 1) & ((np.floor(along / 3) % 2) == 0), SAFFRON, T1)
    main = rug & (d >= 2) & (d <= 5)
    put(main, LAPIS, T3)
    shift = np.where(sy <= sx, 5.0, 0.0)               # two rosettes on the ends, three on the long sides
    ph, dd = ((along + shift + 5) % 10) - 5, d - 3.5
    corner = main & (sx <= 5) & (sy <= 5)
    side = main & ~corner
    put(side & (np.abs(ph) + np.abs(dd) <= 3.5), EMBER, T2)
    put(side & (np.abs(ph) <= 0.5) & (np.abs(dd) <= 0.5), SAFFRON, T1)
    put(side & (np.abs(ph) == 4.5) & (np.abs(dd) <= 0.5), FERN, T2)
    cu, cv = sx - 3.5, sy - 3.5
    put(corner & (np.abs(cu) + np.abs(cv) <= 3), EMBER, T2)
    put(corner & (np.abs(cu) <= 0.5) & (np.abs(cv) <= 0.5), SAFFRON, T1)
    put(rug & (d == 6), FERN, T2)
    put(rug & (d == 6) & ((np.floor(along / 3) % 2) == 0), SAFFRON, T1)
    # the field, with quarter medallions in its corners
    field = rug & (d >= 7)
    put(field, EMBER, T3)
    for (qx, qy) in ((-9.0, -13.0), (9.0, -13.0), (-9.0, 13.0), (9.0, 13.0)):
        q = field & (np.hypot(xc - qx, yc - qy) < 5.6)
        put(q, SAFFRON, T1)
        put(q & ~edge8(q | ~field), LAPIS, T2)
        put(q & (np.hypot(xc - qx, yc - qy) < 2.2), UMBER, T3)
    # small blossoms strewn over the field
    kinds = [(PEARL, 0.0), (SAFFRON, T1), (FERN, T1), (UMBER, T3)]
    for k, (bx, by) in enumerate([(-5.5, -9.5), (5.5, -9.5), (-5.5, 9.5), (5.5, 9.5), (-7.5, -3), (7.5, -3),
                                  (-7.5, 3), (7.5, 3)]):
        f, t = kinds[k % 4]
        put(field & (np.abs(xc - bx) + np.abs(yc - by) <= 1.5), f, t)
    # the central medallion: a lobed lozenge outlined in gold, with a pendant at each end
    lob = 1.0 + 0.07 * np.cos(np.arctan2(yc, xc) * 8)
    med = (np.abs(xc) / 7.4 + np.abs(yc) / 10.2 < lob) | (np.abs(xc) / 2.6 + np.abs(np.abs(yc) - 11.0) / 1.6 < 1)
    med &= field
    put(med, SAFFRON, T1)
    put(med & ~edge8(med, False), LAPIS, T3)
    put(star8(xc, yc, 3.8, 1.9), EMBER, T2)
    put((np.abs(xc) <= 1) & (np.abs(yc) <= 1), PEARL, 0.0)
    grid_paint(c, fam, tone)
    frame(c)
    return encode(c.to_tiles())


SCENES = {
    "talavera": talavera_plate, "papercut": wycinanki, "pysanky": pysanky, "delft": delft_tiles,
    "asanoha": asanoha_kimono, "tartan": tartan, "quilt": patchwork_quilt, "carpet": persian_carpet,
}
