// Port of GameView.swift + ControlPanel.swift + JamCard / WinCard / CoachBanner (Overlays.swift):
// the game screen. Wide layouts put the controls beside the board; tall ones put them underneath.
import { h } from './vdom.js';
import { icon } from './icons.js';
import {
  pill, toggleSwitch, sheet, dialog, starRow, teamFace, chamberPod, miniChip, highScoreList, progressBar,
} from './components.js';
import { cssColor, pieceStyle } from './swatch.js';
import { howToSheet } from './howTo.js';
import {
  BoardCanvas, GroundPresets, pathStyles, pathStyleInfo, modifierInfo, ChallengeModifier, TimeText,
  paletteName, difficultyTitle, formatNumber, Game,
} from './compat.js';

const LOG_LO = Math.log(0.1), LOG_HI = Math.log(16);

/** The board's cell size and panel width for the available space (GameView.computeLayout). */
export function computeLayout(board, w, h) {
  const wide = w > h * 1.05;
  const cols = board.cols, rows = board.rows;
  if (wide) {
    const panelWidth = Math.min(470, Math.max(360, w * 0.38));
    const availW = w - panelWidth - 48;
    const availH = h - 32;
    const cell = Math.max(3, Math.min(availW / cols, availH / rows));
    return { wide, cell: Math.floor(cell * 2) / 2, panelWidth };
  }
  const availW = w - 24;
  if (w < 600) {
    // Phones: the board fills the width, but never pushes the tunnels and slots off the screen
    // (about 280 px of controls stay in view under it); never below 45% of the height. The iPad
    // app keeps the whole panel on screen, which would leave a phone only a small board.
    const essentials = 280;
    const fitH = Math.max((h - essentials) / rows, (h * 0.45) / rows);
    const cell = Math.max(2.5, Math.min(availW / cols, fitH));
    return { wide, cell: Math.floor(cell * 4) / 4, panelWidth: w, phone: true };
  }
  const panelHeight = 480;
  const availH = h - panelHeight - 30;
  const cell = Math.max(2.5, Math.min(availW / cols, availH / rows));
  return { wide, cell: Math.floor(cell * 2) / 2, panelWidth: w };
}

// One press at a time on a team card: a short press sends, a long press (0.35 s) scouts.
let press = null;
function teamPressHandlers(c, q) {
  const clear = () => { if (press && press.timer) clearTimeout(press.timer); press = null; };
  return {
    onpointerdown: e => {
      if (e.button !== undefined && e.button !== 0) return;
      clear();
      press = { q, x: e.clientX, y: e.clientY, scouted: false, timer: setTimeout(() => { if (press) { press.timer = null; press.scouted = true; } c.beginScout(q); }, 350) };
    },
    onpointermove: e => {
      if (press && press.timer && Math.hypot(e.clientX - press.x, e.clientY - press.y) > 12) { clearTimeout(press.timer); press = null; }
    },
    onpointerup: () => {
      if (press && press.q === q && press.timer) { clear(); c.dispatch(q); }
      else if (press && !press.scouted) clear();
      // after a long press the press record stays until contextmenu (or the next press) so the
      // browser's own long-press menu event can't scout a second time
    },
    onpointercancel: clear,
    onclick: e => { if (e.detail === 0) c.dispatch(q); },   // keyboard activation
    onkeydown: e => { if (e.key === 's' || e.key === 'S') { e.preventDefault(); c.beginScout(q); } },
    oncontextmenu: e => {
      e.preventDefault();
      const already = press && press.scouted;
      clear();
      if (!already) c.beginScout(q);
    },
  };
}

function mountBoard(el, c, cell) {
  if (c.boardCanvas) { try { c.boardCanvas.destroy(); } catch (e) { /* already gone */ } }
  const canvas = document.createElement('canvas');
  el.appendChild(canvas);
  c.boardCanvas = new BoardCanvas(canvas, c, cell);
  c.boardCanvas._cell = cell;
}

export function gameView(ctx) {
  const { app, controller: c, ui, size, rerender } = ctx;
  let layout = computeLayout(c.board, size.w, size.h);
  if (c.visuallyComplete && c._frozenLayout) layout = c._frozenLayout;   // typing a name must not resize the board
  c._frozenLayout = layout;
  const bw = Math.round(c.board.cols * layout.cell), bh = Math.round(c.board.rows * layout.cell);
  if (c.boardCanvas && c.boardCanvas._cell !== layout.cell) { c.boardCanvas._cell = layout.cell; c.boardCanvas.setCell(layout.cell); }
  const backdrop = c.groundColor;
  const bg = `rgb(${((backdrop >> 16) & 255) * 0.5 | 0},${((backdrop >> 8) & 255) * 0.5 | 0},${(backdrop & 255) * 0.5 | 0})`;

  const boardStack = h('div', { class: 'board-area', key: 'board-area' },
    h('div', { class: 'board-wrap', key: 'board-' + c.uid, style: { width: bw + 'px', height: bh + 'px' }, ref: el => mountBoard(el, c, layout.cell) }),
    c.coach ? h('div', { class: 'coach-host', key: 'coach' },
      h('div', { class: 'coach', role: 'status' },
        h('span', { class: 'brass', style: { paddingTop: '2px' } }, icon('ant.fill', 24)),
        h('div', { class: 'col grow', style: { gap: '4px' } },
          h('div', { class: 'title', style: { fontSize: '18px' } }, c.coach.title),
          h('div', { class: 'dim', style: { fontSize: '14px', lineHeight: '1.4' } }, c.coach.message)),
        pill('Got it', () => c.dismissCoach(), { prominent: true }))) : null);

  const panel = controlPanel(ctx, !layout.wide);
  const body = layout.wide
    ? h('div', { class: 'game-wide', key: 'wide' }, boardStack, h('div', { class: 'panel-scroll', style: { width: layout.panelWidth + 'px' } }, panel))
    : h('div', { class: 'game-tall', key: 'tall' }, boardStack, panel);

  return h('div', { class: 'game', key: 'game-' + c.uid, style: { background: bg } },
    body,
    overlays(ctx),
    h('button', { class: 'exit-btn', type: 'button', 'aria-label': 'Exit to Home', title: 'Exit to Home (your game is saved)', onclick: () => app.goHome() }, icon('xmark', 18)),
    ui.menu ? gameMenu(ctx) : null,
    modal(ctx));
}

// MARK: - Control panel

function controlPanel(ctx, compact) {
  const { controller: c, size } = ctx;
  const event = c.eventText ? h('div', { class: 'event', key: 'ev', role: 'status' }, h('span', null, c.eventText)) : null;
  if (compact && size.w < 600) {
    // Phones: the teams you tap come straight under the board, then the slots; the rest follows.
    return h('div', { class: ['panel', 'cpanel', 'compact', 'phone'], key: 'cpanel' },
      phoneHeader(ctx),
      tunnelsRow(ctx, true),
      slotsRow(ctx, true),
      event,
      messageArea(ctx),
      toolbar(ctx),
      speedRow(ctx));
  }
  return h('div', { class: ['panel', 'cpanel', compact && 'compact'], key: 'cpanel' },
    header(ctx, compact),
    event,
    slotsRow(ctx, compact),
    tunnelsRow(ctx, compact),
    messageArea(ctx),
    toolbar(ctx),
    speedRow(ctx),
    compact ? null : nestMiniature(c));
}

/** One slim row: title, moves, tiles home, the menu; a thin progress bar under it. */
function phoneHeader(ctx) {
  const { controller: c, ui, rerender } = ctx;
  let sub = `${difficultyTitle(c.difficulty)} · ${c.moveCount} moves`;
  if (c.assistCount > 0) sub += ` · ${c.assistCount} assists`;
  const mods = ChallengeModifier.sorted(c.modifiers);
  return h('div', { class: 'col', style: { gap: '4px' } },
    h('div', { class: 'row', style: { gap: '8px' } },
      h('div', { class: 'col grow', style: { gap: 0 } },
        h('div', { class: 'title lvl-title' }, c.level.title),
        h('div', { class: 'dim num', style: { fontSize: '11px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' } },
          `${sub} · ${formatNumber(c.deliveredCount)}/${formatNumber(c.board.tileCount)} home`)),
      mods.length ? h('span', { class: 'mods', title: 'Harder options · score ×' + c.scoreFactor.toFixed(2) },
        mods.map(m => h('span', { key: m, class: 'm', style: { width: '18px', height: '18px' } }, icon(modifierInfo(m).systemImage, 11)))) : null,
      h('button', {
        class: 'iconbtn', type: 'button', 'aria-label': 'Menu', 'aria-haspopup': 'menu',
        style: { color: 'var(--sand)', '--icon-ink': 'var(--panel-edge)', width: '40px', height: '40px' },
        onclick: e => { const r = e.currentTarget.getBoundingClientRect(); ui.menu = { top: r.bottom + 6, right: Math.max(8, window.innerWidth - r.right) }; rerender(); },
      }, icon('ellipsis.circle.fill', 28))),
    progressBar(c.progress));
}

function header(ctx, compact) {
  const { controller: c, ui, rerender } = ctx;
  let sub = `${difficultyTitle(c.difficulty)} · ${c.moveCount} moves`;
  if (c.assistCount > 0) sub += ` · ${c.assistCount} assists`;
  const mods = ChallengeModifier.sorted(c.modifiers);
  return h('div', { class: 'col', style: { gap: '6px' } },
    h('div', { class: 'row', style: { alignItems: 'flex-start' } },
      h('div', { class: 'col grow', style: { gap: 0 } },
        h('div', { class: 'title lvl-title' }, c.level.title),
        h('div', { class: 'dim', style: { fontSize: '13px' } }, sub)),
      h('button', {
        class: 'iconbtn', type: 'button', 'aria-label': 'Menu', 'aria-haspopup': 'menu', 'aria-expanded': ui.menu ? 'true' : 'false',
        style: { color: 'var(--sand)', '--icon-ink': 'var(--panel-edge)', width: '48px', height: '48px' },
        onclick: e => {
          const r = e.currentTarget.getBoundingClientRect();
          ui.menu = { top: r.bottom + 6, right: Math.max(8, window.innerWidth - r.right) };
          rerender();
        },
      }, icon('ellipsis.circle.fill', 32))),
    mods.length ? h('div', { class: 'mods', 'aria-label': 'Harder options: ' + mods.map(m => modifierInfo(m).title).join(', ') },
      mods.map(m => h('span', { key: m, class: 'm', title: modifierInfo(m).title }, icon(modifierInfo(m).systemImage, 13))),
      h('span', { class: 'dim', style: { fontSize: '11px', fontWeight: 700 } }, 'Harder options · score ×' + c.scoreFactor.toFixed(2))) : null,
    progressBar(c.progress),
    h('div', { class: 'dim num', style: { fontSize: '12px' } },
      `${formatNumber(c.deliveredCount)} of ${formatNumber(c.board.tileCount)} tiles home · ${formatNumber(c.board.tileCount - c.claimedCount)} unclaimed`));
}

function slotsRow(ctx, compact) {
  const { controller: c, ui, rerender, size } = ctx;
  const phone = compact && size.w < 600;
  const pod = phone ? 44 : compact ? 54 : 62;
  const open = Math.max(0, c.capacity - c.occupiedSlots);
  const items = c.slots.map(item => slotView(ctx, item, pod));
  if (c.jammedTeam) {
    items.push(h('div', { class: 'slot', key: 'jam' }, chamberPod(c.palette, c.jammedTeam, pod, { jammed: true }), h('div', { class: 'cap dangerc' }, 'Blocked')));
  }
  if (c.assistsAllowed) {
    items.push(h('div', { class: 'slot', key: 'add' },
      h('button', { class: 'pod add', type: 'button', style: { '--pod': pod + 'px' }, 'aria-label': 'Add a slot', onclick: () => { ui.dialog = { kind: 'addSlot' }; rerender(); } },
        icon('plus', 18), 'Slot'),
      h('div', { class: 'cap dim', style: { fontWeight: 500, fontSize: '10px', opacity: 0.8 } }, 'add · assist')));
  }
  let fullText = null;
  if (!c.hasOpenSlot && !c.isBlocked) {
    const s = c.nextFreeSeconds;
    fullText = s !== null && s > 0 && s < 1e6
      ? `All slots busy — next one opens in about ${Math.ceil(s)} s. Teams can't be sent until then.`
      : 'All slots busy — a slot opens when a working team has picked up all its tiles.';
  }
  return h('div', { class: 'col', style: { gap: '6px' } },
    h('div', { class: 'row', style: { gap: '6px' } },
      h('span', { class: 'caps', style: { color: c.isBlocked ? 'var(--danger)' : 'var(--sand-dim)' } }, 'Slots'),
      h('span', { class: 'num', style: { fontSize: '12px', fontWeight: 700, color: c.hasOpenSlot ? 'var(--ok)' : 'var(--brass)' } }, `${open} of ${c.capacity} open`),
      h('span', { class: 'grow' }),
      h('button', { class: 'iconbtn', type: 'button', style: { height: phone ? '22px' : '32px' }, 'aria-label': 'How slots work', onclick: () => { ui.dialog = { kind: 'slotsHelp' }; rerender(); } }, icon('questionmark.circle', phone ? 18 : 20))),
    h('div', { class: 'slots' }, items),
    fullText ? h('div', { class: 'brass', style: { fontSize: '12px' } }, fullText) : null);
}

function slotView(ctx, item, pod) {
  const { controller: c, ui, rerender } = ctx;
  const pal = c.palette;
  switch (item.kind) {
    case 'open':
      return h('div', { class: 'slot', key: 's' + item.id, 'aria-label': 'Open slot' }, chamberPod(pal, null, pod, { label: 'Open' }), h('div', { class: 'cap' }, ' '));
    case 'working':
      return h('div', { class: 'slot', key: 's' + item.id, 'aria-label': `Slot working: ${paletteName(pal, item.family)} team, ${item.toCollect} tiles still to pick up` },
        chamberPod(pal, { family: item.family, remaining: item.toCollect }, pod), h('div', { class: 'cap' }, 'Working'));
    case 'waiting':
      return h('div', { class: 'slot', key: 's' + item.id },
        h('button', {
          type: 'button', style: { borderRadius: '14px' }, onclick: () => c.recall(item.chamber),
          'aria-label': `Slot waiting: ${paletteName(pal, item.family)} team needs ${item.toCollect} more tiles.` + (c.assistsAllowed ? ' Tap to return it to its tunnel.' : ''),
        }, chamberPod(pal, { family: item.family, remaining: item.toCollect }, pod,
          { badge: c.assistsAllowed ? h('span', { class: 'rb' }, icon('arrow.uturn.down', 10)) : null })),
        h('div', { class: 'cap brass', style: { width: pod + 'px', textAlign: 'center' } }, 'Waiting'));
    case 'held':
      return h('div', { class: 'slot', key: 's' + item.id },
        h('button', { type: 'button', style: { borderRadius: '14px' }, onclick: () => { ui.dialog = { kind: 'chamber', index: item.chamber }; rerender(); },
          'aria-label': `Slot held: ${paletteName(pal, item.family)} team of ${item.need}. Tap to send or return it.` },
        chamberPod(pal, { family: item.family, remaining: item.need }, pod, { opacity: 0.8, hint: c.hintChamber === item.chamber })),
        h('div', { class: 'cap dim' }, 'Held'));
    default:
      return null;
  }
}

function tunnelsRow(ctx, compact) {
  const { controller: c, size } = ctx;
  const phone = size.w < 600;
  const cols = [];
  for (let q = 0; q < c.tunnelCount; q++) cols.push(tunnelColumn(ctx, q, compact));
  return h('div', { class: 'col', style: { gap: '6px' } },
    phone ? null : h('div', { class: 'row base wrap', style: { gap: '4px 10px' } },
      h('span', { class: 'caps dim' }, 'Tunnels'),
      h('span', { class: 'dim', style: { fontSize: '11px', opacity: 0.85, flex: '1 1 200px' } },
        "Tap a team to send it into an open slot — each tap sends the next team in line. A team that can't reach all its tiles waits in its slot by itself.")),
    h('div', { class: 'tunnels' }, cols));
}

function tunnelColumn(ctx, q, compact) {
  const { controller: c, ui, rerender, size } = ctx;
  const phone = compact && size.w < 600;
  const cardHeight = phone ? 64 : compact ? 84 : 104;
  const pal = c.palette;
  const next = c.upcoming(q, phone ? 1 : 3);
  const behind = Math.max(0, c.remaining(q) - 1 - next.length);
  const fr = c.front(q);
  const openQueue = () => { if (!c.queueHidden) { ui.sheet = { kind: 'queue', tunnel: q }; rerender(); } };
  const parts = [
    h('button', { class: 'thead', type: 'button', key: 'th', onclick: openQueue, 'aria-label': `Tunnel ${q + 1}, ${c.remaining(q)} teams left. Show the whole queue.` },
      phone ? (c.tunnelCount >= 3 ? `TUNNEL ${q + 1} · ${c.remaining(q)}`
        : h('span', null, `TUNNEL ${q + 1} · ${c.remaining(q)} LEFT`, behind > 0 && !c.queueHidden ? h('span', { class: 'brass' }, ` · +${behind}`) : null))
        : `TUNNEL ${q + 1} · ${c.remaining(q)} left`),
  ];
  if (fr) {
    const refusal = c.colourRefusal(q);
    const highlighted = c.hintTunnel === q || (c.scout && c.scout.tunnel === q);
    parts.push(teamFace(pal, fr.family, fr.need, cardHeight, [highlighted && 'hl', !c.canSend(q) && 'dim'],
      Object.assign({
        key: 'front-' + fr.uid,
        'aria-label': `Tunnel ${q + 1}: ${paletteName(pal, fr.family)} team, ${fr.need} tiles${fr.isReturned ? ', returned' : ''}. ${c.scoutAllowed ? 'Press and hold, or press S, to scout.' : ''}`,
        children: refusal ? h('span', { class: 'sametag' }, 'Same colour') : null,
      }, teamPressHandlers(c, q))));
    if (c.difficulty === 'gentle' && q < c.fitBadges.length && c.fitBadges[q] !== null && c.fitBadges[q] !== undefined) {
      const fits = c.fitBadges[q];
      parts.push(h('div', { class: 'fit', key: 'fit', style: { color: fits ? 'var(--ok)' : 'var(--brass)' } }, fits ? 'Can finish now' : 'Would wait'));
    } else if (fr.isReturned) {
      parts.push(h('div', { class: 'fit dim', key: 'fit' }, 'Returned team'));
    }
    if (c.queueHidden) {
      const n = Math.min(phone ? 1 : 3, Math.max(0, c.remaining(q) - 1));
      for (let k = 0; k < n; k++) parts.push(h('div', { class: 'minichip hidden', key: 'hq' + k, style: { opacity: String(1 - 0.18 * k) } }, icon('questionmark', 12)));
    } else {
      next.forEach((spec, k) => parts.push(miniChip(pal, spec, k)));
      if (behind > 0 && !phone) parts.push(h('button', { class: 'brass', key: 'more', type: 'button', style: { minHeight: phone ? '22px' : '28px', fontSize: phone ? '11px' : '12px', fontWeight: 700 }, onclick: openQueue }, `+${behind} more`));
    }
  } else {
    parts.push(h('div', { class: 'teamcard emptyq', key: 'empty', style: { '--h': cardHeight + 'px' } }, 'Empty'));
  }
  return h('div', { class: 'tcol', key: 'q' + q }, parts);
}

function messageArea(ctx) {
  const { controller: c } = ctx;
  if (c.scout) {
    const s = c.scout;
    const text = s.fits
      ? `Every one of its ${s.quota} tiles is reachable now — its slot frees as soon as they're picked up.`
      : `Reaches ${s.ownTiles.length} now; it would keep its slot and wait for the other ${s.quota - s.ownTiles.length} until they're uncovered.`;
    return h('div', { class: 'msgcard', key: 'msg-scout', role: 'status' },
      h('div', { class: 'row top' }, h('span', { class: 'brass' }, icon('eye.fill', 20)),
        h('div', { class: 'col grow', style: { gap: '4px' } }, h('div', { style: { fontWeight: 700 } }, `Scouting a team of ${s.quota}`), h('div', { class: 'dim', style: { fontSize: '13px' } }, text))),
      h('div', { class: 'acts' }, pill('Send', () => c.dispatch(s.tunnel), { prominent: true }), pill('Close', () => c.endScout())));
  }
  if (c.hint) {
    const hn = c.hint;
    let text;
    if (hn.kind === 'move') {
      const what = hn.code >= Game.releaseBase ? 'Send the held team glowing in the slots row.' : `Send the team in tunnel ${hn.code + 1} (glowing).`;
      text = hn.onPlan ? what : 'Tricky spot. ' + what + ' It makes the most progress, but no sure win was found.';
    } else if (hn.kind === 'undo') {
      text = `No winning line from here. Undo ${hn.count} move${hn.count === 1 ? '' : 's'} to get back on track — or add a slot / return a waiting team.`;
    } else {
      text = 'Every team has been sent. Sit back and watch.';
    }
    return h('div', { class: 'msgcard', key: 'msg-hint', role: 'status' },
      h('div', { class: 'row top' }, h('span', { class: 'brass' }, icon('lightbulb.fill', 20)), h('div', { class: 'grow', style: { fontSize: '14px' } }, text)),
      h('div', { class: 'acts' },
        hn.kind === 'undo' ? pill(`Undo ${hn.count}`, () => c.undoTimes(hn.count), { prominent: true }) : null,
        hn.kind === 'move' ? pill('Do it', () => c.playHint(), { prominent: true }) : null,
        pill('OK', () => c.clearHint())));
  }
  if (c.isLogicallyWon && !c.visuallyComplete) {
    return h('div', { class: 'msgcard okb', key: 'msg-done', role: 'status' },
      h('div', { class: 'row top' }, h('span', { class: 'okc' }, icon('sparkles', 20)),
        h('div', { class: 'grow', style: { fontSize: '14px' } }, "Every tile is claimed — the colony is carrying the last ones home. Slide the speed up if you'd like them to hurry.")));
  }
  return null;
}

function toolbar(ctx) {
  const { controller: c } = ctx;
  const left = c.undosLeft;
  return h('div', { class: 'row', style: { gap: '10px' } },
    h('button', { class: 'tool', type: 'button', disabled: !c.canUndo, onclick: () => c.undo() }, icon('arrow.uturn.backward', 20), left === null ? 'Undo' : `Undo (${left} left)`),
    c.hintsAllowed ? h('button', { class: 'tool', type: 'button', disabled: c.hintBusy || c.isLogicallyWon, onclick: () => c.requestHint() },
      c.hintBusy ? h('span', { class: 'spinner' }) : icon('lightbulb', 20), 'Hint') : null);
}

function speedLabel(s) { return s < 0.995 ? s.toFixed(2) + '×' : s.toFixed(1) + '×'; }

function speedRow(ctx) {
  const { controller: c } = ctx;
  const v = (Math.log(c.speed) - LOG_LO) / (LOG_HI - LOG_LO);
  return h('div', { class: 'col', style: { gap: '4px' } },
    h('div', { class: 'speed-head' },
      h('span', { class: 'caps dim' }, 'Ant speed'), h('span', { class: 'grow' }),
      h('span', { class: 'num', style: { fontSize: '13px', fontWeight: 700 } }, speedLabel(c.speed)),
      h('button', { class: 'brass', type: 'button', style: { minWidth: '44px', minHeight: '32px', fontSize: '12px', fontWeight: 700 }, onclick: () => { c.setSpeed(1); c.commitSpeed(); } }, '1×')),
    h('div', { class: 'row', style: { minHeight: '44px' } },
      h('span', { class: 'dim' }, icon('tortoise.fill', 20)),
      h('input', {
        id: 'ant-speed', type: 'range', min: '0', max: '1', step: '0.001', value: v.toFixed(3), 'aria-label': 'Ant speed', 'aria-valuetext': speedLabel(c.speed),
        oninput: e => c.setSpeed(Math.exp(LOG_LO + parseFloat(e.target.value) * (LOG_HI - LOG_LO))),
        onchange: () => c.commitSpeed(),
      }),
      h('span', { class: 'dim' }, icon('hare.fill', 20))));
}

function nestMiniature(c) {
  return h('div', { class: 'mini' },
    c.miniImage ? h('img', { class: 'pix', src: c.miniImage, alt: 'The nest gallery: tiles re-laid so far' }) : null,
    h('div', { class: 'col', style: { gap: '4px' } },
      h('div', { class: 'caps brass' }, 'Nest gallery'),
      h('div', { class: 'dim', style: { fontSize: '13px' } }, 'Every tile carried home is re-laid down here, in the same place.')));
}

// MARK: - Menu (…)

function gameMenu(ctx) {
  const { controller: c, ui, rerender, app } = ctx;
  const close = () => { ui.menu = null; rerender(); };
  const pos = ui.menu;
  const item = (ic, label, fn, extra) => h('button', { class: 'mi', type: 'button', role: 'menuitem', onclick: () => { ui.menu = null; fn(); rerender(); } }, h('span', { class: 'brass' }, icon(ic, 18)), h('span', { class: 'grow' }, label), extra || null);
  return h('div', { class: 'scrim', style: { background: 'transparent', padding: 0, display: 'block' }, key: 'menu-scrim', onclick: e => { if (e.target === e.currentTarget) close(); } },
    h('div', { class: 'menu-pop', role: 'menu', style: { top: pos.top + 'px', right: pos.right + 'px', position: 'fixed' } },
      item('arrow.counterclockwise', 'Restart mosaic', () => { ui.dialog = { kind: 'restart' }; }),
      item('questionmark.circle', 'How to play', () => { ui.sheet = { kind: 'howto' }; }),
      h('label', { class: 'mi', role: 'menuitemcheckbox' }, h('span', { class: 'brass' }, icon('ant', 18)), h('span', { class: 'grow' }, 'Detailed legs'),
        toggleSwitch('menu-legs', c.detailedAnts, v => c.setDetailedAnts(v))),
      h('label', { class: 'mi', role: 'menuitemcheckbox' }, h('span', { class: 'brass' }, icon('speaker.wave.2', 18)), h('span', { class: 'grow' }, 'Sound effects'),
        toggleSwitch('menu-sound', c.soundOn, v => c.setSoundOn(v))),
      h('hr', null),
      h('div', { class: 'caps dim', style: { padding: '6px 10px' } }, 'Ant paths: ' + pathStyleInfo(c.pathStyle).title),
      pathStyles().map(s => h('button', { key: s.id, class: 'mi sub', type: 'button', role: 'menuitemradio', 'aria-checked': c.pathStyle === s.id ? 'true' : 'false',
        onclick: () => { c.setPathStyle(s.id); ui.menu = null; rerender(); } },
        h('span', { class: 'grow' }, s.title), c.pathStyle === s.id ? h('span', { class: 'brass' }, icon('checkmark', 16)) : null)),
      h('hr', null),
      item('paintpalette', 'Ground colour…', () => { ui.sheet = { kind: 'ground' }; }),
      item('house', 'Back to the nest', () => app.goHome())));
}

// MARK: - Overlays (blocked / finished)

function overlays(ctx) {
  const { controller: c } = ctx;
  if (c.isBlocked) return h('div', { class: 'overlay-scrim', key: 'jam' }, jamCard(ctx));
  if (c.visuallyComplete) return h('div', { class: 'overlay-scrim', key: 'win', style: { background: 'rgba(0,0,0,.5)', alignItems: 'flex-start' } }, winCard(ctx));
  return null;
}

function jamCard(ctx) {
  const { controller: c, app } = ctx;
  const hasWayOut = c.canUndo || c.assistsAllowed || c.jammedTeam !== null;
  let s = c.jammedTeam
    ? `A team still needs ${c.jammedTeam.remaining} tiles it can't reach, and every slot is taken.`
    : `Every one of the ${c.capacity} slots holds a team waiting for tiles it can't reach yet, so no team can be sent.`;
  if (!hasWayOut) s += ' With this game’s harder options (no undos left, no assists) the only way on is to restart.';
  return h('div', { class: 'jam', role: 'alertdialog', 'aria-label': 'The colony is blocked' },
    h('span', { class: 'dangerc' }, icon('exclamationmark.triangle.fill', 36)),
    h('div', { class: 'title', style: { fontSize: '26px' } }, 'The colony is blocked'),
    h('div', { class: 'dim', style: { fontSize: '15px', lineHeight: '1.45' } }, s),
    h('div', { class: 'col', style: { gap: '10px', width: '100%' } },
      c.canUndo ? pill(c.undosLeft === null ? 'Undo the last move' : `Undo the last move (${c.undosLeft} left)`, () => c.undo(), { prominent: true, wide: true, icon: 'arrow.uturn.backward' }) : null,
      c.assistsAllowed ? pill('Add a slot', () => c.addChamber(), { wide: true, icon: 'plus.square.dashed' }) : null,
      c.jammedTeam ? pill('Return the blocked team to its tunnel', () => c.recallJammed(), { wide: true, icon: 'arrow.down.to.line' }) : null),
    c.chambers.length > 0 && c.assistsAllowed ? h('div', { class: 'col', style: { gap: '8px', width: '100%', textAlign: 'left' } },
      h('div', { class: 'dim', style: { fontSize: '13px' } }, 'Or open a slot — tap a waiting team to return it to its tunnel:'),
      h('div', { class: 'row wrap', style: { gap: '8px' } }, c.chambers.map((t, i) => h('button', { key: 'r' + i, type: 'button', onclick: () => c.recall(i),
        'aria-label': `Return the ${paletteName(c.palette, t.family)} team waiting for ${t.remaining} tiles to its tunnel` }, chamberPod(c.palette, t, 54))))) : null,
    h('div', { class: 'row wrap', style: { gap: '10px', justifyContent: 'center' } },
      c.hintsAllowed ? pill('Hint', () => c.requestHint()) : null,
      pill('Restart', () => c.restart(), { prominent: !hasWayOut }),
      pill('Home', () => app.goHome())));
}

function starText(stars) {
  return stars === 1 ? 'Explored — your first star' : stars === 2 ? 'Two stars — explored on Classic' : 'Three stars — explored on Expert';
}

function fmtFactor(v) {
  const r = Math.round(v * 100) / 100;
  return r === Math.round(r) ? r.toFixed(0) : r.toFixed(2);
}

function winCard(ctx) {
  const { controller: c, app, ui, rerender } = ctx;
  if (ui.nameDraft === undefined || ui.nameDraft === null) ui.nameDraft = c.playerName;
  const news = c.completionNews;
  let subtitle = `${formatNumber(c.board.tileCount)} tiles carried home · ${difficultyTitle(c.difficulty)}`;
  const n = c.modifiers.size;
  if (n > 0) subtitle += ` · ${n} harder option${n === 1 ? '' : 's'}`;
  const newsLines = [];
  if (news) {
    if (news.mastered) newsLines.push(['flame.fill', 'Mastered — Expert with a harder option!']);
    else if (news.newStar) newsLines.push(['star.fill', starText(news.stars)]);
    if (news.newBest) newsLines.push(['stopwatch.fill', `New best time on ${difficultyTitle(c.difficulty)}!`]);
    if (news.unlocked.length > 3) newsLines.push(['sparkles', `Found ${news.unlocked.length} new mosaics — see Home`]);
    else for (const t of news.unlocked) newsLines.push(['sparkles', `Found: ${t}`]);
  }
  const stat = (k, v) => h('div', { class: 'stat', key: k }, h('div', { class: 'v num' }, v), h('div', { class: 'k' }, k.toUpperCase()));
  const harder = app.harderStep(c.difficulty, c.modifiers);
  const next = app.nextLevel(c.level.id);
  const saveScore = () => { c.saveHighScore(ui.nameDraft || ''); };
  let scoreBlock = null;
  const b = c.scoreBreakdown;
  if (b) {
    let bt = `${formatNumber(b.tiles)} tiles × ${fmtFactor(b.difficultyFactor)} ${difficultyTitle(c.difficulty)}`;
    if (b.modifierFactor > 1.0001) bt += ` × ${fmtFactor(b.modifierFactor)} harder options`;
    const minus = [];
    if (b.undoPenalty > 0) minus.push(`${b.undoPenalty} undos`);
    if (b.hintPenalty > 0) minus.push(`${b.hintPenalty} hints`);
    if (b.assistPenalty > 0) minus.push(`${b.assistPenalty} assists`);
    if (minus.length) bt += ' − ' + minus.join(' − ');
    const top = c.topScores;
    let rankPart = null;
    if (c.savedHighScorePlace !== null) {
      rankPart = h('div', { class: 'row okc', style: { fontWeight: 700, fontSize: '14px', justifyContent: 'center' } }, icon('trophy.fill', 16),
        c.savedHighScorePlace > 0 ? `Saved — #${c.savedHighScorePlace} on ${c.level.title}` : 'Saved');
    } else if (c.highScoreRank !== null) {
      const rank = c.highScoreRank;
      rankPart = h('div', { class: 'col', style: { gap: '8px', width: '100%', alignItems: 'center' } },
        h('div', { class: 'row brass', style: { fontWeight: 700, fontSize: '15px', justifyContent: 'center' } }, icon('trophy.fill', 16),
          rank === 1 ? `New high score on ${c.level.title}!` : `High score — #${rank} on ${c.level.title}!`),
        h('form', { class: 'row', style: { width: '100%' }, onsubmit: e => { e.preventDefault(); saveScore(); } },
          h('input', { id: 'hs-name', class: 'namebox', type: 'text', maxlength: '20', autocomplete: 'off', autocapitalize: 'words', spellcheck: 'false',
            placeholder: 'Your name', value: ui.nameDraft || '', 'aria-label': 'Name for the high-score table',
            oninput: e => { ui.nameDraft = e.target.value.slice(0, 20); } }),
          h('button', { class: 'pill prominent', type: 'submit' }, 'Save')),
        h('div', { class: 'dim', style: { fontSize: '12px' } }, 'Type your name, then Save.'));
    } else if (top.length > 0) {
      rankPart = h('div', { class: 'dim', style: { fontSize: '13px', fontWeight: 600 } }, `High score to beat: ${formatNumber(top[0].score)} by ${top[0].name}`);
    }
    scoreBlock = h('div', { class: 'scorebox' },
      h('div', { class: 'row base', style: { justifyContent: 'center' } }, h('span', { class: 'caps brass' }, 'Score'), h('span', { class: 'num', style: { fontSize: '30px', fontWeight: 800 } }, formatNumber(b.score))),
      h('div', { class: 'dim', style: { fontSize: '12px' } }, bt),
      rankPart,
      top.length > 0 && (c.savedHighScorePlace !== null || c.highScoreRank === null)
        ? highScoreList(top, c.savedHighScorePlace !== null ? c.savedHighScorePlace - 1 : null, true) : null);
  }
  return h('div', { class: 'win', role: 'dialog', 'aria-label': 'Mosaic complete' },
    c.miniImage ? h('img', { class: 'pix mini-img', src: c.miniImage, alt: c.level.title, style: { maxHeight: c.highScoreRank !== null ? '130px' : '180px' } }) : null,
    h('div', { class: 'title', style: { fontSize: '28px' } }, 'Re-laid in the nest'),
    h('div', { class: 'dim', style: { fontSize: '15px' } }, subtitle),
    news ? starRow(news.stars, news.mastered, 20) : null,
    newsLines.length ? h('div', { class: 'col brass', style: { gap: '6px', fontWeight: 700, fontSize: '15px', alignItems: 'center' } },
      newsLines.map(([ic, t], i) => h('div', { key: 'n' + i, class: 'row' }, icon(ic, 16), t))) : null,
    h('div', { class: 'stats' }, stat('Time', TimeText.mmss(c.elapsed)), stat('Moves', String(c.moveCount)), stat('Undos', String(c.undos)), stat('Hints', String(c.hintsUsed)), stat('Assists', String(c.assistCount))),
    scoreBlock,
    harder ? pill(harder.label, () => app.play(c.level, true, harder.difficulty, harder.modifiers), { icon: 'arrow.up.circle.fill' }) : null,
    h('div', { class: 'row wrap', style: { gap: '10px', justifyContent: 'center' } },
      pill('Nest gallery', () => app.goHome(), { prominent: !next }),
      pill('Play again', () => { ui.nameDraft = null; c.restart(); }),
      next ? pill('Next mosaic', () => app.play(next, false), { prominent: true }) : null));
}

// MARK: - Dialogs and sheets

function modal(ctx) {
  const { controller: c, ui, rerender } = ctx;
  const closeDialog = () => { ui.dialog = null; rerender(); };
  const closeSheet = () => { ui.sheet = null; rerender(); };
  return [sheetNode(ctx), dialogNode(ctx)];
}

function dialogNode(ctx) {
  const { controller: c, ui, rerender } = ctx;
  const closeDialog = () => { ui.dialog = null; rerender(); };
  const d = ui.dialog;
  if (d) {
    if (d.kind === 'addSlot') return dialog('Add a slot?', 'One more team can work or wait at a time. It counts as an assist and can be undone.',
      [{ label: 'Add slot', prominent: true, onclick: () => { ui.dialog = null; c.addChamber(); rerender(); } }, { label: 'Cancel', onclick: closeDialog }], closeDialog);
    if (d.kind === 'restart') return dialog('Restart this mosaic?', 'Every tile goes back and all tunnels refill.',
      [{ label: 'Restart', prominent: true, destructive: true, onclick: () => { ui.dialog = null; c.restart(); rerender(); } }, { label: 'Cancel', onclick: closeDialog }], closeDialog);
    if (d.kind === 'slotsHelp') return dialog('Slots', 'Every team you send takes a slot. A working team frees its slot once its ants have picked up all its tiles (the number counts down). You can only send a team while a slot is open. Any mix of colours is fine — every slot can hold the same colour.\n\nTo make a team wait, just send it: if it can’t reach all its tiles yet, it keeps its slot and waits, then resumes by itself when its colour is uncovered. One tap on a waiting team returns it to the front of its tunnel and opens its slot (Undo puts it back).',
      [{ label: 'OK', prominent: true, onclick: closeDialog }], closeDialog);
    if (d.kind === 'chamber') {
      const t = c.chambers[d.index];
      if (!t) { ui.dialog = null; return null; }
      const btns = [];
      if (t.held) btns.push({ label: 'Send it now', prominent: true, onclick: () => { ui.dialog = null; c.release(d.index); rerender(); } });
      if (c.assistsAllowed) btns.push({ label: `Return it to tunnel ${Math.floor(t.uid / 1000) + 1}`, onclick: () => { ui.dialog = null; c.recall(d.index); rerender(); } });
      btns.push({ label: 'Leave it', onclick: closeDialog });
      const msg = t.held
        ? 'This team was parked with Hold in an earlier version and won’t work until you send it. Returning it puts it back at the front of its tunnel and opens its slot.'
        : 'This team resumes by itself whenever its colour is uncovered. Returning it opens its slot; it keeps the number of tiles it still needs.';
      return dialog(t.held ? `Held team · ${t.remaining} tiles` : `Waiting team · needs ${t.remaining} more`, msg, btns, closeDialog);
    }
  }
  return null;
}

function sheetNode(ctx) {
  const { controller: c, ui, rerender } = ctx;
  const closeSheet = () => { ui.sheet = null; rerender(); };
  const s = ui.sheet;
  if (s) {
    if (s.kind === 'howto') return howToSheet(closeSheet);
    if (s.kind === 'ground') return groundSheet(c, closeSheet);
    if (s.kind === 'queue') {
      const queue = c.fullQueue(s.tunnel);
      return sheet(`Tunnel ${s.tunnel + 1} · ${queue.length} teams`, closeSheet, [
        h('div', { class: 'dim', style: { fontSize: '14px' } }, 'Teams leave from the top. Tap a team on the game screen to send the front one; the next one then moves up.'),
        h('div', { class: 'queue-grid' }, queue.map((spec, k) => h('div', { key: 'k' + k, class: 'col', style: { gap: '4px', alignItems: 'stretch' } },
          h('div', { class: ['teamcard', 'num', 'ink', k === 0 && 'hl'], style: pieceStyle(c.palette, spec.family, 10, 120, 64, { '--h': '64px' }) }, h('span', null, String(spec.quota))),
          h('div', { style: { textAlign: 'center', fontSize: '11px', fontWeight: 700, color: k === 0 ? 'var(--brass)' : 'var(--sand-dim)' } }, k === 0 ? 'Front' : `#${k + 1}`)))),
      ], { key: 'queue' });
    }
  }
  return null;
}

function groundSheet(c, onDone) {
  return sheet('Ground colour', onDone, [
    h('div', { class: 'dim', style: { fontSize: '14px' } }, 'The ground shows around the mosaic and wherever tiles have been carried away.'),
    h('div', { class: 'swatches', style: { gridTemplateColumns: 'repeat(auto-fill, minmax(76px, 1fr))' } }, GroundPresets.all.map(([name, col]) =>
      h('button', { key: name, type: 'button', class: ['swatch-btn', col === c.groundColor && 'on'], onclick: () => c.setGround(col) },
        h('i', { style: { background: cssColor(col), height: '48px', borderRadius: '12px' } }), name))),
    h('label', { class: 'row', style: { fontWeight: 600, fontSize: '15px' } }, 'Any colour',
      h('input', { id: 'ground-any', type: 'color', value: cssColor(c.groundColor), oninput: e => c.setGround(parseInt(e.target.value.slice(1), 16)) })),
  ], { key: 'ground' });
}
