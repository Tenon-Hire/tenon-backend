from __future__ import annotations

from .shared_auth_principal_bearer_utils import bearer_scheme
from .shared_auth_principal_builder_utils import build_principal
from .shared_auth_principal_checks_utils import require_permissions
from .shared_auth_principal_dependencies_utils import get_principal
from .shared_auth_principal_identity_utils import extract_identity
from .shared_auth_principal_model import Principal
from .shared_auth_principal_permissions_utils import build_permissions
from .shared_auth_principal_selectors_utils import first_claim, normalize_email

_extract_principal = build_principal

__all__ = [
    "Principal",
    "bearer_scheme",
    "build_permissions",
    "build_principal",
    "_extract_principal",
    "extract_identity",
    "get_principal",
    "first_claim",
    "normalize_email",
    "require_permissions",
]
