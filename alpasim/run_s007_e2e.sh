#!/usr/bin/env bash
# Alpamayo 1.5 closed-loop against the DGGT render server (external_video_model).
#
# Set these for your machine:
#   ALPASIM_DIR    path to the alpasim checkout (has alpasim_wizard)
#   RENDERER_HOST  host:port the Docker driver can reach the render server at
#                  (the HOST's LAN IP, not localhost — the driver runs in a container)
#   CHECKPOINT     path to the Alpamayo-1.5-10B checkpoint
set -euo pipefail
ALPASIM_DIR="${ALPASIM_DIR:?set ALPASIM_DIR to your alpasim checkout}"
RENDERER_HOST="${RENDERER_HOST:-RENDER_HOST:50051}"
CHECKPOINT="${CHECKPOINT:?set CHECKPOINT to the Alpamayo-1.5-10B path}"
SCENE="${SCENE:-clipgt-01d503d4-449b-46fc-8d78-9085e70d3554}"

cd "$ALPASIM_DIR"
export PATH="$HOME/.local/bin:$PATH"; export HF_HOME="${HF_HOME:-$HOME/.cache/huggingface}"
uv run alpasim_wizard deploy=external_video_model topology=1gpu \
  driver=alpamayo1_5_1cam +chunking=8frame \
  driver.model.checkpoint_path="$CHECKPOINT" \
  "wizard.external_services.renderer=[\"$RENDERER_HOST\"]" \
  "scenes.scene_ids=['$SCENE']" \
  eval.video.video_layouts=[DEFAULT,REASONING_OVERLAY] \
  wizard.log_dir="$PWD/s007_e2e"
