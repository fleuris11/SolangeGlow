import logging
import sys

from apps.core.logging import RedactPersonalData, redact


def test_phone_numbers_and_emails_are_hidden_codes_stay():
    text = "Code 123456 sent to +229 01 97 00 01 01 and awa.k@example.com"
    assert redact(text) == "Code 123456 sent to +*** and ***@***"


def test_the_filter_cleans_arguments_and_tracebacks():
    record = logging.LogRecord("x", logging.ERROR, __file__, 1, "for %s", ("+33612345678",), None)
    try:
        raise ValueError("bad e-mail awa@example.com")
    except ValueError:
        record.exc_info = sys.exc_info()
    assert RedactPersonalData().filter(record) is True
    assert record.getMessage() == "for +***"
    assert "awa@example.com" not in record.exc_text
