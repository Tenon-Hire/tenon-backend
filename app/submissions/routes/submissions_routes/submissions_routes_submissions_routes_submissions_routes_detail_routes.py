"""Application module for submissions routes submissions routes submissions routes detail routes workflows."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.auth.shared_auth_current_user_utils import get_current_user
from app.shared.auth.shared_auth_roles_utils import ensure_talent_partner
from app.shared.database import get_session
from app.shared.database.shared_database_models_model import User
from app.submissions.presentation import present_detail
from app.submissions.routes.submissions_routes.submissions_routes_submissions_routes_submissions_routes_detail_media_routes import (
    resolve_day_audit,
    resolve_media_payload,
)
from app.submissions.schemas.submissions_schemas_submissions_core_schema import (
    TalentPartnerSubmissionDetailOut,
)
from app.submissions.services import (
    service_talent_partner as talent_partner_sub_service,
)

router = APIRouter(prefix="/submissions", tags=["submissions"])
logger = logging.getLogger(__name__)


@router.get("/{submission_id}", response_model=TalentPartnerSubmissionDetailOut)
async def get_submission_detail_route(
    submission_id: int,
    db: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(get_current_user)],
) -> TalentPartnerSubmissionDetailOut:
    """Return Talent Partner-facing detail for a submission."""
    ensure_talent_partner(user)
    sub, task, cs, sim = await talent_partner_sub_service.fetch_detail(
        db,
        submission_id,
        user.id,
        talent_partner_company_id=getattr(user, "company_id", None),
    )
    day_audit = await resolve_day_audit(db, sub=sub, task=task)
    recording, transcript, recording_download_url = await resolve_media_payload(
        db,
        sub=sub,
        task=task,
        cs=cs,
        talent_partner_id=user.id,
        logger=logger,
    )

    payload = present_detail(
        sub,
        task,
        cs,
        sim,
        day_audit=day_audit,
        recording=recording,
        transcript=transcript,
        recording_download_url=recording_download_url,
    )
    return TalentPartnerSubmissionDetailOut(**payload)
