import SwiftUI

// The collection: how the built-in mosaics are found, explored and made harder.
//
// * Found — a pack opens (after First Dig, or after a mosaic of the pack before it); its first three
//   mosaics are found at once and every mosaic finished in the pack finds one more. The rest show as
//   "?" cards. Settings → Unlock all shows everything.
// * Explored — finished on any difficulty. Stars: one for Gentle, two for Classic, three for Expert
//   (the hardest difficulty you have finished it on).
// * Mastered — finished on Expert with at least one harder option (the flame).
// After a finish, the win card offers the next harder step: Classic, then Expert, then Expert with one
// more harder option.

/// Home's status filter: where a mosaic stands in your collection.
enum StatusFilter: String, CaseIterable, Codable, Identifiable {
    case all, toExplore, explored, goHarder, mastered

    var id: String { rawValue }

    var title: String {
        switch self {
        case .all: return "All"
        case .toExplore: return "To explore"
        case .explored: return "Explored"
        case .goHarder: return "Go harder"
        case .mastered: return "Mastered"
        }
    }

    var icon: String {
        switch self {
        case .all: return "square.grid.2x2"
        case .toExplore: return "magnifyingglass"
        case .explored: return "star.fill"
        case .goHarder: return "arrow.up.circle"
        case .mastered: return "flame.fill"
        }
    }
}

/// Where one mosaic stands in the collection.
enum CollectionStatus: Equatable {
    /// Its pack (or the mosaic before it) hasn't opened yet; the label says what opens it.
    case packLocked(String)
    /// The pack is open but this mosaic isn't found yet: finish `more` more in the pack.
    case hidden(more: Int)
    /// Found and not finished yet; `moves` > 0 while a game is in progress.
    case found(moves: Int)
    /// Finished: stars = hardest difficulty finished (1 Gentle, 2 Classic, 3 Expert).
    case explored(stars: Int)
    /// Finished on Expert with at least one harder option.
    case mastered

    var isPlayable: Bool {
        switch self {
        case .packLocked, .hidden: return false
        default: return true
        }
    }
}

/// Counts for a pack, a theme or the whole collection.
struct PackProgress {
    var total = 0
    var found = 0
    var explored = 0
    var stars = 0
    var mastered = 0
    /// At least one of its mosaics is unlocked.
    var open = false
}

/// The next way to make a finished mosaic harder: the next difficulty up, then (on Expert) one more
/// harder option.
struct HarderStep {
    let difficulty: Difficulty
    let modifiers: Set<ChallengeModifier>
    let label: String

    static func after(_ d: Difficulty, modifiers: Set<ChallengeModifier>) -> HarderStep? {
        switch d {
        case .gentle:
            return HarderStep(difficulty: .classic, modifiers: modifiers, label: "Try it on Classic")
        case .classic:
            return HarderStep(difficulty: .expert, modifiers: modifiers, label: "Try it on Expert")
        case .expert:
            guard let extra = ChallengeModifier.allCases.first(where: { !modifiers.contains($0) }) else { return nil }
            var more = modifiers
            more.insert(extra)
            return HarderStep(difficulty: .expert, modifiers: more, label: "Expert + \(extra.title)")
        }
    }
}

extension AppModel {
    /// Hardest difficulty finished: 0 none, 1 Gentle, 2 Classic, 3 Expert.
    func stars(_ id: String) -> Int {
        guard let rec = progress[id] else { return 0 }
        var best = rec.difficulty.index + 1
        if let by = rec.bestByDifficulty {
            for d in Difficulty.allCases where by[d.rawValue] != nil {
                best = max(best, d.index + 1)
            }
        }
        return best
    }

    /// Finished on Expert with at least one harder option.
    func isMastered(_ id: String) -> Bool {
        (progress[id]?.expertModifiers ?? 0) > 0
    }

    /// How many mosaics of a pack are found right now.
    func foundLimit(packID: String) -> Int {
        let list = LevelCatalog.pack(packID)
        let finished = list.filter { progress[$0.id] != nil }.count
        return LevelCatalog.foundWhenPackOpens + finished
    }

    /// Found: the first three of its pack, one more per mosaic finished in the pack; anything
    /// finished or in progress stays found.
    func isFound(_ level: LevelDefinition) -> Bool {
        if settings.unlockAll || level.isPhoto { return true }
        guard let packID = LevelCatalog.packOfLevel[level.id], packID != "main" else { return true }
        if progress[level.id] != nil || SaveStore.hasGame(level.id) { return true }
        let list = LevelCatalog.pack(packID)
        guard let i = list.firstIndex(where: { $0.id == level.id }) else { return true }
        return i < foundLimit(packID: packID)
    }

    /// Unlocked and found: it can be played.
    func isPlayable(_ level: LevelDefinition) -> Bool {
        isUnlocked(level) && isFound(level)
    }

    func status(of level: LevelDefinition) -> CollectionStatus {
        if !isUnlocked(level) {
            return .packLocked(unlockRequirement(level) ?? "")
        }
        if !isFound(level) {
            var more = 1
            if let packID = LevelCatalog.packOfLevel[level.id],
               let i = LevelCatalog.pack(packID).firstIndex(where: { $0.id == level.id }) {
                more = max(1, i - foundLimit(packID: packID) + 1)
            }
            return .hidden(more: more)
        }
        if progress[level.id] != nil {
            return isMastered(level.id) ? .mastered : .explored(stars: stars(level.id))
        }
        return .found(moves: savedMoves(for: level) ?? 0)
    }

    func packProgress(_ levels: [LevelDefinition]) -> PackProgress {
        var p = PackProgress()
        p.total = levels.count
        for l in levels {
            if isUnlocked(l) { p.open = true }
            if isPlayable(l) { p.found += 1 }
            if progress[l.id] != nil {
                p.explored += 1
                p.stars += stars(l.id)
            }
            if isMastered(l.id) { p.mastered += 1 }
        }
        return p
    }

    /// Home's status filter.
    func passesStatus(_ level: LevelDefinition) -> Bool {
        switch settings.statusFilter {
        case .all: return true
        case .toExplore: return isPlayable(level) && progress[level.id] == nil
        case .explored: return progress[level.id] != nil
        case .goHarder: return progress[level.id] != nil && !isMastered(level.id)
        case .mastered: return isMastered(level.id)
        }
    }

    /// The harder step to offer for a mosaic finished on `difficulty` with `modifiers`.
    func harderStep(after difficulty: Difficulty, modifiers: Set<ChallengeModifier>) -> HarderStep? {
        HarderStep.after(difficulty, modifiers: modifiers)
    }
}

/// Three small stars (Gentle, Classic, Expert — filled up to the hardest finished) and the flame.
struct StarRow: View {
    let stars: Int
    var mastered = false
    var size: CGFloat = 11

    var body: some View {
        HStack(spacing: 2) {
            ForEach(0..<3, id: \.self) { k in
                Image(systemName: k < stars ? "star.fill" : "star")
                    .font(.system(size: size, weight: .bold))
                    .foregroundStyle(k < stars ? Theme.brass : Theme.panelEdge)
            }
            if mastered {
                Image(systemName: "flame.fill")
                    .font(.system(size: size, weight: .bold))
                    .foregroundStyle(Theme.danger)
            }
        }
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(mastered ? "Mastered" : "\(stars) of 3 stars")
    }
}

/// A compact card on a pack shelf: the picture (or a "?" / locked slot), the title, how hard it is on
/// the chosen difficulty, and its stars.
struct CollectionCard: View {
    @EnvironmentObject var app: AppModel
    let level: LevelDefinition
    let onPlay: () -> Void

    var body: some View {
        let status = app.status(of: level)
        return Button(action: onPlay) {
            VStack(alignment: .leading, spacing: 6) {
                picture(status)
                    .frame(width: 150, height: 170)
                Text(cardTitle(status))
                    .font(Theme.title(15))
                    .foregroundStyle(status.isPlayable ? Theme.sand : Theme.sandDim)
                    .lineLimit(1)
                    .minimumScaleFactor(0.8)
                footer(status)
                    .frame(height: 16)
            }
            .frame(width: 150, alignment: .leading)
            .contentShape(Rectangle())
        }
        .buttonStyle(PressableStyle())
        .disabled(!status.isPlayable)
        .accessibilityLabel(accessibilityText(status))
    }

    @ViewBuilder
    private func picture(_ status: CollectionStatus) -> some View {
        ZStack(alignment: .topLeading) {
            RoundedRectangle(cornerRadius: 10).fill(Color(hex: 0x2A2019))
            switch status {
            case .packLocked(let label):
                VStack(spacing: 8) {
                    Image(systemName: "lock.fill")
                        .font(.system(size: 26))
                    Text("Opens after\n\(label)")
                        .font(Theme.label(11, weight: .semibold))
                        .multilineTextAlignment(.center)
                        .padding(.horizontal, 8)
                }
                .foregroundStyle(Theme.sandDim)
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            case .hidden(let more):
                VStack(spacing: 6) {
                    Text("?")
                        .font(Theme.title(46))
                    Text(more == 1 ? "Finish 1 more\nin this pack" : "Finish \(more) more\nin this pack")
                        .font(Theme.label(11, weight: .semibold))
                        .multilineTextAlignment(.center)
                }
                .foregroundStyle(Theme.sandDim)
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            default:
                if let img = app.thumbnail(for: level) {
                    Image(decorative: img, scale: 1)
                        .resizable()
                        .interpolation(.none)
                        .aspectRatio(contentMode: .fit)
                        .padding(6)
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                }
                badge(status)
                    .padding(6)
            }
        }
        .clipShape(RoundedRectangle(cornerRadius: 10))
        .overlay(RoundedRectangle(cornerRadius: 10).strokeBorder(borderColor(status), lineWidth: 2))
    }

    @ViewBuilder
    private func badge(_ status: CollectionStatus) -> some View {
        switch status {
        case .found(let moves):
            Text(moves > 0 ? "IN PROGRESS" : "NEW")
                .font(Theme.label(10, weight: .heavy))
                .tracking(1)
                .padding(.horizontal, 7)
                .padding(.vertical, 3)
                .foregroundStyle(Color(hex: 0x2A1C12))
                .background(Capsule().fill(moves > 0 ? Theme.sand : Theme.brass))
        case .mastered:
            Image(systemName: "flame.fill")
                .font(.system(size: 14, weight: .bold))
                .foregroundStyle(Theme.danger)
                .padding(5)
                .background(Circle().fill(Theme.loam.opacity(0.85)))
        default:
            EmptyView()
        }
    }

    @ViewBuilder
    private func footer(_ status: CollectionStatus) -> some View {
        HStack(spacing: 8) {
            if status.isPlayable, let st = app.difficultyStats(for: level) {
                RatingDots(level: st.rating(app.settings.difficulty).level, size: 8)
            }
            Spacer(minLength: 0)
            switch status {
            case .explored(let s):
                StarRow(stars: s)
            case .mastered:
                StarRow(stars: 3, mastered: true)
            default:
                EmptyView()
            }
        }
    }

    private func cardTitle(_ status: CollectionStatus) -> String {
        switch status {
        case .packLocked: return "Locked"
        case .hidden: return "Undiscovered"
        default: return level.title
        }
    }

    private func borderColor(_ status: CollectionStatus) -> Color {
        switch status {
        case .found: return Theme.brass.opacity(0.9)
        case .mastered: return Theme.danger.opacity(0.8)
        case .explored: return Theme.panelEdge
        default: return Theme.panelEdge.opacity(0.6)
        }
    }

    private func accessibilityText(_ status: CollectionStatus) -> String {
        switch status {
        case .packLocked(let label): return "Locked mosaic. Opens after \(label)."
        case .hidden(let more): return "Undiscovered mosaic. Finish \(more) more in this pack to find it."
        case .found(let moves): return moves > 0 ? "\(level.title), in progress" : "\(level.title), new"
        case .explored(let s): return "\(level.title), explored, \(s) of 3 stars"
        case .mastered: return "\(level.title), mastered"
        }
    }
}

/// The collection at a glance: found, explored, stars and mastered, with a bar of stars earned.
struct CollectionSummary: View {
    let progress: PackProgress

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(alignment: .top, spacing: 16) {
                figure("\(progress.found)", "of \(progress.total) found", "magnifyingglass")
                figure("\(progress.explored)", "explored", "checkmark.seal.fill")
                figure("\(progress.stars)", "of \(progress.total * 3) stars", "star.fill")
                figure("\(progress.mastered)", "mastered", "flame.fill")
            }
            ProgressView(value: Double(progress.stars), total: Double(max(1, progress.total * 3)))
                .tint(Theme.brass)
        }
    }

    private func figure(_ value: String, _ caption: String, _ icon: String) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            HStack(spacing: 5) {
                Image(systemName: icon)
                    .font(.system(size: 13, weight: .bold))
                    .foregroundStyle(Theme.brass)
                Text(value)
                    .font(Theme.number(22))
                    .foregroundStyle(Theme.sand)
                    .monospacedDigit()
            }
            Text(caption)
                .font(Theme.label(12))
                .foregroundStyle(Theme.sandDim)
                .lineLimit(1)
                .minimumScaleFactor(0.8)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .accessibilityElement(children: .combine)
    }
}
