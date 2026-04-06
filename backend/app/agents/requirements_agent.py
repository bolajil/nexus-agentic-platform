"""
NEXUS Platform — Requirements Agent
Parses and structures the raw engineering brief into a formal requirements specification.
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

SYSTEM_PROMPT = """You are the NEXUS Requirements Engineer Agent — a senior systems engineer
specializing in translating engineering challenge briefs into formal, structured requirements.

Your role:
1. Parse the raw engineering brief and extract the PRIMARY OBJECTIVE
2. Identify the engineering DOMAIN (heat_transfer | propulsion | structural | electronics_cooling)
3. Extract quantitative PERFORMANCE TARGETS with units (e.g., "thermal load: 5000 W", "thrust: 500 N")
4. List CONSTRAINTS (physical, material, regulatory, operational)
5. Identify OPERATING CONDITIONS (temperatures, pressures, flow rates, environments)
6. Suggest MATERIALS appropriate for the application
7. Estimate COMPLEXITY SCORE (0.0-1.0) where 1.0 = most complex

Always respond with a valid JSON object matching this schema:
{
  "domain": "heat_transfer|propulsion|structural|electronics_cooling",
  "primary_objective": "One sentence description",
  "constraints": ["constraint1", "constraint2"],
  "performance_targets": {"param_name": value, ...},
  "materials": ["material1", "material2"],
  "operating_conditions": {"condition_name": value, ...},
  "complexity_score": 0.0-1.0,
  "clarifications_needed": ["any missing info"],
  "reasoning": "Brief explanation of your parsing"
}

Be precise with numerical values and always include units in the parameter names or values."""


async def run_requirements_agent(state: "AgentState", config: "Settings") -> dict[str, Any]:
    """
    Parse the engineering brief and produce structured requirements.
    Returns updated state with requirements populated.
    """
    start_time = datetime.utcnow()
    logger.info(f"[{state['session_id']}] Requirements Agent starting")

    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        from app.core.llm_factory import create_llm, get_callbacks

        llm = create_llm(config, temperature=0.1)
        _cb = get_callbacks(config, state["session_id"], "requirements_agent",
                            trace_id=state.get("lf_trace_id"), user_id=state.get("session_user_id"))

        engineering_brief = state.get("engineering_brief", state.get("messages", [{}])[0] if state.get("messages") else "")
        if isinstance(engineering_brief, list):
            # Extract from messages
            engineering_brief = next(
                (m.get("content", "") if isinstance(m, dict) else getattr(m, "content", "")
                 for m in engineering_brief if (m.get("role") if isinstance(m, dict) else getattr(m, "type", "")) in ("human", "user")),
                ""
            )

        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(
                content=f"""Parse this engineering challenge and extract structured requirements:

ENGINEERING BRIEF:
{engineering_brief}

Return ONLY the JSON object described in your instructions. No markdown, no explanation outside the JSON."""
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

        parsed = json.loads(raw_text)

        domain = parsed.get("domain", "heat_transfer")
        raw_targets = parsed.get("performance_targets", {})

        # Strip non-numeric values — downstream agents require float-compatible targets
        numeric_targets = {}
        for k, v in raw_targets.items():
            try:
                numeric_targets[k] = float(v)
            except (TypeError, ValueError):
                pass  # discard strings like "maximize" or "> 100"

        # Inject domain defaults so simulation/optimization always have something to work with
        if not numeric_targets:
            _defaults = {
                "propulsion":         {"thrust_N": 500.0, "Isp_s": 280.0, "chamber_pressure_Pa": 3e6},
                "heat_transfer":      {"thermal_load_W": 5000.0, "effectiveness": 0.8},
                "structural":         {"applied_force_N": 10000.0, "safety_factor_target": 2.5},
                "electronics_cooling":{"power_W": 200.0, "max_junction_temp_C": 85.0},
                "fluids":             {"flow_rate_m3_s": 0.01, "head_loss_m": 10.0, "pump_efficiency": 0.75},
                "mechanisms":         {"input_torque_Nm": 50.0, "gear_ratio": 4.0, "output_speed_rpm": 500.0},
            }
            numeric_targets = _defaults.get(domain, {})

        # Build requirements dict
        requirements = {
            "domain": domain,
            "primary_objective": parsed.get("primary_objective", ""),
            "constraints": parsed.get("constraints", []),
            "performance_targets": numeric_targets,
            "materials": parsed.get("materials", []),
            "operating_conditions": parsed.get("operating_conditions", {}),
            "raw_brief": engineering_brief,
            "complexity_score": parsed.get("complexity_score", 0.5),
            "clarifications_needed": parsed.get("clarifications_needed", []),
        }

        elapsed_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

        provenance_entry = {
            "agent_name": "requirements",
            "timestamp": datetime.utcnow().isoformat(),
            "input_summary": f"Raw engineering brief ({len(engineering_brief)} chars)",
            "output_summary": f"Domain: {requirements['domain']} | Objective: {requirements['primary_objective'][:80]}",
            "tools_used": [],
            "confidence_score": 0.9,
            "duration_ms": elapsed_ms,
        }

        logger.info(f"[{state['session_id']}] Requirements Agent complete — domain: {requirements['domain']}")

        current_provenance = state.get("provenance_chain", [])
        return {
            **state,
            "requirements": requirements,
            "current_agent": "research",
            "provenance_chain": current_provenance + [provenance_entry],
        }

    except json.JSONDecodeError as e:
        logger.error(f"Requirements Agent JSON parse error: {e}")
        # Fallback minimal requirements
        engineering_brief_text = state.get("engineering_brief", "")
        domain = "heat_transfer"
        for keyword in ["propulsion", "nozzle", "thrust", "rocket"]:
            if keyword in engineering_brief_text.lower():
                domain = "propulsion"
                break
        for keyword in ["stress", "beam", "structural", "load", "fatigue"]:
            if keyword in engineering_brief_text.lower():
                domain = "structural"
                break
        for keyword in ["electronics", "cooling", "pcb", "cpu", "junction"]:
            if keyword in engineering_brief_text.lower():
                domain = "electronics_cooling"
                break

        requirements = {
            "domain": domain,
            "primary_objective": engineering_brief_text[:200],
            "constraints": [],
            "performance_targets": {},
            "materials": [],
            "operating_conditions": {},
            "raw_brief": engineering_brief_text,
            "complexity_score": 0.5,
            "clarifications_needed": ["Could not fully parse brief — using defaults"],
        }

        current_provenance = state.get("provenance_chain", [])
        return {
            **state,
            "requirements": requirements,
            "current_agent": "research",
            "provenance_chain": current_provenance + [{
                "agent_name": "requirements",
                "timestamp": datetime.utcnow().isoformat(),
                "input_summary": "Raw brief",
                "output_summary": f"Fallback parse — domain: {domain}",
                "tools_used": [],
                "confidence_score": 0.5,
            }],
        }
    except Exception as e:
        logger.error(f"Requirements Agent error: {e}", exc_info=True)
        return {**state, "error": f"Requirements Agent failed: {str(e)}", "current_agent": "error"}
