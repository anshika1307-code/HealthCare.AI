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
    # Fetch 20 dense candidates before RRF. Was 30 post-RAGAS eval; reduced back
    # to 20 after Railway OOM kills: the larger pool pushed reranker RAM over the
    # 512MB container limit. 20 still covers the relevant chunks on a 4-doc corpus.

    distance_metric: str = "cosine"
    # text-embedding-3-small produces unit-normalised vectors → cosine ≡ dot
    # product. Qdrant's HNSW index is fastest on inner-product for normalised
    # vectors; we declare cosine and let Qdrant optimise internally.

    enable_metadata_filter: bool = True
    # Medical queries are often document-scoped ("in the JNC guidelines…").
    # Pre-filtering via Qdrant payload filter shrinks the ANN search space
    # and raises precision without hurting recall on a 4-doc corpus.

    filter_fields: list[str] = field(
        default_factory=lambda: [
            "document_id",  # per-source grounding
            "doc_type",  # route fda / ada / jnc queries to right subset
            "safety_flag",  # boost safety-flagged chunks when query contains risk terms
        ]
    )

    score_threshold: float | None = 0.25
    # Filters out dense hits with cosine similarity < 0.25 before they reach
    # RRF + reranker. Prevents clearly irrelevant chunks from polluting the
    # fusion pool and causing spurious confidence drops. Tune down to 0.20 if
    # recall drops on rare medical acronym queries.


# ---------------------------------------------------------------------------
# BM25 config
# ---------------------------------------------------------------------------


@dataclass
class BM25Config:
    top_k: int = 20
    # Mirror dense top_k so RRF fusion receives symmetric-size lists from both
    # retrievers. Asymmetric lists bias RRF toward the larger list.
    # Reduced to 20 alongside dense top_k to fix Railway OOM kill.

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
    k: int = 30
    # RRF smoothing constant. Lowered from 60 post-RAGAS eval: k=60 overly
    # smooths rank differences, making it hard for a genuinely top-ranked chunk
    # to separate from the pack. k=30 amplifies rank signal while still being
    # robust — well within the validated 10–60 range from Cormack & Clarke 2009.

    dense_weight: float = 1.0
    bm25_weight: float = 1.3
    # Slight BM25 boost post-RAGAS eval: 9 low-confidence queries include
    # medical acronyms (GMI, SGLT2, ACE, ARB, GLP-1) that BM25 matches exactly
    # while the dense model (text-embedding-3-small, general purpose) may
    # under-weight. 1.3 is conservative — revert to 1.0 if precision drops.

    fusion_pool_size: int = 20
    # Top-20 from the fused list fed to the cross-encoder reranker.
    # Reduced from 40 to fix Railway OOM kill: 40 pairs × 512-token max length
    # caused RAM spike that killed the process. 20 pairs fit safely within the
    # 512MB container limit. The marginal chunks at rank 21-40 rarely contain
    # the correct answer on a 4-doc corpus — they scored low in both retrievers.


# ---------------------------------------------------------------------------
# Cross-encoder reranker config
# ---------------------------------------------------------------------------


@dataclass
class RerankerConfig:
    model_name: str = "cross-encoder/ms-marco-MiniLM-L-2-v2"
    # MiniLM-L-2: 2-layer cross-encoder, ~6M params, ~24MB weights.
    # Chosen over L-6 (22M params, ~88MB) to fit Railway free tier (512MB RAM):
    # L-6 + activations pushed total RAM to ~380MB, causing OOM kills mid-request.
    # L-2 brings total RAM to ~220MB, leaving safe headroom.
    # MS-MARCO MRR@10: L-2=32.0 vs L-6=34.7 — ~5% lower, acceptable on a
    # 4-document corpus where top candidates are rarely ambiguous.

    top_n: int = 3
    # Reduced from 5 for latency: 3 × 512-token chunks ≈ 1,536 tokens fed to
    # the LLM, cutting prompt size by ~40% and generation time accordingly.
    # The top-3 reranked chunks carry the vast majority of signal on a
    # 4-document corpus; chunks 4-5 are usually redundant sections.

    batch_size: int = 8
    # Cross-encoder batch size. Reduced from 32 to 8 to fix Railway OOM kill:
    # 32 pairs × (query + 512 tokens) allocated tensors that spiked RAM over the
    # 512MB container limit mid-request. 8 pairs process the same 20-pair pool
    # in 3 passes with a much smaller per-pass tensor footprint.

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
