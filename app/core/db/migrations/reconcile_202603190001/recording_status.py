"""Helpers for recording_assets status check constraints."""

from __future__ import annotations

import sqlalchemy as sa

from .constants import RECORDING_STATUS_CHECK_EXPR, RECORDING_STATUS_CHECK_NAME
from .introspection import check_names


def reconcile_recording_status_check(op: object, bind: sa.Connection) -> None:
    """Execute reconcile recording status check."""
    if bind.dialect.name != "postgresql":
        return
    names = check_names(bind, "recording_assets")
    if RECORDING_STATUS_CHECK_NAME in names:
        op.drop_constraint(
            RECORDING_STATUS_CHECK_NAME, "recording_assets", type_="check"
        )
    op.create_check_constraint(
        RECORDING_STATUS_CHECK_NAME,
        "recording_assets",
        RECORDING_STATUS_CHECK_EXPR,
    )
