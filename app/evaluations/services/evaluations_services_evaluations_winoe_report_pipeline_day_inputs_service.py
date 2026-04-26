"""Application module for evaluations services evaluations winoe report pipeline day inputs service workflows."""

from __future__ import annotations

import json
from typing import Any

from app.evaluations.services import (
    evaluations_services_evaluations_evaluator_service as evaluator_service,
)
from app.evaluations.services.evaluations_services_evaluations_evaluator_models_service import (
    CodeImplementationEvidenceContext,
)
from app.evaluations.services.evaluations_services_evaluations_winoe_report_pipeline_constants_service import (
    DEFAULT_RUBRIC_VERSION,
)
from app.evaluations.services.evaluations_services_evaluations_winoe_report_pipeline_parse_service import (
    _parse_diff_summary,
)
from app.shared.database.shared_database_models_model import (
    CandidateDayAudit,
    Submission,
    Task,
)


def _load_json_object(value: object) -> dict[str, Any] | None:
    if isinstance(value, dict):
        return value
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = json.loads(value)
    except ValueError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _submission_test_summary(submission: Submission | None) -> dict[str, Any] | None:
    if submission is None:
        return None
    return _load_json_object(submission.test_output)


def _submission_inner_summary(submission: Submission | None) -> dict[str, Any] | None:
    summary = _submission_test_summary(submission)
    if not isinstance(summary, dict):
        return None
    inner_summary = summary.get("summary")
    return inner_summary if isinstance(inner_summary, dict) else None


def _summary_evidence_artifacts(
    submission: Submission | None,
) -> dict[str, dict[str, Any]] | None:
    summary = _submission_inner_summary(submission)
    if not isinstance(summary, dict):
        return None
    evidence_artifacts = summary.get("evidenceArtifacts")
    return evidence_artifacts if isinstance(evidence_artifacts, dict) else None


def _summary_without_evidence(submission: Submission | None) -> dict[str, Any] | None:
    summary = _submission_inner_summary(submission)
    if not isinstance(summary, dict):
        return None
    filtered = {
        key: value for key, value in summary.items() if key != "evidenceArtifacts"
    }
    return filtered or None


def _artifact_payload(
    evidence_artifacts: dict[str, dict[str, Any]] | None,
    key: str,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    if not isinstance(evidence_artifacts, dict):
        return None, None
    artifact = evidence_artifacts.get(key)
    if not isinstance(artifact, dict):
        return None, None
    data = artifact.get("data")
    if not isinstance(data, dict):
        return artifact, None
    payload = data.get("payload")
    return artifact, payload if isinstance(payload, dict) else None


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        if not isinstance(item, str):
            continue
        normalized = item.strip()
        if normalized:
            result.append(normalized)
    return result


def _commit_history_from_submission(
    *,
    submission: Submission,
    day_index: int,
    evidence_artifacts: dict[str, dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    artifact, payload = _artifact_payload(evidence_artifacts, "commitMetadata")
    if artifact is None or payload is None:
        return []
    commits = payload.get("commits")
    if not isinstance(commits, list):
        return []
    artifact_id = artifact.get("artifactId")
    commit_history: list[dict[str, Any]] = []
    for commit in commits:
        if not isinstance(commit, dict):
            continue
        sha = commit.get("sha")
        if not isinstance(sha, str) or not sha.strip():
            continue
        files_changed_paths = _string_list(commit.get("files_changed"))
        files_changed_count = commit.get("files_changed_count")
        commit_history.append(
            {
                "sha": sha.strip(),
                "message": commit.get("message"),
                "committedAt": commit.get("timestamp"),
                "authoredAt": commit.get("timestamp"),
                "author": commit.get("author"),
                "filesChanged": files_changed_count
                if isinstance(files_changed_count, int)
                else len(files_changed_paths),
                "filesChangedPaths": files_changed_paths,
                "additions": commit.get("insertions"),
                "deletions": commit.get("deletions"),
                "dayIndex": day_index,
                "submissionId": submission.id,
                "evidenceArtifactId": artifact_id,
            }
        )
    return commit_history


def _file_creation_timeline_from_submission(
    *,
    submission: Submission,
    day_index: int,
    evidence_artifacts: dict[str, dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    artifact, payload = _artifact_payload(evidence_artifacts, "fileCreationTimeline")
    if artifact is None or payload is None:
        return []
    files = payload.get("files")
    if not isinstance(files, list):
        return []
    artifact_id = artifact.get("artifactId")
    timeline: list[dict[str, Any]] = []
    for event in files:
        if not isinstance(event, dict):
            continue
        created_at = event.get("timestamp")
        first_commit_sha = event.get("commit_sha")
        message = event.get("message")
        paths = event.get("files")
        if not isinstance(paths, list):
            continue
        for path in paths:
            if not isinstance(path, str) or not path.strip():
                continue
            timeline.append(
                {
                    "path": path.strip(),
                    "createdAt": created_at,
                    "firstCommitSha": first_commit_sha,
                    "commitMessage": message,
                    "dayIndex": day_index,
                    "submissionId": submission.id,
                    "evidenceArtifactId": artifact_id,
                }
            )
    return timeline


def _dependency_metadata_from_submission(
    *,
    day_index: int,
    submission: Submission,
    evidence_artifacts: dict[str, dict[str, Any]] | None,
) -> dict[str, Any] | None:
    artifact, payload = _artifact_payload(evidence_artifacts, "dependencyManifests")
    if artifact is None or payload is None:
        return None
    manifests = payload.get("manifests")
    if not isinstance(manifests, list):
        return None
    return {
        "dayIndex": day_index,
        "submissionId": submission.id,
        "evidenceArtifactId": artifact.get("artifactId"),
        "detected": bool(payload.get("detected")),
        "manifests": [dict(item) for item in manifests if isinstance(item, dict)],
    }


def _repository_snapshot_status(
    *,
    repository_reference: str | None,
    day_submission_refs: list[dict[str, Any]],
    commit_history: list[dict[str, Any]],
    file_creation_timeline: list[dict[str, Any]],
    test_coverage_progression: list[dict[str, Any]],
    dependency_metadata: dict[str, Any] | None,
    documentation_evolution: list[dict[str, Any]],
) -> str:
    has_day_evidence = bool(day_submission_refs)
    has_snapshot_artifacts = bool(
        commit_history
        or file_creation_timeline
        or test_coverage_progression
        or dependency_metadata is not None
        or documentation_evolution
    )
    if not has_day_evidence and not repository_reference:
        return "unavailable: no day 2/3 repository or submission evidence found"
    if repository_reference and has_snapshot_artifacts:
        return "available: derived from day 2/3 repository and submission evidence"
    if repository_reference:
        return (
            "partial: repository reference available; persisted repository snapshot "
            "artifacts not found for day 2/3 evidence"
        )
    return (
        "partial: day 2/3 submission evidence available; repository reference not "
        "resolved and persisted repository snapshot artifacts not found"
    )


def _test_coverage_progression_from_submission(
    *,
    day_index: int,
    submission: Submission,
    evidence_artifacts: dict[str, dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    artifact, _payload = _artifact_payload(evidence_artifacts, "testResults")
    if artifact is None:
        return []
    summary = _summary_without_evidence(submission)
    if not isinstance(summary, dict):
        return []
    coverage_path = summary.get("coveragePath")
    if not isinstance(coverage_path, str) or not coverage_path.strip():
        return []
    captured_at = (
        submission.workflow_run_completed_at.isoformat()
        if submission.workflow_run_completed_at is not None
        else (
            submission.last_run_at.isoformat()
            if submission.last_run_at is not None
            else None
        )
    )
    return [
        {
            "dayIndex": day_index,
            "submissionId": submission.id,
            "commitSha": submission.commit_sha,
            "workflowRunId": submission.workflow_run_id,
            "capturedAt": captured_at,
            "testsPassed": submission.tests_passed,
            "testsFailed": submission.tests_failed,
            "coveragePath": coverage_path.strip(),
            "outputLog": summary.get("outputLog"),
            "command": summary.get("command"),
            "detectedTool": summary.get("detectedTool"),
            "exitCode": summary.get("exitCode"),
            "evidenceArtifactId": artifact.get("artifactId"),
        }
    ]


def _documentation_evolution_from_commit_history(
    commit_history: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    documentation_evolution: list[dict[str, Any]] = []
    for commit in commit_history:
        paths = commit.get("filesChangedPaths")
        if not isinstance(paths, list):
            continue
        doc_paths = [
            path
            for path in paths
            if isinstance(path, str)
            and path.strip()
            and (
                path.strip().lower().endswith("readme.md")
                or path.strip().lower().startswith("docs/")
                or "/docs/" in f"/{path.strip().lower()}/"
            )
        ]
        if not doc_paths:
            continue
        documentation_evolution.append(
            {
                "dayIndex": commit.get("dayIndex"),
                "submissionId": commit.get("submissionId"),
                "commitSha": commit.get("sha"),
                "message": commit.get("message"),
                "documentationPaths": doc_paths,
                "evidenceArtifactId": commit.get("evidenceArtifactId"),
            }
        )
    return documentation_evolution


def _resolve_rubric_version(context) -> str:
    version = getattr(
        getattr(context, "scenario_version", None), "rubric_version", None
    )
    return (
        version
        if isinstance(version, str) and version.strip()
        else DEFAULT_RUBRIC_VERSION
    )


def _build_day_inputs(
    *,
    tasks_by_day: dict[int, Task],
    submissions_by_day: dict[int, Submission],
    day_audits: dict[int, CandidateDayAudit],
    transcript_reference: str,
    normalized_segments: list[dict[str, object]],
) -> list[evaluator_service.DayEvaluationInput]:
    day_inputs: list[evaluator_service.DayEvaluationInput] = []
    for day_index in range(1, 6):
        task = tasks_by_day.get(day_index)
        submission = submissions_by_day.get(day_index)
        day_audit = day_audits.get(day_index)
        day_inputs.append(
            evaluator_service.DayEvaluationInput(
                day_index=day_index,
                task_id=task.id if task is not None else None,
                task_type=task.type if task is not None else None,
                submission_id=submission.id if submission is not None else None,
                content_text=submission.content_text
                if submission is not None
                else None,
                content_json=(
                    submission.content_json
                    if submission is not None
                    and isinstance(submission.content_json, dict)
                    else None
                ),
                repo_full_name=submission.code_repo_path
                if submission is not None
                else None,
                commit_sha=submission.commit_sha if submission is not None else None,
                workflow_run_id=submission.workflow_run_id
                if submission is not None
                else None,
                diff_summary=(
                    _parse_diff_summary(submission.diff_summary_json)
                    if submission is not None
                    else None
                ),
                tests_passed=submission.tests_passed
                if submission is not None
                else None,
                tests_failed=submission.tests_failed
                if submission is not None
                else None,
                transcript_reference=transcript_reference if day_index == 4 else None,
                transcript_segments=normalized_segments if day_index == 4 else [],
                cutoff_commit_sha=(
                    day_audit.cutoff_commit_sha if day_audit is not None else None
                ),
                eval_basis_ref=day_audit.eval_basis_ref
                if day_audit is not None
                else None,
            )
        )
    return day_inputs


def _build_code_implementation_evidence_context(
    *,
    candidate_session_id: int,
    submissions_by_day: dict[int, Submission],
    day_audits: dict[int, CandidateDayAudit],
) -> CodeImplementationEvidenceContext:
    """Build the structured repository/process evidence payload for Days 2 and 3."""
    day_submissions = {
        day_index: submissions_by_day.get(day_index) for day_index in (2, 3)
    }
    repo_full_name = next(
        (
            submission.code_repo_path
            for submission in day_submissions.values()
            if submission is not None and submission.code_repo_path
        ),
        None,
    )
    repo_url = f"https://github.com/{repo_full_name}" if repo_full_name else None
    primary_submission = day_submissions.get(3) or day_submissions.get(2)
    repository_artifact_references: list[dict[str, Any]] = []
    day_submission_refs: list[dict[str, Any]] = []
    cutoff_commit_shas: dict[str, str] = {}
    commit_history: list[dict[str, Any]] = []
    file_creation_timeline: list[dict[str, Any]] = []
    test_coverage_progression: list[dict[str, Any]] = []
    dependency_metadata: dict[str, Any] | None = None
    repository_snapshot: dict[str, Any] = {
        "candidateSessionId": candidate_session_id,
        "repoFullName": repo_full_name,
        "repoUrl": repo_url,
        "daySubmissionRefs": day_submission_refs,
        "cutoffCommitShas": None,
        "latestKnownCommitSha": None,
        "latestKnownWorkflowRunId": None,
        "latestKnownWorkflowRunUrl": None,
        "latestKnownDiffSummary": None,
        "latestKnownTestSummary": None,
        "latestKnownRepoTreeSummary": None,
    }
    for day_index, submission in day_submissions.items():
        if submission is None:
            continue
        evidence_artifacts = _summary_evidence_artifacts(submission)
        cutoff_commit_sha = (
            day_audits.get(day_index).cutoff_commit_sha
            if day_index in day_audits
            else None
        )
        if isinstance(cutoff_commit_sha, str) and cutoff_commit_sha.strip():
            cutoff_commit_shas[str(day_index)] = cutoff_commit_sha.strip()
        workflow_run_id = (
            submission.workflow_run_id.strip()
            if isinstance(submission.workflow_run_id, str)
            and submission.workflow_run_id.strip()
            else None
        )
        workflow_run_url = (
            f"https://github.com/{repo_full_name}/actions/runs/{workflow_run_id}"
            if repo_full_name and workflow_run_id
            else None
        )
        day_submission_refs.append(
            {
                "dayIndex": day_index,
                "submissionId": submission.id,
                "taskId": submission.task_id,
                "commitSha": submission.commit_sha,
                "checkpointSha": submission.checkpoint_sha,
                "finalSha": submission.final_sha,
                "workflowRunId": workflow_run_id,
                "workflowRunUrl": workflow_run_url,
                "cutoffCommitSha": cutoff_commit_sha,
                "diffSummary": _parse_diff_summary(submission.diff_summary_json),
                "testsPassed": submission.tests_passed,
                "testsFailed": submission.tests_failed,
                "testOutputPresent": bool(
                    isinstance(submission.test_output, str)
                    and submission.test_output.strip()
                ),
            }
        )
        if workflow_run_url is not None:
            repository_artifact_references.append(
                {
                    "kind": "workflow_run",
                    "dayIndex": day_index,
                    "submissionId": submission.id,
                    "workflowRunId": workflow_run_id,
                    "workflowRunUrl": workflow_run_url,
                }
            )
        if evidence_artifacts:
            repository_artifact_references.extend(
                [
                    {
                        "kind": "artifact_summary",
                        "artifactName": artifact_name,
                        "dayIndex": day_index,
                        "submissionId": submission.id,
                        "artifactId": artifact.get("artifactId"),
                    }
                    for artifact_name, artifact in evidence_artifacts.items()
                    if isinstance(artifact, dict)
                ]
            )
            commit_history.extend(
                _commit_history_from_submission(
                    submission=submission,
                    day_index=day_index,
                    evidence_artifacts=evidence_artifacts,
                )
            )
            file_creation_timeline.extend(
                _file_creation_timeline_from_submission(
                    submission=submission,
                    day_index=day_index,
                    evidence_artifacts=evidence_artifacts,
                )
            )
            test_coverage_progression.extend(
                _test_coverage_progression_from_submission(
                    submission=submission,
                    day_index=day_index,
                    evidence_artifacts=evidence_artifacts,
                )
            )
            if dependency_metadata is None:
                dependency_metadata = _dependency_metadata_from_submission(
                    submission=submission,
                    day_index=day_index,
                    evidence_artifacts=evidence_artifacts,
                )

    latest_commit_sha = None
    latest_workflow_run_id = None
    latest_workflow_run_url = None
    latest_test_summary = None
    latest_diff_summary = None
    latest_repo_tree_summary = None
    if primary_submission is not None:
        latest_commit_sha = (
            primary_submission.commit_sha
            or primary_submission.final_sha
            or primary_submission.checkpoint_sha
        )
        latest_workflow_run_id = (
            primary_submission.workflow_run_id.strip()
            if isinstance(primary_submission.workflow_run_id, str)
            and primary_submission.workflow_run_id.strip()
            else None
        )
        latest_workflow_run_url = (
            f"https://github.com/{repo_full_name}/actions/runs/{latest_workflow_run_id}"
            if repo_full_name and latest_workflow_run_id
            else None
        )
        latest_test_summary = {
            "testsPassed": primary_submission.tests_passed,
            "testsFailed": primary_submission.tests_failed,
            "workflowRunStatus": primary_submission.workflow_run_status,
            "workflowRunConclusion": primary_submission.workflow_run_conclusion,
            "lastRunAt": primary_submission.last_run_at.isoformat()
            if primary_submission.last_run_at
            else None,
        }
        latest_diff_summary = _parse_diff_summary(primary_submission.diff_summary_json)
        primary_evidence_artifacts = _summary_evidence_artifacts(primary_submission)
        if primary_evidence_artifacts is not None:
            latest_repo_tree_summary = primary_evidence_artifacts.get("repoTreeSummary")
    repository_snapshot.update(
        {
            "cutoffCommitShas": cutoff_commit_shas or None,
            "latestKnownCommitSha": latest_commit_sha,
            "latestKnownWorkflowRunId": latest_workflow_run_id,
            "latestKnownWorkflowRunUrl": latest_workflow_run_url,
            "latestKnownDiffSummary": latest_diff_summary,
            "latestKnownTestSummary": latest_test_summary,
            "latestKnownRepoTreeSummary": latest_repo_tree_summary,
        }
    )
    documentation_evolution = _documentation_evolution_from_commit_history(
        commit_history
    )

    evidence_status = {
        "repository_snapshot": _repository_snapshot_status(
            repository_reference=repo_full_name,
            day_submission_refs=day_submission_refs,
            commit_history=commit_history,
            file_creation_timeline=file_creation_timeline,
            test_coverage_progression=test_coverage_progression,
            dependency_metadata=dependency_metadata,
            documentation_evolution=documentation_evolution,
        ),
        "commit_history": (
            "available: derived from persisted submission.test_output summary evidenceArtifacts.commitMetadata"
            if commit_history
            else "unavailable: persisted submission.test_output summary evidenceArtifacts.commitMetadata not found for day 2/3 evidence"
        ),
        "file_creation_timeline": (
            "available: derived from persisted submission.test_output summary evidenceArtifacts.fileCreationTimeline"
            if file_creation_timeline
            else "unavailable: persisted submission.test_output summary evidenceArtifacts.fileCreationTimeline not found for day 2/3 evidence"
        ),
        "test_coverage_progression": (
            "available: derived from persisted submission.test_output summary evidenceArtifacts.testResults and coveragePath"
            if test_coverage_progression
            else "unavailable: persisted submission.test_output summary evidenceArtifacts.testResults coveragePath not found for day 2/3 evidence"
        ),
        "dependency_metadata": (
            "available: derived from persisted submission.test_output summary evidenceArtifacts.dependencyManifests"
            if dependency_metadata is not None
            else "unavailable: persisted submission.test_output summary evidenceArtifacts.dependencyManifests not found for day 2/3 evidence"
        ),
        "documentation_evolution": (
            "available: derived from commit history entries touching README or docs files"
            if documentation_evolution
            else "unavailable: documentation evolution artifacts not found for day 2/3 evidence"
        ),
    }
    return CodeImplementationEvidenceContext(
        repository_snapshot=repository_snapshot,
        repository_url=repo_url,
        repository_reference=repo_full_name,
        repository_artifact_references=repository_artifact_references,
        commit_history=commit_history,
        file_creation_timeline=file_creation_timeline,
        test_coverage_progression=test_coverage_progression,
        dependency_metadata=dependency_metadata,
        documentation_evolution=documentation_evolution,
        evidence_status=evidence_status,
    )


__all__ = [
    "_build_code_implementation_evidence_context",
    "_build_day_inputs",
    "_resolve_rubric_version",
]
