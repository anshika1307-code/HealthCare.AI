"""
src/retrieval/bm25_retriever.py
--------------------------------
BM25 keyword retriever backed by rank_bm25 with a pickled corpus cache.

Design notes:
- BM25 is purely in-memory and CPU-based — no network call needed.
- The corpus (tokenised chunk texts) is built once by scripts/build_bm25_index.py
  and cached as a pickle. The retriever loads it at startup.
- Whitespace tokenisation preserves medical compound tokens (HbA1c, mm Hg, eGFR).
- Returns (chunk_id, score) pairs aligned with DenseRetriever's output so the
  RRF ranker can consume both lists with the same interface.
"""
from __future__ import annotations

import logging
import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from configs.retrieval import RETRIEVAL_CONFIG, BM25Config
from rank_bm25 import BM25Okapi

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result type (mirrors DenseResult interface for RRF)
# ---------------------------------------------------------------------------

@dataclass
class BM25Result:
    """A single hit returned by the BM25 retriever."""
    chunk_id: str       # matches the chunk_id stored in the BM25 corpus index
    score: float        # raw BM25 score (not normalised — RRF only needs rank)
    text: str = ""      # chunk text (stored in corpus for reranker use)
    payload: dict[str, Any] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.payload is None:
            self.payload = {}


# ---------------------------------------------------------------------------
# Corpus index (stored in pickle by build_bm25_index.py)
# ---------------------------------------------------------------------------

@dataclass
class BM25Corpus:
    """The serialisable data structure saved by the index builder."""
    chunk_ids: list[str]         # chunk_ids[i] corresponds to tokenised_corpus[i]
    tokenised_corpus: list[list[str]]
    chunk_texts: list[str]       # raw text for reranker (parallel with chunk_ids)
    chunk_payloads: list[dict]   # full metadata per chunk (parallel with chunk_ids)


# ---------------------------------------------------------------------------
# Retriever
# ---------------------------------------------------------------------------

class BM25Retriever:
    """
    BM25 keyword retriever over the pre-built corpus cache.

    Usage:
        retriever = BM25Retriever.from_cache("data/cache/bm25_corpus.pkl")
        results = retriever.search("metformin contraindications renal impairment")
    """

    def __init__(self, corpus: BM25Corpus, config: BM25Config | None = None) -> None:
        self._cfg = config or RETRIEVAL_CONFIG.bm25
        self._corpus = corpus
        self._bm25 = BM25Okapi(
            corpus.tokenised_corpus,
            k1=self._cfg.k1,
            b=self._cfg.b,
        )
        logger.info(
            "BM25Retriever initialised: %d chunks, k1=%.2f, b=%.2f",
            len(corpus.chunk_ids), self._cfg.k1, self._cfg.b,
        )

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def from_cache(
        cls,
        cache_path: str | Path | None = None,
        config: BM25Config | None = None,
    ) -> BM25Retriever:
        """Load a pre-built BM25Corpus from disk and return a ready retriever."""
        cfg = config or RETRIEVAL_CONFIG.bm25
        path = Path(cache_path or cfg.corpus_cache_path)

        if not path.exists():
            raise FileNotFoundError(
                f"BM25 corpus cache not found at {path}. "
                "Run `python scripts/build_bm25_index.py` after ingestion."
            )

        with path.open("rb") as fh:
            corpus: BM25Corpus = pickle.load(fh)

        logger.info("Loaded BM25 corpus from %s (%d chunks)", path, len(corpus.chunk_ids))
        return cls(corpus, cfg)

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(
        self,
        query: str,
        top_k: int | None = None,
        filter_doc_id: str | None = None,
    ) -> list[BM25Result]:
        """
        Score all corpus chunks against the query and return top-k results.

        Args:
            query:          Raw user query string (will be tokenised here).
            top_k:          Override config top_k for this call.
            filter_doc_id:  Optional — restrict results to a specific document.

        Returns:
            List of BM25Result sorted by BM25 score descending.
        """
        k = top_k or self._cfg.top_k
        tokens = self._tokenise(query)
        scores: list[float] = self._bm25.get_scores(tokens).tolist()

        # Pair scores with chunk metadata, filter if requested
        scored: list[tuple[float, int]] = []
        for idx, score in enumerate(scores):
            if score <= 0.0:
                continue
            if filter_doc_id:
                payload = self._corpus.chunk_payloads[idx]
                if payload.get("document_id") != filter_doc_id:
                    continue
            scored.append((score, idx))

        # Sort descending by score, take top-k
        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:k]

        results = [
            BM25Result(
                chunk_id=self._corpus.chunk_ids[idx],
                score=score,
                text=self._corpus.chunk_texts[idx],
                payload=self._corpus.chunk_payloads[idx],
            )
            for score, idx in top
        ]
        logger.debug("BM25 search returned %d results (k=%d)", len(results), k)
        return results

    # ------------------------------------------------------------------
    # Tokeniser
    # ------------------------------------------------------------------

    def _tokenise(self, text: str) -> list[str]:
        """
        Whitespace tokeniser — same logic used at index build time.
        Preserves medical compound tokens: 'HbA1c', 'mm Hg', 'eGFR <30'.
        """
        return text.lower().split()
