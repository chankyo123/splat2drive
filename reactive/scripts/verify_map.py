import numpy as np, torch, sys, os
sys.path.insert(0,"/home/ubuntu/GS-World")
from gs_world.simulation.dggt_render_backend import DGGTRenderBackend
from PIL import Image, ImageDraw
d=np.load(sys.argv[1]); DUMP=sys.argv[2]; OUT=sys.argv[3]
def quat2R(q):
    w,x,y,z=np.array(q)/ (np.linalg.norm(q)+1e-12)
    return np.array([[1-2*(y*y+z*z),2*(x*y-w*z),2*(x*z+w*y)],
                     [2*(x*y+w*z),1-2*(x*x+z*z),2*(y*z-w*x)],
                     [2*(x*z-w*y),2*(y*z+w*x),1-2*(x*x+y*y)]])
# reference path = GT centers (local: X fwd, Y left, Z up)
gt=d['gt_v']; ref=gt.copy()              # (M,3)
ref_xy=ref[:,:2]
seg=np.diff(ref,axis=0); seglen=np.linalg.norm(seg,axis=1)
arc=np.concatenate([[0],np.cumsum(seglen)]); L=arc[-1]
# requested path (what the policy actually drove) centers
req=d['req_v']                            # (K,3)
be=DGGTRenderBackend(DUMP,metric_scale=1.0,device='cuda')
ext=be.extrinsic.cpu().numpy().astype(np.float64); K=be.intrinsic
N=be.n_frames
# metric scale = GT arclength / DGGT cam arclength
cc=np.array([-(w[:3,:3].T@w[:3,3]) for w in ext]); cam_len=np.sum(np.linalg.norm(np.diff(cc,axis=0),axis=1))
MS=L/cam_len; print(f"L_gt={L:.2f} cam_len={cam_len:.3f} metric_scale={MS:.3f}",flush=True)

def nearest(p_xy):
    dd=np.sum((ref_xy-p_xy[None])**2,axis=1); i=int(np.argmin(dd)); return i
def frenet(p3):
    i=nearest(p3[:2])
    i2=min(i+1,len(ref)-1); i1=max(i2-1,0)
    tan=ref[i2,:2]-ref[i1,:2]; tan=tan/(np.linalg.norm(tan)+1e-9)
    left=np.array([-tan[1],tan[0]])              # +90deg = left
    e=float(np.dot(p3[:2]-ref[i,:2], left))      # signed lateral, left +
    up=float(p3[2]-ref[i,2])
    f=arc[i]/L                                    # fraction along clip
    return f,e,up
def reactive_w2c(p3, lateral_sign=-1.0):
    f,e,up=frenet(p3)
    j=int(round(max(0,min(1,f))*(N-1)))
    c2w=np.linalg.inv(ext[j])
    x_cam=c2w[:3,0]  # right
    # camera-left = -x_cam ; shift by e meters (left+) -> world units /MS
    shift = lateral_sign*(e/MS)*x_cam
    c2w=c2w.copy(); c2w[:3,3]=c2w[:3,3]+shift
    w2c=torch.from_numpy(np.linalg.inv(c2w)).to(be.device).float()
    return w2c,j,e
def render(w2c,j):
    return be._render_w2c(w2c, K[j], j)

# pick 3 frames along the drive; for each show: playback(ext[j]) | reactive(req pose) | req+2m LEFT | req+2m RIGHT
fracs=[0.25,0.5,0.75]
rows=[]
for fr in fracs:
    k=int(fr*(len(req)-1)); p=req[k].copy()
    f,e,up=frenet(p); j=int(round(f*(N-1)))
    imgs=[]
    # playback: raw ext[j]
    imgs.append(("playback j%d"%j, render(be.extrinsic[j].float(), j)))
    # reactive at policy's actual lateral
    w,jr,er=reactive_w2c(p); imgs.append(("reactive e=%.2f"%er, render(w,jr)))
    # +2m left, +2m right (add to lateral by moving p along local-left/right)
    i=nearest(p[:2]); i2=min(i+1,len(ref)-1); tan=ref[i2,:2]-ref[max(i2-1,0),:2]; tan/=np.linalg.norm(tan)+1e-9; left=np.array([-tan[1],tan[0]])
    pL=p.copy(); pL[:2]+=2.0*left; wL,jL,eL=reactive_w2c(pL); imgs.append(("+2m LEFT e=%.2f"%eL, render(wL,jL)))
    pR=p.copy(); pR[:2]-=2.0*left; wR,jR,eR=reactive_w2c(pR); imgs.append(("+2m RIGHT e=%.2f"%eR, render(wR,jR)))
    rows.append(imgs)
H,W=rows[0][0][1].shape[:2]; pad=20
canvas=Image.new("RGB",(W*4, (H+pad)*3),(12,14,18)); dr=ImageDraw.Draw(canvas)
for r,imgs in enumerate(rows):
    for c,(lab,im) in enumerate(imgs):
        canvas.paste(Image.fromarray(im),(c*W, r*(H+pad)+pad))
        dr.text((c*W+4, r*(H+pad)+4), lab, fill=(120,230,150))
canvas.save(OUT); print("saved",OUT,flush=True)
