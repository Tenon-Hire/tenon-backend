TABLE_NAME = "candidate_sessions"

DROP_INDEXES = (
    "ix_candidate_sessions_access_token",
    "ix_candidate_sessions_candidate_access_token_hash",
)

DROP_COLUMNS = (
    "access_token",
    "access_token_expires_at",
    "invite_email_verified_at",
    "candidate_access_token_hash",
    "candidate_access_token_expires_at",
    "candidate_access_token_issued_at",
    "verification_code",
    "verification_code_attempts",
    "verification_code_send_count",
    "verification_code_sent_at",
    "verification_code_expires_at",
    "verification_email_status",
    "verification_email_error",
    "verification_email_last_attempt_at",
)
