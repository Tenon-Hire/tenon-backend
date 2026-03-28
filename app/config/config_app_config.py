"""Compose the canonical application settings object from field and mixin layers."""

from __future__ import annotations

from .config_settings_fields_config import SettingsFields
from .config_settings_shims_config import SettingsShimMixin
from .config_settings_validators_config import SettingsValidationMixin


class Settings(SettingsValidationMixin, SettingsShimMixin, SettingsFields):
    """Unified settings model used by runtime code via ``app.config.settings``."""
