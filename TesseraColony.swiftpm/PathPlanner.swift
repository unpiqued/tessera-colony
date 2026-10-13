import Foundation

/// How newly launched ants choose their route to a tile. Purely visual: which tiles a team claims
/// never changes. Changing the style affects ants launched afterwards; ants already walking keep
/// their route. Mirror of `plan_route` in Tools/engine.py.
enum PathStyle: String, CaseIterable, Codable, Identifiable {
    case direct, natural, curious, wall, scout, randomTeam, randomAnt

    var id: String { rawValue }

    var title: String {
        switch self {
        case .direct: return "Direct"
        case .natural: return "Natural"
        case .curious: return "Curious"
        case .wall: return "Wall-hugger"
        case .scout: return "Scout trail"
        case .randomTeam: return "Random per team"
        case .randomAnt: return "Random per ant"
        }
    }

    var blurb: String {
        switch self {
        case .direct: return "The shortest route, in straight runs."
        case .natural: return "Just as short, but it follows the straight line to the tile."
        case .curious: return "Each ant wanders a little, and about a third stop to sniff on the way."
        case .wall: return "Ants walk along the edge of the mosaic instead of cutting across open ground."
        case .scout: return "A team's first ant explores and leaves a fading trail in its colour; the others follow and straighten it."
        case .randomTeam: return "Each team picks one of the styles when it is sent."
        case .randomAnt: return "Every ant picks Direct, Natural, Curious or Wall-hugger for itself."
        }
    }

    var systemImage: String {
        switch self {
        case .direct: return "arrow.up.right"
        case .natural: return "line.diagonal"
        case .curious: return "scribble"
        case .wall: return "square.dashed"
        case .scout: return "point.topleft.down.curvedto.point.bottomright.up"
        case .randomTeam: return "shuffle"
        case .randomAnt: return "dice"
        }
    }

    static let teamMix: [PathStyle] = [.direct, .natural, .curious, .wall, .scout]
    static let antMix: [PathStyle] = [.direct, .natural, .curious, .wall]
}

/// An ant stopping to sniff on the way out: at path position `at` (cells) for `duration` game seconds.
struct TripPause {
    let at: Double
    let duration: Double
}

/// Reusable search buffers (one per ant scheduler), so planning a route allocates nothing per ant.
/// Cells are "fresh" for a search when their stamp differs from the current generation.
final class PlannerScratch {
    fileprivate var g: [Double]
    fileprivate var steps: [Int32]
    fileprivate var prev: [Int32]
    fileprivate var seen: [Int32]
    fileprivate var closed: [Int32]
    fileprivate var corridor: [Int32]
    fileprivate var gen: Int32 = 0
    fileprivate var corridorGen: Int32 = 0
    fileprivate var heap = PathPlanner.Heap()

    init(count: Int) {
        g = [Double](repeating: 0, count: count)
        steps = [Int32](repeating: 0, count: count)
        prev = [Int32](repeating: -1, count: count)
        seen = [Int32](repeating: 0, count: count)
        closed = [Int32](repeating: 0, count: count)
        corridor = [Int32](repeating: 0, count: count)
    }

    fileprivate func nextSearch() {
        if gen == Int32.max - 1 {
            gen = 0
            for i in seen.indices { seen[i] = 0; closed[i] = 0 }
        }
        gen += 1
        heap.items.removeAll(keepingCapacity: true)
    }

    fileprivate func nextCorridor() {
        if corridorGen == Int32.max - 1 {
            corridorGen = 0
            for i in corridor.indices { corridor[i] = 0 }
        }
        corridorGen += 1
    }

    fileprivate func inCorridor(_ n: Int) -> Bool { corridor[n] == corridorGen }
}

/// Route planning is bounded so a send never stalls the game (mirrors plan_route in Tools/engine.py):
/// each ant's search stays inside a corridor of `corridor` cells around its direct path (a route always
/// exists there and the search cannot flood the open ground) and may not exceed the longest route that
/// would be accepted. At most `maxStyledPerSend` ants of one send get a styled route, spread evenly
/// through the send; the others walk their direct path. A send shares `budgetPerSend` expansions and
/// each ant may use up to 10 per cell of its direct path + 100; an ant whose search runs out walks its
/// direct path.
enum PathPlanner {
    /// Wandering styles avoid cells whose tile has not been lifted yet (the ant would have to wait).
    static let futurePenalty = 4.0
    static let corridor = 3
    static let budgetPerSend = 16_000
    static let maxStyledPerSend = 32

    static func unitHash(_ a: Int, _ b: Int) -> Double { Double(hash32(a, b) & 0xFFFF) / 65535.0 }

    /// How strongly each style's search is pulled towards the tile (weighted A*).
    static func weight(_ style: PathStyle, trail: Bool) -> Double {
        switch style {
        case .natural: return 1.05
        case .curious: return 1.6
        case .wall: return 1.3
        case .scout: return trail ? 1.3 : 1.8
        default: return 1.0
        }
    }

    static func maxRouteCells(_ directCount: Int) -> Int { max(2 * directCount, directCount + 14) }

    static func antBudget(directCount: Int, remaining: Int) -> Int { max(0, min(remaining, 10 * directCount + 100)) }

    /// Minimal binary heap ordered by (f, order).
    struct Heap {
        var items: [(f: Double, order: Int, cell: Int32)] = []

        private static func less(_ a: (f: Double, order: Int, cell: Int32), _ b: (f: Double, order: Int, cell: Int32)) -> Bool {
            a.f < b.f || (a.f == b.f && a.order < b.order)
        }

        var isEmpty: Bool { items.isEmpty }

        mutating func push(_ e: (f: Double, order: Int, cell: Int32)) {
            items.append(e)
            var i = items.count - 1
            while i > 0 {
                let p = (i - 1) / 2
                if Heap.less(items[i], items[p]) {
                    items.swapAt(i, p)
                    i = p
                } else {
                    break
                }
            }
        }

        mutating func pop() -> (f: Double, order: Int, cell: Int32)? {
            guard !items.isEmpty else { return nil }
            let top = items[0]
            let last = items.removeLast()
            if !items.isEmpty {
                items[0] = last
                var i = 0
                while true {
                    let l = 2 * i + 1
                    let r = l + 1
                    var m = i
                    if l < items.count && Heap.less(items[l], items[m]) { m = l }
                    if r < items.count && Heap.less(items[r], items[m]) { m = r }
                    if m == i { break }
                    items.swapAt(i, m)
                    i = m
                }
            }
            return top
        }
    }

    /// Marks the cells within Manhattan distance `corridor` of `path` in the scratch's corridor.
    static func markCorridor(board: Board, path: [Int32], scratch: PlannerScratch) {
        scratch.nextCorridor()
        let cols = board.cols, rows = board.rows
        let tag = scratch.corridorGen
        let r = corridor
        for c32 in path {
            let c = Int(c32)
            let x = c % cols, y = c / cols
            for dy in -r...r {
                let yy = y + dy
                if yy < 0 || yy >= rows { continue }
                let span = r - abs(dy)
                for dx in -span...span {
                    let xx = x + dx
                    if xx < 0 || xx >= cols { continue }
                    scratch.corridor[yy * cols + xx] = tag
                }
            }
        }
    }

    /// Weighted A* over 4-neighbour cells (f = g + weight × Manhattan). Never expands towards a cell
    /// from which the route would exceed `maxCells`, and gives up after `budget` expansions.
    static func astar(board: Board, start: Int, goal: Int, weight: Double, maxCells: Int, budget: Int,
                      scratch sc: PlannerScratch, walkable: (Int) -> Bool,
                      cost: (Int) -> Double) -> (route: [Int32]?, expansions: Int) {
        if start == goal { return ([Int32(goal)], 0) }
        sc.nextSearch()
        let gen = sc.gen
        let cols = board.cols
        let gx = goal % cols, gy = goal / cols
        var order = 0
        var expansions = 0
        sc.seen[start] = gen
        sc.g[start] = 0
        sc.steps[start] = 0
        sc.prev[start] = -1
        sc.heap.push((f: weight * Double(abs(start % cols - gx) + abs(start / cols - gy)), order: 0, cell: Int32(start)))
        var found = false
        while let top = sc.heap.pop() {
            let c = Int(top.cell)
            if sc.closed[c] == gen { continue }
            if c == goal {
                found = true
                break
            }
            sc.closed[c] = gen
            expansions += 1
            if expansions > budget { return (nil, expansions) }
            let nextSteps = sc.steps[c] + 1
            let gc = sc.g[c]
            for k in 0..<4 {
                let n32 = board.neighbours[c * 4 + k]
                if n32 < 0 { continue }
                let n = Int(n32)
                if sc.closed[n] == gen || !walkable(n) { continue }
                let h = abs(n % cols - gx) + abs(n / cols - gy)
                if Int(nextSteps) + 1 + h > maxCells { continue }
                let ng = gc + cost(n)
                if sc.seen[n] != gen || ng < sc.g[n] - 1e-12 {
                    sc.seen[n] = gen
                    sc.g[n] = ng
                    sc.prev[n] = Int32(c)
                    sc.steps[n] = nextSteps
                    order += 1
                    sc.heap.push((f: ng + weight * Double(h), order: order, cell: n32))
                }
            }
        }
        guard found else { return (nil, expansions) }
        var path: [Int32] = [Int32(goal)]
        var cur = goal
        var guardSteps = 0
        while cur != start {
            let p = Int(sc.prev[cur])
            if p < 0 { return (nil, expansions) }
            path.append(Int32(p))
            cur = p
            guardSteps += 1
            if guardSteps > board.count { return (nil, expansions) }
        }
        path.reverse()
        return (path, expansions)
    }

    /// Route for one ant from the hole to the stand cell beside its tile. Only cells that are ground
    /// or already scheduled to be lifted, inside the ant's corridor, are used; the scheduler then
    /// delays the departure until every tile on the route has been lifted. Falls back to the claim's
    /// own path if the search runs out of budget or a style's route would be unreasonably long.
    static func plan(board: Board, liftTime: [Double], claim: Claim, style: PathStyle, seed: Int, now: Double,
                     trail: Set<Int32>?, budget: Int,
                     scratch: PlannerScratch) -> (route: [Int32], pauses: [TripPause], used: PathStyle, spent: Int) {
        let direct = claim.path
        if style == .direct || direct.count < 3 || budget <= 0 { return (direct, [], .direct, 0) }
        switch style {
        case .natural, .curious, .wall, .scout: break
        default: return (direct, [], .direct, 0)
        }
        let start = Int(direct[0])
        let goal = Int(direct[direct.count - 1])
        let cols = board.cols
        markCorridor(board: board, path: direct, scratch: scratch)
        func walkable(_ n: Int) -> Bool { scratch.inCorridor(n) && liftTime[n] < Double.infinity }
        func future(_ n: Int) -> Double {
            (board.family[n] >= 0 && liftTime[n] > now + 1e-9) ? futurePenalty : 0
        }
        let hasTrail = !(trail?.isEmpty ?? true)
        let w = weight(style, trail: hasTrail)
        let maxCells = maxRouteCells(direct.count)
        let result: (route: [Int32]?, expansions: Int)
        switch style {
        case .natural:
            let hx = Double(start % cols) + 0.5, hy = Double(start / cols) + 0.5
            let tx = Double(goal % cols) + 0.5, ty = Double(goal / cols) + 0.5
            let ln = max(1e-9, ((tx - hx) * (tx - hx) + (ty - hy) * (ty - hy)).squareRoot())
            result = astar(board: board, start: start, goal: goal, weight: w, maxCells: maxCells, budget: budget,
                           scratch: scratch, walkable: walkable) { n in
                let px = Double(n % cols) + 0.5, py = Double(n / cols) + 0.5
                return 1.0 + 1e-4 * abs((tx - hx) * (hy - py) - (hx - px) * (ty - hy)) / ln
            }
        case .curious:
            result = astar(board: board, start: start, goal: goal, weight: w, maxCells: maxCells, budget: budget,
                           scratch: scratch, walkable: walkable) { n in
                1.0 + 1.6 * unitHash(seed, n) + future(n)
            }
        case .wall:
            // beside a tile that is still on the board (the mosaic's current edge, not the board's rim)
            func edge(_ n: Int) -> Bool {
                for k in 0..<4 {
                    let m = Int(board.neighbours[n * 4 + k])
                    if m >= 0 && !(liftTime[m] < Double.infinity) { return true }
                }
                return false
            }
            result = astar(board: board, start: start, goal: goal, weight: w, maxCells: maxCells, budget: budget,
                           scratch: scratch, walkable: walkable) { n in
                1.0 + (edge(n) ? 0.0 : 0.9) + future(n)
            }
        default:
            if hasTrail, let t = trail {
                result = astar(board: board, start: start, goal: goal, weight: w, maxCells: maxCells, budget: budget,
                               scratch: scratch, walkable: walkable) { n in
                    1.0 + (t.contains(Int32(n)) ? 0.0 : 1.2) + future(n)
                }
            } else {
                result = astar(board: board, start: start, goal: goal, weight: w, maxCells: maxCells, budget: budget,
                               scratch: scratch, walkable: walkable) { n in
                    1.0 + 2.5 * unitHash(seed, n) + future(n)
                }
            }
        }
        guard let r = result.route, r.count <= maxCells else { return (direct, [], .direct, result.expansions) }
        var sniff = 0
        if style == .curious {
            sniff = unitHash(seed, 7) < 0.35 ? 1 : 0
        } else if style == .scout && !hasTrail {
            sniff = 1
        }
        var pauses: [TripPause] = []
        let l = Double(r.count)
        if r.count >= 8 {
            for k in 0..<sniff {
                let u = 2.0 + unitHash(seed, 101 + k) * (l - 4.0)
                pauses.append(TripPause(at: u, duration: 0.5 + 0.7 * unitHash(seed, 202 + k)))
            }
            pauses.sort { $0.at < $1.at }
        }
        return (r, pauses, style, result.expansions)
    }
}
