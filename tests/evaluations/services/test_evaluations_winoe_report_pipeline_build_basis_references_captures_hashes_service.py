from __future__ import annotations

from tests.evaluations.services.evaluations_winoe_report_pipeline_utils import *


def test_build_basis_references_captures_hashes():
    submission = SimpleNamespace(
        id=7,
        submitted_at=datetime(2026, 3, 12, 14, 0, tzinfo=UTC),
        content_text="text",
        content_json={"k": "v"},
        commit_sha="abc",
        checkpoint_sha="def",
        final_sha="ghi",
        workflow_run_id="123",
        diff_summary_json='{"base":"x","head":"y"}',
        tests_passed=4,
        tests_failed=1,
        test_output="ok",
        last_run_at=datetime(2026, 3, 12, 14, 5, tzinfo=UTC),
    )
    day_audit = SimpleNamespace(cutoff_commit_sha="cutoff", eval_basis_ref="basis-ref")

    references = winoe_report_pipeline._build_basis_references(
        scenario_version_id=22,
        scenario_rubric_version="rubric-v2",
        day_audits={2: day_audit},
        submissions_by_day={2: submission},
        transcript_reference="transcript:11",
        transcript_hash="hash-11",
        disabled_day_indexes=[4],
    )

    assert references["scenarioVersionId"] == 22
    assert references["rubricVersion"] == "rubric-v2"
    assert references["dayRefs"]["2"]["submissionId"] == 7
    assert references["dayRefs"]["2"]["cutoffCommitSha"] == "cutoff"
    assert references["transcriptReference"] == "transcript:11"
    assert references["disabledDayIndexes"] == [4]
