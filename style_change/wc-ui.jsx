// ─────────────────────────────────────────────────────────────
// wc-ui.jsx — shared mobile UI atoms for the prediction frames
// ─────────────────────────────────────────────────────────────

// iOS-style status bar strip
function PhoneStatusBar({ tint = '#fff' }) {
  return (
    <div style={{ height: 44, display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      padding: '0 22px 0 26px', flexShrink: 0, color: tint }}>
      <span style={{ fontSize: 14, fontWeight: 700, letterSpacing: .2 }}>9:41</span>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <svg width="17" height="11" viewBox="0 0 17 11" fill={tint}><rect x="0" y="6" width="3" height="5" rx="1"/><rect x="4.5" y="4" width="3" height="7" rx="1"/><rect x="9" y="2" width="3" height="9" rx="1"/><rect x="13.5" y="0" width="3" height="11" rx="1"/></svg>
        <svg width="16" height="11" viewBox="0 0 16 11" fill={tint}><path d="M8 2.6C10 2.6 11.8 3.4 13.1 4.7L14.4 3.3C12.7 1.6 10.5 .7 8 .7S3.3 1.6 1.6 3.3L2.9 4.7C4.2 3.4 6 2.6 8 2.6Z"/><path d="M8 6.1C8.9 6.1 9.7 6.5 10.3 7L11.6 5.7C10.6 4.8 9.4 4.2 8 4.2S5.4 4.8 4.4 5.7L5.7 7C6.3 6.5 7.1 6.1 8 6.1Z" opacity=".9"/><circle cx="8" cy="9.2" r="1.6"/></svg>
        <div style={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <div style={{ width: 22, height: 11, borderRadius: 3, border: `1px solid ${tint}`, opacity: .9, position: 'relative', padding: 1.5 }}>
            <div style={{ height: '100%', width: '72%', background: tint, borderRadius: 1 }} />
          </div>
          <div style={{ width: 1.5, height: 4, background: tint, borderRadius: 1, opacity: .5 }} />
        </div>
      </div>
    </div>
  );
}

// Home-indicator pill
function HomeBar({ tint = 'rgba(255,255,255,.5)' }) {
  return <div style={{ flexShrink: 0, display: 'flex', justifyContent: 'center', padding: '7px 0 9px' }}>
    <div style={{ width: 130, height: 5, borderRadius: 3, background: tint }} />
  </div>;
}

// Vertical score stepper — big tappable number with +/- on a column.
function VStepper({ value, onChange, accent = '#f5a623', size = 'md' }) {
  const dims = size === 'lg' ? { box: 84, font: 46, btn: 30 }
    : size === 'sm' ? { box: 52, font: 27, btn: 21 }
    : { box: 64, font: 34, btn: 26 };
  const Btn = ({ dir, children }) => (
    <button onClick={() => onChange(Math.max(0, Math.min(20, value + dir)))}
      style={{ width: dims.btn, height: dims.btn, borderRadius: 7, background: 'var(--bg-3)',
        border: '1px solid var(--border-2)', color: 'var(--t1)', fontSize: 16, fontWeight: 700,
        display: 'flex', alignItems: 'center', justifyContent: 'center', lineHeight: 1,
        transition: 'background .12s, transform .08s' }}
      onMouseDown={(e) => (e.currentTarget.style.transform = 'scale(.9)')}
      onMouseUp={(e) => (e.currentTarget.style.transform = 'scale(1)')}
      onMouseLeave={(e) => (e.currentTarget.style.transform = 'scale(1)')}>{children}</button>
  );
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: size === 'sm' ? 4 : 6 }}>
      <Btn dir={+1}>+</Btn>
      <div className="tnum" style={{ width: dims.box, height: dims.box, borderRadius: size === 'sm' ? 10 : 12,
        background: 'var(--bg-1)', border: `2px solid ${value > 0 ? accent : 'var(--border-2)'}`,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: dims.font, fontWeight: 900, color: '#fff', transition: 'border-color .15s' }}>{value}</div>
      <Btn dir={-1}>−</Btn>
    </div>
  );
}

// Conic progress ring with a label in the middle
function ProgressRing({ done, total, size = 46, accent = '#f5a623' }) {
  const pct = total ? done / total : 0;
  return (
    <div style={{ width: size, height: size, borderRadius: '50%', flexShrink: 0,
      background: `conic-gradient(${accent} ${pct * 360}deg, var(--bg-3) 0)`,
      display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div style={{ width: size - 8, height: size - 8, borderRadius: '50%', background: 'var(--bg-1)',
        display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', lineHeight: 1 }}>
        <span className="tnum" style={{ fontSize: 13, fontWeight: 900 }}>{done}<span style={{ color: 'var(--t2)', fontSize: 10 }}>/{total}</span></span>
      </div>
    </div>
  );
}

Object.assign(window, { PhoneStatusBar, HomeBar, VStepper, ProgressRing });
