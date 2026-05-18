"""
tests/unit/test_embedding_openai.py
-------------------------------------
Unit tests for src/embedding/openai_embedder.py

Coverage
--------
_l2_normalize         — unit vector, general normalisation, zero vector
OpenAIEmbedder.__init__ — missing API key raises, client created with key
OpenAIEmbedder.embed_batch — empty input, sub-batching, normalize on/off
OpenAIEmbedder._embed_with_retry — retryable vs non-retryable exception types
Properties            — dimensions, model_name
"""

import math

import openai
import pytest
from unittest.mock import MagicMock, patch

from configs.embedding import EmbeddingConfig
from embedding.openai_embedder import OpenAIEmbedder, _l2_normalize, _RETRYABLE


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _cfg(**overrides) -> EmbeddingConfig:
    """EmbeddingConfig with small dimensions and batch_size for fast tests."""
    base = dict(
        model_name="text-embedding-3-small",
        provider="openai",
        dimensions=4,
        batch_size=2,
        normalize=True,
        request_timeout_seconds=5,
        mlflow_experiment_name="test_experiment",
    )
    base.update(overrides)
    return EmbeddingConfig(**base)


def _api_response(vectors: list[list[float]]) -> MagicMock:
    """Minimal mock of openai.types.CreateEmbeddingResponse."""
    resp = MagicMock()
    resp.data = [MagicMock(embedding=v, index=i) for i, v in enumerate(vectors)]
    return resp


@pytest.fixture
def embedder(monkeypatch):
    """OpenAIEmbedder backed by a mock OpenAI client."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    with patch("embedding.openai_embedder.openai.OpenAI") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        emb = OpenAIEmbedder(config=_cfg())
    return emb


# ===========================================================================
# _l2_normalize
# ===========================================================================


class TestL2Normalize:
    """Helper function that normalises a vector to unit length."""

    def test_unit_vector_is_unchanged(self):
        result = _l2_normalize([1.0, 0.0, 0.0])
        assert abs(result[0] - 1.0) < 1e-9
        assert abs(result[1] - 0.0) < 1e-9

    def test_result_has_unit_length(self):
        result = _l2_normalize([3.0, 4.0])  # norm = 5
        norm = math.sqrt(sum(x * x for x in result))
        assert abs(norm - 1.0) < 1e-9

    def test_correct_components_after_normalisation(self):
        # [3, 4] / 5 → [0.6, 0.8]
        result = _l2_normalize([3.0, 4.0])
        assert abs(result[0] - 0.6) < 1e-9
        assert abs(result[1] - 0.8) < 1e-9

    def test_zero_vector_returned_unchanged(self):
        """Must not raise ZeroDivisionError; return as-is."""
        result = _l2_normalize([0.0, 0.0])
        assert result == [0.0, 0.0]

    def test_single_element_vector(self):
        result = _l2_normalize([5.0])
        assert abs(result[0] - 1.0) < 1e-9

    def test_negative_components_handled(self):
        result = _l2_normalize([-3.0, 4.0])
        norm = math.sqrt(sum(x * x for x in result))
        assert abs(norm - 1.0) < 1e-9


# ===========================================================================
# __init__
# ===========================================================================


class TestOpenAIEmbedderInit:
    def test_raises_when_api_key_missing(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        with pytest.raises(EnvironmentError, match="OPENAI_API_KEY"):
            OpenAIEmbedder()

    def test_client_created_with_api_key(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-mykey")
        with patch("embedding.openai_embedder.openai.OpenAI") as mock_cls:
            mock_cls.return_value = MagicMock()
            OpenAIEmbedder(config=_cfg())
        _, kwargs = mock_cls.call_args
        assert kwargs["api_key"] == "sk-mykey"

    def test_uses_global_config_when_none_passed(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        with patch("embedding.openai_embedder.openai.OpenAI"):
            emb = OpenAIEmbedder(config=None)
        assert emb.model_name is not None


# ===========================================================================
# Properties
# ===========================================================================


class TestProperties:
    def test_dimensions(self, embedder):
        assert embedder.dimensions == 4  # set in _cfg()

    def test_model_name(self, embedder):
        assert embedder.model_name == "text-embedding-3-small"


# ===========================================================================
# embed_batch
# ===========================================================================


class TestEmbedBatch:
    def test_empty_input_returns_empty_list(self, embedder):
        assert embedder.embed_batch([]) == []
        embedder._client.embeddings.create.assert_not_called()

    def test_returns_one_vector_per_text(self, embedder):
        vecs = [[0.1, 0.2, 0.3, 0.4], [0.5, 0.6, 0.7, 0.8]]
        embedder._client.embeddings.create.return_value = _api_response(vecs)
        result = embedder.embed_batch(["text a", "text b"])
        assert len(result) == 2

    def test_splits_into_sub_batches(self, embedder):
        """batch_size=2, 5 texts → 3 API calls (2 + 2 + 1)."""
        vec = [0.1, 0.0, 0.0, 0.0]
        embedder._client.embeddings.create.return_value = _api_response([vec, vec])
        embedder.embed_batch(["t"] * 5)
        assert embedder._client.embeddings.create.call_count == 3

    def test_model_name_passed_to_api(self, embedder):
        vec = [0.1, 0.0, 0.0, 0.0]
        embedder._client.embeddings.create.return_value = _api_response([vec])
        embedder.embed_batch(["text"])
        _, kwargs = embedder._client.embeddings.create.call_args
        assert kwargs["model"] == "text-embedding-3-small"

    def test_normalize_true_produces_unit_vectors(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        with patch("embedding.openai_embedder.openai.OpenAI") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client
            emb = OpenAIEmbedder(config=_cfg(normalize=True))

        # API returns a non-unit vector [3, 4, 0, 0] → norm 5
        raw = [[3.0, 4.0, 0.0, 0.0]]
        emb._client.embeddings.create.return_value = _api_response(raw)
        result = emb.embed_batch(["text"])
        norm = math.sqrt(sum(x * x for x in result[0]))
        assert abs(norm - 1.0) < 1e-6

    def test_normalize_false_returns_raw_vectors(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        with patch("embedding.openai_embedder.openai.OpenAI") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client
            emb = OpenAIEmbedder(config=_cfg(normalize=False))

        raw = [[3.0, 4.0, 0.0, 0.0]]
        emb._client.embeddings.create.return_value = _api_response(raw)
        result = emb.embed_batch(["text"])
        assert result[0][0] == pytest.approx(3.0)
        assert result[0][1] == pytest.approx(4.0)


# ===========================================================================
# Retry configuration
# ===========================================================================


class TestRetryConfiguration:
    """
    Test that _RETRYABLE contains the right exception types.
    Actual sleep/wait behaviour is not tested here — that is tenacity's
    responsibility. We verify our config tells tenacity what to retry.
    """

    def test_rate_limit_error_is_retryable(self):
        assert openai.RateLimitError in _RETRYABLE

    def test_api_timeout_error_is_retryable(self):
        assert openai.APITimeoutError in _RETRYABLE

    def test_api_connection_error_is_retryable(self):
        assert openai.APIConnectionError in _RETRYABLE

    def test_authentication_error_is_not_retryable(self):
        """Wrong API key won't fix itself — must fail fast, no retry."""
        assert openai.AuthenticationError not in _RETRYABLE

    def test_non_retryable_error_propagates_on_first_attempt(self, embedder):
        """AuthenticationError must not be swallowed or retried."""
        import httpx

        # httpx.Response requires an attached request for openai's __init__
        request = httpx.Request("POST", "https://api.openai.com/v1/embeddings")
        response = httpx.Response(401, content=b"{}", request=request)
        auth_err = openai.AuthenticationError(
            "invalid key",
            response=response,
            body=None,
        )
        embedder._client.embeddings.create.side_effect = auth_err

        with pytest.raises(openai.AuthenticationError):
            embedder._embed_with_retry(["text"])

        # Exactly one call — no retry attempted
        assert embedder._client.embeddings.create.call_count == 1
