# Tessera Colony on iPhone: getting there without a Mac

*Researched 5 October 2026. Project checked: `TesseraColony.swiftpm` (Package.swift, GameView, HomeView, BoardView, VersusView, SoundBoard, SaveStore, MosaicRaster, FlightRecorder). No project files were changed. Numbers in brackets link to the Sources list at the end. Time figures marked "estimate" are my own judgement, not published figures.*

---

## Recommended path

**Short answer:** There is no free way to put the app on your iPhone without a Mac. The shortest reliable route is the one Swift Playground was built for:

1. Join the Apple Developer Program.
2. Upload from Swift Playground on the iPad to App Store Connect.
3. Install the build on the iPhone through TestFlight, as an **internal tester**. Internal testers don't need Beta App Review.

The same setup later becomes your App Store submission.

| # | Step | Cost | Time |
|---|------|------|------|
| 0 | **Preview the phone layout on the iPad (free, start now).** iPadOS 26 lets you resize app windows freely [[74]][74]. Make the Swift Playground window narrow and run the app. The game screen switches to its stacked "compact" layout when the width is no more than 1.05 × the height (`GameView.swift` line 13). Home switches to its narrow layout at 700 pt or less (`HomeView.swift` line 15). Fix anything that looks broken, especially two-player mode (see §6). | free | ~1 h (estimate) |
| 1 | **Choose identifiers you'll keep forever.** Use a bundle ID like `com.<yourname>.tesseracolony`. It may contain only letters, digits, hyphens and periods, and **can't be changed after the first upload** [[36]][36]. Make a square, opaque 1024 × 1024 PNG icon [[38]][38]. Swift Playground won't upload an app that uses a preset placeholder icon [[8]][8]. | free | 15–30 min (estimate) |
| 2 | **Enroll in the Apple Developer Program as an individual.** You need an Apple Account with two-factor authentication, and you must enroll under your legal name [[17]][17]. You can enroll in the Apple Developer app, where membership is an auto-renewing subscription, or on the web. Apple says to contact them if no confirmation arrives within 24 hours [[18]][18]. | **US$99/year** (local equivalent) [[17]][17] | minutes to ~1 day |
| 3 | **Accept the agreements in App Store Connect** (Safari on the iPad). No app can be added until the Account Holder signs the latest agreement [[26]][26]. | free | 5 min |
| 4 | **Recommended: add an `Info.plist` and a privacy manifest** (§5). The Info.plist sets `ITSAppUsesNonExemptEncryption = NO`, so you don't have to answer the encryption questions for every version [[27]][27]. The privacy manifest declares the "required-reason" APIs the code uses [[29]][29]. The edits can be made in the copy of the project kept outside the iPad and copied across. Or do them on the iPad with an app that can edit files inside the `.swiftpm` package; the developers I cite used Working Copy [[12]][12][[13]][13]. | free | 30–60 min (estimate) |
| 5 | **Upload from Swift Playground.**<br>• Sign in with your developer account.<br>• Open **App Settings** (button at the top of the sidebar) [[10]][10].<br>• Set the name, accent colour and custom icon. No capabilities are needed.<br>• Set the team, bundle ID, version and category [[8]][8][[9]][9].<br>• Tap **Upload to App Store Connect** [[8]][8].<br>Apple's WWDC22 session says Swift Playground creates the App Store Connect app record and uploads the build for you [[11]][11]. It also raises the build number automatically [[12]][12]. | free | ~15 min, plus server processing |
| 6 | **Finish in App Store Connect → TestFlight.**<br>• If the build shows "Missing Compliance", answer the encryption questions. The app has no networking and no cryptography [[27]][27][[28]][28].<br>• Create an **Internal Testing** group, add yourself and add the build [[22]][22].<br>• Check your email for any "ITMS-91053 Missing API declaration" message [[29]][29]. | free | ~15 min |
| 7 | **On the iPhone:**<br>• Install the TestFlight app. It needs iOS 16 or later.<br>• Open the invitation email and tap "View in TestFlight", then Accept → Install [[25]][25].<br>The app's iOS 17 minimum means any iPhone XR/XS or newer will run it [[49]][49]. | free | 5 min |
| 8 | **Iterate.** Each **Upload** creates a new build. Internal testers can use each build for **90 days** [[21]][21][[22]][22]. | free | — |

**Total:** US$99/year. Expect about half a day of hands-on work, plus up to a day waiting for enrollment (estimate). Inviting friends outside your App Store Connect team (external testers) adds one Beta App Review of the first build (§2).

---

## 1. Can Swift Playground run on iPhone, or run the app on a nearby iPhone?

**No, on both counts.**

- **There is no iPhone version.** The App Store listing for Swift Playground is an iPad app that "Requires iPadOS 18.0 or later" [[1]][1]. Apple's product page describes it as an app "for iPad and Mac" [[2]][2]. An Apple Developer Forums answer confirms it is not available for iPhone [[4]][4].
- **There is no "run on device" like Xcode's.** Swift Playground can share the *project* (AirDrop, Messages, Mail, a copy), export PDFs and playground books, and submit to App Store Connect [[8]][8]. None of these installs an app on another device.
  - A forum answer (2022) says Swift Playgrounds can't run apps on actual iPhones and can't preview iPhone screen sizes [[6]][6].
  - Version 4.7 (March 2026) brought Swift 6 and the iOS 26 SDK [[1]][1]. A reviewer found no functional changes beyond the Liquid Glass redesign [[3]][3].
- **Swift Playground on a Mac doesn't help either.** It can only submit Mac (Catalyst) apps. Xcode is the only way to submit an iOS app from a Mac [[5]][5].
- **The Run button only runs the app on the iPad itself** [[7]][7].

---

## 2. The App Store Connect / TestFlight route from the iPad

### Requirements

| Item | What's needed |
|------|---------------|
| Membership | The paid Apple Developer Program. A free Apple Account gets no App Store Connect, TestFlight or distribution access [[16]][16]. Price: US$99 per membership year; Apple shows the price in local currency at enrollment [[17]][17][[19]][19]. Fee waivers exist only for nonprofits, accredited educational institutions and government bodies [[17]][17]. |
| Agreements | The Account Holder must accept the latest agreement before adding apps [[26]][26]. |
| App record | Platform, name, primary language, bundle ID and SKU are required. An app name can only be used by one app per localization [[26]][26]. Swift Playground creates the record during upload [[11]][11]. If that fails (for example because "Tessera Colony" is already taken), create the record yourself in App Store Connect with the same bundle ID, or pick another name. |
| Bundle ID | Must be unique and match App Store Connect. It can't be changed after a build is uploaded [[36]][36]. `com.example.tesseracolony` must be replaced. |
| App icon | Must be a custom image imported in App Settings; presets are rejected at upload [[8]][8]. 1024 × 1024 px, opaque [[38]][38]. |
| Version / build | Apple documents `CFBundleShortVersionString` as three period-separated integers, e.g. `0.1.0` [[37]][37]. Swift Playground handles build numbers for you [[12]][12]. |
| Export compliance | App Store Connect asks about encryption for every new version unless `ITSAppUsesNonExemptEncryption` is in Info.plist. Set it to `NO` if the app uses no encryption, or only exempt kinds [[27]][27]. Without the key, the build sits at "Missing Compliance" until you answer [[28]][28]. In a Swift Playground project, Info.plist entries are added through `additionalInfoPlistContentFilePath` [[12]][12][[13]][13]. |
| Privacy manifest | Since 1 May 2024, Apple's documentation says App Store Connect doesn't accept apps that use "required-reason" APIs without declaring a reason [[29]][29]. This app uses two of them (§5). |
| SDK | Since 28 April 2026, uploads must be built with the iOS 26 SDK or later [[47]][47]. Swift Playground 4.7 includes the iOS 26 SDK [[1]][1]. |
| App Store only (not TestFlight) | A privacy policy URL ("required for all apps") and the App Privacy questionnaire [[42]][42]. Data processed only on the device doesn't count as "collected" [[41]][41], so this app can answer "Data Not Collected". Updated age-rating questions also apply [[47]][47]. Screenshots: see below. |

### Step-by-step in Swift Playground

1. **Sign in with your developer account.** In the 4.2 guide this was More menu → **Advanced** → **Sign In** [[9]][9]. The current guide just says to sign in with your developer account before uploading [[8]][8].
2. **Open App Settings.** Tap the sidebar button, then **App Settings** near the top [[10]][10].
3. **Set the app's look.** Choose the name and accent/icon colour, then import or paste the icon image (Photos, Files or another app) [[8]][8][[10]][10].
4. **Set the minimum iPadOS version.** Leave capabilities empty; this app needs none (§5) [[8]][8].
5. **Enter the release details:** team, bundle ID, version number and category (for example Games) [[8]][8][[9]][9].
6. **Tap Upload to App Store Connect** [[8]][8].
7. **If the upload reports success but no build appears,** look in App Store Connect in Safari [[77]][77].
   - Credential errors such as "AppRecordCredentialsProviderError" have been reported. Check the account is a paid membership, either as the only member of an individual team or a member of an organization team [[76]][76].

### Getting the build onto the iPhone: internal vs external testers

| | Internal testers | External testers |
|---|---|---|
| Who | Up to 100 App Store Connect users with the Account Holder, Admin, App Manager, Developer or Marketing role [[20]][20]. **You qualify as Account Holder.** | Up to 10,000 people, by email or a public link [[20]][20]. |
| Review | None. Add the build to your internal group, or turn on automatic distribution [[22]][22]. | The first build added to a group goes to Beta App Review; later builds of the same version might not [[21]][21][[23]][23]. You can submit at most 6 builds for TestFlight review in 24 hours [[23]][23]. Apple doesn't publish a TestFlight review time. Its "90% within 24 hours" figure is for App Store review [[46]][46]. |
| Setup | Create the internal group, invite yourself, add the build and fill in "What to Test" [[22]][22]. | An internal group must exist first [[23]][23]. Fill in Test Information: a Beta App Description is required, plus a feedback email [[24]][24]. |
| Expiry | 90 days per build [[22]][22]. | 90 days per build [[21]][21]. |

**On the iPhone:**
- Install TestFlight. It needs iOS or iPadOS 16 or later.
- Open the invitation and tap Accept → Install [[25]][25].
- A tester can use up to 30 devices [[20]][20].
- TestFlight installs **don't** need Developer Mode [[50]][50].
- Testers can send feedback, including screenshots, from inside the beta app [[21]][21].

**Rules to know:** testers can't be paid or rewarded in any way. Betas and demos belong on TestFlight, not the App Store [[45]][45].

### iPhone-only vs universal

- **`Package.swift` is already universal** (`.pad` and `.phone`). One upload covers both devices, and TestFlight will offer it on the iPad too. I recommend keeping it that way.
- **For the App Store** you need at least one screenshot for an "iPhone with Dynamic Island (medium display)". If iPad is supported, you also need at least one for the 13-inch iPad [[43]][43]. TestFlight-only builds need no screenshots.
- **Once released, you can't drop a device family** in later updates. Forum answers citing Apple QA1623 say the only way out is a separate new app [[44]][44].
- **Going iPhone-only gains little.** Apple says iPhone apps should run on iPad whenever possible [[45]][45], and you develop on the iPad.

### Things to watch

- **SDK deadline:** next year's minimum SDK hasn't been announced [[47]][47]. If Apple repeats the 2026 pattern with the iOS 27 SDK in spring 2027, Swift Playground will need an update first. Version 4.7 arrived about seven months after iOS 26 [[3]][3]. This is speculation, not an announcement.
- **iOS 27 phones:** iOS 27 came out on 14 September 2026 and supports iPhone 11 and later, plus iPhone SE (2nd generation and later) [[48]][48]. A build made with the iOS 26 SDK should still be installable there. I expect that from how iOS normally works, but I didn't find a source that states it.

---

## 3. Is there any free way?

**Not without a Mac, and not in a way I'd recommend.**

| Idea | Works? | Why |
|------|--------|-----|
| Swift Playground on the iPhone | No | It's iPad and Mac only [[1]][1][[4]][4]. |
| AirDrop / Messages / Mail from Swift Playground | No | This sends the *project*, which needs Swift Playground to open. It doesn't send an installable app [[8]][8]. |
| Free Apple ID "personal team" provisioning | **Only with Xcode on a Mac** | A free account allows on-device testing with limits: provisioning profiles expire after 7 days, up to 3 test devices per platform, up to 10 App IDs [[16]][16]. Running from Xcode needs Developer Mode on the iPhone [[50]][50]. See §4 ("borrow a Mac"). |
| TestFlight without paying | No | TestFlight and App Store Connect require the paid program [[16]][16]. |
| App Clip | No | An App Clip needs a full app, an App Clip target in Xcode, and App Store Connect setup [[67]][67]. |
| Sideloading tools (AltStore, Sideloadly, …) | Not from Swift Playground | They install `.ipa` files. Swift Playground's sharing options don't include exporting an app binary [[8]][8]. |
| EU Web Distribution / alternative marketplaces | No | Eligibility needs things like a fee-waiver organisation or 2+ years' membership with an app that had 1M+ installs. Apps must also be notarized [[68]][68]. |
| Web wrapper / home-screen web app | Only by rewriting | A SwiftUI app can't run in Safari. This would mean rebuilding the game in web technology (my assessment). |
| **xtool** on a Windows (WSL) or Linux PC, e.g. your gaming PC | Technically yes; risky | xtool builds and deploys iOS apps from SwiftPM on Linux, Windows (WSL) and macOS [[63]][63], and is still maintained [[64]][64]. Drawbacks:<br>• It needs the iOS SDK from an Xcode download. Apple's agreement forbids installing Xcode and the SDK on non-Apple hardware [[65]][65].<br>• Logging in with a free Apple ID uses private APIs; one tester advised using a throwaway Apple ID [[66]][66].<br>• That tester couldn't get direct device install (`xtool dev`) to work [[66]][66].<br>• The project would have to be restructured into xtool's `xtool.yml` + `Package.swift` format [[66]][66].<br>**Not recommended.** |

---

## 4. Mac-based alternatives without owning a Mac

**The key limit:** Xcode pairs an iPhone either by cable, or wirelessly on the **same Wi-Fi network**. Current Xcode needs iOS 27 for wireless pairing [[51]][51]. So a rented cloud Mac **can't install onto your iPhone**. It can only:

- upload to TestFlight (which still needs the US$99 membership);
- run the iPhone Simulator, so you can check layouts at different screen sizes;
- give you Xcode's diagnostics.

| Option | Cost | What it gives you | Trade-offs |
|--------|------|-------------------|------------|
| **Borrow a Mac** | free | AirDrop the project over [[8]][8] and open it in Xcode [[2]][2]. With a free personal team, run it on your iPhone over a cable [[51]][51] with Developer Mode on [[50]][50]. With the paid program you can also archive and upload, with full control of Info.plist and the privacy manifest. | The installed app expires after 7 days [[16]][16]. Xcode 27 needs macOS Tahoe 26.6 or later; Xcode 26.5/26.6 need Tahoe 26.2 or later [[52]][52]. Updating means going back to that Mac. |
| **MacinCloud pay-as-you-go** | From US$1/h with a 25-hour minimum prepaid (US$25), or US$4/day with a 7-day minimum; no trial, no refunds [[55]][55]. Dedicated servers from about US$49/month [[56]][56]. | A managed Mac account to run Xcode and the Simulator, or to upload. | No admin rights on managed plans. The listed macOS versions (Sequoia/Sonoma/Ventura) [[55]][55] may be too old for current Xcode [[52]][52]; check before buying. |
| **AWS EC2 Mac** | Billed per dedicated host, with a **24-hour minimum** [[57]][57][[58]][58]. Roughly US$0.65/h for M1 (US$15.60 minimum) or US$0.878/h for M2 (US$21.07 minimum), per a third-party summary [[59]][59]. | A full bare-metal Mac. | Needs AWS setup and remote-desktop configuration. Overkill here. |
| **Scaleway Mac mini** | M1 €0.11/h (€75/month); M4 €0.22–0.29/h [[60]][60]. A 24-hour minimum lease was reported at launch [[61]][61], so roughly €2.64 minimum for M1. | The cheapest listed way to get a day of Xcode and Simulator. | Remote desktop only. You still need the membership to upload. |
| **GitHub Actions macOS runner** | US$0.062/min for standard macOS runners [[62]][62]. | Command-line builds and uploads (CI). | You must automate code signing and uploading yourself. Advanced. |
| **Xcode Cloud** | 25 compute hours/month included with membership [[53]][53]. | Cloud builds that can feed TestFlight. | The **first workflow must be set up in Xcode** (so on a Mac) and needs a Git repository. After that, App Store Connect can manage workflows [[54]][54]. It adds nothing here because Swift Playground already uploads. |

**When a Mac is worth it:**
- you want a free 7-day install and can borrow one;
- the privacy-manifest check (§5) can't be satisfied from the iPad;
- you want the iPhone Simulator to check small screens (one day on a Scaleway M1 is the cheapest of these).

---

## 5. Project changes before an iPhone / TestFlight build

### What the current `Package.swift` has

- `bundleIdentifier: "com.example.tesseracolony"` is a placeholder and must change.
- No `teamIdentifier`, icon, accent colour or category lines yet. The file's comment leaves icon and accent colour to App Settings.
- `displayVersion: "0.1"`, `bundleVersion: "1"`.
- Device families `[.pad, .phone]`. Portrait and both landscapes, plus upside-down portrait on iPad only. Minimum iOS 17.
- No `additionalInfoPlistContentFilePath`. The target is `.executableTarget(name: "AppModule", path: ".")` with no resources declared.

### Edits to make (not made)

| # | Change | How |
|---|--------|-----|
| 1 | `bundleIdentifier` → `com.<yourname>.tesseracolony` (permanent after the first upload [[36]][36]) | App Settings → Bundle ID [[8]][8] |
| 2 | Add a team | App Settings → Team. Swift Playground writes `teamIdentifier` [[8]][8][[9]][9] |
| 3 | Custom app icon (required to upload) and optional accent colour | App Settings [[8]][8][[10]][10]. Let Swift Playground write these manifest lines rather than typing them by hand. |
| 4 | `displayVersion` `"0.1"` → `"0.1.0"` (Apple's documented three-integer format) [[37]][37] | App Settings → Version |
| 5 | `bundleVersion` | Leave it. Swift Playground increments it on upload [[12]][12]. |
| 6 | Category, e.g. Games | App Settings → Category [[8]][8] |
| 7 | Display name "Tessera Colony" | Already set. Check that the name is free on the App Store [[26]][26]. |
| 8 | Add `additionalInfoPlistContentFilePath: "Info.plist"` as the **last** argument of `.iOSApplication`, and add an `Info.plist` file to the package folder [[12]][12][[13]][13] | Edit outside Swift Playground (this repo copy, or Working Copy on the iPad) |
| 9 | Add `PrivacyInfo.xcprivacy` and declare it as a target resource (**untested in Swift Playground**, see below) | Same |
| 10 | Capabilities: **none** | — |
| 11 | UI text that says "iPad": `HomeView.swift` line 120 ("…on one iPad"), line 557, line 1367 ("iPad volume"); `VersusView.swift` line 463 | Code change, optional |

**Why no capabilities are needed:**
- The system photo picker runs in a separate process and needs no Photos permission [[39]][39]. `HomeView` only uses `PhotosPicker`.
- `SoundBoard` only plays sound through `AVAudioEngine`. There is no microphone input; grep found no `inputNode`, camera or location API.
- There is no networking (no `URLSession`).

**Sketch of the manifest after the edits** (icon, accent colour and category lines omitted because App Settings writes them):

```swift
.iOSApplication(
    name: "Tessera Colony",
    targets: ["AppModule"],
    bundleIdentifier: "com.yourname.tesseracolony",   // was com.example.tesseracolony
    teamIdentifier: "<Team ID>",                       // written when you pick a Team
    displayVersion: "0.1.0",                           // was "0.1"
    bundleVersion: "1",                                // auto-incremented on upload
    /* appIcon / accentColor / appCategory written by App Settings */
    supportedDeviceFamilies: [.pad, .phone],           // keep: universal
    supportedInterfaceOrientations: [ /* unchanged */ ],
    additionalInfoPlistContentFilePath: "Info.plist"   // new, must be last
)
// …
.executableTarget(
    name: "AppModule",
    path: ".",
    resources: [.copy("PrivacyInfo.xcprivacy")]        // new — untested in Swift Playground
)
```

**`Info.plist`** (declares no non-exempt encryption [[27]][27]):

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>ITSAppUsesNonExemptEncryption</key>
    <false/>
</dict>
</plist>
```

**Warning: Swift Playground rewrites `Package.swift`.** A 2021 bug report said changing App Settings or uploading could drop `additionalInfoPlistContentFilePath` (possibly fixed in 4.1) [[15]][15]. A 2024 write-up says manual edits are fine in practice [[12]][12]. To be safe, make all App Settings changes first, add the Info.plist line last, and check it is still there after each upload. Your custom comments in `Package.swift` may also disappear when it's rewritten.

### Privacy manifest (required-reason APIs)

A grep of the code found two required-reason API categories:

| API in code | Where | Category | Reason |
|---|---|---|---|
| `UserDefaults.standard` | `SaveStore.swift` (settings, progress, saved games) | `NSPrivacyAccessedAPICategoryUserDefaults`. Apple flags UserDefaults as needing a `PrivacyInfo.xcprivacy` declaration [[31]][31] | `CA92.1`: read and write data only the app itself can access [[32]][32][[34]][34] |
| `mach_absolute_time()` | `SoundBoard.swift` lines 518 and 522 (audio scheduling) | `NSPrivacyAccessedAPICategorySystemBootTime`, which covers `systemUptime` and `mach_absolute_time` [[32]][32] | `35F9.1`: measure time elapsed between events in the app, or run timers [[33]][33] |

I found no file-timestamp, disk-space or active-keyboard APIs.

**`PrivacyInfo.xcprivacy`** (the file must have exactly this name [[30]][30]):

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>NSPrivacyTracking</key><false/>
    <key>NSPrivacyTrackingDomains</key><array/>
    <key>NSPrivacyCollectedDataTypes</key><array/>
    <key>NSPrivacyAccessedAPITypes</key>
    <array>
        <dict>
            <key>NSPrivacyAccessedAPIType</key>
            <string>NSPrivacyAccessedAPICategoryUserDefaults</string>
            <key>NSPrivacyAccessedAPITypeReasons</key>
            <array><string>CA92.1</string></array>
        </dict>
        <dict>
            <key>NSPrivacyAccessedAPIType</key>
            <string>NSPrivacyAccessedAPICategorySystemBootTime</string>
            <key>NSPrivacyAccessedAPITypeReasons</key>
            <array><string>35F9.1</string></array>
        </dict>
    </array>
</dict>
</plist>
```

**What is and isn't certain:**
- Apple says a missing declaration triggers an email and, since 1 May 2024, the app isn't accepted [[29]][29]. Developers report that enforcement has been inconsistent [[35]][35].
- The manifest must be in the bundle that contains the executable [[29]][29]. Apple's create-a-manifest steps are Xcode-only [[30]][30].
- **I could not confirm** that Swift Playground places a SwiftPM resource where App Store Connect looks for it.

**Practical plan:**
1. Include the manifest.
2. Upload.
3. Watch for an ITMS-91053 email or a rejected build.
4. If that happens, either:
   - do one upload from a Mac with Xcode (§4), or
   - stop calling those two APIs directly. For example, save settings as a JSON file in Application Support, as `FlightRecorder.swift` already does. With no required-reason API in use, nothing needs declaring.

### What Swift Playground apps can't include

- App extensions such as widgets, and Watch apps [[13]][13].
- Separate targets and schemes, so no native unit or UI test targets [[12]][12].
- A debugger or profiler [[13]][13].
- Only a limited set of entitlements; for example no push notifications or WeatherKit [[13]][13].
- One author reports that in-app purchases can't be set up from Swift Playground [[14]][14].

None of these affect Tessera Colony today.

---

## 6. iPhone-specific risks for this app

### Screen size and layout

**Device sizes in points:**

| Device | Portrait size |
|---|---|
| iPhone SE (2nd/3rd gen) | 375 × 667 [[75]][75] |
| iPhone 15/16 | 393 × 852 [[75]][75] |
| iPhone 16 Pro Max | 440 × 956 [[75]][75] |
| Your iPad Air 11-inch | 820 × 1180 [[78]][78] |

**Game screen, portrait.** In the compact branch of `GameView.computeLayout`:
- It reserves 440 pt (480 pt on screens wider than 600 pt) plus 30 pt for the control panel.
- It never makes cells smaller than 2.5 pt.
- After the status bar and home-indicator insets, the board gets roughly 290 pt of height on a 393 × 852 phone and only about 175 pt on an iPhone SE (my estimate from the code).
- A full-size photo board (up to 90 × 100 tiles, `PhotoLevelBuilder.swift` line 59) comes out at about 2.5-point tiles on a 6.1-inch phone. On an SE the board is taller than its slot and pushes the panel down. The column scrolls, so nothing is lost, but the art is tiny.
- Pinch-zoom (up to 4×) helps.
- Play happens in the control panel, not by tapping tiles, so small tiles affect what you can see rather than what you can do.

**Game screen, landscape.** The side-by-side layout gives the panel at least 360 pt, leaving roughly a 330 × 340 pt board area on a 6.1-inch phone (estimate).

**Two-player mode (`VersusView`) is the biggest risk.**
- Portrait stacks two control panels, one rotated, around the board(s). Unlike `GameView`, it isn't inside a ScrollView, so content will probably be squashed or cut off on phones.
- Its setup text says "Two players on one iPad".
- Test it first. Consider hiding it or simplifying it on narrow screens.

**Home screen** switches to its wide layout above 700 pt. Larger iPhones in landscape may get the wide layout.

**Keyboard.** The keyboard covers much more of a phone screen. The win card already scrolls the name field into view; check it on an SE-sized screen.

### Performance

- **The board redraws in full every frame while ants move** (`TimelineView(.animation)` + `Canvas`), and pauses when nothing moves. That's good.
- **Frame rate:**
  - On iPhones with ProMotion (13 Pro and later, iPhone 17, iPhone Air), Core Animation stays at 60 Hz or below unless the app sets `CADisableMinimumFrameDurationOnPhone` [[69]][69]. That matches your iPad Air M3, which has no ProMotion [[70]][70]. **Don't add that key**; 60 Hz keeps power use down.
  - Refresh rates also drop in Low Power Mode or when the phone gets hot [[69]][69].
- **Slower chips.** The oldest supported phones (iPhone XR/XS, 2018) [[49]][49] are much slower than an M3, so test there if you can.
  - `HintSolver` stops after a fixed 3 s + 1 s of real time, so on slow phones hints may be weaker. It runs off the main thread, so the UI won't freeze.
  - `MosaicRaster.makeImage()` copies the whole pixel buffer each time tiles change. At 3× display scale, a board that fills a phone screen is roughly 1,100 × 1,100 px, about 5 MB, which is manageable (estimate from the code).

### Memory

- iPhone XR and SE (2nd gen) have 3 GB of RAM; iPhone 11–13 have 4 GB [[71]][71]. Your iPad Air M3 has 8 GB [[70]][70].
- If iOS ends the app for using too much memory while it's on screen, it looks like a crash [[72]][72].
- The app's working set (one board raster, sprites, up to 128 ants per team) looks modest. The main thing to check is importing several large photos in a row.

### Sound and haptics

- **Silent switch.** The default `.ambient` audio category is silenced by the iPhone's Ring/Silent switch [[40]][40]. The app already has an option to ignore silent mode (`.playback`). Make sure players can find it, because many iPhone users keep silent mode on.
- **Haptics.** iPads have no Taptic Engine [[73]][73]. The haptics on every send and on refused moves (`GameView` lines 59–60) will only be felt for the first time on the iPhone. Check they aren't too much.

### Testing advice

1. **On the iPad, before paying:** narrow the Swift Playground window [[74]][74] and check that the compact game layout, Home, sheets and two-player mode still work. There is no iPhone simulator in Swift Playground [[6]][6].
2. **On the iPhone via TestFlight:**
   - portrait and both landscapes;
   - a large photo board for about 10 minutes (heat and battery);
   - Low Power Mode;
   - the silent switch;
   - photo import;
   - typing a high-score name;
   - two-player mode;
   - quitting mid-game and resuming.
3. **Use the app's own diagnostics** (the Settings self-test, the Sound check, and the FlightRecorder crash banner on Home), plus TestFlight's screenshot feedback [[21]][21]. There is no debugger on the iPad.
4. **If you can borrow an older or smaller iPhone,** add it as a second device. A TestFlight tester can install on up to 30 devices [[20]][20].

---

## Could not verify

- **Privacy manifest:** whether Swift Playground 4.7 packages `PrivacyInfo.xcprivacy` where App Store Connect checks it, and whether App Store Connect currently rejects or only warns. Apple says it rejects [[29]][29]; developers report it doesn't always [[35]][35].
- **Current Swift Playground screens:** the exact place to sign in, and whether 4.7 still creates the App Store Connect record automatically. The sources are the 4.2 guide and WWDC22 [[9]][9][[11]][11]; the current guide only summarises the steps [[8]][8].
- **Manual manifest edits:** whether Swift Playground 4.7 keeps a hand-added `additionalInfoPlistContentFilePath` and `resources:` line. A 2021 bug report says no; a 2024 write-up says fine [[15]][15][[12]][12]. I also couldn't confirm whether Swift Playground lets you edit `Package.swift` directly.
- **Cloud Mac prices:** official AWS hourly Mac prices (the AWS page didn't render, so a third-party summary is used [[59]][59]). Scaleway's 24-hour minimum is only confirmed by a 2021 article [[61]][61]. Whether GitHub's standard macOS runners are free for public repositories.
- **Future SDK deadline:** when Apple will require the iOS 27 SDK for uploads, and whether Swift Playground will be updated in time.
- **Your iPhone:** the model is unknown. Any iPhone XR/XS or newer meets the iOS 17 minimum [[49]][49].
- **Timings:** typical upload-processing and TestFlight review times are not published; mine are estimates.
- **Window size:** the narrowest window width iPadOS 26 allows when previewing the phone layout.

---

## Sources

1. [Swift Playground – App Store listing (version 4.7, compatibility)][1]
2. [Swift Playground – Apple Developer][2]
3. [Swift Playground for iPad updated with iOS 26 SDK and Liquid Glass – SlatePad (Mar 2026)][3]
4. [How to install codes from Playground on iPhone – Apple Developer Forums][4]
5. [(Swift Playgrounds for Mac) How do I build for iPhone? – Apple Developer Forums][5]
6. [iPhone Simulator in Swift Playgrounds – Apple Developer Forums][6]
7. [Local testing of Swift Playgrounds app on iPad – Apple Developer Forums][7]
8. [Share a playground in Swift Playground on iPad (incl. Submit an app to App Store Connect) – Apple Support][8]
9. [Share a playground / submit to App Store Connect – Swift Playgrounds 4.2 guide – Apple Support][9]
10. [Create an app icon in Swift Playground on iPad – Apple Support][10]
11. [Build your first app in Swift Playgrounds – WWDC22][11]
12. [App development on iPad – mutatingfunc (Oct 2024)][12]
13. [The story of one of the largest apps written from an iPad – Medium (May 2024)][13]
14. [Building and publishing an iOS app with your iPad – Tea and Tech Time (2024)][14]
15. [FB9824864: Swift Playgrounds drops additionalInfoPlistContentFilePath – feedback-assistant/reports][15]
16. [Choosing a membership (compare memberships) – Apple Developer][16]
17. [Enroll in the Apple Developer Program – Apple Developer][17]
18. [Enrollment support – Apple Developer][18]
19. [Apple Developer Program – Apple Developer][19]
20. [TestFlight – Apple Developer][20]
21. [TestFlight overview – App Store Connect Help][21]
22. [Add internal testers – App Store Connect Help][22]
23. [Invite external testers – App Store Connect Help][23]
24. [Provide test information – App Store Connect Help][24]
25. [TestFlight (tester instructions) – Apple][25]
26. [Add a new app – App Store Connect Help][26]
27. [Complying with encryption export regulations – Apple Developer Documentation][27]
28. [Fix for Missing Compliance warning in App Store Connect – Code with Andrea][28]
29. [Describing use of required reason API – Apple Developer Documentation][29]
30. [Privacy manifest files – Apple Developer Documentation][30]
31. [UserDefaults – Apple Developer Documentation][31]
32. [Apple privacy manifest guide – dotnet/macios docs][32]
33. [Privacy manifest required reasons (system boot time) – Apple Developer Forums][33]
34. [Need clarification for UserDefaults reason CA92.1 – Apple Developer Forums][34]
35. [Describing use of required reason API – current status – Apple Developer Forums][35]
36. [CFBundleIdentifier – Apple Developer Documentation][36]
37. [CFBundleShortVersionString – Apple Developer Documentation][37]
38. [iOS app icon sizes and guidelines – SplitMetrics (updated 2026)][38]
39. [Delivering an enhanced privacy experience in your photos app – Apple Developer Documentation][39]
40. [AVAudioSession.Category.ambient – Apple Developer Documentation][40]
41. [App privacy details on the App Store – Apple Developer][41]
42. [App privacy (reference) – App Store Connect Help][42]
43. [Screenshot specifications – App Store Connect Help][43]
44. [Can I remove iPad support from my app on a new release? – Apple Developer Forums][44]
45. [App Review Guidelines – Apple Developer][45]
46. [App Review – Apple Developer][46]
47. [Upcoming requirements – Apple Developer News][47]
48. [iOS 27: release date and compatible iPhones – MacRumors (Sep 2026)][48]
49. [iPhone models compatible with iOS 17 – Apple Support][49]
50. [Enabling Developer Mode on a device – Apple Developer Documentation][50]
51. [Managing your simulated and physical devices in Device Hub – Apple Developer Documentation][51]
52. [Xcode system requirements – Apple Developer][52]
53. [Xcode Cloud – Apple Developer][53]
54. [Configuring your first Xcode Cloud workflow – Apple Developer Documentation][54]
55. [MacinCloud pay-as-you-go][55]
56. [Cloud Mac services compared 2026 – NoMac blog (vendor)][56]
57. [Amazon EC2 Mac instances – AWS documentation][57]
58. [Amazon EC2 Dedicated Host pricing – AWS][58]
59. [AWS EC2 Mac pricing explained (2026) – MacYou][59]
60. [Apple silicon pricing – Scaleway][60]
61. [How to rent a virtual M1 Mac mini for 12 cents an hour – Computerworld (2021)][61]
62. [Actions runner pricing – GitHub Docs][62]
63. [xtool – GitHub][63]
64. [xtool releases – GitHub][64]
65. [Xtool: cross-platform Xcode replacement – OSnews (May 2025)][65]
66. [Developing iOS apps on WSL using xtool – Zenn (May 2025)][66]
67. [Creating an App Clip with Xcode – Apple Developer Documentation][67]
68. [Getting started with Web Distribution in the EU – Apple Developer][68]
69. [Optimizing iPhone and iPad apps to support ProMotion displays – Apple Developer Documentation][69]
70. [iPad Air M3 11-inch specs – EveryMac][70]
71. [iPhone RAM list – 9to5Mac][71]
72. [Identifying high-memory use with jetsam event reports – Apple Developer Documentation][72]
73. [Haptic feedback across iPad and iPhone – Nutrient (Jan 2025)][73]
74. [iPadOS 26 introduces powerful new features – Apple Newsroom][74]
75. [iPhone 16 screen sizes – Use Your Loaf][75]
76. [Impossible to transport my code from Swift Playgrounds to App Store Connect – Apple Developer Forums][76]
77. [Swift Playgrounds and App Store Connect – Apple Developer Forums][77]
78. [Resolution by device – iOS Ref][78]

[1]: https://apps.apple.com/us/app/swift-playground/id908519492
[2]: https://developer.apple.com/swift-playground/
[3]: https://slatepad.org/2026/03/17/swift-playground-ipad-ios-26-sdk-liquid-glass/
[4]: https://developer.apple.com/forums/thread/781499
[5]: https://developer.apple.com/forums/thread/770054
[6]: https://developer.apple.com/forums/thread/697763
[7]: https://developer.apple.com/forums/thread/719178
[8]: https://support.apple.com/guide/playgrounds-ipad/share-a-playground-itc65b2d9a15/ipados
[9]: https://support.apple.com/en-ie/guide/playgrounds-ipad/itc65b2d9a15/4.2/ipados/16.0
[10]: https://support.apple.com/guide/playgrounds-ipad/create-an-app-icon-itc8ff20cba7/ipados
[11]: https://developer.apple.com/videos/play/wwdc2022/110348/
[12]: https://mutatingfunc.github.io/blog/2024-10-12-app-development-on-ipad/
[13]: https://medium.com/@crsohr/how-i-wrote-using-my-ipad-one-of-the-largest-app-submitted-to-app-store-connect-b91fc98ab179
[14]: https://teaandtechtime.com/building-and-publishing-an-ios-app-with-your-ipad-for-real/
[15]: https://github.com/feedback-assistant/reports/issues/269
[16]: https://developer.apple.com/support/compare-memberships/
[17]: https://developer.apple.com/programs/enroll/
[18]: https://developer.apple.com/support/enrollment/
[19]: https://developer.apple.com/programs/
[20]: https://developer.apple.com/testflight/
[21]: https://www.developer.apple.com/help/app-store-connect/test-a-beta-version/testflight-overview
[22]: https://www.developer.apple.com/help/app-store-connect/test-a-beta-version/add-internal-testers
[23]: https://www.developer.apple.com/help/app-store-connect/test-a-beta-version/invite-external-testers
[24]: https://developer.apple.com/help/app-store-connect/test-a-beta-version/provide-test-information/
[25]: https://testflight.apple.com/
[26]: https://www.developer.apple.com/help/app-store-connect/create-an-app-record/add-a-new-app
[27]: https://developer.apple.com/documentation/security/complying-with-encryption-export-regulations
[28]: https://codewithandrea.com/tips/fix-missing-compliance-warning/
[29]: https://developer.apple.com/documentation/bundleresources/describing-use-of-required-reason-api
[30]: https://developer.apple.com/documentation/bundleresources/privacy-manifest-files
[31]: https://developer.apple.com/documentation/foundation/userdefaults
[32]: https://github.com/xamarin/xamarin-macios/blob/main/docs/apple-privacy-manifest.md
[33]: https://developer.apple.com/forums/thread/749799
[34]: https://developer.apple.com/forums/thread/735286
[35]: https://developer.apple.com/forums/thread/751216
[36]: https://developer.apple.com/documentation/bundleresources/information-property-list/cfbundleidentifier
[37]: https://developer.apple.com/documentation/bundleresources/information-property-list/cfbundleshortversionstring
[38]: https://splitmetrics.com/blog/guide-to-mobile-icons/
[39]: https://developer.apple.com/documentation/photokit/delivering-an-enhanced-privacy-experience-in-your-photos-app
[40]: https://developer.apple.com/documentation/avfaudio/avaudiosession/category-swift.struct/ambient
[41]: https://developer.apple.com/app-store/app-privacy-details/
[42]: https://developer.apple.com/help/app-store-connect/reference/app-information/app-privacy/
[43]: https://developer.apple.com/help/app-store-connect/reference/app-information/screenshot-specifications/
[44]: https://developer.apple.com/forums/thread/701706
[45]: https://developer.apple.com/app-store/review/guidelines/
[46]: https://developer.apple.com/distribute/app-review/
[47]: https://www.developer.apple.com/news/upcoming-requirements/
[48]: https://www.macrumors.com/2026/09/13/ios-27-release-date-new-features/
[49]: https://support.apple.com/guide/iphone/iphone-models-compatible-with-ios-17-iphe3fa5df43/17.0/ios/17.0
[50]: https://developer.apple.com/documentation/xcode/enabling-developer-mode-on-a-device
[51]: https://developer.apple.com/documentation/xcode/managing-your-simulated-and-physical-devices-in-device-hub
[52]: https://developer.apple.com/xcode/system-requirements/
[53]: https://developer.apple.com/xcode-cloud/
[54]: https://developer.apple.com/documentation/xcode/configuring-your-first-xcode-cloud-workflow
[55]: https://www.macincloud.com/pages/payg.html
[56]: https://nomac.app/blog/cloud-mac-services-compared-2026
[57]: https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-mac-instances.html
[58]: https://aws.amazon.com/ec2/dedicated-hosts/pricing/
[59]: https://macyou.co/blog/aws-ec2-mac-pricing-explained
[60]: https://www.scaleway.com/en/pricing/apple-silicon/
[61]: https://www.computerworld.com/article/1646684/how-to-rent-a-virtual-m1-mac-mini-for-12-cents-an-hour.html
[62]: https://docs.github.com/en/billing/reference/actions-runner-pricing
[63]: https://github.com/xtool-org/xtool
[64]: https://github.com/xtool-org/xtool/releases
[65]: https://www.osnews.com/story/142331/xtool-cross-platform-xcode-replacement-for-linux-windows-and-macos/
[66]: https://zenn.dev/mnonamer/articles/ios-dev-on-wsl-with-xtool?locale=en
[67]: https://developer.apple.com/documentation/appclip/creating-an-app-clip-with-xcode
[68]: https://developer.apple.com/support/web-distribution-eu
[69]: https://developer.apple.com/documentation/quartzcore/optimizing-iphone-and-ipad-apps-to-support-promotion-displays
[70]: https://everymac.com/systems/apple/ipad/specs/apple-ipad-air-m3-11-inch-2025-a3266-wifi-only-specs.html
[71]: https://9to5mac.com/2023/11/18/iphone-ram-list/
[72]: https://developer.apple.com/documentation/xcode/identifying-high-memory-use-with-jetsam-event-reports
[73]: https://www.nutrient.io/blog/haptic-feedback-across-ipad-and-iphone/
[74]: https://www.apple.com/newsroom/2025/06/ipados-26-introduces-powerful-new-features-that-push-ipad-even-further/
[75]: https://useyourloaf.com/blog/iphone-16-screen-sizes/
[76]: https://developer.apple.com/forums/thread/725169
[77]: https://developer.apple.com/forums/thread/713475
[78]: https://iosref.com/res
