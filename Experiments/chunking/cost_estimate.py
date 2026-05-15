"""
cost_estimate.py — Calculate OpenAI API cost for the chunking experiment
before running it.
"""
import sys
sys.path.insert(0, 'experiments/chunking')
from eval_loader import load_eval_questions
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
STRATEGIES      = 3          # boundary_aware, fixed_size, sentence_window
TOKEN_SIZES     = [256, 512, 1024]
TOP_K           = 5          # chunks retrieved per question
MAX_ANSWER_TOKS = 300        # our max_tokens limit in generate_answer()
SYSTEM_PROMPT   = 150        # ~tokens for the system/instruction prompt
QUESTION_TOKS   = 30         # avg tokens per question

# gpt-4o-mini pricing (May 2025)
PRICE_IN  = 0.150 / 1_000_000   # $ per input token
PRICE_OUT = 0.600 / 1_000_000   # $ per output token

# RAGAS LLM judge extra calls (only if ragas is installed)
RAGAS_EXTRA_CALLS_PER_Q = 5    # faithfulness (3) + answer_relevancy (2) avg
RAGAS_EXTRA_INPUT_TOKS  = 600  # per extra call
RAGAS_EXTRA_OUTPUT_TOKS = 80   # per extra call

# ── Load questions ────────────────────────────────────────────────────────────
qs = load_eval_questions(Path('data/evaluation'))
N_QUESTIONS = len(qs)

print(f"Eval questions loaded : {N_QUESTIONS}")
print(f"Strategies            : {STRATEGIES}")
print(f"Token sizes           : {TOKEN_SIZES}")
print(f"Configurations        : {STRATEGIES * len(TOKEN_SIZES)}")
print(f"Total API calls       : {STRATEGIES * len(TOKEN_SIZES) * N_QUESTIONS}")
print()

# ── Answer generation cost ────────────────────────────────────────────────────
print("=== ANSWER GENERATION (gpt-4o-mini) ===")
total_in = total_out = 0.0

for tok_size in TOKEN_SIZES:
    context_toks    = TOP_K * tok_size          # 5 chunks × chunk size
    input_per_call  = SYSTEM_PROMPT + context_toks + QUESTION_TOKS
    output_per_call = MAX_ANSWER_TOKS
    calls           = STRATEGIES * N_QUESTIONS

    in_cost  = calls * input_per_call  * PRICE_IN
    out_cost = calls * output_per_call * PRICE_OUT
    subtotal = in_cost + out_cost

    print(f"  chunk_size={tok_size:4d}  context_tokens={context_toks:5d}"
          f"  input/call={input_per_call:5d}"
          f"  calls={calls:3d}"
          f"  cost=${subtotal:.4f}")
    total_in  += calls * input_per_call
    total_out += calls * output_per_call

answer_gen_cost = total_in * PRICE_IN + total_out * PRICE_OUT
print(f"\n  Total input tokens  : {total_in:,.0f}  → ${total_in  * PRICE_IN:.4f}")
print(f"  Total output tokens : {total_out:,.0f}  → ${total_out * PRICE_OUT:.4f}")
print(f"  ANSWER GEN TOTAL    : ${answer_gen_cost:.4f}")

# ── RAGAS judge cost (if installed) ──────────────────────────────────────────
print()
print("=== RAGAS LLM JUDGE (only if ragas is installed) ===")
ragas_calls   = STRATEGIES * len(TOKEN_SIZES) * N_QUESTIONS * RAGAS_EXTRA_CALLS_PER_Q
ragas_in_cost = ragas_calls * RAGAS_EXTRA_INPUT_TOKS  * PRICE_IN
ragas_out_cost= ragas_calls * RAGAS_EXTRA_OUTPUT_TOKS * PRICE_OUT
ragas_cost    = ragas_in_cost + ragas_out_cost
print(f"  Extra LLM calls     : {ragas_calls:,}")
print(f"  RAGAS JUDGE TOTAL   : ${ragas_cost:.4f}")
print(f"  (Currently using proxy metrics = $0.00 — ragas NOT installed)")

# ── Grand total ───────────────────────────────────────────────────────────────
print()
print("=" * 55)
print(f"  WITHOUT RAGAS (proxy metrics, current setup) : ${answer_gen_cost:.4f}")
print(f"  WITH    RAGAS (if installed later)           : ${answer_gen_cost + ragas_cost:.4f}")
print("=" * 55)
print()
print("NOTE: sentence-transformers embedding is LOCAL → $0 cost")
print("NOTE: gpt-4o-mini is cheapest capable model; gpt-4o = ~10× more expensive")
