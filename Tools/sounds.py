"""Reference model of the in-game sound effects (mirrors SoundBoard.swift, sample for sample).

Every sound is synthesized in code, so the app ships no audio files:
  * struck notes = damped sine partials (glass, marimba, bell and wood recipes) + a noise click,
  * swishes = deterministic noise through one-pole filters with shaped envelopes,
  * glides = sine sweeps with exponential frequency change.
Each sound is DC-removed, faded in/out and normalised to a 0.9 peak; loudness is set per cue at play time.

Usage: python3 sounds.py OUT_DIR [levels_report.json]
  -> one WAV per sound, a contact-sheet PNG and a JSON report; with the level report also two
     listening previews (the opening of First Dig at 1x, and a catalogue of every event sound).
"""
import json
import math
import os
import sys
import wave

import numpy as np

RATE = 44100

# partial recipes: (frequency ratio, amplitude, decay time constant in seconds)
GLASS = [(1.0, 1.0, 0.07), (2.76, 0.35, 0.035), (5.40, 0.12, 0.02)]
MARIMBA = [(1.0, 1.0, 0.25), (4.0, 0.25, 0.05), (9.2, 0.06, 0.02)]
BELL = [(1.0, 1.0, 0.6), (2.0, 0.4, 0.35), (3.0, 0.15, 0.25), (4.2, 0.12, 0.15), (5.4, 0.06, 0.1)]
WOOD = [(1.0, 1.0, 0.03), (2.3, 0.4, 0.02)]

# one note per colour family (major pentatonic, C5 up): each colour sounds its own pitch
TILE_SCALE = [523.25, 587.33, 659.26, 783.99, 880.00, 1046.50, 1174.66, 1318.51]

# Two sound sets plus the colony layer:
#   ACTION: dry wood and clay for the moves the player makes (short, low-mid, no long tails)
#   GOAL:   bright bells and glass for achievements (pentatonic, rising, with a shimmer echo)
#   colony: the tile clinks and nest drops (tile_*, deliver_*)
ACTION_SET = ["send", "scout", "undo", "addSlot", "returnTeam", "refused", "wait", "blocked", "hint"]
GOAL_SET = ["teamDone", "colourCleared", "milestone1", "milestone2", "milestone3", "complete", "newBest", "unlocked"]

# play-time gains per cue (the SoundBoard multiplies these by the player's volume)
GAINS = {"tile": 0.22, "deliver": 0.12,
         "send": 0.5, "scout": 0.3, "undo": 0.35, "addSlot": 0.45, "returnTeam": 0.4, "refused": 0.55,
         "wait": 0.45, "blocked": 0.45, "hint": 0.4,
         "teamDone": 0.38, "colourCleared": 0.45, "milestone1": 0.42, "milestone2": 0.42, "milestone3": 0.42,
         "complete": 0.55, "newBest": 0.5, "unlocked": 0.5}

MARIMBA_SHORT = [(1.0, 1.0, 0.09), (4.0, 0.25, 0.03), (9.2, 0.06, 0.015)]
# a bell with slightly detuned twins: the beating gives goal sounds their shimmer
GLASS_BELL = BELL + [(1.004, 0.5, 0.5), (2.006, 0.2, 0.3)]


class Noise:
    """64-bit LCG, identical to SoundSynth.Noise in Swift."""
    def __init__(self, seed):
        self.s = seed & 0xFFFFFFFFFFFFFFFF

    def next(self):
        self.s = (self.s * 6364136223846793005 + 1442695040888963407) & 0xFFFFFFFFFFFFFFFF
        return ((self.s >> 40) & 0xFFFFFF) / 16777215.0 * 2.0 - 1.0

    def block(self, n):
        return np.array([self.next() for _ in range(n)], dtype=np.float64)


def n_samples(seconds):
    return int(seconds * RATE)


def strike(freq, partials, length, click=0.0, click_decay=0.003, seed=1, attack=0.002):
    n = n_samples(length)
    t = np.arange(n) / RATE
    out = np.zeros(n)
    for ratio, amp, decay in partials:
        f = freq * ratio
        if f >= RATE * 0.45:
            continue
        out += amp * np.exp(-t / decay) * np.sin(2 * math.pi * f * t)
    if click > 0:
        nz = highpass(Noise(seed).block(n), 2000.0)
        out += click * nz * np.exp(-t / click_decay)
    a = n_samples(attack)
    if a > 0:
        out[:a] *= np.arange(a) / a
    return out


def glide(f1, f2, glide_time, decay, length, harmonic2=0.0):
    n = n_samples(length)
    t = np.arange(n) / RATE
    k = np.minimum(t / glide_time, 1.0)
    f = f1 * (f2 / f1) ** k
    phase = 2 * math.pi * np.cumsum(f) / RATE
    env = np.exp(-t / decay)
    a = n_samples(0.004)
    env[:a] *= np.arange(a) / a
    return env * (np.sin(phase) + harmonic2 * np.sin(2 * phase))


def lowpass(x, cutoff):
    a = 1.0 - math.exp(-2 * math.pi * cutoff / RATE)
    y = np.zeros_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc += a * (v - acc)
        y[i] = acc
    return y


def highpass(x, cutoff):
    return x - lowpass(x, cutoff)


def swish(length, cutoff, rise, decay, seed, reverse=False):
    n = n_samples(length)
    t = np.arange(n) / RATE
    nz = lowpass(Noise(seed).block(n), cutoff)
    if reverse:
        env = np.exp((t - rise) / (rise / 4.0))
        env[t > rise] = 0.0
        cut = n_samples(rise)
        fade = min(n_samples(0.004), cut)
        if fade > 0:
            env[cut - fade:cut] *= np.linspace(1, 0, fade)
    else:
        env = np.where(t < rise, t / rise, np.exp(-(t - rise) / decay))
    return nz * env


def place(total, parts):
    out = np.zeros(n_samples(total))
    for offset, samples, gain in parts:
        s = n_samples(offset)
        e = min(len(out), s + len(samples))
        out[s:e] += gain * samples[:e - s]
    return out


def echo(x, delay, feedback, taps):
    """Adds `taps` delayed copies, each `feedback` times quieter (a small hall shimmer)."""
    d = n_samples(delay)
    out = np.zeros(len(x) + taps * d)
    out[:len(x)] += x
    g = 1.0
    for k in range(1, taps + 1):
        g *= feedback
        out[k * d:k * d + len(x)] += g * x
    return out


def finish(x, peak=0.9):
    x = x - np.mean(x)
    fi = n_samples(0.002)
    fo = max(n_samples(0.012), int(len(x) * 0.25))      # long, smooth tail fade (cosine)
    x[:fi] *= np.arange(fi) / fi
    x[-fo:] *= 0.5 * (1 + np.cos(math.pi * np.linspace(0, 1, fo)))
    m = np.max(np.abs(x))
    if m > 0:
        x = x * (peak / m)
    return x.astype(np.float32)


def build_all():
    s = {}
    for f, base in enumerate(TILE_SCALE[:6]):
        for v in range(3):
            freq = base * (1 + (v - 1) * 0.012)
            s["tile_%d_%d" % (f, v)] = finish(strike(freq, GLASS, 0.22, click=0.18, seed=11 + f * 3 + v))
    for v in range(3):
        f = 380.0 * (1 + (v - 1) * 0.03)
        body = strike(f, WOOD, 0.12, seed=40 + v)
        clk = lowpass(Noise(50 + v).block(n_samples(0.12)), 2500.0) * np.exp(-np.arange(n_samples(0.12)) / RATE / 0.006)
        s["deliver_%d" % v] = finish(body + 0.5 * clk)
    # ---- ACTION set: wood and clay ----
    s["send"] = finish(place(0.28, [(0.0, strike(330.0, WOOD, 0.12, click=0.25, seed=61), 0.8),
                                   (0.0, swish(0.28, 1500.0, 0.02, 0.06, 62), 0.45),
                                   (0.01, glide(200.0, 120.0, 0.12, 0.06, 0.2), 0.6)]))
    s["scout"] = finish(place(0.2, [(0.0, strike(660.0, WOOD, 0.08, click=0.1, seed=91), 0.6),
                                   (0.06, strike(880.0, WOOD, 0.08, click=0.1, seed=92), 0.5)]))
    s["undo"] = finish(place(0.2, [(0.0, swish(0.2, 3000.0, 0.09, 0.05, 81, reverse=True), 0.7),
                                  (0.09, strike(520.0, WOOD, 0.11, click=0.2, seed=82), 0.6)]))
    s["addSlot"] = finish(place(0.3, [(0.0, strike(392.0, MARIMBA_SHORT, 0.16), 0.7),
                                     (0.08, strike(523.25, MARIMBA_SHORT, 0.2), 0.8)]))
    s["returnTeam"] = finish(place(0.35, [(0.0, glide(520.0, 260.0, 0.12, 0.08, 0.3, harmonic2=0.25), 0.6),
                                         (0.11, strike(261.63, MARIMBA_SHORT, 0.22), 0.7)]))
    thud = strike(140.0, [(1.0, 1.0, 0.05), (2.0, 0.2, 0.03)], 0.15, click=0.3, click_decay=0.004, seed=71)
    s["refused"] = finish(place(0.3, [(0.0, thud, 1.0), (0.11, thud, 0.8)]))
    s["wait"] = finish(place(0.45, [(0.0, strike(329.63, MARIMBA, 0.3), 1.0),
                                   (0.12, strike(246.94, MARIMBA, 0.32), 0.9)]))
    s["blocked"] = finish(place(0.8, [(0.0, strike(220.0, MARIMBA, 0.68), 0.8),
                                     (0.06, strike(261.63, MARIMBA, 0.68), 0.8),
                                     (0.12, strike(329.63, MARIMBA, 0.68), 0.8)]))
    s["hint"] = finish(place(0.4, [(0.0, strike(440.0, MARIMBA_SHORT, 0.25), 0.7),
                                  (0.09, strike(587.33, MARIMBA_SHORT, 0.3), 0.7)]))
    # ---- GOAL set: bells and glass ----
    s["teamDone"] = finish(echo(place(0.7, [(0.0, strike(783.99, GLASS_BELL, 0.6), 0.55),
                                           (0.08, strike(1174.66, GLASS_BELL, 0.62), 0.55)]), 0.11, 0.3, 2))
    s["colourCleared"] = finish(echo(place(0.9, [(0.0, strike(1046.50, GLASS_BELL, 0.8), 0.45),
                                                (0.07, strike(1318.51, GLASS_BELL, 0.8), 0.45),
                                                (0.14, strike(1567.98, GLASS_BELL, 0.76), 0.45),
                                                (0.14, strike(523.25, BELL, 0.76), 0.3)]), 0.12, 0.35, 3))
    runs = {"milestone1": [523.25, 587.33, 659.26, 783.99],
            "milestone2": [659.26, 783.99, 880.00, 1046.50],
            "milestone3": [783.99, 880.00, 1046.50, 1174.66, 1318.51]}
    for name, notes in runs.items():
        parts = [(k * 0.07, strike(f, GLASS_BELL, 0.7), 0.42) for k, f in enumerate(notes)]
        s[name] = finish(echo(place(1.0, parts), 0.12, 0.3, 2))
    arp = [523.25, 659.26, 783.99, 1046.50, 1318.51, 1567.98]
    parts = [(k * 0.085, strike(f, BELL, 1.2), 0.45) for k, f in enumerate(arp)]
    long_bell = [(r, a, d * 2.2) for r, a, d in BELL]
    for f in (523.25, 783.99, 1046.50, 1318.51):
        parts.append((0.6, strike(f, long_bell, 1.6), 0.3))
    s["complete"] = finish(echo(place(2.2, parts), 0.13, 0.28, 2))
    s["newBest"] = finish(echo(place(0.9, [(k * 0.06, strike(f, GLASS_BELL, 0.7), 0.45)
                                          for k, f in enumerate([1046.50, 1318.51, 1567.98, 2093.0])]), 0.1, 0.3, 2))
    sparkle = [1046.50, 1174.66, 1318.51, 1567.98, 1760.00, 2093.0, 2349.32, 2637.02]
    parts = [(k * 0.045, strike(f, GLASS, 0.25, seed=120 + k), 0.35) for k, f in enumerate(sparkle)]
    for f in (523.25, 659.26, 783.99):
        parts.append((0.4, strike(f, long_bell, 1.2), 0.3))
    s["unlocked"] = finish(echo(place(1.6, parts), 0.12, 0.3, 2))
    return s


def write_wav(path, x):
    pcm = (np.clip(x, -1, 1) * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(pcm.tobytes())


def analyse(name, x):
    a = np.abs(x)
    return {
        "seconds": round(len(x) / RATE, 3),
        "peak": round(float(a.max()), 3),
        "rms_dbfs": round(20 * math.log10(float(np.sqrt(np.mean(x.astype(np.float64) ** 2))) + 1e-12), 1),
        "dc": round(float(np.mean(x)), 5),
        "first_sample": round(float(abs(x[0])), 5),
        "last_sample": round(float(abs(x[-1])), 5),
        "finite": bool(np.all(np.isfinite(x))),
    }


def worst_case_mix(sounds):
    """Loudest plausible moment: a dense pickup stream at the SoundBoard's throttle (one tile click
    per 50 ms), deliveries every 80 ms, and send + slot-open + win landing together."""
    total = n_samples(2.5)
    mix = np.zeros(total)
    names = [k for k in sounds if k.startswith("tile_")]
    t = 0.0
    k = 0
    while t < 2.2:
        x = sounds[names[k % len(names)]]
        s = n_samples(t)
        e = min(total, s + len(x))
        mix[s:e] += GAINS["tile"] * x[:e - s]
        t += 0.05
        k += 1
    t = 0.0
    while t < 2.2:
        x = sounds["deliver_%d" % (k % 3)]
        s = n_samples(t)
        e = min(total, s + len(x))
        mix[s:e] += GAINS["deliver"] * x[:e - s]
        t += 0.08
        k += 1
    for name in ("send", "teamDone", "complete", "unlocked"):
        x = sounds[name]
        mix[:len(x)] += GAINS[name] * x
    return float(np.max(np.abs(mix)))


# ---------------------------------------------------------------------------------------------
# Timing model of GameController.pumpTileSounds + SoundBoard.tile/deliver throttling
# ---------------------------------------------------------------------------------------------

TICK = 0.1            # GameController.tick runs at 10 Hz (real seconds)
LOOKAHEAD = 0.16      # real seconds of events handed over per tick
STALE = 0.3           # events older than this (real seconds at current speed) are skipped
TILE_GAP = 0.05       # SoundBoard: at most one tile clink per 50 ms
DELIVER_GAP = 0.08
VOICES = 14
TILE_LEN = 0.22 + 0.03
DELIVER_LEN = 0.12 + 0.03


class Clock:
    """Game clock with speed changes (GameClock in Swift): game time = anchor + (real - anchor_real) * speed."""
    def __init__(self, speed):
        self.anchor_real, self.anchor_game, self.speed = 0.0, 0.0, speed

    def game(self, r):
        return self.anchor_game + (r - self.anchor_real) * self.speed

    def set_speed(self, v, r):
        self.anchor_game = self.game(r)
        self.anchor_real = r
        self.speed = v

    def real_of(self, g, segments):
        """Real time at which game time g happens, given the full speed timeline."""
        for (r0, g0, sp, r1) in segments:
            g1 = g0 + (r1 - r0) * sp
            if g <= g1 + 1e-12:
                return r0 + (g - g0) / sp
        r0, g0, sp, _ = segments[-1]
        return r0 + (g - g0) / sp


def pump_simulation(trips, speed_plan, jitter_seed=5, return_heard=False):
    """trips: list of (arrive, home) game times. speed_plan: [(real_time, speed), ...] starting at 0.
    Mirrors GameController.setSpeed / pumpTileSounds and SoundBoard.tile / deliver / cancelQueuedClicks.
    Returns how the clinks the SoundBoard would start line up with the real pickups."""
    import random
    rng = random.Random(jitter_seed)
    clock = Clock(speed_plan[0][1])
    plan = list(speed_plan[1:])
    cursor = 0.0
    sound_speed = speed_plan[0][1]
    last_tile = last_deliver = -1.0
    voices = [None] * VOICES          # (busy_until, start, is_click, played_index)
    played = []                       # [kind, event index, real start, cancelled]
    dropped_voice = 0
    cancels = 0
    segments = [[0.0, 0.0, speed_plan[0][1], None]]
    end_game = max(h for _, h in trips) + 1.0
    r = 0.0
    while clock.game(r) < end_game:
        while plan and plan[0][0] <= r:
            rc, v = plan.pop(0)
            segments[-1][3] = rc
            clock.set_speed(v, rc)
            segments.append([rc, clock.game(rc), v, None])
            if abs(math.log(v / sound_speed)) > math.log(1.25):     # GameController.setSpeed
                cancels += 1
                for k, vc in enumerate(voices):                      # SoundBoard.cancelQueuedClicks
                    if vc and vc[2] and vc[1] > rc:
                        played[vc[3]][3] = True
                        voices[k] = None
                last_tile = min(last_tile, rc)
                last_deliver = min(last_deliver, rc)
                cursor = min(cursor, clock.game(rc))
                sound_speed = v
        t = clock.game(r)
        sp = clock.speed
        horizon = t + LOOKAHEAD * sp
        frm = max(cursor, t - STALE * sp)
        cursor = max(cursor, horizon)
        sound_speed = sp
        events = []
        for i, (a, h) in enumerate(trips):
            if frm < a <= horizon:
                events.append((a, "tile", i))
            if frm < h <= horizon:
                events.append((h, "deliver", i))
        events.sort()
        for (et, kind, i) in events:
            start = r + max(0.0, (et - t) / sp)
            if kind == "tile":
                if start - last_tile < TILE_GAP:
                    continue
            elif start - last_deliver < DELIVER_GAP:
                continue
            free = [k for k in range(VOICES) if voices[k] is None or voices[k][0] <= r]
            if not free:
                dropped_voice += 1
                continue
            voices[free[0]] = (start + (TILE_LEN if kind == "tile" else DELIVER_LEN), start, True, len(played))
            if kind == "tile":
                last_tile = start
            else:
                last_deliver = start
            played.append([kind, i, start, False])
        r += TICK * (1 + 0.2 * (rng.random() - 0.5))      # ticks are not perfectly regular
    segments[-1][3] = float("inf")
    segs = [tuple(x) for x in segments]
    heard = [(k, i, st) for k, i, st, c in played if not c]
    if return_heard:
        return heard
    errors = []
    for kind, i, start in heard:
        g = trips[i][0] if kind == "tile" else trips[i][1]
        errors.append(abs(start - clock.real_of(g, segs)))
    tiles = sorted(st for k, _, st in heard if k == "tile")
    max_rate = 0
    j = 0
    for k2 in range(len(tiles)):
        while tiles[k2] - tiles[j] >= 1.0:
            j += 1
        max_rate = max(max_rate, k2 - j + 1)
    dup = len(heard) - len({(k, i) for k, i, _ in heard})
    # every pickup should have a clink close by (its own, or one it was merged into by the throttle)
    import bisect
    nearest = []
    for a, _ in trips:
        x = clock.real_of(a, segs)
        k = bisect.bisect_left(tiles, x)
        d = min(abs(tiles[m] - x) for m in (k - 1, k) if 0 <= m < len(tiles)) if tiles else float("inf")
        nearest.append(d)
    nearest.sort()
    return {
        "pickups": len(trips), "tile_clinks": len(tiles),
        "deliver_drops": sum(1 for k, _, _ in heard if k == "deliver"),
        "speed_changes": len(speed_plan) - 1, "queue_cancels": cancels,
        "max_timing_error_ms": round(1000 * max(errors or [0]), 1),
        "p99_timing_error_ms": round(1000 * sorted(errors)[int(0.99 * (len(errors) - 1))], 1) if errors else 0,
        "max_clinks_in_any_second": max_rate, "duplicates": dup, "voice_starved": dropped_voice,
        "max_ms_from_a_pickup_to_the_nearest_clink": round(1000 * nearest[-1], 1),
        "p99_ms_from_a_pickup_to_the_nearest_clink": round(1000 * nearest[int(0.99 * (len(nearest) - 1))], 1),
    }


def drag(r0, v0, v1, seconds, rate=60):
    """A slider drag from v0 to v1 (log scale) as a list of speed updates."""
    n = max(1, int(seconds * rate))
    return [(r0 + k * seconds / n, v0 * (v1 / v0) ** (k / n)) for k in range(1, n + 1)]


SPEED_PLANS = {
    "1x": [(0, 1.0)],
    "16x": [(0, 16.0)],
    "0.1x": [(0, 0.1)],
    "jumps": [(0, 1.0), (20, 16.0), (40, 0.1), (60, 4.0), (70, 1.0)],
    "drags": [(0, 1.0)] + drag(15, 1.0, 16.0, 1.5) + drag(30, 16.0, 0.1, 2.0) + drag(50, 0.1, 2.0, 1.0),
}


CHECK_KEYS = ["tile_0_0", "tile_5_2", "deliver_1", "send", "refused", "returnTeam", "undo", "hint",
              "teamDone", "colourCleared", "milestone3", "complete", "newBest", "unlocked"]


def checksums(sounds):
    """Sum of |sample| per sound (float32 samples, summed in double) — SelfTest.swift compares these."""
    return {k: round(float(np.sum(np.abs(sounds[k].astype(np.float64)))), 4) for k in CHECK_KEYS}


def contact_sheet(sounds, path):
    from PIL import Image, ImageDraw
    names = list(sounds)
    cols, w, h = 4, 300, 90
    rows = (len(names) + cols - 1) // cols
    img = Image.new("RGB", (cols * w, rows * h), (30, 24, 20))
    d = ImageDraw.Draw(img)
    for i, name in enumerate(names):
        x0, y0 = (i % cols) * w, (i // cols) * h
        x = sounds[name]
        step = max(1, len(x) // (w - 20))
        env = [float(np.max(np.abs(x[j:j + step]))) for j in range(0, len(x), step)][:w - 20]
        mid = y0 + 50
        for j, v in enumerate(env):
            d.line([(x0 + 10 + j, mid - v * 32), (x0 + 10 + j, mid + v * 32)], fill=(222, 170, 90))
        d.text((x0 + 10, y0 + 4), "%s  %.2fs" % (name, len(x) / RATE), fill=(240, 230, 210))
    img.save(path)


def pan_gains(pan):
    """Equal-power pan, -1 (left) ... 1 (right)."""
    a = (pan + 1) * math.pi / 4
    return math.cos(a), math.sin(a)


def render_preview(report_path, out_dir, sounds):
    """Two listening previews made with this reference model (not recordings of the app):
    the opening of First Dig at 1x (sends, clinks, nest drops, slot chimes) and every event sound."""
    from engine import Board, Game, Scheduler
    rep = json.load(open(report_path))
    lv = next(l for l in rep["levels"] if l["key"] == "firstDig")
    board = Board(lv["rows"])
    tunnels = [[tuple(x) for x in t] for t in lv["tunnels"]]
    g = Game(board, tunnels, lv["classic"])
    sch = Scheduler(board)
    length = 26.0
    cues = []                 # (time, name, pan, gain)
    t = 0.6
    for m, q in enumerate(lv["solution"]):
        if t > length - 4:
            break
        before = len(g.state.chambers)
        sch.schedule(g.dispatch(q), m, t + 0.04)
        cues.append((t, "send", 0.0, GAINS["send"]))
        if len(g.state.chambers) > before:
            cues.append((t + 0.28, "wait", 0.0, GAINS["wait"]))
        t += 3.2
    trips = [(tr.arrive, tr.home) for tr in sch.trips]
    cols = board.C
    hole_col = board.hole % cols if hasattr(board, "hole") else cols // 2
    heard = pump_simulation(trips, [(0, 1.0)], return_heard=True)
    for kind, i, start in heard:
        tr = sch.trips[i]
        if kind == "tile":
            col = tr.claim.tile % cols
            v = i % 3
            cues.append((start, "tile_%d_%d" % (tr.claim.family % 6, v), (col / (cols - 1) * 2 - 1) * 0.7, GAINS["tile"]))
        else:
            cues.append((start, "deliver_%d" % (i % 3), (hole_col / (cols - 1) * 2 - 1) * 0.7, GAINS["deliver"]))
    last_pick = {}
    for tr in sch.trips:
        last_pick[tr.claim.team] = max(last_pick.get(tr.claim.team, 0), tr.pickup_end)
    for team, te in last_pick.items():
        if team not in {c.uid for c in g.state.chambers}:
            cues.append((te + 0.05, "teamDone", 0.0, GAINS["teamDone"]))
    mix = np.zeros((n_samples(length), 2))
    for (st, name, pan, gain) in cues:
        x = sounds[name]
        s0 = n_samples(st)
        if s0 >= len(mix):
            continue
        e = min(len(mix), s0 + len(x))
        gl, gr = pan_gains(pan)
        mix[s0:e, 0] += gain * gl * x[:e - s0]
        mix[s0:e, 1] += gain * gr * x[:e - s0]
    fade = n_samples(1.5)
    mix[-fade:] *= np.linspace(1, 0, fade)[:, None]
    write_stereo(os.path.join(out_dir, "sound_preview_first_dig.wav"), mix)
    # catalogues: the action set (plus the colony clinks) and the goal set
    def catalogue(order, path):
        gap = lambda k: 0.12 if k.startswith("tile") else 0.5
        total = sum(len(sounds[k]) / RATE + gap(k) for k in order) + 0.5
        cat = np.zeros((n_samples(total), 2))
        t = 0.3
        for k in order:
            x = sounds[k]
            gain = GAINS["tile"] * 2.2 if k.startswith("tile") else GAINS["deliver"] * 3 if k.startswith("deliver") else GAINS[k]
            s0 = n_samples(t)
            cat[s0:s0 + len(x), 0] += gain * 0.7071 * x
            cat[s0:s0 + len(x), 1] += gain * 0.7071 * x
            t += len(x) / RATE + gap(k)
        write_stereo(os.path.join(out_dir, path), cat)
    colony = ["tile_%d_1" % f for f in range(6)] + ["deliver_1"]
    catalogue(ACTION_SET + colony, "sound_set_actions.wav")
    catalogue(GOAL_SET, "sound_set_goals.wav")
    order = {"actions": ACTION_SET + colony, "goals": GOAL_SET}
    return {"preview_cues": len(cues), "preview_peak": round(float(np.abs(mix).max()), 3),
            "catalogue_order": order}


def write_stereo(path, x):
    pcm = (np.clip(x, -1, 1) * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(pcm.tobytes())


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "sounds_out"
    os.makedirs(out, exist_ok=True)
    sounds = build_all()
    report = {}
    for name, x in sounds.items():
        write_wav(os.path.join(out, name + ".wav"), x)
        report[name] = analyse(name, x)
    report["_worst_case_mix_peak_before_limiter"] = round(worst_case_mix(sounds), 3)
    report["_checksums"] = checksums(sounds)
    contact_sheet(sounds, os.path.join(out, "sounds.png"))
    if len(sys.argv) > 2:
        report["_previews"] = render_preview(sys.argv[2], out, sounds)
    json.dump(report, open(os.path.join(out, "sound_report.json"), "w"), indent=1)
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
