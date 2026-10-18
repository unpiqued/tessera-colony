// Entry module of the builder worker bundle (tools/build_with_worker.mjs bundles it separately and
// embeds the result in the page; BuilderClient starts it from a blob: URL).
// Protocol: the worker posts { ready: true } once loaded; each request { id, kind, params } gets
// { id, ok: true, result } or { id, ok: false, error } (see runBuild in builderWorker.js).

import { runBuild } from './builderWorker.js';

export function installBuilderWorker(scope) {
  scope.onmessage = e => {
    const { id, kind, params } = e.data || {};
    let reply;
    try {
      reply = { id, ok: true, result: runBuild(kind, params) };
    } catch (err) {
      reply = { id, ok: false, error: String((err && err.stack) || err) };
    }
    scope.postMessage(reply);
  };
  scope.postMessage({ ready: true });
}

// Install only inside a worker (never when this module ends up in a page or in Node).
if (typeof self !== 'undefined' && typeof document === 'undefined' && typeof self.postMessage === 'function'
    && typeof importScripts === 'function') {
  installBuilderWorker(self);
}
