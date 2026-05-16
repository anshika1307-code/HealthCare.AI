"""
configs/ingestion.py
--------------------
Configuration for the PDF ingestion and preprocessing pipeline.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ChunkingConfig:
    max_tokens: int = 512
    # Empirically validated via MLflow chunking experiment (see experiments/).
    # 512 tokens ≈ 1 clinical paragraph. RAGAS context_recall peaks at 512 vs
    # 256 (too granular, loses multi-sentence reasoning) and 1024 (too coarse,
    # retrieves irrelevant surrounding content).

    overlap_tokens: int = 64
    # 12.5% overlap (64/512). Preserves cross-boundary context without excessive
    # redundancy. Standard guidance: 10–15%. Higher overlap → more index entries
    # but better coverage of paragraph-spanning clinical facts.

    min_chunk_tokens: int = 30
    # Chunks below 30 tokens (stray section headings, single-line artefacts)
    # add noise to the vector index without retrieval value. Discard them.

    tokenizer_encoding: str = "cl100k_base"
    # Matches OpenAI text-embedding-3-small and gpt-4o-mini tokenisation.
    # Using the same encoding for chunking and embedding guarantees no silent
    # truncation at embedding time (chunk token count = actual embedding input).


@dataclass
class ExtractionConfig:
    near_empty_page_threshold: int = 50
    # Pages with < 50 chars are almost certainly figures, flowcharts, or cover
    # pages. 50 chars ≈ 8 words — below any useful clinical sentence.
    # Logged as skipped_content in chunk metadata for traceability.

    footer_bbox_threshold: float = 0.92
    # JNC JAMA paper footer (page number + copyright + download line) sits in
    # the bottom 8% of each page. 0.92 strips that band without touching content.
    # Verified from manual PyMuPDF bbox inspection (preprocessing_specs_dev.md).


@dataclass
class IngestionConfig:
    chunking: ChunkingConfig = None  # type: ignore[assignment]
    extraction: ExtractionConfig = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.chunking is None:
            self.chunking = ChunkingConfig()
        if self.extraction is None:
            self.extraction = ExtractionConfig()


INGESTION_CONFIG = IngestionConfig()
