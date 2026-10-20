"""Two-player layout at phone and iPad sizes: board sizes, anything off screen, page errors."""
import sys, json
from playwright.sync_api import sync_playwright
page, out = sys.argv[1], sys.argv[2]
levels = sys.argv[3].split(',') if len(sys.argv) > 3 else ['firstDig']
with sync_playwright() as p:
    b = p.chromium.launch()
    for level in levels:
        for (w, hgt) in [(390, 670), (375, 560), (844, 390), (820, 1180), (1180, 820)]:
            for layout in ['race', 'shared']:
                phone = w < 900 and hgt < 900
                pg = b.new_page(viewport={'width': w, 'height': hgt}, device_scale_factor=2 if phone else 1, has_touch=True, is_mobile=phone)
                errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
                pg.goto('file://' + page); pg.wait_for_timeout(1000)
                pg.evaluate("""([layout, id]) => { const app = window.__tc.app; app.startVersus(app.allLevels.find(l => l.id === id), { layout, picking: 'reach3', colour: 'any', scoring: 'upkeep', difficulty: 'classic' }); }""", [layout, level])
                pg.wait_for_timeout(500)
                # launch one team each so slots and messages are in play
                pg.evaluate("() => { const v = window.__tc.app.versus; v.launch(0, 0, 0); v.launch(1, 1, 0); }"); pg.wait_for_timeout(400)
                info = pg.evaluate("""() => ({
                  boards: [...document.querySelectorAll('.vboard .board-wrap')].map(e => e.style.width.replace('px','') + 'x' + e.style.height.replace('px','')),
                  offscreen: [...document.querySelectorAll('.teamcard, .pod.add, .pod')].filter(e => { const r = e.getBoundingClientRect(); return r.bottom > innerHeight + 1 || r.right > innerWidth + 1 || r.top < -1; }).length,
                  hscroll: document.scrollingElement.scrollWidth > innerWidth })""")
                print(f'{level:10} {w}x{hgt} {layout:6}', json.dumps(info), errs[:2])
                pg.screenshot(path=f'{out}/vs_{w}x{hgt}_{layout}_{level}.png')
                pg.close()
    b.close()
