import Foundation

/// Straight (non-premultiplied, opaque) RGBA pixels, row 0 at the top.
struct PixelImage {
    let width: Int
    let height: Int
    let rgba: [UInt8]
}

enum PhotoDetail: String, CaseIterable, Codable, Identifiable {
    case coarse, fine, veryFine
    var id: String { rawValue }
    var targetTiles: Int {
        switch self {
        case .coarse: return 1600
        case .fine: return 3600
        case .veryFine: return 6000
        }
    }
    var title: String {
        switch self {
        case .coarse: return "Chunky"
        case .fine: return "Fine"
        case .veryFine: return "Very fine"
        }
    }
}

enum PhotoBuildError: Error, Equatable {
    case unreadable
    case notEnoughColour(colouredTiles: Int)
    case generationFailed

    var message: String {
        switch self {
        case .unreadable:
            return "That image couldn't be read. Try another photo."
        case .notEnoughColour(let n):
            return n == 0
                ? "That photo is white or near-white all over, so there is nothing for the ants to carry. Try a photo with more colour."
                : "Only \(n) coloured tiles are left after the white areas are removed — not enough for a puzzle. Try a more colourful photo or a finer grid."
        case .generationFailed:
            return "The colony couldn't plan a solvable puzzle for this photo. Try a different detail level."
        }
    }
}

/// Photo -> playable mosaic. Swift port of Tools/photo.py:
/// centre crop -> tile grid (box average) -> near-white tiles become open ground ->
/// k-means colour families in Lab -> merge look-alikes and slivers -> four tones per family ->
/// LevelGenerator builds teams and tunnels and replays the solution to prove it works.
enum PhotoLevelBuilder {
    static let minColouredTiles = 24

    static func gridSize(width: Int, height: Int, tiles: Int) -> (Int, Int, Double) {
        let aspect = min(1.5, max(0.6, Double(width) / Double(max(1, height))))
        let gw = Int((Double(tiles) * aspect).squareRoot().rounded())
        let gh = Int((Double(tiles) / Double(max(1, gw))).rounded())
        return (max(8, min(90, gw)), max(8, min(100, gh)), aspect)
    }

    static func lab(_ r: Double, _ g: Double, _ b: Double) -> (Double, Double, Double) {
        func lin(_ c: Double) -> Double {
            let v = c / 255
            return v <= 0.04045 ? v / 12.92 : pow((v + 0.055) / 1.055, 2.4)
        }
        let lr = lin(r), lg = lin(g), lb = lin(b)
        let x = (lr * 0.4124 + lg * 0.3576 + lb * 0.1805) / 0.95047
        let y = lr * 0.2126 + lg * 0.7152 + lb * 0.0722
        let z = (lr * 0.0193 + lg * 0.1192 + lb * 0.9505) / 1.08883
        func f(_ t: Double) -> Double { t > 0.008856 ? cbrt(t) : 7.787 * t + 16.0 / 116.0 }
        let fx = f(x), fy = f(y), fz = f(z)
        return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))
    }

    static func isNearWhite(_ l: (Double, Double, Double)) -> Bool {
        let c = (l.1 * l.1 + l.2 * l.2).squareRoot()
        return (l.0 > 90 && c < 15) || l.0 > 95
    }

    /// Box-averaged colour of every tile after a centre crop. Returns (gw, gh, rgb triples).
    static func downsample(_ img: PixelImage, tiles: Int) -> (Int, Int, [(Double, Double, Double)]) {
        let (gw, gh, aspect) = gridSize(width: img.width, height: img.height, tiles: tiles)
        var x0 = 0, y0 = 0, w = img.width, h = img.height
        let current = Double(w) / Double(h)
        if current > aspect {
            let cw = Int(Double(h) * aspect)
            x0 = (w - cw) / 2
            w = cw
        } else if current < aspect {
            let ch = Int(Double(w) / aspect)
            y0 = (h - ch) / 2
            h = ch
        }
        var out: [(Double, Double, Double)] = []
        out.reserveCapacity(gw * gh)
        for ty in 0..<gh {
            let ya = ty * h / gh
            let yb = max(ya + 1, (ty + 1) * h / gh)
            for tx in 0..<gw {
                let xa = tx * w / gw
                let xb = max(xa + 1, (tx + 1) * w / gw)
                var sr = 0.0, sg = 0.0, sb = 0.0, n = 0.0
                for y in ya..<yb {
                    let row = (y + y0) * img.width
                    for x in xa..<xb {
                        let o = (row + x + x0) * 4
                        sr += Double(img.rgba[o])
                        sg += Double(img.rgba[o + 1])
                        sb += Double(img.rgba[o + 2])
                        n += 1
                    }
                }
                out.append((sr / n, sg / n, sb / n))
            }
        }
        return (gw, gh, out)
    }

    static func build(image: PixelImage, detail: PhotoDetail, seed: UInt64, id: String, title: String) -> Result<LevelDefinition, PhotoBuildError> {
        guard image.width > 1, image.height > 1, image.rgba.count >= image.width * image.height * 4 else { return .failure(.unreadable) }
        let (gw, gh, rgb) = downsample(image, tiles: detail.targetTiles)
        let labs = rgb.map { lab($0.0, $0.1, $0.2) }
        var coloured: [Int] = []
        for (i, l) in labs.enumerated() where !isNearWhite(l) { coloured.append(i) }
        let n = coloured.count
        if n < minColouredTiles { return .failure(.notEnoughColour(colouredTiles: n)) }

        // k-means on (L/2, a, b) so hue and chroma decide families, lightness decides tones
        let pts: [(Double, Double, Double)] = coloured.map { (labs[$0].0 * 0.5, labs[$0].1, labs[$0].2) }
        func d2(_ a: (Double, Double, Double), _ b: (Double, Double, Double)) -> Double {
            let x = a.0 - b.0, y = a.1 - b.1, z = a.2 - b.2
            return x * x + y * y + z * z
        }
        var rng = SplitMix64(seed: seed)
        let k0 = min(6, max(1, n / 40))
        var cents: [(Double, Double, Double)] = [pts[rng.int(n)]]
        while cents.count < k0 {
            var dist = [Double](repeating: 0, count: n)
            var total = 0.0
            for i in 0..<n {
                var best = Double.infinity
                for c in cents { best = min(best, d2(pts[i], c)) }
                dist[i] = best
                total += best
            }
            if total <= 0 { break }
            var r = rng.unit() * total
            var pick = n - 1
            for i in 0..<n {
                r -= dist[i]
                if r < 0 { pick = i; break }
            }
            cents.append(pts[pick])
        }
        var assign = [Int](repeating: 0, count: n)
        for iteration in 0..<13 {
            for i in 0..<n {
                var best = 0
                var bd = Double.infinity
                for (j, c) in cents.enumerated() {
                    let d = d2(pts[i], c)
                    if d < bd { bd = d; best = j }
                }
                assign[i] = best
            }
            if iteration == 12 { break }
            var sums = [(Double, Double, Double)](repeating: (0, 0, 0), count: cents.count)
            var counts = [Double](repeating: 0, count: cents.count)
            for i in 0..<n {
                let j = assign[i]
                sums[j].0 += pts[i].0; sums[j].1 += pts[i].1; sums[j].2 += pts[i].2
                counts[j] += 1
            }
            for j in 0..<cents.count where counts[j] > 0 {
                cents[j] = (sums[j].0 / counts[j], sums[j].1 / counts[j], sums[j].2 / counts[j])
            }
        }
        // merge look-alike families and slivers (< 3% of tiles)
        var counts = [Double](repeating: 0, count: cents.count)
        for j in assign { counts[j] += 1 }
        var alive = (0..<cents.count).filter { counts[$0] > 0 }
        let sliver = max(8.0, 0.03 * Double(n))
        while alive.count > 1 {
            var best: (Double, Int, Int)? = nil
            for i in 0..<alive.count {
                for j in (i + 1)..<alive.count {
                    let a = alive[i], b = alive[j]
                    let d = d2(cents[a], cents[b]).squareRoot()
                    let small = min(counts[a], counts[b]) < sliver
                    if d < 16 || small {
                        if best == nil || d < best!.0 { best = (d, a, b) }
                    }
                }
            }
            guard let m = best else { break }
            let a = m.1, b = m.2
            let t = counts[a] + counts[b]
            cents[a] = ((cents[a].0 * counts[a] + cents[b].0 * counts[b]) / t,
                        (cents[a].1 * counts[a] + cents[b].1 * counts[b]) / t,
                        (cents[a].2 * counts[a] + cents[b].2 * counts[b]) / t)
            counts[a] = t
            counts[b] = 0
            for i in 0..<n where assign[i] == b { assign[i] = a }
            alive.removeAll { $0 == b }
        }
        var remap = [Int: Int]()
        for (newIndex, old) in alive.enumerated() { remap[old] = newIndex }
        let family = assign.map { remap[$0] ?? 0 }
        let k = alive.count

        // four tones per family by lightness quartile (tone 0 = lightest)
        var tone = [Int](repeating: 0, count: n)
        var tones: [[UInt32]] = []
        var names: [String] = []
        for f in 0..<k {
            let members = (0..<n).filter { family[$0] == f }.sorted { labs[coloured[$0]].0 > labs[coloured[$1]].0 }
            var famTones: [UInt32] = []
            var mean = (0.0, 0.0, 0.0)
            for m in members { let c = rgb[coloured[m]]; mean.0 += c.0; mean.1 += c.1; mean.2 += c.2 }
            let cnt = Double(max(1, members.count))
            mean = (mean.0 / cnt, mean.1 / cnt, mean.2 / cnt)
            for t in 0..<4 {
                let lo = members.count * t / 4
                let hi = members.count * (t + 1) / 4
                var c = (0.0, 0.0, 0.0)
                if hi > lo {
                    for m in members[lo..<hi] {
                        tone[m] = t
                        let p = rgb[coloured[m]]
                        c.0 += p.0; c.1 += p.1; c.2 += p.2
                    }
                    let q = Double(hi - lo)
                    c = (c.0 / q, c.1 / q, c.2 / q)
                } else {
                    c = mean
                }
                famTones.append(hexColor(c))
            }
            tones.append(famTones)
            names.append(colourName(lab(mean.0, mean.1, mean.2)))
        }
        names = uniquified(names)

        // art rows ("." = open ground where the photo was white)
        var grid = [Int](repeating: -1, count: gw * gh)
        for (m, idx) in coloured.enumerated() { grid[idx] = family[m] * 4 + tone[m] }
        let letters = Array("abcdefghijklmnopqrstuvwx")
        var rows: [String] = []
        for y in 0..<gh {
            var s = ""
            for x in 0..<gw {
                let v = grid[y * gw + x]
                s.append(v < 0 ? "." : letters[v])
            }
            rows.append(s)
        }
        let palette = LevelPalette(names: names, tones: tones)
        let board = Board(art: rows)
        guard let gen = LevelGenerator.generate(board: board, seed: seed ^ 0xC0FFEE) else { return .failure(.generationFailed) }
        let used = gen.maxChambersUsed      // most teams waiting at once in the planned solution
        let level = LevelDefinition(id: id, title: title,
                                    subtitle: "Your photo · \(k) colour\(k == 1 ? "" : "s")",
                                    art: rows, palette: palette, tunnels: gen.tunnels,
                                    chambersGentle: used + 4, chambersClassic: used + 2, chambersExpert: used + 1,
                                    solution: gen.solution, goldenClaimsPerMove: [], goldenClaimsHash: 0,
                                    goldenFinalStateHash: 0, isPhoto: true)
        return .success(level)
    }

    static func hexColor(_ c: (Double, Double, Double)) -> UInt32 {
        let r = UInt32(max(0, min(255, c.0.rounded())))
        let g = UInt32(max(0, min(255, c.1.rounded())))
        let b = UInt32(max(0, min(255, c.2.rounded())))
        return (r << 16) | (g << 8) | b
    }

    /// A friendly name for VoiceOver ("Blue", "Dark green", ...). Not shown on pieces.
    static func colourName(_ l: (Double, Double, Double)) -> String {
        let c = (l.1 * l.1 + l.2 * l.2).squareRoot()
        if c < 12 {
            if l.0 > 75 { return "Silver" }
            if l.0 > 40 { return "Grey" }
            return "Charcoal"
        }
        var h = atan2(l.2, l.1) * 180 / Double.pi
        if h < 0 { h += 360 }
        var name: String
        switch h {
        case 0..<20: name = "Pink"
        case 20..<50: name = "Red"
        case 50..<75: name = l.0 < 50 ? "Brown" : "Orange"
        case 75..<100: name = l.0 < 55 ? "Olive" : "Gold"
        case 100..<160: name = "Green"
        case 160..<220: name = "Teal"
        case 220..<290: name = "Blue"
        case 290..<330: name = "Violet"
        default: name = "Magenta"
        }
        if l.0 < 35 && name != "Brown" && name != "Olive" { name = "Dark " + name.lowercased() }
        else if l.0 > 80 { name = "Pale " + name.lowercased() }
        return name
    }

    static func uniquified(_ names: [String]) -> [String] {
        var seen: [String: Int] = [:]
        return names.map { n in
            let c = (seen[n] ?? 0) + 1
            seen[n] = c
            return c == 1 ? n : "\(n) \(c)"
        }
    }
}
