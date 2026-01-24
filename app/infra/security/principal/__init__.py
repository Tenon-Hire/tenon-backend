from __future__ import annotations

from .bearer import bearer_scheme
from .builder import build_principal
from .checks import require_permissions
from .dependencies import get_principal
from .identity import extract_identity
from .model import Principal
from .permissions import build_permissions
from .selectors import first_claim, normalize_email

__all__ = [
    "Principal",
    "bearer_scheme",
    "build_permissions",
    "build_principal",
    "extract_identity",
    "get_principal",
    "first_claim",
    "normalize_email",
    "require_permissions",
]
