from __future__ import annotations

from tests.config.config_test_utils import *


def test_trusted_proxy_coercion_variants(monkeypatch):
    # list input is passed through
    assert Settings._coerce_trusted_proxy_cidrs(["10.0.0.0/8"]) == ["10.0.0.0/8"]
    # JSON array text parses correctly
    assert Settings._coerce_trusted_proxy_cidrs('["10.0.0.0/8"]') == ["10.0.0.0/8"]
    assert Settings._coerce_trusted_proxy_cidrs("[invalid") == ["[invalid"]
