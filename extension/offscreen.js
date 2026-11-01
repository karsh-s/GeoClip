// The model lives here.
//
// WebGPU is not reachable from an MV3 service worker, and WASM is ~6x
// slower (measured: 1.1s vs 7.1s for one guess), so inference runs in this
// offscreen document and background.js forwards requests to it.
//
// The pipeline mirrors geoguessr_server.py exactly:
//   tiles -> 2048x1024 equirectangular -> 4 rectilinear headings
//   -> each heading and its mirror through the visual tower
//   -> average the pair, renormalise, apply the head
//   -> average the per-view probabilities

import {
  equirectToPerspective, resizeBicubicRGB, toCHW,
  l2NormalizeRows, softmax,
} from './geoclip_core.js';

const url = (p) => chrome.runtime.getURL(p);

let META = null, VISUAL = null, HEAD = null, CUES = null, BACKEND = null;
let ready = null;
const cache = new Map();           // panoramas are immutable, so results are too

// ---- setup -------------------------------------------------------------

async function init() {
  META = await (await fetch(url('model/model_meta.json'))).json();

  ort.env.wasm.wasmPaths = url('vendor/');
  ort.env.logLevel = 'error';

  // onnxruntime's native logger is separate from ort-web's, and its warnings
  // go to stderr, which Chrome surfaces as extension errors. The one it always
  // emits here is VerifyEachNodeIsAssignedToAnEp -- some ops have no WebGPU
  // kernel and fall back to CPU, which is expected. Hence logSeverityLevel 3
  // on each session below: errors still surface, routine warnings do not.

  const visualBytes = new Uint8Array(
    await (await fetch(url('model/' + META.visual))).arrayBuffer());
  const headBytes = new Uint8Array(
    await (await fetch(url('model/' + META.head))).arrayBuffer());

  // WebGPU where available, WASM otherwise. Both were measured at >=98%
  // top-1 agreement with the fp32 reference; WASM is exact but slow.
  const eps = navigator.gpu ? ['webgpu', 'wasm'] : ['wasm'];
  for (const ep of eps) {
    try {
      VISUAL = await ort.InferenceSession.create(visualBytes, {
        executionProviders: [ep], logSeverityLevel: 3,
      });
      BACKEND = ep;
      break;
    } catch (e) {
      console.warn(`[GeoCLIP] ${ep} unavailable:`, e);
    }
  }
  if (!VISUAL) throw new Error('no usable backend for the visual model');
  HEAD = await ort.InferenceSession.create(headBytes, {
    executionProviders: ['wasm'], logSeverityLevel: 3,
  });

  if (META.cue_mode === 'scored' && META.cues && Object.keys(META.cues).length) {
    const buf = await (await fetch(url('model/cues.f32'))).arrayBuffer();
    CUES = new Float32Array(buf);
  }
  console.log(`[GeoCLIP] ready — ${BACKEND}, ${META.classes.length} countries, cues ${META.cue_mode}`);
  return { backend: BACKEND, countries: META.classes.length, cue_mode: META.cue_mode };
}

function ensure() {
  if (!ready) ready = init();
  return ready;
}

// ---- panorama fetch ----------------------------------------------------

const TILE_URL = (pid, x, y, z) =>
  'https://streetviewpixels-pa.googleapis.com/v1/tile' +
  `?cb_client=maps_sv.tactile&panoid=${encodeURIComponent(pid)}&x=${x}&y=${y}&zoom=${z}`;

/**
 * Stitch the equirectangular panorama. Returns interleaved RGB floats
 * (0..255) plus its dimensions, or null if no tile could be fetched.
 */
async function fetchPanorama(panoId) {
  const z = META.pano_zoom, T = META.tile_px;
  const nx = 2 ** z, ny = 2 ** (z - 1);
  const W = nx * T, H = ny * T;

  const canvas = new OffscreenCanvas(W, H);
  const ctx = canvas.getContext('2d', { willReadFrequently: true });

  const jobs = [];
  for (let x = 0; x < nx; x++) {
    for (let y = 0; y < ny; y++) {
      jobs.push((async () => {
        try {
          const r = await fetch(TILE_URL(panoId, x, y, z), { credentials: 'omit' });
          if (!r.ok) return { ok: false, status: r.status };
          const bmp = await createImageBitmap(await r.blob());
          ctx.drawImage(bmp, x * T, y * T);
          bmp.close();
          return { ok: true };
        } catch (e) {
          return { ok: false, status: String(e).slice(0, 60) };
        }
      })());
    }
  }
  const res = await Promise.all(jobs);
  const got = res.filter((r) => r.ok).length;
  if (got === 0) {
    const why = res.find((r) => !r.ok);
    throw new Error(`could not fetch any tile (${why ? why.status : 'unknown'})`);
  }

  const { data } = ctx.getImageData(0, 0, W, H);      // RGBA
  const rgb = new Float32Array(W * H * 3);
  for (let i = 0, j = 0; i < data.length; i += 4, j += 3) {
    rgb[j] = data[i]; rgb[j + 1] = data[i + 1]; rgb[j + 2] = data[i + 2];
  }
  return { rgb, W, H, tiles: `${got}/${jobs.length}` };
}

// ---- inference ---------------------------------------------------------

async function predict(panoId) {
  await ensure();
  if (cache.has(panoId)) return cache.get(panoId);

  const t0 = performance.now();
  const pano = await fetchPanorama(panoId);

  const N = META.n_headings, S = META.input_size, V = META.view_px;
  const dim = META.embed_dim, K = META.classes.length;

  // 4 headings x {image, mirror} = 2N tensors, batched in one run
  const batch = new Float32Array(2 * N * 3 * S * S);
  const stride = 3 * S * S;
  for (let i = 0; i < N; i++) {
    const view = equirectToPerspective(pano.rgb, pano.W, pano.H, {
      yawDeg: i * (360 / N), pitchDeg: META.view_pitch,
      fovDeg: META.view_fov, out: V,
    });
    const small = resizeBicubicRGB(view, V, V, S, S);
    batch.set(toCHW(small, S, META.mean, META.std, false), (2 * i) * stride);
    batch.set(toCHW(small, S, META.mean, META.std, true), (2 * i + 1) * stride);
  }

  const emb = await VISUAL.run({
    image: new ort.Tensor('float16', new Float16Array(batch), [2 * N, 3, S, S]),
  });
  const e = Float32Array.from(emb[VISUAL.outputNames[0]].data, Number);

  // pair each heading with its mirror, as the server does
  const merged = new Float32Array(N * dim);
  for (let i = 0; i < N; i++) {
    for (let k = 0; k < dim; k++) {
      merged[i * dim + k] = (e[(2 * i) * dim + k] + e[(2 * i + 1) * dim + k]) / 2;
    }
  }
  l2NormalizeRows(merged, N, dim);

  const out = await HEAD.run({
    embedding: new ort.Tensor('float32', merged, [N, dim]),
  });
  const logits = Float32Array.from(out[HEAD.outputNames[0]].data, Number);
  const probs = softmax(logits, N, K);

  // per-location score = mean over headings (the metric v7 reports)
  const avg = new Float32Array(K);
  for (let i = 0; i < N; i++) for (let k = 0; k < K; k++) avg[k] += probs[i * K + k] / N;

  const top = [...avg].map((p, k) => [META.classes[k], p])
    .sort((a, b) => b[1] - a[1]).slice(0, 5);

  const result = {
    pano_id: panoId,
    top,
    cues: cuesFor(top[0][0], merged, N, dim),
    cue_mode: META.cue_mode,
    backend: BACKEND,
    tiles: pano.tiles,
    ms: Math.round(performance.now() - t0),
  };
  cache.set(panoId, result);
  if (cache.size > 64) cache.delete(cache.keys().next().value);
  return result;
}

/** Which of the country's GeoTips cues this image actually supports. */
function cuesFor(country, merged, N, dim, topK = 3) {
  const entry = META.cues && META.cues[country];
  if (!entry) return [];
  if (META.cue_mode !== 'scored' || !CUES) {
    return entry.labels.slice(0, topK).map((cue, i) => ({ cue, text: entry.texts[i], score: null }));
  }

  const mean = new Float32Array(dim);
  for (let i = 0; i < N; i++) for (let k = 0; k < dim; k++) mean[k] += merged[i * dim + k] / N;
  l2NormalizeRows(mean, 1, dim);

  const sims = new Float32Array(entry.count);
  for (let c = 0; c < entry.count; c++) {
    let s = 0;
    const off = (entry.offset + c) * dim;
    for (let k = 0; k < dim; k++) s += mean[k] * CUES[off + k];
    sims[c] = s;
  }
  let lo = Infinity, hi = -Infinity;
  for (const s of sims) { lo = Math.min(lo, s); hi = Math.max(hi, s); }
  const rng = Math.max(hi - lo, 1e-6);

  return [...sims].map((s, i) => ({
    cue: entry.labels[i], text: entry.texts[i],
    score: Math.round(((s - lo) / rng) * 1000) / 1000,
  })).sort((a, b) => b.score - a.score).slice(0, topK);
}

// ---- message plumbing --------------------------------------------------

chrome.runtime.onMessage.addListener((msg, _sender, reply) => {
  if (!msg || msg.target !== 'offscreen') return;

  if (msg.type === 'health') {
    ensure().then((d) => reply({ ok: true, data: d }))
            .catch((e) => reply({ ok: false, error: String(e.message || e) }));
    return true;
  }
  if (msg.type === 'predict') {
    predict(msg.panoId).then((d) => reply({ ok: true, data: d }))
                       .catch((e) => reply({ ok: false, error: String(e.message || e) }));
    return true;
  }
});
