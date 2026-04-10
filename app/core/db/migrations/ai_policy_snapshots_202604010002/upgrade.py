"""Backfill frozen AI policy snapshots for legacy scenario versions."""

from __future__ import annotations

from types import SimpleNamespace

import sqlalchemy as sa
from sqlalchemy.engine import Connection

from app.ai import build_ai_policy_snapshot
from app.core.db.migrations.shared_trial_schema_compat import (
    resolve_trial_parent_table_name,
)


def run_upgrade(bind: Connection) -> None:
    """Populate missing scenario-version snapshots from current stored config."""
    parent_table_name = resolve_trial_parent_table_name(bind)
    metadata = sa.MetaData()
    companies = sa.Table(
        "companies",
        metadata,
        sa.Column("id", sa.Integer),
        sa.Column("ai_prompt_overrides_json", sa.JSON),
    )
    trials = sa.Table(
        parent_table_name,
        metadata,
        sa.Column("id", sa.Integer),
        sa.Column("company_id", sa.Integer),
        sa.Column("ai_prompt_overrides_json", sa.JSON),
        sa.Column("ai_notice_version", sa.String),
        sa.Column("ai_notice_text", sa.Text),
        sa.Column("ai_eval_enabled_by_day", sa.JSON),
    )
    scenario_versions = sa.Table(
        "scenario_versions",
        metadata,
        sa.Column("id", sa.Integer),
        sa.Column("trial_id", sa.Integer),
        sa.Column("ai_policy_snapshot_json", sa.JSON),
    )

    rows = bind.execute(
        sa.select(
            scenario_versions.c.id.label("scenario_version_id"),
            trials.c.ai_notice_version,
            trials.c.ai_notice_text,
            trials.c.ai_eval_enabled_by_day,
            trials.c.ai_prompt_overrides_json.label("trial_prompt_overrides_json"),
            companies.c.ai_prompt_overrides_json.label("company_prompt_overrides_json"),
        )
        .select_from(
            scenario_versions.join(
                trials, trials.c.id == scenario_versions.c.trial_id
            ).join(companies, companies.c.id == trials.c.company_id)
        )
        .where(scenario_versions.c.ai_policy_snapshot_json.is_(None))
    ).mappings()

    for row in rows:
        trial = SimpleNamespace(
            ai_notice_version=row["ai_notice_version"],
            ai_notice_text=row["ai_notice_text"],
            ai_eval_enabled_by_day=row["ai_eval_enabled_by_day"],
        )
        snapshot_json = build_ai_policy_snapshot(
            trial=trial,
            company_prompt_overrides_json=row["company_prompt_overrides_json"],
            trial_prompt_overrides_json=row["trial_prompt_overrides_json"],
        )
        bind.execute(
            scenario_versions.update()
            .where(scenario_versions.c.id == row["scenario_version_id"])
            .values(ai_policy_snapshot_json=snapshot_json)
        )
