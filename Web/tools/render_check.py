"""Browser check of the board renderer (BoardCanvas) with headless Chromium (Python Playwright).

    python3 tools/render_check.py            (from Web/; writes test-output/*.png and test-output/render_perf.json)

Serves Web/ on 127.0.0.1, opens tools/render_harness.html at iPad size (1180x820 CSS px, device scale 2),
plays the designed solution's first moves, takes screenshots, and measures frame times on the 6,048-tile
"sunflower" showcase with a few hundred ants walking (detailed legs on and off).
"""
import functools
import http.server
import json
import pathlib
import platform
import subprocess
import sys
import threading
import time

from playwright.sync_api import sync_playwright

WEB = pathlib.Path(__file__).resolve().parents[1]
OUT = WEB / "test-output"


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


def serve():
    handler = functools.partial(QuietHandler, directory=str(WEB))
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def cpu_info():
    model = "?"
    try:
        for line in open("/proc/cpuinfo"):
            if line.startswith("model name"):
                model = line.split(":", 1)[1].strip()
                break
    except OSError:
        pass
    nproc = subprocess.run(["nproc"], capture_output=True, text=True).stdout.strip()
    return {"model": model, "nproc": nproc, "platform": platform.platform()}


def main():
    OUT.mkdir(exist_ok=True)
    srv = serve()
    url = "http://127.0.0.1:%d/tools/render_harness.html" % srv.server_address[1]
    report = {"cpu": cpu_info()}
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1180, "height": 820}, device_scale_factor=2)
        page = ctx.new_page()
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(url)
        page.wait_for_function("window.harnessReady === true", timeout=20000)
        report["userAgent"] = page.evaluate("navigator.userAgent")
        report["webgl"] = page.evaluate("harness.webgl()")

        # 1. First Dig: the designed solution's first moves, sent as slots open (as a player would).
        report["firstDig"] = page.evaluate("harness.load('firstDig', {style: 'randomTeam'})")
        page.screenshot(path=str(OUT / "first_dig_start.png"))
        page.evaluate("harness.autoSend(5)")
        time.sleep(4.0)
        page.screenshot(path=str(OUT / "first_dig_4s.png"))
        time.sleep(5.0)
        report["firstDig_9s"] = page.evaluate("harness.info()")
        page.screenshot(path=str(OUT / "first_dig_9s.png"))
        page.evaluate("harness.setZoom(3.2, 0, -330)")
        time.sleep(0.4)
        page.screenshot(path=str(OUT / "first_dig_zoom.png"))
        page.evaluate("harness.setZoom(1)")
        page.evaluate("harness.scout(1)")
        time.sleep(0.3)
        page.screenshot(path=str(OUT / "first_dig_scout.png"))
        page.evaluate("harness.endScout(); harness.setBlocked(true)")
        time.sleep(0.2)
        page.screenshot(path=str(OUT / "first_dig_blocked.png"))

        # 2. Koi Pond with scout trails.
        page.evaluate("harness.load('koiPond', {style: 'scout'})")
        page.evaluate("harness.autoSend(3)")
        time.sleep(6.0)
        page.screenshot(path=str(OUT / "koi_pond_scout.png"))

        # 2b. Two-player shared board (VersusBoardCanvas): two hills with player rings, owner rings on ants.
        page.evaluate("harness.versus('koiPond', 4)")
        time.sleep(6.0)
        page.screenshot(path=str(OUT / "versus_shared.png"))

        # 3. Sunflower (6,048 tiles), resumed half-way so routes are long: send 12 teams at once and let
        #    the hole release ants until as many walk as the game allows (one ant per 0.18 s).
        report["sunflower"] = page.evaluate("harness.load('sunflower', {style: 'randomTeam', capacity: 14, restore: 30})")
        page.evaluate("harness.sendNow(12, true)")
        page.evaluate("harness.setSpeed(6)")

        def wait_visible(target, limit):
            t0 = time.time()
            best = 0
            while time.time() - t0 < limit:
                v = page.evaluate("harness.info()")["visible"]
                best = max(best, v)
                if v >= target:
                    break
                time.sleep(0.25)
            return best

        report["sunflower_peak_visible"] = wait_visible(10_000, 9.0)
        page.evaluate("harness.setSpeed(1)")
        report["sunflower_busy"] = page.evaluate("harness.info()")
        perf = {}
        page.evaluate("harness.setDetailed(true)")
        perf["game_busiest_detailed_on"] = page.evaluate("harness.measure(5000)")
        page.screenshot(path=str(OUT / "sunflower_busy.png"))
        page.evaluate("harness.setDetailed(false)")
        perf["game_busiest_detailed_off"] = page.evaluate("harness.measure(5000)")
        page.evaluate("harness.setDetailed(true)")
        # Stress: a second colony's ants drawn on the same board (not a game state) to reach ~300.
        page.evaluate("harness.addColony(14, 5, 'randomAnt')")
        page.evaluate("harness.setSpeed(6)")
        wait_visible(300, 10.0)
        page.evaluate("harness.setSpeed(0.5)")
        perf["stress_300_detailed_on"] = page.evaluate("harness.measure(5000)")
        page.screenshot(path=str(OUT / "sunflower_stress.png"))
        page.evaluate("harness.setDetailed(false)")
        perf["stress_300_detailed_off"] = page.evaluate("harness.measure(5000)")
        page.evaluate("harness.setDetailed(true)")
        page.evaluate("harness.setZoom(2.5, 0, -600)")
        perf["stress_zoom_2_5x_detailed"] = page.evaluate("harness.measure(4000)")
        page.screenshot(path=str(OUT / "sunflower_zoom.png"))
        page.evaluate("harness.setZoom(1)")
        perf["stress_drawLoop_detailed"] = page.evaluate("harness.drawLoop(120, false)")
        perf["stress_drawLoop_detailed_flush"] = page.evaluate("harness.drawLoop(60, true)")
        page.evaluate("harness.setSpeed(6)")
        wait_visible(10_000, 6.0)
        page.evaluate("harness.setSpeed(0.5)")
        perf["stress_over_320_detailed_setting_on"] = page.evaluate("harness.measure(4000)")
        report["perf"] = perf
        report["sunflower_end"] = page.evaluate("harness.info()")
        report["miniature"] = page.evaluate("harness.miniatureCheck()")
        browser.close()
    srv.shutdown()
    report["errors"] = errors
    (OUT / "render_perf.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
