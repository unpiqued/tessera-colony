"""iPhone-style audio check (UA + a stand-in navigator.audioSession): by default the game mixes
('ambient', no silent <audio> track); sound off releases audio and taps start nothing; the Home,
in-game and two-player sound buttons; Silent-mode playback only when mixing is switched off."""
import sys, json
from playwright.sync_api import sync_playwright
page = sys.argv[1]
IPHONE = 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/129.0 Mobile/15E148 Safari/604.1'
INIT = """
window.__sessionTypes = [];
const session = { _t: 'auto', get type() { return this._t; }, set type(v) { this._t = v; window.__sessionTypes.push(v); } };
Object.defineProperty(Navigator.prototype, 'audioSession', { get: () => session, configurable: true });
const realPlay = HTMLMediaElement.prototype.play;
window.__mediaPlays = 0;
HTMLMediaElement.prototype.play = function () { window.__mediaPlays++; return realPlay.call(this); };
"""
STATE = """() => { const sb = window.__tc.SoundBoard.shared; const c = sb.context;
  return { soundOn: window.__tc.app.settings.soundOn, mix: window.__tc.app.settings.mixWithOtherAudio, session: navigator.audioSession.type,
    ctx: c ? c.state : null, keepAlive: sb.keepAliveActive, mediaPlays: window.__mediaPlays, started: sb.startedCount }; }"""
errs = []
with sync_playwright() as p:
    b = p.chromium.launch(args=['--autoplay-policy=user-gesture-required'])
    ctx = b.new_context(viewport={'width': 390, 'height': 700}, user_agent=IPHONE, has_touch=True, is_mobile=True, device_scale_factor=2)
    ctx.add_init_script(INIT)
    pg = ctx.new_page()
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto('file://' + page); pg.wait_for_timeout(1200)
    st = lambda: pg.evaluate(STATE)
    print('loaded, before any tap      ', json.dumps(st()))
    pg.locator('.lede').tap(); pg.wait_for_timeout(400)
    print('after a tap (defaults)      ', json.dumps(st()))
    played = pg.evaluate("() => window.__tc.SoundBoard.shared.playTestSound()")
    pg.wait_for_timeout(300)
    print('test chime played:', played, '| started', st()['started'])
    home_btn = pg.locator('header button[aria-pressed]')
    home_btn.tap(); pg.wait_for_timeout(400)
    s = st(); print('Home speaker -> off         ', json.dumps(s))
    for _ in range(3): pg.locator('.lede').tap(); pg.wait_for_timeout(100)
    print('three taps while off        ', json.dumps(st()), '| label:', home_btn.get_attribute('aria-label'))
    home_btn.tap(); pg.wait_for_timeout(400)
    print('Home speaker -> on          ', json.dumps(st()))
    # Silent-mode playback is opt-in
    pg.locator('header button[aria-label="Settings"]').tap(); pg.wait_for_timeout(300)
    mix = pg.locator('#set-mix'); mix.scroll_into_view_if_needed()
    print('settings row:', pg.locator('label[for="set-mix"]').inner_text().replace('\n', ' | '))
    mix.tap(); pg.wait_for_timeout(200); pg.locator('.sheet-bar .textbtn').tap(); pg.wait_for_timeout(200)
    pg.locator('.lede').tap(); pg.wait_for_timeout(400)
    print('mixing off, then a tap      ', json.dumps(st()))
    pg.locator('header button[aria-label="Settings"]').tap(); pg.wait_for_timeout(300)
    pg.locator('#set-mix').tap(); pg.wait_for_timeout(200)
    print('mixing back on              ', json.dumps(st()))
    pg.locator('.sheet-bar .textbtn').tap(); pg.wait_for_timeout(200)
    pg.locator('.lede').tap(); pg.wait_for_timeout(300)
    print('  ...then a tap             ', json.dumps(st()))
    # in a game: the menu's Sound effects switch
    pg.evaluate("() => { const app = window.__tc.app; app.updateSettings(s => { s.coachSeen = ['tapTeam','watchAnts','chamber','slotsFull','scout','jam','showcaseIntro','photoIntro']; }); app.play(app.allLevels.find(l => l.id === 'firstDig'), true, 'classic', new Set()); }")
    pg.wait_for_timeout(500)
    pg.locator('.tcol .teamcard:not(.emptyq)').first.tap(); pg.wait_for_timeout(400)
    print('in game, team sent          ', json.dumps(st()))
    pg.locator('button[aria-label="Menu"]').tap(); pg.wait_for_timeout(200)
    pg.locator('label.mi', has_text='Sound effects').tap(); pg.wait_for_timeout(300)
    print('menu: Sound effects off     ', json.dumps(st()))
    pg.keyboard.press('Escape'); pg.wait_for_timeout(100)
    for _ in range(2): pg.locator('.tcol .teamcard:not(.emptyq)').first.tap(); pg.wait_for_timeout(300)
    print('two more sends while off    ', json.dumps(st()))
    pg.evaluate("() => window.__tc.app.goHome()"); pg.wait_for_timeout(300)
    # two players: top-bar speaker
    pg.evaluate("() => { const app = window.__tc.app; app.startVersus(app.allLevels.find(l => l.id === 'firstDig'), { layout: 'race', picking: 'reach3', colour: 'any', scoring: 'upkeep', difficulty: 'classic' }); }")
    pg.wait_for_timeout(500)
    vbtn = pg.locator('.game button[aria-pressed]')
    print('two players, button says:', vbtn.get_attribute('aria-label'))
    vbtn.tap(); pg.wait_for_timeout(400)
    print('two players: sound on       ', json.dumps(st()))
    vbtn.tap(); pg.wait_for_timeout(400)
    print('two players: sound off      ', json.dumps(st()))
    pg.reload(); pg.wait_for_timeout(1200)
    pg.locator('.lede').tap() if pg.locator('.lede').count() else None; pg.wait_for_timeout(300)
    print('reloaded with sound off     ', json.dumps(st()), '| session types set so far:', pg.evaluate("() => window.__sessionTypes"))
    b.close()
print('page errors:', errs or 'none')
