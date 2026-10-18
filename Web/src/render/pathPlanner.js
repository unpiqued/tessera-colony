// Port of PathPlanner.swift: how newly launched ants choose their route to a tile.
// Purely visual: which tiles a team claims never changes. Mirror of `plan_route` in Tools/engine.py
// (except that the Swift code — and this port — does not round sniff pauses to 3 decimals).

import { hash32 } from '../core/util.js';

const INFO = Object.freeze({
  direct: Object.freeze({ title: 'Direct', blurb: 'The shortest route, in straight runs.', systemImage: 'arrow.up.right' }),
  natural: Object.freeze({ title: 'Natural', blurb: 'Just as short, but it follows the straight line to the tile.', systemImage: 'line.diagonal' }),
  curious: Object.freeze({ title: 'Curious', blurb: 'Each ant wanders a little, and about a third stop to sniff on the way.', systemImage: 'scribble' }),
  wall: Object.freeze({ title: 'Wall-hugger', blurb: 'Ants walk along the edge of the mosaic instead of cutting across open ground.', systemImage: 'square.dashed' }),
  scout: Object.freeze({ title: 'Scout trail', blurb: "A team's first ant explores and leaves a fading trail in its colour; the others follow and straighten it.", systemImage: 'point.topleft.down.curvedto.point.bottomright.up' }),
  randomTeam: Object.freeze({ title: 'Random per team', blurb: 'Each team picks one of the styles when it is sent.', systemImage: 'shuffle' }),
  randomAnt: Object.freeze({ title: 'Random per ant', blurb: 'Every ant picks Direct, Natural, Curious or Wall-hugger for itself.', systemImage: 'dice' }),
});

/** Per-style computed properties: PATH_STYLE_INFO[style].title / .blurb / .systemImage. */
export const PATH_STYLE_INFO = INFO;

/**
 * enum PathStyle (raw values are the Swift rawValues, used in saves/settings).
 * Cases are string constants; computed properties are functions taking the case:
 * PathStyle.title(s), PathStyle.blurb(s), PathStyle.systemImage(s), PathStyle.id(s);
 * statics: PathStyle.allCases, PathStyle.teamMix, PathStyle.antMix.
 */
export const PathStyle = Object.freeze({
  direct: 'direct',
  natural: 'natural',
  curious: 'curious',
  wall: 'wall',
  scout: 'scout',
  randomTeam: 'randomTeam',
  randomAnt: 'randomAnt',
  allCases: Object.freeze(['direct', 'natural', 'curious', 'wall', 'scout', 'randomTeam', 'randomAnt']),
  teamMix: Object.freeze(['direct', 'natural', 'curious', 'wall', 'scout']),
  antMix: Object.freeze(['direct', 'natural', 'curious', 'wall']),
  id(s) { return s; },
  title(s) { return INFO[s].title; },
  blurb(s) { return INFO[s].blurb; },
  systemImage(s) { return INFO[s].systemImage; },
});

/** An ant stopping to sniff on the way out: at path position `at` (cells) for `duration` game seconds. */
export function TripPause(at, duration) { return { at, duration }; }

const INT32_MAX = 2147483647;

/** Minimal binary heap ordered by (f, order). Stored as parallel arrays (no per-entry objects). */
class Heap {
  constructor() {
    this._f = [];
    this._o = [];
    this._c = [];
  }

  get count() { return this._f.length; }
  get isEmpty() { return this._f.length === 0; }

  removeAll() { this._f.length = 0; this._o.length = 0; this._c.length = 0; }

  _less(i, j) {
    const a = this._f[i], b = this._f[j];
    return a < b || (a === b && this._o[i] < this._o[j]);
  }

  _swap(i, j) {
    const f = this._f, o = this._o, c = this._c;
    let t = f[i]; f[i] = f[j]; f[j] = t;
    t = o[i]; o[i] = o[j]; o[j] = t;
    t = c[i]; c[i] = c[j]; c[j] = t;
  }

  /** push((f:, order:, cell:)) */
  push(f, order, cell) {
    this._f.push(f);
    this._o.push(order);
    this._c.push(cell);
    let i = this._f.length - 1;
    while (i > 0) {
      const p = (i - 1) >> 1;
      if (this._less(i, p)) {
        this._swap(i, p);
        i = p;
      } else {
        break;
      }
    }
  }

  /** Removes the smallest entry and returns its cell (-1 when empty); its f/order land in topF/topOrder. */
  pop() {
    const n = this._f.length;
    if (n === 0) return -1;
    this.topF = this._f[0];
    this.topOrder = this._o[0];
    const top = this._c[0];
    const lf = this._f.pop(), lo = this._o.pop(), lc = this._c.pop();
    const m0 = this._f.length;
    if (m0 > 0) {
      this._f[0] = lf; this._o[0] = lo; this._c[0] = lc;
      let i = 0;
      for (;;) {
        const l = 2 * i + 1;
        const r = l + 1;
        let m = i;
        if (l < m0 && this._less(l, m)) m = l;
        if (r < m0 && this._less(r, m)) m = r;
        if (m === i) break;
        this._swap(i, m);
        i = m;
      }
    }
    return top;
  }
}

/**
 * Reusable search buffers (one per ant scheduler), so planning a route allocates nothing per ant.
 * Cells are "fresh" for a search when their stamp differs from the current generation.
 */
export class PlannerScratch {
  constructor(count) {
    this.g = new Float64Array(count);
    this.steps = new Int32Array(count);
    this.prev = new Int32Array(count).fill(-1);
    this.seen = new Int32Array(count);
    this.closed = new Int32Array(count);
    this.corridor = new Int32Array(count);
    this.gen = 0;
    this.corridorGen = 0;
    this.heap = new Heap();
  }

  nextSearch() {
    if (this.gen === INT32_MAX - 1) {
      this.gen = 0;
      this.seen.fill(0);
      this.closed.fill(0);
    }
    this.gen += 1;
    this.heap.removeAll();
  }

  nextCorridor() {
    if (this.corridorGen === INT32_MAX - 1) {
      this.corridorGen = 0;
      this.corridor.fill(0);
    }
    this.corridorGen += 1;
  }

  inCorridor(n) { return this.corridor[n] === this.corridorGen; }
}

/**
 * Route planning is bounded so a send never stalls the game (mirrors plan_route in Tools/engine.py):
 * each ant's search stays inside a corridor of `corridor` cells around its direct path (a route always
 * exists there and the search cannot flood the open ground) and may not exceed the longest route that
 * would be accepted. At most `maxStyledPerSend` ants of one send get a styled route, spread evenly
 * through the send; the others walk their direct path. A send shares `budgetPerSend` expansions and
 * each ant may use up to 10 per cell of its direct path + 100; an ant whose search runs out walks its
 * direct path.
 */
export class PathPlanner {
  /** Wandering styles avoid cells whose tile has not been lifted yet (the ant would have to wait). */
  static futurePenalty = 4.0;
  static corridor = 3;
  static budgetPerSend = 16000;
  static maxStyledPerSend = 32;
  static Heap = Heap;

  static unitHash(a, b) { return (hash32(a, b) & 0xFFFF) / 65535.0; }

  /** How strongly each style's search is pulled towards the tile (weighted A*). */
  static weight(style, trail) {
    switch (style) {
      case 'natural': return 1.05;
      case 'curious': return 1.6;
      case 'wall': return 1.3;
      case 'scout': return trail ? 1.3 : 1.8;
      default: return 1.0;
    }
  }

  static maxRouteCells(directCount) { return Math.max(2 * directCount, directCount + 14); }

  /** antBudget(directCount:remaining:) */
  static antBudget(directCount, remaining) { return Math.max(0, Math.min(remaining, 10 * directCount + 100)); }

  /** Marks the cells within Manhattan distance `corridor` of `path` in the scratch's corridor. */
  static markCorridor(board, path, scratch) {
    scratch.nextCorridor();
    const cols = board.cols, rows = board.rows;
    const tag = scratch.corridorGen;
    const cor = scratch.corridor;
    const r = PathPlanner.corridor;
    for (let k = 0; k < path.length; k++) {
      const c = path[k];
      const x = c % cols, y = (c / cols) | 0;
      for (let dy = -r; dy <= r; dy++) {
        const yy = y + dy;
        if (yy < 0 || yy >= rows) continue;
        const span = r - Math.abs(dy);
        for (let dx = -span; dx <= span; dx++) {
          const xx = x + dx;
          if (xx < 0 || xx >= cols) continue;
          cor[yy * cols + xx] = tag;
        }
      }
    }
  }

  /**
   * Weighted A* over 4-neighbour cells (f = g + weight × Manhattan). Never expands towards a cell
   * from which the route would exceed `maxCells`, and gives up after `budget` expansions.
   * Returns { route: number[] | null, expansions }.
   */
  static astar(board, start, goal, weight, maxCells, budget, sc, walkable, cost) {
    if (start === goal) return { route: [goal], expansions: 0 };
    sc.nextSearch();
    const gen = sc.gen;
    const cols = board.cols;
    const nb = board.neighbours;
    const gx = goal % cols, gy = (goal / cols) | 0;
    const g = sc.g, steps = sc.steps, prev = sc.prev, seen = sc.seen, closed = sc.closed;
    const heap = sc.heap;
    let order = 0;
    let expansions = 0;
    seen[start] = gen;
    g[start] = 0;
    steps[start] = 0;
    prev[start] = -1;
    heap.push(weight * (Math.abs(start % cols - gx) + Math.abs(((start / cols) | 0) - gy)), 0, start);
    let found = false;
    while (heap.count > 0) {
      const c = heap.pop();
      if (closed[c] === gen) continue;
      if (c === goal) {
        found = true;
        break;
      }
      closed[c] = gen;
      expansions += 1;
      if (expansions > budget) return { route: null, expansions };
      const nextSteps = steps[c] + 1;
      const gc = g[c];
      for (let k = 0; k < 4; k++) {
        const n = nb[c * 4 + k];
        if (n < 0) continue;
        if (closed[n] === gen || !walkable(n)) continue;
        const h = Math.abs(n % cols - gx) + Math.abs(((n / cols) | 0) - gy);
        if (nextSteps + 1 + h > maxCells) continue;
        const ng = gc + cost(n);
        if (seen[n] !== gen || ng < g[n] - 1e-12) {
          seen[n] = gen;
          g[n] = ng;
          prev[n] = c;
          steps[n] = nextSteps;
          order += 1;
          heap.push(ng + weight * h, order, n);
        }
      }
    }
    if (!found) return { route: null, expansions };
    const path = [goal];
    let cur = goal;
    let guardSteps = 0;
    while (cur !== start) {
      const p = prev[cur];
      if (p < 0) return { route: null, expansions };
      path.push(p);
      cur = p;
      guardSteps += 1;
      if (guardSteps > board.count) return { route: null, expansions };
    }
    path.reverse();
    return { route: path, expansions };
  }

  /**
   * Route for one ant from the hole to the stand cell beside its tile. Only cells that are ground
   * or already scheduled to be lifted, inside the ant's corridor, are used; the scheduler then
   * delays the departure until every tile on the route has been lifted. Falls back to the claim's
   * own path if the search runs out of budget or a style's route would be unreasonably long.
   *
   * plan(board:liftTime:claim:style:seed:now:trail:budget:scratch:)
   * @param {Float64Array} liftTime
   * @param {Set<number>|null} trail
   * @returns {{route: number[], pauses: {at:number,duration:number}[], used: string, spent: number}}
   */
  static plan(board, liftTime, claim, style, seed, now, trail, budget, scratch) {
    const direct = claim.path;
    if (style === 'direct' || direct.length < 3 || budget <= 0) return { route: direct, pauses: [], used: 'direct', spent: 0 };
    switch (style) {
      case 'natural': case 'curious': case 'wall': case 'scout': break;
      default: return { route: direct, pauses: [], used: 'direct', spent: 0 };
    }
    const start = direct[0];
    const goal = direct[direct.length - 1];
    const cols = board.cols;
    const fam = board.family;
    const nb = board.neighbours;
    PathPlanner.markCorridor(board, direct, scratch);
    const cor = scratch.corridor;
    const ctag = scratch.corridorGen;
    const walkable = n => cor[n] === ctag && liftTime[n] < Infinity;
    const futurePenalty = PathPlanner.futurePenalty;
    const future = n => ((fam[n] >= 0 && liftTime[n] > now + 1e-9) ? futurePenalty : 0);
    const hasTrail = !!(trail && trail.size > 0);
    const w = PathPlanner.weight(style, hasTrail);
    const maxCells = PathPlanner.maxRouteCells(direct.length);
    const unitHash = PathPlanner.unitHash;
    let result;
    switch (style) {
      case 'natural': {
        const hx = start % cols + 0.5, hy = ((start / cols) | 0) + 0.5;
        const tx = goal % cols + 0.5, ty = ((goal / cols) | 0) + 0.5;
        const ln = Math.max(1e-9, Math.sqrt((tx - hx) * (tx - hx) + (ty - hy) * (ty - hy)));
        result = PathPlanner.astar(board, start, goal, w, maxCells, budget, scratch, walkable, n => {
          const px = n % cols + 0.5, py = ((n / cols) | 0) + 0.5;
          return 1.0 + 1e-4 * Math.abs((tx - hx) * (hy - py) - (hx - px) * (ty - hy)) / ln;
        });
        break;
      }
      case 'curious':
        result = PathPlanner.astar(board, start, goal, w, maxCells, budget, scratch, walkable,
          n => 1.0 + 1.6 * unitHash(seed, n) + future(n));
        break;
      case 'wall': {
        // beside a tile that is still on the board (the mosaic's current edge, not the board's rim)
        const edge = n => {
          for (let k = 0; k < 4; k++) {
            const m = nb[n * 4 + k];
            if (m >= 0 && !(liftTime[m] < Infinity)) return true;
          }
          return false;
        };
        result = PathPlanner.astar(board, start, goal, w, maxCells, budget, scratch, walkable,
          n => 1.0 + (edge(n) ? 0.0 : 0.9) + future(n));
        break;
      }
      default:
        if (hasTrail) {
          const t = trail;
          result = PathPlanner.astar(board, start, goal, w, maxCells, budget, scratch, walkable,
            n => 1.0 + (t.has(n) ? 0.0 : 1.2) + future(n));
        } else {
          result = PathPlanner.astar(board, start, goal, w, maxCells, budget, scratch, walkable,
            n => 1.0 + 2.5 * unitHash(seed, n) + future(n));
        }
    }
    const r = result.route;
    if (!r || r.length > maxCells) return { route: direct, pauses: [], used: 'direct', spent: result.expansions };
    let sniff = 0;
    if (style === 'curious') {
      sniff = unitHash(seed, 7) < 0.35 ? 1 : 0;
    } else if (style === 'scout' && !hasTrail) {
      sniff = 1;
    }
    const pauses = [];
    const l = r.length;
    if (r.length >= 8) {
      for (let k = 0; k < sniff; k++) {
        const u = 2.0 + unitHash(seed, 101 + k) * (l - 4.0);
        pauses.push(TripPause(u, 0.5 + 0.7 * unitHash(seed, 202 + k)));
      }
      pauses.sort((a, b) => a.at - b.at);
    }
    return { route: r, pauses, used: style, spent: result.expansions };
  }
}
