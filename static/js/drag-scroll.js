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
    button img, a img, .top-icon, .top-icons img, .nav-icons img, img[onclick] {
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

      // Track drag on document so fast gestures don't lose the scroll target
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
        // Reset moved after click suppression fires (click follows mouseup)
        setTimeout(() => { moved = false; }, 0);
      }

      document.addEventListener('mousemove', onMove);
      document.addEventListener('mouseup', onUp);
    });

    // Suppress click after drag — only if this element was the one dragged
    el.addEventListener('click', (e) => {
      if (moved && e.currentTarget === el) {
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
