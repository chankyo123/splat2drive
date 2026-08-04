"""Build a self-contained results report for the new-video runs.

Reads media from workspace/results/{<v>_reactive, <v>_cle} for each video and
emits workspace/results/new_videos_results.html. PNG strips are base64-embedded
(so the report tells the whole story on its own); the mp4s are referenced by
relative path (play when the HTML is opened from inside workspace/results).

Run: python reactive/scripts/build_results_html.py
"""
import base64, os, pathlib, html

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent / "workspace" / "results"

VIDS = [
    dict(key="waymo_real", title="Real Waymo clip", sub="1_TOPLEFT_GT_real_waymo.mp4",
         inp="504×368 · 6 fps · 40 frames · 6.7 s · real dashcam (front-left)",
         world="6.92 M static gaussians · 40 frames · 461 MB dump",
         reactive_frac="5%",
         metrics=[("reasoning steps", "66"), ("collision_at_fault", "0.00"),
                  ("dist_to_gt_trajectory", "0.18 m"), ("dist_traveled", "19.2 m"),
                  ("collision_rear (scene traffic)", "1.00")]),
    dict(key="gen112", title="Generated clip", sub="N01_112m_0_generated_native720x480.mp4",
         inp="720×480 · 16 fps · 481 frames · 30.1 s · world-model generated",
         world="25.34 M static gaussians · 140 frames · 1.6 GB dump",
         reactive_frac="3.5%",
         metrics=None),   # filled from METRICS_GEN if present
]

def b64img(p):
    p = ROOT / p
    if not p.exists():
        return None
    return "data:image/png;base64," + base64.b64encode(p.read_bytes()).decode()

def rel(p):
    return p if (ROOT / p).exists() else None

def img_or_note(path, cap):
    d = b64img(path)
    if d:
        return f'<figure><img src="{d}" alt="{html.escape(cap)}"><figcaption>{html.escape(cap)}</figcaption></figure>'
    return f'<p class="miss">missing: {html.escape(path)}</p>'

def vid_or_note(path, cap):
    r = rel(path)
    if r:
        return (f'<figure><video controls loop muted playsinline src="{r}"></video>'
                f'<figcaption>{html.escape(cap)} · <code>{html.escape(path)}</code></figcaption></figure>')
    return f'<p class="miss">missing: {html.escape(path)}</p>'

def metrics_tbl(rows):
    if not rows:
        return '<p class="miss">metrics pending</p>'
    trs = "".join(f"<tr><td>{html.escape(k)}</td><td class='num'>{html.escape(v)}</td></tr>" for k, v in rows)
    return f"<table class='metrics'><tbody>{trs}</tbody></table>"

def read_metrics(key):
    """Optional: parse a saved <key>_metrics.txt of 'name value' lines."""
    p = ROOT / f"{key}_cle" / f"{key}_metrics.txt"
    if not p.exists():
        return None
    rows = []
    for ln in p.read_text().splitlines():
        parts = ln.split("|")
        if len(parts) == 2:
            rows.append((parts[0].strip(), parts[1].strip()))
    return rows or None

sections = []
for v in VIDS:
    k = v["key"]
    m = v["metrics"] or read_metrics(k)
    sections.append(f"""
<section class="card">
  <header class="cardhead">
    <h2>{html.escape(v['title'])}</h2>
    <code>{html.escape(v['sub'])}</code>
  </header>
  <div class="grid">
    <div class="step"><span class="tag">1 · input</span><p>{html.escape(v['inp'])}</p></div>
    <div class="step"><span class="tag">2 · DGGT 4DGS world</span><p>{html.escape(v['world'])}</p></div>
    <div class="step"><span class="tag">3 · reactive shift</span><p>lateral ±{v['reactive_frac']} of path length</p></div>
  </div>

  <h3>Reactive render — the world responds to steering</h3>
  <div class="media">
    {img_or_note(f"{k}_reactive/lateral_sweep_strip.png", "lateral sweep  L · −½ · 0 · +½ · R  (center = reconstructed view)")}
    {vid_or_note(f"{k}_reactive/reactive_vs_baseline.mp4", "baseline (left) vs reactive left-drift (right)")}
    {img_or_note(f"{k}_reactive/reactive_vs_baseline_strip.png", "baseline vs reactive — keyframes")}
  </div>

  <h3>Alpamayo 1.5 closed-loop — driving this world</h3>
  <div class="media">
    {img_or_note(f"{k}_cle/{k}_motion_strip.png", "closed-loop keyframes + per-step reasoning")}
    {vid_or_note(f"{k}_cle/{k}_cle_overlay.mp4", "closed-loop overlay: world + reasoning + predicted trajectory")}
    {img_or_note(f"{k}_cle/{k}_reasoning_frame.png", "a reasoning + trajectory frame")}
  </div>
  {metrics_tbl(m)}
</section>""")

HTML = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Splat2Drive · new-video runs</title>
<style>
  :root {{ --bg:#0e1014; --panel:#161a21; --edge:#242b36; --ink:#e6e9ee; --dim:#9aa4b2;
          --accent:#63d29a; --accent2:#7bb7ff; --miss:#e0725f; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--ink);
    font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; }}
  .wrap {{ max-width:1120px; margin:0 auto; padding:40px 22px 80px; }}
  h1 {{ font-size:30px; letter-spacing:-.4px; margin:0 0 6px; }}
  .lede {{ color:var(--dim); max-width:75ch; margin:0 0 8px; }}
  .note {{ color:var(--dim); font-size:13px; border-left:2px solid var(--edge); padding:6px 12px; margin:18px 0 30px; }}
  .card {{ background:var(--panel); border:1px solid var(--edge); border-radius:14px; padding:22px 24px; margin:26px 0; }}
  .cardhead {{ display:flex; align-items:baseline; gap:14px; flex-wrap:wrap; border-bottom:1px solid var(--edge); padding-bottom:12px; margin-bottom:16px; }}
  .cardhead h2 {{ margin:0; font-size:21px; }}
  code {{ font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:12.5px; color:var(--accent2); }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(210px,1fr)); gap:12px; margin-bottom:8px; }}
  .step {{ background:#11151b; border:1px solid var(--edge); border-radius:10px; padding:12px 14px; }}
  .step p {{ margin:6px 0 0; color:var(--ink); }}
  .tag {{ font-size:11px; text-transform:uppercase; letter-spacing:.08em; color:var(--accent); }}
  h3 {{ font-size:15px; margin:24px 0 10px; color:var(--ink); }}
  .media {{ display:flex; flex-direction:column; gap:16px; }}
  figure {{ margin:0; }}
  img, video {{ width:100%; border-radius:8px; border:1px solid var(--edge); display:block; background:#000; }}
  figcaption {{ color:var(--dim); font-size:12.5px; margin-top:6px; }}
  .metrics {{ border-collapse:collapse; margin-top:16px; font-size:13.5px; width:auto; }}
  .metrics td {{ border:1px solid var(--edge); padding:5px 14px; }}
  .metrics td.num {{ font-variant-numeric:tabular-nums; color:var(--accent); text-align:right; }}
  .miss {{ color:var(--miss); font-size:13px; }}
  footer {{ color:var(--dim); font-size:12.5px; margin-top:40px; border-top:1px solid var(--edge); padding-top:16px; }}
</style></head><body><div class="wrap">
<h1>Splat2Drive — two new clips, end to end</h1>
<p class="lede">Each input video is turned into a DGGT feed-forward 4D-Gaussian world, that
world is shown reacting to lateral steering, and Alpamayo&nbsp;1.5 then drives it
closed-loop — producing per-frame chain-of-thought and predicted trajectories.</p>
<p class="note">All GPU inference ran on the remote box (2× Blackwell). The closed-loop
ego dynamics, route and traffic come from the s007 AlpaSim scenario scaffold (Tier-0),
so collision/offroad bookkeeping is the scenario's, not the clip's — but Alpamayo
genuinely perceives and drives each reconstructed world. Large lateral shifts render
novel views the single traversal never observed, hence some smear (coverage limit).</p>
{''.join(sections)}
<footer>Splat2Drive · DGGT 4DGS ▸ gRPC WorldModelService ▸ AlpaSim external_video_model ▸ Alpamayo 1.5.
Media in <code>workspace/results/</code> (git-ignored). Open this file from that folder so the mp4s resolve.</footer>
</div></body></html>"""

out = ROOT / "new_videos_results.html"
out.write_text(HTML)
print(f"wrote {out}  ({out.stat().st_size//1024} KB)")
