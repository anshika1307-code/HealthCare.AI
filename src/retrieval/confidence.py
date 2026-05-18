"""
src/retrieval/confidence.py
----------------------------
Confidence scoring layer — evaluates retrieval quality and decides whether
to attach a low-confidence warning to the response.

Design rationale (from decision.md):
- We flag uncertain answers to the user rather than suppressing them.
  Suppressing creates a worse clinical outcome — the user assumes the system
  knows nothing and goes to a less reliable source.
- The confidence proxy is the top-1 reranker score (sigmoid-normalised).
  A low top-1 score means even the best retrieved chunk scored poorly
  against the query, suggesting retrieval quality is low.
- Threshold (0.40) is conservative and will be tuned post-RAGAS evaluation.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from configs.retrieval import RETRIEVAL_CONFIG, ConfidenceConfig

from retrieval.reranker import RankedResult

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result type — final output of the retrieval pipeline
# ---------------------------------------------------------------------------

@dataclass
class RetrievalResult:
    """
    The structured output returned by the retrieval pipeline to the LLM node.
    Contains the top-ranked chunks plus a confidence assessment.
    """
    query: str
    chunks: list[RankedResult]           # top-n chunks for LLM context, ranked
    confidence_score: float              # top-1 reranker score [0, 1]
    low_confidence: bool                 # True if score < threshold
    warning_message: str = ""           # populated when low_confidence=True
    filters_applied: dict[str, Any] = field(default_factory=dict)

    @property
    def context_text(self) -> str:
        """
        Format chunks into a numbered context block for the LLM prompt.
        Each chunk is labelled with its source document and section.
        """
        parts: list[str] = []
        for i, chunk in enumerate(self.chunks, start=1):
            source = chunk.document_id
            section = chunk.section_name
            label = f"[{i}] {source}" + (f" — {section}" if section else "")
            parts.append(f"{label}\n{chunk.text}")
        return "\n\n".join(parts)

    @property
    def has_safety_content(self) -> bool:
        """True if any retrieved chunk is flagged as safety-relevant."""
        return any(c.safety_flag for c in self.chunks)


# ---------------------------------------------------------------------------
# Confidence Scorer
# ---------------------------------------------------------------------------

class ConfidenceScorer:
    """
    Evaluates the quality of the retrieval result and attaches a warning
    if the top-1 reranker score is below the configured threshold.

    Usage:
        scorer = ConfidenceScorer()
        result = scorer.score(query, ranked_chunks, filters_applied)
    """

    def __init__(self, config: ConfidenceConfig | None = None) -> None:
        self._cfg = config or RETRIEVAL_CONFIG.confidence

    def score(
        self,
        query: str,
        ranked_chunks: list[RankedResult],
        filters_applied: dict[str, Any] | None = None,
    ) -> RetrievalResult:
        """
        Build the final RetrievalResult with confidence assessment.

        Args:
            query:           Original user query.
            ranked_chunks:   Reranked chunks (from CrossEncoderReranker.rerank).
            filters_applied: Metadata filters used during retrieval (for audit).

        Returns:
            RetrievalResult with confidence_score, low_confidence flag, and
            warning_message (empty string when confidence is adequate).
        """
        if not ranked_chunks:
            # No results at all — maximum low-confidence
            logger.warning("No chunks retrieved for query: %r", query[:80])
            return RetrievalResult(
                query=query,
                chunks=[],
                confidence_score=0.0,
                low_confidence=True,
                warning_message=self._cfg.warning_message,
                filters_applied=filters_applied or {},
            )

        # Use top-1 reranker score as the confidence proxy
        top_score = ranked_chunks[0].reranker_score
        low_confidence = top_score < self._cfg.low_confidence_threshold

        warning = ""
        if low_confidence:
            warning = self._cfg.warning_message
            logger.info(
                "Low confidence retrieval (score=%.4f < threshold=%.2f) for query: %r",
                top_score, self._cfg.low_confidence_threshold, query[:80],
            )

        if ranked_chunks[0].safety_flag:
            logger.info("Safety-flagged chunk in top position for query: %r", query[:80])

        return RetrievalResult(
            query=query,
            chunks=ranked_chunks,
            confidence_score=top_score,
            low_confidence=low_confidence,
            warning_message=warning,
            filters_applied=filters_applied or {},
        )
