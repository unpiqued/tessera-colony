// Port of Scoring.swift: harder options, the solo score, high-score tables, Home's rating filter,
// the No colour twice rule, high-score names and time text. Mirrors Tools/scoring.py.
//
// Dates: every date here is epoch milliseconds (a number, as Date.now() returns). Swift's
// Date.distantFuture (the rank probe) is Infinity.
// Sets of ChallengeModifier: pass a Set or an array of raw values; results that Swift returns as
// arrays come back in ChallengeModifier.allCases order.

import { Difficulty, swiftRounded } from './level.js';

// MARK: - ChallengeModifier

const MODIFIER_INFO = {
  hiddenQueue: {
    title: 'Hidden queue', bonus: 0.20, systemImage: 'eye.slash',
    blurb: 'Only the front team of each tunnel is shown.',
  },
  noScout: {
    title: 'No scouting', bonus: 0.10, systemImage: 'binoculars',
    blurb: 'Press-and-hold scouting and Gentle’s “can finish” badges are off.',
  },
  noHints: {
    title: 'No hints', bonus: 0.10, systemImage: 'lightbulb.slash',
    blurb: 'The hint button is off.',
  },
  limitedUndo: {
    title: '3 undos', bonus: 0.20, systemImage: 'arrow.uturn.backward.circle',
    blurb: 'Only 3 undos for the whole game.',
  },
  noAssists: {
    title: 'No assists', bonus: 0.15, systemImage: 'hand.raised.slash',
    blurb: 'No adding slots and no returning waiting teams.',
  },
  noRepeatColour: {
    title: 'No colour twice', bonus: 0.25, systemImage: 'circle.lefthalf.filled',
    blurb: "Never send the same colour twice in a row (allowed only when nothing else can go). Hints don't know this rule.",
  },
};

function toSet(mods) {
  if (mods instanceof Set) return mods;
  return new Set(mods ?? []);
}

/**
 * Optional rules that make any mosaic harder, chosen on the start card. Each one adds to the
 * score multiplier. None of them can make a mosaic unsolvable: the designed solution uses no
 * scouting, hints, undo or assists, and it never needs to see past the front of a tunnel.
 * Helpers take the raw value: ChallengeModifier.title(m), .blurb(m), .systemImage(m), .bonus(m).
 */
export const ChallengeModifier = Object.freeze({
  hiddenQueue: 'hiddenQueue',
  noScout: 'noScout',
  noHints: 'noHints',
  limitedUndo: 'limitedUndo',
  noAssists: 'noAssists',
  noRepeatColour: 'noRepeatColour',
  allCases: Object.freeze(['hiddenQueue', 'noScout', 'noHints', 'limitedUndo', 'noAssists', 'noRepeatColour']),
  isValid(m) { return typeof m === 'string' && Object.prototype.hasOwnProperty.call(MODIFIER_INFO, m); },
  id(m) { return m; },
  title(m) { return MODIFIER_INFO[m].title; },
  blurb(m) { return MODIFIER_INFO[m].blurb; },
  /** SF Symbol name (the integrator maps it to an icon). */
  systemImage(m) { return MODIFIER_INFO[m].systemImage; },
  /** Added to the score multiplier (0.2 = +20%). */
  bonus(m) { return MODIFIER_INFO[m].bonus; },
  undoLimit: 3,
  /** Stable order for display and saving (a Set or array in, an array out). */
  sorted(set) {
    const s = toSet(set);
    return ChallengeModifier.allCases.filter(m => s.has(m));
  },
});

// MARK: - ScoreRules

/**
 * How a finished solo game is scored (mirrors Tools/scoring.py).
 *   score = tiles × difficulty factor × (1 + harder-option bonuses)
 *           − 5 per undo − 25 per hint − 25 per assist (never below 0)
 * Ties on the high-score table go to the faster time.
 * (Two-player scores are tallied by VersusController: tiles home + finish bonus − VersusMatch.penalties.)
 */
export const ScoreRules = Object.freeze({
  undoPenalty: 5.0,
  hintPenalty: 25.0,
  assistPenalty: 25.0,

  difficultyFactor(d) {
    switch (d) {
      case 'gentle': return 0.5;
      case 'classic': return 1.0;
      case 'expert': return 1.5;
      default: throw new Error(`Unknown difficulty ${d}`);
    }
  },

  /** Summed in a fixed order so the result never depends on Set ordering. */
  modifierFactor(mods) {
    return ChallengeModifier.sorted(mods).reduce((acc, m) => acc + ChallengeModifier.bonus(m), 1.0);
  },

  /** ScoreRules.Breakdown: a plain object with these fields. */
  Breakdown(tiles, difficultyFactor, modifierFactor, base, undoPenalty, hintPenalty, assistPenalty, score) {
    return { tiles, difficultyFactor, modifierFactor, base, undoPenalty, hintPenalty, assistPenalty, score };
  },

  breakdownEquals(a, b) {
    return a.tiles === b.tiles && a.difficultyFactor === b.difficultyFactor && a.modifierFactor === b.modifierFactor
      && a.base === b.base && a.undoPenalty === b.undoPenalty && a.hintPenalty === b.hintPenalty
      && a.assistPenalty === b.assistPenalty && a.score === b.score;
  },

  /** Swift solo(tiles:difficulty:modifiers:undos:hints:assists:) */
  solo(tiles, difficulty, modifiers, undos, hints, assists) {
    const df = ScoreRules.difficultyFactor(difficulty);
    const mf = ScoreRules.modifierFactor(modifiers);
    const base = swiftRounded(tiles * df * mf);
    const u = Math.trunc(undos * ScoreRules.undoPenalty);
    const h = Math.trunc(hints * ScoreRules.hintPenalty);
    const a = Math.trunc(assists * ScoreRules.assistPenalty);
    return ScoreRules.Breakdown(tiles, df, mf, base, u, h, a, Math.max(0, base - u - h - a));
  },
});

// MARK: - High scores

function newUUID() {
  const c = globalThis.crypto;
  if (c && typeof c.randomUUID === 'function') return c.randomUUID().toUpperCase();
  const hex = [];
  for (let i = 0; i < 32; i++) hex.push(Math.floor(Math.random() * 16).toString(16));
  hex[12] = '4';
  hex[16] = (8 + Math.floor(Math.random() * 4)).toString(16);
  const s = hex.join('').toUpperCase();
  return `${s.slice(0, 8)}-${s.slice(8, 12)}-${s.slice(12, 16)}-${s.slice(16, 20)}-${s.slice(20)}`;
}

/**
 * One line on a high-score table (a plain object):
 * { id: UUID string, name, score, seconds, date: epoch ms, difficulty, modifiers: [ChallengeModifier], detail }
 * `difficulty` — solo: the difficulty played; two players: the slots setting.
 * `detail` — two players: the options and the result ("Race · Reach 3 … · beat 812").
 */
export function HighScoreEntry({ id = newUUID(), name, score, seconds, date, difficulty, modifiers = [], detail = '' }) {
  return {
    id, name, score, seconds,
    date: date instanceof Date ? date.getTime() : date,
    difficulty, modifiers: Array.from(modifiers), detail,
  };
}

HighScoreEntry.equals = (a, b) => a.id === b.id && a.name === b.name && a.score === b.score
  && a.seconds === b.seconds && a.date === b.date && a.difficulty === b.difficulty
  && a.detail === b.detail && a.modifiers.length === b.modifiers.length
  && a.modifiers.every((m, i) => m === b.modifiers[i]);

HighScoreEntry.copy = e => ({ ...e, modifiers: e.modifiers.slice() });

/**
 * Strict decoding of a stored entry (like Swift's synthesized Codable: every key required, raw
 * values must be known). Dates may be epoch ms or an ISO string. Returns null when invalid.
 */
HighScoreEntry.decode = o => {
  if (!o || typeof o !== 'object') return null;
  if (typeof o.id !== 'string' || typeof o.name !== 'string' || !Number.isInteger(o.score)
    || typeof o.seconds !== 'number' || !Difficulty.isValid(o.difficulty)
    || !Array.isArray(o.modifiers) || !o.modifiers.every(ChallengeModifier.isValid)
    || typeof o.detail !== 'string') return null;
  let date = o.date;
  if (typeof date === 'string') date = Date.parse(date);
  if (typeof date !== 'number' || Number.isNaN(date)) return null;
  return HighScoreEntry({ id: o.id, name: o.name, score: o.score, seconds: o.seconds, date,
    difficulty: o.difficulty, modifiers: o.modifiers, detail: o.detail });
};

const KIND_TITLES = { solo: 'Solo', versus: 'Two players' };

/** enum HighScoreKind: 'solo' | 'versus'. HighScoreKind.title(k). */
export const HighScoreKind = Object.freeze({
  solo: 'solo',
  versus: 'versus',
  allCases: Object.freeze(['solo', 'versus']),
  isValid(k) { return k === 'solo' || k === 'versus'; },
  id(k) { return k; },
  title(k) { return KIND_TITLES[k]; },
});

function dict() { return Object.create(null); }

/**
 * Top scores per mosaic, one table for solo games and one for two-player winners.
 * `solo` and `versus` are null-prototype objects: levelID → [HighScoreEntry] (best first).
 * Swift copies the struct on assignment; use copy() where that matters.
 */
export class HighScoreTable {
  static keep = 5;

  constructor() {
    this.solo = dict();
    this.versus = dict();
  }

  list(kind, levelID) {
    const d = kind === 'solo' ? this.solo : this.versus;
    return d[levelID] ?? [];
  }

  /** True when `a` ranks above `b`: higher score, then faster time, then earlier date. */
  static ranksAbove(a, b) {
    if (a.score !== b.score) return a.score > b.score;
    if (Math.abs(a.seconds - b.seconds) > 0.05) return a.seconds < b.seconds;
    return a.date < b.date;
  }

  /** The place (1-based) a new score would take, or null when it wouldn't make the table. */
  rank(kind, levelID, score, seconds) {
    if (!(score > 0)) return null;
    const probe = { name: '', score, seconds, date: Infinity, difficulty: 'classic' };
    const better = this.list(kind, levelID).filter(e => HighScoreTable.ranksAbove(e, probe)).length;
    return better < HighScoreTable.keep ? better + 1 : null;
  }

  /** Adds an entry (keeping the best `keep`) and returns its place, or null if it didn't make it. */
  insert(kind, levelID, entry) {
    let l = this.list(kind, levelID).slice();
    l.push(entry);
    l.sort((a, b) => (HighScoreTable.ranksAbove(a, b) ? -1 : HighScoreTable.ranksAbove(b, a) ? 1 : 0));
    if (l.length > HighScoreTable.keep) l = l.slice(0, HighScoreTable.keep);
    if (kind === 'solo') this.solo[levelID] = l; else this.versus[levelID] = l;
    const i = l.findIndex(e => e.id === entry.id);
    return i >= 0 ? i + 1 : null;
  }

  get isEmpty() {
    return Object.values(this.solo).every(l => l.length === 0) && Object.values(this.versus).every(l => l.length === 0);
  }

  copy() {
    const t = new HighScoreTable();
    for (const k of Object.keys(this.solo)) t.solo[k] = this.solo[k].map(HighScoreEntry.copy);
    for (const k of Object.keys(this.versus)) t.versus[k] = this.versus[k].map(HighScoreEntry.copy);
    return t;
  }

  static equals(a, b) {
    const same = (x, y) => {
      const kx = Object.keys(x), ky = Object.keys(y);
      if (kx.length !== ky.length) return false;
      return kx.every(k => y[k] !== undefined && x[k].length === y[k].length
        && x[k].every((e, i) => HighScoreEntry.equals(e, y[k][i])));
    };
    return same(a.solo, b.solo) && same(a.versus, b.versus);
  }

  /** The Codable shape: { solo: {levelID: [entry]}, versus: {…} }. */
  toJSON() { return { solo: this.solo, versus: this.versus }; }

  /** Strict decoding (any invalid entry → null, as Swift's decoder fails the whole table). */
  static decode(o) {
    if (!o || typeof o !== 'object' || !o.solo || !o.versus
      || typeof o.solo !== 'object' || typeof o.versus !== 'object') return null;
    const t = new HighScoreTable();
    for (const [kind, src] of [['solo', o.solo], ['versus', o.versus]]) {
      for (const k of Object.keys(src)) {
        if (!Array.isArray(src[k])) return null;
        const l = [];
        for (const e of src[k]) {
          const d = HighScoreEntry.decode(e);
          if (!d) return null;
          l.push(d);
        }
        t[kind][k] = l;
      }
    }
    return t;
  }
}

// MARK: - RatingFilter

const RATING_FILTER_INFO = {
  all: { title: 'All', lo: 1, hi: 5, dot: 0 },
  easy: { title: 'Easy', lo: 1, hi: 2, dot: 1 },
  medium: { title: 'Medium', lo: 3, hi: 3, dot: 3 },
  hard: { title: 'Hard', lo: 4, hi: 4, dot: 4 },
  fiendish: { title: 'Fiendish', lo: 5, hi: 5, dot: 5 },
};

function closedRange(lowerBound, upperBound) {
  return Object.freeze({ lowerBound, upperBound, contains(x) { return x >= lowerBound && x <= upperBound; } });
}

/**
 * Home's difficulty filter: which ratings to show (measured on the chosen difficulty).
 * RatingFilter.title(f); RatingFilter.levels(f) → { lowerBound, upperBound, contains(level) }.
 */
export const RatingFilter = Object.freeze({
  all: 'all',
  easy: 'easy',
  medium: 'medium',
  hard: 'hard',
  fiendish: 'fiendish',
  allCases: Object.freeze(['all', 'easy', 'medium', 'hard', 'fiendish']),
  isValid(f) { return typeof f === 'string' && Object.prototype.hasOwnProperty.call(RATING_FILTER_INFO, f); },
  id(f) { return f; },
  title(f) { return RATING_FILTER_INFO[f].title; },
  /** Rating levels (1 Relaxed … 5 Fiendish) this filter keeps (Swift ClosedRange). */
  levels(f) { const i = RATING_FILTER_INFO[f]; return closedRange(i.lo, i.hi); },
  dotLevel(f) { return RATING_FILTER_INFO[f].dot; },
});

// MARK: - ColourRule

/**
 * The No colour twice option (mirrors colour_rule_legal in Tools/scoring.py): the same colour as
 * the last team sent is refused while another tunnel could send a different colour.
 * `last` is the family sent last, or null.
 */
export const ColourRule = Object.freeze({
  /** Swift refuses(game:tunnel:last:) */
  refuses(game, q, last) {
    if (last === null || last === undefined) return false;
    const fr = game.front(q);
    if (!fr || fr.family !== last) return false;
    for (let k = 0; k < game.tunnels.length; k++) {
      if (k === q || !game.canDispatch(k)) continue;
      const f = game.front(k);
      if (f && f.family !== last) return true;
    }
    return false;
  },
});

// MARK: - Names and time

// Swift's CharacterSet.whitespacesAndNewlines: Unicode Z* plus tab, U+000A…U+000D and U+0085.
const EDGE_SPACE = /^[\p{Z}\t\n\v\f\r\u0085]+|[\p{Z}\t\n\v\f\r\u0085]+$/gu;

function graphemes(s) {
  if (typeof Intl !== 'undefined' && typeof Intl.Segmenter === 'function') {
    return Array.from(new Intl.Segmenter(undefined, { granularity: 'grapheme' }).segment(s), x => x.segment);
  }
  return Array.from(s);
}

export const HighScoreNames = Object.freeze({
  maxLength: 20,

  /** Trims spaces and new lines, keeps at most 20 characters; an empty name becomes "Player". */
  clean(raw) {
    const t = String(raw).replace(EDGE_SPACE, '').replace(/\n/g, ' ');
    const short = graphemes(t).slice(0, HighScoreNames.maxLength).join('');
    return short.length === 0 ? 'Player' : short;
  },
});

export const TimeText = Object.freeze({
  /** "m:ss" for a time in seconds. */
  mmss(seconds) {
    const s = Number.isFinite(seconds) ? Math.max(0, Math.trunc(Math.min(seconds, 1e9))) : 0;
    return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
  },
});
