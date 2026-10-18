// Port of PhotoLevelBuilder.swift (plus the pixel-decoding sizes of PhotoLibrary.pixels).
//
// Photo -> playable mosaic: centre crop -> tile grid (box average) -> near-white tiles become open
// ground -> k-means colour families in Lab -> merge look-alikes and slivers -> four tones per family
// -> LevelGenerator builds teams and tunnels and replays the solution to prove it works.
//
// Input pixels — PixelImage: straight (non-premultiplied, opaque) RGBA, row 0 at the top. Both the
// Swift shape { width, height, rgba } and the canvas ImageData shape { width, height, data } are
// accepted (rgba/data: Uint8ClampedArray, Uint8Array or a plain array).
//
// In the browser, decode the photo the way PhotoLibrary.pixels does on the iPad:
//   const { width, height } = targetSize(img.naturalWidth, img.naturalHeight);   // long side <= 720
//   fill a width x height canvas with white, drawImage(img, 0, 0, width, height), getImageData.
// pixelsFromImage() below does exactly that. CoreGraphics and canvas resample differently (see its
// comment), so the same photo gives a very similar but not bit-identical mosaic on the two platforms.
//
// Tuples: gridSize -> [gw, gh, aspect]; lab -> [L, a, b]; downsample -> [gw, gh, rgb[]] with
// rgb[i] = [r, g, b]. Result<LevelDefinition, PhotoBuildError> -> { kind: 'success', value } |
// { kind: 'failure', error }; PhotoBuildError -> { kind: 'unreadable' } |
// { kind: 'notEnoughColour', colouredTiles } | { kind: 'generationFailed' }.

import { SplitMix64 } from '../core/util.js';
import { Board } from '../core/board.js';
import { LevelGenerator } from './levelGenerator.js';

/** PhotoLibrary.pixels(from:maxSide:) default: the long side of the decoded photo, in pixels. */
export const PHOTO_MAX_SIDE = 720;

/** Swift Double.rounded() (schoolbook: half away from zero). */
function rounded(x) {
  if (x < 0) return -rounded(-x);
  const f = Math.floor(x);
  return x - f >= 0.5 ? f + 1 : f;
}

/**
 * Size the photo is drawn at before building (PhotoLibrary.pixels): scaled down so the long side is
 * at most `maxSide` (never up), each side rounded and at least 1. Returns { width, height, scale }.
 */
export function targetSize(width, height, maxSide = PHOTO_MAX_SIDE) {
  const scale = Math.min(1, maxSide / Math.max(width, height));
  return {
    width: Math.max(1, rounded(width * scale)),
    height: Math.max(1, rounded(height * scale)),
    scale,
  };
}

/**
 * Browser helper (mirror of PhotoLibrary.pixels): draws `source` (an HTMLImageElement, ImageBitmap,
 * canvas or video frame with the given natural size) onto white at targetSize and returns a
 * PixelImage { width, height, rgba }. Transparent areas become white, as on the iPad.
 * Resampling: UIKit draws with CoreGraphics' default interpolation; canvas uses the browser's
 * smoother ('high' quality is requested here). Both are averaged again into tiles by downsample(),
 * so only tiles on sharp colour edges can come out slightly different.
 * EXIF orientation: browsers apply it when decoding <img>/createImageBitmap (image-orientation:
 * from-image, the default), like UIImage.draw.
 */
export function pixelsFromImage(source, naturalWidth, naturalHeight, maxSide = PHOTO_MAX_SIDE) {
  if (!(naturalWidth > 0 && naturalHeight > 0)) return null;
  const { width, height } = targetSize(naturalWidth, naturalHeight, maxSide);
  let canvas;
  if (typeof OffscreenCanvas !== 'undefined') canvas = new OffscreenCanvas(width, height);
  else if (typeof document !== 'undefined') {
    canvas = document.createElement('canvas');
    canvas.width = width;
    canvas.height = height;
  } else return null;
  const ctx = canvas.getContext('2d', { willReadFrequently: true });
  if (!ctx) return null;
  ctx.fillStyle = '#ffffff';
  ctx.fillRect(0, 0, width, height);
  ctx.imageSmoothingEnabled = true;
  ctx.imageSmoothingQuality = 'high';
  ctx.drawImage(source, 0, 0, width, height);
  const data = ctx.getImageData(0, 0, width, height).data;
  return { width, height, rgba: data };
}

export const PhotoDetail = Object.freeze({
  coarse: 'coarse',
  fine: 'fine',
  veryFine: 'veryFine',
  allCases: Object.freeze(['coarse', 'fine', 'veryFine']),
  id(d) { return d; },
  targetTiles(d) {
    switch (d) {
      case 'coarse': return 1600;
      case 'fine': return 3600;
      case 'veryFine': return 6000;
      default: throw new Error(`unknown PhotoDetail ${d}`);
    }
  },
  title(d) {
    switch (d) {
      case 'coarse': return 'Chunky';
      case 'fine': return 'Fine';
      case 'veryFine': return 'Very fine';
      default: throw new Error(`unknown PhotoDetail ${d}`);
    }
  },
});

export const PhotoBuildError = Object.freeze({
  unreadable: Object.freeze({ kind: 'unreadable' }),
  notEnoughColour(colouredTiles) { return { kind: 'notEnoughColour', colouredTiles }; },
  generationFailed: Object.freeze({ kind: 'generationFailed' }),

  message(e) {
    switch (e.kind) {
      case 'unreadable':
        return "That image couldn't be read. Try another photo.";
      case 'notEnoughColour':
        return e.colouredTiles === 0
          ? 'That photo is white or near-white all over, so there is nothing for the ants to carry. Try a photo with more colour.'
          : `Only ${e.colouredTiles} coloured tiles are left after the white areas are removed — not enough for a puzzle. Try a more colourful photo or a finer grid.`;
      case 'generationFailed':
        return "The colony couldn't plan a solvable puzzle for this photo. Try a different detail level.";
      default:
        return 'Something went wrong.';
    }
  },
});

function d2(a, b) {
  const x = a[0] - b[0], y = a[1] - b[1], z = a[2] - b[2];
  return x * x + y * y + z * z;
}

export const PhotoLevelBuilder = Object.freeze({
  minColouredTiles: 24,

  /** Tile grid for a photo: [gw, gh, aspect] (aspect clamped to 0.6...1.5). */
  gridSize(width, height, tiles) {
    const aspect = Math.min(1.5, Math.max(0.6, width / Math.max(1, height)));
    const gw = rounded(Math.sqrt(tiles * aspect));
    const gh = rounded(tiles / Math.max(1, gw));
    return [Math.max(8, Math.min(90, gw)), Math.max(8, Math.min(100, gh)), aspect];
  },

  /** sRGB (0...255) -> CIE Lab (D65): [L, a, b]. */
  lab(r, g, b) {
    const lin = c => {
      const v = c / 255;
      return v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
    };
    const lr = lin(r), lg = lin(g), lb = lin(b);
    const x = (lr * 0.4124 + lg * 0.3576 + lb * 0.1805) / 0.95047;
    const y = lr * 0.2126 + lg * 0.7152 + lb * 0.0722;
    const z = (lr * 0.0193 + lg * 0.1192 + lb * 0.9505) / 1.08883;
    const f = t => (t > 0.008856 ? Math.cbrt(t) : 7.787 * t + 16.0 / 116.0);
    const fx = f(x), fy = f(y), fz = f(z);
    return [116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)];
  },

  isNearWhite(l) {
    const c = Math.sqrt(l[1] * l[1] + l[2] * l[2]);
    return (l[0] > 90 && c < 15) || l[0] > 95;
  },

  /** Box-averaged colour of every tile after a centre crop. Returns [gw, gh, rgb triples]. */
  downsample(img, tiles) {
    const px = img.rgba || img.data;
    const [gw, gh, aspect] = PhotoLevelBuilder.gridSize(img.width, img.height, tiles);
    let x0 = 0, y0 = 0, w = img.width, h = img.height;
    const current = w / h;
    if (current > aspect) {
      const cw = Math.trunc(h * aspect);
      x0 = Math.trunc((w - cw) / 2);
      w = cw;
    } else if (current < aspect) {
      const ch = Math.trunc(w / aspect);
      y0 = Math.trunc((h - ch) / 2);
      h = ch;
    }
    const out = [];
    for (let ty = 0; ty < gh; ty++) {
      const ya = Math.trunc(ty * h / gh);
      const yb = Math.max(ya + 1, Math.trunc((ty + 1) * h / gh));
      for (let tx = 0; tx < gw; tx++) {
        const xa = Math.trunc(tx * w / gw);
        const xb = Math.max(xa + 1, Math.trunc((tx + 1) * w / gw));
        let sr = 0, sg = 0, sb = 0, n = 0;
        for (let y = ya; y < yb; y++) {
          const row = (y + y0) * img.width;
          for (let x = xa; x < xb; x++) {
            const o = (row + x + x0) * 4;
            sr += px[o];
            sg += px[o + 1];
            sb += px[o + 2];
            n += 1;
          }
        }
        out.push([sr / n, sg / n, sb / n]);
      }
    }
    return [gw, gh, out];
  },

  /**
   * Builds a photo level. detail: PhotoDetail value; seed: UInt64 (BigInt or number).
   * Returns { kind: 'success', value: LevelDefinition } or { kind: 'failure', error: PhotoBuildError }.
   */
  build(image, detail, seed, id, title) {
    const px = image && (image.rgba || image.data);
    if (!(image && px && image.width > 1 && image.height > 1 && px.length >= image.width * image.height * 4)) {
      return { kind: 'failure', error: PhotoBuildError.unreadable };
    }
    const seed64 = BigInt.asUintN(64, BigInt(seed));
    const [gw, gh, rgb] = PhotoLevelBuilder.downsample(image, PhotoDetail.targetTiles(detail));
    const labs = rgb.map(c => PhotoLevelBuilder.lab(c[0], c[1], c[2]));
    const coloured = [];
    for (let i = 0; i < labs.length; i++) if (!PhotoLevelBuilder.isNearWhite(labs[i])) coloured.push(i);
    const n = coloured.length;
    if (n < PhotoLevelBuilder.minColouredTiles) {
      return { kind: 'failure', error: PhotoBuildError.notEnoughColour(n) };
    }

    // k-means on (L/2, a, b) so hue and chroma decide families, lightness decides tones
    const pts = coloured.map(i => [labs[i][0] * 0.5, labs[i][1], labs[i][2]]);
    const rng = new SplitMix64(seed64);
    const k0 = Math.min(6, Math.max(1, Math.trunc(n / 40)));
    const cents = [pts[rng.int(n)].slice()];
    while (cents.length < k0) {
      const dist = new Float64Array(n);
      let total = 0.0;
      for (let i = 0; i < n; i++) {
        let best = Infinity;
        for (const c of cents) { const d = d2(pts[i], c); if (d < best) best = d; }
        dist[i] = best;
        total += best;
      }
      if (total <= 0) break;
      let r = rng.unit() * total;
      let pick = n - 1;
      for (let i = 0; i < n; i++) {
        r -= dist[i];
        if (r < 0) { pick = i; break; }
      }
      cents.push(pts[pick].slice());
    }
    const assign = new Array(n).fill(0);
    for (let iteration = 0; iteration < 13; iteration++) {
      for (let i = 0; i < n; i++) {
        let best = 0;
        let bd = Infinity;
        for (let j = 0; j < cents.length; j++) {
          const d = d2(pts[i], cents[j]);
          if (d < bd) { bd = d; best = j; }
        }
        assign[i] = best;
      }
      if (iteration === 12) break;
      const sums = cents.map(() => [0, 0, 0]);
      const counts = new Array(cents.length).fill(0);
      for (let i = 0; i < n; i++) {
        const j = assign[i];
        sums[j][0] += pts[i][0]; sums[j][1] += pts[i][1]; sums[j][2] += pts[i][2];
        counts[j] += 1;
      }
      for (let j = 0; j < cents.length; j++) {
        if (counts[j] > 0) cents[j] = [sums[j][0] / counts[j], sums[j][1] / counts[j], sums[j][2] / counts[j]];
      }
    }
    // merge look-alike families and slivers (< 3% of tiles)
    const counts = new Array(cents.length).fill(0);
    for (const j of assign) counts[j] += 1;
    let alive = [];
    for (let j = 0; j < cents.length; j++) if (counts[j] > 0) alive.push(j);
    const sliver = Math.max(8.0, 0.03 * n);
    while (alive.length > 1) {
      let best = null;
      for (let i = 0; i < alive.length; i++) {
        for (let j = i + 1; j < alive.length; j++) {
          const a = alive[i], b = alive[j];
          const d = Math.sqrt(d2(cents[a], cents[b]));
          const small = Math.min(counts[a], counts[b]) < sliver;
          if (d < 16 || small) {
            if (best === null || d < best[0]) best = [d, a, b];
          }
        }
      }
      if (best === null) break;
      const a = best[1], b = best[2];
      const t = counts[a] + counts[b];
      cents[a] = [(cents[a][0] * counts[a] + cents[b][0] * counts[b]) / t,
        (cents[a][1] * counts[a] + cents[b][1] * counts[b]) / t,
        (cents[a][2] * counts[a] + cents[b][2] * counts[b]) / t];
      counts[a] = t;
      counts[b] = 0;
      for (let i = 0; i < n; i++) if (assign[i] === b) assign[i] = a;
      alive = alive.filter(v => v !== b);
    }
    const remap = new Map();
    alive.forEach((old, newIndex) => remap.set(old, newIndex));
    const family = assign.map(v => (remap.has(v) ? remap.get(v) : 0));
    const k = alive.length;

    // four tones per family by lightness quartile (tone 0 = lightest)
    const tone = new Array(n).fill(0);
    const tones = [];
    let names = [];
    for (let f = 0; f < k; f++) {
      const members = [];
      for (let i = 0; i < n; i++) if (family[i] === f) members.push(i);
      // Swift's sort is stable, like Array.prototype.sort: equal lightness keeps tile order.
      members.sort((p, q) => {
        const lp = labs[coloured[p]][0], lq = labs[coloured[q]][0];
        return lp > lq ? -1 : lq > lp ? 1 : 0;
      });
      const famTones = [];
      let mean = [0.0, 0.0, 0.0];
      for (const m of members) { const c = rgb[coloured[m]]; mean[0] += c[0]; mean[1] += c[1]; mean[2] += c[2]; }
      const cnt = Math.max(1, members.length);
      mean = [mean[0] / cnt, mean[1] / cnt, mean[2] / cnt];
      for (let t = 0; t < 4; t++) {
        const lo = Math.trunc(members.length * t / 4);
        const hi = Math.trunc(members.length * (t + 1) / 4);
        let c = [0.0, 0.0, 0.0];
        if (hi > lo) {
          for (let mi = lo; mi < hi; mi++) {
            const m = members[mi];
            tone[m] = t;
            const p = rgb[coloured[m]];
            c[0] += p[0]; c[1] += p[1]; c[2] += p[2];
          }
          const q = hi - lo;
          c = [c[0] / q, c[1] / q, c[2] / q];
        } else {
          c = mean;
        }
        famTones.push(PhotoLevelBuilder.hexColor(c));
      }
      tones.push(famTones);
      names.push(PhotoLevelBuilder.colourName(PhotoLevelBuilder.lab(mean[0], mean[1], mean[2])));
    }
    names = PhotoLevelBuilder.uniquified(names);

    // art rows ("." = open ground where the photo was white)
    const grid = new Array(gw * gh).fill(-1);
    coloured.forEach((idx, m) => { grid[idx] = family[m] * 4 + tone[m]; });
    const letters = 'abcdefghijklmnopqrstuvwx';
    const rows = [];
    for (let y = 0; y < gh; y++) {
      let s = '';
      for (let x = 0; x < gw; x++) {
        const v = grid[y * gw + x];
        s += v < 0 ? '.' : letters[v];
      }
      rows.push(s);
    }
    const palette = { names, tones };
    const board = new Board(rows);
    const gen = LevelGenerator.generate(board, seed64 ^ 0xC0FFEEn);
    if (!gen) return { kind: 'failure', error: PhotoBuildError.generationFailed };
    const used = gen.maxChambersUsed;      // most teams waiting at once in the planned solution
    const level = {
      id, title,
      subtitle: `Your photo · ${k} colour${k === 1 ? '' : 's'}`,
      art: rows, palette, tunnels: gen.tunnels,
      chambersGentle: used + 4, chambersClassic: used + 2, chambersExpert: used + 1,
      solution: gen.solution, goldenClaimsPerMove: [], goldenClaimsHash: 0n,
      goldenFinalStateHash: 0n, isPhoto: true,
      carelessWins: [], greedyWins: [], isChallenge: false, pack: 'main',
    };
    return { kind: 'success', value: level };
  },

  /** [r, g, b] doubles -> 0xRRGGBB (rounded half away from zero, clamped to 0...255). */
  hexColor(c) {
    const r = Math.max(0, Math.min(255, rounded(c[0])));
    const g = Math.max(0, Math.min(255, rounded(c[1])));
    const b = Math.max(0, Math.min(255, rounded(c[2])));
    return ((r << 16) | (g << 8) | b) >>> 0;
  },

  /** A friendly name for VoiceOver ("Blue", "Dark green", ...). Not shown on pieces. */
  colourName(l) {
    const c = Math.sqrt(l[1] * l[1] + l[2] * l[2]);
    if (c < 12) {
      if (l[0] > 75) return 'Silver';
      if (l[0] > 40) return 'Grey';
      return 'Charcoal';
    }
    let h = Math.atan2(l[2], l[1]) * 180 / Math.PI;
    if (h < 0) h += 360;
    let name;
    if (h >= 0 && h < 20) name = 'Pink';
    else if (h >= 20 && h < 50) name = 'Red';
    else if (h >= 50 && h < 75) name = l[0] < 50 ? 'Brown' : 'Orange';
    else if (h >= 75 && h < 100) name = l[0] < 55 ? 'Olive' : 'Gold';
    else if (h >= 100 && h < 160) name = 'Green';
    else if (h >= 160 && h < 220) name = 'Teal';
    else if (h >= 220 && h < 290) name = 'Blue';
    else if (h >= 290 && h < 330) name = 'Violet';
    else name = 'Magenta';
    if (l[0] < 35 && name !== 'Brown' && name !== 'Olive') name = 'Dark ' + name.toLowerCase();
    else if (l[0] > 80) name = 'Pale ' + name.toLowerCase();
    return name;
  },

  uniquified(names) {
    const seen = new Map();
    return names.map(n => {
      const c = (seen.get(n) || 0) + 1;
      seen.set(n, c);
      return c === 1 ? n : `${n} ${c}`;
    });
  },
});
