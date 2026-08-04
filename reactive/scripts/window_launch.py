import subprocess, time, re, sys, os
COMPOSE="/home/ubuntu/GS-World/submodules/alpasim_src/s007_reactive/docker-compose.yaml"
LOG="/tmp/claude-1000/-home-ubuntu/c0e8be85-6256-4a9e-b3bb-99e4fe1a24e1/scratchpad/reactive/alpamayo_win.log"
NEED=25000; TRIES=540  # ~3h at 20s
def gpu_free():
    out=subprocess.check_output(["nvidia-smi","--query-gpu=index,memory.free","--format=csv,noheader,nounits"]).decode()
    d={}
    for ln in out.strip().splitlines():
        i,f=[x.strip() for x in ln.split(",")]; d[int(i)]=int(f)
    return d
def patch_driver_gpu(gpu):
    lines=open(COMPOSE).read().split("\n"); out=[]; indrv=False; indev=False; done=False
    for l in lines:
        if l.strip()=="driver-0:": indrv=True
        if indrv and not done and "device_ids:" in l: indev=True; out.append(l); continue
        if indev and not done and re.match(r"\s*-\s*'?\d+'?\s*$", l):
            out.append(re.sub(r"'?\d+'?", f"'{gpu}'", l)); indev=False; done=True; indrv=False; continue
        out.append(l)
    open(COMPOSE,"w").write("\n".join(out))
for t in range(1,TRIES+1):
    free=gpu_free()
    cand={g:free.get(g,0) for g in (0,1,2)}
    gpu=max(cand,key=cand.get); f=cand[gpu]
    if f>=NEED:
        print(f"[win] try{t}: GPU{gpu} free={f}MiB >= {NEED} -> launching",flush=True)
        patch_driver_gpu(gpu)
        subprocess.run(["docker","compose","-f",COMPOSE,"down","--remove-orphans"],capture_output=True)
        with open(LOG,"w") as lf:
            subprocess.run(["docker","compose","-f",COMPOSE,"up","--abort-on-container-exit"],stdout=lf,stderr=subprocess.STDOUT)
        txt=open(LOG).read()
        oom="OutOfMemoryError" in txt or "CUDA out of memory" in txt
        fin="Alpasim finished" in txt
        if fin and not oom:
            print(f"[win] SUCCESS on GPU{gpu} at try{t}",flush=True); sys.exit(0)
        print(f"[win] try{t}: finished={fin} oom={oom} -> retry",flush=True)
    else:
        if t%15==1: print(f"[win] try{t}: best GPU{gpu} free={f}MiB < {NEED}, waiting...",flush=True)
    time.sleep(20)
print("[win] gave up after all tries",flush=True); sys.exit(2)
