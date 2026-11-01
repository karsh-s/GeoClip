# Chrome Web Store submission — GeoCLIP Assistant

Everything below is copy-paste ready for
<https://chrome.google.com/webstore/devconsole>.
Build the upload with `./build.sh` → `geoclip-assistant-2.0.0.zip`.

---

## 1. Before you can submit

- **One-time US$5 registration fee**, paid in the Developer Dashboard. Not
  refundable, covers the account forever.
- **Publisher display name.** Set this under *Account → Publisher settings*
  before publishing. If you leave it blank, the listing shows the Google
  account name. Pick something you're willing to have attached to this
  publicly — it appears on the listing and cannot be hidden.
- **A verified contact email**, shown on the listing. Use one you don't mind
  being public.

---

## 2. Package

`geoclip-assistant-2.0.0.zip` — **160 MB** (196 MB unpacked), 24 files, no
remote code.

The bulk is the model (173 MB fp16) and onnxruntime-web's WASM runtime
(22 MB). Both ship inside the package and are never fetched at runtime,
which is what keeps this compliant with the remote-code policy. Uploading
160 MB over a slow link can time out; retry rather than re-cutting the zip.

---

## 3. Listing fields

**Name**
```
GeoCLIP Assistant
```

**Short description** (132 char limit; this is 118)
```
Predicts the country from Street View imagery with an on-device model, and shows the visual evidence behind the guess.
```

**Category:** Just for Fun
**Language:** English (United States)

**Detailed description**
```
GeoCLIP Assistant shows a country prediction for the Street View panorama
currently on screen, together with the visual cues the model used to reach it.

Everything runs on your own device. There is nothing to install beyond the
extension itself, no account, and no server.

HOW IT WORKS

The page loads Street View image tiles, and those tile URLs contain a
panorama identifier. The extension reads that identifier, downloads that
panorama's own tiles, stitches them into a full 360 view, reprojects it into
four compass-heading views, and runs a CLIP-based classifier trained on
polygon-verified Street View coverage across 41 European countries.

The result appears in a draggable panel: the top five countries with
confidence bars, a map highlighting the leading guess, and the visual cues --
road markings, bollards, licence plates, architecture, vegetation -- that
pushed the model toward it. Predictions accumulate across every panorama you
visit, so the estimate sharpens as you move.

PRIVACY

No analytics, no telemetry, no accounts, and no developer-operated server.
The model and its runtime are bundled in the extension; the classification
happens in your browser and the imagery is never uploaded anywhere. The only
network request the extension makes is for the panorama's own image tiles,
fetched from Google without credentials.

SOLO PLAY ONLY

The extension deliberately disables itself when the page URL indicates a
multiplayer mode -- duels, team duels, battle royale, parties, lobbies,
ranked and similar. In those modes the panel shows "solo play only" and no
prediction is made.

Using any assistance tool may still breach the terms of service of the site
you use it on, including in single-player. That is between you and that
site; please read their rules.

SIZE

The download is large (about 160 MB) because the neural network ships with
the extension rather than being fetched from a server. This is deliberate:
it is what allows the extension to work entirely offline and to send no
imagery anywhere.

SUPPORTED SITES

geoguessr.com, openguessr.com, worldguessr.com, freeguessr.com

OPEN SOURCE

https://github.com/karsh-s/geogussr-cheat
```

---

## 4. Privacy tab

**Single purpose description**
```
Display a country prediction, and the visual evidence behind it, for the
Street View panorama currently shown on a geography-guessing website.
```

**Permission justifications**

`storage`
```
Stores two user preferences: the keyboard shortcut that shows and hides the
panel, and whether to analyse automatically or only on request. No other
data is stored.
```

`offscreen`
```
The classifier runs on WebGPU, which Chrome does not expose to extension
service workers. The model therefore runs in an offscreen document. The
document renders nothing and is never visible to the user; it exists purely
to give the model a context with WebGPU and canvas access.
```

Host permission `https://streetviewpixels-pa.googleapis.com/*`
```
To download the image tiles of the panorama the user is currently looking
at, so the model has clean imagery to classify rather than a screenshot of
the page. This is the same public endpoint the host page already uses, and
the request is made without credentials. This is the only host the
extension can contact; it has no access to any other server, including any
belonging to the developer.
```

Content script host access (the four guessing sites)
```
To read the Street View panorama identifier out of the URLs of image tiles
the page is already loading, and to draw the prediction panel over the page.
The extension reads no other page content: no account data, no page text, no
cookies, no form fields.
```

**Remote code:** No, I am not using remote code.

**Data usage — tick nothing.** The extension collects none of the listed
categories. Nothing is sent to the developer, and no imagery leaves the
browser. Then certify:
- [x] I do not sell or transfer user data to third parties, outside of the approved use cases
- [x] I do not use or transfer user data for purposes unrelated to my item's single purpose
- [x] I do not use or transfer user data to determine creditworthiness or for lending purposes

**Privacy policy URL**
```
https://github.com/karsh-s/geogussr-cheat/blob/main/PRIVACY.md
```

---

## 5. Graphics you still need to make

| Asset | Size | Required |
|---|---|---|
| Store icon | 128×128 PNG | Yes — `icons/icon128.png` works |
| Screenshot | 1280×800 or 640×400 PNG | Yes, at least 1, up to 5 |
| Small promo tile | 440×280 PNG | Only if you want to be featured |
| Marquee promo tile | 1400×560 PNG | Only if you want to be featured |

Take the screenshot with the panel open, then run
`python3 make_screenshot.py <your.png>` to pad it to exactly 1280×800.

---

## 6. Distribution

- **Visibility:** Public, or Unlisted if you'd rather share by link only.
  Unlisted still goes through the same review.
- **Regions:** all, unless you have a reason to narrow.

---

## 7. What to expect from review

Typical turnaround is a few hours to a few business days. First submissions
and anything touching host permissions often sit at the longer end.

Realistic grounds for rejection, and what to do:

- **Package size.** 160 MB is far above a typical extension. It is within
  Chrome's limit, but it invites a closer look and a slow upload. The
  description explains why the model ships inside the package; if a reviewer
  queries it, the answer is that fetching the model at runtime would be
  remotely-hosted code, which the policy forbids.
- **Host permission scope.** One host, used for one purpose, with the
  justification above. This is a much easier case than the previous
  localhost build.
- **A complaint from one of the four sites.** A site operator can ask Google
  to remove an extension that interferes with their service. If that happens
  the listing is taken down; it is not appealable in any practical sense.

## 8. What was verified before submitting

Numbers from this build, not estimates:

| Check | Result |
|---|---|
| fp16 model vs PyTorch | top-1 100%, top-5 100%, maxdiff 0.021 |
| head ONNX vs PyTorch | maxdiff 4.8e-06 |
| JS reprojection vs server | **bit-exact**, 0/307200 pixels differ |
| JS bicubic vs Pillow | max 1/255 (Pillow's uint8 rounding between passes) |
| JS full chain vs Python | identical top-5 order, max prob delta 4.9e-03 |
| onnxruntime-web WebGPU | 1.1 s per guess |
| onnxruntime-web WASM | 7.1 s per guess (fallback) |
| Tile fetch from extension | works: Referer not required, endpoint returns `Access-Control-Allow-Origin` for `chrome-extension://` origins |

int8 quantisation was tried and rejected: 48% top-1 agreement, a different
and much worse model. Do not revisit it without re-measuring.
