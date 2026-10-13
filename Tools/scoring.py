"""Reference model of solo scoring, the high-score tables and the "No colour twice" option
(mirrors Scoring.swift and GameController.colourRefusal).

score = tiles x difficulty factor x (1 + harder-option bonuses) - 5/undo - 25/hint - 25/assist, >= 0
Tables keep the top 5 per mosaic: higher score first, then faster time, then earlier date.
"""
import sys

from engine import Game

DIFFICULTY_FACTOR = {"gentle": 0.5, "classic": 1.0, "expert": 1.5}
MODIFIER_BONUS = {"hiddenQueue": 0.20, "noScout": 0.10, "noHints": 0.10, "limitedUndo": 0.20,
                  "noAssists": 0.15, "noRepeatColour": 0.25}
UNDO_PENALTY, HINT_PENALTY, ASSIST_PENALTY = 5.0, 25.0, 25.0
KEEP = 5


def swift_round(x):
    """Swift's .rounded() (half away from zero) for non-negative values."""
    import math
    return int(math.floor(x + 0.5))


def solo_score(tiles, difficulty, modifiers, undos, hints, assists):
    df = DIFFICULTY_FACTOR[difficulty]
    mf = 1.0
    for m in MODIFIER_BONUS:            # fixed order, like ChallengeModifier.sorted in Swift
        if m in modifiers:
            mf += MODIFIER_BONUS[m]
    base = swift_round(tiles * df * mf)
    u, h, a = int(undos * UNDO_PENALTY), int(hints * HINT_PENALTY), int(assists * ASSIST_PENALTY)
    return dict(base=base, undo=u, hint=h, assist=a, score=max(0, base - u - h - a), mf=mf, df=df)


def ranks_above(a, b):
    """a, b = (score, seconds, date)."""
    if a[0] != b[0]:
        return a[0] > b[0]
    if abs(a[1] - b[1]) > 0.05:
        return a[1] < b[1]
    return a[2] < b[2]


def rank(table, score, seconds):
    if score <= 0:
        return None
    probe = (score, seconds, float("inf"))
    better = sum(1 for e in table if ranks_above(e, probe))
    return better + 1 if better < KEEP else None


def insert(table, entry):
    import functools
    t = table + [entry]
    t.sort(key=functools.cmp_to_key(lambda a, b: -1 if ranks_above(a, b) else (1 if ranks_above(b, a) else 0)))
    t = t[:KEEP]
    return t, (t.index(entry) + 1 if entry in t else None)


# ---------------------------------------------------------------------------
# No colour twice: is every mosaic still solvable?
# ---------------------------------------------------------------------------

class Budget(Exception):
    pass


def colour_rule_legal(g, st, last):
    """Dispatches allowed under No colour twice (the same colour only when no other tunnel can
    send a different one). Mirrors GameController.colourRefusal."""
    if st.jammed is not None or len(st.chambers) >= st.capacity:
        return []
    fronts = [(q, g.front(st, q)) for q in range(len(g.tunnels))]
    fronts = [(q, f) for q, f in fronts if f is not None]
    out = []
    for q, (fam, _, _) in fronts:
        if last is not None and fam == last and any(f2 != last for q2, (f2, _, _) in fronts if q2 != q):
            continue
        out.append(q)
    return out


def solve_colour_rule(board, tunnels, capacity, budget=300000):
    """Depth-first search (with memo of dead states) for a winning line that obeys No colour twice,
    with no undo and no assists. Returns (line or None, nodes searched)."""
    g = Game(board, tunnels, capacity, spare_allowed=False)
    failed = set()
    nodes = [0]
    sys.setrecursionlimit(10000)

    def dfs(st, last, path):
        if st.cleared == board.tile_count:
            return path
        key = (g.state_hash(st), last)
        if key in failed:
            return None
        nodes[0] += 1
        if nodes[0] > budget:
            raise Budget()
        cands = []
        for q in colour_rule_legal(g, st, last):
            s2 = st.copy()
            fam = g.front(st, q)[0]
            g.apply_dispatch(s2, q)
            if s2.jammed is not None:
                continue
            cands.append((len(s2.chambers), -s2.cleared, q, s2, fam))
        cands.sort(key=lambda c: (c[0], c[1], c[2]))
        for _, _, q, s2, fam in cands:
            r = dfs(s2, fam, path + [q])
            if r is not None:
                return r
        failed.add(key)
        return None

    try:
        line = dfs(g.state.copy(), None, [])
    except Budget:
        return None, nodes[0]
    return line, nodes[0]


def check_line(board, tunnels, capacity, line):
    """Replays a line, checking the colour rule at every step; True if it clears the mosaic."""
    g = Game(board, tunnels, capacity, spare_allowed=False)
    st = g.state
    last = None
    for q in line:
        if q not in colour_rule_legal(g, st, last):
            return False
        last = g.front(st, q)[0]
        g.apply_dispatch(st, q)
        if st.jammed is not None:
            return False
    return st.cleared == board.tile_count
