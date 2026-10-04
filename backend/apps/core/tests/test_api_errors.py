from django.http import Http404
from rest_framework import exceptions

from apps.core.api.exceptions import exception_handler


def test_validation_error_format():
    response = exception_handler(
        exceptions.ValidationError({"email": ["This field is required."]}), {}
    )

    assert response.status_code == 400
    assert response.data["code"] == "validation_error"
    assert response.data["message"]
    assert response.data["fields"] == {"email": ["This field is required."]}


def test_not_found_format():
    response = exception_handler(Http404(), {})

    assert response.status_code == 404
    assert response.data["code"] == "not_found"
    assert response.data["fields"] == {}
