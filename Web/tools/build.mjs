// Minimal bundler for the artifact: follows relative ES-module imports from src/main.js, wraps
// each module in its own function scope, and writes one self-contained HTML page
// (dist/tessera-colony.html) with the page template, styles, script and level data inline.
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

load(entry);

const bundle = `(function () {\n"use strict";\nconst __m = Object.create(null);\n${order.map(r => `// ---- ${r.id}\n${r.code}`).join('\n')}\n})();\n`;

const template = readFileSync(resolve(srcDir, 'ui/page.html'), 'utf8');
const css = readFileSync(resolve(srcDir, 'ui/style.css'), 'utf8');
const levels = readFileSync(resolve(root, 'data/levels.json'), 'utf8');
const safeJSON = s => s.replace(/<\//g, '<\\/');
const html = template
  .replace('/*STYLE*/', () => css)
  .replace('<!--DATA-->', () => `<script type="application/json" id="tc-levels">${safeJSON(levels)}</script>`)
  .replace('/*SCRIPT*/', () => bundle.replace(/<\/script/gi, '<\\/script'));

mkdirSync(resolve(root, 'dist'), { recursive: true });
const out = resolve(root, 'dist/tessera-colony.html');
writeFileSync(out, html);
console.log(`${order.length} modules, ${(html.length / 1024).toFixed(0)} KB -> ${relative(root, out)}`);
