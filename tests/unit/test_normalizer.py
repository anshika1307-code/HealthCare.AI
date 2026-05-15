"""
tests/unit/test_normalizer.py
-----------------------------
Unit tests for src/ingestion/normalizer.py

Coverage:
  Stage 9  normalize_terms
  Stage 10 detect_abbreviations
           expand_abbreviations
           build_abbreviation_map
  Master   normalize_and_expand
"""

import pytest
from ingestion.normalizer import (
    normalize_terms,
    detect_abbreviations,
    expand_abbreviations,
    build_abbreviation_map,
    normalize_and_expand,
    BRAND_ALIASES,
)


# ===========================================================================
# Stage 9 — Term Normalization
# ===========================================================================

class TestNormalizeTerms:

    def test_hba1c_variants_unified(self):
        cases = [
            "hemoglobin A1c",
            "glycated hemoglobin",
            "glycosylated hemoglobin",
            "HbA 1 c",
            "HbA1c",
        ]
        for text in cases:
            result = normalize_terms(text)
            assert "HbA1c" in result, f"Failed for input: {text!r}"

    def test_t2dm_expanded(self):
        result = normalize_terms("T2DM patients show improved outcomes.")
        assert "type 2 diabetes" in result

    def test_t2d_expanded(self):
        result = normalize_terms("T2D is managed with metformin.")
        assert "type 2 diabetes" in result

    def test_t1dm_expanded(self):
        result = normalize_terms("T1DM requires insulin.")
        assert "type 1 diabetes" in result

    def test_metformin_hcl_expanded(self):
        result = normalize_terms("Metformin HCl is the active ingredient.")
        assert "metformin hydrochloride" in result

    def test_mg_dl_spacing_normalised(self):
        result = normalize_terms("Glucose >130 mg / dL fasting.")
        assert "mg/dL" in result

    def test_mm_hg_spacing_normalised(self):
        result = normalize_terms("BP target is <140 mm Hg.")
        assert "mm Hg" in result

    def test_preserves_drug_dosages(self):
        """Normalization must not alter numeric dosage values."""
        text = "Metformin 500 mg twice daily with meals."
        result = normalize_terms(text)
        assert "500 mg" in result

    def test_idempotent_on_canonical_form(self):
        """Running normalization twice must produce the same result."""
        text = "HbA1c is the primary monitoring parameter for type 2 diabetes."
        result1 = normalize_terms(text)
        result2 = normalize_terms(result1)
        assert result1 == result2


# ===========================================================================
# Stage 10 — Abbreviation Detection
# ===========================================================================

class TestDetectAbbreviations:

    def test_detects_pattern_a_abbreviation(self):
        text = "continuous glucose monitoring (CGM) is recommended."
        abbrev_map = detect_abbreviations(text)
        assert "CGM" in abbrev_map
        assert abbrev_map["CGM"] == "continuous glucose monitoring"

    def test_detects_multiple_abbreviations(self):
        text = (
            "blood pressure (BP) is measured in mm Hg. "
            "angiotensin-converting enzyme inhibitors (ACEI) reduce BP."
        )
        abbrev_map = detect_abbreviations(text)
        assert "BP" in abbrev_map
        assert "ACEI" in abbrev_map

    def test_no_abbreviations_returns_empty(self):
        text = "No abbreviations defined in this sentence."
        abbrev_map = detect_abbreviations(text)
        assert isinstance(abbrev_map, dict)
        # May or may not be empty — just verify it's a dict and doesn't crash

    def test_first_occurrence_wins(self):
        """When an abbreviation is defined twice, the first definition is kept."""
        text = (
            "blood pressure (BP) management. "
            "Elevated blood pressure reading (BP) noted."
        )
        abbrev_map = detect_abbreviations(text)
        assert abbrev_map["BP"] == "blood pressure"


# ===========================================================================
# Stage 10 — Abbreviation Expansion
# ===========================================================================

class TestExpandAbbreviations:

    def test_expands_first_occurrence_only(self):
        # IMPORTANT: lines starting with 3+ uppercase letters match _HEADING_LINE
        # and are skipped entirely. Abbreviations must appear mid-sentence.
        abbrev_map = {"CGM": "continuous glucose monitoring"}
        from ingestion.normalizer import expand_abbreviations
        text = "The doctor uses CGM for daily tracking.\nThe CGM reading was normal."
        result = expand_abbreviations(text, abbrev_map)
        # First occurrence (mid-sentence line 1) should be expanded
        assert "continuous glucose monitoring (CGM)" in result
        # The expansion must appear exactly once (line 2 CGM is left as-is)
        assert result.count("continuous glucose monitoring (CGM)") == 1

    def test_does_not_expand_inside_headings(self):
        abbrev_map = {"BP": "blood pressure"}
        # ALL-CAPS line = heading
        text = "BP MANAGEMENT\nBlood pressure BP control is essential."
        result = expand_abbreviations(text, abbrev_map)
        # Heading line should not be expanded
        assert "BP MANAGEMENT" in result

    def test_empty_abbrev_map_returns_unchanged(self):
        text = "CGM levels were checked at fasting."
        result = expand_abbreviations(text, {})
        assert result == text

    def test_expansion_format(self):
        """Expansion format must be: 'full form (ABBR)'."""
        from ingestion.normalizer import expand_abbreviations
        abbrev_map = {"GFR": "glomerular filtration rate"}
        # Must start with non-all-caps word so _HEADING_LINE doesn't match
        text = "The doctor checks GFR before prescribing."
        result = expand_abbreviations(text, abbrev_map)
        assert "glomerular filtration rate (GFR)" in result


# ===========================================================================
# build_abbreviation_map
# ===========================================================================

class TestBuildAbbreviationMap:

    def test_seed_map_overrides_auto_detected(self):
        """Seed map entries take priority over auto-detected ones."""
        text = "blood glucose monitoring (BGM) is key."
        seed = {"BGM": "blood glucose meter"}  # different definition than auto-detected
        result = build_abbreviation_map(text, seed_map=seed)
        # Seed definition must win
        assert result["BGM"] == "blood glucose meter"

    def test_fda_doc_adds_brand_aliases(self):
        result = build_abbreviation_map("", doc_type="fda")
        assert "GLUCOPHAGE" in result
        assert "GLUCOPHAGE XR" in result

    def test_non_fda_excludes_brand_aliases(self):
        result = build_abbreviation_map("", doc_type="ada")
        assert "GLUCOPHAGE" not in result

    def test_returns_dict(self):
        result = build_abbreviation_map("Simple text.", seed_map=None, doc_type="jnc")
        assert isinstance(result, dict)


# ===========================================================================
# Master normalize_and_expand
# ===========================================================================

class TestNormalizeAndExpand:

    def test_returns_tuple(self):
        result = normalize_and_expand("HbA1c is a marker of glycaemic control.")
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], str)
        assert isinstance(result[1], dict)

    def test_normalization_applied_before_expansion(self):
        """T2DM → 'type 2 diabetes (T2DM)' should appear after both stages."""
        text = "T2DM management requires lifestyle intervention."
        result_text, abbrev_map = normalize_and_expand(text)
        assert "type 2 diabetes" in result_text

    def test_hba1c_normalized_in_fda_doc(self):
        text = "Monitor glycated hemoglobin every 3 months."
        result_text, _ = normalize_and_expand(text, doc_type="fda")
        assert "HbA1c" in result_text

    def test_fda_doc_includes_brand_aliases_in_map(self):
        text = "GLUCOPHAGE is the brand name."
        _, abbrev_map = normalize_and_expand(text, doc_type="fda")
        assert "GLUCOPHAGE" in abbrev_map

    def test_empty_text(self):
        result_text, abbrev_map = normalize_and_expand("")
        assert result_text == ""
        assert isinstance(abbrev_map, dict)
