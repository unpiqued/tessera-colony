import Foundation

/// Optional rules that make any mosaic harder, chosen on the start card. Each one adds to the
/// score multiplier. None of them can make a mosaic unsolvable: the designed solution uses no
/// scouting, hints, undo or assists, and it never needs to see past the front of a tunnel.
/// (No colour twice was checked on every built-in mosaic by the reference model — see VALIDATION.)
enum ChallengeModifier: String, CaseIterable, Codable, Identifiable, Hashable {
    case hiddenQueue, noScout, noHints, limitedUndo, noAssists, noRepeatColour

    var id: String { rawValue }

    var title: String {
        switch self {
        case .hiddenQueue: return "Hidden queue"
        case .noScout: return "No scouting"
        case .noHints: return "No hints"
        case .limitedUndo: return "3 undos"
        case .noAssists: return "No assists"
        case .noRepeatColour: return "No colour twice"
        }
    }

    var blurb: String {
        switch self {
        case .hiddenQueue: return "Only the front team of each tunnel is shown."
        case .noScout: return "Press-and-hold scouting and Gentle's \u{201C}can finish\u{201D} badges are off."
        case .noHints: return "The hint button is off."
        case .limitedUndo: return "Only \(ChallengeModifier.undoLimit) undos for the whole game."
        case .noAssists: return "No adding slots and no returning waiting teams."
        case .noRepeatColour: return "Never send the same colour twice in a row (allowed only when nothing else can go). Hints don't know this rule."
        }
    }

    var systemImage: String {
        switch self {
        case .hiddenQueue: return "eye.slash"
        case .noScout: return "binoculars"
        case .noHints: return "lightbulb.slash"
        case .limitedUndo: return "arrow.uturn.backward.circle"
        case .noAssists: return "hand.raised.slash"
        case .noRepeatColour: return "circle.lefthalf.filled"
        }
    }

    /// Added to the score multiplier (0.2 = +20%).
    var bonus: Double {
        switch self {
        case .hiddenQueue: return 0.20
        case .noScout: return 0.10
        case .noHints: return 0.10
        case .limitedUndo: return 0.20
        case .noAssists: return 0.15
        case .noRepeatColour: return 0.25
        }
    }

    static let undoLimit = 3

    /// Stable order for display and saving.
    static func sorted(_ set: Set<ChallengeModifier>) -> [ChallengeModifier] {
        allCases.filter { set.contains($0) }
    }
}

/// How a finished solo game is scored (mirrors Tools/scoring.py).
///   score = tiles × difficulty factor × (1 + harder-option bonuses)
///           − 5 per undo − 25 per hint − 25 per assist (never below 0)
/// Ties on the high-score table go to the faster time.
enum ScoreRules {
    static let undoPenalty = 5.0
    static let hintPenalty = 25.0
    static let assistPenalty = 25.0

    static func difficultyFactor(_ d: Difficulty) -> Double {
        switch d {
        case .gentle: return 0.5
        case .classic: return 1.0
        case .expert: return 1.5
        }
    }

    /// Summed in a fixed order so the result never depends on Set ordering.
    static func modifierFactor(_ mods: Set<ChallengeModifier>) -> Double {
        ChallengeModifier.sorted(mods).reduce(1.0) { $0 + $1.bonus }
    }

    struct Breakdown: Equatable {
        let tiles: Int
        let difficultyFactor: Double
        let modifierFactor: Double
        let base: Int
        let undoPenalty: Int
        let hintPenalty: Int
        let assistPenalty: Int
        let score: Int
    }

    static func solo(tiles: Int, difficulty: Difficulty, modifiers: Set<ChallengeModifier>,
                     undos: Int, hints: Int, assists: Int) -> Breakdown {
        let df = difficultyFactor(difficulty)
        let mf = modifierFactor(modifiers)
        let base = Int((Double(tiles) * df * mf).rounded())
        let u = Int(Double(undos) * undoPenalty)
        let h = Int(Double(hints) * hintPenalty)
        let a = Int(Double(assists) * assistPenalty)
        return Breakdown(tiles: tiles, difficultyFactor: df, modifierFactor: mf, base: base,
                         undoPenalty: u, hintPenalty: h, assistPenalty: a, score: max(0, base - u - h - a))
    }
}

/// One line on a high-score table.
struct HighScoreEntry: Codable, Identifiable, Equatable {
    var id: UUID = UUID()
    var name: String
    var score: Int
    var seconds: Double
    var date: Date
    /// Solo: the difficulty played. Two players: the slots setting.
    var difficulty: Difficulty
    var modifiers: [ChallengeModifier] = []
    /// Two players: the options and the result ("Race · Reach 3 … · beat 812").
    var detail: String = ""
}

enum HighScoreKind: String, Codable, CaseIterable, Identifiable {
    case solo, versus
    var id: String { rawValue }
    var title: String { self == .solo ? "Solo" : "Two players" }
}

/// Top scores per mosaic, one table for solo games and one for two-player winners.
struct HighScoreTable: Codable, Equatable {
    var solo: [String: [HighScoreEntry]] = [:]
    var versus: [String: [HighScoreEntry]] = [:]

    static let keep = 5

    func list(_ kind: HighScoreKind, _ levelID: String) -> [HighScoreEntry] {
        (kind == .solo ? solo[levelID] : versus[levelID]) ?? []
    }

    /// True when `a` ranks above `b`: higher score, then faster time, then earlier date.
    static func ranksAbove(_ a: HighScoreEntry, _ b: HighScoreEntry) -> Bool {
        if a.score != b.score { return a.score > b.score }
        if abs(a.seconds - b.seconds) > 0.05 { return a.seconds < b.seconds }
        return a.date < b.date
    }

    /// The place (1-based) a new score would take, or nil when it wouldn't make the table.
    func rank(_ kind: HighScoreKind, _ levelID: String, score: Int, seconds: Double) -> Int? {
        guard score > 0 else { return nil }
        let probe = HighScoreEntry(name: "", score: score, seconds: seconds, date: .distantFuture, difficulty: .classic)
        let better = list(kind, levelID).filter { HighScoreTable.ranksAbove($0, probe) }.count
        return better < HighScoreTable.keep ? better + 1 : nil
    }

    /// Adds an entry (keeping the best `keep`) and returns its place, or nil if it didn't make it.
    @discardableResult
    mutating func insert(_ kind: HighScoreKind, _ levelID: String, _ entry: HighScoreEntry) -> Int? {
        var l = list(kind, levelID)
        l.append(entry)
        l.sort { HighScoreTable.ranksAbove($0, $1) }
        if l.count > HighScoreTable.keep { l = Array(l.prefix(HighScoreTable.keep)) }
        if kind == .solo { solo[levelID] = l } else { versus[levelID] = l }
        return l.firstIndex(where: { $0.id == entry.id }).map { $0 + 1 }
    }

    var isEmpty: Bool { solo.values.allSatisfy { $0.isEmpty } && versus.values.allSatisfy { $0.isEmpty } }
}

/// Home's difficulty filter: which ratings to show (measured on the chosen difficulty).
enum RatingFilter: String, CaseIterable, Codable, Identifiable {
    case all, easy, medium, hard, fiendish
    var id: String { rawValue }
    var title: String {
        switch self {
        case .all: return "All"
        case .easy: return "Easy"
        case .medium: return "Medium"
        case .hard: return "Hard"
        case .fiendish: return "Fiendish"
        }
    }
    /// Rating levels (1 Relaxed … 5 Fiendish) this filter keeps.
    var levels: ClosedRange<Int> {
        switch self {
        case .all: return 1...5
        case .easy: return 1...2
        case .medium: return 3...3
        case .hard: return 4...4
        case .fiendish: return 5...5
        }
    }
    var dotLevel: Int {
        switch self {
        case .all: return 0
        case .easy: return 1
        case .medium: return 3
        case .hard: return 4
        case .fiendish: return 5
        }
    }
}

/// The No colour twice option (mirrors colour_rule_legal in Tools/scoring.py): the same colour as
/// the last team sent is refused while another tunnel could send a different colour.
enum ColourRule {
    static func refuses(game: Game, tunnel q: Int, last: Int?) -> Bool {
        guard let last = last, let fr = game.front(q), fr.family == last else { return false }
        return (0..<game.tunnels.count).contains { k in
            k != q && game.canDispatch(k) && (game.front(k).map { $0.family != last } ?? false)
        }
    }
}

enum HighScoreNames {
    static let maxLength = 20

    /// Trims spaces and new lines, keeps at most 20 characters; an empty name becomes "Player".
    static func clean(_ raw: String) -> String {
        let t = raw.trimmingCharacters(in: .whitespacesAndNewlines)
            .replacingOccurrences(of: "\n", with: " ")
        let short = String(t.prefix(maxLength))
        return short.isEmpty ? "Player" : short
    }
}

enum TimeText {
    static func mmss(_ seconds: Double) -> String {
        let s = seconds.isFinite ? max(0, Int(min(seconds, 1e9))) : 0
        return String(format: "%d:%02d", s / 60, s % 60)
    }
}
