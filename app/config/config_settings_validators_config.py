"""Application module for config settings validators config workflows."""

from __future__ import annotations

from pydantic import field_validator, model_validator

from .config_merge_config import merge_nested_settings
from .config_parsers_config import parse_env_list


class SettingsValidationMixin:
    """Represent settings validation mixin data and behavior."""

    @field_validator("TRUSTED_PROXY_CIDRS", mode="before")
    @classmethod
    def _coerce_trusted_proxy_cidrs(cls, value):
        return parse_env_list(value)

    @field_validator(
        "DEMO_ADMIN_ALLOWLIST_EMAILS", "DEMO_ADMIN_ALLOWLIST_SUBJECTS", mode="before"
    )
    @classmethod
    def _coerce_demo_allowlists(cls, value):
        return parse_env_list(value)

    @field_validator("DEMO_ADMIN_ALLOWLIST_RECRUITER_IDS", mode="before")
    @classmethod
    def _coerce_demo_allowlist_recruiter_ids(cls, value):
        parsed = parse_env_list(value)
        if parsed in (None, "", []):
            return []
        if not isinstance(parsed, list):
            parsed = [parsed]
        normalized: list[int] = []
        for item in parsed:
            if isinstance(item, bool):
                continue
            if isinstance(item, int):
                normalized.append(item)
                continue
            text = str(item).strip()
            if text.isdigit():
                normalized.append(int(text))
        return normalized

    @field_validator(
        "CSRF_ALLOWED_ORIGINS", "CSRF_PROTECTED_PATH_PREFIXES", mode="before"
    )
    @classmethod
    def _coerce_csrf_lists(cls, value):
        return parse_env_list(value)

    @field_validator("PERF_SPAN_SAMPLE_RATE", mode="before")
    @classmethod
    def _coerce_perf_span_sample_rate(cls, value):
        try:
            sampled = float(value)
        except (TypeError, ValueError):
            return 1.0
        return 0.0 if sampled < 0.0 else 1.0 if sampled > 1.0 else sampled

    @model_validator(mode="before")
    @classmethod
    def _merge_legacy(cls, values: dict) -> dict:
        return merge_nested_settings(values)

    @model_validator(mode="after")
    def _fail_fast_auth(self):
        env = str(self.ENV or "").lower()
        if env != "test":
            issuer_val = (self.auth.AUTH0_ISSUER or "").strip()
            domain_val = (self.auth.AUTH0_DOMAIN or "").strip()
            if not issuer_val and not domain_val:
                raise ValueError(
                    "AUTH0_ISSUER (or AUTH0_DOMAIN) must be set for Auth0 validation"
                )
            if not (self.auth.AUTH0_API_AUDIENCE or "").strip():
                raise ValueError("AUTH0_API_AUDIENCE must be set for Auth0 validation")
        return self

    @model_validator(mode="after")
    def _validate_cors_posture(self):
        if str(self.ENV or "").lower() in {"local", "test"}:
            return self
        raw_origins = getattr(self.cors, "CORS_ALLOW_ORIGINS", [])
        if isinstance(raw_origins, str):
            origins = [raw_origins.strip()] if raw_origins.strip() else []
        elif isinstance(raw_origins, list | tuple | set):
            origins = [str(item).strip() for item in raw_origins if str(item).strip()]
        else:
            origins = []
        origin_regex = (self.cors.CORS_ALLOW_ORIGIN_REGEX or "").strip()
        if origin_regex:
            raise ValueError(
                "CORS_ALLOW_ORIGIN_REGEX is not allowed outside local/test; use explicit CORS_ALLOW_ORIGINS"
            )
        if not origins:
            raise ValueError("CORS_ALLOW_ORIGINS must be configured outside local/test")
        if any("*" in origin for origin in origins):
            raise ValueError("Wildcard CORS origins are not allowed outside local/test")
        return self
