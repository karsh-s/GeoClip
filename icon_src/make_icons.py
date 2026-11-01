"""Turn the logo render into the extension's icon set.

The source is a flat white JPEG-ish render with no alpha. A plain "all white
pixels are background" rule would eat the lens highlight, the white outline
round the globe and the letters of ASSISTANT, so the background is found by
flood fill from the border instead: only white that is connected to the edge
is removed.

Downsampling 2000px -> 128px does the antialiasing, so the mask stays hard.
"""
import os
import numpy as np
from PIL import Image
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
ICONS = os.path.join(os.path.dirname(HERE), 'extension', 'icons')
SIZES = (128, 48, 32, 16)
PAD = 0.045          # breathing room so the artwork does not touch the edge


def cutout(path):
    src = Image.open(path).convert('RGB')
    a = np.array(src)

    white = (a > 236).all(axis=2)
    lab, n = ndimage.label(white)
    border = set(lab[0].tolist()) | set(lab[-1].tolist()) \
        | set(lab[:, 0].tolist()) | set(lab[:, -1].tolist())
    border.discard(0)
    bg = np.isin(lab, list(border))

    alpha = (~bg).astype(np.uint8) * 255
    out = src.convert('RGBA')
    out.putalpha(Image.fromarray(alpha))
    return out.crop(Image.fromarray(alpha).getbbox())


def square(img, size):
    """Fit on a transparent square, preserving aspect, with a little padding."""
    inner = int(size * (1 - 2 * PAD))
    s = min(inner / img.width, inner / img.height)
    r = img.resize((max(1, round(img.width * s)), max(1, round(img.height * s))),
                   Image.LANCZOS)
    canvas = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    canvas.alpha_composite(r, ((size - r.width) // 2, (size - r.height) // 2))
    return canvas


if __name__ == '__main__':
    logo = cutout(os.path.join(HERE, 'logo_source.webp'))
    print('trimmed to', logo.size)
    square(logo, 1024).save(os.path.join(HERE, 'master_1024.png'))
    for n in SIZES:
        square(logo, n).save(os.path.join(ICONS, f'icon{n}.png'))
    print('wrote icon' + '/'.join(str(n) for n in SIZES), 'to', ICONS)
