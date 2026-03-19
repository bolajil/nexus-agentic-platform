"""
NEXUS Platform — Simulation Agent
Runs physics-based simulation using the real engineering simulation engine.
Validates design parameters against physical laws and performance targets.
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

SYSTEM_PROMPT = """You are the NEXUS Simulation Agent — a computational engineer who validates
engineering designs using physics-based simulation.

Your mission:
1. Review the design parameters from the Design Agent
2. Select the appropriate simulation function for the domain
3. Run the simulation with parameters extracted from the design
4. Interpret the simulation results
5. Identify performance gaps vs. requirements
6. Recommend specific parameter adjustments if performance is inadequate

Available simulation tools:
- run_heat_exchanger_simulation: NTU-effectiveness method with full thermal analysis
- run_rocket_nozzle_simulation: de Laval nozzle with isentropic flow
- run_electronics_cooling_simulation: Thermal resistance network + convection
- run_structural_stress_simulation: Classical beam theory + Von Mises

You MUST run the appropriate simulation. After reviewing results:
- Score performance from 0.0 to 1.0 (1.0 = perfectly meets all targets)
- List any warnings or violations
- Suggest parameter modifications if score < 0.8

Always run the simulation that matches the engineering domain."""


async def run_simulation_agent(state: "AgentState", config: "Settings") -> dict[str, Any]:
    """
    Execute physics simulation and validate design parameters.
    Returns updated state with simulation_results populated.
    """
    start_time = datetime.utcnow()
    logger.info(f"[{state['session_id']}] Simulation Agent starting")

    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        from app.tools.simulation_tool import SIMULATION_TOOLS
        from app.core.llm_factory import create_llm, get_callbacks

        llm = create_llm(config, temperature=0.0).bind_tools(SIMULATION_TOOLS)
        _cb = get_callbacks(config, state["session_id"], "simulation_agent",
                            trace_id=state.get("lf_trace_id"), user_id=state.get("session_user_id"))

        requirements = state.get("requirements", {})
        design_params = state.get("design_params", {})
        domain = requirements.get("domain", "heat_transfer")
        targets = requirements.get("performance_targets", {})
        primary_params = design_params.get("primary_parameters", {})

        sim_args = _extract_simulation_args(domain, primary_params, targets, requirements)

        simulation_prompt = f"""Run a physics simulation to validate this engineering design.

DOMAIN: {domain}
DESIGN PARAMETERS:
{json.dumps(primary_params, indent=2)}

PERFORMANCE TARGETS:
{json.dumps(targets, indent=2)}

SUGGESTED SIMULATION INPUTS (use these as starting point):
{json.dumps(sim_args, indent=2)}

INSTRUCTIONS:
1. Call the appropriate simulation function for the '{domain}' domain
2. Use the suggested inputs above, adjusting if needed for physical validity
3. After getting results, evaluate performance against targets
4. Report a performance_score (0.0-1.0) and any warnings"""

        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=simulation_prompt),
        ]

        tools_used = []
        sim_output = {}

        # Agentic tool use loop
        max_iterations = 4
        for iteration in range(max_iterations):
            response = await llm.ainvoke(messages, config={"callbacks": _cb})
            messages.append(response)

            if not response.tool_calls:
                break

            from langchain_core.messages import ToolMessage
            for tc in response.tool_calls:
                tool_name = tc["name"]
                tool_args = tc["args"]
                tools_used.append(tool_name)

                # Execute the simulation tool
                result = await _run_simulation(tool_name, tool_args, SIMULATION_TOOLS)
                sim_output = result if isinstance(result, dict) else sim_output

                messages.append(
                    ToolMessage(
                        content=json.dumps(result, default=str),
                        tool_call_id=tc["id"],
                    )
                )

        # If no tool was called, run simulation directly
        if not tools_used:
            logger.warning(f"[{state['session_id']}] LLM did not call simulation tool — running directly")
            sim_output = _run_simulation_directly(domain, sim_args)
            tools_used = [f"direct_{domain}_simulation"]

        # Compute performance score
        performance_score = _compute_performance_score(sim_output, targets, domain)

        final_text = response.content if hasattr(response, "content") else ""
        warnings = sim_output.get("warnings", [])

        simulation_results = {
            "simulation_type": domain,
            "input_parameters": sim_args,
            "output_metrics": {k: v for k, v in sim_output.items() if isinstance(v, (int, float))},
            "performance_score": performance_score,
            "warnings": warnings,
            "raw_data": sim_output,
            "llm_analysis": final_text[:800] if final_text else "",
        }

        elapsed_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

        provenance_entry = {
            "agent_name": "simulation",
            "timestamp": datetime.utcnow().isoformat(),
            "input_summary": f"Domain: {domain} | Tool: {tools_used[0] if tools_used else 'none'}",
            "output_summary": f"Performance score: {performance_score:.2f} | Warnings: {len(warnings)}",
            "tools_used": tools_used,
            "confidence_score": performance_score,
            "duration_ms": elapsed_ms,
        }

        logger.info(f"[{state['session_id']}] Simulation Agent complete — score: {performance_score:.2f}")

        current_provenance = state.get("provenance_chain", [])
        return {
            **state,
            "simulation_results": simulation_results,
            "current_agent": "optimization",
            "provenance_chain": current_provenance + [provenance_entry],
        }

    except Exception as e:
        logger.error(f"Simulation Agent error: {e}", exc_info=True)
        return {**state, "error": f"Simulation Agent failed: {str(e)}", "current_agent": "error"}


def _extract_simulation_args(
    domain: str, primary_params: dict, targets: dict, requirements: dict
) -> dict:
    """Extract relevant simulation arguments from design parameters."""
    conditions = requirements.get("operating_conditions", {})

    def find_val(keys: list, default: float) -> float:
        for k in keys:
            for source in [primary_params, targets, conditions]:
                for pk, pv in source.items():
                    if any(key.lower() in pk.lower() for key in [k]) and isinstance(pv, (int, float)):
                        return float(pv)
        return default

    if domain == "heat_transfer":
        return {
            "power_watts": find_val(["power", "thermal_load", "heat_load", "kw", "watt"], 5000.0),
            "fluid_type": "water",
            "flow_rate": find_val(["flow_rate", "mass_flow"], 0.1),
            "inlet_temp_hot": find_val(["hot_inlet", "inlet_hot", "temp_hot"], 80.0),
            "inlet_temp_cold": find_val(["cold_inlet", "inlet_cold", "temp_cold"], 20.0),
            "heat_transfer_area": find_val(["area", "heat_transfer_area"], 2.0),
            "overall_htc": find_val(["htc", "U", "overall_u"], 500.0),
        }
    elif domain == "propulsion":
        return {
            "thrust_n": find_val(["thrust", "force", "N"], 500.0),
            "chamber_pressure_pa": find_val(["chamber_pressure", "Pc"], 3_000_000.0),
            "expansion_ratio": find_val(["expansion_ratio", "area_ratio"], 8.0),
            "chamber_temp_k": find_val(["chamber_temp", "Tc"], 3500.0),
            "propellant_molar_mass": find_val(["molar_mass", "M"], 0.022),
        }
    elif domain == "electronics_cooling":
        return {
            "power_w": find_val(["power", "tdp", "thermal_design_power", "watt"], 200.0),
            "ambient_temp_c": find_val(["ambient", "coolant_temp"], 25.0),
            "heatsink_area_m2": find_val(["heatsink_area", "area"], 0.015),
            "airflow_velocity_m_s": find_val(["velocity", "airflow", "flow_velocity"], 3.0),
            "junction_to_case_resistance": find_val(["rjc", "junction_case"], 0.3),
            "component_type": "GPU" if "gpu" in str(requirements).lower() else "CPU",
        }
    elif domain == "structural":
        return {
            "applied_force_n": find_val(["force", "load", "applied_load"], 10000.0),
            "cross_section_area_m2": find_val(["area", "cross_section"], 0.001),
            "material": _find_material(requirements.get("materials", ["steel"])),
            "beam_length_m": find_val(["length", "span"], 2.0),
        }
    return {}


def _find_material(materials: list) -> str:
    material_map = {"steel": "steel", "aluminum": "aluminum", "aluminium": "aluminum",
                    "titanium": "titanium", "carbon": "carbon_fiber"}
    for mat in materials:
        for k, v in material_map.items():
            if k in mat.lower():
                return v
    return "steel"


async def _run_simulation(tool_name: str, args: dict, tools: list) -> dict:
    """Execute a simulation tool by name."""
    for tool in tools:
        if tool.name == tool_name:
            try:
                result = tool.invoke(args)
                return result if isinstance(result, dict) else {"result": result}
            except Exception as e:
                logger.error(f"Simulation tool {tool_name} error: {e}")
                return {"error": str(e)}
    return {"error": f"Unknown simulation tool: {tool_name}"}


def _run_simulation_directly(domain: str, args: dict) -> dict:
    """Run simulation without LLM tool calling (fallback)."""
    from app.tools.simulation_tool import (
        heat_exchanger_simulation,
        rocket_nozzle_simulation,
        electronics_cooling_simulation,
        structural_stress_simulation,
    )
    import math

    try:
        if domain == "heat_transfer":
            return heat_exchanger_simulation(**{
                k: v for k, v in args.items()
                if k in ["power_watts", "fluid_type", "flow_rate", "inlet_temp_hot",
                          "inlet_temp_cold", "heat_transfer_area", "overall_htc"]
            })
        elif domain == "propulsion":
            return rocket_nozzle_simulation(**{
                k: v for k, v in args.items()
                if k in ["thrust_n", "chamber_pressure_pa", "expansion_ratio",
                          "chamber_temp_k", "propellant_molar_mass"]
            })
        elif domain == "electronics_cooling":
            return electronics_cooling_simulation(**{
                k: v for k, v in args.items()
                if k in ["power_w", "ambient_temp_c", "heatsink_area_m2",
                          "junction_to_case_resistance", "airflow_velocity_m_s", "component_type"]
            })
        elif domain == "structural":
            a = args.get("cross_section_area_m2", 0.001)
            r = math.sqrt(a / math.pi)
            I = math.pi * r**4 / 4
            return structural_stress_simulation(
                applied_force_n=args.get("applied_force_n", 10000),
                cross_section_area_m2=a,
                material=args.get("material", "steel"),
                beam_length_m=args.get("beam_length_m", 2.0),
                moment_of_inertia_m4=I,
            )
    except Exception as e:
        logger.error(f"Direct simulation failed: {e}")
        return {"error": str(e), "warnings": [str(e)]}
    return {}


def _safe_float(value, default: float) -> float:
    """Convert value to float, falling back to default if conversion fails."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _compute_performance_score(sim_output: dict, targets: dict, domain: str) -> float:
    """Compute a normalized performance score (0-1) based on simulation results vs targets."""
    if not sim_output or "error" in sim_output:
        return 0.3

    scores = []

    if domain == "heat_transfer":
        eff = _safe_float(sim_output.get("effectiveness", 0), 0)
        scores.append(min(eff / 0.80, 1.0))  # target 80% effectiveness
        perf_ratio = _safe_float(sim_output.get("performance_ratio", 0), 0)
        scores.append(min(perf_ratio, 1.0))

    elif domain == "propulsion":
        isp = _safe_float(sim_output.get("Isp_s", 0), 0)
        target_isp = _safe_float(targets.get("Isp_s", targets.get("isp", 280.0)), 280.0)
        scores.append(min(isp / max(target_isp, 1), 1.0))
        thrust = _safe_float(sim_output.get("thrust_N", 0), 0)
        target_thrust = _safe_float(targets.get("thrust_N", targets.get("thrust", 500.0)), 500.0)
        scores.append(min(thrust / max(target_thrust, 1), 1.0))

    elif domain == "electronics_cooling":
        T_j = _safe_float(sim_output.get("junction_temperature_C", 150), 150)
        margin = _safe_float(sim_output.get("thermal_margin_percent", 0), 0)
        scores.append(max(0.0, min(margin / 30.0, 1.0)))  # 30%+ margin = perfect
        scores.append(1.0 if T_j < 85 else (0.6 if T_j < 100 else 0.2))

    elif domain == "structural":
        sf = _safe_float(sim_output.get("safety_factor", 0), 0)
        scores.append(min(sf / 3.0, 1.0))  # SF=3 = perfect score

    if not scores:
        return 0.7  # default passing score if no metrics extracted

    # Penalize for warnings
    n_warnings = len(sim_output.get("warnings", []))
    warning_penalty = min(n_warnings * 0.05, 0.20)

    base_score = sum(scores) / len(scores)
    return round(max(0.0, base_score - warning_penalty), 3)
