"""Application module for http middleware http request middleware workflows."""

from __future__ import annotations

from urllib.parse import urlsplit


def _headers_map(raw_headers) -> dict[str, str]:
    headers: dict[str, str] = {}
    for key, value in raw_headers or []:
        decoded_key = key.decode("latin1").lower()
        if decoded_key not in headers:
            headers[decoded_key] = value.decode("latin1")
    return headers


def _normalize_origin(value: str | None) -> str | None:
    raw = (value or "").strip()
    if not raw:
        return None
    try:
        parsed = urlsplit(raw)
    except ValueError:
        return None
    scheme = (parsed.scheme or "").strip().lower()
    host = (parsed.hostname or "").strip().lower()
    if (
        scheme not in {"http", "https"}
        or not host
        or parsed.username
        or parsed.password
    ):
        return None
    try:
        port = parsed.port
    except ValueError:
        return None
    default_port = 80 if scheme == "http" else 443
    host_display = f"[{host}]" if ":" in host else host
    return (
        f"{scheme}://{host_display}"
        if port in (None, default_port)
        else f"{scheme}://{host_display}:{port}"
    )


def _is_cookie_authenticated_request(headers: dict[str, str]) -> bool:
    return bool((headers.get("cookie") or "").strip())


def _path_matches_prefixes(path: str, prefixes: list[str]) -> bool:
    normalized_path = path or "/"
    for prefix in prefixes:
        if (
            prefix == "/"
            or normalized_path == prefix
            or normalized_path.startswith(f"{prefix}/")
        ):
            return True
    return False
