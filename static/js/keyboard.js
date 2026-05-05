(function () {
  if (document.getElementById('vkbd')) return;

  const ROWS = [
    ['1','2','3','4','5','6','7','8','9','0','⌫'],
    ['Q','W','E','R','T','Y','U','I','O','P'],
    ['A','S','D','F','G','H','J','K','L'],
    ['⇧','Z','X','C','V','B','N','M','✕'],
    ['SPACE','DONE'],
  ];

  let target = null;
  let capsOn = false;

  const kbd = document.createElement('div');
  kbd.id = 'vkbd';
  kbd.style.cssText = `
    display:none;
    position:fixed;
    bottom:0;left:0;right:0;
    background:#1a1a1a;
    z-index:99999;
    box-shadow:0 -4px 24px rgba(0,0,0,0.5);
    user-select:none;
    -webkit-user-select:none;
  `;

  ROWS.forEach(row => {
    const rowDiv = document.createElement('div');
    rowDiv.dataset.kbdRow = '1';
    rowDiv.style.cssText = 'display:flex;justify-content:center;';
    row.forEach(key => {
      const btn = document.createElement('button');
      btn.textContent = key === 'SPACE' ? '' : key;
      btn.dataset.key = key;
      btn.style.cssText = `
        background:${key === 'DONE' ? '#7b2d2d' : key === '✕' ? '#444' : '#333'};
        color:#fff;border:none;border-radius:8px;
        font-weight:700;cursor:pointer;
        font-family:'League Spartan',sans-serif;
        transition:background 0.1s;
        flex-shrink:0;
        padding:0;margin:0;box-sizing:border-box;
        min-height:0;min-width:0;
      `;
      if (key === 'SPACE') btn.style.background = '#555';
      btn.addEventListener('mousedown', e => { e.preventDefault(); handleKey(key); });
      rowDiv.appendChild(btn);
    });
    kbd.appendChild(rowDiv);
  });

  function applySize() {
    const VH = window.screen.height / 100;
    const VW = window.screen.width  / 100;
    const btnH = Math.round(VH * 9)   + 'px';
    const fs   = Math.round(VH * 2.5) + 'px';
    const pad  = `${Math.round(VH*1.5)}px ${Math.round(VW*2)}px`;
    const gap  = Math.round(VW * 0.4) + 'px';
    const mb   = Math.round(VH * 0.8) + 'px';

    kbd.style.padding = pad;

    kbd.querySelectorAll('[data-kbd-row]').forEach(row => {
      row.style.gap = gap;
      row.style.marginBottom = mb;
    });

    kbd.querySelectorAll('button').forEach(btn => {
      const key = btn.dataset.key;
      let w;
      if (key === 'SPACE') w = Math.round(VW * 22)  + 'px';
      else if (key === 'DONE') w = Math.round(VW * 10) + 'px';
      else if (key === '⌫' || key === '⇧' || key === '✕') w = Math.round(VW * 6.5) + 'px';
      else w = Math.round(VW * 4.5) + 'px';
      btn.style.width    = w;
      btn.style.height   = btnH;
      btn.style.fontSize = key === 'SPACE' ? '0' : fs;
    });
  }

  function handleKey(key) {
    if (!target) return;
    if (key === 'DONE' || key === '✕') { hide(); return; }
    if (key === '⌫') {
      const s = target.selectionStart, e = target.selectionEnd;
      if (s !== e) { insertAtCursor(''); }
      else if (s > 0) {
        target.value = target.value.slice(0, s - 1) + target.value.slice(s);
        target.selectionStart = target.selectionEnd = s - 1;
      }
      target.dispatchEvent(new Event('input', { bubbles: true }));
      return;
    }
    if (key === '⇧') { capsOn = !capsOn; updateCaps(); return; }
    insertAtCursor(key === 'SPACE' ? ' ' : (capsOn ? key.toUpperCase() : key.toLowerCase()));
    target.dispatchEvent(new Event('input', { bubbles: true }));
  }

  function insertAtCursor(char) {
    const s = target.selectionStart, e = target.selectionEnd;
    target.value = target.value.slice(0, s) + char + target.value.slice(e);
    target.selectionStart = target.selectionEnd = s + char.length;
  }

  function updateCaps() {
    kbd.querySelectorAll('button').forEach(btn => {
      const k = btn.dataset.key;
      if (k && k.length === 1 && k >= 'A' && k <= 'Z') {
        btn.textContent = capsOn ? k.toUpperCase() : k.toLowerCase();
        btn.style.background = capsOn ? '#555' : '#333';
      }
    });
    const shift = [...kbd.querySelectorAll('button')].find(b => b.dataset.key === '⇧');
    if (shift) shift.style.background = capsOn ? '#7b2d2d' : '#333';
  }

  function show(input) { target = input; kbd.style.display = 'block'; }
  function hide() { kbd.style.display = 'none'; target = null; }

  document.addEventListener('DOMContentLoaded', () => {
    document.body.appendChild(kbd);
    // Apply sizes here — DOM is fully parsed, viewport is settled
    applySize();

    document.addEventListener('focusin', e => {
      const el = e.target;
      if (el.tagName === 'INPUT' && ['text','search','password','email','number',''].includes(el.type)) {
        show(el);
      }
    });

    document.addEventListener('mousedown', e => {
      if (!kbd.contains(e.target) && e.target !== target) hide();
    });
  });
})();
