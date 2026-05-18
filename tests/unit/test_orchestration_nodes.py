"""
tests/unit/test_orchestration_nodes.py
----------------------------------------
Unit tests for src/orchestration/nodes.py.

Each node factory is tested in isolation with mocked dependencies.
No network calls, no model loading, no Qdrant.

Coverage
--------
make_embed_node   — runs embed_batch in executor, returns query_vector in state
make_retrieve_node — calls pipeline.retrieve, propagates filters, returns result
make_generate_node — calls LLM, builds correct messages, handles retry, returns
                     degraded answer after exhausted retries
"""
import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import openai
import pytest

_SRC = Path(__file__).resolve().parents[2] / "src"
_ROOT = Path(__file__).resolve().parents[2]
for p in (_SRC, _ROOT):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from configs.llm import LLMConfig
from orchestration.nodes import _DEGRADED_ANSWER, make_embed_node, make_generate_node, make_retrieve_node
from retrieval.confidence import RetrievalResult
from retrieval.reranker import RankedResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ranked(chunk_id: str = "c1", score: float = 0.9) -> RankedResult:
    return RankedResult(
        chunk_id=chunk_id,
        reranker_score=score,
        text="Some clinical text.",
        payload={"document_id": "fda", "section_name": "Warnings", "safety_flag": False},
    )


def _retrieval_result(query: str = "q", score: float = 0.8) -> RetrievalResult:
    chunks = [_ranked()]
    return RetrievalResult(
        query=query,
        chunks=chunks,
        confidence_score=score,
        low_confidence=score < 0.4,
    )


def _fake_request() -> httpx.Request:
    return httpx.Request("POST", "https://api.openai.com/v1/chat/completions")


def _make_llm_response(content: str) -> MagicMock:
    msg = MagicMock()
    msg.content = content
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


# ===========================================================================
# make_embed_node
# ===========================================================================

class TestEmbedNode:

    @pytest.fixture
    def embedder(self):
        m = MagicMock()
        m.embed_batch.return_value = [[0.1, 0.2, 0.3]]
        return m

    @pytest.mark.asyncio
    async def test_returns_query_vector(self, embedder):
        node = make_embed_node(embedder)
        result = await node({"query": "HbA1c target?"})
        assert "query_vector" in result
        assert result["query_vector"] == [0.1, 0.2, 0.3]

    @pytest.mark.asyncio
    async def test_calls_embed_batch_with_query_in_list(self, embedder):
        node = make_embed_node(embedder)
        await node({"query": "metformin eGFR"})
        embedder.embed_batch.assert_called_once_with(["metformin eGFR"])

    @pytest.mark.asyncio
    async def test_returns_first_vector(self, embedder):
        embedder.embed_batch.return_value = [[0.1], [0.2]]
        node = make_embed_node(embedder)
        result = await node({"query": "q"})
        assert result["query_vector"] == [0.1]

    @pytest.mark.asyncio
    async def test_sets_query_vector_and_embed_ms(self, embedder):
        node = make_embed_node(embedder)
        result = await node({"query": "q"})
        assert "query_vector" in result
        assert "embed_ms" in result
        assert isinstance(result["embed_ms"], float)

    @pytest.mark.asyncio
    async def test_different_embedders_produce_different_nodes(self):
        e1, e2 = MagicMock(), MagicMock()
        e1.embed_batch.return_value = [[1.0]]
        e2.embed_batch.return_value = [[2.0]]
        n1 = make_embed_node(e1)
        n2 = make_embed_node(e2)
        r1 = await n1({"query": "q"})
        r2 = await n2({"query": "q"})
        assert r1["query_vector"] != r2["query_vector"]


# ===========================================================================
# make_retrieve_node
# ===========================================================================

class TestRetrieveNode:

    @pytest.fixture
    def pipeline(self):
        m = MagicMock()
        m.retrieve = AsyncMock(return_value=_retrieval_result())
        return m

    @pytest.mark.asyncio
    async def test_returns_retrieval_result_key(self, pipeline):
        node = make_retrieve_node(pipeline)
        state = {"query": "q", "query_vector": [0.1]}
        result = await node(state)
        assert "retrieval_result" in result
        assert isinstance(result["retrieval_result"], RetrievalResult)

    @pytest.mark.asyncio
    async def test_calls_pipeline_retrieve_with_query_and_vector(self, pipeline):
        node = make_retrieve_node(pipeline)
        await node({"query": "blood pressure", "query_vector": [0.5, 0.6]})
        pipeline.retrieve.assert_called_once()
        args, kwargs = pipeline.retrieve.call_args
        assert args[0] == "blood pressure"
        assert args[1] == [0.5, 0.6]

    @pytest.mark.asyncio
    async def test_passes_filters_when_present(self, pipeline):
        node = make_retrieve_node(pipeline)
        filters = {"doc_type": "jnc"}
        await node({"query": "q", "query_vector": [0.1], "filters": filters})
        _, kwargs = pipeline.retrieve.call_args
        assert kwargs.get("filters") == filters

    @pytest.mark.asyncio
    async def test_passes_none_filters_when_absent(self, pipeline):
        node = make_retrieve_node(pipeline)
        await node({"query": "q", "query_vector": [0.1]})
        _, kwargs = pipeline.retrieve.call_args
        assert kwargs.get("filters") is None

    @pytest.mark.asyncio
    async def test_sets_retrieval_result_and_retrieve_ms(self, pipeline):
        node = make_retrieve_node(pipeline)
        result = await node({"query": "q", "query_vector": [0.1]})
        assert "retrieval_result" in result
        assert "retrieve_ms" in result
        assert isinstance(result["retrieve_ms"], float)

    @pytest.mark.asyncio
    async def test_pipeline_error_propagates(self, pipeline):
        pipeline.retrieve.side_effect = RuntimeError("Qdrant down")
        node = make_retrieve_node(pipeline)
        with pytest.raises(RuntimeError, match="Qdrant down"):
            await node({"query": "q", "query_vector": [0.1]})


# ===========================================================================
# make_generate_node
# ===========================================================================

class TestGenerateNode:

    @pytest.fixture
    def llm_client(self):
        client = MagicMock()
        client.chat = MagicMock()
        client.chat.completions = MagicMock()
        client.chat.completions.create = AsyncMock(
            return_value=_make_llm_response("Target HbA1c is < 7%.")
        )
        return client

    @pytest.fixture
    def cfg(self):
        return LLMConfig(
            model_name="gpt-4o-mini",
            temperature=0.0,
            max_output_tokens=512,
            system_prompt="You are a clinical assistant.",
        )

    @pytest.fixture
    def state(self):
        return {
            "query": "What is the HbA1c target?",
            "retrieval_result": _retrieval_result(),
        }

    @pytest.mark.asyncio
    async def test_returns_answer_key(self, llm_client, cfg, state):
        node = make_generate_node(llm_client, cfg)
        result = await node(state)
        assert "answer" in result

    @pytest.mark.asyncio
    async def test_answer_matches_llm_output(self, llm_client, cfg, state):
        node = make_generate_node(llm_client, cfg)
        result = await node(state)
        assert result["answer"] == "Target HbA1c is < 7%."

    @pytest.mark.asyncio
    async def test_calls_chat_completions_create(self, llm_client, cfg, state):
        node = make_generate_node(llm_client, cfg)
        await node(state)
        llm_client.chat.completions.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_uses_configured_model(self, llm_client, cfg, state):
        node = make_generate_node(llm_client, cfg)
        await node(state)
        _, kwargs = llm_client.chat.completions.create.call_args
        assert kwargs["model"] == "gpt-4o-mini"

    @pytest.mark.asyncio
    async def test_uses_configured_temperature(self, llm_client, cfg, state):
        node = make_generate_node(llm_client, cfg)
        await node(state)
        _, kwargs = llm_client.chat.completions.create.call_args
        assert kwargs["temperature"] == pytest.approx(0.0)

    @pytest.mark.asyncio
    async def test_uses_configured_max_tokens(self, llm_client, cfg, state):
        node = make_generate_node(llm_client, cfg)
        await node(state)
        _, kwargs = llm_client.chat.completions.create.call_args
        assert kwargs["max_tokens"] == 512

    @pytest.mark.asyncio
    async def test_messages_contain_system_and_user(self, llm_client, cfg, state):
        node = make_generate_node(llm_client, cfg)
        await node(state)
        _, kwargs = llm_client.chat.completions.create.call_args
        roles = [m["role"] for m in kwargs["messages"]]
        assert "system" in roles
        assert "user" in roles

    @pytest.mark.asyncio
    async def test_system_message_is_system_prompt(self, llm_client, cfg, state):
        node = make_generate_node(llm_client, cfg)
        await node(state)
        _, kwargs = llm_client.chat.completions.create.call_args
        system_msg = next(m for m in kwargs["messages"] if m["role"] == "system")
        assert system_msg["content"] == "You are a clinical assistant."

    @pytest.mark.asyncio
    async def test_user_message_contains_query(self, llm_client, cfg, state):
        node = make_generate_node(llm_client, cfg)
        await node(state)
        _, kwargs = llm_client.chat.completions.create.call_args
        user_msg = next(m for m in kwargs["messages"] if m["role"] == "user")
        assert "What is the HbA1c target?" in user_msg["content"]

    @pytest.mark.asyncio
    async def test_user_message_contains_context(self, llm_client, cfg, state):
        node = make_generate_node(llm_client, cfg)
        await node(state)
        _, kwargs = llm_client.chat.completions.create.call_args
        user_msg = next(m for m in kwargs["messages"] if m["role"] == "user")
        # context comes from retrieval_result.context_text
        assert "Context:" in user_msg["content"]

    @pytest.mark.asyncio
    async def test_empty_response_content_returns_empty_string(self, llm_client, cfg, state):
        llm_client.chat.completions.create.return_value = _make_llm_response(None)
        node = make_generate_node(llm_client, cfg)
        result = await node(state)
        assert result["answer"] == ""

    # --- Retry / degraded answer behaviour ---

    @pytest.mark.asyncio
    async def test_rate_limit_error_returns_degraded_answer(self, llm_client, cfg, state):
        req = _fake_request()
        llm_client.chat.completions.create.side_effect = openai.RateLimitError(
            "rate limit", response=httpx.Response(429, request=req), body=None
        )
        node = make_generate_node(llm_client, cfg)
        result = await node(state)
        assert result["answer"] == _DEGRADED_ANSWER

    @pytest.mark.asyncio
    async def test_api_timeout_returns_degraded_answer(self, llm_client, cfg, state):
        req = _fake_request()
        llm_client.chat.completions.create.side_effect = openai.APITimeoutError(
            request=req
        )
        node = make_generate_node(llm_client, cfg)
        result = await node(state)
        assert result["answer"] == _DEGRADED_ANSWER

    @pytest.mark.asyncio
    async def test_api_connection_error_returns_degraded_answer(self, llm_client, cfg, state):
        req = _fake_request()
        llm_client.chat.completions.create.side_effect = openai.APIConnectionError(
            request=req
        )
        node = make_generate_node(llm_client, cfg)
        result = await node(state)
        assert result["answer"] == _DEGRADED_ANSWER

    @pytest.mark.asyncio
    async def test_non_retryable_error_propagates(self, llm_client, cfg, state):
        llm_client.chat.completions.create.side_effect = ValueError("unexpected")
        node = make_generate_node(llm_client, cfg)
        with pytest.raises(ValueError, match="unexpected"):
            await node(state)

    @pytest.mark.asyncio
    async def test_uses_default_config_when_none_passed(self, llm_client, state):
        node = make_generate_node(llm_client, config=None)
        result = await node(state)
        assert "answer" in result

    @pytest.mark.asyncio
    async def test_sets_answer_and_generate_ms(self, llm_client, cfg, state):
        node = make_generate_node(llm_client, cfg)
        result = await node(state)
        assert "answer" in result
        assert "generate_ms" in result
        assert isinstance(result["generate_ms"], float)
