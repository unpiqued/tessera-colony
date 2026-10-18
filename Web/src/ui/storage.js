// Where progress lives. SaveStore talks to a synchronous key/value backend; this one keeps every
// value in memory, mirrors it to the browser's localStorage (instant, this device only), and —
// when the viewer is signed in to Claude and the page has the `db` capability — to the viewer's
// own private documents (data/users/<id>/kv/<key>), so progress follows them to other devices.
// Each value carries a timestamp; on start the newer copy of each key wins.

const PREFIX = 'tessera:';
const STAMPS = PREFIX + '__stamps';
const WRITE_DELAY = 1200;

function safeLocal() {
  try {
    const ls = window.localStorage;
    const probe = PREFIX + '__probe';
    ls.setItem(probe, '1');
    ls.removeItem(probe);
    return ls;
  } catch (e) {
    return null;
  }
}

function docId(key) {
  let id = key.replace(/[^A-Za-z0-9_.~:@+-]/g, '_');
  if (id !== key || id === '.' || id === '..') {
    let h = 2166136261;
    for (let i = 0; i < key.length; i++) h = Math.imul(h ^ key.charCodeAt(i), 16777619) >>> 0;
    id = id.slice(0, 150) + '-' + h.toString(36);
  }
  return id;
}

export function createStorage() {
  const mem = new Map();
  let stamps = {};
  const ls = safeLocal();
  const listeners = new Set();
  let remote = null;            // { col } once connected
  let remoteState = ls ? 'local' : 'memory';
  const pending = new Map();    // key -> true (value read from mem at flush time)
  let flushTimer = null;
  let flushing = false;

  if (ls) {
    try { stamps = JSON.parse(ls.getItem(STAMPS) || '{}') || {}; } catch (e) { stamps = {}; }
    try {
      for (let i = 0; i < ls.length; i++) {
        const k = ls.key(i);
        if (k && k.startsWith(PREFIX) && k !== STAMPS) mem.set(k.slice(PREFIX.length), ls.getItem(k));
      }
    } catch (e) { /* storage became unavailable */ }
  }

  function saveStamps() {
    if (!ls) return;
    try { ls.setItem(STAMPS, JSON.stringify(stamps)); } catch (e) { /* full or blocked */ }
  }

  function localWrite(key, value) {
    if (value === null) mem.delete(key); else mem.set(key, value);
    if (!ls) return;
    try {
      if (value === null) ls.removeItem(PREFIX + key); else ls.setItem(PREFIX + key, value);
    } catch (e) { /* quota or blocked: memory still holds it */ }
  }

  function queueRemote(key) {
    if (!remote) return;
    pending.set(key, true);
    if (!flushTimer) flushTimer = setTimeout(flush, WRITE_DELAY);
  }

  async function flush() {
    flushTimer = null;
    if (!remote || flushing) { if (remote && pending.size) flushTimer = setTimeout(flush, WRITE_DELAY); return; }
    flushing = true;
    try {
      const keys = [...pending.keys()];
      pending.clear();
      for (const key of keys) {
        const v = mem.has(key) ? mem.get(key) : null;
        try {
          await remote.col.doc(docId(key)).set({ k: key, v, t: stamps[key] || Date.now() });
        } catch (e) {
          const code = e && e.code;
          if (code === 'resource_exhausted' || code === 'unavailable') { pending.set(key, true); }
          else if (code === 'invalid_argument' || code === 'revoked' || code === 'quota_exceeded' || code === 'not_granted') {
            remote = null; remoteState = ls ? 'local' : 'memory'; break;
          }
        }
      }
    } finally {
      flushing = false;
      if (remote && pending.size && !flushTimer) flushTimer = setTimeout(flush, WRITE_DELAY * 2);
    }
  }

  const backend = {
    getItem(key) { return mem.has(key) ? mem.get(key) : null; },
    setItem(key, value) {
      const v = String(value);
      if (mem.get(key) === v) return;
      stamps[key] = Date.now();
      localWrite(key, v);
      saveStamps();
      queueRemote(key);
    },
    removeItem(key) {
      if (!mem.has(key) && !(key in stamps)) return;
      stamps[key] = Date.now();
      localWrite(key, null);
      saveStamps();
      queueRemote(key);
    },
    keys() { return [...mem.keys()]; },
  };

  /** Connect to the viewer's private store; calls onChanged() if newer data arrived. */
  async function connect(onChanged) {
    try {
      const c = typeof window !== 'undefined' ? window.claude : null;
      if (!c || typeof c.use !== 'function') return;
      const [user, db] = await Promise.all([c.use('user'), c.use('db')]);
      if (!user || !db) return;
      const id = await user.id();
      if (!id) return;
      const col = db.collection('data/users/' + id + '/kv');
      const snap = await col.limit(1000).get();
      let changed = false;
      const seen = new Set();
      for (const d of snap.docs) {
        const body = d.data();
        if (!body || typeof body.k !== 'string') continue;
        const key = body.k;
        seen.add(key);
        const rt = Number(body.t) || 0;
        const lt = stamps[key] || 0;
        if (rt > lt) {
          const v = body.v === null || body.v === undefined ? null : String(body.v);
          if ((mem.has(key) ? mem.get(key) : null) !== v) changed = true;
          stamps[key] = rt;
          localWrite(key, v);
        } else if (lt > rt) {
          pending.set(key, true);
        }
      }
      for (const key of mem.keys()) if (!seen.has(key)) pending.set(key, true);
      saveStamps();
      remote = { col };
      remoteState = 'account';
      if (pending.size) flushTimer = setTimeout(flush, 200);
      for (const fn of listeners) fn();
      if (changed && onChanged) onChanged();
    } catch (e) {
      remote = null;
    }
  }

  return {
    backend,
    connect,
    flushNow: () => { if (flushTimer) { clearTimeout(flushTimer); flushTimer = null; } return flush(); },
    onStatus(fn) { listeners.add(fn); return () => listeners.delete(fn); },
    /** 'account' (synced to the viewer's Claude account), 'local' (this browser) or 'memory'. */
    get where() { return remoteState; },
  };
}
