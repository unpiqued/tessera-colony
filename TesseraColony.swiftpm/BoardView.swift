import SwiftUI

/// The play field: cached mosaic bitmap + vector ant hill + animated ants, drawn every frame
/// in a Canvas while anything is moving. Pinch to zoom, drag to pan, double-tap to reset.
struct BoardView: View {
    @ObservedObject var controller: GameController
    /// Points per cell at zoom 1 (chosen by the layout).
    let cell: CGFloat

    @Environment(\.displayScale) private var displayScale
    @State private var zoom: CGFloat = 1
    @State private var zoomBase: CGFloat = 1
    @State private var pan: CGSize = .zero
    @State private var panBase: CGSize = .zero

    private var boardSize: CGSize {
        CGSize(width: CGFloat(controller.board.cols) * cell, height: CGFloat(controller.board.rows) * cell)
    }

    var body: some View {
        TimelineView(.animation(minimumInterval: nil, paused: !controller.animating)) { timeline in
            Canvas { ctx, _ in
                draw(&ctx, date: timeline.date)
            }
        }
        .frame(width: boardSize.width, height: boardSize.height)
        .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 12, style: .continuous)
                .strokeBorder(controller.isBlocked ? Theme.danger : Theme.panelEdge, lineWidth: controller.isBlocked ? 3 : 1)
        )
        .contentShape(Rectangle())
        .gesture(
            SimultaneousGesture(
                MagnifyGesture()
                    .onChanged { value in
                        zoom = min(4, max(1, zoomBase * value.magnification))
                        pan = clampedPan(pan)
                    }
                    .onEnded { _ in
                        zoomBase = zoom
                        pan = clampedPan(pan)
                        panBase = pan
                    },
                DragGesture(minimumDistance: 6)
                    .onChanged { value in
                        guard zoom > 1.01 else { return }
                        pan = clampedPan(CGSize(width: panBase.width + value.translation.width,
                                                height: panBase.height + value.translation.height))
                    }
                    .onEnded { _ in panBase = pan }
            )
        )
        .onTapGesture(count: 2) {
            withAnimation(.easeOut(duration: 0.25)) {
                zoom = 1
                zoomBase = 1
                pan = .zero
                panBase = .zero
            }
        }
        .accessibilityElement()
        .accessibilityLabel("Mosaic board, \(controller.board.tileCount - controller.claimedCount) tiles left to claim")
    }

    private func clampedPan(_ p: CGSize) -> CGSize {
        let mx = (zoom - 1) * boardSize.width / 2
        let my = (zoom - 1) * boardSize.height / 2
        return CGSize(width: min(mx, max(-mx, p.width)), height: min(my, max(-my, p.height)))
    }

    // MARK: - Drawing

    private func draw(_ ctx: inout GraphicsContext, date: Date) {
        let b = controller.board
        let cs = cell
        let t = controller.gameTime(at: date)
        let px = max(3, Int((cs * displayScale).rounded()))
        controller.ensureRaster(cellPx: px)
        let w = boardSize.width
        let h = boardSize.height

        ctx.translateBy(x: pan.width + w / 2, y: pan.height + h / 2)
        ctx.scaleBy(x: zoom, y: zoom)
        ctx.translateBy(x: -w / 2, y: -h / 2)

        // 1-3. Mosaic bitmap, the ant hill, lifted tiles and the glow on claimed tiles.
        let trips = controller.scheduler.trips
        BoardPainter.paintBase(&ctx, board: b, cs: cs, t: t, date: date, size: CGSize(width: w, height: h),
                               raster: controller.raster, trips: trips, ground: controller.groundColor,
                               holes: [b.hole], sharp: zoom > 1.3)

        // 4. Scout preview: dim everything except the tiles this team would take.
        if controller.scout != nil {
            var mask = Path()
            mask.addRect(CGRect(x: 0, y: 0, width: w, height: h))
            var ring = Path()
            for tile in controller.scoutTiles {
                let i = Int(tile)
                let r = CGRect(x: CGFloat(b.x(i)) * cs, y: CGFloat(b.y(i)) * cs, width: cs, height: cs)
                mask.addRect(r)
                ring.addRect(r.insetBy(dx: cs * 0.06, dy: cs * 0.06))
            }
            ctx.fill(mask, with: .color(Color.black.opacity(0.5)), style: FillStyle(eoFill: true))
            ctx.stroke(ring, with: .color(Theme.brass), lineWidth: max(1, cs * 0.14))
        }

        // 4b-5. Scout trails and the ants.
        BoardPainter.paintAnts(&ctx, board: b, cs: cs, t: t, trips: trips, sprites: controller.sprites,
                               detailed: controller.detailedAnts && cs * zoom >= 5, ownerRings: false)
    }
}
