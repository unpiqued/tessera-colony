import SwiftUI

struct CoachBanner: View {
    let step: CoachStep
    let onDismiss: () -> Void

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            Image(systemName: "ant.fill")
                .font(.system(size: 22, weight: .bold))
                .foregroundStyle(Theme.brass)
                .padding(.top, 2)
            VStack(alignment: .leading, spacing: 4) {
                Text(step.title)
                    .font(Theme.title(18))
                    .foregroundStyle(Theme.sand)
                Text(step.message)
                    .font(Theme.label(14))
                    .foregroundStyle(Theme.sandDim)
                    .fixedSize(horizontal: false, vertical: true)
            }
            Spacer(minLength: 0)
            Button("Got it", action: onDismiss)
                .buttonStyle(PillButtonStyle(prominent: true))
        }
        .padding(14)
        .frame(maxWidth: 560)
        .background(RoundedRectangle(cornerRadius: 16, style: .continuous).fill(Theme.panel.opacity(0.97)))
        .overlay(RoundedRectangle(cornerRadius: 16, style: .continuous).strokeBorder(Theme.brass.opacity(0.7), lineWidth: 1.5))
        .shadow(color: .black.opacity(0.5), radius: 16, y: 6)
    }
}

struct JamCard: View {
    @ObservedObject var controller: GameController
    @EnvironmentObject var app: AppModel

    var body: some View {
        VStack(spacing: 14) {
            Image(systemName: "exclamationmark.triangle.fill")
                .font(.system(size: 34))
                .foregroundStyle(Theme.danger)
            Text("The colony is blocked")
                .font(Theme.title(26))
                .foregroundStyle(Theme.sand)
            Text(explanation)
                .font(Theme.label(15))
                .foregroundStyle(Theme.sandDim)
                .multilineTextAlignment(.center)
                .fixedSize(horizontal: false, vertical: true)
            VStack(spacing: 10) {
                if controller.canUndo {
                    Button {
                        controller.undo()
                    } label: {
                        Label(controller.undosLeft.map { "Undo the last move (\($0) left)" } ?? "Undo the last move",
                              systemImage: "arrow.uturn.backward")
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(PillButtonStyle(prominent: true))
                }
                if controller.assistsAllowed {
                    Button {
                        controller.addChamber()
                    } label: {
                        Label("Add a slot", systemImage: "plus.square.dashed")
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(PillButtonStyle(prominent: false))
                }
                if controller.jammedTeam != nil {
                    Button {
                        controller.recallJammed()
                    } label: {
                        Label("Return the blocked team to its tunnel", systemImage: "arrow.down.to.line")
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(PillButtonStyle(prominent: false))
                }
            }
            if !controller.chambers.isEmpty && controller.assistsAllowed {
                VStack(alignment: .leading, spacing: 8) {
                    Text("Or open a slot — tap a waiting team to return it to its tunnel:")
                        .font(Theme.label(13))
                        .foregroundStyle(Theme.sandDim)
                        .fixedSize(horizontal: false, vertical: true)
                    HStack(spacing: 8) {
                        ForEach(Array(controller.chambers.enumerated()), id: \.offset) { i, team in
                            Button {
                                controller.recall(i)
                            } label: {
                                ChamberPod(palette: controller.palette, team: team, size: 54)
                            }
                            .buttonStyle(.plain)
                            .accessibilityLabel("Return the \(controller.palette.name(team.family)) team waiting for \(team.remaining) tiles to its tunnel")
                        }
                    }
                }
                .frame(maxWidth: .infinity, alignment: .leading)
            }
            HStack(spacing: 10) {
                if controller.hintsAllowed {
                    Button("Hint") { controller.requestHint() }
                        .buttonStyle(PillButtonStyle(prominent: false))
                }
                Button("Restart") { controller.restart() }
                    .buttonStyle(PillButtonStyle(prominent: !hasWayOut))
                Button("Home") { app.goHome() }
                    .buttonStyle(PillButtonStyle(prominent: false))
            }
        }
        .padding(24)
        .frame(maxWidth: 440)
        .background(RoundedRectangle(cornerRadius: 22, style: .continuous).fill(Theme.panel))
        .overlay(RoundedRectangle(cornerRadius: 22, style: .continuous).strokeBorder(Theme.danger.opacity(0.8), lineWidth: 2))
        .shadow(color: .black.opacity(0.6), radius: 24, y: 8)
    }

    /// Undo or an assist can still get the game going.
    private var hasWayOut: Bool { controller.canUndo || controller.assistsAllowed || controller.jammedTeam != nil }

    private var explanation: String {
        var s: String
        if let j = controller.jammedTeam {
            s = "A team still needs \(j.remaining) tiles it can't reach, and every slot is taken."
        } else {
            s = "Every one of the \(controller.capacity) slots holds a team waiting for tiles it can't reach yet, so no team can be sent."
        }
        if !hasWayOut {
            s += " With this game's harder options (no undos left, no assists) the only way on is to restart."
        }
        return s
    }
}

struct WinCard: View {
    @ObservedObject var controller: GameController
    let onGallery: () -> Void
    let onNext: (() -> Void)?
    /// Called when the name box gains or loses focus (the game screen scrolls it above the keyboard).
    var onEditingName: (Bool) -> Void = { _ in }
    /// The next harder way to play this mosaic ("Try it on Expert", "Expert + No hints"), if any.
    var harderLabel: String? = nil
    var onHarder: () -> Void = {}
    @State private var name = ""
    @FocusState private var nameFocused: Bool

    static let nameFieldID = "highScoreNameField"

    private var timeText: String { TimeText.mmss(controller.elapsed) }

    var body: some View {
        content
        .frame(maxWidth: 480)
        .background(RoundedRectangle(cornerRadius: 24, style: .continuous).fill(Theme.panel))
        .overlay(RoundedRectangle(cornerRadius: 24, style: .continuous).strokeBorder(Theme.brass.opacity(0.8), lineWidth: 2))
        .shadow(color: .black.opacity(0.6), radius: 24, y: 8)
        .onAppear { if name.isEmpty { name = controller.playerName } }
        .onChange(of: nameFocused) { _, focused in onEditingName(focused) }
    }

    private var content: some View {
        VStack(spacing: 14) {
            if let img = controller.miniImage {
                Image(decorative: img, scale: 1)
                    .resizable()
                    .interpolation(.none)
                    .aspectRatio(contentMode: .fit)
                    .frame(maxHeight: controller.highScoreRank != nil ? 130 : 180)
                    .clipShape(RoundedRectangle(cornerRadius: 8))
                    .overlay(RoundedRectangle(cornerRadius: 8).strokeBorder(Theme.brass, lineWidth: 3))
            }
            Text("Re-laid in the nest")
                .font(Theme.title(28))
                .foregroundStyle(Theme.sand)
            Text(subtitle)
                .font(Theme.label(15))
                .foregroundStyle(Theme.sandDim)
                .multilineTextAlignment(.center)
            if let news = controller.completionNews {
                StarRow(stars: news.stars, mastered: news.mastered, size: 20)
                if news.newBest || !news.unlocked.isEmpty || news.newStar || news.mastered {
                    VStack(spacing: 6) {
                        if news.mastered {
                            Label("Mastered — Expert with a harder option!", systemImage: "flame.fill")
                        } else if news.newStar {
                            Label(starText(news.stars), systemImage: "star.fill")
                        }
                        if news.newBest {
                            Label("New best time on \(controller.difficulty.title)!", systemImage: "stopwatch.fill")
                        }
                        if news.unlocked.count > 3 {
                            Label("Found \(news.unlocked.count) new mosaics — see Home", systemImage: "sparkles")
                        } else {
                            ForEach(news.unlocked, id: \.self) { title in
                                Label("Found: \(title)", systemImage: "sparkles")
                            }
                        }
                    }
                    .font(Theme.label(15, weight: .bold))
                    .foregroundStyle(Theme.brass)
                }
            }
            HStack(spacing: 18) {
                stat("Time", timeText)
                stat("Moves", "\(controller.moveCount)")
                stat("Undos", "\(controller.undos)")
                stat("Hints", "\(controller.hintsUsed)")
                stat("Assists", "\(controller.assistCount)")
            }
            if let b = controller.scoreBreakdown {
                scoreBlock(b)
            }
            if let label = harderLabel {
                Button(action: onHarder) {
                    Label(label, systemImage: "arrow.up.circle.fill")
                }
                .buttonStyle(PillButtonStyle(prominent: false))
                .accessibilityHint("Starts this mosaic again, harder")
            }
            HStack(spacing: 10) {
                Button("Nest gallery", action: onGallery)
                    .buttonStyle(PillButtonStyle(prominent: onNext == nil))
                Button("Play again") { controller.restart() }
                    .buttonStyle(PillButtonStyle(prominent: false))
                if let next = onNext {
                    Button("Next mosaic", action: next)
                        .buttonStyle(PillButtonStyle(prominent: true))
                }
            }
        }
        .padding(24)
    }

    private func starText(_ stars: Int) -> String {
        switch stars {
        case 1: return "Explored — your first star"
        case 2: return "Two stars — explored on Classic"
        default: return "Three stars — explored on Expert"
        }
    }

    private var subtitle: String {
        var s = "\(controller.board.tileCount) tiles carried home · \(controller.difficulty.title)"
        let n = controller.modifiers.count
        if n > 0 { s += " · \(n) harder option\(n == 1 ? "" : "s")" }
        return s
    }

    @ViewBuilder
    private func scoreBlock(_ b: ScoreRules.Breakdown) -> some View {
        VStack(spacing: 8) {
            HStack(alignment: .firstTextBaseline, spacing: 8) {
                Text("SCORE")
                    .font(Theme.label(12, weight: .bold))
                    .tracking(1.5)
                    .foregroundStyle(Theme.brass)
                Text(b.score.formatted())
                    .font(Theme.number(30))
                    .foregroundStyle(Theme.sand)
                    .monospacedDigit()
            }
            Text(breakdownText(b))
                .font(Theme.label(12))
                .foregroundStyle(Theme.sandDim)
                .multilineTextAlignment(.center)
                .fixedSize(horizontal: false, vertical: true)
            if let place = controller.savedHighScorePlace {
                Label(place > 0 ? "Saved — #\(place) on \(controller.level.title)" : "Saved", systemImage: "trophy.fill")
                    .font(Theme.label(14, weight: .bold))
                    .foregroundStyle(Theme.ok)
            } else if let rank = controller.highScoreRank {
                VStack(spacing: 8) {
                    Label(rank == 1 ? "New high score on \(controller.level.title)!" : "High score — #\(rank) on \(controller.level.title)!",
                          systemImage: "trophy.fill")
                        .font(Theme.label(15, weight: .bold))
                        .foregroundStyle(Theme.brass)
                    HStack(spacing: 8) {
                        NameBox(name: $name, focused: $nameFocused, onSubmit: saveScore)
                        Button("Save", action: saveScore)
                            .buttonStyle(PillButtonStyle(prominent: true))
                    }
                    .id(WinCard.nameFieldID)
                    Text("Tap the box, type your name, then Save.")
                        .font(Theme.label(12))
                        .foregroundStyle(Theme.sandDim)
                }
            } else if let top = controller.topScores.first {
                Text("High score to beat: \(top.score.formatted()) by \(top.name)")
                    .font(Theme.label(13, weight: .semibold))
                    .foregroundStyle(Theme.sandDim)
            }
            let top = controller.topScores
            if !top.isEmpty && (controller.savedHighScorePlace != nil || controller.highScoreRank == nil) {
                HighScoreList(entries: top, highlight: controller.savedHighScorePlace.map { $0 - 1 }, compact: true)
            }
        }
        .padding(12)
        .frame(maxWidth: .infinity)
        .background(RoundedRectangle(cornerRadius: 16, style: .continuous).fill(Theme.loamRaised.opacity(0.7)))
    }

    private func saveScore() {
        nameFocused = false
        controller.saveHighScore(name: name)
    }

    private func breakdownText(_ b: ScoreRules.Breakdown) -> String {
        var s = "\(b.tiles.formatted()) tiles × \(fmt(b.difficultyFactor)) \(controller.difficulty.title)"
        if b.modifierFactor > 1.0001 { s += " × \(fmt(b.modifierFactor)) harder options" }
        var minus: [String] = []
        if b.undoPenalty > 0 { minus.append("\(b.undoPenalty) undos") }
        if b.hintPenalty > 0 { minus.append("\(b.hintPenalty) hints") }
        if b.assistPenalty > 0 { minus.append("\(b.assistPenalty) assists") }
        if !minus.isEmpty { s += " − " + minus.joined(separator: " − ") }
        return s
    }

    private func fmt(_ v: Double) -> String {
        let r = (v * 100).rounded() / 100
        return r == r.rounded() ? String(format: "%.0f", r) : String(format: "%.2f", r)
    }

    private func stat(_ title: String, _ value: String) -> some View {
        VStack(spacing: 2) {
            Text(value)
                .font(Theme.number(22))
                .foregroundStyle(Theme.sand)
                .monospacedDigit()
            Text(title.uppercased())
                .font(Theme.label(11, weight: .bold))
                .tracking(1.2)
                .foregroundStyle(Theme.sandDim)
        }
    }
}

/// The name box on the finish card and the two-player result card. The whole box is tappable (a
/// plain TextField only responds on its line of text, so taps on the rest of the box used to do
/// nothing), it lights up while typing, and names are limited to 20 characters.
struct NameBox: View {
    @Binding var name: String
    var focused: FocusState<Bool>.Binding
    var placeholder = "Your name"
    var accent: Color = Theme.brass
    let onSubmit: () -> Void

    var body: some View {
        TextField(placeholder, text: $name)
            .textInputAutocapitalization(.words)
            .autocorrectionDisabled()
            .submitLabel(.done)
            .focused(focused)
            .onSubmit(onSubmit)
            .onChange(of: name) { _, v in
                if v.count > HighScoreNames.maxLength { name = String(v.prefix(HighScoreNames.maxLength)) }
            }
            .font(Theme.label(18, weight: .semibold))
            .foregroundStyle(Theme.sand)
            .tint(accent)
            .frame(maxWidth: .infinity, minHeight: 50)
            .padding(.horizontal, 14)
            .background(RoundedRectangle(cornerRadius: 12).fill(Theme.loamRaised))
            .overlay(RoundedRectangle(cornerRadius: 12)
                .strokeBorder(focused.wrappedValue ? accent : accent.opacity(0.6), lineWidth: focused.wrappedValue ? 2.5 : 1.5))
            .contentShape(RoundedRectangle(cornerRadius: 12))
            .onTapGesture { focused.wrappedValue = true }
            .accessibilityLabel("Name for the high-score table")
    }
}

/// A mosaic's top scores: place, name, score, how it was played, time.
struct HighScoreList: View {
    let entries: [HighScoreEntry]
    var highlight: Int? = nil
    var compact = false

    var body: some View {
        VStack(spacing: compact ? 3 : 6) {
            ForEach(Array(entries.enumerated()), id: \.element.id) { i, e in
                HStack(spacing: 8) {
                    Text("\(i + 1)")
                        .font(Theme.label(13, weight: .bold))
                        .foregroundStyle(i == 0 ? Theme.brass : Theme.sandDim)
                        .frame(width: 18, alignment: .trailing)
                    Text(e.name)
                        .font(Theme.label(14, weight: .semibold))
                        .foregroundStyle(Theme.sand)
                        .lineLimit(1)
                    if !compact {
                        Text(howPlayed(e))
                            .font(Theme.label(11))
                            .foregroundStyle(Theme.sandDim)
                            .lineLimit(1)
                            .minimumScaleFactor(0.8)
                    }
                    Spacer(minLength: 4)
                    ForEach(e.modifiers) { m in
                        Image(systemName: m.systemImage)
                            .font(.system(size: 10, weight: .semibold))
                            .foregroundStyle(Theme.danger)
                    }
                    Text(TimeText.mmss(e.seconds))
                        .font(Theme.label(12))
                        .foregroundStyle(Theme.sandDim)
                        .monospacedDigit()
                    Text(e.score.formatted())
                        .font(Theme.label(15, weight: .bold))
                        .foregroundStyle(Theme.sand)
                        .monospacedDigit()
                        .frame(minWidth: 54, alignment: .trailing)
                }
                .padding(.horizontal, 8)
                .padding(.vertical, compact ? 3 : 6)
                .background(RoundedRectangle(cornerRadius: 8).fill(highlight == i ? Theme.brass.opacity(0.22) : Color.clear))
                .accessibilityElement(children: .ignore)
                .accessibilityLabel("\(i + 1). \(e.name), \(e.score) points, \(howPlayed(e)), time \(TimeText.mmss(e.seconds))")
            }
        }
    }

    private func howPlayed(_ e: HighScoreEntry) -> String {
        if !e.detail.isEmpty { return e.detail }
        var s = e.difficulty.title
        if !e.modifiers.isEmpty { s += " + " + e.modifiers.map { $0.title }.joined(separator: ", ") }
        return s
    }
}

struct HowToPlayView: View {
    @Environment(\.dismiss) private var dismiss

    private struct Rule: Identifiable {
        let icon: String
        let title: String
        let text: String
        var id: String { title }
        init(_ icon: String, _ title: String, _ text: String) {
            self.icon = icon
            self.title = title
            self.text = text
        }
    }

    private let rules: [Rule] = [
        Rule("ant.fill", "Send a team", "Tap the team at the front of any tunnel. Its ants leave the hill and claim every tile of their colour they can reach, nearest first, up to the team's number. Each tap sends the next team in that tunnel — as long as a slot is open."),
        Rule("square.stack.fill", "Slots", "Every team you send takes a slot. The number on a working team counts down as its ants pick up tiles; when it reaches zero the slot opens again. Several teams can work at once, one per slot, and you can't send more than the open slots allow."),
        Rule("square.grid.3x3.fill", "Reachable tiles", "Ants walk only on open ground. A tile can be taken when it touches open ground connected to the hill. A team can tunnel through its own colour."),
        Rule("hourglass", "Waiting teams", "To make a team wait, just send it. If it can't reach all its tiles yet, it keeps its slot and waits, resuming by itself as its colour is uncovered. Waiting teams are the ones that can block you, so scout first if you're unsure."),
        Rule("exclamationmark.triangle.fill", "Blocked?", "If every slot holds a waiting team, nothing can be sent. Undo is free and unlimited. You can also add a slot, or tap a waiting team to return it to the front of its tunnel and open its slot."),
        Rule("eye.fill", "Scout", "Press and hold a team to preview exactly which tiles it would take and whether it would have to wait."),
        Rule("lightbulb.fill", "Hints", "A hint suggests the next team, or tells you how many moves to undo to get back to a winning line."),
        Rule("slider.horizontal.3", "Difficulty", "Choose Gentle, Classic or Expert at the top of Home (or on a mosaic's start card). Each mosaic shows its slots and a measured rating from Relaxed to Fiendish, with how often careless tapping wins. The Show filter keeps only Easy, Medium, Hard or Fiendish mosaics."),
        Rule("flame.fill", "Packs and your collection", "193 mosaics in twenty-five packs, grouped into themes: the main Mosaics, Seasons (Halloween, Winter — the one in season wears a badge), Nature (Garden, Wild Wonders, Natural History), Art (Gallery, World Art, World Craft), Literature (Epics & Legends, Fairy Tales & Fables, Children's Classics, Shakespeare, Adventure Classics, Gothic & Mystery, Great Novels), History (Ancient World, Voyages, Modern Moments, Inventions & Firsts), Sky & Science (Sky & Science, Probes & Telescopes, Geometry & Illusions), and the Challenge and Master packs. When a pack opens, its first three mosaics are found; each one you finish finds another (the rest show as ?). Finishing earns stars — one for Gentle, two for Classic, three for Expert — and a flame for Expert with a harder option. The Status filter on Home finds what to explore next or what to play harder. On the hardest mosaics, sending whatever can finish now isn't enough — scout, plan ahead and use undo."),
        Rule("eye.slash", "Harder options", "On the start card: Hidden queue, No scouting, No hints, 3 undos, No assists and No colour twice. Each one raises your score multiplier; none makes a mosaic impossible."),
        Rule("trophy.fill", "High scores", "Score = tiles × difficulty (Gentle ×0.5, Classic ×1, Expert ×1.5) × harder options, minus 5 per undo, 25 per hint and 25 per assist. Make a mosaic's top 5 and type your name on the finish card. Home → High scores shows every table."),
        Rule("xmark", "Leaving a game", "The X in the top-left corner goes straight back to Home. The game is saved — Resume picks it up."),
        Rule("person.2.fill", "Two players", "Home → Two players (the big button at the top). The winner can put their name on the mosaic's two-player high-score table. Race on two copies of a mosaic (split screen) or share one board with two ant hills. Choose Front team only or Reach 3 (jumping the queue costs 3 points a place), any colour or no colour twice in a row, and slot upkeep or a flat slot cost. Score = tiles your ants carry home minus penalties."),
        Rule("point.topleft.down.curvedto.point.bottomright.up", "Ant paths", "Menu → Ant paths changes how newly launched ants walk to their tiles: Direct, Natural, Curious (some stop to sniff), Wall-hugger, Scout trail (a fading trail the team follows), Random per team (the default — each team picks one of the styles when it is sent) or Random per ant. Ants carrying tiles come home in the middle lane."),
        Rule("speaker.wave.2.fill", "Sound", "Wood-and-clay sounds for your moves, bells and glass for goals (a team done, a colour lifted, every quarter home, the finish, a new best, an unlock), and a clink for every tile. Each set has its own switch in Settings."),
        Rule("tortoise.fill", "Ant speed", "Drag the Ant speed slider (0.1× to 16×) to watch the colony crawl slowly or hurry. Ants already walking just change pace. The setting is remembered."),
        Rule("paintpalette", "Ground colour", "Menu → Ground colour… sets the colour behind the mosaic: pick a preset or any colour."),
        Rule("hand.pinch.fill", "Zoom", "Pinch the board to watch the ants up close; drag to pan; double-tap to reset."),
        Rule("photo.on.rectangle", "Your photos", "Turn any photo into a mosaic from the home screen. White and near-white areas become open ground, so no moves are wasted on background."),
        Rule("paintpalette.fill", "Colours", "Tiles are shaded, but shading never changes a tile's colour family. Team pieces are made of the same tiles they collect; each ant is painted the colour of the tile it is fetching.")
    ]

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 18) {
                    ForEach(rules) { rule in
                        HStack(alignment: .top, spacing: 14) {
                            Image(systemName: rule.icon)
                                .font(.system(size: 22, weight: .semibold))
                                .foregroundStyle(Theme.brass)
                                .frame(width: 34)
                            VStack(alignment: .leading, spacing: 4) {
                                Text(rule.title).font(Theme.title(19)).foregroundStyle(Theme.sand)
                                Text(rule.text).font(Theme.label(15)).foregroundStyle(Theme.sandDim)
                                    .fixedSize(horizontal: false, vertical: true)
                            }
                        }
                    }
                    Text("Colour families in the built-in mosaics")
                        .font(Theme.title(19))
                        .foregroundStyle(Theme.sand)
                        .padding(.top, 6)
                    LazyVGrid(columns: [GridItem(.adaptive(minimum: 120), spacing: 10)], spacing: 10) {
                        ForEach(0..<GeneratedPalette.builtIn.familyCount, id: \.self) { f in
                            VStack(alignment: .leading, spacing: 4) {
                                TesseraSwatch(palette: GeneratedPalette.builtIn, family: f, tile: 12)
                                    .frame(height: 36)
                                    .clipShape(RoundedRectangle(cornerRadius: 8))
                                Text(GeneratedPalette.builtIn.name(f))
                                    .font(Theme.label(13, weight: .bold))
                                    .foregroundStyle(Theme.sandDim)
                            }
                        }
                    }
                }
                .padding(22)
            }
            .background(Theme.loam.ignoresSafeArea())
            .navigationTitle("How to play")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button("Done") { dismiss() }
                }
            }
        }
        .preferredColorScheme(.dark)
    }
}
