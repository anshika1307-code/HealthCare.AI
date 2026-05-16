# Embedding & Indexing — Implementation Plan

> **Scope:** Everything from `Chunk` objects (output of `preprocessor.py`) to vectors stored in Qdrant,
> plus the A/B embedding experiment tracking via MLflow (per `decision.md`).

---

## 1. Architecture Flow

```
PreprocessingPipeline.run()
        │
        ▼ list[Chunk]  (text + metadata)
┌───────────────────────┐
│  ChunkIDGenerator     │  Deterministic UUID5 → stable across re-ingestion
└──────────┬────────────┘
           │ list[IndexableChunk]  (chunk + id)
           ▼
┌───────────────────────┐
│  Embedder             │  Abstract base — OpenAIEmbedder or BGEEmbedder
│  (batched, retried)   │  Batch=100, exponential backoff on 429
└──────────┬────────────┘
           │ list[(id, vector, payload)]
           ▼
┌───────────────────────┐
│  QdrantIndexer        │  Idempotent upsert — same ID = overwrite
│  (upsert_batch)       │  Text stored in payload["text"] for reranker
└──────────┬────────────┘
           │
           ▼
    Qdrant Collection
    "healthcare_chunks"

After all docs indexed:
           │
           ▼
┌───────────────────────┐
│  build_bm25_index.py  │  Scrolls Qdrant → saves BM25Corpus pickle
└───────────────────────┘
```

---

## 2. New Files

```
src/embedding/
├── __init__.py
├── base.py            # Abstract Embedder protocol + ChunkIDGenerator
├── openai_embedder.py # OpenAI text-embedding-3-small (default)
├── bge_embedder.py    # BGE-base-en-v1.5 (local, free — A/B candidate)
└── indexer.py         # QdrantIndexer: idempotent batch upsert

scripts/
├── create_qdrant_collection.py   # One-time collection + payload index setup
└── run_ingestion.py              # End-to-end runner: PDF → embed → index → BM25
```

---

## 3. Key Design Decisions & Rationale

### 3.1 Abstract Embedder Interface (Protocol)

**Decision:** Define a `Protocol` (structural typing) rather than an ABC.

```python
class Embedder(Protocol):
    def embed_batch(self, texts: list[str]) -> list[list[float]]: ...
    @property
    def dimensions(self) -> int: ...
    @property
    def model_name(self) -> str: ...
```

**Reason:** `decision.md` explicitly requires A/B between BGE and text-embedding-3-small.
A Protocol means swapping providers requires **zero changes** in `indexer.py` or `run_ingestion.py`.
Tests can inject a `MockEmbedder` without inheriting from a base class.

---

### 3.2 Deterministic Chunk ID (UUID5)

```python
import uuid
NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")  # URL namespace

def make_chunk_id(doc_id: str, chunk_index: int) -> str:
    key = f"{doc_id}::{chunk_index}"
    return str(uuid.uuid5(NAMESPACE, key))
```

**Reason:** Ingestion must be **idempotent** — re-running without duplicating vectors.
UUID5 is deterministic: same inputs → same ID → Qdrant upsert overwrites cleanly.
UUID4 (random) would create duplicate points on every re-ingestion run.

---

### 3.3 Qdrant Payload Schema

Every point stored with:
```python
payload = {
    "text":                    chunk.text,      # for reranker batch fetch
    "document_id":             ...,
    "document_name":           ...,
    "doc_type":                ...,             # "fda"|"ada"|"jnc" — filter routing
    "page_number":             ...,
    "section_name":            ...,
    "section_number":          ...,
    "is_table":                ...,
    "table_number":            ...,
    "evidence_grade":          ...,
    "recommendation_strength": ...,
    "recommendation_number":   ...,
    "safety_flag":             ...,             # boosts safety chunks at retrieval
    "chunk_index":             ...,
    "char_count":              ...,
}
```

**Reason:** Storing `text` in payload = reranker fetches full text via `get_by_ids()`
without a second embed call. `safety_flag` enables retrieval boosting.
`doc_type` enables `filter_fields` routing in `DenseConfig`.

**Payload Indexes (for fast filtering):**
```
document_id  → KEYWORD index
doc_type     → KEYWORD index
safety_flag  → BOOL index
is_table     → BOOL index
```
Without payload indexes, Qdrant scans all points for filter conditions — O(n) not O(log n).

---

### 3.4 Batching & Retry Strategy

```
Batch size : 100 chunks/call  (configs/embedding.py)
Retry on   : RateLimitError   → exponential backoff 1s → 2s → 4s, max 3 attempts
Retry on   : APITimeoutError  → same backoff
Fail fast  : AuthenticationError → no retry (wrong key won't fix itself)
Library    : tenacity (already in typical OpenAI Python client installs)
```

**Reason:** 100 × 512 tokens = 51,200 tokens/call → ≈ 20 calls/min needed.
OpenAI free-tier: 1M tokens/min → plenty of headroom.
Exponential backoff (not fixed sleep) prevents thundering herd if many batches hit 429.

---

### 3.5 MLflow Tracking for A/B Experiment

**Decision:** Log each full ingestion run as an MLflow experiment run. (`decision.md`: "use MLflow — Model Registry to track the experiment")

```
Experiment : "embedding_model_ab"
Run params :
    embedding_model      "text-embedding-3-small"
    provider             "openai"
    dimensions           1536
    batch_size           100
    normalize            True
    total_docs           4

Run metrics :
    total_chunks_indexed     int
    total_embedding_time_s   float
    avg_batch_time_s         float
    failed_batches           int

Run tags :
    run_date             ISO timestamp
    git_sha              current HEAD (if git available)
```

Later, when RAGAS scores are logged, they will be added to the **same run** so the comparison is:
`text-embedding-3-small run → RAGAS faithfulness=0.84` vs `BGE run → RAGAS faithfulness=0.79`
(or vice versa) — giving a single source of truth in MLflow UI.

---

### 3.6 Idempotent Collection Creation

```python
# create_qdrant_collection.py
client.recreate_collection(   # or create_collection with on_disk_payload
    collection_name="healthcare_chunks",
    vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
)
# Then create payload indexes separately (Qdrant creates them async)
client.create_payload_index("healthcare_chunks", "document_id", PayloadSchemaType.KEYWORD)
client.create_payload_index("healthcare_chunks", "safety_flag",  PayloadSchemaType.BOOL)
```

**Args:** `--force-recreate` flag drops and recreates (for fresh A/B run). Default: create only if not exists.

---

## 4. File-by-File Implementation Spec

### `src/embedding/base.py`
- `Embedder` Protocol: `embed_batch()`, `dimensions`, `model_name`
- `IndexableChunk` dataclass: adds `chunk_id: str` to `Chunk`
- `ChunkIDGenerator`: `make_id(doc_id, chunk_index)` → UUID5

### `src/embedding/openai_embedder.py`
- `OpenAIEmbedder(config=EMBEDDING_CONFIG)`
- `embed_batch(texts: list[str]) → list[list[float]]`
- Uses `openai.embeddings.create(model=..., input=texts)`
- L2-normalise output if `config.normalize=True`
- `tenacity.retry` on `RateLimitError` / `APITimeoutError`

### `src/embedding/bge_embedder.py`
- `BGEEmbedder(config=EMBEDDING_CONFIG)` — `SentenceTransformer("BAAI/bge-base-en-v1.5")`
- Same interface — `dimensions=768` hardcoded (BGE native)
- Local CPU inference, no API key, no rate limit
- Used for A/B comparison run

### `src/embedding/indexer.py`
- `QdrantIndexer(client, collection_name)`
- `upsert(indexable_chunks, embeddings)` → batch `PointStruct` upsert
- `_build_payload(chunk)` — maps `Chunk.metadata` to payload dict + adds `text` + `doc_type`
- Returns `(success_count, failed_ids)` for MLflow logging

### `scripts/create_qdrant_collection.py`
- CLI: `--collection`, `--dimensions`, `--distance`, `--force-recreate`
- Reads dimensions from `EMBEDDING_CONFIG` by default

### `scripts/run_ingestion.py`
- CLI: `--docs-dir`, `--provider` (`openai`|`bge`), `--mlflow-run-name`, `--dry-run`
- `--dry-run`: preprocesses + embeds first batch only, no Qdrant write (for testing)
- Iterates over `DOCUMENTS` list from `configs/ingestion.py`
- After all upserts: calls `build_bm25_index()` inline
- Exits with code 1 if any doc fails (so CI can detect ingestion failures)

---

## 5. Configs Updates Needed

### `configs/embedding.py` — add 2 fields
```python
provider: str = "openai"
# "openai" → OpenAIEmbedder  (requires OPENAI_API_KEY env var)
# "bge"    → BGEEmbedder     (local, free, ~400MB RAM)

mlflow_experiment_name: str = "embedding_model_ab"
```

### `configs/ingestion.py` — add document registry
```python
@dataclass
class DocumentEntry:
    doc_id: str
    pdf_path: str   # relative to project root data/raw/

DOCUMENTS: list[DocumentEntry] = [
    DocumentEntry("metformin_fda_label",
                  "data/raw/metformin_fda_label.pdf"),
    DocumentEntry("ada_standards_care_diabetes_6",
                  "data/raw/ada_standards_care_diabetes_6.pdf"),
    DocumentEntry("ada_standards_care_diabetes_9",
                  "data/raw/ada_standards_care_diabetes_9.pdf"),
    DocumentEntry("jnc8_guidelines_manage_hypertension_original",
                  "data/raw/jnc8_guidelines_manage_hypertension_original.pdf"),
]
```

---

## 6. Implementation Order

| # | Task | File | Effort |
|---|------|------|--------|
| 1 | Add `provider` + `mlflow_experiment_name` to `configs/embedding.py` | `configs/embedding.py` | S |
| 2 | Add `DocumentEntry` + `DOCUMENTS` to `configs/ingestion.py` | `configs/ingestion.py` | S |
| 3 | Protocol + `ChunkIDGenerator` + `IndexableChunk` | `src/embedding/base.py` | S |
| 4 | `OpenAIEmbedder` — batched, retried, normalised | `src/embedding/openai_embedder.py` | M |
| 5 | `BGEEmbedder` — local SentenceTransformer | `src/embedding/bge_embedder.py` | S |
| 6 | `QdrantIndexer` — idempotent batch upsert | `src/embedding/indexer.py` | M |
| 7 | Collection creation script | `scripts/create_qdrant_collection.py` | S |
| 8 | Full ingestion runner with MLflow | `scripts/run_ingestion.py` | M |

**Total estimated effort: ~1 day**

---

## 7. What This Unlocks

| After this... | These become possible |
|---|---|
| Chunks in Qdrant | Dense search testable end-to-end |
| BM25 corpus built | Full hybrid retrieval testable |
| MLflow run logged | A/B embedding comparison ready |
| run_ingestion.py working | RAGAS eval can run (full RAG loop) |
| CI can call run_ingestion | Integration tests against real data |
