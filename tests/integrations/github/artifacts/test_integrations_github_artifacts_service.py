from __future__ import annotations

import io
import json
from zipfile import ZipFile

from app.integrations.github.artifacts import (
    build_evidence_artifact_summary,
    parse_evidence_artifact_zip,
    parse_test_results_zip,
)


def _wrapped_payload(*, payload):
    return {
        "schema_version": "1",
        "repository_full_name": "org/repo",
        "commit_sha": "abc123",
        "workflow_run_id": "99",
        "generated_at": "2026-03-13T00:00:00Z",
        "status": "success",
        "payload": payload,
    }


def test_parse_test_results_prefers_json():
    buf = io.BytesIO()
    with ZipFile(buf, "w") as zf:
        zf.writestr(
            "winoe-test-results.json",
            (
                '{"passed":2,"failed":1,"total":3,"stdout":"ok","stderr":"",'
                '"summary":{"detectedTool":"pytest","command":"python -m pytest",'
                '"exitCode":1,"coveragePath":"artifacts/coverage",'
                '"outputLog":"artifacts/test-results/test-output.log"}}'
            ),
        )
    parsed = parse_test_results_zip(buf.getvalue())
    assert parsed
    assert parsed.passed == 2
    assert parsed.failed == 1
    assert parsed.total == 3
    assert parsed.stdout == "ok"
    assert parsed.summary == {
        "detectedTool": "pytest",
        "command": "python -m pytest",
        "exitCode": 1,
        "coveragePath": "artifacts/coverage",
        "outputLog": "artifacts/test-results/test-output.log",
    }


def test_parse_test_results_handles_malformed_json_gracefully():
    buf = io.BytesIO()
    with ZipFile(buf, "w") as zf:
        zf.writestr("winoe-test-results.json", "{not-json")
    assert parse_test_results_zip(buf.getvalue()) is None


def test_parse_test_results_junit_fallback():
    junit_xml = """
    <testsuite name="suite">
        <testcase classname="c" name="pass"/>
        <testcase classname="c" name="fail"><failure/></testcase>
    </testsuite>
    """
    buf = io.BytesIO()
    with ZipFile(buf, "w") as zf:
        zf.writestr("results.xml", junit_xml)
    parsed = parse_test_results_zip(buf.getvalue())
    assert parsed
    assert parsed.passed == 1
    assert parsed.failed == 1
    assert parsed.total == 2
    assert parsed.summary == {"format": "junit"}


def test_parse_test_results_json_fallback_and_bad_xml():
    buf = io.BytesIO()
    with ZipFile(buf, "w") as zf:
        zf.writestr("other.json", '{"passed":3,"failed":1,"total":4,"summary":{"s":1}}')
        zf.writestr("broken.xml", "<testsuite><testcase></testsuite")
    parsed = parse_test_results_zip(buf.getvalue())
    assert parsed
    assert parsed.passed == 3
    assert parsed.total == 4
    assert parsed.summary == {"s": 1}


def test_parse_test_results_bad_xml_only_returns_none():
    buf = io.BytesIO()
    with ZipFile(buf, "w") as zf:
        zf.writestr("only.xml", "<testsuite><bad")
    assert parse_test_results_zip(buf.getvalue()) is None


def test_safe_json_load_returns_none_for_non_dict():
    buf = io.BytesIO()
    with ZipFile(buf, "w") as zf:
        zf.writestr("array.json", "[1,2,3]")
    assert parse_test_results_zip(buf.getvalue()) is None


def test_parse_evidence_artifact_prefers_json_and_keeps_manifest():
    buf = io.BytesIO()
    with ZipFile(buf, "w") as zf:
        zf.writestr(
            "repo_tree_summary.json",
            json.dumps(
                _wrapped_payload(
                    payload={"generatedAt": "2026-03-13T00:00:00Z", "paths": ["a.py"]}
                )
            ),
        )
        zf.writestr("repo_tree_summary.txt", "a.py\n")
    parsed = parse_evidence_artifact_zip(buf.getvalue(), "winoe-repo-tree-summary")
    assert parsed is not None
    assert parsed.artifact_name == "winoe-repo-tree-summary"
    assert parsed.files == [
        "repo_tree_summary.json",
        "repo_tree_summary.txt",
    ]
    assert parsed.data == {
        "schema_version": "1",
        "repository_full_name": "org/repo",
        "commit_sha": "abc123",
        "workflow_run_id": "99",
        "generated_at": "2026-03-13T00:00:00Z",
        "status": "success",
        "payload": {"generatedAt": "2026-03-13T00:00:00Z", "paths": ["a.py"]},
    }
    summary = build_evidence_artifact_summary(parsed)
    assert summary["artifactName"] == "winoe-repo-tree-summary"
    assert summary["jsonFiles"]["repo_tree_summary.json"]["payload"]["paths"] == [
        "a.py"
    ]
