import sys,numpy as np,torch
import os as _os
sys.path.insert(0, _os.environ.get("GS_WORLD_ROOT", "/home/ubuntu/GS-World"))
from gs_world.simulation.dggt_render_backend import DGGTRenderBackend
from PIL import Image,ImageDraw
dp=sys.argv[1]; out=sys.argv[2]; name=sys.argv[3]
d=torch.load(dp,map_location='cpu',weights_only=False); be=DGGTRenderBackend(dp,metric_scale=1.0,device='cuda')
ext=d['cameras']['extrinsic'].float();K=d['cameras']['intrinsic'].float()
ims=[]
for f,n in [(0.0,'start'),(0.5,'mid'),(0.99,'end')]:
    i=int(f*(be.n_frames-1)); ims.append((n,be._render_w2c(ext[i].cuda(),K[i].cuda(),i)))
w=ims[0][1].shape[1];h=ims[0][1].shape[0];g=Image.new("RGB",(w*3,h+18),(15,18,22));dr=ImageDraw.Draw(g)
for k,(n,im) in enumerate(ims): g.paste(Image.fromarray(im),(k*w,18));dr.text((k*w+4,3),f"{name} {n}",fill=(120,230,150))
g.save(out);print("saved",out,be.n_frames)
