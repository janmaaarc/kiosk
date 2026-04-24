(function () {
  // Disable text selection and image dragging globally
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
    button img, a img, .top-icon, .nav-icons img, .card img {
      pointer-events: auto;
    }
  `;
  document.head.appendChild(style);

  function isScrollable(el) {
    const style = window.getComputedStyle(el);
    const overflowY = style.overflowY;
    const overflowX = style.overflowX;
    const canScrollY = (overflowY === 'auto' || overflowY === 'scroll') && el.scrollHeight > el.clientHeight;
    const canScrollX = (overflowX === 'auto' || overflowX === 'scroll') && el.scrollWidth > el.clientWidth;
    return canScrollY || canScrollX;
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
      }

      document.addEventListener('mousemove', onMove);
      document.addEventListener('mouseup', onUp);
    });

    // Suppress click after drag
    el.addEventListener('click', (e) => {
      if (moved) {
        e.stopPropagation();
        e.preventDefault();
        moved = false;
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

    new MutationObserver(() => {
      document.querySelectorAll('*').forEach(attachIfNeeded);
    }).observe(document.body, { childList: true, subtree: true });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
