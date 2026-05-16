"""
configs/llm.py
--------------
LLM generation configuration.
Keeping LLM config separate from retrieval config so the generator can be
swapped independently (e.g. gpt-4o-mini → Groq Llama) without any changes
to retrieval logic.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class LLMConfig:
    provider: str = "openai"
    # Current: "openai". Switch to "groq" for free-tier Llama (Groq free tier
    # provides Llama-3-70B at no cost — useful for development/testing).

    model_name: str = "gpt-4o-mini"
    # Cheapest OpenAI model with sufficient instruction-following for structured
    # clinical Q&A. ~10× cheaper than gpt-4o per token. Adequate for RAG use
    # case where the heavy lifting is done by retrieval, not generation.

    temperature: float = 0.0
    # Medical Q&A must be deterministic and faithful to retrieved context.
    # temperature=0.0 → greedy decoding. Never set > 0.2 for clinical tools.

    max_output_tokens: int = 512
    # 512 tokens ≈ 3–4 paragraph answer. Sufficient for clinical Q&A.
    # Keeps cost low (output tokens are 3× more expensive than input on OpenAI).

    system_prompt: str = (
        "You are a clinical decision support assistant. "
        "Answer ONLY from the provided context. "
        "Cite the document name and section for every claim. "
        "If the context does not contain sufficient information, "
        "respond: 'The provided documents do not contain enough information to answer this question.' "
        "Do NOT use background knowledge outside the provided context. "
        "If the question involves drug dosing, contraindications, or safety warnings, "
        "always include the relevant warning text verbatim."
    )
    # Encodes three decision.md requirements:
    # 1. Context-faithful answers only (no hallucination)
    # 2. Source citation per claim (traceability)
    # 3. Explicit refusal when context is insufficient (safer than guessing)
    # Added: verbatim safety text requirement for clinical safety.

    context_window_tokens: int = 128_000
    # gpt-4o-mini context window. Used by pipeline.py to guard against
    # accidentally building a prompt larger than the model can accept.


LLM_CONFIG = LLMConfig()
