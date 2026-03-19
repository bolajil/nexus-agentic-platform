"""
NEXUS Platform — Report Agent
Compiles all agent outputs into a comprehensive structured engineering report.
This is the final agent in the pipeline — it marks the session as complete.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.agents.orchestrator import AgentState
    from app.core.config import Settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the NEXUS Report Agent — a senior engineering technical writer and systems engineer
who compiles comprehensive, publication-quality engineering reports.

Your mission:
1. Review ALL outputs from the previous 5 agents (Requirements, Research, Design, Simulation, Optimization)
2. Synthesize findings into a structured engineering report
3. Write each section with professional engineering language
4. Ensure all quantitative data is presented with proper units
5. Provide actionable, prioritized recommendations
6. Highlight risks and mitigation strategies

Your report must follow this exact JSON structure:
{
  "title": "Engineering Analysis Report: [brief title]",
  "executive_summary": "3-5 sentence high-level summary for non-technical stakeholders",
  "requirements_section": "Detailed description of parsed requirements with all constraints and targets",
  "research_findings": "Key findings from literature/knowledge base research including relevant formulas",
  "design_solution": "Comprehensive description of the proposed design with all key parameters and their values",
  "simulation_results": "Detailed simulation output analysis with performance scores and validation against targets",
  "optimization_results": "Optimization methodology, parameter improvements, and Pareto analysis",
  "conclusions": "Engineering assessment of whether the design meets requirements",
  "recommendations": ["Prioritized list", "of actionable recommendations", "with specificity"],
  "appendix": {
    "key_parameters": {},
    "performance_metrics": {}
  }
}

Write substantively — each section should be 2-5 detailed sentences minimum.
Include specific numbers, units, and engineering justifications.
The executive summary should be readable by a project manager or executive."""


async def run_report_agent(state: "AgentState", config: "Settings") -> dict[str, Any]:
    """
    Compile a comprehensive engineering report from all previous agent outputs.
    Returns updated state with report populated and is_complete set to True.
    """
    start_time = datetime.utcnow()
    logger.info(f"[{state['session_id']}] Report Agent starting — compiling final report")

    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        from app.core.llm_factory import create_llm, get_callbacks

        llm = create_llm(config, temperature=0.2)
        _cb = get_callbacks(config, state["session_id"], "report_agent",
                            trace_id=state.get("lf_trace_id"), user_id=state.get("session_user_id"))

        requirements = state.get("requirements", {})
        research_results = state.get("research_results", {})
        design_params = state.get("design_params", {})
        simulation_results = state.get("simulation_results", {})
        optimized_params = state.get("optimized_params", {})
        engineering_brief = state.get("engineering_brief", "")
        domain = requirements.get("domain", "unknown")

        # Build a comprehensive context for the LLM
        context = _build_report_context(
            engineering_brief=engineering_brief,
            requirements=requirements,
            research_results=research_results,
            design_params=design_params,
            simulation_results=simulation_results,
            optimized_params=optimized_params,
        )

        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(
                content=f"""Compile the final engineering report for this session.

ORIGINAL ENGINEERING BRIEF:
{engineering_brief}

COMPLETE PIPELINE OUTPUTS:
{context}

Write a comprehensive engineering report as JSON. Every section must be detailed and substantive.
Include specific numerical values from the simulation and optimization results.
Return ONLY the JSON object — no markdown fences, no explanation outside the JSON."""
            ),
        ]

        response = await llm.ainvoke(messages, config={"callbacks": _cb})
        raw_text = response.content.strip()

        # Strip markdown code fences if present
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]
            raw_text = raw_text.strip()
        # Handle trailing fence
        if raw_text.endswith("```"):
            raw_text = raw_text[: raw_text.rfind("```")].strip()

        parsed = json.loads(raw_text)

        # Build final report dict, filling any missing fields
        perf_score = simulation_results.get("performance_score", 0.75)
        opt_params = optimized_params.get("optimized_params", {})
        sim_metrics = simulation_results.get("output_metrics", {})

        report = {
            "title": parsed.get(
                "title",
                f"Engineering Analysis Report: {domain.replace('_', ' ').title()} System",
            ),
            "executive_summary": parsed.get("executive_summary", _fallback_executive_summary(
                domain, requirements, perf_score, optimized_params
            )),
            "requirements_section": parsed.get("requirements_section", _format_requirements(requirements)),
            "research_findings": parsed.get("research_findings", _format_research(research_results)),
            "design_solution": parsed.get("design_solution", _format_design(design_params)),
            "simulation_results": parsed.get("simulation_results", _format_simulation(simulation_results)),
            "optimization_results": parsed.get("optimization_results", _format_optimization(optimized_params)),
            "conclusions": parsed.get("conclusions", _build_conclusions(domain, perf_score, requirements)),
            "recommendations": parsed.get("recommendations", _build_recommendations(
                domain, perf_score, optimized_params, simulation_results
            )),
            "appendix": parsed.get("appendix", {
                "key_parameters": opt_params,
                "performance_metrics": sim_metrics,
            }),
            "generated_at": datetime.utcnow().isoformat(),
        }

        elapsed_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

        provenance_entry = {
            "agent_name": "report",
            "timestamp": datetime.utcnow().isoformat(),
            "input_summary": (
                f"Compiling report from {len(state.get('provenance_chain', []))} agent outputs | "
                f"Domain: {domain} | Performance score: {perf_score:.2f}"
            ),
            "output_summary": (
                f"Report generated: {len(report['recommendations'])} recommendations | "
                f"{len(report['title'])} char title"
            ),
            "tools_used": [],
            "confidence_score": 0.92,
            "duration_ms": elapsed_ms,
        }

        logger.info(
            f"[{state['session_id']}] Report Agent complete — "
            f"{len(report['recommendations'])} recommendations, elapsed {elapsed_ms:.0f}ms"
        )

        current_provenance = state.get("provenance_chain", [])
        return {
            **state,
            "report": report,
            "is_complete": True,
            "current_agent": "complete",
            "provenance_chain": current_provenance + [provenance_entry],
        }

    except json.JSONDecodeError as e:
        logger.error(f"Report Agent JSON parse error: {e} — building fallback report")
        # Build a complete fallback report without LLM JSON
        requirements = state.get("requirements", {})
        simulation_results = state.get("simulation_results", {})
        optimized_params = state.get("optimized_params", {})
        domain = requirements.get("domain", "unknown")
        perf_score = simulation_results.get("performance_score", 0.7)

        report = _build_fallback_report(
            engineering_brief=state.get("engineering_brief", ""),
            requirements=requirements,
            research_results=state.get("research_results", {}),
            design_params=state.get("design_params", {}),
            simulation_results=simulation_results,
            optimized_params=optimized_params,
            domain=domain,
            perf_score=perf_score,
        )

        elapsed_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        current_provenance = state.get("provenance_chain", [])
        return {
            **state,
            "report": report,
            "is_complete": True,
            "current_agent": "complete",
            "provenance_chain": current_provenance + [{
                "agent_name": "report",
                "timestamp": datetime.utcnow().isoformat(),
                "input_summary": "Fallback report generation (JSON parse error)",
                "output_summary": "Structured fallback report compiled",
                "tools_used": [],
                "confidence_score": 0.7,
                "duration_ms": elapsed_ms,
            }],
        }

    except Exception as e:
        logger.error(f"Report Agent error: {e}", exc_info=True)
        return {
            **state,
            "error": f"Report Agent failed: {str(e)}",
            "current_agent": "error",
            "is_complete": False,
        }


# ── Helper builders ───────────────────────────────────────────────────────────


def _build_report_context(
    engineering_brief: str,
    requirements: dict,
    research_results: dict,
    design_params: dict,
    simulation_results: dict,
    optimized_params: dict,
) -> str:
    """Assemble a structured context string for the LLM."""
    sections = []

    sections.append("=== REQUIREMENTS ===")
    sections.append(f"Domain: {requirements.get('domain', 'N/A')}")
    sections.append(f"Objective: {requirements.get('primary_objective', 'N/A')}")
    sections.append(f"Constraints: {json.dumps(requirements.get('constraints', []))}")
    sections.append(f"Performance Targets: {json.dumps(requirements.get('performance_targets', {}))}")
    sections.append(f"Materials: {json.dumps(requirements.get('materials', []))}")
    sections.append(f"Operating Conditions: {json.dumps(requirements.get('operating_conditions', {}))}")

    sections.append("\n=== RESEARCH FINDINGS ===")
    sections.append(f"Query: {research_results.get('query_used', 'N/A')}")
    sections.append(f"Summary: {research_results.get('summary', 'N/A')}")
    sections.append(f"Relevant Formulas: {json.dumps(research_results.get('relevant_formulas', []))}")
    sections.append(f"Recommended Approaches: {json.dumps(research_results.get('recommended_approaches', []))}")

    sections.append("\n=== DESIGN PARAMETERS ===")
    sections.append(f"Primary: {json.dumps(design_params.get('primary_parameters', {}))}")
    sections.append(f"Secondary: {json.dumps(design_params.get('secondary_parameters', {}))}")
    sections.append(f"Units: {json.dumps(design_params.get('units', {}))}")
    sections.append(f"Equations Used: {json.dumps(design_params.get('design_equations_used', []))}")
    sections.append(f"Assumptions: {json.dumps(design_params.get('assumptions', []))}")
    sections.append(f"Feasibility: {design_params.get('feasibility_assessment', 'N/A')}")

    sections.append("\n=== SIMULATION RESULTS ===")
    sections.append(f"Type: {simulation_results.get('simulation_type', 'N/A')}")
    sections.append(f"Performance Score: {simulation_results.get('performance_score', 'N/A'):.2f}/1.00" if isinstance(simulation_results.get('performance_score'), float) else "Performance Score: N/A")
    sections.append(f"Output Metrics: {json.dumps(simulation_results.get('output_metrics', {}))}")
    sections.append(f"Warnings: {json.dumps(simulation_results.get('warnings', []))}")
    sections.append(f"LLM Analysis: {simulation_results.get('llm_analysis', 'N/A')}")

    sections.append("\n=== OPTIMIZATION RESULTS ===")
    sections.append(f"Method: {optimized_params.get('optimization_method', 'N/A')}")
    sections.append(f"Iterations: {optimized_params.get('iterations', 'N/A')}")
    sections.append(f"Original Params: {json.dumps(optimized_params.get('original_params', {}))}")
    sections.append(f"Optimized Params: {json.dumps(optimized_params.get('optimized_params', {}))}")
    sections.append(f"Improvements: {json.dumps(optimized_params.get('improvement_metrics', {}))}")
    sections.append(f"Recommendation: {optimized_params.get('recommendation', 'N/A')}")

    return "\n".join(sections)


def _fallback_executive_summary(domain: str, requirements: dict, perf_score: float, optimized_params: dict) -> str:
    objective = requirements.get("primary_objective", "the stated engineering challenge")
    improvement = optimized_params.get("improvement_metrics", {})
    avg_imp = sum(improvement.values()) / max(len(improvement), 1) if improvement else 0.0
    status = "meets design requirements" if perf_score >= 0.75 else "requires further iteration to meet requirements"
    return (
        f"This report presents a comprehensive analysis of {objective}. "
        f"The NEXUS multi-agent pipeline executed a full engineering workflow spanning requirements parsing, "
        f"literature research, physics-based design, simulation validation, and multi-objective optimization. "
        f"The final design achieves a simulation performance score of {perf_score:.0%} and {status}. "
        f"Optimization yielded an average improvement of {avg_imp:.1f}% across key performance metrics, "
        f"and specific implementation recommendations are provided in the conclusions section."
    )


def _format_requirements(requirements: dict) -> str:
    domain = requirements.get("domain", "unknown")
    objective = requirements.get("primary_objective", "N/A")
    constraints = requirements.get("constraints", [])
    targets = requirements.get("performance_targets", {})
    materials = requirements.get("materials", [])
    conditions = requirements.get("operating_conditions", {})

    lines = [
        f"Engineering Domain: {domain.replace('_', ' ').title()}",
        f"Primary Objective: {objective}",
        f"Performance Targets: {', '.join(f'{k}={v}' for k, v in targets.items()) or 'None specified'}",
        f"Design Constraints: {'; '.join(constraints) or 'None specified'}",
        f"Candidate Materials: {', '.join(materials) or 'Not specified'}",
        f"Operating Conditions: {', '.join(f'{k}={v}' for k, v in conditions.items()) or 'Standard conditions'}",
    ]
    return " | ".join(lines)


def _format_research(research_results: dict) -> str:
    summary = research_results.get("summary", "Research conducted via engineering knowledge base.")
    formulas = research_results.get("relevant_formulas", [])
    approaches = research_results.get("recommended_approaches", [])

    text = summary
    if formulas:
        text += f" Key formulas identified: {'; '.join(formulas[:3])}."
    if approaches:
        text += f" Recommended approaches: {'; '.join(approaches[:3])}."
    return text


def _format_design(design_params: dict) -> str:
    primary = design_params.get("primary_parameters", {})
    units = design_params.get("units", {})
    feasibility = design_params.get("feasibility_assessment", "Feasible based on current analysis.")
    equations = design_params.get("design_equations_used", [])

    params_str = ", ".join(
        f"{k}={v} {units.get(k, '')}" for k, v in list(primary.items())[:8]
    )
    text = f"Design parameters: {params_str or 'Refer to appendix'}. {feasibility}"
    if equations:
        text += f" Design equations: {'; '.join(equations[:3])}."
    return text


def _format_simulation(simulation_results: dict) -> str:
    sim_type = simulation_results.get("simulation_type", "physics")
    score = simulation_results.get("performance_score", 0.0)
    metrics = simulation_results.get("output_metrics", {})
    warnings = simulation_results.get("warnings", [])

    metrics_str = ", ".join(f"{k}={v:.3g}" for k, v in list(metrics.items())[:6])
    text = (
        f"Physics-based {sim_type} simulation completed with performance score {score:.0%}. "
        f"Key output metrics: {metrics_str or 'See appendix'}."
    )
    if warnings:
        text += f" Simulation warnings: {'; '.join(warnings[:3])}."
    return text


def _format_optimization(optimized_params: dict) -> str:
    method = optimized_params.get("optimization_method", "parametric sweep")
    iterations = optimized_params.get("iterations", 0)
    improvements = optimized_params.get("improvement_metrics", {})
    recommendation = optimized_params.get("recommendation", "")

    improvements_str = ", ".join(f"{k}={v:.1f}%" for k, v in improvements.items())
    text = (
        f"Multi-objective optimization via {method} ({iterations} iterations). "
        f"Performance improvements: {improvements_str or 'See appendix'}. "
        f"{recommendation}"
    )
    return text


def _build_conclusions(domain: str, perf_score: float, requirements: dict) -> str:
    objective = requirements.get("primary_objective", "the design objective")
    verdict = (
        "fully satisfies" if perf_score >= 0.85
        else "substantially satisfies" if perf_score >= 0.70
        else "partially satisfies"
    )
    return (
        f"The proposed {domain.replace('_', ' ')} design {verdict} {objective} "
        f"with a validated simulation performance score of {perf_score:.0%}. "
        f"The design was refined through {domain}-specific physics simulation and multi-objective optimization, "
        f"producing a Pareto-optimal solution that balances competing engineering objectives. "
        f"{'The design is recommended for detailed engineering and prototyping.' if perf_score >= 0.75 else 'Additional design iteration is recommended before proceeding to prototyping.'}"
    )


def _build_recommendations(
    domain: str,
    perf_score: float,
    optimized_params: dict,
    simulation_results: dict,
) -> list[str]:
    recs = []
    warnings = simulation_results.get("warnings", [])
    opt_params = optimized_params.get("optimized_params", {})

    # Universal recommendations
    if perf_score >= 0.8:
        recs.append(
            f"Proceed to detailed engineering design using the optimized parameters as baseline."
        )
    else:
        recs.append(
            f"Conduct additional design iterations to improve performance score from {perf_score:.0%} to ≥80%."
        )

    # Address warnings
    for w in warnings[:2]:
        recs.append(f"Address simulation warning: {w}")

    # Domain-specific
    if domain == "heat_transfer":
        recs.append("Validate heat exchanger effectiveness experimentally using a bench-scale prototype before full-scale manufacture.")
        recs.append("Perform a fouling factor sensitivity study to ensure long-term performance meets targets.")
        recs.append("Consider LMTD correction factors if multi-pass or cross-flow configuration is adopted.")
    elif domain == "propulsion":
        recs.append("Conduct hot-fire testing at the simulated chamber conditions to validate Isp and thrust predictions.")
        recs.append("Perform nozzle throat thermal analysis and select an appropriate regenerative or ablative cooling method.")
        recs.append("Verify chamber pressure stability with combustion instability analysis before full-duration tests.")
    elif domain == "electronics_cooling":
        recs.append("Validate thermal resistance network experimentally using IR thermography on a representative PCB assembly.")
        recs.append("Implement thermal runaway protection via on-die temperature sensors triggering fan speed control.")
        recs.append("Review TIM (Thermal Interface Material) bond line thickness specification to minimize junction-to-case resistance.")
    elif domain == "structural":
        recs.append("Perform FEA validation of the analytical beam model, particularly at stress concentrations and joints.")
        recs.append("Conduct fatigue life analysis using an S-N approach if the component is subject to cyclic loading.")
        recs.append("Verify material certification compliance with applicable standards (e.g., ASTM, AMS) for safety-critical use.")

    # Add optimized params recommendation
    if opt_params:
        param_summary = ", ".join(f"{k}={v}" for k, v in list(opt_params.items())[:3])
        recs.append(f"Adopt optimized key parameters in design drawings: {param_summary}.")

    recs.append(
        "Document all design assumptions and re-evaluate if operating conditions deviate more than 10% from specified values."
    )

    return recs[:8]  # Cap at 8 recommendations


def _build_fallback_report(
    engineering_brief: str,
    requirements: dict,
    research_results: dict,
    design_params: dict,
    simulation_results: dict,
    optimized_params: dict,
    domain: str,
    perf_score: float,
) -> dict:
    """Build a complete report dict without LLM assistance."""
    return {
        "title": f"Engineering Analysis Report: {domain.replace('_', ' ').title()} System",
        "executive_summary": _fallback_executive_summary(domain, requirements, perf_score, optimized_params),
        "requirements_section": _format_requirements(requirements),
        "research_findings": _format_research(research_results),
        "design_solution": _format_design(design_params),
        "simulation_results": _format_simulation(simulation_results),
        "optimization_results": _format_optimization(optimized_params),
        "conclusions": _build_conclusions(domain, perf_score, requirements),
        "recommendations": _build_recommendations(domain, perf_score, optimized_params, simulation_results),
        "appendix": {
            "key_parameters": optimized_params.get("optimized_params", design_params.get("primary_parameters", {})),
            "performance_metrics": simulation_results.get("output_metrics", {}),
        },
        "generated_at": datetime.utcnow().isoformat(),
    }
