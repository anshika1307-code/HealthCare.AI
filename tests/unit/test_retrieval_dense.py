"""
tests/unit/test_retrieval_dense.py
------------------------------------
Unit tests for src/retrieval/dense_retriever.py

Coverage
--------
DenseResult        — text populated from payload["text"] in __post_init__
DenseRetriever._build_filter  — string/bool conditions, disallowed keys skipped, empty → None
DenseRetriever.search         — maps hits to DenseResult, passes correct params
DenseRetriever.get_by_ids     — empty list short-circuit, maps retrieve results
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from configs.retrieval import DenseConfig
from src.retrieval.dense_retriever import DenseResult, DenseRetriever


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cfg(**overrides) -> DenseConfig:
    base = dict(
        collection_name="healthcare_chunks",
        top_k=5,
        distance_metric="cosine",
        enable_metadata_filter=True,
        filter_fields=["document_id", "doc_type", "safety_flag"],
        score_threshold=None,
    )
    base.update(overrides)
    return DenseConfig(**base)


def _mock_hit(chunk_id: str = "id-0", score: float = 0.9, payload: dict = None) -> MagicMock:
    """Minimal mock of a Qdrant ScoredPoint."""
    hit = MagicMock()
    hit.id = chunk_id
    hit.score = score
    hit.payload = payload or {"text": "Sample text.", "document_id": "fda"}
    return hit


def _mock_qp_response(hits: list) -> MagicMock:
    """Wrap a list of hits in the query_points response shape (.points)."""
    resp = MagicMock()
    resp.points = hits
    return resp


@pytest.fixture
def mock_client() -> MagicMock:
    client = MagicMock()
    client.query_points = AsyncMock(return_value=_mock_qp_response([]))
    client.retrieve = AsyncMock(return_value=[])
    return client


@pytest.fixture
def retriever(mock_client) -> DenseRetriever:
    return DenseRetriever(mock_client, _cfg())


# ===========================================================================
# DenseResult
# ===========================================================================

class TestDenseResult:

    def test_text_populated_from_payload_when_empty(self):
        """__post_init__ copies payload['text'] into .text when text=''. """
        result = DenseResult(
            chunk_id="id",
            score=0.8,
            payload={"text": "Metformin reduces HbA1c."},
        )
        assert result.text == "Metformin reduces HbA1c."

    def test_explicit_text_not_overwritten(self):
        """If text is already set, payload['text'] should not overwrite it."""
        result = DenseResult(
            chunk_id="id",
            score=0.8,
            payload={"text": "From payload."},
            text="Already set.",
        )
        assert result.text == "Already set."

    def test_no_text_in_payload_leaves_text_empty(self):
        result = DenseResult(chunk_id="id", score=0.5, payload={})
        assert result.text == ""


# ===========================================================================
# DenseRetriever._build_filter
# ===========================================================================

class TestBuildFilter:

    def test_string_condition_creates_field_condition(self, retriever):
        f = retriever._build_filter({"document_id": "jnc8"})
        assert f is not None
        assert len(f.must) == 1
        assert f.must[0].key == "document_id"

    def test_bool_condition_creates_field_condition(self, retriever):
        f = retriever._build_filter({"safety_flag": True})
        assert f is not None
        assert f.must[0].key == "safety_flag"

    def test_disallowed_key_is_skipped(self, retriever):
        """Keys not in filter_fields must be ignored (safety guard)."""
        f = retriever._build_filter({"unknown_field": "value"})
        assert f is None  # no valid conditions → None

    def test_multiple_valid_conditions(self, retriever):
        f = retriever._build_filter({"document_id": "ada_s6", "doc_type": "ada"})
        assert len(f.must) == 2

    def test_empty_filters_dict_returns_none(self, retriever):
        f = retriever._build_filter({})
        assert f is None

    def test_mixed_valid_and_invalid_keys(self, retriever):
        """Only valid keys should appear in the filter."""
        f = retriever._build_filter({"document_id": "fda", "bad_key": "x"})
        assert len(f.must) == 1
        assert f.must[0].key == "document_id"


# ===========================================================================
# DenseRetriever.search
# ===========================================================================

class TestSearch:

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_hits(self, retriever, mock_client):
        mock_client.query_points.return_value = _mock_qp_response([])
        results = await retriever.search([0.1, 0.2, 0.3])
        assert results == []

    @pytest.mark.asyncio
    async def test_maps_hits_to_dense_results(self, retriever, mock_client):
        mock_client.query_points.return_value = _mock_qp_response([_mock_hit("id-1", 0.85)])
        results = await retriever.search([0.1])
        assert len(results) == 1
        assert isinstance(results[0], DenseResult)

    @pytest.mark.asyncio
    async def test_chunk_id_and_score_preserved(self, retriever, mock_client):
        mock_client.query_points.return_value = _mock_qp_response([_mock_hit("chunk-abc", 0.75)])
        results = await retriever.search([0.1])
        assert results[0].chunk_id == "chunk-abc"
        assert results[0].score == pytest.approx(0.75)

    @pytest.mark.asyncio
    async def test_passes_collection_name_to_client(self, retriever, mock_client):
        await retriever.search([0.1])
        _, kwargs = mock_client.query_points.call_args
        assert kwargs["collection_name"] == "healthcare_chunks"

    @pytest.mark.asyncio
    async def test_passes_top_k_to_client(self, retriever, mock_client):
        await retriever.search([0.1], top_k=10)
        _, kwargs = mock_client.query_points.call_args
        assert kwargs["limit"] == 10

    @pytest.mark.asyncio
    async def test_passes_config_top_k_by_default(self, retriever, mock_client):
        await retriever.search([0.1])
        _, kwargs = mock_client.query_points.call_args
        assert kwargs["limit"] == 5

    @pytest.mark.asyncio
    async def test_passes_filter_when_provided(self, retriever, mock_client):
        await retriever.search([0.1], filters={"document_id": "jnc8"})
        _, kwargs = mock_client.query_points.call_args
        assert kwargs["query_filter"] is not None

    @pytest.mark.asyncio
    async def test_no_filter_when_none_passed(self, retriever, mock_client):
        await retriever.search([0.1], filters=None)
        _, kwargs = mock_client.query_points.call_args
        assert kwargs["query_filter"] is None

    @pytest.mark.asyncio
    async def test_propagates_qdrant_exception(self, retriever, mock_client):
        mock_client.query_points.side_effect = RuntimeError("Qdrant down")
        with pytest.raises(RuntimeError, match="Qdrant down"):
            await retriever.search([0.1])


# ===========================================================================
# DenseRetriever.get_by_ids
# ===========================================================================

class TestGetByIds:

    @pytest.mark.asyncio
    async def test_empty_ids_returns_empty_list(self, retriever, mock_client):
        result = await retriever.get_by_ids([])
        assert result == []
        mock_client.retrieve.assert_not_called()

    @pytest.mark.asyncio
    async def test_maps_retrieved_points_to_dense_results(self, retriever, mock_client):
        point = MagicMock()
        point.id = "p-1"
        point.payload = {"text": "Chunk text.", "document_id": "fda"}
        mock_client.retrieve.return_value = [point]

        results = await retriever.get_by_ids(["p-1"])
        assert len(results) == 1
        assert results[0].chunk_id == "p-1"

    @pytest.mark.asyncio
    async def test_score_is_zero_on_direct_fetch(self, retriever, mock_client):
        """get_by_ids has no score — score=0.0 is the sentinel value."""
        point = MagicMock()
        point.id = "p-1"
        point.payload = {"text": "text"}
        mock_client.retrieve.return_value = [point]

        results = await retriever.get_by_ids(["p-1"])
        assert results[0].score == 0.0
