// Tiny dependency-free site script: client-side search over the generated
// index, the Random link, and arrow keys between cases.
(function () {
  var indexUrl = "/search-index.json";
  var index = null;

  function load() {
    if (index) return Promise.resolve(index);
    return fetch(indexUrl)
      .then(function (r) { return r.json(); })
      .then(function (data) { index = data; return index; });
  }

  // Random: any case but the one you're on.
  document.addEventListener("click", function (ev) {
    var a = ev.target.closest && ev.target.closest("[data-random]");
    if (!a || ev.metaKey || ev.ctrlKey || ev.shiftKey) return;
    ev.preventDefault();
    load().then(function (all) {
      var pick;
      do { pick = all[Math.floor(Math.random() * all.length)]; }
      while (all.length > 1 && pick.u === location.pathname);
      location.href = pick.u;
    });
  });

  // ← / → step through a collection when the page links rel=prev/next.
  document.addEventListener("keydown", function (ev) {
    if (ev.altKey || ev.ctrlKey || ev.metaKey || ev.shiftKey) return;
    var t = ev.target;
    if (t && (t.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName))) return;
    var rel = ev.key === "ArrowLeft" ? "prev" : ev.key === "ArrowRight" ? "next" : "";
    var link = rel && document.querySelector('link[rel="' + rel + '"]');
    if (link) location.href = link.href;
  });

  var box = document.getElementById("search");
  var out = document.getElementById("search-results");
  if (!box || !out) return;
  indexUrl = box.getAttribute("data-index") || indexUrl;

  function esc(s) {
    return s.replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }

  // The text is typeset with curly quotes; match what people type.
  function norm(s) {
    return s.replace(/[‘’]/g, "'").replace(/[“”]/g, '"').toLowerCase();
  }

  function snippet(body, q) {
    var i = norm(body).indexOf(q);
    if (i < 0) return "";
    var start = Math.max(0, i - 40);
    return (start > 0 ? "…" : "") + esc(body.slice(start, i)) +
      "<em>" + esc(body.slice(i, i + q.length)) + "</em>" +
      esc(body.slice(i + q.length, i + q.length + 60)) + "…";
  }

  function render(q) {
    q = norm(q.trim());
    out.innerHTML = "";
    if (!q) return;
    var hits = 0;
    index.forEach(function (e) {
      var hay = norm(e.te + " " + e.tz + " " + e.b);
      if (hay.indexOf(q) < 0) return;
      hits++;
      if (hits > 40) return;
      var li = document.createElement("li");
      li.innerHTML =
        '<a href="' + e.u + '">' + esc(e.c) + " " + (e.n ? e.n + ". " : "") +
        esc(e.te) + ' <span class="zh" lang="zh-Hant">' + esc(e.tz) + "</span></a>" +
        '<span class="ctx">' + snippet(e.b, q) + "</span>";
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
