# Privacy Policy — GeoGuessr Assistant

**Last updated: 12 November 2026**

GeoGuessr Assistant displays a country prediction for the Street View imagery
currently on screen. The model runs **on your own device**, inside the
extension. This policy describes every piece of data the extension touches.

## What the extension collects

**Nothing is collected, transmitted to us, or stored on any server we
control.**

The developer operates no backend, no analytics, no telemetry, no error
reporting, and no advertising. There is no account, no sign-in, and no
identifier of any kind. No prediction, image, or browsing activity is ever
sent to the developer.

The extension does **read and process website content** on the supported
sites: the panorama identifiers carried in the page's own tile URLs, and the
Street View imagery it then downloads. All of that processing happens in your
browser and none of it is transmitted to the developer. It is declared under
*Website content* in this extension's Chrome Web Store data disclosure for
that reason. The two sections below describe it in full.

## What the extension stores on your device

Two preferences, held in `chrome.storage.sync`:

| Setting | Purpose |
|---|---|
| Hotkey | The key that shows and hides the panel |
| Auto-analyse | Whether to run on every new panorama, or only when you ask |

Because this uses `storage.sync`, Chrome itself may replicate these two
values across browsers signed in to your Google account. That replication is
performed by Chrome under Google's privacy policy, not by this extension.

Predictions are cached in memory while the tab is open and are discarded
when it closes. Nothing is written to disk.

## What the extension reads from the page

On the supported sites listed below, the extension watches the page's own
network activity for Street View **panorama identifiers** — short opaque IDs
that appear in the URLs of image tiles the page is already loading. It reads
nothing else: not your account, not your game history, not page text, not
cookies, not form fields, not other tabs.

OpenGuessr and WorldGuessr show Street View inside an embedded Google Maps
frame (`www.google.com/maps/embed/…`), so the tiles are loaded by that frame
rather than by the page. A small part of the extension therefore also runs
inside those embedded frames — and only when the page around them is one of
the supported sites; inside a Google Maps embed on any other website it does
nothing. There it reads the same panorama identifiers from the tile URLs and
passes them to the panel, and nothing else. It does not read the embed's own
address, which on these sites contains the round's location.

## The one network request the extension makes

To analyse a panorama the extension downloads that panorama's own image
tiles from Google:

```
https://streetviewpixels-pa.googleapis.com/v1/tile?panoid=…
```

This is the same public endpoint the page itself uses, and the request is
made **without credentials** (`credentials: 'omit'`), so no cookies and no
account information are attached. Google receives the request as the
operator of that endpoint, and their handling of it is governed by
[Google's Privacy Policy](https://policies.google.com/privacy). The
extension sends Google nothing beyond the panorama identifier that the page
had already requested.

The extension has permission to contact that one host and no other. It
cannot reach any other server, including any belonging to the developer.

Once the tiles are downloaded, everything else — reprojection,
classification, cue scoring — happens locally in your browser. The imagery
is never uploaded anywhere.

## Sites the extension runs on

`geoguessr.com`, `openguessr.com`, `worldguessr.com` — plus Google Maps
Street View embeds, but only inside those three sites (see above).

It is inactive on every other site. It additionally disables itself when the
page URL indicates a multiplayer mode (duels, team duels, battle royale,
parties, lobbies, ranked and similar).

## Permissions, and why each is needed

- **`storage`** — to remember the two preferences above.
- **`offscreen`** — the classifier needs WebGPU, which Chrome does not
  expose to extension service workers. The model therefore runs in an
  offscreen document. It displays nothing and is never visible.
- **Access to `streetviewpixels-pa.googleapis.com`** — to download the
  panorama tiles described above.
- **Access to the three guessing sites** — to read the panorama identifier
  from the page's own resource loads and to draw the prediction panel.
- **A script in `www.google.com/maps/embed/*` frames** — to read the
  panorama identifier where a supported site shows Street View in an
  embedded Google map (see above). It exits immediately on other sites.

The extension requests no other permissions. It does not use `tabs`,
`activeTab`, `webRequest`, `cookies`, `history`, or `nativeMessaging`, and
it loads no remote code: the model and the inference runtime are bundled in
the package and never updated at runtime.

## Third-party components

The extension bundles [onnxruntime-web](https://github.com/microsoft/onnxruntime)
(MIT, Microsoft) to run the model. It is served from the extension package,
not from a CDN, and makes no network requests of its own.

## Children

The extension is not directed at children and collects no data from anyone.

## Changes

Material changes to this policy will be published at this URL with an
updated date, and shipped alongside a new extension version.

## Contact

Open an issue at <https://github.com/karsh-s/GeoClip/issues>.
