import Foundation

/// A team that has left its tunnel. `uid` = tunnel * 1000 + position in that tunnel.
struct Team: Equatable {
    var uid: Int
    var family: Int
    var quota: Int
    var remaining: Int
    /// Parked in a chamber with Hold. Hold was removed from the game; this only appears when a
    /// save from the earlier version is restored. Does not claim tiles until released.
    var held: Bool = false
    var tunnel: Int { uid / 1000 }
}

/// One tile claimed by one ant: the path runs from the hill hole to the open "stand" cell
/// beside the tile. Every cell on the path was open when the claim was made.
struct Claim {
    let team: Int
    let family: Int
    let tile: Int32
    let path: [Int32]
}

struct GameState: Equatable {
    var open: [Bool]
    var heads: [Int]
    var chambers: [Team]
    var capacity: Int
    /// Chambers added by the player as a recovery aid.
    var added: Int
    var jammed: Team?
    var cleared: Int
    /// Teams sent back out of a chamber; they wait at the front of their tunnel (last = front).
    var returned: [[Team]]
}

/// What sits at the front of a tunnel.
struct FrontTeam: Equatable {
    let family: Int
    let need: Int
    let uid: Int
    let isReturned: Bool
}

/// Outcome of a scouting preview (what a team would do if sent now).
struct ScoutReport {
    let tunnel: Int
    let family: Int
    let quota: Int
    let ownTiles: [Int32]
    let fits: Bool
    let wouldJam: Bool
    let totalClaims: Int
}

/// Deterministic rules engine. Mirrors Tools/engine.py line for line; the golden hashes in
/// LevelData.swift let the in-app self-test confirm both implementations agree.
final class Game {
    /// Move codes stored in the move list (and in saves).
    static let addChamberMove = 100
    static let recallJammedMove = 199
    static let recallBase = 200     // + chamber index: send a chamber team back to its tunnel
    /// Legacy (Hold was removed): kept so saves from the earlier version still replay.
    static let holdBase = 300       // + tunnel index: park the front team in a free chamber
    static let releaseBase = 400    // + chamber index: send a held team now

    /// Assists (counted separately): add a chamber, send a team back.
    static func isAssist(_ code: Int) -> Bool { code >= addChamberMove && code < holdBase }

    let board: Board
    let level: LevelDefinition
    let tunnels: [[TeamSpec]]
    private(set) var state: GameState
    private(set) var history: [GameState] = []
    private(set) var moves: [Int] = []
    private(set) var moveClaims: [[Claim]] = []

    init(level: LevelDefinition, board: Board, capacity: Int) {
        self.level = level
        self.board = board
        self.tunnels = level.tunnels
        self.state = GameState(open: board.initialOpen(),
                               heads: [Int](repeating: 0, count: level.tunnels.count),
                               chambers: [], capacity: capacity, added: 0,
                               jammed: nil, cleared: 0,
                               returned: [[Team]](repeating: [], count: level.tunnels.count))
    }

    // MARK: - Core rules

    /// One claiming pass for a single team (nearest-first BFS from the hole).
    static func claimRun(board: Board, state st: inout GameState, family: Int, limit: Int, teamUID: Int) -> [Claim] {
        if limit <= 0 { return [] }
        let n = board.count
        let fam = board.family
        let nb = board.neighbours
        var dist = [Int32](repeating: -1, count: n)
        var parent = [Int32](repeating: -1, count: n)
        var cand = [Bool](repeating: false, count: n)
        var claims: [Claim] = []
        dist[board.hole] = 0
        var buckets: [[Int32]] = [[Int32(board.hole)]]
        var d = 0
        var done = false
        while d < buckets.count && !done {
            let cur = buckets[d]
            for e32 in cur {
                let e = Int(e32)
                if !st.open[e] {
                    if claims.count >= limit { done = true; break }
                    st.open[e] = true
                    st.cleared += 1
                    dist[e] = Int32(d)
                    var path: [Int32] = []
                    var p = parent[e]
                    while p != -1 {
                        path.append(p)
                        p = parent[Int(p)]
                    }
                    path.reverse()
                    claims.append(Claim(team: teamUID, family: family, tile: e32, path: path))
                    if claims.count >= limit { done = true; break }
                }
                let base = e * 4
                for k in 0..<4 {
                    let n32 = nb[base + k]
                    if n32 < 0 { continue }
                    let m = Int(n32)
                    if st.open[m] {
                        if dist[m] < 0 {
                            dist[m] = Int32(d + 1)
                            parent[m] = e32
                            if buckets.count == d + 1 { buckets.append([]) }
                            buckets[d + 1].append(n32)
                        }
                    } else if Int(fam[m]) == family && !cand[m] {
                        cand[m] = true
                        parent[m] = e32
                        if buckets.count == d + 1 { buckets.append([]) }
                        buckets[d + 1].append(n32)
                    }
                }
            }
            d += 1
        }
        return claims
    }

    /// Passes over [incoming] + chambers until nobody can claim; then park or jam the incoming team.
    static func resolve(board: Board, state st: inout GameState, incoming: Team?) -> [Claim] {
        var events: [Claim] = []
        var inc = incoming
        while true {
            var progress = false
            if var t = inc, t.remaining > 0 {
                let c = claimRun(board: board, state: &st, family: t.family, limit: t.remaining, teamUID: t.uid)
                if !c.isEmpty {
                    progress = true
                    t.remaining -= c.count
                    events.append(contentsOf: c)
                    inc = t
                }
            }
            for idx in 0..<st.chambers.count {
                var t = st.chambers[idx]
                if t.remaining == 0 || t.held { continue }
                let c = claimRun(board: board, state: &st, family: t.family, limit: t.remaining, teamUID: t.uid)
                if !c.isEmpty {
                    progress = true
                    t.remaining -= c.count
                    events.append(contentsOf: c)
                    st.chambers[idx] = t
                }
            }
            st.chambers.removeAll { $0.remaining == 0 }
            if !progress { break }
        }
        if let t = inc, t.remaining > 0 {
            if st.chambers.count < st.capacity {
                st.chambers.append(t)
            } else {
                st.jammed = t
            }
        }
        return events
    }

    static func front(tunnels: [[TeamSpec]], state: GameState, tunnel q: Int) -> FrontTeam? {
        if let t = state.returned[q].last {
            return FrontTeam(family: t.family, need: t.remaining, uid: t.uid, isReturned: true)
        }
        let h = state.heads[q]
        guard h < tunnels[q].count else { return nil }
        let s = tunnels[q][h]
        return FrontTeam(family: s.family, need: s.quota, uid: q * 1000 + h, isReturned: false)
    }

    static func applyDispatch(board: Board, tunnels: [[TeamSpec]], state st: inout GameState, tunnel q: Int) -> [Claim] {
        let incoming: Team
        if let t = st.returned[q].popLast() {
            incoming = t
        } else {
            let spec = tunnels[q][st.heads[q]]
            incoming = Team(uid: q * 1000 + st.heads[q], family: spec.family, quota: spec.quota, remaining: spec.quota)
            st.heads[q] += 1
        }
        return resolve(board: board, state: &st, incoming: incoming)
    }

    // MARK: - Queries

    func front(_ q: Int) -> FrontTeam? { Game.front(tunnels: tunnels, state: state, tunnel: q) }

    /// The next teams behind the front one (returned teams first, then the tunnel's own queue).
    func upcoming(_ q: Int, count: Int) -> [TeamSpec] {
        var out: [TeamSpec] = []
        let ret = state.returned[q]
        if ret.count > 1 {
            for t in ret.dropLast().reversed() { out.append(TeamSpec(t.family, t.remaining)) }
        }
        var h = state.heads[q] + (ret.isEmpty ? 1 : 0)
        while out.count < count && h < tunnels[q].count {
            out.append(tunnels[q][h])
            h += 1
        }
        return Array(out.prefix(count))
    }

    func remainingInTunnel(_ q: Int) -> Int { tunnels[q].count - state.heads[q] + state.returned[q].count }

    var isJammed: Bool { state.jammed != nil }
    var isWon: Bool { state.cleared == board.tileCount }
    var canUndo: Bool { !history.isEmpty }

    /// Slot rule (logical part): a team can only be sent into an open slot. Waiting and held teams
    /// keep their slots. The app additionally counts teams whose ants are still collecting
    /// (GameController.occupiedSlots). Because a sent team already owns a slot, sending never blocks.
    func canDispatch(_ q: Int) -> Bool {
        state.jammed == nil && front(q) != nil && state.chambers.count < state.capacity
    }

    /// Every slot holds a waiting team (none held, none still collecting): nothing can move
    /// without undo, adding a slot or returning a team.
    func deadlocked(busyOutsideSlots busy: Int) -> Bool {
        if isWon || busy > 0 { return false }
        if state.chambers.contains(where: { $0.held }) { return false }
        let anyFront = (0..<tunnels.count).contains { front($0) != nil }
        return state.chambers.count >= state.capacity && (anyFront || !state.chambers.isEmpty)
    }

    // MARK: - Player actions

    @discardableResult
    func dispatch(_ q: Int) -> [Claim] {
        guard canDispatch(q) else { return [] }
        history.append(state)
        var st = state
        let ev = Game.applyDispatch(board: board, tunnels: tunnels, state: &st, tunnel: q)
        state = st
        record(q, ev)
        return ev
    }

    private func record(_ code: Int, _ claims: [Claim]) {
        moves.append(code)
        moveClaims.append(claims)
    }

    private static func unjam(_ st: inout GameState) {
        if let j = st.jammed, st.chambers.count < st.capacity {
            st.chambers.append(j)
            st.jammed = nil
        }
    }

    /// Recovery: open one more chamber (a jammed team moves straight in).
    func addChamber() {
        history.append(state)
        var st = state
        st.capacity += 1
        st.added += 1
        Game.unjam(&st)
        state = st
        record(Game.addChamberMove, [])
    }

    func canRecall(_ index: Int) -> Bool { index >= 0 && index < state.chambers.count }

    func canHold(_ q: Int) -> Bool {
        state.jammed == nil && front(q) != nil && state.chambers.count < state.capacity
    }

    /// Legacy: park the front team of tunnel `q` in a free chamber without sending it. The game no
    /// longer offers Hold; this only runs when an old save is replayed.
    func hold(_ q: Int) {
        guard canHold(q) else { return }
        history.append(state)
        var st = state
        var t: Team
        if let r = st.returned[q].popLast() {
            t = r
        } else {
            let spec = tunnels[q][st.heads[q]]
            t = Team(uid: q * 1000 + st.heads[q], family: spec.family, quota: spec.quota, remaining: spec.quota)
            st.heads[q] += 1
        }
        t.held = true
        st.chambers.append(t)
        state = st
        record(Game.holdBase + q, [])
    }

    func canRelease(_ index: Int) -> Bool {
        state.jammed == nil && index >= 0 && index < state.chambers.count && state.chambers[index].held
    }

    /// Send a held team out of chamber `index` in state `st`. Its chamber is freed first, so this never blocks.
    static func applyRelease(board: Board, state st: inout GameState, chamber index: Int) -> [Claim] {
        var t = st.chambers.remove(at: index)
        t.held = false
        return resolve(board: board, state: &st, incoming: t)
    }

    /// Send a held team now.
    @discardableResult
    func release(_ index: Int) -> [Claim] {
        guard canRelease(index) else { return [] }
        history.append(state)
        var st = state
        let ev = Game.applyRelease(board: board, state: &st, chamber: index)
        state = st
        record(Game.releaseBase + index, ev)
        return ev
    }

    /// Recovery: send a waiting team back to the front of its tunnel, freeing its chamber.
    /// It keeps the number of tiles it still needs.
    func recall(_ index: Int) {
        guard canRecall(index) else { return }
        history.append(state)
        var st = state
        var t = st.chambers.remove(at: index)
        t.held = false
        st.returned[t.tunnel].append(t)
        Game.unjam(&st)
        state = st
        record(Game.recallBase + index, [])
    }

    /// Recovery: the blocked team steps back into its tunnel instead of waiting.
    func recallJammed() {
        guard let j = state.jammed else { return }
        history.append(state)
        var st = state
        st.jammed = nil
        st.returned[j.tunnel].append(j)
        state = st
        record(Game.recallJammedMove, [])
    }

    /// Applies a stored move code; returns false if it is not legal here.
    @discardableResult
    func apply(move code: Int) -> Bool {
        if code == Game.addChamberMove {
            addChamber()
        } else if code == Game.recallJammedMove {
            guard state.jammed != nil else { return false }
            recallJammed()
        } else if code >= Game.releaseBase {
            guard canRelease(code - Game.releaseBase) else { return false }
            release(code - Game.releaseBase)
        } else if code >= Game.holdBase {
            guard code - Game.holdBase < tunnels.count, canHold(code - Game.holdBase) else { return false }
            hold(code - Game.holdBase)
        } else if code >= Game.recallBase {
            guard canRecall(code - Game.recallBase) else { return false }
            recall(code - Game.recallBase)
        } else {
            guard code >= 0, code < tunnels.count, canDispatch(code) else { return false }
            dispatch(code)
        }
        return true
    }

    /// Returns the claims of the undone move (so their tiles can be restored visually).
    @discardableResult
    func undo() -> [Claim]? {
        guard let prev = history.popLast() else { return nil }
        state = prev
        moves.removeLast()
        return moveClaims.popLast()
    }

    func scout(_ q: Int) -> ScoutReport? {
        guard let fr = front(q), state.jammed == nil else { return nil }
        var st = state
        let ev = Game.applyDispatch(board: board, tunnels: tunnels, state: &st, tunnel: q)
        let own = ev.filter { $0.team == fr.uid }.map { $0.tile }
        return ScoutReport(tunnel: q, family: fr.family, quota: fr.need, ownTiles: own,
                           fits: own.count == fr.need, wouldJam: st.jammed != nil, totalClaims: ev.count)
    }

    // MARK: - Hashes (shared with the Python reference model)

    static let fnvSeed: UInt64 = 0xCBF29CE484222325

    @inline(__always) static func mix(_ h: UInt64, _ v: Int) -> UInt64 {
        let x = h ^ UInt64(UInt32(truncatingIfNeeded: v))
        return x &* 0x100000001B3
    }

    static func stateHash(board: Board, state st: GameState) -> UInt64 {
        var h = fnvSeed
        for i in 0..<board.count where st.open[i] && board.family[i] >= 0 {
            h = mix(h, i)
        }
        for x in st.heads { h = mix(h, x) }
        for t in st.chambers {
            h = mix(h, t.uid)
            h = mix(h, t.remaining)
            h = mix(h, t.held ? 1 : 0)
        }
        for stack in st.returned {
            for t in stack {
                h = mix(h, t.uid)
                h = mix(h, t.remaining)
            }
        }
        h = mix(h, st.capacity)
        h = mix(h, st.jammed == nil ? 0 : 1)
        return h
    }

    var stateHash: UInt64 { Game.stateHash(board: board, state: state) }

    static func claimsHash(_ lists: [[Claim]]) -> UInt64 {
        var h = fnvSeed
        for list in lists {
            for c in list {
                h = mix(h, Int(c.tile))
                h = mix(h, c.path.count)
            }
        }
        return h
    }

    /// Rebuild a game from a saved move list. Returns nil if any move is no longer legal.
    static func replay(level: LevelDefinition, board: Board, capacity: Int, moves: [Int]) -> Game? {
        let g = Game(level: level, board: board, capacity: capacity)
        for m in moves {
            if !g.apply(move: m) { return nil }
        }
        return g
    }
}
