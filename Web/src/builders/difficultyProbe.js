// Port of DifficultyProbe (Level.swift): measures a pattern or photo level on the device — careless
// random play and the one-step greedy player (the same rollout the hints use), on every difficulty.
// Returns DifficultyStats-shaped data: { careless: [gentle, classic, expert], greedy: [g, c, e] }.
//
// Does not depend on core/level.js: `chambers(level, difficulty)` and the difficulty order are
// local copies of LevelDefinition.chambers(for:) and Difficulty.allCases.

import { SplitMix64 } from '../core/util.js';
import { Board } from '../core/board.js';
import { Game } from '../core/engine.js';
import { HintSolver } from '../core/hint.js';

/** Difficulty.allCases, in index order (gentle, classic, expert). */
export const DIFFICULTIES = Object.freeze(['gentle', 'classic', 'expert']);

/** LevelDefinition.chambers(for:) for a plain level object. */
export function chambers(level, difficulty) {
  switch (difficulty) {
    case 'gentle': return level.chambersGentle;
    case 'classic': return level.chambersClassic;
    case 'expert': return level.chambersExpert;
    default: throw new Error(`unknown difficulty ${difficulty}`);
  }
}

export const DifficultyProbe = Object.freeze({
  /**
   * Careless play: `trials` games of random sends into open slots (no undo, no assists), one
   * SplitMix64(seed: 5) stream per difficulty; greedy: HintSolver.rollout from the start.
   */
  measure(level, trials = 10) {
    const board = new Board(level.art);
    const careless = [];
    const greedy = [];
    for (const d of DIFFICULTIES) {
      const cap = chambers(level, d);
      const rng = new SplitMix64(5n);
      let wins = 0;
      for (let t = 0; t < trials; t++) {
        const g = new Game(level, board, cap);
        let steps = 0;
        while (!g.isWon && steps < 2000) {
          const fronts = [];
          for (let q = 0; q < g.tunnels.length; q++) if (g.canDispatch(q)) fronts.push(q);
          if (fronts.length === 0) break;
          g.dispatch(fronts[rng.int(fronts.length)]);
          steps += 1;
        }
        if (g.isWon) wins += 1;
      }
      careless.push(wins / Math.max(1, trials));
      const start = new Game(level, board, cap);
      greedy.push(HintSolver.rollout(board, level.tunnels, start.state).won);
    }
    return { careless, greedy };
  },
});
