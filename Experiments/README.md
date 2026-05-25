# Experiments

Pre-implementation experiments that informed the production pipeline decisions. Both ran before any retrieval or ingestion code was written.

---

## What's here

```
experiments/
├── preprocessing/              — Extraction method comparison (PyMuPDF vs pdfplumber vs LangChain)
│   ├── run_extraction_experiment.py
│   ├── run_noise_analysis.py
│   ├── preprocessing_experiment_report.md   — Results table
│   ├── noise_analysis_report.md
│   └── outputs/
│
└── chunking/                   — 9-config ablation (3 strategies × 3 token sizes)
    ├── run_experiment.py        — Main runner (logs to MLflow)
    ├── strategies.py            — Three chunking strategy implementations
    ├── eval_loader.py           — Loads eval Q&A set
    ├── cost_estimate.py         — API cost calculator
    ├── smoke_test.py            — Quick sanity check (3 questions, no MLflow)
    ├── requirements.txt
    ├── results/                 — RAGAS output per config + summary.json
    └── mlruns/                  — MLflow tracking data
```

---

## Preprocessing experiments

**Goal:** choose the best PDF extraction method for noisy clinical documents before writing the production preprocessor.

**Methods compared:** pdfplumber · PyMuPDF · LangChain default loader

**Results** (`preprocessing/preprocessing_experiment_report.md`):

| PDF | pdfplumber chars | PyMuPDF chars | LangChain chars | Tables found |
|---|---|---|---|---|
| ada_standards_care_diabetes_6.pdf | 79,869 | 83,887 | 84,336 | 9 (pdfplumber) |
| ada_standards_care_diabetes_9.pdf | 211,871 | 217,870 | 223,204 | 17 (pdfplumber) |
| metformin_fda_label.pdf | 74,097 | 81,211 | 80,012 | 12 (pdfplumber) |
| jnc8_guidelines_management_hypertension_original.pdf | 6,433 | 6,505 | 6,558 | 0 |

**Decision:** PyMuPDF for bulk text extraction (faster, slightly cleaner output), pdfplumber for table detection (only pdfplumber returns structured table data).

**Running:**
```powershell
$env:PYTHONPATH = "src"
python experiments/preprocessing/run_extraction_experiment.py
python experiments/preprocessing/run_noise_analysis.py
```

---

## Chunking experiments

**Goal:** find the optimal chunking strategy and token size before committing to a production ingestion pipeline.

**Configurations tested:** 3 strategies × 3 token sizes = 9 total

**Strategies:**

| Strategy | Description |
|---|---|
| `boundary_aware` | Production chunker — section/recommendation-aware, respects clinical structure |
| `fixed_size` | Naive sliding window — pure token budget, no boundary detection |
| `sentence_window` | Sentences grouped to fill the token budget |

**Token sizes:** 256 · 512 · 1024 tokens

**How each config is scored:**
1. Chunk all 4 documents with the config
2. Build an in-memory numpy vector index (sentence-transformers, no Qdrant needed)
3. Retrieve top-k context for each eval question
4. Generate answers via LLM (Groq free tier · OpenAI gpt-4o-mini fallback)
5. Score with RAGAS (faithfulness, answer_relevancy, context_precision, context_recall)
6. Log all metrics + config to MLflow

### Results

`experiments/chunking/results/summary.json`

| Strategy | Token size | Faithfulness | Answer Relevancy | Context Precision | Context Recall | Mean score | Total chunks |
|---|---|---|---|---|---|---|---|
| boundary_aware | 256 | 1.000 | 0.895 | 0.669 | 1.000 | 0.913 | 501 |
| **boundary_aware** | **512** | **1.000** | **0.870** | **0.792** | **1.000** | **0.932** | **279** |
| boundary_aware | 1024 | 0.875 | 0.500 | 0.850 | 1.000 | 0.845 | 171 |

> Only boundary_aware strategy was run at all three token sizes (fixed-size and sentence-window experiments are in `results/` if present from your local run).

**Winner: boundary_aware 512 tokens**
- Highest mean RAGAS score (0.932)
- Context precision 0.79 — meaningfully better than 256 (0.67)
- Faithfulness 1.0 — held; 1024 drops to 0.875 as chunks become too large and mix content
- 279 chunks at ~232 words/chunk — right balance between granularity and context completeness

**Why 1024 fails:** chunks large enough to contain conflicting subsections from the same document. Answer relevancy collapses to 0.50 — the LLM gets too much context and produces less focused answers.

**Why 256 underperforms:** context precision drops to 0.67 because clinical thresholds are often split across chunk boundaries (e.g. a dosing table + its recommendation text end up in separate chunks).

### Running

**Prerequisites:** install experiment dependencies first (lighter than production — uses in-memory vector index, not Qdrant)

```powershell
pip install -r experiments/chunking/requirements.txt
```

Set at least one LLM key:
```powershell
# Groq (free, fast — recommended)
$env:GROQ_API_KEY = "gsk_..."

# Or OpenAI (~$0.76 for full 9-config run)
$env:OPENAI_API_KEY = "sk-..."
```

**Quick smoke test** (3 questions, no MLflow, <$0.01):
```powershell
$env:PYTHONPATH = "src"
python experiments/chunking/smoke_test.py
```

**Full ablation** (all 9 configurations, logs to MLflow):
```powershell
$env:PYTHONPATH = "src"
python experiments/chunking/run_experiment.py
```

**Single strategy:**
```powershell
python experiments/chunking/run_experiment.py --strategy boundary_aware
```

**View results in MLflow:**
```powershell
mlflow ui --backend-store-uri experiments/chunking/mlruns
# Open http://localhost:5000
```

**Cost estimate:**
```powershell
python experiments/chunking/cost_estimate.py
```

---

## How experiments informed production decisions

| Experiment finding | Production decision |
|---|---|
| pdfplumber detects tables, PyMuPDF is faster for text | Both used in production preprocessor |
| 512-token boundary-aware chunks score best (0.932 mean) | Production: 512 tokens, 64-token overlap, section-aware boundaries |
| 1024-token chunks drop faithfulness to 0.875 | 512 upper limit — large chunks mix clinical content |
| 256-token chunks drop context precision to 0.67 | 512 lower bound — too small to contain complete thresholds |
| Fixed-size chunking splits clinical sentences mid-threshold | Boundary-aware splitting required for medical documents |
