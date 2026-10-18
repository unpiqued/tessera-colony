// The catalogue (Level.swift's LevelCatalog), level definitions, palette, ratings, seasons and the
// collection rules (Collection.swift): found limits, status, stars, mastered and the harder steps.
// Golden values from SelfTest.swift section 7 and the Swift tables themselves (Level.swift is parsed
// and compared when the Swift sources are present).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';
import { setLevelData, levelVariableNames } from '../src/core/levelData.js';
import {
  LevelCatalog, GeneratedLevels, GeneratedPalette, LevelPalette, LevelDefinition, Difficulty,
  PuzzleRating, DifficultyStats, TeamSpec, swiftRounded,
} from '../src/core/level.js';
import { ChallengeModifier } from '../src/core/scoring.js';
import { SaveStore, SaveGame } from '../src/core/saveStore.js';
import { StatusFilter, CollectionStatus, HarderStep, PackProgress } from '../src/core/collection.js';
import { AppModel } from '../src/core/appModel.js';

const json = readFileSync(new URL('../data/levels.json', import.meta.url), 'utf8');
setLevelData(json);
const raw = JSON.parse(json);
const swiftPath = new URL('../../TesseraColony.swiftpm/Level.swift', import.meta.url);
const swift = existsSync(swiftPath) ? readFileSync(swiftPath, 'utf8') : null;

const PACK_ORDER = [
  ['main', 'MOSAICS', 5], ['garden', 'GARDEN', 8], ['wild', 'WILD WONDERS', 8], ['gallery', 'GALLERY', 8],
  ['worldart', 'WORLD ART', 8], ['epics', 'EPICS & LEGENDS', 8], ['tales', 'FAIRY TALES & FABLES', 8],
  ['childrens', "CHILDREN'S CLASSICS", 8], ['stage', 'SHAKESPEARE', 8], ['adventure', 'ADVENTURE CLASSICS', 8],
  ['gothic', 'GOTHIC & MYSTERY', 8], ['novels', 'GREAT NOVELS', 8], ['ancient', 'ANCIENT WORLD', 8],
  ['voyages', 'VOYAGES', 8], ['modern', 'MODERN MOMENTS', 8], ['cosmos', 'SKY & SCIENCE', 8],
  ['naturalist', 'NATURAL HISTORY', 8], ['crafts', 'WORLD CRAFT', 8], ['space', 'PROBES & TELESCOPES', 8],
  ['geometry', 'GEOMETRY & ILLUSIONS', 8], ['inventions', 'INVENTIONS & FIRSTS', 8], ['halloween', 'HALLOWEEN', 8],
  ['winter', 'WINTER', 8], ['challenge', 'CHALLENGE', 4], ['master', 'MASTER', 8],
];
const ids = l => l.map(x => x.id);
const freshApp = (hooks) => {
  SaveStore.setBackend(SaveStore.memoryBackend());
  return new AppModel(hooks);
};

test('193 built-in levels load, by Swift variable name, with unique ids', () => {
  assert.equal(levelVariableNames().length, 193);
  assert.equal(Object.keys(GeneratedLevels).length, 193);
  assert.equal(LevelCatalog.builtIn.length, 193);
  const all = ids(LevelCatalog.builtIn);
  assert.equal(new Set(all).size, 193);
  for (const name of levelVariableNames()) {
    const l = GeneratedLevels[name];
    assert.ok(l instanceof LevelDefinition);
    assert.equal(l, GeneratedLevels[name], 'cached');
    assert.ok(all.includes(l.id), `${name} is in a pack`);
  }
});

test('packs: Swift order, titles, counts, every level tagged with its pack, in exactly one pack', () => {
  assert.deepEqual(LevelCatalog.packs.map(p => [p.id, p.title, p.levels.length]), PACK_ORDER);
  const seen = new Map();
  for (const p of LevelCatalog.packs) {
    for (const l of p.levels) {
      assert.equal(l.pack, p.id, `${l.id} tagged ${l.pack}`);
      assert.ok(!seen.has(l.id), `${l.id} listed twice`);
      seen.set(l.id, p.id);
      assert.equal(LevelCatalog.packOfLevel[l.id], p.id);
    }
    assert.equal(LevelCatalog.pack(p.id), p.levels);
    assert.equal(LevelCatalog.packTitle(p.id), p.title);
  }
  assert.equal(seen.size, 193);
  // spot checks of order
  assert.deepEqual(ids(LevelCatalog.main), ['firstDig', 'koiPond', 'peacockFan', 'nightMarket', 'sunflower']);
  assert.deepEqual(ids(LevelCatalog.challenge), ['nestingRings', 'basketWeave', 'labyrinth', 'roseWindow']);
  assert.equal(LevelCatalog.garden[0].id, 'gardenBalloon');
  assert.equal(LevelCatalog.worldArt.at(-1).id, 'worldMondrian');
  assert.equal(LevelCatalog.winter.at(-1).id, 'winterFrostWindow');
  assert.equal(LevelCatalog.builtIn[0].id, 'firstDig');
  assert.equal(LevelCatalog.builtIn[5].id, 'nestingRings', 'builtIn joins main, challenge, garden, master, …');
  assert.equal(LevelCatalog.builtIn.at(-1).id, 'winterFrostWindow');
  assert.deepEqual(LevelCatalog.pack('nope'), []);
  assert.equal(LevelCatalog.packTitle('nope'), 'NOPE');
  // challenge flags: Challenge and Master packs
  const flagged = LevelCatalog.builtIn.filter(l => l.isChallenge).map(l => l.id).sort();
  assert.deepEqual(flagged, ids(LevelCatalog.challenge).concat(ids(LevelCatalog.master)).sort());
});

test('packs and themes match the Swift tables in Level.swift', { skip: swift === null }, () => {
  const lists = {};
  for (const m of swift.matchAll(/static let (\w+): \[LevelDefinition\] = \[(.*?)\]/gs)) {
    const names = [...m[2].matchAll(/GeneratedLevels\.(\w+)/g)].map(x => x[1]);
    if (names.length) lists[m[1]] = names;
  }
  assert.equal(Object.keys(lists).length, 25);
  for (const [name, list] of Object.entries(lists)) assert.deepEqual(ids(LevelCatalog[name]), list, name);
  const packs = [...swift.matchAll(/\("(\w+)", "([^"]+)", (\w+)\)/g)].map(m => [m[1], m[2], lists[m[3]].length]);
  assert.deepEqual(packs, PACK_ORDER);
  const themes = [...swift.matchAll(/\("(\w+)", "([^"]+)", "([\w.]+)", \[([^\]]*)\]\)/g)]
    .map(m => ({ id: m[1], title: m[2], icon: m[3], packIDs: [...m[4].matchAll(/"(\w+)"/g)].map(x => x[1]) }));
  assert.deepEqual(LevelCatalog.themes.map(t => ({ ...t, packIDs: [...t.packIDs] })), themes);
  const coll = swift.match(/collectionPackIDs: Set<String> = \[(.*?)\]/s)[1];
  assert.deepEqual([...LevelCatalog.collectionPackIDs].sort(), [...coll.matchAll(/"(\w+)"/g)].map(x => x[1]).sort());
  // every packRule branch names the same pack list and label as Swift
  const body = swift.match(/static func packRule[\s\S]*?\n    }\n/)[0];
  const branches = [...body.matchAll(/case "(\w+)":\n\s+return UnlockRule\(anyOf: (\w+)\.map \{ \$0\.id \}, label: "([^"]+)"\)/g)];
  assert.equal(branches.length, 15);
  assert.equal(themes.length, 8);
  for (const m of branches) {
    const r = LevelCatalog.packRule(m[1]);
    assert.deepEqual(r, { anyOf: ids(LevelCatalog[m[2]]), label: m[3] }, m[1]);
  }
  const first = body.match(/case ((?:"\w+", )*"\w+"):\n\s+return firstDig/)[1];
  for (const id of [...first.matchAll(/"(\w+)"/g)].map(x => x[1])) {
    assert.deepEqual(LevelCatalog.packRule(id), { anyOf: ['firstDig'], label: 'First Dig' }, id);
  }
});

test('themes and collection packs (SelfTest: every pack in a theme)', () => {
  assert.deepEqual(LevelCatalog.themes.map(t => [t.id, t.title, t.icon, t.packIDs.length]), [
    ['start', 'First Mosaics', 'ant.fill', 1], ['seasons', 'Seasons', 'snowflake', 2],
    ['nature', 'Nature', 'leaf.fill', 3], ['art', 'Art', 'paintpalette.fill', 3],
    ['literature', 'Literature', 'book.fill', 7], ['history', 'History', 'building.columns.fill', 4],
    ['science', 'Sky & Science', 'sparkles', 3], ['skill', 'Tests of Skill', 'flame.fill', 2],
  ]);
  const inThemes = LevelCatalog.themes.flatMap(t => t.packIDs);
  assert.equal(inThemes.length, 25);
  assert.deepEqual(new Set(inThemes), new Set(LevelCatalog.packs.map(p => p.id)));
  assert.equal(LevelCatalog.collectionPackIDs.size, 21);
  for (const id of ['main', 'garden', 'challenge', 'master']) assert.ok(!LevelCatalog.collectionPackIDs.has(id));
  assert.equal(LevelCatalog.foundWhenPackOpens, 3);
});

test('packRule: every branch', () => {
  const firstDig = { anyOf: ['firstDig'], label: 'First Dig' };
  for (const id of ['garden', 'wild', 'gallery', 'ancient', 'challenge', 'epics', 'tales', 'halloween', 'winter']) {
    assert.deepEqual(LevelCatalog.packRule(id), firstDig, id);
  }
  const chained = {
    naturalist: ['garden', 'any Garden mosaic'],
    crafts: ['worldArt', 'any World Art mosaic'],
    space: ['cosmos', 'any Sky & Science mosaic'],
    geometry: ['challenge', 'any Challenge mosaic'],
    inventions: ['modern', 'any Modern Moments mosaic'],
    childrens: ['tales', 'any Fairy Tales mosaic'],
    adventure: ['childrens', "any Children's Classics mosaic"],
    stage: ['epics', 'any Epics & Legends mosaic'],
    gothic: ['adventure', 'any Adventure Classics mosaic'],
    novels: ['stage', 'any Shakespeare mosaic'],
    worldart: ['gallery', 'any Gallery mosaic'],
    voyages: ['ancient', 'any Ancient World mosaic'],
    modern: ['voyages', 'any Voyages mosaic'],
    cosmos: ['wild', 'any Wild Wonders mosaic'],
    master: ['challenge', 'any Challenge mosaic'],
  };
  for (const [id, [list, label]] of Object.entries(chained)) {
    assert.deepEqual(LevelCatalog.packRule(id), { anyOf: ids(LevelCatalog[list]), label }, id);
  }
  assert.equal(LevelCatalog.packRule('main'), null);
  assert.equal(LevelCatalog.packRule('photo'), null);
  // all 25 packs covered: 9 + 15 + main
  assert.equal(9 + Object.keys(chained).length + 1, LevelCatalog.packs.length);
});

test('unlockRule: main chain, pack rules, open levels; every rule points at real mosaics (SelfTest)', () => {
  assert.deepEqual(LevelCatalog.unlockRule('koiPond'), { anyOf: ['firstDig'], label: 'First Dig' });
  assert.deepEqual(LevelCatalog.unlockRule('peacockFan'), { anyOf: ['koiPond'], label: 'Koi Pond' });
  assert.deepEqual(LevelCatalog.unlockRule('nightMarket'), { anyOf: ['peacockFan'], label: GeneratedLevels.peacockFan.title });
  assert.equal(LevelCatalog.unlockRule('firstDig'), null);
  assert.equal(LevelCatalog.unlockRule('sunflower'), null, 'the showcase is open from the start');
  assert.equal(LevelCatalog.unlockRule('photo-abc'), null);
  assert.deepEqual(LevelCatalog.unlockRule('gardenOwl'), LevelCatalog.packRule('garden'));
  assert.deepEqual(LevelCatalog.unlockRule('natRose'), LevelCatalog.packRule('naturalist'));
  assert.deepEqual(LevelCatalog.unlockRule('masterTiger'), LevelCatalog.packRule('master'));
  assert.deepEqual(LevelCatalog.unlockedBy, Object.assign(Object.create(null), { koiPond: 'firstDig', peacockFan: 'koiPond', nightMarket: 'peacockFan' }));
  const known = new Set(ids(LevelCatalog.builtIn));
  for (const l of LevelCatalog.builtIn) {
    const r = LevelCatalog.unlockRule(l.id);
    if (!r) continue;
    assert.ok(r.anyOf.length > 0 && r.anyOf.every(id => known.has(id) && id !== l.id), l.id);
  }
});

test('packList: the pack a mosaic belongs to, main for anything else', () => {
  assert.equal(LevelCatalog.packList('gardenOwl'), LevelCatalog.garden);
  assert.equal(LevelCatalog.packList('roseWindow'), LevelCatalog.challenge);
  assert.equal(LevelCatalog.packList('photo-xyz'), LevelCatalog.main);
});

test('isInSeason: Halloween 9/20–11/7, Winter 12/1–2/28 across the new year (local calendar)', () => {
  const day = (m, d, h = 12, y = 2026) => new Date(y, m - 1, d, h);
  const cases = [
    ['halloween', 9, 19, false], ['halloween', 9, 20, true], ['halloween', 10, 31, true],
    ['halloween', 11, 7, true], ['halloween', 11, 8, false], ['halloween', 3, 1, false],
    ['winter', 11, 30, false], ['winter', 12, 1, true], ['winter', 12, 25, true], ['winter', 12, 31, true],
    ['winter', 1, 1, true], ['winter', 1, 15, true], ['winter', 2, 28, true], ['winter', 3, 1, false],
    ['winter', 7, 1, false], ['gallery', 10, 31, false], ['main', 12, 25, false],
  ];
  for (const [p, m, d, want] of cases) {
    assert.equal(LevelCatalog.isInSeason(p, day(m, d)), want, `${p} ${m}/${d}`);
    assert.equal(LevelCatalog.isInSeason(p, day(m, d, 0).getTime()), want, `${p} ${m}/${d} 00:00 as ms`);
    assert.equal(LevelCatalog.isInSeason(p, new Date(2026, m - 1, d, 23, 59, 59)), want, `${p} ${m}/${d} 23:59`);
  }
  assert.equal(LevelCatalog.isInSeason('winter', day(2, 29, 12, 2028)), false, 'Feb 29 is after the 2/28 end');
  assert.equal(typeof LevelCatalog.isInSeason('halloween'), 'boolean', 'defaults to now');
  assert.deepEqual(LevelCatalog.seasons.map(s => [s.packID, [...s.from], [...s.to]]),
    [['halloween', [9, 20], [11, 7]], ['winter', [12, 1], [2, 28]]]);
});

test('palette: built-in families, tone clamping, names, luminance', () => {
  const p = GeneratedPalette.builtIn;
  assert.ok(p instanceof LevelPalette);
  assert.deepEqual(p.names, ['Lapis', 'Saffron', 'Fern', 'Ember', 'Umber', 'Pearl']);
  assert.equal(p.familyCount, 6);
  assert.equal(GeneratedPalette.soil, 0x3A2D22);
  assert.equal(GeneratedPalette.grout, 0x261D16);
  assert.equal(GeneratedPalette.soilDark, 0x2C2119);
  assert.equal(p.tone(0, 2), 0x4A8FD1);
  assert.equal(p.tone(0, -3), 0xAED6F4);
  assert.equal(p.tone(0, 9), 0x2A5FA8);
  assert.equal(p.tone(6, 0), 0x888888);
  assert.equal(p.tone(-1, 0), 0x888888);
  assert.equal(p.name(2), 'Fern');
  assert.equal(p.name(6), 'Colour 7');
  assert.equal(p.name(-1), 'Colour 0');
  // luminance of tone 1: Pearl is light, Umber is dark
  assert.ok(p.luminance(5) > 0.8 && p.luminance(4) < 0.1);
  const lin = v => (v / 255 <= 0.04045 ? v / 255 / 12.92 : Math.pow((v / 255 + 0.055) / 1.055, 2.4));
  assert.equal(p.luminance(1), 0.2126 * lin(0xFF) + 0.7152 * lin(0xCA) + 0.0722 * lin(0x2C));
  assert.equal(LevelPalette.luminance({ names: [], tones: [[0, 0xFFFFFF]] }, 0), 1);
  assert.equal(LevelPalette.tone({ names: [], tones: raw.palette.tones }, 3, 1), 0xF76A43);
  assert.deepEqual(JSON.parse(JSON.stringify(p)), { names: raw.palette.names, tones: raw.palette.tones });
  assert.ok(LevelPalette.equals(p, LevelPalette.from(JSON.parse(JSON.stringify(p)))));
});

test('LevelDefinition fields and computed properties', () => {
  const fd = GeneratedLevels.firstDig;
  const r = raw.levels.firstDig;
  assert.equal(fd.title, 'First Dig');
  assert.equal(fd.palette, GeneratedPalette.builtIn);
  assert.deepEqual(fd.tunnels[0][0], TeamSpec(2, 96));
  assert.equal(fd.teamCount, r.tunnels.flat().length);
  assert.equal(fd.tileCount, 1008);
  assert.equal(fd.tileCount, r.art.join('').replace(/[^a-x]/g, '').length);
  assert.equal(fd.chambers('gentle'), r.chambersGentle);
  assert.equal(fd.chambers('classic'), r.chambersClassic);
  assert.equal(fd.chambers('expert'), r.chambersExpert);
  assert.equal(fd.goldenClaimsHash, 0x4B5504CED572B875n);
  assert.equal(typeof fd.goldenFinalStateHash, 'bigint');
  assert.equal(fd.isPhoto, false);
  assert.equal(fd.isChallenge, false);
  assert.equal(fd.pack, 'main');
  const st = fd.shippedStats;
  assert.ok(st instanceof DifficultyStats);
  assert.deepEqual(st.careless, [1, 0.925, 0.35]);
  assert.deepEqual(st.greedy, [true, true, false]);
  assert.equal(st.rating('gentle').level, 1);
  assert.equal(st.rating('classic').level, 1);
  assert.equal(st.rating('expert').level, 4);
  assert.equal(st.carelessPercent('classic'), 93);
  assert.equal(st.carelessPercent('expert'), 35);
  const bare = new LevelDefinition({ id: 'x', title: 'X', subtitle: '', art: ['ab.', '.x.'], palette: GeneratedPalette.builtIn,
    tunnels: [[TeamSpec(0, 2)], [TeamSpec(5, 1)]], chambersGentle: 3, chambersClassic: 2, chambersExpert: 1, solution: [0, 1] });
  assert.equal(bare.shippedStats, null);
  assert.equal(bare.tileCount, 3);
  assert.equal(bare.teamCount, 2);
  assert.equal(bare.pack, 'main');
  assert.equal(bare.goldenClaimsHash, 0n);
  for (const l of LevelCatalog.builtIn) assert.ok(l.shippedStats, `${l.id} ships stats`);
});

test('Difficulty, PuzzleRating and swiftRounded', () => {
  assert.deepEqual([...Difficulty.allCases], ['gentle', 'classic', 'expert']);
  assert.deepEqual(Difficulty.allCases.map(Difficulty.title), ['Gentle', 'Classic', 'Expert']);
  assert.deepEqual(Difficulty.allCases.map(Difficulty.index), [0, 1, 2]);
  assert.deepEqual(Difficulty.allCases.map(Difficulty.showsFitBadges), [true, false, false]);
  assert.match(Difficulty.blurb('expert'), /little room to wait/);
  assert.ok(Difficulty.isValid('expert') && !Difficulty.isValid('hard') && !Difficulty.isValid('toString'));
  const r = (c, g) => PuzzleRating.from(c, g).level;
  assert.deepEqual([r(0.75, true), r(0.7499, true), r(0.35, true), r(0.3499, true), r(0, true)], [1, 2, 2, 3, 3]);
  assert.deepEqual([r(1, false), r(0.1001, false), r(0.10, false), r(0, false)], [4, 4, 5, 5]);
  assert.deepEqual([1, 2, 3, 4, 5, 0].map(l => new PuzzleRating(l).word), ['Relaxed', 'Steady', 'Tricky', 'Hard', 'Fiendish', 'Fiendish']);
  assert.equal(new PuzzleRating(1).explanation, 'Almost any order works.');
  assert.equal(new PuzzleRating(5).explanation, 'Needs a real plan: scout, count slots, and use undo.');
  assert.deepEqual([2.5, -2.5, 0.49999, 1966.0000000000002].map(swiftRounded), [3, -3, 0, 1966]);
});

test('HarderStep chain: Gentle → Classic → Expert → Expert with one more harder option each time (SelfTest)', () => {
  let step = HarderStep.after('gentle', []);
  const chain = [];
  while (step && chain.length < 20) {
    chain.push(step.label);
    step = HarderStep.after(step.difficulty, step.modifiers);
  }
  assert.equal(chain.length, 2 + ChallengeModifier.allCases.length);
  assert.deepEqual(chain, ['Try it on Classic', 'Try it on Expert', 'Expert + Hidden queue', 'Expert + No scouting',
    'Expert + No hints', 'Expert + 3 undos', 'Expert + No assists', 'Expert + No colour twice']);
  const s = HarderStep.after('classic', new Set(['noHints']));
  assert.equal(s.difficulty, 'expert');
  assert.deepEqual([...s.modifiers], ['noHints']);
  const e = HarderStep.after('expert', ['noHints']);
  assert.deepEqual(ChallengeModifier.sorted(e.modifiers), ['hiddenQueue', 'noHints']);
  assert.equal(HarderStep.after('expert', ChallengeModifier.allCases), null);
  assert.deepEqual(freshApp().harderStep('gentle', []), HarderStep.after('gentle', []));
});

test('StatusFilter and CollectionStatus', () => {
  assert.deepEqual(StatusFilter.allCases.map(StatusFilter.title), ['All', 'To explore', 'Explored', 'Go harder', 'Mastered']);
  assert.deepEqual(StatusFilter.allCases.map(StatusFilter.icon),
    ['square.grid.2x2', 'magnifyingglass', 'star.fill', 'arrow.up.circle', 'flame.fill']);
  assert.equal(CollectionStatus.isPlayable(CollectionStatus.packLocked('First Dig')), false);
  assert.equal(CollectionStatus.isPlayable(CollectionStatus.hidden(2)), false);
  assert.equal(CollectionStatus.isPlayable(CollectionStatus.found(0)), true);
  assert.equal(CollectionStatus.isPlayable(CollectionStatus.explored(2)), true);
  assert.equal(CollectionStatus.isPlayable(CollectionStatus.mastered()), true);
  assert.ok(CollectionStatus.equals(CollectionStatus.hidden(2), { kind: 'hidden', more: 2 }));
  assert.ok(!CollectionStatus.equals(CollectionStatus.hidden(2), CollectionStatus.hidden(1)));
  assert.deepEqual(PackProgress(), { total: 0, found: 0, explored: 0, stars: 0, mastered: 0, open: false });
});

test('a fresh profile: First Dig and the showcase open, the chain and every pack locked', () => {
  const app = freshApp();
  const G = GeneratedLevels;
  assert.deepEqual(app.status(G.firstDig), { kind: 'found', moves: 0 });
  assert.deepEqual(app.status(G.sunflower), { kind: 'found', moves: 0 });
  assert.deepEqual(app.status(G.koiPond), { kind: 'packLocked', label: 'First Dig' });
  assert.deepEqual(app.status(G.gardenBalloon), { kind: 'packLocked', label: 'First Dig' });
  assert.deepEqual(app.status(G.natFlamingo), { kind: 'packLocked', label: 'any Garden mosaic' });
  assert.equal(app.unlockRequirement(G.masterTiger), 'any Challenge mosaic');
  assert.equal(app.unlockRequirement(G.firstDig), null);
  assert.equal(app.nextUp.id, 'firstDig');
  const playable = LevelCatalog.builtIn.filter(l => app.isPlayable(l)).map(l => l.id);
  assert.deepEqual(playable, ['firstDig', 'sunflower']);
  const pp = app.packProgress(LevelCatalog.garden);
  assert.deepEqual(pp, { total: 8, found: 0, explored: 0, stars: 0, mastered: 0, open: false });
});

test('found limit: the first three when a pack opens, one more per finished mosaic; saved games stay found', () => {
  const app = freshApp();
  const G = GeneratedLevels;
  app.recordCompletion('firstDig', 100, 0, 'classic');
  const garden = LevelCatalog.garden;
  assert.equal(app.foundLimit('garden'), 3);
  assert.deepEqual(garden.map(l => app.status(l)), [
    CollectionStatus.found(0), CollectionStatus.found(0), CollectionStatus.found(0),
    CollectionStatus.hidden(1), CollectionStatus.hidden(2), CollectionStatus.hidden(3),
    CollectionStatus.hidden(4), CollectionStatus.hidden(5),
  ]);
  // the challenge pack has four: three found, one hidden
  assert.deepEqual(LevelCatalog.challenge.map(l => app.isFound(l)), [true, true, true, false]);
  // finishing any found mosaic of the pack finds the next one
  app.recordCompletion('gardenToadstools', 200, 0, 'gentle');
  assert.equal(app.foundLimit('garden'), 4);
  assert.deepEqual(app.status(G.gardenTulips), CollectionStatus.found(0));
  assert.deepEqual(app.status(G.gardenSailboat), CollectionStatus.hidden(1));
  assert.deepEqual(app.status(G.gardenToadstools), CollectionStatus.explored(1));
  // a saved game keeps a mosaic found (and shows its sends, not its assists)
  SaveStore.saveGame(SaveGame({ levelID: 'gardenOwl', difficulty: 'classic', moves: [0, 1, 100, 0, 200], undos: 0, hints: 0, elapsed: 12 }));
  assert.deepEqual(app.status(G.gardenOwl), CollectionStatus.found(3));
  assert.deepEqual(app.status(G.gardenDesert), CollectionStatus.hidden(4), 'only finished mosaics raise the limit');
  // naturalist opens with any Garden mosaic, with its own first three found
  assert.deepEqual(LevelCatalog.naturalist.map(l => app.status(l).kind),
    ['found', 'found', 'found', 'hidden', 'hidden', 'hidden', 'hidden', 'hidden']);
  // packs without a finished prerequisite stay locked
  assert.equal(app.status(G.craftQuilt).kind, 'packLocked');
  const pp = app.packProgress(garden);
  assert.deepEqual(pp, { total: 8, found: 5, explored: 1, stars: 1, mastered: 0, open: true });
});

test('unlock all: every mosaic playable; photo levels are always found and unlocked', () => {
  const app = freshApp();
  app.settings.unlockAll = true;
  assert.ok(LevelCatalog.builtIn.every(l => app.isPlayable(l)));
  assert.equal(app.status(GeneratedLevels.masterOctopus).kind, 'found');
  app.settings.unlockAll = false;
  assert.equal(app.status(GeneratedLevels.masterOctopus).kind, 'packLocked');
  const photo = new LevelDefinition({ id: 'photo-1', title: 'P', subtitle: '', art: ['a'], palette: GeneratedPalette.builtIn,
    tunnels: [[TeamSpec(0, 1)]], chambersGentle: 1, chambersClassic: 1, chambersExpert: 1, solution: [0], isPhoto: true });
  assert.ok(app.isUnlocked(photo) && app.isFound(photo) && app.isPlayable(photo));
});

test('stars and mastered: hardest difficulty finished; mastered needs Expert with a harder option', () => {
  const app = freshApp();
  assert.equal(app.stars('koiPond'), 0);
  app.recordCompletion('koiPond', 300, 1, 'gentle');
  assert.equal(app.stars('koiPond'), 1);
  app.recordCompletion('koiPond', 250, 1, 'classic');
  assert.equal(app.stars('koiPond'), 2);
  app.recordCompletion('koiPond', 200, 1, 'gentle');
  assert.equal(app.stars('koiPond'), 2, 'a later Gentle finish keeps two stars');
  assert.equal(app.isMastered('koiPond'), false);
  app.recordCompletion('koiPond', 280, 0, 'expert', 0);
  assert.equal(app.stars('koiPond'), 3);
  assert.equal(app.isMastered('koiPond'), false, 'Expert without harder options is not mastered');
  // as in Swift, the lock is checked first: finished but still behind First Dig shows locked
  assert.deepEqual(app.status(GeneratedLevels.koiPond), CollectionStatus.packLocked('First Dig'));
  app.recordCompletion('firstDig', 100, 0, 'gentle');
  assert.deepEqual(app.status(GeneratedLevels.koiPond), CollectionStatus.explored(3));
  app.recordCompletion('koiPond', 290, 0, 'expert', 2);
  assert.ok(app.isMastered('koiPond'));
  assert.deepEqual(app.status(GeneratedLevels.koiPond), CollectionStatus.mastered());
  // records from older builds (no bestByDifficulty) count their difficulty only
  SaveStore.saveProgress({ peacockFan: { bestSeconds: 10, fewestUndos: 0, difficulty: 'gentle', completions: 1 } });
  const old = new AppModel();
  assert.equal(old.stars('peacockFan'), 1);
  assert.equal(old.isMastered('peacockFan'), false);
});

test('status filter and Home filter', () => {
  const app = freshApp();
  const G = GeneratedLevels;
  app.recordCompletion('firstDig', 100, 0, 'expert', 1);   // mastered
  app.recordCompletion('koiPond', 100, 0, 'classic');      // explored, can go harder
  const pick = () => [G.firstDig, G.koiPond, G.peacockFan, G.gardenOwl].filter(l => app.passesStatus(l)).map(l => l.id);
  const want = {
    all: ['firstDig', 'koiPond', 'peacockFan', 'gardenOwl'],
    toExplore: ['peacockFan'],
    explored: ['firstDig', 'koiPond'],
    goHarder: ['koiPond'],
    mastered: ['firstDig'],
  };
  for (const f of StatusFilter.allCases) {
    app.settings.statusFilter = f;
    assert.deepEqual(pick(), want[f], f);
  }
  app.settings.statusFilter = 'all';
  // rating filter on the chosen difficulty (First Dig: Relaxed on Classic, Hard on Expert)
  app.settings.ratingFilter = 'easy';
  app.settings.difficulty = 'classic';
  assert.equal(app.passesFilter(G.firstDig), true);
  app.settings.difficulty = 'expert';
  assert.equal(app.passesFilter(G.firstDig), false);
  app.settings.ratingFilter = 'hard';
  assert.equal(app.passesFilter(G.firstDig), true);
  app.settings.ratingFilter = 'all';
  const noStats = new LevelDefinition({ id: 'pattern-1', title: 'P', subtitle: '', art: ['a'], palette: GeneratedPalette.builtIn,
    tunnels: [[TeamSpec(0, 1)]], chambersGentle: 1, chambersClassic: 1, chambersExpert: 1, solution: [0], isPhoto: true });
  assert.equal(app.passesFilter(noStats), true);
  app.settings.ratingFilter = 'medium';
  assert.equal(app.passesFilter(noStats), false, 'unmeasured levels are hidden by a rating filter');
});

test('next up walks the packs in Home order; next mosaic prefers the same pack', () => {
  const app = freshApp();
  assert.equal(app.nextUp.id, 'firstDig');
  app.recordCompletion('firstDig', 100, 0, 'classic');
  assert.equal(app.nextUp.id, 'koiPond');
  assert.equal(app.nextLevel('firstDig').id, 'koiPond');
  assert.equal(app.nextLevel('gardenBalloon').id, 'gardenLighthouse');
  assert.equal(app.nextLevel('gardenToadstools').id, 'koiPond', 'nothing playable after it in Garden: next up');
  app.settings.unlockAll = true;
  for (const l of LevelCatalog.builtIn) app.recordCompletion(l.id, 10, 0, 'gentle');
  assert.equal(app.nextUp, null);
  assert.equal(app.nextLevel('firstDig'), null);
});
