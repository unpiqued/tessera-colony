// LevelPalette helpers (Level.swift) and the built-in palette constants (GeneratedPalette in
// LevelData.swift). A LevelPalette is the plain object { names: string[], tones: number[][] }
// (6 families x 4 tones, 0xRRGGBB); these functions are its computed members.
// The same values are in data/levels.json → palette {names, tones, grout, soil, soilDark}.

export const GeneratedPalette = Object.freeze({
  familyNames: Object.freeze(['Lapis', 'Saffron', 'Fern', 'Ember', 'Umber', 'Pearl']),
  /** 6 families x 4 tones, 0xRRGGBB, light -> deep */
  tones: Object.freeze([
    Object.freeze([0xAED6F4, 0x7DB9E8, 0x4A8FD1, 0x2A5FA8]),
    Object.freeze([0xFFE36A, 0xFFCA2C, 0xF7AE0E, 0xE08E00]),
    Object.freeze([0xA8DB86, 0x74BD4E, 0x46983A, 0x276A2C]),
    Object.freeze([0xFF9A7E, 0xF76A43, 0xDE4527, 0xB52A18]),
    Object.freeze([0x8E6547, 0x6E4A30, 0x533421, 0x3A2315]),
    Object.freeze([0xFFFEFA, 0xEEEBE3, 0xD9D5CA, 0xBDB8AC]),
  ]),
  grout: 0x261D16,
  soil: 0x3A2D22,
  soilDark: 0x2C2119,
});

/** GeneratedPalette.builtIn */
export const builtInPalette = Object.freeze({ names: GeneratedPalette.familyNames, tones: GeneratedPalette.tones });

/** Computed members of the LevelPalette struct: LevelPalette.tone(p, f, t) etc. */
export const LevelPalette = Object.freeze({
  familyCount(p) { return p.tones.length; },

  tone(p, family, tone) {
    if (!(family >= 0 && family < p.tones.length)) return 0x888888;
    const t = p.tones[family];
    return t[Math.max(0, Math.min(t.length - 1, tone))];
  },

  name(p, family) {
    return family >= 0 && family < p.names.length ? p.names[family] : `Colour ${family + 1}`;
  },

  /** Relative luminance (0...1) of a family's main swatch, used to pick legible number ink. */
  luminance(p, family) {
    const c = LevelPalette.tone(p, family, 1);
    const lin = v => {
      const s = v / 255;
      return s <= 0.04045 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
    };
    return 0.2126 * lin((c >>> 16) & 0xFF) + 0.7152 * lin((c >>> 8) & 0xFF) + 0.0722 * lin(c & 0xFF);
  },
});
