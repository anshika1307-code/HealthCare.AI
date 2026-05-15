"""
config.py
---------
Document registry — per-document extraction and cleaning configuration.

Every key in DOC_REGISTRY maps a doc_id to a settings dict consumed by
PDFExtractor and the cleaning stages. Centralising this here means changing
a regex or a flag never requires touching the pipeline logic.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Document Registry
# ---------------------------------------------------------------------------
# Keys used by PDFExtractor:
#   n_cols          : int  — 1=single col, 2=JNC 2-col, 3=ADA 3-col
#   skip_first_page : bool — discard page index 0 before any cleaning
#   strip_footer_bbox: bool — remove blocks in bottom 8% by bounding box (JNC)
#
# Keys used by Cleaner:
#   doc_type        : str  — "fda" | "ada" | "jnc"

DOC_REGISTRY: dict[str, dict] = {
    "metformin_fda_label": {
        "doc_type": "fda",
        "display_name": "Metformin FDA Label",
        "n_cols": 1,
        "skip_first_page": False,
        "strip_footer_bbox": False,
    },
    "ada_standards_care_diabetes_6": {
        "doc_type": "ada",
        "display_name": "ADA Standards of Care in Diabetes — Section 6 (Glycemic Targets)",
        "n_cols": 3,
        "skip_first_page": True,
        "strip_footer_bbox": False,
    },
    "ada_standards_care_diabetes_9": {
        "doc_type": "ada",
        "display_name": "ADA Standards of Care in Diabetes — Section 9 (Pharmacologic Approaches)",
        "n_cols": 3,
        "skip_first_page": True,
        "strip_footer_bbox": False,
    },
    "jnc8_guidelines_manage_hypertension_original": {
        "doc_type": "jnc",
        "display_name": "JNC 8 Hypertension Guidelines (Original JAMA Paper)",
        "n_cols": 2,
        "skip_first_page": True,
        "strip_footer_bbox": True,
    },
}


def get_doc_config(doc_id: str) -> dict:
    if doc_id not in DOC_REGISTRY:
        raise ValueError(
            f"Unknown doc_id '{doc_id}'. "
            f"Valid ids: {list(DOC_REGISTRY.keys())}"
        )
    return DOC_REGISTRY[doc_id]
