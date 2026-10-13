import SwiftUI
import UIKit

/// A photo mosaic saved on the device (Documents/PhotoMosaics/<id>.json).
struct PhotoLevelRecord: Codable {
    var id: String
    var title: String
    var created: Date
    var detail: PhotoDetail
    var art: [String]
    var palette: LevelPalette
    var tunnels: [[TeamSpec]]
    var solution: [Int]
    var chambersGentle: Int
    var chambersClassic: Int
    var chambersExpert: Int
    var subtitle: String

    init(level: LevelDefinition, detail: PhotoDetail, created: Date) {
        id = level.id
        title = level.title
        self.created = created
        self.detail = detail
        art = level.art
        palette = level.palette
        tunnels = level.tunnels
        solution = level.solution
        chambersGentle = level.chambersGentle
        chambersClassic = level.chambersClassic
        chambersExpert = level.chambersExpert
        subtitle = level.subtitle
    }

    var level: LevelDefinition {
        LevelDefinition(id: id, title: title, subtitle: subtitle, art: art, palette: palette, tunnels: tunnels,
                        chambersGentle: chambersGentle, chambersClassic: chambersClassic, chambersExpert: chambersExpert,
                        solution: solution, goldenClaimsPerMove: [], goldenClaimsHash: 0, goldenFinalStateHash: 0,
                        isPhoto: true)
    }
}

enum PhotoLibrary {
    private static var folder: URL? {
        guard let docs = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first else { return nil }
        let url = docs.appendingPathComponent("PhotoMosaics", isDirectory: true)
        try? FileManager.default.createDirectory(at: url, withIntermediateDirectories: true)
        return url
    }

    static func loadAll() -> [PhotoLevelRecord] {
        guard let dir = folder,
              let files = try? FileManager.default.contentsOfDirectory(at: dir, includingPropertiesForKeys: nil) else { return [] }
        var out: [PhotoLevelRecord] = []
        let decoder = JSONDecoder()
        for f in files where f.pathExtension == "json" {
            if let d = try? Data(contentsOf: f), let r = try? decoder.decode(PhotoLevelRecord.self, from: d) {
                out.append(r)
            }
        }
        return out.sorted { $0.created > $1.created }
    }

    static func save(_ r: PhotoLevelRecord) {
        guard let dir = folder, let d = try? JSONEncoder().encode(r) else { return }
        try? d.write(to: dir.appendingPathComponent(r.id + ".json"), options: .atomic)
    }

    static func delete(id: String) {
        guard let dir = folder else { return }
        try? FileManager.default.removeItem(at: dir.appendingPathComponent(id + ".json"))
    }

    /// Decode photo data into upright, opaque RGBA pixels (long side at most `maxSide`).
    /// Transparent areas are composited onto white (so they are treated as background).
    static func pixels(from data: Data, maxSide: CGFloat = 720) -> PixelImage? {
        guard let ui = UIImage(data: data), ui.size.width > 0, ui.size.height > 0 else { return nil }
        let scale = min(1, maxSide / max(ui.size.width, ui.size.height))
        let size = CGSize(width: max(1, (ui.size.width * scale).rounded()), height: max(1, (ui.size.height * scale).rounded()))
        let format = UIGraphicsImageRendererFormat()
        format.scale = 1
        format.opaque = true
        let rendered = UIGraphicsImageRenderer(size: size, format: format).image { ctx in
            UIColor.white.setFill()
            ctx.fill(CGRect(origin: .zero, size: size))
            ui.draw(in: CGRect(origin: .zero, size: size))   // respects the photo's orientation
        }
        guard let cg = rendered.cgImage else { return nil }
        let w = cg.width
        let h = cg.height
        var buf = [UInt8](repeating: 255, count: w * h * 4)
        let ok: Bool = buf.withUnsafeMutableBytes { ptr -> Bool in
            guard let c = CGContext(data: ptr.baseAddress, width: w, height: h, bitsPerComponent: 8, bytesPerRow: w * 4,
                                    space: CGColorSpaceCreateDeviceRGB(),
                                    bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue) else { return false }
            c.draw(cg, in: CGRect(x: 0, y: 0, width: w, height: h))
            return true
        }
        return ok ? PixelImage(width: w, height: h, rgba: buf) : nil
    }
}
