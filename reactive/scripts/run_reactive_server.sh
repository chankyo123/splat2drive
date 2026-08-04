#!/bin/bash
source /home/ubuntu/miniconda3/etc/profile.d/conda.sh && conda activate dggt
export GS_WORLD_ROOT=/home/ubuntu/GS-World
export CUDA_HOME=/home/ubuntu/miniconda3/envs/dggt PATH="$CUDA_HOME/bin:$PATH"
export CPATH=/home/ubuntu/miniconda3/envs/dggt/targets/x86_64-linux/include:${CPATH:-}
export TORCH_CUDA_ARCH_LIST="12.0" PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
export CUDA_VISIBLE_DEVICES=${1:-3}
cd /home/ubuntu/splat2drive/server
exec python server.py --dump /home/ubuntu/dggt/dumps/scene007/001_gaussians_dump.pt \
  --mode reactive --ref_path /home/ubuntu/dggt/dumps/scene007/gt_ref_local.npy \
  --metric_scale 1.0 --clip_duration 20.0 --host 0.0.0.0 --port 50051
