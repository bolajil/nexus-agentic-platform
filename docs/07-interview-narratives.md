# 07 — Interview Narratives (STAR Format)

## Role: Senior AI Engineer – Agentic Platform Lead

---

## Q1: Describe how you architected a scalable multi-agent platform

**Situation:** Needed to automate end-to-end hardware design: requirements parsing,
research retrieval, design calculation, physics simulation, optimization, and reporting.

**Task:** Build a platform where AI agents autonomously route complex engineering
briefs through a deterministic, auditable pipeline.

**Action:**
- Chose **LangGraph StateGraph** over a single ReAct loop to give each agent
  bounded scope, independent testability, and conditional error routing
- Designed **AgentState TypedDict** as the shared memory contract — each agent
  declares only the keys it reads/writes
- Added **SSE streaming** via asyncio Queues so every agent_start/complete/tool_call
  event reaches the browser in real-time without polling
- Persisted state to **Redis after each node** so partial results survive crashes
- Built **provenance chain** (confidence, duration, tools used) into every state update

**Result:** A 6-agent pipeline that can take "Design a 100W heat sink" to a full
engineering report with design parameters, simulation results, and Pareto-optimal
recommendations — fully auditable, resumable, and streamed live to the UI.

---

## Q2: How do you handle agent failures in production?

**Situation:** A simulation agent occasionally times out on complex geometries.

**Task:** Prevent one slow agent from blocking the entire pipeline or losing work.

**Action:**
- Conditional edges in LangGraph: `if state.get("error"): return END`
- Each agent wraps its logic in try/except and sets `state["error"]` on failure
- State is persisted to Redis before and after each node — restart resumes from
  last checkpoint
- Tenacity retry decorator on LLM calls with exponential backoff
- Each agent has a configurable timeout via `asyncio.wait_for()`

**Result:** Agent failures degrade gracefully — partial results are preserved,
the error is surfaced in the UI with the exact agent and provenance context,
and retry logic handles transient API failures invisibly.

---

## Q3: Explain your approach to knowledge retrieval in engineering contexts

**Situation:** LLMs alone hallucinate engineering formulas. We needed agents
grounded in accurate physics.

**Task:** Build a RAG system with authoritative engineering reference material.

**Action:**
- Seeded **ChromaDB** with curated engineering documents: Newton's Law of Cooling,
  Fourier conduction, fin efficiency equations, Tsiolkovsky rocket equation,
  Von Mises yield criterion, Nusselt number correlations
- Used **text-embedding-3-small** for dense retrieval
- Research Agent queries with the engineering brief + domain filter for top-5 chunks
- Injected retrieved chunks directly into the Design Agent's system prompt as
  grounding context: "Use the following reference material for calculations..."

**Result:** Design agents produce physically plausible outputs with cited equations
rather than hallucinated numbers. Knowledge base is extensible — add a document,
it's available to all agents immediately.

---

## Q4: Describe your observability approach for a distributed agent system

**Situation:** With 6 agents, an LLM, a vector DB, and Redis all in the pipeline,
debugging failures requires end-to-end tracing.

**Task:** Implement production-grade observability without instrumenting every line.

**Action:**
- **structlog** for JSON-structured logs with session_id, agent_name, trace_id
- **OpenTelemetry** auto-instrumentation on FastAPI for request traces
- Custom OTEL spans around each agent boundary with attributes: agent_name,
  token_usage, confidence_score, duration_ms
- **Provenance chain** in the session data as application-level audit log
- `/health` (liveness) and `/ready` (checks Redis + OpenAI key) endpoints
- `X-Process-Time-Ms` header on every response for latency tracking

**Result:** When an agent produces unexpected output, I can correlate the OTEL
trace to the session provenance chain, see exactly which tool was called,
what context was retrieved, and how long each step took.

---

## Q5: How would you scale this to handle 100 concurrent engineering sessions?

**Answer:**

"The current architecture already supports horizontal scaling because:

1. **Stateless FastAPI workers** — session state lives in Redis, not in-process memory.
   Add workers with `--workers N` or scale the Docker service.

2. **Isolated asyncio tasks** — each session is an independent `create_task()` with
   its own SSEQueue. Tasks don't share state; they can't interfere.

3. **Redis pub/sub for cross-instance SSE** — if multiple FastAPI instances are behind
   a load balancer, a client may connect to a different instance than the one running
   the pipeline. Fix: publish events to a Redis channel, subscribe in the SSE route.

4. **ChromaDB read replicas** — vector search is read-heavy. Add read replicas and
   route Research Agent queries through a connection pool.

5. **LangGraph distributed execution** — LangGraph supports distributed task
   execution where each node can run on a separate worker. For computationally
   heavy simulation nodes, route to a dedicated GPU/compute pool.

6. **Rate limiting** — wrap LLM calls with a token bucket rate limiter (slowapi)
   to prevent runaway API costs during load spikes."

---

## Closing Statement

"NEXUS demonstrates the core capabilities this role requires: multi-agent
orchestration, distributed system design, LLM integration with grounding,
full provenance for explainability, and production observability. I built it
specifically to show how these patterns apply to autonomous engineering workflows —
the same architecture that compresses a heat sink design from hours to seconds
applies directly to the hardware development cycles you're trying to accelerate."
