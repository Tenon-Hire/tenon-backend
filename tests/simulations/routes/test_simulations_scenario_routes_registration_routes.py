from fastapi.routing import APIRoute

from app.main import app


def test_scenario_routes_are_registered_once():
    expected = [
        ("POST", "/api/simulations/{simulation_id}/scenario/regenerate"),
        (
            "POST",
            "/api/simulations/{simulation_id}/scenario/{scenario_version_id}/approve",
        ),
        ("PATCH", "/api/simulations/{simulation_id}/scenario/active"),
        ("PATCH", "/api/simulations/{simulation_id}/scenario/{scenario_version_id}"),
    ]
    for method, path in expected:
        matches = [
            route
            for route in app.routes
            if isinstance(route, APIRoute)
            and route.path == path
            and method in (route.methods or set())
        ]
        assert len(matches) == 1
