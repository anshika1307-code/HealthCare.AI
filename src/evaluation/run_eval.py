"""
src/evaluation/run_eval.py
---------------------------
Evaluation runner for the Healthcare RAG system.

Loads eval_set.json, runs every question through the RAG pipeline, scores with
RAGAS, and writes a structured eval_report.json.  Exits with code 1 when
average faithfulness falls below 0.75 (CI gate).

Usage:
    python src/evaluation/run_eval.py
    python src/evaluation/run_eval.py --eval-set data/evaluation/eval_set.json
    python src/evaluation/run_eval.py --output reports/eval_20260518.json

Exit codes:
    0 — pass (avg faithfulness >= 0.70)
    1 — fail (avg faithfulness < 0.70) OR critical setup error

Architecture note
-----------------
Two-phase design — no nested event loops, no nest_asyncio:

  Phase 1 (async): asyncio.run(_pipeline_phase())
      Runs every question through the RAG graph. Qdrant is opened and
      FULLY CLOSED before this phase ends.

  Phase 2 (sync): _ragas_score()
      Called after asyncio.run() completes so there is NO running event loop.
      ragas.evaluate() creates its own clean event loop internally.

Environment:
    Requires OPENAI_API_KEY and a running Qdrant instance.
    Optional: QDRANT_URL (default http://localhost:6333), BM25_CORPUS_PATH.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import math
import os
import sys
import time
import warnings
from datetime import UTC, datetime
from pathlib import Path

# ── path setup ───────────────────────────────────────────────────────────────
_ROOT = Path(__file__).resolve().parents[2]
_SRC = _ROOT / "src"
for _p in (_SRC, _ROOT):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

try:
    from dotenv import load_dotenv

    load_dotenv(_ROOT / ".env")
except ImportError:
    pass

# ── third-party ───────────────────────────────────────────────────────────────
import openai
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from qdrant_client import AsyncQdrantClient

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    from ragas import EvaluationDataset, SingleTurnSample
    from ragas import evaluate as ragas_evaluate
    from ragas.dataset_schema import EvaluationResult as RagasEvaluationResult
    from ragas.metrics._answer_relevance import AnswerRelevancy
    from ragas.metrics._context_precision import ContextPrecision
    from ragas.metrics._context_recall import ContextRecall
    from ragas.metrics._faithfulness import Faithfulness

# ── project imports ───────────────────────────────────────────────────────────
from configs.embedding import EMBEDDING_CONFIG
from configs.llm import LLM_CONFIG
from configs.retrieval import RETRIEVAL_CONFIG

from embedding.openai_embedder import OpenAIEmbedder
from orchestration.graph import build_graph
from retrieval.bm25_retriever import BM25Retriever
from retrieval.confidence import ConfidenceScorer
from retrieval.dense_retriever import DenseRetriever
from retrieval.pipeline import RetrievalPipeline
from retrieval.reranker import CrossEncoderReranker
from retrieval.rrf_ranker import RRFRanker

# ── constants ─────────────────────────────────────────────────────────────────
FAITHFULNESS_THRESHOLD = 0.70
_DEFAULT_EVAL_SET = _ROOT / "data" / "evaluation" / "eval_set.json"
_DEFAULT_OUTPUT = _ROOT / "eval_report.json"
_DEFAULT_BM25_PATH = Path("data/cache/bm25_corpus.pkl")

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)

for _noisy in ("httpx", "httpcore", "openai", "ragas", "langchain", "sentence_transformers"):
    logging.getLogger(_noisy).setLevel(logging.WARNING)


# ─────────────────────────────────────────────────────────────────────────────
# PHASE 1 — async pipeline
# ─────────────────────────────────────────────────────────────────────────────


async def _build_pipeline():
    qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333").strip()
    qdrant_api_key = (os.getenv("QDRANT_API_KEY") or "").strip() or None
    bm25_path = Path(os.getenv("BM25_CORPUS_PATH", str(_DEFAULT_BM25_PATH)))

    qdrant = AsyncQdrantClient(url=qdrant_url, api_key=qdrant_api_key, check_compatibility=False)
    dense = DenseRetriever(qdrant, config=RETRIEVAL_CONFIG.dense)
    bm25 = BM25Retriever.from_cache(bm25_path, config=RETRIEVAL_CONFIG.bm25)
    reranker = CrossEncoderReranker(config=RETRIEVAL_CONFIG.reranker)
    rrf = RRFRanker(config=RETRIEVAL_CONFIG.rrf)
    confidence = ConfidenceScorer(config=RETRIEVAL_CONFIG.confidence)
    pipeline = RetrievalPipeline(dense, bm25, reranker, rrf, confidence)
    embedder = OpenAIEmbedder(EMBEDDING_CONFIG)
    llm_client = openai.AsyncOpenAI()
    graph = build_graph(embedder, pipeline, llm_client, LLM_CONFIG)
    return graph, qdrant


async def _run_question(graph, item: dict) -> dict:
    t0 = time.perf_counter()
    try:
        state = await graph.ainvoke({"query": item["question"], "query_id": item["id"]})
        latency_ms = (time.perf_counter() - t0) * 1000
        rr = state.get("retrieval_result")
        answer = state.get("answer", "")
        contexts = [c.text for c in rr.chunks] if rr else []
        conf = rr.confidence_score if rr else 0.0
        low_conf = rr.low_confidence if rr else True
        sources = [c.document_id for c in rr.chunks] if rr else []
        return {
            "id": item["id"],
            "question": item["question"],
            "ground_truth": item["ground_truth"],
            "section": item.get("section", ""),
            "difficulty": item.get("difficulty", ""),
            "source_doc": item.get("source_doc", ""),
            "answer": answer,
            "contexts": contexts,
            "confidence_score": conf,
            "low_confidence": low_conf,
            "sources": sources,
            "latency_ms": round(latency_ms, 1),
            "error": None,
        }
    except Exception as exc:  # noqa: BLE001
        latency_ms = (time.perf_counter() - t0) * 1000
        logger.warning("Question %s failed: %s", item["id"], exc)
        return {
            "id": item["id"],
            "question": item["question"],
            "ground_truth": item["ground_truth"],
            "section": item.get("section", ""),
            "difficulty": item.get("difficulty", ""),
            "source_doc": item.get("source_doc", ""),
            "answer": "",
            "contexts": [],
            "confidence_score": 0.0,
            "low_confidence": True,
            "sources": [],
            "latency_ms": round(latency_ms, 1),
            "error": str(exc),
        }


async def _pipeline_phase(eval_set: list[dict]) -> tuple[list[dict], float]:
    """Run all eval questions through the RAG graph. Returns (rows, elapsed_s)."""
    logger.info("Initialising RAG pipeline …")
    try:
        graph, qdrant = await _build_pipeline()
    except Exception as exc:
        logger.error("Pipeline init failed: %s", exc)
        raise

    t0 = time.perf_counter()
    rows: list[dict] = []
    try:
        for idx, item in enumerate(eval_set, start=1):
            logger.info(
                "[%d/%d] %s — %s",
                idx,
                len(eval_set),
                item["id"],
                item["question"][:70],
            )
            row = await _run_question(graph, item)
            rows.append(row)
            status = (
                f"error: {row['error']}"
                if row["error"]
                else f"conf={row['confidence_score']:.2f} ctx={len(row['contexts'])}"
            )
            logger.info("       → %s", status)
    finally:
        # Close Qdrant BEFORE returning — must be fully closed before
        # phase 2 (RAGAS) creates its own event loop
        await qdrant.close()

    elapsed = time.perf_counter() - t0
    logger.info(
        "Pipeline phase done: %d questions in %.1fs (avg %.1f s/q)",
        len(rows),
        elapsed,
        elapsed / max(len(rows), 1),
    )
    return rows, elapsed


# ─────────────────────────────────────────────────────────────────────────────
# PHASE 2 — synchronous RAGAS evaluation
# Called AFTER asyncio.run() finishes so RAGAS gets a fresh event loop.
# ─────────────────────────────────────────────────────────────────────────────


def _ragas_score(rows: list[dict]) -> tuple[dict[str, float], list[dict]]:
    """
    Build an EvaluationDataset from collected rows, run RAGAS evaluate(), and
    return (averages_dict, per_question_scores).
    Rows with empty contexts get 0.0 for all metrics.
    """
    scoreable = [r for r in rows if r["contexts"]]
    unscorable = [r for r in rows if not r["contexts"]]

    if unscorable:
        logger.warning(
            "%d question(s) had empty context — assigned 0.0 for all metrics",
            len(unscorable),
        )

    per_question: list[dict] = []

    if scoreable:
        # Cast to list[Sample] so EvaluationDataset's invariant type param is satisfied
        samples: list = [
            SingleTurnSample(
                user_input=r["question"],
                response=r["answer"],
                retrieved_contexts=r["contexts"],
                reference=r["ground_truth"],
            )
            for r in scoreable
        ]
        dataset = EvaluationDataset(samples=samples)
        metrics = [
            Faithfulness(),
            AnswerRelevancy(),
            ContextPrecision(),
            ContextRecall(),
        ]
        eval_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        eval_embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

        logger.info("Running RAGAS evaluation on %d questions …", len(scoreable))
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            raw_result = ragas_evaluate(
                dataset,
                metrics=metrics,
                llm=eval_llm,
                embeddings=eval_embeddings,
                show_progress=True,
            )
        # evaluate() returns EvaluationResult | Executor depending on return_executor flag
        # We use the default (return_executor=False) so it is always EvaluationResult
        assert isinstance(raw_result, RagasEvaluationResult), (
            f"Expected EvaluationResult, got {type(raw_result)}"
        )
        scores_df = raw_result.to_pandas()

        for i, row in enumerate(scoreable):
            q = scores_df.iloc[i]
            per_question.append(
                {
                    **_row_meta(row),
                    "faithfulness": _safe_float(q.get("faithfulness")),
                    "answer_relevancy": _safe_float(q.get("answer_relevancy")),
                    "context_precision": _safe_float(q.get("context_precision")),
                    "context_recall": _safe_float(q.get("context_recall")),
                }
            )

    for row in unscorable:
        per_question.append(
            {
                **_row_meta(row),
                "faithfulness": 0.0,
                "answer_relevancy": 0.0,
                "context_precision": 0.0,
                "context_recall": 0.0,
            }
        )

    # Restore original question order
    id_order = {r["id"]: i for i, r in enumerate(rows)}
    per_question.sort(key=lambda r: id_order.get(r["id"], 999))

    metric_keys = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
    averages: dict[str, float] = {
        m: round(sum(r[m] for r in per_question) / max(len(per_question), 1), 4)
        for m in metric_keys
    }
    return averages, per_question


def _row_meta(row: dict) -> dict:
    return {
        k: row[k]
        for k in (
            "id",
            "question",
            "ground_truth",
            "section",
            "difficulty",
            "source_doc",
            "answer",
            "confidence_score",
            "low_confidence",
            "sources",
            "latency_ms",
            "error",
        )
    }


def _safe_float(val) -> float:
    if val is None:
        return 0.0
    try:
        f = float(val)
        return 0.0 if math.isnan(f) else round(f, 4)
    except (TypeError, ValueError):
        return 0.0


# ─────────────────────────────────────────────────────────────────────────────
# Orchestration
# ─────────────────────────────────────────────────────────────────────────────


def _print_summary(averages: dict, per_question: list[dict]) -> None:
    print("\n" + "─" * 60)
    print("RAGAS EVALUATION SUMMARY")
    print("─" * 60)
    for metric, score in averages.items():
        flag = ""
        if metric == "faithfulness" and score < FAITHFULNESS_THRESHOLD:
            flag = f"  ← BELOW threshold ({FAITHFULNESS_THRESHOLD})"
        print(f"  {metric:<22} {score:.4f}{flag}")
    print("─" * 60)
    for diff in ("easy", "medium", "hard"):
        group = [r for r in per_question if r["difficulty"] == diff]
        if group:
            avg_f = sum(r["faithfulness"] for r in group) / len(group)
            print(f"  faithfulness [{diff:<6}]: {avg_f:.4f}  (n={len(group)})")
    print("─" * 60 + "\n")


def _ragas_version() -> str:
    try:
        import ragas

        return getattr(ragas, "__version__", "unknown")
    except ImportError:
        return "unknown"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run RAGAS evaluation against the Healthcare RAG pipeline."
    )
    parser.add_argument(
        "--eval-set",
        type=Path,
        default=_DEFAULT_EVAL_SET,
        help=f"Path to eval_set.json (default: {_DEFAULT_EVAL_SET})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=_DEFAULT_OUTPUT,
        help=f"Output path for eval_report.json (default: {_DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--rows-cache",
        type=Path,
        default=None,
        help="Save pipeline rows to this file after Phase 1 (auto: <output>.rows.json)",
    )
    parser.add_argument(
        "--from-cache",
        type=Path,
        default=None,
        metavar="ROWS_FILE",
        help="Skip Phase 1 — load pipeline rows from a previous cache file and go straight to RAGAS scoring.",
    )
    args = parser.parse_args()

    # Derive default cache path alongside the output file
    rows_cache_path: Path = args.rows_cache or args.output.with_suffix(".rows.json")

    if args.from_cache:
        # ── Resume mode: skip pipeline, load saved rows ───────────────────────
        if not args.from_cache.exists():
            logger.error("Rows cache not found: %s", args.from_cache)
            sys.exit(1)
        cached = json.loads(args.from_cache.read_text(encoding="utf-8"))
        rows: list[dict] = cached["rows"]
        pipeline_s: float = cached.get("pipeline_time_s", 0.0)
        logger.info(
            "Loaded %d cached rows from %s (skipping pipeline)",
            len(rows),
            args.from_cache,
        )
    else:
        # ── Normal mode: run pipeline then cache rows ─────────────────────────
        if not args.eval_set.exists():
            logger.error("Eval set not found: %s", args.eval_set)
            sys.exit(1)

        eval_set: list[dict] = json.loads(args.eval_set.read_text(encoding="utf-8"))
        logger.info("Loaded %d questions from %s", len(eval_set), args.eval_set)

        # Phase 1: async pipeline (opens + closes Qdrant)
        try:
            rows, pipeline_s = asyncio.run(_pipeline_phase(eval_set))
        except Exception as exc:
            logger.error("Pipeline phase failed: %s", exc)
            sys.exit(1)

        # Save rows so RAGAS phase can be retried without re-running the pipeline
        rows_cache_path.parent.mkdir(parents=True, exist_ok=True)
        rows_cache_path.write_text(
            json.dumps(
                {"pipeline_time_s": round(pipeline_s, 1), "rows": rows},
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        logger.info(
            "Pipeline rows cached → %s  (use --from-cache to skip pipeline next time)",
            rows_cache_path,
        )

    # ── Phase 2: RAGAS scoring (synchronous; fresh event loop) ───────────────
    averages, per_question = _ragas_score(rows)

    # ── Write report ──────────────────────────────────────────────────────────
    report = {
        "metadata": {
            "timestamp": datetime.now(UTC).isoformat(),
            "eval_set": str(args.eval_set if not args.from_cache else args.from_cache),
            "num_questions": len(rows),
            "errors": sum(1 for r in rows if r["error"]),
            "ragas_version": _ragas_version(),
            "pipeline_time_s": round(pipeline_s, 1),
        },
        "thresholds": {"faithfulness": FAITHFULNESS_THRESHOLD},
        "averages": averages,
        "per_question": per_question,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Report written → %s", args.output)

    _print_summary(averages, per_question)

    # ── CI exit code ──────────────────────────────────────────────────────────
    avg_faithfulness = averages.get("faithfulness", 0.0)
    if avg_faithfulness < FAITHFULNESS_THRESHOLD:
        logger.error(
            "FAIL: avg_faithfulness=%.4f < threshold=%.2f — deploy blocked",
            avg_faithfulness,
            FAITHFULNESS_THRESHOLD,
        )
        sys.exit(1)

    logger.info(
        "PASS: avg_faithfulness=%.4f >= threshold=%.2f",
        avg_faithfulness,
        FAITHFULNESS_THRESHOLD,
    )


if __name__ == "__main__":
    main()
