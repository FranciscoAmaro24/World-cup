// ─────────────────────────────────────────────────────────────
// style-concepts.jsx — Four DISTINCT visual directions for the
// predictor, deliberately breaking away from the dark-neutral /
// rounded-corner / app-nav look. Same screen (Matchday Fixtures)
// rendered four ways so the aesthetics can be compared directly.
// Depends on wc-data.jsx (flagUrl, NAME, GROUP_COLORS).
// ─────────────────────────────────────────────────────────────

// Fonts for the four universes (one injection)
if (typeof document !== 'undefined' && !document.getElementById('concept-fonts')) {
  const l = document.createElement('link');
  l.id = 'concept-fonts';
  l.rel = 'stylesheet';
  l.href = 'https://fonts.googleapis.com/css2?family=Archivo+Black&family=Archivo:wght@400;500;600;700;800&family=Spectral:ital,wght@0,400;0,600;1,400&family=Space+Grotesk:wght@400;500;600;700&family=Space+Mono:wght@400;700&family=Rajdhani:wght@500;600;700&family=Barlow+Semi+Condensed:wght@400;500;600;700&family=Bricolage+Grotesque:opsz,wght@12..96,400;12..96,600;12..96,800&family=DM+Mono:wght@400;500&display=swap';
  document.head.appendChild(l);
}

// Shared fixture set used by every concept
const SC_FX = [
  { h: 'BRA', a: 'MAR', grp: 'C', time: '22:00', day: 'SAT 13 JUN', venue: 'MetLife Stadium', pred: [2, 1] },
  { h: 'QAT', a: 'SUI', grp: 'B', time: '19:00', day: 'SAT 13 JUN', venue: 'Lumen Field',     pred: [0, 2] },
  { h: 'ESP', a: 'CPV', grp: 'H', time: '21:00', day: 'SUN 14 JUN', venue: 'Hard Rock Stadium', pred: [3, 0] },
  { h: 'USA', a: 'PAR', grp: 'D', time: '01:00', day: 'SUN 14 JUN', venue: 'SoFi Stadium',     pred: null },
  { h: 'MEX', a: 'RSA', grp: 'A', time: '19:00', day: 'THU 11 JUN', venue: 'Estadio Azteca',   pred: null },
];

function injectOnce(id, css) {
  if (typeof document === 'undefined' || document.getElementById(id)) return;
  const s = document.createElement('style');
  s.id = id; s.textContent = css; document.head.appendChild(s);
}

// ═══════════════════════════════════════════════════════════════
// CONCEPT A — "BROADSHEET"  ·  sports-page editorial, ink on paper
// ═══════════════════════════════════════════════════════════════
injectOnce('cA-styles', `
.cA{--ink:#16130d;--paper:#f7f3e8;--red:#b51b1b;--rule:#16130d;--mute:#6f685a;
  background:var(--paper);color:var(--ink);height:100%;width:100%;overflow:hidden;
  font-family:"Spectral",Georgia,serif;display:flex;flex-direction:column;}
.cA *{box-sizing:border-box;margin:0;padding:0;}
.cA .mast{padding:26px 40px 0;}
.cA .kicker{display:flex;justify-content:space-between;align-items:flex-end;
  font-family:"Archivo",sans-serif;font-size:11px;font-weight:700;letter-spacing:.22em;
  text-transform:uppercase;color:var(--ink);padding-bottom:8px;border-bottom:3px double var(--rule);}
.cA h1{font-family:"Archivo Black",sans-serif;font-size:74px;line-height:.86;letter-spacing:-.02em;
  text-transform:uppercase;margin:14px 0 4px;}
.cA .dek{font-style:italic;font-size:17px;color:var(--mute);padding-bottom:14px;
  border-bottom:1px solid var(--rule);margin-bottom:0;}
.cA .cols{flex:1;display:grid;grid-template-columns:1fr 280px;}
.cA .list{border-right:1px solid var(--rule);}
.cA .row{display:grid;grid-template-columns:54px 1fr 92px 96px;align-items:center;gap:18px;
  padding:17px 24px 17px 40px;border-bottom:1px solid var(--rule);}
.cA .grp{font-family:"Archivo Black",sans-serif;font-size:13px;letter-spacing:.04em;
  color:var(--red);writing-mode:horizontal-tb;}
.cA .match{display:flex;align-items:center;gap:0;}
.cA .tm{display:flex;align-items:center;gap:11px;flex:1;}
.cA .tm.away{flex-direction:row-reverse;text-align:right;}
.cA .tm .nm{font-family:"Archivo",sans-serif;font-weight:800;font-size:21px;letter-spacing:-.01em;
  text-transform:uppercase;line-height:1;}
.cA .vs{font-style:italic;color:var(--mute);font-size:15px;padding:0 16px;}
.cA .fl{width:34px;height:23px;object-fit:cover;box-shadow:0 0 0 1px rgba(0,0,0,.25);}
.cA .pick{font-family:"Archivo",sans-serif;text-align:center;}
.cA .pick .sc{font-family:"Archivo Black",sans-serif;font-size:23px;line-height:1;}
.cA .pick .lab{font-size:9px;letter-spacing:.16em;text-transform:uppercase;color:var(--mute);margin-top:3px;}
.cA .cta{font-family:"Archivo",sans-serif;font-size:12px;font-weight:800;letter-spacing:.12em;
  text-transform:uppercase;color:var(--red);text-align:right;cursor:pointer;}
.cA .when{font-family:"Archivo",sans-serif;text-align:right;}
.cA .when .t{font-weight:800;font-size:18px;}
.cA .when .d{font-size:9px;letter-spacing:.14em;color:var(--mute);text-transform:uppercase;}
.cA .aside{padding:22px 26px;}
.cA .aside h3{font-family:"Archivo Black",sans-serif;font-size:13px;letter-spacing:.06em;
  text-transform:uppercase;padding-bottom:9px;border-bottom:2px solid var(--rule);margin-bottom:14px;}
.cA .stat{display:flex;justify-content:space-between;align-items:baseline;padding:9px 0;border-bottom:1px solid rgba(22,19,13,.18);}
.cA .stat .n{font-family:"Archivo",sans-serif;font-weight:600;font-size:15px;}
.cA .stat .v{font-family:"Archivo Black",sans-serif;font-size:18px;}
.cA .pull{margin-top:18px;font-style:italic;font-size:18px;line-height:1.4;}
.cA .pull b{font-style:normal;font-family:"Archivo Black",sans-serif;}
`);

function ConceptA() {
  return (
    <div className="cA">
      <div className="mast">
        <div className="kicker">
          <span>The Predictor &middot; Matchday Edition</span>
          <span>Vol. XXVI &middot; Sat 13 June 2026</span>
        </div>
        <h1>The Fixtures</h1>
        <p className="dek">Five ties to call before kick-off — lock your scorelines, defend your table.</p>
      </div>
      <div className="cols">
        <div className="list">
          {SC_FX.map((m, i) => (
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
                ? <div className="pick"><div className="sc">{m.pred[0]}&ndash;{m.pred[1]}</div><div className="lab">Your call</div></div>
                : <div className="cta">Predict &#9656;</div>}
              <div className="when"><div className="t">{m.time}</div><div className="d">{m.day}</div></div>
            </div>
          ))}
        </div>
        <div className="aside">
          <h3>The Standings</h3>
          <div className="stat"><span className="n">Kiko</span><span className="v">247</span></div>
          <div className="stat"><span className="n">Marta</span><span className="v">243</span></div>
          <div className="stat"><span className="n">You</span><span className="v">231</span></div>
          <p className="pull">You sit <b>3rd</b> — a clean matchday puts the silver within reach.</p>
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// CONCEPT B — "TERRACE"  ·  brutalist, hard edges, offset shadows
// ═══════════════════════════════════════════════════════════════
injectOnce('cB-styles', `
.cB{--blue:#2438ff;--yellow:#ffe600;--ink:#0c0c0c;--paper:#f2f0ea;
  background:var(--paper);color:var(--ink);height:100%;width:100%;overflow:hidden;
  font-family:"Space Grotesk",sans-serif;display:flex;flex-direction:column;}
.cB *{box-sizing:border-box;margin:0;padding:0;}
.cB .top{display:flex;align-items:stretch;border-bottom:3px solid var(--ink);}
.cB .top .ttl{flex:1;padding:24px 30px;}
.cB .top .ttl .lbl{font-family:"Space Mono",monospace;font-size:12px;font-weight:700;
  letter-spacing:.1em;text-transform:uppercase;}
.cB .top h1{font-size:58px;font-weight:700;letter-spacing:-.03em;line-height:.9;text-transform:uppercase;margin-top:6px;}
.cB .top .pts{width:230px;background:var(--blue);color:#fff;border-left:3px solid var(--ink);
  padding:22px 26px;display:flex;flex-direction:column;justify-content:center;}
.cB .top .pts .big{font-size:52px;font-weight:700;line-height:.9;letter-spacing:-.02em;}
.cB .top .pts .sub{font-family:"Space Mono",monospace;font-size:12px;letter-spacing:.08em;
  text-transform:uppercase;margin-top:4px;}
.cB .grid{flex:1;padding:26px 30px;display:grid;grid-template-columns:1fr 1fr;gap:20px;align-content:start;overflow:hidden;}
.cB .card{background:#fff;border:3px solid var(--ink);box-shadow:7px 7px 0 var(--ink);padding:0;}
.cB .card .hd{display:flex;justify-content:space-between;align-items:center;
  padding:9px 14px;border-bottom:3px solid var(--ink);background:var(--yellow);}
.cB .card .hd .g{font-family:"Space Mono",monospace;font-size:12px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;}
.cB .card .hd .tm{font-family:"Space Mono",monospace;font-size:12px;font-weight:700;}
.cB .card .bd{padding:15px 16px;display:flex;align-items:center;gap:12px;}
.cB .tm2{flex:1;display:flex;align-items:center;gap:10px;}
.cB .tm2 .nm{font-size:18px;font-weight:700;letter-spacing:-.01em;text-transform:uppercase;line-height:1;}
.cB .fl{width:38px;height:26px;object-fit:cover;border:2px solid var(--ink);}
.cB .sc{font-size:30px;font-weight:700;letter-spacing:-.02em;min-width:64px;text-align:center;}
.cB .ft{display:flex;border-top:3px solid var(--ink);}
.cB .ft button{flex:1;padding:11px;font-family:"Space Mono",monospace;font-size:13px;font-weight:700;
  letter-spacing:.08em;text-transform:uppercase;cursor:pointer;}
.cB .ft .pred{background:var(--blue);color:#fff;}
.cB .ft .edit{background:#fff;color:var(--ink);border-left:3px solid var(--ink);flex:0 0 86px;}
.cB .locked{color:var(--blue);}
`);

function ConceptB() {
  return (
    <div className="cB">
      <div className="top">
        <div className="ttl">
          <div className="lbl">// Matchday 01 — group stage</div>
          <h1>Fixtures</h1>
        </div>
        <div className="pts">
          <div className="big">247</div>
          <div className="sub">your pts &middot; rank #3</div>
        </div>
      </div>
      <div className="grid">
        {SC_FX.slice(0, 4).map((m, i) => (
          <div className="card" key={i}>
            <div className="hd">
              <span className="g">GROUP {m.grp}</span>
              <span className="tm">{m.day} · {m.time}</span>
            </div>
            <div className="bd">
              <div className="tm2">
                <img className="fl" src={flagUrl(m.h)} alt="" />
                <span className="nm">{SHORT[m.h] || m.h}</span>
              </div>
              <div className="sc">{m.pred ? `${m.pred[0]}–${m.pred[1]}` : 'v'}</div>
              <div className="tm2" style={{ justifyContent: 'flex-end' }}>
                <span className="nm">{SHORT[m.a] || m.a}</span>
                <img className="fl" src={flagUrl(m.a)} alt="" />
              </div>
            </div>
            <div className="ft">
              {m.pred
                ? <><button className="pred locked" style={{ background: '#fff', color: '#2438ff' }}>● Locked {m.pred[0]}–{m.pred[1]}</button><button className="edit">Edit</button></>
                : <button className="pred">Predict →</button>}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// CONCEPT C — "BROADCAST"  ·  TV scoreboard / pitch, light & sporty
// ═══════════════════════════════════════════════════════════════
injectOnce('cC-styles', `
.cC{--green:#0a7d3c;--green-d:#075e2d;--lime:#c6f24e;--ink:#11241a;--paper:#eef2ee;
  background:var(--paper);color:var(--ink);height:100%;width:100%;overflow:hidden;
  font-family:"Barlow Semi Condensed",sans-serif;display:flex;flex-direction:column;}
.cC *{box-sizing:border-box;margin:0;padding:0;}
.cC .bcast{background:linear-gradient(100deg,var(--green-d),var(--green));color:#fff;
  padding:18px 34px;display:flex;align-items:center;gap:18px;position:relative;overflow:hidden;}
.cC .bcast::after{content:'';position:absolute;inset:0;background-image:repeating-linear-gradient(90deg,rgba(255,255,255,.07) 0 2px,transparent 2px 64px);pointer-events:none;}
.cC .live{display:flex;align-items:center;gap:8px;background:rgba(255,255,255,.14);
  padding:6px 13px;border-radius:3px;font-family:"Rajdhani",sans-serif;font-weight:700;
  font-size:13px;letter-spacing:.14em;text-transform:uppercase;}
.cC .live .dot{width:8px;height:8px;border-radius:50%;background:var(--lime);box-shadow:0 0 0 0 var(--lime);animation:cCpulse 1.6s infinite;}
@keyframes cCpulse{0%{box-shadow:0 0 0 0 rgba(198,242,78,.6)}70%{box-shadow:0 0 0 9px rgba(198,242,78,0)}100%{box-shadow:0 0 0 0 rgba(198,242,78,0)}}
.cC .bcast h1{font-family:"Rajdhani",sans-serif;font-weight:700;font-size:34px;letter-spacing:.02em;
  text-transform:uppercase;line-height:1;z-index:1;white-space:nowrap;}
.cC .bcast .meta{margin-left:auto;text-align:right;z-index:1;}
.cC .bcast .meta .p{font-family:"Rajdhani",sans-serif;font-weight:700;font-size:26px;line-height:1;white-space:nowrap;}
.cC .bcast .meta .l{font-size:12px;letter-spacing:.1em;text-transform:uppercase;opacity:.8;}
.cC .list{flex:1;padding:22px 34px;display:flex;flex-direction:column;gap:12px;overflow:hidden;}
.cC .card{background:#fff;border-left:5px solid var(--green);box-shadow:0 1px 0 rgba(0,0,0,.08);
  display:grid;grid-template-columns:128px 1fr 150px;align-items:center;}
.cC .when{padding:14px 18px;border-right:1px solid #e3e8e3;}
.cC .when .t{font-family:"Rajdhani",sans-serif;font-weight:700;font-size:26px;line-height:1;}
.cC .when .d{font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:#7c8a80;}
.cC .when .g{display:inline-block;margin-top:6px;font-family:"Rajdhani",sans-serif;font-weight:700;
  font-size:12px;letter-spacing:.06em;text-transform:uppercase;color:#fff;padding:1px 8px;border-radius:2px;}
.cC .mid{display:flex;align-items:center;justify-content:center;gap:18px;padding:12px;}
.cC .tm{display:flex;align-items:center;gap:12px;flex:1;}
.cC .tm.away{flex-direction:row-reverse;}
.cC .tm .nm{font-family:"Rajdhani",sans-serif;font-weight:700;font-size:24px;text-transform:uppercase;line-height:1;}
.cC .fl{width:40px;height:27px;object-fit:cover;box-shadow:0 0 0 1px rgba(0,0,0,.15);}
.cC .board{font-family:"Rajdhani",sans-serif;font-weight:700;background:var(--ink);color:var(--lime);
  font-size:26px;letter-spacing:.04em;padding:5px 14px;border-radius:3px;min-width:74px;text-align:center;white-space:nowrap;flex-shrink:0;}
.cC .board.empty{background:#eef2ee;color:#9aa89e;border:1px dashed #c2cdc4;}
.cC .act{padding:0 18px;text-align:right;}
.cC .act button{font-family:"Rajdhani",sans-serif;font-weight:700;font-size:15px;letter-spacing:.08em;
  text-transform:uppercase;padding:10px 20px;border-radius:3px;cursor:pointer;}
.cC .act .go{background:var(--lime);color:var(--ink);}
.cC .act .ed{background:#fff;color:var(--green);border:1.5px solid var(--green);}
`);

function ConceptC() {
  return (
    <div className="cC">
      <div className="bcast">
        <span className="live"><span className="dot" />Matchday 1</span>
        <h1>Fixtures &amp; Predictions</h1>
        <div className="meta"><div className="p">247 PTS</div><div className="l">Kiko · Rank 3</div></div>
      </div>
      <div className="list">
        {SC_FX.map((m, i) => (
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

// ═══════════════════════════════════════════════════════════════
// CONCEPT D — "ALBUM"  ·  vintage sticker-album, navy + gold + cream
// ═══════════════════════════════════════════════════════════════
injectOnce('cD-styles', `
.cD{--navy:#16243f;--navy-2:#22355a;--gold:#c79a3e;--gold-2:#e0bd66;--cream:#f3e9d2;--ink:#16243f;
  background:var(--cream);color:var(--ink);height:100%;width:100%;overflow:hidden;
  font-family:"Bricolage Grotesque",sans-serif;display:flex;flex-direction:column;
  background-image:radial-gradient(rgba(22,36,63,.05) 1px,transparent 1px);background-size:14px 14px;}
.cD *{box-sizing:border-box;margin:0;padding:0;}
.cD .head{background:var(--navy);color:var(--cream);padding:20px 34px;display:flex;align-items:center;gap:16px;
  border-bottom:4px solid var(--gold);}
.cD .crest{width:46px;height:46px;border-radius:50%;background:var(--gold);color:var(--navy);
  display:flex;align-items:center;justify-content:center;font-weight:800;font-size:22px;
  box-shadow:inset 0 0 0 3px var(--navy),0 0 0 2px var(--gold);}
.cD .head .tt .k{font-family:"DM Mono",monospace;font-size:11px;letter-spacing:.22em;text-transform:uppercase;color:var(--gold-2);}
.cD .head .tt h1{font-size:30px;font-weight:800;letter-spacing:-.01em;line-height:1;margin-top:2px;}
.cD .head .tag{margin-left:auto;text-align:right;font-family:"DM Mono",monospace;}
.cD .head .tag .v{font-size:24px;font-weight:500;color:var(--gold-2);}
.cD .head .tag .l{font-size:11px;letter-spacing:.14em;text-transform:uppercase;opacity:.7;}
.cD .book{flex:1;padding:24px 34px;display:grid;grid-template-columns:1fr 1fr;gap:16px;align-content:start;overflow:hidden;}
.cD .slot{background:#fbf5e6;border:2px solid var(--navy);border-radius:12px;padding:0;
  box-shadow:0 4px 0 rgba(22,36,63,.16);overflow:hidden;}
.cD .slot .hd{display:flex;justify-content:space-between;align-items:center;background:var(--navy);
  color:var(--cream);padding:7px 14px;}
.cD .slot .hd .g{font-family:"DM Mono",monospace;font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:var(--gold-2);white-space:nowrap;}
.cD .slot .hd .w{font-family:"DM Mono",monospace;font-size:11px;letter-spacing:.06em;white-space:nowrap;}
.cD .slot .bd{display:flex;align-items:center;gap:10px;padding:14px 16px;}
.cD .tm{flex:1;display:flex;flex-direction:column;align-items:center;gap:7px;}
.cD .fl{width:48px;height:32px;object-fit:cover;border-radius:3px;box-shadow:0 0 0 2px var(--gold);}
.cD .tm .nm{font-weight:700;font-size:14px;text-transform:uppercase;letter-spacing:.01em;}
.cD .mid{display:flex;flex-direction:column;align-items:center;gap:3px;min-width:78px;}
.cD .mid .sc{font-size:30px;font-weight:800;letter-spacing:-.02em;line-height:1;white-space:nowrap;}
.cD .mid .sc.empty{color:var(--gold);}
.cD .mid .lab{font-family:"DM Mono",monospace;font-size:9px;letter-spacing:.12em;text-transform:uppercase;color:var(--navy-2);}
.cD .slot .ft{padding:0 14px 14px;}
.cD .slot .ft button{width:100%;border-radius:20px;padding:9px;font-family:"DM Mono",monospace;
  font-size:12px;font-weight:500;letter-spacing:.1em;text-transform:uppercase;cursor:pointer;}
.cD .ft .stick{background:var(--gold);color:var(--navy);box-shadow:0 2px 0 #9c7424;}
.cD .ft .got{background:transparent;color:var(--navy);border:1.5px dashed var(--navy);}
`);

function ConceptD() {
  return (
    <div className="cD">
      <div className="head">
        <div className="crest">W</div>
        <div className="tt">
          <div className="k">World Cup Predictor · '26</div>
          <h1>Matchday One</h1>
        </div>
        <div className="tag"><div className="v">247 pts</div><div className="l">Kiko · 3rd place</div></div>
      </div>
      <div className="book">
        {SC_FX.slice(0, 4).map((m, i) => (
          <div className="slot" key={i}>
            <div className="hd"><span className="g">Group {m.grp}</span><span className="w">{m.day} · {m.time}</span></div>
            <div className="bd">
              <div className="tm">
                <img className="fl" src={flagUrl(m.h)} alt="" />
                <span className="nm">{NAME[m.h]}</span>
              </div>
              <div className="mid">
                <div className={`sc${m.pred ? '' : ' empty'}`}>{m.pred ? `${m.pred[0]}–${m.pred[1]}` : '?–?'}</div>
                <div className="lab">{m.pred ? 'Your pick' : 'No pick'}</div>
              </div>
              <div className="tm">
                <img className="fl" src={flagUrl(m.a)} alt="" />
                <span className="nm">{NAME[m.a]}</span>
              </div>
            </div>
            <div className="ft">
              {m.pred ? <button className="got">✓ Picked — edit</button> : <button className="stick">Make your pick</button>}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

Object.assign(window, { ConceptA, ConceptB, ConceptC, ConceptD });
