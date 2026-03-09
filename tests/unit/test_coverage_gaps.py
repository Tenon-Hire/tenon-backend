from __future__ import annotations

import builtins
import importlib
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from fastapi.security import HTTPAuthorizationCredentials

from app.api import error_utils, middleware_http, middleware_perf
from app.api import main as api_main
from app.api.routers import submissions_helpers
from app.api.routers.simulations_routes import (
    create as sim_create_route,
)
from app.api.routers.simulations_routes import (
    detail as sim_detail_route,
)
from app.api.routers.simulations_routes import (
    list_simulations as sim_list_route,
)
from app.api.routers.submissions_routes import (
    detail as submissions_detail_route,
)
from app.api.routers.submissions_routes import (
    list as submissions_list_route,
)
from app.api.routers.tasks import helpers as task_helpers
from app.core.auth.principal import dev_principal
from app.core.auth.rate_limit.limiter import RateLimiter
from app.core.perf import sqlalchemy_hooks
from app.domains.submissions.presenter.parsed_output import process_parsed_output
from app.domains.submissions.presenter.test_results_runinfo import enrich_run_info
from app.integrations.github.actions_runner.legacy_cache import LegacyCacheMixin
from app.integrations.github.actions_runner.legacy_results import LegacyResultMixin
from app.integrations.github.actions_runner.models import ActionsRunResult
from app.integrations.github.client import compat, transport
from app.services.simulations import invite_factory, task_templates
from app.services.submissions import rate_limits
from app.services.submissions.use_cases import submit_task_runner


@pytest.mark.asyncio
async def test_submissions_list_route_handles_unexpected_rows(monkeypatch):
    async def _fake_list(*_a, **_k):
        return [object(), ("sub", "task"), ("sub", None), ("sub", "task", "extra")]

    monkeypatch.setattr(submissions_list_route, "ensure_recruiter", lambda _u: None)
    monkeypatch.setattr(
        submissions_list_route.recruiter_sub_service,
        "list_submissions",
        _fake_list,
    )
    monkeypatch.setattr(
        submissions_list_route,
        "present_list_item",
        lambda _sub, _task: {
            "submissionId": 1,
            "candidateSessionId": 2,
            "taskId": 3,
            "dayIndex": 1,
            "type": "code",
            "submittedAt": datetime.now(UTC),
        },
    )
    result = await submissions_list_route.list_submissions_route(
        db=object(),
        user=SimpleNamespace(id=7),
    )
    assert len(result.items) == 2


@pytest.mark.asyncio
async def test_submissions_detail_route_maps_service_payload(monkeypatch):
    async def _fake_fetch_detail(*_a, **_k):
        return object(), object(), object(), object()

    monkeypatch.setattr(submissions_detail_route, "ensure_recruiter", lambda _u: None)
    monkeypatch.setattr(
        submissions_detail_route.recruiter_sub_service,
        "fetch_detail",
        _fake_fetch_detail,
    )
    monkeypatch.setattr(
        submissions_detail_route,
        "present_detail",
        lambda *_a, **_k: {
            "submissionId": 1,
            "candidateSessionId": 2,
            "task": {"taskId": 3, "dayIndex": 1, "type": "code"},
            "submittedAt": datetime.now(UTC),
        },
    )
    result = await submissions_detail_route.get_submission_detail_route(
        submission_id=123,
        db=object(),
        user=SimpleNamespace(id=99),
    )
    assert result.submissionId == 1


def test_register_error_handlers_registers_both_types():
    seen = []

    class StubApp:
        def add_exception_handler(self, exc, handler):
            seen.append((exc, handler))

    error_utils.register_error_handlers(StubApp())
    assert len(seen) == 2


def test_api_main_configure_perf_logging_noop_when_disabled(monkeypatch):
    monkeypatch.setattr(api_main, "perf_logging_enabled", lambda: False)

    class StubApp:
        called = False

        def add_middleware(self, _mw):
            self.called = True

    app = StubApp()
    api_main._configure_perf_logging(app)
    assert app.called is False


def test_middleware_http_configure_cors_defaults(monkeypatch):
    monkeypatch.setattr(middleware_http.settings, "cors", None)
    seen = {}

    class StubApp:
        def add_middleware(self, _mw, **kwargs):
            seen.update(kwargs)

    middleware_http.configure_cors(StubApp())
    assert "http://localhost:3000" in seen["allow_origins"]


def test_configure_perf_logging_noop_when_disabled(monkeypatch):
    monkeypatch.setattr(middleware_perf, "perf_logging_enabled", lambda: False)

    class StubApp:
        called = False

        def add_middleware(self, _mw):
            self.called = True

    app = StubApp()
    middleware_perf.configure_perf_logging(app)
    assert app.called is False


@pytest.mark.asyncio
async def test_simulation_routes_execute_service_calls(monkeypatch):
    user = SimpleNamespace(id=42)
    sim = SimpleNamespace(
        id=1,
        title="Sim",
        role="Backend",
        tech_stack="Python",
        seniority="Mid",
        focus="API",
        template_key="python-fastapi",
        scenario_template="default-5day-node-postgres",
        status="ready_for_review",
        generating_at=datetime.now(UTC),
        ready_for_review_at=datetime.now(UTC),
        activated_at=None,
        terminated_at=None,
        created_at=datetime.now(UTC),
    )
    task = SimpleNamespace(id=9, day_index=1, type="code", title="Task")
    scenario_job = SimpleNamespace(id="job-123")
    monkeypatch.setattr(sim_create_route, "ensure_recruiter_or_none", lambda _u: None)
    monkeypatch.setattr(sim_detail_route, "ensure_recruiter_or_none", lambda _u: None)
    monkeypatch.setattr(sim_list_route, "ensure_recruiter_or_none", lambda _u: None)

    async def _create_sim_with_tasks(*_a, **_k):
        return sim, [task], scenario_job

    async def _require_owned(*_a, **_k):
        return sim, [task]

    async def _list_sims(*_a, **_k):
        return [(sim, 2)]

    async def _get_active_scenario(*_a, **_k):
        return SimpleNamespace(id=10, version_index=1, status="ready", locked_at=None)

    monkeypatch.setattr(
        sim_create_route.sim_service,
        "create_simulation_with_tasks",
        _create_sim_with_tasks,
    )
    monkeypatch.setattr(
        sim_detail_route.sim_service,
        "require_owned_simulation_with_tasks",
        _require_owned,
    )
    monkeypatch.setattr(
        sim_detail_route.sim_service,
        "get_active_scenario_version",
        _get_active_scenario,
    )
    monkeypatch.setattr(
        sim_detail_route,
        "render_simulation_detail",
        lambda _sim, _tasks, _active: {
            "id": _sim.id,
            "title": _sim.title,
            "tasks": _tasks,
        },
    )
    monkeypatch.setattr(sim_list_route.sim_service, "list_simulations", _list_sims)

    created = await sim_create_route.create_simulation(
        payload=SimpleNamespace(),
        db=object(),
        user=user,
    )
    detail = await sim_detail_route.get_simulation_detail(
        simulation_id=sim.id,
        db=object(),
        user=user,
    )
    listed = await sim_list_route.list_simulations(db=object(), user=user)
    assert created.id == sim.id
    assert detail["id"] == sim.id
    assert listed[0].numCandidates == 2


@pytest.mark.asyncio
async def test_submissions_helpers_list_skips_rows_without_task(monkeypatch):
    async def _fake_list(*_a, **_k):
        return [object(), ("sub", None), ("sub", "task")]

    monkeypatch.setattr(submissions_helpers, "ensure_recruiter_guard", lambda _u: None)
    monkeypatch.setattr(
        submissions_helpers.recruiter_sub_service, "list_submissions", _fake_list
    )
    monkeypatch.setattr(
        submissions_helpers,
        "present_list_item",
        lambda *_a, **_k: {
            "submissionId": 1,
            "candidateSessionId": 2,
            "taskId": 3,
            "dayIndex": 1,
            "type": "code",
            "submittedAt": datetime.now(UTC),
        },
    )
    result = await submissions_helpers.list_submissions(
        db=object(),
        user=SimpleNamespace(id=7),
    )
    assert len(result.items) == 1


def test_submissions_helpers_guard_falls_back_when_router_import_fails(monkeypatch):
    guard = importlib.import_module("app.api.routers.submissions_helpers_guard")
    calls = {"fallback": 0}
    monkeypatch.setattr(
        guard, "ensure_recruiter", lambda _u: calls.__setitem__("fallback", 1)
    )
    original_import = builtins.__import__

    def _import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "app.api.routers" and "submissions" in fromlist:
            raise ImportError("forced")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", _import)
    guard.ensure_recruiter_guard(SimpleNamespace(id=1))
    assert calls["fallback"] == 1


@pytest.mark.asyncio
async def test_task_helpers_concurrency_guard_uses_rate_limiter(monkeypatch):
    calls = {"entered": 0, "exited": 0}

    @asynccontextmanager
    async def _fake_guard(_key, _limit):
        calls["entered"] += 1
        yield
        calls["exited"] += 1

    monkeypatch.setattr(task_helpers.rate_limit, "rate_limit_enabled", lambda: True)
    monkeypatch.setattr(
        task_helpers.rate_limit.limiter, "concurrency_guard", _fake_guard
    )
    async with task_helpers._concurrency_guard("k", 1):
        pass
    assert calls == {"entered": 1, "exited": 1}


@pytest.mark.asyncio
async def test_task_helpers_compute_current_task(monkeypatch):
    current = object()

    async def _snapshot(*_a, **_k):
        return [], set(), current, 0, 1, False

    monkeypatch.setattr(task_helpers.cs_service, "progress_snapshot", _snapshot)
    assert await task_helpers._compute_current_task(object(), object()) is current


def test_build_dev_principal_rejects_unknown_prefix():
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="admin:user@test")
    assert dev_principal.build_dev_principal(creds) is None


@pytest.mark.asyncio
async def test_rate_limiter_concurrency_guard_keeps_remaining_count():
    limiter = RateLimiter()
    limiter._in_flight["k"] = 1
    async with limiter.concurrency_guard("k", 2):
        assert limiter._in_flight["k"] == 2
    assert limiter._in_flight["k"] == 1


def test_sqlalchemy_hooks_after_execute_handles_missing_stats():
    class EventImpl:
        def __init__(self):
            self.handlers = {}

        def listens_for(self, _target, name):
            def _decorator(fn):
                self.handlers[name] = fn
                return fn

            return _decorator

    event_impl = EventImpl()
    engine = SimpleNamespace(sync_engine=object())
    perf_ctx = SimpleNamespace(get=lambda: None)
    perf_module = SimpleNamespace(perf_logging_enabled=lambda: True)
    sqlalchemy_hooks.register_listeners(
        engine,
        event_impl=event_impl,
        perf_ctx=perf_ctx,
        perf_module=perf_module,
    )
    context = SimpleNamespace()
    event_impl.handlers["before_cursor_execute"](None, None, None, None, context, False)
    event_impl.handlers["after_cursor_execute"](None, None, None, None, context, False)


def test_process_parsed_output_empty_dict_returns_empty_tuple():
    parsed = process_parsed_output({}, include_output=True, max_output_chars=20)
    assert parsed == (None,) * 13


def test_enrich_run_info_handles_non_numeric_run_id():
    sub = SimpleNamespace(
        workflow_run_id="not-a-number",
        workflow_run_status="queued",
        workflow_run_conclusion="timed_out",
        commit_sha="abc",
        last_run_at=datetime.now(UTC),
    )
    run_id, conclusion, timeout, *_ = enrich_run_info(sub, None, None, None)
    assert run_id == "not-a-number"
    assert conclusion == "timed_out"
    assert timeout is True


def test_invite_factory_fallbacks(monkeypatch):
    from app.domains.simulations import service as sim_service

    def marker():
        return "from-service"

    monkeypatch.setattr(sim_service, "create_invite", marker)
    assert invite_factory.resolve_create_invite_callable() is marker

    original_import = builtins.__import__

    def _import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "app.domains.simulations" and "service" in fromlist:
            raise ImportError("forced")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", _import)
    resolved = invite_factory.resolve_create_invite_callable()
    from app.services.simulations.invite_create import create_invite

    assert resolved is create_invite


def test_task_templates_resolver_import_error_uses_catalog(monkeypatch):
    original_import = builtins.__import__

    def _import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "app.domains.simulations" and "service" in fromlist:
            raise ImportError("forced")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", _import)
    resolver = task_templates._resolver()
    assert resolver("python-fastapi")


def test_rate_limits_rules_fall_back_on_import_error(monkeypatch):
    original_import = builtins.__import__

    def _import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "app.api.routers" and "tasks_codespaces" in fromlist:
            raise ImportError("forced")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", _import)
    assert rate_limits._rules() == rate_limits._DEFAULT_RATE_LIMIT_RULES


def test_legacy_cache_and_results_mixins():
    class Holder(LegacyCacheMixin, LegacyResultMixin):
        pass

    cache = SimpleNamespace(
        run_cache={},
        artifact_cache={},
        artifact_list_cache={},
        poll_attempts={},
        max_entries=5,
        cache_run=lambda key, val: cache.run_cache.__setitem__(key, val),
        cache_artifact_result=lambda key,
        parsed,
        error: cache.artifact_cache.__setitem__(key, (parsed, error)),
        cache_artifact_list=lambda key,
        artifacts: cache.artifact_list_cache.__setitem__(key, artifacts),
    )
    holder = Holder()
    holder.cache = cache
    holder._cache_run_result(("repo", 1), "value")
    assert holder._run_cache[("repo", 1)] == "value"
    holder._cache_artifact_result("k", {"ok": True}, None)
    assert holder._artifact_cache["k"][0]["ok"] is True
    holder._cache_artifact_list("k", [1])
    assert holder._artifact_list_cache["k"] == [1]
    _ = holder._poll_attempts
    holder._max_cache_entries = 99
    assert holder._max_cache_entries == 99
    assert holder._run_cache_key("owner/repo", 55) == ("owner/repo", 55)


@pytest.mark.asyncio
async def test_compat_operations_put_json_and_get_bytes(monkeypatch):
    class Ops(compat.CompatOperations):
        def __init__(self):
            self.transport = object()

    calls = {"request": [], "bytes": []}

    async def _request_json(_transport, method, path, **kwargs):
        calls["request"].append((method, path, kwargs))
        return {"ok": True}

    async def _get_bytes(_transport, path, params=None):
        calls["bytes"].append((path, params))
        return b"content"

    monkeypatch.setattr(compat, "request_json", _request_json)
    monkeypatch.setattr(compat, "get_bytes", _get_bytes)
    ops = Ops()
    await ops._put_json("/x", json={"a": 1})
    payload = await ops._get_bytes("/y", params={"q": "1"})
    assert calls["request"][0][0] == "PUT"
    assert calls["bytes"][0][0] == "/y"
    assert payload == b"content"


@pytest.mark.asyncio
async def test_github_transport_aclose_resets_client():
    gh_transport = transport.GithubTransport(
        base_url="https://api.github.com", token="t"
    )
    _ = gh_transport.client()
    assert gh_transport._client is not None
    await gh_transport.aclose()
    assert gh_transport._client is None


@pytest.mark.asyncio
async def test_run_code_submission_returns_without_diff_when_head_sha_missing(
    monkeypatch,
):
    workspace = SimpleNamespace(repo_full_name="owner/repo")
    result = ActionsRunResult(
        status="passed",
        run_id=1,
        conclusion="success",
        passed=1,
        failed=0,
        total=1,
        stdout="",
        stderr="",
        head_sha=None,
        html_url=None,
    )

    async def _fetch_workspace(*_a, **_k):
        return workspace, "main"

    async def _run_actions_tests(*_a, **_k):
        return result

    async def _record(*_a, **_k):
        return None

    monkeypatch.setattr(
        submit_task_runner, "fetch_workspace_and_branch", _fetch_workspace
    )
    monkeypatch.setattr(
        submit_task_runner.submission_service, "run_actions_tests", _run_actions_tests
    )
    monkeypatch.setattr(
        submit_task_runner.submission_service, "record_run_result", _record
    )

    (
        actions_result,
        diff_summary,
        used_workspace,
    ) = await submit_task_runner.run_code_submission(
        db=object(),
        candidate_session_id=1,
        task_id=2,
        payload=SimpleNamespace(workflowInputs=None, branch="main"),
        github_client=object(),
        actions_runner=object(),
    )
    assert actions_result is result
    assert diff_summary is None
    assert used_workspace is workspace
