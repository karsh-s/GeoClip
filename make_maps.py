#!/usr/bin/env python3
"""Generate extension/map_paths.js: one map per region, from Natural Earth.

The panel shows the region the leading guess is in -- Europe, North America,
Central America & Caribbean, South America, Africa, Middle East, Asia,
Oceania -- with a world view as the fallback. Each region is Web Mercator
over its own bounding box, widened to the panel's aspect. Europe is centred
on the frame the original europe_paths.js used (25W-45E, 34N-72N).

Countries the model predicts are drawn as their own paths and coloured by
probability; every other country in view is drawn faintly as context, so a
region never shows holes where its neighbours should be. Countries too small
to see at panel size, and the few Natural Earth folds into a sovereign
(Christmas Island, Gibraltar, Reunion, Svalbard), get a dot instead.

Source: ne_50m_admin_0_countries.geojson from Natural Earth (public domain),
https://github.com/nvkelso/natural-earth-vector

    python3 make_maps.py --ne path/to/ne_50m_admin_0_countries.geojson
"""

import argparse
import json
import math
import os

from shapely.geometry import box, shape, Polygon, MultiPolygon
from shapely.ops import transform

HERE = os.path.dirname(os.path.abspath(__file__))

# key: (label, lng0, lat0, lng1, lat1): the box that must be visible. Europe's
# is the original europe_paths.js frame. Each is widened to the panel aspect.
REGIONS = {
    'europe':        ('Europe', -25, 34, 45, 72),
    'north_america': ('North America', -170, 15, -50, 72),
    'caribbean':     ('Central America & Caribbean', -93, 7, -59, 24),
    'south_america': ('South America', -82, -56, -34, 13),
    'africa':        ('Africa', -18, -35, 56, 38),
    'middle_east':   ('Middle East', 30, 12, 62, 38),
    'asia':          ('Asia', 60, -11, 150, 55),
    'oceania':       ('Oceania', 100, -48, 195, 22),     # past 180 so American Samoa fits
    'world':         ('World', -180, -56, 180, 80),
}

# Where each predicted country is shown. Anything not listed falls back to
# Natural Earth's continent, and anything outside its region's frame (Svalbard)
# to the world view.
REGION_OF = {
    'TR': 'europe', 'CY': 'europe', 'RU': 'europe', 'GE': 'europe',
    'MX': 'north_america', 'BM': 'north_america', 'GL': 'north_america',
    'GT': 'caribbean', 'CR': 'caribbean', 'PA': 'caribbean', 'DO': 'caribbean',
    'PR': 'caribbean', 'VI': 'caribbean', 'CW': 'caribbean',
    'AE': 'middle_east', 'IL': 'middle_east', 'PS': 'middle_east', 'JO': 'middle_east',
    'LB': 'middle_east', 'OM': 'middle_east', 'QA': 'middle_east', 'BH': 'middle_east',
    'SA': 'middle_east',
    'RE': 'africa', 'ST': 'africa', 'MG': 'africa', 'GI': 'europe',
    'CX': 'oceania', 'GU': 'oceania', 'MP': 'oceania', 'AS': 'oceania',
    'SJ': 'world',
}
CONTINENT = {'Europe': 'europe', 'North America': 'north_america',
             'South America': 'south_america', 'Africa': 'africa',
             'Asia': 'asia', 'Oceania': 'oceania'}

# Natural Earth folds these into their sovereign, so they only get a dot.
POINTS = {'CX': (-10.49, 105.62), 'GI': (36.14, -5.35),
          'RE': (-21.11, 55.53), 'SJ': (78.22, 15.65)}

# Where a country is placed when its outline's own centre is unrepresentative:
# Greenland's coverage is its west-coast towns, Russia's mostly west of the Urals.
ANCHOR = {'GL': (64.18, -51.72), 'RU': (55.75, 37.62)}

PANEL_W, PANEL_H = 330, 150          # the map element's size in the panel
DOT_BELOW_PX = 4.0                   # smaller than this on screen -> also a dot


def merc(lat):
    lat = max(-85.0, min(85.0, lat))
    return math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))


def unmerc(y):
    return math.degrees(2 * math.atan(math.exp(y)) - math.pi / 2)


class Frame:
    """A region's Mercator frame, widened to the panel's aspect.

    The core box is what must be visible. It is grown symmetrically (in
    projected space) until it matches the map element's 330x150, so nothing
    is letterboxed: the region sits centred at the same scale, and the
    margins show its real neighbours instead of empty bands.
    """
    def __init__(self, key, label, lng0, lat0, lng1, lat1):
        self.key, self.label = key, label
        x0, x1, y0, y1 = math.radians(lng0), math.radians(lng1), merc(lat0), merc(lat1)
        aspect = PANEL_W / PANEL_H
        w, h = x1 - x0, y1 - y0
        if w / h < aspect and h * aspect <= 2 * math.pi:
            cx = (x0 + x1) / 2
            x0, x1 = cx - h * aspect / 2, cx + h * aspect / 2
        elif w / h > aspect:
            cy = (y0 + y1) / 2
            y0, y1 = cy - w / aspect / 2, cy + w / aspect / 2
        self.lng0, self.lng1 = math.degrees(x0), math.degrees(x1)
        self.lat0, self.lat1 = unmerc(y0), unmerc(y1)
        self.y0, self.y1 = y0, y1
        self.W = 1000.0
        self.H = round(self.W * (y1 - y0) / (x1 - x0))
        self.px = max(self.W / PANEL_W, self.H / PANEL_H)   # view units per pixel
        # simplify to about a third of a screen pixel: invisible, and small
        self.tol = (self.lng1 - self.lng0) / self.W * self.px * 0.35

    def shift(self, g):
        """Wrap polygons by 360 degrees when the frame extends past +-180."""
        if self.lng1 <= 180 and self.lng0 >= -180:
            return g
        polys = g.geoms if isinstance(g, MultiPolygon) else [g]
        moved = []
        for p in polys:
            dx = 0
            if self.lng1 > 180 and p.bounds[2] < self.lng1 - 360:
                dx = 360
            elif self.lng0 < -180 and p.bounds[0] > self.lng0 + 360:
                dx = -360
            moved.append(transform(lambda x, y, z=None, dx=dx: (x + dx, y), p) if dx else p)
        return MultiPolygon(moved) if len(moved) > 1 else moved[0]

    def project(self, x, y, z=None):
        px = (x - self.lng0) / (self.lng1 - self.lng0) * self.W
        py = self.H - (merc(y) - self.y0) / (self.y1 - self.y0) * self.H
        return px, py

    def point(self, lat, lng):
        if self.lng1 > 180 and lng < self.lng1 - 360:
            lng += 360
        elif self.lng0 < -180 and lng > self.lng0 + 360:
            lng -= 360
        return self.project(lng, lat)

    def inside(self, lat, lng):
        x, y = self.point(lat, lng)
        return 0 <= x <= self.W and 0 <= y <= self.H

    def path(self, geom):
        """Clip, simplify and project to an SVG path; holes kept (evenodd)."""
        g = self.shift(geom).intersection(
            box(self.lng0 - 1, self.lat0 - 1, self.lng1 + 1, self.lat1 + 1))
        if g.is_empty:
            return '', 0.0, None
        g = g.simplify(self.tol, preserve_topology=True)
        g = transform(self.project, g)
        polys = [p for p in (g.geoms if hasattr(g, 'geoms') else [g])
                 if isinstance(p, Polygon)]
        d, area, biggest = [], 0.0, None
        for p in polys:
            if p.area < 2.0:                       # specks
                continue
            area += p.area
            if biggest is None or p.area > biggest.area:
                biggest = p
            for ring in [p.exterior, *p.interiors]:
                pts = list(ring.coords)[:-1]
                if len(pts) >= 3:
                    d.append('M' + 'L'.join(f'{x:.0f} {y:.0f}' for x, y in pts) + 'Z')
        return ''.join(d), area, biggest


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--ne', required=True, help='ne_50m_admin_0_countries.geojson')
    ap.add_argument('--meta', default=os.path.join(HERE, 'extension', 'model', 'model_meta.json'))
    ap.add_argument('--out', default=os.path.join(HERE, 'extension', 'map_paths.js'))
    args = ap.parse_args()

    meta = json.load(open(args.meta))
    if 'iso' not in meta:
        raise SystemExit('model_meta.json has no "iso" list -- export a global model first')
    name_of = dict(zip(meta['iso'], meta['classes']))

    feats = {}
    for f in json.load(open(args.ne))['features']:
        p = f['properties']
        iso = p.get('ISO_A2_EH') if p.get('ISO_A2_EH') not in (None, '-99') else p.get('ISO_A2')
        feats.setdefault(iso, []).append((shape(f['geometry']), p))

    frames = {k: Frame(k, *v) for k, v in REGIONS.items()}

    # each predicted country's home region, and a representative point
    region_of, where = {}, {}
    for iso in meta['iso']:
        if iso in POINTS or iso in ANCHOR:
            lat, lng = POINTS.get(iso) or ANCHOR[iso]
        elif iso in feats:
            g = max((g for g, _ in feats[iso]), key=lambda g: g.area)
            biggest = max(g.geoms, key=lambda p: p.area) if hasattr(g, 'geoms') else g
            rp = biggest.representative_point()
            lat, lng = rp.y, rp.x
        else:
            print(f'  !! {iso} {name_of[iso]}: no outline and no point -- world dot omitted')
            continue
        where[iso] = (lat, lng)
        cont = feats[iso][0][1].get('CONTINENT') if iso in feats else None
        reg = REGION_OF.get(iso) or CONTINENT.get(cont, 'world')
        if not frames[reg].inside(lat, lng):
            print(f'  {iso} {name_of[iso]}: outside {reg} frame -> world')
            reg = 'world'
        region_of[name_of[iso]] = reg

    out = {}
    for key, fr in frames.items():
        paths, dots, ctx, order = {}, {}, [], []
        for iso, items in feats.items():
            geom = items[0][0] if len(items) == 1 else MultiPolygon(
                [p for g, _ in items for p in (g.geoms if hasattr(g, 'geoms') else [g])])
            if not geom.is_valid:
                geom = geom.buffer(0)
            if not fr.shift(geom).intersects(box(fr.lng0, fr.lat0, fr.lng1, fr.lat1)):
                continue
            d, area, biggest = fr.path(geom)
            if iso in name_of:
                if d:
                    order.append((area, name_of[iso], d))
                b = biggest.bounds if biggest is not None else None
                small = b is None or max(b[2] - b[0], b[3] - b[1]) < DOT_BELOW_PX * fr.px
                if small and iso in where and fr.inside(*where[iso]):
                    x, y = fr.point(*where[iso])
                    dots[name_of[iso]] = [round(x, 1), round(y, 1)]
            elif d:
                ctx.append(d)
        # biggest first, so an enclave (Lesotho, San Marino) is drawn on top
        for _, name, d in sorted(order, key=lambda t: -t[0]):
            paths[name] = d
        for iso, (lat, lng) in where.items():
            if iso in POINTS and fr.inside(lat, lng):
                x, y = fr.point(lat, lng)
                dots[name_of[iso]] = [round(x, 1), round(y, 1)]
        out[key] = {'label': fr.label, 'view': f'0 0 {fr.W:.0f} {fr.H:.0f}',
                    'px': round(fr.px, 2), 'context': ''.join(ctx),
                    'paths': paths, 'dots': dots}

    js = ('// Region maps for the panel, generated by make_maps.py from Natural Earth 50m\n'
          '// (public domain). Web Mercator per region; see make_maps.py for frames.\n'
          'const MAP_REGIONS = ' + json.dumps(out, ensure_ascii=False, separators=(',', ':')) + ';\n'
          'const MAP_REGION_OF = ' + json.dumps(region_of, ensure_ascii=False, separators=(',', ':')) + ';\n')
    open(args.out, 'w').write(js)

    count = {}
    for n, r in region_of.items():
        count.setdefault(r, []).append(n)
    for k, fr in frames.items():
        o = out[k]
        print(f'  {k:14s} {o["view"]:>12s} | {len(count.get(k, [])):3d} countries | '
              f'{len(o["paths"]):3d} paths, {len(o["dots"]):2d} dots | '
              f'{(len(o["context"]) + sum(map(len, o["paths"].values()))) / 1024:.0f} KB')
    print(f'  wrote {args.out} ({len(js) / 1024:.0f} KB), {len(region_of)}/{len(meta["iso"])} placed')


if __name__ == '__main__':
    main()
