# GeoGuessr Assistant

A Chrome extension that predicts which country a Street View panorama is in,
with an on-device model, and shows why.

Press **G** in a single-player round and a panel shows:

- **the five most likely countries**, out of 119, with confidence that is
  calibrated: when it says 90% or more it is right about 98% of the time;
- **a map of the region** the leading guess is in (Europe, North America,
  Central America & Caribbean, South America, Africa, Middle East, Asia,
  Oceania);
- **the reasons**: the cues for the leading country that best match the view
  (road lines, bollards, signs, architecture, vegetation…).

Evidence pools across every panorama you visit in a round, and the panel
clears itself when the next round starts.

It predicts from pixels. It does not read the game's answer, place pins or
submit guesses, and it switches itself off in multiplayer modes.

Works on [geoguessr.com](https://www.geoguessr.com),
[openguessr.com](https://openguessr.com) and
[worldguessr.com](https://www.worldguessr.com).

## How it works

1. **Find the panorama.** Every Street View tile the page loads carries the
   panorama id in its URL; the content script reads it from the page's own
   resource loads. OpenGuessr and WorldGuessr show Street View inside a Google
   Maps embed, so a small script in those embed frames does the same there.
2. **Fetch clean imagery.** The extension downloads that panorama's tiles
   directly (no screenshots, so the game's interface never reaches the model)
   and reprojects them into four views at 90° apart.
3. **Classify.** A CLIP ViT-B/16 image encoder, with its top eight transformer
   blocks fine-tuned on Street View, embeds each view and its mirror image. A
   head scores 576 sub-country regions, which are summed to 119 countries, and
   the four views are averaged.
4. **Explain.** Each country has 5–7 short GeoTips cues, embedded once with
   CLIP's text encoder; the panel shows the ones closest to the image.

Everything after the tile download runs locally on WebGPU (WASM as a
fallback). See [PRIVACY.md](PRIVACY.md).

### Accuracy

On 9,803 held-out locations in areas the model never trained on:

| | |
|---|---|
| Right first time | 80.9% |
| Right within the top 5 | 96.2% |
| Average across countries | 83.8% |
| Calibration error (ECE) | 0.069 |

Weakest on look-alike neighbours: Serbia, Bosnia and Herzegovina, Poland and
Czechia sit around 40–47%.

## Repository

| Path | What it is |
|---|---|
| `extension/` | The extension itself: manifest, content and embed scripts, offscreen inference, panel, packaging script |
| `extension/STORE_SUBMISSION.md` | Chrome Web Store listing copy, permission justifications and verification notes |
| `geotips_prompts.py` | The cue captions for every country |
| `make_cues.py` | Embeds the cues into `extension/model/cues.f32` |
| `make_maps.py` | Builds the region maps (`extension/map_paths.js`) from Natural Earth |
| `icon_src/` | Source artwork and script for the icons |
| `PRIVACY.md` | Privacy policy |

The model weights (`extension/model/*.onnx`), the cue matrix and the WASM
runtime are too large for git and are not in the repository; the training
data and pipeline are not published either. `extension/build.sh` lists
what a build needs.

## Running from source

1. Put the model files in `extension/model/` and the onnxruntime-web
   1.20.1 runtime in `extension/vendor/` (see `extension/build.sh`).
2. Open `chrome://extensions`, turn on **Developer mode**, click **Load
   unpacked** and choose the `extension/` folder.
3. Start a single-player round on a supported site and press **G**.

`extension/build.sh` produces the Web Store package.

Using any assistance tool may breach the rules of the site you play on.
That is between you and them, so read them.
