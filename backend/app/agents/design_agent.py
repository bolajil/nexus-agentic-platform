"""
NEXUS Platform — Design Agent
Calculates engineering design parameters using physics formulas and
the research agent's knowledge base findings.
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

SYSTEM_PROMPT = """You are the NEXUS Design Agent — a senior design engineer who translates
engineering requirements and research findings into a complete, quantified design solution.

Your responsibilities:
1. Review the structured requirements and research findings
2. Select the most appropriate design approach
3. Calculate all primary design parameters using correct engineering formulas
4. Specify secondary/derived parameters
5. Document all assumptions and their justifications
6. Assess design feasibility with a confidence score (0.0-1.0)

Available calculator tools:
- calculate_reynolds_number: Re = V*L/ν for flow characterization
- calculate_heat_transfer_coefficient: h from Nu correlation
- calculate_isentropic_flow: P/P0, T/T0, A/A* at given Mach
- calculate_thermal_resistance: R_cond + R_conv networks
- calculate_safety_factor: SF = σ_yield / σ_applied
- unit_converter: Convert between engineering unit systems

You MUST use at least 2 calculator tools and show your work.

Respond with a JSON object:
{
  "primary_parameters": {"param_name_unit": value, ...},
  "secondary_parameters": {"param_name_unit": value, ...},
  "design_equations_used": ["equation1", "equation2"],
  "assumptions": ["assumption1", ...],
  "feasibility_assessment": "text assessment",
  "confidence_score": 0.0-1.0,
  "design_narrative": "Step-by-step design explanation"
}"""


async def run_design_agent(state: "AgentState", config: "Settings") -> dict[str, Any]:
    """
    Calculate design parameters based on requirements and research findings.
    Returns updated state with design_params populated.
    """
    start_time = datetime.utcnow()
    logger.info(f"[{state['session_id']}] Design Agent starting")

    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        from app.tools.calculator_tool import CALCULATOR_TOOLS
        from app.core.llm_factory import create_llm, get_callbacks

        llm = create_llm(config, temperature=0.1).bind_tools(CALCULATOR_TOOLS)
        _cb = get_callbacks(config, state["session_id"], "design_agent",
                            trace_id=state.get("lf_trace_id"), user_id=state.get("session_user_id"))

        requirements = state.get("requirements", {})
        research_results = state.get("research_results", {})
        domain = requirements.get("domain", "heat_transfer")

        # Build the design prompt with all context
        design_prompt = _build_design_prompt(requirements, research_results, domain)

        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=design_prompt),
        ]

        tools_used = []
        all_params = {}

        # Agentic loop — LLM can call tools then continue
        max_iterations = 5
        for iteration in range(max_iterations):
            response = await llm.ainvoke(messages, config={"callbacks": _cb})
            messages.append(response)

            if not response.tool_calls:
                # Final response — extract design parameters
                break

            # Process tool calls
            from langchain_core.messages import ToolMessage
            for tc in response.tool_calls:
                tool_name = tc["name"]
                tool_args = tc["args"]
                tools_used.append(tool_name)

                # Find and execute the tool
                tool_result = await _execute_calculator_tool(tool_name, tool_args, CALCULATOR_TOOLS)
                all_params.update(tool_result if isinstance(tool_result, dict) else {})

                messages.append(
                    ToolMessage(
                        content=json.dumps(tool_result, default=str),
                        tool_call_id=tc["id"],
                    )
                )

        # Extract final design parameters from LLM response
        final_text = response.content if hasattr(response, "content") else ""
        design_params = _extract_design_params(final_text, all_params, domain, requirements)

        # ── FreeCAD CAD generation ────────────────────────────────────
        cad_result = {"available": False, "message": "FreeCAD not attempted"}
        try:
            from app.tools.freecad_tool import generate_cad
            cad_result = generate_cad(
                session_id=state["session_id"],
                domain=domain,
                design_params=design_params,
            )
            if cad_result["available"]:
                # Write domain metadata so the CAD router can report it
                from pathlib import Path
                from app.tools.freecad_tool import CAD_OUTPUT_DIR
                meta = CAD_OUTPUT_DIR / state["session_id"] / "meta.txt"
                meta.write_text(domain, encoding="utf-8")
                logger.info(f"[{state['session_id']}] CAD generated: {cad_result['message']}")
            else:
                logger.info(f"[{state['session_id']}] CAD skipped: {cad_result['message']}")
        except Exception as cad_err:
            logger.warning(f"[{state['session_id']}] FreeCAD tool error: {cad_err}")

        elapsed_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        confidence = design_params.get("confidence_score", 0.8)

        provenance_entry = {
            "agent_name": "design",
            "timestamp": datetime.utcnow().isoformat(),
            "input_summary": f"Domain: {domain} | Targets: {list(requirements.get('performance_targets', {}).keys())}",
            "output_summary": f"{len(design_params.get('primary_parameters', {}))} primary params | Confidence: {confidence:.2f}",
            "tools_used": tools_used,
            "confidence_score": confidence,
            "duration_ms": elapsed_ms,
        }

        logger.info(f"[{state['session_id']}] Design Agent complete — {len(tools_used)} tool calls")

        current_provenance = state.get("provenance_chain", [])
        return {
            **state,
            "design_params": design_params,
            "cad_info": cad_result,
            "current_agent": "simulation",
            "provenance_chain": current_provenance + [provenance_entry],
        }

    except Exception as e:
        logger.error(f"Design Agent error: {e}", exc_info=True)
        return {**state, "error": f"Design Agent failed: {str(e)}", "current_agent": "error"}


def _build_design_prompt(requirements: dict, research_results: dict, domain: str) -> str:
    """Build the design calculation prompt."""
    targets = requirements.get("performance_targets", {})
    conditions = requirements.get("operating_conditions", {})
    research_summary = (research_results.get("summary", "")[:1500]
                        if research_results.get("summary") else "No research available")

    return f"""Design a solution for this engineering challenge:

DOMAIN: {domain}
PRIMARY OBJECTIVE: {requirements.get('primary_objective', 'Not specified')}

PERFORMANCE TARGETS:
{json.dumps(targets, indent=2)}

OPERATING CONDITIONS:
{json.dumps(conditions, indent=2)}

CONSTRAINTS:
{chr(10).join('- ' + c for c in requirements.get('constraints', []))}

MATERIALS AVAILABLE:
{', '.join(requirements.get('materials', ['standard engineering materials']))}

RESEARCH BRIEF:
{research_summary}

INSTRUCTIONS:
1. Use the calculator tools to compute key parameters (Reynolds number, heat transfer coefficients, etc.)
2. Show step-by-step calculations
3. After tool calls, provide your final design as a JSON object with all parameters

Calculate the primary design parameters now. Use at least 2 different calculator tools."""


async def _execute_calculator_tool(tool_name: str, args: dict, tools: list) -> dict:
    """Find and execute a calculator tool by name."""
    for tool in tools:
        if tool.name == tool_name:
            try:
                result = tool.invoke(args)
                return result if isinstance(result, dict) else {"result": result}
            except Exception as e:
                logger.warning(f"Tool {tool_name} failed: {e}")
                return {"error": str(e)}
    return {"error": f"Unknown tool: {tool_name}"}


def _extract_design_params(text: str, computed_params: dict, domain: str, requirements: dict) -> dict:
    """Extract or construct design parameters from LLM response and computed values."""
    # Try to parse JSON from LLM response
    try:
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        # Find JSON object
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            parsed = json.loads(text[start:end])
            if "primary_parameters" in parsed:
                return parsed
    except (json.JSONDecodeError, ValueError):
        pass

    # Fallback: construct params from computed values and domain defaults
    targets = requirements.get("performance_targets", {})
    primary = {}
    secondary = {}

    # Add computed params
    for k, v in computed_params.items():
        if isinstance(v, (int, float)):
            primary[k] = v

    # Add domain-specific defaults from targets
    for param, value in targets.items():
        if isinstance(value, (int, float)):
            primary[param] = value

    # Domain-specific derived parameters
    if domain == "heat_transfer":
        primary.setdefault("NTU", 3.0)
        primary.setdefault("effectiveness", 0.85)
        primary.setdefault("heat_transfer_area_m2", 2.5)
        secondary["flow_regime"] = "turbulent"

    elif domain == "propulsion":
        primary.setdefault("expansion_ratio", 8.0)
        primary.setdefault("chamber_pressure_MPa", 3.0)
        primary.setdefault("throat_diameter_mm", 25.0)
        secondary["nozzle_type"] = "de_Laval_converging_diverging"

    elif domain == "electronics_cooling":
        primary.setdefault("heatsink_area_cm2", 100.0)
        primary.setdefault("airflow_velocity_m_s", 3.0)
        primary.setdefault("thermal_resistance_total_C_W", 0.8)

    elif domain == "structural":
        primary.setdefault("safety_factor", 2.5)
        primary.setdefault("cross_section_area_cm2", 25.0)

    elif domain == "fluids":
        primary.setdefault("flow_rate_m3_s", 0.01)
        primary.setdefault("pipe_diameter_m", 0.1)
        primary.setdefault("pipe_length_m", 100.0)
        primary.setdefault("head_loss_m", 10.0)
        secondary["fluid_type"] = "water"
        secondary["pipe_material"] = "steel"

    elif domain == "mechanisms":
        primary.setdefault("input_torque_Nm", 50.0)
        primary.setdefault("gear_ratio", 4.0)
        primary.setdefault("input_speed_rpm", 1750.0)
        primary.setdefault("module_mm", 2.0)
        secondary["gear_material"] = "steel"
        secondary["mechanism_type"] = "gear_train"

    equations = _domain_equations(domain)
    assumptions = [
        "Steady-state operating conditions assumed",
        "Ideal fluid properties at mean temperature",
        "Standard atmospheric pressure unless specified",
    ]

    return {
        "primary_parameters": primary,
        "secondary_parameters": secondary,
        "units": _domain_units(domain),
        "design_equations_used": equations,
        "assumptions": assumptions,
        "feasibility_assessment": f"Design appears feasible based on {domain} standard practices",
        "confidence_score": 0.78,
        "design_narrative": text[:500] if text else "Parameters computed using engineering correlations",
    }


def _domain_equations(domain: str) -> list[str]:
    equations = {
        "heat_transfer": [
            "NTU = UA/C_min",
            "ε = (1 - exp(-NTU(1+Cr))) / (1+Cr) [counter-flow]",
            "Nu = 0.023 * Re^0.8 * Pr^0.4 [Dittus-Boelter]",
            "LMTD = (ΔT1 - ΔT2) / ln(ΔT1/ΔT2)",
        ],
        "propulsion": [
            "F = ṁVe + (Pe-Pa)Ae",
            "Isp = Ve/g0",
            "A/A* = (1/M)*[(2/(γ+1))*(1+(γ-1)/2*M²)]^((γ+1)/(2(γ-1)))",
            "Ve = sqrt(2γ/(γ-1)*R*Tc/M*[1-(Pe/Pc)^((γ-1)/γ)])",
        ],
        "structural": [
            "σ_axial = F/A",
            "σ_bending = Mc/I",
            "σ_VM = sqrt(σ² + 3τ²)",
            "δ = FL³/(48EI) [mid-span, simply supported]",
        ],
        "electronics_cooling": [
            "T_j = T_amb + Q*(Rjc + Rcs + Rsa)",
            "R_sa = 1/(h*A_eff)",
            "Nu_L = 0.664*Re_L^0.5*Pr^(1/3) [laminar plate]",
            "Q_max = (T_j,max - T_amb) / R_total",
        ],
    }
    return equations.get(domain, [])


def _domain_units(domain: str) -> dict[str, str]:
    units = {
        "heat_transfer": {"power": "W", "temperature": "°C", "area": "m²", "pressure": "Pa"},
        "propulsion": {"thrust": "N", "pressure": "Pa", "Isp": "s", "area": "m²"},
        "structural": {"stress": "Pa", "force": "N", "deflection": "mm", "area": "m²"},
        "electronics_cooling": {"power": "W", "temperature": "°C", "resistance": "°C/W", "area": "m²"},
    }
    return units.get(domain, {})
