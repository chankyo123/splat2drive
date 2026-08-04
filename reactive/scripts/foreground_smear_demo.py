"""Show foreground smear: at ONE scene moment, render the DGGT world from the
original camera and from cameras pushed progressively FORWARD along the drive
direction (novel views the single traversal never observed). Crop the bottom
(foreground road / near cars) of each — that region melts as you move into
unobserved space, while distant background holds. Isolates the coverage/novel-
view smear (no time change -> no dynamic ghosting confound).

Usage: foreground_smear_demo.py --dump <dump.pt> --out <dir> [--idx -1] [--fracs 0,0.3,0.6,1.0]
"""
import argparse, os, sys, numpy as np, torch, imageio.v2 as imageio
from PIL import Image, ImageDraw, ImageFont
os.environ.setdefault("GS_WORLD_ROOT", os.path.expanduser("~/GS-World"))
sys.path.insert(0, os.environ["GS_WORLD_ROOT"])
from gs_world.simulation.dggt_render_backend import DGGTRenderBackend

ap = argparse.ArgumentParser()
ap.add_argument("--dump", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--idx", type=int, default=-1, help="scene frame to hold (default mid)")
ap.add_argument("--fracs", default="0,0.3,0.6,1.0", help="forward push as fraction of fwd path len")
args = ap.parse_args()
os.makedirs(args.out, exist_ok=True)
DEV = "cuda"

be = DGGTRenderBackend(args.dump, metric_scale=1.0, device=DEV)
d = torch.load(args.dump, map_location=DEV, weights_only=False)
ext = d["cameras"]["extrinsic"].to(DEV).float()
K = d["cameras"]["intrinsic"].to(DEV).float()
ext_np = ext.cpu().numpy().astype(np.float64)
N, H, W = ext_np.shape[0], be.H, be.W
idx = args.idx if args.idx >= 0 else N // 2
cc = np.array([-(w[:3, :3].T @ w[:3, 3]) for w in ext_np])
fwd_len = float(np.sum(np.linalg.norm(np.diff(cc, axis=0), axis=1)))
d_hat = (cc[-1] - cc[0]); d_hat = d_hat / (np.linalg.norm(d_hat) + 1e-9)   # drive direction
fracs = [float(x) for x in args.fracs.split(",")]
print(f"[fg] N={N} idx={idx} H={H} W={W} fwd_len={fwd_len:.3f} pushes={fracs}", flush=True)

def render_push(dist):
    c2w = np.linalg.inv(ext_np[idx]).copy()
    c2w[:3, 3] += dist * d_hat                     # move camera center forward along the drive
    w2c = torch.from_numpy(np.linalg.inv(c2w)).to(DEV).float()
    return np.asarray(be._render_w2c(w2c, K[idx], idx))

def lab(img, txt, color=(120, 240, 160)):
    im = Image.fromarray(img).copy(); dr = ImageDraw.Draw(im)
    try: f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 15)
    except Exception: f = ImageFont.load_default()
    dr.rectangle([0, 0, im.width, 22], fill=(0, 0, 0)); dr.text((6, 3), txt, font=f, fill=color)
    return np.asarray(im)

full, crops = [], []
y0 = int(0.52 * H)                                 # foreground = bottom ~48%
for fr in fracs:
    r = render_push(fr * fwd_len)
    tag = "original camera" if fr == 0 else f"pushed forward +{fr:.2f}x path"
    full.append(lab(r, tag))
    crops.append(lab(r[y0:H].copy(), f"FOREGROUND crop  ·  {tag}", color=(255, 200, 120)))

imageio.imwrite(os.path.join(args.out, "fg_full_row.png"), np.concatenate(full, axis=1))
imageio.imwrite(os.path.join(args.out, "fg_crops.png"), np.concatenate(crops, axis=0))
# upscale the crops 2x for visibility
big = Image.fromarray(np.concatenate(crops, axis=0))
big = big.resize((big.width * 2, big.height * 2), Image.NEAREST)
big.save(os.path.join(args.out, "fg_crops_2x.png"))
print(f"[fg] wrote fg_full_row.png, fg_crops.png, fg_crops_2x.png", flush=True)
