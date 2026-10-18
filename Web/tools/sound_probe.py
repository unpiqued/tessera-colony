import sys, json
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(headless=True, args=['--autoplay-policy=user-gesture-required'])
    pg = b.new_page(viewport={'width': 390, 'height': 700}, has_touch=True, is_mobile=True)
    msgs = []
    pg.on('console', lambda m: msgs.append(f'{m.type}: {m.text}'))
    pg.on('pageerror', lambda e: msgs.append(f'pageerror: {e}'))
    pg.goto('file://' + sys.argv[1])
    pg.wait_for_timeout(1500)
    st = lambda: pg.evaluate("() => { const sb = window.__tc.SoundBoard.shared; const s = sb.status(); return { ctx: sb.context ? sb.context.state : null, ready: sb.soundsReady, isOn: sb.isOn, started: sb.startedCount, err: sb.lastError, settings: { on: window.__tc.app.settings.soundOn, vol: window.__tc.app.settings.soundVolume } }; }")
    print('before tap', st())
    pg.tap('text=Play…')
    pg.wait_for_timeout(600)
    print('after tap ', st())
    pg.locator('.sheet-foot .pill.prominent').first.tap()
    pg.wait_for_timeout(1000)
    if pg.locator('.coach').count(): pg.get_by_role('button', name='Got it').tap()
    pg.locator('.tcol .teamcard').first.tap()
    pg.wait_for_timeout(1500)
    print('after send', st())
    for m in msgs: print(m[:300])
    b.close()
