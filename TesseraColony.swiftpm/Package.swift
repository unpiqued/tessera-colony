// swift-tools-version: 5.9

// Tessera Colony — an app playground for Swift Playground (iPad) and Xcode.
// Swift 5 language mode is used on purpose (tools version 5.9) so the project builds
// with the Swift 6 compiler in Swift Playground 4.7 without strict-concurrency errors.
// Icon/accent colour are left to Swift Playground's App Settings (optional in the manifest).

import PackageDescription
import AppleProductTypes

let package = Package(
    name: "Tessera Colony",
    platforms: [
        .iOS("17.0")
    ],
    products: [
        .iOSApplication(
            name: "Tessera Colony",
            targets: ["AppModule"],
            bundleIdentifier: "com.example.tesseracolony",
            displayVersion: "0.1",
            bundleVersion: "1",
            supportedDeviceFamilies: [
                .pad,
                .phone
            ],
            supportedInterfaceOrientations: [
                .portrait,
                .landscapeRight,
                .landscapeLeft,
                .portraitUpsideDown(.when(deviceFamilies: [.pad]))
            ]
        )
    ],
    targets: [
        .executableTarget(
            name: "AppModule",
            path: "."
        )
    ]
)
