#!/bin/bash
# run_server_generic.sh <dump.pt> <gpu>
# Launches the DGGT WorldModelService gRPC server on 0.0.0.0:50051.
#
# Requires the `dggt` conda env (GS-World + gsplat). The env vars below are the
# ones that made gsplat's JIT build succeed on an RTX PRO 6000 Blackwell (sm_120);
# adjust CUDA_HOME / paths for your machine.
set -euo pipefail
source /home/ubuntu/miniconda3/etc/profile.d/conda.sh && conda activate dggt
export CUDA_HOME=/home/ubuntu/miniconda3/envs/dggt PATH="$CUDA_HOME/bin:$PATH"
export CPATH=/home/ubuntu/miniconda3/envs/dggt/targets/x86_64-linux/include:${CPATH:-}
export TORCH_CUDA_ARCH_LIST="12.0" PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
export CUDA_VISIBLE_DEVICES=${2:-3}

DUMP="${1:?usage: run_server_generic.sh <dump.pt> <gpu>}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"
python server.py --dump "$DUMP" --metric_scale 1.0 --mode playback \
  --clip_duration 20.0 --host 0.0.0.0 --port 50051
