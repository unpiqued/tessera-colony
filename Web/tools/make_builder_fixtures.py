#!/usr/bin/env python3
"""Fixtures for Web/test/builders.test.js (pattern, photo, level generator, difficulty probe).

Usage: python3 make_builder_fixtures.py [out_dir]      (default: ../test/fixtures)

Writes builders.json plus the photo inputs as gzipped raw RGBA (photo_<name>.rgba.gz, row 0 at the
top, 4 bytes per pixel), so the JS builders and this script read exactly the same pixels.

Sources of truth, in order: the Swift code, then the Python models in ../../Tools.
  * Pattern art rows come straight from Tools/pattern.py (pattern_rows / pattern_layout).
  * LevelGenerator: Tools/generate_levels.py design_sequence / deal, driven by SwiftRng below —
    Swift's SplitMix64 behind the random.Random calls those functions make (random, choice,
    choices) — plus mirrors of LevelGenerator.verify / generate (8 attempts, verify at maxWait).
  * Photo: Tools/photo.py's grid_size / downsample / Lab maths, and a scalar mirror of
    PhotoLevelBuilder.swift for the steps where photo.py differs from Swift (k-means seeding,
    summation order, rounding, colour names, planning). photo.py's own result is stored too
    ("photo_py") so the test can report how far the reference model is from the Swift code.
  * DifficultyProbe: a Python mirror on Tools/engine.py (Game, rollout).
"""
import gzip
import json
import math
import pathlib
import sys
import time
from multiprocessing import Pool

HERE = pathlib.Path(__file__).resolve().parent
WEB = HERE.parent
TOOLS = WEB.parent / "Tools"
sys.path.insert(0, str(TOOLS))

import numpy as np  # noqa: E402

import generate_levels as GL  # noqa: E402
import pattern as PAT  # noqa: E402
import photo as PH  # noqa: E402
from engine import Board, Game, rollout as engine_rollout  # noqa: E402

M64 = (1 << 64) - 1


# ---------------------------------------------------------------------------------------------
# Swift SplitMix64 with the random.Random surface used by generate_levels.design_sequence / deal
# ---------------------------------------------------------------------------------------------

class SwiftRng:
    def __init__(self, seed):
        self.g = PH.SplitMix64(seed & M64)

    def next(self):
        return self.g.next()

    def unit(self):
        return self.g.unit()

    def int(self, n):
        return 0 if n <= 1 else self.g.next() % n

    def weighted(self, weights):
        total = 0.0
        for w in weights:            # sequential, like Swift's reduce(0, +)
            total += w
        if total <= 0:
            return self.int(len(weights))
        r = self.unit() * total
        for i, w in enumerate(weights):
            r -= w
            if r < 0:
                return i
        return len(weights) - 1

    # random.Random surface (Swift: rng.unit(), xs[rng.int(xs.count)], xs[rng.weighted(w)])
    def random(self):
        return self.unit()

    def choice(self, xs):
        return xs[self.int(len(xs))]

    def choices(self, population, weights):
        return [population[self.weighted(weights)]]


def design_sequence(board, rng, max_wait, min_team, p_wait):
    try:
        return [list(t) for t in GL.design_sequence(board, rng, max_wait, 0, min_team, p_wait)]
    except (AssertionError, RuntimeError):
        return None


def deal(seq, n, rng):
    tunnels, solution = GL.deal([tuple(s) for s in seq], n, rng)
    return [[list(s) for s in t] for t in tunnels], solution


def verify(board, tunnels, solution, capacity):
    """Mirror of LevelGenerator.verify (no slot check before a send; a jam fails)."""
    g = Game(board, [[tuple(s) for s in t] for t in tunnels], capacity)
    st = g.state
    max_used = 0
    for q in solution:
        if g.front(st, q) is None:
            return None
        g.apply_dispatch(st, q)
        if st.jammed is not None:
            return None
        max_used = max(max_used, len(st.chambers))
    return max_used if st.cleared == board.tile_count else None


def generate(board, seed):
    """Mirror of LevelGenerator.generate."""
    small = board.tile_count < 600
    n_tunnels = 2 if small else 3
    max_wait = 1 if small else 2
    min_team = 10 if board.tile_count < 2000 else 20
    for attempt in range(8):
        rng = SwiftRng((seed + attempt * 7919) & M64)
        seq = design_sequence(board, rng, max_wait, min_team, 0.18)
        if seq is None:
            continue
        tunnels, solution = deal(seq, n_tunnels, rng)
        used = verify(board, tunnels, solution, max_wait)
        if used is not None:
            return {"tunnels": tunnels, "solution": solution, "maxChambersUsed": used, "attempt": attempt}
    return None


def level_json(tunnels):
    return [[{"family": f, "quota": q} for f, q in t] for t in tunnels]


# ---------------------------------------------------------------------------------------------
# Pattern levels (PatternLevelBuilder.build)
# ---------------------------------------------------------------------------------------------

def pattern_build(seed, number):
    s = seed & M64
    for _ in range(5):
        rows = PAT.pattern_rows(s)
        layout = PAT.pattern_layout(s)
        plan = generate(Board(rows), s ^ 0x5EED)
        if plan:
            used = plan["maxChambersUsed"]
            return {"id": "pattern-%d" % s, "title": "Pattern %d" % number,
                    "subtitle": "Generated pattern · %s · seed %d" % (layout, s % 100000),
                    "art": rows, "tunnels": level_json(plan["tunnels"]), "solution": plan["solution"],
                    "chambersGentle": used + 4, "chambersClassic": used + 2, "chambersExpert": used + 1}
        s = (s + 0x9E3779B97F4A7C15) & M64
    return None


# ---------------------------------------------------------------------------------------------
# Photo levels (PhotoLevelBuilder.build) — scalar mirror of the Swift code
# ---------------------------------------------------------------------------------------------

DETAIL_TILES = {"coarse": 1600, "fine": 3600, "veryFine": 6000}


def swift_round(x):
    """Double.rounded(): half away from zero (Python's round() is half-to-even)."""
    if x < 0:
        return -swift_round(-x)
    f = math.floor(x)
    return f + 1 if x - f >= 0.5 else f


def grid_size(w, h, tiles):
    aspect = min(1.5, max(0.6, w / max(1, h)))
    gw = int(swift_round(math.sqrt(tiles * aspect)))
    gh = int(swift_round(tiles / max(1, gw)))
    return max(8, min(90, gw)), max(8, min(100, gh)), aspect


def lab(r, g, b):
    def lin(c):
        v = c / 255
        return v / 12.92 if v <= 0.04045 else math.pow((v + 0.055) / 1.055, 2.4)
    lr, lg, lb = lin(r), lin(g), lin(b)
    x = (lr * 0.4124 + lg * 0.3576 + lb * 0.1805) / 0.95047
    y = lr * 0.2126 + lg * 0.7152 + lb * 0.0722
    z = (lr * 0.0193 + lg * 0.1192 + lb * 0.9505) / 1.08883

    def f(t):
        return math.cbrt(t) if t > 0.008856 else 7.787 * t + 16.0 / 116.0
    fx, fy, fz = f(x), f(y), f(z)
    return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))


def is_near_white(l):
    c = math.sqrt(l[1] * l[1] + l[2] * l[2])
    return (l[0] > 90 and c < 15) or l[0] > 95


def downsample(img, tiles):
    """img: HxWx4 uint8. Exact integer tile sums / count (equal to Swift's Double accumulation)."""
    H, W, _ = img.shape
    gw, gh, aspect = grid_size(W, H, tiles)
    x0, y0, w, h = 0, 0, W, H
    current = w / h
    if current > aspect:
        cw = int(h * aspect)
        x0 = (w - cw) // 2
        w = cw
    elif current < aspect:
        ch = int(w / aspect)
        y0 = (h - ch) // 2
        h = ch
    out = []
    for ty in range(gh):
        ya = ty * h // gh
        yb = max(ya + 1, (ty + 1) * h // gh)
        for tx in range(gw):
            xa = tx * w // gw
            xb = max(xa + 1, (tx + 1) * w // gw)
            block = img[ya + y0:yb + y0, xa + x0:xb + x0, :3].astype(np.int64)
            n = block.shape[0] * block.shape[1]
            s = block.reshape(-1, 3).sum(0)
            out.append((int(s[0]) / n, int(s[1]) / n, int(s[2]) / n))
    return gw, gh, out


def hex_color(c):
    r = int(max(0, min(255, swift_round(c[0]))))
    g = int(max(0, min(255, swift_round(c[1]))))
    b = int(max(0, min(255, swift_round(c[2]))))
    return (r << 16) | (g << 8) | b


def colour_name(l):
    c = math.sqrt(l[1] * l[1] + l[2] * l[2])
    if c < 12:
        if l[0] > 75:
            return "Silver"
        if l[0] > 40:
            return "Grey"
        return "Charcoal"
    h = math.atan2(l[2], l[1]) * 180 / math.pi
    if h < 0:
        h += 360
    if 0 <= h < 20:
        name = "Pink"
    elif 20 <= h < 50:
        name = "Red"
    elif 50 <= h < 75:
        name = "Brown" if l[0] < 50 else "Orange"
    elif 75 <= h < 100:
        name = "Olive" if l[0] < 55 else "Gold"
    elif 100 <= h < 160:
        name = "Green"
    elif 160 <= h < 220:
        name = "Teal"
    elif 220 <= h < 290:
        name = "Blue"
    elif 290 <= h < 330:
        name = "Violet"
    else:
        name = "Magenta"
    if l[0] < 35 and name != "Brown" and name != "Olive":
        name = "Dark " + name.lower()
    elif l[0] > 80:
        name = "Pale " + name.lower()
    return name


def uniquified(names):
    seen = {}
    out = []
    for n in names:
        c = seen.get(n, 0) + 1
        seen[n] = c
        out.append(n if c == 1 else "%s %d" % (n, c))
    return out


def d2(a, b):
    x, y, z = a[0] - b[0], a[1] - b[1], a[2] - b[2]
    return x * x + y * y + z * z


def photo_build(img, detail, seed, id_, title):
    H, W, _ = img.shape
    if not (W > 1 and H > 1):
        return {"failure": {"kind": "unreadable"}}
    gw, gh, rgb = downsample(img, DETAIL_TILES[detail])
    labs = [lab(*c) for c in rgb]
    coloured = [i for i, l in enumerate(labs) if not is_near_white(l)]
    n = len(coloured)
    if n < 24:
        return {"failure": {"kind": "notEnoughColour", "colouredTiles": n}, "grid": [gw, gh]}
    pts = [(labs[i][0] * 0.5, labs[i][1], labs[i][2]) for i in coloured]
    rng = SwiftRng(seed)
    k0 = min(6, max(1, n // 40))
    cents = [pts[rng.int(n)]]
    while len(cents) < k0:
        dist = [0.0] * n
        total = 0.0
        for i in range(n):
            best = math.inf
            for c in cents:
                d = d2(pts[i], c)
                if d < best:
                    best = d
            dist[i] = best
            total += best
        if total <= 0:
            break
        r = rng.unit() * total
        pick = n - 1
        for i in range(n):
            r -= dist[i]
            if r < 0:
                pick = i
                break
        cents.append(pts[pick])
    assign = [0] * n
    for iteration in range(13):
        for i in range(n):
            best, bd = 0, math.inf
            for j, c in enumerate(cents):
                d = d2(pts[i], c)
                if d < bd:
                    bd, best = d, j
            assign[i] = best
        if iteration == 12:
            break
        sums = [[0.0, 0.0, 0.0] for _ in cents]
        counts = [0.0] * len(cents)
        for i in range(n):
            j = assign[i]
            sums[j][0] += pts[i][0]
            sums[j][1] += pts[i][1]
            sums[j][2] += pts[i][2]
            counts[j] += 1
        for j in range(len(cents)):
            if counts[j] > 0:
                cents[j] = (sums[j][0] / counts[j], sums[j][1] / counts[j], sums[j][2] / counts[j])
    counts = [0.0] * len(cents)
    for j in assign:
        counts[j] += 1
    alive = [j for j in range(len(cents)) if counts[j] > 0]
    sliver = max(8.0, 0.03 * n)
    while len(alive) > 1:
        best = None
        for i in range(len(alive)):
            for j in range(i + 1, len(alive)):
                a, b = alive[i], alive[j]
                d = math.sqrt(d2(cents[a], cents[b]))
                small = min(counts[a], counts[b]) < sliver
                if d < 16 or small:
                    if best is None or d < best[0]:
                        best = (d, a, b)
        if best is None:
            break
        _, a, b = best
        t = counts[a] + counts[b]
        cents[a] = ((cents[a][0] * counts[a] + cents[b][0] * counts[b]) / t,
                    (cents[a][1] * counts[a] + cents[b][1] * counts[b]) / t,
                    (cents[a][2] * counts[a] + cents[b][2] * counts[b]) / t)
        counts[a] = t
        counts[b] = 0
        assign = [a if v == b else v for v in assign]
        alive = [v for v in alive if v != b]
    remap = {old: new for new, old in enumerate(alive)}
    family = [remap.get(v, 0) for v in assign]
    k = len(alive)
    tone = [0] * n
    tones, names = [], []
    for f in range(k):
        members = sorted([i for i in range(n) if family[i] == f], key=lambda m: -labs[coloured[m]][0])  # stable
        mean = [0.0, 0.0, 0.0]
        for m in members:
            c = rgb[coloured[m]]
            mean[0] += c[0]
            mean[1] += c[1]
            mean[2] += c[2]
        cnt = max(1, len(members))
        mean = [mean[0] / cnt, mean[1] / cnt, mean[2] / cnt]
        fam_tones = []
        for t in range(4):
            lo = len(members) * t // 4
            hi = len(members) * (t + 1) // 4
            c = [0.0, 0.0, 0.0]
            if hi > lo:
                for m in members[lo:hi]:
                    tone[m] = t
                    p = rgb[coloured[m]]
                    c[0] += p[0]
                    c[1] += p[1]
                    c[2] += p[2]
                q = hi - lo
                c = [c[0] / q, c[1] / q, c[2] / q]
            else:
                c = mean
            fam_tones.append(hex_color(c))
        tones.append(fam_tones)
        names.append(colour_name(lab(*mean)))
    names = uniquified(names)
    grid = [-1] * (gw * gh)
    for m, idx in enumerate(coloured):
        grid[idx] = family[m] * 4 + tone[m]
    letters = "abcdefghijklmnopqrstuvwx"
    rows = ["".join("." if grid[y * gw + x] < 0 else letters[grid[y * gw + x]] for x in range(gw))
            for y in range(gh)]
    board = Board(rows)
    gen = generate(board, (seed & M64) ^ 0xC0FFEE)
    if gen is None:
        return {"failure": {"kind": "generationFailed"}, "grid": [gw, gh]}
    used = gen["maxChambersUsed"]
    return {"grid": [gw, gh], "coloured": n, "level": {
        "id": id_, "title": title, "subtitle": "Your photo · %d colour%s" % (k, "" if k == 1 else "s"),
        "art": rows, "palette": {"names": names, "tones": tones}, "tunnels": level_json(gen["tunnels"]),
        "solution": gen["solution"], "chambersGentle": used + 4, "chambersClassic": used + 2,
        "chambersExpert": used + 1}}


def photo_py_reference(img, detail, seed):
    """What the unmodified Tools/photo.py makes of the same pixels (reported, not asserted)."""
    rgb = img[:, :, :3]
    small = PH.downsample(rgb, PH.DETAIL_TILES[{"veryFine": "very_fine"}.get(detail, detail)])
    out = {"grid": [small.shape[1], small.shape[0]]}
    labs = PH.srgb_to_lab(small)
    out["coloured"] = int((~PH.is_near_white(labs)).sum())
    if detail == "veryFine" or out["coloured"] > 4000:
        return out      # the planning step of photo.py is slow on the largest grids; grid + mask only
    r = PH.build_photo_level(rgb, {"veryFine": "very_fine"}.get(detail, detail), seed)
    if "rows" in r:
        out.update(rows=r["rows"], palette=r["palette"], families=r["families"])
    else:
        out["error"] = r.get("error")
    return out


# ---------------------------------------------------------------------------------------------
# DifficultyProbe.measure mirror
# ---------------------------------------------------------------------------------------------

def probe(level, trials=10):
    board = Board(level["art"])
    tunnels = [[(s["family"], s["quota"]) for s in t] for t in level["tunnels"]]
    careless, greedy = [], []
    for cap in (level["chambersGentle"], level["chambersClassic"], level["chambersExpert"]):
        rng = SwiftRng(5)
        wins = 0
        for _ in range(trials):
            g = Game(board, tunnels, cap)
            steps = 0
            while g.state.cleared != board.tile_count and steps < 2000:
                fronts = [q for q in range(len(tunnels)) if g.can_dispatch(q)]
                if not fronts:
                    break
                g.dispatch(fronts[rng.int(len(fronts))])
                steps += 1
            if g.state.cleared == board.tile_count:
                wins += 1
        careless.append(wins / max(1, trials))
        start = Game(board, tunnels, cap)
        won, _ = engine_rollout(start, start.state)
        greedy.append(bool(won))
    return {"careless": careless, "greedy": greedy}


# ---------------------------------------------------------------------------------------------
# Input images
# ---------------------------------------------------------------------------------------------

def img_flower():
    """SelfTest.syntheticFlower: 300x400, white background, pink flower, yellow centre, green stem."""
    w, h = 300, 400
    px = np.full((h, w, 4), 250, np.uint8)
    for y in range(h):
        for x in range(w):
            dx, dy = float(x - 150), float(y - 150)
            r = math.sqrt(dx * dx + dy * dy)
            a = math.atan2(dy, dx)
            petal = 70 + 22 * math.cos(5 * a)
            ex, ey = (x - 110) / 40, (y - 290) / 15
            if r < 32:
                px[y, x] = (245, 196, 40, 255)
            elif r < petal:
                px[y, x] = (220, 50, 100, 255)
            elif abs(x - 150) < 7 and 200 < y < 380:
                px[y, x] = (60, 140, 60, 255)
            elif ex * ex + ey * ey < 1:
                px[y, x] = (70, 160, 70, 255)
            else:
                px[y, x, 3] = 255
    return px


def img_blocks():
    """160x120 poster: colour blocks, a gradient band and a white margin."""
    w, h = 160, 120
    px = np.full((h, w, 4), 255, np.uint8)
    blocks = [((10, 10, 60, 50), (30, 80, 200)), ((60, 10, 110, 50), (230, 190, 30)),
              ((110, 10, 150, 50), (200, 40, 40)), ((10, 50, 80, 90), (40, 150, 60)),
              ((80, 50, 150, 90), (120, 70, 40))]
    for (x0, y0, x1, y1), c in blocks:
        px[y0:y1, x0:x1, :3] = c
    for x in range(10, 150):
        t = (x - 10) / 139
        px[92:110, x, :3] = (int(200 * (1 - t) + 20 * t), int(60 + 120 * t), int(150 + 80 * t))
    return px


def img_white():
    return np.full((48, 64, 4), 252, np.uint8)


def img_speck():
    """200x150 white with one small red dot: a few coloured tiles, too few for a puzzle."""
    w, h = 200, 150
    px = np.full((h, w, 4), 255, np.uint8)
    yy, xx = np.mgrid[0:h, 0:w]
    m = (xx - 90) ** 2 + (yy - 70) ** 2 < 10 ** 2
    px[m, :3] = (210, 30, 40)
    return px


def _blur(a, k):
    """Separable box blur (k passes) of an HxWxC float image."""
    for _ in range(k):
        a = (np.roll(a, 1, 0) + a + np.roll(a, -1, 0)) / 3
        a = (np.roll(a, 1, 1) + a + np.roll(a, -1, 1)) / 3
    return a


def img_landscape():
    """720x540 photo-like landscape: sky gradient, hazy sun, mountains, fields, a red barn, trees,
    a lake with reflections, film grain."""
    w, h = 720, 540
    rng = np.random.default_rng(20261018)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    img = np.zeros((h, w, 3))
    t = yy / h
    img[..., 0] = 90 + 130 * t
    img[..., 1] = 150 + 80 * t
    img[..., 2] = 235 - 10 * t
    sun = np.exp(-(((xx - 560) ** 2 + (yy - 110) ** 2) / (2 * 45.0 ** 2)))
    img += sun[..., None] * np.array([150, 120, 40])
    ridge = 250 + 40 * np.sin(xx / 70) + 25 * np.sin(xx / 23 + 1.3) + 10 * np.sin(xx / 9)
    mount = yy > ridge
    img[mount] = np.array([105, 115, 140]) + (yy[mount] - ridge[mount])[..., None] * np.array([-0.2, 0.1, -0.3])
    hill = 330 + 30 * np.sin(xx / 110 + 0.5) + 12 * np.sin(xx / 37)
    field = yy > hill
    tex = rng.normal(0, 1, (h, w))
    tex = _blur(tex[..., None], 2)[..., 0] * 25
    img[field] = np.array([70, 140, 50]) + np.stack([tex[field], tex[field] * 1.4, tex[field] * 0.5], -1)
    stripes = field & (np.sin(yy / 6 + xx / 40) > 0.6)
    img[stripes] = img[stripes] * np.array([1.25, 1.15, 0.7])
    barn = (xx > 170) & (xx < 260) & (yy > 300) & (yy < 370)
    roof = (yy > 270) & (yy <= 300) & (np.abs(xx - 215) < (yy - 270) * 1.6)
    img[barn] = np.array([170, 35, 30])
    img[roof] = np.array([60, 50, 50])
    img[(xx > 200) & (xx < 230) & (yy > 335) & (yy < 370)] = np.array([245, 240, 230])
    for _ in range(14):
        cx, cy, r = rng.uniform(0, w), rng.uniform(320, 420), rng.uniform(14, 34)
        m = (xx - cx) ** 2 + ((yy - cy) * 1.3) ** 2 < r * r
        shade = 1 - 0.4 * np.clip((xx - cx) / r, -1, 1)
        img[m] = (np.array([25, 75, 30])[None] * shade[m][..., None])
    lake = (yy > 430) & ((xx - 470) ** 2 / 260 ** 2 + (yy - 500) ** 2 / 70 ** 2 < 1)
    my = np.clip((2 * 430 - yy).astype(int), 0, h - 1)
    refl = img[my, xx.astype(int)] * 0.6 + np.array([20, 50, 90])
    img[lake] = refl[lake]
    img = _blur(img, 1)
    img += rng.normal(0, 5, img.shape)
    out = np.empty((h, w, 4), np.uint8)
    out[..., :3] = np.clip(np.rint(img), 0, 255).astype(np.uint8)
    out[..., 3] = 255
    return out


def img_bokeh():
    """720x720 photo-like close-up: overlapping soft colour discs on a dark green ground, grain.
    Square, colourful and with no white: the largest grid the Swift code allows (77 x 78 at Very fine)."""
    w = h = 720
    rng = np.random.default_rng(7)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    img = np.zeros((h, w, 3)) + np.array([30, 70, 40])
    img += (yy / h)[..., None] * np.array([20, 30, -10])
    cols = np.array([[230, 60, 90], [250, 190, 40], [90, 60, 200], [240, 120, 30], [60, 170, 210], [180, 40, 160]])
    for i in range(60):
        cx, cy, r = rng.uniform(0, w), rng.uniform(0, h), rng.uniform(20, 90)
        d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / r
        a = np.clip(1.2 - d, 0, 1)[..., None] * 0.85
        img = img * (1 - a) + cols[i % len(cols)] * a
    img += rng.normal(0, 6, img.shape)
    out = np.empty((h, w, 4), np.uint8)
    out[..., :3] = np.clip(np.rint(img), 0, 255).astype(np.uint8)
    out[..., 3] = 255
    return out


IMAGES = {"flower": img_flower, "blocks": img_blocks, "white": img_white, "speck": img_speck,
          "landscape": img_landscape, "bokeh": img_bokeh}

PHOTO_CASES = [
    # name, image, detail, seed (as in the app: seeds are UInt64)
    ("flower-fine-7", "flower", "fine", 7),                       # SelfTest section 3
    ("flower-coarse-big", "flower", "coarse", 0xDEADBEEFCAFEBABE),
    ("blocks-coarse-3", "blocks", "coarse", 3),
    ("blocks-veryfine-11", "blocks", "veryFine", 11),
    ("white-fine-1", "white", "fine", 1),                         # SelfTest: refused, 0 tiles
    ("speck-coarse-5", "speck", "coarse", 5),
    ("landscape-fine", "landscape", "fine", ((1555200 * 2654435761) & M64) ^ 1760793600),
    ("landscape-veryfine-42", "landscape", "veryFine", 42),
    ("bokeh-veryfine-99", "bokeh", "veryFine", 99),
    ("bokeh-coarse-2", "bokeh", "coarse", 2),
]

PROBE_PHOTOS = {"flower-fine-7", "blocks-coarse-3", "landscape-fine", "bokeh-coarse-2"}
PROBE_PATTERNS = {1, 4, 12345}


def pattern_seeds():
    seeds = [1, 2, 3, 4, 6, 12345, 4294967295, (1760793600123 & 0xFFFFFFFF), 0xFFFFFFFFFFFFFFFF]
    per = {}
    for s in range(1, 120):
        lay = PAT.pattern_layout(s)
        if per.get(lay, 0) < 3 and s not in seeds:
            per[lay] = per.get(lay, 0) + 1
            seeds.append(s)
    return seeds


GEN_BOARDS = ["firstDig", "koiPond", "labyrinth", "nightMarket"]
GEN_CASES = [  # seed, maxWait, minTeam, pWait, tunnels
    (1, 1, 10, 0.18, 2), (0xC0FFEE, 2, 20, 0.18, 3), ((1 << 63) + 5, 2, 10, 0.5, 3), (99, 3, 20, 0.9, 4),
]


# ---------------------------------------------------------------------------------------------

def job_pattern(seed):
    t0 = time.time()
    rows = PAT.pattern_rows(seed)
    lv = pattern_build(seed, 7)
    out = {"seed": str(seed), "layout": PAT.pattern_layout(seed), "rows": rows, "level": lv}
    if seed in PROBE_PATTERNS and lv:
        out["probe"] = probe(lv)
    out["seconds"] = round(time.time() - t0, 1)
    return out


def job_photo(case):
    name, image, detail, seed = case
    t0 = time.time()
    img = load_image(image)
    r = photo_build(img, detail, seed, "photo-" + name, "Photo mosaic 3")
    out = {"name": name, "image": image, "detail": detail, "seed": str(seed), **r}
    out["photo_py"] = photo_py_reference(img, detail, seed)
    if name in PROBE_PHOTOS and "level" in r:
        out["probe"] = probe(r["level"])
    out["seconds"] = round(time.time() - t0, 1)
    return out


def job_gen(name):
    levels = json.loads((WEB / "data" / "levels.json").read_text())["levels"]
    art = levels[name]["art"]
    board = Board(art)
    cases = []
    for seed, max_wait, min_team, p_wait, n in GEN_CASES:
        rng = SwiftRng(seed)
        seq = design_sequence(board, rng, max_wait, min_team, p_wait)
        c = {"seed": str(seed), "maxWait": max_wait, "minTeam": min_team, "pWait": p_wait, "tunnelCount": n,
             "seq": seq}
        if seq is not None:
            tunnels, solution = deal(seq, n, rng)
            c.update(tunnels=tunnels, solution=solution, nextRandom=str(rng.next()),
                     verify=verify(board, tunnels, solution, max_wait))
        cases.append(c)
    plans = []
    for seed in (5, 0xFFFFFFFFFFFFFFF0):
        plans.append({"seed": str(seed), "plan": generate(board, seed)})
    return {"name": name, "cases": cases, "generate": plans}


OUT_DIR = None


def load_image(name):
    raw = gzip.decompress((OUT_DIR / ("photo_%s.rgba.gz" % name)).read_bytes())
    meta = json.loads((OUT_DIR / "photos.json").read_text())[name]
    return np.frombuffer(raw, np.uint8).reshape(meta["height"], meta["width"], 4)


def main():
    global OUT_DIR
    OUT_DIR = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else WEB / "test" / "fixtures"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    meta = {}
    for name, fn in IMAGES.items():
        px = fn()
        (OUT_DIR / ("photo_%s.rgba.gz" % name)).write_bytes(gzip.compress(px.tobytes(), 9, mtime=0))
        meta[name] = {"width": int(px.shape[1]), "height": int(px.shape[0])}
    (OUT_DIR / "photos.json").write_text(json.dumps(meta, indent=1))
    print("images %.1fs" % (time.time() - t0), flush=True)
    with Pool(2) as pool:
        pats = pool.map_async(job_pattern, pattern_seeds(), chunksize=1)
        photos = pool.map_async(job_photo, PHOTO_CASES, chunksize=1)
        gens = pool.map_async(job_gen, GEN_BOARDS, chunksize=1)
        pats, photos, gens = pats.get(), photos.get(), gens.get()
    for p in pats:
        print("pattern %-22s %-12s %5.1fs" % (p["seed"], p["layout"], p["seconds"]))
    for p in photos:
        print("photo %-22s %5.1fs %s" % (p["name"], p["seconds"], p.get("failure", "")))
    for p in pats + photos:
        p.pop("seconds")          # keep builders.json reproducible byte for byte
    out = {"palette": json.loads((WEB / "data" / "levels.json").read_text())["palette"],
           "patterns": pats, "photos": photos, "generator": gens}
    (OUT_DIR / "builders.json").write_text(json.dumps(out, separators=(",", ":")))
    print("done %.1fs -> %s" % (time.time() - t0, OUT_DIR / "builders.json"))


if __name__ == "__main__":
    main()
