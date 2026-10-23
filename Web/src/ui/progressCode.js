// Progress codes: a copy-and-paste backup of finished mosaics, high scores, settings and saved
// games. Some browsers forget everything an embedded page stores when they close (Safari and every
// iPhone browser treat the artifact frame as third-party storage, which WebKit makes session-only),
// so the code is how progress survives there — and how it moves to another device anywhere.
// Photo mosaics are left out (each one is a whole picture).
import { SaveStore } from '../core/saveStore.js';

const VERSION = 1;
const CODE_RE = /TC([01])\.([A-Za-z0-9_-]+)/;

function keptKeys() {
  const k = SaveStore.keys;
  return { fixed: [k.settingsKey, k.progressKey, k.highScoreKey], gamePrefix: k.gameKey('') };
}

function toB64url(bytes) {
  let bin = '';
  for (let i = 0; i < bytes.length; i += 0x8000) bin += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
  return btoa(bin).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

function fromB64url(s) {
  const b = s.replace(/-/g, '+').replace(/_/g, '/');
  const bin = atob(b + '==='.slice((b.length + 3) % 4));
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

async function pipe(bytes, stream) {
  return new Uint8Array(await new Response(new Blob([bytes]).stream().pipeThrough(stream)).arrayBuffer());
}

/** Everything worth keeping, as { key: string }. */
export function progressSnapshot(backend) {
  const { fixed, gamePrefix } = keptKeys();
  const data = {};
  const keys = typeof backend.keys === 'function' ? backend.keys() : fixed;
  for (const key of keys) {
    if (!fixed.includes(key) && !key.startsWith(gamePrefix)) continue;
    const v = backend.getItem(key);
    if (v !== null && v !== undefined) data[key] = v;
  }
  return data;
}

/** The progress code for this browser's data ("TC1." + deflated JSON, or "TC0." + plain JSON). */
export async function makeProgressCode(backend) {
  const json = JSON.stringify({ v: VERSION, d: progressSnapshot(backend) });
  const raw = new TextEncoder().encode(json);
  if (typeof CompressionStream !== 'undefined') {
    try { return 'TC1.' + toB64url(await pipe(raw, new CompressionStream('deflate'))); } catch (e) { /* fall through */ }
  }
  return 'TC0.' + toB64url(raw);
}

/** Decodes a pasted code (surrounding text and line breaks are ignored). Throws Error(message). */
export async function readProgressCode(text) {
  const m = String(text || '').replace(/\s+/g, '').match(CODE_RE);
  if (!m) throw new Error("That isn't a progress code. Codes start with TC1. or TC0.");
  let bytes;
  try { bytes = fromB64url(m[2]); } catch (e) { throw new Error('The code is damaged — copy the whole thing and try again.'); }
  if (m[1] === '1') {
    if (typeof DecompressionStream === 'undefined') throw new Error("This browser can't read compressed codes. Try a newer browser.");
    try { bytes = await pipe(bytes, new DecompressionStream('deflate')); } catch (e) { throw new Error('The code is cut short — copy the whole thing and try again.'); }
  }
  let o;
  try { o = JSON.parse(new TextDecoder().decode(bytes)); } catch (e) { throw new Error('The code is damaged — copy the whole thing and try again.'); }
  if (!o || typeof o !== 'object' || typeof o.d !== 'object' || o.d === null) throw new Error("That code doesn't hold any progress.");
  const { fixed, gamePrefix } = keptKeys();
  const data = {};
  for (const [k, v] of Object.entries(o.d)) {
    if ((fixed.includes(k) || k.startsWith(gamePrefix)) && typeof v === 'string') data[k] = v;
  }
  return data;
}

/** How many mosaics a snapshot has finished (for messages). */
export function finishedCount(data) {
  try {
    const p = JSON.parse(data[SaveStore.keys.progressKey] || '{}');
    return p && typeof p === 'object' ? Object.keys(p).length : 0;
  } catch (e) { return 0; }
}

/**
 * Writes a decoded code into storage. Progress, high scores and settings are replaced; saved games
 * in the code are added (games only this browser has are kept).
 */
export function applyProgress(backend, data) {
  const { fixed } = keptKeys();
  for (const key of fixed) if (!(key in data)) backend.removeItem(key);
  for (const [k, v] of Object.entries(data)) backend.setItem(k, v);
}

/**
 * True where the browser keeps an embedded page's storage only until it closes: WebKit (Safari,
 * and every browser on iPhone and iPad) when the page runs in a cross-site frame.
 */
export function storageForgetsOnClose() {
  try {
    let framed = false;
    try { framed = window.self !== window.top && !window.top.location.href; } catch (e) { framed = true; }
    if (!framed) return false;
    return typeof navigator !== 'undefined' && navigator.vendor === 'Apple Computer, Inc.';
  } catch (e) {
    return false;
  }
}
