"""
src/retrieval/dense_retriever.py
---------------------------------
Async Qdrant vector search retriever.

Design notes:
- Uses AsyncQdrantClient so it plays well with FastAPI's async event loop.
- All blocking I/O is awaited — never call synchronous Qdrant methods from
  an async context or you will stall the entire server under concurrent load.
- Returns raw ScoredPoint objects so the RRF ranker can extract (id, score, payload)
  without re-fetching from Qdrant.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from configs.retrieval import RETRIEVAL_CONFIG, DenseConfig
from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as qmodels

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


@dataclass
class DenseResult:
    """A single hit returned by the dense retriever."""

    chunk_id: str  # Qdrant point ID (str uuid)
    score: float  # cosine similarity in [−1, 1] (normalised → [0,1])
    payload: dict[str, Any]  # full chunk metadata stored in Qdrant
    text: str = ""  # chunk text — populated from payload["text"]

    def __post_init__(self) -> None:
        if not self.text and "text" in self.payload:
            self.text = self.payload["text"]


# ---------------------------------------------------------------------------
# Retriever
# ---------------------------------------------------------------------------


class DenseRetriever:
    """
    Wraps Qdrant async client for vector similarity search.

    Usage:
        retriever = DenseRetriever(client, config)
        results = await retriever.search(query_vector, filters={"document_id": "jnc8..."})
    """

    def __init__(
        self,
        client: AsyncQdrantClient,
        config: DenseConfig | None = None,
    ) -> None:
        self._client = client
        self._cfg = config or RETRIEVAL_CONFIG.dense

    async def search(
        self,
        query_vector: list[float],
        filters: dict[str, Any] | None = None,
        top_k: int | None = None,
    ) -> list[DenseResult]:
        """
        Run ANN search against Qdrant and return top-k scored results.

        Args:
            query_vector: Embedding of the user query (must match collection dim).
            filters:      Optional payload filter dict, e.g. {"document_id": "ada_sec6"}.
                          Keys must be in DenseConfig.filter_fields.
            top_k:        Override config top_k for this call.

        Returns:
            List of DenseResult, sorted by score descending.
        """
        k = top_k or self._cfg.top_k
        qdrant_filter = self._build_filter(filters) if filters else None

        try:
            response = await self._client.query_points(
                collection_name=self._cfg.collection_name,
                query=query_vector,
                query_filter=qdrant_filter,
                limit=k,
                score_threshold=self._cfg.score_threshold,
                with_payload=True,
            )
            hits = response.points
        except Exception as exc:
            logger.error("Qdrant search failed: %s", exc, exc_info=True)
            raise

        results = [
            DenseResult(
                chunk_id=str(hit.id),
                score=hit.score,
                payload=hit.payload or {},
            )
            for hit in hits
        ]
        logger.debug("Dense search returned %d results (k=%d)", len(results), k)
        return results

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_filter(self, filters: dict[str, Any]) -> qmodels.Filter:
        """
        Convert a plain dict of {field: value} into a Qdrant must-match filter.
        Only fields declared in DenseConfig.filter_fields are allowed (safety guard).
        """
        allowed = set(self._cfg.filter_fields)
        conditions: list[qmodels.FieldCondition] = []

        for key, value in filters.items():
            if key not in allowed:
                logger.warning("Dense filter key %r not in allowed filter_fields — skipping.", key)
                continue

            if isinstance(value, bool):
                conditions.append(
                    qmodels.FieldCondition(
                        key=key,
                        match=qmodels.MatchValue(value=value),
                    )
                )
            elif isinstance(value, str):
                conditions.append(
                    qmodels.FieldCondition(
                        key=key,
                        match=qmodels.MatchValue(value=value),
                    )
                )
            else:
                logger.warning("Unsupported filter value type for key %r: %s", key, type(value))

        if not conditions:
            return None  # type: ignore[return-value]

        return qmodels.Filter(must=conditions)

    async def get_by_ids(self, ids: list[str]) -> list[DenseResult]:
        """
        Batch-fetch full chunk payloads by point IDs.
        Used by the reranker to retrieve chunk text for the RRF fusion pool.
        """
        if not ids:
            return []
        points = await self._client.retrieve(
            collection_name=self._cfg.collection_name,
            ids=ids,
            with_payload=True,
        )
        return [
            DenseResult(
                chunk_id=str(p.id),
                score=0.0,  # no score available on direct fetch
                payload=p.payload or {},
            )
            for p in points
        ]
