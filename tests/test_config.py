import pytest

from task_cli.config import get_settings


def test_default_settings() -> None:
    settings = get_settings()

    assert settings.database_url


def test_jwt_settings_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "JWT_SECRET_KEY",
        "test-secret-key-for-jwt-settings",
    )
    monkeypatch.setenv(
        "JWT_ALGORITHM",
        "HS512",
    )
    monkeypatch.setenv(
        "ACCESS_TOKEN_EXPIRE_MINUTES",
        "60",
    )

    settings = get_settings()

    assert settings.jwt_secret_key == "test-secret-key-for-jwt-settings"
    assert settings.jwt_algorithm == "HS512"
    assert settings.access_token_expire_minutes == 60


def test_invalid_access_token_expire_minutes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "ACCESS_TOKEN_EXPIRE_MINUTES",
        "invalid",
    )

    with pytest.raises(ValueError):
        get_settings()


def test_default_frontend_origin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(
        "FRONTEND_ORIGIN",
        raising=False,
    )

    settings = get_settings()

    assert settings.frontend_origin == "http://localhost:5173"


def test_frontend_origin_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "FRONTEND_ORIGIN",
        "https://task.example.com",
    )

    settings = get_settings()

    assert settings.frontend_origin == "https://task.example.com"
