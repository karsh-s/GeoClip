#!/usr/bin/env bash
# Builds the Chrome Web Store upload package.
# Ships only what the extension loads at runtime: no README, no build
# scripts, no source maps.
set -euo pipefail
cd "$(dirname "$0")"

for f in model/visual.fp16.onnx model/head.onnx model/model_meta.json \
         vendor/ort.webgpu.min.js vendor/ort-wasm-simd-threaded.jsep.wasm; do
  [ -f "$f" ] || { echo "missing $f — run 'python3 ../export_web.py' first" >&2; exit 1; }
done

VER=$(python3 -c "import json;print(json.load(open('manifest.json'))['version'])")
OUT="geoclip-assistant-${VER}.zip"
rm -f "$OUT"

zip -r -X "$OUT" \
  manifest.json background.js content.js geoclip_core.js europe_paths.js \
  offscreen.html offscreen.js popup.html popup.js \
  icons model vendor \
  -x '.*' -x '__MACOSX/*' -x '*.map' -x 'model/_*' >/dev/null

echo "$OUT  ($(du -h "$OUT" | cut -f1))"
unzip -l "$OUT" | tail -5
