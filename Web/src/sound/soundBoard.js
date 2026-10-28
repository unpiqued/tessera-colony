// Port of SoundBoard.swift: the synthesized sound effects and the voice pool that plays them, on the
// Web Audio API. SoundSynth computes every sample in JS exactly like the Swift buffer code (same
// recipes, same 64-bit LCG noise, same one-pole filters, same fades and normalisation); the float32
// results are bit-identical to Tools/sounds.py on every sample the tests compare (test/sound.test.js).
// Each sound is rendered once into an AudioBuffer; playing one is a buffer source started at a
// precise `when`, so hundreds of clink requests a second at 16x stay cheap (the board thins them to
// about 20 a second anyway).
//
// Browser rules handled here (no DOM is touched; only Web Audio and navigator.audioSession):
// * An AudioContext may only start after a user gesture. The UI calls `SoundBoard.shared.unlock()`
//   from capture-phase pointerdown, pointerup and keydown listeners (a touch pointerdown is not a
//   user activation, its pointerup is). Calling it on every event is cheap and lets iOS recover
//   after an interruption. Until then every play call is a silent no-op that never throws.
// * When the browser suspends or interrupts the context (tab hidden on iOS, phone call, ...) every
//   queued sound is dropped at once, so nothing stale bursts out when it resumes. `setHidden(hidden)`
//   (called by the UI from `visibilitychange`) suspends audio while the page is hidden.
// * Sound off releases audio entirely (the context is closed, nothing is created on taps), so a
//   podcast or music app keeps playing. Sound on mixes with other audio by default ('ambient', no
//   <audio> element): an <audio> element or 'playback' would pause the other app.
// * "Play sounds even in Silent mode" maps to `navigator.audioSession.type = 'playback'` (else
//   'ambient') where the Audio Session API exists (Safari 16.4+). Elsewhere it has no effect: desktop
//   browsers have no silent switch, Android follows the media volume, and on iOS Safari before 16.4
//   Web Audio always follows the Ring/Silent switch.
// * Node (tests): nothing touches AudioContext unless it exists; synthesis and the scheduling
//   bookkeeping run without it.

// ---------------------------------------------------------------------------------------------
// SoundSynth
// ---------------------------------------------------------------------------------------------

/** Damped sine partial: frequency ratio, amplitude, decay time constant (s). Swift `SoundSynth.Partial`. */
export function Partial(ratio, amp, decay) { return { ratio, amp, decay }; }

/** One sound placed in a mix: start offset (s), samples, gain. Swift `SoundSynth.Part`. */
export function Part(offset, samples, gain) { return { offset, samples, gain }; }

const TWO32 = 4294967296;
// LCG multiplier 6364136223846793005 and increment 1442695040888963407 as 32-bit halves
const A_HI = 0x5851F42D, A_LO = 0x4C957F2D, A_LO0 = 0x7F2D, A_LO1 = 0x4C95;
const C_HI = 0x14057B7E, C_LO = 0xF767814F;

/**
 * 64-bit LCG noise (identical sequence to `SoundSynth.Noise` in Swift and `Noise` in sounds.py).
 * The UInt64 state is kept as two uint32 halves so no BigInt work happens per sample.
 */
export class Noise {
  constructor(seed) {
    const s = BigInt.asUintN(64, BigInt(seed));
    this.hi = Number(s >> 32n) >>> 0;
    this.lo = Number(s & 0xFFFFFFFFn) >>> 0;
  }
  /** The state as a BigInt (the Swift `s`). */
  get s() { return (BigInt(this.hi) << 32n) | BigInt(this.lo); }
  next() {
    // s = s &* A &+ C, with a full 32x32 -> 64 bit product for the low halves
    const lo = this.lo, hi = this.hi;
    const a0 = lo & 0xFFFF, a1 = lo >>> 16;
    const mid = a0 * A_LO1 + a1 * A_LO0;                    // < 2^33, exact
    let low = a0 * A_LO0 + (mid % 65536) * 65536;           // < 2^33, exact
    const carry = low >= TWO32 ? 1 : 0;
    low -= carry * TWO32;
    const high = a1 * A_LO1 + Math.floor(mid / 65536) + carry + Math.imul(hi, A_LO) + Math.imul(lo, A_HI);
    const sumLo = low + C_LO;
    const carry2 = sumLo >= TWO32 ? 1 : 0;
    this.lo = (sumLo - carry2 * TWO32) >>> 0;
    this.hi = (high + C_HI + carry2) >>> 0;
    return ((this.hi >>> 8) & 0xFFFFFF) / 16777215.0 * 2.0 - 1.0;
  }
  block(n) {
    const out = new Float64Array(n);
    for (let i = 0; i < n; i++) out[i] = this.next();
    return out;
  }
}

const P = Partial;
const GLASS = Object.freeze([P(1.0, 1.0, 0.07), P(2.76, 0.35, 0.035), P(5.40, 0.12, 0.02)]);
const MARIMBA = Object.freeze([P(1.0, 1.0, 0.25), P(4.0, 0.25, 0.05), P(9.2, 0.06, 0.02)]);
const BELL = Object.freeze([P(1.0, 1.0, 0.6), P(2.0, 0.4, 0.35), P(3.0, 0.15, 0.25), P(4.2, 0.12, 0.15), P(5.4, 0.06, 0.1)]);
const WOOD = Object.freeze([P(1.0, 1.0, 0.03), P(2.3, 0.4, 0.02)]);
const MARIMBA_SHORT = Object.freeze([P(1.0, 1.0, 0.09), P(4.0, 0.25, 0.03), P(9.2, 0.06, 0.015)]);
const GLASS_BELL = Object.freeze([...BELL, P(1.004, 0.5, 0.5), P(2.006, 0.2, 0.3)]);

/**
 * Sound effects are synthesized in code (no audio files ship with the app). Line-by-line mirror of
 * SoundSynth in SoundBoard.swift / Tools/sounds.py.
 *
 * Recipes: struck notes are damped sine partials (glass, marimba, bell, wood) plus a noise click;
 * swishes are deterministic noise through one-pole filters; glides are exponential sine sweeps.
 * Every sound is DC-removed, faded in and out, and normalised to a 0.9 peak; loudness per cue is
 * applied at play time. Sample arrays are Float64Array while building and Float32Array when finished.
 */
export class SoundSynth {
  static rate = 44100.0;

  static glass = GLASS;
  static marimba = MARIMBA;
  static bell = BELL;
  static wood = WOOD;
  static marimbaShort = MARIMBA_SHORT;
  /** A bell with slightly detuned twins: the beating gives the goal sounds their shimmer. */
  static glassBell = GLASS_BELL;

  /** One note per colour family (major pentatonic from C5): each colour clinks at its own pitch. */
  static tileScale = Object.freeze([523.25, 587.33, 659.26, 783.99, 880.00, 1046.50, 1174.66, 1318.51]);
  static tileFamilies = 6;
  static variants = 3;

  static samples(seconds) { return Math.trunc(seconds * SoundSynth.rate); }

  /**
   * exp(-t / decay) for t = i / rate, i < n: the same values strike() would compute, shared between
   * notes that use the same recipe (bit-identical, and about a third less work for the bells).
   */
  static _envelope(decay, n) {
    const cache = SoundSynth._envelopes;
    const key = `${decay}:${n}`;
    let env = cache.get(key);
    if (!env) {
      const rate = SoundSynth.rate;
      env = new Float64Array(n);
      for (let i = 0; i < n; i++) env[i] = Math.exp(-(i / rate) / decay);
      if (cache.size > 64) cache.clear();
      cache.set(key, env);
    }
    return env;
  }
  static _envelopes = new Map();

  static strike(freq, partials, length, click = 0, clickDecay = 0.003, seed = 1, attack = 0.002) {
    const rate = SoundSynth.rate;
    const n = SoundSynth.samples(length);
    const out = new Float64Array(n);
    for (const p of partials) {
      const f = freq * p.ratio;
      if (f >= rate * 0.45) continue;
      const w = 2 * Math.PI * f;
      const amp = p.amp;
      const env = SoundSynth._envelope(p.decay, n);       // env[i] = exp(-t / decay)
      for (let i = 0; i < n; i++) {
        const t = i / rate;
        out[i] += amp * env[i] * Math.sin(w * t);
      }
    }
    if (click > 0) {
      const nz = SoundSynth.highpass(new Noise(seed).block(n), 2000.0);
      for (let i = 0; i < n; i++) {
        const t = i / rate;
        out[i] += click * nz[i] * Math.exp(-t / clickDecay);
      }
    }
    const a = SoundSynth.samples(attack);
    if (a > 0) {
      const m = Math.min(a, n);
      for (let i = 0; i < m; i++) out[i] *= i / a;
    }
    return out;
  }

  static glide(f1, f2, glideTime, decay, length, harmonic2 = 0) {
    const rate = SoundSynth.rate;
    const n = SoundSynth.samples(length);
    const out = new Float64Array(n);
    const a = SoundSynth.samples(0.004);
    const ratio = f2 / f1;
    let acc = 0.0;
    for (let i = 0; i < n; i++) {
      const t = i / rate;
      const k = Math.min(t / glideTime, 1.0);
      acc += f1 * Math.pow(ratio, k);
      const phase = 2 * Math.PI * acc / rate;
      let env = Math.exp(-t / decay);
      if (i < a) env *= i / a;
      out[i] = env * (Math.sin(phase) + harmonic2 * Math.sin(2 * phase));
    }
    return out;
  }

  static lowpass(x, cutoff) {
    const a = 1.0 - Math.exp(-2 * Math.PI * cutoff / SoundSynth.rate);
    const y = new Float64Array(x.length);
    let acc = 0.0;
    for (let i = 0; i < x.length; i++) {
      acc += a * (x[i] - acc);
      y[i] = acc;
    }
    return y;
  }

  static highpass(x, cutoff) {
    const l = SoundSynth.lowpass(x, cutoff);
    const y = new Float64Array(x.length);
    for (let i = 0; i < x.length; i++) y[i] = x[i] - l[i];
    return y;
  }

  static swish(length, cutoff, rise, decay, seed, reverse = false) {
    const rate = SoundSynth.rate;
    const n = SoundSynth.samples(length);
    const nz = SoundSynth.lowpass(new Noise(seed).block(n), cutoff);
    const env = new Float64Array(n);
    for (let i = 0; i < n; i++) {
      const t = i / rate;
      if (reverse) {
        env[i] = t > rise ? 0 : Math.exp((t - rise) / (rise / 4.0));
      } else {
        env[i] = t < rise ? t / rise : Math.exp(-(t - rise) / decay);
      }
    }
    if (reverse) {
      const cut = Math.min(SoundSynth.samples(rise), n);
      const fade = Math.min(SoundSynth.samples(0.004), cut);
      for (let j = 0; j < fade; j++) {
        const w = fade > 1 ? 1.0 - j / (fade - 1) : 1.0;
        env[cut - fade + j] *= w;
      }
    }
    const out = new Float64Array(n);
    for (let i = 0; i < n; i++) out[i] = nz[i] * env[i];
    return out;
  }

  static place(total, parts) {
    const out = new Float64Array(SoundSynth.samples(total));
    for (const p of parts) {
      const s = SoundSynth.samples(p.offset);
      const e = Math.min(out.length, s + p.samples.length);
      for (let i = s; i < e; i++) out[i] += p.gain * p.samples[i - s];
    }
    return out;
  }

  /** Adds `taps` delayed copies, each `feedback` times quieter (a small hall shimmer). */
  static echo(x, delay, feedback, taps) {
    const d = SoundSynth.samples(delay);
    const out = new Float64Array(x.length + Math.max(0, taps) * d);
    for (let i = 0; i < x.length; i++) out[i] += x[i];
    let g = 1.0;
    for (let k = 1; k <= taps; k++) {
      g *= feedback;
      const off = k * d;
      for (let i = 0; i < x.length; i++) out[off + i] += g * x[i];
    }
    return out;
  }

  static finish(input, peak = 0.9) {
    const x = Float64Array.from(input);
    const n = x.length;
    if (n === 0) return new Float32Array(0);
    let sum = 0;
    for (let i = 0; i < n; i++) sum += x[i];
    const mean = sum / n;
    for (let i = 0; i < n; i++) x[i] -= mean;
    const fi = SoundSynth.samples(0.002);
    for (let i = 0, m = Math.min(fi, n); i < m; i++) x[i] *= i / fi;
    const fo = Math.min(n, Math.max(SoundSynth.samples(0.012), Math.trunc(n * 0.25)));
    for (let j = 0; j < fo; j++) {
      const u = fo > 1 ? j / (fo - 1) : 0;
      x[n - fo + j] *= 0.5 * (1 + Math.cos(Math.PI * u));
    }
    let m = 0.0;
    for (let i = 0; i < n; i++) m = Math.max(m, Math.abs(x[i]));
    const k = m > 0 ? peak / m : 0;
    const out = new Float32Array(n);
    for (let i = 0; i < n; i++) out[i] = x[i] * k;
    return out;
  }

  // MARK: the sound set

  static tile(family, variant) {
    const freq = SoundSynth.tileScale[family] * (1 + (variant - 1) * 0.012);
    return SoundSynth.finish(SoundSynth.strike(freq, GLASS, 0.22, 0.18, 0.003, 11 + family * 3 + variant));
  }

  static deliver(variant) {
    const rate = SoundSynth.rate;
    const f = 380.0 * (1 + (variant - 1) * 0.03);
    const body = SoundSynth.strike(f, WOOD, 0.12, 0, 0.003, 40 + variant);
    const n = SoundSynth.samples(0.12);
    const lp = SoundSynth.lowpass(new Noise(50 + variant).block(n), 2500.0);
    const x = body;
    for (let i = 0; i < n; i++) x[i] += 0.5 * lp[i] * Math.exp(-(i / rate) / 0.006);
    return SoundSynth.finish(x);
  }

  static cue(c) {
    const S = SoundSynth, strike = S.strike, place = S.place, echo = S.echo, finish = S.finish;
    switch (c) {
      // ---- ACTION set: wood and clay ----
      case 'send':
        return finish(place(0.28, [Part(0.0, strike(330.0, WOOD, 0.12, 0.25, 0.003, 61), 0.8),
                                   Part(0.0, S.swish(0.28, 1500.0, 0.02, 0.06, 62), 0.45),
                                   Part(0.01, S.glide(200.0, 120.0, 0.12, 0.06, 0.2), 0.6)]));
      case 'scout':
        return finish(place(0.2, [Part(0.0, strike(660.0, WOOD, 0.08, 0.1, 0.003, 91), 0.6),
                                  Part(0.06, strike(880.0, WOOD, 0.08, 0.1, 0.003, 92), 0.5)]));
      case 'undo':
        return finish(place(0.2, [Part(0.0, S.swish(0.2, 3000.0, 0.09, 0.05, 81, true), 0.7),
                                  Part(0.09, strike(520.0, WOOD, 0.11, 0.2, 0.003, 82), 0.6)]));
      case 'addSlot':
        return finish(place(0.3, [Part(0.0, strike(392.0, MARIMBA_SHORT, 0.16), 0.7),
                                  Part(0.08, strike(523.25, MARIMBA_SHORT, 0.2), 0.8)]));
      case 'returnTeam':
        return finish(place(0.35, [Part(0.0, S.glide(520.0, 260.0, 0.12, 0.08, 0.3, 0.25), 0.6),
                                   Part(0.11, strike(261.63, MARIMBA_SHORT, 0.22), 0.7)]));
      case 'refused': {
        const thud = strike(140.0, [P(1.0, 1.0, 0.05), P(2.0, 0.2, 0.03)], 0.15, 0.3, 0.004, 71);
        return finish(place(0.3, [Part(0.0, thud, 1.0), Part(0.11, thud, 0.8)]));
      }
      case 'wait':
        return finish(place(0.45, [Part(0.0, strike(329.63, MARIMBA, 0.3), 1.0),
                                   Part(0.12, strike(246.94, MARIMBA, 0.32), 0.9)]));
      case 'blocked':
        return finish(place(0.8, [Part(0.0, strike(220.0, MARIMBA, 0.68), 0.8),
                                  Part(0.06, strike(261.63, MARIMBA, 0.68), 0.8),
                                  Part(0.12, strike(329.63, MARIMBA, 0.68), 0.8)]));
      case 'hint':
        return finish(place(0.4, [Part(0.0, strike(440.0, MARIMBA_SHORT, 0.25), 0.7),
                                  Part(0.09, strike(587.33, MARIMBA_SHORT, 0.3), 0.7)]));
      // ---- GOAL set: bells and glass ----
      case 'teamDone':
        return finish(echo(place(0.7, [Part(0.0, strike(783.99, GLASS_BELL, 0.6), 0.55),
                                       Part(0.08, strike(1174.66, GLASS_BELL, 0.62), 0.55)]), 0.11, 0.3, 2));
      case 'colourCleared':
        return finish(echo(place(0.9, [Part(0.0, strike(1046.50, GLASS_BELL, 0.8), 0.45),
                                       Part(0.07, strike(1318.51, GLASS_BELL, 0.8), 0.45),
                                       Part(0.14, strike(1567.98, GLASS_BELL, 0.76), 0.45),
                                       Part(0.14, strike(523.25, BELL, 0.76), 0.3)]), 0.12, 0.35, 3));
      case 'milestone1':
      case 'milestone2':
      case 'milestone3': {
        const notes = c === 'milestone1' ? [523.25, 587.33, 659.26, 783.99]
          : c === 'milestone2' ? [659.26, 783.99, 880.00, 1046.50]
          : [783.99, 880.00, 1046.50, 1174.66, 1318.51];
        const parts = notes.map((f, k) => Part(k * 0.07, strike(f, GLASS_BELL, 0.7), 0.42));
        return finish(echo(place(1.0, parts), 0.12, 0.3, 2));
      }
      case 'complete': {
        const arp = [523.25, 659.26, 783.99, 1046.50, 1318.51, 1567.98];
        const parts = arp.map((f, k) => Part(k * 0.085, strike(f, BELL, 1.2), 0.45));
        const longBell = BELL.map(p => P(p.ratio, p.amp, p.decay * 2.2));
        for (const f of [523.25, 783.99, 1046.50, 1318.51]) parts.push(Part(0.6, strike(f, longBell, 1.6), 0.3));
        return finish(echo(place(2.2, parts), 0.13, 0.28, 2));
      }
      case 'newBest': {
        const parts = [1046.50, 1318.51, 1567.98, 2093.0].map((f, k) => Part(k * 0.06, strike(f, GLASS_BELL, 0.7), 0.45));
        return finish(echo(place(0.9, parts), 0.1, 0.3, 2));
      }
      case 'unlocked': {
        const sparkle = [1046.50, 1174.66, 1318.51, 1567.98, 1760.00, 2093.0, 2349.32, 2637.02];
        const parts = sparkle.map((f, k) => Part(k * 0.045, strike(f, GLASS, 0.25, 0, 0.003, 120 + k), 0.35));
        const longBell = BELL.map(p => P(p.ratio, p.amp, p.decay * 2.2));
        for (const f of [523.25, 659.26, 783.99]) parts.push(Part(0.4, strike(f, longBell, 1.2), 0.3));
        return finish(echo(place(1.6, parts), 0.12, 0.3, 2));
      }
      default:
        throw new Error(`SoundSynth.cue: unknown cue ${c}`);
    }
  }

  /** Every key buildAll produces, in its order ("tile_0_0" … "deliver_2", then the cues). */
  static keys() {
    const out = [];
    for (let f = 0; f < SoundSynth.tileFamilies; f++) {
      for (let v = 0; v < SoundSynth.variants; v++) out.push(`tile_${f}_${v}`);
    }
    for (let v = 0; v < SoundSynth.variants; v++) out.push(`deliver_${v}`);
    for (const c of SoundCue.allCases) out.push(c);
    return out;
  }

  /** One sound by key (JS helper used by buildAll and the chunked prepare()). */
  static sound(key) {
    let m = /^tile_(\d+)_(\d+)$/.exec(key);
    if (m) return SoundSynth.tile(Number(m[1]), Number(m[2]));
    m = /^deliver_(\d+)$/.exec(key);
    if (m) return SoundSynth.deliver(Number(m[1]));
    return SoundSynth.cue(key);
  }

  /** Every sound, keyed like the reference WAV files ("tile_2_1", "deliver_0", "send", ...). */
  static buildAll() {
    const out = {};
    for (const key of SoundSynth.keys()) out[key] = SoundSynth.sound(key);
    return out;
  }

  /** Sum of |sample| — compared with the reference model in the self-test. */
  static checksum(x) {
    let s = 0.0;
    for (let i = 0; i < x.length; i++) s += Math.abs(x[i]);
    return s;
  }
}

// ---------------------------------------------------------------------------------------------
// SoundSet / SoundCue
// ---------------------------------------------------------------------------------------------

/**
 * Which set a sound belongs to (each has its own switch in Settings).
 * `action`: dry wood and clay, the moves the player makes. `goal`: bright bells and glass, goals reached.
 * `SoundSet.allCases` is non-enumerable, so Object.values(SoundSet) lists only the cases.
 */
export const SoundSet = Object.freeze(Object.defineProperties({ action: 'action', goal: 'goal' }, {
  allCases: { value: Object.freeze(['action', 'goal']) },
}));

const CUE_GAINS = {
  send: 0.5, scout: 0.3, undo: 0.35, addSlot: 0.45, returnTeam: 0.4, refused: 0.55, wait: 0.45, blocked: 0.45,
  hint: 0.4, teamDone: 0.38, colourCleared: 0.45, milestone1: 0.42, milestone2: 0.42, milestone3: 0.42,
  complete: 0.55, newBest: 0.5, unlocked: 0.5,
};
const ACTION_CUES = ['send', 'scout', 'undo', 'addSlot', 'returnTeam', 'refused', 'wait', 'blocked', 'hint'];
const GOAL_CUES = ['teamDone', 'colourCleared', 'milestone1', 'milestone2', 'milestone3', 'complete', 'newBest', 'unlocked'];

/**
 * Per-cue table for the Swift computed properties `cue.set` and `cue.gain` (play-time gain, which
 * the board multiplies by the player's volume).
 */
export const SOUND_CUE_INFO = Object.freeze(Object.fromEntries([
  ...ACTION_CUES.map(c => [c, Object.freeze({ set: 'action', gain: CUE_GAINS[c] })]),
  ...GOAL_CUES.map(c => [c, Object.freeze({ set: 'goal', gain: CUE_GAINS[c] })]),
]));

/**
 * The event sounds (tile clinks and nest drops are the separate "colony" layer, see
 * `SoundBoard.tile` / `deliver`). Frozen object of strings; the Swift computed properties are
 * non-enumerable helpers: `SoundCue.allCases`, `SoundCue.set(c)`, `SoundCue.gain(c)`,
 * `SoundCue.members(set)` (also available as the SOUND_CUE_INFO table).
 */
export const SoundCue = Object.freeze(Object.defineProperties(
  Object.fromEntries([...ACTION_CUES, ...GOAL_CUES].map(c => [c, c])), {
    allCases: { value: Object.freeze([...ACTION_CUES, ...GOAL_CUES]) },
    set: { value: c => SOUND_CUE_INFO[c].set },
    gain: { value: c => SOUND_CUE_INFO[c].gain },
    members: { value: s => (s === 'goal' ? GOAL_CUES : ACTION_CUES).slice() },
  }));

// ---------------------------------------------------------------------------------------------
// SoundBoard
// ---------------------------------------------------------------------------------------------

function defaultHostSeconds() {
  const perf = globalThis.performance;
  return (perf && typeof perf.now === 'function' ? perf.now() : Date.now()) / 1000;
}

function audioContextConstructor() {
  return globalThis.AudioContext || globalThis.webkitAudioContext || null;
}

/** navigator.audioSession (Safari 16.4+), or null. */
function audioSession() {
  try {
    const nav = globalThis.navigator;
    return nav && nav.audioSession ? nav.audioSession : null;
  } catch (e) {
    return null;
  }
}


/** Half a second of silence (8-bit WAV). Playing it in a looping <audio> element after a tap moves
 *  an iPhone/iPad page into the media "playback" audio category, so Web Audio is heard even with the
 *  Ring/Silent switch on silent — navigator.audioSession alone is not honoured inside every frame. */
const SILENT_WAV = 'data:audio/wav;base64,UklGRsQPAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YaAPAACAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICA';

/** iPhone, iPod or iPad (iPadOS reports itself as a Mac with touch). */
function isAppleTouch() {
  try {
    const nav = globalThis.navigator;
    if (!nav) return false;
    return /iPad|iPhone|iPod/.test(nav.userAgent || '') || (nav.platform === 'MacIntel' && nav.maxTouchPoints > 1);
  } catch (e) {
    return false;
  }
}

function errorText(e) { return e && e.message ? e.message : String(e); }

/** max(0, delay) as Swift computes it for a finite delay; NaN / infinite count as 0. */
function nonNegative(delay) { return Number.isFinite(delay) ? Math.max(0, delay) : 0; }

/** Own-property test (cue names come from callers; 'toString' must not look like a sound). */
function HAS(obj, key) { return obj !== null && Object.prototype.hasOwnProperty.call(obj, key); }

/**
 * Plays the synthesized effects through a small pool of voices.
 *
 * * The web app mixes with other audio by default (audio session 'ambient': a podcast keeps playing
 *   and, on iPhone, sounds follow the Ring/Silent switch); Settings can switch to 'playback' (sounds
 *   play in Silent mode, other audio pauses). Sound off closes the context.
 * * Tile clicks are scheduled against the game clock a fraction of a second ahead, with
 *   sample-accurate start times, so they land exactly when an ant lifts a tile (at any speed).
 * * Throttled: at most ~20 tile clicks and ~12 nest drops a second, one of each other cue per 90 ms,
 *   14 voices, and gains chosen so the loudest plausible moment stays below full scale (0.82).
 *
 * Times: the bookkeeping runs on host seconds (performance.now() / 1000, the analogue of the Swift
 * mach host time); start times are mapped onto the AudioContext clock when a sound is scheduled.
 */
export class SoundBoard {
  static tileGain = 0.22;
  static deliverGain = 0.12;
  static voiceCount = 14;
  /** Longest delay a game sound may be scheduled ahead (Swift clamps to 5 s). */
  static maxDelay = 5;
  /** playSample may queue further ahead: the goal set runs about 10 s (see playSample). */
  static sampleMaxDelay = 15;

  static _shared = null;
  /** The app-wide board (Swift `SoundBoard.shared`). */
  static get shared() {
    if (!SoundBoard._shared) SoundBoard._shared = new SoundBoard();
    return SoundBoard._shared;
  }

  /** Host clock in seconds (Swift: mach host time). */
  static hostSeconds() { return defaultHostSeconds(); }

  /**
   * The app uses `SoundBoard.shared`. Options exist for tests and offline rendering:
   * `now()` host seconds, `createContext()` returns an AudioContext-like object (an
   * OfflineAudioContext renders without a gesture), `scheduleLead` seconds added to every start.
   */
  constructor(options = {}) {
    this._now = options.now || defaultHostSeconds;
    this._createContext = options.createContext || null;
    this._leadOption = options.scheduleLead;
    /** When set to an array, every start attempt is recorded there (tests). */
    this.trace = options.trace || null;

    this._isOn = true;
    this._tileClicks = true;
    this._actionSounds = true;
    this._goalSounds = true;
    this._volume = 0.8;
    this._ignoresSilentMode = true;
    this._lastError = null;
    this._startedCount = 0;

    this._ctx = null;
    this._offline = false;
    this._submix = null;
    this._lead = 0;
    this._hidden = false;
    this._resumePending = false;
    this._resumeAt = -100;
    this._clockOffset = null;
    this._clockAt = 0;
    this._offlineHost0 = 0;

    const n = SoundBoard.voiceCount;
    this._busyUntil = new Array(n).fill(0);
    /** When each voice's current sound starts, and whether it is a tile clink / nest drop. */
    this._voiceStart = new Array(n).fill(0);
    this._voiceIsClick = new Array(n).fill(false);
    this._voiceNode = new Array(n).fill(null);

    this._samples = null;      // key -> Float32Array once prepared
    this._buffers = {};        // key -> AudioBuffer (made when a context exists)
    this._building = false;
    this._buildPromise = null;
    this._lastCue = {};
    this._lastTile = -1.0;
    this._lastDeliver = -1.0;
    this._counter = 0;
  }

  get isOn() { return this._isOn; }
  get tileClicks() { return this._tileClicks; }
  get actionSounds() { return this._actionSounds; }
  get goalSounds() { return this._goalSounds; }
  get volume() { return this._volume; }
  /** Play even when the device is in Silent mode ('playback', pauses other audio); otherwise mix ('ambient'). */
  get ignoresSilentMode() { return this._ignoresSilentMode; }
  /** Last audio error (shown by the Sound check in Settings). */
  get lastError() { return this._lastError; }
  /** How many sounds have been started since launch (Sound check). */
  get startedCount() { return this._startedCount; }
  /** True once unlock() has created the audio context. */
  get isUnlocked() { return this._ctx !== null; }
  /** True while the silent <audio> element is playing (iPhone/iPad, Silent-mode playback only). */
  get keepAliveActive() { return !!(this._keepAlive && !this._keepAlive.paused); }
  /** Number of sounds synthesized (38 when ready). */
  get soundsReady() { return this._samples ? Object.keys(this._samples).length : 0; }
  /** The AudioContext (null until unlock()). */
  get context() { return this._ctx; }

  /** Called with the saved settings at launch and whenever they change. */
  configure(on, volume, tileClicks, actions = true, goals = true, ignoreSilentMode = true) {
    const wasOn = this._isOn, wasPlayback = this._isOn && this._ignoresSilentMode;
    this._ignoresSilentMode = !!ignoreSilentMode;
    this._isOn = !!on;
    // Swift restarts its engine with the new session category; here the type applies at once, and
    // a context started under the other category is closed (the next tap starts a fresh one)
    this._applyAudioSession();
    if ((wasOn && !this._isOn) || (this._isOn && wasPlayback !== this._ignoresSilentMode)) this._release();
    this._tileClicks = !!tileClicks;
    this._actionSounds = !!actions;
    this._goalSounds = !!goals;
    const v = Number(volume);
    this._volume = Number.isFinite(v) ? Math.max(0, Math.min(1, v)) : 0.8;
    this._applyVolume();
    if (this._isOn) {
      this.prepare();
    } else {
      this.silence();
    }
    if (!this._isOn || !this._ignoresSilentMode) this._stopSilentKeepAlive();
  }

  /**
   * Synthesizes every sound once, one or more sounds per macrotask so the page stays responsive
   * (about 0.3 s of work in all; the longest slice, `complete`, about 60 ms on a desktop). Returns a
   * promise that resolves when all 38 are ready (Swift returns nothing; awaiting it is optional).
   */
  prepare() {
    if (this._samples) return Promise.resolve();
    if (this._building) return this._buildPromise;
    this._building = true;
    this._buildPromise = new Promise(resolve => {
      const keys = SoundSynth.keys();
      const all = {};
      let i = 0;
      const step = () => {
        const t0 = defaultHostSeconds();
        while (i < keys.length) {
          all[keys[i]] = SoundSynth.sound(keys[i]);
          i += 1;
          if (defaultHostSeconds() - t0 > 0.008) break;
        }
        if (i < keys.length) {
          setTimeout(step, 0);
        } else {
          this._install(all);
          resolve();
        }
      };
      setTimeout(step, 0);
    });
    return this._buildPromise;
  }

  /** Synthesizes everything right now (blocking, ~0.3 s). Used by tests and offline rendering. */
  prepareNow() {
    if (!this._samples) this._install(SoundSynth.buildAll());
  }

  _install(all) {
    this._samples = all;
    this._buffers = {};
    this._building = false;
  }

  // MARK: playing

  play(cue, delay = 0) {
    const info = HAS(SOUND_CUE_INFO, cue) ? SOUND_CUE_INFO[cue] : null;
    if (!info || !this._isOn || !(info.set === 'action' ? this._actionSounds : this._goalSounds)) return;
    if (!HAS(this._samples, cue)) return;
    const now = this._now();
    const last = this._lastCue[cue];
    if (last !== undefined && now - last < 0.09) return;
    if (this._start(cue, info.gain, 0, delay, false, SoundBoard.maxDelay, now)) this._lastCue[cue] = now;
  }

  /**
   * Plays every sound of a set one after another (the "Play a sample" buttons in Settings).
   * Plays even if that set is switched off, so it can be auditioned. (The Swift version clamps every
   * delay to 5 s, which piles the last goal sounds up at 5 s; here the sample may run to 15 s.)
   */
  playSample(set) {
    if (!this._isOn || !this._samples) return;
    let t = 0.05;
    for (const cue of SoundCue.members(set)) {
      const x = this._samples[cue];
      if (!x) continue;
      this._start(cue, SoundCue.gain(cue), 0, t, false, SoundBoard.sampleMaxDelay);
      t += x.length / SoundSynth.rate * (set === 'goal' ? 0.75 : 1.0) + 0.3;
    }
  }

  /** An ant lifts a tile of colour `family`; `pan` is -1 (left) ... 1 (right). */
  tile(family, pan, delay) {
    if (!this._isOn || !this._tileClicks) return;
    const now = this._now();
    const at = now + nonNegative(delay);
    if (at - this._lastTile < 0.05) return;
    this._counter += 1;
    const nf = SoundSynth.tileFamilies;
    const f = (((family | 0) % nf) + nf) % nf;
    const key = `tile_${f}_${this._counter % SoundSynth.variants}`;
    if (!HAS(this._samples, key)) return;
    if (this._start(key, SoundBoard.tileGain, pan, delay, true, SoundBoard.maxDelay, now)) this._lastTile = at;
  }

  /** An ant drops its tile in the nest. */
  deliver(pan, delay) {
    if (!this._isOn || !this._tileClicks) return;
    const now = this._now();
    const at = now + nonNegative(delay);
    if (at - this._lastDeliver < 0.08) return;
    this._counter += 1;
    const key = `deliver_${this._counter % SoundSynth.variants}`;
    if (!HAS(this._samples, key)) return;
    if (this._start(key, SoundBoard.deliverGain, pan, delay, true, SoundBoard.maxDelay, now)) this._lastDeliver = at;
  }

  /**
   * Drops tile clinks and nest drops queued for the future: their start times assumed the old
   * ant speed. The game hands them over again at the new speed on its next tick.
   */
  cancelQueuedClicks() {
    const now = this._now();
    for (let k = 0; k < this._busyUntil.length; k++) {
      if (this._voiceIsClick[k] && this._voiceStart[k] > now) {
        this._stopVoice(k);
        this._busyUntil[k] = 0;
        this._voiceStart[k] = 0;
      }
    }
    this._lastTile = Math.min(this._lastTile, now);
    this._lastDeliver = Math.min(this._lastDeliver, now);
  }

  /** Stops everything that is playing or queued (and pauses the audio context, like Swift). */
  silence() {
    this._stopSilentKeepAlive();
    this._stopAll();
    const ctx = this._ctx;
    if (ctx && !this._offline && ctx.state === 'running' && typeof ctx.suspend === 'function') {
      this._resumePending = false;
      ctx.suspend().catch(() => {});
    }
  }

  // MARK: browser lifecycle (JS only)

  /**
   * Creates and starts the AudioContext. Call it from user gestures (pointerdown, pointerup,
   * keydown; a touch only counts on pointerup / touchend / click). Calling it again later is cheap
   * and resumes a context the browser suspended (needed on iOS after an interruption). Returns true
   * when a context exists. Never throws.
   */
  unlock() {
    // sound off: touch nothing, so other apps' audio (a podcast, music) keeps playing
    if (!this._isOn) return this._ctx !== null;
    if (this._isOn && this._ignoresSilentMode && !this._hidden) this._startSilentKeepAlive();
    if (this._ctx) {
      if (!this._offline && this._ctx.state !== 'running' && this._isOn && !this._hidden) {
        this._primeOutput();
        this._resume(true);
      }
      return true;
    }
    const Ctor = this._createContext ? null : audioContextConstructor();
    if (!this._createContext && !Ctor) return false;
    this._applyAudioSession();
    let ctx = null;
    try {
      if (this._createContext) {
        ctx = this._createContext();
      } else {
        try {
          ctx = new Ctor({ latencyHint: 'interactive' });
        } catch (e) {
          ctx = new Ctor();                    // old webkitAudioContext takes no options
        }
      }
    } catch (e) {
      this._lastError = `Audio context didn't start: ${errorText(e)}`;
      return false;
    }
    if (!ctx) return false;
    this._build(ctx);
    if (!this._offline) {
      this._primeOutput();
      if (!this._isOn || this._hidden) {
        if (typeof ctx.suspend === 'function') ctx.suspend().catch(() => {});
      } else if (ctx.state !== 'running') {
        this._resume(true);
      }
    }
    return true;
  }

  /**
   * The page was hidden / shown (the UI forwards `document.hidden` from visibilitychange). Hidden:
   * drop every queued sound and suspend the context. Shown: resume (if sound is on).
   */
  setHidden(hidden) {
    this._hidden = !!hidden;
    const ctx = this._ctx;
    if (!ctx || this._offline) return;
    if (this._hidden) {
      this._stopSilentKeepAlive();
      this._stopAll();
      this._resumePending = false;
      if (typeof ctx.suspend === 'function' && ctx.state === 'running') ctx.suspend().catch(() => {});
    } else if (this._isOn && ctx.state !== 'running') {
      this._resume(true);
    }
  }

  // MARK: engine

  /**
   * Starts `key` on a free voice. `now` is the host time the caller throttled with, so the
   * throttle and the start time use one clock reading (Swift reads the host clock twice; with
   * performance.now() coarsened to 0.1-1 ms in browsers that would shift clinks by a step).
   */
  _start(key, gain, pan, delay, click, maxDelay = SoundBoard.maxDelay, now = this._now()) {
    if (!this._ensureRunning()) {
      if (this.trace) this.trace.push({ key, failed: 'not running' });
      return false;
    }
    let k = -1;
    for (let i = 0; i < this._busyUntil.length; i++) {
      if (this._busyUntil[i] <= now) { k = i; break; }
    }
    if (k < 0) {
      if (this.trace) this.trace.push({ key, failed: 'no free voice' });
      return false;
    }
    const buffer = this._buffer(key);
    if (!buffer) return false;
    const d = Math.min(maxDelay, nonNegative(delay));
    const length = this._samples[key].length / SoundSynth.rate;
    const p = Number.isFinite(pan) ? Math.max(-1, Math.min(1, pan)) : 0;
    const ctx = this._ctx;
    let src = null;
    let when = 0;
    try {
      src = ctx.createBufferSource();
      src.buffer = buffer;
      const g = ctx.createGain();
      g.gain.value = gain;
      src.connect(g);
      let out = g;
      let panner = null;
      if (typeof ctx.createStereoPanner === 'function') {
        panner = ctx.createStereoPanner();
        panner.pan.value = p;
        g.connect(panner);
        out = panner;
      }
      out.connect(this._submix);
      // Swift plays d < 4 ms "as soon as possible"; Web Audio takes any time (a past one plays at
      // once) and the lead keeps it in the future, so every sound gets its exact start.
      when = Math.max(ctx.currentTime, this._contextTime(now) + this._lead + d);
      src.onended = () => {
        try { src.disconnect(); g.disconnect(); if (panner) panner.disconnect(); } catch (e) { /* already gone */ }
        if (this._voiceNode[k] === src) this._voiceNode[k] = null;
      };
      src.start(when);
    } catch (e) {
      this._lastError = `Couldn't start a sound: ${errorText(e)}`;
      return false;
    }
    this._busyUntil[k] = now + d + length + 0.03;
    this._voiceStart[k] = now + d;
    this._voiceIsClick[k] = click;
    this._voiceNode[k] = src;
    this._startedCount += 1;
    if (this.trace) this.trace.push({ key, at: now + d, when, ctxTime: ctx.currentTime, gain, pan: p, click, voice: k });
    return true;
  }

  /** True when sounds can be scheduled now. Asks a suspended context to resume (throttled). */
  _ensureRunning() {
    const ctx = this._ctx;
    if (!ctx) return false;                       // not unlocked yet: silent, never throws
    if (this._offline) return true;
    if (this._hidden) return false;
    if (ctx.state === 'running') return true;
    // A resume asked for by a gesture a moment ago: sounds scheduled now play as it starts.
    if (this._resumePending && this._now() - this._resumeAt < 0.5) return true;
    this._resume(false);
    return false;
  }

  _resume(fromGesture) {
    const ctx = this._ctx;
    if (!ctx || typeof ctx.resume !== 'function') return;
    const now = this._now();
    if (!fromGesture && now - this._resumeAt < 2) return;   // don't hammer a failing audio system
    this._resumeAt = now;
    this._resumePending = true;
    this._applyAudioSession();
    let pr;
    try {
      pr = ctx.resume();
    } catch (e) {
      this._resumePending = false;
      this._lastError = `Audio didn't start: ${errorText(e)}`;
      return;
    }
    if (pr && typeof pr.then === 'function') {
      pr.then(() => { this._resumePending = false; },
        e => {
          this._resumePending = false;
          this._lastError = `Audio didn't start: ${errorText(e)}`;
          this._stopAll();                          // nothing queued may play late
        });
    }
  }

  /**
   * Lets go of the audio hardware: stops and drops the silent <audio> element (so it can't stay the
   * phone's "now playing" source) and closes the context. unlock() starts again from scratch.
   */
  _release() {
    this._stopSilentKeepAlive(true);
    this._stopAll();
    const ctx = this._ctx;
    if (!ctx || this._offline) return;
    this._ctx = null;
    this._submix = null;
    this._buffers = {};
    this._resumePending = false;
    this._clockOffset = null;
    try {
      if (typeof ctx.close === 'function') { const p = ctx.close(); if (p && typeof p.catch === 'function') p.catch(() => {}); }
      else if (typeof ctx.suspend === 'function') ctx.suspend().catch(() => {});
    } catch (e) { /* already closed */ }
  }

  _build(ctx) {
    this._ctx = ctx;
    this._offline = typeof ctx.startRendering === 'function';
    this._buffers = {};
    const sub = ctx.createGain();
    sub.gain.value = this._volume;
    sub.connect(ctx.destination);
    this._submix = sub;
    const base = Number(ctx.baseLatency) || 0;
    this._lead = this._leadOption !== undefined ? this._leadOption
      : this._offline ? 0 : Math.min(0.05, Math.max(0.01, 2 * base));
    this._clockOffset = null;
    this._offlineHost0 = this._now();
    const onState = () => {
      if (this._ctx !== ctx) return;              // a context released earlier
      this._clockOffset = null;
      if (ctx.state === 'running') {
        // sounds queued while a resume was pending are stale if it took long (e.g. unlock() was
        // called outside a gesture and the context only started at the next tap)
        if (this._resumePending && this._now() - this._resumeAt > 0.5) this._stopAll();
        this._resumePending = false;
      } else if (!this._resumePending) {
        // suspended / interrupted / closed by the browser: queued sounds would burst out stale later
        this._stopAll();
      }
    };
    if (typeof ctx.addEventListener === 'function') ctx.addEventListener('statechange', onState);
    else ctx.onstatechange = onState;
  }

  /** iPhone/iPad only: loop a silent <audio> element (must start inside a user gesture). */
  _startSilentKeepAlive() {
    if (!isAppleTouch() || typeof document === 'undefined' || !document.createElement) return;
    try {
      let a = this._keepAlive;
      if (!a) {
        a = document.createElement('audio');
        a.setAttribute('x-webkit-airplay', 'deny');
        a.setAttribute('playsinline', '');
        a.preload = 'auto';
        a.loop = true;
        a.src = SILENT_WAV;
        this._keepAlive = a;
      }
      if (a.paused) {
        const p = a.play();
        if (p && typeof p.catch === 'function') p.catch(() => {});
      }
    } catch (e) { /* media playback unavailable: Web Audio still plays when the switch is on ring */ }
  }

  _stopSilentKeepAlive(drop = false) {
    const a = this._keepAlive;
    if (a && !a.paused) { try { a.pause(); } catch (e) { /* ignore */ } }
    if (a && drop) {
      // an emptied element no longer holds the media session
      try { a.removeAttribute('src'); a.load(); } catch (e) { /* ignore */ }
      this._keepAlive = null;
    }
  }

  /** iOS Safari before 15 only unlocks output once a buffer has been started inside the gesture. */
  _primeOutput() {
    const ctx = this._ctx;
    try {
      const b = ctx.createBuffer(1, 1, ctx.sampleRate || 44100);
      const s = ctx.createBufferSource();
      s.buffer = b;
      s.connect(ctx.destination);
      s.start(0);
      s.onended = () => { try { s.disconnect(); } catch (e) { /* ignore */ } };
    } catch (e) { /* not needed elsewhere */ }
  }

  _applyVolume() {
    const sub = this._submix;
    if (!sub) return;
    try {
      const ctx = this._ctx;
      if (!this._offline && typeof sub.gain.setTargetAtTime === 'function' && ctx.state === 'running') {
        sub.gain.setTargetAtTime(this._volume, ctx.currentTime, 0.015);
      } else {
        sub.gain.value = this._volume;
      }
    } catch (e) {
      sub.gain.value = this._volume;
    }
  }

  _applyAudioSession() {
    const s = audioSession();
    if (!s) return;
    const want = this._isOn && this._ignoresSilentMode ? 'playback' : 'ambient';
    try {
      if (s.type !== want) s.type = want;
    } catch (e) {
      this._lastError = `Audio session: ${errorText(e)}`;
    }
  }

  _buffer(key) {
    if (HAS(this._buffers, key)) return this._buffers[key];
    const x = HAS(this._samples, key) ? this._samples[key] : null;
    const ctx = this._ctx;
    if (!x || !ctx) return null;
    try {
      const b = ctx.createBuffer(1, x.length, SoundSynth.rate);
      if (typeof b.copyToChannel === 'function') b.copyToChannel(x, 0);
      else b.getChannelData(0).set(x);
      this._buffers[key] = b;
      return b;
    } catch (e) {
      this._lastError = `Couldn't make a sound buffer: ${errorText(e)}`;
      return null;
    }
  }

  /**
   * Host seconds -> AudioContext time. currentTime only moves once per audio callback, so the
   * sampled offset (currentTime - host) is a sawtooth. The estimate creeps up towards the top of
   * that sawtooth at 1 ms per second and slides down 0.2 ms per second (drift between the audio and
   * host clocks); it jumps only when it is more than half the scheduling lead behind (so `when`
   * stays ahead of the render position) or when the context clock stalled. Clinks handed over in
   * different ticks therefore keep their spacing to about 0.1 ms instead of a whole audio callback.
   */
  _contextTime(hostNow) {
    const ctx = this._ctx;
    // offline rendering: the context timeline starts at the host time of unlock()
    if (this._offline) return ctx.currentTime + Math.max(0, hostNow - this._offlineHost0);
    const sample = ctx.currentTime - hostNow;
    let off = this._clockOffset;
    if (off === null) {
      off = sample;
    } else {
      const dt = Math.max(0, hostNow - this._clockAt);
      off -= 0.0002 * dt;
      if (sample > off + Math.max(0.002, this._lead / 2) || off - sample > 0.1) off = sample;
      else if (sample > off) off = Math.min(sample, off + 0.001 * dt);
    }
    this._clockOffset = off;
    this._clockAt = hostNow;
    return hostNow + off;
  }

  _stopVoice(k) {
    const src = this._voiceNode[k];
    this._voiceNode[k] = null;
    if (src) {
      try { src.stop(); } catch (e) { /* never started or already stopped */ }
    }
  }

  _stopAll() {
    for (let k = 0; k < this._busyUntil.length; k++) {
      this._stopVoice(k);
      this._busyUntil[k] = 0;
      this._voiceStart[k] = 0;
    }
  }

  // MARK: sound check (Settings)

  /**
   * Everything the Sound check shows (Swift `SoundBoard.Status` fields, plus web details).
   * `deviceVolume` is null: web pages cannot read the device volume.
   */
  status() {
    const ctx = this._ctx;
    const s = audioSession();
    let outputs = 'none (tap the page first to start audio)';
    if (ctx) {
      const ch = ctx.destination && ctx.destination.maxChannelCount;
      outputs = `default output (${ch === 1 ? 'mono' : ch ? `${ch} channels` : 'stereo'}, ${ctx.sampleRate} Hz)`;
    }
    return {
      enabled: this._isOn,
      soundsReady: this.soundsReady,
      engineRunning: !!ctx && (this._offline || ctx.state === 'running'),
      category: s ? String(s.type) : 'browser default (no Audio Session API)',
      outputs,
      deviceVolume: null,
      started: this._startedCount,
      error: this._lastError,
      // web extras
      unlocked: !!ctx,
      contextState: ctx ? String(ctx.state) : 'none',
      hidden: this._hidden,
      sampleRate: ctx ? ctx.sampleRate : null,
      baseLatency: ctx && Number.isFinite(ctx.baseLatency) ? ctx.baseLatency : null,
      outputLatency: ctx && Number.isFinite(ctx.outputLatency) ? ctx.outputLatency : null,
      ignoresSilentMode: this._ignoresSilentMode,
      audioSessionAvailable: !!s,
    };
  }

  /** A clear two-note chime, ignoring the per-set switches (for the Sound check). */
  playTestSound() {
    if (!this._isOn) return false;
    this.unlock();                                 // the Sound check button is a user gesture
    if (!this._samples) { this.prepare(); return false; }
    if (!this._samples[SoundCue.teamDone]) return false;
    return this._start(SoundCue.teamDone, 0.8, 0, 0, false);
  }
}

/**
 * The text under "Sound check: play a test chime" (SoundCheckRow.describe in HomeView.swift),
 * adapted to the browser: device volume and output names are not visible to web pages.
 */
export function soundCheckReport(s, played) {
  const lines = [];
  lines.push('Sound effects: ' + (s.enabled ? 'on' : 'OFF (switch on above)'));
  lines.push(`Sounds ready: ${s.soundsReady} of 38` + (s.soundsReady === 0 ? ' — still preparing, tap again' : ''));
  lines.push('Test chime started: ' + (played ? 'yes' : 'no'));
  lines.push('Audio unlocked: ' + (s.unlocked ? 'yes' : 'no — tap the page once, then try again'));
  lines.push('Audio engine running: ' + (s.engineRunning ? 'yes' : `no (${s.contextState})`));
  lines.push(`Session: ${s.category}` + (s.audioSessionAvailable ? ''
    : ' — on iPhone/iPad this browser follows the Ring/Silent switch'));
  lines.push(`Output: ${s.outputs}`);
  lines.push('Device volume: not visible to web pages — make sure it is turned up');
  lines.push(`Sounds started since launch: ${s.started}`);
  if (s.error) lines.push(`Last error: ${s.error}`);
  return lines.join('\n');
}
