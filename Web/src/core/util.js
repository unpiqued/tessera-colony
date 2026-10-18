// Shared helpers. Ports of hash32 (MosaicRaster.swift) and SplitMix64 (LevelGenerator.swift).
// Both must stay bit-exact with the Swift app and Tools/*.py.

/** 32-bit integer hash used for visual jitter and per-ant randomness. */
export function hash32(a, b) {
  let h = (Math.imul(a | 0, 0x9E3779B1) ^ Math.imul(b | 0, 0x85EBCA77)) >>> 0;
  h ^= h >>> 15;
  h = Math.imul(h, 0x2C1B3C6D) >>> 0;
  h ^= h >>> 12;
  h = Math.imul(h, 0x297A2D39) >>> 0;
  h ^= h >>> 15;
  return h >>> 0;
}

const M64 = (1n << 64n) - 1n;

/** Deterministic random numbers (same algorithm as SplitMix64 in Swift and Tools/photo.py). */
export class SplitMix64 {
  constructor(seed) { this.s = BigInt.asUintN(64, BigInt(seed)); }
  next() {
    this.s = (this.s + 0x9E3779B97F4A7C15n) & M64;
    let z = this.s;
    z = ((z ^ (z >> 30n)) * 0xBF58476D1CE4E5B9n) & M64;
    z = ((z ^ (z >> 27n)) * 0x94D049BB133111EBn) & M64;
    return z ^ (z >> 31n);
  }
  /** Uniform in [0, 1). */
  unit() { return Number(this.next() >> 11n) / 9007199254740992; }
  int(n) { return n <= 1 ? 0 : Number(this.next() % BigInt(n)); }
  weighted(weights) {
    let total = 0;
    for (const w of weights) total += w;
    if (total <= 0) return this.int(weights.length);
    let r = this.unit() * total;
    for (let i = 0; i < weights.length; i++) {
      r -= weights[i];
      if (r < 0) return i;
    }
    return weights.length - 1;
  }
  /** Copy (Swift structs are values: `var r2 = rng` copies the state). */
  clone() { const c = new SplitMix64(0); c.s = this.s; return c; }
}

/** FNV-1a style 64-bit mixing shared with Tools/engine.py (hashes are BigInt). */
export const FNV_SEED = 0xCBF29CE484222325n;
export function fnvMix(h, v) {
  return ((h ^ BigInt(v >>> 0)) * 0x100000001B3n) & M64;
}

export function clamp(v, lo, hi) { return v < lo ? lo : v > hi ? hi : v; }

/** Swift-style tuple comparison for arrays of numbers: a > b lexicographically. */
export function tupleGreater(a, b) {
  for (let i = 0; i < a.length; i++) {
    if (a[i] !== b[i]) return a[i] > b[i];
  }
  return false;
}
