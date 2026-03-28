from __future__ import annotations

from tests.config.config_test_utils import *


def test_to_async_url_passthrough_branch():
    assert (
        _to_async_url("mysql://user:pass@localhost/db")
        == "mysql://user:pass@localhost/db"
    )
