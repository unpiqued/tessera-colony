// Port of BoardPainter.swift: drawing shared by the single-player board and the two-player boards —
// the mosaic bitmap, ant hills, lifted tiles, the glow on claimed tiles, scout trails and the ants.
// All functions draw onto a CanvasRenderingContext2D whose current transform maps board points
// (cell * cs) to the canvas, like the SwiftUI GraphicsContext they replace.

import { hash32 } from '../core/util.js';
import { AntGeometry } from './antScheduler.js';
import { AntRenderer } from './antRenderer.js';
import { cssColor } from './theme.js';

/** VersusRules.playerBase (VersusEngine.swift): team uid = player * playerBase + tunnel * 1000 + index. */
const VERSUS_PLAYER_BASE = 100000;

const TWO_PI = 2 * Math.PI;

// Reused between frames (no per-frame allocation of pose objects).
const VISIBLE = [];

export class BoardPainter {
  /** Player colours in two-player mode (rings under ants on a shared board, panel accents). */
  static playerColors = [0x3FB6C8, 0xF08A5D];

  /**
   * paintBase(_:board:cs:t:date:size:raster:trips:ground:holes:sharp:)
   * @param {number} dateMs real time in ms (drives the pulse of the claimed-tile glow)
   * @param {{width:number,height:number}} size board size in points
   */
  static paintBase(ctx, b, cs, t, dateMs, size, raster, trips, ground, holes, sharp) {
    // 1. Mosaic bitmap (tiles + soil), rebuilt ~10x per second at most.
    const img = raster ? raster.image : null;
    if (img) {
      ctx.imageSmoothingEnabled = !sharp;
      if (!sharp) ctx.imageSmoothingQuality = 'medium';
      ctx.drawImage(img, 0, 0, size.width, size.height);
      ctx.imageSmoothingEnabled = true;
    }
    // 2. Ant hills.
    for (const h of holes) BoardPainter.drawHill(ctx, b, h, cs);
    // 3. Tiles lifted since the last bitmap refresh, and a soft glow on claimed tiles.
    const cols = b.cols;
    const shownOpen = raster ? raster.shownOpen : null;
    let anyPatch = false, anyReserved = false;
    for (let k = 0; k < trips.length; k++) {
      const trip = trips[k];
      if (trip.arrive <= t) { if (shownOpen && !shownOpen[trip.tile]) { anyPatch = true; } } else anyReserved = true;
      if (anyPatch && anyReserved) break;
    }
    if (anyPatch) {
      ctx.beginPath();
      for (let k = 0; k < trips.length; k++) {
        const trip = trips[k];
        if (trip.arrive <= t && shownOpen && !shownOpen[trip.tile]) {
          ctx.rect((trip.tile % cols) * cs, ((trip.tile / cols) | 0) * cs, cs, cs);
        }
      }
      ctx.fillStyle = cssColor(ground);
      ctx.fill();
    }
    if (anyReserved) {
      // Claimed tiles glow softly (a light wash, no symbols) until their ant arrives.
      const pulse = 0.5 + 0.5 * Math.sin(dateMs / 1000 * 3.0);
      ctx.beginPath();
      for (let k = 0; k < trips.length; k++) {
        const trip = trips[k];
        if (!(trip.arrive <= t)) ctx.rect((trip.tile % cols) * cs, ((trip.tile / cols) | 0) * cs, cs, cs);
      }
      ctx.fillStyle = `rgba(255,255,255,${0.16 + 0.12 * pulse})`;
      ctx.fill();
    }
  }

  /** paintAnts(_:board:cs:t:trips:sprites:detailed:ownerRings:) */
  static paintAnts(ctx, b, cs, t, trips, sprites, detailed, ownerRings) {
    const cols = b.cols;
    // Scout trails: faint dotted lines in the team's colour, laid as the ant walks and fading a
    // few seconds after it gets home. Overlapping trips make a stronger trail.
    let dashed = false;
    for (let k = 0; k < trips.length; k++) {
      const trip = trips[k];
      if (!(trip.style === 'scout' && t >= trip.depart && t < trip.home + 3)) continue;
      let count = trip.path.length;
      if (t < trip.arrive) {
        const u = AntGeometry.outbound(trip, t - trip.depart).u;
        if (Number.isFinite(u)) {
          count = Math.min(trip.path.length, Math.trunc(Math.max(0, Math.min(u, trip.path.length))) + 1);
        }
      }
      if (count < 2) continue;
      if (!dashed) {
        ctx.setLineDash([cs * 0.18, cs * 0.3]);
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';
        ctx.lineWidth = Math.max(1, cs * 0.16);
        dashed = true;
      }
      ctx.beginPath();
      for (let j = 0; j < count; j++) {
        const c = trip.path[j];
        const px = (c % cols + 0.5) * cs, py = (((c / cols) | 0) + 0.5) * cs;
        if (j === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
      }
      const fade = t > trip.home ? Math.max(0, 1 - (t - trip.home) / 3) : 1;
      ctx.strokeStyle = cssColor(trip.color, 0.28 * fade);
      ctx.stroke();
    }
    if (dashed) ctx.setLineDash([]);
    // Ants: cartoon bodies in the colour of the tile each one is fetching, legs that plant and
    // lift in step with the ground speed, shadows, and the tiles they carry.
    const visible = VISIBLE;
    let n = 0;
    let rings = null;
    if (ownerRings) {
      rings = [new Path2D(), new Path2D()];
    }
    for (let k = 0; k < trips.length; k++) {
      const trip = trips[k];
      if (t < trip.depart || t >= trip.home) continue;   // underground (pose() also checks)
      let slot = visible[n];
      if (slot === undefined) {
        slot = { trip: null, pose: { x: 0, y: 0, heading: 0, scale: 1, carrying: false, liftProgress: 0, gaitDistance: 0, moving: false } };
        visible[n] = slot;
      }
      const pose = AntGeometry.pose(trip, t, b, slot.pose);
      if (pose === null) continue;
      slot.trip = trip;
      n += 1;
      if (ownerRings) {
        const owner = Math.min(1, Math.max(0, Math.trunc(trip.team / VERSUS_PLAYER_BASE)));
        const r = cs * 0.62 * pose.scale;
        rings[owner].moveTo(pose.x * cs + r, pose.y * cs);
        rings[owner].arc(pose.x * cs, pose.y * cs, r, 0, TWO_PI);
      }
    }
    if (ownerRings) {
      ctx.lineWidth = Math.max(1, cs * 0.12);
      for (let k = 0; k < 2; k++) {
        ctx.strokeStyle = cssColor(BoardPainter.playerColors[k], 0.85);
        ctx.stroke(rings[k]);
      }
    }
    AntRenderer.draw(ctx, visible, b, cs, sprites, detailed, n);
    // drop trip references so finished trips can be collected
    for (let k = 0; k < n; k++) visible[k].trip = null;
  }

  /** drawHill(_:board:hole:cs:) */
  static drawHill(ctx, b, hole, cs) {
    const hx = (b.x(hole) + 0.5) * cs;
    const hy = (b.y(hole) + 0.5) * cs;
    const rings = [[4.3, 2.4, 0x5C4632], [3.4, 1.9, 0x6E5440], [2.5, 1.4, 0x80654B]];
    for (const [rx, ry, col] of rings) {
      ctx.beginPath();
      ctx.ellipse(hx, hy + 0.3 * cs, rx * cs, ry * cs, 0, 0, TWO_PI);
      ctx.fillStyle = cssColor(col);
      ctx.fill();
    }
    ctx.beginPath();
    for (let i = 0; i < 36; i++) {
      const a = (hash32(i + hole, 11) % 6283) / 1000.0;
      const rr = 2.0 + (hash32(i, 23) % 1000) / 1000.0 * 2.3;
      const x = hx + rr * Math.cos(a) * cs;
      const y = hy + (rr * Math.sin(a) * 0.55 + 0.3) * cs;
      const s = cs * (0.08 + (hash32(i, 37) % 100) / 1000.0);
      ctx.moveTo(x + s, y);
      ctx.arc(x, y, s, 0, TWO_PI);
    }
    ctx.fillStyle = cssColor(0x927456);
    ctx.fill();
    ctx.beginPath();
    ctx.ellipse(hx, hy, 1.05 * cs, 0.62 * cs, 0, 0, TWO_PI);
    ctx.fillStyle = cssColor(0x18100B);
    ctx.fill();
    ctx.beginPath();
    ctx.ellipse(hx, hy - 0.42 * cs + 0.4 * cs, 0.75 * cs, 0.4 * cs, 0, 0, TWO_PI);
    ctx.fillStyle = cssColor(0x080503);
    ctx.fill();
  }
}
