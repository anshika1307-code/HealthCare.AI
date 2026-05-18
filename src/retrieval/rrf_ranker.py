"""
src/retrieval/rrf_ranker.py
----------------------------
Reciprocal Rank Fusion (RRF) — fuses dense and BM25 ranked lists into a
single unified ranking without requiring score normalisation.

Reference: Cormack, G., Clarke, C., & Buettcher, S. (2009). Reciprocal rank
fusion outperforms Condorcet and individual rank learning methods. SIGIR.

Formula:
    RRF_score(d) = Σ_r  weight_r / (k + rank_r(d))

Where:
    d        = a document/chunk
    r        = a retriever (dense, bm25)
    rank_r   = 1-based rank of d in retriever r's list (∞ if not in list)
    k        = smoothing constant (default: 60)
    weight_r = per-retriever weight (default: 1.0 for both)

Key property: RRF only uses rank position, not raw scores. This means you
never need to worry about score scale differences between dense (cosine
similarity) and BM25 (TF-IDF variant) — they are incomparable raw, but
their ranks are directly fusable.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from configs.retrieval import RETRIEVAL_CONFIG, RRFConfig

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Unified result type (output of RRF, input to reranker)
# ---------------------------------------------------------------------------


@dataclass
class FusedResult:
    """A chunk after RRF fusion, ready for reranking."""

    chunk_id: str
    rrf_score: float
    text: str = ""
    payload: dict[str, Any] = field(default_factory=dict)

    # Source attribution — useful for debugging and RAGAS eval
    dense_rank: int | None = None  # 1-based rank in dense list (None if absent)
    bm25_rank: int | None = None  # 1-based rank in BM25 list (None if absent)
    dense_score: float | None = None
    bm25_score: float | None = None


# ---------------------------------------------------------------------------
# RRF Ranker
# ---------------------------------------------------------------------------


class RRFRanker:
    """
    Fuses two ranked retrieval lists using Reciprocal Rank Fusion.

    Usage:
        ranker = RRFRanker(config)
        fused = ranker.fuse(dense_results, bm25_results)
    """

    def __init__(self, config: RRFConfig | None = None) -> None:
        self._cfg = config or RETRIEVAL_CONFIG.rrf

    def fuse(
        self,
        dense_results: list,  # list[DenseResult]
        bm25_results: list,  # list[BM25Result]
    ) -> list[FusedResult]:
        """
        Fuse dense and BM25 ranked lists via RRF.

        Args:
            dense_results: Sorted dense hits (rank 1 = highest score).
            bm25_results:  Sorted BM25 hits (rank 1 = highest score).

        Returns:
            Top-fusion_pool_size FusedResult objects, sorted by RRF score desc.
        """
        k = self._cfg.k
        dw = self._cfg.dense_weight
        bw = self._cfg.bm25_weight
        pool_size = self._cfg.fusion_pool_size

        # Build per-retriever rank maps: chunk_id → (1-based rank, score, text, payload)
        dense_map: dict[str, tuple[int, float, str, dict]] = {}
        for rank, hit in enumerate(dense_results, start=1):
            dense_map[hit.chunk_id] = (rank, hit.score, hit.text, hit.payload)

        bm25_map: dict[str, tuple[int, float, str, dict]] = {}
        for rank, hit in enumerate(bm25_results, start=1):
            bm25_map[hit.chunk_id] = (rank, hit.score, hit.text, hit.payload)

        # Union of all chunk IDs seen by either retriever
        all_ids = set(dense_map) | set(bm25_map)

        fused: list[FusedResult] = []
        for chunk_id in all_ids:
            rrf_score = 0.0
            d_rank = d_score = None
            b_rank = b_score = None
            text = ""
            payload: dict[str, Any] = {}

            if chunk_id in dense_map:
                d_rank, d_score, text, payload = dense_map[chunk_id]
                rrf_score += dw / (k + d_rank)

            if chunk_id in bm25_map:
                b_rank, b_score, bm25_text, bm25_payload = bm25_map[chunk_id]
                rrf_score += bw / (k + b_rank)
                # Prefer BM25 text/payload if dense didn't provide it (BM25 stores full text)
                if not text:
                    text = bm25_text
                if not payload:
                    payload = bm25_payload

            fused.append(
                FusedResult(
                    chunk_id=chunk_id,
                    rrf_score=rrf_score,
                    text=text,
                    payload=payload,
                    dense_rank=d_rank,
                    bm25_rank=b_rank,
                    dense_score=d_score,
                    bm25_score=b_score,
                )
            )

        # Sort by RRF score descending, return top pool_size
        fused.sort(key=lambda x: x.rrf_score, reverse=True)
        top = fused[:pool_size]

        logger.debug(
            "RRF fusion: %d dense + %d bm25 → %d unique → top %d",
            len(dense_results),
            len(bm25_results),
            len(fused),
            len(top),
        )
        return top
