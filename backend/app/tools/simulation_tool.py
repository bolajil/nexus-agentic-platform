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


# ── Fluid Dynamics Simulation ────────────────────────────────────────────────

def pipe_flow_simulation(
    flow_rate_m3_s: float,
    pipe_diameter_m: float = 0.1,
    pipe_length_m: float = 100.0,
    fluid_type: str = "water",
    pipe_roughness_m: float = 0.000045,  # Commercial steel
    elevation_change_m: float = 0.0,
    num_elbows: int = 0,
    num_valves: int = 0,
) -> dict[str, Any]:
    """
    Simulate pipe flow using Darcy-Weisbach equation and Colebrook-White friction factor.

    Calculates: pressure drop, head loss, pump power required, velocity profile.

    Uses:
      ΔP = f·(L/D)·(ρV²/2)  — Darcy-Weisbach
      1/√f = -2·log₁₀(ε/3.7D + 2.51/(Re·√f))  — Colebrook-White

    Args:
        flow_rate_m3_s: Volumetric flow rate (m³/s)
        pipe_diameter_m: Internal pipe diameter (m)
        pipe_length_m: Total pipe length (m)
        fluid_type: Working fluid (water|oil|glycol|air)
        pipe_roughness_m: Absolute pipe roughness ε (m)
        elevation_change_m: Height change (positive = uphill)
        num_elbows: Number of 90° elbows
        num_valves: Number of gate valves
    """
    props = FLUID_PROPERTIES.get(fluid_type.lower(), FLUID_PROPERTIES["water"])
    rho = props["density"]
    mu = props["viscosity"]

    # Cross-sectional area and velocity
    A = math.pi * (pipe_diameter_m / 2) ** 2
    V = flow_rate_m3_s / A

    # Reynolds number
    Re = rho * V * pipe_diameter_m / mu

    # Friction factor via Colebrook-White (iterative)
    epsilon = pipe_roughness_m
    D = pipe_diameter_m

    if Re < 2300:
        # Laminar flow
        f = 64.0 / max(Re, 1)
        flow_regime = "laminar"
    else:
        # Turbulent — solve Colebrook-White iteratively
        f = 0.02  # initial guess
        for _ in range(50):
            rhs = -2.0 * math.log10(epsilon / (3.7 * D) + 2.51 / (Re * math.sqrt(f)))
            f_new = 1.0 / (rhs ** 2)
            if abs(f_new - f) < 1e-8:
                break
            f = f_new
        flow_regime = "turbulent"

    # Major head loss (friction)
    h_major = f * (pipe_length_m / D) * (V ** 2 / (2 * GRAVITY))

    # Minor losses (fittings)
    K_elbow = 0.9  # 90° elbow
    K_valve = 0.2  # gate valve fully open
    K_total = num_elbows * K_elbow + num_valves * K_valve
    h_minor = K_total * (V ** 2 / (2 * GRAVITY))

    # Total head loss
    h_total = h_major + h_minor + elevation_change_m

    # Pressure drop
    delta_P = rho * GRAVITY * h_total

    # Pump power required (assuming 75% pump efficiency)
    pump_efficiency = 0.75
    pump_power_w = (rho * GRAVITY * flow_rate_m3_s * h_total) / pump_efficiency

    # Velocity profile (for turbulent pipe flow)
    # u/u_max = (1 - r/R)^(1/n), n ≈ 7 for Re ~ 10^5
    n_profile = 7.0 if Re > 1e5 else (6.0 if Re > 1e4 else 8.0)
    u_max = V * (n_profile + 1) * (2 * n_profile + 1) / (2 * n_profile ** 2)

    warnings = []
    if V > 3.0 and fluid_type == "water":
        warnings.append(f"High velocity {V:.2f} m/s may cause erosion in water pipes")
    if Re > 2300 and Re < 4000:
        warnings.append("Transitional flow regime — results have higher uncertainty")
    if h_total < 0:
        warnings.append("Negative head — flow is gravity-driven, no pump needed")
    if delta_P > 1e6:
        warnings.append("Very high pressure drop (>10 bar) — consider larger pipe diameter")

    return {
        "flow_rate_m3_s": flow_rate_m3_s,
        "velocity_m_s": round(V, 4),
        "reynolds_number": round(Re, 0),
        "flow_regime": flow_regime,
        "friction_factor": round(f, 6),
        "major_head_loss_m": round(h_major, 3),
        "minor_head_loss_m": round(h_minor, 3),
        "total_head_loss_m": round(h_total, 3),
        "pressure_drop_Pa": round(delta_P, 0),
        "pressure_drop_bar": round(delta_P / 1e5, 4),
        "pump_power_W": round(pump_power_w, 1),
        "pump_power_kW": round(pump_power_w / 1000, 3),
        "centerline_velocity_m_s": round(u_max, 4),
        "pipe_diameter_m": pipe_diameter_m,
        "pipe_length_m": pipe_length_m,
        "warnings": warnings,
    }


def centrifugal_pump_simulation(
    flow_rate_m3_s: float,
    head_required_m: float,
    impeller_diameter_m: float = 0.2,
    rotational_speed_rpm: float = 1750.0,
    fluid_type: str = "water",
) -> dict[str, Any]:
    """
    Simulate centrifugal pump performance using affinity laws and specific speed.

    Affinity Laws:
      Q₂/Q₁ = N₂/N₁
      H₂/H₁ = (N₂/N₁)²
      P₂/P₁ = (N₂/N₁)³

    Specific Speed: Ns = N·√Q / H^0.75  (characterizes pump type)

    Args:
        flow_rate_m3_s: Required flow rate (m³/s)
        head_required_m: Total dynamic head (m)
        impeller_diameter_m: Pump impeller diameter (m)
        rotational_speed_rpm: Shaft speed (RPM)
        fluid_type: Working fluid
    """
    props = FLUID_PROPERTIES.get(fluid_type.lower(), FLUID_PROPERTIES["water"])
    rho = props["density"]

    N = rotational_speed_rpm
    Q = flow_rate_m3_s
    H = head_required_m

    # Specific speed (metric units: N in RPM, Q in m³/s, H in m)
    Ns = N * math.sqrt(Q) / (H ** 0.75) if H > 0 else 0

    # Classify pump type by specific speed
    if Ns < 25:
        pump_type = "radial_flow"
        efficiency_base = 0.70
    elif Ns < 75:
        pump_type = "mixed_flow"
        efficiency_base = 0.82
    else:
        pump_type = "axial_flow"
        efficiency_base = 0.85

    # Efficiency correction for size (larger pumps more efficient)
    size_factor = min(1.0, 0.8 + 0.2 * (Q / 0.1))
    eta_pump = efficiency_base * size_factor

    # Hydraulic power
    P_hydraulic = rho * GRAVITY * Q * H

    # Shaft power
    P_shaft = P_hydraulic / eta_pump

    # Impeller tip speed
    omega = N * 2 * math.pi / 60
    u_tip = omega * impeller_diameter_m / 2

    # Head coefficient (ψ = gH / u²)
    psi = GRAVITY * H / (u_tip ** 2) if u_tip > 0 else 0

    # Flow coefficient (φ = Q / (π·D²·u/4))
    phi = Q / (math.pi * impeller_diameter_m ** 2 * u_tip / 4) if u_tip > 0 else 0

    # NPSH required (approximate)
    NPSH_r = 0.3 * (N / 1000) ** 1.5 * (Q * 1000) ** 0.5

    warnings = []
    if Ns < 10:
        warnings.append("Very low specific speed — consider positive displacement pump")
    if eta_pump < 0.6:
        warnings.append(f"Low efficiency {eta_pump:.0%} — pump may be poorly matched to duty")
    if u_tip > 40:
        warnings.append(f"High tip speed {u_tip:.1f} m/s — cavitation and wear risk")
    if psi > 1.2:
        warnings.append("High head coefficient — check impeller design")

    return {
        "flow_rate_m3_s": Q,
        "head_m": H,
        "specific_speed_Ns": round(Ns, 2),
        "pump_type": pump_type,
        "efficiency": round(eta_pump, 4),
        "hydraulic_power_W": round(P_hydraulic, 1),
        "shaft_power_W": round(P_shaft, 1),
        "shaft_power_kW": round(P_shaft / 1000, 3),
        "impeller_tip_speed_m_s": round(u_tip, 2),
        "head_coefficient_psi": round(psi, 4),
        "flow_coefficient_phi": round(phi, 4),
        "NPSH_required_m": round(NPSH_r, 2),
        "rotational_speed_rpm": N,
        "warnings": warnings,
    }


# ── Mechanisms Simulation ────────────────────────────────────────────────────

def gear_train_simulation(
    input_torque_nm: float,
    input_speed_rpm: float,
    gear_ratio: float,
    module_mm: float = 2.0,
    pressure_angle_deg: float = 20.0,
    num_stages: int = 1,
    gear_material: str = "steel",
) -> dict[str, Any]:
    """
    Simulate spur gear train performance.

    Calculates: output torque, output speed, efficiency, gear stresses, 
    contact ratio, and face width requirements.

    Lewis Equation for bending stress: σ = Ft / (b·m·Y)
    Hertzian contact stress: σ_H = √(Ft·K / (b·d·I))

    Args:
        input_torque_nm: Input shaft torque (N·m)
        input_speed_rpm: Input shaft speed (RPM)
        gear_ratio: Total gear ratio (>1 = speed reduction)
        module_mm: Gear module in mm (tooth size parameter)
        pressure_angle_deg: Pressure angle (typically 20°)
        num_stages: Number of gear stages
        gear_material: Material (steel|bronze|nylon)
    """
    material_props = {
        "steel": {"allowable_bending": 250e6, "allowable_contact": 1200e6, "efficiency": 0.98},
        "bronze": {"allowable_bending": 80e6, "allowable_contact": 400e6, "efficiency": 0.95},
        "nylon": {"allowable_bending": 40e6, "allowable_contact": 100e6, "efficiency": 0.92},
    }

    props = material_props.get(gear_material.lower(), material_props["steel"])
    eta_stage = props["efficiency"]
    sigma_allow_bend = props["allowable_bending"]
    sigma_allow_contact = props["allowable_contact"]

    # Total efficiency
    eta_total = eta_stage ** num_stages

    # Output calculations
    output_speed_rpm = input_speed_rpm / gear_ratio
    output_torque_nm = input_torque_nm * gear_ratio * eta_total

    # Power
    omega_in = input_speed_rpm * 2 * math.pi / 60
    P_input = input_torque_nm * omega_in
    P_output = P_input * eta_total

    # Gear geometry (assuming single stage for stress calc)
    m = module_mm / 1000  # convert to meters
    phi = math.radians(pressure_angle_deg)

    # Estimate pinion teeth for reasonable size
    z_pinion = max(17, int(20 / math.sqrt(gear_ratio)))  # min teeth to avoid undercut
    z_gear = int(z_pinion * gear_ratio)

    # Pitch diameters
    d_pinion = m * z_pinion
    d_gear = m * z_gear

    # Tangential force at pinion
    Ft = 2 * input_torque_nm / d_pinion if d_pinion > 0 else 0

    # Lewis form factor (approximate for 20° pressure angle)
    Y = 0.154 - 0.912 / z_pinion

    # Required face width from bending stress
    # σ = Ft / (b·m·Y) → b = Ft / (σ·m·Y)
    b_required = Ft / (sigma_allow_bend * m * Y) if (m * Y) > 0 else 0.01
    b_recommended = max(b_required * 1.5, 8 * m)  # safety factor + min width

    # Bending stress with recommended face width
    sigma_bending = Ft / (b_recommended * m * Y) if (b_recommended * m * Y) > 0 else 0

    # Contact ratio (should be > 1.2 for smooth operation)
    # CR ≈ 1.88 - 3.2(1/z1 + 1/z2) for 20° PA
    contact_ratio = 1.88 - 3.2 * (1/z_pinion + 1/z_gear)

    # Pitch line velocity
    v_pitch = d_pinion * omega_in / 2

    warnings = []
    if contact_ratio < 1.2:
        warnings.append(f"Low contact ratio {contact_ratio:.2f} — gear noise likely")
    if z_pinion < 17:
        warnings.append("Pinion teeth < 17 — undercut will occur, use profile shift")
    if v_pitch > 25:
        warnings.append(f"High pitch velocity {v_pitch:.1f} m/s — precision gears required")
    if sigma_bending > sigma_allow_bend * 0.8:
        warnings.append("Bending stress approaching allowable — increase face width")

    return {
        "input_torque_Nm": input_torque_nm,
        "input_speed_rpm": input_speed_rpm,
        "output_torque_Nm": round(output_torque_nm, 3),
        "output_speed_rpm": round(output_speed_rpm, 2),
        "gear_ratio": gear_ratio,
        "efficiency": round(eta_total, 4),
        "input_power_W": round(P_input, 1),
        "output_power_W": round(P_output, 1),
        "pinion_teeth": z_pinion,
        "gear_teeth": z_gear,
        "pinion_diameter_mm": round(d_pinion * 1000, 2),
        "gear_diameter_mm": round(d_gear * 1000, 2),
        "tangential_force_N": round(Ft, 2),
        "bending_stress_Pa": round(sigma_bending, 0),
        "allowable_bending_Pa": sigma_allow_bend,
        "face_width_required_mm": round(b_required * 1000, 2),
        "face_width_recommended_mm": round(b_recommended * 1000, 2),
        "contact_ratio": round(contact_ratio, 3),
        "pitch_velocity_m_s": round(v_pitch, 2),
        "module_mm": module_mm,
        "warnings": warnings,
    }


def four_bar_linkage_simulation(
    crank_length_m: float,
    coupler_length_m: float,
    rocker_length_m: float,
    ground_length_m: float,
    crank_speed_rpm: float = 60.0,
    crank_angle_deg: float = 0.0,
) -> dict[str, Any]:
    """
    Simulate four-bar linkage kinematics using Grashof criterion and position analysis.

    Grashof Criterion: s + l ≤ p + q for continuous rotation
    Position Analysis: Law of cosines for coupler and rocker angles

    Args:
        crank_length_m: Crank (input) link length (m)
        coupler_length_m: Coupler (connecting) link length (m)
        rocker_length_m: Rocker (output) link length (m)
        ground_length_m: Ground (fixed) link length (m)
        crank_speed_rpm: Crank rotational speed (RPM)
        crank_angle_deg: Current crank angle from ground (degrees)
    """
    a = crank_length_m      # crank
    b = coupler_length_m    # coupler
    c = rocker_length_m     # rocker
    d = ground_length_m     # ground

    links = sorted([a, b, c, d])
    s, p, q, l = links[0], links[1], links[2], links[3]

    # Grashof criterion
    is_grashof = (s + l) <= (p + q)

    # Classify linkage type
    if is_grashof:
        if s == a:
            linkage_type = "crank-rocker"
        elif s == d:
            linkage_type = "double-crank"
        elif s == b:
            linkage_type = "double-rocker"
        else:
            linkage_type = "crank-rocker"
    else:
        linkage_type = "triple-rocker"

    # Position analysis at given crank angle
    theta2 = math.radians(crank_angle_deg)
    omega2 = crank_speed_rpm * 2 * math.pi / 60

    # Solve for rocker angle (theta4) using loop closure
    # Using complex number method
    # d + c·e^(iθ4) = a·e^(iθ2) + b·e^(iθ3)

    # Position of crank end (point B)
    Bx = a * math.cos(theta2)
    By = a * math.sin(theta2)

    # Distance from B to rocker pivot (point D at origin shifted by d)
    Dx = d
    Dy = 0
    BD = math.sqrt((Dx - Bx) ** 2 + (Dy - By) ** 2)

    # Check if position is valid
    if BD > (b + c) or BD < abs(b - c):
        return {
            "valid_position": False,
            "error": "Linkage cannot reach this position — links cannot connect",
            "crank_angle_deg": crank_angle_deg,
            "linkage_type": linkage_type,
            "is_grashof": is_grashof,
            "warnings": ["Invalid position — crank angle outside working range"],
        }

    # Solve triangle BDC for angles
    # cos(∠DBC) = (BD² + b² - c²) / (2·BD·b)
    cos_DBC = (BD ** 2 + b ** 2 - c ** 2) / (2 * BD * b) if BD * b > 0 else 0
    cos_DBC = max(-1, min(1, cos_DBC))  # clamp for numerical stability
    angle_DBC = math.acos(cos_DBC)

    # Angle from B to D
    angle_BD = math.atan2(Dy - By, Dx - Bx)

    # Coupler angle (two solutions — take the "open" configuration)
    theta3 = angle_BD + angle_DBC

    # Rocker angle
    Cx = Bx + b * math.cos(theta3)
    Cy = By + b * math.sin(theta3)
    theta4 = math.atan2(Cy - Dy, Cx - Dx)

    # Velocities (using velocity polygon method)
    # ω3 and ω4 from velocity equations
    # Simplified: ω4 ≈ (a/c) · sin(θ2-θ3)/sin(θ4-θ3) · ω2

    denom = c * math.sin(theta4 - theta3)
    if abs(denom) > 1e-9:
        omega4 = (a * omega2 * math.sin(theta2 - theta3)) / denom
        omega3 = (a * omega2 * math.sin(theta2 - theta4)) / (b * math.sin(theta3 - theta4))
    else:
        omega4 = 0
        omega3 = 0

    # Mechanical advantage (approximate)
    mech_advantage = abs(omega2 / omega4) if abs(omega4) > 1e-9 else float('inf')

    # Transmission angle (should be 40°-140° for good force transmission)
    trans_angle = abs(math.degrees(theta3 - theta4))
    if trans_angle > 90:
        trans_angle = 180 - trans_angle

    warnings = []
    if not is_grashof:
        warnings.append("Non-Grashof linkage — crank cannot make full rotation")
    if trans_angle < 40:
        warnings.append(f"Poor transmission angle {trans_angle:.1f}° — force transmission inefficient")
    if abs(omega4) < 0.01 * abs(omega2):
        warnings.append("Near toggle position — very high mechanical advantage but poor controllability")

    return {
        "valid_position": True,
        "crank_angle_deg": crank_angle_deg,
        "coupler_angle_deg": round(math.degrees(theta3), 2),
        "rocker_angle_deg": round(math.degrees(theta4), 2),
        "crank_angular_velocity_rad_s": round(omega2, 4),
        "coupler_angular_velocity_rad_s": round(omega3, 4),
        "rocker_angular_velocity_rad_s": round(omega4, 4),
        "mechanical_advantage": round(mech_advantage, 3),
        "transmission_angle_deg": round(trans_angle, 2),
        "linkage_type": linkage_type,
        "is_grashof": is_grashof,
        "link_lengths_m": {
            "crank": crank_length_m,
            "coupler": coupler_length_m,
            "rocker": rocker_length_m,
            "ground": ground_length_m,
        },
        "coupler_point_x_m": round(Cx, 4),
        "coupler_point_y_m": round(Cy, 4),
        "warnings": warnings,
    }


# ── LangChain Tool Wrappers ───────────────────────────────────────────────────

@tool
def run_pipe_flow_simulation(
    flow_rate_m3_s: float,
    pipe_diameter_m: float = 0.1,
    pipe_length_m: float = 100.0,
    fluid_type: str = "water",
    elevation_change_m: float = 0.0,
) -> dict:
    """
    Simulate pipe flow using Darcy-Weisbach equation.
    Returns pressure drop, head loss, pump power required, and flow regime.
    """
    return pipe_flow_simulation(
        flow_rate_m3_s, pipe_diameter_m, pipe_length_m,
        fluid_type, 0.000045, elevation_change_m, 0, 0
    )


@tool
def run_pump_simulation(
    flow_rate_m3_s: float,
    head_required_m: float,
    rotational_speed_rpm: float = 1750.0,
    fluid_type: str = "water",
) -> dict:
    """
    Simulate centrifugal pump performance using affinity laws.
    Returns efficiency, shaft power, specific speed, and NPSH required.
    """
    return centrifugal_pump_simulation(
        flow_rate_m3_s, head_required_m, 0.2, rotational_speed_rpm, fluid_type
    )


@tool
def run_gear_train_simulation(
    input_torque_nm: float,
    input_speed_rpm: float,
    gear_ratio: float,
    module_mm: float = 2.0,
    gear_material: str = "steel",
) -> dict:
    """
    Simulate spur gear train performance.
    Returns output torque/speed, efficiency, gear stresses, and sizing.
    """
    return gear_train_simulation(
        input_torque_nm, input_speed_rpm, gear_ratio, module_mm, 20.0, 1, gear_material
    )


@tool
def run_four_bar_linkage_simulation(
    crank_length_m: float,
    coupler_length_m: float,
    rocker_length_m: float,
    ground_length_m: float,
    crank_speed_rpm: float = 60.0,
) -> dict:
    """
    Simulate four-bar linkage kinematics.
    Returns linkage type, angles, velocities, and mechanical advantage.
    """
    return four_bar_linkage_simulation(
        crank_length_m, coupler_length_m, rocker_length_m, ground_length_m, crank_speed_rpm, 0.0
    )


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
    run_pipe_flow_simulation,
    run_pump_simulation,
    run_gear_train_simulation,
    run_four_bar_linkage_simulation,
]
