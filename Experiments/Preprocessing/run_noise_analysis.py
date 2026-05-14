# -*- coding: utf-8 -*-
"""run_noise_analysis.py

Part 2 of the extraction experiment.

Goals:
  1. Quantify concrete noise in the raw PyMuPDF output across all 5 PDFs.
  2. Test the `unstructured` library as an alternative preprocessing tool.
  3. Compare raw vs unstructured output on a sample window.
  4. Produce a decision-ready report: `noise_analysis_report.md`.

Run from project root:
    python Experiments/Preprocessing/run_noise_analysis.py
"""

import re
import json
import pathlib
from typing import Dict, List, Any

ROOT = pathlib.Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "DataSource"
OUT_BASE = ROOT / "Experiments" / "Preprocessing" / "outputs"
OUT_BASE.mkdir(parents=True, exist_ok=True)
REPORT_PATH = ROOT / "Experiments" / "Preprocessing" / "noise_analysis_report.md"

# ────────────────────────────────────────────────────────────────
# Known noise patterns (compiled once)
# ────────────────────────────────────────────────────────────────
NOISE_PATTERNS = {
    "fda_header_footer": re.compile(
        r"(This label may not be the latest approved by FDA\..*?drugsatfda)", re.DOTALL
    ),
    "reference_id": re.compile(r"Reference ID:\s*\d+"),
    "standalone_page_num": re.compile(r"^\s*\d{1,3}\s*$", re.MULTILINE),
    "footnote_superscript": re.compile(r"(?m)^[a-e]\s*$"),
    "ada_section_header": re.compile(
        r"(Standards of Medical Care in Diabetes[^\n]*\n)", re.IGNORECASE
    ),
    "doi_url": re.compile(r"https?://doi\.org/\S+"),
    "url_generic": re.compile(r"https?://\S+"),
    "copyright_line": re.compile(
        r"©\s*\d{4}.*?(American Diabetes Association|FDA|All rights reserved)[^\n]*", re.IGNORECASE
    ),
}

def count_noise(text: str) -> Dict[str, int]:
    counts = {}
    for name, pattern in NOISE_PATTERNS.items():
        counts[name] = len(pattern.findall(text))
    return counts


def load_pymupdf_text(pdf_stem: str) -> str:
    p = OUT_BASE / pdf_stem / "pymupdf" / "text.txt"
    return p.read_text(encoding="utf-8") if p.exists() else ""


# ────────────────────────────────────────────────────────────────
# Unstructured extraction
# ────────────────────────────────────────────────────────────────
def extract_with_unstructured(pdf_path: pathlib.Path) -> Dict[str, Any]:
    result: Dict[str, Any] = {"text": "", "elements": 0, "error": None}
    try:
        from unstructured.partition.pdf import partition_pdf

        elements = partition_pdf(
            filename=str(pdf_path),
            strategy="fast",           # no ML model needed; rule-based only
        )
        text_parts = []
        for el in elements:
            text_parts.append(str(el))
        result["text"] = "\n".join(text_parts)
        result["elements"] = len(elements)
    except ImportError:
        result["error"] = "unstructured not installed"
    except Exception as e:
        result["error"] = str(e)
    return result


# ────────────────────────────────────────────────────────────────
# Simple custom cleaner (baseline we'd write ourselves)
# ────────────────────────────────────────────────────────────────
def apply_custom_cleaner(text: str) -> str:
    """Minimal rule-based cleaner applied to raw PyMuPDF text."""
    # 1. Remove FDA header/footer block
    text = NOISE_PATTERNS["fda_header_footer"].sub("", text)
    # 2. Remove Reference IDs
    text = NOISE_PATTERNS["reference_id"].sub("", text)
    # 3. Remove standalone page numbers
    text = NOISE_PATTERNS["standalone_page_num"].sub("", text)
    # 4. Remove lone footnote superscript lines
    text = NOISE_PATTERNS["footnote_superscript"].sub("", text)
    # 5. Remove copyright lines
    text = NOISE_PATTERNS["copyright_line"].sub("", text)
    # 6. Collapse excess blank lines (3+ -> 1)
    text = re.sub(r"\n{3,}", "\n\n", text)
    # 7. Strip trailing spaces per line
    text = "\n".join(line.rstrip() for line in text.splitlines())
    return text.strip()


# ────────────────────────────────────────────────────────────────
# Main
# ────────────────────────────────────────────────────────────────
def main():
    results = []

    for pdf_file in sorted(DATA_DIR.glob("*.pdf")):
        stem = pdf_file.stem
        print(f"\n{'='*60}")
        print(f"  {pdf_file.name}")
        print(f"{'='*60}")

        raw_text = load_pymupdf_text(stem)
        raw_chars = len(raw_text)
        raw_noise = count_noise(raw_text)
        total_noise_hits = sum(raw_noise.values())

        # --- Custom cleaner ---
        cleaned_text = apply_custom_cleaner(raw_text)
        cleaned_chars = len(cleaned_text)
        chars_removed = raw_chars - cleaned_chars
        pct_removed = (chars_removed / raw_chars * 100) if raw_chars else 0

        print(f"  [PyMuPDF raw]     {raw_chars:>8,} chars   noise hits: {total_noise_hits}")
        print(f"  [Custom cleaner]  {cleaned_chars:>8,} chars   removed: {chars_removed:,} ({pct_removed:.1f}%)")

        # Save cleaned text
        cleaned_dir = OUT_BASE / stem / "custom_cleaned"
        cleaned_dir.mkdir(parents=True, exist_ok=True)
        (cleaned_dir / "text.txt").write_text(cleaned_text, encoding="utf-8")

        # --- Unstructured ---
        unst_result = extract_with_unstructured(pdf_file)
        unst_chars = len(unst_result["text"])
        unst_err = unst_result.get("error")
        unst_elements = unst_result.get("elements", 0)

        if unst_err:
            print(f"  [unstructured]    ERROR: {unst_err}")
        else:
            unst_noise = count_noise(unst_result["text"])
            unst_noise_total = sum(unst_noise.values())
            print(f"  [unstructured]    {unst_chars:>8,} chars   elements: {unst_elements}   noise hits: {unst_noise_total}")

            # Save unstructured output
            unst_dir = OUT_BASE / stem / "unstructured"
            unst_dir.mkdir(parents=True, exist_ok=True)
            (unst_dir / "text.txt").write_text(unst_result["text"], encoding="utf-8")

        results.append({
            "pdf": pdf_file.name,
            "raw_chars": raw_chars,
            "raw_noise_hits": total_noise_hits,
            "raw_noise_breakdown": raw_noise,
            "custom_cleaned_chars": cleaned_chars,
            "chars_removed_by_custom": chars_removed,
            "pct_removed_by_custom": round(pct_removed, 2),
            "unstructured_chars": unst_chars if not unst_err else None,
            "unstructured_elements": unst_elements if not unst_err else None,
            "unstructured_noise_hits": sum(count_noise(unst_result["text"]).values()) if not unst_err else None,
            "unstructured_error": unst_err,
        })

    # ── Save JSON ──────────────────────────────────────────────
    json_path = OUT_BASE / "noise_analysis_results.json"
    json_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nJSON saved -> {json_path}")

    # ── Write Markdown Report ──────────────────────────────────
    with REPORT_PATH.open("w", encoding="utf-8") as f:
        f.write("# Noise Analysis & Preprocessing Tool Comparison\n\n")
        f.write("> Compares: **Raw PyMuPDF** vs **Custom Cleaner** vs **Unstructured (fast strategy)**\n\n")

        # Summary table
        f.write("## Summary Table\n\n")
        f.write("| PDF | Raw Chars | Noise Hits | After Custom Clean | % Removed | Unstructured Chars | Unstructured Noise | Unstructured Error |\n")
        f.write("|-----|-----------|------------|--------------------|-----------|--------------------|--------------------|---------|\n")
        for r in results:
            uc = r["unstructured_chars"] if r["unstructured_chars"] is not None else "N/A"
            un = r["unstructured_noise_hits"] if r["unstructured_noise_hits"] is not None else "N/A"
            ue = r["unstructured_error"] or "-"
            f.write(
                f"| {r['pdf']} | {r['raw_chars']:,} | {r['raw_noise_hits']} "
                f"| {r['custom_cleaned_chars']:,} | {r['pct_removed_by_custom']}% "
                f"| {uc} | {un} | {ue} |\n"
            )

        # Per-document noise breakdown
        f.write("\n## Per-Document Noise Breakdown (Raw PyMuPDF)\n\n")
        for r in results:
            f.write(f"### {r['pdf']}\n\n")
            f.write("| Noise Type | Occurrences |\n|-----------|-------------|\n")
            for k, v in r["raw_noise_breakdown"].items():
                f.write(f"| {k} | {v} |\n")
            f.write("\n")

        # Qualitative notes
        f.write("## Qualitative Notes\n\n")
        f.write("- **Custom Cleaner**: Fast, deterministic, zero extra dependencies. Misses noise it wasn't explicitly programmed for.\n")
        f.write("- **Unstructured (fast)**: Rule-based element classification (Title, NarrativeText, Table, Header, Footer). Automatically strips headers/footers by element type. No ML model required in 'fast' mode.\n")
        f.write("- **Unstructured (hi_res)**: Uses a layout detection ML model (detectron2). Much slower but better for multi-column PDFs and complex tables. Not tested here (requires GPU or long CPU time).\n\n")
        f.write("## Decision Criteria\n\n")
        f.write("| Criterion | Custom Cleaner | Unstructured (fast) |\n")
        f.write("|-----------|---------------|--------------------|\n")
        f.write("| Speed | ✅ Fastest | ✅ Fast (no ML) |\n")
        f.write("| Zero extra deps | ✅ Yes | ❌ Extra install |\n")
        f.write("| Auto header/footer removal | ❌ Must write regex | ✅ Built-in |\n")
        f.write("| Section/Title detection | ❌ Must write regex | ✅ Element types |\n")
        f.write("| Table awareness | ❌ No | ⚠️ Basic (pdfplumber still better) |\n")
        f.write("| Python 3.14 compatible | ✅ Yes | ⚠️ Check |\n")
        f.write("| Noise hits after processing | Manual | Auto |\n")

    print(f"Report saved -> {REPORT_PATH}")


if __name__ == "__main__":
    main()
