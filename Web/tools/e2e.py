"""End-to-end play-throughs in Chromium: finish First Dig with the designed solution (win card, score,
high-score name, progress, Home), then a full two-player race."""
import sys, json, time
from playwright.sync_api import sync_playwright
page, out = sys.argv[1], sys.argv[2]
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_page(viewport={'width': 1180, 'height': 820}, device_scale_factor=1)
    errs = []
    pg.on('pageerror', lambda e: errs.append('pageerror: ' + str(e)))
    pg.on('console', lambda m: errs.append(f'{m.type}: {m.text}') if m.type == 'error' and 'ERR_TUNNEL' not in m.text else None)
    pg.goto('file://' + page); pg.wait_for_timeout(1200)
    # --- solo: play the designed solution at 16x
    pg.evaluate("""() => { const app = window.__tc.app;
      app.updateSettings(s => { s.coachSeen = ['tapTeam','watchAnts','chamber','slotsFull','scout','jam','showcaseIntro','photoIntro']; });
      app.play(app.allLevels.find(l => l.id === 'firstDig'), true, 'classic', new Set()); app.current.setSpeed(16); }""")
    t0 = time.time()
    res = pg.evaluate("""() => new Promise(resolve => {
      const c = window.__tc.app.current; const sol = c.level.solution; let k = 0; let refused = 0;
      const step = () => {
        if (c.visuallyComplete) return resolve({ done: true, moves: c.moveCount, refused, elapsed: c.elapsed, score: c.scoreBreakdown && c.scoreBreakdown.score, rank: c.highScoreRank, news: c.completionNews });
        if (k < sol.length && c.hasOpenSlot && c.game.canDispatch(sol[k])) { c.dispatch(sol[k]); k++; }
        setTimeout(step, 60);
      };
      step();
      setTimeout(() => resolve({ done: false, k, moves: c.moveCount, cleared: c.claimedCount, delivered: c.deliveredCount }), 120000);
    })""")
    print('solo:', json.dumps(res), f'{time.time()-t0:.1f}s')
    pg.wait_for_timeout(500)
    pg.screenshot(path=f'{out}/e2e_win.png')
    win_text = pg.locator('.win').inner_text() if pg.locator('.win').count() else ''
    print('win card:', win_text.replace('\n', ' | ')[:500])
    if pg.locator('#hs-name').count():
        pg.fill('#hs-name', 'Tester')
        pg.locator('.win form button').click()
        pg.wait_for_timeout(300)
        print('after save:', pg.locator('.scorebox').inner_text().replace('\n', ' | ')[:300])
    pg.get_by_role('button', name='Next mosaic').click() if pg.get_by_role('button', name='Next mosaic').count() else None
    pg.wait_for_timeout(500)
    print('next level opened:', pg.evaluate("() => window.__tc.app.current && window.__tc.app.current.level.id"))
    pg.evaluate("() => window.__tc.app.goHome()"); pg.wait_for_timeout(600)
    home = pg.evaluate("""() => { const app = window.__tc.app; return { progress: Object.keys(app.progress), stars: app.stars('firstDig'),
      top: app.topScores('solo','firstDig').map(e => [e.name, e.score]), found: app.packProgress(app.allLevels).found }; }""")
    print('home state:', json.dumps(home))
    print('gallery:', pg.locator('.gallery').inner_text().replace('\n', ' | ')[:200] if pg.locator('.gallery').count() else 'none')
    # --- reload: progress persisted in localStorage?
    pg.reload(); pg.wait_for_timeout(1200)
    print('after reload:', pg.evaluate("() => ({ progress: Object.keys(window.__tc.app.progress), top: window.__tc.app.topScores('solo','firstDig').length })"))
    # --- two players: race on First Dig at 16x, each launches its front teams when it can
    pg.evaluate("""() => { const app = window.__tc.app; app.startVersus(app.allLevels.find(l => l.id === 'firstDig'), { layout: 'race', picking: 'reach3', colour: 'any', scoring: 'upkeep', difficulty: 'classic' }); app.versus.setSpeed(16); }""")
    pg.wait_for_timeout(500)
    pg.screenshot(path=f'{out}/e2e_versus.png')
    vres = pg.evaluate("""() => new Promise(resolve => {
      // each player follows the designed solution on its own board; player 1 starts 3 moves late
      const v = window.__tc.app.versus; const sol = window.__tc.app.current ? [] : v.level.solution;
      const k = [0, -3]; let launches = 0, refused = 0;
      const step = () => {
        if (v.result) return resolve({ done: true, launches, refused, winner: v.result.winner, finisher: v.result.finisher, lines: v.result.lines.map(l => Math.round(l.score)), rank: v.highScoreRank });
        for (const p of [0, 1]) {
          if (k[p] < 0) { k[p]++; continue; }
          if (k[p] >= sol.length) continue;
          const q = sol[k[p]];
          if (q >= 100) { k[p]++; continue; }
          if (!v.refusal(p, q, 0)) { v.launch(p, q, 0); launches++; k[p]++; } else refused++;
        }
        setTimeout(step, 150);
      };
      step();
      setTimeout(() => resolve({ done: false, launches, k, delivered: v.delivered, waiting: [v.waiting(0).length, v.waiting(1).length] }), 150000);
    })""")
    print('versus:', json.dumps(vres))
    pg.wait_for_timeout(400)
    pg.screenshot(path=f'{out}/e2e_versus_result.png')
    print('result card:', pg.locator('.win').inner_text().replace('\n', ' | ')[:300] if pg.locator('.win').count() else 'none')
    pg.evaluate("() => window.__tc.app.endVersus()"); pg.wait_for_timeout(300)
    print('back home:', pg.evaluate("() => !window.__tc.app.versus && !window.__tc.app.current"))
    b.close()
print('ERRORS:' if errs else 'no errors'); [print(' ', e[:300]) for e in errs[:20]]
