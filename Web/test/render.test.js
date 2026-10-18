// Ant scheduler, path planner, ant geometry, leg kinematics and mosaic raster templates against
// the Python reference models (fixture: tools/make_render_fixtures.py → test/fixtures/render_fixture.json.gz).
// Trips must match exactly (times within 1e-9): depart, arrive, pickupEnd, home, route cells,
// pauses, lane and style, after sends at given times with every path style, prunes, undos and
// restored (complete-instantly) games.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { gunzipSync } from 'node:zlib';
import { Board } from '../src/core/board.js';
import { Game } from '../src/core/engine.js';
import { AntScheduler, AntGeometry } from '../src/render/antScheduler.js';
import { PathPlanner, PathStyle, PATH_STYLE_INFO } from '../src/render/pathPlanner.js';
import { AntRenderer } from '../src/render/antRenderer.js';
import { MosaicRaster, RGB } from '../src/render/mosaicRaster.js';
import { LevelPalette, GeneratedPalette } from '../src/render/palette.js';
import { hash32 } from '../src/core/util.js';

const data = JSON.parse(readFileSync(new URL('../data/levels.json', import.meta.url)));
const fixture = JSON.parse(gunzipSync(readFileSync(new URL('./fixtures/render_fixture.json.gz', import.meta.url))));
const palette = { names: data.palette.names, tones: data.palette.tones };
const levelOf = id => {
  const l = data.levels[id];
  return { ...l, tunnels: l.tunnels.map(q => q.map(([family, quota]) => ({ family, quota }))) };
};

const TOL = 1e-9;
const dec = v => (v === 'inf' ? Infinity : v === '-inf' ? -Infinity : v);
function near(a, b, what) {
  const e = dec(b);
  if (!Number.isFinite(e) || !Number.isFinite(a)) {
    assert.equal(a, e, what);
    return;
  }
  assert.ok(Math.abs(a - e) <= TOL, `${what}: ${a} vs ${e}`);
}

function checkTimes(sch, board, exp, what) {
  let k = 0;
  for (let i = 0; i < board.count; i++) {
    if (board.family[i] < 0) {
      assert.equal(sch.liftTime[i], -Infinity);
      continue;
    }
    near(sch.liftTime[i], exp.lift[k], `${what} liftTime[${i}]`);
    near(sch.homeTime[i], exp.home[k], `${what} homeTime[${i}]`);
    k += 1;
  }
  assert.equal(k, exp.lift.length);
}

function checkTrip(trip, e, board, what) {
  assert.equal(trip.id, e.id, `${what} id`);
  assert.equal(trip.move, e.move, `${what} move`);
  assert.equal(trip.team, e.team, `${what} team`);
  assert.equal(trip.family, e.family, `${what} family`);
  assert.equal(trip.tile, e.tile, `${what} tile`);
  assert.equal(trip.style, e.style, `${what} style`);
  assert.deepEqual(trip.path, e.path, `${what} route`);
  near(trip.depart, e.depart, `${what} depart`);
  near(trip.arrive, e.arrive, `${what} arrive`);
  near(trip.pickupEnd, e.pickupEnd, `${what} pickupEnd`);
  near(trip.home, e.home, `${what} home`);
  near(trip.lane, e.lane, `${what} lane`);
  assert.equal(trip.pauses.length, e.pauses.length, `${what} pauses`);
  trip.pauses.forEach((p, i) => {
    near(p.at, e.pauses[i][0], `${what} pause.at`);
    near(p.duration, e.pauses[i][1], `${what} pause.duration`);
  });
  assert.equal(trip.tone, board.tone[trip.tile]);
  assert.equal(trip.color, LevelPalette.tone(palette, trip.family, trip.tone));
}

const stats = { trips: 0, styled: 0, pauses: 0, fallbacks: 0, undos: 0, prunes: 0, geometry: 0 };

for (const sc of fixture.scenarios) {
  test(`scheduler: ${sc.level} · ${sc.style}`, () => {
    const level = levelOf(sc.level);
    const board = new Board(level.art);
    const game = new Game(level, board, sc.capacity);
    const sch = new AntScheduler(board, palette);
    sch.style = sc.style;
    for (const [n, op] of sc.ops.entries()) {
      const what = `${sc.level}/${sc.style} op ${n} ${op.op}`;
      switch (op.op) {
        case 'restore':
          for (const m of op.moves) sch.completeInstantly(game.dispatch(m));
          checkTimes(sch, board, op.times, what);
          break;
        case 'send': {
          const ev = game.dispatch(op.q);
          assert.equal(ev.length, op.claims, `${what} claims`);
          const before = sch.trips.length;
          sch.schedule(ev, game.moves.length - 1, op.now);
          const fresh = sch.trips.slice(before);
          assert.equal(fresh.length, op.trips.length, `${what} new trips`);
          fresh.forEach((tr, i) => checkTrip(tr, op.trips[i], board, `${what} trip ${i}`));
          stats.trips += fresh.length;
          for (const tr of fresh) {
            if (tr.style !== 'direct') stats.styled += 1;
            if (tr.pauses.length) stats.pauses += 1;
          }
          const busy = sch.busyTeams(op.busyAt);
          assert.deepEqual([...busy.entries()].sort((a, b) => a[0] - b[0]), op.busy, `${what} busyTeams`);
          for (const [u, tf] of op.slotFree) near(sch.slotFreeTime(u), tf, `${what} slotFreeTime`);
          for (const g of op.geometry) {
            const trip = sch.trips.find(x => x.id === g.trip);
            for (const [u, x, y, dx, dy] of g.curve) {
              const c = AntGeometry.curve(trip, u, board);
              near(c[0], x, `${what} curve x`); near(c[1], y, `${what} curve y`);
              near(c[2], dx, `${what} curve dx`); near(c[3], dy, `${what} curve dy`);
            }
            for (const [e, u, paused] of g.outbound) {
              const o = AntGeometry.outbound(trip, e);
              near(o.u, u, `${what} outbound u`);
              if (paused === null) assert.equal(o.paused, null); else near(o.paused, paused, `${what} paused`);
            }
            stats.geometry += 1;
          }
          break;
        }
        case 'prune': {
          const removed = sch.prune(op.before);
          assert.equal(removed, op.removed, `${what} removed`);
          assert.deepEqual(sch.trips.map(x => x.id), op.remaining, `${what} remaining`);
          stats.prunes += removed;
          break;
        }
        case 'undo': {
          const claims = game.undo();
          sch.undo(claims, game.moves.length);
          assert.deepEqual(sch.trips.map(x => x.id), op.remaining, `${what} remaining`);
          checkTimes(sch, board, op.times, what);
          stats.undos += 1;
          break;
        }
        case 'end':
          assert.deepEqual(sch.trips.map(x => x.id), op.remaining, `${what} remaining`);
          checkTimes(sch, board, op.times, what);
          break;
        default:
          throw new Error(op.op);
      }
    }
  });
}

test('fixture covers styled routes, sniff pauses, prunes and undos', () => {
  assert.ok(stats.trips > 5000, JSON.stringify(stats));
  assert.ok(stats.styled > 500, JSON.stringify(stats));
  assert.ok(stats.pauses > 20, JSON.stringify(stats));
  assert.ok(stats.undos >= 15 && stats.prunes > 100 && stats.geometry > 100, JSON.stringify(stats));
});

test('poses are finite, inside the board and continuous', () => {
  const level = levelOf('koiPond');
  const board = new Board(level.art);
  const game = new Game(level, board, level.chambersExpert);
  const sch = new AntScheduler(board, palette);
  sch.style = 'randomAnt';
  let t = 0;
  for (const q of level.solution.slice(0, 6)) { sch.schedule(game.dispatch(q), game.moves.length - 1, t + 0.04); t += 0.8; }
  let seen = 0;
  for (const trip of sch.trips.slice(0, 200)) {
    let prev = null;
    for (let tt = trip.depart; tt < trip.home; tt += 0.02) {
      const p = AntGeometry.pose(trip, tt, board);
      assert.ok(p && [p.x, p.y, p.heading, p.scale, p.gaitDistance].every(Number.isFinite));
      assert.ok(p.x > 0 && p.x < board.cols && p.y > 0 && p.y < board.rows);
      if (prev) assert.ok(Math.hypot(p.x - prev.x, p.y - prev.y) < 0.2, 'no jumps');
      prev = { x: p.x, y: p.y };
      seen += 1;
    }
    assert.equal(AntGeometry.pose(trip, trip.depart - 0.01, board), null);
    assert.equal(AntGeometry.pose(trip, trip.home, board), null);
  }
  assert.ok(seen > 1000);
});

test('leg kinematics match Tools/ant_gait.py', () => {
  for (const f of fixture.legs) {
    const pose = { x: f.x, y: f.y, heading: f.heading, scale: f.scale, gaitDistance: f.dist, moving: f.moving };
    const out = AntRenderer.legPoints(pose);
    f.legs.forEach((l, i) => {
      const o = i * 7;
      for (let j = 0; j < 6; j++) near(out[o + j], l[j], `leg ${i} coord ${j}`);
      assert.equal(out[o + 6] > 0.05, l[6], `leg ${i} lifted`);
    });
  }
});

test('raster tile templates match Tools/render.py (bevel, grout, glaze) within float32 rounding', () => {
  for (const tf of fixture.raster.tiles) {
    const tpl = MosaicRaster.tileTemplate(RGB(tf.base), tf.s, tf.jitter, data.palette.grout);
    let maxDiff = 0;
    for (let p = 0; p < tf.s * tf.s; p++) {
      for (let c = 0; c < 3; c++) maxDiff = Math.max(maxDiff, Math.abs(tpl[p * 4 + c] - tf.rgb[p * 3 + c]));
      assert.equal(tpl[p * 4 + 3], 255);
    }
    assert.ok(maxDiff <= 1, `s=${tf.s} max diff ${maxDiff}`);
  }
  for (const sf of fixture.raster.soil) {
    const tpl = MosaicRaster.soilTemplate(sf.s, sf.variant, sf.ghost === null ? null : RGB(sf.ghost), sf.soilHex);
    assert.deepEqual([...tpl], sf.rgba);
  }
});

test('raster: sync paints lifted tiles as soil and undo restores them; miniature', () => {
  const level = levelOf('firstDig');
  const board = new Board(level.art);
  const r = new MosaicRaster(board, palette, 7, board.initialOpen(), data.palette.soil);
  assert.equal(r.width, board.cols * 7);
  assert.equal(r.image, null);   // no canvas in Node
  const game = new Game(level, board, level.chambersExpert);
  const sch = new AntScheduler(board, palette);
  sch.schedule(game.dispatch(level.solution[0]), 0, 0.04);
  const tile = sch.trips[0].tile;
  const at = (i, u, v) => {
    const x = board.x(i) * 7 + u, y = board.y(i) * 7 + v;
    return [...r.pixels.slice((y * r.width + x) * 4, (y * r.width + x) * 4 + 4)];
  };
  const before = at(tile, 3, 3);
  assert.equal(r.sync(sch.liftTime, 0), false);
  assert.equal(r.sync(sch.liftTime, sch.trips[0].arrive), true);
  assert.equal(r.shownOpen[tile], 1);
  const variant = hash32(board.x(tile), board.y(tile)) % MosaicRaster.soilVariants;
  const ghost = MosaicRaster.soilTemplate(7, variant, RGB(LevelPalette.tone(palette, board.family[tile], board.tone[tile])), data.palette.soil);
  assert.deepEqual(at(tile, 3, 3), [...ghost.slice((3 * 7 + 3) * 4, (3 * 7 + 3) * 4 + 4)]);
  assert.notDeepEqual(at(tile, 3, 3), before);
  sch.undo(game.undo(), 0);
  assert.equal(r.sync(sch.liftTime, 10), true);
  assert.deepEqual(at(tile, 3, 3), before);
  const mini = MosaicRaster.miniaturePixels(board, palette, () => true);
  assert.equal(mini.length, board.artWidth * board.artHeight * 4);
  const tone0 = LevelPalette.tone(palette, board.family[(Board.marginTop) * board.cols + Board.marginLeft], board.tone[Board.marginTop * board.cols + Board.marginLeft]);
  assert.deepEqual([...mini.slice(0, 3)], [(tone0 >> 16) & 255, (tone0 >> 8) & 255, tone0 & 255]);
  const dark = MosaicRaster.miniaturePixels(board, palette, () => false);
  assert.deepEqual([...dark.slice(0, 4)], [0x2A, 0x20, 0x19, 255]);
});

test('palette, path style tables and planner constants mirror the Swift code', () => {
  assert.deepEqual(data.palette.tones, GeneratedPalette.tones.map(t => [...t]));
  assert.equal(data.palette.grout, GeneratedPalette.grout);
  assert.equal(data.palette.soil, GeneratedPalette.soil);
  assert.equal(data.palette.soilDark, GeneratedPalette.soilDark);
  assert.deepEqual([...PathStyle.allCases], ['direct', 'natural', 'curious', 'wall', 'scout', 'randomTeam', 'randomAnt']);
  assert.equal(PathStyle.title(PathStyle.wall), 'Wall-hugger');
  assert.equal(PATH_STYLE_INFO.scout.title, 'Scout trail');
  assert.equal(PathPlanner.maxRouteCells(10), 24);
  assert.equal(PathPlanner.antBudget(10, 50), 50);
  // heap pops by (f, order)
  const h = new PathPlanner.Heap();
  [[3, 1, 30], [1, 2, 10], [1, 1, 11], [2, 5, 20], [0.5, 9, 5]].forEach(([f, o, c]) => h.push(f, o, c));
  const order = [];
  while (h.count > 0) order.push(h.pop());
  assert.deepEqual(order, [5, 11, 10, 20, 30]);
});
