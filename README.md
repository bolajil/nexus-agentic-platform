# NEXUS — Multi-Agent Agentic Engineering Platform

> **Production-grade AI platform that autonomously routes engineering briefs through a 6-agent LangGraph pipeline — from requirements parsing to fully compiled engineering reports.**

Built as a portfolio showcase for the **Senior AI Engineer – Agentic Platform Lead** role at a defense and space technology organisation. Every architectural decision maps directly to the role's requirements: multi-agent orchestration, distributed systems, LLM integration, memory and provenance, observability, and physics-grounded simulation.

---

## Live Demo

| Service | URL | Description |
|---|---|---|
| Frontend | `http://localhost:3002` | Mission Control UI |
| Backend API | `http://localhost:8003/docs` | FastAPI Swagger docs |
| Health | `http://localhost:8003/health` | Liveness probe |
| Readiness | `http://localhost:8003/ready` | Redis + API key check |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                       NEXUS Platform                            │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Next.js 15 Frontend (port 3002)            │   │
│  │  Mission Control · Sessions · Knowledge · Provenance    │   │
│  └────────────────────┬────────────────────────────────────┘   │
│                       │  SSE streaming / REST API              │
│  ┌────────────────────▼────────────────────────────────────┐   │
│  │            FastAPI Backend (port 8003)                  │   │
│  │                                                         │   │
│  │   ┌─────────────────────────────────────────────────┐  │   │
│  │   │         NEXUSOrchestrator (LangGraph)           │  │   │
│  │   │                                                 │  │   │
│  │   │  START                                          │  │   │
│  │   │    │                                            │  │   │
│  │   │    ▼                                            │  │   │
│  │   │  📋 RequirementsAgent  ─── GPT-4o parse        │  │   │
│  │   │    │                                            │  │   │
│  │   │    ▼                                            │  │   │
│  │   │  🔬 ResearchAgent      ─── ChromaDB RAG        │  │   │
│  │   │    │                                            │  │   │
│  │   │    ▼                                            │  │   │
│  │   │  📐 DesignAgent        ─── Physics equations   │  │   │
│  │   │    │                                            │  │   │
│  │   │    ▼                                            │  │   │
│  │   │  ⚡ SimulationAgent    ─── NumPy/SciPy solvers │  │   │
│  │   │    │                                            │  │   │
│  │   │    ▼                                            │  │   │
│  │   │  🎯 OptimizationAgent  ─── Pareto sweep        │  │   │
│  │   │    │                                            │  │   │
│  │   │    ▼                                            │  │   │
│  │   │  📄 ReportAgent        ─── GPT-4o compile      │  │   │
│  │   │    │                                            │  │   │
│  │   │   END                                           │  │   │
│  │   └─────────────────────────────────────────────────┘  │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌──────────────┐   ┌────────────────────────────────────┐    │
│  │  Redis 7     │   │  ChromaDB 0.5                      │    │
│  │  port 6379   │   │  port 8004 (external)              │    │
│  │  Session TTL │   │  Engineering knowledge base        │    │
│  │  7 days      │   │  text-embedding-3-small            │    │
│  └──────────────┘   └────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Technology Stack

### Backend
| Technology | Version | Role |
|---|---|---|
| **FastAPI** | 0.115 | Async REST API + SSE streaming |
| **LangGraph** | 0.2.56 | Multi-agent StateGraph orchestration |
| **LangChain** | 0.3.10 | LLM abstractions + tool calling |
| **OpenAI GPT-4o** | — | Requirements parsing + report generation |
| **OpenAI GPT-4o-mini** | — | Fast domain-specific agent reasoning |
| **ChromaDB** | 0.5.23 | Vector knowledge base (RAG) |
| **Redis** | 7 | Session persistence (7-day TTL) |
| **NumPy + SciPy** | 2.x / 1.14 | Physics simulation + optimisation |
| **structlog** | 24.4 | Structured JSON logging |
| **OpenTelemetry** | 1.28 | Distributed tracing (OTLP) |
| **Pydantic v2** | 2.10 | Request/response validation + typed agent state |

### Frontend
| Technology | Version | Role |
|---|---|---|
| **Next.js 15** | 15.1 | App Router, server components, API proxy routes |
| **React 19** | 19.0 | UI components |
| **Tailwind CSS** | 3.4 | Utility-first dark design system |
| **Framer Motion** | 12.0 | Agent pipeline animations + transitions |
| **TypeScript** | 5.7 | End-to-end type safety |

### Infrastructure
| Service | Purpose |
|---|---|
| Docker Compose | Orchestrates all 4 services |
| Multi-stage Dockerfiles | Slim production images, non-root execution |
| Redis | Session state store with in-memory fallback |
| ChromaDB | Persistent vector store with ephemeral fallback |

---

## Quick Start

### Prerequisites
- Docker Desktop installed and running
- OpenAI API key (`sk-...`)

### 1 — Configure environment

```bash
cd nexus-agentic-platform
cp .env.example .env
```

Edit `.env` and set your key:
```env
OPENAI_API_KEY=sk-...your-key-here...
```

### 2 — Start all services

```bash
docker compose up --build
```

This starts:
- **Redis** → session store
- **ChromaDB** → vector knowledge base (auto-seeded on first run)
- **NEXUS backend** → FastAPI + LangGraph pipeline
- **NEXUS frontend** → Next.js UI

### 3 — Open the platform

```
http://localhost:3002
```

### 4 — Submit your first brief

Try one of these in the Mission Control input:

> *"Design a heat sink for a 100W power module. Operating environment: 25°C ambient, forced air at 3 m/s. Maximum component temperature: 85°C. Material: aluminum. Target thermal resistance < 0.6 °C/W."*

> *"Design a cold gas thruster for a 3U CubeSat attitude control system. Required thrust: 50 mN. Propellant: nitrogen. Available pressure: 300 bar. Target delta-v: 10 m/s."*

> *"Structural analysis of an aluminum 6061-T6 bracket subjected to 500N axial load and 50 N·m bending moment. Safety factor target: 2.5. Minimise mass."*

Watch the 6 agents execute in real-time via Server-Sent Events.

---

## Project Structure

```
nexus-agentic-platform/
│
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   │   ├── orchestrator.py        # LangGraph StateGraph + SSEQueue
│   │   │   ├── requirements_agent.py  # GPT-4o: parse brief → structured requirements
│   │   │   ├── research_agent.py      # ChromaDB RAG: retrieve relevant engineering refs
│   │   │   ├── design_agent.py        # Physics equations: calculate design parameters
│   │   │   ├── simulation_agent.py    # NumPy/SciPy: domain simulation engine
│   │   │   ├── optimization_agent.py  # Multi-objective Pareto optimisation
│   │   │   └── report_agent.py        # GPT-4o: compile full engineering report
│   │   │
│   │   ├── core/
│   │   │   ├── config.py              # Pydantic-settings environment config
│   │   │   ├── logging_setup.py       # structlog JSON structured logging
│   │   │   └── telemetry.py           # OpenTelemetry OTLP tracing setup
│   │   │
│   │   ├── memory/
│   │   │   ├── session_store.py       # Redis session store (in-memory fallback)
│   │   │   └── vector_store.py        # ChromaDB vector store manager
│   │   │
│   │   ├── models/
│   │   │   └── schemas.py             # Pydantic v2 models (all domain types)
│   │   │
│   │   ├── routers/
│   │   │   ├── health.py              # GET /health, GET /ready
│   │   │   ├── sessions.py            # POST/GET/DELETE /api/v1/sessions
│   │   │   └── knowledge.py           # GET/POST /api/v1/knowledge
│   │   │
│   │   ├── tools/
│   │   │   ├── simulation_tool.py     # Physics simulation tool (LangChain tool)
│   │   │   ├── calculator_tool.py     # Engineering calculations
│   │   │   └── rag_tool.py            # ChromaDB retrieval tool
│   │   │
│   │   └── main.py                    # FastAPI app: lifespan, CORS, routers
│   │
│   ├── scripts/
│   │   └── seed_knowledge_base.py     # Engineering KB seeder (8 reference docs)
│   │
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
│
├── frontend/
│   ├── app/
│   │   ├── page.tsx                   # Mission Control (SSE pipeline, agent cards)
│   │   ├── sessions/
│   │   │   ├── page.tsx               # Session list view
│   │   │   └── [id]/page.tsx          # Session detail: overview/provenance/raw tabs
│   │   ├── knowledge/page.tsx         # KB search + stats + seed trigger
│   │   ├── provenance/page.tsx        # Audit trail timeline viewer
│   │   ├── docs/page.tsx              # Architecture guide + interview prep
│   │   │
│   │   ├── components/
│   │   │   ├── Sidebar.tsx            # Animated navigation with active state
│   │   │   ├── AgentPipeline.tsx      # Live agent status cards with SSE updates
│   │   │   └── ProvenanceChain.tsx    # Timeline component for audit entries
│   │   │
│   │   ├── api/
│   │   │   ├── sessions/route.ts      # SSE proxy POST, list GET
│   │   │   ├── sessions/[id]/route.ts # Session detail + delete
│   │   │   └── knowledge/route.ts     # KB search + stats proxy
│   │   │
│   │   ├── globals.css                # Dark design tokens, glass-card, glow effects
│   │   └── layout.tsx
│   │
│   ├── package.json
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   └── Dockerfile
│
├── docs/
│   ├── 00-README.md                   # Platform overview + quick start
│   ├── 01-multi-agent-orchestration.md # LangGraph, StateGraph, SSE patterns
│   └── 07-interview-narratives.md     # STAR-format interview answers
│
├── docker-compose.yml                 # 4-service stack
├── .env.example
└── README.md
```

---

## Agent Pipeline — Deep Dive

### Agent 1: Requirements Engineer
**Model:** GPT-4o
**Input:** Raw engineering brief (free text)
**Output:** `EngineeringRequirements` (domain, objectives, constraints, performance targets, materials, operating conditions)
**How:** Structured extraction prompt with Pydantic output parser. Detects domain automatically: `heat_transfer`, `propulsion`, `structural`, `electronics_cooling`.

### Agent 2: Research Scientist
**Model:** ChromaDB semantic search + GPT-4o-mini synthesis
**Input:** `EngineeringRequirements`
**Output:** `ResearchResult` (relevant formulas, recommended approaches, references)
**How:** Embeds the engineering brief using `text-embedding-3-small`, queries ChromaDB for top-5 matching documents, synthesises into actionable research findings grounded in real physics.

### Agent 3: Design Engineer
**Model:** GPT-4o-mini + physics calculator tool
**Input:** Requirements + Research findings
**Output:** `DesignParameters` (primary params, secondary params, units, equations used, assumptions, feasibility)
**How:** Uses retrieved formulas from Research Agent as grounding. Applies domain equations:
- Heat transfer: `Q = h·A·ΔT`, fin efficiency `η = tanh(mL)/(mL)`
- Propulsion: `Δv = Isp·g₀·ln(m₀/mf)`, nozzle area-Mach relation
- Structural: `σ = F/A`, Von Mises criterion, safety factor `n = Sy/σ`

### Agent 4: Physics Simulator
**Model:** NumPy/SciPy (deterministic) + GPT-4o-mini interpretation
**Input:** `DesignParameters`
**Output:** `SimulationResult` (output metrics, `performance_score` 0–1, warnings, raw data)
**How:** Runs domain-specific physics solvers entirely in Python — no external simulation software required. Produces quantitative results: thermal resistance, thrust, stress, efficiency scores.

### Agent 5: Optimisation Engineer
**Model:** SciPy optimise + GPT-4o-mini
**Input:** `SimulationResult` + `DesignParameters`
**Output:** `OptimizedParameters` (original vs optimised params, improvement metrics, Pareto front, recommendation)
**How:** Multi-objective optimisation sweeping the parameter space. Returns the Pareto-optimal solution and quantifies the improvement over the initial design.

### Agent 6: Technical Writer
**Model:** GPT-4o
**Input:** All prior agent outputs
**Output:** `EngineeringReport` (executive summary, design solution, simulation results, optimisation results, conclusions, recommendations)
**How:** Compiles a structured engineering report suitable for stakeholder review. Every number traces back to a simulation or calculation — no hallucinated values.

---

## State & Provenance

### AgentState (TypedDict)

```python
class AgentState(TypedDict, total=False):
    session_id:          str
    engineering_brief:   str
    current_agent:       str
    error:               str | None
    requirements:        dict   # populated by RequirementsAgent
    research_results:    dict   # populated by ResearchAgent
    design_params:       dict   # populated by DesignAgent
    simulation_results:  dict   # populated by SimulationAgent
    optimized_params:    dict   # populated by OptimizationAgent
    report:              dict   # populated by ReportAgent
    provenance_chain:    list[ProvenanceEntry]
    messages:            list   # LangChain message history
```

### ProvenanceEntry (per agent)

```python
{
  "agent_name":      "design",
  "timestamp":       "2026-03-19T14:23:11.402Z",
  "input_summary":   "domain=heat_transfer, constraints=[T_max=85°C, ...]",
  "output_summary":  "h=45.2 W/m²K, η_fin=0.87, R_total=0.52°C/W",
  "tools_used":      ["physics_calculator", "fin_efficiency_calculator"],
  "confidence_score": 0.91,
  "duration_ms":     1243.5,
  "token_usage":     {"prompt": 842, "completion": 318}
}
```

Every session accumulates 6 provenance entries — a complete, ordered audit trail visible in the Provenance page.

---

## SSE Streaming Protocol

The frontend connects to `POST /api/v1/sessions` and receives a stream of events:

```
data: {"type":"agent_start","agent":"requirements","label":"Requirements Engineer","content":"Parsing engineering brief..."}

data: {"type":"agent_complete","agent":"requirements","content":{"output_summary":"domain=heat_transfer...","confidence_score":0.94,"duration_ms":1821,"tools_used":[]}}

data: {"type":"agent_start","agent":"research","label":"Research Scientist","content":"Querying engineering knowledge base..."}

... (4 more agent pairs)

data: {"type":"session_complete","session_id":"abc123","content":{"status":"complete","report_title":"Heat Sink Design Report"}}
```

The `SSEQueue` is an `asyncio.Queue` bridging the background pipeline task to the HTTP response. The pipeline and the SSE stream are fully decoupled — the pipeline runs at its own pace and the queue buffers events between producer and consumer.

---

## Knowledge Base

The Research Agent searches 8 built-in engineering reference documents across 4 domains:

| Domain | Documents |
|---|---|
| **Heat Transfer** | Newton's Law of Cooling, Fourier Conduction, Fin Efficiency, Thermal Resistance Networks |
| **Propulsion** | Tsiolkovsky Rocket Equation, De Laval Nozzle Theory |
| **Structural** | Stress/Strain/Safety Factors, Von Mises Criterion |
| **Electronics Cooling** | Forced Convection & Airflow, Heat Pipe Technology |

Add custom documents via the Knowledge Base page or the API:

```bash
curl -X POST http://localhost:8003/api/v1/knowledge/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Radiative Heat Transfer — Stefan-Boltzmann Law",
    "domain": "heat_transfer",
    "content": "Q_rad = ε·σ·A·(T_s⁴ - T_surr⁴)...",
    "source": "Incropera - Fundamentals of Heat and Mass Transfer"
  }'
```

---

## API Reference

### Sessions

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/sessions` | Create session + stream pipeline (SSE) |
| `GET` | `/api/v1/sessions` | List all sessions |
| `GET` | `/api/v1/sessions/{id}` | Get full session with all agent outputs |
| `DELETE` | `/api/v1/sessions/{id}` | Delete session |
| `GET` | `/api/v1/sessions/{id}/provenance` | Get provenance chain only |

### Knowledge

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/knowledge/stats` | Collection statistics |
| `POST` | `/api/v1/knowledge/search?query=...` | Semantic search |
| `POST` | `/api/v1/knowledge/ingest` | Add a document |
| `POST` | `/api/v1/knowledge/seed` | Seed built-in engineering docs |

### Health

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Liveness — always returns 200 if process is alive |
| `GET` | `/ready` | Readiness — checks Redis connectivity + OpenAI key |

---

## Running Without Docker

### Backend

```bash
cd backend

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate        # Linux/macOS
# or: venv\Scripts\activate      # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env — add OPENAI_API_KEY

# Start server
uvicorn app.main:app --host 0.0.0.0 --port 8003 --reload
```

### Frontend

```bash
cd frontend

npm install
npm run dev        # starts on http://localhost:3002
```

### Seed knowledge base

```bash
cd backend
python scripts/seed_knowledge_base.py
```

---

## Port Reference

| Service | Local Port | Notes |
|---|---|---|
| NEXUS Frontend | **3002** | Next.js dev server |
| NEXUS Backend | **8003** | FastAPI + LangGraph |
| Redis | **6379** | Session store |
| ChromaDB | **8004** | Vector DB (maps to 8000 inside container) |

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `OPENAI_API_KEY` | ✅ Yes | — | GPT-4o API access |
| `REDIS_URL` | No | `redis://localhost:6379` | Session store URL |
| `CHROMA_HOST` | No | `localhost` | ChromaDB host |
| `CHROMA_PORT` | No | `8000` | ChromaDB port (internal) |
| `CORS_ORIGINS` | No | `["http://localhost:3002"]` | Allowed CORS origins |
| `APP_ENV` | No | `development` | Environment label |
| `LOG_LEVEL` | No | `INFO` | Logging verbosity |
| `OTLP_ENDPOINT` | No | `http://localhost:4317` | OpenTelemetry collector |

---

## Observability

### Structured Logging (structlog)
Every log line is JSON with `session_id`, `agent_name`, and `trace_id`:
```json
{"level":"info","agent":"design","session_id":"abc123","duration_ms":1243,"event":"agent_complete"}
```

### OpenTelemetry Tracing
- FastAPI auto-instrumentation captures every request as a span
- Custom spans wrap each agent node with `agent_name`, `confidence_score`, `token_usage` attributes
- Compatible with Jaeger, Grafana Tempo, AWS X-Ray via OTLP exporter

### Health Endpoints
```bash
curl http://localhost:8003/health   # → {"status":"healthy","timestamp":"..."}
curl http://localhost:8003/ready    # → {"status":"ready","checks":{"redis":true,"openai_configured":true}}
```

---

## Key Design Decisions

### Why LangGraph over a single ReAct agent?
A single agent controlling the full pipeline becomes a monolith. LangGraph gives each agent bounded responsibility, independent testability, and conditional error routing. If the Simulation Agent fails, state is preserved and the error surfaces cleanly rather than cascading.

### Why SSE over WebSockets?
SSE is unidirectional (server → client), simpler to implement, and natively supported by every browser and reverse proxy. WebSockets would require a handshake protocol for what is fundamentally a read-only event stream. SSE also reconnects automatically.

### Why Redis with in-memory fallback?
The platform is usable without Redis — the in-memory fallback ensures a developer can `pip install` and `uvicorn` with zero infrastructure. In production, Redis provides 7-day session persistence, cross-instance state sharing behind a load balancer, and fast key-pattern queries for session listing.

### Why ChromaDB with ephemeral fallback?
Same philosophy as Redis. The vector store starts in-memory if ChromaDB is not reachable. Knowledge base seeding runs automatically on first startup so the Research Agent always has grounding material.

---

## Interview Context

This platform was built to demonstrate production-grade AI engineering for a **Senior AI Engineer – Agentic Platform Lead** role in the defense and space technology sector.

### Skills demonstrated

| Job Requirement | Platform Evidence |
|---|---|
| Multi-agent orchestration | LangGraph StateGraph, 6 specialist agents, conditional routing |
| Distributed systems | Redis session persistence, async pipeline, horizontal-scale design |
| LLM integration | GPT-4o / GPT-4o-mini, tool calling, structured output parsing |
| Memory, context, provenance | ChromaDB RAG, 7-entry provenance chain, full audit trail |
| Observability | structlog JSON, OpenTelemetry OTLP, health/ready probes |
| Physics simulation | NumPy/SciPy domain solvers (thermal, propulsion, structural) |
| Secure execution | Non-root Docker, per-session isolated state, typed agent boundaries |
| Real-time systems | SSE streaming, asyncio task concurrency, SSEQueue bridge |
| Documentation | 7 architecture guide files + inline code comments at every decision |

### Architecture Guide
See the [docs/](docs/) directory for deep-dive notes on each architectural pillar, or visit the **Architecture** page in the UI at `http://localhost:3002/docs`.

---

## Author

**Lanre Bolaji**
Senior AI Engineer · Full-Stack Developer
[GitHub: bolajil](https://github.com/bolajil)

---

*Built with FastAPI · LangGraph · Next.js 15 · ChromaDB · Redis · Docker*
