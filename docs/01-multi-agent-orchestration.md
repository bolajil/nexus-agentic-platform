# 01 — Multi-Agent Orchestration

## Core Concept

A multi-agent system splits a complex task into specialist sub-tasks, each owned
by an independent agent with bounded responsibility. The orchestrator manages
routing, state sharing, and error handling.

**Why LangGraph over a single ReAct loop?**

| Single ReAct Agent | LangGraph Multi-Agent |
|---|---|
| One LLM owns everything | Each agent is a specialist |
| Hard to audit what happened | Provenance chain per agent |
| No parallelism possible | Conditional parallel edges |
| Monolithic, hard to extend | Add/remove nodes independently |
| Single point of failure | Error short-circuit, graceful degradation |

---

## LangGraph StateGraph

```python
from langgraph.graph import StateGraph, END
from typing_extensions import TypedDict

class AgentState(TypedDict, total=False):
    session_id:        str
    engineering_brief: str
    requirements:      dict
    research_results:  dict
    design_params:     dict
    simulation_results: dict
    optimized_params:  dict
    report:            dict
    provenance_chain:  list[dict]
    error:             str | None

graph = StateGraph(AgentState)

# Register nodes
graph.add_node("requirements", node_requirements)
graph.add_node("research",     node_research)
# ... etc.

# Conditional edge: error short-circuit
def route(state):
    return END if state.get("error") else state["current_agent"]

graph.add_conditional_edges("requirements", route, {"research": "research", END: END})

compiled = graph.compile()
```

### Key design decisions

1. **`total=False`** — agents only declare the keys they touch; no boilerplate
2. **Conditional edges** — error in any node routes to END, protecting downstream
3. **Partial state updates** — each node returns only what it changed; LangGraph merges
4. **Async nodes** — all agent functions are `async def` for non-blocking I/O

---

## Provenance System

Every agent appends to `state["provenance_chain"]`:

```python
entry = {
    "agent_name": "design",
    "timestamp": datetime.utcnow().isoformat(),
    "input_summary": "domain=heat_transfer, constraints=[...]",
    "output_summary": "h=45.2 W/m²K, fin_efficiency=0.87, R_total=0.52 °C/W",
    "tools_used": ["physics_calculator", "fin_efficiency_calculator"],
    "confidence_score": 0.91,
    "duration_ms": 1243.5,
}
state["provenance_chain"].append(entry)
```

This gives:
- **Traceability** — every number has a source
- **Explainability** — stakeholders can audit any decision
- **Debugging** — low confidence scores flag uncertain outputs
- **Compliance** — safety-critical systems need full audit trails

---

## SSE Streaming Pattern

The pipeline runs as an `asyncio.create_task()`. Events are bridged to the
HTTP response via an `SSEQueue`:

```python
# In the route handler:
sse_queue = SSEQueue()
asyncio.create_task(orchestrator.run(initial_state, sse_queue))

return StreamingResponse(_sse_generator(sse_queue), media_type="text/event-stream")

# The generator:
async def _sse_generator(queue):
    async for event in queue:
        yield f"data: {json.dumps(event)}\n\n"
```

Event types:
- `agent_start` — agent is beginning work
- `agent_complete` — agent finished, includes confidence + duration
- `tool_call` — agent called a tool
- `tool_result` — tool returned a result
- `session_complete` — all agents done
- `heartbeat` — keep-alive every 15s
- `error` — pipeline error

---

## Interview Answer: Multi-Agent Architecture

> *"How do you design a multi-agent system for production?"*

"I use LangGraph's StateGraph with a TypedDict shared state. Each agent is a
node that reads relevant keys and appends to the provenance chain. Conditional
edges enable error short-circuits so one failing agent doesn't cascade. State is
persisted to Redis after each node boundary — so if the process restarts, we can
resume from the last checkpoint. For streaming, each node emits SSE events through
an asyncio Queue bridged to a FastAPI StreamingResponse, giving the frontend
real-time visibility without polling."
