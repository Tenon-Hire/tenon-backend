import logging

from app.infra.logging import configure_logging


def test_log_redaction_masks_bearer_token(caplog):
    configure_logging()
    logger = logging.getLogger("test.redaction")
    token = "Bearer abc.def.ghi"

    with caplog.at_level(logging.INFO):
        logger.info("Authorization: %s", token)

    assert "Bearer [redacted]" in caplog.text
    assert token not in caplog.text

    caplog.clear()
    with caplog.at_level(logging.INFO):
        logger.info("auth extras", extra={"headers": {"authorization": token}})

    record = caplog.records[0]
    assert record.headers["authorization"] == "[redacted]"


def test_attach_filter_to_handlers():
    handler = logging.StreamHandler()
    root = logging.getLogger("attach")
    root.addHandler(handler)
    configure_logging()
    assert any("RedactionFilter" in str(f.__class__) for f in handler.filters)
