from __future__ import annotations

import builtins
import importlib
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from types import SimpleNamespace

from fastapi.security import HTTPAuthorizationCredentials

from app.api import main as api_main
from app.integrations.github.actions_runner.integrations_github_actions_runner_github_actions_runner_legacy_cache_service import (
    LegacyCacheMixin,
)
from app.integrations.github.actions_runner.integrations_github_actions_runner_github_actions_runner_legacy_results_service import (
    LegacyResultMixin,
)
from app.integrations.github.actions_runner.integrations_github_actions_runner_github_actions_runner_model import (
    ActionsRunResult,
)
from app.integrations.github.client import (
    integrations_github_client_github_client_compat_client as compat,
)
from app.integrations.github.client import (
    integrations_github_client_github_client_transport_client as transport,
)
from app.shared.auth.principal import (
    shared_auth_principal_dev_principal_utils as dev_principal,
)
from app.shared.auth.rate_limit.shared_auth_rate_limit_limiter_utils import RateLimiter
from app.shared.http import (
    shared_http_middleware_http_setup_middleware as middleware_http,
)
from app.shared.http import shared_http_middleware_perf_middleware as middleware_perf
from app.shared.http.errors import shared_http_errors_handlers_utils as error_utils
from app.shared.perf import shared_perf_sqlalchemy_hooks_utils as sqlalchemy_hooks
from app.submissions.presentation.submissions_presentation_submissions_parsed_output_utils import (
    process_parsed_output,
)
from app.submissions.presentation.submissions_presentation_submissions_test_results_runinfo_utils import (
    enrich_run_info,
)
from app.submissions.routes import (
    submissions_routes_submissions_helpers_routes as submissions_helpers,
)
from app.submissions.routes.submissions_routes import detail as submissions_detail_route
from app.submissions.routes.submissions_routes import list as submissions_list_route
from app.submissions.services import (
    submissions_services_submissions_rate_limits_constants as rate_limits,
)
from app.submissions.services.use_cases import (
    submissions_services_use_cases_submissions_use_cases_submit_task_runner_service as submit_task_runner,
)
from app.tasks.routes.tasks import (
    tasks_routes_tasks_tasks_runtime_utils as task_helpers,
)
from app.trials.routes.trials_routes import create as sim_create_route
from app.trials.routes.trials_routes import detail as sim_detail_route
from app.trials.routes.trials_routes import (
    list_trials as sim_list_route,
)
from app.trials.services import task_templates
from app.trials.services import (
    trials_services_trials_invite_factory_service as invite_factory,
)

app = api_main.app

__all__ = [name for name in globals() if not name.startswith("__")]
