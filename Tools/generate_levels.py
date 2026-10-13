"""Builds the tunnel queues for each level, proves solvability, measures difficulty and
exports Swift level data (LevelData.swift) plus golden checksums for the on-device self-test.

Usage: python3 generate_levels.py <art.json> <out_dir_for_swift> <report.json>
"""
import json
import random
import sys
import time

from engine import Board, Game, Team, State, greedy_choice, claims_hash, SPARE_MOVE
from palette import FAMILIES, GROUT, SOIL, SOIL_DARK

LADDER = [20, 24, 30, 36, 42, 48, 56, 64, 72, 84, 96, 110]
MAX_TEAM = 128


def design_sequence(board: Board, rng: random.Random, max_wait: int, n_tunnels: int,
                    min_team: int, p_wait: float, ladder=None):
    """Simulate a designer playing the level, inventing each team as it goes.
    Returns the ordered list of (family, quota) teams. Every team is created so that the
    designer's own play never needs more than `max_wait` chambers."""
    game = Game(board, [[]], capacity=max_wait)
    st = game.state
    unassigned = board.family_counts()
    seq = []
    last_fam = -1
    guard = 0
    while sum(unassigned) > 0:
        guard += 1
        assert guard < 2000, "designer stuck"
        reach = {}
        for f in range(6):
            if unassigned[f] <= 0:
                continue
            s2 = st.copy()
            reach[f] = len(game.claim_run(s2, f, unassigned[f], -1))
        fitting = [f for f in reach if reach[f] >= min(min_team, unassigned[f])]
        waiting_ok = len(st.chambers) < max_wait
        choice = None
        # Sometimes create a team that will have to wait for its colour to be exposed.
        if waiting_ok and rng.random() < p_wait:
            wait_fams = [f for f in reach if reach[f] < unassigned[f] and unassigned[f] >= min_team
                         and reach[f] + 12 <= MAX_TEAM and all(t.family != f for t in st.chambers)]
            if wait_fams:
                f = rng.choice(wait_fams)
                extra = rng.choice([12, 18, 24, 30, 40])
                q = min(unassigned[f], max(min_team, reach[f] + extra), MAX_TEAM)
                if unassigned[f] - q < min_team and unassigned[f] <= MAX_TEAM:
                    q = unassigned[f]
                choice = (f, q)
        if choice is None:
            if not fitting:
                # nothing reachable in useful amounts: make a waiting team if allowed
                cands = [f for f in reach]
                f = max(cands, key=lambda f: reach[f])
                q = unassigned[f] if unassigned[f] < 2 * min_team else min(MAX_TEAM, max(min_team, reach[f]))
                choice = (f, q)
            else:
                weights = []
                for f in fitting:
                    w = (reach[f] ** 0.6) * (0.35 if f == last_fam else 1.0)
                    weights.append(w)
                f = rng.choices(fitting, weights)[0]
                cap = min(reach[f], unassigned[f])
                options = [x for x in (ladder or LADDER) if x <= cap]
                q = rng.choice(options[-6:]) if options else cap
                q = min(q, cap)
                if unassigned[f] - q < min_team and unassigned[f] <= MAX_TEAM:
                    q = unassigned[f]
                choice = (f, q)
        f, q = choice
        trial = st.copy()
        game.state = trial
        inc = Team(len(seq), f, q, q)
        game.resolve(trial, inc)
        if trial.jammed is not None:
            # fall back to a team that certainly completes right now
            pool = fitting or [x for x in reach if reach[x] > 0]
            if not pool:
                raise RuntimeError("designer jammed with nothing reachable")
            f = max(pool, key=lambda x: reach[x])
            q = min(reach[f], unassigned[f])
            trial = st.copy()
            game.state = trial
            game.resolve(trial, Team(len(seq), f, q, q))
            assert trial.jammed is None
        st = trial
        game.state = st
        seq.append((f, q))
        unassigned[f] -= q
        last_fam = f
    assert st.cleared == board.tile_count, "designer left tiles uncleared"
    assert not st.chambers
    return seq


def deal(seq, n_tunnels, rng):
    """Deal the designer's sequence into tunnels (order inside each tunnel is preserved,
    so the designer's play remains a valid solution)."""
    tunnels = [[] for _ in range(n_tunnels)]
    solution = []
    for f, q in seq:
        lens = [len(t) for t in tunnels]
        lo = min(lens)
        cands = [i for i in range(n_tunnels) if lens[i] <= lo + 2]
        i = rng.choice(cands)
        tunnels[i].append((f, q))
        solution.append(i)
    return tunnels, solution


def replay(board, tunnels, solution, capacity):
    g = Game(board, tunnels, capacity)
    per_move = []
    max_ch = 0
    for q in solution:
        ev = g.dispatch(q)
        assert g.state.jammed is None, "solution jammed"
        per_move.append(len(ev))
        max_ch = max(max_ch, len(g.state.chambers))
    assert g.won(), "solution does not clear the board"
    return g, per_move, max_ch


def policy_win_rate(board, tunnels, capacity, policy, trials, seed):
    """Win rate of a patient player (waits for working teams to finish) under the slot rule."""
    rng = random.Random(seed)
    wins = 0
    for _ in range(trials):
        g = Game(board, tunnels, capacity, spare_allowed=False)
        st = g.state
        while st.jammed is None and st.cleared < board.tile_count:
            if len(st.chambers) >= st.capacity:
                break          # every slot holds a waiting team: deadlock
            fronts = [q for q in range(len(tunnels)) if st.heads[q] < len(tunnels[q])]
            if not fronts:
                break
            if policy == "random":
                q = rng.choice(fronts)
                g.apply_dispatch(st, q)
            else:  # "greedy"
                q, s2 = greedy_choice(g, st)
                if q is None:
                    break
                st = s2
                g.state = st
        if st.jammed is None and st.cleared == board.tile_count:
            wins += 1
        if policy == "greedy":
            break
    return wins / (1 if policy == "greedy" else trials)


def build_level(key, rows, seed, n_tunnels, max_wait, min_team, p_wait, attempts=12):
    board = Board(rows)
    best = None
    for a in range(attempts):
        rng = random.Random(seed + a * 7919)
        try:
            seq = design_sequence(board, rng, max_wait, n_tunnels, min_team, p_wait)
        except (AssertionError, RuntimeError) as e:
            print("  attempt", a, "failed:", e)
            continue
        tunnels, solution = deal(seq, n_tunnels, rng)
        g, per_move, max_ch = replay(board, tunnels, solution, capacity=max_wait + 1)
        greedy = {cap: policy_win_rate(board, tunnels, cap, "greedy", 1, 0) for cap in range(max_wait, max_wait + 4)}
        # prefer levels the greedy one-step player cannot finish with very few chambers
        min_greedy = min([c for c, w in greedy.items() if w > 0] or [99])
        score = (min_greedy, len(seq))
        print("  attempt", a, "teams", len(seq), "max chambers in solution", max_ch, "greedy needs", min_greedy)
        if best is None or score > best[0]:
            best = (score, seq, tunnels, solution, per_move, max_ch, greedy)
        if min_greedy >= max_wait + 2:
            break
    score, seq, tunnels, solution, per_move, max_ch, greedy = best
    return board, tunnels, solution, per_move, max_ch, greedy


CHALLENGE_LADDER = [16, 20, 24, 28, 32, 36, 40]


def tunnels_from(assign, seq, n_tunnels):
    tunnels = [[] for _ in range(n_tunnels)]
    for i, t in enumerate(assign):
        tunnels[t].append(seq[i])
    return tunnels


def master_score(board, tunnels, caps, trials):
    """Master pack: like challenge_score, but the one-step player should fail even on Gentle and
    careless play should rarely win anywhere."""
    gg = policy_win_rate(board, tunnels, caps["gentle"], "greedy", 1, 0)
    gc = policy_win_rate(board, tunnels, caps["classic"], "greedy", 1, 0)
    ge = policy_win_rate(board, tunnels, caps["expert"], "greedy", 1, 0)
    rg = policy_win_rate(board, tunnels, caps["gentle"], "random", trials, 16)
    rc = policy_win_rate(board, tunnels, caps["classic"], "random", trials, 17)
    re_ = policy_win_rate(board, tunnels, caps["expert"], "random", trials, 18)
    score = 2 * gc + ge + gg + rc + 0.5 * re_ + 0.5 * rg
    return score, dict(greedy_gentle=gg, greedy_classic=gc, greedy_expert=ge, random_gentle=rg,
                       random_classic=rc, random_expert=re_)


def challenge_score(board, tunnels, caps, trials):
    """Lower = harder. A sensible one-step player (always sends a team that can finish, the one
    that claims most) must still win on Gentle, but should fail on Classic and Expert; careless
    tapping should almost never win on Classic."""
    gg = policy_win_rate(board, tunnels, caps["gentle"], "greedy", 1, 0)
    gc = policy_win_rate(board, tunnels, caps["classic"], "greedy", 1, 0)
    ge = policy_win_rate(board, tunnels, caps["expert"], "greedy", 1, 0)
    rc = policy_win_rate(board, tunnels, caps["classic"], "random", trials, 17)
    re_ = policy_win_rate(board, tunnels, caps["expert"], "random", trials, 18)
    score = 2 * gc + ge + rc + 0.5 * re_ + 3 * (1 - gg)
    return score, dict(greedy_gentle=gg, greedy_classic=gc, greedy_expert=ge, random_classic=rc, random_expert=re_)


def build_challenge(key, rows, seed, n_tunnels, designs=4, iters=60, trials=16, ladder=None,
                    options=((2, 0.4), (3, 0.45)), scorer=None, min_team=12, trail=None):
    """Challenge levels: the designer invents a sequence with smaller teams and more waiting, then a
    local search re-deals the teams across tunnels (the designer's order inside each tunnel is kept,
    so the designed play is still a winning line) to make careless and one-step play fail.

    If `trail` is a list, every deal the search accepts is appended to it as
    (score, details, design, seq, assign, max_ch); this does not change the search itself."""
    board = Board(rows)
    best = None
    for d in range(designs):
        rng = random.Random(seed + d * 7919)
        mw, pw = options[d % len(options)]
        try:
            seq = design_sequence(board, rng, mw, n_tunnels, min_team, pw, ladder=ladder or CHALLENGE_LADDER)
        except (AssertionError, RuntimeError) as e:
            print("  design", d, "failed:", e)
            continue
        assign = [i % n_tunnels for i in range(len(seq))]
        rng.shuffle(assign)
        tunnels = tunnels_from(assign, seq, n_tunnels)
        _, _, max_ch = replay(board, tunnels, assign, mw + 1)
        caps = dict(expert=max_ch + 1, classic=max_ch + 2, gentle=max_ch + 4)
        score_fn = scorer or challenge_score
        cur, det = score_fn(board, tunnels, caps, trials)
        if trail is not None:
            trail.append((cur, det, d, seq, list(assign), max_ch))
        for it in range(iters):
            a2 = list(assign)
            if rng.random() < 0.3:
                i = rng.randrange(len(a2))
                j = min(len(a2), i + rng.randint(2, 6))
                t = rng.randrange(n_tunnels)
                for k in range(i, j):
                    a2[k] = t
            else:
                i = rng.randrange(len(a2))
                a2[i] = (a2[i] + rng.randint(1, n_tunnels - 1)) % n_tunnels
            lens = [a2.count(t) for t in range(n_tunnels)]
            if max(lens) - min(lens) > 8:
                continue
            sc, d2 = score_fn(board, tunnels_from(a2, seq, n_tunnels), caps, trials)
            if sc <= cur:
                assign, cur, det = a2, sc, d2
                if trail is not None:
                    trail.append((cur, det, d, seq, list(assign), max_ch))
        print("  %s design %d: %d teams, solution keeps %d waiting, score %.2f %s" % (key, d, len(seq), max_ch, cur, det))
        if best is None or cur < best[0]:
            best = (cur, det, seq, assign, max_ch)
    cur, det, seq, assign, max_ch = best
    tunnels = tunnels_from(assign, seq, n_tunnels)
    g, per_move, max_ch2 = replay(board, tunnels, assign, max_ch + 1)
    assert max_ch2 == max_ch
    return board, tunnels, list(assign), per_move, max_ch


def planner_win(board, tunnels, capacity):
    """A thinking player: before each tap, plays each front out with the greedy rollout (what the
    in-game hint does off-plan) and picks a winning one, else the one that clears most."""
    from engine import rollout
    g = Game(board, tunnels, capacity, spare_allowed=False)
    st = g.state
    n = 0
    while st.jammed is None and st.cleared < board.tile_count and n < 600:
        best = None
        for q in range(len(tunnels)):
            if st.heads[q] >= len(tunnels[q]) or len(st.chambers) >= st.capacity:
                continue
            s2 = st.copy()
            g.apply_dispatch(s2, q)
            if s2.jammed is not None:
                continue
            won, cleared = rollout(g, s2)
            key_ = (won, cleared, -q)
            if best is None or key_ > best[0]:
                best = (key_, q)
        if best is None:
            break
        g.apply_dispatch(st, best[1])
        n += 1
    return st.jammed is None and st.cleared == board.tile_count


# The Master bar (also checked by tests.py): the one-step player fails on Classic and Expert, careless
# tapping wins at most 20% of games on Classic and 10% on Expert, and the look-ahead player still wins
# on at least two of the three difficulties.
MASTER_BAR = dict(careless_classic=0.20, careless_expert=0.10, lookahead_min=2)


def build_master_to_bar(key, rows, seed, n_tunnels=3, designs=4, iters=50, trials=12):
    """Master build for pictures where the plain search overshoots or undershoots.

    The re-dealing search only knows the one-step and careless players, so on some pictures it keeps
    going until even a thinking player loses (Viaduct), or its best-scoring deal still lets careless
    play win (City at Dusk). Here every deal the search accepted, in every design, is kept, and they
    are checked from hardest to easiest against MASTER_BAR with the same measurements the report and
    tests use; the hardest deal that passes is used. Returns build_challenge's tuple plus a note."""
    board = Board(rows)
    trail = []
    build_challenge(key, rows, seed, n_tunnels, designs=designs, iters=iters, trials=trials,
                    ladder=MASTER_LADDER, options=((3, 0.5), (2, 0.45)), scorer=master_score,
                    min_team=10, trail=trail)
    seen, cands = set(), []
    for i, (sc, det, d, seq, assign, max_ch) in enumerate(trail):
        k = (d, tuple(assign))
        if k not in seen:
            seen.add(k)
            cands.append((sc, -i, d, seq, assign, max_ch))
    cands.sort(key=lambda c: (c[0], c[1]))
    best_miss = None
    for n, (sc, _, d, seq, assign, max_ch) in enumerate(cands):
        tunnels = tunnels_from(assign, seq, n_tunnels)
        expert, classic, gentle = max_ch + 1, max_ch + 2, max_ch + 4
        if policy_win_rate(board, tunnels, classic, "greedy", 1, 0) or policy_win_rate(board, tunnels, expert, "greedy", 1, 0):
            continue
        cc = policy_win_rate(board, tunnels, classic, "random", 40, 5)
        ce = policy_win_rate(board, tunnels, expert, "random", 40, 5)
        look = sum(planner_win(board, tunnels, c) for c in (gentle, classic, expert))
        ok = (cc <= MASTER_BAR["careless_classic"] and ce <= MASTER_BAR["careless_expert"]
              and look >= MASTER_BAR["lookahead_min"])
        if ok:
            chosen, note = (seq, assign, max_ch), "met the Master bar (candidate %d of %d, design %d, score %.2f)" % (n + 1, len(cands), d, sc)
            break
        miss = (look >= MASTER_BAR["lookahead_min"], -max(0, cc - MASTER_BAR["careless_classic"]), look, -cc, -sc)
        if best_miss is None or miss > best_miss[0]:
            best_miss = (miss, (seq, assign, max_ch), cc, ce, look)
    else:
        if best_miss is None:
            raise RuntimeError("no deal of %s makes the one-step player fail" % key)
        _, chosen, cc, ce, look = best_miss
        note = "no deal met the Master bar; closest used (careless classic %.2f, expert %.2f, look-ahead %d/3)" % (cc, ce, look)
    print("  %s: %s" % (key, note), flush=True)
    seq, assign, max_ch = chosen
    tunnels = tunnels_from(assign, seq, n_tunnels)
    g, per_move, max_ch2 = replay(board, tunnels, assign, max_ch + 1)
    assert max_ch2 == max_ch
    return board, tunnels, list(assign), per_move, max_ch, note


# The Challenge bar (also checked by tests.py): the one-step player wins on Gentle but fails on Classic
# and Expert, careless tapping wins at most 40% on Classic and 20% on Expert, and the look-ahead player
# wins on Classic and Expert.
CHALLENGE_BAR = dict(careless_classic=0.40, careless_expert=0.20)


def build_challenge_to_bar(key, rows, seed, n_tunnels=3):
    """Challenge-tier build for the collection packs: the Challenge search, with every accepted deal
    checked (hardest first) against CHALLENGE_BAR; the hardest deal that passes is used, else the one
    closest to it, else the plain search result. Returns build_challenge's tuple plus a note."""
    board = Board(rows)
    trail = []
    plain = build_challenge(key, rows, seed, n_tunnels, trail=trail)
    seen, cands = set(), []
    for i, (sc, det, d, seq, assign, max_ch) in enumerate(trail):
        k = (d, tuple(assign))
        if k not in seen:
            seen.add(k)
            cands.append((sc, -i, d, seq, assign, max_ch))
    cands.sort(key=lambda c: (c[0], c[1]))
    best_miss, chosen = None, None
    for n, (sc, _, d, seq, assign, max_ch) in enumerate(cands):
        tunnels = tunnels_from(assign, seq, n_tunnels)
        expert, classic, gentle = max_ch + 1, max_ch + 2, max_ch + 4
        if (not policy_win_rate(board, tunnels, gentle, "greedy", 1, 0)
                or policy_win_rate(board, tunnels, classic, "greedy", 1, 0)
                or policy_win_rate(board, tunnels, expert, "greedy", 1, 0)):
            continue
        cc = policy_win_rate(board, tunnels, classic, "random", 40, 5)
        ce = policy_win_rate(board, tunnels, expert, "random", 40, 5)
        look = sum(planner_win(board, tunnels, c) for c in (classic, expert))
        if cc <= CHALLENGE_BAR["careless_classic"] and ce <= CHALLENGE_BAR["careless_expert"] and look == 2:
            chosen = (seq, assign, max_ch)
            note = "met the Challenge bar (candidate %d of %d, design %d, score %.2f)" % (n + 1, len(cands), d, sc)
            break
        miss = (look == 2, -max(0, cc - CHALLENGE_BAR["careless_classic"]) - max(0, ce - CHALLENGE_BAR["careless_expert"]),
                look, -cc, -sc)
        if best_miss is None or miss > best_miss[0]:
            best_miss = (miss, (seq, assign, max_ch), cc, ce, look)
    if chosen is None and best_miss is not None:
        _, chosen, cc, ce, look = best_miss
        note = "no deal met the Challenge bar; closest used (careless classic %.2f, expert %.2f, look-ahead %d/2)" % (cc, ce, look)
    if chosen is None:
        board, tunnels, assign, per_move, max_ch = plain
        note = "no deal passed the one-step test; the plain search result is used"
        print("  %s: %s" % (key, note), flush=True)
        return board, tunnels, assign, per_move, max_ch, note
    print("  %s: %s" % (key, note), flush=True)
    seq, assign, max_ch = chosen
    tunnels = tunnels_from(assign, seq, n_tunnels)
    g, per_move, max_ch2 = replay(board, tunnels, assign, max_ch + 1)
    assert max_ch2 == max_ch
    return board, tunnels, list(assign), per_move, max_ch, note


def rating(random_rate, greedy_won):
    """1 Relaxed ... 5 Fiendish (mirrors LevelRating in Level.swift)."""
    if greedy_won and random_rate >= 0.75:
        return 1
    if greedy_won and random_rate >= 0.35:
        return 2
    if greedy_won:
        return 3
    if random_rate > 0.10:
        return 4
    return 5


def swift_escape_rows(rows):
    return ",\n".join('        "%s"' % r for r in rows)


def export_swift(levels, out_path):
    L = []
    L.append("// GENERATED by Tools/generate_levels.py - do not edit by hand.")
    L.append("// Mosaic art, tunnel queues, palette and golden self-test values.")
    L.append("")
    L.append("import Foundation")
    L.append("")
    L.append("enum GeneratedPalette {")
    L.append("    static let familyNames: [String] = [%s]" % ", ".join('"%s"' % f[0] for f in FAMILIES))
    L.append("    /// 6 families x 4 tones, 0xRRGGBB, light -> deep")
    L.append("    static let tones: [[UInt32]] = [")
    for f in FAMILIES:
        L.append("        [%s]," % ", ".join("0x" + t.lstrip('#').upper() for t in f[2]))
    L.append("    ]")
    L.append("    static let grout: UInt32 = 0x%s" % GROUT.lstrip('#').upper())
    L.append("    static let soil: UInt32 = 0x%s" % SOIL.lstrip('#').upper())
    L.append("    static let soilDark: UInt32 = 0x%s" % SOIL_DARK.lstrip('#').upper())
    L.append("    static let builtIn = LevelPalette(names: familyNames, tones: tones)")
    L.append("}")
    L.append("")
    L.append("enum GeneratedLevels {")
    for lv in levels:
        L.append("    static let %s = LevelDefinition(" % lv["key"])
        L.append('        id: "%s",' % lv["key"])
        L.append('        title: "%s",' % lv["title"])
        L.append('        subtitle: "%s",' % lv["subtitle"])
        L.append("        art: [")
        L.append(swift_escape_rows(lv["rows"]))
        L.append("        ],")
        L.append("        palette: GeneratedPalette.builtIn,")
        L.append("        tunnels: [")
        for t in lv["tunnels"]:
            L.append("            [%s]," % ", ".join("TeamSpec(%d, %d)" % (f, q) for f, q in t))
        L.append("        ],")
        L.append("        chambersGentle: %d," % lv["gentle"])
        L.append("        chambersClassic: %d," % lv["classic"])
        L.append("        chambersExpert: %d," % lv["expert"])
        L.append("        solution: [%s]," % ", ".join(str(x) for x in lv["solution"]))
        L.append("        goldenClaimsPerMove: [%s]," % ", ".join(str(x) for x in lv["per_move"]))
        L.append("        goldenClaimsHash: 0x%016X," % lv["claims_hash"])
        L.append("        goldenFinalStateHash: 0x%016X," % lv["final_hash"])
        L.append("        carelessWins: [%s]," % ", ".join("%.3f" % x for x in lv["careless"]))
        extra = []
        if lv.get("challenge"):
            extra.append("isChallenge: true")
        if lv.get("pack", "main") != "main":
            extra.append('pack: "%s"' % lv["pack"])
        L.append("        greedyWins: [%s]%s" % (", ".join("true" if x else "false" for x in lv["greedy"]),
                                                   "," if extra else ""))
        for k, e in enumerate(extra):
            L.append("        " + e + ("," if k < len(extra) - 1 else ""))
        L.append("    )")
    L.append("}")
    open(out_path, "w").write("\n".join(L) + "\n")
    split_swift(out_path)


# LevelData is split over a few files so no single Swift file gets too large for Swift Playground to
# compile comfortably: the collection packs go into `extension GeneratedLevels` files next to it.
SWIFT_SPLIT = [
    ("LevelDataCollection.swift", ("wild", "gallery", "worldart", "ancient", "voyages", "modern", "cosmos"),
     "The collection packs: Wild Wonders, Gallery, World Art, Ancient World, Voyages, Modern Moments, Sky & Science."),
    ("LevelDataLiterature.swift", ("epics", "tales", "childrens", "stage", "adventure", "gothic", "novels"),
     "The Literature packs: Epics & Legends, Fairy Tales & Fables, Children's Classics, Shakespeare, Adventure Classics, Gothic & Mystery, Great Novels."),
    ("LevelDataDiscovery.swift", ("naturalist", "crafts", "geometry", "space", "inventions"),
     "Natural History, World Craft, Geometry & Illusions, Probes & Telescopes, Inventions & Firsts."),
    ("LevelDataSeasons.swift", ("halloween", "winter"),
     "The seasonal packs: Halloween and Winter."),
]


def split_swift(out_path):
    """Moves the level definitions of the packs in SWIFT_SPLIT out of `out_path` into extension files in
    the same folder (removing any such file that would be empty)."""
    import os
    import re
    src = open(out_path).read()
    folder = os.path.dirname(os.path.abspath(out_path))
    for fname, packs, doc in SWIFT_SPLIT:
        blocks = []
        for m in list(re.finditer(r"    static let \w+ = LevelDefinition\(\n.*?\n    \)\n", src, re.S)):
            b = m.group(0)
            if any(('pack: "%s"' % p) in b for p in packs):
                blocks.append(b)
        for b in blocks:
            src = src.replace(b, "", 1)
        path = os.path.join(folder, fname)
        if blocks:
            head = ["// GENERATED by Tools/generate_levels.py - do not edit by hand.", "// " + doc, "",
                    "import Foundation", "", "extension GeneratedLevels {"]
            open(path, "w").write("\n".join(head) + "\n" + "".join(blocks) + "}\n")
        elif os.path.exists(path):
            os.remove(path)
    open(out_path, "w").write(src)


def read_swift_levels(out_path):
    """The generated Swift level data: LevelData.swift plus its split-off extension files."""
    import glob
    import os
    folder = os.path.dirname(os.path.abspath(out_path))
    return "\n".join(open(p).read() for p in sorted(glob.glob(os.path.join(folder, "LevelData*.swift"))))


MAIN_SPECS = [
    # key, title, subtitle, seed, tunnels, max_wait(solution), min_team, p_wait, art key
    ("firstDig", "First Dig", "A ladybird on a leaf", 11, 2, 1, 20, 0.18, "tutorial"),
    ("koiPond", "Koi Pond", "Three koi among lily pads", 77, 3, 1, 20, 0.2, "koi"),
    ("peacockFan", "Peacock Fan", "A tail of eye-spots", 303, 3, 2, 20, 0.2, "peacock"),
    ("nightMarket", "Night Market", "Lanterns, awnings and a crescent moon", 909, 3, 2, 24, 0.2, "market"),
    ("sunflower", "Sunflower & Monarch", "The showcase mosaic", 2026, 3, 2, 24, 0.2, "showcase"),
]
CHALLENGE_SPECS = [
    # key, title, subtitle, seed, tunnels, art key
    ("nestingRings", "Nesting Rings", "Challenge · rings within rings, cut by four spokes", 4101, 3, "rings"),
    ("basketWeave", "Basket Weave", "Challenge · strips that pass over and under", 4202, 3, "weave"),
    ("labyrinth", "Labyrinth", "Challenge · the deeper rooms need the outer ones cleared", 4303, 3, "maze"),
    ("roseWindow", "Rose Window", "Challenge · stained glass held by its leading", 4404, 3, "rose"),
]
MASTER_LADDER = [12, 16, 20, 24, 28, 32]


def finish_level(key, title, sub, rows, board, tunnels, solution, max_ch, t0, pack, extra_report=None,
                 greedy_caps=None, tier=None):
    expert, classic, gentle = max_ch + 1, max_ch + 2, max_ch + 4
    g, pm, _ = replay(board, tunnels, solution, capacity=expert)
    ch = claims_hash(g.move_claims)
    fh = g.state_hash()
    careless = [policy_win_rate(board, tunnels, c, "random", 40, 5) for c in (gentle, classic, expert)]
    greedy_by = [policy_win_rate(board, tunnels, c, "greedy", 1, 0) > 0 for c in (gentle, classic, expert)]
    lv = dict(key=key, title=title, subtitle=sub, rows=rows, tunnels=tunnels, solution=solution,
              per_move=pm, claims_hash=ch, final_hash=fh, gentle=gentle, classic=classic, expert=expert,
              careless=careless, greedy=greedy_by, pack=pack)
    if pack in ("challenge", "master"):
        lv["challenge"] = True
    if tier:
        lv["tier"] = tier
    rep = dict(tiles=board.tile_count, grid=[board.W, board.H], board=[board.C, board.R],
               families=board.family_counts(), teams=sum(len(t) for t in tunnels),
               tunnel_lengths=[len(t) for t in tunnels], solution_moves=len(solution),
               max_chambers_in_solution=max_ch, chambers_expert=expert, chambers_classic=classic,
               chambers_gentle=gentle, pack=pack,
               careless_win_gentle_classic_expert=careless,
               one_step_player_wins_gentle_classic_expert=greedy_by,
               rating_gentle_classic_expert=[rating(careless[i], greedy_by[i]) for i in range(3)],
               claims_hash="0x%016X" % ch, final_state_hash="0x%016X" % fh)
    if tier:
        rep["tier"] = tier
    if lv.get("challenge") or tier in ("challenge", "master"):
        rep["lookahead_player_wins_gentle_classic_expert"] = [planner_win(board, tunnels, c) for c in (gentle, classic, expert)]
    if extra_report:
        rep.update(extra_report)
    rep["build_seconds"] = round(time.time() - t0, 1)
    return lv, rep


def job(spec):
    kind = spec[0]
    t0 = time.time()
    if kind == "main":
        _, key, title, sub, seed, nt, mw, mt, pw, rows = spec
        board, tunnels, solution, per_move, max_ch, greedy = build_level(key, rows, seed, nt, mw, mt, pw)
        expert, classic, gentle = max_ch + 1, max_ch + 2, max_ch + 4
        rnd = {cap: policy_win_rate(board, tunnels, cap, "random", 40, 5) for cap in (expert, classic, gentle)}
        lv, rep = finish_level(key, title, sub, rows, board, tunnels, solution, max_ch, t0, "main")
        rep["greedy_wins_by_capacity"] = {str(k): v for k, v in greedy.items()}
        rep["random_win_rate"] = {str(k): v for k, v in rnd.items()}
        return lv, rep
    if kind == "garden":
        _, key, title, sub, seed, rows = spec
        for attempt in range(4):
            try:
                board, tunnels, solution, per_move, max_ch, greedy = build_level(
                    key, rows, seed + attempt * 9973, 3, 2, 20, 0.25)
                break
            except (AssertionError, RuntimeError, TypeError) as e:
                print("  %s attempt %d failed: %s" % (key, attempt, e), flush=True)
        else:
            raise RuntimeError("could not build " + key)
        out = finish_level(key, title, sub, rows, board, tunnels, solution, max_ch, t0, "garden")
        print("done", key, round(time.time() - t0, 1), flush=True)
        return out
    if kind == "challenge":
        _, key, title, sub, seed, nt, rows = spec
        board, tunnels, solution, per_move, max_ch = build_challenge(key, rows, seed, nt)
        return finish_level(key, title, sub, rows, board, tunnels, solution, max_ch, t0, "challenge")
    if kind == "master":
        _, key, title, sub, seed, rows = spec
        for attempt in range(4):
            try:
                board, tunnels, solution, per_move, max_ch = build_challenge(
                    key, rows, seed + attempt * 9973, 3, designs=4, iters=50, trials=12, ladder=MASTER_LADDER,
                    options=((3, 0.5), (2, 0.45)), scorer=master_score, min_team=10)
                break
            except (AssertionError, RuntimeError, TypeError) as e:
                print("  %s attempt %d failed: %s" % (key, attempt, e), flush=True)
        else:
            raise RuntimeError("could not build " + key)
        out = finish_level(key, title, sub, rows, board, tunnels, solution, max_ch, t0, "master")
        print("done", key, round(time.time() - t0, 1), flush=True)
        return out
    if kind == "master_bar":
        _, key, title, sub, seed, rows = spec
        board, tunnels, solution, per_move, max_ch, note = build_master_to_bar(key, rows, seed)
        out = finish_level(key, title, sub, rows, board, tunnels, solution, max_ch, t0, "master",
                           extra_report={"build": "bar-checked: " + note})
        print("done", key, round(time.time() - t0, 1), flush=True)
        return out
    if kind == "pack":
        # a collection level: its tier picks the builder
        _, tier, pack, key, title, sub, seed, rows = spec
        note = None
        if tier == "gentle":
            for attempt in range(4):
                try:
                    board, tunnels, solution, per_move, max_ch, greedy = build_level(
                        key, rows, seed + attempt * 9973, 3, 2, 20, 0.25)
                    break
                except (AssertionError, RuntimeError, TypeError) as e:
                    print("  %s attempt %d failed: %s" % (key, attempt, e), flush=True)
            else:
                raise RuntimeError("could not build " + key)
        elif tier == "challenge":
            board, tunnels, solution, per_move, max_ch, note = build_challenge_to_bar(key, rows, seed)
        elif tier == "master":
            try:
                board, tunnels, solution, per_move, max_ch, note = build_master_to_bar(key, rows, seed)
            except RuntimeError as e:
                board, tunnels, solution, per_move, max_ch = build_challenge(
                    key, rows, seed, 3, designs=4, iters=50, trials=12, ladder=MASTER_LADDER,
                    options=((3, 0.5), (2, 0.45)), scorer=master_score, min_team=10)
                note = "%s; the plain search result is used" % e
        else:
            raise ValueError(tier)
        out = finish_level(key, title, sub, rows, board, tunnels, solution, max_ch, t0, pack,
                           extra_report={"build": note} if note else None, tier=tier)
        print("done", key, round(time.time() - t0, 1), flush=True)
        return out
    raise ValueError(kind)


def main():
    """generate_levels.py ART.json OUT.swift REPORT.json [workers]"""
    from multiprocessing import Pool
    from art_packs import GARDEN, MASTER, art_for, master_kind, collection_jobs
    art = json.load(open(sys.argv[1]))
    out_swift = sys.argv[2]
    report_path = sys.argv[3]
    workers = int(sys.argv[4]) if len(sys.argv) > 4 else 2
    jobs = []
    for key, title, sub, seed, nt, mw, mt, pw, art_key in MAIN_SPECS:
        jobs.append(("main", key, title, sub, seed, nt, mw, mt, pw, art[art_key]))
    for key, title, sub, seed, nt, art_key in CHALLENGE_SPECS:
        jobs.append(("challenge", key, title, sub, seed, nt, art[art_key]))
    for key, title, sub, gen, seed in GARDEN:
        jobs.append(("garden", key, title, sub, seed * 101 + 7, art_for(gen, seed)))
    for key, title, sub, gen, seed in MASTER:
        jobs.append((master_kind(key), key, title, sub, seed * 131 + 11, art_for(gen, seed)))
    jobs += collection_jobs()
    # longest jobs first keeps both workers busy; results are put back in catalogue order
    order = sorted(range(len(jobs)), key=lambda i: {"master": 0, "master_bar": 0, "challenge": 1, "main": 2, "garden": 3}.get(
        jobs[i][0], {"master": 0, "challenge": 1, "gentle": 3}.get(jobs[i][1], 3)))
    with Pool(workers) as pool:
        results = pool.map(job, [jobs[i] for i in order], chunksize=1)
    by_index = {order[k]: results[k] for k in range(len(order))}
    levels, report = [], {}
    for i in range(len(jobs)):
        lv, rep = by_index[i]
        levels.append(lv)
        report[lv["key"]] = rep
        print(lv["key"], json.dumps({k: rep[k] for k in ("tiles", "teams", "rating_gentle_classic_expert",
                                                          "careless_win_gentle_classic_expert",
                                                          "one_step_player_wins_gentle_classic_expert") if k in rep}))
    export_swift(levels, out_swift)
    json.dump({"levels": [{k: v for k, v in lv.items()} for lv in levels], "report": report},
              open(report_path, "w"), indent=1)


if __name__ == "__main__":
    main()
