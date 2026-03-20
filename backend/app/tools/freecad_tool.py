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

def _esc(path: str) -> str:
    """Escape Windows paths for embedding in Python string literals."""
    return path.replace("\\", "\\\\")


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
Part.export([obj.Shape], r"{_esc(out_step)}")
obj.Shape.exportStl(r"{_esc(out_stl)}")
print("NEXUS_CAD_OK:{shell_r:.0f}mm_shell_{num_tubes}tubes")
"""


def _rocket_nozzle_script(params: dict, out_step: str, out_stl: str) -> str:
    """De Laval convergent-divergent nozzle built from cone/cylinder primitives."""
    p = params.get("primary_parameters", {})

    throat_mm  = _pval(p, ["throat_diameter_mm", "throat_radius_mm"], 25.0)
    if "throat_diameter_mm" in str(p):
        throat_r = throat_mm / 2
    else:
        throat_r = throat_mm

    exp_ratio  = _pval(p, ["expansion_ratio", "area_ratio"], 8.0)
    exit_r     = throat_r * math.sqrt(exp_ratio)
    chamber_r  = throat_r * 2.5          # typical chamber-to-throat area ratio ~5-8
    wall_t     = max(3.0, throat_r * 0.1)

    chamber_len  = chamber_r * 2.0
    conv_len     = chamber_r * 1.2
    div_len      = throat_r * math.sqrt(exp_ratio) * 2.5

    return f"""\
import FreeCAD, Part
doc = FreeCAD.newDocument("RocketNozzle")

# Outer profile: chamber cylinder + convergent frustum + divergent frustum
chamber  = Part.makeCylinder({chamber_r:.2f}, {chamber_len:.2f})
convergent = Part.makeCone({chamber_r:.2f}, {throat_r:.2f}, {conv_len:.2f})
convergent.translate(FreeCAD.Vector(0, 0, {chamber_len:.2f}))
divergent  = Part.makeCone({throat_r:.2f}, {exit_r:.2f}, {div_len:.2f})
divergent.translate(FreeCAD.Vector(0, 0, {chamber_len + conv_len:.2f}))
outer = chamber.fuse(convergent).fuse(divergent)

# Inner profile (hollow): slightly smaller radii
chamber_i  = Part.makeCylinder({chamber_r - wall_t:.2f}, {chamber_len:.2f})
convergent_i = Part.makeCone({chamber_r - wall_t:.2f}, {max(1, throat_r - wall_t):.2f}, {conv_len:.2f})
convergent_i.translate(FreeCAD.Vector(0, 0, {chamber_len:.2f}))
divergent_i  = Part.makeCone({max(1, throat_r - wall_t):.2f}, {exit_r - wall_t:.2f}, {div_len:.2f})
divergent_i.translate(FreeCAD.Vector(0, 0, {chamber_len + conv_len:.2f}))
inner = chamber_i.fuse(convergent_i).fuse(divergent_i)

nozzle = outer.cut(inner)
obj = doc.addObject("Part::Feature", "deLavalNozzle")
obj.Shape = nozzle
doc.recompute()
Part.export([obj.Shape], r"{_esc(out_step)}")
obj.Shape.exportStl(r"{_esc(out_stl)}")
print("NEXUS_CAD_OK:throat={throat_r:.1f}mm_exit={exit_r:.1f}mm_ratio={exp_ratio:.1f}")
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
Part.export([obj.Shape], r"{_esc(out_step)}")
obj.Shape.exportStl(r"{_esc(out_stl)}")
print("NEXUS_CAD_OK:{width:.0f}x{depth:.0f}mm_{num_fins}fins")
"""


def _beam_script(params: dict, out_step: str, out_stl: str) -> str:
    """Steel I-beam / bracket: two flanges + web."""
    p = params.get("primary_parameters", {})

    # Cross-section area → rough geometry
    area_m2  = _pval(p, ["cross_section_area_m2", "cross_section_area_cm2"], 0.001)
    if area_m2 > 1:
        area_m2 /= 10000   # cm² → m²

    side       = math.sqrt(area_m2) * 1000        # mm — equiv square side
    height     = max(40.0, side * 1.5)
    width      = max(30.0, side * 1.2)
    flange_t   = max(5.0, height * 0.12)
    web_t      = max(4.0, width * 0.08)
    length_mm  = _pval(p, ["beam_length_m", "length_mm"], 2.0) * 1000
    if length_mm < 50:
        length_mm *= 1000   # already in mm

    web_h = height - 2 * flange_t

    return f"""\
import FreeCAD, Part
doc = FreeCAD.newDocument("StructuralBeam")
flange1  = Part.makeBox({width:.2f}, {flange_t:.2f}, {length_mm:.2f})
flange2  = Part.makeBox({width:.2f}, {flange_t:.2f}, {length_mm:.2f},
                         FreeCAD.Vector(0, {height - flange_t:.2f}, 0))
web      = Part.makeBox({web_t:.2f}, {web_h:.2f}, {length_mm:.2f},
                         FreeCAD.Vector({(width - web_t) / 2:.2f}, {flange_t:.2f}, 0))
shape    = flange1.fuse(flange2).fuse(web)
obj = doc.addObject("Part::Feature", "IBeam")
obj.Shape = shape
doc.recompute()
Part.export([obj.Shape], r"{_esc(out_step)}")
obj.Shape.exportStl(r"{_esc(out_stl)}")
print("NEXUS_CAD_OK:{width:.0f}x{height:.0f}mm_L={length_mm:.0f}mm")
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

    Returns:
        {
          "available": bool,
          "step_path": str | None,
          "stl_path":  str | None,
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
            "domain":    domain,
            "message":   "FreeCAD not found — install FreeCAD and connect it in the Tools page",
        }

    # Prepare output directory
    out_dir = CAD_OUTPUT_DIR / session_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out_step = str(out_dir / "design.step")
    out_stl  = str(out_dir / "design.stl")

    # Pick script generator
    generators = {
        "heat_transfer":    _heat_exchanger_script,
        "propulsion":       _rocket_nozzle_script,
        "structural":       _beam_script,
        "electronics_cooling": _heatsink_script,
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
                "domain":    domain,
                "message":   f"CAD generated — {stdout.split(chr(10))[-1][:80]}",
            }
        else:
            return {
                "available": False,
                "step_path": None,
                "stl_path":  None,
                "domain":    domain,
                "message":   f"FreeCAD ran but produced no output. {stdout[:200]}",
            }

    except subprocess.TimeoutExpired:
        return {
            "available": False,
            "step_path": None,
            "stl_path":  None,
            "domain":    domain,
            "message":   "FreeCAD script timed out (>60 s)",
        }
    except Exception as exc:
        logger.error(f"[{session_id}] FreeCAD error: {exc}")
        return {
            "available": False,
            "step_path": None,
            "stl_path":  None,
            "domain":    domain,
            "message":   str(exc),
        }
    finally:
        try:
            os.unlink(script_path)
        except OSError:
            pass
