"""
table_converter.py
------------------
Stage 14 — Convert pdfplumber table rows → natural-language sentences.
Stage 15 — Inject inline placeholder into main text flow.

Decision (from plan):
  - Each table becomes its OWN chunk with metadata {is_table: True}.
  - The original table position in the text flow is replaced with:
      "[See Table N: <section_heading>]"
  - Table chunks are appended to the chunk list after text chunks.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from ingestion.extractor import ExtractedTable

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data container for a converted table chunk
# ---------------------------------------------------------------------------


@dataclass
class TableChunk:
    text: str
    metadata: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Table → Natural Language converter
# ---------------------------------------------------------------------------


def _clean_cell(cell: str | None) -> str:
    """Strip whitespace and newlines from a cell value."""
    if cell is None:
        return ""
    return " ".join(str(cell).split())


def table_rows_to_nl(
    rows: list[list[str | None]],
    table_number: int,
    section_name: str,
    page_number: int,
    document_id: str,
    document_name: str,
) -> TableChunk:
    """
    Convert pdfplumber table rows into a natural-language paragraph chunk.

    Format
    ------
    "Table N — <section>:
    For <col1> = <val>, <col2> is <val>, <col3> is <val>.
    For <col1> = <val2>, ..."

    Parameters
    ----------
    rows : list[list]
        First row is treated as the header row.
    """
    if len(rows) < 2:
        logger.warning(
            "Table %d on page %d has fewer than 2 rows — skipping", table_number, page_number
        )
        return TableChunk(text="", metadata={})

    headers = [_clean_cell(h) for h in rows[0]]
    # Filter out empty headers (some tables have merged/blank header cells)
    valid_col_idxs = [i for i, h in enumerate(headers) if h]

    if not valid_col_idxs:
        logger.warning(
            "Table %d on page %d has no valid headers — skipping", table_number, page_number
        )
        return TableChunk(text="", metadata={})

    sentences: list[str] = []
    for row in rows[1:]:
        parts: list[str] = []
        for i, col_idx in enumerate(valid_col_idxs):
            cell = _clean_cell(row[col_idx]) if col_idx < len(row) else ""
            if not cell:
                continue
            header = headers[col_idx]
            if i == 0:
                parts.append(f"For {header} = {cell}")
            else:
                parts.append(f"{header} is {cell}")
        if parts:
            sentences.append(", ".join(parts) + ".")

    if not sentences:
        return TableChunk(text="", metadata={})

    label = f"Table {table_number}"
    if section_name:
        label += f" — {section_name}"

    full_text = f"{label}:\n" + "\n".join(sentences)

    metadata = {
        "document_id": document_id,
        "document_name": document_name,
        "page_number": page_number,
        "section_name": section_name,
        "is_table": True,
        "table_number": table_number,
        "safety_flag": False,
        "evidence_grade": None,
        "recommendation_number": None,
        "recommendation_strength": None,
        "skipped_content": [],
    }

    return TableChunk(text=full_text, metadata=metadata)


# ---------------------------------------------------------------------------
# Convert all tables for a document
# ---------------------------------------------------------------------------


def convert_all_tables(
    tables: list[ExtractedTable],
    document_id: str,
    document_name: str,
    current_section: str = "",
) -> list[TableChunk]:
    """
    Convert all ExtractedTable objects into TableChunk objects.

    Parameters
    ----------
    tables : list[ExtractedTable]
        Raw table data from the extractor.
    current_section : str
        A fallback section label when per-page section detection is not available.
        The chunker will later associate each table with the nearest detected heading.
    """
    chunks: list[TableChunk] = []
    for i, tbl in enumerate(tables, start=1):
        chunk = table_rows_to_nl(
            rows=tbl.rows,
            table_number=i,
            section_name=current_section,
            page_number=tbl.page_number,
            document_id=document_id,
            document_name=document_name,
        )
        if chunk.text:
            chunks.append(chunk)
            logger.debug(
                "Converted table %d (page %d): %d chars",
                i,
                tbl.page_number,
                len(chunk.text),
            )

    logger.info("Converted %d/%d tables for doc '%s'", len(chunks), len(tables), document_id)
    return chunks


# ---------------------------------------------------------------------------
# Placeholder injection into text flow
# ---------------------------------------------------------------------------


def build_table_placeholder(table_number: int, section_name: str) -> str:
    label = f"Table {table_number}"
    if section_name:
        label += f": {section_name}"
    return f"[See {label}]"
