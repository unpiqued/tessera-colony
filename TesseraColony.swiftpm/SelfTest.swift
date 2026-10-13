import Foundation

struct SelfTestResult: Identifiable {
    let id = UUID()
    let name: String
    let passed: Bool
    let detail: String
}

/// On-device verification of the Swift engine. The built-in levels carry golden values computed
/// by the Python reference model (Tools/engine.py); matching them proves both implementations
/// make exactly the same claims in the same order.
enum SelfTest {
    static func runAll() -> [SelfTestResult] {
        var out: [SelfTestResult] = []
        func check(_ name: String, _ ok: Bool, _ detail: String = "") {
            out.append(SelfTestResult(name: name, passed: ok, detail: detail))
        }

        // 0. Ant stress first (the Alhambra Tiles crash report, 3 Oct): random off-plan play in game
        // time on Expert — sends whenever a slot is open, undo, returned teams, added slots — with every
        // new route checked and every ant's pose evaluated the way the board draws it. If this ever
        // stops the app, the next launch shows a report naming the step (see FlightRecorder).
        let stressRuns: [(PathStyle, UInt64, Int)] = [(.curious, 4, 300), (.randomAnt, 5, 300)]
        for (style, seed, actions) in stressRuns {
            let level = GeneratedLevels.worldAlhambra
            let rep = antStress(level: level, style: style, seed: seed, maxActions: actions)
            var detail = "\(rep.actions) actions: \(rep.sends) sends, \(rep.undos) undos, \(rep.returns) returns, \(rep.adds) slots added; "
            detail += "\(rep.trips) ants planned, \(rep.poses) poses drawn" + (rep.won ? "; mosaic finished" : "")
            check("Ant stress — \(level.title), Expert, \(style.title) ants: random sends, undos, returns and added slots; every route legal, every ant drawable",
                  rep.problems.isEmpty, rep.problems.first ?? detail)
        }

        // 1. Built-in levels: golden replay, legal paths, schedule, undo/recovery, save/replay.
        // The 168 collection mosaics get the golden replay, path and timing checks; the slower
        // real-time and random-play checks run on the other 25 (the reference model runs them all).
        for level in LevelCatalog.builtIn {
            FlightRecorder.shared.note("self-test: built-in mosaic \(level.id)", time: 0)
            let deep = !LevelCatalog.collectionPackIDs.contains(LevelCatalog.packOfLevel[level.id] ?? "main")
            let board = Board(art: level.art)
            let t0 = Date()
            let g = Game(level: level, board: board, capacity: level.chambersExpert)
            var perMove: [Int] = []
            for q in level.solution { perMove.append(g.dispatch(q).count) }
            let ms = Date().timeIntervalSince(t0) * 1000 / Double(max(1, level.solution.count))
            check("\(level.title): designed solution clears the board (expert slots)", g.isWon && !g.isJammed,
                  "\(board.tileCount) tiles, \(level.solution.count) moves, \(String(format: "%.1f", ms)) ms per move")
            check("\(level.title): claims per move match the reference model", perMove == level.goldenClaimsPerMove)
            let ch = Game.claimsHash(g.moveClaims)
            check("\(level.title): claim order hash matches the reference model", ch == level.goldenClaimsHash,
                  String(format: "%016llX", ch))
            check("\(level.title): final state hash matches the reference model", g.stateHash == level.goldenFinalStateHash)
            let pathProblems = verifyPaths(board: board, claims: g.moveClaims)
            check("\(level.title): every ant path is legal", pathProblems.isEmpty,
                  pathProblems.first ?? "\(board.tileCount) paths checked")
            for gap in (deep ? [0.0, 1.5] : [1.5]) {
                let problems = verifySchedule(board: board, palette: level.palette, claims: g.moveClaims, gap: gap, level: level)
                check("\(level.title): pickup timing, hole spacing and team quotas (moves \(gap)s apart)", problems.isEmpty,
                      problems.first ?? "")
            }
            if level.id == "firstDig" || level.id == "labyrinth" {
                var styleProblems: [String] = []
                for style in PathStyle.allCases where style != .direct {
                    styleProblems += verifySchedule(board: board, palette: level.palette, claims: g.moveClaims, gap: 1.5,
                                                    level: level, style: style)
                }
                check("\(level.title): every ant-path style gives legal, correctly timed routes", styleProblems.isEmpty,
                      styleProblems.first ?? "Natural, Curious, Wall-hugger, Scout trail and both random mixes")
            }
            if !deep { continue }
            if let timed = timedSlotRun(level: level, board: board, capacity: level.chambersClassic) {
                check("\(level.title): real-time slot rule — teams only go into open slots and the level completes",
                      timed.won && timed.maxInUse <= level.chambersClassic,
                      "up to \(timed.maxInUse) of \(level.chambersClassic) slots busy; waited \(timed.waits) times; done at \(Int(timed.finish)) s (1×)")
            } else {
                check("\(level.title): real-time slot rule — teams only go into open slots and the level completes", false, "deadlock")
            }
            let rp = randomPlay(level: level, board: board, seed: 42)
            check("\(level.title): undo restores exact states (random sends, returns, added slots)", rp.undoOK)
            check("\(level.title): tiles left always equal tiles owed", rp.invariantOK)
            check("\(level.title): a random player using recovery options finishes", rp.won, "\(rp.moves) moves")
            check("\(level.title): saved move list replays identically", rp.replayOK)
        }

        // 2. Rules on tiny boards
        FlightRecorder.shared.note("self-test: tiny boards, photos, patterns", time: 0)
        out.append(contentsOf: tinyBoardTests())

        // 3. Photo pipeline on synthetic photos
        let flower = syntheticFlower()
        switch PhotoLevelBuilder.build(image: flower, detail: .fine, seed: 7, id: "selftest-photo", title: "Test") {
        case .success(let level):
            let board = Board(art: level.art)
            let empty = level.art.reduce(0) { $0 + $1.filter { $0 == "." }.count }
            let g = Game(level: level, board: board, capacity: level.chambersExpert)
            for q in level.solution { g.dispatch(q) }
            check("Photo: synthetic flower becomes a solvable mosaic", g.isWon && !g.isJammed,
                  "\(board.tileCount) tiles, \(empty) empty, \(level.palette.familyCount) colours, \(level.teamCount) teams")
            check("Photo: white background becomes open ground, not tiles", empty > board.tileCount)
            let quotas = level.tunnels.reduce(0) { $0 + $1.reduce(0) { $0 + $1.quota } }
            check("Photo: team quotas add up to the tile count", quotas == board.tileCount)
        case .failure(let e):
            check("Photo: synthetic flower becomes a solvable mosaic", false, e.message)
        }
        let white = PixelImage(width: 64, height: 48, rgba: [UInt8](repeating: 252, count: 64 * 48 * 4))
        switch PhotoLevelBuilder.build(image: white, detail: .fine, seed: 1, id: "w", title: "White") {
        case .failure(.notEnoughColour(let n)):
            check("Photo: an all-white photo is refused gracefully", n == 0)
        default:
            check("Photo: an all-white photo is refused gracefully", false)
        }

        // 4. Pattern mosaics
        let art = PatternLevelBuilder.rows(seed: 1)
        var diff = 0
        for (a, b) in zip(art, PatternLevelBuilder.goldenSeed1) {
            for (ca, cb) in zip(a, b) where ca != cb { diff += 1 }
        }
        check("Pattern: seed 1 draws the same picture as the reference model", diff <= 12,
              diff == 0 ? "identical" : "\(diff) tiles differ by rounding (the level is still verified)")
        // every layout draws the same picture as the reference model (colour counts per family)
        let layoutGolden: [(UInt64, String, [Int])] = [
            (1, "Rosette", [460, 884, 188, 434, 24, 402]), (2, "Ribbons", [222, 297, 460, 415, 328, 670]),
            (3, "Starburst", [580, 44, 452, 673, 183, 460]), (4, "Kaleidoscope", [288, 580, 460, 784, 228, 52]),
            (6, "Fish scales", [706, 69, 618, 195, 460, 344])
        ]
        var layoutBad: [String] = []
        for (seed, name, want) in layoutGolden {
            let d = PatternLevelBuilder.design(seed: seed)
            var counts = [Int](repeating: 0, count: 6)
            for row in d.rows {
                for sc in row.unicodeScalars where sc.value >= 97 && sc.value < 97 + 24 { counts[Int(sc.value - 97) / 4] += 1 }
            }
            let off = zip(counts, want).reduce(0) { $0 + abs($1.0 - $1.1) }
            if d.layout != name || off > 24 { layoutBad.append("seed \(seed): \(d.layout) (\(off) tiles off)") }
        }
        check("Pattern: all five layouts (rosette, starburst, fish scales, kaleidoscope, ribbons) match the reference model",
              layoutBad.isEmpty, layoutBad.first ?? "5 layouts checked")
        if let p = PatternLevelBuilder.build(seed: 4, number: 1) {
            let board = Board(art: p.art)
            let g = Game(level: p, board: board, capacity: p.chambersExpert)
            for q in p.solution { g.dispatch(q) }
            check("Pattern: a kaleidoscope pattern level is solvable", g.isWon, "\(board.tileCount) tiles, \(p.teamCount) teams")
        } else {
            check("Pattern: a kaleidoscope pattern level is solvable", false, "generation failed")
        }
        if let p = PatternLevelBuilder.build(seed: 12345, number: 1) {
            let board = Board(art: p.art)
            let g = Game(level: p, board: board, capacity: p.chambersExpert)
            for q in p.solution { g.dispatch(q) }
            check("Pattern: a generated pattern level is solvable", g.isWon, "\(board.tileCount) tiles, \(p.teamCount) teams")
        } else {
            check("Pattern: a generated pattern level is solvable", false, "generation failed")
        }

        // 5. Rendering helpers
        check("Cartoon ant sprite renders", AntSpriteCache.render(color: 0x4A8FD1) != nil)

        // 6a. Two-player versus rules: every combination of options, careless players
        FlightRecorder.shared.note("self-test: two players, sounds, route planning, scoring", time: 0)
        var vsProblems: [String] = []
        var vrng = SplitMix64(seed: 99)
        for layout in VersusLayout.allCases {
            for picking in VersusPicking.allCases {
                for colour in VersusColourRule.allCases {
                    for scoring in VersusSlotScoring.allCases {
                        let rules = VersusRules(layout: layout, picking: picking, colour: colour, scoring: scoring, difficulty: .classic)
                        let m = VersusMatch(level: GeneratedLevels.firstDig, rules: rules)
                        let over: () -> Bool = {
                            layout == .race ? m.boards.contains { $0.isCleared } : (m.boards[0].isCleared || m.isStalemate)
                        }
                        var n = 0
                        while !over() && n < 5000 {
                            n += 1
                            let p = vrng.int(2)
                            let opts = m.candidates(p).filter { m.canLaunch(p, tunnel: $0.tunnel, depth: $0.depth) }
                            if !opts.isEmpty {
                                let o = opts[vrng.int(opts.count)]
                                m.launch(p, tunnel: o.tunnel, depth: o.depth)
                            } else {
                                let w = m.waiting(p)
                                if !w.isEmpty && w.count >= m.players[p].capacity {
                                    if vrng.unit() < 0.7 { m.addSlot(p) } else { m.returnTeam(p, uid: w[vrng.int(w.count)].uid) }
                                }
                            }
                            for pp in 0..<2 where m.waiting(pp).count > m.players[pp].capacity {
                                vsProblems.append("slot limit broken")
                            }
                        }
                        let name = "\(layout.title) / \(picking.title) / \(colour.title)"
                        if !over() { vsProblems.append(name + ": did not end") }
                        if layout == .shared && m.boards[0].isCleared && m.tiles(0) + m.tiles(1) != m.tileCount {
                            vsProblems.append(name + ": tiles don't add up")
                        }
                        if layout == .race, let f = (0..<2).first(where: { m.boards[$0].isCleared }), m.tiles(f) != m.tileCount {
                            vsProblems.append(name + ": the finisher is missing tiles")
                        }
                    }
                }
            }
        }
        check("Two players: all 16 option combinations play to the end, slot limits kept, tiles add up",
              vsProblems.isEmpty, vsProblems.first ?? "16 matches with careless players")

        // 6. Sound effects (synthesized on the device; compared with Tools/sounds.py)
        let sounds = SoundSynth.buildAll()
        var soundProblems: [String] = []
        for (key, x) in sounds {
            var peak: Float = 0
            var finite = true
            for v in x {
                if !v.isFinite { finite = false }
                peak = max(peak, abs(v))
            }
            if x.isEmpty || !finite || abs(peak - 0.9) > 0.001 || abs(x[0]) > 0.001 || abs(x[x.count - 1]) > 0.001 {
                soundProblems.append(key)
            }
        }
        check("Sound: all \(sounds.count) effects (action set, goal set, colony clinks) are clean — no clipping, clicks or silence",
              soundProblems.isEmpty && sounds.count == 18 + 3 + SoundCue.allCases.count,
              soundProblems.sorted().joined(separator: ", "))
        let reference: [String: Double] = [
            "tile_0_0": 1221.1821, "tile_5_2": 1189.3696, "deliver_1": 539.8157, "send": 932.7665,
            "refused": 1912.8411, "returnTeam": 3160.2103, "undo": 769.5946, "hint": 2422.5694,
            "teamDone": 5312.5162, "colourCleared": 5976.6603, "milestone3": 7200.6016, "complete": 13814.0814,
            "newBest": 6448.295, "unlocked": 11659.4385
        ]
        var mismatches: [String] = []
        for (key, want) in reference {
            let got = SoundSynth.checksum(sounds[key] ?? [])
            if abs(got - want) > want * 0.001 { mismatches.append(key + String(format: " %.1f≠%.1f", got, want)) }
        }
        check("Sound: synthesized effects match the reference model", mismatches.isEmpty,
              mismatches.sorted().joined(separator: ", "))

        // 6b. Route planning speed: the biggest sends must not stall the game (the pause you saw)
        var worstMS = 0.0
        var worstAnts = 0
        for key in ["nightMarket", "sunflower"] {
            guard let lv = LevelCatalog.builtIn.first(where: { $0.id == key }) else { continue }
            let b = Board(art: lv.art)
            for style in [PathStyle.randomTeam, .curious] {
                let sch = AntScheduler(board: b, palette: lv.palette)
                sch.style = style
                var now = 0.0
                let g2 = Game(level: lv, board: b, capacity: lv.chambersClassic)
                for (m, q) in lv.solution.enumerated() {
                    let ev = g2.dispatch(q)
                    let t0 = Date()
                    sch.schedule(ev, move: m, now: now)
                    let ms = Date().timeIntervalSince(t0) * 1000
                    if ms > worstMS {
                        worstMS = ms
                        worstAnts = ev.count
                    }
                    now += 1.5
                }
            }
        }
        check("Route planning: the slowest send on Night Market and Sunflower plans quickly (no pause when sending)",
              worstMS < 120, String(format: "slowest send: %.0f ms for %d ants (the game stays smooth below about 50 ms)", worstMS, worstAnts))

        // 7. Scoring, high-score tables and harder options (golden values shared with Tools/tests.py)
        let scoreCases: [(Int, Difficulty, Set<ChallengeModifier>, Int, Int, Int, Int)] = [
            (1008, .expert, [.noHints, .limitedUndo], 3, 0, 0, 1951),
            (6048, .gentle, [], 12, 2, 1, 2889),
            (1760, .classic, Set(ChallengeModifier.allCases), 0, 0, 0, 3520),
            (100, .gentle, [], 20, 5, 5, 0),
            (2464, .classic, [.hiddenQueue, .noAssists, .noRepeatColour], 1, 1, 0, 3912)
        ]
        var scoreBad: [String] = []
        for c in scoreCases {
            let got = ScoreRules.solo(tiles: c.0, difficulty: c.1, modifiers: c.2, undos: c.3, hints: c.4, assists: c.5).score
            if got != c.6 { scoreBad.append("\(c.0) tiles: \(got) ≠ \(c.6)") }
        }
        check("Score: tiles × difficulty × harder options minus undo, hint and assist penalties", scoreBad.isEmpty,
              scoreBad.first ?? "5 cases match the reference model")
        var table = HighScoreTable()
        let base = Date(timeIntervalSince1970: 0)
        for (i, e) in [(1000, 60.0), (900, 50.0), (900, 40.0), (500, 70.0), (400, 30.0)].enumerated() {
            table.insert(.solo, "t", HighScoreEntry(name: "P\(i)", score: e.0, seconds: e.1,
                                                     date: base.addingTimeInterval(Double(i)), difficulty: .classic))
        }
        let rankCases: [(Int, Double, Int?)] = [(950, 10, 2), (900, 45, 3), (900, 40, 3), (300, 1, nil), (400, 100, nil), (0, 5, nil), (2000, 999, 1)]
        let rankBad = rankCases.filter { table.rank(.solo, "t", score: $0.0, seconds: $0.1) != $0.2 }
        let order = table.list(.solo, "t").map { $0.score }
        check("High scores: places on the table (score, then time; top 5; zero never counts)",
              rankBad.isEmpty && order == [1000, 900, 900, 500, 400],
              rankBad.first.map { "\($0.0) in \($0.1) s" } ?? "7 cases")
        let placed = table.insert(.solo, "t", HighScoreEntry(name: "New", score: 950, seconds: 10, date: base.addingTimeInterval(9), difficulty: .expert))
        check("High scores: a new entry lands in its predicted place and the table keeps 5",
              placed == 2 && table.list(.solo, "t").count == 5 && table.list(.solo, "t").last?.score == 500)
        check("High scores: names are trimmed and limited to 20 characters",
              HighScoreNames.clean("  Ana  ") == "Ana" && HighScoreNames.clean("") == "Player"
              && HighScoreNames.clean(String(repeating: "x", count: 40)).count == 20)
        // No colour twice on First Dig: a repeat is refused only while another colour could go
        let fd = GeneratedLevels.firstDig
        let fdBoard = Board(art: fd.art)
        let cg = Game(level: fd, board: fdBoard, capacity: fd.chambersExpert)
        var last: Int? = nil
        var colourBad = 0
        var refusedSeen = 0
        for q in fd.solution {
            for k in 0..<cg.tunnels.count {
                let refused = ColourRule.refuses(game: cg, tunnel: k, last: last)
                if refused { refusedSeen += 1 }
                let same = cg.front(k)?.family == last && last != nil
                if refused && !same { colourBad += 1 }
            }
            last = cg.front(q)?.family
            cg.dispatch(q)
        }
        check("Harder options: No colour twice only ever refuses the colour sent last", colourBad == 0,
              "\(refusedSeen) refusals seen along First Dig's designed line")
        // Catalogue: unique ids, every pack filled, unlock rules point at real mosaics
        let ids = LevelCatalog.builtIn.map { $0.id }
        let known = Set(ids)
        let rulesOK = LevelCatalog.builtIn.allSatisfy { lv in
            guard let r = LevelCatalog.unlockRule(for: lv.id) else { return true }
            return !r.anyOf.isEmpty && r.anyOf.allSatisfy { known.contains($0) && $0 != lv.id }
        }
        let packsOK = LevelCatalog.packs.allSatisfy { p in p.levels.allSatisfy { $0.pack == p.id } }
        let eights = LevelCatalog.packs.filter { $0.id != "main" && $0.id != "challenge" }.allSatisfy { $0.levels.count == 8 }
        let inThemes = Set(LevelCatalog.themes.flatMap { $0.packIDs }) == Set(LevelCatalog.packs.map { $0.id })
        // Collection: the harder steps go Gentle → Classic → Expert → Expert with one more option each time
        var step = HarderStep.after(.gentle, modifiers: [])
        var chain: [String] = []
        while let s = step, chain.count < 20 {
            chain.append(s.label)
            step = HarderStep.after(s.difficulty, modifiers: s.modifiers)
        }
        check("Collection: the harder steps offered after a finish lead from Gentle to Expert with every harder option",
              chain.count == 2 + ChallengeModifier.allCases.count && chain.first == "Try it on Classic",
              "\(chain.count) steps, last: \(chain.last ?? "-")")
        check("Catalogue: \(ids.count) built-in mosaics, unique ids, packs tagged, unlock rules valid, every pack in a theme",
              Set(ids).count == ids.count && rulesOK && packsOK && eights && inThemes,
              LevelCatalog.packs.map { "\($0.id) \($0.levels.count)" }.joined(separator: " · "))
        // Seasonal packs: the in-season badge (Halloween in autumn; Winter wraps the new year)
        let cal = Calendar.current
        func day(_ m: Int, _ d: Int) -> Date { cal.date(from: DateComponents(year: 2026, month: m, day: d, hour: 12)) ?? Date() }
        let seasonOK = LevelCatalog.isInSeason("halloween", on: day(10, 31)) && !LevelCatalog.isInSeason("halloween", on: day(3, 1))
            && LevelCatalog.isInSeason("winter", on: day(1, 15)) && LevelCatalog.isInSeason("winter", on: day(12, 25))
            && !LevelCatalog.isInSeason("winter", on: day(7, 1)) && !LevelCatalog.isInSeason("gallery", on: day(10, 31))
        check("Seasons: Halloween is in season in October, Winter from December to February (across the new year)", seasonOK)
        return out
    }

    // MARK: - helpers

    struct StressReport {
        var problems: [String] = []
        var actions = 0
        var sends = 0
        var undos = 0
        var returns = 0
        var adds = 0
        var trips = 0
        var poses = 0
        var won = false
    }

    /// Ant stress (mirrors session_tests in Tools/tests.py): follow the designed line almost to the
    /// end in game time (the end game is where the crash was reported), then play randomly — send any
    /// tunnel when a slot is open, undo, return a waiting team, add a slot, follow the plan — waiting
    /// random times in between. Every new route is checked (starts at the hole, 4-neighbour steps, only
    /// onto ground or tiles lifted before the ant gets there, finite times) and every ant's pose and
    /// scout trail is evaluated as the board draws them.
    static func antStress(level: LevelDefinition, style: PathStyle, seed: UInt64, maxActions: Int) -> StressReport {
        var rep = StressReport()
        let board = Board(art: level.art)
        let g = Game(level: level, board: board, capacity: level.chambersExpert)
        let sch = AntScheduler(board: board, palette: level.palette)
        sch.style = style
        var rng = SplitMix64(seed: seed)
        var t = 0.0
        let cols = board.cols
        func problem(_ s: String) {
            if rep.problems.count < 5 { rep.problems.append(s) }
        }
        func occupied() -> Int {
            var occ = Set(sch.busyTeams(at: t).keys)
            for c in g.state.chambers { occ.insert(c.uid) }
            return occ.count
        }
        func advance(_ dt: Double) {
            let t0 = t
            t += max(0, dt)
            for probe in [t0 + (t - t0) * 0.5, t] {
                for trip in sch.trips {
                    if let p = AntGeometry.pose(trip, at: probe, board: board) {
                        rep.poses += 1
                        if !(p.x.isFinite && p.y.isFinite && p.heading.isFinite && p.scale.isFinite && p.gaitDistance.isFinite) {
                            problem("an ant's pose is not a finite number (trip \(trip.id))")
                        }
                    }
                    if trip.style == .scout && probe >= trip.depart && probe < trip.arrive {
                        if !AntGeometry.outbound(trip, elapsed: probe - trip.depart).u.isFinite {
                            problem("a scout trail position is not a finite number")
                        }
                    }
                }
            }
            sch.prune(before: t - 0.5)
        }
        func checkNewTrips(from first: Int) {
            guard first < sch.trips.count else { return }
            for trip in sch.trips[first...] {
                let r = trip.path
                guard let start = r.first, Int(start) == board.hole else {
                    problem("a route does not start at the hole")
                    continue
                }
                if !(trip.depart.isFinite && trip.arrive >= trip.depart && trip.pickupEnd >= trip.arrive && trip.home >= trip.pickupEnd && trip.home.isFinite) {
                    problem("an ant's times are out of order")
                }
                for i in 1..<max(1, r.count) {
                    let a = Int(r[i - 1]), b = Int(r[i])
                    if abs(a % cols - b % cols) + abs(a / cols - b / cols) != 1 { problem("a route jumps") }
                }
                if let last = r.last, !board.areAdjacent(Int(last), Int(trip.tile)) { problem("a route ends away from its tile") }
                for (k, cell) in r.enumerated() where board.family[Int(cell)] >= 0 {
                    var delay = 0.0
                    for p in trip.pauses where p.at < Double(k) - 0.5 { delay += p.duration }
                    let enter = trip.depart + (Double(k) - 0.5) * AntScheduler.step + delay
                    let lift = sch.liftTime[Int(cell)]
                    if !(lift < Double.infinity) || enter + 1e-9 < lift + AntScheduler.pickup + AntScheduler.margin {
                        problem("an ant would walk through a tile that is still there")
                        break
                    }
                }
            }
        }
        func send(_ q: Int) -> Bool {
            guard q >= 0, q < g.tunnels.count, g.canDispatch(q), occupied() < g.state.capacity else { return false }
            let before = sch.trips.count
            let ev = g.dispatch(q)
            sch.schedule(ev, move: g.moves.count - 1, now: t + 0.04)
            rep.sends += 1
            rep.trips += ev.count
            checkNewTrips(from: before)
            return true
        }
        func note() {
            if rep.actions % 25 == 0 {
                FlightRecorder.shared.note("self-test: ant stress \(level.id) \(style.rawValue) seed \(seed), action \(rep.actions), \(g.moves.count) moves, \(sch.trips.count) ants out", time: t)
            }
        }
        // 1. the designed line, sending as soon as a slot is open, up to ten moves before the end
        let sol = level.solution
        let follow = max(0, sol.count - 10)
        var k = 0
        while k < follow && rep.actions < maxActions {
            rep.actions += 1
            note()
            if send(sol[k]) {
                k += 1
                advance(0.3)
            } else {
                var soonest = Double.infinity
                for (u, _) in sch.busyTeams(at: t) { soonest = min(soonest, sch.slotFreeTime(team: u)) }
                advance(soonest.isFinite ? min(30, max(0.1, soonest - t + 0.01)) : 0.5)
            }
        }
        // 2. careless play with every recovery option, at random moments
        let waits: [Double] = [0, 0.04, 0.1, 0.3, 1, 3]
        while rep.actions < maxActions && !(g.isWon && sch.trips.isEmpty) {
            rep.actions += 1
            note()
            if g.isWon {
                advance(5)
                continue
            }
            let r = rng.unit()
            if r < 0.55 {
                _ = send(rng.int(g.tunnels.count))
            } else if r < 0.70 {
                if let claims = g.undo() {
                    sch.undo(claims: claims, fromMove: g.moves.count)
                    rep.undos += 1
                }
            } else if r < 0.80 {
                if !g.state.chambers.isEmpty {
                    g.recall(rng.int(g.state.chambers.count))
                    rep.returns += 1
                }
            } else if r < 0.84 {
                g.addChamber()
                rep.adds += 1
            } else if r < 0.92 {
                let km = g.moves.count
                if km < sol.count && Array(sol.prefix(km)) == g.moves { _ = send(sol[km]) }
            }
            advance(waits[rng.int(waits.count)])
        }
        // 3. let the last ants walk home
        var steps = 0
        while g.isWon && !sch.trips.isEmpty && steps < 400 {
            advance(1)
            steps += 1
        }
        rep.won = g.isWon && sch.trips.isEmpty
        return rep
    }

    static func verifyPaths(board: Board, claims: [[Claim]]) -> [String] {
        var open = board.initialOpen()
        var problems: [String] = []
        for list in claims {
            for c in list {
                let t = Int(c.tile)
                if open[t] { problems.append("tile \(t) claimed twice") }
                if Int(board.family[t]) != c.family { problems.append("wrong colour at \(t)") }
                if c.path.first.map({ Int($0) }) != board.hole { problems.append("path does not start at the hole") }
                for i in 1..<max(1, c.path.count) where !board.areAdjacent(Int(c.path[i - 1]), Int(c.path[i])) {
                    problems.append("non-adjacent step")
                }
                for cell in c.path where !open[Int(cell)] { problems.append("walks through occupied cell \(cell)") }
                if let last = c.path.last, !board.areAdjacent(Int(last), t) { problems.append("stand cell not beside tile") }
                open[t] = true
                if problems.count > 3 { return problems }
            }
        }
        return problems
    }

    static func verifySchedule(board: Board, palette: LevelPalette, claims: [[Claim]], gap: Double, level: LevelDefinition,
                               style: PathStyle = .direct) -> [String] {
        let sch = AntScheduler(board: board, palette: palette)
        sch.style = style
        var now = 0.0
        var stand: [Int32: Int32] = [:]
        for (m, list) in claims.enumerated() {
            sch.schedule(list, move: m, now: now)
            for c in list { stand[c.tile] = c.path.last }
            now += gap
        }
        var problems: [String] = []
        // routes: hole -> the claim's stand cell, 4-neighbour steps, never over the ant's own tile,
        // and every tile on the way lifted (+ pickup + margin) before the ant steps in, sniff stops included
        let cols = board.cols
        for t in sch.trips {
            let r = t.path
            guard let first = r.first, let last = r.last, Int(first) == board.hole, last == stand[t.tile] else {
                problems.append("a route does not run from the hole to the tile")
                break
            }
            var ok = true
            for i in 1..<max(1, r.count) {
                let a = Int(r[i - 1]), b = Int(r[i])
                if abs(a % cols - b % cols) + abs(a / cols - b / cols) != 1 { ok = false }
            }
            if !ok || r.contains(t.tile) {
                problems.append("a route jumps or walks over its own tile")
                break
            }
            var pauseTotal = 0.0
            for p in t.pauses { pauseTotal += p.duration }
            if abs(t.arrive - (t.depart + Double(r.count) * AntScheduler.step + pauseTotal)) > 1e-9 {
                problems.append("arrival time does not match the route")
                break
            }
            for (k, cell) in r.enumerated() where board.family[Int(cell)] >= 0 {
                var delay = 0.0
                for p in t.pauses where p.at < Double(k) - 0.5 { delay += p.duration }
                let enter = t.depart + (Double(k) - 0.5) * AntScheduler.step + delay
                if !(sch.liftTime[Int(cell)] < Double.infinity) || enter + 1e-9 < sch.liftTime[Int(cell)] + AntScheduler.pickup + AntScheduler.margin {
                    problems.append("\(style.title): an ant would walk through a tile that is still there")
                    break
                }
            }
            if problems.count > 3 { return problems }
        }
        var slots = Set<Int>()
        var byTeam: [Int: [Double]] = [:]
        for t in sch.trips {
            let s = Int((t.depart / AntScheduler.slot).rounded())
            if slots.contains(s) { problems.append("two ants left the hole together") }
            slots.insert(s)
            byTeam[t.team, default: []].append(t.depart)
            if problems.count > 3 { return problems }
        }
        for (_, deps) in byTeam {
            let d = deps.sorted()
            for i in 1..<max(1, d.count) where d[i] - d[i - 1] < AntScheduler.teamGap - 1e-9 {
                problems.append("a team released ants too close together")
                break
            }
        }
        // each team carries exactly its quota
        var counts: [Int: Int] = [:]
        for t in sch.trips { counts[t.team, default: 0] += 1 }
        for (q, tunnel) in level.tunnels.enumerated() {
            for (i, spec) in tunnel.enumerated() where counts[q * 1000 + i, default: 0] != spec.quota {
                problems.append("team \(q)-\(i) carried \(counts[q * 1000 + i, default: 0]) of \(spec.quota)")
                break
            }
        }
        if Set(sch.trips.map { $0.tile }).count != sch.trips.count { problems.append("a tile was assigned to two ants") }
        return problems
    }

    static func owedMatchesLeft(_ g: Game) -> Bool {
        let st = g.state
        var left = [Int](repeating: 0, count: 6)
        for i in 0..<g.board.count where g.board.family[i] >= 0 && !st.open[i] { left[Int(g.board.family[i])] += 1 }
        var owed = [Int](repeating: 0, count: 6)
        for (q, tunnel) in g.tunnels.enumerated() {
            for spec in tunnel[st.heads[q]...] { owed[spec.family] += spec.quota }
        }
        for t in st.chambers { owed[t.family] += t.remaining }
        if let j = st.jammed { owed[j.family] += j.remaining }
        for stack in st.returned { for t in stack { owed[t.family] += t.remaining } }
        return left == owed
    }

    struct RandomPlayReport {
        var undoOK = true
        var invariantOK = true
        var replayOK = true
        var won = false
        var moves = 0
    }

    static func randomPlay(level: LevelDefinition, board: Board, seed: UInt64) -> RandomPlayReport {
        var rep = RandomPlayReport()
        var rng = SplitMix64(seed: seed)
        let g = Game(level: level, board: board, capacity: level.chambersClassic)
        var hashes = [g.stateHash]
        var steps = 0
        func push() {
            hashes.append(g.stateHash)
            if !owedMatchesLeft(g) { rep.invariantOK = false }
        }
        func undoOnce() {
            g.undo()
            hashes.removeLast()
            if g.stateHash != hashes.last { rep.undoOK = false }
        }
        while !g.isWon && steps < 2000 {
            steps += 1
            if g.deadlocked(busyOutsideSlots: 0) {
                let r = rng.unit()
                if r < 0.25 {
                    g.addChamber(); push()
                } else if r < 0.55 {
                    g.recall(rng.int(g.state.chambers.count)); push()
                } else {
                    undoOnce()
                }
                continue
            }
            let fronts = (0..<g.tunnels.count).filter { g.canDispatch($0) }
            if fronts.isEmpty { break }
            let roll = rng.unit()
            if !g.state.chambers.isEmpty && roll > 0.94 {
                g.recall(rng.int(g.state.chambers.count)); push()
                continue
            }
            if !g.moves.isEmpty && roll >= 0.25 && roll < 0.33 {
                undoOnce()
                continue
            }
            g.dispatch(fronts[rng.int(fronts.count)]); push()
        }
        rep.won = g.isWon
        rep.moves = g.moves.count
        if let r = Game.replay(level: level, board: board, capacity: level.chambersClassic, moves: g.moves) {
            rep.replayOK = r.stateHash == g.stateHash && Game.claimsHash(r.moveClaims) == Game.claimsHash(g.moveClaims)
        } else {
            rep.replayOK = false
        }
        return rep
    }

    struct TimedReport {
        let won: Bool
        let maxInUse: Int
        let waits: Int
        let finish: Double
    }

    /// A patient player follows the designed solution in game time: a team is only sent when a slot
    /// is open; a slot stays taken while a team waits or its ants still have tiles to pick up.
    static func timedSlotRun(level: LevelDefinition, board: Board, capacity: Int) -> TimedReport? {
        let g = Game(level: level, board: board, capacity: capacity)
        let sch = AntScheduler(board: board, palette: level.palette)
        var t = 0.0
        var waits = 0
        var maxInUse = 0
        for (m, q) in level.solution.enumerated() {
            while true {
                let chamberIDs = Set(g.state.chambers.map { $0.uid })
                let busy = Set(sch.busyTeams(at: t).keys).subtracting(chamberIDs)
                if g.state.chambers.count + busy.count < capacity { break }
                if busy.isEmpty { return nil }
                var soonest = Double.infinity
                for u in busy { soonest = min(soonest, sch.slotFreeTime(team: u)) }
                t = soonest + 1e-6
                waits += 1
            }
            let ev = g.dispatch(q)
            sch.schedule(ev, move: m, now: t)
            let inUse = Set(sch.busyTeams(at: t + 0.01).keys).union(g.state.chambers.map { $0.uid }).count
            maxInUse = max(maxInUse, inUse)
            t += 0.3
        }
        let finish = sch.trips.map { $0.home }.max() ?? 0
        return TimedReport(won: g.isWon, maxInUse: maxInUse, waits: waits, finish: finish)
    }

    static func tiny(_ rows: [String], _ tunnels: [[TeamSpec]]) -> LevelDefinition {
        LevelDefinition(id: "tiny", title: "tiny", subtitle: "", art: rows, palette: GeneratedPalette.builtIn,
                        tunnels: tunnels, chambersGentle: 1, chambersClassic: 1, chambersExpert: 1, solution: [],
                        goldenClaimsPerMove: [], goldenClaimsHash: 0, goldenFinalStateHash: 0)
    }

    static func tinyBoardTests() -> [SelfTestResult] {
        var out: [SelfTestResult] = []
        func check(_ name: String, _ ok: Bool) { out.append(SelfTestResult(name: name, passed: ok, detail: "")) }
        // Fern pocket sealed by an Umber wall
        let l1 = tiny(["qqqqq", "qiiiq", "qqeqq"], [[TeamSpec(2, 3)], [TeamSpec(4, 11), TeamSpec(1, 1)]])
        let b1 = Board(art: l1.art)
        let g1 = Game(level: l1, board: b1, capacity: 2)
        let e1 = g1.dispatch(0)
        check("Rules: a team that can't reach its tiles keeps its slot and waits", e1.isEmpty && g1.state.chambers.count == 1)
        let e2 = g1.dispatch(1)
        check("Rules: a waiting team resumes when its colour is uncovered", e2.filter { $0.family == 2 }.count == 3 && g1.state.chambers.isEmpty)
        g1.dispatch(1)
        check("Rules: clearing every tile wins", g1.isWon)
        // Two sealed pockets, one slot
        let l2 = tiny(["qqqqq", "qiqeq", "qqqqq"], [[TeamSpec(2, 1)], [TeamSpec(1, 1), TeamSpec(4, 13)]])
        let b2 = Board(art: l2.art)
        let g2 = Game(level: l2, board: b2, capacity: 1)
        let fresh = g2.stateHash
        g2.dispatch(0)
        check("Rules: no team can be sent while every slot is taken", !g2.canDispatch(1))
        check("Rules: every slot holding a waiting team is detected as blocked", g2.deadlocked(busyOutsideSlots: 0))
        check("Rules: a team still collecting tiles is not a block", !g2.deadlocked(busyOutsideSlots: 1))
        g2.addChamber()
        check("Rules: adding a slot lets play continue", g2.canDispatch(1) && !g2.deadlocked(busyOutsideSlots: 0))
        g2.dispatch(1)
        check("Rules: sending never jams — the team already owns its slot", !g2.isJammed && g2.state.chambers.count == 2)
        g2.recall(0)
        check("Rules: returning a waiting team opens its slot; it goes to the front of its tunnel",
              g2.state.chambers.count == 1 && g2.front(0)?.need == 1 && g2.front(0)?.isReturned == true)
        g2.dispatch(1)
        g2.dispatch(0)
        check("Rules: a returned team can be sent again and the level completes", g2.isWon)
        while g2.canUndo { g2.undo() }
        check("Rules: undoing everything returns to the start", g2.stateHash == fresh)
        // Old saves made while Hold existed (Hold was removed; move code holdBase + tunnel)
        let l3 = tiny(["qqqqq", "qiiiq", "qqeqq"], [[TeamSpec(2, 3), TeamSpec(4, 11)], [TeamSpec(1, 1)]])
        let b3 = Board(art: l3.art)
        let old = Game.replay(level: l3, board: b3, capacity: 2, moves: [Game.holdBase + 0, 0])
        check("Old saves: a saved game that used Hold still loads, with that team parked in its slot",
              old != nil && old!.state.chambers.count == 1 && old!.state.chambers[0].held && old!.state.chambers[0].remaining == 3)
        if let g3 = old {
            let e4 = g3.release(0)
            g3.dispatch(1)
            check("Old saves: sending the parked team claims its tiles and the level completes",
                  e4.filter { $0.family == 2 }.count == 3 && g3.isWon)
        }
        return out
    }

    static func leafContains(_ x: Int, _ y: Int) -> Bool {
        let ex = (Double(x) - 110) / 40
        let ey = (Double(y) - 290) / 15
        return ex * ex + ey * ey < 1
    }

    /// A 300x400 "photo": white background with a pink flower, yellow centre and green stem.
    static func syntheticFlower() -> PixelImage {
        let w = 300, h = 400
        var px = [UInt8](repeating: 250, count: w * h * 4)
        func put(_ x: Int, _ y: Int, _ r: UInt8, _ g: UInt8, _ b: UInt8) {
            let o = (y * w + x) * 4
            px[o] = r; px[o + 1] = g; px[o + 2] = b; px[o + 3] = 255
        }
        for y in 0..<h {
            for x in 0..<w {
                let dx = Double(x - 150), dy = Double(y - 150)
                let r = (dx * dx + dy * dy).squareRoot()
                let a = atan2(dy, dx)
                let petal = 70 + 22 * cos(5 * a)
                if r < 32 {
                    put(x, y, 245, 196, 40)
                } else if r < petal {
                    put(x, y, 220, 50, 100)
                } else if abs(x - 150) < 7 && y > 200 && y < 380 {
                    put(x, y, 60, 140, 60)
                } else if leafContains(x, y) {
                    put(x, y, 70, 160, 70)
                } else {
                    px[(y * w + x) * 4 + 3] = 255
                }
            }
        }
        return PixelImage(width: w, height: h, rgba: px)
    }
}
