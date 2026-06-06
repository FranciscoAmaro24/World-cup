// Convert UTC times to local time
document.querySelectorAll('[data-utc]').forEach(el => {
  const utc = el.getAttribute('data-utc');
  if (!utc) return;
  try {
    const d = new Date(utc + 'Z');
    el.textContent = d.toLocaleString(undefined, {
      weekday: 'short', month: 'short', day: 'numeric',
      hour: '2-digit', minute: '2-digit'
    });
  } catch (e) {}
});

// Countdown timers
document.querySelectorAll('[data-countdown]').forEach(el => {
  const utc = el.getAttribute('data-countdown');
  if (!utc) return;
  const target = new Date(utc + 'Z');
  function update() {
    const diff = target - Date.now();
    if (diff <= 0) { el.textContent = 'LIVE'; el.style.color = '#ef4444'; return; }
    const d = Math.floor(diff / 86400000);
    const h = Math.floor((diff % 86400000) / 3600000);
    const m = Math.floor((diff % 3600000) / 60000);
    if (d > 0) el.textContent = `${d}d ${h}h`;
    else if (h > 0) el.textContent = `${h}h ${m}m`;
    else el.textContent = `${m}m`;
  }
  update();
  setInterval(update, 60000);
});

// Copy invite code
document.querySelectorAll('[data-copy]').forEach(btn => {
  btn.addEventListener('click', () => {
    const text = btn.getAttribute('data-copy');
    navigator.clipboard.writeText(text).then(() => {
      const orig = btn.textContent;
      btn.textContent = 'Copied!';
      setTimeout(() => btn.textContent = orig, 2000);
    });
  });
});

// Score input: only allow 0-20
document.querySelectorAll('.score-input').forEach(input => {
  input.addEventListener('input', () => {
    let v = parseInt(input.value);
    if (isNaN(v) || v < 0) input.value = 0;
    if (v > 20) input.value = 20;
  });
});

// Tab switching
document.querySelectorAll('.tab').forEach(tab => {
  tab.addEventListener('click', () => {
    const group = tab.closest('.tabs');
    const target = tab.getAttribute('data-tab');
    group.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
    document.querySelectorAll('[data-tab-content]').forEach(pane => {
      pane.style.display = pane.getAttribute('data-tab-content') === target ? '' : 'none';
    });
  });
});
