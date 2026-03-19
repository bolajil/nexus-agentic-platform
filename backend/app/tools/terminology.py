"""
NEXUS Platform — Engineering Terminology Normalizer
====================================================
Handles the core RAG problem for technical/engineering domains:

  PROBLEM: The same concept appears in many surface forms:
    - "θ_ja"  == "theta_ja"  == "junction-to-ambient thermal resistance"
    - "Δv"    == "delta-v"   == "delta_v"   == "velocity change"
    - "η_f"   == "eta_f"     == "fin efficiency"
    - "σ"     == "sigma"     == "normal stress" == "stress"
    - "I_sp"  == "Isp"       == "specific impulse"

  Pure cosine similarity over embeddings handles SEMANTIC meaning well
  but struggles with NOTATION variance — especially when:
    1. A query uses Greek letters the embedding model may tokenize differently
    2. A project has custom abbreviations not in the LLM's training data
    3. Equations (Q = h·A·ΔT) are stored as plain text and queried by concept

  SOLUTION: Two-stage preprocessing pipeline
    1. Normalize: expand all known notation variants to canonical long form
    2. Augment:   append expanded synonyms alongside the original text
       so BOTH the original and expanded forms are embedded together

  This gives hybrid coverage: the embedding captures semantic meaning from
  the expanded form, while the original notation is preserved for BM25/keyword
  matching in hybrid search.

Architecture note (for interviews):
  This is the same challenge as biomedical NLP (gene symbols, drug names)
  or legal NLP (citation formats). The pattern — glossary expansion before
  embedding + hybrid retrieval — is standard in production RAG systems.
"""
from __future__ import annotations

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


# ── Greek Letter Map ──────────────────────────────────────────────────────────
# Maps Unicode Greek characters AND common ASCII representations → spelled-out name
# Sorted longest-first so multi-character sequences match before single chars

GREEK_MAP: dict[str, str] = {
    # Delta variants (common in engineering: Δv, ΔT, ΔP)
    "Δv":    "delta-v velocity change",
    "ΔT":    "delta T temperature difference",
    "ΔP":    "delta P pressure difference",
    "Δ":     "delta change in",
    "delta-v": "delta-v velocity change",
    "delta_v": "delta-v velocity change",

    # Theta variants (thermal resistance: θ_ja, θ_jc, θ_sa)
    "θ_ja":  "theta junction-to-ambient thermal resistance",
    "θ_jc":  "theta junction-to-case thermal resistance",
    "θ_cs":  "theta case-to-sink thermal resistance",
    "θ_sa":  "theta sink-to-ambient thermal resistance",
    "θ":     "theta thermal resistance",

    # Eta variants (efficiency: η_f fin efficiency, η_o overall surface efficiency)
    "η_f":   "eta fin efficiency",
    "η_o":   "eta overall surface efficiency",
    "η":     "eta efficiency",

    # Sigma variants (stress: σ, σ_vm Von Mises)
    "σ_vm":  "sigma Von Mises stress",
    "σ_x":   "sigma normal stress x-direction",
    "σ_y":   "sigma normal stress y-direction",
    "σ":     "sigma normal stress",

    # Tau (shear stress)
    "τ_xy":  "tau shear stress",
    "τ":     "tau shear stress torsion",

    # Rho (density)
    "ρ":     "rho density",

    # Mu (viscosity)
    "μ":     "mu dynamic viscosity",

    # Nu (Nusselt number, kinematic viscosity)
    "ν":     "nu kinematic viscosity",

    # Epsilon (emissivity, expansion ratio)
    "ε":     "epsilon emissivity expansion ratio",

    # Gamma (ratio of specific heats)
    "γ":     "gamma ratio of specific heats",

    # Lambda (thermal conductivity in some notations, eigenvalue)
    "λ":     "lambda latent heat thermal conductivity",

    # Pi
    "π":     "pi",

    # Omega (angular velocity)
    "ω":     "omega angular velocity",

    # Alpha (thermal diffusivity)
    "α":     "alpha thermal diffusivity angle of attack",

    # Beta (coefficient of thermal expansion)
    "β":     "beta coefficient of thermal expansion",
}

# ── Engineering Abbreviations ─────────────────────────────────────────────────
# Domain-specific abbreviations that embeddings may not understand in isolation.
# Expanded to their full meaning so semantic retrieval works correctly.

ABBREVIATIONS: dict[str, str] = {
    # Thermal / Electronics cooling
    "TIM":      "thermal interface material",
    "BLT":      "bond line thickness",
    "PCM":      "phase change material",
    "TDP":      "thermal design power",
    "HTPB":     "hydroxyl-terminated polybutadiene",
    "CFD":      "computational fluid dynamics",
    "FEM":      "finite element method",
    "FEA":      "finite element analysis",
    "Nu":       "Nusselt number",
    "Re":       "Reynolds number",
    "Pr":       "Prandtl number",
    "Ra":       "Rayleigh number",
    "Bi":       "Biot number",
    "Fo":       "Fourier number",

    # Propulsion
    "Isp":      "specific impulse",
    "I_sp":     "specific impulse",
    "TWR":      "thrust-to-weight ratio",
    "LOX":      "liquid oxygen propellant",
    "RP-1":     "rocket propellant kerosene",
    "LH2":      "liquid hydrogen propellant",
    "MMH":      "monomethyl hydrazine",
    "NTO":      "nitrogen tetroxide oxidizer",
    "GEO":      "geostationary orbit",
    "LEO":      "low Earth orbit",
    "ISP":      "specific impulse",
    "HTPB":     "hydroxyl-terminated polybutadiene propellant binder",

    # Structural
    "FOS":      "factor of safety",
    "UTS":      "ultimate tensile strength",
    "YS":       "yield strength",
    "S_y":      "yield strength",
    "S_u":      "ultimate tensile strength",
    "S_e":      "endurance limit fatigue",
    "k_f":      "fatigue stress concentration factor",

    # General engineering
    "CAD":      "computer-aided design",
    "CAE":      "computer-aided engineering",
    "EDA":      "electronic design automation",
    "MEMS":     "micro electro mechanical systems",
    "PCB":      "printed circuit board",
    "COTS":     "commercial off-the-shelf",
    "MIL-SPEC": "military specification",
    "DO-178":   "avionics software safety standard",
    "FMEA":     "failure mode and effects analysis",
}

# ── Project-Specific Glossary (per-project extension point) ──────────────────
# Projects can register their own terminology at runtime.
# Key = term as it appears in documents, Value = expanded meaning.
_project_glossaries: dict[str, dict[str, str]] = {}


def register_project_glossary(project_id: str, glossary: dict[str, str]) -> None:
    """
    Register a project-specific terminology glossary.

    Called at document upload time so that project-specific terms
    (e.g. "NEXUS-TPS" = "NEXUS thermal protection system") are correctly
    expanded during both indexing and query preprocessing.

    Args:
        project_id: Unique project identifier (used as metadata filter)
        glossary:   Dict mapping term → expanded meaning
    """
    _project_glossaries[project_id] = glossary
    logger.info(f"Registered glossary for project '{project_id}': {len(glossary)} terms")


def _apply_map(text: str, mapping: dict[str, str]) -> str:
    """
    Apply a term→expansion mapping to text.
    Sorts by key length descending so longer patterns match first
    (e.g. "θ_ja" matches before "θ").
    Appends expansions in-line: "θ_ja (theta junction-to-ambient thermal resistance)"
    """
    sorted_keys = sorted(mapping.keys(), key=len, reverse=True)
    for term, expansion in zip(sorted_keys, [mapping[k] for k in sorted_keys]):
        if term in text and expansion not in text:
            # Append the expansion in parentheses on first occurrence only
            text = text.replace(term, f"{term} ({expansion})", 1)
    return text


def normalize_query(query: str, project_id: Optional[str] = None) -> str:
    """
    Normalize a search query before embedding.

    Stages:
      1. Apply Greek letter expansions (θ → theta thermal resistance)
      2. Apply standard engineering abbreviations (Isp → specific impulse)
      3. Apply project-specific glossary if project_id provided

    Returns the enriched query string. The original notation is preserved
    alongside the expansion so BOTH forms are present in the embedding.

    Example:
      Input:  "Calculate θ_ja for a chip with Isp 220s"
      Output: "Calculate θ_ja (theta junction-to-ambient thermal resistance)
               for a chip with Isp (specific impulse) 220s"
    """
    enriched = query

    # Stage 1: Greek letters
    enriched = _apply_map(enriched, GREEK_MAP)

    # Stage 2: Standard abbreviations
    enriched = _apply_map(enriched, ABBREVIATIONS)

    # Stage 3: Project glossary
    if project_id and project_id in _project_glossaries:
        enriched = _apply_map(enriched, _project_glossaries[project_id])

    if enriched != query:
        logger.debug(f"Query normalized: '{query[:60]}' → '{enriched[:80]}'")

    return enriched


def normalize_document(text: str, project_id: Optional[str] = None) -> str:
    """
    Normalize document text before embedding at ingestion time.
    Same pipeline as normalize_query — ensures symmetric expansion
    so query and document embeddings exist in the same semantic space.
    """
    return normalize_query(text, project_id=project_id)


def extract_technical_terms(text: str) -> list[str]:
    """
    Extract technical terms from text for BM25 keyword index.
    Identifies:
      - Greek letter notation (θ_ja, η_f, σ_vm)
      - Uppercase abbreviations (TIM, BLT, TWR, Isp)
      - Subscript patterns (h_conv, k_eff, T_surface)
      - Equation-like patterns (Q = h*A*dT)
    """
    terms = []

    # Greek letters (Unicode)
    greek_pattern = re.compile(r'[αβγδεζηθικλμνξπρστυφχψωΑΒΓΔΕΖΗΘΙΚΛΜΝΞΠΡΣΤΥΦΧΨΩ][_\w]*')
    terms.extend(greek_pattern.findall(text))

    # Uppercase abbreviations (2-6 chars)
    abbrev_pattern = re.compile(r'\b[A-Z]{2,6}\b')
    terms.extend(abbrev_pattern.findall(text))

    # Subscript variable patterns (h_conv, k_eff, T_j, etc.)
    subscript_pattern = re.compile(r'\b[a-zA-Z]{1,3}_[a-zA-Z]{1,4}\b')
    terms.extend(subscript_pattern.findall(text))

    # Remove duplicates, preserve order
    seen = set()
    unique = []
    for t in terms:
        if t not in seen:
            seen.add(t)
            unique.append(t)

    return unique
