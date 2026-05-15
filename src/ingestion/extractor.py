"""
extractor.py
------------
PDF text and table extraction.

- Text  : PyMuPDF (fitz) with column-aware block sorting for multi-column PDFs.
- Tables: pdfplumber, called independently on the same file.

Column config per doc_id is driven by DOC_REGISTRY in config.py.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF
import pdfplumber

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data containers
# ---------------------------------------------------------------------------

@dataclass
class PageText:
    page_number: int          # 1-indexed
    text: str
    skipped: bool = False
    skip_reason: str = ""


@dataclass
class ExtractedTable:
    page_number: int          # 1-indexed
    table_index: int          # order found on page
    rows: list[list[str | None]]


@dataclass
class ExtractionResult:
    doc_id: str
    page_texts: list[PageText] = field(default_factory=list)
    tables: list[ExtractedTable] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Column sorting helpers
# ---------------------------------------------------------------------------

def _bucket(x0: float, page_width: float, n_cols: int) -> int:
    """Map an x-coordinate to a column bucket (0-indexed)."""
    col_width = page_width / n_cols
    return min(int(x0 // col_width), n_cols - 1)


def _sort_blocks_column_aware(
    blocks: list[dict[str, Any]],
    page_width: float,
    n_cols: int,
) -> str:
    """
    Re-order PyMuPDF text blocks to restore reading order in multi-column layouts.

    For n_cols=2 (JNC): left column top-to-bottom, then right column.
    For n_cols=3 (ADA): left → centre → right column.
    """
    # Filter to text blocks only (type == 0)
    text_blocks = [b for b in blocks if b.get("type") == 0]

    # Group by column bucket, preserve y-order within each column
    columns: dict[int, list[tuple[float, str]]] = {i: [] for i in range(n_cols)}
    for block in text_blocks:
        x0 = block["bbox"][0]
        y0 = block["bbox"][1]
        col = _bucket(x0, page_width, n_cols)
        block_text = "".join(
            span["text"]
            for line in block.get("lines", [])
            for span in line.get("spans", [])
        )
        columns[col].append((y0, block_text))

    # Sort each column by y0 and concatenate
    parts: list[str] = []
    for col_idx in range(n_cols):
        for _, text in sorted(columns[col_idx], key=lambda t: t[0]):
            stripped = text.strip()
            if stripped:
                parts.append(stripped)

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Footer/header bbox filter (JNC — strip bottom 8% of page)
# ---------------------------------------------------------------------------

def _filter_footer_blocks(
    blocks: list[dict[str, Any]],
    page_height: float,
    threshold: float = 0.92,
) -> list[dict[str, Any]]:
    """Remove blocks whose top edge is in the bottom `(1-threshold)*100`% of the page."""
    return [b for b in blocks if b["bbox"][1] < page_height * threshold]


# ---------------------------------------------------------------------------
# Main extractor
# ---------------------------------------------------------------------------

class PDFExtractor:
    """
    Extracts text and tables from a PDF.

    Parameters
    ----------
    doc_id : str
        Identifier key matching DOC_REGISTRY (e.g. 'metformin_fda_label').
    n_cols : int
        Number of text columns. 1 = single-col, 2 = JNC, 3 = ADA.
    skip_first_page : bool
        Whether to skip page index 0 (ADA + JNC).
    strip_footer_bbox : bool
        Whether to strip bottom-region blocks by bounding box (JNC).
    """

    def __init__(
        self,
        doc_id: str,
        n_cols: int = 1,
        skip_first_page: bool = False,
        strip_footer_bbox: bool = False,
    ) -> None:
        self.doc_id = doc_id
        self.n_cols = n_cols
        self.skip_first_page = skip_first_page
        self.strip_footer_bbox = strip_footer_bbox

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract(self, pdf_path: str | Path) -> ExtractionResult:
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        logger.info("Extracting '%s' (doc_id=%s, cols=%d)", pdf_path.name, self.doc_id, self.n_cols)

        result = ExtractionResult(doc_id=self.doc_id)
        result.page_texts = self._extract_text(pdf_path)
        result.tables = self._extract_tables(pdf_path)

        logger.info(
            "Extracted %d pages, %d tables from '%s'",
            len(result.page_texts), len(result.tables), pdf_path.name,
        )
        return result

    # ------------------------------------------------------------------
    # Text extraction (PyMuPDF)
    # ------------------------------------------------------------------

    def _extract_text(self, pdf_path: Path) -> list[PageText]:
        page_texts: list[PageText] = []

        with fitz.open(str(pdf_path)) as doc:
            for page_idx, page in enumerate(doc):
                page_num = page_idx + 1  # 1-indexed

                # Skip first page if configured (ADA + JNC)
                if self.skip_first_page and page_idx == 0:
                    logger.debug("Skipping page 1 of '%s' (configured skip)", self.doc_id)
                    page_texts.append(PageText(page_number=page_num, text="", skipped=True, skip_reason="first_page_skip"))
                    continue

                if self.n_cols > 1:
                    # Column-aware extraction using block dict
                    page_dict = page.get_text("dict")
                    blocks = page_dict.get("blocks", [])
                    page_width = page.rect.width
                    page_height = page.rect.height

                    if self.strip_footer_bbox:
                        blocks = _filter_footer_blocks(blocks, page_height)

                    text = _sort_blocks_column_aware(blocks, page_width, self.n_cols)
                else:
                    # Single-column: simple text extraction
                    text = page.get_text("text")

                    # Detect near-empty pages (likely flowcharts/figures)
                    if len(text.strip()) < 50:
                        logger.info(
                            "Page %d of '%s' is near-empty (%d chars) — likely figure/flowchart, skipping",
                            page_num, self.doc_id, len(text.strip()),
                        )
                        page_texts.append(PageText(
                            page_number=page_num, text="", skipped=True,
                            skip_reason="near_empty_likely_figure",
                        ))
                        continue

                page_texts.append(PageText(page_number=page_num, text=text))

        return page_texts

    # ------------------------------------------------------------------
    # Table extraction (pdfplumber)
    # ------------------------------------------------------------------

    def _extract_tables(self, pdf_path: Path) -> list[ExtractedTable]:
        extracted: list[ExtractedTable] = []

        with pdfplumber.open(str(pdf_path)) as pdf:
            for page_idx, page in enumerate(pdf.pages):
                if self.skip_first_page and page_idx == 0:
                    continue

                tables = page.extract_tables()
                if not tables:
                    continue

                for tbl_idx, rows in enumerate(tables):
                    # Normalise cells: None → ""
                    clean_rows = [
                        [cell if cell is not None else "" for cell in row]
                        for row in rows
                        if any(cell for cell in row)  # skip fully-empty rows
                    ]
                    if len(clean_rows) < 2:
                        # Header-only table — skip
                        continue

                    extracted.append(ExtractedTable(
                        page_number=page_idx + 1,
                        table_index=tbl_idx,
                        rows=clean_rows,
                    ))

        return extracted
