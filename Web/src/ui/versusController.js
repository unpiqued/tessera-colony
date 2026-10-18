// Port of VersusController.swift: one two-player match — the rules (VersusMatch), one ant
// scheduler and raster per board, a shared clock, real-time slot occupancy, upkeep, scores, end.
import {
  AntScheduler, MosaicRaster, SoundBoard, Sfx, VersusMatch, VersusRules, versusOptionTitle,
  makeHighScoreEntry, paletteName, soilColor,
} from './compat.js';

const SPEED_MIN = 0.1, SPEED_MAX = 16.0;
const nowMs = () => performance.now();
let uidCounter = 1;

class GameClock {
  constructor() { this.anchorDate = nowMs(); this.anchorTime = 0; this.speed = 1; }
  time(atMs) { return this.anchorTime + (atMs - this.anchorDate) / 1000 * this.speed; }
  set(speed, atMs) { this.anchorTime = this.time(atMs); this.anchorDate = atMs; this.speed = speed; }
}

export class VersusController {
  static names = ['Player 1', 'Player 2'];

  constructor(level, rules, app, onChange) {
    this.uid = uidCounter++;
    this.level = level;
    this.rules = rules;
    this.app = app;
    this.onChange = onChange || (() => {});
    const m = new VersusMatch(level, rules);
    this.match = m;
    const style = app ? app.settings.pathStyle : 'randomTeam';
    this.schedulers = m.boards.map(b => { const s = new AntScheduler(b.board, level.palette); s.style = style; return s; });
    this.rasters = m.boards.map(() => null);
    this.groundColor = app ? app.settings.groundColor : soilColor();
    this.detailedAnts = app ? app.settings.detailedAnts : true;
    const saved = app ? app.settings.antSpeed : 1;
    this.speed = Math.min(SPEED_MAX, Math.max(SPEED_MIN, saved || 1));
    this.clock = new GameClock();
    this.clock.set(this.speed, nowMs());
    this.lastTick = 0;
    this.moveCounter = 0;
    this.soundCursor = 0;
    this.revision = 0;
    this.occupied = [0, 0];
    this.delivered = [0, 0];
    this.scores = [0, 0];
    this.messages = [null, null];
    this.messageExpiry = [0, 0];
    this.result = null;
    this.refusedTick = 0;
    this.sendTick = 0;
    this.animating = true;
    this.highScoreRank = null;
    this.savedHighScorePlace = null;
    this.startMs = nowMs();
    this.boardCanvases = [];
    SoundBoard.shared.prepare();
  }

  changed() { this.onChange(this); }

  get now() { return this.clock.time(nowMs()); }
  gameTime(atMs) { return this.clock.time(atMs); }

  setSpeed(s) {
    const v = Math.min(SPEED_MAX, Math.max(SPEED_MIN, s));
    this.speed = v;
    this.clock.set(v, nowMs());
    SoundBoard.shared.cancelQueuedClicks();
    this.soundCursor = Math.min(this.soundCursor, this.now);
    this.changed();
  }

  get palette() { return this.level.palette; }
  get boardCount() { return this.match.boards.length; }
  board(i) { return this.match.boards[i].board; }
  capacity(p) { return this.match.players[p].capacity; }
  queue(p, q) { return this.match.players[p].queues[q]; }
  get tunnelCount() { return this.level.tunnels.length; }
  waiting(p) { return this.match.waiting(p); }
  lastFamily(p) { return this.match.players[p].lastFamily; }
  penalties(p) { return this.match.penalties(p); }

  /** Teams of player p whose ants still have tiles to pick up (they hold a slot while working). */
  working(p, t) {
    const b = this.match.boardIndex(p);
    const waitingIDs = new Set(this.match.waiting(p).map(w => w.uid));
    const counts = new Map(), fam = new Map();
    for (const trip of this.schedulers[b].trips) {
      if (Math.floor(trip.team / VersusRules.playerBase) === p && trip.pickupEnd > t) {
        counts.set(trip.team, (counts.get(trip.team) || 0) + 1);
        fam.set(trip.team, trip.family);
      }
    }
    return [...counts.keys()].sort((a, c) => a - c).filter(u => !waitingIDs.has(u)).map(u => ({ uid: u, family: fam.get(u) || 0, left: counts.get(u) || 0 }));
  }

  occupancy(p, t) { return this.match.waiting(p).length + this.working(p, t).length; }

  refusal(p, q, d) {
    if (this.result) return 'The match is over.';
    const r = this.match.refusal(p, q, d);
    if (r) return r;
    if (this.occupied[p] >= this.capacity(p)) return `All ${this.capacity(p)} slots are busy.`;
    return null;
  }

  launch(p, q, d) {
    const t = this.now;
    this.occupied[p] = this.occupancy(p, t);
    const why = this.refusal(p, q, d);
    if (why) {
      this.say(p, why);
      this.refusedTick++;
      SoundBoard.shared.play(Sfx.refused);
      this.changed();
      return;
    }
    const before = this.match.waiting(p).length;
    const team = this.match.players[p].queues[q][d];
    const ev = this.match.launch(p, q, d);
    const b = this.match.boardIndex(p);
    this.schedulers[b].schedule(ev, this.moveCounter, t + 0.04);
    this.moveCounter++;
    this.sendTick++;
    try { if (navigator.vibrate) navigator.vibrate(8); } catch (e) { /* none */ }
    SoundBoard.shared.play(Sfx.send);
    const own = ev.filter(c => c.team === team.uid).length;
    let text = `${paletteName(this.palette, team.family)} team of ${team.quota} sent`;
    if (d > 0) text += ` (jumped ${d}, −${Math.round(d * VersusRules.skipPenalty)})`;
    if (this.match.waiting(p).length > before) {
      text += ` — reached ${own}, waiting for the rest.`;
      SoundBoard.shared.play(Sfx.wait, 0.28);
    } else text += '.';
    this.say(p, text);
    this.refresh(t);
    this.changed();
  }

  addSlot(p) {
    if (this.result) return;
    this.match.addSlot(p);
    SoundBoard.shared.play(Sfx.addSlot);
    this.say(p, `Added a slot (−${Math.round(VersusRules.addSlotPenalty)}).`);
    this.refresh(this.now);
    this.changed();
  }

  returnTeam(p, uid) {
    if (this.result) return;
    this.match.returnTeam(p, uid);
    SoundBoard.shared.play(Sfx.returnTeam);
    this.say(p, `Returned a waiting team (−${Math.round(VersusRules.returnPenalty)}).`);
    this.refresh(this.now);
    this.changed();
  }

  say(p, text) { this.messages[p] = text; this.messageExpiry[p] = nowMs() + 5000; }

  ensureRaster(i, cellPx) {
    const r = this.rasters[i];
    if (r && r.cellPx === cellPx) return r;
    const b = this.match.boards[i].board;
    const t = this.now;
    const open = b.initialOpen();
    const lift = this.schedulers[i].liftTime;
    for (let c = 0; c < b.count; c++) if (b.family[c] >= 0) open[c] = lift[c] <= t ? 1 : 0;
    this.rasters[i] = new MosaicRaster(b, this.palette, cellPx, open, this.groundColor);
    return this.rasters[i];
  }

  tick() {
    const t = this.now;
    const dt = Math.max(0, t - this.lastTick);
    this.lastTick = t;
    if (this.result) return;
    this.rasters.forEach((r, i) => { if (r) r.sync(this.schedulers[i].liftTime, t); });
    for (let p = 0; p < 2; p++) {
      const occ = this.occupancy(p, t);
      if (this.rules.scoring === 'upkeep') this.match.players[p].upkeep += VersusRules.upkeepPerSecond * Math.max(0, occ - 1) * dt;
    }
    this.refresh(t);
    this.pumpSounds(t);
    for (const s of this.schedulers) s.prune(t - 0.5);
    const ms = nowMs();
    for (let p = 0; p < 2; p++) if (this.messages[p] !== null && ms > this.messageExpiry[p]) this.messages[p] = null;
    this.checkEnd(t);
    this.changed();
  }

  refresh(t) {
    const occ = [0, 0], home = [0, 0];
    for (let p = 0; p < 2; p++) occ[p] = this.occupancy(p, t);
    this.match.boards.forEach((vb, i) => {
      const ht = this.schedulers[i].homeTime;
      const b = vb.board;
      for (let c = 0; c < b.count; c++) {
        if (b.family[c] >= 0 && ht[c] <= t) {
          const o = vb.owner[c];
          if (o >= 0 && o < 2) home[o]++;
        }
      }
    });
    this.occupied = occ;
    this.delivered = home;
    this.scores = [home[0] - this.match.penalties(0), home[1] - this.match.penalties(1)];
    this.revision++;
  }

  checkEnd(t) {
    let finisher = null;
    if (this.rules.layout === 'race') {
      for (let p = 0; p < 2; p++) if (this.match.boards[p].isCleared && !this.schedulers[p].isBusy) { finisher = p; break; }
      if (finisher === null) return;
    } else {
      const cleared = this.match.boards[0].isCleared || this.match.isStalemate;
      if (!(cleared && !this.schedulers[0].isBusy)) return;
    }
    this.finish(finisher, t);
  }

  finish(finisher, t) {
    this.refresh(t);
    const lines = [];
    for (let p = 0; p < 2; p++) {
      const pl = this.match.players[p];
      const bonus = finisher === p ? Math.round(VersusRules.finishBonusShare * this.match.tileCount) : 0;
      const upkeep = this.rules.scoring === 'upkeep' ? pl.upkeep : 0;
      const score = this.delivered[p] + bonus - this.match.penalties(p);
      lines.push({ tiles: this.delivered[p], bonus, upkeep, addedSlots: pl.added, returns: pl.returns, skips: pl.skips, score });
    }
    const a = Math.round(lines[0].score), b = Math.round(lines[1].score);
    const winner = a === b ? null : (a > b ? 0 : 1);
    const seconds = (nowMs() - this.startMs) / 1000;
    this.result = { lines, winner, finisher, seconds };
    this.animating = false;
    SoundBoard.shared.play(Sfx.complete);
    if (winner !== null && this.app) {
      this.highScoreRank = this.app.highScoreRank('versus', this.level.id, Math.round(lines[winner].score), seconds);
      if (this.highScoreRank !== null) SoundBoard.shared.play(Sfx.newBest, 2.1);
    }
  }

  get topScores() { return this.app ? this.app.topScores('versus', this.level.id) : []; }

  saveWinnerScore(name) {
    const r = this.result;
    if (!r || r.winner === null || this.highScoreRank === null || this.savedHighScorePlace !== null) return;
    const w = r.winner, other = 1 - w;
    const ru = this.rules;
    const detail = `${versusOptionTitle('layout', ru.layout)} · ${versusOptionTitle('picking', ru.picking)} · ${versusOptionTitle('colour', ru.colour)} · ${versusOptionTitle('scoring', ru.scoring)} · beat ${Math.round(r.lines[other].score)}`;
    const entry = makeHighScoreEntry(name, Math.round(r.lines[w].score), r.seconds, ru.difficulty, [], detail);
    const place = this.app ? this.app.saveHighScore('versus', this.level.id, entry) : 0;
    this.savedHighScorePlace = place == null ? 0 : place;
    this.changed();
  }

  pumpSounds(t) {
    const horizon = t + 0.16 * this.speed;
    const from = Math.max(this.soundCursor, t - 0.3 * this.speed);
    this.soundCursor = Math.max(this.soundCursor, horizon);
    const sb = SoundBoard.shared;
    if (!sb.isOn || !sb.tileClicks || !(horizon > from)) return;
    const pace = Math.max(0.01, this.speed);
    this.schedulers.forEach((s, i) => {
      const b = this.match.boards[i].board;
      const width = Math.max(1, b.cols - 1);
      const side = this.rules.layout === 'race' ? (i === 0 ? -0.5 : 0.5) : 0;
      for (const trip of s.trips) {
        if (trip.arrive > from && trip.arrive <= horizon) {
          const pan = Math.max(-1, Math.min(1, side + ((trip.tile % b.cols) / width * 2 - 1) * 0.4));
          sb.tile(trip.family, pan, Math.max(0, (trip.arrive - t) / pace));
        }
      }
    });
  }
}
