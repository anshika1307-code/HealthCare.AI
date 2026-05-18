"""
configs/embedding.py
--------------------
Embedding model configuration.
Keeping this separate from retrieval.py so the embedding model can be
swapped (e.g. text-embedding-3-small → BGE) without touching retrieval logic.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class EmbeddingConfig:
    model_name: str = "text-embedding-3-small"
    # Decision pending A/B RAGAS eval: text-embedding-3-small vs BGE-base-en-v1.5.
    # text-embedding-3-small: 1536-dim, OpenAI API, no local inference overhead.
    # BGE-base: 768-dim, free, local — but requires ~400MB VRAM/RAM.
    # Current default: OpenAI (simpler infra on free-tier prototype).

    provider: str = "openai"
    # "openai" → OpenAIEmbedder (requires OPENAI_API_KEY env var)
    # "bge"    → BGEEmbedder   (local SentenceTransformer, free, ~400MB RAM)
    # Swap here for A/B experiment — no changes needed in indexer or pipeline.

    dimensions: int = 1536
    # text-embedding-3-small native dimensionality.
    # IMPORTANT: changing this requires recreating the Qdrant collection.
    # BGE-base-en-v1.5 uses 768 — update here AND re-run create_qdrant_collection.py.

    batch_size: int = 100
    # OpenAI embedding API: rate limit ≈ 1M tokens/min on free tier.
    # 100 chunks × 512 tokens = 51,200 tokens/call → well within the limit.
    # Reduce to 50 if you encounter HTTP 429 errors.

    normalize: bool = True
    # L2-normalise embeddings before storing in Qdrant.
    # Enables Qdrant to use faster inner-product HNSW (cosine = inner product
    # on normalised vectors). Also required for correct RRF score interpretation.

    request_timeout_seconds: int = 30
    # Max wait for embedding API call. 30s is generous for batch_size=100 on
    # the free-tier OpenAI endpoint. Raise to 60 if timeout errors occur.

    mlflow_experiment_name: str = "embedding_model_ab"
    # MLflow experiment that tracks all embedding A/B runs.
    # Each ingestion run logs params (model, dims, batch_size) + metrics
    # (total_chunks, embedding_time). RAGAS scores are added to the same run
    # post-evaluation, making the comparison table self-contained.


EMBEDDING_CONFIG = EmbeddingConfig()
