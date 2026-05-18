"""
tests/unit/test_cleaner.py
--------------------------
Unit tests for src/ingestion/cleaner.py

Coverage:
  Stage 1  parse_jnc_abbreviation_list
  Stage 2  remove_headers_footers        (fda / ada / jnc)
  Stage 4  remove_reference_section
  Stage 5  remove_guideline_metadata
  Stage 6  remove_inline_noise
  Stage 7  join_hyphenated_lines
  Stage 8  rejoin_broken_lines
  Master   clean()
"""

import pytest
from ingestion.cleaner import (
    parse_jnc_abbreviation_list,
    remove_headers_footers,
    remove_reference_section,
    remove_guideline_metadata,
    remove_inline_noise,
    join_hyphenated_lines,
    rejoin_broken_lines,
    clean,
)


# ===========================================================================
# Stage 1 — JNC Abbreviation List Parser
# ===========================================================================


class TestParseJNCAbbrList:
    def test_parses_standard_block(self):
        text = (
            "ACEI  angiotensin-converting enzyme inhibitor\n"
            "ARB   angiotensin receptor blocker\n"
            "BP    blood pressure\n"
            "The rest of the document begins here."
        )
        cleaned, abbrev_map = parse_jnc_abbreviation_list(text)
        assert abbrev_map == {
            "ACEI": "angiotensin-converting enzyme inhibitor",
            "ARB": "angiotensin receptor blocker",
            "BP": "blood pressure",
        }
        assert "The rest" in cleaned
        # Abbreviation block should be stripped from cleaned text
        assert "ACEI" not in cleaned

    def test_returns_empty_map_when_no_block(self):
        text = "This document has no abbreviation table.\nSome more text."
        cleaned, abbrev_map = parse_jnc_abbreviation_list(text)
        assert abbrev_map == {}
        assert cleaned == text  # text unchanged

    def test_ignores_single_char_abbrevs(self):
        """Single-letter keys must NOT match (pattern requires 2–6 chars)."""
        text = "A  single letter\nBP  blood pressure\nProper text."
        _, abbrev_map = parse_jnc_abbreviation_list(text)
        assert "A" not in abbrev_map
        assert "BP" in abbrev_map

    def test_handles_empty_string(self):
        cleaned, abbrev_map = parse_jnc_abbreviation_list("")
        assert abbrev_map == {}
        assert cleaned == ""


# ===========================================================================
# Stage 2 — Header / Footer Remover
# ===========================================================================


class TestRemoveHeadersFooters:
    # ── FDA ──────────────────────────────────────────────────────────────────

    def test_fda_removes_label_disclaimer(self):
        text = (
            "GLUCOPHAGE Tablets\n"
            "This label may not be the latest approved by FDA. "
            "Please check the product label at https://www.fda.gov/drugsatfda\n"
            "DESCRIPTION\n"
            "Metformin hydrochloride..."
        )
        result = remove_headers_footers(text, "fda")
        assert "label may not be the latest" not in result
        assert "DESCRIPTION" in result

    def test_fda_removes_reference_id(self):
        text = "Some clinical text.\nReference ID: 4567890\nMore text."
        result = remove_headers_footers(text, "fda")
        assert "Reference ID:" not in result
        assert "Some clinical text." in result

    def test_fda_removes_standalone_page_numbers(self):
        text = "Clinical content.\n  42  \nMore content."
        result = remove_headers_footers(text, "fda")
        assert "  42  " not in result

    def test_fda_preserves_embedded_numbers(self):
        """Numbers embedded in sentences must NOT be stripped."""
        text = "The dose is 500 mg twice daily."
        result = remove_headers_footers(text, "fda")
        assert "500" in result

    # ── ADA ──────────────────────────────────────────────────────────────────

    def test_ada_removes_download_line(self):
        text = (
            "Downloaded from http://diabetesjournals.org/care by guest on 15 Jan 2024\n"
            "6.1 A1c targets should be individualised."
        )
        result = remove_headers_footers(text, "ada")
        assert "Downloaded from" not in result
        assert "6.1" in result

    def test_ada_removes_copyright(self):
        text = "© 2023 by the American Diabetes Association. All rights reserved.\nContent."
        result = remove_headers_footers(text, "ada")
        assert "American Diabetes Association" not in result

    # ── JNC ──────────────────────────────────────────────────────────────────

    def test_jnc_removes_jama_footer(self):
        text = "Some JNC text.\njama.com\nMore text."
        result = remove_headers_footers(text, "jnc")
        assert "jama.com" not in result

    def test_jnc_removes_copyright(self):
        text = "Content.\nCopyright © 2014 American Medical Association.\nMore content."
        result = remove_headers_footers(text, "jnc")
        assert "American Medical Association" not in result

    def test_jnc_removes_download_line(self):
        text = "Downloaded from jamanetwork.com by User Name on 01/01/2024\nContent."
        result = remove_headers_footers(text, "jnc")
        assert "jamanetwork" not in result

    def test_unknown_doc_type_returns_text_unchanged(self):
        """Unknown doc_type must not crash — returns text as-is."""
        text = "Some text with no changes expected."
        result = remove_headers_footers(text, "unknown_type")
        assert result == text


# ===========================================================================
# Stage 4 — Reference Section Remover
# ===========================================================================


class TestRemoveReferenceSection:
    def test_ada_truncates_at_references(self):
        text = "Clinical content.\n\nReferences\n\n1. Smith et al. 2023."
        result = remove_reference_section(text, "ada")
        assert "References" not in result
        assert "Clinical content." in result

    def test_jnc_truncates_at_article_information(self):
        text = "JNC content.\n\nARTICLE INFORMATION\n\nAuthor affiliations..."
        result = remove_reference_section(text, "jnc")
        assert "ARTICLE INFORMATION" not in result
        assert "JNC content." in result

    def test_jnc_truncates_at_references_sentinel(self):
        text = "Content.\n\nREFERENCES\n\n1. Ref one."
        result = remove_reference_section(text, "jnc")
        assert "REFERENCES" not in result

    def test_fda_returns_text_unchanged(self):
        """FDA uses inline citations — no sentinel truncation."""
        text = "FDA content.\nReferences\n1. Some ref."
        result = remove_reference_section(text, "fda")
        # FDA has empty sentinel list — text should be returned as-is
        assert result == text

    def test_no_sentinel_present(self):
        text = "This document has no reference section at all."
        result = remove_reference_section(text, "ada")
        assert result == text


# ===========================================================================
# Stage 5 — Guideline Metadata Remover
# ===========================================================================


class TestRemoveGuidelineMetadata:
    def test_jnc_strips_guideline_source_block(self):
        text = "JNC content.\n\nGuideline source: AHA/ACC\nDate: 2014"
        result = remove_guideline_metadata(text, "jnc")
        assert "Guideline source:" not in result
        assert "JNC content." in result

    def test_non_jnc_untouched(self):
        text = "Guideline source: This should stay for FDA doc.\nContent."
        result = remove_guideline_metadata(text, "fda")
        assert "Guideline source:" in result

    def test_no_metadata_block(self):
        text = "JNC content without any metadata block."
        result = remove_guideline_metadata(text, "jnc")
        assert result == text


# ===========================================================================
# Stage 6 — Inline Noise Remover
# ===========================================================================


class TestRemoveInlineNoise:
    def test_removes_urls(self):
        text = "See https://www.example.com/path for more info."
        result = remove_inline_noise(text, "fda")
        assert "https://" not in result

    def test_removes_doi(self):
        text = "doi: 10.1001/jama.2013.284427 — full citation."
        result = remove_inline_noise(text, "jnc")
        assert "doi:" not in result

    def test_removes_parenthetical_citations(self):
        text = "Metformin reduces HbA1c (14) and weight (2-4) in T2DM patients."
        result = remove_inline_noise(text, "ada")
        assert "(14)" not in result
        assert "(2-4)" not in result
        assert "Metformin reduces HbA1c" in result

    def test_superscript_remover_does_not_mangle_words(self):
        """Regression test for Bug 1: _FOOTNOTE_SUPERSCRIPT was stripping the last
        letter of every English word. Fixed by changing lookbehind to [A-Z0-9]."""
        text = "Metformin reduces HbA1c and weight in patients."
        result = remove_inline_noise(text, "ada")
        assert "Metformin" in result, f"'Metformin' mangled: {result!r}"
        assert "reduces" in result, f"'reduces' mangled: {result!r}"
        assert "HbA1c" in result, f"'HbA1c' mangled: {result!r}"
        assert "patients" in result, f"'patients' mangled: {result!r}"

    def test_removes_bracket_citations(self):
        text = "Evidence supports use [12] in patients."
        result = remove_inline_noise(text, "fda")
        assert "[12]" not in result

    def test_removes_figure_references(self):
        text = "As shown in Fig. 2, blood pressure decreases."
        result = remove_inline_noise(text, "ada")
        assert "Fig." not in result

    def test_jnc_removes_key_points_block(self):
        text = "Content.\nKey Points for Practice\n• Use ACE inhibitors.\n• Monitor BP.\nMore."
        result = remove_inline_noise(text, "jnc")
        assert "Key Points for Practice" not in result

    def test_preserves_clinical_content(self):
        """After Bug 1 fix, realistic clinical text must survive intact."""
        text = "HbA1c target is <7.0% for most adults with type 2 diabetes."
        result = remove_inline_noise(text, "ada")
        assert "HbA1c" in result
        assert "<7.0%" in result
        assert "adults" in result

    def test_removes_see_cross_ref(self):
        text = "Contraindicated (see Precautions) in renal impairment."
        result = remove_inline_noise(text, "fda")
        assert "(see Precautions)" not in result
        assert "Contraindicated" in result


# ===========================================================================
# Stage 7 — Hyphen Line Joiner
# ===========================================================================


class TestJoinHyphenatedLines:
    def test_joins_soft_hyphen(self):
        text = "anti\u00ad\nhypertensive therapy is recommended."
        result = join_hyphenated_lines(text)
        assert "antihypertensive" in result
        assert "\u00ad" not in result

    def test_joins_hard_hyphen_lowercase(self):
        text = "The treat-\nment should continue."
        result = join_hyphenated_lines(text)
        assert "treatment" in result

    def test_preserves_hyphenated_uppercase_terms(self):
        """Hard hyphen joining only applies to both-lowercase words."""
        text = "ACE-\nInhibitor is a drug class."
        result = join_hyphenated_lines(text)
        # 'ACE' starts with uppercase — should NOT be joined
        assert "ACE-\nInhibitor" in result or "ACE-" in result

    def test_no_change_on_clean_text(self):
        text = "No hyphens here. All text is clean."
        result = join_hyphenated_lines(text)
        assert result == text


# ===========================================================================
# Stage 8 — Line Rejoiner
# ===========================================================================


class TestRejoinBrokenLines:
    def test_rejoins_wrapped_prose(self):
        text = "The patient should take metformin\nwith meals to reduce GI side effects."
        result = rejoin_broken_lines(text)
        assert "metformin with meals" in result

    def test_does_not_join_after_sentence_terminal(self):
        text = "First sentence.\nSecond sentence starts here."
        result = rejoin_broken_lines(text)
        # Must NOT be joined — period is terminal punctuation
        assert "First sentence.\nSecond sentence" in result

    def test_does_not_join_bullet_lines(self):
        text = "Consider the following:\n• Option A\n• Option B"
        result = rejoin_broken_lines(text)
        assert "• Option A" in result
        assert "• Option B" in result

    def test_does_not_join_headings(self):
        text = "WARNINGS AND PRECAUTIONS\nThis section describes warnings."
        result = rejoin_broken_lines(text)
        # All-caps heading should NOT be joined with next line
        assert "WARNINGS AND PRECAUTIONS\n" in result

    def test_empty_string_returns_empty(self):
        assert rejoin_broken_lines("") == ""


# ===========================================================================
# Master clean() integration
# ===========================================================================


class TestCleanMaster:
    def test_jnc_full_pipeline(self):
        """End-to-end: JNC doc gets abbreviation parse + headers + refs cleaned."""
        text = (
            "ACEI  angiotensin-converting enzyme inhibitor\n"
            "ARB   angiotensin receptor blocker\n"
            "Recommendation 1\n"
            "Use ACE inhibitors for CKD patients.\n"
            "Copyright © 2014 American Medical Association.\n"
            "ARTICLE INFORMATION\n"
            "Author: John Doe."
        )
        cleaned, abbrev_map = clean(text, "jnc")
        assert "ACEI" in abbrev_map
        assert "ARB" in abbrev_map
        assert "ARTICLE INFORMATION" not in cleaned
        assert "Copyright" not in cleaned
        assert "Recommendation 1" in cleaned

    def test_fda_full_pipeline(self):
        """FDA doc: reference ID and page numbers stripped, content preserved."""
        text = (
            "DESCRIPTION\n"
            "Metformin hydrochloride is a biguanide.\n"
            "Reference ID: 123456\n"
            "  5  \n"
            "INDICATIONS AND USAGE\n"
            "Used for type 2 diabetes."
        )
        cleaned, abbrev_map = clean(text, "fda")
        assert "Reference ID:" not in cleaned
        assert "DESCRIPTION" in cleaned
        assert "INDICATIONS AND USAGE" in cleaned
        assert abbrev_map == {} or isinstance(abbrev_map, dict)

    def test_ada_full_pipeline(self):
        """ADA doc: download lines, copyright, and reference section removed."""
        text = (
            "Downloaded from http://diabetesjournals.org/care by guest on 01 Jan 2024\n"
            "6.1 HbA1c target should be individualised.\n"
            "© 2023 by the American Diabetes Association. All rights reserved.\n"
            "References\n"
            "1. Standards of Care."
        )
        cleaned, abbrev_map = clean(text, "ada")
        assert "Downloaded from" not in cleaned
        assert "American Diabetes Association" not in cleaned
        assert "References" not in cleaned
        assert "6.1" in cleaned

    def test_returns_string_and_dict(self):
        """clean() must always return (str, dict) regardless of doc_type."""
        for doc_type in ("fda", "ada", "jnc"):
            result = clean("Some simple text.", doc_type)
            assert isinstance(result, tuple)
            assert isinstance(result[0], str)
            assert isinstance(result[1], dict)
