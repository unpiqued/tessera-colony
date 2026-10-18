// Port of VersusView.swift: two players on one screen. Landscape: side by side. Portrait: face to
// face (the top half is turned round for the player sitting opposite). Race = two boards; Shared =
// one board in the middle with two ant hills.
import { h } from './vdom.js';
import { icon } from './icons.js';
import { pill, sheet, dialog, segmented, teamFace, chamberPod, highScoreList, sectionTitle } from './components.js';
import {
  VersusBoardCanvas, VersusRules, versusOptions, versusOptionTitle, versusOptionBlurb, DIFFICULTIES, levelChambers,
  LevelCatalog, thumbURL, levelTileCount, paletteName, formatNumber, PLAYER_COLORS, defaultVersusRules, swiftRounded,
} from './compat.js';
import { VersusController } from './versusController.js';
import { pieceStyle } from './swatch.js';

const LOG_LO = Math.log(0.1), LOG_HI = Math.log(16);
const hex = c => '#' + c.toString(16).padStart(6, '0');

function mountVersusBoard(el, c, index, w, hgt) {
  const old = c.boardCanvases[index];
  if (old) { try { old.destroy(); } catch (e) { /* gone */ } }
  const canvas = document.createElement('canvas');
  el.appendChild(canvas);
  const bc = new VersusBoardCanvas(canvas, c, index);
  bc.setSize(w, hgt);
  c.boardCanvases[index] = bc;
}

function boardBox(c, index, w, hgt) {
  const b = c.board(index);
  const cs = Math.max(2, Math.min(w / b.cols, hgt / b.rows));
  const bw = Math.floor(b.cols * cs), bh = Math.floor(b.rows * cs);
  const bc = c.boardCanvases[index];
  if (bc && (bc._fitW !== w || bc._fitH !== hgt)) { bc._fitW = w; bc._fitH = hgt; bc.setSize(w, hgt); }
  return h('div', { class: 'vboard', key: 'vb' + index, style: { width: w + 'px', height: hgt + 'px', display: 'flex', alignItems: 'center', justifyContent: 'center', flex: 'none' } },
    h('div', { class: 'board-wrap', key: 'vbw' + index + '-' + c.uid, style: { width: bw + 'px', height: bh + 'px', borderRadius: '10px', border: '1px solid var(--panel-edge)' },
      ref: el => mountVersusBoard(el, c, index, w, hgt), 'aria-label': 'Mosaic board' }));
}

export function versusView(ctx) {
  const { app, match: c, ui, size, rerender } = ctx;
  const wide = size.w >= size.h;
  const accent = p => hex(PLAYER_COLORS[p]);
  const rules = c.rules;
  const topBar = h('div', { class: 'row', style: { gap: '12px', minHeight: '40px' } },
    h('button', { class: 'iconbtn', type: 'button', 'aria-label': 'Leave the match', onclick: () => { ui.dialog = { kind: 'quit' }; rerender(); } }, icon('xmark.circle.fill', 26)),
    h('div', { class: 'dim grow', style: { fontSize: '12px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' } },
      `${c.level.title} · ${versusOptionTitle('layout', rules.layout)} · ${versusOptionTitle('picking', rules.picking)} · ${versusOptionTitle('colour', rules.colour)} · ${versusOptionTitle('scoring', rules.scoring)} · ${DIFFICULTIES.find(d => d.id === rules.difficulty).title}`),
    h('span', { class: 'dim' }, icon('tortoise.fill', 18)),
    h('input', { id: 'vs-speed', type: 'range', min: '0', max: '1', step: '0.001', style: { maxWidth: '220px' }, 'aria-label': 'Ant speed',
      value: String((Math.log(c.speed) - LOG_LO) / (LOG_HI - LOG_LO)), oninput: e => c.setSpeed(Math.exp(LOG_LO + parseFloat(e.target.value) * (LOG_HI - LOG_LO))) }),
    h('span', { class: 'num', style: { fontSize: '12px', fontWeight: 700, width: '40px' } }, c.speed.toFixed(1) + '×'));

  const availH = size.h - 20 - 46;
  const availW = size.w - 20;
  let body;
  if (rules.layout === 'race') {
    const col = (p, w, hgt, rotated) => h('div', { key: 'rc' + p, class: 'col', style: { gap: '6px', padding: '8px', borderRadius: '18px', background: 'rgba(47,36,28,.85)', border: `2px solid ${accent(p)}b3`,
      width: w + 'px', transform: rotated ? 'rotate(180deg)' : null } },
    boardBox(c, p, w - 16, Math.max(80, hgt - 16 - controlsHeight(c))), versusControls(ctx, p));
    body = wide
      ? h('div', { class: 'row', style: { gap: '10px', alignItems: 'stretch' } }, col(0, (availW - 10) / 2, availH, false), col(1, (availW - 10) / 2, availH, false))
      : h('div', { class: 'col', style: { gap: '8px' } }, col(1, availW, (availH - 8) / 2, true), col(0, availW, (availH - 8) / 2, false));
  } else {
    if (wide) {
      const cw = Math.min(330, size.w * 0.28);
      body = h('div', { class: 'row', style: { gap: '10px', alignItems: 'flex-start' } },
        h('div', { style: { width: cw + 'px' } }, versusControls(ctx, 0)),
        boardBox(c, 0, availW - 2 * cw - 20, availH),
        h('div', { style: { width: cw + 'px' } }, versusControls(ctx, 1)));
    } else {
      const ch = controlsHeight(c);
      body = h('div', { class: 'col', style: { gap: '6px' } },
        h('div', { style: { transform: 'rotate(180deg)' } }, versusControls(ctx, 1)),
        boardBox(c, 0, availW, Math.max(80, availH - 2 * ch - 12)),
        versusControls(ctx, 0));
    }
  }
  const bgc = c.groundColor;
  return h('div', { class: 'game', key: 'versus-' + c.uid, style: { background: `rgb(${((bgc >> 16) & 255) * 0.5 | 0},${((bgc >> 8) & 255) * 0.5 | 0},${(bgc & 255) * 0.5 | 0})` } },
    h('div', { class: 'col', style: { gap: '6px', padding: '10px', height: '100%' } }, topBar, body),
    c.result ? h('div', { class: 'overlay-scrim', key: 'vres', style: { background: 'rgba(0,0,0,.55)', alignItems: 'flex-start' } }, resultCard(ctx)) : null,
    ui.dialog && ui.dialog.kind === 'quit' ? dialog('Leave this match?', null, [
      { label: 'Leave', prominent: true, destructive: true, onclick: () => { ui.dialog = null; app.endVersus(); } },
      { label: 'Keep playing', onclick: () => { ui.dialog = null; rerender(); } }], () => { ui.dialog = null; rerender(); }) : null);
}

function controlsHeight(c) {
  const reach = c.rules.picking === 'reach3' ? 3 : 1;
  return 70 + 44 + 54 + (reach - 1) * 46 + Math.max(0, 7 - reach) * 26 + 34;
}

function versusControls(ctx, p) {
  const { match: c } = ctx;
  const accent = hex(PLAYER_COLORS[p]);
  const cap = c.capacity(p);
  const t = c.now;
  const waiting = c.waiting(p);
  const working = c.working(p, t);
  const pod = 38;
  const reach = VersusRules.reachDepth(c.rules);
  const pods = [];
  working.forEach((w, i) => pods.push(h('span', { key: 'w' + i }, chamberPod(c.palette, { family: w.family, remaining: w.left }, pod))));
  waiting.forEach((w, i) => pods.push(h('button', { key: 'q' + i, type: 'button', style: { borderRadius: '12px', boxShadow: '0 0 0 2px var(--brass)' }, onclick: () => c.returnTeam(p, w.uid),
    'aria-label': `Waiting team, needs ${w.remaining} more. Tap to return it to its tunnel, costs ${Math.round(VersusRules.returnPenalty)} points.` },
  chamberPod(c.palette, { family: w.family, remaining: w.remaining }, pod, { badge: h('span', { class: 'rb', style: { width: '15px', height: '15px', top: '-4px', right: '-4px' } }, icon('arrow.uturn.down', 9)) }))));
  for (let k = 0; k < Math.max(0, cap - working.length - waiting.length); k++) pods.push(h('span', { key: 'o' + k }, chamberPod(c.palette, null, pod)));
  const tunnels = [];
  for (let q = 0; q < c.tunnelCount; q++) {
    const queue = c.queue(p, q);
    const items = queue.slice(0, 7).map((team, d) => {
      if (d < reach) {
        const why = c.refusal(p, q, d);
        return teamFace(c.palette, team.family, team.remaining, d === 0 ? 54 : 42, why ? 'dim' : null, {
          key: 'd' + d, onclick: () => c.launch(p, q, d),
          'aria-label': `${paletteName(c.palette, team.family)} team of ${team.remaining}` + (d > 0 ? `, ${d} back in the queue` : ''),
          children: d > 0 ? h('span', { class: 'sametag', style: { top: '3px', bottom: 'auto', left: 'auto', right: '3px', transform: 'none' } }, `−${Math.round(d * VersusRules.skipPenalty)}`) : null,
        });
      }
      return h('div', { key: 'd' + d, class: 'minichip num ink', style: pieceStyle(c.palette, team.family, 8, 200, 22, { opacity: String(0.85 - 0.08 * (d - reach)), height: '22px', borderRadius: '8px' }) }, String(team.remaining));
    });
    tunnels.push(h('div', { class: 'tcol', key: 'vq' + q, style: { gap: '4px' } }, items,
      queue.length > 7 ? h('div', { class: 'dim', style: { fontSize: '10px', fontWeight: 700, textAlign: 'center' } }, `+${queue.length - 7}`) : null,
      queue.length === 0 ? h('div', { class: 'teamcard emptyq', style: { '--h': '54px', fontSize: '11px' } }, 'Empty') : null));
  }
  return h('div', { class: 'col', style: { gap: '6px' } },
    h('div', { class: 'row base', style: { gap: '8px' } },
      h('i', { style: { width: '12px', height: '12px', borderRadius: '50%', background: accent, display: 'block', alignSelf: 'center' } }),
      h('span', { class: 'title', style: { fontSize: '17px' } }, VersusController.names[p]),
      h('span', { class: 'grow' }),
      h('span', { class: 'num', style: { fontSize: '24px', fontWeight: 800, color: accent } }, String(swiftRounded(c.scores[p]))),
      h('span', { class: 'dim', style: { fontSize: '11px' } }, 'pts')),
    h('div', { class: 'dim', style: { fontSize: '10px', marginTop: '-6px' } }, `${c.delivered[p]} tiles home · −${Math.round(c.penalties(p))} penalties`),
    h('div', { class: 'row', style: { gap: '5px', flexWrap: 'wrap' } },
      h('span', { class: 'num', style: { width: '62px', fontSize: '10px', fontWeight: 700, color: c.occupied[p] >= cap ? 'var(--brass)' : 'var(--ok)' } }, `${Math.max(0, cap - c.occupied[p])} of ${cap} open`),
      pods,
      h('button', { class: 'pod add', type: 'button', style: { '--pod': pod + 'px', fontSize: '9px' }, 'aria-label': `Add a slot, costs ${Math.round(VersusRules.addSlotPenalty)} points`, onclick: () => c.addSlot(p) },
        icon('plus', 13), `−${Math.round(VersusRules.addSlotPenalty)}`)),
    h('div', { class: 'tunnels', style: { gap: '6px' } }, tunnels),
    h('div', { class: 'dim', style: { fontSize: '11px', minHeight: '28px' } }, c.messages[p] || ' '));
}

function resultCard(ctx) {
  const { app, match: c, ui, rerender } = ctx;
  const r = c.result;
  const title = r.winner === null ? 'A draw!' : `${VersusController.names[r.winner]} wins!`;
  const line = (a, b) => h('div', { class: 'row', style: { fontSize: '13px' } }, h('span', { class: 'dim grow' }, a), h('span', { class: 'num', style: { fontWeight: 700 } }, b));
  const column = p => {
    const l = r.lines[p];
    const accent = hex(PLAYER_COLORS[p]);
    return h('div', { class: 'col grow', key: 'c' + p, style: { gap: '4px', textAlign: 'left', minWidth: '160px' } },
      h('div', { class: 'row' }, h('i', { style: { width: '12px', height: '12px', borderRadius: '50%', background: accent, display: 'block' } }), h('span', { class: 'title', style: { fontSize: '18px' } }, VersusController.names[p])),
      h('div', { class: 'num', style: { fontSize: '26px', fontWeight: 800, color: accent } }, `${swiftRounded(l.score)} points`),
      line('Tiles home', `+${l.tiles}`),
      l.bonus > 0 ? line('First to finish', `+${Math.round(l.bonus)}`) : null,
      l.upkeep > 0 ? line('Slot upkeep', `−${swiftRounded(l.upkeep)}`) : null,
      l.addedSlots > 0 ? line(`Added slots ×${l.addedSlots}`, `−${Math.round(l.addedSlots * VersusRules.addSlotPenalty)}`) : null,
      l.returns > 0 ? line(`Returned teams ×${l.returns}`, `−${Math.round(l.returns * VersusRules.returnPenalty)}`) : null,
      l.skips > 0 ? line(`Queue jumps ×${l.skips}`, `−${Math.round(l.skips * VersusRules.skipPenalty)}`) : null);
  };
  let hs = null;
  if (r.winner !== null) {
    const w = r.winner;
    const top = c.topScores;
    let part = null;
    if (c.savedHighScorePlace !== null) {
      part = h('div', { class: 'row okc', style: { fontWeight: 700, justifyContent: 'center' } }, icon('trophy.fill', 16),
        c.savedHighScorePlace > 0 ? `Saved — #${c.savedHighScorePlace} on the two-player table for ${c.level.title}` : 'Saved');
    } else if (c.highScoreRank !== null) {
      if (ui.nameDraft === undefined || ui.nameDraft === null) ui.nameDraft = '';
      part = h('div', { class: 'col', style: { gap: '8px', alignItems: 'center', width: '100%' } },
        h('div', { class: 'row brass', style: { fontWeight: 700, fontSize: '15px' } }, icon('trophy.fill', 16), c.highScoreRank === 1 ? 'New two-player high score!' : `Two-player high score — #${c.highScoreRank}!`),
        h('div', { class: 'dim', style: { fontSize: '13px' } }, `${VersusController.names[w]}, enter your name for the table:`),
        h('form', { class: 'row', style: { width: '100%' }, onsubmit: e => { e.preventDefault(); c.saveWinnerScore(ui.nameDraft || ''); } },
          h('input', { id: 'vs-name', class: 'namebox', type: 'text', maxlength: '20', placeholder: "Winner's name", autocomplete: 'off', value: ui.nameDraft,
            style: { borderColor: hex(PLAYER_COLORS[w]) }, oninput: e => { ui.nameDraft = e.target.value.slice(0, 20); } }),
          h('button', { class: 'pill prominent', type: 'submit' }, 'Save')));
    } else if (top.length) {
      part = h('div', { class: 'dim', style: { fontSize: '13px', fontWeight: 600 } }, `Two-player high score to beat: ${formatNumber(top[0].score)} by ${top[0].name}`);
    }
    hs = h('div', { class: 'scorebox' }, part,
      top.length && (c.savedHighScorePlace !== null || c.highScoreRank === null) ? highScoreList(top, c.savedHighScorePlace !== null ? c.savedHighScorePlace - 1 : null, true) : null);
  }
  return h('div', { class: 'win', style: { maxWidth: '560px' }, role: 'dialog', 'aria-label': title },
    h('div', { class: 'title', style: { fontSize: '30px' } }, title),
    r.finisher !== null ? h('div', { class: 'dim', style: { fontSize: '14px' } }, `${VersusController.names[r.finisher]} cleared the mosaic first.`) : null,
    h('div', { class: 'row top wrap', style: { gap: '18px', width: '100%' } }, column(0), column(1)),
    hs,
    h('div', { class: 'row', style: { gap: '10px' } },
      pill('Rematch', () => { ui.nameDraft = null; app.startVersus(c.level, c.rules); }, { prominent: true }),
      pill('Home', () => app.endVersus())));
}

// MARK: - Setup sheet (Home → Two players)

export function versusSetupSheet(ctx, close) {
  const { app, ui, rerender } = ctx;
  const levels = LevelCatalog.builtIn.concat(app.photoLevels.map(r => r.level));
  if (!ui.vs) {
    const saved = app.settings.versusRules || defaultVersusRules();
    ui.vs = { rules: Object.assign({}, saved), levelID: levels.some(l => l.id === app.settings.versusLevelID) ? app.settings.versusLevelID : 'firstDig' };
  }
  const vs = ui.vs;
  const level = levels.find(l => l.id === vs.levelID) || LevelCatalog.main[0];
  const option = (title, key, blurb) => h('div', { class: 'col', key: 'opt-' + key, style: { gap: '6px' } },
    h('div', { class: 'caps brass' }, title),
    segmented(versusOptions(key), vs.rules[key], v => { vs.rules[key] = v; rerender(); }, title),
    h('div', { class: 'dim', style: { fontSize: '12px' } }, blurb));
  const startMatch = () => {
    const rules = Object.assign({}, vs.rules);
    app.updateSettings(s => { s.versusRules = rules; s.versusLevelID = vs.levelID; });
    ui.vs = null; ui.sheet = null;
    app.startVersus(level, rules);
  };
  return sheet('Two players', () => { ui.vs = null; close(); }, [
    h('div', { class: 'dim', style: { fontSize: '13px' } }, 'Two players on one screen. Every option can be combined with every other.'),
    option('BOARD', 'layout', versusOptionBlurb('layout', vs.rules.layout)),
    option('LAUNCHING', 'picking', versusOptionBlurb('picking', vs.rules.picking)),
    option('COLOUR RULE', 'colour', versusOptionBlurb('colour', vs.rules.colour)),
    option('SLOT SCORING', 'scoring', versusOptionBlurb('scoring', vs.rules.scoring)),
    h('div', { class: 'col', style: { gap: '6px' } }, h('div', { class: 'caps brass' }, 'Slots each'),
      segmented(DIFFICULTIES, vs.rules.difficulty, v => { vs.rules.difficulty = v; rerender(); }, 'Slots'),
      h('div', { class: 'dim', style: { fontSize: '12px' } }, `${levelChambers(level, vs.rules.difficulty)} slots each on this mosaic.`)),
    sectionTitle('MOSAIC'),
    h('div', { class: 'hscroll', style: { gap: '10px' } }, levels.map(lv => h('button', {
      key: lv.id, type: 'button', class: 'col', 'aria-pressed': lv.id === vs.levelID ? 'true' : 'false',
      style: { gap: '4px', padding: '6px', borderRadius: '12px', flex: 'none', alignItems: 'center', background: lv.id === vs.levelID ? 'var(--loam-raised)' : 'var(--panel)',
        border: lv.id === vs.levelID ? '2.5px solid var(--brass)' : '1px solid var(--panel-edge)' },
      onclick: () => { vs.levelID = lv.id; rerender(); },
    }, h('img', { class: 'pix', src: thumbURL(lv), alt: '', loading: 'lazy', style: { width: '84px', height: '96px', objectFit: 'contain' } }),
    h('span', { style: { fontSize: '11px', fontWeight: 700, width: '96px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', textAlign: 'center' } }, lv.title),
    h('span', { class: 'dim', style: { fontSize: '10px' } }, `${formatNumber(levelTileCount(lv))} tiles`)))),
    h('div', { class: 'dim', style: { fontSize: '12px' } }, 'Score: tiles your ants carry home, minus penalties (added slots −25, returned teams −10, queue jumps −3 per place, and slot upkeep if chosen). In a race, the first to clear their mosaic gets a bonus of 15% of its tiles and ends the match.'),
  ], { key: 'versus', large: true, footer: [pill('Start the match', startMatch, { prominent: true, wide: true })] });
}
