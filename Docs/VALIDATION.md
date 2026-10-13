# Validation summary

**Bottom line:** the game rules and all **193** built-in mosaics — including the **56 newest** in seven
packs (Natural History, World Craft, Geometry & Illusions, Probes & Telescopes, Inventions & Firsts, and
the seasonal Halloween and Winter) — with their difficulty measurements, ant timing and every ant-path
style, slots, recovery, the harder options, scoring and high-score tables, the pattern generator, photo
levels, the sound sets, two-player mode and whole play sessions mirrored step by step from the Swift game
screen were tested against a Python reference model that mirrors the Swift code (**4,438 automated checks,
all passing**, about 123 minutes). **I cannot compile Swift here**: no Swift toolchain was reachable from my
build environment. The 137-mosaic build compiled and ran on your iPad; this round's changes — the crash
hardening, the crash report (`FlightRecorder.swift`), the *Ant stress* self-test, the seven new packs, the
Seasons theme and its *In season* badge, and two new level-data files (`LevelDataDiscovery.swift`,
`LevelDataSeasons.swift`) — have only been checked by reading them and by the scans below, so your next
build is their first compile.

## New packs and Seasons (3 Oct)

56 new mosaics in seven packs of eight, each picture an original tile composition (no lettering, logos or
protected designs), each pack ordered from its gentlest to its hardest by measured ratings:
*Natural History* (opens after any Garden mosaic), *World Craft* (after any World Art mosaic), *Geometry &
Illusions* (after any Challenge mosaic), *Probes & Telescopes* (after any Sky & Science mosaic),
*Inventions & Firsts* (after any Modern Moments mosaic), and the seasonal *Halloween* and *Winter* (after
First Dig). The seasonal packs are playable all year and sit under a new **Seasons** theme near the top of
Home; the one in season (Halloween 20 Sep – 7 Nov, Winter 1 Dec – 28 Feb) wears an **In season** badge. The
137 earlier mosaics are **byte-identical**. See the level table below and `Renders/seven_new_packs.png`.

## Crash report: Alhambra Tiles (3 Oct)

You reported: the game crashed on **Alhambra Tiles**, on **Expert**, with the mosaic **nearly finished**
and the ants on **Curious**.

**What I checked.** I read every code path that runs while a game is played and finished — sending,
undo, returning a waiting team, adding a slot, hints, the ant scheduler and route planner, the ant pose
and trail maths, the slots panel, the board and nest drawing, the tile and goal sounds, the finish (stars,
found mosaics, the harder step, scores) — looking for anything that stops a Swift app: a number that is
infinite or not a number turned into an integer, an array index out of range, a range whose end is below
its start, a forced unwrap, an integer overflow. Then I wrote `Tools/session_sim.py`, which plays **whole
sessions through a step-by-step mirror of the Swift game screen** (including the parts only the app has:
ants removed once home, the slots panel, the scout trails, the pose maths) and checks every one of those
traps explicitly, plus every new ant route. **291 sessions** — 84 on Alhambra Tiles on Expert (12 with each
of the 7 path styles), 12 on Classic with Curious ants, one careless Expert session with Curious ants on
every one of the 193 mosaics, and the app's new *Ant stress* sequence — follow the designed line part of
the way (often to within a few moves of the end), then send, undo, return waiting teams and add slots at
random moments, and let the last ants walk home: about **762,000 ants planned and 86 million ant poses
drawn, with nothing that would stop the app and every route legal**. (Before writing the tests I also ran
560 similar sessions on Alhambra Tiles while hunting: none failed.)

**What that means, honestly.** I could not reproduce the crash. It is not in the rules, the ant
scheduler, the route planner or the pose maths as far as a faithful mirror can show — or it depends on
something only the iPad has: the audio system, SwiftUI's drawing, memory, or a step I haven't mirrored.
So this build does three things:

1. **Hardening** in the places that run every frame or at the end of a game: an ant route can never be
   empty and its stops are always finite numbers; the scheduler never turns an infinite or absurd time
   into an integer; the ant pose and trail maths refuse non-finite times; the colour swatches, the nest
   miniature, the time display and the "next slot frees in" text guard their number conversions; and the
   sound player re-checks that iOS hasn't stopped the audio engine (it does that on its own when the
   audio route changes or another app interrupts) right before starting a sound — starting one then is
   one way an app can be stopped.
2. **A crash report.** While a game is open, the app keeps a small record: the mosaic, difficulty, harder
   options, ant paths, speed, the move list, a status line every two seconds and the last 60 actions. If
   the app stops mid-game, **Home shows "Last time, the game didn't close normally"** next launch, with
   **Copy report** — paste it to me and I can replay that exact game in the reference model. Leaving a
   game normally (the X, finishing, the app going to the background) doesn't leave a report. The
   self-test uses it too.
3. **A new self-test, *Ant stress*** (it runs first): the real Swift engine, scheduler and pose code play
   Alhambra Tiles on Expert with Curious ants and with Random per ant — the designed line to ten moves
   from the end, then random sends, undos, returns and added slots — checking every route and every ant
   pose. If the crash is in that code, this test will reproduce it on your iPad, and the report will say
   at which step.

## A. Checks I actually ran (4,438 automated checks, all passing)

Run with `python3 Tools/tests.py …` on the 193-mosaic build (full results and metrics in
`Docs/data/test_results.json`).

| Area | What was checked | Result |
|---|---|---|
| Solvability | The designed solution clears all **193** built-in mosaics (5 main, 8 Garden, 4 Challenge, 8 Master, 56 collection, 56 Literature, 56 new) at Expert, Classic and Gentle slot counts | Pass (579/579) |
| **Slot rule, in real time** | A player following the solution in game time only sends into an open slot; every level completes at Expert and Classic; slots in use never exceed the limit | Pass (386/386) |
| Legal ant claims | Every claim on every level (355,784 tiles): starts at the hill hole, 4-neighbour steps, only open cells, ends beside its tile; no tile twice; right colour | Pass (193/193) |
| Golden values | Each level's claim hash exported to the Swift level data matches the reference model (the in-app self-test re-derives them on the iPad). The 137 earlier levels are **byte-identical** to the previous build | Pass (193/193) |
| Timing, undo, saves, hints | Pickup timing and hole spacing at three move gaps; exact undo; saved moves replay identically; careless play with recovery always finishes; hints win from a fresh start and give a move or "undo N" after mistakes; old saves with Hold still win — on all 193 levels | Pass |
| **Different designs** | All 193 built-in mosaics have different titles and subjects, and no two are recolourings of one layout: the similarity of their colour-region maps (normalised mutual information, which ignores which colours are used) is at most 0.41 for any pair (gardenTulips / gardenDesert; bar 0.45); for any pair involving one of the 56 new mosaics, at most 0.37 | Pass (2/2) |
| **Collection packs** | All 21 collection packs (nature, art, history, science, literature, the five new packs and the two seasonal ones) have their 8 mosaics; each is **ordered from gentlest to hardest** (its Classic rating, then Expert, never goes down along the pack) and **spans the range** (every pack starts Relaxed or Steady and reaches Hard or Fiendish on Classic); every one of the 168 can be won by the look-ahead player (the hint's rollouts) on Gentle or Classic — it wins all three difficulties on 153, two on 13, one on 2 — and the designed line wins on all three | Pass (64/64) |
| **Master pack** | Unchanged: one-step play fails on Classic and Expert on all 8 (and on Gentle on 6); careless tapping wins ≤ 20% on Classic and ≤ 10% on Expert; the look-ahead player wins at least two of the three difficulties on each | Pass (24/24) |
| Challenge pack | Unchanged: one-step wins on Gentle, fails on Classic and Expert; careless ≤ 40% / ≤ 20%; look-ahead wins Classic and Expert | Pass (12/12) |
| Catalogue | All 193 generated mosaics appear exactly once in the app's twenty-five packs with the right pack tag | Pass (2/2) |
| **Harder options** | *No colour twice* keeps every mosaic solvable: a search found a winning line that obeys the rule on all 193 mosaics on Expert, with no undo or assists (at most 5,062 search nodes). The other options only remove help, and the designed line needs none | Pass |
| **Scores & high scores** | The score formula on 5 golden cases (shared with the Swift self-test); places on a table (score, then time; top 5; 0 never counts); 40 random inserts keep the best 5 in order and match the predicted place | Pass (3/3) |
| **Route planning** | All 7 path styles give legal routes on First Dig, Night Market, Labyrinth and Rose Window; no send goes past its 16,000-step search budget; levels are no longer than before (every style within 1.08× of Direct) | Pass (12/12) |
| **Play sessions (crash report)** | 291 whole sessions mirrored step by step from the Swift game screen (`Tools/session_sim.py`): Alhambra Tiles on Expert with each of the 7 path styles (12 each) and on Classic with Curious ants (12), one Expert session with Curious ants on every one of the 193 mosaics, and the in-app *Ant stress* sequence. Designed line part of the way, then careless sends, undos, returns and added slots at random moments; every step that would stop the Swift app (Int of inf/NaN, index out of range, empty route, non-finite pose) is checked, and every new route is legal and correctly timed | Pass (10/10) |
| Two players | All 16 option combinations on First Dig and Nesting Rings with careless and greedy players (96 matches), claim by claim; limits and rules never broken; every match ends; timed matches finish | Pass (8/8) |
| Sound | 38 effects clean; loudest moment 0.82; clink timing exact at steady speed, ≤ 30 ms through speed changes; ≤ 19 clinks a second at 16× | Pass |
| Pattern / photo levels, colours | 40 pattern mosaics solvable with legal ant paths; the 40 seeds cover all five layouts and no two are recoloured copies (most similar pair 0.77, bar 0.9); 4 synthetic photos × 3 detail levels solvable; closest cross-family tones ΔE2000 18.5 | Pass |

Not covered by the reference model: the collection's *found / explored / mastered* bookkeeping and the
Home layout are Swift-only (the rules they follow are simple — first three of an open pack found, one
more per finish; stars = hardest difficulty finished; flame = Expert with a harder option — and the
in-app self-test checks the harder-step chain and the catalogue). The same goes for the Seasons theme's
*In season* badge (the self-test checks its dates, including Winter's wrap across the new year).

Other checks: the Swift sources (38 files) were scanned for balanced braces, brackets and parentheses
(strings and comments stripped) and for references to controller / app / settings / engine members that
don't exist — none found. This catches typos but is **not a compile**.

### Levels (reference model)

Careless = random taps with no undo or assists (40 games per difficulty); one-step = always send the team
that can finish now; look-ahead = the hint's rollout player (measured for Challenge and Master).
Rating: 1 Relaxed · 2 Steady · 3 Tricky · 4 Hard · 5 Fiendish.

| Pack | Mosaic | Tiles / teams | Slots G / C / E | Careless wins G / C / E | One-step wins G / C / E | Look-ahead wins G / C / E | Rating G / C / E |
|---|---|---|---|---|---|---|---|
| Main | First Dig | 1,008 / 17 | 5 / 3 / 2 | 100% / 92% / 35% | ✓ / ✓ / ✗ | — | 1 / 1 / 4 |
| Main | Koi Pond | 2,464 / 25 | 5 / 3 / 2 | 95% / 42% / 5% | ✓ / ✓ / ✗ | — | 1 / 2 / 5 |
| Main | Peacock Fan | 2,704 / 39 | 6 / 4 / 3 | 98% / 65% / 25% | ✓ / ✓ / ✗ | — | 1 / 2 / 4 |
| Main | Night Market | 3,584 / 46 | 6 / 4 / 3 | 48% / 8% / 0% | ✓ / ✗ / ✗ | — | 2 / 5 / 5 |
| Main | Sunflower & Monarch | 6,048 / 81 | 6 / 4 / 3 | 75% / 38% / 10% | ✓ / ✗ / ✗ | — | 1 / 4 / 5 |
| Challenge | Nesting Rings | 1,760 / 48 | 7 / 5 / 4 | 88% / 35% / 2% | ✓ / ✗ / ✗ | ✓ / ✓ / ✓ | 1 / 4 / 5 |
| Challenge | Basket Weave | 1,760 / 51 | 7 / 5 / 4 | 45% / 15% / 15% | ✓ / ✗ / ✗ | ✓ / ✓ / ✓ | 2 / 4 / 4 |
| Challenge | Labyrinth | 1,845 / 60 | 6 / 4 / 3 | 80% / 10% / 2% | ✓ / ✗ / ✗ | ✓ / ✓ / ✓ | 1 / 5 / 5 |
| Challenge | Rose Window | 1,760 / 54 | 6 / 4 / 3 | 62% / 5% / 0% | ✓ / ✗ / ✗ | ✓ / ✓ / ✓ | 2 / 5 / 5 |
| Garden | Hot-Air Balloon | 1,760 / 28 | 6 / 4 / 3 | 88% / 28% / 12% | ✓ / ✗ / ✗ | — | 1 / 4 / 4 |
| Garden | Lighthouse | 1,760 / 31 | 6 / 4 / 3 | 100% / 82% / 45% | ✓ / ✓ / ✗ | — | 1 / 1 / 4 |
| Garden | Toadstools | 1,760 / 22 | 6 / 4 / 3 | 92% / 80% / 55% | ✗ / ✗ / ✗ | — | 4 / 4 / 4 |
| Garden | Tulip Bed | 1,760 / 29 | 6 / 4 / 3 | 98% / 57% / 38% | ✓ / ✓ / ✓ | — | 1 / 2 / 2 |
| Garden | Evening Sail | 1,760 / 29 | 6 / 4 / 3 | 88% / 72% / 48% | ✓ / ✓ / ✓ | — | 1 / 2 / 2 |
| Garden | Honeycomb | 1,760 / 27 | 6 / 4 / 3 | 100% / 100% / 80% | ✓ / ✓ / ✓ | — | 1 / 1 / 1 |
| Garden | Owl | 1,760 / 29 | 6 / 4 / 3 | 100% / 85% / 65% | ✓ / ✓ / ✓ | — | 1 / 1 / 2 |
| Garden | Desert Bloom | 1,760 / 26 | 6 / 4 / 3 | 85% / 50% / 30% | ✓ / ✓ / ✗ | — | 1 / 2 / 4 |
| Master | **Tiger** | 1,932 / 66 | 6 / 4 / 3 | 72% / 18% / 2% | ✗ / ✗ / ✗ | ✓ / ✓ / ✓ | 4 / 4 / 5 |
| Master | **Giraffe** | 1,932 / 79 | 7 / 5 / 4 | 82% / 20% / 5% | ✗ / ✗ / ✗ | ✓ / ✓ / ✓ | 4 / 4 / 5 |
| Master | **Autumn Tree** | 1,932 / 71 | 7 / 5 / 4 | 50% / 8% / 2% | ✗ / ✗ / ✗ | ✓ / ✓ / ✓ | 4 / 5 / 5 |
| Master | **Castle** | 1,932 / 74 | 6 / 4 / 3 | 15% / 2% / 0% | ✗ / ✗ / ✗ | ✓ / ✓ / ✓ | 4 / 5 / 5 |
| Master | **Viaduct** | 1,932 / 81 | 6 / 4 / 3 | 35% / 2% / 0% | ✗ / ✗ / ✗ | ✓ / ✓ / ✗ | 4 / 5 / 5 |
| Master | **City at Dusk** | 1,932 / 68 | 6 / 4 / 3 | 75% / 10% / 5% | ✓ / ✗ / ✗ | ✓ / ✓ / ✓ | 1 / 5 / 5 |
| Master | **Chameleon** | 1,932 / 79 | 7 / 5 / 4 | 60% / 18% / 2% | ✓ / ✗ / ✗ | ✓ / ✓ / ✓ | 2 / 4 / 5 |
| Master | **Octopus** | 1,932 / 79 | 6 / 4 / 3 | 10% / 8% / 2% | ✗ / ✗ / ✗ | ✓ / ✓ / ✓ | 5 / 5 / 5 |
| Wild Wonders | Iceberg | 1,764 / 28 | 5 / 3 / 2 | 100% / 98% / 40% | ✓ / ✓ / ✓ | ✓ / ✓ / ✓ | 1 / 1 / 2 |
| Wild Wonders | Northern Lights | 1,760 / 28 | 6 / 4 / 3 | 92% / 70% / 25% | ✓ / ✓ / ✓ | ✓ / ✓ / ✓ | 1 / 2 / 3 |
| Wild Wonders | Rainforest | 1,932 / 63 | 6 / 4 / 3 | 98% / 20% / 0% | ✓ / ✓ / ✗ | ✓ / ✓ / ✓ | 1 / 3 / 5 |
| Wild Wonders | Bamboo Grove | 1,932 / 69 | 7 / 5 / 4 | 100% / 90% / 52% | ✓ / ✗ / ✗ | ✓ / ✓ / ✓ | 1 / 4 / 4 |
| Wild Wonders | Grand Canyon | 1,728 / 27 | 6 / 4 / 3 | 95% / 75% / 25% | ✗ / ✗ / ✗ | ✓ / ✓ / ✓ | 4 / 4 / 4 |
| Wild Wonders | Victoria Falls | 1,840 / 29 | 6 / 4 / 3 | 88% / 30% / 12% | ✗ / ✗ / ✗ | ✓ / ✓ / ✓ | 4 / 4 / 4 |
| Wild Wonders | Volcano | 1,840 / 56 | 7 / 5 / 4 | 52% / 10% / 0% | ✓ / ✗ / ✗ | ✓ / ✓ / ✓ | 2 / 5 / 5 |
| Wild Wonders | Coral Reef | 1,932 / 80 | 6 / 4 / 3 | 42% / 5% / 0% | ✓ / ✗ / ✗ | ✓ / ✓ / ✓ | 2 / 5 / 5 |
| Gallery | Impression, Sunrise | 1,728 / 24 | 6 / 4 / 3 | 100% / 100% / 48% | ✓ / ✓ / ✓ | ✓ / ✓ / ✓ | 1 / 1 / 2 |
| Gallery | Girl with a Pearl Earring | 1,584 / 28 | 6 / 4 / 3 | 90% / 52% / 22% | ✓ / ✓ / ✓ | ✓ / ✓ / ✓ | 1 / 2 / 3 |
| Gallery | Mona Lisa | 1,728 / 25 | 6 / 4 / 3 | 92% / 48% / 22% | ✓ / ✓ / ✗ | ✓ / ✓ / ✓ | 1 / 2 / 4 |
| Gallery | The Water Lily Pond | 1,764 / 26 | 6 / 4 / 3 | 75% / 45% / 28% | ✗ / ✗ / ✗ | ✓ / ✓ / ✓ | 4 / 4 / 4 |
| Gallery | The Starry Night | 1,824 / 56 | 7 / 5 / 4 | 85% / 38% / 5% | ✓ / ✗ / ✗ | ✓ / ✓ / ✓ | 1 / 4 / 5 |
| Gallery | La Grande Jatte | 1,728 / 67 | 7 / 5 / 4 | 95% / 20% / 8% | ✓ / ✗ / ✗ | ✓ / ✓ / ✓ | 1 / 4 / 5 |
| Gallery | The Kiss | 1,764 / 67 | 7 / 5 / 4 | 70% / 25% / 5% | ✗ / ✗ / ✗ | ✓ / ✓ / ✗ | 4 / 4 / 5 |
| Gallery | The Scream | 1,920 / 55 | 7 / 5 / 4 | 25% / 5% / 0% | ✓ / ✗ / ✗ | ✓ / ✓ / ✓ | 3 / 5 / 5 |
| World Art | Ming Vase | 1,656 / 26 | 6 / 4 / 3 | 100% / 98% / 80% | ✓ / ✓ / ✓ | ✓ / ✓ / ✓ | 1 / 1 / 1 |
| World Art | Several Circles | 1,764 / 23 | 6 / 4 / 3 | 100% / 85% / 62% | ✓ / ✓ / ✓ | ✓ / ✓ / ✓ | 1 / 1 / 2 |
| World Art | The Great Wave | 1,632 / 25 | 5 / 3 / 2 | 92% / 65% / 48% | ✓ / ✓ / ✓ | ✓ / ✓ / ✓ | 1 / 2 / 2 |
| World Art | Sudden Shower | 1,728 / 30 | 6 / 4 / 3 | 95% / 70% / 15% | ✓ / ✗ / ✗ | ✓ / ✓ / ✓ | 1 / 4 / 4 |
| World Art | Alhambra Tiles | 1,936 / 51 | 7 / 5 / 4 | 55% / 20% / 0% | ✗ / ✗ / ✗ | ✓ / ✓ / ✗ | 4 / 4 / 5 |
| World Art | Sun Stone | 1,936 / 64 | 6 / 4 / 3 | 52% / 5% / 0% | ✓ / ✗ / ✗ | ✓ / ✓ / ✓ | 2 / 5 / 5 |
| World Art | Starry Vault | 1,932 / 63 | 6 / 4 / 3 | 18% / 2% / 2% | ✓ / ✗ / ✗ | ✓ / ✗ / ✗ | 3 / 5 / 5 |
| World Art | Composition | 1,764 / 65 | 6 / 4 / 3 | 32% / 0% / 2% | ✓ / ✗ / ✗ | ✓ / ✓ / ✓ | 3 / 5 / 5 |
| Ancient World | Stonehenge | 1,728 / 27 | 6 / 4 / 3 | 90% / 70% / 22% | ✓ / ✓ / ✗ | ✓ / ✓ / ✓ | 1 / 2 / 4 |
| Ancient World | Lascaux Cave | 1,728 / 24 | 6 / 4 / 3 | 70% / 48% / 32% | ✓ / ✓ / ✗ | ✓ / ✓ / ✓ | 2 / 2 / 4 |
| Ancient World | First Olympics | 1,748 / 52 | 7 / 5 / 4 | 40% / 10% / 2% | ✓ / ✓ / ✓ | ✓ / ✓ / ✓ | 2 / 3 / 3 |
| Ancient World | Golden Mask | 1,748 / 53 | 6 / 4 / 3 | 92% / 40% / 18% | ✓ / ✗ / ✗ | ✓ / ✓ / ✓ | 1 / 4 / 4 |
| Ancient World | Terracotta Army | 1,760 / 77 | 6 / 4 / 3 | 100% / 52% / 0% | ✓ / ✗ / ✗ | ✓ / ✓ / ✓ | 1 / 4 / 5 |
| Ancient World | The Great Wall | 1,760 / 55 | 7 / 5 / 4 | 90% / 12% / 0% | ✓ / ✗ / ✗ | ✓ / ✓ / ✓ | 1 / 4 / 5 |
| Ancient World | The Great Pyramid | 1,680 / 27 | 6 / 4 / 3 | 68% / 18% / 8% | ✓ / ✗ / ✗ | ✓ / ✓ / ✓ | 2 / 4 / 5 |
| Ancient World | The Colosseum | 1,840 / 62 | 7 / 5 / 4 | 32% / 12% / 2% | ✗ / ✗ / ✗ | ✓ / ✓ / ✓ | 4 / 4 / 5 |
| Voyages | Treasure Ship | 1,848 / 27 | 6 / 4 / 3 | 100% / 95% / 72% | ✓ / ✓ / ✓ | ✓ / ✓ / ✓ | 1 / 1 / 2 |
| Voyages | Silk Road | 1,728 / 26 | 6 / 4 / 3 | 100% / 92% / 48% | ✓ / ✓ / ✓ | ✓ / ✓ / ✓ | 1 / 1 / 2 |
| Voyages | Wayfinders | 1,760 / 29 | 6 / 4 / 3 | 98% / 80% / 48% | ✓ / ✓ / ✓ | ✓ / ✓ / ✓ | 1 / 1 / 2 |
| Voyages | Viking Longship | 1,748 / 27 | 6 / 4 / 3 | 100% / 50% / 38% | ✓ / ✓ / ✗ | ✓ / ✓ / ✓ | 1 / 2 / 4 |
| Voyages | Printing Press | 1,760 / 53 | 7 / 5 / 4 | 80% / 38% / 0% | ✓ / ✗ / ✗ | ✓ / ✓ / ✓ | 1 / 4 / 5 |
| Voyages | Galileo's Moons | 1,848 / 61 | 6 / 4 / 3 | 78% / 28% / 0% | ✓ / ✗ / ✗ | ✓ / ✓ / ✓ | 1 / 4 / 5 |
| Voyages | Galápagos | 1,848 / 74 | 7 / 5 / 4 | 20% / 8% / 0% | ✗ / ✗ / ✗ | ✓ / ✓ / ✓ | 4 / 5 / 5 |
| Voyages | South Pole | 1,764 / 73 | 6 / 4 / 3 | 60% / 2% / 0% | ✗ / ✗ / ✗ | ✗ / ✓ / ✓ | 4 / 5 / 5 |
| Modern Moments | Liberty | 1,728 / 28 | 6 / 4 / 3 | 98% / 85% / 20% | ✓ / ✓ / ✓ | ✓ / ✓ / ✓ | 1 / 1 / 3 |
| Modern Moments | First Flight | 1,728 / 23 | 6 / 4 / 3 | 98% / 60% / 35% | ✓ / ✓ / ✗ | ✓ / ✓ / ✓ | 1 / 2 / 4 |
| Modern Moments | Eiffel Tower | 1,824 / 22 | 6 / 4 / 3 | 82% / 48% / 25% | ✓ / ✓ / ✗ | ✓ / ✓ / ✓ | 1 / 2 / 4 |
| Modern Moments | Golden Gate | 1,824 / 23 | 6 / 4 / 3 | 70% / 42% / 20% | ✗ / ✗ / ✗ | ✓ / ✓ / ✓ | 4 / 4 / 4 |
| Modern Moments | Sputnik | 1,764 / 59 | 6 / 4 / 3 | 88% / 25% / 5% | ✓ / ✗ / ✗ | ✓ / ✓ / ✓ | 1 / 4 / 5 |
| Modern Moments | Berlin Wall | 1,840 / 59 | 7 / 5 / 4 | 100% / 22% / 2% | ✓ / ✗ / ✗ | ✓ / ✓ / ✓ | 1 / 4 / 5 |
| Modern Moments | Everest Summit | 1,932 / 66 | 7 / 5 / 4 | 72% / 22% / 2% | ✓ / ✗ / ✗ | ✓ / ✓ / ✓ | 2 / 4 / 5 |
| Modern Moments | Moon Landing | 1,848 / 84 | 6 / 4 / 3 | 80% / 5% / 2% | ✗ / ✗ / ✗ | ✓ / ✓ / ✓ | 4 / 5 / 5 |
| Sky & Science | Halley's Comet | 1,760 / 29 | 6 / 4 / 3 | 100% / 95% / 48% | ✓ / ✓ / ✓ | ✓ / ✓ / ✓ | 1 / 1 / 2 |
| Sky & Science | Newton's Prism | 1,760 / 29 | 5 / 3 / 2 | 100% / 80% / 42% | ✓ / ✓ / ✗ | ✓ / ✓ / ✓ | 1 / 1 / 4 |
| Sky & Science | Saturn | 1,748 / 23 | 6 / 4 / 3 | 82% / 25% / 18% | ✓ / ✓ / ✓ | ✓ / ✓ / ✓ | 1 / 3 / 3 |
| Sky & Science | Total Eclipse | 1,764 / 25 | 6 / 4 / 3 | 62% / 35% / 15% | ✗ / ✗ / ✗ | ✓ / ✗ / ✗ | 4 / 4 / 4 |
| Sky & Science | Spiral Galaxy | 1,936 / 47 | 6 / 4 / 3 | 100% / 28% / 5% | ✓ / ✗ / ✗ | ✓ / ✓ / ✓ | 1 / 4 / 5 |
| Sky & Science | Periodic Table | 1,728 / 59 | 6 / 4 / 3 | 48% / 15% / 2% | ✓ / ✗ / ✗ | ✓ / ✓ / ✓ | 2 / 4 / 5 |
| Sky & Science | Franklin's Kite | 1,840 / 60 | 6 / 4 / 3 | 90% / 5% / 0% | ✓ / ✗ / ✗ | ✓ / ✓ / ✓ | 1 / 5 / 5 |
| Sky & Science | Double Helix | 1,824 / 66 | 7 / 5 / 4 | 18% / 0% / 0% | ✗ / ✗ / ✗ | ✓ / ✓ / ✓ | 4 / 5 / 5 |
| Epics & Legends | The Sirens | 1,728 / 24 | 6 / 4 / 3 | 100% / 85% / 42% | ✓ / ✓ / ✓ | ✓ / ✓ / ✓ | 1 / 1 / 2 |
| Epics & Legends | The Monkey King | 1,932 / 57 | 6 / 4 / 3 | 100% / 48% / 18% | ✓ / ✓ / ✗ | ✓ / ✓ / ✓ | 1 / 2 / 4 |
| Epics & Legends | The Trojan Horse | 1,760 / 24 | 5 / 3 / 2 | 100% / 95% / 78% | ✓ / ✗ / ✗ | ✓ / ✓ / ✓ | 1 / 4 / 4 |
| Epics & Legends | The Sword in the Stone | 1,656 / 25 | 6 / 4 / 3 | 100% / 55% / 18% | ✓ / ✗ / ✗ | ✓ / ✓ / ✓ | 1 / 4 / 4 |
| Epics & Legends | The Celestial Rose | 1,764 / 27 | 5 / 3 / 2 | 88% / 52% / 8% | ✓ / ✗ / ✗ | ✓ / ✓ / ✓ | 1 / 4 / 5 |
| Epics & Legends | Ali Baba's Cave | 1,848 / 56 | 6 / 4 / 3 | 100% / 8% / 0% | ✓ / ✗ / ✗ | ✓ / ✓ / ✓ | 1 / 5 / 5 |
| Epics & Legends | The Dragon's Hoard | 1,848 / 84 | 7 / 5 / 4 | 70% / 5% / 2% | ✓ / ✗ / ✗ | ✓ / ✓ / ✓ | 2 / 5 / 5 |
| Epics & Legends | Moon over the Palace | 1,848 / 63 | 7 / 5 / 4 | 18% / 0% / 0% | ✗ / ✗ / ✗ | ✓ / ✓ / ✓ | 4 / 5 / 5 |
| Fairy Tales | The Tortoise and the Hare | 1,728 / 27 | 6 / 4 / 3 | 100% / 88% / 55% | ✓ / ✓ / ✓ | ✓ / ✓ / ✓ | 1 / 1 / 2 |
| Fairy Tales | Jack and the Beanstalk | 1,728 / 29 | 6 / 4 / 3 | 100% / 82% / 28% | ✓ / ✓ / ✗ | ✓ / ✓ / ✓ | 1 / 1 / 4 |
| Fairy Tales | Rapunzel | 1,728 / 26 | 6 / 4 / 3 | 100% / 75% / 35% | ✓ / ✓ / ✗ | ✓ / ✓ / ✓ | 1 / 1 / 4 |
| Fairy Tales | The Snow Queen | 1,848 / 61 | 7 / 5 / 4 | 100% / 48% / 12% | ✓ / ✓ / ✓ | ✓ / ✓ / ✓ | 1 / 2 / 3 |
| Fairy Tales | Little Red Riding Hood | 1,760 / 26 | 6 / 4 / 3 | 95% / 55% / 35% | ✓ / ✓ / ✗ | ✓ / ✓ / ✓ | 1 / 2 / 4 |
| Fairy Tales | The Princess and the Pea | 1,840 / 61 | 7 / 5 / 4 | 70% / 18% / 2% | ✓ / ✗ / ✗ | ✓ / ✓ / ✓ | 2 / 4 / 5 |
| Fairy Tales | Cinderella's Midnight | 1,840 / 53 | 6 / 4 / 3 | 40% / 8% / 2% | ✓ / ✗ / ✗ | ✓ / ✓ / ✓ | 2 / 5 / 5 |
| Fairy Tales | The Gingerbread House | 1,848 / 75 | 6 / 4 / 3 | 20% / 0% / 0% | ✗ / ✗ / ✗ | ✓ / ✓ / ✗ | 4 / 5 / 5 |
| Children's Classics | The Yellow Brick Road | 1,848 / 21 | 6 / 4 / 3 | 100% / 100% / 52% | ✓ / ✓ / ✗ | ✓ / ✓ / ✓ | 1 / 1 / 4 |
| Children's Classics | Messing About in Boats | 1,728 / 29 | 5 / 3 / 2 | 88% / 60% / 25% | ✓ / ✓ / ✓ | ✓ / ✓ / ✓ | 1 / 2 / 3 |
| Children's Classics | The Secret Garden | 1,656 / 29 | 6 / 4 / 3 | 100% / 45% / 2% | ✓ / ✓ / ✓ | ✓ / ✓ / ✓ | 1 / 2 / 3 |
| Children's Classics | The Railway Children | 1,728 / 28 | 6 / 4 / 3 | 95% / 85% / 30% | ✗ / ✗ / ✗ | ✓ / ✓ / ✓ | 4 / 4 / 4 |
| Children's Classics | The Council Rock | 1,932 / 66 | 6 / 4 / 3 | 68% / 8% / 0% | ✓ / ✗ / ✗ | ✓ / ✓ / ✓ | 2 / 5 / 5 |
| Children's Classics | Inside the Dogfish | 1,848 / 70 | 7 / 5 / 4 | 42% / 5% / 0% | ✓ / ✗ / ✗ | ✓ / ✓ / ✗ | 2 / 5 / 5 |
| Children's Classics | The Mad Tea-Party | 1,824 / 55 | 6 / 4 / 3 | 48% / 2% / 2% | ✓ / ✗ / ✗ | ✓ / ✓ / ✓ | 2 / 5 / 5 |
| Children's Classics | Through the Looking-Glass | 1,936 / 67 | 6 / 4 / 3 | 15% / 2% / 0% | ✗ / ✗ / ✗ | ✓ / ✓ / ✗ | 4 / 5 / 5 |
| Shakespeare | The Three Witches | 1,848 / 26 | 6 / 4 / 3 | 100% / 98% / 82% | ✓ / ✓ / ✓ | ✓ / ✓ / ✓ | 1 / 1 / 1 |
| Shakespeare | The Balcony | 1,748 / 27 | 6 / 4 / 3 | 100% / 88% / 28% | ✓ / ✓ / ✓ | ✓ / ✓ / ✓ | 1 / 1 / 3 |
| Shakespeare | The Shipwreck | 1,728 / 27 | 6 / 4 / 3 | 100% / 95% / 80% | ✓ / ✓ / ✗ | ✓ / ✓ / ✓ | 1 / 1 / 4 |
| Shakespeare | Alas, Poor Yorick | 1,764 / 29 | 5 / 3 / 2 | 100% / 40% / 5% | ✓ / ✓ / ✓ | ✓ / ✓ / ✓ | 1 / 2 / 3 |
| Shakespeare | The Fairy Wood | 1,932 / 62 | 7 / 5 / 4 | 82% / 22% / 2% | ✓ / ✗ / ✗ | ✓ / ✓ / ✓ | 1 / 4 / 5 |
| Shakespeare | Cleopatra's Barge | 1,728 / 49 | 6 / 4 / 3 | 72% / 38% / 0% | ✓ / ✗ / ✗ | ✓ / ✓ / ✓ | 2 / 4 / 5 |
| Shakespeare | The Globe | 1,936 / 74 | 6 / 4 / 3 | 35% / 2% / 0% | ✗ / ✗ / ✗ | ✓ / ✓ / ✗ | 4 / 5 / 5 |
| Shakespeare | The Three Caskets | 1,848 / 71 | 7 / 5 / 4 | 22% / 0% / 0% | ✗ / ✗ / ✗ | ✓ / ✓ / ✓ | 4 / 5 / 5 |
| Adventure Classics | Tilting at Windmills | 1,728 / 25 | 6 / 4 / 3 | 100% / 85% / 48% | ✓ / ✓ / ✓ | ✓ / ✓ / ✓ | 1 / 1 / 2 |
| Adventure Classics | Gulliver in Lilliput | 1,824 / 28 | 6 / 4 / 3 | 98% / 80% / 25% | ✓ / ✓ / ✗ | ✓ / ✓ / ✓ | 1 / 1 / 4 |
| Adventure Classics | The Nautilus | 1,848 / 74 | 6 / 4 / 3 | 98% / 60% / 2% | ✓ / ✓ / ✗ | ✓ / ✓ / ✓ | 1 / 2 / 5 |
| Adventure Classics | The Underground Sea | 1,728 / 52 | 6 / 4 / 3 | 90% / 25% / 5% | ✓ / ✓ / ✓ | ✓ / ✓ / ✓ | 1 / 3 / 3 |
| Adventure Classics | The Raft | 1,728 / 25 | 6 / 4 / 3 | 92% / 72% / 28% | ✓ / ✗ / ✗ | ✓ / ✓ / ✓ | 1 / 4 / 4 |
| Adventure Classics | The White Whale | 1,848 / 58 | 7 / 5 / 4 | 98% / 57% / 38% | ✓ / ✗ / ✗ | ✓ / ✓ / ✓ | 1 / 4 / 4 |
| Adventure Classics | The Footprint | 1,848 / 28 | 6 / 4 / 3 | 78% / 57% / 22% | ✓ / ✗ / ✗ | ✓ / ✓ / ✓ | 1 / 4 / 4 |
| Adventure Classics | The Treasure Map | 1,848 / 76 | 7 / 5 / 4 | 85% / 18% / 0% | ✗ / ✗ / ✗ | ✓ / ✓ / ✓ | 4 / 4 / 5 |
| Gothic & Mystery | The Raven | 1,656 / 25 | 6 / 4 / 3 | 90% / 75% / 48% | ✓ / ✓ / ✓ | ✓ / ✓ / ✓ | 1 / 1 / 2 |
| Gothic & Mystery | The Hound on the Moor | 1,728 / 26 | 6 / 4 / 3 | 100% / 50% / 25% | ✓ / ✓ / ✗ | ✓ / ✓ / ✓ | 1 / 2 / 4 |
| Gothic & Mystery | The Bells of Notre-Dame | 1,748 / 28 | 6 / 4 / 3 | 95% / 42% / 30% | ✓ / ✓ / ✗ | ✓ / ✓ / ✓ | 1 / 2 / 4 |
| Gothic & Mystery | Across the Ice | 1,728 / 50 | 6 / 4 / 3 | 88% / 28% / 8% | ✓ / ✗ / ✗ | ✓ / ✓ / ✓ | 1 / 4 / 5 |
| Gothic & Mystery | The Headless Horseman | 1,728 / 27 | 6 / 4 / 3 | 95% / 28% / 2% | ✓ / ✗ / ✗ | ✓ / ✓ / ✓ | 1 / 4 / 5 |
| Gothic & Mystery | Castle Dracula | 1,840 / 55 | 6 / 4 / 3 | 100% / 18% / 2% | ✓ / ✗ / ✗ | ✓ / ✓ / ✓ | 1 / 4 / 5 |
| Gothic & Mystery | The Great Chandelier | 1,936 / 67 | 7 / 5 / 4 | 65% / 18% / 5% | ✗ / ✗ / ✗ | ✓ / ✓ / ✓ | 4 / 4 / 5 |
| Gothic & Mystery | The Martian Tripods | 1,848 / 75 | 7 / 5 / 4 | 5% / 0% / 0% | ✗ / ✗ / ✗ | ✓ / ✓ / ✓ | 5 / 5 / 5 |
| Great Novels | Christmas Morning | 1,760 / 30 | 5 / 3 / 2 | 100% / 82% / 50% | ✓ / ✓ / ✓ | ✓ / ✓ / ✓ | 1 / 1 / 2 |
| Great Novels | Wuthering Heights | 1,728 / 29 | 6 / 4 / 3 | 95% / 38% / 10% | ✓ / ✓ / ✗ | ✓ / ✓ / ✓ | 1 / 2 / 5 |
| Great Novels | The Comet of 1812 | 1,848 / 29 | 6 / 4 / 3 | 70% / 15% / 12% | ✓ / ✓ / ✓ | ✓ / ✓ / ✓ | 2 / 3 / 3 |
| Great Novels | Miss Havisham's Room | 1,848 / 54 | 6 / 4 / 3 | 28% / 12% / 2% | ✓ / ✗ / ✗ | ✓ / ✓ / ✓ | 3 / 4 / 5 |
| Great Novels | The Green Light | 1,728 / 24 | 5 / 3 / 2 | 65% / 18% / 10% | ✗ / ✗ / ✗ | ✓ / ✓ / ✓ | 4 / 4 / 5 |
| Great Novels | The Silver Candlesticks | 1,748 / 55 | 6 / 4 / 3 | 68% / 10% / 0% | ✓ / ✗ / ✗ | ✓ / ✓ / ✓ | 2 / 5 / 5 |
| Great Novels | The Netherfield Ball | 1,840 / 55 | 7 / 5 / 4 | 50% / 8% / 0% | ✗ / ✗ / ✗ | ✓ / ✓ / ✓ | 4 / 5 / 5 |
| Great Novels | I Want Some More | 1,848 / 65 | 6 / 4 / 3 | 30% / 0% / 0% | ✗ / ✗ / ✗ | ✓ / ✓ / ✓ | 4 / 5 / 5 |
| Natural History | Audubon's Flamingo | 1,748 / 28 | 4 / 2 / 1 | 88% / 60% / 8% | ✓ / ✓ / ✓ | ✓ / ✓ / ✓ | 1 / 2 / 3 |
| Natural History | Merian's Butterflies | 1,840 / 33 | 6 / 4 / 3 | 88% / 68% / 32% | ✓ / ✓ / ✗ | ✓ / ✓ / ✓ | 1 / 2 / 4 |
| Natural History | Gould's Hummingbirds | 1,840 / 30 | 6 / 4 / 3 | 92% / 65% / 35% | ✓ / ✓ / ✗ | ✓ / ✓ / ✓ | 1 / 2 / 4 |
| Natural History | Redouté's Rose | 1,656 / 26 | 6 / 4 / 3 | 80% / 48% / 35% | ✗ / ✗ / ✗ | ✓ / ✓ / ✓ | 4 / 4 / 4 |
| Natural History | Haeckel's Jellyfish | 1,920 / 58 | 6 / 4 / 3 | 80% / 25% / 5% | ✓ / ✗ / ✗ | ✓ / ✓ / ✓ | 1 / 4 / 5 |
| Natural History | Seba's Shells | 1,936 / 59 | 7 / 5 / 4 | 85% / 8% / 5% | ✓ / ✗ / ✗ | ✓ / ✓ / ✓ | 1 / 5 / 5 |
| Natural History | The Beetle Drawer | 1,840 / 74 | 7 / 5 / 4 | 90% / 8% / 2% | ✓ / ✗ / ✗ | ✓ / ✓ / ✓ | 1 / 5 / 5 |
| Natural History | Haeckel's Radiolarians | 1,932 / 72 | 7 / 5 / 4 | 57% / 8% / 0% | ✗ / ✗ / ✗ | ✓ / ✓ / ✓ | 4 / 5 / 5 |
| World Craft | Pysanky Eggs | 1,824 / 29 | 6 / 4 / 3 | 95% / 68% / 35% | ✓ / ✓ / ✓ | ✓ / ✓ / ✓ | 1 / 2 / 2 |
| World Craft | Talavera Plate | 1,936 / 30 | 6 / 4 / 3 | 100% / 57% / 18% | ✓ / ✓ / ✗ | ✓ / ✓ / ✓ | 1 / 2 / 4 |
| World Craft | Wycinanki | 1,840 / 27 | 6 / 4 / 3 | 88% / 40% / 2% | ✓ / ✓ / ✗ | ✓ / ✓ / ✓ | 1 / 2 / 5 |
| World Craft | Tartan | 1,936 / 59 | 6 / 4 / 3 | 70% / 28% / 10% | ✓ / ✗ / ✗ | ✓ / ✓ / ✓ | 2 / 4 / 5 |
| World Craft | Delft Tiles | 1,968 / 29 | 5 / 3 / 2 | 50% / 18% / 10% | ✗ / ✗ / ✗ | ✓ / ✓ / ✓ | 4 / 4 / 5 |
| World Craft | Persian Carpet | 1,632 / 70 | 7 / 5 / 4 | 78% / 12% / 8% | ✗ / ✗ / ✗ | ✓ / ✓ / ✓ | 4 / 4 / 5 |
| World Craft | Asanoha Kimono | 1,932 / 54 | 6 / 4 / 3 | 15% / 0% / 0% | ✓ / ✗ / ✗ | ✓ / ✓ / ✓ | 3 / 5 / 5 |
| World Craft | Patchwork Quilt | 1,936 / 78 | 6 / 4 / 3 | 50% / 2% / 0% | ✗ / ✗ / ✗ | ✓ / ✗ / ✓ | 4 / 5 / 5 |
| Geometry & Illusions | Mandelbrot Set | 1,840 / 26 | 6 / 4 / 3 | 100% / 68% / 52% | ✓ / ✓ / ✓ | ✓ / ✓ / ✓ | 1 / 2 / 2 |
| Geometry & Illusions | Impossible Triangle | 1,760 / 28 | 5 / 3 / 2 | 90% / 50% / 12% | ✓ / ✓ / ✓ | ✓ / ✓ / ✓ | 1 / 2 / 3 |
| Geometry & Illusions | Golden Spiral | 1,632 / 28 | 5 / 3 / 2 | 42% / 18% / 2% | ✓ / ✓ / ✗ | ✓ / ✓ / ✓ | 2 / 3 / 5 |
| Geometry & Illusions | Sierpiński Triangle | 1,920 / 54 | 6 / 4 / 3 | 32% / 10% / 2% | ✓ / ✓ / ✗ | ✓ / ✓ / ✓ | 3 / 3 / 5 |
| Geometry & Illusions | Café Wall | 1,978 / 60 | 7 / 5 / 4 | 85% / 22% / 10% | ✓ / ✗ / ✗ | ✓ / ✓ / ✓ | 1 / 4 / 5 |
| Geometry & Illusions | Hilbert Curve | 1,681 / 55 | 6 / 4 / 3 | 50% / 8% / 5% | ✓ / ✗ / ✗ | ✓ / ✓ / ✓ | 2 / 5 / 5 |
| Geometry & Illusions | Celtic Knot | 1,936 / 78 | 6 / 4 / 3 | 52% / 8% / 0% | ✗ / ✗ / ✗ | ✓ / ✓ / ✓ | 4 / 5 / 5 |
| Geometry & Illusions | Girih Star | 1,936 / 70 | 6 / 4 / 3 | 10% / 2% / 0% | ✗ / ✗ / ✗ | ✓ / ✓ / ✗ | 5 / 5 / 5 |
| Probes & Telescopes | Earthrise | 1,840 / 28 | 6 / 4 / 3 | 100% / 95% / 85% | ✓ / ✓ / ✓ | ✓ / ✓ / ✓ | 1 / 1 / 1 |
| Probes & Telescopes | Pluto's Heart | 1,764 / 28 | 6 / 4 / 3 | 95% / 45% / 10% | ✓ / ✓ / ✗ | ✓ / ✓ / ✓ | 1 / 2 / 5 |
| Probes & Telescopes | Blue Sunset on Mars | 1,748 / 26 | 6 / 4 / 3 | 100% / 82% / 55% | ✓ / ✗ / ✗ | ✓ / ✓ / ✓ | 1 / 4 / 4 |
| Probes & Telescopes | Pillars of Creation | 1,840 / 60 | 7 / 5 / 4 | 82% / 28% / 8% | ✓ / ✗ / ✗ | ✓ / ✓ / ✓ | 1 / 4 / 5 |
| Probes & Telescopes | Rover on Mars | 1,824 / 57 | 6 / 4 / 3 | 100% / 12% / 2% | ✓ / ✗ / ✗ | ✓ / ✓ / ✓ | 1 / 4 / 5 |
| Probes & Telescopes | Jupiter's Great Red Spot | 1,728 / 26 | 5 / 3 / 2 | 55% / 22% / 5% | ✗ / ✗ / ✗ | ✓ / ✓ / ✓ | 4 / 4 / 5 |
| Probes & Telescopes | Cosmic Cliffs | 1,840 / 67 | 6 / 4 / 3 | 50% / 8% / 5% | ✗ / ✗ / ✗ | ✓ / ✓ / ✗ | 4 / 5 / 5 |
| Probes & Telescopes | Hubble Deep Field | 1,936 / 70 | 7 / 5 / 4 | 15% / 0% / 0% | ✗ / ✗ / ✗ | ✓ / ✓ / ✗ | 4 / 5 / 5 |
| Inventions & Firsts | The Light Bulb | 1,656 / 21 | 6 / 4 / 3 | 100% / 98% / 40% | ✓ / ✓ / ✗ | ✓ / ✓ / ✓ | 1 / 1 / 4 |
| Inventions & Firsts | Da Vinci's Flying Machine | 1,728 / 22 | 6 / 4 / 3 | 62% / 20% / 5% | ✓ / ✓ / ✗ | ✓ / ✓ / ✓ | 2 / 3 / 5 |
| Inventions & Firsts | The Telephone | 1,748 / 26 | 6 / 4 / 3 | 65% / 30% / 18% | ✓ / ✗ / ✗ | ✓ / ✓ / ✓ | 2 / 4 / 4 |
| Inventions & Firsts | Penny-Farthing | 1,748 / 29 | 6 / 4 / 3 | 65% / 45% / 22% | ✗ / ✗ / ✗ | ✓ / ✓ / ✓ | 4 / 4 / 4 |
| Inventions & Firsts | Jacquard Loom | 1,840 / 70 | 6 / 4 / 3 | 100% / 28% / 0% | ✗ / ✗ / ✗ | ✓ / ✓ / ✓ | 4 / 4 / 5 |
| Inventions & Firsts | Difference Engine | 1,848 / 72 | 6 / 4 / 3 | 78% / 8% / 2% | ✓ / ✗ / ✗ | ✓ / ✓ / ✓ | 1 / 5 / 5 |
| Inventions & Firsts | Stephenson's Rocket | 1,728 / 52 | 7 / 5 / 4 | 45% / 2% / 2% | ✓ / ✗ / ✗ | ✓ / ✓ / ✓ | 2 / 5 / 5 |
| Inventions & Firsts | The First Photograph | 1,848 / 57 | 7 / 5 / 4 | 28% / 2% / 0% | ✓ / ✗ / ✗ | ✓ / ✓ / ✓ | 3 / 5 / 5 |
| Halloween | Black Cat on the Fence | 1,840 / 26 | 6 / 4 / 3 | 100% / 42% / 15% | ✓ / ✓ / ✗ | ✓ / ✓ / ✓ | 1 / 2 / 4 |
| Halloween | Trick-or-Treat Street | 1,920 / 78 | 6 / 4 / 3 | 90% / 45% / 5% | ✓ / ✓ / ✗ | ✓ / ✓ / ✓ | 1 / 2 / 5 |
| Halloween | Jack-o'-Lantern | 1,760 / 27 | 6 / 4 / 3 | 95% / 42% / 8% | ✓ / ✓ / ✗ | ✓ / ✓ / ✗ | 1 / 2 / 5 |
| Halloween | Friendly Ghosts | 1,728 / 25 | 6 / 4 / 3 | 70% / 57% / 38% | ✓ / ✗ / ✗ | ✓ / ✓ / ✓ | 2 / 4 / 4 |
| Halloween | Scarecrow | 1,848 / 29 | 6 / 4 / 3 | 90% / 45% / 20% | ✗ / ✗ / ✗ | ✓ / ✓ / ✓ | 4 / 4 / 4 |
| Halloween | Haunted House | 1,840 / 57 | 6 / 4 / 3 | 72% / 10% / 0% | ✓ / ✗ / ✗ | ✓ / ✓ / ✓ | 2 / 5 / 5 |
| Halloween | Pumpkin Patch | 1,824 / 62 | 7 / 5 / 4 | 35% / 2% / 0% | ✓ / ✗ / ✗ | ✓ / ✓ / ✓ | 2 / 5 / 5 |
| Halloween | Spider's Web | 1,936 / 73 | 6 / 4 / 3 | 35% / 10% / 2% | ✗ / ✗ / ✗ | ✗ / ✓ / ✓ | 4 / 5 / 5 |
| Winter | Mittens & Cocoa | 1,840 / 28 | 6 / 4 / 3 | 100% / 100% / 72% | ✓ / ✓ / ✓ | ✓ / ✓ / ✓ | 1 / 1 / 2 |
| Winter | Sledding Hill | 1,728 / 27 | 6 / 4 / 3 | 100% / 78% / 52% | ✓ / ✓ / ✗ | ✓ / ✓ / ✓ | 1 / 1 / 4 |
| Winter | Snowman | 1,840 / 30 | 6 / 4 / 3 | 95% / 68% / 25% | ✓ / ✓ / ✓ | ✓ / ✓ / ✓ | 1 / 2 / 3 |
| Winter | Cardinal in the Snow | 1,848 / 30 | 6 / 4 / 3 | 82% / 35% / 18% | ✗ / ✗ / ✗ | ✓ / ✓ / ✓ | 4 / 4 / 4 |
| Winter | Bentley's Snowflake | 1,936 / 56 | 6 / 4 / 3 | 80% / 25% / 5% | ✓ / ✗ / ✗ | ✓ / ✓ / ✓ | 1 / 4 / 5 |
| Winter | The Skating Pond | 1,728 / 60 | 6 / 4 / 3 | 85% / 0% / 0% | ✓ / ✗ / ✗ | ✓ / ✓ / ✓ | 1 / 5 / 5 |
| Winter | Snow Globe | 1,840 / 61 | 7 / 5 / 4 | 57% / 8% / 0% | ✗ / ✗ / ✗ | ✓ / ✓ / ✓ | 4 / 5 / 5 |
| Winter | Frosted Window | 1,840 / 65 | 7 / 5 / 4 | 25% / 2% / 0% | ✗ / ✗ / ✗ | ✓ / ✓ / ✓ | 4 / 5 / 5 |

**The seven new packs** (added 3 Oct) on Classic: 4 Relaxed, 13 Steady, 3 Tricky, 17 Hard and 19 Fiendish (on Expert: 1 / 3 / 3 / 13 / 36). Of their 29 searched levels, 26 met the Challenge or Master bar; the other three use the closest deal (Sierpiński Triangle, Jacquard Loom and Trick-or-Treat Street — their ratings in the table are what the app shows). Two Geometry levels, the Mandelbrot Set and the Impossible Triangle, were rebuilt with other seeds after the first build left the pack without a Relaxed or Steady mosaic on Classic (both came out Tricky or Hard); the rebuilt ones are Steady. Every picture is an original composition: natural-history plates after public-domain works (Audubon, Redouté, Merian, Gould, Haeckel, Seba), space views after public NASA/ESA images, Currier & Ives and Wilson Bentley for Winter; no logos, no protected characters, an invented tartan.

**The Literature packs** (added 2 Oct) on Classic: 12 Relaxed, 10 Steady, 2 Tricky, 17 Hard and 15 Fiendish (on Expert: 1 / 5 / 7 / 15 / 28). Of their 28 searched levels, 23 met the Challenge or Master bar; the rest use the closest deal (The Nautilus, The Snow Queen and The Monkey King came out Steady on Classic, The Underground Sea Tricky and The White Whale Hard). One gentle level, The Footprint, was rebuilt with another seed after the first test run showed the look-ahead player losing it on every difficulty (careless play still won it often); the rebuilt one is won by the look-ahead player on all three. Every scene is from a public-domain work, drawn as an original composition rather than from a film version.

Honest notes. **The collection's difficulty spread on Classic:** 10 Relaxed, 9 Steady, 3 Tricky, 23 Hard
and 11 Fiendish (on Expert: 1 / 8 / 5 / 15 / 27). Each pack mixes three builders — the Garden builder,
the Challenge search and the Master search, the last two with every accepted deal checked against their
bars — and is then sorted by the measured ratings. The builder is only a means: 12 of the 15 Challenge-
search levels and 10 of the 14 Master-search levels met those bars; the others use the closest deal found
(for example Bamboo Grove came out Hard, Terracotta Army and Berlin Wall Hard on Classic and Fiendish on
Expert). Their ratings in the table are what the app shows. Some Garden-builder pictures came out Hard
even on Gentle (Grand Canyon, Victoria Falls, Golden Gate, Total Eclipse, The Water Lily Pond): one-step
play fails there, but careless play still wins often. Six pictures were redrawn after a first look
because they didn't read at game size (Everest, Stonehenge, Terracotta Army, Galápagos, Printing Press,
Coral Reef), and the Master pack is unchanged from the last round (the Challenge and Master packs keep
their stricter bars, still checked above).

## B. What still needs your iPad (not tested by me)

1. **Compiling in Swift Playground.** Please send compile errors verbatim. New this round:
   `FlightRecorder.swift`, and changes in `AntScheduler.swift`, `GameController.swift`, `SoundBoard.swift`,
   `SelfTest.swift`, `AppModel.swift`, `HomeView.swift`, `BoardPainter.swift`, `ControlPanel.swift`,
   `MosaicRaster.swift` and `Scoring.swift`; then the seven new packs: `Level.swift` (pack arrays, the
   Seasons theme, unlock rules, `isInSeason`), `HomeView.swift` (pack blurbs, the *In season* badge),
   `Overlays.swift`, `SelfTest.swift`, and two new generated files, `LevelDataDiscovery.swift` and
   `LevelDataSeasons.swift` (about 790 KB of level data in all, so the first build takes longer).
2. **If the app stops again** (on any mosaic): reopen it — Home should show *Last time, the game didn't
   close normally*. Tap **Copy report** and paste it to me (*Show* lets you read it first). If Swift
   Playground showed a red error line when it stopped, a screenshot of that helps too.
3. **The in-app self-test** (Home → ⚙ → Run engine self-test). It now starts with two **Ant stress** lines
   (Alhambra Tiles, Expert, Curious and Random per ant) — please screenshot those; if the app stops during
   the self-test, the report on Home will say which step it was on. It covers all 193 mosaics — the golden
   replay, path and timing checks on every one, the slower real-time and random-play checks on the 25
   earlier ones — so it takes a few minutes. It also checks the score formula and high-score tables, the
   *No colour twice* rule, the catalogue and the collection's harder steps, **all five pattern layouts** (their colour counts must match the reference
   model — if that line fails, please send it, it means the Swift and Python generators disagree), and a
   **timing check of route planning**: it reports how many milliseconds the
   slowest send on Night Market and Sunflower takes to plan (pass under 120 ms; smooth below ~50 ms).
   Please screenshot that line in particular.
4. **Smoothness when sending a team while many ants are out** — the pause you reported. Try Night
   Market or Sunflower on Classic at 1× and 4×, sending teams while the board is busy.
5. **Home and the collection:** *Your collection* (found / explored / stars / mastered) and the seven theme
   chips (do they scroll to the right theme?); the pack **shelves** (scroll sideways; **?** cards and
   locked cards); the **Status** chips together with Difficulty and Show; *Next up* moving through the
   packs. Finish a mosaic in a new pack: the finish card should say *Found: …* and a **?** on Home should
   become a picture. Finish one on Expert with a harder option: the flame should appear. Try the
   **harder step** button on the finish card. With 193 thumbnails, is Home still smooth to scroll? The
   **Literature** chip should jump to its seven shelves. **New:** the **Seasons** chip and theme
   (Halloween should show *In season* today; Winter shows no badge until December), and the five new packs
   under Nature, Art, History and Sky & Science, each with its own *Opens after …* line.
   **New pattern:** tap it several times — the subtitle names the layout (Rosette, Starburst, Fish
   scales, Kaleidoscope, Ribbons); each should look different, and each should open and be playable.
6. **Start card:** harder options (toggle a few; the score multiplier updates), the high-score list,
   and the pinned Start button.
7. **Finish card:** the score and breakdown, the name box, the table afterwards; **Home → High scores**.
   *Fixed after your report that typing the name didn't work:* the text field only responded to taps
   on its single line of text, so taps on the rest of the 44-pt box did nothing — now the whole box is
   tappable and lights up while you type; the game screen no longer shrinks and redraws the mosaic
   when the keyboard appears (in portrait it could even switch layout under the card); the name box
   scrolls into view above the keyboard; and the game stops its 10-per-second updates once the mosaic
   is finished. The two-player result card got the same fixes. If typing still fails, please tell me
   whether the on-screen keyboard appears and whether you use a hardware keyboard.
8. **Two players:** the winner's name box on the result card; *Any colour* now the default (settings from
   the previous build are switched once).
9. **The exit X** in the top-left corner of a game, and **one tap on a waiting team** returning it.
10. **Random per team** as the default ant path (settings still on Natural are switched once).
11. Earlier items still open: sound on the device, frame rate with many ants, photo import, layouts on
    other window sizes and on iPhone.

## C. Mockups vs software

Images in `Mockups/` are **mockups**. The board, ants, slots, tunnels, ratings and scores in them come
from the real reference engine and measurements, but the surrounding UI was drawn separately to match
the SwiftUI layout, and each image carries a red "MOCKUP" label (names in the high-score mockups and the
player's collection progress on the Home mockups are examples). `Renders/` images and the `.m4a` previews are made with the same reference model; they are
not recordings or screenshots of the app. No screenshot of the running app exists yet.
