import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from task_cli.auth import decode_access_token
from task_cli.models import User
from task_cli.security import verify_password


def test_register_creates_user(
    client: TestClient,
    db_session: Session,
) -> None:
    response = client.post(
        "/auth/register",
        json={
            "username": "alice",
            "email": "alice@example.com",
            "password": "password123",
        },
    )

    assert response.status_code == 201

    response_data = response.json()

    assert response_data["id"] is not None
    assert response_data["username"] == "alice"
    assert response_data["email"] == "alice@example.com"
    assert set(response_data) == {
        "id",
        "username",
        "email",
    }

    statement = select(User).where(User.username == "alice")
    user = db_session.scalar(statement)

    assert user is not None
    assert user.password_hash != "password123"
    assert verify_password(
        "password123",
        user.password_hash,
    )


def test_register_rejects_duplicate_user(
    client: TestClient,
    user: User,
) -> None:
    response = client.post(
        "/auth/register",
        json={
            "username": user.username,
            "email": "different@example.com",
            "password": "password123",
        },
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "用户名或邮箱已存在",
    }


@pytest.mark.parametrize(
    "payload",
    [
        {
            "username": "ab",
            "email": "alice@example.com",
            "password": "password123",
        },
        {
            "username": "alice",
            "email": "not-an-email",
            "password": "password123",
        },
        {
            "username": "alice",
            "email": "alice@example.com",
            "password": "short",
        },
        {
            "username": "alice",
            "email": "alice@example.com",
            "password": "password123",
            "is_admin": True,
        },
    ],
)
def test_register_rejects_invalid_payload(
    client: TestClient,
    payload: dict[str, object],
) -> None:
    response = client.post(
        "/auth/register",
        json=payload,
    )

    assert response.status_code == 422


def test_registered_user_can_login(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "JWT_SECRET_KEY",
        "test-secret-key-for-day26-at-least-32-bytes",
    )

    register_response = client.post(
        "/auth/register",
        json={
            "username": "alice",
            "email": "alice@example.com",
            "password": "password123",
        },
    )

    login_response = client.post(
        "/auth/login",
        data={
            "username": "alice",
            "password": "password123",
        },
    )

    assert register_response.status_code == 201
    assert login_response.status_code == 200

    response_data = login_response.json()

    assert response_data["token_type"] == "bearer"
    assert isinstance(
        response_data["access_token"],
        str,
    )

    payload = decode_access_token(response_data["access_token"])

    assert payload["user_id"] == register_response.json()["id"]


def test_login_rejects_wrong_password(
    client: TestClient,
) -> None:
    register_response = client.post(
        "/auth/register",
        json={
            "username": "alice",
            "email": "alice@example.com",
            "password": "password123",
        },
    )

    login_response = client.post(
        "/auth/login",
        data={
            "username": "alice",
            "password": "wrong-password",
        },
    )

    assert register_response.status_code == 201
    assert login_response.status_code == 401
    assert login_response.json() == {
        "detail": "用户名或密码错误",
    }
