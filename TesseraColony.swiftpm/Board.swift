import Foundation

/// Immutable description of a level's grid: mosaic tiles plus the walkable ground around them.
/// Board coordinates: x grows right, y grows down. Index = y * cols + x.
final class Board: @unchecked Sendable {
    static let marginLeft = 2
    static let marginRight = 2
    static let marginTop = 2
    static let marginBottom = 6

    let artWidth: Int
    let artHeight: Int
    let cols: Int
    let rows: Int
    let count: Int
    /// -1 for ground, otherwise colour family 0...5.
    let family: [Int8]
    /// Glaze tone 0...3 (visual only; never affects matching).
    let tone: [UInt8]
    /// Cell index of the ant-hill hole.
    let hole: Int
    let tileCount: Int
    let familyTotals: [Int]
    /// Four neighbours per cell in the order up, left, right, down (-1 = outside the board).
    let neighbours: [Int32]

    init(art: [String]) {
        let h = art.count
        let w = art.first?.unicodeScalars.count ?? 0
        let c = w + Board.marginLeft + Board.marginRight
        let r = h + Board.marginTop + Board.marginBottom
        var fam = [Int8](repeating: -1, count: c * r)
        var tn = [UInt8](repeating: 0, count: c * r)
        var totals = [Int](repeating: 0, count: 6)
        var tiles = 0
        for (y, row) in art.enumerated() {
            var x = 0
            for scalar in row.unicodeScalars {
                let code = Int(scalar.value) - 97
                if code >= 0 && code < 24 && x < w {
                    let i = (y + Board.marginTop) * c + (x + Board.marginLeft)
                    fam[i] = Int8(code / 4)
                    tn[i] = UInt8(code % 4)
                    totals[code / 4] += 1
                    tiles += 1
                }
                x += 1
            }
        }
        var nb = [Int32](repeating: -1, count: c * r * 4)
        for i in 0..<(c * r) {
            let x = i % c
            let y = i / c
            if y > 0 { nb[i * 4 + 0] = Int32(i - c) }
            if x > 0 { nb[i * 4 + 1] = Int32(i - 1) }
            if x < c - 1 { nb[i * 4 + 2] = Int32(i + 1) }
            if y < r - 1 { nb[i * 4 + 3] = Int32(i + c) }
        }
        artWidth = w
        artHeight = h
        cols = c
        rows = r
        count = c * r
        family = fam
        tone = tn
        familyTotals = totals
        tileCount = tiles
        hole = (r - 3) * c + c / 2
        neighbours = nb
    }

    @inline(__always) func x(_ i: Int) -> Int { i % cols }
    @inline(__always) func y(_ i: Int) -> Int { i / cols }
    @inline(__always) func isTile(_ i: Int) -> Bool { family[i] >= 0 }

    func areAdjacent(_ a: Int, _ b: Int) -> Bool {
        let dx = abs(x(a) - x(b))
        let dy = abs(y(a) - y(b))
        return dx + dy == 1
    }

    /// Initial open map: ground is open, every tile is closed.
    func initialOpen() -> [Bool] {
        var open = [Bool](repeating: false, count: count)
        for i in 0..<count where family[i] < 0 { open[i] = true }
        return open
    }
}
