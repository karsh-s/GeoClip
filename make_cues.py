#!/usr/bin/env python3
"""Rebuild extension/model/cues.f32 and the cue index in model_meta.json.

The panel's "why" rows are GeoTips captions (geotips_prompts.py) scored
against the image: each caption is embedded once, here, with the text tower
that pairs with the shipped visual tower (open_clip ViT-B-16,
laion2b_s34b_b88k), so the extension ships a small matrix instead of a text
encoder. export_web.py does the same thing as part of a full export; this
does only the cues, for whatever class list model_meta.json currently holds,
so it can be re-run after adding countries without re-exporting the model.

    python3 make_cues.py                 # write cues.f32 + update model_meta.json
    python3 make_cues.py --check DIR     # also score every cue against a
                                         # labelled embedding set (index.jsonl
                                         # + emb/ as written by the collector)

--check answers "does this caption actually look like its country?": for each
cue it ranks all countries by how well their average image matches the
caption and reports where the cue's own country lands (1 = best). It is run
twice, with and without the country's name in the caption, because CLIP
knows country names and the named version flatters weak cues. Scores are
centred per country and per caption first, since some places match any text.
"""

import argparse
import json
import os

import numpy as np
import torch
import torch.nn.functional as F
import open_clip

import geotips_prompts

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL = os.path.join(HERE, 'extension', 'model')
NAMELESS = 'a Google Street View photo, {cue}'


def embed(model, tok, texts):
    out = []
    with torch.no_grad():
        for i in range(0, len(texts), 128):
            e = F.normalize(model.encode_text(tok(texts[i:i + 128])).float(), dim=-1)
            out.append(e.numpy().astype(np.float32))
    return np.concatenate(out)


def country_means(data, classes, isos):
    """L2-normalised mean image embedding per class, from the collector's files."""
    recs = [json.loads(l) for l in open(os.path.join(data, 'index.jsonl'))]
    shards = sorted(f for f in os.listdir(os.path.join(data, 'emb'))
                    if f.startswith('shard_') and f.endswith('.npy') and '.tmp' not in f)
    E = np.concatenate([np.load(os.path.join(data, 'emb', s)) for s in shards]).astype(np.float32)
    k_of = {iso: k for k, iso in enumerate(isos)}
    sums, r = np.zeros((len(classes), E.shape[1]), np.float32), 0
    for rec in recs:
        n = len(rec['files'])
        if rec['cc'] in k_of:
            sums[k_of[rec['cc']]] += E[r:r + n].sum(0)
        r += n
    return sums / np.linalg.norm(sums, axis=1, keepdims=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--check', metavar='DIR', help='labelled embedding set to score cues against')
    ap.add_argument('--dry-run', action='store_true', help='do not write any files')
    args = ap.parse_args()

    meta_path = os.path.join(MODEL, 'model_meta.json')
    meta = json.load(open(meta_path))
    classes = meta['classes']

    model, _, _ = open_clip.create_model_and_transforms(
        'ViT-B-16', pretrained='laion2b_s34b_b88k')
    model.eval()
    tok = open_clip.get_tokenizer('ViT-B-16')

    index, caps, owner, plain = {}, [], [], []
    for k, c in enumerate(classes):
        cues = geotips_prompts.GEOTIPS.get(c, {})
        if not cues:
            continue
        labels, texts = list(cues.keys()), list(cues.values())
        index[c] = {'labels': labels, 'texts': texts, 'offset': len(caps), 'count': len(texts)}
        caps += [geotips_prompts.TEMPLATE.format(c=c, cue=t) for t in texts]
        plain += [NAMELESS.format(cue=t) for t in texts]
        owner += [k] * len(texts)
    mat = embed(model, tok, caps)
    missing = [c for c in classes if c not in index]
    print(f'{mat.shape[0]} cues for {len(index)}/{len(classes)} countries'
          + (f' | none for: {missing}' if missing else ''))

    # the previously shipped rows must come out the same, or the text tower
    # here is not the one the extension's visual tower was paired with
    old_path = os.path.join(MODEL, 'cues.f32')
    old_index = meta.get('cues') or {}
    if os.path.exists(old_path) and old_index:
        old = np.fromfile(old_path, np.float32).reshape(-1, mat.shape[1])
        cos = []
        for c, o in old_index.items():
            n = index.get(c)
            if n and n['texts'] == o['texts']:
                cos.append((old[o['offset']:o['offset'] + o['count']]
                            * mat[n['offset']:n['offset'] + n['count']]).sum(1))
        if cos:
            cos = np.concatenate(cos)
            print(f'unchanged cues vs shipped cues.f32: {len(cos)} rows, min cosine {cos.min():.5f}')
            if cos.min() < 0.999:
                raise SystemExit('text embeddings do not reproduce the shipped ones — not writing')

    if args.check:
        M = country_means(args.check, classes, meta['iso'])
        own = np.array(owner)
        for tag, emb_ in (('with country name (as shipped)', mat),
                          ('caption only', embed(model, tok, plain))):
            S = emb_ @ M.T                                   # cue x country
            # Some countries' average image sits close to almost any caption
            # (dense small places: Gibraltar, Monaco), and some captions are
            # close to almost any image. Remove both baselines, so a cue is
            # judged on whether it fits its country better than expected.
            S = S - S.mean(0, keepdims=True) - S.mean(1, keepdims=True) + S.mean()
            rank = 1 + (S > S[np.arange(len(own)), own][:, None]).sum(1)
            print(f'\n{tag}: own-country rank of {len(own)} cues among {len(classes)} countries')
            print(f'  median {int(np.median(rank))} | top-1 {np.mean(rank == 1):.0%} | '
                  f'top-5 {np.mean(rank <= 5):.0%} | top-20 {np.mean(rank <= 20):.0%} | '
                  f'worse than 40th {np.mean(rank > 40):.0%}')
            if tag == 'caption only':
                order = np.argsort(-rank)
                print('  weakest captions (rank, country, cue, best-matching country instead):')
                for i in order[:40]:
                    print(f'   {rank[i]:3d}  {classes[own[i]]:26s} {caps[i].split(", ", 1)[1][:62]:62s} '
                          f'-> {classes[int(S[i].argmax())]}')
                per = {classes[k]: float(np.median(rank[own == k])) for k in set(owner)}
                worst = sorted(per.items(), key=lambda kv: -kv[1])[:12]
                print('  countries whose cues are weakest overall (median rank):',
                      ', '.join(f'{c} {r:.0f}' for c, r in worst))

    if args.dry_run:
        return
    mat.tofile(old_path)
    meta['cues'] = index
    meta['cue_mode'] = 'scored'
    json.dump(meta, open(meta_path, 'w'), indent=2, ensure_ascii=False)
    print(f'\nwrote {old_path} ({mat.nbytes / 1e6:.2f} MB) and the cue index in model_meta.json')


if __name__ == '__main__':
    main()
