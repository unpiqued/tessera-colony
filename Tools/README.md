# Tools (Python 3 + numpy, scipy, Pillow)

| Script | Purpose |
|---|---|
| `palette.py` | The six colour families × four glaze tones, plus a CIEDE2000 separation check (`python3 palette.py`) |
| `art_challenge.py` | The four Challenge mosaics (nested rings, basket weave, labyrinth, rose window) |
| `art_scenes.py` | The sixteen Garden and Master pictures (balloon, lighthouse, toadstools, tulips, sailboat, honeycomb, owl, desert; tiger, giraffe, autumn tree, castle, viaduct, city at dusk, chameleon, octopus) — one subject each |
| `art_packs.py` | Garden, Master and collection level lists (21 collection packs): key, title, subtitle, picture, build seed (and for the collection, the builder tier); which Master levels use the bar-checked build |
| `art_wild.py`, `art_gallery.py`, `art_worldart.py`, `art_ancient.py`, `art_voyages.py`, `art_modern.py`, `art_cosmos.py` | The 56 collection pictures, eight per pack (artworks are public-domain homages; history scenes are original compositions) |
| `art_myths.py`, `art_tales.py`, `art_childrens.py`, `art_stage.py`, `art_adventure.py`, `art_gothic.py`, `art_novels.py` | The 56 Literature pictures, eight per pack: scenes from public-domain books, plays and tales, drawn as original compositions (never from film versions) |
| `art_naturalist.py`, `art_crafts.py`, `art_geometry.py`, `art_space.py`, `art_inventions.py`, `art_halloween.py`, `art_winter.py` | The 56 newest pictures, eight per pack: natural-history plates, world crafts, geometry and illusions (the Mandelbrot set is computed), views from probes and telescopes, inventions, Halloween and Winter |
| `art.py` | Draws the mosaics procedurally at 8× supersampling and quantises them to tiles (family from the dominant object, tone from shading) → `art.json` |
| `engine.py` | Reference model of the rules engine (slots, recovery, legacy Hold for old saves), hint search, ant scheduler and ant-path styles (mirrors the Swift code) |
| `path_styles.py` | Picture of one team routed by each ant-path style |
| `generate_levels.py` | Plans teams/tunnels by simulating a designer, proves solvability, measures difficulty (careless, one-step and look-ahead players), searches hard tunnel deals for the Challenge and Master packs (for some Master pictures, every deal the search accepted is checked against the Master bar and the hardest passing one is kept), writes `LevelData.swift` (plus `LevelDataCollection.swift` and `LevelDataLiterature.swift`) with golden hashes and ratings |
| `photo.py` | Reference photo → puzzle pipeline (white removal, Lab k-means, tones, planning) |
| `pattern.py` | Reference pattern-mosaic generator: five layouts (rosette, starburst, fish scales, kaleidoscope, ribbons), same formula and seed handling as PatternLevelBuilder.swift |
| `tests.py` | The automated checks summarised in `Docs/VALIDATION.md` |
| `session_sim.py`, `run_session_tests.py` | Whole play sessions through a step-by-step mirror of the Swift game screen (scheduler with pruning, slots panel, ant pose and trail maths), checking every step that would stop the Swift app — written for the Alhambra Tiles crash report; also the exact sequence of the app's *Ant stress* self-test. `run_session_tests.py report.json results.json` runs only these checks and merges them into a results file |
| `sounds.py` | Reference model of the synthesized Action and Goal sound sets and colony clinks (mirrors SoundBoard.swift), click-timing simulation, WAV output and listening previews (`python3 sounds.py OUT_DIR [report.json]`) |
| `ant_gait.py` | Leg kinematics mirror + planted-foot drift check + cartoon ant drawing |
| `scoring.py`, `versus.py` | Score formula and high-score tables (+ the *No colour twice* solvability search); two-player reference model |
| `regen_some.py`, `try_seeds.py`, `build_collection.py` | Rebuild only some levels with the same seeds and merge them into a report; try other build seeds for one Master picture; build the 112 collection and Literature levels (resumable) and merge them |
| `veil_proto.py` | Research prototype of a countdown veil (a hidden section that lifts after N tiles are removed); rebuilds shipped levels with a veil and rates them. Results in `Docs/data/veil_report.json`; not used by the app |
| `render.py`, `mockups.py`, `preview_gif.py` | Tile renderer mirror, labelled mockups, preview animation |

Typical run:

```
python3 art.py art.json
python3 generate_levels.py art.json ../TesseraColony.swiftpm/LevelData.swift report.json
python3 tests.py report.json ../TesseraColony.swiftpm/LevelData.swift results.json
```
Regenerating from scratch reproduces the shipped `LevelData.swift` byte for byte (everything is seeded; the Garden
and Master seeds are in `art_packs.py`).
