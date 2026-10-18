// Port of VersusEngine.swift: two-player versus mode, the rules. Mirror of Tools/versus.py
// (test/versus.test.js replays scripted matches from tools/versus_fixtures.py claim by claim).
//
// Enums are frozen objects of raw values with helpers taking the value (VersusLayout.title(l)).
// VersusRules is a plain object { layout, picking, colour, scoring, difficulty } made by
// VersusRules(fields?); its Swift statics hang off the function (VersusRules.addSlotPenalty …)
// and the computed reachDepth is VersusRules.reachDepth(rules).
// Claims have the engine's shape { team, family, tile, path: number[] }.

import { Board } from './board.js';
import { Difficulty } from './level.js';

function rawEnum(cases, info, extra = {}) {
  const o = { allCases: Object.freeze(cases.slice()) };
  for (const c of cases) o[c] = c;
  o.isValid = v => typeof v === 'string' && cases.includes(v);
  o.id = v => v;
  o.title = v => info[v].title;
  o.blurb = v => info[v].blurb;
  return Object.freeze(Object.assign(o, extra));
}

/** race: split screen, each player has their own copy. shared: one mosaic, two hills. */
export const VersusLayout = rawEnum(['race', 'shared'], {
  race: {
    title: 'Race',
    blurb: 'Split screen. Each of you clears your own copy of the mosaic; the first to finish gets a bonus and ends the match.',
  },
  shared: {
    title: 'Shared board',
    blurb: 'One mosaic, two ant hills. You both have the same tunnels and compete for the same tiles; a team whose colour runs out keeps what it got.',
  },
});

export const VersusPicking = rawEnum(['front', 'reach3'], {
  front: { title: 'Front team only', blurb: 'Only the team at the front of a tunnel can be launched.' },
  reach3: {
    title: 'Reach 3',
    blurb: 'Launch any of the first three teams in a tunnel; jumping the queue costs 3 points per place.',
  },
});

export const VersusColourRule = rawEnum(['any', 'alternate'], {
  any: {
    title: 'Any colour',
    blurb: 'No colour limit: launch the same colour from every tunnel and fill all your slots with it if you like.',
  },
  alternate: {
    title: 'No colour twice in a row',
    blurb: "Optional extra rule: you can't launch the same colour as your previous launch (unless nothing else is left to launch).",
  },
});

export const VersusSlotScoring = rawEnum(['upkeep', 'flat'], {
  upkeep: {
    title: 'Slot upkeep',
    blurb: 'Every busy slot beyond the first costs 0.25 points per second (game time). Adding a slot costs 25.',
  },
  flat: { title: 'Flat slot cost', blurb: 'Busy slots are free; adding a slot costs 25.' },
});

/**
 * The options of a match. VersusRules() gives the defaults (race, reach 3, any colour — the colour
 * rule is an optional extra —, slot upkeep, classic); VersusRules({ layout: 'shared' }) overrides.
 */
export function VersusRules(fields = {}) {
  return {
    layout: fields.layout ?? 'race',
    picking: fields.picking ?? 'reach3',
    colour: fields.colour ?? 'any',
    scoring: fields.scoring ?? 'upkeep',
    difficulty: fields.difficulty ?? 'classic',
  };
}

VersusRules.addSlotPenalty = 25.0;
VersusRules.returnPenalty = 10.0;
VersusRules.skipPenalty = 3.0;
VersusRules.upkeepPerSecond = 0.25;
VersusRules.finishBonusShare = 0.15;
VersusRules.reach = 3;
/** Team uid = player * playerBase + tunnel * 1000 + position in the original tunnel. */
VersusRules.playerBase = 100000;
/** Swift's computed `reachDepth`. */
VersusRules.reachDepth = rules => (rules.picking === 'reach3' ? VersusRules.reach : 1);
VersusRules.equals = (a, b) => a.layout === b.layout && a.picking === b.picking && a.colour === b.colour
  && a.scoring === b.scoring && a.difficulty === b.difficulty;
VersusRules.copy = r => VersusRules(r);
/** Strict decoding like Swift's synthesized Codable: every key present with a known value, else null. */
VersusRules.decode = o => {
  if (!o || typeof o !== 'object') return null;
  if (!VersusLayout.isValid(o.layout) || !VersusPicking.isValid(o.picking) || !VersusColourRule.isValid(o.colour)
    || !VersusSlotScoring.isValid(o.scoring) || !Difficulty.isValid(o.difficulty)) return null;
  return VersusRules(o);
};

/** One team of one player. uid = player * playerBase + tunnel * 1000 + position. */
export class VTeam {
  constructor(uid, player, family, quota, remaining) {
    this.uid = uid;
    this.player = player;
    this.family = family;
    this.quota = quota;
    this.remaining = remaining;
  }

  get tunnel() { return Math.floor((this.uid % VersusRules.playerBase) / 1000); }

  copy() { return new VTeam(this.uid, this.player, this.family, this.quota, this.remaining); }

  static equals(a, b) {
    return a.uid === b.uid && a.player === b.player && a.family === b.family && a.quota === b.quota
      && a.remaining === b.remaining;
  }
}

/** One mosaic in a match (race: one per player; shared: one for both). */
export class VersusBoard {
  /**
   * @param {Board} board
   * @param {Object<number, number>} holes hill hole per player on this board, e.g. { 0: hole }
   */
  constructor(board, holes) {
    this.board = board;
    /** Uint8Array per cell (1 = open). */
    this.open = board.initialOpen();
    /** Which player claimed each tile (-1 = nobody yet). */
    this.owner = new Int8Array(board.count).fill(-1);
    /** Unclaimed tiles per colour family. */
    const l = new Array(8).fill(0);
    for (let i = 0; i < board.count; i++) {
      const f = board.family[i];
      if (f >= 0) l[f] += 1;
    }
    this.left = l;
    this.holes = holes;
    /** Teams waiting in slots on this board (both players on a shared board), in arrival order. */
    this.chambers = [];
    this.claimed = [0, 0];
  }

  get isCleared() { return this.left.reduce((a, b) => a + b, 0) === 0; }

  /** Nearest-first claiming from the team's hill (Game.claimRun with the hole as a parameter). Mutates t. */
  _claimRun(t) {
    const limit = t.remaining;
    if (limit <= 0) return [];
    const board = this.board;
    const hole = this.holes[t.player] ?? board.hole;
    const n = board.count;
    const fam = board.family;
    const nb = board.neighbours;
    const open = this.open;
    const dist = new Int32Array(n).fill(-1);
    const parent = new Int32Array(n).fill(-1);
    const cand = new Uint8Array(n);
    const claims = [];
    dist[hole] = 0;
    const buckets = [[hole]];
    let d = 0;
    let done = false;
    while (d < buckets.length && !done) {
      const cur = buckets[d];
      for (let ci = 0; ci < cur.length; ci++) {
        const e = cur[ci];
        if (!open[e]) {
          if (claims.length >= limit) { done = true; break; }
          open[e] = 1;
          dist[e] = d;
          const path = [];
          let p = parent[e];
          while (p !== -1) { path.push(p); p = parent[p]; }
          path.reverse();
          claims.push({ team: t.uid, family: t.family, tile: e, path });
          this.owner[e] = t.player;
          this.left[t.family] -= 1;
          this.claimed[t.player] += 1;
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
          } else if (fam[m] === t.family && !cand[m]) {
            cand[m] = 1;
            parent[m] = e;
            if (buckets.length === d + 1) buckets.push([]);
            buckets[d + 1].push(m);
          }
        }
      }
      d += 1;
    }
    t.remaining -= claims.length;
    return claims;
  }

  /** Passes over [incoming] + waiting teams until nobody can claim; an unfinished incoming team waits. */
  resolve(incoming) {
    const events = [];
    const inc = incoming ?? null;
    for (;;) {
      let progress = false;
      if (inc && inc.remaining > 0) {
        const c = this._claimRun(inc);
        if (c.length > 0) {
          progress = true;
          for (const x of c) events.push(x);
        }
      }
      for (let idx = 0; idx < this.chambers.length; idx++) {
        const t = this.chambers[idx];
        if (t.remaining === 0) continue;
        const c = this._claimRun(t);
        if (c.length > 0) {
          progress = true;
          for (const x of c) events.push(x);
        }
      }
      this.chambers = this.chambers.filter(t => t.remaining !== 0);
      if (!progress) break;
    }
    if (inc && inc.remaining > 0) this.chambers.push(inc);
    return events;
  }

  /** Waiting teams whose colour has no tiles left retire with what they got (shared board). */
  retireExhausted() {
    const gone = this.chambers.filter(t => this.left[t.family] === 0);
    if (gone.length > 0) this.chambers = this.chambers.filter(t => this.left[t.family] !== 0);
    return gone;
  }

  /** Swift removeChamber(uid:) — the removed team, or null. */
  removeChamber(uid) {
    const i = this.chambers.findIndex(t => t.uid === uid);
    if (i < 0) return null;
    return this.chambers.splice(i, 1)[0];
  }
}

export class VersusPlayer {
  /** @param {{family:number, quota:number}[][]} tunnels TeamSpec queues */
  constructor(index, tunnels, capacity) {
    this.index = index;
    this.capacity = capacity;
    this.added = 0;
    this.returns = 0;
    this.skips = 0;
    this.launches = 0;
    /** Family of the previous launch, or null. */
    this.lastFamily = null;
    /** Slot upkeep accrued so far (points), added by the controller in game time. */
    this.upkeep = 0.0;
    /** Tunnel queues, front first. */
    this.queues = tunnels.map((t, q) => t.map((spec, i) =>
      new VTeam(index * VersusRules.playerBase + q * 1000 + i, index, spec.family, spec.quota, spec.quota)));
  }
}

export class VersusMatch {
  /** @param level a LevelDefinition (art, tunnels, chambers(d)); @param rules VersusRules */
  constructor(level, rules) {
    this.rules = rules;
    this.level = level;
    const cap = level.chambers(rules.difficulty);
    if (rules.layout === 'race') {
      const b0 = new Board(level.art), b1 = new Board(level.art);
      this.boards = [new VersusBoard(b0, { 0: b0.hole }), new VersusBoard(b1, { 1: b1.hole })];
    } else {
      const b = new Board(level.art);
      const h = VersusMatch.sharedHoles(b);
      this.boards = [new VersusBoard(b, { 0: h[0], 1: h[1] })];
    }
    this.players = [new VersusPlayer(0, level.tunnels, cap), new VersusPlayer(1, level.tunnels, cap)];
    this.tileCount = this.boards[0].board.tileCount;
  }

  /** Two hills on a shared board: a quarter and three quarters of the way across the bottom margin. */
  static sharedHoles(b) {
    const row = b.rows - 3;
    return [row * b.cols + Math.floor(b.cols / 4), row * b.cols + Math.floor((3 * b.cols) / 4)];
  }

  boardIndex(p) { return this.rules.layout === 'race' ? p : 0; }
  /** Swift board(of:) */
  board(p) { return this.boards[this.boardIndex(p)]; }
  waiting(p) { return this.board(p).chambers.filter(t => t.player === p); }
  tiles(p) { return this.board(p).claimed[p]; }

  /** Teams within reach: [{ tunnel, depth, team }]. */
  candidates(p) {
    const out = [];
    const reach = VersusRules.reachDepth(this.rules);
    this.players[p].queues.forEach((queue, q) => {
      for (let d = 0; d < Math.min(reach, queue.length); d++) out.push({ tunnel: q, depth: d, team: queue[d] });
    });
    return out;
  }

  /** Null if the launch is allowed, otherwise the reason (the real-time slot check is the controller's). */
  refusal(p, q, d) {
    const pl = this.players[p];
    if (!(q >= 0 && q < pl.queues.length && d >= 0 && d < pl.queues[q].length)) return 'No team there.';
    if (d >= VersusRules.reachDepth(this.rules)) return 'Out of reach.';
    if (this.waiting(p).length >= pl.capacity) return 'Every slot holds a waiting team.';
    const t = pl.queues[q][d];
    if (this.rules.colour === 'alternate' && pl.lastFamily !== null && t.family === pl.lastFamily) {
      const last = pl.lastFamily;
      if (this.candidates(p).some(c => c.team.family !== last)) return 'Not the same colour twice in a row.';
    }
    return null;
  }

  canLaunch(p, q, d) { return this.refusal(p, q, d) === null; }

  launch(p, q, d) {
    if (!this.canLaunch(p, q, d)) return [];
    const pl = this.players[p];
    const team = pl.queues[q].splice(d, 1)[0];
    pl.skips += d;
    pl.launches += 1;
    pl.lastFamily = team.family;
    const ev = this.board(p).resolve(team);
    this._afterAction();
    return ev;
  }

  _afterAction() {
    for (const b of this.boards) b.retireExhausted();
    if (this.rules.layout === 'shared') {
      const b = this.boards[0];
      for (const pl of this.players) {
        pl.queues = pl.queues.map(queue => queue.filter(t => b.left[t.family] > 0));
      }
    }
  }

  addSlot(p) {
    this.players[p].capacity += 1;
    this.players[p].added += 1;
  }

  /**
   * Returns a waiting team to the front of its tunnel, opening its slot. (As in Swift, a uid that
   * belongs to the other player's team on a shared board removes that team without returning it.)
   */
  returnTeam(p, uid) {
    const t = this.board(p).removeChamber(uid);
    if (!t || t.player !== p) return;
    const pl = this.players[p];
    pl.queues[t.tunnel].unshift(t);
    pl.returns += 1;
  }

  penalties(p) {
    const pl = this.players[p];
    let pen = pl.added * VersusRules.addSlotPenalty + pl.returns * VersusRules.returnPenalty
      + pl.skips * VersusRules.skipPenalty;
    if (this.rules.scoring === 'upkeep') pen += pl.upkeep;
    return pen;
  }

  /** Nobody can ever move again (shared board: no queued teams and nothing waiting). */
  get isStalemate() {
    return [0, 1].every(p => this.players[p].queues.every(q => q.length === 0) && this.waiting(p).length === 0);
  }
}
