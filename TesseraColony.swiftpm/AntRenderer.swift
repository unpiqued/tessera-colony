import SwiftUI
import CoreGraphics

/// Pre-rendered cartoon ant bodies, one per tile colour. Each body is shaded with radial
/// gradients, outlined, and has big eyes and antennae; legs are drawn live (see AntRenderer)
/// so the feet can plant and lift in step with the ground speed.
final class AntSpriteCache {
    /// Sprite extent in cell units (ant faces +x, origin at the thorax).
    static let minX: CGFloat = -0.9
    static let maxX: CGFloat = 1.0
    static let minY: CGFloat = -0.44
    static let maxY: CGFloat = 0.44
    static let pxPerCell: CGFloat = 72

    private var cache: [UInt32: CGImage] = [:]

    func sprite(for color: UInt32) -> CGImage? {
        if let c = cache[color] { return c }
        let img = AntSpriteCache.render(color: color)
        if let img = img { cache[color] = img }
        return img
    }

    static var extent: CGRect { CGRect(x: minX, y: minY, width: maxX - minX, height: maxY - minY) }

    private static func cg(_ r: Double, _ g: Double, _ b: Double, _ a: Double = 1) -> CGColor {
        CGColor(red: CGFloat(max(0, min(1, r))), green: CGFloat(max(0, min(1, g))), blue: CGFloat(max(0, min(1, b))), alpha: CGFloat(a))
    }

    static func render(color: UInt32) -> CGImage? {
        let w = Int((maxX - minX) * pxPerCell)
        let h = Int((maxY - minY) * pxPerCell)
        let space = CGColorSpaceCreateDeviceRGB()
        guard let ctx = CGContext(data: nil, width: w, height: h, bitsPerComponent: 8, bytesPerRow: 0,
                                  space: space, bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue) else { return nil }
        // Top-left origin, 1 unit = 1 cell.
        ctx.translateBy(x: 0, y: CGFloat(h))
        ctx.scaleBy(x: 1, y: -1)
        ctx.scaleBy(x: pxPerCell, y: pxPerCell)
        ctx.translateBy(x: -minX, y: -minY)
        ctx.setLineCap(.round)
        ctx.setLineJoin(.round)

        let r = Double((color >> 16) & 0xFF) / 255
        let g = Double((color >> 8) & 0xFF) / 255
        let b = Double(color & 0xFF) / 255
        func shade(_ f: Double) -> (Double, Double, Double) { (r * f, g * f, b * f) }
        func tint(_ t: Double) -> (Double, Double, Double) { (r + (1 - r) * t, g + (1 - g) * t, b + (1 - b) * t) }
        let outline = shade(0.32)

        func part(_ cx: CGFloat, _ cy: CGFloat, _ rx: CGFloat, _ ry: CGFloat, body f: Double) {
            let rect = CGRect(x: cx - rx, y: cy - ry, width: 2 * rx, height: 2 * ry)
            let lite = tint(0.5)
            let mid = shade(f)
            let deep = shade(f * 0.55)
            let colors = [cg(lite.0, lite.1, lite.2), cg(mid.0, mid.1, mid.2), cg(deep.0, deep.1, deep.2)] as CFArray
            let locs: [CGFloat] = [0, 0.5, 1]
            ctx.saveGState()
            ctx.addEllipse(in: rect)
            ctx.clip()
            if let grad = CGGradient(colorsSpace: space, colors: colors, locations: locs) {
                ctx.drawRadialGradient(grad,
                                       startCenter: CGPoint(x: cx - rx * 0.3, y: cy - ry * 0.4), startRadius: 0,
                                       endCenter: CGPoint(x: cx, y: cy), endRadius: max(rx, ry) * 1.05,
                                       options: [.drawsAfterEndLocation])
            }
            ctx.restoreGState()
            ctx.setStrokeColor(cg(outline.0, outline.1, outline.2))
            ctx.setLineWidth(0.035)
            ctx.strokeEllipse(in: rect)
            // glossy highlight
            ctx.setFillColor(cg(1, 1, 1, 0.55))
            ctx.fillEllipse(in: CGRect(x: cx - rx * 0.55, y: cy - ry * 0.72, width: rx * 0.55, height: ry * 0.38))
        }

        // antennae first (they sit under the head's outline where they attach)
        ctx.setStrokeColor(cg(outline.0, outline.1, outline.2))
        ctx.setLineWidth(0.04)
        for s in [CGFloat(-1), CGFloat(1)] {
            ctx.move(to: CGPoint(x: 0.5, y: s * 0.09))
            ctx.addQuadCurve(to: CGPoint(x: 0.86, y: s * 0.24), control: CGPoint(x: 0.64, y: s * 0.3))
            ctx.strokePath()
            let tip = shade(0.9)
            ctx.setFillColor(cg(tip.0, tip.1, tip.2))
            ctx.fillEllipse(in: CGRect(x: 0.86 - 0.045, y: s * 0.24 - 0.045, width: 0.09, height: 0.09))
            ctx.setStrokeColor(cg(outline.0, outline.1, outline.2))
            ctx.setLineWidth(0.025)
            ctx.strokeEllipse(in: CGRect(x: 0.86 - 0.045, y: s * 0.24 - 0.045, width: 0.09, height: 0.09))
            ctx.setLineWidth(0.04)
        }
        part(-0.44, 0, 0.36, 0.27, body: 1.0)     // gaster
        part(-0.07, 0, 0.08, 0.055, body: 0.7)    // petiole
        part(0.07, 0, 0.17, 0.12, body: 0.88)     // thorax
        part(0.4, 0, 0.2, 0.19, body: 0.92)       // head
        // mandibles
        ctx.setStrokeColor(cg(outline.0, outline.1, outline.2))
        ctx.setLineWidth(0.035)
        for s in [CGFloat(-1), CGFloat(1)] {
            ctx.move(to: CGPoint(x: 0.56, y: s * 0.06))
            ctx.addQuadCurve(to: CGPoint(x: 0.64, y: s * 0.01), control: CGPoint(x: 0.64, y: s * 0.07))
            ctx.strokePath()
        }
        // big cartoon eyes
        for s in [CGFloat(-1), CGFloat(1)] {
            let eye = CGRect(x: 0.47 - 0.07, y: s * 0.085 - 0.075, width: 0.14, height: 0.15)
            ctx.setFillColor(cg(1, 1, 1))
            ctx.fillEllipse(in: eye)
            ctx.setStrokeColor(cg(outline.0, outline.1, outline.2))
            ctx.setLineWidth(0.02)
            ctx.strokeEllipse(in: eye)
            ctx.setFillColor(cg(0.06, 0.04, 0.03))
            ctx.fillEllipse(in: CGRect(x: 0.505 - 0.038, y: s * 0.08 - 0.038, width: 0.076, height: 0.076))
            ctx.setFillColor(cg(1, 1, 1, 0.9))
            ctx.fillEllipse(in: CGRect(x: 0.49 - 0.014, y: s * 0.08 - 0.03, width: 0.028, height: 0.028))
        }
        return ctx.makeImage()
    }
}

/// Draws every visible ant in a few batched passes: shadows, legs, bodies, carried tiles.
enum AntRenderer {
    /// Distance travelled (cells) per full stride cycle. Gait phase = distance / stride, so a
    /// slower game speed automatically means slower steps, and stance feet stay planted.
    static let strideLength = 0.8
    static let hips: [(Double, Double)] = [(0.13, 0.07), (0.05, 0.1), (-0.03, 0.08)]
    static let feet: [(Double, Double)] = [(0.47, 0.44), (0.05, 0.53), (-0.4, 0.46)]
    /// Front knees bend forward, hind knees backward.
    static let kneeBias: [Double] = [0.06, 0, -0.06]
    /// A darker (planted) or lighter (lifted, nearer the viewer) shade of the ant's own colour.
    static func legShade(_ color: UInt32, _ f: Double) -> Color {
        let r = Double((color >> 16) & 0xFF) / 255 * f
        let g = Double((color >> 8) & 0xFF) / 255 * f
        let b = Double(color & 0xFF) / 255 * f
        return Color(.sRGB, red: r, green: g, blue: b, opacity: 1)
    }

    struct Visible {
        let trip: AntTrip
        let pose: AntPose
    }

    static func draw(_ ctx: inout GraphicsContext, visible: [Visible], board: Board, cs: CGFloat,
                     sprites: AntSpriteCache, detailed: Bool) {
        if visible.isEmpty { return }
        let lod = detailed && visible.count <= 320
        var shadows = Path()
        // legs are batched per ant colour (a darker shade of the body) so they read on dark soil
        var planted: [UInt32: Path] = [:]
        var lifted: [UInt32: Path] = [:]
        var footDots: [UInt32: Path] = [:]
        for v in visible {
            let p = v.pose
            let color = v.trip.color
            let k = p.scale
            let ch = cos(p.heading), sh = sin(p.heading)
            func world(_ bx: Double, _ by: Double) -> CGPoint {
                CGPoint(x: CGFloat(p.x + (bx * ch - by * sh) * k) * cs, y: CGFloat(p.y + (bx * sh + by * ch) * k) * cs)
            }
            // soft contact shadow, offset down-right in world space
            let sc = CGPoint(x: CGFloat(p.x + 0.05) * cs, y: CGFloat(p.y + 0.12) * cs)
            let shadowRect = CGRect(x: -0.82 * cs * CGFloat(k), y: -0.3 * cs * CGFloat(k), width: 1.64 * cs * CGFloat(k), height: 0.6 * cs * CGFloat(k))
            shadows.addEllipse(in: shadowRect, transform: CGAffineTransform(translationX: sc.x, y: sc.y).rotated(by: CGFloat(p.heading)))
            // legs: alternating tripods, stance feet move backwards at ground speed (planted)
            let phase = p.gaitDistance / strideLength
            for i in 0..<3 {
                for s in [-1.0, 1.0] {
                    let tripodA = (i == 1) ? (s < 0) : (s > 0)
                    var q = phase + (tripodA ? 0 : 0.5)
                    q -= q.rounded(.down)
                    var off: Double
                    var lift = 0.0
                    if q < 0.5 {
                        off = strideLength / 4 - (q / 0.5) * strideLength / 2
                    } else {
                        let tt = (q - 0.5) / 0.5
                        off = -strideLength / 4 + AntGeometry.smooth(tt) * strideLength / 2
                        lift = sin(Double.pi * tt)
                    }
                    if !p.moving { off *= 0.4; lift = 0 }
                    let hip = (hips[i].0, s * hips[i].1)
                    let foot = (feet[i].0 + off, s * (feet[i].1 + 0.06 * lift))
                    let kneeX: Double = (hip.0 + foot.0) / 2 + kneeBias[i]
                    let kneeY: Double = (hip.1 + foot.1) / 2 + s * (0.2 + 0.1 * lift)
                    let knee = (kneeX, kneeY)
                    let a = world(hip.0, hip.1)
                    if lod {
                        let bpt = world(knee.0, knee.1)
                        let c = world(foot.0, foot.1)
                        if lift > 0.05 {
                            lifted[color, default: Path()].move(to: a)
                            lifted[color, default: Path()].addLine(to: bpt)
                            lifted[color, default: Path()].addLine(to: c)
                        } else {
                            planted[color, default: Path()].move(to: a)
                            planted[color, default: Path()].addLine(to: bpt)
                            planted[color, default: Path()].addLine(to: c)
                            let r = 0.05 * cs * CGFloat(k)
                            footDots[color, default: Path()].addEllipse(in: CGRect(x: c.x - r, y: c.y - r, width: 2 * r, height: 2 * r))
                        }
                    } else {
                        planted[color, default: Path()].move(to: a)
                        planted[color, default: Path()].addLine(to: world(foot.0, foot.1))
                    }
                }
            }
        }
        ctx.fill(shadows, with: .color(Color.black.opacity(0.24)))
        let plantedStyle = StrokeStyle(lineWidth: max(0.6, 0.085 * cs), lineCap: .round, lineJoin: .round)
        let liftedStyle = StrokeStyle(lineWidth: max(0.5, 0.065 * cs), lineCap: .round, lineJoin: .round)
        for (color, path) in planted {
            ctx.stroke(path, with: .color(legShade(color, 0.55)), style: plantedStyle)
        }
        if lod {
            for (color, path) in lifted {
                ctx.stroke(path, with: .color(legShade(color, 0.72)), style: liftedStyle)
            }
            for (color, path) in footDots {
                ctx.fill(path, with: .color(legShade(color, 0.4)))
            }
        }

        // bodies (cartoon sprites) with a little sway and bob from the gait
        var resolved: [UInt32: GraphicsContext.ResolvedImage] = [:]
        let ext = AntSpriteCache.extent
        let rect = CGRect(x: ext.minX * cs, y: ext.minY * cs, width: ext.width * cs, height: ext.height * cs)
        var carried: [UInt32: Path] = [:]
        var carriedEdges = Path()
        for v in visible {
            let p = v.pose
            let color = v.trip.color
            if resolved[color] == nil, let img = sprites.sprite(for: color) {
                resolved[color] = ctx.resolve(Image(decorative: img, scale: 1))
            }
            let phase = p.gaitDistance / strideLength
            let sway = p.moving ? 0.07 * sin(2 * Double.pi * 2 * phase) : 0
            let bob = p.moving ? 1 + 0.03 * sin(2 * Double.pi * 2 * phase + Double.pi / 2) : 1
            let lean = p.moving ? 0.0 : 0.06 * sin(Double.pi * p.liftProgress)
            var c = ctx
            c.translateBy(x: CGFloat(p.x + cos(p.heading) * lean) * cs, y: CGFloat(p.y + sin(p.heading) * lean) * cs)
            c.rotate(by: .radians(p.heading + sway))
            c.scaleBy(x: CGFloat(p.scale * bob), y: CGFloat(p.scale * bob))
            if p.scale < 1 { c.opacity = 0.35 + 0.65 * p.scale }
            if let img = resolved[color] {
                c.draw(img, in: rect)
            }
            // tile: rising from the floor into the jaws, then carried in front of the head
            if p.liftProgress > 0 {
                let jawX = p.x + cos(p.heading) * 0.72 * p.scale
                let jawY = p.y + sin(p.heading) * 0.72 * p.scale
                var tx = jawX, ty = jawY
                var size = 0.5 * p.scale
                if !p.carrying {
                    let tile = Int(v.trip.tile)
                    let fx = Double(board.x(tile)) + 0.5, fy = Double(board.y(tile)) + 0.5
                    let e = p.liftProgress
                    tx = fx + (jawX - fx) * e
                    ty = fy + (jawY - fy) * e
                    size = 0.9 - 0.4 * e
                }
                let half = CGFloat(size) * cs / 2
                let r = CGRect(x: CGFloat(tx) * cs - half, y: CGFloat(ty) * cs - half, width: 2 * half, height: 2 * half)
                let tilePath = Path(roundedRect: r, cornerRadius: half * 0.3)
                carried[color, default: Path()].addPath(tilePath)
                carriedEdges.addPath(tilePath)
            }
        }
        for (color, path) in carried {
            ctx.fill(path, with: .color(Color(hex: color)))
        }
        ctx.stroke(carriedEdges, with: .color(Color.black.opacity(0.45)), lineWidth: max(0.5, 0.05 * cs))
    }
}
