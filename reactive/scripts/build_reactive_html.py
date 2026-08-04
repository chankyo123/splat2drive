#!/usr/bin/env python3
import base64, pathlib
# media lives in ../media relative to this script (repo layout)
D = pathlib.Path(__file__).resolve().parent.parent / "media"
def b(p,m): return f"data:{m};base64,"+base64.b64encode((D/p).read_bytes()).decode()
A=dict(
  verify=b("mapping_verify_strip.png","image/png"),
  rvb_strip=b("reactive_vs_baseline_strip.png","image/png"),
  rvb_vid=b("reactive_vs_baseline.mp4","video/mp4"),
  live_strip=b("live_motion_strip.png","image/png"),
  live_vid=b("live_reactive_overlay.mp4","video/mp4"),
  live_hero=b("live_reasoning_frame.png","image/png"),
)
HTML=f"""<title>Splat2Drive — reactive closed-loop</title>
<meta name="description" content="Making the DGGT 4D-Gaussian world REACT to the driving policy: the policy's lateral deviation is applied as a real camera shift, verified in isolation, shown vs a no-lateral baseline, and run as a live Alpamayo closed-loop on a second GPU box.">
<style>
 :root{{--bg:#080b0f;--panel:#121a21;--line:#213039;--ink:#e8eff5;--mut:#8b9aa8;--faint:#596673;
  --vla:#33e0cc;--warn:#f2b04a;--bad:#f0576b;--ok:#5fd38a;
  --mono:ui-monospace,"SF Mono",Menlo,Consolas,monospace;--sans:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif;}}
 *{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);line-height:1.62;-webkit-font-smoothing:antialiased}}
 .wrap{{max-width:940px;margin:0 auto;padding:46px 24px 96px}}
 .eyebrow{{font-family:var(--mono);font-size:11px;letter-spacing:.24em;text-transform:uppercase;color:var(--vla);margin:0 0 14px}}
 h1{{font-size:clamp(25px,3.6vw,34px);margin:0 0 14px;font-weight:680;letter-spacing:-.022em;text-wrap:balance;line-height:1.18}}
 p.intro{{color:var(--mut);font-size:15.5px;margin:0 0 20px;max-width:74ch}} p.intro b{{color:var(--ink)}}
 .steps{{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:22px 0 4px;font-family:var(--mono);font-size:12px}}
 .chip{{padding:7px 12px;border-radius:7px;border:1px solid var(--line);background:var(--panel);color:var(--mut)}} .arw{{color:var(--faint)}}
 section{{margin:40px 0 0;padding-top:28px;border-top:1px solid var(--line)}}
 .k{{font-family:var(--mono);font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--vla);margin:0 0 6px}}
 h2{{font-size:20px;margin:0 0 6px;font-weight:660;letter-spacing:-.01em}}
 p.d{{color:var(--mut);font-size:14.5px;margin:8px 0 14px;max-width:72ch}} p.d b{{color:var(--ink)}} p.d code{{font-family:var(--mono);font-size:12.5px;color:var(--vla);background:#0e1a1f;padding:1px 6px;border-radius:4px}}
 video,img.media{{width:100%;border-radius:10px;border:1px solid var(--line);background:#000;display:block}}
 .cap{{font-family:var(--mono);font-size:11.5px;color:var(--faint);margin:9px 0 0;line-height:1.55}} .cap b{{color:var(--vla)}}
 .facts{{display:grid;grid-template-columns:repeat(4,1fr);gap:1px;background:var(--line);border:1px solid var(--line);border-radius:10px;overflow:hidden;margin:18px 0 0}}
 @media(max-width:620px){{.facts{{grid-template-columns:repeat(2,1fr)}}}}
 .fact{{background:var(--panel);padding:12px 14px}} .fact .fk{{font-family:var(--mono);font-size:10px;letter-spacing:.09em;text-transform:uppercase;color:var(--faint)}} .fact .fv{{font-size:15px;font-weight:660;margin-top:3px;font-variant-numeric:tabular-nums}} .fact .fv.ok{{color:var(--ok)}}
 .note{{background:#0c1a1e;border:1px solid #1c4a44;border-radius:10px;padding:16px 19px;margin:30px 0 0}}
 .note .lbl{{font-family:var(--mono);font-size:10.5px;letter-spacing:.14em;text-transform:uppercase;color:var(--vla);margin-bottom:9px}}
 .note ul{{margin:0;padding-left:18px;color:var(--mut);font-size:13.5px}} .note li{{margin:6px 0}} .note b{{color:var(--ink)}}
 .pill{{display:inline-block;font-family:var(--mono);font-size:10.5px;padding:2px 8px;border-radius:20px;border:1px solid var(--line);color:var(--mut);margin-left:6px}}
 .pill.ok{{color:var(--ok);border-color:#1c4a3a}} .pill.warn{{color:var(--warn);border-color:#4a3a1c}}
 footer{{margin-top:44px;border-top:1px solid var(--line);padding-top:18px;color:var(--faint);font-size:12.5px}} footer code{{font-family:var(--mono);color:var(--mut);font-size:11.5px}}
</style>
<div class="wrap">
 <p class="eyebrow">Splat2Drive · reactive closed-loop</p>
 <h1>월드가 정책에 <b style="color:var(--vla)">반응</b>한다 — playback를 넘어선 reactive 렌더</h1>
 <p class="intro">기존 <b>playback</b>는 카메라가 원본 궤적을 시간순으로만 따라가 <b>정책의 조향을 무시</b>했다. <b>reactive</b>는 종방향(시간→프레임)은 그대로 두고, <b>정책이 매 스텝 이탈한 lateral을 실제 카메라 평행이동으로</b> DGGT 4DGS 월드에 적용한다 — 정책이 옆으로 nudge하면 렌더된 세계가 그만큼 움직인다. 아래는 <b>매핑 검증 → baseline 대비 → 라이브 Alpamayo 폐루프</b> 순서.</p>
 <div class="steps"><span class="chip">정책 pose (rig-local)</span><span class="arw">→</span><span class="chip">GT 경로 기준 lateral e</span><span class="arw">→</span><span class="chip">extrinsic[j] 카메라 e만큼 이동</span><span class="arw">→</span><span class="chip">4DGS novel-view 렌더</span></div>

 <section>
  <p class="k">01 · mapping verify <span class="pill ok">controls pass</span></p>
  <h2>매핑이 물리적으로 맞는가</h2>
  <p class="d">라이브 루프에 넣기 전, 매핑만 독립 검증. 같은 프레임에서 <code>+2m LEFT</code> / <code>+2m RIGHT</code>를 주면 카메라가 <b>정확히 반대 방향</b>으로 이동하고, <code>e=0</code>이면 <b>playback으로 환원</b>(좌 2칸 동일) — 부호·스케일 정상.</p>
  <img class="media" src="{A['verify']}" alt="mapping verification: playback vs reactive vs +-2m">
  <p class="cap">행=프레임, 열: <b>playback</b> · <b>reactive(정책 실제 e)</b> · <b>+2m LEFT</b> · <b>+2m RIGHT</b>. 큰 오프셋일수록 관측 안 된 영역이라 novel-view smear(태생적 한계).</p>
 </section>

 <section>
  <p class="k">02 · reactive vs baseline <span class="pill">policy real path</span></p>
  <h2>반응성 — 같은 위치, 정책의 실제 −1.87m 이탈</h2>
  <p class="d">정책이 실제로 주행한 궤적(우측으로 최대 <b>−1.87m</b> 드리프트)을 따라, <b>같은 전방 위치</b>에서 baseline(e=0)과 reactive를 나란히 렌더. 종방향은 동일하니 <b>차이는 순수하게 정책의 lateral 반응</b>이다.</p>
  <video src="{A['rvb_vid']}" autoplay loop muted playsinline controls></video>
  <p class="cap">좌 <b>BASELINE</b>(월드가 정책 무시) · 우 <b>REACTIVE</b>(월드가 정책 추적) · 실시간 20초, 상단에 라이브 <b>lateral e</b>.</p>
  <img class="media" src="{A['rvb_strip']}" style="margin-top:12px" alt="reactive vs baseline at f350/f500/f588">
  <p class="cap">f350(−0.41m) → f500(−1.20m) → f588(−1.87m): baseline은 차선 중앙, <b>reactive는 카메라가 우측으로 이동</b>해 빨간 차가 우하단에 다가온다.</p>
 </section>

 <section>
  <p class="k">03 · live closed-loop <span class="pill ok">remote GPU</span></p>
  <h2>라이브 Alpamayo 폐루프 — feedback 경로가 실제로 닫힘</h2>
  <p class="d">두 번째 박스의 <b>유휴 GPU</b>에서 Alpamayo 1.5를 클로즈루프로 실행하고, 렌더는 이 박스의 reactive DGGT 서버가 담당(gRPC). <b>매 스텝 정책의 pose로 lateral을 계산해 카메라를 이동한 프레임을 정책이 다시 소비</b> — 진짜 피드백 루프. 전체 20초 완주, OOM 없음.</p>
  <img class="media" src="{A['live_hero']}" alt="live reactive closed-loop reasoning + trajectory">
  <p class="cap">t=10.8s · 추론 <b>&ldquo;stopped truck 뒤라 즉시 병합 막힘 → 우측 차선변경용 gap 생성&rdquo;</b> · 우측 Trajectory Prediction ~28m 전방(실주행).</p>
  <video src="{A['live_vid']}" autoplay loop muted playsinline controls style="margin-top:12px"></video>
  <p class="cap">라이브 폐루프 오버레이(cam+추론+궤적) · 실시간 20초. ego가 언덕길을 전진 주행.</p>
  <img class="media" src="{A['live_strip']}" style="margin-top:12px" alt="live run start-to-end">
  <p class="cap">start → end: 전진 확인(첫–끝 변화 = 프레임간 4×). BEV가 경로 추적.</p>
  <div class="facts">
   <div class="fact"><div class="fk">rollout</div><div class="fv">20s · 75 chunks</div></div>
   <div class="fact"><div class="fk">at-fault collision</div><div class="fv ok">0.00</div></div>
   <div class="fact"><div class="fk">offroad</div><div class="fv ok">0.00</div></div>
   <div class="fact"><div class="fk">live lateral</div><div class="fv">−0.28…+0.07m</div></div>
  </div>
 </section>

 <div class="note">
  <div class="lbl">정직한 해석 &amp; caveats</div>
  <ul>
   <li><b>달성:</b> reactive 렌더러가 <b>정책의 라이브 pose로 카메라를 실시간 이동</b>시키고, Alpamayo가 그 프레임을 보고 주행 — <b>closed-loop feedback 경로가 실제로 닫혔다</b>(원격 유휴 GPU, 전체 완주).</li>
   <li><b>이번 라이브 런은 정책이 차선 중앙을 잘 유지</b>(최대 ~0.28m)해서 카메라 반응이 작아 시각적으론 미묘 — &ldquo;월드가 크게 반응&rdquo;하는 장면은 <b>02(정책 실제 −1.87m 경로)</b>가 보여준다. 둘을 합쳐야 완전한 그림.</li>
   <li><b>reactive = 검증된 것 위에 반응성만 추가:</b> 종방향 프레임은 playback과 동일(시간→프레임), lateral만 GT 경로 기준으로 얹음 — 리스크 최소화.</li>
   <li>큰 이탈일수록 단일-traversal 재구성이 관측하지 못한 novel view라 <b>smear</b> 증가(코드로 못 고치는 태생적 한계). heading 반응·pose-반응형 dynamic는 다음 단계.</li>
   <li>Tier-0 scaffold라 <b>메트릭 절대값보다 반응·주행 여부</b>가 관찰 포인트(collision_any는 rear/at-fault 아님).</li>
  </ul>
 </div>
 <footer><p>Server: <code>server.py --mode reactive --ref_path gt_ref</code> (DGGT 4DGS, GS-World backend) · driver: <code>alpasim deploy=external_video_model driver=alpamayo1_5_1cam</code> on a remote idle-GPU box → renderer over gRPC. AlpaSim 코어 수정 0. Scene: Waymo scene007 → DGGT 17.9M static gaussians.</p></footer>
</div>
"""
out=pathlib.Path(__file__).resolve().parent.parent / "reactive.html"; out.write_text(HTML)
print("wrote",out,out.stat().st_size,"bytes")
