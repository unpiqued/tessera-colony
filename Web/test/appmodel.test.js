// AppModel.swift (non-UI) and SaveStore.swift: recordCompletion → CompletionNews, saved games,
// settings through an injected storage backend (Swift keys and record shapes, tolerant decoding and
// migrations), high scores, photo/pattern records, hooks and subscribe() notifications.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { setLevelData } from '../src/core/levelData.js';
import { LevelCatalog, GeneratedLevels, GeneratedPalette, LevelDefinition, LevelPalette, DifficultyStats, TeamSpec } from '../src/core/level.js';
import { HighScoreEntry } from '../src/core/scoring.js';
import { VersusRules } from '../src/core/versus.js';
import {
  SaveStore, SaveGame, CompletionRecord, CompletionNews, AppSettings, PhotoLevelRecord, PhotoLibrary,
  STATUS_FILTER_VALUES,
} from '../src/core/saveStore.js';
import { StatusFilter } from '../src/core/collection.js';
import { AppModel } from '../src/core/appModel.js';

setLevelData(readFileSync(new URL('../data/levels.json', import.meta.url), 'utf8'));

/** A fake backend that records every call (what the integrator's localStorage wrapper would do). */
function fakeBackend(initial = {}) {
  const map = new Map(Object.entries(initial));
  const log = [];
  return {
    map, log,
    getItem(k) { log.push(['get', k]); return map.has(k) ? map.get(k) : null; },
    setItem(k, v) { log.push(['set', k]); map.set(k, v); },
    removeItem(k) { log.push(['remove', k]); map.delete(k); },
  };
}
const flush = () => new Promise(r => setTimeout(r, 0));
const stored = (b, k) => JSON.parse(b.map.get(k));
const G = () => GeneratedLevels;

function smallLevel(id, extra = {}) {
  return new LevelDefinition({
    id, title: `Mosaic ${id}`, subtitle: 'test', art: ['aab', 'b.a'], palette: new LevelPalette(['A', 'B'], [[1, 2, 3, 4], [5, 6, 7, 8]]),
    tunnels: [[TeamSpec(0, 3)], [TeamSpec(1, 2)]], chambersGentle: 3, chambersClassic: 2, chambersExpert: 1, solution: [0, 1],
    isPhoto: true, ...extra,
  });
}

test('storage keys and the default in-memory backend', () => {
  assert.deepEqual(
    [SaveStore.keys.settingsKey, SaveStore.keys.progressKey, SaveStore.keys.highScoreKey, SaveStore.keys.gameKey('koiPond'),
      SaveStore.keys.photoKey('photo-1'), SaveStore.keys.photoIndexKey],
    ['tessera.settings.v2', 'tessera.progress.v1', 'tessera.highscores.v1', 'tessera.save.v3.koiPond',
      'PhotoMosaics/photo-1.json', 'PhotoMosaics/index.json']);
  SaveStore.setBackend(SaveStore.memoryBackend());
  SaveStore.saveGame(SaveGame({ levelID: 'a', difficulty: 'gentle', moves: [0], undos: 0, hints: 0, elapsed: 1 }));
  assert.ok(SaveStore.backend.map.has('tessera.save.v3.a'));
  assert.throws(() => SaveStore.setBackend({ getItem() {} }));
  assert.deepEqual([...STATUS_FILTER_VALUES], [...StatusFilter.allCases]);
});

test('AppSettings: every field and default', () => {
  assert.deepEqual(AppSettings(), {
    difficulty: 'classic', antSpeed: 1, detailedAnts: true, coachSeen: [], hasLaunchedBefore: false, photoDetail: 'fine',
    groundColor: GeneratedPalette.soil, unlockAll: false, soundOn: true, soundVolume: 0.8, tileClicks: true,
    actionSounds: true, goalSounds: true, pathStyle: 'randomTeam', pathStyleVersion: 2, soundInSilentMode: true,
    versusRules: VersusRules(), versusLevelID: 'firstDig', playerName: '', lastModifiers: [], ratingFilter: 'all',
    statusFilter: 'all', versusRulesVersion: 2,
  });
  assert.deepEqual([...AppSettings.keys], Object.keys(AppSettings()));
});

test('settings round-trip through a fake backend; every write saves (Swift didSet) and re-applies sound', () => {
  const b = fakeBackend();
  SaveStore.setBackend(b);
  const configured = [];
  const app = new AppModel({ soundBoard: { configure: (...a) => configured.push(a) } });
  assert.deepEqual(configured, [[true, 0.8, true, true, true, true]], 'sound applied at launch');
  app.settings.antSpeed = 4;
  app.settings.soundVolume = 0.25;
  app.settings.coachSeen.push('tapTeam');
  app.settings.versusRules.layout = 'shared';
  app.settings.lastModifiers = ['noHints'];
  app.settings.groundColor = 0x123456;
  const s = stored(b, 'tessera.settings.v2');
  assert.equal(s.antSpeed, 4);
  assert.deepEqual(s.coachSeen, ['tapTeam']);
  assert.equal(s.versusRules.layout, 'shared');
  assert.deepEqual(s.lastModifiers, ['noHints']);
  assert.deepEqual(Object.keys(s), [...AppSettings.keys], 'Swift field order');
  assert.deepEqual(configured.at(-1), [true, 0.25, true, true, true, true]);
  // values are copied in (Swift value semantics)
  const rules = VersusRules({ picking: 'front' });
  app.settings.versusRules = rules;
  rules.picking = 'reach3';
  assert.equal(app.settings.versusRules.picking, 'front');
  // a new model reads them back
  const again = new AppModel();
  assert.deepEqual(AppSettings.copy(again.settings), AppSettings.copy(app.settings));
  assert.equal(again.settings.groundColor, 0x123456);
  // assigning a whole settings value
  again.settings = { ...AppSettings(), difficulty: 'expert' };
  assert.equal(stored(b, 'tessera.settings.v2').difficulty, 'expert');
  assert.equal(JSON.stringify(again.settings), JSON.stringify({ ...AppSettings(), difficulty: 'expert' }));
});

test('settings decoding is tolerant, with the pathStyle and versusRules migrations', () => {
  const dec = AppSettings.decode;
  // missing everything → defaults (old versions migrate to the new defaults)
  assert.deepEqual(dec({}), AppSettings());
  // a bad value keeps that field's default only
  const s = dec({ difficulty: 'impossible', antSpeed: '2', unlockAll: 1, soundVolume: 0.3, coachSeen: ['a', 3],
    lastModifiers: ['noHints', 'bogus'], groundColor: -1, playerName: 'Ana', ratingFilter: 'hard', statusFilter: 'nope',
    pathStyle: 'curious', pathStyleVersion: 2, versusRulesVersion: 2, versusRules: { layout: 'shared' }, photoDetail: 'veryFine' });
  assert.equal(s.difficulty, 'classic');
  assert.equal(s.antSpeed, 1);
  assert.equal(s.unlockAll, false);
  assert.equal(s.soundVolume, 0.3);
  assert.deepEqual(s.coachSeen, []);
  assert.deepEqual(s.lastModifiers, []);
  assert.equal(s.groundColor, GeneratedPalette.soil);
  assert.equal(s.playerName, 'Ana');
  assert.equal(s.ratingFilter, 'hard');
  assert.equal(s.statusFilter, 'all');
  assert.equal(s.pathStyle, 'curious');
  assert.equal(s.photoDetail, 'veryFine');
  assert.deepEqual(s.versusRules, VersusRules(), 'an incomplete versusRules record resets to the defaults');
  // older builds: Natural paths → Random per team, once; No colour twice → Any colour, once
  const old = dec({ pathStyle: 'natural', versusRules: { ...VersusRules(), colour: 'alternate', layout: 'shared' } });
  assert.equal(old.pathStyle, 'randomTeam');
  assert.equal(old.pathStyleVersion, 2);
  assert.equal(old.versusRules.colour, 'any');
  assert.equal(old.versusRules.layout, 'shared');
  assert.equal(old.versusRulesVersion, 2);
  const kept = dec({ pathStyle: 'natural', pathStyleVersion: 2, versusRules: { ...VersusRules(), colour: 'alternate' }, versusRulesVersion: 2 });
  assert.equal(kept.pathStyle, 'natural', 'a chosen Natural style is kept once migrated');
  assert.equal(kept.versusRules.colour, 'alternate');
  // corrupt storage or a failing backend never throws
  SaveStore.setBackend(fakeBackend({ 'tessera.settings.v2': '{not json' }));
  assert.deepEqual(SaveStore.loadSettings(), AppSettings());
  SaveStore.setBackend({ getItem() { throw new Error('denied'); }, setItem() { throw new Error('full'); }, removeItem() {} });
  const app = new AppModel();
  app.settings.antSpeed = 3;
  assert.equal(app.settings.antSpeed, 3);
  assert.equal(SaveStore.lastError.message, 'full');
  assert.equal(SaveStore.loadGame('firstDig'), null);
});

test('recordCompletion: first clear unlocks the chain and finds the first three of each pack First Dig opens', () => {
  SaveStore.setBackend(SaveStore.memoryBackend());
  const app = new AppModel();
  const news = app.recordCompletion('firstDig', 120.25, 3, 'classic');
  const firstDigPacks = ['challenge', 'garden', 'wild', 'gallery', 'ancient', 'epics', 'tales', 'halloween', 'winter'];
  const want = LevelCatalog.builtIn.filter(l => l.id === 'koiPond'
    || (firstDigPacks.includes(LevelCatalog.packOfLevel[l.id]) && LevelCatalog.pack(LevelCatalog.packOfLevel[l.id]).indexOf(l) < 3))
    .map(l => l.title);
  assert.equal(want.length, 1 + 9 * 3);
  assert.deepEqual(news, CompletionNews({ newBest: false, firstClear: true, unlocked: want, stars: 2, newStar: true, mastered: false }));
  assert.deepEqual(news.unlocked.slice(0, 5), ['Koi Pond', 'Nesting Rings', 'Basket Weave', 'Labyrinth', 'Hot-Air Balloon']);
  assert.deepEqual(app.progress.firstDig, CompletionRecord({ bestSeconds: 120.25, fewestUndos: 3, difficulty: 'classic',
    completions: 1, bestByDifficulty: { classic: 120.25 } }));
  // stored in the Swift shape (nil optionals left out)
  assert.deepEqual(JSON.parse(SaveStore.backend.map.get('tessera.progress.v1')),
    { firstDig: { bestSeconds: 120.25, fewestUndos: 3, difficulty: 'classic', completions: 1, bestByDifficulty: { classic: 120.25 } } });
});

test('recordCompletion: new best needs half a second on the same difficulty; stars, mastered and record rules', () => {
  SaveStore.setBackend(SaveStore.memoryBackend());
  const app = new AppModel();
  app.recordCompletion('firstDig', 100, 5, 'classic');
  let n = app.recordCompletion('firstDig', 99.6, 6, 'classic');
  assert.equal(n.newBest, false, '0.4 s faster is not a new best');
  assert.equal(n.firstClear, false);
  assert.deepEqual(n.unlocked, []);
  assert.equal(app.progress.firstDig.bestByDifficulty.classic, 99.6);
  n = app.recordCompletion('firstDig', 99.0, 1, 'classic');
  assert.equal(n.newBest, true);
  assert.equal(n.newStar, false);
  n = app.recordCompletion('firstDig', 50, 9, 'gentle');
  assert.equal(n.newBest, false, 'no earlier time on Gentle');
  assert.equal(n.stars, 2);
  assert.equal(app.progress.firstDig.difficulty, 'classic', 'a Gentle finish does not lower the record');
  n = app.recordCompletion('firstDig', 300, 0, 'expert', 0);
  assert.deepEqual([n.stars, n.newStar, n.mastered], [3, true, false]);
  n = app.recordCompletion('firstDig', 310, 0, 'expert', 2);
  assert.deepEqual([n.stars, n.newStar, n.mastered], [3, false, true]);
  n = app.recordCompletion('firstDig', 305, 0, 'expert', 1);
  assert.equal(n.mastered, false, 'mastered only the first time');
  n = app.recordCompletion('firstDig', 90, 0, 'classic');
  const r = app.progress.firstDig;
  assert.deepEqual([r.bestSeconds, r.fewestUndos, r.completions, r.difficulty, r.expertModifiers],
    [50, 0, 8, 'expert', 2], 'a Classic finish after Expert keeps Expert');
  assert.deepEqual(r.bestByDifficulty, { classic: 90, gentle: 50, expert: 300 });
  // gentle → classic upgrades the record's difficulty
  app.recordCompletion('sunflower', 10, 0, 'gentle');
  app.recordCompletion('sunflower', 10, 0, 'classic');
  assert.equal(app.progress.sunflower.difficulty, 'classic');
  // the record survives a relaunch
  assert.deepEqual(new AppModel().progress.firstDig, r);
});

test('saved games: save, load, has, clear; play resumes or starts fresh; goHome saves the controller', () => {
  const b = fakeBackend();
  SaveStore.setBackend(b);
  const made = [];
  const app = new AppModel({
    makeGameController: (level, difficulty, modifiers, model, resume) => {
      const c = { level, difficulty, modifiers, model, resume, saves: 0, save() { this.saves += 1; } };
      made.push(c);
      return c;
    },
  });
  const fd = G().firstDig;
  const g = SaveGame({ levelID: 'firstDig', difficulty: 'expert', moves: [0, 1, 100, 1, 200], undos: 2, hints: 1,
    elapsed: 42.5, modifiers: ['noHints', 'hiddenQueue'] });
  SaveStore.saveGame(g);
  assert.deepEqual(stored(b, 'tessera.save.v3.firstDig'), { version: 1, levelID: 'firstDig', difficulty: 'expert',
    moves: [0, 1, 100, 1, 200], undos: 2, hints: 1, elapsed: 42.5, modifiers: ['noHints', 'hiddenQueue'] });
  assert.ok(SaveStore.hasGame('firstDig'));
  assert.deepEqual(SaveStore.loadGame('firstDig'), g);
  assert.deepEqual(app.savedGame(fd), g);
  assert.equal(app.savedMoves(fd), 3);
  assert.deepEqual(app.status(fd), { kind: 'found', moves: 3 });
  // resume: the save's own difficulty and options
  app.play(fd, false);
  assert.equal(made[0].difficulty, 'expert');
  assert.deepEqual([...made[0].modifiers].sort(), ['hiddenQueue', 'noHints']);
  assert.deepEqual(made[0].resume, g);
  assert.equal(made[0].model, app);
  assert.equal(app.current, made[0]);
  assert.equal(app.settings.hasLaunchedBefore, true);
  assert.equal(app.settings.difficulty, 'classic', 'resuming does not change the chosen difficulty');
  app.goHome();
  assert.equal(made[0].saves, 1);
  assert.equal(app.current, null);
  // fresh with a choice: clears the save and remembers the choice (sorted options)
  app.play(fd, true, 'gentle', new Set(['noRepeatColour', 'noScout']));
  assert.equal(SaveStore.hasGame('firstDig'), false);
  assert.equal(made[1].resume, null);
  assert.equal(made[1].difficulty, 'gentle');
  assert.equal(app.settings.difficulty, 'gentle');
  assert.deepEqual([...app.settings.lastModifiers], ['noScout', 'noRepeatColour']);
  // fresh without a choice: the last choice
  app.play(fd, true);
  assert.equal(made[2].difficulty, 'gentle');
  assert.deepEqual([...made[2].modifiers], ['noScout', 'noRepeatColour']);
  // an old save without modifiers
  SaveStore.saveGame(SaveGame({ levelID: 'koiPond', difficulty: 'classic', moves: [0], undos: 0, hints: 0, elapsed: 1 }));
  assert.equal('modifiers' in stored(b, 'tessera.save.v3.koiPond'), false);
  app.play(G().koiPond, false);
  assert.deepEqual([...made[3].modifiers], []);
  // invalid saves are ignored
  b.map.set('tessera.save.v3.peacockFan', JSON.stringify({ levelID: 'peacockFan', difficulty: 'classic', moves: [0] }));
  assert.equal(SaveStore.loadGame('peacockFan'), null);
  assert.equal(SaveStore.hasGame('peacockFan'), true, 'hasGame does not decode (as in Swift)');
  SaveStore.clearGame('koiPond');
  assert.equal(SaveStore.loadGame('koiPond'), null);
  // without a controller factory, current is a plain description
  const bare = new AppModel();
  bare.play(fd, true, 'expert');
  assert.deepEqual(Object.keys(bare.current), ['level', 'difficulty', 'modifiers', 'resume']);
  assert.equal(bare.current.difficulty, 'expert');
});

test('two-player matches through the controller hook', () => {
  SaveStore.setBackend(SaveStore.memoryBackend());
  let saved = 0;
  const app = new AppModel({
    makeGameController: () => ({ save() { saved += 1; } }),
    makeVersusController: (level, rules, model) => ({ level, rules, model }),
    flightRecorder: { ended: 0, end() { this.ended += 1; } },
  });
  app.play(G().firstDig, true);
  app.startVersus(G().koiPond, VersusRules({ layout: 'shared' }));
  assert.equal(saved, 1);
  assert.equal(app.current, null);
  assert.equal(app.versus.level.id, 'koiPond');
  assert.equal(app.versus.rules.layout, 'shared');
  assert.equal(app.hooks.flightRecorder.ended, 1);
  app.endVersus();
  assert.equal(app.versus, null);
});

test('subscribe: one batched notification per tick, after every kind of mutation; unsubscribe', async () => {
  SaveStore.setBackend(SaveStore.memoryBackend());
  const app = new AppModel();
  const calls = [];
  const off = app.subscribe(m => calls.push(m));
  app.settings.antSpeed = 2;
  app.settings.coachSeen.push('scout');
  app.recordCompletion('firstDig', 10, 0, 'classic');
  assert.equal(calls.length, 0, 'notifications are queued');
  await flush();
  assert.deepEqual(calls, [app]);
  app.saveHighScore('solo', 'firstDig', HighScoreEntry({ name: 'A', score: 10, seconds: 5, date: 1, difficulty: 'classic' }));
  await flush();
  assert.equal(calls.length, 2);
  app.photoMessage = 'hello';
  await flush();
  assert.equal(calls.length, 3);
  app.markCoachSeen('jam');
  await flush();
  assert.equal(calls.length, 4);
  for (const f of [() => app.clearHighScores(), () => app.goHome(), () => app.endVersus(), () => app.dismissCrashReport(),
    () => app.deletePhotoLevel('none'), () => app.resetEverything()]) {
    f();
    await flush();
  }
  assert.equal(calls.length, 10);
  const second = [];
  const off2 = app.subscribe(() => second.push(1));
  off();
  app.settings.unlockAll = true;
  await flush();
  assert.equal(calls.length, 10);
  assert.equal(second.length, 1);
  off2();
});

test('markCoachSeen adds a step once', () => {
  SaveStore.setBackend(SaveStore.memoryBackend());
  const app = new AppModel();
  app.markCoachSeen('tapTeam');
  app.markCoachSeen('tapTeam');
  app.markCoachSeen('scout');
  assert.deepEqual([...app.settings.coachSeen], ['tapTeam', 'scout']);
  assert.deepEqual(new AppModel().settings.coachSeen.slice(), ['tapTeam', 'scout']);
});

test('high scores: names cleaned, player name remembered, places, persistence, clearing', () => {
  const b = fakeBackend();
  SaveStore.setBackend(b);
  const app = new AppModel();
  const e = (name, score, seconds) => HighScoreEntry({ name, score, seconds, date: Date.now(), difficulty: 'classic', modifiers: ['noHints'] });
  assert.equal(app.highScoreRank('solo', 'firstDig', 100, 60), 1);
  assert.equal(app.highScoreRank('solo', 'firstDig', 0, 60), null);
  assert.equal(app.saveHighScore('solo', 'firstDig', e('  Ana  ', 100, 60)), 1);
  assert.equal(app.settings.playerName, 'Ana');
  assert.equal(app.saveHighScore('solo', 'firstDig', e('', 200, 60)), 1);
  assert.equal(app.settings.playerName, 'Player');
  assert.deepEqual(app.topScores('solo', 'firstDig').map(x => [x.name, x.score]), [['Player', 200], ['Ana', 100]]);
  assert.deepEqual(app.topScores('versus', 'firstDig'), []);
  assert.equal(app.highScoreRank('solo', 'firstDig', 150, 1), 2);
  const raw = stored(b, 'tessera.highscores.v1');
  assert.deepEqual(Object.keys(raw), ['solo', 'versus']);
  assert.equal(raw.solo.firstDig.length, 2);
  assert.deepEqual(new AppModel().topScores('solo', 'firstDig'), app.topScores('solo', 'firstDig'));
  app.clearHighScores();
  assert.ok(app.highScores.isEmpty);
  assert.ok(new AppModel().highScores.isEmpty);
});

test('resetEverything removes settings, progress, high scores and saved games, then saves default settings', () => {
  const b = fakeBackend();
  SaveStore.setBackend(b);
  const app = new AppModel();
  app.settings.difficulty = 'expert';
  app.recordCompletion('firstDig', 10, 0, 'classic');
  app.saveHighScore('solo', 'firstDig', HighScoreEntry({ name: 'A', score: 10, seconds: 5, date: 1, difficulty: 'classic' }));
  SaveStore.saveGame(SaveGame({ levelID: 'koiPond', difficulty: 'classic', moves: [0], undos: 0, hints: 0, elapsed: 1 }));
  app.resetEverything();
  assert.equal(b.map.has('tessera.progress.v1'), false);
  assert.equal(b.map.has('tessera.highscores.v1'), false);
  assert.equal(b.map.has('tessera.save.v3.koiPond'), false);
  assert.deepEqual(stored(b, 'tessera.settings.v2'), AppSettings(), 'Swift: settings = AppSettings() saves again in didSet');
  assert.deepEqual(Object.keys(app.progress), []);
  assert.ok(app.highScores.isEmpty);
  assert.equal(app.settings.difficulty, 'classic');
});

test('PhotoLevelRecord: LevelDefinition ↔ record, JSON shape, PhotoLibrary storage newest first', () => {
  const b = fakeBackend();
  SaveStore.setBackend(b);
  const level = smallLevel('photo-abc');
  const rec = new PhotoLevelRecord(level, 'coarse', new Date(5000));
  assert.equal(rec.created, 5000);
  const json = JSON.parse(JSON.stringify(rec));
  assert.deepEqual(Object.keys(json), ['id', 'title', 'created', 'detail', 'art', 'palette', 'tunnels', 'solution',
    'chambersGentle', 'chambersClassic', 'chambersExpert', 'subtitle']);
  assert.deepEqual(json.tunnels, [[{ family: 0, quota: 3 }], [{ family: 1, quota: 2 }]]);
  assert.deepEqual(json.palette, { names: ['A', 'B'], tones: [[1, 2, 3, 4], [5, 6, 7, 8]] });
  const back = PhotoLevelRecord.decode(json);
  const l = back.level;
  assert.ok(l instanceof LevelDefinition && l.palette instanceof LevelPalette);
  assert.equal(l.isPhoto, true);
  assert.equal(l.goldenClaimsHash, 0n);
  assert.deepEqual(l.goldenClaimsPerMove, []);
  assert.equal(l.pack, 'main');
  assert.equal(l.shippedStats, null);
  for (const k of ['id', 'title', 'subtitle', 'art', 'tunnels', 'solution', 'chambersGentle', 'chambersClassic', 'chambersExpert']) {
    assert.deepEqual(l[k], level[k], k);
  }
  assert.equal(l.tileCount, 5);
  assert.equal(PhotoLevelRecord.decode({ ...json, detail: 'huge' }), null);
  PhotoLibrary.save(rec);
  PhotoLibrary.save(new PhotoLevelRecord(smallLevel('pattern-1'), 'fine', 9000));
  PhotoLibrary.save(rec);
  assert.deepEqual(stored(b, 'PhotoMosaics/index.json'), ['photo-abc', 'pattern-1']);
  assert.deepEqual(stored(b, 'PhotoMosaics/photo-abc.json'), json);
  assert.deepEqual(PhotoLibrary.loadAll().map(r => r.id), ['pattern-1', 'photo-abc']);
  const app = new AppModel();
  assert.deepEqual(app.photoLevels.map(r => r.id), ['pattern-1', 'photo-abc']);
  assert.equal(app.allLevels.length, 195);
  assert.equal(app.allLevels.at(-1).id, 'photo-abc');
  // deleting removes the record, its saved game and its progress
  app.recordCompletion('photo-abc', 5, 0, 'classic');
  SaveStore.saveGame(SaveGame({ levelID: 'photo-abc', difficulty: 'classic', moves: [0], undos: 0, hints: 0, elapsed: 1 }));
  app.deletePhotoLevel('photo-abc');
  assert.deepEqual(app.photoLevels.map(r => r.id), ['pattern-1']);
  assert.equal(b.map.has('PhotoMosaics/photo-abc.json'), false);
  assert.equal(SaveStore.hasGame('photo-abc'), false);
  assert.equal(app.progress['photo-abc'], undefined);
  assert.deepEqual(PhotoLibrary.loadAll().map(r => r.id), ['pattern-1']);
});

test('pattern and photo mosaics through the builder hooks', async () => {
  SaveStore.setBackend(SaveStore.memoryBackend());
  const played = [];
  const seeds = [];
  const app = new AppModel({
    makeGameController: (level, difficulty) => { played.push([level.id, difficulty]); return { save() {} }; },
    buildPatternLevel: (seed, number) => { seeds.push(seed); return number === 1 ? smallLevel('pattern-7') : null; },
  });
  const p = app.createPatternLevel();
  assert.equal(app.photoBusy, true);
  assert.equal(await app.createPatternLevel(), null, 'busy: a second request is ignored');
  const level = await p;
  assert.equal(level.id, 'pattern-7');
  assert.equal(typeof seeds[0], 'bigint');
  assert.ok(seeds[0] >= 0n && seeds[0] <= 0xFFFFFFFFn);
  assert.equal(app.photoBusy, false);
  assert.deepEqual(app.photoLevels.map(r => [r.id, r.detail]), [['pattern-7', 'fine']]);
  assert.deepEqual(played, [['pattern-7', 'classic']]);
  assert.equal(await app.createPatternLevel(), null, 'the builder failed (number 2)');
  assert.equal(app.photoMessage, "The colony couldn't plan that pattern. Please tap New pattern again.");
  // photos: unreadable, a build failure, and a success with the chosen detail
  app.hooks.photoPixels = data => (data.byteLength > 2 ? { width: 1, height: 1, rgba: [0, 0, 0, 255] } : null);
  app.hooks.buildPhotoLevel = async (px, detail, seed, id, title) => {
    assert.equal(typeof seed, 'bigint');
    if (detail === 'coarse') return { kind: 'failure', error: { message: 'Only 3 coloured tiles are left.' } };
    return { kind: 'success', level: smallLevel(id, { title }) };
  };
  await app.importPhoto(new Uint8Array(2));
  assert.equal(app.photoMessage, "That image couldn't be read. Try another photo.");
  app.settings.photoDetail = 'coarse';
  await app.importPhoto(new Uint8Array(10));
  assert.equal(app.photoMessage, 'Only 3 coloured tiles are left.');
  app.settings.photoDetail = 'veryFine';
  const res = await app.importPhoto(new Uint8Array(10));
  assert.equal(res.kind, 'success');
  assert.equal(app.photoMessage, null);
  assert.match(app.photoLevels[0].id, /^photo-[0-9a-z]+$/);
  assert.equal(app.photoLevels[0].title, 'Photo mosaic 2');
  assert.equal(app.photoLevels[0].detail, 'veryFine');
  assert.equal(played.at(-1)[0], app.photoLevels[0].id);
  assert.equal(PhotoLibrary.loadAll().length, 2);
});

test('difficulty stats: shipped for built-ins, measured once through the hook for the others', async () => {
  SaveStore.setBackend(SaveStore.memoryBackend());
  let runs = 0;
  const app = new AppModel({ measureDifficulty: () => { runs += 1; return new DifficultyStats([1, 0.5, 0.1], [true, true, false]); } });
  assert.deepEqual(app.difficultyStats(G().firstDig), G().firstDig.shippedStats);
  const l = smallLevel('pattern-3');
  assert.equal(app.difficultyStats(l), null);
  const notes = [];
  app.subscribe(() => notes.push(1));
  app.measureIfNeeded(l);
  app.measureIfNeeded(l);
  app.measureIfNeeded(G().firstDig);
  await flush();
  assert.equal(runs, 1);
  assert.equal(app.difficultyStats(l).rating('expert').level, 5, 'careless 0.10 is not above 0.10: Fiendish');
  assert.ok(notes.length >= 1);
  app.measureIfNeeded(l);
  await flush();
  assert.equal(runs, 1);
});

test('thumbnails come from the hook and are cached per level', () => {
  SaveStore.setBackend(SaveStore.memoryBackend());
  let n = 0;
  const app = new AppModel({ thumbnail: level => ({ id: level.id, n: ++n }) });
  const a = app.thumbnail(G().firstDig);
  assert.equal(app.thumbnail(G().firstDig), a);
  assert.equal(n, 1);
  assert.equal(new AppModel().thumbnail(G().firstDig), null, 'no hook, no picture');
});

test('records decode strictly; progress with one bad record is dropped (as Swift decodes the whole dictionary)', () => {
  assert.equal(CompletionRecord.decode({ bestSeconds: 1, fewestUndos: 0, difficulty: 'classic' }), null);
  assert.deepEqual(CompletionRecord.decode({ bestSeconds: 1, fewestUndos: 0, difficulty: 'classic', completions: 2, bestByDifficulty: null }),
    CompletionRecord({ bestSeconds: 1, fewestUndos: 0, difficulty: 'classic', completions: 2 }));
  assert.equal(CompletionRecord.decode({ bestSeconds: 1, fewestUndos: 0, difficulty: 'classic', completions: 2, expertModifiers: 'x' }), null);
  SaveStore.setBackend(fakeBackend({ 'tessera.progress.v1': JSON.stringify({
    firstDig: { bestSeconds: 1, fewestUndos: 0, difficulty: 'classic', completions: 1 },
    koiPond: { bestSeconds: 1 },
  }) }));
  assert.deepEqual(Object.keys(SaveStore.loadProgress()), []);
  assert.equal(SaveGame.decode({ version: 1, levelID: 'a', difficulty: 'gentle', moves: [0], undos: 0, hints: 0, elapsed: 1, modifiers: ['x'] }), null);
});
