from __future__ import annotations

from tests.integrations.github.template_health.test_integrations_github_template_health_service_utils import *


def test_extract_test_results_json_non_dict_payload():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            f"{template_health.TEST_ARTIFACT_NAMESPACE}.json",
            "[]",
        )
    assert template_health._extract_test_results_json(buf.getvalue()) is None
