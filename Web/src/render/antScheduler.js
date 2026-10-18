// Port of AntScheduler.swift: AntTrip, AntScheduler, AntPose and AntGeometry.
// Mirrors `Scheduler` in Tools/engine.py and `SwiftScheduler` in Tools/session_sim.py.
//
// AntTrip (plain object, a Swift struct — never mutated after scheduling):
//   { id, move, team, family, tone, color /*0xRRGGBB*/, tile, path: number[], depart, arrive,
//     pickupEnd, home, lane, pauses: {at, duration}[], style }
// AntPose (plain object):
//   { x, y, heading, scale, carrying, liftProgress, gaitDistance, moving }

import { hash32 } from '../core/util.js';
import { PathPlanner, PlannerScratch, PathStyle } from './pathPlanner.js';
import { LevelPalette } from './palette.js';

/** Swift `.rounded()` (to nearest, halves away from zero). */
function swiftRound(x) {
  const r = Math.trunc(x);
  return Math.abs(x - r) >= 0.5 ? r + Math.sign(x) : r;
}

/**
 * Turns claims into timed trips.
 *
 * All times are *game* seconds. The speed slider only changes how fast game time runs, so
 * ants already on the board slow down or speed up smoothly (no jumps, no restarted trips).
 *
 * Guarantees (verified by the Python tests and the in-app self-test):
 *  * a tile stays on the board until its own ant arrives beside it (`liftTime`),
 *  * no ant enters a cell until that cell's tile was lifted `pickup + margin` seconds earlier,
 *  * the hole releases at most one ant per `slot`; one team at most one per `teamGap`, so teams
 *    sent at nearly the same time interleave and genuinely work side by side.
 */
export class AntScheduler {
  static step = 1.0 / 4.0;   // game-seconds per cell (1x = 4 cells ≈ 2.5 body lengths per second)
  static slot = 0.18;        // hole release slot
  static teamGap = 0.36;     // minimum spacing between two ants of the same team
  static pickup = 0.9;       // grab, lift and turn around
  static margin = 0.2;       // gap before another ant may walk through a lifted cell

  /** init(board:palette:) */
  constructor(board, palette) {
    this.board = board;
    this.palette = palette;
    const lift = new Float64Array(board.count).fill(-Infinity);
    for (let i = 0; i < board.count; i++) if (board.family[i] >= 0) lift[i] = Infinity;
    /** Game time at which each tile is lifted (+inf = still on the board, -inf = ground). Read-only outside. */
    this.liftTime = lift;
    /** Game time at which each tile arrives in the nest (drives the gallery miniature). Read-only outside. */
    this.homeTime = lift.slice();
    this._slots = new Set();
    this._teamLast = new Map();
    /** @type {object[]} AntTrip list (read-only outside). */
    this.trips = [];
    this._nextID = 0;
    /** Route style for ants launched from now on (ants already walking keep their route). */
    this.style = 'direct';
    /** Latest route of each team that uses the scout-trail style (the trail its next ant follows). */
    this._teamTrail = new Map();
    /** Search buffers reused by every route this scheduler plans. */
    this._scratch = new PlannerScratch(board.count);
  }

  /** The concrete style for one new ant (resolves the random mixes). styleFor(team:tripID:) */
  styleFor(team, tripID) {
    switch (this.style) {
      case 'randomTeam':
        return PathStyle.teamMix[hash32(team, 31) % PathStyle.teamMix.length];
      case 'randomAnt':
        return PathStyle.antMix[hash32(tripID, 37) % PathStyle.antMix.length];
      default:
        return this.style;
    }
  }

  /** schedule(_ claims:, move:, now:) */
  schedule(claims, move, nowIn) {
    const step = AntScheduler.step;
    const now = Number.isFinite(nowIn) ? nowIn : 0;
    const board = this.board;
    const liftTime = this.liftTime;
    // bounded planning (see PathPlanner): at most maxStyledPerSend styled ants, spread evenly
    const stride = Math.max(1, Math.floor((claims.length + PathPlanner.maxStyledPerSend - 1) / PathPlanner.maxStyledPerSend));
    let spent = 0;
    for (let i = 0; i < claims.length; i++) {
      const c = claims[i];
      const tid = this._nextID;
      const chosen = i % stride === 0 ? this.styleFor(c.team, tid) : 'direct';
      const seed = hash32(tid, 0x5EED);
      let trail = null;
      if (chosen === 'scout') {
        const tr = this._teamTrail.get(c.team);
        if (tr !== undefined) trail = new Set(tr);
      }
      const budget = PathPlanner.antBudget(c.path.length, PathPlanner.budgetPerSend - spent);
      const plan = PathPlanner.plan(board, liftTime, c, chosen, seed, now, trail, budget, this._scratch);
      spent += plan.spent;
      if (plan.used === 'scout') this._teamTrail.set(c.team, plan.route);
      // defensive (crash report, 3 Oct): a route always has at least the hole; pauses are finite
      let route = plan.route;
      if (route.length === 0) route = c.path.length === 0 ? [board.hole] : c.path;
      const pauses = plan.pauses.filter(p => Number.isFinite(p.at) && Number.isFinite(p.duration) && p.duration >= 0);
      const l = route.length;
      let earliest = now;
      const last = this._teamLast.get(c.team);
      if (last !== undefined && Number.isFinite(last) && last + AntScheduler.teamGap > earliest) {
        earliest = last + AntScheduler.teamGap;
      }
      for (let k = 0; k < l; k++) {
        const ci = route[k];
        if (!(ci >= 0 && ci < liftTime.length)) continue;
        const req = liftTime[ci] + AntScheduler.pickup + AntScheduler.margin - (k - 0.5) * step;
        if (req > earliest) earliest = req;
      }
      // never convert inf/nan (or an absurd time) to Int
      if (!Number.isFinite(earliest) || earliest > now + 1000000) earliest = now;
      let s = Math.ceil(earliest / AntScheduler.slot - 1e-9);
      while (this._slots.has(s)) s += 1;
      this._slots.add(s);
      const depart = s * AntScheduler.slot;
      this._teamLast.set(c.team, depart);
      let pauseTotal = 0.0;
      for (const p of pauses) pauseTotal += p.duration;
      const arrive = depart + l * step + pauseTotal;
      const pickupEnd = arrive + AntScheduler.pickup;
      const home = pickupEnd + l * step;
      const t = c.tile;
      liftTime[t] = arrive;
      this.homeTime[t] = home;
      // outbound ants alternate between the two outer lanes by release slot; carriers come
      // home in the middle lane
      const jitter = (hash32(tid, 977) & 0xFF) / 255.0 * 0.3 - 0.15;
      const lane = (s % 2 === 0 ? 1.0 : -1.0) * (1.0 + jitter);
      const tone = board.tone[t];
      this.trips.push({
        id: tid, move, team: c.team, family: c.family, tone,
        color: LevelPalette.tone(this.palette, c.family, tone), tile: t, path: route,
        depart, arrive, pickupEnd, home, lane, pauses, style: plan.used,
      });
      this._nextID += 1;
    }
  }

  /** Mark claims as already finished (used when restoring a saved game). */
  completeInstantly(claims) {
    for (const c of claims) {
      this.liftTime[c.tile] = -1000000;
      this.homeTime[c.tile] = -1000000;
    }
  }

  /** Forget every trip of `move` and later; their tiles return to the board. undo(claims:fromMove:) */
  undo(claims, move) {
    for (const c of claims) {
      this.liftTime[c.tile] = Infinity;
      this.homeTime[c.tile] = Infinity;
    }
    const keep = [];
    const removedTeams = new Set();
    for (const t of this.trips) {
      if (t.move >= move) {
        this._slots.delete(swiftRound(t.depart / AntScheduler.slot));
        this.liftTime[t.tile] = Infinity;
        this.homeTime[t.tile] = Infinity;
        removedTeams.add(t.team);
      } else {
        keep.push(t);
      }
    }
    this.trips = keep;
    // recompute the release cadence of teams that lost trips; their trails start afresh
    for (const team of removedTeams) {
      this._teamTrail.delete(team);
      let m = null;
      for (const t of this.trips) if (t.team === team && (m === null || t.depart > m)) m = t.depart;
      if (m === null) this._teamLast.delete(team); else this._teamLast.set(team, m);
    }
  }

  /** Teams with at least one tile not yet picked up at game time `t` — they still occupy a slot.
   *  Swift [Int: Int] → Map(team uid → number of such trips). busyTeams(at:) */
  busyTeams(t) {
    const out = new Map();
    for (const trip of this.trips) {
      if (trip.pickupEnd > t) out.set(trip.team, (out.get(trip.team) || 0) + 1);
    }
    return out;
  }

  /** Game time at which team `uid` will have picked up every tile scheduled so far. slotFreeTime(team:) */
  slotFreeTime(uid) {
    let m = -Infinity;
    for (const trip of this.trips) if (trip.team === uid) m = Math.max(m, trip.pickupEnd);
    return m;
  }

  /** Drop trips that finished before `time`. Returns how many were removed. prune(before:) */
  prune(time) {
    const before = this.trips.length;
    let any = false;
    for (const t of this.trips) if (t.home < time) { any = true; break; }
    if (any) this.trips = this.trips.filter(t => !(t.home < time));
    return before - this.trips.length;
  }

  get isBusy() { return this.trips.length > 0; }
}

/** AntPose(x:y:heading:scale:carrying:liftProgress:gaitDistance:moving:) */
export function AntPose(x, y, heading, scale, carrying, liftProgress, gaitDistance, moving) {
  return { x, y, heading, scale, carrying, liftProgress, gaitDistance, moving };
}

/** Scratch for curve(): three nodes (x, y) at a time. */
const TMP = new Float64Array(12);

export class AntGeometry {
  /** Sideways distance between lanes (cells). Keeps every ant inside its path cells. */
  static laneWidth = 0.2;
  /** Carriers walk home close to the middle: this share of their outbound lane, on the other side. */
  static carrierLane = -0.15;

  /**
   * Path position u (cells) `elapsed` seconds after departure, and how long the ant has been
   * standing still if it is stopped to sniff. outbound(_:elapsed:) → { u, paused: number|null }
   */
  static outbound(trip, elapsed) {
    const step = AntScheduler.step;
    let e = elapsed;
    for (const p of trip.pauses) {
      const reach = p.at * step;
      if (e < reach) return { u: e / step, paused: null };
      if (e < reach + p.duration) return { u: p.at, paused: e - reach };
      e -= p.duration;
    }
    return { u: e / step, paused: null };
  }

  /** Node k in cell units (cell centres); the last node is the approach point beside the tile. → [x, y] */
  static node(trip, kIn, board, out = [0, 0], o = 0) {
    const l = trip.path.length;
    const t = trip.tile;
    const cols = board.cols;
    if (l === 0) {   // defensive: never index an empty route
      out[o] = t % cols + 0.5; out[o + 1] = ((t / cols) | 0) + 0.5;
      return out;
    }
    const k = Math.max(0, kIn);
    if (k < l) {
      const c = trip.path[k];
      out[o] = c % cols + 0.5; out[o + 1] = ((c / cols) | 0) + 0.5;
      return out;
    }
    const s = trip.path[l - 1];
    const sx = s % cols + 0.5, sy = ((s / cols) | 0) + 0.5;
    const tx = t % cols + 0.5, ty = ((t / cols) | 0) + 0.5;
    out[o] = sx + (tx - sx) * 0.22; out[o + 1] = sy + (ty - sy) * 0.22;
    return out;
  }

  /**
   * Position and tangent at parameter u in [0, L] where L = path.count. Corners are rounded
   * with quadratic curves that stay inside the corner cell. → [x, y, dx, dy] (written into `out`)
   */
  static curve(trip, uIn, board, out = [0, 0, 0, 0]) {
    const l = trip.path.length;
    const N = TMP;
    if (l === 0) {
      AntGeometry.node(trip, 0, board, N, 0);
      out[0] = N[0]; out[1] = N[1]; out[2] = 1; out[3] = 0;
      return out;
    }
    const u = Number.isFinite(uIn) ? Math.max(0, Math.min(l, uIn)) : l;
    if (u <= 0.5) {
      AntGeometry.node(trip, 0, board, N, 0);
      AntGeometry.node(trip, 1, board, N, 2);
      const mx = (N[0] + N[2]) / 2, my = (N[1] + N[3]) / 2;
      const tau = u / 0.5;
      out[0] = N[0] + (mx - N[0]) * tau; out[1] = N[1] + (my - N[1]) * tau;
      out[2] = N[2] - N[0]; out[3] = N[3] - N[1];
      return out;
    }
    if (u >= l - 0.5) {
      AntGeometry.node(trip, l - 1, board, N, 0);
      AntGeometry.node(trip, l, board, N, 2);
      const mx = (N[0] + N[2]) / 2, my = (N[1] + N[3]) / 2;
      const tau = (u - (l - 0.5)) / 0.5;
      out[0] = mx + (N[2] - mx) * tau; out[1] = my + (N[3] - my) * tau;
      out[2] = N[2] - N[0]; out[3] = N[3] - N[1];
      return out;
    }
    const j = Math.floor(u + 0.5);
    const tau = u - (j - 0.5);
    AntGeometry.node(trip, j - 1, board, N, 0);
    AntGeometry.node(trip, j, board, N, 2);
    AntGeometry.node(trip, j + 1, board, N, 4);
    const pjx = N[2], pjy = N[3];
    const ax = (N[0] + pjx) / 2, ay = (N[1] + pjy) / 2;
    const cx = (pjx + N[4]) / 2, cy = (pjy + N[5]) / 2;
    const o = 1 - tau;
    out[0] = o * o * ax + 2 * o * tau * pjx + tau * tau * cx;
    out[1] = o * o * ay + 2 * o * tau * pjy + tau * tau * cy;
    out[2] = 2 * o * (pjx - ax) + 2 * tau * (cx - pjx);
    out[3] = 2 * o * (pjy - ay) + 2 * tau * (cy - pjy);
    return out;
  }

  /** Length (cells) of the path from the hole to the approach point. */
  static length(trip) { return trip.path.length - 0.78; }

  /** Where the ant is at game time `t`, or null if it is underground. pose(_:at:board:) */
  static pose(trip, t, board, out = null) {
    if (!(Number.isFinite(t) && Number.isFinite(trip.depart) && Number.isFinite(trip.home) && trip.path.length > 0)) return null;
    if (t < trip.depart || t >= trip.home) return null;
    const p = out || AntPose(0, 0, 0, 1, false, 0, 0, false);
    const l = trip.path.length;
    const step = AntScheduler.step;
    const turnDistance = 0.9;   // legs "walk" through the 180° turn at the tile
    const C = CURVE;
    const smooth = AntGeometry.smooth;
    if (t < trip.arrive) {
      const ob = AntGeometry.outbound(trip, t - trip.depart);
      const paused = ob.paused;
      const u = Math.min(ob.u, l);
      AntGeometry.curve(trip, u, board, C);
      const taper = Math.min(1.0, 0.4 + 0.6 * Math.min(u, l - u));
      applyLane(C, trip.lane * AntGeometry.laneWidth * taper);
      let heading = Math.atan2(C[3], C[2]);
      if (paused !== null) {
        // sniffing: the head swings left and right while the ant stands still
        heading += 0.4 * Math.sin(paused / 0.8 * 2 * Math.PI) * smooth(paused / 0.2);
      }
      p.x = C[0]; p.y = C[1]; p.heading = heading; p.scale = u < 1.0 ? 0.3 + 0.7 * u : 1.0;
      p.carrying = false; p.liftProgress = 0; p.gaitDistance = u; p.moving = paused === null;
      return p;
    }
    if (t < trip.pickupEnd) {
      const q = (t - trip.arrive) / AntScheduler.pickup;
      AntGeometry.curve(trip, l, board, C);
      const face = Math.atan2(C[3], C[2]);
      const grab = 0.5;
      const turn = q < grab ? 0.0 : smooth((q - grab) / (1 - grab));
      // slide from the outer outbound lane toward the middle (carrier) lane while turning round
      const outLane = trip.lane * (1 - turn) + trip.lane * AntGeometry.carrierLane * turn;
      applyLane(C, outLane * AntGeometry.laneWidth * 0.4);
      const lift = Math.min(1.0, q / grab);
      p.x = C[0]; p.y = C[1]; p.heading = face + Math.PI * turn; p.scale = 1;
      p.carrying = q >= grab; p.liftProgress = smooth(lift); p.gaitDistance = l + turn * turnDistance; p.moving = q >= grab;
      return p;
    }
    const u = l - (t - trip.pickupEnd) / step;
    AntGeometry.curve(trip, u, board, C);
    const taper = Math.min(1.0, 0.4 + 0.6 * Math.min(Math.max(0, u), l - u));
    applyLane(C, trip.lane * AntGeometry.carrierLane * AntGeometry.laneWidth * taper);
    p.x = C[0]; p.y = C[1]; p.heading = Math.atan2(-C[3], -C[2]);
    p.scale = u < 1.0 ? 0.3 + 0.7 * Math.max(0, u) : 1.0;
    p.carrying = true; p.liftProgress = 1; p.gaitDistance = l + turnDistance + (l - u); p.moving = true;
    return p;
  }

  static smooth(x) {
    const t = Math.max(0, Math.min(1, x));
    return t * t * (3 - 2 * t);
  }
}

const CURVE = new Float64Array(4);

/** applyLane(&x, &y, dx, dy, off) on a [x, y, dx, dy] buffer. */
function applyLane(c, off) {
  const dx = c[2], dy = c[3];
  const len = Math.sqrt(dx * dx + dy * dy);
  if (len < 1e-6) return;
  c[0] += -dy / len * off;
  c[1] += dx / len * off;
}
