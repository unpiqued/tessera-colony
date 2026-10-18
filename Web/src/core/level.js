// Port of Level.swift (everything except DifficultyProbe, which lives with the builders), plus
// GeneratedPalette / GeneratedLevels from LevelData*.swift, built lazily from levelData.js.
//
// Conventions used here (see PORTING.md):
// - Simple enums are frozen objects of string constants with lookup helpers taking the value:
//   Difficulty.title(d), Difficulty.index(d), … and Difficulty.allCases.
// - LevelPalette keeps the fixed shape { names, tones } (a class instance, so palette.tone(f, t)
//   works; LevelPalette.tone(p, f, t) works on any plain { names, tones } object too).
// - LevelDefinition is a class built from one object of fields (the Swift memberwise init's
//   labels); golden hashes are BigInt.
// - LevelCatalog's static lists are getters, computed on first use after setLevelData().

import { TeamSpec } from './engine.js';
import { onLevelData, requireLevelData, rawLevel, levelVariableNames } from './levelData.js';

export { TeamSpec };

/** Swift's Double.rounded(): half away from zero (Math.round rounds -2.5 to -2). */
export function swiftRounded(x) {
  return x < 0 ? -Math.round(-x) : Math.round(x);
}

// MARK: - LevelPalette

/**
 * Colour families of a level: each family has four glaze tones (light -> deep), 0xRRGGBB numbers.
 * Built-in mosaics share GeneratedPalette.builtIn; photo mosaics derive theirs from the photo.
 */
export class LevelPalette {
  constructor(names, tones) {
    this.names = names;
    this.tones = tones;
  }

  /** Wraps any { names, tones } object (returns it unchanged if it already is a LevelPalette). */
  static from(p) {
    if (p instanceof LevelPalette) return p;
    return new LevelPalette(p.names.slice(), p.tones.map(t => t.map(c => c >>> 0)));
  }

  static familyCount(p) { return p.tones.length; }

  static tone(p, family, tone) {
    if (!(family >= 0 && family < p.tones.length)) return 0x888888;
    const t = p.tones[family];
    return t[Math.max(0, Math.min(t.length - 1, tone))];
  }

  static name(p, family) {
    return family >= 0 && family < p.names.length ? p.names[family] : `Colour ${family + 1}`;
  }

  /** Relative luminance (0...1) of a family's main swatch, used to pick legible number ink. */
  static luminance(p, family) {
    const c = LevelPalette.tone(p, family, 1);
    const lin = v => {
      const s = v / 255;
      return s <= 0.04045 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
    };
    return 0.2126 * lin((c >>> 16) & 0xFF) + 0.7152 * lin((c >>> 8) & 0xFF) + 0.0722 * lin(c & 0xFF);
  }

  static equals(a, b) {
    if (a === b) return true;
    if (!a || !b || a.names.length !== b.names.length || a.tones.length !== b.tones.length) return false;
    for (let i = 0; i < a.names.length; i++) if (a.names[i] !== b.names[i]) return false;
    for (let i = 0; i < a.tones.length; i++) {
      if (a.tones[i].length !== b.tones[i].length) return false;
      for (let k = 0; k < a.tones[i].length; k++) if (a.tones[i][k] !== b.tones[i][k]) return false;
    }
    return true;
  }

  get familyCount() { return LevelPalette.familyCount(this); }
  tone(family, tone) { return LevelPalette.tone(this, family, tone); }
  name(family) { return LevelPalette.name(this, family); }
  luminance(family) { return LevelPalette.luminance(this, family); }
  /** JSON shape matches the Swift Codable record: { names, tones }. */
  toJSON() { return { names: this.names, tones: this.tones }; }
}

// MARK: - Difficulty

const DIFFICULTY_INFO = {
  gentle: {
    title: 'Gentle', index: 0,
    blurb: 'Extra slots, and each tunnel tells you whether its team can finish now.',
  },
  classic: {
    title: 'Classic', index: 1,
    blurb: 'The intended challenge. Scout, plan, undo freely.',
  },
  expert: {
    title: 'Expert', index: 2,
    blurb: 'Only the slots the designed solution needs — little room to wait.',
  },
};

/** enum Difficulty: 'gentle' | 'classic' | 'expert'. Helpers take the value: Difficulty.title(d). */
export const Difficulty = Object.freeze({
  gentle: 'gentle',
  classic: 'classic',
  expert: 'expert',
  allCases: Object.freeze(['gentle', 'classic', 'expert']),
  isValid(d) { return typeof d === 'string' && Object.prototype.hasOwnProperty.call(DIFFICULTY_INFO, d); },
  id(d) { return d; },
  title(d) { return DIFFICULTY_INFO[d].title; },
  blurb(d) { return DIFFICULTY_INFO[d].blurb; },
  showsFitBadges(d) { return d === 'gentle'; },
  /** Position in (gentle, classic, expert) arrays. */
  index(d) { return DIFFICULTY_INFO[d].index; },
});

// MARK: - Ratings

const RATING_WORDS = ['Relaxed', 'Steady', 'Tricky', 'Hard', 'Fiendish'];
const RATING_EXPLANATIONS = [
  'Almost any order works.',
  'A little care goes a long way.',
  "Send teams that can finish now and you'll get there.",
  "Sending whatever can finish now isn't enough — think a few moves ahead.",
  'Needs a real plan: scout, count slots, and use undo.',
];

/**
 * How hard a mosaic is on one difficulty, from 1 (Relaxed) to 5 (Fiendish).
 * Mirrors `rating()` in Tools/generate_levels.py.
 */
export class PuzzleRating {
  constructor(level) { this.level = level; }

  static from(careless, greedy) {
    if (greedy && careless >= 0.75) return new PuzzleRating(1);
    if (greedy && careless >= 0.35) return new PuzzleRating(2);
    if (greedy) return new PuzzleRating(3);
    if (careless > 0.10) return new PuzzleRating(4);
    return new PuzzleRating(5);
  }

  static equals(a, b) { return a.level === b.level; }

  get word() { return this.level >= 1 && this.level <= 4 ? RATING_WORDS[this.level - 1] : RATING_WORDS[4]; }
  get explanation() {
    return this.level >= 1 && this.level <= 4 ? RATING_EXPLANATIONS[this.level - 1] : RATING_EXPLANATIONS[4];
  }
}

/** Measured difficulty of one mosaic on each difficulty setting. */
export class DifficultyStats {
  /**
   * @param {number[]} careless careless (random) win rate on gentle, classic, expert
   * @param {boolean[]} greedy does the one-step player win on gentle, classic, expert?
   */
  constructor(careless, greedy) {
    this.careless = careless;
    this.greedy = greedy;
  }

  static equals(a, b) {
    return a.careless.length === b.careless.length && a.greedy.length === b.greedy.length
      && a.careless.every((v, i) => v === b.careless[i]) && a.greedy.every((v, i) => v === b.greedy[i]);
  }

  rating(d) {
    const i = Difficulty.index(d);
    return PuzzleRating.from(this.careless[i], this.greedy[i]);
  }

  carelessPercent(d) { return swiftRounded(this.careless[Difficulty.index(d)] * 100); }
}

// MARK: - LevelDefinition

function hexToBigInt(h) {
  if (typeof h === 'bigint') return h;
  if (typeof h === 'number') return BigInt(h);
  if (typeof h !== 'string' || h.length === 0) return 0n;
  return BigInt('0x' + h);
}

/**
 * Everything that defines a level. Built-in levels are generated by Tools/generate_levels.py
 * (LevelData.swift → levels.json); photo levels are built on the device by PhotoLevelBuilder.
 *
 * new LevelDefinition({ id, title, subtitle, art, palette, tunnels, chambersGentle, chambersClassic,
 *   chambersExpert, solution, goldenClaimsPerMove, goldenClaimsHash, goldenFinalStateHash,
 *   isPhoto = false, carelessWins = [], greedyWins = [], isChallenge = false, pack = 'main' })
 */
export class LevelDefinition {
  constructor(f) {
    this.id = f.id;
    this.title = f.title;
    this.subtitle = f.subtitle;
    /** Mosaic rows; each character encodes family * 4 + tone as "a"..."x", "." = empty ground. */
    this.art = f.art;
    this.palette = f.palette;
    /** [[TeamSpec]]: one queue per tunnel, front first. */
    this.tunnels = f.tunnels;
    this.chambersGentle = f.chambersGentle;
    this.chambersClassic = f.chambersClassic;
    this.chambersExpert = f.chambersExpert;
    /** The designer's winning order of tunnel taps (used by hints and the self-test). */
    this.solution = f.solution;
    this.goldenClaimsPerMove = f.goldenClaimsPerMove ?? [];
    /** UInt64 → BigInt */
    this.goldenClaimsHash = hexToBigInt(f.goldenClaimsHash ?? 0n);
    this.goldenFinalStateHash = hexToBigInt(f.goldenFinalStateHash ?? 0n);
    this.isPhoto = f.isPhoto ?? false;
    /**
     * Share of careless games (random taps, no undo or assists) won on Gentle, Classic, Expert,
     * measured by the level generator. Empty for pattern and photo levels (measured on the device).
     */
    this.carelessWins = f.carelessWins ?? [];
    /**
     * Whether a sensible one-step player (always sends a team that can finish now, the one that
     * claims most) wins on Gentle, Classic, Expert.
     */
    this.greedyWins = f.greedyWins ?? [];
    /** Part of the Challenge or Master pack. */
    this.isChallenge = f.isChallenge ?? false;
    /**
     * Which pack the mosaic belongs to (a LevelCatalog.packs id such as "garden", "gallery" or
     * "master"); "main" for the main mosaics and for pattern and photo levels.
     */
    this.pack = f.pack ?? 'main';
    this._tileCount = -1;
  }

  /** Builds a built-in level from its levels.json record (tunnels [[family, quota]] → TeamSpec). */
  static fromRaw(raw, palette) {
    return new LevelDefinition({
      id: raw.id,
      title: raw.title,
      subtitle: raw.subtitle,
      art: raw.art,
      palette,
      tunnels: raw.tunnels.map(q => q.map(t => (Array.isArray(t) ? TeamSpec(t[0], t[1]) : TeamSpec(t.family, t.quota)))),
      chambersGentle: raw.chambersGentle,
      chambersClassic: raw.chambersClassic,
      chambersExpert: raw.chambersExpert,
      solution: raw.solution,
      goldenClaimsPerMove: raw.goldenClaimsPerMove,
      goldenClaimsHash: raw.goldenClaimsHash,
      goldenFinalStateHash: raw.goldenFinalStateHash,
      carelessWins: raw.carelessWins ?? [],
      greedyWins: raw.greedyWins ?? [],
      isChallenge: raw.isChallenge ?? false,
      pack: raw.pack ?? 'main',
    });
  }

  /** Difficulty measurements shipped with the level, if any (null otherwise). */
  get shippedStats() {
    if (this.carelessWins.length !== 3 || this.greedyWins.length !== 3) return null;
    return new DifficultyStats(this.carelessWins, this.greedyWins);
  }

  /** Swift chambers(for:) */
  chambers(difficulty) {
    switch (difficulty) {
      case 'gentle': return this.chambersGentle;
      case 'classic': return this.chambersClassic;
      case 'expert': return this.chambersExpert;
      default: throw new Error(`Unknown difficulty ${difficulty}`);
    }
  }

  get teamCount() { return this.tunnels.reduce((n, q) => n + q.length, 0); }

  get tileCount() {
    if (this._tileCount < 0) {
      let n = 0;
      for (const row of this.art) {
        for (const ch of row) {
          const v = ch.codePointAt(0);
          if (v >= 97 && v < 97 + 24) n += 1;
        }
      }
      this._tileCount = n;
    }
    return this._tileCount;
  }
}

// MARK: - Generated data (lazy)

let cache = Object.create(null);
const levelCache = new Map();

/** The six built-in colour families. Getters read the installed level data. */
export const GeneratedPalette = Object.freeze({
  get familyNames() { return requireLevelData().palette.names; },
  /** 6 families x 4 tones, 0xRRGGBB, light -> deep */
  get tones() { return requireLevelData().palette.tones; },
  get grout() { return requireLevelData().palette.grout; },
  get soil() { return requireLevelData().palette.soil; },
  get soilDark() { return requireLevelData().palette.soilDark; },
  get builtIn() {
    if (!cache.builtInPalette) {
      const p = requireLevelData().palette;
      cache.builtInPalette = new LevelPalette(p.names, p.tones);
    }
    return cache.builtInPalette;
  },
});

/**
 * Every built-in level by its Swift variable name (GeneratedLevels.firstDig, …). The properties
 * appear when setLevelData() runs; each LevelDefinition is built on first access and cached.
 */
export const GeneratedLevels = {};

function generatedLevel(name) {
  let l = levelCache.get(name);
  if (!l) {
    const raw = rawLevel(name);
    if (!raw) return undefined;
    l = LevelDefinition.fromRaw(raw, GeneratedPalette.builtIn);
    levelCache.set(name, l);
  }
  return l;
}

onLevelData(() => {
  cache = Object.create(null);
  levelCache.clear();
  for (const k of Object.keys(GeneratedLevels)) delete GeneratedLevels[k];
  for (const name of levelVariableNames()) {
    Object.defineProperty(GeneratedLevels, name, {
      get: () => generatedLevel(name),
      enumerable: true,
      configurable: true,
    });
  }
});

// MARK: - UnlockRule & LevelCatalog

/** What must be finished before a built-in mosaic opens: any one of `anyOf`. `label` is shown as "Locked — finish <label>". */
export function UnlockRule(anyOf, label) {
  return { anyOf, label };
}

/** The static pack lists of LevelCatalog (Swift variable names, in Level.swift's order). */
const PACK_LISTS = {
  /** The main mosaics in play order. The showcase is open from the start. */
  main: ['firstDig', 'koiPond', 'peacockFan', 'nightMarket', 'sunflower'],
  /** Interlocking pictures whose tunnels were dealt to defeat careless and one-step play. */
  challenge: ['nestingRings', 'basketWeave', 'labyrinth', 'roseWindow'],
  garden: ['gardenBalloon', 'gardenLighthouse', 'gardenToadstools', 'gardenTulips', 'gardenSailboat', 'gardenBees', 'gardenOwl', 'gardenDesert'],
  /** The hardest mosaics: tunnel orders searched to defeat one-step play (still solvable). */
  master: ['masterTiger', 'masterGiraffe', 'masterAutumn', 'masterCastle', 'masterViaduct', 'masterSkyline', 'masterChameleon', 'masterOctopus'],
  wild: ['wildIceberg', 'wildAurora', 'wildRainforest', 'wildBamboo', 'wildCanyon', 'wildFalls', 'wildVolcano', 'wildReef'],
  gallery: ['gallerySunrise', 'galleryPearl', 'galleryMonaLisa', 'galleryLilyPond', 'galleryStarryNight', 'galleryGrandeJatte', 'galleryKiss', 'galleryScream'],
  worldArt: ['worldMingVase', 'worldCircles', 'worldGreatWave', 'worldShower', 'worldAlhambra', 'worldSunStone', 'worldRavenna', 'worldMondrian'],
  ancient: ['ancientStonehenge', 'ancientLascaux', 'ancientOlympia', 'ancientMask', 'ancientTerracotta', 'ancientGreatWall', 'ancientPyramids', 'ancientColosseum'],
  voyages: ['voyageTreasureShip', 'voyageSilkRoad', 'voyageWayfinders', 'voyageLongship', 'voyagePress', 'voyageGalileo', 'voyageGalapagos', 'voyageSouthPole'],
  modern: ['modernLiberty', 'modernFirstFlight', 'modernEiffel', 'modernGoldenGate', 'modernSputnik', 'modernBerlinWall', 'modernEverest', 'modernMoon'],
  cosmos: ['cosmosHalley', 'cosmosPrism', 'cosmosSaturn', 'cosmosEclipse', 'cosmosGalaxy', 'cosmosPeriodic', 'cosmosKite', 'cosmosHelix'],
  /** Literature: iconic scenes from public-domain books, plays and tales (gentlest first). */
  epics: ['epicsSirens', 'epicsMonkeyKing', 'epicsTrojanHorse', 'epicsSwordStone', 'epicsCelestialRose', 'epicsAliBaba', 'epicsDragonHoard', 'epicsGenji'],
  tales: ['talesTortoiseHare', 'talesBeanstalk', 'talesRapunzel', 'talesSnowQueen', 'talesRedRidingHood', 'talesPrincessPea', 'talesCinderella', 'talesGingerbread'],
  childrens: ['kidsYellowBrick', 'kidsRiverbank', 'kidsSecretGarden', 'kidsRailway', 'kidsCouncilRock', 'kidsPinocchio', 'kidsTeaParty', 'kidsLookingGlass'],
  stage: ['stageWitches', 'stageBalcony', 'stageTempest', 'stageYorick', 'stageFairyWood', 'stageCleopatra', 'stageGlobe', 'stageCaskets'],
  adventure: ['advWindmills', 'advLilliput', 'advNautilus', 'advUndergroundSea', 'advRaft', 'advWhiteWhale', 'advFootprint', 'advTreasureMap'],
  gothic: ['gothicRaven', 'gothicHound', 'gothicNotreDame', 'gothicArctic', 'gothicHorseman', 'gothicDracula', 'gothicChandelier', 'gothicTripods'],
  novels: ['novelChristmas', 'novelWuthering', 'novelComet', 'novelHavisham', 'novelGreenLight', 'novelCandlesticks', 'novelNetherfield', 'novelWorkhouse'],
  /** Natural History: tile homages of famous public-domain natural-history plates. */
  naturalist: ['natFlamingo', 'natMetamorphosis', 'natHummingbirds', 'natRose', 'natJellyfish', 'natShells', 'natBeetles', 'natRadiolarians'],
  /** World Craft: traditional crafts and patterns from around the world. */
  crafts: ['craftPysanky', 'craftTalavera', 'craftPaperCut', 'craftTartan', 'craftDelft', 'craftCarpet', 'craftAsanoha', 'craftQuilt'],
  /** Geometry & Illusions: figures, fractals and optical illusions. */
  geometry: ['geoMandelbrot', 'geoTriangle', 'geoSpiral', 'geoSierpinski', 'geoCafeWall', 'geoHilbert', 'geoCelticKnot', 'geoGirih'],
  /** Probes & Telescopes: famous views from space probes, rovers and telescopes. */
  space: ['spaceEarthrise', 'spacePlutoHeart', 'spaceMarsSunset', 'spacePillars', 'spaceRover', 'spaceRedSpot', 'spaceCliffs', 'spaceDeepField'],
  /** Inventions & Firsts: famous machines and first moments of invention. */
  inventions: ['invLightBulb', 'invFlyingMachine', 'invTelephone', 'invPennyFarthing', 'invLoom', 'invDifferenceEngine', 'invRocket', 'invFirstPhoto'],
  /** Halloween (seasonal): in season from late September to early November. */
  halloween: ['halloBlackCat', 'halloTrickOrTreat', 'halloJackOLantern', 'halloGhosts', 'halloScarecrow', 'halloHauntedHouse', 'halloPumpkinPatch', 'halloSpiderWeb'],
  /** Winter (seasonal): in season from December to February. */
  winter: ['winterCocoa', 'winterSledding', 'winterSnowman', 'winterCardinal', 'winterSnowflake', 'winterSkating', 'winterSnowGlobe', 'winterFrostWindow'],
};

/** Swift's `builtIn` join order. */
const BUILT_IN_ORDER = ['main', 'challenge', 'garden', 'master',
  'wild', 'gallery', 'worldArt', 'ancient', 'voyages', 'modern', 'cosmos',
  'epics', 'tales', 'childrens', 'stage', 'adventure', 'gothic', 'novels',
  'naturalist', 'crafts', 'geometry', 'space', 'inventions', 'halloween', 'winter'];

/** The packs in the order Home shows them (and "Next up" walks them): [id, title, list name]. */
const PACK_TABLE = [
  ['main', 'MOSAICS', 'main'],
  ['garden', 'GARDEN', 'garden'],
  ['wild', 'WILD WONDERS', 'wild'],
  ['gallery', 'GALLERY', 'gallery'],
  ['worldart', 'WORLD ART', 'worldArt'],
  ['epics', 'EPICS & LEGENDS', 'epics'],
  ['tales', 'FAIRY TALES & FABLES', 'tales'],
  ['childrens', "CHILDREN'S CLASSICS", 'childrens'],
  ['stage', 'SHAKESPEARE', 'stage'],
  ['adventure', 'ADVENTURE CLASSICS', 'adventure'],
  ['gothic', 'GOTHIC & MYSTERY', 'gothic'],
  ['novels', 'GREAT NOVELS', 'novels'],
  ['ancient', 'ANCIENT WORLD', 'ancient'],
  ['voyages', 'VOYAGES', 'voyages'],
  ['modern', 'MODERN MOMENTS', 'modern'],
  ['cosmos', 'SKY & SCIENCE', 'cosmos'],
  ['naturalist', 'NATURAL HISTORY', 'naturalist'],
  ['crafts', 'WORLD CRAFT', 'crafts'],
  ['space', 'PROBES & TELESCOPES', 'space'],
  ['geometry', 'GEOMETRY & ILLUSIONS', 'geometry'],
  ['inventions', 'INVENTIONS & FIRSTS', 'inventions'],
  ['halloween', 'HALLOWEEN', 'halloween'],
  ['winter', 'WINTER', 'winter'],
  ['challenge', 'CHALLENGE', 'challenge'],
  ['master', 'MASTER', 'master'],
];

/** Home groups the packs into themes — the wings of the collection. */
const THEMES = Object.freeze([
  { id: 'start', title: 'First Mosaics', icon: 'ant.fill', packIDs: ['main'] },
  { id: 'seasons', title: 'Seasons', icon: 'snowflake', packIDs: ['halloween', 'winter'] },
  { id: 'nature', title: 'Nature', icon: 'leaf.fill', packIDs: ['garden', 'wild', 'naturalist'] },
  { id: 'art', title: 'Art', icon: 'paintpalette.fill', packIDs: ['gallery', 'worldart', 'crafts'] },
  { id: 'literature', title: 'Literature', icon: 'book.fill', packIDs: ['epics', 'tales', 'childrens', 'stage', 'adventure', 'gothic', 'novels'] },
  { id: 'history', title: 'History', icon: 'building.columns.fill', packIDs: ['ancient', 'voyages', 'modern', 'inventions'] },
  { id: 'science', title: 'Sky & Science', icon: 'sparkles', packIDs: ['cosmos', 'space', 'geometry'] },
  { id: 'skill', title: 'Tests of Skill', icon: 'flame.fill', packIDs: ['challenge', 'master'] },
].map(t => Object.freeze({ ...t, packIDs: Object.freeze(t.packIDs) })));

/** The collection packs (themes Seasons, Nature, Art, Literature, History and Sky & Science, apart from Garden). */
const COLLECTION_PACK_IDS = new Set(['wild', 'gallery', 'worldart', 'ancient', 'voyages', 'modern', 'cosmos',
  'epics', 'tales', 'childrens', 'stage', 'adventure', 'gothic', 'novels',
  'naturalist', 'crafts', 'geometry', 'space', 'inventions',
  'halloween', 'winter']);

/** Seasonal packs and when they are in season (month, day — inclusive, the range may wrap the new year). */
const SEASONS = Object.freeze([
  Object.freeze({ packID: 'halloween', from: Object.freeze([9, 20]), to: Object.freeze([11, 7]) }),
  Object.freeze({ packID: 'winter', from: Object.freeze([12, 1]), to: Object.freeze([2, 28]) }),
]);

/** Finishing the value unlocks the key (main chain). */
const UNLOCKED_BY = Object.freeze(Object.assign(Object.create(null), {
  koiPond: 'firstDig',
  peacockFan: 'koiPond',
  nightMarket: 'peacockFan',
}));

function list(name) {
  const k = 'list:' + name;
  if (!cache[k]) cache[k] = Object.freeze(PACK_LISTS[name].map(n => {
    const l = generatedLevel(n);
    if (!l) throw new Error(`Level data has no level named ${n}`);
    return l;
  }));
  return cache[k];
}

function lazy(key, make) {
  if (!(key in cache)) cache[key] = make();
  return cache[key];
}

const ids = levels => levels.map(l => l.id);

/**
 * The built-in catalogue. Swift static lets are getters here (computed on first use after
 * setLevelData); packs/themes/seasons are arrays of objects in place of Swift tuples:
 * packs [{ id, title, levels }], themes [{ id, title, icon, packIDs }],
 * seasons [{ packID, from: [month, day], to: [month, day] }]. packOfLevel and unlockedBy are
 * null-prototype objects (id → id); collectionPackIDs is a Set.
 */
export const LevelCatalog = Object.freeze({
  get main() { return list('main'); },
  get challenge() { return list('challenge'); },
  get garden() { return list('garden'); },
  get master() { return list('master'); },
  get wild() { return list('wild'); },
  get gallery() { return list('gallery'); },
  get worldArt() { return list('worldArt'); },
  get ancient() { return list('ancient'); },
  get voyages() { return list('voyages'); },
  get modern() { return list('modern'); },
  get cosmos() { return list('cosmos'); },
  get epics() { return list('epics'); },
  get tales() { return list('tales'); },
  get childrens() { return list('childrens'); },
  get stage() { return list('stage'); },
  get adventure() { return list('adventure'); },
  get gothic() { return list('gothic'); },
  get novels() { return list('novels'); },
  get naturalist() { return list('naturalist'); },
  get crafts() { return list('crafts'); },
  get geometry() { return list('geometry'); },
  get space() { return list('space'); },
  get inventions() { return list('inventions'); },
  get halloween() { return list('halloween'); },
  get winter() { return list('winter'); },

  /** Every built-in mosaic. */
  get builtIn() {
    return lazy('builtIn', () => Object.freeze(BUILT_IN_ORDER.flatMap(n => list(n))));
  },

  /** The packs in the order Home shows them (and "Next up" walks them). */
  get packs() {
    return lazy('packs', () => Object.freeze(PACK_TABLE.map(([id, title, name]) =>
      Object.freeze({ id, title, levels: list(name) }))));
  },

  get themes() { return THEMES; },
  get collectionPackIDs() { return COLLECTION_PACK_IDS; },
  get seasons() { return SEASONS; },

  /**
   * Is a seasonal pack in season on `date`? (false for every other pack). `date` is a Date or epoch
   * milliseconds; month and day are read in the viewer's local calendar (Calendar.current).
   */
  isInSeason(packID, date = new Date()) {
    const s = SEASONS.find(x => x.packID === packID);
    if (!s) return false;
    const d = date instanceof Date ? date : new Date(date);
    const md = (d.getMonth() + 1) * 100 + d.getDate();
    const from = s.from[0] * 100 + s.from[1];
    const to = s.to[0] * 100 + s.to[1];
    return from <= to ? (md >= from && md <= to) : (md >= from || md <= to);
  },

  /** Which pack each built-in mosaic belongs to. */
  get packOfLevel() {
    return lazy('packOfLevel', () => {
      const d = Object.create(null);
      for (const p of LevelCatalog.packs) for (const l of p.levels) d[l.id] = p.id;
      return Object.freeze(d);
    });
  },

  pack(id) {
    const p = LevelCatalog.packs.find(x => x.id === id);
    return p ? p.levels : [];
  },

  packTitle(id) {
    const p = LevelCatalog.packs.find(x => x.id === id);
    return p ? p.title : String(id).toUpperCase();
  },

  /**
   * When a pack opens, its first three mosaics are found; every mosaic finished in the pack finds
   * one more (Settings → Unlock all shows everything).
   */
  foundWhenPackOpens: 3,

  /** Finishing the value unlocks the key (main chain). */
  get unlockedBy() { return UNLOCKED_BY; },

  /** What opens a whole pack (null = open from the start). */
  packRule(packID) {
    switch (packID) {
      case 'garden': case 'wild': case 'gallery': case 'ancient': case 'challenge':
      case 'epics': case 'tales': case 'halloween': case 'winter':
        return UnlockRule(['firstDig'], GeneratedLevels.firstDig.title);
      case 'naturalist': return UnlockRule(ids(LevelCatalog.garden), 'any Garden mosaic');
      case 'crafts': return UnlockRule(ids(LevelCatalog.worldArt), 'any World Art mosaic');
      case 'space': return UnlockRule(ids(LevelCatalog.cosmos), 'any Sky & Science mosaic');
      case 'geometry': return UnlockRule(ids(LevelCatalog.challenge), 'any Challenge mosaic');
      case 'inventions': return UnlockRule(ids(LevelCatalog.modern), 'any Modern Moments mosaic');
      case 'childrens': return UnlockRule(ids(LevelCatalog.tales), 'any Fairy Tales mosaic');
      case 'adventure': return UnlockRule(ids(LevelCatalog.childrens), "any Children's Classics mosaic");
      case 'stage': return UnlockRule(ids(LevelCatalog.epics), 'any Epics & Legends mosaic');
      case 'gothic': return UnlockRule(ids(LevelCatalog.adventure), 'any Adventure Classics mosaic');
      case 'novels': return UnlockRule(ids(LevelCatalog.stage), 'any Shakespeare mosaic');
      case 'worldart': return UnlockRule(ids(LevelCatalog.gallery), 'any Gallery mosaic');
      case 'voyages': return UnlockRule(ids(LevelCatalog.ancient), 'any Ancient World mosaic');
      case 'modern': return UnlockRule(ids(LevelCatalog.voyages), 'any Voyages mosaic');
      case 'cosmos': return UnlockRule(ids(LevelCatalog.wild), 'any Wild Wonders mosaic');
      case 'master': return UnlockRule(ids(LevelCatalog.challenge), 'any Challenge mosaic');
      default: return null;
    }
  },

  /** The unlock rule for a built-in mosaic (null = open from the start). Swift unlockRule(for:). */
  unlockRule(id) {
    const req = UNLOCKED_BY[id];
    if (req !== undefined) {
      const l = LevelCatalog.builtIn.find(x => x.id === req);
      return UnlockRule([req], l ? l.title : req);
    }
    const p = LevelCatalog.packOfLevel[id];
    if (p !== undefined && p !== 'main') return LevelCatalog.packRule(p);
    return null;
  },

  /** The pack list a mosaic belongs to (for "Next mosaic"). Swift packList(containing:). */
  packList(id) {
    for (const p of LevelCatalog.packs) if (p.levels.some(l => l.id === id)) return p.levels;
    return LevelCatalog.main;
  },
});
