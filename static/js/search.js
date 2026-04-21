const input = document.getElementById("searchInput");
const suggestions = document.getElementById("suggestions");

input.addEventListener("input", async () => {
    const query = input.value;
    if (query.length < 1) {
        suggestions.innerHTML = "";
        return;
    }

    const response = await fetch(`/search_suggestions?q=${query}`);
    const data = await response.json();

    suggestions.innerHTML = "";

    data.forEach(item => {
        const div = document.createElement("div");
        div.textContent = item.name + " (" + item.type + ")";
        div.onclick = () => window.location.href = item.url;
        suggestions.appendChild(div);
    });
});
<script src="{{ url_for('static', filename='js/search.js') }}"></script> 