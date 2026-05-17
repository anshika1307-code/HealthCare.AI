"""
tests/unit/test_serving_schemas.py
------------------------------------
Unit tests for src/serving/schemas.py (Pydantic models).

Covers validation, defaults, rejection of invalid input, and round-trip
JSON serialisation for all three models: QueryRequest, SourceChunk,
QueryResponse.
"""
import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[2] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import pytest
from pydantic import ValidationError

from serving.schemas import QueryRequest, QueryResponse, SourceChunk


# ===========================================================================
# QueryRequest
# ===========================================================================

class TestQueryRequest:

    def test_valid_minimal(self):
        req = QueryRequest(query="What is metformin?")
        assert req.query == "What is metformin?"

    def test_filters_default_none(self):
        req = QueryRequest(query="test query")
        assert req.filters is None

    def test_filters_accepts_dict(self):
        req = QueryRequest(query="q", filters={"doc_type": "fda"})
        assert req.filters == {"doc_type": "fda"}

    def test_filters_accepts_bool_value(self):
        req = QueryRequest(query="q", filters={"safety_flag": True})
        assert req.filters["safety_flag"] is True

    def test_query_too_short_raises(self):
        with pytest.raises(ValidationError):
            QueryRequest(query="")

    def test_query_too_long_raises(self):
        with pytest.raises(ValidationError):
            QueryRequest(query="x" * 2001)

    def test_query_at_max_length_accepted(self):
        req = QueryRequest(query="x" * 2000)
        assert len(req.query) == 2000

    def test_query_missing_raises(self):
        with pytest.raises(ValidationError):
            QueryRequest()  # type: ignore[call-arg]

    def test_query_stripped_preserved(self):
        # Pydantic does not auto-strip; leading/trailing spaces kept
        req = QueryRequest(query=" test ")
        assert req.query == " test "

    def test_json_roundtrip(self):
        req = QueryRequest(query="HbA1c target?", filters={"doc_type": "ada"})
        restored = QueryRequest.model_validate_json(req.model_dump_json())
        assert restored.query == req.query
        assert restored.filters == req.filters


# ===========================================================================
# SourceChunk
# ===========================================================================

class TestSourceChunk:

    def _minimal(self, **kw):
        defaults = dict(
            chunk_id="abc-123",
            document_id="fda_metformin",
            reranker_score=0.85,
        )
        defaults.update(kw)
        return SourceChunk(**defaults)

    def test_minimal_required_fields(self):
        chunk = self._minimal()
        assert chunk.chunk_id == "abc-123"
        assert chunk.document_id == "fda_metformin"
        assert chunk.reranker_score == pytest.approx(0.85)

    def test_optional_doc_type_defaults_empty(self):
        assert self._minimal().doc_type == ""

    def test_optional_section_name_defaults_empty(self):
        assert self._minimal().section_name == ""

    def test_optional_text_defaults_empty(self):
        assert self._minimal().text == ""

    def test_explicit_doc_type(self):
        chunk = self._minimal(doc_type="fda")
        assert chunk.doc_type == "fda"

    def test_explicit_section_name(self):
        chunk = self._minimal(section_name="Contraindications")
        assert chunk.section_name == "Contraindications"

    def test_explicit_text(self):
        chunk = self._minimal(text="Metformin is contraindicated in renal impairment.")
        assert "renal" in chunk.text

    def test_none_section_name_raises(self):
        with pytest.raises(ValidationError):
            self._minimal(section_name=None)  # type: ignore[arg-type]

    def test_none_doc_type_raises(self):
        with pytest.raises(ValidationError):
            self._minimal(doc_type=None)  # type: ignore[arg-type]

    def test_reranker_score_zero(self):
        chunk = self._minimal(reranker_score=0.0)
        assert chunk.reranker_score == pytest.approx(0.0)

    def test_reranker_score_one(self):
        chunk = self._minimal(reranker_score=1.0)
        assert chunk.reranker_score == pytest.approx(1.0)

    def test_missing_chunk_id_raises(self):
        with pytest.raises(ValidationError):
            SourceChunk(document_id="x", reranker_score=0.5)  # type: ignore[call-arg]

    def test_missing_document_id_raises(self):
        with pytest.raises(ValidationError):
            SourceChunk(chunk_id="x", reranker_score=0.5)  # type: ignore[call-arg]

    def test_json_roundtrip(self):
        chunk = self._minimal(doc_type="ada", section_name="§9.1", text="context text")
        restored = SourceChunk.model_validate_json(chunk.model_dump_json())
        assert restored.doc_type == "ada"
        assert restored.section_name == "§9.1"
        assert restored.text == "context text"


# ===========================================================================
# QueryResponse
# ===========================================================================

class TestQueryResponse:

    def _chunk(self, idx: int = 0) -> SourceChunk:
        return SourceChunk(
            chunk_id=f"id-{idx}",
            document_id="fda",
            reranker_score=0.9 - idx * 0.1,
        )

    def test_minimal_valid(self):
        resp = QueryResponse(
            answer="Metformin is first-line therapy.",
            sources=[],
            confidence_score=0.88,
            low_confidence=False,
        )
        assert resp.answer == "Metformin is first-line therapy."
        assert resp.sources == []
        assert resp.confidence_score == pytest.approx(0.88)
        assert resp.low_confidence is False

    def test_warning_message_defaults_empty(self):
        resp = QueryResponse(
            answer="a", sources=[], confidence_score=0.5, low_confidence=False
        )
        assert resp.warning_message == ""

    def test_filters_applied_defaults_empty_dict(self):
        resp = QueryResponse(
            answer="a", sources=[], confidence_score=0.5, low_confidence=False
        )
        assert resp.filters_applied == {}

    def test_sources_list_of_chunks(self):
        resp = QueryResponse(
            answer="answer",
            sources=[self._chunk(0), self._chunk(1)],
            confidence_score=0.7,
            low_confidence=False,
        )
        assert len(resp.sources) == 2
        assert resp.sources[0].chunk_id == "id-0"

    def test_low_confidence_true(self):
        resp = QueryResponse(
            answer="uncertain",
            sources=[],
            confidence_score=0.25,
            low_confidence=True,
            warning_message="Low confidence: verify source.",
        )
        assert resp.low_confidence is True
        assert "Low confidence" in resp.warning_message

    def test_explicit_filters_applied(self):
        resp = QueryResponse(
            answer="a",
            sources=[],
            confidence_score=0.9,
            low_confidence=False,
            filters_applied={"doc_type": "fda"},
        )
        assert resp.filters_applied["doc_type"] == "fda"

    def test_missing_answer_raises(self):
        with pytest.raises(ValidationError):
            QueryResponse(sources=[], confidence_score=0.9, low_confidence=False)  # type: ignore[call-arg]

    def test_missing_confidence_score_raises(self):
        with pytest.raises(ValidationError):
            QueryResponse(answer="a", sources=[], low_confidence=False)  # type: ignore[call-arg]

    def test_json_roundtrip(self):
        resp = QueryResponse(
            answer="target HbA1c < 7%",
            sources=[self._chunk(0)],
            confidence_score=0.92,
            low_confidence=False,
            warning_message="",
            filters_applied={"doc_type": "ada"},
        )
        restored = QueryResponse.model_validate_json(resp.model_dump_json())
        assert restored.answer == resp.answer
        assert len(restored.sources) == 1
        assert restored.filters_applied == {"doc_type": "ada"}
