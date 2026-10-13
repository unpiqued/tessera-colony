"""Side-by-side picture of the ant-path styles: the same team, sent at the same moment, routed by
each style (reference model, not a screenshot of the app).

Usage: python3 path_styles.py levels_report.json OUT.png [level_key] [move]
"""
import json
import math
import sys

from PIL import Image, ImageDraw, ImageFont

from engine import Board, Game, Scheduler, MARGIN_L, MARGIN_T
from palette import FAMILIES
from render import render_board

STYLES = [("direct", "Direct"), ("natural", "Natural"), ("curious", "Curious"),
          ("wall", "Wall-hugger"), ("scout", "Scout trail"), ("random_ant", "Random per ant")]


def hexrgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def panel(lv, style, move, s=12):
    board = Board(lv["rows"])
    tunnels = [[tuple(x) for x in t] for t in lv["tunnels"]]
    g = Game(board, tunnels, lv["classic"])
    sch = Scheduler(board, style)
    t = 0.0
    for m, q in enumerate(lv["solution"][:move + 1]):
        sch.schedule(g.dispatch(q), m, t)
        t += 3.0
    # board as it looks when the team of `move` leaves: tiles of earlier moves lifted
    first = min((tr.depart for tr in sch.trips if tr.move == move), default=0)
    cleared = set()
    for tr in sch.trips:
        if tr.arrive <= first:
            c = tr.claim.tile
            cleared.add((c % board.C - MARGIN_L, c // board.C - MARGIN_T))
    im = render_board(lv["rows"], s, cleared).convert("RGBA")
    ov = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    trips = [tr for tr in sch.trips if tr.move == move]
    for i, tr in enumerate(trips):
        fam = tr.claim.family
        col = hexrgb(FAMILIES[fam][2][2])
        off = ((i % 5) - 2) * 0.12
        pts = [((c % board.C) + 0.5 + off, (c // board.C) + 0.5 + off) for c in tr.route]
        pts = [(x * s, y * s) for x, y in pts]
        d.line(pts, fill=col + (235,), width=3, joint="curve")
        d.line(pts, fill=(20, 14, 10, 110), width=1)
        for at, dur in tr.pauses:
            k = min(len(tr.route) - 1, int(at))
            c = tr.route[k]
            x, y = ((c % board.C) + 0.5) * s, ((c // board.C) + 0.5) * s
            d.ellipse([x - 5, y - 5, x + 5, y + 5], outline=(255, 255, 255, 230), width=2)
        tile = tr.claim.tile
        x, y = (tile % board.C) * s, (tile // board.C) * s
        d.rectangle([x + 1, y + 1, x + s - 2, y + s - 2], outline=(255, 255, 255, 200), width=2)
    return Image.alpha_composite(im, ov), len(trips)


def main():
    rep = json.load(open(sys.argv[1]))
    out = sys.argv[2]
    key = sys.argv[3] if len(sys.argv) > 3 else "firstDig"
    move = int(sys.argv[4]) if len(sys.argv) > 4 else 6
    lv = next(l for l in rep["levels"] if l["key"] == key)
    panels = []
    n = 0
    for style, title in STYLES:
        im, n = panel(lv, style, move)
        panels.append((title, im))
    w, h = panels[0][1].size
    pad, head = 16, 34
    cols = 3
    rows = math.ceil(len(panels) / cols)
    sheet = Image.new("RGB", (cols * (w + pad) + pad, rows * (h + head + pad) + pad + 40), (28, 21, 17))
    d = ImageDraw.Draw(sheet)
    try:
        f = ImageFont.truetype("DejaVuSans-Bold.ttf", 20)
        f2 = ImageFont.truetype("DejaVuSans.ttf", 14)
    except OSError:
        f = f2 = ImageFont.load_default()
    for i, (title, im) in enumerate(panels):
        x = pad + (i % cols) * (w + pad)
        y = pad + (i // cols) * (h + head + pad)
        d.text((x, y), title, font=f, fill=(233, 220, 195))
        sheet.paste(im.convert("RGB"), (x, y + head))
    d.text((pad, sheet.height - 32),
           "%s, move %d: the same team of %d ants routed by each style (white squares: its tiles; white rings: sniff stops). "
           "Reference model — not a screenshot of the app." % (lv["title"], move + 1, n), font=f2, fill=(184, 169, 143))
    sheet.save(out)
    print("saved", out, sheet.size)


if __name__ == "__main__":
    main()
