"""
src/orchestration/graph.py
---------------------------
LangGraph StateGraph that wires the three RAG nodes into a compiled pipeline.

Graph topology:
    START → embed_query → retrieve → generate → END

Usage (at server startup):
    from orchestration.graph import build_graph, GraphState
    graph = build_graph(embedder, pipeline, llm_client)
    result: GraphState = await graph.ainvoke({"query": "...", "filters": None})

The compiled graph is thread-safe and can be shared across concurrent requests.
"""
from __future__ import annotations

from typing import Any, TypedDict

import openai
from configs.llm import LLMConfig
from langgraph.graph import END, START, StateGraph

from embedding.base import Embedder
from orchestration.nodes import make_embed_node, make_generate_node, make_retrieve_node
from retrieval.confidence import RetrievalResult
from retrieval.pipeline import RetrievalPipeline

# ---------------------------------------------------------------------------
# State schema — every key is Optional so nodes can safely read partial state
# ---------------------------------------------------------------------------

class GraphState(TypedDict, total=False):
    query: str                          # set by caller
    filters: dict[str, Any] | None     # set by caller (optional)
    query_id: str                       # set by caller (UUID for log correlation)
    query_vector: list[float]           # set by embed_query node
    retrieval_result: RetrievalResult   # set by retrieve node
    answer: str                         # set by generate node
    embed_ms: float                     # set by embed_query node (timing)
    retrieve_ms: float                  # set by retrieve node (timing)
    generate_ms: float                  # set by generate node (timing)


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------

def build_graph(
    embedder: Embedder,
    pipeline: RetrievalPipeline,
    llm_client: openai.AsyncOpenAI,
    llm_config: LLMConfig | None = None,
):
    """
    Compile the LangGraph StateGraph with all three nodes bound to their deps.

    Args:
        embedder:    Embedding provider (OpenAIEmbedder or BGEEmbedder).
        pipeline:    Fully initialised RetrievalPipeline (heavy: loaded once).
        llm_client:  AsyncOpenAI client (or compatible) for generation.
        llm_config:  LLM generation parameters; defaults to LLM_CONFIG singleton.

    Returns:
        A compiled LangGraph graph ready for ainvoke().
    """
    workflow: StateGraph = StateGraph(GraphState)

    workflow.add_node("embed_query", make_embed_node(embedder))
    workflow.add_node("retrieve", make_retrieve_node(pipeline))
    workflow.add_node("generate", make_generate_node(llm_client, llm_config))

    workflow.add_edge(START, "embed_query")
    workflow.add_edge("embed_query", "retrieve")
    workflow.add_edge("retrieve", "generate")
    workflow.add_edge("generate", END)

    return workflow.compile()
