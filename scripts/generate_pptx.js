/**
 * NEXUS Platform — PowerPoint Generator
 * Run: node scripts/generate_pptx.js
 * Output: C:/Users/bolaf/Desktop/NEXUS_Platform_Presentation.pptx
 */
const pptxgen = require("pptxgenjs");

// ── Color Palette ──────────────────────────────────────────────────────────
const C = {
  darkBg:  "0D0D1F", darkerBg: "060612",
  indigo:  "4F46E5", purple:   "7C3AED",
  white:   "FFFFFF", slate:    "94A3B8",
  slateD:  "1E293B", emerald:  "10B981",
  amber:   "F59E0B", red:      "EF4444",
  lightBg: "F8FAFC", cardBg:   "F1F5F9",
  gray:    "E2E8F0", grayBd:   "CBD5E1",
  textDark:"0F172A", textMid:  "475569",
  // AWS
  awsOrg:  "FF9900", awsRed:   "CC2321",
  awsBlu:  "146EB4", awsGrn:   "1D8A00",
  // GCP
  gcpBlu:  "4285F4", gcpRed:   "EA4335",
  gcpYlw:  "FBBC05", gcpGrn:   "34A853",
  gcpDrk:  "1A73E8",
  // Azure
  azrBlu:  "0078D4", azrGrn:   "107C10",
  azrPrp:  "5C2D91",
};

// ── Helpers ────────────────────────────────────────────────────────────────
const makeShadow = () => ({ type: "outer", color: "000000", blur: 8, offset: 3, angle: 135, opacity: 0.12 });

let pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";  // 13.3" × 7.5"
pres.author = "Lanre Bolaji";
pres.title  = "NEXUS — Multi-Agent Engineering Intelligence Platform";

function hdrBar(s, title, sub, bg = C.darkBg) {
  s.addShape(pres.shapes.RECTANGLE, { x:0, y:0, w:13.3, h:0.85, fill:{color:bg}, line:{color:bg} });
  s.addText(title, { x:0.4, y:0.09, w:10, h:0.45, fontSize:20, bold:true, color:C.white, fontFace:"Calibri", margin:0 });
  if (sub) s.addText(sub, { x:0.4, y:0.54, w:12.5, h:0.26, fontSize:9, color:C.slate, fontFace:"Calibri", margin:0 });
  s.addShape(pres.shapes.RECTANGLE, { x:0, y:0.83, w:13.3, h:0.04, fill:{color:C.indigo}, line:{color:C.indigo} });
}

function svc(s, label, x, y, w, h, fill, txtColor, sz) {
  txtColor = txtColor || C.white; sz = sz || 8;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, fill:{color:fill}, line:{color:fill, width:0.5}, rectRadius:0.05 });
  s.addText(label, { x, y, w, h, fontSize:sz, bold:true, color:txtColor, align:"center", valign:"middle", fontFace:"Calibri", margin:0 });
}

function grpBox(s, label, x, y, w, h, borderColor, lblColor) {
  lblColor = lblColor || borderColor;
  s.addShape(pres.shapes.RECTANGLE, { x, y, w, h, fill:{color:"FFFFFF", transparency:100}, line:{color:borderColor, width:1.5, dashType:"dash"} });
  if (label) s.addText(label, { x:x+0.08, y:y+0.04, w:w-0.16, h:0.22, fontSize:7, bold:true, color:lblColor, fontFace:"Calibri", margin:0 });
}

function arrowH(s, x1, y, x2, color) {
  color = color || C.slateD;
  s.addShape(pres.shapes.LINE, { x:x1, y, w:x2-x1, h:0, line:{color, width:1.3, endArrowType:"triangle"} });
}
function arrowV(s, x, y1, y2, color) {
  color = color || C.slateD;
  s.addShape(pres.shapes.LINE, { x, y:y1, w:0, h:y2-y1, line:{color, width:1.3, endArrowType:"triangle"} });
}

// ════════════════════════════════════════════════════════════════════════════
// SLIDE 1 — TITLE
// ════════════════════════════════════════════════════════════════════════════
{
  let s = pres.addSlide();
  s.background = { color: C.darkBg };
  // Left accent bar
  s.addShape(pres.shapes.RECTANGLE, { x:0, y:0, w:0.45, h:7.5, fill:{color:C.indigo}, line:{color:C.indigo} });
  // Logo circle
  s.addShape(pres.shapes.OVAL, { x:0.75, y:1.2, w:1.1, h:1.1, fill:{color:C.indigo}, line:{color:C.purple, width:2} });
  s.addText("N", { x:0.75, y:1.2, w:1.1, h:1.1, fontSize:40, bold:true, color:C.white, align:"center", valign:"middle", fontFace:"Calibri", margin:0 });
  // Title
  s.addText("NEXUS", { x:2.1, y:1.0, w:9.5, h:1.2, fontSize:78, bold:true, color:C.white, fontFace:"Calibri", margin:0 });
  s.addShape(pres.shapes.RECTANGLE, { x:2.1, y:2.35, w:9, h:0.04, fill:{color:C.indigo}, line:{color:C.indigo} });
  s.addText("Multi-Agent Engineering Intelligence Platform", { x:2.1, y:2.45, w:10.5, h:0.5, fontSize:20, color:C.slate, fontFace:"Calibri", margin:0 });
  s.addText("Autonomous Hardware Design  ·  LangGraph Orchestration  ·  Multi-Cloud Kubernetes", { x:2.1, y:3.05, w:10.5, h:0.38, fontSize:12, color:"64748B", fontFace:"Calibri", margin:0 });
  s.addText("Lanre Bolaji  |  Senior AI Engineer — Agentic Platform Lead", { x:2.1, y:3.6, w:9.5, h:0.45, fontSize:16, bold:true, color:C.indigo, fontFace:"Calibri", margin:0 });
  s.addText("Portfolio Project  ·  March 2026  ·  github.com/bolajil/nexus-agentic-platform", { x:2.1, y:4.12, w:10.5, h:0.35, fontSize:11, color:"475569", fontFace:"Calibri", margin:0 });
  // Badges
  const badges = [["LangGraph","4F46E5"],["FastAPI","059669"],["Next.js 15","18181B"],["ChromaDB","F59E0B"],["Redis","DC382D"],["Kubernetes","326CE5"],["Langfuse","7C3AED"],["GPT-4o","10A37F"]];
  let bx = 2.1;
  badges.forEach(([lbl,col]) => {
    const bw = Math.max(lbl.length * 0.085 + 0.3, 1.0);
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x:bx, y:5.1, w:bw, h:0.38, fill:{color:col}, line:{color:col}, rectRadius:0.05 });
    s.addText(lbl, { x:bx, y:5.1, w:bw, h:0.38, fontSize:9.5, bold:true, color:C.white, align:"center", valign:"middle", fontFace:"Calibri", margin:0 });
    bx += bw + 0.16;
  });
  s.addText("github.com/bolajil/nexus-agentic-platform", { x:2.1, y:6.85, w:7, h:0.3, fontSize:10, color:"334155", fontFace:"Calibri", margin:0 });
}

// ════════════════════════════════════════════════════════════════════════════
// SLIDE 2 — WHAT IS NEXUS?
// ════════════════════════════════════════════════════════════════════════════
{
  let s = pres.addSlide();
  s.background = { color: C.darkBg };
  hdrBar(s, "What is NEXUS?", "Production-grade multi-agent AI platform for autonomous hardware design — built as a Senior AI Engineer portfolio showcase");
  const cols = [
    { icon:"⚙️", title:"Autonomous Design Pipeline", color:C.indigo,
      body:"LangGraph StateGraph orchestrates 6 specialist AI agents — from parsing engineering briefs through physics simulation, Pareto optimisation, to FreeCAD output and final structured report generation. SSE streaming shows every agent step in real time." },
    { icon:"🔬", title:"Engineering Knowledge Base", color:"0891B2",
      body:"BM25 + ChromaDB cosine hybrid search with Reciprocal Rank Fusion (RRF). Engineering-aware tokeniser preserves domain symbols: Re, Nu, Pr, Isp, LMTD, NTU, Von Mises — across 9 KB documents in 4 engineering domains." },
    { icon:"☁️", title:"Production Cloud Ready", color:C.purple,
      body:"Terraform IaC for AWS (EKS 1.29), GCP (GKE Autopilot), Azure (AKS). K8s HPA scales backend 3–20 pods, PodDisruptionBudget, TopologySpreadConstraints, WAFv2, cert-manager TLS, kube-prometheus-stack alerts." },
  ];
  cols.forEach((col, i) => {
    const x = 0.4 + i * 4.25;
    s.addShape(pres.shapes.RECTANGLE, { x, y:1.1, w:4.05, h:5.6, fill:{color:"111827"}, line:{color:col.color, width:1.5}, shadow:makeShadow() });
    s.addShape(pres.shapes.RECTANGLE, { x, y:1.1, w:4.05, h:0.08, fill:{color:col.color}, line:{color:col.color} });
    s.addText(col.icon, { x, y:1.3, w:4.05, h:0.75, fontSize:32, align:"center", valign:"middle", margin:0 });
    s.addText(col.title, { x:x+0.18, y:2.18, w:3.7, h:0.65, fontSize:13.5, bold:true, color:C.white, fontFace:"Calibri", margin:0 });
    s.addText(col.body, { x:x+0.18, y:2.9, w:3.7, h:3.6, fontSize:11, color:C.slate, fontFace:"Calibri", margin:0 });
  });
  // Bottom stats
  const stats = [["24","Langfuse traces\ntracked (dev)"],["6","AI agents in\npipeline"],["3","Cloud platforms\nsupported"],["2","Storage engines\n(BM25 + Vector)"]];
  stats.forEach(([num, lbl], i) => {
    s.addText(num, { x:0.4+i*3.1, y:6.85, w:1.4, h:0.5, fontSize:36, bold:true, color:C.indigo, align:"center", fontFace:"Calibri", margin:0 });
    s.addText(lbl, { x:1.85+i*3.1, y:6.88, w:1.4, h:0.45, fontSize:9, color:C.slate, fontFace:"Calibri", margin:0 });
  });
}

// ════════════════════════════════════════════════════════════════════════════
// SLIDE 3 — SYSTEM ARCHITECTURE (GENERAL)
// ════════════════════════════════════════════════════════════════════════════
{
  let s = pres.addSlide();
  s.background = { color: C.lightBg };
  hdrBar(s, "System Architecture — General Overview", "End-to-end component map: browser → FastAPI → LangGraph → data stores → observability");

  // User
  svc(s, "👤  User Browser", 0.3, 1.15, 2.1, 0.65, "334155");
  arrowH(s, 2.43, 1.475, 3.0, C.slateD);

  // Frontend
  svc(s, "Next.js 15  :3002", 3.0, 1.15, 2.3, 0.65, "18181B");
  s.addText("Aurora shader  ·  JWT middleware\n/login  /register  /integrations  /change-password", { x:3.0, y:1.84, w:2.3, h:0.45, fontSize:7.5, color:C.textMid, align:"center", fontFace:"Calibri", margin:0 });
  arrowH(s, 5.33, 1.475, 5.95, C.slateD);

  // Backend
  svc(s, "FastAPI  :8003", 5.95, 1.15, 2.4, 0.65, C.indigo);
  s.addText("JWT auth  ·  slowapi rate limit\nSSE streaming  ·  REST API  ·  Langfuse traces", { x:5.95, y:1.84, w:2.4, h:0.45, fontSize:7.5, color:C.textMid, align:"center", fontFace:"Calibri", margin:0 });

  // Arrow down to pipeline
  arrowV(s, 7.15, 1.82, 2.7, C.indigo);

  // LangGraph Pipeline group
  grpBox(s, "LangGraph StateGraph Pipeline  (nexus-pipeline root span)", 5.4, 2.7, 7.6, 2.85, C.indigo, C.indigo);
  const agents = [
    ["Requirements\nEngineer","4F46E5"],["Research\nScientist","0891B2"],["Design\nEngineer","059669"],
    ["Physics\nSimulator","D97706"],["Optimisation\nEngineer","7C3AED"],["Technical\nWriter","DB2777"],
  ];
  agents.forEach(([lbl, col], i) => {
    const ax = 5.6 + i * 1.22;
    svc(s, lbl, ax, 3.05, 1.15, 1.05, col, C.white, 7.5);
    if (i < 5) s.addShape(pres.shapes.LINE, { x:ax+1.15, y:3.575, w:0.07, h:0, line:{color:C.white, width:1.5, endArrowType:"triangle"} });
  });

  // Data stores (left)
  svc(s, "Redis  :6379", 0.3, 2.7, 2.0, 0.65, "DC382D");
  s.addText("JWT tokens · session data · 7-day TTL", { x:0.3, y:3.38, w:2.0, h:0.35, fontSize:7.5, color:C.textMid, align:"center", fontFace:"Calibri", margin:0 });

  svc(s, "ChromaDB  :8004", 0.3, 3.9, 2.0, 0.65, C.amber, C.textDark);
  s.addText("Cosine similarity · 9 KB documents\nBM25 in-memory index (RRF fusion)", { x:0.3, y:4.58, w:2.0, h:0.4, fontSize:7.5, color:C.textMid, align:"center", fontFace:"Calibri", margin:0 });

  svc(s, "OpenAI GPT-4o", 2.6, 3.9, 2.1, 0.65, "10A37F");
  s.addText("LLM inference\ntext-embedding-3-small", { x:2.6, y:4.58, w:2.1, h:0.4, fontSize:7.5, color:C.textMid, align:"center", fontFace:"Calibri", margin:0 });

  svc(s, "Langfuse v3.7", 2.6, 2.7, 2.1, 0.65, C.purple);
  s.addText("Root span + 6 agent spans\nUser tracking · cost monitoring", { x:2.6, y:3.38, w:2.1, h:0.4, fontSize:7.5, color:C.textMid, align:"center", fontFace:"Calibri", margin:0 });

  // Connection lines
  arrowH(s, 5.95, 1.47, 2.33, C.grayBd);
  arrowH(s, 5.95, 3.03, 4.73, C.grayBd);
  arrowH(s, 5.95, 4.22, 4.73, C.grayBd);

  // Collaboration row
  svc(s, "Slack Webhook  |  Microsoft Teams  |  SMTP Email", 0.3, 5.65, 7.0, 0.58, "1E293B");
  s.addText("Share completed designs for review  ·  Vote: Approve / Request Changes / Reject  ·  Notification on each vote", { x:0.3, y:6.27, w:7.0, h:0.3, fontSize:8, color:C.textMid, align:"center", fontFace:"Calibri", margin:0 });
  arrowV(s, 7.15, 5.55, 5.65, C.slateD);

  // FreeCAD / CAD output
  svc(s, "FreeCAD Headless\nSTEP + STL output", 7.5, 5.65, 2.3, 0.58, C.emerald);
  s.addText("3D viewer in browser (Three.js)", { x:7.5, y:6.27, w:2.3, h:0.3, fontSize:7.5, color:C.textMid, align:"center", fontFace:"Calibri", margin:0 });
  arrowH(s, 12.98, 3.6, 9.83, C.grayBd);
  svc(s, "FreeCADCmd.exe", 9.85, 5.65, 2.1, 0.58, "475569");
}

// ════════════════════════════════════════════════════════════════════════════
// SLIDE 4 — 6-AGENT LANGGRAPH PIPELINE
// ════════════════════════════════════════════════════════════════════════════
{
  let s = pres.addSlide();
  s.background = { color: C.darkBg };
  hdrBar(s, "6-Agent LangGraph Pipeline", "Directed StateGraph DAG — each node is an async specialist agent; SSE streams every step to the browser");

  const agents = [
    { icon:"📋", name:"Requirements\nEngineer",  color:"4F46E5", role:"Parses engineering brief",        out:"domain, constraints,\ntargets, units" },
    { icon:"🔬", name:"Research\nScientist",     color:"0891B2", role:"BM25 + Semantic RAG search",      out:"equations, prior designs,\nbenchmarks" },
    { icon:"📐", name:"Design\nEngineer",        color:"059669", role:"Physics-based calculations",     out:"parameters, materials,\ngeometry" },
    { icon:"⚡", name:"Physics\nSimulator",      color:"D97706", role:"NumPy/SciPy simulation",         out:"stress, thermal,\nflow results" },
    { icon:"🎯", name:"Optimisation\nEngineer",  color:"7C3AED", role:"Pareto-front multi-objective",   out:"optimal config,\ntrade-off surface" },
    { icon:"📄", name:"Technical\nWriter",       color:"DB2777", role:"Structured report + CAD output", out:"JSON report,\nSTEP + STL files" },
  ];

  agents.forEach((a, i) => {
    const x = 0.3 + i * 2.1;
    s.addShape(pres.shapes.RECTANGLE, { x, y:1.1, w:1.92, h:4.35, fill:{color:"111827"}, line:{color:a.color, width:1.5}, shadow:makeShadow() });
    s.addShape(pres.shapes.RECTANGLE, { x, y:1.1, w:1.92, h:0.07, fill:{color:a.color}, line:{color:a.color} });
    s.addText(a.icon, { x, y:1.3, w:1.92, h:0.65, fontSize:30, align:"center", valign:"middle", margin:0 });
    s.addText(a.name,  { x:x+0.06, y:2.05, w:1.8, h:0.6,  fontSize:11, bold:true, color:C.white, align:"center", fontFace:"Calibri", margin:0 });
    s.addText(a.role,  { x:x+0.06, y:2.72, w:1.8, h:0.42, fontSize:9,  color:a.color, align:"center", fontFace:"Calibri", margin:0 });
    s.addText("OUTPUT",{ x:x+0.06, y:3.22, w:1.8, h:0.24, fontSize:7,  bold:true, color:"334155", align:"center", fontFace:"Calibri", margin:0 });
    s.addText(a.out,   { x:x+0.06, y:3.5,  w:1.8, h:0.7,  fontSize:9,  color:C.slate, align:"center", fontFace:"Calibri", margin:0 });
    if (i < 5) s.addShape(pres.shapes.LINE, { x:x+1.92, y:3.275, w:0.18, h:0, line:{color:a.color, width:2, endArrowType:"triangle"} });
  });

  s.addText("START", { x:0.3,  y:0.93, w:1.92, h:0.2, fontSize:8, bold:true, color:C.emerald, align:"center", fontFace:"Calibri", margin:0 });
  s.addText("END",   { x:10.98,y:0.93, w:1.92, h:0.2, fontSize:8, bold:true, color:C.red,     align:"center", fontFace:"Calibri", margin:0 });

  s.addShape(pres.shapes.RECTANGLE, { x:0.3, y:5.62, w:12.7, h:1.55, fill:{color:"111827"}, line:{color:"1E293B"} });
  s.addText([
    { text:"SSE Streaming", options:{bold:true, color:C.indigo} },
    { text:"  — agent_start → agent_thought → tool_call → tool_result → agent_complete → session_complete\n", options:{color:C.slate} },
    { text:"Redis",         options:{bold:true, color:"DC382D"} },
    { text:"  — session persisted 7-day TTL  ·  ", options:{color:C.slate} },
    { text:"Langfuse",      options:{bold:true, color:C.purple} },
    { text:"  — root span + 6 nested agent child spans · token usage + cost per agent", options:{color:C.slate} },
  ], { x:0.5, y:5.72, w:12.3, h:1.35, fontSize:11, fontFace:"Calibri", valign:"middle", margin:0 });
}

// ════════════════════════════════════════════════════════════════════════════
// SLIDE 5 — HYBRID RAG SEARCH
// ════════════════════════════════════════════════════════════════════════════
{
  let s = pres.addSlide();
  s.background = { color: C.darkBg };
  hdrBar(s, "Hybrid RAG Search — BM25 + Semantic + RRF", "Engineering-aware retrieval that handles both exact symbols and concept similarity");

  // Flow
  svc(s, "Query\n'heat sink NTU effectiveness'", 0.3, 1.2, 3.0, 0.75, C.indigo);

  // Split arrow to BM25 and Semantic
  arrowV(s, 1.8, 1.95, 2.55, C.slate);
  s.addShape(pres.shapes.LINE, { x:1.8, y:2.55, w:2.4, h:0,  line:{color:C.slate, width:1.2} });
  s.addShape(pres.shapes.LINE, { x:1.8, y:2.55, w:0,   h:0.45, line:{color:C.slate, width:1.2} });
  arrowH(s, 4.2, 2.55, 4.65, C.slate);
  arrowV(s, 1.8, 2.55, 3.7, C.slate);

  svc(s, "BM25 Search\nrank-bm25==0.2.2", 4.65, 2.1, 2.8, 0.7, "0891B2");
  s.addText("Weight: 0.4  ·  Engineering tokeniser\npreserves Re, Nu, Pr, Isp, LMTD, NTU", { x:4.65, y:2.84, w:2.8, h:0.45, fontSize:8, color:C.slate, align:"center", fontFace:"Calibri", margin:0 });

  svc(s, "Semantic Search\nChromaDB cosine similarity", 4.65, 3.5, 2.8, 0.7, C.amber, C.textDark);
  s.addText("Weight: 0.6  ·  text-embedding-3-small\n9 engineering KB docs (4 domains)", { x:4.65, y:4.24, w:2.8, h:0.45, fontSize:8, color:C.slate, align:"center", fontFace:"Calibri", margin:0 });

  arrowH(s, 7.48, 2.45, 7.9, C.slate);
  arrowH(s, 7.48, 3.85, 7.9, C.slate);

  svc(s, "Reciprocal Rank\nFusion (RRF)", 7.9, 2.9, 2.8, 0.7, C.purple);
  s.addText("score = Σ wᵢ / (k + rankᵢ(d))\nk = 60  ·  semantic 0.6  ·  BM25 0.4", { x:7.9, y:3.64, w:2.8, h:0.45, fontSize:9, color:C.slate, align:"center", fontFace:"Calibri", margin:0 });
  arrowH(s, 10.73, 3.25, 11.1, C.slate);
  svc(s, "Top-K Results\nto Research Agent", 11.1, 2.9, 2.0, 0.7, C.emerald);

  // Details cards
  const cards = [
    { title:"BM25 Index Lifecycle", color:C.indigo,
      body:"Startup: _sync_bm25_from_chroma() rebuilds index from existing ChromaDB docs on every startup\nUpsert: every document upload appends to _bm25_docs and calls _rebuild_bm25() immediately\nFallback: pure semantic search if rank-bm25 unavailable at runtime" },
    { title:"Why Hybrid for Engineering?", color:"0891B2",
      body:"BM25 finds 'Re=50000' exactly — semantic search misses specific numeric parameters\nChromaDB finds 'heat transfer' when query says 'thermal management' (concept similarity)\nEngineering tokeniser preserves two-letter symbols (Re, Nu, Pr) — standard tokenisers split these" },
    { title:"Knowledge Base Contents", color:C.amber,
      body:"9 documents across 4 domains: Heat Transfer (NTU method, LMTD), Fluid Dynamics (Reynolds, Bernoulli), Structural Mechanics (Von Mises, FEA), Propulsion (Isp, rocket nozzle)\nAll documents indexed in ChromaDB with cosine embeddings and BM25 term frequencies" },
  ];
  cards.forEach((c, i) => {
    const cx = 0.3 + i * 4.35;
    s.addShape(pres.shapes.RECTANGLE, { x:cx, y:4.85, w:4.15, h:2.4, fill:{color:"111827"}, line:{color:c.color, width:1} });
    s.addShape(pres.shapes.RECTANGLE, { x:cx, y:4.85, w:4.15, h:0.06, fill:{color:c.color}, line:{color:c.color} });
    s.addText(c.title, { x:cx+0.15, y:4.98, w:3.85, h:0.38, fontSize:11.5, bold:true, color:C.white, fontFace:"Calibri", margin:0 });
    s.addText(c.body,  { x:cx+0.15, y:5.4,  w:3.85, h:1.75, fontSize:9.5, color:C.slate, fontFace:"Calibri", margin:0 });
  });
}

// ════════════════════════════════════════════════════════════════════════════
// SLIDE 6 — TEAM COLLABORATION
// ════════════════════════════════════════════════════════════════════════════
{
  let s = pres.addSlide();
  s.background = { color: C.lightBg };
  hdrBar(s, "Team Collaboration", "Slack + Microsoft Teams + SMTP Email — share designs, run team review votes, get notified on every decision");

  // Step flow: Pipeline → ShareModal → Channels → ReviewPanel
  svc(s, "Pipeline\nCompletes", 0.3, 1.3, 1.85, 0.7, C.indigo);
  arrowH(s, 2.18, 1.65, 2.55, C.slateD);
  svc(s, "Share for\nReview", 2.55, 1.3, 1.85, 0.7, C.purple);
  s.addText("ShareModal — select channels\nadd message, choose recipients", { x:2.55, y:2.04, w:1.85, h:0.4, fontSize:8, color:C.textMid, align:"center", fontFace:"Calibri", margin:0 });

  arrowH(s, 4.43, 1.65, 4.8, C.slateD);

  // 3 channel dispatch
  const channels = [
    { name:"Slack",          sub:"Block Kit messages\nresults + deep-link button", color:"4A154B" },
    { name:"Microsoft Teams",sub:"Adaptive Card\nresults + deep-link button",   color:"5059C9" },
    { name:"SMTP Email",     sub:"HTML template\nGmail / Outlook / SendGrid",   color:"059669" },
  ];
  channels.forEach((ch, i) => {
    const cy = 1.1 + i * 1.1;
    svc(s, ch.name, 4.8, cy, 2.2, 0.65, ch.color);
    s.addText(ch.sub, { x:4.8, y:cy+0.68, w:2.2, h:0.35, fontSize:7.5, color:C.textMid, align:"center", fontFace:"Calibri", margin:0 });
    arrowH(s, 7.03, cy+0.325, 7.4, C.slateD);
  });

  // ReviewPanel
  grpBox(s, "ReviewPanel — Team Deliberation  (Redis-backed review thread)", 7.4, 1.0, 5.6, 2.55, C.indigo, C.indigo);
  const votes = [
    { icon:"✅", lbl:"Approve",          color:"059669", desc:"Design meets all\nengineering requirements" },
    { icon:"🔄", lbl:"Request Changes",  color:C.amber,  desc:"Suggest improvements\nbefore final acceptance" },
    { icon:"❌", lbl:"Reject",           color:C.red,    desc:"Design fails critical\nperformance criteria" },
  ];
  votes.forEach((v, i) => {
    const vx = 7.6 + i * 1.77;
    svc(s, v.icon+"  "+v.lbl, vx, 1.35, 1.6, 0.6, v.color);
    s.addText(v.desc, { x:vx, y:1.99, w:1.6, h:0.45, fontSize:8, color:C.textMid, align:"center", fontFace:"Calibri", margin:0 });
  });
  s.addText("Aggregated Decision Badge updates live  ·  Notification fires to all configured channels on each vote submission", { x:7.5, y:2.65, w:5.3, h:0.45, fontSize:8.5, color:C.textMid, align:"center", fontFace:"Calibri", margin:0 });

  // Integrations page
  s.addShape(pres.shapes.RECTANGLE, { x:0.3, y:3.85, w:12.7, h:1.35, fill:{color:"111827"}, line:{color:"1E293B"} });
  s.addText("Integrations Settings Page  (/integrations)", { x:0.5, y:3.95, w:6, h:0.38, fontSize:13, bold:true, color:C.white, fontFace:"Calibri", margin:0 });
  s.addText("Configure Slack webhook URL  ·  Teams webhook URL  ·  SMTP host/port/credentials\nTest each channel with one click  ·  Config stored in Redis per user  ·  Accessible from Sidebar nav", { x:0.5, y:4.37, w:12.3, h:0.72, fontSize:10.5, color:C.slate, fontFace:"Calibri", margin:0 });

  // Key files
  s.addShape(pres.shapes.RECTANGLE, { x:0.3, y:5.35, w:12.7, h:1.9, fill:{color:C.cardBg}, line:{color:C.grayBd} });
  s.addText("Key Files", { x:0.5, y:5.45, w:3, h:0.35, fontSize:12, bold:true, color:C.textDark, fontFace:"Calibri", margin:0 });
  const files = [
    "backend/app/core/notifiers.py  — send_slack(), send_teams(), send_email()",
    "backend/app/routers/integrations.py  — configure webhooks, test, share",
    "backend/app/routers/reviews.py  — submit vote, get aggregated decision",
    "frontend/app/components/ShareModal.tsx  — channel picker + message input",
    "frontend/app/components/ReviewPanel.tsx  — live vote thread with avatars",
    "frontend/app/integrations/page.tsx  — settings UI with test buttons",
  ];
  files.forEach((f, i) => {
    s.addText("• " + f, { x:0.5, y:5.85+i*0.3, w:12.3, h:0.28, fontSize:9, color:C.textMid, fontFace:"Calibri", margin:0 });
  });
}

// ════════════════════════════════════════════════════════════════════════════
// SLIDE 7 — AUTH, SECURITY & ADMIN
// ════════════════════════════════════════════════════════════════════════════
{
  let s = pres.addSlide();
  s.background = { color: C.darkBg };
  hdrBar(s, "Auth, Security & Admin", "JWT auth flow · bcrypt · refresh token rotation · WAF-ready infrastructure");

  // Left: JWT flow
  s.addText("JWT Auth Flow", { x:0.4, y:1.1, w:5.8, h:0.4, fontSize:15, bold:true, color:C.white, fontFace:"Calibri", margin:0 });
  const flow = [
    ["Login Request",  "POST /api/auth/login  with email + password",                C.indigo],
    ["bcrypt verify",  "passlib[bcrypt]  — constant-time to prevent enumeration",    "475569"],
    ["Issue Tokens",   "HS256 access (15 min)  ·  random refresh token (7 days Redis)","059669"],
    ["Route Guard",    "Next.js middleware.ts checks nexus_logged_in cookie",         "0891B2"],
    ["Bearer Token",   "Authorization: Bearer <jwt> on every FastAPI request",        C.purple],
  ];
  flow.forEach((f, i) => {
    const fy = 1.58 + i * 1.03;
    s.addShape(pres.shapes.RECTANGLE, { x:0.4, y:fy, w:5.8, h:0.85, fill:{color:"111827"}, line:{color:f[2], width:1} });
    s.addText(f[0], { x:0.55, y:fy+0.06, w:5.5, h:0.3,  fontSize:11, bold:true, color:C.white, fontFace:"Calibri", margin:0 });
    s.addText(f[1], { x:0.55, y:fy+0.4,  w:5.5, h:0.38, fontSize:9,  color:C.slate, fontFace:"Calibri", margin:0 });
    if (i < 4) arrowV(s, 3.3, fy+0.85, fy+1.03, f[2]);
  });

  // Right: Security controls
  s.addText("Security Controls", { x:6.6, y:1.1, w:6.4, h:0.4, fontSize:15, bold:true, color:C.white, fontFace:"Calibri", margin:0 });
  const sec = [
    { t:"Rate Limiting",    d:"slowapi: 5 req/min pipeline  ·  120 req/min all other routes",                      color:C.red },
    { t:"Security Headers", d:"HSTS  ·  CSP  ·  X-Frame-Options  ·  X-Content-Type-Options",                      color:C.amber },
    { t:"Prompt Guard",     d:"sanitise_brief() strips injection patterns before LLM invocation",                  color:C.purple },
    { t:"WAF Ready",        d:"AWS WAFv2 OWASP ruleset  ·  GCP Cloud Armor  ·  Azure Application Gateway WAF_v2", color:"0891B2" },
    { t:"Admin Account",    d:"admin@nexus.ai / 123password  ·  force_password_change on first login\n/change-password page with strength checklist + amber aurora background", color:C.emerald },
  ];
  sec.forEach((f, i) => {
    const fy = 1.58 + i * 1.03;
    s.addShape(pres.shapes.RECTANGLE, { x:6.6, y:fy, w:6.45, h:0.85, fill:{color:"111827"}, line:{color:"1E293B"} });
    s.addShape(pres.shapes.RECTANGLE, { x:6.6, y:fy, w:0.07, h:0.85, fill:{color:f.color}, line:{color:f.color} });
    s.addText(f.t, { x:6.8, y:fy+0.06, w:6.1, h:0.3,  fontSize:11, bold:true, color:C.white, fontFace:"Calibri", margin:0 });
    s.addText(f.d, { x:6.8, y:fy+0.4,  w:6.1, h:0.38, fontSize:9,  color:C.slate, fontFace:"Calibri", margin:0 });
  });
}

// ════════════════════════════════════════════════════════════════════════════
// SLIDE 8 — AWS ARCHITECTURE
// ════════════════════════════════════════════════════════════════════════════
{
  let s = pres.addSlide();
  s.background = { color: C.lightBg };
  hdrBar(s, "AWS Architecture", "EKS 1.29  ·  ElastiCache Redis HA  ·  WAFv2  ·  EFS (RWX)  ·  S3+KMS  ·  Route 53  ·  CloudWatch  ·  Secrets Manager");

  // Top routing row
  svc(s, "🌐\nInternet", 0.3, 1.05, 1.1, 0.8, "334155");
  arrowH(s, 1.43, 1.45, 1.8, C.awsRed);
  svc(s, "Route 53", 1.8, 1.05, 1.25, 0.65, C.awsGrn);
  s.addText("DNS Failover\nHealth Checks", { x:1.8, y:1.73, w:1.25, h:0.35, fontSize:7, color:C.textMid, align:"center", fontFace:"Calibri", margin:0 });
  arrowH(s, 3.08, 1.375, 3.35, C.awsOrg);
  svc(s, "WAFv2 +\nCloudFront", 3.35, 1.05, 1.6, 0.65, C.awsOrg);
  s.addText("OWASP ruleset\n2000 req/5min limit", { x:3.35, y:1.73, w:1.6, h:0.35, fontSize:7, color:C.textMid, align:"center", fontFace:"Calibri", margin:0 });
  arrowH(s, 4.98, 1.375, 5.25, C.awsOrg);
  svc(s, "Application\nLoad Balancer", 5.25, 1.05, 1.6, 0.65, C.awsOrg);
  s.addText("Multi-AZ  ·  SSL termination", { x:5.25, y:1.73, w:1.6, h:0.35, fontSize:7, color:C.textMid, align:"center", fontFace:"Calibri", margin:0 });
  arrowV(s, 6.05, 1.73, 2.18, C.awsOrg);

  // VPC
  grpBox(s, "VPC  (us-east-1)  —  3 Availability Zones", 0.3, 2.18, 8.85, 4.77, C.awsOrg, C.awsOrg);
  grpBox(s, "EKS Cluster 1.29  (On-Demand system pool + Spot worker pool)", 0.5, 2.48, 8.45, 2.8, C.awsBlu, C.awsBlu);

  // 3 AZ boxes
  ["AZ-1a","AZ-1b","AZ-1c"].forEach((az, i) => {
    const ax = 0.7 + i * 2.7;
    grpBox(s, az, ax, 2.75, 2.45, 2.3, C.awsOrg);
    svc(s, "Frontend\nNext.js  2-10 pods", ax+0.08, 3.05, 1.12, 0.75, C.awsBlu);
    svc(s, "Backend\nFastAPI  3-20 pods", ax+1.25, 3.05, 1.12, 0.75, C.indigo);
    s.addText("HPA · PDB · TopologySpread", { x:ax, y:3.84, w:2.45, h:0.22, fontSize:6.5, color:C.textMid, align:"center", fontFace:"Calibri", margin:0 });
  });

  // Stateful services in VPC
  svc(s, "ElastiCache Redis\nr7g.medium  Multi-AZ HA", 0.5, 5.45, 2.5, 0.65, C.awsRed);
  s.addText("AOF + RDB · auto-failover", { x:0.5, y:6.13, w:2.5, h:0.22, fontSize:7, color:C.textMid, align:"center", fontFace:"Calibri", margin:0 });
  svc(s, "ChromaDB\nStatefulSet  20Gi EBS", 3.2, 5.45, 2.5, 0.65, C.amber, C.textDark);
  s.addText("Headless service · persistent", { x:3.2, y:6.13, w:2.5, h:0.22, fontSize:7, color:C.textMid, align:"center", fontFace:"Calibri", margin:0 });
  svc(s, "EFS (RWX)\nCAD file storage", 5.9, 5.45, 2.2, 0.65, C.awsOrg);
  s.addText("Shared across all backend pods", { x:5.9, y:6.13, w:2.2, h:0.22, fontSize:7, color:C.textMid, align:"center", fontFace:"Calibri", margin:0 });

  // Right column: supporting services
  const rs = [
    ["S3 + KMS","Docs + CAD\nLifecycle rules",C.awsRed],   ["ECR","Immutable tags\nscan-on-push",C.awsOrg],
    ["Secrets Mgr","JWT · API keys\nESO integration",C.awsRed],["CloudWatch","Dashboard + alarms\nerror rate · latency","FF4F8B"],
    ["ACM","TLS certs\nauto-renewal",C.awsGrn],            ["EBS Snap","Auto backups\nChrома checkpoints",C.awsRed],
  ];
  rs.forEach((r, i) => {
    const rc = i % 2, rw = Math.floor(i / 2);
    const rx = 9.45 + rc * 1.92, ry = 1.05 + rw * 1.48;
    svc(s, r[0], rx, ry, 1.75, 0.65, r[2]);
    s.addText(r[1], { x:rx, y:ry+0.68, w:1.75, h:0.35, fontSize:6.5, color:C.textMid, align:"center", fontFace:"Calibri", margin:0 });
  });

  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x:9.45, y:6.5, w:3.67, h:0.55, fill:{color:C.awsOrg}, line:{color:C.awsOrg}, rectRadius:0.05 });
  s.addText("Est. ~$700 / month  (3 AZ production)", { x:9.45, y:6.5, w:3.67, h:0.55, fontSize:10, bold:true, color:C.white, align:"center", valign:"middle", fontFace:"Calibri", margin:0 });
}

// ════════════════════════════════════════════════════════════════════════════
// SLIDE 9 — GCP ARCHITECTURE
// ════════════════════════════════════════════════════════════════════════════
{
  let s = pres.addSlide();
  s.background = { color: C.lightBg };
  hdrBar(s, "GCP Architecture", "GKE Autopilot  ·  Memorystore Redis HA  ·  Cloud Armor  ·  GCS+KMS  ·  Artifact Registry  ·  Secret Manager  ·  Cloud Monitoring");

  svc(s, "🌐\nInternet", 0.3, 1.05, 1.1, 0.8, "334155");
  arrowH(s, 1.43, 1.45, 1.8, C.gcpBlu);
  svc(s, "Cloud DNS", 1.8, 1.05, 1.3, 0.65, C.gcpBlu);
  s.addText("Managed zones\nhealth checks", { x:1.8, y:1.73, w:1.3, h:0.35, fontSize:7, color:C.textMid, align:"center", fontFace:"Calibri", margin:0 });
  arrowH(s, 3.13, 1.375, 3.4, C.gcpBlu);
  svc(s, "Cloud Armor", 3.4, 1.05, 1.5, 0.65, C.gcpRed);
  s.addText("DDoS protection\nrate limiting rules", { x:3.4, y:1.73, w:1.5, h:0.35, fontSize:7, color:C.textMid, align:"center", fontFace:"Calibri", margin:0 });
  arrowH(s, 4.93, 1.375, 5.2, C.gcpBlu);
  svc(s, "Global HTTPS\nLoad Balancer", 5.2, 1.05, 1.6, 0.65, C.gcpBlu);
  s.addText("SSL termination\nbackend services", { x:5.2, y:1.73, w:1.6, h:0.35, fontSize:7, color:C.textMid, align:"center", fontFace:"Calibri", margin:0 });
  arrowV(s, 6.0, 1.73, 2.18, C.gcpBlu);

  grpBox(s, "GCP Project  (us-central1)", 0.3, 2.18, 8.85, 4.77, C.gcpBlu, C.gcpBlu);
  grpBox(s, "GKE Autopilot  (pay-per-pod — zero node management — auto-upgrades)", 0.5, 2.48, 8.45, 2.8, C.gcpGrn, C.gcpGrn);

  ["Pool A","Pool B","Pool C"].forEach((lbl, i) => {
    const ax = 0.7 + i * 2.7;
    grpBox(s, lbl, ax, 2.75, 2.45, 2.3, C.gcpGrn);
    svc(s, "Frontend\nNext.js  2-10 pods", ax+0.08, 3.05, 1.12, 0.75, C.gcpBlu);
    svc(s, "Backend\nFastAPI  3-20 pods", ax+1.25, 3.05, 1.12, 0.75, C.gcpDrk);
    s.addText("Autopilot scales automatically", { x:ax, y:3.84, w:2.45, h:0.22, fontSize:6.5, color:C.textMid, align:"center", fontFace:"Calibri", margin:0 });
  });

  svc(s, "Memorystore Redis\nStandard HA Tier", 0.5, 5.45, 2.5, 0.65, C.gcpRed);
  s.addText("Regional HA · auto-failover", { x:0.5, y:6.13, w:2.5, h:0.22, fontSize:7, color:C.textMid, align:"center", fontFace:"Calibri", margin:0 });
  svc(s, "ChromaDB\nStatefulSet  20Gi PD", 3.2, 5.45, 2.5, 0.65, C.amber, C.textDark);
  s.addText("Persistent Disk · headless svc", { x:3.2, y:6.13, w:2.5, h:0.22, fontSize:7, color:C.textMid, align:"center", fontFace:"Calibri", margin:0 });
  svc(s, "GCS + KMS\nObject Storage", 5.9, 5.45, 2.2, 0.65, C.gcpYlw, C.textDark);
  s.addText("Lifecycle rules · CMEK", { x:5.9, y:6.13, w:2.2, h:0.22, fontSize:7, color:C.textMid, align:"center", fontFace:"Calibri", margin:0 });

  const gs = [
    ["Artifact\nRegistry","Container images\nscan-on-push",C.gcpBlu],    ["Secret\nManager","JWT · API keys\nESO integration",C.gcpRed],
    ["Cloud\nMonitoring","Uptime checks\nalert policies",C.gcpGrn],       ["Langfuse","Tracing callbacks\nper pipeline run",C.purple],
    ["cert-manager","Let's Encrypt TLS\nClusterIssuer",C.gcpGrn],         ["Prometheus","kube-prometheus\nalert rules",C.gcpRed],
  ];
  gs.forEach((g, i) => {
    const rc = i % 2, rw = Math.floor(i / 2);
    const rx = 9.45 + rc * 1.92, ry = 1.05 + rw * 1.48;
    svc(s, g[0], rx, ry, 1.75, 0.65, g[2]);
    s.addText(g[1], { x:rx, y:ry+0.68, w:1.75, h:0.35, fontSize:6.5, color:C.textMid, align:"center", fontFace:"Calibri", margin:0 });
  });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x:9.45, y:6.5, w:3.67, h:0.55, fill:{color:C.gcpBlu}, line:{color:C.gcpBlu}, rectRadius:0.05 });
  s.addText("Est. ~$590 / month  (most cost-efficient)", { x:9.45, y:6.5, w:3.67, h:0.55, fontSize:10, bold:true, color:C.white, align:"center", valign:"middle", fontFace:"Calibri", margin:0 });
}

// ════════════════════════════════════════════════════════════════════════════
// SLIDE 10 — AZURE ARCHITECTURE
// ════════════════════════════════════════════════════════════════════════════
{
  let s = pres.addSlide();
  s.background = { color: C.lightBg };
  hdrBar(s, "Azure Architecture", "AKS 1.29  ·  Application Gateway WAF_v2  ·  Azure Cache Redis Premium  ·  Azure Files (RWX)  ·  ACR  ·  Key Vault  ·  Log Analytics");

  svc(s, "🌐\nInternet", 0.3, 1.05, 1.1, 0.8, "334155");
  arrowH(s, 1.43, 1.45, 1.8, C.azrBlu);
  svc(s, "Azure DNS", 1.8, 1.05, 1.3, 0.65, C.azrBlu);
  s.addText("Managed zones\nhealth probes", { x:1.8, y:1.73, w:1.3, h:0.35, fontSize:7, color:C.textMid, align:"center", fontFace:"Calibri", margin:0 });
  arrowH(s, 3.13, 1.375, 3.4, C.azrBlu);
  svc(s, "App Gateway\nWAF_v2", 3.4, 1.05, 1.55, 0.65, C.azrBlu);
  s.addText("Zone-redundant\nOWASP ruleset", { x:3.4, y:1.73, w:1.55, h:0.35, fontSize:7, color:C.textMid, align:"center", fontFace:"Calibri", margin:0 });
  arrowH(s, 4.98, 1.375, 5.25, C.azrBlu);
  svc(s, "Internal Load\nBalancer", 5.25, 1.05, 1.55, 0.65, C.azrBlu);
  s.addText("SSL offload\nhealth probes", { x:5.25, y:1.73, w:1.55, h:0.35, fontSize:7, color:C.textMid, align:"center", fontFace:"Calibri", margin:0 });
  arrowV(s, 6.02, 1.73, 2.18, C.azrBlu);

  grpBox(s, "Virtual Network  (eastus)  —  Zone-Redundant  ·  Key Vault CSI Driver  ·  Container Insights enabled", 0.3, 2.18, 8.85, 4.77, C.azrBlu, C.azrBlu);
  grpBox(s, "AKS 1.29  (System NodePool + Spot NodePool  ·  Key Vault CSI  ·  Container Insights)", 0.5, 2.48, 8.45, 2.8, C.azrPrp, C.azrPrp);

  ["Zone 1","Zone 2","Zone 3"].forEach((z, i) => {
    const ax = 0.7 + i * 2.7;
    grpBox(s, z, ax, 2.75, 2.45, 2.3, C.azrBlu);
    svc(s, "Frontend\nNext.js  2-10 pods", ax+0.08, 3.05, 1.12, 0.75, C.azrBlu);
    svc(s, "Backend\nFastAPI  3-20 pods", ax+1.25, 3.05, 1.12, 0.75, C.azrPrp);
    s.addText("HPA · PDB · Spot scale-out", { x:ax, y:3.84, w:2.45, h:0.22, fontSize:6.5, color:C.textMid, align:"center", fontFace:"Calibri", margin:0 });
  });

  svc(s, "Azure Cache Redis\nPremium  VNet-injected", 0.5, 5.45, 2.5, 0.65, C.azrBlu);
  s.addText("RDB backups · geo-replication", { x:0.5, y:6.13, w:2.5, h:0.22, fontSize:7, color:C.textMid, align:"center", fontFace:"Calibri", margin:0 });
  svc(s, "ChromaDB\nStatefulSet  20Gi Disk", 3.2, 5.45, 2.5, 0.65, C.amber, C.textDark);
  s.addText("Azure Disk · headless svc", { x:3.2, y:6.13, w:2.5, h:0.22, fontSize:7, color:C.textMid, align:"center", fontFace:"Calibri", margin:0 });
  svc(s, "Azure Files\nRWX Share  100Gi ZRS", 5.9, 5.45, 2.2, 0.65, C.azrBlu);
  s.addText("Shared CAD output across pods", { x:5.9, y:6.13, w:2.2, h:0.22, fontSize:7, color:C.textMid, align:"center", fontFace:"Calibri", margin:0 });

  const az = [
    ["ACR Premium","Geo-replication\nscan-on-push",C.azrBlu],        ["Key Vault","JWT · API keys\nCSI driver",C.azrPrp],
    ["Log Analytics","Container Insights\ndiagnostics",C.azrBlu],    ["Azure Monitor","Alert rules\ndashboards","0078D4"],
    ["Blob ZRS","Docs + CAD output\nlifecycle rules",C.azrBlu],      ["cert-manager","Let's Encrypt TLS\nClusterIssuer",C.azrGrn],
  ];
  az.forEach((a, i) => {
    const rc = i % 2, rw = Math.floor(i / 2);
    const rx = 9.45 + rc * 1.92, ry = 1.05 + rw * 1.48;
    svc(s, a[0], rx, ry, 1.75, 0.65, a[2]);
    s.addText(a[1], { x:rx, y:ry+0.68, w:1.75, h:0.35, fontSize:6.5, color:C.textMid, align:"center", fontFace:"Calibri", margin:0 });
  });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x:9.45, y:6.5, w:3.67, h:0.55, fill:{color:C.azrBlu}, line:{color:C.azrBlu}, rectRadius:0.05 });
  s.addText("Est. ~$750 / month  (zone-redundant)", { x:9.45, y:6.5, w:3.67, h:0.55, fontSize:10, bold:true, color:C.white, align:"center", valign:"middle", fontFace:"Calibri", margin:0 });
}

// ════════════════════════════════════════════════════════════════════════════
// SLIDE 11 — OBSERVABILITY
// ════════════════════════════════════════════════════════════════════════════
{
  let s = pres.addSlide();
  s.background = { color: C.darkBg };
  hdrBar(s, "Observability Stack", "Langfuse v3.7  ·  OpenTelemetry  ·  Structlog JSON  ·  Locust load tests  ·  User-level tracking");

  // Big stat
  s.addShape(pres.shapes.RECTANGLE, { x:0.4, y:1.1, w:3.3, h:2.85, fill:{color:"111827"}, line:{color:C.purple, width:1.5} });
  s.addText("24", { x:0.4, y:1.35, w:3.3, h:1.1, fontSize:80, bold:true, color:C.purple, align:"center", fontFace:"Calibri", margin:0 });
  s.addText("Langfuse Traces\nTracked in Dev", { x:0.4, y:2.52, w:3.3, h:0.55, fontSize:14, color:C.slate, align:"center", fontFace:"Calibri", margin:0 });
  s.addText("6 per pipeline run\n(1 root + 6 agent child spans)", { x:0.4, y:3.12, w:3.3, h:0.5, fontSize:9.5, color:"475569", align:"center", fontFace:"Calibri", margin:0 });

  // Trace hierarchy
  s.addText("Trace Hierarchy", { x:4.0, y:1.1, w:5, h:0.4, fontSize:14, bold:true, color:C.white, fontFace:"Calibri", margin:0 });
  const traces = [
    ["nexus-pipeline  (root span — session_id, user_id)", C.purple, 0],
    ["agent:requirements  — requirements engineer span",  "4F46E5", 0.35],
    ["agent:research  ← LangChain CallbackHandler",       "0891B2", 0.35],
    ["agent:design  — physics calculation span",          "059669", 0.35],
    ["agent:simulation  — NumPy/SciPy span",              "D97706", 0.35],
    ["agent:optimization  — Pareto span",                 "7C3AED", 0.35],
    ["agent:report  — structured output span",            "DB2777", 0.35],
  ];
  traces.forEach((t, i) => {
    s.addShape(pres.shapes.RECTANGLE, { x:4.0+t[2], y:1.58+i*0.43, w:0.07, h:0.34, fill:{color:t[1]}, line:{color:t[1]} });
    s.addText(t[0], { x:4.2+t[2], y:1.58+i*0.43, w:5.5, h:0.34, fontSize:10, color:t[2]>0?C.slate:C.white, fontFace:"Calibri", margin:0 });
  });

  // Known gap box
  s.addShape(pres.shapes.RECTANGLE, { x:0.4, y:4.12, w:12.55, h:1.45, fill:{color:"1C0A0A"}, line:{color:C.red, width:1} });
  s.addText("⚠️  Known Gap — Cost & User Tracking Shows $0.00", { x:0.6, y:4.2, w:9, h:0.38, fontSize:12, bold:true, color:C.red, fontFace:"Calibri", margin:0 });
  s.addText("Root cause: token usage must flow through CallbackHandler with correct trace_id nesting so cost rolls up to the root span. Model prices ARE registered via REST API at startup (_register_model_prices). Fix: ensure trace_id propagates from root Langfuse span to every agent's CallbackHandler kwargs.", { x:0.6, y:4.62, w:12.15, h:0.82, fontSize:9.5, color:C.slate, fontFace:"Calibri", margin:0 });

  // Tools
  const tools = [
    { t:"OpenTelemetry", d:"OTLP export · configurable\nendpoint · span-level tracing",   color:"0891B2" },
    { t:"Structlog",     d:"JSON structured logs\ncorrelation IDs per session",            color:C.emerald },
    { t:"Locust",        d:"Load test suite\nbackend/tests/locustfile.py",                 color:C.amber },
    { t:"User Tracking", d:"localStorage UUID →\nX-User-ID header → Langfuse",           color:C.purple },
  ];
  tools.forEach((t, i) => {
    const tx = 0.4 + i * 3.12;
    s.addShape(pres.shapes.RECTANGLE, { x:tx, y:5.72, w:2.95, h:1.52, fill:{color:"111827"}, line:{color:t.color, width:1} });
    s.addShape(pres.shapes.RECTANGLE, { x:tx, y:5.72, w:2.95, h:0.07, fill:{color:t.color}, line:{color:t.color} });
    s.addText(t.t, { x:tx+0.12, y:5.84, w:2.71, h:0.36, fontSize:12, bold:true, color:C.white, fontFace:"Calibri", margin:0 });
    s.addText(t.d, { x:tx+0.12, y:6.24, w:2.71, h:0.9,  fontSize:9.5, color:C.slate, fontFace:"Calibri", margin:0 });
  });
}

// ════════════════════════════════════════════════════════════════════════════
// SLIDE 12 — TECH STACK
// ════════════════════════════════════════════════════════════════════════════
{
  let s = pres.addSlide();
  s.background = { color: C.darkBg };
  hdrBar(s, "Tech Stack", "Every technology choice across orchestration, backend, frontend, AI, search, auth, collaboration, infra, and observability");

  const stack = [
    { cat:"Orchestration", items:["LangGraph StateGraph","LangChain callbacks","asyncio concurrent agents","Pydantic TypedDict state"],               color:C.indigo  },
    { cat:"Backend",       items:["FastAPI + Uvicorn","Pydantic v2 settings","slowapi rate limiting","SSE streaming + heartbeat"],                    color:"059669"  },
    { cat:"Frontend",      items:["Next.js 15 App Router","Three.js WebGL aurora","Tailwind CSS 3","Framer Motion"],                                 color:"18181B"  },
    { cat:"AI / LLM",      items:["OpenAI GPT-4o","text-embedding-3-small","NumPy / SciPy physics","FreeCAD headless CAD"],                          color:"10A37F"  },
    { cat:"Search",        items:["ChromaDB vector store","rank-bm25 BM25 index","RRF fusion (k=60)","Engineering tokeniser"],                       color:C.amber   },
    { cat:"Auth",          items:["bcrypt (passlib)","HS256 JWT (python-jose)","Random refresh tokens","Next.js middleware guard"],                   color:C.purple  },
    { cat:"Collab",        items:["Slack Block Kit webhook","Teams Adaptive Cards","SMTP email (aiosmtplib)","Redis review store"],                   color:"4A154B"  },
    { cat:"Infra",         items:["Docker Compose (dev)","Kubernetes HPA/PDB","Terraform AWS+GCP+Azure","kube-prometheus-stack"],                    color:"326CE5"  },
    { cat:"Observability", items:["Langfuse v3.7 tracing","OpenTelemetry OTLP","Structlog JSON logs","Locust load tests"],                           color:C.purple  },
  ];

  stack.forEach((item, i) => {
    const col = i % 3, row = Math.floor(i / 3);
    const x = 0.4 + col * 4.25, y = 1.1 + row * 1.9;
    s.addShape(pres.shapes.RECTANGLE, { x, y, w:4.05, h:1.75, fill:{color:"111827"}, line:{color:item.color, width:1} });
    s.addShape(pres.shapes.RECTANGLE, { x, y, w:0.07, h:1.75, fill:{color:item.color}, line:{color:item.color} });
    s.addText(item.cat, { x:x+0.18, y:y+0.09, w:3.75, h:0.38, fontSize:12.5, bold:true, color:C.white, fontFace:"Calibri", margin:0 });
    s.addText(item.items.join("\n"), { x:x+0.18, y:y+0.52, w:3.75, h:1.12, fontSize:9.5, color:C.slate, fontFace:"Calibri", margin:0 });
  });
}

// ════════════════════════════════════════════════════════════════════════════
// SLIDE 13 — CLOUD COSTS & SCALABILITY
// ════════════════════════════════════════════════════════════════════════════
{
  let s = pres.addSlide();
  s.background = { color: C.lightBg };
  hdrBar(s, "Cloud Costs & Scalability", "Monthly cost comparison and Kubernetes horizontal scaling configuration");

  s.addText("Monthly Cost Comparison", { x:0.4, y:1.1, w:6, h:0.42, fontSize:15, bold:true, color:C.textDark, fontFace:"Calibri", margin:0 });
  const clouds = [
    { name:"GCP  (GKE Autopilot)", cost:590, color:C.gcpBlu, note:"Most cost-efficient — pay-per-pod", pct:78.7 },
    { name:"AWS  (EKS 1.29)",      cost:700, color:C.awsOrg, note:"Broadest ecosystem + managed services", pct:93.3 },
    { name:"Azure  (AKS 1.29)",    cost:750, color:C.azrBlu, note:"Zone-redundant — premium HA",          pct:100  },
  ];
  clouds.forEach((c, i) => {
    const y = 1.65 + i * 1.22;
    s.addText(c.name, { x:0.4, y, w:3.5, h:0.42, fontSize:13, bold:true, color:C.textDark, fontFace:"Calibri", margin:0 });
    s.addText(c.note, { x:0.4, y:y+0.44, w:3.5, h:0.28, fontSize:9, color:C.textMid, fontFace:"Calibri", margin:0 });
    s.addShape(pres.shapes.RECTANGLE, { x:3.95, y:y+0.08, w:5.0, h:0.35, fill:{color:C.gray}, line:{color:C.gray} });
    s.addShape(pres.shapes.RECTANGLE, { x:3.95, y:y+0.08, w:5.0*c.pct/100, h:0.35, fill:{color:c.color}, line:{color:c.color} });
    s.addText("$"+c.cost+"/mo", { x:9.1, y:y+0.08, w:1.3, h:0.35, fontSize:14, bold:true, color:c.color, fontFace:"Calibri", valign:"middle", margin:0 });
  });

  s.addText("Kubernetes Scalability", { x:0.4, y:4.45, w:6, h:0.42, fontSize:15, bold:true, color:C.textDark, fontFace:"Calibri", margin:0 });
  const tableData = [
    [
      { text:"Component",     options:{bold:true, fill:{color:C.indigo}, color:"FFFFFF", fontFace:"Calibri"} },
      { text:"Min Pods",      options:{bold:true, fill:{color:C.indigo}, color:"FFFFFF", fontFace:"Calibri"} },
      { text:"Max Pods",      options:{bold:true, fill:{color:C.indigo}, color:"FFFFFF", fontFace:"Calibri"} },
      { text:"Scale Triggers",options:{bold:true, fill:{color:C.indigo}, color:"FFFFFF", fontFace:"Calibri"} },
      { text:"PDB",           options:{bold:true, fill:{color:C.indigo}, color:"FFFFFF", fontFace:"Calibri"} },
    ],
    ["Backend (FastAPI)",  "3", "20", "CPU >65%  |  Mem >75%  |  pipeline_sessions custom metric", "minAvailable: 2"],
    ["Frontend (Next.js)", "2", "10", "CPU >65%  |  Mem >70%",                                       "minAvailable: 1"],
    ["Redis StatefulSet",  "1", "1",  "Manual — StatefulSet (no HPA)",                               "—"],
    ["ChromaDB StatefulSet","1","1",  "Manual — StatefulSet (no HPA)",                               "—"],
  ];
  s.addTable(tableData, { x:0.4, y:4.92, w:12.55, h:2.4, border:{pt:0.5, color:C.gray}, fill:{color:"FFFFFF"}, fontFace:"Calibri", fontSize:10.5, colW:[2.6,1.0,1.0,5.7,2.25] });
}

// ════════════════════════════════════════════════════════════════════════════
// SLIDE 14 — SUMMARY / WHY NEXUS
// ════════════════════════════════════════════════════════════════════════════
{
  let s = pres.addSlide();
  s.background = { color: C.darkBg };
  s.addShape(pres.shapes.RECTANGLE, { x:0, y:0, w:0.45, h:7.5, fill:{color:C.indigo}, line:{color:C.indigo} });
  s.addText("Why NEXUS?", { x:0.75, y:0.45, w:11, h:0.7, fontSize:38, bold:true, color:C.white, fontFace:"Calibri", margin:0 });
  s.addShape(pres.shapes.RECTANGLE, { x:0.75, y:1.22, w:9, h:0.04, fill:{color:C.indigo}, line:{color:C.indigo} });
  s.addText("Demonstrates every capability expected of a Senior AI Engineer — Agentic Platform Lead", { x:0.75, y:1.32, w:12.2, h:0.38, fontSize:13, color:C.slate, fontFace:"Calibri", margin:0 });

  const pts = [
    { icon:"🤖", t:"Agentic Systems",      d:"LangGraph DAG, 6 specialist agents, provenance chain, SSE real-time streaming — not a toy chatbot or RAG wrapper" },
    { icon:"🔍", t:"Production RAG",       d:"Hybrid BM25 + vector search with RRF, engineering-aware tokeniser, in-memory index rebuilt from ChromaDB on every startup" },
    { icon:"🔐", t:"Security-First",       d:"JWT auth, bcrypt, refresh token rotation, rate limiting, CSP/HSTS headers, prompt injection guard, WAFv2 at infra layer" },
    { icon:"☁️", t:"Multi-Cloud IaC",      d:"Terraform + Kubernetes for AWS EKS, GCP GKE Autopilot, Azure AKS — HPA, PDB, TopologySpread, HA Redis, KMS encryption" },
    { icon:"👥", t:"Team Tooling",         d:"Slack + Teams + Email webhooks, ReviewPanel with vote aggregation (Approve/Changes/Reject), channel notification on each vote" },
    { icon:"📊", t:"Observability",        d:"Langfuse root + 6 agent spans, OpenTelemetry OTLP, Structlog JSON, user-level tracking via localStorage UUID, Locust load tests" },
  ];
  pts.forEach((p, i) => {
    const col = i % 2, row = Math.floor(i / 2);
    const x = 0.75 + col * 6.2, y = 1.88 + row * 1.44;
    s.addShape(pres.shapes.RECTANGLE, { x, y, w:5.9, h:1.3, fill:{color:"111827"}, line:{color:"1E293B"} });
    s.addText(p.icon+"  "+p.t, { x:x+0.15, y:y+0.1, w:5.6, h:0.38, fontSize:13, bold:true, color:C.white, fontFace:"Calibri", margin:0 });
    s.addText(p.d, { x:x+0.15, y:y+0.52, w:5.6, h:0.68, fontSize:10, color:C.slate, fontFace:"Calibri", margin:0 });
  });

  s.addShape(pres.shapes.RECTANGLE, { x:0.75, y:6.72, w:12.2, h:0.58, fill:{color:C.indigo}, line:{color:C.indigo} });
  s.addText("github.com/bolajil/nexus-agentic-platform  ·  Backend :8003  ·  Frontend :3002  ·  Docs: infra/DEPLOYMENT.md", { x:0.75, y:6.72, w:12.2, h:0.58, fontSize:11, color:C.white, align:"center", valign:"middle", fontFace:"Calibri", margin:0 });
}

// ── Write ──────────────────────────────────────────────────────────────────
pres.writeFile({ fileName: "C:/Users/bolaf/Desktop/NEXUS_Platform_Presentation.pptx" })
  .then(() => console.log("✅  NEXUS_Platform_Presentation.pptx saved to Desktop"))
  .catch(err => console.error("❌  Error:", err));
