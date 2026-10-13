import SwiftUI
import UIKit

/// Visual language: warm loam backgrounds, sandstone panels, brass accents,
/// New York (serif) for titles and SF Rounded for numbers.
enum Theme {
    static let loam = Color(hex: 0x1C1511)
    static let loamRaised = Color(hex: 0x271D17)
    static let panel = Color(hex: 0x2F241C)
    static let panelEdge = Color(hex: 0x4A3A2C)
    static let sand = Color(hex: 0xE9DCC3)
    static let sandDim = Color(hex: 0xB8A98F)
    static let brass = Color(hex: 0xD9A441)
    static let brassDeep = Color(hex: 0xA8772A)
    static let terracotta = Color(hex: 0xC8643B)
    static let danger = Color(hex: 0xE0563A)
    static let ok = Color(hex: 0x8CC56A)

    static func title(_ size: CGFloat) -> Font { .system(size: size, weight: .semibold, design: .serif) }
    static func number(_ size: CGFloat) -> Font { .system(size: size, weight: .bold, design: .rounded) }
    static func label(_ size: CGFloat, weight: Font.Weight = .medium) -> Font { .system(size: size, weight: weight, design: .rounded) }
}

/// Ground colours offered for the area behind the mosaic (the player can also pick any colour).
enum GroundPresets {
    static let all: [(String, UInt32)] = [
        ("Loam", 0x3A2D22), ("Night", 0x161A24), ("Slate", 0x333A45), ("Moss", 0x2E3A28),
        ("Plum", 0x3B2637), ("Clay", 0x7A4A36), ("Sand", 0xC9B48A), ("Chalk", 0xE7E2D6)
    ]

    /// A darker version of a ground colour for the screen around the board.
    static func backdrop(_ hex: UInt32) -> Color {
        let r = Double((hex >> 16) & 0xFF) / 255, g = Double((hex >> 8) & 0xFF) / 255, b = Double(hex & 0xFF) / 255
        return Color(.sRGB, red: r * 0.5, green: g * 0.5, blue: b * 0.5, opacity: 1)
    }
}

extension Color {
    /// 0xRRGGBB of this colour in sRGB (used to store a picked ground colour).
    func rgbHex() -> UInt32 {
        let ui = UIColor(self)
        var r: CGFloat = 0, g: CGFloat = 0, b: CGFloat = 0, a: CGFloat = 0
        ui.getRed(&r, green: &g, blue: &b, alpha: &a)
        func c(_ v: CGFloat) -> UInt32 { UInt32(max(0, min(255, (v * 255).rounded()))) }
        return (c(r) << 16) | (c(g) << 8) | c(b)
    }

    init(hex: UInt32, opacity: Double = 1) {
        self.init(.sRGB,
                  red: Double((hex >> 16) & 0xFF) / 255,
                  green: Double((hex >> 8) & 0xFF) / 255,
                  blue: Double(hex & 0xFF) / 255,
                  opacity: opacity)
    }
}

/// Colours for team controls, taken straight from the level's own glaze tones so a team piece
/// looks like the tiles it collects. No symbols are drawn on coloured pieces.
enum FamilyStyle {
    static func tone(_ p: LevelPalette, _ f: Int, _ t: Int) -> Color { Color(hex: p.tone(f, t)) }
    static func swatch(_ p: LevelPalette, _ f: Int) -> Color { tone(p, f, 1) }
    static func swatchDeep(_ p: LevelPalette, _ f: Int) -> Color { tone(p, f, 2) }
    /// Dark ink on light families, light ink on dark ones (for the numbers only).
    static func ink(_ p: LevelPalette, _ f: Int) -> Color {
        p.luminance(f) > 0.42 ? Color(hex: 0x24170F) : Color.white
    }
    static func inkShadow(_ p: LevelPalette, _ f: Int) -> Color {
        p.luminance(f) > 0.42 ? Color.white.opacity(0.35) : Color.black.opacity(0.45)
    }
}
