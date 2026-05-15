# Preprocessing Specification (AI-driven)

Based on the initial extraction experiment using `pdfplumber` and `PyMuPDF`, we have identified several noise patterns and structural elements that require custom preprocessing to ensure high-quality RAG performance.

## 1. Noise Identification

### 1.1. Repetitive Headers and Footers
Across multiple documents, particularly the FDA labels and clinical guidelines, repetitive text blocks appear on almost every page.
*   **Pattern 1 (FDA Labels):** `This label may not be the latest approved by FDA. For current labeling information, please visit https://www.fda.gov/drugsatfda`
*   **Pattern 2 (ADA Standards):** `Section \d+—[A-Z\s]+` (e.g., `Section 9—Pharmacologic Approaches to Glycemic Treatment`)
*   **Pattern 3 (Reference IDs):** `Reference ID: \d+` (e.g., `Reference ID: 4079189`)

### 1.2. Page Numbers
*   **Pattern:** Standalone integers at the bottom or top of the page, sometimes followed by the header text.

### 1.3. Footnote References
*   **Pattern:** Lowercase letters (`a`, `b`, `c`, `d`, etc.) appearing at the start of lines or inside table cells, often followed by a newline or space. These refer to footnotes located at the end of sections or pages.

### 1.4. In-text Citations
*   **Pattern:** Numbers in parentheses or brackets (e.g., `(1)`, `[12]`) referencing the bibliography. These can clutter semantic search if not handled.

## 2. Structural Elements

### 2.1. Section Headings
*   **Format:** Uppercase headings (e.g., `DESCRIPTION`, `CLINICAL PHARMACOLOGY`, `INDICATIONS AND USAGE`).
*   **Action:** These should be used as chunk boundaries to maintain semantic continuity.

### 2.2. Tables
*   `pdfplumber` successfully extracts tables as structured lists.
*   **Action:** Tables should be converted to Markdown or a simplified CSV string representation before being embedded, to preserve column-row relationships.

## 3. Cleaning and Normalization Rules

### 3.1. Line-level Cleaning
1.  **Remove Headers/Footers:** Use fuzzy matching or exact regex to strip identified repetitive blocks.
2.  **Remove Page Numbers:** Regex: `^\d+$` on a single line.
3.  **Remove Reference IDs:** Regex: `Reference ID: \d+`.
4.  **Fix Joined Lines:** Detect cases where headers are joined with the first line of content (e.g., `Reference ID: 4079189This label...`).

### 3.2. Text Normalization
1.  **Whitespace:** Collapse multiple spaces and trim lines.
2.  **Newlines:** Normalize paragraph breaks. PDF extraction often adds hard breaks inside sentences. Use a heuristic (e.g., if a line doesn't end with a sentence-ending punctuation, join it with the next line).

### 3.3. Footnote Handling
1.  **Option A (Strip):** Remove the superscript-like letters if they add noise.
2.  **Option B (Contextualize):** If the footnote content is captured, append it to the relevant paragraph (complex).
*   **Recommendation:** For the initial prototype, strip them to avoid semantic confusion.

## 4. Proposed Pipeline Architecture

```python
def preprocess_document(raw_text, tables):
    # 1. Strip known repetitive noise (Regex)
    # 2. Join broken sentences (Heuristic)
    # 3. Identify Section boundaries
    # 4. Format Tables as Markdown strings
    # 5. Segment into Section-aware chunks
    return cleaned_chunks
```

## 5. Decision on Tools
*   **Text Extraction:** Use `PyMuPDF` for its speed and generally cleaner text flow for paragraphs.
*   **Table Extraction:** Use `pdfplumber` specifically for tables and merge them back into the `PyMuPDF` text flow at the correct locations (or keep them as separate metadata-linked documents).
*   **Custom Preprocessing:** Required to implement the rules above.

---

## 6. Document-Specific Spec: `jnc8_guidelines_manage_hypertension_original.pdf`

> **Data source note:** The extraction experiment outputs in `experiments/preprocessing/outputs/jnc8_guidelines_management_hypertension/` correspond to the **wrong document** — a 2-page AFP summary (~6.5K chars), not the full original JAMA paper. The extractor comparison below uses those outputs only to understand tool behavior patterns (column interleaving, line joining, footer bleed-through). The noise patterns and structural rules in this section are derived from the **dev's manual reading** of the actual original PDF (`preprocessing_specs_dev.md`).

### 6.1. Layout: 2-Column Format

The original JAMA paper is formatted in **two equal-width columns per page**. This is the most critical structural challenge for this document.

*   **What PyMuPDF does (observed from wrong-doc experiment):** Extracts text in reading order by y-coordinate across both columns simultaneously. This causes left-column and right-column sentences to **interleave** mid-paragraph, producing semantically broken output (e.g., line 64–67 in `pymupdf/text.txt` where `angiotensin-converting`, `enzyme`, `(ACE)` appear on three separate lines because they fell across a column gap).
*   **What pdfplumber does (observed):** Produces the same interleaving problem — see `pdfplumber/text.txt` lines 10–22 where "Key Points for Practice" bullet text is alternating mid-sentence with the main body text. **pdfplumber is worse** for this document — it merges both columns in a single line in some cases (line 20: two different sentences joined).
*   **What Unstructured does (observed):** Handles it better — longer coherent paragraphs visible in `unstructured/text.txt` lines 12–15, though it still fails on the page-break mid-sentence case (line 15 ends mid-sentence, continued in line 17 with content from the wrong column).
*   **Recommended fix:** Use PyMuPDF's `page.get_text("dict")` to extract text blocks with bounding box coordinates. Split blocks into **left column** (`x0 < page_width / 2`) and **right column** (`x0 >= page_width / 2`). Concatenate left column blocks top-to-bottom, then right column blocks top-to-bottom, per page. This restores reading order.

### 6.2. Noise Patterns

#### 6.2.1. Page Header
*   **Pattern (observed in PyMuPDF lines 1–3 and 96–98):** Each page starts with a journal citation line and page number, e.g.:
    ```
    October 1, 2014 ◆ Volume 90, Number 7
    www.aafp.org/afp
    American Family Physician  503
    ```
    And on even pages:
    ```
    504  American Family Physician
    www.aafp.org/afp
    Volume 90, Number 7 ◆ October 1, 2014
    ```
*   **Regex patterns:**
    ```
    r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}\s+[◆♦]\s+Volume\s+\d+"
    r"www\.aafp\.org/afp"
    r"\d{3}\s+American Family Physician"
    r"American Family Physician\s+\d{3}"
    ```
*   **Note:** For the original JAMA paper, the header pattern will differ — it will be JAMA-branded (e.g., `508 JAMA February 5, 2014 Volume 311, Number 5 jama.com`). Dev confirmed exact format in `preprocessing_specs_dev.md` line 94.
    ```
    r"\d{3}\s+JAMA\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}\s+Volume\s+\d+"
    r"jama\.com\s*$"
    ```

#### 6.2.2. Page Footer (3-line block — Original JAMA doc)
*   **Pattern (from dev manual observation, `preprocessing_specs_dev.md` line 94):** Three lines at the bottom of each page in the original:
    1. `508 JAMA February 5, 2014 Volume 311, Number 5 jama.com`
    2. `Copyright © 2014 American Medical Association.`
    3. `Downloaded from jamanetwork.com by Anshika Goel on 05/14/2026`
*   **Regex patterns:**
    ```
    r"Copyright\s+©\s+2014\s+American Medical Association\.?"
    r"Downloaded from jamanetwork\.com by .+ on \d{2}/\d{2}/\d{4}"
    ```
*   **Detection strategy:** Since these are in the bottom region of each page, use bounding-box filtering: discard any text block where `y0 > page_height * 0.92` before column stitching. As a fallback, apply the regex patterns above on the full extracted text.
*   **Observed in wrong-doc experiment:** The AFP-version footer (`Downloaded from the American Family Physician website...`) appears in PyMuPDF at lines 93–94 and in pdfplumber at line 62. The **custom cleaner missed it entirely** (still present in `custom_cleaned/text.txt` lines 93–94), and Unstructured absorbed it into a paragraph (line 16). This confirms: **existing custom cleaner regex does not cover this document's footer — new patterns required.**

#### 6.2.3. Non-Clinical Trailing Content
*   **Observed (all extractors, lines 133–145 in PyMuPDF output):** After the clinical content ends, there is a full advertisement block ("AAFP's Five Key Metrics for Financial Success", "Master your business", tutorial URLs). This is entirely non-clinical noise.
*   **Pattern:** Detect the sentinel line `CARRIE ARMSTRONG, AFP Senior Associate Editor` (or equivalent author credit line in JAMA version) → discard everything after it.
*   **For JAMA original:** Sentinel lines will be `ARTICLE INFORMATION` and `REFERENCES`. Regex: `r"^ARTICLE INFORMATION\s*$"` and `r"^REFERENCES\s*$"` — discard everything after the first match.

#### 6.2.4. "Key Points for Practice" / Summary Block (Page 1)
*   **Observed (PyMuPDF lines 78–92, pdfplumber lines 11–31):** Page 1 contains a "Key Points for Practice" bullet list that summarizes the guidelines. This content is a **duplicate** of the main body text and interleaves badly with the 2-column layout during extraction.
*   **Dev observation:** "page 1 has summary or key points kind of thing — these are not part of guidelines, can remove them."
*   **Pattern:** Detect `r"^Key Points for Practice\s*$"` as sentinel → strip this entire block (from sentinel until the next non-bullet line that starts a proper paragraph).
*   **Note:** In the original JAMA paper this may be a "Summary" or "Abstract" block. Apply the same sentinel-detection approach.

#### 6.2.5. Inline Cross-References
*   **Pattern (observed in content and confirmed by dev):** `(in Table 1)`, `(70)`, `(see Figure 1)` — same pattern as ADA documents.
*   **Regex:**
    ```
    r"\(in\s+(Table|Figure)\s+\d+\)"
    r"\(\d{1,3}\)"
    ```

#### 6.2.6. Hyphenated Line-Break Artifacts
*   **Observed across all extractors** (e.g., PyMuPDF line 14: `appropri­`, line 61: `anti­`, line 117: `moder­`): Soft hyphens (`\u00ad`) and regular hyphens at line ends cause words to be split across lines.
*   **Patterns:**
    ```
    r"(\w+)\u00ad\n(\w+)"   # soft hyphen join
    r"(\w+)-\n(\w+)"         # hard hyphen join
    ```
*   **Action:** Join both forms — remove the hyphen and newline, concatenate the word parts.

#### 6.2.7. Guideline Metadata Block (End of Document)
*   **Observed (PyMuPDF lines 120–131):** A structured metadata block appears at the end:
    ```
    Guideline source: Eighth Joint National Committee
    Evidence rating system used? Yes
    Literature search described? Yes
    Guideline developed by participants without relevant financial ties to industry? No
    Published source: Journal of the American Medical Association, December 18, 2013
    Available at: http://...
    ```
*   **Action:** This is non-clinical metadata. Strip it entirely. Regex: `r"^Guideline source:"` as sentinel → discard block until next section or EOF.

### 6.3. Structural Elements Specific to This Document

#### 6.3.1. Recommendation Blocks (Original JAMA Document)
*   **Pattern (from dev observation, `preprocessing_specs_dev.md` lines 100–107):**
    ```
    Recommendation 1
    In the general population aged 60 years or older...
    Strong Recommendation – Grade A
    ```
*   **Detection regex:**
    ```
    r"^Recommendation\s+(\d+)\s*$"                                           # block start
    r"(Strong|Moderate|Expert Opinion)\s+Recommendation\s*[–\-]\s*Grade\s+([A-E])"  # grade line
    ```
*   **Action:** Each `Recommendation N` block is a **hard chunk boundary**. Extract `recommendation_number`, `recommendation_strength`, and `grade` into chunk metadata. Strip the grade line from the chunk text body (it moves to metadata only).

#### 6.3.2. Section Headings
*   **Observed (PyMuPDF lines 40–41, 59, 75–77):** Title-case short headings that start new content sections:
    ```
    Hypertension in Patients with CKD or Diabetes
    Pharmacologic Treatment
    Practice Guidelines
    ```
*   **Detection heuristic:** A line is a section heading if: (a) it is ≤ 8 words, (b) it is Title-Cased or ALL-CAPS, (c) it is not followed by a period, and (d) it is not a bullet point. Use as soft chunk boundary.

#### 6.3.3. Abbreviation List (Start of Original JAMA Document)
*   **Pattern (from dev, `preprocessing_specs_dev.md` lines 81–91):** The original JAMA paper contains an explicit abbreviation table at the start:
    ```
    ACEI  angiotensin-converting enzyme inhibitor
    ARB   angiotensin receptor blocker
    BP    blood pressure
    CCB   calcium channel blocker
    CKD   chronic kidney disease
    CVD   cardiovascular disease
    ESRD  end-stage renal disease
    GFR   glomerular filtration rate
    HF    heart failure
    ```
*   **Action:** Parse this table as a first pass before any other cleaning. Build a per-document `abbreviation_map` dict: `{"ACEI": "angiotensin-converting enzyme inhibitor", "ARB": "angiotensin receptor blocker", ...}`. Use this map in the abbreviation expansion stage. After parsing, **remove** the abbreviation list block from the main text body (it is a lookup artifact, not clinical content).

#### 6.3.4. Negative / Safety Instructions
*   **Observed in extracted text (PyMuPDF line 101–102):** `"do not combine an ACE inhibitor with an ARB"` — a contraindication buried inside a paragraph.
*   **Dev note:** "there are some negative instructions too — very important to keep them... flag them too (safety concerns)."
*   **Action:** After chunking, scan each chunk for safety trigger phrases:
    ```python
    SAFETY_TRIGGERS = [
        r"\bdo not\b", r"\bAvoid\b", r"\bnot recommended\b",
        r"\bcontraindicated\b", r"\bshould not\b"
    ]
    ```
    Set `metadata["safety_flag"] = True` for any matching chunk.

### 6.4. Extractor Comparison Summary for This Document

| Criterion | PyMuPDF | pdfplumber | Unstructured (fast) | Custom Cleaner |
|-----------|---------|-----------|---------------------|----------------|
| Column order correct | ❌ Interleaves cols | ❌ Worse — merges cross-col lines | ⚠️ Better but not perfect | ❌ No fix (inherits PyMuPDF) |
| Header/footer stripped | ❌ All present | ❌ All present | ⚠️ Partial | ❌ Missed entirely |
| Hyphen join | ❌ Split across lines | ⚠️ Some joined | ✅ Joined | ❌ Not fixed |
| Trailing ad block stripped | ❌ Present | ❌ Present | ❌ Present | ❌ Present |
| Tables detected | None found | 0 tables (correct — this doc has no structured tables) | N/A | N/A |

*   **Conclusion:** For this document, **PyMuPDF with bounding-box column sorting** is the correct extractor. None of the existing pipeline handles the 2-column layout — this requires a custom column-stitching step before any other cleaning. Unstructured (fast) partially handles it but introduces its own ordering issues and adds an extra dependency.

### 6.5. Cleaning Rules Summary (Ordered Pipeline)

```
[Step 1]  Column stitching       — sort PyMuPDF blocks by (column, y0) per page
[Step 2]  Page 1 skip            — discard "Key Points for Practice" block
[Step 3]  Abbreviation map parse — extract ACEI/ARB/BP/... table → abbreviation_map dict
[Step 4]  Header strip           — JAMA journal line + page number per page
[Step 5]  Footer strip           — 3-line block (JAMA copyright + download line) per page
[Step 6]  Trailing content strip — sentinel: "ARTICLE INFORMATION" or "REFERENCES"
[Step 7]  Guideline metadata strip — sentinel: "Guideline source:"
[Step 8]  Soft hyphen join       — \u00ad\n and -\n → joined word
[Step 9]  Inline ref strip       — (70), (in Table 1) patterns
[Step 10] Section heading detect — Title-Case ≤8 words → chunk boundary marker
[Step 11] Recommendation detect  — "Recommendation N" → hard chunk boundary + metadata extract
[Step 12] Safety flag scan       — "do not", "Avoid", "contraindicated" → metadata flag
[Step 13] Abbreviation expand    — first occurrence of each abbreviation → expand inline
[Step 14] Line rejoin            — non-terminal lines → join with next line
[Step 15] Whitespace normalize   — collapse spaces and excess newlines
```
