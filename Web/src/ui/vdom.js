// A very small virtual DOM: declarative views (like SwiftUI bodies) patched onto real elements.
// h(tag, props, ...children) builds a node; render(node, container) creates or patches it.
//
// Props: key, ref(el) (called once when the element is created), class (string | array | object),
// style (string | object), html (innerHTML, for inline SVG icons), on<event> handlers (lower case
// after "on", e.g. onclick, onpointerdown), value/checked/disabled/selected set as properties,
// anything else as an attribute (false/null removes it).

const SVG_NS = 'http://www.w3.org/2000/svg';

function flatten(children, out) {
  for (const c of children) {
    if (c === null || c === undefined || c === false || c === true) continue;
    if (Array.isArray(c)) flatten(c, out);
    else if (typeof c === 'object') out.push(c);
    else out.push({ tag: '#text', text: String(c) });
  }
  return out;
}

export function h(tag, props, ...children) {
  if (typeof tag === 'function') return tag(props || {}, flatten(children, []));
  const p = props || {};
  return { tag, props: p, key: p.key, children: flatten(children, []), el: null };
}

function className(v) {
  if (!v) return '';
  if (typeof v === 'string') return v;
  if (Array.isArray(v)) return v.filter(Boolean).map(className).join(' ');
  return Object.keys(v).filter(k => v[k]).join(' ');
}

function setStyle(el, oldV, v) {
  if (typeof v === 'string' || v == null) {
    if (oldV !== v) el.style.cssText = v || '';
    return;
  }
  const old = typeof oldV === 'object' && oldV ? oldV : {};
  if (typeof oldV === 'string') el.style.cssText = '';
  for (const k in old) if (!(k in v)) {
    if (k.startsWith('--')) el.style.removeProperty(k); else el.style[k] = '';
  }
  for (const k in v) {
    if (old[k] === v[k]) continue;
    if (k.startsWith('--')) el.style.setProperty(k, v[k]); else el.style[k] = v[k];
  }
}

function dispatcher(e) {
  const fn = this.__handlers && this.__handlers[e.type];
  if (fn) fn(e);
}

const PROPS_AS_PROPERTY = new Set(['value', 'checked', 'disabled', 'selected', 'indeterminate']);

function setProp(el, name, oldV, v, isSvg) {
  if (name === 'key' || name === 'ref' || name === 'children') return;
  if (name === 'class') {
    const c = className(v);
    if (className(oldV) !== c || el.__cls !== c) {
      if (isSvg) el.setAttribute('class', c); else el.className = c;
      el.__cls = c;
    }
    return;
  }
  if (name === 'style') { setStyle(el, oldV, v); return; }
  if (name === 'html') { if (oldV !== v) el.innerHTML = v || ''; return; }
  if (name.startsWith('on')) {
    const type = name.slice(2);
    if (!el.__handlers) el.__handlers = {};
    if (v && !el.__handlers[type]) el.addEventListener(type, dispatcher, type === 'touchstart' || type === 'touchmove' || type === 'wheel' ? { passive: false } : false);
    if (!v && el.__handlers[type]) el.removeEventListener(type, dispatcher);
    el.__handlers[type] = v || null;
    return;
  }
  if (PROPS_AS_PROPERTY.has(name) && !isSvg) {
    if (el[name] !== v) el[name] = v == null ? (name === 'value' ? '' : false) : v;
    return;
  }
  if (v === false || v == null) { if (oldV != null && oldV !== false) el.removeAttribute(name); }
  else if (oldV !== v) el.setAttribute(name, v === true ? '' : String(v));
}

function create(node, isSvg) {
  if (node.tag === '#text') {
    node.el = document.createTextNode(node.text);
    return node.el;
  }
  const svg = isSvg || node.tag === 'svg';
  const el = svg ? document.createElementNS(SVG_NS, node.tag) : document.createElement(node.tag);
  node.el = el;
  for (const k in node.props) setProp(el, k, undefined, node.props[k], svg);
  if (!('html' in node.props)) for (const c of node.children) el.appendChild(create(c, svg && node.tag !== 'foreignObject'));
  if (node.props.ref) node.props.ref(el);
  return el;
}

function sameKind(a, b) { return a.tag === b.tag && a.key === b.key; }

function patch(old, node, isSvg) {
  if (node.tag === '#text') {
    node.el = old.el;
    if (old.text !== node.text) node.el.nodeValue = node.text;
    return node.el;
  }
  const el = (node.el = old.el);
  const svg = isSvg || node.tag === 'svg';
  const op = old.props, np = node.props;
  for (const k in op) if (!(k in np)) setProp(el, k, op[k], undefined, svg);
  for (const k in np) if (op[k] !== np[k] || k === 'class' || k === 'value' || k === 'checked') setProp(el, k, op[k], np[k], svg);
  if (!('html' in np)) patchChildren(el, old.children, node.children, svg && node.tag !== 'foreignObject');
  return el;
}

function patchChildren(parent, oldCh, newCh, isSvg) {
  const keyed = newCh.length > 0 && newCh.some(c => c.key !== undefined);
  if (!keyed) {
    const n = Math.min(oldCh.length, newCh.length);
    for (let i = 0; i < n; i++) {
      if (sameKind(oldCh[i], newCh[i])) patch(oldCh[i], newCh[i], isSvg);
      else parent.replaceChild(create(newCh[i], isSvg), oldCh[i].el);
    }
    for (let i = n; i < newCh.length; i++) parent.appendChild(create(newCh[i], isSvg));
    for (let i = oldCh.length - 1; i >= n; i--) parent.removeChild(oldCh[i].el);
    return;
  }
  const byKey = new Map();
  const unkeyedOld = [];
  for (const c of oldCh) {
    if (c.key !== undefined) byKey.set(c.tag + '\u0000' + c.key, c);
    else unkeyedOld.push(c);
  }
  let u = 0;
  const used = new Set();
  const els = [];
  for (const c of newCh) {
    let old = null;
    if (c.key !== undefined) old = byKey.get(c.tag + '\u0000' + c.key) || null;
    else {
      while (u < unkeyedOld.length && unkeyedOld[u].tag !== c.tag) u++;
      if (u < unkeyedOld.length) old = unkeyedOld[u++];
    }
    if (old && !used.has(old)) { used.add(old); els.push(patch(old, c, isSvg)); }
    else els.push(create(c, isSvg));
  }
  for (const c of oldCh) if (!used.has(c) && c.el.parentNode === parent) parent.removeChild(c.el);
  let ref = parent.firstChild;
  for (const el of els) {
    if (el === ref) ref = ref.nextSibling;
    else parent.insertBefore(el, ref);
  }
}

/** Render `node` as the only child of `container`, patching what is already there. */
export function render(node, container) {
  const old = container.__vnode;
  if (!old) {
    container.textContent = '';
    container.appendChild(create(node, false));
  } else if (sameKind(old, node)) {
    patch(old, node, false);
  } else {
    container.replaceChild(create(node, false), old.el);
  }
  container.__vnode = node;
}
