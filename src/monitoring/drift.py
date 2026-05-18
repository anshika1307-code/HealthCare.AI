"""
src/monitoring/drift.py
------------------------
DriftDetector — detects embedding distribution drift using centroid cosine distance.

Algorithm (from decision.md / observability_specs.md):
    drift_score = 1 - cosine_similarity(new_centroid, baseline_centroid)
    threshold  : 0.15  (conservative — alert more than miss a real drift)

The baseline centroid is stored in Redis as a raw float64 array (tobytes/frombuffer)
so it persists across restarts.  On the first call the current batch becomes
the baseline and drift_score is 0.0.

Graceful degradation: if Redis or numpy are unavailable, returns 0.0 and logs a warning.
"""

from __future__ import annotations

import logging

import numpy as np

logger = logging.getLogger(__name__)

_THRESHOLD = 0.15
_BASELINE_KEY = "drift:baseline_centroid"
_DTYPE = np.float64

try:
    import redis.asyncio as aioredis

    _REDIS_AVAILABLE = True
except ImportError:  # pragma: no cover
    _REDIS_AVAILABLE = False


class DriftDetector:
    """
    Usage (typically called after every ingestion batch):

        detector = DriftDetector(redis_url="redis://localhost:6379")
        drift = await detector.on_new_batch(embeddings)  # list[list[float]]
        if drift > 0.15:
            alert(...)
    """

    def __init__(self, redis_url: str = "redis://localhost:6379") -> None:
        if not _REDIS_AVAILABLE:  # pragma: no cover
            logger.warning("redis package not installed — drift detection disabled")
            self._client = None
            return
        self._client = aioredis.from_url(redis_url, decode_responses=False)

    async def on_new_batch(self, embeddings: list[list[float]]) -> float:
        """
        Compute centroid of new batch, compare to baseline, return drift score.

        Returns:
            drift_score in [0, 1].  0 = identical to baseline.  1 = completely different.
            Returns 0.0 if Redis is unavailable or batch is empty.
        """
        if not embeddings or self._client is None:
            return 0.0

        new_centroid = np.mean(np.array(embeddings, dtype=_DTYPE), axis=0)

        try:
            baseline_bytes: bytes | None = await self._client.get(_BASELINE_KEY)
        except Exception as exc:  # noqa: BLE001
            logger.warning("DriftDetector: Redis unavailable — %s", exc)
            return 0.0

        if baseline_bytes is None:
            # First batch ever — store as baseline
            await self._store_centroid(new_centroid)
            logger.info("DriftDetector: baseline centroid stored (dim=%d)", len(new_centroid))
            return 0.0

        baseline = np.frombuffer(baseline_bytes, dtype=_DTYPE)

        if baseline.shape != new_centroid.shape:
            logger.warning(
                "DriftDetector: centroid dimension mismatch (baseline=%d, new=%d) — resetting baseline",
                baseline.shape[0],
                new_centroid.shape[0],
            )
            await self._store_centroid(new_centroid)
            return 0.0

        drift_score = float(1.0 - _cosine_similarity(new_centroid, baseline))

        if drift_score > _THRESHOLD:
            logger.warning(
                "Embedding drift detected: drift_score=%.4f > threshold=%.2f — "
                "consider re-evaluating retrieval quality",
                drift_score,
                _THRESHOLD,
            )
        else:
            logger.info("Embedding drift check: drift_score=%.4f (ok)", drift_score)

        return drift_score

    async def update_baseline(self, embeddings: list[list[float]]) -> None:
        """Explicitly replace the stored baseline (e.g., after a planned doc update)."""
        if not embeddings or self._client is None:
            return
        centroid = np.mean(np.array(embeddings, dtype=_DTYPE), axis=0)
        await self._store_centroid(centroid)
        logger.info("DriftDetector: baseline updated (dim=%d)", len(centroid))

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()

    async def _store_centroid(self, centroid: np.ndarray) -> None:
        try:
            await self._client.set(_BASELINE_KEY, centroid.astype(_DTYPE).tobytes())
        except Exception as exc:  # noqa: BLE001
            logger.warning("DriftDetector: failed to store centroid — %s", exc)


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity in [−1, 1].  Both vectors must be same shape."""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 1.0  # treat zero-vectors as identical (degenerate case)
    return float(np.dot(a, b) / (norm_a * norm_b))
