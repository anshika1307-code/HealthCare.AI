"""
cleaner.py
----------
Document-specific and cross-document noise removal.

Stages (matching the plan):
  Stage 1  abbreviation_list_parser   — JNC only: parse ABBR table → map, strip block
  Stage 2  header_footer_remover      — per doc_type regex patterns
  Stage 3  (page 1 skip handled in extractor)
  Stage 4  reference_section_remover  — sentinel-based tail truncation
  Stage 5  guideline_metadata_remover — JNC "Guideline source:" block
  Stage 6  inline_noise_remover       — URLs, citations, figure refs, page numbers
  Stage 7  hyphen_line_joiner         — soft (\u00ad) and hard (-) hyphen word join
  Stage 8  line_rejoiner              — broken PDF line wraps
"""

from __future__ import annotations

import re
import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Type alias
# ---------------------------------------------------------------------------
AbbrevMap = dict[str, str]   # {"CGM": "continuous glucose monitoring", ...}


# ===========================================================================
# Stage 1 — JNC Abbreviation List Parser
# ===========================================================================

# The JNC original opens with a table like:
#   ACEI  angiotensin-converting enzyme inhibitor
#   ARB   angiotensin receptor blocker
# Two or more spaces separate abbreviation from expansion.
_JNC_ABBREV_LINE = re.compile(r"^([A-Z]{2,6})\s{2,}(.+)$", re.MULTILINE)

# Sentinel: the abbreviation block ends when a non-all-caps line appears
# that cannot match the pattern above (i.e., normal prose begins).


def parse_jnc_abbreviation_list(text: str) -> tuple[str, AbbrevMap]:
    """
    Extract the JNC abbreviation table from the start of the document text.

    Returns
    -------
    cleaned_text : str
        Text with the abbreviation block removed.
    abbrev_map : dict
        {ABBREVIATION: full_form} extracted from the block.
    """
    abbrev_map: AbbrevMap = {}
    lines = text.splitlines()

    block_end_idx = 0
    in_block = False

    for i, line in enumerate(lines):
        m = _JNC_ABBREV_LINE.match(line.strip())
        if m:
            abbrev_map[m.group(1)] = m.group(2).strip()
            in_block = True
            block_end_idx = i
        elif in_block:
            # First non-matching line after block started = block is over
            break

    if abbrev_map:
        logger.info("JNC abbreviation map built: %d entries", len(abbrev_map))
        cleaned = "\n".join(lines[block_end_idx + 1 :])
        return cleaned, abbrev_map

    return text, {}


# ===========================================================================
# Stage 2 — Header / Footer Remover
# ===========================================================================

# --- FDA ---
_FDA_HEADER = re.compile(
    r"This label may not be the latest approved by FDA\..*?https://www\.fda\.gov/drugsatfda",
    re.DOTALL | re.IGNORECASE,
)
_FDA_REF_ID = re.compile(r"Reference ID:\s*\d+")
# Page number: standalone integer on its own line
_STANDALONE_PAGE_NUM = re.compile(r"^\s*\d{1,3}\s*$", re.MULTILINE)
# Duplicate heading on FDA page 1 (handled after text join, safe to apply globally)
_FDA_DUPE_HEADING = re.compile(
    r"GLUCOPHAGE®?\s*\(metformin hydrochloride\)\s*Tablets\s*and\s*"
    r"GLUCOPHAGE®?\s*XR\s*\(metformin hydrochloride\)\s*Extended-Release Tablets",
    re.IGNORECASE,
)

# --- ADA ---
_ADA_HEADER_1 = re.compile(r"diabetesjournals\.org/care\s+.*?S\d+", re.DOTALL)
_ADA_HEADER_2 = re.compile(r"S\d+\s+[\w][\w\s]+Diabetes Care Volume.*", re.IGNORECASE)
_ADA_HEADER_3 = re.compile(r"Diabetes Care Volume \d+.*?S\d+\s*$", re.MULTILINE | re.IGNORECASE)
_ADA_DOWNLOAD = re.compile(
    r"Downloaded from http://diabetesjournals\.org/\S+\s*by guest on \d{2} \w+ \d{4}",
    re.IGNORECASE,
)
_ADA_COPYRIGHT = re.compile(r"©\s*20\d{2}\s+by the American Diabetes Association[^\n]*", re.IGNORECASE)

# --- JNC ---
_JNC_HEADER = re.compile(
    r"\d{3}\s+JAMA\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{1,2},\s+\d{4}\s+Volume\s+\d+[^\n]*",
    re.IGNORECASE,
)
_JNC_FOOTER_JAMA = re.compile(r"jama\.com\s*$", re.MULTILINE | re.IGNORECASE)
_JNC_FOOTER_COPYRIGHT = re.compile(
    r"Copyright\s+©\s+2014\s+American Medical Association\.?", re.IGNORECASE
)
_JNC_FOOTER_DOWNLOAD = re.compile(
    r"Downloaded from jamanetwork\.com by .+ on \d{2}/\d{2}/\d{4}", re.IGNORECASE
)
# AFP summary version footer (wrong doc — kept for safety)
_AFP_FOOTER = re.compile(
    r"Downloaded from the American Family Physician website.*?permission requests\.",
    re.DOTALL | re.IGNORECASE,
)


def remove_headers_footers(text: str, doc_type: str) -> str:
    """Apply doc-type-specific header/footer regex patterns."""
    if doc_type == "fda":
        text = _FDA_HEADER.sub("", text)
        # Split on Reference ID first to avoid footer gluing to content
        text = _FDA_REF_ID.sub("", text)
        text = _STANDALONE_PAGE_NUM.sub("", text)
        text = _FDA_DUPE_HEADING.sub("", text)

    elif doc_type == "ada":
        text = _ADA_HEADER_1.sub("", text)
        text = _ADA_HEADER_2.sub("", text)
        text = _ADA_HEADER_3.sub("", text)
        text = _ADA_DOWNLOAD.sub("", text)
        text = _ADA_COPYRIGHT.sub("", text)
        text = _STANDALONE_PAGE_NUM.sub("", text)

    elif doc_type == "jnc":
        text = _JNC_HEADER.sub("", text)
        text = _JNC_FOOTER_JAMA.sub("", text)
        text = _JNC_FOOTER_COPYRIGHT.sub("", text)
        text = _JNC_FOOTER_DOWNLOAD.sub("", text)
        text = _AFP_FOOTER.sub("", text)
        text = _STANDALONE_PAGE_NUM.sub("", text)

    return text


# ===========================================================================
# Stage 4 — Reference Section Remover
# ===========================================================================

_SENTINEL_PATTERNS: dict[str, list[re.Pattern]] = {
    "ada": [re.compile(r"^References\s*$", re.MULTILINE)],
    "jnc": [
        re.compile(r"^ARTICLE INFORMATION\s*$", re.MULTILINE),
        re.compile(r"^REFERENCES\s*$", re.MULTILINE),
        # Trailing CARRIE ARMSTRONG author credit (AFP version)
        re.compile(r"CARRIE ARMSTRONG,\s*AFP Senior Associate Editor", re.IGNORECASE),
        # AAFP advertisement block
        re.compile(r"AAFP'?s?\s+.Five Key Metrics", re.IGNORECASE),
    ],
    "fda": [],  # FDA has inline citations — handled in inline_noise_remover
}


def remove_reference_section(text: str, doc_type: str) -> str:
    """Truncate text at the first sentinel line marking a reference/metadata block."""
    for pattern in _SENTINEL_PATTERNS.get(doc_type, []):
        m = pattern.search(text)
        if m:
            logger.debug("Reference sentinel '%s' found at char %d", pattern.pattern[:40], m.start())
            text = text[: m.start()].rstrip()
            break  # first sentinel wins
    return text


# ===========================================================================
# Stage 5 — JNC Guideline Metadata Block Remover
# ===========================================================================

_GUIDELINE_META_SENTINEL = re.compile(r"^Guideline source:", re.MULTILINE)


def remove_guideline_metadata(text: str, doc_type: str) -> str:
    """JNC-only: strip 'Guideline source: ...' block at end of document."""
    if doc_type != "jnc":
        return text
    m = _GUIDELINE_META_SENTINEL.search(text)
    if m:
        text = text[: m.start()].rstrip()
    return text


# ===========================================================================
# Stage 6 — Inline Noise Remover
# ===========================================================================

# URLs (generic + DOI)
_URL = re.compile(r"https?://\S+", re.IGNORECASE)
_DOI = re.compile(r"\bdoi:\s*\S+", re.IGNORECASE)

# Inline citations
_CITATION_PARENS = re.compile(r"\(\d{1,3}\)")           # (70)
_CITATION_RANGE = re.compile(r"\(\d+[–\-]\d+\)")        # (2–4), (24–29)
_CITATION_BRACKETS = re.compile(r"\[\d{1,3}\]")         # [12]
_SEE_CROSS_REF = re.compile(r"\(see\s+[^)]+\)", re.IGNORECASE)  # (see Precautions)
_IN_TABLE_REF = re.compile(r"\(in\s+(?:Table|Figure)\s+[\d\.]+\)", re.IGNORECASE)

# Figure references in text
_FIG_REF_PARENS = re.compile(r"\(in Fig\.?\s*[\d\.]+\)", re.IGNORECASE)
_FIG_REF_INLINE = re.compile(r"\bFig\.\s*[\d\.]+", re.IGNORECASE)

# Superscript/subscript footnote letter artifacts: e.g. "AUCa" where 'a' is superscript
# FIX (2026-05-16): original lookbehind [a-zA-Z0-9] matched the last letter of EVERY
# English word ("reduces"→"reduce", "Metformin"→"Metformi"). Corrected to [A-Z0-9] so
# only a lowercase letter appended to an UPPERCASE letter or digit is stripped.
# This catches "AUCa", "Cmaxb", "T½a" while preserving regular word endings.
_FOOTNOTE_SUPERSCRIPT = re.compile(r"(?<=[A-Z0-9])([a-z])\b(?=[\s,\.\;\:\)])")  # Bug fix

# Protected medical tokens — must survive the superscript remover intact.
# These end in a lowercase letter after a digit ("HbA1c") or UPPERCASE ("T2DMa")
# and would otherwise be mangled by the corrected regex.
_PROTECTED_MEDICAL = re.compile(
    r"\b(HbA1c|HbA1C|T1DM|T2DM|T1D|T2D|CKD3a|CKD3b|GLP1|GLP\-1)\b",
    re.IGNORECASE,
)

# ADA "See related editorial on page N" cross-reference
_EDITORIAL_REF = re.compile(r"▲?\s*See related editorial on page \d+\.", re.IGNORECASE)

# JNC "Key Points for Practice" summary block (AFP version sentinel)
_KEY_POINTS_BLOCK = re.compile(
    r"Key Points for Practice\s*\n(?:•[^\n]*\n?)+",
    re.MULTILINE,
)
# "From the AFP Editors" byline
_AFP_BYLINE = re.compile(r"From the AFP Editors\s*", re.IGNORECASE)

# Generic "Practice Guidelines" section header noise
_PRACTICE_GUIDELINES = re.compile(r"^Practice Guidelines\s*$", re.MULTILINE)


def remove_inline_noise(text: str, doc_type: str) -> str:
    """Strip inline noise: URLs, citations, figure refs, superscripts, etc."""
    text = _URL.sub("", text)
    text = _DOI.sub("", text)
    text = _CITATION_RANGE.sub("", text)
    text = _CITATION_PARENS.sub("", text)
    text = _CITATION_BRACKETS.sub("", text)
    text = _SEE_CROSS_REF.sub("", text)
    text = _IN_TABLE_REF.sub("", text)
    text = _FIG_REF_PARENS.sub("", text)
    text = _FIG_REF_INLINE.sub("", text)
    text = _EDITORIAL_REF.sub("", text)

    if doc_type == "jnc":
        text = _KEY_POINTS_BLOCK.sub("", text)
        text = _AFP_BYLINE.sub("", text)
        text = _PRACTICE_GUIDELINES.sub("", text)

    # Superscript footnote artifacts — apply cautiously
    # Skip for JNC to avoid mangling abbreviations.
    # For FDA/ADA: protect known medical tokens before applying, then restore.
    if doc_type in ("fda", "ada"):
        # Step 1: stash protected tokens so superscript remover can't touch them
        _protected: dict[str, str] = {}

        def _protect(m: re.Match) -> str:
            key = f"__PROT{len(_protected)}__"
            _protected[key] = m.group(0)
            return key

        text = _PROTECTED_MEDICAL.sub(_protect, text)
        # Step 2: strip superscript artefacts
        text = _FOOTNOTE_SUPERSCRIPT.sub("", text)
        # Step 3: restore protected tokens
        for key, val in _protected.items():
            text = text.replace(key, val)

    return text


# ===========================================================================
# Stage 7 — Hyphen Line Joiner
# ===========================================================================

_SOFT_HYPHEN_BREAK = re.compile(r"(\w+)\u00ad\n(\w+)")  # soft hyphen
_HARD_HYPHEN_BREAK = re.compile(r"(\b[a-z]+)-\n([a-z]+\b)")  # hard hyphen, both lowercase


def join_hyphenated_lines(text: str) -> str:
    """
    Rejoin words broken by hyphen + newline (PDF line-wrap artifact).

    Soft hyphens (\u00ad) are always joined.
    Hard hyphens are only joined when both parts are lowercase
    — this preserves intentional hyphenated terms like 'anti-hypertensive'.
    """
    text = _SOFT_HYPHEN_BREAK.sub(r"\1\2", text)
    text = _HARD_HYPHEN_BREAK.sub(r"\1\2", text)
    return text


# ===========================================================================
# Stage 8 — Line Rejoiner (broken PDF wraps)
# ===========================================================================

_TERMINAL_PUNCT = re.compile(r"[.?!:]\s*$")
_IS_HEADING = re.compile(r"^(?:[A-Z][A-Z\s]{3,}|(?:\d+\.)+\d*[a-z]?\s+\w)")


def rejoin_broken_lines(text: str) -> str:
    """
    Join lines that are broken by PDF hard-wrapping.

    A line is joined with the next if:
    - It does NOT end with sentence-terminal punctuation (.?!:)
    - It does NOT look like a section heading (all-caps or numbered)
    - The next line is not a bullet/numbered list item
    """
    lines = text.splitlines()
    result: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.rstrip()

        # Check if this line should be joined with the next
        if (
            i + 1 < len(lines)
            and stripped
            and not _TERMINAL_PUNCT.search(stripped)
            and not _IS_HEADING.match(stripped)
            and not stripped.startswith(("•", "-", "*", "–"))
            and not lines[i + 1].strip().startswith(("•", "-", "*", "–"))
            and lines[i + 1].strip()  # next line is not blank
        ):
            result.append(stripped + " " + lines[i + 1].strip())
            i += 2
        else:
            result.append(stripped)
            i += 1

    return "\n".join(result)


# ===========================================================================
# Master clean function
# ===========================================================================

def clean(text: str, doc_type: str) -> tuple[str, AbbrevMap]:
    """
    Run the full cleaning pipeline on a document's raw text.

    Returns
    -------
    cleaned_text : str
    jnc_abbrev_map : dict  — populated for JNC docs, empty dict otherwise
    """
    abbrev_map: AbbrevMap = {}

    # Stage 1: JNC abbreviation list (must be first — removes block before header clean)
    if doc_type == "jnc":
        text, abbrev_map = parse_jnc_abbreviation_list(text)

    # Stage 2: headers / footers
    text = remove_headers_footers(text, doc_type)

    # Stage 4: reference section sentinel truncation
    text = remove_reference_section(text, doc_type)

    # Stage 5: JNC guideline metadata block
    text = remove_guideline_metadata(text, doc_type)

    # Stage 6: inline noise
    text = remove_inline_noise(text, doc_type)

    # Stage 7: hyphen line joins
    text = join_hyphenated_lines(text)

    # Stage 8: broken line rejoining
    text = rejoin_broken_lines(text)

    return text, abbrev_map
