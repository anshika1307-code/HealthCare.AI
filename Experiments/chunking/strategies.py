"""
strategies.py
-------------
Chunking strategy implementations for the experiment.
Three strategies are tested:

  1. boundary_aware   — our production chunker (section/recommendation-aware)
  2. fixed_size       — naive sliding window (pure token budget, no boundaries)
  3. sentence_window  — sentences grouped to fill the token budget

Each strategy returns list[dict] where each dict has:
  - text : str
  - metadata : dict  (document_id, strategy, token_size, chunk_index, char_count)
"""

from __future__ import annotations

import re
import sys
import logging
from pathlib import Path

# ── resolve src root ──────────────────────────────────────────────────────────
_SRC = Path(__file__).resolve().parents[2] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from ingestion.preprocessor import PreprocessingPipeline
from ingestion.chunker import Chunk

logger = logging.getLogger(__name__)

# ── shared token counter ──────────────────────────────────────────────────────
try:
    import tiktoken
    _ENC = tiktoken.get_encoding("cl100k_base")
    def _tok(text: str) -> int: return len(_ENC.encode(text))
    def _decode_tokens(tokens: list) -> str: return _ENC.decode(tokens)
    def _encode(text: str) -> list: return _ENC.encode(text)
except ImportError:
    def _tok(text: str) -> int: return len(text.split())       # type: ignore
    def _decode_tokens(tokens: list) -> str: return " ".join(str(t) for t in tokens)  # type: ignore
    def _encode(text: str) -> list: return text.split()        # type: ignore

# ── sentence splitter ─────────────────────────────────────────────────────────
_SENT_SPLIT = re.compile(r"(?<=[.?!])\s+")


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENT_SPLIT.split(text) if s.strip()]


# =============================================================================
# Strategy 1 — Boundary-Aware (our existing production chunker)
# =============================================================================

def boundary_aware_chunks(
    doc_id: str, pdf_path: str, token_size: int, overlap: int = 64
) -> list[dict]:
    """Run the full ingestion pipeline with the given max_tokens."""
    pipeline = PreprocessingPipeline(max_tokens=token_size, overlap_tokens=overlap)
    chunks: list[Chunk] = pipeline.run(doc_id, pdf_path)
    return [
        {
            "text": c.text,
            "metadata": {
                **c.metadata,
                "strategy": "boundary_aware",
                "token_size": token_size,
            },
        }
        for c in chunks
        if c.text.strip()
    ]


# =============================================================================
# Strategy 2 — Fixed-Size (naive sliding window, no structural awareness)
# =============================================================================

def fixed_size_chunks(
    doc_id: str, pdf_path: str, token_size: int, overlap: int = 64
) -> list[dict]:
    """
    Pure token-window chunking.
    Runs extraction + cleaning but ignores all document structure.
    Overlap is applied at token level.
    """
    # Reuse the pipeline just for extraction + cleaning (not chunking)
    from ingestion.extractor import PDFExtractor
    from ingestion.cleaner import clean
    from ingestion.normalizer import normalize_and_expand
    from ingestion.config import get_doc_config

    cfg = get_doc_config(doc_id)
    extractor = PDFExtractor(
        doc_id=doc_id,
        n_cols=cfg["n_cols"],
        skip_first_page=cfg["skip_first_page"],
        strip_footer_bbox=cfg["strip_footer_bbox"],
    )
    result = extractor.extract(pdf_path)
    full_text = "\n\n".join(
        pt.text for pt in result.page_texts if pt.text.strip()
    )
    cleaned, abbrev_map = clean(full_text, cfg["doc_type"])
    normalized, _ = normalize_and_expand(cleaned, abbrev_map, cfg["doc_type"])

    # Pure token sliding window
    tokens = _encode(normalized)
    chunks: list[dict] = []
    start = 0
    idx = 0
    while start < len(tokens):
        end = start + token_size
        window = tokens[start:end]
        text = _decode_tokens(window).strip()
        if text:
            chunks.append({
                "text": text,
                "metadata": {
                    "document_id": doc_id,
                    "strategy": "fixed_size",
                    "token_size": token_size,
                    "chunk_index": idx,
                    "char_count": len(text),
                    "safety_flag": False,
                    "is_table": False,
                },
            })
            idx += 1
        start += token_size - overlap  # sliding with overlap

    logger.info("fixed_size: %d chunks for %s (size=%d)", len(chunks), doc_id, token_size)
    return chunks


# =============================================================================
# Strategy 3 — Sentence-Window (sentences grouped to fill token budget)
# =============================================================================

def sentence_window_chunks(
    doc_id: str, pdf_path: str, token_size: int, overlap_sents: int = 1
) -> list[dict]:
    """
    Group sentences greedily until the token budget is reached.
    overlap_sents: number of sentences from the previous chunk to prepend (context overlap).
    """
    from ingestion.extractor import PDFExtractor
    from ingestion.cleaner import clean
    from ingestion.normalizer import normalize_and_expand
    from ingestion.config import get_doc_config

    cfg = get_doc_config(doc_id)
    extractor = PDFExtractor(
        doc_id=doc_id,
        n_cols=cfg["n_cols"],
        skip_first_page=cfg["skip_first_page"],
        strip_footer_bbox=cfg["strip_footer_bbox"],
    )
    result = extractor.extract(pdf_path)
    full_text = "\n\n".join(
        pt.text for pt in result.page_texts if pt.text.strip()
    )
    cleaned, abbrev_map = clean(full_text, cfg["doc_type"])
    normalized, _ = normalize_and_expand(cleaned, abbrev_map, cfg["doc_type"])

    sentences = _sentences(normalized)
    chunks: list[dict] = []
    i = 0
    idx = 0

    while i < len(sentences):
        # Prepend overlap from previous chunk
        overlap_prefix = sentences[max(0, i - overlap_sents):i] if overlap_sents and chunks else []
        buffer: list[str] = list(overlap_prefix)
        token_count = sum(_tok(s) for s in buffer)

        while i < len(sentences):
            sent = sentences[i]
            sent_tok = _tok(sent)
            if token_count + sent_tok > token_size and buffer:
                break
            buffer.append(sent)
            token_count += sent_tok
            i += 1

        text = " ".join(buffer).strip()
        if text:
            chunks.append({
                "text": text,
                "metadata": {
                    "document_id": doc_id,
                    "strategy": "sentence_window",
                    "token_size": token_size,
                    "chunk_index": idx,
                    "char_count": len(text),
                    "safety_flag": False,
                    "is_table": False,
                },
            })
            idx += 1

    logger.info("sentence_window: %d chunks for %s (size=%d)", len(chunks), doc_id, token_size)
    return chunks


# =============================================================================
# Registry — map strategy name → callable
# =============================================================================

STRATEGIES = {
    "boundary_aware": boundary_aware_chunks,
    "fixed_size": fixed_size_chunks,
    "sentence_window": sentence_window_chunks,
}
