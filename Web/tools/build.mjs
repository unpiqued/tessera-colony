// Bundler for the artifact, plus a second bundle for the builder Web Worker.
//
// Differences from build.mjs:
//   1. The module loader is a function, bundle(entry), so it can run twice with separate module maps.
//   2. src/builders/builderWorkerMain.js is bundled on its own (builders + the core modules they
//      import) and embedded in the page as JSON text:
//        <script type="application/json" id="tc-builder-worker">"…source…"</script>
//      placed with the level data (the <!--DATA--> placeholder), so page.html needs no change.
//      builderWorker.js reads it (builderWorkerSource) and starts it from a blob: URL; every "<" is
//      written as < so no "</script" or "<!--" can end or confuse the element.
//   3. `node tools/build_with_worker.mjs --worker-only OUT.js` writes just the worker bundle (tests).
//
// Supported syntax (keep to it in src/):
//   import { a, b as c } from './x.js';      import * as ns from './x.js';
//   export function f / export async function f / export class C / export const|let x
//   export { a, b as c };
// No default exports, no bare package imports, no dynamic import().
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { dirname, resolve, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const srcDir = resolve(root, 'src');
const entry = resolve(srcDir, 'main.js');
const workerEntry = resolve(srcDir, 'builders/builderWorkerMain.js');

/** Bundles `entryAbs` and the relative modules it imports into one IIFE (source text). */
function bundle(entryAbs) {
  const modules = new Map(); // abs path -> { id, code, deps }
  const order = [];

  function load(abs) {
    if (modules.has(abs)) return modules.get(abs);
    const id = relative(srcDir, abs);
    let code = readFileSync(abs, 'utf8');
    const deps = [];
    const exportsList = [];
    const rec = { id, code: '', deps };
    modules.set(abs, rec);

    // imports
    code = code.replace(/^import\s+(\{[\s\S]*?\}|\*\s+as\s+\w+)\s+from\s+['"](\.[^'"]+)['"];?/gm, (m, what, spec) => {
      const depAbs = resolve(dirname(abs), spec);
      const dep = load(depAbs);
      deps.push(dep.id);
      const ref = `__m[${JSON.stringify(dep.id)}]`;
      if (what.startsWith('*')) {
        const ns = what.replace(/\*\s+as\s+/, '').trim();
        return `const ${ns} = ${ref};`;
      }
      const names = what.slice(1, -1).split(',').map(s => s.trim()).filter(Boolean)
        .map(s => { const [a, b] = s.split(/\s+as\s+/); return b ? `${a.trim()}: ${b.trim()}` : a.trim(); });
      return `const { ${names.join(', ')} } = ${ref};`;
    });
    if (/^import\s/m.test(code)) throw new Error(`${id}: unsupported import syntax`);

    // exports
    code = code.replace(/^export\s+(async\s+function|function\*?|class|const|let|var)\s+([A-Za-z_$][\w$]*)/gm, (m, kind, name) => {
      exportsList.push(`${name}: ${name}`);
      return `${kind} ${name}`;
    });
    code = code.replace(/^export\s*\{([\s\S]*?)\};?/gm, (m, list) => {
      for (const s of list.split(',').map(x => x.trim()).filter(Boolean)) {
        const [a, b] = s.split(/\s+as\s+/);
        exportsList.push(`${(b || a).trim()}: ${a.trim()}`);
      }
      return '';
    });
    if (/^export\s/m.test(code)) throw new Error(`${id}: unsupported export syntax`);

    rec.code = `__m[${JSON.stringify(id)}] = (function () {\n${code}\nreturn { ${exportsList.join(', ')} };\n})();\n`;
    order.push(rec);
    return rec;
  }

  load(entryAbs);
  return {
    count: order.length,
    text: `(function () {\n"use strict";\nconst __m = Object.create(null);\n${order.map(r => `// ---- ${r.id}\n${r.code}`).join('\n')}\n})();\n`,
  };
}

const worker = bundle(workerEntry);

const argv = process.argv.slice(2);
const wi = argv.indexOf('--worker-only');
if (wi >= 0) {
  const out = resolve(argv[wi + 1] || resolve(root, 'dist/builder-worker.js'));
  mkdirSync(dirname(out), { recursive: true });
  writeFileSync(out, worker.text);
  console.log(`worker: ${worker.count} modules, ${(worker.text.length / 1024).toFixed(0)} KB -> ${out}`);
  process.exit(0);
}

const main = bundle(entry);
const template = readFileSync(resolve(srcDir, 'ui/page.html'), 'utf8');
const css = readFileSync(resolve(srcDir, 'ui/style.css'), 'utf8');
const levels = readFileSync(resolve(root, 'data/levels.json'), 'utf8');
const safeJSON = s => s.replace(/<\//g, '<\\/');
const workerJSON = JSON.stringify(worker.text).replace(/</g, '\\u003c');
const html = template
  .replace('/*STYLE*/', () => css)
  .replace('<!--DATA-->', () => `<script type="application/json" id="tc-levels">${safeJSON(levels)}</script>\n`
    + `<script type="application/json" id="tc-builder-worker">${workerJSON}</script>`)
  .replace('/*SCRIPT*/', () => main.text.replace(/<\/script/gi, '<\\/script'));

mkdirSync(resolve(root, 'dist'), { recursive: true });
const out = resolve(root, 'dist/tessera-colony.html');
writeFileSync(out, html);
console.log(`${main.count} modules + worker ${worker.count} modules (${(worker.text.length / 1024).toFixed(0)} KB), `
  + `${(html.length / 1024).toFixed(0)} KB -> ${relative(root, out)}`);
