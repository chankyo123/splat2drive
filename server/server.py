"""DGGT WorldModelService gRPC server.

Wraps GS-World DGGTRenderBackend so AlpaSim's `deploy=external_video_model` can
render frames from a DGGT 4DGS dump.

Two render modes:
  playback  - camera follows the dump's own logged trajectory, indexed by
              session-relative time (timestamp->frame). Ignores the policy pose,
              so the world does NOT react to the policy's steering.
  reactive  - longitudinal progress still comes from time->frame (the verified
              playback anchor), but the policy's LATERAL deviation from the scene
              reference path is applied as a real camera translation, so the
              rendered world reacts to the policy nudging left/right. Needs
              --ref_path (the scene's ground-truth ego path in the rollout LOCAL
              frame: x=forward, y=left, z=up).
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
    def __init__(self, dump_path, metric_scale, mode="playback", device="cuda",
                 clip_duration=None, ref_path=None, lat_clip=5.0,
                 backend="dggt", field_dir=None, holefill=True):
        if backend == "window":
            print(f"[server] loading WindowField backend: {field_dir} (holefill={holefill}, mode={mode})", flush=True)
            from window_field_backend import WindowFieldBackend
            self.backend = WindowFieldBackend(field_dir, device=device,
                                              clip_duration=clip_duration, holefill=holefill)
            self.ext = self.backend.ext
            self.K = self.backend.K
            self.ext_np = self.backend.ext_np.astype(np.float64)
        else:
            print(f"[server] loading DGGT backend: {dump_path} (metric_scale={metric_scale}, mode={mode})", flush=True)
            self.backend = DGGTRenderBackend(dump_path, metric_scale=metric_scale, device=device)
            if clip_duration:
                self.backend.real_duration_s = float(clip_duration)
                print(f"[server] clip_duration override -> {clip_duration}s (dump spans full rollout)", flush=True)
            d = torch.load(dump_path, map_location=device, weights_only=False)
            self.ext = d['cameras']['extrinsic'].to(device).float()
            self.K = d['cameras']['intrinsic'].to(device).float()
            self.ext_np = self.ext.cpu().numpy().astype(np.float64)   # (N,4,4) world->cam
        self.device = device
        self.mode = mode
        self.lat_clip = float(lat_clip)
        self.sessions = {}
        self._sid = 0
        # ── reactive setup: scene reference path + metric scale ──
        self.reactive = False
        if mode == "reactive":
            if not ref_path:
                print("[server] WARNING: mode=reactive but no --ref_path; falling back to playback", flush=True)
                self.mode = "playback"
            else:
                ref = np.load(ref_path).astype(np.float64)       # (M,3) GT ego centers, local x=fwd,y=left,z=up
                self.ref_xy = ref[:, :2]
                L = float(np.sum(np.linalg.norm(np.diff(ref, axis=0), axis=1)))
                cc = np.array([-(w[:3, :3].T @ w[:3, 3]) for w in self.ext_np])  # DGGT cam centers
                cam_len = float(np.sum(np.linalg.norm(np.diff(cc, axis=0), axis=1)))
                self.MS = L / max(cam_len, 1e-9)                 # metres per DGGT unit
                self.reactive = True
                print(f"[server] reactive: ref={ref.shape} L_gt={L:.2f}m cam_len={cam_len:.3f} "
                      f"metric_scale={self.MS:.3f} lat_clip={self.lat_clip}m", flush=True)
        print(f"[server] backend ready: n_frames={self.backend.n_frames} "
              f"H={self.backend.H} W={self.backend.W} dur={self.backend.real_duration_s:.1f}s "
              f"mode={self.mode}", flush=True)

    def _lateral(self, px, py):
        """Signed lateral offset (metres, +=left) of point (px,py) from the reference path."""
        q = np.array([px, py])
        i = int(np.argmin(np.sum((self.ref_xy - q[None]) ** 2, axis=1)))
        i2 = min(i + 1, len(self.ref_xy) - 1); i1 = max(i2 - 1, 0)
        tan = self.ref_xy[i2] - self.ref_xy[i1]
        n = np.linalg.norm(tan)
        if n < 1e-9:
            return 0.0
        tan = tan / n
        left = np.array([-tan[1], tan[0]])       # +90deg from tangent = left
        return float(np.dot(q - self.ref_xy[i], left))

    def _reactive_w2c(self, idx, e):
        """extrinsic[idx] translated laterally by e metres (+=left) in the camera's frame."""
        e = float(np.clip(e, -self.lat_clip, self.lat_clip))
        c2w = np.linalg.inv(self.ext_np[idx])
        x_cam = c2w[:3, 0]                        # camera right axis (world)
        c2w = c2w.copy()
        c2w[:3, 3] -= (e / self.MS) * x_cam       # move left by e (verified sign)
        return torch.from_numpy(np.linalg.inv(c2w)).to(self.device).float()

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
        rel0 = rel1 = 0.0; f0 = f1 = 0; e0 = e1 = 0.0
        for ci, (logical_id, rh, rw) in enumerate(sess["cams"]):
            out = ret.camera_outputs.add()
            out.camera_logical_id = logical_id
            for pi, pat in enumerate(poses):
                idx, t_s = self._frame_idx(sess, pat.timestamp_us)
                if self.reactive:
                    e = self._lateral(pat.pose.vec.x, pat.pose.vec.y)   # policy lateral deviation
                    w2c = self._reactive_w2c(idx, e)
                    img = self.backend._render_w2c(w2c, self.K[idx], idx)
                else:
                    e = 0.0
                    img = self.backend._render_w2c(self.ext[idx], self.K[idx], idx)  # (H,W,3) uint8
                if (rh, rw) != img.shape[:2]:
                    img = np.array(PILImage.fromarray(img).resize((rw, rh)))
                buf = io.BytesIO(); PILImage.fromarray(img).save(buf, format="JPEG", quality=92)
                im = out.rgb_frames.add(); im.data = buf.getvalue(); im.format = vm.JPEG
                if ci == 0 and pi == 0: rel0, f0, e0 = t_s, idx, e
                if ci == 0: rel1, f1, e1 = t_s, idx, e
        print(f"[server] render_video_chunk {sid}: {len(poses)} pose(s) x {len(sess['cams'])} cam "
              f"-> rel_t {rel0:.2f}->{rel1:.2f}s  dggt_frame {f0}->{f1}  lateral {e0:+.2f}->{e1:+.2f}m", flush=True)
        return ret

    def close_session(self, request, context):
        self.sessions.pop(request.session_id, None)
        return cm.VersionId(version_id="closed")


def serve(dump_path, metric_scale, mode, host, port, max_workers=4, clip_duration=None,
          ref_path=None, lat_clip=5.0, backend="dggt", field_dir=None, holefill=True):
    servicer = DGGTWorldModelServicer(dump_path, metric_scale, mode=mode, clip_duration=clip_duration,
                                      ref_path=ref_path, lat_clip=lat_clip,
                                      backend=backend, field_dir=field_dir, holefill=holefill)
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
    ap.add_argument("--backend", choices=["dggt", "window"], default="dggt")
    ap.add_argument("--dump", default=None, help="dggt backend: path to a DGGT gaussian dump .pt")
    ap.add_argument("--field_dir", default=None, help="window backend: dir with manifest + window/single PLYs")
    ap.add_argument("--no_holefill", action="store_true", help="window backend: window layer only, no single-field fill")
    ap.add_argument("--metric_scale", type=float, default=34.108)
    ap.add_argument("--mode", choices=["playback", "reactive"], default="playback")
    ap.add_argument("--ref_path", default=None,
                    help="reactive mode: .npy of the scene GT ego path (local x=fwd,y=left,z=up)")
    ap.add_argument("--lat_clip", type=float, default=5.0,
                    help="reactive mode: clamp |lateral| to this many metres")
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=50051)
    ap.add_argument("--clip_duration", type=float, default=None)
    args = ap.parse_args()
    serve(args.dump, args.metric_scale, args.mode, args.host, args.port,
          clip_duration=args.clip_duration, ref_path=args.ref_path, lat_clip=args.lat_clip,
          backend=args.backend, field_dir=args.field_dir, holefill=not args.no_holefill)
