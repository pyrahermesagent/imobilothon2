/* Codebase artifact viewer — logic */
"use strict";

const DOCS = [
  { id: "spec",     label: "Specification",    file: "Specification.md",   icon: "book-open" },
  { id: "activity", label: "Activity Diagram", file: "ActivityDiagram.md", icon: "workflow" },
  { id: "usecase",  label: "Use-Case Model",   file: "UseCaseModel.md",    icon: "users" },
  { id: "class",    label: "Class Model",      file: "ClassModel.md",      icon: "boxes" },
  { id: "domain",   label: "Domain Model",     file: "DomainModel.md",     icon: "shapes" },
  { id: "database", label: "Database Model",   file: "DatabaseModel.md",   icon: "database" },
];

const state = {
  repos: [],
  repo: null,
  doc: "spec",
  fits: [],
};

const els = {
  repoView: document.getElementById("repo-view"),
  repoList: document.getElementById("repo-list"),
  docView: document.getElementById("doc-view"),
  back: document.getElementById("back"),
  repoName: document.getElementById("repo-name"),
  docList: document.getElementById("doc-list"),
  view: document.getElementById("view"),
  docContent: document.getElementById("doc-content"),
};

/* ---------- helpers ---------- */
function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}
function refreshIcons() { if (window.lucide) lucide.createIcons(); }

/* ---------- markdown + mermaid config ---------- */
function setupRenderers() {
  marked.setOptions({ gfm: true, breaks: false });

  const themeVariables = {
    fontFamily: "inherit",
    fontSize: "14px",
    primaryColor: "#ffffff",
    primaryTextColor: "#0b0b0b",
    primaryBorderColor: "#0b0b0b",
    lineColor: "#0b0b0b",
    secondaryColor: "#ffffff",
    tertiaryColor: "#ffffff",
    mainBkg: "#ffffff",
    nodeBkg: "#ffffff",
    nodeBorder: "#0b0b0b",
    nodeTextColor: "#0b0b0b",
    textColor: "#0b0b0b",
    titleColor: "#0b0b0b",
    clusterBkg: "#f5f5f5",
    clusterBorder: "#0b0b0b",
    edgeLabelBackground: "#ffffff",
    edgeLabelColor: "#0b0b0b",
    labelBg: "#ffffff",
    labelColor: "#0b0b0b",
    relationshipLabelColor: "#0b0b0b",
    relationshipLineColor: "#0b0b0b",
    entityBkg: "#ffffff",
    entityAttrBkg: "#ffffff",
    attributeBackgroundColor: "#ffffff",
    attributeIconColor: "#0b0b0b",
    classAttribute: "",
  };

  // Belt-and-suspenders: force black-on-white for every diagram type.
  const themeCSS = [
    "text { fill: #0b0b0b; }",
    ".node rect, .node polygon, .node circle, .node ellipse, .node path { fill:#fff !important; stroke:#0b0b0b !important; }",
    ".nodeLabel, .nodeLabel * { fill:#0b0b0b !important; color:#0b0b0b !important; }",
    ".cluster rect, .cluster polygon { fill:#f5f5f5 !important; stroke:#0b0b0b !important; }",
    ".cluster-label text, .cluster-label * { fill:#0b0b0b !important; }",
    ".edgePath .path, path.edgePath, .flowchart-link, .dependency, .relation { stroke:#0b0b0b !important; }",
    ".marker .path, .marker path { fill:#0b0b0b !important; stroke:#0b0b0b !important; }",
    ".edgeLabel rect { fill:#fff !important; stroke:#0b0b0b !important; }",
    ".edgeLabel text, .edgeLabel tspan, .edgeLabel span { fill:#0b0b0b !important; }",
    ".class-node rect, .class-node polygon, .classEntity rect, .classEntity polygon { fill:#fff !important; stroke:#0b0b0b !important; }",
    ".class-node text, .classEntity text { fill:#0b0b0b !important; }",
    ".er .entityBox, .er .entityType, .er .attributeBox { fill:#fff !important; stroke:#0b0b0b !important; }",
    ".er .entityBox > *, .er .entityType > * { fill:#fff !important; }",
    ".er .relationshipLine path { stroke:#0b0b0b !important; fill:none !important; }",
    ".er .relationshipLabel, .er .relationshipLabel > * { fill:#0b0b0b !important; }",
  ].join("\n");

  mermaid.initialize({
    startOnLoad: false,
    securityLevel: "loose",
    theme: "base",
    fontFamily: "inherit",
    flowchart: { useMaxWidth: false, htmlLabels: true, curve: "basis", padding: 14 },
    themeVariables,
    themeCSS,
  });
}

/* ---------- repo list ---------- */
async function loadRepos() {
  let repos = [];
  try {
    const r = await fetch("/api/repos");
    if (r.ok) repos = await r.json();
  } catch (e) {
    /* offline / no server */
  }
  state.repos = repos;
  renderRepoList();
}

function renderRepoList() {
  els.repoList.innerHTML = "";
  if (!state.repos.length) {
    const d = document.createElement("div");
    d.className = "repo-empty";
    d.innerHTML =
      "No modeled repositories found yet.<br>Run the codebase-modeler skill to " +
      "generate artifacts under <code>output/&lt;repo&gt;/</code>, then reload.";
    els.repoList.appendChild(d);
    return;
  }
  state.repos.forEach((name) => {
    const b = document.createElement("button");
    b.className = "repo-item";
    b.innerHTML =
      '<span data-lucide="git-branch"></span><span>' + escapeHtml(name) + "</span>";
    b.addEventListener("click", () => openRepo(name));
    els.repoList.appendChild(b);
  });
  refreshIcons();
}

/* ---------- navigation ---------- */
function openRepo(name) {
  state.repo = name;
  els.repoName.textContent = name;
  els.repoView.style.display = "none";
  els.docView.style.display = "block";
  selectDoc("spec");
}

function backToRepos() {
  state.repo = null;
  state.fits = [];
  els.docView.style.display = "none";
  els.repoView.style.display = "grid";
}

function buildDocList() {
  els.docList.innerHTML = "";
  DOCS.forEach((d) => {
    const b = document.createElement("button");
    b.className = "doc-item";
    b.dataset.id = d.id;
    b.innerHTML = '<span data-lucide="' + d.icon + '"></span><span>' + d.label + "</span>";
    b.addEventListener("click", () => selectDoc(d.id));
    els.docList.appendChild(b);
  });
  refreshIcons();
}

function selectDoc(id) {
  state.doc = id;
  Array.from(els.docList.children).forEach((b) => {
    b.classList.toggle("active", b.dataset.id === id);
  });
  renderDoc();
}

/* ---------- document rendering ---------- */
async function renderDoc() {
  const meta = DOCS.find((d) => d.id === state.doc);
  state.fits = [];
  els.docContent.innerHTML = '<div class="status">Loading…</div>';
  els.view.scrollTop = 0;
  try {
    const url = "/api/content?repo=" + encodeURIComponent(state.repo) +
      "&doc=" + encodeURIComponent(meta.file);
    const resp = await fetch(url);
    if (!resp.ok) {
      let msg = "HTTP " + resp.status;
      try { const j = await resp.json(); if (j.error) msg = j.error; } catch (e) {}
      throw new Error(msg);
    }
    const text = await resp.text();
    els.docContent.innerHTML = marked.parse(text);

    const preBlocks = Array.from(els.docContent.querySelectorAll("pre")).filter((pre) => {
      const c = pre.querySelector("code");
      return c && /\blanguage-mermaid\b/.test(c.className || "");
    });
    for (let i = 0; i < preBlocks.length; i++) {
      await makeDiagram(preBlocks[i], i + 1);
    }
    refreshIcons();
  } catch (err) {
    els.docContent.innerHTML = "";
    const div = document.createElement("div");
    div.className = "doc-error";
    div.textContent = "Could not load " + meta.file +
      "\n" + (err && err.message ? err.message : String(err));
    els.docContent.appendChild(div);
  }
}

/* ---------- mermaid -> interactive diagram ---------- */
async function makeDiagram(pre, index) {
  const codeEl = pre.querySelector("code");
  const code = (codeEl ? codeEl.textContent : "").trim();

  const stage = document.createElement("div");
  stage.className = "diagram";
  stage.innerHTML =
    '<div class="d-toolbar">' +
      '<div class="d-title">Diagram ' + index + "</div>" +
      '<div class="d-controls">' +
        '<button data-act="out" title="Zoom out"><span data-lucide="zoom-out"></span></button>' +
        '<button data-act="in" title="Zoom in"><span data-lucide="zoom-in"></span></button>' +
        '<button data-act="fit" title="Fit to screen"><span data-lucide="maximize"></span></button>' +
      "</div>" +
    "</div>" +
    '<div class="d-stage"><div class="d-inner"></div>' +
      '<div class="d-hint">scroll to zoom · drag to pan · double-click to fit</div>' +
    "</div>";
  const inner = stage.querySelector(".d-inner");
  pre.replaceWith(stage);

  try {
    const id = "mmd-" + Date.now() + "-" + index;
    const res = await mermaid.render(id, code);
    inner.innerHTML = res.svg;
    if (typeof res.bindFunctions === "function") res.bindFunctions(inner);
    const svg = inner.querySelector("svg");
    if (!svg) throw new Error("no SVG produced");
    const dims = svgDims(svg);
    svg.style.maxWidth = "none";
    svg.setAttribute("width", dims.w);
    svg.setAttribute("height", dims.h);
    attachPanZoom(stage, inner, dims);
  } catch (err) {
    inner.innerHTML =
      '<div class="doc-error" style="position:absolute;top:12px;left:12px;right:12px">' +
      "mermaid error\n" + (err && err.message ? err.message : String(err)) +
      "\n\n--- source ---\n" + escapeHtml(code) + "</div>";
  }
  refreshIcons();
  return stage;
}

function svgDims(svg) {
  let w = null, h = null;
  if (svg.viewBox && svg.viewBox.baseVal && svg.viewBox.baseVal.width) {
    w = svg.viewBox.baseVal.width;
    h = svg.viewBox.baseVal.height;
  }
  if (!w || !h) {
    const rw = parseFloat(svg.getAttribute("width"));
    const rh = parseFloat(svg.getAttribute("height"));
    if (rw && rw > 0) w = w || rw;
    if (rh && rh > 0) h = h || rh;
  }
  if (!w || !h) {
    try { const b = svg.getBBox(); if (b.width) w = b.width; if (b.height) h = b.height; }
    catch (e) {}
  }
  return { w: w || 800, h: h || 400 };
}

/* ---------- pan / zoom ---------- */
function attachPanZoom(stage, inner, dims) {
  const el = stage.querySelector(".d-stage");
  const MIN = 0.1, MAX = 8;
  const st = { scale: 1, tx: 0, ty: 0 };

  function apply() {
    inner.style.transform =
      "translate(" + st.tx + "px, " + st.ty + "px) scale(" + st.scale + ")";
  }
  function fit() {
    const r = el.getBoundingClientRect();
    if (!r.width || !r.height) return;
    const s = Math.min(r.width / dims.w, r.height / dims.h);
    st.scale = s;
    st.tx = (r.width - dims.w * s) / 2;
    st.ty = (r.height - dims.h * s) / 2;
    apply();
  }
  function zoomBy(factor, cx, cy) {
    const ns = Math.max(MIN, Math.min(MAX, st.scale * factor));
    const k = ns / st.scale;
    st.tx = cx - (cx - st.tx) * k;
    st.ty = cy - (cy - st.ty) * k;
    st.scale = ns;
    apply();
  }

  el.addEventListener("wheel", (e) => {
    e.preventDefault();
    const r = el.getBoundingClientRect();
    zoomBy(e.deltaY < 0 ? 1.12 : 1 / 1.12, e.clientX - r.left, e.clientY - r.top);
  }, { passive: false });

  let dragging = false, sx = 0, sy = 0, stx = 0, sty = 0;
  el.addEventListener("mousedown", (e) => {
    dragging = true;
    sx = e.clientX; sy = e.clientY; stx = st.tx; sty = st.ty;
    el.classList.add("grabbing");
  });
  window.addEventListener("mousemove", (e) => {
    if (!dragging) return;
    st.tx = stx + (e.clientX - sx);
    st.ty = sty + (e.clientY - sy);
    apply();
  });
  window.addEventListener("mouseup", () => {
    if (!dragging) return;
    dragging = false;
    el.classList.remove("grabbing");
  });

  el.addEventListener("dblclick", fit);

  stage.querySelectorAll(".d-controls button").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const r = el.getBoundingClientRect();
      const act = btn.dataset.act;
      if (act === "in") zoomBy(1.25, r.width / 2, r.height / 2);
      else if (act === "out") zoomBy(1 / 1.25, r.width / 2, r.height / 2);
      else fit();
    });
  });

  // touch pan
  let t = null;
  el.addEventListener("touchstart", (e) => {
    if (e.touches.length === 1)
      t = { x: e.touches[0].clientX, y: e.touches[0].clientY, tx: st.tx, ty: st.ty };
  }, { passive: true });
  el.addEventListener("touchmove", (e) => {
    if (e.touches.length === 1 && t) {
      e.preventDefault();
      st.tx = t.tx + (e.touches[0].clientX - t.x);
      st.ty = t.ty + (e.touches[0].clientY - t.y);
      apply();
    }
  }, { passive: false });
  el.addEventListener("touchend", () => { t = null; });

  state.fits.push(fit);
  requestAnimationFrame(fit);
}

/* ---------- boot ---------- */
function init() {
  setupRenderers();
  buildDocList();
  els.back.addEventListener("click", backToRepos);
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && state.repo) backToRepos();
  });
  let rt = null;
  window.addEventListener("resize", () => {
    clearTimeout(rt);
    rt = setTimeout(() => state.fits.forEach((f) => f()), 120);
  });
  refreshIcons(); // static back chevron
  loadRepos();
}

document.addEventListener("DOMContentLoaded", init);
