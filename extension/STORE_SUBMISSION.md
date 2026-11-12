# Chrome Web Store submission — GeoGuessr Assistant

Everything below is copy-paste ready for
<https://chrome.google.com/webstore/devconsole>.
Build the upload with `./build.sh` → `geoguessr-assistant-3.0.0.zip`.

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

`geoguessr-assistant-3.0.0.zip` — **160 MB** (196 MB unpacked), 24 files, no
remote code.

The bulk is the model (173 MB fp16) and onnxruntime-web's WASM runtime
(22 MB). Both ship inside the package and are never fetched at runtime,
which is what keeps this compliant with the remote-code policy. Uploading
160 MB over a slow link can time out; retry rather than re-cutting the zip.

---

## 3. Listing fields

**Name**
```
GeoGuessr Assistant
```

**Short description** (132 char limit; this is 118). Lives in `manifest.json`,
so changing it needs a repackage.
```
Predicts the country from Street View imagery with an on-device model, with honest confidence and a map of the region.
```

**Category:** Just for Fun
**Language:** English (United States)

**Detailed description**
```
Some rounds you know on sight. Others you spin in a circle on a gravel track
under a grey sky with absolutely nothing to go on.

This is for the second kind.

Press G. A panel slides in with the five countries most likely to be the one
you are standing in -- and then it tells you what made it think so.


WHAT THE PANEL GIVES YOU

The guess. 119 countries and territories, from Iceland to American Samoa,
ranked by probability, with a map of the region the leader is in.

How sure it is -- honestly. The percentages are calibrated against thousands
of locations the model never trained on. When it says 90% or more, it is
right about 98% of the time; when it says around 50%, about 60%. So a high
number means commit, and a low one with a close second means slow down and
look again. The spread is as useful as the answer, and it is the part most
tools never show you.

The reasons. Yellow centre lines. Bollard shapes. Licence plates, roof tiles,
road paint, the plants growing on the verge. The panel surfaces the cues of
the leading country that best match what is actually in front of you -- for
every one of the 119.

It keeps up. Move down the road and it reads each new panorama, and the
estimate sharpens as you go. When the next round starts, it clears itself.


LEARN THE META, NOT JUST THE ANSWER

Plenty of tools hand you a pin. This one hands you an argument.

After a few dozen rounds you start catching the bollards yourself, and the
reflector posts, and the particular grey of a Nordic sky. That is the point.
It is a second opinion you can interrogate, not an autopilot -- and when it
is only 30% sure, you will know to trust your own eyes instead.


IT ALL HAPPENS ON YOUR MACHINE

No account. No sign-up. No server to run. Nothing to configure.

The neural network ships inside the extension, which is why the download is
about 160 MB. Your screen is never captured, never uploaded, never seen by
anyone. No analytics, no telemetry, no developer server -- there is nothing
to send anything to. The one request it makes is to Google, for the Street
View imagery of the panorama you are already looking at.


SOLO PLAY ONLY

The extension switches itself off in duels, team duels, battle royale,
parties, lobbies and ranked. In those modes the panel says "solo play only"
and makes no guess. That is deliberate, and it is not a setting.

Even in single-player, using any assistance tool may breach the rules of the
site you are on. That is between you and them, so go and read them.


WORKS ON

geoguessr.com, openguessr.com, worldguessr.com


OPEN SOURCE

Every line of it: https://github.com/karsh-s/GeoClip
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

Content script host access (the three guessing sites)
```
To read the Street View panorama identifier out of the URLs of image tiles
the page is already loading, and to draw the prediction panel over the page.
The extension reads no other page content: no account data, no page text, no
cookies, no form fields.
```

Content script on `https://www.google.com/maps/embed/*`
```
OpenGuessr and WorldGuessr show Street View inside a Google Maps embed
iframe, so the panorama's image tiles are requested from inside that
iframe rather than by the game page. A small script runs only in those
embed frames, and only when the page around them is one of the three
supported games (checked with location.ancestorOrigins; on any other site
it exits immediately). It reads the panorama identifier out of the tile
URLs and passes it to the panel on the game page. It does not read the
embed's own URL, page content, cookies or anything else.
```

**Remote code:** No, I am not using remote code.

**Data usage — tick `Website content`, and nothing else.**

This is a judgement call, because Google never defines "collect". What its
User Data FAQ does say is that disclosure applies "even when data is processed
or stored locally on a user's device" and even when data "is not transmitted
to external servers or third parties". The content script reads tile URLs out
of the page and the extension downloads and processes panorama imagery, which
is website content under anyone's reading -- so it gets declared even though
none of it leaves the browser.

The asymmetry decides it: under-disclosing is a removal reason, over-disclosing
costs nothing. Everything else stays unticked --

- not *Location*: it infers where a **panorama** is, never where the user is
- not *Web history*: it reads the current URL to switch itself off in
  multiplayer, and neither stores nor transmits it
- not *User activity*: one keydown listener for the show/hide hotkey is not
  keystroke logging

Then tick all three certifications, each of which is true:
- [x] I do not sell or transfer user data to third parties, outside of the approved use cases
- [x] I do not use or transfer user data for purposes unrelated to my item's single purpose
- [x] I do not use or transfer user data to determine creditworthiness or for lending purposes

**Privacy policy URL**
```
https://github.com/karsh-s/GeoClip/blob/main/PRIVACY.md
```

---

## 5. Test instructions tab

A reviewer who installs this and opens geoguessr.com will see nothing at
all: the panel is behind a hotkey, and the extension disables itself in
multiplayer. Without these instructions the likeliest outcome is a
rejection for not working. Paste this into the **Test instructions** tab.

```
No account, login or credentials are needed.

1. Open https://www.geoguessr.com/ and start a SINGLE-PLAYER round on any
   map. The extension deliberately disables itself in duels, team duels,
   battle royale, parties and ranked modes; in those it shows "solo play
   only" and makes no prediction.

2. Press the "g" key. A panel appears in the top-left corner.

3. The first prediction takes a few seconds while the model loads. The
   model is read from inside the extension package, not downloaded.
   Later predictions take about one second.

4. The panel shows the five most likely countries with confidence bars,
   a map of the region the leading country is in (Europe, the Americas,
   Africa, the Middle East, Asia or Oceania), and the visual cues of that
   country which best match the image on screen.

If the panel says it is waiting for a panorama, pan or move once so the
page requests new Street View tiles. The extension reads the panorama
identifier out of those tile URLs; it does not read anything else on the
page.

The same works on openguessr.com and worldguessr.com.

The classifier and the onnxruntime-web runtime are both bundled in the
package. The only network request the extension makes is to
https://streetviewpixels-pa.googleapis.com/ for the image tiles of the
panorama being viewed, sent without credentials.
```

---

## 6. Graphics you still need to make

| Asset | Size | Required |
|---|---|---|
| Store icon | 128×128 PNG | Yes — `icons/icon128.png` works |
| Screenshot | 1280×800 or 640×400 PNG | Yes, at least 1, up to 5 |
| Small promo tile | 440×280 PNG | Only if you want to be featured |
| Marquee promo tile | 1400×560 PNG | Only if you want to be featured |

Take the screenshot with the panel open, then run
`python3 make_screenshot.py <your.png>` to pad it to exactly 1280×800.

---

## 7. Distribution

- **Visibility:** Public, or Unlisted if you'd rather share by link only.
  Unlisted still goes through the same review.
- **Regions:** all, unless you have a reason to narrow.

---

## 8. What to expect from review

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
- **A complaint from one of the three sites.** A site operator can ask Google
  to remove an extension that interferes with their service. If that happens
  the listing is taken down; it is not appealable in any practical sense.

## 9. What was verified before submitting

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
| 3.0 model | CLIP ViT-B/16, top 8 blocks fine-tuned on Street View; head over 576 sub-country regions summed to 119 countries, temperature 0.638 folded in |
| 3.0 fp16 export vs PyTorch | top-1 agreement 100%, min cosine 0.99999; head maxdiff 7.6e-06 |
| 3.0 training data | 63,356 locations x 4 views; quotas scaled by country size (5x for the largest, e.g. US, Russia, Brazil) |
| 3.0 held-out test, 119 countries | 9,803 locations in areas never trained on: top-1 80.9%, top-3 93.1%, top-5 96.2%; per-country average 83.8% |
| 3.0 calibration (held-out) | ECE 0.069; 80–100% band said 95%, was 98%; 40–60% band said 50%, was 61% |
| 3.0 live, full shipped path | 151 fresh panoramas, raw tiles, fp16 visual + head.onnx: top-1 85.4% (2.x head on the same: 74.8%), top-5 98.0% |
| 3.0 cues | 627 captions, 5–7 for each of the 119 countries; the 216 unchanged ones re-embed to cosine 1.00000 against 2.0's file; against labelled imagery a cue ranks its own country 2nd of 119 on median, 82% in the top 5 (new countries and the original 41 score the same) |
| 3.0 vs 2.0 on Europe | 3,729 held-out European locations: 2.0 (41-way) 49.5%, 3.0 (119-way) 67.4% |

int8 quantisation was tried and rejected: 48% top-1 agreement, a different
and much worse model. Do not revisit it without re-measuring.
