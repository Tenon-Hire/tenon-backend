from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.config.config_storage_media_config import StorageMediaSettings


def test_storage_media_settings_validates_signed_url_expiry_upper_bound():
    with pytest.raises(ValidationError):
        StorageMediaSettings(SIGNED_URL_EXPIRY_SECONDS=1801)


def test_storage_media_settings_validates_media_retention_days():
    with pytest.raises(ValidationError):
        StorageMediaSettings(MEDIA_RETENTION_DAYS=0)


def test_storage_media_settings_default_media_retention_days():
    assert StorageMediaSettings().MEDIA_RETENTION_DAYS == 45


def test_storage_media_settings_allows_media_retention_days_override():
    assert StorageMediaSettings(MEDIA_RETENTION_DAYS=7).MEDIA_RETENTION_DAYS == 7


def test_storage_media_settings_validates_signed_url_expiry_positive():
    with pytest.raises(ValidationError):
        StorageMediaSettings(SIGNED_URL_EXPIRY_SECONDS=0)


def test_storage_media_settings_validates_signed_url_min_positive():
    with pytest.raises(ValidationError):
        StorageMediaSettings(MEDIA_SIGNED_URL_MIN_SECONDS=0)


def test_storage_media_settings_validates_signed_url_max_positive():
    with pytest.raises(ValidationError):
        StorageMediaSettings(MEDIA_SIGNED_URL_MAX_SECONDS=0)


def test_storage_media_settings_validates_signed_url_max_upper_bound():
    with pytest.raises(ValidationError):
        StorageMediaSettings(MEDIA_SIGNED_URL_MAX_SECONDS=1801)


def test_storage_media_settings_validates_signed_url_min_not_above_max():
    with pytest.raises(ValidationError):
        StorageMediaSettings(
            MEDIA_SIGNED_URL_MIN_SECONDS=601,
            MEDIA_SIGNED_URL_MAX_SECONDS=600,
        )


def test_storage_media_settings_rejects_non_string_or_list_extensions():
    with pytest.raises(ValidationError):
        StorageMediaSettings(MEDIA_ALLOWED_EXTENSIONS=123)


def test_storage_media_settings_defaults_only_allow_mp4():
    settings = StorageMediaSettings()
    assert ["video/mp4"] == settings.MEDIA_ALLOWED_CONTENT_TYPES
    assert ["mp4"] == settings.MEDIA_ALLOWED_EXTENSIONS
