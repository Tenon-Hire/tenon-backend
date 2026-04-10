from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from app.evaluations.services import (
    evaluations_services_evaluations_runs_service as evaluation_runs,
)
from app.evaluations.services import (
    evaluations_services_evaluations_winoe_report_composer_service as winoe_report_composer,
)
from app.integrations.email.email_provider.integrations_email_email_provider_base_client import (
    EmailSendError,
)
from app.media.services import media_services_media_keys_service as media_keys
from app.media.services import media_services_media_privacy_service as media_privacy
from app.notifications.services.notifications_services_notifications_email_sender_service import (
    EmailSender,
)
from app.trials.services import (
    trials_services_trials_candidates_compare_formatting_service as candidates_compare,
)
from app.trials.services import (
    trials_services_trials_invite_factory_service as invite_factory,
)
from app.trials.services import (
    trials_services_trials_scenario_payload_builder_service as scenario_payload_builder,
)
from app.trials.services import (
    trials_services_trials_update_service as trials_update,
)

if not hasattr(candidates_compare, "_display_name"):  # compat for older test helpers
    candidates_compare._display_name = candidates_compare.display_name


class _DummyDB:
    def __init__(self):
        self.commits = 0
        self.refreshes = 0
        self.flushes = 0
        self.rollbacks = 0

    async def commit(self):
        self.commits += 1

    async def refresh(self, _obj):
        self.refreshes += 1

    async def flush(self):
        self.flushes += 1

    async def rollback(self):
        self.rollbacks += 1


__all__ = [name for name in globals() if not name.startswith("__")]
