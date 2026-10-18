"""Smoke test of the built page in Chromium at iPad size: Home renders, a game starts, teams can be
sent, ants move, no console errors. Screenshots go to test-output/."""
import sys, time, json
from playwright.sync_api import sync_playwright

page_path = sys.argv[1]
out = sys.argv[2]
w, h = (int(x) for x in (sys.argv[3] if len(sys.argv) > 3 else '1180x820').split('x'))
errors = []
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    ctx = b.new_context(viewport={'width': w, 'height': h}, device_scale_factor=2, has_touch=True)
    pg = ctx.new_page()
    pg.on('console', lambda m: errors.append(f'{m.type}: {m.text}') if m.type in ('error', 'warning') else None)
    pg.on('pageerror', lambda e: errors.append(f'pageerror: {e}'))
    pg.goto('file://' + page_path)
    pg.wait_for_timeout(1500)
    pg.screenshot(path=f'{out}/home.png')
    pg.screenshot(path=f'{out}/home_full.png', full_page=False)
    # open Next up → start sheet → Start
    pg.get_by_role('button', name='Play…').first.click()
    pg.wait_for_timeout(400)
    pg.screenshot(path=f'{out}/start_sheet.png')
    pg.locator('.sheet-foot .pill.prominent').first.click()
    pg.wait_for_timeout(800)
    pg.screenshot(path=f'{out}/game_start.png')
    # dismiss coach, send teams in tunnel order from the designed solution
    if pg.locator('.coach').count():
        pg.get_by_role('button', name='Got it').click()
    sent = 0
    for i in range(6):
        cards = pg.locator('.tcol .teamcard:not(.emptyq)')
        n = cards.count()
        if n == 0: break
        cards.nth(i % n).dispatch_event('pointerdown', {'button': 0, 'clientX': 0, 'clientY': 0})
        cards.nth(i % n).dispatch_event('pointerup', {'button': 0})
        sent += 1
        pg.wait_for_timeout(250)
    pg.wait_for_timeout(1500)
    pg.screenshot(path=f'{out}/game_ants.png')
    stats = pg.evaluate("""() => new Promise(res => {
      const times = []; let last = performance.now(); let n = 0;
      function f(t) { times.push(t - last); last = t; if (++n < 120) requestAnimationFrame(f); else res(times); }
      requestAnimationFrame(f);
    })""")
    stats = sorted(stats[5:])
    print(json.dumps({'sent': sent, 'frame_ms_median': round(stats[len(stats)//2], 2), 'frame_ms_p95': round(stats[int(len(stats)*0.95)], 2)}))
    print('panel text:', pg.locator('.cpanel').inner_text()[:400].replace('\n', ' | '))
    b.close()
print('ERRORS:' if errors else 'no console errors')
for e in errors[:30]: print(' ', e)
