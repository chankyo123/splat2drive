import sys, os, numpy as np, torch
import os as _os
sys.path.insert(0, _os.environ.get("GS_WORLD_ROOT", "/home/ubuntu/GS-World"))
from gs_world.simulation.dggt_render_backend import DGGTRenderBackend
import imageio.v2 as imageio
dump = sys.argv[1]; outdir = sys.argv[2]; ms = float(sys.argv[3]) if len(sys.argv)>3 else 1.0
os.makedirs(outdir, exist_ok=True)
be = DGGTRenderBackend(dump, metric_scale=ms, device='cuda')
d = torch.load(dump, map_location='cuda', weights_only=False)
ext = d['cameras']['extrinsic']; K = d['cameras']['intrinsic']
n = be.n_frames
def g(t, i): return t[i] if t.shape[0] > i else t[min(i, t.shape[0]-1)]
for i in range(n):
    img = be._render_w2c(g(ext,i).to('cuda').float(), g(K,i).to('cuda').float(), i)
    imageio.imwrite(os.path.join(outdir, f"f{i:03d}.png"), img)
    if i % 40 == 0: print(f"  {i}/{n}", flush=True)
print("done", outdir, flush=True)
