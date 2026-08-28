from fastapi.testclient import TestClient


def test_api_root_is_available(
    client: TestClient,
) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "message": "Task API running",
    }


def test_openapi_contains_primary_routes(
    client: TestClient,
) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200

    paths = set(response.json()["paths"])

    assert {
        "/",
        "/auth/register",
        "/auth/login",
        "/tasks/",
        "/assistant/",
        "/assistant/actions/{action_id}/confirm",
        "/assistant/actions/{action_id}/cancel",
    }.issubset(paths)
