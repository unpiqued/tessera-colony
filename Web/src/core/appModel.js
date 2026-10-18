// Port of the non-UI part of AppModel.swift (RootView and the SwiftUI plumbing stay with the
// integrator), with Collection.swift's `extension AppModel` mixed in from collection.js.
//
// @Published properties are plain properties plus a change notification: subscribe(fn) returns an
// unsubscribe function; listeners are called with the model once per batch of mutations (queued
// with queueMicrotask).
//
// `settings` behaves like Swift's `@Published var settings { didSet { save; applySound } }`: it is a
// live view of the stored settings, and ANY write into it — app.settings.antSpeed = 2,
// app.settings.coachSeen.push('scout'), app.settings.versusRules.layout = 'shared', or
// app.settings = AppSettings() — saves the settings, re-applies the sound settings and notifies.
// Assigned objects are copied in (Swift value semantics); take a detached copy out with
// AppSettings.copy(app.settings) (structuredClone cannot copy the live view).
// progress, highScores, photoLevels, measuredStats, current, versus, photoBusy and crashReport are
// read-only getters (Swift private(set)); photoMessage is read-write.
//
// Things the core cannot do itself are injected through `hooks` (constructor argument, or assign
// app.hooks.x later); every hook is optional and may return a value or a Promise where noted:
//   makeGameController(level, difficulty, modifiers: Set, app, resume: SaveGame|null) → controller
//       (needs .save()); without it `current` is a plain { level, difficulty, modifiers, resume }.
//   makeVersusController(level, rules, app) → controller; without it `versus` is { level, rules }.
//   soundBoard: { configure(on, volume, tileClicks, actions, goals, ignoreSilentMode) }
//   flightRecorder: { launchCheck(), pendingReport, dismissReport(), end() }
//   thumbnail(level) → image (cached per level id; null results are not cached)
//   measureDifficulty(level) → DifficultyStats | Promise   (DifficultyProbe.measure)
//   buildPatternLevel(seed: BigInt, number) → LevelDefinition | null | Promise
//   photoPixels(data) → PixelImage | null | Promise          (PhotoLibrary.pixels(from:))
//   buildPhotoLevel(image, detail, seed: BigInt, id, title) →
//       { kind: 'success', level } | { kind: 'failure', error: { message } } | Promise of either

import { Game } from './engine.js';
import { LevelCatalog } from './level.js';
import { ChallengeModifier, HighScoreTable, HighScoreNames, HighScoreEntry, RatingFilter } from './scoring.js';
import { SaveStore, AppSettings, CompletionRecord, CompletionNews, PhotoLibrary, PhotoLevelRecord } from './saveStore.js';
import { AppModelCollection } from './collection.js';

const UNREADABLE_PHOTO = "That image couldn't be read. Try another photo.";
const PATTERN_FAILED = "The colony couldn't plan that pattern. Please tap New pattern again.";
const PHOTO_FAILED = "The colony couldn't plan a solvable puzzle for this photo. Try a different detail level.";

function plainCopy(v) {
  if (v === null || typeof v !== 'object') return v;
  if (Array.isArray(v)) return v.map(plainCopy);
  if (v instanceof Set) return new Set(v);
  const o = {};
  for (const k of Object.keys(v)) o[k] = plainCopy(v[k]);
  return o;
}

/** A live, deep view of `root`: every write goes to root (copied in) and calls onChange(). */
function liveView(root, onChange) {
  const proxies = new WeakMap();
  const handler = {
    get(t, k) {
      const v = Reflect.get(t, k);
      return v !== null && typeof v === 'object' ? wrap(v) : v;
    },
    set(t, k, v) {
      t[k] = plainCopy(v);
      onChange();
      return true;
    },
    deleteProperty(t, k) {
      delete t[k];
      onChange();
      return true;
    },
  };
  function wrap(obj) {
    let p = proxies.get(obj);
    if (!p) {
      p = new Proxy(obj, handler);
      proxies.set(obj, p);
    }
    return p;
  }
  return wrap(root);
}

function sameList(a, b) {
  if (a.length !== b.length) return false;
  for (let i = 0; i < a.length; i++) if (a[i] !== b[i]) return false;
  return true;
}

export class AppModel {
  constructor(hooks = {}) {
    this.hooks = { ...hooks };
    this._listeners = new Set();
    this._notifyQueued = false;
    this.hooks.flightRecorder?.launchCheck?.();
    this._settings = SaveStore.loadSettings();
    this._settingsView = null;
    this._progress = SaveStore.loadProgress();
    this._current = null;
    /** A two-player match in progress. */
    this._versus = null;
    this._photoLevels = PhotoLibrary.loadAll();
    this._photoBusy = false;
    this._photoMessage = null;
    /** Difficulty measured on the device for pattern and photo levels (built-ins ship theirs). */
    this._measuredStats = Object.create(null);
    /** Top scores per mosaic (solo and two-player winners). */
    this._highScores = SaveStore.loadHighScores();
    /** Report left by a game that didn't close normally last time (see FlightRecorder). */
    this._crashReport = this.hooks.flightRecorder?.pendingReport ?? null;
    this._measuring = new Set();
    this._thumbnailCache = new Map();
    this._applySound();
  }

  // MARK: - Change notification

  /** Calls fn(app) after mutations (batched per microtask). Returns the unsubscribe function. */
  subscribe(fn) {
    this._listeners.add(fn);
    return () => { this._listeners.delete(fn); };
  }

  _changed() {
    if (this._notifyQueued) return;
    this._notifyQueued = true;
    queueMicrotask(() => {
      this._notifyQueued = false;
      for (const fn of Array.from(this._listeners)) {
        try {
          fn(this);
        } catch (e) {
          queueMicrotask(() => { throw e; });
        }
      }
    });
  }

  // MARK: - Published state

  get settings() {
    if (!this._settingsView) this._settingsView = liveView(this._settings, () => this._settingsDidSet());
    return this._settingsView;
  }

  set settings(s) {
    this._settings = AppSettings.copy(plainCopy(s));
    this._settingsView = null;
    this._settingsDidSet();
  }

  _settingsDidSet() {
    SaveStore.saveSettings(this._settings);
    this._applySound();
    this._changed();
  }

  /** { levelID: CompletionRecord } (null-prototype object). */
  get progress() { return this._progress; }
  /** The game in progress (a GameController from hooks.makeGameController), or null. */
  get current() { return this._current; }
  /** A two-player match in progress, or null. */
  get versus() { return this._versus; }
  /** [PhotoLevelRecord], newest first. */
  get photoLevels() { return this._photoLevels; }
  get photoBusy() { return this._photoBusy; }
  get photoMessage() { return this._photoMessage; }
  set photoMessage(m) { this._photoMessage = m; this._changed(); }
  /** { levelID: DifficultyStats } measured on the device for pattern and photo levels. */
  get measuredStats() { return this._measuredStats; }
  get highScores() { return this._highScores; }
  get crashReport() { return this._crashReport; }

  dismissCrashReport() {
    this.hooks.flightRecorder?.dismissReport?.();
    this._crashReport = null;
    this._changed();
  }

  _applySound() {
    const s = this._settings;
    this.hooks.soundBoard?.configure?.(s.soundOn, s.soundVolume, s.tileClicks, s.actionSounds, s.goalSounds,
      s.soundInSilentMode);
  }

  get allLevels() { return LevelCatalog.builtIn.concat(this._photoLevels.map(r => r.level)); }

  // MARK: - Playing

  /**
   * Opens a mosaic. `fresh` starts over with `difficulty` and `modifiers` (defaults: the last
   * choice); otherwise the saved game resumes on its own difficulty and harder options.
   * Swift play(_:fresh:difficulty:modifiers:) — modifiers is a Set (or array) of ChallengeModifier.
   */
  play(level, fresh, difficulty = null, modifiers = null) {
    let save = null;
    const settings = this.settings;
    if (difficulty !== null && difficulty !== undefined && difficulty !== settings.difficulty) settings.difficulty = difficulty;
    if (modifiers !== null && modifiers !== undefined) {
      const list = ChallengeModifier.sorted(modifiers);
      if (!sameList(list, this._settings.lastModifiers)) settings.lastModifiers = list;
    }
    let d = difficulty ?? this._settings.difficulty;
    let mods = modifiers !== null && modifiers !== undefined ? new Set(modifiers) : new Set(this._settings.lastModifiers);
    if (fresh) {
      SaveStore.clearGame(level.id);
    } else {
      const s = SaveStore.loadGame(level.id);
      if (s) {
        save = s;
        d = s.difficulty;
        mods = new Set(s.modifiers ?? []);
      }
    }
    const make = this.hooks.makeGameController;
    this._current = make ? make(level, d, mods, this, save) : { level, difficulty: d, modifiers: mods, resume: save };
    settings.hasLaunchedBefore = true;
    this._changed();
  }

  /** Swift startVersus(level:rules:) */
  startVersus(level, rules) {
    this._current?.save?.();
    this._current = null;
    this.hooks.flightRecorder?.end?.();
    const make = this.hooks.makeVersusController;
    this._versus = make ? make(level, rules, this) : { level, rules };
    this._changed();
  }

  endVersus() {
    this._versus = null;
    this._changed();
  }

  goHome() {
    this._current?.save?.();
    this._current = null;
    this.hooks.flightRecorder?.end?.();
    this._changed();
  }

  /** `step` is a CoachStep raw value (e.g. 'tapTeam'). */
  markCoachSeen(step) {
    if (!this._settings.coachSeen.includes(step)) this.settings.coachSeen.push(step);
  }

  /**
   * Records a finish. Swift recordCompletion(levelID:seconds:undos:difficulty:modifiers:) —
   * `modifiers` is the number of harder options used. Returns CompletionNews.
   */
  recordCompletion(levelID, seconds, undos, difficulty, modifiers = 0) {
    const closedBefore = new Set(this.allLevels.filter(l => !this.isPlayable(l)).map(l => l.id));
    const starsBefore = this.stars(levelID);
    const masteredBefore = this.isMastered(levelID);
    const old = this._progress[levelID];
    const rec = old ? CompletionRecord.copy(old)
      : CompletionRecord({ bestSeconds: seconds, fewestUndos: undos, difficulty, completions: 0 });
    const prevBest = old && old.bestByDifficulty ? old.bestByDifficulty[difficulty] ?? null : null;
    const byDifficulty = rec.bestByDifficulty ? { ...rec.bestByDifficulty } : {};
    byDifficulty[difficulty] = Math.min(prevBest ?? seconds, seconds);
    rec.bestByDifficulty = byDifficulty;
    rec.bestSeconds = Math.min(rec.bestSeconds, seconds);
    rec.fewestUndos = Math.min(rec.fewestUndos, undos);
    rec.completions += 1;
    if (difficulty === 'expert' || (difficulty === 'classic' && rec.difficulty === 'gentle')) rec.difficulty = difficulty;
    if (difficulty === 'expert') rec.expertModifiers = Math.max(rec.expertModifiers ?? 0, modifiers);
    this._progress[levelID] = rec;
    SaveStore.saveProgress(this._progress);
    const opened = this.allLevels.filter(l => closedBefore.has(l.id) && this.isPlayable(l)).map(l => l.title);
    const beat = prevBest !== null ? seconds < prevBest - 0.5 : false;
    const starsNow = this.stars(levelID);
    this._changed();
    return CompletionNews({
      newBest: beat, firstClear: old === undefined, unlocked: opened,
      stars: starsNow, newStar: starsNow > starsBefore,
      mastered: !masteredBefore && this.isMastered(levelID),
    });
  }

  resetEverything() {
    SaveStore.resetEverything(this.allLevels.map(l => l.id));
    this.settings = AppSettings();
    this._progress = Object.create(null);
    this._highScores = new HighScoreTable();
    this._changed();
  }

  // MARK: - High scores

  /** Swift topScores(_:levelID:) */
  topScores(kind, levelID) {
    return this._highScores.list(kind, levelID);
  }

  /** The place a score would take on a mosaic's table (null = doesn't make the top 5). */
  highScoreRank(kind, levelID, score, seconds) {
    return this._highScores.rank(kind, levelID, score, seconds);
  }

  /** Saves a score under a name; returns its place on the table. Swift saveHighScore(_:levelID:entry:). */
  saveHighScore(kind, levelID, entry) {
    const e = HighScoreEntry.copy(entry);
    e.name = HighScoreNames.clean(e.name);
    const place = this._highScores.insert(kind, levelID, e);
    SaveStore.saveHighScores(this._highScores);
    if (this._settings.playerName !== e.name) this.settings.playerName = e.name;
    this._changed();
    return place;
  }

  clearHighScores() {
    this._highScores = new HighScoreTable();
    SaveStore.saveHighScores(this._highScores);
    this._changed();
  }

  // MARK: - Home filter

  /** Does a mosaic pass Home's filters (status, then its rating on the chosen difficulty)? */
  passesFilter(level) {
    if (!this.passesStatus(level)) return false;
    const f = this._settings.ratingFilter;
    if (f === 'all') return true;
    const st = this.difficultyStats(level);
    if (!st) return false;
    return RatingFilter.levels(f).contains(st.rating(this._settings.difficulty).level);
  }

  /** The level's miniature from hooks.thumbnail (MosaicRaster.miniature), cached per id. */
  thumbnail(level) {
    const t = this._thumbnailCache.get(level.id);
    if (t !== undefined) return t;
    const img = this.hooks.thumbnail ? this.hooks.thumbnail(level) : null;
    if (img !== null && img !== undefined) this._thumbnailCache.set(level.id, img);
    return img ?? null;
  }

  // MARK: - Unlocking

  isUnlocked(level) {
    if (this._settings.unlockAll || level.isPhoto) return true;
    const rule = LevelCatalog.unlockRule(level.id);
    if (!rule) return true;
    return rule.anyOf.some(id => this._progress[id] !== undefined);
  }

  /** What must be finished first, e.g. "First Dig" or "any Challenge mosaic" (null when open). */
  unlockRequirement(level) {
    if (this.isUnlocked(level)) return null;
    const rule = LevelCatalog.unlockRule(level.id);
    return rule ? rule.label : null;
  }

  /**
   * The first found mosaic you haven't finished yet, going through the packs in Home's order —
   * the "Next up" banner (null when there is none).
   */
  get nextUp() {
    for (const pack of LevelCatalog.packs) {
      const l = pack.levels.find(x => this.isPlayable(x) && this._progress[x.id] === undefined);
      if (l) return l;
    }
    return null;
  }

  /** What "Next mosaic" on the win card opens (the next unfinished one in the same pack first). Swift nextLevel(after:). */
  nextLevel(id) {
    const list = LevelCatalog.packList(id);
    const i = list.findIndex(l => l.id === id);
    if (i >= 0 && i + 1 < list.length) {
      const fresh = list.slice(i + 1).find(l => this.isPlayable(l) && this._progress[l.id] === undefined);
      if (fresh) return fresh;
    }
    return this.nextUp;
  }

  /** The in-progress game for a level, if any (its difficulty and moves). Swift savedGame(for:). */
  savedGame(level) { return SaveStore.loadGame(level.id); }

  /** Measured difficulty: shipped with built-in levels, measured on the device for the others. */
  difficultyStats(level) {
    return level.shippedStats ?? this._measuredStats[level.id] ?? null;
  }

  /** Starts measuring a pattern or photo level's difficulty (hooks.measureDifficulty) if needed. */
  measureIfNeeded(level) {
    if (this.difficultyStats(level) !== null || this._measuring.has(level.id)) return;
    const measure = this.hooks.measureDifficulty;
    if (!measure) return;
    this._measuring.add(level.id);
    Promise.resolve()
      .then(() => measure(level))
      .then(stats => {
        if (stats) this._measuredStats[level.id] = stats;
        this._measuring.delete(level.id);
        this._changed();
      }, () => {
        this._measuring.delete(level.id);
      });
  }

  /** Number of tunnel sends in the saved game (assists not counted), or null. Swift savedMoves(for:). */
  savedMoves(level) {
    const s = SaveStore.loadGame(level.id);
    if (!s) return null;
    return s.moves.filter(m => m < Game.addChamberMove).length;
  }

  // MARK: - Pattern mosaics (a new, verified level on demand)

  /** Builds a pattern mosaic through hooks.buildPatternLevel, saves it and opens it. Returns a Promise of the level (or null). */
  createPatternLevel() {
    if (this._photoBusy) return Promise.resolve(null);
    this._photoBusy = true;
    this._photoMessage = null;
    this._changed();
    const number = this._photoLevels.filter(r => r.id.startsWith('pattern-')).length + 1;
    const seed = BigInt.asUintN(64, BigInt(Date.now())) & 0xFFFFFFFFn;
    const build = this.hooks.buildPatternLevel;
    return Promise.resolve()
      .then(() => (build ? build(seed, number) : null))
      .catch(() => null)
      .then(level => {
        this._photoBusy = false;
        if (!level) {
          this._photoMessage = PATTERN_FAILED;
          this._changed();
          return null;
        }
        const rec = new PhotoLevelRecord(level, 'fine', Date.now());
        PhotoLibrary.save(rec);
        this._photoLevels = [rec].concat(this._photoLevels);
        this.play(level, true);
        this._changed();
        return level;
      });
  }

  // MARK: - Photo mosaics

  /**
   * Converts picked photo data (ArrayBuffer, typed array or Blob) into a playable mosaic through
   * hooks.photoPixels and hooks.buildPhotoLevel, then opens it. Returns a Promise of the result.
   */
  importPhoto(data) {
    if (this._photoBusy) return Promise.resolve(null);
    this._photoBusy = true;
    this._photoMessage = null;
    this._changed();
    const detail = this._settings.photoDetail;
    const number = this._photoLevels.length + 1;
    const now = Date.now();
    const id = 'photo-' + now.toString(36);
    const count = data?.byteLength ?? data?.size ?? data?.length ?? 0;
    const seed = BigInt.asUintN(64, BigInt(count) * 2654435761n) ^ BigInt(Math.floor(now / 1000));
    const hooks = this.hooks;
    const run = async () => {
      const px = hooks.photoPixels ? await hooks.photoPixels(data) : null;
      if (!px) return { kind: 'failure', error: { kind: 'unreadable', message: UNREADABLE_PHOTO } };
      if (!hooks.buildPhotoLevel) return { kind: 'failure', error: { kind: 'generationFailed', message: PHOTO_FAILED } };
      return await hooks.buildPhotoLevel(px, detail, seed, id, `Photo mosaic ${number}`);
    };
    return run()
      .catch(() => ({ kind: 'failure', error: { kind: 'generationFailed', message: PHOTO_FAILED } }))
      .then(result => {
        this._finishImport(result, detail);
        return result;
      });
  }

  _finishImport(result, detail) {
    this._photoBusy = false;
    if (!result || result.kind !== 'success') {
      this._photoMessage = result?.error?.message ?? PHOTO_FAILED;
    } else {
      const rec = new PhotoLevelRecord(result.level, detail, Date.now());
      PhotoLibrary.save(rec);
      this._photoLevels = [rec].concat(this._photoLevels);
      this.play(result.level, true);
    }
    this._changed();
  }

  /** Swift deletePhotoLevel(id:) */
  deletePhotoLevel(id) {
    PhotoLibrary.delete(id);
    SaveStore.clearGame(id);
    this._photoLevels = this._photoLevels.filter(r => r.id !== id);
    this._thumbnailCache.delete(id);
    delete this._progress[id];
    SaveStore.saveProgress(this._progress);
    this._changed();
  }
}

for (const k of Object.keys(AppModelCollection)) {
  Object.defineProperty(AppModel.prototype, k, { value: AppModelCollection[k], writable: true, configurable: true });
}
