"""
tests/unit/test_retrieval_confidence.py
-----------------------------------------
Unit tests for src/retrieval/confidence.py

Coverage
--------
RetrievalResult.context_text     — numbered label format, section included/omitted
RetrievalResult.has_safety_content — any safety chunk present
ConfidenceScorer.score           — empty chunks, above/below threshold, warning msg
"""

import pytest

from configs.retrieval import ConfidenceConfig
from retrieval.confidence import ConfidenceScorer, RetrievalResult
from retrieval.reranker import RankedResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cfg(**overrides) -> ConfidenceConfig:
    base = dict(
        low_confidence_threshold=0.40,
        warning_message="⚠️ Low confidence warning.",
        return_answer_below_threshold=True,
        score_source="top1_reranker",
    )
    base.update(overrides)
    return ConfidenceConfig(**base)


def _ranked(
    chunk_id: str = "id",
    score: float = 0.8,
    text: str = "Clinical text.",
    doc_id: str = "metformin_fda_label",
    section: str = "DOSAGE",
    safety: bool = False,
) -> RankedResult:
    return RankedResult(
        chunk_id=chunk_id,
        reranker_score=score,
        text=text,
        payload={
            "document_id": doc_id,
            "section_name": section,
            "safety_flag": safety,
        },
    )


# ===========================================================================
# RetrievalResult.context_text
# ===========================================================================

class TestContextText:

    def test_single_chunk_produces_labelled_block(self):
        result = RetrievalResult(
            query="q",
            chunks=[_ranked(doc_id="fda", section="DOSAGE", text="Metformin 500 mg.")],
            confidence_score=0.8,
            low_confidence=False,
        )
        ctx = result.context_text
        assert "[1] fda" in ctx
        assert "DOSAGE" in ctx
        assert "Metformin 500 mg." in ctx

    def test_multiple_chunks_numbered_sequentially(self):
        result = RetrievalResult(
            query="q",
            chunks=[_ranked(chunk_id=f"id-{i}") for i in range(3)],
            confidence_score=0.8,
            low_confidence=False,
        )
        ctx = result.context_text
        assert "[1]" in ctx
        assert "[2]" in ctx
        assert "[3]" in ctx

    def test_section_omitted_when_empty(self):
        """When section_name is empty string, the ' — section' part is not added."""
        chunk = _ranked(doc_id="jnc8", section="", text="BP target.")
        result = RetrievalResult(
            query="q", chunks=[chunk], confidence_score=0.8, low_confidence=False
        )
        ctx = result.context_text
        assert "—" not in ctx       # no dash when section is absent
        assert "jnc8" in ctx

    def test_empty_chunks_returns_empty_string(self):
        result = RetrievalResult(
            query="q", chunks=[], confidence_score=0.0, low_confidence=True
        )
        assert result.context_text == ""

    def test_chunks_separated_by_double_newline(self):
        result = RetrievalResult(
            query="q",
            chunks=[_ranked(chunk_id="a"), _ranked(chunk_id="b")],
            confidence_score=0.8,
            low_confidence=False,
        )
        assert "\n\n" in result.context_text


# ===========================================================================
# RetrievalResult.has_safety_content
# ===========================================================================

class TestHasSafetyContent:

    def test_true_when_any_chunk_is_safety_flagged(self):
        result = RetrievalResult(
            query="q",
            chunks=[_ranked(safety=False), _ranked(safety=True)],
            confidence_score=0.8,
            low_confidence=False,
        )
        assert result.has_safety_content is True

    def test_false_when_no_safety_chunks(self):
        result = RetrievalResult(
            query="q",
            chunks=[_ranked(safety=False), _ranked(safety=False)],
            confidence_score=0.8,
            low_confidence=False,
        )
        assert result.has_safety_content is False

    def test_false_for_empty_chunk_list(self):
        result = RetrievalResult(
            query="q", chunks=[], confidence_score=0.0, low_confidence=True
        )
        assert result.has_safety_content is False


# ===========================================================================
# ConfidenceScorer.score
# ===========================================================================

class TestConfidenceScorer:

    def test_empty_chunks_returns_low_confidence(self):
        scorer = ConfidenceScorer(_cfg(low_confidence_threshold=0.4))
        result = scorer.score("query", [])
        assert result.low_confidence is True
        assert result.confidence_score == 0.0

    def test_empty_chunks_attaches_warning_message(self):
        scorer = ConfidenceScorer(_cfg(warning_message="WARNING"))
        result = scorer.score("query", [])
        assert result.warning_message == "WARNING"

    def test_empty_chunks_result_has_empty_chunk_list(self):
        scorer = ConfidenceScorer(_cfg())
        result = scorer.score("query", [])
        assert result.chunks == []

    def test_score_above_threshold_is_high_confidence(self):
        scorer = ConfidenceScorer(_cfg(low_confidence_threshold=0.40))
        result = scorer.score("query", [_ranked(score=0.85)])
        assert result.low_confidence is False
        assert result.warning_message == ""

    def test_score_below_threshold_is_low_confidence(self):
        scorer = ConfidenceScorer(_cfg(low_confidence_threshold=0.40))
        result = scorer.score("query", [_ranked(score=0.25)])
        assert result.low_confidence is True

    def test_low_confidence_attaches_warning_message(self):
        scorer = ConfidenceScorer(_cfg(
            low_confidence_threshold=0.40,
            warning_message="⚠️ Low confidence.",
        ))
        result = scorer.score("query", [_ranked(score=0.20)])
        assert result.warning_message == "⚠️ Low confidence."

    def test_high_confidence_warning_message_is_empty_string(self):
        scorer = ConfidenceScorer(_cfg(low_confidence_threshold=0.40))
        result = scorer.score("query", [_ranked(score=0.90)])
        assert result.warning_message == ""

    def test_top1_score_is_used_as_confidence_score(self):
        """confidence_score must equal the top-1 chunk's reranker_score."""
        scorer = ConfidenceScorer(_cfg())
        chunks = [_ranked(score=0.72), _ranked(score=0.50)]
        result = scorer.score("query", chunks)
        assert result.confidence_score == pytest.approx(0.72)

    def test_threshold_boundary_equal_is_high_confidence(self):
        """score == threshold → not low_confidence (strict less-than comparison)."""
        scorer = ConfidenceScorer(_cfg(low_confidence_threshold=0.40))
        result = scorer.score("query", [_ranked(score=0.40)])
        assert result.low_confidence is False

    def test_query_preserved_in_result(self):
        scorer = ConfidenceScorer(_cfg())
        result = scorer.score("metformin dosing renal", [_ranked()])
        assert result.query == "metformin dosing renal"

    def test_chunks_preserved_in_result(self):
        scorer = ConfidenceScorer(_cfg())
        chunks = [_ranked(chunk_id="c1"), _ranked(chunk_id="c2")]
        result = scorer.score("query", chunks)
        assert len(result.chunks) == 2

    def test_filters_applied_stored_in_result(self):
        scorer = ConfidenceScorer(_cfg())
        filters = {"document_id": "jnc8"}
        result = scorer.score("query", [_ranked()], filters_applied=filters)
        assert result.filters_applied == {"document_id": "jnc8"}

    def test_filters_none_stored_as_empty_dict(self):
        scorer = ConfidenceScorer(_cfg())
        result = scorer.score("query", [_ranked()], filters_applied=None)
        assert result.filters_applied == {}
