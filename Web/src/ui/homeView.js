// Port of HomeView.swift (with CollectionCard, CollectionSummary, LevelCard, LevelStartSheet,
// SettingsView, HighScoresView): the collection, filters, packs, new levels and the gallery.
import { h } from './vdom.js';
import { icon } from './icons.js';
import {
  pill, toggleSwitch, segmented, sheet, dialog, ratingDots, ratingColor, starRow, highScoreList, sectionTitle, spinner, progressBar,
} from './components.js';
import { cssColor } from './swatch.js';
import { howToSheet } from './howTo.js';
import {
  LevelCatalog, DIFFICULTIES, difficultyTitle, difficultyBlurb, levelChambers, levelTileCount, levelTeamCount, ratingFor,
  RatingFilters, StatusFilters, ChallengeModifier, modifierInfo, ScoreRules, pathStyles, pathStyleInfo, GroundPresets,
  SoundBoard, Sfx, thumbURL, PhotoDetails, packBlurb, formatNumber, HighScoreKinds,
} from './compat.js';
import { runSelfTest } from './selfTest.js';

const THEME_ICONS = { start: 'ant.fill', seasons: 'snowflake', nature: 'leaf.fill', art: 'paintpalette.fill', literature: 'book.fill', history: 'building.columns.fill', science: 'sparkles', skill: 'flame.fill' };

export function homeView(ctx) {
  const { app, ui, size } = ctx;
  const wide = size.w > 700;
  const filtering = app.settings.ratingFilter !== 'all' || app.settings.statusFilter !== 'all';
  const shownCount = filtering ? app.allLevels.filter(l => app.isPlayable(l) && app.passesFilter(l)).length : 0;
  for (const r of app.photoLevels) app.measureIfNeeded(r.level);   // filters need every rating (HomeView.onAppear)
  const mine = app.photoLevels.map(r => r.level).filter(l => app.passesFilter(l));
  return h('div', { class: 'home', key: 'home', ref: el => { ui.homeScroller = el; } },
    h('main', { class: 'home-inner' },
      header(ctx),
      topActions(ctx),
      progressCard(ctx),
      nextUpBanner(ctx),
      collectionBar(ctx),
      filterBar(ctx, filtering, shownCount),
      LevelCatalog.themes.map(t => themeSection(ctx, t, filtering)),
      mine.length ? h('section', { class: 'col', key: 'mine', style: { gap: '16px' } }, sectionTitle('YOUR MOSAICS'),
        h('div', { class: 'two-col' }, mine.map(l => levelCard(ctx, l)))) : null,
      filtering && shownCount === 0 ? h('div', { class: 'card', key: 'empty', style: { fontSize: '15px' } }, emptyFilterText(app)) : null,
      makeNewSection(ctx, wide),
      gallery(ctx),
      h('div', { class: 'row wrap', style: { gap: '12px' } },
        pill('How to play', () => openSheet(ctx, { kind: 'howto' }), { icon: 'questionmark.circle' }),
        pill('Settings & self-test', () => openSheet(ctx, { kind: 'settings' }), { icon: 'gearshape' }))),
    modal(ctx));
}

function openSheet(ctx, s) { ctx.ui.sheet = s; ctx.rerender(); }

function emptyFilterText(app) {
  const parts = [];
  if (app.settings.statusFilter !== 'all') parts.push(`“${StatusFilters.find(f => f.id === app.settings.statusFilter).title}”`);
  if (app.settings.ratingFilter !== 'all') parts.push(`rated ${RatingFilters.find(f => f.id === app.settings.ratingFilter).title} on ${difficultyTitle(app.settings.difficulty)}`);
  return 'No mosaic you can play is ' + parts.join(' and ') + ' yet. Try another filter.';
}

function header(ctx) {
  return h('header', { class: 'col', style: { gap: '6px', paddingTop: '10px' } },
    h('div', { class: 'row' },
      h('span', { class: 'brass' }, icon('ant.fill', 34)),
      h('h1', { class: 'title home-title grow', style: { margin: 0 } }, 'Tessera Colony'),
      h('button', { class: 'iconbtn', type: 'button', 'aria-label': 'How to play', onclick: () => openSheet(ctx, { kind: 'howto' }) }, icon('questionmark.circle', 26)),
      h('button', { class: 'iconbtn', type: 'button', 'aria-label': 'Settings', onclick: () => openSheet(ctx, { kind: 'settings' }) }, icon('gearshape', 26))),
    h('p', { class: 'lede', style: { margin: 0 } }, 'Send the colony out. Carry the mosaic home, one tile at a time.'));
}

function bigButton(ic, title, subtitle, prominent, onclick) {
  return h('button', { class: ['bigbtn', 'pressable', prominent && 'prominent'], type: 'button', onclick },
    h('span', { style: { width: '40px', display: 'flex', justifyContent: 'center' } }, icon(ic, 30)),
    h('span', { class: 'col grow', style: { gap: '2px' } }, h('span', { class: 't' }, title), h('span', { class: 's' }, subtitle)),
    h('span', { style: { opacity: 0.7 } }, icon('chevron.right', 16)));
}

function topActions(ctx) {
  return h('div', { class: 'big-actions' },
    bigButton('person.2.fill', 'Two players', 'Race or share a board on one screen', true, () => openSheet(ctx, { kind: 'versus' })),
    bigButton('trophy.fill', 'High scores', 'Best scores and names per mosaic', false, () => openSheet(ctx, { kind: 'scores', table: 'solo' })));
}

/** Unlock all puzzles, and where progress is kept (with the progress-code backup). */
function progressCard(ctx) {
  const { app, ui, rerender } = ctx;
  const unlocked = app.settings.unlockAll;
  const forgets = app.storageForgets;
  return h('section', { class: 'card col', key: 'progress-card', style: { gap: '12px' } },
    h('div', { class: 'row wrap', style: { gap: '10px 14px' } },
      unlocked
        ? h('div', { class: 'row okc', style: { gap: '8px', fontWeight: 700, fontSize: '15px', flex: '1 1 200px' } }, icon('lock.open.fill', 20), 'All puzzles are unlocked')
        : pill('Unlock all puzzles', () => app.updateSettings(st => { st.unlockAll = true; }), { prominent: true, icon: 'lock.open.fill', iconSize: 18, key: 'unlock-all', cls: 'unlock-all' }),
      unlocked
        ? pill('Lock again', () => app.updateSettings(st => { st.unlockAll = false; }), { icon: 'lock.fill', key: 'relock' })
        : h('div', { class: 'dim', style: { fontSize: '13px', flex: '1 1 200px' } }, 'Play any mosaic now — or keep opening them one by one by finishing the one before.')),
    h('div', { class: ['row', 'top', forgets ? 'brass' : 'dim'], style: { gap: '8px', fontSize: '13px', lineHeight: '1.45', fontWeight: forgets ? 600 : 400 } },
      forgets ? h('span', { style: { paddingTop: '1px' } }, icon('exclamationmark.triangle.fill', 16)) : null,
      h('span', { class: 'grow' }, app.storageNote())),
    h('div', { class: 'row wrap', style: { gap: '10px' } },
      pill('Copy progress code', () => copyProgressCode(ctx), { icon: 'doc.on.doc', key: 'copy-code', prominent: forgets && unlocked }),
      pill('Paste a code', () => { ui.dialog = { kind: 'pasteCode', text: '' }; rerender(); }, { icon: 'square.and.arrow.down', key: 'paste-code' })));
}

/** Builds the code and tries to put it on the clipboard straight from the tap (Safari needs that). */
function copyProgressCode(ctx) {
  const { app, ui, rerender } = ctx;
  const codeP = app.progressCode();
  let copied;
  try {
    if (navigator.clipboard && typeof navigator.clipboard.write === 'function' && typeof ClipboardItem !== 'undefined') {
      const item = new ClipboardItem({ 'text/plain': codeP.then(t => new Blob([t], { type: 'text/plain' })) });
      copied = navigator.clipboard.write([item]).then(() => true, () => false);
    } else if (navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
      copied = codeP.then(t => navigator.clipboard.writeText(t)).then(() => true, () => false);
    } else copied = Promise.resolve(false);
  } catch (e) { copied = Promise.resolve(false); }
  ui.dialog = { kind: 'copyCode', code: null, copied: null };
  rerender();
  codeP.then(code => {
    if (!ui.dialog || ui.dialog.kind !== 'copyCode') return;
    ui.dialog.code = code;
    rerender();
    return copied.then(ok => { if (ui.dialog && ui.dialog.kind === 'copyCode') { ui.dialog.copied = ok; rerender(); } });
  }, () => { ui.dialog = { kind: 'copyCode', code: '', copied: false }; rerender(); });
}

/** Selects the code box and asks the browser to copy it (works in frames where the clipboard API is blocked). */
function selectAndCopy(ui, rerender) {
  const el = document.getElementById('progress-code');
  if (!el) return;
  el.focus();
  el.select();
  try { el.setSelectionRange(0, el.value.length); } catch (e) { /* not a text field */ }
  let ok = false;
  try { ok = document.execCommand('copy'); } catch (e) { ok = false; }
  if (ui.dialog && ui.dialog.kind === 'copyCode') { ui.dialog.copied = ok ? true : 'selected'; rerender(); }
}

function codeDialog(title, body, buttons, onCancel, key) {
  return h('div', { class: 'scrim', key: 'dlg-' + key, onclick: e => { if (e.target === e.currentTarget) onCancel(); } },
    h('div', { class: 'dialog', role: 'dialog', 'aria-modal': 'true', 'aria-label': title },
      h('div', { class: 'title' }, title),
      body,
      h('div', { class: 'btns' }, buttons.map((b, i) => pill(b.label, b.onclick, { prominent: b.prominent, wide: true, disabled: b.disabled, key: 'b' + i })))));
}

function progressDialogs(ctx, d, closeDialog) {
  const { app, ui, rerender } = ctx;
  if (d.kind === 'copyCode') {
    const status = d.code === null ? 'Making your code…'
      : d.code === '' ? "Couldn't make a code in this browser."
        : d.copied === true ? 'Copied. Keep it somewhere safe (Notes, a message to yourself) and paste it here next time with Paste a code.'
          : d.copied === 'selected' ? 'The code is selected — use Copy from your browser’s menu, then keep it somewhere safe.'
            : d.copied === false ? 'Select the whole code below and copy it, then keep it somewhere safe.'
              : 'Copying…';
    const finished = Object.keys(app.progress).length;
    return codeDialog('Progress code', [
      h('div', { class: 'dim', key: 'what', style: { fontSize: '14px', lineHeight: '1.45' } },
        `Holds ${finished} finished mosaic${finished === 1 ? '' : 's'}, your high scores, settings and saved games (not photo mosaics).`),
      h('div', { key: 'st', role: 'status', class: d.copied === true ? 'okc' : 'brass', style: { fontSize: '14px', fontWeight: 600, lineHeight: '1.45' } }, status),
      d.code ? h('textarea', { key: 'box', id: 'progress-code', class: 'codebox', readonly: true, rows: 4, value: d.code, 'aria-label': 'Your progress code', onfocus: e => e.target.select() }) : null,
    ], [
      { label: d.copied === true ? 'Copy again' : 'Select & copy', prominent: d.copied !== true, disabled: !d.code, onclick: () => selectAndCopy(ui, rerender) },
      { label: 'Done', prominent: d.copied === true, onclick: closeDialog },
    ], closeDialog, 'copycode');
  }
  if (d.kind === 'pasteCode') {
    const finished = Object.keys(app.progress).length;
    const load = () => {
      if (d.busy) return;
      d.busy = true; d.error = null; rerender();
      app.loadProgressCode(d.text).then(n => {
        ui.dialog = { kind: 'codeLoaded', count: n };
        rerender();
      }, e => {
        if (ui.dialog === d) { d.busy = false; d.error = (e && e.message) || "That code couldn't be read."; rerender(); }
      });
    };
    return codeDialog('Paste a progress code', [
      h('div', { class: 'dim', key: 'what', style: { fontSize: '14px', lineHeight: '1.45' } },
        finished > 0 ? `Loading a code replaces the progress in this browser (${finished} finished mosaic${finished === 1 ? '' : 's'}) with the code’s.`
          : 'Paste the code you copied last time to get your finished mosaics, high scores and saved games back.'),
      h('textarea', { key: 'box', id: 'paste-code', class: 'codebox', rows: 4, value: d.text || '', placeholder: 'TC1.…', 'aria-label': 'Progress code',
        autocapitalize: 'off', autocomplete: 'off', spellcheck: 'false', oninput: e => { d.text = e.target.value; if (d.error) { d.error = null; rerender(); } } }),
      d.error ? h('div', { key: 'err', role: 'alert', class: 'dangerc', style: { fontSize: '14px', fontWeight: 600 } }, d.error) : null,
    ], [
      { label: d.busy ? 'Loading…' : 'Load progress', prominent: true, disabled: d.busy, onclick: load },
      { label: 'Cancel', onclick: closeDialog },
    ], closeDialog, 'pastecode');
  }
  if (d.kind === 'codeLoaded') {
    return dialog('Progress loaded', `${d.count} finished mosaic${d.count === 1 ? '' : 's'}, plus your high scores, settings and saved games, are back.`,
      [{ label: 'OK', prominent: true, onclick: closeDialog }], closeDialog, 'loaded');
  }
  if (d.kind === 'locked') {
    const level = app.allLevels.find(l => l.id === d.levelID);
    const st = level ? app.status(level) : null;
    const hidden = st && st.kind === 'hidden';
    const why = st && st.kind === 'packLocked' ? `It opens after ${st.label}.`
      : hidden ? (st.more === 1 ? 'Finish 1 more mosaic in this pack to find it.' : `Finish ${st.more} more mosaics in this pack to find it.`) : '';
    return dialog(hidden ? 'Undiscovered mosaic' : 'Locked mosaic', `${why}\nOr unlock every puzzle now and play it straight away.`, [
      { label: 'Unlock all puzzles', prominent: true, onclick: () => { ui.dialog = null; app.updateSettings(x => { x.unlockAll = true; }); ui.sheet = { kind: 'start', levelID: d.levelID }; rerender(); } },
      { label: 'Not now', onclick: closeDialog }], closeDialog, 'locked');
  }
  return null;
}

function nextUpBanner(ctx) {
  const { app } = ctx;
  const next = app.nextUp;
  if (next) {
    return h('div', { class: 'nextup' },
      h('img', { class: 'pix', src: thumbURL(next), alt: '' }),
      h('div', { class: 'col grow', style: { gap: '4px' } },
        h('div', { class: 'caps brass' }, 'Next up'),
        h('div', { class: 'title', style: { fontSize: '24px' } }, next.title),
        h('div', { class: 'dim', style: { fontSize: '13px' } }, `${formatNumber(levelTileCount(next))} tiles · ${levelTeamCount(next)} teams`)),
      pill(app.savedMoves(next) !== null ? 'Resume…' : 'Play…', () => openSheet(ctx, { kind: 'start', levelID: next.id }), { prominent: true }));
  }
  return h('div', { class: 'nextup' },
    h('div', { class: 'col grow', style: { gap: '4px' } },
      h('div', { class: 'caps brass' }, 'All mosaics finished'),
      h('div', { style: { fontSize: '15px' } }, 'Make a new level from a pattern or a photo.')),
    pill('New pattern', () => app.createPatternLevel(), { prominent: true, disabled: app.photoBusy }));
}

function figure(value, caption, ic) {
  return h('div', { class: 'figure col', style: { gap: '2px' } },
    h('div', { class: 'row', style: { gap: '5px' } }, h('span', { class: 'brass' }, icon(ic, 14)), h('span', { class: 'v num' }, value)),
    h('div', { class: 'dim', style: { fontSize: '12px', whiteSpace: 'nowrap' } }, caption));
}

function collectionBar(ctx) {
  const { app } = ctx;
  const p = app.packProgress(LevelCatalog.builtIn);
  return h('section', { class: 'card col', style: { gap: '12px' } },
    h('div', { class: 'row base wrap', style: { gap: '4px 10px' } },
      sectionTitle('YOUR COLLECTION'), h('span', { class: 'grow' }),
      h('span', { class: 'dim', style: { fontSize: '11px' } }, '★ Gentle · ★★ Classic · ★★★ Expert · flame = Expert with a harder option')),
    h('div', { class: 'figures' },
      figure(String(p.found), `of ${p.total} found`, 'magnifyingglass'), figure(String(p.explored), 'explored', 'checkmark.seal.fill'),
      figure(String(p.stars), `of ${p.total * 3} stars`, 'star.fill'), figure(String(p.mastered), 'mastered', 'flame.fill')),
    progressBar(p.stars, Math.max(1, p.total * 3)),
    h('div', { class: 'hscroll' }, LevelCatalog.themes.map(t => {
      const tp = app.packProgress(t.packIDs.flatMap(pid => LevelCatalog.pack(pid)));
      return h('button', {
        key: t.id, class: 'chip', type: 'button', style: { borderColor: tp.open ? 'rgba(217,164,65,.6)' : null },
        'aria-label': `${t.title}: ${tp.explored} of ${tp.total} explored`,
        onclick: () => { const el = document.getElementById('theme-' + t.id); if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' }); },
      }, icon(THEME_ICONS[t.id] || 'sparkles', 13), t.title, h('span', { class: 'sub num' }, `${tp.explored}/${tp.total}`));
    })));
}

function filterBar(ctx, filtering, shownCount) {
  const { app } = ctx;
  const set = fn => app.updateSettings(fn);
  const total = app.allLevels.length;
  const d = difficultyTitle(app.settings.difficulty);
  const note = filtering ? `Showing ${shownCount} of ${total} mosaics (only ones you have found).`
    : `New games start on ${d}; the dots on each card show how hard it is on ${d}. ${total} mosaics.`;
  return h('section', { class: 'card col', style: { gap: '10px' } },
    h('div', { class: 'filter-row' }, h('span', { class: 'caps brass' }, 'Difficulty'),
      segmented(DIFFICULTIES, app.settings.difficulty, v => set(s => { s.difficulty = v; }), 'Difficulty')),
    h('div', { class: 'filter-row' }, h('span', { class: 'caps brass' }, 'Show'),
      h('div', { class: 'hscroll' }, RatingFilters.map(f => h('button', {
        key: f.id, type: 'button', class: ['chip', app.settings.ratingFilter === f.id && 'on'], 'aria-pressed': app.settings.ratingFilter === f.id ? 'true' : 'false',
        onclick: () => set(s => { s.ratingFilter = f.id; }),
      }, f.dotLevel > 0 ? h('i', { style: { width: '9px', height: '9px', borderRadius: '50%', background: ratingColor(f.dotLevel), display: 'block' } }) : null, f.title)))),
    h('div', { class: 'filter-row' }, h('span', { class: 'caps brass' }, 'Status'),
      h('div', { class: 'hscroll' }, StatusFilters.map(f => h('button', {
        key: f.id, type: 'button', class: ['chip', app.settings.statusFilter === f.id && 'on'], 'aria-pressed': app.settings.statusFilter === f.id ? 'true' : 'false',
        onclick: () => set(s => { s.statusFilter = f.id; }),
      }, f.id !== 'all' ? icon(f.icon, 12) : null, f.title)))),
    h('div', { class: 'dim', style: { fontSize: '12px' } }, note));
}

function shelfShows(app, level, filtering) { return filtering ? (app.isPlayable(level) && app.passesFilter(level)) : true; }

function themeSection(ctx, theme, filtering) {
  const { app } = ctx;
  const levels = theme.packIDs.flatMap(pid => LevelCatalog.pack(pid));
  if (!levels.some(l => shelfShows(app, l, filtering))) return null;
  const p = app.packProgress(levels);
  return h('section', { class: 'col', key: 'theme-' + theme.id, id: 'theme-' + theme.id, style: { gap: '18px', scrollMarginTop: '12px' } },
    h('div', { class: 'theme-head' },
      h('span', { class: 'brass' }, icon(THEME_ICONS[theme.id] || 'sparkles', 20)),
      h('h2', { class: 'title', style: { margin: 0 } }, theme.title),
      h('span', { class: 'grow' }),
      h('span', { class: 'dim', style: { fontSize: '13px' } }, `${p.explored} of ${p.total} explored · ${p.stars} ★`)),
    theme.packIDs.map(pid => packShelf(ctx, pid, filtering)));
}

function packLine(id, p) {
  if (!p.open) { const rule = LevelCatalog.packRule(id); if (rule) return `Opens after ${rule.label}`; }
  let s = `${p.found} of ${p.total} found · ${p.explored} explored · ${p.stars} of ${p.total * 3} ★`;
  if (p.mastered > 0) s += ` · ${p.mastered} mastered`;
  return s;
}

function packShelf(ctx, id, filtering) {
  const { app } = ctx;
  const levels = LevelCatalog.pack(id);
  const shown = levels.filter(l => shelfShows(app, l, filtering));
  if (!shown.length) return null;
  const p = app.packProgress(levels);
  return h('div', { class: 'col', key: 'pack-' + id, style: { gap: '8px' } },
    h('div', { class: 'row base wrap', style: { gap: '4px 10px' } },
      sectionTitle(LevelCatalog.packTitle(id)),
      LevelCatalog.isInSeason(id) ? h('span', { class: 'tag', 'aria-label': 'In season now' }, 'IN SEASON') : null,
      h('span', { class: 'dim', style: { fontSize: '12px' } }, packLine(id, p))),
    progressBar(p.explored, Math.max(1, p.total), !p.open, '320px'),
    h('div', { class: 'dim', style: { fontSize: '13px', lineHeight: '1.45', maxWidth: '70ch' } }, id === 'main' ? unlockExplanation(app) : packBlurb(id)),
    h('div', { class: 'shelf-cards' }, shown.map(l => collectionCard(ctx, l))));
}

function unlockExplanation(app) {
  if (app.settings.unlockAll) return 'All puzzles are unlocked.';
  return 'Finish a mosaic on any difficulty to unlock the next one. Sunflower & Monarch is open from the start. Want everything now? Tap Unlock all puzzles at the top — or make a new level below.';
}

function collectionCard(ctx, level) {
  const { app } = ctx;
  const st = app.status(level);
  const playable = st.kind !== 'packLocked' && st.kind !== 'hidden';
  let pic;
  if (st.kind === 'packLocked') {
    pic = h('div', { class: 'pic closed' }, icon('lock.fill', 26), h('div', null, 'Opens after', h('br', null), st.label));
  } else if (st.kind === 'hidden') {
    pic = h('div', { class: 'pic closed' }, h('div', { class: 'q' }, '?'), h('div', null, st.more === 1 ? 'Finish 1 more' : `Finish ${st.more} more`, h('br', null), 'in this pack'));
  } else {
    let badge = null;
    if (st.kind === 'found') badge = h('span', { class: ['tag', st.moves > 0 && 'sand'] }, st.moves > 0 ? 'IN PROGRESS' : 'NEW');
    else if (st.kind === 'mastered') badge = h('span', { class: 'dangerc', style: { background: 'rgba(28,21,17,.85)', borderRadius: '50%', padding: '5px', display: 'inline-flex' } }, icon('flame.fill', 14));
    pic = h('div', { class: ['pic', st.kind === 'found' && 'found', st.kind === 'mastered' && 'mastered'] },
      h('img', { class: 'pix', src: thumbURL(level), alt: '', loading: 'lazy' }), badge ? h('span', { class: 'badge' }, badge) : null);
  }
  const stats = playable ? app.difficultyStats(level) : null;
  const title = st.kind === 'packLocked' ? 'Locked' : st.kind === 'hidden' ? 'Undiscovered' : level.title;
  const label = st.kind === 'packLocked' ? `Locked mosaic. Opens after ${st.label}. Tap to unlock all puzzles.`
    : st.kind === 'hidden' ? `Undiscovered mosaic. Finish ${st.more} more in this pack to find it, or tap to unlock all puzzles.`
    : st.kind === 'found' ? `${level.title}, ${st.moves > 0 ? 'in progress' : 'new'}`
    : st.kind === 'explored' ? `${level.title}, explored, ${st.stars} of 3 stars` : `${level.title}, mastered`;
  return h('button', { key: level.id, type: 'button', class: ['ccard', 'pressable', !playable && 'locked'], 'aria-label': label,
    onclick: () => { if (playable) openSheet(ctx, { kind: 'start', levelID: level.id }); else { ctx.ui.dialog = { kind: 'locked', levelID: level.id }; ctx.rerender(); } } },
  pic,
  h('div', { class: 'name', style: { color: playable ? 'var(--sand)' : 'var(--sand-dim)' } }, title),
  h('div', { class: 'foot' },
    stats ? ratingDots(ratingFor(stats, app.settings.difficulty).level, 8) : null,
    h('span', { class: 'grow' }),
    st.kind === 'explored' ? starRow(st.stars) : st.kind === 'mastered' ? starRow(3, true) : null));
}

function levelCard(ctx, level) {
  const { app, ui, rerender } = ctx;
  const saved = app.savedMoves(level);
  const done = app.progress[level.id];
  const requirement = app.unlockRequirement(level);
  const stats = app.difficultyStats(level);
  if (!stats) app.measureIfNeeded(level);
  return h('div', { class: 'panel levelcard', key: 'lc-' + level.id },
    h('img', { class: 'thumb pix', src: thumbURL(level), alt: '' }),
    h('div', { class: 'row base' }, h('div', { class: 'title grow', style: { fontSize: '22px' } }, level.title),
      done ? h('span', { class: 'row okc', style: { fontWeight: 700, fontSize: '13px', gap: '4px' } }, icon('checkmark.seal.fill', 15), 'Completed') : null),
    h('div', { class: 'dim', style: { fontSize: '14px' } }, `${level.subtitle} · ${formatNumber(levelTileCount(level))} tiles · ${levelTeamCount(level)} teams in ${level.tunnels.length} tunnels`),
    ratingLine(stats, app.settings.difficulty),
    h('div', { class: 'row' },
      requirement ? h('span', { class: 'brass', style: { fontWeight: 700 } }, `Locked — finish ${requirement} to unlock`)
        : pill(saved !== null ? `Resume (${saved} moves)…` : done ? 'Play again…' : 'Play…', () => openSheet(ctx, { kind: 'start', levelID: level.id }), { prominent: true }),
      h('span', { class: 'grow' }),
      level.isPhoto ? h('button', { class: 'iconbtn dangerc', type: 'button', 'aria-label': 'Delete this mosaic', onclick: () => { ui.dialog = { kind: 'deletePhoto', id: level.id }; rerender(); } }, icon('trash', 20)) : null));
}

function ratingLine(stats, difficulty) {
  if (!stats) return h('div', { class: 'row dim', style: { fontSize: '13px' } }, spinner(), 'Measuring how hard it is…');
  const r = ratingFor(stats, difficulty);
  return h('div', { class: 'row', style: { gap: '8px', fontSize: '13px' } },
    h('span', { class: 'dim' }, `${difficultyTitle(difficulty)}:`), h('span', { style: { fontWeight: 700, color: ratingColor(r.level) } }, r.word), ratingDots(r.level));
}

function makeNewSection(ctx, wide) {
  const { app, ui, rerender } = ctx;
  return h('section', { class: 'col', style: { gap: '12px' } },
    sectionTitle('MAKE A NEW LEVEL'),
    h('div', { class: 'make-grid' },
      h('div', { class: 'panel make-card' },
        h('div', { class: 'row title', style: { fontSize: '20px' } }, h('span', { class: 'brass' }, icon('sparkles', 20)), 'Pattern mosaic'),
        h('div', { class: 'dim grow', style: { fontSize: '14px' } }, 'A fresh pattern (about 2,400 tiles) every time you tap — a rosette, a starburst, fish scales, a kaleidoscope or crossed ribbons, each drawn new from its own seed. Each one is planned and checked so it can be solved.'),
        h('div', null, pill(app.photoBusy ? 'Building…' : 'New pattern', () => app.createPatternLevel(), { prominent: true, icon: 'wand.and.stars', disabled: app.photoBusy }))),
      h('div', { class: 'panel make-card' },
        h('div', { class: 'row title', style: { fontSize: '20px' } }, h('span', { class: 'brass' }, icon('photo.on.rectangle.angled', 20)), 'From your photo'),
        h('div', { class: 'dim', style: { fontSize: '14px' } }, 'White and near-white areas become open ground; every coloured tile is part of the puzzle. The photo stays on this device.'),
        segmented(PhotoDetails, app.settings.photoDetail, v => app.updateSettings(s => { s.photoDetail = v; }), 'Tile size'),
        h('div', null,
          pill(app.photoBusy ? 'Building…' : 'Choose a photo', () => { const el = document.getElementById('photo-input'); if (el) el.click(); }, { prominent: true, icon: 'photo', disabled: app.photoBusy }),
          h('input', { id: 'photo-input', type: 'file', accept: 'image/*', tabindex: '-1', 'aria-hidden': 'true', style: { display: 'none' },
            onchange: e => { const f = e.target.files && e.target.files[0]; e.target.value = ''; if (f) app.importPhotoFile(f); } })))),
    app.photoBusy ? h('div', { class: 'row dim', style: { fontSize: '13px' } }, spinner(), 'Planning teams and tunnels…') : null,
    app.photoMessage ? h('div', { class: 'raised row top', style: { padding: '12px' } },
      h('span', { class: 'brass' }, icon('info.circle.fill', 18)), h('div', { class: 'grow', style: { fontSize: '14px' } }, app.photoMessage),
      pill('OK', () => { app.photoMessage = null; app.notify(); })) : null);
}

function gallery(ctx) {
  const { app } = ctx;
  const done = app.allLevels.filter(l => app.progress[l.id]);
  return h('section', { class: 'col', style: { gap: '12px' } },
    sectionTitle('NEST GALLERY'),
    h('div', { class: 'dim', style: { fontSize: '14px' } }, 'Mosaics your colony has carried home and re-laid underground.'),
    done.length === 0 ? h('div', { class: 'dim', style: { fontSize: '14px' } }, 'Nothing here yet — finish a mosaic and it hangs here.')
      : h('div', { class: 'gallery' }, done.map(l => {
        const rec = app.progress[l.id];
        const secs = Math.floor(rec.bestSeconds);
        return h('div', { class: 'gframe', key: 'g-' + l.id },
          h('div', { class: 'pic' }, h('img', { class: 'pix', src: thumbURL(l), alt: '', loading: 'lazy' })),
          h('div', { class: 'title', style: { fontSize: '15px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' } }, l.title),
          h('div', { class: 'dim', style: { fontSize: '12px' } }, `Best ${Math.floor(secs / 60)}:${String(secs % 60).padStart(2, '0')} · ${difficultyTitle(rec.difficulty)}`));
      })));
}

// MARK: - Sheets and dialogs

function modal(ctx) {
  return [sheetFor(ctx), dialogFor(ctx)];
}

function dialogFor(ctx) {
  const { app, ui, rerender } = ctx;
  const closeDialog = () => { ui.dialog = null; rerender(); };
  const d = ui.dialog;
  if (!d) return null;
  const pd = progressDialogs(ctx, d, closeDialog);
  if (pd) return pd;
  if (d.kind === 'deletePhoto') return dialog('Delete this mosaic?', null,
    [{ label: 'Delete', prominent: true, destructive: true, onclick: () => { ui.dialog = null; app.deletePhotoLevel(d.id); rerender(); } }, { label: 'Cancel', onclick: closeDialog }], closeDialog);
  if (d.kind === 'reset') return dialog('Reset all progress?', 'Clears finished mosaics, saved games, high scores and settings.',
    [{ label: 'Reset', prominent: true, destructive: true, onclick: () => { ui.dialog = null; app.resetEverything(); rerender(); } }, { label: 'Cancel', onclick: closeDialog }], closeDialog);
  if (d.kind === 'clearScores') return dialog('Clear all high scores?', 'Both the solo and two-player tables are emptied. Finished mosaics and best times are kept.',
    [{ label: 'Clear', prominent: true, destructive: true, onclick: () => { ui.dialog = null; app.clearHighScores(); rerender(); } }, { label: 'Cancel', onclick: closeDialog }], closeDialog);
  return null;
}

function sheetFor(ctx) {
  const { app, ui, rerender } = ctx;
  const close = () => { ui.sheet = null; rerender(); };
  const s = ui.sheet;
  if (!s) return null;
  if (s.kind === 'howto') return howToSheet(close);
  if (s.kind === 'settings') return settingsSheet(ctx, close);
  if (s.kind === 'scores') return scoresSheet(ctx, close);
  if (s.kind === 'start') {
    const level = app.allLevels.find(l => l.id === s.levelID);
    return level ? startSheet(ctx, level, close) : null;
  }
  if (s.kind === 'versus' && ctx.versusSetupSheet) return ctx.versusSetupSheet(ctx, close);
  return null;
}

function startSheet(ctx, level, close) {
  const { app, ui, rerender } = ctx;
  const saved = app.savedGame(level);
  if (!ui.start || ui.start.levelID !== level.id) {
    ui.start = { levelID: level.id, choice: saved ? saved.difficulty : app.settings.difficulty, mods: new Set(app.settings.lastModifiers || []) };
  }
  const st = ui.start;
  const stats = app.difficultyStats(level);
  if (!stats) app.measureIfNeeded(level);
  const savedMoveCount = app.savedMoves(level) || 0;
  const suffix = st.mods.size ? ` · ${st.mods.size} harder` : '';
  const start = (fresh) => { const choice = st.choice, mods = new Set(st.mods); ui.sheet = null; ui.start = null; if (fresh) app.play(level, true, choice, mods); else app.play(level, false); };
  const bestText = d => {
    const rec = app.progress[level.id];
    const secs = rec && rec.bestByDifficulty ? rec.bestByDifficulty[d] : undefined;
    if (secs === undefined || secs === null) return null;
    const s = Math.floor(secs);
    return `Your best: ${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
  };
  const top = app.topScores('solo', level.id);
  const footer = saved
    ? [pill(`Resume · ${difficultyTitle(saved.difficulty)} · ${savedMoveCount} move${savedMoveCount === 1 ? "" : "s"}`, () => start(false), { prominent: true, wide: true, key: 'resume' }),
      pill(`New game on ${difficultyTitle(st.choice)}${suffix}`, () => start(true), { wide: true, key: 'new' })]
    : [pill(`Start on ${difficultyTitle(st.choice)}${suffix}`, () => start(true), { prominent: true, wide: true, key: 'start' })];
  return sheet(level.title, () => { ui.start = null; close(); }, [
    h('div', { class: 'row top', style: { gap: '16px' } },
      h('img', { class: 'pix', src: thumbURL(level), alt: '', style: { width: '84px', height: '96px', objectFit: 'contain', borderRadius: '8px', border: '2px solid var(--panel-edge)', background: 'var(--frame)' } }),
      h('div', { class: 'col grow', style: { gap: '4px' } },
        level.pack !== 'main' && !level.isPhoto ? h('div', { class: 'caps', style: { color: level.isChallenge ? 'var(--danger)' : 'var(--ok)' } }, LevelCatalog.packTitle(level.pack)) : null,
        h('div', { class: 'title', style: { fontSize: '24px' } }, level.title),
        h('div', { class: 'dim', style: { fontSize: '14px' } }, level.subtitle),
        h('div', { class: 'dim', style: { fontSize: '13px' } }, `${formatNumber(levelTileCount(level))} tiles · ${levelTeamCount(level)} teams · ${level.tunnels.length} tunnels`),
        app.progress[level.id] ? h('div', { class: 'row', style: { gap: '8px' } }, starRow(app.stars(level.id), app.isMastered(level.id), 14),
          h('span', { class: 'dim', style: { fontSize: '12px' } }, app.isMastered(level.id) ? 'Mastered' : 'Stars: Gentle · Classic · Expert')) : null)),
    sectionTitle('CHOOSE A DIFFICULTY'),
    DIFFICULTIES.map(d => {
      const selected = d.id === st.choice;
      const r = stats ? ratingFor(stats, d.id) : null;
      const best = bestText(d.id);
      return h('button', { key: d.id, type: 'button', class: ['diff-row', selected && 'on'], role: 'radio', 'aria-checked': selected ? 'true' : 'false',
        onclick: () => { st.choice = d.id; rerender(); } },
      h('span', { style: { color: selected ? 'var(--brass)' : 'var(--sand-dim)' } }, icon(selected ? 'largecircle.fill.circle' : 'circle', 22)),
      h('div', { class: 'col grow', style: { gap: '4px' } },
        h('div', { class: 'row base' }, h('span', { class: 'title grow', style: { fontSize: '19px' } }, d.title),
          h('span', { class: 'brass num', style: { fontSize: '14px', fontWeight: 700 } }, `${levelChambers(level, d.id)} slots`)),
        selected ? h('div', { class: 'dim', style: { fontSize: '13px' } }, difficultyBlurb(d.id)) : null,
        r ? h('div', { class: 'row wrap', style: { gap: '4px 8px' } }, ratingDots(r.level, 10),
          h('span', { style: { fontWeight: 700, fontSize: '14px', color: ratingColor(r.level) } }, r.word),
          h('span', { class: 'dim', style: { fontSize: '13px' } }, `· careless tapping wins ${Math.round(stats.careless[DIFFICULTIES.indexOf(d)] * 100)}%`)) : null,
        selected && r ? h('div', { style: { fontSize: '13px', opacity: 0.9 } }, r.explanation) : null,
        best ? h('div', { class: 'okc', style: { fontSize: '12px', fontWeight: 700 } }, best) : null));
    }),
    stats ? null : h('div', { class: 'row dim', style: { fontSize: '13px' } }, spinner(), 'Measuring how hard this mosaic is on each difficulty…'),
    h('div', { class: 'dim', style: { fontSize: '12px', opacity: 0.85 } }, 'Ratings come from computer play-throughs of this mosaic: how often careless tapping wins, and whether always sending a team that can finish right now is enough.'),
    h('div', { class: 'row base' }, sectionTitle('HARDER OPTIONS'), h('span', { class: 'grow' }),
      h('span', { class: 'num', style: { fontWeight: 700, fontSize: '14px' } }, 'Score ×' + (ScoreRules.difficultyFactor(st.choice) * ScoreRules.modifierFactor(st.mods)).toFixed(2))),
    h('div', { class: 'mod-grid' }, ChallengeModifier.allCases.map(m => {
      const on = st.mods.has(m);
      const info = modifierInfo(m);
      return h('button', { key: m, type: 'button', class: ['mod-chip', on && 'on'], 'aria-pressed': on ? 'true' : 'false',
        'aria-label': `${info.title}, plus ${Math.round(info.bonus * 100)} percent score. ${info.blurb}`,
        onclick: () => { if (on) st.mods.delete(m); else st.mods.add(m); rerender(); } },
      h('span', { style: { color: on ? 'var(--brass)' : 'var(--sand-dim)' } }, icon(on ? 'checkmark.square.fill' : 'square', 18)),
      h('span', { style: { color: on ? 'var(--danger)' : 'var(--sand-dim)' } }, icon(info.systemImage, 15)),
      h('span', { class: 'grow', style: { fontWeight: 600, fontSize: '14px' } }, info.title),
      h('span', { style: { fontSize: '12px', fontWeight: 700, color: on ? 'var(--brass)' : 'var(--sand-dim)' } }, `+${Math.round(info.bonus * 100)}%`));
    })),
    h('div', { class: 'dim', style: { fontSize: '12px' } }, st.mods.size === 0 ? 'Optional. Each one makes any mosaic harder and raises your score. None of them makes a mosaic impossible.'
      : ChallengeModifier.sorted(st.mods).map(m => modifierInfo(m).blurb).join(' ')),
    sectionTitle('HIGH SCORES'),
    top.length === 0 ? h('div', { class: 'dim', style: { fontSize: '13px' } }, 'No high score on this mosaic yet — finish it to put your name here.') : highScoreList(top),
  ], { key: 'start-' + level.id, large: true, footer, leading: h('span', { style: { width: '60px' } }) });
}

function settingsSheet(ctx, close) {
  const { app, ui, rerender } = ctx;
  const s = app.settings;
  const set = fn => app.updateSettings(fn);
  const row = (label, control, id) => h('label', { class: 'form-row', for: id || null }, h('span', { class: 'grow' }, label), control);
  const soundOff = !s.soundOn;
  return sheet('Settings', close, [
    h('div', { class: 'form-section' }, h('div', { class: 'caps' }, 'Play'),
      h('div', { class: 'form-group' },
        row('Detailed legs (feet plant and lift)', toggleSwitch('set-legs', s.detailedAnts, v => set(x => { x.detailedAnts = v; })), 'set-legs'),
        row('Unlock all puzzles', toggleSwitch('set-unlock', s.unlockAll, v => set(x => { x.unlockAll = v; })), 'set-unlock'),
        h('div', { class: 'form-row stack' }, h('label', { for: 'set-speed' }, 'Default ant speed: ' + s.antSpeed.toFixed(2) + '×'),
          h('input', { id: 'set-speed', type: 'range', min: '0.1', max: '16', step: '0.05', value: String(s.antSpeed), oninput: e => set(x => { x.antSpeed = parseFloat(e.target.value); }) })))),
    h('div', { class: 'form-section' }, h('div', { class: 'caps' }, 'Ant paths'),
      h('div', { class: 'form-group' }, row('Ant paths', h('select', { id: 'set-paths', onchange: e => set(x => { x.pathStyle = e.target.value; }) },
        pathStyles().map(p => h('option', { key: p.id, value: p.id, selected: p.id === s.pathStyle }, p.title))), 'set-paths')),
      h('div', { class: 'form-foot' }, pathStyleInfo(s.pathStyle).blurb + ' Applies to ants launched after you change it; ants already walking finish their route. Ants carrying a tile always come home in the middle lane.')),
    h('div', { class: 'form-section' }, h('div', { class: 'caps' }, 'Sound'),
      h('div', { class: 'form-group' },
        row('Sound effects', toggleSwitch('set-sound', s.soundOn, v => set(x => { x.soundOn = v; })), 'set-sound'),
        h('div', { class: 'form-row stack' }, h('label', { for: 'set-vol', style: { opacity: soundOff ? 0.5 : 1 } }, `Volume: ${Math.round(s.soundVolume * 100)}%`),
          h('input', { id: 'set-vol', type: 'range', min: '0', max: '1', step: '0.01', value: String(s.soundVolume), disabled: soundOff,
            oninput: e => set(x => { x.soundVolume = parseFloat(e.target.value); }), onchange: () => SoundBoard.shared.play(Sfx.teamDone) })),
        h('div', { class: 'form-row' }, h('label', { class: 'grow', for: 'set-actions' }, 'Action sounds'), pill('Play a sample', () => SoundBoard.shared.playSample('action'), { disabled: soundOff }),
          toggleSwitch('set-actions', s.actionSounds, v => set(x => { x.actionSounds = v; }), soundOff)),
        h('div', { class: 'form-row' }, h('label', { class: 'grow', for: 'set-goals' }, 'Goal sounds'), pill('Play a sample', () => SoundBoard.shared.playSample('goal'), { disabled: soundOff }),
          toggleSwitch('set-goals', s.goalSounds, v => set(x => { x.goalSounds = v; }), soundOff)),
        row('Colony clinks (ants lifting and delivering tiles)', toggleSwitch('set-clinks', s.tileClicks, v => set(x => { x.tileClicks = v; }), soundOff), 'set-clinks'),
        row('Play sounds even in Silent mode (iPhone, where supported)', toggleSwitch('set-silent', s.soundInSilentMode, v => set(x => { x.soundInSilentMode = v; }), soundOff), 'set-silent'),
        h('div', { class: 'form-row stack' },
          h('button', { type: 'button', class: 'row brass', style: { fontWeight: 600, minHeight: '36px' }, onclick: () => {
            const played = SoundBoard.shared.playTestSound();
            setTimeout(() => { ui.soundReport = app.soundReport(played); rerender(); }, 400);
          } }, icon('speaker.wave.3', 18), 'Sound check: play a test chime'),
          ui.soundReport ? h('div', { class: 'mono' }, ui.soundReport) : null)),
      h('div', { class: 'form-foot' }, 'Action sounds are dry wood and clay: sending, scouting, undo, adding a slot, returning a team, a refused tap, a team that must wait, blocked, hints. Goal sounds are bells and glass: a team finishing, a whole colour lifted, each quarter of the mosaic home, the finished mosaic, a new best time and a newly unlocked mosaic. Colony clinks give every colour its own note. Everything is synthesized in the browser; it starts after your first tap.')),
    h('div', { class: 'form-section' }, h('div', { class: 'caps' }, 'Ground colour behind the mosaic'),
      h('div', { class: 'form-group' }, h('div', { class: 'form-row stack' },
        h('div', { class: 'swatches' }, GroundPresets.all.map(([name, col]) => h('button', { key: name, type: 'button', class: ['swatch-btn', s.groundColor === col && 'on'], onclick: () => set(x => { x.groundColor = col; }) },
          h('i', { style: { background: cssColor(col) } }), name))),
        h('label', { class: 'row', for: 'set-ground' }, h('span', { class: 'grow' }, 'Any colour'),
          h('input', { id: 'set-ground', type: 'color', value: cssColor(s.groundColor), oninput: e => set(x => { x.groundColor = parseInt(e.target.value.slice(1), 16); }) })))),
      h('div', { class: 'form-foot' }, 'You can also change it during a game from the menu (…).')),
    h('div', { class: 'form-section' }, h('div', { class: 'caps' }, 'Diagnostics'),
      h('div', { class: 'form-group' },
        h('div', { class: 'form-row' }, pill(ui.testRunning ? 'Running…' : 'Run engine self-test', () => {
          ui.testRunning = true; ui.testResults = null; rerender();
          setTimeout(() => runSelfTest(results => { ui.testResults = results; ui.testRunning = false; rerender(); }, () => rerender()), 30);
        }, { disabled: !!ui.testRunning })),
        (ui.testResults || []).map((r, i) => h('div', { class: 'form-row top', key: 'r' + i, style: { alignItems: 'flex-start' } },
          h('span', { style: { color: r.passed ? 'var(--ok)' : 'var(--danger)' } }, icon(r.passed ? 'checkmark.circle.fill' : 'xmark.octagon.fill', 18)),
          h('div', { class: 'col', style: { gap: '2px' } }, h('div', { style: { fontWeight: 600, fontSize: '14px' } }, r.name), r.detail ? h('div', { class: 'dim', style: { fontSize: '12px' } }, r.detail) : null)))),
      h('div', { class: 'form-foot' }, 'Replays each mosaic’s designed solution and compares it with values computed by the reference model, exercises undo, recovery options and save/restore, and times the ant drawing. Please screenshot the results if anything fails.')),
    h('div', { class: 'form-section' },
      h('div', { class: 'form-group' },
        h('div', { class: 'form-row' }, h('button', { type: 'button', class: 'brass', style: { fontWeight: 600 }, onclick: () => set(x => { x.coachSeen = []; }) }, 'Replay the tutorial tips')),
        h('div', { class: 'form-row' }, h('button', { type: 'button', class: 'dangerc', style: { fontWeight: 600 }, onclick: () => { ui.dialog = { kind: 'reset' }; rerender(); } }, 'Reset all progress')))),
    h('div', { class: 'form-foot' }, app.storageNote ? app.storageNote() : ''),
  ], { key: 'settings', large: true });
}

function scoresSheet(ctx, close) {
  const { app, ui, rerender } = ctx;
  const kind = ui.sheet.table || 'solo';
  const levels = app.allLevels.filter(l => app.topScores(kind, l.id).length > 0);
  const anyScores = app.allLevels.some(l => app.topScores('solo', l.id).length || app.topScores('versus', l.id).length);
  return sheet('High scores', close, [
    segmented(HighScoreKinds, kind, v => { ui.sheet = { kind: 'scores', table: v }; rerender(); }, 'Table'),
    h('div', { class: 'dim', style: { fontSize: '13px' } }, kind === 'solo'
      ? 'Score = tiles × difficulty (Gentle ×0.5, Classic ×1, Expert ×1.5) × harder options (up to ×2), minus 5 per undo, 25 per hint and 25 per assist. Ties go to the faster time. Each mosaic keeps its top 5.'
      : 'The winner’s match score (tiles home, finish bonus, minus penalties). Each mosaic keeps its top 5 with the options that were played.'),
    levels.length === 0 ? h('div', { class: 'col', style: { alignItems: 'center', padding: '40px 0', gap: '10px', textAlign: 'center' } },
      h('span', { style: { color: 'var(--panel-edge)' } }, icon('trophy', 44)),
      h('div', { style: { fontSize: '15px' } }, kind === 'solo' ? 'No high scores yet. Finish a mosaic and put your name on its table.' : 'No two-player high scores yet. The winner of a match can save theirs.')) : null,
    levels.map(l => h('div', { class: 'card col', key: 'hs-' + l.id, style: { gap: '8px' } },
      h('div', { class: 'row', style: { gap: '12px' } }, h('img', { class: 'pix', src: thumbURL(l), alt: '', style: { width: '44px', height: '50px', objectFit: 'contain', borderRadius: '6px' } }),
        h('div', { class: 'col', style: { gap: '2px' } }, h('div', { class: 'title', style: { fontSize: '19px' } }, l.title), h('div', { class: 'dim', style: { fontSize: '12px' } }, `${formatNumber(levelTileCount(l))} tiles`))),
      highScoreList(app.topScores(kind, l.id)))),
  ], { key: 'scores', large: true, leading: h('button', { class: 'textbtn', type: 'button', style: { color: anyScores ? 'var(--danger)' : 'var(--panel-edge)' }, disabled: !anyScores, onclick: () => { ui.dialog = { kind: 'clearScores' }; rerender(); } }, 'Clear…') });
}
