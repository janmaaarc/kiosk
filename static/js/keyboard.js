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

  // Floating toggle tab shown when keyboard is hidden but an input is active
  const toggleTab = document.createElement('button');
  toggleTab.id = 'vkbd-toggle';
  toggleTab.textContent = '⌨';
  toggleTab.style.cssText = `
    display:none;position:fixed;bottom:16px;right:16px;
    background:#7b2d2d;color:#fff;border:none;border-radius:50%;
    width:56px;height:56px;font-size:24px;cursor:pointer;
    z-index:99998;box-shadow:0 4px 16px rgba(0,0,0,0.35);
    align-items:center;justify-content:center;
    user-select:none;-webkit-user-select:none;
  `;

  function showToggleTab() { toggleTab.style.display = 'flex'; }
  function hideToggleTab() { toggleTab.style.display = 'none'; }

  function show(input) {
    target = input;
    kbd.style.display = 'block';
    hideToggleTab();
  }

  function hide() {
    kbd.style.display = 'none';
    target = null;
    if (document.activeElement && document.activeElement.tagName === 'INPUT') {
      showToggleTab();
    }
  }

  let _toggleTarget = null;
  toggleTab.addEventListener('mousedown', function(e) {
    e.preventDefault();
    _toggleTarget = document.activeElement;
  });
  toggleTab.addEventListener('click', function() {
    hideToggleTab();
    if (_toggleTarget && _toggleTarget.tagName === 'INPUT') {
      show(_toggleTarget);
      _toggleTarget = null;
    }
  });

  // RFID scan interceptor: strip scanner keystrokes from focused text inputs.
  // RFID scanners fire digits at < 50ms/char. Humans type at > 150ms/char.
  let _rfidBuf = '';
  let _rfidSeed = '';
  let _rfidPrevKey = '';
  let _rfidPrevTime = 0;
  let _rfidRapid = false;

  document.addEventListener('keydown', function(e) {
    const el = document.activeElement;
    const isText = el && el.tagName === 'INPUT' &&
      ['text','search','password','email','number',''].includes(el.type || '');
    const now = Date.now();
    const gap = now - _rfidPrevTime;

    if (e.key === 'Enter') {
      const full = _rfidSeed + _rfidBuf;
      if (_rfidRapid && full.length > 4 && isText) {
        e.preventDefault();
        el.value = el.value.slice(0, Math.max(0, el.value.length - full.length));
        el.dispatchEvent(new Event('input', { bubbles: true }));
      }
      _rfidBuf = ''; _rfidSeed = ''; _rfidRapid = false;
      _rfidPrevKey = ''; _rfidPrevTime = 0;
      return;
    }

    if (e.key.length === 1) {
      if (gap < 60 && _rfidPrevKey) {
        if (!_rfidRapid) { _rfidSeed = _rfidPrevKey; _rfidBuf = ''; _rfidRapid = true; }
        _rfidBuf += e.key;
      } else {
        _rfidBuf = ''; _rfidSeed = ''; _rfidRapid = false;
      }
      _rfidPrevKey = e.key;
      _rfidPrevTime = now;
    } else {
      _rfidBuf = ''; _rfidSeed = ''; _rfidRapid = false;
      _rfidPrevKey = ''; _rfidPrevTime = 0;
    }
  }, false);

  document.addEventListener('DOMContentLoaded', () => {
    document.body.appendChild(kbd);
    document.body.appendChild(toggleTab);
    applySize();

    document.addEventListener('focusin', e => {
      const el = e.target;
      if (el.tagName === 'INPUT' && ['text','search','password','email','number',''].includes(el.type)) {
        show(el);
      }
    });

    // Re-show keyboard when clicking an already-focused input (focusin won't re-fire).
    document.addEventListener('click', e => {
      const el = e.target;
      if (el.tagName === 'INPUT' && ['text','search','password','email','number',''].includes(el.type || '')) {
        show(el);
      }
    });

    document.addEventListener('mousedown', e => {
      const isInput = e.target.tagName === 'INPUT' &&
        ['text','search','password','email','number',''].includes(e.target.type || '');
      const isToggle = e.target === toggleTab;
      if (!kbd.contains(e.target) && !isInput && !isToggle) {
        hide();
        hideToggleTab();
      }
    });
  });
})();
