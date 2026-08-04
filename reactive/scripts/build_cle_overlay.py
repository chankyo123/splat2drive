"""Build a closed-loop overlay video straight from an AlpaSim rollout.asl.

The rollout already contains, per policy step: the camera frame Alpamayo saw
(driver_camera_image, JPEG), its chain-of-thought (driver_return.debug_info.
unstructured_debug_info, a pickled dict with key 'reasoning_text'), and its
predicted trajectory (driver_return.trajectory.poses). We decode all three and
compose: rendered world (top) + a BEV of the predicted trajectory (inset) +
the reasoning caption (bottom).

Usage: build_cle_overlay.py <rollout.asl> <out_dir> <label>
Outputs: <out_dir>/<label>_cle_overlay.mp4, _motion_strip.png, _reasoning_frame.png
"""
import os, sys, struct, io, pickle, json, textwrap, numpy as np
import imageio.v2 as imageio
from PIL import Image, ImageDraw, ImageFont
os.environ.setdefault("PYTHONPATH", "")
sys.path.insert(0, os.path.expanduser("~/GS-World/submodules/alpasim_src/src/grpc"))
from alpasim_grpc.v0.logging_pb2 import LogEntry

ASL, OUT, LABEL = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(OUT, exist_ok=True)

def _font(sz):
    for p in ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"]:
        if os.path.exists(p):
            return ImageFont.truetype(p, sz)
    return ImageFont.load_default()

def _reason(dbg_bytes):
    """unstructured_debug_info is a pickled dict; reasoning_text is a list[str],
    command_name is STRAIGHT/LEFT/RIGHT/... Return '[CMD] joined reasoning'."""
    if not dbg_bytes:
        return None
    d = None
    for loader in (lambda b: pickle.loads(b), lambda b: json.loads(b.decode("utf-8", "ignore"))):
        try:
            d = loader(dbg_bytes); break
        except Exception:
            d = None
    if not isinstance(d, dict):
        return None
    rt = d.get("reasoning_text") or d.get("reasoning") or d.get("text")
    if isinstance(rt, (list, tuple)):
        rt = " ".join(str(x) for x in rt if x)
    if not rt:
        return None
    cmd = d.get("command_name")
    return (f"[{cmd}] " if cmd else "") + str(rt)

# ── parse rollout ──
frames = []      # (t_us, jpeg_bytes)
reasons = []     # (t_us, text)
pred = []        # (t_us, np[K,2] forward/left)
ego = []         # (t_us, x, y)
n = 0
with open(ASL, "rb") as f:
    while True:
        hdr = f.read(4)
        if len(hdr) < 4:
            break
        (sz,) = struct.unpack(">L", hdr)
        e = LogEntry(); e.ParseFromString(f.read(sz)); n += 1
        w = e.WhichOneof("log_entry")
        if w == "driver_camera_image":
            ci = e.driver_camera_image.camera_image
            if b"front" in ci.logical_id.encode() or "front" in ci.logical_id or not frames:
                frames.append((ci.frame_start_us, ci.image_bytes))
        elif w == "driver_return":
            dr = e.driver_return
            txt = _reason(dr.debug_info.unstructured_debug_info)
            ps = dr.trajectory.poses
            t0 = ps[0].timestamp_us if ps else (frames[-1][0] if frames else 0)
            if txt:
                reasons.append((t0, txt))
            if ps:
                xy = np.array([[p.pose.vec.x, p.pose.vec.y] for p in ps], float)
                pred.append((t0, xy))
        elif w == "actor_poses":
            ap = e.actor_poses
            if ap.actor_poses:
                p0 = ap.actor_poses[0].actor_pose
                ego.append((ap.timestamp_us, p0.vec.x, p0.vec.y))
print(f"[cle] entries={n} frames={len(frames)} reasons={len(reasons)} pred={len(pred)} ego={len(ego)}", flush=True)
if not frames:
    print("[cle] no camera frames in rollout — aborting"); sys.exit(1)

frames.sort(key=lambda r: r[0])
reasons.sort(key=lambda r: r[0])
pred.sort(key=lambda r: r[0])

def latest(seq, t):
    best = None
    for tt, v in seq:
        if tt <= t + 1:
            best = v
        else:
            break
    return best if best is not None else (seq[0][1] if seq else None)

# ── compose overlay ──
BASE_W = 900
out_frames = []
strip_keys = []
reason_frame_saved = False
for i, (t, jb) in enumerate(frames):
    cam = Image.open(io.BytesIO(jb)).convert("RGB")
    scale = BASE_W / cam.width
    cam = cam.resize((BASE_W, int(cam.height * scale)))
    W, Hc = cam.size
    panelH = 210
    canvas = Image.new("RGB", (W, Hc + panelH), (12, 12, 16))
    canvas.paste(cam, (0, 0))
    dr = ImageDraw.Draw(canvas)
    # header
    dr.rectangle([0, 0, W, 26], fill=(0, 0, 0))
    dr.text((8, 5), f"{LABEL}  |  Alpamayo 1.5 closed-loop in DGGT 4DGS world  |  t={ (t-frames[0][0])/1e6:5.2f}s  frame {i+1}/{len(frames)}",
            font=_font(15), fill=(180, 230, 255))
    # BEV inset of predicted trajectory (forward=up, left=+x-left)
    xy = latest(pred, t)
    bev = 170
    bx0, by0 = W - bev - 10, 34
    dr.rectangle([bx0, by0, bx0 + bev, by0 + bev], fill=(20, 22, 30), outline=(70, 80, 100))
    dr.text((bx0 + 6, by0 + 3), "pred traj (BEV)", font=_font(11), fill=(150, 170, 200))
    if xy is not None and len(xy) > 1:
        p = xy - xy[0]
        rng = max(1e-3, np.abs(p).max())
        cx, cy = bx0 + bev / 2, by0 + bev - 16
        pts = [(cx - (pt[1] / rng) * (bev/2 - 14), cy - (pt[0] / rng) * (bev - 30)) for pt in p]
        dr.line(pts, fill=(120, 240, 140), width=3)
        dr.ellipse([cx-4, cy-4, cx+4, cy+4], fill=(255, 210, 90))
    # reasoning caption
    txt = latest(reasons, t) or "(no reasoning emitted this step)"
    txt = " ".join(txt.split())
    lines = textwrap.wrap(txt, width=118)[:6]
    dr.text((10, Hc + 8), "Alpamayo reasoning:", font=_font(14), fill=(255, 200, 120))
    for li, ln in enumerate(lines):
        dr.text((10, Hc + 30 + li * 28), ln, font=_font(15), fill=(225, 225, 230))
    arr = np.asarray(canvas)
    out_frames.append(arr)
    if i in (0, len(frames)//4, len(frames)//2, 3*len(frames)//4, len(frames)-1):
        strip_keys.append(arr)
    if not reason_frame_saved and latest(reasons, t) and len(lines) >= 3:
        imageio.imwrite(os.path.join(OUT, f"{LABEL}_reasoning_frame.png"), arr)
        reason_frame_saved = True

imageio.mimwrite(os.path.join(OUT, f"{LABEL}_cle_overlay.mp4"), out_frames, fps=10, quality=8)
# motion strip: downscale keyframes and stack horizontally
sh = min(a.shape[0] for a in strip_keys)
strip = np.concatenate([np.asarray(Image.fromarray(a).resize((int(a.shape[1]*sh/a.shape[0]), sh))) for a in strip_keys], axis=1)
imageio.imwrite(os.path.join(OUT, f"{LABEL}_motion_strip.png"), strip)
if not reason_frame_saved and out_frames:
    imageio.imwrite(os.path.join(OUT, f"{LABEL}_reasoning_frame.png"), out_frames[len(out_frames)//2])
print(f"[cle] wrote {LABEL}_cle_overlay.mp4 ({len(out_frames)} frames) + strip + reasoning_frame", flush=True)
