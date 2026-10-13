# Tessera Colony — product & development plan

*Updated after your feedback: slots, queues, levels, ground colour, speed, removing Hold, sound sets, a Challenge pack, visible difficulty selection, ant-path styles, a sound fix and two players.*

An original iPad-first puzzle game in the "colour ant teams clear a mosaic" genre, built as a
Swift Playground app playground (`TesseraColony.swiftpm`) with a path to an iPhone release.

---

## 1. Research: the reference game and its genre

### What I could and could not verify

I could not find a store listing titled exactly **"Ant Mosaic: Color Puzzle"**. Searches for that
name return the closely matching games **Ants Flow: Pixel Puzzle Game / Pixel Color Puzzle!**
(Estoty) and **Colony Flow!** (ABI Games), plus Colony Flow walkthrough sites that describe the
rules in detail. The findings below come from those games; if "Ant Mosaic" is a different app,
the mechanics are very likely the same family, but I have not seen it directly.

### Mechanics (verified from sources)

| Earlier working understanding | What the sources say | Verdict |
|---|---|---|
| Players choose coloured ant teams from queues | "Tap colored ant boxes to release swarms of tiny ants onto the board" (Ants Flow, App Store); boxes carry a number of ants (Colony Flow guide) | Verified |
| Ants collect reachable matching tiles | "The ants spawn from the hole at the bottom and need a direct open path to their target color. They cannot dig through a color that does not match" (colony-flow.com, level 250) | Verified, with the detail that ants start from a hole at the bottom |
| Teams that cannot finish occupy limited waiting spaces | Colony Flow has **five** waiting slots; "tapping a box slides it into a slot… Clear a box and the slot frees up" (App Store). "Filling all five slots with blocked colors causes an instant loss" (level 250 guide) | Partly verified: in Colony Flow *every* sent box sits in a slot until its count reaches zero, not only blocked ones |
| — | Extra mechanics: linked boxes that move as one unit and take several slots; hidden "?" boxes whose colour is revealed later (level 824 & 987 guides); "2x speed toggle", "bigger grids and limited slots" (Ants Flow, Google Play) | New information |

### What players enjoy (direct player evidence)

- **Satisfying, ASMR-like motion.** "It's a 5 star game because the ASMR effect is off the charts." (Stephen Johnson, Ants Flow, Google Play) · "fun, relaxing, mesmerizing" (MyGirlz#1Mom, Colony Flow, App Store)
- **Thinking ahead.** "Makes you think about your next move." (Jeanne Rose, Colony Flow via AppBrain) · praise for "clever level design" (Michael Smit, Colony Flow, Google Play)
- **Fair, winnable levels without paying.** "all levels winnable without having to pay" (Kokorozo, Ants Flow, App Store); "NO micro transactions" (AGuyCalledCat)
- **The hidden picture as reward.** Both store listings sell "every solved level reveals hidden art".

### Common complaints (direct player evidence)

- **Difficulty walls that push boosters or payment.** "Some levels you can't pass unless you buy" (Atamos91); level 694 "truly unplayable without using any items" (eyrecura); Champion levels needing "15 times" retries (Ants Flow, Google Play); Super Hard levels "basically impossible" without luck or money (Sophia Mc).
- **Ads.** "45-second level, 1-minute ad" (Isaac Schurter); ads after every level (Kyle Greenlees); ads that open the browser mid-level (cornbread_21, hlc111).
- **Similar colours.** Shades "hard to distinguish, especially with night shift" (Dreamers4444, Colony Flow); "3 different purple colors shade so close…" (Ant Blocks, Google Play).
- **No explanation of new mechanics** (AGuyCalledCat); **no replay** of finished levels (Kokorozo); **lost progress** when the app is backgrounded (Colony Flow 3-star review); **repeated puzzles** (Des2414, Atamos91); the game "will bypass certain colors" (Chris Garcia) — i.e. it is not always clear which tiles are reachable.

### Genre context

Pixel Flow (Loom Games), the hit this genre descends from, pairs a colour-matching board with strict
slot limits and a deterministic, skill-based feel; skilled players can "chain actions… to recover
seemingly lost situations" (Deconstructor of Fun, Feb 2026). Its commercial model leans on
difficulty and ads — exactly what the complaints above are about.

### Ant targeting and path styles (follow-up research)

*Which tile does an ant take?* It matters to the puzzle only when a team can reach more tiles of its
colour than its number: the rule then decides what is uncovered for the next colours. Options:
nearest to the hill by walking distance (current: predictable, and scouting shows it exactly);
farthest first (long channels, slow, hard to predict); edge-first erosion (organic look, harder to
predict); line of sight like Pixel Flow, whose shooters fire "when aligned with matching colored
pixels" ([pixelflowgame.com](https://pixelflowgame.com/)); a player-placed crumb that the next team
works outward from (adds strategy); random (rejected: breaks planning, hints and undo). Any
deterministic rule works with the level planner, but changing it regenerates every level.

*How does it walk there?* Purely visual, so it can be a setting. Direct grid paths (current); any-angle
"natural" paths, since Theta* finds shorter, more realistic paths than grid A*
([Nash et al.](https://arxiv.org/abs/1401.3843)); individual straightness ("37% straight walkers,
26% semi-straight, 30% semi-curvy, 7% curvy" in a tracking study,
[Scientific Reports 2019](https://www.nature.com/articles/s41598-019-49655-3)); a scout that lays a
trail the others follow and tighten, as trail pheromones aid route learning in *Lasius niger*
([JEB](https://journals.biologists.com/jeb/article/216/2/188/11672/Ant-foraging-on-complex-trails-route-learning-and));
wall-hugging along the remaining mosaic, as most *Lasius niger* follow a box's edge rather than the
direct path ([figure](https://www.researchgate.net/figure/Illustration-of-the-wall-following-tendency-in-ants-A-colony-of-the-ant-Lasius-niger-is_fig1_7868432));
and army-ant traffic lanes, laden ants in the middle and unladen ants on the outer lanes giving way
([Couzin & Franks via AskNature](https://asknature.org/strategy/groups-move-efficiently/)).
Built (your choice): tile choice stays nearest-first; an *Ant paths* setting offers Direct, Natural
(default), Curious, Wall-hugger, Scout trail, Random per team and Random per ant for newly launched
ants; carriers always come home in the middle lane.

### Harder levels and new features (follow-up research, 27 Sep 2026)

*Evidence — mechanics in the genre.* Colony Flow adds hidden "?" cubes (colour revealed when the box
enters a slot), locked cubes that need the cube on top cleared, rope-linked cubes that must be freed
in order, and "a second nest hole from level 18", plus "Super Hard" spike levels
([colonyflow.games](https://colonyflow.games/)). Pixel Flow adds frozen shooters ("Deplete other pigs
to shatter their ice!"), locks and keys, surprise pixels revealed when exposed, hard pixels that take
more hits, refilling pipes, "hungry doors" fed with one colour, and a conveyor with limited space on
top of five slots ([pixel-flow.app wiki](https://pixel-flow.app/wiki/features)). None of the three
games uses timers ("No timers, no lives, no pressure" — Colony Flow on Google Play).

*Evidence — players on fairness and features.* When recovery tools cost money, hard levels read as a
paywall ("Once you reach a certain level, the game will make it very impossible to advance without
spending" — Colony Flow, Google Play); Ants Flow is praised because "Every level so far has been
winnable without having to pay" (App Store). Requests: don't lose progress when the app is
backgrounded, an explanation when new elements appear, replaying levels, other modes ("No other home
screen where you can pick another mode"), cross-device sync, and less waiting (Ants Flow ships a
"2x speed toggle").

*Evidence — design research.* Difficulty can be predicted from level features such as the number of
"counterintuitive moves" (van Kreveld et al., [CIG 2015](https://ics-websites.science.uu.nl/docs/vakken/mscip/assignments/CIG2015-AutomatedPuzzleDifficultyEstimation.pdf));
in Sokoban, human-like solver models beat solution length as a predictor (Jarušek & Pelánek,
[2010](https://www.fi.muni.cz/adaptivelearning/documents/sokoban.pdf)); generators can reject puzzles
that a second solver finds shortcuts through (Smith, Butler & Popović, [FDG 2013](https://adamsmith.as/papers/fdg2013_shortcuts.pdf))
— the same idea as our Challenge search; AI players' *best* runs track human pass rates better than
their average runs (Roohi et al., [CHI PLAY 2021](https://arxiv.org/abs/2107.12061)); a generator
producing a "sawtooth-shaped difficulty curve" was confirmed with about 1,000 players (ELIMINATION,
[CoG 2019](https://arxiv.org/abs/1905.06379)). A single shared daily puzzle worked for Wordle because
"people have an appetite for things that transparently don't want anything from you"
([TechCrunch](https://techcrunch.com/2022/01/12/josh-wardle-interview-wordle/)). Swift Playground app
playgrounds list Local Network (Multipeer) but not Game Center or iCloud among their capabilities
([Apple](https://developer.apple.com/documentation/swift-playgrounds/project-capabilities)).

*My suggestions — harder but fair.* (1) Rate levels with a ladder of bots: careless, one-step, look-ahead,
full solver; target Gentle = one-step, Classic = look-ahead, Expert = solver; count "counterintuitive"
sends (deliberately parking a waiting team) in the shortest solution. (2) Pace a sawtooth: a spike every
~10 levels, an easy level after it; introduce each mechanic alone before combining it. (3) New mechanics
that fit our rules: **mystery teams** (colour shown only at the front; a legend shows how many of each
colour remain), **roped teams** (two teams sent together, taking two slots), **frozen team** (thaws after
N teams finish), **locked tunnel + key team**, **hard tiles** (count double against a team's number),
**rubble** (colourless tiles cleared when a neighbour is picked up), **fog** (hidden region revealed when
its edge is cleared; pairs with scouting), **second hill** opening mid-level, **hungry gate** (opens after N
tiles of its colour), **cracked slot** (unusable until a team finishes). No timers in the core mode.

*My suggestions — features, ranked for a no-ads iPad game.* Daily Colony (one date-seeded, solver-checked
level per day, shareable result text, a streak that never punishes), a clean-solve badge (no undo or
assists), Zen mode (never blocked) and Time Attack, saving finished mosaics to Photos, earned cosmetics
(ant skins, hill themes) and on-device achievements, a level editor with share codes checked by the
solver, export/import of saves through Files (no iCloud in app playgrounds), and later two-iPad play over
Multipeer. **Two players on one iPad is built in this version** (below). **Also built now** (your
request of 27 Sep): the clean-solve idea as optional *harder options* with a score multiplier, per-mosaic
high scores with names (solo and two-player winners), a Home difficulty filter, and 16 more mosaics —
the Garden pack and a Master pack rated with the bot ladder (careless, one-step, look-ahead).

### Harder boards: countdown veils and other options (research, 5 Oct 2026)

*Your idea:* hide part of the board behind a cover showing a number that counts down as tiles are removed
anywhere; at zero the cover lifts.

*Evidence — the genre already uses count-down locks and reveals.* Color Block Jam: "Iced blocks are frozen
in place. To free them, you'll need to remove a specified number of other blocks"; Turn Based Arrows have "a
number that shows how many blocks must be cleared before it unlocks"; "Hidden Blocks stay invisible until a
specific visible block on the board is cleared" ([Rollic help centre](https://rollic.helpshift.com/hc/en/24-color-block-jam/faq/1234-obstacles-in-color-block-jam/)).
Pixel Flow: Curtain "Pull up the curtains to reveal what's underneath!", Surprise Pixel "Expose them to reveal
its color!", Ice Blocks, Hard Pixels, Locks and Keys, Hungry Door ([wiki](https://pixel-flow.app/wiki/features)).
Colony Flow: hidden cubes "show a gray '?' instead of their color" (from level 8), locked cubes (level 12), a
second nest hole (level 18) ([wiki](https://colonyflow.games/wiki/features/)). The opposite kind of countdown,
a failure timer, is Candy Crush's Candy Bomb: at zero "it will explode the whole board and the player will
fail the level" ([fandom](https://candycrush.fandom.com/wiki/Candy_Bomb)).

*Evidence — pacing.* King: blockers arrive on a "complexity staircase"; "Any new blocker has to earn its place
by offering a distinct behaviour"; "a particularly challenging level to be followed by something lighter"
([PocketGamer.biz](https://www.pocketgamer.biz/crafting-candy-crushs-difficulty-blockers-level-design-ai-and-the-complexity-staircase/)).
Playrix: "no more than three or four elements per level"; "You should be able to beat every match-3 level in
your game without using boosters" ([Game World Observer](https://gameworldobserver.com/2019/09/27/playrix-levels-elements-match-3)).
Pixel Flow keeps hard levels evenly spread: 14, 16 and 15 per hundred over levels 1–300
([Gamigion](https://gamigion.substack.com/p/pixel-flow-1-300)). Bots and people only see the same puzzle when
there is "no hidden information, so that the AI and human have exactly the same information"
(Isaksen et al., [CIG 2017](https://gfx.cs.princeton.edu/pubs/Isaksen_2017_SSA/isaksen-cig17.pdf)).

*Measured — a prototype of your countdown veil* (`Tools/veil_proto.py`, results in
`Docs/data/veil_report.json`). Rule: a veiled tile can't be claimed until the number of removed tiles
reaches the threshold. It is a pure function of the board state, so undo, saves, golden hashes, hints and
the ant scheduler need nothing new. Three shipped pictures were rebuilt with the same seeds and the same
designer, then measured with the same bots. Plain builds reproduce the shipped levels exactly.

| Picture | Plain: rating G/C/E | Low-side veil: bottom-left quarter, lifts after 30 % removed | Centre veil: middle third, lifts after 50 % removed |
|---|---|---|---|
| Iceberg (Wild Wonders) | 1/1/2 | 1/1/4 | 1/4/4 |
| Jack-o'-Lantern (Halloween) | 1/2/5 | **1/1/4 (easier)** | 1/4/5 |
| Audubon's Flamingo (Natural History) | 1/2/3 | 4/4/5 | 1/2/4 |

Ratings run from 1 (Relaxed) to 5 (Fiendish). The look-ahead player won every veiled build on every
difficulty, so the veils stayed fair in the sense we test. Findings:

1. Veils usually make a level harder, often by two or three steps on Classic. Placement decides how much:
   one veil made a level easier, and one overshot (the low-side Flamingo rates 4 even on Gentle). The
   generator must therefore search veil placement and threshold against a target rating, as it already
   searches deals for Challenge and Master.
2. The bots see under the veil. With the colours hidden, people will find these levels harder than measured,
   so a hidden-colour version needs a fog-blind bot before its ratings mean anything.
3. Hiding colours over the whole board ("?" on every tile until reachable) would hide over 90 % of the picture
   at the start: in the shipped levels only a median 9.2 % of tiles are exposed. Mystery
   tiles should come in patches.

*My suggestions — ranked, one new mechanic at a time, at most three or four per level, no failure timers.*
1. **Countdown veil**, first with the colours faintly visible under frosted glass (exactly what was
   measured), later a dark version that shows only a colour legend ("12 red, 30 blue…"). What it counts can
   vary later: any tiles, tiles of one colour, or teams finished.
2. **Mystery patches**: tiles show "?" until reachable. Information only, no rule change, so it could also be
   a harder option on any existing level.
3. **Numbered ice** on single tiles or small clusters: the veil rule at small scale.
4. **Hungry gate**: a region that opens after N tiles of one colour.
5. **Locks and keys**: claiming a key tile opens a locked region.
6. Later: hard tiles, rubble, frozen teams. Avoid failure countdowns, spreading hazards and moving parts.

Rollout: a first pack of eight veiled levels on the existing picture style, rated with the bot ladder,
alternating a veiled spike with a lighter level; then veils appear occasionally in later packs.

### My conclusions (design ideas, not player evidence)

1. Keep the core loop (colour teams → reachable tiles → limited waiting space) and the hole at the bottom.
2. Remove the frustration levers: no ads, lives or paid boosters; **free unlimited undo**; hints that
   say how far to undo; an explicit **scout** preview so reachability is never a mystery.
3. Make recovery a player choice rather than a loss screen: **add a slot**, or **return a waiting
   team** to its tunnel (added after your mid-build feedback).
4. Every sent team occupies a slot until its ants have picked up its tiles, so you can't fire off every
   team at once; but several colours work side by side, one per slot (your concurrency and
   slot-timing feedback).
5. Make colours unambiguous even with shading: six families, four tones each, and every
   cross-family pair at least **ΔE2000 18.5** apart (measured); shading never changes a tile's family.
6. Autosave after every move; replay any mosaic; a gallery for finished pictures.

---

## 2. Design: Tessera Colony

**Theme.** A colony of ants dismantles a Byzantine-style tessera mosaic and re-lays it, tile by tile,
in the Nest Gallery underground. Warm loam backgrounds, sandstone panels, brass accents, a serif
title face (New York) and rounded numerals.

**Board.** Thousands of small glazed tesserae (bevel, grout, per-tile glaze jitter) — no symbols on
any tile. A ground margin surrounds the art and the ant hill sits in the bottom margin.

**Rules.**
- Tunnels hold queues of teams (a colour + a number). Tap the front team to send it; each tap sends
  the next team in that tunnel. The next three teams are shown under each tunnel, and tapping the
  tunnel name shows its whole queue.
- Its ants claim matching tiles reachable over open ground from the hill, nearest first, up to its number.
  A team can tunnel through its own colour (claimed tiles become open ground at once).
- **Slots.** Every team you send occupies a slot. A working team's number counts down as its ants pick
  up tiles; when it reaches zero the slot opens again. You can only send a team when a slot
  is open — so you can't fire off every team at once, but several colours do work at the same time,
  one per slot. (This follows your feedback and matches Colony Flow, where every sent box sits in a slot.)
  There is no colour limit: every slot can hold the same colour, sent from any tunnels.
- A team that can't reach all its tiles keeps its slot and **waits**; it resumes by itself when its
  colour is uncovered. Sending is the only way to make a team wait, and the slots help says so.
  (An earlier build had a **Hold** button that parked a team in a slot without sending it. It was
  removed: sending does the same job or better, because a sent team also collects whatever it can
  reach. Saves made with Hold still load.)
- If every slot holds a waiting team, the colony is **blocked**. Recovery: undo (unlimited unless you
  chose *3 undos*), add a slot, or **one tap on a waiting team** returns it to the front of its tunnel
  and opens its slot (a small ↩ badge marks it; there is no confirmation pop-up any more, and Undo puts
  it back). Adding a slot and returning a team count as "assists".
- **Leaving a game:** a round **X** in the top-left corner of the game screen goes straight back to
  Home (the game is saved; *Resume* continues it). The … menu still has *Back to the nest*.

**Ants.** Cartoon ants with shaded, glossy, outlined bodies, big eyes and antennae, painted the exact
colour of the tile each one is fetching (photo colours included). Legs use an alternating-tripod gait
tied to distance walked, so feet plant and lift and the steps slow down when the ants do. Ants emerge
from the hole, follow real paths (three lanes, rounded corners), stop, lift the tile into their jaws,
turn around and carry it home. The tile stays on the board until its ant arrives.

**Speed.** 1× = four tiles (about two ant lengths) per second — far slower than my first draft
(22 tiles/s). A log-scale slider runs from 0.1× (crawl) to **16×** (fast-forward). It changes the game
clock, so ants already walking change pace smoothly; it is remembered between sessions.

**Sound.** Every effect is synthesized on the device (no audio files), in two sets plus the colony:
- *Action set* — dry wood and clay for the moves you make: send (a knock and a soft whoosh), scout
  (two light taps), undo (a reverse swish), add a slot (two rising clay knocks), return a team (a
  sliding note), refused tap (a muted double thud), a team that must wait (a low two-note "hmm"),
  blocked (a minor marimba roll), hint (a questioning two-note marimba).
- *Goal set* — bells and glass with a shimmer: a team finishing its tiles, a whole colour lifted,
  each quarter of the mosaic carried home (three rising runs), the finished mosaic (fanfare), a new
  best time on that difficulty, and a newly unlocked mosaic (a glass sparkle).
- *Colony* — a ceramic clink when an ant lifts a tile, pitched per colour on a pentatonic scale and
  panned by where the tile is, and a wooden tick when a tile drops into the nest; scheduled against
  the game clock so they land on the frame the tile lifts, capped at about 20 a second.
Settings: master on/off and volume; separate switches for Action sounds, Goal sounds and Colony
clinks, each set with a *Play a sample* button; a quick switch in the in-game menu. The audio mixes
with the player's music and follows the iPad's volume and silent mode.

**Ant paths.** Which tiles a team takes never changes (nearest first); how each ant walks there is a
setting for newly launched ants: Direct, Natural (equally short, follows the straight line),
Curious (wanders; about a third stop to sniff), Wall-hugger (walks along the mosaic's current edge),
Scout trail (a team's first ant explores and leaves a fading dotted trail in its colour; followers
use it and straighten it), **Random per team** (the default since 27 Sep — each team picks one of
Direct, Natural, Curious, Wall-hugger or Scout trail when it is sent), Random per ant. Every route only crosses ground or tiles
already lifted, and the ant's departure waits until each tile on its route is up.
*Planning is bounded* (fix for the pause you saw when sending a team while many ants were out): each
ant's route is searched only inside a 3-cell corridor around its shortest path, pulled towards its
tile, with buffers reused between ants; a send plans at most 32 styled routes (spread through the
send) within 16,000 search steps, and the other ants walk their shortest path. Before, one send on
Night Market could take about 1.5 million search steps (433 ants, every one searched across the whole
open board, each allocating three board-sized arrays); now no send exceeds 16,000, the styles still
look different, and levels are no longer. The nest miniature beside the board is also redrawn at most
twice a second instead of ten times.

**Ground colour.** The ground behind the mosaic (margin and cleared tiles) can be any colour: eight
presets or a colour picker, from the in-game menu or Settings.

**Levels and unlocking.** 193 built-in mosaics in twenty-five packs, plus unlimited pattern and photo mosaics.
- *Mosaics* (main): *First Dig* — 1,008-tile ladybird with coached onboarding (open); *Koi Pond*
  (2,464, after First Dig); *Peacock Fan* (2,704, after Koi Pond); *Night Market* (3,584, after
  Peacock Fan); *Sunflower & Monarch* — the **6,048-tile** showcase (open from the start).
- *Garden* (8, after First Dig): Hot-Air Balloon, Lighthouse, Toadstools, Tulip Bed, Evening Sail,
  Honeycomb (bees on the comb), Owl and Desert Bloom — eight different pictures —
  drawn in `Tools/art_scenes.py`, levels built like the main ones.
- *Challenge* (4, after First Dig) — see below.
- *Master* (8, after **any** Challenge mosaic) — see below.
- **The collection** (56 more, seven packs of eight, each ordered from its gentlest to its hardest) —
  see *Collection* below: *Wild Wonders* (after First Dig), *Gallery* (after First Dig), *World Art*
  (after any Gallery mosaic), *Ancient World* (after First Dig), *Voyages* (after any Ancient World
  mosaic), *Modern Moments* (after any Voyages mosaic) and *Sky & Science* (after any Wild Wonders
  mosaic).
- **Literature** (56 more, seven packs of eight, added 2 Oct) — see *Literature* below: *Epics & Legends*
  and *Fairy Tales & Fables* (after First Dig), *Children's Classics* (after any Fairy Tales mosaic),
  *Adventure Classics* (after any Children's Classics mosaic), *Gothic & Mystery* (after any Adventure
  mosaic), *Shakespeare* (after any Epics & Legends mosaic) and *Great Novels* (after any Shakespeare
  mosaic).
- **New packs and Seasons** (56 more, seven packs of eight, added 3 Oct) — see *New packs* below:
  *Natural History* (after any Garden mosaic), *World Craft* (after any World Art mosaic), *Geometry &
  Illusions* (after any Challenge mosaic), *Probes & Telescopes* (after any Sky & Science mosaic),
  *Inventions & Firsts* (after any Modern Moments mosaic), and the seasonal *Halloween* and *Winter*
  (after First Dig; playable all year, with an *In season* badge from 20 Sep to 7 Nov and from 1 Dec to
  28 Feb).
- **Make a new level**: *New pattern* generates a fresh pattern mosaic (~2,400 tiles) on the iPad in one
  of five different layouts — rosette, starburst, fish scales, six-way kaleidoscope of random shapes, or
  striped ribbons over polka dots (so repeated taps give different designs, not recoloured ones) —
  planned and verified solvable before it opens — as many times as you like; *From your photo* turns a
  photo into a level. A "Next up" banner on the home screen always shows where to go, locked cards say
  exactly what unlocks them, and Settings has *Unlock all mosaics*.

**Difficulty.** Slots = (most teams the designed solution ever keeps waiting) + 1 on Expert, + 2 on
Classic, + 4 on Gentle (which also tells you whether each front team can finish now). Tapping *Play*
opens a start card with a large Gentle / Classic / Expert choice; each option shows this mosaic's slot
count, a 1–5 rating (Relaxed, Steady, Tricky, Hard, Fiendish), the share of careless games won and
your best time on it. Ratings are measured by computer play: careless random tapping (40 games per
difficulty) and a one-step player that always sends the team that can finish now and claims most.
Built-in levels ship their measurements; pattern and photo levels are measured on the iPad.

**Home.** At the top: two big buttons — **Two players** (opens match setup) and **High scores** — then
*Next up* (the first found, unfinished mosaic, walking the packs in order), **Your collection** (found /
explored / stars / mastered, with one chip per theme that scrolls to it), and a filter bar:
**Difficulty** (Gentle / Classic / Expert: the difficulty new games start on and the one the cards'
rating dots describe), **Show** chips (All · Easy = Relaxed/Steady · Medium = Tricky · Hard · Fiendish)
and **Status** chips (All · To explore · Explored · Go harder · Mastered). Then the six themes, each
with its packs as sideways shelves of compact cards (picture, title, rating dots, stars; **?** for
mosaics not found yet, a lock for packs not open yet); with a filter on, only found mosaics that match
are shown. Then your own mosaics, *Make a new level* and the Nest Gallery (finished mosaics only).

**Harder options (any mosaic, chosen on the start card).** Each raises the score multiplier:
*Hidden queue* (+20%: only the front team of each tunnel shows), *No scouting* (+10%: no
press-and-hold preview, no Gentle "can finish" badges), *No hints* (+10%), *3 undos* (+20%),
*No assists* (+15%: no adding slots or returning waiting teams) and *No colour twice* (+25%: not the
same colour as the last team sent while another colour could go). None of them can make a mosaic
impossible — the designed solution needs no scouting, hints, undo or assists and never looks past the
front of a tunnel, and a search found a line that obeys *No colour twice* on every built-in mosaic
on Expert. The panel shows the active options and the multiplier. With no undos left and no assists,
a blocked game can only be restarted (the blocked card says so).

**Scores and high scores.** A finished solo game scores *tiles × difficulty (Gentle ×0.5, Classic ×1,
Expert ×1.5) × harder options (up to ×2) − 5 per undo − 25 per hint − 25 per assist* (never below 0).
Each mosaic keeps a **top 5** (ties go to the faster time). When a score makes the table, the finish
card asks for a name (pre-filled with the last one used) and shows the table with the new entry.
Two-player matches have their own table per mosaic: the **winner** types a name on the result card,
saved with the options played and the loser's score. Home → *High scores* lists every table (Solo /
Two players) and can clear them; the start card shows the mosaic's top scores.

**Two players (one iPad).** Home → *Two players* → choose options (all combinable) and a mosaic:
- *Board*: **Race** — split screen, each player clears their own copy; the first to finish gets a bonus
  of 15% of the tiles and ends the match. **Shared board** — one mosaic with two ant hills (left and
  right); both players get the same tunnels and compete for the same tiles; a team whose colour runs out
  retires with what it got; ants carry a ring in their player's colour.
- *Launching*: **Front team only**, or **Reach 3** — any of the first three teams in a tunnel, each place
  jumped costs 3 points. Each tunnel shows seven teams deep.
- *Colour rule*: **Any colour** (the default — launch the same colour from every tunnel if you like), or
  the optional **No colour twice in a row** (lifted if nothing else can be launched).
- *Slot scoring*: **Slot upkeep** — every busy slot beyond the first costs 0.25 points per game second —
  or **Flat** (no upkeep). Always: adding a slot −25, returning a waiting team −10.
- *Slots each*: Gentle / Classic / Expert counts for that mosaic.
Score = tiles your ants carry home (+ race bonus) − penalties. Landscape puts the players side by side;
portrait puts them face to face with the far half turned round. No undo or hints in a match. One tap on
a waiting team returns it (−10).

**Challenge pack.** Four 1,760–1,845-tile mosaics built from interlocking layers — Nesting Rings,
Basket Weave, Labyrinth and Rose Window — with 48–60 smaller teams. After the designer invents a
solvable sequence, a local search re-deals the teams across the tunnels (keeping each tunnel's order,
so the designed play still wins on Expert) to defeat careless and one-step play. Result: the one-step
player wins every challenge on Gentle but none on Classic or Expert; careless play wins 5–35% on
Classic and 0–15% on Expert; a look-ahead player (the hint's rollouts) still wins all of them on
Classic and Expert, so they are hard but fair. Unlocked by finishing First Dig.

**Master pack.** Eight 1,932-tile pictures, each a different subject — Tiger, Giraffe, Autumn Tree,
Castle, Viaduct, City at Dusk, Chameleon and Octopus (drawn in `Tools/art_scenes.py`) — with 66–81
teams, most of them small. They are deliberately busy so that each colour sits in many separate places
(stripes, coat patches, loose leaves, bricks between mortar, window panels between floor slabs, rows of
suckers): that is what makes a team wait. The tunnel orders come from the same re-dealing search, scored
more harshly (one-step play should fail even on Gentle; careless play is counted on Gentle too). On four
pictures the plain search missed: on Viaduct it kept going until even a thinking player lost, and on
Tiger, Giraffe and City at Dusk its best deal still let careless play win too often. For those, every
deal the search accepted is kept and checked, hardest first, against the Master bar with the same
measurements as the tests, and the hardest deal that passes is used (`build_master_to_bar`). Result:
one-step play fails on Classic and Expert on all eight and on Gentle on six; careless play wins at most
20% on Classic and 5% on Expert; the look-ahead player wins all three difficulties on seven and two of
three on Viaduct; the designed line always wins (hints know it). Unlocked by finishing any Challenge
mosaic. The first City at Dusk (plain towers with scattered windows) could not be made hard enough by
any deal — careless play still won more than half its games on Classic — so its towers were redrawn
with grid faces.

**The collection (added 27 Sep).** 56 more mosaics in seven themed packs of eight, chosen from lists of
the most famous artworks, the great explorations and the natural wonders (sources at the end): *Wild Wonders* (Northern Lights, Grand Canyon, Victoria Falls, an Antarctic iceberg, a
volcano, a rainforest, a coral reef, a panda's bamboo grove); *Gallery* (Monet's *Impression, Sunrise*
and *Water Lily Pond*, Vermeer's *Girl with a Pearl Earring*, the *Mona Lisa*, Munch's *Scream*, Van
Gogh's *Starry Night*, Seurat's *Grande Jatte*, Klimt's *Kiss*); *World Art* (Hokusai's *Great Wave*,
Hiroshige's *Sudden Shower*, a Ming vase, Kandinsky's *Several Circles*, the Aztec Sun Stone, the starry
vault of Ravenna, Alhambra tiles, a Mondrian composition); *Ancient World* (Lascaux, the Great Pyramid,
Stonehenge, Tutankhamun's mask, the first Olympics, the Great Wall, the Terracotta Army, the
Colosseum); *Voyages* (Polynesian wayfinders, a Viking longship, the Silk Road, Zheng He's treasure
ship, Gutenberg's press, Galileo's moons, Darwin's Galápagos, the South Pole); *Modern Moments* (the
first flight, Liberty, the Eiffel Tower, the Golden Gate, Everest, Sputnik, the Moon landing, the
Berlin Wall); *Sky & Science* (an eclipse, Saturn, Halley's comet, Newton's prism, Franklin's kite, a
spiral galaxy, the double helix, the periodic table). Every artwork is public domain (made before 1930
by artists who died before 1956); history scenes are original compositions, not copies of photographs.
Each pack mixes three builders — three or four gentle levels (the Garden builder), two or three re-dealt
against the Challenge bar and two against the Master bar — and is then ordered by measured difficulty, so
a pack runs from Relaxed or Steady to Hard or Fiendish. Across the 56, Classic ratings came out 10
Relaxed, 9 Steady, 3 Tricky, 23 Hard and 11 Fiendish; the look-ahead player wins every one on Gentle or
Classic (51 on all three difficulties) and the designed line always wins. The Challenge and Master bars
were met by 22 of the 29 searched levels; the rest use the closest deal and are rated by what was
measured (details in VALIDATION).

**Literature (added 2 Oct).** 56 iconic scenes from books, plays and tales, all in the public domain
(published before 1931 by authors who died before 1956, or ancient and folk works), each drawn as an
original composition of the book's own scene — never from a film or animated version (no Disney, MGM or
Universal designs), with no lettering and nothing violent. *Epics & Legends*: the Sirens (Odyssey), the
Trojan Horse (Aeneid), the sword in the stone (Malory), Dante's celestial rose, the Monkey King (Journey
to the West), Ali Baba's cave, Beowulf's dragon on its hoard, moon-viewing from the Tale of Genji.
*Fairy Tales & Fables*: Red Riding Hood, Jack's beanstalk, the tortoise and the hare, Rapunzel, the Snow
Queen, Cinderella's midnight, the gingerbread house, the princess and the pea. *Children's Classics*:
the yellow brick road (Baum), messing about in boats (Grahame), the Railway Children, the Secret Garden,
the Mad Tea-Party, the Council Rock (Kipling), the Looking-Glass chessboard, Pinocchio inside the
Dogfish. *Shakespeare*: the balcony, Yorick, the three witches, the Tempest's shipwreck, the fairy wood,
Cleopatra's barge, the Globe, the three caskets. *Adventure Classics*: Crusoe's footprint, Don Quixote's
windmills, Huck Finn's raft, Gulliver in Lilliput, the white whale, Verne's underground sea, the treasure
map, the Nautilus. *Gothic & Mystery*: the Raven, the Headless Horseman, the Hound of the Baskervilles,
the bells of Notre-Dame, Castle Dracula, Frankenstein's Arctic pursuit, the Martian tripods, the Opera's
great chandelier. *Great Novels*: Gatsby's green light, Scrooge's Christmas morning, Wuthering Heights,
the comet of 1812 (War and Peace), Miss Havisham's room, the bishop's candlesticks (Les Misérables), the
Netherfield ball, "I want some more" (Oliver Twist). Built and ordered exactly like the collection packs:
on Classic the 56 came out 12 Relaxed, 10 Steady, 2 Tricky, 17 Hard and 15 Fiendish, every pack runs from
Relaxed to Hard or Fiendish, and the look-ahead player wins every one on Gentle or Classic.

**New packs and Seasons (added 3 Oct).** 56 more pictures in seven packs, each drawn as an original
tile composition, with no lettering, logos or protected designs. *Natural History* — after public-domain
plates: Audubon's flamingo, Redouté's rose, Merian's butterflies, Gould's hummingbirds, Haeckel's jellyfish
and radiolarians, Seba's shells, a collector's beetle drawer. *World Craft* — a Talavera plate, a Polish
paper cut, Ukrainian pysanky, Delft tiles, a hemp-leaf kimono, an original tartan, a patchwork quilt, a
Persian medallion carpet. *Geometry & Illusions* — the Mandelbrot set (computed), the impossible triangle,
the golden spiral, Sierpiński's triangle, the Hilbert curve, the café wall illusion, a Celtic knot, a
ten-pointed girih star. *Probes & Telescopes* — Earthrise, Pluto's heart, a blue Martian sunset, the
Pillars of Creation, a rover, Jupiter's Great Red Spot, Webb's Cosmic Cliffs, the Hubble Deep Field.
*Inventions & Firsts* — the light bulb, Leonardo's flying machine, the candlestick telephone, the
penny-farthing, the Jacquard loom, Babbage's Difference Engine, Stephenson's Rocket, the first photograph.
*Halloween* — a black cat, a trick-or-treat street, a jack-o'-lantern, friendly ghosts, a scarecrow, a
haunted house, a pumpkin patch, a dewy spider's web. *Winter* — mittens and cocoa, a sledding hill, a
snowman, a cardinal, Bentley's snowflake, the skating pond (after Currier & Ives), a snow globe, a frosted
window. Seasonal packs are open all year; the one in season wears a badge on Home. Built and ordered like
the other collection packs: on Classic the 56 came out 4 Relaxed, 13 Steady, 3 Tricky, 17 Hard and 19
Fiendish; every pack runs from Relaxed or Steady to Hard or Fiendish (two Geometry levels were rebuilt with
other seeds so the pack has a gentle start), and the look-ahead player wins every one on Gentle or Classic.

**Found, explored, made harder.** With 193 mosaics, Home is organised as a collection. *Your collection*
counts what you have found, explored (finished), your stars and your mastered mosaics, with one chip per
theme (First Mosaics, Seasons, Nature, Art, Literature, History, Sky & Science, Tests of Skill) that scrolls to it; each
theme shows its packs as sideways shelves with a progress line. **Found:** when a pack opens (after
First Dig, or after any mosaic of a related pack — see the list above), its first three mosaics are found;
each one you finish in the pack finds the next, so there are always a few new pictures waiting and the
pack unfolds from gentle to hard. Unfound ones show as **?** cards ("finish 1 more in this pack").
**Explored:** stars for the hardest difficulty finished — ★ Gentle, ★★ Classic, ★★★ Expert.
**Made harder:** a flame for Expert with at least one harder option (*Mastered*); the finish card offers
the next harder step (Classic, then Expert, then Expert plus one more harder option), and the Status
filter (*To explore*, *Explored*, *Go harder*, *Mastered*) finds what to play next.

**Photo → puzzle.** Centre-crop, average into a tile grid (Chunky ≈1,600 / Fine ≈3,600 / Very fine
≈6,000 tiles), turn white and near-white tiles into open ground, cluster the rest into ≤6 colour
families in Lab space (look-alikes and slivers merged), give each family four tones by lightness,
then plan teams and tunnels by simulating a designer who plays as they build — the designer's play is
replayed to prove the level is solvable. All-white or almost-white photos are refused with a clear
message.

**Progression.** Resume from autosave, replay any mosaic, best time / difficulty per mosaic, and a
Nest Gallery of completed pictures.

### First playable version vs later

| Now (this build) | Later |
|---|---|
| 193 built-in mosaics in twenty-five packs and eight themes (main 5, Garden 8, Challenge 4, Master 8, a 56-mosaic collection: Wild Wonders, Gallery, World Art, Ancient World, Voyages, Modern Moments, Sky & Science; 56 Literature mosaics in seven packs; and 56 more in Natural History, World Craft, Geometry & Illusions, Probes & Telescopes, Inventions & Firsts and the seasonal Halloween and Winter packs) with measured ratings, found / explored / mastered progress and Home filters; unlimited pattern mosaics; photo mosaics | A sawtooth difficulty curve across packs; new mechanics introduced one at a time |
| Slots, undo, hints, scout, one-tap return, add slot, autosave, 3 difficulties per game; six harder options with a score multiplier; per-mosaic top-5 high scores with names (solo and two-player winners); exit X | Daily mosaic; time bonus or par times; star ratings for fewer assists; Game Center leaderboards (not available to app playgrounds) |
| Cartoon crawling ants, 7 ant-path styles, 0.1×–16× speed slider, pinch-zoom, ground colour, Action/Goal/Colony sound sets | Tiny footsteps and ambient colony sound; haptic patterns per colour; a second ant hill for big mosaics |
| Nest Gallery with miniatures | Gallery wall you can arrange; share a finished mosaic as an image |
| iPad + iPhone layouts in one app playground; two players on one iPad (race or shared board) | Daily Colony, Zen / Time Attack modes, level editor with share codes, new mechanics (mystery, roped, frozen, locks and keys, fog, hungry gates); two iPads over Multipeer; iCloud sync and Game Center (not in the app-playground capability list) |
| — | Genre mechanics seen in research (linked teams, hidden-colour teams), added one at a time with an explanation screen |

---

## 3. Architecture

```
TesseraColony.swiftpm/
  Package.swift            AppleProductTypes .iOSApplication, iPad + iPhone, iOS 17+
  Engine.swift             deterministic rules: claim BFS, slots, send, return, add slot, undo, hashes
  AntScheduler.swift       claims → timed trips (release slots, per-team cadence, pickup timing, lanes, poses)
  AntRenderer.swift        cartoon ant sprites per colour + live legs (tripod gait), shadows, carried tiles
  MosaicRaster.swift       stamps pre-rendered tile templates into one bitmap (fast for thousands of tiles)
  BoardView.swift          Canvas + TimelineView; pinch-zoom/pan; scout overlay
  GameController.swift     session state, slot occupancy in real time, game clock & speed, ground colour,
                           hints (background), saving, coaching
  LevelGenerator.swift     on-device team/tunnel planner (used for photos and patterns)
  PatternLevelBuilder.swift  procedural pattern mosaics from a seed (five layouts)
  PhotoLevelBuilder.swift  photo → palette, tiles, level;  PhotoLibrary.swift  decode + store photo levels
  HintSolver.swift         follow the plan, else greedy-rollout search (3 s budget), else "undo N"
  SoundBoard.swift         synthesized Action / Goal / Colony sounds, voice pool on AVAudioEngine, clink scheduling
  PathPlanner.swift        ant-path styles (A* with style costs, sniff stops, scout trails)
  VersusEngine.swift       two-player rules (race / shared board, reach, colour rule, scoring)
  VersusController.swift   a match: boards, schedulers, clock, slot upkeep, scores, end of match
  VersusView.swift         two-player screens, compact controls, setup sheet, results
  BoardPainter.swift       board drawing shared by one- and two-player boards
  Scoring.swift            harder options, the score formula, high-score tables, Home's rating filter
  Collection.swift         found / explored / mastered, stars, the Status filter, harder steps, shelf cards
  HighScoresView.swift     Home → High scores
  SelfTest.swift           on-device checks against golden values from the Python model (+ the Ant stress run)
  FlightRecorder.swift     crash report: the open game's settings, moves and last actions, offered on Home
                           after an unexpected stop
  ControlPanel / GameView / HomeView / Overlays / Theme   SwiftUI UI
  LevelData.swift          GENERATED: art, palette, tunnels, solutions, golden hashes, difficulty measurements
  LevelDataCollection.swift, LevelDataLiterature.swift, LevelDataDiscovery.swift, LevelDataSeasons.swift
                           GENERATED: the same for the collection, Literature, new and seasonal packs
Tools/  (Python)           art.py, art_challenge.py, generate_levels.py, engine.py (reference model), photo.py,
                           pattern.py, sounds.py, tests.py, session_sim.py (play sessions mirrored step by step), ant_gait.py, render.py, mockups.py, art_scenes.py, art_wild.py,
                           art_gallery.py, art_worldart.py, art_ancient.py, art_voyages.py, art_modern.py, art_cosmos.py,
                           art_myths.py, art_tales.py, art_childrens.py, art_stage.py, art_adventure.py, art_gothic.py, art_novels.py,
                           preview_gif.py, path_styles.py, versus.py, art_packs.py (Garden / Master
                           pictures), scoring.py (scores, tables, No colour twice search), regen_some.py, try_seeds.py, build_collection.py
```

Key decisions: the rules engine is pure and deterministic, so a Python mirror can prove solvability,
path legality and timing, and the app re-derives the same golden hashes on the iPad. Claims are decided
the moment a team is sent; the animation is scheduled separately, and slot occupancy combines the
two (waiting teams from the rules, teams still picking up tiles from the schedule).

## 4. Path to iPhone and release

The same playground already targets iPhone (compact layout: board on top, controls below, scrollable).
For release: set a real bundle ID and an app icon (App Settings in Swift Playground), test on an iPhone,
then upload to App Store Connect from Swift Playground or open the `.swiftpm` in Xcode on a Mac.
The photo picker runs out of process, so no photo-library permission prompt is needed.

**Step-by-step guide: `Docs/IPHONE.md`** (research, 5 Oct 2026). In short: Swift Playground has no iPhone
version and can't install onto a phone, so without a Mac the route is the Apple Developer Program
(US$99/year) → *Upload to App Store Connect* from Swift Playground on the iPad → TestFlight internal testing
→ install on the iPhone. Before paying, preview the phone layout by narrowing the Swift Playground window.
The guide lists the Package.swift, Info.plist and privacy-manifest changes, and the iPhone risks (two-player
mode first).

## Sources

- Ants Flow: Pixel Puzzle Game — App Store: https://apps.apple.com/us/app/ants-flow-pixel-puzzle-game/id6761752384
- Ants Flow: Pixel Color Puzzle! — Google Play: https://play.google.com/store/apps/details?id=com.ants.box&hl=en_US
- Ants Flow — AppBrain (reviews, downloads): https://www.appbrain.com/app/ants-flow-pixel-color-puzzle/com.ants.box
- Colony Flow! — App Store: https://apps.apple.com/us/app/colony-flow/id6779167923
- Colony Flow! — App Store reviews: https://apps.apple.com/us/app/colony-flow/id6779167923?see-all=reviews&platform=iphone
- Colony Flow! — Google Play: https://play.google.com/store/apps/details?id=com.abi.colony.flow&hl=en_US
- Colony Flow! — AppBrain: https://www.appbrain.com/app/colony-flow/com.abi.colony.flow
- Colony Flow walkthroughs (rules, slots, linked/hidden boxes): https://colony-flow.com/level/250 · https://colony-flow.com/level/824 · https://colony-flow.com/level/987
- LevelSolve, "How to Beat Hard Colony Flow Levels": https://levelsolve.com/blog/how-to-beat-hard-colony-flow-levels/
- Ant Blocks: Puzzle Game — Google Play (colour-similarity review): https://play.google.com/store/apps/details?id=com.ant.blocks&hl=en_US
- Deconstructor of Fun, "Pixel Flow: The Publisher's Dream": https://www.deconstructoroffun.com/blog/2026/2/13/pixel-flow-the-publishers-dream
- Swift Playground — App Store (4.7: Swift 6 + iOS 26 SDK; requires iPadOS 18): https://apps.apple.com/us/app/swift-playground/id908519492
- Slatepad, Swift Playground 4.7 with iOS 26 SDK (March 17, 2026): https://slatepad.org/2026/03/17/swift-playground-ipad-ios-26-sdk-liquid-glass/
- Apple, Swift Playground release notes: https://developer.apple.com/swift-playground/release-notes/
- App playground (.swiftpm) manifest examples: https://skyaaron.com/posts/swiftpm-app-projects/ · https://github.com/alemohamad/swift-playground-app-structure
- Collection subjects — My Modern Met, "37 of the Most Famous Artworks in History": https://mymodernmet.com/most-famous-artwork-history/
- Collection subjects — TIME, "Mankind's Greatest Explorations and Adventures": https://content.time.com/time/specials/packages/completelist/0,29569,1932261,00.html
- Collection subjects — Wikipedia, "Seven Natural Wonders (CNN)": https://en.wikipedia.org/wiki/Seven_Natural_Wonders_(CNN)
