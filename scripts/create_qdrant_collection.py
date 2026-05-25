"""
scripts/create_qdrant_collection.py
-------------------------------------
One-time collection + payload index setup for Qdrant.

Run this before the first ingestion. Re-running is safe by default
(no-op if collection already exists). Use --force-recreate for a clean
A/B experiment run with a different embedding model/dimension.

Usage:
    python scripts/create_qdrant_collection.py
    python scripts/create_qdrant_collection.py --force-recreate
    python scripts/create_qdrant_collection.py --dimensions 768 --collection healthcare_chunks_bge
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(_REPO_ROOT / ".env")
except ImportError:
    pass  # fall back to env vars already set in the shell

from configs.embedding import EMBEDDING_CONFIG
from configs.retrieval import RETRIEVAL_CONFIG
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PayloadSchemaType, VectorParams

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

_DISTANCE_MAP = {
    "cosine": Distance.COSINE,
    "dot": Distance.DOT,
    "euclid": Distance.EUCLID,
}


def create_collection(
    collection_name: str,
    dimensions: int,
    distance: str,
    force_recreate: bool,
) -> None:
    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

    existing = {c.name for c in client.get_collections().collections}

    if collection_name in existing:
        if force_recreate:
            logger.info("--force-recreate: deleting existing collection %r", collection_name)
            client.delete_collection(collection_name)
        else:
            logger.info(
                "Collection %r already exists — skipping creation. "
                "Use --force-recreate to drop and recreate.",
                collection_name,
            )
            return

    dist = _DISTANCE_MAP.get(distance, Distance.COSINE)
    logger.info(
        "Creating collection %r: dim=%d distance=%s",
        collection_name,
        dimensions,
        distance,
    )
    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=dimensions, distance=dist),
    )

    # Payload indexes — without these Qdrant scans all points for filter conditions.
    logger.info("Creating payload indexes...")
    client.create_payload_index(
        collection_name=collection_name,
        field_name="document_id",
        field_schema=PayloadSchemaType.KEYWORD,
    )
    client.create_payload_index(
        collection_name=collection_name,
        field_name="doc_type",
        field_schema=PayloadSchemaType.KEYWORD,
    )
    client.create_payload_index(
        collection_name=collection_name,
        field_name="safety_flag",
        field_schema=PayloadSchemaType.BOOL,
    )
    client.create_payload_index(
        collection_name=collection_name,
        field_name="is_table",
        field_schema=PayloadSchemaType.BOOL,
    )

    logger.info("Collection %r ready with payload indexes.", collection_name)


def main() -> None:
    parser = argparse.ArgumentParser(description="Create Qdrant collection for healthcare chunks.")
    parser.add_argument(
        "--collection",
        default=RETRIEVAL_CONFIG.dense.collection_name,
        help="Collection name (default: from configs/retrieval.py)",
    )
    parser.add_argument(
        "--dimensions",
        type=int,
        default=EMBEDDING_CONFIG.dimensions,
        help="Vector dimensions (default: from configs/embedding.py)",
    )
    parser.add_argument(
        "--distance",
        choices=list(_DISTANCE_MAP.keys()),
        default=RETRIEVAL_CONFIG.dense.distance_metric,
        help="Distance metric (default: from configs/retrieval.py)",
    )
    parser.add_argument(
        "--force-recreate",
        action="store_true",
        help="Drop and recreate the collection if it already exists",
    )
    args = parser.parse_args()

    create_collection(
        collection_name=args.collection,
        dimensions=args.dimensions,
        distance=args.distance,
        force_recreate=args.force_recreate,
    )


if __name__ == "__main__":
    main()
