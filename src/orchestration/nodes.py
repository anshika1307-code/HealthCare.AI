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
returning a degraded "service unavailable" answer.
"""
from __future__ import annotations

import asyncio
import logging
from functools import partial
from typing import Any

import openai
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from configs.llm import LLMConfig, LLM_CONFIG
from embedding.base import Embedder
from retrieval.pipeline import RetrievalPipeline

logger = logging.getLogger(__name__)

_DEGRADED_ANSWER = (
    "The system is temporarily unable to generate a response due to a service error. "
    "Please try again in a few moments."
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
        logger.info("embed_query: %r", query[:80])

        loop = asyncio.get_event_loop()
        # embed_batch is synchronous — run in thread pool to avoid blocking the loop
        vectors = await loop.run_in_executor(
            None, partial(embedder.embed_batch, [query])
        )
        return {"query_vector": vectors[0]}

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

        logger.info("retrieve: query=%r, filters=%s", query[:80], filters)
        result = await pipeline.retrieve(query, vector, filters=filters)
        return {"retrieval_result": result}

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
        context: str = retrieval_result.context_text

        logger.info(
            "generate: confidence=%.4f, low_conf=%s",
            retrieval_result.confidence_score,
            retrieval_result.low_confidence,
        )

        messages = [
            {"role": "system", "content": cfg.system_prompt},
            {
                "role": "user",
                "content": (
                    f"Context:\n{context}\n\n"
                    f"Question: {query}"
                ),
            },
        ]

        try:
            answer = await _call_llm(messages)
        except _LLM_RETRYABLE as exc:
            logger.error("LLM call failed after retries: %s", exc)
            answer = _DEGRADED_ANSWER

        return {"answer": answer}

    return generate
