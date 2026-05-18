"""
src/evaluation/check_confidence.py
------------------------------------
Quick confidence probe for the 9 previously low-confidence eval questions.

Runs only those questions through the RAG pipeline and prints a concise
confidence table — no RAGAS scoring, no report file.  Use this to verify
retrieval tuning (top_k, RRF weights, etc.) before committing to a full
40-question eval run.

Usage:
    python src/evaluation/check_confidence.py
    python src/evaluation/check_confidence.py --threshold 0.40
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time
from pathlib import Path

# ── path setup ────────────────────────────────────────────────────────────────
_ROOT = Path(__file__).resolve().parents[2]
_SRC  = _ROOT / "src"
for _p in (_SRC, _ROOT):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

try:
    from dotenv import load_dotenv
    load_dotenv(_ROOT / ".env")
except ImportError:
    pass

import logging

logging.basicConfig(level=logging.WARNING, format="%(levelname)s  %(message)s")
# Silence all noisy loggers — we only want our own table output
for _noisy in ("httpx", "httpcore", "openai", "sentence_transformers",
               "retrieval", "orchestration", "embedding"):
    logging.getLogger(_noisy).setLevel(logging.ERROR)

import openai
from configs.embedding import EMBEDDING_CONFIG
from configs.llm import LLM_CONFIG
from configs.retrieval import RETRIEVAL_CONFIG
from qdrant_client import AsyncQdrantClient

from embedding.openai_embedder import OpenAIEmbedder
from orchestration.graph import build_graph
from retrieval.bm25_retriever import BM25Retriever
from retrieval.confidence import ConfidenceScorer
from retrieval.dense_retriever import DenseRetriever
from retrieval.pipeline import RetrievalPipeline
from retrieval.reranker import CrossEncoderReranker
from retrieval.rrf_ranker import RRFRanker

# ── the 9 previously low-confidence questions ─────────────────────────────────
PROBE_QUESTIONS = [
    {
        "id": "fda_04",
        "question": "After stopping metformin for a contrast imaging procedure, when can it be restarted and what must be confirmed first?",
        "prev_conf": 0.1793,
        "difficulty": "medium",
    },
    {
        "id": "ada6_08",
        "question": "What does GMI stand for and what is it used as an alternative or supplement to?",
        "prev_conf": 0.0357,
        "difficulty": "medium",
    },
    {
        "id": "ada9_03",
        "question": "What does the ADA section 9 say should happen to metformin when insulin is being intensified — should it be stopped or continued?",
        "prev_conf": 0.2183,
        "difficulty": "medium",
    },
    {
        "id": "ada9_05",
        "question": "The ADA section 9 identifies a trade-off with stepwise therapy vs combination — what is the stated advantage of stepwise addition over initial combination?",
        "prev_conf": 0.0117,
        "difficulty": "hard",
    },
    {
        "id": "ada9_06",
        "question": "Which two drug classes should be continued and which two should be weaned when intensifying insulin therapy according to ADA 2023 section 9?",
        "prev_conf": 0.3480,
        "difficulty": "hard",
    },
    {
        "id": "ada9_10",
        "question": "Does ADA section 9 say medication regimen should be re-evaluated and at what time interval?",
        "prev_conf": 0.0419,
        "difficulty": "easy",
    },
    {
        "id": "jnc_07",
        "question": "JNC 8 prohibits combining two specific drug classes — which combination is explicitly not recommended?",
        "prev_conf": 0.1063,
        "difficulty": "easy",
    },
    {
        "id": "jnc_08",
        "question": "If a patient's BP target is not reached after starting antihypertensive therapy, what is the JNC 8 recommended time window and action?",
        "prev_conf": 0.3059,
        "difficulty": "medium",
    },
    {
        "id": "jnc_10",
        "question": "JNC 8 lists exactly four drug classes as acceptable for first-line and later-line treatment — what are they?",
        "prev_conf": 0.2455,
        "difficulty": "easy",
    },
]


async def _build_pipeline():
    qdrant_url     = os.getenv("QDRANT_URL", "http://localhost:6333")
    qdrant_api_key = os.getenv("QDRANT_API_KEY")
    bm25_path      = Path(os.getenv("BM25_CORPUS_PATH", "data/cache/bm25_corpus.pkl"))

    qdrant     = AsyncQdrantClient(url=qdrant_url, api_key=qdrant_api_key, check_compatibility=False)
    dense      = DenseRetriever(qdrant, config=RETRIEVAL_CONFIG.dense)
    bm25       = BM25Retriever.from_cache(bm25_path, config=RETRIEVAL_CONFIG.bm25)
    reranker   = CrossEncoderReranker(config=RETRIEVAL_CONFIG.reranker)
    rrf        = RRFRanker(config=RETRIEVAL_CONFIG.rrf)
    confidence = ConfidenceScorer(config=RETRIEVAL_CONFIG.confidence)
    pipeline   = RetrievalPipeline(dense, bm25, reranker, rrf, confidence)
    embedder   = OpenAIEmbedder(EMBEDDING_CONFIG)
    llm_client = openai.AsyncOpenAI()
    graph      = build_graph(embedder, pipeline, llm_client, LLM_CONFIG)
    return graph, qdrant


async def _probe(threshold: float) -> list[dict]:
    print("\nLoading pipeline (cross-encoder model download on first run) …")
    graph, qdrant = await _build_pipeline()

    results = []
    try:
        for item in PROBE_QUESTIONS:
            t0 = time.perf_counter()
            state = await graph.ainvoke({
                "query":    item["question"],
                "query_id": item["id"],
            })
            elapsed_ms = (time.perf_counter() - t0) * 1000

            rr   = state.get("retrieval_result")
            conf = rr.confidence_score if rr else 0.0
            low  = rr.low_confidence   if rr else True

            results.append({
                **item,
                "new_conf":   conf,
                "low_conf":   low,
                "elapsed_ms": round(elapsed_ms),
            })
    finally:
        await qdrant.close()

    return results


def _print_table(results: list[dict], threshold: float) -> None:
    PASS = "\033[92m✓\033[0m"  # green
    FAIL = "\033[91m✗\033[0m"  # red
    UP   = "\033[92m▲\033[0m"
    DOWN = "\033[91m▼\033[0m"
    EQ   = "\033[93m─\033[0m"

    print("\n" + "─" * 78)
    print(f"  CONFIDENCE PROBE  (threshold = {threshold:.2f})")
    print("─" * 78)
    print(f"  {'ID':<12} {'Diff':<7} {'Prev':>6}  {'Now':>6}  {'Δ':>6}  {'Pass?':>6}  {'ms':>5}")
    print("─" * 78)

    passed = 0
    for r in results:
        delta  = r["new_conf"] - r["prev_conf"]
        status = PASS if not r["low_conf"] else FAIL
        trend  = UP if delta > 0.01 else (DOWN if delta < -0.01 else EQ)
        if not r["low_conf"]:
            passed += 1
        print(
            f"  {r['id']:<12} {r['difficulty']:<7} "
            f"{r['prev_conf']:>6.4f}  {r['new_conf']:>6.4f}  "
            f"{trend} {delta:>+.4f}  {status}       {r['elapsed_ms']:>4}ms"
        )

    print("─" * 78)
    print(f"  Passed threshold: {passed}/{len(results)}")
    print("─" * 78 + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Confidence probe for the 9 previously low-confidence questions."
    )
    parser.add_argument(
        "--threshold", type=float,
        default=RETRIEVAL_CONFIG.confidence.low_confidence_threshold,
        help=f"Confidence threshold (default: {RETRIEVAL_CONFIG.confidence.low_confidence_threshold})",
    )
    args = parser.parse_args()

    results = asyncio.run(_probe(args.threshold))
    _print_table(results, args.threshold)


if __name__ == "__main__":
    main()
