import struct, sys, numpy as np
from alpasim_grpc.v0.logging_pb2 import LogEntry
asl = sys.argv[1]; out = sys.argv[2]
def pose_to_vq(p):
    return ([p.vec.x,p.vec.y,p.vec.z],[p.quat.w,p.quat.x,p.quat.y,p.quat.z])
gt_v=[]; gt_q=[]; gt_t=[]
req_v=[]; req_q=[]; req_t=[]
ego_v=[]; ego_q=[]; ego_t=[]
n=0
with open(asl,'rb') as f:
    while True:
        hdr=f.read(4)
        if len(hdr)<4: break
        (sz,)=struct.unpack('>L',hdr)
        buf=f.read(sz)
        e=LogEntry(); e.ParseFromString(buf); n+=1
        w=e.WhichOneof('log_entry')
        if w=='rollout_metadata':
            tr=e.rollout_metadata.ego_rig_recorded_ground_truth_trajectory
            for pa in tr.poses:
                v,q=pose_to_vq(pa.pose); gt_v.append(v); gt_q.append(q); gt_t.append(pa.timestamp_us)
        elif w=='video_model_chunk_request':
            for pa in e.video_model_chunk_request.rig_trajectory.poses:
                v,q=pose_to_vq(pa.pose); req_v.append(v); req_q.append(q); req_t.append(pa.timestamp_us)
        elif w=='actor_poses':
            ap=e.actor_poses
            if ap.actor_poses:
                ego=ap.actor_poses[0]  # ego at index 0
                v,q=pose_to_vq(ego.actor_pose); ego_v.append(v); ego_q.append(q); ego_t.append(ap.timestamp_us)
np.savez(out,
  gt_v=np.array(gt_v),gt_q=np.array(gt_q),gt_t=np.array(gt_t,dtype=np.int64),
  req_v=np.array(req_v),req_q=np.array(req_q),req_t=np.array(req_t,dtype=np.int64),
  ego_v=np.array(ego_v),ego_q=np.array(ego_q),ego_t=np.array(ego_t,dtype=np.int64))
print(f"entries={n}  gt={len(gt_v)}  req={len(req_v)}  ego={len(ego_v)}")
