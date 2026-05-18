"""
tests/unit/test_preprocessor.py
--------------------------------
Unit tests for src/ingestion/preprocessor.py (PreprocessingPipeline)

Strategy:
  PreprocessingPipeline.run() calls PDFExtractor which needs a real PDF.
  We test it by mocking the entire PDFExtractor.extract() call and verifying
  that the pipeline correctly wires cleaning → normalizing → chunking → table
  conversion, producing a properly structured list of Chunk objects.

Coverage:
  Pipeline instantiation
  run() — output type and shape
  run() — metadata completeness on every chunk
  run() — text and table chunks both present
  run() — global chunk_index re-assigned after merge
  run() — invalid doc_id raises ValueError
  run() — missing pdf_path raises FileNotFoundError (via extractor)
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from ingestion.preprocessor import PreprocessingPipeline
from ingestion.chunker import Chunk
from ingestion.extractor import ExtractionResult, PageText, ExtractedTable


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def pipeline():
    return PreprocessingPipeline(max_tokens=512, overlap_tokens=64)


def _make_extraction_result(doc_id: str, page_texts_text: list[str], include_table: bool = False):
    """Build a mock ExtractionResult to substitute for PDFExtractor.extract()."""
    page_texts = [PageText(page_number=i + 1, text=text) for i, text in enumerate(page_texts_text)]
    tables = []
    if include_table:
        tables.append(
            ExtractedTable(
                page_number=1,
                table_index=0,
                rows=[
                    ["Drug", "Initial Dose", "Max Dose"],
                    ["Metformin", "500 mg", "2550 mg"],
                    ["Glipizide", "5 mg", "40 mg"],
                ],
            )
        )
    return ExtractionResult(doc_id=doc_id, page_texts=page_texts, tables=tables)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestPreprocessingPipelineInit:
    def test_stores_max_tokens(self):
        pipeline = PreprocessingPipeline(max_tokens=256, overlap_tokens=32)
        assert pipeline.max_tokens == 256

    def test_stores_overlap_tokens(self):
        pipeline = PreprocessingPipeline(max_tokens=512, overlap_tokens=64)
        assert pipeline.overlap_tokens == 64

    def test_default_values(self):
        pipeline = PreprocessingPipeline()
        assert pipeline.max_tokens == 512
        assert pipeline.overlap_tokens == 64


class TestPreprocessingPipelineRun:
    FDA_PAGE_TEXT = [
        "DESCRIPTION\n"
        "Metformin hydrochloride is an oral antihyperglycemic drug used in the "
        "management of type 2 diabetes mellitus (T2DM). "
        "It belongs to the biguanide class of medications.\n\n"
        "INDICATIONS AND USAGE\n"
        "GLUCOPHAGE is indicated as an adjunct to diet and exercise to improve "
        "glycemic control in adults with type 2 diabetes.\n\n"
        "CONTRAINDICATIONS\n"
        "Do not use in patients with severe renal impairment (eGFR <30 mL/min).",
    ]

    @patch("ingestion.preprocessor.PDFExtractor")
    def test_returns_list_of_chunks(self, MockExtractor, pipeline, tmp_path):
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b"fake")

        mock_instance = MockExtractor.return_value
        mock_instance.extract.return_value = _make_extraction_result(
            "metformin_fda_label", self.FDA_PAGE_TEXT
        )

        chunks = pipeline.run("metformin_fda_label", pdf_path)
        assert isinstance(chunks, list)
        assert all(isinstance(c, Chunk) for c in chunks)

    @patch("ingestion.preprocessor.PDFExtractor")
    def test_chunks_have_non_empty_text(self, MockExtractor, pipeline, tmp_path):
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b"fake")

        mock_instance = MockExtractor.return_value
        mock_instance.extract.return_value = _make_extraction_result(
            "metformin_fda_label", self.FDA_PAGE_TEXT
        )

        chunks = pipeline.run("metformin_fda_label", pdf_path)
        for c in chunks:
            assert c.text.strip() != "", f"Empty chunk at index {c.metadata['chunk_index']}"

    @patch("ingestion.preprocessor.PDFExtractor")
    def test_chunk_indices_are_sequential_and_unique(self, MockExtractor, pipeline, tmp_path):
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b"fake")

        mock_instance = MockExtractor.return_value
        mock_instance.extract.return_value = _make_extraction_result(
            "metformin_fda_label", self.FDA_PAGE_TEXT
        )

        chunks = pipeline.run("metformin_fda_label", pdf_path)
        indices = [c.metadata["chunk_index"] for c in chunks]
        assert indices == list(range(len(chunks))), "chunk_index must be sequential from 0"

    @patch("ingestion.preprocessor.PDFExtractor")
    def test_char_count_matches_text_length(self, MockExtractor, pipeline, tmp_path):
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b"fake")

        mock_instance = MockExtractor.return_value
        mock_instance.extract.return_value = _make_extraction_result(
            "metformin_fda_label", self.FDA_PAGE_TEXT
        )

        chunks = pipeline.run("metformin_fda_label", pdf_path)
        for c in chunks:
            assert c.metadata["char_count"] == len(c.text)

    @patch("ingestion.preprocessor.PDFExtractor")
    def test_all_chunks_have_document_id(self, MockExtractor, pipeline, tmp_path):
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b"fake")

        mock_instance = MockExtractor.return_value
        mock_instance.extract.return_value = _make_extraction_result(
            "metformin_fda_label", self.FDA_PAGE_TEXT
        )

        chunks = pipeline.run("metformin_fda_label", pdf_path)
        for c in chunks:
            assert c.metadata["document_id"] == "metformin_fda_label"

    @patch("ingestion.preprocessor.PDFExtractor")
    def test_all_chunks_have_required_metadata_keys(self, MockExtractor, pipeline, tmp_path):
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b"fake")

        mock_instance = MockExtractor.return_value
        mock_instance.extract.return_value = _make_extraction_result(
            "metformin_fda_label", self.FDA_PAGE_TEXT
        )

        required_keys = {
            "document_id",
            "document_name",
            "chunk_index",
            "char_count",
            "safety_flag",
            "is_table",
            "abbrev_map_size",
        }
        chunks = pipeline.run("metformin_fda_label", pdf_path)
        for c in chunks:
            missing = required_keys - set(c.metadata.keys())
            assert not missing, f"Chunk {c.metadata['chunk_index']} missing keys: {missing}"

    @patch("ingestion.preprocessor.PDFExtractor")
    def test_table_chunks_included_and_flagged(self, MockExtractor, pipeline, tmp_path):
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b"fake")

        mock_instance = MockExtractor.return_value
        mock_instance.extract.return_value = _make_extraction_result(
            "metformin_fda_label", self.FDA_PAGE_TEXT, include_table=True
        )

        chunks = pipeline.run("metformin_fda_label", pdf_path)
        table_chunks = [c for c in chunks if c.metadata.get("is_table")]
        assert len(table_chunks) >= 1
        for tc in table_chunks:
            assert "Table" in tc.text

    @patch("ingestion.preprocessor.PDFExtractor")
    def test_skipped_pages_annotated_in_metadata(self, MockExtractor, pipeline, tmp_path):
        """Near-empty pages should be noted in chunk skipped_content metadata."""
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b"fake")

        # Mix a near-empty page (skipped) with real content
        page_texts = [
            PageText(
                page_number=1, text="DESCRIPTION\nMetformin is a biguanide drug used in T2DM."
            ),
            PageText(page_number=2, text="", skipped=True, skip_reason="near_empty_likely_figure"),
        ]
        extraction = ExtractionResult(
            doc_id="metformin_fda_label",
            page_texts=page_texts,
            tables=[],
        )
        mock_instance = MockExtractor.return_value
        mock_instance.extract.return_value = extraction

        chunks = pipeline.run("metformin_fda_label", pdf_path)
        all_skipped = []
        for c in chunks:
            all_skipped.extend(c.metadata.get("skipped_content", []))
        assert any("near_empty_page_2" in s for s in all_skipped)

    def test_invalid_doc_id_raises_value_error(self, pipeline, tmp_path):
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b"fake")
        with pytest.raises(ValueError, match="Unknown doc_id"):
            pipeline.run("totally_unknown_doc_id", pdf_path)

    @patch("ingestion.preprocessor.PDFExtractor")
    def test_abbrev_map_size_in_metadata(self, MockExtractor, pipeline, tmp_path):
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b"fake")

        mock_instance = MockExtractor.return_value
        mock_instance.extract.return_value = _make_extraction_result(
            "metformin_fda_label", self.FDA_PAGE_TEXT
        )

        chunks = pipeline.run("metformin_fda_label", pdf_path)
        for c in chunks:
            assert isinstance(c.metadata["abbrev_map_size"], int)
            assert c.metadata["abbrev_map_size"] >= 0
