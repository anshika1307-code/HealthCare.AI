"""
src/serving/schemas.py
-----------------------
Pydantic request/response models for the FastAPI /query endpoint.

Keeps all wire-format concerns out of the orchestration layer.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    filters: dict[str, Any] | None = Field(
        default=None,
        description=(
            "Optional metadata filters forwarded to Qdrant and BM25. "
            "Supported keys: document_id (str), doc_type (str), safety_flag (bool)."
        ),
    )


class SourceChunk(BaseModel):
    chunk_id: str
    document_id: str
    doc_type: str = ""
    section_name: str = ""
    reranker_score: float
    text: str = ""


class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceChunk]
    confidence_score: float
    low_confidence: bool
    warning_message: str = ""
    filters_applied: dict[str, Any] = Field(default_factory=dict)
