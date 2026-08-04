import numpy as np, torch, sys
d=np.load(sys.argv[1])
DUMP=sys.argv[2]
def quat2R(q):
    w,x,y,z=q; n=w*w+x*x+y*y+z*z
    if n<1e-9: return np.eye(3)
    w,x,y,z=np.array([w,x,y,z])/np.sqrt(n)
    return np.array([
      [1-2*(y*y+z*z), 2*(x*y-w*z),   2*(x*z+w*y)],
      [2*(x*y+w*z),   1-2*(x*x+z*z), 2*(y*z-w*x)],
      [2*(x*z-w*y),   2*(y*z+w*x),   1-2*(x*x+y*y)]])
def centers(v,q,mode):
    C=[]
    for vi,qi in zip(v,q):
        R=quat2R(qi)
        C.append(R@vi if mode=='tfirst' else vi)  # standard: origin maps to vec
    return np.array(C)
def plen(C): return float(np.sum(np.linalg.norm(np.diff(C,axis=0),axis=1)))
for name in ['gt','ego','req']:
    v=d[name+'_v']; q=d[name+'_q']
    if len(v)==0: continue
    Cs=centers(v,q,'std'); Ct=centers(v,q,'tfirst')
    print(f"{name}: N={len(v)} | std path_len={plen(Cs):.2f} span={Cs.max(0)-Cs.min(0)} "
          f"first={np.round(Cs[0],2)} last={np.round(Cs[-1],2)}")
    print(f"        tfirst path_len={plen(Ct):.2f} first={np.round(Ct[0],2)} last={np.round(Ct[-1],2)}")
    print(f"        |quat| range=[{np.linalg.norm(q,axis=1).min():.3f},{np.linalg.norm(q,axis=1).max():.3f}]")
# DGGT camera centers
dd=torch.load(DUMP,map_location='cpu',weights_only=False)
ext=dd['cameras']['extrinsic'].numpy().astype(np.float64)  # (N,4,4) world->cam
cc=np.array([-(w[:3,:3].T@w[:3,3]) for w in ext])
print(f"DGGT cam: N={len(cc)} path_len={plen(cc):.2f} span={cc.max(0)-cc.min(0)} first={np.round(cc[0],2)} last={np.round(cc[-1],2)}")
