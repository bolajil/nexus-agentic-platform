'use client';
import { useState } from 'react';
import { motion } from 'framer-motion';
import Sidebar from '../components/Sidebar';

const SECTIONS = [
  {
    id: 'overview',
    title: 'Platform Overview',
    icon: '⬡',
    content: `NEXUS is a production-grade multi-agent AI platform for autonomous hardware engineering design.

It demonstrates all key skills required for a Senior AI Engineer – Agentic Platform Lead role:
• Multi-agent orchestration with LangGraph StateGraph
• Distributed systems with Redis session persistence
• RAG-powered knowledge retrieval with ChromaDB
• Real-time SSE streaming for live pipeline visibility
• Full provenance and audit trail for explainability
• Physics-based simulation and multi-objective optimization
• Docker-compose deployment with observability hooks`
  },
  {
    id: 'pipeline',
    title: '6-Agent Pipeline',
    icon: '◈',
    content: `The pipeline routes state through 6 specialist agents in sequence:

1. Requirements Agent
   - Parses the engineering brief using GPT-4o
   - Extracts: domain, objectives, constraints, performance targets, materials
   - Outputs: EngineeringRequirements model

2. Research Agent
   - Queries ChromaDB with semantic similarity search
   - Retrieves relevant formulas, equations, and design approaches
   - Grounds subsequent agents in engineering reference material

3. Design Agent
   - Calculates primary design parameters using physics equations
   - Applies domain-specific formulas (e.g. Newton's Law of Cooling, Tsiolkovsky)
   - Outputs: DesignParameters with units, assumptions, and feasibility

4. Simulation Agent
   - Runs domain-specific physics simulation (NumPy/SciPy)
   - Evaluates thermal resistance, nozzle thrust, structural stress, etc.
   - Outputs: SimulationResult with performance_score and warnings

5. Optimization Agent
   - Multi-objective optimization sweeping the parameter space
   - Pareto-front analysis (performance vs. weight vs. cost)
   - Outputs: OptimizedParameters with improvement metrics

6. Report Agent
   - Compiles all outputs into a structured engineering report
   - Sections: executive summary, design, simulation, optimization, recommendations
   - Exports as structured JSON`
  },
  {
    id: 'orchestration',
    title: 'LangGraph Orchestration',
    icon: '◉',
    content: `The orchestrator uses LangGraph's StateGraph for deterministic multi-agent routing.

AgentState TypedDict:
  session_id, engineering_brief, current_agent, is_complete, error
  requirements, research_results, design_params, simulation_results
  optimized_params, report, provenance_chain, messages

Graph topology:
  START → requirements → research → design → simulation → optimization → report → END

Conditional edges allow error short-circuit:
  If any agent sets state["error"], the graph routes to END immediately.

This design enables:
  • Extension with human-in-the-loop approval nodes
  • Retry loops for low-confidence outputs
  • Parallel execution (e.g. research + design running concurrently)
  • Branching based on domain detected in requirements

SSE streaming:
  Each node emits agent_start → (thought) → agent_complete events
  through an asyncio.Queue bridged to FastAPI StreamingResponse.`
  },
  {
    id: 'memory',
    title: 'Memory & Provenance',
    icon: '◎',
    content: `NEXUS implements two memory systems:

1. Session Store (Redis / In-Memory fallback)
   - Stores full pipeline state after each agent completes
   - TTL: 7 days
   - Keys: nexus:session:{uuid}
   - Enables resume, replay, and audit

2. Vector Store (ChromaDB)
   - Embedding model: text-embedding-3-small
   - Collection: nexus_engineering_kb
   - Documents: heat transfer, propulsion, structural, electronics cooling
   - Retrieved chunks grounded in real engineering equations

Provenance Chain:
   Every agent execution appends a ProvenanceEntry:
   { agent_name, timestamp, input_summary, output_summary,
     tools_used[], confidence_score, duration_ms, token_usage }

   This creates a complete, ordered audit trail — critical for:
   • Explaining design decisions to stakeholders
   • Debugging unexpected outputs
   • Regulatory compliance in safety-critical systems`
  },
  {
    id: 'observability',
    title: 'Observability',
    icon: '◇',
    content: `Production observability stack:

Structured Logging (structlog):
  - JSON-formatted logs with trace_id, agent, session_id
  - Log levels: DEBUG, INFO, WARNING, ERROR

OpenTelemetry:
  - Traces span across agent boundaries
  - OTLP exporter (compatible with Jaeger, Grafana Tempo)
  - FastAPI auto-instrumentation

Metrics (via OTLP):
  - Pipeline execution time per agent
  - Token usage per LLM call
  - Cache hit/miss rate for vector search
  - Error rates by agent name

Health Endpoints:
  GET /health  → liveness probe
  GET /ready   → readiness probe (checks Redis + OpenAI key)

Request timing:
  X-Process-Time-Ms header on every response`
  },
  {
    id: 'interview',
    title: 'Interview Talking Points',
    icon: '★',
    content: `Key narratives for Senior AI Engineer – Agentic Platform Lead:

Q: How do you design a multi-agent system for reliability?
A: "I use LangGraph's StateGraph so each agent has bounded responsibility and error
   short-circuits route to END without affecting other sessions. State is persisted
   to Redis after each node so partial results survive failures and can be replayed."

Q: How do you ensure explainability?
A: "Every agent appends a ProvenanceEntry with input summary, output summary, tools
   used, confidence score, and duration. This creates a full audit trail the frontend
   renders as a timeline — you can trace exactly why each design decision was made."

Q: How do you handle agents that run simulations or external tools?
A: "Each agent has access to domain-specific tools: physics simulation (NumPy/SciPy),
   a calculator, and RAG retrieval. Tools are called with structured inputs and
   return typed outputs, so the LLM parses reliable data rather than free text."

Q: How do you stream results in real-time?
A: "The pipeline runs as an asyncio background task. An SSEQueue bridges agent events
   to a FastAPI StreamingResponse. The client receives agent_start, agent_complete,
   and session_complete events as they fire — no polling required."

Q: Describe your approach to scaling this system.
A: "The stateless FastAPI workers read/write session state from Redis, so horizontal
   scaling is trivial. LangGraph graphs can be distributed across worker processes.
   For high-concurrency, each session gets its own asyncio task with bounded queues."`
  },
];

export default function DocsPage() {
  const [active, setActive] = useState('overview');
  const section = SECTIONS.find(s => s.id === active)!;

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="ml-60 flex-1 p-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white">Architecture Guide</h1>
          <p className="text-slate-400 mt-1 text-sm">Reference documentation for interview preparation and platform understanding</p>
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-4 gap-6">
          {/* Nav */}
          <div className="xl:col-span-1 space-y-1.5">
            {SECTIONS.map(s => (
              <button
                key={s.id}
                onClick={() => setActive(s.id)}
                className={`w-full flex items-center gap-3 text-left px-4 py-3 rounded-xl text-sm transition-all ${
                  active === s.id
                    ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/30'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-[#1e1e38]'
                }`}
              >
                <span>{s.icon}</span>
                {s.title}
              </button>
            ))}
          </div>

          {/* Content */}
          <motion.div
            key={active}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="xl:col-span-3 glass-card p-8"
          >
            <h2 className="text-xl font-bold text-white mb-6 flex items-center gap-3">
              <span className="text-indigo-400">{section.icon}</span>
              {section.title}
            </h2>
            <pre className="text-sm text-slate-300 leading-relaxed whitespace-pre-wrap font-mono">
              {section.content}
            </pre>
          </motion.div>
        </div>
      </main>
    </div>
  );
}
