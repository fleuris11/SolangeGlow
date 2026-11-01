from config.sentry import _scrub, init


def test_errors_sent_to_glitchtip_carry_no_personal_data():
    event = {
        "exception": {"values": [{"type": "ValueError", "value": "no user +22901970001 here"}]},
        "logentry": {"message": "mail awa@example.com"},
        "request": {"url": "/api/v1/me", "data": {"phone": "+2290197"}, "cookies": {"a": "b"}},
        "user": {"email": "awa@example.com"},
    }
    cleaned = _scrub(event, {})
    assert cleaned["exception"]["values"][0]["value"] == "no user +*** here"
    assert cleaned["logentry"]["message"] == "mail ***@***"
    assert "data" not in cleaned["request"] and "cookies" not in cleaned["request"]
    assert "user" not in cleaned


def test_off_without_a_dsn():
    assert init("", environment="test", traces=0) is None
