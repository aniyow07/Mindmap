// AutoMap viewer: renders the JSON produced by `python -m automap build` as a
// collapsible left-to-right tree, with cross-links and a passage panel.
(function () {
  const API = window.AUTOMAP_API || ""; // same origin when served by server.py
  const COL = 250; // horizontal distance between depths
  const ROW = 38; // vertical distance between leaves
  const MAX_LABEL = 30;
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const dur = reduceMotion ? 0 : 320;

  const svg = d3.select("#map");
  const scene = svg.append("g");
  const gLinks = scene.append("g");
  const gCross = scene.append("g");
  const gNodes = scene.append("g");
  const zoom = d3.zoom().scaleExtent([0.2, 2.5]).on("zoom", (e) => scene.attr("transform", e.transform));
  svg.call(zoom).on("dblclick.zoom", null);

  const panel = document.getElementById("panel");
  const stats = document.getElementById("stats");
  const busy = document.getElementById("busy");
  const measure = document.createElement("canvas").getContext("2d");

  let data = null; // raw JSON
  let root = null; // d3.hierarchy
  let byId = new Map();
  let selected = null;

  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  const clip = (s, n = MAX_LABEL) => (s.length > n ? s.slice(0, n - 1).trimEnd() + "…" : s);

  function textWidth(s, kind) {
    measure.font = `${kind === "document" ? 600 : 500} ${kind === "document" ? 15 : 13}px "Chakra Petch", sans-serif`;
    return measure.measureText(s).width;
  }

  // ---------- loading ----------

  async function loadExamples() {
    const select = document.getElementById("examples");
    let list = [];
    try {
      list = await (await fetch("examples/index.json")).json();
    } catch {
      select.hidden = true;
    }
    for (const ex of list) {
      const o = document.createElement("option");
      o.value = ex.file;
      o.textContent = ex.name;
      o.dataset.source = ex.source || "";
      select.append(o);
    }
    select.addEventListener("change", () => openExample(select.selectedOptions[0]));
    if (list.length) openExample(select.selectedOptions[0]);
  }

  async function openExample(option) {
    const res = await fetch(`examples/${option.value}`);
    show(await res.json(), option.dataset.source);
  }

  async function checkApi() {
    const btn = document.getElementById("upload-btn");
    const input = document.getElementById("file");
    let live = false;
    try {
      live = (await fetch(`${API}/api/health`, { cache: "no-store" })).ok;
    } catch { /* static hosting */ }
    if (!live) {
      btn.setAttribute("aria-disabled", "true");
      btn.title = "Mapping your own PDF needs the Python server. See the README to run it locally.";
      btn.addEventListener("click", () => document.getElementById("about").showModal());
      return;
    }
    btn.addEventListener("click", () => input.click());
    input.addEventListener("change", async () => {
      const file = input.files[0];
      if (!file) return;
      busy.hidden = false;
      const form = new FormData();
      form.append("file", file);
      try {
        const res = await fetch(`${API}/api/map`, { method: "POST", body: form });
        const body = await res.json();
        if (!res.ok) throw new Error(body.detail || `Server returned ${res.status}`);
        show(body, `Your file: ${file.name}`);
      } catch (err) {
        panel.innerHTML = `<p class="error">Couldn't map ${esc(file.name)}: ${esc(err.message)}</p>`;
      } finally {
        busy.hidden = true;
        input.value = "";
      }
    });
  }

  // ---------- model ----------

  function show(json, sourceNote) {
    data = json;
    data.sourceNote = sourceNote || "";
    root = d3.hierarchy(data.root, (d) => d.children);
    byId = new Map();
    root.each((n) => {
      byId.set(n.data.id, n);
      n.label = clip(n.data.label, n.depth === 0 ? 60 : MAX_LABEL);
    });
    // Start compact on big maps: sections visible, topics folded.
    const big = root.descendants().length > 45;
    root.each((n) => {
      if (n.children && n.depth >= (big ? 1 : 3)) collapse(n);
    });
    const heading = document.getElementById("doc-title");
    heading.textContent = data.title;
    heading.title = data.title;
    const s = data.stats || {};
    stats.textContent = [
      s.pages && `${s.pages} pages`,
      s.headings_detected != null && `${s.headings_detected} headings detected`,
      s.topics != null && `${s.topics} topics clustered`,
      s.links != null && `${s.links} cross-links`,
      s.seconds != null && `built in ${s.seconds}s`,
    ].filter(Boolean).join(", ");
    selected = null;
    renderPanel(null);
    update(root, true);
    fit(false);
  }

  function collapse(n) {
    if (n.children) {
      n._children = n.children;
      n.children = null;
    }
  }
  function expand(n) {
    if (n._children) {
      n.children = n._children;
      n._children = null;
    }
  }
  function reveal(n) {
    for (let a = n.parent; a; a = a.parent) expand(a);
  }

  // ---------- drawing ----------

  function layout() {
    d3.tree().nodeSize([ROW, COL]).separation((a, b) => (a.parent === b.parent ? 1 : 1.25))(root);
  }

  function linkPath(s, t) {
    const sx = s.y + s.w, mid = (sx + t.y) / 2;
    return `M${sx},${s.x}C${mid},${s.x} ${mid},${t.x} ${t.y},${t.x}`;
  }

  function update(source, first = false) {
    layout();
    const nodes = root.descendants();
    nodes.forEach((n) => (n.w = textWidth(n.label, n.data.kind) + 26));
    const t = svg.transition().duration(first ? 0 : dur);

    const node = gNodes.selectAll("g.node").data(nodes, (d) => d.data.id);
    const enter = node.enter().append("g")
      .attr("class", (d) => `node ${d.data.kind}`)
      .attr("transform", () => `translate(${source.y0 ?? source.y},${source.x0 ?? source.x})`)
      .attr("tabindex", 0)
      .attr("role", "treeitem")
      .attr("opacity", 0)
      .on("click", (e, d) => select(d))
      .on("keydown", (e, d) => {
        if (e.key === "Enter") select(d);
        if (e.key === " ") { e.preventDefault(); toggle(d); }
      });
    enter.append("rect").attr("class", "pill").attr("rx", 13).attr("y", -13).attr("height", 26);
    enter.append("text").attr("x", 13);
    enter.append("circle").attr("class", "knob").attr("r", 5)
      .on("click", (e, d) => { e.stopPropagation(); toggle(d); });
    enter.append("title");

    const all = enter.merge(node);
    all.classed("selected", (d) => d === selected)
      .attr("aria-expanded", (d) => (d.children ? "true" : d._children ? "false" : null))
      .attr("aria-label", (d) => d.data.label);
    all.select("rect").attr("width", (d) => d.w);
    all.select("text").text((d) => d.label);
    all.select("title").text((d) => d.data.title || d.data.label);
    all.select("circle")
      .attr("cx", (d) => d.w)
      .attr("display", (d) => (d.children || d._children ? null : "none"))
      .classed("closed", (d) => !!d._children);
    all.transition(t).attr("opacity", 1).attr("transform", (d) => `translate(${d.y},${d.x})`);

    node.exit().transition(t).attr("opacity", 0)
      .attr("transform", () => `translate(${source.y},${source.x})`).remove();

    const link = gLinks.selectAll("path").data(root.links(), (d) => d.target.data.id);
    link.enter().append("path").attr("class", "link-tree")
      .attr("d", () => { const p = { x: source.x0 ?? source.x, y: source.y0 ?? source.y, w: 0 }; return linkPath(p, p); })
      .merge(link).transition(t).attr("d", (d) => linkPath(d.source, d.target));
    link.exit().transition(t).attr("d", () => { const p = { x: source.x, y: source.y, w: 0 }; return linkPath(p, p); }).remove();

    drawCross(t);
    nodes.forEach((n) => { n.x0 = n.x; n.y0 = n.y; });
  }

  function visible(id) {
    const n = byId.get(id);
    if (!n) return null;
    for (let a = n.parent; a; a = a.parent) if (!a.children) return null;
    return n;
  }

  function drawCross(t) {
    const pairs = (data.links || []).map((l) => ({ l, a: visible(l.source), b: visible(l.target) })).filter((p) => p.a && p.b);
    const path = gCross.selectAll("path").data(pairs, (p) => p.l.source + p.l.target);
    path.enter().append("path").attr("class", "link-cross").attr("opacity", 0)
      .merge(path)
      .classed("hot", (p) => selected && (p.a === selected || p.b === selected))
      .transition(t).attr("opacity", null)
      .attr("d", (p) => {
        // bow out to the right so links don't run through the tree
        const ax = p.a.y + p.a.w, bx = p.b.y + p.b.w;
        const bow = Math.max(ax, bx) + 60 + Math.abs(p.a.x - p.b.x) * 0.15;
        return `M${ax},${p.a.x}C${bow},${p.a.x} ${bow},${p.b.x} ${bx},${p.b.x}`;
      });
    path.exit().remove();
  }

  function toggle(d) {
    if (d.children) collapse(d); else expand(d);
    update(d);
  }

  function select(d) {
    selected = d;
    if (d._children) expand(d);
    update(d);
    renderPanel(d);
  }

  function fit(animate = true) {
    // Measure from the layout, not the DOM: nodes may still be mid-transition.
    const nodes = root.descendants().filter((n) => n.x != null);
    const x0 = d3.min(nodes, (n) => n.y), x1 = d3.max(nodes, (n) => n.y + n.w) + 80;
    const y0 = d3.min(nodes, (n) => n.x) - 20, y1 = d3.max(nodes, (n) => n.x) + 20;
    const box = { x: x0, y: y0, width: x1 - x0, height: y1 - y0 };
    const { width, height } = svg.node().getBoundingClientRect();
    if (!box.width || !width) return;
    const k = Math.min(1.2, 0.9 * Math.min(width / box.width, height / box.height));
    const tx = width / 2 - k * (box.x + box.width / 2);
    const ty = height / 2 - k * (box.y + box.height / 2);
    (animate ? svg.transition().duration(dur) : svg).call(zoom.transform, d3.zoomIdentity.translate(tx, ty).scale(k));
  }

  function centerOn(d) {
    const { width, height } = svg.node().getBoundingClientRect();
    const k = d3.zoomTransform(svg.node()).k;
    svg.transition().duration(dur).call(zoom.transform, d3.zoomIdentity.translate(width / 2 - k * (d.y + d.w / 2), height / 2 - k * d.x).scale(k));
  }

  // ---------- panel ----------

  function highlight(text, words) {
    let html = esc(text);
    for (const w of words) {
      if (w.length < 3) continue;
      const re = new RegExp(`\\b(${w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&").replace(/\s+/g, "\\s+")})\\b`, "gi");
      html = html.replace(re, "<mark>$1</mark>");
    }
    return html;
  }

  function subtreePassages(n) {
    const out = [];
    (function walk(x) {
      (x.passages || []).forEach((i) => out.push(i));
      (x.children || []).forEach(walk);
    })(n.data);
    return out;
  }

  function renderPanel(d) {
    if (!d) {
      panel.innerHTML = `<div class="panel-empty"><p>Select a node to see the passages it came from.</p>
        <p class="hint">Click a node to open it. Click its dot to fold or unfold its branch. Drag to pan, scroll to zoom.</p>
        ${data && data.sourceNote ? `<p class="source-note">${esc(data.sourceNote)}</p>` : ""}</div>`;
      return;
    }
    const n = d.data;
    const kindText = { document: "Document", section: "Section from the document", topic: "Topic found by clustering" }[n.kind] || n.kind;
    const own = n.passages || [];
    const ids = own.length ? own : subtreePassages(d).slice(0, 6);
    const words = (n.keywords || []).slice(0, 3);
    const passages = ids.map((i) => data.passages[i]).filter(Boolean);
    const related = (data.links || [])
      .filter((l) => l.source === n.id || l.target === n.id)
      .map((l) => ({ other: byId.get(l.source === n.id ? l.target : l.source), l }))
      .filter((r) => r.other);

    panel.className = `panel node-kind-${n.kind}`;
    panel.innerHTML = `
      <p class="kind ${n.kind}">${kindText}</p>
      <h2>${esc(n.label)}</h2>
      ${n.title ? `<p class="full-title">${esc(n.title)}</p>` : ""}
      ${n.summary ? `<p class="summary">${esc(n.summary)}</p>` : ""}
      ${words.length ? `<h3>Keyphrases</h3><ul class="chips">${words.map((w) => `<li>${esc(w)}</li>`).join("")}</ul>` : ""}
      ${related.length ? `<h3>Related elsewhere in the document</h3><ul class="related">${related.map((r) => `
        <li><button type="button" data-id="${esc(r.other.data.id)}">${esc(r.other.data.label)}
        <span class="why">${r.l.shared.length ? "Shares " + r.l.shared.map(esc).join(", ") : ""} (similarity ${r.l.score.toFixed(2)})</span></button></li>`).join("")}</ul>` : ""}
      ${passages.length ? `<h3>${own.length ? "Passages" : "Sample passages from this branch"}</h3>
        ${passages.map((p) => `<blockquote class="passage">${highlight(p.text, words)}<span class="page">Page ${p.page}</span></blockquote>`).join("")}` : ""}
      ${data.sourceNote ? `<p class="source-note">${esc(data.sourceNote)}</p>` : ""}`;
    panel.scrollTop = 0;
    panel.querySelectorAll(".related button").forEach((b) =>
      b.addEventListener("click", () => {
        const target = byId.get(b.dataset.id);
        reveal(target);
        select(target);
        centerOn(target);
      }),
    );
  }

  // ---------- controls ----------

  document.getElementById("fit").addEventListener("click", () => fit());
  document.getElementById("expand").addEventListener("click", () => { root.each(expand); update(root); fit(); });
  document.getElementById("collapse").addEventListener("click", () => {
    root.each((n) => { if (n.depth >= 1) collapse(n); });
    update(root);
    fit();
  });
  document.getElementById("about-btn").addEventListener("click", () => document.getElementById("about").showModal());
  window.addEventListener("resize", () => root && fit(false));

  loadExamples();
  checkApi();
})();
