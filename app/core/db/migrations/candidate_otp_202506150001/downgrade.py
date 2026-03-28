"""Application module for downgrade workflows."""

from __future__ import annotations

from .constants import TABLE_NAME

_COLUMN_SPECS = (
    ("access_token", lambda sa: sa.String(length=255), True, None),
    ("access_token_expires_at", lambda sa: sa.DateTime(timezone=True), True, None),
    ("invite_email_verified_at", lambda sa: sa.DateTime(timezone=True), True, None),
    ("candidate_access_token_hash", lambda sa: sa.String(length=128), True, None),
    (
        "candidate_access_token_expires_at",
        lambda sa: sa.DateTime(timezone=True),
        True,
        None,
    ),
    (
        "candidate_access_token_issued_at",
        lambda sa: sa.DateTime(timezone=True),
        True,
        None,
    ),
    ("verification_code", lambda sa: sa.String(length=20), True, None),
    ("verification_code_attempts", lambda sa: sa.Integer(), False, "0"),
    ("verification_code_send_count", lambda sa: sa.Integer(), False, "0"),
    ("verification_code_sent_at", lambda sa: sa.DateTime(timezone=True), True, None),
    ("verification_code_expires_at", lambda sa: sa.DateTime(timezone=True), True, None),
    ("verification_email_status", lambda sa: sa.String(length=50), True, None),
    ("verification_email_error", lambda sa: sa.String(length=500), True, None),
    (
        "verification_email_last_attempt_at",
        lambda sa: sa.DateTime(timezone=True),
        True,
        None,
    ),
)


def run_downgrade(op, sa) -> None:
    """Run downgrade."""
    for name, type_factory, nullable, server_default in _COLUMN_SPECS:
        kwargs = {"nullable": nullable}
        if server_default is not None:
            kwargs["server_default"] = server_default
        op.add_column(TABLE_NAME, sa.Column(name, type_factory(sa), **kwargs))

    op.create_index(
        "ix_candidate_sessions_access_token",
        TABLE_NAME,
        ["access_token"],
        unique=True,
    )
    op.create_index(
        "ix_candidate_sessions_candidate_access_token_hash",
        TABLE_NAME,
        ["candidate_access_token_hash"],
        unique=False,
    )
