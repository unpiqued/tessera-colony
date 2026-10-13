import Foundation

// Two-player versus mode: the rules. Mirror of Tools/versus.py (tested there claim by claim for
// every combination of options).

enum VersusLayout: String, CaseIterable, Codable, Identifiable {
    /// Split screen: each player has their own copy of the mosaic.
    case race
    /// One mosaic, two hills (left and right): both players get the same tunnels and race for the same tiles.
    case shared
    var id: String { rawValue }
    var title: String { self == .race ? "Race" : "Shared board" }
    var blurb: String {
        switch self {
        case .race: return "Split screen. Each of you clears your own copy of the mosaic; the first to finish gets a bonus and ends the match."
        case .shared: return "One mosaic, two ant hills. You both have the same tunnels and compete for the same tiles; a team whose colour runs out keeps what it got."
        }
    }
}

enum VersusPicking: String, CaseIterable, Codable, Identifiable {
    case front, reach3
    var id: String { rawValue }
    var title: String { self == .front ? "Front team only" : "Reach 3" }
    var blurb: String {
        self == .front ? "Only the team at the front of a tunnel can be launched."
            : "Launch any of the first three teams in a tunnel; jumping the queue costs 3 points per place."
    }
}

enum VersusColourRule: String, CaseIterable, Codable, Identifiable {
    case any, alternate
    var id: String { rawValue }
    var title: String { self == .any ? "Any colour" : "No colour twice in a row" }
    var blurb: String {
        self == .any ? "No colour limit: launch the same colour from every tunnel and fill all your slots with it if you like."
            : "Optional extra rule: you can't launch the same colour as your previous launch (unless nothing else is left to launch)."
    }
}

enum VersusSlotScoring: String, CaseIterable, Codable, Identifiable {
    case upkeep, flat
    var id: String { rawValue }
    var title: String { self == .upkeep ? "Slot upkeep" : "Flat slot cost" }
    var blurb: String {
        self == .upkeep ? "Every busy slot beyond the first costs 0.25 points per second (game time). Adding a slot costs 25."
            : "Busy slots are free; adding a slot costs 25."
    }
}

struct VersusRules: Codable, Equatable {
    var layout: VersusLayout = .race
    var picking: VersusPicking = .reach3
    /// Any colour by default — the colour rule is an optional extra.
    var colour: VersusColourRule = .any
    var scoring: VersusSlotScoring = .upkeep
    var difficulty: Difficulty = .classic

    static let addSlotPenalty = 25.0
    static let returnPenalty = 10.0
    static let skipPenalty = 3.0
    static let upkeepPerSecond = 0.25
    static let finishBonusShare = 0.15
    static let reach = 3
    /// Team uid = player * playerBase + tunnel * 1000 + position in the original tunnel.
    static let playerBase = 100_000

    var reachDepth: Int { picking == .reach3 ? VersusRules.reach : 1 }
}

struct VTeam: Equatable {
    let uid: Int
    let player: Int
    let family: Int
    let quota: Int
    var remaining: Int
    var tunnel: Int { (uid % VersusRules.playerBase) / 1000 }
}

/// One mosaic in a match (race: one per player; shared: one for both).
final class VersusBoard {
    let board: Board
    private(set) var open: [Bool]
    /// Which player claimed each tile (-1 = nobody yet).
    private(set) var owner: [Int8]
    /// Unclaimed tiles per colour family.
    private(set) var left: [Int]
    /// Hill hole per player on this board.
    let holes: [Int: Int]
    /// Teams waiting in slots on this board (both players on a shared board), in arrival order.
    private(set) var chambers: [VTeam] = []
    private(set) var claimed: [Int] = [0, 0]

    init(board: Board, holes: [Int: Int]) {
        self.board = board
        self.open = board.initialOpen()
        self.owner = [Int8](repeating: -1, count: board.count)
        var l = [Int](repeating: 0, count: 8)
        for f in board.family where f >= 0 { l[Int(f)] += 1 }
        self.left = l
        self.holes = holes
    }

    var isCleared: Bool { left.reduce(0, +) == 0 }

    /// Nearest-first claiming from the team's hill (Game.claimRun with the hole as a parameter).
    private func claimRun(_ t: inout VTeam) -> [Claim] {
        let limit = t.remaining
        if limit <= 0 { return [] }
        let hole = holes[t.player] ?? board.hole
        let n = board.count
        let fam = board.family
        let nb = board.neighbours
        var dist = [Int32](repeating: -1, count: n)
        var parent = [Int32](repeating: -1, count: n)
        var cand = [Bool](repeating: false, count: n)
        var claims: [Claim] = []
        dist[hole] = 0
        var buckets: [[Int32]] = [[Int32(hole)]]
        var d = 0
        var done = false
        while d < buckets.count && !done {
            let cur = buckets[d]
            for e32 in cur {
                let e = Int(e32)
                if !open[e] {
                    if claims.count >= limit { done = true; break }
                    open[e] = true
                    dist[e] = Int32(d)
                    var path: [Int32] = []
                    var p = parent[e]
                    while p != -1 {
                        path.append(p)
                        p = parent[Int(p)]
                    }
                    path.reverse()
                    claims.append(Claim(team: t.uid, family: t.family, tile: e32, path: path))
                    owner[e] = Int8(t.player)
                    left[t.family] -= 1
                    claimed[t.player] += 1
                    if claims.count >= limit { done = true; break }
                }
                let base = e * 4
                for k in 0..<4 {
                    let n32 = nb[base + k]
                    if n32 < 0 { continue }
                    let m = Int(n32)
                    if open[m] {
                        if dist[m] < 0 {
                            dist[m] = Int32(d + 1)
                            parent[m] = e32
                            if buckets.count == d + 1 { buckets.append([]) }
                            buckets[d + 1].append(n32)
                        }
                    } else if Int(fam[m]) == t.family && !cand[m] {
                        cand[m] = true
                        parent[m] = e32
                        if buckets.count == d + 1 { buckets.append([]) }
                        buckets[d + 1].append(n32)
                    }
                }
            }
            d += 1
        }
        t.remaining -= claims.count
        return claims
    }

    /// Passes over [incoming] + waiting teams until nobody can claim; an unfinished incoming team waits.
    func resolve(incoming: VTeam?) -> [Claim] {
        var events: [Claim] = []
        var inc = incoming
        while true {
            var progress = false
            if var t = inc, t.remaining > 0 {
                let c = claimRun(&t)
                if !c.isEmpty {
                    progress = true
                    events.append(contentsOf: c)
                }
                inc = t
            }
            for idx in 0..<chambers.count {
                var t = chambers[idx]
                if t.remaining == 0 { continue }
                let c = claimRun(&t)
                if !c.isEmpty {
                    progress = true
                    events.append(contentsOf: c)
                }
                chambers[idx] = t
            }
            chambers.removeAll { $0.remaining == 0 }
            if !progress { break }
        }
        if let t = inc, t.remaining > 0 { chambers.append(t) }
        return events
    }

    /// Waiting teams whose colour has no tiles left retire with what they got (shared board).
    @discardableResult
    func retireExhausted() -> [VTeam] {
        let gone = chambers.filter { left[$0.family] == 0 }
        if !gone.isEmpty { chambers.removeAll { left[$0.family] == 0 } }
        return gone
    }

    func removeChamber(uid: Int) -> VTeam? {
        guard let i = chambers.firstIndex(where: { $0.uid == uid }) else { return nil }
        return chambers.remove(at: i)
    }
}

final class VersusPlayer {
    let index: Int
    /// Tunnel queues, front first.
    fileprivate(set) var queues: [[VTeam]]
    fileprivate(set) var capacity: Int
    fileprivate(set) var added = 0
    fileprivate(set) var returns = 0
    fileprivate(set) var skips = 0
    fileprivate(set) var launches = 0
    fileprivate(set) var lastFamily: Int?
    /// Slot upkeep accrued so far (points), added by the controller in game time.
    var upkeep = 0.0

    init(index: Int, tunnels: [[TeamSpec]], capacity: Int) {
        self.index = index
        self.capacity = capacity
        var qs: [[VTeam]] = []
        for (q, t) in tunnels.enumerated() {
            var row: [VTeam] = []
            for (i, spec) in t.enumerated() {
                row.append(VTeam(uid: index * VersusRules.playerBase + q * 1000 + i, player: index,
                                 family: spec.family, quota: spec.quota, remaining: spec.quota))
            }
            qs.append(row)
        }
        self.queues = qs
    }
}

final class VersusMatch {
    let rules: VersusRules
    let level: LevelDefinition
    let boards: [VersusBoard]
    let players: [VersusPlayer]
    let tileCount: Int

    init(level: LevelDefinition, rules: VersusRules) {
        self.rules = rules
        self.level = level
        let cap = level.chambers(for: rules.difficulty)
        switch rules.layout {
        case .race:
            let b0 = Board(art: level.art), b1 = Board(art: level.art)
            boards = [VersusBoard(board: b0, holes: [0: b0.hole]), VersusBoard(board: b1, holes: [1: b1.hole])]
        case .shared:
            let b = Board(art: level.art)
            let h = VersusMatch.sharedHoles(b)
            boards = [VersusBoard(board: b, holes: [0: h[0], 1: h[1]])]
        }
        players = [VersusPlayer(index: 0, tunnels: level.tunnels, capacity: cap),
                   VersusPlayer(index: 1, tunnels: level.tunnels, capacity: cap)]
        tileCount = boards[0].board.tileCount
    }

    /// Two hills on a shared board: a quarter and three quarters of the way across the bottom margin.
    static func sharedHoles(_ b: Board) -> [Int] {
        let row = b.rows - 3
        return [row * b.cols + b.cols / 4, row * b.cols + (3 * b.cols) / 4]
    }

    func boardIndex(_ p: Int) -> Int { rules.layout == .race ? p : 0 }
    func board(of p: Int) -> VersusBoard { boards[boardIndex(p)] }
    func waiting(_ p: Int) -> [VTeam] { board(of: p).chambers.filter { $0.player == p } }
    func tiles(_ p: Int) -> Int { board(of: p).claimed[p] }

    /// Teams within reach: (tunnel, depth, team).
    func candidates(_ p: Int) -> [(tunnel: Int, depth: Int, team: VTeam)] {
        var out: [(tunnel: Int, depth: Int, team: VTeam)] = []
        for (q, queue) in players[p].queues.enumerated() {
            for d in 0..<min(rules.reachDepth, queue.count) { out.append((tunnel: q, depth: d, team: queue[d])) }
        }
        return out
    }

    /// Nil if the launch is allowed, otherwise the reason (the real-time slot check is the controller's).
    func refusal(_ p: Int, tunnel q: Int, depth d: Int) -> String? {
        let pl = players[p]
        guard q < pl.queues.count, d < pl.queues[q].count else { return "No team there." }
        if d >= rules.reachDepth { return "Out of reach." }
        if waiting(p).count >= pl.capacity { return "Every slot holds a waiting team." }
        let t = pl.queues[q][d]
        if rules.colour == .alternate, let last = pl.lastFamily, t.family == last {
            if candidates(p).contains(where: { $0.team.family != last }) {
                return "Not the same colour twice in a row."
            }
        }
        return nil
    }

    func canLaunch(_ p: Int, tunnel q: Int, depth d: Int) -> Bool { refusal(p, tunnel: q, depth: d) == nil }

    @discardableResult
    func launch(_ p: Int, tunnel q: Int, depth d: Int) -> [Claim] {
        guard canLaunch(p, tunnel: q, depth: d) else { return [] }
        let pl = players[p]
        let team = pl.queues[q].remove(at: d)
        pl.skips += d
        pl.launches += 1
        pl.lastFamily = team.family
        let ev = board(of: p).resolve(incoming: team)
        afterAction()
        return ev
    }

    private func afterAction() {
        for b in boards { b.retireExhausted() }
        if rules.layout == .shared {
            let b = boards[0]
            for pl in players {
                pl.queues = pl.queues.map { queue in queue.filter { b.left[$0.family] > 0 } }
            }
        }
    }

    func addSlot(_ p: Int) {
        players[p].capacity += 1
        players[p].added += 1
    }

    /// Returns a waiting team to the front of its tunnel, opening its slot.
    func returnTeam(_ p: Int, uid: Int) {
        guard let t = board(of: p).removeChamber(uid: uid), t.player == p else { return }
        let pl = players[p]
        pl.queues[t.tunnel].insert(t, at: 0)
        pl.returns += 1
    }

    func penalties(_ p: Int) -> Double {
        let pl = players[p]
        var pen = Double(pl.added) * VersusRules.addSlotPenalty + Double(pl.returns) * VersusRules.returnPenalty
            + Double(pl.skips) * VersusRules.skipPenalty
        if rules.scoring == .upkeep { pen += pl.upkeep }
        return pen
    }

    /// Nobody can ever move again (shared board: no queued teams and nothing waiting).
    var isStalemate: Bool {
        (0..<2).allSatisfy { p in players[p].queues.allSatisfy { $0.isEmpty } && waiting(p).isEmpty }
    }
}
