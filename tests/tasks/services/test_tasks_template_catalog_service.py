import pytest

from app.tasks.services import (
    tasks_services_tasks_template_catalog_service as template_catalog_service,
)
from app.tasks.services.tasks_services_tasks_template_catalog_service import (
    ALLOWED_TEMPLATE_KEYS,
    DEFAULT_TEMPLATE_KEY,
    LEGACY_TEMPLATE_REPO_REWRITES,
    TemplateKeyError,
    normalize_template_repo_value,
    resolve_template_repo_full_name,
    validate_template_key,
)


@pytest.mark.parametrize(
    ("template_key", "expected_repo"),
    [
        ("python-fastapi", "winoe-hire-dev/winoe-template-python-fastapi"),
        ("node-express-ts", "winoe-hire-dev/winoe-template-node-express-ts"),
        (
            "monorepo-nextjs-fastapi",
            "winoe-hire-dev/winoe-template-monorepo-nextjs-fastapi",
        ),
        (
            "monorepo-react-springboot",
            "winoe-hire-dev/winoe-template-monorepo-react-springboot",
        ),
        (
            "mobile-backend-fastapi",
            "winoe-hire-dev/winoe-template-mobile-backend-fastapi",
        ),
        ("ml-infra-mlops", "winoe-hire-dev/winoe-template-ml-infra-mlops"),
    ],
)
def test_resolve_template_repo_full_name(template_key: str, expected_repo: str):
    assert resolve_template_repo_full_name(template_key) == expected_repo


def test_invalid_template_key_raises():
    with pytest.raises(TemplateKeyError) as excinfo:
        resolve_template_repo_full_name("unknown-stack")
    msg = str(excinfo.value)
    assert "Invalid templateKey" in msg
    for allowed in sorted(ALLOWED_TEMPLATE_KEYS)[:3]:
        assert allowed in msg


@pytest.mark.parametrize(
    ("legacy_repo", "expected_repo"),
    [
        (
            "winoe-templates/node-day2-api",
            LEGACY_TEMPLATE_REPO_REWRITES["winoe-templates/node-day2-api"],
        ),
        (
            "winoe-templates/node-day3-debug",
            LEGACY_TEMPLATE_REPO_REWRITES["winoe-templates/node-day3-debug"],
        ),
        (
            "winoe-dev/winoe-template-python",
            "winoe-hire-dev/winoe-template-python-fastapi",
        ),
    ],
)
def test_normalize_template_repo_value_rewrites_legacy(
    legacy_repo: str, expected_repo: str
):
    assert normalize_template_repo_value(legacy_repo) == expected_repo


def test_normalize_template_repo_value_uses_template_key_for_blank():
    resolved = normalize_template_repo_value(None, template_key=DEFAULT_TEMPLATE_KEY)
    assert resolved == resolve_template_repo_full_name(DEFAULT_TEMPLATE_KEY)


def test_normalize_template_repo_value_rewrites_legacy_with_template_key():
    repo = normalize_template_repo_value(
        "winoe-templates/node-day2-api", template_key="node-express-ts"
    )
    assert repo == "winoe-hire-dev/winoe-template-node-express-ts"


def test_normalize_template_repo_value_returns_none_when_no_hints():
    assert normalize_template_repo_value("", template_key=None) is None


def test_validate_template_key_requires_string():
    with pytest.raises(TemplateKeyError):
        validate_template_key(123)  # type: ignore[arg-type]


def test_normalize_template_repo_value_invalid_key_and_custom_repo():
    assert normalize_template_repo_value(None, template_key="invalid-key") is None
    assert (
        normalize_template_repo_value("custom/repo", template_key="invalid-key")
        == "custom/repo"
    )


def test_canonical_key_from_repo_handles_missing_and_late_match(monkeypatch):
    monkeypatch.setattr(
        template_catalog_service,
        "TEMPLATE_CATALOG",
        {
            "first": {"repo_full_name": "org/first"},
            "second": {"repo_full_name": "org/second"},
        },
    )

    assert template_catalog_service._canonical_key_from_repo("org/second") == "second"
    assert (
        template_catalog_service._canonical_key_from_repo("org/does-not-exist") is None
    )


def test_build_template_key_aliases_skips_blank_repo_and_unknown_legacy_rewrite(
    monkeypatch,
):
    monkeypatch.setattr(
        template_catalog_service,
        "TEMPLATE_CATALOG",
        {
            "python-fastapi": {
                "repo_full_name": "winoe-hire-dev/winoe-template-python-fastapi"
            },
            "blank-repo": {"repo_full_name": "   "},
        },
    )
    monkeypatch.setattr(
        template_catalog_service,
        "LEGACY_TEMPLATE_REPO_REWRITES",
        {"legacy/repo": "winoe-hire-dev/non-existent-template"},
    )

    aliases = template_catalog_service._build_template_key_aliases()
    assert aliases["python-fastapi"] == "python-fastapi"
    assert aliases["blank-repo"] == "blank-repo"
    assert "legacy/repo" not in aliases
