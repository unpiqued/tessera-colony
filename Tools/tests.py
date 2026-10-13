"""Automated checks for Tessera Colony's rules, level data and ant scheduling.

Runs against the Python reference model (engine.py), which mirrors the Swift engine.
Usage: python3 tests.py <levels_report.json> <LevelData.swift> <out_results.json>
"""
import json
import os
import random

import numpy as np
import sys
import time

from engine import (Board, Game, Scheduler, STEP, SLOT, TEAM_GAP, PICKUP, MARGIN, SPARE_MOVE, ADD_MOVE, RECALL_BASE, RECALL_JAMMED, HOLD_BASE, RELEASE_BASE,
                    claims_hash, hint_full, NEIGHBOURS)
from palette import cross_family_min_delta
import scoring

RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append({"name": name, "passed": bool(cond), "detail": detail})
    print(("PASS " if cond else "FAIL ") + name + ("  -- " + detail if detail else ""))
    return cond


def adjacent(board, a, b):
    ax, ay = a % board.C, a // board.C
    bx, by = b % board.C, b // board.C
    return abs(ax - bx) + abs(ay - by) == 1


def verify_claim_sequence(board, claim_lists):
    """Replays claims on a fresh open-map and checks every path is legal at claim time."""
    opn = bytearray(board.N)
    for i, f in enumerate(board.family):
        if f < 0:
            opn[i] = 1
    problems = []
    seen = set()
    for lst in claim_lists:
        for c in lst:
            if c.tile in seen:
                problems.append("tile claimed twice %d" % c.tile)
            seen.add(c.tile)
            if board.family[c.tile] != c.family:
                problems.append("wrong colour at %d" % c.tile)
            if opn[c.tile]:
                problems.append("tile already open %d" % c.tile)
            if not c.path or c.path[0] != board.hole:
                problems.append("path does not start at hole")
            for a, b in zip(c.path, c.path[1:]):
                if not adjacent(board, a, b):
                    problems.append("non-adjacent step")
            for cell in c.path:
                if not opn[cell]:
                    problems.append("walks through occupied cell %d" % cell)
            if not adjacent(board, c.path[-1], c.tile):
                problems.append("stand cell not next to tile")
            opn[c.tile] = 1
            if len(problems) > 5:
                return problems
    return problems


def schedule_game(board, game_claims, gap):
    """Schedules every move's claims, with `gap` seconds of game time between moves."""
    sch = Scheduler(board)
    now = 0.0
    for m, lst in enumerate(game_claims):
        sch.schedule(lst, m, now)
        now += gap
    return sch


def verify_schedule(board, sch):
    problems = []
    lift = {}
    for t in sch.trips:
        lift[t.claim.tile] = t.arrive
    slots = set()
    by_team = {}
    for t in sch.trips:
        s = round(t.depart / SLOT)
        if s in slots:
            problems.append("two ants leave the hole in the same slot")
        slots.add(s)
        by_team.setdefault(t.claim.team, []).append(t.depart)
    for team, deps in by_team.items():
        deps.sort()
        for a, b in zip(deps, deps[1:]):
            if b - a < TEAM_GAP - 1e-9:
                problems.append("team %d releases ants closer than TEAM_GAP" % team)
                break
        if abs(t.arrive - (t.depart + len(t.route) * STEP + sum(d for _, d in t.pauses))) > 1e-9:
            problems.append("arrival time mismatch")
        # every cell on the way out must have been lifted (with margin) before the ant enters it
        for k, cell in enumerate(t.route):
            if board.family[cell] < 0:
                continue
            if cell not in lift:
                problems.append("route crosses a tile that is never lifted")
                break
            delay = sum(d for u, d in t.pauses if u < k - 0.5)
            enter = t.depart + (k - 0.5) * STEP + delay
            if enter + 1e-9 < lift[cell] + PICKUP + MARGIN:
                problems.append("ant enters cell %d before its tile is lifted (%.3f < %.3f)" % (cell, enter, lift[cell] + PICKUP))
                break
        if t.pickup_end - t.arrive < PICKUP - 1e-9:
            problems.append("pickup too short")
        if t.home < t.pickup_end:
            problems.append("returns before pickup")
        if len(problems) > 5:
            break
    return problems


def max_concurrent(sch):
    ev = []
    for t in sch.trips:
        ev.append((t.depart, 1))
        ev.append((t.home, -1))
    ev.sort()
    cur = best = 0
    for _, d in ev:
        cur += d
        best = max(best, cur)
    return best


def max_parallel_teams(sch):
    """Largest number of teams whose release windows (first..last departure) overlap."""
    win = {}
    for t in sch.trips:
        a, b = win.get(t.claim.team, (t.depart, t.depart))
        win[t.claim.team] = (min(a, t.depart), max(b, t.depart))
    ev = []
    for a, b in win.values():
        ev.append((a, 1)); ev.append((b + 1e-6, -1))
    ev.sort()
    cur = best = 0
    for _, d in ev:
        cur += d; best = max(best, cur)
    return best


def max_parallel_colours(sch):
    """Largest number of distinct colour families with ants out of the hole at the same instant (sampled)."""
    if not sch.trips:
        return 0
    end = max(t.home for t in sch.trips)
    best = 0
    tt = 0.0
    trips = sorted(sch.trips, key=lambda t: t.depart)
    while tt < end:
        fams = {t.claim.family for t in trips if t.depart <= tt < t.home}
        best = max(best, len(fams))
        tt += 2.0
    return best


def timed_solution_run(board, tunnels, sol, capacity, reaction=0.3):
    """A patient player follows the designed solution in real (game) time under the slot rule:
    a team may only be sent when a slot is open; a slot stays taken until the team's ants have
    picked up every tile (or while the team waits)."""
    g = Game(board, tunnels, capacity)
    sch = Scheduler(board)
    t = 0.0
    waits = 0
    max_working = 0
    refused = 0
    total_wait = 0.0
    for m, q in enumerate(sol):
        while True:
            chamber_ids = {c.uid for c in g.state.chambers}
            busy = sch.busy_teams(t) - chamber_ids
            occupied = len(g.state.chambers) + len(busy)
            if occupied < capacity:
                break
            if not busy:
                return None      # deadlock: would be a failure
            refused += 1         # a tap now would be refused by the app
            nt = min(sch.slot_free_time(u) for u in busy) + 1e-6
            total_wait += nt - t
            t = nt
            waits += 1
        ev = g.dispatch(q)
        sch.schedule(ev, m, t)
        max_working = max(max_working, len(sch.busy_teams(t + 0.01) | {c.uid for c in g.state.chambers}))
        t += reaction
    end = max(tr.home for tr in sch.trips)
    return {"won": g.won(), "waits": waits, "refused_taps": refused, "max_slots_in_use": max_working,
            "finish_seconds_1x": round(end, 1), "player_wait_seconds_1x": round(total_wait, 1),
            "trips": len(sch.trips), "schedule_problems": verify_schedule(board, sch)}


def invariant_quota(game, board):
    """Tiles still on the board of each colour == quota still owed to that colour."""
    st = game.state
    left = [0] * 6
    for i, f in enumerate(board.family):
        if f >= 0 and not st.open[i]:
            left[f] += 1
    owed = [0] * 6
    for q, tun in enumerate(game.tunnels):
        for f, n in tun[st.heads[q]:]:
            owed[f] += n
    for t in st.chambers:
        owed[t.family] += t.remaining
    if st.jammed:
        owed[st.jammed.family] += st.jammed.remaining
    for stack in st.returned:
        for t in stack:
            owed[t.family] += t.remaining
    return left == owed


def tiny_board_tests():
    # Rows are encoded art: family*4+tone -> letter. a=Lapis0 e=Saffron0 i=Fern0 m=Ember0 q=Umber0 u=Pearl0
    # A 5x3 art: a Fern pocket guarded by an Umber wall.
    rows = ["qqqqq",
            "qiiiq",
            "qqeqq"]
    b = Board(rows)
    tunnels = [[(2, 3)], [(4, 11), (1, 1)]]
    g = Game(b, tunnels, capacity=2)
    ev = g.dispatch(0)
    check("tiny: a team that can't reach its tiles keeps its slot and waits", len(ev) == 0 and len(g.state.chambers) == 1)
    ev = g.dispatch(1)
    fern_after = sum(1 for c in ev if c.family == 2)
    check("tiny: a waiting team resumes automatically once its colour is exposed", fern_after == 3 and len(g.state.chambers) == 0,
          "cascade fern claims=%d" % fern_after)
    g.dispatch(1)
    check("tiny: board cleared, win detected", g.won())
    check("tiny: claim paths legal", not verify_claim_sequence(b, g.move_claims))
    # slot rule: two sealed pockets, one slot
    rows = ["qqqqq",
            "qiqeq",
            "qqqqq"]
    b = Board(rows)
    tunnels = [[(2, 1)], [(1, 1), (4, 13)]]
    g = Game(b, tunnels, capacity=1)
    start_hash = g.state_hash()
    g.dispatch(0)
    check("tiny: no team can be sent while every slot is taken", not g.can_dispatch(1))
    check("tiny: all slots holding waiting teams is detected as blocked", g.deadlocked())
    g.add_chamber()
    check("tiny: adding a slot lets play continue", g.can_dispatch(1) and g.state.capacity == 2 and not g.deadlocked())
    g.dispatch(1)
    check("tiny: sending never jams — the team already owns its slot", g.state.jammed is None and len(g.state.chambers) == 2)
    g.recall(0)
    check("tiny: returning a waiting team frees its slot; it goes to the front of its tunnel",
          len(g.state.chambers) == 1 and g.front(g.state, 0) == (2, 1, 0) and g.can_dispatch(1))
    check("tiny: tiles owed still match tiles left after a return", invariant_quota(g, b))
    g.dispatch(1)          # umber clears the wall; the waiting saffron team finishes by itself
    g.dispatch(0)          # the returned fern team is sent again and finishes
    check("tiny: a returned team can be sent again and the level completes", g.won() and not g.state.chambers)
    while g.moves:
        g.undo()
    check("tiny: undo reverses sends, returns and added slots exactly", g.state_hash() == start_hash)
    # nearest-first order: two reachable fern tiles, quota 1 -> nearest to the hole is taken
    rows = ["iqi",
            "qqq",
            "qiq"]
    b = Board(rows)
    g = Game(b, [[(2, 1)]], capacity=1)
    ev = g.dispatch(0)
    near = ev[0].tile
    check("tiny: team takes the nearest reachable matching tile", len(ev) == 1 and b.family[near] == 2 and near // b.C == 2 + 2,
          "took row %d" % (near // b.C))
    # tunnelling through own colour: a fern corridor from the bottom edge
    rows = ["qqiqq",
            "qqiqq",
            "qqiqq"]
    b = Board(rows)
    g = Game(b, [[(2, 3)]], capacity=1)
    ev = g.dispatch(0)
    check("tiny: a team tunnels through its own colour", len(ev) == 3 and not verify_claim_sequence(b, g.move_claims))
    # old saves made while Hold existed still replay (Hold was removed from the game)
    rows = ["qqqqq",
            "qiiiq",
            "qqeqq"]
    b3 = Board(rows)
    tun = [[(2, 3), (4, 11)], [(1, 1)]]
    g3 = Game(b3, tun, capacity=2)
    for code in (HOLD_BASE + 0, 0):
        g3.apply_move(code)
    check("old saves: a saved game that used Hold still loads, with that team parked in its slot",
          len(g3.state.chambers) == 1 and g3.state.chambers[0].held and g3.state.chambers[0].remaining == 3
          and invariant_quota(g3, b3))
    ev = g3.release(0)
    g3.dispatch(1)
    check("old saves: sending the parked team claims its tiles and the level completes",
          sum(1 for c in ev if c.family == 2) == 3 and g3.won() and not verify_claim_sequence(b3, g3.move_claims))
    g4 = Game(b3, tun, capacity=1)
    g4.apply_move(HOLD_BASE + 0); g4.recall(0)
    check("old saves: a parked team can be returned to its tunnel instead",
          g4.front(g4.state, 0) == (2, 3, 0) and not g4.state.chambers and not g4.state.returned[0][-1].held)


def synthetic_photos():
    import math
    import numpy as np
    from PIL import Image, ImageDraw, ImageFilter
    rng = np.random.default_rng(3)

    def noisy(img, amt=6):
        a = np.asarray(img).astype(float) + rng.normal(0, amt, (img.height, img.width, 3))
        return np.clip(a, 0, 255).astype(np.uint8)
    im = Image.new('RGB', (900, 1200), (250, 250, 248)); d = ImageDraw.Draw(im)
    d.rectangle([440, 600, 470, 1150], fill=(60, 140, 60))
    d.ellipse([200, 750, 450, 870], fill=(70, 160, 70))
    for k in range(10):
        a = k * math.pi / 5; cx, cy = 450 + 170 * math.cos(a), 450 + 170 * math.sin(a)
        d.ellipse([cx - 110, cy - 110, cx + 110, cy + 110], fill=(220, 40, 90))
    d.ellipse([350, 350, 550, 550], fill=(250, 200, 40))
    flower = noisy(im.filter(ImageFilter.GaussianBlur(3)))
    white = noisy(Image.new('RGB', (800, 600), (252, 252, 250)), 2)
    im3 = Image.new('RGB', (1000, 800), (255, 255, 255)); ImageDraw.Draw(im3).ellipse([480, 380, 520, 420], fill=(30, 60, 200))
    g = np.zeros((600, 800, 3)); y = np.linspace(0, 1, 600)[:, None]
    g[..., 0] = 250 - 150 * y; g[..., 1] = 120 + 60 * np.sin(y * 3); g[..., 2] = 60 + 150 * y
    g = np.clip(g, 0, 255).astype(np.uint8); g[400:, :, :] = [40, 70, 50]
    grey = (rng.random((500, 700, 1)) * 200).repeat(3, 2).astype(np.uint8)
    # blotchy multi-colour noise with white holes (enclosed white islands become open ground)
    blot = rng.random((40, 30, 3)) * 255
    blot = np.asarray(Image.fromarray(blot.astype(np.uint8)).resize((600, 800), Image.BICUBIC)).copy()
    holes = np.asarray(Image.fromarray((rng.random((20, 15)) > 0.72).astype(np.uint8) * 255).resize((600, 800), Image.NEAREST)) > 0
    blot[holes] = 253
    return {"blotchy colours with white holes": blot, "flower on white": flower, "all white": white, "tiny logo on white": np.asarray(im3), "sunset (no white)": g, "grey noise": grey}


def photo_tests(metrics):
    from photo import build_photo_level, srgb_to_lab, is_near_white
    import numpy as np
    pm = {}
    for name, img in synthetic_photos().items():
        for detail in ("coarse", "fine", "very_fine"):
            r = build_photo_level(img, detail, seed=7)
            key = "%s/%s" % (name, detail)
            if name in ("all white", "tiny logo on white"):
                check("photo: '%s' (%s) is refused gracefully instead of making a level" % (name, detail),
                      r.get("error") == "not_enough_colour", str(r.get("error")))
                continue
            if "error" in r:
                check("photo: '%s' (%s) produces a level" % (name, detail), False, str(r))
                continue
            board = Board(r["rows"])
            tunnels = [[tuple(x) for x in t] for t in r["tunnels"]]
            g = Game(board, tunnels, r["chambers"]["expert"])
            for q in r["solution"]:
                g.dispatch(q)
            ok = g.won() and not g.state.jammed
            empty = sum(row.count(".") for row in r["rows"])
            quota_ok = sum(q for t in tunnels for _, q in t) == board.tile_count
            fam_ok = all(0 <= f < len(r["palette"]) for t in tunnels for f, _ in t)
            paths_ok = not verify_claim_sequence(board, g.move_claims)
            # every empty cell really was near-white in the downsampled photo, every tile was not
            check("photo: '%s' (%s) becomes a solvable puzzle with matching teams" % (name, detail),
                  ok and quota_ok and fam_ok and paths_ok,
                  "%dx%d grid, %d tiles, %d empty, %d colours, %d teams" % (r["grid"][0], r["grid"][1], board.tile_count, empty,
                                                                             len(r["palette"]), sum(len(t) for t in tunnels)))
            if name == "flower on white":
                check("photo: white background becomes empty ground, not tiles (%s)" % detail, empty > board.tile_count,
                      "%d empty vs %d tiles" % (empty, board.tile_count))
            if name == "sunset (no white)":
                check("photo: a photo without white keeps every cell as a tile (%s)" % detail, empty == 0)
            pm[key] = {"tiles": board.tile_count, "empty": empty, "colours": len(r["palette"]), "teams": sum(len(t) for t in tunnels),
                       "chambers": r["chambers"]}
    # robustness sweep: many seeds on every colourful synthetic photo
    fails = 0
    runs = 0
    imgs = synthetic_photos()
    for name in ("flower on white", "sunset (no white)", "blotchy colours with white holes", "grey noise"):
        for seed in range(1, 13):
            for detail in ("coarse", "fine"):
                runs += 1
                r = build_photo_level(imgs[name], detail, seed=seed)
                if "error" in r:
                    fails += 1
                    continue
                board = Board(r["rows"])
                tunnels = [[tuple(x) for x in t] for t in r["tunnels"]]
                g = Game(board, tunnels, r["chambers"]["expert"])
                for q in r["solution"]:
                    g.dispatch(q)
                if not (g.won() and not g.state.jammed):
                    fails += 1
    check("photo: robustness sweep (4 photos x 12 seeds x 2 detail levels) always yields a solvable level",
          fails == 0, "%d of %d builds failed" % (fails, runs))
    metrics["photo"] = pm


def design_label_grid(rows, n=32):
    """A mosaic's colour families sampled on an n x n grid (-1 = open ground)."""
    H, W = len(rows), len(rows[0])
    return [(-1 if rows[int((j + 0.5) * H / n)][int((i + 0.5) * W / n)] == '.' else
             (ord(rows[int((j + 0.5) * H / n)][int((i + 0.5) * W / n)]) - 97) // 4) for j in range(n) for i in range(n)]


def design_similarity(a, b):
    """Normalised mutual information between two pictures' colour regions. It ignores which colours
    are used, so a recoloured copy of the same design scores close to 1."""
    import math
    from collections import Counter
    n = len(a)
    pa, pb, pab = Counter(a), Counter(b), Counter(zip(a, b))
    ha = -sum(c / n * math.log(c / n) for c in pa.values())
    hb = -sum(c / n * math.log(c / n) for c in pb.values())
    mi = sum(c / n * math.log((c / n) / (pa[x] / n * pb[y] / n)) for (x, y), c in pab.items())
    return 0.0 if min(ha, hb) == 0 else mi / math.sqrt(ha * hb)


def design_tests(rep, metrics):
    """Every built-in mosaic is its own design: no two share a subject, and no pair is a recolouring
    of the same layout (the old repeated rosettes, quilts and mazes scored 0.44-0.58 on this measure)."""
    grids = {lv["key"]: design_label_grid(lv["rows"]) for lv in rep["levels"]}
    keys = list(grids)
    worst = (0.0, "", "")
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            v = design_similarity(grids[keys[i]], grids[keys[j]])
            if v > worst[0]:
                worst = (v, keys[i], keys[j])
    titles = [lv["title"] for lv in rep["levels"]]
    check("designs: all %d built-in mosaics have different titles and subjects" % len(titles), len(set(titles)) == len(titles),
          ", ".join(t for t in titles if titles.count(t) > 1))
    check("designs: no two built-in mosaics are recolourings of one layout (colour-region similarity below 0.45 for every pair)",
          worst[0] < 0.45, "most similar pair: %s / %s at %.2f" % (worst[1], worst[2], worst[0]))
    metrics["design_similarity_max"] = {"pair": [worst[1], worst[2]], "value": round(worst[0], 3)}


def pattern_tests(metrics):
    from pattern import build_pattern_level, pattern_layout, LAYOUTS
    fails = 0
    tiles = []
    layouts = set()
    for seed in range(1, 41):
        layouts.add(pattern_layout(seed))
        r = build_pattern_level(seed)
        if r is None:
            fails += 1
            continue
        board = Board(r["rows"])
        tunnels = [[tuple(x) for x in t] for t in r["tunnels"]]
        g = Game(board, tunnels, r["chambers"]["expert"])
        for q in r["solution"]:
            g.dispatch(q)
        ok = g.won() and not verify_claim_sequence(board, g.move_claims) and \
            sum(q for t in tunnels for _, q in t) == board.tile_count
        if not ok:
            fails += 1
        tiles.append(board.tile_count)
    check("pattern: 40 generated pattern mosaics are all solvable with legal ant paths", fails == 0,
          "%d failed; %d tiles each" % (fails, tiles[0] if tiles else 0))
    check("pattern: the 40 seeds cover all five layouts (rosette, starburst, fish scales, kaleidoscope, ribbons)",
          layouts == set(LAYOUTS), ", ".join(sorted(layouts)))
    grids = [design_label_grid(__import__("pattern").pattern_rows(sd)) for sd in range(1, 41)]
    best = max(design_similarity(grids[i], grids[j]) for i in range(40) for j in range(i + 1, 40))
    check("pattern: no two of the 40 patterns are recoloured copies of each other (similarity below 0.9)", best < 0.9,
          "most similar pair %.2f" % best)
    metrics["pattern"] = {"levels": 40, "failed": fails, "layouts": sorted(layouts), "max_similarity": round(best, 3)}


def route_problems(board, sch):
    """Routes run hole -> the claim's stand cell in 4-neighbour steps and never cross the ant's own tile."""
    C = board.C
    for t in sch.trips:
        r = t.route
        if r[0] != board.hole or r[-1] != t.claim.path[-1]:
            return ["route does not run from the hole to the tile"]
        if any(abs(a % C - b % C) + abs(a // C - b // C) != 1 for a, b in zip(r, r[1:])):
            return ["route is not made of 4-neighbour steps"]
        if t.claim.tile in r:
            return ["route walks over its own tile"]
    return []


def path_style_tests(rep, metrics):
    """Every ant-path style, on a few levels: legal routes and correct timing, and the cost in time."""
    from engine import PATH_STYLES
    pm = {}
    for key in ("firstDig", "nightMarket", "labyrinth", "roseWindow"):
        lv = next((l for l in rep["levels"] if l["key"] == key), None)
        if lv is None:
            continue
        board = Board(lv["rows"])
        tunnels = [[tuple(x) for x in t] for t in lv["tunnels"]]
        base = None
        bad = []
        stats = {}
        worst_send = {}
        for style in PATH_STYLES:
            g = Game(board, tunnels, lv["classic"])
            sch = Scheduler(board, style)
            t = 0.0
            ws = 0
            for m_i, q in enumerate(lv["solution"]):
                sch.schedule(g.dispatch(q), m_i, t)
                ws = max(ws, sch.last_expansions)
                t += 3.0
            worst_send[style] = ws
            probs = verify_schedule(board, sch) + route_problems(board, sch)
            if probs:
                bad.append("%s: %s" % (style, probs[0]))
            longest = max(len(tr.route) / max(1, len(tr.claim.path)) for tr in sch.trips)
            finish = max(tr.home for tr in sch.trips)
            if base is None:
                base = finish
            stats[style] = {"finish_vs_direct": round(finish / base, 2),
                            "mean_route_vs_shortest": round(sum(len(tr.route) for tr in sch.trips) /
                                                            sum(len(tr.claim.path) for tr in sch.trips), 2),
                            "longest_route_vs_shortest": round(longest, 2),
                            "sniff_stops": sum(len(tr.pauses) for tr in sch.trips)}
        pm[key] = stats
        check("paths (%s): all 7 ant-path styles give legal routes — hole to tile in 4-neighbour steps, never through a tile that is still there, sniff stops included" % key,
              not bad, "; ".join(bad[:2]) if bad else "%d ants x 7 styles" % board.tile_count)
        worst = max(v["finish_vs_direct"] for v in stats.values())
        check("paths (%s): no style makes the level more than 1.5x as long as Direct" % key, worst <= 1.5,
              ", ".join("%s x%.2f" % (k, v["finish_vs_direct"]) for k, v in stats.items()))
        from engine import PLAN_BUDGET_PER_SEND
        check("paths (%s): route planning per send stays within its budget (no stall when a big team is sent)" % key,
              max(worst_send.values()) <= PLAN_BUDGET_PER_SEND + 1,
              "most search steps in one send: %d (budget %d)" % (max(worst_send.values()), PLAN_BUDGET_PER_SEND))
        for k in stats:
            stats[k]["most_search_steps_in_one_send"] = worst_send[k]
    metrics["path_styles"] = pm


def versus_tests(rep, metrics):
    """Two-player versus: every combination of options (2 boards x 2 picking x 2 colour rules x 2 slot
    scorings) on two mosaics with careless and greedy players, checking the rules claim by claim."""
    import itertools
    import versus as V
    from engine import NEIGHBOURS as _NB

    class Checked(V.VBoard):
        problems = []

        def _run(self, t):
            before = bytes(self.opn)
            owner_before = list(self.owner)
            c = super()._run(t)
            b = self.board
            C = b.C
            opened = set()
            for cl in c:
                p = cl.path
                if not p or p[0] != self.holes[t.player]:
                    Checked.problems.append("claim does not start at the player's hill")
                    break
                if any(abs(a % C - q % C) + abs(a // C - q // C) != 1 for a, q in zip(p, p[1:])):
                    Checked.problems.append("claim path is not 4-neighbour steps")
                    break
                if any(not before[x] and x not in opened for x in p):
                    Checked.problems.append("claim path crosses a tile that was still there")
                    break
                last = p[-1]
                if abs(last % C - cl.tile % C) + abs(last // C - cl.tile // C) != 1:
                    Checked.problems.append("claim does not end beside its tile")
                    break
                if b.family[cl.tile] != t.family or owner_before[cl.tile] != -1 or before[cl.tile]:
                    Checked.problems.append("wrong colour or tile claimed twice")
                    break
                opened.add(cl.tile)
            if t.remaining < 0:
                Checked.problems.append("team took more than its number")
            return c

    V_VBoard = V.VBoard
    V.VBoard = Checked
    vm = {}
    try:
        for key in ("firstDig", "nestingRings"):
            lv = next((l for l in rep["levels"] if l["key"] == key), None)
            if lv is None:
                continue
            tunnels = [[tuple(x) for x in t] for t in lv["tunnels"]]
            bad, stalls, ends = [], 0, 0
            rule_breaks = 0
            combos = list(itertools.product(V.LAYOUTS, V.PICKING, V.COLOUR, V.SCORING))
            for (layout, picking, colour, scoring) in combos:
                for seed, greedy in ((1, False), (2, False), (3, True)):
                    Checked.problems = []
                    m = V.VMatch(lv["rows"], tunnels, lv["classic"], layout, picking, colour, scoring)
                    rng = random.Random(seed)
                    # play, checking the slot limit and the colour rule after every action
                    n = 0
                    while not m.over() and n < 5000:
                        n += 1
                        p = rng.randrange(2)
                        opts = [(q, d, t) for q, d, t in m.candidates(p) if m.check(p, q, d)[0]]
                        if opts:
                            q, d, t = (min(opts, key=lambda o: (o[1], -o[2].quota)) if greedy else rng.choice(opts))
                            last = m.players[p].last_family
                            others = any(c.family != last for _, _, c in m.candidates(p))
                            if colour == "alternate" and last == t.family and others:
                                rule_breaks += 1
                            if d >= m.reach():
                                rule_breaks += 1
                            m.launch(p, q, d)
                        else:
                            w = m.waiting(p)
                            if w and len(w) >= m.players[p].capacity:
                                if rng.random() < 0.7:
                                    m.add_slot(p)
                                else:
                                    m.return_team(p, rng.choice(w).uid)
                        for pp in (0, 1):
                            if len(m.waiting(pp)) > m.players[pp].capacity:
                                rule_breaks += 1
                    if not m.over():
                        stalls += 1
                    else:
                        ends += 1
                    if layout == "race":
                        fin = [p for p in (0, 1) if m.boards[p].done()]
                        if not fin or m.tiles(fin[0]) != m.tile_count:
                            bad.append("race ended without a finished board")
                    else:
                        if not m.boards[0].done() or m.tiles(0) + m.tiles(1) != m.tile_count:
                            bad.append("shared board ended with tiles left or tiles double-counted")
                    bad += Checked.problems[:1]
            check("versus (%s): all 16 option combinations x 3 players — every claim starts at the right hill, walks only on open ground, takes the right colour once, never over a team's number" % key,
                  not [b for b in bad if "claim" in b or "colour" in b or "number" in b],
                  "; ".join(bad[:2]) if bad else "%d matches" % (len(combos) * 3))
            check("versus (%s): matches always end — race when a player's mosaic is cleared, shared when every tile is taken (tiles split between the two players, none double-counted)" % key,
                  stalls == 0 and not [b for b in bad if "ended" in b], "%d ended, %d stalled" % (ends, stalls))
            check("versus (%s): slot limits, reach 3 and the no-same-colour rule are never broken" % key,
                  rule_breaks == 0, "%d violations" % rule_breaks)
            # timed matches: typical scores with slot upkeep
            scores = {}
            for layout in V.LAYOUTS:
                m = V.VMatch(lv["rows"], tunnels, lv["classic"], layout, "reach3", "alternate", "upkeep")
                sc, fin = V.play_timed(m, random.Random(5))
                scores[layout] = {"scores": [round(x) for x in sc], "finish_seconds_1x": round(fin or -1),
                                  "upkeep": [round(p.upkeep) for p in m.players],
                                  "tiles": [m.tiles(0), m.tiles(1)]}
            vm[key] = scores
            ok = all(v["finish_seconds_1x"] > 0 for v in scores.values())
            check("versus (%s): timed matches under the real-time slot rule finish, and slot upkeep stays a minority of the score" % key,
                  ok and all(max(v["upkeep"]) < 0.5 * max(1, max(v["tiles"])) for v in scores.values()),
                  "; ".join("%s: scores %s, upkeep %s, %ds" % (k, v["scores"], v["upkeep"], v["finish_seconds_1x"]) for k, v in scores.items()))
    finally:
        V.VBoard = V_VBoard
    metrics["versus"] = vm


SCORE_GOLDEN = [
    # tiles, difficulty, modifiers, undos, hints, assists, expected score
    (1008, "expert", ("noHints", "limitedUndo"), 3, 0, 0, 1951),
    (6048, "gentle", (), 12, 2, 1, 2889),
    (1760, "classic", tuple(scoring.MODIFIER_BONUS), 0, 0, 0, 3520),
    (100, "gentle", (), 20, 5, 5, 0),
    (2464, "classic", ("hiddenQueue", "noAssists", "noRepeatColour"), 1, 1, 0, 3912),
]
RANK_TABLE = [(1000, 60.0, 1), (900, 50.0, 2), (900, 40.0, 3), (500, 70.0, 4), (400, 30.0, 5)]
RANK_GOLDEN = [((950, 10.0), 2), ((900, 45.0), 3), ((900, 40.0), 3), ((300, 1.0), None), ((400, 100.0), None),
               ((0, 5.0), None), ((2000, 999.0), 1)]


def score_and_option_tests(rep, swift_src, level_swift, metrics):
    """Solo scoring and high-score tables (golden values shared with the Swift self-test), the
    No colour twice option on every mosaic, and the pack catalogue."""
    bad = []
    for tiles, d, mods, u, h, a, want in SCORE_GOLDEN:
        got = scoring.solo_score(tiles, d, mods, u, h, a)["score"]
        if got != want:
            bad.append("%d/%s/%s: %d != %d" % (tiles, d, mods, got, want))
    check("score: tiles x difficulty x harder options minus undo / hint / assist penalties (5 golden cases, same as the Swift self-test)",
          not bad, "; ".join(bad) or "e.g. First Dig on Expert with No hints + 3 undos, 3 undos used = 1,951")
    bad = []
    for (sc, secs), want in RANK_GOLDEN:
        got = scoring.rank(RANK_TABLE, sc, secs)
        if got != want:
            bad.append("%s -> %s (want %s)" % ((sc, secs), got, want))
    check("high scores: place on the table (higher score first, then faster time; top 5 only; 0 never qualifies)", not bad,
          "; ".join(bad) or "%d cases" % len(RANK_GOLDEN))
    t = []
    rng = random.Random(4)
    ok = True
    for i in range(40):
        e = (rng.randrange(0, 3000), round(rng.uniform(30, 900), 1), i)
        r = scoring.rank(t, e[0], e[1])
        t, place = scoring.insert(t, e)
        if (r is None) != (place is None) or (r is not None and r != place) or len(t) > scoring.KEEP:
            ok = False
    check("high scores: inserting 40 random results keeps the best 5 in order, and the predicted place always matches", ok,
          "final table %s" % [x[0] for x in t])
    # No colour twice keeps every mosaic solvable (searched on Expert, the fewest slots)
    cr = {}
    for lv in rep["levels"]:
        board = Board(lv["rows"])
        tunnels = [[tuple(x) for x in tn] for tn in lv["tunnels"]]
        line, nodes = scoring.solve_colour_rule(board, tunnels, lv["expert"])
        cr[lv["key"]] = {"solved": line is not None and scoring.check_line(board, tunnels, lv["expert"], line), "nodes": nodes}
    unsolved = [k for k, v in cr.items() if not v["solved"]]
    check("harder option No colour twice: every built-in mosaic still has a winning line on Expert (no undo, no assists)",
          not unsolved, ("unsolved: " + ", ".join(unsolved)) if unsolved else "%d mosaics, at most %d search nodes"
          % (len(cr), max(v["nodes"] for v in cr.values())))
    metrics["colour_rule"] = cr
    # catalogue: every generated level is listed in exactly one pack, with the right pack tag
    import re
    lists = {}
    swift_names = {"worldart": "worldArt"}
    for pack in ("main", "challenge", "garden", "master", "wild", "gallery", "worldart", "ancient", "voyages",
                 "modern", "cosmos", "epics", "tales", "childrens", "stage", "adventure", "gothic", "novels",
                 "naturalist", "crafts", "geometry", "space", "inventions", "halloween", "winter"):
        m = re.search(r"static let %s: \[LevelDefinition\] = \[(.*?)\]" % swift_names.get(pack, pack), level_swift, re.S)
        lists[pack] = re.findall(r"GeneratedLevels\.(\w+)", m.group(1)) if m else []
    listed = [k for v in lists.values() for k in v]
    keys = [lv["key"] for lv in rep["levels"]]
    wrong = [lv["key"] for lv in rep["levels"] if lv["key"] not in lists.get(lv.get("pack", "main"), [])]
    check("catalogue: all %d generated mosaics appear exactly once in the app's packs, each in its own pack" % len(keys),
          sorted(listed) == sorted(keys) and not wrong,
          "; ".join("%s %d" % (p, len(v)) for p, v in lists.items()) + ((" · misplaced: " + ", ".join(wrong)) if wrong else ""))
    tagged = [lv["key"] for lv in rep["levels"] if lv.get("pack", "main") != "main"
              and ('pack: "%s"' % lv["pack"]) not in swift_src]
    check("catalogue: pack tags are exported to LevelData.swift", not tagged, ", ".join(tagged))


def challenge_tests(rep, swift_src, metrics):
    """Difficulty ratings exported to Swift, and the Challenge pack being hard but fair."""
    from generate_levels import policy_win_rate, planner_win, MASTER_BAR
    cm = {}
    for lv in rep["levels"]:
        key = lv["key"]
        exported = "carelessWins: [%s]" % ", ".join("%.3f" % x for x in lv["careless"])
        check("%s: measured difficulty (careless win rates, one-step player) is exported to the app" % key,
              exported in swift_src and len(lv["greedy"]) == 3, exported)
        if not lv.get("challenge"):
            continue
        board = Board(lv["rows"])
        tunnels = [[tuple(x) for x in t] for t in lv["tunnels"]]
        caps = (lv["gentle"], lv["classic"], lv["expert"])
        greedy = [policy_win_rate(board, tunnels, c, "greedy", 1, 0) > 0 for c in caps]
        careless = [policy_win_rate(board, tunnels, c, "random", 40, 5) for c in caps]
        # built-in Master levels, and collection levels of the master tier, meet the Master bar; the
        # Challenge pack and collection levels of the challenge tier meet the Challenge bar
        if (lv.get("tier") or lv.get("pack")) == "master":
            look = [planner_win(board, tunnels, c) for c in caps]
            cm[key] = {"careless_gentle_classic_expert": careless, "one_step_wins": greedy, "lookahead_wins_gentle_classic_expert": look}
            check("master %s: always sending a team that can finish now fails on Classic and Expert" % key,
                  greedy[1:] == [False, False], "one-step player: gentle %s, classic %s, expert %s" % tuple(greedy))
            check("master %s: careless tapping rarely wins (Classic <= %d%%, Expert <= %d%%)"
                  % (key, round(100 * MASTER_BAR["careless_classic"]), round(100 * MASTER_BAR["careless_expert"])),
                  careless[1] <= MASTER_BAR["careless_classic"] and careless[2] <= MASTER_BAR["careless_expert"],
                  "careless wins: gentle %.0f%%, classic %.0f%%, expert %.0f%%" % tuple(100 * x for x in careless))
            check("master %s: a look-ahead player (the hint's rollouts) wins on at least two of the three difficulties" % key,
                  sum(look) >= MASTER_BAR["lookahead_min"], "look-ahead wins: gentle %s, classic %s, expert %s (the designed line always wins)" % tuple(look))
            continue
        look = [planner_win(board, tunnels, c) for c in caps[1:]]
        cm[key] = {"careless_gentle_classic_expert": careless, "one_step_wins": greedy, "lookahead_wins_classic_expert": look}
        check("challenge %s: always sending a team that can finish now wins on Gentle but fails on Classic and Expert" % key,
              greedy == [True, False, False], "one-step player: gentle %s, classic %s, expert %s" % tuple(greedy))
        check("challenge %s: careless tapping rarely wins (Classic <= 40%%, Expert <= 20%%)" % key,
              careless[1] <= 0.40 and careless[2] <= 0.20,
              "careless wins: gentle %.0f%%, classic %.0f%%, expert %.0f%%" % tuple(100 * x for x in careless))
        check("challenge %s: still fair — a look-ahead player (the hint's rollouts) wins on Classic and Expert" % key,
              all(look), "look-ahead wins: classic %s, expert %s" % tuple(look))
    metrics["challenge"] = cm


def collection_tests(rep, metrics):
    """The collection packs: each ordered from gentlest to hardest by its measured Classic
    rating, each spanning the range, and every mosaic fair on Gentle for a thinking player."""
    from generate_levels import planner_win, rating
    from art_packs import COLLECTION
    by_key = {lv["key"]: lv for lv in rep["levels"]}
    cm = {}
    unfair = []
    for pack, title, _, specs in COLLECTION:
        lvs = [by_key[s[0]] for s in specs if s[0] in by_key]
        check("collection %s: all %d mosaics were generated" % (pack, len(specs)), len(lvs) == len(specs), "%d found" % len(lvs))
        classic = [rating(lv["careless"][1], lv["greedy"][1]) for lv in lvs]
        expert = [rating(lv["careless"][2], lv["greedy"][2]) for lv in lvs]
        order = list(zip(classic, expert))
        check("collection %s: ordered from gentlest to hardest (Classic rating, then Expert, never goes down)" % pack,
              order == sorted(order), "Classic " + " ".join(map(str, classic)) + " · Expert " + " ".join(map(str, expert)))
        check("collection %s: spans the range — a Relaxed or Steady mosaic and a Hard or Fiendish one on Classic" % pack,
              min(classic) <= 2 and max(classic) >= 4, "Classic ratings %s" % classic)
        for lv in lvs:
            board = Board(lv["rows"])
            tunnels = [[tuple(x) for x in t] for t in lv["tunnels"]]
            look = [planner_win(board, tunnels, c) for c in (lv["gentle"], lv["classic"], lv["expert"])]
            cm[lv["key"]] = {"classic_rating": rating(lv["careless"][1], lv["greedy"][1]),
                             "lookahead_wins_gentle_classic_expert": look}
            if not (look[0] or look[1]):
                unfair.append(lv["key"])
    counts = [sum(1 for v in cm.values() if sum(v["lookahead_wins_gentle_classic_expert"]) == k) for k in (3, 2, 1, 0)]
    check("collection: every one of the %d mosaics can be won by a thinking player — the look-ahead player (the "
          "hint's rollouts) wins it on Gentle or Classic (the designed line wins on all three)" % len(cm),
          not unfair, (("look-ahead loses both: " + ", ".join(unfair) + " · ") if unfair else "")
          + "look-ahead wins all three difficulties on %d, two on %d, one on %d, none on %d" % tuple(counts))
    metrics["collection"] = cm


def sound_tests(rep, metrics):
    """Synthesized sound effects (sounds.py mirrors SoundBoard.swift) and the timing of tile clinks."""
    import sounds
    fx = sounds.build_all()
    bad = [k for k, x in fx.items()
           if not (abs(float(abs(x).max()) - 0.9) < 1e-3 and abs(float(x[0])) < 1e-3 and abs(float(x[-1])) < 1e-3
                   and bool(np.isfinite(x).all()))]
    check("sound: all %d synthesized effects are clean (0.9 peak, silent start and end, no NaN)" % len(fx), not bad, ", ".join(bad))
    worst = sounds.worst_case_mix(fx)
    check("sound: the loudest plausible moment stays below full scale even before the limiter", worst < 1.0,
          "peak %.3f" % worst)
    sm = {"worst_case_mix_peak": round(worst, 3)}
    for key in ("firstDig", "sunflower"):
        lv = next(l for l in rep["levels"] if l["key"] == key)
        board = Board(lv["rows"])
        tunnels = [[tuple(x) for x in t] for t in lv["tunnels"]]
        g = Game(board, tunnels, lv["classic"])
        sch = Scheduler(board)
        t = 0.0
        for m_i, q in enumerate(lv["solution"]):
            sch.schedule(g.dispatch(q), m_i, t)
            t += 3.0
        trips = [(tr.arrive, tr.home) for tr in sch.trips]
        runs = {name: sounds.pump_simulation(trips, plan) for name, plan in sounds.SPEED_PLANS.items()
                if not (key == "sunflower" and name == "0.1x")}
        sm[key] = runs
        steady = max(runs[n]["max_timing_error_ms"] for n in ("1x", "16x"))
        check("sound (%s): at a steady speed every clink starts exactly when its ant lifts the tile" % key, steady < 1.0,
              "max error %.1f ms at 1x and 16x" % steady)
        changing = [runs[n] for n in ("jumps", "drags")]
        ok = all(r["max_timing_error_ms"] <= 50 and r["duplicates"] == 0 and r["voice_starved"] == 0
                 and r["max_ms_from_a_pickup_to_the_nearest_clink"] <= 300 for r in changing)
        check("sound (%s): through speed jumps and slider drags clinks stay within 50 ms of their pickup, never repeat or run out of voices" % key,
              ok, "; ".join("%s: max error %.0f ms, longest miss %.0f ms" % (n, runs[n]["max_timing_error_ms"],
                                                                           runs[n]["max_ms_from_a_pickup_to_the_nearest_clink"])
                             for n in ("jumps", "drags")))
        rate = max(r["max_clinks_in_any_second"] for r in runs.values())
        check("sound (%s): at most 20 clinks a second, even at 16x" % key, rate <= 20, "max %d per second" % rate)
    metrics["sound"] = sm


def _session_job(job):
    """One play session in a worker process (see session_sim.py)."""
    import session_sim as S
    kind, lv, difficulty, style, seed = job
    try:
        if kind == "stress":
            r = S.ant_stress(lv, style, seed, 300)
            return {"kind": kind, "key": lv["key"], "style": style, "seed": seed, "trap": None,
                    "route_problems": r["route_problems"], "won": r["won"], "stress": {k: v for k, v in r.items() if k != "route_problems"}}
        s = S.random_session(lv, difficulty, style, seed)
        return {"kind": kind, "key": lv["key"], "difficulty": difficulty, "style": style, "seed": seed, "trap": None,
                "route_problems": s.sch.route_problems[:3], "won": s.game.won() and not s.sch.trips,
                "counts": s.counts, "poses": s.poses}
    except S.Trap as e:
        return {"kind": kind, "key": lv["key"], "difficulty": difficulty, "style": style, "seed": seed,
                "trap": str(e), "route_problems": [], "won": False}


def session_tests(rep, metrics, workers=2):
    """The Alhambra Tiles crash report (3 Oct: Expert, nearly finished, Curious ants). Whole play
    sessions through a step-by-step mirror of the Swift game screen (session_sim.py): the designed line
    part of the way, then careless sends, undos, returned teams and added slots at random moments, with
    the board drawn as the app draws it. Any step that would stop the Swift app (Int of inf/nan, an index
    out of range, an empty route, a non-finite ant pose) or any illegal route fails the check."""
    from multiprocessing import Pool
    levels = {l["key"]: l for l in rep["levels"]}
    alh = levels["worldAlhambra"]
    from engine import PATH_STYLES
    jobs = []
    for st in PATH_STYLES:
        for i in range(12):
            jobs.append(("alhambra", alh, "expert", st, 3000 + 17 * i + PATH_STYLES.index(st)))
    for i in range(12):
        jobs.append(("alhambra_classic", alh, "classic", "curious", 5000 + i))
    for lv in rep["levels"]:
        jobs.append(("every", lv, "expert", "curious", 7000 + len(jobs)))
    jobs.append(("stress", alh, "expert", "curious", 4))
    jobs.append(("stress", alh, "expert", "random_ant", 5))
    t0 = time.time()
    with Pool(workers) as pool:
        res = pool.map(_session_job, jobs, chunksize=1)
    secs = time.time() - t0
    names = {"direct": "Direct", "natural": "Natural", "curious": "Curious", "wall": "Wall-hugger",
             "scout": "Scout trail", "random_team": "Random per team", "random_ant": "Random per ant"}

    def summary(rs):
        bad = [r for r in rs if r["trap"] or r["route_problems"]]
        ants = sum(r.get("counts", {}).get("ants", 0) for r in rs)
        poses = sum(r.get("poses", 0) for r in rs)
        acts = sum(sum(r.get("counts", {}).get(k, 0) for k in ("undos", "returns", "adds")) for r in rs)
        won = sum(1 for r in rs if r["won"])
        if bad:
            b = bad[0]
            return False, "%s seed %s: %s" % (b["key"], b["seed"], b["trap"] or b["route_problems"][0])
        return True, "%d sessions, %d finished; %s ants planned, %s ant poses drawn, %d undos/returns/added slots" % (
            len(rs), won, "{:,}".format(ants), "{:,}".format(poses), acts)

    m = {"seconds": round(secs, 1)}
    for st in PATH_STYLES:
        rs = [r for r in res if r["kind"] == "alhambra" and r["style"] == st]
        ok, detail = summary(rs)
        check("session: Alhambra Tiles on Expert with %s ants — careless play with undo, returns and added slots at random moments, "
              "often from a nearly finished board: nothing that would stop the app, every route legal" % names[st], ok, detail)
        m["alhambra_expert_" + st] = detail
    rs = [r for r in res if r["kind"] == "alhambra_classic"]
    ok, detail = summary(rs)
    check("session: Alhambra Tiles on Classic with Curious ants, same careless play: nothing that would stop the app, every route legal",
          ok, detail)
    rs = [r for r in res if r["kind"] == "every"]
    ok, detail = summary(rs)
    check("session: every one of the %d built-in mosaics, one careless Expert session each with Curious ants: nothing that would stop "
          "the app, every route legal" % len(rs), ok, detail)
    m["every_level_expert_curious"] = detail
    rs = [r for r in res if r["kind"] == "stress"]
    bad = [r for r in rs if r["trap"] or r["route_problems"]]
    check("session: the app's new self-test 'Ant stress' (same choices: Curious seed 4, Random per ant seed 5 on Alhambra Tiles, Expert) "
          "runs clean in the reference model and finishes the mosaic", not bad and all(r["won"] for r in rs),
          "; ".join("%s: %d actions, %d sends, %d undos, %d returns, %d slots added, %s ants" % (
              names[r["style"]], r["stress"]["actions"], r["stress"]["sends"], r["stress"]["undos"], r["stress"]["returns"],
              r["stress"]["adds"], "{:,}".format(r["stress"]["trips"])) for r in rs if "stress" in r) or str(bad[:1]))
    metrics["session"] = m


def main():
    rep = json.load(open(sys.argv[1]))
    from generate_levels import read_swift_levels
    swift_src = read_swift_levels(sys.argv[2])
    out = sys.argv[3]
    t0 = time.time()
    metrics = {}

    tiny_board_tests()

    worst = cross_family_min_delta()[0]
    check("palette: every cross-family tone pair differs by CIEDE2000 >= 15", worst[0] >= 15,
          "closest pair %s%d vs %s%d = %.1f" % (worst[1], worst[2], worst[3], worst[4], worst[0]))

    for lv in rep["levels"]:
        key = lv["key"]
        board = Board(lv["rows"])
        tunnels = [[tuple(x) for x in t] for t in lv["tunnels"]]
        sol = lv["solution"]
        m = {}
        # solvability at every difficulty
        for label, cap in (("expert", lv["expert"]), ("classic", lv["classic"]), ("gentle", lv["gentle"])):
            g = Game(board, tunnels, cap)
            maxch = 0
            for q in sol:
                g.dispatch(q)
                maxch = max(maxch, len(g.state.chambers))
                if g.state.jammed:
                    break
            check("%s: designer solution clears the board at %s (%d slots)" % (key, label, cap), g.won() and not g.state.jammed,
                  "at most %d teams waiting at once" % maxch)
        g = Game(board, tunnels, lv["classic"])
        for q in sol:
            g.dispatch(q)
        probs = verify_claim_sequence(board, g.move_claims)
        check("%s: every ant path is legal (starts at hole, 4-adjacent steps, only open cells, ends beside its tile)" % key,
              not probs, "; ".join(probs[:3]) if probs else "%d claims checked" % sum(len(x) for x in g.move_claims))
        check("%s: sum of team quotas equals tile count" % key,
              sum(q for t in tunnels for _, q in t) == board.tile_count, "%d tiles" % board.tile_count)
        # golden values present in Swift data
        ch = claims_hash(g.move_claims)
        check("%s: golden claim hash exported to Swift matches the reference model" % key,
              ("0x%016X" % ch) in swift_src, "0x%016X" % ch)
        # schedule at several player speeds
        path_lengths = [len(c.path) for lst in g.move_claims for c in lst]
        m["max_path_cells"] = max(path_lengths)
        m["mean_path_cells"] = round(sum(path_lengths) / len(path_lengths), 1)
        for gap in (0.0, 1.5, 4.0):
            sch = schedule_game(board, g.move_claims, gap)
            probs = verify_schedule(board, sch)
            check("%s: pickup timing & hole spacing valid when moves are %.1fs apart" % (key, gap), not probs,
                  "; ".join(probs[:2]) if probs else "")
            m["gap_%.1f" % gap] = {
                "animation_seconds_1x": round(max(t.home for t in sch.trips), 1),
                "max_ants_on_board": max_concurrent(sch),
                "max_teams_releasing_at_once": max_parallel_teams(sch),
                "max_colours_on_board_at_once": max_parallel_colours(sch),
            }
            if gap == 1.5:
                check("%s: teams sent while others are still working release ants concurrently (interleaved at the hole)" % key,
                      max_parallel_teams(sch) >= 2 and max_parallel_colours(sch) >= 2,
                      "up to %d teams releasing, %d colours on the board at once" % (max_parallel_teams(sch), max_parallel_colours(sch)))
                per_team = {}
                for tr in sch.trips:
                    per_team[tr.claim.team] = per_team.get(tr.claim.team, 0) + 1
                quotas = {q * 1000 + i: n for q, tun in enumerate(tunnels) for i, (_, n) in enumerate(tun)}
                check("%s: every team ends up with exactly its quota of ant trips (no duplicates, no shortfall)" % key,
                      per_team == quotas and len({tr.claim.tile for tr in sch.trips}) == len(sch.trips) == board.tile_count,
                      "%d trips, %d distinct tiles" % (len(sch.trips), len({tr.claim.tile for tr in sch.trips})))
        # real-time slot rule with the designed solution
        for label in ("expert", "classic"):
            r = timed_solution_run(board, tunnels, sol, lv[label])
            ok = r is not None and r["won"] and not r["schedule_problems"] and r["max_slots_in_use"] <= lv[label]
            check("%s: in real time, teams are only sent into open slots and the level completes (%s, %d slots)" % (key, label, lv[label]),
                  ok, "" if r is None else "slots in use at most %d; %d times the player had to wait; finishes at %.0fs (1x)"
                  % (r["max_slots_in_use"], r["waits"], r["finish_seconds_1x"]))
            if label == "classic" and r:
                check("%s: several teams work at the same time when slots allow" % key, r["max_slots_in_use"] >= 2,
                      "up to %d slots busy at once" % r["max_slots_in_use"])
                m["timed_classic"] = {k: v for k, v in r.items() if k != "schedule_problems"}
        # undo round trip + invariants under random play
        rng = random.Random(99)
        undo_ok = True
        inv_ok = True
        replay_ok = True
        random_wins = 0
        for trial in range(6):
            gg = Game(board, tunnels, lv["classic"])
            init_hash = gg.state_hash()
            hashes = [init_hash]
            steps = 0
            while not gg.won() and steps < 1200:
                steps += 1

                def push():
                    hashes.append(gg.state_hash())
                    return invariant_quota(gg, board)

                if gg.deadlocked():
                    roll = rng.random()
                    if roll < 0.25:
                        gg.add_chamber(); inv_ok &= push()
                    elif roll < 0.55:
                        gg.recall(rng.randrange(len(gg.state.chambers))); inv_ok &= push()
                    else:
                        gg.undo(); hashes.pop()
                        if gg.state_hash() != hashes[-1]:
                            undo_ok = False
                    continue
                fronts = [q for q in range(len(tunnels)) if gg.can_dispatch(q)]
                if not fronts:
                    # no open slot, but not deadlocked: only possible when the board is done
                    break
                roll = rng.random()
                if gg.state.chambers and roll > 0.94:
                    gg.recall(rng.randrange(len(gg.state.chambers))); inv_ok &= push()
                    continue
                if gg.moves and 0.25 <= roll < 0.33:
                    gg.undo(); hashes.pop()
                    if gg.state_hash() != hashes[-1]:
                        undo_ok = False
                    continue
                gg.dispatch(rng.choice(fronts)); inv_ok &= push()
            if gg.won():
                random_wins += 1
            # save/replay
            moves = list(gg.moves)
            rp = Game(board, tunnels, lv["classic"])
            for mv in moves:
                rp.apply_move(mv)
            if rp.state_hash() != gg.state_hash() or claims_hash(rp.move_claims) != claims_hash(gg.move_claims):
                replay_ok = False
            while gg.moves:
                gg.undo()
            if gg.state_hash() != init_hash:
                undo_ok = False
        check("%s: undo restores the exact previous state (random play with sends, returns and added slots, 6 games)" % key, undo_ok)
        check("%s: tiles left per colour always equal quota owed (random play)" % key, inv_ok)
        check("%s: a careless random player who uses the recovery options (add slot, return team, undo) still finishes" % key, random_wins == 6,
              "%d of 6 random games completed" % random_wins)
        check("%s: saved move list replays to an identical state and identical ant claims" % key, replay_ok)
        # hints: following hints from the start wins; deviating then asking yields undo advice or a move
        hg = Game(board, tunnels, lv["classic"])
        n = 0
        while not hg.won() and n < 300:
            h = hint_full(hg, sol)
            if h[0] != "move":
                break
            hg.apply_move(h[1]); n += 1
        check("%s: following hints from a fresh start wins" % key, hg.won(), "%d moves" % n)
        # an old save with a team parked by Hold (removed feature): following hints still wins
        hg = Game(board, tunnels, lv["classic"])
        hg.dispatch(sol[0])
        hq = next(q for q in range(len(tunnels)) if hg.can_hold(q))
        hg.apply_move(HOLD_BASE + hq)
        n = 0; kinds = set()
        while not hg.won() and n < 400:
            h = hint_full(hg, sol)
            kinds.add(h[0] if h[0] != "move" or h[1] < RELEASE_BASE else "release")
            if h[0] == "move":
                hg.apply_move(h[1])
            elif h[0] == "undo":
                for _ in range(h[1]):
                    hg.undo()
            else:
                break
            n += 1
        check("%s: old save with a parked team: following hints still wins" % key, hg.won(), "hint kinds used: %s" % sorted(kinds))
        # deliberate mistakes
        dg = Game(board, tunnels, lv["expert"])
        rng = random.Random(3)
        for _ in range(4):
            fronts = [q for q in range(len(tunnels)) if dg.can_dispatch(q)]
            if not fronts:
                break
            dg.dispatch(rng.choice(fronts))
        h = hint_full(dg, sol)
        check("%s: after off-plan moves the hint gives a move or an undo count" % key, h[0] in ("move", "undo"), str(h))
        # performance proxy: claim-run work per dispatch
        m["teams"] = sum(len(t) for t in tunnels)
        m["tiles"] = board.tile_count
        metrics[key] = m
    design_tests(rep, metrics)
    challenge_tests(rep, swift_src, metrics)
    collection_tests(rep, metrics)
    score_and_option_tests(rep, swift_src, open(os.path.join(os.path.dirname(os.path.abspath(sys.argv[2])), "Level.swift")).read(), metrics)
    path_style_tests(rep, metrics)
    versus_tests(rep, metrics)
    photo_tests(metrics)
    pattern_tests(metrics)
    sound_tests(rep, metrics)
    session_tests(rep, metrics)
    json.dump({"results": RESULTS, "metrics": metrics, "seconds": round(time.time() - t0, 1)}, open(out, "w"), indent=1)
    print("metrics", json.dumps(metrics, indent=1))
    failed = [r for r in RESULTS if not r["passed"]]
    print("%d checks, %d failed" % (len(RESULTS), len(failed)))


if __name__ == "__main__":
    main()
