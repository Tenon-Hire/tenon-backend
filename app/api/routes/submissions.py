"""Aggregated recruiter submissions router."""

from fastapi import APIRouter

from app.api.routes.submissions_routes import router as submissions_router
from app.domains.submissions.presenter import (
    build_test_results as _build_test_results,
)
from app.domains.submissions.presenter import (
    parse_diff_summary as _parse_diff_summary,
)
from app.domains.submissions.presenter import (
    redact_text as _redact_text,
)
from app.domains.submissions.presenter import (
    truncate_output as _truncate_output,
)

router = APIRouter()
router.include_router(submissions_router)

__all__ = [
    "router",
    "_build_test_results",
    "_parse_diff_summary",
    "_redact_text",
    "_truncate_output",
]
