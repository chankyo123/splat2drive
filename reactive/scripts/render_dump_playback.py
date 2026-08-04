"""Re-render a DGGT dump along its OWN logged camera trajectory (playback) and,
optionally, put the original input video frame side by side. This isolates the
reconstruction: playback renders the exact views DGGT was fit on, so any
ghosting/smear here is the 4DGS reconstruction itself (global-static baking of
moving objects, alpha_t fade), NOT closed-loop novel-view extrapolation.

Usage: render_dump_playback.py --dump <dump.pt> --out <dir> [--video <input.mp4>] [--fps 8]
Outputs: <out>/playback.mp4 (or playback_vs_input.mp4), + _strip.png
"""
import argparse, os, sys, numpy as np, torch, imageio.v2 as imageio
from PIL import Image
os.environ.setdefault("GS_WORLD_ROOT", os.path.expanduser("~/GS-World"))
sys.path.insert(0, os.environ["GS_WORLD_ROOT"])
from gs_world.simulation.dggt_render_backend import DGGTRenderBackend

ap = argparse.ArgumentParser()
ap.add_argument("--dump", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--video", default=None, help="original input mp4 for side-by-side GT")
ap.add_argument("--fps", type=int, default=8)
args = ap.parse_args()
os.makedirs(args.out, exist_ok=True)
DEV = "cuda"

be = DGGTRenderBackend(args.dump, metric_scale=1.0, device=DEV)
d = torch.load(args.dump, map_location=DEV, weights_only=False)
ext = d["cameras"]["extrinsic"].to(DEV).float()
K = d["cameras"]["intrinsic"].to(DEV).float()
N, H, W = ext.shape[0], be.H, be.W
print(f"[pb] N={N} H={H} W={W}", flush=True)

# optional: decode input video frames matched to the dump frames
gt = None
if args.video and os.path.exists(args.video):
    import cv2
    cap = cv2.VideoCapture(args.video); raw = []
    while True:
        ok, f = cap.read()
        if not ok: break
        raw.append(cv2.cvtColor(f, cv2.COLOR_BGR2RGB))
    cap.release()
    nT = len(raw)
    idx = np.unique(np.linspace(0, nT - 1, min(N, nT)).round().astype(int))
    gt = [np.asarray(Image.fromarray(raw[i]).resize((W, H), Image.BILINEAR)) for i in idx]
    print(f"[pb] input frames matched: {len(gt)} (video had {nT})", flush=True)

def label(img, txt):
    im = Image.fromarray(img).copy()
    from PIL import ImageDraw, ImageFont
    dr = ImageDraw.Draw(im)
    try: fnt = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 15)
    except Exception: fnt = ImageFont.load_default()
    dr.rectangle([0, 0, im.width, 22], fill=(0, 0, 0)); dr.text((6, 3), txt, font=fnt, fill=(120, 240, 160))
    return np.asarray(im)

frames = []
for i in range(N):
    r = np.asarray(be._render_w2c(ext[i], K[i], i))          # playback render at logged cam
    r = label(r, f"DGGT 4DGS render  ·  frame {i+1}/{N}")
    if gt is not None and i < len(gt):
        g = label(gt[i], "input video (GT)")
        frames.append(np.concatenate([g, r], axis=1))
    else:
        frames.append(r)

tag = "playback_vs_input" if gt is not None else "playback"
imageio.mimwrite(os.path.join(args.out, f"{tag}.mp4"), frames, fps=args.fps, quality=8)
ks = [0, N//4, N//2, 3*N//4, N-1]
imageio.imwrite(os.path.join(args.out, f"{tag}_strip.png"), np.concatenate([frames[k] for k in ks], axis=0))
print(f"[pb] wrote {tag}.mp4 ({N} frames) + strip", flush=True)
