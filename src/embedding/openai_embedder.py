"""
src/embedding/openai_embedder.py
---------------------------------
OpenAI embedding provider — wraps text-embedding-3-small (default).

Design notes:
- Batch calls with configurable batch_size (default: 100).
- tenacity exponential-backoff retry on RateLimitError / APITimeoutError.
- L2-normalisation applied if config.normalize=True (required for Qdrant cosine HNSW).
- AuthenticationError is NOT retried — wrong API key won't fix itself.
- Reads OPENAI_API_KEY from environment (never hardcode keys).
"""
from __future__ import annotations

import logging
import math
import os

import openai
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)

from configs.embedding import EmbeddingConfig, EMBEDDING_CONFIG

logger = logging.getLogger(__name__)

# Retry on transient API errors only.
# AuthenticationError, InvalidRequestError → fail fast (user must fix config).
_RETRYABLE = (
    openai.RateLimitError,
    openai.APITimeoutError,
    openai.APIConnectionError,
)


class OpenAIEmbedder:
    """
    Batch embedding via OpenAI Embeddings API.

    Usage:
        embedder = OpenAIEmbedder()
        vectors = embedder.embed_batch(["Metformin dosing", "HbA1c target"])
    """

    def __init__(self, config: EmbeddingConfig | None = None) -> None:
        self._cfg = config or EMBEDDING_CONFIG
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "OPENAI_API_KEY environment variable is not set. "
                "Set it in your .env file or shell before running ingestion."
            )
        self._client = openai.OpenAI(
            api_key=api_key,
            timeout=self._cfg.request_timeout_seconds,
        )
        logger.info(
            "OpenAIEmbedder ready: model=%s dim=%d batch=%d normalize=%s",
            self._cfg.model_name, self._cfg.dimensions,
            self._cfg.batch_size, self._cfg.normalize,
        )

    # ------------------------------------------------------------------
    # Embedder Protocol implementation
    # ------------------------------------------------------------------

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Embed a batch of texts. Splits into sub-batches if len(texts) > batch_size.

        Args:
            texts: List of strings to embed (no length limit — internally batched).

        Returns:
            List of float vectors (one per text), L2-normalised if config.normalize=True.
        """
        if not texts:
            return []

        all_vectors: list[list[float]] = []
        batch_size = self._cfg.batch_size

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            vectors = self._embed_with_retry(batch)
            all_vectors.extend(vectors)

        return all_vectors

    @property
    def dimensions(self) -> int:
        return self._cfg.dimensions

    @property
    def model_name(self) -> str:
        return self._cfg.model_name

    # ------------------------------------------------------------------
    # Internal: retried single-batch call
    # ------------------------------------------------------------------

    @retry(
        retry=retry_if_exception_type(_RETRYABLE),
        wait=wait_exponential(multiplier=1, min=1, max=16),
        stop=stop_after_attempt(3),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    def _embed_with_retry(self, texts: list[str]) -> list[list[float]]:
        """Single API call with tenacity retry wrapping."""
        response = self._client.embeddings.create(
            model=self._cfg.model_name,
            input=texts,
        )
        # response.data is sorted by index — safe to zip directly
        vectors = [item.embedding for item in response.data]

        if self._cfg.normalize:
            vectors = [_l2_normalize(v) for v in vectors]

        logger.debug("Embedded batch of %d texts.", len(texts))
        return vectors


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _l2_normalize(vector: list[float]) -> list[float]:
    """L2-normalise a vector to unit length."""
    norm = math.sqrt(sum(x * x for x in vector))
    if norm == 0.0:
        return vector  # zero vector — return as-is to avoid division by zero
    return [x / norm for x in vector]
