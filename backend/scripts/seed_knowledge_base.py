"""
NEXUS Platform — Engineering Knowledge Base Seeder
====================================================
Seeds ChromaDB with authoritative engineering reference documents
covering: heat transfer, propulsion, structural mechanics, and
electronics cooling.

Run standalone:
    python scripts/seed_knowledge_base.py

Or call seed() from the FastAPI lifespan on first startup.

These documents are the ground truth that the Research Agent queries
via semantic search. The quality of retrieval directly determines the
quality of design and simulation outputs.
"""
from __future__ import annotations

import logging
import sys
import os

logger = logging.getLogger(__name__)

# ── Engineering Knowledge Documents ──────────────────────────────────────────

ENGINEERING_DOCUMENTS = [
    # ── Heat Transfer ──────────────────────────────────────────────────────────
    {
        "title": "Newton's Law of Cooling — Fundamentals",
        "domain": "heat_transfer",
        "source": "Engineering Thermodynamics Reference",
        "content": """
Newton's Law of Cooling states that the rate of heat transfer between a solid surface
and a fluid is proportional to the temperature difference between them.

Formula: Q = h × A × (T_surface - T_fluid)

Where:
- Q = heat transfer rate [W]
- h = convection heat transfer coefficient [W/m²·K]
- A = surface area [m²]
- T_surface = surface temperature [K or °C]
- T_fluid = fluid (bulk) temperature [K or °C]

Typical h values:
- Natural convection (air): 5–25 W/m²·K
- Forced convection (air): 25–250 W/m²·K
- Forced convection (water): 500–10,000 W/m²·K
- Boiling water: 2,500–100,000 W/m²·K

Design rule of thumb: For electronics cooling with forced air, target h ≥ 50 W/m²·K.
For passive (natural convection) designs, use h = 10 W/m²·K as conservative estimate.
""",
        "metadata": {"equations": ["Q = h*A*(Ts-Tf)"], "keywords": ["convection", "cooling", "heat flux"]},
    },
    {
        "title": "Fourier's Law of Heat Conduction",
        "domain": "heat_transfer",
        "source": "Engineering Thermodynamics Reference",
        "content": """
Fourier's Law describes heat conduction through a solid material.

Formula: Q = -k × A × (dT/dx) = k × A × ΔT / L  (for 1D steady-state)

Where:
- Q = conductive heat transfer rate [W]
- k = thermal conductivity [W/m·K]
- A = cross-sectional area [m²]
- ΔT = temperature difference [K]
- L = thickness of material [m]

Thermal resistance (analogous to electrical resistance):
  R_thermal = L / (k × A)  [K/W]

Common thermal conductivities:
- Copper: 385 W/m·K
- Aluminum: 205 W/m·K
- Steel (carbon): 50 W/m·K
- Stainless steel: 16 W/m·K
- Air (still): 0.026 W/m·K
- Thermal grease/paste: 1–10 W/m·K

For composite walls: R_total = R_1 + R_2 + ... + R_n (series)
For parallel paths: 1/R_total = 1/R_1 + 1/R_2 + ... (parallel)

Design guideline: Minimize thermal resistance by maximizing k and A, and minimizing L.
""",
        "metadata": {"equations": ["Q = k*A*dT/L", "R = L/(k*A)"], "keywords": ["conduction", "thermal resistance", "conductivity"]},
    },
    {
        "title": "Fin Efficiency and Extended Surface Heat Transfer",
        "domain": "heat_transfer",
        "source": "Heat Transfer: A Practical Approach",
        "content": """
Fins (extended surfaces) are used to increase the effective heat transfer area.

Fin efficiency η_f represents the ratio of actual fin heat transfer to ideal heat transfer
(if the entire fin were at base temperature).

For rectangular fins:
  η_f = tanh(mL) / (mL)

Where:
  m = sqrt(h × P / (k × A_c))

  P = fin perimeter [m]
  A_c = fin cross-sectional area [m²]
  k = fin thermal conductivity [W/m·K]
  h = convection coefficient [W/m²·K]
  L = fin length [m]

Overall surface efficiency:
  η_o = 1 - (N × A_f / A_total) × (1 - η_f)

Where N = number of fins, A_f = fin surface area

Optimal fin spacing for natural convection:
  S_optimal ≈ 2.714 × (L / Ra_L^0.25)

Aluminum heat sinks: k = 205 W/m·K
Typical fin efficiency target: η_f > 0.85 for good designs

Rule of thumb: Increasing fin count beyond η_f < 0.7 gives diminishing returns.
""",
        "metadata": {"equations": ["eta_f = tanh(mL)/(mL)", "m = sqrt(h*P/(k*Ac))"], "keywords": ["fins", "heat sink", "extended surface"]},
    },
    {
        "title": "Thermal Resistance Network — System Level Analysis",
        "domain": "heat_transfer",
        "source": "Electronics Cooling Reference",
        "content": """
System-level thermal analysis uses resistance networks to model complete heat paths.

Junction-to-ambient thermal resistance:
  θ_ja = θ_jc + θ_cs + θ_sa

Where:
- θ_jc = junction-to-case resistance [°C/W] (chip package property)
- θ_cs = case-to-sink resistance [°C/W] (thermal interface material)
- θ_sa = sink-to-ambient resistance [°C/W] (heat sink + airflow)

Maximum junction temperature:
  T_j = T_ambient + P_dissipated × θ_ja

Target: T_j < T_j_max (typically 125°C for silicon, 150°C for wide-bandgap)

Thermal interface material (TIM) resistance:
  θ_cs = BLT / (k_TIM × A)

Where BLT = bond line thickness (typically 50–100 μm)
Common TIM: k = 3–8 W/m·K

For forced air cooling:
  θ_sa = 1 / (h × A_hs)
  h = Nu × k_air / D_h

Design flow: Calculate total θ_ja → check T_j → iterate h or A if T_j > limit.
""",
        "metadata": {"equations": ["T_j = T_a + P*theta_ja", "theta_ja = theta_jc + theta_cs + theta_sa"], "keywords": ["thermal resistance", "junction temperature", "electronics cooling"]},
    },

    # ── Propulsion ─────────────────────────────────────────────────────────────
    {
        "title": "Rocket Propulsion — Tsiolkovsky Rocket Equation",
        "domain": "propulsion",
        "source": "Rocket Propulsion Elements",
        "content": """
The Tsiolkovsky rocket equation relates velocity change (delta-v) to propellant mass fraction.

Δv = v_e × ln(m_0 / m_f)  = I_sp × g_0 × ln(m_0 / m_f)

Where:
- Δv = velocity change [m/s]
- v_e = effective exhaust velocity [m/s]
- I_sp = specific impulse [s]
- g_0 = 9.80665 m/s² (standard gravity)
- m_0 = initial (wet) mass [kg]
- m_f = final (dry) mass [kg]
- m_0/m_f = mass ratio

Common I_sp values:
- Cold gas (N₂): 65–75 s
- Monopropellant hydrazine: 220–240 s
- Bipropellant LOX/RP-1: 310–330 s (vacuum)
- Bipropellant LOX/LH₂: 450–460 s (vacuum)
- Electric (Hall thruster): 1,500–3,000 s (very low thrust)

Thrust:
  F = ṁ × v_e = ṁ × I_sp × g_0

Power:
  P_jet = (1/2) × ṁ × v_e²

Thrust-to-weight ratio (TWR) for launch vehicle: TWR > 1.3 required for liftoff.
""",
        "metadata": {"equations": ["dv = Isp*g0*ln(m0/mf)", "F = mdot*ve"], "keywords": ["rocket", "delta-v", "specific impulse", "thrust"]},
    },
    {
        "title": "Nozzle Design — De Laval Nozzle Theory",
        "domain": "propulsion",
        "source": "Gas Dynamics and Jet Propulsion",
        "content": """
The converging-diverging (De Laval) nozzle accelerates gas to supersonic speeds.

Area-Mach relationship (isentropic flow):
  A/A* = (1/M) × [(2/(γ+1)) × (1 + (γ-1)/2 × M²)]^((γ+1)/(2(γ-1)))

Where:
- A = local cross-sectional area [m²]
- A* = throat area (where M=1) [m²]
- M = local Mach number
- γ = ratio of specific heats (1.4 for air, ~1.2 for rocket exhaust)

Exit velocity:
  v_e = sqrt(2γ/(γ-1) × R×T_c/M_mol × [1 - (p_e/p_c)^((γ-1)/γ)])

Thrust coefficient:
  C_F = sqrt(2γ²/(γ-1) × (2/(γ+1))^((γ+1)/(γ-1)) × [1-(p_e/p_c)^((γ-1)/γ)]) + (p_e-p_a)/p_c × A_e/A_t

Optimum expansion: p_e = p_a (exit pressure = ambient pressure)
Over-expanded: p_e < p_a → oblique shocks at exit
Under-expanded: p_e > p_a → expansion waves at exit

Design guideline: For vacuum operation, maximize A_e/A_t (expansion ratio ε) to increase I_sp.
Typical ε: 6–20 for upper stages, 40–200 for vacuum engines.
""",
        "metadata": {"equations": ["A/A* = (1/M)*[...]", "ve = sqrt(2*gamma/(gamma-1)*R*Tc/Mmol*[...])"], "keywords": ["nozzle", "Mach number", "isentropic", "expansion ratio"]},
    },

    # ── Structural ─────────────────────────────────────────────────────────────
    {
        "title": "Structural Mechanics — Stress, Strain, and Safety Factors",
        "domain": "structural",
        "source": "Shigley's Mechanical Engineering Design",
        "content": """
Fundamental stress-strain relationships for structural design.

Normal stress (axial):
  σ = F / A  [Pa or MPa]

Shear stress:
  τ = V × Q / (I × b)  (for beams)
  τ = T × r / J  (for torsion)

Bending stress:
  σ = M × c / I

Where:
- F = axial force [N]
- A = cross-sectional area [m²]
- M = bending moment [N·m]
- c = distance from neutral axis to outer fiber [m]
- I = second moment of area [m⁴]  (rectangle: bh³/12)
- J = polar moment of inertia [m⁴] (circle: πd⁴/32)

Von Mises yield criterion (for combined loading):
  σ_vm = sqrt(σx² - σx×σy + σy² + 3τxy²)
  Yield occurs when: σ_vm ≥ S_y

Safety factor:
  n = S_y / σ_max  (static, ductile)
  n = S_e / σ_a    (fatigue, endurance limit)

Material yield strengths:
- Aluminum 6061-T6: S_y = 276 MPa, S_u = 310 MPa
- Steel 4340: S_y = 470 MPa (normalized)
- Titanium Ti-6Al-4V: S_y = 880 MPa, ρ = 4430 kg/m³

Design target: n ≥ 1.5 for static, n ≥ 2.0 for fatigue-critical components.
""",
        "metadata": {"equations": ["sigma = F/A", "sigma_vm = sqrt(sx^2-sx*sy+sy^2+3*txy^2)"], "keywords": ["stress", "safety factor", "von mises", "yield"]},
    },

    # ── Electronics Cooling ────────────────────────────────────────────────────
    {
        "title": "Electronics Cooling — Forced Convection and Airflow",
        "domain": "electronics_cooling",
        "source": "Thermal Design of Electronic Equipment",
        "content": """
Thermal management of electronics using forced air convection.

Required airflow for a given power dissipation:
  Q = ṁ × c_p × ΔT = ρ × V_dot × c_p × ΔT

Solving for volumetric flow rate:
  V_dot = Q / (ρ × c_p × ΔT)

Where:
- Q = total power dissipated [W]
- ṁ = mass flow rate [kg/s]
- V_dot = volumetric flow rate [m³/s]
- c_p = specific heat of air = 1006 J/kg·K
- ρ = density of air = 1.225 kg/m³ (at sea level, 15°C)
- ΔT = allowable temperature rise of air [K]

Reynolds number for channel flow:
  Re = ρ × V × D_h / μ

Hydraulic diameter:
  D_h = 4 × A_c / P  (A_c = channel area, P = wetted perimeter)

Nusselt number (laminar, fully developed, uniform heat flux):
  Nu = 8.235  (for rectangular channel, aspect ratio → 0)
  Nu = 3.608  (for square channel)

Nusselt number (turbulent, Dittus-Boelter):
  Nu = 0.023 × Re^0.8 × Pr^0.4

Convection coefficient from Nusselt number:
  h = Nu × k_fluid / D_h

Target: ΔT_air < 10–15°C for most electronic systems.
Component junction temp budget: ΔT_ja = ΔT_air + ΔT_heat-sink + ΔT_TIM + ΔT_jc
""",
        "metadata": {"equations": ["V_dot = Q/(rho*cp*dT)", "Nu = 0.023*Re^0.8*Pr^0.4"], "keywords": ["forced convection", "airflow", "electronics thermal", "Nusselt"]},
    },
    {
        "title": "Heat Pipe Technology — Operating Principles and Limits",
        "domain": "electronics_cooling",
        "source": "Heat Pipe Design Handbook",
        "content": """
Heat pipes are passive two-phase heat transfer devices with very low thermal resistance.

Operating principle:
1. Evaporator section: liquid evaporates, absorbs heat, becomes vapor
2. Transport section: vapor flows to condenser (pressure-driven)
3. Condenser section: vapor condenses, releases heat, liquid returns via wick

Effective thermal conductivity:
  k_eff = Q × L / (A × ΔT)  [W/m·K]
  Typical k_eff = 10,000–100,000 W/m·K (vs. copper = 385 W/m·K)

Operating limits (in order of typical occurrence):
1. Capillary limit: ΔP_capillary ≥ ΔP_liquid + ΔP_vapor + ΔP_gravity
   Q_max_cap = (2σ/r_eff - ρ_l×g×L×sinθ) × K×A_w / (μ_l×L_eff/k_l + μ_v×L_eff/(k_v×r_v²×ρ_v×λ))

2. Boiling limit: Q_max_boil = 4π×λ×k_eff×L_eff×T_v / (ln(r_o/r_i)×h_fg×ρ_v)

3. Sonic limit (vapor channel): Mach ≤ 0.2 for reliable operation

Common heat pipe working fluids:
- Water: 30–200°C (best for electronics)
- Ammonia: -60–100°C (spacecraft)
- Methanol: 10–130°C
- Acetone: 0–120°C

Wick materials: copper mesh (K ≈ 5×10⁻¹⁰ m²), sintered copper, grooves

Design guideline: Heat pipes can transfer 10–100× more heat than solid copper rods
of equivalent cross-section. Use for spreading heat from point sources.
""",
        "metadata": {"keywords": ["heat pipe", "two-phase", "capillary limit", "wick"]},
    },
]


def seed(vector_store) -> int:
    """
    Seed the vector store with engineering documents.
    Returns the number of documents successfully ingested.
    """
    ingested = 0
    for doc in ENGINEERING_DOCUMENTS:
        try:
            vector_store.add_document(**doc)
            ingested += 1
            logger.info(f"Ingested: {doc['title']}")
        except Exception as e:
            logger.warning(f"Skipped '{doc['title']}': {e}")

    logger.info(f"Seeding complete: {ingested}/{len(ENGINEERING_DOCUMENTS)} documents ingested")
    return ingested


if __name__ == "__main__":
    """Standalone seed script."""
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    from dotenv import load_dotenv
    load_dotenv()

    from app.core.config import get_settings
    from app.memory.vector_store import VectorStoreManager

    settings = get_settings()
    vs = VectorStoreManager(
        openai_api_key=settings.OPENAI_API_KEY,
        host=settings.CHROMA_HOST,
        port=settings.CHROMA_PORT,
    )
    vs.initialize()

    count = seed(vs)
    print(f"\n✓ Seeded {count} documents into the NEXUS knowledge base.")
