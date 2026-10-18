// Port of GameController.swift: owns one play session — rules engine, ant scheduler, raster,
// clock, slots, hints, sounds and saving. @Published properties are plain fields; every change
// calls this.changed(), which asks the UI to re-render (coalesced to one frame).

import { Board } from '../core/board.js';
import { Game } from '../core/engine.js';
import { HintSolver } from '../core/hint.js';
import {
  AntScheduler, MosaicRaster, SoundBoard, Sfx, ScoreRules, ChallengeModifier, ColourRule,
  SaveStore, makeSaveGame, makeHighScoreEntry, levelChambers, difficultyTitle, paletteName,
  PathStyleDefault, busyEntries, soilColor, canvasDataURL,
} from './compat.js';

const SPEED_MIN = 0.1, SPEED_MAX = 16.0;
const nowMs = () => performance.now();
let controllerCounter = 1;

/** Game clock: re-anchoring keeps game time continuous when the speed changes. */
class GameClock {
  constructor() { this.anchorDate = nowMs(); this.anchorTime = 0; this.speed = 1; }
  time(atMs) { return this.anchorTime + (atMs - this.anchorDate) / 1000 * this.speed; }
  set(speed, atMs) { this.anchorTime = this.time(atMs); this.anchorDate = atMs; this.speed = speed; }
}

export const CoachStep = Object.freeze({
  tapTeam: { id: 'tapTeam', title: 'Send out a team', message: 'Tap the team at the front of a tunnel. Its ants crawl out of the hill and fetch every reachable tile of their colour. Each tap sends the next team in line.' },
  watchAnts: { id: 'watchAnts', title: 'Each team takes a slot', message: 'A sent team occupies a slot, counting down until its ants have picked up every tile. While slots are open you can send more teams, and they all work at once.' },
  chamber: { id: 'chamber', title: 'A team is waiting', message: "That team couldn't reach all its tiles, so it keeps its slot and waits. It resumes by itself when its colour is uncovered — there's nothing else to do to make a team wait." },
  slotsFull: { id: 'slotsFull', title: 'All slots are busy', message: 'A team can only be sent into an open slot. Wait for a working team to finish, or use the speed slider to hurry the ants.' },
  scout: { id: 'scout', title: 'Scout before you send', message: "Press and hold a team to scout it: the tiles it would take light up and you'll see whether it would have to wait." },
  jam: { id: 'jam', title: 'The colony is blocked', message: "Every slot holds a team that's waiting for tiles it can't reach. Undo is free, or add a slot, or tap a waiting team to return it to its tunnel." },
  showcaseIntro: { id: 'showcaseIntro', title: '6,048 tiles to carry home', message: 'Ants can only reach tiles touching open ground, so peel the frame first. Pinch the board to zoom in on the ants; hold a team to scout.' },
  photoIntro: { id: 'photoIntro', title: 'Your photo is now a mosaic', message: 'White areas of your photo became open ground. Every coloured tile is part of the puzzle, and the teams were built so the mosaic can be cleared.' },
});

export class GameController {
  static speedRange = [SPEED_MIN, SPEED_MAX];

  /**
   * @param level LevelDefinition  @param difficulty 'gentle'|'classic'|'expert'
   * @param modifiers Set of ChallengeModifier ids  @param app AppModel  @param save SaveGame|null
   */
  constructor(level, difficulty, modifiers, app, save, onChange) {
    this.uid = controllerCounter++;
    this.level = level;
    this.difficulty = difficulty;
    this.modifiers = new Set(modifiers || []);
    this.app = app;
    this.onChange = onChange || (() => {});
    const b = new Board(level.art);
    this.board = b;
    this.palette = level.palette;
    const cap = levelChambers(level, difficulty);
    let g = new Game(level, b, cap);
    let restoredUndos = 0, restoredHints = 0, restoredElapsed = 0;
    if (save) {
      const rg = Game.replay(level, b, cap, save.moves);
      if (rg) { g = rg; restoredUndos = save.undos; restoredHints = save.hints; restoredElapsed = save.elapsed; }
    }
    this.game = g;
    this.moveFamilies = GameController.families(level, b, cap, g.moves);
    const settings = app ? app.settings : null;
    const sch = new AntScheduler(b, level.palette);
    for (const claims of g.moveClaims) sch.completeInstantly(claims);
    this.scheduler = sch;
    this.raster = null;
    this.miniImage = null;          // data URL of the nest miniature
    this.miniShown = new Uint8Array(b.count);
    this.miniDirty = false;
    this.miniBuiltAt = -Infinity;
    this.clock = new GameClock();
    this.slotOwners = [];

    this.revision = 0;
    this.deliveredCount = 0;
    this.animating = false;
    this.scout = null;
    this.hint = null;
    this.hintBusy = false;
    this.visuallyComplete = false;
    this.coach = null;
    this.speed = 1;
    this.undos = restoredUndos;
    this.hintsUsed = restoredHints;
    this.hapticTick = 0;
    this.refusedTick = 0;
    this.fitBadges = [];
    this.slots = [];
    this.occupiedSlots = 0;
    this.blocked = false;
    this.nextFreeSeconds = null;
    this.eventText = null;
    this.eventExpiry = -Infinity;
    this.groundColor = settings ? settings.groundColor : soilColor();
    this.detailedAnts = settings ? settings.detailedAnts : true;
    this.soundOn = settings ? settings.soundOn : true;
    this.pathStyle = settings ? settings.pathStyle : PathStyleDefault;
    this.soundCursor = 0;
    this.soundSpeed = 1;
    this.soundsLive = false;
    this.familyLeft = [];
    this.milestone = 0;
    this.completionNews = null;
    this.scoreBreakdown = null;
    this.highScoreRank = null;
    this.savedHighScorePlace = null;
    this.elapsed = restoredElapsed;
    this.scoutSet = new Set();
    this.lastTickMs = nowMs();

    const savedSpeed = settings ? settings.antSpeed : 1;
    this.speed = Math.min(SPEED_MAX, Math.max(SPEED_MIN, savedSpeed || 1));
    this.clock.set(this.speed, nowMs());
    this.scheduler.style = this.pathStyle;
    this.refreshMiniature(true);
    this.refreshFitBadges();
    this.refreshSlots(this.now);
    this.startCoachIfNeeded();
    this.soundCursor = this.now;
    this.soundSpeed = this.speed;
    this.milestone = b.tileCount === 0 ? 0 : Math.min(3, Math.floor(this.deliveredCount * 4 / b.tileCount));
    this.checkGoals(this.now);
    this.soundsLive = true;
    SoundBoard.shared.prepare();
  }

  changed() {
    if (this.boardCanvas) this.boardCanvas.invalidate();
    this.onChange(this);
  }

  // MARK: - Time & speed

  get now() { return this.clock.time(nowMs()); }
  gameTime(atMs) { return this.clock.time(atMs); }

  setSpeed(s) {
    const v = Math.min(SPEED_MAX, Math.max(SPEED_MIN, s));
    this.speed = v;
    this.clock.set(v, nowMs());
    if (Math.abs(Math.log(v / this.soundSpeed)) > Math.log(1.25)) {
      SoundBoard.shared.cancelQueuedClicks();
      this.soundCursor = Math.min(this.soundCursor, this.now);
      this.soundSpeed = v;
    }
    this.changed();
  }

  commitSpeed() { if (this.app) this.app.updateSettings(s => { s.antSpeed = this.speed; }); }

  setGround(color) {
    if (color === this.groundColor) return;
    this.groundColor = color;
    this.raster = null;
    if (this.app) this.app.updateSettings(s => { s.groundColor = color; });
    this.animating = true;
    this.changed();
  }

  // MARK: - Derived state for the UI

  get tunnelCount() { return this.game.tunnels.length; }
  front(q) { return this.game.front(q); }
  upcoming(q, count = 3) { return this.game.upcoming(q, count); }
  fullQueue(q) {
    const out = [];
    const f = this.game.front(q);
    if (f) out.push({ family: f.family, quota: f.need });
    for (const s of this.game.upcoming(q, 10000)) out.push(s);
    return out;
  }
  remaining(q) { return this.game.remainingInTunnel(q); }
  get chambers() { return this.game.state.chambers; }
  get capacity() { return this.game.state.capacity; }
  get addedChambers() { return this.game.state.added; }
  get jammedTeam() { return this.game.state.jammed; }
  get isJammed() { return this.game.isJammed; }
  get isBlocked() { return this.blocked || this.game.isJammed; }
  get hasOpenSlot() { return this.occupiedSlots < this.capacity; }
  get canUndo() { const l = this.undosLeft; return this.game.canUndo && (l === null ? 1 : l) > 0; }
  get undosLeft() {
    return this.modifiers.has(ChallengeModifier.limitedUndo) ? Math.max(0, ChallengeModifier.undoLimit - this.undos) : null;
  }
  get hintsAllowed() { return !this.modifiers.has(ChallengeModifier.noHints); }
  get scoutAllowed() { return !this.modifiers.has(ChallengeModifier.noScout); }
  get assistsAllowed() { return !this.modifiers.has(ChallengeModifier.noAssists); }
  get queueHidden() { return this.modifiers.has(ChallengeModifier.hiddenQueue); }
  get scoreFactor() { return ScoreRules.difficultyFactor(this.difficulty) * ScoreRules.modifierFactor(this.modifiers); }
  get isLogicallyWon() { return this.game.isWon; }
  get moveCount() { let n = 0; for (const m of this.game.moves) if (!Game.isAssist(m)) n++; return n; }
  get assistCount() { let n = 0; for (const m of this.game.moves) if (Game.isAssist(m)) n++; return n; }
  get claimedCount() { return this.game.state.cleared; }
  get progress() { return this.board.tileCount === 0 ? 0 : this.deliveredCount / this.board.tileCount; }
  get scoutTiles() { return this.scoutSet; }

  canSend(q) { return this.game.canDispatch(q) && this.hasOpenSlot && this.colourRefusal(q) === null; }

  get lastSentFamily() {
    if (this.moveFamilies.length !== this.game.moves.length) {
      this.moveFamilies = GameController.families(this.level, this.board, levelChambers(this.level, this.difficulty), this.game.moves);
    }
    for (let i = this.moveFamilies.length - 1; i >= 0; i--) if (this.moveFamilies[i] >= 0) return this.moveFamilies[i];
    return null;
  }

  colourRefusal(q) {
    if (!this.modifiers.has(ChallengeModifier.noRepeatColour)) return null;
    const last = this.lastSentFamily;
    if (last === null || !ColourRule.refuses(this.game, q, last)) return null;
    return `No colour twice: ${paletteName(this.palette, last)} was the last colour sent — send another colour first.`;
  }

  static families(level, board, capacity, moves) {
    const g = new Game(level, board, capacity);
    const out = [];
    for (const code of moves) {
      let fam = -1;
      if (code >= 0 && code < Game.addChamberMove) {
        const f = g.front(code);
        fam = f ? f.family : -1;
      } else if (code >= Game.releaseBase) {
        const i = code - Game.releaseBase;
        if (i >= 0 && i < g.state.chambers.length) fam = g.state.chambers[i].family;
      }
      g.apply(code);
      out.push(fam);
    }
    return out;
  }

  get hintTunnel() {
    const h = this.hint;
    return h && h.kind === 'move' && h.code < Game.addChamberMove ? h.code : null;
  }
  get hintChamber() {
    const h = this.hint;
    return h && h.kind === 'move' && h.code >= Game.releaseBase ? h.code - Game.releaseBase : null;
  }

  playHint() {
    const h = this.hint;
    if (!h || h.kind !== 'move') return;
    if (h.code >= Game.releaseBase) this.release(h.code - Game.releaseBase); else this.dispatch(h.code);
  }

  // MARK: - Raster

  ensureRaster(cellPx) {
    if (this.raster && this.raster.cellPx === cellPx) return this.raster;
    const t = this.now;
    const b = this.board;
    const open = b.initialOpen();
    const lift = this.scheduler.liftTime;
    for (let i = 0; i < b.count; i++) if (b.family[i] >= 0) open[i] = lift[i] <= t ? 1 : 0;
    this.raster = new MosaicRaster(b, this.palette, cellPx, open, this.groundColor);
    return this.raster;
  }

  // MARK: - Slots

  refreshSlots(t, natural = false) {
    const busy = busyEntries(this.scheduler.busyTeams(t)); // Map uid -> tiles still to pick up
    const chamberList = this.game.state.chambers;
    const chamberIndex = new Map();
    chamberList.forEach((c, i) => chamberIndex.set(c.uid, i));
    const occupants = new Set(busy.keys());
    for (const c of chamberList) occupants.add(c.uid);
    let freed = 0;
    for (let k = 0; k < this.slotOwners.length; k++) {
      const u = this.slotOwners[k];
      if (u !== null && !occupants.has(u)) { this.slotOwners[k] = null; freed++; }
    }
    if (natural && freed > 0 && this.soundsLive) SoundBoard.shared.play(Sfx.teamDone);
    const cap = this.game.state.capacity;
    if (this.slotOwners.length < cap) {
      while (this.slotOwners.length < cap) this.slotOwners.push(null);
    } else if (this.slotOwners.length > cap) {
      this.slotOwners = this.slotOwners.filter(u => u !== null);
      while (this.slotOwners.length < cap) this.slotOwners.push(null);
    }
    const placed = new Set(this.slotOwners.filter(u => u !== null));
    const newcomers = chamberList.map(c => c.uid).filter(u => !placed.has(u));
    for (const u of [...busy.keys()].sort((a, b) => a - b)) if (!placed.has(u) && !chamberIndex.has(u)) newcomers.push(u);
    for (const u of newcomers) {
      const free = this.slotOwners.indexOf(null);
      if (free >= 0) this.slotOwners[free] = u; else this.slotOwners.push(u);
    }
    const items = [];
    this.slotOwners.forEach((u, k) => {
      if (u === null) { items.push({ id: k, kind: 'open' }); return; }
      if (chamberIndex.has(u)) {
        const ci = chamberIndex.get(u);
        const team = chamberList[ci];
        if (team.held) items.push({ id: k, kind: 'held', chamber: ci, uid: u, family: team.family, need: team.remaining });
        else items.push({ id: k, kind: 'waiting', chamber: ci, uid: u, family: team.family, toCollect: team.remaining + (busy.get(u) || 0) });
      } else {
        const trip = this.scheduler.trips.find(tr => tr.team === u);
        items.push({ id: k, kind: 'working', uid: u, family: trip ? trip.family : 0, toCollect: busy.get(u) || 0 });
      }
    });
    let slotsChanged = items.length !== this.slots.length;
    if (!slotsChanged) for (let i = 0; i < items.length; i++) {
      const a = items[i], b = this.slots[i];
      if (a.kind !== b.kind || a.uid !== b.uid || a.family !== b.family || a.toCollect !== b.toCollect || a.need !== b.need || a.chamber !== b.chamber) { slotsChanged = true; break; }
    }
    let dirty = false;
    if (slotsChanged) { this.slots = items; dirty = true; }
    const occ = occupants.size;
    if (occ !== this.occupiedSlots) { this.occupiedSlots = occ; dirty = true; }
    let busyOutside = 0;
    for (const u of busy.keys()) if (!chamberIndex.has(u)) busyOutside++;
    const isBlockedNow = this.game.deadlocked(busyOutside);
    if (isBlockedNow !== this.blocked) {
      this.blocked = isBlockedNow;
      dirty = true;
      if (isBlockedNow) {
        this.showCoach(CoachStep.jam);
        if (this.soundsLive) SoundBoard.shared.play(Sfx.blocked);
      }
    }
    let nextFree = null;
    if (occ >= cap) {
      let soonest = Infinity;
      for (const u of busy.keys()) soonest = Math.min(soonest, this.scheduler.slotFreeTime(u));
      if (Number.isFinite(soonest)) nextFree = Math.max(0, (soonest - t) / Math.max(0.01, this.speed));
    }
    const rounded = nextFree === null ? null : Math.ceil(nextFree * 2) / 2;
    if (rounded !== this.nextFreeSeconds) { this.nextFreeSeconds = rounded; dirty = true; }
    return dirty;
  }

  refuseBecauseFull() {
    this.refusedTick++;
    SoundBoard.shared.play(Sfx.refused);
    const s = this.nextFreeSeconds;
    if (s !== null && s > 0 && s < 1e6) {
      this.announce(`All ${this.capacity} slots are busy — the next one frees in about ${Math.ceil(s)} s. Speed up the ants to hurry.`);
    } else {
      this.announce(`All ${this.capacity} slots are taken. Wait for a team to finish, or return a waiting team.`);
    }
    this.showCoach(CoachStep.slotsFull);
    this.changed();
  }

  // MARK: - Actions

  dispatch(q) {
    this.refreshSlots(this.now);
    const fr = this.game.front(q);
    if (!fr || this.game.isJammed) return;
    if (!(this.hasOpenSlot && this.game.canDispatch(q))) { this.refuseBecauseFull(); return; }
    const why = this.colourRefusal(q);
    if (why) {
      this.refusedTick++;
      SoundBoard.shared.play(Sfx.refused);
      this.announce(why);
      this.changed();
      return;
    }
    const chambersBefore = this.game.state.chambers.length;
    this.clearTransient();
    void this.lastSentFamily;
    const ev = this.game.dispatch(q);
    this.moveFamilies.push(fr.family);
    this.scheduler.schedule(ev, this.game.moves.length - 1, this.now + 0.04);
    this.hapticTick++;
    haptic(8);
    SoundBoard.shared.play(Sfx.send);
    if (this.game.state.chambers.length > chambersBefore) SoundBoard.shared.play(Sfx.wait, 0.28);
    this.describeSend(`Tunnel ${q + 1}`, fr.uid, fr.need, ev);
    this.afterLogicalChange();
    if (this.coach === CoachStep.tapTeam) this.dismissCoach();
    if (this.game.state.chambers.length > chambersBefore) this.showCoach(CoachStep.chamber);
    else if (this.moveCount === 1) this.showCoach(CoachStep.watchAnts);
    else if (this.moveCount >= 4) this.showCoach(CoachStep.scout);
    this.changed();
  }

  undo() {
    if (!this.game.canUndo) return;
    const left = this.undosLeft;
    if (left !== null && left <= 0) {
      this.refusedTick++;
      SoundBoard.shared.play(Sfx.refused);
      this.announce(`No undos left — this game allows ${ChallengeModifier.undoLimit}.`);
      this.changed();
      return;
    }
    void this.lastSentFamily;
    const claims = this.game.undo();
    if (!claims) return;
    if (this.moveFamilies.length) this.moveFamilies.pop();
    this.scheduler.undo(claims, this.game.moves.length);
    this.undos++;
    SoundBoard.shared.play(Sfx.undo);
    this.clearTransient();
    if (this.raster) this.raster.sync(this.scheduler.liftTime, this.now);
    this.afterLogicalChange();
    this.changed();
  }

  undoTimes(n) { for (let i = 0; i < Math.max(0, n); i++) this.undo(); }

  addChamber() {
    if (!this.assistsAllowed) {
      this.refusedTick++;
      this.announce('Assists are off in this game (No assists).');
      this.changed();
      return;
    }
    void this.lastSentFamily;
    this.game.addChamber();
    this.moveFamilies.push(-1);
    this.clearTransient();
    SoundBoard.shared.play(Sfx.addSlot);
    this.announce(`Added a slot (${this.game.state.capacity} now). Counted as an assist.`);
    this.afterLogicalChange();
    this.changed();
  }

  recall(index) {
    if (!this.game.canRecall(index)) return;
    if (!this.assistsAllowed) {
      this.refusedTick++;
      this.announce("Assists are off in this game (No assists): waiting teams can't be returned.");
      this.changed();
      return;
    }
    const t = this.game.state.chambers[index];
    void this.lastSentFamily;
    this.game.recall(index);
    this.moveFamilies.push(-1);
    this.clearTransient();
    SoundBoard.shared.play(Sfx.returnTeam);
    this.announce(`Returned the team of ${t.remaining} to the front of tunnel ${Math.floor(t.uid / 1000) + 1}. Its slot is open.`);
    this.afterLogicalChange();
    this.changed();
  }

  recallJammed() {
    void this.lastSentFamily;
    this.game.recallJammed();
    this.moveFamilies.push(-1);
    this.clearTransient();
    this.afterLogicalChange();
    this.changed();
  }

  release(index) {
    if (!this.game.canRelease(index)) return;
    const t = this.game.state.chambers[index];
    this.clearTransient();
    void this.lastSentFamily;
    const ev = this.game.release(index);
    this.moveFamilies.push(t.family);
    this.scheduler.schedule(ev, this.game.moves.length - 1, this.now + 0.04);
    this.hapticTick++;
    SoundBoard.shared.play(Sfx.send);
    this.describeSend('Held team', t.uid, t.remaining, ev);
    this.afterLogicalChange();
    this.changed();
  }

  describeSend(source, uid, need, claims) {
    let own = 0;
    for (const c of claims) if (c.team === uid) own++;
    const others = claims.length - own;
    const extra = others > 0 ? ` Waiting teams picked up ${others} more.` : '';
    if (own === need) {
      this.announce(`${source}: team of ${need} sent — every tile is reachable; its slot frees when the ants have picked them all up.` + extra);
    } else {
      this.announce(`${source}: team reached ${own} of ${need} tiles now and keeps its slot, waiting for the rest.` + extra);
    }
  }

  announce(text) {
    this.eventText = text;
    this.eventExpiry = nowMs() + 6000;
  }

  restart() {
    this.game = new Game(this.level, this.board, levelChambers(this.level, this.difficulty));
    this.scheduler = new AntScheduler(this.board, this.palette);
    this.scheduler.style = this.pathStyle;
    if (this.raster) this.raster = new MosaicRaster(this.board, this.palette, this.raster.cellPx, this.board.initialOpen(), this.groundColor);
    this.clearTransient();
    this.undos = 0;
    this.hintsUsed = 0;
    this.elapsed = 0;
    this.visuallyComplete = false;
    this.deliveredCount = 0;
    this.eventText = null;
    this.slotOwners = [];
    this.clock = new GameClock();
    this.clock.set(this.speed, nowMs());
    this.soundCursor = 0;
    this.milestone = 0;
    this.familyLeft = [];
    this.completionNews = null;
    this.scoreBreakdown = null;
    this.highScoreRank = null;
    this.savedHighScorePlace = null;
    this.moveFamilies = [];
    SoundBoard.shared.play(Sfx.undo);
    SaveStore.clearGame(this.level.id);
    this.miniShown.fill(0);
    this.refreshMiniature(true);
    this.afterLogicalChange(false);
    this.changed();
  }

  clearTransient() {
    this.scout = null;
    this.scoutSet = new Set();
    this.hint = null;
  }

  beginScout(q) {
    if (!this.scoutAllowed) { this.announce('Scouting is off in this game (No scouting).'); this.changed(); return; }
    const rep = this.game.scout(q);
    if (!rep) return;
    this.scout = rep;
    this.scoutSet = new Set(rep.ownTiles);
    this.animating = true;
    SoundBoard.shared.play(Sfx.scout);
    if (this.coach === CoachStep.scout) this.dismissCoach();
    this.changed();
  }

  endScout() {
    this.scout = null;
    this.scoutSet = new Set();
    this.changed();
  }

  requestHint() {
    if (this.hintBusy || !this.hintsAllowed) return;
    this.hintBusy = true;
    this.hintsUsed++;
    this.changed();
    const b = this.board, tunnels = this.game.tunnels, st = this.game.state, mv = this.game.moves.slice(), sol = this.level.solution;
    const stale = () => this.game.state !== st;
    const done = r => { if (stale()) { this.hintBusy = false; this.changed(); return; } this.applyHint(r); };
    if (this.app && this.app.runHint) {
      // off the main thread (the search can take seconds off the designed line)
      this.app.runHint(this.level, tunnels, st, mv, sol).then(done, () => done(HintSolver.hint(b, tunnels, st, mv, sol)));
    } else {
      setTimeout(() => done(HintSolver.hint(b, tunnels, st, mv, sol)), 30);
    }
  }

  applyHint(r) {
    this.hintBusy = false;
    this.hint = r;
    SoundBoard.shared.play(Sfx.hint);
    this.animating = true;
    this.save();
    this.changed();
  }

  clearHint() { this.hint = null; this.changed(); }

  afterLogicalChange(doSave = true) {
    this.revision++;
    this.animating = true;
    this.refreshFitBadges();
    this.refreshSlots(this.now);
    if (doSave) this.save();
  }

  refreshFitBadges() {
    if (!this.scoutAllowed) { this.fitBadges = []; return; }
    const out = [];
    for (let q = 0; q < this.game.tunnels.length; q++) {
      const rep = this.game.scout(q);
      out.push(rep ? rep.fits : null);
    }
    this.fitBadges = out;
  }

  // MARK: - Tick (10 Hz, driven by the game screen)

  tick() {
    if (this.visuallyComplete) return false;
    const t = this.now;
    const ms = nowMs();
    // Real elapsed time (the Swift timer adds 0.1 s per tick); hidden tabs don't count.
    this.elapsed += Math.min(0.5, Math.max(0, (ms - this.lastTickMs) / 1000));
    this.lastTickMs = ms;
    let dirty = false;
    if (this.raster) this.raster.sync(this.scheduler.liftTime, t);
    if (this.refreshMiniature(false)) dirty = true;
    if (this.refreshSlots(t, true)) dirty = true;
    if (this.checkGoals(t)) dirty = true;
    this.pumpTileSounds(t);
    this.scheduler.prune(t - 0.5);
    if (this.eventText !== null && ms > this.eventExpiry) { this.eventText = null; dirty = true; }
    const busy = this.scheduler.isBusy;
    const wantAnimating = busy || this.scout !== null || this.hint !== null;
    if (this.animating !== wantAnimating) { this.animating = wantAnimating; dirty = true; }
    if (this.game.isWon && !busy && !this.visuallyComplete) {
      this.visuallyComplete = true;
      dirty = true;
      SaveStore.clearGame(this.level.id);
      const news = this.app ? this.app.recordCompletion(this.level.id, this.elapsed, this.undos, this.difficulty, this.modifiers.size) : null;
      this.completionNews = news;
      const breakdown = ScoreRules.solo(this.board.tileCount, this.difficulty, this.modifiers, this.undos, this.hintsUsed, this.assistCount);
      this.scoreBreakdown = breakdown;
      this.highScoreRank = this.app ? this.app.highScoreRank('solo', this.level.id, breakdown.score, this.elapsed) : null;
      const sb = SoundBoard.shared;
      sb.play(Sfx.complete);
      let delay = 2.1;
      if ((news && news.newBest) || this.highScoreRank !== null) { sb.play(Sfx.newBest, delay); delay += 1.0; }
      if (news && news.unlocked.length > 0) sb.play(Sfx.unlocked, delay);
    }
    if (dirty) this.changed();
    return dirty;
  }

  checkGoals(t) {
    const fc = Math.max(1, this.palette.tones.length);
    const left = new Array(fc).fill(0);
    const lift = this.scheduler.liftTime;
    const b = this.board;
    for (let i = 0; i < b.count; i++) {
      const f = b.family[i];
      if (f >= 0 && f < fc && lift[i] > t) left[f]++;
    }
    const remaining = left.reduce((a, c) => a + c, 0);
    let dirty = false;
    if (this.soundsLive && this.familyLeft.length === left.length && remaining > 0) {
      for (let f = 0; f < left.length; f++) {
        if (left[f] === 0 && this.familyLeft[f] > 0) {
          SoundBoard.shared.play(Sfx.colourCleared);
          this.announce(`Every ${paletteName(this.palette, f)} tile has been lifted.`);
          dirty = true;
          break;
        }
      }
    }
    this.familyLeft = left;
    const quarter = b.tileCount === 0 ? 0 : Math.min(3, Math.floor(this.deliveredCount * 4 / b.tileCount));
    if (quarter > this.milestone) {
      if (this.soundsLive) SoundBoard.shared.play(quarter === 1 ? Sfx.milestone1 : quarter === 2 ? Sfx.milestone2 : Sfx.milestone3);
      this.milestone = quarter;
    }
    return dirty;
  }

  /** Hands the sound board every pickup and nest drop due before the next tick, with exact delays. */
  pumpTileSounds(t) {
    const horizon = t + 0.16 * this.speed;
    const from = Math.max(this.soundCursor, t - 0.3 * this.speed);
    this.soundCursor = Math.max(this.soundCursor, horizon);
    this.soundSpeed = this.speed;
    const sb = SoundBoard.shared;
    if (!sb.isOn || !sb.tileClicks || !(horizon > from)) return;
    const b = this.board;
    const holeColumn = b.hole % b.cols;
    const events = [];
    for (const trip of this.scheduler.trips) {
      if (trip.arrive > from && trip.arrive <= horizon) events.push({ time: trip.arrive, pickup: true, family: trip.family, column: trip.tile % b.cols });
      if (trip.home > from && trip.home <= horizon) events.push({ time: trip.home, pickup: false, family: trip.family, column: holeColumn });
    }
    if (events.length === 0) return;
    events.sort((a, c) => a.time - c.time);
    const width = Math.max(1, b.cols - 1);
    const pace = Math.max(0.01, this.speed);
    for (const e of events) {
      const delay = Math.max(0, (e.time - t) / pace);
      const pan = (e.column / width * 2 - 1) * 0.7;
      if (e.pickup) sb.tile(e.family, pan, delay); else sb.deliver(pan, delay);
    }
  }

  refreshMiniature(force) {
    const t = this.now;
    let changed = force;
    let count = 0;
    const home = this.scheduler.homeTime;
    const b = this.board;
    for (let i = 0; i < b.count; i++) {
      if (b.family[i] < 0) continue;
      const shown = home[i] <= t ? 1 : 0;
      if (shown) count++;
      if (shown !== this.miniShown[i]) { this.miniShown[i] = shown; changed = true; }
    }
    if (changed) this.miniDirty = true;
    let dirty = false;
    const ms = nowMs();
    if (this.miniDirty && (force || count === b.tileCount || ms - this.miniBuiltAt >= 500)) {
      const snap = this.miniShown.slice();
      const canvas = MosaicRaster.miniature(b, this.palette, i => snap[i] === 1);
      this.miniImage = canvas ? canvasDataURL(canvas) : null;
      this.miniDirty = false;
      this.miniBuiltAt = ms;
      dirty = true;
    }
    if (count !== this.deliveredCount) { this.deliveredCount = count; dirty = true; }
    return dirty;
  }

  // MARK: - Coaching

  startCoachIfNeeded() {
    if (this.game.moves.length > 0) return;
    if (this.level.id === 'firstDig') this.showCoach(CoachStep.tapTeam);
    else if (this.level.id === 'sunflower') this.showCoach(CoachStep.showcaseIntro);
    else if (this.level.isPhoto && !this.level.id.startsWith('pattern-')) this.showCoach(CoachStep.photoIntro);
  }

  showCoach(step) {
    if (!this.app) return;
    if (this.app.settings.coachSeen.includes(step.id)) return;
    this.coach = step;
  }

  dismissCoach() {
    if (this.coach && this.app) this.app.markCoachSeen(this.coach.id);
    this.coach = null;
    this.changed();
  }

  // MARK: - Saving

  save() {
    if (this.game.moves.length === 0 || this.visuallyComplete) {
      if (this.game.moves.length === 0) SaveStore.clearGame(this.level.id);
      return;
    }
    SaveStore.saveGame(makeSaveGame(this.level.id, this.difficulty, this.game.moves.slice(), this.undos, this.hintsUsed,
      this.elapsed, ChallengeModifier.sorted(this.modifiers)));
  }

  saveHighScore(name) {
    const b = this.scoreBreakdown;
    if (!b || this.savedHighScorePlace !== null || this.highScoreRank === null) return;
    const entry = makeHighScoreEntry(name, b.score, this.elapsed, this.difficulty, ChallengeModifier.sorted(this.modifiers));
    const place = this.app ? this.app.saveHighScore('solo', this.level.id, entry) : 0;
    this.savedHighScorePlace = place == null ? 0 : place;
    this.changed();
  }

  get topScores() { return this.app ? this.app.topScores('solo', this.level.id) : []; }
  get playerName() { return this.app ? this.app.settings.playerName || '' : ''; }

  setPathStyle(s) {
    this.pathStyle = s;
    this.scheduler.style = s;
    if (this.app) this.app.updateSettings(st => { st.pathStyle = s; });
    this.changed();
  }

  setSoundOn(on) {
    this.soundOn = on;
    if (this.app) this.app.updateSettings(st => { st.soundOn = on; });
    this.changed();
  }

  setDetailedAnts(on) {
    this.detailedAnts = on;
    if (this.app) this.app.updateSettings(st => { st.detailedAnts = on; });
    this.changed();
  }

  get difficultyTitle() { return difficultyTitle(this.difficulty); }
}

function haptic(ms) {
  try { if (navigator.vibrate) navigator.vibrate(ms); } catch (e) { /* not supported */ }
}
