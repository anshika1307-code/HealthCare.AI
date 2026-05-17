"""
tests/unit/test_embedding_indexer.py
--------------------------------------
Unit tests for src/embedding/indexer.py

Coverage
--------
QdrantIndexer._build_payload — all 15 payload fields, type coercion, fallbacks
QdrantIndexer.upsert         — success, batching, failure handling, edge cases
"""

import pytest
from unittest.mock import MagicMock, call

from embedding.base import IndexableChunk
from embedding.indexer import QdrantIndexer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _chunk(
    chunk_id: str = "test-uuid-0",
    text: str = "Metformin 500 mg twice daily.",
    **meta_overrides,
) -> IndexableChunk:
    """Build an IndexableChunk with fully-populated metadata for testing."""
    meta = {
        "document_id":             "metformin_fda_label",
        "document_name":           "Metformin FDA Label",
        "doc_type":                "fda",
        "page_number":             2,
        "section_name":            "DOSAGE AND ADMINISTRATION",
        "section_number":          None,
        "is_table":                False,
        "table_number":            None,
        "evidence_grade":          None,
        "recommendation_number":   None,
        "recommendation_strength": None,
        "safety_flag":             False,
        "chunk_index":             0,
        "char_count":              29,
    }
    meta.update(meta_overrides)
    return IndexableChunk(chunk_id=chunk_id, text=text, metadata=meta)


def _vec(dims: int = 4) -> list[float]:
    return [0.1] * dims


@pytest.fixture
def mock_client() -> MagicMock:
    client = MagicMock()
    client.upsert.return_value = None
    return client


@pytest.fixture
def indexer(mock_client) -> QdrantIndexer:
    return QdrantIndexer(mock_client, "healthcare_chunks")


# ===========================================================================
# _build_payload
# ===========================================================================

class TestBuildPayload:
    """Verify the 15-field Qdrant point payload is constructed correctly."""

    EXPECTED_KEYS = {
        "text", "document_id", "document_name", "doc_type",
        "page_number", "section_name", "section_number",
        "is_table", "table_number", "evidence_grade",
        "recommendation_strength", "recommendation_number",
        "safety_flag", "chunk_index", "char_count",
    }

    def test_all_required_keys_present(self, indexer):
        payload = indexer._build_payload(_chunk())
        assert self.EXPECTED_KEYS.issubset(payload.keys())

    def test_text_stored_in_payload(self, indexer):
        """text field enables reranker to fetch full chunk without re-embedding."""
        chunk = _chunk(text="HbA1c should be below 7%.")
        assert indexer._build_payload(chunk)["text"] == "HbA1c should be below 7%."

    def test_document_id_and_name(self, indexer):
        payload = indexer._build_payload(_chunk())
        assert payload["document_id"] == "metformin_fda_label"
        assert payload["document_name"] == "Metformin FDA Label"

    def test_doc_type_from_metadata(self, indexer):
        assert indexer._build_payload(_chunk(doc_type="ada"))["doc_type"] == "ada"

    def test_doc_type_falls_back_to_chunk_property(self, indexer):
        """When doc_type absent from metadata, IndexableChunk.doc_type is used."""
        chunk = IndexableChunk("id", "text", {"doc_type": "jnc"})
        assert indexer._build_payload(chunk)["doc_type"] == "jnc"

    def test_is_table_coerced_to_bool(self, indexer):
        assert indexer._build_payload(_chunk(is_table=1))["is_table"] is True
        assert indexer._build_payload(_chunk(is_table=0))["is_table"] is False

    def test_safety_flag_coerced_to_bool(self, indexer):
        assert indexer._build_payload(_chunk(safety_flag=1))["safety_flag"] is True
        assert indexer._build_payload(_chunk(safety_flag=0))["safety_flag"] is False

    def test_optional_fields_are_none_when_absent(self, indexer):
        """Missing optional metadata keys must be stored as None, not raise."""
        chunk = IndexableChunk("id", "text", {})
        payload = indexer._build_payload(chunk)
        assert payload["section_name"] is None
        assert payload["evidence_grade"] is None
        assert payload["recommendation_number"] is None
        assert payload["table_number"] is None

    def test_char_count_defaults_to_text_length(self, indexer):
        """When char_count missing from metadata, len(text) is used."""
        chunk = IndexableChunk("id", "hello", {})
        assert indexer._build_payload(chunk)["char_count"] == 5

    def test_char_count_uses_metadata_value_when_present(self, indexer):
        assert indexer._build_payload(_chunk(char_count=99))["char_count"] == 99

    def test_ada_evidence_grade_propagated(self, indexer):
        payload = indexer._build_payload(_chunk(doc_type="ada", evidence_grade="A"))
        assert payload["evidence_grade"] == "A"

    def test_jnc_recommendation_fields_propagated(self, indexer):
        chunk = _chunk(
            doc_type="jnc",
            recommendation_number=5,
            recommendation_strength="Strong",
            evidence_grade="A",
        )
        payload = indexer._build_payload(chunk)
        assert payload["recommendation_number"] == 5
        assert payload["recommendation_strength"] == "Strong"
        assert payload["evidence_grade"] == "A"

    def test_table_chunk_payload(self, indexer):
        chunk = _chunk(is_table=True, table_number=3)
        payload = indexer._build_payload(chunk)
        assert payload["is_table"] is True
        assert payload["table_number"] == 3

    def test_safety_chunk_payload(self, indexer):
        payload = indexer._build_payload(_chunk(safety_flag=True))
        assert payload["safety_flag"] is True


# ===========================================================================
# upsert
# ===========================================================================

class TestUpsert:

    # --- Edge cases ---

    def test_empty_input_returns_zero_and_no_failures(self, indexer, mock_client):
        success, failed = indexer.upsert([], [])
        assert success == 0
        assert failed == []
        mock_client.upsert.assert_not_called()

    def test_mismatched_lengths_raise_value_error(self, indexer):
        with pytest.raises(ValueError, match="same length"):
            indexer.upsert([_chunk()], [_vec(), _vec()])  # 1 chunk, 2 vectors

    # --- Normal success path ---

    def test_single_chunk_upserted_returns_success_count_1(self, indexer, mock_client):
        success, failed = indexer.upsert([_chunk(chunk_id="abc")], [_vec()])
        assert success == 1
        assert failed == []

    def test_upsert_called_with_correct_collection_name(self, indexer, mock_client):
        indexer.upsert([_chunk()], [_vec()])
        _, kwargs = mock_client.upsert.call_args
        assert kwargs["collection_name"] == "healthcare_chunks"

    def test_upsert_called_with_wait_true(self, indexer, mock_client):
        """wait=True ensures Qdrant acknowledges the write before returning."""
        indexer.upsert([_chunk()], [_vec()])
        _, kwargs = mock_client.upsert.call_args
        assert kwargs["wait"] is True

    def test_point_has_correct_id_and_vector(self, indexer, mock_client):
        vector = [0.1, 0.2, 0.3, 0.4]
        indexer.upsert([_chunk(chunk_id="my-id")], [vector])
        _, kwargs = mock_client.upsert.call_args
        point = kwargs["points"][0]
        assert point.id == "my-id"
        assert point.vector == vector

    # --- Batching ---

    def test_splits_into_batches(self, indexer, mock_client):
        """5 chunks with batch_size=2 → 3 upsert calls (2 + 2 + 1)."""
        chunks = [_chunk(chunk_id=f"id-{i}") for i in range(5)]
        vectors = [_vec() for _ in range(5)]
        indexer.upsert(chunks, vectors, batch_size=2)
        assert mock_client.upsert.call_count == 3

    def test_total_success_count_across_batches(self, indexer, mock_client):
        chunks = [_chunk(chunk_id=f"id-{i}") for i in range(5)]
        vectors = [_vec() for _ in range(5)]
        success, failed = indexer.upsert(chunks, vectors, batch_size=2)
        assert success == 5
        assert failed == []

    def test_batch_size_one_makes_one_call_per_chunk(self, indexer, mock_client):
        n = 4
        chunks = [_chunk(chunk_id=f"id-{i}") for i in range(n)]
        vectors = [_vec() for _ in range(n)]
        indexer.upsert(chunks, vectors, batch_size=1)
        assert mock_client.upsert.call_count == n

    # --- Failure paths ---

    def test_failed_batch_adds_chunk_ids_to_failed_list(self, indexer, mock_client):
        mock_client.upsert.side_effect = Exception("connection refused")
        success, failed = indexer.upsert([_chunk(chunk_id="fail-id")], [_vec()])
        assert success == 0
        assert "fail-id" in failed

    def test_partial_failure_tracked_per_batch(self, indexer, mock_client):
        """First batch succeeds, second fails → partial success_count."""
        mock_client.upsert.side_effect = [None, Exception("timeout")]
        chunks = [_chunk(chunk_id=f"id-{i}") for i in range(4)]
        vectors = [_vec() for _ in range(4)]
        success, failed = indexer.upsert(chunks, vectors, batch_size=2)
        assert success == 2
        assert len(failed) == 2

    def test_all_ids_in_failed_on_complete_failure(self, indexer, mock_client):
        mock_client.upsert.side_effect = Exception("down")
        ids = [f"id-{i}" for i in range(3)]
        chunks = [_chunk(chunk_id=cid) for cid in ids]
        vectors = [_vec() for _ in range(3)]
        _, failed = indexer.upsert(chunks, vectors)
        assert set(failed) == set(ids)
