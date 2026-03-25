from __future__ import annotations

import pytest

from tests.candidates.routes.candidates_submissions_routes_utils import *


def test_rate_limit_or_429_enforces_in_prod(monkeypatch):
    monkeypatch.setattr(candidate_submissions.settings, "ENV", "prod")
    monkeypatch.setattr(
        candidate_submissions,
        "_RATE_LIMIT_RULE",
        {
            "init": candidate_submissions.rate_limit.RateLimitRule(
                limit=1, window_seconds=999.0
            )
        },
    )
    candidate_submissions.rate_limit.limiter.reset()
    candidate_submissions._rate_limit_or_429(1, "init")
    with pytest.raises(HTTPException):
        candidate_submissions._rate_limit_or_429(1, "init")
