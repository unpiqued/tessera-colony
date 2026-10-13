import Foundation

/// Deterministic random numbers (same algorithm as SplitMix64 in Tools/photo.py).
struct SplitMix64 {
    private var s: UInt64
    init(seed: UInt64) { s = seed }

    mutating func next() -> UInt64 {
        s = s &+ 0x9E3779B97F4A7C15
        var z = s
        z = (z ^ (z >> 30)) &* 0xBF58476D1CE4E5B9
        z = (z ^ (z >> 27)) &* 0x94D049BB133111EB
        return z ^ (z >> 31)
    }

    /// Uniform in [0, 1).
    mutating func unit() -> Double { Double(next() >> 11) / Double(UInt64(1) << 53) }

    mutating func int(_ n: Int) -> Int { n <= 1 ? 0 : Int(next() % UInt64(n)) }

    mutating func weighted(_ weights: [Double]) -> Int {
        let total = weights.reduce(0, +)
        if total <= 0 { return int(weights.count) }
        var r = unit() * total
        for (i, w) in weights.enumerated() {
            r -= w
            if r < 0 { return i }
        }
        return weights.count - 1
    }
}

/// Builds tunnel queues for any mosaic by simulating a "designer" who invents each team while
/// playing; the designer's own play is therefore a guaranteed solution. Swift port of
/// design_sequence / deal in Tools/generate_levels.py (used on-device for photo mosaics).
enum LevelGenerator {
    static let ladder = [20, 24, 30, 36, 42, 48, 56, 64, 72, 84, 96, 110]
    static let maxTeam = 128

    struct Plan {
        let tunnels: [[TeamSpec]]
        let solution: [Int]
        let maxChambersUsed: Int
    }

    static func designSequence(board: Board, rng: inout SplitMix64, maxWait: Int, minTeam: Int, pWait: Double) -> [TeamSpec]? {
        var st = GameState(open: board.initialOpen(), heads: [0], chambers: [], capacity: maxWait, added: 0,
                           jammed: nil, cleared: 0, returned: [[]])
        var unassigned = board.familyTotals
        var seq: [TeamSpec] = []
        var lastFam = -1
        var guardCount = 0
        while unassigned.reduce(0, +) > 0 {
            guardCount += 1
            if guardCount > 5000 { return nil }
            var reach = [Int](repeating: -1, count: unassigned.count)
            var fams: [Int] = []
            for f in 0..<unassigned.count where unassigned[f] > 0 {
                var s2 = st
                reach[f] = Game.claimRun(board: board, state: &s2, family: f, limit: unassigned[f], teamUID: -1).count
                fams.append(f)
            }
            let fitting = fams.filter { reach[$0] >= min(minTeam, unassigned[$0]) }
            var choice: (Int, Int)? = nil
            if st.chambers.count < maxWait && rng.unit() < pWait {
                let waitFams = fams.filter { f in
                    reach[f] < unassigned[f] && unassigned[f] >= minTeam && reach[f] + 12 <= maxTeam
                        && !st.chambers.contains(where: { $0.family == f })
                }
                if !waitFams.isEmpty {
                    let f = waitFams[rng.int(waitFams.count)]
                    let extra = [12, 18, 24, 30, 40][rng.int(5)]
                    var q = min(unassigned[f], max(minTeam, reach[f] + extra), maxTeam)
                    if unassigned[f] - q < minTeam && unassigned[f] <= maxTeam { q = unassigned[f] }
                    choice = (f, q)
                }
            }
            if choice == nil {
                if fitting.isEmpty {
                    var f = fams[0]
                    for g in fams where reach[g] > reach[f] { f = g }
                    let q = unassigned[f] < 2 * minTeam ? unassigned[f] : min(maxTeam, max(minTeam, reach[f]))
                    choice = (f, q)
                } else {
                    let weights = fitting.map { pow(Double(max(1, reach[$0])), 0.6) * ($0 == lastFam ? 0.35 : 1.0) }
                    let f = fitting[rng.weighted(weights)]
                    let cap = min(reach[f], unassigned[f])
                    let options = ladder.filter { $0 <= cap }
                    var q = cap
                    if !options.isEmpty {
                        let top = Array(options.suffix(6))
                        q = min(top[rng.int(top.count)], cap)
                    }
                    if unassigned[f] - q < minTeam && unassigned[f] <= maxTeam { q = unassigned[f] }
                    choice = (f, q)
                }
            }
            guard let picked = choice, picked.1 > 0 else { return nil }
            var f = picked.0
            var q = picked.1
            var trial = st
            _ = Game.resolve(board: board, state: &trial, incoming: Team(uid: seq.count, family: f, quota: q, remaining: q))
            if trial.jammed != nil {
                // fall back to a team that certainly completes right now
                let pool = fitting.isEmpty ? fams.filter { reach[$0] > 0 } : fitting
                guard !pool.isEmpty else { return nil }
                f = pool[0]
                for g in pool where reach[g] > reach[f] { f = g }
                q = min(reach[f], unassigned[f])
                trial = st
                _ = Game.resolve(board: board, state: &trial, incoming: Team(uid: seq.count, family: f, quota: q, remaining: q))
                if trial.jammed != nil { return nil }
            }
            st = trial
            seq.append(TeamSpec(f, q))
            unassigned[f] -= q
            lastFam = f
        }
        guard st.cleared == board.tileCount, st.chambers.isEmpty else { return nil }
        return seq
    }

    static func deal(_ seq: [TeamSpec], tunnelCount n: Int, rng: inout SplitMix64) -> ([[TeamSpec]], [Int]) {
        var tunnels = [[TeamSpec]](repeating: [], count: n)
        var solution: [Int] = []
        for spec in seq {
            let lens = tunnels.map { $0.count }
            let lo = lens.min() ?? 0
            let cands = (0..<n).filter { lens[$0] <= lo + 2 }
            let i = cands[rng.int(cands.count)]
            tunnels[i].append(spec)
            solution.append(i)
        }
        return (tunnels, solution)
    }

    /// Replays a solution; returns the most chambers it ever needed, or nil if it fails.
    static func verify(board: Board, tunnels: [[TeamSpec]], solution: [Int], capacity: Int) -> Int? {
        var st = GameState(open: board.initialOpen(), heads: [Int](repeating: 0, count: tunnels.count), chambers: [],
                           capacity: capacity, added: 0, jammed: nil, cleared: 0,
                           returned: [[Team]](repeating: [], count: tunnels.count))
        var maxUsed = 0
        for q in solution {
            guard Game.front(tunnels: tunnels, state: st, tunnel: q) != nil else { return nil }
            _ = Game.applyDispatch(board: board, tunnels: tunnels, state: &st, tunnel: q)
            if st.jammed != nil { return nil }
            maxUsed = max(maxUsed, st.chambers.count)
        }
        return st.cleared == board.tileCount ? maxUsed : nil
    }

    static func generate(board: Board, seed: UInt64) -> Plan? {
        let small = board.tileCount < 600
        let tunnelCount = small ? 2 : 3
        let maxWait = small ? 1 : 2
        let minTeam = board.tileCount < 2000 ? 10 : 20
        for attempt in 0..<8 {
            var rng = SplitMix64(seed: seed &+ UInt64(attempt) &* 7919)
            guard let seq = designSequence(board: board, rng: &rng, maxWait: maxWait, minTeam: minTeam, pWait: 0.18) else { continue }
            let (tunnels, solution) = deal(seq, tunnelCount: tunnelCount, rng: &rng)
            if let used = verify(board: board, tunnels: tunnels, solution: solution, capacity: maxWait) {
                return Plan(tunnels: tunnels, solution: solution, maxChambersUsed: used)
            }
        }
        return nil
    }
}
