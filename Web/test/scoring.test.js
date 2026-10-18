// Scoring.swift: golden values of SelfTest.swift section 7 and Tools/tests.py, plus fixtures from
// Tools/scoring.py (tools/make_fixtures.py → test/fixtures/scoring.json): score breakdowns, the
// 40-insert high-score sequence and the No colour twice rule.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { setLevelData } from '../src/core/levelData.js';
import { GeneratedLevels } from '../src/core/level.js';
import { Board } from '../src/core/board.js';
import { Game } from '../src/core/engine.js';
import {
  ChallengeModifier, ScoreRules, HighScoreEntry, HighScoreKind, HighScoreTable, RatingFilter, ColourRule,
  HighScoreNames, TimeText,
} from '../src/core/scoring.js';

setLevelData(readFileSync(new URL('../data/levels.json', import.meta.url), 'utf8'));
const fx = JSON.parse(readFileSync(new URL('./fixtures/scoring.json', import.meta.url), 'utf8'));

// SelfTest.swift section 7 = SCORE_GOLDEN in Tools/tests.py
const SCORE_GOLDEN = [
  [1008, 'expert', ['noHints', 'limitedUndo'], 3, 0, 0, 1951],
  [6048, 'gentle', [], 12, 2, 1, 2889],
  [1760, 'classic', ChallengeModifier.allCases, 0, 0, 0, 3520],
  [100, 'gentle', [], 20, 5, 5, 0],
  [2464, 'classic', ['hiddenQueue', 'noAssists', 'noRepeatColour'], 1, 1, 0, 3912],
];
const RANK_TABLE = [[1000, 60.0], [900, 50.0], [900, 40.0], [500, 70.0], [400, 30.0]];
const RANK_GOLDEN = [[950, 10, 2], [900, 45, 3], [900, 40, 3], [300, 1, null], [400, 100, null], [0, 5, null], [2000, 999, 1]];

function goldenTable() {
  const table = new HighScoreTable();
  RANK_TABLE.forEach(([score, seconds], i) => {
    table.insert('solo', 't', HighScoreEntry({ name: `P${i}`, score, seconds, date: i * 1000, difficulty: 'classic' }));
  });
  return table;
}

test('score: tiles × difficulty × harder options minus undo, hint and assist penalties (5 golden cases)', () => {
  for (const [tiles, d, mods, u, h, a, want] of SCORE_GOLDEN) {
    assert.equal(ScoreRules.solo(tiles, d, mods, u, h, a).score, want, `${tiles} tiles`);
    assert.equal(ScoreRules.solo(tiles, d, new Set(mods), u, h, a).score, want, 'Set or array');
  }
  assert.deepEqual(ScoreRules.solo(1008, 'expert', ['noHints', 'limitedUndo'], 3, 0, 0), {
    tiles: 1008, difficultyFactor: 1.5, modifierFactor: 1.3, base: 1966,
    undoPenalty: 15, hintPenalty: 0, assistPenalty: 0, score: 1951,
  });
});

test('score: 300 breakdowns agree exactly with Tools/scoring.py', () => {
  for (const c of fx.solo) {
    const b = ScoreRules.solo(c.tiles, c.difficulty, c.modifiers, c.undos, c.hints, c.assists);
    const got = [b.base, b.undoPenalty, b.hintPenalty, b.assistPenalty, b.score, b.modifierFactor, b.difficultyFactor];
    assert.deepEqual(got, [c.base, c.undo, c.hint, c.assist, c.score, c.mf, c.df], JSON.stringify(c));
  }
});

test('score factors and the harder options', () => {
  assert.deepEqual(['gentle', 'classic', 'expert'].map(ScoreRules.difficultyFactor), [0.5, 1, 1.5]);
  assert.equal(ScoreRules.modifierFactor([]), 1);
  assert.equal(ScoreRules.modifierFactor(['noRepeatColour', 'hiddenQueue']), 1 + 0.2 + 0.25);
  // fixed summing order, whatever order the set was built in
  assert.equal(ScoreRules.modifierFactor([...ChallengeModifier.allCases].reverse()), ScoreRules.modifierFactor(ChallengeModifier.allCases));
  assert.equal([ScoreRules.undoPenalty, ScoreRules.hintPenalty, ScoreRules.assistPenalty].join(), '5,25,25');
  assert.deepEqual(ChallengeModifier.allCases.map(ChallengeModifier.title),
    ['Hidden queue', 'No scouting', 'No hints', '3 undos', 'No assists', 'No colour twice']);
  assert.deepEqual(ChallengeModifier.allCases.map(ChallengeModifier.bonus), [0.2, 0.1, 0.1, 0.2, 0.15, 0.25]);
  assert.deepEqual(ChallengeModifier.allCases.map(ChallengeModifier.systemImage),
    ['eye.slash', 'binoculars', 'lightbulb.slash', 'arrow.uturn.backward.circle', 'hand.raised.slash', 'circle.lefthalf.filled']);
  assert.equal(ChallengeModifier.undoLimit, 3);
  assert.equal(ChallengeModifier.blurb('limitedUndo'), 'Only 3 undos for the whole game.');
  assert.equal(ChallengeModifier.blurb('noScout'), 'Press-and-hold scouting and Gentle’s “can finish” badges are off.');
  assert.deepEqual(ChallengeModifier.sorted(new Set(['noRepeatColour', 'noScout', 'hiddenQueue'])),
    ['hiddenQueue', 'noScout', 'noRepeatColour']);
  const b = ScoreRules.solo(10, 'gentle', [], 0, 0, 0);
  assert.ok(ScoreRules.breakdownEquals(b, ScoreRules.Breakdown(10, 0.5, 1, 5, 0, 0, 0, 5)));
});

test('high scores: places on the table (score, then time; top 5; zero never counts)', () => {
  const table = goldenTable();
  for (const [score, seconds, want] of RANK_GOLDEN) {
    assert.equal(table.rank('solo', 't', score, seconds), want, `${score} in ${seconds} s`);
  }
  assert.deepEqual(table.list('solo', 't').map(e => e.score), [1000, 900, 900, 500, 400]);
  assert.deepEqual(table.list('solo', 't').map(e => e.seconds), [60, 40, 50, 70, 30]);
  assert.equal(table.rank('versus', 't', 10, 10), 1, 'the other table is empty');
  assert.equal(table.rank('solo', 'other', -5, 10), null);
});

test('high scores: a new entry lands in its predicted place and the table keeps 5', () => {
  const table = goldenTable();
  const placed = table.insert('solo', 't', HighScoreEntry({ name: 'New', score: 950, seconds: 10, date: 9000, difficulty: 'expert' }));
  assert.equal(placed, 2);
  assert.equal(table.list('solo', 't').length, 5);
  assert.equal(table.list('solo', 't').at(-1).score, 500);
  assert.equal(table.insert('solo', 't', HighScoreEntry({ name: 'Low', score: 1, seconds: 1, date: 0, difficulty: 'gentle' })), null);
  assert.equal(table.list('solo', 't').length, 5);
});

test('high scores: ties go to the faster time (beyond 0.05 s), then the earlier date', () => {
  const e = (score, seconds, date) => HighScoreEntry({ name: 'x', score, seconds, date, difficulty: 'classic' });
  assert.ok(HighScoreTable.ranksAbove(e(10, 50, 5), e(9, 1, 0)));
  assert.ok(HighScoreTable.ranksAbove(e(10, 49.9, 5), e(10, 50, 0)));
  assert.ok(!HighScoreTable.ranksAbove(e(10, 49.96, 5), e(10, 50, 0)), 'within 0.05 s the date decides');
  assert.ok(HighScoreTable.ranksAbove(e(10, 50.04, 0), e(10, 50, 5)));
  const t = new HighScoreTable();
  t.insert('versus', 'a', e(100, 30, 1));
  assert.equal(t.rank('versus', 'a', 100, 30.02), 2, 'an equal result ranks below the existing one');
  assert.equal(t.rank('versus', 'a', 100, 29), 1);
  const place = t.insert('versus', 'a', e(100, 30.02, 2));
  assert.equal(place, 2);
  assert.equal(t.insert('versus', 'a', e(100, 30, 0)), 1, 'earlier date wins a full tie');
});

test('high scores: 40 random results (tests.py) — predicted place always matches, best 5 kept', () => {
  const t = new HighScoreTable();
  for (const r of fx.inserts) {
    assert.equal(t.rank('solo', 'x', r.score, r.seconds), r.rank, JSON.stringify(r));
    const place = t.insert('solo', 'x', HighScoreEntry({ name: 'p', score: r.score, seconds: r.seconds, date: r.date, difficulty: 'classic' }));
    assert.equal(place, r.place, JSON.stringify(r));
    assert.ok(t.list('solo', 'x').length <= HighScoreTable.keep);
  }
  assert.deepEqual(t.list('solo', 'x').map(e => [e.score, e.seconds, e.date]), fx.finalTable);
});

test('high-score table: JSON round trip, strict decoding, copy, isEmpty', () => {
  const t = goldenTable();
  t.insert('versus', 'firstDig', HighScoreEntry({ name: 'V', score: 812, seconds: 99.5, date: Date.UTC(2026, 9, 18),
    difficulty: 'classic', detail: 'Race · Reach 3 · beat 700' }));
  const back = HighScoreTable.decode(JSON.parse(JSON.stringify(t)));
  assert.ok(back && HighScoreTable.equals(back, t));
  assert.equal(back.list('versus', 'firstDig')[0].detail, 'Race · Reach 3 · beat 700');
  const json = JSON.parse(JSON.stringify(t));
  assert.deepEqual(Object.keys(json), ['solo', 'versus']);
  assert.deepEqual(Object.keys(json.solo.t[0]), ['id', 'name', 'score', 'seconds', 'date', 'difficulty', 'modifiers', 'detail']);
  assert.match(json.solo.t[0].id, /^[0-9A-F]{8}-[0-9A-F]{4}-4[0-9A-F]{3}-[89AB][0-9A-F]{3}-[0-9A-F]{12}$/);
  json.solo.t[0].difficulty = 'impossible';
  assert.equal(HighScoreTable.decode(json), null, 'an unknown raw value fails the table, like Swift');
  assert.equal(HighScoreTable.decode({ solo: {} }), null);
  const c = t.copy();
  c.insert('solo', 't', HighScoreEntry({ name: 'C', score: 5000, seconds: 1, date: 0, difficulty: 'classic' }));
  assert.equal(t.list('solo', 't')[0].score, 1000, 'copy() is independent');
  assert.ok(new HighScoreTable().isEmpty);
  assert.ok(!t.isEmpty);
  assert.deepEqual(HighScoreKind.allCases.map(HighScoreKind.title), ['Solo', 'Two players']);
  const iso = HighScoreEntry.decode({ ...JSON.parse(JSON.stringify(t)).solo.t[0], date: '1970-01-01T00:00:01Z' });
  assert.equal(iso.date, 1000, 'ISO dates are read as epoch ms');
});

test('names: trimmed, new lines become spaces, at most 20 characters, empty → "Player"', () => {
  assert.equal(HighScoreNames.clean('  Ana  '), 'Ana');
  assert.equal(HighScoreNames.clean(''), 'Player');
  assert.equal(HighScoreNames.clean(' \n\t '), 'Player');
  assert.equal(HighScoreNames.clean('x'.repeat(40)).length, 20);
  assert.equal(HighScoreNames.clean('Ana\nBo'), 'Ana Bo');
  assert.equal(HighScoreNames.clean('  Zoë '), 'Zoë');
  const family = '\u{1F468}‍\u{1F469}‍\u{1F467}';
  assert.equal(HighScoreNames.clean(family.repeat(25)), family.repeat(20), 'Swift counts characters (grapheme clusters)');
  assert.equal(HighScoreNames.maxLength, 20);
});

test('time text: m:ss', () => {
  const cases = [[0, '0:00'], [59.9, '0:59'], [60, '1:00'], [61.5, '1:01'], [3599, '59:59'], [3600, '60:00'],
    [-5, '0:00'], [NaN, '0:00'], [Infinity, '0:00'], [1e12, '16666666:40']];
  for (const [s, want] of cases) assert.equal(TimeText.mmss(s), want, String(s));
});

test('rating filter', () => {
  assert.deepEqual(RatingFilter.allCases.map(RatingFilter.title), ['All', 'Easy', 'Medium', 'Hard', 'Fiendish']);
  assert.deepEqual(RatingFilter.allCases.map(f => [RatingFilter.levels(f).lowerBound, RatingFilter.levels(f).upperBound]),
    [[1, 5], [1, 2], [3, 3], [4, 4], [5, 5]]);
  assert.deepEqual(RatingFilter.allCases.map(RatingFilter.dotLevel), [0, 1, 3, 4, 5]);
  assert.ok(RatingFilter.levels('easy').contains(2) && !RatingFilter.levels('easy').contains(3));
});

test('No colour twice on First Dig: a repeat is refused only while another colour could go (SelfTest)', () => {
  const fd = GeneratedLevels.firstDig;
  const board = new Board(fd.art);
  const g = new Game(fd, board, fd.chambersExpert);
  let last = null;
  let bad = 0;
  let refusedSeen = 0;
  for (const q of fd.solution) {
    for (let k = 0; k < g.tunnels.length; k++) {
      const refused = ColourRule.refuses(g, k, last);
      if (refused) refusedSeen += 1;
      const same = last !== null && g.front(k)?.family === last;
      if (refused && !same) bad += 1;
    }
    last = g.front(q)?.family ?? null;
    g.dispatch(q);
  }
  assert.equal(bad, 0);
  assert.ok(g.isWon);
  assert.equal(ColourRule.refuses(g, 0, null), false);
});

test('No colour twice agrees with Tools/scoring.py: designed lines, careless walks and searched winning lines', () => {
  const legal = (g, last) => {
    const out = [];
    for (let k = 0; k < g.tunnels.length; k++) if (g.canDispatch(k) && !ColourRule.refuses(g, k, last)) out.push(k);
    return out;
  };
  for (const rec of fx.colourRule) {
    const level = GeneratedLevels[rec.level];
    const board = new Board(level.art);
    // the designed line on Expert
    let g = new Game(level, board, rec.capacity);
    let last = null;
    level.solution.forEach((q, i) => {
      assert.deepEqual(legal(g, last), rec.solutionLegal[i], `${rec.level} solution step ${i}`);
      last = g.front(q).family;
      g.dispatch(q);
    });
    // careless walks under the rule
    for (const w of rec.walks) {
      g = new Game(level, board, w.capacity);
      last = null;
      w.steps.forEach(([ok, q], i) => {
        assert.deepEqual(legal(g, last), ok, `${rec.level} walk step ${i}`);
        if (q !== null) {
          last = g.front(q).family;
          g.dispatch(q);
        }
      });
      assert.equal(g.state.cleared, w.cleared);
      assert.equal(g.isJammed, w.jammed);
    }
    // the reference search's winning line obeys the rule here too
    assert.ok(rec.lineChecks, `${rec.level}: reference line found`);
    g = new Game(level, board, rec.capacity);
    last = null;
    for (const q of rec.line) {
      assert.ok(legal(g, last).includes(q));
      last = g.front(q).family;
      g.dispatch(q);
      assert.ok(!g.isJammed);
    }
    assert.ok(g.isWon, `${rec.level}: winning line`);
  }
});
