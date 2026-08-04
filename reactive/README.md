# Reactive closed-loop

Make the DGGT 4D-Gaussian world **react to the driving policy**. Plain playback
follows the reconstructed trajectory by time and ignores the policy's steering;
reactive mode keeps that longitudinal anchor but applies the policy's **lateral
deviation** as a real camera translation in the DGGT world — so the rendered
scene shifts when the policy nudges left/right.

The reactive server lives in [`../server/server.py`](../server/server.py)
(`--mode reactive`). This folder is the demo + the scripts that produced it.

Full write-up: [`reactive.html`](reactive.html) (self-contained; open locally).

## How reactive rendering works

```
policy pose (rig-local, x=fwd y=left z=up)
  ├─ longitudinal:  j = time -> frame        (same anchor as playback, verified)
  └─ lateral:       e = signed offset of the pose from the scene GT path
                        camera = extrinsic[j] translated by e/metric_scale along camera-left
                    -> gsplat renders that novel view from the 4DGS
```

- `e = 0` (on the reference path) reduces exactly to playback.
- `metric_scale = GT_arclength / DGGT_cam_arclength` (≈ 48.8 for scene007).
- Sign/scale verified three ways (see media below).

## Media

| file | what it shows |
| --- | --- |
| `media/mapping_verify_strip.png` | **verification** — `+2m LEFT` / `+2m RIGHT` shift the camera the correct opposite ways; `e=0` == playback |
| `media/reactive_vs_baseline.mp4` + `_strip.png` | **isolation** — same forward position, baseline (world ignores policy) vs reactive (world tracks the policy's real −1.87 m drift) |
| `media/reactive_progress_strip.png` | reactive render along the policy's real path (e: 0 → −1.87 m) |
| `media/live_reactive_overlay.mp4` | **live closed-loop** — Alpamayo driven closed-loop on a remote idle GPU, rendering from the reactive server; cam + reasoning + trajectory |
| `media/live_motion_strip.png` | live run start→end (ego drives forward) |
| `media/live_reasoning_frame.png` | a live reasoning + trajectory-prediction frame |

## Scripts (provenance)

Absolute paths inside these reflect the authoring machine — adapt for reuse.

| script | role |
| --- | --- |
| `scripts/extract_poses.py` | parse a rollout `.asl` → GT / requested / ego pose arrays (4-byte-BE-len + `LogEntry`) |
| `scripts/analyze.py` | pick the Pose→matrix convention; compute `metric_scale` from GT vs DGGT camera paths |
| `scripts/verify_map.py` | render playback / reactive / ±2 m to check sign + scale visually |
| `scripts/unit_test_server.py` | in-process: reactive frames must differ with lateral, reduce to playback at `e=0` |
| `scripts/render_client.py` | gRPC client: render the policy's real path reactive vs baseline |
| `scripts/run_reactive_server.sh` | launch the reactive DGGT server for a dump + ref path |
| `scripts/build_reactive_html.py` | rebuild `reactive.html` from `../media` |
| `scripts/window_launch.py` | (GPU-contended box) wait for a free GPU, then run the closed-loop |
| `scripts/remote_patch.sh` | patch a transferred compose for a remote idle-GPU box (driver→GPU, renderer→host, HF offline) |

## Run it

```bash
# 1) reactive server (needs a DGGT dump + the scene GT reference path, local x=fwd,y=left,z=up)
../server/run_server_generic.sh /path/to/dump.pt 3        # playback, or:
python -   # or launch server.py --mode reactive --ref_path gt_ref_local.npy   (see run_reactive_server.sh)

# 2) drive Alpamayo closed-loop against it (external_video_model) — see ../alpasim/run_s007_e2e.sh

# 3) rebuild the write-up
python scripts/build_reactive_html.py       # -> reactive.html
```

## Honest limits

- The **live run stayed near-center** (lateral ≤ 0.28 m), so its visible reactivity
  is subtle — the dramatic reactivity is the `reactive_vs_baseline` (policy's real
  −1.87 m path).
- Large lateral shifts render **novel views the single-traversal clip never
  observed** → smear. This is mostly a coverage/reconstruction-fidelity issue
  (feed-forward monocular DGGT degrades sooner than an optimized multi-view 3DGS),
  not a limitation of the render step itself. Diffusion refinement / denser
  reconstruction would help.
- Tier-0 scaffold: absolute metrics are illustrative, not a benchmark.
