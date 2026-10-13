"""Python mirror of AntRenderer's gait + a PIL rendition of the cartoon ant (for checks and mockups).

The Swift renderer draws a pre-rendered body sprite (radial-gradient segments, outline, big eyes,
antennae) and live legs. Leg kinematics: alternating tripods; phase = distance / STRIDE; stance feet
slide backwards in the body frame at exactly the ground speed, so they stay planted in the world.
"""
import math
from PIL import Image, ImageDraw, ImageFilter

STRIDE = 0.8
HIPS = [(0.13, 0.07), (0.05, 0.1), (-0.03, 0.08)]
FEET = [(0.47, 0.44), (0.05, 0.53), (-0.4, 0.46)]


def smooth(x):
    t = max(0.0, min(1.0, x))
    return t * t * (3 - 2 * t)


def legs(x, y, heading, dist, moving=True, scale=1.0):
    """Returns list of (hip, knee, foot, lifted) in world cell units."""
    ch, sh = math.cos(heading), math.sin(heading)
    def world(bx, by):
        return (x + (bx * ch - by * sh) * scale, y + (bx * sh + by * ch) * scale)
    out = []
    phase = dist / STRIDE
    for i in range(3):
        for s in (-1.0, 1.0):
            tripod_a = (s < 0) if i == 1 else (s > 0)
            q = phase + (0 if tripod_a else 0.5)
            q -= math.floor(q)
            lift = 0.0
            if q < 0.5:
                off = STRIDE / 4 - (q / 0.5) * STRIDE / 2
            else:
                tt = (q - 0.5) / 0.5
                off = -STRIDE / 4 + smooth(tt) * STRIDE / 2
                lift = math.sin(math.pi * tt)
            if not moving:
                off *= 0.4; lift = 0
            hip = (HIPS[i][0], s * HIPS[i][1])
            foot = (FEET[i][0] + off, s * (FEET[i][1] + 0.06 * lift))
            knee = ((hip[0] + foot[0]) / 2 + (0.06 if i == 0 else (-0.06 if i == 2 else 0)),
                    (hip[1] + foot[1]) / 2 + s * (0.2 + 0.1 * lift))
            out.append((world(*hip), world(*knee), world(*foot), lift > 0.05, (i, s)))
    return out


def planted_foot_drift(step=0.01, distance=2.0):
    """Max world-space movement of a foot while it is planted (should be ~0)."""
    worst = 0.0
    prev = None
    d = 0.0
    while d < distance:
        cur = legs(d, 0.0, 0.0, d)
        if prev is not None:
            for a, b in zip(prev, cur):
                if not a[3] and not b[3]:
                    # both frames planted and same stance (phase did not wrap into swing)
                    dx = b[2][0] - a[2][0]; dy = b[2][1] - a[2][1]
                    worst = max(worst, math.hypot(dx, dy))
        prev = cur
        d += step
    return worst


def lighten(c, t):
    return tuple(int(v + (255 - v) * t) for v in c)


def darken(c, f):
    return tuple(int(v * f) for v in c)


def draw_ant(img, x, y, heading, dist, color, cs, carrying=None, moving=True, scale=1.0, shadow=True):
    """Draw one cartoon ant at world cell coords (x, y) on a PIL image (cs = pixels per cell)."""
    d = ImageDraw.Draw(img, 'RGBA')
    ch, sh = math.cos(heading), math.sin(heading)
    phase = dist / STRIDE
    sway = 0.07 * math.sin(2 * math.pi * 2 * phase) if moving else 0.0
    bob = 1 + 0.03 * math.sin(2 * math.pi * 2 * phase + math.pi / 2) if moving else 1.0
    k = scale * bob
    hb = heading + sway
    cb, sb = math.cos(hb), math.sin(hb)

    def W(bx, by, body=True):
        c_, s_ = (cb, sb) if body else (ch, sh)
        kk = k if body else scale
        return ((x + (bx * c_ - by * s_) * kk) * cs, (y + (bx * s_ + by * c_) * kk) * cs)

    if shadow:
        pts = []
        for a in range(24):
            t = a / 24 * 2 * math.pi
            bx, by = 0.82 * math.cos(t), 0.3 * math.sin(t)
            pts.append(((x + 0.05 + (bx * ch - by * sh) * scale) * cs, (y + 0.12 + (bx * sh + by * ch) * scale) * cs))
        d.polygon(pts, fill=(0, 0, 0, 62))
    lw = max(1, int(0.085 * cs))
    for hip, knee, foot, lifted, _ in legs(x, y, heading, dist, moving, scale):
        p = [(hip[0] * cs, hip[1] * cs), (knee[0] * cs, knee[1] * cs), (foot[0] * cs, foot[1] * cs)]
        col = darken(color, 0.72 if lifted else 0.55) + (255,)
        d.line(p, fill=col, width=lw if not lifted else max(1, int(0.065 * cs)), joint='curve')
        if not lifted:
            r = 0.05 * cs
            d.ellipse([p[2][0] - r, p[2][1] - r, p[2][0] + r, p[2][1] + r], fill=darken(color, 0.4) + (255,))
    outline = darken(color, 0.32)

    def ellipse_part(cx, cy, rx, ry, f):
        # approximate radial gradient with concentric shrinking ellipses
        base = darken(color, f)
        deep = darken(color, f * 0.55)
        lite = lighten(color, 0.5)
        steps = 10
        for i in range(steps):
            t = i / (steps - 1)
            if t < 0.5:
                col = tuple(int(deep[j] + (base[j] - deep[j]) * (t / 0.5)) for j in range(3))
            else:
                col = tuple(int(base[j] + (lite[j] - base[j]) * ((t - 0.5) / 0.5)) for j in range(3))
            sc = 1 - 0.8 * t
            ox, oy = -rx * 0.3 * t, -ry * 0.4 * t
            pts = []
            for a in range(28):
                ang = a / 28 * 2 * math.pi
                pts.append(W(cx + ox + rx * sc * math.cos(ang), cy + oy + ry * sc * math.sin(ang)))
            d.polygon(pts, fill=col + (255,))
        pts = [W(cx + rx * math.cos(a / 28 * 2 * math.pi), cy + ry * math.sin(a / 28 * 2 * math.pi)) for a in range(29)]
        d.line(pts, fill=outline + (255,), width=max(1, int(0.035 * cs)))
        hl = [W(cx - rx * 0.28 + rx * 0.28 * math.cos(a / 16 * 2 * math.pi), cy - ry * 0.53 + ry * 0.19 * math.sin(a / 16 * 2 * math.pi)) for a in range(16)]
        d.polygon(hl, fill=(255, 255, 255, 140))

    for s in (-1, 1):
        pts = []
        for i in range(9):
            t = i / 8
            bx = (1 - t) ** 2 * 0.5 + 2 * (1 - t) * t * 0.64 + t * t * 0.86
            by = s * ((1 - t) ** 2 * 0.09 + 2 * (1 - t) * t * 0.3 + t * t * 0.24)
            pts.append(W(bx, by))
        d.line(pts, fill=outline + (255,), width=max(1, int(0.04 * cs)))
        tx, ty = W(0.86, s * 0.24); r = 0.045 * cs * k
        d.ellipse([tx - r, ty - r, tx + r, ty + r], fill=darken(color, 0.9) + (255,), outline=outline + (255,))
    ellipse_part(-0.44, 0, 0.36, 0.27, 1.0)
    ellipse_part(-0.07, 0, 0.08, 0.055, 0.7)
    ellipse_part(0.07, 0, 0.17, 0.12, 0.88)
    ellipse_part(0.4, 0, 0.2, 0.19, 0.92)
    for s in (-1, 1):
        ex, ey = W(0.47, s * 0.085); rx, ry = 0.07 * cs * k, 0.075 * cs * k
        d.ellipse([ex - rx, ey - ry, ex + rx, ey + ry], fill=(255, 255, 255, 255), outline=outline + (255,))
        px, py = W(0.505, s * 0.08); r = 0.038 * cs * k
        d.ellipse([px - r, py - r, px + r, py + r], fill=(15, 10, 8, 255))
        gx, gy = W(0.49, s * 0.08 - 0.016); r = 0.014 * cs * k
        d.ellipse([gx - r, gy - r, gx + r, gy + r], fill=(255, 255, 255, 230))
    if carrying is not None:
        jx, jy = x + math.cos(heading) * 0.72 * scale, y + math.sin(heading) * 0.72 * scale
        h = 0.25 * cs * scale
        d.rounded_rectangle([jx * cs - h, jy * cs - h, jx * cs + h, jy * cs + h], radius=h * 0.3,
                            fill=carrying + (255,), outline=(0, 0, 0, 115), width=max(1, int(0.05 * cs)))


if __name__ == "__main__":
    import sys
    drift = planted_foot_drift()
    print("max planted-foot drift (cells):", round(drift, 6))
    # film strip: 8 frames of one stride, colour of a Lapis tile, big scale
    cs = 90
    frames = []
    for f in range(8):
        dist = f * STRIDE / 8
        im = Image.new('RGB', (int(2.4 * cs), int(1.6 * cs)), (58, 45, 34))
        draw_ant(im, 1.1 + dist, 0.8, 0.0, dist, (74, 143, 209), cs)
        frames.append(im)
    strip = Image.new('RGB', (frames[0].width * 4, frames[0].height * 2), (30, 24, 20))
    for i, fr in enumerate(frames):
        strip.paste(fr, ((i % 4) * fr.width, (i // 4) * fr.height))
    strip.save(sys.argv[1] if len(sys.argv) > 1 else "gait.png")
