// Port of LevelGenerator.swift: builds tunnel queues for any mosaic by simulating a "designer" who
// invents each team while playing; the designer's own play is therefore a guaranteed solution.
// Swift port of design_sequence / deal in Tools/generate_levels.py (used for photo and pattern mosaics).
//
// SplitMix64 lives in ../core/util.js (bit-exact BigInt port); it is re-exported here because the
// Swift struct is declared in LevelGenerator.swift. Swift `inout rng` = pass the SplitMix64 object
// (it is advanced in place). Seeds are UInt64 → BigInt (numbers are accepted and converted).
//
// Tuples: deal returns [tunnels, solution] (Swift `([[TeamSpec]], [Int])`).

import { SplitMix64 } from '../core/util.js';
import { Game, cloneState, makeTeam } from '../core/engine.js';

export { SplitMix64 };

const M64 = (1n << 64n) - 1n;

/** Plan: the planned tunnels, the designer's solution, and the most chambers it ever needed. */
export function Plan(tunnels, solution, maxChambersUsed) {
  return { tunnels, solution, maxChambersUsed };
}

export const LevelGenerator = Object.freeze({
  ladder: Object.freeze([20, 24, 30, 36, 42, 48, 56, 64, 72, 84, 96, 110]),
  maxTeam: 128,
  Plan,

  /**
   * The designer: plays the board, inventing each team as it goes. Every team is created so that
   * the designer's play never needs more than `maxWait` chambers. Returns [TeamSpec] or null.
   */
  designSequence(board, rng, maxWait, minTeam, pWait) {
    const ladder = LevelGenerator.ladder;
    const maxTeam = LevelGenerator.maxTeam;
    let st = {
      open: board.initialOpen(), heads: [0], chambers: [], capacity: maxWait, added: 0,
      jammed: null, cleared: 0, returned: [[]],
    };
    const unassigned = board.familyTotals.slice();
    const seq = [];
    let lastFam = -1;
    let guardCount = 0;
    const sum = a => { let s = 0; for (const v of a) s += v; return s; };
    while (sum(unassigned) > 0) {
      guardCount += 1;
      if (guardCount > 5000) return null;
      const reach = new Array(unassigned.length).fill(-1);
      const fams = [];
      for (let f = 0; f < unassigned.length; f++) {
        if (!(unassigned[f] > 0)) continue;
        const s2 = cloneState(st);
        reach[f] = Game.claimRun(board, s2, f, unassigned[f], -1).length;
        fams.push(f);
      }
      const fitting = fams.filter(f => reach[f] >= Math.min(minTeam, unassigned[f]));
      let choice = null;
      if (st.chambers.length < maxWait && rng.unit() < pWait) {
        const waitFams = fams.filter(f =>
          reach[f] < unassigned[f] && unassigned[f] >= minTeam && reach[f] + 12 <= maxTeam
          && !st.chambers.some(t => t.family === f));
        if (waitFams.length > 0) {
          const f = waitFams[rng.int(waitFams.length)];
          const extra = [12, 18, 24, 30, 40][rng.int(5)];
          let q = Math.min(unassigned[f], Math.max(minTeam, reach[f] + extra), maxTeam);
          if (unassigned[f] - q < minTeam && unassigned[f] <= maxTeam) q = unassigned[f];
          choice = [f, q];
        }
      }
      if (choice === null) {
        if (fitting.length === 0) {
          let f = fams[0];
          for (const g of fams) if (reach[g] > reach[f]) f = g;
          const q = unassigned[f] < 2 * minTeam ? unassigned[f] : Math.min(maxTeam, Math.max(minTeam, reach[f]));
          choice = [f, q];
        } else {
          const weights = fitting.map(g => Math.pow(Math.max(1, reach[g]), 0.6) * (g === lastFam ? 0.35 : 1.0));
          const f = fitting[rng.weighted(weights)];
          const cap = Math.min(reach[f], unassigned[f]);
          const options = ladder.filter(v => v <= cap);
          let q = cap;
          if (options.length > 0) {
            const top = options.slice(-6);
            q = Math.min(top[rng.int(top.length)], cap);
          }
          if (unassigned[f] - q < minTeam && unassigned[f] <= maxTeam) q = unassigned[f];
          choice = [f, q];
        }
      }
      if (choice === null || !(choice[1] > 0)) return null;
      let [f, q] = choice;
      let trial = cloneState(st);
      Game.resolve(board, trial, makeTeam(seq.length, f, q, q));
      if (trial.jammed !== null) {
        // fall back to a team that certainly completes right now
        const pool = fitting.length === 0 ? fams.filter(g => reach[g] > 0) : fitting;
        if (pool.length === 0) return null;
        f = pool[0];
        for (const g of pool) if (reach[g] > reach[f]) f = g;
        q = Math.min(reach[f], unassigned[f]);
        trial = cloneState(st);
        Game.resolve(board, trial, makeTeam(seq.length, f, q, q));
        if (trial.jammed !== null) return null;
      }
      st = trial;
      seq.push({ family: f, quota: q });
      unassigned[f] -= q;
      lastFam = f;
    }
    if (!(st.cleared === board.tileCount && st.chambers.length === 0)) return null;
    return seq;
  },

  /**
   * Deals the designer's sequence into `tunnelCount` tunnels (order inside each tunnel is kept,
   * so the designer's play stays a valid solution). Returns [tunnels, solution].
   */
  deal(seq, tunnelCount, rng) {
    const n = tunnelCount;
    const tunnels = Array.from({ length: n }, () => []);
    const solution = [];
    for (const spec of seq) {
      const lens = tunnels.map(t => t.length);
      const lo = lens.length > 0 ? Math.min(...lens) : 0;
      const cands = [];
      for (let i = 0; i < n; i++) if (lens[i] <= lo + 2) cands.push(i);
      const i = cands[rng.int(cands.length)];
      tunnels[i].push(spec);
      solution.push(i);
    }
    return [tunnels, solution];
  },

  /** Replays a solution; returns the most chambers it ever needed, or null if it fails. */
  verify(board, tunnels, solution, capacity) {
    const st = {
      open: board.initialOpen(), heads: new Array(tunnels.length).fill(0), chambers: [],
      capacity, added: 0, jammed: null, cleared: 0, returned: tunnels.map(() => []),
    };
    let maxUsed = 0;
    for (const q of solution) {
      if (Game.front(tunnels, st, q) === null) return null;
      Game.applyDispatch(board, tunnels, st, q);
      if (st.jammed !== null) return null;
      maxUsed = Math.max(maxUsed, st.chambers.length);
    }
    return st.cleared === board.tileCount ? maxUsed : null;
  },

  /** Plans a level for `board` (up to 8 seeded attempts). Returns a Plan or null. */
  generate(board, seed) {
    const s0 = BigInt.asUintN(64, BigInt(seed));
    const small = board.tileCount < 600;
    const tunnelCount = small ? 2 : 3;
    const maxWait = small ? 1 : 2;
    const minTeam = board.tileCount < 2000 ? 10 : 20;
    for (let attempt = 0; attempt < 8; attempt++) {
      const rng = new SplitMix64((s0 + BigInt(attempt) * 7919n) & M64);
      const seq = LevelGenerator.designSequence(board, rng, maxWait, minTeam, 0.18);
      if (seq === null) continue;
      const [tunnels, solution] = LevelGenerator.deal(seq, tunnelCount, rng);
      const used = LevelGenerator.verify(board, tunnels, solution, maxWait);
      if (used !== null) return Plan(tunnels, solution, used);
    }
    return null;
  },
});
