import grpc, numpy as np, sys, io
from alpasim_grpc.v0 import video_model_pb2 as vm
from alpasim_grpc.v0 import common_pb2 as cm
from PIL import Image
d=np.load(sys.argv[1]); mode=sys.argv[2]; outdir=sys.argv[3]
import os; os.makedirs(outdir,exist_ok=True)
gt=d['gt_v'].astype(np.float64); gt_xy=gt[:,:2]
V=d['req_v'].astype(np.float64); Q=d['req_q'].astype(np.float64); T=d['req_t'].astype(np.int64)
if mode=='baseline':  # project each pose onto GT path -> lateral 0 (== playback)
    for k in range(len(V)):
        i=int(np.argmin(np.sum((gt_xy-V[k,:2])**2,axis=1))); V[k]=gt[i]
ch=grpc.insecure_channel('10.150.0.126:50051',options=[('grpc.max_receive_message_length',256*1024*1024)])
stub=vm.WorldModelServiceStub if hasattr(vm,'WorldModelServiceStub') else None
from alpasim_grpc.v0 import video_model_pb2_grpc as vmg
stub=vmg.WorldModelServiceStub(ch)
sreq=vm.SessionRequest(); c=sreq.camera_specs.add(); c.logical_id="camera_front_wide_120fov"; c.resolution_h=350; c.resolution_w=518
sid=stub.start_session(sreq,timeout=30)
frames=[]; CH=8
for s in range(0,len(V),CH):
    req=vm.VideoChunkRequest(); req.session_id.CopyFrom(sid)
    for k in range(s,min(s+CH,len(V))):
        pa=req.rig_trajectory.poses.add()
        pa.timestamp_us=int(T[k])
        pa.pose.vec.x,pa.pose.vec.y,pa.pose.vec.z=float(V[k,0]),float(V[k,1]),float(V[k,2])
        pa.pose.quat.w,pa.pose.quat.x,pa.pose.quat.y,pa.pose.quat.z=[float(x) for x in Q[k]]
    r=stub.render_video_chunk(req,timeout=120)
    for fr in r.camera_outputs[0].rgb_frames:
        frames.append(fr.data)
print(f"{mode}: {len(frames)} frames",flush=True)
for i,b in enumerate(frames):
    Image.open(io.BytesIO(b)).save(os.path.join(outdir,f"f{i:04d}.png"))
print("saved to",outdir,flush=True)
