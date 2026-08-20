import pytest
from fastapi import HTTPException
from jose import JWTError
from sqlalchemy.orm import Session

from task_cli.auth import (
    create_access_token,
    decode_access_token,
)
from task_cli.auth_dependencies import (
    get_current_user,
)
from task_cli.models import User

TEST_SECRET_KEY = "test-jwt-secret-key-for-day25"


def _configure_jwt(
    monkeypatch: pytest.MonkeyPatch,
    secret_key: str = TEST_SECRET_KEY,
) -> None:
    monkeypatch.setenv(
        "JWT_SECRET_KEY",
        secret_key,
    )
    monkeypatch.setenv(
        "JWT_ALGORITHM",
        "HS256",
    )
    monkeypatch.setenv(
        "ACCESS_TOKEN_EXPIRE_MINUTES",
        "30",
    )


def test_access_token_round_trip(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_jwt(monkeypatch)

    original_data = {
        "user_id": 123,
    }

    token = create_access_token(original_data)

    payload = decode_access_token(token)

    assert payload["user_id"] == 123
    assert "exp" in payload
    assert "exp" not in original_data


def test_create_access_token_requires_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(
        "JWT_SECRET_KEY",
        raising=False,
    )

    with pytest.raises(
        RuntimeError,
        match="未配置 JWT_SECRET_KEY",
    ):
        create_access_token(
            {
                "user_id": 123,
            }
        )


def test_decode_rejects_wrong_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_jwt(
        monkeypatch,
        secret_key=("first-test-secret-key"),
    )

    token = create_access_token(
        {
            "user_id": 123,
        }
    )

    monkeypatch.setenv(
        "JWT_SECRET_KEY",
        "different-test-secret-key",
    )

    with pytest.raises(JWTError):
        decode_access_token(token)


def test_get_current_user_from_token(
    monkeypatch: pytest.MonkeyPatch,
    db_session: Session,
    user: User,
) -> None:
    _configure_jwt(monkeypatch)

    token = create_access_token(
        {
            "user_id": user.id,
        }
    )

    current_user = get_current_user(
        token=token,
        db=db_session,
    )

    assert current_user.id == user.id
    assert current_user.username == user.username


def test_get_current_user_rejects_missing_user(
    monkeypatch: pytest.MonkeyPatch,
    db_session: Session,
) -> None:
    _configure_jwt(monkeypatch)

    token = create_access_token(
        {
            "user_id": 999999,
        }
    )

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(
            token=token,
            db=db_session,
        )

    assert exc_info.value.status_code == 401


def test_get_current_user_rejects_invalid_token(
    monkeypatch: pytest.MonkeyPatch,
    db_session: Session,
) -> None:
    _configure_jwt(monkeypatch)

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(
            token="not-a-valid-token",
            db=db_session,
        )

    assert exc_info.value.status_code == 401


def test_get_current_user_preserves_missing_secret_error(
    monkeypatch: pytest.MonkeyPatch,
    db_session: Session,
) -> None:
    monkeypatch.delenv(
        "JWT_SECRET_KEY",
        raising=False,
    )

    with pytest.raises(
        RuntimeError,
        match="未配置 JWT_SECRET_KEY",
    ):
        get_current_user(
            token="any-token",
            db=db_session,
        )
