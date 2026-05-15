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
