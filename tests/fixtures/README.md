# tests/fixtures/

Place the 4 clinical PDF documents here for CI evaluation.
Each PDF filename must match its `doc_id` in `src/ingestion/config.py`:

| Filename                                         | doc_id                                          |
|--------------------------------------------------|-------------------------------------------------|
| `metformin_fda_label.pdf`                        | `metformin_fda_label`                           |
| `ada_standards_care_diabetes_6.pdf`              | `ada_standards_care_diabetes_6`                 |
| `ada_standards_care_diabetes_9.pdf`              | `ada_standards_care_diabetes_9`                 |
| `jnc8_guidelines_manage_hypertension_original.pdf` | `jnc8_guidelines_manage_hypertension_original` |

## How to populate for CI

**Option A — DVC remote (recommended):**
Add `DVC_REMOTE_URL` as a GitHub Actions secret. The CI workflow calls `dvc pull data/raw/`
and the ingestion step picks up the PDFs.

**Option B — Commit small test PDFs:**
Place minimal single-page PDFs here for fast CI runs (full eval quality will be lower).

**Option C — Cloud Qdrant for eval:**
Skip the local ingestion step and point `QDRANT_URL` to your qdrant.cloud cluster
(where data is already indexed). Set `QDRANT_URL` and `QDRANT_API_KEY` as GitHub secrets.
The eval job will query the cloud collection directly.

PDFs are **not committed to git** because they are large binary files managed externally.
