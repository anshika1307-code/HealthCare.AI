"""
tests/unit/test_configs.py
---------------------------
Unit tests for configs/embedding.py, configs/llm.py, configs/retrieval.py.

Verifies default values, dataclass override, singleton identity, and that
composite config (RetrievalConfig) correctly nests sub-configs.
"""

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
if str(_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_ROOT / "src"))

import pytest

from configs.embedding import EmbeddingConfig, EMBEDDING_CONFIG
from configs.llm import LLMConfig, LLM_CONFIG
from configs.retrieval import (
    BM25Config,
    ConfidenceConfig,
    DenseConfig,
    RRFConfig,
    RerankerConfig,
    RetrievalConfig,
    RETRIEVAL_CONFIG,
)


# ===========================================================================
# EmbeddingConfig
# ===========================================================================


class TestEmbeddingConfig:
    def test_default_model(self):
        assert EmbeddingConfig().model_name == "text-embedding-3-small"

    def test_default_provider(self):
        assert EmbeddingConfig().provider == "openai"

    def test_default_dimensions(self):
        assert EmbeddingConfig().dimensions == 1536

    def test_default_batch_size(self):
        assert EmbeddingConfig().batch_size == 100

    def test_default_normalize(self):
        assert EmbeddingConfig().normalize is True

    def test_default_timeout(self):
        assert EmbeddingConfig().request_timeout_seconds == 30

    def test_default_mlflow_experiment(self):
        assert EmbeddingConfig().mlflow_experiment_name == "embedding_model_ab"

    def test_override_model(self):
        cfg = EmbeddingConfig(model_name="text-embedding-ada-002")
        assert cfg.model_name == "text-embedding-ada-002"

    def test_override_dimensions(self):
        cfg = EmbeddingConfig(dimensions=768)
        assert cfg.dimensions == 768

    def test_override_batch_size(self):
        cfg = EmbeddingConfig(batch_size=50)
        assert cfg.batch_size == 50

    def test_override_provider_bge(self):
        cfg = EmbeddingConfig(provider="bge")
        assert cfg.provider == "bge"

    def test_singleton_identity(self):
        from configs.embedding import EMBEDDING_CONFIG as cfg2

        assert EMBEDDING_CONFIG is cfg2

    def test_singleton_defaults(self):
        assert EMBEDDING_CONFIG.provider == "openai"
        assert EMBEDDING_CONFIG.dimensions == 1536

    def test_instances_are_independent(self):
        a = EmbeddingConfig(batch_size=10)
        b = EmbeddingConfig(batch_size=200)
        assert a.batch_size != b.batch_size


# ===========================================================================
# LLMConfig
# ===========================================================================


class TestLLMConfig:
    def test_default_provider(self):
        assert LLMConfig().provider == "groq"

    def test_default_model(self):
        assert LLMConfig().model_name == "llama-3.3-70b-versatile"

    def test_default_fallback_model(self):
        assert LLMConfig().fallback_model_name == "gpt-4o-mini"

    def test_default_suggestions_model(self):
        assert LLMConfig().suggestions_model_name == "llama-3.1-8b-instant"

    def test_default_temperature(self):
        assert LLMConfig().temperature == 0.0

    def test_default_max_tokens(self):
        assert LLMConfig().max_output_tokens == 256

    def test_default_context_window(self):
        assert LLMConfig().context_window_tokens == 128_000

    def test_system_prompt_not_empty(self):
        assert len(LLMConfig().system_prompt) > 50

    def test_system_prompt_contains_context_restriction(self):
        prompt = LLMConfig().system_prompt
        assert "ONLY" in prompt or "context" in prompt.lower()

    def test_system_prompt_mentions_source(self):
        prompt = LLMConfig().system_prompt.lower()
        assert "context" in prompt or "source" in prompt or "document" in prompt

    def test_override_model(self):
        cfg = LLMConfig(model_name="gpt-4o")
        assert cfg.model_name == "gpt-4o"

    def test_override_temperature(self):
        cfg = LLMConfig(temperature=0.1)
        assert cfg.temperature == pytest.approx(0.1)

    def test_override_max_tokens(self):
        cfg = LLMConfig(max_output_tokens=1024)
        assert cfg.max_output_tokens == 1024

    def test_singleton_identity(self):
        from configs.llm import LLM_CONFIG as cfg2

        assert LLM_CONFIG is cfg2

    def test_singleton_is_correct_model(self):
        assert LLM_CONFIG.model_name == "llama-3.3-70b-versatile"


# ===========================================================================
# DenseConfig
# ===========================================================================


class TestDenseConfig:
    def test_default_collection(self):
        assert DenseConfig().collection_name == "healthcare_chunks"

    def test_default_top_k(self):
        assert DenseConfig().top_k == 20

    def test_default_distance_metric(self):
        assert DenseConfig().distance_metric == "cosine"

    def test_default_score_threshold(self):
        assert DenseConfig().score_threshold == pytest.approx(0.25)

    def test_filter_fields_contains_doc_type(self):
        assert "doc_type" in DenseConfig().filter_fields

    def test_filter_fields_contains_document_id(self):
        assert "document_id" in DenseConfig().filter_fields

    def test_filter_fields_is_list(self):
        assert isinstance(DenseConfig().filter_fields, list)

    def test_instances_share_no_filter_list(self):
        a = DenseConfig()
        b = DenseConfig()
        a.filter_fields.append("extra")
        assert "extra" not in b.filter_fields


# ===========================================================================
# BM25Config
# ===========================================================================


class TestBM25Config:
    def test_default_top_k(self):
        assert BM25Config().top_k == 20

    def test_default_k1(self):
        assert BM25Config().k1 == pytest.approx(1.5)

    def test_default_b(self):
        assert BM25Config().b == pytest.approx(0.75)

    def test_default_tokenizer(self):
        assert BM25Config().tokenizer == "whitespace"

    def test_corpus_cache_path_is_pkl(self):
        assert BM25Config().corpus_cache_path.endswith(".pkl")

    def test_override_top_k(self):
        assert BM25Config(top_k=10).top_k == 10


# ===========================================================================
# RRFConfig
# ===========================================================================


class TestRRFConfig:
    def test_default_k(self):
        assert RRFConfig().k == 30

    def test_default_weights(self):
        cfg = RRFConfig()
        assert cfg.dense_weight == pytest.approx(1.0)
        assert cfg.bm25_weight == pytest.approx(1.3)

    def test_default_fusion_pool_size(self):
        assert RRFConfig().fusion_pool_size == 20

    def test_pool_size_equals_individual_top_k(self):
        assert RRFConfig().fusion_pool_size == DenseConfig().top_k


# ===========================================================================
# RerankerConfig
# ===========================================================================


class TestRerankerConfig:
    def test_default_model(self):
        assert "cross-encoder" in RerankerConfig().model_name

    def test_default_top_n(self):
        assert RerankerConfig().top_n == 3

    def test_default_batch_size(self):
        assert RerankerConfig().batch_size == 8

    def test_default_device(self):
        assert RerankerConfig().device == "cpu"

    def test_normalize_scores_true(self):
        assert RerankerConfig().normalize_scores is True

    def test_top_n_less_than_pool_size(self):
        assert RerankerConfig().top_n < RRFConfig().fusion_pool_size


# ===========================================================================
# ConfidenceConfig
# ===========================================================================


class TestConfidenceConfig:
    def test_default_threshold(self):
        assert ConfidenceConfig().low_confidence_threshold == pytest.approx(0.40)

    def test_return_answer_below_threshold_is_true(self):
        assert ConfidenceConfig().return_answer_below_threshold is True

    def test_score_source(self):
        assert ConfidenceConfig().score_source == "top1_reranker"

    def test_warning_message_not_empty(self):
        assert len(ConfidenceConfig().warning_message) > 10

    def test_threshold_between_zero_and_one(self):
        t = ConfidenceConfig().low_confidence_threshold
        assert 0.0 < t < 1.0


# ===========================================================================
# RetrievalConfig (composite)
# ===========================================================================


class TestRetrievalConfig:
    def test_has_dense(self):
        assert isinstance(RetrievalConfig().dense, DenseConfig)

    def test_has_bm25(self):
        assert isinstance(RetrievalConfig().bm25, BM25Config)

    def test_has_rrf(self):
        assert isinstance(RetrievalConfig().rrf, RRFConfig)

    def test_has_reranker(self):
        assert isinstance(RetrievalConfig().reranker, RerankerConfig)

    def test_has_confidence(self):
        assert isinstance(RetrievalConfig().confidence, ConfidenceConfig)

    def test_instances_have_independent_sub_configs(self):
        a = RetrievalConfig()
        b = RetrievalConfig()
        a.dense.top_k = 99
        assert b.dense.top_k != 99

    def test_singleton_identity(self):
        from configs.retrieval import RETRIEVAL_CONFIG as cfg2

        assert RETRIEVAL_CONFIG is cfg2

    def test_singleton_top_k(self):
        assert RETRIEVAL_CONFIG.dense.top_k == 20
        assert RETRIEVAL_CONFIG.bm25.top_k == 20
