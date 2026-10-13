"""Python mirror of the Swift MosaicRaster tile renderer (used for previews and mockups).

Keep in sync with MosaicRaster.swift: same hash, same bevel/grout/glaze rules.
"""
import numpy as np
from PIL import Image, ImageDraw
from palette import FAMILIES, GROUT, SOIL, hex_to_rgb

MARGIN_L, MARGIN_R, MARGIN_T, MARGIN_B = 2, 2, 2, 6
M32 = 0xFFFFFFFF


def hash32(a, b):
    h = ((a * 0x9E3779B1) & M32) ^ ((b * 0x85EBCA77) & M32)
    h ^= h >> 15
    h = (h * 0x2C1B3C6D) & M32
    h ^= h >> 12
    h = (h * 0x297A2D39) & M32
    h ^= h >> 15
    return h


PAL = [[hex_to_rgb(t) for t in fam[2]] for fam in FAMILIES]
GROUT_RGB = np.array(hex_to_rgb(GROUT), np.float32)
SOIL_RGB = np.array(hex_to_rgb(SOIL), np.float32)


def tile_block(base, s, cellx, celly):
    """Return s x s x 3 float array for one glazed tessera (grout on right/bottom)."""
    g = max(1, round(s / 12))
    inner = s - g
    b = max(1, round(s / 10))
    jit = 1.0 + (((hash32(cellx, celly) & 0xFF) / 255.0) - 0.5) * 0.08
    out = np.empty((s, s, 3), np.float32)
    out[:] = GROUT_RGB
    rc = s * 0.16
    base = np.array(base, np.float32)
    for v in range(inner):
        for u in range(inner):
            # rounded corners
            cxd = min(u + 0.5, inner - u - 0.5)
            cyd = min(v + 0.5, inner - v - 0.5)
            if cxd < rc and cyd < rc and (rc - cxd) ** 2 + (rc - cyd) ** 2 > rc * rc:
                continue
            f = 1.0
            if u < b or v < b:
                f = 1.16
            if u >= inner - b or v >= inner - b:
                f = 0.80
            f *= 1.05 - 0.10 * v / inner
            col = base * f * jit
            out[v, u] = col
    return np.clip(out, 0, 255)


def soil_block(s, cellx, celly, ghost=None):
    out = np.empty((s, s, 3), np.float32)
    for v in range(s):
        for u in range(s):
            n = (hash32(cellx * s + u, celly * s + v) & 0xFF) / 255.0
            f = 0.92 + 0.16 * n
            col = SOIL_RGB * f
            if ghost is not None:
                col = col * 0.86 + np.array(ghost, np.float32) * 0.14
            out[v, u] = col
    return out


def render_board(rows, s=12, cleared=None, hill=True, palette=None):
    """rows: encoded art strings ('.' = empty ground). cleared: set of (x,y) art coords removed.
    palette: optional per-level palette (list of 4 hex tones per family)."""
    pal = PAL if palette is None else [[hex_to_rgb(t) for t in fam] for fam in palette]
    h = len(rows); w = len(rows[0])
    C, R = w + MARGIN_L + MARGIN_R, h + MARGIN_T + MARGIN_B
    img = np.zeros((R * s, C * s, 3), np.float32)
    cache = {}
    for by in range(R):
        for bx in range(C):
            ax, ay = bx - MARGIN_L, by - MARGIN_T
            if 0 <= ax < w and 0 <= ay < h and rows[ay][ax] != '.':
                code = ord(rows[ay][ax]) - 97
                fam, tone = divmod(code, 4)
                if cleared and (ax, ay) in cleared:
                    blk = soil_block(s, bx, by, pal[fam][tone])
                else:
                    blk = tile_block(pal[fam][tone], s, bx, by)
            else:
                key = ('soil', (bx * 7 + by * 3) % 5)
                blk = soil_block(s, bx, by)
            img[by * s:(by + 1) * s, bx * s:(bx + 1) * s] = blk
    im = Image.fromarray(img.astype(np.uint8))
    if hill:
        draw_hill(im, C, R, s)
    return im


def hole_cell(C, R):
    return (C // 2, R - 3)


def draw_hill(im, C, R, s, hole=None):
    d = ImageDraw.Draw(im, 'RGBA')
    hx, hy = hole if hole is not None else hole_cell(C, R)
    cx, cy = (hx + 0.5) * s, (hy + 0.5) * s
    for k, (rx, ry, col) in enumerate([(4.2, 2.3, (92, 70, 50, 255)), (3.3, 1.8, (110, 84, 60, 255)),
                                       (2.4, 1.3, (126, 97, 70, 255))]):
        d.ellipse([cx - rx * s, cy - ry * s + 0.3 * s, cx + rx * s, cy + ry * s + 0.3 * s], fill=col)
    # crumbs
    import random
    rnd = random.Random(7)
    for i in range(40):
        a = rnd.random() * 6.283; r = 2.0 + rnd.random() * 2.3
        x = cx + r * s * np.cos(a); y = cy + r * s * np.sin(a) * 0.55 + 0.3 * s
        rr = s * (0.08 + rnd.random() * 0.1)
        d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=(146, 116, 86, 255))
    d.ellipse([cx - 1.05 * s, cy - 0.62 * s, cx + 1.05 * s, cy + 0.62 * s], fill=(24, 16, 11, 255))
    d.ellipse([cx - 0.75 * s, cy - 0.42 * s, cx + 0.75 * s, cy + 0.38 * s], fill=(8, 5, 3, 255))


if __name__ == "__main__":
    import json, sys
    art = json.load(open(sys.argv[1]))
    for name, s in (("showcase", 12), ("tutorial", 20), ("koi", 14), ("peacock", 14), ("market", 13)):
        render_board(art[name], s).save(sys.argv[2] + "/" + name + "_preview.png")
    print("rendered")
