# Custom Preprocessing Plan — Healthcare_AI

> Sources: `preprocessing_specs_dev.md`, `preprocessing_spec_ai.md` (including new §6 for JNC8), `noise_analysis_report.md`, `preprocessing_experiment_report.md`
> Target docs: `metformin_fda_label.pdf`, `ada_standards_care_diabetes_6.pdf`, `ada_standards_care_diabetes_9.pdf`, `jnc8_guidelines_manage_hypertension_original.pdf`

---

## Answers to Dev Questions

### Q1: Are A, B, C, D, E in ADA docs evidence grades?
**YES — confirmed from raw PyMuPDF extracted text.**

From `ada_standards_care_diabetes_6/pymupdf/text.txt`, lines 41–47:
```
6.1 Assess glycemic status... E
6.2 Assess glycemic status at least quarterly... E
```
Lines 565–611:
```
6.5a An A1C goal for many non-pregnant adults of <7% ... A
6.5b If using ambulatory glucose profile/GMI ... B
6.6  On the basis of health care professional judgment ... B
6.7  Less stringent A1C goals ... B
6.8  Reassess glycemic targets based on individualized criteria ... E
```
Each numbered ADA recommendation (`6.1`, `6.5a`, `9.1`, `9.3` etc.) ends with a **single uppercase letter on the same line** — this is the ADA evidence grade. Same pattern confirmed in ADA-9.

**Grade system:**
- `A` — Clear evidence from well-conducted RCTs
- `B` — Supportive evidence from well-conducted cohort studies
- `C` — Supportive evidence from poorly controlled studies
- `D` — Expert consensus or clinical experience
- `E` — Expert consensus, no evidence

**Extraction regex:** `r"(?<=\s)([A-E])\s*$"` at end of a recommendation line (after the recommendation text, preceded by whitespace).

**Action (confirmed by dev):** Keep grade in `metadata["evidence_grade"]`, strip from the text body.

---

### Q2: JNC8 grades — confirmed?
**YES.** From dev observations, each JNC Recommendation block ends with a grade line:
```
Recommendation 1
In the general population aged 60 years or older...
Strong Recommendation – Grade A
```
Grade system: `A`, `B`, `C` (evidence quality). Strength: `Strong`, `Moderate`, `Expert Opinion`.

**Extraction regex:**
```python
r"(Strong|Moderate|Expert Opinion)\s+Recommendation\s*[–\-]\s*Grade\s+([A-C])"
```
**Action:** Extract both `recommendation_strength` and `evidence_grade` into metadata. Strip the grade line from chunk text.

---

### Q3: Should the reference list at the end be removed?
**YES — remove it.** Reasoning for this RAG use case:

- Reference lists are citation metadata (author, journal, year) — not clinical content.
- They will poison retrieval: a query about "metformin dosing" could retrieve a chunk that is just a bibliography entry like *"Nathan DM. Diabetes Care 2009..."* — semantically meaningless.
- They constitute a large portion of text (ADA docs have dozens of refs), diluting the useful corpus.
- If traceability is needed, source doc + page number in chunk metadata already handles attribution.

**Action:** Detect sentinel lines and discard everything after:
- ADA: `r"^References\s*$"`
- JNC: `r"^ARTICLE INFORMATION\s*$"` or `r"^REFERENCES\s*$"`
- Metformin FDA: References are inline numbered — strip inline `(1)`, `[12]` patterns instead.

---

### Q4: Is `GLUCOPHAGE → metformin` the correct normalization?
**No — this normalization is wrong for a pharmacist tool. Revise it.**

Here's why: `GLUCOPHAGE` is the **brand name**. `metformin hydrochloride` is the **salt form** (slightly different from `metformin base`). A pharmacist querying "GLUCOPHAGE XR dosing" vs "metformin ER dosing" expects different answers because brand labels have specific formulation details.

**Corrected normalization rules:**

| Variants | Action | Reason |
|----------|--------|--------|
| `GLUCOPHAGE`, `GLUCOPHAGE XR` | Keep as-is + add alias `metformin (brand: GLUCOPHAGE)` to abbreviation_map | Brand name must remain for pharmacist queries |
| `metformin hydrochloride` | Normalize → `metformin hydrochloride` (do not shorten to `metformin`) | Salt form is pharmacologically specific |
| `metformin HCl` | Normalize → `metformin hydrochloride` | HCl is abbreviation of hydrochloride |
| `Metformin`, `METFORMIN` | Normalize → `metformin` (lowercase) | Casing only |

**Rule:** For brand names, **expand and alias, never collapse.** Collapsing `GLUCOPHAGE → metformin` would cause a query about brand-specific instructions to retrieve generic metformin content — clinically dangerous in a pharmacist tool.

---

### Q5: Abbreviation detection logic + term normalization logic

#### Abbreviation Detection & Expansion

Two patterns cover 95% of how abbreviations are introduced in clinical documents:

**Pattern A — Full form first, abbreviation in parentheses (most common):**
```
continuous glucose monitoring (CGM)
angiotensin-converting enzyme (ACE) inhibitor
chronic kidney disease (CKD)
```
Regex: `r"([A-Za-z][a-z\s\-]+)\s+\(([A-Z]{2,6})\)"`
→ Extract: `abbreviation_map[group(2)] = group(1)` → e.g. `{"CGM": "continuous glucose monitoring"}`

**Pattern B — Abbreviation first, full form after (less common, JNC abbreviation table):**
```
ACEI  angiotensin-converting enzyme inhibitor
ARB   angiotensin receptor blocker
```
Regex: `r"^([A-Z]{2,6})\s{2,}(.+)$"` (multi-space separator, in the abbreviation list block)
→ Parse this block once at document start, seed the map.

**Expansion logic (first-occurrence only):**
```python
def expand_abbreviations(text, abbrev_map):
    expanded = set()
    for abbrev, full_form in abbrev_map.items():
        # Only expand FIRST occurrence
        pattern = rf"\b{re.escape(abbrev)}\b"
        def replacer(m):
            if abbrev not in expanded:
                expanded.add(abbrev)
                return f"{full_form} ({abbrev})"
            return m.group(0)  # subsequent occurrences: keep as-is
        text = re.sub(pattern, replacer, text)
    return text
```
> **Important:** Do NOT expand inside table headers or section headings — it breaks formatting. Only expand within paragraph body text.

#### Term Normalization Logic

Term normalization is **not** abbreviation expansion — it's about unifying different surface forms of the same concept across documents.

**Algorithm:**
```python
NORMALIZATION_MAP = [
    # (list_of_variants_regex, canonical_form)
    (r"[Vv]itamin\s+B\s*[-]?\s*12\b", "Vitamin B12"),
    (r"\bblood[\s-]pressure\b", "blood pressure"),  # keep lowercase
    (r"\b(HbA\s*1\s*c|hemoglobin A1c|glycated hemoglobin|glycosylated hemoglobin)\b", "HbA1c"),
    (r"\b(T2DM|T2D)\b", "type 2 diabetes (T2DM)"),
    (r"\b(T1DM|T1D)\b", "type 1 diabetes (T1DM)"),
    (r"\bmetformin\s+HCl\b", "metformin hydrochloride"),
]

def normalize_terms(text):
    for pattern, canonical in NORMALIZATION_MAP:
        text = re.sub(pattern, canonical, text)
    return text
```

**Key rule:** Normalization runs **before** abbreviation expansion. Otherwise you risk expanding a partially-normalized term incorrectly.

**What NOT to normalize:**
- Drug dosages: `500 mg`, `850 mg` — never touch numbers with units
- Measurement values: `140 mm Hg`, `90 mg/dL`
- Brand names: as decided in Q4 above

---

## Resolved Open Questions

| # | Question | Decision |
|---|----------|---------|
| Q1 | ADA page 1 — discard or keep? | **Discard** (page index 0) |
| Q2 | JNC flowchart (page 512) | **Skip** — log as `skipped_content: ["flowchart_p512"]`. To keep later: use `hi_res` Unstructured (detectron2 layout model) or GPT-4o vision on that page to generate a textual description |
| Q3 | JNC abbreviation list | **Parse** programmatically as first pass → seed `abbreviation_map` for JNC doc, then remove list from text body |
| Q4 | ADA evidence grades | **Metadata only** — extract to `evidence_grade`, strip letter from text body |
| Q5 | JNC safety instructions | **Flag via metadata** (`safety_flag: true`) + keep text as-is. Retrieval layer boosts safety-flagged chunks |
| Q6 | Table strategy | **Both**: inline placeholder `[See Table N: <section>]` in text flow + separate table chunk linked by `table_number` |

---

## Extraction Strategy

| Document | Text Extractor | Table Extractor | Special Step |
|----------|---------------|----------------|--------------|
| metformin_fda_label.pdf | PyMuPDF | pdfplumber (12 tables) | None |
| ada_standards_care_diabetes_6.pdf | PyMuPDF | pdfplumber (9 tables) | 3-col block sort |
| ada_standards_care_diabetes_9.pdf | PyMuPDF | pdfplumber (17 tables) | 3-col block sort |
| jnc8_guidelines_manage_hypertension_original.pdf | PyMuPDF (`get_text("dict")`) | pdfplumber (0 tables) | 2-col stitch + bbox footer strip |

---

## Document 1: `metformin_fda_label.pdf`
*(143 noise hits, 15.31% removal — highest noise)*

| # | Noise | Regex / Rule |
|---|-------|-------------|
| 1 | Header (every page) | `r"This label may not be the latest.*?https://www\.fda\.gov/drugsatfda"` (DOTALL) |
| 2 | Footer: page number | `r"^\s*\d{1,3}\s*$"` |
| 3 | Footer: Reference ID | `r"Reference ID:\s*\d+"` |
| 4 | Footer glued to content | Split on `Reference ID:` first, then strip |
| 5 | Duplicate heading page 1 | Strip `GLUCOPHAGE® ... Extended-Release Tablets` block on page 0 only |
| 6 | Inline cross-refs | `r"\(see\s+[^)]+\)"` |
| 7 | Superscript artifacts (Cmax footnote letters) | `r"(?<=[a-zA-Z])[a-z]\b(?=[\s,.])"` — cautious; preserve units |
| 8 | Generic URLs | `r"https?://\S+"` |
| 9 | Boxed WARNING / CONTRAINDICATIONS headings | Keep text, set `safety_flag: true` |
| 10 | Inline numbered refs | `r"\(\d{1,3}\)"` |

---

## Document 2 & 3: `ada_standards_care_diabetes_6.pdf` & `ada_standards_care_diabetes_9.pdf`
*(Same structure. Sec9 has 51 URL hits vs 3 in Sec6. Sec9 also has a download line on every page.)*

| # | Noise | Regex / Rule |
|---|-------|-------------|
| 1 | 3-format repeating header | `r"diabetesjournals\.org/care\s+.*?S\d+"` + `r"S\d+\s+\w[\w\s]+Diabetes Care Volume.*"` + `r"Diabetes Care Volume \d+.*S\d+\s*$"` |
| 2 | Download line (ADA-9 every page) | `r"Downloaded from http://diabetesjournals\.org/.*by guest on \d{2} \w+ \d{4}"` |
| 3 | Copyright line | `r"©\s*20\d{2}\s+by the American Diabetes Association"` |
| 4 | DOI / URLs | `r"https?://\S+"` and `r"doi:\S+"` |
| 5 | Figure references | `r"\(in Fig\.?\s*[\d\.]+\)"` and `r"\bFig\.\s*[\d\.]+"` |
| 6 | Inline citations `(70)` | `r"\(\d{1,3}\)"` |
| 7 | Multi-citation ranges `(2–4)`, `(24–29)` | `r"\(\d+[–\-]\d+\)"` |
| 8 | Reference block at end | Sentinel `r"^References\s*$"` → discard after |
| 9 | Page 1 discard | Skip page index 0 entirely |
| 10 | 3-column layout interleave | `page.get_text("dict")` → sort blocks by `(x0_bucket, y0)` where `x0_bucket = 0,1,2` based on thirds of page width |
| 11 | Evidence grades at recommendation end | `r"(?<=\s)([A-E])\s*$"` → extract to `evidence_grade`, strip from text |
| 12 | ADA recommendation numbers | `r"^(\d+\.\d+[a-z]?)\s"` at line start → section boundary marker |

---

## Document 4: `jnc8_guidelines_manage_hypertension_original.pdf`
*(2-column JAMA format — most structurally complex. AI spec now complete.)*

| # | Noise / Problem | Rule |
|---|----------------|------|
| 1 | **2-col reading order** | `page.get_text("dict")` → split blocks: `x0 < page_width/2` = left col, `x0 >= page_width/2` = right col → concat left top-to-bottom, then right top-to-bottom |
| 2 | **3-line JAMA footer** (every page) | Bbox: strip all blocks where `y0 > page_height * 0.92`. Fallback regex: `r"\d{3}\s+JAMA\s+\w+ \d{1,2}, \d{4}"`, `r"Copyright\s+©\s+2014\s+American Medical Association"`, `r"Downloaded from jamanetwork\.com by .+ on \d{2}/\d{2}/\d{4}"` |
| 3 | **JAMA header** (every page) | `r"\d{3}\s+JAMA\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{1,2},\s+\d{4}\s+Volume\s+\d+"` and `r"jama\.com\s*$"` |
| 4 | **Page 1 Key Points / Summary block** | Sentinel `r"^Key Points for Practice\s*$"` (AFP version) or `r"^Summary\s*$"` (JAMA version) → strip block until next body paragraph starts |
| 5 | **Abbreviation list at start** | Regex `r"^([A-Z]{2,6})\s{2,}(.+)$"` multiline → parse into `abbreviation_map`, then remove block |
| 6 | **Inline cross-refs** | `r"\(in\s+(Table\|Figure)\s+\d+\)"` and `r"\(\d{1,3}\)"` |
| 7 | **Soft hyphen word breaks** (`\u00ad`) | `r"(\w+)\u00ad\n(\w+)"` → join; also `r"(\w+)-\n(\w+)"` → join |
| 8 | **Recommendation blocks** | `r"^Recommendation\s+(\d+)\s*$"` → hard chunk boundary; each = one chunk |
| 9 | **Recommendation grade line** | `r"(Strong\|Moderate\|Expert Opinion)\s+Recommendation\s*[–\-]\s*Grade\s+([A-C])"` → extract `recommendation_strength` + `evidence_grade` → strip line from text |
| 10 | **Safety / negative instructions** | `r"\bdo not\b"`, `r"\bAvoid\b"`, `r"\bcontraindicated\b"` → `safety_flag: true` |
| 11 | **Guideline metadata block** | Sentinel `r"^Guideline source:"` → strip block to EOF |
| 12 | **Trailing content** (Article Info + Refs) | Sentinel `r"^ARTICLE INFORMATION\s*$"` or `r"^REFERENCES\s*$"` → discard after |
| 13 | **Flowchart page** | PyMuPDF returns near-empty text on that page → log `skipped_content: ["flowchart"]`, skip |
| 14 | **Section headings** (for chunk boundaries) | Heuristic: line ≤ 8 words + Title-Case + no terminal period + not bullet → soft boundary |

---

## Cross-Document Rules (All Docs, Applied After Doc-Specific Cleaning)

| Rule | Logic |
|------|-------|
| Broken line rejoin | Line not ending in `.?!:` and not a heading → join with next line |
| Soft hyphen join | `r"(\w+)\u00ad\n(\w+)"` → joined word |
| Hard hyphen join | `r"(\w+)-\n(\w+)"` → joined word (only if both parts are lowercase — avoids joining legitimate hyphenated terms like `anti-hypertensive`) |
| Whitespace collapse | `re.sub(r" {2,}", " ")` and `re.sub(r"\n{3,}", "\n\n")` |
| Term normalization | See normalization map — runs first |
| Abbreviation expansion | First-occurrence only — runs after normalization |
| Safety flag scan | Applied per-chunk after chunking |

### Normalization Map (Final — revised per Q4 answer)

| Variants | Canonical Form |
|----------|---------------|
| `Vitamin B 12`, `Vit B-12`, `vitamin B12`, `B12` | `Vitamin B12` |
| `blood-pressure`, `Blood Pressure` | `blood pressure` |
| `HbA 1c`, `hemoglobin A1c`, `glycated hemoglobin`, `glycosylated hemoglobin` | `HbA1c` |
| `T2DM`, `T2D` | `type 2 diabetes (T2DM)` |
| `T1DM`, `T1D` | `type 1 diabetes (T1DM)` |
| `metformin HCl` | `metformin hydrochloride` |
| ~~`GLUCOPHAGE → metformin`~~ | ❌ **Do NOT normalize** — keep brand name, alias in map only |

---

## Table Handling

pdfplumber table counts: Metformin=12, ADA-6=9, ADA-9=17, JNC=0.

```
For each table from pdfplumber:
  1. rows = list of lists; row[0] = header
  2. Convert to NL sentences:
     "For [col1_header] = [val], [col2_header] is [val], [col3_header] is [val]."
  3. Prepend label: "Table N — <section_heading>:"
  4. Store as separate chunk with metadata: {is_table:true, table_number, page_number, section_name}
  5. In main text flow: insert placeholder "[See Table N: <section_heading>]"
     at the position where the table was detected
```

---

## Metadata Schema (Per Chunk)

```python
{
    "document_id": str,               # "metformin_fda_label"
    "document_name": str,             # "Metformin FDA Label"
    "page_number": int,
    "section_name": str | None,       # "CLINICAL PHARMACOLOGY" / "Glycemic Targets"
    "section_number": str | None,     # "6.1", "9.3a"
    "subsection_name": str | None,
    "is_table": bool,
    "table_number": int | None,
    "figure_number": int | None,
    "evidence_grade": str | None,     # "A"–"E" (ADA) or "A"–"C" (JNC)
    "recommendation_strength": str | None,  # "Strong" | "Moderate" | "Expert Opinion" (JNC only)
    "recommendation_number": int | None,    # JNC only
    "safety_flag": bool,              # True = contains warning/avoid/contraindication
    "skipped_content": list[str],     # e.g. ["flowchart_p512"] for logged skips
    "chunk_index": int,
    "char_count": int,
}
```

---

## Chunk Boundary Priority

```
1. [HARD] Recommendation N (JNC) — always one chunk, never split
2. [HARD] Table — always its own chunk
3. [SOFT] Uppercase section heading (FDA: DESCRIPTION, INDICATIONS…)
4. [SOFT] Numbered ADA recommendation (6.1, 9.3a…)
5. [SOFT] Title-Case heading ≤8 words (JNC sections)
6. [FALLBACK] 512-token limit with 64-token overlap
   → never split mid-sentence; extend to next sentence end
```

---

## Safety Flagging

```python
SAFETY_TRIGGERS = [
    r"\bBOXED WARNING\b",
    r"\bWARNING[S]?\b",
    r"\bCONTRAINDICATION[S]?\b",
    r"\bAvoid\b",
    r"\bdo not\b",
    r"\bshould not\b",
    r"\bnot recommended\b",
    r"\badverse reaction[s]?\b",
    r"\bside effect[s]?\b",
]
# Scan per-chunk AFTER chunking. If any trigger matches → metadata["safety_flag"] = True
```

---

## Full Ordered Pipeline

```
INPUT: PDF path + doc_id

EXTRACTION PHASE (per page):
  ├─ PyMuPDF get_text("dict") → block list with bboxes
  │    ├─ [JNC / ADA] apply_column_sort(blocks, page_width, n_cols)
  │    └─ concatenate → raw_page_text
  └─ pdfplumber → extract_tables(page) → table_rows[]

CLEANING PHASE (per document, full text):
  Stage 1  │ abbreviation_list_parser(text, doc_id)   # JNC only — parse abbrev table → map, remove block
  Stage 2  │ header_footer_remover(text, doc_id)       # doc-specific regex patterns
  Stage 3  │ page1_discard(text, doc_id)               # ADA + JNC: remove first page
  Stage 4  │ reference_section_remover(text, doc_id)   # sentinel-based truncation
  Stage 5  │ guideline_metadata_remover(text, doc_id)  # JNC: "Guideline source:" block
  Stage 6  │ inline_noise_remover(text, doc_id)        # URLs, citations, figure refs, page nums
  Stage 7  │ hyphen_line_joiner(text)                  # soft + hard hyphen word join
  Stage 8  │ line_rejoiner(text)                       # non-terminal lines → join next line
  Stage 9  │ normalize_terms(text)                     # normalization map (before abbrev expand)
  Stage 10 │ abbreviation_expander(text, abbrev_map)   # first-occurrence expansion

STRUCTURE EXTRACTION PHASE:
  Stage 11 │ section_heading_detector(text, doc_id)    # tag headings → chunk boundary markers
  Stage 12 │ recommendation_detector(text)             # JNC: extract rec_number + grade → metadata
  Stage 13 │ evidence_grade_extractor(text, doc_id)    # ADA: extract trailing A-E → metadata

TABLE PHASE:
  Stage 14 │ table_converter(table_rows[], section_name) → table_chunks[]
  Stage 15 │ placeholder_injector(text, table_positions) → text with [See Table N] markers

CHUNKING PHASE:
  Stage 16 │ chunker(text, boundary_markers, metadata) → chunks[]
               # respects hard/soft boundaries, 512-token fallback, no mid-sentence splits

POST-CHUNKING PHASE:
  Stage 17 │ safety_flag_scanner(chunks[])             # per-chunk SAFETY_TRIGGERS check
  Stage 18 │ whitespace_normalizer(chunks[])           # final collapse pass

OUTPUT: list of {text: str, metadata: dict}
```
