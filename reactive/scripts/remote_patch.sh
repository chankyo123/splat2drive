#!/bin/bash
set -e
BASE=/home/ubuntu/GS-World/submodules/alpasim_src
C=$BASE/s007_reactive/docker-compose.yaml
# 1) context_length back to 4 (remote GPU is free, no mem pressure)
sed -i 's/^  context_length: 2/  context_length: 4/' $BASE/s007_reactive/driver-config.yaml || true
# 2) add HF_HUB_OFFLINE to driver env (keep expandable_segments)
python3 - <<'PY'
p="/home/ubuntu/GS-World/submodules/alpasim_src/s007_reactive/docker-compose.yaml"
s=open(p).read()
if "HF_HUB_OFFLINE" not in s:
    s=s.replace("      PYTORCH_CUDA_ALLOC_CONF: expandable_segments:True",
                "      PYTORCH_CUDA_ALLOC_CONF: expandable_segments:True\n      HF_HUB_OFFLINE: '1'",1)
open(p,"w").write(s)
print("HF_HUB_OFFLINE added:", "HF_HUB_OFFLINE" in s)
PY
echo "context_length:"; grep -n context_length $BASE/s007_reactive/driver-config.yaml
echo "driver device_ids + env:"; sed -n '27,52p' $C | grep -nE "device_ids|'[0-9]'|PYTORCH|HF_HUB|renderer"
echo "renderer target:"; grep -rn "10.150.0.126" $BASE/s007_reactive/*.yaml | head -1
