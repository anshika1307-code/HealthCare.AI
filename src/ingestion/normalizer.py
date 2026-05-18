"""
normalizer.py
-------------
Stage 9  — Medical term normalization (surface-form unification)
Stage 10 — Abbreviation detection & first-occurrence expansion

Rules:
- Normalization runs BEFORE abbreviation expansion.
- Brand names (GLUCOPHAGE) are NOT collapsed to generics — alias only.
- Drug dosages and measurement values are never touched.
- Abbreviation expansion: first occurrence → "full form (ABBR)",
  subsequent occurrences left as-is.
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

# Type alias — defined here to avoid circular import with cleaner.py
AbbrevMap = dict  # dict[str, str]


# ===========================================================================
# Stage 9 — Term Normalization
# ===========================================================================

# Each entry: (compiled_pattern, canonical_replacement)
# Order matters: more specific patterns first.
_NORMALIZATION_MAP: list[tuple[re.Pattern, str]] = [
    # Vitamin B12 variants
    (re.compile(r"[Vv]itamin\s+B\s*[-]?\s*12\b"), "Vitamin B12"),
    # HbA1c variants
    (
        re.compile(
            r"\b(HbA\s*1\s*c|hemoglobin\s+A1c|glycated\s+hemoglobin|glycosylated\s+hemoglobin)\b",
            re.IGNORECASE,
        ),
        "HbA1c",
    ),
    # Blood pressure (casing/hyphen only — do not expand to include "(BP)" here,
    # that is handled by abbreviation expansion for first-occurrence)
    (re.compile(r"\bblood[-\s]pressure\b", re.IGNORECASE), "blood pressure"),
    # T2D/T2DM → full form (abbreviation expansion will handle first occurrence)
    (re.compile(r"\bT2DM\b"), "type 2 diabetes (T2DM)"),
    (re.compile(r"\bT2D\b"), "type 2 diabetes (T2DM)"),
    # T1D/T1DM
    (re.compile(r"\bT1DM\b"), "type 1 diabetes (T1DM)"),
    (re.compile(r"\bT1D\b"), "type 1 diabetes (T1DM)"),
    # metformin HCl → metformin hydrochloride (salt form must stay)
    (re.compile(r"\bmetformin\s+HCl\b", re.IGNORECASE), "metformin hydrochloride"),
    # mm Hg spacing normalisation
    (re.compile(r"\bmm\s+Hg\b"), "mm Hg"),
    # mg / dL spacing
    (re.compile(r"\bmg\s*/\s*dL\b", re.IGNORECASE), "mg/dL"),
]

# Brand name alias note — added to abbreviation_map, NOT substituted in text
BRAND_ALIASES: dict[str, str] = {
    "GLUCOPHAGE": "metformin hydrochloride (brand: GLUCOPHAGE)",
    "GLUCOPHAGE XR": "metformin hydrochloride extended-release (brand: GLUCOPHAGE XR)",
}


def normalize_terms(text: str) -> str:
    """Apply the term normalization map to text."""
    for pattern, canonical in _NORMALIZATION_MAP:
        text = pattern.sub(canonical, text)
    return text


# ===========================================================================
# Stage 10 — Abbreviation Detection & Expansion
# ===========================================================================

# Pattern A: "full form (ABBR)" — most common in clinical docs
# Captures: group(1) = full form (1+ words, may contain hyphens)
#           group(2) = abbreviation (2-6 uppercase letters/digits)
_ABBREV_PATTERN_A = re.compile(r"([A-Za-z][a-z\s\-]{2,40})\s+\(([A-Z][A-Z0-9]{1,5})\)")

# Pattern B: "ABBR   full form" — JNC abbreviation table lines
# (Handled separately in cleaner.parse_jnc_abbreviation_list — not repeated here)

# Lines that are headings — do not expand inside these.
# FIX (2026-05-16): original [A-Z][A-Z\s]{3,} matched lines STARTING with 3+
# uppercase letters, treating "CGM is used...", "GFR should..." as headings and
# silently skipping abbreviation expansion for those entire lines. Fix: add $ anchor
# so the all-caps pattern must span the WHOLE line (true FDA headings like "DESCRIPTION"
# or "WARNINGS AND PRECAUTIONS" are all-caps to end of line; prose starting with an
# abbreviation is not).
_HEADING_LINE = re.compile(r"^(?:[A-Z][A-Z\s\-\/]{3,}$|\d+\.\d+[a-z]?\s)")


def detect_abbreviations(text: str) -> dict[str, str]:
    """
    Auto-detect abbreviations from Pattern A ("full form (ABBR)") in the text.

    Returns a map of {ABBR: full_form} found in this document.
    This supplements any pre-seeded map (e.g., from JNC abbreviation list).
    """
    abbrev_map: dict[str, str] = {}
    for m in _ABBREV_PATTERN_A.finditer(text):
        full_form = m.group(1).strip()
        abbrev = m.group(2).strip()
        if abbrev not in abbrev_map:
            abbrev_map[abbrev] = full_form
            logger.debug("Detected abbreviation: %s = '%s'", abbrev, full_form)
    return abbrev_map


def expand_abbreviations(text: str, abbrev_map: dict[str, str]) -> str:
    """
    Expand each abbreviation on its FIRST occurrence in the text only.

    Expansion: "CGM" → "continuous glucose monitoring (CGM)"
    Subsequent occurrences: left as-is.

    Skips expansion inside heading lines to avoid breaking structure markers.
    """
    if not abbrev_map:
        return text

    expanded: set[str] = set()
    lines = text.splitlines()
    result_lines: list[str] = []

    for line in lines:
        is_heading = bool(_HEADING_LINE.match(line.strip()))

        for abbrev, full_form in abbrev_map.items():
            if is_heading:
                break  # don't touch headings
            if abbrev in expanded:
                continue  # already expanded once in a previous line

            pattern = re.compile(rf"\b{re.escape(abbrev)}\b")

            def _replacer(m: re.Match, _abbrev: str = abbrev, _full: str = full_form) -> str:
                if _abbrev not in expanded:
                    expanded.add(_abbrev)
                    return f"{_full} ({_abbrev})"
                return m.group(0)

            line = pattern.sub(_replacer, line)

        result_lines.append(line)

    return "\n".join(result_lines)


def build_abbreviation_map(
    text: str,
    seed_map: dict[str, str] | None = None,
    doc_type: str = "",
) -> dict[str, str]:
    """
    Build the final abbreviation map for a document by merging:
    1. seed_map (from JNC abbreviation list or other pre-seeded data)
    2. Auto-detected abbreviations from Pattern A in the document text
    3. Brand aliases (added as informational entries)

    The seed_map takes priority over auto-detected entries for the same key.
    """
    final_map: dict[str, str] = {}

    # Start with auto-detected
    final_map.update(detect_abbreviations(text))

    # Seed map overrides auto-detected
    if seed_map:
        final_map.update(seed_map)

    # Add brand aliases (informational — not expanded in text)
    if doc_type == "fda":
        final_map.update(BRAND_ALIASES)

    logger.info("Abbreviation map built: %d entries (doc_type=%s)", len(final_map), doc_type)
    return final_map


def normalize_and_expand(
    text: str,
    seed_abbrev_map: dict[str, str] | None = None,
    doc_type: str = "",
) -> tuple[str, dict[str, str]]:
    """
    Run stage 9 (normalization) then stage 10 (abbreviation expansion).

    Returns
    -------
    text : str
        Normalized and expanded text.
    abbrev_map : dict
        Full abbreviation map used (for storage in chunk metadata / audit).
    """
    # Stage 9: term normalization first
    text = normalize_terms(text)

    # Build final abbreviation map (detect from normalized text)
    abbrev_map = build_abbreviation_map(text, seed_map=seed_abbrev_map, doc_type=doc_type)

    # Stage 10: expand first occurrences
    text = expand_abbreviations(text, abbrev_map)

    return text, abbrev_map
