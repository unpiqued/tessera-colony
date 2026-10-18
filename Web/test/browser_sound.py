#!/usr/bin/env python3
"""Browser check of the Web Audio sound port (Chromium via Playwright; run: python3 test/browser_sound.py [OUT_DIR]).

1. Runs the reference model (`python3 ../Tools/sounds.py OUT_DIR`) for its WAV files.
2. Serves Web/ with http.server on 127.0.0.1 and opens headless Chromium with
   --autoplay-policy=user-gesture-required (audio may only start after a gesture, like Safari).
3. Offline: renders each of the 38 sounds through the module's real play path (SoundBoard.play /
   tile / deliver into a 44.1 kHz stereo OfflineAudioContext) and compares length, audible duration
   (to -60 dBFS), RMS and spectral centroid with the reference WAV, plus the largest difference
   from the float reference (sounds.build_all). Also checks panning and the volume control.
4. Real time (AudioContext): play() is a silent no-op before the first gesture; a click unlocks;
   a 16x clink stream thins to <= 20 a second and keeps its spacing on the context clock;
   cancelQueuedClicks; setHidden() and a browser-side suspend drop queued sounds and nothing stale
   plays after resuming; the Sound check report. The same unlock in a sandboxed iframe (like the
   artifact) with the module inlined as a classic script.
Prints the comparison table and a JSON summary (also written to OUT_DIR/browser_sound_report.json);
exits non-zero on failure.
"""
import base64
import functools
import html
import json
import math
import pathlib
import re
import subprocess
import sys
import tempfile
import threading
import wave
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import numpy as np
from playwright.sync_api import sync_playwright

WEB = pathlib.Path(__file__).resolve().parent.parent
TOOLS = WEB.parent / "Tools"
RATE = 44100
CENTER = math.cos(math.pi / 4)          # equal-power pan at 0 (StereoPannerNode and sounds.pan_gains)

sys.path.insert(0, str(TOOLS))
import sounds as S  # noqa: E402

OFFLINE_JS = """
async ({ keys, extra }) => {
  const m = await import('/src/sound/soundBoard.js');
  const src = new m.SoundBoard();
  await src.prepare();                     // the real (sliced) synthesis path
  const b64 = f32 => {
    const u8 = new Uint8Array(f32.buffer, f32.byteOffset, f32.byteLength);
    let s = '';
    for (let i = 0; i < u8.length; i += 0x8000) s += String.fromCharCode.apply(null, u8.subarray(i, i + 0x8000));
    return btoa(s);
  };
  const render = async (key, volume, pan) => {
    const n = src._samples[key].length;
    const ctx = new OfflineAudioContext(2, n + 4410, 44100);
    const sb = new m.SoundBoard({ createContext: () => ctx, now: () => 0 });
    sb._install(src._samples);
    sb.configure(true, volume, true, true, true, true);
    sb.unlock();
    let gain, mt;
    if ((mt = /^tile_(\\d)_(\\d)$/.exec(key))) {
      sb._counter = (Number(mt[2]) + 2) % 3;          // the next clink uses this variant
      sb.tile(Number(mt[1]), pan, 0);
      gain = m.SoundBoard.tileGain;
    } else if ((mt = /^deliver_(\\d)$/.exec(key))) {
      sb._counter = (Number(mt[1]) + 2) % 3;
      sb.deliver(pan, 0);
      gain = m.SoundBoard.deliverGain;
    } else {
      sb.play(key);
      gain = m.SoundCue.gain(key);
    }
    const buf = await ctx.startRendering();
    return { started: sb.startedCount, gain, n, L: b64(buf.getChannelData(0)), R: b64(buf.getChannelData(1)) };
  };
  const out = { sounds: {}, extra: {} };
  for (const key of keys) out.sounds[key] = await render(key, 1.0, 0);
  for (const [name, key, volume, pan] of extra) out.extra[name] = { ...(await render(key, volume, pan)), volume, pan };
  return out;
}
"""

SETUP_JS = """
async () => {
  const m = await import('/src/sound/soundBoard.js');
  const sb = m.SoundBoard.shared;
  window.__sb = sb; window.__m = m;
  sb.configure(true, 0.8, true, true, true, true);
  await sb.prepare();
  const r = {};
  let threw = null;
  try {
    sb.play('send'); sb.play('teamDone', 0.2); sb.tile(1, 0, 0); sb.deliver(0, 0.1);
    sb.playSample('goal'); sb.cancelQueuedClicks(); sb.setHidden(false);
  } catch (e) { threw = String(e); }
  r.beforeGesture = { threw, unlocked: sb.isUnlocked, started: sb.startedCount, soundsReady: sb.soundsReady };
  const unlock = () => sb.unlock();
  window.addEventListener('pointerdown', unlock, { capture: true });
  window.addEventListener('keydown', unlock, { capture: true });
  return r;
}
"""

REALTIME_JS = """
async () => {
  const sb = window.__sb, m = window.__m, ctx = sb.context;
  const sleep = ms => new Promise(res => setTimeout(res, ms));
  const waitState = async (s) => { for (let i = 0; i < 100 && ctx.state !== s; i++) await sleep(10); return ctx.state; };
  const r = { state: ctx.state, sampleRate: ctx.sampleRate, baseLatency: ctx.baseLatency, lead: sb._lead };
  // a tap on the analyser: anything audible on the submix shows up here
  const tap = ctx.createAnalyser();
  tap.fftSize = 2048;
  sb._submix.connect(tap);
  const tapBuf = new Float32Array(tap.fftSize);
  const loudness = async (ms) => {
    let peak = 0;
    for (let t = 0; t < ms; t += 20) {
      tap.getFloatTimeDomainData(tapBuf);
      for (const v of tapBuf) peak = Math.max(peak, Math.abs(v));
      await sleep(20);
    }
    return peak;
  };
  let s0 = sb.startedCount;
  sb.play('send');
  r.sendStarted = sb.startedCount - s0;
  r.sendPeak = await loudness(300);

  // 16x clink stream: 400 pickups a second, handed over 0.16 s ahead every 100 ms for 3 s
  sb.trace = [];
  let next = performance.now() / 1000 + 0.05, k = 0, ticks = 0;
  await new Promise(res => {
    const h = setInterval(() => {
      const now = performance.now() / 1000;
      for (; next <= now + 0.16; next += 0.0025, k++) {
        if (next >= now - 0.3) sb.tile(k, (k % 7) / 3 - 1, Math.max(0, next - now));
      }
      if (++ticks >= 30) { clearInterval(h); res(); }
    }, 100);
  });
  const st = sb.trace.filter(e => e.at !== undefined);
  const ats = st.map(e => e.at);
  let maxPerSecond = 0;
  for (let i = 0, j = 0; i < ats.length; i++) { while (ats[i] - ats[j] >= 1) j++; maxPerSecond = Math.max(maxPerSecond, i - j + 1); }
  let minGap = Infinity;
  const spacing = [];
  for (let i = 1; i < st.length; i++) {
    minGap = Math.min(minGap, st[i].at - st[i - 1].at);
    spacing.push(Math.abs((st[i].when - st[i - 1].when) - (st[i].at - st[i - 1].at)));
  }
  spacing.sort((a, b) => a - b);
  r.stream = {
    requests: k, clinks: st.length, failed: sb.trace.filter(e => e.failed).length, maxPerSecond,
    minGapMs: minGap * 1000,
    spacingErrMaxMs: spacing[spacing.length - 1] * 1000,
    spacingErrP90Ms: spacing[Math.floor(spacing.length * 0.9)] * 1000,
    scheduledAheadMinMs: Math.min(...st.map(e => (e.when - e.ctxTime) * 1000)),
  };
  await sleep(400);

  // cancelQueuedClicks: clinks queued ahead are dropped, cues stay
  sb.trace = [];
  sb.play('wait', 0.3);
  for (let j = 0; j < 5; j++) sb.tile(j, 0, 0.1 + 0.06 * j);
  const queued = sb.trace.filter(e => e.at !== undefined && e.click).length;
  sb.cancelQueuedClicks();
  const nowH = performance.now() / 1000;
  r.cancel = {
    queued,
    clickVoicesStillQueued: sb._busyUntil.filter((b, i) => sb._voiceIsClick[i] && sb._voiceStart[i] > nowH).length,
    cueStillQueued: sb._busyUntil.filter((b, i) => !sb._voiceIsClick[i] && sb._voiceStart[i] > nowH).length,
  };
  await sleep(1200);

  // hidden page: queued sounds dropped, context suspended, nothing plays; shown: resumes, no burst
  sb.play('newBest', 0.25);
  sb.tile(2, 0, 0.12);
  sb.setHidden(true);
  r.hidden = { state: await waitState('suspended'), busyVoices: sb._busyUntil.filter(b => b > 0).length };
  s0 = sb.startedCount;
  sb.play('hint'); sb.tile(3, 0, 0);
  r.hidden.startedWhileHidden = sb.startedCount - s0;
  await sleep(200);
  sb.setHidden(false);
  r.shown = { state: await waitState('running'), peakAfterResume: await loudness(600) };

  // the browser suspends the context on its own (iOS: background, phone call)
  sb.play('complete', 0.3);
  sb.tile(4, 0, 0.1);
  await ctx.suspend();
  await sleep(50);                         // the statechange event follows the promise
  r.browserSuspend = { state: ctx.state, busyVoices: sb._busyUntil.filter(b => b > 0).length };
  await sleep(300);
  await ctx.resume();
  r.browserSuspend.peakAfterResume = await loudness(700);
  r.browserSuspend.state2 = ctx.state;

  // Sound check
  const played = sb.playTestSound();
  await sleep(400);
  r.soundCheck = m.soundCheckReport(sb.status(), played);
  r.status = sb.status();
  return r;
}
"""

IFRAME_SETUP_JS = """
async () => {
  const sb = window.__tc.SoundBoard.shared;
  sb.configure(true, 0.8, true, true, true, true);
  await sb.prepare();
  window.addEventListener('pointerdown', () => sb.unlock(), { capture: true });
  sb.play('send');
  return { unlocked: sb.isUnlocked, started: sb.startedCount, origin: String(window.origin) };
}
"""

IFRAME_CHECK_JS = """
async () => {
  const sb = window.__tc.SoundBoard.shared;
  for (let i = 0; i < 100 && !(sb.context && sb.context.state === 'running'); i++) await new Promise(r => setTimeout(r, 10));
  const s0 = sb.startedCount;
  sb.play('teamDone');
  sb.tile(0, 0, 0.05);
  return { state: sb.context && sb.context.state, started: sb.startedCount - s0 };
}
"""


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def serve(directory):
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(QuietHandler, directory=str(directory)))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def read_wav(path):
    with wave.open(str(path), "rb") as w:
        assert w.getnchannels() == 1 and w.getframerate() == RATE and w.getsampwidth() == 2
        return np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float64) / 32767.0


def f32(b64):
    return np.frombuffer(base64.b64decode(b64), dtype="<f4").astype(np.float64)


def audible_seconds(x, floor=0.001):
    idx = np.nonzero(np.abs(x) >= floor)[0]
    return (idx[-1] + 1) / RATE if len(idx) else 0.0


def rms_db(x):
    return 20 * math.log10(math.sqrt(float(np.mean(x ** 2))) + 1e-12)


def centroid(x):
    mag = np.abs(np.fft.rfft(x))
    freqs = np.fft.rfftfreq(len(x), 1.0 / RATE)
    return float(np.sum(freqs * mag) / np.sum(mag))


def best_lag(a, b, span=64):
    best, lag = -1e9, 0
    for k in range(-span, span + 1):
        if k >= 0:
            c = float(np.dot(a[k:], b[:len(b) - k]))
        else:
            c = float(np.dot(a[:k], b[-k:]))
        if c > best:
            best, lag = c, k
    return lag


def inline_module_page():
    """The module as a classic script in a sandboxed srcdoc iframe (what the bundled artifact does)."""
    code = (WEB / "src" / "sound" / "soundBoard.js").read_text()
    code = re.sub(r"^export\s+", "", code, flags=re.M)
    script = "(function(){\n" + code + "\nwindow.__tc = { SoundBoard, SoundCue, soundCheckReport };\n})();"
    inner = ("<!doctype html><html><body style='margin:0;height:300px;background:#eee'>"
             "<script>" + script.replace("</script", "<\\/script") + "</script></body></html>")
    return ("<!doctype html><html><body style='margin:0'>"
            "<iframe id='f' sandbox='allow-scripts' width='400' height='300' srcdoc=\"" + html.escape(inner, quote=True)
            + "\"></iframe></body></html>")


def main():
    out_dir = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path(tempfile.mkdtemp(prefix="tc_sound_"))
    out_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, str(TOOLS / "sounds.py"), str(out_dir)], check=True, stdout=subprocess.DEVNULL)
    ref = S.build_all()
    keys = list(ref.keys())
    failures = []
    summary = {"out_dir": str(out_dir)}

    httpd = serve(WEB)
    base = "http://127.0.0.1:%d" % httpd.server_address[1]
    (out_dir / "iframe.html").write_text(inline_module_page())
    frame_httpd = serve(out_dir)
    frame_base = "http://127.0.0.1:%d" % frame_httpd.server_address[1]
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, args=["--autoplay-policy=user-gesture-required"])
        page = browser.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(base + "/")

        # ---- offline rendering of every sound ----
        extra = [["pan_left", "tile_2_1", 1.0, -0.5], ["pan_right", "deliver_1", 1.0, 0.7], ["volume_half", "send", 0.5, 0]]
        res = page.evaluate(OFFLINE_JS, {"keys": keys, "extra": extra})
        rows = []
        for key in keys:
            r = res["sounds"][key]
            L, R = f32(r["L"]), f32(r["R"])
            want = ref[key].astype(np.float64)
            wav = read_wav(out_dir / (key + ".wav"))
            n = len(want)
            web = L / (r["gain"] * CENTER)                      # undo the play-time gain and centre pan
            lag = best_lag(web[:n], want)
            row = {
                "key": key,
                "set": "goal" if key in S.GOAL_SET else "action" if key in S.ACTION_SET else "colony",
                "gain": r["gain"],
                "samples_ref": len(wav), "samples_web": r["n"],
                "dur_ref": audible_seconds(wav), "dur_web": audible_seconds(web),
                "rms_ref": rms_db(wav), "rms_web": rms_db(web[:n]),
                "cent_ref": centroid(wav), "cent_web": centroid(web[:n]),
                "max_diff_float_ref": float(np.max(np.abs(web[:n] - want))),
                "after_end": float(np.max(np.abs(L[n:]))) if len(L) > n else 0.0,
                "lag": lag, "lr_equal": bool(np.array_equal(L, R)), "started": r["started"],
            }
            rows.append(row)
            problems = []
            if row["started"] != 1:
                problems.append("not started")
            if row["samples_web"] != row["samples_ref"]:
                problems.append("length")
            if lag != 0:
                problems.append("lag %d" % lag)
            if abs(row["dur_web"] - row["dur_ref"]) > 0.001:
                problems.append("duration")
            if abs(row["rms_web"] - row["rms_ref"]) > 0.01:
                problems.append("rms")
            if abs(row["cent_web"] - row["cent_ref"]) > 0.002 * row["cent_ref"]:
                problems.append("centroid")
            if row["max_diff_float_ref"] > 2e-6:
                problems.append("samples")
            if not row["lr_equal"] or row["after_end"] != 0.0:
                problems.append("channels / tail")
            if problems:
                failures.append("%s: %s" % (key, ", ".join(problems)))
        # panning (equal power, like sounds.pan_gains) and volume
        pan_rows = {}
        for name, key, volume, pan in extra:
            r = res["extra"][name]
            L, R = f32(r["L"]), f32(r["R"])
            x = ref[key].astype(np.float64)
            gl, gr = S.pan_gains(pan)
            gl, gr = gl * r["gain"] * volume, gr * r["gain"] * volume
            n = len(x)
            dl = float(np.max(np.abs(L[:n] - gl * x)))
            dr = float(np.max(np.abs(R[:n] - gr * x)))
            pan_rows[name] = {"key": key, "volume": volume, "pan": pan, "max_diff_L": dl, "max_diff_R": dr}
            if max(dl, dr) > 2e-7:
                failures.append("%s: |diff| %.2g / %.2g" % (name, dl, dr))
        summary["pan_volume"] = pan_rows

        # ---- real-time AudioContext ----
        setup = page.evaluate(SETUP_JS)
        bg = setup["beforeGesture"]
        if bg["threw"] or bg["unlocked"] or bg["started"] != 0:
            failures.append("before a gesture: %s" % bg)
        page.mouse.click(30, 30)
        page.wait_for_function("window.__sb.context && window.__sb.context.state === 'running'", timeout=5000)
        rt = page.evaluate(REALTIME_JS)
        summary["before_gesture"] = bg
        summary["realtime"] = rt
        st = rt["stream"]
        if rt["sendStarted"] != 1 or rt["sendPeak"] <= 0.01:
            failures.append("send after unlock: started %s, peak %s" % (rt["sendStarted"], rt["sendPeak"]))
        if st["maxPerSecond"] > 21 or st["maxPerSecond"] < 18 or st["minGapMs"] < 50 - 1e-6:
            failures.append("16x thinning: %s" % st)
        if st["spacingErrMaxMs"] > 1.5 or st["scheduledAheadMinMs"] < 0:
            failures.append("context clock mapping: %s" % st)
        c = rt["cancel"]
        if c["queued"] < 3 or c["clickVoicesStillQueued"] != 0 or c["cueStillQueued"] != 1:
            failures.append("cancelQueuedClicks: %s" % c)
        h = rt["hidden"]
        if h["state"] != "suspended" or h["busyVoices"] != 0 or h["startedWhileHidden"] != 0:
            failures.append("setHidden(true): %s" % h)
        if rt["shown"]["state"] != "running" or rt["shown"]["peakAfterResume"] != 0:
            failures.append("setHidden(false): %s" % rt["shown"])
        b = rt["browserSuspend"]
        if b["busyVoices"] != 0 or b["peakAfterResume"] != 0 or b["state2"] != "running":
            failures.append("browser suspend: %s" % b)
        if "Sounds ready: 38 of 38" not in rt["soundCheck"] or "Test chime started: yes" not in rt["soundCheck"]:
            failures.append("sound check: %s" % rt["soundCheck"])

        # ---- sandboxed iframe (opaque origin, module inlined like the bundle) ----
        page2 = browser.new_page()
        page2.on("pageerror", lambda e: errors.append("iframe page: " + str(e)))
        page2.goto(frame_base + "/iframe.html")
        frame = page2.frames[1]
        frame.wait_for_function("window.__tc !== undefined")
        f_before = frame.evaluate(IFRAME_SETUP_JS)
        box = page2.locator("#f").bounding_box()
        page2.mouse.click(box["x"] + 50, box["y"] + 50)
        f_after = frame.evaluate(IFRAME_CHECK_JS)
        summary["iframe"] = {"before": f_before, "after": f_after}
        if f_before["unlocked"] or f_before["started"] != 0 or f_after["state"] != "running" or f_after["started"] != 2:
            failures.append("sandboxed iframe: %s" % summary["iframe"])
        browser.close()
        if errors:
            failures.append("page errors: %s" % errors)
    httpd.shutdown()
    frame_httpd.shutdown()

    # ---- report ----
    print("| sound | set | gain | samples | dur ref s | dur web s | RMS ref dBFS | RMS web dBFS | centroid ref Hz | centroid web Hz | max diff vs float ref |")
    print("|---|---|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        print("| %s | %s | %.2f | %d | %.3f | %.3f | %.2f | %.2f | %.0f | %.0f | %.1e |" % (
            r["key"], r["set"], r["gain"], r["samples_web"], r["dur_ref"], r["dur_web"], r["rms_ref"], r["rms_web"],
            r["cent_ref"], r["cent_web"], r["max_diff_float_ref"]))
    worst = {
        "duration_ms": max(abs(r["dur_web"] - r["dur_ref"]) * 1000 for r in rows),
        "rms_db": max(abs(r["rms_web"] - r["rms_ref"]) for r in rows),
        "centroid_pct": max(abs(r["cent_web"] - r["cent_ref"]) / r["cent_ref"] * 100 for r in rows),
        "samples_vs_float_ref": max(r["max_diff_float_ref"] for r in rows),
    }
    summary["worst"] = worst
    summary["rows"] = rows
    summary["failures"] = failures
    (out_dir / "browser_sound_report.json").write_text(json.dumps(summary, indent=1))
    print()
    print(json.dumps({k: summary[k] for k in ("worst", "pan_volume", "before_gesture", "iframe")}, indent=1))
    print(json.dumps({k: v for k, v in summary["realtime"].items() if k not in ("soundCheck", "status")}, indent=1))
    print(summary["realtime"]["soundCheck"])
    print("FAILURES:" if failures else "ALL BROWSER SOUND CHECKS PASSED", *failures, sep="\n  ")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
