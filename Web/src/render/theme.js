// Port of Theme.swift: colours and presets the drawing code and screens share.
// Colours are 0xRRGGBB numbers; `cssColor(hex, opacity)` turns one into a CSS colour string.
// (SwiftUI `Color` values become CSS strings: Theme.* are strings, Theme.hex.* the numbers.)

import { LevelPalette } from './palette.js';

/** Color(hex:opacity:) → CSS colour string. */
export function cssColor(hex, opacity = 1) {
  const r = (hex >>> 16) & 0xFF, g = (hex >>> 8) & 0xFF, b = hex & 0xFF;
  if (opacity >= 1) return '#' + ((hex & 0xFFFFFF) >>> 0).toString(16).padStart(6, '0');
  return `rgba(${r},${g},${b},${Math.max(0, opacity)})`;
}

/** Color.rgbHex(): 0xRRGGBB from a CSS hex colour ('#rgb' / '#rrggbb', e.g. from <input type=color>). */
export function rgbHex(css) {
  let s = String(css).trim().replace(/^#/, '');
  if (s.length === 3) s = s.split('').map(c => c + c).join('');
  const v = parseInt(s.slice(0, 6), 16);
  return Number.isFinite(v) ? v >>> 0 : 0;
}

const THEME_HEX = Object.freeze({
  loam: 0x1C1511,
  loamRaised: 0x271D17,
  panel: 0x2F241C,
  panelEdge: 0x4A3A2C,
  sand: 0xE9DCC3,
  sandDim: 0xB8A98F,
  brass: 0xD9A441,
  brassDeep: 0xA8772A,
  terracotta: 0xC8643B,
  danger: 0xE0563A,
  ok: 0x8CC56A,
});

/** Visual language: warm loam backgrounds, sandstone panels, brass accents, serif titles, rounded numbers. */
export const Theme = Object.freeze({
  hex: THEME_HEX,
  loam: cssColor(THEME_HEX.loam),
  loamRaised: cssColor(THEME_HEX.loamRaised),
  panel: cssColor(THEME_HEX.panel),
  panelEdge: cssColor(THEME_HEX.panelEdge),
  sand: cssColor(THEME_HEX.sand),
  sandDim: cssColor(THEME_HEX.sandDim),
  brass: cssColor(THEME_HEX.brass),
  brassDeep: cssColor(THEME_HEX.brassDeep),
  terracotta: cssColor(THEME_HEX.terracotta),
  danger: cssColor(THEME_HEX.danger),
  ok: cssColor(THEME_HEX.ok),
  /** CSS font shorthands standing in for New York (serif) titles and SF Rounded numbers/labels. */
  title(size) { return `600 ${size}px "New York", ui-serif, Georgia, "Times New Roman", serif`; },
  number(size) { return `700 ${size}px ui-rounded, "SF Pro Rounded", "Nunito", system-ui, sans-serif`; },
  label(size, weight = 500) { return `${weight} ${size}px ui-rounded, "SF Pro Rounded", "Nunito", system-ui, sans-serif`; },
});

/** Ground colours offered for the area behind the mosaic (the player can also pick any colour). */
export const GroundPresets = Object.freeze({
  all: Object.freeze([
    ['Loam', 0x3A2D22], ['Night', 0x161A24], ['Slate', 0x333A45], ['Moss', 0x2E3A28],
    ['Plum', 0x3B2637], ['Clay', 0x7A4A36], ['Sand', 0xC9B48A], ['Chalk', 0xE7E2D6],
  ].map(e => Object.freeze(e))),

  /** A darker version of a ground colour for the screen around the board (CSS colour). */
  backdrop(hex) {
    const r = Math.round(((hex >>> 16) & 0xFF) * 0.5);
    const g = Math.round(((hex >>> 8) & 0xFF) * 0.5);
    const b = Math.round((hex & 0xFF) * 0.5);
    return `rgb(${r},${g},${b})`;
  },
});

/** Colours for team controls, taken straight from the level's own glaze tones (CSS colours). */
export const FamilyStyle = Object.freeze({
  tone(p, f, t) { return cssColor(LevelPalette.tone(p, f, t)); },
  swatch(p, f) { return FamilyStyle.tone(p, f, 1); },
  swatchDeep(p, f) { return FamilyStyle.tone(p, f, 2); },
  /** Dark ink on light families, light ink on dark ones (for the numbers only). */
  ink(p, f) { return LevelPalette.luminance(p, f) > 0.42 ? cssColor(0x24170F) : '#ffffff'; },
  inkShadow(p, f) { return LevelPalette.luminance(p, f) > 0.42 ? 'rgba(255,255,255,0.35)' : 'rgba(0,0,0,0.45)'; },
});
