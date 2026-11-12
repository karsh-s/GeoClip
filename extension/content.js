/*
 * GeoGuessr Assistant — content script.
 *
 * Reads the Street View panorama id out of the page's own tile requests,
 * runs the on-device model over it, and shows the answer with a map
 * and the visual evidence behind it. Nothing leaves the machine except
 * the request for the panorama's own image tiles.
 *
 * It predicts from pixels. It does not read the game's answer, place
 * pins, or submit guesses.
 */

(function () {
  'use strict';

  const CFG = { hotkey: 'g', autoShow: false };

  // ── Solo-play guard ──────────────────────────────────────
  // The assistant is for solo play. In any mode where a live opponent is
  // involved it disables itself: no predictions, no panel, no inference
  // at all. Matching is on the URL, which is reliable across all
  // three supported sites, and is re-checked on every SPA navigation.
  const MULTIPLAYER_RE = [
    /\/duels?(\/|$)/i,            // GeoGuessr Duels / Team Duels
    /\/team-duels?(\/|$)/i,
    /\/battle-royale(\/|$)/i,
    /\/br(\/|$)/i,
    /\/live-challenge(\/|$)/i,
    /\/party(\/|$)/i,
    /\/lobby(\/|$)/i,
    /\/multiplayer(\/|$)/i,
    /\/competitive(\/|$)/i,
    /\/ranked(\/|$)/i,
    /\/matchmaking(\/|$)/i,
    /\/versus(\/|$)/i,
    /\/1v1(\/|$)/i,
    /\/online(\/|$)/i,            // WorldGuessr / OpenGuessr online play
    /\/room(\/|$)/i,
  ];

  let blocked = false;

  function multiplayerHere() {
    const u = location.pathname + location.search + location.hash;
    return MULTIPLAYER_RE.some(re => re.test(u));
  }

  function refreshMode() {
    const was = blocked;
    blocked = multiplayerHere();
    if (blocked && !was) {
      // drop anything already accumulated so nothing lingers on screen
      sums = new Map(); panoCount = 0; lastCues = [];
      if (ui) ui.root.classList.add('gc-hidden');
      visible = false;
    }
    if (ui && was !== blocked) render();
  }

  function watchNavigation() {
    for (const m of ['pushState', 'replaceState']) {
      const orig = history[m];
      history[m] = function (...a) {
        const r = orig.apply(this, a);
        setTimeout(refreshMode, 0);
        return r;
      };
    }
    addEventListener('popstate', refreshMode);
    addEventListener('hashchange', refreshMode);
    setInterval(refreshMode, 2000);   // belt and braces for client routers
    refreshMode();
  }
  const seen = new Set();
  let sums = new Map();        // country -> summed probability
  let panoCount = 0;
  let lastCues = [];
  let cueMode = 'none';
  let latestPano = null;
  let busy = false;
  let visible = false;
  let ui = null;

  chrome.runtime.sendMessage({ type: 'settings' }, (r) => {
    if (r && r.ok) Object.assign(CFG, r.data);
  });

  // ── Panel ────────────────────────────────────────────────
  const CSS = `
  #gc-root{position:fixed;inset:auto auto 20px 20px;z-index:2147483647;width:330px;
    font:13px/1.4 ui-sans-serif,-apple-system,"Segoe UI",sans-serif;color:#e8eaf0;
    background:linear-gradient(170deg,rgba(17,19,28,.96),rgba(12,13,20,.97));
    border:1px solid rgba(255,255,255,.09);border-radius:16px;
    box-shadow:0 20px 50px rgba(0,0,0,.55);backdrop-filter:blur(14px);
    overflow:hidden;user-select:none}
  #gc-root.gc-hidden{display:none}
  #gc-head{display:flex;align-items:center;gap:10px;padding:13px 15px 10px;cursor:move}
  #gc-flagdot{width:9px;height:9px;border-radius:50%;background:#6b7280;flex:none}
  #gc-country{font-size:19px;font-weight:650;letter-spacing:-.2px;flex:1;
    overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  #gc-conf{font-size:12px;font-variant-numeric:tabular-nums;font-weight:600}
  #gc-map{display:block;width:100%;height:150px;background:rgba(255,255,255,.02);
    border-top:1px solid rgba(255,255,255,.06);border-bottom:1px solid rgba(255,255,255,.06)}
  #gc-map path{stroke:rgba(255,255,255,.14);stroke-width:.8;vector-effect:non-scaling-stroke}
  #gc-map .gc-ctx{fill:rgba(255,255,255,.035);stroke:rgba(255,255,255,.07)}
  .gc-sec{padding:10px 15px}
  .gc-lbl{font-size:10px;letter-spacing:.09em;text-transform:uppercase;
    color:#79808f;margin-bottom:7px;font-weight:600}
  .gc-row{display:flex;align-items:center;gap:8px;margin:5px 0}
  .gc-nm{width:96px;font-size:12px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  .gc-track{flex:1;height:6px;background:rgba(255,255,255,.07);border-radius:3px;overflow:hidden}
  .gc-fill{height:100%;border-radius:3px;transition:width .25s ease}
  .gc-pc{width:40px;text-align:right;font-size:11px;color:#9aa1b0;font-variant-numeric:tabular-nums}
  #gc-cues{border-top:1px solid rgba(255,255,255,.06)}
  .gc-cue{display:flex;gap:8px;margin:6px 0;font-size:11.5px;color:#c3c8d4;line-height:1.35}
  .gc-cuetag{flex:none;font-size:9px;letter-spacing:.05em;text-transform:uppercase;
    color:#8b93a4;background:rgba(255,255,255,.06);padding:2px 6px;border-radius:5px;
    height:fit-content;margin-top:1px}
  #gc-foot{display:flex;align-items:center;justify-content:space-between;gap:8px;
    padding:9px 15px 12px;border-top:1px solid rgba(255,255,255,.06);
    font-size:11px;color:#79808f}
  #gc-foot button{background:rgba(255,255,255,.08);color:#e8eaf0;border:0;
    border-radius:7px;padding:5px 11px;font-size:11px;font-weight:550;cursor:pointer}
  #gc-foot button:hover{background:rgba(255,255,255,.14)}
  #gc-hint{font-size:10.5px;color:#6b7280}`;

  function colourFor(p) {
    if (p >= 0.70) return '#34d399';
    if (p >= 0.40) return '#fbbf24';
    return '#f87171';
  }

  function build() {
    const root = document.createElement('div');
    root.id = 'gc-root';
    root.className = 'gc-hidden';
    const style = document.createElement('style');
    style.textContent = CSS;
    root.appendChild(style);

    root.insertAdjacentHTML('beforeend', `
      <div id="gc-head">
        <span id="gc-flagdot"></span>
        <span id="gc-country">No panorama yet</span>
        <span id="gc-conf"></span>
      </div>
      <svg id="gc-map" viewBox="0 0 1000 1000" preserveAspectRatio="xMidYMid meet"></svg>
      <div class="gc-sec" id="gc-list"><div class="gc-lbl">Most likely</div></div>
      <div class="gc-sec" id="gc-cues"></div>
      <div id="gc-foot">
        <span id="gc-status">connecting…</span>
        <span style="display:flex;gap:6px;align-items:center">
          <span id="gc-hint"></span>
          <button id="gc-reset">New round</button>
        </span>
      </div>`);
    document.documentElement.appendChild(root);

    ui = {
      root,
      dot: root.querySelector('#gc-flagdot'),
      country: root.querySelector('#gc-country'),
      conf: root.querySelector('#gc-conf'),
      map: root.querySelector('#gc-map'),
      list: root.querySelector('#gc-list'),
      cues: root.querySelector('#gc-cues'),
      status: root.querySelector('#gc-status'),
      hint: root.querySelector('#gc-hint'),
    };
    ui.hint.textContent = `${CFG.hotkey.toUpperCase()} to hide`;
    root.querySelector('#gc-reset').onclick = reset;
    drawMap({});
    makeDraggable(root, root.querySelector('#gc-head'));
    checkHealth();
  }

  function makeDraggable(root, handle) {
    let dx = 0, dy = 0, on = false;
    handle.addEventListener('mousedown', (e) => {
      on = true;
      const r = root.getBoundingClientRect();
      dx = e.clientX - r.left; dy = e.clientY - r.top;
      root.style.inset = 'auto';
      root.style.left = r.left + 'px'; root.style.top = r.top + 'px';
      e.preventDefault();
    });
    addEventListener('mousemove', (e) => {
      if (!on) return;
      root.style.left = (e.clientX - dx) + 'px';
      root.style.top = (e.clientY - dy) + 'px';
    });
    addEventListener('mouseup', () => { on = false; });
  }

  // ── Map ──────────────────────────────────────────────────
  // One map per region (map_paths.js, generated by make_maps.py). The panel
  // shows the region of the current leader: a South American guess draws
  // South America. Countries outside the model are drawn faintly for context.
  function drawMap(probs) {
    const entries = Object.entries(probs);
    const max = Math.max(...entries.map(e => e[1]), 0.0001);
    const lead = entries.length ? entries.reduce((a, b) => (b[1] > a[1] ? b : a))[0] : null;
    const key = (lead && MAP_REGION_OF[lead]) || 'world';
    const R = MAP_REGIONS[key];
    ui.map.setAttribute('viewBox', R.view);
    ui.map.setAttribute('aria-label', `Map: ${R.label}`);

    const parts = [];
    if (R.context) parts.push(`<path class="gc-ctx" d="${R.context}"></path>`);
    for (const [name, d] of Object.entries(R.paths)) {
      const p = probs[name] || 0;
      const t = p / max;                       // relative to the leader
      const fill = p > 0
        ? `rgba(${Math.round(52 + 200 * t)},${Math.round(211 - 60 * t)},${Math.round(153 - 40 * t)},${0.18 + 0.72 * t})`
        : 'rgba(255,255,255,0.05)';
      parts.push(`<path d="${d}" fill="${fill}" fill-rule="evenodd"></path>`);
    }
    // places too small to see at this scale: a ring when strong, otherwise a
    // faint dot if this is their home region. R.px is view units per screen
    // pixel, so sizes hold across regions.
    const u = R.px;
    for (const [name, [x, y]] of Object.entries(R.dots)) {
      const t = (probs[name] || 0) / max;
      if (t >= 0.45) {
        parts.push(`<circle cx="${x}" cy="${y}" r="${4.5 * u}" fill="none" stroke="#34d399" stroke-width="${1.6 * u}"></circle>`);
      } else if (MAP_REGION_OF[name] === key) {
        parts.push(`<circle cx="${x}" cy="${y}" r="${1.3 * u}" fill="rgba(255,255,255,.3)"></circle>`);
      }
    }
    ui.map.innerHTML = parts.join('');
  }

  // ── Rendering ────────────────────────────────────────────
  function render() {
    if (!ui) return;
    if (blocked) {
      ui.country.textContent = 'Multiplayer';
      ui.conf.textContent = '';
      ui.dot.style.background = '#f87171';
      ui.list.innerHTML = '<div class="gc-lbl">Disabled</div>'
        + '<div class="gc-cue"><span>This is a game against other players, '
        + 'so the assistant is switched off. It works in solo and practice '
        + 'rounds.</span></div>';
      ui.cues.innerHTML = '';
      drawMap({});
      ui.status.textContent = 'solo play only';
      return;
    }
    if (!panoCount) {
      ui.country.textContent = 'No panorama yet';
      ui.conf.textContent = '';
      return;
    }
    const ranked = [...sums.entries()]
      .map(([c, s]) => [c, s / panoCount])
      .sort((a, b) => b[1] - a[1]);
    const top = ranked.slice(0, 5);
    const [best, p] = top[0];
    const col = colourFor(p);

    ui.country.textContent = best;
    ui.conf.textContent = `${(p * 100).toFixed(0)}%`;
    ui.conf.style.color = col;
    ui.dot.style.background = col;

    ui.list.innerHTML = '<div class="gc-lbl">Most likely</div>' + top.map(([c, v]) => `
      <div class="gc-row">
        <span class="gc-nm">${esc(c)}</span>
        <span class="gc-track"><span class="gc-fill" style="width:${(v * 100).toFixed(1)}%;
          background:${c === best ? col : 'rgba(255,255,255,.26)'}"></span></span>
        <span class="gc-pc">${(v * 100).toFixed(1)}%</span>
      </div>`).join('');

    drawMap(Object.fromEntries(ranked));

    if (lastCues.length) {
      const title = cueMode === 'scored'
        ? 'Why — strongest visual evidence'
        : 'Typical clues for this country';
      ui.cues.innerHTML = `<div class="gc-lbl">${title}</div>` + lastCues.map(c => `
        <div class="gc-cue"><span class="gc-cuetag">${esc(c.cue)}</span>
          <span>${esc(c.text)}</span></div>`).join('');
    } else {
      ui.cues.innerHTML = '';
    }
    ui.status.textContent = `${panoCount} panorama${panoCount === 1 ? '' : 's'}`;
  }

  const esc = (s) => String(s).replace(/[&<>"]/g,
    m => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[m]));

  function reset() {
    sums = new Map(); panoCount = 0; lastCues = []; seen.clear();
    if (ui) { ui.cues.innerHTML = ''; ui.list.innerHTML = '<div class="gc-lbl">Most likely</div>'; drawMap({}); }
    render();
    if (ui) ui.status.textContent = 'reset — move to load a panorama';
  }

  // ── Model ────────────────────────────────────────────────
  function checkHealth() {
    chrome.runtime.sendMessage({ type: 'health' }, (r) => {
      if (!ui) return;
      if (r && r.ok) {
        cueMode = r.data.cue_mode || 'none';
        ui.status.textContent = `${r.data.backend} · ${r.data.countries} countries`;
      } else {
        ui.status.textContent = (r && r.error) || 'model failed to load';
      }
    });
  }

  function analyse(panoId) {
    if (blocked) { if (ui) ui.status.textContent = 'disabled in multiplayer'; return; }
    if (busy || !panoId) return;
    busy = true;
    if (ui) ui.status.textContent = 'analysing…';
    chrome.runtime.sendMessage({ type: 'predict', panoId }, (r) => {
      busy = false;
      if (!r || !r.ok) {
        if (ui) ui.status.textContent = (r && r.error) || 'model unavailable';
        return;
      }
      const d = r.data;
      if (d.error) { if (ui) ui.status.textContent = d.error; return; }
      panoCount++;
      for (const [c, p] of d.top) sums.set(c, (sums.get(c) || 0) + p);
      lastCues = d.cues || [];
      cueMode = d.cue_mode || cueMode;
      render();
    });
  }

  // ── Rounds ───────────────────────────────────────────────
  // Evidence is pooled over every panorama of a round, so it has to be
  // cleared when the next round starts. Signals, any one of which is enough:
  //   - OpenGuessr / WorldGuessr: each round loads a fresh Street View embed,
  //     and embed_bridge.js marks the first panorama of each embed as fresh
  //   - GeoGuessr: the round-result screen appears (the round is over, so
  //     the next panorama is a new round); the round counter changing is a
  //     backup. Selectors follow GeoGuessr's markup and may need updating.
  //   - any site: the page path changes (a new game)
  // The "New round" button stays as a manual override.
  let latestAt = 0;            // when latestPano was first seen
  let awaitingRound = false;   // a round started; analyse its first panorama

  function newRound(why, nextOnly = false) {
    sums = new Map(); panoCount = 0; lastCues = []; seen.clear();
    // The signal can land just before or just after the round's first
    // panorama. If one arrived a moment ago it belongs to the new round --
    // unless the signal is "the round just ended", where it cannot.
    const fresh = !nextOnly && latestPano && Date.now() - latestAt < 3000;
    if (!fresh) latestPano = null;
    awaitingRound = !fresh;
    if (ui) {
      ui.cues.innerHTML = '';
      ui.list.innerHTML = '<div class="gc-lbl">Most likely</div>';
      drawMap({});
      render();
      ui.status.textContent = `new round (${why})`;
    }
    if (fresh) { seen.add(latestPano); startRound(latestPano); }
  }

  function startRound(id) {
    awaitingRound = false;
    if (blocked) return;
    if (visible) { seen.add(id + ':done'); analyse(id); }
    else if (CFG.autoShow) { show(true); seen.add(id + ':done'); analyse(id); }
  }

  const RESULT_SCREEN = '[data-qa="round-result"], [class*="result-layout_root__"], ' +
                        '[class*="round-score_container__"]';
  let lastPath = location.pathname;
  let lastRoundText = null;
  let resultShown = false;
  function watchRounds() {
    setInterval(() => {
      if (location.pathname !== lastPath) {
        lastPath = location.pathname;
        lastRoundText = null;
        if (panoCount || latestPano) newRound('new game');
        return;
      }
      const result = !!document.querySelector(RESULT_SCREEN);
      if (result && !resultShown && (panoCount || latestPano)) newRound('round over', true);
      resultShown = result;
      if (result) return;
      // GeoGuessr's status bar: "1 / 5", "2 / 5", ...
      const el = document.querySelector('[data-qa="round-number"]');
      const t = el ? el.textContent.replace(/\s+/g, ' ').trim() : null;
      if (t && lastRoundText && t !== lastRoundText) newRound(`round ${t}`);
      if (t) lastRoundText = t;
    }, 700);
  }

  // ── Panorama id sniffing ─────────────────────────────────
  const PANO_RE = /[?&]panoid=([A-Za-z0-9_\-]+)/;

  function notePano(id) {
    if (!id || seen.has(id)) { latestPano = id || latestPano; return; }
    seen.add(id);
    latestPano = id;
    latestAt = Date.now();
    if (blocked) return;
    if (awaitingRound) { startRound(id); return; }
    if (CFG.autoShow) { show(true); analyse(id); }
  }

  // Panoramas from a Street View embed iframe, relayed by the background.
  chrome.runtime.onMessage.addListener((msg) => {
    if (!msg || msg.type !== 'embedPano' || !msg.panoId) return;
    // the panorama in this message is the new round's first, so nothing
    // seen before it can be
    if (msg.fresh && (panoCount || latestPano)) newRound('new panorama', true);
    notePano(msg.panoId);
  });

  function watch() {
    try {
      new PerformanceObserver((list) => {
        for (const e of list.getEntries()) {
          const m = PANO_RE.exec(e.name);
          if (m) notePano(m[1]);
        }
      }).observe({ entryTypes: ['resource'] });
    } catch (_) { /* ignore */ }

    const of = window.fetch;
    if (of) window.fetch = function (...a) {
      try {
        const u = typeof a[0] === 'string' ? a[0] : a[0] && a[0].url;
        const m = u && PANO_RE.exec(u);
        if (m) notePano(m[1]);
      } catch (_) { /* ignore */ }
      return of.apply(this, a);
    };
  }

  // ── Hotkey ───────────────────────────────────────────────
  function show(v) {
    visible = v;
    if (!ui) build();
    ui.root.classList.toggle('gc-hidden', !visible);
  }

  addEventListener('keydown', (e) => {
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    const t = e.target;
    if (t && (/^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName) || t.isContentEditable)) return;
    if (e.key.toLowerCase() !== (CFG.hotkey || 'g').toLowerCase()) return;
    e.preventDefault();
    refreshMode();
    show(!visible);
    if (visible && blocked) { render(); return; }
    if (visible) {
      if (!ui.status.textContent || /offline|connecting/.test(ui.status.textContent)) checkHealth();
      if (latestPano && !seen.has(latestPano + ':done')) {
        seen.add(latestPano + ':done');
        analyse(latestPano);
      } else if (latestPano && panoCount === 0) {
        analyse(latestPano);
      }
    }
  }, true);

  watch();
  watchNavigation();
  if (window.top === window) watchRounds();
})();
