#!/usr/bin/env bash
# Builds the Chrome Web Store upload package.
# Ships only what the extension loads at runtime: no README, no build
# scripts, no source maps.
set -euo pipefail
cd "$(dirname "$0")"

# The model and the WASM runtime are too large for git, so a fresh clone
# has to supply them:
#   model/visual.fp16.onnx, model/head.onnx  ->  the fine-tuned 3.0 model, produced
#       by the training pipeline (kept out of this repository with its data)
#   model/cues.f32 + cue index in model_meta.json  ->  python3 ../make_cues.py
#   map_paths.js  ->  python3 ../make_maps.py --ne ne_50m_admin_0_countries.geojson
#       (re-run whenever the class list changes)
#   vendor/* ->  npm pack onnxruntime-web@1.20.1, then copy from dist/
for f in model/visual.fp16.onnx model/head.onnx model/model_meta.json model/cues.f32 map_paths.js; do
  [ -f "$f" ] || { echo "missing $f — see the notes at the top of build.sh" >&2; exit 1; }
done
for f in vendor/ort.webgpu.min.js vendor/ort-wasm-simd-threaded.jsep.wasm; do
  [ -f "$f" ] || { echo "missing $f — copy it from onnxruntime-web@1.20.1/dist/" >&2; exit 1; }
done

VER=$(python3 -c "import json;print(json.load(open('manifest.json'))['version'])")
OUT="geoguessr-assistant-${VER}.zip"
rm -f "$OUT"

zip -r -X "$OUT" \
  manifest.json background.js content.js embed_bridge.js geoclip_core.js map_paths.js \
  offscreen.html offscreen.js popup.html popup.js \
  icons model vendor \
  -x '.*' -x '__MACOSX/*' -x '*.map' -x 'model/_*' >/dev/null

echo "$OUT  ($(du -h "$OUT" | cut -f1))"
unzip -l "$OUT" | tail -5
