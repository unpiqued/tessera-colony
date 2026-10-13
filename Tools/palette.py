"""Single source of truth for Tessera Colony colours (exported to Swift by generate_levels.py)."""

# Six colour families, four glaze tones each (0 = lightest, 3 = deepest).
FAMILIES = [
    # name,     SF Symbol glyph,      tones (light -> deep)
    ("Lapis",   "drop.fill",          ["#AED6F4", "#7DB9E8", "#4A8FD1", "#2A5FA8"]),
    ("Saffron", "sun.max.fill",       ["#FFE36A", "#FFCA2C", "#F7AE0E", "#E08E00"]),
    ("Fern",    "leaf.fill",          ["#A8DB86", "#74BD4E", "#46983A", "#276A2C"]),
    ("Ember",   "flame.fill",         ["#FF9A7E", "#F76A43", "#DE4527", "#B52A18"]),
    ("Umber",   "hexagon.fill",       ["#8E6547", "#6E4A30", "#533421", "#3A2315"]),
    ("Pearl",   "cloud.fill",         ["#FFFEFA", "#EEEBE3", "#D9D5CA", "#BDB8AC"]),
]

GROUT = "#261D16"
SOIL = "#3A2D22"
SOIL_DARK = "#2C2119"


def hex_to_rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def tone_rgb(family, tone):
    return hex_to_rgb(FAMILIES[family][2][tone])


# ---- perceptual check helpers (CIEDE2000) ----
import math

def _srgb_to_lab(rgb):
    def lin(c):
        c = c / 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(c) for c in rgb)
    x = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047
    y = (0.2126 * r + 0.7152 * g + 0.0722 * b)
    z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883
    def f(t):
        return t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116
    fx, fy, fz = f(x), f(y), f(z)
    return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))


def ciede2000(rgb1, rgb2):
    L1, a1, b1 = _srgb_to_lab(rgb1)
    L2, a2, b2 = _srgb_to_lab(rgb2)
    C1 = math.hypot(a1, b1); C2 = math.hypot(a2, b2)
    Cb = (C1 + C2) / 2
    G = 0.5 * (1 - math.sqrt(Cb ** 7 / (Cb ** 7 + 25 ** 7)))
    a1p, a2p = (1 + G) * a1, (1 + G) * a2
    C1p, C2p = math.hypot(a1p, b1), math.hypot(a2p, b2)
    h1p = math.degrees(math.atan2(b1, a1p)) % 360
    h2p = math.degrees(math.atan2(b2, a2p)) % 360
    dLp = L2 - L1; dCp = C2p - C1p
    dhp = h2p - h1p
    if C1p * C2p == 0: dhp = 0
    elif dhp > 180: dhp -= 360
    elif dhp < -180: dhp += 360
    dHp = 2 * math.sqrt(C1p * C2p) * math.sin(math.radians(dhp / 2))
    Lbp = (L1 + L2) / 2; Cbp = (C1p + C2p) / 2
    if C1p * C2p == 0: hbp = h1p + h2p
    elif abs(h1p - h2p) <= 180: hbp = (h1p + h2p) / 2
    elif h1p + h2p < 360: hbp = (h1p + h2p + 360) / 2
    else: hbp = (h1p + h2p - 360) / 2
    T = (1 - 0.17 * math.cos(math.radians(hbp - 30)) + 0.24 * math.cos(math.radians(2 * hbp))
         + 0.32 * math.cos(math.radians(3 * hbp + 6)) - 0.20 * math.cos(math.radians(4 * hbp - 63)))
    dtheta = 30 * math.exp(-((hbp - 275) / 25) ** 2)
    Rc = 2 * math.sqrt(Cbp ** 7 / (Cbp ** 7 + 25 ** 7))
    Sl = 1 + 0.015 * (Lbp - 50) ** 2 / math.sqrt(20 + (Lbp - 50) ** 2)
    Sc = 1 + 0.045 * Cbp; Sh = 1 + 0.015 * Cbp * T
    Rt = -math.sin(math.radians(2 * dtheta)) * Rc
    return math.sqrt((dLp / Sl) ** 2 + (dCp / Sc) ** 2 + (dHp / Sh) ** 2 + Rt * (dCp / Sc) * (dHp / Sh))


def cross_family_min_delta():
    worst = []
    for f1 in range(len(FAMILIES)):
        for f2 in range(f1 + 1, len(FAMILIES)):
            for t1 in range(4):
                for t2 in range(4):
                    d = ciede2000(tone_rgb(f1, t1), tone_rgb(f2, t2))
                    worst.append((d, FAMILIES[f1][0], t1, FAMILIES[f2][0], t2))
    worst.sort()
    return worst


if __name__ == "__main__":
    for row in cross_family_min_delta()[:12]:
        print("%.1f  %s%d vs %s%d" % row)
