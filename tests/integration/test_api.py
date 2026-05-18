"""
tests/integration/test_api.py
-------------------------------
Integration tests for src/serving/api.py using FastAPI's TestClient.

Strategy
--------
The real lifespan loads Qdrant Cloud + cross-encoder model (~90 s).
We patch app.router.lifespan_context with a no-op before entering
the TestClient context, preventing all heavy initialisation.
app.state is populated manually with mocked graph + Qdrant client.

All tests share the `client` fixture (function-scoped — resets state
each test).  Tests that need different graph behaviour set app.state
directly before making the request.

Coverage
--------
GET  /health   — 200 + body, 503 when Qdrant unreachable
POST /query    — happy path shape, filters forwarded, long query OK
               — low-confidence flag + warning message
               — None fields coerced to "" (regression for pydantic None bug)
               — empty/missing query → 422
               — graph raises → 500
               — retrieval_result missing → 500
               — empty sources list OK
               — multi-source response
               — answer is empty string
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

_ROOT = Path(__file__).resolve().parents[2]
for p in (_ROOT / "src", _ROOT):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

try:
    from dotenv import load_dotenv

    load_dotenv(_ROOT / ".env")
except ImportError:
    pass

from retrieval.confidence import RetrievalResult
from retrieval.reranker import RankedResult
from serving.api import app


# ---------------------------------------------------------------------------
# No-op lifespan — replaces the real one in every test
# ---------------------------------------------------------------------------


@asynccontextmanager
async def _noop_lifespan(application):
    """Prevents model loading and Qdrant connection during tests."""
    yield


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ranked(chunk_id: str = "c1", score: float = 0.9) -> RankedResult:
    return RankedResult(
        chunk_id=chunk_id,
        reranker_score=score,
        text="Metformin is first-line therapy for type 2 diabetes.",
        payload={
            "document_id": "ada_sec9",
            "doc_type": "ada",
            "section_name": "§9.1",
            "safety_flag": False,
        },
    )


def _retrieval_result(score: float = 0.88, low: bool = False) -> RetrievalResult:
    return RetrievalResult(
        query="test query",
        chunks=[_ranked()],
        confidence_score=score,
        low_confidence=low,
        warning_message="Low confidence." if low else "",
    )


def _make_graph(answer: str = "Clinical answer.", retrieval_result=None, raise_exc=None):
    graph = MagicMock()
    rr = retrieval_result if retrieval_result is not None else _retrieval_result()
    if raise_exc:
        graph.ainvoke = AsyncMock(side_effect=raise_exc)
    else:
        graph.ainvoke = AsyncMock(
            return_value={
                "query": "test query",
                "query_vector": [0.1, 0.2],
                "retrieval_result": rr,
                "answer": answer,
                "embed_ms": 10.0,
                "retrieve_ms": 150.0,
                "generate_ms": 200.0,
            }
        )
    return graph


def _make_qdrant(reachable: bool = True):
    client = MagicMock()
    if reachable:
        client.get_collections = AsyncMock(return_value=MagicMock())
    else:
        client.get_collections = AsyncMock(side_effect=Exception("connection refused"))
    return client


def _make_metrics():
    m = MagicMock()
    m.record = AsyncMock()
    m.record_error = AsyncMock()
    m.close = AsyncMock()
    return m


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client():
    """
    TestClient with no-op lifespan and default mocked app.state.
    Function-scoped so state is reset before each test.
    """
    original_lifespan = app.router.lifespan_context
    app.router.lifespan_context = _noop_lifespan
    app.state.graph = _make_graph()
    app.state.qdrant_client = _make_qdrant(reachable=True)
    app.state.metrics = _make_metrics()
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.router.lifespan_context = original_lifespan


# ===========================================================================
# GET /health
# ===========================================================================


class TestHealth:
    def test_returns_200_when_reachable(self, client):
        assert client.get("/health").status_code == 200

    def test_body_status_ok(self, client):
        assert client.get("/health").json()["status"] == "ok"

    def test_body_qdrant_reachable(self, client):
        assert client.get("/health").json()["qdrant"] == "reachable"

    def test_returns_503_when_unreachable(self, client):
        app.state.qdrant_client = _make_qdrant(reachable=False)
        assert client.get("/health").status_code == 503

    def test_503_detail_mentions_qdrant(self, client):
        app.state.qdrant_client = _make_qdrant(reachable=False)
        assert "Qdrant" in client.get("/health").json().get("detail", "")


# ===========================================================================
# POST /query — happy path
# ===========================================================================


class TestQueryHappyPath:
    def test_returns_200(self, client):
        assert client.post("/query", json={"query": "HbA1c target?"}).status_code == 200

    def test_answer_matches_graph_output(self, client):
        assert client.post("/query", json={"query": "q"}).json()["answer"] == "Clinical answer."

    def test_sources_is_list(self, client):
        assert isinstance(client.post("/query", json={"query": "q"}).json()["sources"], list)

    def test_source_has_all_required_fields(self, client):
        src = client.post("/query", json={"query": "q"}).json()["sources"][0]
        for field in (
            "chunk_id",
            "document_id",
            "reranker_score",
            "doc_type",
            "section_name",
            "text",
        ):
            assert field in src

    def test_source_doc_type_populated(self, client):
        assert client.post("/query", json={"query": "q"}).json()["sources"][0]["doc_type"] == "ada"

    def test_source_section_name_populated(self, client):
        assert (
            client.post("/query", json={"query": "q"}).json()["sources"][0]["section_name"]
            == "§9.1"
        )

    def test_source_text_populated(self, client):
        assert (
            "Metformin" in client.post("/query", json={"query": "q"}).json()["sources"][0]["text"]
        )

    def test_confidence_score_is_float(self, client):
        body = client.post("/query", json={"query": "q"}).json()
        assert isinstance(body["confidence_score"], float)

    def test_low_confidence_false_for_high_score(self, client):
        assert client.post("/query", json={"query": "q"}).json()["low_confidence"] is False

    def test_warning_message_present_in_response(self, client):
        assert "warning_message" in client.post("/query", json={"query": "q"}).json()

    def test_content_type_is_json(self, client):
        resp = client.post("/query", json={"query": "q"})
        assert "application/json" in resp.headers.get("content-type", "")

    def test_filters_forwarded_to_graph(self, client):
        graph = _make_graph()
        app.state.graph = graph
        client.post("/query", json={"query": "q", "filters": {"doc_type": "fda"}})
        initial_state = graph.ainvoke.call_args[0][0]
        assert initial_state["filters"] == {"doc_type": "fda"}

    def test_no_filters_sends_none_to_graph(self, client):
        graph = _make_graph()
        app.state.graph = graph
        client.post("/query", json={"query": "q"})
        assert graph.ainvoke.call_args[0][0]["filters"] is None

    def test_query_text_forwarded_to_graph(self, client):
        graph = _make_graph()
        app.state.graph = graph
        client.post("/query", json={"query": "blood pressure threshold"})
        assert graph.ainvoke.call_args[0][0]["query"] == "blood pressure threshold"


# ===========================================================================
# POST /query — low-confidence
# ===========================================================================


class TestQueryLowConfidence:
    def test_low_confidence_flag_true(self, client):
        rr = _retrieval_result(score=0.25, low=True)
        app.state.graph = _make_graph(answer="Uncertain.", retrieval_result=rr)
        assert client.post("/query", json={"query": "q"}).json()["low_confidence"] is True

    def test_confidence_score_below_threshold(self, client):
        rr = _retrieval_result(score=0.25, low=True)
        app.state.graph = _make_graph(retrieval_result=rr)
        assert client.post("/query", json={"query": "q"}).json()["confidence_score"] < 0.4

    def test_warning_message_non_empty_when_low(self, client):
        rr = _retrieval_result(score=0.25, low=True)
        app.state.graph = _make_graph(retrieval_result=rr)
        assert client.post("/query", json={"query": "q"}).json()["warning_message"] != ""


# ===========================================================================
# POST /query — None field coercion (regression guard)
# ===========================================================================


class TestQueryNoneCoercion:
    def test_none_section_name_coerced_to_empty_string(self, client):
        ranked = _ranked()
        ranked.payload["section_name"] = None  # simulate missing/null section from Qdrant
        rr = RetrievalResult(query="q", chunks=[ranked], confidence_score=0.9, low_confidence=False)
        app.state.graph = _make_graph(retrieval_result=rr)
        resp = client.post("/query", json={"query": "q"})
        assert resp.status_code == 200
        assert resp.json()["sources"][0]["section_name"] == ""

    def test_none_text_coerced_to_empty_string(self, client):
        ranked = RankedResult(
            chunk_id="c1",
            reranker_score=0.9,
            text=None,  # type: ignore[arg-type]
            payload={"document_id": "fda", "doc_type": "fda", "safety_flag": False},
        )
        rr = RetrievalResult(query="q", chunks=[ranked], confidence_score=0.9, low_confidence=False)
        app.state.graph = _make_graph(retrieval_result=rr)
        resp = client.post("/query", json={"query": "q"})
        assert resp.status_code == 200
        assert resp.json()["sources"][0]["text"] == ""

    def test_none_doc_type_coerced_to_empty_string(self, client):
        ranked = _ranked()
        ranked.payload["doc_type"] = None
        rr = RetrievalResult(query="q", chunks=[ranked], confidence_score=0.9, low_confidence=False)
        app.state.graph = _make_graph(retrieval_result=rr)
        resp = client.post("/query", json={"query": "q"})
        assert resp.status_code == 200
        assert resp.json()["sources"][0]["doc_type"] == ""


# ===========================================================================
# POST /query — validation errors (422)
# ===========================================================================


class TestQueryValidation:
    def test_empty_query_returns_422(self, client):
        assert client.post("/query", json={"query": ""}).status_code == 422

    def test_missing_query_field_returns_422(self, client):
        assert client.post("/query", json={}).status_code == 422

    def test_query_too_long_returns_422(self, client):
        assert client.post("/query", json={"query": "x" * 2001}).status_code == 422

    def test_query_at_max_length_returns_200(self, client):
        assert client.post("/query", json={"query": "x" * 2000}).status_code == 200

    def test_non_json_body_returns_422(self, client):
        resp = client.post(
            "/query", content=b"not json", headers={"Content-Type": "application/json"}
        )
        assert resp.status_code == 422


# ===========================================================================
# POST /query — error paths (500)
# ===========================================================================


class TestQueryErrors:
    def test_graph_exception_returns_500(self, client):
        app.state.graph = _make_graph(raise_exc=RuntimeError("pipeline exploded"))
        assert client.post("/query", json={"query": "q"}).status_code == 500

    def test_500_detail_mentions_pipeline(self, client):
        app.state.graph = _make_graph(raise_exc=RuntimeError("pipeline exploded"))
        body = client.post("/query", json={"query": "q"}).json()
        assert "pipeline" in body.get("detail", "").lower()

    def test_missing_retrieval_result_returns_500(self, client):
        graph = MagicMock()
        graph.ainvoke = AsyncMock(return_value={"query": "q", "answer": "a"})
        app.state.graph = graph
        assert client.post("/query", json={"query": "q"}).status_code == 500

    def test_missing_retrieval_result_detail_message(self, client):
        graph = MagicMock()
        graph.ainvoke = AsyncMock(return_value={"query": "q", "answer": "a"})
        app.state.graph = graph
        body = client.post("/query", json={"query": "q"}).json()
        assert "Retrieval" in body.get("detail", "")


# ===========================================================================
# POST /query — edge cases
# ===========================================================================


class TestQueryEdgeCases:
    def test_empty_sources_list_returns_200(self, client):
        rr = RetrievalResult(query="q", chunks=[], confidence_score=0.5, low_confidence=False)
        app.state.graph = _make_graph(retrieval_result=rr)
        resp = client.post("/query", json={"query": "q"})
        assert resp.status_code == 200
        assert resp.json()["sources"] == []

    def test_multiple_sources_in_response(self, client):
        rr = RetrievalResult(
            query="q",
            chunks=[_ranked("c1"), _ranked("c2"), _ranked("c3")],
            confidence_score=0.9,
            low_confidence=False,
        )
        app.state.graph = _make_graph(retrieval_result=rr)
        assert len(client.post("/query", json={"query": "q"}).json()["sources"]) == 3

    def test_empty_answer_string_returned(self, client):
        graph = MagicMock()
        graph.ainvoke = AsyncMock(
            return_value={
                "query": "q",
                "query_vector": [0.1],
                "retrieval_result": _retrieval_result(),
                "answer": "",
            }
        )
        app.state.graph = graph
        body = client.post("/query", json={"query": "q"}).json()
        assert body["answer"] == ""
        assert body["sources"] is not None
