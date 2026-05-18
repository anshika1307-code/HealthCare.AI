"""
src/embedding/indexer.py
------------------------
QdrantIndexer — idempotent batch upsert of embeddings into Qdrant.

Every point is upserted with a UUID5 chunk_id, so re-running ingestion
overwrites existing vectors cleanly instead of creating duplicates.

Text is stored in payload["text"] so the reranker can fetch full chunk
text via get_by_ids() without a second embed call.
"""

from __future__ import annotations

import logging
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

from .base import IndexableChunk

logger = logging.getLogger(__name__)

_DEFAULT_BATCH = 100


class QdrantIndexer:
    """
    Upserts embedded chunks into a Qdrant collection.

    Usage:
        indexer = QdrantIndexer(client, "healthcare_chunks")
        success_count, failed_ids = indexer.upsert(chunks, vectors)
    """

    def __init__(self, client: QdrantClient, collection_name: str) -> None:
        self._client = client
        self._collection = collection_name

    def upsert(
        self,
        chunks: list[IndexableChunk],
        embeddings: list[list[float]],
        batch_size: int = _DEFAULT_BATCH,
    ) -> tuple[int, list[str]]:
        """
        Upsert IndexableChunks with their embedding vectors into Qdrant.

        Args:
            chunks:     IndexableChunk objects (one per embedding).
            embeddings: Parallel list of float vectors.
            batch_size: Points per upsert call.

        Returns:
            (success_count, failed_ids) — count of successfully upserted points
            and list of chunk_ids whose batch failed.
        """
        if len(chunks) != len(embeddings):
            raise ValueError(
                f"chunks ({len(chunks)}) and embeddings ({len(embeddings)}) must be same length"
            )

        success_count = 0
        failed_ids: list[str] = []

        for i in range(0, len(chunks), batch_size):
            batch_chunks = chunks[i : i + batch_size]
            batch_vectors = embeddings[i : i + batch_size]

            points = [
                PointStruct(
                    id=chunk.chunk_id,
                    vector=vector,
                    payload=self._build_payload(chunk),
                )
                for chunk, vector in zip(batch_chunks, batch_vectors)
            ]

            try:
                self._client.upsert(
                    collection_name=self._collection,
                    points=points,
                    wait=True,
                )
                success_count += len(points)
                logger.debug(
                    "Upserted batch of %d points (total: %d)",
                    len(points),
                    success_count,
                )
            except Exception as exc:
                logger.error("Upsert failed for batch starting at index %d: %s", i, exc)
                failed_ids.extend(c.chunk_id for c in batch_chunks)

        logger.info(
            "Upsert complete: %d succeeded, %d failed",
            success_count,
            len(failed_ids),
        )
        return success_count, failed_ids

    @staticmethod
    def _build_payload(chunk: IndexableChunk) -> dict[str, Any]:
        """Map IndexableChunk fields to the Qdrant point payload schema."""
        meta = chunk.metadata
        return {
            "text": chunk.text,
            "document_id": meta.get("document_id", ""),
            "document_name": meta.get("document_name", ""),
            "doc_type": meta.get("doc_type", chunk.doc_type),
            "page_number": meta.get("page_number"),
            "section_name": meta.get("section_name"),
            "section_number": meta.get("section_number"),
            "is_table": bool(meta.get("is_table", False)),
            "table_number": meta.get("table_number"),
            "evidence_grade": meta.get("evidence_grade"),
            "recommendation_strength": meta.get("recommendation_strength"),
            "recommendation_number": meta.get("recommendation_number"),
            "safety_flag": bool(meta.get("safety_flag", False)),
            "chunk_index": meta.get("chunk_index", 0),
            "char_count": meta.get("char_count", len(chunk.text)),
        }
