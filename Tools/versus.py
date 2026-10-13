"""Reference model of two-player versus mode (mirrors VersusEngine.swift).

Options (all combinable):
  layout   "race"   - split screen: each player has their own copy of the mosaic
           "shared" - one mosaic, two hills (left and right); both players get the same tunnels and
                      race for the same tiles; a team whose colour is used up retires with what it got
  picking  "front"  - only the front team of a tunnel can be launched
           "reach3" - any of the first 3 teams in a tunnel; jumping the queue costs 3 points per place
  colour   "any"    - any colour, no limit (the default): the same colour from every tunnel is fine
           "alternate" - optional: not the same colour as your previous launch (lifted if nothing else is launchable)
  scoring  "upkeep" - every busy slot beyond the first costs 0.25 points per game second
           "flat"   - no upkeep
  Always: adding a slot costs 25, returning a waiting team costs 10. Race: the first player to finish
  gets a bonus of 15% of the tile count and the match ends.
Score = tiles carried home by your ants + bonus - penalties.
"""
import random

from engine import Claim, Board

LAYOUTS = ["race", "shared"]
PICKING = ["front", "reach3"]
COLOUR = ["any", "alternate"]
SCORING = ["upkeep", "flat"]
ADD_SLOT_PENALTY = 25.0
RETURN_PENALTY = 10.0
SKIP_PENALTY = 3.0
UPKEEP_PER_SECOND = 0.25
FINISH_BONUS_SHARE = 0.15
REACH = 3
PLAYER_BASE = 100000


def shared_holes(board):
    row = board.R - 3
    return [row * board.C + board.C // 4, row * board.C + (3 * board.C) // 4]


def claim_run(board, opn, fam, limit, uid, hole):
    """Nearest-first claiming from `hole` (Game.claimRun with the hole as a parameter)."""
    if limit <= 0:
        return []
    N = board.N
    famarr = board.family
    nb = board.nb
    dist = [-1] * N
    parent = [-1] * N
    cand = bytearray(N)
    dist[hole] = 0
    buckets = [[hole]]
    claims = []
    d = 0
    done = False
    while d < len(buckets) and not done:
        for e in buckets[d]:
            if not opn[e]:
                if len(claims) >= limit:
                    done = True
                    break
                opn[e] = 1
                dist[e] = d
                path = []
                p = parent[e]
                while p != -1:
                    path.append(p)
                    p = parent[p]
                path.reverse()
                claims.append(Claim(uid, fam, e, path))
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
                        if len(buckets) == d + 1:
                            buckets.append([])
                        buckets[d + 1].append(n)
                elif famarr[n] == fam and not cand[n]:
                    cand[n] = 1
                    parent[n] = e
                    if len(buckets) == d + 1:
                        buckets.append([])
                    buckets[d + 1].append(n)
        d += 1
    return claims


class VTeam:
    __slots__ = ("uid", "player", "family", "quota", "remaining")

    def __init__(self, uid, player, family, quota):
        self.uid, self.player, self.family, self.quota, self.remaining = uid, player, family, quota, quota

    @property
    def tunnel(self):
        return (self.uid % PLAYER_BASE) // 1000


class VBoard:
    def __init__(self, board, holes):
        self.board = board
        self.opn = bytearray(1 if f < 0 else 0 for f in board.family)
        self.owner = [-1] * board.N
        self.left = [0] * 6
        for f in board.family:
            if f >= 0:
                self.left[f] += 1
        self.holes = holes            # player -> hole cell
        self.chambers = []            # waiting teams (both players on a shared board), arrival order
        self.claimed = [0, 0]

    def _run(self, t):
        c = claim_run(self.board, self.opn, t.family, t.remaining, t.uid, self.holes[t.player])
        for cl in c:
            self.owner[cl.tile] = t.player
            self.left[t.family] -= 1
            self.claimed[t.player] += 1
        t.remaining -= len(c)
        return c

    def resolve(self, incoming):
        events = []
        while True:
            progress = False
            if incoming is not None and incoming.remaining > 0:
                c = self._run(incoming)
                if c:
                    progress = True
                    events += c
            for t in self.chambers:
                if t.remaining == 0:
                    continue
                c = self._run(t)
                if c:
                    progress = True
                    events += c
            self.chambers = [t for t in self.chambers if t.remaining > 0]
            if not progress:
                break
        if incoming is not None and incoming.remaining > 0:
            self.chambers.append(incoming)
        return events

    def retire_exhausted(self):
        gone = [t for t in self.chambers if self.left[t.family] == 0]
        if gone:
            self.chambers = [t for t in self.chambers if self.left[t.family] > 0]
        return gone

    def done(self):
        return sum(self.left) == 0


class VPlayer:
    def __init__(self, index, tunnels, capacity):
        self.index = index
        self.queues = [[VTeam(index * PLAYER_BASE + q * 1000 + i, index, f, n) for i, (f, n) in enumerate(t)]
                       for q, t in enumerate(tunnels)]
        self.capacity = capacity
        self.added = 0
        self.returns = 0
        self.skips = 0
        self.launches = 0
        self.last_family = None
        self.upkeep = 0.0


class VMatch:
    def __init__(self, board_rows, tunnels, capacity, layout="race", picking="reach3", colour="any",
                 scoring="upkeep"):
        self.layout, self.picking, self.colour, self.scoring = layout, picking, colour, scoring
        if layout == "race":
            b0, b1 = Board(board_rows), Board(board_rows)
            self.boards = [VBoard(b0, {0: b0.hole}), VBoard(b1, {1: b1.hole})]
        else:
            b = Board(board_rows)
            h = shared_holes(b)
            self.boards = [VBoard(b, {0: h[0], 1: h[1]})]
        self.players = [VPlayer(0, tunnels, capacity), VPlayer(1, tunnels, capacity)]
        self.tile_count = self.boards[0].board.tile_count
        self.log = []                 # (player, action, detail)

    def bidx(self, p):
        return p if self.layout == "race" else 0

    def waiting(self, p):
        return [t for t in self.boards[self.bidx(p)].chambers if t.player == p]

    def reach(self):
        return REACH if self.picking == "reach3" else 1

    def candidates(self, p):
        pl = self.players[p]
        out = []
        for q, queue in enumerate(pl.queues):
            for d in range(min(self.reach(), len(queue))):
                out.append((q, d, queue[d]))
        return out

    def check(self, p, q, d):
        pl = self.players[p]
        if q >= len(pl.queues) or d >= len(pl.queues[q]):
            return False, "no team there"
        if d >= self.reach():
            return False, "out of reach"
        if len(self.waiting(p)) >= pl.capacity:
            return False, "every slot holds a waiting team"
        t = pl.queues[q][d]
        if self.colour == "alternate" and pl.last_family is not None and t.family == pl.last_family:
            if any(c.family != pl.last_family for _, _, c in self.candidates(p)):
                return False, "same colour as your last launch"
        return True, ""

    def launch(self, p, q, d):
        ok, why = self.check(p, q, d)
        assert ok, why
        pl = self.players[p]
        team = pl.queues[q].pop(d)
        pl.skips += d
        pl.launches += 1
        pl.last_family = team.family
        b = self.boards[self.bidx(p)]
        ev = b.resolve(team)
        self._after()
        self.log.append((p, "launch", (q, d, team.family, team.quota, len(ev))))
        return ev

    def _after(self):
        for b in self.boards:
            b.retire_exhausted()
        if self.layout == "shared":
            b = self.boards[0]
            for pl in self.players:
                pl.queues = [[t for t in queue if b.left[t.family] > 0] for queue in pl.queues]

    def add_slot(self, p):
        pl = self.players[p]
        pl.capacity += 1
        pl.added += 1
        self.log.append((p, "add_slot", None))

    def return_team(self, p, uid):
        b = self.boards[self.bidx(p)]
        t = next(t for t in b.chambers if t.uid == uid)
        b.chambers.remove(t)
        pl = self.players[p]
        pl.queues[t.tunnel].insert(0, t)
        pl.returns += 1
        self.log.append((p, "return", uid))

    def penalties(self, p):
        pl = self.players[p]
        pen = pl.added * ADD_SLOT_PENALTY + pl.returns * RETURN_PENALTY + pl.skips * SKIP_PENALTY
        if self.scoring == "upkeep":
            pen += pl.upkeep
        return pen

    def tiles(self, p):
        return self.boards[self.bidx(p)].claimed[p]

    def over(self):
        if self.layout == "race":
            return any(b.done() for b in self.boards)
        b = self.boards[0]
        if b.done():
            return True
        # nobody can ever move again (no queued teams, nothing waiting)
        return all(not any(pl.queues) and not self.waiting(i) for i, pl in enumerate(self.players))

    def final_scores(self):
        s = [self.tiles(p) - self.penalties(p) for p in (0, 1)]
        if self.layout == "race":
            for p in (0, 1):
                if self.boards[p].done():
                    s[p] += FINISH_BONUS_SHARE * self.tile_count
                    break
        return s


def play_random(match, rng, max_actions=5000, greedy=False):
    """Two careless (or greedy) players taking turns at random; blocked players add a slot or
    return a waiting team. Returns the number of actions taken."""
    n = 0
    while not match.over() and n < max_actions:
        n += 1
        p = rng.randrange(2)
        opts = [(q, d, t) for q, d, t in match.candidates(p) if match.check(p, q, d)[0]]
        if opts:
            if greedy:
                q, d, _ = min(opts, key=lambda o: (o[1], -o[2].quota))
            else:
                q, d, _ = rng.choice(opts)
            match.launch(p, q, d)
            continue
        w = match.waiting(p)
        if w and len(w) >= match.players[p].capacity:
            if rng.random() < 0.7:
                match.add_slot(p)
            else:
                match.return_team(p, rng.choice(w).uid)
    return n


def play_timed(match, rng, reaction=0.6, max_time=20000.0, stop_at=None, keep=None):
    """Two players acting in game time under the real-time slot rule (a slot is busy while a team
    waits or its ants still have tiles to pick up), with slot upkeep accrued per game second.
    Returns (final scores, finish time)."""
    from engine import Scheduler
    scheds = [Scheduler(b.board, "direct") for b in match.boards]
    t = 0.0
    next_act = [0.0, reaction / 2]
    move = 0

    def busy(p):
        b = match.bidx(p)
        waiting = {w.uid for w in match.waiting(p)}
        working = {u for u in scheds[b].busy_teams(t) if u // PLAYER_BASE == p and u not in waiting}
        return len(waiting) + len(working)

    def all_home(b):
        return all(tr.home <= t for tr in scheds[b].trips)

    dt = 0.1
    finished_at = None
    if keep is not None:
        keep["schedulers"] = scheds
    while t < max_time:
        if stop_at is not None and t >= stop_at:
            if keep is not None:
                keep["t"] = t
            return match.final_scores(), None
        for p in (0, 1):
            occ = busy(p)
            match.players[p].upkeep += UPKEEP_PER_SECOND * max(0, occ - 1) * dt
        for p in (0, 1):
            if t < next_act[p]:
                continue
            pl = match.players[p]
            occ = busy(p)
            opts = [(q, d, tm) for q, d, tm in match.candidates(p) if match.check(p, q, d)[0]]
            if opts and occ < pl.capacity:
                q, d, _ = rng.choice(opts)
                b = match.bidx(p)
                ev = match.launch(p, q, d)
                scheds[b].schedule(ev, move, t + 0.04)
                move += 1
                next_act[p] = t + reaction
            elif match.waiting(p) and len(match.waiting(p)) >= pl.capacity:
                match.add_slot(p)
                next_act[p] = t + reaction
        if match.layout == "race":
            done = [p for p in (0, 1) if match.boards[p].done() and all_home(p)]
            if done:
                finished_at = t
                break
        elif match.over() and all_home(0):
            finished_at = t
            break
        t += dt
    return match.final_scores(), finished_at
