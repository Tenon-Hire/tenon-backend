from __future__ import annotations

import pytest

from tests.submissions.services.precommit_bundle_runtime.submissions_precommit_bundle_runtime_test_utils import *


def test_parse_patch_entries_and_path_guards():
    assert (
        precommit_service._parse_patch_entries(
            patch_text=json.dumps({"files": [{"path": "a.txt", "delete": True}]}),
            storage_ref=None,
        )[0].delete
        is True
    )

    with pytest.raises(ApiError) as storage_only:
        precommit_service._parse_patch_entries(patch_text=None, storage_ref="ref:abc")
    assert storage_only.value.error_code == "PRECOMMIT_STORAGE_REF_UNSUPPORTED"

    with pytest.raises(ApiError) as invalid_json:
        precommit_service._parse_patch_entries(patch_text="{not-json", storage_ref=None)
    assert invalid_json.value.error_code == "PRECOMMIT_PATCH_INVALID_JSON"

    with pytest.raises(ApiError) as invalid_format:
        precommit_service._parse_patch_entries(
            patch_text=json.dumps({"files": {"path": "x"}}),
            storage_ref=None,
        )
    assert invalid_format.value.error_code == "PRECOMMIT_PATCH_INVALID_FORMAT"

    with pytest.raises(ApiError) as invalid_entry:
        precommit_service._parse_patch_entries(
            patch_text=json.dumps({"files": [123]}),
            storage_ref=None,
        )
    assert invalid_entry.value.error_code == "PRECOMMIT_PATCH_INVALID_ENTRY"

    with pytest.raises(ApiError) as invalid_path:
        precommit_service._parse_patch_entries(
            patch_text=json.dumps({"files": [{"path": 42, "content": "x"}]}),
            storage_ref=None,
        )
    assert invalid_path.value.error_code == "PRECOMMIT_PATCH_INVALID_PATH"

    with pytest.raises(ApiError) as invalid_content:
        precommit_service._parse_patch_entries(
            patch_text=json.dumps({"files": [{"path": "a.txt", "content": 42}]}),
            storage_ref=None,
        )
    assert invalid_content.value.error_code == "PRECOMMIT_PATCH_INVALID_CONTENT"

    for bad_path in ("", "\\bad\\path", "a//b", ".git/config"):
        with pytest.raises(ApiError) as bad_path_error:
            precommit_service._ensure_safe_repo_path(bad_path)
        assert bad_path_error.value.error_code == "PRECOMMIT_PATCH_UNSAFE_PATH"
