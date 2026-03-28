"""Application module for integrations github template health github template health artifact selection service workflows."""

from __future__ import annotations

from app.integrations.github.template_health.integrations_github_template_health_github_template_health_schema import (
    LEGACY_ARTIFACT_NAME,
)
from app.shared.utils.shared_utils_brand_utils import TEST_ARTIFACT_NAMESPACE


def select_artifacts(artifacts):
    """Execute select artifacts."""
    tenon_artifact = legacy_artifact = None
    artifact_name_found = None
    for artifact in artifacts:
        if not artifact or artifact.get("expired"):
            continue
        name = str(artifact.get("name") or "")
        lowered = name.lower()
        if lowered == LEGACY_ARTIFACT_NAME:
            legacy_artifact = artifact
            artifact_name_found = name
        if lowered == TEST_ARTIFACT_NAMESPACE:
            tenon_artifact = artifact
            artifact_name_found = name
    return tenon_artifact, legacy_artifact, artifact_name_found
