"""
tests/unit/test_retrieval_bm25.py
-----------------------------------
Unit tests for src/retrieval/bm25_retriever.py

Coverage
--------
BM25Result      — payload defaults to {} when None
BM25Corpus      — dataclass field storage
BM25Retriever   — search ranking, top_k override, document filter, zero-score filtering
                  _tokenise, from_cache (FileNotFoundError)
"""

import pickle
import pytest
from io import BytesIO
from unittest.mock import mock_open, patch

from configs.retrieval import BM25Config
from retrieval.bm25_retriever import BM25Corpus, BM25Result, BM25Retriever


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def corpus() -> BM25Corpus:
    """Minimal BM25Corpus covering three doc types for filter tests."""
    return BM25Corpus(
        chunk_ids=["fda-0", "ada-0", "jnc-0"],
        tokenised_corpus=[
            ["metformin", "dosing", "renal", "impairment"],
            ["hba1c", "target", "diabetes", "glycaemic"],
            ["blood", "pressure", "hypertension", "target"],
        ],
        chunk_texts=[
            "Metformin dosing in renal impairment.",
            "HbA1c target for diabetes glycaemic control.",
            "Blood pressure hypertension target.",
        ],
        chunk_payloads=[
            {"document_id": "metformin_fda_label", "doc_type": "fda"},
            {"document_id": "ada_s6",              "doc_type": "ada"},
            {"document_id": "jnc8",                "doc_type": "jnc"},
        ],
    )


@pytest.fixture
def cfg() -> BM25Config:
    return BM25Config(top_k=5, k1=1.5, b=0.75)


@pytest.fixture
def retriever(corpus, cfg) -> BM25Retriever:
    return BM25Retriever(corpus, cfg)


# ===========================================================================
# BM25Result
# ===========================================================================

class TestBM25Result:

    def test_payload_defaults_to_empty_dict_when_none(self):
        result = BM25Result(chunk_id="id", score=1.0)
        assert result.payload == {}

    def test_explicit_payload_stored(self):
        result = BM25Result(chunk_id="id", score=1.0, payload={"doc_type": "fda"})
        assert result.payload["doc_type"] == "fda"

    def test_text_defaults_to_empty_string(self):
        result = BM25Result(chunk_id="id", score=1.0)
        assert result.text == ""


# ===========================================================================
# BM25Retriever.from_cache
# ===========================================================================

class TestFromCache:

    def test_raises_file_not_found_when_cache_missing(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="BM25 corpus cache not found"):
            BM25Retriever.from_cache(tmp_path / "nonexistent.pkl")

    def test_loads_corpus_from_pickle(self, tmp_path, corpus, cfg):
        cache_path = tmp_path / "corpus.pkl"
        with cache_path.open("wb") as f:
            pickle.dump(corpus, f)

        loaded = BM25Retriever.from_cache(cache_path, config=cfg)
        assert loaded is not None
        # Basic sanity: loaded retriever returns results on a known query
        results = loaded.search("metformin")
        assert len(results) > 0


# ===========================================================================
# BM25Retriever._tokenise
# ===========================================================================

class TestTokenise:

    def test_lowercases_input(self, retriever):
        tokens = retriever._tokenise("HbA1c METFORMIN Diabetes")
        assert tokens == ["hba1c", "metformin", "diabetes"]

    def test_splits_on_whitespace(self, retriever):
        tokens = retriever._tokenise("blood pressure target")
        assert tokens == ["blood", "pressure", "target"]

    def test_preserves_medical_compound_tokens(self, retriever):
        """Whitespace tokenisation keeps 'hba1c' as a single token."""
        tokens = retriever._tokenise("HbA1c eGFR mm Hg")
        assert "hba1c" in tokens
        assert "egfr" in tokens

    def test_empty_string_returns_empty_list(self, retriever):
        assert retriever._tokenise("") == []


# ===========================================================================
# BM25Retriever.search — normal cases
# ===========================================================================

class TestSearch:

    def test_returns_bm25result_objects(self, retriever):
        results = retriever.search("metformin renal")
        assert all(isinstance(r, BM25Result) for r in results)

    def test_relevant_chunk_is_top_result(self, retriever):
        """'metformin renal' query → fda-0 chunk should rank first."""
        results = retriever.search("metformin renal")
        assert results[0].chunk_id == "fda-0"

    def test_chunk_ids_match_corpus(self, retriever):
        results = retriever.search("target")
        returned_ids = {r.chunk_id for r in results}
        assert returned_ids.issubset({"fda-0", "ada-0", "jnc-0"})

    def test_text_populated_from_corpus(self, retriever):
        results = retriever.search("metformin")
        top = results[0]
        assert "Metformin" in top.text

    def test_payload_populated_from_corpus(self, retriever):
        results = retriever.search("metformin")
        assert "document_id" in results[0].payload

    def test_results_sorted_by_score_descending(self, retriever):
        results = retriever.search("target")
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_zero_score_chunks_excluded(self, retriever):
        """Chunks with BM25 score ≤ 0 (no matching terms) are filtered out."""
        results = retriever.search("metformin renal")
        assert all(r.score > 0.0 for r in results)

    def test_top_k_override_limits_results(self, retriever):
        results = retriever.search("target", top_k=1)
        assert len(results) <= 1

    def test_top_k_from_config_applied_by_default(self, corpus):
        cfg = BM25Config(top_k=2)
        r = BM25Retriever(corpus, cfg)
        results = r.search("target")
        assert len(results) <= 2

    def test_empty_query_returns_empty_list(self, retriever):
        """Empty query has no BM25 signal — all scores are zero, nothing returned."""
        results = retriever.search("")
        assert results == []

    # --- filter_doc_id ---

    def test_filter_restricts_to_single_document(self, retriever):
        results = retriever.search("target", filter_doc_id="ada_s6")
        assert all(r.payload["document_id"] == "ada_s6" for r in results)

    def test_filter_nonexistent_doc_returns_empty(self, retriever):
        results = retriever.search("metformin", filter_doc_id="no_such_doc")
        assert results == []

    def test_no_filter_returns_results_from_all_docs(self, retriever):
        results = retriever.search("target")
        doc_ids = {r.payload["document_id"] for r in results}
        # "target" appears in both ADA and JNC corpora
        assert len(doc_ids) > 1
