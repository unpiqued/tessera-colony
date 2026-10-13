import SwiftUI
import Combine

/// Game clock. The speed slider changes `speed`; re-anchoring keeps game time continuous,
/// so ants already walking simply slow down or speed up — they never jump or restart.
struct GameClock {
    var anchorDate = Date()
    var anchorTime = 0.0
    var speed = 1.0
    func time(at d: Date) -> Double { anchorTime + d.timeIntervalSince(anchorDate) * speed }
    mutating func set(speed s: Double, at d: Date) {
        anchorTime = time(at: d)
        anchorDate = d
        speed = s
    }
}

enum CoachStep: String, CaseIterable {
    case tapTeam, watchAnts, chamber, slotsFull, scout, jam, showcaseIntro, photoIntro

    var title: String {
        switch self {
        case .tapTeam: return "Send out a team"
        case .watchAnts: return "Each team takes a slot"
        case .chamber: return "A team is waiting"
        case .slotsFull: return "All slots are busy"
        case .scout: return "Scout before you send"
        case .jam: return "The colony is blocked"
        case .showcaseIntro: return "6,048 tiles to carry home"
        case .photoIntro: return "Your photo is now a mosaic"
        }
    }

    var message: String {
        switch self {
        case .tapTeam:
            return "Tap the team at the front of a tunnel. Its ants crawl out of the hill and fetch every reachable tile of their colour. Each tap sends the next team in line."
        case .watchAnts:
            return "A sent team occupies a slot, counting down until its ants have picked up every tile. While slots are open you can send more teams, and they all work at once."
        case .chamber:
            return "That team couldn't reach all its tiles, so it keeps its slot and waits. It resumes by itself when its colour is uncovered — there's nothing else to do to make a team wait."
        case .slotsFull:
            return "A team can only be sent into an open slot. Wait for a working team to finish, or use the speed slider to hurry the ants."
        case .scout:
            return "Press and hold a team to scout it: the tiles it would take light up and you'll see whether it would have to wait."
        case .jam:
            return "Every slot holds a team that's waiting for tiles it can't reach. Undo is free, or add a slot, or tap a waiting team to return it to its tunnel."
        case .showcaseIntro:
            return "Ants can only reach tiles touching open ground, so peel the frame first. Pinch the board to zoom in on the ants; hold a team to scout."
        case .photoIntro:
            return "White areas of your photo became open ground. Every coloured tile is part of the puzzle, and the teams were built so the mosaic can be cleared."
        }
    }
}

/// What one slot shows.
enum SlotContent: Equatable {
    case open
    /// Sent team whose ants are still picking up tiles.
    case working(uid: Int, family: Int, toCollect: Int)
    /// Team that couldn't reach all its tiles; it keeps working as tiles are uncovered.
    case waiting(chamber: Int, uid: Int, family: Int, toCollect: Int)
    /// Team parked with Hold in an earlier version (only appears when an old save is restored).
    case held(chamber: Int, uid: Int, family: Int, need: Int)
}

struct SlotItem: Identifiable, Equatable {
    let id: Int
    let content: SlotContent
}

/// Owns one play session: rules engine, ant scheduler, raster, clock, slots, hints, saving.
@MainActor
final class GameController: ObservableObject {
    static let speedRange: ClosedRange<Double> = 0.1...16.0

    let level: LevelDefinition
    let board: Board
    let difficulty: Difficulty
    /// Harder options chosen on the start card (fixed for the whole game).
    let modifiers: Set<ChallengeModifier>
    var palette: LevelPalette { level.palette }
    let sprites = AntSpriteCache()
    private(set) var game: Game
    private(set) var scheduler: AntScheduler
    private(set) var raster: MosaicRaster?
    private(set) var miniImage: CGImage?
    private var miniShown: [Bool]
    private var miniDirty = false
    private var miniBuiltAt = Date.distantPast
    private var clock = GameClock()
    private weak var app: AppModel?
    private var slotOwners: [Int?] = []

    @Published private(set) var revision = 0
    @Published private(set) var deliveredCount = 0
    @Published private(set) var animating = false
    @Published private(set) var scout: ScoutReport?
    @Published private(set) var hint: HintResult?
    @Published private(set) var hintBusy = false
    @Published private(set) var visuallyComplete = false
    @Published private(set) var coach: CoachStep?
    @Published private(set) var speed = 1.0
    @Published private(set) var undos = 0
    @Published private(set) var hintsUsed = 0
    @Published private(set) var hapticTick = 0
    @Published private(set) var refusedTick = 0
    @Published private(set) var fitBadges: [Bool?] = []
    @Published private(set) var slots: [SlotItem] = []
    @Published private(set) var occupiedSlots = 0
    @Published private(set) var blocked = false
    /// Real seconds until the next busy slot frees (nil when a slot is open or none is working).
    @Published private(set) var nextFreeSeconds: Double?
    /// One-line description of what the last action did (clears itself after a few seconds).
    @Published private(set) var eventText: String?
    @Published private(set) var groundColor: UInt32
    private var eventExpiry = Date.distantPast
    @Published var detailedAnts = true
    @Published private(set) var soundOn = true
    /// How newly launched ants choose their route (Settings / in-game menu).
    @Published private(set) var pathStyle: PathStyle = .randomTeam
    /// Game time up to which tile clicks / nest drops have been handed to the SoundBoard.
    private var soundCursor = 0.0
    /// Ant speed the queued clicks were timed for.
    private var soundSpeed = 1.0
    /// False while the controller is being set up (no sounds for a restored state).
    private var soundsLive = false
    /// Tiles of each colour family not yet lifted (for the "colour cleared" goal sound).
    private var familyLeft: [Int] = []
    /// Quarter milestones already celebrated (0...3).
    private var milestone = 0
    /// What the finish achieved (new best, unlocked mosaics), shown on the win card.
    @Published private(set) var completionNews: CompletionNews?
    /// The finished game's score (set when the mosaic is complete).
    @Published private(set) var scoreBreakdown: ScoreRules.Breakdown?
    /// Place that score would take on this mosaic's high-score table (nil = not in the top 5).
    @Published private(set) var highScoreRank: Int?
    /// Place it took once saved under a name.
    @Published private(set) var savedHighScorePlace: Int?
    /// Colour family sent by each entry of game.moves (-1 for assists), for No colour twice.
    private var moveFamilies: [Int] = []
    private(set) var elapsed = 0.0
    private var scoutSet: Set<Int32> = []
    /// When the flight recorder last got a status line (see FlightRecorder.swift).
    private var flightStatusAt = Date.distantPast

    init(level: LevelDefinition, difficulty: Difficulty, modifiers: Set<ChallengeModifier> = [],
         app: AppModel?, resume save: SaveGame?) {
        self.level = level
        self.difficulty = difficulty
        self.modifiers = modifiers
        self.app = app
        let b = Board(art: level.art)
        self.board = b
        let cap = level.chambers(for: difficulty)
        var g = Game(level: level, board: b, capacity: cap)
        var restoredUndos = 0
        var restoredHints = 0
        var restoredElapsed = 0.0
        if let s = save, let rg = Game.replay(level: level, board: b, capacity: cap, moves: s.moves) {
            g = rg
            restoredUndos = s.undos
            restoredHints = s.hints
            restoredElapsed = s.elapsed
        }
        self.game = g
        self.moveFamilies = GameController.families(level: level, board: b, capacity: cap, moves: g.moves)
        let sch = AntScheduler(board: b, palette: level.palette)
        for claims in g.moveClaims { sch.completeInstantly(claims) }
        self.scheduler = sch
        self.miniShown = [Bool](repeating: false, count: b.count)
        self.groundColor = app?.settings.groundColor ?? GeneratedPalette.soil
        self.undos = restoredUndos
        self.hintsUsed = restoredHints
        self.elapsed = restoredElapsed
        self.detailedAnts = app?.settings.detailedAnts ?? true
        let savedSpeed = app?.settings.antSpeed ?? 1.0
        self.speed = min(GameController.speedRange.upperBound, max(GameController.speedRange.lowerBound, savedSpeed))
        clock.set(speed: speed, at: Date())
        self.soundOn = app?.settings.soundOn ?? true
        self.pathStyle = app?.settings.pathStyle ?? .randomTeam
        scheduler.style = pathStyle
        refreshMiniature(force: true)
        refreshFitBadges()
        refreshSlots(at: now)
        startCoachIfNeeded()
        soundCursor = now
        soundSpeed = speed
        milestone = board.tileCount == 0 ? 0 : min(3, deliveredCount * 4 / board.tileCount)
        checkGoals(at: now)
        soundsLive = true
        SoundBoard.shared.prepare()
        beginFlightRecord(resumed: save != nil && !game.moves.isEmpty)
    }

    // MARK: - Flight recorder (what happened just before an unexpected stop)

    private func beginFlightRecord(resumed: Bool) {
        let mods = ChallengeModifier.sorted(modifiers).map { $0.title }
        let os = ProcessInfo.processInfo.operatingSystemVersionString
        FlightRecorder.shared.begin([
            "Mosaic: \(level.title) [\(level.id)] · \(difficulty.title) · \(capacity) slots · \(board.tileCount) tiles",
            "Harder options: " + (mods.isEmpty ? "none" : mods.joined(separator: ", ")),
            "Ant paths: \(pathStyle.title) · speed \(String(format: "%.2f", speed))× · detailed legs \(detailedAnts ? "on" : "off") · sound \(soundOn ? "on" : "off")",
            "Started: \(Date()) · iPadOS/iOS \(os)",
            resumed ? "Resumed a saved game (\(game.moves.count) moves replayed)" : "New game"
        ], moves: game.moves)
    }

    /// One line in the flight record.
    private func flight(_ text: String) {
        FlightRecorder.shared.note(text, time: now, moves: game.moves)
    }

    private func flightStatus(at t: Double) {
        var waiting = 0
        for c in game.state.chambers where !c.held { waiting += 1 }
        let s = String(format: "game time %.1f s · ", t)
            + "\(claimedCount)/\(board.tileCount) tiles claimed · \(deliveredCount) home · \(scheduler.trips.count) ants out · "
            + "\(occupiedSlots)/\(capacity) slots busy (\(waiting) waiting) · blocked \(isBlocked ? "yes" : "no") · "
            + "speed \(String(format: "%.2f", speed))× · paths \(pathStyle.title) · \(undos) undos · \(hintsUsed) hints"
        FlightRecorder.shared.update(status: s, moves: game.moves)
    }

    // MARK: - Time & speed

    var now: Double { clock.time(at: Date()) }
    func gameTime(at date: Date) -> Double { clock.time(at: date) }

    /// Live speed change from the slider: ants keep their place and just move slower/faster.
    func setSpeed(_ s: Double) {
        let v = min(GameController.speedRange.upperBound, max(GameController.speedRange.lowerBound, s))
        speed = v
        clock.set(speed: v, at: Date())
        // Clicks are queued up to 0.16 s ahead, timed for the speed at that moment. After a real
        // change (more than 25%), drop the queued ones and hand them over again at the new speed.
        if abs(log(v / soundSpeed)) > log(1.25) {
            SoundBoard.shared.cancelQueuedClicks()
            soundCursor = min(soundCursor, now)
            soundSpeed = v
        }
    }

    /// Remember the speed for next time (called when the slider is released).
    func commitSpeed() {
        app?.settings.antSpeed = speed
        flight("speed \(String(format: "%.2f", speed))×")
    }

    // MARK: - Ground colour (the background behind the mosaic)

    func setGround(_ color: UInt32) {
        guard color != groundColor else { return }
        groundColor = color
        raster = nil            // rebuilt on the next frame with the new colour
        app?.settings.groundColor = color
        animating = true
    }

    // MARK: - Derived state for the UI

    var tunnelCount: Int { game.tunnels.count }
    func front(_ q: Int) -> FrontTeam? { game.front(q) }
    func upcoming(_ q: Int, count: Int = 3) -> [TeamSpec] { game.upcoming(q, count: count) }
    /// Every team still waiting in tunnel `q`, front first.
    func fullQueue(_ q: Int) -> [TeamSpec] {
        var out: [TeamSpec] = []
        if let f = game.front(q) { out.append(TeamSpec(f.family, f.need)) }
        out.append(contentsOf: game.upcoming(q, count: 10_000))
        return out
    }
    func remaining(_ q: Int) -> Int { game.remainingInTunnel(q) }
    var chambers: [Team] { game.state.chambers }
    var capacity: Int { game.state.capacity }
    var addedChambers: Int { game.state.added }
    var jammedTeam: Team? { game.state.jammed }
    var isJammed: Bool { game.isJammed }
    /// Blocked: every slot holds a waiting team (or a legacy jam from an old save).
    var isBlocked: Bool { blocked || game.isJammed }
    var hasOpenSlot: Bool { occupiedSlots < capacity }
    var canUndo: Bool { game.canUndo && (undosLeft ?? 1) > 0 }
    /// Undos still allowed with the 3-undos option (nil = unlimited).
    var undosLeft: Int? {
        modifiers.contains(.limitedUndo) ? max(0, ChallengeModifier.undoLimit - undos) : nil
    }
    var hintsAllowed: Bool { !modifiers.contains(.noHints) }
    var scoutAllowed: Bool { !modifiers.contains(.noScout) }
    var assistsAllowed: Bool { !modifiers.contains(.noAssists) }
    var queueHidden: Bool { modifiers.contains(.hiddenQueue) }
    /// Score multiplier from difficulty and harder options (shown in the panel).
    var scoreFactor: Double { ScoreRules.difficultyFactor(difficulty) * ScoreRules.modifierFactor(modifiers) }
    var isLogicallyWon: Bool { game.isWon }
    var moveCount: Int { game.moves.filter { !Game.isAssist($0) }.count }
    var assistCount: Int { game.moves.filter { Game.isAssist($0) }.count }
    var claimedCount: Int { game.state.cleared }
    var progress: Double { board.tileCount == 0 ? 0 : Double(deliveredCount) / Double(board.tileCount) }
    var scoutTiles: Set<Int32> { scoutSet }

    func canSend(_ q: Int) -> Bool { game.canDispatch(q) && hasOpenSlot && colourRefusal(q) == nil }

    /// The colour of the last team sent (No colour twice).
    var lastSentFamily: Int? {
        if moveFamilies.count != game.moves.count {
            moveFamilies = GameController.families(level: level, board: board, capacity: level.chambers(for: difficulty), moves: game.moves)
        }
        return moveFamilies.last(where: { $0 >= 0 })
    }

    /// Why No colour twice refuses tunnel `q` right now (nil = allowed). The same colour is allowed
    /// when no other tunnel can send a different colour.
    func colourRefusal(_ q: Int) -> String? {
        guard modifiers.contains(.noRepeatColour), let last = lastSentFamily,
              ColourRule.refuses(game: game, tunnel: q, last: last) else { return nil }
        return "No colour twice: \(palette.name(last)) was the last colour sent — send another colour first."
    }

    /// The colour family each move sent (-1 for assists and holds), by replaying the moves.
    static func families(level: LevelDefinition, board: Board, capacity: Int, moves: [Int]) -> [Int] {
        let g = Game(level: level, board: board, capacity: capacity)
        var out: [Int] = []
        out.reserveCapacity(moves.count)
        for code in moves {
            var fam = -1
            if code >= 0 && code < Game.addChamberMove {
                fam = g.front(code)?.family ?? -1
            } else if code >= Game.releaseBase {
                let i = code - Game.releaseBase
                if i >= 0 && i < g.state.chambers.count { fam = g.state.chambers[i].family }
            }
            _ = g.apply(move: code)
            out.append(fam)
        }
        return out
    }

    var hintTunnel: Int? {
        if case .move(let code, _)? = hint, code < Game.addChamberMove { return code }
        return nil
    }

    var hintChamber: Int? {
        if case .move(let code, _)? = hint, code >= Game.releaseBase { return code - Game.releaseBase }
        return nil
    }

    /// Plays whatever the current hint suggests.
    func playHint() {
        guard case .move(let code, _)? = hint else { return }
        if code >= Game.releaseBase { release(code - Game.releaseBase) } else { dispatch(code) }
    }

    // MARK: - Raster

    func ensureRaster(cellPx: Int) {
        if let r = raster, r.cellPx == cellPx { return }
        let t = now
        var open = board.initialOpen()
        for i in 0..<board.count where board.family[i] >= 0 {
            open[i] = scheduler.liftTime[i] <= t
        }
        raster = MosaicRaster(board: board, palette: palette, cellPx: cellPx, open: open, soil: groundColor)
    }

    // MARK: - Slots

    /// Recomputes which team owns which slot at game time `t`. A slot is taken by a team that is
    /// waiting or held (logical), or whose ants still have tiles to pick up (from the scheduler).
    private func refreshSlots(at t: Double, natural: Bool = false) {
        let busy = scheduler.busyTeams(at: t)
        let chamberList = game.state.chambers
        var chamberIndex: [Int: Int] = [:]
        for (i, c) in chamberList.enumerated() { chamberIndex[c.uid] = i }
        var occupants = Set(busy.keys)
        for c in chamberList { occupants.insert(c.uid) }
        // keep positions stable: drop teams that left, then fill gaps with newcomers
        var freed = 0
        for k in slotOwners.indices {
            if let u = slotOwners[k], !occupants.contains(u) {
                slotOwners[k] = nil
                freed += 1
            }
        }
        // a working team finished picking up its tiles (not an undo or a return)
        if natural && freed > 0 && soundsLive { SoundBoard.shared.play(.teamDone) }
        let cap = game.state.capacity
        if slotOwners.count < cap {
            slotOwners.append(contentsOf: [Int?](repeating: nil, count: cap - slotOwners.count))
        } else if slotOwners.count > cap {
            let kept = slotOwners.compactMap { $0 }
            slotOwners = kept.map { Optional($0) }
            if slotOwners.count < cap {
                slotOwners.append(contentsOf: [Int?](repeating: nil, count: cap - slotOwners.count))
            }
        }
        let placed = Set(slotOwners.compactMap { $0 })
        var newcomers = chamberList.map { $0.uid }.filter { !placed.contains($0) }
        for u in busy.keys.sorted() where !placed.contains(u) && chamberIndex[u] == nil { newcomers.append(u) }
        for u in newcomers {
            if let free = slotOwners.firstIndex(where: { $0 == nil }) {
                slotOwners[free] = u
            } else {
                slotOwners.append(u)       // only after undoing an added slot while teams are busy
            }
        }
        var items: [SlotItem] = []
        for (k, owner) in slotOwners.enumerated() {
            guard let u = owner else {
                items.append(SlotItem(id: k, content: .open))
                continue
            }
            if let ci = chamberIndex[u] {
                let team = chamberList[ci]
                if team.held {
                    items.append(SlotItem(id: k, content: .held(chamber: ci, uid: u, family: team.family, need: team.remaining)))
                } else {
                    let left = team.remaining + (busy[u] ?? 0)
                    items.append(SlotItem(id: k, content: .waiting(chamber: ci, uid: u, family: team.family, toCollect: left)))
                }
            } else {
                let fam = scheduler.trips.first(where: { $0.team == u })?.family ?? 0
                items.append(SlotItem(id: k, content: .working(uid: u, family: fam, toCollect: busy[u] ?? 0)))
            }
        }
        if items != slots { slots = items }
        let occ = occupants.count
        if occ != occupiedSlots { occupiedSlots = occ }
        var busyOutside = 0
        for u in busy.keys where chamberIndex[u] == nil { busyOutside += 1 }
        let isBlockedNow = game.deadlocked(busyOutsideSlots: busyOutside)
        if isBlockedNow != blocked {
            blocked = isBlockedNow
            if soundsLive { flight(isBlockedNow ? "blocked: every slot holds a waiting team" : "no longer blocked") }
            if isBlockedNow {
                showCoach(.jam)
                if soundsLive { SoundBoard.shared.play(.blocked) }
            }
        }
        // time until the next working slot frees (only interesting when every slot is taken)
        var nextFree: Double? = nil
        if occ >= cap {
            var soonest = Double.infinity
            for u in busy.keys { soonest = min(soonest, scheduler.slotFreeTime(team: u)) }
            if soonest.isFinite { nextFree = max(0, (soonest - t) / max(0.01, speed)) }
        }
        let rounded = nextFree.map { ($0 * 2).rounded(.up) / 2 }
        if rounded != nextFreeSeconds { nextFreeSeconds = rounded }
    }

    private func refuseBecauseFull() {
        refusedTick += 1
        SoundBoard.shared.play(.refused)
        flight("refused: no open slot (\(occupiedSlots)/\(capacity) busy)")
        if let s = nextFreeSeconds, s > 0, s < 1e6 {
            announce("All \(capacity) slots are busy — the next one frees in about \(Int(s.rounded(.up))) s. Speed up the ants to hurry.")
        } else {
            announce("All \(capacity) slots are taken. Wait for a team to finish, or return a waiting team.")
        }
        showCoach(.slotsFull)
    }

    // MARK: - Actions

    func dispatch(_ q: Int) {
        refreshSlots(at: now)
        guard let fr = game.front(q), !game.isJammed else { return }
        guard hasOpenSlot, game.canDispatch(q) else {
            refuseBecauseFull()
            return
        }
        if let why = colourRefusal(q) {
            refusedTick += 1
            SoundBoard.shared.play(.refused)
            announce(why)
            return
        }
        let chambersBefore = game.state.chambers.count
        clearTransient()
        _ = lastSentFamily              // make sure the family list matches the moves so far
        let ev = game.dispatch(q)
        moveFamilies.append(fr.family)
        var own = 0
        for c in ev where c.team == fr.uid { own += 1 }
        flight("send tunnel \(q + 1) (team \(fr.uid), \(palette.name(fr.family)), needs \(fr.need)): \(ev.count) tiles claimed, \(own) by this team; \(game.state.chambers.count) waiting; \(scheduler.trips.count) ants out before")
        scheduler.schedule(ev, move: game.moves.count - 1, now: now + 0.04)
        hapticTick += 1
        SoundBoard.shared.play(.send)
        if game.state.chambers.count > chambersBefore { SoundBoard.shared.play(.wait, delay: 0.28) }
        describeSend(from: "Tunnel \(q + 1)", uid: fr.uid, need: fr.need, claims: ev)
        afterLogicalChange()
        if coach == .tapTeam { dismissCoach() }
        if game.state.chambers.count > chambersBefore {
            showCoach(.chamber)
        } else if moveCount == 1 {
            showCoach(.watchAnts)
        } else if moveCount >= 4 {
            showCoach(.scout)
        }
    }

    func undo() {
        guard game.canUndo else { return }
        if let left = undosLeft, left <= 0 {
            refusedTick += 1
            SoundBoard.shared.play(.refused)
            announce("No undos left — this game allows \(ChallengeModifier.undoLimit).")
            return
        }
        _ = lastSentFamily
        guard let claims = game.undo() else { return }
        if !moveFamilies.isEmpty { moveFamilies.removeLast() }
        flight("undo: \(claims.count) tiles back on the board, \(game.moves.count) moves left")
        scheduler.undo(claims: claims, fromMove: game.moves.count)
        undos += 1
        SoundBoard.shared.play(.undo)
        clearTransient()
        raster?.sync(liftTime: scheduler.liftTime, now: now)
        afterLogicalChange()
    }

    func undo(times n: Int) {
        for _ in 0..<max(0, n) { undo() }
    }

    /// Recovery: one more slot.
    func addChamber() {
        guard assistsAllowed else {
            refusedTick += 1
            announce("Assists are off in this game (No assists).")
            return
        }
        _ = lastSentFamily
        game.addChamber()
        moveFamilies.append(-1)
        flight("add a slot (\(game.state.capacity) now)")
        clearTransient()
        SoundBoard.shared.play(.addSlot)
        announce("Added a slot (\(game.state.capacity) now). Counted as an assist.")
        afterLogicalChange()
    }

    /// Recovery: return the team in chamber `index` to the front of its tunnel, freeing its slot.
    func recall(_ index: Int) {
        guard game.canRecall(index) else { return }
        guard assistsAllowed else {
            refusedTick += 1
            announce("Assists are off in this game (No assists): waiting teams can't be returned.")
            return
        }
        let t = game.state.chambers[index]
        _ = lastSentFamily
        game.recall(index)
        moveFamilies.append(-1)
        flight("return waiting team \(t.uid) (needs \(t.remaining)) from slot list position \(index)")
        clearTransient()
        SoundBoard.shared.play(.returnTeam)
        announce("Returned the team of \(t.remaining) to the front of tunnel \(t.tunnel + 1). Its slot is open.")
        afterLogicalChange()
    }

    /// Legacy recovery for a jam restored from an old save.
    func recallJammed() {
        _ = lastSentFamily
        game.recallJammed()
        moveFamilies.append(-1)
        flight("return the blocked team")
        clearTransient()
        afterLogicalChange()
    }

    /// Send a team that an old save left parked with Hold (Hold itself was removed; it already
    /// owns its slot, so this never needs a free one).
    func release(_ index: Int) {
        guard game.canRelease(index) else { return }
        let t = game.state.chambers[index]
        clearTransient()
        _ = lastSentFamily
        let ev = game.release(index)
        moveFamilies.append(t.family)
        flight("send held team \(t.uid): \(ev.count) tiles claimed")
        scheduler.schedule(ev, move: game.moves.count - 1, now: now + 0.04)
        hapticTick += 1
        SoundBoard.shared.play(.send)
        describeSend(from: "Held team", uid: t.uid, need: t.remaining, claims: ev)
        afterLogicalChange()
    }

    private func describeSend(from source: String, uid: Int, need: Int, claims: [Claim]) {
        var own = 0
        for c in claims where c.team == uid { own += 1 }
        let others = claims.count - own
        let extra = others > 0 ? " Waiting teams picked up \(others) more." : ""
        if own == need {
            announce("\(source): team of \(need) sent — every tile is reachable; its slot frees when the ants have picked them all up." + extra)
        } else {
            announce("\(source): team reached \(own) of \(need) tiles now and keeps its slot, waiting for the rest." + extra)
        }
    }

    private func announce(_ text: String) {
        eventText = text
        eventExpiry = Date().addingTimeInterval(6)
    }

    func restart() {
        game = Game(level: level, board: board, capacity: level.chambers(for: difficulty))
        scheduler = AntScheduler(board: board, palette: palette)
        scheduler.style = pathStyle
        if let r = raster {
            raster = MosaicRaster(board: board, palette: palette, cellPx: r.cellPx, open: board.initialOpen(), soil: groundColor)
        }
        clearTransient()
        undos = 0
        hintsUsed = 0
        elapsed = 0
        visuallyComplete = false
        deliveredCount = 0
        eventText = nil
        slotOwners = []
        clock = GameClock()
        clock.set(speed: speed, at: Date())
        soundCursor = 0
        milestone = 0
        familyLeft = []
        completionNews = nil
        scoreBreakdown = nil
        highScoreRank = nil
        savedHighScorePlace = nil
        moveFamilies = []
        SoundBoard.shared.play(.undo)
        SaveStore.clearGame(level.id)
        refreshMiniature(force: true)
        afterLogicalChange(save: false)
        beginFlightRecord(resumed: false)
        flight("restart")
    }

    private func clearTransient() {
        scout = nil
        scoutSet = []
        hint = nil
    }

    func beginScout(_ q: Int) {
        guard scoutAllowed else {
            announce("Scouting is off in this game (No scouting).")
            return
        }
        guard let rep = game.scout(q) else { return }
        scout = rep
        scoutSet = Set(rep.ownTiles)
        animating = true
        SoundBoard.shared.play(.scout)
        if coach == .scout { dismissCoach() }
    }

    func endScout() {
        scout = nil
        scoutSet = []
    }

    func requestHint() {
        guard !hintBusy, hintsAllowed else { return }
        hintBusy = true
        hintsUsed += 1
        flight("hint asked")
        let b = board
        let tunnels = game.tunnels
        let st = game.state
        let mv = game.moves
        let sol = level.solution
        Task { [weak self] in
            let result = await Task.detached(priority: .userInitiated) {
                HintSolver.hint(board: b, tunnels: tunnels, state: st, moves: mv, solution: sol)
            }.value
            self?.applyHint(result)
        }
    }

    private func applyHint(_ r: HintResult) {
        hintBusy = false
        hint = r
        switch r {
        case .move(let code, let onPlan): flight("hint: move \(code)\(onPlan ? "" : " (no sure win)")")
        case .undo(let n): flight("hint: undo \(n)")
        case .finished: flight("hint: finished")
        }
        SoundBoard.shared.play(.hint)
        animating = true
        save()
    }

    func clearHint() { hint = nil }

    private func afterLogicalChange(save doSave: Bool = true) {
        revision += 1
        animating = true
        refreshFitBadges()
        refreshSlots(at: now)
        if doSave { save() }
    }

    private func refreshFitBadges() {
        guard scoutAllowed else {
            if !fitBadges.isEmpty { fitBadges = [] }
            return
        }
        var out: [Bool?] = []
        for q in 0..<game.tunnels.count {
            if let rep = game.scout(q) { out.append(rep.fits) } else { out.append(nil) }
        }
        fitBadges = out
    }

    // MARK: - Tick (10 Hz, driven by GameView)

    func tick() {
        // Finished: nothing moves any more, so skip the per-tick work (keeps the finish card and its
        // name box responsive). Play again resets visuallyComplete and the ticks resume.
        if visuallyComplete { return }
        let t = now
        elapsed += 0.1
        raster?.sync(liftTime: scheduler.liftTime, now: t)
        refreshMiniature(force: false)
        refreshSlots(at: t, natural: true)
        checkGoals(at: t)
        pumpTileSounds(now: t)
        scheduler.prune(before: t - 0.5)
        if Date().timeIntervalSince(flightStatusAt) >= 2 {
            flightStatusAt = Date()
            flightStatus(at: t)
        }
        if eventText != nil && Date() > eventExpiry { eventText = nil }
        let busy = scheduler.isBusy
        let wantAnimating = busy || scout != nil || hint != nil
        if animating != wantAnimating { animating = wantAnimating }
        if game.isWon && !busy && !visuallyComplete {
            visuallyComplete = true
            flight("finished: every tile is home")
            FlightRecorder.shared.end()
            SaveStore.clearGame(level.id)
            let news = app?.recordCompletion(levelID: level.id, seconds: elapsed, undos: undos, difficulty: difficulty,
                                             modifiers: modifiers.count)
            completionNews = news
            let breakdown = ScoreRules.solo(tiles: board.tileCount, difficulty: difficulty, modifiers: modifiers,
                                            undos: undos, hints: hintsUsed, assists: assistCount)
            scoreBreakdown = breakdown
            highScoreRank = app?.highScoreRank(.solo, levelID: level.id, score: breakdown.score, seconds: elapsed)
            let sb = SoundBoard.shared
            sb.play(.complete)
            var delay = 2.1
            if news?.newBest == true || highScoreRank != nil {
                sb.play(.newBest, delay: delay)
                delay += 1.0
            }
            if let n = news, !n.unlocked.isEmpty { sb.play(.unlocked, delay: delay) }
        }
    }

    /// Goal sounds that come from progress rather than a tap: a whole colour lifted, and each
    /// quarter of the mosaic carried home.
    private func checkGoals(at t: Double) {
        var left = [Int](repeating: 0, count: max(1, palette.familyCount))
        let lift = scheduler.liftTime
        for i in 0..<board.count {
            let f = Int(board.family[i])
            if f >= 0 && f < left.count && lift[i] > t { left[f] += 1 }
        }
        let remaining = left.reduce(0, +)
        if soundsLive && familyLeft.count == left.count && remaining > 0 {
            for f in left.indices where left[f] == 0 && familyLeft[f] > 0 {
                SoundBoard.shared.play(.colourCleared)
                announce("Every \(palette.name(f)) tile has been lifted.")
                break
            }
        }
        familyLeft = left
        let quarter = board.tileCount == 0 ? 0 : min(3, deliveredCount * 4 / board.tileCount)
        if quarter > milestone {
            if soundsLive {
                SoundBoard.shared.play(quarter == 1 ? .milestone1 : quarter == 2 ? .milestone2 : .milestone3)
            }
            milestone = quarter
        }
    }

    private struct SoundEvent {
        let time: Double
        let pickup: Bool
        let family: Int
        let column: Int
    }

    /// Hands the SoundBoard every tile pickup and nest drop due before the next tick (plus a little
    /// margin), each with its exact start delay, so clicks land on the frame the ant lifts the tile.
    private func pumpTileSounds(now t: Double) {
        let horizon = t + 0.16 * speed                  // game seconds covering the next 10 Hz tick
        let from = max(soundCursor, t - 0.3 * speed)    // never replay stale events (e.g. after backgrounding)
        soundCursor = max(soundCursor, horizon)
        soundSpeed = speed
        let sb = SoundBoard.shared
        guard sb.isOn, sb.tileClicks, horizon > from else { return }
        let holeColumn = board.hole % board.cols
        var events: [SoundEvent] = []
        for trip in scheduler.trips {
            if trip.arrive > from && trip.arrive <= horizon {
                events.append(SoundEvent(time: trip.arrive, pickup: true, family: trip.family, column: Int(trip.tile) % board.cols))
            }
            if trip.home > from && trip.home <= horizon {
                events.append(SoundEvent(time: trip.home, pickup: false, family: trip.family, column: holeColumn))
            }
        }
        guard !events.isEmpty else { return }
        events.sort { $0.time < $1.time }
        let width = Double(max(1, board.cols - 1))
        let pace = max(0.01, speed)
        for e in events {
            let delay = max(0, (e.time - t) / pace)
            let pan = (Double(e.column) / width * 2 - 1) * 0.7
            if e.pickup {
                sb.tile(family: e.family, pan: pan, delay: delay)
            } else {
                sb.deliver(pan: pan, delay: delay)
            }
        }
    }

    private func refreshMiniature(force: Bool) {
        let t = now
        var changed = force
        var count = 0
        let home = scheduler.homeTime
        for i in 0..<board.count where board.family[i] >= 0 {
            let shown = home[i] <= t
            if shown { count += 1 }
            if shown != miniShown[i] {
                miniShown[i] = shown
                changed = true
            }
        }
        if changed { miniDirty = true }
        // the miniature redraws every tile, so rebuild it at most twice a second (and at once when forced
        // or when the last tile is home) — it used to be rebuilt ten times a second while ants delivered
        if miniDirty && (force || count == board.tileCount || Date().timeIntervalSince(miniBuiltAt) >= 0.5) {
            let snapshot = miniShown
            miniImage = MosaicRaster.miniature(board: board, palette: palette) { snapshot[$0] }
            miniDirty = false
            miniBuiltAt = Date()
        }
        if count != deliveredCount { deliveredCount = count }
    }

    // MARK: - Coaching

    private func startCoachIfNeeded() {
        guard game.moves.isEmpty else { return }
        if level.id == "firstDig" {
            showCoach(.tapTeam)
        } else if level.id == "sunflower" {
            showCoach(.showcaseIntro)
        } else if level.isPhoto && !level.id.hasPrefix("pattern-") {
            showCoach(.photoIntro)
        }
    }

    private func showCoach(_ step: CoachStep) {
        guard let app = app else { return }
        if app.settings.coachSeen.contains(step.rawValue) { return }
        coach = step
    }

    func dismissCoach() {
        if let c = coach { app?.markCoachSeen(c) }
        coach = nil
    }

    // MARK: - Saving

    func save() {
        if game.moves.isEmpty || visuallyComplete {
            if game.moves.isEmpty { SaveStore.clearGame(level.id) }
            return
        }
        SaveStore.saveGame(SaveGame(levelID: level.id, difficulty: difficulty, moves: game.moves,
                                    undos: undos, hints: hintsUsed, elapsed: elapsed,
                                    modifiers: ChallengeModifier.sorted(modifiers)))
    }

    /// Puts the finished score on this mosaic's high-score table under `name`.
    func saveHighScore(name: String) {
        guard let b = scoreBreakdown, savedHighScorePlace == nil, highScoreRank != nil else { return }
        let entry = HighScoreEntry(name: name, score: b.score, seconds: elapsed, date: Date(),
                                   difficulty: difficulty, modifiers: ChallengeModifier.sorted(modifiers))
        savedHighScorePlace = app?.saveHighScore(.solo, levelID: level.id, entry: entry) ?? 0
    }

    /// Top scores for this mosaic (for the win card).
    var topScores: [HighScoreEntry] { app?.topScores(.solo, levelID: level.id) ?? [] }
    var playerName: String { app?.settings.playerName ?? "" }

    /// New ants use this style from now on; ants already walking finish their current route.
    func setPathStyle(_ s: PathStyle) {
        pathStyle = s
        scheduler.style = s
        app?.settings.pathStyle = s
        flight("ant paths: \(s.title)")
    }

    func setSoundOn(_ on: Bool) {
        soundOn = on
        if let app = app {
            app.settings.soundOn = on
        } else {
            SoundBoard.shared.configure(on: on, volume: 0.8, tileClicks: true)
        }
    }

    func setDetailedAnts(_ on: Bool) {
        detailedAnts = on
        app?.settings.detailedAnts = on
    }
}
