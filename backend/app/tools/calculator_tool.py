"""
NEXUS Platform — Engineering Calculator Tools
General-purpose engineering calculation utilities used by design agents.
"""
from __future__ import annotations

import math
from typing import Any

from langchain_core.tools import tool


@tool
def calculate_reynolds_number(
    velocity: float,
    length: float,
    kinematic_viscosity: float = 1.5e-5,
) -> dict[str, Any]:
    """
    Calculate Reynolds number for flow characterization.
    Re = V * L / ν
    Args: velocity (m/s), characteristic length (m), kinematic viscosity (m²/s)
    Returns Re and flow regime classification.
    """
    Re = velocity * length / max(kinematic_viscosity, 1e-12)
    if Re < 2300:
        regime = "laminar"
    elif Re < 4000:
        regime = "transitional"
    else:
        regime = "turbulent"
    return {
        "reynolds_number": round(Re, 2),
        "flow_regime": regime,
        "velocity_m_s": velocity,
        "length_m": length,
        "kinematic_viscosity_m2_s": kinematic_viscosity,
    }


@tool
def calculate_heat_transfer_coefficient(
    fluid: str = "air",
    reynolds_number: float = 10000.0,
    prandtl: float = 0.71,
    conductivity: float = 0.026,
    length: float = 0.1,
    surface_condition: str = "smooth",
) -> dict[str, Any]:
    """
    Calculate convective heat transfer coefficient using Dittus-Boelter or Churchill-Bernstein.
    Returns h (W/m²·K) and Nusselt number.
    """
    Re = reynolds_number
    Pr = prandtl
    k = conductivity

    if Re > 10000:
        # Dittus-Boelter — turbulent pipe/channel flow
        Nu = 0.023 * Re ** 0.8 * Pr ** 0.4
        correlation = "Dittus-Boelter"
    elif Re > 2300:
        # Gnielinski — transitional
        f = (0.790 * math.log(Re) - 1.64) ** (-2)
        Nu = (f / 8) * (Re - 1000) * Pr / (1 + 12.7 * math.sqrt(f / 8) * (Pr ** (2 / 3) - 1))
        correlation = "Gnielinski"
    else:
        # Laminar — constant wall temperature
        Nu = 3.66
        correlation = "Laminar (constant T_wall)"

    h = Nu * k / length
    return {
        "heat_transfer_coefficient_W_m2K": round(h, 3),
        "nusselt_number": round(Nu, 3),
        "correlation_used": correlation,
        "reynolds_number": Re,
        "prandtl_number": Pr,
    }


@tool
def calculate_isentropic_flow(
    mach_number: float,
    gamma: float = 1.4,
    stagnation_pressure_pa: float = 101325.0,
    stagnation_temperature_k: float = 300.0,
) -> dict[str, Any]:
    """
    Calculate isentropic flow properties at a given Mach number.
    Returns static pressure, static temperature, density ratios, and area ratio.
    """
    M = mach_number
    g = gamma

    # Pressure ratio P/P0
    p_ratio = (1 + (g - 1) / 2 * M ** 2) ** (-g / (g - 1))

    # Temperature ratio T/T0
    t_ratio = (1 + (g - 1) / 2 * M ** 2) ** (-1)

    # Density ratio ρ/ρ0
    rho_ratio = (1 + (g - 1) / 2 * M ** 2) ** (-1 / (g - 1))

    # Area ratio A/A*
    a_ratio = (1 / M) * ((2 / (g + 1)) * (1 + (g - 1) / 2 * M ** 2)) ** ((g + 1) / (2 * (g - 1)))

    static_p = stagnation_pressure_pa * p_ratio
    static_t = stagnation_temperature_k * t_ratio

    return {
        "mach_number": M,
        "pressure_ratio_P_P0": round(p_ratio, 6),
        "temperature_ratio_T_T0": round(t_ratio, 6),
        "density_ratio": round(rho_ratio, 6),
        "area_ratio_A_Astar": round(a_ratio, 6),
        "static_pressure_Pa": round(static_p, 2),
        "static_temperature_K": round(static_t, 2),
    }


@tool
def calculate_thermal_resistance(
    geometry: str = "flat_wall",
    thickness_m: float = 0.01,
    thermal_conductivity: float = 45.0,
    area_m2: float = 0.01,
    convection_h: float = 100.0,
) -> dict[str, Any]:
    """
    Calculate thermal resistance for conduction and convection.
    Geometries: flat_wall, cylinder, sphere.
    Returns conduction resistance, convection resistance, and total.
    """
    if geometry == "flat_wall":
        R_cond = thickness_m / (thermal_conductivity * area_m2)
    elif geometry == "cylinder":
        # Hollow cylinder: R = ln(r_out/r_in) / (2π k L)
        r_in = thickness_m  # reuse as inner radius
        r_out = r_in * 1.2  # 20% wall thickness
        L = area_m2  # reuse as length
        R_cond = math.log(r_out / r_in) / (2 * math.pi * thermal_conductivity * L)
    else:
        R_cond = thickness_m / (thermal_conductivity * area_m2)

    R_conv = 1.0 / (convection_h * area_m2)
    R_total = R_cond + R_conv

    return {
        "conduction_resistance_C_W": round(R_cond, 6),
        "convection_resistance_C_W": round(R_conv, 6),
        "total_resistance_C_W": round(R_total, 6),
        "geometry": geometry,
        "thermal_conductivity_W_mK": thermal_conductivity,
        "convection_h_W_m2K": convection_h,
    }


@tool
def calculate_safety_factor(
    applied_stress_pa: float,
    yield_strength_pa: float,
    stress_concentration_factor: float = 1.0,
    load_factor: float = 1.0,
) -> dict[str, Any]:
    """
    Calculate structural safety factor and reliability assessment.
    Returns safety factor, status, and recommendations.
    """
    effective_stress = applied_stress_pa * stress_concentration_factor * load_factor
    sf = yield_strength_pa / max(effective_stress, 1.0)

    if sf >= 4.0:
        status = "over_designed"
        assessment = "Very conservative design — consider weight reduction"
    elif sf >= 2.0:
        status = "safe"
        assessment = "Adequate safety margin for static loading"
    elif sf >= 1.5:
        status = "marginal"
        assessment = "Minimum acceptable for non-critical static loads"
    else:
        status = "unsafe"
        assessment = "INSUFFICIENT safety factor — redesign required"

    return {
        "safety_factor": round(sf, 3),
        "status": status,
        "assessment": assessment,
        "applied_stress_Pa": applied_stress_pa,
        "effective_stress_Pa": round(effective_stress, 0),
        "yield_strength_Pa": yield_strength_pa,
        "stress_concentration_factor": stress_concentration_factor,
    }


@tool
def unit_converter(
    value: float,
    from_unit: str,
    to_unit: str,
) -> dict[str, Any]:
    """
    Convert between common engineering units.
    Supports: temperature (C/F/K), pressure (Pa/bar/psi/atm),
    length (m/cm/mm/in/ft), force (N/kN/lbf), power (W/kW/hp/BTU_hr).
    """
    conversions = {
        # Pressure (to Pa)
        "pa": 1.0, "bar": 1e5, "psi": 6894.76, "atm": 101325.0, "kpa": 1e3, "mpa": 1e6,
        # Length (to m)
        "m": 1.0, "cm": 0.01, "mm": 0.001, "in": 0.0254, "ft": 0.3048, "km": 1000.0,
        # Force (to N)
        "n": 1.0, "kn": 1000.0, "lbf": 4.44822, "kgf": 9.80665,
        # Power (to W)
        "w": 1.0, "kw": 1000.0, "hp": 745.7, "btu_hr": 0.29307,
        # Energy (to J)
        "j": 1.0, "kj": 1000.0, "mj": 1e6, "cal": 4.184, "kcal": 4184.0, "kwh": 3.6e6,
        # Mass (to kg)
        "kg": 1.0, "g": 0.001, "lb": 0.453592, "oz": 0.0283495,
    }

    from_l = from_unit.lower()
    to_l = to_unit.lower()

    # Handle temperature separately
    temp_units = {"c", "f", "k"}
    if from_l in temp_units and to_l in temp_units:
        if from_l == "c":
            temp_k = value + 273.15
        elif from_l == "f":
            temp_k = (value - 32) * 5 / 9 + 273.15
        else:
            temp_k = value

        if to_l == "c":
            result = temp_k - 273.15
        elif to_l == "f":
            result = (temp_k - 273.15) * 9 / 5 + 32
        else:
            result = temp_k

        return {"original_value": value, "from_unit": from_unit, "converted_value": round(result, 4), "to_unit": to_unit}

    if from_l not in conversions or to_l not in conversions:
        return {"error": f"Unknown units: {from_unit} or {to_unit}", "supported_units": list(conversions.keys())}

    value_si = value * conversions[from_l]
    result = value_si / conversions[to_l]

    return {
        "original_value": value,
        "from_unit": from_unit,
        "converted_value": round(result, 6),
        "to_unit": to_unit,
        "si_value": round(value_si, 6),
    }


# Export all calculator tools
CALCULATOR_TOOLS = [
    calculate_reynolds_number,
    calculate_heat_transfer_coefficient,
    calculate_isentropic_flow,
    calculate_thermal_resistance,
    calculate_safety_factor,
    unit_converter,
]
