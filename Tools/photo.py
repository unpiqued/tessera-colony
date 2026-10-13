"""Photo-to-puzzle pipeline (reference model of PhotoLevelBuilder.swift).

photo -> centre crop -> tile grid -> drop near-white tiles (they become open ground) ->
k-means colour families in Lab -> merge look-alike families -> 4 glaze tones per family by
lightness -> designer simulation builds teams + tunnels -> replay proves it is solvable.
"""
import math
import random

import numpy as np

from engine import Board, Game
from generate_levels import design_sequence, deal, replay

DETAIL_TILES = {"coarse": 1600, "fine": 3600, "very_fine": 6000}
M64 = 0xFFFFFFFFFFFFFFFF


class SplitMix64:
    """Same generator as SplitMix64 in PhotoLevelBuilder.swift."""
    def __init__(self, seed):
        self.s = seed & M64

    def next(self):
        self.s = (self.s + 0x9E3779B97F4A7C15) & M64
        z = self.s
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & M64
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & M64
        return z ^ (z >> 31)

    def unit(self):
        return (self.next() >> 11) / float(1 << 53)


def srgb_to_lab(rgb):
    c = rgb / 255.0
    lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    x = (lin[..., 0] * 0.4124 + lin[..., 1] * 0.3576 + lin[..., 2] * 0.1805) / 0.95047
    y = lin[..., 0] * 0.2126 + lin[..., 1] * 0.7152 + lin[..., 2] * 0.0722
    z = (lin[..., 0] * 0.0193 + lin[..., 1] * 0.1192 + lin[..., 2] * 0.9505) / 1.08883
    f = lambda t: np.where(t > 0.008856, np.cbrt(t), 7.787 * t + 16 / 116)
    fx, fy, fz = f(x), f(y), f(z)
    return np.stack([116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)], -1)


def is_near_white(lab):
    L, a, b = lab[..., 0], lab[..., 1], lab[..., 2]
    C = np.hypot(a, b)
    return ((L > 90) & (C < 15)) | (L > 95)


def grid_size(w, h, tiles):
    aspect = min(1.5, max(0.6, w / h))
    gw = int(round(math.sqrt(tiles * aspect)))
    gh = int(round(tiles / gw))
    return max(8, min(90, gw)), max(8, min(100, gh)), aspect


def downsample(img, tiles):
    """img: HxWx3 uint8. Centre-crop to the clamped aspect, box-average into tiles."""
    H, W, _ = img.shape
    gw, gh, aspect = grid_size(W, H, tiles)
    # centre crop to aspect
    if W / H > aspect:
        cw = int(H * aspect); x0 = (W - cw) // 2; img = img[:, x0:x0 + cw]
    elif W / H < aspect:
        ch = int(W / aspect); y0 = (H - ch) // 2; img = img[y0:y0 + ch, :]
    H, W, _ = img.shape
    out = np.zeros((gh, gw, 3), np.float64)
    for ty in range(gh):
        y0, y1 = ty * H // gh, max(ty * H // gh + 1, (ty + 1) * H // gh)
        for tx in range(gw):
            x0, x1 = tx * W // gw, max(tx * W // gw + 1, (tx + 1) * W // gw)
            out[ty, tx] = img[y0:y1, x0:x1].reshape(-1, 3).mean(0)
    return out


def feat(lab):
    return np.stack([lab[..., 0] * 0.5, lab[..., 1], lab[..., 2]], -1)


def kmeans(points, k, rng):
    n = len(points)
    cents = [points[int(rng.unit() * n) % n]]
    while len(cents) < k:
        d2 = np.min(((points[:, None, :] - np.array(cents)[None]) ** 2).sum(-1), 1)
        tot = d2.sum()
        if tot <= 0:
            break
        r = rng.unit() * tot
        acc = np.cumsum(d2)
        cents.append(points[int(np.searchsorted(acc, r)) if r < acc[-1] else n - 1])
    cents = np.array(cents)
    for _ in range(12):
        lab = np.argmin(((points[:, None, :] - cents[None]) ** 2).sum(-1), 1)
        for j in range(len(cents)):
            m = lab == j
            if m.any():
                cents[j] = points[m].mean(0)
    lab = np.argmin(((points[:, None, :] - cents[None]) ** 2).sum(-1), 1)
    return cents, lab


def build_photo_level(img, detail="fine", seed=1):
    rgb = downsample(img, DETAIL_TILES[detail])
    gh, gw, _ = rgb.shape
    lab = srgb_to_lab(rgb)
    white = is_near_white(lab)
    colored = np.argwhere(~white)
    n = len(colored)
    if n < 24:
        return {"error": "not_enough_colour", "coloured_tiles": int(n), "grid": [gw, gh]}
    pts = feat(lab[~white])
    rng = SplitMix64(seed)
    k0 = min(6, max(1, n // 40))
    cents, assign = kmeans(pts, k0, rng)
    counts = np.bincount(assign, minlength=len(cents)).astype(float)
    # merge look-alikes and tiny clusters
    alive = [j for j in range(len(cents)) if counts[j] > 0]
    changed = True
    while changed and len(alive) > 1:
        changed = False
        best = None
        for i in range(len(alive)):
            for j in range(i + 1, len(alive)):
                a, b = alive[i], alive[j]
                d = float(np.sqrt(((cents[a] - cents[b]) ** 2).sum()))
                small = min(counts[a], counts[b]) < max(8, 0.03 * n)
                if (d < 16 or small) and (best is None or d < best[0]):
                    best = (d, a, b)
        if best is not None:
            _, a, b = best
            cents[a] = (cents[a] * counts[a] + cents[b] * counts[b]) / (counts[a] + counts[b])
            counts[a] += counts[b]; counts[b] = 0
            assign[assign == b] = a
            alive.remove(b)
            changed = True
    remap = {old: new for new, old in enumerate(alive)}
    fam = np.array([remap[a] for a in assign])
    K = len(alive)
    # tones by lightness quartile inside each family
    tone = np.zeros(n, int)
    palette = []
    Ls = lab[~white][:, 0]
    cols = rgb[~white]
    for f in range(K):
        idx = np.nonzero(fam == f)[0]
        order = idx[np.argsort(-Ls[idx], kind="stable")]
        tones = []
        for t in range(4):
            part = order[len(order) * t // 4:len(order) * (t + 1) // 4]
            tone[part] = t
            tones.append(cols[part].mean(0) if len(part) else None)
        mean = cols[idx].mean(0)
        tones = [tc if tc is not None else mean for tc in tones]
        palette.append(["#%02X%02X%02X" % tuple(int(round(v)) for v in tc) for tc in tones])
    rows = []
    grid = np.full((gh, gw), -1)
    for (y, x), f, t in zip(colored, fam, tone):
        grid[y, x] = f * 4 + t
    alphabet = "abcdefghijklmnopqrstuvwx"
    for y in range(gh):
        rows.append("".join("." if grid[y, x] < 0 else alphabet[grid[y, x]] for x in range(gw)))
    # puzzle
    board = Board(rows)
    small = board.tile_count < 600
    n_tunnels = 2 if small else 3
    max_wait = 1 if small else 2
    min_team = 10 if board.tile_count < 2000 else 20
    last_err = None
    for attempt in range(6):
        prng = random.Random(seed * 7919 + attempt)
        try:
            seq = design_sequence(board, prng, max_wait, n_tunnels, min_team, 0.18)
        except (AssertionError, RuntimeError) as e:
            last_err = str(e)
            continue
        tunnels, solution = deal(seq, n_tunnels, prng)
        g, per_move, max_ch = replay(board, tunnels, solution, capacity=max_wait + 1)
        return {"rows": rows, "palette": palette, "tunnels": tunnels, "solution": solution,
                "chambers": {"expert": max_ch + 1, "classic": max_ch + 2, "gentle": max_ch + 4},
                "grid": [gw, gh], "tiles": board.tile_count, "empty": int(white.sum()), "families": K}
    return {"error": "generation_failed", "detail": last_err}
