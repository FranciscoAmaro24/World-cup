// ─────────────────────────────────────────────────────────────
// programme-picker.jsx — the SCORELINE PICKER rendered in the
// "Matchday Programme" system (the blend between 1·Broadsheet and
// 3·Broadcast). Three frames:
//   PickerProgEditorial  — mobile, editorial lean (≈1.5)
//   PickerProgBroadcast  — mobile, broadcast lean (≈2.5)
//   PickerProgDesktop    — desktop programme
// Cream paper, Archivo Black headlines, Rajdhani LED scoreboards,
// pitch-green + lime, square corners. Steppers replace the old
// dark number inputs.
// Depends on wc-data.jsx + wc-ui.jsx (PhoneStatusBar, HomeBar).
// ─────────────────────────────────────────────────────────────

if (typeof document !== 'undefined' && !document.getElementById('picker-fonts')) {
  const l = document.createElement('link');
  l.id = 'picker-fonts';
  l.rel = 'stylesheet';
  l.href = 'https://fonts.googleapis.com/css2?family=Archivo+Black&family=Archivo:wght@400;500;600;700;800&family=Spectral:ital,wght@0,400;0,600;1,400&family=Rajdhani:wght@500;600;700&display=swap';
  document.head.appendChild(l);
}

function pkInject(id, css) {
  if (typeof document === 'undefined' || document.getElementById(id)) return;
  const s = document.createElement('style');
  s.id = id; s.textContent = css; document.head.appendChild(s);
}

const PK_BOLT = (c) => (
  <svg width="15" height="15" viewBox="0 0 16 16" fill={c} style={{ display: 'block' }}>
    <path d="M9.4.6 3 9.3h3.7L5.9 15.4 13 6.4H8.5z" />
  </svg>
);

// Shared programme stepper — ink LED box with square +/- controls
pkInject('ps-styles', `
.ps{display:flex;flex-direction:column;align-items:center;gap:7px;}
.ps button{background:#f5f0e4;border:1.5px solid #0a7d3c;color:#0a7d3c;font-family:"Archivo",sans-serif;
  font-weight:800;display:flex;align-items:center;justify-content:center;cursor:pointer;line-height:1;transition:background .12s;}
.ps button:hover{background:#0a7d3c;color:#fff;}
.ps .bx{background:#15271d;color:#c6f24e;font-family:"Rajdhani",sans-serif;font-weight:700;
  display:flex;align-items:center;justify-content:center;line-height:1;position:relative;overflow:hidden;
  background-image:repeating-linear-gradient(45deg,rgba(198,242,78,.10) 0 1px,transparent 1px 9px),
    repeating-linear-gradient(-45deg,rgba(198,242,78,.10) 0 1px,transparent 1px 9px);}
.ps .bx span{position:relative;z-index:1;}
.ps.md button{width:30px;height:24px;font-size:15px;}
.ps.md .bx{width:54px;height:62px;font-size:40px;}
.ps.lg button{width:38px;height:30px;font-size:18px;}
.ps.lg .bx{width:70px;height:84px;font-size:54px;}
/* shared pitch-marking watermark (center circle + halfway line) */
.pitch{position:absolute;inset:0;pointer-events:none;z-index:0;}
.pitch .cc{position:absolute;left:50%;top:50%;width:130px;height:130px;transform:translate(-50%,-50%);
  border-radius:50%;border:1.6px solid currentColor;}
.pitch .cs{position:absolute;left:50%;top:50%;width:7px;height:7px;transform:translate(-50%,-50%);border-radius:50%;background:currentColor;}
.pitch .hl{position:absolute;left:50%;top:6%;bottom:6%;width:1.6px;transform:translateX(-50%);background:currentColor;}
.pitch.lg .cc{width:184px;height:184px;}
`);

function ProgStep({ value, onChange, size = 'md' }) {
  const set = (d) => onChange(Math.max(0, Math.min(20, value + d)));
  return (
    <div className={`ps ${size}`}>
      <button onClick={() => set(1)}>+</button>
      <div className="bx"><span>{value}</span></div>
      <button onClick={() => set(-1)}>−</button>
    </div>
  );
}

// Pitch-marking watermark — center circle, spot, halfway line
function PitchLines({ color, big }) {
  return (
    <div className={`pitch${big ? ' lg' : ''}`} style={{ color }}>
      <span className="cc" /><span className="cs" /><span className="hl" />
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// MOBILE — EDITORIAL LEAN (≈1.5)
// ═══════════════════════════════════════════════════════════════
pkInject('pkE-styles', `
.pkE{--paper:#f5f0e4;--ink:#15271d;--green:#0a7d3c;--lime:#c6f24e;--mute:#6c7268;
  background:var(--paper);color:var(--ink);height:100%;display:flex;flex-direction:column;
  font-family:"Spectral",Georgia,serif;}
.pkE *{box-sizing:border-box;margin:0;padding:0;}
.pkE .strip{background:var(--green);color:#fff;display:flex;justify-content:space-between;align-items:center;
  padding:8px 22px;font-family:"Archivo",sans-serif;font-size:10px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;}
.pkE .strip .live{display:flex;align-items:center;gap:7px;}
.pkE .strip .dot{width:7px;height:7px;border-radius:50%;background:var(--lime);}
.pkE .mast{padding:16px 22px 0;}
.pkE .kick{font-family:"Archivo",sans-serif;font-weight:800;font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--green);}
.pkE h1{font-family:"Archivo Black",sans-serif;font-size:30px;line-height:.92;letter-spacing:-.02em;text-transform:uppercase;margin:3px 0 5px;}
.pkE .venue{font-style:italic;font-size:13.5px;color:var(--mute);padding-bottom:11px;border-bottom:3px double var(--ink);}
.pkE .score{display:flex;align-items:center;justify-content:space-between;padding:24px 18px 18px;gap:4px;position:relative;overflow:hidden;}
.pkE .score .team,.pkE .score .ps,.pkE .score .colon{position:relative;z-index:1;}
.pkE .team{display:flex;flex-direction:column;align-items:center;gap:9px;width:92px;}
.pkE .team .fl{width:50px;height:34px;object-fit:cover;box-shadow:0 0 0 1px rgba(0,0,0,.25);}
.pkE .team .nm{font-family:"Archivo Black",sans-serif;font-size:14px;text-transform:uppercase;line-height:1;text-align:center;}
.pkE .team .sd{font-family:"Archivo",sans-serif;font-weight:800;font-size:9px;letter-spacing:.14em;text-transform:uppercase;}
.pkE .team.h .sd{color:var(--green);} .pkE .team.a .sd{color:var(--mute);}
.pkE .colon{font-family:"Rajdhani",sans-serif;font-weight:700;font-size:32px;color:var(--mute);padding-bottom:8px;}
.pkE .boost{margin:2px 20px 0;display:flex;align-items:center;gap:11px;padding:11px 13px;border:1.5px solid var(--green);
  background:transparent;cursor:pointer;text-align:left;width:calc(100% - 40px);font-family:"Archivo",sans-serif;}
.pkE .boost.on{background:var(--green);}
.pkE .boost .ic{width:32px;height:32px;flex-shrink:0;display:flex;align-items:center;justify-content:center;background:var(--ink);color:var(--lime);}
.pkE .boost.on .ic{background:var(--lime);color:var(--ink);}
.pkE .boost .tx{flex:1;}
.pkE .boost .t{display:block;font-weight:800;font-size:13px;letter-spacing:.02em;color:var(--green);}
.pkE .boost.on .t{color:#fff;}
.pkE .boost .s{display:block;font-family:"Spectral",serif;font-style:italic;font-size:11.5px;color:var(--mute);margin-top:1px;}
.pkE .boost.on .s{color:rgba(255,255,255,.85);font-style:normal;font-family:"Archivo",sans-serif;}
.pkE .boost .sw{width:42px;height:24px;flex-shrink:0;background:#d8d2c2;padding:3px;display:flex;}
.pkE .boost.on .sw{background:rgba(255,255,255,.35);justify-content:flex-end;}
.pkE .boost .sw i{width:18px;height:18px;background:#fff;display:block;}
.pkE .rival{margin:15px 22px 0;padding-top:12px;border-top:1px solid rgba(21,39,29,.3);font-style:italic;
  font-size:13px;line-height:1.45;}
.pkE .rival .tag{font-family:"Archivo",sans-serif;font-style:normal;font-weight:800;font-size:9px;letter-spacing:.12em;
  text-transform:uppercase;color:var(--green);margin-right:6px;}
.pkE .rival b{font-style:normal;font-family:"Archivo Black",sans-serif;}
.pkE .sp{flex:1;}
.pkE .cta{margin:0 18px;padding:15px;background:var(--green);color:#fff;font-family:"Archivo",sans-serif;font-weight:800;
  font-size:14px;letter-spacing:.05em;text-transform:uppercase;display:flex;align-items:center;justify-content:center;gap:10px;cursor:pointer;white-space:nowrap;}
.pkE .cta .pill{font-family:"Rajdhani",sans-serif;font-weight:700;background:rgba(0,0,0,.2);padding:2px 10px;letter-spacing:.04em;white-space:nowrap;}
`);

function PickerProgEditorial() {
  const [h, setH] = React.useState(2);
  const [a, setA] = React.useState(1);
  const [boost, setBoost] = React.useState(true);
  const pts = boost ? SCORING.exact * 2 : SCORING.exact;
  return (
    <div className="pkE">
      <PhoneStatusBar tint="#15271d" />
      <div className="strip">
        <span className="live"><span className="dot" />Matchday 01 · Group C</span>
        <span>Sat 13 Jun</span>
      </div>
      <div className="mast">
        <div className="kick">Predict the score</div>
        <h1>Brazil v Morocco</h1>
        <div className="venue">MetLife Stadium · kick-off 22:00</div>
      </div>
      <div className="score">
        <PitchLines color="rgba(10,125,60,.20)" />
        <div className="team h">
          <img className="fl" src={flagUrl('BRA')} alt="" />
          <span className="nm">Brazil</span><span className="sd">Home</span>
        </div>
        <ProgStep value={h} onChange={setH} />
        <span className="colon">:</span>
        <ProgStep value={a} onChange={setA} />
        <div className="team a">
          <img className="fl" src={flagUrl('MAR')} alt="" />
          <span className="nm">Morocco</span><span className="sd">Away</span>
        </div>
      </div>
      <button className={`boost${boost ? ' on' : ''}`} onClick={() => setBoost(!boost)}>
        <span className="ic">{PK_BOLT(boost ? '#15271d' : '#c6f24e')}</span>
        <span className="tx">
          <span className="t">{boost ? 'Boosted ×2' : 'Boost this pick'}</span>
          <span className="s">{boost ? 'Double if exact — zero if you miss' : 'Double-or-nothing on the exact score'}</span>
        </span>
        <span className="sw"><i /></span>
      </button>
      <p className="rival">
        <span className="tag">Rival · Kiko</span>
        Called it <b>1–2 Morocco</b> — “enjoy the silver.”
      </p>
      <div className="sp" />
      <button className="cta">
        Lock in
        <span className="pill">{h}–{a}</span>
        +{pts} pts
      </button>
      <HomeBar tint="rgba(21,39,29,.35)" />
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// MOBILE — BROADCAST LEAN (≈2.5)
// ═══════════════════════════════════════════════════════════════
pkInject('pkB-styles', `
.pkB{--paper:#f3eee1;--ink:#15271d;--green:#0a7d3c;--green-d:#06532a;--lime:#cdfa57;--mute:#6c7268;
  background:var(--paper);color:var(--ink);height:100%;display:flex;flex-direction:column;font-family:"Archivo",sans-serif;}
.pkB *{box-sizing:border-box;margin:0;padding:0;}
.pkB .band{background:linear-gradient(100deg,var(--green-d),var(--green));color:#fff;position:relative;overflow:hidden;
  padding:12px 22px 16px;border-bottom:4px solid var(--ink);}
.pkB .band::after{content:'';position:absolute;inset:0;pointer-events:none;
  background-image:repeating-linear-gradient(90deg,rgba(255,255,255,.06) 0 56px,rgba(0,0,0,.05) 56px 112px);}
.pkB .band .row1{position:relative;z-index:1;display:flex;justify-content:space-between;align-items:center;}
.pkB .live{display:flex;align-items:center;gap:7px;background:rgba(255,255,255,.15);padding:5px 11px;
  font-weight:700;font-size:10px;letter-spacing:.14em;text-transform:uppercase;}
.pkB .live .dot{width:7px;height:7px;border-radius:50%;background:var(--lime);}
.pkB .band .meta{font-family:"Rajdhani",sans-serif;font-weight:700;font-size:14px;letter-spacing:.04em;}
.pkB .band h1{position:relative;z-index:1;font-family:"Archivo Black",sans-serif;font-size:23px;letter-spacing:-.01em;
  text-transform:uppercase;line-height:1;margin-top:12px;}
.pkB .band .ven{position:relative;z-index:1;font-size:11px;letter-spacing:.04em;opacity:.8;margin-top:5px;text-transform:uppercase;}
.pkB .score{display:flex;align-items:center;justify-content:space-between;padding:26px 16px 20px;gap:2px;position:relative;overflow:hidden;}
.pkB .score .team,.pkB .score .ps,.pkB .score .colon{position:relative;z-index:1;}
.pkB .team{display:flex;flex-direction:column;align-items:center;gap:9px;width:86px;}
.pkB .team .fl{width:54px;height:36px;object-fit:cover;box-shadow:0 0 0 1px rgba(0,0,0,.2);}
.pkB .team .nm{font-family:"Archivo Black",sans-serif;font-size:13px;text-transform:uppercase;line-height:1;text-align:center;}
.pkB .team .sd{font-weight:800;font-size:9px;letter-spacing:.14em;text-transform:uppercase;}
.pkB .team.h .sd{color:var(--green);} .pkB .team.a .sd{color:var(--mute);}
.pkB .colon{font-family:"Rajdhani",sans-serif;font-weight:700;font-size:40px;color:var(--mute);padding-bottom:14px;}
.pkB .boost{margin:0 18px;display:flex;align-items:center;gap:11px;padding:12px 14px;border:1.5px solid var(--green);
  background:transparent;cursor:pointer;text-align:left;width:calc(100% - 36px);}
.pkB .boost.on{background:var(--green);}
.pkB .boost .ic{width:34px;height:34px;flex-shrink:0;display:flex;align-items:center;justify-content:center;background:var(--ink);color:var(--lime);}
.pkB .boost.on .ic{background:var(--lime);color:var(--ink);}
.pkB .boost .tx{flex:1;}
.pkB .boost .t{display:block;font-weight:800;font-size:13.5px;color:var(--green);}
.pkB .boost.on .t{color:#fff;}
.pkB .boost .s{display:block;font-size:11.5px;color:var(--mute);margin-top:1px;}
.pkB .boost.on .s{color:rgba(255,255,255,.85);}
.pkB .boost .sw{width:44px;height:25px;flex-shrink:0;background:#d8d2c2;padding:3px;display:flex;}
.pkB .boost.on .sw{background:rgba(255,255,255,.35);justify-content:flex-end;}
.pkB .boost .sw i{width:19px;height:19px;background:#fff;display:block;}
.pkB .rival{margin:16px 18px 0;background:#fbf8ef;border:1px solid rgba(21,39,29,.25);border-left:4px solid var(--green);
  padding:11px 13px;font-size:12.5px;line-height:1.45;}
.pkB .rival .tag{font-weight:800;font-size:9px;letter-spacing:.12em;text-transform:uppercase;color:var(--green);margin-right:6px;}
.pkB .rival b{font-family:"Archivo Black",sans-serif;}
.pkB .sp{flex:1;}
.pkB .cta{margin:0 18px;padding:16px;background:var(--green);color:#fff;font-weight:800;font-size:14px;letter-spacing:.05em;
  text-transform:uppercase;display:flex;align-items:center;justify-content:center;gap:10px;cursor:pointer;white-space:nowrap;}
.pkB .cta .pill{font-family:"Rajdhani",sans-serif;font-weight:700;background:rgba(0,0,0,.2);padding:3px 11px;letter-spacing:.05em;white-space:nowrap;}
`);

function PickerProgBroadcast() {
  const [h, setH] = React.useState(2);
  const [a, setA] = React.useState(1);
  const [boost, setBoost] = React.useState(true);
  const pts = boost ? SCORING.exact * 2 : SCORING.exact;
  return (
    <div className="pkB">
      <div style={{ background: '#06532a' }}><PhoneStatusBar tint="#fff" /></div>
      <div className="band">
        <div className="row1">
          <span className="live"><span className="dot" />Live picks open</span>
          <span className="meta">GRP C · 22:00</span>
        </div>
        <h1>Brazil vs Morocco</h1>
        <div className="ven">MetLife Stadium · Sat 13 Jun</div>
      </div>
      <div className="score">
        <PitchLines color="rgba(10,125,60,.20)" />
        <div className="team h">
          <img className="fl" src={flagUrl('BRA')} alt="" />
          <span className="nm">Brazil</span><span className="sd">Home</span>
        </div>
        <ProgStep value={h} onChange={setH} size="lg" />
        <span className="colon">:</span>
        <ProgStep value={a} onChange={setA} size="lg" />
        <div className="team a">
          <img className="fl" src={flagUrl('MAR')} alt="" />
          <span className="nm">Morocco</span><span className="sd">Away</span>
        </div>
      </div>
      <button className={`boost${boost ? ' on' : ''}`} onClick={() => setBoost(!boost)}>
        <span className="ic">{PK_BOLT(boost ? '#15271d' : '#cdfa57')}</span>
        <span className="tx">
          <span className="t">{boost ? 'Boosted ×2' : 'Boost this pick'}</span>
          <span className="s">{boost ? 'Double if exact — zero if you miss' : 'Double-or-nothing on the exact score'}</span>
        </span>
        <span className="sw"><i /></span>
      </button>
      <div className="rival">
        <span className="tag">Rival · Kiko</span>
        Called it <b>1–2 Morocco</b> — “enjoy the silver.”
      </div>
      <div className="sp" />
      <button className="cta">
        Lock it in
        <span className="pill">{h} : {a}</span>
        +{pts} pts
      </button>
      <HomeBar tint="rgba(21,39,29,.35)" />
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// DESKTOP — PROGRAMME
// ═══════════════════════════════════════════════════════════════
pkInject('pkD-styles', `
.pkD{--paper:#f3eee1;--ink:#15271d;--green:#0a7d3c;--green-d:#06532a;--lime:#cdfa57;--mute:#6c7268;
  background:var(--paper);color:var(--ink);height:100%;width:100%;overflow:hidden;display:flex;flex-direction:column;font-family:"Archivo",sans-serif;}
.pkD *{box-sizing:border-box;margin:0;padding:0;}
.pkD .head{background:linear-gradient(100deg,var(--green-d),var(--green));color:#fff;padding:18px 40px;position:relative;overflow:hidden;
  display:flex;align-items:center;gap:18px;border-bottom:4px solid var(--ink);}
.pkD .head::after{content:'';position:absolute;inset:0;pointer-events:none;
  background-image:repeating-linear-gradient(90deg,rgba(255,255,255,.06) 0 60px,rgba(0,0,0,.05) 60px 120px);}
.pkD .live{z-index:1;display:flex;align-items:center;gap:8px;background:rgba(255,255,255,.15);padding:6px 13px;
  font-weight:700;font-size:11px;letter-spacing:.16em;text-transform:uppercase;}
.pkD .live .dot{width:8px;height:8px;border-radius:50%;background:var(--lime);}
.pkD .head h1{z-index:1;font-family:"Archivo Black",sans-serif;font-size:30px;letter-spacing:-.01em;text-transform:uppercase;line-height:1;white-space:nowrap;}
.pkD .head .pts{z-index:1;margin-left:auto;text-align:right;}
.pkD .head .pts .v{font-family:"Rajdhani",sans-serif;font-weight:700;font-size:26px;line-height:1;white-space:nowrap;}
.pkD .head .pts .l{font-size:10px;letter-spacing:.12em;text-transform:uppercase;opacity:.85;white-space:nowrap;}
.pkD .body{flex:1;display:grid;grid-template-columns:1.18fr 1fr;}
.pkD .left{padding:24px 36px;border-right:1px solid rgba(21,39,29,.2);}
.pkD .ctx{font-family:"Rajdhani",sans-serif;font-weight:700;font-size:15px;letter-spacing:.04em;text-transform:uppercase;
  color:var(--mute);padding-bottom:12px;border-bottom:3px double var(--ink);margin-bottom:8px;}
.pkD .hero{display:flex;align-items:center;justify-content:center;gap:22px;padding:22px 0 6px;position:relative;overflow:hidden;}
.pkD .hero .team,.pkD .hero .ps,.pkD .hero .colon{position:relative;z-index:1;}
.pkD .team{display:flex;flex-direction:column;align-items:center;gap:11px;width:120px;}
.pkD .team .fl{width:74px;height:50px;object-fit:cover;box-shadow:0 0 0 1px rgba(0,0,0,.2);}
.pkD .team .nm{font-family:"Archivo Black",sans-serif;font-size:18px;text-transform:uppercase;line-height:1;}
.pkD .team .sd{font-weight:800;font-size:10px;letter-spacing:.14em;text-transform:uppercase;}
.pkD .team.h .sd{color:var(--green);} .pkD .team.a .sd{color:var(--mute);}
.pkD .colon{font-family:"Rajdhani",sans-serif;font-weight:700;font-size:46px;color:var(--mute);padding-bottom:18px;}
.pkD .boost{margin-top:20px;display:flex;align-items:center;gap:13px;padding:14px 16px;border:1.5px solid var(--green);
  background:transparent;cursor:pointer;text-align:left;width:100%;}
.pkD .boost.on{background:var(--green);}
.pkD .boost .ic{width:38px;height:38px;flex-shrink:0;display:flex;align-items:center;justify-content:center;background:var(--ink);color:var(--lime);}
.pkD .boost.on .ic{background:var(--lime);color:var(--ink);}
.pkD .boost .tx{flex:1;}
.pkD .boost .t{display:block;font-weight:800;font-size:15px;color:var(--green);}
.pkD .boost.on .t{color:#fff;}
.pkD .boost .s{display:block;font-size:12.5px;color:var(--mute);margin-top:2px;}
.pkD .boost.on .s{color:rgba(255,255,255,.85);}
.pkD .boost .sw{width:48px;height:27px;flex-shrink:0;background:#d8d2c2;padding:3px;display:flex;}
.pkD .boost.on .sw{background:rgba(255,255,255,.35);justify-content:flex-end;}
.pkD .boost .sw i{width:21px;height:21px;background:#fff;display:block;}
.pkD .right{padding:24px 36px;display:flex;flex-direction:column;}
.pkD .sect{font-weight:800;font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--green);
  display:flex;align-items:center;gap:9px;margin-bottom:13px;}
.pkD .sect::before{content:'';width:3px;height:13px;background:var(--green);}
.pkD .stake{display:flex;align-items:baseline;gap:10px;margin-bottom:22px;}
.pkD .stake .big{font-family:"Rajdhani",sans-serif;font-weight:700;font-size:46px;color:var(--green);line-height:1;}
.pkD .stake .cap{font-size:13px;color:var(--mute);}
.pkD .stake .cap b{color:var(--ink);font-family:"Archivo Black",sans-serif;}
.pkD .rival{background:#fbf8ef;border:1px solid rgba(21,39,29,.25);border-left:4px solid var(--green);
  padding:13px 14px;margin-bottom:22px;font-size:13px;line-height:1.45;}
.pkD .rival .tag{font-weight:800;font-size:9px;letter-spacing:.12em;text-transform:uppercase;color:var(--green);margin-right:6px;}
.pkD .rival b{font-family:"Archivo Black",sans-serif;}
.pkD .cbar{display:flex;align-items:center;gap:11px;margin-bottom:9px;}
.pkD .cbar .cl{width:66px;font-weight:700;font-size:13px;flex-shrink:0;}
.pkD .cbar.lead .cl{color:var(--ink);} .pkD .cbar .cl{color:var(--mute);}
.pkD .cbar .track{flex:1;height:18px;background:#e3ddcd;overflow:hidden;}
.pkD .cbar .fill{height:100%;background:var(--green);}
.pkD .cbar.sub .fill{background:#b9c2ad;}
.pkD .cbar .pc{width:36px;text-align:right;font-family:"Rajdhani",sans-serif;font-weight:700;font-size:14px;}
.pkD .foot{display:flex;justify-content:flex-end;align-items:center;gap:12px;padding:16px 40px;border-top:1px solid rgba(21,39,29,.2);background:#efe9da;}
.pkD .foot .cancel{font-weight:800;font-size:12.5px;letter-spacing:.05em;text-transform:uppercase;color:var(--green);
  border:1.5px solid var(--green);background:transparent;padding:11px 20px;cursor:pointer;}
.pkD .foot .lock{font-weight:800;font-size:13px;letter-spacing:.05em;text-transform:uppercase;color:#fff;background:var(--green);
  padding:12px 24px;cursor:pointer;display:flex;align-items:center;gap:10px;}
.pkD .foot .lock .pill{font-family:"Rajdhani",sans-serif;font-weight:700;background:rgba(0,0,0,.2);padding:2px 10px;white-space:nowrap;}
`);

function PickerProgDesktop() {
  const [h, setH] = React.useState(2);
  const [a, setA] = React.useState(1);
  const [boost, setBoost] = React.useState(true);
  const pts = boost ? SCORING.exact * 2 : SCORING.exact;
  return (
    <div className="pkD">
      <div className="head">
        <span className="live"><span className="dot" />Predict · Matchday 1</span>
        <h1>Brazil v Morocco</h1>
        <div className="pts"><div className="v">247 PTS</div><div className="l">Kiko · Rank 3</div></div>
      </div>
      <div className="body">
        <div className="left">
          <div className="ctx">Group C · Sat 13 Jun · 22:00 · MetLife Stadium</div>
          <div className="hero">
            <PitchLines color="rgba(10,125,60,.18)" big />
            <div className="team h">
              <img className="fl" src={flagUrl('BRA')} alt="" />
              <span className="nm">Brazil</span><span className="sd">Home</span>
            </div>
            <ProgStep value={h} onChange={setH} size="lg" />
            <span className="colon">:</span>
            <ProgStep value={a} onChange={setA} size="lg" />
            <div className="team a">
              <img className="fl" src={flagUrl('MAR')} alt="" />
              <span className="nm">Morocco</span><span className="sd">Away</span>
            </div>
          </div>
          <button className={`boost${boost ? ' on' : ''}`} onClick={() => setBoost(!boost)}>
            <span className="ic">{PK_BOLT(boost ? '#15271d' : '#cdfa57')}</span>
            <span className="tx">
              <span className="t">{boost ? 'Boosted ×2' : 'Boost this pick'}</span>
              <span className="s">{boost ? 'Double if exact — zero if you miss it' : 'Double-or-nothing on the exact score'}</span>
            </span>
            <span className="sw"><i /></span>
          </button>
        </div>
        <div className="right">
          <div className="sect">At stake</div>
          <div className="stake">
            <span className="big">+{pts}</span>
            <span className="cap">pts if your <b>{h}–{a}</b> is exact</span>
          </div>
          <div className="sect">Your rival</div>
          <div className="rival">
            <span className="tag">Kiko · 2nd</span>
            Called it <b>1–2 Morocco</b> — “enjoy the silver.”
          </div>
          <div className="sect">League consensus · 12 in</div>
          <div className="cbar lead"><span className="cl">Brazil</span><span className="track"><span className="fill" style={{ width: '64%' }} /></span><span className="pc">64%</span></div>
          <div className="cbar sub"><span className="cl">Draw</span><span className="track"><span className="fill" style={{ width: '21%' }} /></span><span className="pc">21%</span></div>
          <div className="cbar sub"><span className="cl">Morocco</span><span className="track"><span className="fill" style={{ width: '15%' }} /></span><span className="pc">15%</span></div>
        </div>
      </div>
      <div className="foot">
        <button className="cancel">Cancel</button>
        <button className="lock">Lock in <span className="pill">{h}–{a}</span> +{pts}</button>
      </div>
    </div>
  );
}

Object.assign(window, { PickerProgEditorial, PickerProgBroadcast, PickerProgDesktop, ProgStep });
