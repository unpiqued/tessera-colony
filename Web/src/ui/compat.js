// Adapter between the screens (src/ui) and the ported modules: one place that maps the names the
// views use onto core/, render/, sound/ and builders/, and boots the AppModel with its hooks.
import { Game } from '../core/engine.js';
import { Board } from '../core/board.js';
import { setLevelData } from '../core/levelData.js';
import { LevelCatalog, Difficulty, GeneratedPalette, LevelPalette, LevelDefinition, DifficultyStats } from '../core/level.js';
import { ChallengeModifier, ScoreRules, ColourRule, HighScoreEntry, HighScoreKind, RatingFilter, TimeText } from '../core/scoring.js';
import { StatusFilter } from '../core/collection.js';
import { SaveStore, SaveGame } from '../core/saveStore.js';
import { VersusMatch, VersusRules, VersusLayout, VersusPicking, VersusColourRule, VersusSlotScoring } from '../core/versus.js';
import { AppModel } from '../core/appModel.js';
import { AntScheduler } from '../render/antScheduler.js';
import { MosaicRaster } from '../render/mosaicRaster.js';
import { BoardCanvas, VersusBoardCanvas } from '../render/boardCanvas.js';
import { BoardPainter } from '../render/boardPainter.js';
import { GroundPresets } from '../render/theme.js';
import { PATH_STYLE_INFO, PathStyle } from '../render/pathPlanner.js';
import { SoundBoard, SoundCue } from '../sound/soundBoard.js';
import { PhotoDetail } from '../builders/photoLevelBuilder.js';
import { PACK_BLURBS } from './text.js';

export {
  Game, DifficultyStats, LevelDefinition, LevelPalette, LevelCatalog, ChallengeModifier, ScoreRules, ColourRule, TimeText, SaveStore, VersusMatch, VersusRules,
  AntScheduler, MosaicRaster, BoardCanvas, VersusBoardCanvas, GroundPresets, SoundBoard,
};

export const Sfx = SoundCue;
export const PathStyleDefault = PathStyle.randomTeam || 'randomTeam';
export const PLAYER_COLORS = BoardPainter.playerColors;

// MARK: - Levels and difficulty

export const DIFFICULTIES = Difficulty.allCases.map(id => ({ id, title: Difficulty.title(id) }));
export function difficultyTitle(d) { return Difficulty.title(d); }
export function difficultyBlurb(d) { return Difficulty.blurb(d); }

export function levelChambers(level, d) {
  if (typeof level.chambers === 'function') return level.chambers(d);
  return d === 'gentle' ? level.chambersGentle : d === 'expert' ? level.chambersExpert : level.chambersClassic;
}
export function levelTileCount(level) {
  if (typeof level.tileCount === 'number') return level.tileCount;
  let n = 0;
  for (const row of level.art) for (const ch of row) { const c = ch.charCodeAt(0); if (c >= 97 && c < 121) n++; }
  return n;
}
export function levelTeamCount(level) {
  if (typeof level.teamCount === 'number') return level.teamCount;
  return level.tunnels.reduce((a, q) => a + q.length, 0);
}
export function ratingFor(stats, d) {
  if (typeof stats.rating === 'function') return stats.rating(d);
  return new DifficultyStats(stats.careless, stats.greedy).rating(d);
}
export function paletteName(p, f) { return LevelPalette.name(p, f); }
export function builtInPalette() { return GeneratedPalette.builtIn; }
export function soilColor() { return GeneratedPalette.soil; }
export function packBlurb(id) { return PACK_BLURBS[id] || PACK_BLURBS.master; }

export const RatingFilters = RatingFilter.allCases.map(id => ({ id, title: RatingFilter.title(id), dotLevel: RatingFilter.dotLevel(id) }));
export const StatusFilters = StatusFilter.allCases.map(id => ({ id, title: StatusFilter.title(id), icon: StatusFilter.icon(id) }));
export const HighScoreKinds = HighScoreKind.allCases.map(id => ({ id, title: HighScoreKind.title(id) }));
export const PhotoDetails = PhotoDetail.allCases.map(id => ({ id, title: PhotoDetail.title(id) }));

export function modifierInfo(m) {
  return { title: ChallengeModifier.title(m), blurb: ChallengeModifier.blurb(m), systemImage: ChallengeModifier.systemImage(m), bonus: ChallengeModifier.bonus(m) };
}

export function pathStyles() {
  return PathStyle.allCases.map(id => Object.assign({ id }, PATH_STYLE_INFO[id]));
}
export function pathStyleInfo(id) { return Object.assign({ id }, PATH_STYLE_INFO[id] || PATH_STYLE_INFO.randomTeam); }

const VERSUS_ENUMS = { layout: VersusLayout, picking: VersusPicking, colour: VersusColourRule, scoring: VersusSlotScoring };
export function versusOptions(key) { const E = VERSUS_ENUMS[key]; return E.allCases.map(id => ({ id, title: E.title(id) })); }
export function versusOptionTitle(key, v) { return VERSUS_ENUMS[key].title(v); }
export function versusOptionBlurb(key, v) { return VERSUS_ENUMS[key].blurb(v); }
export function defaultVersusRules() { return VersusRules(); }

/** Swift `Int.formatted()`: grouping separators in the viewer's locale. */
export function formatNumber(n) {
  try { return Math.round(n).toLocaleString(); } catch (e) { return String(Math.round(n)); }
}

/** scheduler.busyTeams returns a Map (Swift [Int: Int]); accept a plain object too. */
export function busyEntries(b) {
  if (b instanceof Map) return b;
  const m = new Map();
  if (b) for (const k of Object.keys(b)) m.set(Number(k), b[k]);
  return m;
}

export function makeSaveGame(levelID, difficulty, moves, undos, hints, elapsed, modifiers) {
  return SaveGame({ levelID, difficulty, moves, undos, hints, elapsed, modifiers });
}
export function makeHighScoreEntry(name, score, seconds, difficulty, modifiers = [], detail = '') {
  return HighScoreEntry({ name, score, seconds, date: Date.now(), difficulty, modifiers, detail });
}

// MARK: - Thumbnails (Swift app.thumbnail(for:) — cached data URLs of the finished picture)

/** A data URL for any canvas (MosaicRaster may hand back an OffscreenCanvas, which has no toDataURL). */
export function canvasDataURL(c) {
  if (!c) return '';
  if (typeof c.toDataURL === 'function') return c.toDataURL();
  const el = document.createElement('canvas');
  el.width = c.width; el.height = c.height;
  el.getContext('2d').drawImage(c, 0, 0);
  return el.toDataURL();
}

const thumbs = new Map();
export function thumbURL(level) {
  let u = thumbs.get(level.id);
  if (u) return u;
  const canvas = MosaicRaster.miniature(new Board(level.art), level.palette, () => true);
  u = canvasDataURL(canvas);
  thumbs.set(level.id, u);
  return u;
}
export function forgetThumb(id) { thumbs.delete(id); }

