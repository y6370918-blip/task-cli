import os
from collections.abc import Generator
from datetime import datetime

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import (
    create_engine,
    inspect,
    text,
)
from sqlalchemy.engine import Engine

TEST_POSTGRES_URL = os.getenv("TEST_POSTGRES_URL")

pytestmark = [
    pytest.mark.postgres,
    pytest.mark.skipif(
        not TEST_POSTGRES_URL,
        reason=("TEST_POSTGRES_URL is not configured"),
    ),
]


@pytest.fixture(scope="module")
def postgres_engine() -> Generator[
    Engine,
    None,
    None,
]:
    assert TEST_POSTGRES_URL is not None

    engine = create_engine(TEST_POSTGRES_URL)

    try:
        if engine.dialect.name != "postgresql":
            pytest.fail("TEST_POSTGRES_URL must use PostgreSQL")

        with engine.connect() as connection:
            database_name = connection.scalar(text("SELECT current_database()"))

        if not isinstance(database_name, str) or "test" not in database_name.lower():
            pytest.fail(
                "PostgreSQL integration tests "
                "require a database whose name "
                "contains 'test'"
            )

        yield engine

    finally:
        engine.dispose()


def test_postgres_connection_returns_aware_time(
    postgres_engine: Engine,
) -> None:
    with postgres_engine.connect() as connection:
        current_time = connection.scalar(text("SELECT CURRENT_TIMESTAMP"))

    assert isinstance(
        current_time,
        datetime,
    )
    assert current_time.tzinfo is not None


def test_postgres_schema_is_at_alembic_head(
    postgres_engine: Engine,
) -> None:
    alembic_config = Config("alembic.ini")

    script_directory = ScriptDirectory.from_config(alembic_config)

    code_heads = set(script_directory.get_heads())

    with postgres_engine.connect() as connection:
        database_heads = set(
            connection.scalars(text("SELECT version_num FROM alembic_version"))
        )

    assert database_heads == code_heads

    inspector = inspect(postgres_engine)

    expected_tables = {
        "alembic_version",
        "users",
        "tasks",
        "pending_actions",
        "conversations",
        "messages",
    }

    assert expected_tables.issubset(inspector.get_table_names())


def test_postgres_schema_has_critical_constraints(
    postgres_engine: Engine,
) -> None:
    inspector = inspect(postgres_engine)

    task_foreign_keys = inspector.get_foreign_keys("tasks")

    assert any(
        foreign_key["referred_table"] == "users"
        and foreign_key["constrained_columns"] == ["owner_id"]
        for foreign_key in task_foreign_keys
    )

    message_checks = inspector.get_check_constraints("messages")

    assert any(
        constraint["name"] == "ck_messages_role" for constraint in message_checks
    )
