import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    database_url: str
    log_level: str
    jwt_secret_key: str | None
    jwt_algorithm: str
    access_token_expire_minutes: int


def get_settings() -> Settings:
    return Settings(
        database_url=os.getenv(
            "DATABASE_URL",
            "sqlite:///data/tasks.db",
        ),
        log_level=os.getenv(
            "LOG_LEVEL",
            "INFO",
        ),
        jwt_secret_key=(os.getenv("JWT_SECRET_KEY") or None),
        jwt_algorithm=os.getenv(
            "JWT_ALGORITHM",
            "HS256",
        ),
        access_token_expire_minutes=int(
            os.getenv(
                "ACCESS_TOKEN_EXPIRE_MINUTES",
                "30",
            )
        ),
    )
