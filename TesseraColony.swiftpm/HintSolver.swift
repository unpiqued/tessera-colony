import Foundation

enum HintResult: Equatable {
    /// Play this move code (a tunnel index = send its front team; Game.releaseBase + i = send the
    /// held team in chamber i). `onPlan` = part of a known winning line.
    case move(code: Int, onPlan: Bool)
    /// No safe move found from here; undoing this many moves returns to the designer's plan.
    case undo(count: Int)
    case finished
}

/// Hint search. Mirrors `hint_full` / `evaluate_fronts` in Tools/engine.py.
enum HintSolver {
    struct FrontEval {
        /// Move code: tunnel index, or Game.releaseBase + chamber index.
        let tunnel: Int
        let fits: Bool
        let jams: Bool
        let own: Int
        let total: Int
        let after: GameState
    }

    static func evaluateFronts(board: Board, tunnels: [[TeamSpec]], state: GameState) -> [FrontEval] {
        var out: [FrontEval] = []
        for (i, t) in state.chambers.enumerated() where t.held {
            var s2 = state
            let ev = Game.applyRelease(board: board, state: &s2, chamber: i)
            var own = 0
            for c in ev where c.team == t.uid { own += 1 }
            out.append(FrontEval(tunnel: Game.releaseBase + i, fits: own == t.remaining, jams: false,
                                 own: own, total: ev.count, after: s2))
        }
        for q in 0..<tunnels.count where state.chambers.count < state.capacity {
            guard let fr = Game.front(tunnels: tunnels, state: state, tunnel: q) else { continue }
            var s2 = state
            let ev = Game.applyDispatch(board: board, tunnels: tunnels, state: &s2, tunnel: q)
            var own = 0
            for c in ev where c.team == fr.uid { own += 1 }
            out.append(FrontEval(tunnel: q, fits: own == fr.need, jams: s2.jammed != nil,
                                 own: own, total: ev.count, after: s2))
        }
        return out
    }

    private static func better(_ a: FrontEval, than b: FrontEval) -> Bool {
        if a.total != b.total { return a.total > b.total }
        return a.tunnel < b.tunnel
    }

    static func greedyChoice(board: Board, tunnels: [[TeamSpec]], state: GameState) -> FrontEval? {
        let opts = evaluateFronts(board: board, tunnels: tunnels, state: state)
        if opts.isEmpty { return nil }
        let fits = opts.filter { $0.fits }
        let pool: [FrontEval]
        if !fits.isEmpty {
            pool = fits
        } else {
            let safe = opts.filter { !$0.jams }
            pool = safe.isEmpty ? opts : safe
        }
        var best = pool[0]
        for o in pool.dropFirst() where better(o, than: best) { best = o }
        return best
    }

    static func rollout(board: Board, tunnels: [[TeamSpec]], state: GameState, maxMoves: Int = 400,
                        deadline: Date = .distantFuture) -> (won: Bool, cleared: Int) {
        var st = state
        var n = 0
        while st.jammed == nil && st.cleared < board.tileCount && n < maxMoves {
            if Date() > deadline { return (false, st.cleared) }
            guard let choice = greedyChoice(board: board, tunnels: tunnels, state: st) else { break }
            st = choice.after
            n += 1
        }
        return (st.jammed == nil && st.cleared == board.tileCount, st.cleared)
    }

    /// Best front by greedy rollouts. Returns (tunnel, rolloutWins).
    static func searchMove(board: Board, tunnels: [[TeamSpec]], state: GameState,
                           deadline: Date = .distantFuture) -> (Int, Bool)? {
        var bestScore: (Int, Int, Int, Int)? = nil
        var bestTunnel = -1
        for f in evaluateFronts(board: board, tunnels: tunnels, state: state) {
            let score: (Int, Int, Int, Int)
            if f.jams {
                score = (0, 0, 0, -f.tunnel)
            } else {
                let r = rollout(board: board, tunnels: tunnels, state: f.after, deadline: deadline)
                score = (r.won ? 1 : 0, f.fits ? 1 : 0, r.cleared, -f.tunnel)
            }
            if let b = bestScore {
                if score > b { bestScore = score; bestTunnel = f.tunnel }
            } else {
                bestScore = score
                bestTunnel = f.tunnel
            }
        }
        guard let b = bestScore else { return nil }
        return (bestTunnel, b.0 == 1)
    }

    static func hint(board: Board, tunnels: [[TeamSpec]], state: GameState, moves: [Int], solution: [Int]) -> HintResult {
        let k = moves.count
        if state.jammed == nil && k <= solution.count && Array(solution.prefix(k)) == moves {
            if k < solution.count { return .move(code: solution[k], onPlan: true) }
            return .finished
        }
        // Off the designed line: search with greedy rollouts, but never for more than ~3 seconds.
        let deadline = Date().addingTimeInterval(3.0)
        if state.jammed == nil, let found = searchMove(board: board, tunnels: tunnels, state: state, deadline: deadline), found.1 {
            return .move(code: found.0, onPlan: true)
        }
        var lcp = 0
        while lcp < moves.count && lcp < solution.count && moves[lcp] == solution[lcp] { lcp += 1 }
        let back = moves.count - lcp
        let slotsFullOfWaiting = state.chambers.count >= state.capacity && !state.chambers.contains(where: { $0.held })
        if back > 0 || state.jammed != nil || slotsFullOfWaiting { return .undo(count: max(1, back)) }
        if let found = searchMove(board: board, tunnels: tunnels, state: state, deadline: Date().addingTimeInterval(1.0)) {
            return .move(code: found.0, onPlan: false)
        }
        return .finished
    }
}
