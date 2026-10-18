"""Golden fixtures for the JS core tests, generated with the Python reference models in ../../Tools.

Usage: python3 make_fixtures.py            (from Web/tools; writes ../test/fixtures/*.json)

versus.json  — scripted two-player matches played by Tools/versus.py (every combination of options on
               First Dig and Nesting Rings, careless and greedy players, random adds and returns). Each
               step records the acting player, the action, the legality of every (tunnel, depth) probe,
               a hash of the claims (team, family, tile, full path) and a hash of the match state, so
               test/versus.test.js can replay the same actions on src/core/versus.js and compare.
scoring.json — Tools/scoring.py: solo score breakdowns for a grid of cases, the 40-insert high-score
               sequence of tests.py, and the No colour twice rule (legal tunnels at every step of
               First Dig's designed line and of careless walks, plus a winning line found by the
               reference search).
"""
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.normpath(os.path.join(HERE, "..", "..", "Tools"))
sys.path.insert(0, TOOLS)

import versus as V          # noqa: E402
import scoring              # noqa: E402
from engine import Board, Game   # noqa: E402

DATA = json.load(open(os.path.join(HERE, "..", "data", "levels.json")))
OUT = os.path.join(HERE, "..", "test", "fixtures")

M32 = 0xFFFFFFFF
SEED32 = 2166136261


def mix(h, v):
    return ((h ^ (v & M32)) * 16777619) & M32


def claims_hash(claims):
    h = SEED32
    for c in claims:
        h = mix(h, c.team)
        h = mix(h, c.family)
        h = mix(h, c.tile)
        h = mix(h, len(c.path))
        for x in c.path:
            h = mix(h, x)
    return h


def state_hash(m):
    h = SEED32
    for b in m.boards:
        for t in b.chambers:
            h = mix(h, t.uid)
            h = mix(h, t.remaining)
        h = mix(h, len(b.chambers))
        for f in range(6):
            h = mix(h, b.left[f])
        h = mix(h, b.claimed[0])
        h = mix(h, b.claimed[1])
    for pl in m.players:
        for queue in pl.queues:
            h = mix(h, len(queue))
            for t in queue:
                h = mix(h, t.uid)
                h = mix(h, t.remaining)
        for v in (pl.capacity, pl.added, pl.returns, pl.skips, pl.launches,
                  0 if pl.last_family is None else pl.last_family + 1):
            h = mix(h, v)
    return h


def cells_hash(m):
    h = SEED32
    for b in m.boards:
        for i in range(b.board.N):
            h = mix(h, b.owner[i] + 1)
            h = mix(h, b.opn[i])
    return h


REASON = {"no team there": "n", "out of reach": "r", "every slot holds a waiting team": "s",
          "same colour as your last launch": "c"}


def probes(m, p):
    """Legality of every (tunnel, depth) for depth 0 .. min(3, len(queue)) — one letter each,
    tunnels separated by '|': o = allowed, n / r / s / c = refused (no team / reach / slots / colour)."""
    out = []
    for q, queue in enumerate(m.players[p].queues):
        s = ""
        for d in range(min(3, len(queue)) + 1):
            ok, why = m.check(p, q, d)
            s += "o" if ok else REASON[why]
        out.append(s)
    return "|".join(out)


def level(key):
    lv = DATA["levels"][key]
    return lv, [[tuple(t) for t in q] for q in lv["tunnels"]]


def play_match(key, layout, picking, colour, scoring_rule, difficulty, seed, greedy, keep_first=False):
    lv, tunnels = level(key)
    cap = lv["chambers" + difficulty.capitalize()]
    m = V.VMatch(lv["art"], tunnels, cap, layout, picking, colour, scoring_rule)
    rng = random.Random(seed)
    steps = []
    first_claims = None
    n = 0
    while not m.over() and n < 5000:
        n += 1
        p = rng.randrange(2)
        pr = probes(m, p)
        opts = [(q, d, t) for q, d, t in m.candidates(p) if m.check(p, q, d)[0]]
        if opts:
            q, d, _ = (min(opts, key=lambda o: (o[1], -o[2].quota)) if greedy else rng.choice(opts))
            ev = m.launch(p, q, d)
            if keep_first and first_claims is None:
                first_claims = [[c.team, c.family, c.tile, list(c.path)] for c in ev]
            step = [p, "launch", q, d, pr, len(ev), claims_hash(ev)]
        else:
            w = m.waiting(p)
            if w and len(w) >= m.players[p].capacity:
                if rng.random() < 0.7:
                    m.add_slot(p)
                    step = [p, "add", pr]
                else:
                    uid = rng.choice(w).uid
                    m.return_team(p, uid)
                    step = [p, "return", uid, pr]
            else:
                step = [p, "none", pr]
        # scripted slot upkeep: a 0.1 s tick with the waiting teams as the busy slots
        for pp in (0, 1):
            m.players[pp].upkeep += V.UPKEEP_PER_SECOND * max(0, len(m.waiting(pp)) - 1) * 0.1
        step.append(state_hash(m))
        steps.append(step)
    rec = {
        "level": key,
        "rules": {"layout": layout, "picking": picking, "colour": colour, "scoring": scoring_rule,
                  "difficulty": difficulty},
        "capacity": cap, "seed": seed, "greedy": greedy, "steps": steps,
        "final": {
            "over": m.over(),
            "tiles": [m.tiles(0), m.tiles(1)],
            "penalties": [m.penalties(0), m.penalties(1)],
            "upkeep": [m.players[0].upkeep, m.players[1].upkeep],
            "scores": m.final_scores(),
            "tileCount": m.tile_count,
            "left": [b.left[:6] for b in m.boards],
            "done": [b.done() for b in m.boards],
            "cellsHash": cells_hash(m),
            "stateHash": state_hash(m),
        },
    }
    if first_claims is not None:
        rec["firstClaims"] = first_claims
    return rec


def versus_fixture():
    matches = []
    combos = [(l, pk, c, s) for l in V.LAYOUTS for pk in V.PICKING for c in V.COLOUR for s in V.SCORING]
    diffs = ["classic", "gentle", "expert"]
    for i, (layout, picking, colour, sc) in enumerate(combos):
        matches.append(play_match("firstDig", layout, picking, colour, sc, diffs[i % 3], 1 + i, False, keep_first=(i == 0)))
        matches.append(play_match("firstDig", layout, picking, colour, sc, "classic", 100 + i, True))
        matches.append(play_match("nestingRings", layout, picking, colour, sc, "classic", 200 + i, False))
    return {"generator": "Web/tools/make_fixtures.py (Tools/versus.py)", "hash": "FNV-1a 32 (see make_fixtures.py)",
            "matches": matches}


# ---------------------------------------------------------------------------
# scoring
# ---------------------------------------------------------------------------

def scoring_fixture():
    mods_all = list(scoring.MODIFIER_BONUS)
    rng = random.Random(7)
    cases = []
    for _ in range(300):
        tiles = rng.randrange(0, 7000)
        d = rng.choice(["gentle", "classic", "expert"])
        mods = [m for m in mods_all if rng.random() < 0.4]
        u, h, a = rng.randrange(0, 40), rng.randrange(0, 8), rng.randrange(0, 8)
        r = scoring.solo_score(tiles, d, mods, u, h, a)
        cases.append({"tiles": tiles, "difficulty": d, "modifiers": mods, "undos": u, "hints": h, "assists": a,
                      "base": r["base"], "undo": r["undo"], "hint": r["hint"], "assist": r["assist"],
                      "score": r["score"], "mf": r["mf"], "df": r["df"]})
    # tests.py: 40 random results into an empty table
    t = []
    rng = random.Random(4)
    inserts = []
    for i in range(40):
        e = (rng.randrange(0, 3000), round(rng.uniform(30, 900), 1), i)
        r = scoring.rank(t, e[0], e[1])
        t, place = scoring.insert(t, e)
        inserts.append({"score": e[0], "seconds": e[1], "date": e[2], "rank": r, "place": place})
    final_table = [[x[0], x[1], x[2]] for x in t]

    # No colour twice
    colour = []
    for key, walks in (("firstDig", 3), ("koiPond", 2), ("nestingRings", 2)):
        lv, tunnels = level(key)
        board = Board(lv["art"])
        cap = lv["chambersExpert"]
        rec = {"level": key, "capacity": cap}
        # along the designed line
        g = Game(board, tunnels, cap, spare_allowed=False)
        st = g.state
        last = None
        legal = []
        for q in lv["solution"]:
            legal.append(scoring.colour_rule_legal(g, st, last))
            last = g.front(st, q)[0]
            g.apply_dispatch(st, q)
        rec["solutionLegal"] = legal
        # careless walks that obey the rule (stop when nothing is legal or the board is cleared)
        rec["walks"] = []
        for w in range(walks):
            rng = random.Random(50 + w)
            g = Game(board, tunnels, lv["chambersClassic"], spare_allowed=False)
            st = g.state
            last = None
            steps = []
            while st.cleared < board.tile_count and len(steps) < 400:
                ok = scoring.colour_rule_legal(g, st, last)
                if not ok:
                    steps.append([ok, None])
                    break
                q = rng.choice(ok)
                steps.append([ok, q])
                last = g.front(st, q)[0]
                g.apply_dispatch(st, q)
            rec["walks"].append({"capacity": lv["chambersClassic"], "steps": steps,
                                 "cleared": st.cleared, "jammed": st.jammed is not None})
        line, nodes = scoring.solve_colour_rule(board, tunnels, cap, budget=200000)
        rec["line"] = line
        rec["lineChecks"] = line is not None and scoring.check_line(board, tunnels, cap, line)
        colour.append(rec)
    return {"generator": "Web/tools/make_fixtures.py (Tools/scoring.py)",
            "solo": cases, "inserts": inserts, "finalTable": final_table, "colourRule": colour}


def main():
    os.makedirs(OUT, exist_ok=True)
    v = versus_fixture()
    with open(os.path.join(OUT, "versus.json"), "w") as f:
        json.dump(v, f, separators=(",", ":"))
    s = scoring_fixture()
    with open(os.path.join(OUT, "scoring.json"), "w") as f:
        json.dump(s, f, separators=(",", ":"))
    steps = sum(len(m["steps"]) for m in v["matches"])
    print("versus: %d matches, %d steps; scoring: %d cases, %d inserts, %d colour-rule levels"
          % (len(v["matches"]), steps, len(s["solo"]), len(s["inserts"]), len(s["colourRule"])))


if __name__ == "__main__":
    main()
