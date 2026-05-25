"""
src/retrieval/reranker.py
--------------------------
Cross-encoder reranker using sentence-transformers.

Design notes:
- Receives the RRF fusion pool (top-40) and re-scores every (query, chunk) pair
  jointly — unlike bi-encoders, cross-encoders see both texts together and can
  model token-level interaction.
- Model: cross-encoder/ms-marco-MiniLM-L-6-v2 (22M params, CPU-friendly).
- Runs synchronously because sentence-transformers predict() is not async.
  The pipeline.py wraps this in asyncio.run_in_executor to stay non-blocking.
- Scores are sigmoid-normalised to [0, 1] when normalize_scores=True.
"""

from __future__ import annotations

import asyncio
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any

# huggingface_hub's httpx client has a lifecycle bug on Python 3.14+ where the
# client is closed before the metadata HEAD request completes. Since the model is
# pre-downloaded (Dockerfile line 16 / first local run), skip the network check.
os.environ.setdefault("HF_HUB_OFFLINE", "1")

from configs.retrieval import RETRIEVAL_CONFIG, RerankerConfig
from sentence_transformers import CrossEncoder

from retrieval.rrf_ranker import FusedResult

logger = logging.getLogger(__name__)

# Module-level thread pool — one worker is enough since the cross-encoder is
# single-threaded internally. Multiple workers would compete for the same CPU cores.
_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="reranker")


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


@dataclass
class RankedResult:
    """A reranked chunk, ready for the LLM context window."""

    chunk_id: str
    reranker_score: float  # cross-encoder score (sigmoid-normalised if enabled)
    text: str
    payload: dict[str, Any] = field(default_factory=dict)

    # Carry through fusion metadata for RAGAS eval / debugging
    rrf_score: float = 0.0
    dense_rank: int | None = None
    bm25_rank: int | None = None

    @property
    def document_id(self) -> str:
        return self.payload.get("document_id", "")

    @property
    def section_name(self) -> str:
        return self.payload.get("section_name", "")

    @property
    def safety_flag(self) -> bool:
        return bool(self.payload.get("safety_flag", False))


# ---------------------------------------------------------------------------
# Reranker
# ---------------------------------------------------------------------------


class CrossEncoderReranker:
    """
    Wraps a sentence-transformers CrossEncoder for reranking.

    Usage:
        reranker = CrossEncoderReranker()
        ranked = await reranker.rerank(query, fused_pool)
    """

    def __init__(self, config: RerankerConfig | None = None) -> None:
        self._cfg = config or RETRIEVAL_CONFIG.reranker
        logger.info("Loading cross-encoder model: %s", self._cfg.model_name)
        self._model = CrossEncoder(
            self._cfg.model_name,
            device=self._cfg.device,
            max_length=512,  # truncate (query + chunk) to 512 tokens
        )
        logger.info("Cross-encoder loaded on device=%s", self._cfg.device)

    # ------------------------------------------------------------------
    # Main entry point (async-safe)
    # ------------------------------------------------------------------

    async def rerank(
        self,
        query: str,
        candidates: list[FusedResult],
        top_n: int | None = None,
    ) -> list[RankedResult]:
        """
        Rerank the RRF fusion pool using the cross-encoder.

        Args:
            query:      User query string.
            candidates: RRF fusion pool (typically top-40 FusedResult objects).
            top_n:      Override config top_n for this call.

        Returns:
            List of RankedResult sorted by reranker_score descending, top-n only.
        """
        if not candidates:
            return []

        n = top_n or self._cfg.top_n

        # Build (query, chunk_text) pairs for the cross-encoder
        pairs = [(query, c.text) for c in candidates]

        # Run synchronous predict() in a thread so we don't block the event loop
        loop = asyncio.get_event_loop()
        scores: list[float] = await loop.run_in_executor(
            _EXECUTOR,
            self._predict_sync,
            pairs,
        )

        # Pair scores with candidates, sort, take top-n
        scored = sorted(
            zip(scores, candidates),
            key=lambda x: x[0],
            reverse=True,
        )

        results = [
            RankedResult(
                chunk_id=c.chunk_id,
                reranker_score=score,
                text=c.text,
                payload=c.payload,
                rrf_score=c.rrf_score,
                dense_rank=c.dense_rank,
                bm25_rank=c.bm25_rank,
            )
            for score, c in scored[:n]
        ]

        logger.debug(
            "Reranker: %d candidates → top %d. Top score=%.4f",
            len(candidates),
            len(results),
            results[0].reranker_score if results else 0.0,
        )
        return results

    # ------------------------------------------------------------------
    # Sync predict (runs in thread executor)
    # ------------------------------------------------------------------

    def _predict_sync(self, pairs: list[tuple[str, str]]) -> list[float]:
        """
        Run the cross-encoder predict() call synchronously.
        Uses batching to fit within RAM budget on free-tier server.
        """
        all_scores: list[float] = []
        batch_size = self._cfg.batch_size

        for i in range(0, len(pairs), batch_size):
            batch = pairs[i : i + batch_size]
            raw = self._model.predict(
                batch,
                apply_softmax=False,  # we handle normalisation ourselves
                show_progress_bar=False,
            )
            if self._cfg.normalize_scores:
                import math

                batch_scores = [1.0 / (1.0 + math.exp(-s)) for s in raw]
            else:
                batch_scores = [float(s) for s in raw]
            all_scores.extend(batch_scores)

        return all_scores
