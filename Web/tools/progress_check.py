"""Unlock-all button, locked-card dialog, wins settled when leaving early, progress codes, and the
forgets-on-close warning (cross-origin frame + Apple vendor)."""
import sys, json, os, subprocess, time
from playwright.sync_api import sync_playwright
local, out = sys.argv[1], sys.argv[2]
SEEN = "['tapTeam','watchAnts','chamber','slotsFull','scout','jam','showcaseIntro','photoIntro']"
errs = []
def watch(pg):
    pg.on('pageerror', lambda e: errs.append('pageerror: ' + str(e)))
    pg.on('console', lambda m: errs.append(m.text) if m.type == 'error' and 'ERR_TUNNEL' not in m.text else None)

def play_to_logical_win(pg, level='firstDig'):
    pg.evaluate("(id) => { const app = window.__tc.app; app.updateSettings(s => { s.coachSeen = " + SEEN + "; }); app.play(app.allLevels.find(l => l.id === id), true, 'classic', new Set()); }", level)
    return pg.evaluate("""() => new Promise(res => { const c = window.__tc.app.current; const sol = c.level.solution; let k = 0;
      const step = () => { if (c.game.isWon) return res({ won: true, visual: c.visuallyComplete, moves: c.moveCount });
        if (k < sol.length && c.hasOpenSlot && c.game.canDispatch(sol[k])) { c.dispatch(sol[k]); k++; } setTimeout(step, 30); };
      c.setSpeed(16); step(); setTimeout(() => res({ won: false }), 60000); })""")

with sync_playwright() as p:
    b = p.chromium.launch()
    # 1–2: button on Home (phone), persists; locked card dialog
    ctx = b.new_context(viewport={'width': 390, 'height': 670}, device_scale_factor=2, has_touch=True, is_mobile=True)
    pg = ctx.new_page(); watch(pg)
    pg.goto('file://' + local); pg.wait_for_timeout(1200)
    btn = pg.get_by_role('button', name='Unlock all puzzles', exact=True)
    box = btn.bounding_box()
    print('unlock button visible on first screen:', btn.is_visible(), 'top', round(box['y']), 'of', 670)
    pg.screenshot(path=f'{out}/home_unlock_phone.png')
    locked = pg.locator('.ccard.locked').first
    locked.scroll_into_view_if_needed(); locked.tap(); pg.wait_for_timeout(300)
    print('locked dialog:', pg.locator('.dialog').inner_text().replace('\n', ' | '))
    pg.screenshot(path=f'{out}/locked_dialog.png')
    pg.locator('.dialog').get_by_role('button', name='Unlock all puzzles').tap(); pg.wait_for_timeout(400)
    print('after unlock: sheet open =', pg.locator('.sheet').count() == 1, '| unlockAll =', pg.evaluate("() => window.__tc.app.settings.unlockAll"))
    pg.keyboard.press('Escape'); pg.wait_for_timeout(200)
    pg.reload(); pg.wait_for_timeout(1200)
    print('after reload: unlockAll =', pg.evaluate("() => window.__tc.app.settings.unlockAll"), '| card says:', pg.locator('.okc', has_text='All puzzles are unlocked').count() == 1)
    pg.get_by_role('button', name='Lock again').tap(); pg.wait_for_timeout(200)
    print('lock again: unlockAll =', pg.evaluate("() => window.__tc.app.settings.unlockAll"))
    # 3a: leave via Home while the ants still carry tiles
    r = play_to_logical_win(pg)
    pg.evaluate("() => window.__tc.app.current.setSpeed(0.1)")
    pg.evaluate("() => window.__tc.app.goHome()"); pg.wait_for_timeout(300)
    print('left early via Home:', r, '-> progress', pg.evaluate("() => Object.keys(window.__tc.app.progress)"),
          '| koiPond playable', pg.evaluate("() => window.__tc.app.isPlayable(window.__tc.app.allLevels.find(l => l.id === 'koiPond'))"),
          '| save cleared', pg.evaluate("() => window.__tc.app.savedMoves(window.__tc.app.allLevels.find(l => l.id === 'firstDig')) === null"))
    # 3b: close the page mid-carry (reload), win settles at start
    r = play_to_logical_win(pg, 'koiPond')
    pg.evaluate("() => window.__tc.app.current.setSpeed(0.1)")
    pg.reload(); pg.wait_for_timeout(1500)
    print('closed mid-carry:', r, '-> progress', pg.evaluate("() => Object.keys(window.__tc.app.progress)"))
    # 4: progress code out of this browser...
    ctx.grant_permissions(['clipboard-read', 'clipboard-write'])
    pg.get_by_role('button', name='Copy progress code').tap()
    pg.wait_for_function("() => { const d = document.querySelector('.dialog [role=status]'); return d && !/Making|Copying/.test(d.textContent); }", timeout=10000)
    code = pg.locator('#progress-code').input_value()
    print('copy dialog:', pg.locator('.dialog [role=status]').inner_text(), '| code length', len(code), code[:12] + '…')
    clip = pg.evaluate("() => navigator.clipboard.readText().catch(e => 'ERR ' + e)")
    print('clipboard holds the code:', clip == code)
    pg.screenshot(path=f'{out}/copy_code.png')
    pg.get_by_role('button', name='Done').tap()
    ctx.close()
    # ...into a fresh one
    ctx = b.new_context(viewport={'width': 1180, 'height': 820})
    pg = ctx.new_page(); watch(pg)
    pg.goto('file://' + local); pg.wait_for_timeout(1200)
    print('fresh browser progress:', pg.evaluate("() => Object.keys(window.__tc.app.progress)"))
    pg.get_by_role('button', name='Paste a code').click()
    pg.fill('#paste-code', 'nonsense'); pg.get_by_role('button', name='Load progress').click(); pg.wait_for_timeout(300)
    print('bad code error:', pg.locator('.dialog [role=alert]').inner_text())
    pg.fill('#paste-code', '  here you go:\n' + code[:40] + '\n' + code[40:] + '  ')
    pg.get_by_role('button', name='Load progress').click(); pg.wait_for_timeout(600)
    print('loaded dialog:', pg.locator('.dialog').inner_text().replace('\n', ' | '))
    print('fresh browser progress now:', pg.evaluate("() => Object.keys(window.__tc.app.progress)"))
    pg.get_by_role('button', name='OK').click()
    pg.screenshot(path=f'{out}/home_unlock_ipad.png')
    ctx.close()
    # 5: cross-origin frame with Apple's vendor string -> warning
    srv = subprocess.Popen([sys.executable, '-m', 'http.server', '8765', '--bind', '127.0.0.1', '--directory', os.path.dirname(local)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)
    try:
        ctx = b.new_context(viewport={'width': 390, 'height': 700})
        ctx.add_init_script("Object.defineProperty(Navigator.prototype, 'vendor', { get: () => 'Apple Computer, Inc.' });")
        pg = ctx.new_page(); watch(pg)
        pg.set_content(f'<body style="margin:0"><iframe src="http://127.0.0.1:8765/{os.path.basename(local)}" style="border:0;width:100vw;height:100vh"></iframe></body>')
        pg.wait_for_timeout(2500)
        fr = pg.frames[1]
        print('framed + Apple vendor -> forgets:', fr.evaluate("() => window.__tc.app.storageForgets"))
        print('warning:', fr.locator('.card.col .brass span.grow').first.inner_text()[:120])
        pg.screenshot(path=f'{out}/home_forgets_warning.png')
        ctx.close()
        ctx = b.new_context(viewport={'width': 390, 'height': 700})
        pg = ctx.new_page(); watch(pg)
        pg.set_content(f'<body style="margin:0"><iframe src="http://127.0.0.1:8765/{os.path.basename(local)}" style="border:0;width:100vw;height:100vh"></iframe></body>')
        pg.wait_for_timeout(2500)
        print('framed + Chrome vendor -> forgets:', pg.frames[1].evaluate("() => window.__tc.app.storageForgets"))
        ctx.close()
    finally:
        srv.terminate()
    b.close()
print('ERRORS:' if errs else 'no errors'); [print(' ', e[:300]) for e in errs[:10]]
