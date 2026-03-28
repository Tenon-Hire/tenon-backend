from __future__ import annotations

import importlib
from types import SimpleNamespace

import sqlalchemy as sa

candidate_otp_constants = importlib.import_module(
    "app.core.db.migrations.candidate_otp_202506150001.constants"
)
candidate_otp_downgrade = importlib.import_module(
    "app.core.db.migrations.candidate_otp_202506150001.downgrade"
)
candidate_otp_upgrade = importlib.import_module(
    "app.core.db.migrations.candidate_otp_202506150001.upgrade"
)
recording_assets_constants = importlib.import_module(
    "app.core.db.migrations.recording_assets_202603100003.constants"
)
recording_assets_downgrade = importlib.import_module(
    "app.core.db.migrations.recording_assets_202603100003.downgrade"
)
recording_assets_upgrade = importlib.import_module(
    "app.core.db.migrations.recording_assets_202603100003.upgrade"
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


def test_candidate_otp_upgrade_drops_only_existing_columns_and_indexes():
    op = _RecordingOp()
    bind = object()
    op.bind_to(bind)
    inspector = SimpleNamespace(
        get_columns=lambda _table: [
            {"name": "access_token"},
            {"name": "verification_code"},
        ],
        get_indexes=lambda _table: [{"name": "ix_candidate_sessions_access_token"}],
    )
    fake_sa = SimpleNamespace(inspect=lambda _bind: inspector)

    candidate_otp_upgrade.run_upgrade(op, fake_sa)

    dropped_indexes = [args[0] for name, args, _ in op.calls if name == "drop_index"]
    dropped_columns = [args[1] for name, args, _ in op.calls if name == "drop_column"]

    assert dropped_indexes == ["ix_candidate_sessions_access_token"]
    assert set(dropped_columns) == {"access_token", "verification_code"}


def test_candidate_otp_downgrade_restores_all_columns_and_indexes():
    op = _RecordingOp()

    candidate_otp_downgrade.run_downgrade(op, sa)

    add_column_calls = [args for name, args, _ in op.calls if name == "add_column"]
    create_index_calls = [args for name, args, _ in op.calls if name == "create_index"]

    assert len(add_column_calls) == len(candidate_otp_downgrade._COLUMN_SPECS)
    assert len(create_index_calls) == 2
    assert {args[0] for args in create_index_calls} == set(
        candidate_otp_constants.DROP_INDEXES
    )
    restored_column_names = {args[1].name for args in add_column_calls}
    assert restored_column_names == set(candidate_otp_constants.DROP_COLUMNS)


def test_recording_assets_upgrade_creates_tables_and_indexes():
    op = _RecordingOp()

    recording_assets_upgrade.run_upgrade(op, sa)

    create_table_calls = [args for name, args, _ in op.calls if name == "create_table"]
    create_index_calls = [args for name, args, _ in op.calls if name == "create_index"]

    assert [args[0] for args in create_table_calls] == [
        recording_assets_constants.RECORDING_ASSETS_TABLE,
        recording_assets_constants.TRANSCRIPTS_TABLE,
    ]
    assert {args[0] for args in create_index_calls} == {
        recording_assets_constants.IX_RECORDING_ASSETS_SESSION_TASK_CREATED,
        recording_assets_constants.IX_RECORDING_ASSETS_SESSION_ID,
        recording_assets_constants.IX_RECORDING_ASSETS_TASK_ID,
        recording_assets_constants.IX_TRANSCRIPTS_RECORDING_ID,
        recording_assets_constants.IX_TRANSCRIPTS_STATUS_CREATED_AT,
    }


def test_recording_assets_downgrade_drops_indexes_before_tables():
    op = _RecordingOp()

    recording_assets_downgrade.run_downgrade(op)

    calls = [(name, args) for name, args, _ in op.calls]
    assert calls == [
        (
            "drop_index",
            (recording_assets_constants.IX_TRANSCRIPTS_STATUS_CREATED_AT,),
        ),
        (
            "drop_index",
            (recording_assets_constants.IX_TRANSCRIPTS_RECORDING_ID,),
        ),
        ("drop_table", (recording_assets_constants.TRANSCRIPTS_TABLE,)),
        ("drop_index", (recording_assets_constants.IX_RECORDING_ASSETS_TASK_ID,)),
        ("drop_index", (recording_assets_constants.IX_RECORDING_ASSETS_SESSION_ID,)),
        (
            "drop_index",
            (recording_assets_constants.IX_RECORDING_ASSETS_SESSION_TASK_CREATED,),
        ),
        ("drop_table", (recording_assets_constants.RECORDING_ASSETS_TABLE,)),
    ]
