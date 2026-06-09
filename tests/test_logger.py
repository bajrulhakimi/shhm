import logging

from app.utils.logger import SecretRedactionFilter


def test_secret_redaction_filter() -> None:
    record = logging.LogRecord("test", logging.INFO, "", 0, "token=super-secret", (), None)
    SecretRedactionFilter(["super-secret"]).filter(record)

    assert record.getMessage() == "token=[REDACTED]"
