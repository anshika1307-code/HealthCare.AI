"""
configs/llm.py
--------------
LLM generation configuration.

LLM strategy (dual-provider):
- Primary: Groq llama-3.3-70b-versatile — ~200-300ms, free tier, OpenAI-compatible API.
  Cuts answer latency from ~9s (gpt-4o-mini) to ~300ms end-to-end.
- Fallback: gpt-4o-mini — activates automatically when Groq returns RateLimitError.
  Keeps the service live even when Groq free-tier quota is exhausted.
- Suggestions: llama-3.1-8b-instant — tiny/fast model for non-critical follow-up generation.
  Runs concurrently with the main answer so it adds zero extra latency.
- Embeddings: always text-embedding-3-small via OpenAI (no Groq equivalent).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class LLMConfig:
    provider: str = "groq"
    # "groq" = primary. "openai" = skip Groq and go straight to OpenAI (for local dev
    # without GROQ_API_KEY set).

    model_name: str = "llama-3.3-70b-versatile"
    # Groq's best general-purpose model. Equivalent quality to gpt-4o-mini for
    # extractive clinical Q&A; 30-50× faster on Groq free tier.

    fallback_model_name: str = "gpt-4o-mini"
    # OpenAI fallback. Used when Groq returns RateLimitError (429). gpt-4o-mini is
    # ~10× cheaper than gpt-4o and handles the 1-3 sentence extractive task well.

    suggestions_model_name: str = "llama-3.1-8b-instant"
    # Ultra-fast 8B model for follow-up suggestion generation. Runs concurrently
    # with the main answer — quality sufficient for 3 short question strings.

    temperature: float = 0.0
    # Medical Q&A must be deterministic and faithful to retrieved context.

    max_output_tokens: int = 256
    # 256 tokens ≈ 1-3 sentences, matching the system prompt's extractive style.

    system_prompt: str = (
        "You are a clinical document retrieval assistant. "
        "Answer using ONLY the text provided in the context. "
        "Follow these rules without exception:\n"
        "1. Directly quote or closely paraphrase the relevant passage — do not paraphrase loosely.\n"
        "2. Keep your answer to 1–3 sentences. Do not elaborate or explain.\n"
        "3. Do NOT add any information not explicitly present in the context, "
        "even if it is medically accurate or obvious.\n"
        "4. Do NOT add warnings, caveats, or background reasoning unless the context states them.\n"
        "5. If the context does not contain the answer, respond exactly: "
        "'The provided documents do not contain sufficient information to answer this question.'"
    )

    context_window_tokens: int = 128_000
    # Both Groq Llama-3.3-70B and gpt-4o-mini support 128k context.


LLM_CONFIG = LLMConfig()
