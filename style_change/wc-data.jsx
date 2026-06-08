// ─────────────────────────────────────────────────────────────
// wc-data.jsx — shared tokens, fonts, team data, flag helper
// Lifted straight from the repo: dark-neutral theme, gold accent,
// Inter, flagcdn flags, real MD1 fixtures + scoring model.
// ─────────────────────────────────────────────────────────────

// One-time style injection (Inter + the WC token set, scoped under .wc)
if (typeof document !== 'undefined' && !document.getElementById('wc-styles')) {
  const link = document.createElement('link');
  link.rel = 'stylesheet';
  link.href = 'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap';
  document.head.appendChild(link);

  const s = document.createElement('style');
  s.id = 'wc-styles';
  s.textContent = `
  .wc {
    --bg-0:#0a0a0a; --bg-1:#111; --bg-2:#1a1a1a; --bg-3:#222; --bg-4:#2a2a2a;
    --border:#2a2a2a; --border-2:#383838;
    --gold:#f5a623; --gold-2:#fbbf24; --red:#ef4444; --green:#22c55e; --blue:#4a9eff;
    --t0:#fff; --t1:#ccc; --t2:#888; --t3:#444;
    font-family:"Inter",-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
    color:var(--t0); -webkit-font-smoothing:antialiased; height:100%;
  }
  .wc *{box-sizing:border-box;margin:0;padding:0;}
  .wc .flag{object-fit:cover;border-radius:2px;flex-shrink:0;display:block;
    box-shadow:0 0 0 1px rgba(255,255,255,.08);}
  .wc .upper{text-transform:uppercase;}
  .wc .tnum{font-variant-numeric:tabular-nums;}
  .wc button{font-family:inherit;cursor:pointer;border:none;background:none;color:inherit;}
  @keyframes wcPulse{0%,100%{opacity:1}50%{opacity:.4}}
  @keyframes wcPop{0%{transform:scale(.6);opacity:0}60%{transform:scale(1.15)}100%{transform:scale(1);opacity:1}}
  @keyframes wcRise{from{transform:translateY(8px);opacity:0}to{transform:translateY(0);opacity:1}}
  .wc .gb{display:inline-flex;align-items:center;justify-content:center;padding:2px 7px;
    border-radius:4px;font-size:10px;font-weight:800;letter-spacing:.04em;text-transform:uppercase;white-space:nowrap;}
  `;
  document.head.appendChild(s);
}

// 3-letter squad code → flagcdn ISO-2 (lowercase). England/Scotland use GB subdivisions.
const FLAG = {
  MEX:'mx', RSA:'za', KOR:'kr', CZE:'cz', CAN:'ca', BIH:'ba', QAT:'qa', SUI:'ch',
  BRA:'br', MAR:'ma', HAI:'ht', SCO:'gb-sct', USA:'us', PAR:'py', AUS:'au', TUR:'tr',
  GER:'de', CUW:'cw', CIV:'ci', ECU:'ec', NED:'nl', JPN:'jp', SWE:'se', TUN:'tn',
  BEL:'be', EGY:'eg', IRN:'ir', NZL:'nz', ESP:'es', CPV:'cv', KSA:'sa', URU:'uy',
  FRA:'fr', SEN:'sn', IRQ:'iq', NOR:'no', ARG:'ar', ALG:'dz', AUT:'at', JOR:'jo',
  POR:'pt', COD:'cd', UZB:'uz', COL:'co', ENG:'gb-eng', CRO:'hr', GHA:'gh', PAN:'pa',
};
const flagUrl = (code, w = 160) => `https://flagcdn.com/w${w}/${FLAG[code] || 'un'}.png`;

// Group badge palette (from style.css gb-A … gb-L)
const GROUP_COLORS = {
  A:'#16a34a', B:'#7c3aed', C:'#ea580c', D:'#0891b2', E:'#db2777', F:'#ca8a04',
  G:'#dc2626', H:'#059669', I:'#6366f1', J:'#c2410c', K:'#0f766e', L:'#9333ea',
};

// Team display names
const NAME = {
  MEX:'Mexico', RSA:'South Africa', KOR:'South Korea', CZE:'Czechia',
  CAN:'Canada', BIH:'Bosnia & Herz.', QAT:'Qatar', SUI:'Switzerland',
  BRA:'Brazil', MAR:'Morocco', HAI:'Haiti', SCO:'Scotland',
  USA:'United States', PAR:'Paraguay', GER:'Germany', CUW:'Curaçao',
  NED:'Netherlands', JPN:'Japan', ARG:'Argentina', ALG:'Algeria',
  POR:'Portugal', COD:'DR Congo', ENG:'England', CRO:'Croatia',
  ESP:'Spain', CPV:'Cape Verde', FRA:'France', SEN:'Senegal',
};
const SHORT = {
  MEX:'MEX', RSA:'RSA', KOR:'KOR', CZE:'CZE', CAN:'CAN', BIH:'BIH', QAT:'QAT', SUI:'SUI',
  BRA:'BRA', MAR:'MAR', USA:'USA', PAR:'PAR', BEL:'BEL', EGY:'EGY',
};

// Real Matchday-1 fixtures used in the slate (subset of seed_data.py)
const MD1 = [
  { num:1, h:'MEX', a:'RSA', grp:'A', time:'19:00', venue:'Estadio Azteca, Mexico City' },
  { num:3, h:'CAN', a:'BIH', grp:'B', time:'19:00', venue:'BMO Field, Toronto' },
  { num:6, h:'BRA', a:'MAR', grp:'C', time:'22:00', venue:'MetLife Stadium, New Jersey' },
  { num:4, h:'USA', a:'PAR', grp:'D', time:'01:00', venue:'SoFi Stadium, Inglewood' },
];

// Scoring model (league defaults)
const SCORING = { exact: 5, result: 2 };

// User-selectable app accent palette
const WC_ACCENTS = [
  { id: 'amber',   name: 'Amber',    hex: '#f5a623' },
  { id: 'pitch',   name: 'Pitch',    hex: '#2bd66a' },
  { id: 'volt',    name: 'Volt',     hex: '#c8ff32' },
  { id: 'azure',   name: 'Electric', hex: '#3d8bff' },
  { id: 'magenta', name: 'Hot Pink', hex: '#ff3d77' },
];

Object.assign(window, { FLAG, flagUrl, GROUP_COLORS, NAME, SHORT, MD1, SCORING, WC_ACCENTS });
