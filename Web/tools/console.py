import sys
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_page(viewport={'width': 1180, 'height': 820})
    msgs = []
    pg.on('console', lambda m: msgs.append(f'{m.type}: {m.text}'))
    pg.on('pageerror', lambda e: msgs.append(f'pageerror: {e}\n{getattr(e, "stack", "")}'))
    pg.goto('file://' + sys.argv[1])
    pg.wait_for_timeout(int(sys.argv[2]) if len(sys.argv) > 2 else 1500)
    for m in msgs[:20]: print(m[:1500])
    print('app text:', pg.locator('#app').inner_text()[:300].replace('\n', ' | '))
    b.close()
