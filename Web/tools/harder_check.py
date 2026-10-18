import sys
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_page(viewport={'width': 1180, 'height': 820})
    errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto('file://' + sys.argv[1]); pg.wait_for_timeout(1200)
    r = pg.evaluate("""async () => {
      const app = window.__tc.app;
      const lv = app.allLevels.find(l => l.id === 'firstDig');
      app.play(lv, true, 'classic', new Set());
      await new Promise(r => setTimeout(r, 400));
      const first = app.current;
      const c1 = first.boardCanvas;
      app.play(lv, true, 'expert', new Set());     // what "Try it on Expert" does
      await new Promise(r => setTimeout(r, 400));
      const second = app.current;
      return { sameController: first === second, newCanvas: !!second.boardCanvas && second.boardCanvas !== c1,
               boundTo: second.boardCanvas && second.boardCanvas.source === second,
               canvases: document.querySelectorAll('.board-wrap canvas').length, difficulty: second.difficulty };
    }""")
    print(r, errs)
    b.close()
