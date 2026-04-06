"""
NEXUS Platform — FreeCAD Parametric CAD Tool
=============================================
Generates 3D geometry (STEP + STL) from engineering design parameters
by running FreeCADCmd.exe with a domain-specific Python script.

Supports: heat_transfer (shell-and-tube HX), propulsion (de Laval nozzle),
          structural (I-beam / bracket), electronics_cooling (finned heatsink)

Output files are written to: backend/cad_output/{session_id}/
  design.step  — ISO 10303 STEP AP203 for CAD interop
  design.stl   — STL mesh for 3D printing / browser viewing
"""
from __future__ import annotations

import logging
import math
import os
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

# Output directory — one sub-folder per session
CAD_OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "cad_output"
CAD_OUTPUT_DIR.mkdir(exist_ok=True)

# Candidate FreeCADCmd executables (tried in order)
_FREECAD_CANDIDATES = [
    r"C:\Program Files\FreeCAD 1.0\bin\FreeCADCmd.exe",
    r"C:\Program Files\FreeCAD 0.21\bin\FreeCADCmd.exe",
    r"C:\Program Files\FreeCAD 0.20\bin\FreeCADCmd.exe",
    r"C:\Program Files (x86)\FreeCAD 1.0\bin\FreeCADCmd.exe",
    "FreeCADCmd",
    "freecadcmd",
]

_cached_freecad_exe: str | None = None


def _find_freecad_exe() -> str | None:
    """Return path to FreeCADCmd, or None if not installed."""
    global _cached_freecad_exe
    if _cached_freecad_exe is not None:
        return _cached_freecad_exe

    for candidate in _FREECAD_CANDIDATES:
        if os.path.isabs(candidate):
            if os.path.isfile(candidate):
                _cached_freecad_exe = candidate
                return candidate
        else:
            try:
                r = subprocess.run(
                    [candidate, "--version"],
                    capture_output=True, timeout=5
                )
                if r.returncode == 0 or r.stdout or r.stderr:
                    _cached_freecad_exe = candidate
                    return candidate
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue

    return None


# ── Script generators ─────────────────────────────────────────────────────────

def _fwd(path: str) -> str:
    """Convert Windows backslashes to forward slashes (Python on Windows accepts both)."""
    return path.replace("\\", "/")


def _heat_exchanger_script(params: dict, out_step: str, out_stl: str) -> str:
    """Shell-and-tube heat exchanger: hollow cylinder with tube bores."""
    p = params.get("primary_parameters", {})

    # Derive geometry from design params (convert m → mm where needed)
    area_m2   = _pval(p, ["heat_transfer_area_m2", "area", "heat_transfer_area"], 2.0)
    shell_r   = max(100, min(300, area_m2 * 50))   # rough mm
    shell_len = max(500, area_m2 * 200)             # mm
    num_tubes = max(4, min(37, int(area_m2 * 4)))
    tube_r    = max(8, shell_r * 0.06)
    pitch     = shell_r * 0.55 / max(1, (num_tubes - 1) / 6)

    # Build tube position list (central + rings)
    positions = [(0.0, 0.0)]
    for i in range(1, num_tubes):
        angle = i * 360 / (num_tubes - 1) if num_tubes > 1 else 0
        r = pitch
        positions.append((r * math.cos(math.radians(angle)),
                           r * math.sin(math.radians(angle))))

    tube_cuts = "\n".join(
        f"    t{i} = Part.makeCylinder({tube_r:.1f}, {shell_len:.1f}, "
        f"FreeCAD.Vector({x:.1f}, {y:.1f}, 0)); shell = shell.cut(t{i})"
        for i, (x, y) in enumerate(positions[:num_tubes])
    )

    return f"""\
import FreeCAD, Part
doc = FreeCAD.newDocument("HeatExchanger")
shell = Part.makeCylinder({shell_r:.1f}, {shell_len:.1f})
{tube_cuts}
obj = doc.addObject("Part::Feature", "ShellAndTube")
obj.Shape = shell
doc.recompute()
Part.export([obj.Shape], "{_fwd(out_step)}")
obj.Shape.exportStl("{_fwd(out_stl)}")
print("NEXUS_CAD_OK:{shell_r:.0f}mm_shell_{num_tubes}tubes")
"""


def _rocket_nozzle_script(params: dict, out_step: str, out_stl: str) -> str:
    """
    De Laval nozzle — proportions match the 2D diagram schematic:
      chamber : convergent : divergent  ≈  80 : 72 : 118  (diagram units)
      3-segment parabolic bell (steep→medium→shallow) + hollow bore + injector flange
    """
    p = params.get("primary_parameters", {})

    throat_mm = _pval(p, ["throat_diameter_mm", "throat_radius_mm"], 25.0)
    throat_r  = throat_mm / 2 if "throat_diameter_mm" in str(p) else throat_mm

    exp_ratio  = _pval(p, ["expansion_ratio", "area_ratio"], 10.0)
    exit_r     = throat_r * math.sqrt(exp_ratio)
    chamber_r  = throat_r * 3.2           # chamber/throat area ratio ≈ 10 → matches diagram
    wall_t     = max(4.0, throat_r * 0.14)

    # Lengths proportional to diagram (80 : 72 : 118)
    chamber_len = chamber_r * 2.5         # 80 parts
    conv_len    = chamber_len * 0.90      # 72 parts
    bell_len    = chamber_len * 1.475     # 118 parts

    # Bell: 3 frustum segments approximating parabolic profile
    # Steep (38%), medium (34%), shallow (28%) — matches bell opening angle
    r1 = throat_r + (exit_r - throat_r) * 0.38   # 38% of way to exit
    r2 = throat_r + (exit_r - throat_r) * 0.72   # 72% of way to exit
    z0 = chamber_len + conv_len
    z1 = z0 + bell_len * 0.38
    z2 = z0 + bell_len * 0.72
    z3 = z0 + bell_len

    # Injector flange
    flange_r = chamber_r + wall_t * 2.0
    flange_t = wall_t * 2.2

    return f"""\
import FreeCAD, Part
doc = FreeCAD.newDocument("deLavalNozzle")

# ── Outer shell ───────────────────────────────────────────────────────────────
flange  = Part.makeCylinder({flange_r:.2f}, {flange_t:.2f})
chamber = Part.makeCylinder({chamber_r + wall_t:.2f}, {chamber_len:.2f})
chamber.translate(FreeCAD.Vector(0, 0, {flange_t:.2f}))
conv    = Part.makeCone({chamber_r + wall_t:.2f}, {throat_r + wall_t:.2f}, {conv_len:.2f})
conv.translate(FreeCAD.Vector(0, 0, {flange_t + chamber_len:.2f}))
bell1   = Part.makeCone({throat_r + wall_t:.2f}, {r1 + wall_t:.2f}, {z1 - z0:.2f})
bell1.translate(FreeCAD.Vector(0, 0, {flange_t + z0:.2f}))
bell2   = Part.makeCone({r1 + wall_t:.2f}, {r2 + wall_t:.2f}, {z2 - z1:.2f})
bell2.translate(FreeCAD.Vector(0, 0, {flange_t + z1:.2f}))
bell3   = Part.makeCone({r2 + wall_t:.2f}, {exit_r + wall_t:.2f}, {z3 - z2:.2f})
bell3.translate(FreeCAD.Vector(0, 0, {flange_t + z2:.2f}))
outer   = flange.fuse(chamber).fuse(conv).fuse(bell1).fuse(bell2).fuse(bell3)

# ── Inner bore (flow path) ────────────────────────────────────────────────────
bore_ch = Part.makeCylinder({chamber_r:.2f}, {flange_t + chamber_len + 0.1:.2f})
bore_cv = Part.makeCone({chamber_r:.2f}, {throat_r:.2f}, {conv_len:.2f})
bore_cv.translate(FreeCAD.Vector(0, 0, {flange_t + chamber_len:.2f}))
bore_b1 = Part.makeCone({throat_r:.2f}, {r1:.2f}, {z1 - z0:.2f})
bore_b1.translate(FreeCAD.Vector(0, 0, {flange_t + z0:.2f}))
bore_b2 = Part.makeCone({r1:.2f}, {r2:.2f}, {z2 - z1:.2f})
bore_b2.translate(FreeCAD.Vector(0, 0, {flange_t + z1:.2f}))
bore_b3 = Part.makeCone({r2:.2f}, {exit_r:.2f}, {z3 - z2:.2f})
bore_b3.translate(FreeCAD.Vector(0, 0, {flange_t + z2:.2f}))
inner   = bore_ch.fuse(bore_cv).fuse(bore_b1).fuse(bore_b2).fuse(bore_b3)

nozzle = outer.cut(inner)
obj = doc.addObject("Part::Feature", "deLavalNozzle")
obj.Shape = nozzle
doc.recompute()
Part.export([obj.Shape], "{_fwd(out_step)}")
obj.Shape.exportStl("{_fwd(out_stl)}")
print("NEXUS_CAD_OK:throat={throat_r:.1f}mm_exit={exit_r:.1f}mm_bell={bell_len:.0f}mm")
"""


def _heatsink_script(params: dict, out_step: str, out_stl: str) -> str:
    """Finned aluminum heatsink: base plate with rectangular fins."""
    p = params.get("primary_parameters", {})

    area_cm2   = _pval(p, ["heatsink_area_cm2", "heatsink_area_m2"], 100.0)
    if area_cm2 < 1:
        area_cm2 *= 10000   # convert m² → cm²

    width      = math.sqrt(area_cm2) * 10      # mm
    depth      = width * 0.8
    base_h     = 6.0
    fin_h      = max(20.0, width * 0.4)
    num_fins   = max(6, min(24, int(width / 6)))
    fin_t      = max(1.5, width / (num_fins * 4))
    pitch      = (width - fin_t) / max(num_fins - 1, 1)

    fins_code = "\n".join(
        f"    f{i} = Part.makeBox({fin_t:.2f}, {depth:.2f}, {fin_h:.2f}, "
        f"FreeCAD.Vector({i * pitch:.2f}, 0, {base_h:.2f})); shape = shape.fuse(f{i})"
        for i in range(num_fins)
    )

    return f"""\
import FreeCAD, Part
doc = FreeCAD.newDocument("Heatsink")
shape = Part.makeBox({width:.2f}, {depth:.2f}, {base_h:.2f})
{fins_code}
obj = doc.addObject("Part::Feature", "FinnedHeatsink")
obj.Shape = shape
doc.recompute()
Part.export([obj.Shape], "{_fwd(out_step)}")
obj.Shape.exportStl("{_fwd(out_stl)}")
print("NEXUS_CAD_OK:{width:.0f}x{depth:.0f}mm_{num_fins}fins")
"""


def _beam_script(params: dict, out_step: str, out_stl: str) -> str:
    """
    Al 6061-T6 cantilever L-bracket matching the structural diagram:
      - Vertical mounting plate with 4 bolt holes
      - Horizontal cantilever arm
      - Triangular gusset for bending stiffness
    Dimensions derived from cross-section area and safety factor.
    """
    p = params.get("primary_parameters", {})

    # Cross-section area → arm thickness
    area_cm2 = _pval(p, ["cross_section_area_cm2", "cross_section_area_m2"], 25.0)
    if area_cm2 < 1:
        area_cm2 *= 10000   # m² → cm²
    arm_side   = math.sqrt(area_cm2) * 10      # mm — equivalent square side
    wall_t     = max(8.0, arm_side * 0.20)     # wall/arm thickness
    arm_w      = max(40.0, arm_side * 1.2)     # arm width (Y)
    arm_t      = wall_t                         # arm thickness (Z) = wall thickness

    # Arm length — scale from bending scenario (500N × arm gives ~50 N·m → 100mm)
    arm_len    = max(100.0, arm_side * 3.0)

    # Mounting plate
    plate_t    = wall_t * 1.3
    plate_w    = arm_w  * 1.4
    plate_h    = arm_len * 0.55

    # Gusset (right-triangle block under arm, at plate junction)
    gusset_d   = arm_len * 0.28
    gusset_h   = plate_h * 0.35

    # Arm Y-offset to centre it on plate
    arm_y0     = (plate_w - arm_w) / 2
    # Arm sits at mid-height of plate
    arm_z0     = plate_h * 0.40

    # Bolt hole radius (M8 clearance)
    hole_r     = 4.5
    # Hole positions on mounting plate
    hy1, hy2   = plate_w * 0.20, plate_w * 0.80
    hz1, hz2   = plate_h * 0.18, plate_h * 0.82

    return f"""\
import FreeCAD, Part
doc = FreeCAD.newDocument("AlBracket")

# ── Mounting plate (YZ plane, X = thickness) ──────────────────────────────────
plate = Part.makeBox({plate_t:.2f}, {plate_w:.2f}, {plate_h:.2f})

# ── Cantilever arm (extends in +X from plate face) ───────────────────────────
arm = Part.makeBox({arm_len:.2f}, {arm_w:.2f}, {arm_t:.2f},
                    FreeCAD.Vector({plate_t:.2f}, {arm_y0:.2f}, {arm_z0:.2f}))

# ── Gusset (triangular support under arm at plate junction) ───────────────────
gusset = Part.makeBox({gusset_d:.2f}, {arm_w:.2f}, {gusset_h:.2f},
                       FreeCAD.Vector({plate_t:.2f}, {arm_y0:.2f}, {arm_z0 - gusset_h:.2f}))

bracket = plate.fuse(arm).fuse(gusset)

# ── Bolt holes through mounting plate (X-axis direction) ─────────────────────
h1 = Part.makeCylinder({hole_r:.2f}, {plate_t + 2:.2f},
      FreeCAD.Vector(-1, {hy1:.2f}, {hz1:.2f}), FreeCAD.Vector(1, 0, 0))
h2 = Part.makeCylinder({hole_r:.2f}, {plate_t + 2:.2f},
      FreeCAD.Vector(-1, {hy2:.2f}, {hz1:.2f}), FreeCAD.Vector(1, 0, 0))
h3 = Part.makeCylinder({hole_r:.2f}, {plate_t + 2:.2f},
      FreeCAD.Vector(-1, {hy1:.2f}, {hz2:.2f}), FreeCAD.Vector(1, 0, 0))
h4 = Part.makeCylinder({hole_r:.2f}, {plate_t + 2:.2f},
      FreeCAD.Vector(-1, {hy2:.2f}, {hz2:.2f}), FreeCAD.Vector(1, 0, 0))

bracket = bracket.cut(h1).cut(h2).cut(h3).cut(h4)

obj = doc.addObject("Part::Feature", "Al6061Bracket")
obj.Shape = bracket
doc.recompute()
Part.export([obj.Shape], "{_fwd(out_step)}")
obj.Shape.exportStl("{_fwd(out_stl)}")
print("NEXUS_CAD_OK:arm={arm_len:.0f}mm_w={arm_w:.0f}mm_t={arm_t:.0f}mm_4bolts")
"""


def _pipe_assembly_script(params: dict, out_step: str, out_stl: str) -> str:
    """
    Pipe section with flanges — represents a fluid flow component.
    Generates a straight pipe with welded flanges on both ends.
    """
    p = params.get("primary_parameters", {})

    pipe_d = _pval(p, ["pipe_diameter_m", "diameter"], 0.1) * 1000  # convert m to mm
    pipe_len = _pval(p, ["pipe_length_m", "length"], 1.0) * 100    # scale for visualization (1m → 100mm)
    pipe_len = min(pipe_len, 500)  # cap at 500mm for reasonable CAD

    wall_t = max(3.0, pipe_d * 0.05)  # 5% wall thickness
    outer_d = pipe_d + 2 * wall_t

    # Flange dimensions
    flange_d = outer_d * 1.8
    flange_t = max(10.0, wall_t * 2)
    bolt_circle_d = (outer_d + flange_d) / 2
    num_bolts = 4 if pipe_d < 100 else 8
    bolt_r = max(4.0, pipe_d * 0.04)

    # Bolt hole positions
    bolt_cuts = []
    for i in range(num_bolts):
        angle = i * 360 / num_bolts
        x = bolt_circle_d / 2 * math.cos(math.radians(angle))
        y = bolt_circle_d / 2 * math.sin(math.radians(angle))
        bolt_cuts.append(f"    b{i}_1 = Part.makeCylinder({bolt_r:.2f}, {flange_t + 2:.2f}, "
                         f"FreeCAD.Vector({x:.2f}, {y:.2f}, -1), FreeCAD.Vector(0, 0, 1)); "
                         f"flange1 = flange1.cut(b{i}_1)")
        bolt_cuts.append(f"    b{i}_2 = Part.makeCylinder({bolt_r:.2f}, {flange_t + 2:.2f}, "
                         f"FreeCAD.Vector({x:.2f}, {y:.2f}, {pipe_len - 1:.2f}), FreeCAD.Vector(0, 0, 1)); "
                         f"flange2 = flange2.cut(b{i}_2)")

    bolt_code = "\n".join(bolt_cuts)

    return f"""\
import FreeCAD, Part
doc = FreeCAD.newDocument("PipeAssembly")

# Pipe body (hollow cylinder)
outer_cyl = Part.makeCylinder({outer_d / 2:.2f}, {pipe_len:.2f})
inner_cyl = Part.makeCylinder({pipe_d / 2:.2f}, {pipe_len + 2:.2f}, FreeCAD.Vector(0, 0, -1))
pipe = outer_cyl.cut(inner_cyl)

# Flange 1 (inlet)
flange1 = Part.makeCylinder({flange_d / 2:.2f}, {flange_t:.2f})
flange1_bore = Part.makeCylinder({pipe_d / 2:.2f}, {flange_t + 2:.2f}, FreeCAD.Vector(0, 0, -1))
flange1 = flange1.cut(flange1_bore)
{bolt_code.split("flange2")[0].rstrip()}

# Flange 2 (outlet)
flange2 = Part.makeCylinder({flange_d / 2:.2f}, {flange_t:.2f}, FreeCAD.Vector(0, 0, {pipe_len - flange_t:.2f}))
flange2_bore = Part.makeCylinder({pipe_d / 2:.2f}, {flange_t + 2:.2f}, FreeCAD.Vector(0, 0, {pipe_len - flange_t - 1:.2f}))
flange2 = flange2.cut(flange2_bore)

assembly = pipe.fuse(flange1).fuse(flange2)
obj = doc.addObject("Part::Feature", "PipeAssembly")
obj.Shape = assembly
doc.recompute()
Part.export([obj.Shape], "{_fwd(out_step)}")
obj.Shape.exportStl("{_fwd(out_stl)}")
print("NEXUS_CAD_OK:pipe_D={pipe_d:.0f}mm_L={pipe_len:.0f}mm_{num_bolts}bolts")
"""


def _gear_train_script(params: dict, out_step: str, out_stl: str) -> str:
    """
    Spur gear pair — pinion and gear meshing.
    Uses involute approximation via polygonal teeth.
    """
    p = params.get("primary_parameters", {})

    module = _pval(p, ["module_mm", "module"], 2.0)
    gear_ratio = _pval(p, ["gear_ratio", "ratio"], 4.0)

    # Tooth counts
    z_pinion = max(17, int(_pval(p, ["pinion_teeth"], 20)))
    z_gear = int(z_pinion * gear_ratio)

    # Pitch diameters
    d_pinion = module * z_pinion
    d_gear = module * z_gear

    # Addendum and dedendum
    ha = module          # addendum
    hf = 1.25 * module   # dedendum

    # Face width
    face_w = max(8 * module, _pval(p, ["face_width_mm", "face_width"], 10 * module))

    # Outer diameters
    da_pinion = d_pinion + 2 * ha
    da_gear = d_gear + 2 * ha

    # Center distance
    center_dist = (d_pinion + d_gear) / 2

    # Shaft diameters (20% of pitch diameter)
    shaft_d_pinion = max(5.0, d_pinion * 0.2)
    shaft_d_gear = max(8.0, d_gear * 0.2)

    return f"""\
import FreeCAD, Part
import math
doc = FreeCAD.newDocument("GearTrain")

# Simplified gear representation using cylinders with central bore
# (Full involute profile requires Part.BSplineCurve which is complex)

# Pinion (smaller gear)
pinion_outer = Part.makeCylinder({da_pinion / 2:.2f}, {face_w:.2f})
pinion_bore = Part.makeCylinder({shaft_d_pinion / 2:.2f}, {face_w + 2:.2f}, FreeCAD.Vector(0, 0, -1))
pinion = pinion_outer.cut(pinion_bore)

# Gear (larger gear) — offset by center distance
gear_outer = Part.makeCylinder({da_gear / 2:.2f}, {face_w:.2f}, FreeCAD.Vector({center_dist:.2f}, 0, 0))
gear_bore = Part.makeCylinder({shaft_d_gear / 2:.2f}, {face_w + 2:.2f}, FreeCAD.Vector({center_dist:.2f}, 0, -1))
gear = gear_outer.cut(gear_bore)

# Add keyways (rectangular slots)
keyway_w = {shaft_d_pinion * 0.25:.2f}
keyway_h = {shaft_d_pinion * 0.15:.2f}
key1 = Part.makeBox(keyway_w, keyway_h, {face_w + 2:.2f}, FreeCAD.Vector(-keyway_w/2, {shaft_d_pinion / 2 - keyway_h:.2f}, -1))
pinion = pinion.cut(key1)

key2 = Part.makeBox({shaft_d_gear * 0.25:.2f}, {shaft_d_gear * 0.15:.2f}, {face_w + 2:.2f}, 
       FreeCAD.Vector({center_dist - shaft_d_gear * 0.125:.2f}, {shaft_d_gear / 2 - shaft_d_gear * 0.15:.2f}, -1))
gear = gear.cut(key2)

assembly = pinion.fuse(gear)
obj = doc.addObject("Part::Feature", "GearTrain")
obj.Shape = assembly
doc.recompute()
Part.export([obj.Shape], "{_fwd(out_step)}")
obj.Shape.exportStl("{_fwd(out_stl)}")
print("NEXUS_CAD_OK:m={module:.1f}_z1={z_pinion}_z2={z_gear}_ratio={gear_ratio:.2f}")
"""


# ── Parameter helper ──────────────────────────────────────────────────────────

def _pval(params: dict, keys: list[str], default: float) -> float:
    """Search a params dict for any of the given key substrings, return first match."""
    for key in keys:
        # Exact match
        if key in params:
            try:
                return float(params[key])
            except (TypeError, ValueError):
                continue
        # Partial match
        for k, v in params.items():
            if key.lower() in k.lower():
                try:
                    return float(v)
                except (TypeError, ValueError):
                    continue
    return default


# ── Public API ────────────────────────────────────────────────────────────────

def generate_cad(session_id: str, domain: str, design_params: dict) -> dict:
    """
    Generate STEP and STL files for a given engineering domain + design params.
    Also generates tolerance annotations (GD&T) as a JSON sidecar file.

    Returns:
        {
          "available": bool,
          "step_path": str | None,
          "stl_path":  str | None,
          "tolerances_path": str | None,
          "domain":    str,
          "message":   str,
        }
    """
    exe = _find_freecad_exe()
    if exe is None:
        return {
            "available": False,
            "step_path": None,
            "stl_path":  None,
            "tolerances_path": None,
            "domain":    domain,
            "message":   "FreeCAD not found — install FreeCAD and connect it in the Tools page",
        }

    # Prepare output directory
    out_dir = CAD_OUTPUT_DIR / session_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out_step = str(out_dir / "design.step")
    out_stl  = str(out_dir / "design.stl")
    out_tol  = None

    # Generate tolerance annotations (GD&T)
    try:
        from app.tools.tolerance_specs import generate_tolerances, save_tolerance_package
        tol_pkg = generate_tolerances(session_id, domain, design_params)
        tol_path = save_tolerance_package(tol_pkg, out_dir)
        out_tol = str(tol_path)
        logger.info(f"[{session_id}] Generated tolerance specs: {len(tol_pkg.critical_dimensions)} annotations")
    except Exception as e:
        logger.warning(f"[{session_id}] Failed to generate tolerances: {e}")

    # Pick script generator
    generators = {
        "heat_transfer":       _heat_exchanger_script,
        "propulsion":          _rocket_nozzle_script,
        "structural":          _beam_script,
        "electronics_cooling": _heatsink_script,
        "fluids":              _pipe_assembly_script,
        "mechanisms":          _gear_train_script,
    }
    gen_fn = generators.get(domain, _heat_exchanger_script)
    script_src = gen_fn(design_params, out_step, out_stl)

    # Write temp script
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as tf:
        tf.write(script_src)
        script_path = tf.name

    try:
        result = subprocess.run(
            [exe, script_path],
            capture_output=True,
            text=True,
            timeout=60,
        )
        stdout = (result.stdout + result.stderr).strip()
        logger.info(f"[{session_id}] FreeCAD output: {stdout[:200]}")

        step_ok = os.path.isfile(out_step) and os.path.getsize(out_step) > 100
        stl_ok  = os.path.isfile(out_stl)  and os.path.getsize(out_stl)  > 100

        if step_ok or stl_ok:
            return {
                "available": True,
                "step_path": out_step if step_ok else None,
                "stl_path":  out_stl  if stl_ok  else None,
                "tolerances_path": out_tol,
                "domain":    domain,
                "message":   f"CAD generated — {stdout.split(chr(10))[-1][:80]}",
            }
        else:
            return {
                "available": False,
                "step_path": None,
                "stl_path":  None,
                "tolerances_path": out_tol,
                "domain":    domain,
                "message":   f"FreeCAD ran but produced no output. {stdout[:200]}",
            }

    except subprocess.TimeoutExpired:
        return {
            "available": False,
            "step_path": None,
            "stl_path":  None,
            "tolerances_path": out_tol,
            "domain":    domain,
            "message":   "FreeCAD script timed out (>60 s)",
        }
    except Exception as exc:
        logger.error(f"[{session_id}] FreeCAD error: {exc}")
        return {
            "available": False,
            "step_path": None,
            "stl_path":  None,
            "tolerances_path": out_tol,
            "domain":    domain,
            "message":   str(exc),
        }
    finally:
        try:
            os.unlink(script_path)
        except OSError:
            pass
