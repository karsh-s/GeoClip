// Core image pipeline, ported from geoguessr_server.py.
//
// Pure functions over typed arrays -- no DOM, no canvas -- so the same code
// runs in the offscreen document and under node, where it is checked against
// the Python original. Every constant here must match model_meta.json.

// ---- PIL-compatible bicubic resampling --------------------------------
//
// Pillow does NOT do a plain 4x4 bicubic when downscaling: it widens the
// filter support by the reduction factor, so 320->224 samples a ~5.7px
// window, not 4px. Skipping that antialiasing feeds the model visibly
// different pixels from the ones it trained on, so this reproduces
// Pillow's ImagingResample exactly (float throughout; Pillow quantises to
// uint8 between passes, which is the one remaining difference).

const BICUBIC_SUPPORT = 2.0;

function bicubicKernel(x) {
  const a = -0.5;                       // Pillow's hardcoded 'a'
  if (x < 0) x = -x;
  if (x < 1.0) return ((a + 2.0) * x - (a + 3.0)) * x * x + 1.0;
  if (x < 2.0) return (((x - 5.0) * x + 8.0) * x - 4.0) * a;
  return 0.0;
}

/** Per-output-pixel filter taps, following Pillow's precompute_coeffs. */
function precomputeCoeffs(inSize, outSize) {
  const scale = inSize / outSize;
  const filterscale = Math.max(1.0, scale);
  const support = BICUBIC_SUPPORT * filterscale;
  const invScale = 1.0 / filterscale;

  const bounds = new Int32Array(outSize * 2);
  const kk = [];
  for (let xx = 0; xx < outSize; xx++) {
    const center = (xx + 0.5) * scale;
    let xmin = Math.floor(center - support + 0.5);
    if (xmin < 0) xmin = 0;
    let xmax = Math.floor(center + support + 0.5);
    if (xmax > inSize) xmax = inSize;

    const n = xmax - xmin;
    const k = new Float64Array(n);
    let ww = 0.0;
    for (let x = 0; x < n; x++) {
      const w = bicubicKernel((x + xmin - center + 0.5) * invScale);
      k[x] = w;
      ww += w;
    }
    if (ww !== 0.0) for (let x = 0; x < n; x++) k[x] /= ww;
    bounds[xx * 2] = xmin;
    bounds[xx * 2 + 1] = n;
    kk.push(k);
  }
  return { bounds, kk };
}

/**
 * Resize interleaved RGB. src is Float32Array|Uint8ClampedArray of
 * sw*sh*3; returns Float32Array of dw*dh*3. Horizontal pass then
 * vertical, as Pillow does.
 */
export function resizeBicubicRGB(src, sw, sh, dw, dh) {
  const h = precomputeCoeffs(sw, dw);
  const tmp = new Float32Array(dw * sh * 3);
  for (let y = 0; y < sh; y++) {
    const rowOff = y * sw * 3;
    for (let x = 0; x < dw; x++) {
      const xmin = h.bounds[x * 2], n = h.bounds[x * 2 + 1], k = h.kk[x];
      let r = 0, g = 0, b = 0;
      for (let i = 0; i < n; i++) {
        const o = rowOff + (xmin + i) * 3, w = k[i];
        r += src[o] * w; g += src[o + 1] * w; b += src[o + 2] * w;
      }
      const o = (y * dw + x) * 3;
      tmp[o] = r; tmp[o + 1] = g; tmp[o + 2] = b;
    }
  }

  const v = precomputeCoeffs(sh, dh);
  const dst = new Float32Array(dw * dh * 3);
  for (let y = 0; y < dh; y++) {
    const ymin = v.bounds[y * 2], n = v.bounds[y * 2 + 1], k = v.kk[y];
    for (let x = 0; x < dw; x++) {
      let r = 0, g = 0, b = 0;
      for (let i = 0; i < n; i++) {
        const o = ((ymin + i) * dw + x) * 3, w = k[i];
        r += tmp[o] * w; g += tmp[o + 1] * w; b += tmp[o + 2] * w;
      }
      const o = (y * dw + x) * 3;
      dst[o] = r; dst[o + 1] = g; dst[o + 2] = b;
    }
  }
  return dst;
}

// ---- Equirectangular -> rectilinear -----------------------------------
//
// Cropping the panorama directly leaves heavy barrel distortion, which is
// nothing like the photos the model trained on. One ray per output pixel,
// sampled nearest-neighbour -- matching the Python, which indexes with
// .astype(np.int32) rather than interpolating.

export function equirectToPerspective(src, W, H, opts = {}) {
  const { yawDeg = 0, pitchDeg = -5.0, fovDeg = 90.0, out = 320 } = opts;
  const dst = new Float32Array(out * out * 3);
  const f = 0.5 * out / Math.tan((fovDeg * Math.PI / 180) / 2);

  const p = pitchDeg * Math.PI / 180, yw = yawDeg * Math.PI / 180;
  const cp = Math.cos(p), sp = Math.sin(p);
  const cy = Math.cos(yw), sy = Math.sin(yw);
  const TWO_PI = Math.PI * 2;

  for (let i = 0; i < out; i++) {
    const y = i - out / 2;
    for (let j = 0; j < out; j++) {
      const x = j - out / 2;

      const y2 = y * cp - f * sp;          // pitch about X
      const z2 = y * sp + f * cp;
      const x3 = x * cy + z2 * sy;         // yaw about Y
      const z3 = -x * sy + z2 * cy;

      const r = Math.sqrt(x3 * x3 + y2 * y2 + z3 * z3);
      const lon = Math.atan2(x3, z3);
      let s = y2 / r;
      if (s < -1) s = -1; else if (s > 1) s = 1;
      const lat = Math.asin(s);

      let u = ((lon / TWO_PI) + 0.5) * W | 0;
      let v = ((lat / Math.PI) + 0.5) * H | 0;
      if (u < 0) u = 0; else if (u > W - 1) u = W - 1;
      if (v < 0) v = 0; else if (v > H - 1) v = H - 1;

      const so = (v * W + u) * 3, dof = (i * out + j) * 3;
      dst[dof] = src[so]; dst[dof + 1] = src[so + 1]; dst[dof + 2] = src[so + 2];
    }
  }
  return dst;
}

// ---- Tensor preparation -----------------------------------------------

/**
 * Interleaved RGB in 0..255 -> planar CHW, scaled to 0..1 and normalised.
 * `mirror` reproduces the server's horizontal-flip TTA.
 */
export function toCHW(rgb, size, mean, std, mirror = false) {
  const out = new Float32Array(3 * size * size);
  const plane = size * size;
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const sx = mirror ? size - 1 - x : x;
      const s = (y * size + sx) * 3, d = y * size + x;
      out[d] = (rgb[s] / 255 - mean[0]) / std[0];
      out[plane + d] = (rgb[s + 1] / 255 - mean[1]) / std[1];
      out[2 * plane + d] = (rgb[s + 2] / 255 - mean[2]) / std[2];
    }
  }
  return out;
}

/** L2-normalise each row of an n x dim matrix, in place. */
export function l2NormalizeRows(a, n, dim) {
  for (let i = 0; i < n; i++) {
    let ss = 0;
    for (let k = 0; k < dim; k++) { const v = a[i * dim + k]; ss += v * v; }
    const inv = 1 / Math.max(Math.sqrt(ss), 1e-12);
    for (let k = 0; k < dim; k++) a[i * dim + k] *= inv;
  }
  return a;
}

export function softmax(logits, n, k) {
  const out = new Float32Array(n * k);
  for (let i = 0; i < n; i++) {
    let m = -Infinity;
    for (let j = 0; j < k; j++) m = Math.max(m, logits[i * k + j]);
    let s = 0;
    for (let j = 0; j < k; j++) { const e = Math.exp(logits[i * k + j] - m); out[i * k + j] = e; s += e; }
    for (let j = 0; j < k; j++) out[i * k + j] /= s;
  }
  return out;
}
