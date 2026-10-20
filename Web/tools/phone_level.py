"""Open one mosaic on a phone-sized page and screenshot it with a few teams out."""
import sys
from playwright.sync_api import sync_playwright
page, out, level, size = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
w, hgt = (int(x) for x in size.split('x'))
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_page(viewport={'width': w, 'height': hgt}, device_scale_factor=2, has_touch=True, is_mobile=True)
    errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto('file://' + page); pg.wait_for_timeout(1200)
    pg.evaluate("""(id) => { const app = window.__tc.app; app.updateSettings(s => { s.unlockAll = true; s.coachSeen = ['tapTeam','watchAnts','chamber','slotsFull','scout','jam','showcaseIntro','photoIntro']; });
      app.play(app.allLevels.find(l => l.id === id), true, 'expert', new Set()); }""", level)
    pg.wait_for_timeout(600)
    for i in range(3):
        cards = pg.locator('.tcol .teamcard:not(.emptyq)')
        cards.nth(i % cards.count()).tap(); pg.wait_for_timeout(300)
    pg.wait_for_timeout(800)
    pg.screenshot(path=out)
    info = pg.evaluate("() => { const r = document.querySelector('.slots').getBoundingClientRect(); return { slotsBottom: Math.round(r.bottom), viewport: innerHeight, board: document.querySelector('.board-wrap').style.width + ' x ' + document.querySelector('.board-wrap').style.height }; }")
    print(level, info, errs)
    b.close()
