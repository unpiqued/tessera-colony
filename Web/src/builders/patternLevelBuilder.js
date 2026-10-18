// Port of PatternLevelBuilder.swift.
//
// Pattern mosaics: a fresh level from a seed. Inside the same checkered frame, each seed picks one
// of five different layouts — a rosette (petals, bead ring, scallops, lattice), a starburst, fish
// scales, a six-way kaleidoscope of random shapes, or striped ribbons over polka dots — so new
// patterns are new designs, not recoloured copies. Each tile's colour family comes straight from a
// formula (mirror of Tools/pattern.py), and LevelGenerator plans teams and tunnels and replays the
// plan, so every pattern level is proven solvable before it is offered.
//
// Seeds are UInt64 → BigInt (numbers are accepted). design(seed) returns { rows, layout }
// (the Swift labelled tuple). Floating-point expressions are kept in the Swift order on purpose.

import { SplitMix64 } from '../core/util.js';
import { Board } from '../core/board.js';
import { LevelGenerator } from './levelGenerator.js';

const M64 = (1n << 64n) - 1n;

/**
 * GeneratedPalette.builtIn (LevelData.swift): the palette every built-in and pattern mosaic uses.
 * Kept here so the builders run stand-alone in a Worker; equal to data/levels.json "palette".
 */
export const builtInPalette = Object.freeze({
  names: Object.freeze(['Lapis', 'Saffron', 'Fern', 'Ember', 'Umber', 'Pearl']),
  tones: Object.freeze([
    Object.freeze([0xAED6F4, 0x7DB9E8, 0x4A8FD1, 0x2A5FA8]),
    Object.freeze([0xFFE36A, 0xFFCA2C, 0xF7AE0E, 0xE08E00]),
    Object.freeze([0xA8DB86, 0x74BD4E, 0x46983A, 0x276A2C]),
    Object.freeze([0xFF9A7E, 0xF76A43, 0xDE4527, 0xB52A18]),
    Object.freeze([0x8E6547, 0x6E4A30, 0x533421, 0x3A2315]),
    Object.freeze([0xFFFEFA, 0xEEEBE3, 0xD9D5CA, 0xBDB8AC]),
  ]),
});

const width = 46;
const height = 52;
const bayer = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]];
const LETTERS = 'abcdefghijklmnopqrstuvwx';
const PI = Math.PI;

function pick(rng, n) { return rng.int(n); }
/** Floor modulo (the Python mirror uses Python's %, which floors). */
function fmod(a, n) { return a - n * Math.floor(a / n); }
function imod(a, n) { return ((a % n) + n) % n; }
/** Swift Int(Double): truncates toward zero. */
const toInt = Math.trunc;

// MARK: - the other layouts (mirrors of starburst / fish_scales / kaleidoscope / ribbons in pattern.py)

function starburst(r, a, field, accent, petals, ring, centre, nPts, rOut, rIn, nRays) {
  const sector = imod(toInt(Math.floor((a + PI) / (2 * PI) * nRays)), 2);
  let fam = sector === 1 ? accent : field;
  let shade = (sector === 1 ? 0.3 : 0.2) + 0.4 * Math.min(1.0, r / 32.0);
  const t = fmod((a + PI) / (2 * PI) * nPts, 1.0);
  const pt = Math.abs(2 * t - 1);
  const radius = rIn + (rOut - rIn) * Math.pow(pt, 1.5);
  if (radius <= r && r < radius + 1.4) { fam = ring; shade = 0.8; }
  if (r < radius) {
    fam = petals;
    shade = 0.15 + 0.55 * r / radius + (t < 0.5 ? 0.2 : 0.0);
  }
  if (Math.abs(r - rIn * 0.55) < 0.9) { fam = ring; shade = 0.3; }
  if (r < rIn * 0.4) { fam = centre; shade = 0.1 + 0.7 * r / (rIn * 0.4); }
  return [fam, shade];
}

function fishScales(x, y, field, bandFams, R, bands, phase, moon) {
  const px0 = x, py = y;
  const dm = Math.sqrt((px0 - moon[0]) * (px0 - moon[0]) + (py - moon[1]) * (py - moon[1]));
  if (dm < moon[2]) return [field, 0.1 + 0.5 * dm / moon[2]];
  if (dm < moon[2] + 1.2) return [bandFams[0], 0.9];
  const px = px0 + phase * R / 4.0;
  const stepY = R * 0.5;
  const rowsN = toInt(height / stepY) + 3;
  let j = rowsN;
  while (j >= -1) {
    const sy = j * stepY;
    if (py > sy + 0.01) { j -= 1; continue; }
    const off = imod(j, 2) === 1 ? R : 0.0;
    const i0 = toInt(Math.floor((px - off) / (2 * R)));
    for (const i of [i0, i0 + 1]) {
      const sx = i * 2 * R + off;
      const d = Math.sqrt((px - sx) * (px - sx) + (py - sy) * (py - sy));
      if (d < R) {
        const bw = R / bands;
        const band = toInt(d / bw);
        const fam = bandFams[imod(j, 2) * 2 + band % 2];
        return [fam, 0.15 + 0.6 * fmod(d, bw) / bw];
      }
    }
    j -= 1;
  }
  return [field, 0.3];
}

function kaleidoscope(dx, dy, r, field, ring, bandFams, blobs) {
  const hexd = Math.max(Math.abs(dy), Math.abs(dy) * 0.5 + Math.abs(dx) * Math.sqrt(3.0) / 2);
  if (hexd > 21.5) {
    const on = imod(toInt(Math.floor(r / 3.0)), 2) === 0;
    return [field, on ? 0.25 : 0.55];
  }
  if (hexd > 20.0) return [ring, 0.7];
  const a = Math.atan2(dy, dx);
  let af = fmod(a, PI / 3);
  if (af > PI / 6) af = PI / 3 - af;
  const px = r * Math.cos(af), py = r * Math.sin(af);
  let fam = field;
  let shade = 0.1 + 0.5 * r / 22.0;
  for (const b of blobs) {
    const d = Math.sqrt((px - b.x) * (px - b.x) + (py - b.y) * (py - b.y));
    if (d < b.r) { fam = bandFams[b.f]; shade = 0.15 + 0.6 * d / b.r; }
  }
  return [fam, shade];
}

function ribbons(x, y, dx, dy, field, accent, centre, petals, ring, sp, dotR, w, angle1, angle2, knot, period, dots) {
  const gx = x % sp, gy = y % sp;
  const half = (sp - 1) / 2.0;
  const ex = Math.abs(gx - half), ey = Math.abs(gy - half);
  let inDot;
  let dd;
  if (dots === 0) {
    dd = Math.sqrt(ex * ex + ey * ey); inDot = dd < dotR;
  } else if (dots === 1) {
    inDot = ex + ey < dotR * 1.3; dd = (ex + ey) / 1.3;
  } else {
    inDot = Math.min(ex, ey) < 0.6 && Math.max(ex, ey) < dotR + 0.4; dd = Math.max(ex, ey);
  }
  const qx = dx - knot[0], qy = dy - knot[1];
  const r = Math.sqrt(qx * qx + qy * qy);
  let fam = field;
  let shade = 0.2 + 0.2 * Math.min(1.0, r / 30.0);
  if (inDot) {
    fam = (Math.floor(x / sp) + Math.floor(y / sp)) % 2 === 0 ? accent : centre;
    shade = 0.15 + 0.5 * dd / Math.max(dotR, 0.1);
  }
  const a1 = angle1 * PI / 8.0;
  const a2 = a1 + (2 + angle2) * PI / 8.0;
  const along1 = qx * Math.cos(a1) + qy * Math.sin(a1), across1 = -qx * Math.sin(a1) + qy * Math.cos(a1);
  const along2 = qx * Math.cos(a2) + qy * Math.sin(a2), across2 = -qx * Math.sin(a2) + qy * Math.cos(a2);
  if (Math.abs(across1) < w) {
    fam = petals;
    shade = imod(toInt(Math.floor(along1 / period)), 2) === 0 ? 0.2 : 0.6;
    if (Math.abs(across1) > w - 0.9) shade = 0.9;
  }
  if (Math.abs(across2) < w) {
    fam = ring;
    shade = imod(toInt(Math.floor(along2 / period)), 2) === 0 ? 0.2 : 0.6;
    if (Math.abs(across2) > w - 0.9) shade = 0.9;
  }
  if (r < w * 1.5) { fam = centre; shade = 0.1 + 0.6 * r / (w * 1.5); }
  if (Math.abs(r - w * 1.5) < 0.8) { fam = accent; shade = 0.8; }
  return [fam, shade];
}

export const PatternLevelBuilder = Object.freeze({
  width,
  height,
  bayer,
  layoutNames: Object.freeze(['Rosette', 'Starburst', 'Fish scales', 'Kaleidoscope', 'Ribbons']),
  /** Makes seed 1 the rosette (the golden picture the self-test compares). */
  layoutOffset: 4,

  rows(seed) { return PatternLevelBuilder.design(seed).rows; },

  /** The pattern's rows and the name of its layout: { rows, layout }. */
  design(seed) {
    const rng = new SplitMix64(BigInt.asUintN(64, BigInt(seed)));
    const fams = [0, 1, 2, 3, 4, 5];
    let i = fams.length - 1;
    while (i > 0) {
      const j = pick(rng, i + 1);
      const tmp = fams[i]; fams[i] = fams[j]; fams[j] = tmp;
      i -= 1;
    }
    const frame = fams[0], field = fams[1], petals = fams[2], ring = fams[3], centre = fams[4], accent = fams[5];
    const nPetals = 5 + pick(rng, 8);
    const petalK = [0.8, 1.4, 2.2][pick(rng, 3)];
    const rPetal = 16.0 + pick(rng, 4);
    const rInner = rPetal * (0.5 + 0.08 * pick(rng, 3));
    const rRing = 5.5 + pick(rng, 3);
    const rCentre = 2.6 + pick(rng, 3) * 0.6;
    const nBeads = 14 + 2 * pick(rng, 6);
    const nScallops = 2 * nPetals;
    const lattice = pick(rng, 3);
    const twist = (pick(rng, 5) - 2) * 0.06;
    const layout = (pick(rng, 5) + PatternLevelBuilder.layoutOffset) % 5;
    // parameters of the other layouts (drawn after the rosette's, so seed 1 is unchanged)
    const nPts = 5 + pick(rng, 6);
    const rOut = 17.0 + pick(rng, 4);
    const rIn = rOut * (0.42 + 0.05 * pick(rng, 3));
    const nRays = 2 * (8 + pick(rng, 5));
    let scaleR = 9.0 + pick(rng, 3);
    const nBlobs = 8 + pick(rng, 5);
    const blobs = [];
    for (let k = 0; k < nBlobs; k++) {
      const rr = 2.0 + pick(rng, 19);
      const ang = pick(rng, 7) * (PI / 6.0) / 6.0;
      const br = 1.5 + 0.5 * pick(rng, 6);
      const bf = pick(rng, 4);
      blobs.push({ x: rr * Math.cos(ang), y: rr * Math.sin(ang), r: br, f: bf });
    }
    const dotSp = 5 + pick(rng, 2);
    const dotR = 1.4 + 0.4 * pick(rng, 2);
    const ribbonW = 3.0 + pick(rng, 3);
    // more variety for fish scales and ribbons (drawn last, so earlier draws are unchanged)
    const fsBands = 3 + pick(rng, 2);
    const fsPhase = pick(rng, 8);
    scaleR += pick(rng, 4) - 1;
    const moonX = 9 + pick(rng, 25);
    const moonY = 9 + pick(rng, 14);
    const moonR = 5 + pick(rng, 4);
    const rbA1 = pick(rng, 8);
    const rbA2 = pick(rng, 4);
    const rbKx = pick(rng, 13) - 6;
    const rbKy = pick(rng, 13) - 6;
    const rbPeriod = 2 + pick(rng, 3);
    const rbDots = pick(rng, 3);
    const bandFams = [petals, ring, accent, centre];
    const w = width, h = height;
    const cx = (w - 1) / 2.0, cy = (h - 1) / 2.0;
    const np = nPetals;
    const moon = [moonX, moonY, moonR];
    const knot = [rbKx, rbKy];
    const corners = [[3, 3], [w - 4, 3], [3, h - 4], [w - 4, h - 4]];
    const out = [];
    for (let y = 0; y < h; y++) {
      let row = '';
      for (let x = 0; x < w; x++) {
        const dx = x - cx, dy = y - cy;
        const r = Math.sqrt(dx * dx + dy * dy);
        const a = Math.atan2(dy, dx) + twist * r / 10.0;
        const dEdge = Math.min(Math.min(x, y), Math.min(w - 1 - x, h - 1 - y));
        let fam;
        let shade;
        if (dEdge === 0) {
          fam = frame; shade = 0.85;
        } else if (dEdge === 1) {
          if ((x + y) % 2 === 0) { fam = frame; shade = 0.3; } else { fam = accent; shade = 0.1; }
        } else if (dEdge === 2) {
          fam = frame; shade = 0.6;
        } else if (layout === 1) {
          [fam, shade] = starburst(r, a, field, accent, petals, ring, centre, nPts, rOut, rIn, nRays);
        } else if (layout === 2) {
          [fam, shade] = fishScales(x, y, field, bandFams, scaleR, fsBands, fsPhase, moon);
        } else if (layout === 3) {
          [fam, shade] = kaleidoscope(dx, dy, r, field, ring, bandFams, blobs);
        } else if (layout === 4) {
          [fam, shade] = ribbons(x, y, dx, dy, field, accent, centre, petals, ring, dotSp, dotR, ribbonW,
            rbA1, rbA2, knot, rbPeriod, rbDots);
        } else {
          fam = field;
          let on;
          if (lattice === 0) {
            const s1 = (Math.abs(dx) + Math.abs(dy)) % 6;   // truncatingRemainder
            const s2 = Math.abs(dx - dy) % 6;
            on = s1 < 1 || s2 < 1;
          } else if (lattice === 1) {
            on = (x + y) % 5 === 0 || (x - y) % 5 === 0;
          } else {
            on = x % 5 === 0 || y % 5 === 0;
          }
          shade = (on ? 0.75 : 0.2) + 0.15 * Math.min(1.0, r / 30.0);
          for (const [qx, qy] of corners) {
            const ex = x - qx, ey = y - qy;
            const qr = Math.sqrt(ex * ex + ey * ey);
            if (qr < 6.5) {
              if (qr < 4.5) { fam = ring; shade = 0.25 + 0.1 * qr; } else { fam = accent; shade = 0.4; }
            }
          }
          const sr = rPetal + 2.2;
          let seg = (a + PI) / (2 * PI) * nScallops;
          seg -= Math.floor(seg);
          const bump = 1.3 * Math.sin(PI * seg);
          if (sr - 0.6 < r && r < sr + bump) {
            fam = accent; shade = 0.2 + 0.5 * (r - sr + 0.6) / 2.0;
          }
          const lobe = Math.pow(Math.abs(Math.cos(np * a / 2.0)), petalK);
          const pr = rPetal * (0.42 + 0.58 * lobe);
          if (r < pr) {
            fam = petals;
            shade = 0.15 + 0.75 * (r / pr);
            if (Math.abs(Math.sin(np * a)) < 0.1 && r > rRing + 1) shade = 1.0;
          }
          const lobe2 = Math.pow(Math.abs(Math.cos(np * (a + PI / np) / 2.0)), petalK);
          const pr2 = rInner * (0.5 + 0.5 * lobe2);
          if (r < pr2) {
            fam = accent; shade = 0.1 + 0.6 * r / pr2;
          }
          if (Math.abs(r - rRing) < 1.2) {
            fam = ring;
            const bead = toInt(((a + PI) / (2 * PI)) * nBeads) % 2;
            shade = bead !== 0 ? 0.15 : 0.75;
          }
          if (r < rCentre) {
            fam = centre !== ring ? centre : petals;
            shade = 0.1 + 0.8 * r / rCentre;
          }
        }
        shade = Math.min(1.0, Math.max(0.0, shade));
        const dth = (bayer[y % 4][x % 4] / 16.0 - 0.47) * 0.85;
        const tone = Math.min(3, Math.max(0, toInt(Math.floor(shade * 3.0 + 0.5 + dth))));
        row += LETTERS[fam * 4 + tone];
      }
      out.push(row);
    }
    return { rows: out, layout: PatternLevelBuilder.layoutNames[layout] };
  },

  /**
   * Builds a playable, verified pattern level (LevelDefinition-shaped plain object), or null.
   * Tries a few seeds if planning ever fails. `palette` is an addition for the port (defaults to
   * GeneratedPalette.builtIn, as in Swift).
   */
  build(seed, number, palette = builtInPalette) {
    let s = BigInt.asUintN(64, BigInt(seed));
    for (let k = 0; k < 5; k++) {
      const d = PatternLevelBuilder.design(s);
      const art = d.rows;
      const board = new Board(art);
      const plan = LevelGenerator.generate(board, s ^ 0x5EEDn);
      if (plan) {
        const used = plan.maxChambersUsed;
        return {
          id: `pattern-${s}`, title: `Pattern ${number}`,
          subtitle: `Generated pattern · ${d.layout} · seed ${s % 100000n}`,
          art, palette, tunnels: plan.tunnels,
          chambersGentle: used + 4, chambersClassic: used + 2, chambersExpert: used + 1,
          solution: plan.solution, goldenClaimsPerMove: [], goldenClaimsHash: 0n,
          goldenFinalStateHash: 0n, isPhoto: true,
          carelessWins: [], greedyWins: [], isChallenge: false, pack: 'main',
        };
      }
      s = (s + 0x9E3779B97F4A7C15n) & M64;
    }
    return null;
  },

  goldenSeed1: Object.freeze([
    'cdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcd',
    'dbvbvbvbvbvbvbvbvbvbvbvbvbvbvbvbvbvbvbvbvbvbvc',
    'cubcccbcccbcccbcccbcccbcccbcccbcccbcccbcccbcbd',
    'dbcjjjkkwvhffffgffffhffffhffffhffffhwvkkkjjcvd',
    'cucjjjjkvvgffffhffffgffffhffffgffffhvvkkjjjcbd',
    'dbcjkjkkvvhhhghghghghghghghghghhhghhvvkkkjkcvc',
    'cubkjkkvvfgffffhfffwvwvvvwvfffgffffhfvvkkkjcbd',
    'dbckkkvvwfhffffgfvvvvffffvvvwfhffffgfvvvkkkcvd',
    'cucvvvvvffgffwvvufffgfffehffevvvvffhffvvvvvcbd',
    'dbcvvvffffhwwvfgffffhffffgffffhfvvwgffffvvwcvc',
    'cubhghghghvvuhghghghghghopopopghgvvwghghghgcbd',
    'dbcffhfffvvffffgffffhffopopppppffffvwfffhffcvd',
    'cucffhffvvgfeffhefffgfopooopopofeffhvwffgffcbd',
    'dbcffgffvfhffffgffffhfpooopopopffffgfvffhffcvc',
    'cubffhffffgpopopffefgpoooopoooopffehffffgffcbd',
    'dbcghhwvhgpopopopphghooooopooopphghghgvvhhhcvd',
    'cucffwvfepopooooooofgooononoooopeffheffvvffcbd',
    'dbcffvfffoppoooooopohoooonoooopffffgffffvffcvc',
    'cubfvvffopoopoooooowwkijkpnoooofffehffffvwfcbd',
    'dbcfwvffpppooooooooilkjilkjooopffffgffffvvfcvd',
    'cucwvhghgpooooopnoijkkijkkijwoghggghghghgvwcbd',
    'dbcwvgfffopooooookliwvwvnwjkkwpopopopfffhvwcvc',
    'cubwvhffffoooonoijkwvvvvvwvkijooooooopefgvvcbd',
    'dbcvvgffffhopooojiwwwvttvvwvjioooooopopfhvwcvd',
    'cucvehffefgfoookkkvvvsrssvvwkkkonoooooopgfvcbd',
    'dbcghghghghghgpkkkwvtsrrsswwkklooooooopphghcvc',
    'cubffhffffgfffojijvvssrrstvwijionoooopopgffcbd',
    'dbcvfgffffhfpooijiwvwssstvvvjijooooopopphfwcvd',
    'cucwuhffefgpooookkwwvvstvvvwkknonoooopofgvvcbd',
    'dbcvvgffffpoooookkjwwvvvwvwikkoooopopoffhvwcvc',
    'cubwvhghgpoooononjikvvvwnwkjiwooopopohghgvvcbd',
    'dbcwwgfffppooooponlkjilkjilkwohffffgffffhvwcvd',
    'cucfvvffopoooooononkiikkiikonoofeffhefffuvfcbd',
    'dbcfwvffpopopoooooowwilkjpoooopffffgffffvvfcvc',
    'cubffvfffpopooooooopgooononoooofffehffffvffcbd',
    'dbcghwvghppopopopopghooooooooopphghghghvwhhcvd',
    'cucffhvvefopooopopefgooooopoooopeffhefuvgffcbd',
    'dbcffgffffhppoppffffhopooopoooppfffgffffhffcvc',
    'cubffhffvfgfffehffefgfooooooopoffffhfvffgffcbd',
    'dbcffhffwvhffffgffffhfpopopppopffffgvvffhffcvd',
    'cuchghghgwvhghghghghgggpooopopohghgvvhghghgcbd',
    'dbcffgffffwvvffgffffhfffpopppphffvvwffffhffcvc',
    'cubvvvffffgwvvfhffffgffffhffffgfvwvhffffvvvcbd',
    'dbcvwvvvffhffwwvvfffhffffgfffvvvwffgffvvwvvcvd',
    'cuckkkvvvfgffffhevvvufffevuvvfgffffhfvvvkkkcbd',
    'dbckkkkvvghhhghghghvwvwvwvwghghghghhhvwkkkkcvc',
    'cubjjkjkvvgffffhffffgffffhffffgffffhvvkkjkjcbd',
    'dbcjkjkkwvhffffgffffhffffhffffhffffgwvkkkjjcvd',
    'cucjjjjkvvgffffhffffgffffhffffgffffhvvkkjjicbd',
    'dbccccccccccccccccccccccccccccccccccccccccccvc',
    'cububububububububububububububububububububububd',
    'dddcdddcdddcdddcdddcdddcdddcdddcdddcdddcdddcdd',
  ]),
});
