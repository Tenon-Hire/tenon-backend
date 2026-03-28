"""Application module for auth principal bearer utils workflows."""

from __future__ import annotations

from fastapi.security import HTTPBearer

bearer_scheme = HTTPBearer(auto_error=False)
