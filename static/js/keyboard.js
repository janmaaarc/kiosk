(function () {
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
    padding:10px 8px 16px;
    z-index:99999;
    box-shadow:0 -4px 24px rgba(0,0,0,0.5);
    user-select:none;
    -webkit-user-select:none;
  `;

  ROWS.forEach(row => {
    const rowDiv = document.createElement('div');
    rowDiv.style.cssText = 'display:flex;justify-content:center;gap:6px;margin-bottom:6px;';

    row.forEach(key => {
      const btn = document.createElement('button');
      btn.textContent = key === 'SPACE' ? '' : key;
      btn.dataset.key = key;

      let w = '42px';
      if (key === 'SPACE') w = '260px';
      if (key === 'DONE')  w = '100px';
      if (key === '⌫')    w = '60px';
      if (key === '⇧')    w = '60px';
      if (key === '✕')    w = '60px';

      btn.style.cssText = `
        width:${w};height:48px;
        background:${key === 'DONE' ? '#7b2d2d' : key === '✕' ? '#444' : '#333'};
        color:#fff;border:none;border-radius:8px;
        font-size:${key === 'SPACE' ? '0' : '16px'};
        font-weight:700;cursor:pointer;
        font-family:'League Spartan',sans-serif;
        transition:background 0.1s;
        flex-shrink:0;
      `;
      if (key === 'SPACE') {
        btn.style.background = '#555';
      }

      btn.addEventListener('mousedown', e => {
        e.preventDefault();
        handleKey(key);
      });

      rowDiv.appendChild(btn);
    });

    kbd.appendChild(rowDiv);
  });

  function handleKey(key) {
    if (!target) return;
    if (key === 'DONE' || key === '✕') {
      hide();
      return;
    }
    if (key === '⌫') {
      const s = target.selectionStart;
      const e = target.selectionEnd;
      if (s !== e) {
        insertAtCursor('');
      } else if (s > 0) {
        target.value = target.value.slice(0, s - 1) + target.value.slice(s);
        target.selectionStart = target.selectionEnd = s - 1;
      }
      target.dispatchEvent(new Event('input', { bubbles: true }));
      return;
    }
    if (key === '⇧') {
      capsOn = !capsOn;
      updateCaps();
      return;
    }
    if (key === 'SPACE') {
      insertAtCursor(' ');
    } else {
      insertAtCursor(capsOn ? key.toUpperCase() : key.toLowerCase());
    }
    target.dispatchEvent(new Event('input', { bubbles: true }));
  }

  function insertAtCursor(char) {
    const s = target.selectionStart;
    const e = target.selectionEnd;
    target.value = target.value.slice(0, s) + char + target.value.slice(e);
    target.selectionStart = target.selectionEnd = s + char.length;
  }

  function updateCaps() {
    kbd.querySelectorAll('button').forEach(btn => {
      const k = btn.dataset.key;
      if (k && k.length === 1 && k >= 'A' && k <= 'Z') {
        btn.textContent = capsOn ? k.toUpperCase() : k.toLowerCase();
        btn.style.background = (capsOn && k >= 'A' && k <= 'Z') ? '#555' : '#333';
      }
    });
    const shiftBtn = [...kbd.querySelectorAll('button')].find(b => b.dataset.key === '⇧');
    if (shiftBtn) shiftBtn.style.background = capsOn ? '#7b2d2d' : '#333';
  }

  function show(input) {
    target = input;
    kbd.style.display = 'block';
  }

  function hide() {
    kbd.style.display = 'none';
    target = null;
  }

  document.addEventListener('DOMContentLoaded', () => {
    document.body.appendChild(kbd);

    document.addEventListener('focusin', e => {
      const el = e.target;
      if (el.tagName === 'INPUT' && ['text','search','password','email','number',''].includes(el.type)) {
        show(el);
      }
    });

    document.addEventListener('mousedown', e => {
      if (!kbd.contains(e.target) && e.target !== target) {
        hide();
      }
    });
  });
})();
