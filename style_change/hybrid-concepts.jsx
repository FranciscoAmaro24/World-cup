// ─────────────────────────────────────────────────────────────
// hybrid-concepts.jsx — "Matchday Programme" — the blend between
// A·Broadsheet (ink-on-paper editorial) and C·Broadcast (TV
// scoreboard). Two points on the spectrum:
//   E1 · Programme — leans editorial (paper, rules, serif dek)
//   E2 · Broadcast — leans TV (green header band, LED boards)
// Both keep: cream paper, Archivo Black editorial display,
// Rajdhani sporty numbers, pitch-green + lime, square corners.
// Depends on wc-data.jsx (flagUrl, NAME, GROUP_COLORS).
// ─────────────────────────────────────────────────────────────

if (typeof document !== 'undefined' && !document.getElementById('hybrid-fonts')) {
  const l = document.createElement('link');
  l.id = 'hybrid-fonts';
  l.rel = 'stylesheet';
  l.href = 'https://fonts.googleapis.com/css2?family=Archivo+Black&family=Archivo:wght@400;500;600;700;800&family=Spectral:ital,wght@0,400;0,600;1,400&family=Rajdhani:wght@500;600;700&display=swap';
  document.head.appendChild(l);
}

const HFX = [
  { h: 'BRA', a: 'MAR', grp: 'C', time: '22:00', day: 'SAT 13 JUN', pred: [2, 1] },
  { h: 'QAT', a: 'SUI', grp: 'B', time: '19:00', day: 'SAT 13 JUN', pred: [0, 2] },
  { h: 'ESP', a: 'CPV', grp: 'H', time: '21:00', day: 'SUN 14 JUN', pred: [3, 0] },
  { h: 'USA', a: 'PAR', grp: 'D', time: '01:00', day: 'SUN 14 JUN', pred: null },
  { h: 'MEX', a: 'RSA', grp: 'A', time: '19:00', day: 'THU 11 JUN', pred: null },
];

function hInject(id, css) {
  if (typeof document === 'undefined' || document.getElementById(id)) return;
  const s = document.createElement('style');
  s.id = id; s.textContent = css; document.head.appendChild(s);
}

// ═══════════════════════════════════════════════════════════════
// E1 — PROGRAMME (editorial lean, ~1.5 on the 1↔3 line)
// ═══════════════════════════════════════════════════════════════
hInject('hE-styles', `
.hE{--paper:#f5f0e4;--ink:#15271d;--green:#0a7d3c;--green-d:#075e2d;--lime:#c6f24e;--mute:#6c7268;
  background:var(--paper);color:var(--ink);height:100%;width:100%;overflow:hidden;
  font-family:"Spectral",Georgia,serif;display:flex;flex-direction:column;}
.hE *{box-sizing:border-box;margin:0;padding:0;}
.hE .strip{background:var(--green);color:#fff;display:flex;align-items:center;justify-content:space-between;
  padding:9px 40px;font-family:"Archivo",sans-serif;font-size:11px;font-weight:700;letter-spacing:.18em;text-transform:uppercase;}
.hE .strip .live{display:flex;align-items:center;gap:9px;}
.hE .strip .dot{width:8px;height:8px;border-radius:50%;background:var(--lime);}
.hE .mast{padding:22px 40px 0;}
.hE h1{font-family:"Archivo Black",sans-serif;font-size:62px;line-height:.88;letter-spacing:-.02em;text-transform:uppercase;}
.hE .dek{font-style:italic;font-size:16px;color:var(--mute);padding:8px 0 12px;border-bottom:3px double var(--ink);}
.hE .cols{flex:1;display:grid;grid-template-columns:1fr 268px;}
.hE .list{border-right:1px solid var(--ink);}
.hE .row{display:grid;grid-template-columns:60px 1fr 116px 80px;align-items:center;gap:14px;
  padding:14px 22px 14px 40px;border-bottom:1px solid rgba(21,39,29,.45);}
.hE .grp{font-family:"Archivo Black",sans-serif;font-size:12px;color:var(--green);}
.hE .match{display:flex;align-items:center;}
.hE .tm{display:flex;align-items:center;gap:10px;flex:1;min-width:0;}
.hE .tm.away{flex-direction:row-reverse;text-align:right;}
.hE .tm .nm{font-family:"Archivo",sans-serif;font-weight:800;font-size:19px;text-transform:uppercase;line-height:1;}
.hE .vs{font-style:italic;color:var(--mute);font-size:14px;padding:0 14px;}
.hE .fl{width:32px;height:22px;object-fit:cover;box-shadow:0 0 0 1px rgba(0,0,0,.25);flex-shrink:0;}
.hE .board{display:flex;flex-direction:column;align-items:center;gap:4px;}
.hE .board .bx{font-family:"Rajdhani",sans-serif;font-weight:700;font-size:22px;background:var(--ink);color:var(--lime);
  padding:2px 13px;letter-spacing:.06em;line-height:1.1;white-space:nowrap;}
.hE .board .lab{font-family:"Archivo",sans-serif;font-size:8px;letter-spacing:.16em;text-transform:uppercase;color:var(--mute);}
.hE .cta{font-family:"Archivo",sans-serif;font-size:11.5px;font-weight:800;letter-spacing:.1em;text-transform:uppercase;
  color:#fff;background:var(--green);padding:8px 10px;text-align:center;cursor:pointer;white-space:nowrap;}
.hE .when{font-family:"Rajdhani",sans-serif;text-align:right;}
.hE .when .t{font-weight:700;font-size:22px;line-height:1;}
.hE .when .d{font-family:"Archivo",sans-serif;font-size:8.5px;letter-spacing:.12em;color:var(--mute);text-transform:uppercase;margin-top:3px;white-space:nowrap;}
.hE .aside{padding:20px 24px;}
.hE .aside h3{font-family:"Archivo Black",sans-serif;font-size:12px;letter-spacing:.06em;text-transform:uppercase;
  padding-bottom:9px;border-bottom:2px solid var(--ink);margin-bottom:12px;}
.hE .stat{display:flex;justify-content:space-between;align-items:baseline;padding:8px 0;border-bottom:1px solid rgba(21,39,29,.2);}
.hE .stat .n{font-family:"Archivo",sans-serif;font-weight:600;font-size:14px;}
.hE .stat.me .n{color:var(--green);font-weight:800;}
.hE .stat .v{font-family:"Rajdhani",sans-serif;font-weight:700;font-size:18px;}
.hE .pull{margin-top:16px;font-style:italic;font-size:16px;line-height:1.45;}
.hE .pull b{font-style:normal;font-family:"Archivo Black",sans-serif;color:var(--green);}
`);

function HybridEditorial() {
  return (
    <div className="hE">
      <div className="strip">
        <span className="live"><span className="dot" />Matchday 01 · Group Stage</span>
        <span>Sat 13 June 2026</span>
      </div>
      <div className="mast">
        <h1>The Fixtures</h1>
        <p className="dek">Five ties to call before kick-off — lock your scorelines, defend your table.</p>
      </div>
      <div className="cols">
        <div className="list">
          {HFX.map((m, i) => (
            <div className="row" key={i}>
              <span className="grp">GRP&nbsp;{m.grp}</span>
              <div className="match">
                <div className="tm">
                  <img className="fl" src={flagUrl(m.h)} alt="" />
                  <span className="nm">{NAME[m.h]}</span>
                </div>
                <span className="vs">v</span>
                <div className="tm away">
                  <img className="fl" src={flagUrl(m.a)} alt="" />
                  <span className="nm">{NAME[m.a]}</span>
                </div>
              </div>
              {m.pred
                ? <div className="board"><span className="bx">{m.pred[0]}–{m.pred[1]}</span><span className="lab">Your call</span></div>
                : <div className="cta">Predict ▸</div>}
              <div className="when"><div className="t">{m.time}</div><div className="d">{m.day}</div></div>
            </div>
          ))}
        </div>
        <div className="aside">
          <h3>The Standings</h3>
          <div className="stat"><span className="n">Kiko</span><span className="v">247</span></div>
          <div className="stat"><span className="n">Marta</span><span className="v">243</span></div>
          <div className="stat me"><span className="n">You</span><span className="v">231</span></div>
          <p className="pull">You sit <b>3rd</b> — a clean matchday puts the silver within reach.</p>
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// E2 — BROADCAST PROGRAMME (TV lean, ~2.5 on the 1↔3 line)
// ═══════════════════════════════════════════════════════════════
hInject('hB-styles', `
.hB{--paper:#f3eee1;--ink:#15271d;--green:#0a7d3c;--green-d:#06532a;--lime:#cdfa57;--mute:#6c7268;
  background:var(--paper);color:var(--ink);height:100%;width:100%;overflow:hidden;
  font-family:"Archivo",sans-serif;display:flex;flex-direction:column;}
.hB *{box-sizing:border-box;margin:0;padding:0;}
.hB .head{background:linear-gradient(100deg,var(--green-d),var(--green));color:#fff;padding:20px 36px;
  display:flex;align-items:center;gap:18px;position:relative;overflow:hidden;border-bottom:4px solid var(--ink);}
.hB .head::after{content:'';position:absolute;inset:0;pointer-events:none;
  background-image:repeating-linear-gradient(90deg,rgba(255,255,255,.06) 0 2px,transparent 2px 66px);}
.hB .live{z-index:1;display:flex;align-items:center;gap:8px;background:rgba(255,255,255,.14);padding:6px 13px;
  font-weight:700;font-size:11px;letter-spacing:.16em;text-transform:uppercase;}
.hB .live .dot{width:8px;height:8px;border-radius:50%;background:var(--lime);}
.hB .head h1{z-index:1;font-family:"Archivo Black",sans-serif;font-size:33px;letter-spacing:-.01em;
  text-transform:uppercase;line-height:1;white-space:nowrap;}
.hB .head .pts{z-index:1;margin-left:auto;text-align:right;}
.hB .head .pts .v{font-family:"Rajdhani",sans-serif;font-weight:700;font-size:28px;line-height:1;white-space:nowrap;}
.hB .head .pts .l{font-size:10px;letter-spacing:.12em;text-transform:uppercase;opacity:.85;white-space:nowrap;}
.hB .list{flex:1;padding:20px 36px;display:flex;flex-direction:column;gap:11px;}
.hB .card{background:#fbf8ef;border:1px solid rgba(21,39,29,.3);border-left:5px solid var(--green);
  display:grid;grid-template-columns:122px 1fr 146px;align-items:center;}
.hB .when{padding:13px 16px;border-right:1px solid rgba(21,39,29,.16);}
.hB .when .t{font-family:"Rajdhani",sans-serif;font-weight:700;font-size:24px;line-height:1;}
.hB .when .d{font-size:10px;letter-spacing:.1em;text-transform:uppercase;color:var(--mute);white-space:nowrap;}
.hB .when .g{display:inline-block;margin-top:6px;font-weight:800;font-size:10px;letter-spacing:.06em;
  text-transform:uppercase;color:#fff;padding:1px 8px;}
.hB .mid{display:flex;align-items:center;justify-content:center;gap:16px;padding:11px;}
.hB .tm{display:flex;align-items:center;gap:11px;flex:1;min-width:0;}
.hB .tm.away{flex-direction:row-reverse;}
.hB .tm .nm{font-weight:800;font-size:20px;text-transform:uppercase;line-height:1;}
.hB .fl{width:38px;height:26px;object-fit:cover;box-shadow:0 0 0 1px rgba(0,0,0,.18);flex-shrink:0;}
.hB .board{font-family:"Rajdhani",sans-serif;font-weight:700;background:var(--ink);color:var(--lime);font-size:25px;
  letter-spacing:.05em;padding:4px 14px;min-width:74px;text-align:center;white-space:nowrap;flex-shrink:0;}
.hB .board.empty{background:transparent;color:#9aa89e;border:1px dashed rgba(21,39,29,.4);}
.hB .act{padding:0 16px;text-align:right;}
.hB .act button{font-weight:800;font-size:12px;letter-spacing:.08em;text-transform:uppercase;padding:9px 18px;cursor:pointer;}
.hB .act .go{background:var(--green);color:#fff;}
.hB .act .ed{background:transparent;color:var(--green);border:1.5px solid var(--green);}
`);

function HybridBroadcast() {
  return (
    <div className="hB">
      <div className="head">
        <span className="live"><span className="dot" />Matchday 1</span>
        <h1>Fixtures &amp; Predictions</h1>
        <div className="pts"><div className="v">247 PTS</div><div className="l">Kiko · Rank 3</div></div>
      </div>
      <div className="list">
        {HFX.map((m, i) => (
          <div className="card" key={i} style={{ borderLeftColor: GROUP_COLORS[m.grp] }}>
            <div className="when">
              <div className="t">{m.time}</div>
              <div className="d">{m.day}</div>
              <span className="g" style={{ background: GROUP_COLORS[m.grp] }}>GRP {m.grp}</span>
            </div>
            <div className="mid">
              <div className="tm">
                <img className="fl" src={flagUrl(m.h)} alt="" />
                <span className="nm">{NAME[m.h]}</span>
              </div>
              <div className={`board${m.pred ? '' : ' empty'}`}>{m.pred ? `${m.pred[0]} : ${m.pred[1]}` : '– : –'}</div>
              <div className="tm away">
                <img className="fl" src={flagUrl(m.a)} alt="" />
                <span className="nm">{NAME[m.a]}</span>
              </div>
            </div>
            <div className="act">
              {m.pred ? <button className="ed">Edit pick</button> : <button className="go">Predict</button>}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

Object.assign(window, { HybridEditorial, HybridBroadcast });
