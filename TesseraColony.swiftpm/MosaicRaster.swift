import CoreGraphics
import Foundation

@inline(__always) func hash32(_ a: Int, _ b: Int) -> UInt32 {
    var h = (UInt32(truncatingIfNeeded: a) &* 0x9E3779B1) ^ (UInt32(truncatingIfNeeded: b) &* 0x85EBCA77)
    h ^= h >> 15
    h = h &* 0x2C1B3C6D
    h ^= h >> 12
    h = h &* 0x297A2D39
    h ^= h >> 15
    return h
}

struct RGB {
    var r: Double
    var g: Double
    var b: Double
    init(_ hex: UInt32) {
        r = Double((hex >> 16) & 0xFF)
        g = Double((hex >> 8) & 0xFF)
        b = Double(hex & 0xFF)
    }
    init(r: Double, g: Double, b: Double) {
        self.r = r
        self.g = g
        self.b = b
    }
    func scaled(_ f: Double) -> RGB { RGB(r: r * f, g: g * f, b: b * f) }
    func mixed(with o: RGB, _ t: Double) -> RGB { RGB(r: r * (1 - t) + o.r * t, g: g * (1 - t) + o.g * t, b: b * (1 - t) + o.b * t) }
}

/// Paints the mosaic into a pixel buffer (one small bevelled tessera per tile, no markings) and turns it into a
/// CGImage. Tiles are stamped from pre-rendered templates, so a full repaint of ~7,000 cells is a
/// few thousand row copies. Mirrors Tools/render.py.
final class MosaicRaster {
    let board: Board
    let palette: LevelPalette
    let soil: UInt32
    let cellPx: Int
    let width: Int
    let height: Int
    private var pixels: [UInt8]
    /// What each cell currently shows: true = soil (open), false = tile.
    private(set) var shownOpen: [Bool]
    private var tileTemplates: [[UInt8]] = []   // (family*4+tone)*4 + jitter
    private var soilTemplates: [[UInt8]] = []   // 8 variants
    private var ghostTemplates: [[UInt8]] = []  // (family*4+tone)*8 + variant
    private(set) var image: CGImage?
    private var dirty = true

    static let soilVariants = 8

    init(board: Board, palette: LevelPalette, cellPx: Int, open: [Bool], soil: UInt32 = GeneratedPalette.soil) {
        self.board = board
        self.palette = palette
        self.soil = soil
        self.cellPx = max(3, cellPx)
        self.width = board.cols * max(3, cellPx)
        self.height = board.rows * max(3, cellPx)
        self.pixels = [UInt8](repeating: 255, count: board.cols * board.rows * max(3, cellPx) * max(3, cellPx) * 4)
        self.shownOpen = open
        buildTemplates()
        for i in 0..<board.count { paint(i, open: open[i]) }
        image = makeImage()
        dirty = false
    }

    // MARK: templates

    private func buildTemplates() {
        let s = cellPx
        let families = max(1, palette.familyCount)
        for f in 0..<families {
            for t in 0..<4 {
                let base = RGB(palette.tone(f, t))
                for j in 0..<4 {
                    let jit = [0.965, 0.988, 1.012, 1.035][j]
                    tileTemplates.append(MosaicRaster.tileTemplate(base: base, s: s, jitter: jit))
                }
            }
        }
        for v in 0..<MosaicRaster.soilVariants {
            soilTemplates.append(MosaicRaster.soilTemplate(s: s, variant: v, ghost: nil, soil: soil))
        }
        for f in 0..<families {
            for t in 0..<4 {
                let base = RGB(palette.tone(f, t))
                for v in 0..<MosaicRaster.soilVariants {
                    ghostTemplates.append(MosaicRaster.soilTemplate(s: s, variant: v, ghost: base, soil: soil))
                }
            }
        }
    }

    static func tileTemplate(base: RGB, s: Int, jitter: Double) -> [UInt8] {
        var out = [UInt8](repeating: 255, count: s * s * 4)
        let grout = RGB(GeneratedPalette.grout)
        let g = max(1, Int((Double(s) / 12).rounded()))
        let inner = s - g
        let b = max(1, Int((Double(s) / 10).rounded()))
        let rc = Double(s) * 0.16
        for v in 0..<s {
            for u in 0..<s {
                var col = grout
                if u < inner && v < inner {
                    let cxd = min(Double(u) + 0.5, Double(inner - u) - 0.5)
                    let cyd = min(Double(v) + 0.5, Double(inner - v) - 0.5)
                    let outside = cxd < rc && cyd < rc && (rc - cxd) * (rc - cxd) + (rc - cyd) * (rc - cyd) > rc * rc
                    if !outside {
                        var f = 1.0
                        if u < b || v < b { f = 1.16 }
                        if u >= inner - b || v >= inner - b { f = 0.80 }
                        f *= 1.05 - 0.10 * Double(v) / Double(inner)
                        col = base.scaled(f * jitter)
                    }
                }
                let o = (v * s + u) * 4
                out[o] = UInt8(max(0, min(255, col.r)))
                out[o + 1] = UInt8(max(0, min(255, col.g)))
                out[o + 2] = UInt8(max(0, min(255, col.b)))
                out[o + 3] = 255
            }
        }
        return out
    }

    static func soilTemplate(s: Int, variant: Int, ghost: RGB?, soil soilHex: UInt32) -> [UInt8] {
        var out = [UInt8](repeating: 255, count: s * s * 4)
        let soil = RGB(soilHex)
        for v in 0..<s {
            for u in 0..<s {
                let n = Double(hash32(variant * 131 + u, v * 7 + variant) & 0xFF) / 255.0
                var col = soil.scaled(0.92 + 0.16 * n)
                if n > 0.965 { col = col.scaled(1.3) }
                if let gh = ghost { col = col.mixed(with: gh, 0.14) }
                let o = (v * s + u) * 4
                out[o] = UInt8(max(0, min(255, col.r)))
                out[o + 1] = UInt8(max(0, min(255, col.g)))
                out[o + 2] = UInt8(max(0, min(255, col.b)))
                out[o + 3] = 255
            }
        }
        return out
    }

    // MARK: painting

    private func blit(_ tpl: [UInt8], cell i: Int) {
        let s = cellPx
        let cx = board.x(i) * s
        let cy = board.y(i) * s
        let rowBytes = s * 4
        let stride = width * 4
        pixels.withUnsafeMutableBytes { dst in
            tpl.withUnsafeBytes { src in
                guard let d = dst.baseAddress, let sb = src.baseAddress else { return }
                for row in 0..<s {
                    (d + (cy + row) * stride + cx * 4).copyMemory(from: sb + row * rowBytes, byteCount: rowBytes)
                }
            }
        }
    }

    private func paint(_ i: Int, open: Bool) {
        let fam = Int(board.family[i])
        let variant = Int(hash32(board.x(i), board.y(i)) % UInt32(MosaicRaster.soilVariants))
        if fam < 0 {
            blit(soilTemplates[variant], cell: i)
        } else {
            let code = fam * 4 + Int(board.tone[i])
            if open {
                blit(ghostTemplates[code * MosaicRaster.soilVariants + variant], cell: i)
            } else {
                let jit = Int(hash32(board.x(i) + 17, board.y(i) + 5) & 3)
                blit(tileTemplates[code * 4 + jit], cell: i)
            }
        }
        shownOpen[i] = open
    }

    /// Bring the picture in line with the scheduler: a tile disappears when its ant lifts it and
    /// reappears if an undo returns it. Returns true if the image changed.
    @discardableResult
    func sync(liftTime: [Double], now: Double) -> Bool {
        var changed = false
        for i in 0..<board.count where board.family[i] >= 0 {
            let open = liftTime[i] <= now
            if open != shownOpen[i] {
                paint(i, open: open)
                changed = true
            }
        }
        if changed {
            image = makeImage()
        }
        return changed
    }

    func makeImage() -> CGImage? {
        let data = Data(pixels)
        guard let provider = CGDataProvider(data: data as CFData) else { return nil }
        let space = CGColorSpace(name: CGColorSpace.sRGB) ?? CGColorSpaceCreateDeviceRGB()
        return CGImage(width: width, height: height, bitsPerComponent: 8, bitsPerPixel: 32,
                       bytesPerRow: width * 4, space: space,
                       bitmapInfo: CGBitmapInfo(rawValue: CGImageAlphaInfo.noneSkipLast.rawValue),
                       provider: provider, decode: nil, shouldInterpolate: false, intent: .defaultIntent)
    }

    // MARK: miniatures

    /// One pixel per art tile. `shown(i)` decides whether a tile is drawn (else dark mortar).
    static func miniature(board: Board, palette: LevelPalette, shown: (Int) -> Bool) -> CGImage? {
        let w = board.artWidth
        let h = board.artHeight
        var px = [UInt8](repeating: 255, count: w * h * 4)
        let mortar = RGB(0x2A2019)
        for y in 0..<h {
            for x in 0..<w {
                let i = (y + Board.marginTop) * board.cols + (x + Board.marginLeft)
                let f = Int(board.family[i])
                let col: RGB
                if f >= 0 && shown(i) {
                    col = RGB(palette.tone(f, Int(board.tone[i])))
                } else {
                    col = mortar
                }
                let o = (y * w + x) * 4
                px[o] = UInt8(max(0, min(255, col.r)))
                px[o + 1] = UInt8(max(0, min(255, col.g)))
                px[o + 2] = UInt8(max(0, min(255, col.b)))
                px[o + 3] = 255
            }
        }
        let data = Data(px)
        guard let provider = CGDataProvider(data: data as CFData) else { return nil }
        let space = CGColorSpace(name: CGColorSpace.sRGB) ?? CGColorSpaceCreateDeviceRGB()
        return CGImage(width: w, height: h, bitsPerComponent: 8, bitsPerPixel: 32, bytesPerRow: w * 4,
                       space: space, bitmapInfo: CGBitmapInfo(rawValue: CGImageAlphaInfo.noneSkipLast.rawValue),
                       provider: provider, decode: nil, shouldInterpolate: false, intent: .defaultIntent)
    }
}
