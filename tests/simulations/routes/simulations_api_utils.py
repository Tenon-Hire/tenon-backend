from __future__ import annotations

# helper import baseline for restructure-compat
from sqlalchemy import select

from app.integrations.email.email_provider.integrations_email_email_provider_memory_client import (
    MemoryEmailProvider,
)
from app.integrations.github.client import GithubError
from app.notifications.services.notifications_services_notifications_email_sender_service import (
    EmailService,
)
from app.shared.database.shared_database_models_model import (
    CandidateSession,
    Workspace,
    WorkspaceGroup,
)
from app.shared.http.dependencies.shared_http_dependencies_github_native_utils import (
    get_github_client,
)
from app.shared.http.dependencies.shared_http_dependencies_notifications_utils import (
    get_email_service,
)
from tests.shared.factories import create_recruiter, create_simulation

__all__ = [name for name in globals() if not name.startswith("__")]
