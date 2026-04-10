"""Rename legacy Tenon schema objects to Winoe names.

Revision ID: 202604090001
Revises: 202604010002
Create Date: 2026-04-09 00:01:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "202604090001"
down_revision: str | Sequence[str] | None = "202604010002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _inspector() -> sa.Inspector:
    return sa.inspect(op.get_bind())


def _has_table(name: str) -> bool:
    return name in _inspector().get_table_names()


def _has_column(table_name: str, column_name: str) -> bool:
    return any(
        column["name"] == column_name
        for column in _inspector().get_columns(table_name)
    )


def _index_names(table_name: str) -> set[str]:
    return {
        index["name"]
        for index in _inspector().get_indexes(table_name)
        if index.get("name")
    }


def _unique_names(table_name: str) -> set[str]:
    return {
        unique["name"]
        for unique in _inspector().get_unique_constraints(table_name)
        if unique.get("name")
    }


def _foreign_key_names(table_name: str) -> set[str]:
    return {
        foreign_key["name"]
        for foreign_key in _inspector().get_foreign_keys(table_name)
        if foreign_key.get("name")
    }


def _check_names(table_name: str) -> set[str]:
    return {
        check["name"]
        for check in _inspector().get_check_constraints(table_name)
        if check.get("name")
    }


def _rename_index(old_name: str, new_name: str) -> None:
    op.execute(sa.text(f'ALTER INDEX "{old_name}" RENAME TO "{new_name}"'))


def _rename_constraint(table_name: str, old_name: str, new_name: str) -> None:
    op.execute(
        sa.text(
            f'ALTER TABLE "{table_name}" RENAME CONSTRAINT "{old_name}" TO "{new_name}"'
        )
    )


def _rename_sequence(old_name: str, new_name: str) -> None:
    op.execute(sa.text(f'ALTER SEQUENCE "{old_name}" RENAME TO "{new_name}"'))


def _rename_postgres_table_artifacts(
    old_table: str,
    new_table: str,
    *,
    rename_indexes: dict[str, str] | None = None,
    rename_constraints: dict[str, str] | None = None,
) -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    pk_name = _inspector().get_pk_constraint(new_table).get("name")
    if pk_name == f"{old_table}_pkey":
        _rename_constraint(new_table, f"{old_table}_pkey", f"{new_table}_pkey")

    if rename_indexes:
        existing_indexes = _index_names(new_table)
        for old_name, new_name in rename_indexes.items():
            if old_name in existing_indexes:
                _rename_index(old_name, new_name)

    if rename_constraints:
        existing_uniques = _unique_names(new_table)
        existing_foreign_keys = _foreign_key_names(new_table)
        existing_checks = _check_names(new_table)
        existing_constraints = (
            existing_uniques | existing_foreign_keys | existing_checks | {pk_name}
        )
        for old_name, new_name in rename_constraints.items():
            if old_name in existing_constraints:
                _rename_constraint(new_table, old_name, new_name)

    sequence_old = f"{old_table}_id_seq"
    sequence_new = f"{new_table}_id_seq"
    sequence_query = sa.text(
        """
        SELECT 1
        FROM information_schema.sequences
        WHERE sequence_name = :sequence_name
        """
    )
    if op.get_bind().execute(sequence_query, {"sequence_name": sequence_old}).scalar():
        _rename_sequence(sequence_old, sequence_new)


def _rename_trial_table_and_columns() -> None:
    bind = op.get_bind()

    if _has_table("simulations") and not _has_table("trials"):
        op.rename_table("simulations", "trials")
        _rename_postgres_table_artifacts(
            "simulations",
            "trials",
            rename_indexes={
                "ix_simulations_template_key": "ix_trials_template_key",
            },
            rename_constraints={
                "ck_simulations_status_lifecycle": "ck_trials_status_lifecycle",
                "fk_simulations_pending_scenario_version_id": "fk_trials_pending_scenario_version_id",
            },
        )

    if _has_table("trials") and _has_column(
        "trials", "terminated_by_recruiter_id"
    ) and not _has_column("trials", "terminated_by_talent_partner_id"):
        op.alter_column(
            "trials",
            "terminated_by_recruiter_id",
            new_column_name="terminated_by_talent_partner_id",
            existing_type=sa.Integer(),
        )
        if bind.dialect.name == "postgresql":
            table_name = "trials"
            foreign_keys = _foreign_key_names(table_name)
            if (
                "fk_simulations_terminated_by_recruiter_id_users" in foreign_keys
                or "fk_trials_terminated_by_recruiter_id_users" in foreign_keys
            ):
                old_name = (
                    "fk_simulations_terminated_by_recruiter_id_users"
                    if "fk_simulations_terminated_by_recruiter_id_users"
                    in foreign_keys
                    else "fk_trials_terminated_by_recruiter_id_users"
                )
                _rename_constraint(
                    table_name,
                    old_name,
                    "fk_trials_terminated_by_talent_partner_id_users",
                )

    if _has_table("tasks") and _has_column("tasks", "simulation_id") and not _has_column(
        "tasks", "trial_id"
    ):
        op.alter_column(
            "tasks",
            "simulation_id",
            new_column_name="trial_id",
            existing_type=sa.Integer(),
        )
        if bind.dialect.name == "postgresql":
            indexes = _index_names("tasks")
            if "ix_tasks_simulation_day_index" in indexes:
                _rename_index("ix_tasks_simulation_day_index", "ix_tasks_trial_day_index")

    if _has_table("candidate_sessions") and _has_column(
        "candidate_sessions", "simulation_id"
    ) and not _has_column("candidate_sessions", "trial_id"):
        op.alter_column(
            "candidate_sessions",
            "simulation_id",
            new_column_name="trial_id",
            existing_type=sa.Integer(),
        )
        if bind.dialect.name == "postgresql":
            uniques = _unique_names("candidate_sessions")
            if "uq_candidate_sessions_simulation_invite_email" in uniques:
                _rename_constraint(
                    "candidate_sessions",
                    "uq_candidate_sessions_simulation_invite_email",
                    "uq_candidate_session_trial_invite_email",
                )
            indexes = _index_names("candidate_sessions")
            if "uq_candidate_sessions_simulation_invite_email_ci" in indexes:
                _rename_index(
                    "uq_candidate_sessions_simulation_invite_email_ci",
                    "uq_candidate_sessions_trial_invite_email_ci",
                )


def _rename_winoe_report_schema() -> None:
    if _has_table("fit_profiles") and not _has_table("winoe_reports"):
        op.rename_table("fit_profiles", "winoe_reports")
        _rename_postgres_table_artifacts(
            "fit_profiles",
            "winoe_reports",
            rename_indexes={
                "ix_fit_profiles_candidate_session_id": "ix_winoe_reports_candidate_session_id",
            },
            rename_constraints={
                "uq_fit_profiles_candidate_session_id": "uq_winoe_reports_candidate_session_id",
            },
        )

    if _has_table("evaluation_runs") and _has_column(
        "evaluation_runs", "overall_fit_score"
    ) and not _has_column("evaluation_runs", "overall_winoe_score"):
        op.alter_column(
            "evaluation_runs",
            "overall_fit_score",
            new_column_name="overall_winoe_score",
            existing_type=sa.Float(),
        )


def _rename_talent_partner_schema() -> None:
    bind = op.get_bind()

    if _has_table("scenario_edit_audit") and _has_column(
        "scenario_edit_audit", "recruiter_id"
    ) and not _has_column("scenario_edit_audit", "talent_partner_id"):
        op.alter_column(
            "scenario_edit_audit",
            "recruiter_id",
            new_column_name="talent_partner_id",
            existing_type=sa.Integer(),
        )
        if bind.dialect.name == "postgresql":
            indexes = _index_names("scenario_edit_audit")
            if "ix_scenario_edit_audit_recruiter_created_at" in indexes:
                _rename_index(
                    "ix_scenario_edit_audit_recruiter_created_at",
                    "ix_scenario_edit_audit_talent_partner_created_at",
                )

    op.execute(
        sa.text(
            """
            UPDATE users
            SET role = 'talent_partner'
            WHERE role = 'recruiter'
            """
        )
    )


def upgrade() -> None:
    _rename_trial_table_and_columns()
    _rename_winoe_report_schema()
    _rename_talent_partner_schema()


def downgrade() -> None:
    bind = op.get_bind()

    op.execute(
        sa.text(
            """
            UPDATE users
            SET role = 'recruiter'
            WHERE role = 'talent_partner'
            """
        )
    )

    if _has_table("scenario_edit_audit") and _has_column(
        "scenario_edit_audit", "talent_partner_id"
    ) and not _has_column("scenario_edit_audit", "recruiter_id"):
        if bind.dialect.name == "postgresql":
            indexes = _index_names("scenario_edit_audit")
            if "ix_scenario_edit_audit_talent_partner_created_at" in indexes:
                _rename_index(
                    "ix_scenario_edit_audit_talent_partner_created_at",
                    "ix_scenario_edit_audit_recruiter_created_at",
                )
        op.alter_column(
            "scenario_edit_audit",
            "talent_partner_id",
            new_column_name="recruiter_id",
            existing_type=sa.Integer(),
        )

    if _has_table("evaluation_runs") and _has_column(
        "evaluation_runs", "overall_winoe_score"
    ) and not _has_column("evaluation_runs", "overall_fit_score"):
        op.alter_column(
            "evaluation_runs",
            "overall_winoe_score",
            new_column_name="overall_fit_score",
            existing_type=sa.Float(),
        )

    if _has_table("winoe_reports") and not _has_table("fit_profiles"):
        op.rename_table("winoe_reports", "fit_profiles")
        _rename_postgres_table_artifacts(
            "winoe_reports",
            "fit_profiles",
            rename_indexes={
                "ix_winoe_reports_candidate_session_id": "ix_fit_profiles_candidate_session_id",
            },
            rename_constraints={
                "uq_winoe_reports_candidate_session_id": "uq_fit_profiles_candidate_session_id",
            },
        )

    if _has_table("candidate_sessions") and _has_column(
        "candidate_sessions", "trial_id"
    ) and not _has_column("candidate_sessions", "simulation_id"):
        if bind.dialect.name == "postgresql":
            indexes = _index_names("candidate_sessions")
            if "uq_candidate_sessions_trial_invite_email_ci" in indexes:
                _rename_index(
                    "uq_candidate_sessions_trial_invite_email_ci",
                    "uq_candidate_sessions_simulation_invite_email_ci",
                )
            uniques = _unique_names("candidate_sessions")
            if "uq_candidate_session_trial_invite_email" in uniques:
                _rename_constraint(
                    "candidate_sessions",
                    "uq_candidate_session_trial_invite_email",
                    "uq_candidate_sessions_simulation_invite_email",
                )
        op.alter_column(
            "candidate_sessions",
            "trial_id",
            new_column_name="simulation_id",
            existing_type=sa.Integer(),
        )

    if _has_table("tasks") and _has_column("tasks", "trial_id") and not _has_column(
        "tasks", "simulation_id"
    ):
        if bind.dialect.name == "postgresql":
            indexes = _index_names("tasks")
            if "ix_tasks_trial_day_index" in indexes:
                _rename_index("ix_tasks_trial_day_index", "ix_tasks_simulation_day_index")
        op.alter_column(
            "tasks",
            "trial_id",
            new_column_name="simulation_id",
            existing_type=sa.Integer(),
        )

    if _has_table("trials") and _has_column(
        "trials", "terminated_by_talent_partner_id"
    ) and not _has_column("trials", "terminated_by_recruiter_id"):
        if bind.dialect.name == "postgresql":
            foreign_keys = _foreign_key_names("trials")
            if "fk_trials_terminated_by_talent_partner_id_users" in foreign_keys:
                _rename_constraint(
                    "trials",
                    "fk_trials_terminated_by_talent_partner_id_users",
                    "fk_simulations_terminated_by_recruiter_id_users",
                )
        op.alter_column(
            "trials",
            "terminated_by_talent_partner_id",
            new_column_name="terminated_by_recruiter_id",
            existing_type=sa.Integer(),
        )

    if _has_table("trials") and not _has_table("simulations"):
        op.rename_table("trials", "simulations")
        _rename_postgres_table_artifacts(
            "trials",
            "simulations",
            rename_indexes={
                "ix_trials_template_key": "ix_simulations_template_key",
            },
            rename_constraints={
                "ck_trials_status_lifecycle": "ck_simulations_status_lifecycle",
                "fk_trials_pending_scenario_version_id": "fk_simulations_pending_scenario_version_id",
            },
        )
