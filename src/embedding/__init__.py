"""
src/embedding
-------------
Embedding layer: embed chunks and index them in Qdrant.

Exports
-------
Embedder        - Protocol for provider swap (OpenAI ↔ BGE requires zero indexer changes)
IndexableChunk  - Chunk + deterministic UUID5 chunk_id
make_chunk_id   - UUID5 ID generator
make_indexable  - Convert raw Chunk list → IndexableChunk list
OpenAIEmbedder  - OpenAI text-embedding-3-small provider
BGEEmbedder     - Local BGE-base-en-v1.5 provider
QdrantIndexer   - Idempotent batch upsert to Qdrant
"""
from .base import Embedder, IndexableChunk, make_chunk_id, make_indexable
from .bge_embedder import BGEEmbedder
from .indexer import QdrantIndexer
from .openai_embedder import OpenAIEmbedder

__all__ = [
    "Embedder",
    "IndexableChunk",
    "make_chunk_id",
    "make_indexable",
    "OpenAIEmbedder",
    "BGEEmbedder",
    "QdrantIndexer",
]
