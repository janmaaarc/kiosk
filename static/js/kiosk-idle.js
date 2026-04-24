(function () {
  var MENU_TIMEOUT_MS = 60 * 1000;
  var SCREENSAVER_TIMEOUT_MS = 120 * 1000;
  var SLIDE_INTERVAL_MS = 4000;
  var SCREENSAVER_IMAGES = [
    '/static/images/screensaver/slide1.png',
    '/static/images/screensaver/slide2.png',
    '/static/images/screensaver/slide3.png',
    '/static/images/screensaver/slide4.png',
  ];

  var menuTimer = null;
  var screensaverTimer = null;
  var screensaverEl = null;
  var slideInterval = null;
  var slideIdx = 0;

  function buildScreensaver() {
    var el = document.createElement('div');
    el.id = 'kiosk-screensaver';
    el.style.cssText =
      'position:fixed;top:0;left:0;width:100%;height:100%;' +
      'z-index:9999;background:#000;display:none;cursor:pointer;';

    var img = document.createElement('img');
    img.id = 'kiosk-ss-img';
    img.alt = '';
    img.style.cssText = 'width:100%;height:100%;object-fit:cover;display:block;';
    el.appendChild(img);

    var hint = document.createElement('div');
    hint.textContent = 'Tap anywhere to continue';
    hint.style.cssText =
      'position:absolute;bottom:40px;left:0;right:0;text-align:center;' +
      'color:#fff;font-size:28px;font-family:League Spartan,sans-serif;' +
      'font-weight:700;text-shadow:0 2px 12px rgba(0,0,0,0.9);pointer-events:none;';
    el.appendChild(hint);

    el.addEventListener('click', dismissScreensaver, true);
    el.addEventListener('touchstart', dismissScreensaver, { capture: true, passive: true });

    document.documentElement.appendChild(el);
    return el;
  }

  function advanceSlide() {
    var img = document.getElementById('kiosk-ss-img');
    if (img) {
      img.src = SCREENSAVER_IMAGES[slideIdx % SCREENSAVER_IMAGES.length];
      slideIdx += 1;
    }
  }

  function showScreensaver() {
    if (!screensaverEl) screensaverEl = buildScreensaver();
    slideIdx = 0;
    advanceSlide();
    screensaverEl.style.display = 'block';
    slideInterval = setInterval(advanceSlide, SLIDE_INTERVAL_MS);
  }

  function dismissScreensaver() {
    if (screensaverEl) screensaverEl.style.display = 'none';
    clearInterval(slideInterval);
    resetTimers();
  }

  var warningTimer = null;
  var warningEl = null;
  var countdownInterval = null;

  function isAdminPage() {
    var p = window.location.pathname;
    return p.startsWith('/admin') || p.startsWith('/dashboard');
  }

  function buildWarning() {
    var el = document.createElement('div');
    el.id = 'kiosk-idle-warning';
    el.style.cssText =
      'position:fixed;top:0;left:0;width:100%;height:100%;z-index:99998;' +
      'background:rgba(0,0,0,0.75);display:none;align-items:center;justify-content:center;';
    var box = document.createElement('div');
    box.style.cssText =
      'background:#fff;border-radius:16px;padding:40px 48px;text-align:center;' +
      'font-family:League Spartan,sans-serif;max-width:420px;';
    var title = document.createElement('div');
    title.style.cssText = 'font-size:22px;font-weight:900;color:#7b2d2d;margin-bottom:12px;';
    title.textContent = 'Still there?';
    var msg = document.createElement('div');
    msg.style.cssText = 'font-size:16px;color:#555;margin-bottom:24px;';
    msg.textContent = 'Returning to menu in ';
    var counter = document.createElement('strong');
    counter.id = 'kiosk-countdown';
    counter.style.color = '#7b2d2d';
    counter.textContent = '10';
    msg.appendChild(counter);
    msg.appendChild(document.createTextNode(' seconds…'));
    var btn = document.createElement('button');
    btn.textContent = 'STAY ON PAGE';
    btn.style.cssText =
      'background:#7b2d2d;color:#fff;border:none;border-radius:10px;' +
      'padding:14px 32px;font-family:inherit;font-size:16px;font-weight:900;cursor:pointer;';
    btn.onclick = dismissWarning;
    box.appendChild(title);
    box.appendChild(msg);
    box.appendChild(btn);
    el.appendChild(box);
    document.body.appendChild(el);
    return el;
  }

  function showWarning() {
    if (!warningEl) warningEl = buildWarning();
    var n = 10;
    var counter = document.getElementById('kiosk-countdown');
    if (counter) counter.textContent = n;
    warningEl.style.display = 'flex';
    countdownInterval = setInterval(function () {
      n -= 1;
      if (counter) counter.textContent = n;
      if (n <= 0) {
        clearInterval(countdownInterval);
        window.location.href = '/menu';
      }
    }, 1000);
  }

  function dismissWarning() {
    if (warningEl) warningEl.style.display = 'none';
    clearInterval(countdownInterval);
    resetTimers();
  }

  function resetTimers() {
    clearTimeout(menuTimer);
    clearTimeout(screensaverTimer);
    clearTimeout(warningTimer);
    clearInterval(countdownInterval);
    if (warningEl) warningEl.style.display = 'none';

    if (window.location.pathname !== '/menu') {
      if (isAdminPage()) {
        // Show warning instead of hard redirect on admin pages
        warningTimer = setTimeout(showWarning, MENU_TIMEOUT_MS);
      } else {
        menuTimer = setTimeout(function () {
          window.location.href = '/menu';
        }, MENU_TIMEOUT_MS);
      }
    }

    screensaverTimer = setTimeout(showScreensaver, SCREENSAVER_TIMEOUT_MS);
  }

  var ACTIVITY_EVENTS = ['touchstart', 'mousedown', 'keydown', 'scroll'];
  for (var i = 0; i < ACTIVITY_EVENTS.length; i++) {
    document.addEventListener(ACTIVITY_EVENTS[i], resetTimers, { passive: true });
  }

  function injectRippleCSS() {
    if (document.getElementById('kiosk-ripple-css')) return;
    var s = document.createElement('style');
    s.id = 'kiosk-ripple-css';
    s.textContent =
      '@keyframes kiosk-ripple{to{transform:scale(4);opacity:0}}' +
      '.kiosk-ripple-wave{position:absolute;border-radius:50%;pointer-events:none;' +
      'background:rgba(255,255,255,0.4);transform:scale(0);' +
      'animation:kiosk-ripple 480ms linear forwards;}';
    document.head.appendChild(s);
  }

  function spawnRipple(e) {
    var target = e.currentTarget;
    var d = Math.max(target.clientWidth, target.clientHeight);
    var r = d / 2;
    var rect = target.getBoundingClientRect();
    var clientX = e.touches ? e.touches[0].clientX : e.clientX;
    var clientY = e.touches ? e.touches[0].clientY : e.clientY;
    var cx = clientX - rect.left - r;
    var cy = clientY - rect.top - r;

    var wave = document.createElement('span');
    wave.className = 'kiosk-ripple-wave';
    wave.style.cssText =
      'width:' + d + 'px;height:' + d + 'px;left:' + cx + 'px;top:' + cy + 'px;';

    var old = target.querySelector('.kiosk-ripple-wave');
    if (old) old.remove();

    if (getComputedStyle(target).position === 'static') {
      target.style.position = 'relative';
    }
    target.style.overflow = 'hidden';
    target.appendChild(wave);
    setTimeout(function () { wave.remove(); }, 500);
  }

  function attachRipples() {
    var els = document.querySelectorAll('a, button, .menu-card, [role="button"]');
    for (var j = 0; j < els.length; j++) {
      els[j].addEventListener('touchstart', spawnRipple, { passive: true });
      els[j].addEventListener('mousedown', spawnRipple);
    }
  }

  function init() {
    injectRippleCSS();
    attachRipples();
    resetTimers();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
