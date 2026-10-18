// The built-in level data (Web/data/levels.json, converted from LevelData*.swift by
// tools/convert_levels.py). Shape:
//   { palette: { names, tones, grout, soil, soilDark },
//     levels: { <Swift variable name>: { id, title, subtitle, art, tunnels: [[[family, quota], …], …],
//               chambersGentle, chambersClassic, chambersExpert, solution, goldenClaimsPerMove,
//               goldenClaimsHash: "16 hex digits", goldenFinalStateHash, carelessWins, greedyWins,
//               isChallenge, pack } } }
//
// Nothing here (or in the modules built on it) touches the data at import time. The browser entry
// point calls setLevelData(JSON.parse(document.getElementById('tc-levels').textContent)) first;
// tests call it with the file's contents. Modules that derive objects from the data register with
// onLevelData() and rebuild lazily whenever the data is replaced.
//
// The bundler copies imported bindings once, so the data is only ever reached through functions.

let data = null;
let version = 0;
const listeners = [];

/** Installs the level data (an object, or its JSON text). Replacing it invalidates every cache. */
export function setLevelData(json) {
  const d = typeof json === 'string' ? JSON.parse(json) : json;
  if (!d || typeof d !== 'object' || !d.palette || !d.levels) {
    throw new Error('setLevelData: expected { palette, levels }');
  }
  data = d;
  version += 1;
  for (const fn of listeners.slice()) fn(d, version);
}

export function hasLevelData() { return data !== null; }

/** Increments every time setLevelData installs new data (0 = none yet). */
export function levelDataVersion() { return version; }

/** The raw data; throws a clear error when setLevelData has not been called yet. */
export function requireLevelData() {
  if (data === null) throw new Error('Level data is not loaded: call setLevelData(json) first');
  return data;
}

/** The raw palette record { names, tones, grout, soil, soilDark }. */
export function rawPalette() { return requireLevelData().palette; }

/** The raw record of one built-in level by its Swift variable name (undefined if unknown). */
export function rawLevel(name) {
  const levels = requireLevelData().levels;
  return Object.prototype.hasOwnProperty.call(levels, name) ? levels[name] : undefined;
}

/** Swift variable names of every built-in level, in file order. */
export function levelVariableNames() { return Object.keys(requireLevelData().levels); }

/**
 * Calls fn(data, version) whenever new data is installed (and at once if data is already there).
 * Returns a function that removes the listener.
 */
export function onLevelData(fn) {
  listeners.push(fn);
  if (data !== null) fn(data, version);
  return () => {
    const i = listeners.indexOf(fn);
    if (i >= 0) listeners.splice(i, 1);
  };
}
