from datetime import (
    UTC,
    datetime,
    timedelta,
)
from typing import Any

from jose import jwt

from task_cli.config import (
    Settings,
    get_settings,
)


def _require_jwt_secret_key(
    settings: Settings,
) -> str:
    secret_key = settings.jwt_secret_key

    if secret_key is None:
        raise RuntimeError("未配置 JWT_SECRET_KEY")

    return secret_key


def create_access_token(
    data: dict[str, Any],
) -> str:
    settings = get_settings()

    secret_key = _require_jwt_secret_key(settings)

    to_encode = data.copy()

    expire = datetime.now(UTC) + timedelta(
        minutes=(settings.access_token_expire_minutes)
    )

    to_encode.update(
        {
            "exp": expire,
        }
    )

    return jwt.encode(
        to_encode,
        secret_key,
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(
    token: str,
) -> dict[str, Any]:
    settings = get_settings()

    secret_key = _require_jwt_secret_key(settings)

    return jwt.decode(
        token,
        secret_key,
        algorithms=[
            settings.jwt_algorithm,
        ],
    )
