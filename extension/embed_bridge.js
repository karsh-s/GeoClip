/*
 * GeoGuessr Assistant — embed bridge.
 *
 * OpenGuessr and WorldGuessr show Street View inside a Google Maps embed
 * iframe (www.google.com/maps/embed/v1/streetview). The image tiles are
 * requested from inside that iframe, so the content script on the game's
 * own page never sees them. This script runs only in those embed frames,
 * reads the panorama id out of the tile URLs -- exactly what content.js
 * does on GeoGuessr -- and passes it to the panel on the game page.
 *
 * It reads nothing else. In particular it never looks at the iframe's own
 * URL, which on these sites carries the round's coordinates: the extension
 * predicts from pixels and does not read the game's answer.
 */
(function () {
  'use strict';

  // Only inside the supported games; every other site embedding a
  // Google map is left alone. ancestorOrigins lists the frames above us,
  // the last entry being the top-level page.
  const GAMES = /^https:\/\/(www\.)?(geoguessr|openguessr|worldguessr)\.com$/;
  const anc = location.ancestorOrigins;
  if (!anc || !anc.length || !GAMES.test(anc[anc.length - 1])) return;

  const PANO_RE = /[?&]panoid=([A-Za-z0-9_\-]+)/;
  const seen = new Set();

  function found(id) {
    if (seen.has(id)) return;
    // The first panorama this document loads is the start of a round: the
    // game sets a fresh iframe for each one. Moving within the round loads
    // later panoramas into the same document.
    const fresh = seen.size === 0;
    seen.add(id);
    try {
      chrome.runtime.sendMessage({ type: 'embedPano', panoId: id, fresh });
    } catch (_) { /* extension reloaded underneath us */ }
  }

  try {
    new PerformanceObserver((list) => {
      for (const e of list.getEntries()) {
        const m = PANO_RE.exec(e.name);
        if (m) found(m[1]);
      }
    }).observe({ type: 'resource', buffered: true });
  } catch (_) { /* ignore */ }
})();
