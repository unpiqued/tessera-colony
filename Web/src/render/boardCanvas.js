// Browser equivalent of BoardView.swift: the play field — cached mosaic bitmap + vector ant hill +
// animated ants, drawn into one <canvas> every frame while anything is moving. Pinch (or
// ctrl/trackpad-wheel) to zoom 1...4x about the board centre, drag (or scroll) to pan when zoomed,
// double-tap to reset — as the Swift gestures.
//
// ── The `source` interface (the game controller; same names as GameController.swift) ──────────────
//   board            Board                      the level's grid
//   scheduler        AntScheduler               reads scheduler.trips every frame
//   gameTime(ms)     (number) => number         game seconds at a performance.now()/rAF timestamp (ms)
//   ensureRaster(px) (number) => void           make `raster` exist with cellPx === px (rebuild otherwise)
//   raster           MosaicRaster | null        its .image (canvas) and .shownOpen are drawn
//   groundColor      number 0xRRGGBB            soil colour behind lifted tiles
//   scout            object | null              non-null while a team is being scouted
//   scoutTiles       Set<number>                tile indices that scouted team would take
//   sprites          AntSpriteCache             one per controller
//   detailedAnts     boolean                    legs with knees/feet (Settings)
//   animating        boolean                    keep redrawing every frame while true
//   isBlocked        boolean                    red border when every slot holds a waiting team
//   claimedCount     number                     for the accessibility label (with board.tileCount)
// The controller must call `boardCanvas.invalidate()` whenever something it publishes changes
// (send, undo, scout begin/end, hint, ground colour, detailed legs, animating turning true, …):
// SwiftUI re-renders on @Published changes; here a frame is only drawn on invalidate(), on
// gestures/resizes, and on every animation frame while `source.animating` is true.
// ───────────────────────────────────────────────────────────────────────────────────────────────

import { BoardPainter } from './boardPainter.js';
import { AntSpriteCache } from './antRenderer.js';
import { Theme } from './theme.js';

/** GameView.computeLayout(size:wide:) → { cell, panelWidth } (points per cell at zoom 1). */
export function computeLayout(board, width, height, wide = width > height * 1.05) {
  const cols = board.cols;
  const rows = board.rows;
  if (wide) {
    const panelWidth = Math.min(470, Math.max(360, width * 0.38));
    const availW = width - panelWidth - 48;
    const availH = height - 32;
    const cell = Math.max(3, Math.min(availW / cols, availH / rows));
    return { cell: Math.floor(cell * 2) / 2, panelWidth };
  }
  const panelHeight = width > 600 ? 480 : 440;
  const availW = width - 24;
  const availH = height - panelHeight - 30;
  const cell = Math.max(2.5, Math.min(availW / cols, availH / rows));
  return { cell: Math.floor(cell * 2) / 2, panelWidth: width };
}

/** Swift `.rounded()` for positive numbers. */
const roundHalfUp = x => Math.floor(x + 0.5);

/** SwiftUI .easeOut = cubic-bezier(0, 0, 0.58, 1). */
function easeOut(x) {
  if (x <= 0) return 0;
  if (x >= 1) return 1;
  // solve bx(s) = x for s (control x: 0, 0.58), then return by(s) (control y: 0, 1)
  const bx = s => 3 * (1 - s) * s * s * 0.58 + s * s * s;
  let lo = 0, hi = 1, s = x;
  for (let k = 0; k < 30; k++) {
    s = (lo + hi) / 2;
    if (bx(s) < x) lo = s; else hi = s;
  }
  return 3 * (1 - s) * s * s + s * s * s;
}

function roundedRectPath(ctx, x, y, w, h, r) {
  const rr = Math.max(0, Math.min(r, w / 2, h / 2));
  ctx.beginPath();
  ctx.moveTo(x + rr, y);
  ctx.arcTo(x + w, y, x + w, y + h, rr);
  ctx.arcTo(x + w, y + h, x, y + h, rr);
  ctx.arcTo(x, y + h, x, y, rr);
  ctx.arcTo(x, y, x + w, y, rr);
  ctx.closePath();
}

export class BoardCanvas {
  static maxZoom = 4;
  static cornerRadius = 12;

  /**
   * @param {HTMLCanvasElement} canvas  sized by this class (style.width/height = board size in CSS px)
   * @param {object} source             the game controller (interface above)
   * @param {number} [cell]             points per cell at zoom 1 (see computeLayout / setCell)
   */
  constructor(canvas, source, cell = 8) {
    this.canvas = canvas;
    this.source = source;
    this.ctx = canvas.getContext('2d', { alpha: true });
    this.cell = cell;
    this.zoom = 1;
    this.zoomBase = 1;
    this.pan = { x: 0, y: 0 };
    this.panBase = { x: 0, y: 0 };
    this.dpr = 0;
    /** Time spent in the last draw() call (ms); onDraw(ms, nowMs) is called after each frame (profiling). */
    this.lastDrawMs = 0;
    this.onDraw = null;
    this._raf = 0;
    this._resetAnim = null;
    this._pointers = new Map();
    this._pinch = null;
    this._drag = null;
    this._lastTap = null;
    this._gestureBase = 0;
    this._label = '';
    this._frame = this._frame.bind(this);
    canvas.setAttribute('role', 'img');
    canvas.style.touchAction = 'none';
    canvas.style.display = canvas.style.display || 'block';
    canvas.style.borderRadius = this.constructor.cornerRadius + 'px';
    this._ownSprites = null;
    this._listeners = [];
    this._listen();
    this.setCell(cell);
  }

  /** Points per cell at zoom 1 (from the game screen's layout). Resizes the canvas. */
  setCell(cell) {
    this.cell = cell;
    this._resize(true);
    this.pan = this._clampedPan(this.pan);
    this.panBase = { x: this.pan.x, y: this.pan.y };
    this.invalidate();
  }

  get boardSize() {
    const b = this._boardOf(this.source);
    return { width: b.cols * this.cell, height: b.rows * this.cell };
  }

  /** The Board this view shows (subclasses: one board of a match). */
  _boardOf(src) { return src.board; }

  /** source.sprites, or a cache of our own if the source has none. */
  _sprites(src) {
    if (src.sprites) return src.sprites;
    if (!this._ownSprites) this._ownSprites = new AntSpriteCache();
    return this._ownSprites;
  }

  /** Swap the controller (e.g. after restart builds a new one) and redraw. */
  setSource(source) {
    this.source = source;
    this.setCell(this.cell);
  }

  /** Redraw on the next animation frame; keeps going every frame while source.animating. */
  invalidate() {
    if (!this._raf && typeof requestAnimationFrame !== 'undefined') this._raf = requestAnimationFrame(this._frame);
  }

  /** Double-tap: back to zoom 1 with an ease-out of 0.25 s. */
  resetZoom(animated = true) {
    if (!animated) {
      this.zoom = 1; this.zoomBase = 1;
      this.pan = { x: 0, y: 0 }; this.panBase = { x: 0, y: 0 };
      this._resetAnim = null;
      this.invalidate();
      return;
    }
    this._resetAnim = { start: performance.now(), zoom: this.zoom, x: this.pan.x, y: this.pan.y };
    this.zoomBase = 1;
    this.panBase = { x: 0, y: 0 };
    this.invalidate();
  }

  /** Programmatic zoom/pan (clamped like the gestures). */
  setZoom(zoom, pan = this.pan) {
    this.zoom = Math.min(BoardCanvas.maxZoom, Math.max(1, zoom));
    this.zoomBase = this.zoom;
    this.pan = this._clampedPan(pan);
    this.panBase = { x: this.pan.x, y: this.pan.y };
    this.invalidate();
  }

  destroy() {
    if (this._raf) cancelAnimationFrame(this._raf);
    this._raf = 0;
    for (const [target, type, fn, opts] of this._listeners) target.removeEventListener(type, fn, opts);
    this._listeners = [];
  }

  // MARK: - Sizing

  _resize(force) {
    const dpr = (typeof window !== 'undefined' && window.devicePixelRatio) || 1;
    if (!force && dpr === this.dpr) return;
    this.dpr = dpr;
    const { width, height } = this.boardSize;
    const w = Math.max(1, Math.round(width * dpr));
    const h = Math.max(1, Math.round(height * dpr));
    this.canvas.style.width = width + 'px';
    this.canvas.style.height = height + 'px';
    if (this.canvas.width !== w) this.canvas.width = w;
    if (this.canvas.height !== h) this.canvas.height = h;
  }

  _clampedPan(p) {
    const { width, height } = this.boardSize;
    const mx = (this.zoom - 1) * width / 2;
    const my = (this.zoom - 1) * height / 2;
    return { x: Math.min(mx, Math.max(-mx, p.x)), y: Math.min(my, Math.max(-my, p.y)) };
  }

  // MARK: - Frame loop (TimelineView(.animation(paused: !controller.animating)))

  _frame(ts) {
    this._raf = 0;
    this.draw(ts);
    if (this.source.animating || this._resetAnim) this._raf = requestAnimationFrame(this._frame);
  }

  // MARK: - Drawing

  /** Draws one frame for real time `nowMs` (a performance.now()/rAF timestamp). */
  draw(nowMs = performance.now()) {
    const t0 = performance.now();
    this._resize(false);
    // Unzoomed, a one-finger vertical drag scrolls the page (the phone layout puts the controls
    // below the board); zoomed in, every drag pans the board.
    const ta = this.zoom > 1.01 ? 'none' : 'pan-y';
    if (this._touchAction !== ta) { this._touchAction = ta; this.canvas.style.touchAction = ta; }
    if (this._resetAnim) {
      const a = this._resetAnim;
      const e = easeOut((nowMs - a.start) / 250);
      this.zoom = a.zoom + (1 - a.zoom) * e;
      this.pan = { x: a.x * (1 - e), y: a.y * (1 - e) };
      if (e >= 1) { this._resetAnim = null; this.zoom = 1; this.pan = { x: 0, y: 0 }; }
    }
    const src = this.source;
    const ctx = this.ctx;
    const b = src.board;
    const cs = this.cell;
    const t = src.gameTime(nowMs);
    const { width: w, height: h } = this.boardSize;
    const sx = this.canvas.width / w, sy = this.canvas.height / h;
    const px = Math.max(3, roundHalfUp(cs * sx));
    src.ensureRaster(px);

    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    ctx.setTransform(sx, 0, 0, sy, 0, 0);
    ctx.save();
    // .clipShape(RoundedRectangle(cornerRadius: 12)) is the element's CSS border-radius (set in
    // the constructor): the browser clips the corners, so no canvas clip mask is needed.

    ctx.translate(this.pan.x + w / 2, this.pan.y + h / 2);
    ctx.scale(this.zoom, this.zoom);
    ctx.translate(-w / 2, -h / 2);

    // 1-3. Mosaic bitmap, the ant hill, lifted tiles and the glow on claimed tiles.
    const trips = src.scheduler.trips;
    BoardPainter.paintBase(ctx, b, cs, t, nowMs, { width: w, height: h }, src.raster, trips, src.groundColor,
      [b.hole], this.zoom > 1.3);

    // 4. Scout preview: dim everything except the tiles this team would take.
    if (src.scout != null) {
      const cols = b.cols;
      ctx.beginPath();
      ctx.rect(0, 0, w, h);
      for (const tile of src.scoutTiles) ctx.rect((tile % cols) * cs, ((tile / cols) | 0) * cs, cs, cs);
      ctx.fillStyle = 'rgba(0,0,0,0.5)';
      ctx.fill('evenodd');
      ctx.beginPath();
      const ins = cs * 0.06;
      for (const tile of src.scoutTiles) ctx.rect((tile % cols) * cs + ins, ((tile / cols) | 0) * cs + ins, cs - 2 * ins, cs - 2 * ins);
      ctx.strokeStyle = Theme.brass;
      ctx.lineWidth = Math.max(1, cs * 0.14);
      ctx.lineCap = 'butt';
      ctx.lineJoin = 'miter';
      ctx.stroke();
    }

    // 4b-5. Scout trails and the ants.
    BoardPainter.paintAnts(ctx, b, cs, t, trips, this._sprites(src), !!src.detailedAnts && cs * this.zoom >= 5, false);
    ctx.restore();

    // Border (strokeBorder: inside the rounded rectangle, not zoomed).
    const blocked = !!src.isBlocked;
    const lw = blocked ? 3 : 1;
    roundedRectPath(ctx, lw / 2, lw / 2, w - lw, h - lw, BoardCanvas.cornerRadius - lw / 2);
    ctx.strokeStyle = blocked ? Theme.danger : Theme.panelEdge;
    ctx.lineWidth = lw;
    ctx.stroke();

    const label = `Mosaic board, ${b.tileCount - (src.claimedCount || 0)} tiles left to claim`;
    if (label !== this._label) {
      this._label = label;
      this.canvas.setAttribute('aria-label', label);
    }
    this.lastDrawMs = performance.now() - t0;
    if (this.onDraw) this.onDraw(this.lastDrawMs, nowMs);
  }

  // MARK: - Gestures

  _on(target, type, fn, opts) {
    target.addEventListener(type, fn, opts);
    this._listeners.push([target, type, fn, opts]);
  }

  _local(e) {
    const r = this.canvas.getBoundingClientRect();
    return { x: e.clientX - r.left, y: e.clientY - r.top };
  }

  _listen() {
    const c = this.canvas;
    this._on(c, 'pointerdown', e => this._pointerDown(e));
    this._on(c, 'pointermove', e => this._pointerMove(e));
    this._on(c, 'pointerup', e => this._pointerUp(e, false));
    this._on(c, 'pointercancel', e => this._pointerUp(e, true));
    this._on(c, 'wheel', e => this._wheel(e), { passive: false });
    // Safari: trackpad pinch (macOS) arrives as gesture events; on iOS they would zoom the page.
    this._on(c, 'gesturestart', e => { e.preventDefault(); this._gestureBase = this.zoom; }, { passive: false });
    this._on(c, 'gesturechange', e => {
      e.preventDefault();
      if (this._pointers.size >= 2 || !(e.scale > 0)) return;
      this.zoom = Math.min(BoardCanvas.maxZoom, Math.max(1, this._gestureBase * e.scale));
      this.pan = this._clampedPan(this.pan);
      this.invalidate();
    }, { passive: false });
    this._on(c, 'gestureend', e => {
      e.preventDefault();
      this.zoomBase = this.zoom;
      this.pan = this._clampedPan(this.pan);
      this.panBase = { x: this.pan.x, y: this.pan.y };
    }, { passive: false });
  }

  _pointerDown(e) {
    if (e.pointerType === 'mouse' && e.button !== 0) return;
    try { this.canvas.setPointerCapture(e.pointerId); } catch (err) { /* ignore */ }
    const p = this._local(e);
    this._pointers.set(e.pointerId, { x: p.x, y: p.y, sx: p.x, sy: p.y });
    this._resetAnim = null;
    if (this._pointers.size === 2) {
      const [a, b] = [...this._pointers.values()];
      this._pinch = { dist: Math.max(1, Math.hypot(a.x - b.x, a.y - b.y)) };
      this.zoomBase = this.zoom;
      this._drag = null;
      this.panBase = { x: this.pan.x, y: this.pan.y };
      this._tapCandidate = false;
    } else if (this._pointers.size === 1) {
      this._drag = { x: p.x, y: p.y, active: false };
      this.panBase = { x: this.pan.x, y: this.pan.y };
      this._tapCandidate = true;
    }
  }

  _pointerMove(e) {
    const ptr = this._pointers.get(e.pointerId);
    if (!ptr) return;
    const p = this._local(e);
    ptr.x = p.x; ptr.y = p.y;
    if (this._pointers.size >= 2 && this._pinch) {
      const [a, b] = [...this._pointers.values()];
      const mag = Math.hypot(a.x - b.x, a.y - b.y) / this._pinch.dist;
      this.zoom = Math.min(BoardCanvas.maxZoom, Math.max(1, this.zoomBase * mag));
      this.pan = this._clampedPan(this.pan);
      this.invalidate();
      e.preventDefault();
      return;
    }
    const d = this._drag;
    if (!d) return;
    const dx = p.x - d.x, dy = p.y - d.y;
    if (!d.active && Math.hypot(dx, dy) >= 6) { d.active = true; this._tapCandidate = false; }
    if (d.active && this.zoom > 1.01) {
      this.pan = this._clampedPan({ x: this.panBase.x + dx, y: this.panBase.y + dy });
      this.invalidate();
    }
  }

  _pointerUp(e, cancelled) {
    const ptr = this._pointers.get(e.pointerId);
    if (!ptr) return;
    this._pointers.delete(e.pointerId);
    if (this._pinch) {
      if (this._pointers.size < 2) {
        // pinch ended: keep the zoom, continue dragging from where the remaining finger is
        this._pinch = null;
        this.zoomBase = this.zoom;
        this.pan = this._clampedPan(this.pan);
        this.panBase = { x: this.pan.x, y: this.pan.y };
        const rest = [...this._pointers.values()][0];
        this._drag = rest ? { x: rest.x, y: rest.y, active: true } : null;
        this.invalidate();
      }
      return;
    }
    if (this._pointers.size === 0) {
      if (this._drag && this._drag.active) this.panBase = { x: this.pan.x, y: this.pan.y };
      this._drag = null;
      if (!cancelled && this._tapCandidate) {
        const now = performance.now();
        const last = this._lastTap;
        if (last && now - last.time < 350 && Math.hypot(ptr.x - last.x, ptr.y - last.y) < 30) {
          this._lastTap = null;
          this.resetZoom(true);
        } else {
          this._lastTap = { time: now, x: ptr.x, y: ptr.y };
        }
      }
    }
  }

  _wheel(e) {
    if (e.ctrlKey) {
      // trackpad pinch (Chrome/Firefox/Edge) or ctrl + mouse wheel
      e.preventDefault();
      const unit = e.deltaMode === 1 ? 16 : e.deltaMode === 2 ? 400 : 1;
      this.zoom = Math.min(BoardCanvas.maxZoom, Math.max(1, this.zoom * Math.exp(-e.deltaY * unit * 0.01)));
      this.zoomBase = this.zoom;
      this.pan = this._clampedPan(this.pan);
      this.panBase = { x: this.pan.x, y: this.pan.y };
      this._resetAnim = null;
      this.invalidate();
      return;
    }
    if (this.zoom <= 1.01) return;   // not zoomed: let the page scroll
    e.preventDefault();
    const unit = e.deltaMode === 1 ? 16 : e.deltaMode === 2 ? 400 : 1;
    this.pan = this._clampedPan({ x: this.pan.x - e.deltaX * unit, y: this.pan.y - e.deltaY * unit });
    this.panBase = { x: this.pan.x, y: this.pan.y };
    this.invalidate();
  }
}

/** VersusMatch.sharedHoles (VersusEngine.swift): two hills on a shared board, a quarter and three
 *  quarters of the way across, three rows from the bottom. */
function sharedHoles(b) {
  const row = b.rows - 3;
  return [row * b.cols + Math.floor(b.cols / 4), row * b.cols + Math.floor((3 * b.cols) / 4)];
}

/**
 * Browser equivalent of VersusBoardView (VersusView.swift): one board of a two-player match, drawn
 * by the same painter as the single-player board, sized to fit its box (no zoom or pan).
 *
 * `source` (VersusController, same names as the Swift one):
 *   match.boards[index]   { board: Board, holes: Map|object|array (player → hole cell) }
 *   rules.layout          'race' | 'shared' (shared: player-coloured hill rings and ant owner rings)
 *   schedulers[index]     AntScheduler        rasters[index]   MosaicRaster | null
 *   ensureRaster(index, px), gameTime(ms), groundColor, detailedAnts, animating, sprites (optional)
 * Call setSize(width, height) with the box it must fit (cs = max(2, min(w / cols, h / rows))).
 */
export class VersusBoardCanvas extends BoardCanvas {
  static cornerRadius = 10;

  constructor(canvas, source, index) {
    super(canvas, source, 8);
    canvas.style.touchAction = 'manipulation';   // no gestures here: let the page scroll
    this.index = index;
    this.setCell(this.cell);
  }

  _boardOf(src) { return src.match.boards[this.index || 0].board; }

  /** No gestures on the two-player boards. */
  _listen() {}

  /** Fit the board into a box of width × height CSS px. */
  setSize(width, height) {
    const b = this._boardOf(this.source);
    this.setCell(Math.max(2, Math.min(width / b.cols, height / b.rows)));
  }

  draw(nowMs = performance.now()) {
    const t0 = performance.now();
    this._resize(false);
    const src = this.source;
    const index = this.index || 0;
    const vb = src.match.boards[index];
    const b = vb.board;
    const cs = this.cell;
    const ctx = this.ctx;
    const t = src.gameTime(nowMs);
    const { width: w, height: h } = this.boardSize;
    const sx = this.canvas.width / w, sy = this.canvas.height / h;
    src.ensureRaster(index, Math.max(2, roundHalfUp(cs * sx)));
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    ctx.setTransform(sx, 0, 0, sy, 0, 0);
    const trips = src.schedulers[index].trips;
    const hv = vb.holes;
    const holes = (hv instanceof Map ? [...hv.values()] : Array.isArray(hv) ? [...hv] : Object.values(hv || {}))
      .sort((a, c) => a - c);
    BoardPainter.paintBase(ctx, b, cs, t, nowMs, { width: w, height: h }, src.rasters[index], trips, src.groundColor,
      holes.length ? holes : [b.hole], false);
    const shared = src.rules && src.rules.layout === 'shared';
    if (shared) {
      // mark each hill with its player's colour
      sharedHoles(b).forEach((hole, p) => {
        ctx.beginPath();
        ctx.ellipse((b.x(hole) + 0.5) * cs, (b.y(hole) + 0.5) * cs, 1.4 * cs, 0.9 * cs, 0, 0, 2 * Math.PI);
        ctx.strokeStyle = '#' + BoardPainter.playerColors[p].toString(16).padStart(6, '0');
        ctx.lineWidth = Math.max(1.5, cs * 0.25);
        ctx.stroke();
      });
    }
    BoardPainter.paintAnts(ctx, b, cs, t, trips, this._sprites(src), !!src.detailedAnts && cs >= 5, shared);
    roundedRectPath(ctx, 0.5, 0.5, w - 1, h - 1, VersusBoardCanvas.cornerRadius - 0.5);
    ctx.strokeStyle = Theme.panelEdge;
    ctx.lineWidth = 1;
    ctx.stroke();
    this.lastDrawMs = performance.now() - t0;
    if (this.onDraw) this.onDraw(this.lastDrawMs, nowMs);
  }
}
