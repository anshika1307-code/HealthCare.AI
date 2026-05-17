"""
scripts/build_bm25_index.py
----------------------------
One-time script: fetch all chunks from Qdrant, tokenise, and save as a
BM25Corpus pickle.  Run this once after ingestion completes.

Usage:
    python scripts/build_bm25_index.py
    python scripts/build_bm25_index.py --collection healthcare_chunks --output data/cache/bm25_corpus.pkl

The generated pickle is loaded by BM25Retriever.from_cache() at server startup.
"""
from __future__ import annotations

import argparse
import logging
import os
import pickle
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]

try:
    from dotenv import load_dotenv
    load_dotenv(_REPO_ROOT / ".env")
except ImportError:
    pass  # fall back to env vars already set in the shell

# Make both src/ and repo root importable (configs/ lives at repo root, not src/)
sys.path.insert(0, str(_REPO_ROOT / "src"))
sys.path.insert(0, str(_REPO_ROOT))

from qdrant_client import QdrantClient

from configs.retrieval import RETRIEVAL_CONFIG
from retrieval.bm25_retriever import BM25Corpus

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

QDRANT_URL     = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
DEFAULT_BATCH = 200


def build_index(collection_name: str, output_path: Path) -> None:
    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

    chunk_ids: list[str] = []
    chunk_texts: list[str] = []
    chunk_payloads: list[dict] = []
    tokenised_corpus: list[list[str]] = []

    logger.info("Fetching all points from collection: %s", collection_name)
    offset = None
    total = 0

    while True:
        records, next_offset = client.scroll(
            collection_name=collection_name,
            scroll_filter=None,
            limit=DEFAULT_BATCH,
            offset=offset,
            with_payload=True,
            with_vectors=False,  # we only need metadata + text, not vectors
        )
        if not records:
            break

        for record in records:
            payload = record.payload or {}
            text: str = payload.get("text", "")
            if not text:
                continue  # skip chunks without text (shouldn't happen)

            chunk_ids.append(str(record.id))
            chunk_texts.append(text)
            chunk_payloads.append(payload)
            tokenised_corpus.append(text.lower().split())  # whitespace tokeniser

        total += len(records)
        logger.info("Fetched %d points so far...", total)

        if next_offset is None:
            break
        offset = next_offset

    if not chunk_ids:
        logger.error("No chunks found in collection %r — is ingestion complete?", collection_name)
        sys.exit(1)

    corpus = BM25Corpus(
        chunk_ids=chunk_ids,
        tokenised_corpus=tokenised_corpus,
        chunk_texts=chunk_texts,
        chunk_payloads=chunk_payloads,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as fh:
        pickle.dump(corpus, fh, protocol=pickle.HIGHEST_PROTOCOL)

    logger.info(
        "BM25 corpus saved: %d chunks → %s (%.1f KB)",
        len(chunk_ids), output_path, output_path.stat().st_size / 1024,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Build BM25 corpus index from Qdrant.")
    parser.add_argument(
        "--collection",
        default=RETRIEVAL_CONFIG.dense.collection_name,
        help="Qdrant collection name (default: from configs/retrieval.py)",
    )
    parser.add_argument(
        "--output",
        default=RETRIEVAL_CONFIG.bm25.corpus_cache_path,
        help="Output pickle path (default: from configs/retrieval.py)",
    )
    args = parser.parse_args()

    build_index(
        collection_name=args.collection,
        output_path=Path(args.output),
    )


if __name__ == "__main__":
    main()
