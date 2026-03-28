from __future__ import annotations

import importlib
from datetime import UTC, datetime
from types import SimpleNamespace

import sqlalchemy as sa

reconcile_constants = importlib.import_module(
    "app.core.db.migrations.reconcile_202603190001.constants"
)
reconcile_introspection = importlib.import_module(
    "app.core.db.migrations.reconcile_202603190001.introspection"
)
reconcile_recording_status = importlib.import_module(
    "app.core.db.migrations.reconcile_202603190001.recording_status"
)
reconcile_safe_ops = importlib.import_module(
    "app.core.db.migrations.reconcile_202603190001.safe_ops"
)
reconcile_scenario_backfill = importlib.import_module(
    "app.core.db.migrations.reconcile_202603190001.scenario_backfill"
)
reconcile_upgrade = importlib.import_module(
    "app.core.db.migrations.reconcile_202603190001.upgrade"
)


class _RecordingOp:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...], dict[str, object]]] = []

    def __getattr__(self, name: str):
        def _record(*args: object, **kwargs: object) -> None:
            self.calls.append((name, args, kwargs))

        return _record


def test_reconcile_introspection_helpers_collect_names(monkeypatch):
    inspector = SimpleNamespace(
        get_columns=lambda _table: [{"name": "id"}, {"name": "status"}],
        get_foreign_keys=lambda _table: [{"name": "fk_a"}, {"name": None}],
        get_indexes=lambda _table: [{"name": "ix_a"}, {"name": None}],
        get_check_constraints=lambda _table: [{"name": "ck_a"}, {"name": None}],
        get_table_names=lambda: ["simulations", "scenario_versions"],
        get_unique_constraints=lambda _table: [{"name": "uq_a"}, {"name": None}],
    )
    monkeypatch.setattr(reconcile_introspection.sa, "inspect", lambda _bind: inspector)
    bind = object()

    assert reconcile_introspection.column_names(bind, "simulations") == {"id", "status"}
    assert reconcile_introspection.has_column(bind, "simulations", "status") is True
    assert reconcile_introspection.fk_names(bind, "simulations") == {"fk_a"}
    assert reconcile_introspection.index_names(bind, "simulations") == {"ix_a"}
    assert reconcile_introspection.check_names(bind, "simulations") == {"ck_a"}
    assert reconcile_introspection.table_exists(bind, "scenario_versions") is True
    assert reconcile_introspection.unique_constraint_names(bind, "simulations") == {
        "uq_a"
    }


def test_reconcile_safe_ops_add_only_when_missing(monkeypatch):
    op = _RecordingOp()
    bind = object()
    column = sa.Column("example_col", sa.Integer())

    monkeypatch.setattr(
        reconcile_safe_ops,
        "has_column",
        lambda _bind, _table, column_name: column_name == "existing_col",
    )
    reconcile_safe_ops.add_column_if_missing(op, bind, "example", column)
    reconcile_safe_ops.add_column_if_missing(
        op, bind, "example", sa.Column("existing_col", sa.Integer())
    )

    monkeypatch.setattr(
        reconcile_safe_ops,
        "fk_names",
        lambda _bind, _table: {"existing_fk"},
    )
    reconcile_safe_ops.add_fk_if_missing(
        op,
        bind,
        name="missing_fk",
        source_table="child",
        referent_table="parent",
        local_cols=["parent_id"],
        remote_cols=["id"],
    )
    reconcile_safe_ops.add_fk_if_missing(
        op,
        bind,
        name="existing_fk",
        source_table="child",
        referent_table="parent",
        local_cols=["parent_id"],
        remote_cols=["id"],
    )

    monkeypatch.setattr(
        reconcile_safe_ops,
        "index_names",
        lambda _bind, _table: {"existing_ix"},
    )
    reconcile_safe_ops.add_index_if_missing(
        op,
        bind,
        name="missing_ix",
        table_name="items",
        columns=["id"],
    )
    reconcile_safe_ops.add_index_if_missing(
        op,
        bind,
        name="existing_ix",
        table_name="items",
        columns=["id"],
    )

    call_names = [name for name, _, _ in op.calls]
    assert call_names.count("add_column") == 1
    assert call_names.count("create_foreign_key") == 1
    assert call_names.count("create_index") == 1


def test_reconcile_recording_status_noop_for_non_postgresql():
    op = _RecordingOp()
    bind = SimpleNamespace(dialect=SimpleNamespace(name="sqlite"))
    reconcile_recording_status.reconcile_recording_status_check(op, bind)
    assert not op.calls


def test_reconcile_recording_status_replaces_existing_check(monkeypatch):
    op = _RecordingOp()
    bind = SimpleNamespace(dialect=SimpleNamespace(name="postgresql"))
    monkeypatch.setattr(
        reconcile_recording_status,
        "check_names",
        lambda _bind, _table: {reconcile_constants.RECORDING_STATUS_CHECK_NAME},
    )

    reconcile_recording_status.reconcile_recording_status_check(op, bind)

    call_names = [name for name, _, _ in op.calls]
    assert call_names == ["drop_constraint", "create_check_constraint"]


def test_reconcile_recording_status_creates_check_when_missing(monkeypatch):
    op = _RecordingOp()
    bind = SimpleNamespace(dialect=SimpleNamespace(name="postgresql"))
    monkeypatch.setattr(
        reconcile_recording_status,
        "check_names",
        lambda _bind, _table: set(),
    )

    reconcile_recording_status.reconcile_recording_status_check(op, bind)

    call_names = [name for name, _, _ in op.calls]
    assert call_names == ["create_check_constraint"]


class _ScalarResult:
    def __init__(self, scalar: object) -> None:
        self._scalar = scalar

    def scalar_one_or_none(self) -> object:
        return self._scalar


class _MappingsResult:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self._rows = rows

    def mappings(self) -> list[dict[str, object]]:
        return self._rows


class _ScenarioBackfillBind:
    def __init__(self) -> None:
        self.updates: list[dict[str, int]] = []
        self.final_update_called = False

    def execute(
        self, statement: object, params: dict[str, int] | None = None
    ) -> object:
        sql = statement.text if hasattr(statement, "text") else str(statement)
        if "FROM simulations" in sql and "scenario_template" in sql:
            return _MappingsResult(
                [
                    {
                        "id": 1,
                        "status": "active_inviting",
                        "title": "A",
                        "role": "R",
                        "tech_stack": "python",
                        "seniority": "mid",
                        "focus": "f",
                        "scenario_template": "t",
                        "template_key": None,
                        "created_at": datetime(2026, 1, 1, tzinfo=UTC),
                        "activated_at": datetime(2026, 1, 2, tzinfo=UTC),
                        "terminated_at": None,
                    },
                    {
                        "id": 2,
                        "status": "draft",
                        "title": "B",
                        "role": "R2",
                        "tech_stack": "python",
                        "seniority": "senior",
                        "focus": "f2",
                        "scenario_template": "t2",
                        "template_key": "custom",
                        "created_at": datetime(2026, 1, 3, tzinfo=UTC),
                        "activated_at": None,
                        "terminated_at": None,
                    },
                ]
            )
        if "SELECT id FROM scenario_versions" in sql:
            assert params is not None
            return _ScalarResult(None if params["simulation_id"] == 1 else 222)
        if "UPDATE simulations SET active_scenario_version_id" in sql:
            assert params is not None
            self.updates.append(
                {
                    "simulation_id": params["simulation_id"],
                    "scenario_id": params["scenario_id"],
                }
            )
            return object()
        if "UPDATE candidate_sessions cs SET scenario_version_id" in sql:
            self.final_update_called = True
            return object()
        raise AssertionError(f"Unexpected statement: {sql}")


def test_reconcile_ensure_scenario_versions_backfill_guard_clauses(monkeypatch):
    bind = _ScenarioBackfillBind()
    monkeypatch.setattr(reconcile_scenario_backfill, "table_exists", lambda *_: False)
    reconcile_scenario_backfill.ensure_scenario_versions_backfill(bind)
    assert not bind.updates

    monkeypatch.setattr(reconcile_scenario_backfill, "table_exists", lambda *_: True)
    monkeypatch.setattr(
        reconcile_scenario_backfill,
        "has_column",
        lambda _bind, table, _col: table != "simulations",
    )
    reconcile_scenario_backfill.ensure_scenario_versions_backfill(bind)
    assert not bind.updates

    monkeypatch.setattr(
        reconcile_scenario_backfill,
        "has_column",
        lambda _bind, table, _col: table != "candidate_sessions",
    )
    reconcile_scenario_backfill.ensure_scenario_versions_backfill(bind)
    assert not bind.updates


def test_reconcile_ensure_scenario_versions_backfill_updates_active_ids(monkeypatch):
    bind = _ScenarioBackfillBind()
    monkeypatch.setattr(reconcile_scenario_backfill, "table_exists", lambda *_: True)
    monkeypatch.setattr(reconcile_scenario_backfill, "has_column", lambda *_: True)
    create_calls: list[int] = []

    def _fake_create_v1(_bind, _table, row):
        create_calls.append(int(row["id"]))
        return 900

    monkeypatch.setattr(reconcile_scenario_backfill, "_create_v1", _fake_create_v1)
    reconcile_scenario_backfill.ensure_scenario_versions_backfill(bind)

    assert create_calls == [1]
    assert bind.updates == [
        {"simulation_id": 1, "scenario_id": 900},
        {"simulation_id": 2, "scenario_id": 222},
    ]
    assert bind.final_update_called is True


def test_reconcile_create_v1_inserts_expected_locked_row():
    engine = sa.create_engine("sqlite+pysqlite:///:memory:")
    metadata = sa.MetaData()
    scenario_versions = sa.Table(
        "scenario_versions",
        metadata,
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("simulation_id", sa.Integer(), nullable=False),
        sa.Column("version_index", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("storyline_md", sa.Text(), nullable=False),
        sa.Column("task_prompts_json", sa.JSON(), nullable=False),
        sa.Column("rubric_json", sa.JSON(), nullable=False),
        sa.Column("focus_notes", sa.Text(), nullable=False),
        sa.Column("template_key", sa.String(), nullable=False),
        sa.Column("tech_stack", sa.String(), nullable=False),
        sa.Column("seniority", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
    )
    metadata.create_all(engine)
    row = {
        "id": 7,
        "status": "terminated",
        "title": "Title",
        "role": "Role",
        "tech_stack": "python",
        "seniority": "mid",
        "focus": "Focus",
        "scenario_template": "template",
        "template_key": None,
        "created_at": datetime(2026, 1, 4, tzinfo=UTC),
        "activated_at": None,
        "terminated_at": datetime(2026, 1, 5, tzinfo=UTC),
    }

    with engine.begin() as conn:
        created_id = reconcile_scenario_backfill._create_v1(
            conn, scenario_versions, row
        )
        stored = conn.execute(sa.select(scenario_versions)).mappings().one()

    assert created_id == 1
    assert stored["simulation_id"] == 7
    assert stored["status"] == "locked"
    assert stored["template_key"] == reconcile_constants.DEFAULT_TEMPLATE_KEY
    assert stored["locked_at"] is not None


def test_reconcile_create_v1_inserts_ready_row_for_non_terminal_status():
    engine = sa.create_engine("sqlite+pysqlite:///:memory:")
    metadata = sa.MetaData()
    scenario_versions = sa.Table(
        "scenario_versions",
        metadata,
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("simulation_id", sa.Integer(), nullable=False),
        sa.Column("version_index", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("storyline_md", sa.Text(), nullable=False),
        sa.Column("task_prompts_json", sa.JSON(), nullable=False),
        sa.Column("rubric_json", sa.JSON(), nullable=False),
        sa.Column("focus_notes", sa.Text(), nullable=False),
        sa.Column("template_key", sa.String(), nullable=False),
        sa.Column("tech_stack", sa.String(), nullable=False),
        sa.Column("seniority", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
    )
    metadata.create_all(engine)
    row = {
        "id": 8,
        "status": "draft",
        "title": "Draft Title",
        "role": "Role",
        "tech_stack": "python",
        "seniority": "junior",
        "focus": "Focus",
        "scenario_template": "template",
        "template_key": "custom-template",
        "created_at": datetime(2026, 1, 6, tzinfo=UTC),
        "activated_at": None,
        "terminated_at": None,
    }

    with engine.begin() as conn:
        created_id = reconcile_scenario_backfill._create_v1(
            conn, scenario_versions, row
        )
        stored = conn.execute(sa.select(scenario_versions)).mappings().one()

    assert created_id == 1
    assert stored["simulation_id"] == 8
    assert stored["status"] == "ready"
    assert stored["template_key"] == "custom-template"
    assert stored["locked_at"] is None


def test_reconcile_run_upgrade_delegates_specs_and_unique_constraint(monkeypatch):
    op = _RecordingOp()
    bind = object()
    seen: dict[str, int] = {
        "columns": 0,
        "fks": 0,
        "indexes": 0,
        "backfill": 0,
        "status": 0,
    }

    monkeypatch.setattr(
        reconcile_upgrade,
        "add_column_if_missing",
        lambda *_args, **_kwargs: seen.__setitem__("columns", seen["columns"] + 1),
    )
    monkeypatch.setattr(
        reconcile_upgrade,
        "ensure_scenario_versions_backfill",
        lambda _bind: seen.__setitem__("backfill", seen["backfill"] + 1),
    )
    monkeypatch.setattr(
        reconcile_upgrade,
        "add_fk_if_missing",
        lambda *_args, **_kwargs: seen.__setitem__("fks", seen["fks"] + 1),
    )
    monkeypatch.setattr(
        reconcile_upgrade,
        "add_index_if_missing",
        lambda *_args, **_kwargs: seen.__setitem__("indexes", seen["indexes"] + 1),
    )
    monkeypatch.setattr(
        reconcile_upgrade,
        "unique_constraint_names",
        lambda *_args, **_kwargs: set(),
    )
    monkeypatch.setattr(
        reconcile_upgrade,
        "index_names",
        lambda *_args, **_kwargs: set(),
    )
    monkeypatch.setattr(
        reconcile_upgrade,
        "reconcile_recording_status_check",
        lambda *_args, **_kwargs: seen.__setitem__("status", seen["status"] + 1),
    )

    reconcile_upgrade.run_upgrade(op, bind)

    assert seen["columns"] == len(reconcile_upgrade.COLUMN_SPECS)
    assert seen["fks"] == len(reconcile_upgrade.FK_SPECS)
    assert seen["indexes"] == len(reconcile_upgrade.INDEX_SPECS)
    assert seen["backfill"] == 1
    assert seen["status"] == 1
    assert any(name == "create_unique_constraint" for name, _, _ in op.calls)


def test_reconcile_run_upgrade_skips_unique_constraint_when_present(monkeypatch):
    op = _RecordingOp()
    bind = object()

    monkeypatch.setattr(
        reconcile_upgrade, "add_column_if_missing", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        reconcile_upgrade,
        "ensure_scenario_versions_backfill",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        reconcile_upgrade, "add_fk_if_missing", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        reconcile_upgrade, "add_index_if_missing", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        reconcile_upgrade,
        "unique_constraint_names",
        lambda *_args, **_kwargs: {reconcile_upgrade.WORKSPACES_GROUP_UNIQUE_NAME},
    )
    monkeypatch.setattr(
        reconcile_upgrade, "index_names", lambda *_args, **_kwargs: set()
    )
    monkeypatch.setattr(
        reconcile_upgrade,
        "reconcile_recording_status_check",
        lambda *_args, **_kwargs: None,
    )

    reconcile_upgrade.run_upgrade(op, bind)

    assert not any(name == "create_unique_constraint" for name, _, _ in op.calls)
