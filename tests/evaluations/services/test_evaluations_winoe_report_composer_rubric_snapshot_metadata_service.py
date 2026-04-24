from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from app.evaluations.services.evaluations_services_evaluations_winoe_report_composer_service import (
    build_ready_payload,
)


def test_build_ready_payload_includes_rubric_snapshot_metadata():
    rubric_snapshots = [
        {
            "snapshotId": 101,
            "scenarioVersionId": 7,
            "rubricScope": "winoe",
            "rubricKind": "day_1_design_doc",
            "rubricKey": "designDocReviewer",
            "rubricVersion": "v1",
            "contentHash": "hash-1",
            "sourcePath": "app/evaluations/rubrics/day_1_design_doc.md",
        }
    ]
    run = SimpleNamespace(
        overall_winoe_score=0.78,
        recommendation="hire",
        confidence=0.82,
        raw_report_json={"overallWinoeScore": 0.78},
        scenario_version_id=7,
        day_scores=[
            SimpleNamespace(
                day_index=1,
                score=0.8,
                rubric_results_json={"signal": 0.8},
                evidence_pointers_json=[],
            )
        ],
        reviewer_reports=[],
        metadata_json={
            "rubricSnapshots": rubric_snapshots,
            "aiPolicyProvider": "anthropic",
            "aiPolicySnapshotDigest": "digest-1",
        },
        model_name="fit-evaluator",
        model_version="2026-03-12",
        prompt_version="winoe-report-v1",
        rubric_version="rubric-v3",
        generated_at=datetime(2026, 3, 12, 12, 3, tzinfo=UTC),
        completed_at=datetime(2026, 3, 12, 12, 3, tzinfo=UTC),
        started_at=datetime(2026, 3, 12, 12, 0, tzinfo=UTC),
    )

    payload = build_ready_payload(run)
    report_version = payload["report"]["version"]
    assert report_version["scenarioVersionId"] == 7
    assert report_version["rubricSnapshots"] == rubric_snapshots
    assert report_version["rubricSnapshots"][0]["snapshotId"] == 101
    assert report_version["rubricSnapshots"][0]["scenarioVersionId"] == 7
    assert report_version["rubricSnapshots"][0]["rubricScope"] == "winoe"
    assert report_version["rubricSnapshots"][0]["rubricKind"] == "day_1_design_doc"
    assert report_version["rubricSnapshots"][0]["rubricKey"] == "designDocReviewer"
    assert report_version["rubricSnapshots"][0]["rubricVersion"] == "v1"
    assert report_version["rubricSnapshots"][0]["contentHash"] == "hash-1"
    assert report_version["rubricSnapshots"][0]["sourcePath"].endswith(
        "day_1_design_doc.md"
    )
