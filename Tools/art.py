"""Procedural mosaic artwork for Tessera Colony.

Each picture is drawn as a supersampled "semantic" illustration: every pixel carries
(family, shade, priority). A tile's colour family comes from the dominant object under it
(weighted by priority so thin veins/outlines survive), and its glaze tone (0-3) comes from
the average shading of that family inside the tile, with ordered dithering for smooth
gradients. Shading therefore never changes a tile's family - that is how colour matching
stays unambiguous even though the picture is fully shaded.
"""
import math
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

LAPIS, SAFFRON, FERN, EMBER, UMBER, PEARL = range(6)
SS = 8  # supersampling (pixels per tile) for the illustration

BAYER4 = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16.0


class Canvas:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.W, self.H = w * SS, h * SS
        ys, xs = np.mgrid[0:self.H, 0:self.W]
        self.X = (xs + 0.5) / SS
        self.Y = (ys + 0.5) / SS
        self.fam = np.full((self.H, self.W), -1, np.int8)
        self.shade = np.zeros((self.H, self.W), np.float32)
        self.prio = np.ones((self.H, self.W), np.float32)

    def paint(self, mask, family, shade, prio=1.0):
        self.fam[mask] = family
        s = shade if np.isscalar(shade) else shade[mask]
        self.shade[mask] = s
        p = prio if np.isscalar(prio) else prio[mask]
        self.prio[mask] = p

    def poly_mask(self, pts):
        img = Image.new('L', (self.W, self.H), 0)
        ImageDraw.Draw(img).polygon([(x * SS, y * SS) for x, y in pts], fill=255)
        return np.array(img) > 127

    def line_mask(self, pts, width):
        img = Image.new('L', (self.W, self.H), 0)
        d = ImageDraw.Draw(img)
        sp = [(x * SS, y * SS) for x, y in pts]
        d.line(sp, fill=255, width=max(1, int(round(width * SS))), joint='curve')
        r = width * SS / 2
        for x, y in sp:
            d.ellipse([x - r, y - r, x + r, y + r], fill=255)
        return np.array(img) > 127

    def circle(self, cx, cy, r):
        return (self.X - cx) ** 2 + (self.Y - cy) ** 2 <= r * r

    def to_tiles(self):
        """Downsample to (family, tone) tile grid."""
        grid = np.zeros((self.h, self.w, 2), np.int16)
        for ty in range(self.h):
            for tx in range(self.w):
                sl = (slice(ty * SS, (ty + 1) * SS), slice(tx * SS, (tx + 1) * SS))
                f = self.fam[sl].ravel(); s = self.shade[sl].ravel(); p = self.prio[sl].ravel()
                assert (f >= 0).all(), "unpainted pixel at tile %d,%d" % (tx, ty)
                weights = np.bincount(f, weights=p, minlength=6)
                fam = int(np.argmax(weights))
                sel = f == fam
                shade = float(np.average(s[sel], weights=p[sel]))
                d = (BAYER4[ty % 4, tx % 4] - 0.47) * 0.85
                tone = int(np.clip(np.floor(shade * 3.0 + 0.5 + d), 0, 3))
                grid[ty, tx] = (fam, tone)
        return grid


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


# ---------------------------------------------------------------------------
# Showcase: "Sunflower & Monarch" (72 x 84 tiles)
# ---------------------------------------------------------------------------

def sunflower(c, cx, cy, disk_r, petal_len, petal_w, n_petals, rot=0.0, seeds=True):
    X, Y = c.X - cx, c.Y - cy
    R = np.hypot(X, Y)
    A = np.arctan2(Y, X)
    # back ring then front ring of petals
    for ring, (ln, off, dark) in enumerate([(petal_len * 0.86, math.pi / n_petals, 0.22), (petal_len, 0.0, 0.0)]):
        for k in range(n_petals):
            a = rot + off + 2 * math.pi * k / n_petals + 0.05 * math.sin(k * 2.3)
            dx, dy = math.cos(a), math.sin(a)
            along = X * dx + Y * dy
            perp = -X * dy + Y * dx
            rd = disk_r - 0.6 + ln / 2
            u = (along - rd) / (ln / 2)
            half_w = petal_w / 2 * np.sqrt(np.clip(1 - np.abs(u) ** 1.6, 0, 1))
            m = (np.abs(u) <= 1) & (np.abs(perp) <= half_w)
            frac = np.clip((along - (disk_r - 0.6)) / ln, 0, 1)
            side = np.abs(perp) / (petal_w / 2)
            shade = 0.85 - 0.75 * frac + 0.22 * side + dark
            # a faint centre crease on each petal
            shade = shade + 0.18 * (np.abs(perp) < 0.18)
            c.paint(m, SAFFRON, np.clip(shade, 0, 1))
    # disk
    dm = R <= disk_r
    base = 0.45 + 0.4 * smoothstep(disk_r * 0.72, disk_r, R) - 0.35 * (1 - smoothstep(0, disk_r * 0.35, R))
    c.paint(dm, UMBER, np.clip(base, 0, 1), 1.0)
    if seeds:
        n = int(disk_r * disk_r * 4.2)
        golden = math.pi * (3 - math.sqrt(5))
        seed_mask = np.zeros_like(dm)
        for i in range(n):
            r = disk_r * 0.93 * math.sqrt((i + 0.5) / n)
            a = i * golden
            sx, sy = cx + r * math.cos(a), cy + r * math.sin(a)
            rr = 0.36 + 0.1 * r / disk_r
            seed_mask |= (c.X - sx) ** 2 + (c.Y - sy) ** 2 <= rr * rr
        c.paint(dm & seed_mask & (R > disk_r * 0.3), UMBER, 0.98, 1.0)


def leaf(c, bx, by, tx, ty, width, bend=0.12, lighter=0.0):
    """Leaf from base (bx,by) to tip (tx,ty) with midrib and veins."""
    L = math.hypot(tx - bx, ty - by)
    dx, dy = (tx - bx) / L, (ty - by) / L
    X, Y = c.X - bx, c.Y - by
    s = X * dx + Y * dy
    t = -X * dy + Y * dx
    u = np.clip(s / L, 0, 1)
    t_axis = bend * L * (u - u * u) * 2.2   # curved axis
    tt = t - t_axis
    half = width / 2 * np.power(np.sin(np.pi * u), 0.75)
    m = (s >= 0) & (s <= L) & (np.abs(tt) <= half)
    side = tt / np.maximum(half, 1e-3)
    shade = 0.64 + 0.1 * np.sign(side) + 0.06 * u - lighter
    shade = np.where(np.abs(tt) > half - 0.5, 1.0, shade)
    vein_phase = (s - np.abs(tt) * 0.9) / 3.0
    veins = (np.abs(vein_phase - np.round(vein_phase)) < 0.09) & (np.abs(tt) < half * 0.85) & (u > 0.08)
    shade = np.where(veins, 0.2, shade)
    shade = np.where(np.abs(tt) < 0.4, 0.05, shade)  # midrib
    c.paint(m, FERN, np.clip(shade, 0, 1))


def butterfly(c, cx, cy, scale=1.0, tilt=-0.26):
    ca, sa = math.cos(tilt), math.sin(tilt)

    def T(px, py):
        px, py = px * scale, py * scale
        return (cx + px * ca - py * sa, cy + px * sa + py * ca)

    fore = [(0.7, -1.2), (3.5, -5.5), (7.5, -8.8), (11.2, -9.6), (12.6, -8.2), (12.4, -5.0), (10.8, -1.6), (7.0, 0.2), (1.0, 0.6)]
    hind = [(0.9, 0.6), (5.0, 0.8), (9.0, 1.8), (10.2, 4.6), (8.8, 8.2), (5.6, 10.0), (2.8, 9.0), (1.2, 5.6), (0.6, 2.2)]
    fore_veins = [[(0.9, -0.4), (6.0, -4.4), (11.3, -9.0)], [(0.9, -0.2), (7.0, -3.4), (12.4, -6.4)],
                  [(0.9, 0.0), (7.0, -2.2), (11.8, -3.2)], [(1.0, 0.3), (6.5, -0.8), (10.4, -1.4)],
                  [(4.2, -3.0), (6.9, -2.2)]]
    hind_veins = [[(1.0, 0.8), (6.0, 1.9), (9.9, 3.2)], [(1.0, 1.2), (6.0, 4.0), (9.4, 6.6)],
                  [(1.0, 1.6), (4.8, 5.6), (6.8, 9.2)], [(1.0, 2.0), (2.8, 5.6), (3.8, 9.2)]]
    for side in (1, -1):
        for shape, veins, dark in ((hind, hind_veins, 0.1), (fore, fore_veins, 0.0)):
            pts = [T(side * x, y) for x, y in shape]
            m = c.poly_mask(pts)
            m = ndimage.binary_closing(m, iterations=3)
            dist = ndimage.distance_transform_edt(m) / SS
            r = np.hypot(c.X - cx, c.Y - cy) / scale
            shade = np.clip(0.66 - 0.42 * np.clip(r / 11.0, 0, 1) + dark, 0, 1)
            c.paint(m, EMBER, shade)
            # black-brown veins
            for v in veins:
                vm = c.line_mask([T(side * x, y) for x, y in v], 0.36 * scale) & m & (r > 3.4)
                c.paint(vm, UMBER, 0.95, 1.3)
            # margin band
            margin = m & (dist < 0.8 * scale) & (r > 3.6)
            c.paint(margin, UMBER, 0.92, 1.45)
            # pearl spots inside the margin band
            band = m & (dist > 0.4 * scale) & (dist < 0.6 * scale)
            ys, xs = np.nonzero(band)
            if len(xs):
                pcx, pcy = xs.mean(), ys.mean()
                ang = np.arctan2(ys - pcy, xs - pcx)
                bins = np.floor((ang + math.pi) / (2 * math.pi) * 13).astype(int)
                for b in np.unique(bins):
                    idx = np.nonzero(bins == b)[0]
                    j = idx[len(idx) // 2]
                    sx, sy = (xs[j] + 0.5) / SS, (ys[j] + 0.5) / SS
                    c.paint(c.circle(sx, sy, 0.36 * scale) & m, PEARL, 0.1, 2.2)
    # body + head + antennae
    body = c.line_mask([T(0, -2.2), T(0, 5.4)], 1.2 * scale)
    c.paint(body, UMBER, 0.95, 2.4)
    head = c.circle(*T(0, -2.9), 0.95 * scale)
    c.paint(head, UMBER, 1.0, 3.0)
    for side in (1, -1):
        ant = c.line_mask([T(side * 0.3, -3.4), T(side * 1.6, -6.2), T(side * 2.6, -8.0)], 0.38 * scale)
        c.paint(ant, UMBER, 1.0, 3.0)
        c.paint(c.circle(*T(side * 2.75, -8.25), 0.5 * scale), UMBER, 1.0, 3.0)
    # a few pearl dots on the thorax
    for yy in (-1.4, -0.4):
        c.paint(c.circle(*T(0.0, yy), 0.28 * scale), PEARL, 0.2, 3.2)


def daisy(c, cx, cy, r=1.4):
    for k in range(6):
        a = k * math.pi / 3 + 0.3
        c.paint(c.circle(cx + r * 0.75 * math.cos(a), cy + r * 0.75 * math.sin(a), r * 0.48), PEARL, 0.25 + 0.1 * (k % 2), 1.4)
    c.paint(c.circle(cx, cy, r * 0.42), SAFFRON, 0.4, 1.6)


def meander_border(c, band=5):
    """Umber outer line, a running-wave band of Ember on Pearl, and an Umber inner line."""
    X, Y, w, h = c.X, c.Y, c.w, c.h
    dl, dr, dt, db = X, w - X, Y, h - Y
    d = np.minimum.reduce([dl, dr, dt, db])
    along = np.where((d == dt) | (d == db), X, Y)
    outer = d < 1
    c.paint(outer, UMBER, 0.72, 1.2)
    bandm = (d >= 1) & (d < band - 1)
    depth = d - 1
    rows = band - 2
    period = 8.0
    ph = 2 * np.pi * along / period
    centre = rows / 2 + (rows / 2 - 0.55) * np.sin(ph)
    slope = (rows / 2 - 0.55) * 2 * np.pi / period * np.cos(ph)
    dist = np.abs(depth - centre) / np.sqrt(1 + slope * slope)
    wave = bandm & (dist < 0.62)
    c.paint(bandm, PEARL, np.clip(0.12 + 0.3 * depth / rows, 0, 1))
    c.paint(wave, EMBER, np.clip(0.3 + 0.45 * depth / rows, 0, 1), 1.3)
    cs = band - 1
    for (x0, y0) in ((0, 0), (w - cs, 0), (0, h - cs), (w - cs, h - cs)):
        m = (X >= x0) & (X < x0 + cs) & (Y >= y0) & (Y < y0 + cs) & (d >= 1)
        c.paint(m, PEARL, 0.1)
        mx, my = x0 + cs / 2, y0 + cs / 2
        dia = m & (np.abs(X - mx) + np.abs(Y - my) < cs * 0.42)
        c.paint(dia, EMBER, 0.6, 1.3)
    inner = (d >= band - 1) & (d < band)
    c.paint(inner, UMBER, 0.9, 1.2)


def showcase():
    W, H = 72, 84
    c = Canvas(W, H)
    B = 5  # border thickness
    X, Y = c.X, c.Y
    u, v = X - B, Y - B
    inner = (X >= B) & (X < W - B) & (Y >= B) & (Y < H - B)
    # sky gradient (deep at top, pale at the horizon) with a soft sun glow
    horizon = 50.0
    sky_shade = np.clip(0.98 - 0.93 * (v / horizon), 0, 1)
    glow = np.exp(-(((u - 44) / 16) ** 2 + ((v - 44) / 11) ** 2))
    sky_shade = np.clip(sky_shade - 0.28 * glow, 0, 1)
    c.paint(inner, LAPIS, sky_shade)
    # clouds
    def cloud(cxs, cys, rs):
        m = np.zeros_like(inner)
        for (a, b, r) in zip(cxs, cys, rs):
            m |= c.circle(a + B, b + B, r)
        cy_mean = np.mean(cys) + B
        flat = Y <= cy_mean + max(rs) * 0.45
        m &= flat
        top = min(b - r for b, r in zip(cys, rs)) + B
        sh = np.clip(0.05 + 0.85 * (Y - top) / (cy_mean + max(rs) * 0.45 - top), 0, 1) ** 1.3
        c.paint(m & inner, PEARL, sh, 1.0)
    cloud([9, 14, 19, 24, 5], [11, 8, 9, 12, 13], [3.2, 4.3, 3.8, 2.8, 2.4])
    cloud([40, 45, 50, 55], [40, 37.5, 38.5, 41], [2.6, 3.5, 3.0, 2.2])
    cloud([30, 34, 37], [4, 2.5, 4.5], [1.8, 2.4, 1.7])
    # back hills
    back = inner & (v > 47.5 + 3.2 * np.sin(u * 0.13 + 0.6) + 1.2 * np.sin(u * 0.41))
    c.paint(back, FERN, np.clip(0.02 + 0.12 * (np.sin(u * 0.9 + v * 0.6) > 0.7), 0, 1))
    # front meadow with grass blades
    front_edge = 57.5 + 2.2 * np.sin(u * 0.2 + 2.4) + 0.8 * np.sin(u * 0.7)
    front = inner & (v > front_edge)
    blades = 0.5 + 0.5 * np.sin(u * 2.3 + 1.7 * np.sin(v * 0.9) + v * 0.35)
    c.paint(front, FERN, np.clip(0.3 + 0.012 * (v - front_edge) + 0.3 * (blades - 0.5), 0, 1))
    # small daisies in the meadow
    for (a, b) in ((6, 66), (12, 70.5), (4, 72), (40, 67), (47, 71.5), (55, 66.5), (58, 72), (33, 72.5), (51, 62.5)):
        daisy(c, a + B, b + B, 1.35)
    # main sunflower stem
    stem_pts = [(22.5 + 2.6 * math.sin(t * 1.7) + B, 34 + t * 41 + B) for t in np.linspace(0, 1, 30)]
    stem = c.line_mask(stem_pts, 2.3) & inner
    stem_x = np.interp(Y, [p[1] for p in stem_pts], [p[0] for p in stem_pts])
    c.paint(stem, FERN, np.clip(0.8 + 0.3 * (X - stem_x), 0, 1))
    # leaves
    leaf(c, 23.0 + B, 49 + B, 4.0 + B, 41.5 + B, 8.0, bend=-0.14)
    leaf(c, 25.2 + B, 58.5 + B, 45.5 + B, 52.5 + B, 8.6, bend=0.16)
    leaf(c, 23.8 + B, 66.5 + B, 9.5 + B, 60.5 + B, 5.6, bend=-0.1, lighter=0.08)
    # second, younger sunflower on the right
    stem2 = [(50.5 + 0.9 * math.sin(t * 2.4) + B, 47 + t * 28 + B) for t in np.linspace(0, 1, 20)]
    c.paint(c.line_mask(stem2, 1.5) & inner, FERN, 0.9)
    leaf(c, 50.6 + B, 60 + B, 59.5 + B, 55.5 + B, 4.2, bend=0.12)
    sunflower(c, 50.3 + B, 45.2 + B, 3.1, 4.4, 2.2, 14, rot=0.2)
    # main sunflower head
    sunflower(c, 22.0 + B, 26.5 + B, 7.6, 8.4, 3.3, 21, rot=0.1)
    # monarch butterfly
    butterfly(c, 45.5 + B, 17.0 + B, scale=1.22)
    meander_border(c, band=B)
    return c.to_tiles()


# ---------------------------------------------------------------------------
# Tutorial: "Ladybird" (36 x 28 tiles)
# ---------------------------------------------------------------------------

def tutorial():
    W, H = 36, 28
    c = Canvas(W, H)
    X, Y = c.X, c.Y
    allm = np.ones_like(X, bool)
    c.paint(allm, LAPIS, np.clip(0.8 - 0.6 * Y / H + 0.04 * np.sin(X * 0.7), 0, 1))
    # a small cloud
    cl = (c.circle(6, 5, 2.2) | c.circle(9, 4, 2.8) | c.circle(12, 5.2, 2.0)) & (Y < 6.6)
    c.paint(cl, PEARL, np.clip((Y - 1.5) / 5.5, 0, 1))
    leaf(c, 1.0, 27.5, 35.0, 4.0, 17.0, bend=0.06)
    cx, cy, rx, ry = 18.5, 15.5, 5.6, 6.3
    # legs
    for side in (1, -1):
        for k, yy in enumerate((12.5, 15.5, 18.5)):
            c.paint(c.line_mask([(cx + side * 4.6, yy), (cx + side * 7.0, yy + (k - 1) * 1.3)], 0.55), UMBER, 0.95, 1.6)
    shell = ((X - cx) / rx) ** 2 + ((Y - cy) / ry) ** 2 <= 1
    sh = np.clip(0.62 + 0.22 * ((X - cx) / rx + (Y - cy) / ry), 0, 1)
    sh = np.where((X - 16.3) ** 2 + (Y - 11.4) ** 2 < 1.1, 0.1, sh)
    c.paint(shell, EMBER, sh)
    c.paint(shell & (np.abs(X - cx) < 0.36) & (Y > cy - ry + 1.2), UMBER, 0.95, 2.0)
    for (a, b, r) in ((15.8, 13.2, 1.15), (21.2, 13.2, 1.15), (15.2, 17.6, 1.3), (21.8, 17.6, 1.3), (17.0, 20.6, 0.95), (20.0, 20.6, 0.95)):
        c.paint(c.circle(a, b, r) & shell, UMBER, 0.85, 1.6)
    head = ((X - cx) / 3.0) ** 2 + ((Y - (cy - ry + 0.3)) / 2.1) ** 2 <= 1
    c.paint(head & (Y < cy - ry + 1.2), UMBER, 0.9, 1.5)
    for a in (cx - 1.2, cx + 1.2):
        c.paint(c.circle(a, cy - ry - 0.2, 0.45), PEARL, 0.05, 2.6)
    d = np.minimum.reduce([X, W - X, Y, H - Y])
    c.paint(d < 1, UMBER, 0.7, 1.2)
    return c.to_tiles()


# ---------------------------------------------------------------------------
# Koi Pond (44 x 56)
# ---------------------------------------------------------------------------

def koi(c, cx, cy, length, angle, body_fam, patch_fam, seed, bend=0.35):
    """A koi seen from above, built as a polygon around a gently curved spine: rounded head,
    tapering body, a forked tail, two pectoral fins, colour patches and eyes."""
    import random
    rnd = random.Random(seed)
    ca, sa = math.cos(angle), math.sin(angle)

    def spine(u):  # u: 0 tail .. 1 head  -> world point and unit normal
        s_ = (u - 0.5) * length
        off = bend * length * 0.12 * math.sin(math.pi * u)
        px = cx + s_ * ca - off * sa
        py = cy + s_ * sa + off * ca
        # tangent by finite difference
        e = 1e-3
        s2 = (u + e - 0.5) * length
        off2 = bend * length * 0.12 * math.sin(math.pi * (u + e))
        tx = (cx + s2 * ca - off2 * sa) - px
        ty = (cy + s2 * sa + off2 * ca) - py
        l = math.hypot(tx, ty)
        return px, py, -ty / l, tx / l

    def half_width(u):
        # widest just behind the head, narrow at the tail root
        return length * 0.14 * (math.sin(math.pi * min(1.0, 0.18 + u * 0.95)) ** 0.8) + 0.25

    ts = np.linspace(0.12, 1.0, 40)
    left, right = [], []
    for u in ts:
        px, py, nx, ny = spine(u)
        w = half_width(u)
        left.append((px + nx * w, py + ny * w))
        right.append((px - nx * w, py - ny * w))
    body = c.poly_mask(left + right[::-1])
    hx, hy, _, _ = spine(0.97)
    body |= c.circle(hx, hy, half_width(0.9) * 0.95)
    # tail fork
    tx0, ty0, nx0, ny0 = spine(0.12)
    ex, ey = tx0 - ca * length * 0.2, ty0 - sa * length * 0.2
    wing = length * 0.13
    tail = c.poly_mask([(tx0 + nx0 * 0.4, ty0 + ny0 * 0.4), (ex + nx0 * wing, ey + ny0 * wing),
                        (tx0 - ca * length * 0.09, ty0 - sa * length * 0.09),
                        (ex - nx0 * wing, ey - ny0 * wing), (tx0 - nx0 * 0.4, ty0 - ny0 * 0.4)])
    c.paint(tail & ~body, body_fam, 0.45, 1.1)
    # pectoral fins
    fx, fy, fnx, fny = spine(0.72)
    for side in (-1, 1):
        w = half_width(0.72)
        px_, py_ = fx + side * fnx * (w + 0.9) - ca * 1.0, fy + side * fny * (w + 0.9) - sa * 1.0
        fin = c.circle(px_, py_, 1.2) & ~body
        c.paint(fin, body_fam, 0.5, 1.1)
    # body shading: lighter along the spine
    X, Y = c.X, c.Y
    dist_c = np.full(X.shape, 99.0)
    for u in np.linspace(0.12, 1.0, 20):
        px, py, _, _ = spine(u)
        dist_c = np.minimum(dist_c, np.hypot(X - px, Y - py))
    shade = np.clip(0.1 + 0.55 * dist_c / (length * 0.14), 0, 1)
    c.paint(body, body_fam, shade)
    # patches
    for k in range(4):
        u = rnd.uniform(0.3, 0.92)
        px, py, nx, ny = spine(u)
        o = rnd.uniform(-0.5, 0.5) * half_width(u)
        r = rnd.uniform(0.9, 1.6) * length / 16
        m = body & c.circle(px + nx * o, py + ny * o, r)
        c.paint(m, patch_fam, np.clip(0.2 + 0.5 * dist_c / (length * 0.14), 0, 1), 1.2)
    # eyes
    for side in (-1, 1):
        px, py, nx, ny = spine(0.93)
        w = half_width(0.93) * 0.62
        c.paint(c.circle(px + side * nx * w, py + side * ny * w, 0.42), UMBER, 1.0, 2.6)


def koi_pond():
    W, H = 44, 56
    c = Canvas(W, H)
    X, Y = c.X, c.Y
    allm = np.ones_like(X, bool)
    # water: deep at the bottom, ripple bands
    rip = 0.5 + 0.5 * np.sin(np.hypot(X - 30, Y - 14) * 1.3)
    rip2 = 0.5 + 0.5 * np.sin(np.hypot(X - 10, Y - 40) * 1.1)
    water = np.clip(0.35 + 0.45 * Y / H + 0.14 * (rip - 0.5) + 0.1 * (rip2 - 0.5), 0, 1)
    c.paint(allm, LAPIS, water)
    # lily pads with a notch and veins
    def pad(px, py, r, notch_a, flower=False):
        R = np.hypot(X - px, Y - py); A = np.arctan2(Y - py, X - px)
        d = np.angle(np.exp(1j * (A - notch_a)))
        m = (R < r) & (np.abs(d) > 0.28)
        sh = np.clip(0.35 + 0.35 * R / r, 0, 1)
        vein = (np.abs(np.sin(A * 5)) < 0.12) & (R > 0.8)
        sh = np.where(vein, 0.9, sh)
        sh = np.where(R > r - 0.55, 1.0, sh)
        c.paint(m, FERN, sh)
        if flower:
            for k in range(8):
                a = k * math.pi / 4 + 0.2
                c.paint(c.circle(px + 1.3 * math.cos(a), py + 1.3 * math.sin(a), 1.05), PEARL, 0.15 + 0.1 * (k % 2), 1.4)
            for k in range(5):
                a = k * 2 * math.pi / 5
                c.paint(c.circle(px + 0.6 * math.cos(a), py + 0.6 * math.sin(a), 0.7), EMBER, 0.05, 1.5)
            c.paint(c.circle(px, py, 0.7), SAFFRON, 0.2, 1.8)
    pad(9, 10, 5.5, 0.6, flower=True)
    pad(34, 44, 6.5, 2.4)
    pad(35, 8, 3.6, 3.6)
    pad(7, 47, 4.2, -0.8, flower=True)
    pad(22, 27, 2.6, 1.2)
    # koi
    koi(c, 25, 18, 19, 0.5, PEARL, EMBER, 3, bend=0.9)
    koi(c, 17, 38, 17, -2.5, SAFFRON, PEARL, 8, bend=-0.9)
    koi(c, 33, 30, 13, 2.0, EMBER, PEARL, 11, bend=0.7)
    # stone rim
    d = np.minimum.reduce([X, W - X, Y, H - Y])
    stones = 0.5 + 0.5 * np.sin(X * 1.7) * np.sin(Y * 1.9)
    c.paint(d < 1.6, UMBER, np.clip(0.3 + 0.5 * stones, 0, 1), 1.2)
    c.paint((d >= 1.6) & (d < 2.2), UMBER, 0.95, 1.2)
    return c.to_tiles()


# ---------------------------------------------------------------------------
# Peacock Fan (52 x 52)
# ---------------------------------------------------------------------------

def peacock():
    W, H = 52, 52
    c = Canvas(W, H)
    X, Y = c.X, c.Y
    allm = np.ones_like(X, bool)
    cx, cy = 26.0, 44.0
    R = np.hypot(X - cx, Y - cy); A = np.arctan2(Y - cy, X - cx)
    # warm dark background with a soft halo
    c.paint(allm, UMBER, np.clip(0.95 - 0.3 * np.exp(-((R - 20) / 12) ** 2), 0, 1))
    # fan: feathers between angles -170..-10 degrees
    fan = (R < 40) & (A < -0.1) & (A > -math.pi + 0.1)
    c.paint(fan, FERN, np.clip(0.25 + 0.5 * R / 40 + 0.1 * np.sin(A * 40), 0, 1))
    # thin feather shafts
    for k in range(27):
        a = -math.pi + 0.18 + k * (math.pi - 0.36) / 26
        shaft = fan & (np.abs(np.angle(np.exp(1j * (A - a)))) * R < 0.28) & (R > 9)
        c.paint(shaft, FERN, 0.0, 1.05)
    # three staggered rows of eye-spots
    for rr, n, size in ((35.0, 13, 1.0), (27.0, 10, 0.85), (19.5, 7, 0.72)):
        for k in range(n):
            a = -math.pi + 0.3 + k * (math.pi - 0.6) / (n - 1)
            ex, ey = cx + rr * math.cos(a), cy + rr * math.sin(a)
            ca_, sa_ = math.cos(a), math.sin(a)
            s_ = (X - ex) * ca_ + (Y - ey) * sa_
            t_ = -(X - ex) * sa_ + (Y - ey) * ca_
            e = np.hypot(s_ / (3.1 * size), t_ / (2.4 * size))
            c.paint(fan & (e < 1.0), SAFFRON, 0.25, 1.2)
            c.paint(fan & (e < 0.8), FERN, 0.95, 1.3)
            c.paint(fan & (e < 0.62), LAPIS, 0.5, 1.4)
            c.paint(fan & (e < 0.38), UMBER, 1.0, 1.6)
    # body: lapis teardrop with a darker wing
    bx, by = cx, cy - 4
    body = (((X - bx) / 5.0) ** 2 + ((Y - by) / 8.0) ** 2 < 1) & (Y > by - 8.0)
    c.paint(body, LAPIS, np.clip(0.4 + 0.35 * (X - bx) / 5.0 + 0.1 * (Y - by) / 8.0, 0, 1), 1.3)
    wing = body & (((X - (bx + 2.0)) / 3.2) ** 2 + ((Y - (by + 2.5)) / 5.2) ** 2 < 1)
    c.paint(wing, FERN, 0.75, 1.1)
    neck = c.line_mask([(bx - 0.2, by - 5), (bx - 1.2, by - 9.5), (bx - 0.8, by - 13)], 2.6)
    c.paint(neck, LAPIS, 0.55, 1.3)
    head = c.circle(bx - 0.6, by - 14.2, 2.0)
    c.paint(head, LAPIS, 0.45, 1.3)
    c.paint(c.circle(bx - 1.1, by - 14.6, 0.55), PEARL, 0.05, 2.5)
    c.paint(c.line_mask([(bx - 2.2, by - 14.2), (bx - 3.6, by - 13.7)], 0.7), SAFFRON, 0.6, 2.0)
    for k in range(3):
        c.paint(c.line_mask([(bx - 0.5, by - 16), (bx - 1.6 + k * 1.1, by - 19)], 0.35), UMBER, 0.2, 2.0)
        c.paint(c.circle(bx - 1.6 + k * 1.1, by - 19.2, 0.5), LAPIS, 0.3, 2.2)
    # ground line
    c.paint(Y > H - 3.5, UMBER, 0.55, 1.1)
    # frame
    d = np.minimum.reduce([X, W - X, Y, H - Y])
    c.paint(d < 1, SAFFRON, 0.6, 1.3)
    return c.to_tiles()


# ---------------------------------------------------------------------------
# Night Market (56 x 64)
# ---------------------------------------------------------------------------

def night_market():
    W, H = 56, 64
    c = Canvas(W, H)
    X, Y = c.X, c.Y
    allm = np.ones_like(X, bool)
    c.paint(allm, LAPIS, np.clip(1.0 - 0.6 * Y / 34, 0.3, 1))
    import random
    rnd = random.Random(12)
    for k in range(30):
        sx, sy = rnd.uniform(2, W - 2), rnd.uniform(2, 24)
        c.paint(c.circle(sx, sy, rnd.choice([0.45, 0.55, 0.7])), PEARL, rnd.choice([0.0, 0.2]), 2.0)
    moon = c.circle(28, 5.6, 3.9) & ~c.circle(29.9, 4.6, 3.4)
    c.paint(moon, SAFFRON, np.clip(0.1 + 0.08 * (Y - 2), 0, 0.6), 1.5)
    # skyline: simple buildings with pitched roofs and lit windows
    bx = 0.0
    bi = 0
    while bx < W:
        bw = rnd.choice([6, 7, 8, 9])
        top = rnd.uniform(24, 30)
        bld = (X >= bx) & (X < bx + bw) & (Y >= top) & (Y < 40)
        roof = (Y >= top - (bw / 2 - np.abs(X - (bx + bw / 2))) * 0.6) & (Y < top) & (X >= bx) & (X < bx + bw)
        c.paint(bld | roof, UMBER, 0.95 if bi % 2 else 0.85)
        for wy in np.arange(top + 1.5, 38, 3.0):
            for wx in np.arange(bx + 1.5, bx + bw - 1.5, 2.5):
                if rnd.random() < 0.55:
                    c.paint((np.abs(X - wx) < 0.6) & (np.abs(Y - wy) < 0.7), SAFFRON, 0.3, 1.4)
        bx += bw
        bi += 1
    # two strings of lanterns across the sky
    for (y0, amp, n, fams) in ((11, 3.5, 7, (EMBER, SAFFRON)), (19, 3.0, 6, (SAFFRON, EMBER))):
        xs = np.linspace(0, W, 60)
        pts = [(x, y0 + amp * math.sin(x / W * math.pi)) for x in xs]
        c.paint(c.line_mask(pts, 0.35), UMBER, 0.95, 1.3)
        for k in range(n):
            fam = fams[k % 2]
            lx = (k + 0.5) * W / n
            ly = y0 + amp * math.sin(lx / W * math.pi) + 2.6
            body = ((X - lx) / 2.0) ** 2 + ((Y - ly) / 2.5) ** 2 < 1
            sh = np.clip(0.1 + 0.55 * np.abs(X - lx) / 2.0, 0, 1)
            ribs = np.abs(np.sin((X - lx) * 1.9)) < 0.18
            c.paint(body, fam, np.where(ribs, 0.95, sh), 1.4)
            c.paint((np.abs(X - lx) < 1.0) & (np.abs(Y - (ly - 2.7)) < 0.5), UMBER, 0.9, 1.6)
            c.paint((np.abs(X - lx) < 0.35) & (Y > ly + 2.3) & (Y < ly + 3.9), fam, 0.8, 1.6)
    # market stalls
    stall_y = 40.0
    c.paint((Y >= stall_y) & (Y < 57), UMBER, 0.98)
    for (x0, x1, fa, fb) in ((1, 19, EMBER, PEARL), (19, 37, FERN, PEARL), (37, 55, EMBER, SAFFRON)):
        aw = (X >= x0) & (X < x1) & (Y >= stall_y) & (Y < stall_y + 4 + 0.9 * np.abs(np.sin((X - x0) * math.pi / 3)))
        stripe = (np.floor((X - x0) / 3.0) % 2) == 0
        c.paint(aw & stripe, fa, np.clip(0.25 + 0.1 * (Y - stall_y), 0, 1), 1.2)
        c.paint(aw & ~stripe, fb, np.clip(0.05 + 0.1 * (Y - stall_y), 0, 1), 1.2)
        posts = ((np.abs(X - (x0 + 0.8)) < 0.55) | (np.abs(X - (x1 - 0.8)) < 0.55)) & (Y >= stall_y + 4) & (Y < 57)
        c.paint(posts, UMBER, 0.6, 1.3)
        # shelves of goods: rows of round fruit, each stall with its own colours
        goods = {EMBER: (SAFFRON, EMBER), FERN: (FERN, PEARL), PEARL: (PEARL, EMBER)}
        g1, g2 = goods.get(fa, (SAFFRON, FERN)) if fa != EMBER or x0 < 30 else (FERN, SAFFRON)
        for row, gy in enumerate((47.0, 50.2)):
            c.paint((X > x0 + 1.4) & (X < x1 - 1.4) & (np.abs(Y - (gy + 1.3)) < 0.35), UMBER, 0.55, 1.2)
            for gx in np.arange(x0 + 2.8, x1 - 2.0, 2.7):
                c.paint(c.circle(gx, gy, 0.95), g1 if row == 0 else g2, 0.3, 1.5)
        counter = (X >= x0) & (X < x1) & (Y >= 53) & (Y < 57)
        c.paint(counter, UMBER, np.clip(0.2 + 0.25 * (np.sin(Y * 2.5) ** 2), 0, 1), 1.1)
    # cobblestone street
    street = Y >= 57
    cob = (np.abs(np.sin(X * 1.6 + np.floor(Y) * 1.3)) < 0.22) | (np.abs(np.sin(Y * 3.1)) < 0.2)
    c.paint(street, PEARL, np.where(cob, 0.95, 0.5 + 0.25 * np.sin(X * 0.7) ** 2))
    d = np.minimum.reduce([X, W - X, Y, H - Y])
    c.paint(d < 1, UMBER, 0.75, 1.2)
    return c.to_tiles()


def encode(grid):
    alphabet = "abcdefghijklmnopqrstuvwx"
    rows = []
    for row in grid:
        rows.append("".join(alphabet[f * 4 + t] for f, t in row))
    return rows


if __name__ == "__main__":
    import json, sys
    out = {"showcase": encode(showcase()), "tutorial": encode(tutorial()),
           "koi": encode(koi_pond()), "peacock": encode(peacock()), "market": encode(night_market())}
    from art_challenge import CHALLENGE_ART
    for key, fn in CHALLENGE_ART.items():
        out[key] = encode(fn())
    json.dump(out, open(sys.argv[1] if len(sys.argv) > 1 else "art.json", "w"))
    print("ok")
