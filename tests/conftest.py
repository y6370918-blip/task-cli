from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from task_cli.api import app
from task_cli.auth_dependencies import get_current_user
from task_cli.dependencies import get_db
from task_cli.models import (
    Base,
    Task,
    User,
)


# =========================================================
# 测试数据库
# =========================================================

TEST_DATABASE_URL = "sqlite://"


engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={
        "check_same_thread": False,
    },
    poolclass=StaticPool,
)


TestingSessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)


# =========================================================
# 每个测试独立数据库
# =========================================================

@pytest.fixture
def db_session() -> Generator[
    Session,
    None,
    None,
]:
    Base.metadata.drop_all(
        bind=engine
    )

    Base.metadata.create_all(
        bind=engine
    )

    session = TestingSessionLocal()

    try:
        yield session

    finally:
        session.rollback()
        session.close()

        Base.metadata.drop_all(
            bind=engine
        )


# =========================================================
# 普通 TestClient
# =========================================================

@pytest.fixture
def client(
    db_session: Session,
) -> Generator[
    TestClient,
    None,
    None,
]:

    def override_get_db() -> Generator[
        Session,
        None,
        None,
    ]:
        yield db_session

    app.dependency_overrides.clear()

    app.dependency_overrides[
        get_db
    ] = override_get_db

    try:
        with TestClient(app) as test_client:
            yield test_client

    finally:
        app.dependency_overrides.clear()


# =========================================================
# 当前测试用户
# =========================================================

@pytest.fixture
def user(
    db_session: Session,
) -> User:

    user = User(
        username="testuser",
        email="test@example.com",
        password_hash="fake-password-hash",
    )

    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    return user


# =========================================================
# 第二个用户
#
# 用于 ownership / 越权测试
# =========================================================

@pytest.fixture
def other_user(
    db_session: Session,
) -> User:

    user = User(
        username="otheruser",
        email="other@example.com",
        password_hash="fake-password-hash",
    )

    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    return user


# =========================================================
# 当前用户自己的 Task
# =========================================================

@pytest.fixture
def task(
    db_session: Session,
    user: User,
) -> Task:

    task = Task(
        title="Test Task",
        description="Test Description",
        status="pending",
        owner_id=user.id,
    )

    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    return task


# =========================================================
# 模拟已登录客户端
# =========================================================

@pytest.fixture
def authenticated_client(
    client: TestClient,
    user: User,
) -> Generator[
    TestClient,
    None,
    None,
]:

    def override_get_current_user() -> User:
        return user

    app.dependency_overrides[
        get_current_user
    ] = override_get_current_user

    try:
        yield client

    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )