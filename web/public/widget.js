/*
 * Solange Glow booking widget. On the salon's website:
 *   <div data-solangeglow="salon-slug"></div>
 *   <script src="https://solangeglow.com/widget.js" async></script>
 * Optional: data-lang="fr" | "en" | "sk". The booking page only opens on the websites the
 * salon listed in her settings; its height follows the content.
 */
(function () {
  var script = document.currentScript;
  if (!script) return;
  var origin = new URL(script.src).origin;
  var languages = ["fr", "en", "sk"];

  function mount(element) {
    if (element.getAttribute("data-solangeglow-ready")) return;
    element.setAttribute("data-solangeglow-ready", "1");
    var slug = element.getAttribute("data-solangeglow") || "";
    var lang = (element.getAttribute("data-lang") || document.documentElement.lang || "fr")
      .slice(0, 2)
      .toLowerCase();
    if (languages.indexOf(lang) < 0) lang = "fr";
    var frame = document.createElement("iframe");
    frame.src = origin + "/" + lang + "/embed/" + encodeURIComponent(slug);
    frame.title = element.getAttribute("data-title") || "Solange Glow";
    frame.loading = "lazy";
    frame.style.width = "100%";
    frame.style.minHeight = "640px";
    frame.style.border = "0";
    element.appendChild(frame);
    window.addEventListener("message", function (event) {
      var data = event.data || {};
      if (event.origin !== origin || event.source !== frame.contentWindow) return;
      if (data.type === "solangeglow:height" && typeof data.height === "number") {
        frame.style.height = Math.max(400, Math.ceil(data.height)) + "px";
      }
    });
  }

  var elements = document.querySelectorAll("[data-solangeglow]");
  for (var i = 0; i < elements.length; i++) mount(elements[i]);
})();
