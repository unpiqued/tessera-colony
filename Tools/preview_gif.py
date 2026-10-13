"""Animated preview of the First Dig level: two teams sent one second apart, ants crawling out of the
hill, lifting tiles and carrying them home. Rendered from the reference scheduler + gait model.
It is a PREVIEW RENDER, not a recording of the app.

Usage: python3 preview_gif.py <levels_report.json> <out.gif>
"""
import json
import math
import sys

from PIL import Image, ImageDraw, ImageFont

from engine import Board, Game, Scheduler
from render import render_board, MARGIN_L, MARGIN_T, PAL
from ant_gait import draw_ant
from mockups import pose

CS = 16


def main():
    rep = json.load(open(sys.argv[1]))
    lv = next(l for l in rep["levels"] if l["key"] == "firstDig")
    board = Board(lv["rows"])
    tunnels = [[tuple(x) for x in t] for t in lv["tunnels"]]
    g = Game(board, tunnels, lv["classic"])
    sch = Scheduler(board, "natural")
    sol = lv["solution"]
    times = [0.0, 1.0, 2.0]
    for m, (q, t0) in enumerate(zip(sol[:3], times)):
        ev = g.dispatch(q)
        sch.schedule(ev, m, t0)
    full = render_board(lv["rows"], CS).convert("RGB")
    cleared_all = {(x, y) for y in range(len(lv["rows"])) for x in range(len(lv["rows"][0]))}
    soil = render_board(lv["rows"], CS, cleared=cleared_all).convert("RGB")
    try:
        f = ImageFont.truetype("/usr/share/fonts/truetype/google-fonts/Poppins-SemiBold.ttf", 13)
    except OSError:
        f = ImageFont.load_default()
    frames = []
    t = 1.5
    while t < 17.0:
        im = full.copy()
        for tr in sch.trips:
            if tr.arrive <= t:
                i = tr.claim.tile
                x, y = i % board.C, i // board.C
                im.paste(soil.crop((x * CS, y * CS, (x + 1) * CS, (y + 1) * CS)), (x * CS, y * CS))
        d = ImageDraw.Draw(im, "RGBA")
        for tr in sch.trips:
            if tr.arrive > t:
                i = tr.claim.tile
                x, y = i % board.C, i // board.C
                d.rectangle([x * CS, y * CS, (x + 1) * CS - 1, (y + 1) * CS - 1], fill=(255, 255, 255, 60))
        im = im.convert("RGBA")
        for tr in sch.trips:
            p = pose(board, tr, t)
            if not p:
                continue
            i = tr.claim.tile
            col = PAL[board.family[i]][board.tone[i]]
            if not p["carrying"] and p["lift"] > 0:
                fx, fy = i % board.C + 0.5, i // board.C + 0.5
                jx, jy = p["x"] + math.cos(p["h"]) * 0.72, p["y"] + math.sin(p["h"]) * 0.72
                e = p["lift"]
                x, y = fx + (jx - fx) * e, fy + (jy - fy) * e
                h = (0.9 - 0.4 * e) * CS / 2
                ImageDraw.Draw(im, "RGBA").rounded_rectangle([x * CS - h, y * CS - h, x * CS + h, y * CS + h], radius=h * 0.3,
                                                             fill=col + (255,), outline=(0, 0, 0, 115))
            draw_ant(im, p["x"], p["y"], p["h"], p["dist"], col, CS, carrying=col if p["carrying"] else None, scale=p["scale"])
        d = ImageDraw.Draw(im, "RGBA")
        label = "PREVIEW RENDER (reference model, not the app)  ·  1x speed  ·  t = %.1fs" % t
        d.rectangle([0, 0, im.width, 22], fill=(20, 14, 10, 220))
        d.text((8, 3), label, font=f, fill=(240, 220, 190))
        frames.append(im.convert("P", palette=Image.ADAPTIVE, colors=128))
        t += 0.125
    frames[0].save(sys.argv[2], save_all=True, append_images=frames[1:], duration=125, loop=0, optimize=True)
    print(len(frames), "frames", full.size)


if __name__ == "__main__":
    main()
