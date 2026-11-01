// Service worker: owns the offscreen document and routes messages to it.
//
// The model cannot run here -- WebGPU is not exposed to service workers,
// and the worker is killed between events, which would mean reloading
// 173MB every time. offscreen.js holds the sessions; this file just makes
// sure it exists and forwards work to it.

const OFFSCREEN = 'offscreen.html';
const DEFAULTS = { hotkey: 'g', autoShow: false };

let creating = null;                 // de-dupes concurrent createDocument calls

async function hasDocument() {
  const ctxs = await chrome.runtime.getContexts({
    contextTypes: ['OFFSCREEN_DOCUMENT'],
    documentUrls: [chrome.runtime.getURL(OFFSCREEN)],
  });
  return ctxs.length > 0;
}

async function ensureDocument() {
  if (await hasDocument()) return;
  if (creating) return creating;
  creating = chrome.offscreen.createDocument({
    url: OFFSCREEN,
    reasons: ['BLOBS', 'WORKERS'],
    justification:
      'Decodes Street View image tiles and runs the country-classification ' +
      'model, which needs WebGPU and therefore a document context.',
  }).finally(() => { creating = null; });
  return creating;
}

async function toOffscreen(payload) {
  await ensureDocument();
  return chrome.runtime.sendMessage({ target: 'offscreen', ...payload });
}

async function settings() {
  return { ...DEFAULTS, ...(await chrome.storage.sync.get(DEFAULTS)) };
}

chrome.runtime.onMessage.addListener((msg, _sender, reply) => {
  if (!msg || msg.target === 'offscreen') return;   // not ours to handle

  if (msg.type === 'settings') {
    settings().then((s) => reply({ ok: true, data: s }));
    return true;
  }
  if (msg.type === 'health' || msg.type === 'predict') {
    toOffscreen(msg)
      .then((r) => reply(r || { ok: false, error: 'no response from model' }))
      .catch((e) => reply({ ok: false, error: String(e.message || e) }));
    return true;
  }
});

// Warm the model up when a supported tab loads, so the first guess of a
// round is not the one that pays the startup cost.
chrome.runtime.onInstalled.addListener(() => { ensureDocument().catch(() => {}); });
chrome.runtime.onStartup.addListener(() => { ensureDocument().catch(() => {}); });
