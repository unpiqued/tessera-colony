import SwiftUI

/// Two players on one iPad. Landscape: side by side. Portrait: face to face (the top half is turned
/// round for the player sitting opposite). Race = two compact boards; Shared = one board in the middle.
struct VersusView: View {
    @ObservedObject var controller: VersusController
    @EnvironmentObject var app: AppModel
    @State private var confirmQuit = false

    var body: some View {
        ZStack {
            GeometryReader { geo in
                let wide = geo.size.width >= geo.size.height
                ZStack {
                    GroundPresets.backdrop(controller.groundColor).ignoresSafeArea()
                    VStack(spacing: 6) {
                        topBar
                        if controller.rules.layout == .race {
                            if wide {
                                HStack(spacing: 10) {
                                    raceColumn(0)
                                    raceColumn(1)
                                }
                            } else {
                                VStack(spacing: 8) {
                                    raceColumn(1).rotationEffect(.degrees(180))
                                    raceColumn(0)
                                }
                            }
                        } else {
                            if wide {
                                HStack(alignment: .top, spacing: 10) {
                                    VersusControls(controller: controller, player: 0)
                                        .frame(width: min(330, geo.size.width * 0.28))
                                    VersusBoardView(controller: controller, index: 0)
                                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                                    VersusControls(controller: controller, player: 1)
                                        .frame(width: min(330, geo.size.width * 0.28))
                                }
                            } else {
                                VStack(spacing: 6) {
                                    VersusControls(controller: controller, player: 1)
                                        .rotationEffect(.degrees(180))
                                    VersusBoardView(controller: controller, index: 0)
                                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                                    VersusControls(controller: controller, player: 0)
                                }
                            }
                        }
                    }
                    .padding(10)
                }
            }
            // the boards keep their size (and layout) when the keyboard comes up for the winner's name
            .ignoresSafeArea(.keyboard, edges: .bottom)
            if let r = controller.result {
                Color.black.opacity(0.55).ignoresSafeArea()
                GeometryReader { g in
                    ScrollViewReader { proxy in
                        ScrollView {
                            VersusResultCard(controller: controller, result: r, onRematch: {
                                app.startVersus(level: controller.level, rules: controller.rules)
                            }, onHome: {
                                app.endVersus()
                            }, onEditingName: { editing in
                                guard editing else { return }
                                Task { @MainActor in
                                    // wait for the keyboard to finish sliding up, then bring the name box into view
                                    try? await Task.sleep(nanoseconds: 350_000_000)
                                    withAnimation(.easeOut(duration: 0.25)) {
                                        proxy.scrollTo(WinCard.nameFieldID, anchor: .center)
                                    }
                                }
                            })
                            .frame(maxWidth: .infinity, minHeight: g.size.height)
                        }
                        .scrollBounceBehavior(.basedOnSize)
                    }
                }
            }
        }
        .task {
            while !Task.isCancelled {
                controller.tick()
                try? await Task.sleep(nanoseconds: 100_000_000)
            }
        }
        .sensoryFeedback(.impact(weight: .light), trigger: controller.sendTick)
        .sensoryFeedback(.warning, trigger: controller.refusedTick)
        .alert("Leave this match?", isPresented: $confirmQuit) {
            Button("Leave", role: .destructive) { app.endVersus() }
            Button("Keep playing", role: .cancel) {}
        }
        .preferredColorScheme(.dark)
    }

    private func raceColumn(_ p: Int) -> some View {
        VStack(spacing: 6) {
            VersusBoardView(controller: controller, index: p)
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                .layoutPriority(1)
            VersusControls(controller: controller, player: p)
        }
        .padding(8)
        .background(RoundedRectangle(cornerRadius: 18, style: .continuous).fill(Theme.panel.opacity(0.85)))
        .overlay(RoundedRectangle(cornerRadius: 18, style: .continuous)
            .strokeBorder(Color(hex: BoardPainter.playerColors[p]).opacity(0.7), lineWidth: 2))
    }

    private var topBar: some View {
        HStack(spacing: 12) {
            Button { confirmQuit = true } label: {
                Image(systemName: "xmark.circle.fill")
                    .font(.system(size: 26))
                    .foregroundStyle(Theme.sandDim)
                    .frame(width: 44, height: 40)
            }
            .accessibilityLabel("Leave the match")
            Text("\(controller.level.title) · \(controller.rules.layout.title) · \(controller.rules.picking.title) · \(controller.rules.colour.title) · \(controller.rules.scoring.title) · \(controller.rules.difficulty.title)")
                .font(Theme.label(12))
                .foregroundStyle(Theme.sandDim)
                .lineLimit(1)
                .minimumScaleFactor(0.7)
            Spacer()
            Image(systemName: "tortoise.fill").foregroundStyle(Theme.sandDim)
            Slider(value: Binding(get: { log(controller.speed) },
                                  set: { controller.setSpeed(exp($0)) }),
                   in: log(GameController.speedRange.lowerBound)...log(GameController.speedRange.upperBound))
                .frame(maxWidth: 220)
                .tint(Theme.brass)
            Text(String(format: "%.1f×", controller.speed))
                .font(Theme.label(12, weight: .bold))
                .foregroundStyle(Theme.sand)
                .monospacedDigit()
                .frame(width: 40)
        }
    }
}

/// One board of the match: the same painter as the single-player board, sized to fit.
struct VersusBoardView: View {
    @ObservedObject var controller: VersusController
    let index: Int
    @Environment(\.displayScale) private var displayScale

    var body: some View {
        GeometryReader { geo in
            let b = controller.board(index)
            let cs = max(2, min(geo.size.width / CGFloat(b.cols), geo.size.height / CGFloat(b.rows)))
            let size = CGSize(width: CGFloat(b.cols) * cs, height: CGFloat(b.rows) * cs)
            TimelineView(.animation(minimumInterval: nil, paused: !controller.animating)) { timeline in
                Canvas { ctx, _ in
                    draw(&ctx, date: timeline.date, cs: cs, size: size)
                }
            }
            .frame(width: size.width, height: size.height)
            .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
            .overlay(RoundedRectangle(cornerRadius: 10, style: .continuous).strokeBorder(Theme.panelEdge, lineWidth: 1))
            .frame(width: geo.size.width, height: geo.size.height)
        }
        .accessibilityElement()
        .accessibilityLabel("Mosaic board")
    }

    private func draw(_ ctx: inout GraphicsContext, date: Date, cs: CGFloat, size: CGSize) {
        let vb = controller.match.boards[index]
        let b = vb.board
        let t = controller.gameTime(at: date)
        controller.ensureRaster(index, cellPx: max(2, Int((cs * displayScale).rounded())))
        let trips = controller.schedulers[index].trips
        BoardPainter.paintBase(&ctx, board: b, cs: cs, t: t, date: date, size: size,
                               raster: controller.rasters[index], trips: trips, ground: controller.groundColor,
                               holes: Array(vb.holes.values).sorted(), sharp: false)
        if controller.rules.layout == .shared {
            // mark each hill with its player's colour
            let holes = VersusMatch.sharedHoles(b)
            for (p, h) in holes.enumerated() {
                let r = CGRect(x: (CGFloat(b.x(h)) + 0.5) * cs - 1.4 * cs, y: (CGFloat(b.y(h)) + 0.5) * cs - 0.9 * cs,
                               width: 2.8 * cs, height: 1.8 * cs)
                ctx.stroke(Path(ellipseIn: r), with: .color(Color(hex: BoardPainter.playerColors[p])), lineWidth: max(1.5, cs * 0.25))
            }
        }
        BoardPainter.paintAnts(&ctx, board: b, cs: cs, t: t, trips: trips, sprites: controller.sprites,
                               detailed: controller.detailedAnts && cs >= 5, ownerRings: controller.rules.layout == .shared)
    }
}

/// A player's compact controls: score, slots, and each tunnel with a deeper view of its queue.
struct VersusControls: View {
    @ObservedObject var controller: VersusController
    let player: Int

    private var accent: Color { Color(hex: BoardPainter.playerColors[player]) }

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            header
            slotsRow
            HStack(alignment: .top, spacing: 6) {
                ForEach(0..<controller.tunnelCount, id: \.self) { q in
                    tunnelColumn(q)
                }
            }
            Text(controller.messages[player] ?? " ")
                .font(Theme.label(11))
                .foregroundStyle(Theme.sandDim)
                .lineLimit(2)
                .frame(maxWidth: .infinity, alignment: .leading)
        }
    }

    private var header: some View {
        HStack(alignment: .firstTextBaseline, spacing: 8) {
            Circle().fill(accent).frame(width: 12, height: 12)
            Text(VersusController.names[player])
                .font(Theme.title(17))
                .foregroundStyle(Theme.sand)
            Spacer()
            Text("\(Int(controller.scores[player].rounded()))")
                .font(Theme.number(24))
                .foregroundStyle(accent)
                .monospacedDigit()
            Text("pts")
                .font(Theme.label(11))
                .foregroundStyle(Theme.sandDim)
        }
        .overlay(alignment: .bottomLeading) {
            Text("\(controller.delivered[player]) tiles home · −\(Int(controller.penalties(player).rounded())) penalties")
                .font(Theme.label(10))
                .foregroundStyle(Theme.sandDim)
                .offset(y: 13)
        }
        .padding(.bottom, 12)
    }

    private var slotsRow: some View {
        let cap = controller.capacity(player)
        let waiting = controller.waiting(player)
        let working = controller.working(player, at: controller.now)
        let pod: CGFloat = 38
        return HStack(spacing: 5) {
            Text("\(max(0, cap - controller.occupied[player])) of \(cap) open")
                .font(Theme.label(10, weight: .bold))
                .foregroundStyle(controller.occupied[player] >= cap ? Theme.brass : Theme.ok)
                .monospacedDigit()
                .frame(width: 62, alignment: .leading)
            ForEach(Array(working.enumerated()), id: \.offset) { _, w in
                ChamberPod(palette: controller.palette, team: Team(uid: w.uid, family: w.family, quota: w.left, remaining: w.left), size: pod)
            }
            ForEach(Array(waiting.enumerated()), id: \.offset) { _, w in
                // one tap returns it to the front of its tunnel and frees the slot
                Button { controller.returnTeam(player, uid: w.uid) } label: {
                    ChamberPod(palette: controller.palette, team: Team(uid: w.uid, family: w.family, quota: w.quota, remaining: w.remaining), size: pod)
                        .overlay(RoundedRectangle(cornerRadius: 14).strokeBorder(Theme.brass, lineWidth: 2))
                        .overlay(alignment: .topTrailing) { ReturnBadge(size: 15).offset(x: 4, y: -4) }
                }
                .buttonStyle(.plain)
                .accessibilityLabel("Waiting team, needs \(w.remaining) more. Double-tap to return it to its tunnel, costs \(Int(VersusRules.returnPenalty)) points.")
            }
            ForEach(0..<max(0, cap - working.count - waiting.count), id: \.self) { _ in
                ChamberPod(palette: controller.palette, team: nil, size: pod)
            }
            Button { controller.addSlot(player) } label: {
                VStack(spacing: 0) {
                    Image(systemName: "plus").font(.system(size: 13, weight: .bold))
                    Text("−\(Int(VersusRules.addSlotPenalty))").font(Theme.label(9, weight: .bold))
                }
                .foregroundStyle(Theme.brass)
                .frame(width: pod, height: pod)
                .background(RoundedRectangle(cornerRadius: 12).strokeBorder(Theme.brass.opacity(0.7), style: StrokeStyle(lineWidth: 1.5, dash: [4, 3])))
            }
            .buttonStyle(.plain)
            .accessibilityLabel("Add a slot, costs \(Int(VersusRules.addSlotPenalty)) points")
            Spacer(minLength: 0)
        }
    }

    private func tunnelColumn(_ q: Int) -> some View {
        let queue = controller.queue(player, tunnel: q)
        let reach = controller.rules.reachDepth
        let shown = 7
        return VStack(spacing: 4) {
            ForEach(Array(queue.prefix(shown).enumerated()), id: \.offset) { d, team in
                if d < reach {
                    let why = controller.refusal(player, tunnel: q, depth: d)
                    Button { controller.launch(player, tunnel: q, depth: d) } label: {
                        TeamCard(palette: controller.palette, family: team.family, need: team.remaining,
                                 height: d == 0 ? 54 : 42, highlighted: false, dimmed: why != nil)
                            .overlay(alignment: .topTrailing) {
                                if d > 0 {
                                    Text("−\(Int(Double(d) * VersusRules.skipPenalty))")
                                        .font(Theme.label(10, weight: .bold))
                                        .foregroundStyle(.white)
                                        .padding(.horizontal, 4)
                                        .background(Capsule().fill(Color.black.opacity(0.55)))
                                        .padding(3)
                                }
                            }
                    }
                    .buttonStyle(.plain)
                    .accessibilityLabel("\(controller.palette.name(team.family)) team of \(team.remaining)" + (d > 0 ? ", \(d) back in the queue" : ""))
                } else {
                    TeamCard(palette: controller.palette, family: team.family, need: team.remaining, height: 22)
                        .opacity(0.85 - 0.08 * Double(d - reach))
                        .accessibilityLabel("Later: \(controller.palette.name(team.family)) team of \(team.remaining)")
                }
            }
            if queue.count > shown {
                Text("+\(queue.count - shown)")
                    .font(Theme.label(10, weight: .bold))
                    .foregroundStyle(Theme.sandDim)
            }
            if queue.isEmpty {
                RoundedRectangle(cornerRadius: 12)
                    .strokeBorder(Theme.panelEdge, style: StrokeStyle(lineWidth: 1, dash: [4, 3]))
                    .frame(height: 54)
                    .overlay(Text("Empty").font(Theme.label(11)).foregroundStyle(Theme.sandDim))
            }
        }
        .frame(maxWidth: .infinity, alignment: .top)
    }
}

/// End of the match: both scores with their breakdown.
struct VersusResultCard: View {
    @ObservedObject var controller: VersusController
    let result: VersusResult
    let onRematch: () -> Void
    let onHome: () -> Void
    var onEditingName: (Bool) -> Void = { _ in }
    @State private var name = ""
    @FocusState private var nameFocused: Bool

    var body: some View {
        VStack(spacing: 14) {
            Text(title)
                .font(Theme.title(30))
                .foregroundStyle(Theme.sand)
            if let f = result.finisher {
                Text("\(VersusController.names[f]) cleared the mosaic first.")
                    .font(Theme.label(14))
                    .foregroundStyle(Theme.sandDim)
            }
            HStack(alignment: .top, spacing: 18) {
                ForEach(0..<2, id: \.self) { p in column(p) }
            }
            if let w = result.winner {
                highScoreBlock(winner: w)
            }
            HStack(spacing: 10) {
                Button("Rematch", action: onRematch)
                    .buttonStyle(PillButtonStyle(prominent: true))
                Button("Home", action: onHome)
                    .buttonStyle(PillButtonStyle(prominent: false))
            }
        }
        .padding(24)
        .frame(maxWidth: 560)
        .background(RoundedRectangle(cornerRadius: 24, style: .continuous).fill(Theme.panel))
        .overlay(RoundedRectangle(cornerRadius: 24, style: .continuous).strokeBorder(Theme.brass.opacity(0.8), lineWidth: 2))
        .padding(20)
        .onChange(of: nameFocused) { _, focused in onEditingName(focused) }
    }

    @ViewBuilder
    private func highScoreBlock(winner w: Int) -> some View {
        VStack(spacing: 8) {
            if let place = controller.savedHighScorePlace {
                Label(place > 0 ? "Saved — #\(place) on the two-player table for \(controller.level.title)" : "Saved",
                      systemImage: "trophy.fill")
                    .font(Theme.label(14, weight: .bold))
                    .foregroundStyle(Theme.ok)
            } else if let rank = controller.highScoreRank {
                Label(rank == 1 ? "New two-player high score!" : "Two-player high score — #\(rank)!", systemImage: "trophy.fill")
                    .font(Theme.label(15, weight: .bold))
                    .foregroundStyle(Theme.brass)
                Text("\(VersusController.names[w]), enter your name for the table:")
                    .font(Theme.label(13))
                    .foregroundStyle(Theme.sandDim)
                HStack(spacing: 8) {
                    NameBox(name: $name, focused: $nameFocused, placeholder: "Winner's name",
                            accent: Color(hex: BoardPainter.playerColors[w]), onSubmit: save)
                    Button("Save", action: save)
                        .buttonStyle(PillButtonStyle(prominent: true))
                }
                .id(WinCard.nameFieldID)
            } else if let top = controller.topScores.first {
                Text("Two-player high score to beat: \(top.score.formatted()) by \(top.name)")
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

    private func save() {
        nameFocused = false
        controller.saveWinnerScore(name: name)
    }

    private var title: String {
        guard let w = result.winner else { return "A draw!" }
        return "\(VersusController.names[w]) wins!"
    }

    private func column(_ p: Int) -> some View {
        let l = result.lines[p]
        return VStack(alignment: .leading, spacing: 4) {
            HStack {
                Circle().fill(Color(hex: BoardPainter.playerColors[p])).frame(width: 12, height: 12)
                Text(VersusController.names[p]).font(Theme.title(18)).foregroundStyle(Theme.sand)
            }
            Text("\(Int(l.score.rounded())) points")
                .font(Theme.number(26))
                .foregroundStyle(Color(hex: BoardPainter.playerColors[p]))
            line("Tiles home", "+\(l.tiles)")
            if l.bonus > 0 { line("First to finish", "+\(Int(l.bonus))") }
            if l.upkeep > 0 { line("Slot upkeep", "−\(Int(l.upkeep.rounded()))") }
            if l.addedSlots > 0 { line("Added slots ×\(l.addedSlots)", "−\(Int(Double(l.addedSlots) * VersusRules.addSlotPenalty))") }
            if l.returns > 0 { line("Returned teams ×\(l.returns)", "−\(Int(Double(l.returns) * VersusRules.returnPenalty))") }
            if l.skips > 0 { line("Queue jumps ×\(l.skips)", "−\(Int(Double(l.skips) * VersusRules.skipPenalty))") }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private func line(_ a: String, _ b: String) -> some View {
        HStack {
            Text(a).font(Theme.label(13)).foregroundStyle(Theme.sandDim)
            Spacer()
            Text(b).font(Theme.label(13, weight: .bold)).foregroundStyle(Theme.sand).monospacedDigit()
        }
    }
}

/// Home → Two players: choose the mode options and the mosaic.
struct VersusSetupSheet: View {
    @EnvironmentObject var app: AppModel
    @Environment(\.dismiss) private var dismiss
    @State private var rules = VersusRules()
    @State private var levelID = "firstDig"

    private var levels: [LevelDefinition] { LevelCatalog.builtIn + app.photoLevels.map { $0.level } }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                HStack {
                    Text("Two players")
                        .font(Theme.title(28))
                        .foregroundStyle(Theme.sand)
                    Spacer()
                    Button { dismiss() } label: {
                        Image(systemName: "xmark.circle.fill").font(.system(size: 26)).foregroundStyle(Theme.sandDim)
                    }
                    .accessibilityLabel("Close")
                }
                Text("Two players on one iPad. Every option can be combined with every other.")
                    .font(Theme.label(13))
                    .foregroundStyle(Theme.sandDim)
                option("BOARD", rules.layout.blurb) {
                    Picker("Board", selection: $rules.layout) {
                        ForEach(VersusLayout.allCases) { Text($0.title).tag($0) }
                    }
                }
                option("LAUNCHING", rules.picking.blurb) {
                    Picker("Launching", selection: $rules.picking) {
                        ForEach(VersusPicking.allCases) { Text($0.title).tag($0) }
                    }
                }
                option("COLOUR RULE", rules.colour.blurb) {
                    Picker("Colour rule", selection: $rules.colour) {
                        ForEach(VersusColourRule.allCases) { Text($0.title).tag($0) }
                    }
                }
                option("SLOT SCORING", rules.scoring.blurb) {
                    Picker("Slot scoring", selection: $rules.scoring) {
                        ForEach(VersusSlotScoring.allCases) { Text($0.title).tag($0) }
                    }
                }
                option("SLOTS EACH", "\(level.chambers(for: rules.difficulty)) slots each on this mosaic.") {
                    Picker("Slots", selection: $rules.difficulty) {
                        ForEach(Difficulty.allCases) { Text($0.title).tag($0) }
                    }
                }
                Text("MOSAIC")
                    .font(Theme.label(12, weight: .bold))
                    .tracking(1.5)
                    .foregroundStyle(Theme.brass)
                ScrollView(.horizontal, showsIndicators: false) {
                    LazyHStack(spacing: 10) {
                        ForEach(levels, id: \.id) { lv in
                            Button { levelID = lv.id } label: {
                                VStack(spacing: 4) {
                                    if let img = app.thumbnail(for: lv) {
                                        Image(decorative: img, scale: 1)
                                            .resizable()
                                            .interpolation(.none)
                                            .aspectRatio(contentMode: .fit)
                                            .frame(width: 84, height: 96)
                                    }
                                    Text(lv.title)
                                        .font(Theme.label(11, weight: .bold))
                                        .foregroundStyle(Theme.sand)
                                        .lineLimit(1)
                                        .frame(width: 96)
                                    Text("\(lv.tileCount) tiles")
                                        .font(Theme.label(10))
                                        .foregroundStyle(Theme.sandDim)
                                }
                                .padding(6)
                                .background(RoundedRectangle(cornerRadius: 12).fill(levelID == lv.id ? Theme.loamRaised : Theme.panel))
                                .overlay(RoundedRectangle(cornerRadius: 12).strokeBorder(levelID == lv.id ? Theme.brass : Theme.panelEdge,
                                                                                         lineWidth: levelID == lv.id ? 2.5 : 1))
                            }
                            .buttonStyle(.plain)
                        }
                    }
                }
                Text("Score: tiles your ants carry home, minus penalties (added slots −25, returned teams −10, queue jumps −3 per place, and slot upkeep if chosen). In a race, the first to clear their mosaic gets a bonus of 15% of its tiles and ends the match.")
                    .font(Theme.label(12))
                    .foregroundStyle(Theme.sandDim)
                    .fixedSize(horizontal: false, vertical: true)
            }
            .padding(22)
        }
        .safeAreaInset(edge: .bottom, spacing: 0) {
            VStack(spacing: 0) {
                Rectangle().fill(Theme.panelEdge).frame(height: 1)
                Button {
                    app.settings.versusRules = rules
                    app.settings.versusLevelID = levelID
                    dismiss()
                    app.startVersus(level: level, rules: rules)
                } label: {
                    Text("Start the match").frame(maxWidth: .infinity)
                }
                .buttonStyle(PillButtonStyle(prominent: true))
                .padding(.horizontal, 22)
                .padding(.vertical, 14)
            }
            .background(Theme.loamRaised.ignoresSafeArea())
        }
        .background(Theme.loam.ignoresSafeArea())
        .preferredColorScheme(.dark)
        .onAppear {
            rules = app.settings.versusRules
            if levels.contains(where: { $0.id == app.settings.versusLevelID }) { levelID = app.settings.versusLevelID }
        }
    }

    private var level: LevelDefinition { levels.first(where: { $0.id == levelID }) ?? LevelCatalog.main[0] }

    private func option<C: View>(_ title: String, _ blurb: String, @ViewBuilder picker: () -> C) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(title)
                .font(Theme.label(12, weight: .bold))
                .tracking(1.5)
                .foregroundStyle(Theme.brass)
            picker()
                .pickerStyle(.segmented)
            Text(blurb)
                .font(Theme.label(12))
                .foregroundStyle(Theme.sandDim)
                .fixedSize(horizontal: false, vertical: true)
        }
    }
}
