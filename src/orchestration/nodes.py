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
import json
import logging
import time
from functools import partial
from typing import Any

import openai
from configs.llm import LLM_CONFIG, LLMConfig
from openai.types.chat import ChatCompletionMessageParam
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

_SUGGESTIONS_SYSTEM = (
    "Given a clinical question and the context used to answer it, return exactly 3 short "
    "follow-up questions a clinician might ask next. Respond with ONLY a valid JSON array "
    'of 3 strings. Example: ["What is the recommended dose?", '
    '"Are there any contraindications?", "What monitoring is required?"]'
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


def make_generate_node(
    client: openai.AsyncOpenAI,
    config: LLMConfig | None = None,
    groq_client: openai.AsyncOpenAI | None = None,
):
    """Return an async LangGraph node that calls the LLM with retrieved context."""

    cfg = config or LLM_CONFIG

    # primary = Groq (fast/free) if available, else OpenAI
    primary = groq_client or client
    primary_model = cfg.model_name if groq_client else cfg.fallback_model_name
    sugg_model = cfg.suggestions_model_name if groq_client else cfg.fallback_model_name

    _TRANSIENT = (openai.APITimeoutError, openai.APIConnectionError)

    @retry(
        retry=retry_if_exception_type(_TRANSIENT),
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        reraise=True,
    )
    async def _call_primary(messages: list[ChatCompletionMessageParam]) -> str:
        response = await primary.chat.completions.create(
            model=primary_model,
            messages=messages,
            temperature=cfg.temperature,
            max_tokens=cfg.max_output_tokens,
        )
        return response.choices[0].message.content or ""

    @retry(
        retry=retry_if_exception_type(_LLM_RETRYABLE),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        reraise=True,
    )
    async def _call_fallback(messages: list[ChatCompletionMessageParam]) -> str:
        response = await client.chat.completions.create(
            model=cfg.fallback_model_name,
            messages=messages,
            temperature=cfg.temperature,
            max_tokens=cfg.max_output_tokens,
        )
        return response.choices[0].message.content or ""

    async def _call_llm(messages: list[ChatCompletionMessageParam]) -> str:
        """Try Groq primary; if rate-limited fall back to OpenAI automatically."""
        try:
            return await _call_primary(messages)
        except openai.RateLimitError:
            if groq_client:
                logger.warning("Groq rate limit hit — falling back to OpenAI gpt-4o-mini")
                return await _call_fallback(messages)
            raise

    async def _gen_suggestions(query: str, context: str) -> list[str]:
        """Generate 3 follow-up questions concurrently with the main answer call."""
        try:
            sugg_messages: list[ChatCompletionMessageParam] = [
                {"role": "system", "content": _SUGGESTIONS_SYSTEM},
                {"role": "user", "content": f"Question: {query}\n\nContext:\n{context[:600]}"},
            ]
            resp = await primary.chat.completions.create(
                model=sugg_model,
                messages=sugg_messages,
                temperature=0.4,
                max_tokens=120,
            )
            raw = (resp.choices[0].message.content or "").strip()
            parsed = json.loads(raw)
            return [str(q) for q in parsed[:3]] if isinstance(parsed, list) else []
        except Exception:  # noqa: BLE001
            return []

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

        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": cfg.system_prompt},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"},
        ]

        t0 = time.perf_counter()
        try:
            # Run main answer + suggestions concurrently — suggestions add ~0ms latency
            answer, suggested_queries = await asyncio.gather(
                _call_llm(messages),
                _gen_suggestions(query, context),
            )
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
            suggested_queries = []

        return {
            "answer": answer,
            "generate_ms": generate_ms,
            "suggested_queries": suggested_queries,
        }

    return generate
