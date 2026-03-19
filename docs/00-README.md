# NEXUS Platform — Knowledge Base

> **Purpose:** Interview preparation and deep-dive reference for the
> **Senior AI Engineer – Agentic Platform Lead** role at a defense/space technology org.

---

## What This Platform Demonstrates

| Requirement | NEXUS Implementation |
|---|---|
| Multi-agent orchestration | LangGraph `StateGraph` with 6 specialist agents |
| Scalable distributed systems | FastAPI + Redis session store + async pipeline |
| LLM integration & agent frameworks | LangChain + LangGraph + GPT-4o |
| Memory, context, provenance | ChromaDB RAG + full `ProvenanceEntry` audit chain |
| Observability | structlog + OpenTelemetry + `/health` + `/ready` |
| Real-time streaming | Server-Sent Events (SSE) via `asyncio.Queue` |
| Physics simulation | NumPy/SciPy domain-specific engineering solvers |
| Secure execution | Containerised, non-root, isolated per-session state |

---

## Guide Structure

| File | Topic |
|---|---|
| [01-multi-agent-orchestration.md](01-multi-agent-orchestration.md) | LangGraph, StateGraph, AgentState |
| [02-distributed-systems.md](02-distributed-systems.md) | Redis, session persistence, concurrency |
| [03-llm-rag-knowledge.md](03-llm-rag-knowledge.md) | ChromaDB, embeddings, RAG pipeline |
| [04-observability-performance.md](04-observability-performance.md) | OTEL, structlog, metrics, SSE |
| [05-secure-execution.md](05-secure-execution.md) | Docker, provenance, sandboxing |
| [06-engineering-tools.md](06-engineering-tools.md) | Simulation, physics, optimization |
| [07-interview-narratives.md](07-interview-narratives.md) | STAR answers, talking points |

---

## Quick Start

```bash
# 1. Copy environment file
cp .env.example .env
# → Add your OPENAI_API_KEY

# 2. Start all services
docker compose up --build

# 3. Open the UI
open http://localhost:3002

# 4. Backend API docs
open http://localhost:8003/docs
```

---

## Architecture Diagram

```
┌──────────────────────────────────────────────────────────┐
│                    NEXUS Platform                         │
│                                                           │
│  Browser (Next.js 15)                                     │
│  ├── Mission Control    → POST /api/sessions  (SSE)       │
│  ├── Sessions           → GET  /api/sessions              │
│  ├── Provenance         → GET  /api/sessions/{id}         │
│  └── Knowledge Base     → GET/POST /api/knowledge         │
│                                                           │
│  FastAPI Backend (port 8003)                              │
│  ├── NEXUSOrchestrator  (LangGraph StateGraph)            │
│  │   ├── RequirementsAgent  → GPT-4o parse               │
│  │   ├── ResearchAgent      → ChromaDB RAG               │
│  │   ├── DesignAgent        → Physics equations           │
│  │   ├── SimulationAgent    → NumPy/SciPy solvers         │
│  │   ├── OptimizationAgent  → Pareto sweep               │
│  │   └── ReportAgent        → GPT-4o compile             │
│  ├── Redis (session state, 7-day TTL)                     │
│  └── ChromaDB (engineering KB, embeddings)               │
└──────────────────────────────────────────────────────────┘
```
