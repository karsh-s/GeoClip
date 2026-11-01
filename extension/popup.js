const DEFAULTS = { hotkey: 'g', autoShow: false };
const $ = (id) => document.getElementById(id);

function setStatus(text, cls) {
  const el = $('status');
  el.textContent = text;
  el.className = cls || '';
}

function ping() {
  setStatus('checking…');
  chrome.runtime.sendMessage({ type: 'health' }, (r) => {
    if (r && r.ok) {
      const d = r.data;
      const cue = d.cue_mode === 'scored' ? 'evidence scored per image'
        : d.cue_mode === 'typical' ? 'typical clues only' : 'no clues';
      setStatus(`${d.backend} · ${d.countries} countries · ${cue}`, 'ok');
    } else {
      setStatus((r && r.error) || 'model failed to load', 'bad');
    }
  });
}

chrome.storage.sync.get(DEFAULTS, (s) => {
  $('hotkey').value = s.hotkey;
  $('autoShow').checked = !!s.autoShow;
  ping();
});

$('save').onclick = () => {
  chrome.storage.sync.set({
    hotkey: ($('hotkey').value || 'g').trim().toLowerCase(),
    autoShow: $('autoShow').checked,
  }, () => {
    setStatus('saved — reload the game tab', 'ok');
    setTimeout(ping, 900);
  });
};
