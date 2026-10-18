// Entry point (RootView in AppModel.swift): loads the level data, opens storage, builds the
// AppModel, and renders Home, a game or a two-player match. Re-renders are coalesced to one
// per animation frame; the game ticks at 10 Hz like the Swift task loop.
import { render } from './ui/vdom.js';
import { homeView } from './ui/homeView.js';
import { gameView } from './ui/gameView.js';
import { SoundBoard } from './ui/compat.js';
import { bootApp } from './ui/boot.js';
import { versusView, versusSetupSheet } from './ui/versusView.js';

const root = document.getElementById('app');
const ui = { sheet: null, dialog: null, menu: null };
let app = null;
let scheduled = false;
let lastScreen = null;

function size() {
  return { w: root.clientWidth || window.innerWidth, h: root.clientHeight || window.innerHeight };
}

function rerender() {
  if (scheduled) return;
  scheduled = true;
  requestAnimationFrame(draw);
}

function draw() {
  scheduled = false;
  if (!app) return;
  const screen = app.versus ? 'versus' : app.current ? 'game' : 'home';
  const screenKey = screen + ':' + (app.versus ? app.versus.uid : app.current ? app.current.uid : '');
  if (screenKey !== lastScreen) {
    // a new screen starts with no sheet, dialog or menu open
    if (lastScreen !== null) { ui.sheet = null; ui.dialog = null; ui.menu = null; ui.nameDraft = null; ui.vs = null; ui.start = null; }
    lastScreen = screenKey;
  }
  const ctx = { app, ui, size: size(), rerender, versusSetupSheet };
  let node;
  if (screen === 'versus') node = versusView(Object.assign(ctx, { match: app.versus }));
  else if (screen === 'game') node = gameView(Object.assign(ctx, { controller: app.current }));
  else node = homeView(ctx);
  try {
    render(node, root);
  } catch (e) {
    // a half-applied patch would break every later frame: start the page over from scratch
    root.__vnode = null;
    root.textContent = '';
    render(node, root);
    console.error(e);
  }
}

function tick() {
  if (!app || document.visibilityState === 'hidden') return;
  if (app.current) app.current.tick();
  if (app.versus && app.versus.tick) app.versus.tick();
}

function unlockAudio() {
  try { SoundBoard.shared.unlock(); } catch (e) { /* audio unavailable */ }
}

function start() {
  app = bootApp(rerender);
  window.__tc = { app, SoundBoard };   // for diagnostics from the console
  if (typeof ResizeObserver !== 'undefined') new ResizeObserver(rerender).observe(root);
  else window.addEventListener('resize', rerender);
  // iPhone/iPad only treat touchend / pointerup / click as gestures that may start audio
  for (const t of ['pointerup', 'touchend', 'click']) window.addEventListener(t, unlockAudio, { capture: true });
  window.addEventListener('keydown', e => {
    unlockAudio();
    if (e.key === 'Escape') {
      if (ui.menu) ui.menu = null;
      else if (ui.dialog) ui.dialog = null;
      else if (ui.sheet) { ui.sheet = null; ui.start = null; ui.vs = null; }
      else return;
      rerender();
    }
  }, { capture: true });
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden' && app && app.current) app.current.save();
    rerender();
  });
  window.addEventListener('pagehide', () => { if (app && app.current) app.current.save(); });
  setInterval(tick, 100);
  rerender();
}

try {
  start();
} catch (e) {
  root.innerHTML = '';
  const box = document.createElement('div');
  box.className = 'loading';
  box.style.flexDirection = 'column';
  box.style.padding = '24px';
  box.textContent = 'Tessera Colony could not start: ' + (e && e.message ? e.message : String(e));
  root.appendChild(box);
  throw e;
}
