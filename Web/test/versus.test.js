// VersusEngine.swift: exact agreement with Tools/versus.py on 48 scripted matches
// (tools/make_fixtures.py → test/fixtures/versus.json): every option combination on First Dig and
// Nesting Rings, careless and greedy players, adds and returns. At every step the legality of each
// (tunnel, depth) probe (colour rule, reach, slots), the claims (team, family, tile, full path) and
// the whole match state must match the reference model.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { setLevelData } from '../src/core/levelData.js';
import { GeneratedLevels } from '../src/core/level.js';
import { Board } from '../src/core/board.js';
import {
  VersusLayout, VersusPicking, VersusColourRule, VersusSlotScoring, VersusRules, VTeam, VersusBoard,
  VersusMatch,
} from '../src/core/versus.js';

setLevelData(readFileSync(new URL('../data/levels.json', import.meta.url), 'utf8'));
const fx = JSON.parse(readFileSync(new URL('./fixtures/versus.json', import.meta.url), 'utf8'));

// FNV-1a 32, as in make_fixtures.py
const SEED32 = 2166136261;
const mix = (h, v) => Math.imul((h ^ v) >>> 0, 16777619) >>> 0;

function claimsHash(claims) {
  let h = SEED32;
  for (const c of claims) {
    h = mix(h, c.team);
    h = mix(h, c.family);
    h = mix(h, c.tile);
    h = mix(h, c.path.length);
    for (const x of c.path) h = mix(h, x);
  }
  return h;
}

function stateHash(m) {
  let h = SEED32;
  for (const b of m.boards) {
    for (const t of b.chambers) {
      h = mix(h, t.uid);
      h = mix(h, t.remaining);
    }
    h = mix(h, b.chambers.length);
    for (let f = 0; f < 6; f++) h = mix(h, b.left[f]);
    h = mix(h, b.claimed[0]);
    h = mix(h, b.claimed[1]);
  }
  for (const pl of m.players) {
    for (const queue of pl.queues) {
      h = mix(h, queue.length);
      for (const t of queue) {
        h = mix(h, t.uid);
        h = mix(h, t.remaining);
      }
    }
    for (const v of [pl.capacity, pl.added, pl.returns, pl.skips, pl.launches, pl.lastFamily === null ? 0 : pl.lastFamily + 1]) {
      h = mix(h, v);
    }
  }
  return h;
}

function cellsHash(m) {
  let h = SEED32;
  for (const b of m.boards) {
    for (let i = 0; i < b.board.count; i++) {
      h = mix(h, b.owner[i] + 1);
      h = mix(h, b.open[i]);
    }
  }
  return h;
}

const REASON = {
  'No team there.': 'n', 'Out of reach.': 'r', 'Every slot holds a waiting team.': 's',
  'Not the same colour twice in a row.': 'c',
};

function probes(m, p) {
  return m.players[p].queues.map((queue, q) => {
    let s = '';
    for (let d = 0; d <= Math.min(3, queue.length); d++) {
      const r = m.refusal(p, q, d);
      s += r === null ? 'o' : REASON[r];
    }
    return s;
  }).join('|');
}

const over = m => (m.rules.layout === 'race' ? m.boards.some(b => b.isCleared) : (m.boards[0].isCleared || m.isStalemate));

test('fixtures cover every option combination and every refusal', () => {
  const combos = new Set(fx.matches.map(x => [x.rules.layout, x.rules.picking, x.rules.colour, x.rules.scoring].join()));
  assert.equal(combos.size, 16);
  const all = fx.matches.flatMap(x => x.steps.map(s => s[1] === 'launch' ? s[4] : s[1] === 'return' ? s[3] : s[2])).join();
  for (const ch of 'onrsc') assert.ok(all.includes(ch), `probe outcome ${ch} appears`);
  const kinds = new Set(fx.matches.flatMap(x => x.steps.map(s => s[1])));
  assert.deepEqual([...kinds].sort(), ['add', 'launch', 'return']);
});

for (const [i, fm] of fx.matches.entries()) {
  const r = fm.rules;
  test(`match ${i}: ${fm.level} ${r.layout}/${r.picking}/${r.colour}/${r.scoring}/${r.difficulty} seed ${fm.seed}${fm.greedy ? ' greedy' : ''}`, () => {
    const level = GeneratedLevels[fm.level];
    const m = new VersusMatch(level, VersusRules(r));
    assert.equal(m.players[0].capacity, fm.capacity);
    for (const [k, step] of fm.steps.entries()) {
      assert.ok(!over(m), `step ${k}: not over yet`);
      const p = step[0];
      const kind = step[1];
      if (kind === 'launch') {
        const [, , q, d, pr, n, ch] = step;
        assert.equal(probes(m, p), pr, `step ${k} probes`);
        assert.ok(m.canLaunch(p, q, d));
        const ev = m.launch(p, q, d);
        assert.equal(ev.length, n, `step ${k} claim count`);
        assert.equal(claimsHash(ev), ch, `step ${k} claims`);
        if (k === 0 && fm.firstClaims) assert.deepEqual(ev.map(c => [c.team, c.family, c.tile, c.path]), fm.firstClaims);
      } else if (kind === 'add') {
        assert.equal(probes(m, p), step[2], `step ${k} probes`);
        m.addSlot(p);
      } else if (kind === 'return') {
        assert.equal(probes(m, p), step[3], `step ${k} probes`);
        m.returnTeam(p, step[2]);
      } else {
        assert.equal(probes(m, p), step[2], `step ${k} probes`);
      }
      for (const pp of [0, 1]) {
        m.players[pp].upkeep += VersusRules.upkeepPerSecond * Math.max(0, m.waiting(pp).length - 1) * 0.1;
      }
      assert.equal(stateHash(m), step.at(-1), `step ${k} state`);
    }
    const f = fm.final;
    assert.equal(over(m), f.over);
    assert.deepEqual([m.tiles(0), m.tiles(1)], f.tiles);
    assert.deepEqual([m.penalties(0), m.penalties(1)], f.penalties);
    assert.deepEqual([m.players[0].upkeep, m.players[1].upkeep], f.upkeep);
    assert.equal(m.tileCount, f.tileCount);
    assert.deepEqual(m.boards.map(b => b.left.slice(0, 6)), f.left);
    assert.ok(m.boards.every(b => b.left.slice(6).every(x => x === 0)));
    assert.deepEqual(m.boards.map(b => b.isCleared), f.done);
    assert.equal(cellsHash(m), f.cellsHash);
    assert.equal(stateHash(m), f.stateHash);
    // versus.py final_scores: tiles − penalties (+ 15% of the tiles to the first finished race board)
    const finisher = r.layout === 'race' ? m.boards.findIndex(b => b.isCleared) : -1;
    const scores = [0, 1].map(p => m.tiles(p) - m.penalties(p) + (p === finisher ? VersusRules.finishBonusShare * m.tileCount : 0));
    assert.deepEqual(scores, f.scores);
    if (r.layout === 'shared' && m.boards[0].isCleared) assert.equal(m.tiles(0) + m.tiles(1), m.tileCount);
    if (finisher >= 0) assert.equal(m.tiles(finisher), m.tileCount);
  });
}

test('rules: defaults, statics, reach depth, strict decoding, enum titles', () => {
  assert.deepEqual(VersusRules(), { layout: 'race', picking: 'reach3', colour: 'any', scoring: 'upkeep', difficulty: 'classic' });
  assert.deepEqual(VersusRules({ layout: 'shared', colour: 'alternate' }),
    { layout: 'shared', picking: 'reach3', colour: 'alternate', scoring: 'upkeep', difficulty: 'classic' });
  assert.deepEqual([VersusRules.addSlotPenalty, VersusRules.returnPenalty, VersusRules.skipPenalty, VersusRules.upkeepPerSecond,
    VersusRules.finishBonusShare, VersusRules.reach, VersusRules.playerBase], [25, 10, 3, 0.25, 0.15, 3, 100000]);
  assert.equal(VersusRules.reachDepth(VersusRules()), 3);
  assert.equal(VersusRules.reachDepth(VersusRules({ picking: 'front' })), 1);
  assert.ok(VersusRules.equals(VersusRules.decode(JSON.parse(JSON.stringify(VersusRules()))), VersusRules()));
  assert.equal(VersusRules.decode({ layout: 'race', picking: 'reach3', colour: 'any', scoring: 'upkeep' }), null, 'every key is required');
  assert.equal(VersusRules.decode({ ...VersusRules(), colour: 'rainbow' }), null);
  assert.deepEqual(VersusLayout.allCases.map(VersusLayout.title), ['Race', 'Shared board']);
  assert.deepEqual(VersusPicking.allCases.map(VersusPicking.title), ['Front team only', 'Reach 3']);
  assert.deepEqual(VersusColourRule.allCases.map(VersusColourRule.title), ['Any colour', 'No colour twice in a row']);
  assert.deepEqual(VersusSlotScoring.allCases.map(VersusSlotScoring.title), ['Slot upkeep', 'Flat slot cost']);
  assert.match(VersusSlotScoring.blurb('upkeep'), /0\.25 points per second/);
  assert.match(VersusPicking.blurb('reach3'), /costs 3 points per place/);
});

test('teams, boards and holes', () => {
  const t = new VTeam(1 * 100000 + 3 * 1000 + 7, 1, 2, 40, 40);
  assert.equal(t.tunnel, 3);
  assert.ok(VTeam.equals(t, t.copy()) && t.copy() !== t);
  const level = GeneratedLevels.firstDig;
  const b = new Board(level.art);
  assert.deepEqual(VersusMatch.sharedHoles(b), [(b.rows - 3) * b.cols + Math.floor(b.cols / 4), (b.rows - 3) * b.cols + Math.floor(3 * b.cols / 4)]);
  const vb = new VersusBoard(b, { 0: b.hole });
  assert.equal(vb.left.length, 8);
  assert.equal(vb.left.reduce((a, x) => a + x, 0), b.tileCount);
  assert.equal(vb.owner.length, b.count);
  assert.ok(vb.owner.every(x => x === -1));
  assert.equal(vb.removeChamber(5), null);
  const race = new VersusMatch(level, VersusRules());
  assert.equal(race.boards.length, 2);
  assert.notEqual(race.board(0), race.board(1));
  assert.equal(race.boardIndex(1), 1);
  const shared = new VersusMatch(level, VersusRules({ layout: 'shared', difficulty: 'expert' }));
  assert.equal(shared.boards.length, 1);
  assert.equal(shared.board(1), shared.board(0));
  assert.equal(shared.players[1].capacity, level.chambersExpert);
  assert.equal(shared.players[1].queues[0][2].uid, 100000 + 2);
  assert.equal(shared.isStalemate, false);
  assert.equal(shared.refusal(0, 9, 0), 'No team there.');
  assert.equal(shared.refusal(0, 0, 3), 'Out of reach.');
  assert.deepEqual(shared.launch(0, 0, 3), [], 'a refused launch does nothing');
  assert.equal(shared.players[0].launches, 0);
});

test('reach 3 skips cost 3 per place; adds 25; returns 10; upkeep only with slot upkeep scoring', () => {
  const level = GeneratedLevels.firstDig;
  for (const scoring of ['upkeep', 'flat']) {
    const m = new VersusMatch(level, VersusRules({ scoring }));
    m.launch(0, 0, 2);
    assert.equal(m.players[0].skips, 2);
    m.addSlot(0);
    const w = m.waiting(0);
    assert.ok(w.length > 0);
    m.returnTeam(0, w[0].uid);
    assert.equal(m.players[0].queues[w[0].tunnel][0], w[0], 'returned to the front of its tunnel');
    m.players[0].upkeep = 1.5;
    assert.equal(m.penalties(0), 2 * 3 + 25 + 10 + (scoring === 'upkeep' ? 1.5 : 0));
    assert.equal(m.penalties(1), 0);
  }
});

test("Swift quirk kept: returning the other player's waiting team on a shared board drops it from the board", () => {
  const m = new VersusMatch(GeneratedLevels.firstDig, VersusRules({ layout: 'shared' }));
  m.launch(1, 0, 0);
  const theirs = m.waiting(1)[0];
  assert.ok(theirs);
  m.returnTeam(0, theirs.uid);
  assert.equal(m.waiting(1).length, 0);
  assert.equal(m.players[0].returns, 0);
  assert.ok(m.players.every(pl => pl.queues.flat().every(t => t.uid !== theirs.uid)));
});
