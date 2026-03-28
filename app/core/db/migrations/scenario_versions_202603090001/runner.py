"""Upgrade/downgrade runner for revision 202603090001."""

from __future__ import annotations

from .backfill import run_backfill
from .schema_ops import create_schema, finalize_upgrade, run_downgrade_schema


def run_upgrade(op: object) -> None:
    """Run upgrade."""
    create_schema(op)
    run_backfill(op.get_bind())
    finalize_upgrade(op)


def run_downgrade(op: object) -> None:
    """Run downgrade."""
    run_downgrade_schema(op)
