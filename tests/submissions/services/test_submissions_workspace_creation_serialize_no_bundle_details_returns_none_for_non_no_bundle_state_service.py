from __future__ import annotations

from tests.submissions.services.test_submissions_workspace_creation_service_utils import *


def test_serialize_no_bundle_details_returns_none_for_non_no_bundle_state():
    assert (
        wc._serialize_no_bundle_details(
            SimpleNamespace(state="applied", details={"reason": "commit_created"})
        )
        is None
    )
