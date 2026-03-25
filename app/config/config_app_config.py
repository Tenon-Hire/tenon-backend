from __future__ import annotations

from .config_settings_fields_config import SettingsFields
from .config_settings_shims_config import SettingsShimMixin
from .config_settings_validators_config import SettingsValidationMixin


class Settings(SettingsValidationMixin, SettingsShimMixin, SettingsFields):
    """Application settings loaded from environment variables and `.env`."""
