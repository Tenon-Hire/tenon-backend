from __future__ import annotations

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.settings.parsers import parse_env_list

DEFAULT_MEDIA_ALLOWED_CONTENT_TYPES = ["video/mp4", "video/webm", "video/quicktime"]
DEFAULT_MEDIA_ALLOWED_EXTENSIONS = ["mp4", "webm", "mov"]


class StorageMediaSettings(BaseSettings):
    """Object storage and signed URL configuration for media assets."""

    MEDIA_STORAGE_PROVIDER: str = "fake"

    MEDIA_S3_ENDPOINT: str = ""
    MEDIA_S3_REGION: str = "us-east-1"
    MEDIA_S3_BUCKET: str = ""
    MEDIA_S3_ACCESS_KEY_ID: str = ""
    MEDIA_S3_SECRET_ACCESS_KEY: str = ""
    MEDIA_S3_SESSION_TOKEN: str = ""
    MEDIA_S3_USE_PATH_STYLE: bool = True

    SIGNED_URL_EXPIRY_SECONDS: int = 900
    MEDIA_SIGNED_URL_EXPIRES_SECONDS: int | None = None
    MEDIA_SIGNED_URL_MIN_SECONDS: int = 60
    MEDIA_SIGNED_URL_MAX_SECONDS: int = 1800

    MEDIA_RETENTION_DAYS: int = 45
    MEDIA_DELETE_ENABLED: bool = True

    MEDIA_MAX_UPLOAD_BYTES: int = 100 * 1024 * 1024
    MEDIA_ALLOWED_CONTENT_TYPES: list[str] | str = DEFAULT_MEDIA_ALLOWED_CONTENT_TYPES
    MEDIA_ALLOWED_EXTENSIONS: list[str] | str = DEFAULT_MEDIA_ALLOWED_EXTENSIONS

    model_config = SettingsConfigDict(extra="ignore", env_prefix="")

    @field_validator("MEDIA_ALLOWED_CONTENT_TYPES", mode="before")
    @classmethod
    def _coerce_content_types(cls, value):
        return parse_env_list(value)

    @field_validator("MEDIA_ALLOWED_EXTENSIONS", mode="before")
    @classmethod
    def _coerce_extensions(cls, value):
        parsed = parse_env_list(value)
        if isinstance(parsed, list):
            return [str(item).lower().lstrip(".") for item in parsed]
        return parsed

    @model_validator(mode="after")
    def _validate_privacy_controls(self):
        if self.MEDIA_SIGNED_URL_EXPIRES_SECONDS is not None:
            self.SIGNED_URL_EXPIRY_SECONDS = int(self.MEDIA_SIGNED_URL_EXPIRES_SECONDS)
        self.MEDIA_SIGNED_URL_EXPIRES_SECONDS = self.SIGNED_URL_EXPIRY_SECONDS

        if self.SIGNED_URL_EXPIRY_SECONDS <= 0:
            raise ValueError("SIGNED_URL_EXPIRY_SECONDS must be > 0")
        if self.SIGNED_URL_EXPIRY_SECONDS > 1800:
            raise ValueError("SIGNED_URL_EXPIRY_SECONDS must be <= 1800")

        if self.MEDIA_RETENTION_DAYS <= 0:
            raise ValueError("MEDIA_RETENTION_DAYS must be > 0")

        if self.MEDIA_SIGNED_URL_MIN_SECONDS <= 0:
            raise ValueError("MEDIA_SIGNED_URL_MIN_SECONDS must be > 0")
        if self.MEDIA_SIGNED_URL_MAX_SECONDS <= 0:
            raise ValueError("MEDIA_SIGNED_URL_MAX_SECONDS must be > 0")
        if self.MEDIA_SIGNED_URL_MAX_SECONDS > 1800:
            raise ValueError("MEDIA_SIGNED_URL_MAX_SECONDS must be <= 1800")
        if self.MEDIA_SIGNED_URL_MIN_SECONDS > self.MEDIA_SIGNED_URL_MAX_SECONDS:
            raise ValueError(
                "MEDIA_SIGNED_URL_MIN_SECONDS must be <= MEDIA_SIGNED_URL_MAX_SECONDS"
            )

        return self
