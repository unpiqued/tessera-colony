// Shared view pieces (ports of the small SwiftUI views): pills, switches, sheets, dialogs,
// team cards, slot pods, stars, rating dots and high-score lists.
import { h } from './vdom.js';
import { icon } from './icons.js';
import { pieceStyle } from './swatch.js';
import { modifierInfo, TimeText, difficultyTitle, formatNumber, paletteName } from './compat.js';

export function pill(label, onclick, opts = {}) {
  return h('button', {
    class: ['pill', opts.prominent && 'prominent', opts.wide && 'wide', opts.destructive && 'destructive', opts.cls],
    onclick, disabled: !!opts.disabled, type: 'button', 'aria-label': opts.aria || null, key: opts.key,
  }, opts.icon ? icon(opts.icon, opts.iconSize || 16) : null, h('span', { class: 'lbl' }, label));
}

export function toggleSwitch(id, checked, onchange, disabled = false, aria = null) {
  return h('span', { class: 'switch' },
    h('input', { id, type: 'checkbox', role: 'switch', checked: !!checked, disabled, 'aria-label': aria, onchange: e => onchange(e.target.checked) }),
    h('i', null));
}

export function segmented(options, value, onpick, aria) {
  return h('div', { class: 'segmented', role: 'radiogroup', 'aria-label': aria || null },
    options.map(o => h('button', {
      key: o.id, type: 'button', role: 'radio', 'aria-checked': o.id === value ? 'true' : 'false',
      class: { on: o.id === value }, onclick: () => onpick(o.id),
    }, o.title)));
}

/** A modal sheet with a title bar and a Done button (NavigationStack + toolbar in SwiftUI). */
export function sheet(title, onDone, body, opts = {}) {
  return h('div', {
    class: 'scrim sheet-host', key: 'sheet-' + (opts.key || title),
    onclick: e => { if (e.target === e.currentTarget) onDone(); },
  },
  h('div', { class: ['sheet', opts.large && 'large'], role: 'dialog', 'aria-modal': 'true', 'aria-label': title },
    h('div', { class: 'sheet-bar' },
      opts.leading || h('span', { style: { width: '60px' } }),
      h('div', { class: 'title' }, title),
      h('button', { class: 'textbtn', type: 'button', onclick: onDone }, opts.doneLabel || 'Done')),
    h('div', { class: 'sheet-body' }, body),
    opts.footer ? h('div', { class: 'sheet-foot' }, opts.footer) : null));
}

/** An alert / confirmation dialog. buttons: [{label, onclick, prominent, destructive}] */
export function dialog(title, message, buttons, onCancel, key) {
  return h('div', { class: 'scrim', key: 'dlg-' + (key || title), onclick: e => { if (e.target === e.currentTarget) onCancel(); } },
    h('div', { class: 'dialog', role: 'alertdialog', 'aria-modal': 'true', 'aria-label': title },
      h('div', { class: 'title' }, title),
      message ? h('div', { class: 'dim', style: { fontSize: '14px', lineHeight: '1.45', whiteSpace: 'pre-line' } }, message) : null,
      h('div', { class: 'btns' }, buttons.map((b, i) => pill(b.label, b.onclick, { prominent: b.prominent, destructive: b.destructive, wide: true, key: 'b' + i })))));
}

export const RATING_COLORS = { 1: '#8CC56A', 2: '#9CC45A', 3: '#D9A441', 4: '#E0803A', 5: '#E0563A' };
export function ratingColor(level) { return RATING_COLORS[level] || RATING_COLORS[5]; }

export function ratingDots(level, size = 9) {
  const c = ratingColor(level);
  return h('span', { class: 'dots', 'aria-hidden': 'true', style: { '--d': size + 'px' } },
    [1, 2, 3, 4, 5].map(k => h('i', { key: k, style: k <= level ? { background: c } : null })));
}

export function starRow(stars, mastered = false, size = 11) {
  return h('span', { class: 'stars', role: 'img', 'aria-label': mastered ? 'Mastered' : `${stars} of 3 stars` },
    [0, 1, 2].map(k => h('span', { key: k, class: k < stars ? 'brass' : '', style: k < stars ? null : { color: 'var(--panel-edge)' } }, icon(k < stars ? 'star.fill' : 'star', size + 2))),
    mastered ? h('span', { class: 'dangerc' }, icon('flame.fill', size + 2)) : null);
}

/** A team button face: a piece made of the colour it collects with the number it needs. */
export function teamFace(palette, family, need, height, extraClass, props = {}) {
  const tile = Math.max(10, height / 7);
  return h('button', Object.assign({
    type: 'button', class: ['teamcard', 'num', 'ink', extraClass],
    style: pieceStyle(palette, family, tile, 260, height, { '--h': height + 'px' }),
  }, props), h('span', null, String(need)), props.children || null);
}

export function chamberPod(palette, team, size, opts = {}) {
  if (!team) {
    return h('div', { class: 'pod empty', style: { '--pod': size + 'px' } }, opts.label || null);
  }
  return h('div', {
    class: ['pod', 'num', 'ink', opts.jammed && 'jammed', opts.hint && 'hint'],
    style: pieceStyle(palette, team.family, size / 5, size, size, { '--pod': size + 'px', opacity: opts.opacity || null }),
  }, String(team.remaining), opts.badge || null);
}

export function miniChip(palette, spec, k) {
  return h('div', {
    key: 'mc' + k, class: 'minichip num ink', 'aria-label': `Next: ${paletteName(palette, spec.family)} team, ${spec.quota} tiles`,
    style: pieceStyle(palette, spec.family, 9, 200, 26, { opacity: String(0.9 * (1 - 0.18 * k)) }),
  }, String(spec.quota));
}

export function howPlayed(e) {
  if (e.detail) return e.detail;
  let s = difficultyTitle(e.difficulty);
  if (e.modifiers && e.modifiers.length) s += ' + ' + e.modifiers.map(m => modifierInfo(m).title).join(', ');
  return s;
}

export function highScoreList(entries, highlight = null, compact = false) {
  return h('div', { class: ['hs-list', compact && 'compact'], role: 'list' },
    entries.map((e, i) => h('div', { key: 'hs' + i, role: 'listitem', class: ['hs-row', highlight === i && 'hl'], 'aria-label': `${i + 1}. ${e.name}, ${e.score} points, ${howPlayed(e)}, time ${TimeText.mmss(e.seconds)}` },
      h('span', { class: 'num', style: { width: '18px', textAlign: 'right', fontSize: '13px', fontWeight: 700, color: i === 0 ? 'var(--brass)' : 'var(--sand-dim)' } }, String(i + 1)),
      h('span', { style: { fontWeight: 600, fontSize: '14px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', minWidth: 0 } }, e.name),
      compact ? null : h('span', { class: 'dim', style: { fontSize: '11px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', minWidth: 0 } }, howPlayed(e)),
      h('span', { class: 'grow' }),
      (e.modifiers || []).map(m => h('span', { key: m, class: 'dangerc' }, icon(modifierInfo(m).systemImage, 12))),
      h('span', { class: 'dim num', style: { fontSize: '12px' } }, TimeText.mmss(e.seconds)),
      h('span', { class: 'num', style: { fontSize: '15px', fontWeight: 700, minWidth: '54px', textAlign: 'right' } }, formatNumber(e.score)))));
}

export function sectionTitle(text) {
  return h('div', { class: 'caps brass', style: { fontSize: '13px', letterSpacing: '0.15em' } }, text);
}

export function spinner() { return h('span', { class: 'spinner', role: 'progressbar', 'aria-label': 'Working' }); }

export function progressBar(value, total = 1, muted = false, maxWidth = null) {
  const pct = total > 0 ? Math.max(0, Math.min(1, value / total)) * 100 : 0;
  return h('div', { class: ['progress', muted && 'muted'], style: maxWidth ? { maxWidth } : null, role: 'progressbar', 'aria-valuenow': String(Math.round(pct)), 'aria-valuemin': '0', 'aria-valuemax': '100' },
    h('i', { style: { width: pct.toFixed(2) + '%' } }));
}
