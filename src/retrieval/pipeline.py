"""
src/retrieval/pipeline.py
--------------------------
The single async entry-point for the full hybrid retrieval pipeline.

Stage order:
    1. DenseRetriever.search()       → top-20 Qdrant hits
    2. BM25Retriever.search()        → top-20 BM25 hits
    3. RRFRanker.fuse()              → top-40 fused candidates
    4. [Fetch texts for BM25-only hits via DenseRetriever.get_by_ids()]
    5. CrossEncoderReranker.rerank() → top-5 reranked chunks
    6. ConfidenceScorer.score()      → RetrievalResult with warning flag

This module is imported by the LangGraph retrieve_node in orchestration/graph.py.
It is NOT responsible for embedding the query — the caller passes the vector.
"""

from __future__ import annotations

import logging
from typing import Any

from retrieval.bm25_retriever import BM25Retriever
from retrieval.confidence import ConfidenceScorer, RetrievalResult
from retrieval.dense_retriever import DenseRetriever
from retrieval.reranker import CrossEncoderReranker
from retrieval.rrf_ranker import FusedResult, RRFRanker

logger = logging.getLogger(__name__)


class RetrievalPipeline:
    """
    Wires all retrieval stages into a single async callable.

    Instantiate once at server startup (heavy: loads BM25 corpus + cross-encoder).
    Call retrieve() for each user query.

    Usage:
        pipeline = RetrievalPipeline(dense, bm25, reranker)
        result = await pipeline.retrieve(query_text, query_vector, filters)
    """

    def __init__(
        self,
        dense_retriever: DenseRetriever,
        bm25_retriever: BM25Retriever,
        reranker: CrossEncoderReranker,
        rrf_ranker: RRFRanker | None = None,
        confidence_scorer: ConfidenceScorer | None = None,
    ) -> None:
        self._dense = dense_retriever
        self._bm25 = bm25_retriever
        self._reranker = reranker
        self._rrf = rrf_ranker or RRFRanker()
        self._confidence = confidence_scorer or ConfidenceScorer()

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    async def retrieve(
        self,
        query_text: str,
        query_vector: list[float],
        filters: dict[str, Any] | None = None,
    ) -> RetrievalResult:
        """
        Run the full hybrid retrieval pipeline for a single query.

        Args:
            query_text:    Raw user query (for BM25 and reranker).
            query_vector:  Embedded query vector (for dense search).
            filters:       Optional metadata filters (e.g. {"document_id": "jnc8..."}).

        Returns:
            RetrievalResult with top-5 chunks, confidence score, and warning flag.
        """
        logger.info("RetrievalPipeline.retrieve: %r", query_text[:80])

        # ----------------------------------------------------------
        # Stage 1 + 2: Dense and BM25 run concurrently
        # ----------------------------------------------------------
        dense_coro = self._dense.search(query_vector, filters=filters)
        # BM25 is synchronous but fast (in-memory) — run in the event loop directly
        bm25_results = self._bm25.search(
            query_text,
            filter_doc_id=filters.get("document_id") if filters else None,
        )
        dense_results = await dense_coro

        logger.debug(
            "Dense: %d hits | BM25: %d hits",
            len(dense_results),
            len(bm25_results),
        )

        # ----------------------------------------------------------
        # Stage 3: RRF fusion
        # ----------------------------------------------------------
        fused: list[FusedResult] = self._rrf.fuse(dense_results, bm25_results)

        # ----------------------------------------------------------
        # Stage 4: Ensure all fused chunks have text
        # BM25 corpus stores text; dense hits may not (if payload["text"] missing).
        # Batch-fetch missing texts from Qdrant.
        # ----------------------------------------------------------
        missing_ids = [f.chunk_id for f in fused if not f.text]
        if missing_ids:
            fetched = await self._dense.get_by_ids(missing_ids)
            fetched_map = {r.chunk_id: r for r in fetched}
            for item in fused:
                if not item.text and item.chunk_id in fetched_map:
                    item.text = fetched_map[item.chunk_id].text
                    if not item.payload:
                        item.payload = fetched_map[item.chunk_id].payload

        # Drop any items that still have no text (shouldn't happen in production)
        fused = [f for f in fused if f.text]

        # ----------------------------------------------------------
        # Stage 5: Cross-encoder reranking
        # ----------------------------------------------------------
        ranked = await self._reranker.rerank(query_text, fused)

        # ----------------------------------------------------------
        # Stage 6: Confidence scoring
        # ----------------------------------------------------------
        result = self._confidence.score(query_text, ranked, filters_applied=filters)

        logger.info(
            "Pipeline complete: %d chunks, confidence=%.4f, low_conf=%s",
            len(result.chunks),
            result.confidence_score,
            result.low_confidence,
        )
        return result
