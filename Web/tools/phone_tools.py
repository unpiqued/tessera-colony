"""Phone check: header Undo/Hint, slots and a floating hint card all inside the viewport on tall mosaics."""
import sys, json
from playwright.sync_api import sync_playwright
page, out = sys.argv[1], sys.argv[2]
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    for (w, hgt) in [(390, 670), (375, 560)]:
        pg = b.new_page(viewport={'width': w, 'height': hgt}, device_scale_factor=2, has_touch=True, is_mobile=True)
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.on('console', lambda m: errs.append(m.text) if m.type == 'error' and 'ERR_TUNNEL' not in m.text else None)
        pg.goto('file://' + page); pg.wait_for_timeout(1200)
        for level in ['sunflower', 'craftCarpet', 'galleryMonaLisa', 'firstDig']:
            ok = pg.evaluate("""(id) => { const app = window.__tc.app; app.updateSettings(s => { s.unlockAll = true; s.coachSeen = ['tapTeam','watchAnts','chamber','slotsFull','scout','jam','showcaseIntro','photoIntro']; });
              const l = app.allLevels.find(l => l.id === id); if (!l) return false; app.play(l, true, 'classic', new Set()); return true; }""", level)
            if not ok: print('missing level', level); continue
            pg.wait_for_timeout(500)
            cards = pg.locator('.tcol .teamcard:not(.emptyq)')
            cards.nth(0).tap(); pg.wait_for_timeout(250)
            pg.locator('.hdr-tool[aria-label="Hint"]').tap()
            pg.wait_for_function("() => !window.__tc.app.current.hintBusy && window.__tc.app.current.hint", timeout=20000)
            pg.wait_for_timeout(300)
            info = pg.evaluate("""() => { const R = s => { const e = document.querySelector(s); if (!e) return null; const r = e.getBoundingClientRect(); return [Math.round(r.top), Math.round(r.bottom)]; };
              return { vh: innerHeight, board: document.querySelector('.board-wrap').style.width + 'x' + document.querySelector('.board-wrap').style.height,
                undo: R('.hdr-tool[aria-label^="Undo"]'), hint: R('.hdr-tool[aria-label="Hint"]'), slots: R('.slots'), msg: R('.msgcard.float'),
                title: document.querySelector('.lvl-title').scrollWidth > document.querySelector('.lvl-title').clientWidth ? 'ellipsized' : 'fits' }; }""")
            print(f'{w}x{hgt}', level, json.dumps(info))
            pg.screenshot(path=f'{out}/phone_{w}_{level}.png')
            # Do it from the floating card, then undo from the header
            pg.locator('.msgcard.float button', has_text='Do it').tap(); pg.wait_for_timeout(300)
            before = pg.evaluate("() => window.__tc.app.current.moveCount")
            pg.locator('.hdr-tool[aria-label^="Undo"]').tap(); pg.wait_for_timeout(300)
            after = pg.evaluate("() => window.__tc.app.current.moveCount")
            print('   do-it then undo: moves', before, '->', after, '| floating card gone:', pg.locator('.msgcard.float').count() == 0)
            pg.evaluate("() => window.__tc.app.goHome()"); pg.wait_for_timeout(300)
        print('errors:', errs[:5] or 'none')
        pg.close()
    b.close()
