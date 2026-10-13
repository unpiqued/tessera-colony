"""Natural History pack: eight tile homages of famous public-domain natural-history plates, drawn with
the supersampled Canvas of art.py (a tile's colour family comes from the dominant object under it, its
tone from the shading). Every scene is an original composition in the manner of the plate it honours:
no plate numbers, captions or lettering.

Gentle: Audubon's flamingo, Redouté's rose, Merian's butterflies, Gould's hummingbirds.
Challenge: Haeckel's jellyfish, Seba's shells.
Master (busy, every colour in many islands): Haeckel's radiolarians, the beetle drawer.
"""
import math

import numpy as np

from scipy import ndimage

from art import Canvas, LAPIS, SAFFRON, FERN, EMBER, UMBER, PEARL, SS, encode
from art_scenes import ALL, ellipse, rect, tube, frame


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------

def tiles(c):
    return np.floor(c.X).astype(int), np.floor(c.Y).astype(int)


def axis(c, bx, by, tx, ty):
    """Coordinates along (s) and across (t) the segment base->tip, its length and unit vectors."""
    L = math.hypot(tx - bx, ty - by)
    dx, dy = (tx - bx) / L, (ty - by) / L
    s = (c.X - bx) * dx + (c.Y - by) * dy
    t = -(c.X - bx) * dy + (c.Y - by) * dx
    return s, t, L, dx, dy


def leaflet(c, bx, by, tx, ty, width, shade=0.55, fam=FERN, teeth=0.0, prio=1.15, bend=0.0, rim=0.0):
    """A pointed leaf from base to tip, optionally saw-toothed and dark-rimmed, with a pale midrib and a
    darker lower half."""
    s, t, L, dx, dy = axis(c, bx, by, tx, ty)
    u = np.clip(s / L, 0, 1)
    t = t - bend * L * (u - u * u) * 2.0
    half = width / 2 * np.sin(np.pi * u) ** 0.7
    if teeth:
        half = half * (0.8 + 0.28 * ((s / teeth) % 1.0))
    m = (s >= 0) & (s <= L) & (np.abs(t) <= half)
    tone = np.where(t > 0, shade + 0.15, shade - 0.05)
    tone = np.where(np.abs(t) < 0.3, shade - 0.3, tone)
    if rim:
        tone = np.where(np.abs(t) > half - rim, 1.0, tone)
    c.paint(m, fam, np.clip(tone, 0, 1), prio)
    return m


def local(cx, cy, ang, s=1.0, flip=1):
    """A transform from a shape's local frame (x right, y down, unit s; flip=-1 mirrors x) into canvas
    coordinates."""
    ca, sa = math.cos(ang), math.sin(ang)
    return lambda px, py: (cx + (flip * px * ca - py * sa) * s, cy + (flip * px * sa + py * ca) * s)


# ---------------------------------------------------------------------------
# gentle
# ---------------------------------------------------------------------------

def flamingo():
    """Audubon's American Flamingo (Birds of America, 1838): the great pink bird fills the plate and bows
    its long neck right down to feed beside its feet; behind it a low lagoon shore with a far-off flock."""
    c = Canvas(38, 46)
    X, Y = c.X, c.Y
    hz = 35.5
    # pale sky: soft blue above, cream towards the low horizon
    c.paint(ALL(c), PEARL, np.where(Y < 29 + 2 * np.sin(X * 0.4), 0.0, 0.33))
    c.paint(Y < 12.5 + 1.5 * np.sin(X * 0.25 + 1), LAPIS, 0.0)
    # far shore: low wooded hills on the horizon, the lagoon, a sandy mudflat in front
    bumps = np.clip(np.sin(X * 0.45) + 0.6 * np.sin(X * 1.3 + 2), 0, None)
    c.paint(Y > hz - 0.8 - 1.1 * bumps, FERN, np.clip(0.75 + 0.1 * np.sin(X * 2.0), 0, 1))
    rip = np.sin(Y * 2.6 + np.sin(X * 0.5) * 1.5) > 0.6
    c.paint(Y > hz + 0.7, LAPIS, np.clip(0.4 - 0.25 * rip + 0.03 * (Y - hz), 0, 1))
    flat = Y > 40.8 + 0.9 * np.sin(X * 0.33 + 0.5)
    c.paint(flat, SAFFRON, np.clip(0.3 + 0.03 * (Y - 40) + 0.12 * np.sin(X * 1.7 + Y), 0, 1))
    for (gx, gy) in ((3.5, 42.5), (8.5, 43.5), (24, 42.8), (35.0, 42.0)):
        for dx in (-0.8, 0.0, 0.8):
            c.paint(c.line_mask([(gx + dx * 0.4, gy + 1.0), (gx + dx * 1.6, gy - 1.6)], 0.45), FERN, 0.6, 1.4)
    # the far-off flock wading in the lagoon
    for fx in (3.0, 6.0, 9.0, 21.5, 34.5):
        bird = ellipse(c, fx, hz + 1.6, 1.0, 0.6) | c.line_mask([(fx + 0.7, hz + 1.4), (fx + 0.9, hz - 0.8)], 0.45)
        c.paint(bird, EMBER, 0.05, 1.5)
    # long legs with the backward-bending ankle, webbed feet in the shallows
    for (hip, knee, foot) in (((12.6, 19.0), (11.6, 30.0), (12.4, 41.6)), ((16.2, 19.0), (17.4, 30.0), (17.0, 41.6))):
        c.paint(tube(c, [hip, knee, foot], 1.3, 1.0), EMBER, 0.45, 1.8)
        c.paint(ellipse(c, knee[0], knee[1], 0.8, 1.0), EMBER, 0.6, 1.85)
        c.paint(c.poly_mask([(foot[0] - 1.8, foot[1] + 1.0), (foot[0] + 1.8, foot[1] + 1.0), (foot[0], foot[1] - 0.4)]),
                EMBER, 0.6, 1.85)
    # the body: a plump oval tilted tail-down, with a short tail and a scaled feather texture
    body = ellipse(c, 14.0, 14.4, 9.3, 5.7, -0.12) | ellipse(c, 6.5, 16.6, 3.2, 2.0, 0.5)
    scales = (np.sin(X * 1.5 + Y * 0.5) * np.sin(Y * 1.7) > 0.35)
    c.paint(body, EMBER, np.clip(0.02 + 0.015 * (Y - 9) + 0.12 * scales, 0, 1), 1.2)
    # the folded wing: deep rosy coverts, darkest at the trailing flight feathers
    wing = ellipse(c, 12.6, 13.0, 7.4, 3.6, -0.12)
    c.paint(wing, EMBER, np.clip(0.45 + 0.25 * scales + 0.3 * (X < 9), 0, 1), 1.25)
    # the long neck rising from the breast, arching over and plunging down to feed at the water's edge
    neck = [(21.5, 12.8), (24.0, 8.4), (27.3, 6.0), (30.3, 6.8), (31.7, 10.6), (31.4, 16.5), (30.4, 23.0),
            (29.7, 29.0), (29.4, 33.5)]
    c.paint(tube(c, neck, 3.0, 1.9), EMBER, np.clip(0.02 + 0.1 * (X > 30.5), 0, 1), 1.3)
    # head upside-down at the shore, the sharply bent bill pale at the base and black at the tip
    c.paint(ellipse(c, 29.2, 35.0, 1.9, 1.7), EMBER, 0.05, 1.6)
    c.paint(c.circle(29.9, 34.3, 0.5), SAFFRON, 0.3, 1.9)
    bill = tube(c, [(28.8, 36.2), (28.4, 37.8), (26.4, 39.0)], 2.0, 1.2)
    c.paint(bill, UMBER, 0.95, 1.7)
    c.paint(bill & (Y < 37.4), PEARL, 0.15, 1.75)
    frame(c)
    return encode(c.to_tiles())


def rose():
    """Redouté's Rose (Les Roses, 1817-24): one stem of a cabbage rose on the pale plate - a full open
    bloom of layered petals, two buds wrapped in long sepals, and toothed compound leaves."""
    c = Canvas(36, 46)
    X, Y = c.X, c.Y
    c.paint(ALL(c), PEARL, 0.0)
    # the main stem and two bud stalks, with a few hooked thorns
    c.paint(tube(c, [(9.0, 46), (10.6, 39), (13.6, 31), (17.0, 25), (20.0, 20)], 1.6, 1.2), FERN, 0.85, 1.4)
    for pts in ([(14.4, 29.5), (10.5, 24.5), (7.6, 19.5), (7.0, 16.0)], [(11.6, 36.0), (18.0, 34.5), (24.0, 31.0), (28.5, 27.2)]):
        c.paint(tube(c, pts, 1.1, 0.8), FERN, 0.85, 1.4)
    for (tx, ty, sd) in ((10.0, 42.0, -1), (12.0, 33.5, 1), (15.6, 28.0, -1)):
        c.paint(c.poly_mask([(tx, ty - 0.7), (tx + sd * 1.5, ty - 1.3), (tx, ty + 0.5)]), EMBER, 0.9, 1.5)

    def compound(base, tip, size, pairs):
        """A leaf stalk with a terminal leaflet and pairs of toothed side leaflets."""
        (bx, by), (tx, ty) = base, tip
        c.paint(c.line_mask([base, tip], 0.6), FERN, 0.85, 1.3)
        L = math.hypot(tx - bx, ty - by)
        dx, dy = (tx - bx) / L, (ty - by) / L
        leaflet(c, tx - dx * 0.4, ty - dy * 0.4, tx + dx * size, ty + dy * size, size * 0.8, 0.4, teeth=0.9, rim=0.35)
        for f in (0.92, 0.42)[:pairs]:
            px, py = bx + (tx - bx) * f, by + (ty - by) * f
            for sd in (-1, 1):
                ex, ey = px + (dx * 0.5 - sd * dy) * size * 0.95, py + (dy * 0.5 + sd * dx) * size * 0.95
                leaflet(c, px, py, ex, ey, size * 0.72, 0.35 + 0.1 * sd, teeth=0.9, rim=0.35)
    compound((10.4, 40.0), (4.6, 36.0), 4.4, 1)
    compound((10.8, 43.0), (19.5, 41.5), 4.6, 2)
    compound((18.5, 34.0), (21.5, 38.5), 3.8, 1)
    compound((10.8, 25.0), (4.8, 26.5), 3.4, 1)
    compound((23.5, 31.3), (26.0, 35.5), 3.4, 1)
    # slender sepals peeping out below the bloom
    cx, cy = 21.5, 12.5
    for a in (0.45, 1.25, 1.9, 2.7):
        c.paint(tube(c, [(cx + 6 * math.cos(a), cy + 6 * math.sin(a)), (cx + 11 * math.cos(a + 0.1), cy + 11 * math.sin(a + 0.1))],
                     1.5, 0.5), FERN, 0.6, 1.2)

    def petal(px, py, rx, ry, ang, fill, edge, w=0.6):
        c.paint(ellipse(c, px, py, rx, ry, ang), EMBER, edge, 1.4)
        inner = ellipse(c, px, py, rx - w, ry - w, ang)
        c.paint(inner, EMBER, np.clip(fill + 0.25 * (1 - np.hypot(X - cx, Y - cy) / 9), 0, 1), 1.4)
    # the bloom, back to front: eight outer petals, five inner ones, the dark heart, two cupped front petals
    for k in range(8):
        a = -math.pi / 2 + k * math.pi / 4
        petal(cx + 5.0 * math.cos(a), cy + 5.0 * math.sin(a), 4.3, 3.9, a, 0.0, 0.7)
    for k in range(5):
        a = -math.pi / 2 + math.pi / 5 + k * 2 * math.pi / 5
        petal(cx + 2.6 * math.cos(a), cy + 2.6 * math.sin(a), 3.2, 2.8, a, 0.25, 0.95)
    c.paint(c.circle(cx, cy - 0.3, 2.0), EMBER, 0.95, 1.45)
    c.paint(c.line_mask([(cx - 1.2, cy - 0.2), (cx - 0.3, cy - 1.4), (cx + 1.0, cy - 0.8)], 0.55), EMBER, 0.5, 1.5)
    for sd in (-1, 1):
        petal(cx + sd * 2.2, cy + 3.4, 3.9, 2.5, -sd * 0.25, 0.0, 0.7)
    # two buds at the tips of the stalks, wrapped in green sepals
    for (bx, by, ang, open_) in ((6.9, 12.6, -0.15, False), (29.4, 24.0, 0.45, True)):
        T = local(bx, by, ang)
        bud = ellipse(c, bx, by, 2.2, 3.2, ang) | c.poly_mask([T(-1.4, -1.8), T(0, -4.8), T(1.4, -1.8)])
        c.paint(bud, EMBER, 0.4 if open_ else 0.75, 1.5)
        if open_:
            for sd in (-1, 1):
                c.paint(ellipse(c, *T(sd * 1.7, -2.4), 1.5, 2.3, ang + sd * 0.5), EMBER, 0.05, 1.55)
        for sd in (-1, 0, 1):
            c.paint(tube(c, [T(sd * 0.9, 2.8), T(sd * 2.1, 0.2), T(sd * 2.0, -3.0 + abs(sd) * 1.0)], 1.0, 0.4), FERN, 0.7, 1.6)
        c.paint(ellipse(c, *T(0, 3.2), 1.3, 1.2, ang), FERN, 0.75, 1.6)
    frame(c)
    return encode(c.to_tiles())


# butterfly wing outlines (right side, body at the origin, head up), shared by every butterfly
FORE = [(0.7, -1.2), (3.5, -5.5), (7.5, -8.8), (11.2, -9.6), (12.6, -8.2), (12.4, -5.0), (10.8, -1.6), (7.0, 0.2), (1.0, 0.6)]
HIND = [(0.9, 0.6), (5.0, 0.8), (9.0, 1.8), (10.2, 4.6), (8.8, 8.2), (5.6, 10.0), (2.8, 9.0), (1.2, 5.6), (0.6, 2.2)]


def butterfly(c, cx, cy, s, tilt, fam, shade, border=UMBER, bw=1.0, spots=PEARL, eye=None):
    """An open-winged butterfly seen from above (span about 25 s): coloured wings, the fore wings edged
    with a dark border carrying pale spots, an optional eyespot on each hind wing, dark body and antennae."""
    T = local(cx, cy, tilt, s)
    ca, sa = math.cos(tilt), math.sin(tilt)
    lx = np.abs((c.X - cx) * ca + (c.Y - cy) * sa) / s
    ly = (-(c.X - cx) * sa + (c.Y - cy) * ca) / s
    for sd in (-1, 1):
        for shape in (HIND, FORE):
            m = c.poly_mask([T(sd * x, y) for x, y in shape])
            r = np.hypot(c.X - cx, c.Y - cy) / (12 * s)
            c.paint(m, fam, np.clip(shade + 0.3 * (r - 0.5), 0, 1), 1.4)
            if shape is FORE:
                dist = ndimage.distance_transform_edt(m) / SS
                c.paint(m & ((lx - 0.5 * ly > 11.2) | ((dist < bw) & (lx - 0.5 * ly > 8.5))), border, 0.95, 1.45)
        for (x, y) in ((11.0, -8.2), (11.8, -5.6)):
            c.paint(c.circle(*T(sd * x, y), 0.55), spots, 0.05, 1.6)
        if eye is not None:
            c.paint(c.circle(*T(sd * 5.4, 4.6), 1.3), eye, 0.3, 1.6)
            c.paint(c.circle(*T(sd * 5.4, 4.6), 0.6), UMBER, 0.95, 1.65)
        c.paint(c.line_mask([T(0, -3.0), T(sd * 1.3, -5.6), T(sd * 2.0, -7.2)], 0.9), UMBER, 0.95, 1.7)
    c.paint(tube(c, [T(0, -2.4), T(0, 6.5)], 2.2 * s, 1.2 * s), UMBER, 0.9, 1.75)
    c.paint(c.circle(*T(0, -3.0), 1.3 * s), UMBER, 0.95, 1.75)


def metamorphosis():
    """Maria Sibylla Merian's Surinam plate (1705): a pomegranate branch in flower and fruit with the life
    of its butterflies on it - a banded caterpillar crawling along a leaf, a golden chrysalis hanging under
    another, and two great butterflies, the shining blue morpho and a yellow one with red eyespots."""
    c = Canvas(40, 46)
    X, Y = c.X, c.Y
    c.paint(ALL(c), PEARL, 0.0)
    # narrow glossy leaves along the branch
    for (bx, by, tx, ty, w) in ((20.6, 40.0, 29.0, 43.6, 3.6), (20.8, 40.2, 13.0, 39.0, 3.2), (22.5, 34.5, 15.5, 31.0, 3.4),
                                 (25.5, 27.0, 33.5, 25.0, 3.4), (27.5, 23.5, 21.5, 18.0, 3.2), (30.0, 18.0, 37.5, 19.0, 3.2),
                                 (31.5, 11.5, 37.0, 7.0, 3.0), (31.2, 11.8, 27.0, 6.0, 2.8)):
        leaflet(c, bx, by, tx, ty, w, shade=0.45, bend=0.12, rim=0.35)
    # the branch climbing from the foot of the plate to the top right, with side twigs
    c.paint(tube(c, [(20.0, 46), (21.0, 38), (24.0, 30), (28.0, 22), (31.0, 15), (32.0, 8)], 2.2, 1.0), UMBER,
            np.clip(0.45 + 0.2 * np.sin(Y * 1.5 + X), 0, 1), 1.3)
    for pts in ([(24.0, 30), (30.0, 29.5), (31.0, 30.5)], [(31.0, 15.5), (27.0, 12.0), (24.5, 11.0)]):
        c.paint(tube(c, pts, 1.2, 0.7), UMBER, 0.45, 1.35)
    # scarlet flowers: a fleshy calyx tube, crumpled petals and a golden boss of stamens
    for (fx, fy, s) in ((33.0, 4.6, 0.95), (24.5, 9.5, 1.05)):
        c.paint(c.poly_mask([(fx - 1.0 * s, fy + 3.5 * s), (fx + 1.0 * s, fy + 3.5 * s), (fx + 1.6 * s, fy + 0.8 * s),
                             (fx - 1.6 * s, fy + 0.8 * s)]), EMBER, 0.85, 1.4)
        for k in range(5):
            a = -math.pi / 2 + (k - 2) * 0.62
            c.paint(c.circle(fx + 2.0 * s * math.cos(a), fy + 0.3 + 2.0 * s * math.sin(a), 1.6 * s), EMBER, 0.4, 1.45)
        c.paint(ellipse(c, fx, fy - 0.6 * s, 1.0 * s, 0.7 * s), SAFFRON, 0.25, 1.5)
    # the great pomegranate hanging from its twig, with its crown
    fx, fy, fr = 30.0, 37.0, 5.4
    c.paint(tube(c, [(30.5, 29.8), (30.2, 32.0)], 1.0, 1.0), UMBER, 0.6, 1.3)
    c.paint(c.circle(fx, fy, fr), EMBER, np.clip(0.3 + 0.5 * np.clip(np.hypot(X - fx + 2, Y - fy + 2) / (2 * fr), 0, 1), 0, 1), 1.3)
    c.paint(c.circle(fx - 2.0, fy - 2.2, 1.2), EMBER, 0.0, 1.35)
    c.paint(c.poly_mask([(fx - 1.6, fy + fr - 0.6), (fx - 2.2, fy + fr + 1.8), (fx - 0.6, fy + fr + 0.6), (fx, fy + fr + 2.0),
                         (fx + 0.6, fy + fr + 0.6), (fx + 2.2, fy + fr + 1.8), (fx + 1.6, fy + fr - 0.6)]), EMBER, 0.9, 1.4)
    # the caterpillar crawling along a leaf, the golden chrysalis hanging beneath the next leaf up
    cat = tube(c, [(24.8, 25.9), (26.6, 24.9), (28.4, 25.5), (30.2, 24.7), (32.2, 25.0)], 2.0, 1.7)
    c.paint(cat, SAFFRON, np.where(((X - 24.4) % 1.6) < 0.8, 0.0, 0.67), 1.6)
    c.paint(c.circle(32.8, 25.0, 1.0), EMBER, 0.67, 1.7)
    c.paint(c.line_mask([(35.4, 19.0), (35.4, 20.4)], 0.5), UMBER, 0.6, 1.5)
    chrys = ellipse(c, 35.4, 22.2, 1.4, 2.4) | c.poly_mask([(34.6, 23.8), (35.4, 25.6), (36.2, 23.8)])
    c.paint(chrys, SAFFRON, np.where(X < 35.4, 0.0, 0.67), 1.6)
    # the two butterflies: the blue morpho above, the yellow one below
    butterfly(c, 11.8, 13.0, 0.8, -0.2, LAPIS, 0.35, bw=0.8)
    butterfly(c, 9.6, 32.5, 0.6, 0.25, SAFFRON, 0.15, bw=0.8, eye=EMBER)
    frame(c)
    return encode(c.to_tiles())


def hummingbird(c, cx, cy, ang, s, back, throat, tail, flip=1, hover=True, crown=None, streamers=False):
    """A hummingbird in profile, facing +x of its frame (flip=-1 faces left): plump body, round head, a
    long needle bill, forked tail, and either two blurred wings raised over the back or a folded wing."""
    T = local(cx, cy, ang, s, flip)
    ea = lambda a: ang + flip * a
    if hover:
        for (tx_, ty_) in ((1.5, -8.5), (-4.8, -7.6)):
            c.paint(tube(c, [T(-0.4, -1.4), T(tx_ * 0.6, ty_ * 0.6), T(tx_, ty_)], 2.2 * s, 0.6 * s), PEARL, 0.4, 1.35)
    tails = ((-7.6, 1.0), (-7.0, 3.4)) if not streamers else ((-14.0, 0.5), (-13.0, 4.0))
    for k, (tx_, ty_) in enumerate(tails):
        c.paint(tube(c, [T(-2.4, 0.6), T(tx_, ty_)], 1.6 * s, 0.6 * s), tail, 0.6 + 0.2 * k, 1.4)
    c.paint(ellipse(c, *T(0, 0), 3.4 * s, 2.3 * s, ea(0)), back, 0.45, 1.45)
    c.paint(ellipse(c, *T(0.4, 1.3), 2.8 * s, 1.0 * s, ea(0)), PEARL, 0.1, 1.5)
    if not hover:
        c.paint(ellipse(c, *T(-1.6, -0.2), 3.2 * s, 1.2 * s, ea(0.1)), back, 0.85, 1.5)
    c.paint(c.circle(*T(3.4, -1.0), 1.9 * s), crown if crown is not None else back, 0.4, 1.55)
    c.paint(ellipse(c, *T(3.3, 0.6), 1.8 * s, 1.0 * s, ea(0.3)), throat, 0.3, 1.6)
    c.paint(c.line_mask([T(5.0, -1.1), T(10.6, -0.8)], 0.6 * s), UMBER, 0.95, 1.7)
    c.paint(c.circle(*T(4.0, -1.4), 0.5 * s), UMBER, 1.0, 1.8)


def fuchsia(c, x, y, s=1.0):
    """A hanging fuchsia from (x, y): a stalk, a scarlet tube with four flaring sepals, a pale petal skirt
    and dangling golden stamens."""
    c.paint(c.line_mask([(x, y), (x + 0.3 * s, y + 2.5 * s)], 0.45), UMBER, 0.6, 1.4)
    yt = y + 2.5 * s
    c.paint(tube(c, [(x + 0.3 * s, yt), (x + 0.3 * s, yt + 2.2 * s)], 1.1 * s, 1.6 * s), EMBER, 0.45, 1.45)
    for sd in (-1, 1):
        c.paint(tube(c, [(x + 0.3 * s, yt + 2.0 * s), (x + 0.3 * s + sd * 2.6 * s, yt + 2.6 * s), (x + 0.3 * s + sd * 3.0 * s, yt + 1.6 * s)],
                     1.1 * s, 0.5 * s), EMBER, 0.55, 1.5)
    c.paint(ellipse(c, x + 0.3 * s, yt + 3.6 * s, 1.5 * s, 1.5 * s) & (c.Y > yt + 2.4 * s), PEARL, 0.1, 1.5)
    for dx in (-0.6, 0.6):
        c.paint(c.line_mask([(x + 0.3 * s + dx * s, yt + 4.4 * s), (x + 0.3 * s + dx * 1.3 * s, yt + 6.2 * s)], 0.4), SAFFRON, 0.4, 1.55)


def hummingbirds():
    """Gould's hummingbirds (1849-61): three jewel-bright birds at a flowering fuchsia against a soft sky -
    one hovering to sip a hanging bloom, one perched below, a long-tailed sylph darting in."""
    c = Canvas(46, 40)
    X, Y = c.X, c.Y
    c.paint(ALL(c), LAPIS, 0.0)
    # a soft far landscape: blue mountains and green hills low on the plate
    peaks = 26.5 + 7.0 * np.abs(((X + 6) / 9.0) % 2 - 1) + 0.5 * np.sin(X * 1.3)
    c.paint(Y > peaks, LAPIS, 0.33)
    c.paint((Y > peaks) & (Y < 29.2 + 0.4 * np.sin(X * 2.1)), PEARL, 0.0, 1.05)
    c.paint(Y > 34.5 + 1.6 * np.sin(X * 0.2 + 0.6) + 0.6 * np.sin(X * 0.7), FERN, 0.0, 1.0)
    # the flowering branch arching in from the right, a lower twig for the percher
    c.paint(tube(c, [(47, 15.0), (38, 11.5), (30, 10.0), (23, 8.5), (18, 7.4)], 1.9, 1.2), UMBER, 0.6, 1.3)
    c.paint(tube(c, [(47, 32.5), (40, 31.0), (30, 31.5)], 1.6, 1.0), UMBER, 0.6, 1.3)
    for (bx, by, tx, ty, w) in ((40, 12.0, 44.0, 6.0, 3.6), (34, 10.8, 37.0, 4.5, 3.2), (27, 9.5, 28.5, 3.5, 3.0),
                                 (42, 31.6, 44.5, 25.0, 3.0), (32, 31.4, 29.5, 36.5, 2.8)):
        leaflet(c, bx, by, tx, ty, w, shade=0.45, bend=0.1, rim=0.35)
    for (fx, fy, fs) in ((25.5, 9.3, 1.15), (32.0, 10.4, 1.05), (38.0, 11.6, 1.1)):
        fuchsia(c, fx, fy, fs)
    # the birds: a ruby-throat hovering to sip, a topaz-throat perched below, a long-tailed sylph darting in
    hummingbird(c, 14.0, 24.5, -0.5, 1.4, FERN, EMBER, UMBER)
    hummingbird(c, 39.2, 27.6, 0.95, 1.2, FERN, SAFFRON, EMBER, flip=-1, hover=False, crown=EMBER)
    hummingbird(c, 8.0, 11.5, -0.3, 0.9, FERN, EMBER, UMBER, streamers=True)
    frame(c)
    return encode(c.to_tiles())


# ---------------------------------------------------------------------------
# challenge
# ---------------------------------------------------------------------------

def jellyfish():
    """Haeckel's Discomedusae (Art Forms in Nature, 1904): one great jellyfish on a dark plate - a red dome
    ribbed with pale canals and fringed with lappets, four frilled oral arms hanging from its heart and long
    golden tentacles trailing down, with baby medusae drifting at the edges."""
    c = Canvas(40, 48)
    X, Y = c.X, c.Y
    cx, rim = 20.0, 17.0
    c.paint(ALL(c), LAPIS, 1.0)
    # long golden tentacles from the outer rim, swaying in mirrored pairs to the foot of the plate
    for k, x0 in enumerate((6.6, 8.6, 10.6, 12.6)):
        for sd in (-1, 1):
            pts = [(cx + sd * (x0 + 0.04 * t * (1 + k) + 1.4 * math.sin(t * 0.2 + k * 1.7) * min(1.0, t / 5)), rim + 0.5 + t)
                   for t in np.arange(0, 31, 1.0)]
            c.paint(tube(c, pts, 1.15, 1.0), SAFFRON if k % 2 == 0 else PEARL, 0.05, 1.4)
    # four frilled oral arms: ruffled ribbons hanging from the centre, the outer pair pale, the inner pink
    for (x0, x1, fam) in ((-5.0, -8.4, PEARL), (-1.9, -3.2, EMBER), (1.9, 3.2, EMBER), (5.0, 8.4, PEARL)):
        pts = [(cx + x0 + (x1 - x0) * t / 22 + 0.7 * math.sin(t * 0.4 + x0), rim + 0.5 + t) for t in np.arange(0, 23, 0.5)]
        for i, (px, py) in enumerate(pts):
            c.paint(c.circle(px, py, 1.15 + 0.5 * math.sin(i * 1.2) - 0.012 * i), fam, 0.05 if i % 6 < 3 else 0.33, 1.5)
    # the dome: shaded red with pale radial canals converging on the crown, a dark rim and pale lappets
    half = 14.5 * np.sqrt(np.clip(1 - ((rim - Y) / 14.0) ** 2, 0, 1)) ** 0.8
    dome = (np.abs(X - cx) <= half) & (Y <= rim) & (Y > rim - 14)
    u = (X - cx) / np.maximum(half, 0.1)
    c.paint(dome, EMBER, np.where(np.abs(u) < 0.6, 0.33, 0.67), 1.3)
    canals = np.zeros_like(X, bool)
    for uk in (-0.8, -0.48, -0.16, 0.16, 0.48, 0.8):
        canals |= np.abs(u - uk) * half < 0.5
    c.paint(dome & canals & (Y > rim - 12.5), PEARL, 0.15, 1.35)
    c.paint(dome & (rim - Y < 1.2), EMBER, 1.0, 1.4)
    lappets = rect(c, cx - 13.6, rim - 0.2, cx + 13.6, rim + 0.6)
    for k in range(13):
        lappets |= c.circle(cx - 13.0 + 26.0 * k / 12, rim + 0.4, 1.0) & (Y > rim - 0.2)
    c.paint(lappets, PEARL, 0.1, 1.45)
    # baby medusae drifting at the edges: little green bells with a pale rim and three trailing threads
    for (mx, my, mr, sd) in ((4.2, 26.0, 2.5, 1), (35.8, 29.5, 2.5, -1), (4.4, 40.0, 2.2, 1), (35.6, 41.5, 2.1, -1)):
        for dx in (-0.65, 0.0, 0.65):
            x0 = mx + dx * mr
            c.paint(c.line_mask([(x0, my), (x0 + sd * 0.7, my + 1.0 * mr), (x0 - sd * 0.2, my + 2.0 * mr)], 0.55), PEARL, 0.33, 1.5)
        c.paint(ellipse(c, mx, my, mr, mr * 1.3) & (Y <= my), FERN, np.where(Y < my - mr * 0.5, 0.0, 0.33), 1.55)
        c.paint(rect(c, mx - mr, my - 0.1, mx + mr, my + 0.8), FERN, 1.0, 1.6)
    frame(c)
    return encode(c.to_tiles())


def shells():
    """Seba's cabinet (Thesaurus, 1734-65): a plate of many different shells laid out symmetrically -
    a flame-striped nautilus in the middle, a ribbed scallop above and a queen conch below, with banded
    cones, toothed cowries, tower shells and green turbans in mirrored pairs."""
    c = Canvas(44, 44)
    X, Y = c.X, c.Y
    c.paint(ALL(c), PEARL, 0.33)

    def edged(m, fam, shade, edge=UMBER, w=0.7):
        """Paint a shell body with a thin dark edge; returns its interior."""
        c.paint(m, edge, 0.8, 1.25)
        inner = ndimage.binary_erosion(m, iterations=max(1, int(w * SS)))
        c.paint(inner, fam, shade, 1.3)
        return inner

    def along(x, y, ang):
        return -(X - x) * math.sin(ang) + (Y - y) * math.cos(ang), (X - x) * math.cos(ang) + (Y - y) * math.sin(ang)

    def cone(x, y, L, W, ang):
        """A cone shell, low spire up: golden with two dark bands and a pale spire."""
        T = local(x, y, ang)
        m = c.poly_mask([T(0, -L / 2), T(W / 2, -L / 2 + 0.22 * L), T(0.12 * W, L / 2), T(-0.12 * W, L / 2), T(-W / 2, -L / 2 + 0.22 * L)])
        c.paint(m, SAFFRON, 0.33, 1.3)
        v, u = along(x, y, ang)
        c.paint(m & (np.abs(v - 0.06 * L) < 1.1), UMBER, 0.67, 1.35)
        c.paint(m & (v < -0.3 * L), SAFFRON, 0.0, 1.35)

    def cowrie(x, y, rx, ry, seed):
        """A cowrie from below: a glossy blue-grey oval with a highlight and the dark slit down the middle."""
        inner = ellipse(c, x, y, rx, ry)
        c.paint(inner, LAPIS, np.where(X < x + 0.5, 0.0, 0.33), 1.3)
        c.paint(ellipse(c, x - 0.45 * rx, y - 0.45 * ry, 0.8, 1.6), PEARL, 0.0, 1.35)
        slit = ellipse(c, x, y, 1.0, ry * 0.8)
        c.paint(slit, UMBER, 1.0, 1.4)
        teeth = ellipse(c, x, y, 2.0, ry * 0.7) & ~ellipse(c, x, y, 1.1, ry * 0.8) & (np.floor(Y).astype(int) % 2 == 0)
        c.paint(teeth, PEARL, 0.0, 1.45)

    def tower(x, y, L, W, ang):
        """A tower shell: a long spire of slanting cream and brown whorls."""
        T = local(x, y, ang)
        m = c.poly_mask([T(0, -L / 2), T(W / 2, L / 2 - 1.4), T(0, L / 2 + 0.3), T(-W / 2, L / 2 - 1.4)])
        inner = edged(m, PEARL, 0.0, w=0.7)
        v, u = along(x, y, ang)
        c.paint(m & ((((v + 0.35 * u) + L) / 1.9) % 1.0 < 0.45), UMBER, 0.33, 1.35)

    def turban(x, y, r):
        """A green turban: a round shell with a little peaked spire and spiral bands."""
        m = c.circle(x, y, r) | c.poly_mask([(x - r * 0.6, y - r * 0.5), (x, y - r * 1.45), (x + r * 0.6, y - r * 0.5)])
        c.paint(m, FERN, 0.33, 1.3)
        c.paint(m & ((np.hypot(X - x, (Y - y) * 1.3) % 1.7) < 0.7), FERN, 1.0, 1.35)

    # the scallop above: a red fan of pale ribs radiating from the hinge inside a wavy rim, two ears
    hx, hy, R = 22.0, 13.5, 11.4
    phi = np.arctan2(Y - hy, X - hx) + math.pi / 2
    rh = np.hypot(X - hx, Y - hy)
    k = (phi + 1.05) / (2.1 / 9)
    fan = (np.abs(phi) < 1.05) & (rh < R * (1 - 0.05 * np.abs(np.sin(k * math.pi)))) & (Y < hy + 0.5)
    fan |= rect(c, hx - 3.6, hy - 1.8, hx + 3.6, hy + 0.6)
    c.paint(fan, EMBER, np.where(np.floor(k).astype(int) % 2 == 0, 0.0, 0.67), 1.3)
    # the queen conch below, lying on its side: a pointed spire, a knobbed and banded body, a flared pink lip
    conch = (c.poly_mask([(11.0, 37.6), (17.5, 34.0), (17.5, 40.8)]) | ellipse(c, 22.4, 37.4, 6.6, 5.0)
             | c.poly_mask([(25.0, 33.4), (32.0, 35.4), (30.8, 41.8), (24.0, 42.8)]))
    for kx in (18.4, 21.6, 24.8):
        conch |= c.poly_mask([(kx - 1.5, 33.6), (kx, 30.6), (kx + 1.5, 33.6)])
    inner = edged(conch, SAFFRON, 0.0, w=0.7)
    for bx in (14.6, 19.2):
        c.paint(conch & (np.abs(X - bx - 0.3 * (Y - 37)) < 0.55) & (X < 25), UMBER, 0.33, 1.35)
    lip = c.poly_mask([(25.6, 34.8), (31.0, 36.2), (30.0, 40.8), (24.8, 41.6)]) & inner
    c.paint(lip, EMBER, np.where(X > 27.5, 0.0, 0.33), 1.4)
    # the nautilus: a cream whorl with curved flame stripes from the navel, the plain new chamber, the lip
    nx, ny = 21.0, 21.6
    shell = c.circle(nx, ny, 9.0) | ellipse(c, nx + 2.4, ny + 0.2, 7.6, 9.8)
    inner = edged(shell, PEARL, 0.0, w=0.7)
    for k in range(9):
        th = math.radians(115 + k * 26)
        pts = [(nx + r * math.cos(th + 0.05 * r * r / 4), ny + r * math.sin(th + 0.05 * r * r / 4)) for r in np.arange(2.0, 10.0, 0.5)]
        c.paint(tube(c, pts, 1.3, 1.0) & inner, EMBER, 0.67, 1.35)
    c.paint(c.line_mask([(nx + 6.4, ny - 8.4), (nx + 7.8, ny - 3.0), (nx + 7.6, ny + 3.5), (nx + 6.0, ny + 8.6)], 0.8) & shell, UMBER, 0.6, 1.4)
    c.paint(c.circle(nx - 0.4, ny, 2.1), UMBER, 1.0, 1.45)
    # mirrored pairs round the edges
    for sd in (-1, 1):
        cone(22 + sd * 14.8, 9.6, 15.0, 10.0, sd * 0.6)
        cowrie(22 + sd * 17.0, 24.0, 5.0, 7.6, 4 + sd)
        tower(22 + sd * 15.4, 36.4, 16.5, 7.0, -sd * 0.42)
        turban(22 + sd * 9.4, 4.6, 2.3)
        turban(22 + sd * 11.2, 31.0, 2.4)
    frame(c)
    return encode(c.to_tiles())


# ---------------------------------------------------------------------------
# master
# ---------------------------------------------------------------------------

def hexgrid(c, s, ox=0.0, oy=0.0):
    """Pointy-top hexagon cells of size s: returns (distance from cell centre, 0 centre .. 1 edge; cell id)."""
    X, Y = c.X - ox, c.Y - oy
    qx = (math.sqrt(3) / 3 * X - Y / 3) / s
    qz = (2 / 3 * Y) / s
    qy = -qx - qz
    rx, ry, rz = np.round(qx), np.round(qy), np.round(qz)
    dx, dy, dz = np.abs(rx - qx), np.abs(ry - qy), np.abs(rz - qz)
    fx = (dx > dy) & (dx > dz)
    fy = ~fx & (dy > dz)
    rx = np.where(fx, -ry - rz, rx)
    ry = np.where(fy, -rx - rz, ry)
    rz = np.where(~fx & ~fy, -rx - ry, rz)
    hx, hy = s * math.sqrt(3) * (rx + rz / 2), s * 1.5 * rz
    d = np.maximum.reduce([np.abs(X - hx) * 2 / math.sqrt(3), np.abs((X - hx) / math.sqrt(3) + (Y - hy)),
                           np.abs(-(X - hx) / math.sqrt(3) + (Y - hy))]) / s
    return d, (rx * 7919 + rz * 104729).astype(np.int64)


def spines(c, x, y, r0, r1, n, fam, w=0.9, off=0.0, shade=0.0):
    """n tapering spines radiating from radius r0 to r1 round (x, y)."""
    for k in range(n):
        a = off + k * 2 * math.pi / n
        c.paint(tube(c, [(x + r0 * math.cos(a), y + r0 * math.sin(a)), (x + r1 * math.cos(a), y + r1 * math.sin(a))], w, 0.45),
                fam, shade, 1.5)


def sphere(c, x, y, r, s, bar, holes, shade=0.0):
    """A lattice ball: bars of one colour, hexagonal windows coloured by depth: [(max radius, fam, shade)]."""
    d, _ = hexgrid(c, s, x, y)
    rr = np.hypot(c.X - x, c.Y - y) / r
    ball = rr <= 1
    c.paint(ball, bar, shade, 1.3)
    win = ball & (d < 0.6 - 0.3 * rr ** 4)
    for (rmax, fam, sh) in reversed(holes):
        c.paint(win & (rr <= rmax), fam, sh, 1.35)


def pores(c, m, fam, shade, ox=0, oy=0):
    """Square 2x2-tile windows on a 3-tile grid inside the mask."""
    tx, ty = tiles(c)
    inside = ndimage.binary_erosion(m, iterations=SS // 2)
    c.paint(inside & ((tx + ox) % 3 < 2) & ((ty + oy) % 3 < 2), fam, shade, 1.35)


def radiolarians():
    """Haeckel's radiolarians (Art Forms in Nature, 1904): glassy microscopic skeletons crowded on a dark
    plate - a great lattice sphere ringed by free spines in the middle, and round it a pored helmet, a
    spiny star, a spiked crown, a double lattice ball, a ringed disc, a spongy disc, a three-armed star and
    little spiked balls; every skeleton a mesh of tiny windows."""
    c = Canvas(46, 42)
    X, Y = c.X, c.Y
    c.paint(ALL(c), LAPIS, 1.0)

    # the great lattice sphere: pale bars, windows dark outside and golden over the inner shell, free spines
    spines(c, 23, 21, 10.0, 13.8, 12, PEARL, 1.4, math.pi / 12)
    sphere(c, 23, 21, 9.0, 2.0, PEARL, [(0.5, SAFFRON, 0.33), (1.0, LAPIS, 1.0)])
    c.paint(c.circle(23, 21, 1.4), UMBER, 1.0, 1.45)
    # a pored helmet (top left): domed cap on a flared bell, a horn above, three feet below
    hx, hy = 8.0, 8.6
    helm = (ellipse(c, hx, hy, 4.4, 4.6) & (Y < hy)) | c.poly_mask([(hx - 4.4, hy), (hx + 4.4, hy), (hx + 5.8, hy + 5.4), (hx - 5.8, hy + 5.4)])
    c.paint(helm, SAFFRON, 0.0, 1.3)
    pores(c, helm, LAPIS, 1.0, 1, 0)
    c.paint(c.line_mask([(hx, hy - 4.4), (hx, hy - 7.2)], 0.9), SAFFRON, 0.0, 1.4)
    for fx in (-5.4, 0.0, 5.4):
        c.paint(c.line_mask([(hx + fx, hy + 5.2), (hx + fx * 1.2, hy + 8.2)], 0.9), SAFFRON, 0.33, 1.4)
    # a spiny star (top right): red blade spines round a small pale lattice ball
    spines(c, 38.0, 9.0, 3.6, 7.4, 10, EMBER, 1.5, 0.1)
    spines(c, 38.0, 9.0, 3.6, 5.6, 10, EMBER, 1.1, 0.1 + math.pi / 10, 0.67)
    sphere(c, 38.0, 9.0, 2.8, 1.2, PEARL, [(1.0, EMBER, 1.0)])
    # a spiked crown (top centre): an arched band on a straight foot, five thorns rising from the arch
    cx_, cy_ = 23.0, 7.4
    arch = (np.abs(np.hypot((X - cx_) / 1.45, Y - cy_) - 3.3) < 0.6) & (Y < cy_)
    crown = arch | rect(c, cx_ - 5.4, cy_ - 0.4, cx_ + 5.4, cy_ + 0.7) | rect(c, cx_ - 0.5, cy_ - 3.6, cx_ + 0.5, cy_)
    for k in range(5):
        a = math.pi + (k + 1) * math.pi / 6
        bx, by = cx_ + 1.45 * 3.3 * math.cos(a), cy_ + 3.3 * math.sin(a)
        crown |= c.poly_mask([(bx - 0.7, by + 0.3), (bx + 2.6 * math.cos(a), by + 2.6 * math.sin(a)), (bx + 0.7, by + 0.3)])
    c.paint(crown, FERN, 0.33, 1.35)
    # a double lattice ball (left): a pale outer mesh over a green inner shell, pale spines
    spines(c, 6.0, 24.0, 4.0, 6.4, 8, PEARL, 0.9, 0.0)
    sphere(c, 6.0, 24.0, 4.4, 1.8, PEARL, [(0.5, FERN, 0.33), (1.0, LAPIS, 1.0)], 0.33)
    # a spiky ball (right): golden lattice over dark windows, golden spines
    spines(c, 40.5, 23.5, 4.6, 7.0, 12, SAFFRON, 0.9)
    sphere(c, 40.5, 23.5, 4.0, 1.6, SAFFRON, [(1.0, UMBER, 1.0)], 0.33)
    # a ringed disc (bottom left): separate green rings round a red heart, four spines
    dx_, dy_ = 8.5, 34.5
    rr = np.hypot(X - dx_, Y - dy_)
    c.paint(rr < 6.0, FERN, 0.33, 1.3)
    c.paint((rr < 6.0) & ((rr % 2.2) > 1.1), LAPIS, 1.0, 1.35)
    c.paint(c.circle(dx_, dy_, 1.2), EMBER, 0.33, 1.4)
    spines(c, dx_, dy_, 6.0, 8.2, 4, FERN, 1.1, math.pi / 4)
    # a spongy disc (bottom centre): red, riddled with golden pores
    sd_ = c.circle(23.5, 36.5, 4.6)
    c.paint(sd_, EMBER, 0.0, 1.3)
    pores(c, sd_, SAFFRON, 0.0, 1, 1)
    spines(c, 23.5, 36.5, 4.4, 6.0, 8, EMBER, 0.8, 0.2)
    # a three-armed star (bottom right): brown chambered arms with pale windows, round knobs at the tips
    ax, ay = 37.5, 34.0
    for k in range(3):
        a = -math.pi / 2 + k * 2 * math.pi / 3
        arm = tube(c, [(ax, ay), (ax + 6.4 * math.cos(a), ay + 6.4 * math.sin(a))], 3.0, 2.4)
        c.paint(arm, UMBER, 0.0, 1.3)
        al = (X - ax) * math.cos(a) + (Y - ay) * math.sin(a)
        c.paint(arm & (al > 1.8) & ((al % 2.0) < 1.0) & (np.abs(-(X - ax) * math.sin(a) + (Y - ay) * math.cos(a)) < 0.6), PEARL, 0.0, 1.35)
        c.paint(c.circle(ax + 6.6 * math.cos(a), ay + 6.6 * math.sin(a), 1.4), UMBER, 0.33, 1.35)
    c.paint(c.circle(ax, ay, 1.8), SAFFRON, 0.33, 1.4)
    # little spiked balls in the gaps
    for (bx, by, fam, hole) in ((15.0, 11.5, EMBER, PEARL), (31.5, 13.0, FERN, LAPIS), (15.0, 31.0, SAFFRON, UMBER), (31.0, 30.5, PEARL, EMBER)):
        spines(c, bx, by, 2.4, 3.8, 8, fam, 0.8)
        sphere(c, bx, by, 2.0, 1.1, fam, [(1.0, hole, 0.5)])
    frame(c)
    return encode(c.to_tiles())


def beetle(c, cx, cy, s, shell, sh, kind="oval", pron=UMBER, pron_sh=1.0, marks=None, mfam=UMBER, extra=None):
    """A pinned beetle seen from above, head up (about 8 x 9 tiles at s=1): six jointed legs, antennae,
    head, pronotum and the two wing cases split by a dark suture, with spots, stripes or bands."""
    T = local(cx, cy, 0.0, s)
    X, Y = c.X, c.Y
    legs = (((1.0, -1.4), (3.0, -2.4), (3.6, -4.0)), ((1.3, 0.3), (3.6, 0.4), (4.3, 1.8)), ((1.2, 1.8), (3.3, 3.4), (3.6, 5.0)))
    for sd in (-1, 1):
        for leg in legs:
            c.paint(c.line_mask([T(sd * x, y) for x, y in leg], 0.8), UMBER, 1.0, 1.5)
        if extra == "longhorn":
            c.paint(c.line_mask([T(sd * 0.5, -4.0), T(sd * 2.2, -5.0), T(sd * 3.8, -3.0), T(sd * 4.2, 1.0)], 0.5), UMBER, 1.0, 1.5)
        elif extra == "stag":
            c.paint(tube(c, [T(sd * 0.7, -4.0), T(sd * 2.2, -5.4), T(sd * 1.6, -7.0), T(sd * 0.5, -7.4)], 1.2 * s, 0.6 * s), EMBER, 1.0, 1.55)
            c.paint(c.line_mask([T(sd * 2.0, -5.8), T(sd * 0.9, -5.9)], 0.5), EMBER, 1.0, 1.55)
        else:
            c.paint(c.line_mask([T(sd * 0.5, -4.0), T(sd * 1.6, -5.4)], 0.5), UMBER, 1.0, 1.5)
    if extra == "horn":
        c.paint(tube(c, [T(0, -3.6), T(0, -5.6), T(-0.6, -6.4)], 1.4 * s, 0.6 * s), UMBER, 0.67, 1.6)
    if extra == "snout":
        c.paint(tube(c, [T(0, -3.6), T(0, -5.6)], 1.1 * s, 0.8 * s), shell, sh, 1.6)
    c.paint(ellipse(c, *T(0, -3.5), 1.1 * s, 0.9 * s), UMBER, 1.0, 1.6)
    c.paint(ellipse(c, *T(0, -2.1), 2.1 * s, 1.2 * s), pron, pron_sh, 1.6)
    if extra == "goliath":
        c.paint(ellipse(c, *T(0, -2.1), 2.1 * s, 1.2 * s) & (np.abs(np.abs(X - cx) - 0.9 * s) < 0.4), UMBER, 1.0, 1.65)
    el = ellipse(c, *T(0, 1.5), (3.3 if kind == "round" else 2.9) * s, (3.3 if kind == "round" else 3.7) * s)
    c.paint(el, shell, np.where(X < cx - 0.6, sh, min(1.0, sh + 0.33)), 1.6)
    if marks == "spots":
        for (x, y) in ((-1.4, 0.0), (1.4, 0.0), (-1.6, 2.4), (1.6, 2.4), (-0.6, 3.8), (0.6, 3.8)):
            c.paint(c.circle(*T(x, y), 0.65 * s) & el, mfam, 1.0, 1.65)
    elif marks == "stripes":
        c.paint(el & (np.abs(np.abs(X - cx) - 1.3 * s) < 0.45), mfam, 0.0, 1.65)
    elif marks == "bands":
        c.paint(el & (np.abs(((Y - cy) / s - 1.5) % 2.4 - 1.2) < 0.5), mfam, 1.0, 1.65)
    c.paint(c.line_mask([T(0, -0.9), T(0, 5.0)], 0.45) & el, UMBER, 1.0, 1.7)
    c.paint(c.circle(*T(1.1, 0.4), 0.45), PEARL, 0.0, 1.9)


def beetles():
    """The beetle drawer: a collector's drawer of card trays in three rows of four, each holding one pinned
    beetle of a different shape and colour above a blank label - a stag beetle, a ladybird, jewel beetles,
    a longhorn, a golden scarab, a rhinoceros beetle, a weevil, a wasp beetle, a goliath and more."""
    c = Canvas(46, 40)
    X, Y = c.X, c.Y
    c.paint(ALL(c), UMBER, 0.67)
    xs = [1.0 + k * 11.0 for k in range(4)]
    ys = [1.0 + k * 12.67 for k in range(3)]
    # row by row: stag beetle, ladybird, jewel beetle, longhorn / golden scarab, rhinoceros beetle, weevil,
    # wasp beetle / tiger beetle, blister beetle, goliath, ground beetle
    specs = [(EMBER, 0.67, dict(extra="stag", pron=EMBER, pron_sh=1.0)),
             (EMBER, 0.33, dict(kind="round", marks="spots")),
             (FERN, 0.33, dict(marks="stripes", mfam=SAFFRON, pron=FERN, pron_sh=0.67)),
             (LAPIS, 0.0, dict(marks="spots", extra="longhorn", pron=LAPIS, pron_sh=0.0)),
             (SAFFRON, 0.33, dict(kind="round", pron=SAFFRON, pron_sh=0.67)),
             (UMBER, 0.33, dict(extra="horn", pron=UMBER, pron_sh=0.67)),
             (LAPIS, 1.0, dict(marks="spots", mfam=SAFFRON, extra="snout", pron=LAPIS, pron_sh=1.0)),
             (SAFFRON, 0.0, dict(marks="bands", pron=UMBER)),
             (FERN, 0.67, dict(marks="spots", mfam=PEARL, pron=FERN, pron_sh=1.0)),
             (EMBER, 0.67, dict(marks="bands", pron=UMBER)),
             (UMBER, 0.0, dict(pron=PEARL, pron_sh=1.0, extra="goliath")),
             (LAPIS, 0.67, dict(marks="stripes", mfam=FERN, pron=LAPIS, pron_sh=1.0))]
    for j, y0 in enumerate(ys):
        for i, x0 in enumerate(xs):
            # the card tray, its floor shaded at the back, and a blank label below the specimen
            tray = rect(c, x0 + 1.0, y0 + 1.0, x0 + 11.0, y0 + 12.67)
            c.paint(tray, PEARL, np.where(Y < y0 + 2.0, 0.33, 0.0), 1.1)
            c.paint(rect(c, x0 + 4.0, y0 + 11.0, x0 + 8.0, y0 + 12.0), SAFFRON, 0.0, 1.3)
            fam, sh, kw = specs[j * 4 + i]
            beetle(c, x0 + 6.0, y0 + 5.9, 0.92, fam, sh, **kw)
    frame(c)
    return encode(c.to_tiles())


SCENES = {
    "flamingo": flamingo, "rose": rose, "metamorphosis": metamorphosis, "hummingbirds": hummingbirds,
    "jellyfish": jellyfish, "shells": shells, "radiolarians": radiolarians, "beetles": beetles,
}
