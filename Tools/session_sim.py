"""Play-session simulator: a Swift-faithful mirror of GameController + AntScheduler + AntGeometry,
written for the Alhambra Tiles crash report (3 Oct 2026: Expert, nearly finished, Curious ants).

Unlike engine.Scheduler (the reference used for the level data), this follows the Swift code step by
step, including the parts that only exist in the app: trips pruned once their ant is home, undo that
also restores pruned trips' tiles, the slot owners of the panel, the scout-trail drawing and the
ant pose maths. Every operation that would stop a Swift app is checked explicitly:
  * Int(Double) of nan, inf or a number too big for Int,
  * array index out of range (Python would silently accept negative indices),
  * an empty route, a non-finite pose.
It also checks every new route (starts at the hole, 4-neighbour steps, never over a tile that is still
there) — the same checks as SelfTest.antStress in the app.

Two drivers:
  random_session(...)  careless play with undo / return / add slot at random moments, after following
                       the designed line part of the way (the end game is where the crash happened);
  ant_stress(...)      the exact action sequence of SelfTest.antStress in the app (same SplitMix64).
"""
import math
import random

import engine as E

INF = float("inf")


class Trap(Exception):
    """Something that would stop the Swift app (a runtime trap)."""


def s_int(x, what):
    """Swift Int(Double): traps on nan, inf and out-of-range values; truncates toward zero."""
    if x != x or x in (INF, -INF) or abs(x) >= 9.223372036854775e18:
        raise Trap("Int(%r) in %s" % (x, what))
    return int(x)


def s_min(x, y):   # Swift.min(x, y) == (y < x ? y : x)
    return y if y < x else x


def s_max(x, y):   # Swift.max(x, y) == (y >= x ? y : x)
    return y if y >= x else x


def s_round(x):    # Swift .rounded(): half away from zero
    return math.floor(x + 0.5) if x >= 0 else -math.floor(-x + 0.5)


def idx(arr, k, what):
    if k < 0 or k >= len(arr):
        raise Trap("index %d out of range 0..<%d in %s" % (k, len(arr), what))
    return arr[k]


class SplitMix64:
    """SplitMix64 in LevelGenerator.swift (unit() and int(n) as there)."""
    M = (1 << 64) - 1

    def __init__(self, seed):
        self.s = seed & self.M

    def next(self):
        self.s = (self.s + 0x9E3779B97F4A7C15) & self.M
        z = self.s
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & self.M
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & self.M
        return z ^ (z >> 31)

    def unit(self):
        return (self.next() >> 11) / float(1 << 53)

    def int(self, n):
        return 0 if n <= 1 else self.next() % n


class Trip:
    __slots__ = ("id", "move", "team", "family", "tile", "path", "depart", "arrive", "pickup_end", "home",
                 "lane", "pauses", "style")

    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)


class SwiftScheduler:
    """AntScheduler.swift, line for line."""
    STEP, SLOT, TEAM_GAP, PICKUP, MARGIN = 0.25, 0.18, 0.36, 0.9, 0.2

    def __init__(self, board, style):
        self.board = board
        self.lift = [-INF if f < 0 else INF for f in board.family]
        self.home = list(self.lift)
        self.slots = set()
        self.team_last = {}
        self.trips = []
        self.next_id = 0
        self.style = style
        self.team_trail = {}
        self.route_problems = []

    def style_for(self, team, tid):
        if self.style == "random_team":
            return E.TEAM_MIX[E.hash32(team, 31) % len(E.TEAM_MIX)]
        if self.style == "random_ant":
            return E.ANT_MIX[E.hash32(tid, 37) % len(E.ANT_MIX)]
        return self.style

    def schedule(self, claims, move, now):
        b = self.board
        stride = max(1, (len(claims) + E.MAX_STYLED_PER_SEND - 1) // E.MAX_STYLED_PER_SEND)
        spent = 0
        first = len(self.trips)
        for i, c in enumerate(claims):
            tid = self.next_id
            chosen = self.style_for(c.team, tid) if i % stride == 0 else "direct"
            seed = E.hash32(tid, 0x5EED)
            trail = self.team_trail.get(c.team) if chosen == "scout" else None
            budget = E.ant_budget(len(c.path), E.PLAN_BUDGET_PER_SEND - spent)
            route, pauses, used, sp = E.plan_route(b, self.lift, c, chosen, seed, now, trail, budget)
            spent += sp
            if used == "scout":
                self.team_trail[c.team] = route
            if not route:
                raise Trap("empty route")
            L = len(route)
            earliest = now
            last = self.team_last.get(c.team)
            if last is not None and last + self.TEAM_GAP > earliest:
                earliest = last + self.TEAM_GAP
            for k, cell in enumerate(route):
                req = idx(self.lift, cell, "liftTime[route]") + self.PICKUP + self.MARGIN - (k - 0.5) * self.STEP
                if req > earliest:
                    earliest = req
            if not math.isfinite(earliest):
                # the Swift code guards this (never converts inf to Int); it would mean a route over a
                # tile that is not scheduled to be lifted
                self.route_problems.append("route over a tile that is still there (non-finite departure)")
                earliest = now
            s = s_int(math.ceil(earliest / self.SLOT - 1e-9), "release slot")
            while s in self.slots:
                s += 1
            self.slots.add(s)
            depart = s * self.SLOT
            self.team_last[c.team] = depart
            arrive = depart + L * self.STEP + sum(d for _, d in pauses)
            pickup_end = arrive + self.PICKUP
            home = pickup_end + L * self.STEP
            self.lift[c.tile] = arrive
            self.home[c.tile] = home
            jitter = (E.hash32(tid, 977) & 0xFF) / 255.0 * 0.3 - 0.15
            lane = (1.0 if s % 2 == 0 else -1.0) * (1.0 + jitter)
            self.trips.append(Trip(id=tid, move=move, team=c.team, family=c.family, tile=c.tile, path=route,
                                   depart=depart, arrive=arrive, pickup_end=pickup_end, home=home, lane=lane,
                                   pauses=pauses, style=used))
            self.next_id += 1
        self.check_routes(first)

    def check_routes(self, first):
        """SelfTest.antStress checkNewTrips: hole start, 4-neighbour steps, ends beside the tile, finite
        ordered times, and the ant never enters a tile cell before that tile is lifted (+ pickup + margin)."""
        b = self.board
        C = b.C
        for t in self.trips[first:]:
            r = t.path
            if r[0] != b.hole:
                self.route_problems.append("a route does not start at the hole")
                continue
            if not (math.isfinite(t.depart) and t.depart <= t.arrive <= t.pickup_end <= t.home and math.isfinite(t.home)):
                self.route_problems.append("an ant's times are out of order")
            for i in range(1, len(r)):
                if abs(r[i - 1] % C - r[i] % C) + abs(r[i - 1] // C - r[i] // C) != 1:
                    self.route_problems.append("a route jumps")
            last = r[-1]
            if abs(last % C - t.tile % C) + abs(last // C - t.tile // C) != 1:
                self.route_problems.append("a route ends away from its tile")
            for k, cell in enumerate(r):
                if b.family[cell] < 0:
                    continue
                delay = sum(d for at, d in t.pauses if at < k - 0.5)
                enter = t.depart + (k - 0.5) * self.STEP + delay
                lift = self.lift[cell]
                if not lift < INF or enter + 1e-9 < lift + self.PICKUP + self.MARGIN:
                    self.route_problems.append("an ant would walk through a tile that is still there")
                    break

    def undo(self, claims, from_move):
        for c in claims:
            self.lift[c.tile] = INF
            self.home[c.tile] = INF
        keep = []
        removed = set()
        for t in self.trips:
            if t.move >= from_move:
                self.slots.discard(s_int(s_round(t.depart / self.SLOT), "undo slot"))
                self.lift[t.tile] = INF
                self.home[t.tile] = INF
                removed.add(t.team)
            else:
                keep.append(t)
        self.trips = keep
        for team in removed:
            self.team_trail.pop(team, None)
            rest = [t.depart for t in self.trips if t.team == team]
            if rest:
                self.team_last[team] = max(rest)
            else:
                self.team_last.pop(team, None)

    def busy_teams(self, t):
        out = {}
        for tr in self.trips:
            if tr.pickup_end > t:
                out[tr.team] = out.get(tr.team, 0) + 1
        return out

    def slot_free_time(self, team):
        m = -INF
        for tr in self.trips:
            if tr.team == team:
                m = max(m, tr.pickup_end)
        return m

    def prune(self, before):
        self.trips = [t for t in self.trips if not t.home < before]


# ---- AntGeometry (AntScheduler.swift) with trap checks ----

def outbound(trip, elapsed):
    step = SwiftScheduler.STEP
    e = elapsed
    for at, dur in trip.pauses:
        reach = at * step
        if e < reach:
            return e / step, None
        if e < reach + dur:
            return at, e - reach
        e -= dur
    return e / step, None


def node(trip, k, b):
    l = len(trip.path)
    if k < 0:
        raise Trap("node index %d < 0" % k)
    if k < l:
        c = trip.path[k]
        return (c % b.C + 0.5, c // b.C + 0.5)
    s = idx(trip.path, l - 1, "node last")
    t = trip.tile
    sx, sy = s % b.C + 0.5, s // b.C + 0.5
    tx, ty = t % b.C + 0.5, t // b.C + 0.5
    return (sx + (tx - sx) * 0.22, sy + (ty - sy) * 0.22)


def curve(trip, u_in, b):
    l = len(trip.path)
    u = s_max(0.0, s_min(float(l), u_in))
    mid = lambda a, c: ((a[0] + c[0]) / 2, (a[1] + c[1]) / 2)
    if u <= 0.5:
        p0 = node(trip, 0, b); p1 = node(trip, 1, b)
        m = mid(p0, p1); tau = u / 0.5
        return (p0[0] + (m[0] - p0[0]) * tau, p0[1] + (m[1] - p0[1]) * tau, p1[0] - p0[0], p1[1] - p0[1])
    if u >= l - 0.5:
        a = node(trip, l - 1, b); c = node(trip, l, b)
        m = mid(a, c); tau = (u - (l - 0.5)) / 0.5
        return (m[0] + (c[0] - m[0]) * tau, m[1] + (c[1] - m[1]) * tau, c[0] - a[0], c[1] - a[1])
    j = s_int(math.floor(u + 0.5), "curve segment")
    tau = u - (j - 0.5)
    pp = node(trip, j - 1, b); pj = node(trip, j, b); pn = node(trip, j + 1, b)
    a = mid(pp, pj); c = mid(pj, pn); o = 1 - tau
    x = o * o * a[0] + 2 * o * tau * pj[0] + tau * tau * c[0]
    y = o * o * a[1] + 2 * o * tau * pj[1] + tau * tau * c[1]
    dx = 2 * o * (pj[0] - a[0]) + 2 * tau * (c[0] - pj[0])
    dy = 2 * o * (pj[1] - a[1]) + 2 * tau * (c[1] - pj[1])
    return (x, y, dx, dy)


def pose(trip, t, b):
    if t < trip.depart or t >= trip.home:
        return None
    l = float(len(trip.path))
    if t < trip.arrive:
        u_raw, _ = outbound(trip, t - trip.depart)
        x, y, dx, dy = curve(trip, min(u_raw, l), b)
        return (x, y, math.atan2(dy, dx))
    if t < trip.pickup_end:
        x, y, dx, dy = curve(trip, l, b)
        return (x, y, math.atan2(dy, dx))
    u = l - (t - trip.pickup_end) / SwiftScheduler.STEP
    x, y, dx, dy = curve(trip, u, b)
    return (x, y, math.atan2(-dy, -dx))


def scout_trail(trip, t, b):
    """BoardPainter.paintAnts: the dotted trail of a scout ant."""
    if not (trip.style == "scout" and trip.depart <= t < trip.home + 3):
        return
    count = len(trip.path)
    if t < trip.arrive:
        count = min(len(trip.path), s_int(outbound(trip, t - trip.depart)[0], "trail length") + 1)
    for k in range(count if count >= 2 else 0):
        idx(trip.path, k, "trail cell")


def draw_frame(sch, t, b):
    n = 0
    for tr in sch.trips:
        p = pose(tr, t, b)
        if p is not None:
            n += 1
            if not all(math.isfinite(v) for v in p):
                raise Trap("non-finite ant pose %r" % (p,))
        scout_trail(tr, t, b)
    return n


class Session:
    """GameController's play-time paths (dispatch, undo, return, add slot, tick, slots panel)."""

    def __init__(self, lv, difficulty, style):
        self.lv = lv
        self.board = E.Board(lv["rows"])
        self.game = E.Game(self.board, [[tuple(x) for x in q] for q in lv["tunnels"]], lv[difficulty])
        self.sch = SwiftScheduler(self.board, style)
        self.t = 0.0
        self.slot_owners = []
        self.occupied = 0
        self.poses = 0
        self.counts = {"sends": 0, "undos": 0, "returns": 0, "adds": 0, "ants": 0}

    def refresh_slots(self):
        """GameController.refreshSlots (the parts that index arrays or convert numbers)."""
        busy = self.sch.busy_teams(self.t)
        chambers = self.game.state.chambers
        ci = {c.uid: i for i, c in enumerate(chambers)}
        occupants = set(busy) | {c.uid for c in chambers}
        for k in range(len(self.slot_owners)):
            u = self.slot_owners[k]
            if u is not None and u not in occupants:
                self.slot_owners[k] = None
        cap = self.game.state.capacity
        if len(self.slot_owners) < cap:
            self.slot_owners += [None] * (cap - len(self.slot_owners))
        elif len(self.slot_owners) > cap:
            kept = [u for u in self.slot_owners if u is not None]
            self.slot_owners = kept + [None] * max(0, cap - len(kept))
        placed = {u for u in self.slot_owners if u is not None}
        newcomers = [c.uid for c in chambers if c.uid not in placed]
        newcomers += [u for u in sorted(busy) if u not in placed and u not in ci]
        for u in newcomers:
            if None in self.slot_owners:
                self.slot_owners[self.slot_owners.index(None)] = u
            else:
                self.slot_owners.append(u)
        for u in self.slot_owners:
            if u is not None and u in ci:
                idx(chambers, ci[u], "slot's waiting team")
        self.occupied = len(occupants)
        if self.occupied >= cap:
            soonest = INF
            for u in busy:
                soonest = min(soonest, self.sch.slot_free_time(u))
            if math.isfinite(soonest):
                s_int(math.ceil(max(0.0, soonest - self.t) * 2) / 2, "next slot frees in")

    def send(self, q):
        self.refresh_slots()
        g = self.game
        if not (0 <= q < len(g.tunnels)) or g.front(g.state, q) is None or g.state.jammed is not None:
            return False
        if not (self.occupied < g.state.capacity and g.can_dispatch(q)):
            return False
        ev = g.dispatch(q)
        self.sch.schedule(ev, len(g.moves) - 1, self.t + 0.04)
        self.counts["sends"] += 1
        self.counts["ants"] += len(ev)
        self.refresh_slots()
        return True

    def undo(self):
        g = self.game
        if not g.history:
            return False
        claims = g.move_claims[-1]
        g.undo()
        self.sch.undo(claims, len(g.moves))
        self.counts["undos"] += 1
        self.refresh_slots()
        return True

    def recall(self, i):
        if not self.game.can_recall(i):
            return False
        self.game.recall(i)
        self.counts["returns"] += 1
        self.refresh_slots()
        return True

    def add_slot(self):
        self.game.add_chamber()
        self.counts["adds"] += 1
        self.refresh_slots()

    def advance(self, dt, frames):
        """10 Hz ticks (slots, prune) with `frames` drawn per tick."""
        end = self.t + dt
        while self.t < end - 1e-12:
            step = min(0.1, end - self.t)
            t0 = self.t
            self.t += step
            for f in range(1, frames + 1):
                self.poses += draw_frame(self.sch, t0 + step * f / frames, self.board)
            self.refresh_slots()
            self.sch.prune(self.t - 0.5)

    def wait_for_slot(self):
        soonest = INF
        for u in self.sch.busy_teams(self.t):
            soonest = min(soonest, self.sch.slot_free_time(u))
        self.advance(min(30.0, max(0.1, soonest - self.t + 0.01)) if math.isfinite(soonest) else 0.5, frames=1)

    def done(self):
        return self.game.won() and not self.sch.trips


def random_session(lv, difficulty, style, seed, max_actions=600):
    """Follow the designed line part of the way (often almost to the end), then play carelessly with
    every recovery option at random moments; finally let the last ants walk home."""
    rng = random.Random(seed)
    s = Session(lv, difficulty, style)
    sol = lv["solution"]
    n = len(sol)
    follow = rng.choice([n - 1, n - 2, n - 4, n - 8, n // 2, 0])
    actions = 0
    k = 0
    while k < max(0, follow) and actions < max_actions:
        actions += 1
        if s.send(sol[k]):
            k += 1
            s.advance(rng.choice([0.05, 0.2, 0.5, 1.0]), frames=1 if rng.random() < 0.3 else 0)
        else:
            s.wait_for_slot()
    g = s.game
    while not s.done() and actions < max_actions:
        actions += 1
        if g.won():
            s.advance(1.0, frames=1)
            continue
        r = rng.random()
        if r < 0.55:
            s.send(rng.randrange(len(g.tunnels)))
        elif r < 0.70:
            s.undo()
        elif r < 0.80:
            if g.state.chambers:
                s.recall(rng.randrange(len(g.state.chambers)))
        elif r < 0.84:
            s.add_slot()
        elif r < 0.88:
            km = len(g.moves)
            if g.moves == sol[:km] and km < n:
                s.send(sol[km])
        s.advance(rng.choice([0.0, 0.04, 0.1, 0.3, 1.0, 3.0]), frames=1 if rng.random() < 0.25 else 0)
    steps = 0
    while g.won() and s.sch.trips and steps < 2000:
        s.advance(1.0, frames=1)
        steps += 1
    return s


def ant_stress(lv, style, seed, max_actions):
    """SelfTest.antStress in the app, step for step (same SplitMix64 choices)."""
    b = E.Board(lv["rows"])
    g = E.Game(b, [[tuple(x) for x in q] for q in lv["tunnels"]], lv["expert"])
    sch = SwiftScheduler(b, style)
    rng = SplitMix64(seed)
    rep = {"actions": 0, "sends": 0, "undos": 0, "returns": 0, "adds": 0, "trips": 0, "poses": 0, "won": False}
    t = [0.0]

    def occupied():
        occ = set(sch.busy_teams(t[0]))
        occ |= {c.uid for c in g.state.chambers}
        return len(occ)

    def advance(dt):
        t0 = t[0]
        t[0] += max(0.0, dt)
        for probe in (t0 + (t[0] - t0) * 0.5, t[0]):
            for tr in sch.trips:
                p = pose(tr, probe, b)
                if p is not None:
                    rep["poses"] += 1
                    if not all(math.isfinite(v) for v in p):
                        raise Trap("non-finite pose")
                if tr.style == "scout" and tr.depart <= probe < tr.arrive:
                    if not math.isfinite(outbound(tr, probe - tr.depart)[0]):
                        raise Trap("non-finite trail position")
        sch.prune(t[0] - 0.5)

    def send(q):
        if not (0 <= q < len(g.tunnels)) or not g.can_dispatch(q) or occupied() >= g.state.capacity:
            return False
        ev = g.dispatch(q)
        sch.schedule(ev, len(g.moves) - 1, t[0] + 0.04)
        rep["sends"] += 1
        rep["trips"] += len(ev)
        return True

    sol = lv["solution"]
    follow = max(0, len(sol) - 10)
    k = 0
    while k < follow and rep["actions"] < max_actions:
        rep["actions"] += 1
        if send(sol[k]):
            k += 1
            advance(0.3)
        else:
            soonest = INF
            for u in sch.busy_teams(t[0]):
                soonest = min(soonest, sch.slot_free_time(u))
            advance(min(30.0, max(0.1, soonest - t[0] + 0.01)) if math.isfinite(soonest) else 0.5)
    waits = [0.0, 0.04, 0.1, 0.3, 1.0, 3.0]
    while rep["actions"] < max_actions and not (g.won() and not sch.trips):
        rep["actions"] += 1
        if g.won():
            advance(5.0)
            continue
        r = rng.unit()
        if r < 0.55:
            send(rng.int(len(g.tunnels)))
        elif r < 0.70:
            if g.history:
                claims = g.move_claims[-1]
                g.undo()
                sch.undo(claims, len(g.moves))
                rep["undos"] += 1
        elif r < 0.80:
            if g.state.chambers:
                g.recall(rng.int(len(g.state.chambers)))
                rep["returns"] += 1
        elif r < 0.84:
            g.add_chamber()
            rep["adds"] += 1
        elif r < 0.92:
            km = len(g.moves)
            if km < len(sol) and g.moves == sol[:km]:
                send(sol[km])
        advance(waits[rng.int(len(waits))])
    steps = 0
    while g.won() and sch.trips and steps < 400:
        advance(1.0)
        steps += 1
    rep["won"] = g.won() and not sch.trips
    rep["route_problems"] = sch.route_problems[:3]
    return rep
