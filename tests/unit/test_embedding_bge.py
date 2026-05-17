"""
tests/unit/test_embedding_bge.py
----------------------------------
Unit tests for src/embedding/bge_embedder.py

All tests mock SentenceTransformer so sentence-transformers does not need
to be installed — this is a unit test, not an integration test.

Coverage
--------
BGEEmbedder.__init__ — ImportError when library missing, correct model loaded
BGEEmbedder.embed_batch — empty input, instruction prefix, sub-batching, normalize flag
Properties            — dimensions always 768, model_name constant
"""

import numpy as np
import pytest
from unittest.mock import MagicMock, patch

from configs.embedding import EmbeddingConfig
from embedding.bge_embedder import (
    BGEEmbedder,
    _BGE_DIMENSIONS,
    _BGE_MODEL_ID,
    _BGE_QUERY_INSTRUCTION,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cfg(**overrides) -> EmbeddingConfig:
    base = dict(
        model_name=_BGE_MODEL_ID,
        provider="bge",
        dimensions=_BGE_DIMENSIONS,
        batch_size=2,
        normalize=True,
        request_timeout_seconds=30,
        mlflow_experiment_name="test_experiment",
    )
    base.update(overrides)
    return EmbeddingConfig(**base)


def _mock_st_module(n_dims: int = _BGE_DIMENSIONS) -> tuple[MagicMock, MagicMock]:
    """
    Return (mock_module, mock_model) where mock_module.SentenceTransformer()
    returns mock_model. The model's encode() produces (n, n_dims) float32 arrays.
    """
    mock_model = MagicMock()
    mock_model.device = "cpu"

    def _encode(texts, normalize_embeddings, show_progress_bar, batch_size):
        return np.ones((len(texts), n_dims), dtype=np.float32)

    mock_model.encode.side_effect = _encode

    mock_module = MagicMock()
    mock_module.SentenceTransformer.return_value = mock_model
    return mock_module, mock_model


@pytest.fixture
def embedder():
    """BGEEmbedder with SentenceTransformer fully mocked out."""
    mock_module, mock_model = _mock_st_module()
    with patch.dict("sys.modules", {"sentence_transformers": mock_module}):
        emb = BGEEmbedder(config=_cfg())
    # Ensure the mock model is attached even after the patch context exits
    emb._model = mock_model
    return emb


# ===========================================================================
# __init__
# ===========================================================================

class TestBGEEmbedderInit:

    def test_raises_import_error_when_library_missing(self):
        """
        When sentence-transformers is not installed, BGEEmbedder must raise
        ImportError with a helpful installation message.

        Simulated by setting sys.modules entry to None, which Python treats
        as a failed import for that module name.
        """
        with patch.dict("sys.modules", {"sentence_transformers": None}):
            with pytest.raises(ImportError, match="sentence-transformers"):
                BGEEmbedder(config=_cfg())

    def test_loads_correct_model_id(self):
        """SentenceTransformer must be called with the BAAI/bge-base-en-v1.5 ID."""
        mock_module, _ = _mock_st_module()
        with patch.dict("sys.modules", {"sentence_transformers": mock_module}):
            BGEEmbedder(config=_cfg())
        mock_module.SentenceTransformer.assert_called_once_with(_BGE_MODEL_ID)


# ===========================================================================
# Properties
# ===========================================================================

class TestBGEEmbedderProperties:

    def test_dimensions_is_always_768(self, embedder):
        """BGE-base-en-v1.5 output is always 768-dim regardless of config."""
        assert embedder.dimensions == 768

    def test_model_name_is_bge_identifier(self, embedder):
        assert embedder.model_name == "BAAI/bge-base-en-v1.5"


# ===========================================================================
# embed_batch
# ===========================================================================

class TestBGEEmbedderEmbedBatch:

    def test_empty_input_returns_empty_list(self, embedder):
        assert embedder.embed_batch([]) == []
        embedder._model.encode.assert_not_called()

    def test_returns_one_vector_per_text(self, embedder):
        result = embedder.embed_batch(["text one", "text two"])
        assert len(result) == 2

    def test_each_vector_has_768_dimensions(self, embedder):
        result = embedder.embed_batch(["HbA1c target"])
        assert len(result[0]) == _BGE_DIMENSIONS

    def test_prepends_instruction_prefix_to_each_text(self, embedder):
        """
        BGE retrieval tasks require a specific instruction prefix.
        Without it, recall drops ~5% on asymmetric retrieval benchmarks.
        """
        embedder.embed_batch(["some clinical text"])
        texts_passed = embedder._model.encode.call_args[0][0]
        assert all(t.startswith(_BGE_QUERY_INSTRUCTION) for t in texts_passed)

    def test_splits_into_sub_batches(self, embedder):
        """batch_size=2, 5 texts → 3 encode calls (2 + 2 + 1)."""
        embedder.embed_batch(["t"] * 5)
        assert embedder._model.encode.call_count == 3

    def test_passes_normalize_flag_through(self, embedder):
        embedder.embed_batch(["text"])
        call_kwargs = embedder._model.encode.call_args[1]
        assert call_kwargs["normalize_embeddings"] is True

    def test_normalize_false_forwarded(self):
        """normalize=False in config must reach SentenceTransformer.encode."""
        mock_module, mock_model = _mock_st_module()
        with patch.dict("sys.modules", {"sentence_transformers": mock_module}):
            emb = BGEEmbedder(config=_cfg(normalize=False))
        emb._model = mock_model
        emb.embed_batch(["text"])
        call_kwargs = mock_model.encode.call_args[1]
        assert call_kwargs["normalize_embeddings"] is False

    def test_returns_python_lists_not_numpy_arrays(self, embedder):
        """embed_batch must return list[list[float]], not numpy arrays."""
        result = embedder.embed_batch(["text"])
        assert isinstance(result, list)
        assert isinstance(result[0], list)
        assert isinstance(result[0][0], float)
