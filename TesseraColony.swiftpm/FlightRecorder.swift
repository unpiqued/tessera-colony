import SwiftUI
import UIKit

/// A small flight recorder for play sessions (added after the Alhambra Tiles crash report, 3 Oct).
///
/// While a game is open, the mosaic, difficulty, harder options, ant-path style, speed, the move list,
/// a status line and the last 60 actions are kept in a little text file. A normal exit (Home, a
/// finished mosaic, the app going to the background) marks the file closed. If the app ever stops
/// while a game is open, the next launch keeps the file as a report that Home offers to copy — enough
/// to replay that exact game in the reference model (Tools/) and find what went wrong.
/// The in-app self-test uses it too, so a test that stops the app leaves its last step behind.
final class FlightRecorder: @unchecked Sendable {
    static let shared = FlightRecorder()
    static let build = "3 Oct 2026"

    private let lock = NSLock()
    private var header: [String] = []
    private var events: [String] = []
    private var moves: [Int] = []
    private var status = ""
    private var isOpen = false
    private var suspended = false
    private static let openMark = "OPEN\n"
    private static let closedMark = "CLOSED\n"

    private init() {}

    private var folder: URL? {
        guard let base = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first else { return nil }
        let url = base.appendingPathComponent("FlightRecorder", isDirectory: true)
        try? FileManager.default.createDirectory(at: url, withIntermediateDirectories: true)
        return url
    }
    private var sessionURL: URL? { folder?.appendingPathComponent("session.txt") }
    private var reportURL: URL? { folder?.appendingPathComponent("report.txt") }

    // MARK: launch

    /// Called once at launch: a session file still marked open means the app stopped mid-game (or
    /// mid-self-test) last time. It becomes the report Home offers to copy.
    func launchCheck() {
        lock.lock()
        defer { lock.unlock() }
        guard let s = sessionURL, let text = try? String(contentsOf: s, encoding: .utf8) else { return }
        if text.hasPrefix(FlightRecorder.openMark), let r = reportURL {
            try? FileManager.default.removeItem(at: r)
            try? String(text.dropFirst(FlightRecorder.openMark.count)).write(to: r, atomically: true, encoding: .utf8)
        }
        try? FileManager.default.removeItem(at: s)
    }

    /// The report left by a session that didn't close normally, if any.
    var pendingReport: String? {
        lock.lock()
        defer { lock.unlock() }
        guard let r = reportURL, let text = try? String(contentsOf: r, encoding: .utf8), !text.isEmpty else { return nil }
        return text
    }

    func dismissReport() {
        lock.lock()
        defer { lock.unlock() }
        if let r = reportURL { try? FileManager.default.removeItem(at: r) }
    }

    // MARK: recording

    /// A game (or the self-test) starts: `lines` describe it.
    func begin(_ lines: [String], moves m: [Int] = []) {
        lock.lock()
        defer { lock.unlock() }
        header = ["Tessera Colony flight record · build \(FlightRecorder.build)"] + lines
        events = []
        moves = m
        status = ""
        isOpen = true
        suspended = false
        flush()
    }

    /// One action, at game time `time` (seconds). `moves` = the game's move list after it.
    func note(_ text: String, time: Double, moves m: [Int]? = nil) {
        lock.lock()
        defer { lock.unlock() }
        guard isOpen else { return }
        let t = time.isFinite ? String(format: "%9.2f", time) : "        ?"
        events.append(t + "  " + text)
        if events.count > 60 { events.removeFirst(events.count - 60) }
        if let m = m { moves = m }
        flush()
    }

    /// The latest state of the game (written every couple of seconds while playing).
    func update(status s: String, moves m: [Int]) {
        lock.lock()
        defer { lock.unlock() }
        guard isOpen else { return }
        status = s
        moves = m
        flush()
    }

    /// The game closed normally (Home, finished, restarted into a new session, self-test done).
    func end() {
        lock.lock()
        defer { lock.unlock() }
        isOpen = false
        suspended = false
        if let s = sessionURL { try? FileManager.default.removeItem(at: s) }
    }

    /// The app went to the background: if iOS closes it there, that is not a crash.
    func suspend() {
        lock.lock()
        defer { lock.unlock() }
        guard isOpen else { return }
        suspended = true
        flush()
    }

    /// The app is in front again.
    func resume() {
        lock.lock()
        defer { lock.unlock() }
        guard isOpen, suspended else { return }
        suspended = false
        flush()
    }

    /// Writes the session file (the caller holds the lock).
    private func flush() {
        guard let s = sessionURL else { return }
        var text = suspended ? FlightRecorder.closedMark : FlightRecorder.openMark
        text += header.joined(separator: "\n") + "\n"
        text += "Moves so far (\(moves.count)): " + moves.map { String($0) }.joined(separator: ",") + "\n"
        if !status.isEmpty { text += "Last status: " + status + "\n" }
        text += "Last actions (game time in seconds):\n" + events.joined(separator: "\n") + "\n"
        try? text.write(to: s, atomically: true, encoding: .utf8)
    }
}

/// Home's notice after the app stopped unexpectedly: copy the report or dismiss it.
struct CrashReportBanner: View {
    let report: String
    let onDismiss: () -> Void
    @State private var copied = false
    @State private var showText = false

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(alignment: .top, spacing: 12) {
                Image(systemName: "exclamationmark.bubble.fill")
                    .font(.system(size: 24, weight: .bold))
                    .foregroundStyle(Theme.brass)
                VStack(alignment: .leading, spacing: 4) {
                    Text("Last time, the game didn't close normally")
                        .font(Theme.title(18))
                        .foregroundStyle(Theme.sand)
                    Text("If the app crashed, please copy this report and paste it to Claude — it lists the mosaic, your settings and your last moves, so the exact game can be replayed and the cause found. (It also appears if the app was stopped from Swift Playground mid-game.)")
                        .font(Theme.label(13))
                        .foregroundStyle(Theme.sandDim)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
            HStack(spacing: 10) {
                Button {
                    UIPasteboard.general.string = report
                    copied = true
                } label: {
                    Label(copied ? "Copied" : "Copy report", systemImage: copied ? "checkmark" : "doc.on.doc")
                }
                .buttonStyle(PillButtonStyle(prominent: true))
                Button("Show") { showText = true }
                    .buttonStyle(PillButtonStyle(prominent: false))
                Button("Dismiss", action: onDismiss)
                    .buttonStyle(PillButtonStyle(prominent: false))
            }
        }
        .padding(16)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(RoundedRectangle(cornerRadius: 16, style: .continuous).fill(Theme.panel))
        .overlay(RoundedRectangle(cornerRadius: 16, style: .continuous).strokeBorder(Theme.brass.opacity(0.7), lineWidth: 1.5))
        .sheet(isPresented: $showText) {
            NavigationStack {
                ScrollView {
                    Text(report)
                        .font(.system(size: 12, design: .monospaced))
                        .foregroundStyle(Theme.sand)
                        .textSelection(.enabled)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(16)
                }
                .background(Theme.loam.ignoresSafeArea())
                .navigationTitle("Crash report")
                .navigationBarTitleDisplayMode(.inline)
                .toolbar {
                    ToolbarItem(placement: .confirmationAction) {
                        Button("Copy") {
                            UIPasteboard.general.string = report
                            copied = true
                        }
                    }
                }
            }
            .preferredColorScheme(.dark)
        }
    }
}
