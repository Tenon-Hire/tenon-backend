from __future__ import annotations

import importlib
from datetime import UTC, datetime
from types import SimpleNamespace

import sqlalchemy as sa

scenario_versions_backfill = importlib.import_module(
    "app.core.db.migrations.scenario_versions_202603090001.backfill"
)
scenario_versions_constants = importlib.import_module(
    "app.core.db.migrations.scenario_versions_202603090001.constants"
)
scenario_versions_runner = importlib.import_module(
    "app.core.db.migrations.scenario_versions_202603090001.runner"
)
scenario_versions_schema_ops = importlib.import_module(
    "app.core.db.migrations.scenario_versions_202603090001.schema_ops"
)
table_refs = importlib.import_module(
    "app.core.db.migrations.scenario_versions_202603090001.table_refs"
).table_refs
trial_schema_compat = importlib.import_module(
    "app.core.db.migrations.shared_trial_schema_compat"
)


class _RecordingOp:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...], dict[str, object]]] = []
        self._bind: object = object()

    def __getattr__(self, name: str):
        def _record(*args: object, **kwargs: object) -> None:
            self.calls.append((name, args, kwargs))

        return _record

    def get_bind(self) -> object:
        return self._bind

    def bind_to(self, bind: object) -> None:
        self._bind = bind


def test_scenario_versions_table_refs_expose_expected_table_shapes():
    trials, scenario_versions, candidate_sessions = table_refs()
    assert trials.name == "trials"
    assert scenario_versions.name == "scenario_versions"
    assert candidate_sessions.name == "candidate_sessions"
    assert "active_scenario_version_id" in trials.c
    assert "version_index" in scenario_versions.c
    assert "scenario_version_id" in candidate_sessions.c


def test_scenario_versions_table_refs_support_legacy_schema_names(monkeypatch):
    inspector = SimpleNamespace(
        get_table_names=lambda: ["simulations", "candidate_sessions"],
        get_columns=lambda table_name: (
            [{"name": "simulation_id"}, {"name": "scenario_version_id"}]
            if table_name == "candidate_sessions"
            else []
        ),
    )
    monkeypatch.setattr(trial_schema_compat.sa, "inspect", lambda _bind: inspector)

    trials, _scenario_versions, candidate_sessions = table_refs(object())

    assert trials.name == "simulations"
    assert "simulation_id" in candidate_sessions.c


def test_scenario_versions_row_get_supports_mapping_dict_and_object():
    mapping_row = type("MappingRow", (), {"_mapping": {"id": 1}})()
    dict_row = {"id": 2}
    object_row = type("ObjectRow", (), {"id": 3})()

    assert scenario_versions_backfill._row_get(mapping_row, "id") == 1
    assert scenario_versions_backfill._row_get(dict_row, "id") == 2
    assert scenario_versions_backfill._row_get(object_row, "id") == 3
    assert scenario_versions_backfill._row_get(object_row, "missing") is None


def test_scenario_versions_run_backfill_inserts_versions_and_links_sessions():
    engine = sa.create_engine("sqlite+pysqlite:///:memory:")
    metadata = sa.MetaData()
    trials = sa.Table(
        "trials",
        metadata,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("active_scenario_version_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("role", sa.String(), nullable=True),
        sa.Column("tech_stack", sa.String(), nullable=True),
        sa.Column("seniority", sa.String(), nullable=True),
        sa.Column("focus", sa.Text(), nullable=True),
        sa.Column("scenario_template", sa.String(), nullable=True),
        sa.Column("template_key", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("terminated_at", sa.DateTime(timezone=True), nullable=True),
    )
    scenario_versions = sa.Table(
        "scenario_versions",
        metadata,
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("trial_id", sa.Integer(), nullable=False),
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
    candidate_sessions = sa.Table(
        "candidate_sessions",
        metadata,
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("trial_id", sa.Integer(), nullable=False),
        sa.Column("scenario_version_id", sa.Integer(), nullable=True),
    )
    metadata.create_all(engine)

    with engine.begin() as conn:
        conn.execute(
            trials.insert(),
            [
                {
                    "id": 1,
                    "status": "active_inviting",
                    "title": "Backend Refactor",
                    "role": "Senior Engineer",
                    "tech_stack": "python,fastapi",
                    "seniority": "senior",
                    "focus": "correctness",
                    "scenario_template": "general",
                    "template_key": "custom-template",
                    "created_at": datetime(2026, 1, 2, tzinfo=UTC),
                    "activated_at": datetime(2026, 1, 3, tzinfo=UTC),
                    "terminated_at": None,
                },
                {
                    "id": 2,
                    "status": "draft",
                    "title": "Data Cleanup",
                    "role": "Engineer",
                    "tech_stack": "python",
                    "seniority": "mid",
                    "focus": None,
                    "scenario_template": "ops",
                    "template_key": None,
                    "created_at": None,
                    "activated_at": None,
                    "terminated_at": None,
                },
            ],
        )
        conn.execute(
            candidate_sessions.insert(),
            [
                {"trial_id": 1, "scenario_version_id": None},
                {"trial_id": 2, "scenario_version_id": None},
            ],
        )

        scenario_versions_backfill.run_backfill(conn)

        version_rows = (
            conn.execute(
                sa.select(
                    scenario_versions.c.trial_id,
                    scenario_versions.c.status,
                    scenario_versions.c.template_key,
                    scenario_versions.c.locked_at,
                ).order_by(scenario_versions.c.trial_id)
            )
            .mappings()
            .all()
        )
        assert len(version_rows) == 2
        assert version_rows[0]["status"] == "locked"
        assert version_rows[0]["template_key"] == "custom-template"
        assert version_rows[0]["locked_at"] is not None
        assert version_rows[1]["status"] == "ready"
        assert (
            version_rows[1]["template_key"]
            == scenario_versions_constants.DEFAULT_TEMPLATE_KEY
        )
        assert version_rows[1]["locked_at"] is None

        linked_sessions = (
            conn.execute(
                sa.select(candidate_sessions.c.scenario_version_id).order_by(
                    candidate_sessions.c.trial_id
                )
            )
            .scalars()
            .all()
        )
        assert all(linked_sessions)

        active_ids = (
            conn.execute(
                sa.select(trials.c.active_scenario_version_id).order_by(trials.c.id)
            )
            .scalars()
            .all()
        )
        assert all(active_ids)


def test_scenario_versions_schema_ops_create_finalize_and_downgrade():
    op = _RecordingOp()
    scenario_versions_schema_ops.create_schema(op)
    scenario_versions_schema_ops.finalize_upgrade(op)
    scenario_versions_schema_ops.run_downgrade_schema(op)

    call_names = [name for name, _, _ in op.calls]
    assert "create_table" in call_names
    assert "create_foreign_key" in call_names
    assert "create_check_constraint" in call_names
    assert "drop_table" in call_names

    create_table_call = next(
        args for name, args, _ in op.calls if name == "create_table"
    )
    assert create_table_call[0] == "scenario_versions"

    check_call = next(
        args for name, args, _ in op.calls if name == "create_check_constraint"
    )
    assert (
        check_call[0]
        == scenario_versions_constants.TRIAL_ACTIVE_SCENARIO_REQUIRED_CHECK_NAME
    )


def test_scenario_versions_schema_ops_use_legacy_parent_table(monkeypatch):
    inspector = SimpleNamespace(get_table_names=lambda: ["simulations"])
    monkeypatch.setattr(
        scenario_versions_schema_ops.sa, "inspect", lambda _bind: inspector
    )
    op = _RecordingOp()

    scenario_versions_schema_ops.create_schema(op)

    create_table_call = next(
        args for name, args, _ in op.calls if name == "create_table"
    )
    foreign_key = next(
        iter(
            arg
            for arg in create_table_call[1:]
            if isinstance(arg, sa.ForeignKeyConstraint)
        )
    )
    add_column_call = next(args for name, args, _ in op.calls if name == "add_column")

    assert next(iter(foreign_key.elements)).target_fullname == "simulations.id"
    assert add_column_call[0] == "simulations"


def test_scenario_versions_runner_delegates_upgrade_and_downgrade(monkeypatch):
    op = _RecordingOp()
    fake_bind = object()
    op.bind_to(fake_bind)
    seen: list[tuple[str, object]] = []

    monkeypatch.setattr(
        scenario_versions_runner,
        "create_schema",
        lambda value: seen.append(("create_schema", value)),
    )
    monkeypatch.setattr(
        scenario_versions_runner,
        "run_backfill",
        lambda value: seen.append(("run_backfill", value)),
    )
    monkeypatch.setattr(
        scenario_versions_runner,
        "finalize_upgrade",
        lambda value: seen.append(("finalize_upgrade", value)),
    )
    monkeypatch.setattr(
        scenario_versions_runner,
        "run_downgrade_schema",
        lambda value: seen.append(("run_downgrade_schema", value)),
    )

    scenario_versions_runner.run_upgrade(op)
    scenario_versions_runner.run_downgrade(op)

    assert seen == [
        ("create_schema", op),
        ("run_backfill", fake_bind),
        ("finalize_upgrade", op),
        ("run_downgrade_schema", op),
    ]
