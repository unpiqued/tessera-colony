"""Golden fixtures for test/render.test.js, produced by the Python reference models in ../../Tools.

    python3 tools/make_render_fixtures.py            (from Web/; writes test/fixtures/render_fixture.json.gz)

Scheduler + path planner: real levels from data/levels.json are played through Tools/engine.py's Game
and Tools/session_sim.py's SwiftScheduler (the line-for-line mirror of AntScheduler.swift: homeTime,
undo with claims, prune) with every path style. Each operation (send at a game time, undo, prune,
complete-instantly for a restored game) and its results (new trips: depart, arrive, pickupEnd, home,
route, pauses, lane, style; liftTime/homeTime; busy teams) are dumped so the JS port can replay them.

Where the Python model differs from the Swift code, the Swift code wins and is patched here:
  * engine.plan_route rounds sniff pauses to 3 decimals (round(u, 3)); PathPlanner.swift does not.
  * SwiftScheduler has no completeInstantly (AntScheduler.swift: lift/home = -1_000_000); added below.

Also dumped: AntGeometry.curve / outbound samples (session_sim.curve / outbound), leg kinematics
(ant_gait.legs) and MosaicRaster tile templates (render.tile_block; see the note at raster_fixture).
"""
import gzip
import json
import math
import pathlib
import sys

WEB = pathlib.Path(__file__).resolve().parents[1]
TOOLS = WEB.parent / "Tools"
sys.path.insert(0, str(TOOLS))

import engine as E          # noqa: E402
import session_sim as S     # noqa: E402
import ant_gait as G        # noqa: E402
import render as R          # noqa: E402

# Swift wins: no rounding of sniff pauses (module-level `round` shadows the builtin inside engine.py).
E.round = lambda v, nd=None: v

STYLE_PY = {"direct": "direct", "natural": "natural", "curious": "curious", "wall": "wall", "scout": "scout",
            "randomTeam": "random_team", "randomAnt": "random_ant"}
DTS = [0.05, 0.3, 1.1, 0.0, 2.4, 0.7, 4.0, 0.15]


def enc(v):
    if v == math.inf:
        return "inf"
    if v == -math.inf:
        return "-inf"
    return v


def trip_json(t):
    return {"id": t.id, "move": t.move, "team": t.team, "family": t.family, "tile": t.tile,
            "path": list(t.path), "depart": t.depart, "arrive": t.arrive, "pickupEnd": t.pickup_end,
            "home": t.home, "lane": t.lane, "pauses": [[a, d] for a, d in t.pauses], "style": t.style}


def times_json(sch, board):
    """liftTime / homeTime of every tile cell (ground is always -inf)."""
    return {"lift": [enc(sch.lift[i]) for i in range(board.N) if board.family[i] >= 0],
            "home": [enc(sch.home[i]) for i in range(board.N) if board.family[i] >= 0]}


def complete_instantly(sch, claims):
    for c in claims:
        sch.lift[c.tile] = -1_000_000
        sch.home[c.tile] = -1_000_000


def geometry_samples(trip, board):
    L = len(trip.path)
    us = sorted(set([0.0, 0.25, 0.5, 0.75, 1.0, 1.3, L / 2, L - 0.75, L - 0.5, L - 0.2, float(L)]
                    + [k + 0.1 * ((k * 7) % 10) for k in range(L)]))
    curve = [[u] + list(S.curve(trip, u, board)) for u in us if 0 <= u <= L]
    total = L * S.SwiftScheduler.STEP + sum(d for _, d in trip.pauses)
    es = [total * k / 23 for k in range(24)]
    outb = []
    for e in es:
        u, p = S.outbound(trip, e)
        outb.append([e, u, p])
    return {"trip": trip.id, "curve": curve, "outbound": outb}


def scenario(levels, key, style, moves, undo_at=(), restore=0, prune=True):
    lv = levels[key]
    board = E.Board(lv["art"])
    tunnels = [[tuple(x) for x in q] for q in lv["tunnels"]]
    cap = lv["chambersExpert"]
    game = E.Game(board, tunnels, cap)
    sch = S.SwiftScheduler(board, STYLE_PY[style])
    ops = []
    sol = lv["solution"]
    k = 0
    # restored game: the first `restore` moves are replayed and their claims completed instantly
    for _ in range(restore):
        q = sol[k]
        assert game.can_dispatch(q)
        ev = game.dispatch(q)
        complete_instantly(sch, ev)
        k += 1
    if restore:
        ops.append({"op": "restore", "moves": [sol[i] for i in range(restore)], "times": times_json(sch, board)})
    t = 0.0
    step_i = 0
    undone = set()
    end = min(len(sol), restore + moves)
    while k < end:
        q = sol[k]
        if not game.can_dispatch(q):
            raise RuntimeError("solution move not dispatchable")
        ev = game.dispatch(q)
        now = t + 0.04
        before = len(sch.trips)
        sch.schedule(ev, len(game.moves) - 1, now)
        new = sch.trips[before:]
        busy_t = t + 0.5
        busy = sch.busy_teams(busy_t)
        op = {"op": "send", "q": q, "now": now, "claims": len(ev), "trips": [trip_json(x) for x in new],
              "busyAt": busy_t, "busy": [[u, n] for u, n in sorted(busy.items())],
              "slotFree": [[u, sch.slot_free_time(u)] for u in sorted(busy)]}
        geo = [x for x in new if x.pauses or x.style != "direct"][:2] + new[:1]
        op["geometry"] = [geometry_samples(x, board) for x in geo]
        ops.append(op)
        k += 1
        t += DTS[step_i % len(DTS)]
        step_i += 1
        if prune:
            removed = len(sch.trips)
            sch.prune(t - 0.5)
            ops.append({"op": "prune", "before": t - 0.5, "removed": removed - len(sch.trips),
                        "remaining": [x.id for x in sch.trips]})
        if k in undo_at and k not in undone:
            undone.add(k)
            n = 2 if (k % 2 == 0) else 1
            for _ in range(n):
                claims = game.move_claims[-1]
                game.undo()
                sch.undo(claims, len(game.moves))
                k -= 1
                ops.append({"op": "undo", "remaining": [x.id for x in sch.trips], "times": times_json(sch, board)})
    ops.append({"op": "end", "times": times_json(sch, board), "remaining": [x.id for x in sch.trips]})
    return {"level": key, "style": style, "capacity": cap, "ops": ops}


def raster_fixture(palette):
    """MosaicRaster templates vs Tools/render.py.

    render.tile_block uses the same bevel/grout/glaze rules as MosaicRaster.tileTemplate but a
    continuous per-cell jitter (1 + ((hash32(x, y) & 0xFF)/255 - 0.5) * 0.08) where the Swift code
    picks one of four fixed jitters per cell; so render.hash32 is patched to a fixed value per sample
    and the JS template is called with the same jitter. render.py works in float32, so values may
    differ by 1. Its soil noise (different hash arguments, no sparkle) and hill differ from the Swift
    code by design and are not compared here; the soil template is checked against the transcription
    of MosaicRaster.soilTemplate below.
    """
    out = {"tiles": [], "soil": []}
    real_hash = R.hash32
    for (fam, tone, s, h) in [(0, 2, 12, 0x10), (1, 1, 17, 0x80), (3, 3, 9, 0xF0), (5, 0, 24, 0x41), (2, 2, 3, 0x7F), (4, 1, 7, 0x00)]:
        base = [(palette["tones"][fam][tone] >> sh) & 0xFF for sh in (16, 8, 0)]
        R.hash32 = lambda a, b, h=h: h
        blk = R.tile_block(base, s, 0, 0)
        R.hash32 = real_hash
        jit = 1.0 + (((h & 0xFF) / 255.0) - 0.5) * 0.08
        out["tiles"].append({"base": palette["tones"][fam][tone], "s": s, "jitter": jit,
                             "rgb": [int(v) for v in blk.astype("uint8").reshape(-1)]})

    def soil_template(s, variant, ghost, soil_hex):
        soil = [(soil_hex >> sh) & 0xFF for sh in (16, 8, 0)]
        px = []
        for v in range(s):
            for u in range(s):
                n = (E.hash32(variant * 131 + u, v * 7 + variant) & 0xFF) / 255.0
                col = [c * (0.92 + 0.16 * n) for c in soil]
                if n > 0.965:
                    col = [c * 1.3 for c in col]
                if ghost is not None:
                    g = [(ghost >> sh) & 0xFF for sh in (16, 8, 0)]
                    col = [c * (1 - 0.14) + gg * 0.14 for c, gg in zip(col, g)]
                px += [int(max(0, min(255, c))) for c in col] + [255]
        return px

    for (s, variant, ghost) in [(12, 0, None), (17, 5, palette["tones"][0][2]), (5, 7, palette["tones"][4][3])]:
        out["soil"].append({"s": s, "variant": variant, "ghost": ghost, "soilHex": palette["soil"],
                            "rgba": soil_template(s, variant, ghost, palette["soil"])})
    return out


def legs_fixture():
    out = []
    for (x, y, hd, dist, moving, scale) in [(3.5, 7.25, 0.3, 0.0, True, 1.0), (10.2, 4.1, -2.0, 1.37, True, 0.8),
                                             (5.0, 5.0, 3.0, 2.95, False, 1.0), (0.5, 0.5, 1.2, 0.41, True, 0.45)]:
        legs = G.legs(x, y, hd, dist, moving, scale)
        out.append({"x": x, "y": y, "heading": hd, "dist": dist, "moving": moving, "scale": scale,
                    "legs": [[h[0], h[1], k[0], k[1], f[0], f[1], bool(lf)] for h, k, f, lf, _ in legs]})
    return out


def main():
    data = json.loads((WEB / "data" / "levels.json").read_text())
    levels = data["levels"]
    scenarios = []
    for style in ["direct", "natural", "curious", "wall", "scout", "randomTeam", "randomAnt"]:
        scenarios.append(scenario(levels, "firstDig", style, moves=17, undo_at=(5, 12)))
    for style in ["natural", "curious", "scout", "randomAnt"]:
        scenarios.append(scenario(levels, "koiPond", style, moves=8, undo_at=(4,)))
    alh = levels["worldAlhambra"]
    for style in ["curious", "wall", "scout", "randomTeam"]:
        scenarios.append(scenario(levels, "worldAlhambra", style, moves=10, undo_at=(len(alh["solution"]) - 6,),
                                  restore=len(alh["solution"]) - 12))
    fixture = {"generator": "Web/tools/make_render_fixtures.py",
               "pythonDiffersFromSwift": ["engine.plan_route rounds pauses to 3 decimals (patched out)"],
               "scenarios": scenarios, "raster": raster_fixture(data["palette"]), "legs": legs_fixture()}
    out = WEB / "test" / "fixtures" / "render_fixture.json.gz"
    out.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(fixture, separators=(",", ":")).encode()
    with gzip.open(out, "wb", compresslevel=9) as f:
        f.write(raw)
    n_trips = sum(len(op.get("trips", [])) for sc in scenarios for op in sc["ops"])
    print("wrote %s: %d scenarios, %d trips, %.1f MB json (%.1f MB gz)" %
          (out, len(scenarios), n_trips, len(raw) / 1e6, out.stat().st_size / 1e6))


if __name__ == "__main__":
    main()
