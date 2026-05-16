"""
src/retrieval/
--------------
Hybrid retrieval pipeline: Dense (Qdrant) + BM25 → RRF Fusion → Cross-Encoder Reranker.

Primary public surface — import directly from submodules for clarity:
    from retrieval.pipeline import RetrievalPipeline
    from retrieval.confidence import RetrievalResult, ConfidenceScorer
    from retrieval.rrf_ranker import RRFRanker, FusedResult
    from retrieval.bm25_retriever import BM25Retriever, BM25Corpus
    from retrieval.dense_retriever import DenseRetriever
    from retrieval.reranker import CrossEncoderReranker, RankedResult

Note: CrossEncoderReranker and RetrievalPipeline load heavy models at
instantiation time (sentence-transformers, qdrant_client). Import the classes
lazily in application startup, not at module import time.
"""
