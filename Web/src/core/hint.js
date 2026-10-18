// Port of HintSolver.swift (mirrors hint_full / evaluate_fronts in Tools/engine.py).
// HintResult: { kind: 'move', code, onPlan } | { kind: 'undo', count } | { kind: 'finished' }

import { Game, cloneState } from './engine.js';
import { tupleGreater } from './util.js';

const now = () => (typeof performance !== 'undefined' ? performance.now() : Date.now());

export const HintSolver = {
  evaluateFronts(board, tunnels, state) {
    const out = [];
    state.chambers.forEach((t, i) => {
      if (!t.held) return;
      const s2 = cloneState(state);
      const ev = Game.applyRelease(board, s2, i);
      let own = 0;
      for (const c of ev) if (c.team === t.uid) own += 1;
      out.push({ tunnel: Game.releaseBase + i, fits: own === t.remaining, jams: false, own, total: ev.length, after: s2 });
    });
    for (let q = 0; q < tunnels.length; q++) {
      if (!(state.chambers.length < state.capacity)) continue;
      const fr = Game.front(tunnels, state, q);
      if (!fr) continue;
      const s2 = cloneState(state);
      const ev = Game.applyDispatch(board, tunnels, s2, q);
      let own = 0;
      for (const c of ev) if (c.team === fr.uid) own += 1;
      out.push({ tunnel: q, fits: own === fr.need, jams: s2.jammed !== null, own, total: ev.length, after: s2 });
    }
    return out;
  },

  _better(a, b) {
    if (a.total !== b.total) return a.total > b.total;
    return a.tunnel < b.tunnel;
  },

  greedyChoice(board, tunnels, state) {
    const opts = HintSolver.evaluateFronts(board, tunnels, state);
    if (opts.length === 0) return null;
    const fits = opts.filter(o => o.fits);
    let pool;
    if (fits.length > 0) pool = fits;
    else {
      const safe = opts.filter(o => !o.jams);
      pool = safe.length > 0 ? safe : opts;
    }
    let best = pool[0];
    for (let i = 1; i < pool.length; i++) if (HintSolver._better(pool[i], best)) best = pool[i];
    return best;
  },

  /** @returns {{won:boolean, cleared:number}}; deadline in performance.now() milliseconds */
  rollout(board, tunnels, state, maxMoves = 400, deadline = Infinity) {
    let st = state;
    let n = 0;
    while (st.jammed === null && st.cleared < board.tileCount && n < maxMoves) {
      if (now() > deadline) return { won: false, cleared: st.cleared };
      const choice = HintSolver.greedyChoice(board, tunnels, st);
      if (!choice) break;
      st = choice.after;
      n += 1;
    }
    return { won: st.jammed === null && st.cleared === board.tileCount, cleared: st.cleared };
  },

  /** Best front by greedy rollouts. Returns [tunnel, rolloutWins] or null. */
  searchMove(board, tunnels, state, deadline = Infinity) {
    let bestScore = null;
    let bestTunnel = -1;
    for (const f of HintSolver.evaluateFronts(board, tunnels, state)) {
      let score;
      if (f.jams) {
        score = [0, 0, 0, -f.tunnel];
      } else {
        const r = HintSolver.rollout(board, tunnels, f.after, 400, deadline);
        score = [r.won ? 1 : 0, f.fits ? 1 : 0, r.cleared, -f.tunnel];
      }
      if (bestScore) {
        if (tupleGreater(score, bestScore)) { bestScore = score; bestTunnel = f.tunnel; }
      } else {
        bestScore = score;
        bestTunnel = f.tunnel;
      }
    }
    if (!bestScore) return null;
    return [bestTunnel, bestScore[0] === 1];
  },

  hint(board, tunnels, state, moves, solution) {
    const k = moves.length;
    let onLine = state.jammed === null && k <= solution.length;
    for (let i = 0; onLine && i < k; i++) if (solution[i] !== moves[i]) onLine = false;
    if (onLine) {
      if (k < solution.length) return { kind: 'move', code: solution[k], onPlan: true };
      return { kind: 'finished' };
    }
    // Off the designed line: search with greedy rollouts, but never for more than ~3 seconds.
    const deadline = now() + 3000;
    if (state.jammed === null) {
      const found = HintSolver.searchMove(board, tunnels, state, deadline);
      if (found && found[1]) return { kind: 'move', code: found[0], onPlan: true };
    }
    let lcp = 0;
    while (lcp < moves.length && lcp < solution.length && moves[lcp] === solution[lcp]) lcp += 1;
    const back = moves.length - lcp;
    const slotsFullOfWaiting = state.chambers.length >= state.capacity && !state.chambers.some(t => t.held);
    if (back > 0 || state.jammed !== null || slotsFullOfWaiting) return { kind: 'undo', count: Math.max(1, back) };
    const found = HintSolver.searchMove(board, tunnels, state, now() + 1000);
    if (found) return { kind: 'move', code: found[0], onPlan: false };
    return { kind: 'finished' };
  },
};
