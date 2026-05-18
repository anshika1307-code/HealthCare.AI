"""
src/embedding/bge_embedder.py
------------------------------
BGE-base-en-v1.5 local embedding provider via sentence-transformers.

Used for A/B comparison against text-embedding-3-small (per decision.md):
  "will take after testing two-three models on our documents and evaluating"

Why BGE:
  - Free — no API key, no rate limits, no per-token cost.
  - 768-dim vectors (vs 1536 for OpenAI) — smaller index, faster ANN search.
  - Competitive quality on biomedical retrieval benchmarks (BEIR).
  - Trade-off: requires ~400MB RAM for model weights; CPU inference adds ~200ms/batch.

IMPORTANT: Changing from OpenAI (1536-dim) to BGE (768-dim) requires:
  1. Update configs/embedding.py: dimensions=768, model_name="BAAI/bge-base-en-v1.5", provider="bge"
  2. Re-run scripts/create_qdrant_collection.py --force-recreate
  3. Re-run scripts/run_ingestion.py (full re-embed)
"""
from __future__ import annotations

import logging

from configs.embedding import EMBEDDING_CONFIG, EmbeddingConfig

logger = logging.getLogger(__name__)

_BGE_DIMENSIONS = 768
_BGE_MODEL_ID = "BAAI/bge-base-en-v1.5"

# BGE instruction prefix — required for retrieval tasks (from BGE paper).
# Without this, recall drops ~5% on asymmetric retrieval tasks.
_BGE_QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages: "


class BGEEmbedder:
    """
    Local BGE-base-en-v1.5 embedding provider.

    Usage:
        embedder = BGEEmbedder()
        vectors = embedder.embed_batch(["Metformin dosing", "HbA1c target"])

    Note: First call downloads ~400MB model weights (cached by HuggingFace).
    Subsequent runs load from cache instantly.
    """

    def __init__(self, config: EmbeddingConfig | None = None) -> None:
        self._cfg = config or EMBEDDING_CONFIG
        # Lazy import — only pulled in when BGE is actually requested
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as e:
            raise ImportError(
                "sentence-transformers is required for BGEEmbedder. "
                "Install with: pip install sentence-transformers"
            ) from e

        logger.info("Loading BGE model: %s (first run downloads ~400MB)", _BGE_MODEL_ID)
        self._model = SentenceTransformer(_BGE_MODEL_ID)
        logger.info("BGE model loaded. Device: %s", self._model.device)

    # ------------------------------------------------------------------
    # Embedder Protocol implementation
    # ------------------------------------------------------------------

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Embed a list of texts using BGE local inference.

        Args:
            texts: List of strings to embed (no API rate limit applies).

        Returns:
            List of float vectors (768-dim), L2-normalised.
        """
        if not texts:
            return []

        all_vectors: list[list[float]] = []
        batch_size = self._cfg.batch_size

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            # BGE requires the query instruction prefix for passage encoding too
            # (symmetric retrieval — both documents and queries use same instruction)
            prefixed = [f"{_BGE_QUERY_INSTRUCTION}{t}" for t in batch]

            embeddings = self._model.encode(
                prefixed,
                normalize_embeddings=self._cfg.normalize,
                show_progress_bar=False,
                batch_size=min(batch_size, 32),  # BGE optimal GPU batch; CPU: 32 fine
            )
            all_vectors.extend(embeddings.tolist())
            logger.debug("BGE embedded batch of %d texts.", len(batch))

        return all_vectors

    @property
    def dimensions(self) -> int:
        return _BGE_DIMENSIONS  # BGE-base is always 768

    @property
    def model_name(self) -> str:
        return _BGE_MODEL_ID
