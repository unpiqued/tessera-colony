// Port of Board.swift: immutable description of a level's grid (mosaic tiles plus the walkable
// ground around them). x grows right, y grows down. Index = y * cols + x.

export class Board {
  static marginLeft = 2;
  static marginRight = 2;
  static marginTop = 2;
  static marginBottom = 6;

  /** @param {string[]} art rows; "a"..."x" = family*4+tone, anything else = ground */
  constructor(art) {
    const h = art.length;
    const w = h > 0 ? [...art[0]].length : 0;
    const c = w + Board.marginLeft + Board.marginRight;
    const r = h + Board.marginTop + Board.marginBottom;
    const fam = new Int8Array(c * r).fill(-1);
    const tn = new Uint8Array(c * r);
    const totals = [0, 0, 0, 0, 0, 0];
    let tiles = 0;
    for (let y = 0; y < h; y++) {
      const row = art[y];
      let x = 0;
      for (const ch of row) {
        const code = ch.codePointAt(0) - 97;
        if (code >= 0 && code < 24 && x < w) {
          const i = (y + Board.marginTop) * c + (x + Board.marginLeft);
          fam[i] = (code / 4) | 0;
          tn[i] = code % 4;
          totals[(code / 4) | 0] += 1;
          tiles += 1;
        }
        x += 1;
      }
    }
    const nb = new Int32Array(c * r * 4).fill(-1);
    for (let i = 0; i < c * r; i++) {
      const x = i % c;
      const y = (i / c) | 0;
      if (y > 0) nb[i * 4 + 0] = i - c;
      if (x > 0) nb[i * 4 + 1] = i - 1;
      if (x < c - 1) nb[i * 4 + 2] = i + 1;
      if (y < r - 1) nb[i * 4 + 3] = i + c;
    }
    this.artWidth = w;
    this.artHeight = h;
    this.cols = c;
    this.rows = r;
    this.count = c * r;
    /** -1 for ground, otherwise colour family 0...5 */
    this.family = fam;
    /** glaze tone 0...3 (visual only) */
    this.tone = tn;
    this.familyTotals = totals;
    this.tileCount = tiles;
    this.hole = (r - 3) * c + ((c / 2) | 0);
    /** four neighbours per cell: up, left, right, down (-1 = outside) */
    this.neighbours = nb;
  }

  x(i) { return i % this.cols; }
  y(i) { return (i / this.cols) | 0; }
  isTile(i) { return this.family[i] >= 0; }

  areAdjacent(a, b) {
    return Math.abs(this.x(a) - this.x(b)) + Math.abs(this.y(a) - this.y(b)) === 1;
  }

  /** Initial open map: ground is open (1), every tile is closed (0). */
  initialOpen() {
    const open = new Uint8Array(this.count);
    for (let i = 0; i < this.count; i++) if (this.family[i] < 0) open[i] = 1;
    return open;
  }
}
