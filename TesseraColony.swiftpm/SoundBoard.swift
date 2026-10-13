import AVFoundation
import AudioToolbox
import Foundation

/// Sound effects are synthesized in code (no audio files ship with the app). This is a line-by-line
/// mirror of Tools/sounds.py, so the in-app self-test can compare checksums with the reference.
///
/// Recipes: struck notes are damped sine partials (glass, marimba, bell, wood) plus a noise click;
/// swishes are deterministic noise through one-pole filters; glides are exponential sine sweeps.
/// Every sound is DC-removed, faded in and out, and normalised to a 0.9 peak; loudness per cue is
/// applied at play time.
enum SoundSynth {
    static let rate = 44_100.0

    struct Partial {
        let ratio: Double
        let amp: Double
        let decay: Double
        init(_ ratio: Double, _ amp: Double, _ decay: Double) {
            self.ratio = ratio
            self.amp = amp
            self.decay = decay
        }
    }

    static let glass = [Partial(1.0, 1.0, 0.07), Partial(2.76, 0.35, 0.035), Partial(5.40, 0.12, 0.02)]
    static let marimba = [Partial(1.0, 1.0, 0.25), Partial(4.0, 0.25, 0.05), Partial(9.2, 0.06, 0.02)]
    static let bell = [Partial(1.0, 1.0, 0.6), Partial(2.0, 0.4, 0.35), Partial(3.0, 0.15, 0.25),
                       Partial(4.2, 0.12, 0.15), Partial(5.4, 0.06, 0.1)]
    static let wood = [Partial(1.0, 1.0, 0.03), Partial(2.3, 0.4, 0.02)]
    static let marimbaShort = [Partial(1.0, 1.0, 0.09), Partial(4.0, 0.25, 0.03), Partial(9.2, 0.06, 0.015)]
    /// A bell with slightly detuned twins: the beating gives the goal sounds their shimmer.
    static let glassBell = bell + [Partial(1.004, 0.5, 0.5), Partial(2.006, 0.2, 0.3)]

    /// One note per colour family (major pentatonic from C5): each colour clinks at its own pitch.
    static let tileScale: [Double] = [523.25, 587.33, 659.26, 783.99, 880.00, 1046.50, 1174.66, 1318.51]
    static let tileFamilies = 6
    static let variants = 3

    /// 64-bit LCG noise (identical sequence to `Noise` in Tools/sounds.py).
    struct Noise {
        var s: UInt64
        init(_ seed: UInt64) { s = seed }
        mutating func next() -> Double {
            s = s &* 6364136223846793005 &+ 1442695040888963407
            return Double((s >> 40) & 0xFFFFFF) / 16777215.0 * 2.0 - 1.0
        }
        mutating func block(_ n: Int) -> [Double] {
            var out = [Double](repeating: 0, count: n)
            for i in 0..<n { out[i] = next() }
            return out
        }
    }

    static func samples(_ seconds: Double) -> Int { Int(seconds * rate) }

    static func strike(_ freq: Double, _ partials: [Partial], _ length: Double, click: Double = 0,
                       clickDecay: Double = 0.003, seed: UInt64 = 1, attack: Double = 0.002) -> [Double] {
        let n = samples(length)
        var out = [Double](repeating: 0, count: n)
        for p in partials {
            let f = freq * p.ratio
            if f >= rate * 0.45 { continue }
            let w = 2 * Double.pi * f
            for i in 0..<n {
                let t = Double(i) / rate
                out[i] += p.amp * exp(-t / p.decay) * sin(w * t)
            }
        }
        if click > 0 {
            var g = Noise(seed)
            let nz = highpass(g.block(n), 2000.0)
            for i in 0..<n {
                let t = Double(i) / rate
                out[i] += click * nz[i] * exp(-t / clickDecay)
            }
        }
        let a = samples(attack)
        if a > 0 {
            for i in 0..<min(a, n) { out[i] *= Double(i) / Double(a) }
        }
        return out
    }

    static func glide(_ f1: Double, _ f2: Double, _ glideTime: Double, _ decay: Double, _ length: Double,
                      harmonic2: Double = 0) -> [Double] {
        let n = samples(length)
        var out = [Double](repeating: 0, count: n)
        let a = samples(0.004)
        var acc = 0.0
        for i in 0..<n {
            let t = Double(i) / rate
            let k = min(t / glideTime, 1.0)
            acc += f1 * pow(f2 / f1, k)
            let phase = 2 * Double.pi * acc / rate
            var env = exp(-t / decay)
            if i < a { env *= Double(i) / Double(a) }
            out[i] = env * (sin(phase) + harmonic2 * sin(2 * phase))
        }
        return out
    }

    static func lowpass(_ x: [Double], _ cutoff: Double) -> [Double] {
        let a = 1.0 - exp(-2 * Double.pi * cutoff / rate)
        var y = x
        var acc = 0.0
        for i in 0..<x.count {
            acc += a * (x[i] - acc)
            y[i] = acc
        }
        return y
    }

    static func highpass(_ x: [Double], _ cutoff: Double) -> [Double] {
        let l = lowpass(x, cutoff)
        var y = x
        for i in 0..<x.count { y[i] = x[i] - l[i] }
        return y
    }

    static func swish(_ length: Double, cutoff: Double, rise: Double, decay: Double, seed: UInt64,
                      reverse: Bool = false) -> [Double] {
        let n = samples(length)
        var g = Noise(seed)
        let nz = lowpass(g.block(n), cutoff)
        var env = [Double](repeating: 0, count: n)
        for i in 0..<n {
            let t = Double(i) / rate
            if reverse {
                env[i] = t > rise ? 0 : exp((t - rise) / (rise / 4.0))
            } else {
                env[i] = t < rise ? t / rise : exp(-(t - rise) / decay)
            }
        }
        if reverse {
            let cut = min(samples(rise), n)
            let fade = min(samples(0.004), cut)
            if fade > 0 {
                for j in 0..<fade {
                    let w = fade > 1 ? 1.0 - Double(j) / Double(fade - 1) : 1.0
                    env[cut - fade + j] *= w
                }
            }
        }
        var out = nz
        for i in 0..<n { out[i] = nz[i] * env[i] }
        return out
    }

    struct Part {
        let offset: Double
        let samples: [Double]
        let gain: Double
        init(_ offset: Double, _ samples: [Double], _ gain: Double) {
            self.offset = offset
            self.samples = samples
            self.gain = gain
        }
    }

    static func place(_ total: Double, _ parts: [Part]) -> [Double] {
        var out = [Double](repeating: 0, count: samples(total))
        for p in parts {
            let s = samples(p.offset)
            let e = min(out.count, s + p.samples.count)
            if e > s {
                for i in s..<e { out[i] += p.gain * p.samples[i - s] }
            }
        }
        return out
    }

    /// Adds `taps` delayed copies, each `feedback` times quieter (a small hall shimmer).
    static func echo(_ x: [Double], _ delay: Double, _ feedback: Double, _ taps: Int) -> [Double] {
        let d = samples(delay)
        var out = [Double](repeating: 0, count: x.count + max(0, taps) * d)
        for i in 0..<x.count { out[i] += x[i] }
        var g = 1.0
        var k = 1
        while k <= taps {
            g *= feedback
            let off = k * d
            for i in 0..<x.count { out[off + i] += g * x[i] }
            k += 1
        }
        return out
    }

    static func finish(_ input: [Double], peak: Double = 0.9) -> [Float] {
        var x = input
        let n = x.count
        guard n > 0 else { return [] }
        let mean = x.reduce(0, +) / Double(n)
        for i in 0..<n { x[i] -= mean }
        let fi = samples(0.002)
        for i in 0..<min(fi, n) { x[i] *= Double(i) / Double(fi) }
        let fo = min(n, max(samples(0.012), Int(Double(n) * 0.25)))
        for j in 0..<fo {
            let u = fo > 1 ? Double(j) / Double(fo - 1) : 0
            x[n - fo + j] *= 0.5 * (1 + cos(Double.pi * u))
        }
        var m = 0.0
        for v in x { m = max(m, abs(v)) }
        let k = m > 0 ? peak / m : 0
        return x.map { Float($0 * k) }
    }

    // MARK: the sound set

    static func tile(family f: Int, variant v: Int) -> [Float] {
        let freq = tileScale[f] * (1 + Double(v - 1) * 0.012)
        return finish(strike(freq, glass, 0.22, click: 0.18, seed: UInt64(11 + f * 3 + v)))
    }

    static func deliver(variant v: Int) -> [Float] {
        let f = 380.0 * (1 + Double(v - 1) * 0.03)
        let body = strike(f, wood, 0.12, seed: UInt64(40 + v))
        let n = samples(0.12)
        var g = Noise(UInt64(50 + v))
        let lp = lowpass(g.block(n), 2500.0)
        var x = body
        for i in 0..<n { x[i] += 0.5 * lp[i] * exp(-(Double(i) / rate) / 0.006) }
        return finish(x)
    }

    static func cue(_ c: SoundCue) -> [Float] {
        switch c {
        // ---- ACTION set: wood and clay ----
        case .send:
            return finish(place(0.28, [Part(0.0, strike(330.0, wood, 0.12, click: 0.25, seed: 61), 0.8),
                                       Part(0.0, swish(0.28, cutoff: 1500.0, rise: 0.02, decay: 0.06, seed: 62), 0.45),
                                       Part(0.01, glide(200.0, 120.0, 0.12, 0.06, 0.2), 0.6)]))
        case .scout:
            return finish(place(0.2, [Part(0.0, strike(660.0, wood, 0.08, click: 0.1, seed: 91), 0.6),
                                      Part(0.06, strike(880.0, wood, 0.08, click: 0.1, seed: 92), 0.5)]))
        case .undo:
            return finish(place(0.2, [Part(0.0, swish(0.2, cutoff: 3000.0, rise: 0.09, decay: 0.05, seed: 81, reverse: true), 0.7),
                                      Part(0.09, strike(520.0, wood, 0.11, click: 0.2, seed: 82), 0.6)]))
        case .addSlot:
            return finish(place(0.3, [Part(0.0, strike(392.0, marimbaShort, 0.16), 0.7),
                                      Part(0.08, strike(523.25, marimbaShort, 0.2), 0.8)]))
        case .returnTeam:
            return finish(place(0.35, [Part(0.0, glide(520.0, 260.0, 0.12, 0.08, 0.3, harmonic2: 0.25), 0.6),
                                       Part(0.11, strike(261.63, marimbaShort, 0.22), 0.7)]))
        case .refused:
            let thud = strike(140.0, [Partial(1.0, 1.0, 0.05), Partial(2.0, 0.2, 0.03)], 0.15,
                              click: 0.3, clickDecay: 0.004, seed: 71)
            return finish(place(0.3, [Part(0.0, thud, 1.0), Part(0.11, thud, 0.8)]))
        case .wait:
            return finish(place(0.45, [Part(0.0, strike(329.63, marimba, 0.3), 1.0),
                                       Part(0.12, strike(246.94, marimba, 0.32), 0.9)]))
        case .blocked:
            return finish(place(0.8, [Part(0.0, strike(220.0, marimba, 0.68), 0.8),
                                      Part(0.06, strike(261.63, marimba, 0.68), 0.8),
                                      Part(0.12, strike(329.63, marimba, 0.68), 0.8)]))
        case .hint:
            return finish(place(0.4, [Part(0.0, strike(440.0, marimbaShort, 0.25), 0.7),
                                      Part(0.09, strike(587.33, marimbaShort, 0.3), 0.7)]))
        // ---- GOAL set: bells and glass ----
        case .teamDone:
            return finish(echo(place(0.7, [Part(0.0, strike(783.99, glassBell, 0.6), 0.55),
                                           Part(0.08, strike(1174.66, glassBell, 0.62), 0.55)]), 0.11, 0.3, 2))
        case .colourCleared:
            return finish(echo(place(0.9, [Part(0.0, strike(1046.50, glassBell, 0.8), 0.45),
                                           Part(0.07, strike(1318.51, glassBell, 0.8), 0.45),
                                           Part(0.14, strike(1567.98, glassBell, 0.76), 0.45),
                                           Part(0.14, strike(523.25, bell, 0.76), 0.3)]), 0.12, 0.35, 3))
        case .milestone1, .milestone2, .milestone3:
            let notes: [Double]
            switch c {
            case .milestone1: notes = [523.25, 587.33, 659.26, 783.99]
            case .milestone2: notes = [659.26, 783.99, 880.00, 1046.50]
            default: notes = [783.99, 880.00, 1046.50, 1174.66, 1318.51]
            }
            var parts: [Part] = []
            for (k, f) in notes.enumerated() { parts.append(Part(Double(k) * 0.07, strike(f, glassBell, 0.7), 0.42)) }
            return finish(echo(place(1.0, parts), 0.12, 0.3, 2))
        case .complete:
            let arp: [Double] = [523.25, 659.26, 783.99, 1046.50, 1318.51, 1567.98]
            var parts: [Part] = []
            for (k, f) in arp.enumerated() { parts.append(Part(Double(k) * 0.085, strike(f, bell, 1.2), 0.45)) }
            let longBell = bell.map { Partial($0.ratio, $0.amp, $0.decay * 2.2) }
            for f in [523.25, 783.99, 1046.50, 1318.51] { parts.append(Part(0.6, strike(f, longBell, 1.6), 0.3)) }
            return finish(echo(place(2.2, parts), 0.13, 0.28, 2))
        case .newBest:
            var parts: [Part] = []
            for (k, f) in [1046.50, 1318.51, 1567.98, 2093.0].enumerated() {
                parts.append(Part(Double(k) * 0.06, strike(f, glassBell, 0.7), 0.45))
            }
            return finish(echo(place(0.9, parts), 0.1, 0.3, 2))
        case .unlocked:
            let sparkle: [Double] = [1046.50, 1174.66, 1318.51, 1567.98, 1760.00, 2093.0, 2349.32, 2637.02]
            var parts: [Part] = []
            for (k, f) in sparkle.enumerated() {
                parts.append(Part(Double(k) * 0.045, strike(f, glass, 0.25, seed: UInt64(120 + k)), 0.35))
            }
            let longBell = bell.map { Partial($0.ratio, $0.amp, $0.decay * 2.2) }
            for f in [523.25, 659.26, 783.99] { parts.append(Part(0.4, strike(f, longBell, 1.2), 0.3)) }
            return finish(echo(place(1.6, parts), 0.12, 0.3, 2))
        }
    }

    /// Every sound, keyed like the reference WAV files ("tile_2_1", "deliver_0", "send", ...).
    static func buildAll() -> [String: [Float]] {
        var out: [String: [Float]] = [:]
        for f in 0..<tileFamilies {
            for v in 0..<variants { out["tile_\(f)_\(v)"] = tile(family: f, variant: v) }
        }
        for v in 0..<variants { out["deliver_\(v)"] = deliver(variant: v) }
        for c in SoundCue.allCases { out[c.rawValue] = cue(c) }
        return out
    }

    /// Sum of |sample| — compared with the reference model in the self-test.
    static func checksum(_ x: [Float]) -> Double {
        var s = 0.0
        for v in x { s += Double(abs(v)) }
        return s
    }
}

/// Which set a sound belongs to (each has its own switch in Settings).
enum SoundSet: String, CaseIterable {
    /// Dry wood and clay: the moves the player makes.
    case action
    /// Bright bells and glass: goals reached.
    case goal
}

/// The event sounds (tile clinks and nest drops are the separate "colony" layer, see
/// `SoundBoard.tile` / `deliver`).
enum SoundCue: String, CaseIterable {
    // action set
    case send, scout, undo, addSlot, returnTeam, refused, wait, blocked, hint
    // goal set
    case teamDone, colourCleared, milestone1, milestone2, milestone3, complete, newBest, unlocked

    var set: SoundSet {
        switch self {
        case .teamDone, .colourCleared, .milestone1, .milestone2, .milestone3, .complete, .newBest, .unlocked:
            return .goal
        default:
            return .action
        }
    }

    var gain: Float {
        switch self {
        case .send: return 0.5
        case .scout: return 0.3
        case .undo: return 0.35
        case .addSlot: return 0.45
        case .returnTeam: return 0.4
        case .refused: return 0.55
        case .wait: return 0.45
        case .blocked: return 0.45
        case .hint: return 0.4
        case .teamDone: return 0.38
        case .colourCleared: return 0.45
        case .milestone1, .milestone2, .milestone3: return 0.42
        case .complete: return 0.55
        case .newBest: return 0.5
        case .unlocked: return 0.5
        }
    }

    static func members(of set: SoundSet) -> [SoundCue] { allCases.filter { $0.set == set } }
}

/// Plays the synthesized effects through a small pool of voices.
///
/// * Audio session category `.playback` with `.mixWithOthers` by default, so the game is heard even
///   when the iPad is in Silent mode and still mixes with the player's music. Settings can switch to
///   `.ambient` (sounds follow Silent mode).
/// * Tile clicks are scheduled against the game clock a fraction of a second ahead, with
///   sample-accurate start times, so they land exactly when an ant lifts a tile (at any speed).
/// * Throttled: at most ~20 tile clicks and ~12 nest drops a second, one of each other cue per 90 ms,
///   and gains chosen so the loudest plausible moment stays below full scale (measured: 0.82).
@MainActor
final class SoundBoard {
    static let shared = SoundBoard()

    static let tileGain: Float = 0.22
    static let deliverGain: Float = 0.12
    static let voiceCount = 14

    private(set) var isOn = true
    private(set) var tileClicks = true
    private(set) var actionSounds = true
    private(set) var goalSounds = true
    private var volume: Float = 0.8

    private var engine: AVAudioEngine?
    private var submix: AVAudioMixerNode?
    private var voices: [AVAudioPlayerNode] = []
    private var busyUntil: [Double] = []
    /// When each voice's current sound starts, and whether it is a tile clink / nest drop.
    private var voiceStart: [Double] = []
    private var voiceIsClick: [Bool] = []
    private var buffers: [String: AVAudioPCMBuffer] = [:]
    private var building = false
    private var lastCue: [SoundCue: Double] = [:]
    private var lastTile = -1.0
    private var lastDeliver = -1.0
    private var counter = 0
    private var lastFailedStart = -100.0
    /// Play even when the iPad is in Silent mode (`.playback`); otherwise follow it (`.ambient`).
    private(set) var ignoresSilentMode = true
    /// Last audio error (shown by the Sound check in Settings).
    private(set) var lastError: String?
    /// How many sounds have been started since launch (Sound check).
    private(set) var startedCount = 0
    private let monoFormat = AVAudioFormat(standardFormatWithSampleRate: SoundSynth.rate, channels: 1)

    private init() {}

    /// Called with the saved settings at launch and whenever they change.
    func configure(on: Bool, volume v: Double, tileClicks t: Bool, actions: Bool = true, goals: Bool = true,
                   ignoreSilentMode: Bool = true) {
        if ignoreSilentMode != ignoresSilentMode {
            ignoresSilentMode = ignoreSilentMode
            engine?.stop()          // restarts on the next sound with the new session category
        }
        isOn = on
        tileClicks = t
        actionSounds = actions
        goalSounds = goals
        volume = Float(max(0, min(1, v)))
        submix?.outputVolume = volume
        if on {
            prepare()
        } else {
            silence()
        }
    }

    /// Synthesizes every sound in the background (about a tenth of a second), once.
    func prepare() {
        guard buffers.isEmpty, !building else { return }
        building = true
        Task { [weak self] in
            let all = await Task.detached(priority: .utility) { SoundSynth.buildAll() }.value
            self?.install(all)
        }
    }

    private func install(_ all: [String: [Float]]) {
        for (key, samples) in all {
            if let b = pcm(samples) { buffers[key] = b }
        }
        building = false
    }

    // MARK: playing

    func play(_ cue: SoundCue, delay: Double = 0) {
        guard isOn, cue.set == .action ? actionSounds : goalSounds, let b = buffers[cue.rawValue] else { return }
        let now = SoundBoard.hostSeconds()
        if let last = lastCue[cue], now - last < 0.09 { return }
        if start(b, gain: cue.gain, pan: 0, delay: delay, click: false) { lastCue[cue] = now }
    }

    /// Plays every sound of a set one after another (the "Play a sample" buttons in Settings).
    /// Plays even if that set is switched off, so it can be auditioned.
    func playSample(_ set: SoundSet) {
        guard isOn else { return }
        var t = 0.05
        for cue in SoundCue.members(of: set) {
            guard let b = buffers[cue.rawValue] else { continue }
            _ = start(b, gain: cue.gain, pan: 0, delay: t, click: false)
            t += Double(b.frameLength) / SoundSynth.rate * (set == .goal ? 0.75 : 1.0) + 0.3
        }
    }

    /// An ant lifts a tile of colour `family`; `pan` is -1 (left) ... 1 (right).
    func tile(family: Int, pan: Double, delay: Double) {
        guard isOn, tileClicks else { return }
        let at = SoundBoard.hostSeconds() + max(0, delay)
        if at - lastTile < 0.05 { return }
        counter += 1
        let f = ((family % SoundSynth.tileFamilies) + SoundSynth.tileFamilies) % SoundSynth.tileFamilies
        guard let b = buffers["tile_\(f)_\(counter % SoundSynth.variants)"] else { return }
        if start(b, gain: SoundBoard.tileGain, pan: Float(pan), delay: delay, click: true) { lastTile = at }
    }

    /// An ant drops its tile in the nest.
    func deliver(pan: Double, delay: Double) {
        guard isOn, tileClicks else { return }
        let at = SoundBoard.hostSeconds() + max(0, delay)
        if at - lastDeliver < 0.08 { return }
        counter += 1
        guard let b = buffers["deliver_\(counter % SoundSynth.variants)"] else { return }
        if start(b, gain: SoundBoard.deliverGain, pan: Float(pan), delay: delay, click: true) { lastDeliver = at }
    }

    /// Drops tile clinks and nest drops queued for the future: their start times assumed the old
    /// ant speed. The game hands them over again at the new speed on its next tick.
    func cancelQueuedClicks() {
        let now = SoundBoard.hostSeconds()
        for k in voices.indices where voiceIsClick[k] && voiceStart[k] > now {
            voices[k].stop()
            busyUntil[k] = 0
            voiceStart[k] = 0
        }
        lastTile = min(lastTile, now)
        lastDeliver = min(lastDeliver, now)
    }

    /// Stops everything that is playing or queued.
    func silence() {
        for v in voices { v.stop() }
        for k in busyUntil.indices { busyUntil[k] = 0 }
        engine?.pause()
    }

    // MARK: engine

    static func hostSeconds() -> Double { AVAudioTime.seconds(forHostTime: mach_absolute_time()) }

    private func start(_ buffer: AVAudioPCMBuffer, gain: Float, pan: Float, delay: Double, click: Bool) -> Bool {
        guard ensureRunning(), let e = engine else { return false }
        let hostNow = mach_absolute_time()
        let now = AVAudioTime.seconds(forHostTime: hostNow)
        guard let k = busyUntil.indices.first(where: { busyUntil[$0] <= now }), k < voices.count else { return false }
        let v = voices[k]
        // a player node may only start while its engine runs (iOS stops the engine on its own when the
        // audio route changes or another app interrupts); playing it then would stop the app
        guard e.isRunning, v.engine != nil else { return false }
        let d = delay.isFinite ? min(5, max(0, delay)) : 0
        busyUntil[k] = now + d + Double(buffer.frameLength) / SoundSynth.rate + 0.03
        voiceStart[k] = now + d
        voiceIsClick[k] = click
        v.volume = gain
        v.pan = max(-1, min(1, pan))
        if !v.isPlaying { v.play() }
        if d < 0.004 {
            v.scheduleBuffer(buffer, at: nil, options: [], completionHandler: nil)
        } else {
            let when = AVAudioTime(hostTime: hostNow + AVAudioTime.hostTime(forSeconds: d))
            v.scheduleBuffer(buffer, at: when, options: [], completionHandler: nil)
        }
        startedCount += 1
        return true
    }

    private func ensureRunning() -> Bool {
        if engine == nil { build() }
        guard let e = engine else { return false }
        if e.isRunning { return true }
        let now = SoundBoard.hostSeconds()
        if now - lastFailedStart < 2 { return false }     // don't hammer a failing audio system
        let session = AVAudioSession.sharedInstance()
        do {
            if ignoresSilentMode {
                try session.setCategory(.playback, mode: .default, options: [.mixWithOthers])
            } else {
                try session.setCategory(.ambient, mode: .default, options: [.mixWithOthers])
            }
            try session.setActive(true)
        } catch {
            lastError = "Audio session: \(error.localizedDescription)"
        }
        do {
            try e.start()
        } catch {
            lastFailedStart = now
            lastError = "Audio engine didn't start: \(error.localizedDescription)"
            return false
        }
        for v in voices { v.play() }
        for k in busyUntil.indices { busyUntil[k] = 0 }
        return true
    }

    private func build() {
        guard let mono = monoFormat else { return }
        let e = AVAudioEngine()
        let sub = AVAudioMixerNode()
        e.attach(sub)
        for _ in 0..<SoundBoard.voiceCount {
            let p = AVAudioPlayerNode()
            e.attach(p)
            e.connect(p, to: sub, format: mono)
            voices.append(p)
            busyUntil.append(0)
            voiceStart.append(0)
            voiceIsClick.append(false)
        }
        let stereo = AVAudioFormat(standardFormatWithSampleRate: SoundSynth.rate, channels: 2)
        e.connect(sub, to: e.mainMixerNode, format: stereo)
        sub.outputVolume = volume
        e.prepare()
        engine = e
        submix = sub
    }

    // MARK: sound check (Settings)

    struct Status {
        let enabled: Bool
        let soundsReady: Int
        let engineRunning: Bool
        let category: String
        let outputs: String
        let deviceVolume: Float
        let started: Int
        let error: String?
    }

    /// Everything the Sound check shows.
    func status() -> Status {
        let session = AVAudioSession.sharedInstance()
        let outs = session.currentRoute.outputs.map { $0.portName }.joined(separator: ", ")
        return Status(enabled: isOn, soundsReady: buffers.count, engineRunning: engine?.isRunning ?? false,
                      category: session.category.rawValue.replacingOccurrences(of: "AVAudioSessionCategory", with: ""),
                      outputs: outs.isEmpty ? "none" : outs, deviceVolume: session.outputVolume,
                      started: startedCount, error: lastError)
    }

    /// A clear two-note chime, ignoring the per-set switches (for the Sound check).
    @discardableResult
    func playTestSound() -> Bool {
        guard isOn else { return false }
        if buffers.isEmpty { prepare(); return false }
        guard let b = buffers[SoundCue.teamDone.rawValue] else { return false }
        return start(b, gain: 0.8, pan: 0, delay: 0, click: false)
    }

    private func pcm(_ samples: [Float]) -> AVAudioPCMBuffer? {
        guard let fmt = monoFormat, !samples.isEmpty,
              let b = AVAudioPCMBuffer(pcmFormat: fmt, frameCapacity: AVAudioFrameCount(samples.count)),
              let ch = b.floatChannelData?[0] else { return nil }
        b.frameLength = AVAudioFrameCount(samples.count)
        for i in 0..<samples.count { ch[i] = samples[i] }
        return b
    }
}
