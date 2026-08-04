"""Rolling-window + single-field (holefill) render backend — drop-in for
DGGTRenderBackend. Renders the DA3 feed-forward field handed off in a
`N01_112m_field/` dir (manifest + 35 window PLYs + single_field PLY + traj/K/
profile). No DGGT, no per-scene optimisation.

Two layers, composited exactly as the hand-off's holefill:
  im_w, al_w = raster(window_for(arclength), pose, K)   # sharp, ~1.5M, swapped by distance
  im_s, al_s = raster(single_field,          pose, K)   # fill, 31.1M, resident
  out = im_w * (al_w>0.5) + im_s * (1-(al_w>0.5))

Exposes the same surface server.py uses on DGGTRenderBackend: .n_frames, .H, .W,
.ext (w2c, N×4×4), .K (N×3×3), .real_duration_s, ._render_w2c(w2c,K,idx),
._sim_t_to_dggt_frame(t).

PLY layout (14 float32, binary_little_endian): [0:3] means, [3:6] SH-DC colour
(*0.28209+0.5), [6] opacity logit (sigmoid), [7:10] log-scale (exp), [10:14] quat.
Camera per frame: R = w2c[i].R^T, C = raw[0] + unit(raw[i]-raw[0]) * dist[i]
(direction from the raw npz path, magnitude from profile.json metric arclength).
"""
import json, os, numpy as np, torch

SH0 = 0.28209479177387814


class WindowFieldBackend:
    def __init__(self, field_dir, device="cuda", clip_duration=None, holefill=True,
                 traj="traj_N_0.1556_T481.npz", single="N01_112m_single_field.ply",
                 win_cache=3):
        from gsplat.rendering import rasterization
        self._raster = rasterization
        self.device = torch.device(device)
        self.dir = field_dir
        self.holefill = bool(holefill)
        self.win_cache = int(win_cache)

        man = json.load(open(os.path.join(field_dir, "manifest.json")))
        self.H, self.W = int(man["res"][0]), int(man["res"][1])
        self.windows = man["windows"]
        self.anchors = np.array([w["anchor_m"] for w in self.windows], dtype=np.float64)

        tr = np.load(os.path.join(field_dir, traj))
        w2c = tr["w2c"].astype(np.float64)
        self.n_frames = w2c.shape[0]
        Rwc = np.stack([w2c[i, :3, :3].T for i in range(self.n_frames)])
        raw = np.stack([-w2c[i, :3, :3].T @ w2c[i, :3, 3] for i in range(self.n_frames)])
        dist = np.asarray(json.load(open(os.path.join(field_dir, "profile.json")))["dist"],
                          np.float64)[:self.n_frames]
        self.dist = dist
        s = np.linalg.norm(raw - raw[0], axis=1)
        u = np.where(s[:, None] > 1e-9, (raw - raw[0]) / np.maximum(s[:, None], 1e-9),
                     np.array([0.0, 0.0, 1.0]))
        Cen = raw[0] + u * dist[:, None]
        ext = np.zeros((self.n_frames, 4, 4))
        for i in range(self.n_frames):
            c2w = np.eye(4); c2w[:3, :3] = Rwc[i]; c2w[:3, 3] = Cen[i]
            ext[i] = np.linalg.inv(c2w)
        self.ext = torch.tensor(ext, dtype=torch.float32, device=self.device)
        self.ext_np = ext
        Kz = np.load(os.path.join(field_dir, "per_frame_K.npz"))
        self.K = torch.tensor(Kz["K"], dtype=torch.float32, device=self.device)
        self.intrinsic = self.K
        self.real_duration_s = float(clip_duration) if clip_duration else self.n_frames / 16.0

        self._wcache = {}
        self.single = self._load_ply(os.path.join(field_dir, single)) if self.holefill else None
        print(f"[WindowField] n_frames={self.n_frames} H={self.H} W={self.W} "
              f"windows={len(self.windows)} dist=0->{self.dist[-1]:.1f}m holefill={self.holefill} "
              f"single={'31M resident' if self.single else 'off'}", flush=True)

    def _load_ply(self, path):
        with open(path, "rb") as f:
            n, props = 0, []
            while True:
                t = f.readline().decode(errors="replace").strip()
                if t.startswith("element vertex"): n = int(t.split()[-1])
                elif t.startswith("property float"): props.append(t.split()[-1])
                elif t == "end_header": break
            assert len(props) == 14, f"expected 14 props, got {len(props)}"
            arr = np.frombuffer(f.read(n * 14 * 4), dtype="<f4").reshape(n, 14)
        T = lambda x: torch.tensor(np.ascontiguousarray(x), dtype=torch.float32, device=self.device)
        return (T(arr[:, 0:3]), T(arr[:, 10:14]), torch.exp(T(arr[:, 7:10])),
                torch.sigmoid(T(arr[:, 6])), (T(arr[:, 3:6]) * SH0 + 0.5).clamp(0, 1))

    def _window_for(self, idx):
        d = float(self.dist[int(np.clip(idx, 0, self.n_frames - 1))])
        j = max(0, int(np.searchsorted(self.anchors, d, side="right") - 1))  # largest anchor <= d, clamp first
        f = self.windows[j]["file"]
        if f not in self._wcache:
            if len(self._wcache) >= self.win_cache:
                self._wcache.pop(next(iter(self._wcache)))
            self._wcache[f] = self._load_ply(os.path.join(self.dir, f))
        return self._wcache[f]

    def _raster_one(self, g, w2c, K):
        out, al, _ = self._raster(*[t.contiguous() for t in g], w2c[None], K[None], self.W, self.H,
                                  near_plane=0.1, far_plane=400.0, render_mode="RGB")
        return out[0].clamp(0, 1), al[0, ..., 0]

    def _render_w2c(self, w2c, K, frame_idx):
        idx = int(max(0, min(self.n_frames - 1, frame_idx)))
        w2c = w2c.to(self.device).float(); K = K.to(self.device).float()
        im_w, al_w = self._raster_one(self._window_for(idx), w2c, K)
        if self.single is not None:
            im_s, _ = self._raster_one(self.single, w2c, K)
            m = (al_w > 0.5).float()[..., None]
            im = im_w * m + im_s * (1 - m)
        else:
            im = im_w
        return (im.clamp(0, 1) * 255).to(torch.uint8).cpu().numpy()

    def _sim_t_to_dggt_frame(self, sim_t):
        frac = max(0.0, min(1.0, sim_t / max(self.real_duration_s, 1e-6)))
        return int(round(frac * (self.n_frames - 1)))
