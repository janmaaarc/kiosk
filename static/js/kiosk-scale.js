(function () {
  var DESIGN_W = 1360;
  var DESIGN_H = 768;

  function ensureViewport() {
    var m = document.querySelector('meta[name="viewport"]');
    if (!m) {
      m = document.createElement("meta");
      m.name = "viewport";
      (document.head || document.documentElement).appendChild(m);
    }
    m.content = "width=" + DESIGN_W + ", initial-scale=1, user-scalable=no";
  }

  function setupStage() {
    document.documentElement.style.background = "#000";
    document.documentElement.style.overflow = "hidden";
    document.documentElement.style.margin = "0";
    document.body.style.width = DESIGN_W + "px";
    document.body.style.height = DESIGN_H + "px";
    document.body.style.margin = "0";
    document.body.style.transformOrigin = "top left";
    document.body.style.overflow = "hidden";
  }

  function applyScale() {
    var s = Math.min(
      window.innerWidth / DESIGN_W,
      window.innerHeight / DESIGN_H
    );
    var offsetX = (window.innerWidth - DESIGN_W * s) / 2 / s;
    var offsetY = (window.innerHeight - DESIGN_H * s) / 2 / s;
    document.body.style.transform =
      "scale(" + s + ") translate(" + offsetX + "px, " + offsetY + "px)";
  }

  function init() {
    ensureViewport();
    setupStage();
    applyScale();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
  window.addEventListener("resize", applyScale);
  window.addEventListener("orientationchange", applyScale);
})();
