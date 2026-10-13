import SwiftUI

/// A patch of glazed tesserae in one colour family's own tones (no symbols).
struct TesseraSwatch: View {
    let palette: LevelPalette
    let family: Int
    var tile: CGFloat = 13

    var body: some View {
        Canvas { ctx, size in
            guard tile > 0, size.width.isFinite, size.height.isFinite, size.width > 0, size.height > 0 else { return }
            let cols = min(400, Int((size.width / tile).rounded(.up)))
            let rows = min(400, Int((size.height / tile).rounded(.up)))
            let grout = Color(hex: 0x1E1611).opacity(0.55)
            ctx.fill(Path(CGRect(origin: .zero, size: size)), with: .color(FamilyStyle.tone(palette, family, 2)))
            for y in 0..<rows {
                for x in 0..<cols {
                    let h = hash32(x + family * 97, y * 31 + family)
                    let pick = Int(h % 10)
                    let tone = pick < 3 ? 0 : (pick < 7 ? 1 : (pick < 9 ? 2 : 3))
                    let r = CGRect(x: CGFloat(x) * tile, y: CGFloat(y) * tile, width: tile - 1, height: tile - 1)
                    ctx.fill(Path(roundedRect: r, cornerRadius: 2), with: .color(FamilyStyle.tone(palette, family, tone)))
                    ctx.stroke(Path(roundedRect: r, cornerRadius: 2), with: .color(grout), lineWidth: 0.5)
                }
            }
        }
        .allowsHitTesting(false)
    }
}

/// A team button: a piece made of the colour it collects, showing only the number of tiles it needs.
struct TeamCard: View {
    let palette: LevelPalette
    let family: Int
    let need: Int
    var height: CGFloat = 104
    var highlighted = false
    var dimmed = false

    var body: some View {
        ZStack {
            TesseraSwatch(palette: palette, family: family, tile: max(10, height / 7))
                .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
            RoundedRectangle(cornerRadius: 16, style: .continuous)
                .fill(LinearGradient(colors: [Color.white.opacity(0.22), Color.clear, Color.black.opacity(0.22)],
                                     startPoint: .top, endPoint: .bottom))
            Text("\(need)")
                .font(Theme.number(height * 0.36))
                .monospacedDigit()
                .foregroundStyle(FamilyStyle.ink(palette, family))
                .shadow(color: FamilyStyle.inkShadow(palette, family), radius: 2, y: 1)
                .minimumScaleFactor(0.5)
                .lineLimit(1)
                .padding(.horizontal, 6)
        }
        .frame(height: height)
        .overlay(
            RoundedRectangle(cornerRadius: 16, style: .continuous)
                .strokeBorder(highlighted ? Theme.brass : Color.black.opacity(0.4), lineWidth: highlighted ? 4 : 1)
        )
        .shadow(color: highlighted ? Theme.brass.opacity(0.7) : .black.opacity(0.35), radius: highlighted ? 10 : 4, y: 2)
        .opacity(dimmed ? 0.45 : 1)
    }
}

struct MiniTeamChip: View {
    let palette: LevelPalette
    let spec: TeamSpec
    var body: some View {
        ZStack {
            TesseraSwatch(palette: palette, family: spec.family, tile: 9)
                .clipShape(Capsule())
            Text("\(spec.quota)")
                .font(Theme.label(13, weight: .bold))
                .monospacedDigit()
                .foregroundStyle(FamilyStyle.ink(palette, spec.family))
                .shadow(color: FamilyStyle.inkShadow(palette, spec.family), radius: 1)
        }
        .frame(height: 26)
        .frame(maxWidth: .infinity)
        .overlay(Capsule().strokeBorder(Color.black.opacity(0.35), lineWidth: 1))
        .opacity(0.9)
        .accessibilityLabel("Next: \(palette.name(spec.family)) team, \(spec.quota) tiles")
    }
}

/// The little "return" mark on a waiting team: one tap sends it back to its tunnel.
/// "Same colour" on a front team refused by No colour twice.
struct SameColourTag: View {
    let shown: Bool

    var body: some View {
        if shown {
            Text("Same colour")
                .font(Theme.label(10, weight: .bold))
                .foregroundStyle(.white)
                .padding(.horizontal, 6)
                .background(Capsule().fill(Color.black.opacity(0.6)))
                .padding(4)
                .allowsHitTesting(false)
        }
    }
}

struct ReturnBadge: View {
    var size: CGFloat = 16

    var body: some View {
        Image(systemName: "arrow.uturn.down")
            .font(.system(size: size * 0.55, weight: .heavy))
            .foregroundStyle(Color(hex: 0x2A1C12))
            .frame(width: size, height: size)
            .background(Circle().fill(Theme.brass))
            .overlay(Circle().strokeBorder(Color.black.opacity(0.35), lineWidth: 1))
            .accessibilityHidden(true)
    }
}

struct ChamberPod: View {
    let palette: LevelPalette
    let team: Team?
    var jammed = false
    var size: CGFloat = 62

    var body: some View {
        ZStack {
            if let t = team {
                TesseraSwatch(palette: palette, family: t.family, tile: size / 5)
                    .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
                RoundedRectangle(cornerRadius: 14, style: .continuous)
                    .strokeBorder(jammed ? Theme.danger : Color.black.opacity(0.4), lineWidth: jammed ? 3 : 1)
                Text("\(t.remaining)")
                    .font(Theme.number(size * 0.34))
                    .monospacedDigit()
                    .minimumScaleFactor(0.5)
                    .foregroundStyle(FamilyStyle.ink(palette, t.family))
                    .shadow(color: FamilyStyle.inkShadow(palette, t.family), radius: 1.5, y: 1)
            } else {
                RoundedRectangle(cornerRadius: 14, style: .continuous)
                    .fill(Theme.loamRaised)
                RoundedRectangle(cornerRadius: 14, style: .continuous)
                    .strokeBorder(Theme.panelEdge, style: StrokeStyle(lineWidth: 1.5, dash: [5, 4]))
            }
        }
        .frame(width: size, height: size)
    }
}

/// Identifies which tunnel's full queue is shown in a sheet.
struct TunnelQueueID: Identifiable {
    let id: Int
}

/// Right-hand (or bottom) control panel.
struct ControlPanel: View {
    @ObservedObject var controller: GameController
    let compact: Bool
    var onHome: () -> Void
    var onHowTo: () -> Void
    @State private var confirmAdd = false
    @State private var confirmRestart = false
    @State private var chamberAction: Int? = nil
    @State private var queueSheet: TunnelQueueID? = nil
    @State private var showChamberHelp = false
    @State private var showGround = false

    var body: some View {
        VStack(alignment: .leading, spacing: compact ? 10 : 14) {
            header
            eventLine
            chambersRow
            tunnelsRow
            messageArea
            toolbar
            speedRow
            if !compact { nestMiniature }
        }
        .padding(compact ? 12 : 16)
        .background(
            RoundedRectangle(cornerRadius: 20, style: .continuous)
                .fill(Theme.panel)
                .overlay(RoundedRectangle(cornerRadius: 20, style: .continuous).strokeBorder(Theme.panelEdge, lineWidth: 1))
        )
        .animation(.easeOut(duration: 0.25), value: controller.revision)
        .alert("Add a slot?", isPresented: $confirmAdd) {
            Button("Add slot") { controller.addChamber() }
            Button("Cancel", role: .cancel) {}
        } message: {
            Text("One more team can work or wait at a time. It counts as an assist and can be undone.")
        }
        .alert("Restart this mosaic?", isPresented: $confirmRestart) {
            Button("Restart", role: .destructive) { controller.restart() }
            Button("Cancel", role: .cancel) {}
        } message: {
            Text("Every tile goes back and all tunnels refill.")
        }
        .alert("Slots", isPresented: $showChamberHelp) {
            Button("OK", role: .cancel) {}
        } message: {
            Text("Every team you send takes a slot. A working team frees its slot once its ants have picked up all its tiles (the number counts down). You can only send a team while a slot is open. Any mix of colours is fine — every slot can hold the same colour.\n\nTo make a team wait, just send it: if it can't reach all its tiles yet, it keeps its slot and waits, then resumes by itself when its colour is uncovered. One tap on a waiting team returns it to the front of its tunnel and opens its slot (Undo puts it back).")
        }
        .confirmationDialog(chamberDialogTitle, isPresented: Binding(get: { chamberAction != nil }, set: { if !$0 { chamberAction = nil } }),
                            titleVisibility: .visible) {
            if let i = chamberAction, i < controller.chambers.count {
                if controller.chambers[i].held {
                    Button("Send it now") {
                        controller.release(i)
                        chamberAction = nil
                    }
                }
                if controller.assistsAllowed {
                    Button("Return it to tunnel \(controller.chambers[i].tunnel + 1)") {
                        controller.recall(i)
                        chamberAction = nil
                    }
                }
            }
            Button("Leave it", role: .cancel) { chamberAction = nil }
        } message: {
            Text(chamberDialogMessage)
        }
        .sheet(isPresented: $showGround) {
            GroundColorSheet(color: controller.groundColor) { controller.setGround($0) }
                .presentationDetents([.medium])
        }
        .sheet(item: $queueSheet) { item in
            TunnelQueueSheet(palette: controller.palette, tunnel: item.id, queue: controller.fullQueue(item.id))
        }
    }

    private var chamberDialogTitle: String {
        guard let i = chamberAction, i < controller.chambers.count else { return "Chamber" }
        let t = controller.chambers[i]
        return t.held ? "Held team · \(t.remaining) tiles" : "Waiting team · needs \(t.remaining) more"
    }

    private var chamberDialogMessage: String {
        guard let i = chamberAction, i < controller.chambers.count else { return "" }
        if controller.chambers[i].held {
            return "This team was parked with Hold in an earlier version and won't work until you send it. Returning it puts it back at the front of its tunnel and opens its slot."
        }
        if !controller.assistsAllowed {
            return "This team resumes by itself whenever its colour is uncovered. Returning waiting teams is off in this game (No assists)."
        }
        return "This team resumes by itself whenever its colour is uncovered. Returning it opens its slot; it keeps the number of tiles it still needs."
    }

    // MARK: header

    private var header: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack(alignment: .firstTextBaseline) {
                VStack(alignment: .leading, spacing: 0) {
                    Text(controller.level.title)
                        .font(Theme.title(compact ? 20 : 24))
                        .foregroundStyle(Theme.sand)
                        .lineLimit(1)
                        .minimumScaleFactor(0.7)
                    Text(subtitleText)
                        .font(Theme.label(13))
                        .foregroundStyle(Theme.sandDim)
                }
                Spacer()
                Menu {
                    Button { confirmRestart = true } label: { Label("Restart mosaic", systemImage: "arrow.counterclockwise") }
                    Button { onHowTo() } label: { Label("How to play", systemImage: "questionmark.circle") }
                    Toggle(isOn: Binding(get: { controller.detailedAnts }, set: { controller.setDetailedAnts($0) })) {
                        Label("Detailed legs", systemImage: "ant")
                    }
                    Toggle(isOn: Binding(get: { controller.soundOn }, set: { controller.setSoundOn($0) })) {
                        Label("Sound effects", systemImage: "speaker.wave.2")
                    }
                    Picker(selection: Binding(get: { controller.pathStyle }, set: { controller.setPathStyle($0) })) {
                        ForEach(PathStyle.allCases) { style in
                            Label(style.title, systemImage: style.systemImage).tag(style)
                        }
                    } label: {
                        Label("Ant paths: \(controller.pathStyle.title)", systemImage: "point.topleft.down.curvedto.point.bottomright.up")
                    }
                    .pickerStyle(.menu)
                    Button { showGround = true } label: { Label("Ground colour…", systemImage: "paintpalette") }
                    Divider()
                    Button { onHome() } label: { Label("Back to the nest", systemImage: "house") }
                } label: {
                    Image(systemName: "ellipsis.circle.fill")
                        .font(.system(size: 30))
                        .foregroundStyle(Theme.sand, Theme.panelEdge)
                        .frame(width: 48, height: 48)
                }
                .accessibilityLabel("Menu")
            }
            if !controller.modifiers.isEmpty {
                modifierLine
            }
            ProgressView(value: controller.progress)
                .tint(Theme.brass)
            Text("\(controller.deliveredCount) of \(controller.board.tileCount) tiles home · \(controller.board.tileCount - controller.claimedCount) unclaimed")
                .font(Theme.label(12))
                .foregroundStyle(Theme.sandDim)
                .monospacedDigit()
        }
    }

    /// The harder options in play, as small icons, with the score multiplier.
    private var modifierLine: some View {
        HStack(spacing: 6) {
            ForEach(ChallengeModifier.sorted(controller.modifiers)) { m in
                Image(systemName: m.systemImage)
                    .font(.system(size: 12, weight: .semibold))
                    .foregroundStyle(Theme.danger)
                    .frame(width: 22, height: 22)
                    .background(Circle().fill(Theme.loamRaised))
                    .accessibilityLabel(m.title)
            }
            Text("Harder options · score ×" + String(format: "%.2f", controller.scoreFactor))
                .font(Theme.label(11, weight: .bold))
                .foregroundStyle(Theme.sandDim)
                .lineLimit(1)
                .minimumScaleFactor(0.7)
        }
        .accessibilityElement(children: .combine)
    }

    private var subtitleText: String {
        var s = "\(controller.difficulty.title) · \(controller.moveCount) moves"
        if controller.assistCount > 0 { s += " · \(controller.assistCount) assists" }
        return s
    }

    @ViewBuilder
    private var eventLine: some View {
        if let text = controller.eventText {
            HStack(alignment: .top, spacing: 8) {
                RoundedRectangle(cornerRadius: 2).fill(Theme.brass).frame(width: 4)
                Text(text)
                    .font(Theme.label(13))
                    .foregroundStyle(Theme.sand)
                    .fixedSize(horizontal: false, vertical: true)
                Spacer(minLength: 0)
            }
            .padding(.vertical, 2)
            .transition(.opacity)
        }
    }

    // MARK: slots

    private var chambersRow: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack(spacing: 6) {
                Text("SLOTS")
                    .font(Theme.label(12, weight: .bold))
                    .tracking(1.5)
                    .foregroundStyle(controller.isBlocked ? Theme.danger : Theme.sandDim)
                Text(slotCountText)
                    .font(Theme.label(12, weight: .bold))
                    .foregroundStyle(controller.hasOpenSlot ? Theme.ok : Theme.brass)
                    .monospacedDigit()
                Spacer()
                Button { showChamberHelp = true } label: {
                    Image(systemName: "questionmark.circle")
                        .font(.system(size: 18))
                        .foregroundStyle(Theme.sandDim)
                        .frame(width: 44, height: 32)
                }
                .buttonStyle(.plain)
                .accessibilityLabel("How slots work")
            }
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(alignment: .top, spacing: 8) {
                    let pod: CGFloat = compact ? 54 : 62
                    ForEach(controller.slots) { item in
                        slotView(item, pod: pod)
                    }
                    if let j = controller.jammedTeam {
                        VStack(spacing: 3) {
                            ChamberPod(palette: controller.palette, team: j, jammed: true, size: pod)
                            Text("Blocked")
                                .font(Theme.label(11, weight: .bold))
                                .foregroundStyle(Theme.danger)
                        }
                    }
                    if controller.assistsAllowed {
                        addSlotButton(pod: pod)
                    }
                }
                .padding(.vertical, 6)
                .padding(.trailing, 6)
            }
            if !controller.hasOpenSlot && !controller.isBlocked {
                Text(slotsFullText)
                    .font(Theme.label(12))
                    .foregroundStyle(Theme.brass)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
    }

    private func addSlotButton(pod: CGFloat) -> some View {
        VStack(spacing: 3) {
            Button { confirmAdd = true } label: {
                VStack(spacing: 2) {
                    Image(systemName: "plus")
                        .font(.system(size: 18, weight: .bold))
                    Text("Slot")
                        .font(Theme.label(11, weight: .bold))
                }
                .foregroundStyle(Theme.brass)
                .frame(width: pod, height: pod)
                .background(RoundedRectangle(cornerRadius: 14, style: .continuous)
                    .strokeBorder(Theme.brass.opacity(0.7), style: StrokeStyle(lineWidth: 1.5, dash: [4, 3])))
            }
            .buttonStyle(.plain)
            .accessibilityLabel("Add a slot")
            Text("add · assist")
                .font(Theme.label(10))
                .foregroundStyle(Theme.sandDim.opacity(0.8))
        }
    }

    private var slotCountText: String {
        let open = max(0, controller.capacity - controller.occupiedSlots)
        return "\(open) of \(controller.capacity) open"
    }

    private var slotsFullText: String {
        if let s = controller.nextFreeSeconds, s > 0, s < 1e6 {
            return "All slots busy — next one opens in about \(Int(s.rounded(.up))) s. Teams can't be sent until then."
        }
        return "All slots busy — a slot opens when a working team has picked up all its tiles."
    }

    @ViewBuilder
    private func slotView(_ item: SlotItem, pod: CGFloat) -> some View {
        switch item.content {
        case .open:
            VStack(spacing: 3) {
                ChamberPod(palette: controller.palette, team: nil, size: pod)
                    .overlay(Text("Open").font(Theme.label(12, weight: .bold)).foregroundStyle(Theme.ok.opacity(0.9)))
                Text(" ").font(Theme.label(11))
            }
            .accessibilityElement(children: .ignore)
            .accessibilityLabel("Open slot")
        case .working(let uid, let family, let left):
            VStack(spacing: 3) {
                ChamberPod(palette: controller.palette, team: Team(uid: uid, family: family, quota: left, remaining: left), size: pod)
                Text("Working")
                    .font(Theme.label(11, weight: .bold))
                    .foregroundStyle(Theme.sand)
            }
            .accessibilityElement(children: .ignore)
            .accessibilityLabel("Slot working: \(controller.palette.name(family)) team, \(left) tiles still to pick up")
        case .waiting(let chamber, let uid, let family, let left):
            VStack(spacing: 3) {
                // one tap returns the team to the front of its tunnel and opens the slot (undo reverses it)
                Button { controller.recall(chamber) } label: {
                    ChamberPod(palette: controller.palette, team: Team(uid: uid, family: family, quota: left, remaining: left), size: pod)
                        .overlay(alignment: .topTrailing) {
                            if controller.assistsAllowed { ReturnBadge(size: 18).offset(x: 5, y: -5) }
                        }
                }
                .buttonStyle(.plain)
                Text("Waiting")
                    .font(Theme.label(11, weight: .bold))
                    .foregroundStyle(Theme.brass)
                    .lineLimit(1)
                    .minimumScaleFactor(0.7)
                    .frame(width: pod)
            }
            .accessibilityElement(children: .ignore)
            .accessibilityLabel("Slot waiting: \(controller.palette.name(family)) team needs \(left) more tiles." + (controller.assistsAllowed ? " Double-tap to return it to its tunnel." : ""))
            .accessibilityAddTraits(.isButton)
            .accessibilityAction { controller.recall(chamber) }
        case .held(let chamber, let uid, let family, let need):
            VStack(spacing: 3) {
                Button { chamberAction = chamber } label: {
                    ChamberPod(palette: controller.palette, team: Team(uid: uid, family: family, quota: need, remaining: need), size: pod)
                        .opacity(0.8)
                        .overlay(
                            RoundedRectangle(cornerRadius: 14, style: .continuous)
                                .strokeBorder(controller.hintChamber == chamber ? Theme.brass : Color.clear, lineWidth: 4)
                        )
                }
                .buttonStyle(.plain)
                Text("Held")
                    .font(Theme.label(11, weight: .bold))
                    .foregroundStyle(Theme.sandDim)
            }
            .accessibilityElement(children: .ignore)
            .accessibilityLabel("Slot held: \(controller.palette.name(family)) team of \(need). Double-tap to send or return it.")
            .accessibilityAddTraits(.isButton)
            .accessibilityAction { chamberAction = chamber }
        }
    }

    // MARK: tunnels

    private var tunnelsRow: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack(alignment: .firstTextBaseline) {
                Text("TUNNELS")
                    .font(Theme.label(12, weight: .bold))
                    .tracking(1.5)
                    .foregroundStyle(Theme.sandDim)
                Text("Tap a team to send it into an open slot — each tap sends the next team in line. A team that can't reach all its tiles waits in its slot by itself.")
                    .font(Theme.label(11))
                    .foregroundStyle(Theme.sandDim.opacity(0.85))
                    .fixedSize(horizontal: false, vertical: true)
            }
            HStack(alignment: .top, spacing: 10) {
                ForEach(0..<controller.tunnelCount, id: \.self) { q in
                    tunnelColumn(q)
                }
            }
        }
    }

    private func tunnelColumn(_ q: Int) -> some View {
        let cardHeight: CGFloat = compact ? 84 : 104
        let pal = controller.palette
        let next = controller.upcoming(q, count: 3)
        let behind = max(0, controller.remaining(q) - 1 - next.count)
        return VStack(spacing: 6) {
            Button { if !controller.queueHidden { queueSheet = TunnelQueueID(id: q) } } label: {
                Text("TUNNEL \(q + 1) · \(controller.remaining(q)) left")
                    .font(Theme.label(11, weight: .bold))
                    .tracking(1.0)
                    .foregroundStyle(Theme.sandDim)
                    .lineLimit(1)
                    .minimumScaleFactor(0.7)
                    .frame(maxWidth: .infinity, minHeight: 24)
            }
            .buttonStyle(.plain)
            .accessibilityLabel("Tunnel \(q + 1), \(controller.remaining(q)) teams left. Show the whole queue.")
            if let fr = controller.front(q) {
                TeamCard(palette: pal, family: fr.family, need: fr.need, height: cardHeight,
                         highlighted: controller.hintTunnel == q || controller.scout?.tunnel == q,
                         dimmed: !controller.canSend(q))
                    .id(fr.uid)
                    .transition(.asymmetric(insertion: .move(edge: .bottom).combined(with: .opacity),
                                            removal: .scale(scale: 0.6).combined(with: .opacity)))
                    .contentShape(RoundedRectangle(cornerRadius: 16))
                    .onTapGesture { controller.dispatch(q) }
                    .onLongPressGesture(minimumDuration: 0.35) { controller.beginScout(q) }
                    .overlay(alignment: .bottom) { SameColourTag(shown: controller.colourRefusal(q) != nil) }
                    .accessibilityElement(children: .ignore)
                    .accessibilityLabel("Tunnel \(q + 1): \(pal.name(fr.family)) team, \(fr.need) tiles" + (fr.isReturned ? ", returned" : ""))
                    .accessibilityHint(controller.scoutAllowed ? "Double-tap to send the team. Use the Scout action to preview its tiles." : "Double-tap to send the team.")
                    .accessibilityAddTraits(.isButton)
                    .accessibilityAction(named: "Scout") { controller.beginScout(q) }
                if controller.difficulty.showsFitBadges, q < controller.fitBadges.count, let fits = controller.fitBadges[q] {
                    Text(fits ? "Can finish now" : "Would wait")
                        .font(Theme.label(11, weight: .bold))
                        .foregroundStyle(fits ? Theme.ok : Theme.brass)
                        .frame(height: 14)
                } else if fr.isReturned {
                    Text("Returned team")
                        .font(Theme.label(11, weight: .bold))
                        .foregroundStyle(Theme.sandDim)
                        .frame(height: 14)
                }
                queuePreview(q, next: next, behind: behind)
            } else {
                RoundedRectangle(cornerRadius: 16, style: .continuous)
                    .strokeBorder(Theme.panelEdge, style: StrokeStyle(lineWidth: 1.5, dash: [6, 4]))
                    .frame(height: cardHeight)
                    .overlay(Text("Empty").font(Theme.label(14)).foregroundStyle(Theme.sandDim))
            }
        }
        .frame(maxWidth: .infinity, alignment: .top)
    }

    /// The next teams under a tunnel's front card (or "?" chips with Hidden queue).
    @ViewBuilder
    private func queuePreview(_ q: Int, next: [TeamSpec], behind: Int) -> some View {
        if controller.queueHidden {
            VStack(spacing: 4) {
                ForEach(0..<min(3, max(0, controller.remaining(q) - 1)), id: \.self) { k in
                    Capsule()
                        .fill(Theme.loamRaised)
                        .frame(height: 26)
                        .overlay(Image(systemName: "questionmark").font(.system(size: 12, weight: .bold)).foregroundStyle(Theme.sandDim))
                        .overlay(Capsule().strokeBorder(Theme.panelEdge, lineWidth: 1))
                        .opacity(1.0 - 0.18 * Double(k))
                }
            }
            .accessibilityElement(children: .ignore)
            .accessibilityLabel("The rest of this tunnel is hidden")
        } else {
            VStack(spacing: 4) {
                ForEach(Array(next.enumerated()), id: \.offset) { k, spec in
                    MiniTeamChip(palette: controller.palette, spec: spec)
                        .opacity(1.0 - 0.18 * Double(k))
                }
                if behind > 0 {
                    Button { queueSheet = TunnelQueueID(id: q) } label: {
                        Text("+\(behind) more")
                            .font(Theme.label(12, weight: .bold))
                            .foregroundStyle(Theme.brass)
                            .frame(maxWidth: .infinity, minHeight: 28)
                    }
                    .buttonStyle(.plain)
                }
            }
        }
    }

    // MARK: messages (scout / hint / finishing)

    @ViewBuilder
    private var messageArea: some View {
        if let s = controller.scout {
            MessageCard(icon: "eye.fill", tint: Theme.brass) {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Scouting a team of \(s.quota)")
                        .font(Theme.label(15, weight: .bold))
                    Text(scoutText(s))
                        .font(Theme.label(13))
                        .foregroundStyle(Theme.sandDim)
                }
            } actions: {
                Button("Send") { controller.dispatch(s.tunnel) }
                    .buttonStyle(PillButtonStyle(prominent: true))
                Button("Close") { controller.endScout() }
                    .buttonStyle(PillButtonStyle(prominent: false))
            }
        } else if let h = controller.hint {
            MessageCard(icon: "lightbulb.fill", tint: Theme.brass) {
                Text(hintText(h))
                    .font(Theme.label(14))
                    .fixedSize(horizontal: false, vertical: true)
            } actions: {
                if case .undo(let n) = h {
                    Button("Undo \(n)") { controller.undo(times: n) }
                        .buttonStyle(PillButtonStyle(prominent: true))
                }
                if case .move = h {
                    Button("Do it") { controller.playHint() }
                        .buttonStyle(PillButtonStyle(prominent: true))
                }
                Button("OK") { controller.clearHint() }
                    .buttonStyle(PillButtonStyle(prominent: false))
            }
        } else if controller.isLogicallyWon && !controller.visuallyComplete {
            MessageCard(icon: "sparkles", tint: Theme.ok) {
                Text("Every tile is claimed — the colony is carrying the last ones home. Slide the speed up if you'd like them to hurry.")
                    .font(Theme.label(14))
                    .fixedSize(horizontal: false, vertical: true)
            } actions: { EmptyView() }
        }
    }

    private func scoutText(_ s: ScoutReport) -> String {
        if s.fits { return "Every one of its \(s.quota) tiles is reachable now — its slot frees as soon as they're picked up." }
        return "Reaches \(s.ownTiles.count) now; it would keep its slot and wait for the other \(s.quota - s.ownTiles.count) until they're uncovered."
    }

    private func hintText(_ h: HintResult) -> String {
        switch h {
        case .move(let code, let onPlan):
            let what: String
            if code >= Game.releaseBase {
                what = "Send the held team glowing in the slots row."
            } else {
                what = "Send the team in tunnel \(code + 1) (glowing)."
            }
            return onPlan ? what : "Tricky spot. " + what + " It makes the most progress, but no sure win was found."
        case .undo(let n):
            return "No winning line from here. Undo \(n) move\(n == 1 ? "" : "s") to get back on track — or add a slot / return a waiting team."
        case .finished:
            return "Every team has been sent. Sit back and watch."
        }
    }

    // MARK: toolbar + speed

    private var toolbar: some View {
        HStack(spacing: 10) {
            ToolButton(icon: "arrow.uturn.backward", label: undoLabel, enabled: controller.canUndo) { controller.undo() }
            if controller.hintsAllowed {
                ToolButton(icon: controller.hintBusy ? "hourglass" : "lightbulb", label: "Hint",
                           enabled: !controller.hintBusy && !controller.isLogicallyWon) { controller.requestHint() }
            }
        }
    }

    private var undoLabel: String {
        if let left = controller.undosLeft { return "Undo (\(left) left)" }
        return "Undo"
    }

    private var speedRow: some View {
        let lo = log(GameController.speedRange.lowerBound)
        let hi = log(GameController.speedRange.upperBound)
        let binding = Binding<Double>(
            get: { (log(controller.speed) - lo) / (hi - lo) },
            set: { controller.setSpeed(exp(lo + $0 * (hi - lo))) }
        )
        return VStack(alignment: .leading, spacing: 4) {
            HStack {
                Text("ANT SPEED")
                    .font(Theme.label(12, weight: .bold))
                    .tracking(1.5)
                    .foregroundStyle(Theme.sandDim)
                Spacer()
                Text(speedLabel(controller.speed))
                    .font(Theme.label(13, weight: .bold))
                    .monospacedDigit()
                    .foregroundStyle(Theme.sand)
                Button("1×") {
                    controller.setSpeed(1)
                    controller.commitSpeed()
                }
                .font(Theme.label(12, weight: .bold))
                .foregroundStyle(Theme.brass)
                .frame(minWidth: 44, minHeight: 32)
            }
            HStack(spacing: 10) {
                Image(systemName: "tortoise.fill")
                    .foregroundStyle(Theme.sandDim)
                Slider(value: binding, in: 0...1, onEditingChanged: { editing in
                    if !editing { controller.commitSpeed() }
                })
                .tint(Theme.brass)
                .accessibilityLabel("Ant speed")
                .accessibilityValue(speedLabel(controller.speed))
                Image(systemName: "hare.fill")
                    .foregroundStyle(Theme.sandDim)
            }
            .frame(minHeight: 44)
        }
    }

    private func speedLabel(_ s: Double) -> String {
        if s < 0.995 { return String(format: "%.2f×", s) }
        return String(format: "%.1f×", s)
    }

    // MARK: miniature

    private var nestMiniature: some View {
        HStack(alignment: .center, spacing: 12) {
            if let img = controller.miniImage {
                Image(decorative: img, scale: 1)
                    .resizable()
                    .interpolation(.none)
                    .aspectRatio(contentMode: .fit)
                    .frame(maxHeight: 140)
                    .clipShape(RoundedRectangle(cornerRadius: 6))
                    .overlay(RoundedRectangle(cornerRadius: 6).strokeBorder(Theme.brassDeep, lineWidth: 2))
            }
            VStack(alignment: .leading, spacing: 4) {
                Text("NEST GALLERY")
                    .font(Theme.label(12, weight: .bold))
                    .tracking(1.5)
                    .foregroundStyle(Theme.brass)
                Text("Every tile carried home is re-laid down here, in the same place.")
                    .font(Theme.label(13))
                    .foregroundStyle(Theme.sandDim)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
    }
}

/// Pick the colour of the ground behind the mosaic: presets or any colour.
struct GroundColorSheet: View {
    let color: UInt32
    let onPick: (UInt32) -> Void
    @State private var custom: Color = .brown
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            VStack(alignment: .leading, spacing: 16) {
                Text("The ground shows around the mosaic and wherever tiles have been carried away.")
                    .font(Theme.label(14))
                    .foregroundStyle(Theme.sandDim)
                    .fixedSize(horizontal: false, vertical: true)
                LazyVGrid(columns: [GridItem(.adaptive(minimum: 76), spacing: 12)], spacing: 12) {
                    ForEach(0..<GroundPresets.all.count, id: \.self) { i in
                        let preset = GroundPresets.all[i]
                        Button {
                            onPick(preset.1)
                        } label: {
                            VStack(spacing: 4) {
                                RoundedRectangle(cornerRadius: 12, style: .continuous)
                                    .fill(Color(hex: preset.1))
                                    .frame(height: 48)
                                    .overlay(RoundedRectangle(cornerRadius: 12, style: .continuous)
                                        .strokeBorder(preset.1 == color ? Theme.brass : Theme.panelEdge, lineWidth: preset.1 == color ? 3 : 1))
                                Text(preset.0)
                                    .font(Theme.label(12, weight: .bold))
                                    .foregroundStyle(Theme.sand)
                            }
                        }
                        .buttonStyle(.plain)
                    }
                }
                ColorPicker("Any colour", selection: Binding(get: { custom }, set: { newValue in
                    custom = newValue
                    onPick(newValue.rgbHex())
                }), supportsOpacity: false)
                    .font(Theme.label(15, weight: .semibold))
                    .foregroundStyle(Theme.sand)
                Spacer()
            }
            .padding(20)
            .background(Theme.loam.ignoresSafeArea())
            .navigationTitle("Ground colour")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button("Done") { dismiss() }
                }
            }
            .onAppear { custom = Color(hex: color) }
        }
        .preferredColorScheme(.dark)
    }
}

/// The whole queue of one tunnel, front first.
struct TunnelQueueSheet: View {
    let palette: LevelPalette
    let tunnel: Int
    let queue: [TeamSpec]
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 12) {
                    Text("Teams leave from the top. Tap a team on the game screen to send the front one; the next one then moves up.")
                        .font(Theme.label(14))
                        .foregroundStyle(Theme.sandDim)
                        .fixedSize(horizontal: false, vertical: true)
                    LazyVGrid(columns: [GridItem(.adaptive(minimum: 88), spacing: 10)], spacing: 10) {
                        ForEach(Array(queue.enumerated()), id: \.offset) { k, spec in
                            VStack(spacing: 4) {
                                TeamCard(palette: palette, family: spec.family, need: spec.quota, height: 64,
                                         highlighted: k == 0)
                                Text(k == 0 ? "Front" : "#\(k + 1)")
                                    .font(Theme.label(11, weight: .bold))
                                    .foregroundStyle(k == 0 ? Theme.brass : Theme.sandDim)
                            }
                        }
                    }
                }
                .padding(20)
            }
            .background(Theme.loam.ignoresSafeArea())
            .navigationTitle("Tunnel \(tunnel + 1) · \(queue.count) teams")
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

struct ToolButton: View {
    let icon: String
    let label: String
    let enabled: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: 8) {
                Image(systemName: icon)
                    .font(.system(size: 19, weight: .semibold))
                Text(label)
                    .font(Theme.label(15, weight: .semibold))
                    .lineLimit(1)
            }
            .frame(maxWidth: .infinity, minHeight: 50)
            .foregroundStyle(enabled ? Theme.sand : Theme.sandDim.opacity(0.5))
            .background(RoundedRectangle(cornerRadius: 14, style: .continuous).fill(Theme.loamRaised))
            .overlay(RoundedRectangle(cornerRadius: 14, style: .continuous).strokeBorder(Theme.panelEdge, lineWidth: 1))
        }
        .buttonStyle(.plain)
        .disabled(!enabled)
    }
}

struct PillButtonStyle: ButtonStyle {
    let prominent: Bool
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(Theme.label(14, weight: .bold))
            .padding(.horizontal, 16)
            .frame(minHeight: 44)
            .foregroundStyle(prominent ? Color(hex: 0x2A1C12) : Theme.sand)
            .background(Capsule().fill(prominent ? Theme.brass : Theme.loamRaised))
            .overlay(Capsule().strokeBorder(Theme.panelEdge, lineWidth: prominent ? 0 : 1))
            .opacity(configuration.isPressed ? 0.75 : 1)
    }
}

struct MessageCard<Content: View, Actions: View>: View {
    let icon: String
    let tint: Color
    @ViewBuilder var content: () -> Content
    @ViewBuilder var actions: () -> Actions

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(alignment: .top, spacing: 10) {
                Image(systemName: icon)
                    .font(.system(size: 18, weight: .bold))
                    .foregroundStyle(tint)
                content()
                    .foregroundStyle(Theme.sand)
                Spacer(minLength: 0)
            }
            HStack(spacing: 8) {
                Spacer()
                actions()
            }
        }
        .padding(12)
        .background(RoundedRectangle(cornerRadius: 14, style: .continuous).fill(Theme.loamRaised))
        .overlay(RoundedRectangle(cornerRadius: 14, style: .continuous).strokeBorder(tint.opacity(0.6), lineWidth: 1))
    }
}
