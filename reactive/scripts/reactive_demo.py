"""Self-contained reactive render demo for ANY DGGT dump (no AlpaSim needed).

Given a dump built from a single video, this shows the 4DGS world REACTING to a
lateral steering deviation:
  (A) lateral_sweep_strip.png     : at a mid frame, camera shifted L..0..R -> the
                                    world slides the correct opposite ways; delta=0
                                    reproduces the reconstructed view exactly.
  (B) reactive_vs_baseline.mp4    : baseline (camera on the reconstructed path) vs
      + _strip.png                  reactive (camera additionally drifts left over
                                    the clip) side by side.

Lateral shift is done in DGGT camera units (delta along the camera-right axis),
sized as a fraction of the clip's forward path length so it's visible but not
extreme. This is the same camera transform server.py uses in --mode reactive,
minus the metric_scale (which needs a GT metric path we don't have per-video).

Usage: reactive_demo.py --dump <dump.pt> --out <dir> [--frac 0.04] [--fps 10]
"""
import argparse, os, sys, numpy as np, torch, imageio.v2 as imageio
os.environ.setdefault("GS_WORLD_ROOT", os.path.expanduser("~/GS-World"))
sys.path.insert(0, os.environ["GS_WORLD_ROOT"])
from gs_world.simulation.dggt_render_backend import DGGTRenderBackend

ap = argparse.ArgumentParser()
ap.add_argument("--dump", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--frac", type=float, default=0.04, help="sweep amplitude as fraction of fwd path len")
ap.add_argument("--fps", type=int, default=10)
args = ap.parse_args()
os.makedirs(args.out, exist_ok=True)
DEV = "cuda"

be = DGGTRenderBackend(args.dump, metric_scale=1.0, device=DEV)
d = torch.load(args.dump, map_location=DEV, weights_only=False)
ext = d["cameras"]["extrinsic"].to(DEV).float()        # (N,4,4) world->cam
K = d["cameras"]["intrinsic"].to(DEV).float()
ext_np = ext.cpu().numpy().astype(np.float64)
N = ext_np.shape[0]
cc = np.array([-(w[:3, :3].T @ w[:3, 3]) for w in ext_np])            # cam centers (world)
fwd_len = float(np.sum(np.linalg.norm(np.diff(cc, axis=0), axis=1)))
Delta = args.frac * fwd_len
print(f"[demo] N={N} H={be.H} W={be.W} fwd_len={fwd_len:.3f}u  sweep Delta={Delta:.4f}u", flush=True)

def w2c_shift(idx, delta):    # +delta = shift camera RIGHT (world) by delta DGGT units
    c2w = np.linalg.inv(ext_np[idx]).copy()
    c2w[:3, 3] += delta * c2w[:3, 0]
    return torch.from_numpy(np.linalg.inv(c2w)).to(DEV).float()

def render(idx, delta):
    return np.asarray(be._render_w2c(w2c_shift(idx, delta), K[idx], idx))

# (A) lateral sweep at mid frame: L .. center .. R
mid = N // 2
strip = [render(mid, dl) for dl in (-Delta, -Delta/2, 0.0, Delta/2, Delta)]
imageio.imwrite(os.path.join(args.out, "lateral_sweep_strip.png"), np.concatenate(strip, axis=1))
print("[demo] wrote lateral_sweep_strip.png", flush=True)

# (B) baseline vs reactive left-drift over the clip
frames = []
for i in range(N):
    base = render(i, 0.0)
    reac = render(i, -Delta * (i / max(N - 1, 1)))   # drift left, ramping to -Delta
    frames.append(np.concatenate([base, reac], axis=1))
imageio.mimwrite(os.path.join(args.out, "reactive_vs_baseline.mp4"), frames, fps=args.fps, quality=8)
ks = [0, N // 4, N // 2, (3 * N) // 4, N - 1]
imageio.imwrite(os.path.join(args.out, "reactive_vs_baseline_strip.png"),
                np.concatenate([frames[k] for k in ks], axis=0))
print(f"[demo] wrote reactive_vs_baseline.mp4 ({N} frames) + strip", flush=True)
