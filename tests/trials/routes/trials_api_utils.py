from __future__ import annotations

# helper import baseline for restructure-compat
from sqlalchemy import select

from app.ai import build_ai_policy_snapshot
from app.integrations.email.email_provider.integrations_email_email_provider_memory_client import (
    MemoryEmailProvider,
)
from app.integrations.github.client import GithubError
from app.notifications.services.notifications_services_notifications_email_sender_service import (
    EmailService,
)
from app.shared.database.shared_database_models_model import (
    CandidateSession,
    ScenarioVersion,
    Workspace,
    WorkspaceGroup,
)
from app.shared.http.dependencies.shared_http_dependencies_github_native_utils import (
    get_github_client,
)
from app.shared.http.dependencies.shared_http_dependencies_notifications_utils import (
    get_email_service,
)
from app.trials.services.trials_services_trials_codespace_specializer_service import (
    ensure_precommit_bundle_prepared_for_approved_scenario,
)
from tests.shared.factories import create_talent_partner
from tests.shared.factories import create_trial as _create_trial


async def create_trial(*args, **kwargs):
    session = args[0]
    sim, tasks = await _create_trial(*args, **kwargs)
    scenario_version = await session.get(
        ScenarioVersion, sim.active_scenario_version_id
    )
    if scenario_version is not None:
        scenario_version.ai_policy_snapshot_json = build_ai_policy_snapshot(trial=sim)
        await ensure_precommit_bundle_prepared_for_approved_scenario(
            session,
            trial=sim,
            scenario_version=scenario_version,
            tasks=tasks,
        )
        await session.flush()
    return sim, tasks


__all__ = [name for name in globals() if not name.startswith("__")]
