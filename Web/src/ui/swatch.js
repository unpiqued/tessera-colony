// TesseraSwatch (ControlPanel.swift) and FamilyStyle (Theme.swift): team pieces are made of the
// tiles they collect. Swatches are drawn once per (palette, family, tile size) into a canvas and
// used as CSS background images.
import { hash32 } from '../core/util.js';

const cache = new Map();
const hex = c => '#' + (c >>> 0).toString(16).padStart(6, '0');

export function paletteTone(p, f, t) {
  if (f < 0 || f >= p.tones.length) return 0x888888;
  const row = p.tones[f];
  return row[Math.max(0, Math.min(row.length - 1, t))];
}

export function luminance(p, f) {
  const c = paletteTone(p, f, 1);
  const lin = v => { const s = v / 255; return s <= 0.04045 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4); };
  return 0.2126 * lin((c >> 16) & 0xFF) + 0.7152 * lin((c >> 8) & 0xFF) + 0.0722 * lin(c & 0xFF);
}

/** Number ink on a team piece: dark on light families, white on dark ones. */
export function inkStyle(p, f) {
  const light = luminance(p, f) > 0.42;
  return { color: light ? '#24170F' : '#FFFFFF', '--ink-shadow': light ? 'rgba(255,255,255,.35)' : 'rgba(0,0,0,.45)' };
}

export function cssColor(c) { return hex(c); }

function paletteKey(p) { return p.tones.map(r => r.join(',')).join(';'); }

/** A data URL of a w×h (CSS px) patch of glazed tesserae in family f, tiles `tile` px wide. */
export function swatchURL(p, f, tile, w = 240, h = 120) {
  const key = paletteKey(p) + '|' + f + '|' + tile + '|' + w + '|' + h;
  const hit = cache.get(key);
  if (hit) return hit;
  const dpr = Math.min(3, Math.max(1, (typeof devicePixelRatio === 'number' ? devicePixelRatio : 1)));
  const cv = document.createElement('canvas');
  cv.width = Math.ceil(w * dpr);
  cv.height = Math.ceil(h * dpr);
  const ctx = cv.getContext('2d');
  ctx.scale(dpr, dpr);
  ctx.fillStyle = hex(paletteTone(p, f, 2));
  ctx.fillRect(0, 0, w, h);
  const cols = Math.min(400, Math.ceil(w / tile));
  const rows = Math.min(400, Math.ceil(h / tile));
  ctx.lineWidth = 0.5;
  ctx.strokeStyle = 'rgba(30,22,17,0.55)';
  for (let y = 0; y < rows; y++) {
    for (let x = 0; x < cols; x++) {
      const hv = hash32(x + f * 97, y * 31 + f);
      const pick = hv % 10;
      const tone = pick < 3 ? 0 : (pick < 7 ? 1 : (pick < 9 ? 2 : 3));
      const rx = x * tile, ry = y * tile, s = tile - 1;
      ctx.beginPath();
      if (ctx.roundRect) ctx.roundRect(rx, ry, s, s, 2); else ctx.rect(rx, ry, s, s);
      ctx.fillStyle = hex(paletteTone(p, f, tone));
      ctx.fill();
      ctx.stroke();
    }
  }
  const url = cv.toDataURL();
  cache.set(key, url);
  return url;
}

/** CSS for an element that should look like a piece of family f. */
export function pieceStyle(p, f, tile, w, h, extra) {
  return Object.assign({ backgroundImage: `url(${swatchURL(p, f, tile, w, h)})`, backgroundSize: `${w}px ${h}px`, backgroundPosition: 'left top' },
    inkStyle(p, f), extra || {});
}
