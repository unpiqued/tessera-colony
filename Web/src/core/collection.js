// Port of Collection.swift's logic: how the built-in mosaics are found, explored and made harder.
//
// * Found — a pack opens (after First Dig, or after a mosaic of the pack before it); its first three
//   mosaics are found at once and every mosaic finished in the pack finds one more. The rest show as
//   "?" cards. Settings → Unlock all shows everything.
// * Explored — finished on any difficulty. Stars: one for Gentle, two for Classic, three for Expert
//   (the hardest difficulty you have finished it on).
// * Mastered — finished on Expert with at least one harder option (the flame).
// After a finish, the win card offers the next harder step: Classic, then Expert, then Expert with one
// more harder option.
//
// The SwiftUI views stay with the integrator. What they compute:
// - StarRow(stars, mastered): three stars filled up to `stars`, plus a flame when mastered;
//   accessibility label "Mastered" or "<n> of 3 stars".
// - CollectionCard(level): status = app.status(level); title "Locked" (packLocked) / "Undiscovered"
//   (hidden) / level.title; disabled unless CollectionStatus.isPlayable(status). Picture: lock +
//   "Opens after\n<label>" | "?" + "Finish 1 more\nin this pack" / "Finish <n> more\nin this pack" |
//   thumbnail + badge ("IN PROGRESS" when found with moves > 0, "NEW" when found with 0 moves, a flame
//   when mastered). Footer: rating dots of app.difficultyStats(level).rating(settings.difficulty).level
//   when playable; StarRow for explored(stars) / mastered (3 stars + flame). Border: brass (found),
//   danger (mastered), panel edge (explored), dimmed edge otherwise. Accessibility text per status:
//   "Locked mosaic. Opens after <label>." / "Undiscovered mosaic. Finish <n> more in this pack to find
//   it." / "<title>, in progress" | "<title>, new" / "<title>, explored, <s> of 3 stars" / "<title>, mastered".
// - CollectionSummary(progress: PackProgress): "<found> of <total> found", "<explored> explored",
//   "<stars> of <total*3> stars", "<mastered> mastered", and a bar stars / max(1, total * 3).

import { Difficulty, LevelCatalog } from './level.js';
import { ChallengeModifier } from './scoring.js';
import { SaveStore, STATUS_FILTER_VALUES } from './saveStore.js';

const STATUS_FILTER_INFO = {
  all: { title: 'All', icon: 'square.grid.2x2' },
  toExplore: { title: 'To explore', icon: 'magnifyingglass' },
  explored: { title: 'Explored', icon: 'star.fill' },
  goHarder: { title: 'Go harder', icon: 'arrow.up.circle' },
  mastered: { title: 'Mastered', icon: 'flame.fill' },
};

/** Home's status filter: where a mosaic stands in your collection. StatusFilter.title(f), .icon(f) (SF Symbol name). */
export const StatusFilter = Object.freeze({
  all: 'all',
  toExplore: 'toExplore',
  explored: 'explored',
  goHarder: 'goHarder',
  mastered: 'mastered',
  allCases: STATUS_FILTER_VALUES,
  isValid(f) { return typeof f === 'string' && STATUS_FILTER_VALUES.includes(f); },
  id(f) { return f; },
  title(f) { return STATUS_FILTER_INFO[f].title; },
  icon(f) { return STATUS_FILTER_INFO[f].icon; },
});

/**
 * Where one mosaic stands in the collection (tagged objects):
 *   { kind: 'packLocked', label }  its pack (or the mosaic before it) hasn't opened yet; label says what opens it
 *   { kind: 'hidden', more }       the pack is open but this mosaic isn't found yet: finish `more` more in the pack
 *   { kind: 'found', moves }       found and not finished yet; moves > 0 while a game is in progress
 *   { kind: 'explored', stars }    finished: stars = hardest difficulty finished (1 Gentle, 2 Classic, 3 Expert)
 *   { kind: 'mastered' }           finished on Expert with at least one harder option
 */
export const CollectionStatus = Object.freeze({
  packLocked: label => ({ kind: 'packLocked', label }),
  hidden: more => ({ kind: 'hidden', more }),
  found: moves => ({ kind: 'found', moves }),
  explored: stars => ({ kind: 'explored', stars }),
  mastered: () => ({ kind: 'mastered' }),
  isPlayable(s) { return s.kind !== 'packLocked' && s.kind !== 'hidden'; },
  equals(a, b) {
    if (a.kind !== b.kind) return false;
    switch (a.kind) {
      case 'packLocked': return a.label === b.label;
      case 'hidden': return a.more === b.more;
      case 'found': return a.moves === b.moves;
      case 'explored': return a.stars === b.stars;
      default: return true;
    }
  },
});

/** Counts for a pack, a theme or the whole collection. `open`: at least one of its mosaics is unlocked. */
export function PackProgress() {
  return { total: 0, found: 0, explored: 0, stars: 0, mastered: 0, open: false };
}

/**
 * The next way to make a finished mosaic harder: the next difficulty up, then (on Expert) one more
 * harder option. { difficulty, modifiers: Set<ChallengeModifier>, label }.
 */
export const HarderStep = Object.freeze({
  /** Swift after(_:modifiers:) — `modifiers` is a Set or an array; null when nothing harder is left. */
  after(d, modifiers) {
    const mods = new Set(modifiers ?? []);
    switch (d) {
      case 'gentle':
        return { difficulty: 'classic', modifiers: mods, label: 'Try it on Classic' };
      case 'classic':
        return { difficulty: 'expert', modifiers: mods, label: 'Try it on Expert' };
      case 'expert': {
        const extra = ChallengeModifier.allCases.find(m => !mods.has(m));
        if (extra === undefined) return null;
        const more = new Set(mods);
        more.add(extra);
        return { difficulty: 'expert', modifiers: more, label: `Expert + ${ChallengeModifier.title(extra)}` };
      }
      default:
        return null;
    }
  },
});

/**
 * The `extension AppModel` methods of Collection.swift; appModel.js mixes them into
 * AppModel.prototype. They use this.progress, this.settings, this.isUnlocked(level),
 * this.unlockRequirement(level) and this.savedMoves(level).
 */
export const AppModelCollection = {
  /** Hardest difficulty finished: 0 none, 1 Gentle, 2 Classic, 3 Expert. */
  stars(id) {
    const rec = this.progress[id];
    if (!rec) return 0;
    let best = Difficulty.index(rec.difficulty) + 1;
    const by = rec.bestByDifficulty;
    if (by) {
      for (const d of Difficulty.allCases) {
        if (by[d] !== undefined && by[d] !== null) best = Math.max(best, Difficulty.index(d) + 1);
      }
    }
    return best;
  },

  /** Finished on Expert with at least one harder option. */
  isMastered(id) {
    const rec = this.progress[id];
    return ((rec && rec.expertModifiers) ?? 0) > 0;
  },

  /** How many mosaics of a pack are found right now. Swift foundLimit(packID:). */
  foundLimit(packID) {
    const list = LevelCatalog.pack(packID);
    const finished = list.filter(l => this.progress[l.id] !== undefined).length;
    return LevelCatalog.foundWhenPackOpens + finished;
  },

  /**
   * Found: the first three of its pack, one more per mosaic finished in the pack; anything
   * finished or in progress stays found.
   */
  isFound(level) {
    if (this.settings.unlockAll || level.isPhoto) return true;
    const packID = LevelCatalog.packOfLevel[level.id];
    if (packID === undefined || packID === 'main') return true;
    if (this.progress[level.id] !== undefined || SaveStore.hasGame(level.id)) return true;
    const list = LevelCatalog.pack(packID);
    const i = list.findIndex(l => l.id === level.id);
    if (i < 0) return true;
    return i < this.foundLimit(packID);
  },

  /** Unlocked and found: it can be played. */
  isPlayable(level) {
    return this.isUnlocked(level) && this.isFound(level);
  },

  /** Swift status(of:) → a CollectionStatus tagged object. */
  status(level) {
    if (!this.isUnlocked(level)) {
      return CollectionStatus.packLocked(this.unlockRequirement(level) ?? '');
    }
    if (!this.isFound(level)) {
      let more = 1;
      const packID = LevelCatalog.packOfLevel[level.id];
      if (packID !== undefined) {
        const i = LevelCatalog.pack(packID).findIndex(l => l.id === level.id);
        if (i >= 0) more = Math.max(1, i - this.foundLimit(packID) + 1);
      }
      return CollectionStatus.hidden(more);
    }
    if (this.progress[level.id] !== undefined) {
      return this.isMastered(level.id) ? CollectionStatus.mastered() : CollectionStatus.explored(this.stars(level.id));
    }
    return CollectionStatus.found(this.savedMoves(level) ?? 0);
  },

  packProgress(levels) {
    const p = PackProgress();
    p.total = levels.length;
    for (const l of levels) {
      if (this.isUnlocked(l)) p.open = true;
      if (this.isPlayable(l)) p.found += 1;
      if (this.progress[l.id] !== undefined) {
        p.explored += 1;
        p.stars += this.stars(l.id);
      }
      if (this.isMastered(l.id)) p.mastered += 1;
    }
    return p;
  },

  /** Home's status filter. */
  passesStatus(level) {
    switch (this.settings.statusFilter) {
      case 'toExplore': return this.isPlayable(level) && this.progress[level.id] === undefined;
      case 'explored': return this.progress[level.id] !== undefined;
      case 'goHarder': return this.progress[level.id] !== undefined && !this.isMastered(level.id);
      case 'mastered': return this.isMastered(level.id);
      default: return true;
    }
  },

  /** The harder step to offer for a mosaic finished on `difficulty` with `modifiers`. Swift harderStep(after:modifiers:). */
  harderStep(difficulty, modifiers) {
    return HarderStep.after(difficulty, modifiers);
  },
};
