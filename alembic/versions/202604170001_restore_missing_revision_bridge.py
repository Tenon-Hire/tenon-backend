"""Restore the missing local revision bridge for Alembic upgrade flow.

This no-op migration keeps local databases stamped to the historical
202604170001 revision upgradeable from the repo's current revision chain.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op  # noqa: F401
import sqlalchemy as sa  # noqa: F401


# revision identifiers, used by Alembic.
revision: str = "202604170001"
down_revision: str | Sequence[str] | None = "202604160001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """No-op bridge migration."""
    pass


def downgrade() -> None:
    """No-op bridge migration."""
    pass
