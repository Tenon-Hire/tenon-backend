"""Aggregated Talent Partner submissions router."""

from fastapi import APIRouter

from app.shared.auth.shared_auth_roles_utils import ensure_talent_partner
from app.submissions.presentation import build_diff_url as _build_diff_url
from app.submissions.presentation import (
    build_test_results as _build_test_results,
)
from app.submissions.presentation import (
    parse_diff_summary as _parse_diff_summary,
)
from app.submissions.presentation import (
    redact_text as _redact_text,
)
from app.submissions.presentation import (
    truncate_output as _truncate_output,
)
from app.submissions.routes.submissions_routes import router as submissions_router
from app.submissions.routes.submissions_routes_submissions_helpers_routes import (
    get_submission_detail,
    list_submissions,
)
from app.submissions.services import (
    service_talent_partner as talent_partner_sub_service,
)

router = APIRouter()
router.include_router(submissions_router)
_derive_test_status = talent_partner_sub_service.derive_test_status


__all__ = [
    "router",
    "_build_test_results",
    "_parse_diff_summary",
    "_build_diff_url",
    "_redact_text",
    "_truncate_output",
    "_derive_test_status",
    "talent_partner_sub_service",
    "ensure_talent_partner",
    "get_submission_detail",
    "list_submissions",
]
