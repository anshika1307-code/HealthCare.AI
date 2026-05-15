"""
tests/unit/test_extractor.py
----------------------------
Unit tests for src/ingestion/extractor.py

Strategy: We avoid requiring real PDF files in unit tests (no fixtures in repo).
All PDF-dependent functions (PDFExtractor.extract) are tested via mocking.
Pure-logic helpers (_bucket, _sort_blocks_column_aware, _filter_footer_blocks)
are tested directly without mocks.

Coverage:
  _bucket                       column-bucket mapping
  _sort_blocks_column_aware     multi-column reading order
  _filter_footer_blocks         JNC footer bounding-box filter
  PDFExtractor.__init__         config propagation
  PDFExtractor.extract          mocked PDF — page skips, table extraction
  PageText / ExtractedTable / ExtractionResult  dataclass shape
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from pathlib import Path

from ingestion.extractor import (
    _bucket,
    _sort_blocks_column_aware,
    _filter_footer_blocks,
    PDFExtractor,
    PageText,
    ExtractedTable,
    ExtractionResult,
)


# ===========================================================================
# _bucket — column bucket mapping
# ===========================================================================

class TestBucket:

    def test_single_column_always_zero(self):
        assert _bucket(0.0, 600.0, 1) == 0
        assert _bucket(599.0, 600.0, 1) == 0

    def test_two_column_left(self):
        assert _bucket(0.0, 600.0, 2) == 0
        assert _bucket(299.0, 600.0, 2) == 0

    def test_two_column_right(self):
        assert _bucket(300.0, 600.0, 2) == 1
        assert _bucket(599.0, 600.0, 2) == 1

    def test_three_column_buckets(self):
        assert _bucket(0.0, 600.0, 3) == 0    # left
        assert _bucket(200.0, 600.0, 3) == 1  # centre
        assert _bucket(400.0, 600.0, 3) == 2  # right

    def test_clamps_to_max_column_index(self):
        """x0 at exactly page_width should clamp to last column."""
        assert _bucket(600.0, 600.0, 2) == 1


# ===========================================================================
# _sort_blocks_column_aware
# ===========================================================================

class TestSortBlocksColumnAware:

    def _make_block(self, x0, y0, text, block_type=0):
        return {
            "type": block_type,
            "bbox": [x0, y0, x0 + 100, y0 + 20],
            "lines": [{"spans": [{"text": text}]}],
        }

    def test_two_column_order(self):
        """Left column top→bottom then right column top→bottom."""
        blocks = [
            self._make_block(300, 50, "Right-top"),
            self._make_block(0, 100, "Left-bottom"),
            self._make_block(0, 50, "Left-top"),
            self._make_block(300, 100, "Right-bottom"),
        ]
        result = _sort_blocks_column_aware(blocks, page_width=600, n_cols=2)
        lines = [l.strip() for l in result.split("\n") if l.strip()]
        assert lines.index("Left-top") < lines.index("Left-bottom")
        assert lines.index("Left-bottom") < lines.index("Right-top")
        assert lines.index("Right-top") < lines.index("Right-bottom")

    def test_ignores_non_text_blocks(self):
        """Block type != 0 (e.g. images) must be ignored."""
        blocks = [
            self._make_block(0, 50, "Text block", block_type=0),
            self._make_block(0, 100, "Image block", block_type=1),
        ]
        result = _sort_blocks_column_aware(blocks, page_width=600, n_cols=1)
        assert "Text block" in result
        assert "Image block" not in result

    def test_empty_blocks_returns_empty_string(self):
        result = _sort_blocks_column_aware([], page_width=600, n_cols=2)
        assert result == ""


# ===========================================================================
# _filter_footer_blocks
# ===========================================================================

class TestFilterFooterBlocks:

    def test_removes_bottom_8_percent(self):
        """Blocks with y0 > 0.92 * page_height should be removed."""
        page_height = 800.0
        blocks = [
            {"bbox": [0, 100, 100, 120]},   # top of page — keep
            {"bbox": [0, 740, 100, 760]},   # y0=740, 740/800=0.925 > 0.92 — remove
        ]
        result = _filter_footer_blocks(blocks, page_height)
        assert len(result) == 1
        assert result[0]["bbox"][1] == 100

    def test_keeps_all_above_threshold(self):
        page_height = 800.0
        blocks = [{"bbox": [0, 300, 100, 320]}, {"bbox": [0, 500, 100, 520]}]
        result = _filter_footer_blocks(blocks, page_height)
        assert len(result) == 2

    def test_custom_threshold(self):
        page_height = 1000.0
        blocks = [{"bbox": [0, 850, 100, 870]}]  # y0=850, 850/1000=0.85
        # With threshold=0.90 → 850 < 900 → keep
        result = _filter_footer_blocks(blocks, page_height, threshold=0.90)
        assert len(result) == 1
        # With threshold=0.80 → 850 > 800 → remove
        result = _filter_footer_blocks(blocks, page_height, threshold=0.80)
        assert len(result) == 0


# ===========================================================================
# Dataclass Shape Tests
# ===========================================================================

class TestDataclasses:

    def test_page_text_defaults(self):
        pt = PageText(page_number=1, text="content")
        assert pt.skipped is False
        assert pt.skip_reason == ""

    def test_extraction_result_defaults(self):
        er = ExtractionResult(doc_id="test")
        assert er.page_texts == []
        assert er.tables == []

    def test_extracted_table_fields(self):
        rows = [["Header1", "Header2"], ["val1", "val2"]]
        et = ExtractedTable(page_number=3, table_index=0, rows=rows)
        assert et.page_number == 3
        assert len(et.rows) == 2


# ===========================================================================
# PDFExtractor — config propagation
# ===========================================================================

class TestPDFExtractorInit:

    def test_stores_config(self):
        extractor = PDFExtractor(
            doc_id="metformin_fda_label",
            n_cols=2,
            skip_first_page=True,
            strip_footer_bbox=True,
        )
        assert extractor.doc_id == "metformin_fda_label"
        assert extractor.n_cols == 2
        assert extractor.skip_first_page is True
        assert extractor.strip_footer_bbox is True

    def test_defaults(self):
        extractor = PDFExtractor(doc_id="test_doc")
        assert extractor.n_cols == 1
        assert extractor.skip_first_page is False
        assert extractor.strip_footer_bbox is False


# ===========================================================================
# PDFExtractor.extract — mocked PDF tests
# ===========================================================================

class TestPDFExtractorExtract:
    """
    These tests mock fitz.open and pdfplumber.open to avoid requiring
    real PDF files in the unit test suite.
    """

    def _make_fitz_page(self, text="Sample page text with enough content."):
        """Create a mock fitz page."""
        page = MagicMock()
        page.get_text.return_value = text
        page.rect.width = 600.0
        page.rect.height = 800.0
        page.get_text.return_value = text
        return page

    def _make_fitz_doc(self, pages):
        """Create a mock fitz document context manager."""
        doc = MagicMock()
        doc.__enter__ = MagicMock(return_value=pages)
        doc.__exit__ = MagicMock(return_value=False)
        doc.__iter__ = MagicMock(return_value=iter(pages))
        return doc

    @patch("ingestion.extractor.pdfplumber")
    @patch("ingestion.extractor.fitz")
    def test_extract_returns_extraction_result(self, mock_fitz, mock_plumber, tmp_path):
        # Create a dummy PDF path
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b"fake pdf content")

        # Mock fitz
        page1 = self._make_fitz_page("Full page content here, enough text for extraction.")
        mock_fitz_doc = MagicMock()
        mock_fitz_doc.__enter__.return_value = [page1]
        mock_fitz_doc.__exit__.return_value = False
        mock_fitz.open.return_value = mock_fitz_doc

        # Mock pdfplumber — no tables
        mock_plumber_page = MagicMock()
        mock_plumber_page.extract_tables.return_value = []
        mock_plumber_pdf = MagicMock()
        mock_plumber_pdf.__enter__.return_value = MagicMock(pages=[mock_plumber_page])
        mock_plumber_pdf.__exit__.return_value = False
        mock_plumber.open.return_value = mock_plumber_pdf

        extractor = PDFExtractor(doc_id="test_doc", n_cols=1)
        result = extractor.extract(pdf_path)

        assert isinstance(result, ExtractionResult)
        assert result.doc_id == "test_doc"
        assert len(result.page_texts) == 1
        assert result.tables == []

    @patch("ingestion.extractor.pdfplumber")
    @patch("ingestion.extractor.fitz")
    def test_near_empty_page_marked_skipped(self, mock_fitz, mock_plumber, tmp_path):
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b"fake")

        # Page with <50 chars = near-empty
        page1 = self._make_fitz_page("Fig 1")
        mock_fitz_doc = MagicMock()
        mock_fitz_doc.__enter__.return_value = [page1]
        mock_fitz_doc.__exit__.return_value = False
        mock_fitz.open.return_value = mock_fitz_doc

        mock_plumber_pdf = MagicMock()
        mock_plumber_pdf.__enter__.return_value = MagicMock(pages=[MagicMock()])
        mock_plumber_pdf.__exit__.return_value = False
        mock_plumber.open.return_value = mock_plumber_pdf
        mock_plumber.open.return_value.__enter__.return_value.pages[0].extract_tables.return_value = []

        extractor = PDFExtractor(doc_id="test_doc", n_cols=1)
        result = extractor.extract(pdf_path)

        skipped = [p for p in result.page_texts if p.skipped]
        assert len(skipped) == 1
        assert skipped[0].skip_reason == "near_empty_likely_figure"

    def test_extract_raises_on_missing_file(self):
        extractor = PDFExtractor(doc_id="test_doc")
        with pytest.raises(FileNotFoundError):
            extractor.extract(Path("/nonexistent/path/file.pdf"))
