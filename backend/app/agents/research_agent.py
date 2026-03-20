"""
NEXUS Platform — Research Agent
Performs RAG-based search of the engineering knowledge base to surface
relevant formulas, design patterns, and references for the design agent.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.agents.orchestrator import AgentState
    from app.core.config import Settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the NEXUS Research Agent — a specialist engineering librarian with
deep knowledge of thermodynamics, fluid mechanics, structural mechanics, and propulsion systems.

Your mission is to:
1. Analyze the structured engineering requirements
2. Identify the most relevant scientific principles and formulas
3. Recommend proven design approaches for this type of problem
4. Surface critical constraints and failure modes from engineering literature
5. Compile a concise research brief to guide the Design Agent

Use the search_engineering_knowledge tool to query the knowledge base.
Search with 2-3 different queries to maximize relevant coverage.

After searching, synthesize the results into:
- Key relevant formulas with explanations
- Recommended design approaches (ranked by suitability)
- Critical constraints and gotchas
- Relevant performance benchmarks from literature
- Suggested calculation sequence for the Design Agent

Be thorough but concise. The Design Agent depends on your output to make correct calculations."""


async def run_research_agent(state: "AgentState", config: "Settings") -> dict[str, Any]:
    """
    Research engineering knowledge base and compile relevant findings.
    Returns updated state with research_results populated.
    """
    start_time = datetime.utcnow()
    logger.info(f"[{state['session_id']}] Research Agent starting")

    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        from app.tools.rag_tool import search_engineering_knowledge
        from app.core.llm_factory import create_llm, get_callbacks

        llm = create_llm(config, temperature=0.2)
        _cb = get_callbacks(config, state["session_id"], "research_agent",
                            trace_id=state.get("lf_trace_id"), user_id=state.get("session_user_id"))

        requirements = state.get("requirements", {})
        domain = requirements.get("domain", "heat_transfer")
        objective = requirements.get("primary_objective", "")
        performance_targets = requirements.get("performance_targets", {})

        # ── NIST fluid property queries ───────────────────────────────
        nist_data = {}
        nist_tools_used = []
        fluid = _infer_fluid(domain, requirements)
        if fluid:
            temp_k  = _infer_temperature_k(requirements)
            press_mpa = _infer_pressure_mpa(requirements)
            try:
                from app.tools.nist_tool import get_fluid_properties
                props = get_fluid_properties.invoke({
                    "fluid": fluid,
                    "temperature_k": temp_k,
                    "pressure_mpa": press_mpa,
                })
                if "error" not in props:
                    nist_data = props
                    nist_tools_used.append(
                        f"NIST({fluid} @ {temp_k:.0f}K, {press_mpa:.4f}MPa)"
                    )
                    logger.info(f"[{state['session_id']}] NIST data retrieved for {fluid}")
            except Exception as e:
                logger.warning(f"[{state['session_id']}] NIST lookup failed: {e}")

        # ── RAG knowledge base searches ───────────────────────────────
        queries = _build_search_queries(domain, objective, performance_targets)
        all_documents = []
        tools_used = list(nist_tools_used)

        for query in queries:
            logger.info(f"[{state['session_id']}] Research search: '{query}'")
            results = await _safe_rag_search(query, domain, k=4)
            all_documents.extend(results)
            tools_used.append(f"search_engineering_knowledge('{query[:40]}...')")

        # Deduplicate by content
        seen_content = set()
        unique_docs = []
        for doc in all_documents:
            content_key = doc.get("content", "")[:100]
            if content_key not in seen_content:
                seen_content.add(content_key)
                unique_docs.append(doc)

        # Synthesize with LLM
        docs_text = "\n\n".join(
            f"[Source {i+1} | Relevance: {d.get('relevance_score', 0):.2f}]\n{d.get('content', '')}"
            for i, d in enumerate(unique_docs[:8])
        )

        # Format NIST data for injection into synthesis prompt
        nist_section = ""
        if nist_data:
            nist_lines = [f"  {k}: {v}" for k, v in nist_data.items() if k != "source"]
            nist_section = (
                f"\nREAL FLUID PROPERTIES (NIST WebBook — {nist_data.get('source', fluid)}):\n"
                + "\n".join(nist_lines)
                + "\n"
            )

        synthesis_messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(
                content=f"""Synthesize the following retrieved knowledge for this engineering challenge:

REQUIREMENTS SUMMARY:
- Domain: {domain}
- Objective: {objective}
- Performance Targets: {performance_targets}
- Operating Conditions: {requirements.get('operating_conditions', {})}
{nist_section}
RETRIEVED KNOWLEDGE BASE DOCUMENTS:
{docs_text if docs_text else "No documents found in knowledge base. Use your training knowledge."}

Provide a structured research brief covering:
1. Most relevant formulas and equations (with context)
2. Recommended design approach (step by step)
3. Critical design constraints for this application
4. Performance benchmarks and typical values
5. Common failure modes to avoid
6. Key references/standards

Format as clear, actionable engineering guidance for the Design Agent."""
            ),
        ]

        response = await llm.ainvoke(synthesis_messages, config={"callbacks": _cb})
        synthesis_text = response.content

        # Extract formulas mentioned in the synthesis
        relevant_formulas = _extract_formulas_from_text(synthesis_text, domain)

        # Build recommended approaches list
        recommended_approaches = _extract_approaches(synthesis_text)

        elapsed_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

        research_results = {
            "query_used": " | ".join(queries),
            "retrieved_documents": unique_docs[:8],
            "relevant_formulas": relevant_formulas,
            "recommended_approaches": recommended_approaches,
            "references": [d.get("metadata", {}).get("source", "Engineering KB") for d in unique_docs[:5]],
            "summary": synthesis_text,
            "document_count": len(unique_docs),
        }

        provenance_entry = {
            "agent_name": "research",
            "timestamp": datetime.utcnow().isoformat(),
            "input_summary": f"Domain: {domain} | {len(queries)} queries",
            "output_summary": f"Retrieved {len(unique_docs)} docs | {len(relevant_formulas)} formulas | {len(recommended_approaches)} approaches",
            "tools_used": tools_used,
            "confidence_score": min(0.95, 0.5 + len(unique_docs) * 0.05),
            "duration_ms": elapsed_ms,
        }

        logger.info(f"[{state['session_id']}] Research Agent complete — {len(unique_docs)} docs retrieved")

        current_provenance = state.get("provenance_chain", [])
        return {
            **state,
            "research_results": research_results,
            "current_agent": "design",
            "provenance_chain": current_provenance + [provenance_entry],
        }

    except Exception as e:
        logger.error(f"Research Agent error: {e}", exc_info=True)
        return {**state, "error": f"Research Agent failed: {str(e)}", "current_agent": "error"}


def _build_search_queries(domain: str, objective: str, targets: dict) -> list[str]:
    """Build targeted search queries for the knowledge base."""
    queries = []

    domain_queries = {
        "heat_transfer": [
            "heat exchanger design NTU effectiveness method",
            "convection heat transfer coefficient Nusselt number",
            "LMTD log mean temperature difference shell tube",
        ],
        "propulsion": [
            "rocket nozzle design de Laval isentropic flow",
            "specific impulse Isp thrust coefficient nozzle",
            "chamber pressure expansion ratio Mach number",
        ],
        "structural": [
            "beam stress analysis Von Mises failure criterion",
            "safety factor fatigue analysis structural design",
            "FEA finite element stress concentration",
        ],
        "electronics_cooling": [
            "thermal resistance junction temperature heatsink",
            "forced convection electronics cooling fan design",
            "PCB thermal management power dissipation",
        ],
    }

    queries.extend(domain_queries.get(domain, domain_queries["heat_transfer"])[:2])
    # Add objective-based query
    if objective:
        queries.append(objective[:80])

    return queries[:3]


async def _safe_rag_search(query: str, domain: str, k: int = 4) -> list[dict]:
    """Safely invoke RAG search, returning empty list on failure."""
    try:
        from app.tools.rag_tool import _vector_store_manager
        if _vector_store_manager is None:
            return []
        results = _vector_store_manager.similarity_search(query=query, k=k, filter_domain=domain)
        return results
    except Exception as e:
        logger.warning(f"RAG search failed for '{query}': {e}")
        return []


def _extract_formulas_from_text(text: str, domain: str) -> list[str]:
    """Extract formula references from synthesis text."""
    # Look for common formula patterns
    formula_keywords = {
        "heat_transfer": ["NTU", "LMTD", "Nusselt", "Reynolds", "Prandtl", "Fourier", "Newton", "effectiveness"],
        "propulsion": ["Tsiolkovsky", "Isp", "De Laval", "isentropic", "thrust coefficient", "Mach", "c*"],
        "structural": ["Von Mises", "Hooke", "Euler", "moment of inertia", "safety factor", "yield"],
        "electronics_cooling": ["thermal resistance", "junction temperature", "Rθjc", "Newton cooling", "Biot"],
    }
    keywords = formula_keywords.get(domain, [])
    found = []
    for kw in keywords:
        if kw.lower() in text.lower():
            found.append(kw)
    return found


def _infer_fluid(domain: str, requirements: dict) -> str | None:
    """Guess the primary fluid from domain and requirements text."""
    brief = str(requirements).lower()
    fluid_map = {
        "water": ["water", "aqueous", "cooling water", "chilled water"],
        "nitrogen": ["nitrogen", "n2", "cold gas"],
        "oxygen": ["oxygen", "lox", "liquid oxygen"],
        "air": ["air", "forced air", "ambient air"],
        "co2": ["co2", "carbon dioxide"],
        "r134a": ["r134a", "refrigerant", "hfc"],
        "methane": ["methane", "lng", "ch4"],
        "hydrogen": ["hydrogen", "h2"],
    }
    for fluid, keywords in fluid_map.items():
        if any(kw in brief for kw in keywords):
            return fluid
    # Domain defaults
    defaults = {
        "heat_transfer":    "water",
        "electronics_cooling": "air",
        "propulsion":       "nitrogen",
        "structural":       None,
    }
    return defaults.get(domain)


def _infer_temperature_k(requirements: dict) -> float:
    """Extract operating temperature in Kelvin from requirements."""
    conditions = requirements.get("operating_conditions", {})
    targets    = requirements.get("performance_targets", {})
    for source in [conditions, targets]:
        for k, v in source.items():
            if any(t in k.lower() for t in ["temp", "inlet", "hot", "cold"]):
                try:
                    val = float(v)
                    if val < 100:
                        return val + 273.15  # assume Celsius
                    return val
                except (TypeError, ValueError):
                    pass
    return 300.0  # default 300 K


def _infer_pressure_mpa(requirements: dict) -> float:
    """Extract operating pressure in MPa from requirements."""
    conditions = requirements.get("operating_conditions", {})
    targets    = requirements.get("performance_targets", {})
    for source in [conditions, targets]:
        for k, v in source.items():
            if "press" in k.lower():
                try:
                    val = float(v)
                    if val > 1000:
                        return val / 1e6       # Pa → MPa
                    elif val > 10:
                        return val / 1000      # kPa → MPa
                    return val                 # already MPa
                except (TypeError, ValueError):
                    pass
    return 0.101325  # 1 atm


def _extract_approaches(text: str) -> list[str]:
    """Extract recommended approaches from synthesis text (first 3 numbered items)."""
    approaches = []
    lines = text.split("\n")
    for line in lines:
        stripped = line.strip()
        if stripped and (stripped[0].isdigit() or stripped.startswith("-") or stripped.startswith("•")):
            clean = stripped.lstrip("0123456789.-•) ").strip()
            if len(clean) > 20:
                approaches.append(clean[:150])
        if len(approaches) >= 5:
            break
    return approaches
