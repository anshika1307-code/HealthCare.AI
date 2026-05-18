"""
tests/unit/test_embedding_base.py
----------------------------------
Unit tests for src/embedding/base.py

Coverage
--------
make_chunk_id      — UUID5 determinism, uniqueness, valid format
IndexableChunk     — property accessors (doc_id, doc_type, safety_flag) and fallbacks
make_indexable     — Chunk → IndexableChunk conversion, ID assignment
Embedder Protocol  — structural isinstance checks
"""

import uuid

import pytest

from embedding.base import (
    Embedder,
    IndexableChunk,
    _UUID5_NAMESPACE,
    make_chunk_id,
    make_indexable,
)
from ingestion.chunker import Chunk


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _chunk(text: str = "Sample text.", **meta_overrides) -> Chunk:
    """Build a minimal Chunk with sensible defaults."""
    meta = {
        "document_id": "metformin_fda_label",
        "document_name": "Metformin FDA Label",
        "doc_type": "fda",
        "page_number": 1,
        "section_name": "DOSAGE",
        "section_number": None,
        "is_table": False,
        "table_number": None,
        "evidence_grade": None,
        "recommendation_number": None,
        "recommendation_strength": None,
        "safety_flag": False,
        "chunk_index": 0,
        "char_count": len(text),
    }
    meta.update(meta_overrides)
    return Chunk(text=text, metadata=meta)


# ===========================================================================
# make_chunk_id
# ===========================================================================


class TestMakeChunkId:
    """UUID5-based deterministic ID generator."""

    def test_same_inputs_produce_same_id(self):
        """Re-ingesting the same doc must produce identical IDs (idempotency)."""
        assert make_chunk_id("doc_a", 0) == make_chunk_id("doc_a", 0)

    def test_different_doc_ids_produce_different_ids(self):
        assert make_chunk_id("doc_a", 0) != make_chunk_id("doc_b", 0)

    def test_different_chunk_indices_produce_different_ids(self):
        assert make_chunk_id("doc_a", 0) != make_chunk_id("doc_a", 1)

    def test_returns_valid_uuid5_string(self):
        result = make_chunk_id("doc_a", 3)
        parsed = uuid.UUID(result)
        assert parsed.version == 5

    def test_matches_expected_uuid5_computation(self):
        """Verify the namespace and key format match the implementation spec."""
        expected = str(uuid.uuid5(_UUID5_NAMESPACE, "metformin_fda_label::7"))
        assert make_chunk_id("metformin_fda_label", 7) == expected

    def test_chunk_index_zero_works(self):
        result = make_chunk_id("doc", 0)
        assert uuid.UUID(result).version == 5

    def test_large_chunk_index_works(self):
        result = make_chunk_id("doc", 99_999)
        assert uuid.UUID(result).version == 5


# ===========================================================================
# IndexableChunk
# ===========================================================================


class TestIndexableChunk:
    """Property accessors and metadata fallback behaviour."""

    def test_doc_id_reads_from_metadata(self):
        ic = IndexableChunk("id", "text", {"document_id": "ada_s6"})
        assert ic.doc_id == "ada_s6"

    def test_doc_type_reads_from_metadata(self):
        ic = IndexableChunk("id", "text", {"doc_type": "ada"})
        assert ic.doc_type == "ada"

    def test_safety_flag_reads_from_metadata(self):
        ic = IndexableChunk("id", "text", {"safety_flag": True})
        assert ic.safety_flag is True

    def test_doc_id_missing_returns_empty_string(self):
        ic = IndexableChunk("id", "text", {})
        assert ic.doc_id == ""

    def test_doc_type_missing_returns_empty_string(self):
        ic = IndexableChunk("id", "text", {})
        assert ic.doc_type == ""

    def test_safety_flag_missing_returns_false(self):
        ic = IndexableChunk("id", "text", {})
        assert ic.safety_flag is False

    def test_safety_flag_truthy_int_coerced_to_bool(self):
        ic = IndexableChunk("id", "text", {"safety_flag": 1})
        assert ic.safety_flag is True
        assert type(ic.safety_flag) is bool

    def test_safety_flag_zero_coerced_to_false(self):
        ic = IndexableChunk("id", "text", {"safety_flag": 0})
        assert ic.safety_flag is False


# ===========================================================================
# make_indexable
# ===========================================================================


class TestMakeIndexable:
    """Conversion of raw Chunk list into IndexableChunk list."""

    def test_empty_input_returns_empty_list(self):
        assert make_indexable([], "doc") == []

    def test_length_preserved(self):
        chunks = [_chunk(), _chunk(chunk_index=1)]
        result = make_indexable(chunks, "doc")
        assert len(result) == 2

    def test_text_preserved(self):
        c = _chunk(text="Metformin 500 mg twice daily.")
        result = make_indexable([c], "doc")
        assert result[0].text == "Metformin 500 mg twice daily."

    def test_metadata_preserved(self):
        c = _chunk(section_name="WARNINGS")
        result = make_indexable([c], "doc")
        assert result[0].metadata["section_name"] == "WARNINGS"

    def test_chunk_id_is_deterministic(self):
        """Same chunk produces same ID on repeated calls."""
        c = _chunk(chunk_index=3)
        r1 = make_indexable([c], "metformin_fda_label")
        r2 = make_indexable([c], "metformin_fda_label")
        assert r1[0].chunk_id == r2[0].chunk_id

    def test_chunk_id_uses_metadata_chunk_index(self):
        """UUID5 is keyed on metadata chunk_index, not the list position."""
        c = _chunk(chunk_index=5)
        result = make_indexable([c], "metformin_fda_label")
        expected = make_chunk_id("metformin_fda_label", 5)
        assert result[0].chunk_id == expected

    def test_falls_back_to_enumerate_index_when_missing(self):
        """Without chunk_index in metadata, list position is used as fallback."""
        c0 = Chunk(text="a", metadata={})
        c1 = Chunk(text="b", metadata={})
        result = make_indexable([c0, c1], "doc")
        # Both have different positions → different IDs
        assert result[0].chunk_id != result[1].chunk_id

    def test_all_chunk_ids_are_valid_uuids(self):
        chunks = [_chunk(chunk_index=i) for i in range(4)]
        for ic in make_indexable(chunks, "doc"):
            uuid.UUID(ic.chunk_id)  # must not raise


# ===========================================================================
# Embedder Protocol
# ===========================================================================


class TestEmbedderProtocol:
    """Structural isinstance checks — no ABC inheritance required."""

    def test_fully_compliant_object_satisfies_protocol(self):
        class Good:
            def embed_batch(self, texts: list[str]) -> list[list[float]]:
                return [[0.0]] * len(texts)

            @property
            def dimensions(self) -> int:
                return 1536

            @property
            def model_name(self) -> str:
                return "mock"

        assert isinstance(Good(), Embedder)

    def test_missing_embed_batch_fails_protocol(self):
        class NoEmbed:
            @property
            def dimensions(self):
                return 1536

            @property
            def model_name(self):
                return "mock"

        assert not isinstance(NoEmbed(), Embedder)

    def test_missing_dimensions_fails_protocol(self):
        class NoDims:
            def embed_batch(self, texts):
                return []

            @property
            def model_name(self):
                return "mock"

        assert not isinstance(NoDims(), Embedder)

    def test_plain_object_fails_protocol(self):
        assert not isinstance(object(), Embedder)
