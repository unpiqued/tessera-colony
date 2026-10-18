#!/usr/bin/env python3
"""Browser check of the builder worker (Chromium via Playwright; run: python3 test/browser_builders.py).

Builds a throwaway page with tools/build_with_worker.mjs in a temporary copy of Web/ (stub main.js
and page.html that only expose the builder API), then in Chromium:
  * runs pattern / photo / probe jobs in the blob: Worker, top-level and inside a sandboxed iframe
    (allow-scripts only, like the artifact) and compares them with test/fixtures/builders.json;
  * measures the longest main-thread stall while the largest photo level builds + probes in the
    worker, and while the same job runs on the main thread (the fallback);
  * checks the fallbacks: no embedded source, a worker script that fails to start;
  * checks pixelsFromImage (white under transparent pixels, targetSize scaling).
Prints a JSON summary; exits non-zero on failure.
"""
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

from playwright.sync_api import sync_playwright

WEB = pathlib.Path(__file__).resolve().parent.parent
FIX = json.loads((WEB / "test" / "fixtures" / "builders.json").read_text())

MAIN_JS = """\
import { createBuilder, runBuild, BuilderClient, builderWorkerSource } from './builders/builderWorker.js';
import { PatternLevelBuilder } from './builders/patternLevelBuilder.js';
import { PhotoLevelBuilder, pixelsFromImage, targetSize } from './builders/photoLevelBuilder.js';
window.__tc = { createBuilder, runBuild, BuilderClient, builderWorkerSource, PatternLevelBuilder, PhotoLevelBuilder,
  pixelsFromImage, targetSize };
"""
PAGE_HTML = """<!doctype html><html><head><meta charset="utf-8"><style>/*STYLE*/</style></head>
<body><!--DATA--><script>/*SCRIPT*/</script></body></html>"""
FRAME_HTML = """<!doctype html><html><body>
<iframe id="f" sandbox="allow-scripts" src="https://tc.test/page.html" width="300" height="200"></iframe>
</body></html>"""

# Runs in the page; returns JSON-safe results.
JOBS_JS = """
async ([want4, wantFlower]) => {
  const T = window.__tc;
  const strip = v => JSON.parse(JSON.stringify(v, (k, x) => typeof x === 'bigint' ? x.toString() + 'n' : x));
  const out = {};
  const b = T.createBuilder();
  out.modeAtStart = b.mode;
  const p = await b.run('pattern', { seed: 4n, number: 7, probe: true });
  out.modeAfter = b.mode;
  out.patternMatches = JSON.stringify(p.level.art) === JSON.stringify(want4.level.art)
    && JSON.stringify(p.level.tunnels) === JSON.stringify(want4.level.tunnels)
    && JSON.stringify(p.level.solution) === JSON.stringify(want4.level.solution)
    && p.level.id === want4.level.id && p.level.subtitle === want4.level.subtitle;
  out.patternHashIsBigInt = typeof p.level.goldenClaimsHash === 'bigint';
  out.patternStats = p.stats;
  out.patternStatsMatch = JSON.stringify(p.stats) === JSON.stringify(want4.probe);
  // the SelfTest flower, drawn here with the same formula as tools/make_builder_fixtures.py
  const w = 300, h = 400, px = new Uint8ClampedArray(w * h * 4).fill(250);
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    const dx = x - 150, dy = y - 150, r = Math.sqrt(dx * dx + dy * dy), a = Math.atan2(dy, dx);
    const petal = 70 + 22 * Math.cos(5 * a), ex = (x - 110) / 40, ey = (y - 290) / 15, o = (y * w + x) * 4;
    let c = null;
    if (r < 32) c = [245, 196, 40]; else if (r < petal) c = [220, 50, 100];
    else if (Math.abs(x - 150) < 7 && y > 200 && y < 380) c = [60, 140, 60];
    else if (ex * ex + ey * ey < 1) c = [70, 160, 70];
    if (c) { px[o] = c[0]; px[o + 1] = c[1]; px[o + 2] = c[2]; }
    px[o + 3] = 255;
  }
  const f = await b.run('photo', { image: { width: w, height: h, data: px }, detail: 'fine', seed: 7n,
    id: 'photo-flower-fine-7', title: 'Photo mosaic 3', probe: true });
  out.photoKind = f.result.kind;
  out.photoMatches = f.result.kind === 'success'
    && JSON.stringify(f.result.value.art) === JSON.stringify(wantFlower.level.art)
    && JSON.stringify(f.result.value.palette) === JSON.stringify(wantFlower.level.palette)
    && JSON.stringify(f.result.value.tunnels) === JSON.stringify(wantFlower.level.tunnels);
  out.photoStatsMatch = JSON.stringify(f.stats) === JSON.stringify(wantFlower.probe);
  const pr = await b.run('probe', { level: { ...p.level, notCloneable: () => 0 } });
  out.probeJobMatches = JSON.stringify(pr.stats) === JSON.stringify(want4.probe);
  try { await b.run('nope', {}); out.badJobRejected = false; } catch (e) { out.badJobRejected = /unknown build kind/.test(e.message); }
  b.terminate();
  return strip(out);
}
"""

STALL_JS = """
async (useWorker) => {
  const T = window.__tc;
  // a 720x720 colourful, noisy picture: the largest grid (77 x 78 tiles at Very fine)
  const w = 720, h = 720, px = new Uint8ClampedArray(w * h * 4);
  let s = 12345;
  const rnd = () => (s = (Math.imul(s, 1103515245) + 12345) >>> 0) / 4294967296;
  const discs = Array.from({ length: 60 }, (_, i) => [rnd() * w, rnd() * h, 20 + rnd() * 70, i % 6]);
  const cols = [[230, 60, 90], [250, 190, 40], [90, 60, 200], [240, 120, 30], [60, 170, 210], [180, 40, 160]];
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    let c = [30, 70, 40];
    for (const [cx, cy, r, k] of discs) if ((x - cx) ** 2 + (y - cy) ** 2 < r * r) c = cols[k];
    const o = (y * w + x) * 4, n = (rnd() - 0.5) * 12;
    px[o] = c[0] + n; px[o + 1] = c[1] + n; px[o + 2] = c[2] + n; px[o + 3] = 255;
  }
  const b = useWorker ? T.createBuilder() : T.createBuilder(null);
  // warm-up so the worker has started and both paths have compiled the code
  await b.run('pattern', { seed: 3n, number: 1 });
  let last = performance.now(), maxGap = 0, ticks = 0;
  const timer = setInterval(() => { const t = performance.now(); maxGap = Math.max(maxGap, t - last); last = t; ticks++; }, 10);
  const t0 = performance.now();
  const r = await b.run('photo', { image: { width: w, height: h, data: px }, detail: 'veryFine', seed: 99n,
    id: 'big', title: 'Big', probe: true });
  const total = performance.now() - t0;
  await new Promise(res => setTimeout(res, 40));   // let the timer see a main-thread block, if any
  clearInterval(timer);
  const mode = b.mode;
  b.terminate();
  return { mode, total: Math.round(total), maxMainThreadGap: Math.round(maxGap), ticks,
    tiles: r.result.kind === 'success' ? r.result.value.art.join('').replace(/\\./g, '').length : 0, stats: r.stats };
}
"""

FALLBACK_JS = """
async (want4) => {
  const T = window.__tc;
  const out = {};
  const none = T.createBuilder(null);
  out.nullSourceMode = none.mode;
  const a = await none.run('pattern', { seed: 4n, number: 7 });
  out.nullSourceMatches = JSON.stringify(a.level.solution) === JSON.stringify(want4.level.solution);
  const broken = T.createBuilder('this is not javascript (');
  out.brokenModeAtStart = broken.mode;
  const c = await broken.run('pattern', { seed: 4n, number: 7 });
  out.brokenFellBack = broken.mode === 'main';
  out.brokenMatches = JSON.stringify(c.level.solution) === JSON.stringify(want4.level.solution);
  const silent = T.createBuilder('/* never says ready */', { readyTimeoutMs: 300 });
  const d = await silent.run('pattern', { seed: 4n, number: 7 });
  out.silentFellBack = silent.mode === 'main';
  out.silentMatches = JSON.stringify(d.level.solution) === JSON.stringify(want4.level.solution);
  out.embeddedSourceKB = Math.round((T.builderWorkerSource() || '').length / 1024);
  // pixelsFromImage: a 1600x1000 half-transparent picture -> 720x450, transparent areas white
  const cv = new OffscreenCanvas(1600, 1000), cx = cv.getContext('2d');
  cx.fillStyle = 'rgb(200, 30, 40)'; cx.fillRect(0, 0, 800, 1000);
  const bmp = await createImageBitmap(cv);
  const img = T.pixelsFromImage(bmp, 1600, 1000);
  const at = (x, y) => Array.from(img.rgba.slice((y * img.width + x) * 4, (y * img.width + x) * 4 + 4));
  out.pixels = { width: img.width, height: img.height, left: at(100, 200), right: at(600, 200),
    targetSize: T.targetSize(1600, 1000) };
  return out;
}
"""


def main():
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="tc-builders-"))
    try:
        for d in ("src", "data", "tools"):
            shutil.copytree(WEB / d, tmp / d)
        (tmp / "src" / "main.js").write_text(MAIN_JS)
        (tmp / "src" / "ui").mkdir(exist_ok=True)
        (tmp / "src" / "ui" / "page.html").write_text(PAGE_HTML)
        (tmp / "src" / "ui" / "style.css").write_text("body{margin:0}")
        build = subprocess.run(["node", str(tmp / "tools" / "build_with_worker.mjs")], capture_output=True, text=True)
        if build.returncode:
            print(build.stdout, build.stderr)
            return 1
        page = (tmp / "dist" / "tessera-colony.html").read_text()
        want4 = next(p for p in FIX["patterns"] if p["seed"] == "4")
        want_flower = next(p for p in FIX["photos"] if p["name"] == "flower-fine-7")
        results = {"build": build.stdout.strip()}
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            ctx = browser.new_context()

            def serve(route):
                url = route.request.url
                body = FRAME_HTML if url.endswith("/frame.html") else page
                route.fulfill(status=200, content_type="text/html", body=body)
            ctx.route("https://tc.test/**", serve)
            pg = ctx.new_page()
            errors = []
            pg.on("pageerror", lambda e: errors.append(str(e)))
            pg.goto("https://tc.test/page.html")
            results["top"] = pg.evaluate(JOBS_JS, [want4, want_flower])
            results["fallback"] = pg.evaluate(FALLBACK_JS, want4)
            results["stallWorker"] = pg.evaluate(STALL_JS, True)
            results["stallMain"] = pg.evaluate(STALL_JS, False)
            pg.goto("https://tc.test/frame.html")
            pg.wait_for_function("document.getElementById('f').contentWindow !== null")
            frame = next(f for f in pg.frames if f.url.endswith("/page.html"))
            frame.wait_for_function("!!window.__tc")
            results["sandboxedIframe"] = frame.evaluate(JOBS_JS, [want4, want_flower])
            results["pageErrors"] = errors
            browser.close()
        print(json.dumps(results, indent=1))
        ok = True
        for k in ("top", "sandboxedIframe"):
            r = results[k]
            ok &= r["modeAfter"] == "worker" and r["patternMatches"] and r["patternHashIsBigInt"] \
                and r["patternStatsMatch"] and r["photoMatches"] and r["photoStatsMatch"] \
                and r["probeJobMatches"] and r["badJobRejected"]
        fb = results["fallback"]
        ok &= fb["nullSourceMode"] == "main" and fb["nullSourceMatches"] and fb["brokenFellBack"] \
            and fb["brokenMatches"] and fb["silentFellBack"] and fb["silentMatches"] and fb["embeddedSourceKB"] > 0
        ok &= fb["pixels"]["width"] == 720 and fb["pixels"]["height"] == 450
        ok &= fb["pixels"]["left"] == [200, 30, 40, 255] and fb["pixels"]["right"] == [255, 255, 255, 255]
        ok &= results["stallWorker"]["mode"] == "worker" and results["stallWorker"]["tiles"] == 6006
        ok &= results["stallWorker"]["maxMainThreadGap"] < 200
        print("OK" if ok else "FAILED")
        return 0 if ok else 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
