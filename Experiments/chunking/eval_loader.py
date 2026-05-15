"""
eval_loader.py
--------------
Load eval questions from the markdown tables in data/evaluation/.
Returns a flat list of dicts: {question, expected_answer_contains, source_doc, difficulty}
"""

from __future__ import annotations

import re
from pathlib import Path

# Match a table header line containing the word "question"
_HEADER_LINE = re.compile(r"^\|.*\bquestion\b.*\|", re.IGNORECASE)
# Separator line |---|---|---|
_SEP_LINE = re.compile(r"^\|\s*[-:]+\s*\|")


def _parse_all_tables(md_text: str) -> list[dict]:
    """Extract question rows from ALL markdown pipe tables in the file."""
    rows: list[dict] = []
    lines = md_text.splitlines()
    i = 0
    while i < len(lines):
        # Look for a header line
        if _HEADER_LINE.match(lines[i].strip()):
            header_cells = [c.strip().lower() for c in lines[i].split("|")[1:-1]]
            i += 1
            # Skip separator
            if i < len(lines) and _SEP_LINE.match(lines[i].strip()):
                i += 1
            # Parse data rows
            while i < len(lines) and lines[i].strip().startswith("|"):
                if _SEP_LINE.match(lines[i].strip()):
                    i += 1
                    continue
                cells = [c.strip() for c in lines[i].split("|")[1:-1]]
                if len(cells) >= len(header_cells):
                    row = dict(zip(header_cells, cells))
                    if row.get("question") and not row["question"].startswith("-"):
                        rows.append(row)
                i += 1
        else:
            i += 1
    return rows


def load_eval_questions(eval_dir: str | Path) -> list[dict]:
    """
    Load all eval questions from *.md files in eval_dir.
    Deduplicate by question text.
    """
    eval_dir = Path(eval_dir)
    all_questions: list[dict] = []
    seen: set[str] = set()

    for md_file in sorted(eval_dir.glob("*.md")):
        text = md_file.read_text(encoding="utf-8")
        rows = _parse_all_tables(text)
        for row in rows:
            q = row.get("question", "").strip()
            if not q or q in seen:
                continue
            seen.add(q)
            all_questions.append({
                "question": q,
                "expected_answer_contains": row.get("expected_answer_contains", "").strip(),
                "source_doc": row.get("source_doc", "").strip(),
                "difficulty": row.get("difficulty", "medium").strip(),
                "section": row.get("section", "").strip(),
            })

    return all_questions
