import SwiftUI

/// Drawing shared by the single-player board and the two-player boards: the mosaic bitmap, ant
/// hills, lifted tiles, the glow on claimed tiles, scout trails and the ants.
enum BoardPainter {
    /// Player colours in two-player mode (rings under ants on a shared board, panel accents).
    static let playerColors: [UInt32] = [0x3FB6C8, 0xF08A5D]

    static func paintBase(_ ctx: inout GraphicsContext, board b: Board, cs: CGFloat, t: Double, date: Date, size: CGSize,
                          raster: MosaicRaster?, trips: [AntTrip], ground: UInt32, holes: [Int], sharp: Bool) {
        // 1. Mosaic bitmap (tiles + soil), rebuilt ~10x per second at most.
        if let img = raster?.image {
            let image = Image(decorative: img, scale: 1).interpolation(sharp ? .none : .medium)
            ctx.draw(image, in: CGRect(origin: .zero, size: size))
        }
        // 2. Ant hills.
        for h in holes { drawHill(&ctx, board: b, hole: h, cs: cs) }
        // 3. Tiles lifted since the last bitmap refresh, and a soft glow on claimed tiles.
        var soilPatch = Path()
        var reserved = Path()
        for trip in trips {
            let tile = Int(trip.tile)
            let rect = CGRect(x: CGFloat(b.x(tile)) * cs, y: CGFloat(b.y(tile)) * cs, width: cs, height: cs)
            if trip.arrive <= t {
                if let r = raster, !r.shownOpen[tile] { soilPatch.addRect(rect) }
            } else {
                reserved.addRect(rect)
            }
        }
        ctx.fill(soilPatch, with: .color(Color(hex: ground)))
        // Claimed tiles glow softly (a light wash, no symbols) until their ant arrives.
        let pulse = 0.5 + 0.5 * sin(date.timeIntervalSinceReferenceDate * 3.0)
        ctx.fill(reserved, with: .color(Color.white.opacity(0.16 + 0.12 * pulse)))
    }

    static func paintAnts(_ ctx: inout GraphicsContext, board b: Board, cs: CGFloat, t: Double, trips: [AntTrip],
                          sprites: AntSpriteCache, detailed: Bool, ownerRings: Bool) {
        // Scout trails: faint dotted lines in the team's colour, laid as the ant walks and fading a
        // few seconds after it gets home. Overlapping trips make a stronger trail.
        for trip in trips where trip.style == .scout && t >= trip.depart && t < trip.home + 3 {
            var count = trip.path.count
            if t < trip.arrive {
                let u = AntGeometry.outbound(trip, elapsed: t - trip.depart).u
                if u.isFinite {
                    count = min(trip.path.count, Int(max(0, min(u, Double(trip.path.count)))) + 1)
                }
            }
            if count < 2 { continue }
            var line = Path()
            for k in 0..<count {
                let c = Int(trip.path[k])
                let p = CGPoint(x: (CGFloat(b.x(c)) + 0.5) * cs, y: (CGFloat(b.y(c)) + 0.5) * cs)
                if k == 0 { line.move(to: p) } else { line.addLine(to: p) }
            }
            let fade = t > trip.home ? max(0, 1 - (t - trip.home) / 3) : 1
            ctx.stroke(line, with: .color(Color(hex: trip.color).opacity(0.28 * fade)),
                       style: StrokeStyle(lineWidth: max(1, cs * 0.16), lineCap: .round, lineJoin: .round,
                                          dash: [cs * 0.18, cs * 0.3]))
        }
        // Ants: cartoon bodies in the colour of the tile each one is fetching, legs that plant and
        // lift in step with the ground speed, shadows, and the tiles they carry.
        var visible: [AntRenderer.Visible] = []
        visible.reserveCapacity(trips.count)
        var rings: [Path] = [Path(), Path()]
        for trip in trips {
            if let pose = AntGeometry.pose(trip, at: t, board: b) {
                visible.append(AntRenderer.Visible(trip: trip, pose: pose))
                if ownerRings {
                    let owner = min(1, max(0, trip.team / VersusRules.playerBase))
                    let r = cs * 0.62 * CGFloat(pose.scale)
                    rings[owner].addEllipse(in: CGRect(x: CGFloat(pose.x) * cs - r, y: CGFloat(pose.y) * cs - r,
                                                       width: 2 * r, height: 2 * r))
                }
            }
        }
        if ownerRings {
            for k in 0..<2 {
                ctx.stroke(rings[k], with: .color(Color(hex: playerColors[k]).opacity(0.85)), lineWidth: max(1, cs * 0.12))
            }
        }
        AntRenderer.draw(&ctx, visible: visible, board: b, cs: cs, sprites: sprites, detailed: detailed)
    }

    static func drawHill(_ ctx: inout GraphicsContext, board b: Board, hole: Int, cs: CGFloat) {
        let hx = (CGFloat(b.x(hole)) + 0.5) * cs
        let hy = (CGFloat(b.y(hole)) + 0.5) * cs
        let rings: [(CGFloat, CGFloat, UInt32)] = [(4.3, 2.4, 0x5C4632), (3.4, 1.9, 0x6E5440), (2.5, 1.4, 0x80654B)]
        for (rx, ry, col) in rings {
            let r = CGRect(x: hx - rx * cs, y: hy - ry * cs + 0.3 * cs, width: rx * 2 * cs, height: ry * 2 * cs)
            ctx.fill(Path(ellipseIn: r), with: .color(Color(hex: col)))
        }
        var crumbs = Path()
        for i in 0..<36 {
            let a = Double(hash32(i + hole, 11) % 6283) / 1000.0
            let rr = 2.0 + Double(hash32(i, 23) % 1000) / 1000.0 * 2.3
            let x = hx + CGFloat(rr * cos(a)) * cs
            let y = hy + CGFloat(rr * sin(a) * 0.55 + 0.3) * cs
            let s = cs * CGFloat(0.08 + Double(hash32(i, 37) % 100) / 1000.0)
            crumbs.addEllipse(in: CGRect(x: x - s, y: y - s, width: 2 * s, height: 2 * s))
        }
        ctx.fill(crumbs, with: .color(Color(hex: 0x927456)))
        ctx.fill(Path(ellipseIn: CGRect(x: hx - 1.05 * cs, y: hy - 0.62 * cs, width: 2.1 * cs, height: 1.24 * cs)),
                 with: .color(Color(hex: 0x18100B)))
        ctx.fill(Path(ellipseIn: CGRect(x: hx - 0.75 * cs, y: hy - 0.42 * cs, width: 1.5 * cs, height: 0.8 * cs)),
                 with: .color(Color(hex: 0x080503)))
    }
}
