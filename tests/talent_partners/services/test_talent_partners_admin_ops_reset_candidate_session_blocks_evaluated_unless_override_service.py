from __future__ import annotations

import pytest

from tests.talent_partners.services.talent_partners_admin_ops_utils import *


@pytest.mark.asyncio
async def test_reset_candidate_session_blocks_evaluated_unless_override(async_session):
    talent_partner = await create_talent_partner(
        async_session, email="reset-eval-owner@test.com"
    )
    trial, _ = await create_trial(async_session, created_by=talent_partner)
    candidate_session = await create_candidate_session(
        async_session,
        trial=trial,
        status="completed",
        candidate_auth0_sub="auth0|candidate-reset-eval",
        claimed_at=datetime.now(UTC) - timedelta(days=1),
        completed_at=datetime.now(UTC) - timedelta(hours=1),
    )
    async_session.add(
        EvaluationRun(
            candidate_session_id=candidate_session.id,
            scenario_version_id=candidate_session.scenario_version_id,
            status=EVALUATION_RUN_STATUS_COMPLETED,
            started_at=datetime.now(UTC) - timedelta(hours=2),
            completed_at=datetime.now(UTC) - timedelta(hours=1),
            model_name="eval-model",
            model_version="v1",
            prompt_version="p1",
            rubric_version="r1",
            day2_checkpoint_sha="day2",
            day3_final_sha="day3",
            cutoff_commit_sha="cutoff",
            transcript_reference="transcript://reset-eval",
        )
    )
    await async_session.commit()

    with pytest.raises(ApiError) as blocked:
        await admin_ops_service.reset_candidate_session(
            async_session,
            actor=_actor(),
            candidate_session_id=candidate_session.id,
            target_state="claimed",
            reason="block evaluated",
            override_if_evaluated=False,
            dry_run=False,
        )
    assert blocked.value.status_code == 409
    assert blocked.value.error_code == admin_ops_service.UNSAFE_OPERATION_ERROR_CODE

    allowed = await admin_ops_service.reset_candidate_session(
        async_session,
        actor=_actor(),
        candidate_session_id=candidate_session.id,
        target_state="claimed",
        reason="  override   evaluated \n reset ",
        override_if_evaluated=True,
        dry_run=False,
    )
    assert allowed.status == "ok"
    assert allowed.audit_id is not None
    audit = await _audit_by_id(async_session, allowed.audit_id)
    assert audit.payload_json["reason"] == "override evaluated reset"
    assert audit.payload_json["overrideIfEvaluated"] is True
    assert audit.payload_json["evaluated"] is True
