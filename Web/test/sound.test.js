// Sound port checks against the reference model (Tools/sounds.py via test/fixtures/sounds.json,
// regenerated with `python3 tools/sound_fixtures.py`) and the Swift self-test checksums.
// Web Audio is replaced by a small fake context driven by a fake host clock, so the voice pool,
// throttles, clink thinning and queue cancelling run exactly as they would in a browser.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { SoundSynth, SoundCue, SoundSet, SOUND_CUE_INFO, SoundBoard, Noise, soundCheckReport } from '../src/sound/soundBoard.js';

const fx = JSON.parse(readFileSync(new URL('./fixtures/sounds.json', import.meta.url)));
const T = fx.tables;
const all = SoundSynth.buildAll();

// ---------------------------------------------------------------------------------------------
// helpers

function maxAbsDiff(a, b) {
  assert.equal(a.length, b.length, 'length');
  let m = 0;
  for (let i = 0; i < a.length; i++) m = Math.max(m, Math.abs(a[i] - b[i]));
  return m;
}

/** A minimal AudioContext stand-in. `clock.t` is both host time and context time. */
function fakeContext(clock, opts = {}) {
  const listeners = [];
  const sources = [];
  const param = v => ({ value: v, setTargetAtTime(x) { this.value = x; } });
  const fire = () => { for (const fn of listeners) fn(); };
  const ctx = {
    state: opts.state || 'running',
    sampleRate: 48000,
    baseLatency: 0.005,
    destination: { maxChannelCount: 2 },
    sources,
    resumeCalls: 0,
    suspendCalls: 0,
    get currentTime() { return opts.quantum ? Math.floor(clock.t / opts.quantum) * opts.quantum + (opts.ctxOffset || 0) : clock.t; },
    createGain() { return { connect() {}, disconnect() {}, gain: param(1) }; },
    createStereoPanner() { return { connect() {}, disconnect() {}, pan: param(0) }; },
    createBuffer(ch, n, sr) {
      const data = new Float32Array(n);
      return { length: n, sampleRate: sr, numberOfChannels: ch, copyToChannel(x) { data.set(x); }, getChannelData() { return data; } };
    },
    createBufferSource() {
      const s = {
        buffer: null, when: null, stopped: false, onended: null,
        connect() {}, disconnect() {},
        start(w) { this.when = w; sources.push(this); },
        stop() { this.stopped = true; },
      };
      return s;
    },
    resume() { ctx.resumeCalls += 1; if (!opts.resumeFails) { ctx.state = 'running'; fire(); } return opts.resumeFails ? Promise.reject(new Error('denied')) : Promise.resolve(); },
    suspend() { ctx.suspendCalls += 1; ctx.state = 'suspended'; fire(); return Promise.resolve(); },
    addEventListener(type, fn) { if (type === 'statechange') listeners.push(fn); },
    browserSets(state) { ctx.state = state; fire(); },   // the browser changes state on its own
  };
  return ctx;
}

function makeBoard(opts = {}) {
  const clock = { t: opts.t0 ?? 100 };
  const ctx = fakeContext(clock, opts);
  const trace = [];
  const sb = new SoundBoard({ now: () => clock.t, createContext: () => ctx, scheduleLead: opts.lead ?? 0, trace });
  sb._install(all);
  if (opts.unlock !== false) sb.unlock();
  return { sb, ctx, clock, trace };
}

const started = trace => trace.filter(e => e.at !== undefined);
const sounds = ctx => ctx.sources.filter(s => s.buffer && s.buffer.length > 1);   // skip the 1-sample primer

// ---------------------------------------------------------------------------------------------
// parameter tables

test('tables: recipes, scale, gains and sets match sounds.py and SoundBoard.swift', () => {
  const asTuples = list => list.map(p => [p.ratio, p.amp, p.decay]);
  assert.equal(SoundSynth.rate, T.rate);
  assert.deepEqual(asTuples(SoundSynth.glass), T.glass);
  assert.deepEqual(asTuples(SoundSynth.marimba), T.marimba);
  assert.deepEqual(asTuples(SoundSynth.bell), T.bell);
  assert.deepEqual(asTuples(SoundSynth.wood), T.wood);
  assert.deepEqual(asTuples(SoundSynth.marimbaShort), T.marimbaShort);
  assert.deepEqual(asTuples(SoundSynth.glassBell), T.glassBell);
  assert.deepEqual([...SoundSynth.tileScale], T.tileScale);
  assert.equal(SoundSynth.tileFamilies, 6);
  assert.equal(SoundSynth.variants, 3);
  assert.deepEqual(SoundCue.members(SoundSet.action), T.action);
  assert.deepEqual(SoundCue.members(SoundSet.goal), T.goal);
  assert.deepEqual([...SoundCue.allCases], [...T.action, ...T.goal]);
  assert.deepEqual(Object.keys(SoundCue), [...T.action, ...T.goal]);
  assert.deepEqual(Object.values(SoundSet), ['action', 'goal']);
  for (const c of SoundCue.allCases) {
    assert.equal(SoundCue[c], c);
    assert.equal(SoundCue.gain(c), T.gains[c], c);
    assert.equal(SOUND_CUE_INFO[c].gain, T.gains[c], c);
    assert.equal(SoundCue.set(c), T.goal.includes(c) ? 'goal' : 'action', c);
  }
  assert.equal(SoundBoard.tileGain, T.gains.tile);
  assert.equal(SoundBoard.deliverGain, T.gains.deliver);
  assert.equal(SoundBoard.voiceCount, T.voices);
  assert.deepEqual(SoundSynth.keys(), T.keys);
  assert.equal(SoundSynth.keys().length, 38);       // "Sounds ready: N of 38" in the Sound check
  assert.ok(Object.isFrozen(SoundCue) && Object.isFrozen(SoundSet));
});

// ---------------------------------------------------------------------------------------------
// synthesis

test('noise: 64-bit LCG sequence is identical (including a seed above 2^63)', () => {
  for (const [seed, want] of Object.entries(fx.noise)) {
    const got = new Noise(BigInt(seed)).block(want.length);
    assert.deepEqual([...got], want, `seed ${seed}`);
  }
  // and against a straightforward BigInt implementation over a long run
  const M = (1n << 64n) - 1n;
  let s = 11n;
  const n = new Noise(11);
  for (let i = 0; i < 20000; i++) {
    s = (s * 6364136223846793005n + 1442695040888963407n) & M;
    assert.equal(n.next(), Number((s >> 40n) & 0xFFFFFFn) / 16777215.0 * 2.0 - 1.0);
  }
  assert.equal(n.s, s);
});

// Doubles before the float32 cast. numpy's vectorised exp/sin/pow and V8's Math functions may
// differ in the last bit, and numpy's mean/linspace round differently from the Swift loops this
// port follows; 1e-12 leaves room for that and nothing else.
test('primitives: strike, glide, swish, filters, place/echo match sounds.py (|diff| < 1e-12)', () => {
  const P = fx.primitives;
  const S = SoundSynth;
  const got = {
    strike_glass_click: S.strike(659.26, S.glass, 0.02, 0.18, 0.003, 17),
    strike_thud: S.strike(140.0, [{ ratio: 1.0, amp: 1.0, decay: 0.05 }, { ratio: 2.0, amp: 0.2, decay: 0.03 }], 0.02, 0.3, 0.004, 71),
    glide: S.glide(520.0, 260.0, 0.012, 0.08, 0.03, 0.25),
    swish: S.swish(0.02, 1500.0, 0.005, 0.006, 62),
    swish_reverse: S.swish(0.02, 3000.0, 0.012, 0.05, 81, true),
    highpass: S.highpass(new Noise(3).block(600), 2000.0),
    echo_place: S.echo(S.place(0.01, [{ offset: 0.0, samples: S.strike(880.0, S.wood, 0.006), gain: 0.7 },
                                      { offset: 0.002, samples: S.strike(990.0, S.wood, 0.006), gain: 0.5 }]), 0.003, 0.3, 2),
  };
  for (const k of Object.keys(P)) {
    const d = maxAbsDiff(got[k], P[k]);
    assert.ok(d < 1e-12, `${k}: max |diff| ${d}`);
  }
});

// Finished sounds are float32 (0.9 peak). One float32 step near the peak is 6e-8; the double-level
// differences above can flip a rounding, so samples may differ by one step: tolerance 1.2e-7.
test('all 38 sounds match sounds.py sample for sample (|diff| <= 1 float32 step)', () => {
  let worst = 0, worstKey = '';
  for (const [key, ref] of Object.entries(fx.sounds)) {
    const x = all[key];
    assert.ok(x instanceof Float32Array, key);
    assert.equal(x.length, ref.n, `${key} length`);
    const stride = [];
    for (let i = 0; i < x.length; i += 127) stride.push(x[i]);
    const d = Math.max(maxAbsDiff(x.subarray(0, 48), ref.head), maxAbsDiff(x.subarray(x.length - 8), ref.tail),
      maxAbsDiff(stride, ref.stride));
    if (d > worst) { worst = d; worstKey = key; }
    let peak = 0, sumsq = 0;
    for (const v of x) { peak = Math.max(peak, Math.abs(v)); sumsq += v * v; }
    assert.ok(Math.abs(peak - ref.peak) < 1e-7, `${key} peak ${peak} vs ${ref.peak}`);
    assert.ok(Math.abs(Math.sqrt(sumsq / x.length) - ref.rms) < 1e-7 * ref.rms + 1e-12, `${key} rms`);
    assert.ok(Math.abs(sumsq - ref.sumsq) < 1e-6 * ref.sumsq, `${key} sum of squares`);
    assert.ok(Math.abs(SoundSynth.checksum(x) - ref.checksum) < 1e-6 * ref.checksum, `${key} checksum`);
    assert.equal(Math.abs(x[0]), 0, `${key} starts at 0`);
    assert.ok(Math.abs(x[x.length - 1]) < 1e-3, `${key} ends quietly`);
  }
  assert.ok(worst <= 1.2e-7, `worst sample difference ${worst} in ${worstKey}`);
});

test('checksums match SelfTest.swift reference values (Swift allows 0.1 %, here 1e-6)', () => {
  const swift = {
    tile_0_0: 1221.1821, tile_5_2: 1189.3696, deliver_1: 539.8157, send: 932.7665,
    refused: 1912.8411, returnTeam: 3160.2103, undo: 769.5946, hint: 2422.5694,
    teamDone: 5312.5162, colourCleared: 5976.6603, milestone3: 7200.6016, complete: 13814.0814,
    newBest: 6448.295, unlocked: 11659.4385,
  };
  for (const [k, want] of Object.entries(swift)) {
    assert.ok(Math.abs(SoundSynth.checksum(all[k]) - want) < 1e-6 * want + 1e-4, `${k}: ${SoundSynth.checksum(all[k])} vs ${want}`);
    assert.equal(fx.checksums[k], want, `fixture ${k}`);
  }
});

test('loudest plausible moment stays below full scale (sounds.worst_case_mix: 0.818)', () => {
  // the same mix as sounds.worst_case_mix: clinks every 50 ms, drops every 80 ms, four big cues at once
  const rate = SoundSynth.rate, S = SoundSynth;
  const total = S.samples(2.5);
  const mix = new Float64Array(total);
  const add = (x, t, g) => {
    const s = S.samples(t), e = Math.min(total, s + x.length);
    for (let i = s; i < e; i++) mix[i] += g * x[i - s];
  };
  const tiles = SoundSynth.keys().filter(k => k.startsWith('tile_'));
  let t = 0.0, k = 0;
  while (t < 2.2) { add(all[tiles[k % tiles.length]], t, SoundBoard.tileGain); t += 0.05; k += 1; }
  t = 0.0;
  while (t < 2.2) { add(all[`deliver_${k % 3}`], t, SoundBoard.deliverGain); t += 0.08; k += 1; }
  for (const c of ['send', 'teamDone', 'complete', 'unlocked']) add(all[c], 0, SoundCue.gain(c));
  let peak = 0;
  for (const v of mix) peak = Math.max(peak, Math.abs(v));
  assert.ok(Math.abs(peak - fx.worst_case_mix) < 1e-6, `${peak} vs ${fx.worst_case_mix}`);
  assert.ok(peak < 0.85);
  void rate;
});

// ---------------------------------------------------------------------------------------------
// clink scheduling: GameController.pumpTileSounds driving the real SoundBoard, against
// sounds.pump_simulation (same ticks, trips and speed plans)

function makeTrips(count, span) {
  const { phi, plastic } = fx.tripConstants;
  const out = [];
  for (let i = 0; i < count; i++) {
    const a = span * ((i * phi) % 1.0);
    out.push([a, a + 0.8 + 1.7 * ((i * plastic) % 1.0)]);
  }
  return out;
}

function runPump(name) {
  const spec = fx.pump[name];
  const ts = fx.tripSets[spec.trips];
  const trips = makeTrips(ts.count, ts.span);
  const { sb, ctx, clock, trace } = makeBoard({ t0: 0 });
  // GameClock: game = anchorGame + (real - anchorReal) * speed
  const gc = { ar: 0, ag: 0, speed: spec.plan[0][1] };
  const game = r => gc.ag + (r - gc.ar) * gc.speed;
  const plan = spec.plan.slice(1);
  let cursor = 0, soundSpeed = spec.plan[0][1], cancels = 0;
  for (const r of spec.ticks) {
    while (plan.length && plan[0][0] <= r) {
      const [rc, v] = plan.shift();
      gc.ag = game(rc); gc.ar = rc; gc.speed = v;                       // GameController.setSpeed
      if (Math.abs(Math.log(v / soundSpeed)) > Math.log(1.25)) {
        clock.t = rc;
        sb.cancelQueuedClicks();
        cursor = Math.min(cursor, game(rc));
        soundSpeed = v;
        cancels += 1;
      }
    }
    clock.t = r;                                                        // GameController.pumpTileSounds
    const t = game(r), sp = gc.speed;
    const horizon = t + T.lookahead * sp;
    const from = Math.max(cursor, t - T.stale * sp);
    cursor = Math.max(cursor, horizon);
    soundSpeed = sp;
    if (!(horizon > from)) continue;
    const events = [];
    trips.forEach(([a, h], i) => {
      if (from < a && a <= horizon) events.push([a, 'tile', i]);
      if (from < h && h <= horizon) events.push([h, 'deliver', i]);
    });
    events.sort((x, y) => x[0] - y[0] || (x[1] < y[1] ? -1 : x[1] > y[1] ? 1 : 0) || x[2] - y[2]);
    const pace = Math.max(0.01, sp);
    for (const [et, kind, i] of events) {
      const delay = Math.max(0, (et - t) / pace);
      if (kind === 'tile') sb.tile(i, 0, delay); else sb.deliver(0, delay);
    }
  }
  const srcs = sounds(ctx);
  const heard = started(trace).map((e, j) => ({ ...e, src: srcs[j] })).filter(e => !e.src.stopped);
  return { spec, heard, trace, cancels, ctx };
}

for (const name of Object.keys(fx.pump)) {
  test(`clink timing and thinning match sounds.pump_simulation: ${name}`, () => {
    const { spec, heard, trace, cancels } = runPump(name);
    const kinds = heard.map(e => (e.key.startsWith('tile') ? 't' : 'd')).join('');
    assert.equal(kinds.length, spec.heardKinds.length, 'number of clinks heard');
    assert.equal(kinds, spec.heardKinds, 'order of tile clinks and nest drops');
    let worst = 0;
    heard.forEach((e, i) => { worst = Math.max(worst, Math.abs(e.at - spec.heardStarts[i])); });
    assert.ok(worst < 1e-9, `start times differ by ${worst}`);
    // the start time handed to Web Audio is the same instant (fake context time == host time, no lead)
    for (const e of heard) assert.ok(Math.abs(e.when - e.at) < 1e-9 && e.src.when === e.when);
    const st = spec.stats;
    assert.equal(heard.filter(e => e.key.startsWith('tile')).length, st.tile_clinks);
    assert.equal(heard.filter(e => e.key.startsWith('deliver')).length, st.deliver_drops);
    assert.equal(cancels, st.queue_cancels);
    assert.equal(trace.filter(e => e.failed === 'no free voice').length, st.voice_starved);
    const tiles = heard.filter(e => e.key.startsWith('tile')).map(e => e.at).sort((a, b) => a - b);
    let maxRate = 0;
    for (let k = 0, j = 0; k < tiles.length; k++) {
      while (tiles[k] - tiles[j] >= 1.0) j++;
      maxRate = Math.max(maxRate, k - j + 1);
    }
    assert.equal(maxRate, st.max_clinks_in_any_second);
    if (name === '16x') assert.ok(maxRate <= 20, 'clinks thin out to about 20 a second at 16x');
  });
}

// ---------------------------------------------------------------------------------------------
// SoundBoard behaviour

test('without Web Audio (Node): nothing throws and nothing plays', async () => {
  const sb = SoundBoard.shared;
  assert.equal(SoundBoard.shared, sb);
  assert.equal(sb.unlock(), false);
  assert.equal(sb.isUnlocked, false);
  sb.configure(true, 0.7, true, true, true, false);
  sb.play(SoundCue.send);
  sb.play('nonsense');
  sb.tile(3, 0.2, 0.01);
  sb.deliver(-0.4, 0);
  sb.playSample(SoundSet.goal);
  sb.cancelQueuedClicks();
  sb.setHidden(true);
  sb.setHidden(false);
  assert.equal(sb.playTestSound(), false);
  sb.silence();
  await sb.prepare();
  assert.equal(sb.soundsReady, 38);
  sb.play(SoundCue.teamDone);
  assert.equal(sb.startedCount, 0);
  const s = sb.status();
  assert.equal(s.engineRunning, false);
  assert.equal(s.soundsReady, 38);
  assert.match(soundCheckReport(s, false), /Sounds ready: 38 of 38/);
  assert.match(soundCheckReport(s, false), /Audio unlocked: no/);
  assert.equal(typeof SoundBoard.hostSeconds(), 'number');
});

test('prepare() synthesizes all 38 sounds once, in slices, identical to buildAll()', async () => {
  const sb = new SoundBoard();
  assert.equal(sb.soundsReady, 0);
  const p1 = sb.prepare();
  assert.equal(sb.prepare(), p1, 'a second call while building returns the same promise');
  assert.equal(sb.soundsReady, 0, 'installed all at once when done (like Swift)');
  await p1;
  assert.equal(sb.soundsReady, 38);
  for (const k of SoundSynth.keys()) assert.deepEqual(sb._samples[k], all[k]);
});

test('play: gates on unlock, on/off, set switches and the 90 ms per-cue throttle', () => {
  const { sb, ctx, clock, trace } = makeBoard({ unlock: false });
  sb.play(SoundCue.send);
  assert.equal(started(trace).length, 0, 'no-op before unlock()');
  assert.equal(sb.unlock(), true);
  sb.play(SoundCue.send);
  assert.equal(started(trace).length, 1);
  const e = started(trace)[0];
  assert.equal(e.gain, 0.5);
  assert.equal(e.pan, 0);
  assert.equal(e.when, clock.t);
  assert.equal(sounds(ctx)[0].buffer.length, all.send.length);
  assert.deepEqual(sounds(ctx)[0].buffer.getChannelData(0), all.send);
  clock.t += 0.05; sb.play(SoundCue.send);
  assert.equal(started(trace).length, 1, 'within 90 ms of the last send');
  sb.play(SoundCue.undo);
  assert.equal(started(trace).length, 2, 'other cues are throttled separately');
  clock.t += 0.05; sb.play(SoundCue.send);
  assert.equal(started(trace).length, 3, '100 ms later');
  sb.configure(true, 0.8, true, false, true);          // action sounds off
  clock.t += 1; sb.play(SoundCue.hint); sb.play(SoundCue.teamDone);
  assert.deepEqual(started(trace).slice(3).map(x => x.key), ['teamDone']);
  sb.configure(true, 0.8, true, true, false);          // goal sounds off
  clock.t += 1; sb.play(SoundCue.hint); sb.play(SoundCue.complete);
  assert.deepEqual(started(trace).slice(4).map(x => x.key), ['hint']);
  sb.configure(false, 0.8, true);                      // all off
  clock.t += 1; sb.play(SoundCue.hint); sb.tile(0, 0, 0); sb.deliver(0, 0); sb.playSample('action');
  assert.equal(sb.playTestSound(), false);
  assert.equal(started(trace).length, 5);
  assert.equal(ctx.state, 'suspended', 'switching sound off pauses the context (Swift: engine.pause)');
});

test('play(cue, delay): delay is scheduled exactly, clamped to 0...5 s', () => {
  const { sb, clock, trace } = makeBoard();
  sb.play(SoundCue.wait, 0.28);
  sb.play(SoundCue.newBest, 2.1);
  sb.play(SoundCue.unlocked, 12);
  sb.play(SoundCue.blocked, NaN);
  sb.play(SoundCue.refused, -3);
  const s = started(trace);
  assert.deepEqual(s.map(x => x.key), ['wait', 'newBest', 'unlocked', 'blocked', 'refused']);
  assert.deepEqual(s.map(x => +(x.at - clock.t).toFixed(9)), [0.28, 2.1, 5, 0, 0]);
  assert.deepEqual(s.map(x => +(x.when - clock.t).toFixed(9)), [0.28, 2.1, 5, 0, 0]);
});

test('tile/deliver: colour pitch, variants, panning, gains and the 50 / 80 ms throttles', () => {
  const { sb, clock, trace } = makeBoard();
  // the variant counter only advances for requests that pass the throttle (as in Swift)
  sb.tile(2, -0.5, 0);          // counter 1 -> variant 1
  sb.tile(2, 0, 0.03);          // 30 ms later: merged into the first
  sb.tile(-1, 3, 0.06);         // family wraps to 5, pan clamps to 1
  sb.tile(7, 0, 0.12);          // family 7 -> 1
  sb.deliver(0.4, 0);
  sb.deliver(0, 0.07);          // 70 ms: dropped
  sb.deliver(0, 0.09);
  const s = started(trace);
  assert.deepEqual(s.map(x => x.key), ['tile_2_1', 'tile_5_2', 'tile_1_0', 'deliver_1', 'deliver_2']);
  assert.deepEqual(s.map(x => x.pan), [-0.5, 1, 0, 0.4, 0]);
  assert.deepEqual(s.map(x => x.gain), [0.22, 0.22, 0.22, 0.12, 0.12]);
  assert.ok(s.every(x => x.click));
  assert.deepEqual(s.map(x => +(x.at - clock.t).toFixed(9)), [0, 0.06, 0.12, 0, 0.09]);
  sb.configure(true, 0.8, false);        // colony clinks off
  clock.t += 1; sb.tile(0, 0, 0); sb.deliver(0, 0);
  assert.equal(started(trace).length, 5);
});

test('16x: a dense pickup stream thins to at most 20 clinks a second; 14 voices', () => {
  const { sb, clock, trace } = makeBoard();
  // 400 pickups a second handed over 0.16 s ahead every 100 ms (GameController's lookahead)
  for (let tick = 0; tick < 30; tick++) {
    clock.t = 100 + tick * 0.1;
    for (let j = 0; j < 64; j++) sb.tile(j, 0, j * 0.0025);
  }
  const s = started(trace).filter(x => x.click).map(x => x.at);
  for (let i = 1; i < s.length; i++) assert.ok(s[i] - s[i - 1] >= 0.05 - 1e-9);
  const perSecond = s.filter(a => a >= 101 && a < 102).length;
  assert.ok(perSecond >= 19 && perSecond <= 20, `${perSecond} clinks in one second`);
  // voice pool: 14 long sounds at once, the 15th finds no voice
  const v = makeBoard();
  for (const c of SoundCue.allCases) { v.sb.play(c, 0.5); v.clock.t += 0.001; }
  assert.equal(started(v.trace).length, 14);
  assert.equal(v.trace.filter(x => x.failed === 'no free voice').length, 17 - 14);
  v.clock.t += 5;                         // all finished: voices free again
  v.sb.play(SoundCue.send);
  assert.equal(started(v.trace).length, 15);
});

test('cancelQueuedClicks stops only clinks that have not started; the next ones re-queue', () => {
  const { sb, ctx, clock, trace } = makeBoard();
  sb.play(SoundCue.wait, 0.28);           // queued cue: kept
  sb.tile(0, 0, 0);                       // playing now: kept
  sb.tile(1, 0, 0.1);                     // queued: dropped
  sb.deliver(0, 0.12);                    // queued: dropped
  clock.t += 0.01;
  sb.cancelQueuedClicks();
  const srcs = sounds(ctx);
  assert.deepEqual(srcs.map(s => s.stopped), [false, false, true, true]);
  // handed over again at the new speed: the throttles restart from now (not from the dropped ones)
  sb.tile(1, 0, 0.03);                    // 30 ms after the reset point: still too close
  sb.tile(1, 0, 0.06);
  sb.deliver(0, 0.09);
  assert.deepEqual(started(trace).slice(4).map(x => x.key), ['tile_1_1', 'deliver_2']);
});

test('suspended/interrupted context: queued sounds are dropped, nothing stale plays on resume', async () => {
  const { sb, ctx, clock, trace } = makeBoard();
  sb.tile(0, 0, 0.1);
  sb.play(SoundCue.unlocked, 3.1);
  ctx.browserSets('interrupted');          // e.g. iOS: phone call or tab hidden
  assert.ok(sounds(ctx).every(s => s.stopped), 'every queued sound stopped');
  clock.t += 0.5;
  sb.play(SoundCue.send);                  // not running: asks to resume, plays nothing now
  assert.equal(started(trace).length, 2);
  assert.equal(ctx.resumeCalls, 1);
  await Promise.resolve();
  clock.t += 0.5;                          // the resume landed
  sb.play(SoundCue.send);
  assert.equal(started(trace).length, 3);
  assert.equal(sounds(ctx).filter(s => !s.stopped).length, 1, 'only the new sound is live');
  // a failing resume is not retried more than every 2 s (Swift: lastFailedStart)
  const f = makeBoard({ state: 'suspended', resumeFails: true, unlock: false });
  f.sb.unlock();
  await Promise.resolve(); await Promise.resolve();
  for (let i = 0; i < 10; i++) { f.clock.t += 0.6; f.sb.play(SoundCue.send); }
  assert.ok(f.ctx.resumeCalls <= 4, `${f.ctx.resumeCalls} resume attempts in 6 s`);
  assert.match(f.sb.status().error, /denied/);
});

test('setHidden: drops the queue and suspends; showing resumes', async () => {
  const { sb, ctx, clock, trace } = makeBoard();
  sb.tile(0, 0, 0.12);
  sb.setHidden(true);
  assert.equal(ctx.state, 'suspended');
  assert.ok(sounds(ctx).every(s => s.stopped));
  clock.t += 1;
  sb.play(SoundCue.send); sb.tile(1, 0, 0);
  assert.equal(started(trace).length, 1, 'silent while hidden');
  assert.equal(ctx.resumeCalls, 0, 'no resume while hidden');
  sb.setHidden(false);
  assert.equal(ctx.state, 'running');
  sb.play(SoundCue.send);
  assert.equal(started(trace).length, 2);
});

test('a sound requested just after a gesture resume is scheduled, not lost', () => {
  const clock = { t: 10 };
  const ctx = fakeContext(clock, { state: 'suspended' });
  ctx.resume = () => { ctx.resumeCalls += 1; return new Promise(() => {}); };   // still pending
  const trace = [];
  const sb = new SoundBoard({ now: () => clock.t, createContext: () => ctx, scheduleLead: 0, trace });
  sb._install(all);
  sb.unlock();
  sb.play(SoundCue.send);
  assert.equal(started(trace).length, 1);
  clock.t += 1;                            // the resume never finished: give up scheduling
  sb.play(SoundCue.hint);
  assert.equal(started(trace).length, 1);
  // when that resume finally lands (much later, e.g. at the next tap), the old sound is dropped
  ctx.state = 'running';
  ctx.browserSets('running');
  assert.ok(sounds(ctx).every(x => x.stopped), 'no stale burst after a late resume');
  // a prompt resume keeps what was queued in the meantime
  const c2 = fakeContext(clock, { state: 'suspended' });
  c2.resume = () => { c2.resumeCalls += 1; return new Promise(() => {}); };
  const t2 = [];
  const b2 = new SoundBoard({ now: () => clock.t, createContext: () => c2, scheduleLead: 0, trace: t2 });
  b2._install(all);
  b2.unlock();
  b2.play(SoundCue.send, 0.1);
  clock.t += 0.02;
  c2.browserSets('running');
  assert.equal(sounds(c2).filter(x => !x.stopped).length, 1);
});

test('volume and Silent mode: master gain, navigator.audioSession playback / ambient', () => {
  const session = { type: 'auto' };
  const had = Object.getOwnPropertyDescriptor(globalThis.navigator, 'audioSession');
  Object.defineProperty(globalThis.navigator, 'audioSession', { value: session, configurable: true });
  try {
    const { sb } = makeBoard({ unlock: false });
    sb.configure(true, 1.7, true);
    assert.equal(session.type, 'playback', 'default: play even in Silent mode');
    assert.equal(sb.volume, 1);
    sb.unlock();
    assert.equal(sb._submix.gain.value, 1);
    sb.configure(true, 0.25, true, true, true, false);
    assert.equal(session.type, 'ambient');
    assert.equal(sb._submix.gain.value, 0.25);
    assert.equal(sb.ignoresSilentMode, false);
    assert.equal(sb.status().category, 'ambient');
    sb.configure(true, 0.25, true, true, true, true);
    assert.equal(session.type, 'playback');
  } finally {
    if (had) Object.defineProperty(globalThis.navigator, 'audioSession', had);
    else delete globalThis.navigator.audioSession;
  }
});

test('playSample: every sound of a set in turn, even when that set is switched off', () => {
  const { sb, clock, trace } = makeBoard();
  sb.configure(true, 0.8, true, false, false);
  sb.playSample(SoundSet.action);
  let s = started(trace);
  assert.deepEqual(s.map(x => x.key), T.action);
  let t = 0.05;
  T.action.forEach((c, i) => {
    assert.ok(Math.abs(s[i].at - clock.t - t) < 1e-9, c);
    assert.equal(s[i].gain, T.gains[c]);
    t += all[c].length / 44100 + 0.3;
  });
  clock.t += 30;
  sb.playSample(SoundSet.goal);
  s = started(trace).slice(T.action.length);
  assert.deepEqual(s.map(x => x.key), T.goal);
  t = 0.05;
  T.goal.forEach((c, i) => {
    assert.ok(Math.abs(s[i].at - clock.t - t) < 1e-9, `${c} at ${s[i].at - clock.t} (not clamped to 5 s)`);
    t += all[c].length / 44100 * 0.75 + 0.3;
  });
});

test('Sound check: test chime ignores the set switches; report mirrors SoundCheckRow', () => {
  const { sb, trace } = makeBoard({ unlock: false });
  sb.configure(true, 0.8, true, true, false);
  assert.equal(sb.playTestSound(), true, 'the button press unlocks audio');
  const e = started(trace)[0];
  assert.equal(e.key, 'teamDone');
  assert.equal(e.gain, 0.8);
  const st = sb.status();
  assert.deepEqual(Object.keys(st).slice(0, 8),
    ['enabled', 'soundsReady', 'engineRunning', 'category', 'outputs', 'deviceVolume', 'started', 'error']);
  assert.equal(st.engineRunning, true);
  assert.equal(st.started, 1);
  const text = soundCheckReport(st, true);
  assert.match(text, /^Sound effects: on\nSounds ready: 38 of 38\nTest chime started: yes\n/);
  assert.match(text, /Audio engine running: yes/);
  assert.match(text, /Sounds started since launch: 1/);
  const fresh = new SoundBoard({ createContext: () => fakeContext({ t: 0 }) });
  assert.equal(fresh.playTestSound(), false, 'sounds not ready yet: starts preparing');
  assert.equal(fresh._building, true);
});

test('context clock mapping keeps clinks evenly spaced although currentTime moves in steps', () => {
  // currentTime advances in 10.7 ms audio callbacks and runs 3 s ahead of the host clock
  const { sb, ctx, clock, trace } = makeBoard({ quantum: 512 / 48000, ctxOffset: 3, t0: 50 });
  for (let tick = 0; tick < 300; tick++) {
    clock.t = 50 + tick * 0.1 + 0.0037 * ((tick * 7) % 5);      // irregular ticks
    // a clink every 60 ms of host time, handed over up to 0.16 s ahead
    const first = Math.ceil((clock.t - 50) / 0.06);
    for (let j = first; 50 + j * 0.06 <= clock.t + 0.16; j++) sb.tile(j, 0, 50 + j * 0.06 - clock.t);
  }
  const s = started(trace);
  assert.ok(s.length > 400);
  // the mapping settles on the top of the currentTime sawtooth within the first ticks; after that
  // the spacing of the scheduled starts equals the spacing asked for
  const settled = s.filter(e => e.at > 50.5);
  const gaps = [];
  for (let i = 1; i < settled.length; i++) gaps.push((settled[i].when - settled[i - 1].when) - (settled[i].at - settled[i - 1].at));
  const errs = gaps.map(Math.abs).sort((a, b) => a - b);
  const worst = errs[errs.length - 1], p90 = errs[Math.floor(errs.length * 0.9)];
  assert.ok(worst < 0.001 && p90 < 0.0002,
    `spacing error max ${worst * 1000} ms, p90 ${p90 * 1000} ms (raw currentTime would give up to 10.7 ms)`);
  // never scheduled behind the context's current time; host -> context offset is the 3 s head start
  for (const e of s) assert.ok(e.when - (e.at + 3) > -512 / 48000 - 1e-9 && e.when - (e.at + 3) < 1e-9);
  void ctx;
});
