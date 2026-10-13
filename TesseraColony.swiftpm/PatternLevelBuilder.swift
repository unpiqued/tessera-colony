import Foundation

/// Pattern mosaics: a fresh level from a seed. Inside the same checkered frame, each seed picks one
/// of five different layouts — a rosette (petals, bead ring, scallops, lattice), a starburst, fish
/// scales, a six-way kaleidoscope of random shapes, or striped ribbons over polka dots — so new
/// patterns are new designs, not recoloured copies. Each tile's colour family comes straight from a
/// formula (mirror of Tools/pattern.py), and LevelGenerator plans teams and tunnels and replays the
/// plan, so every pattern level is proven solvable before it is offered.
enum PatternLevelBuilder {
    static let width = 46
    static let height = 52
    static let bayer: [[Int]] = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]

    private static func pick(_ rng: inout SplitMix64, _ n: Int) -> Int { rng.int(n) }

    static let layoutNames = ["Rosette", "Starburst", "Fish scales", "Kaleidoscope", "Ribbons"]
    /// Makes seed 1 the rosette (the golden picture the self-test compares).
    static let layoutOffset = 4

    /// Floor modulo (the Python mirror uses Python's %, which floors).
    private static func fmod(_ a: Double, _ n: Double) -> Double { a - n * (a / n).rounded(.down) }
    private static func imod(_ a: Int, _ n: Int) -> Int { ((a % n) + n) % n }

    static func rows(seed: UInt64) -> [String] { design(seed: seed).rows }

    /// The pattern's rows and the name of its layout.
    static func design(seed: UInt64) -> (rows: [String], layout: String) {
        var rng = SplitMix64(seed: seed)
        var fams = Array(0..<6)
        var i = fams.count - 1
        while i > 0 {
            let j = pick(&rng, i + 1)
            fams.swapAt(i, j)
            i -= 1
        }
        let frame = fams[0], field = fams[1], petals = fams[2], ring = fams[3], centre = fams[4], accent = fams[5]
        let nPetals = 5 + pick(&rng, 8)
        let petalK = [0.8, 1.4, 2.2][pick(&rng, 3)]
        let rPetal = 16.0 + Double(pick(&rng, 4))
        let rInner = rPetal * (0.5 + 0.08 * Double(pick(&rng, 3)))
        let rRing = 5.5 + Double(pick(&rng, 3))
        let rCentre = 2.6 + Double(pick(&rng, 3)) * 0.6
        let nBeads = 14 + 2 * pick(&rng, 6)
        let nScallops = 2 * nPetals
        let lattice = pick(&rng, 3)
        let twist = Double(pick(&rng, 5) - 2) * 0.06
        let layout = (pick(&rng, 5) + layoutOffset) % 5
        // parameters of the other layouts (drawn after the rosette's, so seed 1 is unchanged)
        let nPts = 5 + pick(&rng, 6)
        let rOut = 17.0 + Double(pick(&rng, 4))
        let rIn = rOut * (0.42 + 0.05 * Double(pick(&rng, 3)))
        let nRays = 2 * (8 + pick(&rng, 5))
        var scaleR = 9.0 + Double(pick(&rng, 3))
        let nBlobs = 8 + pick(&rng, 5)
        var blobs: [(x: Double, y: Double, r: Double, f: Int)] = []
        for _ in 0..<nBlobs {
            let rr = 2.0 + Double(pick(&rng, 19))
            let ang = Double(pick(&rng, 7)) * (Double.pi / 6.0) / 6.0
            let br = 1.5 + 0.5 * Double(pick(&rng, 6))
            let bf = pick(&rng, 4)
            blobs.append((x: rr * cos(ang), y: rr * sin(ang), r: br, f: bf))
        }
        let dotSp = 5 + pick(&rng, 2)
        let dotR = 1.4 + 0.4 * Double(pick(&rng, 2))
        let ribbonW = 3.0 + Double(pick(&rng, 3))
        // more variety for fish scales and ribbons (drawn last, so earlier draws are unchanged)
        let fsBands = 3 + pick(&rng, 2)
        let fsPhase = pick(&rng, 8)
        scaleR += Double(pick(&rng, 4) - 1)
        let moonX = Double(9 + pick(&rng, 25))
        let moonY = Double(9 + pick(&rng, 14))
        let moonR = Double(5 + pick(&rng, 4))
        let rbA1 = pick(&rng, 8)
        let rbA2 = pick(&rng, 4)
        let rbKx = Double(pick(&rng, 13) - 6)
        let rbKy = Double(pick(&rng, 13) - 6)
        let rbPeriod = Double(2 + pick(&rng, 3))
        let rbDots = pick(&rng, 3)
        let bandFams = [petals, ring, accent, centre]
        let w = width, h = height
        let cx = Double(w - 1) / 2.0, cy = Double(h - 1) / 2.0
        let letters = Array("abcdefghijklmnopqrstuvwx")
        let np = Double(nPetals)
        var out: [String] = []
        for y in 0..<h {
            var row = ""
            for x in 0..<w {
                let dx = Double(x) - cx, dy = Double(y) - cy
                let r = (dx * dx + dy * dy).squareRoot()
                let a = atan2(dy, dx) + twist * r / 10.0
                let dEdge = min(min(x, y), min(w - 1 - x, h - 1 - y))
                var fam: Int
                var shade: Double
                if dEdge == 0 {
                    fam = frame; shade = 0.85
                } else if dEdge == 1 {
                    if (x + y) % 2 == 0 { fam = frame; shade = 0.3 } else { fam = accent; shade = 0.1 }
                } else if dEdge == 2 {
                    fam = frame; shade = 0.6
                } else if layout == 1 {
                    (fam, shade) = starburst(r: r, a: a, field: field, accent: accent, petals: petals, ring: ring,
                                             centre: centre, nPts: nPts, rOut: rOut, rIn: rIn, nRays: nRays)
                } else if layout == 2 {
                    (fam, shade) = fishScales(x: x, y: y, field: field, bandFams: bandFams, radius: scaleR, bands: fsBands,
                                              phase: fsPhase, moon: (moonX, moonY, moonR))
                } else if layout == 3 {
                    (fam, shade) = kaleidoscope(dx: dx, dy: dy, r: r, field: field, ring: ring, bandFams: bandFams, blobs: blobs)
                } else if layout == 4 {
                    (fam, shade) = ribbons(x: x, y: y, dx: dx, dy: dy, field: field, accent: accent, centre: centre,
                                           petals: petals, ring: ring, spacing: dotSp, dotR: dotR, width: ribbonW,
                                           angle1: rbA1, angle2: rbA2, knot: (rbKx, rbKy), period: rbPeriod, dots: rbDots)
                } else {
                    fam = field
                    var on: Bool
                    if lattice == 0 {
                        let s1 = (abs(dx) + abs(dy)).truncatingRemainder(dividingBy: 6)
                        let s2 = abs(dx - dy).truncatingRemainder(dividingBy: 6)
                        on = s1 < 1 || s2 < 1
                    } else if lattice == 1 {
                        on = (x + y) % 5 == 0 || (x - y) % 5 == 0
                    } else {
                        on = x % 5 == 0 || y % 5 == 0
                    }
                    shade = (on ? 0.75 : 0.2) + 0.15 * min(1.0, r / 30.0)
                    for (qx, qy) in [(3, 3), (w - 4, 3), (3, h - 4), (w - 4, h - 4)] {
                        let ex = Double(x - qx), ey = Double(y - qy)
                        let qr = (ex * ex + ey * ey).squareRoot()
                        if qr < 6.5 {
                            if qr < 4.5 { fam = ring; shade = 0.25 + 0.1 * qr } else { fam = accent; shade = 0.4 }
                        }
                    }
                    let sr = rPetal + 2.2
                    var seg = (a + Double.pi) / (2 * Double.pi) * Double(nScallops)
                    seg -= seg.rounded(.down)
                    let bump = 1.3 * sin(Double.pi * seg)
                    if sr - 0.6 < r && r < sr + bump {
                        fam = accent; shade = 0.2 + 0.5 * (r - sr + 0.6) / 2.0
                    }
                    let lobe = pow(abs(cos(np * a / 2.0)), petalK)
                    let pr = rPetal * (0.42 + 0.58 * lobe)
                    if r < pr {
                        fam = petals
                        shade = 0.15 + 0.75 * (r / pr)
                        if abs(sin(np * a)) < 0.1 && r > rRing + 1 { shade = 1.0 }
                    }
                    let lobe2 = pow(abs(cos(np * (a + Double.pi / np) / 2.0)), petalK)
                    let pr2 = rInner * (0.5 + 0.5 * lobe2)
                    if r < pr2 {
                        fam = accent; shade = 0.1 + 0.6 * r / pr2
                    }
                    if abs(r - rRing) < 1.2 {
                        fam = ring
                        let bead = Int(((a + Double.pi) / (2 * Double.pi)) * Double(nBeads)) % 2
                        shade = bead != 0 ? 0.15 : 0.75
                    }
                    if r < rCentre {
                        fam = centre != ring ? centre : petals
                        shade = 0.1 + 0.8 * r / rCentre
                    }
                }
                shade = min(1.0, max(0.0, shade))
                let dth = (Double(bayer[y % 4][x % 4]) / 16.0 - 0.47) * 0.85
                let tone = min(3, max(0, Int((shade * 3.0 + 0.5 + dth).rounded(.down))))
                row.append(letters[fam * 4 + tone])
            }
            out.append(row)
        }
        return (out, layoutNames[layout])
    }

    // MARK: - the other layouts (mirrors of starburst / fish_scales / kaleidoscope / ribbons in pattern.py)

    private static func starburst(r: Double, a: Double, field: Int, accent: Int, petals: Int, ring: Int, centre: Int,
                                  nPts: Int, rOut: Double, rIn: Double, nRays: Int) -> (Int, Double) {
        let sector = imod(Int(((a + Double.pi) / (2 * Double.pi) * Double(nRays)).rounded(.down)), 2)
        var fam = sector == 1 ? accent : field
        var shade = (sector == 1 ? 0.3 : 0.2) + 0.4 * min(1.0, r / 32.0)
        let t = fmod((a + Double.pi) / (2 * Double.pi) * Double(nPts), 1.0)
        let pt = abs(2 * t - 1)
        let radius = rIn + (rOut - rIn) * pow(pt, 1.5)
        if radius <= r && r < radius + 1.4 { fam = ring; shade = 0.8 }
        if r < radius {
            fam = petals
            shade = 0.15 + 0.55 * r / radius + (t < 0.5 ? 0.2 : 0.0)
        }
        if abs(r - rIn * 0.55) < 0.9 { fam = ring; shade = 0.3 }
        if r < rIn * 0.4 { fam = centre; shade = 0.1 + 0.7 * r / (rIn * 0.4) }
        return (fam, shade)
    }

    private static func fishScales(x: Int, y: Int, field: Int, bandFams: [Int], radius R: Double, bands: Int,
                                   phase: Int, moon: (Double, Double, Double)) -> (Int, Double) {
        let px0 = Double(x), py = Double(y)
        let dm = ((px0 - moon.0) * (px0 - moon.0) + (py - moon.1) * (py - moon.1)).squareRoot()
        if dm < moon.2 { return (field, 0.1 + 0.5 * dm / moon.2) }
        if dm < moon.2 + 1.2 { return (bandFams[0], 0.9) }
        let px = px0 + Double(phase) * R / 4.0
        let stepY = R * 0.5
        let rowsN = Int(Double(height) / stepY) + 3
        var j = rowsN
        while j >= -1 {
            let sy = Double(j) * stepY
            if py > sy + 0.01 { j -= 1; continue }
            let off = imod(j, 2) == 1 ? R : 0.0
            let i0 = Int(((px - off) / (2 * R)).rounded(.down))
            for i in [i0, i0 + 1] {
                let sx = Double(i) * 2 * R + off
                let d = ((px - sx) * (px - sx) + (py - sy) * (py - sy)).squareRoot()
                if d < R {
                    let bw = R / Double(bands)
                    let band = Int(d / bw)
                    let fam = bandFams[imod(j, 2) * 2 + band % 2]
                    return (fam, 0.15 + 0.6 * fmod(d, bw) / bw)
                }
            }
            j -= 1
        }
        return (field, 0.3)
    }

    private static func kaleidoscope(dx: Double, dy: Double, r: Double, field: Int, ring: Int, bandFams: [Int],
                                     blobs: [(x: Double, y: Double, r: Double, f: Int)]) -> (Int, Double) {
        let hexd = max(abs(dy), abs(dy) * 0.5 + abs(dx) * 3.0.squareRoot() / 2)
        if hexd > 21.5 {
            let on = imod(Int((r / 3.0).rounded(.down)), 2) == 0
            return (field, on ? 0.25 : 0.55)
        }
        if hexd > 20.0 { return (ring, 0.7) }
        let a = atan2(dy, dx)
        var af = fmod(a, Double.pi / 3)
        if af > Double.pi / 6 { af = Double.pi / 3 - af }
        let px = r * cos(af), py = r * sin(af)
        var fam = field
        var shade = 0.1 + 0.5 * r / 22.0
        for b in blobs {
            let d = ((px - b.x) * (px - b.x) + (py - b.y) * (py - b.y)).squareRoot()
            if d < b.r { fam = bandFams[b.f]; shade = 0.15 + 0.6 * d / b.r }
        }
        return (fam, shade)
    }

    private static func ribbons(x: Int, y: Int, dx: Double, dy: Double, field: Int, accent: Int, centre: Int,
                                petals: Int, ring: Int, spacing sp: Int, dotR: Double, width w: Double,
                                angle1: Int, angle2: Int, knot: (Double, Double), period: Double, dots: Int) -> (Int, Double) {
        let gx = Double(x % sp), gy = Double(y % sp)
        let half = Double(sp - 1) / 2.0
        let ex = abs(gx - half), ey = abs(gy - half)
        var inDot: Bool
        var dd: Double
        if dots == 0 {
            dd = (ex * ex + ey * ey).squareRoot(); inDot = dd < dotR
        } else if dots == 1 {
            inDot = ex + ey < dotR * 1.3; dd = (ex + ey) / 1.3
        } else {
            inDot = min(ex, ey) < 0.6 && max(ex, ey) < dotR + 0.4; dd = max(ex, ey)
        }
        let qx = dx - knot.0, qy = dy - knot.1
        let r = (qx * qx + qy * qy).squareRoot()
        var fam = field
        var shade = 0.2 + 0.2 * min(1.0, r / 30.0)
        if inDot {
            fam = (x / sp + y / sp) % 2 == 0 ? accent : centre
            shade = 0.15 + 0.5 * dd / max(dotR, 0.1)
        }
        let a1 = Double(angle1) * Double.pi / 8.0
        let a2 = a1 + Double(2 + angle2) * Double.pi / 8.0
        let along1 = qx * cos(a1) + qy * sin(a1), across1 = -qx * sin(a1) + qy * cos(a1)
        let along2 = qx * cos(a2) + qy * sin(a2), across2 = -qx * sin(a2) + qy * cos(a2)
        if abs(across1) < w {
            fam = petals
            shade = imod(Int((along1 / period).rounded(.down)), 2) == 0 ? 0.2 : 0.6
            if abs(across1) > w - 0.9 { shade = 0.9 }
        }
        if abs(across2) < w {
            fam = ring
            shade = imod(Int((along2 / period).rounded(.down)), 2) == 0 ? 0.2 : 0.6
            if abs(across2) > w - 0.9 { shade = 0.9 }
        }
        if r < w * 1.5 { fam = centre; shade = 0.1 + 0.6 * r / (w * 1.5) }
        if abs(r - w * 1.5) < 0.8 { fam = accent; shade = 0.8 }
        return (fam, shade)
    }

    /// Builds a playable, verified pattern level. Tries a few seeds if planning ever fails.
    static func build(seed: UInt64, number: Int) -> LevelDefinition? {
        var s = seed
        for _ in 0..<5 {
            let d = design(seed: s)
            let art = d.rows
            let board = Board(art: art)
            if let plan = LevelGenerator.generate(board: board, seed: s ^ 0x5EED) {
                let used = plan.maxChambersUsed
                return LevelDefinition(id: "pattern-\(s)", title: "Pattern \(number)",
                                       subtitle: "Generated pattern · \(d.layout) · seed \(s % 100_000)",
                                       art: art, palette: GeneratedPalette.builtIn, tunnels: plan.tunnels,
                                       chambersGentle: used + 4, chambersClassic: used + 2, chambersExpert: used + 1,
                                       solution: plan.solution, goldenClaimsPerMove: [], goldenClaimsHash: 0,
                                       goldenFinalStateHash: 0, isPhoto: true)
            }
            s = s &+ 0x9E3779B97F4A7C15
        }
        return nil
    }

    static let goldenSeed1: [String] = [
        "cdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcd",
        "dbvbvbvbvbvbvbvbvbvbvbvbvbvbvbvbvbvbvbvbvbvbvc",
        "cubcccbcccbcccbcccbcccbcccbcccbcccbcccbcccbcbd",
        "dbcjjjkkwvhffffgffffhffffhffffhffffhwvkkkjjcvd",
        "cucjjjjkvvgffffhffffgffffhffffgffffhvvkkjjjcbd",
        "dbcjkjkkvvhhhghghghghghghghghghhhghhvvkkkjkcvc",
        "cubkjkkvvfgffffhfffwvwvvvwvfffgffffhfvvkkkjcbd",
        "dbckkkvvwfhffffgfvvvvffffvvvwfhffffgfvvvkkkcvd",
        "cucvvvvvffgffwvvufffgfffehffevvvvffhffvvvvvcbd",
        "dbcvvvffffhwwvfgffffhffffgffffhfvvwgffffvvwcvc",
        "cubhghghghvvuhghghghghghopopopghgvvwghghghgcbd",
        "dbcffhfffvvffffgffffhffopopppppffffvwfffhffcvd",
        "cucffhffvvgfeffhefffgfopooopopofeffhvwffgffcbd",
        "dbcffgffvfhffffgffffhfpooopopopffffgfvffhffcvc",
        "cubffhffffgpopopffefgpoooopoooopffehffffgffcbd",
        "dbcghhwvhgpopopopphghooooopooopphghghgvvhhhcvd",
        "cucffwvfepopooooooofgooononoooopeffheffvvffcbd",
        "dbcffvfffoppoooooopohoooonoooopffffgffffvffcvc",
        "cubfvvffopoopoooooowwkijkpnoooofffehffffvwfcbd",
        "dbcfwvffpppooooooooilkjilkjooopffffgffffvvfcvd",
        "cucwvhghgpooooopnoijkkijkkijwoghggghghghgvwcbd",
        "dbcwvgfffopooooookliwvwvnwjkkwpopopopfffhvwcvc",
        "cubwvhffffoooonoijkwvvvvvwvkijooooooopefgvvcbd",
        "dbcvvgffffhopooojiwwwvttvvwvjioooooopopfhvwcvd",
        "cucvehffefgfoookkkvvvsrssvvwkkkonoooooopgfvcbd",
        "dbcghghghghghgpkkkwvtsrrsswwkklooooooopphghcvc",
        "cubffhffffgfffojijvvssrrstvwijionoooopopgffcbd",
        "dbcvfgffffhfpooijiwvwssstvvvjijooooopopphfwcvd",
        "cucwuhffefgpooookkwwvvstvvvwkknonoooopofgvvcbd",
        "dbcvvgffffpoooookkjwwvvvwvwikkoooopopoffhvwcvc",
        "cubwvhghgpoooononjikvvvwnwkjiwooopopohghgvvcbd",
        "dbcwwgfffppooooponlkjilkjilkwohffffgffffhvwcvd",
        "cucfvvffopoooooononkiikkiikonoofeffhefffuvfcbd",
        "dbcfwvffpopopoooooowwilkjpoooopffffgffffvvfcvc",
        "cubffvfffpopooooooopgooononoooofffehffffvffcbd",
        "dbcghwvghppopopopopghooooooooopphghghghvwhhcvd",
        "cucffhvvefopooopopefgooooopoooopeffhefuvgffcbd",
        "dbcffgffffhppoppffffhopooopoooppfffgffffhffcvc",
        "cubffhffvfgfffehffefgfooooooopoffffhfvffgffcbd",
        "dbcffhffwvhffffgffffhfpopopppopffffgvvffhffcvd",
        "cuchghghgwvhghghghghgggpooopopohghgvvhghghgcbd",
        "dbcffgffffwvvffgffffhfffpopppphffvvwffffhffcvc",
        "cubvvvffffgwvvfhffffgffffhffffgfvwvhffffvvvcbd",
        "dbcvwvvvffhffwwvvfffhffffgfffvvvwffgffvvwvvcvd",
        "cuckkkvvvfgffffhevvvufffevuvvfgffffhfvvvkkkcbd",
        "dbckkkkvvghhhghghghvwvwvwvwghghghghhhvwkkkkcvc",
        "cubjjkjkvvgffffhffffgffffhffffgffffhvvkkjkjcbd",
        "dbcjkjkkwvhffffgffffhffffhffffhffffgwvkkkjjcvd",
        "cucjjjjkvvgffffhffffgffffhffffgffffhvvkkjjicbd",
        "dbccccccccccccccccccccccccccccccccccccccccccvc",
        "cububububububububububububububububububububububd",
        "dddcdddcdddcdddcdddcdddcdddcdddcdddcdddcdddcdd"
    ]
}
