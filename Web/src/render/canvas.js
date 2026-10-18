// Offscreen drawing surfaces for cached bitmaps (ant sprites, mosaic raster, miniatures).
// OffscreenCanvas when it has a 2D context (Safari < 16.4 has the constructor but no '2d'),
// else a detached <canvas>; null where neither exists (Node tests).

export function makeCanvas(width, height) {
  const w = Math.max(1, width | 0), h = Math.max(1, height | 0);
  if (typeof OffscreenCanvas !== 'undefined') {
    try {
      const c = new OffscreenCanvas(w, h);
      const ctx = c.getContext('2d');
      if (ctx) return { canvas: c, ctx };
    } catch (e) { /* fall through */ }
  }
  if (typeof document !== 'undefined' && document.createElement) {
    const c = document.createElement('canvas');
    c.width = w;
    c.height = h;
    const ctx = c.getContext('2d');
    if (ctx) return { canvas: c, ctx };
  }
  return null;
}
