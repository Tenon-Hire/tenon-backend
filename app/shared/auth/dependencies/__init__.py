from __future__ import annotations

import sys

from app.config import settings
from app.shared.auth.principal import get_principal

from .shared_auth_dependencies_current_user_utils import (
    get_authenticated_user,
    get_current_user,
)
from .shared_auth_dependencies_db_utils import lookup_user as _lookup_user
from .shared_auth_dependencies_dev_bypass_utils import dev_bypass_user
from .shared_auth_dependencies_env_utils import _env_name_base, env_name
from .shared_auth_dependencies_env_utils import env_name as _env_name
from .shared_auth_dependencies_users_utils import user_from_principal

_dev_bypass_user = dev_bypass_user
_user_from_principal = user_from_principal

__all__ = [
    "_env_name",
    "_dev_bypass_user",
    "_env_name_base",
    "_lookup_user",
    "_user_from_principal",
    "get_principal",
    "dev_bypass_user",
    "env_name",
    "get_authenticated_user",
    "get_current_user",
    "settings",
    "sys",
    "user_from_principal",
]
