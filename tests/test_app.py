from collections.abc import Generator
from unittest.mock import Mock

from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from task_cli.api import app, settings
from task_cli.dependencies import get_db


def test_api_root_is_available(
    client: TestClient,
) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "message": "Task API running",
    }


def test_liveness_check_is_available(
    client: TestClient,
) -> None:
    response = client.get("/health/live")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "status": "alive",
    }


def test_readiness_check_confirms_database(
    client: TestClient,
) -> None:
    response = client.get("/health/ready")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "status": "ready",
    }


def test_readiness_check_reports_database_failure(
    client: TestClient,
) -> None:
    unavailable_session = Mock(
        spec=Session,
    )
    unavailable_session.execute.side_effect = SQLAlchemyError(
        "private database error detail",
    )

    def override_unavailable_db() -> Generator[
        Session,
        None,
        None,
    ]:
        yield unavailable_session

    previous_override = app.dependency_overrides[get_db]
    app.dependency_overrides[get_db] = override_unavailable_db

    try:
        response = client.get("/health/ready")
    finally:
        app.dependency_overrides[get_db] = previous_override

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.json() == {
        "detail": "Database unavailable",
    }


def test_openapi_contains_primary_routes(
    client: TestClient,
) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200

    paths = set(response.json()["paths"])

    assert {
        "/",
        "/health/live",
        "/health/ready",
        "/auth/register",
        "/auth/login",
        "/tasks/",
        "/assistant/",
        "/assistant/actions/{action_id}/confirm",
        "/assistant/actions/{action_id}/cancel",
    }.issubset(paths)


def test_cors_allows_configured_frontend(
    client: TestClient,
) -> None:
    response = client.get(
        "/health/live",
        headers={
            "Origin": settings.frontend_origin,
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.headers["access-control-allow-origin"] == settings.frontend_origin


def test_cors_allows_authorization_preflight(
    client: TestClient,
) -> None:
    response = client.options(
        "/tasks/",
        headers={
            "Origin": settings.frontend_origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": ("authorization,content-type"),
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.headers["access-control-allow-origin"] == settings.frontend_origin

    allowed_headers = {
        header.strip().lower()
        for header in response.headers["access-control-allow-headers"].split(",")
    }

    assert {
        "authorization",
        "content-type",
    }.issubset(allowed_headers)


def test_cors_rejects_unconfigured_origin_preflight(
    client: TestClient,
) -> None:
    response = client.options(
        "/tasks/",
        headers={
            "Origin": "https://untrusted.example.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": ("authorization,content-type"),
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "access-control-allow-origin" not in response.headers
