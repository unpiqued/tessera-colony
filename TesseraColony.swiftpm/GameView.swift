import SwiftUI

/// Game screen. Wide layouts (iPad landscape, large windows) put the controls beside the board;
/// tall layouts (iPad portrait, iPhone) put them underneath. Touch targets stay >= 44 pt.
struct GameView: View {
    @ObservedObject var controller: GameController
    @EnvironmentObject var app: AppModel
    @State private var showHowTo = false

    var body: some View {
        ZStack {
            GeometryReader { geo in
                let wide = geo.size.width > geo.size.height * 1.05
                let layout = computeLayout(size: geo.size, wide: wide)
                ZStack {
                    GroundPresets.backdrop(controller.groundColor).ignoresSafeArea()
                    if wide {
                        HStack(alignment: .center, spacing: 16) {
                            boardStack(cell: layout.cell)
                                .frame(maxWidth: .infinity, maxHeight: .infinity)
                            ScrollView(.vertical, showsIndicators: false) {
                                panel(compact: false)
                            }
                            .frame(width: layout.panelWidth)
                        }
                        .padding(16)
                    } else {
                        ScrollView(.vertical, showsIndicators: false) {
                            VStack(spacing: 10) {
                                boardStack(cell: layout.cell)
                                    .frame(maxWidth: .infinity)
                                panel(compact: true)
                            }
                            .padding(.horizontal, 12)
                            .padding(.vertical, 8)
                        }
                        .scrollDisabled(false)
                    }
                }
            }
            // The board and panel keep their size when the keyboard comes up (typing a high-score
            // name used to shrink the screen, flip the layout and redraw the whole mosaic under the
            // finish card, which could stall the typing).
            .ignoresSafeArea(.keyboard, edges: .bottom)
            overlays
            // Always-visible way out (the game is saved; Resume picks it up again)
            ExitButton { app.goHome() }
                .padding(.leading, 8)
                .padding(.top, 6)
                .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
                .ignoresSafeArea(.keyboard, edges: .bottom)
        }
        .task(id: controller.level.id) {
            while !Task.isCancelled {
                controller.tick()
                try? await Task.sleep(nanoseconds: 100_000_000)
            }
        }
        .sensoryFeedback(.impact(weight: .light), trigger: controller.hapticTick)
        .sensoryFeedback(.warning, trigger: controller.refusedTick)
        .sheet(isPresented: $showHowTo) { HowToPlayView() }
        .preferredColorScheme(.dark)
    }

    private struct Layout {
        let cell: CGFloat
        let panelWidth: CGFloat
    }

    private func computeLayout(size: CGSize, wide: Bool) -> Layout {
        let b = controller.board
        let cols = CGFloat(b.cols)
        let rows = CGFloat(b.rows)
        if wide {
            let panelWidth = min(470, max(360, size.width * 0.38))
            let availW = size.width - panelWidth - 48
            let availH = size.height - 32
            let cell = max(3, min(availW / cols, availH / rows))
            return Layout(cell: (cell * 2).rounded(.down) / 2, panelWidth: panelWidth)
        } else {
            let panelHeight: CGFloat = size.width > 600 ? 480 : 440
            let availW = size.width - 24
            let availH = size.height - panelHeight - 30
            let cell = max(2.5, min(availW / cols, availH / rows))
            return Layout(cell: (cell * 2).rounded(.down) / 2, panelWidth: size.width)
        }
    }

    private func boardStack(cell: CGFloat) -> some View {
        ZStack(alignment: .top) {
            BoardView(controller: controller, cell: cell)
            if let step = controller.coach {
                CoachBanner(step: step) { controller.dismissCoach() }
                    .padding(12)
                    .padding(.leading, 44)      // clear of the exit button
                    .transition(.move(edge: .top).combined(with: .opacity))
            }
        }
        .animation(.easeOut(duration: 0.25), value: controller.coach)
    }

    private func panel(compact: Bool) -> some View {
        ControlPanel(controller: controller, compact: compact,
                     onHome: { app.goHome() },
                     onHowTo: { showHowTo = true })
    }

    @ViewBuilder
    private var overlays: some View {
        if controller.isBlocked {
            Color.black.opacity(0.45).ignoresSafeArea()
            JamCard(controller: controller)
                .padding(24)
                .transition(.scale.combined(with: .opacity))
        } else if controller.visuallyComplete {
            Color.black.opacity(0.5).ignoresSafeArea()
            // centred when it fits, scrollable when it doesn't (small screens, keyboard up); while a
            // name is being typed the name box is scrolled into view above the keyboard
            GeometryReader { g in
                ScrollViewReader { proxy in
                    ScrollView {
                        WinCard(controller: controller,
                                onGallery: { app.goHome() },
                                onNext: nextLevelAction,
                                onEditingName: { editing in
                                    guard editing else { return }
                                    Task { @MainActor in
                                        // wait for the keyboard to finish sliding up, then bring the name box into view
                                        try? await Task.sleep(nanoseconds: 350_000_000)
                                        withAnimation(.easeOut(duration: 0.25)) {
                                            proxy.scrollTo(WinCard.nameFieldID, anchor: .center)
                                        }
                                    }
                                },
                                harderLabel: harderStep?.label,
                                onHarder: playHarder)
                            .padding(24)
                            .frame(maxWidth: .infinity, minHeight: g.size.height)
                    }
                    .scrollBounceBehavior(.basedOnSize)
                }
            }
            .transition(.scale.combined(with: .opacity))
        }
    }

    /// The next harder way to play this mosaic (Classic, Expert, then Expert plus a harder option).
    private var harderStep: HarderStep? {
        app.harderStep(after: controller.difficulty, modifiers: controller.modifiers)
    }

    private func playHarder() {
        guard let step = harderStep else { return }
        app.play(controller.level, fresh: true, difficulty: step.difficulty, modifiers: step.modifiers)
    }

    private var nextLevelAction: (() -> Void)? {
        guard let next = app.nextLevel(after: controller.level.id) else { return nil }
        return { app.play(next, fresh: false) }
    }
}

/// The round X in the corner of the game screen: back to Home in one tap (the game is saved).
struct ExitButton: View {
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Image(systemName: "xmark")
                .font(.system(size: 17, weight: .bold))
                .foregroundStyle(Theme.sand)
                .frame(width: 44, height: 44)
                .background(Circle().fill(Theme.panel.opacity(0.92)))
                .overlay(Circle().strokeBorder(Theme.panelEdge, lineWidth: 1.5))
                .shadow(color: .black.opacity(0.45), radius: 6, y: 2)
        }
        .buttonStyle(.plain)
        .accessibilityLabel("Exit to Home")
        .accessibilityHint("Your game is saved; choose Resume to continue it.")
    }
}
