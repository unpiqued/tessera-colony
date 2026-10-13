"""Pattern mosaics: a fresh, solvable level from a seed (reference model of PatternLevelBuilder.swift).

Each tile's colour family comes straight from a formula (no supersampling), so the Swift port can
compute exactly the same picture from the same seed. Every pattern has the same checkered frame;
inside it the seed picks one of five different layouts (seed 1 is always the rosette):
  rosette     : n petals (|cos| lobes), a bead ring, a scalloped band, corner quarter-rosettes, a lattice
  starburst   : a faceted n-pointed star with an outline over alternating rays
  fish scales : rows of overlapping scales, each with concentric bands (the seigaiha wave pattern)
  kaleidoscope: random shapes in one 30-degree wedge, mirrored six ways inside a hexagon
  ribbons     : two striped ribbons crossing at a knot, over a field of polka dots
Tones 0..3 come from shading values with a 4x4 ordered dither.
"""
import math

from engine import Board
from generate_levels import deal, replay
from photo import SplitMix64

BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]
W, H = 46, 52


def pick(rng, n):
    return int(rng.next() % n) if n > 1 else 0


def shuffle(rng, xs):
    xs = list(xs)
    for i in range(len(xs) - 1, 0, -1):
        j = pick(rng, i + 1)
        xs[i], xs[j] = xs[j], xs[i]
    return xs


LAYOUTS = ["Rosette", "Starburst", "Fish scales", "Kaleidoscope", "Ribbons"]
LAYOUT_OFFSET = 4          # makes seed 1 the rosette (the golden picture the app's self-test compares)


def fmod(a, n):
    """Floor modulo for floats (Swift mirrors it the same way)."""
    return a - n * math.floor(a / n)


def pattern_layout(seed):
    return LAYOUTS[_params(seed)[-1]]


def _params(seed):
    rng = SplitMix64(seed)
    fams = shuffle(rng, range(6))
    n_petals = 5 + pick(rng, 8)
    petal_k = [0.8, 1.4, 2.2][pick(rng, 3)]
    r_petal = 16.0 + pick(rng, 4)
    r_inner = r_petal * (0.5 + 0.08 * pick(rng, 3))
    r_ring = 5.5 + pick(rng, 3)
    r_centre = 2.6 + pick(rng, 3) * 0.6
    n_beads = 14 + 2 * pick(rng, 6)
    lattice = pick(rng, 3)
    twist = (pick(rng, 5) - 2) * 0.06
    layout = (pick(rng, 5) + LAYOUT_OFFSET) % 5
    return rng, fams, n_petals, petal_k, r_petal, r_inner, r_ring, r_centre, n_beads, lattice, twist, layout


def pattern_rows(seed):
    rng = SplitMix64(seed)
    fams = shuffle(rng, range(6))          # frame, field, petals, ring, centre, accent
    frame, field, petals, ring, centre, accent = fams
    n_petals = 5 + pick(rng, 8)            # 5..12
    petal_k = [0.8, 1.4, 2.2][pick(rng, 3)]
    r_petal = 16.0 + pick(rng, 4)          # 16 .. 19
    r_inner = r_petal * (0.5 + 0.08 * pick(rng, 3))
    r_ring = 5.5 + pick(rng, 3)            # 5.5 .. 7.5
    r_centre = 2.6 + pick(rng, 3) * 0.6
    n_beads = 14 + 2 * pick(rng, 6)
    n_scallops = 2 * n_petals
    lattice = pick(rng, 3)                 # 0 diamonds, 1 diagonal lines, 2 squares
    twist = (pick(rng, 5) - 2) * 0.06
    layout = (pick(rng, 5) + LAYOUT_OFFSET) % 5
    # parameters of the other layouts (drawn after the rosette's, so seed 1 is unchanged)
    n_pts = 5 + pick(rng, 6)
    r_out = 17.0 + pick(rng, 4)
    r_in = r_out * (0.42 + 0.05 * pick(rng, 3))
    n_rays = 2 * (8 + pick(rng, 5))
    scale_r = 9.0 + pick(rng, 3)
    n_blobs = 8 + pick(rng, 5)
    blobs = []
    for _ in range(n_blobs):
        rr = 2.0 + pick(rng, 19)
        ang = pick(rng, 7) * (math.pi / 6.0) / 6.0
        br = 1.5 + 0.5 * pick(rng, 6)
        bf = pick(rng, 4)
        blobs.append((rr * math.cos(ang), rr * math.sin(ang), br, bf))
    dot_sp = 5 + pick(rng, 2)
    dot_r = 1.4 + 0.4 * pick(rng, 2)
    ribbon_w = 3.0 + pick(rng, 3)
    # more variety for fish scales and ribbons (drawn last, so earlier draws are unchanged)
    fs_bands = 3 + pick(rng, 2)
    fs_phase = pick(rng, 8)
    scale_r += pick(rng, 4) - 1                # 8 .. 13
    moon = (9 + pick(rng, 25), 9 + pick(rng, 14), 5 + pick(rng, 4))
    rb_a1 = pick(rng, 8)                       # first ribbon's angle, in eighths of a half-turn
    rb_a2 = pick(rng, 4)                       # the second crosses it 2..5 eighths further round
    rb_kx, rb_ky = pick(rng, 13) - 6, pick(rng, 13) - 6
    rb_period = 2 + pick(rng, 3)
    rb_dots = pick(rng, 3)
    band_fams = [petals, ring, accent, centre]
    cx, cy = (W - 1) / 2.0, (H - 1) / 2.0
    rows = []
    letters = "abcdefghijklmnopqrstuvwx"
    for y in range(H):
        row = []
        for x in range(W):
            dx, dy = x - cx, y - cy
            r = math.hypot(dx, dy)
            a = math.atan2(dy, dx) + twist * r / 10.0
            d_edge = min(x, y, W - 1 - x, H - 1 - y)
            if d_edge == 0:
                fam, shade = frame, 0.85
            elif d_edge == 1:
                fam, shade = (frame, 0.3) if (x + y) % 2 == 0 else (accent, 0.1)
            elif d_edge == 2:
                fam, shade = frame, 0.6
            elif layout == 1:
                fam, shade = starburst(dx, dy, r, a, field, accent, petals, ring, centre, n_pts, r_out, r_in, n_rays)
            elif layout == 2:
                fam, shade = fish_scales(x, y, field, band_fams, scale_r, fs_bands, fs_phase, moon)
            elif layout == 3:
                fam, shade = kaleidoscope(dx, dy, r, field, ring, band_fams, blobs)
            elif layout == 4:
                fam, shade = ribbons(x, y, dx, dy, field, accent, centre, petals, ring, dot_sp, dot_r, ribbon_w,
                                     rb_a1, rb_a2, rb_kx, rb_ky, rb_period, rb_dots)
            else:
                fam = field
                if lattice == 0:
                    on = (abs(dx) + abs(dy)) % 6 < 1 or (abs(dx - dy)) % 6 < 1
                elif lattice == 1:
                    on = (x + y) % 5 == 0 or (x - y) % 5 == 0
                else:
                    on = x % 5 == 0 or y % 5 == 0
                shade = (0.75 if on else 0.2) + 0.15 * min(1.0, r / 30.0)
                # corner quarter-rosettes
                for (qx, qy) in ((3, 3), (W - 4, 3), (3, H - 4), (W - 4, H - 4)):
                    qr = math.hypot(x - qx, y - qy)
                    if qr < 6.5:
                        fam, shade = (ring, 0.25 + 0.1 * qr) if qr < 4.5 else (accent, 0.4)
                # scallop ring around the rosette
                sr = r_petal + 2.2
                seg = (a + math.pi) / (2 * math.pi) * n_scallops
                seg = seg - math.floor(seg)
                bump = 1.3 * math.sin(math.pi * seg)
                if sr - 0.6 < r < sr + bump:
                    fam, shade = accent, 0.2 + 0.5 * (r - sr + 0.6) / 2.0
                # outer petals
                lobe = abs(math.cos(n_petals * a / 2.0)) ** petal_k
                pr = r_petal * (0.42 + 0.58 * lobe)
                if r < pr:
                    fam = petals
                    shade = 0.15 + 0.75 * (r / pr)
                    if abs(math.sin(n_petals * a)) < 0.1 and r > r_ring + 1:
                        shade = 1.0          # petal crease
                # inner petals, rotated half a step
                lobe2 = abs(math.cos(n_petals * (a + math.pi / n_petals) / 2.0)) ** petal_k
                pr2 = r_inner * (0.5 + 0.5 * lobe2)
                if r < pr2:
                    fam, shade = accent, 0.1 + 0.6 * r / pr2
                if abs(r - r_ring) < 1.2:
                    fam = ring
                    bead = int(((a + math.pi) / (2 * math.pi)) * n_beads) % 2
                    shade = 0.15 if bead else 0.75
                if r < r_centre:
                    fam = centre if centre not in (ring,) else petals
                    shade = 0.1 + 0.8 * r / r_centre
            shade = min(1.0, max(0.0, shade))
            dth = (BAYER[y % 4][x % 4] / 16.0 - 0.47) * 0.85
            tone = min(3, max(0, int(math.floor(shade * 3.0 + 0.5 + dth))))
            row.append(letters[fam * 4 + tone])
        rows.append("".join(row))
    return rows


def starburst(dx, dy, r, a, field, accent, petals, ring, centre, n_pts, r_out, r_in, n_rays):
    sector = int(math.floor((a + math.pi) / (2 * math.pi) * n_rays)) % 2
    fam, shade = (accent, 0.3) if sector == 1 else (field, 0.2)
    shade += 0.4 * min(1.0, r / 32.0)
    t = fmod((a + math.pi) / (2 * math.pi) * n_pts, 1.0)
    pt = abs(2 * t - 1)
    radius = r_in + (r_out - r_in) * pt ** 1.5
    if radius <= r < radius + 1.4:
        fam, shade = ring, 0.8
    if r < radius:
        fam = petals
        shade = 0.15 + 0.55 * r / radius + (0.2 if t < 0.5 else 0.0)
    if abs(r - r_in * 0.55) < 0.9:
        fam, shade = ring, 0.3
    if r < r_in * 0.4:
        fam, shade = centre, 0.1 + 0.7 * r / (r_in * 0.4)
    return fam, shade


def fish_scales(x, y, field, band_fams, R, bands, phase, moon):
    mx, my, mr = moon
    dm = math.hypot(x - mx, y - my)
    if dm < mr:
        return field, 0.1 + 0.5 * dm / mr
    if dm < mr + 1.2:
        return band_fams[0], 0.9
    px = x + phase * R / 4.0
    step_y = R * 0.5
    rows_n = int(H / step_y) + 3
    for j in range(rows_n, -2, -1):
        sy = j * step_y
        if y > sy + 0.01:
            continue
        off = R if j % 2 else 0.0
        i0 = int(math.floor((px - off) / (2 * R)))
        for i in (i0, i0 + 1):
            sx = i * 2 * R + off
            d = math.hypot(px - sx, y - sy)
            if d < R:
                bw = R / bands
                band = int(d / bw)
                fam = band_fams[(j % 2) * 2 + band % 2]
                return fam, 0.15 + 0.6 * fmod(d, bw) / bw
    return field, 0.3


def kaleidoscope(dx, dy, r, field, ring, band_fams, blobs):
    # hexagon of radius 21 (distance to the nearest side)
    hexd = max(abs(dy), abs(dy) * 0.5 + abs(dx) * math.sqrt(3) / 2)
    if hexd > 21.5:
        on = int(math.floor(r / 3.0)) % 2 == 0
        return field, (0.25 if on else 0.55)
    if hexd > 20.0:
        return ring, 0.7
    a = math.atan2(dy, dx)
    af = fmod(a, math.pi / 3)
    if af > math.pi / 6:
        af = math.pi / 3 - af
    px, py = r * math.cos(af), r * math.sin(af)
    fam, shade = field, 0.1 + 0.5 * r / 22.0
    for (bx, by, br, bf) in blobs:
        d = math.hypot(px - bx, py - by)
        if d < br:
            fam, shade = band_fams[bf], 0.15 + 0.6 * d / br
    return fam, shade


def ribbons(x, y, dx, dy, field, accent, centre, petals, ring, sp, dot_r, w, a1i, a2i, kx, ky, period, dots):
    gx, gy = x % sp, y % sp
    half = (sp - 1) / 2.0
    ex, ey = abs(gx - half), abs(gy - half)
    if dots == 0:
        in_dot, dd = math.hypot(ex, ey) < dot_r, math.hypot(ex, ey)
    elif dots == 1:
        in_dot, dd = ex + ey < dot_r * 1.3, (ex + ey) / 1.3
    else:
        in_dot, dd = min(ex, ey) < 0.6 and max(ex, ey) < dot_r + 0.4, max(ex, ey)
    qx, qy = dx - kx, dy - ky
    r = math.hypot(qx, qy)
    fam, shade = field, 0.2 + 0.2 * min(1.0, r / 30.0)
    if in_dot:
        fam = accent if ((x // sp) + (y // sp)) % 2 == 0 else centre
        shade = 0.15 + 0.5 * dd / max(dot_r, 0.1)
    a1 = a1i * math.pi / 8.0
    a2 = a1 + (2 + a2i) * math.pi / 8.0
    along1, across1 = qx * math.cos(a1) + qy * math.sin(a1), -qx * math.sin(a1) + qy * math.cos(a1)
    along2, across2 = qx * math.cos(a2) + qy * math.sin(a2), -qx * math.sin(a2) + qy * math.cos(a2)
    if abs(across1) < w:
        fam = petals
        shade = 0.2 if int(math.floor(along1 / period)) % 2 == 0 else 0.6
        if abs(across1) > w - 0.9:
            shade = 0.9
    if abs(across2) < w:
        fam = ring
        shade = 0.2 if int(math.floor(along2 / period)) % 2 == 0 else 0.6
        if abs(across2) > w - 0.9:
            shade = 0.9
    if r < w * 1.5:
        fam, shade = centre, 0.1 + 0.6 * r / (w * 1.5)
    if abs(r - w * 1.5) < 0.8:
        fam, shade = accent, 0.8
    return fam, shade


def build_pattern_level(seed):
    """Mirror of PatternLevelBuilder.build: rows + LevelGenerator plan (Python designer)."""
    import random
    from generate_levels import design_sequence
    rows = pattern_rows(seed)
    board = Board(rows)
    for attempt in range(8):
        prng = random.Random(seed * 7919 + attempt)
        try:
            seq = design_sequence(board, prng, 2, 3, 20, 0.18)
        except (AssertionError, RuntimeError):
            continue
        tunnels, solution = deal(seq, 3, prng)
        g, per_move, max_ch = replay(board, tunnels, solution, capacity=3)
        return {"rows": rows, "tunnels": tunnels, "solution": solution,
                "chambers": {"expert": max_ch + 1, "classic": max_ch + 2, "gentle": max_ch + 4},
                "tiles": board.tile_count}
    return None


if __name__ == "__main__":
    import sys
    from render import render_board
    from PIL import Image
    out = sys.argv[1]
    ims = []
    picked, seen = [], {}
    for seed in range(1, 200):                 # one of each layout, then a second kaleidoscope
        lay = pattern_layout(seed)
        if seen.get(lay, 0) < (2 if lay == "Kaleidoscope" else 1):
            seen[lay] = seen.get(lay, 0) + 1
            picked.append(seed)
        if len(picked) == 6:
            break
    for seed in picked:
        ims.append(render_board(pattern_rows(seed), 7))
    Wt = sum(i.width for i in ims[:3]); Ht = ims[0].height * 2
    c = Image.new("RGB", (Wt, Ht), (30, 24, 20))
    for k, im in enumerate(ims):
        c.paste(im, ((k % 3) * im.width, (k // 3) * im.height))
    c.save(out)
    print("ok")
