"""Events between modules: listeners run after the commit, a failing one never breaks
the action that announced the event."""

from apps.core import events


def test_listeners_hear_the_event_once_each(db):
    heard = []

    def listener(**payload):
        heard.append(payload)

    events.subscribe("test.done", listener)
    events.subscribe("test.done", listener)
    try:
        events.emit("test.done", value=3)
    finally:
        events.unsubscribe("test.done", listener)
    events.emit("test.done", value=4)
    assert heard == [{"value": 3}]


def test_a_failing_listener_is_logged_and_the_others_run(caplog, db):
    heard = []

    def broken(**payload):
        raise RuntimeError("boom")

    def fine(**payload):
        heard.append(payload["value"])

    events.subscribe("test.fail", broken)
    events.subscribe("test.fail", fine)
    try:
        events.emit("test.fail", value=1)
    finally:
        events.unsubscribe("test.fail", broken)
        events.unsubscribe("test.fail", fine)
    assert heard == [1]
    assert "Listener of test.fail failed" in caplog.text
