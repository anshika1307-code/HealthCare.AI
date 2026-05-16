"""
configs/retrieval.py
--------------------
All tuneable knobs for the hybrid retrieval pipeline.
Every value is accompanied by an explicit reason so future developers
can understand WHY a number was chosen, not just what it is.

Design principle: change a number here → whole pipeline adapts.
Never hardcode retrieval parameters inside src/.
"""
from __future__ import annotations

from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Dense (Qdrant) config
# ---------------------------------------------------------------------------

@dataclass
class DenseConfig:
    collection_name: str = "healthcare_chunks"
    # Single collection per prototype. In production: namespace by corpus version
    # (e.g. "healthcare_chunks_v2") so re-ingestion doesn't break live traffic.

    top_k: int = 20
    # Fetch 20 dense candidates before RRF. Cormack & Clarke 2009 show RRF is
    # stable with 20–60 candidates per retriever. 20 is conservative for a
    # 4-document corpus (≈ 400 chunks total).

    distance_metric: str = "cosine"
    # text-embedding-3-small produces unit-normalised vectors → cosine ≡ dot
    # product. Qdrant's HNSW index is fastest on inner-product for normalised
    # vectors; we declare cosine and let Qdrant optimise internally.

    enable_metadata_filter: bool = True
    # Medical queries are often document-scoped ("in the JNC guidelines…").
    # Pre-filtering via Qdrant payload filter shrinks the ANN search space
    # and raises precision without hurting recall on a 4-doc corpus.

    filter_fields: list[str] = field(default_factory=lambda: [
        "document_id",  # per-source grounding
        "doc_type",     # route fda / ada / jnc queries to right subset
        "safety_flag",  # boost safety-flagged chunks when query contains risk terms
    ])

    score_threshold: float | None = None
    # None = no score gate at dense-search time; let RRF + reranker gate quality.
    # Set ≈ 0.30 post-RAGAS eval if low-relevance dense hits pollute fusion pool.


# ---------------------------------------------------------------------------
# BM25 config
# ---------------------------------------------------------------------------

@dataclass
class BM25Config:
    top_k: int = 20
    # Mirror dense top_k so RRF fusion receives symmetric-size lists from both
    # retrievers. Asymmetric lists bias RRF toward the larger list.

    k1: float = 1.5
    # Term-frequency saturation. Standard Elasticsearch default. Well-validated
    # on short biomedical snippets (PubMed abstracts ≈ 250 words; our chunks ≈
    # 512 tokens). Higher k1 (e.g. 2.0) rewards repeated terms more aggressively
    # — not needed here since chunks are short and non-repetitive.

    b: float = 0.75
    # Document-length normalisation. BM25 paper default. Works well when all
    # chunks are roughly equal length (512-token budget enforced by chunker).
    # Lower b (e.g. 0.5) if chunks vary widely in length after re-chunking.

    corpus_cache_path: str = "data/cache/bm25_corpus.pkl"
    # BM25 is in-memory. Pickle the tokenised corpus so the API server loads
    # it at startup without re-tokenising hundreds of chunks every restart.
    # Production upgrade: swap for an OpenSearch/ES inverted index.

    tokenizer: str = "whitespace"
    # Medical text contains meaningful compound tokens: "HbA1c", "mm Hg",
    # "eGFR". Whitespace tokenisation preserves them intact. spaCy/NLTK would
    # fragment "mm Hg" → ["mm", "Hg"], breaking exact-match for unit queries.


# ---------------------------------------------------------------------------
# Reciprocal Rank Fusion config
# ---------------------------------------------------------------------------

@dataclass
class RRFConfig:
    k: int = 60
    # Canonical RRF smoothing constant from Cormack & Clarke 2009.
    # Empirically robust across IR benchmarks. Google's hybrid search uses k=60.
    # Lower k (e.g. 10) amplifies top-rank differences; higher k (e.g. 120)
    # smooths ranks more. 60 is the safe default until RAGAS eval guides tuning.

    dense_weight: float = 1.0
    bm25_weight: float = 1.0
    # Equal weights. Medical documents are acronym-heavy (BP, CGM, GFR), making
    # BM25 genuinely competitive with dense search for exact-term matching.
    # Post-RAGAS: if context_recall is low → increase dense_weight.
    #             if context_precision is low → increase bm25_weight.

    fusion_pool_size: int = 40
    # Top-40 from the fused list fed to the cross-encoder reranker.
    # More signal than top-20 without the O(n²) cross-encoder cost of all 80.


# ---------------------------------------------------------------------------
# Cross-encoder reranker config
# ---------------------------------------------------------------------------

@dataclass
class RerankerConfig:
    model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    # Smallest MS-MARCO cross-encoder with solid reranking performance on
    # biomedical text. MiniLM-L-6 = 22M params → ~100ms CPU latency for
    # 40 (query, chunk) pairs. BGE reranker is higher quality but 3× larger —
    # unacceptable on a free-tier server (512MB RAM budget).

    top_n: int = 5
    # decision.md: "top 5 for final context window".
    # 5 × 512-token chunks ≈ 2,560 tokens → well inside gpt-4o-mini's 128k
    # context window while keeping prompt cost minimal.

    batch_size: int = 32
    # Cross-encoder batch size. 32 pairs × (query + 512-token chunk) fits in
    # ~256MB RAM on free server. Reduce to 16 if OOM errors occur at startup.

    device: str = "cpu"
    # Free-tier servers (Render, Railway) have no GPU. MiniLM-L-6 CPU inference
    # is fast enough for our latency target (< 2s end-to-end).

    normalize_scores: bool = True
    # Apply sigmoid to raw cross-encoder logits → scores in [0, 1].
    # Normalised scores feed cleanly into the confidence layer threshold check.


# ---------------------------------------------------------------------------
# Confidence scoring config
# ---------------------------------------------------------------------------

@dataclass
class ConfidenceConfig:
    low_confidence_threshold: float = 0.40
    # Conservative starting threshold. Will be calibrated post-RAGAS eval.
    # Raise to 0.50 if too many spurious warnings appear in manual testing.
    # Lower to 0.30 if high-stakes safety chunks are being silently returned.

    warning_message: str = (
        "⚠️ Low confidence: The retrieved context may not fully support this answer. "
        "Please verify with the original clinical document."
    )
    # Shown to user when top-1 reranker score < low_confidence_threshold.
    # Follows decision.md requirement: warn alongside answer, never suppress.

    return_answer_below_threshold: bool = True
    # "Flag it to user with a warning ALONG the answer" (decision.md, §Retrieval).
    # Setting False would suppress answers — unacceptable for a clinical tool
    # where a missing answer is worse than an uncertain one.

    score_source: str = "top1_reranker"
    # Use top-ranked chunk's cross-encoder score as the confidence proxy.
    # Alternative: mean of top-5 scores. Top-1 is more conservative (safer)
    # and doesn't require a second LLM call or calibration pass.


# ---------------------------------------------------------------------------
# Root config object
# ---------------------------------------------------------------------------

@dataclass
class RetrievalConfig:
    dense: DenseConfig = field(default_factory=DenseConfig)
    bm25: BM25Config = field(default_factory=BM25Config)
    rrf: RRFConfig = field(default_factory=RRFConfig)
    reranker: RerankerConfig = field(default_factory=RerankerConfig)
    confidence: ConfidenceConfig = field(default_factory=ConfidenceConfig)


# Module-level singleton — import this everywhere in src/retrieval/
RETRIEVAL_CONFIG = RetrievalConfig()
