"""
tests/unit/test_config.py
--------------------------
Unit tests for src/ingestion/config.py

Coverage:
  DOC_REGISTRY   structure and required key validation
  get_doc_config  happy path + unknown doc_id error
"""

import pytest
from ingestion.config import DOC_REGISTRY, get_doc_config


# ===========================================================================
# DOC_REGISTRY structure
# ===========================================================================

EXPECTED_DOC_IDS = [
    "metformin_fda_label",
    "ada_standards_care_diabetes_6",
    "ada_standards_care_diabetes_9",
    "jnc8_guidelines_manage_hypertension_original",
]

REQUIRED_KEYS = {"doc_type", "display_name", "n_cols", "skip_first_page", "strip_footer_bbox"}
VALID_DOC_TYPES = {"fda", "ada", "jnc"}


class TestDocRegistry:

    def test_all_expected_doc_ids_present(self):
        for doc_id in EXPECTED_DOC_IDS:
            assert doc_id in DOC_REGISTRY, f"Missing doc_id: {doc_id}"

    def test_all_entries_have_required_keys(self):
        for doc_id, cfg in DOC_REGISTRY.items():
            missing = REQUIRED_KEYS - set(cfg.keys())
            assert not missing, f"doc_id '{doc_id}' missing keys: {missing}"

    def test_doc_types_are_valid(self):
        for doc_id, cfg in DOC_REGISTRY.items():
            assert cfg["doc_type"] in VALID_DOC_TYPES, \
                f"Invalid doc_type '{cfg['doc_type']}' for {doc_id}"

    def test_n_cols_is_positive_integer(self):
        for doc_id, cfg in DOC_REGISTRY.items():
            assert isinstance(cfg["n_cols"], int), f"{doc_id}: n_cols must be int"
            assert cfg["n_cols"] >= 1, f"{doc_id}: n_cols must be >= 1"

    def test_skip_first_page_is_bool(self):
        for doc_id, cfg in DOC_REGISTRY.items():
            assert isinstance(cfg["skip_first_page"], bool), \
                f"{doc_id}: skip_first_page must be bool"

    def test_strip_footer_bbox_is_bool(self):
        for doc_id, cfg in DOC_REGISTRY.items():
            assert isinstance(cfg["strip_footer_bbox"], bool), \
                f"{doc_id}: strip_footer_bbox must be bool"

    def test_display_name_is_non_empty_string(self):
        for doc_id, cfg in DOC_REGISTRY.items():
            assert isinstance(cfg["display_name"], str), f"{doc_id}: display_name must be str"
            assert len(cfg["display_name"]) > 0, f"{doc_id}: display_name is empty"

    # ── Per-document specific assertions ────────────────────────────────────

    def test_fda_is_single_column(self):
        cfg = DOC_REGISTRY["metformin_fda_label"]
        assert cfg["n_cols"] == 1
        # FDA does not skip first page (it's content from page 1)
        assert cfg["skip_first_page"] is False

    def test_ada_is_three_column(self):
        for doc_id in ("ada_standards_care_diabetes_6", "ada_standards_care_diabetes_9"):
            cfg = DOC_REGISTRY[doc_id]
            assert cfg["n_cols"] == 3
            assert cfg["skip_first_page"] is True

    def test_jnc_is_two_column(self):
        cfg = DOC_REGISTRY["jnc8_guidelines_manage_hypertension_original"]
        assert cfg["n_cols"] == 2
        assert cfg["skip_first_page"] is True
        assert cfg["strip_footer_bbox"] is True


# ===========================================================================
# get_doc_config
# ===========================================================================

class TestGetDocConfig:

    def test_returns_correct_config_for_known_id(self):
        cfg = get_doc_config("metformin_fda_label")
        assert cfg["doc_type"] == "fda"
        assert cfg["n_cols"] == 1

    def test_raises_value_error_for_unknown_id(self):
        with pytest.raises(ValueError) as exc_info:
            get_doc_config("nonexistent_document_id")
        assert "nonexistent_document_id" in str(exc_info.value)
        assert "Valid ids" in str(exc_info.value)

    def test_returns_dict(self):
        cfg = get_doc_config("ada_standards_care_diabetes_6")
        assert isinstance(cfg, dict)

    @pytest.mark.parametrize("doc_id", EXPECTED_DOC_IDS)
    def test_all_known_ids_return_without_error(self, doc_id):
        cfg = get_doc_config(doc_id)
        assert cfg is not None
