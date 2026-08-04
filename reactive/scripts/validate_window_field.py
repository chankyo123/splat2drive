"""Validate WindowFieldBackend offline: render playback along the field's own
recorded trajectory and lay it next to the input clip. Confirms (a) pose/scale
alignment (camera matches the field), (b) the holefill hybrid, (c) that the
window layer is sharp vs the single field. GPU render -> remote only.

Usage: validate_window_field.py --field_dir <dir> --clip <input.mp4> --out <dir>
"""
import argparse, os, sys, numpy as np, torch, imageio.v2 as imageio, cv2
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.expanduser("~/splat2drive/server"))
from window_field_backend import WindowFieldBackend

ap = argparse.ArgumentParser()
ap.add_argument("--field_dir", required=True)
ap.add_argument("--clip", default=None)
ap.add_argument("--out", required=True)
ap.add_argument("--fps", type=int, default=12)
ap.add_argument("--stride", type=int, default=3)
args = ap.parse_args()
os.makedirs(args.out, exist_ok=True)

be = WindowFieldBackend(args.field_dir, device="cuda", holefill=True)
H, W, N = be.H, be.W, be.n_frames

gt = None
if args.clip and os.path.exists(args.clip):
    cap, raw = cv2.VideoCapture(args.clip), []
    while True:
        ok, f = cap.read()
        if not ok: break
        raw.append(cv2.cvtColor(f, cv2.COLOR_BGR2RGB))
    cap.release()
    idx = np.unique(np.linspace(0, len(raw) - 1, min(N, len(raw))).round().astype(int))
    gt = {i: np.asarray(Image.fromarray(raw[min(i, len(raw)-1)]).resize((W, H))) for i in range(N)}

def lab(img, txt, c=(120, 240, 160)):
    im = Image.fromarray(img).copy(); dr = ImageDraw.Draw(im)
    try: fn = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
    except Exception: fn = ImageFont.load_default()
    dr.rectangle([0, 0, im.width, 20], fill=(0, 0, 0)); dr.text((5, 3), txt, font=fn, fill=c)
    return np.asarray(im)

def render(idx, mode):
    w2c, K = be.ext[idx], be.K[idx]
    if mode == "hybrid":
        return be._render_w2c(w2c, K, idx)
    if mode == "window":
        sv = be.single; be.single = None
        out = be._render_w2c(w2c, K, idx); be.single = sv; return out
    if mode == "single":                     # single field only, rasterized alone
        im, _ = be._raster_one(be.single, w2c.to(be.device).float(), K.to(be.device).float())
        return (im.clamp(0, 1) * 255).to(torch.uint8).cpu().numpy()

frames, keys = [], []
KEYSET = set(int(x) for x in np.linspace(0, N - 1, 5).round())
for i in range(0, N, args.stride):
    hyb = lab(render(i, "hybrid"), f"HYBRID (window+holefill)  f{i}/{N}  d={be.dist[i]:.1f}m")
    row = [hyb]
    if gt is not None:
        row = [lab(gt[i], "input clip (GT)"), hyb]
    frames.append(np.concatenate(row, axis=1))
    if i in KEYSET:
        win = lab(render(i, "window"), "window only (sharp)", (120, 240, 160))
        sin = lab(render(i, "single"), "single field only (blurry)", (255, 170, 120))
        parts = ([lab(gt[i], "GT")] if gt is not None else []) + [win, sin]
        keys.append(np.concatenate(parts, axis=1))

imageio.mimwrite(os.path.join(args.out, "window_playback.mp4"), frames, fps=args.fps, quality=8)
imageio.imwrite(os.path.join(args.out, "window_playback_strip.png"),
                np.concatenate([frames[k] for k in np.linspace(0, len(frames)-1, 5).astype(int)], axis=0))
if keys:
    imageio.imwrite(os.path.join(args.out, "window_vs_single_keys.png"), np.concatenate(keys, axis=0))
print(f"[val] wrote window_playback.mp4 ({len(frames)} frames) + strips", flush=True)
