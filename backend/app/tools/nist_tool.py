"""
NEXUS Platform — NIST WebBook Tool
====================================
LangChain tool that queries the NIST Chemistry WebBook for real
thermophysical fluid properties during Research Agent pipeline runs.

Supported fluids: water, nitrogen, oxygen, hydrogen, helium, air,
                  co2, methane, ethanol, ammonia, LOX (= oxygen), RP-1 (≈ octane)
"""
from __future__ import annotations

import logging
import urllib.request
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

# NIST fluid IDs (CAS-based identifiers for the WebBook API)
FLUID_IDS: dict[str, str] = {
    "water":    "C7732185",
    "nitrogen": "C7727379",
    "oxygen":   "C7782447",
    "lox":      "C7782447",   # liquid oxygen = oxygen
    "hydrogen": "C1333740",
    "helium":   "C7440597",
    "air":      "C132259",
    "co2":      "C124389",
    "methane":  "C74828",
    "ethanol":  "C64175",
    "ammonia":  "C7664417",
    "rp1":      "C111659",    # n-dodecane as RP-1 proxy
    "kerosene": "C111659",
    "propane":  "C74986",
    "r134a":    "C811972",    # refrigerant HFC-134a
}

# NIST isobar column positions (tab-separated)
_ISOBAR_COLS = [
    ("temperature_K",       0),
    ("pressure_MPa",        1),
    ("density_kg_m3",       2),
    ("enthalpy_kJ_kg",      5),
    ("entropy_kJ_kgK",      6),
    ("Cp_kJ_kgK",           8),
    ("sound_speed_m_s",     9),
    ("viscosity_uPa_s",    11),
    ("conductivity_W_mK",  12),
    ("phase",              13),
]


@tool
def get_fluid_properties(
    fluid: str,
    temperature_k: float = 300.0,
    pressure_mpa: float = 0.101325,
) -> dict:
    """
    Query NIST Chemistry WebBook for real thermophysical properties of engineering fluids.

    Args:
        fluid: Fluid name — water, nitrogen, oxygen, lox, hydrogen, helium, air,
               co2, methane, ethanol, ammonia, rp1, kerosene, propane, r134a
        temperature_k: Operating temperature in Kelvin (default 300 K)
        pressure_mpa:  Operating pressure in MPa (default 0.101325 = 1 atm)

    Returns:
        Dict with: density_kg_m3, Cp_kJ_kgK, viscosity_uPa_s, conductivity_W_mK,
                   prandtl_number, enthalpy_kJ_kg, phase, plus computed Re-relevant props.
    """
    fluid_id = FLUID_IDS.get(fluid.lower().replace("-", "").replace("_", ""))
    if not fluid_id:
        available = sorted(FLUID_IDS.keys())
        return {"error": f"Unknown fluid '{fluid}'. Available: {available}"}

    # Clamp temperature so NIST doesn't reject it
    temperature_k = max(20.0, min(temperature_k, 2000.0))
    pressure_mpa  = max(0.001, min(pressure_mpa, 100.0))

    try:
        url = (
            "https://webbook.nist.gov/cgi/fluid.cgi"
            f"?Action=Load&ID={fluid_id}&Type=IsoBar&Digits=5"
            f"&P={pressure_mpa:.6f}"
            f"&THigh={temperature_k + 1:.2f}"
            f"&TLow={temperature_k - 1:.2f}"
            f"&TInc=1"
            "&RefState=DEF&TUnit=K&PUnit=MPa&DUnit=kg%2Fm3"
            "&HUnit=kJ%2Fkg&WUnit=m%2Fs&VisUnit=uPa*s&STUnit=N%2Fm"
        )
        req = urllib.request.Request(url, headers={"User-Agent": "NEXUS-Platform/1.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            raw = r.read().decode("utf-8")

        # Skip header rows
        data_rows = [
            ln for ln in raw.splitlines()
            if ln.strip() and not ln.lower().startswith("temp")
            and not ln.lower().startswith("phase")
        ]

        if not data_rows:
            return {
                "error": "NIST returned no data — fluid may be outside valid range",
                "fluid": fluid,
                "temperature_k": temperature_k,
                "pressure_mpa": pressure_mpa,
            }

        cols = data_rows[0].split("\t")
        props: dict = {}

        for name, idx in _ISOBAR_COLS:
            if idx < len(cols) and cols[idx].strip():
                try:
                    props[name] = float(cols[idx].strip())
                except ValueError:
                    props[name] = cols[idx].strip()

        # Derive Prandtl number: Pr = Cp * μ / k
        try:
            cp_si  = props["Cp_kJ_kgK"] * 1000          # J/kg/K
            mu_si  = props["viscosity_uPa_s"] * 1e-6     # Pa·s
            k_si   = props["conductivity_W_mK"]           # W/m/K
            props["prandtl_number"] = round(cp_si * mu_si / k_si, 4)
        except (KeyError, ZeroDivisionError, TypeError):
            pass

        # Derive kinematic viscosity: ν = μ/ρ (m²/s)
        try:
            props["kinematic_viscosity_m2_s"] = (
                props["viscosity_uPa_s"] * 1e-6 / props["density_kg_m3"]
            )
        except (KeyError, ZeroDivisionError, TypeError):
            pass

        props["source"] = (
            f"NIST WebBook — {fluid} at {temperature_k:.1f} K, {pressure_mpa:.5f} MPa"
        )
        return props

    except Exception as exc:
        logger.warning(f"NIST query failed for {fluid}: {exc}")
        return {"error": f"NIST query failed: {exc}", "fluid": fluid}


NIST_TOOLS = [get_fluid_properties]
