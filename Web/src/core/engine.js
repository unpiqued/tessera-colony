// Port of Engine.swift: the deterministic rules engine. Mirrors Tools/engine.py line for line;
// golden hashes in the level data let tests confirm all three implementations agree.
//
// Value semantics: Swift copies GameState on assignment. Here every state handed to history or
// mutated speculatively is copied with cloneState(); Team objects are never shared between states.

import { FNV_SEED, fnvMix } from './util.js';

/** A team that has left its tunnel. uid = tunnel * 1000 + position in that tunnel. */
export function makeTeam(uid, family, quota, remaining, held = false) {
  return { uid, family, quota, remaining, held };
}
export function teamTunnel(t) { return Math.floor(t.uid / 1000); }
export function cloneTeam(t) {
  return { uid: t.uid, family: t.family, quota: t.quota, remaining: t.remaining, held: t.held };
}

/** One tile claimed by one ant: path runs from the hole to the open cell beside the tile. */
export function makeClaim(team, family, tile, path) { return { team, family, tile, path }; }

/** TeamSpec: { family, quota } */
export function TeamSpec(family, quota) { return { family, quota }; }

export function cloneState(s) {
  return {
    open: s.open.slice(),
    heads: s.heads.slice(),
    chambers: s.chambers.map(cloneTeam),
    capacity: s.capacity,
    added: s.added,
    jammed: s.jammed ? cloneTeam(s.jammed) : null,
    cleared: s.cleared,
    returned: s.returned.map(a => a.map(cloneTeam)),
  };
}

export class Game {
  static addChamberMove = 100;
  static recallJammedMove = 199;
  static recallBase = 200;   // + chamber index
  static holdBase = 300;     // legacy: + tunnel index
  static releaseBase = 400;  // + chamber index

  static isAssist(code) { return code >= Game.addChamberMove && code < Game.holdBase; }

  constructor(level, board, capacity) {
    this.level = level;
    this.board = board;
    this.tunnels = level.tunnels;
    this.state = {
      open: board.initialOpen(),
      heads: new Array(level.tunnels.length).fill(0),
      chambers: [],
      capacity,
      added: 0,
      jammed: null,
      cleared: 0,
      returned: level.tunnels.map(() => []),
    };
    this.history = [];
    this.moves = [];
    this.moveClaims = [];
  }

  // MARK: - Core rules

  /** One claiming pass for a single team (nearest-first BFS from the hole). Mutates st. */
  static claimRun(board, st, family, limit, teamUID) {
    if (limit <= 0) return [];
    const n = board.count;
    const fam = board.family;
    const nb = board.neighbours;
    const open = st.open;
    const dist = new Int32Array(n).fill(-1);
    const parent = new Int32Array(n).fill(-1);
    const cand = new Uint8Array(n);
    const claims = [];
    dist[board.hole] = 0;
    const buckets = [[board.hole]];
    let d = 0;
    let done = false;
    while (d < buckets.length && !done) {
      const cur = buckets[d];
      for (let ci = 0; ci < cur.length; ci++) {
        const e = cur[ci];
        if (!open[e]) {
          if (claims.length >= limit) { done = true; break; }
          open[e] = 1;
          st.cleared += 1;
          dist[e] = d;
          const path = [];
          let p = parent[e];
          while (p !== -1) { path.push(p); p = parent[p]; }
          path.reverse();
          claims.push({ team: teamUID, family, tile: e, path });
          if (claims.length >= limit) { done = true; break; }
        }
        const base = e * 4;
        for (let k = 0; k < 4; k++) {
          const m = nb[base + k];
          if (m < 0) continue;
          if (open[m]) {
            if (dist[m] < 0) {
              dist[m] = d + 1;
              parent[m] = e;
              if (buckets.length === d + 1) buckets.push([]);
              buckets[d + 1].push(m);
            }
          } else if (fam[m] === family && !cand[m]) {
            cand[m] = 1;
            parent[m] = e;
            if (buckets.length === d + 1) buckets.push([]);
            buckets[d + 1].push(m);
          }
        }
      }
      d += 1;
    }
    return claims;
  }

  /** Passes over [incoming] + chambers until nobody can claim; then park or jam the incoming team. */
  static resolve(board, st, incoming) {
    const events = [];
    const inc = incoming; // owned by st's caller; mutated in place
    for (;;) {
      let progress = false;
      if (inc && inc.remaining > 0) {
        const c = Game.claimRun(board, st, inc.family, inc.remaining, inc.uid);
        if (c.length > 0) {
          progress = true;
          inc.remaining -= c.length;
          for (const x of c) events.push(x);
        }
      }
      for (let idx = 0; idx < st.chambers.length; idx++) {
        const t = st.chambers[idx];
        if (t.remaining === 0 || t.held) continue;
        const c = Game.claimRun(board, st, t.family, t.remaining, t.uid);
        if (c.length > 0) {
          progress = true;
          t.remaining -= c.length;
          for (const x of c) events.push(x);
        }
      }
      st.chambers = st.chambers.filter(t => t.remaining !== 0);
      if (!progress) break;
    }
    if (inc && inc.remaining > 0) {
      if (st.chambers.length < st.capacity) st.chambers.push(inc);
      else st.jammed = inc;
    }
    return events;
  }

  static front(tunnels, state, q) {
    const ret = state.returned[q];
    if (ret.length > 0) {
      const t = ret[ret.length - 1];
      return { family: t.family, need: t.remaining, uid: t.uid, isReturned: true };
    }
    const h = state.heads[q];
    if (h >= tunnels[q].length) return null;
    const s = tunnels[q][h];
    return { family: s.family, need: s.quota, uid: q * 1000 + h, isReturned: false };
  }

  static applyDispatch(board, tunnels, st, q) {
    let incoming;
    if (st.returned[q].length > 0) {
      incoming = st.returned[q].pop();
    } else {
      const spec = tunnels[q][st.heads[q]];
      incoming = makeTeam(q * 1000 + st.heads[q], spec.family, spec.quota, spec.quota);
      st.heads[q] += 1;
    }
    return Game.resolve(board, st, incoming);
  }

  // MARK: - Queries

  front(q) { return Game.front(this.tunnels, this.state, q); }

  /** The next teams behind the front one (returned teams first, then the tunnel's own queue). */
  upcoming(q, count) {
    const out = [];
    const ret = this.state.returned[q];
    if (ret.length > 1) {
      for (let i = ret.length - 2; i >= 0; i--) out.push({ family: ret[i].family, quota: ret[i].remaining });
    }
    let h = this.state.heads[q] + (ret.length === 0 ? 1 : 0);
    while (out.length < count && h < this.tunnels[q].length) {
      out.push(this.tunnels[q][h]);
      h += 1;
    }
    return out.slice(0, count);
  }

  remainingInTunnel(q) { return this.tunnels[q].length - this.state.heads[q] + this.state.returned[q].length; }

  get isJammed() { return this.state.jammed !== null; }
  get isWon() { return this.state.cleared === this.board.tileCount; }
  get canUndo() { return this.history.length > 0; }

  canDispatch(q) {
    return this.state.jammed === null && this.front(q) !== null && this.state.chambers.length < this.state.capacity;
  }

  deadlocked(busyOutsideSlots) {
    if (this.isWon || busyOutsideSlots > 0) return false;
    if (this.state.chambers.some(t => t.held)) return false;
    let anyFront = false;
    for (let q = 0; q < this.tunnels.length; q++) if (this.front(q) !== null) { anyFront = true; break; }
    return this.state.chambers.length >= this.state.capacity && (anyFront || this.state.chambers.length > 0);
  }

  // MARK: - Player actions

  dispatch(q) {
    if (!this.canDispatch(q)) return [];
    this.history.push(this.state);
    const st = cloneState(this.state);
    const ev = Game.applyDispatch(this.board, this.tunnels, st, q);
    this.state = st;
    this._record(q, ev);
    return ev;
  }

  _record(code, claims) {
    this.moves.push(code);
    this.moveClaims.push(claims);
  }

  static _unjam(st) {
    if (st.jammed && st.chambers.length < st.capacity) {
      st.chambers.push(st.jammed);
      st.jammed = null;
    }
  }

  addChamber() {
    this.history.push(this.state);
    const st = cloneState(this.state);
    st.capacity += 1;
    st.added += 1;
    Game._unjam(st);
    this.state = st;
    this._record(Game.addChamberMove, []);
  }

  canRecall(index) { return index >= 0 && index < this.state.chambers.length; }

  canHold(q) {
    return this.state.jammed === null && this.front(q) !== null && this.state.chambers.length < this.state.capacity;
  }

  /** Legacy (Hold was removed): only runs when an old save is replayed. */
  hold(q) {
    if (!this.canHold(q)) return;
    this.history.push(this.state);
    const st = cloneState(this.state);
    let t;
    if (st.returned[q].length > 0) {
      t = st.returned[q].pop();
    } else {
      const spec = this.tunnels[q][st.heads[q]];
      t = makeTeam(q * 1000 + st.heads[q], spec.family, spec.quota, spec.quota);
      st.heads[q] += 1;
    }
    t.held = true;
    st.chambers.push(t);
    this.state = st;
    this._record(Game.holdBase + q, []);
  }

  canRelease(index) {
    return this.state.jammed === null && index >= 0 && index < this.state.chambers.length && this.state.chambers[index].held;
  }

  static applyRelease(board, st, index) {
    const t = st.chambers.splice(index, 1)[0];
    t.held = false;
    return Game.resolve(board, st, t);
  }

  release(index) {
    if (!this.canRelease(index)) return [];
    this.history.push(this.state);
    const st = cloneState(this.state);
    const ev = Game.applyRelease(this.board, st, index);
    this.state = st;
    this._record(Game.releaseBase + index, ev);
    return ev;
  }

  /** Recovery: send a waiting team back to the front of its tunnel, freeing its chamber. */
  recall(index) {
    if (!this.canRecall(index)) return;
    this.history.push(this.state);
    const st = cloneState(this.state);
    const t = st.chambers.splice(index, 1)[0];
    t.held = false;
    st.returned[teamTunnel(t)].push(t);
    Game._unjam(st);
    this.state = st;
    this._record(Game.recallBase + index, []);
  }

  /** Legacy recovery: the blocked team steps back into its tunnel. */
  recallJammed() {
    const j = this.state.jammed;
    if (!j) return;
    this.history.push(this.state);
    const st = cloneState(this.state);
    const jt = st.jammed;
    st.jammed = null;
    st.returned[teamTunnel(jt)].push(jt);
    this.state = st;
    this._record(Game.recallJammedMove, []);
  }

  /** Applies a stored move code; returns false if it is not legal here. */
  apply(code) {
    if (code === Game.addChamberMove) {
      this.addChamber();
    } else if (code === Game.recallJammedMove) {
      if (this.state.jammed === null) return false;
      this.recallJammed();
    } else if (code >= Game.releaseBase) {
      if (!this.canRelease(code - Game.releaseBase)) return false;
      this.release(code - Game.releaseBase);
    } else if (code >= Game.holdBase) {
      if (!(code - Game.holdBase < this.tunnels.length && this.canHold(code - Game.holdBase))) return false;
      this.hold(code - Game.holdBase);
    } else if (code >= Game.recallBase) {
      if (!this.canRecall(code - Game.recallBase)) return false;
      this.recall(code - Game.recallBase);
    } else {
      if (!(code >= 0 && code < this.tunnels.length && this.canDispatch(code))) return false;
      this.dispatch(code);
    }
    return true;
  }

  /** Returns the claims of the undone move (so their tiles can be restored visually), or null. */
  undo() {
    if (this.history.length === 0) return null;
    this.state = this.history.pop();
    this.moves.pop();
    return this.moveClaims.pop();
  }

  scout(q) {
    const fr = this.front(q);
    if (!fr || this.state.jammed !== null) return null;
    const st = cloneState(this.state);
    const ev = Game.applyDispatch(this.board, this.tunnels, st, q);
    const own = ev.filter(c => c.team === fr.uid).map(c => c.tile);
    return {
      tunnel: q, family: fr.family, quota: fr.need, ownTiles: own,
      fits: own.length === fr.need, wouldJam: st.jammed !== null, totalClaims: ev.length,
    };
  }

  // MARK: - Hashes (shared with the Python reference model)

  static stateHash(board, st) {
    let h = FNV_SEED;
    for (let i = 0; i < board.count; i++) {
      if (st.open[i] && board.family[i] >= 0) h = fnvMix(h, i);
    }
    for (const x of st.heads) h = fnvMix(h, x);
    for (const t of st.chambers) {
      h = fnvMix(h, t.uid);
      h = fnvMix(h, t.remaining);
      h = fnvMix(h, t.held ? 1 : 0);
    }
    for (const stack of st.returned) {
      for (const t of stack) {
        h = fnvMix(h, t.uid);
        h = fnvMix(h, t.remaining);
      }
    }
    h = fnvMix(h, st.capacity);
    h = fnvMix(h, st.jammed === null ? 0 : 1);
    return h;
  }

  get stateHash() { return Game.stateHash(this.board, this.state); }

  static claimsHash(lists) {
    let h = FNV_SEED;
    for (const list of lists) {
      for (const c of list) {
        h = fnvMix(h, c.tile);
        h = fnvMix(h, c.path.length);
      }
    }
    return h;
  }

  /** Rebuild a game from a saved move list. Returns null if any move is no longer legal. */
  static replay(level, board, capacity, moves) {
    const g = new Game(level, board, capacity);
    for (const m of moves) if (!g.apply(m)) return null;
    return g;
  }
}
