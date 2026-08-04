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

## Test a new video

1. Drop an `.mp4` into `inputs/`.
2. Extract frames → DGGT layout `<scene>/images/<frame>_0.png` (view 0 = front).
3. `inference.py --mode 3 --dump_gs` → a `*_gaussians_dump.pt` in `results/`.
4. Point the render server at that dump
   (`../server/run_server_generic.sh results/<scene>_dump.pt 3`), optionally
   drive Alpamayo closed-loop against it (`../alpasim/`).

## What's already here

`results/` currently holds the full durable reactive run (moved out of the old
`~/reactive_results`): `live_rollout.asl` (~700 MB), the raw + overlay live
videos, `reactive_vs_baseline.mp4`, the verification strips, and a standalone
`reactive.html`. The **lean, committed** copies of the demo media live under
[`../reactive/media`](../reactive/media) — this folder is the heavy originals.
