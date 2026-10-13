import Foundation

struct SaveGame: Codable {
    var version: Int = 1
    var levelID: String
    var difficulty: Difficulty
    var moves: [Int]
    var undos: Int
    var hints: Int
    var elapsed: Double
    /// Harder options this game was started with (nil in saves from older builds).
    var modifiers: [ChallengeModifier]? = nil
}

struct CompletionRecord: Codable {
    var bestSeconds: Double
    var fewestUndos: Int
    var difficulty: Difficulty
    var completions: Int
    /// Best time per difficulty ("gentle" / "classic" / "expert"); nil in records from older builds.
    var bestByDifficulty: [String: Double]? = nil
    /// Most harder options used in a finish on Expert (1 or more = mastered); nil if never.
    var expertModifiers: Int? = nil
}

/// What a finish achieved (drives the goal sounds and the win card).
struct CompletionNews {
    /// Beat an earlier time on the same difficulty.
    let newBest: Bool
    let firstClear: Bool
    /// Titles of mosaics this finish made playable (unlocked or found).
    let unlocked: [String]
    /// Stars now (1 Gentle … 3 Expert) and whether this finish added one.
    var stars: Int = 0
    var newStar: Bool = false
    /// This finish mastered the mosaic (Expert with a harder option) for the first time.
    var mastered: Bool = false
}

struct AppSettings: Codable {
    var difficulty: Difficulty = .classic
    /// Ant speed multiplier (0.1 ... 16). 1 = four tiles (about two ant lengths) per second.
    var antSpeed: Double = 1.0
    var detailedAnts: Bool = true
    var coachSeen: [String] = []
    var hasLaunchedBefore: Bool = false
    var photoDetail: PhotoDetail = .fine
    /// Colour of the ground behind the mosaic (margin and cleared tiles), 0xRRGGBB.
    var groundColor: UInt32 = GeneratedPalette.soil
    /// Play any built-in mosaic without finishing the one before it.
    var unlockAll: Bool = false
    /// Sound effects (all synthesized on the device).
    var soundOn: Bool = true
    /// 0 ... 1
    var soundVolume: Double = 0.8
    /// The little clinks as ants lift tiles and drop them in the nest ("colony" layer).
    var tileClicks: Bool = true
    /// Wood-and-clay sounds for the moves you make.
    var actionSounds: Bool = true
    /// Bell-and-glass sounds for goals reached.
    var goalSounds: Bool = true
    /// How newly launched ants choose their route (default: each team picks a style at random).
    var pathStyle: PathStyle = .randomTeam
    /// 2 = the default path style is Random per team (older builds defaulted to Natural).
    var pathStyleVersion: Int = 2
    /// Play sounds even when the iPad is in Silent mode.
    var soundInSilentMode: Bool = true
    /// Last two-player options and mosaic.
    var versusRules = VersusRules()
    var versusLevelID = "firstDig"
    /// Name last typed for a high score (pre-filled next time).
    var playerName: String = ""
    /// Harder options last chosen on the start card.
    var lastModifiers: [ChallengeModifier] = []
    /// Home's difficulty filter.
    var ratingFilter: RatingFilter = .all
    /// Home's status filter (to explore, explored, go harder, mastered).
    var statusFilter: StatusFilter = .all
    /// 2 = two-player colour rule defaults to Any colour (older builds defaulted to No colour twice).
    var versusRulesVersion: Int = 2

    init() {}

    /// Tolerant decoding: a missing or unknown key keeps its default instead of resetting everything.
    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        difficulty = (try? c.decodeIfPresent(Difficulty.self, forKey: .difficulty)) ?? .classic
        antSpeed = (try? c.decodeIfPresent(Double.self, forKey: .antSpeed)) ?? 1.0
        detailedAnts = (try? c.decodeIfPresent(Bool.self, forKey: .detailedAnts)) ?? true
        coachSeen = (try? c.decodeIfPresent([String].self, forKey: .coachSeen)) ?? []
        hasLaunchedBefore = (try? c.decodeIfPresent(Bool.self, forKey: .hasLaunchedBefore)) ?? false
        photoDetail = (try? c.decodeIfPresent(PhotoDetail.self, forKey: .photoDetail)) ?? .fine
        groundColor = (try? c.decodeIfPresent(UInt32.self, forKey: .groundColor)) ?? GeneratedPalette.soil
        unlockAll = (try? c.decodeIfPresent(Bool.self, forKey: .unlockAll)) ?? false
        soundOn = (try? c.decodeIfPresent(Bool.self, forKey: .soundOn)) ?? true
        soundVolume = (try? c.decodeIfPresent(Double.self, forKey: .soundVolume)) ?? 0.8
        tileClicks = (try? c.decodeIfPresent(Bool.self, forKey: .tileClicks)) ?? true
        actionSounds = (try? c.decodeIfPresent(Bool.self, forKey: .actionSounds)) ?? true
        goalSounds = (try? c.decodeIfPresent(Bool.self, forKey: .goalSounds)) ?? true
        pathStyle = (try? c.decodeIfPresent(PathStyle.self, forKey: .pathStyle)) ?? .randomTeam
        pathStyleVersion = (try? c.decodeIfPresent(Int.self, forKey: .pathStyleVersion)) ?? 1
        if pathStyleVersion < 2 {
            // settings saved by older builds hold the old default (Natural): move them to the new one once
            if pathStyle == .natural { pathStyle = .randomTeam }
            pathStyleVersion = 2
        }
        soundInSilentMode = (try? c.decodeIfPresent(Bool.self, forKey: .soundInSilentMode)) ?? true
        versusRules = (try? c.decodeIfPresent(VersusRules.self, forKey: .versusRules)) ?? VersusRules()
        versusLevelID = (try? c.decodeIfPresent(String.self, forKey: .versusLevelID)) ?? "firstDig"
        playerName = (try? c.decodeIfPresent(String.self, forKey: .playerName)) ?? ""
        lastModifiers = (try? c.decodeIfPresent([ChallengeModifier].self, forKey: .lastModifiers)) ?? []
        ratingFilter = (try? c.decodeIfPresent(RatingFilter.self, forKey: .ratingFilter)) ?? .all
        statusFilter = (try? c.decodeIfPresent(StatusFilter.self, forKey: .statusFilter)) ?? .all
        versusRulesVersion = (try? c.decodeIfPresent(Int.self, forKey: .versusRulesVersion)) ?? 1
        if versusRulesVersion < 2 {
            // the old default limited each launch to a different colour; lift it once
            versusRules.colour = .any
            versusRulesVersion = 2
        }
    }
}

/// Small JSON blobs in UserDefaults: settings, per-level progress, and one in-progress game per level.
enum SaveStore {
    private static var defaults: UserDefaults { UserDefaults.standard }
    private static let settingsKey = "tessera.settings.v2"
    private static let progressKey = "tessera.progress.v1"
    private static let highScoreKey = "tessera.highscores.v1"
    private static func gameKey(_ id: String) -> String { "tessera.save.v3." + id }

    static func loadSettings() -> AppSettings {
        guard let d = defaults.data(forKey: settingsKey),
              let s = try? JSONDecoder().decode(AppSettings.self, from: d) else { return AppSettings() }
        return s
    }

    static func saveSettings(_ s: AppSettings) {
        if let d = try? JSONEncoder().encode(s) { defaults.set(d, forKey: settingsKey) }
    }

    static func loadProgress() -> [String: CompletionRecord] {
        guard let d = defaults.data(forKey: progressKey),
              let p = try? JSONDecoder().decode([String: CompletionRecord].self, from: d) else { return [:] }
        return p
    }

    static func saveProgress(_ p: [String: CompletionRecord]) {
        if let d = try? JSONEncoder().encode(p) { defaults.set(d, forKey: progressKey) }
    }

    static func loadHighScores() -> HighScoreTable {
        guard let d = defaults.data(forKey: highScoreKey),
              let t = try? JSONDecoder().decode(HighScoreTable.self, from: d) else { return HighScoreTable() }
        return t
    }

    static func saveHighScores(_ t: HighScoreTable) {
        if let d = try? JSONEncoder().encode(t) { defaults.set(d, forKey: highScoreKey) }
    }

    static func loadGame(_ id: String) -> SaveGame? {
        guard let d = defaults.data(forKey: gameKey(id)),
              let g = try? JSONDecoder().decode(SaveGame.self, from: d) else { return nil }
        return g
    }

    static func saveGame(_ g: SaveGame) {
        if let d = try? JSONEncoder().encode(g) { defaults.set(d, forKey: gameKey(g.levelID)) }
    }

    /// Is there a saved game for this mosaic (without decoding it)?
    static func hasGame(_ id: String) -> Bool {
        defaults.data(forKey: gameKey(id)) != nil
    }

    static func clearGame(_ id: String) {
        defaults.removeObject(forKey: gameKey(id))
    }

    static func resetEverything(levelIDs: [String]) {
        defaults.removeObject(forKey: settingsKey)
        defaults.removeObject(forKey: progressKey)
        defaults.removeObject(forKey: highScoreKey)
        for id in levelIDs { clearGame(id) }
    }
}
