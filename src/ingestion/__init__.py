"""
ingestion package
-----------------
Public API surface for the preprocessing pipeline.

    from ingestion import PreprocessingPipeline, Chunk
"""

from ingestion.preprocessor import PreprocessingPipeline
from ingestion.chunker import Chunk
from ingestion.config import DOC_REGISTRY, get_doc_config

__all__ = ["PreprocessingPipeline", "Chunk", "DOC_REGISTRY", "get_doc_config"]
