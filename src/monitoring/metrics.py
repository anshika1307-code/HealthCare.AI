"""
src/monitoring/metrics.py
--------------------------
RAGMetrics — per-query observability sink backed by Redis sorted sets.

PHI POLICY: Query text is NEVER stored. Only query_id (UUID), timings,
scores, and document IDs are recorded.

Redis schema
------------
metrics:latency        sorted set  score=unix_ts  value="<qid>|<total_ms>"
metrics:embed_time     sorted set  score=unix_ts  value="<qid>|<ms>"
metrics:retrieve_time  sorted set  score=unix_ts  value="<qid>|<ms>"
metrics:generate_time  sorted set  score=unix_ts  value="<qid>|<ms>"
metrics:confidence     sorted set  score=unix_ts  value="<qid>|<score>"
metrics:query_count    string      incremented per query
metrics:low_conf_count string      incremented when low_confidence=True
metrics:error_count    string      incremented on pipeline errors

All sorted-set entries are capped at MAX_ENTRIES (default 10 000) via ZREMRANGEBYRANK
so Redis memory stays bounded.

Graceful degradation
--------------------
If Redis is unreachable, every method logs a warning and returns silently.
The main request pipeline is never interrupted by observability failures.
"""

from __future__ import annotations

import logging
import time

try:
    import redis.asyncio as aioredis

    _REDIS_AVAILABLE = True
except ImportError:  # pragma: no cover
    _REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)

_MAX_ENTRIES = 10_000


class RAGMetrics:
    """
    Async metrics recorder.  Instantiate once at app startup and store on app.state.

    Example:
        metrics = RAGMetrics(redis_url="redis://localhost:6379")
        await metrics.record(
            query_id="abc123",
            total_ms=412,
            embed_ms=12,
            retrieve_ms=210,
            generate_ms=190,
            confidence_score=0.82,
            doc_ids=["ada_sec9", "jnc8_ch3"],
            low_confidence=False,
        )
    """

    def __init__(self, redis_url: str = "redis://localhost:6379") -> None:
        if not _REDIS_AVAILABLE:  # pragma: no cover
            logger.warning("redis package not installed — metrics disabled")
            self._client: aioredis.Redis | None = None  # type: ignore[assignment]
            return
        self._client = aioredis.from_url(redis_url, decode_responses=True)

    async def record(
        self,
        *,
        query_id: str,
        total_ms: float,
        embed_ms: float,
        retrieve_ms: float,
        generate_ms: float,
        confidence_score: float,
        doc_ids: list[str],
        low_confidence: bool,
    ) -> None:
        """Write all per-query metrics to Redis in a single pipeline."""
        if self._client is None:
            return
        ts = time.time()
        try:
            pipe = self._client.pipeline(transaction=False)
            _zadd(pipe, "metrics:latency", ts, f"{query_id}|{total_ms:.1f}")
            _zadd(pipe, "metrics:embed_time", ts, f"{query_id}|{embed_ms:.1f}")
            _zadd(pipe, "metrics:retrieve_time", ts, f"{query_id}|{retrieve_ms:.1f}")
            _zadd(pipe, "metrics:generate_time", ts, f"{query_id}|{generate_ms:.1f}")
            _zadd(pipe, "metrics:confidence", ts, f"{query_id}|{confidence_score:.4f}")
            pipe.incr("metrics:query_count")
            if low_confidence:
                pipe.incr("metrics:low_conf_count")
            await pipe.execute()
        except Exception as exc:  # noqa: BLE001
            logger.warning("metrics.record failed (Redis unavailable?): %s", exc)

    async def record_error(self, *, query_id: str, error_type: str) -> None:
        """Increment error counter and add to sorted set for time-series analysis."""
        if self._client is None:
            return
        ts = time.time()
        try:
            pipe = self._client.pipeline(transaction=False)
            _zadd(pipe, "metrics:errors", ts, f"{query_id}|{error_type}")
            pipe.incr("metrics:error_count")
            await pipe.execute()
        except Exception as exc:  # noqa: BLE001
            logger.warning("metrics.record_error failed: %s", exc)

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()


def _zadd(pipe: aioredis.client.Pipeline, key: str, score: float, value: str) -> None:  # type: ignore[name-defined]
    """Add to sorted set and trim to MAX_ENTRIES to bound Redis memory."""
    pipe.zadd(key, {value: score})
    # Keep only the most recent MAX_ENTRIES records
    pipe.zremrangebyrank(key, 0, -(_MAX_ENTRIES + 2))
