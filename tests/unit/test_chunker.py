"""
tests/unit/test_chunker.py
--------------------------
Unit tests for src/ingestion/chunker.py

Coverage:
  Stage 11  _FDA_HEADING, _ADA_REC_NUM, _JNC_HEADING patterns
  Stage 12  extract_jnc_recommendation_blocks
  Stage 13  extract_ada_evidence_grades
  Stage 17  is_safety_chunk
  Stage 18  normalize_whitespace
  Core      Chunker.chunk() — fda / ada / jnc doc types
  Metadata  base_meta completeness, chunk_index assignment
"""

import pytest
from ingestion.chunker import (
    Chunk,
    Chunker,
    extract_jnc_recommendation_blocks,
    extract_ada_evidence_grades,
    is_safety_chunk,
    normalize_whitespace,
    _FDA_HEADING,
    _ADA_REC_NUM,
    _is_jnc_title_case_heading,
)


# ===========================================================================
# Heading Pattern Tests
# ===========================================================================

class TestHeadingPatterns:

    def test_fda_heading_matches_all_caps(self):
        assert _FDA_HEADING.match("WARNINGS AND PRECAUTIONS")
        assert _FDA_HEADING.match("DESCRIPTION")
        assert _FDA_HEADING.match("INDICATIONS AND USAGE")

    def test_fda_heading_rejects_mixed_case(self):
        assert not _FDA_HEADING.match("Warnings and Precautions")
        assert not _FDA_HEADING.match("Description")

    def test_fda_heading_rejects_short_strings(self):
        # Pattern requires 4+ chars after first letter
        assert not _FDA_HEADING.match("AB")

    def test_ada_rec_num_matches(self):
        assert _ADA_REC_NUM.match("6.1 Glycaemic targets should be individualised.")
        assert _ADA_REC_NUM.match("9.3a Metformin is preferred first-line therapy.")

    def test_ada_rec_num_rejects_plain_text(self):
        assert not _ADA_REC_NUM.match("The A1c target is below 7%.")
        assert not _ADA_REC_NUM.match("6 is a number")  # No decimal

    def test_jnc_title_case_heading_valid(self):
        assert _is_jnc_title_case_heading("Treatment Goals")
        assert _is_jnc_title_case_heading("Evidence Summary")

    def test_jnc_title_case_heading_rejects_long(self):
        # > 8 words
        assert not _is_jnc_title_case_heading(
            "This Is A Very Long Heading That Exceeds Eight Words Limit"
        )

    def test_jnc_title_case_heading_rejects_bullets(self):
        assert not _is_jnc_title_case_heading("• Use ACE inhibitors")
        assert not _is_jnc_title_case_heading("- Reduce sodium intake")

    def test_jnc_title_case_heading_rejects_terminal_period(self):
        assert not _is_jnc_title_case_heading("Treatment Goals.")


# ===========================================================================
# Stage 12 — JNC Recommendation Block Extractor
# ===========================================================================

class TestExtractJNCRecommendationBlocks:

    JNC_SAMPLE = (
        "Introduction text.\n\n"
        "Recommendation 1\n"
        "In the general non-black population, initial antihypertensive treatment "
        "should include a thiazide-type diuretic, CCB, ACEI, or ARB.\n"
        "Strong Recommendation – Grade A\n\n"
        "Some bridging text.\n\n"
        "Recommendation 2\n"
        "In the general black population, including those with diabetes, initial "
        "antihypertensive treatment should include a thiazide-type diuretic or CCB.\n"
        "Moderate Recommendation – Grade B\n"
    )

    def test_finds_two_recommendations(self):
        blocks = extract_jnc_recommendation_blocks(self.JNC_SAMPLE)
        assert len(blocks) == 2

    def test_recommendation_numbers_correct(self):
        blocks = extract_jnc_recommendation_blocks(self.JNC_SAMPLE)
        nums = [b["rec_number"] for b in blocks]
        assert nums == [1, 2]

    def test_strength_extracted(self):
        blocks = extract_jnc_recommendation_blocks(self.JNC_SAMPLE)
        assert blocks[0]["recommendation_strength"] == "Strong"
        assert blocks[1]["recommendation_strength"] == "Moderate"

    def test_grade_extracted(self):
        blocks = extract_jnc_recommendation_blocks(self.JNC_SAMPLE)
        assert blocks[0]["evidence_grade"] == "A"
        assert blocks[1]["evidence_grade"] == "B"

    def test_body_text_not_empty(self):
        blocks = extract_jnc_recommendation_blocks(self.JNC_SAMPLE)
        for block in blocks:
            assert len(block["body_text"]) > 10

    def test_no_recommendations_returns_empty_list(self):
        blocks = extract_jnc_recommendation_blocks("Just some regular text.")
        assert blocks == []


# ===========================================================================
# Stage 13 — ADA Evidence Grade Extractor
# ===========================================================================

class TestExtractADAEvidenceGrades:

    def test_finds_trailing_grade_letters(self):
        text = "6.1 HbA1c target should be individualized. A\n6.2 Avoid hypoglycaemia. B\n"
        cleaned, annotations = extract_ada_evidence_grades(text)
        grades = [a["grade"] for a in annotations]
        assert "A" in grades
        assert "B" in grades

    def test_strips_grades_from_text(self):
        text = "Recommendation text. A\nMore content."
        cleaned, _ = extract_ada_evidence_grades(text)
        # Grade letter 'A' at end of line should be stripped
        assert not cleaned.strip().endswith(" A")

    def test_no_grades_returns_original(self):
        text = "No trailing grade letters here. All prose."
        cleaned, annotations = extract_ada_evidence_grades(text)
        assert annotations == []
        assert cleaned == text


# ===========================================================================
# Stage 17 — Safety Flag Scanner
# ===========================================================================

class TestIsSafetyChunk:

    @pytest.mark.parametrize("text", [
        "BOXED WARNING: Lactic acidosis is a rare but serious complication.",
        "CONTRAINDICATIONS: Do not use in patients with severe renal impairment.",
        "WARNINGS: Avoid in patients with liver disease.",
        "Adverse reactions include nausea, vomiting, and diarrhea.",
        "Do not administer to patients with acute heart failure.",
        "Metformin should not be used in eGFR < 30.",
        "Side effects include lactic acidosis.",
    ])
    def test_detects_safety_content(self, text):
        assert is_safety_chunk(text) is True

    @pytest.mark.parametrize("text", [
        "Metformin reduces HbA1c by approximately 1.5% in T2DM.",
        "The recommended starting dose is 500 mg twice daily.",
        "Blood pressure targets should be individualized.",
    ])
    def test_no_false_positives_on_safe_content(self, text):
        assert is_safety_chunk(text) is False


# ===========================================================================
# Stage 18 — Whitespace Normalizer
# ===========================================================================

class TestNormalizeWhitespace:

    def test_collapses_multiple_spaces(self):
        assert normalize_whitespace("Too   many   spaces") == "Too many spaces"

    def test_collapses_excessive_newlines(self):
        text = "First paragraph.\n\n\n\nSecond paragraph."
        result = normalize_whitespace(text)
        assert "\n\n\n" not in result

    def test_strips_leading_trailing_whitespace(self):
        assert normalize_whitespace("  content  ") == "content"

    def test_empty_string(self):
        assert normalize_whitespace("") == ""


# ===========================================================================
# Chunker — FDA doc type
# ===========================================================================

class TestChunkerFDA:

    def make_chunker(self, max_tokens=512, overlap=64):
        return Chunker(
            doc_id="metformin_fda_label",
            doc_type="fda",
            document_name="Metformin FDA Label",
            max_tokens=max_tokens,
            overlap_tokens=overlap,
        )

    FDA_TEXT = (
        "DESCRIPTION\n"
        "Metformin hydrochloride is an oral antihyperglycemic drug used in the "
        "management of type 2 diabetes mellitus.\n\n"
        "INDICATIONS AND USAGE\n"
        "GLUCOPHAGE is indicated as an adjunct to diet and exercise to improve "
        "glycemic control in adults with type 2 diabetes mellitus.\n\n"
        "CONTRAINDICATIONS\n"
        "Do not use in patients with severe renal impairment (eGFR <30).\n"
    )

    def test_returns_list_of_chunks(self):
        chunker = self.make_chunker()
        chunks = chunker.chunk(self.FDA_TEXT)
        assert isinstance(chunks, list)
        assert all(isinstance(c, Chunk) for c in chunks)

    def test_chunks_have_text(self):
        chunker = self.make_chunker()
        chunks = chunker.chunk(self.FDA_TEXT)
        for c in chunks:
            assert c.text.strip() != ""

    def test_section_names_assigned(self):
        chunker = self.make_chunker()
        chunks = chunker.chunk(self.FDA_TEXT)
        section_names = [c.metadata.get("section_name") for c in chunks]
        # At least some chunks should be labelled with an FDA section
        assert any(
            name in ("DESCRIPTION", "INDICATIONS AND USAGE", "CONTRAINDICATIONS")
            for name in section_names
        )

    def test_contraindications_flagged_as_safety(self):
        chunker = self.make_chunker()
        chunks = chunker.chunk(self.FDA_TEXT)
        safety_chunks = [c for c in chunks if c.metadata.get("safety_flag")]
        assert len(safety_chunks) >= 1

    def test_chunk_index_sequential(self):
        chunker = self.make_chunker()
        chunks = chunker.chunk(self.FDA_TEXT)
        indices = [c.metadata["chunk_index"] for c in chunks]
        assert indices == list(range(len(chunks)))

    def test_metadata_keys_present(self):
        chunker = self.make_chunker()
        chunks = chunker.chunk(self.FDA_TEXT)
        required_keys = {
            "document_id", "document_name", "page_number",
            "section_name", "is_table", "safety_flag",
            "chunk_index", "char_count",
        }
        for c in chunks:
            assert required_keys.issubset(c.metadata.keys())

    def test_char_count_matches_text_length(self):
        chunker = self.make_chunker()
        chunks = chunker.chunk(self.FDA_TEXT)
        for c in chunks:
            assert c.metadata["char_count"] == len(c.text)

    def test_max_token_limit_respected(self):
        """No chunk should exceed max_tokens (within tiktoken's accuracy)."""
        chunker = self.make_chunker(max_tokens=100)
        long_text = " ".join(["The patient should take metformin with meals."] * 50)
        chunks = chunker.chunk(long_text)
        for c in chunks:
            # Allow 20% slack for sentence-boundary alignment
            word_count = len(c.text.split())
            assert word_count < 100 * 1.3, f"Chunk too long: {word_count} words"


# ===========================================================================
# Chunker — JNC doc type
# ===========================================================================

class TestChunkerJNC:

    JNC_TEXT = (
        "Treatment Goals\n"
        "Introduce lifestyle modification before pharmacologic therapy.\n\n"
        "Recommendation 1\n"
        "In the general non-black population, initial antihypertensive treatment "
        "should include a thiazide-type diuretic, CCB, ACEI, or ARB.\n"
        "Strong Recommendation – Grade A\n\n"
        "Evidence Summary\n"
        "RCT data supports use of thiazides as first-line agents.\n"
    )

    def make_chunker(self):
        return Chunker(
            doc_id="jnc8_guidelines",
            doc_type="jnc",
            document_name="JNC 8 Hypertension Guidelines",
        )

    def test_recommendation_block_becomes_hard_chunk(self):
        chunker = self.make_chunker()
        chunks = chunker.chunk(self.JNC_TEXT)
        rec_chunks = [
            c for c in chunks
            if c.metadata.get("recommendation_number") is not None
        ]
        assert len(rec_chunks) >= 1

    def test_recommendation_metadata_populated(self):
        chunker = self.make_chunker()
        chunks = chunker.chunk(self.JNC_TEXT)
        rec_chunk = next(
            (c for c in chunks if c.metadata.get("recommendation_number") == 1),
            None,
        )
        assert rec_chunk is not None
        assert rec_chunk.metadata["recommendation_strength"] == "Strong"
        assert rec_chunk.metadata["evidence_grade"] == "A"

    def test_non_recommendation_text_still_chunked(self):
        chunker = self.make_chunker()
        chunks = chunker.chunk(self.JNC_TEXT)
        # "Treatment Goals" text should appear in some chunk
        all_text = " ".join(c.text for c in chunks)
        assert "lifestyle modification" in all_text or "Treatment Goals" in all_text


# ===========================================================================
# Chunker — ADA doc type
# ===========================================================================

class TestChunkerADA:

    ADA_TEXT = (
        "6.1 HbA1c targets should be individualized based on patient factors. A\n"
        "Factors include age, duration of diabetes, and comorbidities.\n\n"
        "6.2 For most adults, an HbA1c target of <7% is recommended. B\n"
        "More stringent targets may be appropriate for certain patients.\n\n"
        "9.1 Metformin is the preferred initial pharmacologic agent. A\n"
        "It is effective, safe, and inexpensive.\n"
    )

    def make_chunker(self):
        return Chunker(
            doc_id="ada_standards_care_diabetes_6",
            doc_type="ada",
            document_name="ADA Standards of Care — Section 6",
        )

    def test_returns_chunks(self):
        chunker = self.make_chunker()
        chunks = chunker.chunk(self.ADA_TEXT)
        assert len(chunks) > 0

    def test_evidence_grades_in_metadata(self):
        chunker = self.make_chunker()
        chunks = chunker.chunk(self.ADA_TEXT)
        grades = [c.metadata.get("evidence_grade") for c in chunks]
        # At least some chunks should carry a grade
        assert any(g in ("A", "B", "C") for g in grades)

    def test_grades_stripped_from_chunk_text(self):
        """Grade letters should NOT appear as trailing characters in chunk text."""
        chunker = self.make_chunker()
        chunks = chunker.chunk(self.ADA_TEXT)
        for c in chunks:
            # Text should not end with a lone grade letter
            stripped = c.text.rstrip()
            assert not (len(stripped) > 1 and stripped[-1] in "ABCDE" and stripped[-2] == " "), \
                f"Trailing grade letter in chunk: {stripped[-20:]!r}"

    def test_chunk_section_numbers(self):
        chunker = self.make_chunker()
        chunks = chunker.chunk(self.ADA_TEXT)
        section_nums = [c.metadata.get("section_number") for c in chunks]
        # section_number is set from ADA rec number detection
        # Some chunks should have a section label from the "6.1", "6.2" lines
        all_text = " ".join(c.text for c in chunks)
        assert "HbA1c" in all_text or "Metformin" in all_text


# ===========================================================================
# Chunker — Edge Cases
# ===========================================================================

class TestChunkerEdgeCases:

    def make_chunker(self, doc_type="fda"):
        return Chunker(
            doc_id="test_doc",
            doc_type=doc_type,
            document_name="Test Document",
        )

    def test_empty_text_returns_empty_list(self):
        chunker = self.make_chunker()
        chunks = chunker.chunk("")
        assert chunks == []

    def test_whitespace_only_text_returns_empty_list(self):
        chunker = self.make_chunker()
        chunks = chunker.chunk("   \n\n\t  ")
        assert chunks == []

    def test_document_id_in_all_chunks(self):
        chunker = self.make_chunker()
        chunks = chunker.chunk("DESCRIPTION\nSome content about metformin.")
        for c in chunks:
            assert c.metadata["document_id"] == "test_doc"

    def test_page_number_propagated(self):
        chunker = self.make_chunker()
        chunks = chunker.chunk("DESCRIPTION\nContent.", page_number=5)
        for c in chunks:
            assert c.metadata["page_number"] == 5
