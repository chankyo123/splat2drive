# Splat2Drive

### Closed-Loop Driving Inside Feed-Forward 4D-Gaussian Worlds

Drive **NVIDIA Alpamayo 1.5** closed-loop *inside* a **DGGT** feed-forward
4D-Gaussian reconstruction of a scene from the **Waymo Open Dataset** — with
**zero edits to AlpaSim core**. Reconstruct → render → drive, in the loop. The
ego actually drives a full San Francisco hill block over 20 s: stopping at a red
light and nudging past a bus, cones, and trash bags, all rendered from splats.

![hero](media/waymo_moving_hero.png)

> `t≈13 s` — **BEV (top-left):** the ego (green) advances along the GT route
> (orange), leaving a trail behind it. **Metrics:** `collision_at_fault 0.00`,
> `offroad 0.00`, lateral `dist_to_gt_trajectory 0.22` (stays in-lane).
> **Camera:** the reconstructed hill street, driven `STRAIGHT`.

---

## The result

An earlier run (Waymo *scene003*, an alley) *looked* static because the policy
correctly **stopped behind a stopped lead vehicle**. This run picks **scene007**
— an open SF hill street — so there is room to drive. The ego moves for the full
rollout. Motion is verified three independent ways:

| Evidence | Signal |
| --- | --- |
| **Frame differencing** | first-vs-last frame diff `28.7` vs consecutive `≈6.9` → ~4× cumulative displacement (not jitter) |
| **BEV trail** | ego leaves a growing trajectory behind it along the GT route |
| **Trajectory-prediction panel** | prediction extends **~38 m** longitudinally (near-zero when stopped) |

![motion strip](media/s007_motion_strip.png)

*Closed-loop camera at start · ¼ · ½ · ¾ · end — Mission Dolores basilica grows
in the distance as the ego advances.*

### Chain-of-thought (13 steps over 20 s)

The policy narrates decisions that reference objects **existing only in the DGGT
reconstruction** — direct evidence it is genuinely consuming the rendered 4DGS
frames:

1. Keep distance to the cut-in vehicle merging into our lane
2. Keep distance to the lead vehicle directly ahead
3. Keep lane — clear ahead
4. **Stop for the red traffic light**
5. **Nudge left** — cones blocking the right
6. **Nudge left** — stopped bus blocking the right
7. **Nudge right** — car encroaching from the left
8. Keep lane — clear
9. Keep distance to cut-in vehicle
10. **Nudge right** — vehicle encroaching from left
11. Keep distance to cut-in vehicle
12. **Nudge left** — trash bags blocking the right
13. Keep lane — clear

![reasoning timeline](media/reasoning_timeline.png)

### Videos
- [`media/waymo_moving_overlay.mp4`](media/waymo_moving_overlay.mp4) — camera + live reasoning + trajectory-prediction panel, real-time (20 s)
- [`media/waymo_moving_cam.mp4`](media/waymo_moving_cam.mp4) — clean camera only, no overlay

A self-contained visual write-up is in [`docs/index.html`](docs/index.html)
(everything base64-embedded; open it directly or serve via GitHub Pages).

---

## How it works

```
Waymo front camera frames
      │  (already pinhole — no undistort needed)
      ▼
DGGT  mode=3 --dump_gs           feed-forward, pose-free 4DGS
      │   → 001_gaussians_dump.pt (17.9M static gaussians, T=197)
      ▼
DGGTRenderBackend  (GS-World)    _render_w2c(w2c, K, frame_idx) → RGB
      │
      ▼
server/server.py                 gRPC WorldModelService (this repo)
      │   50051, playback mode: session-relative time → dump frame
      ▼
AlpaSim  deploy=external_video_model  driver=alpamayo1_5_1cam
      │   Docker containers reach the host server at its LAN IP
      ▼
Alpamayo 1.5 (10B)  closed-loop  sees splat frames, emits CoT + trajectory
```

The only new code is an **additive** gRPC server: a subclass of the generated
`WorldModelServiceServicer` implementing four methods
(`get_version` / `start_session` / `render_video_chunk` / `close_session`).
AlpaSim is otherwise stock.

**Key facts**
- **DGGT is pinhole-only** (pose encoding `absT_quaR_FoV`, no distortion term).
  Waymo is already pinhole, so no undistortion step is needed (unlike the NVIDIA
  f-theta NuRec scenes, which must be undistorted first).
- **Playback mode:** the render camera follows the dump's own logged trajectory,
  indexed by session-relative time. `--clip_duration 20.0` maps rollout time
  across *all* dump frames (without it the camera freezes early).
- **Timestamp anchoring:** AlpaSim's pose timestamps are absolute sim-epoch
  microseconds; the server anchors `t0` on the first pose of a session so the
  frame index advances smoothly (this fixed an earlier frozen-camera bug).

---

## Repository layout

```
server/
  server.py               DGGT WorldModelService gRPC server (the additive glue)
  run_server_generic.sh   launch the server:  run_server_generic.sh <dump.pt> <gpu>
render/
  render_full_playback.py render a dump along its logged camera → PNG frames
  sanity_generic.py       quick start/mid/end strip from a dump
alpasim/
  run_s007_e2e.sh         the AlpaSim closed-loop launch (external_video_model)
viz/
  build_waymo_moving_html.py  base64-embeds the media into docs/index.html
docs/
  index.html              self-contained visual write-up (published as an Artifact)
media/                    hero, motion strip, reasoning timeline, mp4s
```

---

## Reproduce

```bash
# 1) Build the DGGT 4DGS dump from Waymo front-camera frames (in the DGGT repo)
python inference.py mode=3 --dump_gs   # → 001_gaussians_dump.pt

# 2) Start the render server (host machine, dggt conda env)
server/run_server_generic.sh /path/to/scene007/001_gaussians_dump.pt 3
#   verify it answers before launching AlpaSim:
#   python -c "import grpc; from alpasim_grpc.v0 import video_model_pb2_grpc as g, common_pb2 as c; \
#     print(g.WorldModelServiceStub(grpc.insecure_channel('HOST:50051')).get_version(c.Empty()))"

# 3) Run Alpamayo closed-loop against it (AlpaSim repo)
#    edit the renderer IP in alpasim/run_s007_e2e.sh to the host's LAN IP
bash alpasim/run_s007_e2e.sh

# 4) Rebuild the write-up page
python viz/build_waymo_moving_html.py   # → docs/index.html
```

---

## Caveats (Tier-0)

- **This proves the plumbing + perception, not a benchmark score.** The
  map / GT / actor scaffold is a stand-in that does not exactly match this scene,
  so **absolute metrics are not meaningful** — the point is that the policy
  perceives reconstruction-only objects and drives coherently.
- `collision_any 1.00` is a *rear* event and **not at fault** (`collision_at_fault 0.00`).
- `dist_to_gt_location` (5.65) grows from speed/timing offset; lateral
  `dist_to_gt_trajectory` (0.22) stays tight — it followed the lane.
- The server renders **pinhole**; Alpamayo nominally expects f-theta. The
  intrinsic mismatch is tolerable for perception here; matching it (gsplat
  `ftheta_coeffs` on output) is future work.
- **DGGT recon quality tracks ego baseline** — moving scenes reconstruct well;
  dense stop-and-go (low parallax) reconstructs poorly.

---

## Environment notes

- Server runs in a `dggt` conda env (GS-World + gsplat). gsplat JIT build on an
  RTX PRO 6000 Blackwell needs `TORCH_CUDA_ARCH_LIST=12.0` and
  `CPATH=$CUDA_HOME/targets/x86_64-linux/include` (see `run_server_generic.sh`).
- AlpaSim Docker containers reach the host server via the host's **LAN IP**
  (not `localhost`).
- Wait for the server to finish `torch.load` (large dump) and answer
  `get_version` before launching AlpaSim, or the runtime probe hits
  `DEADLINE_EXCEEDED`.

*Alpamayo 1.5 is NVIDIA's; AlpaSim is NVlabs'; DGGT and GS-World are their
respective authors'. This repo is the integration glue + write-up only.*
