from django.test import RequestFactory

from apps.accounts.throttling import SettingRateThrottle, forwarded_ip


def _request(**headers):
    return RequestFactory().get("/api/v1/feed", REMOTE_ADDR="10.0.0.5", **headers)


def test_the_web_server_passes_the_visitor_address_with_the_secret(settings):
    settings.INTERNAL_API_TOKEN = "s3cret"
    good = _request(HTTP_X_SG_INTERNAL="s3cret", HTTP_X_SG_CLIENT_IP="196.192.1.7")
    assert forwarded_ip(good) == "196.192.1.7"
    assert SettingRateThrottle().get_ident(good) == "196.192.1.7"


def test_anyone_else_cannot_choose_its_address(settings):
    settings.INTERNAL_API_TOKEN = "s3cret"
    for request in (
        _request(HTTP_X_SG_CLIENT_IP="1.2.3.4"),
        _request(HTTP_X_SG_INTERNAL="wrong", HTTP_X_SG_CLIENT_IP="1.2.3.4"),
        _request(HTTP_X_SG_INTERNAL="s3cret", HTTP_X_SG_CLIENT_IP="not-an-ip"),
    ):
        assert SettingRateThrottle().get_ident(request) == "10.0.0.5"
    settings.INTERNAL_API_TOKEN = ""
    assert forwarded_ip(_request(HTTP_X_SG_INTERNAL="", HTTP_X_SG_CLIENT_IP="1.2.3.4")) is None
