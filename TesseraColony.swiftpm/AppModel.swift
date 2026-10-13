import SwiftUI

@MainActor
final class AppModel: ObservableObject {
    @Published var settings: AppSettings {
        didSet {
            SaveStore.saveSettings(settings)
            applySound()
        }
    }
    @Published private(set) var progress: [String: CompletionRecord]
    @Published private(set) var current: GameController?
    /// A two-player match in progress.
    @Published private(set) var versus: VersusController?
    @Published private(set) var photoLevels: [PhotoLevelRecord]
    @Published private(set) var photoBusy = false
    @Published var photoMessage: String?
    /// Difficulty measured on the iPad for pattern and photo levels (built-ins ship theirs).
    @Published private(set) var measuredStats: [String: DifficultyStats] = [:]
    /// Top scores per mosaic (solo and two-player winners).
    @Published private(set) var highScores: HighScoreTable
    /// Report left by a game that didn't close normally last time (see FlightRecorder).
    @Published private(set) var crashReport: String?
    private var measuring = Set<String>()
    private var thumbnailCache: [String: CGImage] = [:]

    init() {
        FlightRecorder.shared.launchCheck()
        settings = SaveStore.loadSettings()
        progress = SaveStore.loadProgress()
        photoLevels = PhotoLibrary.loadAll()
        highScores = SaveStore.loadHighScores()
        crashReport = FlightRecorder.shared.pendingReport
        applySound()
    }

    func dismissCrashReport() {
        FlightRecorder.shared.dismissReport()
        crashReport = nil
    }

    private func applySound() {
        SoundBoard.shared.configure(on: settings.soundOn, volume: settings.soundVolume, tileClicks: settings.tileClicks,
                                    actions: settings.actionSounds, goals: settings.goalSounds,
                                    ignoreSilentMode: settings.soundInSilentMode)
    }

    var allLevels: [LevelDefinition] { LevelCatalog.builtIn + photoLevels.map { $0.level } }

    /// Opens a mosaic. `fresh` starts over with `difficulty` and `modifiers` (defaults: the last
    /// choice); otherwise the saved game resumes on its own difficulty and harder options.
    func play(_ level: LevelDefinition, fresh: Bool, difficulty chosen: Difficulty? = nil,
              modifiers chosenMods: Set<ChallengeModifier>? = nil) {
        var save: SaveGame? = nil
        if let c = chosen, c != settings.difficulty { settings.difficulty = c }
        if let m = chosenMods {
            let list = ChallengeModifier.sorted(m)
            if list != settings.lastModifiers { settings.lastModifiers = list }
        }
        var difficulty = chosen ?? settings.difficulty
        var mods = chosenMods ?? Set(settings.lastModifiers)
        if fresh {
            SaveStore.clearGame(level.id)
        } else if let s = SaveStore.loadGame(level.id) {
            save = s
            difficulty = s.difficulty
            mods = Set(s.modifiers ?? [])
        }
        current = GameController(level: level, difficulty: difficulty, modifiers: mods, app: self, resume: save)
        settings.hasLaunchedBefore = true
    }

    func startVersus(level: LevelDefinition, rules: VersusRules) {
        current?.save()
        current = nil
        FlightRecorder.shared.end()
        versus = VersusController(level: level, rules: rules, app: self)
    }

    func endVersus() {
        versus = nil
    }

    func goHome() {
        current?.save()
        current = nil
        FlightRecorder.shared.end()
    }

    func markCoachSeen(_ step: CoachStep) {
        if !settings.coachSeen.contains(step.rawValue) {
            settings.coachSeen.append(step.rawValue)
        }
    }

    @discardableResult
    func recordCompletion(levelID: String, seconds: Double, undos: Int, difficulty: Difficulty,
                          modifiers: Int = 0) -> CompletionNews {
        let closedBefore = Set(allLevels.filter { !isPlayable($0) }.map { $0.id })
        let starsBefore = stars(levelID)
        let masteredBefore = isMastered(levelID)
        let old = progress[levelID]
        var rec = old ?? CompletionRecord(bestSeconds: seconds, fewestUndos: undos, difficulty: difficulty, completions: 0)
        let prevBest = old?.bestByDifficulty?[difficulty.rawValue]
        var byDifficulty = rec.bestByDifficulty ?? [:]
        byDifficulty[difficulty.rawValue] = min(prevBest ?? seconds, seconds)
        rec.bestByDifficulty = byDifficulty
        rec.bestSeconds = min(rec.bestSeconds, seconds)
        rec.fewestUndos = min(rec.fewestUndos, undos)
        rec.completions += 1
        if difficulty == .expert || (difficulty == .classic && rec.difficulty == .gentle) { rec.difficulty = difficulty }
        if difficulty == .expert { rec.expertModifiers = max(rec.expertModifiers ?? 0, modifiers) }
        progress[levelID] = rec
        SaveStore.saveProgress(progress)
        let opened = allLevels.filter { closedBefore.contains($0.id) && isPlayable($0) }.map { $0.title }
        let beat = prevBest.map { seconds < $0 - 0.5 } ?? false
        let starsNow = stars(levelID)
        return CompletionNews(newBest: beat, firstClear: old == nil, unlocked: opened,
                              stars: starsNow, newStar: starsNow > starsBefore,
                              mastered: !masteredBefore && isMastered(levelID))
    }

    func resetEverything() {
        SaveStore.resetEverything(levelIDs: allLevels.map { $0.id })
        settings = AppSettings()
        progress = [:]
        highScores = HighScoreTable()
    }

    // MARK: - High scores

    func topScores(_ kind: HighScoreKind, levelID: String) -> [HighScoreEntry] {
        highScores.list(kind, levelID)
    }

    /// The place a score would take on a mosaic's table (nil = doesn't make the top 5).
    func highScoreRank(_ kind: HighScoreKind, levelID: String, score: Int, seconds: Double) -> Int? {
        highScores.rank(kind, levelID, score: score, seconds: seconds)
    }

    /// Saves a score under a name; returns its place on the table.
    @discardableResult
    func saveHighScore(_ kind: HighScoreKind, levelID: String, entry: HighScoreEntry) -> Int? {
        var e = entry
        e.name = HighScoreNames.clean(e.name)
        let place = highScores.insert(kind, levelID, e)
        SaveStore.saveHighScores(highScores)
        if settings.playerName != e.name { settings.playerName = e.name }
        return place
    }

    func clearHighScores() {
        highScores = HighScoreTable()
        SaveStore.saveHighScores(highScores)
    }

    // MARK: - Home filter

    /// Does a mosaic pass Home's difficulty filter (its rating on the chosen difficulty)?
    func passesFilter(_ level: LevelDefinition) -> Bool {
        if !passesStatus(level) { return false }
        let f = settings.ratingFilter
        if f == .all { return true }
        guard let st = difficultyStats(for: level) else { return false }
        return f.levels.contains(st.rating(settings.difficulty).level)
    }

    func thumbnail(for level: LevelDefinition) -> CGImage? {
        if let t = thumbnailCache[level.id] { return t }
        let board = Board(art: level.art)
        let img = MosaicRaster.miniature(board: board, palette: level.palette) { _ in true }
        thumbnailCache[level.id] = img
        return img
    }

    // MARK: - Unlocking

    func isUnlocked(_ level: LevelDefinition) -> Bool {
        if settings.unlockAll || level.isPhoto { return true }
        guard let rule = LevelCatalog.unlockRule(for: level.id) else { return true }
        return rule.anyOf.contains { progress[$0] != nil }
    }

    /// What must be finished first, e.g. "First Dig" or "any Challenge mosaic" (nil when open).
    func unlockRequirement(_ level: LevelDefinition) -> String? {
        guard !isUnlocked(level), let rule = LevelCatalog.unlockRule(for: level.id) else { return nil }
        return rule.label
    }

    /// The first found mosaic you haven't finished yet, going through the packs in Home's order —
    /// the "Next up" banner.
    var nextUp: LevelDefinition? {
        for pack in LevelCatalog.packs {
            if let l = pack.levels.first(where: { isPlayable($0) && progress[$0.id] == nil }) { return l }
        }
        return nil
    }

    /// What "Next mosaic" on the win card opens (the next unfinished one in the same pack first).
    func nextLevel(after id: String) -> LevelDefinition? {
        let list = LevelCatalog.packList(containing: id)
        if let i = list.firstIndex(where: { $0.id == id }), i + 1 < list.count {
            if let fresh = list[(i + 1)...].first(where: { isPlayable($0) && progress[$0.id] == nil }) { return fresh }
        }
        return nextUp
    }

    /// The in-progress game for a level, if any (its difficulty and moves).
    func savedGame(for level: LevelDefinition) -> SaveGame? { SaveStore.loadGame(level.id) }

    /// Measured difficulty: shipped with built-in levels, measured on the iPad for the others.
    func difficultyStats(for level: LevelDefinition) -> DifficultyStats? {
        level.shippedStats ?? measuredStats[level.id]
    }

    /// Starts measuring a pattern or photo level's difficulty in the background (a few seconds).
    func measureIfNeeded(_ level: LevelDefinition) {
        guard difficultyStats(for: level) == nil, !measuring.contains(level.id) else { return }
        measuring.insert(level.id)
        Task { [weak self] in
            let stats = await Task.detached(priority: .utility) { DifficultyProbe.measure(level: level) }.value
            self?.measuredStats[level.id] = stats
            self?.measuring.remove(level.id)
        }
    }

    func savedMoves(for level: LevelDefinition) -> Int? {
        guard let s = SaveStore.loadGame(level.id) else { return nil }
        return s.moves.filter { $0 < Game.addChamberMove }.count
    }

    // MARK: - Pattern mosaics (a new, verified level on demand)

    func createPatternLevel() {
        guard !photoBusy else { return }
        photoBusy = true
        photoMessage = nil
        let number = photoLevels.filter { $0.id.hasPrefix("pattern-") }.count + 1
        let seed = UInt64(truncatingIfNeeded: Int64(Date().timeIntervalSince1970 * 1000)) & 0xFFFF_FFFF
        Task { [weak self] in
            let level = await Task.detached(priority: .userInitiated) { () -> LevelDefinition? in
                PatternLevelBuilder.build(seed: seed, number: number)
            }.value
            guard let self = self else { return }
            self.photoBusy = false
            guard let level = level else {
                self.photoMessage = "The colony couldn't plan that pattern. Please tap New pattern again."
                return
            }
            let rec = PhotoLevelRecord(level: level, detail: .fine, created: Date())
            PhotoLibrary.save(rec)
            self.photoLevels.insert(rec, at: 0)
            self.play(level, fresh: true)
        }
    }

    // MARK: - Photo mosaics

    /// Converts picked photo data into a playable mosaic in the background, then opens it.
    func importPhoto(_ data: Data) {
        guard !photoBusy else { return }
        photoBusy = true
        photoMessage = nil
        let detail = settings.photoDetail
        let number = photoLevels.count + 1
        let id = "photo-" + String(UInt64(Date().timeIntervalSince1970 * 1000), radix: 36)
        let seed = UInt64(truncatingIfNeeded: data.count &* 2654435761) ^ UInt64(Date().timeIntervalSince1970)
        Task { [weak self] in
            let result = await Task.detached(priority: .userInitiated) { () -> Result<LevelDefinition, PhotoBuildError> in
                guard let px = PhotoLibrary.pixels(from: data) else { return .failure(.unreadable) }
                return PhotoLevelBuilder.build(image: px, detail: detail, seed: seed, id: id, title: "Photo mosaic \(number)")
            }.value
            self?.finishImport(result, detail: detail)
        }
    }

    private func finishImport(_ result: Result<LevelDefinition, PhotoBuildError>, detail: PhotoDetail) {
        photoBusy = false
        switch result {
        case .failure(let e):
            photoMessage = e.message
        case .success(let level):
            let rec = PhotoLevelRecord(level: level, detail: detail, created: Date())
            PhotoLibrary.save(rec)
            photoLevels.insert(rec, at: 0)
            play(level, fresh: true)
        }
    }

    func deletePhotoLevel(id: String) {
        PhotoLibrary.delete(id: id)
        SaveStore.clearGame(id)
        photoLevels.removeAll { $0.id == id }
        thumbnailCache[id] = nil
        progress[id] = nil
        SaveStore.saveProgress(progress)
    }
}

struct RootView: View {
    @StateObject private var app = AppModel()
    @Environment(\.scenePhase) private var scenePhase

    var body: some View {
        ZStack {
            if let match = app.versus {
                VersusView(controller: match)
                    .id(ObjectIdentifier(match))
                    .transition(.opacity)
            } else if let game = app.current {
                GameView(controller: game)
                    .id(ObjectIdentifier(game))
                    .transition(.opacity)
            } else {
                HomeView()
                    .transition(.opacity)
            }
        }
        .animation(.easeInOut(duration: 0.3), value: app.current.map { ObjectIdentifier($0) })
        .animation(.easeInOut(duration: 0.3), value: app.versus.map { ObjectIdentifier($0) })
        .environmentObject(app)
        .onChange(of: scenePhase) { _, phase in
            // a game left open in the background and closed there by iOS is not a crash
            if phase == .background {
                FlightRecorder.shared.suspend()
            } else if phase == .active {
                FlightRecorder.shared.resume()
            }
        }
    }
}
