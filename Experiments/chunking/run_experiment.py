"""
run_experiment.py
-----------------
Chunking experiment runner.

Tests 3 strategies x 3 token sizes = 9 configurations.
For each configuration:
  1. Chunk all 4 documents
  2. Build an in-memory numpy vector index (sentence-transformers, LOCAL)
  3. Retrieve top-k context for each eval question
  4. Generate answers via LLM (Groq free / OpenAI)
  5. Score with proxy metrics (or RAGAS if installed)
  6. Log all metrics + config to MLflow

Usage
-----
    python experiments/chunking/run_experiment.py
    python experiments/chunking/run_experiment.py --strategy boundary_aware

LLM Provider (auto-detected, first match wins)
----------------------------------------------
    GROQ_API_KEY   set  -> Groq  (free, fast, recommended)
    OPENAI_API_KEY set  -> OpenAI gpt-4o-mini (~$0.76 total)
    neither set         -> raises RuntimeError with setup instructions
"""

from __future__ import annotations

import os
import sys
import json
import logging
import argparse
import numpy as np
from pathlib import Path
from datetime import datetime

# ── path bootstrap ────────────────────────────────────────────────────────────
_ROOT = Path(__file__).resolve().parents[2]
_SRC = _ROOT / "src"
for p in [str(_SRC), str(_ROOT / "experiments" / "chunking")]:
    if p not in sys.path:
        sys.path.insert(0, p)

# ── load .env ─────────────────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv(_ROOT / ".env")
except ImportError:
    pass

import mlflow
import mlflow.data
from openai import OpenAI
from sentence_transformers import SentenceTransformer
from datasets import Dataset

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("chunking_experiment")

# ── RAGAS (optional — falls back to lightweight metrics if unavailable) ────────
try:
    from ragas import evaluate as ragas_evaluate
    from ragas.metrics import (
        _Faithfulness as RagasFaithfulness,
        _ResponseRelevancy as RagasAnswerRelevancy,
        _LLMContextPrecisionWithReference as RagasContextPrecision,
        _LLMContextRecall as RagasContextRecall,
    )
    from ragas.dataset_schema import EvaluationDataset, SingleTurnSample
    from ragas.llms import llm_factory
    from ragas.embeddings import embedding_factory
    _RAGAS_AVAILABLE = True
    logger.info("RAGAS 0.4.x available — will run full LLM-judge metrics")
except (ImportError, Exception) as e:
    _RAGAS_AVAILABLE = False
    logger.warning(
        f"ragas not available or incompatible ({e}) — using lightweight proxy metrics."
    )

from strategies import STRATEGIES
from eval_loader import load_eval_questions

# ── constants ─────────────────────────────────────────────────────────────────
TOKEN_SIZES = [256, 512, 1024]
TOP_K = 5                     # chunks retrieved per question
MLFLOW_EXPERIMENT = "chunking_strategy_eval"
RESULTS_DIR = _ROOT / "experiments" / "chunking" / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# Map doc_id → PDF filename (must match data/raw/)
DOC_MAP: dict[str, str] = {
    "metformin_fda_label": "metformin_fda_label.pdf",
    "ada_standards_care_diabetes_6": "ada_standards_care_diabetes_6.pdf",
    "ada_standards_care_diabetes_9": "ada_standards_care_diabetes_9.pdf",
    "jnc8_guidelines_manage_hypertension_original": "jnc8_guidelines_manage_hypertension_original.pdf",
}

# Normalise source_doc strings in eval set → doc_id keys
_SOURCE_TO_DOCID: dict[str, str] = {
    "metformin_fda_label.pdf": "metformin_fda_label",
    "ada_standards_care_diabetes_6.pdf": "ada_standards_care_diabetes_6",
    "ada_standards_care_diabetes_section6.pdf": "ada_standards_care_diabetes_6",
    "ada_standards_care_diabetes_9.pdf": "ada_standards_care_diabetes_9",
    "ada_standards_care_diabetes_section9.pdf": "ada_standards_care_diabetes_9",
    "jnc8_guidelines_management_hypertension_original.pdf": "jnc8_guidelines_manage_hypertension_original",
    "jnc8_guidelines_manage_hypertension_original.pdf": "jnc8_guidelines_manage_hypertension_original",
    "all_docs": None,   # cross-document questions — use all docs
}


# =============================================================================
# Embedding & Retrieval helpers
# =============================================================================

class InMemoryRetriever:
    """Lightweight numpy-based cosine retriever."""

    def __init__(self, model: SentenceTransformer) -> None:
        self.model = model
        self.embeddings: np.ndarray | None = None
        self.chunks: list[dict] = []

    def index(self, chunks: list[dict]) -> None:
        self.chunks = chunks
        texts = [c["text"] for c in chunks]
        logger.info("Encoding %d chunks…", len(texts))
        self.embeddings = self.model.encode(
            texts, batch_size=64, show_progress_bar=False, normalize_embeddings=True
        )

    def retrieve(self, query: str, top_k: int = TOP_K) -> list[str]:
        if self.embeddings is None or not self.chunks:
            return []
        q_emb = self.model.encode([query], normalize_embeddings=True)
        scores = (self.embeddings @ q_emb.T).squeeze()
        top_idx = np.argsort(scores)[::-1][:top_k]
        return [self.chunks[i]["text"] for i in top_idx]


# =============================================================================
# LLM Client Factory — Groq (free) preferred, OpenAI fallback
# =============================================================================

_LLM_PROVIDERS = {
    "groq": {
        "env_key":  "GROQ_API_KEY",
        "base_url": "https://api.groq.com/openai/v1",
        "model":    "llama-3.1-8b-instant",   # 20K TPM free, fast
        "rpm":      30,                         # free tier rate limit
    },
    "openai": {
        "env_key":  "OPENAI_API_KEY",
        "base_url": None,                       # default OpenAI endpoint
        "model":    "gpt-4o-mini",
        "rpm":      500,
    },
}


def build_llm_client() -> tuple["OpenAI", str, str, int]:
    """
    Auto-detect available LLM provider (Groq first, OpenAI fallback).

    Returns
    -------
    client      : OpenAI-compatible client
    model_name  : str
    provider    : str  ("groq" | "openai")
    rpm_limit   : int  (requests per minute — for rate-limit sleep)
    """
    for provider_name, cfg in _LLM_PROVIDERS.items():
        api_key = os.getenv(cfg["env_key"])
        if api_key:
            kwargs = {"api_key": api_key}
            if cfg["base_url"]:
                kwargs["base_url"] = cfg["base_url"]
            client = OpenAI(**kwargs)
            logger.info(
                "LLM provider: %s  model: %s  (rpm_limit=%d)",
                provider_name.upper(), cfg["model"], cfg["rpm"],
            )
            return client, cfg["model"], provider_name, cfg["rpm"]

    raise RuntimeError(
        "No LLM API key found. Set one of:\n"
        "  GROQ_API_KEY   (free)  — get at https://console.groq.com\n"
        "  OPENAI_API_KEY (paid)  — get at https://platform.openai.com"
    )


# =============================================================================
# Answer generation
# =============================================================================

import time

def generate_answer(client: "OpenAI", question: str, contexts: list[str], model: str) -> str:
    context_block = "\n\n---\n\n".join(contexts)
    prompt = (
        "You are a clinical AI assistant. Answer the question ONLY from the provided context. "
        "If the context does not contain enough information, say 'Insufficient context to answer.' "
        "Cite the relevant document section when possible.\n\n"
        f"Context:\n{context_block}\n\n"
        f"Question: {question}\n\nAnswer:"
    )
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=300,
    )
    return resp.choices[0].message.content.strip()


# =============================================================================
# Lightweight proxy metrics (used when RAGAS is unavailable)
# =============================================================================

def _token_overlap(text_a: str, text_b: str) -> float:
    """Jaccard token overlap between two strings."""
    a = set(text_a.lower().split())
    b = set(text_b.lower().split())
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _proxy_metrics(ragas_data: list[dict]) -> dict:
    """
    Proxy RAGAS-like scores computed without the ragas library.

    context_recall_proxy   : keyword overlap between ground_truth and retrieved contexts
    context_precision_proxy: fraction of contexts containing at least one ground_truth keyword
    faithfulness_proxy     : overlap between answer and concatenated contexts
    answer_relevancy_proxy : overlap between answer and question
    """
    ctx_recall, ctx_precision, faithfulness_, ans_relevancy = [], [], [], []

    for row in ragas_data:
        question = row["question"]
        answer = row["answer"]
        ground_truth = row["ground_truth"]
        contexts = row["contexts"]
        ctx_text = " ".join(contexts)

        # context_recall: how much of the ground truth is present in the retrieved contexts
        ctx_recall.append(_token_overlap(ground_truth, ctx_text))

        # context_precision: what fraction of contexts contain at least one gt keyword
        gt_words = set(ground_truth.lower().split())
        prec = sum(
            1 for c in contexts
            if gt_words & set(c.lower().split())
        ) / len(contexts) if contexts else 0.0
        ctx_precision.append(prec)

        # faithfulness: answer grounded in contexts
        faithfulness_.append(_token_overlap(answer, ctx_text))

        # answer_relevancy: question words present in answer
        ans_relevancy.append(_token_overlap(question, answer))

    def _mean(lst: list) -> float:
        return float(sum(lst) / len(lst)) if lst else 0.0

    return {
        "context_recall": _mean(ctx_recall),
        "context_precision": _mean(ctx_precision),
        "faithfulness": _mean(faithfulness_),
        "answer_relevancy": _mean(ans_relevancy),
        "metric_source": 0.0,   # 0 = proxy, 1 = RAGAS (for MLflow tracking)
    }


# =============================================================================
# Single experiment run
# =============================================================================

def run_single_experiment(
    strategy_name: str,
    token_size: int,
    all_chunks_by_docid: dict[str, list[dict]],
    eval_questions: list[dict],
    embed_model: SentenceTransformer,
    llm_client: "OpenAI",
    llm_model: str,
    rpm_limit: int = 30,
) -> dict:
    """
    Run one configuration (strategy x token_size), return scores.
    """
    logger.info("Strategy=%s  TokenSize=%d", strategy_name, token_size)
    _sleep = 60.0 / rpm_limit   # seconds between calls to respect rate limit

    # Build one flat index over all documents for this config
    all_chunks: list[dict] = []
    for chunks in all_chunks_by_docid.values():
        all_chunks.extend(chunks)

    retriever = InMemoryRetriever(embed_model)
    retriever.index(all_chunks)

    # Checkpoint: reuse saved answers if they exist (avoids re-running LLM calls)
    out_file = RESULTS_DIR / f"{strategy_name}_{token_size}_ragas_data.json"
    if out_file.exists():
        logger.info("Checkpoint found — loading saved answers from %s", out_file.name)
        with open(out_file, encoding="utf-8") as f:
            ragas_data = json.load(f)
    else:
        ragas_data: list[dict] = []
        for eq in eval_questions:
            question = eq["question"]
            expected = eq.get("expected_answer_contains", "")

            contexts = retriever.retrieve(question, top_k=TOP_K)
            if not contexts:
                continue

            answer = generate_answer(llm_client, question, contexts, llm_model)
            time.sleep(_sleep)   # respect rate limit

            ragas_data.append({
                "question": question,
                "answer": answer,
                "contexts": contexts,
                "ground_truth": expected,
            })

        if not ragas_data:
            logger.warning("No RAGAS data produced for %s/%d", strategy_name, token_size)
            return {}

        # Save immediately so a RAGAS crash doesn't lose the LLM calls
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(ragas_data, f, indent=2, ensure_ascii=False)
        logger.info("Answers saved to %s", out_file.name)

    dataset = Dataset.from_list(ragas_data)

    if _RAGAS_AVAILABLE:
        logger.info("Running RAGAS LLM-judge on %d questions...", len(ragas_data))
        # Build EvaluationDataset (ragas 0.4.x schema)
        samples = [
            SingleTurnSample(
                user_input=r["question"],
                response=r["answer"],
                retrieved_contexts=r["contexts"],
                reference=r["ground_truth"],
            )
            for r in ragas_data
        ]
        eval_dataset = EvaluationDataset(samples=samples)

        # LLM via Groq (free), embeddings via OpenAI text-embedding-3-small (~$0.001 total)
        ragas_llm = llm_factory(llm_model, client=llm_client)
        ragas_emb = embedding_factory("text-embedding-3-small")
        result = ragas_evaluate(
            dataset=eval_dataset,
            metrics=[
                RagasFaithfulness(llm=ragas_llm),
                RagasAnswerRelevancy(llm=ragas_llm, embeddings=ragas_emb),
                RagasContextPrecision(llm=ragas_llm),
                RagasContextRecall(llm=ragas_llm),
            ],
            show_progress=True,
        )
        scores = {
            "faithfulness": float(np.nanmean(result["faithfulness"])),
            "answer_relevancy": float(np.nanmean(result["answer_relevancy"])),
            "context_precision": float(np.nanmean(result["llm_context_precision_with_reference"])),
            "context_recall": float(np.nanmean(result["context_recall"])),
            "metric_source": 1.0,
        }
    else:
        # ── Lightweight proxy metrics (no RAGAS dependency) ───────────────
        logger.info("Computing proxy metrics on %d questions…", len(ragas_data))
        scores = _proxy_metrics(ragas_data)
    scores["mean_score"] = sum(scores.values()) / len(scores)

    # Chunk stats
    sizes = [len(c["text"].split()) for c in all_chunks]
    scores["total_chunks"] = len(all_chunks)
    scores["mean_chunk_words"] = float(np.mean(sizes)) if sizes else 0
    scores["median_chunk_words"] = float(np.median(sizes)) if sizes else 0
    scores["std_chunk_words"] = float(np.std(sizes)) if sizes else 0

    logger.info(
        "  faithfulness=%.3f  answer_relevancy=%.3f  "
        "context_precision=%.3f  context_recall=%.3f  mean=%.3f",
        scores["faithfulness"], scores["answer_relevancy"],
        scores["context_precision"], scores["context_recall"],
        scores["mean_score"],
    )

    return scores


# =============================================================================
# Main
# =============================================================================

def main(strategies_to_run: list[str] | None = None, max_questions: int | None = None) -> None:
    llm_client, llm_model, provider, rpm_limit = build_llm_client()

    logger.info("Loading embedding model (BAAI/bge-small-en-v1.5, LOCAL)...")
    embed_model = SentenceTransformer("BAAI/bge-small-en-v1.5")

    # Load eval questions (optionally capped for faster runs)
    eval_dir = _ROOT / "data" / "evaluation"
    eval_questions = load_eval_questions(eval_dir)
    if max_questions and len(eval_questions) > max_questions:
        # Sample evenly across documents so all docs are represented
        import random
        random.seed(42)
        eval_questions = random.sample(eval_questions, max_questions)
    logger.info("Using %d eval questions", len(eval_questions))

    # MLflow setup — use file:// URI so Windows drive letters don't break it
    mlruns_dir = _ROOT / "experiments" / "chunking" / "mlruns"
    mlflow.set_tracking_uri(mlruns_dir.as_uri())   # file:///F:/... on Windows
    mlflow.set_experiment(MLFLOW_EXPERIMENT)

    strategies_to_run = strategies_to_run or list(STRATEGIES.keys())
    raw_dir = _ROOT / "data" / "raw"

    all_results: list[dict] = []

    for strategy_name in strategies_to_run:
        strategy_fn = STRATEGIES[strategy_name]

        for token_size in TOKEN_SIZES:
            run_name = f"{strategy_name}_{token_size}tok_{datetime.now().strftime('%H%M%S')}"

            # ── 1. Generate chunks for all docs ──────────────────────────────
            logger.info("Chunking documents: strategy=%s size=%d", strategy_name, token_size)
            all_chunks_by_docid: dict[str, list[dict]] = {}
            for doc_id, fname in DOC_MAP.items():
                pdf_path = raw_dir / fname
                if not pdf_path.exists():
                    logger.warning("PDF not found: %s — skipping", pdf_path)
                    continue
                try:
                    chunks = strategy_fn(doc_id=doc_id, pdf_path=str(pdf_path), token_size=token_size)
                    all_chunks_by_docid[doc_id] = chunks
                    logger.info("  %s: %d chunks", doc_id, len(chunks))
                except Exception as exc:
                    logger.error("  Failed chunking %s: %s", doc_id, exc, exc_info=True)

            # Save chunk stats per config
            chunk_counts = {k: len(v) for k, v in all_chunks_by_docid.items()}

            # ── 2. Evaluate ───────────────────────────────────────────────────
            with mlflow.start_run(run_name=run_name):
                # Log params
                mlflow.log_params({
                    "strategy": strategy_name,
                    "token_size": token_size,
                    "top_k": TOP_K,
                    "embed_model": "BAAI/bge-small-en-v1.5",
                    "llm_model": llm_model,
                    "llm_provider": provider,
                    "num_eval_questions": len(eval_questions),
                    **{f"chunks_{k}": v for k, v in chunk_counts.items()},
                })

                try:
                    scores = run_single_experiment(
                        strategy_name=strategy_name,
                        token_size=token_size,
                        all_chunks_by_docid=all_chunks_by_docid,
                        eval_questions=eval_questions,
                        embed_model=embed_model,
                        llm_client=llm_client,
                        llm_model=llm_model,
                        rpm_limit=rpm_limit,
                    )

                    if scores:
                        mlflow.log_metrics(scores)
                        result_row = {
                            "strategy": strategy_name,
                            "token_size": token_size,
                            **scores,
                        }
                        all_results.append(result_row)
                        mlflow.log_dict(result_row, "summary.json")

                        # Log raw RAGAS data as MLflow artifact
                        raw_file = RESULTS_DIR / f"{strategy_name}_{token_size}_ragas_data.json"
                        if raw_file.exists():
                            mlflow.log_artifact(str(raw_file))

                except Exception as exc:
                    logger.error("Run failed: %s", exc, exc_info=True)
                    mlflow.set_tag("status", "FAILED")
                    mlflow.set_tag("error", str(exc))

    # ── 3. Summary table ──────────────────────────────────────────────────────
    summary_path = RESULTS_DIR / "summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2)

    logger.info("\n=== EXPERIMENT COMPLETE ===")
    logger.info("Results: %s", summary_path)
    logger.info(
        "MLflow UI: mlflow ui --backend-store-uri %s",
        mlruns_dir.as_uri(),
    )

    if all_results:
        best = max(all_results, key=lambda r: r.get("mean_score", 0))
        logger.info(
            "Best config: strategy=%s  token_size=%d  mean_score=%.3f",
            best["strategy"], best["token_size"], best["mean_score"],
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chunking strategy experiment")
    parser.add_argument(
        "--strategy",
        choices=list(STRATEGIES.keys()),
        default=None,
        help="Run only this strategy (default: all)",
    )
    parser.add_argument(
        "--max-questions",
        type=int,
        default=None,
        dest="max_questions",
        help="Cap the number of eval questions (sampled evenly). Default: use all.",
    )
    args = parser.parse_args()
    strategies = [args.strategy] if args.strategy else None
    main(strategies, max_questions=args.max_questions)
