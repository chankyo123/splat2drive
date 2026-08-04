# workspace/ — local working data (not tracked by git)

Everything the pipeline reads or writes lives here so the repo root stays clean
and nothing large ever gets committed. Only this README and the two `.gitkeep`
placeholders are tracked; all actual videos/dumps/renders are git-ignored (see
[`../.gitignore`](../.gitignore)).

```
workspace/
├── inputs/    drop new videos to test here          (contents ignored)
└── results/   generated dumps, rollouts, renders     (contents ignored)
```

## Test a new video (end-to-end)

> All GPU inference runs on the **remote box only** (2× Blackwell); the local box
> GPUs are reserved. Below, `RENV` = the remote dggt env + CUDA build flags
> (see `../server/start_render_server.sh` for the exact exports).

1. Drop an `.mp4` into `inputs/`.
2. **Reconstruct** a DGGT 4D-Gaussian world straight from the clip (no dataset
   layout needed):
   `python dggt_frames_to_dump.py inputs/<clip>.mp4 results/<name>_dump.pt <max_frames>`
3. **Reactive render** (world reacts to steering — sweep + baseline-vs-reactive):
   `python ../reactive/scripts/reactive_demo.py --dump results/<name>_dump.pt --out results/<name>_reactive`
4. **Alpamayo closed-loop**: start the render server on the box pointed at the
   dump (`../server/start_render_server.sh results/<name>_dump.pt <gpu> playback`),
   set the AlpaSim `generated-network-config.yaml` renderer to `localhost:50051`,
   then `docker compose up runtime-0`. It writes a `rollout.asl`.
5. **Overlay** the rollout (world + reasoning + predicted trajectory):
   `python ../reactive/scripts/build_cle_overlay.py <rollout.asl> results/<name>_cle <name>`
6. **Report**: `python ../reactive/scripts/build_results_html.py` → `results/new_videos_results.html`.

## What's already here

Two clips have been run end-to-end (open `results/new_videos_results.html`):

| clip | DGGT world | Alpamayo closed-loop |
| --- | --- | --- |
| `waymo_real` (real Waymo, 40 f) | 6.9 M gaussians | 66 reasoning steps, at-fault 0, on-route 0.18 m — stops for stop-sign, yields to pedestrians |
| `gen112` (generated, 140 f) | 25.3 M gaussians | 66 reasoning steps, at-fault 0, on-route 0.14 m — lane-keeps, plans a right lane-change into the curve |

Media per clip: `<name>_reactive/` (sweep + reactive_vs_baseline) and
`<name>_cle/` (overlay mp4 + motion strip + reasoning frame + metrics).
`collision_rear=1.0` in both is the shared s007 scenario's background traffic
(Tier-0), not the clip. Also here: the earlier durable reactive run
(`live_rollout.asl` ~700 MB, `reactive.html`). Committed lean demo copies live
under [`../reactive/media`](../reactive/media).
