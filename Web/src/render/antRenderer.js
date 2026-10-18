// Port of AntRenderer.swift: AntSpriteCache (pre-rendered cartoon ant bodies, one per tile colour)
// and AntRenderer (draws every visible ant in a few batched passes onto a CanvasRenderingContext2D).

import { AntGeometry } from './antScheduler.js';
import { makeCanvas } from './canvas.js';

const TWO_PI = 2 * Math.PI;

/**
 * Pre-rendered cartoon ant bodies, one per tile colour. Each body is shaded with radial
 * gradients, outlined, and has big eyes and antennae; legs are drawn live (see AntRenderer)
 * so the feet can plant and lift in step with the ground speed.
 *
 * Web addition: besides the Swift 72 px/cell sprite, smaller copies (36 and 18 px/cell) are drawn
 * from the same vector geometry, so ants shown a few device pixels long are not minified 4-8x by
 * bilinear filtering (which shimmers). AntRenderer picks the smallest one at least as sharp as needed.
 */
export class AntSpriteCache {
  /** Sprite extent in cell units (ant faces +x, origin at the thorax). */
  static minX = -0.9;
  static maxX = 1.0;
  static minY = -0.44;
  static maxY = 0.44;
  static pxPerCell = 72;
  /** Resolutions kept per colour (px per cell), largest first. */
  static levels = [72, 36, 18];

  constructor() {
    this._cache = new Map();   // key: color * 4 + level index
  }

  /** sprite(for:) — the body image for `color` (0xRRGGBB) at `pxPerCell` (one of `levels`). */
  sprite(color, pxPerCell = AntSpriteCache.pxPerCell) {
    let li = AntSpriteCache.levels.indexOf(pxPerCell);
    if (li < 0) li = 0;
    const key = color * 4 + li;
    const c = this._cache.get(key);
    if (c !== undefined) return c;
    const img = AntSpriteCache.render(color, AntSpriteCache.levels[li]);
    if (img) this._cache.set(key, img);
    return img;
  }

  /** The smallest cached resolution that is at least `devicePxPerCell` (or the largest). */
  static levelFor(devicePxPerCell) {
    const L = AntSpriteCache.levels;
    for (let i = L.length - 1; i >= 0; i--) if (L[i] >= devicePxPerCell) return L[i];
    return L[0];
  }

  static get extent() {
    const s = AntSpriteCache;
    return { x: s.minX, y: s.minY, width: s.maxX - s.minX, height: s.maxY - s.minY };
  }

  static _cg(r, g, b, a = 1) {
    const c = v => Math.round(Math.max(0, Math.min(1, v)) * 255);
    return a >= 1 ? `rgb(${c(r)},${c(g)},${c(b)})` : `rgba(${c(r)},${c(g)},${c(b)},${a})`;
  }

  /** render(color:) → canvas (OffscreenCanvas or <canvas>), or null without a canvas implementation. */
  static render(color, pxPerCell = AntSpriteCache.pxPerCell) {
    const S = AntSpriteCache;
    const w = Math.trunc((S.maxX - S.minX) * pxPerCell);
    const h = Math.trunc((S.maxY - S.minY) * pxPerCell);
    const surf = makeCanvas(w, h);
    if (!surf) return null;
    const ctx = surf.ctx;
    // Top-left origin, 1 unit = 1 cell.
    ctx.setTransform(pxPerCell, 0, 0, pxPerCell, -S.minX * pxPerCell, -S.minY * pxPerCell);
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    const cg = S._cg;

    const r = ((color >>> 16) & 0xFF) / 255;
    const g = ((color >>> 8) & 0xFF) / 255;
    const b = (color & 0xFF) / 255;
    const shade = f => [r * f, g * f, b * f];
    const tint = t => [r + (1 - r) * t, g + (1 - g) * t, b + (1 - b) * t];
    const outline = shade(0.32);
    const outlineCSS = cg(outline[0], outline[1], outline[2]);
    const ellipse = (cx, cy, rx, ry) => {
      ctx.beginPath();
      ctx.ellipse(cx, cy, rx, ry, 0, 0, TWO_PI);
    };

    const part = (cx, cy, rx, ry, f) => {
      const lite = tint(0.5);
      const mid = shade(f);
      const deep = shade(f * 0.55);
      ctx.save();
      ellipse(cx, cy, rx, ry);
      ctx.clip();
      const grad = ctx.createRadialGradient(cx - rx * 0.3, cy - ry * 0.4, 0, cx, cy, Math.max(rx, ry) * 1.05);
      grad.addColorStop(0, cg(lite[0], lite[1], lite[2]));
      grad.addColorStop(0.5, cg(mid[0], mid[1], mid[2]));
      grad.addColorStop(1, cg(deep[0], deep[1], deep[2]));
      ctx.fillStyle = grad;
      ctx.fillRect(cx - rx - 0.1, cy - ry - 0.1, 2 * rx + 0.2, 2 * ry + 0.2);
      ctx.restore();
      ctx.strokeStyle = outlineCSS;
      ctx.lineWidth = 0.035;
      ellipse(cx, cy, rx, ry);
      ctx.stroke();
      // glossy highlight
      ctx.fillStyle = cg(1, 1, 1, 0.55);
      ellipse(cx - rx * 0.55 + rx * 0.55 / 2, cy - ry * 0.72 + ry * 0.38 / 2, rx * 0.55 / 2, ry * 0.38 / 2);
      ctx.fill();
    };

    // antennae first (they sit under the head's outline where they attach)
    ctx.strokeStyle = outlineCSS;
    ctx.lineWidth = 0.04;
    for (const s of [-1, 1]) {
      ctx.beginPath();
      ctx.moveTo(0.5, s * 0.09);
      ctx.quadraticCurveTo(0.64, s * 0.3, 0.86, s * 0.24);
      ctx.stroke();
      const tip = shade(0.9);
      ctx.fillStyle = cg(tip[0], tip[1], tip[2]);
      ellipse(0.86, s * 0.24, 0.045, 0.045);
      ctx.fill();
      ctx.strokeStyle = outlineCSS;
      ctx.lineWidth = 0.025;
      ctx.stroke();
      ctx.lineWidth = 0.04;
    }
    part(-0.44, 0, 0.36, 0.27, 1.0);     // gaster
    part(-0.07, 0, 0.08, 0.055, 0.7);    // petiole
    part(0.07, 0, 0.17, 0.12, 0.88);     // thorax
    part(0.4, 0, 0.2, 0.19, 0.92);       // head
    // mandibles
    ctx.strokeStyle = outlineCSS;
    ctx.lineWidth = 0.035;
    for (const s of [-1, 1]) {
      ctx.beginPath();
      ctx.moveTo(0.56, s * 0.06);
      ctx.quadraticCurveTo(0.64, s * 0.07, 0.64, s * 0.01);
      ctx.stroke();
    }
    // big cartoon eyes
    for (const s of [-1, 1]) {
      ctx.fillStyle = cg(1, 1, 1);
      ellipse(0.47, s * 0.085, 0.07, 0.075);
      ctx.fill();
      ctx.strokeStyle = outlineCSS;
      ctx.lineWidth = 0.02;
      ctx.stroke();
      ctx.fillStyle = cg(0.06, 0.04, 0.03);
      ellipse(0.505, s * 0.08, 0.038, 0.038);
      ctx.fill();
      ctx.fillStyle = cg(1, 1, 1, 0.9);
      ellipse(0.49, s * 0.08 - 0.016, 0.014, 0.014);
      ctx.fill();
    }
    return surf.canvas;
  }
}

/** CSS colour of a darker (planted) or lighter (lifted) shade of an ant's colour: legShade(_:_:) */
function legShade(color, f) {
  const r = Math.round(((color >>> 16) & 0xFF) * f);
  const g = Math.round(((color >>> 8) & 0xFF) * f);
  const b = Math.round((color & 0xFF) * f);
  return `rgb(${r},${g},${b})`;
}

function colorCSS(color) { return '#' + ((color & 0xFFFFFF) >>> 0).toString(16).padStart(6, '0'); }

// Per-colour CSS strings are cached (colours are a fixed set of glaze tones).
const SHADE_CACHE = new Map();
function shadeCSS(color, f) {
  const key = color * 8 + (f === 0.55 ? 0 : f === 0.72 ? 1 : f === 0.4 ? 2 : 3);
  let s = SHADE_CACHE.get(key);
  if (s === undefined) {
    s = f === 1 ? colorCSS(color) : legShade(color, f);
    SHADE_CACHE.set(key, s);
  }
  return s;
}

const LEG_BUF = new Float64Array(6 * 7);

/** Draws every visible ant in a few batched passes: shadows, legs, bodies, carried tiles. */
export class AntRenderer {
  /** Distance travelled (cells) per full stride cycle. Gait phase = distance / stride, so a
   *  slower game speed automatically means slower steps, and stance feet stay planted. */
  static strideLength = 0.8;
  static hips = [[0.13, 0.07], [0.05, 0.1], [-0.03, 0.08]];
  static feet = [[0.47, 0.44], [0.05, 0.53], [-0.4, 0.46]];
  /** Front knees bend forward, hind knees backward. */
  static kneeBias = [0.06, 0, -0.06];
  static legShade = legShade;

  /**
   * Leg kinematics of one pose (the loop inside Swift's draw): six legs in the order
   * i = 0..2 × s = -1, +1, each as 7 numbers in world cell units:
   * hip x, y, knee x, y, foot x, y, lift (0 = planted ... 1 = highest). Writes into `out`.
   * Alternating tripods; stance feet move backwards at ground speed (planted).
   */
  static legPoints(p, out = new Float64Array(42)) {
    const stride = AntRenderer.strideLength;
    const hips = AntRenderer.hips, feet = AntRenderer.feet, kneeBias = AntRenderer.kneeBias;
    const k = p.scale;
    const ch = Math.cos(p.heading), sh = Math.sin(p.heading);
    const phase = p.gaitDistance / stride;
    let o = 0;
    for (let i = 0; i < 3; i++) {
      for (let si = 0; si < 2; si++) {
        const s = si === 0 ? -1.0 : 1.0;
        const tripodA = (i === 1) ? (s < 0) : (s > 0);
        let q = phase + (tripodA ? 0 : 0.5);
        q -= Math.floor(q);
        let off;
        let lift = 0.0;
        if (q < 0.5) {
          off = stride / 4 - (q / 0.5) * stride / 2;
        } else {
          const tt = (q - 0.5) / 0.5;
          off = -stride / 4 + AntGeometry.smooth(tt) * stride / 2;
          lift = Math.sin(Math.PI * tt);
        }
        if (!p.moving) { off *= 0.4; lift = 0; }
        const hx = hips[i][0], hy = s * hips[i][1];
        const fx = feet[i][0] + off, fy = s * (feet[i][1] + 0.06 * lift);
        const kx = (hx + fx) / 2 + kneeBias[i];
        const ky = (hy + fy) / 2 + s * (0.2 + 0.1 * lift);
        out[o] = p.x + (hx * ch - hy * sh) * k; out[o + 1] = p.y + (hx * sh + hy * ch) * k;
        out[o + 2] = p.x + (kx * ch - ky * sh) * k; out[o + 3] = p.y + (kx * sh + ky * ch) * k;
        out[o + 4] = p.x + (fx * ch - fy * sh) * k; out[o + 5] = p.y + (fx * sh + fy * ch) * k;
        out[o + 6] = lift;
        o += 7;
      }
    }
    return out;
  }

  /**
   * draw(_:visible:board:cs:sprites:detailed:)
   * @param {CanvasRenderingContext2D} ctx  current transform maps cell*cs units to the canvas
   * @param {{trip: object, pose: object}[]} visible
   * @param {number} [count] number of entries of `visible` to draw (default: all) — lets callers reuse the array
   */
  static draw(ctx, visible, board, cs, sprites, detailed, count = visible.length) {
    if (count === 0) return;
    const lod = detailed && count <= 320;
    const base = ctx.getTransform();
    const B_a = base.a, B_b = base.b, B_c = base.c, B_d = base.d, B_e = base.e, B_f = base.f;
    const devicePx = Math.hypot(B_a, B_b) * cs;
    const level = AntSpriteCache.levelFor(devicePx);
    const shadows = new Path2D();
    // legs are batched per ant colour (a darker shade of the body) so they read on dark soil
    const planted = new Map();
    const lifted = new Map();
    const footDots = new Map();
    const legs = LEG_BUF;
    const getPath = (m, color) => {
      let p = m.get(color);
      if (p === undefined) { p = new Path2D(); m.set(color, p); }
      return p;
    };
    for (let vi = 0; vi < count; vi++) {
      const v = visible[vi];
      const p = v.pose;
      const color = v.trip.color;
      const k = p.scale;
      // soft contact shadow, offset down-right in world space
      const scx = (p.x + 0.05) * cs, scy = (p.y + 0.12) * cs;
      const rx = 0.82 * cs * k, ry = 0.3 * cs * k;
      const chd = Math.cos(p.heading), shd = Math.sin(p.heading);
      shadows.moveTo(scx + rx * chd, scy + rx * shd);
      shadows.ellipse(scx, scy, rx, ry, p.heading, 0, TWO_PI);
      AntRenderer.legPoints(p, legs);
      const pl = getPath(planted, color);
      if (lod) {
        let lf = null, fd = null;
        const r = 0.05 * cs * k;
        for (let o = 0; o < 42; o += 7) {
          if (legs[o + 6] > 0.05) {
            if (lf === null) lf = getPath(lifted, color);
            lf.moveTo(legs[o] * cs, legs[o + 1] * cs);
            lf.lineTo(legs[o + 2] * cs, legs[o + 3] * cs);
            lf.lineTo(legs[o + 4] * cs, legs[o + 5] * cs);
          } else {
            pl.moveTo(legs[o] * cs, legs[o + 1] * cs);
            pl.lineTo(legs[o + 2] * cs, legs[o + 3] * cs);
            const cx = legs[o + 4] * cs, cy = legs[o + 5] * cs;
            pl.lineTo(cx, cy);
            if (fd === null) fd = getPath(footDots, color);
            fd.moveTo(cx + r, cy);
            fd.arc(cx, cy, r, 0, TWO_PI);
          }
        }
      } else {
        for (let o = 0; o < 42; o += 7) {
          pl.moveTo(legs[o] * cs, legs[o + 1] * cs);
          pl.lineTo(legs[o + 4] * cs, legs[o + 5] * cs);
        }
      }
    }
    ctx.fillStyle = 'rgba(0,0,0,0.24)';
    ctx.fill(shadows);
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    ctx.lineWidth = Math.max(0.6, 0.085 * cs);
    for (const [color, path] of planted) {
      ctx.strokeStyle = shadeCSS(color, 0.55);
      ctx.stroke(path);
    }
    if (lod) {
      ctx.lineWidth = Math.max(0.5, 0.065 * cs);
      for (const [color, path] of lifted) {
        ctx.strokeStyle = shadeCSS(color, 0.72);
        ctx.stroke(path);
      }
      for (const [color, path] of footDots) {
        ctx.fillStyle = shadeCSS(color, 0.4);
        ctx.fill(path);
      }
    }

    // bodies (cartoon sprites) with a little sway and bob from the gait
    const S = AntSpriteCache;
    const rx0 = S.minX * cs, ry0 = S.minY * cs, rw = (S.maxX - S.minX) * cs, rh = (S.maxY - S.minY) * cs;
    const stride = AntRenderer.strideLength;
    let carried = null;
    let carriedEdges = null;
    let lastColor = -1, img = null;
    for (let vi = 0; vi < count; vi++) {
      const v = visible[vi];
      const p = v.pose;
      const color = v.trip.color;
      if (color !== lastColor) {
        img = sprites.sprite(color, level);
        lastColor = color;
      }
      const phase = p.gaitDistance / stride;
      const sway = p.moving ? 0.07 * Math.sin(2 * Math.PI * 2 * phase) : 0;
      const bob = p.moving ? 1 + 0.03 * Math.sin(2 * Math.PI * 2 * phase + Math.PI / 2) : 1;
      const lean = p.moving ? 0.0 : 0.06 * Math.sin(Math.PI * p.liftProgress);
      const ch = Math.cos(p.heading), sh = Math.sin(p.heading);
      if (img) {
        const tx = (p.x + ch * lean) * cs, ty = (p.y + sh * lean) * cs;
        const ang = p.heading + sway;
        const kk = p.scale * bob;
        const la = kk * Math.cos(ang), lb = kk * Math.sin(ang);
        // base × translate(tx, ty) × rotate(ang) × scale(kk)
        ctx.setTransform(B_a * la + B_c * lb, B_b * la + B_d * lb, B_a * -lb + B_c * la, B_b * -lb + B_d * la,
          B_a * tx + B_c * ty + B_e, B_b * tx + B_d * ty + B_f);
        if (p.scale < 1) ctx.globalAlpha = 0.35 + 0.65 * p.scale;
        ctx.drawImage(img, rx0, ry0, rw, rh);
        if (p.scale < 1) ctx.globalAlpha = 1;
      }
      // tile: rising from the floor into the jaws, then carried in front of the head
      if (p.liftProgress > 0) {
        const jawX = p.x + ch * 0.72 * p.scale;
        const jawY = p.y + sh * 0.72 * p.scale;
        let tx = jawX, ty = jawY;
        let size = 0.5 * p.scale;
        if (!p.carrying) {
          const tile = v.trip.tile;
          const fx = board.x(tile) + 0.5, fy = board.y(tile) + 0.5;
          const e = p.liftProgress;
          tx = fx + (jawX - fx) * e;
          ty = fy + (jawY - fy) * e;
          size = 0.9 - 0.4 * e;
        }
        const half = size * cs / 2;
        if (carried === null) { carried = new Map(); carriedEdges = new Path2D(); }
        let cp = carried.get(color);
        if (cp === undefined) { cp = new Path2D(); carried.set(color, cp); }
        roundRectPath(cp, tx * cs - half, ty * cs - half, 2 * half, 2 * half, half * 0.3);
        roundRectPath(carriedEdges, tx * cs - half, ty * cs - half, 2 * half, 2 * half, half * 0.3);
      }
    }
    ctx.setTransform(base);
    if (carried !== null) {
      for (const [color, path] of carried) {
        ctx.fillStyle = shadeCSS(color, 1);
        ctx.fill(path);
      }
      ctx.strokeStyle = 'rgba(0,0,0,0.45)';
      ctx.lineWidth = Math.max(0.5, 0.05 * cs);
      ctx.stroke(carriedEdges);
    }
  }
}

/** Path(roundedRect:cornerRadius:) appended to `p` (circular corners). */
export function roundRectPath(p, x, y, w, h, r) {
  const rr = Math.max(0, Math.min(r, w / 2, h / 2));
  p.moveTo(x + rr, y);
  p.lineTo(x + w - rr, y);
  p.arcTo(x + w, y, x + w, y + rr, rr);
  p.lineTo(x + w, y + h - rr);
  p.arcTo(x + w, y + h, x + w - rr, y + h, rr);
  p.lineTo(x + rr, y + h);
  p.arcTo(x, y + h, x, y + h - rr, rr);
  p.lineTo(x, y + rr);
  p.arcTo(x, y, x + rr, y, rr);
  p.closePath();
}
