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
    });

    el.addEventListener('mouseleave', () => {
      isDown = false;
      el.style.cursor = '';
    });

    el.addEventListener('mouseup', () => {
      isDown = false;
      el.style.cursor = '';
    });

    el.addEventListener('mousemove', (e) => {
      if (!isDown) return;
      e.preventDefault();
      const rect = el.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      const walkX = x - startX;
      const walkY = y - startY;
      if (Math.abs(walkX) > 3 || Math.abs(walkY) > 3) moved = true;
      el.scrollLeft = scrollLeft - walkX;
      el.scrollTop = scrollTop - walkY;
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

  function init() {
    // Apply to all currently scrollable elements
    document.querySelectorAll('*').forEach(el => {
      if (isScrollable(el)) attachDragScroll(el);
    });

    // Also watch for dynamically added scrollable elements
    new MutationObserver(() => {
      document.querySelectorAll('*').forEach(el => {
        if (!el._dragScrollAttached && isScrollable(el)) {
          el._dragScrollAttached = true;
          attachDragScroll(el);
        }
      });
    }).observe(document.body, { childList: true, subtree: true });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
