// Golden replay of every built-in level (the same check as SelfTest.swift section 1 and
// Tools/tests.py): the designed solution on Expert slots must reproduce the reference model's
// claims per move, claim-order hash and final state hash exactly.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { Board } from '../src/core/board.js';
import { Game, cloneState } from '../src/core/engine.js';
import { HintSolver } from '../src/core/hint.js';

const data = JSON.parse(readFileSync(new URL('../data/levels.json', import.meta.url)));
const levels = Object.values(data.levels).map(l => ({ ...l, tunnels: l.tunnels.map(q => q.map(([family, quota]) => ({ family, quota }))) }));
const hex = h => h.toString(16).toUpperCase().padStart(16, '0');

test('193 built-in levels', () => assert.equal(levels.length, 193));

for (const level of levels) {
  test(`golden replay: ${level.id}`, () => {
    const board = new Board(level.art);
    const g = new Game(level, board, level.chambersExpert);
    const perMove = level.solution.map(q => g.dispatch(q).length);
    assert.ok(g.isWon && !g.isJammed, 'solution clears the board');
    assert.deepEqual(perMove, level.goldenClaimsPerMove);
    assert.equal(hex(Game.claimsHash(g.moveClaims)), level.goldenClaimsHash);
    assert.equal(hex(g.stateHash), level.goldenFinalStateHash);
  });
}

test('undo restores the exact earlier state; replay rebuilds it', () => {
  const level = levels.find(l => l.id === 'firstDig');
  const board = new Board(level.art);
  const g = new Game(level, board, level.chambersClassic);
  const hashes = [g.stateHash];
  for (const q of level.solution.slice(0, 8)) { g.dispatch(q); hashes.push(g.stateHash); }
  g.addChamber(); hashes.push(g.stateHash);
  const r = Game.replay(level, board, level.chambersClassic, g.moves);
  assert.equal(r.stateHash, g.stateHash);
  for (let i = hashes.length - 2; i >= 0; i--) { g.undo(); assert.equal(g.stateHash, hashes[i]); }
});

test('hints follow the designed line, then the greedy search off it', () => {
  const level = levels.find(l => l.id === 'koiPond');
  const board = new Board(level.art);
  const g = new Game(level, board, level.chambersClassic);
  const h0 = HintSolver.hint(board, g.tunnels, g.state, g.moves, level.solution);
  assert.deepEqual(h0, { kind: 'move', code: level.solution[0], onPlan: true });
  // scout never changes the real state
  const before = g.stateHash;
  g.scout(0);
  assert.equal(g.stateHash, before);
  const st = cloneState(g.state);
  assert.equal(Game.stateHash(board, st), before);
});
