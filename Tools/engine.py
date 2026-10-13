"""Reference model of the Tessera Colony rules engine.

This is a line-for-line mirror of Engine.swift / AntScheduler.swift. It is used to
  * generate the tunnel queues of each level (generate_levels.py),
  * prove every shipped level is solvable and measure its difficulty,
  * test legal ant paths, pickup timing, chamber behaviour, undo and save/replay,
  * produce golden checksums that the Swift app re-derives in its on-device self-test.

Rules summary
-------------
Board: art W x H plus ground margins (2 left, 2 right, 2 top, 6 bottom). The ant-hill hole is
at (C // 2, R - 3). Ground cells and removed tiles are "open". Ants walk on open cells
(4-neighbour moves) and can pick up a tile that is 4-adjacent to an open cell they reach.

Claim run (one team, one pass): unit-cost BFS from the hole over open cells in bucket order.
Matching tiles adjacent to the explored region become candidates at distance d+1; a candidate is
claimed when its bucket is processed (nearest first, FIFO tie-break, neighbour order
up/left/right/down). A claimed tile immediately becomes open, so a team can tunnel through its
own colour. Each claim records the path hole -> stand cell (the open cell next to the tile).

Slots: `capacity` is the number of slots. Every sent team occupies a slot. In this model a slot
is taken by a team that is waiting (couldn't reach all its tiles); the Scheduler adds teams whose
ants are still picking up tiles (busy_teams). A team can only be sent when a slot is open, so
sending never jams; "deadlocked" = every slot holds a waiting team.

Hold (parking a team in a slot without sending it) was removed from the game. hold/release and
the `held` flag remain only so saves made with the earlier version still replay.

Dispatch: the front team of a tunnel enters. Passes repeat over [incoming] + non-held waiting
teams until nobody can claim anything; finished teams leave. If the incoming team still needs
tiles it keeps its slot and waits.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
import math

MARGIN_L, MARGIN_R, MARGIN_T, MARGIN_B = 2, 2, 2, 6
NEIGHBOURS = ((0, -1), (-1, 0), (1, 0), (0, 1))  # up, left, right, down
SPARE_MOVE = 100   # kept as an alias of ADD_MOVE
ADD_MOVE = 100
RECALL_JAMMED = 199
RECALL_BASE = 200   # + chamber index: send a chamber team back to its tunnel
HOLD_BASE = 300     # legacy (old saves): + tunnel index, park the front team without sending it
RELEASE_BASE = 400  # legacy (old saves): + chamber index, send a held team now


def fnv_mix(h, v):
    h ^= v & 0xFFFFFFFF
    return (h * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF


FNV_SEED = 0xCBF29CE484222325


@dataclass
class Team:
    uid: int          # tunnel * 1000 + index within tunnel
    family: int
    quota: int
    remaining: int
    held: bool = False   # parked in a chamber by the player; does not claim until released


@dataclass
class Claim:
    team: int         # Team.uid
    family: int
    tile: int
    path: List[int]   # hole ... stand


class Board:
    def __init__(self, rows):
        self.W, self.H = len(rows[0]), len(rows)
        self.C = self.W + MARGIN_L + MARGIN_R
        self.R = self.H + MARGIN_T + MARGIN_B
        self.N = self.C * self.R
        self.family = [-1] * self.N
        self.tone = [0] * self.N
        for y in range(self.H):
            for x in range(self.W):
                if rows[y][x] == '.':
                    continue
                code = ord(rows[y][x]) - 97
                i = (y + MARGIN_T) * self.C + (x + MARGIN_L)
                self.family[i], self.tone[i] = divmod(code, 4)
        self.hole = (self.R - 3) * self.C + self.C // 2
        self.tile_count = sum(1 for f in self.family if f >= 0)
        # neighbour table (-1 = outside)
        C, R = self.C, self.R
        self.nb = []
        for i in range(self.N):
            x, y = i % C, i // C
            row = []
            for dx, dy in NEIGHBOURS:
                nx, ny = x + dx, y + dy
                row.append(ny * C + nx if 0 <= nx < C and 0 <= ny < R else -1)
            self.nb.append(tuple(row))

    def family_counts(self):
        counts = [0] * 6
        for f in self.family:
            if f >= 0:
                counts[f] += 1
        return counts


@dataclass
class State:
    open: bytearray
    heads: List[int]
    chambers: List[Team]
    capacity: int
    added: int = 0
    jammed: Optional[Team] = None
    cleared: int = 0
    returned: Optional[List[List[Team]]] = None   # teams sent back to the front of their tunnel

    def copy(self):
        cp = lambda t: Team(t.uid, t.family, t.quota, t.remaining, t.held)
        return State(bytearray(self.open), list(self.heads), [cp(t) for t in self.chambers],
                     self.capacity, self.added, None if self.jammed is None else cp(self.jammed),
                     self.cleared, [[cp(t) for t in stack] for stack in self.returned])


class Game:
    def __init__(self, board: Board, tunnels, capacity, spare_allowed=True):
        self.board = board
        self.tunnels = tunnels            # list of list of (family, quota)
        op = bytearray(board.N)
        for i, f in enumerate(board.family):
            if f < 0:
                op[i] = 1
        self.state = State(op, [0] * len(tunnels), [], capacity, returned=[[] for _ in tunnels])
        self.history: List[State] = []
        self.moves: List[int] = []
        self.move_claims: List[List[Claim]] = []

    # ---------------- core ----------------
    def claim_run(self, st: State, fam: int, limit: int, team_uid: int) -> List[Claim]:
        b = self.board
        if limit <= 0:
            return []
        N = b.N
        opn = st.open
        famarr = b.family
        nb = b.nb
        dist = [-1] * N
        parent = [-1] * N
        cand = bytearray(N)
        dist[b.hole] = 0
        buckets = [[b.hole]]
        claims: List[Claim] = []
        d = 0
        done = False
        while d < len(buckets) and not done:
            cur = buckets[d]
            nxt = None
            for e in cur:
                if not opn[e]:
                    if len(claims) >= limit:
                        done = True
                        break
                    opn[e] = 1
                    st.cleared += 1
                    dist[e] = d
                    path = []
                    p = parent[e]
                    while p != -1:
                        path.append(p)
                        p = parent[p]
                    path.reverse()
                    claims.append(Claim(team_uid, fam, e, path))
                    if len(claims) >= limit:
                        done = True
                        break
                for n in nb[e]:
                    if n < 0:
                        continue
                    if opn[n]:
                        if dist[n] < 0:
                            dist[n] = d + 1
                            parent[n] = e
                            if nxt is None:
                                if len(buckets) == d + 1:
                                    buckets.append([])
                                nxt = buckets[d + 1]
                            nxt.append(n)
                    elif famarr[n] == fam and not cand[n]:
                        cand[n] = 1
                        parent[n] = e
                        if nxt is None:
                            if len(buckets) == d + 1:
                                buckets.append([])
                            nxt = buckets[d + 1]
                        nxt.append(n)
            d += 1
        return claims

    def front(self, st: State, q: int):
        """(family, tiles needed, uid) of the team at the front of tunnel q, or None."""
        if st.returned[q]:
            t = st.returned[q][-1]
            return (t.family, t.remaining, t.uid)
        if st.heads[q] < len(self.tunnels[q]):
            f, n = self.tunnels[q][st.heads[q]]
            return (f, n, q * 1000 + st.heads[q])
        return None

    def resolve(self, st: State, incoming: Optional[Team]) -> List[Claim]:
        events: List[Claim] = []
        while True:
            progress = False
            order = ([incoming] if incoming is not None else []) + st.chambers
            for t in order:
                if t.remaining == 0 or t.held:
                    continue
                c = self.claim_run(st, t.family, t.remaining, t.uid)
                if c:
                    progress = True
                    t.remaining -= len(c)
                    events.extend(c)
            st.chambers = [t for t in st.chambers if t.remaining > 0]
            if not progress:
                break
        if incoming is not None and incoming.remaining > 0:
            if len(st.chambers) < st.capacity:
                st.chambers.append(incoming)
            else:
                st.jammed = incoming
        return events

    def apply_dispatch(self, st: State, q: int) -> List[Claim]:
        if st.returned[q]:
            t = st.returned[q].pop()
            inc = Team(t.uid, t.family, t.quota, t.remaining)
        else:
            fam, quota = self.tunnels[q][st.heads[q]]
            inc = Team(q * 1000 + st.heads[q], fam, quota, quota)
            st.heads[q] += 1
        return self.resolve(st, inc)

    # ---------------- player actions ----------------
    def can_dispatch(self, q):
        """Slot rule: a team can only be sent into an open slot. Teams that are waiting or held
        keep their slot; (in the app, teams whose ants are still collecting also keep theirs —
        see Scheduler.busy_teams). Because the sent team already owns a slot, sending never blocks."""
        st = self.state
        return st.jammed is None and self.front(st, q) is not None and len(st.chambers) < st.capacity

    def deadlocked(self, busy=0):
        """Every slot holds a waiting team (none held, none still collecting): nothing can move."""
        st = self.state
        if self.won():
            return False
        has_front = any(self.front(st, q) is not None for q in range(len(self.tunnels)))
        return (len(st.chambers) + busy >= st.capacity and busy == 0
                and not any(t.held for t in st.chambers) and (has_front or st.chambers))

    def _record(self, code, claims):
        self.moves.append(code)
        self.move_claims.append(claims)

    def dispatch(self, q) -> List[Claim]:
        assert self.can_dispatch(q)
        self.history.append(self.state.copy())
        ev = self.apply_dispatch(self.state, q)
        self._record(q, ev)
        return ev

    @staticmethod
    def _unjam(st):
        if st.jammed is not None and len(st.chambers) < st.capacity:
            st.chambers.append(st.jammed)
            st.jammed = None

    def add_chamber(self):
        """Recovery: open one more chamber (a jammed team moves straight in)."""
        self.history.append(self.state.copy())
        st = self.state
        st.capacity += 1
        st.added += 1
        self._unjam(st)
        self._record(ADD_MOVE, [])

    def can_recall(self, i):
        return 0 <= i < len(self.state.chambers)

    def recall(self, i):
        """Recovery: send a waiting team back to the front of its tunnel, freeing its chamber.
        It keeps the number of tiles it still needs."""
        assert self.can_recall(i)
        self.history.append(self.state.copy())
        st = self.state
        t = st.chambers.pop(i)
        t.held = False
        st.returned[t.uid // 1000].append(t)
        self._unjam(st)
        self._record(RECALL_BASE + i, [])

    def recall_jammed(self):
        """Recovery: the blocked team steps back into its tunnel instead of waiting."""
        assert self.state.jammed is not None
        self.history.append(self.state.copy())
        st = self.state
        t = st.jammed
        st.jammed = None
        st.returned[t.uid // 1000].append(t)
        self._record(RECALL_JAMMED, [])

    def can_hold(self, q):
        st = self.state
        return st.jammed is None and self.front(st, q) is not None and len(st.chambers) < st.capacity

    def hold(self, q):
        """Legacy (old saves only): park the front team of tunnel q in a free chamber."""
        assert self.can_hold(q)
        self.history.append(self.state.copy())
        st = self.state
        if st.returned[q]:
            t = st.returned[q].pop()
            t = Team(t.uid, t.family, t.quota, t.remaining, True)
        else:
            fam, quota = self.tunnels[q][st.heads[q]]
            t = Team(q * 1000 + st.heads[q], fam, quota, quota, True)
            st.heads[q] += 1
        st.chambers.append(t)
        self._record(HOLD_BASE + q, [])

    def can_release(self, i):
        st = self.state
        return st.jammed is None and 0 <= i < len(st.chambers) and st.chambers[i].held

    @staticmethod
    def apply_release(game, st, i):
        t = st.chambers.pop(i)
        inc = Team(t.uid, t.family, t.quota, t.remaining, False)
        return game.resolve(st, inc)   # its own chamber is free again, so this can never block

    def release(self, i):
        """Send a held team now."""
        assert self.can_release(i)
        self.history.append(self.state.copy())
        ev = Game.apply_release(self, self.state, i)
        self._record(RELEASE_BASE + i, ev)
        return ev

    def apply_move(self, code):
        if code == ADD_MOVE:
            self.add_chamber()
        elif code == RECALL_JAMMED:
            self.recall_jammed()
        elif code >= RELEASE_BASE:
            self.release(code - RELEASE_BASE)
        elif code >= HOLD_BASE:
            self.hold(code - HOLD_BASE)
        elif code >= RECALL_BASE:
            self.recall(code - RECALL_BASE)
        else:
            self.dispatch(code)

    def undo(self):
        if not self.history:
            return False
        self.state = self.history.pop()
        self.moves.pop()
        self.move_claims.pop()
        return True

    def won(self):
        return self.state.cleared == self.board.tile_count

    def scout(self, q):
        """What would happen if tunnel q's front team were sent now."""
        st = self.state.copy()
        fam, need, uid = self.front(self.state, q)
        ev = self.apply_dispatch(st, q)
        own = sum(1 for c in ev if c.team == uid)
        return {"own": own, "quota": need, "tiles": [c.tile for c in ev if c.team == uid],
                "fits": own == need, "jam": st.jammed is not None, "total": len(ev)}

    def state_hash(self, st=None):
        st = st or self.state
        h = FNV_SEED
        for i, v in enumerate(st.open):
            if v and self.board.family[i] >= 0:
                h = fnv_mix(h, i)
        for x in st.heads:
            h = fnv_mix(h, x)
        for t in st.chambers:
            h = fnv_mix(h, t.uid)
            h = fnv_mix(h, t.remaining)
            h = fnv_mix(h, 1 if t.held else 0)
        for stack in st.returned:
            for t in stack:
                h = fnv_mix(h, t.uid)
                h = fnv_mix(h, t.remaining)
        h = fnv_mix(h, st.capacity)
        h = fnv_mix(h, 1 if st.jammed else 0)
        return h


def claims_hash(claim_lists):
    h = FNV_SEED
    for lst in claim_lists:
        for c in lst:
            h = fnv_mix(h, c.tile)
            h = fnv_mix(h, len(c.path))
    return h


# ---------------------------------------------------------------------------
# Greedy policy + rollouts (mirrors HintSolver.swift)
# ---------------------------------------------------------------------------

def evaluate_fronts(game: Game, st: State):
    """Candidate moves: send each tunnel's front team, or release a held team.
    Returns list of (move code, fits, jam, own, total_claims, state after)."""
    out = []
    for i, t in enumerate(st.chambers):
        if not t.held:
            continue
        s2 = st.copy()
        ev = Game.apply_release(game, s2, i)
        own = sum(1 for c in ev if c.team == t.uid)
        out.append((RELEASE_BASE + i, own == t.remaining, False, own, len(ev), s2))
    for q in range(len(game.tunnels)):
        fr = game.front(st, q)
        if fr is None or len(st.chambers) >= st.capacity:
            continue
        fam, need, uid = fr
        s2 = st.copy()
        ev = game.apply_dispatch(s2, q)
        own = sum(1 for c in ev if c.team == uid)
        out.append((q, own == need, s2.jammed is not None, own, len(ev), s2))
    return out


def greedy_choice(game: Game, st: State):
    opts = evaluate_fronts(game, st)
    if not opts:
        return None, None
    fits = [o for o in opts if o[1]]
    if fits:
        best = max(fits, key=lambda o: (o[4], -o[0]))
        return best[0], best[5]
    safe = [o for o in opts if not o[2]]
    if safe:
        best = max(safe, key=lambda o: (o[4], -o[0]))
        return best[0], best[5]
    best = max(opts, key=lambda o: (o[4], -o[0]))
    return best[0], best[5]


def rollout(game: Game, st: State, max_moves=400):
    st = st.copy()
    n = 0
    while st.jammed is None and st.cleared < game.board.tile_count and n < max_moves:
        q, s2 = greedy_choice(game, st)
        if q is None:
            break
        st = s2
        n += 1
    return st.jammed is None and st.cleared == game.board.tile_count, st.cleared


def hint(game: Game):
    """Mirror of HintSolver.bestMove: evaluate each front with a greedy rollout."""
    st = game.state
    best = None
    for (q, fits, jam, own, total, s2) in evaluate_fronts(game, st):
        if jam:
            score = (0, 0, 0, -q)
        else:
            win, cleared = rollout(game, s2)
            score = (1 if win else 0, 1 if fits else 0, cleared, -q)
        if best is None or score > best[0]:
            best = (score, q)
    return None if best is None else (best[1], best[0][0] == 1)


# ---------------------------------------------------------------------------
# Visual scheduler (mirrors AntScheduler.swift)
# ---------------------------------------------------------------------------

STEP = 1.0 / 4.0         # game-seconds per cell: at 1x an ant walks 4 cells (~2.5 body lengths) per second
SLOT = 0.18              # the hole releases at most one ant per slot
TEAM_GAP = 0.36          # one team releases at most one ant every TEAM_GAP (other teams fill the gaps)
PICKUP = 0.9             # grab, lift and turn around
MARGIN = 0.2             # gap after a pickup before another ant walks through that cell


@dataclass
class Trip:
    claim: Claim
    move: int
    depart: float
    arrive: float
    pickup_end: float
    home: float
    route: List[int] = None          # cells the ant walks (hole ... stand); the claim path for "direct"
    pauses: List[Tuple[float, float]] = field(default_factory=list)   # (at path position u, seconds)
    style: str = "direct"
    lane: float = 0.0                # outbound lane (outer lanes); carriers come home in the middle

    def __post_init__(self):
        if self.route is None:
            self.route = list(self.claim.path)


# ---------------------------------------------------------------------------------------------
# Ant path styles (visual only: which tiles are claimed never changes). Mirrors PathPlanner.swift.
# Every route runs hole -> the claim's stand cell over cells that are ground or already scheduled
# to be lifted; the scheduler then delays the ant's departure until every tile on its route is
# lifted (+ pickup + margin), exactly as for the direct path.
# ---------------------------------------------------------------------------------------------

PATH_STYLES = ["direct", "natural", "curious", "wall", "scout", "random_team", "random_ant"]
TEAM_MIX = ["direct", "natural", "curious", "wall", "scout"]
ANT_MIX = ["direct", "natural", "curious", "wall"]
FUTURE_PENALTY = 4.0       # wandering styles avoid cells whose tile is not lifted yet


def hash32(a, b):
    M32 = 0xFFFFFFFF
    h = ((a * 0x9E3779B1) & M32) ^ ((b * 0x85EBCA77) & M32)
    h ^= h >> 15
    h = (h * 0x2C1B3C6D) & M32
    h ^= h >> 12
    h = (h * 0x297A2D39) & M32
    h ^= h >> 15
    return h


def unit_hash(a, b):
    return (hash32(a, b) & 0xFFFF) / 65535.0


# Route planning is bounded so a send never stalls the game (mirrors PathPlanner.swift): each ant's
# search stays inside a corridor of CORRIDOR cells around its direct path (so a route always exists
# and the search cannot flood the open ground), and may not exceed the longest acceptable route.
# At most MAX_STYLED_PER_SEND ants of one send get a styled route, spread evenly through the send;
# the others walk their direct path (no search at all). A send shares PLAN_BUDGET_PER_SEND
# expansions; each ant may use up to 10 per cell of its direct path + 100. An ant whose search runs
# out walks its direct path.
CORRIDOR = 3
PLAN_BUDGET_PER_SEND = 16000
MAX_STYLED_PER_SEND = 32


def ant_budget(direct_len, remaining):
    return max(0, min(remaining, 10 * direct_len + 100))
STYLE_WEIGHT = {"natural": 1.05, "curious": 1.6, "wall": 1.3, "scout_trail": 1.3, "scout": 1.8}


def corridor_cells(board, path, radius=CORRIDOR):
    """Cells within Manhattan distance `radius` of any cell of `path`."""
    C, R = board.C, board.R
    cells = set()
    for c in path:
        x, y = c % C, c // C
        for dy in range(-radius, radius + 1):
            yy = y + dy
            if yy < 0 or yy >= R:
                continue
            span = radius - abs(dy)
            for dx in range(-span, span + 1):
                xx = x + dx
                if 0 <= xx < C:
                    cells.add(yy * C + xx)
    return cells


def max_route_cells(direct_len):
    return max(2 * direct_len, direct_len + 14)


def astar(board, walkable, start, goal, cost, weight=1.0, max_steps=None, budget=None):
    """Weighted A* over 4-neighbour cells (f = g + weight * Manhattan), never expanding a cell from
    which the goal is more than `max_steps` steps away along the route so far, and giving up after
    `budget` expansions. Returns (cells or None, expansions)."""
    import heapq
    C, R = board.C, board.R
    gx, gy = goal % C, goal // C
    INF = float("inf")
    g = {start: 0.0}
    steps = {start: 0}
    prev = {start: -1}
    closed = set()
    counter = 0
    expansions = 0
    heap = [(weight * (abs(start % C - gx) + abs(start // C - gy)), 0, start)]
    found = start == goal
    while heap:
        f, _, c = heapq.heappop(heap)
        if c in closed:
            continue
        if c == goal:
            found = True
            break
        closed.add(c)
        expansions += 1
        if budget is not None and expansions > budget:
            return None, expansions
        x, y = c % C, c // C
        sc = steps[c] + 1
        for dx, dy in NEIGHBOURS:
            nx, ny = x + dx, y + dy
            if nx < 0 or ny < 0 or nx >= C or ny >= R:
                continue
            n = ny * C + nx
            if n in closed or not walkable(n):
                continue
            h = abs(nx - gx) + abs(ny - gy)
            if max_steps is not None and sc + 1 + h > max_steps:
                continue
            ng = g[c] + cost(n)
            if ng < g.get(n, INF) - 1e-12:
                g[n] = ng
                prev[n] = c
                steps[n] = sc
                counter += 1
                heapq.heappush(heap, (ng + weight * h, counter, n))
    if not found:
        return None, expansions
    path = [goal]
    while path[-1] != start:
        path.append(prev[path[-1]])
    path.reverse()
    return path, expansions


def plan_route(board, lift_time, claim, style, seed, now, trail=None, budget=PLAN_BUDGET_PER_SEND):
    """Route for one ant. Returns (cells, pauses, style actually used, expansions spent)."""
    direct = list(claim.path)
    if style == "direct" or len(direct) < 3 or budget <= 0:
        return direct, [], "direct", 0
    start, goal = direct[0], direct[-1]
    C = board.C
    INF = float("inf")
    corridor = corridor_cells(board, direct)

    def walkable(n):
        return n in corridor and lift_time[n] < INF

    def future(n):
        return FUTURE_PENALTY if (board.family[n] >= 0 and lift_time[n] > now + 1e-9) else 0.0

    weight = STYLE_WEIGHT.get(style, 1.0)
    if style == "natural":
        hx, hy = start % C + 0.5, start // C + 0.5
        tx, ty = goal % C + 0.5, goal // C + 0.5
        ln = max(1e-9, math.hypot(tx - hx, ty - hy))

        def cost(n):
            px, py = n % C + 0.5, n // C + 0.5
            return 1.0 + 1e-4 * abs((tx - hx) * (hy - py) - (hx - px) * (ty - hy)) / ln
    elif style == "curious":
        def cost(n):
            return 1.0 + 1.6 * unit_hash(seed, n) + future(n)
    elif style == "wall":
        R = board.R

        def edge(n):
            # beside a tile that is still on the board (the mosaic's current edge, not the board's rim)
            x, y = n % C, n // C
            for dx, dy in NEIGHBOURS:
                nx, ny = x + dx, y + dy
                if 0 <= nx < C and 0 <= ny < R and not lift_time[ny * C + nx] < INF:
                    return True
            return False

        def cost(n):
            return 1.0 + (0.0 if edge(n) else 0.9) + future(n)
    elif style == "scout":
        if trail:
            tset = set(trail)
            weight = STYLE_WEIGHT["scout_trail"]

            def cost(n):
                return 1.0 + (0.0 if n in tset else 1.2) + future(n)
        else:
            def cost(n):
                return 1.0 + 2.5 * unit_hash(seed, n) + future(n)
    else:
        return direct, [], "direct", 0
    L0 = len(direct)
    route, spent = astar(board, walkable, start, goal, cost, weight, max_route_cells(L0), budget)
    if route is None or len(route) > max_route_cells(L0):
        return direct, [], "direct", spent
    pauses = []
    L = len(route)
    sniff = 0
    if style == "curious":
        sniff = 1 if unit_hash(seed, 7) < 0.35 else 0      # about a third of curious ants stop to sniff
    elif style == "scout" and not trail:
        sniff = 1
    if L >= 8:
        for k in range(sniff):
            u = 2.0 + unit_hash(seed, 101 + k) * (L - 4.0)
            pauses.append((round(u, 3), round(0.5 + 0.7 * unit_hash(seed, 202 + k), 3)))
        pauses.sort()
    return route, pauses, style, spent


class Scheduler:
    def __init__(self, board: Board, style="direct"):
        self.board = board
        self.lift_time = [float('-inf') if f < 0 else float('inf') for f in board.family]
        self.slots = set()
        self.team_last = {}
        self.trips: List[Trip] = []
        self.style = style
        self.team_trail = {}
        self.next_id = 0

    def style_for(self, team, trip_id):
        st = self.style
        if st == "random_team":
            return TEAM_MIX[hash32(team, 31) % len(TEAM_MIX)]
        if st == "random_ant":
            return ANT_MIX[hash32(trip_id, 37) % len(ANT_MIX)]
        return st

    def schedule(self, claims: List[Claim], move: int, now: float, style=None):
        if style is not None:
            self.style = style
        self.last_expansions = 0
        stride = max(1, -(-len(claims) // MAX_STYLED_PER_SEND))     # ceil: style every stride-th ant
        for i, c in enumerate(claims):
            tid = self.next_id
            self.next_id += 1
            st = self.style_for(c.team, tid) if i % stride == 0 else "direct"
            seed = hash32(tid, 0x5EED)
            route, pauses, used, spent = plan_route(self.board, self.lift_time, c, st, seed, now,
                                                    self.team_trail.get(c.team) if st == "scout" else None,
                                                    ant_budget(len(c.path), PLAN_BUDGET_PER_SEND - self.last_expansions))
            self.last_expansions += spent
            if used == "scout":
                self.team_trail[c.team] = route
            L = len(route)
            earliest = now
            last = self.team_last.get(c.team)
            if last is not None and last + TEAM_GAP > earliest:
                earliest = last + TEAM_GAP
            for k, cell in enumerate(route):
                req = self.lift_time[cell] + PICKUP + MARGIN - (k - 0.5) * STEP
                if req > earliest:
                    earliest = req
            slot = int(math.ceil(earliest / SLOT - 1e-9))
            while slot in self.slots:
                slot += 1
            self.slots.add(slot)
            depart = slot * SLOT
            self.team_last[c.team] = depart
            arrive = depart + L * STEP + sum(d for _, d in pauses)
            self.lift_time[c.tile] = arrive
            pickup_end = arrive + PICKUP
            home = pickup_end + L * STEP
            jitter = (hash32(tid, 977) & 0xFF) / 255.0 * 0.3 - 0.15
            lane = (1.0 if slot % 2 == 0 else -1.0) * (1.0 + jitter)
            self.trips.append(Trip(c, move, depart, arrive, pickup_end, home, route, pauses, used, lane))

    def busy_teams(self, t):
        """Teams with at least one tile not yet picked up at time t (they still occupy a slot)."""
        return {tr.claim.team for tr in self.trips if tr.pickup_end > t}

    def slot_free_time(self, team):
        return max((tr.pickup_end for tr in self.trips if tr.claim.team == team), default=float('-inf'))

    def undo_move(self, move: int):
        keep = []
        teams = set()
        for t in self.trips:
            if t.move >= move:
                self.lift_time[t.claim.tile] = float('inf')
                self.slots.discard(int(round(t.depart / SLOT)))
                teams.add(t.claim.team)
            else:
                keep.append(t)
        self.trips = keep
        for team in teams:
            self.team_trail.pop(team, None)
            rest = [t.depart for t in self.trips if t.claim.team == team]
            if rest:
                self.team_last[team] = max(rest)
            else:
                self.team_last.pop(team, None)


def hint_full(game: Game, solution):
    """Mirror of HintSolver.hint(): follow the designer's plan while the player is on it,
    otherwise search with greedy rollouts, otherwise suggest undoing back to the plan."""
    moves = game.moves
    k = len(moves)
    if k <= len(solution) and moves == solution[:k] and game.state.jammed is None:
        if k < len(solution):
            return ("move", solution[k], True)
        return ("none", -1, True)
    if game.state.jammed is None:
        h = hint(game)
        if h is not None and h[1]:
            return ("move", h[0], True)
    lcp = 0
    while lcp < len(moves) and lcp < len(solution) and moves[lcp] == solution[lcp]:
        lcp += 1
    back = len(moves) - lcp
    if back > 0 or game.state.jammed is not None or game.deadlocked():
        return ("undo", max(1, back), False)
    h = hint(game)
    return ("move", h[0], False) if h else ("none", -1, False)
