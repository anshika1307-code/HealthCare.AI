# Custom Preprocessing Plan — Healthcare_AI

> Derived from: `preprocessing_specs_dev.md`, `preprocessing_spec_ai.md`, `noise_analysis_report.md`, `preprocessing_experiment_report.md`
> Target documents: `metformin_fda_label.pdf`, `ada_standards_care_diabetes_6.pdf`, `ada_standards_care_diabetes_9.pdf`, `jnc8_guidelines_manage_hypertension_original.pdf`

---

## Extraction Strategy (Confirmed from Experiment Report)

| Document | Primary Extractor | Tables |
|----------|------------------|--------|
| metformin_fda_label.pdf | **PyMuPDF** (81k chars, cleaner flow) | **pdfplumber** (12 tables found) |
| ada_standards_care_diabetes_6.pdf | **PyMuPDF** (83k chars) | **pdfplumber** (9 tables) |
| ada_standards_care_diabetes_9.pdf | **PyMuPDF** (217k chars) | **pdfplumber** (17 tables) |
| jnc8_guidelines_manage_hypertension_original.pdf | **PyMuPDF** (raw, then fix column ordering) | **pdfplumber** |

> [!NOTE]
> PyMuPDF is used for all text flow. pdfplumber is called separately, only for tables, and the table text is injected back at the correct position.

---

## Document-by-Document Noise Inventory & Rules

### Document 1: `metformin_fda_label.pdf`
*(Highest noise: 143 hits, 15.31% removal — most complex document)*

| # | Noise / Problem | Source | Regex / Rule |
|---|----------------|--------|-------------|
| 1 | Repeating header (every page) | Dev obs #1, AI spec 1.1 P1 | `r"This label may not be the latest approved by FDA\..*?https://www\.fda\.gov/drugsatfda"` (DOTALL) |
| 2 | Footer: page number (bottom center) | Dev obs #2, noise report: 36 hits | `r"^\s*\d{1,3}\s*$"` on a line |
| 3 | Footer: Reference ID | Dev obs #2, AI spec 1.1 P3, noise report: 35 hits | `r"Reference ID:\s*\d+"` |
| 4 | Footer joins with next line | AI spec 3.1 #4 | After header strip, re-check if `Reference ID:...` is glued to content text — split on `Reference ID:` first |
| 5 | Duplicate heading on page 1 | Dev obs #7 | Remove `GLUCOPHAGE® (metformin hydrochloride) Tablets and GLUCOPHAGE® XR (metformin hydrochloride) Extended-Release Tablets` from page 1 only |
| 6 | Inline citations like `(see Precautions)`, `(see Table 1)` | Dev obs #4 | `r"\(see\s+[^)]+\)"` — strip |
| 7 | Superscript/subscript artifacts (Cmax, Tmax, footnote letters) | Dev obs #5, AI spec 1.3, noise report: 2 hits | `r"(?<=[a-zA-Z])[a-z]\b(?=\s)"` — cautious strip; preserve units like "mg/dL" |
| 8 | Vitamin B naming variants (B 12, B12, vitamin B12) | Dev obs #10 | Normalize: `r"[Vv]itamin\s+B\s*[-]?\s*12\b"` → `"Vitamin B12"` |
| 9 | Acronyms (GLUCOPHAGE, AUC) | Dev obs #3, #8 | Abbreviation expansion table (see section below) |
| 10 | Generic URLs from headers | noise report: 35 url_generic hits | `r"https?://\S+"` — strip |
| 11 | Boxed warnings / safety text | Dev general note | Flag lines containing `BOXED WARNING`, `WARNING`, `CONTRAINDICATIONS` → metadata: `safety_flag: true` |

---

### Document 2 & 3: `ada_standards_care_diabetes_6.pdf` & `ada_standards_care_diabetes_9.pdf`
*(Same structure — apply same rules. Section 9 has 51 URL hits vs 3 in Section 6)*

| # | Noise / Problem | Source | Regex / Rule |
|---|----------------|--------|-------------|
| 1 | Repeating header (3 formats, varies left/right page) | Dev obs #2, AI spec 1.1 P2 | `r"diabetesjournals\.org/care\s+.*?S\d+"` and `r"S\d+\s+\w[\w\s]+Diabetes Care Volume.*"` and `r"Diabetes Care Volume \d+.*S\d+\s*$"` |
| 2 | Page numbers embedded in header line | Dev obs #2, noise report: 40 hits (sec6) | Handled as part of header strip above (S97, S98, S99 at line edges) |
| 3 | Figure/diagram references | Dev obs #8 | `r"\(in Fig\.?\s*\d+[\.\d]*\)"` and `r"\bFig\.?\s*\d+\b"` — strip |
| 4 | In-text citation numbers `(70)` | Dev obs #9, AI spec 1.4 | `r"\(\d+\)"` — strip |
| 5 | Reference section at end | Dev obs #10 | Detect `^References\s*$` as a sentinel line → discard everything after it |
| 6 | 3-column PDF layout → broken/interleaved lines | Dev obs #5 | PyMuPDF `page.get_text("dict")` with block sorting by `(y0, x0)` to reorder columns correctly |
| 7 | Evidence grades at end of paragraphs (A, B, C, D, E) | Dev obs #7 | Extract grade letter before stripping: `r"\s+([A-E])\s*$"` → metadata: `evidence_grade: "A"` |
| 8 | Page 1 cluttered / low-info | Dev obs #3 | Skip page 1 entirely (page index 0) |
| 9 | Abbreviations: CGM, etc | Dev obs #11 | Abbreviation expansion table |
| 10 | URLs (doi + generic) | noise report: 2 doi + 51 url_generic (sec9) | `r"https?://\S+"` and `r"doi:\S+"` — strip |
| 11 | Copyright line | noise report: 1 hit | `r"©\s*\d{4}\s+American Diabetes Association"` — strip |

---

### Document 4: `jnc8_guidelines_manage_hypertension_original.pdf`
*(No AI spec for this doc — dev observations only. Most structurally complex.)*

| # | Noise / Problem | Source | Rule |
|---|----------------|--------|------|
| 1 | 2-column layout → wrong reading order | Dev obs | PyMuPDF block-based extraction with `sort=True` or manual column split by `x0 < page_width/2` for left column, `x0 >= page_width/2` for right column |
| 2 | 3-line footer (every page) | Dev obs | Detect bottom-region lines by `y0 > page_height * 0.92` → strip. Alternatively exact patterns: `r"\d{3}\s+JAMA\s+February"`, `r"Copyright\s+©\s+2014"`, `r"Downloaded from jamanetwork"` |
| 3 | Page 1 — summary/key points section | Dev obs | Skip page 1 (page index 0), OR detect `^Key Points$` sentinel and skip until main content starts |
| 4 | Content order broken across columns | Dev obs | After column-aware extraction, re-stitch paragraphs by reading left column top-to-bottom, then right column top-to-bottom, per page |
| 5 | Inline references `(in Table 1)`, `(70)` | Dev obs | `r"\(in\s+Table\s+\d+\)"` and `r"\(\d+\)"` — strip |
| 6 | Recommendations as chunk boundaries | Dev obs | Detect `r"^Recommendation\s+\d+"` → this is a hard chunk boundary. Each recommendation = one chunk |
| 7 | Recommendation grade tagging | Dev obs | After `Recommendation N` text, detect `r"(Strong|Expert Opinion|Moderate)\s+Recommendation\s*[–-]\s*Grade\s+([A-E])"` → metadata: `grade`, `recommendation_strength` |
| 8 | Negative/safety instructions | Dev obs | Flag sentences containing `Avoid`, `Do not`, `contraindicated` → metadata: `safety_flag: true` |
| 9 | Full flowchart on page 512 | Dev obs | Skip or extract as plain alt-text. PyMuPDF `page.get_text()` on that page will be near-empty → log as `skipped_content: ["flowchart_p512"]` |
| 10 | Article Information + References at end | Dev obs | Detect `^ARTICLE INFORMATION\s*$` sentinel → discard everything after |
| 11 | Abbreviation list at start (ACEI, ARB, BP…) | Dev obs | Parse this list once → seed abbreviation expansion table for this document |

---

## Cross-Document Rules (Apply to All)

> [!IMPORTANT]
> These apply after document-specific cleaning.

| Rule | Logic |
|------|-------|
| **Broken line rejoining** | If a line does NOT end with `.`, `?`, `!`, `:`, or is not a heading → join with next line. This fixes PDF hard-wrap artifacts. |
| **Hyphenated word join** | `r"(\w+)-\n(\w+)"` → join as one word. E.g. `cardio-\nvascular` → `cardiovascular` |
| **Collapse whitespace** | `re.sub(r" {2,}", " ", text)` and `re.sub(r"\n{3,}", "\n\n", text)` |
| **Trim lines** | Strip leading/trailing whitespace per line |
| **Abbreviation expansion** | On first occurrence, expand and note: `"CGM (continuous glucose monitoring)"` → keep both forms; record in per-document abbreviation map |
| **Medical term normalization** | Normalize variants (see table below) — do not change meaning |
| **Safety flag propagation** | Any sentence with BOXED WARNING / Avoid / Do not / contraindicated → `safety_flag: true` in chunk metadata |

### Medical Term Normalization Map

| Variants | Normalized Form |
|----------|----------------|
| `Vitamin B 12`, `B12`, `vitamin B12`, `Vit B-12` | `Vitamin B12` |
| `blood pressure`, `BP`, `blood-pressure` | `blood pressure (BP)` |
| `HbA1c`, `HbA 1c`, `hemoglobin A1c`, `glycated hemoglobin` | `HbA1c` |
| `continuous glucose monitoring`, `CGM` | `CGM (continuous glucose monitoring)` |
| `GLUCOPHAGE`, `metformin hydrochloride` | `metformin` (with alias note) |
| `type 2 diabetes`, `T2D`, `T2DM` | `type 2 diabetes (T2DM)` |

---

## Table Handling

From dev spec + AI spec + experiment (pdfplumber found: 12 Metformin, 9 ADA-6, 17 ADA-9 tables):

```
For each table extracted by pdfplumber:
  1. Get table as list of rows (list of lists)
  2. First row = header row
  3. Convert to natural language sentences:
     "For [header_col_1] = [val], [header_col_2] is [val], [header_col_3] is [val]."
  4. Prepend: "Table [N]: [surrounding section heading]"
  5. Store as a separate chunk with metadata:
     - table_number, page_number, section_name, document_id
  6. In the main text flow, replace the original table region with a placeholder:
     "[See Table N: <section_heading>]"
```

> [!WARNING]
> Do NOT embed the full raw table text inline — it destroys semantic coherence for the surrounding paragraphs. Keep it as a separate chunk.

---

## Metadata Schema (Per Chunk)

```python
{
    "document_id": str,          # e.g. "metformin_fda_label"
    "document_name": str,        # human-readable
    "page_number": int,
    "section_name": str | None,  # e.g. "CLINICAL PHARMACOLOGY"
    "section_number": str | None,# e.g. "6.1"
    "subsection_name": str | None,
    "subsection_number": str | None,
    "is_table": bool,
    "table_number": int | None,
    "figure_number": int | None,
    "evidence_grade": str | None,# "A", "B", "C", "D", "E"
    "recommendation_strength": str | None, # "Strong", "Moderate", "Expert Opinion"
    "recommendation_number": int | None,   # JNC only
    "safety_flag": bool,         # True if boxed warning / avoid / contraindicated
    "chunk_index": int,          # position within document
    "char_count": int,
}
```

---

## Chunk Boundary Strategy

```
Priority order (highest wins):
  1. Recommendation N (JNC) → hard boundary, always one chunk
  2. Uppercase section heading (FDA label: DESCRIPTION, INDICATIONS…)
  3. Numbered section heading (ADA: 6.1, 9.2…)
  4. Table → always its own chunk
  5. 512-token soft boundary with 64-token overlap (fallback)
```

> Do NOT split mid-sentence. If a 512-token boundary lands mid-sentence, extend to the next sentence end.

---

## Safety Content Flagging Logic

```python
SAFETY_TRIGGERS = [
    r"\bBOXED WARNING\b",
    r"\bWARNING[S]?\b",
    r"\bCONTRAINDICATION[S]?\b",
    r"\bAvoid\b",
    r"\bDo not\b",
    r"\bshould not\b",
    r"\bnot recommended\b",
    r"\bside effect[s]?\b",
    r"\badverse reaction[s]?\b",
]
# If any trigger found in chunk text → metadata["safety_flag"] = True
```

---

## Full Pipeline Architecture

```
PDF file
  │
  ├─► PyMuPDF (page-by-page)
  │     └─► apply_column_fix(page)         # for ADA (3-col) and JNC (2-col)
  │         └─► raw_text per page
  │
  ├─► pdfplumber (same file, same pages)
  │     └─► extract_tables(page)
  │         └─► table_rows list
  │
  ▼
[Stage 1] header_footer_remover(text, doc_id)
  └─► doc-specific regex patterns
  └─► returns: cleaned_text

[Stage 2] reference_section_remover(text, doc_id)
  └─► detect sentinel line (References / ARTICLE INFORMATION)
  └─► truncate everything after it

[Stage 3] inline_noise_remover(text)
  └─► strip: page numbers, DOIs, URLs, inline citations (70), figure refs
  └─► strip: footnote superscripts

[Stage 4] line_rejoiner(text)
  └─► hyphen-join broken words
  └─► sentence-continuation join (no terminal punctuation → join next line)

[Stage 5] normalizer(text, doc_id)
  └─► term normalization map
  └─► whitespace collapse

[Stage 6] abbreviation_expander(text, doc_id)
  └─► first-occurrence expansion
  └─► returns: expanded_text, abbreviation_map (stored in metadata)

[Stage 7] metadata_extractor(text, doc_id)
  └─► section headings → section_name, section_number
  └─► evidence grades → evidence_grade
  └─► recommendation tags → recommendation_number, strength
  └─► safety triggers → safety_flag

[Stage 8] table_converter(table_rows, section_name, table_num)
  └─► rows → natural language sentences
  └─► returns: table_chunk (with metadata)

[Stage 9] chunker(text, metadata)
  └─► apply hard boundaries first
  └─► 512-token soft split with 64-token overlap
  └─► returns: list of (chunk_text, chunk_metadata)
```

---

## Open Questions (Need Decisions)

| # | Question | Recommendation |
|---|----------|---------------|
| Q1 | ADA page 1 — discard or keep? | **Discard** — cluttered, low clinical value |
| Q2 | JNC flowchart (page 512) — extract or skip? | **Skip for prototype** — log as `skipped_content`. If needed later, use `hi_res` Unstructured or a multimodal model |
| Q3 | JNC abbreviation list at start — parse into expansion table? | **Yes** — parse it programmatically as a first pass, seed `abbreviation_map` for JNC doc |
| Q4 | ADA evidence grade letters (A-E at paragraph end) — strip or metadata only? | **Keep in metadata** (`evidence_grade`), strip from text body |
| Q5 | JNC negative instructions — flag only or also emphasize in chunk? | **Flag via metadata** (`safety_flag: true`) + keep text as-is. Retrieval layer will boost safety-flagged chunks |
| Q6 | Table injection strategy — inline placeholder or separate chunk only? | **Both**: placeholder in text flow + separate table chunk with same metadata, linked by `table_number` |
