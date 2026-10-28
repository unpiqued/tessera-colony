// Port of SaveStore.swift (SaveGame, CompletionRecord, CompletionNews, AppSettings, SaveStore) and
// the data half of PhotoLibrary.swift (PhotoLevelRecord and its storage).
//
// Storage goes through an injected synchronous backend:
//   SaveStore.setBackend({ getItem(key) → string|null, setItem(key, string), removeItem(key) })
// (the default is an in-memory Map; the integrator passes a localStorage wrapper). Keys and JSON
// record shapes are the Swift ones (UserDefaults keys; Codable field names):
//   tessera.settings.v2        AppSettings
//   tessera.progress.v1        { levelID: CompletionRecord }
//   tessera.highscores.v1      HighScoreTable { solo: {levelID: [entry]}, versus: {…} }
//   tessera.save.v3.<levelID>  SaveGame
//   PhotoMosaics/<id>.json     PhotoLevelRecord (Swift: Documents/PhotoMosaics/<id>.json)
//   PhotoMosaics/index.json    [id] — the web backend cannot list keys, so the folder listing is kept here
// Dates are epoch milliseconds (numbers). Swift wrote Date as seconds since 2001 (deferredToDate);
// nothing is shared with the iPad, so the web build uses Date.now() values throughout.
// Like Swift's `try?`, a storage or decoding failure never throws: loads fall back to defaults.

import { Difficulty, LevelDefinition, LevelPalette, GeneratedPalette, TeamSpec } from './level.js';
import { ChallengeModifier, HighScoreTable, RatingFilter } from './scoring.js';
import { VersusRules } from './versus.js';

// Raw values of enums defined in other modules (PathStyle: render/PathPlanner, PhotoDetail:
// builders/PhotoLevelBuilder, StatusFilter: collection.js — importing it would be circular).
// Used only to validate stored settings, exactly as Swift's decoder rejects unknown raw values.
const PATH_STYLE_VALUES = ['direct', 'natural', 'curious', 'wall', 'scout', 'randomTeam', 'randomAnt'];
const PHOTO_DETAIL_VALUES = ['coarse', 'fine', 'veryFine'];
export const STATUS_FILTER_VALUES = Object.freeze(['all', 'toExplore', 'explored', 'goHarder', 'mastered']);

// MARK: - type checks (Swift JSONDecoder semantics)

const isInt = v => Number.isSafeInteger(v);
const isDouble = v => typeof v === 'number' && Number.isFinite(v);
const isBool = v => typeof v === 'boolean';
const isString = v => typeof v === 'string';
const isUInt32 = v => Number.isInteger(v) && v >= 0 && v <= 0xFFFFFFFF;
const isArrayOf = (v, f) => Array.isArray(v) && v.every(f);
const isObject = v => v !== null && typeof v === 'object' && !Array.isArray(v);
const has = (o, k) => Object.prototype.hasOwnProperty.call(o, k);
/** decodeIfPresent: missing or null → absent (undefined); present and valid → value; invalid → throws. */
class DecodeError extends Error {}
function optional(o, k, check) {
  if (!has(o, k) || o[k] === null) return undefined;
  if (!check(o[k])) throw new DecodeError(k);
  return o[k];
}
function required(o, k, check) {
  if (!has(o, k) || !check(o[k])) throw new DecodeError(k);
  return o[k];
}
function dateMs(v) {
  if (v instanceof Date) return v.getTime();
  if (typeof v === 'string') return Date.parse(v);
  return v;
}

// MARK: - Records

/**
 * An in-progress game (one per level).
 * SaveGame({ version = 1, levelID, difficulty, moves, undos, hints, elapsed, modifiers = null })
 * `modifiers`: harder options this game was started with (null in saves from older builds).
 */
export function SaveGame({ version = 1, levelID, difficulty, moves, undos, hints, elapsed, modifiers = null }) {
  return { version, levelID, difficulty, moves: Array.from(moves), undos, hints, elapsed,
    modifiers: modifiers === null || modifiers === undefined ? null : Array.from(modifiers) };
}

/** The stored shape: a nil `modifiers` is left out, as Swift's encoder does. */
SaveGame.encode = g => {
  const o = { version: g.version, levelID: g.levelID, difficulty: g.difficulty, moves: g.moves.slice(),
    undos: g.undos, hints: g.hints, elapsed: g.elapsed };
  if (g.modifiers !== null && g.modifiers !== undefined) o.modifiers = g.modifiers.slice();
  return o;
};

/** Strict decoding (synthesized Codable); null when invalid. */
SaveGame.decode = o => {
  try {
    if (!isObject(o)) return null;
    return SaveGame({
      version: required(o, 'version', isInt),
      levelID: required(o, 'levelID', isString),
      difficulty: required(o, 'difficulty', Difficulty.isValid),
      moves: required(o, 'moves', v => isArrayOf(v, isInt)),
      undos: required(o, 'undos', isInt),
      hints: required(o, 'hints', isInt),
      elapsed: required(o, 'elapsed', isDouble),
      modifiers: optional(o, 'modifiers', v => isArrayOf(v, ChallengeModifier.isValid)) ?? null,
    });
  } catch (e) {
    if (e instanceof DecodeError) return null;
    throw e;
  }
};

/**
 * Progress on one level.
 * CompletionRecord({ bestSeconds, fewestUndos, difficulty, completions, bestByDifficulty = null, expertModifiers = null })
 * `bestByDifficulty`: best time per difficulty ({ gentle?, classic?, expert? }); null in records from older builds.
 * `expertModifiers`: most harder options used in a finish on Expert (1 or more = mastered); null if never.
 */
export function CompletionRecord({ bestSeconds, fewestUndos, difficulty, completions, bestByDifficulty = null, expertModifiers = null }) {
  return { bestSeconds, fewestUndos, difficulty, completions,
    bestByDifficulty: bestByDifficulty ? { ...bestByDifficulty } : null,
    expertModifiers: expertModifiers ?? null };
}

/** A value copy (Swift structs copy on assignment). */
CompletionRecord.copy = r => CompletionRecord(r);

/** The stored shape: nil optionals are left out, as Swift's encoder does. */
CompletionRecord.encode = r => {
  const o = { bestSeconds: r.bestSeconds, fewestUndos: r.fewestUndos, difficulty: r.difficulty, completions: r.completions };
  if (r.bestByDifficulty !== null && r.bestByDifficulty !== undefined) o.bestByDifficulty = { ...r.bestByDifficulty };
  if (r.expertModifiers !== null && r.expertModifiers !== undefined) o.expertModifiers = r.expertModifiers;
  return o;
};

CompletionRecord.decode = o => {
  try {
    if (!isObject(o)) return null;
    return CompletionRecord({
      bestSeconds: required(o, 'bestSeconds', isDouble),
      fewestUndos: required(o, 'fewestUndos', isInt),
      difficulty: required(o, 'difficulty', Difficulty.isValid),
      completions: required(o, 'completions', isInt),
      bestByDifficulty: optional(o, 'bestByDifficulty', v => isObject(v) && Object.values(v).every(isDouble)) ?? null,
      expertModifiers: optional(o, 'expertModifiers', isInt) ?? null,
    });
  } catch (e) {
    if (e instanceof DecodeError) return null;
    throw e;
  }
};

/**
 * What a finish achieved (drives the goal sounds and the win card).
 * CompletionNews({ newBest, firstClear, unlocked, stars = 0, newStar = false, mastered = false })
 * newBest: beat an earlier time on the same difficulty. unlocked: titles of mosaics this finish made
 * playable (unlocked or found). stars: stars now (1 Gentle … 3 Expert); newStar: this finish added
 * one. mastered: this finish mastered the mosaic (Expert with a harder option) for the first time.
 */
export function CompletionNews({ newBest, firstClear, unlocked, stars = 0, newStar = false, mastered = false }) {
  return { newBest, firstClear, unlocked, stars, newStar, mastered };
}

// MARK: - AppSettings

/**
 * The player's settings, a plain object. AppSettings() gives the defaults:
 *   difficulty 'classic'; antSpeed 1.0 (0.1 ... 16; 1 = four tiles per second); detailedAnts true;
 *   coachSeen [] (CoachStep raw values); hasLaunchedBefore false; photoDetail 'fine';
 *   groundColor GeneratedPalette.soil (0xRRGGBB behind the mosaic); unlockAll false; soundOn true;
 *   soundVolume 0.8 (0 ... 1); tileClicks true; actionSounds true; goalSounds true;
 *   pathStyle 'randomTeam'; pathStyleVersion 2; soundInSilentMode true; versusRules VersusRules();
 *   versusLevelID 'firstDig'; playerName ''; lastModifiers []; ratingFilter 'all';
 *   statusFilter 'all'; versusRulesVersion 2; mixWithOtherAudio true (web only).
 */
export function AppSettings() {
  return {
    difficulty: 'classic',
    /** Ant speed multiplier (0.1 ... 16). 1 = four tiles (about two ant lengths) per second. */
    antSpeed: 1.0,
    detailedAnts: true,
    coachSeen: [],
    hasLaunchedBefore: false,
    photoDetail: 'fine',
    /** Colour of the ground behind the mosaic (margin and cleared tiles), 0xRRGGBB. */
    groundColor: GeneratedPalette.soil,
    /** Play any built-in mosaic without finishing the one before it. */
    unlockAll: false,
    /** Sound effects (all synthesized on the device). */
    soundOn: true,
    /** 0 ... 1 */
    soundVolume: 0.8,
    /** The little clinks as ants lift tiles and drop them in the nest ("colony" layer). */
    tileClicks: true,
    /** Wood-and-clay sounds for the moves you make. */
    actionSounds: true,
    /** Bell-and-glass sounds for goals reached. */
    goalSounds: true,
    /** How newly launched ants choose their route (default: each team picks a style at random). */
    pathStyle: 'randomTeam',
    /** 2 = the default path style is Random per team (older builds defaulted to Natural). */
    pathStyleVersion: 2,
    /** Play sounds even when the device is in Silent mode. */
    soundInSilentMode: true,
    /** Last two-player options and mosaic. */
    versusRules: VersusRules(),
    versusLevelID: 'firstDig',
    /** Name last typed for a high score (pre-filled next time). */
    playerName: '',
    /** Harder options last chosen on the start card. */
    lastModifiers: [],
    /** Home's difficulty filter. */
    ratingFilter: 'all',
    /** Home's status filter (to explore, explored, go harder, mastered). */
    statusFilter: 'all',
    /** 2 = two-player colour rule defaults to Any colour (older builds defaulted to No colour twice). */
    versusRulesVersion: 2,
    /**
     * Web only: let podcasts and music keep playing (audio session 'ambient'; on iPhone the game's
     * sounds then follow the Ring/Silent switch). Off: soundInSilentMode applies ('playback', which
     * pauses other audio).
     */
    mixWithOtherAudio: true,
  };
}

/** Field names in Swift declaration order (also the encoded key order). */
AppSettings.keys = Object.freeze(Object.keys({
  difficulty: 0, antSpeed: 0, detailedAnts: 0, coachSeen: 0, hasLaunchedBefore: 0, photoDetail: 0,
  groundColor: 0, unlockAll: 0, soundOn: 0, soundVolume: 0, tileClicks: 0, actionSounds: 0, goalSounds: 0,
  pathStyle: 0, pathStyleVersion: 0, soundInSilentMode: 0, versusRules: 0, versusLevelID: 0, playerName: 0,
  lastModifiers: 0, ratingFilter: 0, statusFilter: 0, versusRulesVersion: 0, mixWithOtherAudio: 0,
}));

/** A deep value copy (works on the live settings object of AppModel too). */
AppSettings.copy = s => {
  const out = {};
  for (const k of Object.keys(s)) {
    const v = s[k];
    if (Array.isArray(v)) out[k] = v.slice();
    else if (v !== null && typeof v === 'object') out[k] = { ...v };
    else out[k] = v;
  }
  return out;
};

/** The JSON-ready record (Swift's synthesized encode: every field, declaration order). */
AppSettings.encode = s => {
  const out = {};
  for (const k of AppSettings.keys) {
    const v = s[k];
    out[k] = Array.isArray(v) ? v.slice() : (v !== null && typeof v === 'object') ? { ...v } : v;
  }
  return out;
};

/**
 * Tolerant decoding (Swift init(from:)): a missing or unknown key keeps its default instead of
 * resetting everything; includes the one-time pathStyle and versusRules migrations.
 */
AppSettings.decode = o => {
  const s = AppSettings();
  if (!isObject(o)) return s;
  const take = (k, check, fallback) => (has(o, k) && o[k] !== null && check(o[k]) ? o[k] : fallback);
  s.difficulty = take('difficulty', Difficulty.isValid, 'classic');
  s.antSpeed = take('antSpeed', isDouble, 1.0);
  s.detailedAnts = take('detailedAnts', isBool, true);
  s.coachSeen = take('coachSeen', v => isArrayOf(v, isString), []).slice();
  s.hasLaunchedBefore = take('hasLaunchedBefore', isBool, false);
  s.photoDetail = take('photoDetail', v => PHOTO_DETAIL_VALUES.includes(v), 'fine');
  s.groundColor = take('groundColor', isUInt32, GeneratedPalette.soil);
  s.unlockAll = take('unlockAll', isBool, false);
  s.soundOn = take('soundOn', isBool, true);
  s.soundVolume = take('soundVolume', isDouble, 0.8);
  s.tileClicks = take('tileClicks', isBool, true);
  s.actionSounds = take('actionSounds', isBool, true);
  s.goalSounds = take('goalSounds', isBool, true);
  s.pathStyle = take('pathStyle', v => PATH_STYLE_VALUES.includes(v), 'randomTeam');
  s.pathStyleVersion = take('pathStyleVersion', isInt, 1);
  if (s.pathStyleVersion < 2) {
    // settings saved by older builds hold the old default (Natural): move them to the new one once
    if (s.pathStyle === 'natural') s.pathStyle = 'randomTeam';
    s.pathStyleVersion = 2;
  }
  s.soundInSilentMode = take('soundInSilentMode', isBool, true);
  s.versusRules = (has(o, 'versusRules') && VersusRules.decode(o.versusRules)) || VersusRules();
  s.versusLevelID = take('versusLevelID', isString, 'firstDig');
  s.playerName = take('playerName', isString, '');
  s.lastModifiers = take('lastModifiers', v => isArrayOf(v, ChallengeModifier.isValid), []).slice();
  s.ratingFilter = take('ratingFilter', RatingFilter.isValid, 'all');
  s.statusFilter = take('statusFilter', v => STATUS_FILTER_VALUES.includes(v), 'all');
  s.versusRulesVersion = take('versusRulesVersion', isInt, 1);
  if (s.versusRulesVersion < 2) {
    // the old default limited each launch to a different colour; lift it once
    s.versusRules.colour = 'any';
    s.versusRulesVersion = 2;
  }
  s.mixWithOtherAudio = take('mixWithOtherAudio', isBool, true);
  return s;
};

// MARK: - Backend

/** A fresh in-memory backend (the default; also handy for tests). `map` exposes the stored strings. */
function memoryBackend() {
  const map = new Map();
  return {
    map,
    getItem(key) { return map.has(key) ? map.get(key) : null; },
    setItem(key, value) { map.set(key, String(value)); },
    removeItem(key) { map.delete(key); },
  };
}

let backend = memoryBackend();
let lastError = null;

function getItem(key) {
  try {
    const v = backend.getItem(key);
    return v === undefined ? null : v;
  } catch (e) {
    lastError = e;
    return null;
  }
}
function setItem(key, value) {
  try {
    backend.setItem(key, value);
    return true;
  } catch (e) {
    lastError = e;
    return false;
  }
}
function removeItem(key) {
  try {
    backend.removeItem(key);
  } catch (e) {
    lastError = e;
  }
}
function readJSON(key) {
  const s = getItem(key);
  if (s === null) return undefined;
  try {
    return JSON.parse(s);
  } catch (e) {
    lastError = e;
    return undefined;
  }
}
function writeJSON(key, value) {
  let s;
  try {
    s = JSON.stringify(value);
  } catch (e) {
    lastError = e;
    return false;
  }
  return setItem(key, s);
}

const settingsKey = 'tessera.settings.v2';
const progressKey = 'tessera.progress.v1';
const highScoreKey = 'tessera.highscores.v1';
const gameKey = id => 'tessera.save.v3.' + id;
const photoFolder = 'PhotoMosaics/';
const photoKey = id => photoFolder + id + '.json';
const photoIndexKey = photoFolder + 'index.json';

/** Small JSON blobs: settings, per-level progress, high scores and one in-progress game per level. */
export const SaveStore = Object.freeze({
  /** Installs the storage backend: { getItem(key) → string|null, setItem(key, string), removeItem(key) }. */
  setBackend(b) {
    if (!b || typeof b.getItem !== 'function' || typeof b.setItem !== 'function' || typeof b.removeItem !== 'function') {
      throw new Error('SaveStore.setBackend: expected { getItem, setItem, removeItem }');
    }
    backend = b;
  },
  get backend() { return backend; },
  memoryBackend,
  /** The last storage or parse error swallowed (null if none) — for diagnostics only. */
  get lastError() { return lastError; },

  keys: Object.freeze({ settingsKey, progressKey, highScoreKey, gameKey, photoKey, photoIndexKey }),

  loadSettings() {
    const o = readJSON(settingsKey);
    return o === undefined ? AppSettings() : AppSettings.decode(o);
  },

  saveSettings(s) { writeJSON(settingsKey, AppSettings.encode(s)); },

  /** { levelID: CompletionRecord } as a null-prototype object; {} when missing or any record is invalid. */
  loadProgress() {
    const out = Object.create(null);
    const o = readJSON(progressKey);
    if (!isObject(o)) return out;
    for (const k of Object.keys(o)) {
      const r = CompletionRecord.decode(o[k]);
      if (!r) return Object.create(null);
      out[k] = r;
    }
    return out;
  },

  saveProgress(p) {
    const out = {};
    for (const k of Object.keys(p)) out[k] = CompletionRecord.encode(p[k]);
    writeJSON(progressKey, out);
  },

  loadHighScores() {
    const o = readJSON(highScoreKey);
    return (o !== undefined && HighScoreTable.decode(o)) || new HighScoreTable();
  },

  saveHighScores(t) { writeJSON(highScoreKey, t); },

  loadGame(id) {
    const o = readJSON(gameKey(id));
    return o === undefined ? null : SaveGame.decode(o);
  },

  saveGame(g) { writeJSON(gameKey(g.levelID), SaveGame.encode(g)); },

  /** Is there a saved game for this mosaic (without decoding it)? */
  hasGame(id) { return getItem(gameKey(id)) !== null; },

  clearGame(id) { removeItem(gameKey(id)); },

  resetEverything(levelIDs) {
    removeItem(settingsKey);
    removeItem(progressKey);
    removeItem(highScoreKey);
    for (const id of levelIDs) SaveStore.clearGame(id);
  },
});

// MARK: - Photo mosaics

/**
 * A photo (or pattern) mosaic saved on the device. new PhotoLevelRecord(level, detail, created)
 * mirrors Swift init(level:detail:created:); `created` is epoch ms (a Date is converted).
 * `record.level` rebuilds the LevelDefinition (isPhoto, no golden values).
 */
export class PhotoLevelRecord {
  #level = null;

  constructor(level, detail, created) {
    this.id = level.id;
    this.title = level.title;
    this.created = dateMs(created);
    this.detail = detail;
    this.art = level.art;
    this.palette = level.palette;
    this.tunnels = level.tunnels;
    this.solution = level.solution;
    this.chambersGentle = level.chambersGentle;
    this.chambersClassic = level.chambersClassic;
    this.chambersExpert = level.chambersExpert;
    this.subtitle = level.subtitle;
  }

  get level() {
    if (!this.#level) {
      this.#level = new LevelDefinition({
        id: this.id, title: this.title, subtitle: this.subtitle, art: this.art,
        palette: LevelPalette.from(this.palette), tunnels: this.tunnels,
        chambersGentle: this.chambersGentle, chambersClassic: this.chambersClassic, chambersExpert: this.chambersExpert,
        solution: this.solution, goldenClaimsPerMove: [], goldenClaimsHash: 0n, goldenFinalStateHash: 0n,
        isPhoto: true,
      });
    }
    return this.#level;
  }

  /** The Codable record (Swift field order). */
  toJSON() {
    return {
      id: this.id, title: this.title, created: this.created, detail: this.detail, art: this.art,
      palette: { names: this.palette.names, tones: this.palette.tones },
      tunnels: this.tunnels.map(q => q.map(t => ({ family: t.family, quota: t.quota }))),
      solution: this.solution, chambersGentle: this.chambersGentle, chambersClassic: this.chambersClassic,
      chambersExpert: this.chambersExpert, subtitle: this.subtitle,
    };
  }

  /** Strict decoding; null when invalid. */
  static decode(o) {
    try {
      if (!isObject(o)) return null;
      const pal = required(o, 'palette', v => isObject(v) && isArrayOf(v.names, isString)
        && isArrayOf(v.tones, row => isArrayOf(row, isUInt32)));
      const tunnels = required(o, 'tunnels', v => isArrayOf(v, q => isArrayOf(q, t => isObject(t) && isInt(t.family) && isInt(t.quota))));
      let created = required(o, 'created', v => isDouble(v) || isString(v));
      created = dateMs(created);
      if (!isDouble(created)) return null;
      return new PhotoLevelRecord({
        id: required(o, 'id', isString),
        title: required(o, 'title', isString),
        subtitle: required(o, 'subtitle', isString),
        art: required(o, 'art', v => isArrayOf(v, isString)),
        palette: new LevelPalette(pal.names.slice(), pal.tones.map(r => r.slice())),
        tunnels: tunnels.map(q => q.map(t => TeamSpec(t.family, t.quota))),
        solution: required(o, 'solution', v => isArrayOf(v, isInt)),
        chambersGentle: required(o, 'chambersGentle', isInt),
        chambersClassic: required(o, 'chambersClassic', isInt),
        chambersExpert: required(o, 'chambersExpert', isInt),
      }, required(o, 'detail', v => PHOTO_DETAIL_VALUES.includes(v)), created);
    } catch (e) {
      if (e instanceof DecodeError) return null;
      throw e;
    }
  }
}

function photoIndex() {
  const ids = readJSON(photoIndexKey);
  return isArrayOf(ids, isString) ? ids : [];
}

/** Saved photo and pattern mosaics (Swift PhotoLibrary: loadAll / save / delete). Image decoding is the integrator's. */
export const PhotoLibrary = Object.freeze({
  /** Every saved record, newest first. */
  loadAll() {
    const out = [];
    for (const id of photoIndex()) {
      const r = PhotoLevelRecord.decode(readJSON(photoKey(id)));
      if (r) out.push(r);
    }
    return out.sort((a, b) => b.created - a.created);
  },

  save(r) {
    if (!writeJSON(photoKey(r.id), r)) return;
    const ids = photoIndex();
    if (!ids.includes(r.id)) {
      ids.push(r.id);
      writeJSON(photoIndexKey, ids);
    }
  },

  delete(id) {
    removeItem(photoKey(id));
    const ids = photoIndex();
    const i = ids.indexOf(id);
    if (i >= 0) {
      ids.splice(i, 1);
      writeJSON(photoIndexKey, ids);
    }
  },
});
