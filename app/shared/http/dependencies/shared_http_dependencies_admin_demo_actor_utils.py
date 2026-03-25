from __future__ import annotations

from dataclasses import dataclass

from app.shared.auth.principal import Principal


@dataclass(frozen=True, slots=True)
class DemoAdminActor:
    principal: Principal
    actor_type: str
    actor_id: str
    recruiter_id: int | None
