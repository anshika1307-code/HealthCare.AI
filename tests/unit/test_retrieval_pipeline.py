"""
tests/unit/test_retrieval_pipeline.py
---------------------------------------
Unit tests for src/retrieval/pipeline.py

All heavy dependencies (DenseRetriever, BM25Retriever, CrossEncoderReranker)
are mocked so no network or model-loading occurs.

Coverage
--------
RetrievalPipeline.retrieve — calls each stage in the correct order,
                             passes filters, handles missing chunk texts,
                             returns RetrievalResult from ConfidenceScorer
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from retrieval.bm25_retriever import BM25Result
from retrieval.confidence import ConfidenceScorer, RetrievalResult
from retrieval.dense_retriever import DenseResult
from retrieval.pipeline import RetrievalPipeline
from retrieval.reranker import CrossEncoderReranker, RankedResult
from retrieval.rrf_ranker import FusedResult, RRFRanker


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _dense(chunk_id: str, text: str = "dense text") -> DenseResult:
    return DenseResult(chunk_id=chunk_id, score=0.9, payload={"text": text}, text=text)


def _bm25(chunk_id: str, text: str = "bm25 text") -> BM25Result:
    return BM25Result(chunk_id=chunk_id, score=10.0, text=text)


def _fused(chunk_id: str, text: str = "fused text") -> FusedResult:
    return FusedResult(chunk_id=chunk_id, rrf_score=0.5, text=text)


def _ranked(chunk_id: str = "id", score: float = 0.8) -> RankedResult:
    return RankedResult(
        chunk_id=chunk_id,
        reranker_score=score,
        text="text",
        payload={"document_id": "fda", "section_name": "SEC", "safety_flag": False},
    )


@pytest.fixture
def mock_dense():
    m = MagicMock()
    m.search = AsyncMock(return_value=[_dense("id-1"), _dense("id-2")])
    m.get_by_ids = AsyncMock(return_value=[])
    return m


@pytest.fixture
def mock_bm25():
    m = MagicMock()
    m.search.return_value = [_bm25("id-1"), _bm25("id-3")]
    return m


@pytest.fixture
def mock_rrf():
    m = MagicMock()
    m.fuse.return_value = [_fused("id-1", "text 1"), _fused("id-2", "text 2")]
    return m


@pytest.fixture
def mock_reranker():
    m = MagicMock()
    m.rerank = AsyncMock(return_value=[_ranked("id-1")])
    return m


@pytest.fixture
def mock_confidence():
    m = MagicMock()
    m.score.return_value = RetrievalResult(
        query="test query",
        chunks=[_ranked("id-1")],
        confidence_score=0.8,
        low_confidence=False,
    )
    return m


@pytest.fixture
def pipeline(mock_dense, mock_bm25, mock_reranker, mock_rrf, mock_confidence):
    return RetrievalPipeline(
        dense_retriever=mock_dense,
        bm25_retriever=mock_bm25,
        reranker=mock_reranker,
        rrf_ranker=mock_rrf,
        confidence_scorer=mock_confidence,
    )


# ===========================================================================
# RetrievalPipeline.retrieve
# ===========================================================================


class TestRetrieve:
    @pytest.mark.asyncio
    async def test_returns_retrieval_result(self, pipeline):
        result = await pipeline.retrieve("test query", [0.1, 0.2])
        assert isinstance(result, RetrievalResult)

    @pytest.mark.asyncio
    async def test_dense_search_called_with_query_vector(self, pipeline, mock_dense):
        vector = [0.1, 0.2, 0.3]
        await pipeline.retrieve("query", vector)
        mock_dense.search.assert_called_once()
        call_args = mock_dense.search.call_args
        assert call_args[0][0] == vector  # positional arg

    @pytest.mark.asyncio
    async def test_bm25_search_called_with_query_text(self, pipeline, mock_bm25):
        await pipeline.retrieve("metformin dosing", [0.1])
        mock_bm25.search.assert_called_once()
        call_args = mock_bm25.search.call_args
        assert call_args[0][0] == "metformin dosing"

    @pytest.mark.asyncio
    async def test_rrf_fuse_called_with_both_results(
        self, pipeline, mock_dense, mock_bm25, mock_rrf
    ):
        await pipeline.retrieve("query", [0.1])
        mock_rrf.fuse.assert_called_once()
        args = mock_rrf.fuse.call_args[0]
        # First arg: dense results, second arg: bm25 results
        assert len(args) == 2

    @pytest.mark.asyncio
    async def test_reranker_called_with_fused_pool(self, pipeline, mock_reranker, mock_rrf):
        fused_pool = [_fused(f"id-{i}", f"text {i}") for i in range(3)]
        mock_rrf.fuse.return_value = fused_pool
        await pipeline.retrieve("query", [0.1])
        mock_reranker.rerank.assert_called_once()
        args = mock_reranker.rerank.call_args[0]
        assert args[0] == "query"  # query text passed through
        assert args[1] == fused_pool  # fused pool passed to reranker

    @pytest.mark.asyncio
    async def test_confidence_scorer_called_with_ranked_results(
        self, pipeline, mock_confidence, mock_reranker
    ):
        ranked = [_ranked("r-1")]
        mock_reranker.rerank.return_value = ranked
        await pipeline.retrieve("query", [0.1])
        mock_confidence.score.assert_called_once()
        args = mock_confidence.score.call_args[0]
        assert args[1] == ranked

    @pytest.mark.asyncio
    async def test_filter_passed_to_dense_search(self, pipeline, mock_dense):
        filters = {"document_id": "jnc8"}
        await pipeline.retrieve("query", [0.1], filters=filters)
        _, kwargs = mock_dense.search.call_args
        assert kwargs.get("filters") == filters

    @pytest.mark.asyncio
    async def test_filter_doc_id_passed_to_bm25(self, pipeline, mock_bm25):
        filters = {"document_id": "jnc8"}
        await pipeline.retrieve("query", [0.1], filters=filters)
        _, kwargs = mock_bm25.search.call_args
        assert kwargs.get("filter_doc_id") == "jnc8"

    @pytest.mark.asyncio
    async def test_get_by_ids_called_for_missing_texts(self, pipeline, mock_dense, mock_rrf):
        """Fused chunks with empty text must trigger a Qdrant batch fetch."""
        mock_rrf.fuse.return_value = [
            FusedResult(chunk_id="needs-text", rrf_score=0.5, text=""),
        ]
        await pipeline.retrieve("query", [0.1])
        mock_dense.get_by_ids.assert_called_once_with(["needs-text"])

    @pytest.mark.asyncio
    async def test_chunks_with_no_text_dropped_before_reranking(
        self, pipeline, mock_dense, mock_rrf, mock_reranker
    ):
        """After fetch attempt, still-empty chunks must be dropped."""
        mock_rrf.fuse.return_value = [
            FusedResult(chunk_id="empty-chunk", rrf_score=0.5, text=""),
        ]
        mock_dense.get_by_ids.return_value = []  # fetch returns nothing
        await pipeline.retrieve("query", [0.1])
        # Reranker called with an empty list (no text chunks to rank)
        args = mock_reranker.rerank.call_args[0]
        assert args[1] == []
