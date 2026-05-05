(function () {
  const style = document.createElement('style');
  style.textContent = `
    * {
      user-select: none;
      -webkit-user-select: none;
    }
    input, textarea {
      user-select: text;
      -webkit-user-select: text;
    }
    html {
      scroll-behavior: smooth;
    }
    img {
      -webkit-user-drag: none;
      pointer-events: none;
    }
    button img, a img, .top-icon, .top-icons img, .nav-icons img, img[onclick], .img-thumb {
      pointer-events: auto;
    }
  `;
  document.head.appendChild(style);

  function isScrollable(el) {
    // Only check CSS overflow — NOT scrollHeight vs clientHeight.
    // Content height check at init time fails when images haven't loaded yet,
    // causing drag-scroll to never attach on image-heavy pages.
    const s = window.getComputedStyle(el);
    return s.overflowY === 'auto' || s.overflowY === 'scroll' ||
           s.overflowX === 'auto' || s.overflowX === 'scroll';
  }

  function attachDragScroll(el) {
    let isDown = false;
    let startX, startY, scrollLeft, scrollTop;
    let moved = false;

    // Mouse drag
    el.addEventListener('mousedown', (e) => {
      if (e.button !== 0) return;
      isDown = true;
      moved = false;
      const rect = el.getBoundingClientRect();
      startX = e.clientX - rect.left;
      startY = e.clientY - rect.top;
      scrollLeft = el.scrollLeft;
      scrollTop = el.scrollTop;
      el.style.cursor = 'grabbing';

      function onMove(e) {
        if (!isDown) return;
        e.preventDefault();
        const rect = el.getBoundingClientRect();
        const walkX = (e.clientX - rect.left) - startX;
        const walkY = (e.clientY - rect.top) - startY;
        if (Math.abs(walkX) > 3 || Math.abs(walkY) > 3) moved = true;
        el.scrollLeft = scrollLeft - walkX;
        el.scrollTop = scrollTop - walkY;
      }

      function onUp() {
        isDown = false;
        el.style.cursor = '';
        document.removeEventListener('mousemove', onMove);
        document.removeEventListener('mouseup', onUp);
        setTimeout(() => { moved = false; }, 0);
      }

      document.addEventListener('mousemove', onMove);
      document.addEventListener('mouseup', onUp);
    });

    // Touch drag (kiosk/TV touchscreen)
    let touchStartX, touchStartY, touchScrollLeft, touchScrollTop, touchMoved = false;
    el.addEventListener('touchstart', (e) => {
      const t = e.touches[0];
      touchStartX = t.clientX;
      touchStartY = t.clientY;
      touchScrollLeft = el.scrollLeft;
      touchScrollTop = el.scrollTop;
      touchMoved = false;
    }, { passive: true });

    el.addEventListener('touchmove', (e) => {
      const t = e.touches[0];
      const walkX = t.clientX - touchStartX;
      const walkY = t.clientY - touchStartY;
      if (Math.abs(walkX) > 3 || Math.abs(walkY) > 3) touchMoved = true;
      el.scrollLeft = touchScrollLeft - walkX;
      el.scrollTop = touchScrollTop - walkY;
    }, { passive: true });

    // Suppress click after drag
    el.addEventListener('click', (e) => {
      if ((moved || touchMoved) && e.currentTarget === el) {
        e.stopPropagation();
        e.preventDefault();
      }
    }, true);
  }

  function attachIfNeeded(el) {
    if (!el._dragScrollAttached && isScrollable(el)) {
      el._dragScrollAttached = true;
      attachDragScroll(el);
    }
  }

  function init() {
    document.querySelectorAll('*').forEach(attachIfNeeded);

    new MutationObserver((mutations) => {
      mutations.forEach(m => {
        m.addedNodes.forEach(node => {
          if (node.nodeType !== 1) return;
          attachIfNeeded(node);
          node.querySelectorAll('*').forEach(attachIfNeeded);
        });
      });
    }).observe(document.body, { childList: true, subtree: true });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // Re-scan after all images/resources load — catches containers that
  // weren't scrollable yet at DOMContentLoaded
  window.addEventListener('load', () => {
    document.querySelectorAll('*').forEach(attachIfNeeded);
  });
})();
