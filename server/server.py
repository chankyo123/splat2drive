"""DGGT WorldModelService gRPC server.

Wraps GS-World DGGTRenderBackend so AlpaSim's `deploy=external_video_model` can
render frames from a DGGT 4DGS dump. Playback mode: the camera follows the
dump's own logged trajectory, indexed by session-relative time (timestamp->frame).
"""
import argparse, io, sys, time
from concurrent import futures
import numpy as np, torch
from PIL import Image as PILImage
import grpc

import os as _os
sys.path.insert(0, _os.environ.get("GS_WORLD_ROOT", "/home/ubuntu/GS-World"))
from alpasim_grpc.v0 import video_model_pb2 as vm
from alpasim_grpc.v0 import video_model_pb2_grpc as vmg
from alpasim_grpc.v0 import common_pb2 as cm
from gs_world.simulation.dggt_render_backend import DGGTRenderBackend


class DGGTWorldModelServicer(vmg.WorldModelServiceServicer):
    def __init__(self, dump_path, metric_scale, mode="playback", device="cuda", clip_duration=None):
        print(f"[server] loading DGGT backend: {dump_path} (metric_scale={metric_scale}, mode={mode})", flush=True)
        self.backend = DGGTRenderBackend(dump_path, metric_scale=metric_scale, device=device)
        if clip_duration:
            self.backend.real_duration_s = float(clip_duration)
            print(f"[server] clip_duration override -> {clip_duration}s (dump spans full rollout)", flush=True)
        d = torch.load(dump_path, map_location=device, weights_only=False)
        self.ext = d['cameras']['extrinsic'].to(device).float()
        self.K = d['cameras']['intrinsic'].to(device).float()
        self.device = device
        self.sessions = {}
        self._sid = 0
        print(f"[server] backend ready: n_frames={self.backend.n_frames} "
              f"H={self.backend.H} W={self.backend.W} dur={self.backend.real_duration_s:.1f}s", flush=True)

    def get_version(self, request, context):
        return cm.VersionId(version_id="dggt-wms-0.1", git_hash="n/a")

    def start_session(self, request, context):
        self._sid += 1
        sid = f"dggt-{int(time.time()*1000)}-{self._sid}"
        cams = [(c.logical_id, int(c.resolution_h), int(c.resolution_w)) for c in request.camera_specs]
        if not cams:
            cams = [("camera_front_wide_120fov", self.backend.H, self.backend.W)]
        self.sessions[sid] = {"cams": cams, "t0_us": None}
        print(f"[server] start_session {sid}: cams={[c[0] for c in cams]}", flush=True)
        return vm.SessionId(session_id=sid)

    def _frame_idx(self, sess, ts_us):
        if sess["t0_us"] is None:
            sess["t0_us"] = ts_us
        t_s = (ts_us - sess["t0_us"]) / 1e6
        return self.backend._sim_t_to_dggt_frame(t_s), t_s

    def render_video_chunk(self, request, context):
        sid = request.session_id.session_id
        sess = self.sessions.get(sid)
        if sess is None:
            sess = self.sessions[sid] = {"cams": [("camera_front_wide_120fov", self.backend.H, self.backend.W)], "t0_us": None}
        poses = list(request.rig_trajectory.poses)
        ret = vm.VideoChunkReturn()
        rel0 = rel1 = 0.0; f0 = f1 = 0
        for ci, (logical_id, rh, rw) in enumerate(sess["cams"]):
            out = ret.camera_outputs.add()
            out.camera_logical_id = logical_id
            for pi, pat in enumerate(poses):
                idx, t_s = self._frame_idx(sess, pat.timestamp_us)
                img = self.backend._render_w2c(self.ext[idx], self.K[idx], idx)  # (H,W,3) uint8
                if (rh, rw) != img.shape[:2]:
                    img = np.array(PILImage.fromarray(img).resize((rw, rh)))
                buf = io.BytesIO(); PILImage.fromarray(img).save(buf, format="JPEG", quality=92)
                im = out.rgb_frames.add(); im.data = buf.getvalue(); im.format = vm.JPEG
                if ci == 0 and pi == 0: rel0, f0 = t_s, idx
                if ci == 0: rel1, f1 = t_s, idx
        print(f"[server] render_video_chunk {sid}: {len(poses)} pose(s) x {len(sess['cams'])} cam "
              f"-> rel_t {rel0:.2f}->{rel1:.2f}s  dggt_frame {f0}->{f1}", flush=True)
        return ret

    def close_session(self, request, context):
        self.sessions.pop(request.session_id, None)
        return cm.VersionId(version_id="closed")


def serve(dump_path, metric_scale, mode, host, port, max_workers=4, clip_duration=None):
    servicer = DGGTWorldModelServicer(dump_path, metric_scale, mode=mode, clip_duration=clip_duration)
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=max_workers),
                         options=[("grpc.max_send_message_length", 256 * 1024 * 1024),
                                  ("grpc.max_receive_message_length", 256 * 1024 * 1024)])
    vmg.add_WorldModelServiceServicer_to_server(servicer, server)
    bound = server.add_insecure_port(f"{host}:{port}")
    server.start()
    print(f"[server] WorldModelService listening on {host}:{bound}", flush=True)
    server.wait_for_termination()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump", required=True)
    ap.add_argument("--metric_scale", type=float, default=34.108)
    ap.add_argument("--mode", choices=["playback", "pose"], default="playback")
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=50051)
    ap.add_argument("--clip_duration", type=float, default=None)
    args = ap.parse_args()
    serve(args.dump, args.metric_scale, args.mode, args.host, args.port, clip_duration=args.clip_duration)
