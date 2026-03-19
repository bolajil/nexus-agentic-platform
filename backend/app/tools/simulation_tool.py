"""
NEXUS Platform — Physics Simulation Engine
Real engineering equations for heat transfer, propulsion, and electronics cooling.
All calculations use established thermodynamic and mechanical engineering formulas.
"""
from __future__ import annotations

import math
from typing import Any

from langchain_core.tools import tool


# ── Physical Constants ────────────────────────────────────────────────────────

STEFAN_BOLTZMANN = 5.670374419e-8  # W/(m²·K⁴)
GRAVITY = 9.80665                   # m/s²
R_AIR = 287.058                     # J/(kg·K) — specific gas constant for air
GAMMA_AIR = 1.4                     # ratio of specific heats for air
GAMMA_HOT_GAS = 1.2                 # typical for rocket propellant exhaust

# Fluid property lookup table (at ~300 K)
FLUID_PROPERTIES: dict[str, dict[str, float]] = {
    "water": {
        "density": 997.0,       # kg/m³
        "cp": 4182.0,           # J/(kg·K)
        "viscosity": 8.9e-4,    # Pa·s
        "conductivity": 0.606,  # W/(m·K)
        "prandtl": 6.14,
    },
    "air": {
        "density": 1.204,
        "cp": 1005.0,
        "viscosity": 1.81e-5,
        "conductivity": 0.0257,
        "prandtl": 0.713,
    },
    "oil": {
        "density": 870.0,
        "cp": 1900.0,
        "viscosity": 0.04,
        "conductivity": 0.145,
        "prandtl": 490.0,
    },
    "glycol": {
        "density": 1113.0,
        "cp": 3500.0,
        "viscosity": 5.0e-3,
        "conductivity": 0.253,
        "prandtl": 69.0,
    },
}


def heat_exchanger_simulation(
    power_watts: float,
    fluid_type: str = "water",
    flow_rate: float = 0.05,
    inlet_temp_hot: float = 80.0,
    inlet_temp_cold: float = 20.0,
    heat_transfer_area: float = 1.0,
    overall_htc: float = 500.0,
) -> dict[str, Any]:
    """
    Simulate a shell-and-tube or plate heat exchanger.

    Uses the NTU-Effectiveness method (Kays & London):
      NTU = UA / C_min
      ε   = 1 - exp(-NTU(1 + C_r)) / (1 + C_r)   [counter-flow]

    Args:
        power_watts: Target thermal load (W)
        fluid_type: Working fluid (water|air|oil|glycol)
        flow_rate: Mass flow rate (kg/s)
        inlet_temp_hot: Hot-side inlet temperature (°C)
        inlet_temp_cold: Cold-side inlet temperature (°C)
        heat_transfer_area: Heat transfer surface area (m²)
        overall_htc: Overall heat transfer coefficient U (W/m²·K)

    Returns:
        Dictionary with effectiveness, outlet temps, pressure drop, NTU, etc.
    """
    props = FLUID_PROPERTIES.get(fluid_type.lower(), FLUID_PROPERTIES["water"])
    cp = props["cp"]
    density = props["density"]
    viscosity = props["viscosity"]
    conductivity = props["conductivity"]
    prandtl = props["prandtl"]

    # Capacity rates
    C_hot = flow_rate * cp       # W/K
    C_cold = flow_rate * cp      # assume same fluid both sides for simplicity
    C_min = min(C_hot, C_cold)
    C_max = max(C_hot, C_cold)
    C_r = C_min / C_max          # capacity ratio

    # Number of Transfer Units
    U = overall_htc
    A = heat_transfer_area
    NTU = (U * A) / C_min

    # Effectiveness — counter-flow configuration
    if abs(C_r - 1.0) < 1e-6:
        effectiveness = NTU / (1.0 + NTU)
    else:
        exp_term = math.exp(-NTU * (1.0 - C_r))
        effectiveness = (1.0 - exp_term) / (1.0 - C_r * exp_term)

    # Clamp effectiveness to physical limits
    effectiveness = min(effectiveness, 0.99)

    # Maximum possible heat transfer
    delta_T_max = inlet_temp_hot - inlet_temp_cold
    Q_max = C_min * delta_T_max
    Q_actual = effectiveness * Q_max

    # Outlet temperatures
    T_hot_out = inlet_temp_hot - Q_actual / C_hot
    T_cold_out = inlet_temp_cold + Q_actual / C_cold

    # Log Mean Temperature Difference (LMTD)
    delta_T1 = inlet_temp_hot - T_cold_out
    delta_T2 = T_hot_out - inlet_temp_cold
    if abs(delta_T1 - delta_T2) < 1e-6:
        LMTD = delta_T1
    else:
        LMTD = (delta_T1 - delta_T2) / math.log(delta_T1 / max(delta_T2, 0.01))

    # Reynolds number for flow characterization
    hydraulic_diameter = 0.01  # 10 mm assumed channel
    velocity = flow_rate / (density * math.pi * (hydraulic_diameter / 2) ** 2)
    Re = (density * velocity * hydraulic_diameter) / viscosity

    # Nusselt number — Dittus-Boelter equation (turbulent: Re > 10000)
    if Re > 10000:
        Nu = 0.023 * (Re ** 0.8) * (prandtl ** 0.4)
    elif Re > 2300:
        # Gnielinski correlation for transitional flow
        f = (0.790 * math.log(Re) - 1.64) ** (-2)
        Nu = (f / 8.0) * (Re - 1000) * prandtl / (
            1.0 + 12.7 * math.sqrt(f / 8.0) * (prandtl ** (2 / 3) - 1.0)
        )
    else:
        Nu = 3.66  # Laminar, constant wall temperature

    h_internal = Nu * conductivity / hydraulic_diameter

    # Darcy-Weisbach pressure drop
    L = A / (math.pi * hydraulic_diameter)  # estimated tube length
    if Re > 4000:
        f_darcy = 0.3164 * Re ** (-0.25)  # Blasius equation
    else:
        f_darcy = 64.0 / max(Re, 1e-6)

    pressure_drop_pa = f_darcy * (L / hydraulic_diameter) * (density * velocity ** 2) / 2.0

    # Performance gap vs target
    performance_ratio = Q_actual / max(power_watts, 1.0)

    warnings = []
    if Re < 2300:
        warnings.append("Laminar flow regime — consider increasing flow rate for better heat transfer")
    if effectiveness < 0.5:
        warnings.append("Low effectiveness — increase heat transfer area or NTU")
    if pressure_drop_pa > 50000:
        warnings.append("High pressure drop (>0.5 bar) — consider parallel flow arrangement")
    if performance_ratio < 0.9:
        warnings.append(f"Heat exchanger provides {Q_actual:.0f}W but {power_watts:.0f}W required")

    return {
        "effectiveness": round(effectiveness, 4),
        "NTU": round(NTU, 3),
        "capacity_ratio": round(C_r, 4),
        "heat_transferred_W": round(Q_actual, 2),
        "target_power_W": power_watts,
        "performance_ratio": round(performance_ratio, 4),
        "outlet_temp_hot_C": round(T_hot_out, 2),
        "outlet_temp_cold_C": round(T_cold_out, 2),
        "LMTD_K": round(LMTD, 2),
        "pressure_drop_Pa": round(pressure_drop_pa, 1),
        "reynolds_number": round(Re, 0),
        "nusselt_number": round(Nu, 2),
        "convection_coeff_W_m2K": round(h_internal, 1),
        "fluid_velocity_m_s": round(velocity, 4),
        "warnings": warnings,
        "flow_regime": "turbulent" if Re > 4000 else ("transitional" if Re > 2300 else "laminar"),
    }


def rocket_nozzle_simulation(
    thrust_n: float,
    chamber_pressure_pa: float = 3_000_000.0,
    expansion_ratio: float = 8.0,
    chamber_temp_k: float = 3500.0,
    propellant_molar_mass: float = 0.022,
) -> dict[str, Any]:
    """
    Simulate a converging-diverging (de Laval) rocket nozzle.

    Uses isentropic flow relations and rocket thrust equation:
      F = ṁ·Ve + (Pe - Pa)·Ae
      Isp = F / (ṁ·g₀)
      Ve = sqrt(2γ/(γ-1) · R·Tc/M · [1 - (Pe/Pc)^((γ-1)/γ)])

    Args:
        thrust_n: Required thrust (N)
        chamber_pressure_pa: Chamber stagnation pressure (Pa)
        expansion_ratio: Nozzle area ratio Ae/At
        chamber_temp_k: Chamber temperature (K)
        propellant_molar_mass: Molar mass of propellant (kg/mol)

    Returns:
        Dictionary with Isp, exit velocity, throat area, mass flow, etc.
    """
    gamma = GAMMA_HOT_GAS
    R_universal = 8.314  # J/(mol·K)
    R_specific = R_universal / propellant_molar_mass  # J/(kg·K)

    Pc = chamber_pressure_pa
    Tc = chamber_temp_k
    Pa = 101325.0  # ambient pressure (Pa) at sea level

    # Critical (throat) conditions — isentropic choked flow
    T_throat = Tc * (2.0 / (gamma + 1.0))
    P_throat = Pc * (2.0 / (gamma + 1.0)) ** (gamma / (gamma - 1.0))
    rho_throat = P_throat / (R_specific * T_throat)
    a_throat = math.sqrt(gamma * R_specific * T_throat)  # throat speed of sound = exit velocity at throat (Mach 1)

    # Exit Mach number from area-Mach relation (iterative Newton solve)
    def area_mach_ratio(M: float) -> float:
        """Isentropic A/A* relation."""
        return (1.0 / M) * ((2.0 / (gamma + 1.0)) * (1.0 + (gamma - 1.0) / 2.0 * M ** 2)) ** (
            (gamma + 1.0) / (2.0 * (gamma - 1.0))
        )

    # Newton-Raphson solve for exit Mach number
    Me = 3.0  # initial guess for supersonic solution
    for _ in range(100):
        f = area_mach_ratio(Me) - expansion_ratio
        # Numerical derivative
        dM = 1e-6
        df = (area_mach_ratio(Me + dM) - area_mach_ratio(Me - dM)) / (2 * dM)
        if abs(df) < 1e-12:
            break
        Me -= f / df
        Me = max(Me, 1.001)  # stay supersonic

    # Exit pressure and temperature via isentropic relations
    Pe = Pc * (1.0 + (gamma - 1.0) / 2.0 * Me ** 2) ** (-gamma / (gamma - 1.0))
    Te = Tc * (1.0 + (gamma - 1.0) / 2.0 * Me ** 2) ** (-1.0)

    # Exit velocity (isentropic)
    Ve = math.sqrt(
        2.0 * gamma / (gamma - 1.0) * R_specific * Tc
        * (1.0 - (Pe / Pc) ** ((gamma - 1.0) / gamma))
    )

    # Throat area from thrust equation (F = ṁ·Ve + (Pe-Pa)·Ae)
    # ṁ = rho_throat * a_throat * At  →  solve for At
    # F = At * [rho_throat * a_throat * Ve + (Pe - Pa) * expansion_ratio]
    thrust_coefficient_term = rho_throat * a_throat * Ve + (Pe - Pa) * expansion_ratio
    At = thrust_n / max(thrust_coefficient_term, 1e-6)

    # Exit area
    Ae = At * expansion_ratio

    # Mass flow rate
    mass_flow = rho_throat * a_throat * At

    # Specific impulse
    Isp = Ve / GRAVITY  # effective exhaust velocity / g₀

    # Thrust coefficient CF
    CF = thrust_n / (Pc * At)

    # Characteristic velocity c*
    c_star = Pc * At / max(mass_flow, 1e-9)

    # Nozzle throat and exit diameters
    d_throat = 2.0 * math.sqrt(At / math.pi)
    d_exit = 2.0 * math.sqrt(Ae / math.pi)

    warnings = []
    if Pe / Pa < 0.3:
        warnings.append("Significant over-expansion — flow separation likely; reduce expansion ratio")
    if Pe / Pa > 3.0:
        warnings.append("Under-expanded nozzle — increase expansion ratio for better efficiency")
    if Isp < 200:
        warnings.append("Low Isp — consider higher chamber temperature or lighter propellant")
    if At < 1e-6:
        warnings.append("Very small throat area — verify input parameters")

    return {
        "thrust_N": round(thrust_n, 2),
        "Isp_s": round(Isp, 1),
        "exit_velocity_m_s": round(Ve, 1),
        "mass_flow_kg_s": round(mass_flow, 6),
        "throat_area_m2": round(At, 8),
        "exit_area_m2": round(Ae, 6),
        "throat_diameter_m": round(d_throat, 6),
        "exit_diameter_m": round(d_exit, 4),
        "expansion_ratio": round(expansion_ratio, 2),
        "exit_mach_number": round(Me, 3),
        "exit_pressure_Pa": round(Pe, 0),
        "exit_temperature_K": round(Te, 1),
        "chamber_pressure_Pa": Pc,
        "chamber_temperature_K": Tc,
        "thrust_coefficient_CF": round(CF, 4),
        "characteristic_velocity_c_star_m_s": round(c_star, 1),
        "warnings": warnings,
    }


def electronics_cooling_simulation(
    power_w: float,
    ambient_temp_c: float = 25.0,
    heatsink_area_m2: float = 0.01,
    heatsink_fin_efficiency: float = 0.85,
    junction_to_case_resistance: float = 0.5,
    case_to_heatsink_resistance: float = 0.1,
    airflow_velocity_m_s: float = 2.0,
    component_type: str = "CPU",
) -> dict[str, Any]:
    """
    Simulate electronics thermal management for a power component.

    Uses thermal resistance network:
      T_junction = T_ambient + Q * (R_jc + R_cs + R_sa)
      R_sa = 1 / (h * A_eff)

    Forced convection coefficient via flat-plate correlation:
      Nu_L = 0.664 * Re_L^0.5 * Pr^(1/3)  (laminar)
      Nu_L = 0.037 * Re_L^0.8 * Pr^(1/3)  (turbulent)

    Args:
        power_w: Component power dissipation (W)
        ambient_temp_c: Ambient/coolant inlet temperature (°C)
        heatsink_area_m2: Total heatsink surface area (m²)
        heatsink_fin_efficiency: Fin efficiency factor (0-1)
        junction_to_case_resistance: Rjc in °C/W
        case_to_heatsink_resistance: Rcs (thermal interface material) in °C/W
        airflow_velocity_m_s: Cooling air velocity (m/s)
        component_type: Component identifier for reporting

    Returns:
        Dictionary with junction temp, thermal resistance chain, cooling metrics.
    """
    air_props = FLUID_PROPERTIES["air"]
    rho = air_props["density"]
    cp_air = air_props["cp"]
    mu = air_props["viscosity"]
    k_air = air_props["conductivity"]
    Pr = air_props["prandtl"]

    # Characteristic length for heatsink (assume square base)
    L_char = math.sqrt(heatsink_area_m2 / max(heatsink_fin_efficiency, 0.01))

    # Reynolds number
    Re_L = rho * airflow_velocity_m_s * L_char / mu

    # Nusselt number — flat plate correlation
    if Re_L < 5e5:
        # Laminar boundary layer (Pohlhausen solution)
        Nu_L = 0.664 * Re_L ** 0.5 * Pr ** (1.0 / 3.0)
    else:
        # Turbulent flat plate
        Nu_L = (0.037 * Re_L ** 0.8 - 871.0) * Pr ** (1.0 / 3.0)

    h_conv = Nu_L * k_air / L_char

    # Effective area with fin efficiency
    A_eff = heatsink_area_m2 * heatsink_fin_efficiency

    # Heatsink-to-ambient thermal resistance
    R_sa = 1.0 / (h_conv * A_eff)

    # Total thermal resistance
    R_total = junction_to_case_resistance + case_to_heatsink_resistance + R_sa

    # Junction temperature
    T_junction = ambient_temp_c + power_w * R_total
    T_case = ambient_temp_c + power_w * (case_to_heatsink_resistance + R_sa)
    T_heatsink_base = ambient_temp_c + power_w * R_sa

    # Fan power estimation (if forced convection)
    # Fan power ≈ ΔP * Q_vol / η_fan
    # ΔP ≈ 0.5 * ρ * v² * (L/Dh) * f   (rough estimate for fin channels)
    fan_power_w = 0.0
    if airflow_velocity_m_s > 0.5:
        # Rough fan power model: P_fan ∝ v³ for centrifugal fans
        nominal_fan_power = 5.0  # W at reference 3 m/s
        fan_power_w = nominal_fan_power * (airflow_velocity_m_s / 3.0) ** 3

    # Cooling capacity — max power this system can handle at Tj_max = 125°C
    T_junction_max = 125.0
    Q_max_capability = (T_junction_max - ambient_temp_c) / max(R_total, 1e-6)

    # Thermal margin
    thermal_margin_c = T_junction_max - T_junction
    margin_pct = thermal_margin_c / (T_junction_max - ambient_temp_c) * 100.0

    # System COP (coefficient of performance) for cooling
    # COP_cooling = Q_dissipated / W_fan  (higher is better)
    cop = power_w / max(fan_power_w, 0.001)

    warnings = []
    if T_junction > 100.0:
        warnings.append(f"Junction temperature {T_junction:.1f}°C is dangerously high — increase cooling")
    if T_junction > 85.0:
        warnings.append(f"Junction temperature {T_junction:.1f}°C exceeds recommended 85°C for many components")
    if margin_pct < 15.0:
        warnings.append(f"Low thermal margin {margin_pct:.1f}% — reliability risk under transient loads")
    if R_sa > 5.0:
        warnings.append("Very high heatsink-to-ambient resistance — increase heatsink area or airflow")
    if Re_L < 1000:
        warnings.append("Very low Reynolds number — natural convection may be better than forced convection at this velocity")

    return {
        "component_type": component_type,
        "junction_temperature_C": round(T_junction, 2),
        "case_temperature_C": round(T_case, 2),
        "heatsink_base_temperature_C": round(T_heatsink_base, 2),
        "ambient_temperature_C": ambient_temp_c,
        "thermal_margin_C": round(thermal_margin_c, 2),
        "thermal_margin_percent": round(margin_pct, 1),
        "R_junction_to_case_C_W": junction_to_case_resistance,
        "R_case_to_heatsink_C_W": case_to_heatsink_resistance,
        "R_heatsink_to_ambient_C_W": round(R_sa, 4),
        "R_total_C_W": round(R_total, 4),
        "convection_coefficient_W_m2K": round(h_conv, 2),
        "nusselt_number": round(Nu_L, 2),
        "reynolds_number": round(Re_L, 0),
        "fan_power_W": round(fan_power_w, 2),
        "cooling_COP": round(cop, 2),
        "max_cooling_capacity_W": round(Q_max_capability, 1),
        "power_dissipated_W": power_w,
        "warnings": warnings,
    }


def structural_stress_simulation(
    applied_force_n: float,
    cross_section_area_m2: float,
    material: str = "steel",
    beam_length_m: float = 1.0,
    moment_of_inertia_m4: float = 8.33e-6,
) -> dict[str, Any]:
    """
    Simulate structural stress analysis using classical mechanics.

    Computes: axial stress, bending stress, Von Mises equivalent stress,
    safety factor, deflection, and natural frequency.

    Args:
        applied_force_n: Applied axial/transverse force (N)
        cross_section_area_m2: Cross-sectional area (m²)
        material: Material identifier (steel|aluminum|titanium|carbon_fiber)
        beam_length_m: Beam span length (m)
        moment_of_inertia_m4: Second moment of area (m⁴)
    """
    material_props = {
        "steel": {"E": 200e9, "yield_strength": 250e6, "density": 7850, "poisson": 0.3},
        "aluminum": {"E": 69e9, "yield_strength": 270e6, "density": 2700, "poisson": 0.33},
        "titanium": {"E": 116e9, "yield_strength": 880e6, "density": 4510, "poisson": 0.34},
        "carbon_fiber": {"E": 150e9, "yield_strength": 600e6, "density": 1600, "poisson": 0.27},
    }

    props = material_props.get(material.lower(), material_props["steel"])
    E = props["E"]
    sigma_yield = props["yield_strength"]
    rho = props["density"]

    # Axial stress (tension/compression)
    sigma_axial = applied_force_n / cross_section_area_m2

    # Bending moment at mid-span for simply supported beam with central load
    M_max = applied_force_n * beam_length_m / 4.0

    # Distance to neutral axis (for circular cross-section estimate)
    c = math.sqrt(cross_section_area_m2 / math.pi)  # radius of equivalent circle

    # Bending stress
    sigma_bending = M_max * c / moment_of_inertia_m4

    # Combined stress (simplified — axial + bending)
    sigma_combined = abs(sigma_axial) + abs(sigma_bending)

    # Shear stress at neutral axis for rectangular cross-section: τ = 3V/(2A)
    V_shear = applied_force_n / 2.0
    tau_shear = 1.5 * V_shear / cross_section_area_m2

    # Von Mises equivalent stress
    sigma_vm = math.sqrt(sigma_combined ** 2 + 3.0 * tau_shear ** 2)

    # Safety factor
    safety_factor = sigma_yield / max(sigma_vm, 1.0)

    # Mid-span deflection for simply supported beam: δ = FL³/(48EI)
    deflection_m = applied_force_n * beam_length_m ** 3 / (48.0 * E * moment_of_inertia_m4)

    # Natural frequency for simply supported beam: f₁ = π²/(2L²) * sqrt(EI/(ρA))
    linear_density = rho * cross_section_area_m2
    f_natural_hz = (math.pi ** 2 / (2.0 * beam_length_m ** 2)) * math.sqrt(
        E * moment_of_inertia_m4 / max(linear_density, 1e-9)
    )

    warnings = []
    if safety_factor < 1.5:
        warnings.append(f"CRITICAL: Safety factor {safety_factor:.2f} is below minimum 1.5 — redesign required")
    elif safety_factor < 2.0:
        warnings.append(f"Low safety factor {safety_factor:.2f} — consider increasing cross-section")
    if deflection_m > beam_length_m / 300.0:
        warnings.append(f"Excessive deflection {deflection_m*1000:.2f}mm — check serviceability limit")
    if sigma_vm > sigma_yield:
        warnings.append("Von Mises stress EXCEEDS yield strength — plastic deformation will occur")

    return {
        "material": material,
        "axial_stress_Pa": round(sigma_axial, 0),
        "bending_stress_Pa": round(sigma_bending, 0),
        "shear_stress_Pa": round(tau_shear, 0),
        "von_mises_stress_Pa": round(sigma_vm, 0),
        "yield_strength_Pa": sigma_yield,
        "safety_factor": round(safety_factor, 3),
        "mid_span_deflection_mm": round(deflection_m * 1000, 4),
        "natural_frequency_Hz": round(f_natural_hz, 2),
        "elastic_modulus_Pa": E,
        "warnings": warnings,
    }


# ── LangChain Tool Wrappers ───────────────────────────────────────────────────

@tool
def run_heat_exchanger_simulation(
    power_watts: float,
    fluid_type: str = "water",
    flow_rate: float = 0.05,
    inlet_temp_hot: float = 80.0,
    inlet_temp_cold: float = 20.0,
    heat_transfer_area: float = 1.0,
    overall_htc: float = 500.0,
) -> dict:
    """
    Run a heat exchanger simulation using the NTU-effectiveness method.
    Returns effectiveness, NTU, outlet temperatures, pressure drop, and flow regime.
    """
    return heat_exchanger_simulation(
        power_watts, fluid_type, flow_rate,
        inlet_temp_hot, inlet_temp_cold, heat_transfer_area, overall_htc
    )


@tool
def run_rocket_nozzle_simulation(
    thrust_n: float,
    chamber_pressure_pa: float = 3_000_000.0,
    expansion_ratio: float = 8.0,
    chamber_temp_k: float = 3500.0,
    propellant_molar_mass: float = 0.022,
) -> dict:
    """
    Simulate a de Laval converging-diverging rocket nozzle.
    Returns Isp, exit velocity, throat area, mass flow, and thrust coefficient.
    """
    return rocket_nozzle_simulation(
        thrust_n, chamber_pressure_pa, expansion_ratio,
        chamber_temp_k, propellant_molar_mass
    )


@tool
def run_electronics_cooling_simulation(
    power_w: float,
    ambient_temp_c: float = 25.0,
    heatsink_area_m2: float = 0.01,
    airflow_velocity_m_s: float = 2.0,
    junction_to_case_resistance: float = 0.5,
    component_type: str = "CPU",
) -> dict:
    """
    Simulate electronics thermal management using thermal resistance network.
    Returns junction temperature, thermal resistance chain, fan power, and COP.
    """
    return electronics_cooling_simulation(
        power_w, ambient_temp_c, heatsink_area_m2,
        0.85, junction_to_case_resistance, 0.1,
        airflow_velocity_m_s, component_type
    )


@tool
def run_structural_stress_simulation(
    applied_force_n: float,
    cross_section_area_m2: float,
    material: str = "steel",
    beam_length_m: float = 1.0,
) -> dict:
    """
    Perform structural stress analysis using classical beam theory.
    Returns Von Mises stress, safety factor, deflection, and natural frequency.
    """
    # Estimate moment of inertia for circular cross-section
    r = math.sqrt(cross_section_area_m2 / math.pi)
    I = math.pi * r ** 4 / 4.0
    return structural_stress_simulation(
        applied_force_n, cross_section_area_m2, material, beam_length_m, I
    )


# Export all simulation tools as a list for agent use
SIMULATION_TOOLS = [
    run_heat_exchanger_simulation,
    run_rocket_nozzle_simulation,
    run_electronics_cooling_simulation,
    run_structural_stress_simulation,
]
