import SwiftUI

/// Final tally of a two-player match.
struct VersusResult {
    struct Line {
        let tiles: Int
        let bonus: Double
        let upkeep: Double
        let addedSlots: Int
        let returns: Int
        let skips: Int
        let score: Double
    }
    let lines: [Line]
    /// Nil on a draw.
    let winner: Int?
    /// Race: who cleared their mosaic first.
    let finisher: Int?
    let seconds: Double
}

/// Runs one two-player match: the rules (VersusMatch), one ant scheduler and bitmap per board,
/// a shared game clock, real-time slot occupancy, slot upkeep, scores and the end of the match.
@MainActor
final class VersusController: ObservableObject {
    static let names = ["Player 1", "Player 2"]

    let level: LevelDefinition
    let rules: VersusRules
    let match: VersusMatch
    let schedulers: [AntScheduler]
    let sprites = AntSpriteCache()
    let groundColor: UInt32
    let detailedAnts: Bool
    private(set) var rasters: [MosaicRaster?]
    private var clock = GameClock()
    private var lastTick = 0.0
    private var moveCounter = 0
    private var soundCursor = 0.0
    private weak var app: AppModel?

    @Published private(set) var speed: Double
    @Published private(set) var revision = 0
    @Published private(set) var occupied: [Int] = [0, 0]
    @Published private(set) var delivered: [Int] = [0, 0]
    @Published private(set) var scores: [Double] = [0, 0]
    @Published private(set) var messages: [String?] = [nil, nil]
    @Published private(set) var result: VersusResult?
    @Published private(set) var refusedTick = 0
    @Published private(set) var sendTick = 0
    @Published private(set) var animating = true
    /// Place the winner's score would take on this mosaic's two-player table (nil = not in the top 5).
    @Published private(set) var highScoreRank: Int?
    /// Place it took once saved under the winner's name.
    @Published private(set) var savedHighScorePlace: Int?
    private var messageExpiry: [Date] = [.distantPast, .distantPast]
    private let startDate = Date()

    init(level: LevelDefinition, rules: VersusRules, app: AppModel?) {
        self.level = level
        self.rules = rules
        self.app = app
        let m = VersusMatch(level: level, rules: rules)
        self.match = m
        let style = app?.settings.pathStyle ?? .randomTeam
        self.schedulers = m.boards.map { b in
            let s = AntScheduler(board: b.board, palette: level.palette)
            s.style = style
            return s
        }
        self.rasters = m.boards.map { _ in nil }
        self.groundColor = app?.settings.groundColor ?? GeneratedPalette.soil
        self.detailedAnts = app?.settings.detailedAnts ?? true
        let saved = app?.settings.antSpeed ?? 1.0
        self.speed = min(GameController.speedRange.upperBound, max(GameController.speedRange.lowerBound, saved))
        clock.set(speed: speed, at: Date())
        SoundBoard.shared.prepare()
    }

    // MARK: time & speed

    var now: Double { clock.time(at: Date()) }
    func gameTime(at date: Date) -> Double { clock.time(at: date) }

    func setSpeed(_ s: Double) {
        let v = min(GameController.speedRange.upperBound, max(GameController.speedRange.lowerBound, s))
        speed = v
        clock.set(speed: v, at: Date())
        SoundBoard.shared.cancelQueuedClicks()
        soundCursor = min(soundCursor, now)
    }

    // MARK: queries for the UI

    var palette: LevelPalette { level.palette }
    var boardCount: Int { match.boards.count }
    func board(_ i: Int) -> Board { match.boards[i].board }
    func capacity(_ p: Int) -> Int { match.players[p].capacity }
    func queue(_ p: Int, tunnel q: Int) -> [VTeam] { match.players[p].queues[q] }
    var tunnelCount: Int { level.tunnels.count }
    func waiting(_ p: Int) -> [VTeam] { match.waiting(p) }
    func lastFamily(_ p: Int) -> Int? { match.players[p].lastFamily }
    func penalties(_ p: Int) -> Double { match.penalties(p) }

    /// Teams of player `p` whose ants still have tiles to pick up (they hold a slot while working).
    func working(_ p: Int, at t: Double) -> [(uid: Int, family: Int, left: Int)] {
        let b = match.boardIndex(p)
        let waitingIDs = Set(match.waiting(p).map { $0.uid })
        var counts: [Int: Int] = [:]
        var fam: [Int: Int] = [:]
        for trip in schedulers[b].trips where trip.team / VersusRules.playerBase == p && trip.pickupEnd > t {
            counts[trip.team, default: 0] += 1
            fam[trip.team] = trip.family
        }
        return counts.keys.sorted().filter { !waitingIDs.contains($0) }.map { (uid: $0, family: fam[$0] ?? 0, left: counts[$0] ?? 0) }
    }

    func occupancy(_ p: Int, at t: Double) -> Int { match.waiting(p).count + working(p, at: t).count }

    /// Why a tap on this team would be refused right now (nil = it can go).
    func refusal(_ p: Int, tunnel q: Int, depth d: Int) -> String? {
        if result != nil { return "The match is over." }
        if let r = match.refusal(p, tunnel: q, depth: d) { return r }
        if occupied[p] >= capacity(p) { return "All \(capacity(p)) slots are busy." }
        return nil
    }

    // MARK: actions

    func launch(_ p: Int, tunnel q: Int, depth d: Int) {
        let t = now
        occupied[p] = occupancy(p, at: t)
        if let why = refusal(p, tunnel: q, depth: d) {
            say(p, why)
            refusedTick += 1
            SoundBoard.shared.play(.refused)
            return
        }
        let before = match.waiting(p).count
        let team = match.players[p].queues[q][d]
        let ev = match.launch(p, tunnel: q, depth: d)
        let b = match.boardIndex(p)
        schedulers[b].schedule(ev, move: moveCounter, now: t + 0.04)
        moveCounter += 1
        sendTick += 1
        SoundBoard.shared.play(.send)
        let own = ev.filter { $0.team == team.uid }.count
        var text = "\(palette.name(team.family)) team of \(team.quota) sent"
        if d > 0 { text += " (jumped \(d), −\(Int(Double(d) * VersusRules.skipPenalty)))" }
        if match.waiting(p).count > before {
            text += " — reached \(own), waiting for the rest."
            SoundBoard.shared.play(.wait, delay: 0.28)
        } else {
            text += "."
        }
        say(p, text)
        refresh(at: t)
    }

    func addSlot(_ p: Int) {
        guard result == nil else { return }
        match.addSlot(p)
        SoundBoard.shared.play(.addSlot)
        say(p, "Added a slot (−\(Int(VersusRules.addSlotPenalty))).")
        refresh(at: now)
    }

    func returnTeam(_ p: Int, uid: Int) {
        guard result == nil else { return }
        match.returnTeam(p, uid: uid)
        SoundBoard.shared.play(.returnTeam)
        say(p, "Returned a waiting team (−\(Int(VersusRules.returnPenalty))).")
        refresh(at: now)
    }

    private func say(_ p: Int, _ text: String) {
        messages[p] = text
        messageExpiry[p] = Date().addingTimeInterval(5)
    }

    // MARK: raster

    func ensureRaster(_ i: Int, cellPx: Int) {
        if let r = rasters[i], r.cellPx == cellPx { return }
        let b = match.boards[i].board
        let t = now
        var open = b.initialOpen()
        for c in 0..<b.count where b.family[c] >= 0 {
            open[c] = schedulers[i].liftTime[c] <= t
        }
        rasters[i] = MosaicRaster(board: b, palette: palette, cellPx: cellPx, open: open, soil: groundColor)
    }

    // MARK: tick (10 Hz)

    func tick() {
        let t = now
        let dt = max(0, t - lastTick)
        lastTick = t
        guard result == nil else { return }
        for i in rasters.indices { rasters[i]?.sync(liftTime: schedulers[i].liftTime, now: t) }
        for p in 0..<2 {
            let occ = occupancy(p, at: t)
            if rules.scoring == .upkeep {
                match.players[p].upkeep += VersusRules.upkeepPerSecond * Double(max(0, occ - 1)) * dt
            }
        }
        refresh(at: t)
        pumpSounds(now: t)
        for s in schedulers { s.prune(before: t - 0.5) }
        for p in 0..<2 where messages[p] != nil && Date() > messageExpiry[p] { messages[p] = nil }
        checkEnd(at: t)
    }

    private func refresh(at t: Double) {
        var occ = [0, 0]
        var home = [0, 0]
        for p in 0..<2 { occ[p] = occupancy(p, at: t) }
        for (i, vb) in match.boards.enumerated() {
            let ht = schedulers[i].homeTime
            let b = vb.board
            for c in 0..<b.count where b.family[c] >= 0 && ht[c] <= t {
                let o = Int(vb.owner[c])
                if o >= 0 && o < 2 { home[o] += 1 }
            }
        }
        if occ != occupied { occupied = occ }
        if home != delivered { delivered = home }
        let sc = [Double(home[0]) - match.penalties(0), Double(home[1]) - match.penalties(1)]
        if sc != scores { scores = sc }
        revision += 1
    }

    private func checkEnd(at t: Double) {
        var finisher: Int? = nil
        switch rules.layout {
        case .race:
            for p in 0..<2 where match.boards[p].isCleared && !schedulers[p].isBusy {
                finisher = p
                break
            }
            guard finisher != nil else { return }
        case .shared:
            let cleared = match.boards[0].isCleared || match.isStalemate
            guard cleared && !schedulers[0].isBusy else { return }
        }
        finish(finisher: finisher, at: t)
    }

    private func finish(finisher: Int?, at t: Double) {
        refresh(at: t)
        var lines: [VersusResult.Line] = []
        for p in 0..<2 {
            let pl = match.players[p]
            let bonus = (finisher == p) ? (VersusRules.finishBonusShare * Double(match.tileCount)).rounded() : 0
            let upkeep = rules.scoring == .upkeep ? pl.upkeep : 0
            let score = Double(delivered[p]) + bonus - match.penalties(p)
            lines.append(VersusResult.Line(tiles: delivered[p], bonus: bonus, upkeep: upkeep, addedSlots: pl.added,
                                           returns: pl.returns, skips: pl.skips, score: score))
        }
        let a = lines[0].score.rounded(), b = lines[1].score.rounded()
        let winner: Int? = a == b ? nil : (a > b ? 0 : 1)
        let seconds = Date().timeIntervalSince(startDate)
        result = VersusResult(lines: lines, winner: winner, finisher: finisher, seconds: seconds)
        animating = false
        SoundBoard.shared.play(.complete)
        if let w = winner {
            highScoreRank = app?.highScoreRank(.versus, levelID: level.id, score: Int(lines[w].score.rounded()), seconds: seconds)
            if highScoreRank != nil { SoundBoard.shared.play(.newBest, delay: 2.1) }
        }
    }

    /// Top two-player scores for this mosaic.
    var topScores: [HighScoreEntry] { app?.topScores(.versus, levelID: level.id) ?? [] }

    /// Puts the winner's score on the two-player table under `name`.
    func saveWinnerScore(name: String) {
        guard let r = result, let w = r.winner, highScoreRank != nil, savedHighScorePlace == nil else { return }
        let other = 1 - w
        let detail = "\(rules.layout.title) · \(rules.picking.title) · \(rules.colour.title) · \(rules.scoring.title) · beat \(Int(r.lines[other].score.rounded()))"
        let entry = HighScoreEntry(name: name, score: Int(r.lines[w].score.rounded()), seconds: r.seconds, date: Date(),
                                   difficulty: rules.difficulty, detail: detail)
        savedHighScorePlace = app?.saveHighScore(.versus, levelID: level.id, entry: entry) ?? 0
    }

    // MARK: sounds (colony clinks for every board)

    private func pumpSounds(now t: Double) {
        let horizon = t + 0.16 * speed
        let from = max(soundCursor, t - 0.3 * speed)
        soundCursor = max(soundCursor, horizon)
        let sb = SoundBoard.shared
        guard sb.isOn, sb.tileClicks, horizon > from else { return }
        let pace = max(0.01, speed)
        for (i, s) in schedulers.enumerated() {
            let b = match.boards[i].board
            let width = Double(max(1, b.cols - 1))
            // race boards sit left and right: push each board's sounds to its side
            let side = rules.layout == .race ? (i == 0 ? -0.5 : 0.5) : 0.0
            for trip in s.trips where trip.arrive > from && trip.arrive <= horizon {
                let pan = max(-1, min(1, side + (Double(Int(trip.tile) % b.cols) / width * 2 - 1) * 0.4))
                sb.tile(family: trip.family, pan: pan, delay: max(0, (trip.arrive - t) / pace))
            }
        }
    }
}
