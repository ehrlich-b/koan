// Tiny dependency-free client-side search over the generated index.
(function () {
  var box = document.getElementById("search");
  var out = document.getElementById("search-results");
  if (!box || !out) return;

  var index = [];
  var loaded = false;
  var indexUrl = box.getAttribute("data-index") || "/search-index.json";

  function load() {
    if (loaded) return Promise.resolve();
    return fetch(indexUrl)
      .then(function (r) { return r.json(); })
      .then(function (data) { index = data; loaded = true; });
  }

  function esc(s) {
    return s.replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }

  function snippet(body, q) {
    var i = body.toLowerCase().indexOf(q);
    if (i < 0) return "";
    var start = Math.max(0, i - 40);
    var frag = (start > 0 ? "…" : "") + body.slice(start, i + q.length + 60) + "…";
    return esc(frag).replace(
      new RegExp(q.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "i"),
      function (m) { return "<em>" + m + "</em>"; }
    );
  }

  function render(q) {
    q = q.trim().toLowerCase();
    out.innerHTML = "";
    if (!q) return;
    var hits = 0;
    index.forEach(function (e) {
      var hay = (e.te + " " + e.tz + " " + e.b).toLowerCase();
      if (hay.indexOf(q) < 0) return;
      hits++;
      if (hits > 40) return;
      var li = document.createElement("li");
      li.innerHTML =
        '<a href="' + e.u + '">' + esc(e.c) + " " + (e.n ? e.n + ". " : "") +
        esc(e.te) + ' <span class="zh">' + esc(e.tz) + "</span></a>" +
        '<span class="ctx">' + (snippet(e.b, q) || "") + "</span>";
      out.appendChild(li);
    });
    if (!hits) {
      var li = document.createElement("li");
      li.textContent = "No matches.";
      out.appendChild(li);
    }
  }

  box.addEventListener("input", function () {
    var q = box.value;
    load().then(function () { render(q); });
  });
  box.addEventListener("focus", load);
})();
