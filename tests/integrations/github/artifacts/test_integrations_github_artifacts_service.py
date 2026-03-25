from __future__ import annotations

import io
from zipfile import ZipFile

from app.integrations.github.artifacts import parse_test_results_zip


def test_parse_test_results_prefers_json():
    buf = io.BytesIO()
    with ZipFile(buf, "w") as zf:
        zf.writestr(
            "tenon-test-results.json",
            '{"passed":2,"failed":1,"total":3,"stdout":"ok","stderr":""}',
        )
    parsed = parse_test_results_zip(buf.getvalue())
    assert parsed
    assert parsed.passed == 2
    assert parsed.failed == 1
    assert parsed.total == 3
    assert parsed.stdout == "ok"


def test_parse_test_results_handles_malformed_json_gracefully():
    buf = io.BytesIO()
    with ZipFile(buf, "w") as zf:
        zf.writestr("tenon-test-results.json", "{not-json")
    assert parse_test_results_zip(buf.getvalue()) is None


def test_parse_test_results_junit_fallback():
    junit_xml = """
    <testsuite name="suite">
        <testcase classname="c" name="pass"/>
        <testcase classname="c" name="fail"><failure/></testcase>
    </testsuite>
    """
    buf = io.BytesIO()
    with ZipFile(buf, "w") as zf:
        zf.writestr("results.xml", junit_xml)
    parsed = parse_test_results_zip(buf.getvalue())
    assert parsed
    assert parsed.passed == 1
    assert parsed.failed == 1
    assert parsed.total == 2
    assert parsed.summary == {"format": "junit"}


def test_parse_test_results_json_fallback_and_bad_xml():
    buf = io.BytesIO()
    with ZipFile(buf, "w") as zf:
        zf.writestr("other.json", '{"passed":3,"failed":1,"total":4,"summary":{"s":1}}')
        zf.writestr("broken.xml", "<testsuite><testcase></testsuite")
    parsed = parse_test_results_zip(buf.getvalue())
    assert parsed
    assert parsed.passed == 3
    assert parsed.total == 4
    assert parsed.summary == {"s": 1}


def test_parse_test_results_bad_xml_only_returns_none():
    buf = io.BytesIO()
    with ZipFile(buf, "w") as zf:
        zf.writestr("only.xml", "<testsuite><bad")
    assert parse_test_results_zip(buf.getvalue()) is None


def test_safe_json_load_returns_none_for_non_dict():
    buf = io.BytesIO()
    with ZipFile(buf, "w") as zf:
        zf.writestr("array.json", "[1,2,3]")
    assert parse_test_results_zip(buf.getvalue()) is None
