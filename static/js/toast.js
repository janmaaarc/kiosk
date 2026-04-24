(function () {
  const container = document.createElement('div');
  container.style.cssText = [
    'position:fixed','top:24px','right:24px','z-index:999999',
    'display:flex','flex-direction:column','gap:10px','pointer-events:none',
  ].join(';');
  function attachContainer() {
    if(document.body) { document.body.appendChild(container); }
    else { document.addEventListener('DOMContentLoaded', () => document.body.appendChild(container)); }
  }
  attachContainer();

  window.toast = function (message, type, duration) {
    type     = type     || 'info';
    duration = duration || 2800;

    const colors = {
      success: { bg: '#1a7a3c', icon: '✓' },
      error:   { bg: '#c0392b', icon: '✕' },
      info:    { bg: '#2c6fad', icon: 'ℹ' },
      warn:    { bg: '#b7770d', icon: '⚠' },
    };
    const cfg = colors[type] || colors.info;

    const el = document.createElement('div');
    el.style.cssText = [
      'background:' + cfg.bg, 'color:#fff',
      'padding:14px 20px', 'border-radius:10px',
      "font-family:'League Spartan',sans-serif",
      'font-size:15px', 'font-weight:700', 'letter-spacing:.5px',
      'box-shadow:0 4px 16px rgba(0,0,0,0.25)',
      'display:flex', 'align-items:center', 'gap:10px',
      'pointer-events:auto',
      'opacity:0', 'transform:translateX(40px)',
      'transition:opacity 0.25s ease,transform 0.25s ease',
      'max-width:320px', 'line-height:1.4',
    ].join(';');

    const iconEl = document.createElement('span');
    iconEl.textContent = cfg.icon;
    iconEl.style.fontSize = '18px';

    const textEl = document.createElement('span');
    textEl.textContent = message;

    el.appendChild(iconEl);
    el.appendChild(textEl);
    container.appendChild(el);

    requestAnimationFrame(() => requestAnimationFrame(() => {
      el.style.opacity = '1';
      el.style.transform = 'translateX(0)';
    }));

    setTimeout(() => {
      el.style.opacity = '0';
      el.style.transform = 'translateX(40px)';
      setTimeout(() => el.remove(), 280);
    }, duration);
  };
})();
