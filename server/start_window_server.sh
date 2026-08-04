#!/bin/bash
# Launch the DA3 rolling-window + holefill render server on the box.
# $1 = field_dir (handoff N01_112m_field), $2 = gpu (default 1), $3 = clip_duration s (default 20)
FIELD=${1:?field_dir required}; GPU=${2:-1}; DUR=${3:-20.0}
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
  --backend window --field_dir "$FIELD" --mode playback \
  --clip_duration "$DUR" --host 0.0.0.0 --port 50051
