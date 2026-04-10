from app.config import settings
from app.shared.utils import shared_utils_env_utils as env
from app.submissions.constants import (
    submissions_constants_submissions_exceptions_constants as exceptions,
)


def test_env_helpers_local(monkeypatch):
    monkeypatch.setenv("ENV", "local")
    monkeypatch.setattr(settings, "ENV", "local")
    assert env.env_name() == "local"
    assert env.is_local_or_test() is True
    assert env.is_prod() is False


def test_env_helpers_prod(monkeypatch):
    monkeypatch.setenv("ENV", "prod")
    monkeypatch.setattr(settings, "ENV", "prod")
    assert env.env_name() == "prod"
    assert env.is_local_or_test() is False
    assert env.is_prod() is True


def test_env_name_falls_back_to_winoe_env(monkeypatch):
    monkeypatch.setattr(settings, "ENV", "")
    monkeypatch.setenv("WINOE_ENV", "staging")
    assert env.env_name() == "staging"


def test_submission_exceptions_payloads():
    conflict = exceptions.SubmissionConflict()
    order_error = exceptions.SubmissionOrderError()
    sim_complete = exceptions.TrialComplete()
    workspace_missing = exceptions.WorkspaceMissing()

    assert conflict.status_code == 409
    assert order_error.status_code == 400
    assert sim_complete.status_code == 409
    assert workspace_missing.status_code == 400

    # Custom detail propagates through __init__
    custom = exceptions.WorkspaceMissing(detail="Init first")
    assert custom.detail == "Init first"
