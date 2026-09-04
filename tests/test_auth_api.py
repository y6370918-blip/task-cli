import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from task_cli.auth import create_access_token, decode_access_token
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


def test_get_me_returns_current_user(
    client: TestClient,
    user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # 使用测试专用密钥，避免依赖本机 .env 中的真实密钥。
    # monkeypatch 会在测试结束后自动恢复环境变量。
    monkeypatch.setenv(
        "JWT_SECRET_KEY",
        "day53-test-secret-key-at-least-32-bytes-long",
    )

    # user 是测试数据库里的真实 ORM 用户。
    # 调用项目已有函数签发真实 JWT，不替换认证依赖。
    token = create_access_token({"user_id": user.id})

    # 使用普通 client，确保请求经过真实的 get_current_user。
    # Bearer 与 Token 之间必须有一个空格。
    response = client.get(
        "/auth/me",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 200

    # 比较完整字典，同时验证：
    # 1. 返回的是 Token 对应的用户。
    # 2. 响应没有混入 password_hash 等额外字段。
    assert response.json() == {
        "id": user.id,
        "username": user.username,
        "email": user.email,
    }


def test_get_me_rejects_missing_token(
    client: TestClient,
) -> None:
    # 没有发送 Authorization 请求头，不能获取用户资料。
    response = client.get("/auth/me")

    assert response.status_code == 401


def test_get_me_rejects_invalid_token(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "JWT_SECRET_KEY",
        "day53-test-secret-key-at-least-32-bytes-long",
    )

    # 字符串不为空，不代表它是有效 JWT。
    response = client.get(
        "/auth/me",
        headers={
            "Authorization": "Bearer not-a-valid-token",
        },
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "无法验证身份",
    }


def test_get_me_rejects_token_for_missing_user(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "JWT_SECRET_KEY",
        "day53-test-secret-key-at-least-32-bytes-long",
    )

    # 当前测试没有使用 user fixture，也没有创建用户。
    # 根据已有 conftest.py，每个测试都有独立的空白 SQLite 表，
    # 因此测试数据库中不存在 ID 为 999 的用户。
    token = create_access_token({"user_id": 999})

    response = client.get(
        "/auth/me",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    # JWT 签名有效，也不能让不存在的用户获得身份。
    # 这个测试证明认证过程仍然查询了数据库。
    assert response.status_code == 401
    assert response.json() == {
        "detail": "无法验证身份",
    }
