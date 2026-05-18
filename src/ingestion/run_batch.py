"""
src/ingestion/run_batch.py
---------------------------
CI/CD batch ingestion: process PDFs from a directory, embed them, upsert into
Qdrant, then rebuild the BM25 corpus.

Designed for CI where test fixtures mirror the production PDFs (same filenames,
same doc_ids). Supports a --force-recreate flag to wipe and rebuild the Qdrant
collection from scratch.

Usage:
    python src/ingestion/run_batch.py --docs tests/fixtures/
    python src/ingestion/run_batch.py --docs data/raw/ --force-recreate
    python src/ingestion/run_batch.py --docs tests/fixtures/ --collection healthcare_chunks_ci

Exit codes:
    0 — all docs ingested successfully, BM25 index built
    1 — one or more docs failed, or Qdrant/BM25 setup failed

Environment:
    OPENAI_API_KEY   — required for embedding
    QDRANT_URL       — default http://localhost:6333
    QDRANT_API_KEY   — optional
"""
from __future__ import annotations

import argparse
import logging
import os
import pickle
import sys
import time
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC = _REPO_ROOT / "src"
for _p in (_SRC, _REPO_ROOT):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

try:
    from dotenv import load_dotenv
    load_dotenv(_REPO_ROOT / ".env")
except ImportError:
    pass

from configs.embedding import EMBEDDING_CONFIG
from configs.retrieval import RETRIEVAL_CONFIG
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PayloadSchemaType, VectorParams

from embedding.base import make_indexable
from embedding.indexer import QdrantIndexer
from embedding.openai_embedder import OpenAIEmbedder
from ingestion.config import DOC_REGISTRY
from ingestion.preprocessor import PreprocessingPipeline
from retrieval.bm25_retriever import BM25Corpus

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

# Map from lowercase filename stem to registered doc_id
_STEM_TO_DOC_ID: dict[str, str] = {k.lower(): k for k in DOC_REGISTRY}


def _resolve_doc_id(pdf_path: Path) -> str | None:
    stem = pdf_path.stem.lower()
    # Exact match first
    if stem in _STEM_TO_DOC_ID:
        return _STEM_TO_DOC_ID[stem]
    # Prefix match (handles minor naming variations)
    for registered_stem, doc_id in _STEM_TO_DOC_ID.items():
        if stem.startswith(registered_stem) or registered_stem.startswith(stem):
            return doc_id
    return None


def _ensure_collection(client: QdrantClient, collection_name: str, force_recreate: bool) -> None:
    existing = {c.name for c in client.get_collections().collections}
    if collection_name in existing:
        if force_recreate:
            logger.info("--force-recreate: deleting %r", collection_name)
            client.delete_collection(collection_name)
        else:
            logger.info("Collection %r already exists — skipping creation.", collection_name)
            return

    logger.info("Creating collection %r (dim=%d)…", collection_name, EMBEDDING_CONFIG.dimensions)
    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=EMBEDDING_CONFIG.dimensions, distance=Distance.COSINE),
    )
    for field, schema in [
        ("document_id", PayloadSchemaType.KEYWORD),
        ("doc_type", PayloadSchemaType.KEYWORD),
        ("safety_flag", PayloadSchemaType.BOOL),
        ("is_table", PayloadSchemaType.BOOL),
    ]:
        client.create_payload_index(collection_name=collection_name, field_name=field, field_schema=schema)
    logger.info("Collection %r ready.", collection_name)


def _build_bm25(client: QdrantClient, collection_name: str, output_path: Path) -> None:
    chunk_ids: list[str] = []
    chunk_texts: list[str] = []
    chunk_payloads: list[dict] = []
    tokenised_corpus: list[list[str]] = []

    logger.info("Fetching all points from %r for BM25 index…", collection_name)
    offset = None
    while True:
        records, next_offset = client.scroll(
            collection_name=collection_name,
            limit=200,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        if not records:
            break
        for record in records:
            payload = record.payload or {}
            text: str = payload.get("text", "")
            if not text:
                continue
            chunk_ids.append(str(record.id))
            chunk_texts.append(text)
            chunk_payloads.append(payload)
            tokenised_corpus.append(text.lower().split())
        if next_offset is None:
            break
        offset = next_offset

    if not chunk_ids:
        logger.error("No chunks found in %r — BM25 build skipped.", collection_name)
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
    logger.info("BM25 corpus saved → %s (%d chunks)", output_path, len(chunk_ids))


def run(docs_dir: Path, collection_name: str, bm25_output: Path, force_recreate: bool) -> None:
    pdfs = sorted(docs_dir.glob("*.pdf"))
    if not pdfs:
        logger.error("No PDF files found in %s", docs_dir)
        sys.exit(1)

    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY, check_compatibility=False)
    _ensure_collection(client, collection_name, force_recreate)

    embedder = OpenAIEmbedder(EMBEDDING_CONFIG)
    indexer = QdrantIndexer(client, collection_name)
    pipeline = PreprocessingPipeline()

    any_failed = False

    for pdf_path in pdfs:
        doc_id = _resolve_doc_id(pdf_path)
        if doc_id is None:
            logger.warning(
                "No matching doc_id for %s — skipping. "
                "Add it to src/ingestion/config.py DOC_REGISTRY.",
                pdf_path.name,
            )
            any_failed = True
            continue

        logger.info("=== %s → %s ===", pdf_path.name, doc_id)
        t0 = time.perf_counter()

        try:
            chunks = pipeline.run(doc_id, pdf_path)
        except Exception as exc:
            logger.error("Preprocessing failed for %s: %s", doc_id, exc)
            any_failed = True
            continue

        if not chunks:
            logger.warning("No chunks for %s — skipping.", doc_id)
            continue

        from ingestion.config import get_doc_config
        doc_type = get_doc_config(doc_id)["doc_type"]
        for chunk in chunks:
            chunk.metadata["doc_type"] = doc_type

        indexable = make_indexable(chunks, doc_id)
        texts = [c.text for c in indexable]

        try:
            vectors = embedder.embed_batch(texts)
        except Exception as exc:
            logger.error("Embedding failed for %s: %s", doc_id, exc)
            any_failed = True
            continue

        success, failed_ids = indexer.upsert(indexable, vectors)
        if failed_ids:
            logger.warning("%d chunks failed upsert for %s", len(failed_ids), doc_id)
            any_failed = True

        elapsed = time.perf_counter() - t0
        logger.info("Done %s: %d chunks in %.1fs", doc_id, success, elapsed)

    if any_failed:
        logger.error("One or more documents had errors — see logs above.")
        sys.exit(1)

    _build_bm25(client, collection_name, bm25_output)
    logger.info("Batch ingestion complete.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Batch-ingest PDFs from a directory into Qdrant + BM25."
    )
    parser.add_argument(
        "--docs",
        type=Path,
        required=True,
        help="Directory containing PDF files to ingest.",
    )
    parser.add_argument(
        "--collection",
        default=RETRIEVAL_CONFIG.dense.collection_name,
        help="Qdrant collection name (default: from configs/retrieval.py)",
    )
    parser.add_argument(
        "--bm25-output",
        type=Path,
        default=Path(RETRIEVAL_CONFIG.bm25.corpus_cache_path),
        help="Output path for BM25 pickle (default: from configs/retrieval.py)",
    )
    parser.add_argument(
        "--force-recreate",
        action="store_true",
        help="Drop and recreate the Qdrant collection before ingestion.",
    )
    args = parser.parse_args()

    if not args.docs.is_dir():
        logger.error("--docs %s is not a directory", args.docs)
        sys.exit(1)

    run(
        docs_dir=args.docs,
        collection_name=args.collection,
        bm25_output=args.bm25_output,
        force_recreate=args.force_recreate,
    )


if __name__ == "__main__":
    main()
