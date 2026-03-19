"""
NEXUS Platform — LangGraph Multi-Agent Orchestrator
====================================================
The central nervous system of NEXUS. Defines the AgentState TypedDict and
the directed acyclic graph (DAG) that routes state between agents.

Pipeline:
    START → requirements → research → design → simulation → optimization → report → END

Each node is an async function that receives the full state, does its work,
and returns a partial state update. LangGraph merges the updates.

Architecture note (for interviews):
  We use a StateGraph rather than a ReAct loop so that:
  1. Each specialist agent has a clear, bounded responsibility
  2. Provenance is captured at every hop (traceable decisions)
  3. The graph can be extended with conditional edges (e.g. retry loops,
     human-in-the-loop approval) without rewiring existing agents
  4. Observability hooks fire deterministically at node boundaries
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any, Optional

from typing_extensions import TypedDict

logger = logging.getLogger(__name__)


# ── Agent State ───────────────────────────────────────────────────────────────

class AgentState(TypedDict, total=False):
    """
    Shared state passed through every node in the NEXUS pipeline.

    All keys are optional (total=False) so each agent only needs to
    declare what it reads and what it writes — no boilerplate required.

    Provenance design:
      Each agent APPENDS one ProvenanceEntry to `provenance_chain`.
      This gives a complete, ordered audit trail of every decision made,
      which tool was called, how long it took, and the agent's confidence.
    """
    # ── Session identity ──────────────────────────────────────────────
    session_id: str
    engineering_brief: str
    current_agent: str           # Which agent is currently executing
    is_complete: bool
    error: Optional[str]

    # ── Agent outputs (populated sequentially) ────────────────────────
    requirements: dict[str, Any]        # From: RequirementsAgent
    research_results: dict[str, Any]    # From: ResearchAgent
    design_params: dict[str, Any]       # From: DesignAgent
    simulation_results: dict[str, Any]  # From: SimulationAgent
    optimized_params: dict[str, Any]    # From: OptimizationAgent
    report: dict[str, Any]             # From: ReportAgent

    # ── Observability ─────────────────────────────────────────────────
    provenance_chain: list[dict[str, Any]]  # Ordered audit trail
    messages: list[dict[str, Any]]          # LangChain message history


# ── SSE Event Queue ───────────────────────────────────────────────────────────

class SSEQueue:
    """
    Thread-safe async queue that bridges the pipeline execution to
    Server-Sent Events streaming in the FastAPI route handler.

    The orchestrator puts events; the SSE generator consumes them.
    A sentinel value (None) signals stream completion.
    """

    def __init__(self) -> None:
        self._queue: asyncio.Queue[Optional[dict]] = asyncio.Queue()

    async def put(self, event: dict) -> None:
        await self._queue.put(event)

    async def get(self) -> Optional[dict]:
        return await self._queue.get()

    async def close(self) -> None:
        await self._queue.put(None)  # sentinel

    def __aiter__(self):
        return self

    async def __anext__(self):
        item = await self._queue.get()
        if item is None:
            raise StopAsyncIteration
        return item


# ── Orchestrator ──────────────────────────────────────────────────────────────

class NEXUSOrchestrator:
    """
    Multi-agent pipeline orchestrator.

    Responsibilities:
    - Build and compile the LangGraph StateGraph
    - Stream SSE events for real-time frontend updates
    - Persist intermediate state after each agent completes
    - Handle errors with graceful degradation (pipeline continues)

    Usage:
        orchestrator = NEXUSOrchestrator(config, session_store)
        sse_queue = SSEQueue()
        asyncio.create_task(orchestrator.run(initial_state, sse_queue))
        async for event in sse_queue:
            yield f"data: {json.dumps(event)}\n\n"
    """

    AGENT_ORDER = [
        "requirements",
        "research",
        "design",
        "simulation",
        "optimization",
        "report",
    ]

    AGENT_LABELS = {
        "requirements": "Requirements Engineer",
        "research":     "Research Scientist",
        "design":       "Design Engineer",
        "simulation":   "Physics Simulator",
        "optimization": "Optimization Engineer",
        "report":       "Technical Writer",
    }

    AGENT_THOUGHTS = {
        "requirements": "Parsing engineering brief and extracting domain, objectives, constraints, performance targets...",
        "research":     "Querying engineering knowledge base with semantic search for relevant formulas and approaches...",
        "design":       "Calculating design parameters using physics equations and research findings...",
        "simulation":   "Running physics-based simulation with domain-specific engineering equations...",
        "optimization": "Executing multi-objective optimization — Pareto front sweep across parameter space...",
        "report":       "Compiling comprehensive engineering report from all agent outputs...",
    }

    def __init__(self, config, session_store=None) -> None:
        self.config = config
        self.session_store = session_store
        self._graph = None
        self._build_graph()

    def _build_graph(self) -> None:
        """
        Compile the LangGraph StateGraph.

        Graph topology (linear pipeline with error short-circuit):
          requirements → research → design → simulation → optimization → report

        Conditional edges could be added here for:
          - Human-in-the-loop approval after requirements
          - Retry loops if simulation performance_score < threshold
          - Parallel research + design if requirements confidence is high
        """
        try:
            from langgraph.graph import StateGraph, END

            from app.agents.requirements_agent import run_requirements_agent
            from app.agents.research_agent import run_research_agent
            from app.agents.design_agent import run_design_agent
            from app.agents.simulation_agent import run_simulation_agent
            from app.agents.optimization_agent import run_optimization_agent
            from app.agents.report_agent import run_report_agent

            cfg = self.config

            # Wrap each agent to inject config and handle errors
            async def node_requirements(state: AgentState) -> AgentState:
                return await run_requirements_agent(state, cfg)

            async def node_research(state: AgentState) -> AgentState:
                return await run_research_agent(state, cfg)

            async def node_design(state: AgentState) -> AgentState:
                return await run_design_agent(state, cfg)

            async def node_simulation(state: AgentState) -> AgentState:
                return await run_simulation_agent(state, cfg)

            async def node_optimization(state: AgentState) -> AgentState:
                return await run_optimization_agent(state, cfg)

            async def node_report(state: AgentState) -> AgentState:
                return await run_report_agent(state, cfg)

            def route_after_agent(state: AgentState) -> str:
                """
                Conditional edge: if any agent sets error, skip to END.
                Otherwise follow the linear pipeline.
                """
                if state.get("error"):
                    return END
                return state.get("current_agent", END)

            graph = StateGraph(AgentState)

            # Register nodes
            graph.add_node("requirements", node_requirements)
            graph.add_node("research",     node_research)
            graph.add_node("design",       node_design)
            graph.add_node("simulation",   node_simulation)
            graph.add_node("optimization", node_optimization)
            graph.add_node("report",       node_report)

            # Entry point
            graph.set_entry_point("requirements")

            # Linear edges with error short-circuit
            for i, agent in enumerate(self.AGENT_ORDER[:-1]):
                next_agent = self.AGENT_ORDER[i + 1]
                graph.add_conditional_edges(
                    agent,
                    route_after_agent,
                    {next_agent: next_agent, END: END},
                )

            # Report → END
            graph.add_edge("report", END)

            self._graph = graph.compile()
            logger.info("NEXUS LangGraph pipeline compiled successfully")

        except ImportError as e:
            logger.warning(f"LangGraph not available ({e}) — will use sequential fallback")
            self._graph = None
        except Exception as e:
            logger.error(f"Failed to compile LangGraph: {e}", exc_info=True)
            self._graph = None

    async def run(
        self,
        initial_state: AgentState,
        sse_queue: SSEQueue,
    ) -> AgentState:
        """
        Execute the full 6-agent pipeline, streaming SSE events at each step.

        Two execution modes:
        1. LangGraph mode: uses compiled StateGraph for proper graph execution
        2. Sequential fallback: runs agents in order if LangGraph unavailable

        Both modes emit identical SSE events so the frontend is unaffected.
        """
        session_id = initial_state.get("session_id", "unknown")

        try:
            if self._graph is not None:
                final_state = await self._run_with_langgraph(
                    initial_state, sse_queue, session_id
                )
            else:
                final_state = await self._run_sequential_fallback(
                    initial_state, sse_queue, session_id
                )

            # Persist completed session
            if self.session_store and not final_state.get("error"):
                await self._persist_session(final_state, "complete")

            await sse_queue.put({
                "type": "session_complete",
                "session_id": session_id,
                "timestamp": datetime.utcnow().isoformat(),
                "content": {
                    "status": "complete" if not final_state.get("error") else "error",
                    "provenance_count": len(final_state.get("provenance_chain", [])),
                    "report_title": final_state.get("report", {}).get("title", ""),
                },
            })

            return final_state

        except Exception as e:
            logger.error(f"[{session_id}] Pipeline fatal error: {e}", exc_info=True)
            await sse_queue.put({
                "type": "error",
                "session_id": session_id,
                "timestamp": datetime.utcnow().isoformat(),
                "content": str(e),
            })
            return {**initial_state, "error": str(e), "is_complete": False}

        finally:
            await sse_queue.close()

    async def _run_with_langgraph(
        self,
        initial_state: AgentState,
        sse_queue: SSEQueue,
        session_id: str,
    ) -> AgentState:
        """Execute pipeline using LangGraph's compiled StateGraph."""
        state = initial_state
        state["current_agent"] = "requirements"

        # Stream through LangGraph nodes
        async for chunk in self._graph.astream(state):
            for node_name, node_state in chunk.items():
                if node_name == "__end__":
                    continue

                # Emit agent_start event BEFORE the node output lands
                await sse_queue.put({
                    "type": "agent_start",
                    "agent": node_name,
                    "label": self.AGENT_LABELS.get(node_name, node_name),
                    "session_id": session_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "content": self.AGENT_THOUGHTS.get(node_name, "Processing..."),
                })

                # Merge partial state
                state = {**state, **node_state}

                # Persist intermediate state
                if self.session_store:
                    await self._persist_session(state, "running")

                # Emit agent_complete with provenance
                provenance = state.get("provenance_chain", [])
                last_prov = provenance[-1] if provenance else {}

                await sse_queue.put({
                    "type": "agent_complete",
                    "agent": node_name,
                    "label": self.AGENT_LABELS.get(node_name, node_name),
                    "session_id": session_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "content": {
                        "output_summary": last_prov.get("output_summary", ""),
                        "confidence_score": last_prov.get("confidence_score", 0.8),
                        "duration_ms": last_prov.get("duration_ms", 0),
                        "tools_used": last_prov.get("tools_used", []),
                    },
                })

                if state.get("error"):
                    break

        return state

    async def _run_sequential_fallback(
        self,
        initial_state: AgentState,
        sse_queue: SSEQueue,
        session_id: str,
    ) -> AgentState:
        """
        Sequential agent execution fallback when LangGraph is unavailable.
        Imports agents directly and calls them in order.
        """
        from app.agents.requirements_agent import run_requirements_agent
        from app.agents.research_agent import run_research_agent
        from app.agents.design_agent import run_design_agent
        from app.agents.simulation_agent import run_simulation_agent
        from app.agents.optimization_agent import run_optimization_agent
        from app.agents.report_agent import run_report_agent

        agent_funcs = [
            ("requirements", run_requirements_agent),
            ("research",     run_research_agent),
            ("design",       run_design_agent),
            ("simulation",   run_simulation_agent),
            ("optimization", run_optimization_agent),
            ("report",       run_report_agent),
        ]

        state = initial_state

        for agent_name, agent_fn in agent_funcs:
            if state.get("error"):
                break

            await sse_queue.put({
                "type": "agent_start",
                "agent": agent_name,
                "label": self.AGENT_LABELS.get(agent_name, agent_name),
                "session_id": session_id,
                "timestamp": datetime.utcnow().isoformat(),
                "content": self.AGENT_THOUGHTS.get(agent_name, "Processing..."),
            })

            try:
                new_state = await agent_fn(state, self.config)
                state = {**state, **new_state}
            except Exception as e:
                logger.error(f"[{session_id}] Agent {agent_name} failed: {e}", exc_info=True)
                state = {**state, "error": f"{agent_name} agent failed: {str(e)}"}
                break

            if self.session_store:
                await self._persist_session(state, "running")

            provenance = state.get("provenance_chain", [])
            last_prov = provenance[-1] if provenance else {}

            await sse_queue.put({
                "type": "agent_complete",
                "agent": agent_name,
                "label": self.AGENT_LABELS.get(agent_name, agent_name),
                "session_id": session_id,
                "timestamp": datetime.utcnow().isoformat(),
                "content": {
                    "output_summary": last_prov.get("output_summary", ""),
                    "confidence_score": last_prov.get("confidence_score", 0.8),
                    "duration_ms": last_prov.get("duration_ms", 0),
                    "tools_used": last_prov.get("tools_used", []),
                },
            })

        return state

    async def _persist_session(self, state: AgentState, status: str) -> None:
        """Serialize and save current pipeline state to session store."""
        try:
            session_dict = {
                "id": state.get("session_id", ""),
                "engineering_brief": state.get("engineering_brief", ""),
                "status": status,
                "current_agent": state.get("current_agent", ""),
                "requirements": state.get("requirements"),
                "research_results": state.get("research_results"),
                "design_params": state.get("design_params"),
                "simulation_results": state.get("simulation_results"),
                "optimized_params": state.get("optimized_params"),
                "report": state.get("report"),
                "provenance_chain": state.get("provenance_chain", []),
                "error": state.get("error"),
                "updated_at": datetime.utcnow().isoformat(),
            }

            if hasattr(self.session_store, "save_session"):
                self.session_store.save_session(session_dict)
            else:
                # Async store
                await asyncio.get_event_loop().run_in_executor(
                    None, self.session_store.save_session, session_dict
                )
        except Exception as e:
            logger.warning(f"Failed to persist session state: {e}")
