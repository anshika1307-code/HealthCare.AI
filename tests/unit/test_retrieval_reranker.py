"""
tests/unit/test_retrieval_reranker.py
---------------------------------------
Unit tests for src/retrieval/reranker.py

CrossEncoder is patched so sentence-transformers is not loaded during tests.

Coverage
--------
RankedResult        — property accessors (document_id, section_name, safety_flag)
CrossEncoderReranker._predict_sync — sigmoid normalisation on/off, batching
CrossEncoderReranker.rerank        — empty input, top-n selection, ordering
"""

import math

import pytest
from unittest.mock import MagicMock, patch

from configs.retrieval import RerankerConfig
from retrieval.rrf_ranker import FusedResult
from retrieval.reranker import CrossEncoderReranker, RankedResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cfg(**overrides) -> RerankerConfig:
    base = dict(
        model_name="cross-encoder/ms-marco-MiniLM-L-6-v2",
        top_n=3,
        batch_size=2,
        device="cpu",
        normalize_scores=True,
    )
    base.update(overrides)
    return RerankerConfig(**base)


def _fused(chunk_id: str = "id", text: str = "text", **payload_overrides) -> FusedResult:
    payload = {"document_id": "fda", "section_name": "DOSAGE", "safety_flag": False}
    payload.update(payload_overrides)
    return FusedResult(chunk_id=chunk_id, rrf_score=0.5, text=text, payload=payload)


@pytest.fixture
def reranker() -> CrossEncoderReranker:
    """CrossEncoderReranker with the CrossEncoder model fully mocked."""
    with patch("retrieval.reranker.CrossEncoder") as mock_ce_cls:
        mock_model = MagicMock()
        mock_model.predict.return_value = [0.0]   # default: one raw score
        mock_ce_cls.return_value = mock_model
        r = CrossEncoderReranker(config=_cfg())
    return r


# ===========================================================================
# RankedResult
# ===========================================================================

class TestRankedResult:

    def test_document_id_from_payload(self):
        r = RankedResult(
            chunk_id="id", reranker_score=0.8, text="t",
            payload={"document_id": "jnc8"},
        )
        assert r.document_id == "jnc8"

    def test_section_name_from_payload(self):
        r = RankedResult(
            chunk_id="id", reranker_score=0.8, text="t",
            payload={"section_name": "Recommendation 1"},
        )
        assert r.section_name == "Recommendation 1"

    def test_safety_flag_true_from_payload(self):
        r = RankedResult(
            chunk_id="id", reranker_score=0.8, text="t",
            payload={"safety_flag": True},
        )
        assert r.safety_flag is True

    def test_safety_flag_false_when_absent(self):
        r = RankedResult(chunk_id="id", reranker_score=0.8, text="t", payload={})
        assert r.safety_flag is False

    def test_document_id_empty_when_absent(self):
        r = RankedResult(chunk_id="id", reranker_score=0.8, text="t", payload={})
        assert r.document_id == ""

    def test_section_name_empty_when_absent(self):
        r = RankedResult(chunk_id="id", reranker_score=0.8, text="t", payload={})
        assert r.section_name == ""


# ===========================================================================
# CrossEncoderReranker._predict_sync
# ===========================================================================

class TestPredictSync:

    def test_sigmoid_applied_when_normalize_true(self, reranker):
        """sigmoid(0.0) = 0.5; the output should be exactly 0.5."""
        reranker._model.predict.return_value = [0.0]
        result = reranker._predict_sync([("query", "text")])
        assert abs(result[0] - 0.5) < 1e-9

    def test_sigmoid_positive_logit(self, reranker):
        """sigmoid(large positive) → close to 1.0."""
        reranker._model.predict.return_value = [100.0]
        result = reranker._predict_sync([("query", "text")])
        assert result[0] > 0.99

    def test_sigmoid_negative_logit(self, reranker):
        """sigmoid(large negative) → close to 0.0."""
        reranker._model.predict.return_value = [-100.0]
        result = reranker._predict_sync([("query", "text")])
        assert result[0] < 0.01

    def test_no_sigmoid_when_normalize_false(self):
        """With normalize_scores=False, raw model output is returned unchanged."""
        with patch("retrieval.reranker.CrossEncoder") as mock_ce_cls:
            mock_model = MagicMock()
            mock_model.predict.return_value = [3.7]
            mock_ce_cls.return_value = mock_model
            r = CrossEncoderReranker(config=_cfg(normalize_scores=False))

        result = r._predict_sync([("query", "text")])
        assert result[0] == pytest.approx(3.7)

    def test_splits_into_batches(self, reranker):
        """batch_size=2, 5 pairs → 3 predict calls (2+2+1)."""
        reranker._model.predict.return_value = [0.0, 0.0]
        pairs = [("q", f"t{i}") for i in range(5)]
        reranker._predict_sync(pairs)
        assert reranker._model.predict.call_count == 3

    def test_returns_one_score_per_pair(self, reranker):
        reranker._model.predict.return_value = [0.5, 0.6]
        result = reranker._predict_sync([("q", "t1"), ("q", "t2")])
        assert len(result) == 2


# ===========================================================================
# CrossEncoderReranker.rerank
# ===========================================================================

class TestRerank:

    @pytest.mark.asyncio
    async def test_empty_candidates_returns_empty_list(self, reranker):
        result = await reranker.rerank("query", [])
        assert result == []

    @pytest.mark.asyncio
    async def test_returns_ranked_result_objects(self, reranker):
        reranker._predict_sync = MagicMock(return_value=[0.8])
        result = await reranker.rerank("query", [_fused("id-1")])
        assert len(result) == 1
        assert isinstance(result[0], RankedResult)

    @pytest.mark.asyncio
    async def test_results_sorted_by_score_descending(self, reranker):
        reranker._predict_sync = MagicMock(return_value=[0.3, 0.9, 0.6])
        candidates = [_fused(f"id-{i}") for i in range(3)]
        result = await reranker.rerank("query", candidates)
        scores = [r.reranker_score for r in result]
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_top_n_limits_output(self, reranker):
        """top_n=3 from config; 5 candidates → at most 3 returned."""
        reranker._predict_sync = MagicMock(return_value=[0.9, 0.8, 0.7, 0.6, 0.5])
        candidates = [_fused(f"id-{i}") for i in range(5)]
        result = await reranker.rerank("query", candidates)
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_top_n_override(self, reranker):
        reranker._predict_sync = MagicMock(return_value=[0.9, 0.8, 0.7, 0.6])
        candidates = [_fused(f"id-{i}") for i in range(4)]
        result = await reranker.rerank("query", candidates, top_n=2)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_chunk_id_preserved_in_result(self, reranker):
        reranker._predict_sync = MagicMock(return_value=[0.7])
        result = await reranker.rerank("query", [_fused("my-special-id")])
        assert result[0].chunk_id == "my-special-id"

    @pytest.mark.asyncio
    async def test_text_preserved_in_result(self, reranker):
        reranker._predict_sync = MagicMock(return_value=[0.7])
        result = await reranker.rerank("query", [_fused(text="clinical text here")])
        assert result[0].text == "clinical text here"
