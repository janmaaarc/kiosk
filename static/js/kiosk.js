(function () {
  function clearSuggestions(el) {
    while (el.firstChild) el.removeChild(el.firstChild);
  }

  window.addEventListener('DOMContentLoaded', function () {
    var input = document.getElementById('searchInput');
    var suggestions = document.getElementById('suggestions');
    if (!input || !suggestions) return;

    var debounceTimer = null;

    input.addEventListener('input', function () {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(async function () {
        var q = input.value.trim();
        if (!q) { clearSuggestions(suggestions); return; }
        try {
          var res = await fetch('/api/rooms?q=' + encodeURIComponent(q));
          var data = await res.json();
          clearSuggestions(suggestions);
          data.forEach(function (item) {
            var div = document.createElement('div');
            div.textContent = item;
            div.onclick = function () {
              window.location.href = '/search?query=' + encodeURIComponent(item);
            };
            suggestions.appendChild(div);
          });
        } catch (_) {
          clearSuggestions(suggestions);
        }
      }, 200);
    });
  });
})();
