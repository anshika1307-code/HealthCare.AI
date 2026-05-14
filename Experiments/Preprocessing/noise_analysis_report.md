# Noise Analysis & Preprocessing Tool Comparison

> Compares: **Raw PyMuPDF** vs **Custom Cleaner** vs **Unstructured (fast strategy)**

## Summary Table

| PDF | Raw Chars | Noise Hits | After Custom Clean | % Removed | Unstructured Chars | Unstructured Noise | Unstructured Error |
|-----|-----------|------------|--------------------|-----------|--------------------|--------------------|---------|
| ada_standards_care_diabetes_6.pdf | 83,887 | 48 | 83,721 | 0.2% | 83784 | 37 | - |
| ada_standards_care_diabetes_9.pdf | 217,870 | 54 | 211,766 | 2.8% | 221668 | 34 | - |
| jnc8_guidelines_management_hypertension.pdf | 6,505 | 3 | 6,406 | 1.52% | 6406 | 3 | - |
| metformin_fda_label.pdf | 81,211 | 143 | 68,777 | 15.31% | 74030 | 157 | - |
| nutrients-11-00766.pdf | 71,132 | 8 | 71,123 | 0.01% | 74567 | 5 | - |

## Per-Document Noise Breakdown (Raw PyMuPDF)

### ada_standards_care_diabetes_6.pdf

| Noise Type | Occurrences |
|-----------|-------------|
| fda_header_footer | 0 |
| reference_id | 0 |
| standalone_page_num | 40 |
| footnote_superscript | 2 |
| ada_section_header | 0 |
| doi_url | 2 |
| url_generic | 3 |
| copyright_line | 1 |

### ada_standards_care_diabetes_9.pdf

| Noise Type | Occurrences |
|-----------|-------------|
| fda_header_footer | 0 |
| reference_id | 0 |
| standalone_page_num | 0 |
| footnote_superscript | 0 |
| ada_section_header | 0 |
| doi_url | 2 |
| url_generic | 51 |
| copyright_line | 1 |

### jnc8_guidelines_management_hypertension.pdf

| Noise Type | Occurrences |
|-----------|-------------|
| fda_header_footer | 0 |
| reference_id | 0 |
| standalone_page_num | 0 |
| footnote_superscript | 0 |
| ada_section_header | 0 |
| doi_url | 0 |
| url_generic | 3 |
| copyright_line | 0 |

### metformin_fda_label.pdf

| Noise Type | Occurrences |
|-----------|-------------|
| fda_header_footer | 35 |
| reference_id | 35 |
| standalone_page_num | 36 |
| footnote_superscript | 2 |
| ada_section_header | 0 |
| doi_url | 0 |
| url_generic | 35 |
| copyright_line | 0 |

### nutrients-11-00766.pdf

| Noise Type | Occurrences |
|-----------|-------------|
| fda_header_footer | 0 |
| reference_id | 0 |
| standalone_page_num | 4 |
| footnote_superscript | 0 |
| ada_section_header | 1 |
| doi_url | 0 |
| url_generic | 3 |
| copyright_line | 0 |

## Qualitative Notes

- **Custom Cleaner**: Fast, deterministic, zero extra dependencies. Misses noise it wasn't explicitly programmed for.
- **Unstructured (fast)**: Rule-based element classification (Title, NarrativeText, Table, Header, Footer). Automatically strips headers/footers by element type. No ML model required in 'fast' mode.
- **Unstructured (hi_res)**: Uses a layout detection ML model (detectron2). Much slower but better for multi-column PDFs and complex tables. Not tested here (requires GPU or long CPU time).

## Decision Criteria

| Criterion | Custom Cleaner | Unstructured (fast) |
|-----------|---------------|--------------------|
| Speed | ✅ Fastest | ✅ Fast (no ML) |
| Zero extra deps | ✅ Yes | ❌ Extra install |
| Auto header/footer removal | ❌ Must write regex | ✅ Built-in |
| Section/Title detection | ❌ Must write regex | ✅ Element types |
| Table awareness | ❌ No | ⚠️ Basic (pdfplumber still better) |
| Python 3.14 compatible | ✅ Yes | ⚠️ Check |
| Noise hits after processing | Manual | Auto |
