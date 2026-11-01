"""Compose the store icon: the globe, a magnifying glass, and the wordmark.

Rendered at 8x and downsampled -- cheaper than writing an antialiaser, and it
keeps the curves clean once this is squeezed into a 16px toolbar icon.

The lens genuinely magnifies what is under it rather than sitting on top as a
grey disc, which is the whole reason it reads as a magnifier at 128px.
"""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

S = 1024
HERE = os.path.dirname(os.path.abspath(__file__)) + '/'
FONT = '/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf'

EDGE, CENTRE, WHITE = (34, 28, 60), (86, 78, 140), (255, 255, 255)
RADIUS = int(S * 0.18)
ZOOM = 1.75


def corner_mask():
    m = Image.new('L', (S, S), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, S - 1, S - 1], radius=RADIUS, fill=255)
    return m


def tile():
    y, x = np.mgrid[0:S, 0:S].astype(np.float32)
    r = np.sqrt(((x - S * .5) / (S * .70)) ** 2 + ((y - S * .40) / (S * .70)) ** 2)
    t = np.clip(r, 0, 1)[..., None]
    img = np.array(CENTRE, np.float32) * (1 - t) + np.array(EDGE, np.float32) * t
    bg = Image.fromarray(img.astype(np.uint8), 'RGB').convert('RGBA')
    bg.putalpha(corner_mask())
    return bg


def add_glass(base, cx, cy, rad):
    """Magnify `base` inside the lens, then rim and handle it."""
    d = int(rad * 2.4)
    box = (cx - d // 2, cy - d // 2, cx + d // 2, cy + d // 2)
    patch = base.crop(box).resize((int(d * ZOOM),) * 2, Image.LANCZOS)
    px = cx - patch.width // 2
    py = cy - patch.height // 2

    lens = Image.new('L', (S, S), 0)
    ImageDraw.Draw(lens).ellipse([cx - rad, cy - rad, cx + rad, cy + rad], fill=255)
    lens = lens.filter(ImageFilter.GaussianBlur(1.5))

    shadow = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).ellipse(
        [cx - rad, cy - rad + 16, cx + rad, cy + rad + 16], fill=(0, 0, 0, 110))
    base.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(20)))

    mag = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    mag.paste(patch.convert('RGBA'), (px, py))
    mag.putalpha(Image.fromarray(
        np.minimum(np.array(mag.split()[3]), np.array(lens))))
    base.alpha_composite(mag)

    deco = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    dd = ImageDraw.Draw(deco)
    dd.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], fill=(200, 228, 255, 34))
    dd.arc([cx - rad * .70, cy - rad * .70, cx + rad * .70, cy + rad * .70],
           start=146, end=232, fill=(255, 255, 255, 170), width=18)
    base.alpha_composite(deco)

    a = np.radians(225)
    hand = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    hd = ImageDraw.Draw(hand)
    x0, y0 = cx + rad * .96 * np.cos(a), cy + rad * .96 * np.sin(a)
    x1, y1 = cx + (rad + 128) * np.cos(a), cy + (rad + 128) * np.sin(a)
    hd.line([x0, y0, x1, y1], fill=WHITE + (255,), width=54)
    hd.ellipse([x1 - 27, y1 - 27, x1 + 27, y1 + 27], fill=WHITE + (255,))
    hd.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], outline=WHITE + (255,), width=42)
    base.alpha_composite(hand)


def wordmark(layer, text, cy, target_w, tracking=.10):
    size = 10
    while size < 400:
        f = ImageFont.truetype(FONT, size)
        w = (sum(f.getbbox(c)[2] - f.getbbox(c)[0] for c in text)
             + tracking * size * (len(text) - 1))
        if w >= target_w:
            break
        size += 2
    f = ImageFont.truetype(FONT, size)
    widths = [f.getbbox(c)[2] - f.getbbox(c)[0] for c in text]
    gap = tracking * size
    asc, _ = f.getmetrics()
    x = (S - (sum(widths) + gap * (len(text) - 1))) / 2
    d = ImageDraw.Draw(layer)
    for c, w in zip(text, widths):
        d.text((x - f.getbbox(c)[0], cy - asc / 2), c, font=f, fill=WHITE + (255,))
        x += w + gap


def build(with_text=True):
    img = tile()
    globe = Image.open(HERE + 'globe_cut.png').convert('RGBA')
    gw = int(S * (.58 if with_text else .76))
    gh = int(gw * globe.height / globe.width)
    globe = globe.resize((gw, gh), Image.LANCZOS)
    gx, gy = (S - gw) // 2, int(S * (.045 if with_text else .11))
    img.alpha_composite(globe, (gx, gy))

    if with_text:
        add_glass(img, gx + int(gw * .23), gy + int(gh * .78), int(S * .147))
    else:
        add_glass(img, gx + int(gw * .23), gy + int(gh * .80), int(S * .175))

    if with_text:
        layer = Image.new('RGBA', (S, S), (0, 0, 0, 0))
        wordmark(layer, 'ASSISTANT', int(S * .873), int(S * .72))
        sh = Image.new('RGBA', (S, S), (0, 0, 0, 0))
        sh.putalpha(layer.split()[3].point(lambda v: int(v * .6)))
        img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(9)))
        img.alpha_composite(layer)

    img.putalpha(Image.fromarray(
        np.minimum(np.array(img.split()[3]), np.array(corner_mask()))))
    return img


if __name__ == '__main__':
    # 128 carries the wordmark -- it is the store icon and the one shown on
    # chrome://extensions. Below that the word is an unreadable smudge, so the
    # toolbar sizes get the globe and lens alone.
    icons = os.path.join(os.path.dirname(HERE.rstrip('/')), 'extension', 'icons')
    text, plain = build(True), build(False)
    text.save(HERE + 'master_1024.png')
    text.resize((128, 128), Image.LANCZOS).save(os.path.join(icons, 'icon128.png'))
    for n in (48, 32, 16):
        plain.resize((n, n), Image.LANCZOS).save(os.path.join(icons, f'icon{n}.png'))
    print('wrote icon128 (with wordmark) and icon48/32/16 to', icons)
