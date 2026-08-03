import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    database_url: str

    log_level: str


def get_settings() -> Settings:

    return Settings(
        database_url=os.getenv("DATABASE_URL", "sqlite:///data/tasks.db"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )
