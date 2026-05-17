"""
tests/unit/test_orchestration_graph.py
----------------------------------------
Unit tests for src/orchestration/graph.py.

Verifies that build_graph returns a compiled LangGraph with correct topology.
The compiled graph is invoked end-to-end with fully mocked dependencies —
no network, no Qdrant, no OpenAI calls.

Coverage
--------
build_graph        — returns a compiled graph
GraphState         — TypedDict keys are correct
End-to-end ainvoke — state flows START → embed → retrieve → generate → END
                   — filters propagate through state
                   — custom LLMConfig is respected
"""
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

_SRC = Path(__file__).resolve().parents[2] / "src"
_ROOT = Path(__file__).resolve().parents[2]
for p in (_SRC, _ROOT):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from configs.llm import LLMConfig
from orchestration.graph import GraphState, build_graph
from retrieval.confidence import RetrievalResult
from retrieval.reranker import RankedResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ranked() -> RankedResult:
    return RankedResult(
        chunk_id="c1",
        reranker_score=0.88,
        text="Metformin is first-line therapy for T2DM.",
        payload={"document_id": "ada", "section_name": "§9.1", "safety_flag": False},
    )


def _retrieval_result() -> RetrievalResult:
    return RetrievalResult(
        query="metformin therapy",
        chunks=[_ranked()],
        confidence_score=0.88,
        low_confidence=False,
    )


def _make_embedder(vector: list[float] | None = None):
    m = MagicMock()
    m.embed_batch.return_value = [vector or [0.1, 0.2, 0.3]]
    return m


def _make_pipeline(result: RetrievalResult | None = None):
    m = MagicMock()
    m.retrieve = AsyncMock(return_value=result or _retrieval_result())
    return m


def _make_llm_client(answer: str = "Clinical answer."):
    msg = MagicMock()
    msg.content = answer
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    client = MagicMock()
    client.chat = MagicMock()
    client.chat.completions = MagicMock()
    client.chat.completions.create = AsyncMock(return_value=resp)
    return client


# ===========================================================================
# build_graph — structural checks
# ===========================================================================

class TestBuildGraph:

    def test_returns_compiled_graph(self):
        graph = build_graph(_make_embedder(), _make_pipeline(), _make_llm_client())
        # LangGraph compiled graphs expose ainvoke
        assert callable(getattr(graph, "ainvoke", None))

    def test_graph_has_astream(self):
        graph = build_graph(_make_embedder(), _make_pipeline(), _make_llm_client())
        assert callable(getattr(graph, "astream", None))

    def test_different_clients_produce_distinct_graphs(self):
        g1 = build_graph(_make_embedder(), _make_pipeline(), _make_llm_client())
        g2 = build_graph(_make_embedder(), _make_pipeline(), _make_llm_client())
        assert g1 is not g2


# ===========================================================================
# GraphState TypedDict
# ===========================================================================

class TestGraphState:

    def test_can_create_with_query_only(self):
        state: GraphState = {"query": "test"}
        assert state["query"] == "test"

    def test_can_create_fully_populated(self):
        state: GraphState = {
            "query": "test",
            "filters": {"doc_type": "fda"},
            "query_vector": [0.1, 0.2],
            "retrieval_result": _retrieval_result(),
            "answer": "Some answer",
        }
        assert state["answer"] == "Some answer"

    def test_partial_state_no_error(self):
        # total=False means all keys optional
        state: GraphState = {"answer": "x"}
        assert "query" not in state


# ===========================================================================
# End-to-end ainvoke (mocked dependencies)
# ===========================================================================

class TestGraphInvoke:

    @pytest.mark.asyncio
    async def test_returns_answer(self):
        graph = build_graph(
            _make_embedder(),
            _make_pipeline(),
            _make_llm_client("Target HbA1c < 7%."),
        )
        result = await graph.ainvoke({"query": "HbA1c target?"})
        assert result["answer"] == "Target HbA1c < 7%."

    @pytest.mark.asyncio
    async def test_result_contains_retrieval_result(self):
        graph = build_graph(_make_embedder(), _make_pipeline(), _make_llm_client())
        result = await graph.ainvoke({"query": "metformin"})
        assert "retrieval_result" in result
        assert isinstance(result["retrieval_result"], RetrievalResult)

    @pytest.mark.asyncio
    async def test_result_contains_query_vector(self):
        graph = build_graph(
            _make_embedder([0.5, 0.6]), _make_pipeline(), _make_llm_client()
        )
        result = await graph.ainvoke({"query": "q"})
        assert result["query_vector"] == [0.5, 0.6]

    @pytest.mark.asyncio
    async def test_query_preserved_in_final_state(self):
        graph = build_graph(_make_embedder(), _make_pipeline(), _make_llm_client())
        result = await graph.ainvoke({"query": "blood pressure target"})
        assert result["query"] == "blood pressure target"

    @pytest.mark.asyncio
    async def test_filters_propagated_to_pipeline(self):
        pipeline = _make_pipeline()
        graph = build_graph(_make_embedder(), pipeline, _make_llm_client())
        filters = {"doc_type": "jnc"}
        await graph.ainvoke({"query": "BP threshold", "filters": filters})
        _, kwargs = pipeline.retrieve.call_args
        assert kwargs.get("filters") == filters

    @pytest.mark.asyncio
    async def test_embed_batch_called_with_query(self):
        embedder = _make_embedder()
        graph = build_graph(embedder, _make_pipeline(), _make_llm_client())
        await graph.ainvoke({"query": "eGFR metformin"})
        embedder.embed_batch.assert_called_once_with(["eGFR metformin"])

    @pytest.mark.asyncio
    async def test_pipeline_retrieve_called_once(self):
        pipeline = _make_pipeline()
        graph = build_graph(_make_embedder(), pipeline, _make_llm_client())
        await graph.ainvoke({"query": "q"})
        pipeline.retrieve.assert_called_once()

    @pytest.mark.asyncio
    async def test_llm_create_called_once(self):
        client = _make_llm_client()
        graph = build_graph(_make_embedder(), _make_pipeline(), client)
        await graph.ainvoke({"query": "q"})
        client.chat.completions.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_custom_llm_config_respected(self):
        client = _make_llm_client()
        cfg = LLMConfig(model_name="gpt-4o", temperature=0.1, max_output_tokens=256)
        graph = build_graph(_make_embedder(), _make_pipeline(), client, llm_config=cfg)
        await graph.ainvoke({"query": "q"})
        _, kwargs = client.chat.completions.create.call_args
        assert kwargs["model"] == "gpt-4o"
        assert kwargs["temperature"] == pytest.approx(0.1)
        assert kwargs["max_tokens"] == 256

    @pytest.mark.asyncio
    async def test_no_filters_key_in_initial_state(self):
        pipeline = _make_pipeline()
        graph = build_graph(_make_embedder(), pipeline, _make_llm_client())
        await graph.ainvoke({"query": "q"})
        _, kwargs = pipeline.retrieve.call_args
        assert kwargs.get("filters") is None
