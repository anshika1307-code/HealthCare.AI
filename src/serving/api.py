"""
src/serving/api.py
-------------------
FastAPI application for the healthcare RAG system.

Endpoints:
    POST /query   — submit a clinical question, get a sourced answer
    GET  /health  — liveness + Qdrant connectivity check

All heavy dependencies (BM25 corpus, cross-encoder, Qdrant client, compiled
LangGraph) are loaded once inside the lifespan context manager and stored on
app.state so request handlers can access them without re-initialising.

Environment variables required:
    OPENAI_API_KEY         — for embedder and LLM generation
    QDRANT_URL             — Qdrant REST endpoint (default: http://localhost:6333)

Optional:
    QDRANT_API_KEY         — if Qdrant is deployed with an API key
    BM25_CORPUS_PATH       — override default data/cache/bm25_corpus.pkl
"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

# Load .env before any config or openai imports so env vars are available
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
except ImportError:
    pass

import openai
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from qdrant_client import AsyncQdrantClient

from configs.embedding import EMBEDDING_CONFIG
from configs.llm import LLM_CONFIG
from configs.retrieval import RETRIEVAL_CONFIG
from embedding.openai_embedder import OpenAIEmbedder
from orchestration.graph import GraphState, build_graph
from retrieval.bm25_retriever import BM25Retriever
from retrieval.confidence import ConfidenceScorer
from retrieval.dense_retriever import DenseRetriever
from retrieval.pipeline import RetrievalPipeline
from retrieval.reranker import CrossEncoderReranker
from retrieval.rrf_ranker import RRFRanker
from serving.schemas import QueryRequest, QueryResponse, SourceChunk

logger = logging.getLogger(__name__)

_DEFAULT_BM25_PATH = Path("data/cache/bm25_corpus.pkl")


# ---------------------------------------------------------------------------
# Application lifespan — initialise all heavy components once
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up Healthcare RAG API …")

    qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
    qdrant_api_key = os.getenv("QDRANT_API_KEY")
    bm25_path = Path(os.getenv("BM25_CORPUS_PATH", str(_DEFAULT_BM25_PATH)))

    # Qdrant async client (connection pooled internally)
    qdrant_client = AsyncQdrantClient(url=qdrant_url, api_key=qdrant_api_key, check_compatibility=False)

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

    # Stash everything on app.state for request handlers
    app.state.graph = graph
    app.state.qdrant_client = qdrant_client

    logger.info("Healthcare RAG API ready.")
    yield

    # Cleanup
    await qdrant_client.close()
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

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
async def query(request: QueryRequest) -> QueryResponse:
    """
    Submit a clinical question and receive a sourced answer.

    The pipeline runs: embed → hybrid retrieve → rerank → LLM generate.
    A warning_message is included when retrieval confidence is low.
    """
    logger.info("POST /query: %r (filters=%s)", request.query[:80], request.filters)

    initial_state: GraphState = {
        "query": request.query,
        "filters": request.filters,
    }

    try:
        final_state: GraphState = await app.state.graph.ainvoke(initial_state)
    except Exception as exc:
        logger.exception("Graph invocation failed: %s", exc)
        raise HTTPException(status_code=500, detail="Internal pipeline error") from exc

    retrieval_result = final_state.get("retrieval_result")
    if retrieval_result is None:
        raise HTTPException(status_code=500, detail="Retrieval stage produced no result")

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
