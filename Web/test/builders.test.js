// Builders: PatternLevelBuilder, PhotoLevelBuilder, LevelGenerator, DifficultyProbe, builder worker
// client (main-thread fallback). Expected values come from tools/make_builder_fixtures.py, which runs
// Tools/pattern.py, Tools/generate_levels.py (design_sequence / deal driven by Swift's SplitMix64),
// a Swift-faithful mirror of PhotoLevelBuilder on Tools/photo.py's maths, and a DifficultyProbe
// mirror on Tools/engine.py — on exactly the same input pixels (test/fixtures/photo_*.rgba.gz).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { gunzipSync } from 'node:zlib';
import { Board } from '../src/core/board.js';
import { Game } from '../src/core/engine.js';
import { SplitMix64 } from '../src/core/util.js';
import { LevelGenerator } from '../src/builders/levelGenerator.js';
import { PatternLevelBuilder, builtInPalette } from '../src/builders/patternLevelBuilder.js';
import {
  PhotoLevelBuilder, PhotoDetail, PhotoBuildError, targetSize, PHOTO_MAX_SIDE,
} from '../src/builders/photoLevelBuilder.js';
import { DifficultyProbe, chambers } from '../src/builders/difficultyProbe.js';
import { runBuild, createBuilder, createBuilderWorker, BuilderClient } from '../src/builders/builderWorker.js';

const fx = new URL('./fixtures/', import.meta.url);
const F = JSON.parse(readFileSync(new URL('builders.json', fx)));
const photoMeta = JSON.parse(readFileSync(new URL('photos.json', fx)));
const levelsData = JSON.parse(readFileSync(new URL('../data/levels.json', import.meta.url)));

const images = new Map();
function image(name) {
  if (!images.has(name)) {
    const { width, height } = photoMeta[name];
    const rgba = new Uint8Array(gunzipSync(readFileSync(new URL(`photo_${name}.rgba.gz`, fx))));
    assert.equal(rgba.length, width * height * 4);
    images.set(name, { width, height, rgba });
  }
  return images.get(name);
}

const tunnelsOf = list => list.map(t => t.map(s => (Array.isArray(s) ? { family: s[0], quota: s[1] } : s)));

/** Replays the designed solution on Expert slots with the JS Game. */
function solvesOnExpert(level) {
  const board = new Board(level.art);
  const g = new Game(level, board, level.chambersExpert);
  for (const q of level.solution) {
    if (!g.canDispatch(q)) return false;
    g.dispatch(q);
  }
  const quotas = level.tunnels.reduce((a, t) => a + t.reduce((b, s) => b + s.quota, 0), 0);
  return g.isWon && !g.isJammed && quotas === board.tileCount;
}

function assertLevelShape(lv) {
  for (const k of ['id', 'title', 'subtitle', 'art', 'palette', 'tunnels', 'chambersGentle', 'chambersClassic',
    'chambersExpert', 'solution', 'goldenClaimsPerMove', 'goldenClaimsHash', 'goldenFinalStateHash', 'isPhoto',
    'carelessWins', 'greedyWins', 'isChallenge', 'pack']) assert.ok(k in lv, `level has ${k}`);
  assert.equal(lv.goldenClaimsHash, 0n);
  assert.equal(lv.goldenFinalStateHash, 0n);
  assert.deepEqual(lv.goldenClaimsPerMove, []);
  assert.equal(lv.isPhoto, true);
  assert.equal(lv.isChallenge, false);
  assert.equal(lv.pack, 'main');
}

// MARK: - Pattern mosaics

test('builtInPalette equals GeneratedPalette.builtIn (data/levels.json)', () => {
  assert.deepEqual([...builtInPalette.names], levelsData.palette.names);
  assert.deepEqual(builtInPalette.tones.map(t => [...t]), levelsData.palette.tones);
});

test('Pattern: seed 1 draws goldenSeed1 (SelfTest section 4: <= 12 tiles may differ; here 0)', () => {
  const art = PatternLevelBuilder.rows(1);
  let diff = 0;
  art.forEach((row, y) => { for (let x = 0; x < row.length; x++) if (row[x] !== PatternLevelBuilder.goldenSeed1[y][x]) diff++; });
  assert.equal(art.length, PatternLevelBuilder.height);
  assert.equal(art[0].length, PatternLevelBuilder.width);
  assert.equal(diff, 0);
});

test('Pattern: all five layouts match the SelfTest colour counts', () => {
  const layoutGolden = [
    [1, 'Rosette', [460, 884, 188, 434, 24, 402]], [2, 'Ribbons', [222, 297, 460, 415, 328, 670]],
    [3, 'Starburst', [580, 44, 452, 673, 183, 460]], [4, 'Kaleidoscope', [288, 580, 460, 784, 228, 52]],
    [6, 'Fish scales', [706, 69, 618, 195, 460, 344]],
  ];
  for (const [seed, name, want] of layoutGolden) {
    const d = PatternLevelBuilder.design(seed);
    const counts = [0, 0, 0, 0, 0, 0];
    for (const row of d.rows) for (const ch of row) counts[((ch.charCodeAt(0) - 97) / 4) | 0] += 1;
    assert.equal(d.layout, name, `seed ${seed}`);
    assert.deepEqual(counts, want, `seed ${seed} colour counts`);
  }
});

for (const p of F.patterns) {
  test(`Pattern seed ${p.seed} (${p.layout}): rows = pattern.py, level = Swift build`, () => {
    const seed = BigInt(p.seed);
    const d = PatternLevelBuilder.design(seed);
    assert.equal(d.layout, p.layout);
    assert.deepEqual(d.rows, p.rows);
    const lv = PatternLevelBuilder.build(seed, 7);
    assert.ok(lv, 'built');
    assertLevelShape(lv);
    const want = p.level;
    for (const k of ['id', 'title', 'subtitle', 'art', 'solution', 'chambersGentle', 'chambersClassic', 'chambersExpert']) {
      assert.deepEqual(lv[k], want[k], k);
    }
    assert.deepEqual(lv.tunnels, want.tunnels);
    assert.deepEqual(lv.palette, builtInPalette);
    assert.ok(solvesOnExpert(lv), 'solution clears the board on Expert');
    if (p.probe) assert.deepEqual(DifficultyProbe.measure(lv), p.probe, 'DifficultyProbe = engine.py mirror');
  });
}

// MARK: - Level generator

const boardOf = name => new Board(levelsData.levels[name].art);
for (const g of F.generator) {
  test(`LevelGenerator on ${g.name}: designSequence / deal / verify / generate = generate_levels.py`, () => {
    const board = boardOf(g.name);
    for (const c of g.cases) {
      const rng = new SplitMix64(BigInt(c.seed));
      const seq = LevelGenerator.designSequence(board, rng, c.maxWait, c.minTeam, c.pWait);
      if (c.seq === null) { assert.equal(seq, null); continue; }
      assert.deepEqual(seq, tunnelsOf([c.seq])[0], `seq seed ${c.seed}`);
      const [tunnels, solution] = LevelGenerator.deal(seq, c.tunnelCount, rng);
      assert.deepEqual(tunnels, tunnelsOf(c.tunnels));
      assert.deepEqual(solution, c.solution);
      assert.equal(rng.next(), BigInt(c.nextRandom), 'same number of random draws');
      assert.equal(LevelGenerator.verify(board, tunnels, solution, c.maxWait), c.verify);
    }
    for (const { seed, plan } of g.generate) {
      const got = LevelGenerator.generate(board, BigInt(seed));
      if (plan === null) { assert.equal(got, null); continue; }
      assert.deepEqual(got.tunnels, tunnelsOf(plan.tunnels));
      assert.deepEqual(got.solution, plan.solution);
      assert.equal(got.maxChambersUsed, plan.maxChambersUsed);
    }
  });
}

test('LevelGenerator: a jammed or short solution fails verify', () => {
  const board = boardOf('firstDig');
  const plan = LevelGenerator.generate(board, 5n);
  assert.equal(LevelGenerator.verify(board, plan.tunnels, plan.solution.slice(0, -1), 1), null);
  assert.equal(LevelGenerator.verify(board, plan.tunnels, [...plan.solution, 0], 1), null);
});

// MARK: - Photo mosaics

test('PhotoDetail and PhotoBuildError helpers', () => {
  assert.deepEqual([...PhotoDetail.allCases], ['coarse', 'fine', 'veryFine']);
  assert.deepEqual(PhotoDetail.allCases.map(PhotoDetail.targetTiles), [1600, 3600, 6000]);
  assert.deepEqual(PhotoDetail.allCases.map(PhotoDetail.title), ['Chunky', 'Fine', 'Very fine']);
  assert.match(PhotoBuildError.message(PhotoBuildError.notEnoughColour(0)), /white or near-white/);
  assert.match(PhotoBuildError.message(PhotoBuildError.notEnoughColour(5)), /^Only 5 coloured tiles/);
  assert.match(PhotoBuildError.message(PhotoBuildError.generationFailed), /couldn't plan/);
  assert.match(PhotoBuildError.message(PhotoBuildError.unreadable), /couldn't be read/);
});

test('targetSize mirrors PhotoLibrary.pixels (long side <= 720, rounded, never upscaled)', () => {
  assert.equal(PHOTO_MAX_SIDE, 720);
  assert.deepEqual(targetSize(4032, 3024), { width: 720, height: 540, scale: 720 / 4032 });
  assert.deepEqual(targetSize(3024, 4032), { width: 540, height: 720, scale: 720 / 4032 });
  assert.deepEqual(targetSize(500, 400), { width: 500, height: 400, scale: 1 });
  assert.equal(targetSize(1001, 333).height, 240);        // 239.52 -> 240
  assert.equal(targetSize(1, 5000).width, 1);             // never below 1
  assert.equal(targetSize(1440, 1081).height, 541);       // 540.5 -> 541 (half away from zero)
});

test('gridSize: the largest grids the Swift code allows', () => {
  assert.deepEqual(PhotoLevelBuilder.gridSize(720, 720, 6000).slice(0, 2), [77, 78]);    // 6006 tiles
  assert.deepEqual(PhotoLevelBuilder.gridSize(720, 480, 6000).slice(0, 2), [90, 63]);    // aspect 1.5, gw clamped
  assert.deepEqual(PhotoLevelBuilder.gridSize(432, 720, 6000).slice(0, 2), [60, 100]);   // aspect 0.6
  assert.deepEqual(PhotoLevelBuilder.gridSize(2, 2000, 1600).slice(0, 2), [31, 52]);      // aspect clamped to 0.6
});

test('Photo: unreadable input is refused', () => {
  const tiny = { width: 1, height: 10, rgba: new Uint8Array(40) };
  assert.deepEqual(PhotoLevelBuilder.build(tiny, 'fine', 1n, 'x', 'X'), { kind: 'failure', error: { kind: 'unreadable' } });
  const short = { width: 10, height: 10, rgba: new Uint8Array(399) };
  assert.equal(PhotoLevelBuilder.build(short, 'fine', 1n, 'x', 'X').error.kind, 'unreadable');
  assert.equal(PhotoLevelBuilder.build(null, 'fine', 1n, 'x', 'X').error.kind, 'unreadable');
});

for (const c of F.photos) {
  test(`Photo ${c.name}: = Swift PhotoLevelBuilder (Python mirror on the same pixels)`, t => {
    const img = image(c.image);
    const id = `photo-${c.name}`, title = 'Photo mosaic 3';
    const r = PhotoLevelBuilder.build(img, c.detail, BigInt(c.seed), id, title);
    const [gw, gh] = PhotoLevelBuilder.gridSize(img.width, img.height, PhotoDetail.targetTiles(c.detail));
    assert.deepEqual([gw, gh], c.photo_py.grid, 'grid = photo.py grid_size');
    if (c.failure) {
      assert.deepEqual(r, { kind: 'failure', error: c.failure });
      assert.equal(c.photo_py.coloured, c.failure.colouredTiles ?? c.photo_py.coloured);
      return;
    }
    assert.equal(r.kind, 'success', r.error && PhotoBuildError.message(r.error));
    const lv = r.value;
    assertLevelShape(lv);
    const want = c.level;
    assert.equal(lv.id, id);
    assert.equal(lv.title, title);
    assert.equal(lv.subtitle, want.subtitle);
    assert.deepEqual(lv.art, want.art);
    assert.deepEqual(lv.palette, want.palette);
    assert.deepEqual(lv.tunnels, want.tunnels);
    assert.deepEqual(lv.solution, want.solution);
    for (const k of ['chambersGentle', 'chambersClassic', 'chambersExpert']) assert.equal(lv[k], want[k], k);
    const coloured = lv.art.join('').replace(/\./g, '').length;
    assert.equal(coloured, c.coloured);
    assert.equal(coloured, c.photo_py.coloured, 'white mask = photo.py');
    assert.ok(solvesOnExpert(lv), 'solution clears the board on Expert');
    // ImageData-shaped input ({ data: Uint8ClampedArray }) gives the same level
    const r2 = PhotoLevelBuilder.build({ width: img.width, height: img.height, data: new Uint8ClampedArray(img.rgba) },
      c.detail, BigInt(c.seed), id, title);
    assert.deepEqual(r2.value.art, lv.art);
    assert.deepEqual(r2.value.tunnels, lv.tunnels);
    if (c.probe) assert.deepEqual(DifficultyProbe.measure(lv), c.probe, 'DifficultyProbe = engine.py mirror');
    // How far the unmodified Tools/photo.py is from the Swift code on the same photo (reported only)
    if (c.photo_py.rows) {
      let diff = 0;
      c.photo_py.rows.forEach((row, y) => { for (let x = 0; x < row.length; x++) if (row[x] !== lv.art[y][x]) diff++; });
      t.diagnostic(`photo.py: ${c.photo_py.families} families vs Swift ${lv.palette.tones.length}; ${diff} of ${gw * gh} tiles differ`);
    }
  });
}

test('Photo: SelfTest synthetic flower — white background becomes open ground', () => {
  const r = PhotoLevelBuilder.build(image('flower'), PhotoDetail.fine, 7n, 'selftest-photo', 'Test');
  assert.equal(r.kind, 'success');
  const board = new Board(r.value.art);
  const empty = r.value.art.join('').split('.').length - 1;
  assert.ok(empty > board.tileCount);
});

test('Photo: colourName and uniquified', () => {
  assert.equal(PhotoLevelBuilder.colourName([80, 2, 3]), 'Silver');
  assert.equal(PhotoLevelBuilder.colourName([30, 2, 3]), 'Charcoal');
  // Lab hue angles: (40,120,220) 282° Blue; (30,60,200) 299.5° (L 33) Dark violet, as the Swift switch says
  assert.equal(PhotoLevelBuilder.colourName(PhotoLevelBuilder.lab(40, 120, 220)), 'Blue');
  assert.equal(PhotoLevelBuilder.colourName(PhotoLevelBuilder.lab(20, 60, 110)), 'Dark blue');
  assert.equal(PhotoLevelBuilder.colourName(PhotoLevelBuilder.lab(200, 230, 250)), 'Pale blue');
  assert.equal(PhotoLevelBuilder.colourName(PhotoLevelBuilder.lab(30, 60, 200)), 'Dark violet');
  assert.equal(PhotoLevelBuilder.colourName(PhotoLevelBuilder.lab(220, 50, 100)), 'Pink');
  assert.equal(PhotoLevelBuilder.colourName(PhotoLevelBuilder.lab(120, 70, 30)), 'Brown');
  assert.equal(PhotoLevelBuilder.colourName(PhotoLevelBuilder.lab(230, 200, 60)), 'Pale gold');
  assert.deepEqual(PhotoLevelBuilder.uniquified(['Red', 'Blue', 'Red', 'Red']), ['Red', 'Blue', 'Red 2', 'Red 3']);
  assert.equal(PhotoLevelBuilder.hexColor([254.5, 0.49, -3]), 0xFF0000);
  assert.equal(PhotoLevelBuilder.hexColor([12.5, 127.5, 300]), 0x0D80FF);
});

// MARK: - DifficultyProbe

test('DifficultyProbe: shape, chambers helper, trials parameter', () => {
  const lv = PatternLevelBuilder.build(4n, 1);
  assert.equal(chambers(lv, 'gentle'), lv.chambersGentle);
  assert.equal(chambers(lv, 'expert'), lv.chambersExpert);
  const s = DifficultyProbe.measure(lv, 3);
  assert.equal(s.careless.length, 3);
  assert.equal(s.greedy.length, 3);
  for (const v of s.careless) assert.ok(v === 0 || v === 1 / 3 || v === 2 / 3 || v === 1);
  for (const v of s.greedy) assert.equal(typeof v, 'boolean');
});

// MARK: - Worker wrapper (Node has no Web Worker: exercises the main-thread fallback)

test('runBuild: pattern, photo, probe; unknown kind throws', () => {
  const a = runBuild('pattern', { seed: 4n, number: 1, probe: true });
  assert.deepEqual(a.level, PatternLevelBuilder.build(4n, 1));
  assert.deepEqual(a.stats, F.patterns.find(p => p.seed === '4').probe);
  const fl = F.photos.find(p => p.name === 'flower-fine-7');
  const b = runBuild('photo', { image: image('flower'), detail: 'fine', seed: 7n, id: 'i', title: 'T', probe: true });
  assert.equal(b.result.kind, 'success');
  assert.deepEqual(b.result.value.art, fl.level.art);
  assert.deepEqual(b.stats, fl.probe);
  assert.deepEqual(runBuild('probe', { level: a.level }).stats, a.stats);
  assert.throws(() => runBuild('nope', {}), /unknown build kind/);
});

test('BuilderClient falls back to the main thread without Worker support', async () => {
  assert.equal(createBuilderWorker('self.postMessage({ready:true})'), null);   // no Worker in Node
  const builder = createBuilder();
  assert.equal(builder.mode, 'main');
  const { level, stats } = await builder.run('pattern', { seed: 12345, number: 2, probe: true });
  assert.equal(level.title, 'Pattern 2');
  assert.deepEqual(level.solution, F.patterns.find(p => p.seed === '12345').level.solution);
  assert.deepEqual(stats, F.patterns.find(p => p.seed === '12345').probe);
  const { stats: s2 } = await builder.run('probe', { level: { ...level, extra: () => 1 } });
  assert.deepEqual(s2, stats);
  await assert.rejects(builder.run('bad', {}), /unknown build kind/);
  builder.terminate();
  assert.equal(new BuilderClient(null).mode, 'main');
});

// MARK: - Timing (reported; see the report for the numbers on this machine)

test('timing: pattern level and the largest photo level, build + probe', t => {
  const ms = f => { const t0 = performance.now(); const v = f(); return [v, performance.now() - t0]; };
  const [pl, tPattern] = ms(() => PatternLevelBuilder.build(12345n, 1));
  const [, tPatternProbe] = ms(() => DifficultyProbe.measure(pl));
  const big = image('bokeh');
  const [r, tPhoto] = ms(() => PhotoLevelBuilder.build(big, 'veryFine', 99n, 'p', 'P'));
  assert.equal(new Board(r.value.art).tileCount, 6006);
  const [, tPhotoProbe] = ms(() => DifficultyProbe.measure(r.value));
  const line = `pattern build ${tPattern.toFixed(0)} ms + probe ${tPatternProbe.toFixed(0)} ms; `
    + `photo 720x720 veryFine (77x78 = 6006 tiles) build ${tPhoto.toFixed(0)} ms + probe ${tPhotoProbe.toFixed(0)} ms`;
  t.diagnostic(line);
  assert.ok(tPhoto + tPhotoProbe < 60000);
});
