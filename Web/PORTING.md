# Tessera Colony — browser port: conventions

The Swift Playground app in `../TesseraColony.swiftpm` is being ported to one self-contained HTML page
(a claude.ai artifact). Swift is never compiled here; read it. Python reference models in `../Tools`
mirror the Swift logic and are the source of truth for exact-match tests.

## Layout
- `src/core/` — rules and data, no DOM (runs in Node): `util.js` (hash32, SplitMix64, FNV), `board.js`,
  `engine.js` (Game), `hint.js` (HintSolver) — **already written and verified; do not edit**
  (all 193 golden replays pass: `node --test test/engine.test.js`). If you need a change there, say so in
  your report instead.
- `src/render/` — ants, scheduler, path planner, mosaic raster, board drawing (Canvas 2D).
- `src/sound/` — Web Audio port of SoundBoard.
- `src/builders/` — pattern and photo level builders, level generator, difficulty probe.
- `src/ui/` — screens (Home, game, overlays). Owned by the integrator.
- `test/*.test.js` — `node --test test/` (Node 22). Browser checks: Python Playwright
  (`from playwright.sync_api import sync_playwright`; Chromium is preinstalled, never run
  `playwright install`). No npm packages are available (the registry is blocked).
- `tools/build.mjs` bundles `src/main.js` into `dist/tessera-colony.html`.

## Module syntax (the bundler is tiny — keep to this)
- ES modules, **named exports only**: `export function f`, `export class C`, `export const X`,
  `export { a, b }`. Imports: `import { a, b as c } from './x.js'` or `import * as ns from './x.js'`,
  relative paths with the `.js` extension. No default exports, no packages, no dynamic `import()`.
- All `import` / `export` keywords at the start of a line.

## Mirror the Swift API one-to-one
- Same type names, method and property names, and argument order as the Swift code, so the
  integrator can port callers line by line. Swift argument labels become positional arguments in the
  same order. Defaulted Swift parameters stay trailing optional parameters.
- Swift `static` members → `static` class members or a frozen object of functions.
- Simple enums → frozen objects of string constants, e.g.
  `export const PathStyle = Object.freeze({ direct: 'direct', … })`, plus lookup helpers for their
  computed properties (`PathStyle.title(s)` or a `PATH_STYLE_INFO[s].title` table — document which).
- Enums with associated values → tagged objects: `{ kind: 'move', code, onPlan }`.
- Structs → plain objects. Swift copies structs on assignment; copy explicitly where the Swift code
  relies on that (see `cloneState` in engine.js).
- Types: `UInt64` → `BigInt`; `UInt32` → number (`>>> 0`); `[Bool]` per cell → `Uint8Array`;
  `[Int32]`/`[Double]` per cell → `Int32Array`/`Float64Array`; colours are `0xRRGGBB` numbers.
- Data shapes already fixed by the core: TeamSpec `{family, quota}`; Team
  `{uid, family, quota, remaining, held}`; Claim `{team, family, tile, path:number[]}`;
  GameState `{open:Uint8Array, heads, chambers, capacity, added, jammed, cleared, returned}`;
  LevelPalette `{names:string[], tones:number[][]}` (6 families × 4 tones).
- Game time is in seconds (a plain number). Real time: `performance.now()` (ms).
- Keep the Swift doc comments (shortened is fine) — they explain the why.

## The page runs in a sandboxed iframe
No network, no `alert/confirm/prompt`, audio only after a user gesture, Web Workers only from
`blob:` URLs. Must run smoothly on an iPad (Safari) and on phones, in light and dark themes.
