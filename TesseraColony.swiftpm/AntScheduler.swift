import Foundation

/// A single ant's round trip: leave the hole, walk to the stand cell, lift the tile, walk home.
struct AntTrip {
    let id: Int
    let move: Int
    let team: Int
    let family: Int
    let tone: Int
    /// The exact colour of the tile this ant collects (its body is painted this colour).
    let color: UInt32
    let tile: Int32
    /// The route the ant walks, hole ... stand cell beside the tile (depends on the path style).
    let path: [Int32]
    let depart: Double
    let arrive: Double
    let pickupEnd: Double
    let home: Double
    /// About ±1: which outer lane the ant walks out in. Ants carrying a tile come home in the
    /// middle lane (army-ant traffic: laden ants hold the centre, unladen ants keep to the sides).
    let lane: Double
    /// Stops to sniff on the way out (sorted by position).
    var pauses: [TripPause] = []
    /// The style that produced `path`.
    var style: PathStyle = .direct
}

/// Turns claims into timed trips. Mirrors `Scheduler` in Tools/engine.py.
///
/// All times are *game* seconds. The speed slider only changes how fast game time runs, so
/// ants already on the board slow down or speed up smoothly (no jumps, no restarted trips).
///
/// Guarantees (verified by the Python tests and the in-app self-test):
///  * a tile stays on the board until its own ant arrives beside it (`liftTime`),
///  * no ant enters a cell until that cell's tile was lifted `pickup + margin` seconds earlier,
///  * the hole releases at most one ant per `slot`; one team at most one per `teamGap`, so teams
///    sent at nearly the same time interleave and genuinely work side by side.
final class AntScheduler {
    static let step = 1.0 / 4.0      // game-seconds per cell (1x = 4 cells ≈ 2.5 body lengths per second)
    static let slot = 0.18           // hole release slot
    static let teamGap = 0.36        // minimum spacing between two ants of the same team
    static let pickup = 0.9          // grab, lift and turn around
    static let margin = 0.2          // gap before another ant may walk through a lifted cell

    let board: Board
    let palette: LevelPalette
    /// Game time at which each tile is lifted (+inf = still on the board, -inf = ground).
    private(set) var liftTime: [Double]
    /// Game time at which each tile arrives in the nest (drives the gallery miniature).
    private(set) var homeTime: [Double]
    private var slots = Set<Int>()
    private var teamLast: [Int: Double] = [:]
    private(set) var trips: [AntTrip] = []
    private var nextID = 0
    /// Route style for ants launched from now on (ants already walking keep their route).
    var style: PathStyle = .direct
    /// Latest route of each team that uses the scout-trail style (the trail its next ant follows).
    private var teamTrail: [Int: [Int32]] = [:]
    /// Search buffers reused by every route this scheduler plans.
    private let scratch: PlannerScratch

    /// The concrete style for one new ant (resolves the random mixes).
    func styleFor(team: Int, tripID: Int) -> PathStyle {
        switch style {
        case .randomTeam:
            return PathStyle.teamMix[Int(hash32(team, 31) % UInt32(PathStyle.teamMix.count))]
        case .randomAnt:
            return PathStyle.antMix[Int(hash32(tripID, 37) % UInt32(PathStyle.antMix.count))]
        default:
            return style
        }
    }

    init(board: Board, palette: LevelPalette) {
        self.board = board
        self.palette = palette
        var lift = [Double](repeating: -Double.infinity, count: board.count)
        for i in 0..<board.count where board.family[i] >= 0 { lift[i] = Double.infinity }
        liftTime = lift
        homeTime = lift
        scratch = PlannerScratch(count: board.count)
    }

    func schedule(_ claims: [Claim], move: Int, now nowIn: Double) {
        let step = AntScheduler.step
        let now = nowIn.isFinite ? nowIn : 0
        // bounded planning (see PathPlanner): at most maxStyledPerSend styled ants, spread evenly
        let stride = max(1, (claims.count + PathPlanner.maxStyledPerSend - 1) / PathPlanner.maxStyledPerSend)
        var spent = 0
        for (i, c) in claims.enumerated() {
            let tid = nextID
            let chosen = i % stride == 0 ? styleFor(team: c.team, tripID: tid) : .direct
            let seed = Int(hash32(tid, 0x5EED))
            var trail: Set<Int32>? = nil
            if chosen == .scout, let tr = teamTrail[c.team] { trail = Set(tr) }
            let budget = PathPlanner.antBudget(directCount: c.path.count, remaining: PathPlanner.budgetPerSend - spent)
            let plan = PathPlanner.plan(board: board, liftTime: liftTime, claim: c, style: chosen, seed: seed,
                                        now: now, trail: trail, budget: budget, scratch: scratch)
            spent += plan.spent
            if plan.used == .scout { teamTrail[c.team] = plan.route }
            // defensive (crash report, 3 Oct): a route always has at least the hole; pauses are finite
            var route = plan.route
            if route.isEmpty { route = c.path.isEmpty ? [Int32(board.hole)] : c.path }
            let pauses = plan.pauses.filter { $0.at.isFinite && $0.duration.isFinite && $0.duration >= 0 }
            let l = route.count
            var earliest = now
            if let last = teamLast[c.team], last.isFinite, last + AntScheduler.teamGap > earliest {
                earliest = last + AntScheduler.teamGap
            }
            for (k, cell) in route.enumerated() {
                let ci = Int(cell)
                guard ci >= 0 && ci < liftTime.count else { continue }
                let req = liftTime[ci] + AntScheduler.pickup + AntScheduler.margin - (Double(k) - 0.5) * step
                if req > earliest { earliest = req }
            }
            // never convert inf/nan (or an absurd time) to Int
            if !earliest.isFinite || earliest > now + 1_000_000 { earliest = now }
            var s = Int((earliest / AntScheduler.slot - 1e-9).rounded(.up))
            while slots.contains(s) { s += 1 }
            slots.insert(s)
            let depart = Double(s) * AntScheduler.slot
            teamLast[c.team] = depart
            var pauseTotal = 0.0
            for p in pauses { pauseTotal += p.duration }
            let arrive = depart + Double(l) * step + pauseTotal
            let pickupEnd = arrive + AntScheduler.pickup
            let home = pickupEnd + Double(l) * step
            let t = Int(c.tile)
            liftTime[t] = arrive
            homeTime[t] = home
            // outbound ants alternate between the two outer lanes by release slot; carriers come
            // home in the middle lane
            let jitter = Double(hash32(tid, 977) & 0xFF) / 255.0 * 0.3 - 0.15
            let lane = (s % 2 == 0 ? 1.0 : -1.0) * (1.0 + jitter)
            let tone = Int(board.tone[t])
            trips.append(AntTrip(id: tid, move: move, team: c.team, family: c.family, tone: tone,
                                 color: palette.tone(c.family, tone), tile: c.tile, path: route,
                                 depart: depart, arrive: arrive, pickupEnd: pickupEnd, home: home, lane: lane,
                                 pauses: pauses, style: plan.used))
            nextID += 1
        }
    }

    /// Mark claims as already finished (used when restoring a saved game).
    func completeInstantly(_ claims: [Claim]) {
        for c in claims {
            liftTime[Int(c.tile)] = -1_000_000
            homeTime[Int(c.tile)] = -1_000_000
        }
    }

    /// Forget every trip of `move` and later; their tiles return to the board.
    func undo(claims: [Claim], fromMove move: Int) {
        for c in claims {
            liftTime[Int(c.tile)] = Double.infinity
            homeTime[Int(c.tile)] = Double.infinity
        }
        var keep: [AntTrip] = []
        keep.reserveCapacity(trips.count)
        var removedTeams = Set<Int>()
        for t in trips {
            if t.move >= move {
                slots.remove(Int((t.depart / AntScheduler.slot).rounded()))
                liftTime[Int(t.tile)] = Double.infinity
                homeTime[Int(t.tile)] = Double.infinity
                removedTeams.insert(t.team)
            } else {
                keep.append(t)
            }
        }
        trips = keep
        // recompute the release cadence of teams that lost trips; their trails start afresh
        for team in removedTeams {
            teamTrail[team] = nil
            let rest = trips.filter { $0.team == team }.map { $0.depart }
            teamLast[team] = rest.max()
        }
    }

    /// Teams with at least one tile not yet picked up at game time `t` — they still occupy a slot.
    func busyTeams(at t: Double) -> [Int: Int] {
        var out: [Int: Int] = [:]
        for trip in trips where trip.pickupEnd > t { out[trip.team, default: 0] += 1 }
        return out
    }

    /// Game time at which team `uid` will have picked up every tile scheduled so far.
    func slotFreeTime(team uid: Int) -> Double {
        var m = -Double.infinity
        for trip in trips where trip.team == uid { m = max(m, trip.pickupEnd) }
        return m
    }

    /// Drop trips that finished before `time`. Returns how many were removed.
    @discardableResult
    func prune(before time: Double) -> Int {
        let before = trips.count
        trips.removeAll { $0.home < time }
        return before - trips.count
    }

    var isBusy: Bool { !trips.isEmpty }
}

/// Where an ant is and what its body is doing at one instant (cell units).
struct AntPose {
    var x: Double
    var y: Double
    /// Direction of the body axis (radians).
    var heading: Double
    /// 0...1 while emerging from / diving into the hole.
    var scale: Double
    var carrying: Bool
    /// 0...1 while the tile travels from its cell into the ant's jaws.
    var liftProgress: Double
    /// Distance walked so far (cells) — drives the gait so steps match ground speed.
    var gaitDistance: Double
    /// True while the ant is travelling (legs cycle); false while it stands still.
    var moving: Bool
}

enum AntGeometry {
    /// Sideways distance between lanes (cells). Keeps every ant inside its path cells.
    static let laneWidth = 0.2
    /// Carriers walk home close to the middle: this share of their outbound lane, on the other side.
    static let carrierLane = -0.15

    /// Path position u (cells) `elapsed` seconds after departure, and how long the ant has been
    /// standing still if it is stopped to sniff.
    static func outbound(_ trip: AntTrip, elapsed: Double) -> (u: Double, paused: Double?) {
        let step = AntScheduler.step
        var e = elapsed
        for p in trip.pauses {
            let reach = p.at * step
            if e < reach { return (e / step, nil) }
            if e < reach + p.duration { return (p.at, e - reach) }
            e -= p.duration
        }
        return (e / step, nil)
    }
    /// Node k in cell units (cell centres); the last node is the approach point beside the tile.
    static func node(_ trip: AntTrip, _ kIn: Int, board: Board) -> (Double, Double) {
        let l = trip.path.count
        let t = Int(trip.tile)
        if l == 0 { return (Double(board.x(t)) + 0.5, Double(board.y(t)) + 0.5) }   // defensive: never index an empty route
        let k = max(0, kIn)
        if k < l {
            let c = Int(trip.path[k])
            return (Double(board.x(c)) + 0.5, Double(board.y(c)) + 0.5)
        }
        let s = Int(trip.path[l - 1])
        let sx = Double(board.x(s)) + 0.5, sy = Double(board.y(s)) + 0.5
        let tx = Double(board.x(t)) + 0.5, ty = Double(board.y(t)) + 0.5
        return (sx + (tx - sx) * 0.22, sy + (ty - sy) * 0.22)
    }

    /// Position and tangent at parameter u in [0, L] where L = path.count. Corners are rounded
    /// with quadratic curves that stay inside the corner cell.
    static func curve(_ trip: AntTrip, u uIn: Double, board: Board) -> (Double, Double, Double, Double) {
        let l = trip.path.count
        if l == 0 {
            let p = node(trip, 0, board: board)
            return (p.0, p.1, 1, 0)
        }
        let u = uIn.isFinite ? max(0, min(Double(l), uIn)) : Double(l)
        func mid(_ a: (Double, Double), _ b: (Double, Double)) -> (Double, Double) { ((a.0 + b.0) / 2, (a.1 + b.1) / 2) }
        if u <= 0.5 {
            let p0 = node(trip, 0, board: board)
            let p1 = node(trip, 1, board: board)
            let m = mid(p0, p1)
            let tau = u / 0.5
            return (p0.0 + (m.0 - p0.0) * tau, p0.1 + (m.1 - p0.1) * tau, p1.0 - p0.0, p1.1 - p0.1)
        }
        if u >= Double(l) - 0.5 {
            let a = node(trip, l - 1, board: board)
            let b = node(trip, l, board: board)
            let m = mid(a, b)
            let tau = (u - (Double(l) - 0.5)) / 0.5
            return (m.0 + (b.0 - m.0) * tau, m.1 + (b.1 - m.1) * tau, b.0 - a.0, b.1 - a.1)
        }
        let j = Int((u + 0.5).rounded(.down))
        let tau = u - (Double(j) - 0.5)
        let pPrev = node(trip, j - 1, board: board)
        let pj = node(trip, j, board: board)
        let pNext = node(trip, j + 1, board: board)
        let a = mid(pPrev, pj)
        let c = mid(pj, pNext)
        let o = 1 - tau
        let x = o * o * a.0 + 2 * o * tau * pj.0 + tau * tau * c.0
        let y = o * o * a.1 + 2 * o * tau * pj.1 + tau * tau * c.1
        let dx = 2 * o * (pj.0 - a.0) + 2 * tau * (c.0 - pj.0)
        let dy = 2 * o * (pj.1 - a.1) + 2 * tau * (c.1 - pj.1)
        return (x, y, dx, dy)
    }

    /// Length (cells) of the path from the hole to the approach point.
    static func length(_ trip: AntTrip) -> Double { Double(trip.path.count) - 0.78 }

    /// Where the ant is at game time `t`, or nil if it is underground.
    static func pose(_ trip: AntTrip, at t: Double, board: Board) -> AntPose? {
        guard t.isFinite, trip.depart.isFinite, trip.home.isFinite, !trip.path.isEmpty else { return nil }
        if t < trip.depart || t >= trip.home { return nil }
        let l = Double(trip.path.count)
        let step = AntScheduler.step
        let turnDistance = 0.9   // legs "walk" through the 180° turn at the tile
        if t < trip.arrive {
            let (uRaw, paused) = outbound(trip, elapsed: t - trip.depart)
            let u = min(uRaw, l)
            var (x, y, dx, dy) = curve(trip, u: u, board: board)
            let taper = min(1.0, 0.4 + 0.6 * min(u, l - u))
            applyLane(&x, &y, dx, dy, trip.lane * AntGeometry.laneWidth * taper)
            let scale = u < 1.0 ? 0.3 + 0.7 * u : 1.0
            var heading = atan2(dy, dx)
            if let p = paused {
                // sniffing: the head swings left and right while the ant stands still
                heading += 0.4 * sin(p / 0.8 * 2 * Double.pi) * smooth(p / 0.2)
            }
            return AntPose(x: x, y: y, heading: heading, scale: scale, carrying: false,
                           liftProgress: 0, gaitDistance: u, moving: paused == nil)
        }
        if t < trip.pickupEnd {
            let p = (t - trip.arrive) / AntScheduler.pickup
            var (x, y, dx, dy) = curve(trip, u: l, board: board)
            let face = atan2(dy, dx)
            let grab = 0.5
            let turn = p < grab ? 0.0 : smooth((p - grab) / (1 - grab))
            // slide from the outer outbound lane toward the middle (carrier) lane while turning round
            let outLane = trip.lane * (1 - turn) + trip.lane * AntGeometry.carrierLane * turn
            applyLane(&x, &y, dx, dy, outLane * AntGeometry.laneWidth * 0.4)
            let lift = min(1.0, p / grab)
            return AntPose(x: x, y: y, heading: face + Double.pi * turn, scale: 1, carrying: p >= grab,
                           liftProgress: smooth(lift), gaitDistance: l + turn * turnDistance, moving: p >= grab)
        }
        let u = l - (t - trip.pickupEnd) / step
        var (x, y, dx, dy) = curve(trip, u: u, board: board)
        let taper = min(1.0, 0.4 + 0.6 * min(max(0, u), l - u))
        applyLane(&x, &y, dx, dy, trip.lane * AntGeometry.carrierLane * AntGeometry.laneWidth * taper)
        let scale = u < 1.0 ? 0.3 + 0.7 * max(0, u) : 1.0
        return AntPose(x: x, y: y, heading: atan2(-dy, -dx), scale: scale, carrying: true,
                       liftProgress: 1, gaitDistance: l + turnDistance + (l - u), moving: true)
    }

    @inline(__always) static func smooth(_ x: Double) -> Double {
        let t = max(0, min(1, x))
        return t * t * (3 - 2 * t)
    }

    private static func applyLane(_ x: inout Double, _ y: inout Double, _ dx: Double, _ dy: Double, _ off: Double) {
        let len = (dx * dx + dy * dy).squareRoot()
        if len < 1e-6 { return }
        x += -dy / len * off
        y += dx / len * off
    }
}
