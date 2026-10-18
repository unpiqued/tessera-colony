// Start-up: level data, storage, the builder worker, and the AppModel with its hooks (the parts of
// AppModel.swift / RootView that need the browser). Kept apart from compat.js so the screens'
// adapter never imports the controllers that import it.
import { Board } from '../core/board.js';
import { setLevelData } from '../core/levelData.js';
import { LevelDefinition, LevelPalette, DifficultyStats } from '../core/level.js';
import { SaveStore } from '../core/saveStore.js';
import { AppModel } from '../core/appModel.js';
import { SoundBoard, soundCheckReport } from '../sound/soundBoard.js';
import { createBuilder } from '../builders/builderWorker.js';
import { pixelsFromImage } from '../builders/photoLevelBuilder.js';
import { GameController } from './gameController.js';
import { VersusController } from './versusController.js';
import { createStorage } from './storage.js';
import { thumbURL, forgetThumb } from './compat.js';

/** Plain level objects from the worker → LevelDefinition (palette methods, chambers(), counts). */
function toLevelDefinition(plain) {
  if (!plain) return null;
  if (plain instanceof LevelDefinition) return plain;
  return new LevelDefinition(Object.assign({}, plain, { palette: LevelPalette.from(plain.palette), isPhoto: true }));
}

/** Decode a picked image file into pixels at the size the iPad app decodes photos (≤ 720 px). */
async function decodePhoto(file) {
  let img = null, w = 0, h = 0, url = null;
  try {
    if (typeof createImageBitmap === 'function') {
      img = await createImageBitmap(file);
      w = img.width; h = img.height;
    }
  } catch (e) { img = null; }
  if (!img) {
    url = URL.createObjectURL(file);
    img = await new Promise((resolve, reject) => {
      const el = new Image();
      el.onload = () => resolve(el);
      el.onerror = () => reject(new Error('unreadable'));
      el.src = url;
    }).catch(() => null);
    if (img) { w = img.naturalWidth; h = img.naturalHeight; }
  }
  try {
    if (!img || !w || !h) return null;
    return pixelsFromImage(img, w, h);
  } finally {
    if (url) URL.revokeObjectURL(url);
    if (img && typeof img.close === 'function') img.close();
  }
}

export function bootApp(rerender) {
  const dataEl = document.getElementById('tc-levels');
  setLevelData(JSON.parse(dataEl.textContent));
  const storage = createStorage();
  SaveStore.setBackend(storage.backend);
  const builder = createBuilder();
  const sound = SoundBoard.shared;

  const hooks = {
    makeGameController: (level, d, mods, a, resume) => new GameController(level, d, mods, a, resume, rerender),
    makeVersusController: (level, rules, a) => new VersusController(level, rules, a, rerender),
    soundBoard: sound,
    thumbnail: level => thumbURL(level),
    measureDifficulty: level => builder.run('probe', { level }).then(r => (r && r.stats ? new DifficultyStats(r.stats.careless, r.stats.greedy) : null)),
    buildPatternLevel: (seed, number) => builder.run('pattern', { seed, number }).then(r => toLevelDefinition(r.level)),
    photoPixels: data => data,   // importPhotoFile decodes the file first
    buildPhotoLevel: (px, detail, seed, id, title) => builder.run('photo', { image: px, detail, seed, id, title }).then(r => {
      const res = r.result;
      if (res.kind === 'success') return { kind: 'success', level: toLevelDefinition(res.value) };
      return { kind: 'failure', error: { message: (res.error && res.error.message) || "The colony couldn't plan a solvable puzzle for this photo. Try a different detail level." } };
    }),
  };
  const app = new AppModel(hooks);
  app.builder = builder;
  app.storage = storage;
  app.subscribe(rerender);
  wireApp(app, rerender);
  storage.onStatus(rerender);
  storage.connect(() => {
    // Newer progress arrived from the viewer's account: reload it unless a game is open.
    const reload = () => { app._reloadFromStore(); rerender(); };
    if (!app.current && !app.versus) reload(); else app._reloadPending = reload;
  });
  document.addEventListener('visibilitychange', () => { try { sound.setHidden(document.visibilityState === 'hidden'); } catch (e) { /* none */ } });
  return app;
}

/** UI-side additions to AppModel (things Swift did in views or through bindings). */
function wireApp(app, rerender) {
  /** Settings writes save themselves (Swift didSet); fn mutates the live settings. */
  app.updateSettings = fn => { fn(app.settings); rerender(); };
  app.notify = () => rerender();
  app.importPhotoFile = file => {
    if (app.photoBusy) return;
    // the photo is decoded here; AppModel.importPhoto builds and opens it
    decodePhoto(file).then(px => app.importPhoto(px || null), () => app.importPhoto(null));
  };
  app.storageNote = () => app.storage.where === 'account'
    ? 'Your progress, saved games and high scores are kept in your Claude account, private to you, so they follow you to other devices.'
    : app.storage.where === 'local'
      ? 'Your progress is saved in this browser on this device. Sign in to Claude to keep it with your account.'
      : 'This browser is not letting the page save, so progress lasts only until you close it.';
  app._reloadFromStore = () => {
    app._settings = SaveStore.loadSettings();
    app._settingsView = null;
    app._progress = SaveStore.loadProgress();
    app._highScores = SaveStore.loadHighScores();
    app._applySound();
  };
  const goHome = app.goHome.bind(app);
  app.goHome = () => {
    const c = app.current;
    if (c && c.boardCanvas) { try { c.boardCanvas.destroy(); } catch (e) { /* gone */ } }
    goHome();
    if (app._reloadPending) { const f = app._reloadPending; app._reloadPending = null; f(); }
  };
  const endVersus = app.endVersus.bind(app);
  app.endVersus = () => {
    const v = app.versus;
    if (v && v.boardCanvases) for (const bc of v.boardCanvases) { try { if (bc) bc.destroy(); } catch (e) { /* gone */ } }
    endVersus();
    if (app._reloadPending) { const f = app._reloadPending; app._reloadPending = null; f(); }
  };
  const deletePhotoLevel = app.deletePhotoLevel.bind(app);
  app.deletePhotoLevel = id => { forgetThumb(id); deletePhotoLevel(id); };
  // Hints run in the builder worker so an off-plan search never freezes the page.
  app.runHint = (level, tunnels, state, moves, solution) =>
    app.builder.run('hint', { art: level.art, tunnels, state, moves, solution }).then(r => r.hint);
  app.soundReport = played => soundCheckReport(SoundBoard.shared.status(), played);
}
