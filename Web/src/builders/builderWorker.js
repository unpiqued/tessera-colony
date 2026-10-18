// Off-main-thread building of pattern and photo levels (and their difficulty probe).
//
// On the iPad these run in `Task.detached` (AppModel.createPatternLevel / importPhoto /
// measureIfNeeded). In the page they run in a Web Worker made from a blob: URL whose source is the
// separately bundled builder code (tools/build_with_worker.mjs embeds it as JSON in
// <script type="application/json" id="tc-builder-worker">). When Workers are unavailable (no
// Worker/Blob, blob: workers blocked, the script fails to start) every job runs on the main thread
// instead, after yielding once so a "building…" state can paint first.
//
// Usage (page):
//   const builder = createBuilder();                        // once
//   const { level, stats } = await builder.run('pattern', { seed, number, probe: true });
//   const { result } = await builder.run('photo', { image, detail, seed, id, title });
//   const { stats } = await builder.run('probe', { level });
//
// Jobs (runBuild(kind, params), synchronous, results are structured-cloneable):
//   'pattern' {seed, number, probe?}            -> { level: LevelDefinition|null, stats: DifficultyStats|null }
//   'photo'   {image, detail, seed, id, title, probe?}
//                                               -> { result: {kind:'success', value}|{kind:'failure', error}, stats }
//   'probe'   {level, trials?}                  -> { stats }
// seed: BigInt (UInt64) or number; image: PixelImage {width, height, rgba} or ImageData-like
// {width, height, data}; DifficultyStats: { careless: [g, c, e], greedy: [g, c, e] }.

import { PatternLevelBuilder } from './patternLevelBuilder.js';
import { PhotoLevelBuilder } from './photoLevelBuilder.js';
import { DifficultyProbe } from './difficultyProbe.js';

/** id of the <script type="application/json"> element holding the worker bundle's source text. */
export const BUILDER_WORKER_SCRIPT_ID = 'tc-builder-worker';

/** Runs one job synchronously (inside the worker, or on the main thread as the fallback). */
export function runBuild(kind, params) {
  const p = params || {};
  switch (kind) {
    case 'pattern': {
      const level = PatternLevelBuilder.build(p.seed, p.number);
      return { level, stats: level && p.probe ? DifficultyProbe.measure(level, p.trials ?? 10) : null };
    }
    case 'photo': {
      const result = PhotoLevelBuilder.build(p.image, p.detail, p.seed, p.id, p.title);
      const stats = result.kind === 'success' && p.probe ? DifficultyProbe.measure(result.value, p.trials ?? 10) : null;
      return { result, stats };
    }
    case 'probe':
      return { stats: DifficultyProbe.measure(p.level, p.trials ?? 10) };
    default:
      throw new Error(`unknown build kind: ${kind}`);
  }
}

/** Only what DifficultyProbe reads (a level object may carry fields that cannot be cloned). */
function probeFields(level) {
  return {
    art: level.art, tunnels: level.tunnels,
    chambersGentle: level.chambersGentle, chambersClassic: level.chambersClassic, chambersExpert: level.chambersExpert,
  };
}

/** The bundled worker source embedded in the page, or null (not bundled / not in a browser). */
export function builderWorkerSource() {
  if (typeof document === 'undefined') return null;
  const el = document.getElementById(BUILDER_WORKER_SCRIPT_ID);
  if (!el) return null;
  try {
    const s = JSON.parse(el.textContent);
    return typeof s === 'string' && s.length > 0 ? s : null;
  } catch {
    return null;
  }
}

/**
 * A Worker running the builder bundle, made from a blob: URL (the only kind the sandboxed artifact
 * iframe allows), or null when that is impossible here. The URL is revoked once the worker has
 * started (first message) or failed (first error).
 */
export function createBuilderWorker(source = builderWorkerSource()) {
  if (typeof source !== 'string' || source.length === 0) return null;
  if (typeof Worker === 'undefined' || typeof Blob === 'undefined'
      || typeof URL === 'undefined' || typeof URL.createObjectURL !== 'function') return null;
  let url = null;
  try {
    url = URL.createObjectURL(new Blob([source], { type: 'text/javascript' }));
    const worker = new Worker(url);
    const revoke = () => { if (url) { URL.revokeObjectURL(url); url = null; } };
    worker.addEventListener('message', revoke, { once: true });
    worker.addEventListener('error', revoke, { once: true });
    return worker;
  } catch {
    if (url) URL.revokeObjectURL(url);
    return null;
  }
}

/** Lets the browser paint (e.g. a "building…" state) before a long synchronous job. */
function yieldToPaint() {
  return new Promise(resolve => {
    if (typeof requestAnimationFrame === 'function' && typeof document !== 'undefined' && !document.hidden) {
      requestAnimationFrame(() => setTimeout(resolve, 0));
    } else {
      setTimeout(resolve, 0);
    }
  });
}

function runOnMainThread(kind, params) {
  return yieldToPaint().then(() => runBuild(kind, params));
}

/**
 * Sends jobs to the builder worker; falls back to the main thread when there is no worker or it
 * fails to start. `mode` is 'worker', 'starting' or 'main'.
 */
export class BuilderClient {
  /**
   * @param {string|null} [source] worker bundle source (default: the page's embedded copy);
   *   pass null to force main-thread building.
   * @param {{readyTimeoutMs?: number}} [options] how long to wait for the worker to start.
   */
  constructor(source = builderWorkerSource(), options = {}) {
    this._jobs = new Map();
    this._nextId = 1;
    this._ready = false;
    this._worker = source ? createBuilderWorker(source) : null;
    this._readyTimer = null;
    if (!this._worker) return;
    this._worker.addEventListener('message', e => this._onMessage(e.data));
    this._worker.addEventListener('error', e => {
      if (e && typeof e.preventDefault === 'function') e.preventDefault();
      this._fail();
    });
    this._worker.addEventListener('messageerror', () => this._fail());
    const ms = options.readyTimeoutMs ?? 5000;
    this._readyTimer = setTimeout(() => { if (!this._ready) this._fail(); }, ms);
  }

  get mode() { return this._worker ? (this._ready ? 'worker' : 'starting') : 'main'; }

  /** Runs a job (see runBuild). Resolves with its result; rejects if the job itself throws. */
  run(kind, params = {}) {
    const p = kind === 'probe' && params.level ? { ...params, level: probeFields(params.level) } : params;
    if (!this._worker) return runOnMainThread(kind, p);
    return new Promise((resolve, reject) => {
      const id = this._nextId++;
      this._jobs.set(id, { kind, params: p, resolve, reject });
      try {
        // No transfer list: the caller keeps its pixels, so a failed worker can rerun the job here.
        this._worker.postMessage({ id, kind, params: p });
      } catch (err) {
        this._jobs.delete(id);
        runOnMainThread(kind, p).then(resolve, reject);
      }
    });
  }

  terminate() {
    if (this._readyTimer) clearTimeout(this._readyTimer);
    if (this._worker) this._worker.terminate();
    this._worker = null;
    for (const job of this._jobs.values()) job.reject(new Error('builder terminated'));
    this._jobs.clear();
  }

  _onMessage(msg) {
    if (!msg) return;
    if (msg.ready) {
      this._ready = true;
      if (this._readyTimer) { clearTimeout(this._readyTimer); this._readyTimer = null; }
      return;
    }
    const job = this._jobs.get(msg.id);
    if (!job) return;
    this._jobs.delete(msg.id);
    if (msg.ok) job.resolve(msg.result);
    else job.reject(new Error(msg.error));
  }

  /** The worker could not start or died: rerun everything outstanding on the main thread. */
  _fail() {
    if (this._readyTimer) { clearTimeout(this._readyTimer); this._readyTimer = null; }
    if (this._worker) {
      try { this._worker.terminate(); } catch { /* already gone */ }
      this._worker = null;
    }
    const pending = [...this._jobs.values()];
    this._jobs.clear();
    for (const job of pending) runOnMainThread(job.kind, job.params).then(job.resolve, job.reject);
  }
}

/** Convenience: one shared client per page (source defaults to the page's embedded bundle). */
export function createBuilder(source, options) {
  return new BuilderClient(source, options);
}
