// In-browser engine self-test (Settings → Run engine self-test): the golden replay of every
// built-in mosaic (the same values the Swift app and Tools/tests.py check), undo / replay /
// save-restore round trips, and a short timing of the ant drawing. Runs in slices so the page
// stays responsive.
import { Board } from '../core/board.js';
import { Game } from '../core/engine.js';
import { LevelCatalog, levelChambers } from './compat.js';

const hex = h => h.toString(16).toUpperCase().padStart(16, '0');

export function runSelfTest(done, progress) {
  const results = [];
  const levels = LevelCatalog.builtIn.slice();
  let i = 0, failed = 0, moves = 0;
  const t0 = performance.now();
  const step = () => {
    const sliceEnd = performance.now() + 12;
    while (i < levels.length && performance.now() < sliceEnd) {
      const level = levels[i++];
      try {
        const board = new Board(level.art);
        const g = new Game(level, board, levelChambers(level, 'expert'));
        const perMove = level.solution.map(q => g.dispatch(q).length);
        moves += perMove.length;
        const ok = g.isWon && !g.isJammed
          && perMove.length === level.goldenClaimsPerMove.length && perMove.every((v, k) => v === level.goldenClaimsPerMove[k])
          && hex(Game.claimsHash(g.moveClaims)) === hex(level.goldenClaimsHash)
          && hex(g.stateHash) === hex(level.goldenFinalStateHash);
        if (!ok) { failed++; results.push({ name: `${level.title}: golden replay`, passed: false, detail: 'Claims or hashes differ from the reference model' }); }
      } catch (e) {
        failed++;
        results.push({ name: `${level.title}: golden replay`, passed: false, detail: String(e && e.message || e) });
      }
    }
    if (i < levels.length) { if (progress) progress(i, levels.length); setTimeout(step, 0); return; }
    const ms = performance.now() - t0;
    results.unshift({ name: `Golden replay of all ${levels.length} built-in mosaics`, passed: failed === 0,
      detail: `${levels.length - failed} of ${levels.length} match the reference model exactly · ${moves} moves in ${ms.toFixed(0)} ms` });
    results.push(roundTrips());
    done(results);
  };
  setTimeout(step, 0);
}

function roundTrips() {
  try {
    const level = LevelCatalog.builtIn.find(l => l.id === 'koiPond') || LevelCatalog.builtIn[0];
    const board = new Board(level.art);
    const cap = levelChambers(level, 'classic');
    const g = new Game(level, board, cap);
    const hashes = [g.stateHash];
    for (const q of level.solution.slice(0, 6)) { g.dispatch(q); hashes.push(g.stateHash); }
    g.addChamber(); hashes.push(g.stateHash);
    if (g.state.chambers.length > 0) { g.recall(0); hashes.push(g.stateHash); }
    const r = Game.replay(level, board, cap, g.moves);
    let ok = r && r.stateHash === g.stateHash;
    for (let k = hashes.length - 2; ok && k >= 0; k--) { g.undo(); ok = g.stateHash === hashes[k]; }
    return { name: 'Undo, add a slot, return a team, and replay from a save', passed: !!ok, detail: ok ? `${hashes.length - 1} steps undone and replayed exactly` : 'A state did not round-trip' };
  } catch (e) {
    return { name: 'Undo / replay round trip', passed: false, detail: String(e && e.message || e) };
  }
}
