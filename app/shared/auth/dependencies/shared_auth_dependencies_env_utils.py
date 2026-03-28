"""Application module for auth dependencies env utils workflows."""

from __future__ import annotations

from app.shared.utils.shared_utils_env_utils import env_name as _env_name_base

from .shared_auth_dependencies_modules_utils import current_user_module


def env_name() -> str:
    """Env name with monkeypatch-friendly override via current_user._env_name."""
    current_user_mod = current_user_module()
    override = getattr(current_user_mod, "_env_name", None)
    if callable(override) and override is not env_name:
        return override()
    return _env_name_base()
