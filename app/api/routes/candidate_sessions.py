from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Path, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.notifications import get_email_service
from app.domains.candidate_sessions import service as cs_service
from app.domains.candidate_sessions.auth_tokens import mint_candidate_token
from app.domains.candidate_sessions.schemas import (
    CandidateInviteListItem,
    CandidateSessionResolveResponse,
    CandidateSimulationSummary,
    CandidateVerificationConfirmRequest,
    CandidateVerificationConfirmResponse,
    CandidateVerificationSendResponse,
    CurrentTaskResponse,
    ProgressSummary,
)
from app.domains.notifications import service as notification_service
from app.domains.simulations import service as sim_service
from app.domains.tasks.schemas_public import TaskPublic
from app.infra.db import get_session
from app.infra.security.candidate_access import require_candidate_principal
from app.infra.security.principal import Principal
from app.services.email import EmailService

router = APIRouter()

MAX_VERIFICATION_CODE_ATTEMPTS = 5
VERIFICATION_CODE_COOLDOWN_SECONDS = 60
VERIFICATION_CODE_MAX_SENDS = 5


def _mask_email(email: str) -> str:
    """Simple masking to avoid leaking full candidate email."""
    if not email:
        return ""
    local, sep, domain = email.partition("@")
    masked_local = (local[0] + "***") if len(local) > 1 else "*"
    return masked_local + (sep + domain if domain else "")


@router.get("/session/{token}", response_model=CandidateSessionResolveResponse)
async def resolve_candidate_session(
    token: Annotated[str, Path(..., min_length=20, max_length=255)],
    principal: Annotated[Principal, Depends(require_candidate_principal)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> CandidateSessionResolveResponse:
    """Claim an invite token for the authenticated candidate."""
    cs = await cs_service.claim_invite_with_principal(
        db, token, principal, now=datetime.now(UTC)
    )
    await db.refresh(cs, attribute_names=["simulation"])
    sim = cs.simulation
    return CandidateSessionResolveResponse(
        candidateSessionId=cs.id,
        status=cs.status,
        startedAt=cs.started_at,
        completedAt=cs.completed_at,
        candidateName=cs.candidate_name,
        simulation=CandidateSimulationSummary(
            id=sim.id,
            title=sim.title,
            role=sim.role,
        ),
    )


@router.post(
    "/session/{token}/verification/code/send",
    response_model=CandidateVerificationSendResponse,
    status_code=status.HTTP_200_OK,
)
async def send_verification_code(
    token: Annotated[str, Path(..., min_length=20, max_length=255)],
    db: Annotated[AsyncSession, Depends(get_session)],
    email_service: Annotated[EmailService, Depends(get_email_service)],
):
    """Send a verification code email for a candidate invite token."""
    now = datetime.now(UTC)
    cs = await cs_service.fetch_by_token(db, token, now=now)
    await db.refresh(cs, attribute_names=["simulation"])
    sent_at = getattr(cs, "verification_code_sent_at", None)
    if sent_at is not None:
        sent_at = sent_at.replace(tzinfo=UTC) if sent_at.tzinfo is None else sent_at
        delta = (now - sent_at).total_seconds()
        if delta < VERIFICATION_CODE_COOLDOWN_SECONDS:
            retry_after = int(VERIFICATION_CODE_COOLDOWN_SECONDS - delta)
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "otp_cooldown",
                    "retryAfterSeconds": retry_after,
                },
            )
    send_count = int(getattr(cs, "verification_code_send_count", 0) or 0)
    if send_count >= VERIFICATION_CODE_MAX_SENDS:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"error": "otp_send_limit"},
        )
    result = await notification_service.send_verification_email(
        db,
        candidate_session=cs,
        invite_url=sim_service.invite_url(cs.token),
        email_service=email_service,
        now=now,
    )
    status_value = getattr(cs, "verification_email_status", None) or result.status
    expires_at = getattr(cs, "verification_code_expires_at", None)
    return CandidateVerificationSendResponse(
        status=status_value,
        maskedEmail=_mask_email(cs.invite_email),
        expiresAt=expires_at,
    )


@router.post(
    "/session/{token}/verification/code/confirm",
    response_model=CandidateVerificationConfirmResponse,
    status_code=status.HTTP_200_OK,
)
async def confirm_verification_code(
    token: Annotated[str, Path(..., min_length=20, max_length=255)],
    payload: CandidateVerificationConfirmRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
):
    """Confirm a previously sent verification code."""
    code = payload.code.strip()
    email = payload.email.strip().lower()
    if len(code) != 6 or not code.isdigit():
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "invalid_otp"},
        )

    now = datetime.now(UTC)
    response_status = status.HTTP_200_OK
    response_payload: dict[str, object] | None = None
    access_token: str | None = None
    access_expires_at = None

    async with db.begin_nested():
        cs = await cs_service.fetch_by_token_for_update(db, token, now=now)
        attempts = int(getattr(cs, "verification_code_attempts", 0) or 0)
        if attempts >= MAX_VERIFICATION_CODE_ATTEMPTS:
            cs.verification_code = None
            cs.verification_code_expires_at = None
            response_status = status.HTTP_429_TOO_MANY_REQUESTS
            response_payload = {"error": "otp_locked"}
        elif email != (cs.invite_email or "").strip().lower():
            response_status = status.HTTP_400_BAD_REQUEST
            response_payload = {"error": "email_mismatch"}
        else:
            expires_at = getattr(cs, "verification_code_expires_at", None)
            if (
                expires_at is None
                or (
                    expires_at.replace(tzinfo=UTC)
                    if expires_at.tzinfo is None
                    else expires_at
                )
                < now
            ):
                response_status = status.HTTP_410_GONE
                response_payload = {"error": "otp_expired"}
            elif getattr(cs, "verification_code", None) != code:
                attempts += 1
                cs.verification_code_attempts = attempts
                if attempts >= MAX_VERIFICATION_CODE_ATTEMPTS:
                    cs.verification_code = None
                    cs.verification_code_expires_at = None
                    response_status = status.HTTP_429_TOO_MANY_REQUESTS
                    response_payload = {"error": "otp_locked"}
                else:
                    response_status = status.HTTP_400_BAD_REQUEST
                    response_payload = {"error": "invalid_otp"}
            else:
                cs.invite_email_verified_at = now
                cs.verification_code = None
                cs.verification_code_attempts = 0
                cs.verification_code_sent_at = None
                cs.verification_code_expires_at = None
                (
                    access_token,
                    token_hash,
                    access_expires_at,
                    issued_at,
                ) = mint_candidate_token(
                    candidate_session_id=cs.id,
                    invite_email=cs.invite_email,
                    now=now,
                )
                cs.candidate_access_token_hash = token_hash
                cs.candidate_access_token_expires_at = access_expires_at
                cs.candidate_access_token_issued_at = issued_at

    await db.commit()
    if response_payload is not None:
        return JSONResponse(status_code=response_status, content=response_payload)
    await db.refresh(cs)

    return CandidateVerificationConfirmResponse(
        verified=True,
        candidateAccessToken=access_token or "",
        expiresAt=access_expires_at,
    )


@router.post(
    "/session/{token}/claim",
    response_model=CandidateSessionResolveResponse,
    status_code=status.HTTP_200_OK,
)
@router.post(
    "/session/{token}/verify",
    response_model=CandidateSessionResolveResponse,
    status_code=status.HTTP_200_OK,
)
async def claim_candidate_session(
    token: Annotated[str, Path(..., min_length=20, max_length=255)],
    db: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(require_candidate_principal)],
) -> CandidateSessionResolveResponse:
    """Idempotent claim endpoint for authenticated candidates (no email body required)."""
    now = datetime.now(UTC)
    cs = await cs_service.claim_invite_with_principal(db, token, principal, now=now)
    await db.refresh(cs, attribute_names=["simulation"])

    sim = cs.simulation
    return CandidateSessionResolveResponse(
        candidateSessionId=cs.id,
        status=cs.status,
        startedAt=cs.started_at,
        completedAt=cs.completed_at,
        candidateName=cs.candidate_name,
        simulation=CandidateSimulationSummary(
            id=sim.id,
            title=sim.title,
            role=sim.role,
        ),
    )


@router.get(
    "/session/{candidate_session_id}/current_task",
    response_model=CurrentTaskResponse,
)
async def get_current_task(
    candidate_session_id: int,
    principal: Annotated[Principal, Depends(require_candidate_principal)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> CurrentTaskResponse:
    """Return the current task for a candidate session.

    The current task is defined as the lowest day_index task
    that does not yet have a submission from this candidate.
    """
    now = datetime.now(UTC)
    cs = await cs_service.fetch_owned_session(
        db, candidate_session_id, principal, now=now
    )
    (
        tasks,
        completed_task_ids,
        current_task,
        completed,
        total,
        is_complete,
    ) = await cs_service.progress_snapshot(db, cs)

    if is_complete and cs.status != "completed":
        cs.status = "completed"
        if cs.completed_at is None:
            cs.completed_at = now
        await db.commit()
        await db.refresh(cs)

    return CurrentTaskResponse(
        candidateSessionId=cs.id,
        status=cs.status,
        currentDayIndex=None if is_complete else current_task.day_index,
        currentTask=(
            None
            if is_complete
            else TaskPublic(
                id=current_task.id,
                dayIndex=current_task.day_index,
                title=current_task.title,
                type=current_task.type,
                description=current_task.description,
            )
        ),
        completedTaskIds=sorted(completed_task_ids),
        progress=ProgressSummary(completed=completed, total=total),
        isComplete=is_complete,
    )


@router.get("/invites", response_model=list[CandidateInviteListItem])
async def list_candidate_invites(
    principal: Annotated[Principal, Depends(require_candidate_principal)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> list[CandidateInviteListItem]:
    """List all invites for the authenticated candidate email."""
    return await cs_service.invite_list_for_principal(db, principal)
