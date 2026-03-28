from __future__ import annotations

from tests.shared.utils.shared_candidate_submissions_branch_gaps_utils import *


def test_rate_limit_rules_fallback_when_override_is_not_dict(monkeypatch):
    from app.shared.http.routes import tasks_codespaces

    monkeypatch.setattr(tasks_codespaces, "_RATE_LIMIT_RULE", "invalid", raising=False)
    resolved = rate_limits._rules()
    assert resolved == rate_limits._DEFAULT_RATE_LIMIT_RULES
