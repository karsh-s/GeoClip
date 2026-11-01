# Chrome Web Store submission — GeoGuessr Assistant

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
GeoGuessr Assistant
```

**Short description** (132 char limit; this is 125). Lives in `manifest.json`,
so changing it needs a repackage.
```
Predicts the country from Street View imagery with an on-device model, and shows which of that country's cues match the view.
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

The guess. 41 European countries, ranked by probability.

How sure it is. 82% on Iceland means commit. 38% on Malta with Spain right
behind it means slow down and look again. The spread is as useful as the
answer, and it is the part most tools never show you.

The reasons. Yellow centre lines. Bollard shapes. Licence plates, roof tiles,
road paint, the plants growing on the verge. The panel surfaces the cues of
the leading country that best match what is actually in front of you.

It keeps up. Move down the road and it reads each new panorama, and the
estimate sharpens as you go.


LEARN THE META, NOT JUST THE ANSWER

Plenty of tools hand you a pin. This one hands you an argument.

After a few dozen rounds you start catching the bollards yourself, and the
reflector posts, and the particular grey of a Nordic sky. That is the point.
It is a second opinion you can interrogate, not an autopilot -- and when it
is only 38% sure, you will know to trust your own eyes instead.


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

geoguessr.com, openguessr.com, worldguessr.com, freeguessr.com


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
   a map of the leading country, and the visual cues of that country
   which best match the image on screen.

If the panel says it is waiting for a panorama, pan or move once so the
page requests new Street View tiles. The extension reads the panorama
identifier out of those tile URLs; it does not read anything else on the
page.

The same works on openguessr.com, worldguessr.com and freeguessr.com.

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
- **A complaint from one of the four sites.** A site operator can ask Google
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

int8 quantisation was tried and rejected: 48% top-1 agreement, a different
and much worse model. Do not revisit it without re-measuring.
