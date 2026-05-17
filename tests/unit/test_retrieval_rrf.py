"""
tests/unit/test_retrieval_rrf.py
----------------------------------
Unit tests for src/retrieval/rrf_ranker.py

Coverage
--------
FusedResult  — dataclass field defaults
RRFRanker    — score formula, chunk-in-both-lists, single-retriever chunks,
               ordering, pool_size limit, empty inputs, source attribution
"""

import pytest

from configs.retrieval import RRFConfig
from retrieval.bm25_retriever import BM25Result
from retrieval.dense_retriever import DenseResult
from retrieval.rrf_ranker import FusedResult, RRFRanker


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cfg(k: int = 60, pool_size: int = 40, dw: float = 1.0, bw: float = 1.0) -> RRFConfig:
    return RRFConfig(k=k, dense_weight=dw, bm25_weight=bw, fusion_pool_size=pool_size)


def _dense(chunk_id: str, score: float = 0.9, text: str = "text") -> DenseResult:
    return DenseResult(chunk_id=chunk_id, score=score, payload={}, text=text)


def _bm25(chunk_id: str, score: float = 10.0, text: str = "text") -> BM25Result:
    return BM25Result(chunk_id=chunk_id, score=score, text=text)


# ===========================================================================
# FusedResult
# ===========================================================================

class TestFusedResult:

    def test_payload_defaults_to_empty_dict(self):
        fr = FusedResult(chunk_id="id", rrf_score=0.5)
        assert fr.payload == {}

    def test_optional_rank_fields_default_to_none(self):
        fr = FusedResult(chunk_id="id", rrf_score=0.5)
        assert fr.dense_rank is None
        assert fr.bm25_rank is None
        assert fr.dense_score is None
        assert fr.bm25_score is None


# ===========================================================================
# RRFRanker.fuse — score formula
# ===========================================================================

class TestRRFScoreFormula:
    """Verify the RRF score matches the reference formula: w / (k + rank)."""

    def test_single_dense_hit_score_matches_formula(self):
        ranker = RRFRanker(_cfg(k=60, dw=1.0))
        result = ranker.fuse([_dense("id-1")], [])
        expected = 1.0 / (60 + 1)
        assert abs(result[0].rrf_score - expected) < 1e-10

    def test_single_bm25_hit_score_matches_formula(self):
        ranker = RRFRanker(_cfg(k=60, bw=1.0))
        result = ranker.fuse([], [_bm25("id-1")])
        expected = 1.0 / (60 + 1)
        assert abs(result[0].rrf_score - expected) < 1e-10

    def test_chunk_in_both_lists_accumulates_both_contributions(self):
        ranker = RRFRanker(_cfg(k=60))
        result = ranker.fuse([_dense("shared")], [_bm25("shared")])
        expected = (1.0 / (60 + 1)) + (1.0 / (60 + 1))
        assert abs(result[0].rrf_score - expected) < 1e-10

    def test_higher_rank_chunk_scores_higher(self):
        """Rank 1 should score higher than rank 2 (same retriever)."""
        ranker = RRFRanker(_cfg(k=60))
        result = ranker.fuse(
            [_dense("rank-1"), _dense("rank-2")], []
        )
        rank1 = next(r for r in result if r.chunk_id == "rank-1")
        rank2 = next(r for r in result if r.chunk_id == "rank-2")
        assert rank1.rrf_score > rank2.rrf_score

    def test_dense_weight_scales_contribution(self):
        ranker = RRFRanker(_cfg(k=60, dw=2.0, bw=1.0))
        result = ranker.fuse([_dense("id")], [])
        expected = 2.0 / (60 + 1)
        assert abs(result[0].rrf_score - expected) < 1e-10


# ===========================================================================
# RRFRanker.fuse — ordering and pool
# ===========================================================================

class TestFuseOrdering:

    def test_results_sorted_by_rrf_score_descending(self):
        ranker = RRFRanker(_cfg())
        dense = [_dense("d1"), _dense("d2"), _dense("d3")]
        result = ranker.fuse(dense, [])
        scores = [r.rrf_score for r in result]
        assert scores == sorted(scores, reverse=True)

    def test_chunk_in_both_lists_ranks_above_single_list_chunk(self):
        """
        'shared' appears in both → higher RRF score than 'dense-only' at rank 2.
        """
        ranker = RRFRanker(_cfg(k=60))
        dense = [_dense("dense-only"), _dense("shared")]
        bm25 = [_bm25("shared")]
        result = ranker.fuse(dense, bm25)
        ids_in_order = [r.chunk_id for r in result]
        assert ids_in_order.index("shared") < ids_in_order.index("dense-only")

    def test_pool_size_limits_output(self):
        ranker = RRFRanker(_cfg(pool_size=2))
        dense = [_dense(f"d-{i}") for i in range(5)]
        result = ranker.fuse(dense, [])
        assert len(result) <= 2

    def test_output_does_not_exceed_union_size(self):
        ranker = RRFRanker(_cfg(pool_size=100))
        dense = [_dense("a"), _dense("b")]
        bm25 = [_bm25("b"), _bm25("c")]
        result = ranker.fuse(dense, bm25)
        # Union of {a, b} ∪ {b, c} = 3 unique chunks
        assert len(result) == 3


# ===========================================================================
# RRFRanker.fuse — empty inputs
# ===========================================================================

class TestFuseEmptyInputs:

    def test_both_empty_returns_empty_list(self):
        ranker = RRFRanker(_cfg())
        assert ranker.fuse([], []) == []

    def test_empty_dense_returns_bm25_only_results(self):
        ranker = RRFRanker(_cfg())
        result = ranker.fuse([], [_bm25("b-0"), _bm25("b-1")])
        assert len(result) == 2
        assert all(r.dense_rank is None for r in result)

    def test_empty_bm25_returns_dense_only_results(self):
        ranker = RRFRanker(_cfg())
        result = ranker.fuse([_dense("d-0"), _dense("d-1")], [])
        assert len(result) == 2
        assert all(r.bm25_rank is None for r in result)


# ===========================================================================
# RRFRanker.fuse — source attribution
# ===========================================================================

class TestSourceAttribution:

    def test_dense_rank_populated_for_dense_hits(self):
        ranker = RRFRanker(_cfg())
        result = ranker.fuse([_dense("id")], [])
        assert result[0].dense_rank == 1

    def test_bm25_rank_populated_for_bm25_hits(self):
        ranker = RRFRanker(_cfg())
        result = ranker.fuse([], [_bm25("id")])
        assert result[0].bm25_rank == 1

    def test_shared_chunk_has_both_ranks(self):
        ranker = RRFRanker(_cfg())
        result = ranker.fuse([_dense("shared")], [_bm25("shared")])
        item = result[0]
        assert item.dense_rank == 1
        assert item.bm25_rank == 1

    def test_dense_only_chunk_has_no_bm25_rank(self):
        ranker = RRFRanker(_cfg())
        result = ranker.fuse([_dense("d-only"), _dense("shared")], [_bm25("shared")])
        dense_only = next(r for r in result if r.chunk_id == "d-only")
        assert dense_only.bm25_rank is None

    def test_text_taken_from_dense_when_available(self):
        ranker = RRFRanker(_cfg())
        result = ranker.fuse([_dense("id", text="Dense text")], [])
        assert result[0].text == "Dense text"

    def test_text_falls_back_to_bm25_when_dense_has_none(self):
        ranker = RRFRanker(_cfg())
        dense_hit = DenseResult(chunk_id="id", score=0.5, payload={}, text="")
        bm25_hit = _bm25("id", text="BM25 text")
        result = ranker.fuse([dense_hit], [bm25_hit])
        assert result[0].text == "BM25 text"
