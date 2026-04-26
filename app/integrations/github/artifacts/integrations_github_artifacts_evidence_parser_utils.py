"""Application module for integrations github artifacts evidence parser utils workflows."""

from __future__ import annotations

import io
import json
from typing import Any
from zipfile import BadZipFile, ZipFile

from app.integrations.github.artifacts.integrations_github_artifacts_models_model import (
    ParsedArtifactEvidence,
)

EVIDENCE_ARTIFACT_SUMMARY_KEYS: dict[str, str] = {
    "winoe-commit-metadata": "commitMetadata",
    "winoe-file-creation-timeline": "fileCreationTimeline",
    "winoe-repo-tree-summary": "repoTreeSummary",
    "winoe-dependency-manifests": "dependencyManifests",
    "winoe-test-detection": "testDetection",
    "winoe-test-results": "testResults",
    "winoe-lint-detection": "lintDetection",
    "winoe-lint-results": "lintResults",
    "winoe-evidence-manifest": "evidenceManifest",
    # Legacy compatibility only. The v4 active path uses repo-tree summary.
    "winoe-repo-structure-snapshot": "repoStructureSnapshot",
    "winoe-coverage": "coverage",
}


def parse_evidence_artifact_zip(
    content: bytes, artifact_name: str
) -> ParsedArtifactEvidence | None:
    """Parse a non-test evidence artifact zip."""
    try:
        with ZipFile(io.BytesIO(content)) as zf:
            files = list(zf.namelist())
            json_files: dict[str, Any] = {}
            text_files: dict[str, str] = {}
            for name in files:
                lower_name = name.lower()
                if lower_name.endswith(".json"):
                    with zf.open(name) as fp:
                        data = _safe_json_load(fp)
                    if data is not None:
                        json_files[name] = data
                elif artifact_name.lower() in {
                    "winoe-repo-structure-snapshot",
                    "winoe-repo-tree-summary",
                } and lower_name.endswith(".txt"):
                    with zf.open(name) as fp:
                        text_files[name] = _safe_text_load(fp)
            data = _choose_primary_payload(
                artifact_name=artifact_name,
                json_files=json_files,
                text_files=text_files,
            )
            return ParsedArtifactEvidence(
                artifact_name=artifact_name,
                files=files,
                data=data,
                json_files=json_files or None,
                text_files=text_files or None,
            )
    except BadZipFile:
        return None


def build_evidence_artifact_summary(
    evidence: ParsedArtifactEvidence,
) -> dict[str, Any]:
    """Build a machine-readable summary for an evidence artifact."""
    payload: dict[str, Any] = {
        "artifactName": evidence.artifact_name,
        "files": evidence.files,
    }
    if evidence.data is not None:
        payload["data"] = evidence.data
    if evidence.json_files:
        payload["jsonFiles"] = evidence.json_files
    if evidence.text_files:
        payload["textFiles"] = evidence.text_files
    if evidence.error:
        payload["error"] = evidence.error
    return payload


def _choose_primary_payload(
    *,
    artifact_name: str,
    json_files: dict[str, Any],
    text_files: dict[str, str],
) -> Any | None:
    if json_files:
        if len(json_files) == 1:
            return next(iter(json_files.values()))
        preferred_file = {
            "winoe-repo-tree-summary": "repo_tree_summary.json",
            "winoe-repo-structure-snapshot": "repo-structure-snapshot.json",
            "winoe-commit-metadata": "commit_metadata.json",
            "winoe-file-creation-timeline": "file_creation_timeline.json",
            "winoe-dependency-manifests": "dependency_manifests.json",
            "winoe-test-detection": "test_detection.json",
            "winoe-test-results": "test_results.json",
            "winoe-lint-detection": "lint_detection.json",
            "winoe-lint-results": "lint_results.json",
            "winoe-evidence-manifest": "evidence_manifest.json",
        }.get(artifact_name.lower())
        if preferred_file and preferred_file in json_files:
            return json_files[preferred_file]
        return json_files
    if (
        artifact_name.lower()
        in {
            "winoe-repo-structure-snapshot",
            "winoe-repo-tree-summary",
        }
        and text_files
    ):
        if len(text_files) == 1:
            return next(iter(text_files.values()))
        return text_files
    return None


def _safe_json_load(fp) -> Any | None:
    try:
        return json.load(fp)
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
        return None


def _safe_text_load(fp) -> str:
    raw = fp.read()
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("utf-8", errors="replace")
