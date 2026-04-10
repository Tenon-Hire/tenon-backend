from __future__ import annotations

from datetime import UTC, datetime, time, timedelta
from types import SimpleNamespace

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.shared.database.shared_database_models_model import (
    CandidateSession,
    Job,
    Trial,
)
from app.shared.types.shared_types_types_model import CANDIDATE_SESSION_STATUS_COMPLETED
from app.trials import services as sim_service
from app.trials.services import (
    trials_services_trials_creation_service as sim_creation,
)
from tests.shared.factories import create_talent_partner, create_trial

__all__ = [name for name in globals() if not name.startswith("__")]
