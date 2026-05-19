"""
src/serving/api.py
-------------------
FastAPI application for the healthcare RAG system.

Endpoints:
    POST /query   — submit a clinical question, get a sourced answer
    GET  /health  — liveness + Qdrant connectivity check
    GET  /metrics — latest observability snapshot from Redis

PHI POLICY: query text is NEVER logged or stored. Only query_id (UUID) is
used for log correlation.  See monitoring/logging_config.py.

Environment variables required:
    OPENAI_API_KEY         — for embedder and LLM generation
    QDRANT_URL             — Qdrant REST endpoint (default: http://localhost:6333)

Optional:
    QDRANT_API_KEY         — if Qdrant is deployed with an API key
    BM25_CORPUS_PATH       — override default data/cache/bm25_corpus.pkl
    REDIS_URL              — Redis endpoint for metrics (default: redis://localhost:6379)
"""

from __future__ import annotations

import logging
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

# Load .env before any config or openai imports so env vars are available
try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
except ImportError:
    pass

import openai
import tiktoken
from configs.embedding import EMBEDDING_CONFIG
from configs.llm import LLM_CONFIG
from configs.retrieval import RETRIEVAL_CONFIG
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from qdrant_client import AsyncQdrantClient
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from embedding.openai_embedder import OpenAIEmbedder
from monitoring.logging_config import configure_json_logging
from monitoring.metrics import RAGMetrics
from orchestration.graph import GraphState, build_graph
from retrieval.bm25_retriever import BM25Retriever
from retrieval.confidence import ConfidenceScorer
from retrieval.dense_retriever import DenseRetriever
from retrieval.pipeline import RetrievalPipeline
from retrieval.reranker import CrossEncoderReranker
from retrieval.rrf_ranker import RRFRanker
from serving.schemas import QueryRequest, QueryResponse, SourceChunk

configure_json_logging()
logger = logging.getLogger(__name__)

_DEFAULT_BM25_PATH = Path("data/cache/bm25_corpus.pkl")

# Rate limiter — keyed by client IP
_limiter = Limiter(key_func=get_remote_address)

# Token counter — cl100k_base matches gpt-4o-mini and text-embedding-3-small
_tokenizer = tiktoken.get_encoding("cl100k_base")
_MAX_QUERY_TOKENS = 500


# ---------------------------------------------------------------------------
# Application lifespan — initialise all heavy components once
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up Healthcare RAG API …")

    qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333").strip()
    qdrant_api_key = (os.getenv("QDRANT_API_KEY") or "").strip() or None
    bm25_path = Path(os.getenv("BM25_CORPUS_PATH", str(_DEFAULT_BM25_PATH)))
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")

    # Qdrant async client (connection pooled internally)
    qdrant_client = AsyncQdrantClient(
        url=qdrant_url, api_key=qdrant_api_key, check_compatibility=False
    )

    # Retrieval components
    dense = DenseRetriever(qdrant_client, config=RETRIEVAL_CONFIG.dense)
    bm25 = BM25Retriever.from_cache(bm25_path, config=RETRIEVAL_CONFIG.bm25)
    reranker = CrossEncoderReranker(config=RETRIEVAL_CONFIG.reranker)
    rrf = RRFRanker(config=RETRIEVAL_CONFIG.rrf)
    confidence = ConfidenceScorer(config=RETRIEVAL_CONFIG.confidence)
    pipeline = RetrievalPipeline(dense, bm25, reranker, rrf, confidence)

    # Embedding provider (synchronous; called in thread pool inside embed_query node)
    embedder = OpenAIEmbedder(EMBEDDING_CONFIG)

    # LLM client
    llm_client = openai.AsyncOpenAI()

    # Compile the LangGraph pipeline once — reused for every request
    graph = build_graph(embedder, pipeline, llm_client, LLM_CONFIG)

    # Observability — graceful: if Redis is down metrics are silently skipped
    metrics = RAGMetrics(redis_url=redis_url)

    # Stash everything on app.state for request handlers
    app.state.graph = graph
    app.state.qdrant_client = qdrant_client
    app.state.metrics = metrics

    logger.info("Healthcare RAG API ready.")
    yield

    # Cleanup
    await qdrant_client.close()
    await metrics.close()
    logger.info("Healthcare RAG API shut down.")


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Healthcare AI",
    description="Clinical decision support via hybrid RAG (FDA / ADA / JNC guidelines).",
    version="0.1.0",
    lifespan=lifespan,
)

app.state.limiter = _limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/metrics")
async def metrics_snapshot():
    """Latest observability snapshot: per-query counters + CI eval scores."""
    client = app.state.metrics._client
    if client is None:
        raise HTTPException(status_code=503, detail="Redis not available")
    try:
        query_count, low_conf_count, error_count = await client.mget(
            "metrics:query_count", "metrics:low_conf_count", "metrics:error_count"
        )

        latency_entries = await client.zrange("metrics:latency", -200, -1)
        latencies = [float(e.split("|")[1]) for e in latency_entries if "|" in e]

        conf_entries = await client.zrange("metrics:confidence", -200, -1)
        conf_scores = [float(e.split("|")[1]) for e in conf_entries if "|" in e]

        eval_data = await client.hgetall("eval:latest")

        return {
            "query_count": int(query_count or 0),
            "low_confidence_count": int(low_conf_count or 0),
            "error_count": int(error_count or 0),
            "avg_latency_ms": round(sum(latencies) / len(latencies), 1) if latencies else None,
            "avg_confidence": round(sum(conf_scores) / len(conf_scores), 4)
            if conf_scores
            else None,
            "eval": {k: float(v) if k != "timestamp" else v for k, v in eval_data.items()}
            if eval_data
            else None,
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("metrics fetch failed: %s", exc)
        raise HTTPException(status_code=503, detail="Redis unavailable") from exc


@app.get("/health")
async def health():
    """Liveness + Qdrant connectivity check."""
    try:
        await app.state.qdrant_client.get_collections()
        return {"status": "ok", "qdrant": "reachable"}
    except Exception as exc:  # noqa: BLE001
        logger.warning("Health check: Qdrant unreachable — %s", exc)
        raise HTTPException(status_code=503, detail="Qdrant not reachable") from exc


@app.post("/query", response_model=QueryResponse)
@_limiter.limit("20/minute")
async def query(request: Request, body: QueryRequest) -> QueryResponse:
    """
    Submit a clinical question and receive a sourced answer.

    The pipeline runs: embed → hybrid retrieve → rerank → LLM generate.
    A warning_message is included when retrieval confidence is low.

    Rate limit: 20 requests/minute per IP.
    Token limit: 500 tokens per query (≈ 2 000 chars).

    PHI: query text is NOT logged. Only the query_id is used for correlation.
    """
    # Token-count guard — protects against LLM API cost exhaustion
    token_count = len(_tokenizer.encode(body.query))
    if token_count > _MAX_QUERY_TOKENS:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Query too long: {token_count} tokens "
                f"(limit {_MAX_QUERY_TOKENS}). Please shorten your question."
            ),
        )

    query_id = str(uuid4())
    t_start = time.perf_counter()

    # Log request metadata — never the query text itself (PHI risk)
    logger.info(
        "POST /query received",
        extra={
            "query_id": query_id,
            "has_filters": body.filters is not None,
            "token_count": token_count,
        },
    )

    initial_state: GraphState = {
        "query": body.query,
        "filters": body.filters,
        "query_id": query_id,
    }

    try:
        final_state: GraphState = await app.state.graph.ainvoke(initial_state)
    except Exception as exc:
        total_ms = (time.perf_counter() - t_start) * 1000
        logger.exception(
            "Graph invocation failed",
            extra={"query_id": query_id, "total_ms": round(total_ms, 1)},
        )
        await app.state.metrics.record_error(query_id=query_id, error_type=type(exc).__name__)
        raise HTTPException(status_code=500, detail="Internal pipeline error") from exc

    retrieval_result = final_state.get("retrieval_result")
    if retrieval_result is None:
        raise HTTPException(status_code=500, detail="Retrieval stage produced no result")

    total_ms = (time.perf_counter() - t_start) * 1000
    embed_ms: float = final_state.get("embed_ms", 0.0)
    retrieve_ms: float = final_state.get("retrieve_ms", 0.0)
    generate_ms: float = final_state.get("generate_ms", 0.0)

    logger.info(
        "POST /query complete",
        extra={
            "query_id": query_id,
            "total_ms": round(total_ms, 1),
            "embed_ms": round(embed_ms, 1),
            "retrieve_ms": round(retrieve_ms, 1),
            "generate_ms": round(generate_ms, 1),
            "confidence_score": round(retrieval_result.confidence_score, 4),
            "low_confidence": retrieval_result.low_confidence,
            "num_sources": len(retrieval_result.chunks),
        },
    )

    # Fire-and-forget metrics recording — never blocks the response
    doc_ids = [c.document_id for c in retrieval_result.chunks]
    await app.state.metrics.record(
        query_id=query_id,
        total_ms=total_ms,
        embed_ms=embed_ms,
        retrieve_ms=retrieve_ms,
        generate_ms=generate_ms,
        confidence_score=retrieval_result.confidence_score,
        doc_ids=doc_ids,
        low_confidence=retrieval_result.low_confidence,
    )

    sources = [
        SourceChunk(
            chunk_id=chunk.chunk_id,
            document_id=chunk.document_id,
            doc_type=chunk.payload.get("doc_type", "") or "",
            section_name=chunk.section_name or "",
            reranker_score=chunk.reranker_score,
            text=chunk.text or "",
        )
        for chunk in retrieval_result.chunks
    ]

    return QueryResponse(
        answer=final_state.get("answer", ""),
        sources=sources,
        confidence_score=retrieval_result.confidence_score,
        low_confidence=retrieval_result.low_confidence,
        warning_message=retrieval_result.warning_message,
        filters_applied=retrieval_result.filters_applied,
    )
