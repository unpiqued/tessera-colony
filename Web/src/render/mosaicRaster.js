// Port of MosaicRaster.swift: paints the mosaic into a pixel buffer (one small bevelled tessera per
// tile, no markings) and turns it into a drawable image. Tiles are stamped from pre-rendered
// templates, so a full repaint of ~7,000 cells is a few thousand row copies. Mirrors Tools/render.py
// (same bevel/grout/glaze rules; render.py's jitter and soil noise differ by design, see the tests).
//
// Web notes: `pixels` is an RGBA Uint8ClampedArray; `image` is a canvas (OffscreenCanvas or
// <canvas>) usable with drawImage(), kept up to date by uploading only the cells that changed
// (putImageData with dirty rectangles). In Node (no canvas) `image` stays null.

import { hash32 } from '../core/util.js';
import { Board } from '../core/board.js';
import { GeneratedPalette, LevelPalette } from './palette.js';
import { makeCanvas } from './canvas.js';

/** struct RGB: components 0...255 as doubles. RGB(hex) / RGB.of(r, g, b). */
export function RGB(hex) {
  return { r: (hex >>> 16) & 0xFF, g: (hex >>> 8) & 0xFF, b: hex & 0xFF };
}
RGB.of = (r, g, b) => ({ r, g, b });
RGB.scaled = (c, f) => ({ r: c.r * f, g: c.g * f, b: c.b * f });
RGB.mixed = (c, o, t) => ({ r: c.r * (1 - t) + o.r * t, g: c.g * (1 - t) + o.g * t, b: c.b * (1 - t) + o.b * t });

/** UInt8(max(0, min(255, v))) — truncates like the Swift conversion (Uint8ClampedArray would round). */
const u8 = v => (v <= 0 ? 0 : v >= 255 ? 255 : v | 0);

export class MosaicRaster {
  static soilVariants = 8;
  /** Grout colour of the tile templates (GeneratedPalette.grout). */
  static grout = GeneratedPalette.grout;

  /**
   * init(board:palette:cellPx:open:soil:)
   * @param {Uint8Array} open per cell: 1 = soil (open), 0 = tile
   */
  constructor(board, palette, cellPx, open, soil = GeneratedPalette.soil) {
    this.board = board;
    this.palette = palette;
    this.soil = soil;
    this.cellPx = Math.max(3, cellPx | 0);
    this.width = board.cols * this.cellPx;
    this.height = board.rows * this.cellPx;
    this.pixels = new Uint8ClampedArray(this.width * this.height * 4).fill(255);
    this._px32 = new Uint32Array(this.pixels.buffer);
    /** What each cell currently shows: 1 = soil (open), 0 = tile. Read-only outside. */
    this.shownOpen = new Uint8Array(board.count);
    this._tileTemplates = [];   // (family*4+tone)*4 + jitter   (Uint32Array views, one pixel per element)
    this._soilTemplates = [];   // 8 variants
    this._ghostTemplates = [];  // (family*4+tone)*8 + variant
    this._buildTemplates();
    for (let i = 0; i < board.count; i++) this._paint(i, open[i] ? 1 : 0);
    this._dirty = [];
    this._allDirty = true;
    this._surface = null;
    this._imageData = null;
    /** The picture (canvas) or null without a canvas implementation. */
    this.image = this.makeImage();
  }

  // MARK: templates

  _buildTemplates() {
    const s = this.cellPx;
    const families = Math.max(1, LevelPalette.familyCount(this.palette));
    const jitters = [0.965, 0.988, 1.012, 1.035];
    const view = a => new Uint32Array(a.buffer);
    for (let f = 0; f < families; f++) {
      for (let t = 0; t < 4; t++) {
        const base = RGB(LevelPalette.tone(this.palette, f, t));
        for (let j = 0; j < 4; j++) this._tileTemplates.push(view(MosaicRaster.tileTemplate(base, s, jitters[j])));
      }
    }
    for (let v = 0; v < MosaicRaster.soilVariants; v++) {
      this._soilTemplates.push(view(MosaicRaster.soilTemplate(s, v, null, this.soil)));
    }
    for (let f = 0; f < families; f++) {
      for (let t = 0; t < 4; t++) {
        const base = RGB(LevelPalette.tone(this.palette, f, t));
        for (let v = 0; v < MosaicRaster.soilVariants; v++) {
          this._ghostTemplates.push(view(MosaicRaster.soilTemplate(s, v, base, this.soil)));
        }
      }
    }
  }

  /** tileTemplate(base:s:jitter:) → RGBA Uint8ClampedArray (s*s*4). */
  static tileTemplate(base, s, jitter, groutHex = MosaicRaster.grout) {
    const out = new Uint8ClampedArray(s * s * 4).fill(255);
    const grout = RGB(groutHex);
    const g = Math.max(1, Math.round(s / 12));
    const inner = s - g;
    const b = Math.max(1, Math.round(s / 10));
    const rc = s * 0.16;
    for (let v = 0; v < s; v++) {
      for (let u = 0; u < s; u++) {
        let cr = grout.r, cg = grout.g, cb = grout.b;
        if (u < inner && v < inner) {
          const cxd = Math.min(u + 0.5, (inner - u) - 0.5);
          const cyd = Math.min(v + 0.5, (inner - v) - 0.5);
          const outside = cxd < rc && cyd < rc && (rc - cxd) * (rc - cxd) + (rc - cyd) * (rc - cyd) > rc * rc;
          if (!outside) {
            let f = 1.0;
            if (u < b || v < b) f = 1.16;
            if (u >= inner - b || v >= inner - b) f = 0.80;
            f *= 1.05 - 0.10 * v / inner;
            const k = f * jitter;
            cr = base.r * k; cg = base.g * k; cb = base.b * k;
          }
        }
        const o = (v * s + u) * 4;
        out[o] = u8(cr);
        out[o + 1] = u8(cg);
        out[o + 2] = u8(cb);
        out[o + 3] = 255;
      }
    }
    return out;
  }

  /** soilTemplate(s:variant:ghost:soil:) → RGBA Uint8ClampedArray (s*s*4). ghost: RGB or null. */
  static soilTemplate(s, variant, ghost, soilHex) {
    const out = new Uint8ClampedArray(s * s * 4).fill(255);
    const soil = RGB(soilHex);
    for (let v = 0; v < s; v++) {
      for (let u = 0; u < s; u++) {
        const n = (hash32(variant * 131 + u, v * 7 + variant) & 0xFF) / 255.0;
        let f = 0.92 + 0.16 * n;
        let cr = soil.r * f, cg = soil.g * f, cb = soil.b * f;
        if (n > 0.965) { cr *= 1.3; cg *= 1.3; cb *= 1.3; }
        if (ghost) {
          cr = cr * (1 - 0.14) + ghost.r * 0.14;
          cg = cg * (1 - 0.14) + ghost.g * 0.14;
          cb = cb * (1 - 0.14) + ghost.b * 0.14;
        }
        const o = (v * s + u) * 4;
        out[o] = u8(cr);
        out[o + 1] = u8(cg);
        out[o + 2] = u8(cb);
        out[o + 3] = 255;
      }
    }
    return out;
  }

  // MARK: painting

  _blit(tpl, i) {
    const s = this.cellPx;
    const cols = this.board.cols;
    const cx = (i % cols) * s;
    const cy = ((i / cols) | 0) * s;
    const W = this.width;
    const px = this._px32;
    let src = 0;
    for (let row = 0; row < s; row++) {
      let d = (cy + row) * W + cx;
      for (let u = 0; u < s; u++) px[d++] = tpl[src++];
    }
  }

  _paint(i, open) {
    const board = this.board;
    const fam = board.family[i];
    const x = board.x(i), y = board.y(i);
    const variant = hash32(x, y) % MosaicRaster.soilVariants;
    if (fam < 0) {
      this._blit(this._soilTemplates[variant], i);
    } else {
      const code = fam * 4 + board.tone[i];
      if (open) {
        this._blit(this._ghostTemplates[code * MosaicRaster.soilVariants + variant], i);
      } else {
        const jit = hash32(x + 17, y + 5) & 3;
        this._blit(this._tileTemplates[code * 4 + jit], i);
      }
    }
    this.shownOpen[i] = open ? 1 : 0;
    if (this._dirty && !this._allDirty) this._dirty.push(i);
  }

  /**
   * Bring the picture in line with the scheduler: a tile disappears when its ant lifts it and
   * reappears if an undo returns it. Returns true if the image changed. sync(liftTime:now:)
   */
  sync(liftTime, now) {
    let changed = false;
    const fam = this.board.family;
    const shown = this.shownOpen;
    for (let i = 0, n = this.board.count; i < n; i++) {
      if (fam[i] < 0) continue;
      const open = liftTime[i] <= now ? 1 : 0;
      if (open !== shown[i]) {
        this._paint(i, open);
        changed = true;
      }
    }
    if (changed) this.image = this.makeImage();
    return changed;
  }

  /**
   * The current picture as a canvas (drawImage-able). Uploads only the cells painted since the
   * last call (one putImageData per cell for a few cells, else one call for their bounding box).
   */
  makeImage() {
    if (this._surface === null) {
      this._surface = makeCanvas(this.width, this.height);
      if (!this._surface) { this._surface = undefined; }
      this._allDirty = true;
    }
    if (!this._surface) { this._dirty.length = 0; return null; }
    const ctx = this._surface.ctx;
    if (this._imageData === null) this._imageData = new ImageData(this.pixels, this.width, this.height);
    const img = this._imageData;
    if (this._allDirty) {
      ctx.putImageData(img, 0, 0);
    } else if (this._dirty.length > 0) {
      const s = this.cellPx;
      const cols = this.board.cols;
      const d = this._dirty;
      if (d.length <= 24) {
        for (let k = 0; k < d.length; k++) {
          const i = d[k];
          ctx.putImageData(img, 0, 0, (i % cols) * s, ((i / cols) | 0) * s, s, s);
        }
      } else {
        let x0 = Infinity, y0 = Infinity, x1 = -1, y1 = -1;
        for (let k = 0; k < d.length; k++) {
          const x = d[k] % cols, y = (d[k] / cols) | 0;
          if (x < x0) x0 = x;
          if (x > x1) x1 = x;
          if (y < y0) y0 = y;
          if (y > y1) y1 = y;
        }
        ctx.putImageData(img, 0, 0, x0 * s, y0 * s, (x1 - x0 + 1) * s, (y1 - y0 + 1) * s);
      }
    }
    this._allDirty = false;
    this._dirty.length = 0;
    return this._surface.canvas;
  }

  // MARK: miniatures

  /** One pixel per art tile, RGBA. `shown(i)` decides whether a tile is drawn (else dark mortar). */
  static miniaturePixels(board, palette, shown) {
    const w = board.artWidth;
    const h = board.artHeight;
    const px = new Uint8ClampedArray(Math.max(1, w * h) * 4).fill(255);
    const mortar = RGB(0x2A2019);
    for (let y = 0; y < h; y++) {
      for (let x = 0; x < w; x++) {
        const i = (y + Board.marginTop) * board.cols + (x + Board.marginLeft);
        const f = board.family[i];
        const col = (f >= 0 && shown(i)) ? RGB(LevelPalette.tone(palette, f, board.tone[i])) : mortar;
        const o = (y * w + x) * 4;
        px[o] = col.r;
        px[o + 1] = col.g;
        px[o + 2] = col.b;
        px[o + 3] = 255;
      }
    }
    return px;
  }

  /** miniature(board:palette:shown:) → small canvas (artWidth × artHeight), or null without canvas. */
  static miniature(board, palette, shown) {
    const w = Math.max(1, board.artWidth), h = Math.max(1, board.artHeight);
    const surf = makeCanvas(w, h);
    if (!surf) return null;
    const px = MosaicRaster.miniaturePixels(board, palette, shown);
    surf.ctx.putImageData(new ImageData(px, w, h), 0, 0);
    return surf.canvas;
  }
}
