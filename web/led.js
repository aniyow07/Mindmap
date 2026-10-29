// Dot-matrix LED title, in the spirit of a certain robot helmet. Text is drawn
// to a tiny offscreen canvas, sampled, and re-drawn as round LEDs. Long titles
// scroll; with reduced motion they sit still and are cut to fit.
(function () {
  const canvas = document.getElementById("led");
  const ctx = canvas.getContext("2d");
  const ROWS = 9;
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  let bitmap = null; // { cols, on: Uint8Array }
  let offset = 0;
  let raf = null;

  function rasterise(text) {
    const off = document.createElement("canvas");
    const o = off.getContext("2d");
    o.font = `600 ${ROWS + 1}px "Chakra Petch", sans-serif`;
    const width = Math.ceil(o.measureText(text).width) + 2;
    off.width = width;
    off.height = ROWS;
    o.font = `600 ${ROWS + 1}px "Chakra Petch", sans-serif`;
    o.fillStyle = "#fff";
    o.textBaseline = "middle";
    o.fillText(text, 0, ROWS / 2 + 0.5);
    const data = o.getImageData(0, 0, width, ROWS).data;
    const on = new Uint8Array(width * ROWS);
    for (let i = 0; i < on.length; i++) on[i] = data[i * 4 + 3] > 110 ? 1 : 0;
    return { cols: width, on };
  }

  function draw() {
    const dpr = window.devicePixelRatio || 1;
    const w = canvas.clientWidth, h = canvas.clientHeight;
    if (canvas.width !== w * dpr) { canvas.width = w * dpr; canvas.height = h * dpr; }
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);
    const pitch = h / ROWS;
    const r = pitch * 0.36;
    const visible = Math.floor(w / pitch);
    const style = getComputedStyle(document.documentElement);
    const lit = style.getPropertyValue("--gold").trim();
    const unlit = style.getPropertyValue("--visor-2").trim();
    const gap = 12;
    const span = bitmap ? bitmap.cols + gap : 0;
    for (let c = 0; c < visible; c++) {
      const src = bitmap ? Math.floor(c + offset) % span : -1;
      for (let row = 0; row < ROWS; row++) {
        const isOn = bitmap && src < bitmap.cols && bitmap.on[row * bitmap.cols + src];
        ctx.fillStyle = isOn ? lit : unlit;
        ctx.beginPath();
        ctx.arc(c * pitch + pitch / 2, row * pitch + pitch / 2, r, 0, Math.PI * 2);
        ctx.fill();
      }
    }
    return { visible, cols: bitmap ? bitmap.cols : 0 };
  }

  function loop() {
    offset += 0.12;
    draw();
    raf = requestAnimationFrame(loop);
  }

  let lastText = "";

  window.setLedText = function (text) {
    lastText = text;
    if (raf) cancelAnimationFrame(raf);
    offset = 0;
    bitmap = rasterise(text);
    const { visible, cols } = draw();
    if (cols > visible && !reduceMotion) raf = requestAnimationFrame(loop);
  };

  window.addEventListener("resize", () => draw());
  // the first rasterise may have used a fallback font
  document.fonts && document.fonts.ready.then(() => lastText && window.setLedText(lastText));
})();
