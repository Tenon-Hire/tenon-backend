from __future__ import annotations

import json
from types import SimpleNamespace

from app.integrations.github.client import GithubError
from app.shared.utils.shared_utils_errors_utils import ApiError
from app.submissions.repositories.precommit_bundles import repository as precommit_repo
from app.submissions.repositories.precommit_bundles.submissions_repositories_precommit_bundles_submissions_precommit_bundles_core_model import (
    PRECOMMIT_BUNDLE_STATUS_READY,
)
from app.submissions.services import (
    submissions_services_submissions_workspace_precommit_bundle_service as precommit_service,
)
from app.submissions.services.submissions_services_submissions_workspace_precommit_bundle_service import (
    apply_precommit_bundle_if_available,
    build_precommit_commit_marker,
)
from tests.shared.factories import (
    create_candidate_session,
    create_talent_partner,
    create_trial,
)
from tests.submissions.services.precommit_bundle_runtime.submissions_precommit_bundle_runtime_branch_failure_github_utils import (
    _BranchFailureGithub,
)
from tests.submissions.services.precommit_bundle_runtime.submissions_precommit_bundle_runtime_stub_github_client_utils import (
    StubGithubClient,
)

__all__ = [name for name in globals() if not name.startswith("__")]
