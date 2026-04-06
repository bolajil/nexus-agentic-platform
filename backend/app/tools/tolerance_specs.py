"""
NEXUS Platform — Tolerance & GD&T Specifications
=================================================
Generates manufacturing tolerance annotations for CAD output.
Supports ISO 2768 general tolerances and domain-specific GD&T.

GD&T symbols reference:
  ⌀ - Diameter           ⊥ - Perpendicularity    ∥ - Parallelism
  ○ - Circularity        ◎ - Concentricity       ⌓ - Cylindricity
  ⊕ - Position           ⏤ - Flatness            ⟋ - Angularity
"""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Literal

# ISO 2768 General Tolerances (linear dimensions in mm)
ISO_2768_TOLERANCES = {
    "fine": {
        (0, 3): 0.05,
        (3, 6): 0.05,
        (6, 30): 0.1,
        (30, 120): 0.15,
        (120, 400): 0.2,
        (400, 1000): 0.3,
    },
    "medium": {
        (0, 3): 0.1,
        (3, 6): 0.1,
        (6, 30): 0.2,
        (30, 120): 0.3,
        (120, 400): 0.5,
        (400, 1000): 0.8,
    },
    "coarse": {
        (0, 3): 0.2,
        (3, 6): 0.3,
        (6, 30): 0.5,
        (30, 120): 0.8,
        (120, 400): 1.2,
        (400, 1000): 2.0,
    },
}


@dataclass
class ToleranceAnnotation:
    """Single tolerance annotation for a feature."""
    feature_name: str
    dimension_mm: float
    tolerance_plus: float
    tolerance_minus: float
    tolerance_class: str  # ISO 2768-f, -m, -c or custom
    gdt_symbol: str | None = None  # GD&T symbol if applicable
    gdt_value: float | None = None  # GD&T tolerance value
    datum_ref: str | None = None  # Reference datum (A, B, C)
    notes: str | None = None


@dataclass
class MaterialSpec:
    """Material specification for manufacturing."""
    name: str
    grade: str
    density_kg_m3: float
    yield_strength_mpa: float
    thermal_conductivity_w_mk: float | None = None
    max_service_temp_c: float | None = None


@dataclass
class TolerancePackage:
    """Complete tolerance package for a CAD model."""
    session_id: str
    domain: str
    iso_tolerance_class: str
    material: MaterialSpec
    critical_dimensions: list[ToleranceAnnotation]
    surface_finish_ra_um: float  # Surface roughness Ra in micrometers
    general_notes: list[str]


def get_iso_tolerance(dimension_mm: float, tolerance_class: str = "medium") -> float:
    """Get ISO 2768 tolerance for a given dimension."""
    tolerances = ISO_2768_TOLERANCES.get(tolerance_class, ISO_2768_TOLERANCES["medium"])
    for (min_d, max_d), tol in tolerances.items():
        if min_d <= dimension_mm < max_d:
            return tol
    # For dimensions > 1000mm, extrapolate
    return tolerances[(400, 1000)] * (dimension_mm / 700)


def generate_heat_transfer_tolerances(params: dict, session_id: str) -> TolerancePackage:
    """Generate tolerances for heat exchanger / heat sink."""
    p = params.get("primary_parameters", {})
    
    # Extract key dimensions
    area = p.get("heat_transfer_area_m2", p.get("heatsink_area_cm2", 100))
    if area < 1:
        area *= 10000  # m² to cm²
    
    width = (area ** 0.5) * 10  # mm estimate
    
    annotations = [
        ToleranceAnnotation(
            feature_name="Base plate flatness",
            dimension_mm=width,
            tolerance_plus=0.1,
            tolerance_minus=0.1,
            tolerance_class="ISO 2768-m",
            gdt_symbol="⏤",  # Flatness
            gdt_value=0.1,
            notes="Critical for thermal contact"
        ),
        ToleranceAnnotation(
            feature_name="Fin height",
            dimension_mm=width * 0.4,
            tolerance_plus=get_iso_tolerance(width * 0.4, "medium"),
            tolerance_minus=get_iso_tolerance(width * 0.4, "medium"),
            tolerance_class="ISO 2768-m"
        ),
        ToleranceAnnotation(
            feature_name="Fin spacing",
            dimension_mm=width / 12,
            tolerance_plus=0.2,
            tolerance_minus=0.2,
            tolerance_class="ISO 2768-m",
            notes="Affects airflow distribution"
        ),
        ToleranceAnnotation(
            feature_name="Mounting hole position",
            dimension_mm=width * 0.8,
            tolerance_plus=0.15,
            tolerance_minus=0.15,
            tolerance_class="ISO 2768-m",
            gdt_symbol="⊕",  # Position
            gdt_value=0.3,
            datum_ref="A"
        ),
    ]
    
    return TolerancePackage(
        session_id=session_id,
        domain="heat_transfer",
        iso_tolerance_class="ISO 2768-mK",
        material=MaterialSpec(
            name="Aluminum",
            grade="6061-T6",
            density_kg_m3=2700,
            yield_strength_mpa=276,
            thermal_conductivity_w_mk=167,
            max_service_temp_c=150
        ),
        critical_dimensions=annotations,
        surface_finish_ra_um=3.2,
        general_notes=[
            "All dimensions in mm unless otherwise specified",
            "Base plate contact surface: Ra ≤ 1.6 μm",
            "Deburr all edges",
            "Anodize after machining (Type II, Class 1)"
        ]
    )


def generate_propulsion_tolerances(params: dict, session_id: str) -> TolerancePackage:
    """Generate tolerances for rocket nozzle."""
    p = params.get("primary_parameters", {})
    
    throat_mm = p.get("throat_diameter_mm", p.get("throat_radius_mm", 25))
    if "diameter" not in str(p):
        throat_mm *= 2
    
    exp_ratio = p.get("expansion_ratio", 10)
    exit_mm = throat_mm * (exp_ratio ** 0.5)
    
    annotations = [
        ToleranceAnnotation(
            feature_name="Throat diameter",
            dimension_mm=throat_mm,
            tolerance_plus=0.025,
            tolerance_minus=0.025,
            tolerance_class="ISO 2768-f",
            gdt_symbol="⌀",
            gdt_value=0.05,
            notes="Critical for mass flow rate — tight tolerance required"
        ),
        ToleranceAnnotation(
            feature_name="Throat circularity",
            dimension_mm=throat_mm,
            tolerance_plus=0.02,
            tolerance_minus=0.02,
            tolerance_class="Custom",
            gdt_symbol="○",
            gdt_value=0.02,
            notes="Affects flow uniformity"
        ),
        ToleranceAnnotation(
            feature_name="Exit diameter",
            dimension_mm=exit_mm,
            tolerance_plus=get_iso_tolerance(exit_mm, "fine"),
            tolerance_minus=get_iso_tolerance(exit_mm, "fine"),
            tolerance_class="ISO 2768-f",
            gdt_symbol="⌀"
        ),
        ToleranceAnnotation(
            feature_name="Nozzle concentricity",
            dimension_mm=exit_mm,
            tolerance_plus=0.05,
            tolerance_minus=0.05,
            tolerance_class="Custom",
            gdt_symbol="◎",
            gdt_value=0.1,
            datum_ref="A",
            notes="Throat to exit axis alignment"
        ),
        ToleranceAnnotation(
            feature_name="Convergent half-angle",
            dimension_mm=30,  # degrees (stored as value)
            tolerance_plus=0.5,
            tolerance_minus=0.5,
            tolerance_class="Custom",
            gdt_symbol="⟋",
            notes="30° ±0.5° per industry standard"
        ),
    ]
    
    return TolerancePackage(
        session_id=session_id,
        domain="propulsion",
        iso_tolerance_class="ISO 2768-fH",
        material=MaterialSpec(
            name="Inconel",
            grade="718",
            density_kg_m3=8190,
            yield_strength_mpa=1034,
            thermal_conductivity_w_mk=11.4,
            max_service_temp_c=700
        ),
        critical_dimensions=annotations,
        surface_finish_ra_um=0.8,
        general_notes=[
            "All dimensions in mm unless otherwise specified",
            "Internal flow surfaces: Ra ≤ 0.8 μm",
            "Throat section: Ra ≤ 0.4 μm (polished)",
            "Proof pressure test required before delivery",
            "No burrs or sharp edges on flow path"
        ]
    )


def generate_structural_tolerances(params: dict, session_id: str) -> TolerancePackage:
    """Generate tolerances for structural bracket."""
    p = params.get("primary_parameters", {})
    
    area_cm2 = p.get("cross_section_area_cm2", 25)
    if area_cm2 < 1:
        area_cm2 *= 10000
    
    arm_side = (area_cm2 ** 0.5) * 10  # mm
    arm_len = arm_side * 3
    
    annotations = [
        ToleranceAnnotation(
            feature_name="Mounting plate flatness",
            dimension_mm=arm_side * 1.4,
            tolerance_plus=0.15,
            tolerance_minus=0.15,
            tolerance_class="ISO 2768-m",
            gdt_symbol="⏤",
            gdt_value=0.15,
            datum_ref="A",
            notes="Reference surface for assembly"
        ),
        ToleranceAnnotation(
            feature_name="Bolt hole diameter",
            dimension_mm=9.0,  # M8 clearance
            tolerance_plus=0.2,
            tolerance_minus=0.0,
            tolerance_class="H11",
            gdt_symbol="⌀",
            notes="M8 clearance hole per ISO 273"
        ),
        ToleranceAnnotation(
            feature_name="Bolt hole position",
            dimension_mm=arm_side,
            tolerance_plus=0.25,
            tolerance_minus=0.25,
            tolerance_class="ISO 2768-m",
            gdt_symbol="⊕",
            gdt_value=0.5,
            datum_ref="A"
        ),
        ToleranceAnnotation(
            feature_name="Cantilever arm perpendicularity",
            dimension_mm=arm_len,
            tolerance_plus=0.2,
            tolerance_minus=0.2,
            tolerance_class="ISO 2768-m",
            gdt_symbol="⊥",
            gdt_value=0.3,
            datum_ref="A",
            notes="Arm to mounting plate"
        ),
        ToleranceAnnotation(
            feature_name="Arm length",
            dimension_mm=arm_len,
            tolerance_plus=get_iso_tolerance(arm_len, "medium"),
            tolerance_minus=get_iso_tolerance(arm_len, "medium"),
            tolerance_class="ISO 2768-m"
        ),
    ]
    
    return TolerancePackage(
        session_id=session_id,
        domain="structural",
        iso_tolerance_class="ISO 2768-mK",
        material=MaterialSpec(
            name="Aluminum",
            grade="6061-T6",
            density_kg_m3=2700,
            yield_strength_mpa=276,
            thermal_conductivity_w_mk=167,
            max_service_temp_c=150
        ),
        critical_dimensions=annotations,
        surface_finish_ra_um=6.3,
        general_notes=[
            "All dimensions in mm unless otherwise specified",
            "Mounting surface: Ra ≤ 3.2 μm",
            "Deburr all edges, break sharp corners 0.5 max",
            "Anodize Type II, Class 1 (clear) after machining",
            "Mark part number per drawing"
        ]
    )


def generate_electronics_tolerances(params: dict, session_id: str) -> TolerancePackage:
    """Generate tolerances for electronics cooling (heat sink)."""
    # Similar to heat_transfer but with electronics-specific notes
    pkg = generate_heat_transfer_tolerances(params, session_id)
    pkg.domain = "electronics_cooling"
    pkg.general_notes = [
        "All dimensions in mm unless otherwise specified",
        "Thermal interface surface: Ra ≤ 1.6 μm, flatness ≤ 0.05 mm",
        "Verify flatness with optical flat before shipping",
        "Deburr all edges — no conductive debris",
        "Anodize Type II, Class 1 (clear) — do NOT anodize thermal interface",
        "ESD-safe packaging required"
    ]
    return pkg


def generate_fluids_tolerances(params: dict, session_id: str) -> TolerancePackage:
    """Generate tolerances for fluid systems (pipes, pumps)."""
    p = params.get("primary_parameters", {})
    
    pipe_d = p.get("pipe_diameter_m", 0.1) * 1000  # mm
    pipe_len = p.get("pipe_length_m", 100) * 10  # scale for CAD
    
    annotations = [
        ToleranceAnnotation(
            feature_name="Pipe inner diameter",
            dimension_mm=pipe_d,
            tolerance_plus=get_iso_tolerance(pipe_d, "medium"),
            tolerance_minus=get_iso_tolerance(pipe_d, "medium"),
            tolerance_class="ISO 2768-m",
            gdt_symbol="⌀",
            notes="Critical for flow rate"
        ),
        ToleranceAnnotation(
            feature_name="Pipe wall concentricity",
            dimension_mm=pipe_d,
            tolerance_plus=0.5,
            tolerance_minus=0.5,
            tolerance_class="ISO 2768-m",
            gdt_symbol="◎",
            gdt_value=1.0,
            notes="Wall thickness uniformity"
        ),
        ToleranceAnnotation(
            feature_name="Flange face flatness",
            dimension_mm=pipe_d * 1.8,
            tolerance_plus=0.1,
            tolerance_minus=0.1,
            tolerance_class="ISO 2768-m",
            gdt_symbol="⏤",
            gdt_value=0.1,
            notes="Critical for gasket sealing"
        ),
        ToleranceAnnotation(
            feature_name="Bolt hole position",
            dimension_mm=pipe_d * 1.5,
            tolerance_plus=0.25,
            tolerance_minus=0.25,
            tolerance_class="ISO 2768-m",
            gdt_symbol="⊕",
            gdt_value=0.5,
            datum_ref="A"
        ),
        ToleranceAnnotation(
            feature_name="Flange perpendicularity",
            dimension_mm=pipe_d * 1.8,
            tolerance_plus=0.15,
            tolerance_minus=0.15,
            tolerance_class="ISO 2768-m",
            gdt_symbol="⊥",
            gdt_value=0.2,
            datum_ref="A",
            notes="Flange to pipe axis"
        ),
    ]
    
    return TolerancePackage(
        session_id=session_id,
        domain="fluids",
        iso_tolerance_class="ISO 2768-mK",
        material=MaterialSpec(
            name="Carbon Steel",
            grade="A106 Grade B",
            density_kg_m3=7850,
            yield_strength_mpa=240,
            thermal_conductivity_w_mk=50,
            max_service_temp_c=400
        ),
        critical_dimensions=annotations,
        surface_finish_ra_um=6.3,
        general_notes=[
            "All dimensions in mm unless otherwise specified",
            "Pipe schedule: Sch 40 unless noted",
            "Flange rating: ANSI 150# RF",
            "Hydrostatic test required: 1.5× MAWP",
            "Internal surfaces: clean, free of scale and debris",
            "Weld per ASME B31.3"
        ]
    )


def generate_mechanisms_tolerances(params: dict, session_id: str) -> TolerancePackage:
    """Generate tolerances for mechanical systems (gears, linkages)."""
    p = params.get("primary_parameters", {})
    
    module = p.get("module_mm", 2.0)
    gear_ratio = p.get("gear_ratio", 4.0)
    z_pinion = int(p.get("pinion_teeth", 20))
    
    d_pinion = module * z_pinion
    d_gear = module * z_pinion * gear_ratio
    
    annotations = [
        ToleranceAnnotation(
            feature_name="Pinion pitch diameter",
            dimension_mm=d_pinion,
            tolerance_plus=0.02,
            tolerance_minus=0.02,
            tolerance_class="DIN 3962 Grade 6",
            gdt_symbol="⌀",
            notes="AGMA Quality 10 equivalent"
        ),
        ToleranceAnnotation(
            feature_name="Gear pitch diameter",
            dimension_mm=d_gear,
            tolerance_plus=0.025,
            tolerance_minus=0.025,
            tolerance_class="DIN 3962 Grade 6",
            gdt_symbol="⌀"
        ),
        ToleranceAnnotation(
            feature_name="Bore diameter (pinion)",
            dimension_mm=d_pinion * 0.2,
            tolerance_plus=0.012,
            tolerance_minus=0.0,
            tolerance_class="H7",
            gdt_symbol="⌀",
            notes="Interference fit with shaft"
        ),
        ToleranceAnnotation(
            feature_name="Bore concentricity",
            dimension_mm=d_pinion * 0.2,
            tolerance_plus=0.015,
            tolerance_minus=0.015,
            tolerance_class="Custom",
            gdt_symbol="◎",
            gdt_value=0.03,
            datum_ref="A",
            notes="Bore to pitch circle"
        ),
        ToleranceAnnotation(
            feature_name="Face width",
            dimension_mm=10 * module,
            tolerance_plus=get_iso_tolerance(10 * module, "medium"),
            tolerance_minus=get_iso_tolerance(10 * module, "medium"),
            tolerance_class="ISO 2768-m"
        ),
        ToleranceAnnotation(
            feature_name="Tooth profile",
            dimension_mm=module,
            tolerance_plus=0.01,
            tolerance_minus=0.01,
            tolerance_class="DIN 3962",
            notes="Involute profile per ISO 53"
        ),
        ToleranceAnnotation(
            feature_name="Center distance",
            dimension_mm=(d_pinion + d_gear) / 2,
            tolerance_plus=0.05,
            tolerance_minus=0.05,
            tolerance_class="ISO 2768-m",
            notes="Critical for backlash control"
        ),
    ]
    
    return TolerancePackage(
        session_id=session_id,
        domain="mechanisms",
        iso_tolerance_class="DIN 3962 Grade 6",
        material=MaterialSpec(
            name="Alloy Steel",
            grade="4140 (42CrMo4)",
            density_kg_m3=7850,
            yield_strength_mpa=655,
            thermal_conductivity_w_mk=42,
            max_service_temp_c=200
        ),
        critical_dimensions=annotations,
        surface_finish_ra_um=1.6,
        general_notes=[
            "All dimensions in mm unless otherwise specified",
            "Gear quality: AGMA 10 / DIN 3962 Grade 6",
            "Tooth flank hardness: 58-62 HRC (case hardened)",
            "Core hardness: 30-35 HRC",
            "Backlash: 0.04-0.08 × module",
            "Lubrication: ISO VG 220 gear oil",
            "Run-in required: 8 hours at 50% load"
        ]
    )


def generate_tolerances(session_id: str, domain: str, design_params: dict) -> TolerancePackage:
    """
    Generate tolerance package for a CAD model based on domain.
    
    Args:
        session_id: NEXUS session ID
        domain: Engineering domain (heat_transfer, propulsion, structural, electronics_cooling, fluids, mechanisms)
        design_params: Design parameters from the design agent
        
    Returns:
        TolerancePackage with GD&T annotations
    """
    generators = {
        "heat_transfer": generate_heat_transfer_tolerances,
        "propulsion": generate_propulsion_tolerances,
        "structural": generate_structural_tolerances,
        "electronics_cooling": generate_electronics_tolerances,
        "fluids": generate_fluids_tolerances,
        "mechanisms": generate_mechanisms_tolerances,
    }
    
    gen_fn = generators.get(domain, generate_heat_transfer_tolerances)
    return gen_fn(design_params, session_id)


def save_tolerance_package(pkg: TolerancePackage, output_dir: Path) -> Path:
    """Save tolerance package as JSON file."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Convert to dict for JSON serialization
    data = {
        "session_id": pkg.session_id,
        "domain": pkg.domain,
        "iso_tolerance_class": pkg.iso_tolerance_class,
        "material": asdict(pkg.material),
        "critical_dimensions": [asdict(a) for a in pkg.critical_dimensions],
        "surface_finish_ra_um": pkg.surface_finish_ra_um,
        "general_notes": pkg.general_notes,
    }
    
    out_path = output_dir / "tolerances.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    return out_path


def load_tolerance_package(json_path: Path) -> dict | None:
    """Load tolerance package from JSON file."""
    if not json_path.is_file():
        return None
    
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)
