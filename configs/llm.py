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
    # v2 post-RAGAS eval (faithfulness=0.7458, relevancy=0.5357):
    # v1 (faithfulness=0.62): LLM elaborated from training knowledge → unfaithful claims.
    # v2: strict extractive mode. faithfulness +0.12 vs v1. relevancy dropped due to
    # 1-3 sentence cap on multi-part questions — acceptable trade-off at this threshold.

    context_window_tokens: int = 128_000
    # gpt-4o-mini context window. Used by pipeline.py to guard against
    # accidentally building a prompt larger than the model can accept.


LLM_CONFIG = LLMConfig()
