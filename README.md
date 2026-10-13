# Tessera Colony — iPad app playground

An original colour-ant mosaic puzzle for iPad (and later iPhone), built to open and run directly in
Apple's **Swift Playground** app — no Mac needed.

## What's in this folder

| Path | What it is |
|---|---|
| `TesseraColony.swiftpm` | **The app.** Open this in Swift Playground on the iPad (or in Xcode on a Mac). |
| `Docs/PLAN.md` | Research (with sources), design, first-version scope vs later, architecture, iPhone path |
| `Docs/VALIDATION.md` | Which checks were actually run, and what still needs your iPad |
| `Docs/IPHONE.md` | How to get the app onto an iPhone without a Mac (TestFlight via Swift Playground), with costs, project changes and iPhone risks |
| `Docs/data/` | Raw test results and level statistics (JSON) |
| `Mockups/` | Labelled design mockups: active play (exit X, one-tap return), blocked recovery, **Home with your collection** (found / explored / stars / mastered, theme chips, pack shelves), Home filtered to *Go harder*, Home scrolled to the **Literature** theme, to **Seasons** (the *In season* badge on Halloween) and to **Sky & Science** (Probes & Telescopes, Geometry & Illusions), iPad portrait, photo-to-puzzle, the start card (difficulty, harder options, high scores), the finish card (stars, mastered, the harder step, a new high score with name entry), two players (race and shared board) |
| `Renders/first_dig_preview.gif` | Preview animation of ants crawling out, lifting tiles and carrying them home (reference model, not the app) |
| `Renders/all_mosaics.png`, `Renders/pattern_samples.png` | The five main mosaics, and six sample *New pattern* mosaics covering all five pattern layouts, rendered by the reference tools |
| `Renders/sound_set_actions.m4a`, `Renders/sound_set_goals.m4a`, `Renders/sound_preview_first_dig.m4a` | Listening previews: the Action set (plus the colony clinks), the Goal set, and the opening of First Dig at 1×. Made with the reference sound model — not recordings of the app |
| `Renders/path_styles.png` | The same team routed by each ant-path style (reference model) |
| `Renders/challenge_mosaics.png` | The four Challenge mosaics |
| `Renders/garden_master_mosaics.png` | The sixteen Garden and Master pictures — every one a different subject |
| `Renders/collection_mosaics.png` | The 56 collection mosaics (nature, art, history, science) in their seven packs, with each one's measured rating on Classic |
| `Renders/literature_mosaics.png` | The 56 Literature mosaics — iconic scenes from public-domain books, plays and tales — in their seven packs, with ratings |
| `Renders/seven_new_packs.png` | The 56 newest mosaics — Natural History, World Craft, Geometry & Illusions, Probes & Telescopes, Inventions & Firsts, Halloween and Winter — with ratings |
| `Tools/` | Python tools that generate the mosaic art and levels and run the reference tests |

## Setup on the iPad (about 5 minutes)

1. **Update Swift Playground** from the App Store (version 4.7 or later; it needs iPadOS 18+, and you have iPadOS 26).
2. **Get the project onto the iPad.** Download the ZIP and open the **Files** app → *Downloads*.
   Tap the ZIP once and Files unzips it into a `TesseraColony` folder.
3. **Open the app playground.** Inside that folder, tap **`TesseraColony.swiftpm`**. It opens in Swift Playground.
   If it doesn't: open Swift Playground → *Locations* / *Browse* → pick `TesseraColony.swiftpm` from Files.
   (Moving the `.swiftpm` into *iCloud Drive → Playgrounds* keeps it in Swift Playground's own list.)
4. **Run it.** Wait for the first build (a few seconds), then tap **▶ Run**. To play in full screen,
   use the full-screen app preview button.
5. If Swift Playground shows **red errors**, take a screenshot of the error list (or tap an error and
   copy its text) and send it to me. That is the most useful thing if the build fails.

## Your first test (15–20 minutes)

0. **Sound first:** Home → *Settings & self-test* → *Sound* → **Sound check: play a test chime**. You
   should hear a two-note chime. If not, screenshot the report under the button (it shows whether the
   sounds are ready, whether the audio engine is running, the output and the iPad volume). Sounds now
   play even when the iPad is in Silent mode (there is a switch to change that).
1. **Home:** two big buttons (**Two players**, **High scores**), *Next up*, then **Your collection** —
   how many mosaics you have found, explored (finished), the stars you have earned and how many you
   have mastered, with a chip per theme (First Mosaics, Seasons, Nature, Art, Literature, History, Sky &
   Science, Tests of Skill) that scrolls straight to it. Below: the filter bar — **Difficulty**, **Show** (rating) and
   the new **Status** (All, To explore, Explored, Go harder, Mastered) — and then each theme with its
   packs as shelves you scroll sideways. Cards marked **?** are not found yet; locked cards say what
   opens them. Set the filters back to *All*, then **Next up → Play… → Start.** The start card shows each difficulty's slots and rating, the new
   **Harder options** and the mosaic's **High scores**. Pick Classic with no harder options for
   First Dig. Tap a team and watch the ants crawl out, lift tiles and carry them home.
2. **Slots:** watch the SLOTS row. Each team you send takes a slot and its number counts down as its
   ants pick up tiles. Send teams from different tunnels until every slot is busy; the next tap should
   be refused with a message saying when a slot opens.
3. **Waiting and the queue:** send a team that can't reach all its tiles (long-press it first to
   scout). It should stay in its slot marked *Waiting* with a small ↩ badge, and finish by
   itself once its colour is uncovered. **One tap on it** sends it straight back to its tunnel (no
   pop-up); Undo puts it back. Try sending the same colour from two tunnels — that is allowed.
   Tap a tunnel's name to see its whole queue.
   **Exit:** tap the round **X** in the top-left corner — you should land on Home, and *Resume* should
   bring the game back.
4. **Speed:** drag the **Ant speed** slider from 0.1× to 16×. Ants already walking should change pace
   smoothly without jumping. Pinch the board to zoom in on the legs.
5. **Blocked on purpose:** keep sending teams that can't finish until every slot holds a waiting team.
   Try *Add a slot*, returning a waiting team, and **Undo**.
6. **Ground colour:** in-game menu (…) → *Ground colour…* → try a light and a dark preset.
   **Ant paths:** the default is now **Random per team** (each team picks a style when it is sent;
   settings still on the old default, Natural, are switched once). In-game menu (…) → *Ant paths* →
   try Curious, Wall-hugger and Scout trail. Only ants launched after the change use the new style.
   **Sound:** Settings → *Sound* → **Play a sample** next to *Action sounds* and *Goal sounds*. In a
   game you should hear wood-and-clay sounds for your moves, bells when a team finishes, when a whole
   colour is lifted, at each quarter of the mosaic and at the end, plus the colony clinks. Try 16×
   (clinks thin out to about 20 a second).
7. **New levels and the collection:** finishing First Dig opens Koi Pond and seven packs — Garden,
   **Wild Wonders**, **Gallery** (famous public-domain paintings), **Ancient World**, Challenge, and the
   first two **Literature** packs, **Epics & Legends** and **Fairy Tales & Fables**. In Literature, a Fairy
   Tales mosaic opens **Children's Classics**, which opens **Adventure Classics**, which opens **Gothic &
   Mystery**; an Epics & Legends mosaic opens **Shakespeare**, which opens **Great Novels**. In
   each pack the first three mosaics are found at once; **every mosaic you finish finds the next one**
   (watch a **?** card turn into a picture — the finish card says *Found: …*). Finishing a Gallery
   mosaic opens **World Art**; Ancient World opens **Voyages**, which opens **Modern Moments**; Wild
   Wonders opens **Sky & Science**; any Challenge mosaic opens **Master**. New: the seasonal **Halloween**
   and **Winter** packs open after First Dig (Halloween wears an **In season** badge now; Winter gets it in
   December — both are playable all year); a Garden mosaic opens **Natural History**, a World Art mosaic
   **World Craft**, a Sky & Science mosaic **Probes & Telescopes**, a Challenge mosaic **Geometry &
   Illusions**, and a Modern Moments mosaic **Inventions & Firsts**. Each pack runs from its
   gentlest to its hardest. Finish a mosaic on Gentle for ★, Classic ★★, Expert ★★★, and on Expert with
   a harder option for the flame (*Mastered*). The finish card now offers the **next harder step**
   (*Try it on Classic*, *Try it on Expert*, then *Expert + a harder option*). The **Go harder** status
   chip lists what you have finished but not mastered. No two of the 193 mosaics share a design.
   Or turn on *Unlock all mosaics* in Settings to see and play everything. Try **Labyrinth on Classic**: sending whatever can
   finish now should get you stuck; scout, plan and undo. Then a Master mosaic on Gentle.
   **Finish First Dig again with a harder option or two** (e.g. *3 undos* + *No hints*): the finish
   card should show your score and, if it makes the top 5, a name box — tap anywhere in the box, type
   your name (the box lights up and stays above the keyboard), then **Save**; the table appears.
   Home → **High scores** should show it too. On the home screen, tap
   **New pattern** under *Make a new level* a few times — you should get different layouts (rosette,
   starburst, fish scales, kaleidoscope, crossed ribbons), not the same rosette in new colours — then try **Choose a photo** with one photo that has a
   white background (its difficulty is measured on the iPad in a few seconds).
8. **Two players:** the big **Two players** button at the top of Home. Try **Race** with *Reach 3* on
   First Dig (landscape: side by side; portrait: face to face), then **Shared board**. *Any colour* is now
   the default, so you can launch the same colour from every tunnel. Both players can tap at the same
   time; one tap on a waiting team returns it (−10). At the end the winner can type a name for the
   two-player high-score table.
9. **Home → Settings & self-test → Run engine self-test.** Screenshot the results — especially the two
   new **Ant stress** lines at the top (Alhambra Tiles on Expert with Curious and Random per ant ants,
   added after your crash report).
10. **If the app ever stops (crashes):** open it again. Home shows *Last time, the game didn't close
    normally* — tap **Copy report** and paste it to me. It lists the mosaic, your settings, your moves and
    the last actions, so I can replay exactly that game. (It also appears if you stopped the app from
    Swift Playground in the middle of a game; then just tap *Dismiss*.)

## Feedback that helps most

- Did it build and run? Any errors, word for word.
- **If it crashed:** the crash report from Home (*Copy report*), and a screenshot of any red error line
  Swift Playground showed.
- Self-test screenshot.
- Slots: does waiting for a slot feel right? Are 3–4 slots on Classic too few or too many?
- Speed: is 1× the right default? Level lengths at 1× range from about 5 minutes to about 24 minutes
  (showcase). Do you want a second ant hill on the big mosaics?
- Smoothness on Sunflower & Monarch when many ants are out.
- Now that Hold is gone, is it clear how a team ends up waiting, what the queue shows, and what each tap does?
- Ground colour: does the picker work, and do light grounds still look good?
- Sound: are the Action and Goal sets easy to tell apart? Too loud, too busy or too quiet? Are the
  colony clinks pleasant or tiring after a few minutes? Which sounds would you change or drop?
- Challenge pack: is Classic hard in a fun way or just frustrating? Do the ratings on the start card
  match how hard it felt?
- Ant paths: *Random per team* is now the default, as you asked. Does the mix look good, or should some styles be left out of it?
- Sound check report if you still hear nothing.
- Two players: which board and rules are most fun? Are the penalties (upkeep 0.25/s per extra busy slot,
  −25 per added slot, −3 per queue place jumped) too harsh or too soft? Is the compact layout readable
  from the other side of the table?
- New pattern / photo levels: a screenshot or two.
- Harder options and scores: are the bonuses (+10% to +25%) and penalties (−5 per undo, −25 per hint or
  assist) fair? Would you like a time bonus as well (right now time only breaks ties)?
- The Literature scenes: does each one say its book at a glance? Which would you redraw, drop or swap
  for another favourite (any book published before 1931 can be drawn)?
- The seven newest packs: does each picture read at game size (the Rocket, the loom, the Hubble Deep Field
  and the café wall are the ones I'm least sure of)? Is the *In season* badge enough, or should the
  seasonal pack move to the top of Home in its season?
- The other new pictures: do they read clearly at game size? More subjects you'd like (sport, music,
  your own town)?
- The collection: do the shelves make 193 mosaics easy to find? Is *three found, one more per finish*
  the right pace, or should more be found at once? Do the stars, the flame and the *harder step* on the
  finish card make you want to replay?
- The one-tap return: is it too easy to hit by accident, or is Undo enough of a safety net?

## Sharing the ZIP

On the iPad: in **Files**, long-press the ZIP → **Share** → AirDrop, Messages or Mail. For a link,
put the ZIP in iCloud Drive, long-press → **Share** → **Copy Link** (or *Collaborate → Anyone with the link*).
Whoever receives it follows the setup steps above. On a Mac, double-click `TesseraColony.swiftpm` to
open it in Xcode.

## Regenerating art and levels (optional, needs Python 3 + numpy, scipy, Pillow)

```
cd Tools
python3 art.py art.json
python3 generate_levels.py art.json ../TesseraColony.swiftpm/LevelData.swift report.json 2   # ~5 hours on 2 cores (Challenge, Master, collection and Literature searches)
python3 tests.py report.json ../TesseraColony.swiftpm/LevelData.swift results.json           # about an hour on 2 cores
# only the play-session checks (crash hunt), merged into an existing results file (~7 minutes):
python3 run_session_tests.py report.json results.json
# rebuild only some levels (same seeds) and merge them into an existing report:
python3 regen_some.py art.json report.json ../TesseraColony.swiftpm/LevelData.swift report.json masterViaduct,masterSkyline
# the 168 collection, Literature, new and seasonal levels on their own (resumable; ~7 hours on 2 cores), then merge:
python3 build_collection.py build coll 2
python3 build_collection.py merge coll report.json report.json ../TesseraColony.swiftpm/LevelData.swift
```
The level data is written to `LevelData.swift` plus `LevelDataCollection.swift`, `LevelDataLiterature.swift`,
`LevelDataDiscovery.swift` and `LevelDataSeasons.swift` (extensions of the same `GeneratedLevels` enum), so no
single Swift file is huge.
