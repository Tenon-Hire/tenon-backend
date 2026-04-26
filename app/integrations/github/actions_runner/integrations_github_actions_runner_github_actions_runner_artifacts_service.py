"""Application module for integrations github actions runner github actions runner artifacts service workflows."""

from __future__ import annotations

from typing import Any

from app.integrations.github.actions_runner.integrations_github_actions_runner_github_actions_runner_artifact_list_service import (
    list_artifacts_with_cache,
)
from app.integrations.github.actions_runner.integrations_github_actions_runner_github_actions_runner_artifact_partition_service import (
    partition_artifacts,
)
from app.integrations.github.actions_runner.integrations_github_actions_runner_github_actions_runner_cache_service import (
    ActionsCache,
)
from app.integrations.github.artifacts import (
    EVIDENCE_ARTIFACT_SUMMARY_KEYS,
    ParsedTestResults,
    build_evidence_artifact_summary,
    parse_evidence_artifact_zip,
    parse_test_results_zip,
)
from app.integrations.github.client import GithubClient, GithubError


async def parse_artifacts(
    client: GithubClient, cache: ActionsCache, repo_full_name: str, run_id: int
) -> tuple[ParsedTestResults | None, str | None]:
    """Parse artifacts."""
    artifacts = await list_artifacts_with_cache(client, cache, repo_full_name, run_id)
    preferred, others = partition_artifacts(artifacts)
    test_artifacts = _pick_test_artifacts(preferred + others)
    evidence_key = (repo_full_name, run_id)
    parsed, error, test_evidence = await _parse_first_test_artifact(
        client, cache, repo_full_name, run_id, test_artifacts
    )
    evidence = cache.evidence_summary_cache.get(evidence_key)
    if evidence is None:
        evidence_artifacts = dict(test_evidence)
        evidence_artifacts.update(
            await _collect_evidence_artifacts(
                client,
                repo_full_name,
                preferred + others,
                excluded_artifact_ids={
                    int(a["id"]) for a in test_artifacts if a.get("id")
                },
            )
        )
        if evidence_artifacts:
            evidence = {"evidenceArtifacts": evidence_artifacts}
            cache.cache_evidence_summary(evidence_key, evidence)
    elif test_evidence:
        evidence = dict(evidence)
        merged_artifacts = dict(evidence.get("evidenceArtifacts", {}))
        merged_artifacts.update(test_evidence)
        evidence["evidenceArtifacts"] = merged_artifacts
    if parsed:
        summary = dict(parsed.summary or {})
        if evidence:
            summary["evidenceArtifacts"] = evidence.get("evidenceArtifacts", {})
        parsed.summary = summary or None
        cache.cache_evidence_summary(evidence_key, summary)
        return parsed, None
    if error:
        return None, error
    if artifacts:
        return None, "artifact_missing"
    return None, "artifact_missing"


async def _parse_first_test_artifact(
    client: GithubClient,
    cache: ActionsCache,
    repo_full_name: str,
    run_id: int,
    artifacts: list[dict[str, Any]],
) -> tuple[ParsedTestResults | None, str | None, dict[str, dict[str, Any]]]:
    """Parse the first parseable test-results artifact."""
    found = False
    last_error: str | None = None
    for artifact in artifacts:
        artifact_id = artifact.get("id")
        if not artifact_id:
            continue
        artifact_name = str(artifact.get("name") or "").lower()
        found = True
        cache_key = (repo_full_name, run_id, int(artifact_id))
        cached = cache.artifact_cache.get(cache_key)
        if cached:
            parsed_cached, cached_error = cached
            if parsed_cached or cached_error:
                return parsed_cached, cached_error, {}
        try:
            content = await client.download_artifact_zip(
                repo_full_name, int(artifact_id)
            )
        except GithubError:
            last_error = "artifact_download_failed"
            continue
        parsed = parse_test_results_zip(content)
        if parsed:
            cache.cache_artifact_result(cache_key, parsed, None)
            return (
                parsed,
                None,
                _collect_evidence_from_test_artifact(
                    content, artifact_name, artifact_id
                ),
            )
        last_error = "artifact_corrupt"
        cache.cache_artifact_result(cache_key, None, last_error)
    if found:
        return None, last_error or "artifact_unavailable", {}
    return None, None, {}


def _collect_evidence_from_test_artifact(
    content: bytes, artifact_name: str, artifact_id: Any
) -> dict[str, dict[str, Any]]:
    """Parse evidence payloads that share the test-results artifact zip."""
    summary_key = EVIDENCE_ARTIFACT_SUMMARY_KEYS.get(artifact_name)
    if summary_key is None:
        return {}
    parsed = parse_evidence_artifact_zip(content, artifact_name)
    if parsed is None:
        return {
            summary_key: {
                "artifactName": artifact_name,
                "artifactId": int(artifact_id),
                "error": "artifact_corrupt",
            }
        }
    summary = build_evidence_artifact_summary(parsed)
    summary["artifactId"] = int(artifact_id)
    return {summary_key: summary}


async def _collect_evidence_artifacts(
    client: GithubClient,
    repo_full_name: str,
    artifacts: list[dict[str, Any]],
    *,
    excluded_artifact_ids: set[int] | None = None,
) -> dict[str, dict[str, Any]]:
    """Collect evidence artifact summaries best-effort."""
    evidence: dict[str, dict[str, Any]] = {}
    excluded_artifact_ids = excluded_artifact_ids or set()
    for artifact in artifacts:
        artifact_id = artifact.get("id")
        if not artifact_id:
            continue
        if int(artifact_id) in excluded_artifact_ids:
            continue
        artifact_name = str(artifact.get("name") or "").lower()
        summary_key = EVIDENCE_ARTIFACT_SUMMARY_KEYS.get(artifact_name)
        if summary_key is None:
            continue
        try:
            content = await client.download_artifact_zip(
                repo_full_name, int(artifact_id)
            )
        except GithubError:
            evidence[summary_key] = {
                "artifactName": artifact_name,
                "artifactId": int(artifact_id),
                "error": "artifact_download_failed",
            }
            continue
        parsed = parse_evidence_artifact_zip(content, artifact_name)
        if parsed is None:
            evidence[summary_key] = {
                "artifactName": artifact_name,
                "artifactId": int(artifact_id),
                "error": "artifact_corrupt",
            }
            continue
        summary = build_evidence_artifact_summary(parsed)
        summary["artifactId"] = int(artifact_id)
        evidence[summary_key] = summary
    return evidence


def _pick_test_artifacts(artifacts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return only artifacts that can contain parseable test results."""
    from app.shared.utils.shared_utils_brand_utils import (
        LEGACY_TEST_ARTIFACT_NAMESPACE,
        TEST_ARTIFACT_NAMESPACE,
    )

    allowed_names = {
        TEST_ARTIFACT_NAMESPACE,
        LEGACY_TEST_ARTIFACT_NAMESPACE,
        "test-results",
        "junit",
    }
    selected: list[dict[str, Any]] = []
    for artifact in artifacts:
        if not artifact or artifact.get("expired"):
            continue
        name = str(artifact.get("name") or "").lower()
        if name in allowed_names:
            selected.append(artifact)
    return selected
