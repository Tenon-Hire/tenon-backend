from __future__ import annotations

from tests.integrations.github.template_health.test_integrations_github_template_health_service_utils import *


def test_decode_contents_base64_with_newlines():
    content = "workflow: test"
    encoded = base64.encodebytes(content.encode("utf-8")).decode("ascii")
    payload = {"content": encoded, "encoding": "base64"}
    assert _decode_contents(payload) == content
