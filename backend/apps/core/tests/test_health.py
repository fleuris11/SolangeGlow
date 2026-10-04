import pytest


@pytest.mark.django_db
def test_health_returns_ok(api_client):
    response = api_client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.django_db
def test_openapi_schema_lists_health(api_client):
    response = api_client.get("/api/schema/", HTTP_ACCEPT="application/json")

    assert response.status_code == 200
    assert "/api/v1/health" in response.json()["paths"]


@pytest.mark.django_db
def test_api_docs_page_is_served(api_client):
    assert api_client.get("/api/docs/").status_code == 200
