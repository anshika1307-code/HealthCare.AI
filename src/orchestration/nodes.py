"""
src/orchestration/nodes.py
---------------------------
LangGraph node factories for the healthcare RAG pipeline.

Each public function returns a coroutine that LangGraph calls with the
current GraphState. Dependencies (embedder, pipeline, LLM client) are
closed over so no global state is required.

Node order:
    embed_query → retrieve → generate

The generate node retries up to 3 times on transient OpenAI errors before
returning a degraded "service unavailable" answer that still surfaces the
retrieved sources (stored separately in GraphState).

PHI POLICY: query text is never written to logs — only query_id and metadata.
"""

from __future__ import annotations

import asyncio
import logging
import time
from functools import partial
from typing import Any

import openai
from configs.llm import LLM_CONFIG, LLMConfig
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from embedding.base import Embedder
from retrieval.pipeline import RetrievalPipeline

logger = logging.getLogger(__name__)

_DEGRADED_ANSWER = (
    "The system is temporarily unable to generate a full response due to a service error. "
    "Relevant source documents are included below — please consult them directly."
)

_LLM_RETRYABLE = (
    openai.APITimeoutError,
    openai.APIConnectionError,
    openai.RateLimitError,
)


# ---------------------------------------------------------------------------
# Node 1: embed_query
# ---------------------------------------------------------------------------


def make_embed_node(embedder: Embedder):
    """Return an async LangGraph node that embeds the user query."""

    async def embed_query(state: dict[str, Any]) -> dict[str, Any]:
        query: str = state["query"]
        query_id: str = state.get("query_id", "unknown")
        logger.info("embed_query start", extra={"query_id": query_id})

        t0 = time.perf_counter()
        loop = asyncio.get_event_loop()
        vectors = await loop.run_in_executor(None, partial(embedder.embed_batch, [query]))
        embed_ms = (time.perf_counter() - t0) * 1000

        logger.info(
            "embed_query done",
            extra={"query_id": query_id, "embed_ms": round(embed_ms, 1)},
        )
        return {"query_vector": vectors[0], "embed_ms": embed_ms}

    return embed_query


# ---------------------------------------------------------------------------
# Node 2: retrieve
# ---------------------------------------------------------------------------


def make_retrieve_node(pipeline: RetrievalPipeline):
    """Return an async LangGraph node that runs the hybrid retrieval pipeline."""

    async def retrieve(state: dict[str, Any]) -> dict[str, Any]:
        query: str = state["query"]
        vector: list[float] = state["query_vector"]
        filters: dict[str, Any] | None = state.get("filters")
        query_id: str = state.get("query_id", "unknown")

        logger.info(
            "retrieve start",
            extra={"query_id": query_id, "has_filters": filters is not None},
        )

        t0 = time.perf_counter()
        result = await pipeline.retrieve(query, vector, filters=filters)
        retrieve_ms = (time.perf_counter() - t0) * 1000

        logger.info(
            "retrieve done",
            extra={
                "query_id": query_id,
                "retrieve_ms": round(retrieve_ms, 1),
                "chunks_returned": len(result.chunks),
                "confidence_score": round(result.confidence_score, 4),
                "low_confidence": result.low_confidence,
            },
        )
        return {"retrieval_result": result, "retrieve_ms": retrieve_ms}

    return retrieve


# ---------------------------------------------------------------------------
# Node 3: generate
# ---------------------------------------------------------------------------


def make_generate_node(client: openai.AsyncOpenAI, config: LLMConfig | None = None):
    """Return an async LangGraph node that calls the LLM with retrieved context."""

    cfg = config or LLM_CONFIG

    @retry(
        retry=retry_if_exception_type(_LLM_RETRYABLE),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        reraise=True,
    )
    async def _call_llm(messages: list[dict]) -> str:
        response = await client.chat.completions.create(
            model=cfg.model_name,
            messages=messages,
            temperature=cfg.temperature,
            max_tokens=cfg.max_output_tokens,
        )
        return response.choices[0].message.content or ""

    async def generate(state: dict[str, Any]) -> dict[str, Any]:
        retrieval_result = state["retrieval_result"]
        query: str = state["query"]
        query_id: str = state.get("query_id", "unknown")
        context: str = retrieval_result.context_text

        logger.info(
            "generate start",
            extra={
                "query_id": query_id,
                "confidence_score": round(retrieval_result.confidence_score, 4),
                "low_confidence": retrieval_result.low_confidence,
            },
        )

        messages = [
            {"role": "system", "content": cfg.system_prompt},
            {
                "role": "user",
                "content": (f"Context:\n{context}\n\nQuestion: {query}"),
            },
        ]

        t0 = time.perf_counter()
        try:
            answer = await _call_llm(messages)
            generate_ms = (time.perf_counter() - t0) * 1000
            logger.info(
                "generate done",
                extra={"query_id": query_id, "generate_ms": round(generate_ms, 1)},
            )
        except _LLM_RETRYABLE as exc:
            generate_ms = (time.perf_counter() - t0) * 1000
            logger.error(
                "LLM call failed after 3 retries — returning degraded answer",
                extra={"query_id": query_id, "error_type": type(exc).__name__},
            )
            answer = _DEGRADED_ANSWER

        return {"answer": answer, "generate_ms": generate_ms}

    return generate
