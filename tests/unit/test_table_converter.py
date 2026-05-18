"""
tests/unit/test_table_converter.py
------------------------------------
Unit tests for src/ingestion/table_converter.py

Coverage:
  _clean_cell                 cell normalisation
  table_rows_to_nl            row → NL sentence conversion
  convert_all_tables          bulk conversion
  build_table_placeholder     placeholder text format
"""

import pytest
from ingestion.table_converter import (
    _clean_cell,
    table_rows_to_nl,
    convert_all_tables,
    build_table_placeholder,
    TableChunk,
)
from ingestion.extractor import ExtractedTable


# ===========================================================================
# _clean_cell
# ===========================================================================


class TestCleanCell:
    def test_strips_whitespace(self):
        assert _clean_cell("  value  ") == "value"

    def test_normalises_internal_newlines(self):
        assert _clean_cell("line1\nline2") == "line1 line2"

    def test_none_returns_empty_string(self):
        assert _clean_cell(None) == ""

    def test_empty_string_unchanged(self):
        assert _clean_cell("") == ""

    def test_numeric_cell(self):
        assert _clean_cell("  42  ") == "42"


# ===========================================================================
# table_rows_to_nl
# ===========================================================================


class TestTableRowsToNL:
    SAMPLE_ROWS = [
        ["Drug Class", "Initial Dose", "Max Dose"],
        ["Metformin", "500 mg", "2550 mg"],
        ["Glipizide", "5 mg", "40 mg"],
        ["Sitagliptin", "100 mg", "100 mg"],
    ]

    def test_returns_table_chunk(self):
        chunk = table_rows_to_nl(
            self.SAMPLE_ROWS,
            table_number=1,
            section_name="Diabetes Medications",
            page_number=5,
            document_id="metformin_fda_label",
            document_name="Metformin FDA Label",
        )
        assert isinstance(chunk, TableChunk)

    def test_text_not_empty(self):
        chunk = table_rows_to_nl(
            self.SAMPLE_ROWS,
            table_number=1,
            section_name="Diabetes Medications",
            page_number=5,
            document_id="test",
            document_name="Test Doc",
        )
        assert chunk.text.strip() != ""

    def test_table_label_in_text(self):
        chunk = table_rows_to_nl(
            self.SAMPLE_ROWS,
            table_number=3,
            section_name="Drug Dosing",
            page_number=5,
            document_id="test",
            document_name="Test Doc",
        )
        assert "Table 3" in chunk.text
        assert "Drug Dosing" in chunk.text

    def test_nl_format_for_rows(self):
        chunk = table_rows_to_nl(
            self.SAMPLE_ROWS,
            table_number=1,
            section_name="",
            page_number=1,
            document_id="test",
            document_name="Test",
        )
        # Should contain "For Drug Class = Metformin"
        assert "For Drug Class = Metformin" in chunk.text
        # Should contain "Initial Dose is 500 mg"
        assert "Initial Dose is 500 mg" in chunk.text

    def test_metadata_is_table_true(self):
        chunk = table_rows_to_nl(
            self.SAMPLE_ROWS,
            table_number=1,
            section_name="Section",
            page_number=2,
            document_id="test",
            document_name="Test",
        )
        assert chunk.metadata["is_table"] is True

    def test_metadata_document_id(self):
        chunk = table_rows_to_nl(
            self.SAMPLE_ROWS,
            table_number=1,
            section_name="",
            page_number=1,
            document_id="my_doc",
            document_name="My Doc",
        )
        assert chunk.metadata["document_id"] == "my_doc"

    def test_metadata_page_number(self):
        chunk = table_rows_to_nl(
            self.SAMPLE_ROWS,
            table_number=1,
            section_name="",
            page_number=7,
            document_id="test",
            document_name="Test",
        )
        assert chunk.metadata["page_number"] == 7

    def test_single_row_table_returns_empty_chunk(self):
        """Tables with only a header row (< 2 rows) should return an empty TableChunk."""
        chunk = table_rows_to_nl(
            [["Header1", "Header2"]],
            table_number=1,
            section_name="",
            page_number=1,
            document_id="test",
            document_name="Test",
        )
        assert chunk.text == ""

    def test_no_valid_headers_returns_empty_chunk(self):
        """All-blank header row → empty chunk."""
        chunk = table_rows_to_nl(
            [["", ""], ["val1", "val2"]],
            table_number=1,
            section_name="",
            page_number=1,
            document_id="test",
            document_name="Test",
        )
        assert chunk.text == ""

    def test_skips_fully_empty_rows(self):
        """Data rows where all cells are empty should be skipped silently."""
        rows = [
            ["Drug", "Dose"],
            ["", ""],  # fully empty data row
            ["Metformin", "500 mg"],
        ]
        chunk = table_rows_to_nl(
            rows,
            table_number=1,
            section_name="",
            page_number=1,
            document_id="test",
            document_name="Test",
        )
        assert "Metformin" in chunk.text
        # Should not contain a stray "For Drug = ," line
        assert "For Drug = ," not in chunk.text

    def test_section_name_omitted_when_empty(self):
        """When section_name is empty, label should just be 'Table N' without dash."""
        chunk = table_rows_to_nl(
            self.SAMPLE_ROWS,
            table_number=2,
            section_name="",
            page_number=1,
            document_id="test",
            document_name="Test",
        )
        assert "Table 2:" in chunk.text
        assert "—" not in chunk.text.split(":")[0]  # no dash before colon

    def test_safety_flag_default_false(self):
        chunk = table_rows_to_nl(
            self.SAMPLE_ROWS,
            table_number=1,
            section_name="General",
            page_number=1,
            document_id="test",
            document_name="Test",
        )
        assert chunk.metadata["safety_flag"] is False


# ===========================================================================
# convert_all_tables
# ===========================================================================


class TestConvertAllTables:
    def _make_table(self, page_number: int, table_index: int = 0):
        return ExtractedTable(
            page_number=page_number,
            table_index=table_index,
            rows=[
                ["Parameter", "Value"],
                ["HbA1c", "<7%"],
                ["BP", "<140/90 mm Hg"],
            ],
        )

    def test_converts_all_tables(self):
        tables = [self._make_table(1), self._make_table(3)]
        chunks = convert_all_tables(tables, document_id="ada_sec6", document_name="ADA Section 6")
        assert len(chunks) == 2

    def test_returns_list_of_table_chunks(self):
        tables = [self._make_table(2)]
        chunks = convert_all_tables(tables, document_id="test", document_name="Test")
        assert isinstance(chunks, list)
        assert all(isinstance(c, TableChunk) for c in chunks)

    def test_empty_table_list(self):
        chunks = convert_all_tables([], document_id="test", document_name="Test")
        assert chunks == []

    def test_table_numbers_sequential(self):
        tables = [self._make_table(1), self._make_table(2), self._make_table(3)]
        chunks = convert_all_tables(tables, document_id="test", document_name="Test")
        for i, chunk in enumerate(chunks, start=1):
            assert f"Table {i}" in chunk.text

    def test_empty_chunk_not_included(self):
        """Tables that produce no text (e.g. header-only) must be excluded."""
        header_only_table = ExtractedTable(
            page_number=1,
            table_index=0,
            rows=[["Col1", "Col2"]],  # Only header, no data rows
        )
        full_table = self._make_table(2)
        chunks = convert_all_tables(
            [header_only_table, full_table],
            document_id="test",
            document_name="Test",
        )
        # Only the non-empty table should appear
        assert len(chunks) == 1


# ===========================================================================
# build_table_placeholder
# ===========================================================================


class TestBuildTablePlaceholder:
    def test_format_with_section(self):
        result = build_table_placeholder(3, "Drug Dosing Guide")
        assert result == "[See Table 3: Drug Dosing Guide]"

    def test_format_without_section(self):
        result = build_table_placeholder(1, "")
        assert result == "[See Table 1]"

    def test_contains_see(self):
        result = build_table_placeholder(5, "Some Section")
        assert result.startswith("[See Table")
