"""Prototype: a 'veil' (hidden section) that lifts after N tiles have been removed anywhere.

Rule (deterministic, a pure function of the state): a veiled tile cannot be claimed while
st.cleared < threshold. Tiles always block walking, so nothing else changes. Same seeds as the
shipped levels, so the plain builds reproduce the shipped levels exactly; the veiled builds re-plan
the tunnels with the same designer and are measured with the same bots.
Research prototype for Docs/PLAN.md, 'Harder boards' (5 Oct 2026); not used by the app or the level build.
Usage: python3 veil_proto.py OUT.json wildIceberg:plain wildIceberg:lowside wildIceberg:centre ..."""
import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from multiprocessing import Pool
import engine as E
import generate_levels as G
from art_packs import COLLECTION, collection_art


def claim_run(self, st, fam, limit, team_uid):
    b = self.board
    if limit <= 0:
        return []
    veil_of = getattr(b, "veil_of", None)
    thr = getattr(b, "veil_thr", None)
    N = b.N; opn = st.open; famarr = b.family; nb = b.nb
    dist = [-1] * N; parent = [-1] * N; cand = bytearray(N)
    dist[b.hole] = 0
    buckets = [[b.hole]]
    claims = []
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
                claims.append(E.Claim(team_uid, fam, e, path))
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
                elif famarr[n] == fam and not cand[n] and not (veil_of is not None and veil_of[n] >= 0
                                                               and st.cleared < thr[veil_of[n]]):
                    cand[n] = 1
                    parent[n] = e
                    if nxt is None:
                        if len(buckets) == d + 1:
                            buckets.append([])
                        nxt = buckets[d + 1]
                    nxt.append(n)
        d += 1
    return claims


E.Game.claim_run = claim_run
VEIL = {}


class VeilBoard(E.Board):
    def __init__(self, rows):
        super().__init__(rows)
        spec = VEIL.get(tuple(rows))
        if spec:
            (x0, y0, x1, y1), frac = spec
            self.veil_of = [-1] * self.N
            n = 0
            for y in range(y0, y1):
                for x in range(x0, x1):
                    i = (y + E.MARGIN_T) * self.C + (x + E.MARGIN_L)
                    if self.family[i] >= 0:
                        self.veil_of[i] = 0
                        n += 1
            self.veil_thr = [int(round(frac * self.tile_count))]
            self.veil_tiles = n


G.Board = VeilBoard
specs = {s[0]: (p[0], p[2], s) for p in COLLECTION for s in p[3]}


def region(rows, variant):
    H, W = len(rows), len(rows[0])
    if variant == "plain":
        return None
    if variant == "lowside":     # bottom-left quarter of the art (close to the hill), lifts after 30% removed
        return ((0, H // 2, W // 2, H), 0.30)
    if variant == "centre":      # the middle third (a band across the picture), lifts after 50% removed
        return ((0, H // 3, W, 2 * H // 3), 0.50)
    raise ValueError(variant)


def run(arg):
    key, variant = arg.split(":")
    pack, module, s = specs[key]
    _, title, sub, scene, seed, tier = s
    rows = collection_art(module, scene)
    VEIL.clear()                 # pool workers are reused: never carry a veil over to the next build
    r = region(rows, variant)
    if r:
        VEIL[tuple(rows)] = r
    t0 = time.time()
    s_ = seed * 101 + 7 if tier == "gentle" else seed * 131 + 11
    lv, rep = G.job(("pack", tier, pack, key, title, sub, s_, rows))
    b = VeilBoard(rows)
    tun = [[tuple(x) for x in q] for q in lv["tunnels"]]
    look = [G.planner_win(b, tun, c) for c in (lv["gentle"], lv["classic"], lv["expert"])]
    out = dict(key=key, variant=variant, veil_tiles=getattr(b, "veil_tiles", 0), tiles=b.tile_count,
               threshold=getattr(b, "veil_thr", [0])[0], slots=[lv["gentle"], lv["classic"], lv["expert"]],
               careless=lv["careless"], greedy=lv["greedy"], rating=rep["rating_gentle_classic_expert"],
               lookahead=look, teams=rep["teams"], seconds=round(time.time() - t0))
    print(json.dumps(out), flush=True)
    return out


if __name__ == "__main__":
    with Pool(2) as p:
        res = p.map(run, sys.argv[2:], chunksize=1)
    json.dump(res, open(sys.argv[1], "w"), indent=1)
