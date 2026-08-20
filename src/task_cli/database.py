from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from task_cli.config import get_settings
from task_cli.models import Base

settings = get_settings()


engine = create_engine(
    settings.database_url
    )


SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


def create_tables() -> None:

    Base.metadata.create_all(bind=engine)


def get_session() -> Generator[Session, None, None]:

    session = SessionLocal()

    try:
        yield session

    finally:
        session.close()
