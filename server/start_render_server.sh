#!/bin/bash
# $1 = dump path, $2 = gpu (default 1), $3 = mode (default playback)
DUMP=$1; GPU=${2:-1}; MODE=${3:-playback}
export CUDA_HOME=$HOME/miniconda3/envs/dggt
export PATH=$HOME/miniconda3/envs/dggt/bin:$PATH
export CPATH=$HOME/miniconda3/envs/dggt/targets/x86_64-linux/include
export TORCH_CUDA_ARCH_LIST=12.0
export CUDA_VISIBLE_DEVICES=$GPU
export GS_WORLD_ROOT=$HOME/GS-World
export PYTHONPATH=$HOME/dggt:$HOME/GS-World:$HOME/GS-World/submodules/alpasim_src/src/grpc
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
cd $HOME/splat2drive/server
exec $HOME/miniconda3/envs/dggt/bin/python server.py \
  --dump "$DUMP" --mode "$MODE" --clip_duration 20.0 \
  --ref_path $HOME/splat2drive/workspace/results/gt_ref_local.npy \
  --host 0.0.0.0 --port 50051
