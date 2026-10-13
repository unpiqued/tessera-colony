"""Modern Moments: eight original tile pictures of famous moments of the modern age, drawn with the
supersampled Canvas of art.py (a tile's colour family comes from the dominant object under it, its tone
from the shading). Own compositions throughout: no copied photographs, no lettering, simple figures.

Gentle: first powered flight, Statue of Liberty, Eiffel Tower, Golden Gate Bridge.
Challenge: Everest summit, Sputnik 1.  Master: Moon landing, fall of the Berlin Wall.
"""
import math
import random

import numpy as np

from art import Canvas, LAPIS, SAFFRON, FERN, EMBER, UMBER, PEARL, encode, smoothstep
from art_scenes import ALL, ellipse, rect, tube, frame, sky, cloud, smooth_noise


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def burst(c, cx, cy, r, fam, spokes=10, shade=0.15, prio=1.5, rot=0.0, tips=True):
    """A firework: spokes radiating from a bright centre, each ending in a spark."""
    for k in range(spokes):
        a = rot + 2 * math.pi * k / spokes
        x1, y1 = cx + math.cos(a) * r, cy + math.sin(a) * r
        c.paint(c.line_mask([(cx + math.cos(a) * r * 0.25, cy + math.sin(a) * r * 0.25), (x1, y1)], 0.55),
                fam, shade, prio)
        if tips:
            c.paint(c.circle(x1, y1, 0.55), fam, max(0.0, shade - 0.1), prio + 0.1)
    c.paint(c.circle(cx, cy, 0.7), fam, 0.0, prio + 0.1)


def person(c, x, foot, h, fam, shade, prio=1.6, arms="up", stride=0.0):
    """A simple standing figure `h` tiles tall with its feet at (x, foot); arms 'up', 'wave' or 'run'."""
    head_r = h * 0.13
    hip, neck = foot - h * 0.45, foot - h * 0.78
    m = c.circle(x, foot - h + head_r, head_r)
    m |= c.line_mask([(x, neck), (x, hip)], h * 0.2)
    m |= c.line_mask([(x - 0.1, hip), (x - h * 0.14 - stride, foot)], h * 0.12)
    m |= c.line_mask([(x + 0.1, hip), (x + h * 0.14 + stride, foot)], h * 0.12)
    if arms == "up":
        ends = [(x - h * 0.3, foot - h * 1.02), (x + h * 0.3, foot - h * 1.02)]
    elif arms == "wave":
        ends = [(x - h * 0.34, neck + h * 0.3), (x + h * 0.26, foot - h * 1.05)]
    else:
        ends = [(x - h * 0.34, neck + h * 0.25), (x + h * 0.36, neck + h * 0.12)]
    for ex, ey in ends:
        m |= c.line_mask([(x, neck + h * 0.04), (ex, ey)], h * 0.1)
    c.paint(m, fam, shade, prio)
    return m


# ---------------------------------------------------------------------------
# Gentle
# ---------------------------------------------------------------------------

def first_flight():
    """Kitty Hawk, 1903: the biplane lifts off its launch rail over the dunes, a helper running below."""
    c = Canvas(48, 36)
    X, Y = c.X, c.Y
    sky(c, 0.8, 0.25, horizon=24)
    cloud(c, [(4.5, 18.5, 1.3), (6.8, 17.8, 1.8), (9.2, 18.7, 1.2)])
    # the sea on the horizon, Kill Devil Hill on the right and the rolling sand in front
    sea = Y > 22.4
    c.paint(sea, LAPIS, np.clip(0.6 + 0.12 * np.sin(X * 1.3 + Y * 3), 0, 1))
    c.paint(sea & (np.abs(Y - 24.6 - 0.3 * np.sin(X * 0.7)) < 0.75), PEARL, 0.1, 1.2)
    hill = ellipse(c, 42, 25, 13, 7.5) & (Y < 26)
    c.paint(hill, SAFFRON, np.clip(0.45 + 0.3 * (X - 36) / 12 + 0.04 * np.sin(Y * 2), 0, 1))
    sand = Y > 25.6 + 0.8 * np.sin(X * 0.21 + 0.6)
    c.paint(sand, SAFFRON, np.clip(0.05 + 0.22 * (0.5 + 0.5 * np.sin(X * 0.35 + Y * 0.9)) + 0.01 * (Y - 25), 0, 1))
    for (gx, gy) in ((3.2, 31.0), (42.5, 32.2)):                       # tufts of dune grass
        for dx in (-0.9, 0.0, 0.9):
            c.paint(c.line_mask([(gx + dx, gy + 1.6), (gx + dx * 2, gy - 1.2)], 0.75), FERN, 0.55, 1.3)
    # the launch rail running back along the sand, and the flyer's shadow on it
    c.paint(ellipse(c, 25, 31.0, 7.5, 1.0), SAFFRON, 0.9, 1.1)
    c.paint(c.line_mask([(21, 32.5), (46.5, 27.4)], 1.4), UMBER, 0.8, 1.5)
    # the flyer: two long wings (slight perspective), struts, two propellers in the gap, the pilot
    def wing_y(top_l, top_r, x):
        return top_l + (top_r - top_l) * (x - 4) / 40
    for (tl, tr) in ((3.6, 1.7), (11.0, 8.4)):
        yc = wing_y(tl, tr, X)
        w = (X > 4) & (X < 44) & (Y > yc) & (Y < yc + 3.5 - 0.02 * (X - 4))
        ribs = (np.floor(X / 1.5).astype(int) % 2) == 0
        c.paint(w, PEARL, np.where(ribs, 0.02, 0.3), 1.3)
    for sx in (5.2, 12.6, 35.4, 42.8):
        c.paint(c.line_mask([(sx, wing_y(3.6, 1.7, sx) + 3.0), (sx, wing_y(11.0, 8.4, sx) + 0.3)], 0.55), UMBER, 0.85, 1.7)
    for px in (20.2, 27.8):                                    # two wooden propellers in the gap
        py = wing_y(8.3, 5.9, px)
        c.paint(tube(c, [(px - 0.9, py - 3.2), (px, py), (px + 0.9, py + 3.2)], 1.3, 1.3), SAFFRON, 0.9, 1.7)
    c.paint(ellipse(c, 24.0, wing_y(11.0, 8.4, 24.0) + 0.4, 1.9, 1.0), UMBER, 0.95, 1.8)   # pilot, lying prone
    # the elevator out in front, carried on two booms
    for bx in (20.0, 27.6):
        c.paint(c.line_mask([(bx, wing_y(11.0, 8.4, bx) + 3.2), (bx + 0.3, 19.6)], 0.5), UMBER, 0.85, 1.6)
    for (y0, t) in ((15.0, 1.5), (18.2, 1.5)):
        c.paint(c.poly_mask([(17.2, y0 + 0.35), (30.5, y0 - 0.35), (30.5, y0 + t - 0.35), (17.2, y0 + t + 0.35)]),
                PEARL, 0.1, 1.5)
    # the helper running alongside the wingtip
    person(c, 8.5, 34.0, 6.0, UMBER, 0.9, 1.7, arms="run", stride=0.9)
    frame(c)
    return encode(c.to_tiles())


def liberty():
    """New York harbour, 1886: the copper statue raises her torch over the star fort; fireworks."""
    c = Canvas(36, 48)
    X, Y = c.X, c.Y
    c.paint(ALL(c), LAPIS, np.clip(1.0 - 0.45 * Y / 42, 0, 1))
    # fireworks in the night sky
    burst(c, 28.5, 9.5, 5.0, EMBER, 12, 0.2)
    burst(c, 29.5, 24.5, 3.6, SAFFRON, 10, 0.1, rot=0.3)
    burst(c, 4.5, 20.5, 3.4, PEARL, 9, 0.05, rot=0.2)
    burst(c, 5.2, 32.0, 3.1, SAFFRON, 8, 0.05, rot=0.4)
    # harbour water with reflections
    water = Y > 42.5
    c.paint(water, LAPIS, np.clip(0.55 + 0.25 * np.sin(Y * 3.1 + np.sin(X * 0.8)), 0, 1))
    c.paint(water & (np.sin(Y * 3.1 + np.sin(X * 0.8)) > 0.7) & (np.abs(X - 18) < 6), SAFFRON, 0.25, 1.1)
    # the island: trees and the star-shaped fort walls
    for (bx, by, br) in ((3.5, 40.5, 2.4), (7, 41.2, 2.0), (32.5, 40.5, 2.4), (29, 41.2, 1.9)):
        c.paint(c.circle(bx, by, br) & (Y < 43), FERN, 0.8, 1.1)
    fort = c.poly_mask([(4, 43), (6, 40.5), (10, 40), (12.5, 38.5), (23.5, 38.5), (26, 40), (30, 40.5), (32, 43)])
    c.paint(fort, PEARL, np.clip(0.45 + 0.08 * (Y - 38.5), 0, 1))
    c.paint(fort & (np.abs(Y - 41.0) < 0.35) & (np.abs(X - 18) > 5.2), UMBER, 0.6, 1.2)
    for bx in (9.5, 26.5):
        c.paint(c.poly_mask([(bx - 2.5, 43), (bx, 40.8), (bx + 2.5, 43)]), PEARL, 0.8, 1.2)
    # the pedestal: cornice, shaft with a loggia, a broad base
    ped = rect(c, 12.2, 31.5, 23.8, 39) | rect(c, 11.2, 30.6, 24.8, 31.8) | rect(c, 11.0, 36.5, 25.0, 39.0)
    c.paint(ped, PEARL, np.clip(0.12 + 0.35 * np.abs(X - 17.2) / 6.5 + 0.02 * (Y - 31), 0, 1), 1.1)
    for lx in (14.2, 16.4, 18.6, 20.8):
        c.paint(rect(c, lx - 0.55, 32.6, lx + 0.55, 34.8), UMBER, 0.75, 1.5)
    # the statue: robe, raised arm with torch, head with crown rays, tablet
    cx = 17.5
    robe = c.poly_mask([(14.0, 15.4), (21.2, 15.4), (22.4, 22), (23.6, 30.8), (11.6, 30.8), (12.4, 22)])
    arm = tube(c, [(14.4, 16.4), (13.0, 11.5), (11.6, 6.6)], 2.6, 1.9)
    head = ellipse(c, cx, 12.2, 1.9, 2.3)
    tablet = c.poly_mask([(20.2, 17.4), (23.4, 16.4), (24.4, 24.6), (21.3, 25.4)])
    statue = robe | arm | head
    folds = 0.5 + 0.5 * np.sin(X * 2.2 + 0.25 * Y)
    c.paint(statue, FERN, np.clip(0.0 + 0.2 * folds + 0.16 * (X - 12) / 11, 0, 0.45), 1.2)
    c.paint(head, FERN, np.clip(0.02 + 0.1 * (X - cx), 0, 0.4), 1.4)
    c.paint(tablet, FERN, np.clip(0.62 + 0.02 * (Y - 16), 0, 1), 1.35)
    c.paint(c.line_mask([(20.4, 17.9), (23.4, 16.9)], 0.7), FERN, 0.95, 1.5)
    for k in range(7):
        a = math.pi * (1.1 + 0.8 * k / 6)
        tip = (cx + math.cos(a) * 4.4, 11.6 + math.sin(a) * 4.0)
        c.paint(c.poly_mask([(cx + math.cos(a - 0.35) * 1.8, 11.6 + math.sin(a - 0.35) * 1.8), tip,
                             (cx + math.cos(a + 0.35) * 1.8, 11.6 + math.sin(a + 0.35) * 1.8)]), FERN, 0.12, 1.5)
    # the torch: handle, cup and flame
    c.paint(rect(c, 10.8, 3.6, 12.4, 6.8), FERN, 0.55, 1.5)
    c.paint(ellipse(c, 11.6, 3.4, 1.9, 0.8), FERN, 0.35, 1.5)
    flame = ellipse(c, 11.6, 1.2, 1.5, 2.4) & (Y < 3.2)
    c.paint(flame, SAFFRON, np.clip(0.05 + 0.3 * (Y - 0.5) / 2, 0, 1), 1.7)
    frame(c)
    return encode(c.to_tiles())


def eiffel():
    """Paris, 1889: the lattice tower over the World's Fair, searchlights sweeping the evening sky."""
    c = Canvas(38, 48)
    X, Y = c.X, c.Y
    c.paint(ALL(c), LAPIS, np.clip(1.0 - 0.75 * Y / 34, 0, 1))
    c.paint(Y > 30.5, SAFFRON, np.clip(0.1 + 0.1 * (Y - 30.5), 0, 1))
    # searchlight beams from the summit
    top = (19, 4.0)
    for (ex, e0, e1) in ((-2, -1.5, 3.0), (40, 3.5, 7.5), (-2, 14, 17.5)):
        c.paint(c.poly_mask([top, (ex, e0), (ex, e1)]), PEARL, np.clip(0.02 + 0.02 * np.abs(X - 19), 0, 0.45), 1.0)
    # the central dome of the fair, seen through the great arch
    c.paint(rect(c, 12.5, 37.0, 25.5, 41.5), PEARL, np.clip(0.1 + 0.05 * (Y - 37), 0, 1), 1.1)
    c.paint(rect(c, 12.5, 38.2, 25.5, 40.4) & (np.abs(((X - 12.5) % 2.0) - 1.0) < 0.4), UMBER, 0.8, 1.3)
    c.paint(ellipse(c, 19, 37.2, 3.6, 3.0) & (Y < 37.2), SAFFRON, 0.45, 1.2)
    # the tower: a curving profile, two arched openings, lattice shading, three platforms
    w = np.interp(Y, [1.2, 5.0, 26.2, 33.6, 41.0], [0.25, 1.1, 2.9, 5.2, 9.8])
    tower = (np.abs(X - 19) <= w) & (Y > 1.2) & (Y < 41)
    arch = ellipse(c, 19, 41.5, 6.6, 7.0)
    arch2 = ellipse(c, 19, 33.4, 2.3, 5.2) & (Y < 33.2)
    body = tower & ~arch & ~arch2
    tx, ty = np.floor(X).astype(int), np.floor(Y).astype(int)
    lat = (((tx + ty) % 3 == 0) | ((tx - ty) % 3 == 0)) & (w > 1.6)
    c.paint(body, UMBER, np.where(lat, 0.95, np.clip(0.25 + 0.15 * np.abs(X - 19) / np.maximum(w, 0.5), 0, 1)))
    for (py, hw, th) in ((33.4, 6.6, 1.4), (26.0, 3.8, 1.0), (5.0, 1.8, 0.8)):
        c.paint(rect(c, 19 - hw, py - th / 2, 19 + hw, py + th / 2), UMBER, 0.85, 1.4)
    c.paint(rect(c, 12.8, 33.8, 25.2, 34.6) & ((np.floor(X).astype(int) % 2) == 0), SAFFRON, 0.1, 1.5)
    c.paint(c.circle(19, 3.2, 0.9), SAFFRON, 0.0, 1.8)
    c.paint(c.poly_mask([(19.2, 0.6), (22.2, 1.1), (19.2, 1.9)]), EMBER, 0.3, 1.8)
    # the fairground: lawns and paths, trees, domed pavilions with flags
    ground = Y > 40
    c.paint(ground, FERN, np.clip(0.35 + 0.2 * np.sin(X * 1.7) * 0.5, 0, 1))
    path = ground & (np.abs(X - 19) < 2.2 + (Y - 40) * 1.2)
    c.paint(path, SAFFRON, np.clip(0.15 + 0.03 * (Y - 40), 0, 1), 1.1)
    for (x0, x1, dome_fam) in ((0.5, 10.5, LAPIS), (27.5, 37.5, EMBER)):
        mid = (x0 + x1) / 2
        hall = rect(c, x0, 35.5, x1, 42.5)
        c.paint(hall, PEARL, np.clip(0.1 + 0.2 * (Y - 35.5) / 7, 0, 1), 1.2)
        c.paint(hall & (np.abs(((X - x0) % 2.5) - 1.25) < 0.45) & (Y > 37.2) & (Y < 40.6), UMBER, 0.8, 1.4)
        c.paint(ellipse(c, mid, 35.5, 3.4, 3.6) & (Y < 35.6), dome_fam, 0.55, 1.3)
        c.paint(c.line_mask([(mid, 31.9), (mid, 28.6)], 0.4), UMBER, 0.9, 1.5)
        c.paint(c.poly_mask([(mid, 28.4), (mid + 2.4, 29.2), (mid, 30.0)]), SAFFRON if dome_fam == LAPIS else LAPIS, 0.2, 1.6)
    for bx in (2.5, 6.5, 31.5, 35.5):
        c.paint(ellipse(c, bx, 44.2, 1.8, 1.5), FERN, 0.85, 1.2)
    frame(c)
    return encode(c.to_tiles())


def golden_gate():
    """San Francisco, 1937: the two red-orange towers and swooping cables, fog rolling under the deck."""
    c = Canvas(48, 38)
    X, Y = c.X, c.Y
    sky(c, 0.6, 0.05, horizon=24)
    cloud(c, [(21, 4.5, 1.6), (23.5, 3.6, 2.2), (26, 4.7, 1.5)])
    # Marin headlands behind the far tower, the city bluff at the lower left
    back = (Y > 13.0 + 0.012 * (X - 46) ** 2 + 0.8 * np.sin(X * 0.5)) & (X > 22)
    c.paint(back, FERN, np.clip(0.75 + 0.05 * np.sin(X * 0.9 + Y), 0, 1))
    front = (Y > 18.0 + 0.02 * (X - 44) ** 2 + 0.6 * np.sin(X * 0.7 + 1)) & (X > 24)
    c.paint(front, FERN, np.clip(0.35 + 0.06 * (Y - 18), 0, 1))
    # water and the fog bank under the deck
    water = Y > 27
    c.paint(water, LAPIS, np.clip(0.6 + 0.25 * np.sin(Y * 2.4 + np.sin(X * 0.6) * 1.5), 0, 1))
    fogtop = 22.0 + 1.3 * np.sin(X * 0.45) + 0.8 * np.sin(X * 1.1 + 1)
    fog = (Y > fogtop) & (Y < 31.5 + 1.0 * np.sin(X * 0.3 + 2))
    c.paint(fog, PEARL, np.clip(0.05 + 0.4 * (Y - fogtop) / 9, 0, 1), 1.05)
    bluff = c.poly_mask([(0, 30), (5, 28.5), (9, 31), (12, 38), (0, 38)])
    c.paint(bluff, FERN, np.clip(0.55 + 0.05 * (Y - 28), 0, 1), 1.1)
    c.paint(c.poly_mask([(2, 38), (4.5, 33.5), (8, 34), (10, 38)]), UMBER, 0.6, 1.15)
    # the deck (with its darker truss) receding slightly to the right
    deck_y = 24.3 - 4.2 * X / 48
    c.paint((Y > deck_y) & (Y < deck_y + 1.3), EMBER, 0.45, 1.4)
    c.paint((Y >= deck_y + 1.3) & (Y < deck_y + 1.9), EMBER, 0.95, 1.4)
    # the towers: two legs with portal braces; sky shows between them
    def tower(x0, leg, gap, top, bottom, braces):
        legs = rect(c, x0, top, x0 + leg, bottom) | rect(c, x0 + leg + gap, top, x0 + 2 * leg + gap, bottom)
        br = np.zeros_like(X, bool)
        for (b0, b1) in braces:
            br |= rect(c, x0, b0, x0 + 2 * leg + gap, b1)
        m = (legs | br) & ~fog
        c.paint(m, EMBER, np.clip(0.3 + 0.35 * ((X - x0) % (leg + gap) > leg * 0.55), 0, 1), 1.5)
        return m
    tower(8.8, 1.9, 3.0, 1.6, 30, [(1.6, 3.4), (8.0, 9.4), (14.2, 15.4)])
    tower(35.6, 1.2, 2.0, 11.2, 28, [(11.2, 12.4), (15.0, 15.8), (18.2, 18.9)])
    # main cables and a few suspenders
    near_top, far_top = (12.3, 2.0), (37.8, 11.6)
    cab = [(x, 20.4 - 0.082 * (x - 27.0) ** 2) for x in np.arange(12.3, 37.9, 0.5)]
    c.paint(c.line_mask(cab, 0.75), EMBER, 0.6, 1.6)
    c.paint(c.line_mask([(-1, 17.5), near_top], 0.75), EMBER, 0.6, 1.6)
    c.paint(c.line_mask([far_top, (49, 18.5)], 0.6), EMBER, 0.6, 1.6)
    for sx in np.arange(15.5, 37, 3.0):
        cy_ = 20.4 - 0.082 * (sx - 27.0) ** 2
        c.paint(c.line_mask([(sx, cy_), (sx, 24.3 - 4.2 * sx / 48)], 0.35), EMBER, 0.55, 1.45)
    frame(c)
    return encode(c.to_tiles())


# ---------------------------------------------------------------------------
# Challenge
# ---------------------------------------------------------------------------

def everest():
    """Everest, 1953: two roped climbers near the top of the snowy summit pyramid, a flag and prayer flags
    at the summit, a sea of cloud below."""
    c = Canvas(42, 46)
    X, Y = c.X, c.Y
    c.paint(ALL(c), LAPIS, np.clip(1.0 - 0.3 * np.clip(Y - 20, 0, None) / 16, 0, 1))
    # the pyramid: summit ridge rising from the lower left, a steep right skyline, an arete between the faces
    sx, sy = 24.0, 6.0
    left_y = sy + (sx - X) * 27.0 / 25.0            # the summit ridge (skyline on the left)
    right_y = sy + (X - sx) * 20.0 / 18.0           # the right skyline
    peak = (Y > left_y) & (Y > right_y)
    arete = sx + (Y - sy) * 0.2
    lit, shade = peak & (X <= arete), peak & (X > arete)
    c.paint(lit, PEARL, np.clip(0.02 + 0.18 * (Y - sy) / 30 + 0.1 * (arete - X) / 25, 0, 0.35))
    c.paint(shade, LAPIS, 0.62)
    c.paint(peak & (Y < right_y + 1.7) & (X > sx - 0.5), PEARL, 0.12, 1.5)    # snow rim on the right skyline
    for (gx, gy, ln) in ((9.0, 26.0, 5.5), (15.5, 20.5, 6.5), (20.0, 26.5, 5.0)):  # pale-blue gullies
        c.paint(c.line_mask([(gx, gy), (gx + 0.9, gy + ln)], 0.9) & lit, LAPIS, 0.05, 1.15)
    # a few brown rock bands, wrapping round the arete
    for (y0, gaps) in ((17.0, (19.5, 29.5)), (24.5, (12.0, 23.5, 33.0)), (31.5, (33.5, 38.5))):
        band_y = y0 + 0.22 * np.abs(X - arete)
        band = peak & (np.abs(Y - band_y) < 0.95)
        for gx in gaps:
            band &= np.abs(X - gx) > 1.6
        c.paint(band, UMBER, np.where(X > arete, 0.85, 0.55), 1.1)
    # the sea of cloud, with one far peak poking through
    far = (Y > 30.5 + np.abs(X - 4.5) * 0.9) & (X < 12)
    c.paint(far & ~peak, UMBER, np.where(X > 4.5, 0.8, 0.5))
    c.paint(far & ~peak & (Y < 32.6 + np.abs(X - 4.5) * 0.9), PEARL, 0.1, 1.1)
    billow_top = 36.0 + 0.9 * np.sin(X * 0.7) + 0.6 * np.sin(X * 1.7 + 2)
    c.paint(Y > billow_top, PEARL, np.clip(0.03 + 0.03 * (Y - 36), 0, 0.3), 1.05)
    for (bx, by, bw) in ((7, 40.0, 3.2), (19, 39.2, 3.6), (32, 40.2, 3.4), (13, 43.4, 3.0), (27, 43.6, 3.2),
                         (39, 43.2, 2.6), (2.5, 42.6, 1.8), (25.5, 37.6, 1.8), (38.5, 38.0, 1.8)):
        c.paint(ellipse(c, bx, by, bw, 0.6), LAPIS, 0.15, 1.1)
    # the summit flag and two garlands of prayer flags in clean arcs (blue, white, red, green, yellow)
    c.paint(c.line_mask([(sx, sy + 0.4), (sx, 1.4)], 0.5), UMBER, 0.9, 1.7)
    c.paint(c.poly_mask([(sx + 0.2, 1.3), (sx + 3.2, 2.1), (sx + 0.2, 3.1)]), EMBER, 0.3, 1.8)
    cycle = [LAPIS, PEARL, EMBER, FERN, SAFFRON]
    for (x0, y0, x1, y1, sag, t0, n, off) in ((sx + 0.2, 1.8, 41.5, 6.0, 2.6, 0.2, 8, 0),
                                               (sx + 0.2, 4.4, 41.5, 12.5, 1.5, 0.32, 6, 2)):
        pts = [(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t + sag * 4 * t * (1 - t)) for t in np.linspace(0, 1, 30)]
        c.paint(c.line_mask(pts, 0.35), UMBER, 0.7, 1.3)
        for k in range(n):
            t = t0 + (0.94 - t0) * k / (n - 1)
            fx, fy = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t + sag * 4 * t * (1 - t)
            fam = cycle[(k + off) % 5]
            c.paint(rect(c, fx - 0.75, fy + 0.15, fx + 0.75, fy + 2.0), fam, 0.0 if fam in (LAPIS, PEARL) else 0.3, 1.8)
    # two climbers roped together on the summit ridge: packs, bright suits
    rope = []
    for (x, fam, shade_, arms) in ((13.2, EMBER, 0.35, "run"), (19.2, SAFFRON, 0.55, "up")):
        foot = sy + (sx - x) * 27.0 / 25.0 + 0.4
        c.paint(rect(c, x - 2.0, foot - 5.6, x - 0.4, foot - 3.0), UMBER, 0.85, 1.75)   # rucksack
        person(c, x, foot, 6.6, fam, shade_, 1.8, arms=arms, stride=0.5)
        rope.append((x - 0.2, foot - 3.2))
    mid = ((rope[0][0] + rope[1][0]) / 2, (rope[0][1] + rope[1][1]) / 2 + 1.2)
    c.paint(c.line_mask([rope[0], mid, rope[1]], 0.4), UMBER, 0.95, 1.6)
    frame(c)
    return encode(c.to_tiles())


def sputnik():
    """Sputnik 1, 1957: the polished sphere and its four swept-back antennas over the curve of the Earth."""
    c = Canvas(42, 42)
    X, Y = c.X, c.Y
    c.paint(ALL(c), LAPIS, 0.97)
    # stars: sparkles (plus shapes) and single points
    tx, ty = np.floor(X).astype(int), np.floor(Y).astype(int)
    r = random.Random(57)
    for _ in range(40):
        sx, sy = r.randrange(2, 40), r.randrange(2, 38)
        fam = r.choice([PEARL, PEARL, SAFFRON])
        m = (tx == sx) & (ty == sy)
        if r.random() < 0.6:
            m |= ((np.abs(tx - sx) == 1) & (ty == sy)) | ((np.abs(ty - sy) == 1) & (tx == sx))
        c.paint(m, fam, 0.05, 1.2)
    # the Earth: a haze rim, ocean, continents and cloud swirls
    ex, ey, er = 46.0, 72.0, 57.0
    d = np.hypot(X - ex, Y - ey)
    earth = d < er
    c.paint(earth & (d > er - 1.1), PEARL, 0.2, 1.3)
    ocean = d < er - 1.1
    c.paint(ocean, LAPIS, np.clip(0.2 + 0.35 * (er - d) / 12, 0, 0.7), 1.1)
    land = ocean & ((smooth_noise(c, 21, 0.45) > 0.12) | (smooth_noise(c, 5, 1.1) > 0.5))
    c.paint(land, FERN, np.clip(0.4 + 0.3 * smooth_noise(c, 4, 0.6), 0, 1), 1.1)
    c.paint(land & (smooth_noise(c, 13, 0.5) > 0.3), SAFFRON, 0.45, 1.15)
    c.paint(land & (smooth_noise(c, 33, 0.7) > 0.45), UMBER, 0.5, 1.15)
    for (cx_, cy_, rad) in ((30, 28, 3.4), (37, 36, 2.8), (15, 36, 2.6), (38, 21.5, 2.0), (23, 31, 2.2), (7, 39.5, 2.0)):
        ang = np.arctan2(Y - cy_, X - cx_)
        rr = np.hypot(X - cx_, Y - cy_)
        swirl = (np.sin(ang * 1.0 + rr * 1.6) > 0.35) & (rr < rad)
        c.paint(ocean & swirl, PEARL, 0.1, 1.25)
    c.paint(ocean & (np.abs(np.sin((X * 0.3 - Y * 0.9) * 0.9)) < 0.18) & (smooth_noise(c, 7, 0.4) > 0.1), PEARL, 0.15, 1.2)
    # the Moon, far off
    moon = c.circle(37.0, 5.5, 2.3)
    c.paint(moon, PEARL, 0.2, 1.3)
    c.paint(moon & (c.circle(36.2, 5.0, 0.7) | c.circle(37.9, 6.6, 0.6)), PEARL, 0.8, 1.4)
    # the satellite: four antennas swept back from the polished sphere
    cx, cy, R = 25.0, 11.0, 5.2
    for (ang, ln) in ((158, 21.0), (170, 22.5), (192, 21.5), (204, 19.0)):
        a = math.radians(ang)
        x0, y0 = cx + math.cos(a) * R * 0.9, cy + math.sin(a) * R * 0.9
        c.paint(c.line_mask([(x0, y0), (cx + math.cos(a) * ln, cy + math.sin(a) * ln)], 0.55), PEARL, 0.55, 1.8)
    ball = c.circle(cx, cy, R)
    lit = np.clip(np.hypot(X - (cx - 1.9), Y - (cy - 1.9)) / (R * 1.5), 0, 1)
    c.paint(ball, PEARL, np.clip(0.05 + 0.85 * lit, 0, 1), 1.5)
    c.paint(ball & ~c.circle(cx - 0.9, cy - 1.5, R), LAPIS, 0.15, 1.55)   # the Earth mirrored in the polish
    c.paint(ball & (np.abs(X - cx + 0.55 * (Y - cy)) < 0.4), UMBER, 0.6, 1.6)   # the seam
    c.paint(c.circle(cx - 2.0, cy - 2.0, 1.2), PEARL, 0.0, 1.7)
    frame(c)
    return encode(c.to_tiles())


# ---------------------------------------------------------------------------
# Master
# ---------------------------------------------------------------------------

def crater(c, x, y, rx, prio=1.3):
    """A crater seen at a low angle: a shadowed inner lip at the back, a bright rim at the front."""
    ry = rx * 0.45
    bowl = ellipse(c, x, y, rx, ry)
    c.paint(ellipse(c, x, y + ry * 0.2, rx * 1.25, ry * 1.4), PEARL, 0.1, prio)
    c.paint(bowl, PEARL, 0.45, prio + 0.05)
    c.paint(bowl & ~ellipse(c, x + rx * 0.2, y + ry * 0.8, rx * 0.95, ry * 0.9), UMBER, 0.6, prio + 0.1)


def lunar_module(c, lx, base):
    """The lander: legs and pads, a gold-foil descent stage (with crinkles) and the angular ascent stage."""
    X, Y = c.X, c.Y
    b = base
    c.paint(ellipse(c, lx + 1.0, b + 7.8, 5.5, 1.2), UMBER, 0.9, 1.2)                 # shadow underneath
    for (x0, y0, x1, y1) in ((lx - 4.6, b + 2.5, lx - 9.0, b + 11.4), (lx + 4.6, b + 2.5, lx + 8.8, b + 11.4),
                             (lx, b + 6.2, lx, b + 13.2)):
        c.paint(c.line_mask([(x0, y0), (x1, y1)], 0.8), SAFFRON, 0.8, 1.6)
        c.paint(ellipse(c, x1, y1 + 0.4, 1.5, 0.7), SAFFRON, 0.55, 1.6)
    for side in (-1, 1):
        c.paint(c.line_mask([(lx + side * 4.8, b + 5.4), (lx + side * 8.3, b + 10.4)], 0.5), UMBER, 0.7, 1.55)
    for k in range(3):
        c.paint(c.line_mask([(lx - 0.9, b + 7.8 + 1.6 * k), (lx + 0.9, b + 7.8 + 1.6 * k)], 0.45), UMBER, 0.7, 1.65)
    descent = c.poly_mask([(lx - 5, b), (lx - 3.5, b - 1.4), (lx + 3.5, b - 1.4), (lx + 5, b), (lx + 5, b + 5),
                           (lx + 3.5, b + 6.4), (lx - 3.5, b + 6.4), (lx - 5, b + 5)])
    crinkle = smooth_noise(c, 44, 2.2)
    c.paint(descent, SAFFRON, np.clip(0.2 + 0.45 * (crinkle + 0.5), 0, 1), 1.4)
    c.paint(descent & (crinkle > 0.1), EMBER, 0.4, 1.45)
    c.paint(descent & (crinkle < -0.42), UMBER, 0.6, 1.45)
    c.paint(descent & (np.abs(X - lx + 3.0) < 0.35), UMBER, 0.8, 1.5)
    ascent = c.poly_mask([(lx - 4.2, b - 1.2), (lx - 4.2, b - 6.2), (lx - 2.6, b - 8.2), (lx + 3.2, b - 8.2),
                          (lx + 4.8, b - 6.2), (lx + 4.8, b - 1.2)])
    c.paint(ascent, PEARL, np.clip(0.1 + 0.08 * (X - lx + 4), 0, 0.7), 1.4)
    c.paint(ascent & (Y > b - 3.2) & (X < lx - 1.4), UMBER, 0.75, 1.45)                 # dark thermal panel
    for side in (-1, 1):                                                                # triangular windows
        c.paint(c.poly_mask([(lx + side * 0.6, b - 6.6), (lx + side * 2.8, b - 6.6), (lx + side * 0.6, b - 4.4)]),
                UMBER, 0.95, 1.6)
    c.paint(rect(c, lx - 0.8, b - 3.6, lx + 0.8, b - 1.4), PEARL, 0.75, 1.55)            # hatch
    c.paint(rect(c, lx - 0.7, b - 9.4, lx + 0.9, b - 8.1), PEARL, 0.5, 1.5)             # docking tunnel
    c.paint(c.line_mask([(lx + 4.2, b - 7.2), (lx + 6.4, b - 9.6)], 0.4), PEARL, 0.5, 1.6)
    c.paint(ellipse(c, lx + 7.0, b - 10.2, 1.5, 1.1, -0.5), PEARL, 0.25, 1.6)          # antenna dish


def astronaut(c, x, top):
    """A spacesuited figure (about 20 tiles tall), dark-outlined, gold visor, one arm raised."""
    X, Y = c.X, c.Y

    def suit(g):
        m = c.circle(x, top + 2.7, 2.7 + g) | rect(c, x - 4.8 - g, top + 2.2 - g, x - 1.8 + g, top + 11.2 + g)
        m |= ellipse(c, x, top + 8.6, 3.2 + g, 4.4 + g)
        m |= tube(c, [(x - 2.4, top + 6.4), (x - 3.1, top + 12.4)], 2.0 + 2 * g, 1.8 + 2 * g)
        m |= tube(c, [(x + 2.4, top + 6.4), (x + 4.6, top + 3.8), (x + 5.2, top + 1.0)], 2.0 + 2 * g, 1.8 + 2 * g)
        m |= tube(c, [(x - 1.4, top + 11.8), (x - 2.0, top + 19.6)], 2.4 + 2 * g, 2.2 + 2 * g)
        m |= tube(c, [(x + 1.4, top + 11.8), (x + 2.4, top + 19.6)], 2.4 + 2 * g, 2.2 + 2 * g)
        return m
    c.paint(suit(0.65), UMBER, 0.95, 1.6)
    body = suit(0.0)
    c.paint(body, PEARL, np.clip(0.08 * np.sin(Y * 1.8) ** 2 + 0.03 * (X - x + 3), 0, 0.3), 1.7)
    c.paint(body & rect(c, x - 4.8, top + 2.2, x - 1.8, top + 11.2), PEARL, 0.35, 1.72)    # backpack
    c.paint(ellipse(c, x + 0.6, top + 2.9, 2.0, 1.6), SAFFRON, 0.35, 1.8)                 # gold visor
    c.paint(c.circle(x + 1.4, top + 2.3, 0.6), PEARL, 0.0, 1.85)
    c.paint(rect(c, x - 1.2, top + 7.4, x + 1.2, top + 9.0), PEARL, 0.85, 1.8)            # chest controls
    for (gx, gy) in ((x - 3.2, top + 12.6), (x + 5.2, top + 0.8)):
        c.paint(c.circle(gx, gy, 1.05), LAPIS, 0.5, 1.8)                                  # gloves
    for bx in (x - 2.1, x + 2.6):
        c.paint(ellipse(c, bx, top + 19.8, 1.5, 0.8), PEARL, 0.8, 1.8)                    # boots


def moon_landing():
    """Tranquility Base, 1969: an astronaut, the flag and the gold-foiled lunar module under a black sky."""
    c = Canvas(44, 42)
    X, Y = c.X, c.Y
    tx, ty = np.floor(X).astype(int), np.floor(Y).astype(int)
    c.paint(ALL(c), UMBER, 0.97)
    # stars: sparkles and points in five colours
    r = random.Random(69)
    for _ in range(46):
        sx, sy = r.randrange(2, 42), r.randrange(1, 19)
        m = (tx == sx) & (ty == sy)
        if r.random() < 0.75:
            m |= ((np.abs(tx - sx) == 1) & (ty == sy)) | ((np.abs(ty - sy) == 1) & (tx == sx))
        c.paint(m, r.choice([PEARL, PEARL, SAFFRON, LAPIS, EMBER, FERN]), 0.05, 1.2)
    # the Earth: ocean, green and tan land, cloud bands, a sliver of night
    ex, ey, er = 7.8, 7.4, 5.8
    earth = c.circle(ex, ey, er)
    c.paint(earth, LAPIS, np.clip(0.25 + 0.3 * np.hypot(X - ex, Y - ey) / er, 0, 1), 1.3)
    c.paint(earth & (smooth_noise(c, 17, 1.5) > 0.12), FERN, 0.45, 1.35)
    c.paint(earth & (smooth_noise(c, 3, 1.2) > 0.45), SAFFRON, 0.4, 1.35)
    c.paint(earth & (np.abs(np.sin(Y * 1.3 + np.sin(X * 0.9) * 1.2)) < 0.22), PEARL, 0.05, 1.4)
    c.paint(earth & ~c.circle(ex + 1.3, ey - 0.8, er), UMBER, 0.8, 1.45)
    # grey regolith with craters
    horizon = 19.5 + 1.0 * np.sin(X * 0.23 + 1.0) + 0.4 * np.sin(X * 0.9)
    c.paint(Y > horizon, PEARL, np.clip(0.64 + 0.07 * smooth_noise(c, 2, 0.8), 0, 1))
    for (x, y, rx) in ((4.0, 23.0, 2.6), (23, 22.2, 2.0), (40.5, 22.2, 2.0), (22.5, 28.5, 2.0), (3.8, 32.0, 2.2),
                       (26.5, 39.4, 3.2), (39.5, 39.4, 2.6)):
        crater(c, x, y, rx)
    # tile-sized rocks (with a lit corner) and bootprints (2x2 tiles) scattered over the dust
    for (x, y) in ((28, 32), (41, 28), (2, 36), (32, 38), (17, 24), (41, 34), (10, 38), (20, 33), (15, 30), (36, 35)):
        c.paint((tx >= x) & (tx <= x + 2) & (ty >= y) & (ty <= y + 1), UMBER, 0.6, 1.3)
        c.paint((tx == x) & (ty == y), PEARL, 0.3, 1.35)
    for (x, y) in ((14, 38), (17, 37), (20, 38), (23, 37), (6, 39), (3, 40), (1, 28), (27, 34), (30, 35)):
        c.paint((tx >= x) & (tx <= x + 1) & (ty >= y) & (ty <= y + 1), UMBER, 0.8, 1.5)
    lunar_module(c, 33.0, 21.6)
    # the flag on its pole: red and white stripes, a blue canton with white stars
    c.paint(c.line_mask([(19.5, 36.0), (19.5, 9.8)], 0.55), PEARL, 0.55, 1.7)
    flag = (tx >= 20) & (tx <= 26) & (ty >= 10) & (ty <= 15)
    c.paint(flag, EMBER, 0.45, 1.8)
    c.paint(flag & (ty % 2 == 1), PEARL, 0.05, 1.8)
    canton = flag & (tx <= 22) & (ty <= 12)
    c.paint(canton, LAPIS, 0.8, 1.85)
    c.paint(canton & ((tx + ty) % 2 == 1) & (ty == 11), PEARL, 0.0, 1.9)
    astronaut(c, 11.0, 15.8)
    frame(c)
    return encode(c.to_tiles())


def graffiti(c, x0, x1, y0, y1, r):
    """One wall slab's worth of bright abstract spray shapes (no letters): rings, zigzags, stripes, blobs."""
    X, Y = c.X, c.Y
    fams = [EMBER, SAFFRON, FERN, LAPIS, EMBER, SAFFRON, FERN]
    cx, w = (x0 + x1) / 2, x1 - x0
    slab = rect(c, x0, y0, x1, y1)
    for yy in (y0 + 2.6, y1 - 2.6):
        kind = r.randrange(6)
        a, b = r.sample(fams, 2)
        yy += r.uniform(-0.6, 0.6)
        if kind == 0:      # ring with a dot
            c.paint(c.circle(cx, yy, w * 0.5) & slab, a, 0.3, 1.3)
            c.paint(c.circle(cx, yy, w * 0.24) & slab, b, 0.2, 1.35)
        elif kind == 1:    # zigzag
            pts = [(x0 + 0.3 + (w - 0.6) * (k % 2), yy - 2.4 + 1.6 * k) for k in range(4)]
            c.paint(c.line_mask(pts, 1.2) & slab, a, 0.35, 1.35)
        elif kind == 2:    # diagonal stripes in two colours
            band = slab & (np.abs(Y - yy) < 2.2)
            c.paint(band & (((X + Y) % 3.0) < 1.5), a, 0.3, 1.3)
            c.paint(band & (((X + Y) % 3.0) >= 1.5), b, 0.2, 1.3)
        elif kind == 3:    # a blob with a spot
            c.paint(ellipse(c, cx, yy, w * 0.55, 2.3, r.uniform(-0.5, 0.5)) & slab, b, 0.2, 1.3)
            c.paint(ellipse(c, cx, yy, w * 0.28, 1.1) & slab, a, 0.5, 1.35)
        elif kind == 4:    # triangle
            c.paint(c.poly_mask([(x0, yy + 2.2), (cx, yy - 2.4), (x1, yy + 2.2)]) & slab, a, 0.3, 1.3)
        else:              # squares
            c.paint(slab & (np.abs(Y - yy) < 1.9) & (np.abs(X - cx) < 1.6), a, 0.3, 1.3)
            c.paint(slab & (np.abs(Y - yy) < 0.9) & (np.abs(X - cx) < 0.7), b, 0.1, 1.35)


def berlin_wall():
    """Berlin, 1989: people dancing on the graffiti-covered wall before the floodlit Brandenburg Gate."""
    c = Canvas(46, 40)
    X, Y = c.X, c.Y
    tx, ty = np.floor(X).astype(int), np.floor(Y).astype(int)
    c.paint(ALL(c), LAPIS, np.clip(0.95 - 0.35 * Y / 22, 0, 1))
    # fireworks over the city
    for (fx, fy, fr, fam, n) in ((5, 5.5, 4.2, EMBER, 11), (16.5, 3.4, 2.8, SAFFRON, 8), (31, 3.2, 2.8, FERN, 8),
                                 (41, 6.0, 4.0, PEARL, 11), (2.6, 14.0, 2.2, SAFFRON, 7), (43.4, 14.0, 2.2, EMBER, 7)):
        burst(c, fx, fy, fr, fam, n, 0.1, rot=fx)
    # the floodlit gate: quadriga, attic, entablature, six fluted columns, dark passages, low side wings
    c.paint(rect(c, 7.5, 9.5, 38.5, 24) | rect(c, 16.5, 6.6, 29.5, 9.6), SAFFRON, 0.05)
    c.paint(rect(c, 7.5, 12.2, 38.5, 13.2), SAFFRON, 0.75, 1.2)
    c.paint(rect(c, 18.0, 7.4, 28.0, 8.8), SAFFRON, 0.45, 1.2)
    c.paint(rect(c, 7.5, 10.6, 38.5, 11.4) & (tx % 2 == 0), SAFFRON, 0.5, 1.2)
    for (p0, p1) in ((10.0, 13.0), (15.4, 18.4), (20.8, 25.2), (27.6, 30.6), (33.0, 36.0)):
        c.paint(rect(c, p0, 14.4, p1, 24), LAPIS, 0.95, 1.3)
    for (w0, w1) in ((1.0, 7.5), (38.5, 45.0)):
        c.paint(rect(c, w0, 16.0, w1, 24), SAFFRON, 0.25, 1.1)
        c.paint(rect(c, w0 + 1.2, 17.8, w1 - 1.2, 21.0) & (tx % 2 == 1), UMBER, 0.8, 1.3)
    quad = ellipse(c, 23, 5.6, 3.6, 1.1) | rect(c, 20.0, 4.2, 26.0, 5.6) | c.circle(23.8, 2.8, 1.0)
    c.paint(quad, FERN, 0.85, 1.4)
    c.paint(c.line_mask([(24.8, 4.2), (25.6, 0.9)], 0.45), FERN, 0.85, 1.5)
    # the wall: pipe cap, shadow line, slabs with seams, a rainbow mural band and sprayed shapes
    c.paint(rect(c, -1, 21.0, 47, 22.8), PEARL, 0.05, 1.2)
    c.paint(rect(c, -1, 22.8, 47, 23.4), UMBER, 0.6, 1.2)
    wall = rect(c, -1, 23.4, 47, 35.2)
    c.paint(wall, PEARL, np.clip(0.3 + 0.1 * np.sin(X * 0.9), 0, 1))
    r = random.Random(1989)
    for s in range(10):
        graffiti(c, s * 5 + 1, s * 5 + 5, 23.4, 35.2, r)
    wave = Y - 29.3 - 2.2 * np.sin(X * 0.33)
    for k, fam in enumerate((EMBER, SAFFRON, FERN, LAPIS)):
        c.paint(wall & (np.abs(wave - (k - 1.5) * 0.9) < 0.45) & (np.sin(X * 0.33) > -0.2), fam, 0.3, 1.4)
    c.paint(wall & (tx % 5 == 0), UMBER, 0.65, 1.5)
    # people standing on the wall, arms raised
    for (x, h, fam, arms) in ((3.5, 6.0, UMBER, "up"), (8.8, 5.6, EMBER, "wave"), (14.2, 6.4, PEARL, "up"),
                              (19.6, 5.8, UMBER, "up"), (26.6, 6.4, EMBER, "wave"), (32.2, 5.8, FERN, "up"),
                              (37.8, 6.2, UMBER, "up"), (42.8, 5.6, PEARL, "wave")):
        person(c, x, 21.2, h, fam, 0.35 if fam != UMBER else 0.95, 1.7, arms=arms)
        c.paint(c.circle(x, 21.2 - h + h * 0.13, h * 0.14), UMBER, 0.9, 1.75)
    # the crowd below, heads and shoulders
    c.paint(Y > 35.2, UMBER, 0.85, 1.1)
    for k, x in enumerate(np.arange(1.5, 46, 3.2)):
        fam = [EMBER, LAPIS, SAFFRON, FERN, PEARL][k % 5]
        c.paint(ellipse(c, x, 40.0, 1.5, 2.2) & (Y > 37.0), fam, 0.45, 1.3)
        c.paint(c.circle(x, 36.9, 1.0), UMBER if k % 2 else EMBER, 0.5 if k % 2 else 0.05, 1.35)
    frame(c)
    return encode(c.to_tiles())


SCENES = {
    "firstflight": first_flight, "liberty": liberty, "eiffel": eiffel, "goldengate": golden_gate,
    "everest": everest, "sputnik": sputnik, "moonlanding": moon_landing,
    "berlinwall": berlin_wall,
}
