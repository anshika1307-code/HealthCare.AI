"""
chunker.py
----------
Stages 11–17: Structure detection → chunk boundary resolution → tokenized splitting → safety flagging.

Chunk boundary priority (from plan):
  1. [HARD] Recommendation N (JNC) — one chunk, never split
  2. [HARD] Table — its own chunk (handled by table_converter)
  3. [SOFT] Uppercase section heading (FDA)
  4. [SOFT] Numbered ADA recommendation (6.1, 9.3a…)
  5. [SOFT] Title-Case heading ≤8 words (JNC)
  6. [FALLBACK] 512-token limit with 64-token overlap, never split mid-sentence
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Try to use tiktoken for accurate token counting; fall back to word count.
# ---------------------------------------------------------------------------
try:
    import tiktoken

    _ENC = tiktoken.get_encoding("cl100k_base")

    def _count_tokens(text: str) -> int:
        return len(_ENC.encode(text))

    def _token_split(text: str, max_tokens: int) -> list[str]:
        """Split text into chunks of ≤ max_tokens, aligned to sentence boundaries."""
        tokens = _ENC.encode(text)
        if len(tokens) <= max_tokens:
            return [text]
        # Split at sentence boundaries within the token budget
        sentences = re.split(r"(?<=[.?!])\s+", text)
        chunks: list[str] = []
        current: list[str] = []
        current_tokens = 0
        for sent in sentences:
            sent_tokens = len(_ENC.encode(sent))
            if current_tokens + sent_tokens > max_tokens and current:
                chunks.append(" ".join(current))
                current = [sent]
                current_tokens = sent_tokens
            else:
                current.append(sent)
                current_tokens += sent_tokens
        if current:
            chunks.append(" ".join(current))
        return chunks

except ImportError:
    logger.warning(
        "tiktoken not installed — falling back to whitespace word count for token estimation"
    )

    def _count_tokens(text: str) -> int:  # type: ignore[misc]
        return len(text.split())

    def _token_split(text: str, max_tokens: int) -> list[str]:  # type: ignore[misc]
        sentences = re.split(r"(?<=[.?!])\s+", text)
        chunks: list[str] = []
        current: list[str] = []
        current_tokens = 0
        for sent in sentences:
            sent_tokens = len(sent.split())
            if current_tokens + sent_tokens > max_tokens and current:
                chunks.append(" ".join(current))
                current = [sent]
                current_tokens = sent_tokens
            else:
                current.append(sent)
                current_tokens += sent_tokens
        if current:
            chunks.append(" ".join(current))
        return chunks


# ===========================================================================
# Chunk dataclass
# ===========================================================================


@dataclass
class Chunk:
    text: str
    metadata: dict = field(default_factory=dict)


# ===========================================================================
# Stage 11 — Section Heading Detection
# ===========================================================================

# FDA: ALL-CAPS headings (e.g. DESCRIPTION, INDICATIONS AND USAGE)
_FDA_HEADING = re.compile(r"^([A-Z][A-Z\s\-]{3,})$")

# ADA: Numbered recommendations (e.g. 6.1, 6.5a, 9.3)
_ADA_REC_NUM = re.compile(r"^(\d+\.\d+[a-z]?)\s+(.+)")

# JNC: Title-Case line ≤8 words, no terminal period, not a bullet
_JNC_HEADING = re.compile(r"^([A-Z][a-zA-Z\s\-]{3,60})$")


def _is_jnc_title_case_heading(line: str) -> bool:
    words = line.strip().split()
    if len(words) == 0 or len(words) > 8:
        return False
    if line.strip().endswith("."):
        return False
    if line.strip().startswith(("•", "-", "*", "–")):
        return False
    # At least the first word must be capitalised
    return words[0][0].isupper()


# ===========================================================================
# Stage 12 — JNC Recommendation Detector
# ===========================================================================

_JNC_REC_START = re.compile(r"^Recommendation\s+(\d+)\s*$", re.MULTILINE)
_JNC_GRADE_LINE = re.compile(
    r"(Strong|Moderate|Expert Opinion)\s+Recommendation\s*[–\-]\s*Grade\s+([A-C])",
    re.IGNORECASE,
)


def extract_jnc_recommendation_blocks(text: str) -> list[dict]:
    """
    Find all JNC recommendation blocks and return their spans + metadata.

    Each block runs from "Recommendation N" line to the grade line (inclusive).
    """
    blocks: list[dict] = []
    for m_start in _JNC_REC_START.finditer(text):
        rec_num = int(m_start.group(1))
        start_pos = m_start.start()

        # Look for the grade line within the next 2000 chars
        search_window = text[m_start.end() : m_start.end() + 2000]
        m_grade = _JNC_GRADE_LINE.search(search_window)

        if m_grade:
            end_pos = m_start.end() + m_grade.end()
            block_text = text[start_pos:end_pos].strip()
            # Strip the grade line from block text (it goes to metadata)
            body_text = _JNC_GRADE_LINE.sub("", block_text).strip()
            strength = m_grade.group(1)
            grade = m_grade.group(2)
        else:
            # No grade found — take up to next Recommendation or 1500 chars
            next_m = _JNC_REC_START.search(text, m_start.end())
            end_pos = next_m.start() if next_m else m_start.end() + 1500
            body_text = text[start_pos:end_pos].strip()
            strength = None
            grade = None

        blocks.append(
            {
                "start": start_pos,
                "end": end_pos,
                "rec_number": rec_num,
                "recommendation_strength": strength,
                "evidence_grade": grade,
                "body_text": body_text,
            }
        )

    return blocks


# ===========================================================================
# Stage 13 — ADA Evidence Grade Extractor
# ===========================================================================

# Trailing evidence grade: single A-E letter at end of a recommendation line
_ADA_GRADE_TRAIL = re.compile(r"(?<=\s)([A-E])\s*$", re.MULTILINE)


def extract_ada_evidence_grades(text: str) -> tuple[str, list[dict]]:
    """
    Find and strip trailing evidence grade letters from ADA recommendation lines.

    Returns
    -------
    cleaned_text : str — grade letters removed from text body
    grade_annotations : list[dict] — {position, grade} for each match
    """
    annotations: list[dict] = []
    for m in _ADA_GRADE_TRAIL.finditer(text):
        annotations.append({"position": m.start(), "grade": m.group(1)})

    # Remove the grade letters from text
    cleaned = _ADA_GRADE_TRAIL.sub("", text)
    return cleaned, annotations


# ===========================================================================
# Stage 17 — Safety Flag Scanner
# ===========================================================================

_SAFETY_TRIGGERS = [
    re.compile(r"\bBOXED WARNING\b", re.IGNORECASE),
    re.compile(r"\bWARNINGS?\b"),
    re.compile(r"\bCONTRAINDICATIONS?\b", re.IGNORECASE),
    re.compile(r"\bAvoid\b"),
    re.compile(r"\bdo not\b", re.IGNORECASE),
    re.compile(r"\bshould not\b", re.IGNORECASE),
    re.compile(r"\bnot recommended\b", re.IGNORECASE),
    re.compile(r"\badverse reactions?\b", re.IGNORECASE),
    re.compile(r"\bside effects?\b", re.IGNORECASE),
]


def is_safety_chunk(text: str) -> bool:
    return any(p.search(text) for p in _SAFETY_TRIGGERS)


# ===========================================================================
# Whitespace normaliser (Stage 18)
# ===========================================================================


def normalize_whitespace(text: str) -> str:
    text = re.sub(r" {2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ===========================================================================
# Main Chunker
# ===========================================================================


class Chunker:
    """
    Splits cleaned, normalized text into semantically coherent chunks.

    Parameters
    ----------
    doc_id : str
    doc_type : str        — "fda" | "ada" | "jnc"
    document_name : str
    max_tokens : int      — soft token limit per chunk (default 512)
    overlap_tokens : int  — overlap between adjacent fallback chunks (default 64)
    """

    def __init__(
        self,
        doc_id: str,
        doc_type: str,
        document_name: str,
        max_tokens: int = 512,
        overlap_tokens: int = 64,
    ) -> None:
        self.doc_id = doc_id
        self.doc_type = doc_type
        self.document_name = document_name
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens

    # ------------------------------------------------------------------

    def chunk(self, text: str, page_number: int = 0) -> list[Chunk]:
        """
        Produce chunks from a cleaned, normalized text block.

        For JNC: recommendation blocks are extracted as hard chunks first,
        remaining text is processed with soft boundaries + fallback split.
        For ADA: evidence grades stripped, numbered recs used as soft boundaries.
        For FDA: ALL-CAPS headings used as soft boundaries.
        """
        chunks: list[Chunk] = []
        skipped_content: list[str] = []

        # ---- JNC: extract hard recommendation chunks first ----
        if self.doc_type == "jnc":
            rec_blocks = extract_jnc_recommendation_blocks(text)
            covered_ranges: list[tuple[int, int]] = []

            for block in rec_blocks:
                body = normalize_whitespace(block["body_text"])
                if not body:
                    continue
                meta = self._base_meta(page_number)
                meta.update(
                    {
                        "recommendation_number": block["rec_number"],
                        "recommendation_strength": block["recommendation_strength"],
                        "evidence_grade": block["evidence_grade"],
                        "safety_flag": is_safety_chunk(body),
                        "section_name": f"Recommendation {block['rec_number']}",
                    }
                )
                chunks.append(Chunk(text=body, metadata=meta))
                covered_ranges.append((block["start"], block["end"]))

            # Process remaining text (outside recommendation blocks)
            remaining = self._remove_covered(text, covered_ranges)
            chunks += self._split_generic(remaining, page_number, skipped_content)

        # ---- ADA: strip grades, split on numbered rec boundaries ----
        elif self.doc_type == "ada":
            text, grade_annotations = extract_ada_evidence_grades(text)
            chunks += self._split_ada(text, page_number, grade_annotations)

        # ---- FDA: split on ALL-CAPS section headings ----
        else:
            chunks += self._split_generic(text, page_number, skipped_content)

        # Attach skipped_content log to each chunk (same per page)
        if skipped_content:
            for c in chunks:
                c.metadata.setdefault("skipped_content", []).extend(skipped_content)

        # Assign chunk_index and char_count
        for idx, c in enumerate(chunks):
            c.metadata["chunk_index"] = idx
            c.metadata["char_count"] = len(c.text)

        return chunks

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _base_meta(self, page_number: int) -> dict:
        return {
            "document_id": self.doc_id,
            "document_name": self.document_name,
            "page_number": page_number,
            "section_name": None,
            "section_number": None,
            "subsection_name": None,
            "is_table": False,
            "table_number": None,
            "figure_number": None,
            "evidence_grade": None,
            "recommendation_number": None,
            "recommendation_strength": None,
            "safety_flag": False,
            "skipped_content": [],
            "chunk_index": 0,
            "char_count": 0,
        }

    def _make_chunk(
        self, text: str, page_number: int, section_name: str | None = None, **extra
    ) -> Chunk:
        text = normalize_whitespace(text)
        if not text:
            return None  # type: ignore[return-value]
        meta = self._base_meta(page_number)
        meta["section_name"] = section_name
        meta["safety_flag"] = is_safety_chunk(text)
        meta.update(extra)
        return Chunk(text=text, metadata=meta)

    def _token_budget_split(
        self, text: str, page_number: int, section_name: str | None
    ) -> list[Chunk]:
        """Split a text block into ≤max_tokens chunks at sentence boundaries."""
        sub_texts = _token_split(text, self.max_tokens)
        result: list[Chunk] = []
        for sub in sub_texts:
            c = self._make_chunk(sub, page_number, section_name)
            if c:
                result.append(c)
        return result

    def _split_generic(
        self, text: str, page_number: int, skipped_content: list[str]
    ) -> list[Chunk]:
        """
        Split text using soft heading boundaries (FDA ALL-CAPS / JNC Title-Case),
        with token-budget fallback for long sections.
        """
        chunks: list[Chunk] = []
        lines = text.splitlines()
        current_section: str | None = None
        buffer: list[str] = []

        def flush(section: str | None) -> None:
            block = "\n".join(buffer).strip()
            buffer.clear()
            if not block:
                return
            for c in self._token_budget_split(block, page_number, section):
                chunks.append(c)

        for line in lines:
            stripped = line.strip()

            # Skip near-empty pages logged as flowcharts
            if not stripped and len(buffer) == 0:
                continue

            # Detect soft heading boundaries
            is_heading = False
            if self.doc_type == "fda" and _FDA_HEADING.match(stripped):
                is_heading = True
            elif self.doc_type == "jnc" and _is_jnc_title_case_heading(stripped):
                is_heading = True

            if is_heading and buffer:
                flush(current_section)
                current_section = stripped
                buffer = []
            else:
                buffer.append(line)

        flush(current_section)
        return chunks

    def _split_ada(self, text: str, page_number: int, grade_annotations: list[dict]) -> list[Chunk]:
        """
        Split ADA text using numbered recommendation lines as soft boundaries.
        Propagate the most recent evidence grade found near each boundary.
        """
        chunks: list[Chunk] = []
        lines = text.splitlines()
        current_section: str | None = None
        current_grade: str | None = None
        buffer: list[str] = []

        # Build a position-sorted list of grades for lookup
        sorted_grades = sorted(grade_annotations, key=lambda g: g["position"])

        def flush() -> None:
            block = "\n".join(buffer).strip()
            buffer.clear()
            if not block:
                return
            for c in self._token_budget_split(block, page_number, current_section):
                c.metadata["evidence_grade"] = current_grade
                chunks.append(c)

        char_pos = 0
        for line in lines:
            stripped = line.strip()
            m_rec = _ADA_REC_NUM.match(stripped)

            if m_rec and buffer:
                # Grade = the annotation closest to (just before) this position
                grade_here = None
                for g in reversed(sorted_grades):
                    if g["position"] <= char_pos:
                        grade_here = g["grade"]
                        break
                current_grade = grade_here
                flush()
                current_section = m_rec.group(1)

            buffer.append(line)
            char_pos += len(line) + 1  # +1 for newline

        current_grade = sorted_grades[-1]["grade"] if sorted_grades else None
        flush()
        return chunks

    @staticmethod
    def _remove_covered(text: str, ranges: list[tuple[int, int]]) -> str:
        """Return text with the given character ranges blanked out."""
        if not ranges:
            return text
        chars = list(text)
        for start, end in ranges:
            for i in range(start, min(end, len(chars))):
                chars[i] = ""
        return "".join(chars)
