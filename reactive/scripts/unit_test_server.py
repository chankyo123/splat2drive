import importlib.util, sys, numpy as np
sys.argv=['x']
spec=importlib.util.spec_from_file_location("srv","/home/ubuntu/splat2drive/server/server.py")
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
from alpasim_grpc.v0 import video_model_pb2 as vm
from alpasim_grpc.v0 import common_pb2 as cm

DUMP="/home/ubuntu/dggt/dumps/scene007/001_gaussians_dump.pt"
REF="/home/ubuntu/dggt/dumps/scene007/gt_ref_local.npy"
srv=m.DGGTWorldModelServicer(DUMP, 1.0, mode="reactive", clip_duration=20.0, ref_path=REF)

# start a session
class Spec:  # minimal camera_specs stand-in
    pass
sreq=vm.SessionRequest()
c=sreq.camera_specs.add(); c.logical_id="camera_front_wide_120fov"; c.resolution_h=srv.backend.H; c.resolution_w=srv.backend.W
sid=srv.start_session(sreq, None)
print("session:", sid.session_id)

def chunk_at(t_us, lateral_y):
    req=vm.VideoChunkRequest(); req.session_id.CopyFrom(sid)
    pa=req.rig_trajectory.poses.add()
    pa.timestamp_us=t_us
    # local frame: x=fwd, y=left, z=up ; put ego ~mid-clip forward, with lateral y
    pa.pose.vec.x=35.0; pa.pose.vec.y=lateral_y; pa.pose.vec.z=0.0
    pa.pose.quat.w=1.0
    return req

# same timestamp (=> same dggt frame j), different lateral -> frames must differ
base_t=9310000000
import hashlib
outs={}
for lat in [0.0, +2.0, -2.0]:
    r=srv.render_video_chunk(chunk_at(base_t, lat), None)
    b=r.camera_outputs[0].rgb_frames[0].data
    outs[lat]=b
    print(f"lateral={lat:+.1f}  jpeg_bytes={len(b)}  md5={hashlib.md5(b).hexdigest()[:10]}")
d02=outs[0.0]!=outs[2.0]; d0m2=outs[0.0]!=outs[-2.0]; d2m2=outs[2.0]!=outs[-2.0]
print(f"differ(0 vs +2)={d02}  differ(0 vs -2)={d0m2}  differ(+2 vs -2)={d2m2}")
assert d02 and d0m2 and d2m2, "FAIL: reactive did not change the frame with lateral"
print("UNIT TEST PASS: reactive frames respond to lateral offset")
