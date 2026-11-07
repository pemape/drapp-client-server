// Concept heatmap viewer (MA, HE, SE, EX ...) drawn on top of the preprocessed fundus image.
document.addEventListener("DOMContentLoaded", function () {
  const stage = document.getElementById("concept-stage");
  if (!stage) return;

  const toggles = Array.from(document.querySelectorAll(".concept-toggle"));
  const allBox = document.getElementById("concept-all");
  const opacity = document.getElementById("concept-opacity");
  const tintBox = document.getElementById("concept-tint");

  // Heatmaps share one palette, so each concept gets its own colour to tell them apart when shown together.
  const COLORS = {
    ma: [0, 229, 255],
    he: [213, 0, 249],
    se: [0, 230, 118],
    ex: [41, 121, 255],
  };
  const FALLBACK = [[255, 87, 34], [255, 235, 59], [0, 150, 136], [121, 85, 72]];

  function colorFor(key) {
    if (COLORS[key]) return COLORS[key];
    const idx = toggles.findIndex((t) => t.dataset.key === key);
    return FALLBACK[Math.max(idx, 0) % FALLBACK.length];
  }

  document.querySelectorAll(".concept-swatch").forEach(function (el) {
    const c = colorFor(el.dataset.key);
    el.style.backgroundColor = "rgb(" + c.join(",") + ")";
  });

  const layers = {};

  function render(layer) {
    if (!layer.source) return;
    const ctx = layer.canvas.getContext("2d");
    const out = ctx.createImageData(layer.source.width, layer.source.height);
    out.data.set(layer.source.data);
    if (tintBox && tintBox.checked) {
      const c = colorFor(layer.key);
      for (let i = 0; i < out.data.length; i += 4) {
        out.data[i] = c[0];
        out.data[i + 1] = c[1];
        out.data[i + 2] = c[2];
      }
    }
    ctx.putImageData(out, 0, 0);
  }

  function ensureLayer(toggle) {
    const key = toggle.dataset.key;
    if (layers[key]) return layers[key];

    const canvas = document.createElement("canvas");
    canvas.className = "concept-layer";
    canvas.dataset.key = key;
    stage.appendChild(canvas);

    const layer = { key: key, canvas: canvas, source: null };
    layers[key] = layer;

    const img = new Image();
    img.onload = function () {
      canvas.width = img.naturalWidth;
      canvas.height = img.naturalHeight;
      const ctx = canvas.getContext("2d");
      ctx.drawImage(img, 0, 0);
      layer.source = ctx.getImageData(0, 0, canvas.width, canvas.height);
      render(layer);
    };
    img.src = toggle.dataset.src;
    return layer;
  }

  function sync(toggle) {
    const layer = ensureLayer(toggle);
    layer.canvas.style.display = toggle.checked ? "block" : "none";
  }

  function syncAllBox() {
    const enabled = toggles.filter((t) => !t.disabled);
    if (allBox) allBox.checked = enabled.length > 0 && enabled.every((t) => t.checked);
  }

  toggles.forEach(function (toggle) {
    toggle.addEventListener("change", function () {
      sync(toggle);
      syncAllBox();
    });
  });

  if (allBox) {
    allBox.addEventListener("change", function () {
      toggles.forEach(function (toggle) {
        if (toggle.disabled) return;
        toggle.checked = allBox.checked;
        sync(toggle);
      });
    });
  }

  if (opacity) {
    const applyOpacity = function () {
      stage.style.setProperty("--concept-opacity", String(opacity.value / 100));
    };
    opacity.addEventListener("input", applyOpacity);
    applyOpacity();
  }

  if (tintBox) {
    tintBox.addEventListener("change", function () {
      Object.values(layers).forEach(render);
    });
  }
});
