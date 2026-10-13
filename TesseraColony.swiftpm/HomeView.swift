import SwiftUI
import PhotosUI

struct HomeView: View {
    @EnvironmentObject var app: AppModel
    @State private var showHowTo = false
    @State private var showSettings = false
    @State private var pickedPhoto: PhotosPickerItem?
    @State private var starting: StartItem?
    @State private var showVersus = false
    @State private var showScores = false

    var body: some View {
        GeometryReader { geo in
            let wide = geo.size.width > 700
            ScrollViewReader { proxy in
            ScrollView {
                VStack(alignment: .leading, spacing: 24) {
                    // (grouped so the stack stays within ten direct children on any SDK)
                    Group {
                        header
                        if let report = app.crashReport {
                            CrashReportBanner(report: report) { app.dismissCrashReport() }
                        }
                        topActions
                        nextUpBanner
                    }
                    collectionBar(proxy)
                    filterBar
                    ForEach(LevelCatalog.themes, id: \.id) { theme in
                        themeSection(theme.id, title: theme.title, icon: theme.icon, packIDs: theme.packIDs)
                            .id(theme.id)
                    }
                    if !app.photoLevels.isEmpty {
                        let mine = app.photoLevels.map { $0.level }.filter { app.passesFilter($0) }
                        if !mine.isEmpty {
                            sectionTitle("YOUR MOSAICS")
                            levelGrid(mine, wide: wide)
                        }
                    }
                    if filtering && shownCount == 0 {
                        Text(emptyFilterText)
                            .font(Theme.label(15))
                            .foregroundStyle(Theme.sand)
                            .padding(16)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .background(RoundedRectangle(cornerRadius: 16).fill(Theme.panel))
                    }
                    makeNewSection(wide: wide)
                    gallery
                    HStack(spacing: 12) {
                        Button { showHowTo = true } label: {
                            Label("How to play", systemImage: "questionmark.circle")
                        }
                        .buttonStyle(PillButtonStyle(prominent: false))
                        Button { showSettings = true } label: {
                            Label("Settings & self-test", systemImage: "gearshape")
                        }
                        .buttonStyle(PillButtonStyle(prominent: false))
                    }
                }
                .padding(wide ? 36 : 20)
                .frame(maxWidth: 980)
                .frame(maxWidth: .infinity)
            }
            }
        }
        .background(Theme.loam.ignoresSafeArea())
        .sheet(isPresented: $showHowTo) { HowToPlayView() }
        .sheet(isPresented: $showSettings) { SettingsView() }
        .sheet(isPresented: $showVersus) { VersusSetupSheet() }
        .sheet(isPresented: $showScores) { HighScoresView() }
        .sheet(item: $starting) { item in
            LevelStartSheet(level: item.level)
                .presentationDetents([.large])
        }
        .onChange(of: pickedPhoto) { _, item in
            guard let item = item else { return }
            Task {
                if let data = try? await item.loadTransferable(type: Data.self) {
                    app.importPhoto(data)
                } else {
                    app.photoMessage = PhotoBuildError.unreadable.message
                }
                pickedPhoto = nil
            }
        }
        .onAppear {
            // pattern and photo mosaics need a rating before the filter can place them
            for rec in app.photoLevels { app.measureIfNeeded(rec.level) }
        }
        .preferredColorScheme(.dark)
    }

    /// Mosaics passing the filters, across every section (only ones you can play count).
    private var shownCount: Int {
        app.allLevels.filter { app.isPlayable($0) && app.passesFilter($0) }.count
    }

    /// Is a rating or status filter on?
    private var filtering: Bool {
        app.settings.ratingFilter != .all || app.settings.statusFilter != .all
    }

    private var emptyFilterText: String {
        var parts: [String] = []
        if app.settings.statusFilter != .all { parts.append("\u{201C}\(app.settings.statusFilter.title)\u{201D}") }
        if app.settings.ratingFilter != .all {
            parts.append("rated \(app.settings.ratingFilter.title) on \(app.settings.difficulty.title)")
        }
        return "No mosaic you can play is " + parts.joined(separator: " and ") + " yet. Try another filter."
    }

    // MARK: top of the screen

    /// Two big buttons: start a two-player match, see the high scores.
    private var topActions: some View {
        HStack(spacing: 14) {
            BigActionButton(icon: "person.2.fill", title: "Two players",
                            subtitle: "Race or share a board on one iPad", prominent: true) {
                showVersus = true
            }
            .accessibilityHint("Set up a two-player match")
            BigActionButton(icon: "trophy.fill", title: "High scores",
                            subtitle: "Best scores and names per mosaic", prominent: false) {
                showScores = true
            }
        }
    }

    /// Difficulty to play (and to rate by) plus which ratings to show.
    private var filterBar: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 12) {
                Text("DIFFICULTY")
                    .font(Theme.label(12, weight: .bold))
                    .tracking(1.5)
                    .foregroundStyle(Theme.brass)
                    .frame(width: 92, alignment: .leading)
                Picker("Difficulty", selection: $app.settings.difficulty) {
                    ForEach(Difficulty.allCases) { d in Text(d.title).tag(d) }
                }
                .pickerStyle(.segmented)
                .frame(maxWidth: 420)
            }
            HStack(spacing: 12) {
                Text("SHOW")
                    .font(Theme.label(12, weight: .bold))
                    .tracking(1.5)
                    .foregroundStyle(Theme.brass)
                    .frame(width: 92, alignment: .leading)
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 8) {
                        ForEach(RatingFilter.allCases) { f in
                            filterChip(f)
                        }
                    }
                    .padding(.vertical, 2)
                }
            }
            HStack(spacing: 12) {
                Text("STATUS")
                    .font(Theme.label(12, weight: .bold))
                    .tracking(1.5)
                    .foregroundStyle(Theme.brass)
                    .frame(width: 92, alignment: .leading)
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 8) {
                        ForEach(StatusFilter.allCases) { f in
                            statusChip(f)
                        }
                    }
                    .padding(.vertical, 2)
                }
            }
            Text(filterNote)
                .font(Theme.label(12))
                .foregroundStyle(Theme.sandDim)
                .fixedSize(horizontal: false, vertical: true)
        }
        .padding(14)
        .background(RoundedRectangle(cornerRadius: 18, style: .continuous).fill(Theme.panel))
        .overlay(RoundedRectangle(cornerRadius: 18, style: .continuous).strokeBorder(Theme.panelEdge, lineWidth: 1))
    }

    private var filterNote: String {
        let total = app.allLevels.count
        let d = app.settings.difficulty.title
        if !filtering {
            return "New games start on \(d); the dots on each card show how hard it is on \(d). \(total) mosaics."
        }
        return "Showing \(shownCount) of \(total) mosaics (only ones you have found)."
    }

    private func statusChip(_ f: StatusFilter) -> some View {
        let on = app.settings.statusFilter == f
        return Button { app.settings.statusFilter = f } label: {
            HStack(spacing: 6) {
                if f != .all {
                    Image(systemName: f.icon)
                        .font(.system(size: 11, weight: .bold))
                }
                Text(f.title)
                    .font(Theme.label(14, weight: .bold))
            }
            .padding(.horizontal, 14)
            .frame(minHeight: 40)
            .foregroundStyle(on ? Color(hex: 0x2A1C12) : Theme.sand)
            .background(Capsule().fill(on ? Theme.brass : Theme.loamRaised))
            .overlay(Capsule().strokeBorder(on ? Color.clear : Theme.panelEdge, lineWidth: 1))
        }
        .buttonStyle(.plain)
        .accessibilityAddTraits(on ? .isSelected : [])
    }

    // MARK: collection

    /// Found / explored / stars / mastered for everything, and one chip per theme to jump to it.
    private func collectionBar(_ proxy: ScrollViewProxy) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(alignment: .firstTextBaseline) {
                sectionTitle("YOUR COLLECTION")
                Spacer()
                Text("★ Gentle · ★★ Classic · ★★★ Expert · flame = Expert with a harder option")
                    .font(Theme.label(11))
                    .foregroundStyle(Theme.sandDim)
                    .lineLimit(1)
                    .minimumScaleFactor(0.7)
            }
            CollectionSummary(progress: app.packProgress(LevelCatalog.builtIn))
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 8) {
                    ForEach(LevelCatalog.themes, id: \.id) { theme in
                        themeChip(theme.id, title: theme.title, icon: theme.icon, packIDs: theme.packIDs, proxy: proxy)
                    }
                }
                .padding(.vertical, 2)
            }
        }
        .padding(14)
        .background(RoundedRectangle(cornerRadius: 18, style: .continuous).fill(Theme.panel))
        .overlay(RoundedRectangle(cornerRadius: 18, style: .continuous).strokeBorder(Theme.panelEdge, lineWidth: 1))
    }

    private func themeChip(_ id: String, title: String, icon: String, packIDs: [String], proxy: ScrollViewProxy) -> some View {
        let p = app.packProgress(packIDs.flatMap { LevelCatalog.pack($0) })
        return Button {
            withAnimation(.easeInOut(duration: 0.35)) { proxy.scrollTo(id, anchor: .top) }
        } label: {
            HStack(spacing: 6) {
                Image(systemName: icon)
                    .font(.system(size: 12, weight: .bold))
                Text(title)
                    .font(Theme.label(13, weight: .bold))
                Text("\(p.explored)/\(p.total)")
                    .font(Theme.label(12))
                    .opacity(0.75)
            }
            .padding(.horizontal, 12)
            .frame(minHeight: 40)
            .foregroundStyle(Theme.sand)
            .background(Capsule().fill(Theme.loamRaised))
            .overlay(Capsule().strokeBorder(p.open ? Theme.brass.opacity(0.6) : Theme.panelEdge, lineWidth: 1))
        }
        .buttonStyle(.plain)
        .accessibilityLabel("\(title): \(p.explored) of \(p.total) explored")
    }

    /// A theme (a wing of the collection) and its packs.
    @ViewBuilder
    private func themeSection(_ id: String, title: String, icon: String, packIDs: [String]) -> some View {
        let levels = packIDs.flatMap { LevelCatalog.pack($0) }
        if levels.contains(where: { shelfShows($0) }) {
            let p = app.packProgress(levels)
            VStack(alignment: .leading, spacing: 18) {
                HStack(alignment: .firstTextBaseline, spacing: 10) {
                    Image(systemName: icon)
                        .font(.system(size: 18, weight: .bold))
                        .foregroundStyle(Theme.brass)
                    Text(title)
                        .font(Theme.title(26))
                        .foregroundStyle(Theme.sand)
                        .lineLimit(1)
                        .minimumScaleFactor(0.7)
                    Spacer(minLength: 8)
                    Text("\(p.explored) of \(p.total) explored · \(p.stars) ★")
                        .font(Theme.label(13))
                        .foregroundStyle(Theme.sandDim)
                        .lineLimit(1)
                        .minimumScaleFactor(0.7)
                }
                ForEach(packIDs, id: \.self) { pid in
                    packShelf(pid, title: LevelCatalog.packTitle(pid), levels: LevelCatalog.pack(pid))
                }
            }
        }
    }

    /// With no filter every card shows (found, "?" and locked alike); with a filter, only mosaics you
    /// can play that pass it.
    private func shelfShows(_ level: LevelDefinition) -> Bool {
        filtering ? (app.isPlayable(level) && app.passesFilter(level)) : true
    }

    /// One pack: its progress, a line about it, and a shelf of cards you can scroll sideways.
    @ViewBuilder
    private func packShelf(_ id: String, title: String, levels: [LevelDefinition]) -> some View {
        let shown = levels.filter { shelfShows($0) }
        if !shown.isEmpty {
            let p = app.packProgress(levels)
            VStack(alignment: .leading, spacing: 8) {
                HStack(alignment: .firstTextBaseline, spacing: 10) {
                    sectionTitle(title)
                    if LevelCatalog.isInSeason(id) {
                        Text("IN SEASON")
                            .font(Theme.label(10, weight: .heavy))
                            .tracking(1)
                            .padding(.horizontal, 7)
                            .padding(.vertical, 3)
                            .foregroundStyle(Color(hex: 0x2A1C12))
                            .background(Capsule().fill(Theme.brass))
                            .accessibilityLabel("In season now")
                    }
                    Text(packLine(id, p))
                        .font(Theme.label(12))
                        .foregroundStyle(Theme.sandDim)
                        .lineLimit(1)
                        .minimumScaleFactor(0.8)
                    Spacer(minLength: 0)
                }
                ProgressView(value: Double(p.explored), total: Double(max(1, p.total)))
                    .tint(p.open ? Theme.brass : Theme.panelEdge)
                    .frame(maxWidth: 320)
                Text(packBlurb(id))
                    .font(Theme.label(13))
                    .foregroundStyle(Theme.sandDim)
                    .fixedSize(horizontal: false, vertical: true)
                ScrollView(.horizontal, showsIndicators: false) {
                    LazyHStack(alignment: .top, spacing: 14) {
                        ForEach(shown, id: \.id) { level in
                            CollectionCard(level: level) { starting = StartItem(level: level) }
                        }
                    }
                    .padding(.vertical, 4)
                }
            }
        }
    }

    private func packLine(_ id: String, _ p: PackProgress) -> String {
        if !p.open, let rule = LevelCatalog.packRule(id) {
            return "Opens after \(rule.label)"
        }
        var s = "\(p.found) of \(p.total) found · \(p.explored) explored · \(p.stars) of \(p.total * 3) ★"
        if p.mastered > 0 { s += " · \(p.mastered) mastered" }
        return s
    }

    private func filterChip(_ f: RatingFilter) -> some View {
        let on = app.settings.ratingFilter == f
        return Button { app.settings.ratingFilter = f } label: {
            HStack(spacing: 6) {
                if f.dotLevel > 0 {
                    Circle().fill(RatingDots.color(f.dotLevel)).frame(width: 9, height: 9)
                }
                Text(f.title)
                    .font(Theme.label(14, weight: .bold))
            }
            .padding(.horizontal, 14)
            .frame(minHeight: 40)
            .foregroundStyle(on ? Color(hex: 0x2A1C12) : Theme.sand)
            .background(Capsule().fill(on ? Theme.brass : Theme.loamRaised))
            .overlay(Capsule().strokeBorder(on ? Color.clear : Theme.panelEdge, lineWidth: 1))
        }
        .buttonStyle(.plain)
        .accessibilityAddTraits(on ? .isSelected : [])
    }

    // MARK: packs

    private func packBlurb(_ id: String) -> String {
        switch id {
        case "main":
            return unlockExplanation
        case "garden":
            return "Eight new pictures — a hot-air balloon, a lighthouse, toadstools, tulips, an evening sail, bees on a honeycomb, an owl and a desert bloom. The gentlest pack: most are Relaxed or Steady on Classic (Toadstools and the balloon are Hard). Unlocked by finishing First Dig."
        case "wild":
            return "Natural wonders — the Northern Lights, the Grand Canyon, Victoria Falls, an iceberg, a volcano, a rainforest, a coral reef and a panda's bamboo grove. Ordered from gentlest to hardest. Opens after First Dig."
        case "gallery":
            return "Famous paintings as mosaics — Monet, Vermeer, Leonardo, Munch, Van Gogh, Seurat and Klimt (all public domain). Ordered from gentlest to hardest. Opens after First Dig."
        case "worldart":
            return "Art and design from around the world — Hokusai's wave, Hiroshige's rain, a Ming vase, Kandinsky, the Aztec Sun Stone, Ravenna's starry vault, Alhambra tiles and Mondrian. Ordered from gentlest to hardest. Opens after any Gallery mosaic."
        case "ancient":
            return "Marvels of the ancient world — Lascaux, Giza, Stonehenge, Tutankhamun's mask, the first Olympics, the Great Wall, the Terracotta Army and the Colosseum. Ordered from gentlest to hardest. Opens after First Dig."
        case "voyages":
            return "Great voyages and discoveries — Polynesian wayfinders, a Viking longship, the Silk Road, Zheng He's treasure ship, Gutenberg's press, Galileo's moons, Darwin's Galápagos and the South Pole. Ordered from gentlest to hardest. Opens after any Ancient World mosaic."
        case "modern":
            return "Moments of the modern age — the first flight, Liberty, the Eiffel Tower, the Golden Gate, Everest, Sputnik, the Moon landing and the fall of the Berlin Wall. Ordered from gentlest to hardest. Opens after any Voyages mosaic."
        case "cosmos":
            return "Wonders of the sky and moments of science — an eclipse, Saturn, Halley's comet, Newton's prism, Franklin's kite, a spiral galaxy, the double helix and the periodic table. Ordered from gentlest to hardest. Opens after any Wild Wonders mosaic."
        case "epics":
            return "Iconic scenes from epics and legends — the Sirens, the Trojan Horse, the sword in the stone, Dante's celestial rose, the Monkey King, Ali Baba's cave, Beowulf's dragon and the Tale of Genji. Ordered from gentlest to hardest. Opens after First Dig."
        case "tales":
            return "Fairy tales and fables — Red Riding Hood, Jack's beanstalk, the tortoise and the hare, Rapunzel, the Snow Queen, Cinderella's midnight, the gingerbread house and the princess and the pea. Ordered from gentlest to hardest. Opens after First Dig."
        case "childrens":
            return "Children's classics — the yellow brick road, the Wind in the Willows, the Railway Children, the Secret Garden, the Mad Tea-Party, the Jungle Book, Through the Looking-Glass and Pinocchio. Ordered from gentlest to hardest. Opens after any Fairy Tales mosaic."
        case "stage":
            return "Shakespeare — the balcony, Yorick's skull, Macbeth's witches, the Tempest, the fairy wood, Cleopatra's barge, the Globe and the three caskets. Ordered from gentlest to hardest. Opens after any Epics & Legends mosaic."
        case "adventure":
            return "Adventure classics — Crusoe's footprint, Don Quixote's windmills, Huck Finn's raft, Gulliver in Lilliput, the white whale, the underground sea, the treasure map and the Nautilus. Ordered from gentlest to hardest. Opens after any Children's Classics mosaic."
        case "gothic":
            return "Gothic and mystery — the Raven, the Headless Horseman, the Hound of the Baskervilles, the bells of Notre-Dame, Castle Dracula, Frankenstein's Arctic, the Martian tripods and the Phantom's chandelier. Ordered from gentlest to hardest. Opens after any Adventure Classics mosaic."
        case "novels":
            return "Great novels — Gatsby's green light, A Christmas Carol, Wuthering Heights, the comet of 1812, Miss Havisham's room, the bishop's candlesticks, the Netherfield ball and Oliver Twist. Ordered from gentlest to hardest. Opens after any Shakespeare mosaic."
        case "naturalist":
            return "Natural-history plates as mosaics — Audubon's flamingo, Redouté's rose, Merian's butterflies, Gould's hummingbirds, Haeckel's jellyfish and radiolarians, Seba's shells and a collector's beetle drawer (all after public-domain plates). Ordered from gentlest to hardest. Opens after any Garden mosaic."
        case "crafts":
            return "Craft traditions from around the world — a Talavera plate, a Polish paper cut, Ukrainian painted eggs, Delft tiles, a hemp-leaf kimono, a tartan, a patchwork quilt and a Persian carpet. Ordered from gentlest to hardest. Opens after any World Art mosaic."
        case "geometry":
            return "Figures, fractals and illusions — the impossible triangle, the golden spiral, the Mandelbrot set, Sierpiński's triangle, the Hilbert curve, the café wall, a Celtic knot and a ten-pointed girih star. Ordered from gentlest to hardest. Opens after any Challenge mosaic."
        case "space":
            return "Views sent back by probes and telescopes — Earthrise, Pluto's heart, Jupiter's Great Red Spot, a blue sunset on Mars, the Pillars of Creation, a rover, Webb's Cosmic Cliffs and the Hubble Deep Field. Ordered from gentlest to hardest. Opens after any Sky & Science mosaic."
        case "inventions":
            return "Inventions and firsts — the penny-farthing, the light bulb, the telephone, Leonardo's flying machine, Stephenson's Rocket, the first photograph, the Jacquard loom and Babbage's Difference Engine. Ordered from gentlest to hardest. Opens after any Modern Moments mosaic."
        case "halloween":
            return "A seasonal pack, in season from late September to early November — a jack-o'-lantern, a black cat, a scarecrow, friendly ghosts, a haunted house, a pumpkin patch, a dewy spider's web and a trick-or-treat street. Playable all year. Ordered from gentlest to hardest. Opens after First Dig."
        case "winter":
            return "A seasonal pack, in season from December to February — a snowman, a cardinal, a sledding hill, mittens and cocoa, Bentley's snowflake, the skating pond, a snow globe and a frosted window. Playable all year. Ordered from gentlest to hardest. Opens after First Dig."
        case "challenge":
            return "Four hard mosaics built from interlocking layers. Sending whatever can finish now won't get you through on Classic or Expert — scout, plan ahead and use undo. Gentle is the way in. Unlocked by finishing First Dig."
        default:
            return "The hardest mosaics — a tiger, a giraffe, an autumn tree, a castle, a viaduct, a city at dusk, a chameleon and an octopus. Busy pictures put each colour in many separate places, and the tunnel orders were searched so that sending whatever can finish now fails on Classic and Expert (on six of the eight even on Gentle). Every one can be solved; hints always know the designed line. Unlocked by finishing any Challenge mosaic."
        }
    }

    private var unlockExplanation: String {
        if app.settings.unlockAll {
            return "All mosaics are unlocked (Settings)."
        }
        return "Finish a mosaic on any difficulty to unlock the next one. Sunflower & Monarch is open from the start. Want everything now? Turn on Unlock all mosaics in Settings — or make a new level below."
    }

    private func sectionTitle(_ s: String) -> some View {
        Text(s)
            .font(Theme.label(13, weight: .bold))
            .tracking(2)
            .foregroundStyle(Theme.brass)
    }

    @ViewBuilder
    private func levelGrid(_ levels: [LevelDefinition], wide: Bool) -> some View {
        if wide {
            LazyVGrid(columns: [GridItem(.flexible(), spacing: 18), GridItem(.flexible(), spacing: 18)], alignment: .leading, spacing: 18) {
                ForEach(levels, id: \.id) { level in
                    LevelCard(level: level) { starting = StartItem(level: level) }
                }
            }
        } else {
            VStack(spacing: 16) {
                ForEach(levels, id: \.id) { level in
                    LevelCard(level: level) { starting = StartItem(level: level) }
                }
            }
        }
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack(spacing: 10) {
                Image(systemName: "ant.fill")
                    .font(.system(size: 30))
                    .foregroundStyle(Theme.brass)
                Text("Tessera Colony")
                    .font(Theme.title(44))
                    .foregroundStyle(Theme.sand)
                    .lineLimit(1)
                    .minimumScaleFactor(0.6)
                Spacer(minLength: 8)
                Button { showHowTo = true } label: {
                    Image(systemName: "questionmark.circle")
                        .font(.system(size: 24))
                        .foregroundStyle(Theme.sandDim)
                        .frame(width: 44, height: 44)
                }
                .accessibilityLabel("How to play")
                Button { showSettings = true } label: {
                    Image(systemName: "gearshape")
                        .font(.system(size: 24))
                        .foregroundStyle(Theme.sandDim)
                        .frame(width: 44, height: 44)
                }
                .accessibilityLabel("Settings")
            }
            Text("Send the colony out. Carry the mosaic home, one tile at a time.")
                .font(Theme.label(17))
                .foregroundStyle(Theme.sandDim)
        }
        .padding(.top, 10)
    }

    @ViewBuilder
    private var nextUpBanner: some View {
        HStack(spacing: 16) {
            if let next = app.nextUp {
                if let img = app.thumbnail(for: next) {
                    Image(decorative: img, scale: 1)
                        .resizable()
                        .interpolation(.none)
                        .aspectRatio(contentMode: .fit)
                        .frame(width: 70, height: 80)
                        .clipShape(RoundedRectangle(cornerRadius: 8))
                }
                VStack(alignment: .leading, spacing: 4) {
                    Text("NEXT UP")
                        .font(Theme.label(12, weight: .bold))
                        .tracking(1.5)
                        .foregroundStyle(Theme.brass)
                    Text(next.title)
                        .font(Theme.title(24))
                        .foregroundStyle(Theme.sand)
                    Text("\(next.tileCount) tiles · \(next.teamCount) teams")
                        .font(Theme.label(13))
                        .foregroundStyle(Theme.sandDim)
                }
                Spacer()
                Button(app.savedMoves(for: next) != nil ? "Resume…" : "Play…") { starting = StartItem(level: next) }
                    .buttonStyle(PillButtonStyle(prominent: true))
            } else {
                VStack(alignment: .leading, spacing: 4) {
                    Text("ALL MOSAICS FINISHED")
                        .font(Theme.label(12, weight: .bold))
                        .tracking(1.5)
                        .foregroundStyle(Theme.brass)
                    Text("Make a new level from a pattern or a photo.")
                        .font(Theme.label(15))
                        .foregroundStyle(Theme.sand)
                }
                Spacer()
                Button("New pattern") { app.createPatternLevel() }
                    .buttonStyle(PillButtonStyle(prominent: true))
                    .disabled(app.photoBusy)
            }
        }
        .padding(16)
        .background(RoundedRectangle(cornerRadius: 20, style: .continuous).fill(Theme.panel))
        .overlay(RoundedRectangle(cornerRadius: 20, style: .continuous).strokeBorder(Theme.brass.opacity(0.6), lineWidth: 1.5))
    }

    private func makeNewSection(wide: Bool) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            sectionTitle("MAKE A NEW LEVEL")
            let cards = Group {
                VStack(alignment: .leading, spacing: 10) {
                    Label("Pattern mosaic", systemImage: "sparkles")
                        .font(Theme.title(20))
                        .foregroundStyle(Theme.sand)
                    Text("A fresh pattern (about 2,400 tiles) every time you tap — a rosette, a starburst, fish scales, a kaleidoscope or crossed ribbons, each drawn new from its own seed. Each one is planned and checked on the iPad so it can be solved.")
                        .font(Theme.label(14))
                        .foregroundStyle(Theme.sandDim)
                        .fixedSize(horizontal: false, vertical: true)
                    Spacer(minLength: 0)
                    Button {
                        app.createPatternLevel()
                    } label: {
                        Label(app.photoBusy ? "Building…" : "New pattern", systemImage: "wand.and.stars")
                    }
                    .buttonStyle(PillButtonStyle(prominent: true))
                    .disabled(app.photoBusy)
                }
                .padding(16)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(RoundedRectangle(cornerRadius: 20, style: .continuous).fill(Theme.panel))
                .overlay(RoundedRectangle(cornerRadius: 20, style: .continuous).strokeBorder(Theme.panelEdge, lineWidth: 1))
                VStack(alignment: .leading, spacing: 10) {
                    Label("From your photo", systemImage: "photo.on.rectangle.angled")
                        .font(Theme.title(20))
                        .foregroundStyle(Theme.sand)
                    Text("White and near-white areas become open ground; every coloured tile is part of the puzzle.")
                        .font(Theme.label(14))
                        .foregroundStyle(Theme.sandDim)
                        .fixedSize(horizontal: false, vertical: true)
                    Picker("Tile size", selection: $app.settings.photoDetail) {
                        ForEach(PhotoDetail.allCases) { d in
                            Text(d.title).tag(d)
                        }
                    }
                    .pickerStyle(.segmented)
                    PhotosPicker(selection: $pickedPhoto, matching: .images) {
                        Label(app.photoBusy ? "Building…" : "Choose a photo", systemImage: "photo")
                            .font(Theme.label(14, weight: .bold))
                            .padding(.horizontal, 16)
                            .frame(minHeight: 44)
                            .foregroundStyle(Color(hex: 0x2A1C12))
                            .background(Capsule().fill(Theme.brass))
                    }
                    .disabled(app.photoBusy)
                }
                .padding(16)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(RoundedRectangle(cornerRadius: 20, style: .continuous).fill(Theme.panel))
                .overlay(RoundedRectangle(cornerRadius: 20, style: .continuous).strokeBorder(Theme.panelEdge, lineWidth: 1))
            }
            if wide {
                HStack(alignment: .top, spacing: 18) { cards }
            } else {
                VStack(spacing: 16) { cards }
            }
            if app.photoBusy {
                HStack(spacing: 8) {
                    ProgressView().tint(Theme.brass)
                    Text("Planning teams and tunnels…")
                        .font(Theme.label(13))
                        .foregroundStyle(Theme.sandDim)
                }
            }
            if let msg = app.photoMessage {
                HStack(alignment: .top, spacing: 8) {
                    Image(systemName: "info.circle.fill").foregroundStyle(Theme.brass)
                    Text(msg)
                        .font(Theme.label(14))
                        .foregroundStyle(Theme.sand)
                        .fixedSize(horizontal: false, vertical: true)
                    Spacer(minLength: 0)
                    Button("OK") { app.photoMessage = nil }
                        .buttonStyle(PillButtonStyle(prominent: false))
                }
                .padding(12)
                .background(RoundedRectangle(cornerRadius: 12).fill(Theme.loamRaised))
            }
        }
    }

    private var gallery: some View {
        VStack(alignment: .leading, spacing: 12) {
            sectionTitle("NEST GALLERY")
            Text("Mosaics your colony has carried home and re-laid underground.")
                .font(Theme.label(14))
                .foregroundStyle(Theme.sandDim)
            let done = app.allLevels.filter { app.progress[$0.id] != nil }
            if done.isEmpty {
                Text("Nothing here yet — finish a mosaic and it hangs here.")
                    .font(Theme.label(14))
                    .foregroundStyle(Theme.sandDim)
            } else {
                ScrollView(.horizontal, showsIndicators: false) {
                    LazyHStack(spacing: 14) {
                        ForEach(done, id: \.id) { level in
                            GalleryFrame(title: level.title, image: app.thumbnail(for: level),
                                         caption: caption(for: level))
                        }
                    }
                }
            }
        }
    }

    func caption(for level: LevelDefinition) -> String {
        guard let rec = app.progress[level.id] else {
            if let req = app.unlockRequirement(level) { return "Locked — finish \(req)" }
            return "Not yet completed"
        }
        let secs = Int(rec.bestSeconds)
        let mm = secs / 60
        let ss = secs % 60
        let pad = ss < 10 ? "0" : ""
        return "Best \(mm):\(pad)\(ss) · \(rec.difficulty.title)"
    }
}

/// A large, full-width tappable tile (Home's Two players / High scores).
struct BigActionButton: View {
    let icon: String
    let title: String
    let subtitle: String
    let prominent: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: 14) {
                Image(systemName: icon)
                    .font(.system(size: 28, weight: .semibold))
                    .frame(width: 40)
                VStack(alignment: .leading, spacing: 2) {
                    Text(title)
                        .font(Theme.title(22))
                        .lineLimit(1)
                        .minimumScaleFactor(0.7)
                    Text(subtitle)
                        .font(Theme.label(13))
                        .opacity(0.8)
                        .lineLimit(2)
                        .minimumScaleFactor(0.8)
                }
                Spacer(minLength: 0)
                Image(systemName: "chevron.right")
                    .font(.system(size: 16, weight: .bold))
                    .opacity(0.7)
            }
            .foregroundStyle(prominent ? Color(hex: 0x2A1C12) : Theme.sand)
            .padding(.horizontal, 18)
            .frame(maxWidth: .infinity, minHeight: 84, alignment: .leading)
            .background(RoundedRectangle(cornerRadius: 20, style: .continuous).fill(prominent ? Theme.brass : Theme.panel))
            .overlay(RoundedRectangle(cornerRadius: 20, style: .continuous)
                .strokeBorder(prominent ? Color.clear : Theme.brass.opacity(0.6), lineWidth: 1.5))
            .contentShape(RoundedRectangle(cornerRadius: 20, style: .continuous))
        }
        .buttonStyle(PressableStyle())
    }
}

/// Dims slightly while pressed.
struct PressableStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .opacity(configuration.isPressed ? 0.8 : 1)
            .scaleEffect(configuration.isPressed ? 0.98 : 1)
    }
}

struct GalleryFrame: View {
    let title: String
    let image: CGImage?
    let caption: String

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            ZStack {
                RoundedRectangle(cornerRadius: 8).fill(Color(hex: 0x2A2019))
                if let img = image {
                    Image(decorative: img, scale: 1)
                        .resizable()
                        .interpolation(.none)
                        .aspectRatio(contentMode: .fit)
                        .padding(6)
                } else {
                    Image(systemName: "lock.fill")
                        .font(.system(size: 22))
                        .foregroundStyle(Theme.panelEdge)
                }
            }
            .frame(width: 150, height: 170)
            .overlay(RoundedRectangle(cornerRadius: 8).strokeBorder(image == nil ? Theme.panelEdge : Theme.brass, lineWidth: 3))
            Text(title)
                .font(Theme.title(15))
                .foregroundStyle(Theme.sand)
                .lineLimit(1)
            Text(caption)
                .font(Theme.label(12))
                .foregroundStyle(Theme.sandDim)
                .lineLimit(2)
                .frame(width: 150, alignment: .leading)
        }
    }
}

struct LevelCard: View {
    @EnvironmentObject var app: AppModel
    let level: LevelDefinition
    /// Opens the start sheet (difficulty choice, resume or new game).
    let onPlay: () -> Void
    @State private var confirmDelete = false

    var body: some View {
        let saved = app.savedMoves(for: level)
        let done = app.progress[level.id]
        let requirement = app.unlockRequirement(level)
        VStack(alignment: .leading, spacing: 12) {
            if let img = app.thumbnail(for: level) {
                Image(decorative: img, scale: 1)
                    .resizable()
                    .interpolation(.none)
                    .aspectRatio(contentMode: .fit)
                    .frame(maxWidth: .infinity, maxHeight: 280)
                    .background(Color(hex: 0x2A2019))
                    .clipShape(RoundedRectangle(cornerRadius: 10))
                    .overlay(RoundedRectangle(cornerRadius: 10).strokeBorder(Theme.panelEdge, lineWidth: 2))
                    .saturation(requirement == nil ? 1 : 0.15)
                    .opacity(requirement == nil ? 1 : 0.55)
                    .overlay {
                        if requirement != nil {
                            Image(systemName: "lock.fill")
                                .font(.system(size: 34))
                                .foregroundStyle(Theme.sand)
                        }
                    }
            }
            HStack(alignment: .firstTextBaseline) {
                Text(level.title)
                    .font(Theme.title(22))
                    .foregroundStyle(Theme.sand)
                    .lineLimit(1)
                Spacer()
                if done != nil {
                    Label("Completed", systemImage: "checkmark.seal.fill")
                        .font(Theme.label(13, weight: .bold))
                        .foregroundStyle(Theme.ok)
                }
            }
            Text("\(level.subtitle) · \(level.tileCount) tiles · \(level.teamCount) teams in \(level.tunnels.count) tunnels")
                .font(Theme.label(14))
                .foregroundStyle(Theme.sandDim)
            RatingLine(stats: app.difficultyStats(for: level), difficulty: app.settings.difficulty)
            HStack(spacing: 10) {
                if let req = requirement {
                    Text("Locked — finish \(req) to unlock")
                        .font(Theme.label(14, weight: .bold))
                        .foregroundStyle(Theme.brass)
                } else if let moves = saved {
                    Button("Resume (\(moves) moves)…", action: onPlay)
                        .buttonStyle(PillButtonStyle(prominent: true))
                } else {
                    Button(done == nil ? "Play…" : "Play again…", action: onPlay)
                        .buttonStyle(PillButtonStyle(prominent: true))
                }
                Spacer()
                if level.isPhoto {
                    Button(role: .destructive) { confirmDelete = true } label: {
                        Image(systemName: "trash")
                            .frame(width: 44, height: 44)
                    }
                    .foregroundStyle(Theme.danger)
                    .accessibilityLabel("Delete this mosaic")
                }
            }
        }
        .padding(16)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(RoundedRectangle(cornerRadius: 20, style: .continuous).fill(Theme.panel))
        .overlay(RoundedRectangle(cornerRadius: 20, style: .continuous).strokeBorder(Theme.panelEdge, lineWidth: 1))
        .onAppear { app.measureIfNeeded(level) }
        .alert("Delete this mosaic?", isPresented: $confirmDelete) {
            Button("Delete", role: .destructive) { app.deletePhotoLevel(id: level.id) }
            Button("Cancel", role: .cancel) {}
        }
    }
}

struct SettingsView: View {
    @EnvironmentObject var app: AppModel
    @Environment(\.dismiss) private var dismiss
    @State private var results: [SelfTestResult] = []
    @State private var running = false
    @State private var confirmReset = false

    var body: some View {
        NavigationStack {
            Form {
                Section("Play") {
                    Toggle("Detailed legs (feet plant and lift)", isOn: $app.settings.detailedAnts)
                    Toggle("Unlock all mosaics", isOn: $app.settings.unlockAll)
                    VStack(alignment: .leading) {
                        Text("Default ant speed: " + String(format: "%.2f×", app.settings.antSpeed))
                        Slider(value: $app.settings.antSpeed, in: 0.1...16.0)
                    }
                }
                Section {
                    Picker("Ant paths", selection: $app.settings.pathStyle) {
                        ForEach(PathStyle.allCases) { style in
                            Text(style.title).tag(style)
                        }
                    }
                } header: {
                    Text("Ant paths")
                } footer: {
                    Text(app.settings.pathStyle.blurb + " Applies to ants launched after you change it; ants already walking finish their route. Ants carrying a tile always come home in the middle lane.")
                }
                Section {
                    Toggle("Sound effects", isOn: $app.settings.soundOn)
                    VStack(alignment: .leading) {
                        Text("Volume: \(Int((app.settings.soundVolume * 100).rounded()))%")
                        Slider(value: $app.settings.soundVolume, in: 0...1) { editing in
                            if !editing { SoundBoard.shared.play(.teamDone) }
                        }
                    }
                    .disabled(!app.settings.soundOn)
                    HStack {
                        Toggle("Action sounds", isOn: $app.settings.actionSounds)
                        Button("Play a sample") { SoundBoard.shared.playSample(.action) }
                            .buttonStyle(.bordered)
                    }
                    .disabled(!app.settings.soundOn)
                    HStack {
                        Toggle("Goal sounds", isOn: $app.settings.goalSounds)
                        Button("Play a sample") { SoundBoard.shared.playSample(.goal) }
                            .buttonStyle(.bordered)
                    }
                    .disabled(!app.settings.soundOn)
                    Toggle("Colony clinks (ants lifting and delivering tiles)", isOn: $app.settings.tileClicks)
                        .disabled(!app.settings.soundOn)
                    Toggle("Play sounds even in Silent mode", isOn: $app.settings.soundInSilentMode)
                        .disabled(!app.settings.soundOn)
                    SoundCheckRow()
                } header: {
                    Text("Sound")
                } footer: {
                    Text("Action sounds are dry wood and clay: sending, scouting, undo, adding a slot, returning a team, a refused tap, a team that must wait, blocked, hints. Goal sounds are bells and glass: a team finishing, a whole colour lifted, each quarter of the mosaic home, the finished mosaic, a new best time and a newly unlocked mosaic. Colony clinks give every colour its own note. Everything is generated on the iPad and follows its volume. If you hear nothing, run the Sound check and make sure the iPad volume is up.")
                }
                Section {
                    LazyVGrid(columns: [GridItem(.adaptive(minimum: 64), spacing: 10)], spacing: 10) {
                        ForEach(0..<GroundPresets.all.count, id: \.self) { i in
                            let preset = GroundPresets.all[i]
                            Button {
                                app.settings.groundColor = preset.1
                            } label: {
                                VStack(spacing: 3) {
                                    RoundedRectangle(cornerRadius: 8)
                                        .fill(Color(hex: preset.1))
                                        .frame(height: 34)
                                        .overlay(RoundedRectangle(cornerRadius: 8)
                                            .strokeBorder(app.settings.groundColor == preset.1 ? Theme.brass : Color.gray.opacity(0.4),
                                                          lineWidth: app.settings.groundColor == preset.1 ? 3 : 1))
                                    Text(preset.0).font(Theme.label(11))
                                }
                            }
                            .buttonStyle(.plain)
                        }
                    }
                    ColorPicker("Any colour", selection: Binding(get: { Color(hex: app.settings.groundColor) },
                                                                set: { app.settings.groundColor = $0.rgbHex() }),
                                supportsOpacity: false)
                } header: {
                    Text("Ground colour behind the mosaic")
                } footer: {
                    Text("You can also change it during a game from the menu (…).")
                }
                Section {
                    Button(running ? "Running…" : "Run engine self-test") { runTests() }
                        .disabled(running)
                    ForEach(results) { r in
                        HStack(alignment: .top) {
                            Image(systemName: r.passed ? "checkmark.circle.fill" : "xmark.octagon.fill")
                                .foregroundStyle(r.passed ? Theme.ok : Theme.danger)
                            VStack(alignment: .leading, spacing: 2) {
                                Text(r.name).font(Theme.label(14, weight: .semibold))
                                if !r.detail.isEmpty {
                                    Text(r.detail).font(Theme.label(12)).foregroundStyle(.secondary)
                                }
                            }
                        }
                    }
                } header: {
                    Text("Diagnostics")
                } footer: {
                    Text("Replays each mosaic's designed solution and compares it with values computed by the reference model, checks every ant path and pickup time, exercises undo, recovery options and save/restore, and builds test mosaics from synthetic photos. Please screenshot the results if anything fails.")
                }
                Section {
                    Button("Replay the tutorial tips") { app.settings.coachSeen = [] }
                    Button("Reset all progress", role: .destructive) { confirmReset = true }
                }
            }
            .navigationTitle("Settings")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button("Done") { dismiss() }
                }
            }
            .alert("Reset all progress?", isPresented: $confirmReset) {
                Button("Reset", role: .destructive) { app.resetEverything() }
                Button("Cancel", role: .cancel) {}
            } message: {
                Text("Clears finished mosaics, saved games, high scores and settings.")
            }
        }
        .preferredColorScheme(.dark)
    }

    private func runTests() {
        running = true
        results = []
        // if a test ever stops the app, the next launch reports which step it was on
        FlightRecorder.shared.begin(["In-app self-test (Settings)"])
        Task {
            let r = await Task.detached(priority: .userInitiated) { SelfTest.runAll() }.value
            FlightRecorder.shared.end()
            results = r
            running = false
        }
    }
}

/// A level waiting to be started (drives the start sheet).
struct StartItem: Identifiable {
    let level: LevelDefinition
    var id: String { level.id }
}

/// Five dots, filled up to the rating (green → red).
struct RatingDots: View {
    let level: Int
    var size: CGFloat = 9

    var body: some View {
        HStack(spacing: 3) {
            ForEach(1...5, id: \.self) { k in
                Circle()
                    .fill(k <= level ? RatingDots.color(level) : Theme.panelEdge)
                    .frame(width: size, height: size)
            }
        }
        .accessibilityHidden(true)
    }

    static func color(_ level: Int) -> Color {
        switch level {
        case 1: return Theme.ok
        case 2: return Color(hex: 0x9CC45A)
        case 3: return Theme.brass
        case 4: return Color(hex: 0xE0803A)
        default: return Theme.danger
        }
    }
}

/// "Classic: Tricky ●●●○○" on a mosaic card.
struct RatingLine: View {
    let stats: DifficultyStats?
    let difficulty: Difficulty

    var body: some View {
        HStack(spacing: 8) {
            if let st = stats {
                let r = st.rating(difficulty)
                Text("\(difficulty.title):")
                    .font(Theme.label(13))
                    .foregroundStyle(Theme.sandDim)
                Text(r.word)
                    .font(Theme.label(13, weight: .bold))
                    .foregroundStyle(RatingDots.color(r.level))
                RatingDots(level: r.level)
            } else {
                ProgressView().controlSize(.mini).tint(Theme.brass)
                Text("Measuring how hard it is…")
                    .font(Theme.label(13))
                    .foregroundStyle(Theme.sandDim)
            }
        }
        .accessibilityElement(children: .combine)
    }
}

/// Opened by Play: choose Gentle / Classic / Expert with this mosaic's slots and measured
/// difficulty for each, then start (or resume the saved game on its own difficulty).
struct LevelStartSheet: View {
    @EnvironmentObject var app: AppModel
    @Environment(\.dismiss) private var dismiss
    let level: LevelDefinition
    @State private var choice: Difficulty = .classic
    @State private var mods: Set<ChallengeModifier> = []

    var body: some View {
        let stats = app.difficultyStats(for: level)
        let saved = app.savedGame(for: level)
        let savedMoveCount = app.savedMoves(for: level) ?? 0
        ScrollView {
            VStack(alignment: .leading, spacing: 14) {
                HStack(alignment: .top, spacing: 16) {
                    if let img = app.thumbnail(for: level) {
                        Image(decorative: img, scale: 1)
                            .resizable()
                            .interpolation(.none)
                            .aspectRatio(contentMode: .fit)
                            .frame(width: 84, height: 96)
                            .clipShape(RoundedRectangle(cornerRadius: 8))
                            .overlay(RoundedRectangle(cornerRadius: 8).strokeBorder(Theme.panelEdge, lineWidth: 2))
                    }
                    VStack(alignment: .leading, spacing: 4) {
                        if level.pack != "main" {
                            Text(LevelCatalog.packTitle(level.pack))
                                .font(Theme.label(12, weight: .bold))
                                .tracking(1.5)
                                .foregroundStyle(level.isChallenge ? Theme.danger : Theme.ok)
                        }
                        Text(level.title)
                            .font(Theme.title(24))
                            .foregroundStyle(Theme.sand)
                        Text(level.subtitle)
                            .font(Theme.label(14))
                            .foregroundStyle(Theme.sandDim)
                        Text("\(level.tileCount) tiles · \(level.teamCount) teams · \(level.tunnels.count) tunnels")
                            .font(Theme.label(13))
                            .foregroundStyle(Theme.sandDim)
                        if app.progress[level.id] != nil {
                            HStack(spacing: 8) {
                                StarRow(stars: app.stars(level.id), mastered: app.isMastered(level.id), size: 14)
                                Text(app.isMastered(level.id) ? "Mastered" : "Stars: Gentle · Classic · Expert")
                                    .font(Theme.label(12))
                                    .foregroundStyle(Theme.sandDim)
                            }
                        }
                    }
                    Spacer(minLength: 0)
                    Button { dismiss() } label: {
                        Image(systemName: "xmark.circle.fill")
                            .font(.system(size: 28))
                            .foregroundStyle(Theme.sandDim)
                            .frame(width: 44, height: 44)
                    }
                    .accessibilityLabel("Close")
                }
                Text("CHOOSE A DIFFICULTY")
                    .font(Theme.label(13, weight: .bold))
                    .tracking(2)
                    .foregroundStyle(Theme.brass)
                ForEach(Difficulty.allCases) { d in
                    difficultyRow(d, stats: stats)
                }
                if stats == nil {
                    HStack(spacing: 8) {
                        ProgressView().tint(Theme.brass)
                        Text("Measuring how hard this mosaic is on each difficulty…")
                            .font(Theme.label(13))
                            .foregroundStyle(Theme.sandDim)
                    }
                }
                Text("Ratings come from computer play-throughs of this mosaic: how often careless tapping wins, and whether always sending a team that can finish right now is enough.")
                    .font(Theme.label(12))
                    .foregroundStyle(Theme.sandDim.opacity(0.85))
                    .fixedSize(horizontal: false, vertical: true)
                harderOptions
                highScores
            }
            .padding(.horizontal, 22)
            .padding(.top, 20)
            .padding(.bottom, 12)
        }
        // the start buttons stay pinned at the bottom, always visible
        .safeAreaInset(edge: .bottom, spacing: 0) {
            VStack(spacing: 0) {
                Rectangle().fill(Theme.panelEdge).frame(height: 1)
                HStack(spacing: 10) {
                    if let s = saved {
                        Button {
                            dismiss()
                            app.play(level, fresh: false)
                        } label: {
                            Text("Resume · \(s.difficulty.title) · \(savedMoveCount) moves")
                                .lineLimit(1)
                                .minimumScaleFactor(0.7)
                                .frame(maxWidth: .infinity)
                        }
                        .buttonStyle(PillButtonStyle(prominent: true))
                        Button {
                            dismiss()
                            app.play(level, fresh: true, difficulty: choice, modifiers: mods)
                        } label: {
                            Text("New game on \(choice.title)" + optionsSuffix)
                                .lineLimit(1)
                                .minimumScaleFactor(0.7)
                                .frame(maxWidth: .infinity)
                        }
                        .buttonStyle(PillButtonStyle(prominent: false))
                    } else {
                        Button {
                            dismiss()
                            app.play(level, fresh: true, difficulty: choice, modifiers: mods)
                        } label: {
                            Text("Start on \(choice.title)" + optionsSuffix)
                                .lineLimit(1)
                                .minimumScaleFactor(0.7)
                                .frame(maxWidth: .infinity)
                        }
                        .buttonStyle(PillButtonStyle(prominent: true))
                    }
                }
                    .padding(.horizontal, 22)
                    .padding(.vertical, 14)
            }
            .background(Theme.loamRaised.ignoresSafeArea())
        }
        .background(Theme.loam.ignoresSafeArea())
        .preferredColorScheme(.dark)
        .onAppear {
            choice = app.savedGame(for: level)?.difficulty ?? app.settings.difficulty
            mods = Set(app.settings.lastModifiers)
            app.measureIfNeeded(level)
        }
    }

    private var optionsSuffix: String {
        mods.isEmpty ? "" : " · \(mods.count) harder"
    }

    /// Optional rules that make this mosaic harder and multiply the score.
    private var harderOptions: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(alignment: .firstTextBaseline) {
                Text("HARDER OPTIONS")
                    .font(Theme.label(13, weight: .bold))
                    .tracking(2)
                    .foregroundStyle(Theme.brass)
                Spacer()
                Text("Score ×" + String(format: "%.2f", ScoreRules.difficultyFactor(choice) * ScoreRules.modifierFactor(mods)))
                    .font(Theme.label(14, weight: .bold))
                    .foregroundStyle(Theme.sand)
                    .monospacedDigit()
            }
            LazyVGrid(columns: [GridItem(.flexible(), spacing: 8), GridItem(.flexible(), spacing: 8)], spacing: 8) {
                ForEach(ChallengeModifier.allCases) { m in
                    modifierChip(m)
                }
            }
            Text(mods.isEmpty ? "Optional. Each one makes any mosaic harder and raises your score. None of them makes a mosaic impossible."
                              : ChallengeModifier.sorted(mods).map { $0.blurb }.joined(separator: " "))
                .font(Theme.label(12))
                .foregroundStyle(Theme.sandDim)
                .fixedSize(horizontal: false, vertical: true)
        }
    }

    private func modifierChip(_ m: ChallengeModifier) -> some View {
        let on = mods.contains(m)
        return Button {
            if on { _ = mods.remove(m) } else { _ = mods.insert(m) }
        } label: {
            HStack(spacing: 8) {
                Image(systemName: on ? "checkmark.square.fill" : "square")
                    .font(.system(size: 18))
                    .foregroundStyle(on ? Theme.brass : Theme.sandDim)
                Image(systemName: m.systemImage)
                    .font(.system(size: 14, weight: .semibold))
                    .foregroundStyle(on ? Theme.danger : Theme.sandDim)
                Text(m.title)
                    .font(Theme.label(14, weight: .semibold))
                    .foregroundStyle(Theme.sand)
                    .lineLimit(1)
                    .minimumScaleFactor(0.75)
                Spacer(minLength: 2)
                Text("+\(Int((m.bonus * 100).rounded()))%")
                    .font(Theme.label(12, weight: .bold))
                    .foregroundStyle(on ? Theme.brass : Theme.sandDim)
            }
            .padding(.horizontal, 10)
            .frame(maxWidth: .infinity, minHeight: 44)
            .background(RoundedRectangle(cornerRadius: 12, style: .continuous).fill(on ? Theme.loamRaised : Theme.panel))
            .overlay(RoundedRectangle(cornerRadius: 12, style: .continuous)
                .strokeBorder(on ? Theme.brass : Theme.panelEdge, lineWidth: on ? 2 : 1))
            .contentShape(RoundedRectangle(cornerRadius: 12))
        }
        .buttonStyle(.plain)
        .accessibilityLabel("\(m.title), plus \(Int((m.bonus * 100).rounded())) percent score. \(m.blurb)")
        .accessibilityAddTraits(on ? .isSelected : [])
    }

    @ViewBuilder
    private var highScores: some View {
        let top = app.topScores(.solo, levelID: level.id)
        VStack(alignment: .leading, spacing: 8) {
            Text("HIGH SCORES")
                .font(Theme.label(13, weight: .bold))
                .tracking(2)
                .foregroundStyle(Theme.brass)
            if top.isEmpty {
                Text("No high score on this mosaic yet — finish it to put your name here.")
                    .font(Theme.label(13))
                    .foregroundStyle(Theme.sandDim)
            } else {
                HighScoreList(entries: top)
            }
        }
    }

    private func bestText(_ d: Difficulty) -> String? {
        guard let secs = app.progress[level.id]?.bestByDifficulty?[d.rawValue] else { return nil }
        let s = Int(secs)
        return String(format: "Your best: %d:%02d", s / 60, s % 60)
    }

    private func difficultyRow(_ d: Difficulty, stats: DifficultyStats?) -> some View {
        let selected = d == choice
        return Button { choice = d } label: {
            HStack(alignment: .top, spacing: 12) {
                Image(systemName: selected ? "largecircle.fill.circle" : "circle")
                    .font(.system(size: 22))
                    .foregroundStyle(selected ? Theme.brass : Theme.sandDim)
                VStack(alignment: .leading, spacing: 4) {
                    HStack(alignment: .firstTextBaseline) {
                        Text(d.title)
                            .font(Theme.title(19))
                            .foregroundStyle(Theme.sand)
                        Spacer()
                        Text("\(level.chambers(for: d)) slots")
                            .font(Theme.label(14, weight: .bold))
                            .foregroundStyle(Theme.brass)
                            .monospacedDigit()
                    }
                    if selected {
                        Text(d.blurb)
                            .font(Theme.label(13))
                            .foregroundStyle(Theme.sandDim)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                    if let st = stats {
                        let r = st.rating(d)
                        HStack(spacing: 8) {
                            RatingDots(level: r.level, size: 10)
                            Text(r.word)
                                .font(Theme.label(14, weight: .bold))
                                .foregroundStyle(RatingDots.color(r.level))
                            Text("· careless tapping wins \(st.carelessPercent(d))%")
                                .font(Theme.label(13))
                                .foregroundStyle(Theme.sandDim)
                        }
                        if selected {
                            Text(r.explanation)
                                .font(Theme.label(13))
                                .foregroundStyle(Theme.sand.opacity(0.9))
                                .fixedSize(horizontal: false, vertical: true)
                        }
                    }
                    if let best = bestText(d) {
                        Text(best)
                            .font(Theme.label(12, weight: .bold))
                            .foregroundStyle(Theme.ok)
                    }
                }
            }
            .padding(.horizontal, 14)
            .padding(.vertical, 10)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(RoundedRectangle(cornerRadius: 16, style: .continuous).fill(selected ? Theme.loamRaised : Theme.panel))
            .overlay(RoundedRectangle(cornerRadius: 16, style: .continuous)
                .strokeBorder(selected ? Theme.brass : Theme.panelEdge, lineWidth: selected ? 2.5 : 1))
            .contentShape(RoundedRectangle(cornerRadius: 16))
        }
        .buttonStyle(.plain)
        .accessibilityLabel("\(d.title), \(level.chambers(for: d)) slots" + (stats.map { ", " + $0.rating(d).word } ?? ""))
        .accessibilityAddTraits(selected ? .isSelected : [])
    }
}

/// Settings → Sound: plays a test chime and shows what the audio system reports, so a silent
/// iPad can be diagnosed (Silent mode, volume, output route, engine errors).
struct SoundCheckRow: View {
    @State private var report: String?

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Button {
                let played = SoundBoard.shared.playTestSound()
                // give the engine a moment, then read its state
                Task { @MainActor in
                    try? await Task.sleep(nanoseconds: 400_000_000)
                    report = describe(SoundBoard.shared.status(), played: played)
                }
            } label: {
                Label("Sound check: play a test chime", systemImage: "speaker.wave.3")
            }
            if let r = report {
                Text(r)
                    .font(.system(size: 13, design: .monospaced))
                    .foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
    }

    private func describe(_ s: SoundBoard.Status, played: Bool) -> String {
        var lines: [String] = []
        lines.append("Sound effects: " + (s.enabled ? "on" : "OFF (switch on above)"))
        lines.append("Sounds ready: \(s.soundsReady) of 38" + (s.soundsReady == 0 ? " — still preparing, tap again" : ""))
        lines.append("Test chime started: " + (played ? "yes" : "no"))
        lines.append("Audio engine running: " + (s.engineRunning ? "yes" : "no"))
        lines.append("Session: \(s.category)")
        lines.append("Output: \(s.outputs)")
        lines.append("iPad volume: \(Int((s.deviceVolume * 100).rounded()))%" + (s.deviceVolume < 0.05 ? " — turn the volume up" : ""))
        lines.append("Sounds started since launch: \(s.started)")
        if let e = s.error { lines.append("Last error: \(e)") }
        return lines.joined(separator: "\n")
    }
}
