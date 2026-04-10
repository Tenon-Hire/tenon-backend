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
from app.integrations.github.artifacts.integrations_github_artifacts_zip_parser_utils import (
    parse_test_results_zip,
)
from app.shared.utils.shared_utils_brand_utils import (
    LEGACY_TEST_ARTIFACT_NAMESPACE,
    TEST_ARTIFACT_NAMESPACE,
)

PREFERRED_ARTIFACT_NAMES = {
    TEST_ARTIFACT_NAMESPACE,
    LEGACY_TEST_ARTIFACT_NAMESPACE,
    "test-results",
    "junit",
}

__all__ = [
    "ParsedTestResults",
    "PREFERRED_ARTIFACT_NAMES",
    "parse_any_json",
    "parse_named_json",
    "parse_junit",
    "parse_test_results_zip",
]
