import SwiftUI

/// Home → High scores: the top five per mosaic, solo or two-player.
struct HighScoresView: View {
    @EnvironmentObject var app: AppModel
    @Environment(\.dismiss) private var dismiss
    @State private var kind: HighScoreKind = .solo
    @State private var confirmClear = false

    private var levelsWithScores: [LevelDefinition] {
        app.allLevels.filter { !app.topScores(kind, levelID: $0.id).isEmpty }
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    Picker("Table", selection: $kind) {
                        ForEach(HighScoreKind.allCases) { k in Text(k.title).tag(k) }
                    }
                    .pickerStyle(.segmented)
                    Text(kind == .solo ? soloRules : versusRules)
                        .font(Theme.label(13))
                        .foregroundStyle(Theme.sandDim)
                        .fixedSize(horizontal: false, vertical: true)
                    if levelsWithScores.isEmpty {
                        VStack(spacing: 10) {
                            Image(systemName: "trophy")
                                .font(.system(size: 40))
                                .foregroundStyle(Theme.panelEdge)
                            Text(kind == .solo ? "No high scores yet. Finish a mosaic and put your name on its table."
                                               : "No two-player high scores yet. The winner of a match can save theirs.")
                                .font(Theme.label(15))
                                .foregroundStyle(Theme.sand)
                                .multilineTextAlignment(.center)
                        }
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 40)
                    }
                    ForEach(levelsWithScores, id: \.id) { level in
                        VStack(alignment: .leading, spacing: 8) {
                            HStack(spacing: 12) {
                                if let img = app.thumbnail(for: level) {
                                    Image(decorative: img, scale: 1)
                                        .resizable()
                                        .interpolation(.none)
                                        .aspectRatio(contentMode: .fit)
                                        .frame(width: 44, height: 50)
                                        .clipShape(RoundedRectangle(cornerRadius: 6))
                                }
                                VStack(alignment: .leading, spacing: 2) {
                                    Text(level.title)
                                        .font(Theme.title(19))
                                        .foregroundStyle(Theme.sand)
                                    Text("\(level.tileCount) tiles")
                                        .font(Theme.label(12))
                                        .foregroundStyle(Theme.sandDim)
                                }
                            }
                            HighScoreList(entries: app.topScores(kind, levelID: level.id))
                        }
                        .padding(14)
                        .background(RoundedRectangle(cornerRadius: 16, style: .continuous).fill(Theme.panel))
                        .overlay(RoundedRectangle(cornerRadius: 16, style: .continuous).strokeBorder(Theme.panelEdge, lineWidth: 1))
                    }
                }
                .padding(20)
                .frame(maxWidth: 760)
                .frame(maxWidth: .infinity)
            }
            .background(Theme.loam.ignoresSafeArea())
            .navigationTitle("High scores")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button("Done") { dismiss() }
                }
                ToolbarItem(placement: .cancellationAction) {
                    Button("Clear…", role: .destructive) { confirmClear = true }
                        .disabled(app.highScores.isEmpty)
                }
            }
            .alert("Clear all high scores?", isPresented: $confirmClear) {
                Button("Clear", role: .destructive) { app.clearHighScores() }
                Button("Cancel", role: .cancel) {}
            } message: {
                Text("Both the solo and two-player tables are emptied. Finished mosaics and best times are kept.")
            }
        }
        .preferredColorScheme(.dark)
    }

    private var soloRules: String {
        "Score = tiles × difficulty (Gentle ×0.5, Classic ×1, Expert ×1.5) × harder options (up to ×2), minus 5 per undo, 25 per hint and 25 per assist. Ties go to the faster time. Each mosaic keeps its top 5."
    }

    private var versusRules: String {
        "The winner's match score (tiles home, finish bonus, minus penalties). Each mosaic keeps its top 5 with the options that were played."
    }
}
