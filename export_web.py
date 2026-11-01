"""Export the v7 model for the self-contained extension.

Differs from export_onnx.py in three ways, all forced by what the browser
actually has to do:

  1. The visual tower and the head are SEPARATE graphs. The server averages
     the embeddings of an image and its mirror, renormalises, and only then
     applies the head -- so the head has to be callable on its own. Fusing
     them, as export_onnx.py does, makes that impossible.
  2. The visual graph is fp16. Measured at 100% top-1 agreement with fp32
     over 60 real Street View images (int8, by contrast, collapsed to 48%).
     The head stays fp32: it is ~1MB, so shrinking it buys nothing.
  3. The GeoTips cue embeddings are precomputed here. They are fixed, so
     shipping a 257x512 matrix beats shipping CLIP's whole text tower.

Produces, in extension/model/:
  visual.fp16.onnx   image  -> L2-normalised embedding
  head.onnx          embedding -> logits
  cues.f32           concatenated cue text embeddings, row-major float32
  model_meta.json    classes, preprocessing constants, cue index

Run:  python3 export_web.py
"""

import os
import json
import glob

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import open_clip
import onnx
import onnxruntime as ort
from onnxconverter_common import float16
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
OUT  = os.path.join(HERE, 'extension', 'model')
SIZE = 224
MEAN = [0.48145466, 0.4578275, 0.40821073]
STD  = [0.26862954, 0.26130258, 0.27577711]

CKPT_CANDIDATES = [
    os.path.join(HERE, 'models', 'geoclip_v7', 'best_model.pth'),
    os.path.join(HERE, 'best_model.pth'),
]


class Head(nn.Module):
    """Must match geoclip_v7.ipynb exactly."""
    def __init__(self, dim, n_cls):
        super().__init__()
        self.net = nn.Sequential(
            nn.Dropout(0.3), nn.Linear(dim, 512), nn.GELU(),
            nn.Dropout(0.2), nn.Linear(512, n_cls))

    def forward(self, x):
        return self.net(x)


class Visual(nn.Module):
    """Image -> L2-normalised embedding, matching the server's e1/e2."""
    def __init__(self, visual):
        super().__init__()
        self.visual = visual

    def forward(self, x):
        return F.normalize(self.visual(x), dim=-1)


def repair_fp16_casts(model):
    """convert_float_to_float16 rewrites tensor types but leaves each Cast
    node's own `to` attribute saying FLOAT, so the node contradicts its
    declared output and onnxruntime refuses to load the graph. These casts
    come from open_clip's LayerNormFp32 upcasting for precision; once the
    surrounding graph is fp16 they are no-ops, so aligning the attribute is
    the consistent fix. Measured lossless on this model -- see the module
    docstring -- but re-measure if the architecture ever changes."""
    vi = {v.name: v.type.tensor_type.elem_type
          for v in list(model.graph.value_info)
          + list(model.graph.output) + list(model.graph.input)}
    fixed = 0
    for n in model.graph.node:
        if n.op_type != 'Cast':
            continue
        for a in n.attribute:
            if (a.name == 'to' and a.i == onnx.TensorProto.FLOAT
                    and vi.get(n.output[0]) == onnx.TensorProto.FLOAT16):
                a.i = onnx.TensorProto.FLOAT16
                fixed += 1
    return fixed


def real_images(limit=60):
    """Prefer real Street View views over random noise: fp16 error depends
    on the activation distribution, and noise does not have the right one."""
    pats = [os.path.join(HERE, 'trainEurope', '*', '*.jpg'),
            os.path.join(HERE, 'trainStreetView', '*', '*.jpg')]
    files = sorted(f for p in pats for f in glob.glob(p))[:limit]
    if not files:
        return None
    mean = np.array(MEAN, np.float32)
    std = np.array(STD, np.float32)
    out = []
    for f in files:
        im = Image.open(f).convert('RGB')
        w, h = im.size
        s = SIZE / min(w, h)
        im = im.resize((round(w * s), round(h * s)), Image.BICUBIC)
        w, h = im.size
        l, t = (w - SIZE) // 2, (h - SIZE) // 2
        a = np.asarray(im.crop((l, t, l + SIZE, t + SIZE)), np.float32) / 255.0
        out.append(((a - mean) / std).transpose(2, 0, 1))
    return np.stack(out)


def main():
    ckpt = next((p for p in CKPT_CANDIDATES if os.path.exists(p)), None)
    if ckpt is None:
        raise SystemExit('No checkpoint found at:\n  ' + '\n  '.join(CKPT_CANDIDATES))
    os.makedirs(OUT, exist_ok=True)

    ck = torch.load(ckpt, map_location='cpu')
    if 'mode' not in ck:
        raise SystemExit(f'{ckpt} is not a v7 checkpoint (no "mode" key).')
    mode    = ck['mode']
    classes = list(ck['classes'])
    cm = ck.get('clip_model', 'ViT-B-16')
    cp = ck.get('clip_pretrain', 'laion2b_s34b_b88k')
    print(f'checkpoint : {os.path.relpath(ckpt, HERE)}')
    print(f'             {mode}, {len(classes)} classes, {cm}/{cp}')

    clip_model, _, _ = open_clip.create_model_and_transforms(cm, pretrained=cp)
    if mode == 'finetune':
        clip_model.visual.load_state_dict(ck['visual'])
    dim = clip_model.visual.output_dim
    head = Head(dim, len(classes))
    head.load_state_dict(ck['head'])

    visual = Visual(clip_model.visual).eval()
    head = head.eval()

    # ── reference activations from real imagery ──────────────
    batch = real_images()
    if batch is None:
        print('! no local Street View images; falling back to noise '
              '(fp16 check will be weaker)')
        batch = np.random.randn(8, 3, SIZE, SIZE).astype(np.float32)
    print(f'reference  : {batch.shape[0]} images')
    with torch.no_grad():
        emb_ref = visual(torch.from_numpy(batch)).numpy()
        log_ref = head(torch.from_numpy(emb_ref)).numpy()

    # ── visual graph ─────────────────────────────────────────
    vis_fp32 = os.path.join(OUT, '_visual.fp32.onnx')
    torch.onnx.export(
        visual, torch.from_numpy(batch[:1]), vis_fp32,
        input_names=['image'], output_names=['embedding'],
        dynamic_axes={'image': {0: 'batch'}, 'embedding': {0: 'batch'}},
        opset_version=17, do_constant_folding=True, dynamo=False)

    m = onnx.load(vis_fp32)
    m16 = float16.convert_float_to_float16(m, keep_io_types=False)
    fixed = repair_fp16_casts(m16)
    onnx.checker.check_model(m16, full_check=False)
    vis_fp16 = os.path.join(OUT, 'visual.fp16.onnx')
    onnx.save(m16, vis_fp16)
    print(f'visual     : {os.path.getsize(vis_fp16)/1e6:.0f} MB fp16 '
          f'({fixed} Cast nodes repaired)')

    s = ort.InferenceSession(vis_fp16, providers=['CPUExecutionProvider'])
    emb16 = np.concatenate([
        np.asarray(s.run(None, {'image': batch[i:i+10].astype(np.float16)})[0],
                   np.float32)
        for i in range(0, len(batch), 10)])
    del s

    # ── head graph ───────────────────────────────────────────
    head_path = os.path.join(OUT, 'head.onnx')
    torch.onnx.export(
        head, torch.from_numpy(emb_ref[:1]), head_path,
        input_names=['embedding'], output_names=['logits'],
        dynamic_axes={'embedding': {0: 'batch'}, 'logits': {0: 'batch'}},
        opset_version=17, do_constant_folding=True, dynamo=False)
    print(f'head       : {os.path.getsize(head_path)/1e6:.1f} MB fp32')

    sh = ort.InferenceSession(head_path, providers=['CPUExecutionProvider'])
    log16 = sh.run(None, {'embedding': emb16})[0]
    log32 = sh.run(None, {'embedding': emb_ref})[0]
    del sh

    # ── end-to-end check against PyTorch ─────────────────────
    agree = float(np.mean(log16.argmax(1) == log_ref.argmax(1)))
    top5 = float(np.mean([
        len(set(np.argsort(log16[i])[::-1][:5]) &
            set(np.argsort(log_ref[i])[::-1][:5])) / 5
        for i in range(len(log_ref))]))
    print(f'\nfp16 vs PyTorch : top-1 {agree:.1%}  top-5 {top5:.1%}  '
          f'maxdiff {np.abs(log16 - log_ref).max():.4f}')
    print(f'head  ONNX/torch: maxdiff {np.abs(log32 - log_ref).max():.2e}')
    if agree < 0.98:
        raise SystemExit('fp16 degraded the model — do not ship this.')

    # ── GeoTips cue embeddings ───────────────────────────────
    cue_index, rows = {}, []
    try:
        import geotips_prompts
    except ImportError:
        geotips_prompts = None

    if geotips_prompts and mode == 'probe':
        tokenizer = open_clip.get_tokenizer(cm)
        with torch.no_grad():
            for c in classes:
                cues = geotips_prompts.GEOTIPS.get(c, {})
                if not cues:
                    continue
                labels, texts = list(cues.keys()), list(cues.values())
                caps = [geotips_prompts.TEMPLATE.format(c=c, cue=t) for t in texts]
                e = F.normalize(clip_model.encode_text(tokenizer(caps)), dim=-1)
                cue_index[c] = {'labels': labels, 'texts': texts,
                                'offset': sum(r.shape[0] for r in rows),
                                'count': e.shape[0]}
                rows.append(e.numpy().astype(np.float32))
        mat = np.concatenate(rows) if rows else np.zeros((0, dim), np.float32)
        mat.tofile(os.path.join(OUT, 'cues.f32'))
        print(f'cues       : {mat.shape[0]} captions x {mat.shape[1]} dims '
              f'({mat.nbytes/1e6:.2f} MB) for {len(cue_index)} countries')
        cue_mode = 'scored'
    else:
        cue_mode = 'typical' if geotips_prompts else 'none'
        print(f'cues       : {cue_mode} (no embeddings)')

    meta = {'classes': classes, 'input_size': SIZE, 'mean': MEAN, 'std': STD,
            'clip_model': cm, 'mode': mode, 'embed_dim': dim,
            'cue_mode': cue_mode, 'cues': cue_index,
            'visual': 'visual.fp16.onnx', 'head': 'head.onnx',
            'n_headings': 4, 'view_fov': 90.0, 'view_pitch': -5.0,
            'view_px': 320, 'pano_zoom': 2, 'tile_px': 512}
    with open(os.path.join(OUT, 'model_meta.json'), 'w') as f:
        json.dump(meta, f, indent=2)

    os.remove(vis_fp32)
    print(f'\nwrote {os.path.relpath(OUT, HERE)}/')


if __name__ == '__main__':
    main()
