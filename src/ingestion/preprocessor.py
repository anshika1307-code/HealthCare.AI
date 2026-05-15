"""
preprocessor.py
---------------
Pipeline orchestrator — wires all stages together in the correct order.

Usage
-----
    from ingestion.preprocessor import PreprocessingPipeline

    pipeline = PreprocessingPipeline()
    chunks = pipeline.run("metformin_fda_label", "data/raw/metformin_fda_label.pdf")

    for chunk in chunks:
        print(chunk.text[:120])
        print(chunk.metadata)
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Union

# Ensure `src` is on sys.path when this module is run as a script (CLI mode).
# When imported as `ingestion.preprocessor`, this block has no effect.
_SRC_ROOT = Path(__file__).resolve().parents[2]  # Healthcare_AI/src
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from ingestion.config import get_doc_config
from ingestion.extractor import PDFExtractor
from ingestion.cleaner import clean
from ingestion.normalizer import normalize_and_expand
from ingestion.table_converter import convert_all_tables, TableChunk
from ingestion.chunker import Chunk, Chunker

logger = logging.getLogger(__name__)


class PreprocessingPipeline:
    """
    End-to-end preprocessing pipeline for a single PDF document.

    Stages
    ------
    EXTRACTION   PDFExtractor   — text (column-sorted) + tables
    CLEANING     cleaner.clean  — headers, footers, refs, inline noise, hyphen join, line rejoin
    NORMALIZING  normalizer     — term normalization → abbreviation map build → first-occurrence expand
    STRUCTURE    chunker        — heading/rec detection + ADA grade extraction
    TABLES       table_converter— rows → NL sentences → TableChunk objects
    CHUNKING     Chunker.chunk  — hard/soft boundaries + 512-token fallback split
    SAFETY       chunker        — per-chunk safety_flag scan
    """

    def __init__(self, max_tokens: int = 512, overlap_tokens: int = 64) -> None:
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def run(
        self,
        doc_id: str,
        pdf_path: Union[str, Path],
    ) -> list[Chunk]:
        """
        Process a single PDF and return a flat list of Chunk objects
        (text chunks first, table chunks appended at the end).

        Parameters
        ----------
        doc_id : str
            Must match a key in config.DOC_REGISTRY.
        pdf_path : str | Path
            Absolute or relative path to the PDF file.

        Returns
        -------
        list[Chunk]
            Ordered list of chunks ready for embedding.
        """
        cfg = get_doc_config(doc_id)
        doc_type = cfg["doc_type"]
        document_name = cfg["display_name"]

        logger.info("=== Starting preprocessing: %s (%s) ===", doc_id, doc_type.upper())

        # ----------------------------------------------------------------
        # EXTRACTION
        # ----------------------------------------------------------------
        extractor = PDFExtractor(
            doc_id=doc_id,
            n_cols=cfg["n_cols"],
            skip_first_page=cfg["skip_first_page"],
            strip_footer_bbox=cfg["strip_footer_bbox"],
        )
        extraction = extractor.extract(pdf_path)

        # ----------------------------------------------------------------
        # ASSEMBLE full-document text from page texts
        # ----------------------------------------------------------------
        page_texts: list[str] = []
        skipped_pages: list[int] = []

        for pt in extraction.page_texts:
            if pt.skipped:
                if pt.skip_reason == "near_empty_likely_figure":
                    skipped_pages.append(pt.page_number)
                    logger.info("Page %d skipped: %s", pt.page_number, pt.skip_reason)
                # first_page_skip pages also contribute empty string — just skip
                page_texts.append("")
            else:
                page_texts.append(pt.text)

        full_text = "\n\n".join(t for t in page_texts if t.strip())

        # ----------------------------------------------------------------
        # CLEANING
        # ----------------------------------------------------------------
        logger.info("Running cleaner (doc_type=%s)…", doc_type)
        cleaned_text, jnc_abbrev_map = clean(full_text, doc_type)

        # ----------------------------------------------------------------
        # NORMALIZATION + ABBREVIATION EXPANSION
        # ----------------------------------------------------------------
        logger.info("Running normalizer…")
        normalized_text, abbrev_map = normalize_and_expand(
            text=cleaned_text,
            seed_abbrev_map=jnc_abbrev_map,  # populated for JNC, empty dict otherwise
            doc_type=doc_type,
        )

        # ----------------------------------------------------------------
        # CHUNKING (text chunks)
        # ----------------------------------------------------------------
        logger.info("Running chunker (max_tokens=%d)…", self.max_tokens)
        chunker = Chunker(
            doc_id=doc_id,
            doc_type=doc_type,
            document_name=document_name,
            max_tokens=self.max_tokens,
            overlap_tokens=self.overlap_tokens,
        )

        text_chunks = chunker.chunk(normalized_text, page_number=0)

        # Log skipped pages across all text chunks
        if skipped_pages:
            skip_labels = [f"near_empty_page_{p}" for p in skipped_pages]
            for c in text_chunks:
                c.metadata.setdefault("skipped_content", []).extend(skip_labels)

        # ----------------------------------------------------------------
        # TABLE CONVERSION
        # ----------------------------------------------------------------
        logger.info("Converting %d tables…", len(extraction.tables))
        raw_table_chunks: list[TableChunk] = convert_all_tables(
            tables=extraction.tables,
            document_id=doc_id,
            document_name=document_name,
        )

        # Wrap TableChunks as Chunks for a unified interface
        table_chunks: list[Chunk] = [
            Chunk(text=tc.text, metadata=tc.metadata)
            for tc in raw_table_chunks
            if tc.text
        ]

        # ----------------------------------------------------------------
        # MERGE + FINAL INDEXING
        # ----------------------------------------------------------------
        all_chunks = text_chunks + table_chunks

        # Re-index globally
        for idx, c in enumerate(all_chunks):
            c.metadata["chunk_index"] = idx
            c.metadata["char_count"] = len(c.text)
            # Attach abbreviation map summary to each chunk (useful for debugging / audit)
            c.metadata["abbrev_map_size"] = len(abbrev_map)

        logger.info(
            "=== Done: %d text chunks + %d table chunks = %d total ===",
            len(text_chunks), len(table_chunks), len(all_chunks),
        )
        return all_chunks


# ---------------------------------------------------------------------------
# CLI helper for quick manual testing
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    import json

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    if len(sys.argv) != 3:
        print("Usage: python preprocessor.py <doc_id> <path/to/file.pdf>")
        sys.exit(1)

    doc_id_arg = sys.argv[1]
    pdf_path_arg = sys.argv[2]

    pipeline = PreprocessingPipeline()
    chunks = pipeline.run(doc_id_arg, pdf_path_arg)

    print(f"\nTotal chunks: {len(chunks)}\n")
    for i, chunk in enumerate(chunks[:5]):
        print(f"--- Chunk {i} ---")
        print(f"Text ({len(chunk.text)} chars): {chunk.text[:200]}...")
        print(f"Metadata: {json.dumps({k: v for k, v in chunk.metadata.items() if k != 'abbrev_map_size'}, indent=2)}")
        print()
