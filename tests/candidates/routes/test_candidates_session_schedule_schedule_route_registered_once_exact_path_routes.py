from __future__ import annotations

from tests.candidates.routes.candidates_session_schedule_api_utils import *


def test_schedule_route_registered_once_exact_path() -> None:
    matches = [
        route
        for route in app.routes
        if getattr(route, "path", None) == "/api/candidate/session/{token}/schedule"
        and "POST" in getattr(route, "methods", set())
    ]
    assert len(matches) == 1
