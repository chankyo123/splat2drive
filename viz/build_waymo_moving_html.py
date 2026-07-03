#!/usr/bin/env python3
import base64, pathlib
SP = pathlib.Path("/tmp/claude-1000/-home-ubuntu/c0e8be85-6256-4a9e-b3bb-99e4fe1a24e1/scratchpad")
def b(p,m): return f"data:{m};base64,"+base64.b64encode((SP/p).read_bytes()).decode()
A=dict(
  hero=b("waymo_moving_hero.png","image/png"),
  overlay=b("waymo_moving_overlay.mp4","video/mp4"),
  cam=b("waymo_moving_cam.mp4","video/mp4"),
  strip=b("s007_motion_strip.png","image/png"),
)
# 13-step chain-of-thought, ~every 1.5s across the 20s rollout
TL=[
 ("keep","Keep distance to the cut-in vehicle merging into our lane ahead"),
 ("keep","Keep distance to the lead vehicle directly ahead in our lane"),
 ("go","Keep lane — the lane is clear ahead"),
 ("stop","Stop for the red traffic light since it is red"),
 ("turn","Nudge left — cones blocking the right side of our lane"),
 ("turn","Nudge left to clear the stopped bus blocking the right side"),
 ("turn","Nudge right — a car is encroaching from the left side of our lane"),
 ("go","Keep lane — the lane is clear ahead"),
 ("keep","Keep distance to the cut-in vehicle merging into our lane"),
 ("turn","Nudge right to clear the vehicle encroaching from the left"),
 ("keep","Keep distance to the cut-in vehicle merging into our lane"),
 ("turn","Nudge left to clear the trash bags blocking the right side"),
 ("go","Keep lane — the lane is clear ahead"),
]
rows="".join(f'<div class="ev {k}"><span class="dot"></span><span>{t}</span></div>' for k,t in TL)
HTML=f"""<title>Alpamayo drives closed-loop through a moving DGGT-Waymo world</title>
<meta name="description" content="A moving Tier-0 run: Alpamayo 1.5 drives a full SF hill block inside a DGGT 4D-Gaussian reconstruction of the Waymo Open Dataset — stopping at a red light and nudging past a bus, cones and trash bags, all in real time.">
<style>
 :root{{--bg:#080b0f;--panel:#121a21;--panel2:#0e161d;--line:#213039;--ink:#e8eff5;--mut:#8b9aa8;--faint:#596673;
  --vla:#33e0cc;--stop:#f0576b;--go:#5fd38a;--turn:#f2b04a;--keep:#7aa2ff;
  --mono:ui-monospace,"SF Mono",Menlo,Consolas,monospace;--sans:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif;}}
 *{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);line-height:1.62;-webkit-font-smoothing:antialiased}}
 .wrap{{max-width:900px;margin:0 auto;padding:46px 24px 96px}}
 .eyebrow{{font-family:var(--mono);font-size:11px;letter-spacing:.24em;text-transform:uppercase;color:var(--vla);margin:0 0 14px}}
 h1{{font-size:clamp(25px,3.6vw,34px);margin:0 0 15px;font-weight:680;letter-spacing:-.022em;text-wrap:balance;line-height:1.18}}
 p.intro{{color:var(--mut);font-size:15.5px;margin:0 0 22px;max-width:73ch}} p.intro b{{color:var(--ink)}}
 .movetag{{display:inline-flex;align-items:center;gap:7px;font-family:var(--mono);font-size:11.5px;color:var(--vla);border:1px solid #1f5049;background:#0c1a1e;padding:4px 10px;border-radius:20px;margin:0 0 18px}}
 .movetag .p{{width:7px;height:7px;border-radius:50%;background:var(--vla);animation:pl 1.6s ease-in-out infinite}}
 @keyframes pl{{0%,100%{{opacity:.35;transform:scale(.8)}}50%{{opacity:1;transform:scale(1.15)}}}}
 @media(prefers-reduced-motion:reduce){{.movetag .p{{animation:none}}}}
 .hero{{border:1px solid var(--line);border-radius:11px;overflow:hidden;background:#000}} .hero img{{width:100%;display:block}}
 .cap{{font-family:var(--mono);font-size:11.5px;color:var(--faint);margin:9px 0 0;line-height:1.55}} .cap b{{color:var(--vla)}}
 .flow{{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:26px 0 6px;font-family:var(--mono);font-size:12px}}
 .chip{{padding:7px 12px;border-radius:7px;border:1px solid var(--line);background:var(--panel);color:var(--mut)}} .arw{{color:var(--faint)}}
 section{{margin:40px 0 0;padding-top:28px;border-top:1px solid var(--line)}}
 h2{{font-size:19.5px;margin:0 0 5px;font-weight:640;letter-spacing:-.01em}}
 p.d{{color:var(--mut);font-size:14.5px;margin:8px 0 14px;max-width:71ch}} p.d b{{color:var(--ink)}}
 video,img.media{{width:100%;border-radius:10px;border:1px solid var(--line);background:#000;display:block}}
 .facts{{display:grid;grid-template-columns:repeat(4,1fr);gap:1px;background:var(--line);border:1px solid var(--line);border-radius:10px;overflow:hidden;margin:18px 0 0}}
 @media(max-width:620px){{.facts{{grid-template-columns:repeat(2,1fr)}}}}
 .fact{{background:var(--panel);padding:13px 15px}} .fact .k{{font-family:var(--mono);font-size:10px;letter-spacing:.09em;text-transform:uppercase;color:var(--faint)}} .fact .v{{font-size:16px;font-weight:660;margin-top:3px;font-variant-numeric:tabular-nums}} .fact .v.ok{{color:var(--go)}}
 .tl{{display:flex;flex-direction:column;gap:1px;background:var(--line);border:1px solid var(--line);border-radius:10px;overflow:hidden;margin:10px 0 0;counter-reset:s}}
 .ev{{background:var(--panel);display:flex;align-items:center;gap:12px;padding:10px 15px;font-size:13.5px;position:relative}}
 .ev::before{{counter-increment:s;content:counter(s);font-family:var(--mono);font-size:10.5px;color:var(--faint);width:16px;flex:none;text-align:right}}
 .ev .dot{{width:8px;height:8px;border-radius:50%;flex:none}}
 .ev.stop .dot{{background:var(--stop)}}.ev.turn .dot{{background:var(--turn)}}.ev.keep .dot{{background:var(--keep)}}.ev.go .dot{{background:var(--go)}}
 .ev.stop{{border-left:3px solid var(--stop)}}.ev.turn{{border-left:3px solid var(--turn)}}.ev.keep{{border-left:3px solid var(--keep)}}.ev.go{{border-left:3px solid var(--go)}}
 .lgd{{display:flex;flex-wrap:wrap;gap:14px;margin:12px 2px 0;font-family:var(--mono);font-size:11px;color:var(--mut)}}
 .lgd span{{display:inline-flex;align-items:center;gap:6px}} .lgd i{{width:9px;height:9px;border-radius:50%;display:inline-block}}
 .note{{background:#0c1a1e;border:1px solid #1c4a44;border-radius:10px;padding:16px 19px;margin:32px 0 0}}
 .note .lbl{{font-family:var(--mono);font-size:10.5px;letter-spacing:.14em;text-transform:uppercase;color:var(--vla);margin-bottom:9px}}
 .note ul{{margin:0;padding-left:18px;color:var(--mut);font-size:13.5px}} .note li{{margin:6px 0}} .note b{{color:var(--ink)}}
 footer{{margin-top:44px;border-top:1px solid var(--line);padding-top:18px;color:var(--faint);font-size:12.5px}} footer code{{font-family:var(--mono);color:var(--mut);font-size:11.5px}}
</style>
<div class="wrap">
 <p class="eyebrow">Splat2Drive · Waymo · DGGT 4DGS · Alpamayo 1.5 · closed-loop</p>
 <h1>이번엔 <b style="color:var(--vla)">움직인다</b> — Alpamayo가 복원된 Waymo 골목을 한 블록 통째로 주행</h1>
 <span class="movetag"><span class="p"></span>MOVING · ego가 20초 동안 전진 · 정지 아님</span>
 <p class="intro">앞선 scene003 런은 정책이 <b>정차 차량 뒤에 멈춰</b> 카메라가 거의 안 움직였다. 이번엔 <b>앞이 트인 샌프란시스코 언덕길(scene007)</b>을 골라 DGGT로 4DGS 복원하고 그 안에서 Alpamayo 1.5를 클로즈루프로 돌렸다. 결과: ego가 <b>블록 전체를 실제로 주행</b>하며 빨간불에 정지하고, 버스·콘·쓰레기봉투를 좌우로 nudge한다 — <b>at-fault 충돌 0, offroad 0.</b></p>
 <div class="hero"><img src="{A['hero']}" alt="Alpamayo driving forward in reconstructed Waymo hill street"></div>
 <p class="cap">t≈13s · <b>BEV(좌상)</b>: ego(초록)가 뒤에 주행 궤적을 남기며 GT 경로(주황)를 따라 전진. <b>metrics</b>: collision_at_fault 0.00 · offroad 0.00 · 측방 이탈(dist_to_gt_trajectory) 0.22로 경로 밀착. <b>cam</b>: 복원된 언덕길을 STRAIGHT로 주행.</p>

 <div class="flow"><span class="chip">Waymo 전방 카메라</span><span class="arw">→</span><span class="chip">DGGT 4DGS (pose-free)</span><span class="arw">→</span><span class="chip">gRPC WorldModelService</span><span class="arw">→</span><span class="chip">Alpamayo 클로즈루프</span></div>

 <section>
  <h2>주행 + 실시간 추론 + 궤적 예측</h2>
  <p class="d">복원 4DGS를 WorldModelService gRPC 서버로 올리고 Alpamayo 1.5(10B)를 20초 클로즈루프 실행. <b>우측 Trajectory Prediction 패널의 예측선이 ~38m 전방까지 길게 뻗는다</b> — 정책이 실제 속도로 전진 중이라는 직접 증거(정차 런에선 예측선이 짧았다).</p>
  <video src="{A['overlay']}" autoplay loop muted playsinline controls></video>
  <p class="cap">카메라 · 실시간 추론(<b>Reasoning</b>) · <b>Trajectory Prediction</b> — 실시간(20초)으로 리타이밍. 매 스텝 splat 프레임을 보고 CoT로 판단→예측 궤적 생성.</p>
 </section>

 <section>
  <h2>움직인다는 증거 — start → end</h2>
  <p class="d">복원 카메라 뷰만. 첫 프레임과 끝 프레임이 <b>완전히 다른 위치</b>(주차차량·건물이 흘러 지나가고 언덕이 다가온다). 프레임 간 변화 대비 <b>첫–끝 변화가 4배</b> — 지터가 아니라 누적 전진.</p>
  <img class="media" src="{A['strip']}" alt="start to end motion strip">
  <p class="cap">클로즈루프 카메라 start · ¼ · ½ · ¾ · end. 미션 돌로레스 대성당 첨탑이 멀리서 점점 다가온다.</p>
  <video src="{A['cam']}" autoplay loop muted playsinline controls style="margin-top:12px"></video>
  <p class="cap">카메라 단독 · 실시간 · 오버레이 없음 — 순수하게 주행만.</p>
 </section>

 <section>
  <h2>Chain-of-thought — 13 스텝</h2>
  <p class="d">Alpamayo가 20초 동안 내놓은 판단. 빨간불 정지 1회, nudge 5회(콘·버스·쓰레기봉투·대향 차량 회피), cut-in 거리유지 다수 — <b>모두 DGGT 복원물 안의 실제 요소를 지칭</b>한다.</p>
  <div class="tl">{rows}</div>
  <div class="lgd">
   <span><i style="background:var(--stop)"></i>정지 stop</span>
   <span><i style="background:var(--turn)"></i>회피 nudge</span>
   <span><i style="background:var(--keep)"></i>거리유지 keep-dist</span>
   <span><i style="background:var(--go)"></i>차선유지 keep-lane</span>
  </div>
  <div class="facts">
   <div class="fact"><div class="k">static gaussians</div><div class="v">17.9M</div></div>
   <div class="fact"><div class="k">dynamic T</div><div class="v">197</div></div>
   <div class="fact"><div class="k">at-fault collision</div><div class="v ok">0.00</div></div>
   <div class="fact"><div class="k">offroad</div><div class="v ok">0.00</div></div>
  </div>
 </section>

 <div class="note">
  <div class="lbl">이 결과의 의미 & caveats</div>
  <ul>
   <li><b>요청 달성:</b> &ldquo;정지 말고 움직이는 클로즈루프&rdquo; — ego가 20초 내내 <b>블록 전체를 전진 주행</b>. 궤적 예측선·BEV 이동·start↔end 프레임 차이 모두 실주행을 확증.</li>
   <li><b>인지 증거:</b> 콘·정차 버스·쓰레기봉투·cut-in 차량은 <b>DGGT 복원물에만</b> 존재. CoT가 이들을 정확히 지칭하며 nudge/정지 → 정책이 <b>렌더된 4DGS를 진짜 시각적으로 소비</b>.</li>
   <li><b>측방 경로 밀착:</b> dist_to_gt_trajectory 최대 0.22 — 차로를 벗어나지 않고 GT 경로를 따라감. dist_to_gt_location(5.65)은 속도/시점 차이로 인한 종방향 위치 차이.</li>
   <li><b>Tier-0 caveat:</b> map/GT/actor scaffold가 이 scene과 완전 일치하진 않아 <b>메트릭 절대값보다 인지·행동·주행 여부</b>가 관찰 포인트. collision_any 1.00은 rear이며 <b>at-fault 아님</b>(0.00). 서버는 pinhole 렌더, Alpamayo는 f-theta 기대(intrinsic mismatch)로도 인지엔 충분.</li>
  </ul>
 </div>
 <footer><p>Scene: Waymo Open Dataset (SF hill street, scene007) → <code>dggt mode=3 --dump_gs</code> (17.9M) → <code>DGGTRenderBackend</code> gRPC WorldModelService → <code>alpasim deploy=external_video_model driver=alpamayo1_5_1cam</code>. 20s / 74 chunks · AlpaSim 코어 수정 0. 이전 정차 런(scene003)은 별도 아티팩트.</p></footer>
</div>
"""
out=SP/"waymo_moving.html"; out.write_text(HTML); print("wrote",out,out.stat().st_size,"bytes")
