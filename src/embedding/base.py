"""
src/embedding/base.py
----------------------
Shared types and utilities for the embedding layer.

Contains:
  - Embedder     : Protocol (structural typing) — swap providers without ABC inheritance
  - IndexableChunk: Chunk augmented with a deterministic UUID5 id
  - ChunkIDGenerator: UUID5-based stable ID generation for idempotent upserts
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

# ---------------------------------------------------------------------------
# UUID5 namespace — fixed, never change after first ingestion.
# Using the URL namespace UUID so the seed is universally recognisable.
# ---------------------------------------------------------------------------
_UUID5_NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")


def make_chunk_id(doc_id: str, chunk_index: int) -> str:
    """
    Generate a deterministic UUID5 for a chunk.

    Why UUID5:
      - Same (doc_id, chunk_index) always → same UUID → Qdrant upsert overwrites cleanly.
      - UUID4 (random) creates duplicate points on every re-ingestion run.
      - UUID5 is spec-defined, reproducible across machines and Python versions.

    Args:
        doc_id:       Document identifier, e.g. "metformin_fda_label".
        chunk_index:  Position of the chunk within the document (0-based).

    Returns:
        UUID5 string, e.g. "550e8400-e29b-41d4-a716-446655440000".
    """
    key = f"{doc_id}::{chunk_index}"
    return str(uuid.uuid5(_UUID5_NAMESPACE, key))


# ---------------------------------------------------------------------------
# IndexableChunk — Chunk + deterministic ID
# ---------------------------------------------------------------------------

@dataclass
class IndexableChunk:
    """
    A preprocessed chunk ready for embedding and Qdrant upsert.

    Wraps the raw (text, metadata) dict output of PreprocessingPipeline.run()
    and attaches a pre-computed chunk_id so the embedder and indexer don't
    need to know about ID generation.
    """
    chunk_id: str          # UUID5 — stable across re-ingestion runs
    text: str              # cleaned + normalised chunk text (what gets embedded)
    metadata: dict[str, Any]  # full metadata dict from chunker

    @property
    def doc_id(self) -> str:
        return self.metadata.get("document_id", "")

    @property
    def doc_type(self) -> str:
        return self.metadata.get("doc_type", "")

    @property
    def safety_flag(self) -> bool:
        return bool(self.metadata.get("safety_flag", False))


def make_indexable(chunks: list, doc_id: str) -> list[IndexableChunk]:
    """
    Convert raw Chunk objects (from PreprocessingPipeline) into IndexableChunks.

    Args:
        chunks: list of Chunk objects (with .text and .metadata attributes).
        doc_id: document identifier (used as UUID5 namespace seed).

    Returns:
        list[IndexableChunk] with deterministic chunk_ids.
    """
    result: list[IndexableChunk] = []
    for i, chunk in enumerate(chunks):
        text = chunk.text if hasattr(chunk, "text") else chunk.get("text", "")
        meta = chunk.metadata if hasattr(chunk, "metadata") else chunk.get("metadata", {})
        chunk_id = make_chunk_id(doc_id, meta.get("chunk_index", i))
        result.append(IndexableChunk(chunk_id=chunk_id, text=text, metadata=meta))
    return result


# ---------------------------------------------------------------------------
# Embedder Protocol — structural typing for provider swap
# ---------------------------------------------------------------------------

@runtime_checkable
class Embedder(Protocol):
    """
    Structural interface for embedding providers.

    Why Protocol (not ABC):
      - Swapping OpenAI → BGE requires zero changes in indexer.py or run_ingestion.py.
      - MockEmbedder in tests doesn't need to inherit from anything.
      - runtime_checkable allows isinstance(obj, Embedder) for runtime validation.
    """

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Embed a list of texts.

        Args:
            texts: list of strings to embed (length ≤ config.batch_size).

        Returns:
            list of float vectors, one per input text.
            Vectors are L2-normalised if config.normalize=True.
        """
        ...

    @property
    def dimensions(self) -> int:
        """Dimensionality of the output vectors."""
        ...

    @property
    def model_name(self) -> str:
        """Human-readable model identifier (logged to MLflow)."""
        ...
