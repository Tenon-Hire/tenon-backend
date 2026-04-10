"""Application module for trials routes trials routes trials routes invite create logic routes workflows."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.github import GithubClient, GithubError
from app.notifications.services.notifications_services_notifications_email_sender_service import (
    EmailService,
)
from app.shared.http.shared_http_error_utils import map_github_error
from app.trials import services as sim_service
from app.trials.routes.trials_routes.trials_routes_trials_routes_trials_routes_invite_render_routes import (
    render_invite_error,
    render_invite_response,
)
from app.trials.routes.trials_routes.trials_routes_trials_routes_trials_routes_rate_limits_routes import (
    enforce_invite_create_limit,
)
from app.trials.services import (
    trials_services_trials_invite_workflow_service as invite_workflow,
)


async def create_invite_response(
    db: AsyncSession,
    *,
    trial_id: int,
    payload,
    user_id: int,
    request,
    email_service: EmailService,
    github_client: GithubClient,
):
    """Create invite response."""
    enforce_invite_create_limit(request, user_id, payload.inviteEmail)
    try:
        (
            cs,
            sim,
            outcome,
            invite_url,
        ) = await invite_workflow.create_candidate_invite_workflow(
            db,
            trial_id=trial_id,
            payload=payload,
            user_id=user_id,
            email_service=email_service,
            github_client=github_client,
        )
    except sim_service.InviteRejectedError as exc:
        return render_invite_error(exc)
    except GithubError as exc:
        raise map_github_error(exc) from exc

    return render_invite_response(cs, invite_url, outcome)
