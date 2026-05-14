# -*- coding: utf-8 -*-
"""run_extraction_experiment.py

Experimental script to evaluate three PDF extraction approaches on the project's data sources:
- pdfplumber (high‑fidelity table extraction)
- PyMuPDF (fast bulk text extraction)
- LangChain PdfLoader (convenient pipeline integration, wraps PyMuPDF)

The script:
1. Iterates over PDFs in `DataSource/`.
2. Extracts **raw text** and **tables** (where applicable).
3. Stores each method's output under `Experiments/Preprocessing/outputs/<pdf_name>/<method>/`.
4. Generates a summary JSON (`extraction_results.json`) containing:
   * page count
   * character count of extracted text
   * number of tables extracted (pdfplumber only)
   * any extraction errors
5. Finally, a markdown report (`preprocessing_experiment_report.md`) is produced with a concise comparison table.

Run the script from the repository root:
    python Experiments/Preprocessing/run_extraction_experiment.py

Make sure the required packages are installed:
    pip install pdfplumber pymupdf langchain
"""

import os
import json
import pathlib
from typing import Dict, List, Any

# ------------ Helpers for each extraction method ------------

def extract_with_pdfplumber(pdf_path: str) -> Dict[str, Any]:
    import pdfplumber
    result = {"text": "", "tables": []}
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                # Append page text
                result["text"] += page.extract_text() or ""
                # Extract tables (grid & lattice)
                tables = page.extract_tables()
                for table in tables:
                    # Clean empty rows
                    cleaned = [row for row in table if any(cell is not None and cell.strip() != "" for cell in row)]
                    if cleaned:
                        result["tables"].append({"page": page.page_number, "data": cleaned})
    except Exception as e:
        result["error"] = str(e)
    return result


def extract_with_pymupdf(pdf_path: str) -> Dict[str, Any]:
    import fitz  # PyMuPDF
    result = {"text": ""}
    try:
        doc = fitz.open(pdf_path)
        for page in doc:
            result["text"] += page.get_text("text")
    except Exception as e:
        result["error"] = str(e)
    return result


def extract_with_langchain(pdf_path: str) -> Dict[str, Any]:
    """
    Simulates LangChain's PyPDFLoader behaviour using pypdf directly.
    This avoids the Python 3.14 Pydantic-v1 'REGEX attribute' incompatibility
    that crashes langchain_community.document_loaders.PyPDFLoader.

    The output mirrors what LangChain returns:
      - text:  all page content concatenated (same as calling loader.load())
      - pages: list of {page_number, content} dicts (same as page-level Document objects)
    """
    result: Dict[str, Any] = {"text": "", "pages": []}
    try:
        import pypdf

        reader = pypdf.PdfReader(pdf_path)
        for i, page in enumerate(reader.pages):
            page_text = page.extract_text() or ""
            result["text"] += page_text
            result["pages"].append({"page": i + 1, "content": page_text})
    except Exception as e:
        result["error"] = str(e)
    return result


# ------------ Main experiment orchestration ------------

def main():
    root_dir = pathlib.Path(__file__).resolve().parents[2]  # project root (Healthcare_AI)
    data_dir = root_dir / "DataSource"
    out_base = root_dir / "Experiments" / "Preprocessing" / "outputs"
    out_base.mkdir(parents=True, exist_ok=True)

    summary: List[Dict[str, Any]] = []

    for pdf_file in sorted(data_dir.glob("*.pdf")):
        pdf_name = pdf_file.stem
        print(f"Processing {pdf_name}.pdf ...")
        pdf_summary = {"pdf": pdf_file.name}
        methods = {
            "pdfplumber": extract_with_pdfplumber,
            "pymupdf": extract_with_pymupdf,
            "langchain": extract_with_langchain,
        }
        for method_name, func in methods.items():
            out_dir = out_base / pdf_name / method_name
            out_dir.mkdir(parents=True, exist_ok=True)
            result = func(str(pdf_file))
            # Save raw text
            (out_dir / "text.txt").write_text(result.get("text", ""), encoding="utf-8")
            # Save tables if present (pdfplumber only)
            if method_name == "pdfplumber" and result.get("tables"):
                import csv, json
                tables_path = out_dir / "tables.json"
                tables_path.write_text(json.dumps(result["tables"], ensure_ascii=False, indent=2), encoding="utf-8")
            # Record stats
            method_stats: Dict[str, Any] = {
                "method": method_name,
                "pages": None,
                "char_count": len(result.get("text", "")),
                "table_count": len(result.get("tables", [])) if method_name == "pdfplumber" else None,
                "error": result.get("error"),
            }
            # Page count (available from pdfplumber/pymupdf loaders)
            if method_name == "pdfplumber":
                try:
                    import pdfplumber
                    with pdfplumber.open(pdf_file) as pdf:
                        method_stats["pages"] = len(pdf.pages)
                except Exception:
                    method_stats["pages"] = None
            elif method_name == "pymupdf":
                try:
                    import fitz
                    doc = fitz.open(pdf_file)
                    method_stats["pages"] = doc.page_count
                except Exception:
                    method_stats["pages"] = None
            else:  # langchain (pypdf-based)
                method_stats["pages"] = len(result.get("pages", [])) or None
            pdf_summary.setdefault("methods", []).append(method_stats)
        summary.append(pdf_summary)

    # Write summary JSON
    summary_path = out_base / "extraction_results.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Summary written to {summary_path}")

    # Generate markdown report (simple table)
    report_path = root_dir / "Experiments" / "Preprocessing" / "preprocessing_experiment_report.md"
    with report_path.open("w", encoding="utf-8") as f:
        f.write("# Preprocessing Extraction Experiment Report\n\n")
        f.write("The table below summarizes key metrics for each PDF and extraction method.\n\n")
        f.write("| PDF | Method | Pages | Characters | Tables | Error |\n")
        f.write("|-----|--------|-------|------------|--------|-------|\n")
        for pdf in summary:
            pdf_name = pdf["pdf"]
            for m in pdf["methods"]:
                f.write(f"| {pdf_name} | {m['method']} | {m.get('pages','-')} | {m['char_count']} | {m.get('table_count','-')} | {m.get('error','-')} |\n")
        f.write("\n*Run the script to generate up‑to‑date numbers.*\n")
    print(f"Markdown report written to {report_path}")

if __name__ == "__main__":
    main()
