"""Application module for integrations github artifacts zip parser utils workflows."""

from __future__ import annotations

import io
import zipfile

from app.integrations.github.artifacts.integrations_github_artifacts_json_parser_utils import (
    parse_any_json,
    parse_named_json,
)
from app.integrations.github.artifacts.integrations_github_artifacts_junit_parser_utils import (
    parse_junit,
)
from app.integrations.github.artifacts.integrations_github_artifacts_models_model import (
    ParsedTestResults,
)


def parse_test_results_zip(content: bytes) -> ParsedTestResults | None:
    """Parse test results zip."""
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            return parse_named_json(zf) or parse_any_json(zf) or parse_junit(zf)
    except zipfile.BadZipFile:
        return None
