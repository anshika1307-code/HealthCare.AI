"""
scripts/run_ingestion.py
-------------------------
End-to-end ingestion runner: PDF → preprocess → embed → Qdrant → BM25.

Iterates DOCUMENTS from configs/ingestion.py. Each doc is preprocessed,
embedded, and upserted into Qdrant. After all docs succeed, the BM25
corpus is built inline. All metrics are logged to MLflow.

Usage:
    python scripts/run_ingestion.py
    python scripts/run_ingestion.py --provider bge
    python scripts/run_ingestion.py --dry-run
    python scripts/run_ingestion.py --mlflow-run-name openai_baseline_v1

Flags:
    --provider        openai | bge  (default: from configs/embedding.py)
    --collection      Qdrant collection name
    --mlflow-run-name Name for this MLflow run
    --dry-run         Preprocess + embed first batch only — no Qdrant writes
"""

from __future__ import annotations

import argparse
import datetime
import logging
import os
import subprocess
import sys
import time
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_REPO_ROOT / "src"))

try:
    from dotenv import load_dotenv

    load_dotenv(_REPO_ROOT / ".env")
except ImportError:
    pass  # fall back to env vars already set in the shell

import mlflow
from configs.embedding import EMBEDDING_CONFIG
from configs.ingestion import DOCUMENTS
from configs.retrieval import RETRIEVAL_CONFIG
from qdrant_client import QdrantClient
from src.embedding.base import make_indexable
from src.embedding.indexer import QdrantIndexer
from src.ingestion.config import get_doc_config
from src.ingestion.preprocessor import PreprocessingPipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")


def _build_embedder(provider: str):
    if provider == "openai":
        from src.embedding.openai_embedder import OpenAIEmbedder

        return OpenAIEmbedder(EMBEDDING_CONFIG)
    elif provider == "bge":
        from src.embedding.bge_embedder import BGEEmbedder

        return BGEEmbedder(EMBEDDING_CONFIG)
    raise ValueError(f"Unknown provider {provider!r}. Choose 'openai' or 'bge'.")


def _git_sha() -> str:
    try:
        import git

        return git.Repo(_REPO_ROOT).head.commit.hexsha[:8]
    except Exception:
        return "unknown"


def _build_bm25_index() -> None:
    script = _REPO_ROOT / "scripts" / "build_bm25_index.py"
    result = subprocess.run([sys.executable, str(script)], cwd=str(_REPO_ROOT))
    if result.returncode != 0:
        logger.error("build_bm25_index.py exited with code %d", result.returncode)
        sys.exit(result.returncode)


def run(
    provider: str,
    collection_name: str,
    mlflow_run_name: str | None,
    dry_run: bool,
) -> None:
    embedder = _build_embedder(provider)
    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    indexer = QdrantIndexer(client, collection_name)
    pipeline = PreprocessingPipeline(max_tokens=512, overlap_tokens=64)

    mlflow.set_experiment(EMBEDDING_CONFIG.mlflow_experiment_name)
    run_name = mlflow_run_name or f"{provider}_ingestion"

    total_chunks = 0
    total_embed_time = 0.0
    total_batches = 0
    failed_batches = 0
    any_doc_failed = False

    with mlflow.start_run(run_name=run_name) as mlrun:
        mlflow.log_params(
            {
                "embedding_model": embedder.model_name,
                "provider": provider,
                "dimensions": embedder.dimensions,
                "batch_size": EMBEDDING_CONFIG.batch_size,
                "normalize": EMBEDDING_CONFIG.normalize,
                "total_docs": len(DOCUMENTS),
            }
        )
        mlflow.set_tags(
            {
                "run_date": datetime.datetime.utcnow().isoformat(),
                "git_sha": _git_sha(),
            }
        )

        for entry in DOCUMENTS:
            pdf_path = _REPO_ROOT / entry.pdf_path

            if not pdf_path.exists():
                logger.error("PDF not found: %s — skipping.", pdf_path)
                any_doc_failed = True
                continue

            logger.info("=== %s (%s) ===", entry.doc_id, pdf_path.name)

            try:
                chunks = pipeline.run(entry.doc_id, pdf_path)
            except Exception as exc:
                logger.error("Preprocessing failed for %s: %s", entry.doc_id, exc)
                any_doc_failed = True
                continue

            if not chunks:
                logger.warning("No chunks produced for %s — skipping.", entry.doc_id)
                continue

            # Inject doc_type into metadata so the Qdrant payload is populated.
            # The chunker's _base_meta() doesn't include doc_type; we pull it
            # from the doc registry and stamp it here before make_indexable().
            doc_type = get_doc_config(entry.doc_id)["doc_type"]
            for chunk in chunks:
                chunk.metadata["doc_type"] = doc_type

            indexable = make_indexable(chunks, entry.doc_id)
            texts = [c.text for c in indexable]

            if dry_run:
                cap = EMBEDDING_CONFIG.batch_size
                logger.info(
                    "[dry-run] Embedding first %d of %d chunks", min(cap, len(texts)), len(texts)
                )
                texts = texts[:cap]
                indexable = indexable[:cap]

            logger.info("Embedding %d chunks…", len(texts))
            t0 = time.perf_counter()
            try:
                vectors = embedder.embed_batch(texts)
            except Exception as exc:
                logger.error("Embedding failed for %s: %s", entry.doc_id, exc)
                any_doc_failed = True
                failed_batches += 1
                continue

            elapsed = time.perf_counter() - t0
            total_embed_time += elapsed
            total_batches += max(
                1, (len(texts) + EMBEDDING_CONFIG.batch_size - 1) // EMBEDDING_CONFIG.batch_size
            )

            if dry_run:
                logger.info("[dry-run] Skipping Qdrant upsert for %s.", entry.doc_id)
                total_chunks += len(vectors)
                continue

            success, failed_ids = indexer.upsert(indexable, vectors)
            total_chunks += success
            if failed_ids:
                failed_batches += 1
                logger.warning("%d chunks failed to upsert for %s", len(failed_ids), entry.doc_id)

        avg_batch_time = total_embed_time / total_batches if total_batches else 0.0
        mlflow.log_metrics(
            {
                "total_chunks_indexed": total_chunks,
                "total_embedding_time_s": round(total_embed_time, 3),
                "avg_batch_time_s": round(avg_batch_time, 3),
                "failed_batches": failed_batches,
            }
        )
        logger.info(
            "Ingestion complete: %d chunks indexed, %.1fs embed time, MLflow run=%s",
            total_chunks,
            total_embed_time,
            mlrun.info.run_id,
        )

    if not dry_run and not any_doc_failed:
        logger.info("Building BM25 index...")
        _build_bm25_index()

    if any_doc_failed:
        logger.error("One or more documents failed — see logs above.")
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest PDFs: preprocess → embed → Qdrant → BM25.")
    parser.add_argument(
        "--provider",
        choices=["openai", "bge"],
        default=EMBEDDING_CONFIG.provider,
        help="Embedding provider (default: from configs/embedding.py)",
    )
    parser.add_argument(
        "--collection",
        default=RETRIEVAL_CONFIG.dense.collection_name,
        help="Qdrant collection name (default: from configs/retrieval.py)",
    )
    parser.add_argument(
        "--mlflow-run-name",
        default=None,
        help="MLflow run name (default: <provider>_ingestion)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preprocess + embed first batch only, skip all Qdrant writes",
    )
    args = parser.parse_args()

    run(
        provider=args.provider,
        collection_name=args.collection,
        mlflow_run_name=args.mlflow_run_name,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
